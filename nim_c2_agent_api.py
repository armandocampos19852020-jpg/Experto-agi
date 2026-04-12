import os
import re
import secrets
from pathlib import Path

import stripe
from fastapi import FastAPI, HTTPException, Request
from openai import OpenAI
from pydantic import BaseModel, EmailStr, Field
import uvicorn


NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
OUTPUT_DIR = Path("generadas")
CLIENT_WALLETS: dict[str, dict] = {}

if not NVIDIA_API_KEY:
    print("WARNING: NVIDIA_API_KEY is not configured.")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    print("WARNING: STRIPE_SECRET_KEY is not configured.")

client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)
app = FastAPI(title="C2 Agent - Computacion Acelerada", version="1.0.0")


class Mision(BaseModel):
    objetivo: str = Field(min_length=5, description="Objetivo para generar codigo.")
    nombre_archivo: str = Field(default="mision_generada.py", min_length=1)


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


def sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", filename.strip())
    if not cleaned:
        cleaned = "mision_generada.py"
    if not cleaned.endswith(".py"):
        cleaned = f"{cleaned}.py"
    return cleaned


def extract_python_blocks(text: str) -> list[str]:
    # Capture fenced python blocks first, then generic fenced blocks.
    python_blocks = re.findall(r"```python\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if python_blocks:
        return [block.strip() for block in python_blocks if block.strip()]

    generic_blocks = re.findall(r"```\s*(.*?)```", text, flags=re.DOTALL)
    return [block.strip() for block in generic_blocks if block.strip()]


@app.post("/v1/billing/buy-credits", response_model=BuyCreditsResponse)
async def buy_quantum_credits(payload: BuyCreditsRequest) -> BuyCreditsResponse:
    """
    Cobra en USD usando Stripe y emite una API key local para el saldo comprado.
    """
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY is not configured in environment.")

    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=payload.amount_usd * 100,
            currency="usd",
            payment_method=payload.payment_method_id,
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        )

        if payment_intent.status != "succeeded":
            raise HTTPException(status_code=400, detail="El banco rechazo la transaccion.")

        new_api_key = f"HELLFIRE_{secrets.token_hex(16).upper()}"
        CLIENT_WALLETS[new_api_key] = {
            "email": str(payload.email),
            "usd_balance": float(payload.amount_usd),
            "tier": "ELITE_NODE" if payload.amount_usd >= 1000 else "STANDARD_NODE",
        }

        return BuyCreditsResponse(
            status="PAYMENT_SUCCESS",
            message="Pago procesado. Bienvenido a la red de inferencia cuantica.",
            api_key=new_api_key,
            credits_loaded_usd=payload.amount_usd,
            instruction="Guarde esta llave. Es su unico acceso al cluster de NVIDIA.",
        )

    except stripe.error.CardError as exc:
        user_message = getattr(exc, "user_message", None) or str(exc)
        raise HTTPException(status_code=402, detail=f"Tarjeta declinada: {user_message}") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en el pipeline de cobro: {exc}") from exc


@app.post("/generar_y_desplegar")
async def generar_codigo_acelerado(mision: Mision) -> dict:
    if not NVIDIA_API_KEY:
        raise HTTPException(status_code=500, detail="NVIDIA_API_KEY is not configured in environment.")

    try:
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
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error calling NVIDIA API: {exc}") from exc

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

    return {
        "status": "ok",
        "archivo": str(ruta_salida),
        "lineas": len(codigo_final.splitlines()),
        "preview": codigo_final[:300],
    }


@app.get("/obtener_mision/{nombre_archivo}")
async def descargar_codigo(nombre_archivo: str) -> dict:
    """
    Descarga el código generado previamente para ejecutarlo en GPU/CPU remoto.
    """
    nombre_archivo_seguro = sanitize_filename(nombre_archivo)
    ruta_salida = OUTPUT_DIR / nombre_archivo_seguro

    if ruta_salida.exists():
        return {"codigo": ruta_salida.read_text(encoding="utf-8")}

    raise HTTPException(status_code=404, detail="Mision no encontrada")


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
        print("WARNING: STRIPE_WEBHOOK_SECRET is not configured.")
        return {"status": "warning", "message": "Webhook secret not configured"}

    try:
        event = stripe.Webhook.construct_event(
            payload.decode("utf-8"), sig_header, webhook_secret
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {exc}") from exc

    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        print(f"✓ Pago exitoso: {payment_intent['id']} - {payment_intent['amount']/100} USD")
        # Aqui liberas ejecucion remota o desbloqueas recursos
        return {"status": "success", "message": "Pago procesado y recursos liberados"}

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        print(f"✗ Pago fallido: {payment_intent['id']}")
        return {"status": "failed", "message": "Pago rechazado"}

    return {"status": "received", "message": f"Evento {event['type']} recibido"}


if __name__ == "__main__":
    uvicorn.run("nim_c2_agent_api:app", host="0.0.0.0", port=8000, reload=False)
