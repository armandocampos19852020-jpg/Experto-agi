import os
import re
import stripe
import kagglehub
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI(title="EXPERTO-AGI Quantum Engine")

stripe.api_key = os.getenv("STRIPE_API_KEY", "")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

if not stripe.api_key:
    raise RuntimeError("Missing STRIPE_API_KEY")

if not WEBHOOK_SECRET:
    raise RuntimeError("Missing STRIPE_WEBHOOK_SECRET")

if not NVIDIA_API_KEY:
    raise RuntimeError("Missing NVIDIA_API_KEY")

client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=NVIDIA_API_KEY)

class Mision(BaseModel):
    objetivo: str
    nombre_archivo: str

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def 
_extract_python_code(text: str) -> str:
    match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/v1/pagos")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        amount = session.get("amount_total")
        customer_email = session.get("customer_details", {}).get("email")
        print(f"💰 PAGO RECIBIDO: {amount} - Liberando recursos para {customer_email or 'cliente desconocido'}")
        return {"status": "success", "amount_total": amount}

    return {"status": "ignored", "event_type": event["type"]}


@app.get("/descargar_modelo/{modelo_path:path}")
async def fetch_model(modelo_path: str):
    try:
        path = kagglehub.model_download(modelo_path)
        return {"status": "descargado", "local_path": path}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/generar_y_desplegar")
async def generar_codigo(mision: Mision):
    prompt = (
        f"Escribe un script de Python que cumpla esto: {mision.objetivo}. "
        "Solo dame el código entre bloques ```python ... ```."
    )

    try:
        completion = client.chat.completions.create(
            model="nvidia/nemotron-4-340b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2048,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {exc}")

    raw_code = ""
    if hasattr(completion, "choices") and completion.choices:
        first_choice = completion.choices[0]
        if hasattr(first_choice, "message"):
            raw_code = getattr(first_choice.message, "content", "") or first_choice.message.get("content", "")
        elif isinstance(first_choice, dict):
            raw_code = first_choice.get("message", {}).get("content", "")

    raw_code = (raw_code or "").strip()
    codigo = _extract_python_code(raw_code)
    if not codigo:
        raise HTTPException(status_code=500, detail="Error al extraer el código cuántico")

    os.makedirs("generadas", exist_ok=True)
    path = os.path.join("generadas", mision.nombre_archivo)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(codigo)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Error saving generated file: {exc}")

    return {"status": "Misión lista", "archivo": path}


@app.get("/obtener_mision/{nombre_archivo}")
async def get_mision(nombre_archivo: str):
    path = os.path.join("generadas", nombre_archivo)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"codigo": content}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

