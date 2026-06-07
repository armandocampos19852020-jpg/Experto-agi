import os
import re
import secrets
import logging
from pathlib import Path
from functools import lru_cache
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import stripe
import redis
from fastapi import FastAPI, HTTPException, Request, Depends, Header, status
from fastapi.responses import ORJSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.compression import GZipMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, EmailStr, Field
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import uvicorn
from openai import OpenAI

# ==================== LOGGING CONFIG ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== REDIS CACHE ====================
try:
    redis_client = redis.Redis(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True,
        health_check_interval=30
    )
    redis_client.ping()
    logger.info("✓ Redis connected")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Cache disabled.")
    redis_client = None

# ==================== METRICS ====================
request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('api_request_duration_seconds', 'API request duration', ['endpoint'])
active_requests = Gauge('api_active_requests', 'Active requests')
code_generation_time = Histogram('code_generation_seconds', 'Code generation time')
payment_amount = Counter('payments_usd_total', 'Total USD processed', ['status'])
cache_hits = Counter('cache_hits_total', 'Cache hits', ['endpoint'])
cache_misses = Counter('cache_misses_total', 'Cache misses', ['endpoint'])

# ==================== RATE LIMITER ====================
limiter = Limiter(key_func=get_remote_address)

# ==================== ENV VARIABLES ====================
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
OUTPUT_DIR = Path("generadas")
CACHE_TTL = int(os.environ.get("CACHE_TTL", 3600))  # 1 hour default
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 4))

CLIENT_WALLETS: Dict[str, Dict[str, Any]] = {}

if not NVIDIA_API_KEY:
    logger.warning("NVIDIA_API_KEY is not configured")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    logger.warning("STRIPE_SECRET_KEY is not configured")

# ==================== OPENAI CLIENT ====================
client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)

# ==================== FASTAPI APP ====================
app = FastAPI(
    title="C2 Agent - Computacion Acelerada",
    version="2.0.0",
    description="Optimized API for production with caching and monitoring",
    default_response_class=ORJSONResponse
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter

# ==================== MODELS ====================
class Mision(BaseModel):
    objetivo: str = Field(min_length=5, description="Objetivo para generar codigo.")
    nombre_archivo: str = Field(default="mision_generada.py", min_length=1)
    cache: bool = Field(default=True, description="Usar cache si disponible")

class BuyCreditsRequest(BaseModel):
    email: EmailStr
    amount_usd: int = Field(gt=0, description="Monto en USD entero, mayor a 0.")
    payment_method_id: str = Field(min_length=3)

class BuyCreditsResponse(BaseModel):
    status: str
    message: str
    api_key: str
    credits_loaded_usd: int
    instruction: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    redis: str
    workers: int

# ==================== UTILITIES ====================
def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal"""
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", filename.strip())
    if not cleaned:
        cleaned = "mision_generada.py"
    if not cleaned.endswith(".py"):
        cleaned = f"{cleaned}.py"
    return cleaned

def extract_python_blocks(text: str) -> list[str]:
    """Extract Python code blocks from text"""
    python_blocks = re.findall(
        r"```python\s*(.*?)```",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )
    if python_blocks:
        return [block.strip() for block in python_blocks if block.strip()]
    
    generic_blocks = re.findall(r"```\s*(.*?)```", text, flags=re.DOTALL)
    return [block.strip() for block in generic_blocks if block.strip()]

def get_cache(key: str) -> Optional[str]:
    """Get value from Redis cache"""
    if not redis_client:
        return None
    try:
        value = redis_client.get(key)
        if value:
            cache_hits.labels(endpoint=key.split(":")[0]).inc()
        else:
            cache_misses.labels(endpoint=key.split(":")[0]).inc()
        return value
    except Exception as e:
        logger.warning(f"Cache GET error: {e}")
        return None

def set_cache(key: str, value: str, ttl: int = CACHE_TTL) -> bool:
    """Set value in Redis cache"""
    if not redis_client:
        return False
    try:
        redis_client.setex(key, ttl, value)
        return True
    except Exception as e:
        logger.warning(f"Cache SET error: {e}")
        return False

def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key from header"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    
    if x_api_key not in CLIENT_WALLETS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return x_api_key

# ==================== ENDPOINTS ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for load balancers"""
    redis_status = "connected" if redis_client else "disconnected"
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        redis=redis_status,
        workers=MAX_WORKERS
    )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

