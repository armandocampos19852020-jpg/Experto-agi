import base64
import os
from datetime import datetime

import requests
from fpdf import FPDF


def generar_ebook_elite() -> str:
    print(">>> Iniciando Protocolo de Generacion de Activo Digital...")

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 24)
    pdf.cell(200, 20, txt="ARQUITECTURA DE SUPREMACIA IA", ln=1, align="C")
    pdf.set_font("Arial", "I", 12)
    pdf.cell(
        200,
        10,
        txt="Guia Estrategica 2026 - Generado por Agente Autonomo",
        ln=1,
        align="C",
    )

    pdf.ln(20)
    pdf.set_font("Arial", size=12)
    contenido = [
        "1. La Era Agentica: Dejar de operar y empezar a orquestar.",
        "2. El Stack Tecnologico: NVIDIA Blackwell y Google Gemini.",
        "3. Automatizacion de Ingresos: Como usar Python para vender.",
        "4. El Futuro: Agentes que se pagan a si mismos.",
        "",
        "Este documento es un activo digital generado automaticamente.",
        f"Fecha de generacion: {datetime.now().strftime('%Y-%m-%d')}",
    ]

    for linea in contenido:
        pdf.cell(200, 10, txt=linea, ln=1, align="L")

    nombre_archivo = "Supremacia_IA_Elite_2026.pdf"
    pdf.output(nombre_archivo)
    print(f">>> EXITO: Documento '{nombre_archivo}' generado.")
    return nombre_archivo


def _build_basic_header(client_id: str, client_secret: str, basic_token: str) -> str:
    if basic_token:
        return f"Basic {basic_token}"

    credenciales = f"{client_id}:{client_secret}"
    token_b64 = base64.b64encode(credenciales.encode()).decode()
    return f"Basic {token_b64}"


def conectar_hotmart() -> str | None:
    print("\n>>> Estableciendo enlace seguro con Hotmart...")

    client_id = os.getenv("HOTMART_CLIENT_ID", "")
    client_secret = os.getenv("HOTMART_CLIENT_SECRET", "")
    basic_token = os.getenv("HOTMART_BASIC_TOKEN", "")

    if not basic_token and (not client_id or not client_secret):
        print(
            "[ALERTA] Faltan credenciales. Define HOTMART_BASIC_TOKEN o HOTMART_CLIENT_ID/HOTMART_CLIENT_SECRET."
        )
        return None

    auth_url = "https://api-sec-vlc.hotmart.com/security/oauth/token"
    headers = {
        "Content-Type": "application/json",
        "Authorization": _build_basic_header(client_id, client_secret, basic_token),
    }

    try:
        response = requests.post(
            auth_url,
            params={"grant_type": "client_credentials"},
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            if not access_token:
                print("!!! ERROR: Respuesta sin access_token.")
                return None

            print(">>> CONEXION ESTABLECIDA: Acceso de elite concedido.")
            print(f">>> Token temporal: {access_token[:10]}...")
            return access_token

        print(f"!!! ERROR DE CONEXION: {response.status_code}")
        print(response.text)
        return None
    except requests.RequestException as exc:
        print(f"!!! ERROR CRITICO DE RED: {exc}")
        return None


if __name__ == "__main__":
    generar_ebook_elite()
    conectar_hotmart()