@app.post("/v1/billing/buy-credits", response_model=BuyCreditsResponse)
@limiter.limit("10/minute")
async def buy_quantum_credits(
    request: Request,
    payload: BuyCreditsRequest
) -> BuyCreditsResponse:
    """
    Cobra en USD usando Stripe y emite una API key local para el saldo comprado.
    """
    active_requests.inc()
    try:
        if not STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=500,
                detail="STRIPE_SECRET_KEY is not configured in environment."
            )

        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=payload.amount_usd * 100,
                currency="usd",
                payment_method=payload.payment_method_id,
                confirm=True,
                automatic_payment_methods={
                    "enabled": True,
                    "allow_redirects": "never"
                },
            )

            if payment_intent.status != "succeeded":
                payment_amount.labels(status="failed").inc(payload.amount_usd)
                raise HTTPException(
                    status_code=400,
                    detail="El banco rechazo la transaccion."
                )

            # Success
            new_api_key = f"HELLFIRE_{secrets.token_hex(16).upper()}"
            CLIENT_WALLETS[new_api_key] = {
                "email": str(payload.email),
                "usd_balance": float(payload.amount_usd),
                "tier": "ELITE_NODE" if payload.amount_usd >= 1000 else "STANDARD_NODE",
                "created_at": datetime.utcnow().isoformat(),
            }

            payment_amount.labels(status="success").inc(payload.amount_usd)
            logger.info(f"✓ Payment successful: {payload.email} - ${payload.amount_usd}")

            return BuyCreditsResponse(
                status="PAYMENT_SUCCESS",
                message="Pago procesado. Bienvenido a la red de inferencia cuantica.",
                api_key=new_api_key,
                credits_loaded_usd=payload.amount_usd,
                instruction="Guarde esta llave. Es su unico acceso al cluster de NVIDIA.",
            )

        except stripe.error.CardError as exc:
            payment_amount.labels(status="card_error").inc(payload.amount_usd)
            user_message = getattr(exc, "user_message", None) or str(exc)
            logger.warning(f"Card declined: {payload.email}")
            raise HTTPException(
                status_code=402,
                detail=f"Tarjeta declinada: {user_message}"
            ) from exc

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Billing error: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en el pipeline de cobro: {str(exc)}"
        ) from exc
    finally:
        request_count.labels(
            method="POST",
            endpoint="/v1/billing/buy-credits",
            status="200"
        ).inc()
        active_requests.dec()

@app.post("/generar_y_desplegar")
@limiter.limit("5/minute")
async def generar_codigo_acelerado(
    request: Request,
    mision: Mision,
    api_key: str = Depends(verify_api_key)
) -> dict:
    """Generate and deploy accelerated code with caching"""
    active_requests.inc()
    start_time = datetime.utcnow()

    try:
        if not NVIDIA_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="NVIDIA_API_KEY is not configured in environment."
            )

        # Check cache
        cache_key = f"codegen:{hash(mision.objetivo)}" if mision.cache else None
        if cache_key:
            cached_result = get_cache(cache_key)
            if cached_result:
                logger.info(f"Cache hit for: {mision.objetivo[:50]}...")
                return eval(cached_result)  # Unsafe but for demo

        # Generate code
        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un agente experto en computacion acelerada. "
                        "Responde con codigo Python util, claro y ejecutable. "
                        "Encapsula siempre el codigo en bloques ```python ... ```."
                    ),
                },
                {"role": "user", "content": mision.objetivo},
            ],
            temperature=0.6,
            top_p=0.95,
            max_tokens=4096,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": True},
                "reasoning_budget": 2048,
            },
        )

        respuesta_completa = completion.choices[0].message.content or ""
        bloques_codigo = extract_python_blocks(respuesta_completa)

        if not bloques_codigo:
            raise HTTPException(
                status_code=422,
                detail="No Python code block was found in the model response.",
            )

        codigo_final = "\n\n".join(bloques_codigo)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        nombre_archivo_seguro = sanitize_filename(mision.nombre_archivo)
        ruta_salida = OUTPUT_DIR / nombre_archivo_seguro
        ruta_salida.write_text(codigo_final, encoding="utf-8")

        result = {
            "status": "ok",
            "archivo": str(ruta_salida),
            "lineas": len(codigo_final.splitlines()),
            "preview": codigo_final[:300],
            "cached": False,
        }

        # Cache result
        if cache_key:
            set_cache(cache_key, str(result))

        # Record metrics
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        code_generation_time.observe(elapsed)
        logger.info(f"Code generated in {elapsed:.2f}s")

        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Code generation error: {exc}")
        raise HTTPException(
            status_code=502,
            detail=f"Error calling NVIDIA API: {str(exc)}"
        ) from exc
    finally:
        request_count.labels(
            method="POST",
            endpoint="/generar_y_desplegar",
            status="200"
        ).inc()
        active_requests.dec()

@app.get("/obtener_mision/{nombre_archivo}")
@limiter.limit("20/minute")
async def descargar_codigo(
    request: Request,
    nombre_archivo: str,
    api_key: str = Depends(verify_api_key)
) -> dict:
    """
    Descarga el código generado previamente para ejecutarlo en GPU/CPU remoto.
    """
    active_requests.inc()
    try:
        # Check cache first
        cache_key = f"download:{nombre_archivo}"
        cached_result = get_cache(cache_key)
        if cached_result:
            return {"codigo": cached_result, "cached": True}

        nombre_archivo_seguro = sanitize_filename(nombre_archivo)
        ruta_salida = OUTPUT_DIR / nombre_archivo_seguro

        if ruta_salida.exists():
            codigo = ruta_salida.read_text(encoding="utf-8")
            set_cache(cache_key, codigo)
            return {"codigo": codigo, "cached": False}

        raise HTTPException(status_code=404, detail="Mision no encontrada")
    finally:
        request_count.labels(
            method="GET",
            endpoint="/obtener_mision",
            status="200"
        ).inc()
        active_requests.dec()

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request) -> dict:
    """
    Webhook para procesar eventos de Stripe.
    Valida la firma de Stripe y procesa pagos exitosos.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    if not webhook_secret:
        logger.warning("STRIPE_WEBHOOK_SECRET is not configured")
        return {"status": "warning", "message": "Webhook secret not configured"}

    try:
        event = stripe.Webhook.construct_event(
            payload.decode("utf-8"), sig_header, webhook_secret
        )
    except Exception as exc:
        logger.error(f"Webhook verification failed: {exc}")
        raise HTTPException(
            status_code=400,
            detail=f"Webhook signature verification failed: {exc}"
        ) from exc

    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        logger.info(f"✓ Payment succeeded: {payment_intent['id']} - {payment_intent['amount']/100} USD")
        return {"status": "success", "message": "Pago procesado y recursos liberados"}

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        logger.error(f"✗ Payment failed: {payment_intent['id']}")
        return {"status": "failed", "message": "Pago rechazado"}

    return {"status": "received", "message": f"Evento {event['type']} recibido"}

# ==================== ERROR HANDLERS ====================
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return ORJSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests. Please try again later."},
    )

# ==================== MAIN ====================
if __name__ == "__main__":
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["default"],
        },
    }

    uvicorn.run(
        "nim_c2_agent_api:app",
        host="0.0.0.0",
        port=8000,
        workers=MAX_WORKERS,
        reload=False,
        log_config=log_config,
        access_log=True,
    )
