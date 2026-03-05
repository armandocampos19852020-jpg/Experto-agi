from __future__ import annotations

import argparse
import base64
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests
from fpdf import FPDF


OUTPUT_DIR = Path("output")
HOTMART_AUTH_URL = "https://api-sec-vlc.hotmart.com/security/oauth/token"


@dataclass
class GeneratedAssets:
    pdf_path: Path
    posts_path: Path


def now_suffix() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_content(topic: str) -> list[str]:
    return [
        f"1. Panorama 2026 de {topic}",
        "2. Herramientas y stack recomendado",
        "3. Flujo semanal de automatización",
        "4. Métricas para escalar resultados",
        "5. Riesgos y checklist de operación",
    ]


def generate_ebook(title: str, topic: str) -> Path:
    ensure_output_dir()
    pdf_name = OUTPUT_DIR / f"ebook_{now_suffix()}.pdf"
    sections = build_content(topic)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 22)
    pdf.multi_cell(0, 12, title)
    pdf.ln(2)

    pdf.set_font("Helvetica", "I", 12)
    pdf.cell(0, 8, f"Tema: {topic}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.set_font("Helvetica", size=12)
    for item in sections:
        pdf.multi_cell(0, 8, f"- {item}")

    pdf.output(str(pdf_name))
    return pdf_name


def generate_posts_markdown(topic: str, amount: int = 10) -> Path:
    ensure_output_dir()
    posts_name = OUTPUT_DIR / f"posts_{now_suffix()}.md"

    lines = [
        f"# Ideas de contenido: {topic}",
        "",
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for index in range(1, amount + 1):
        lines.extend(
            [
                f"## Post {index}",
                f"- Hook: \"{topic}: el error #{index} que frena resultados\"",
                "- Desarrollo: 3 puntos accionables en formato carrusel.",
                "- CTA: Comenta 'plantilla' para recibir el checklist.",
                "",
            ]
        )

    posts_name.write_text("\n".join(lines), encoding="utf-8")
    return posts_name


def connect_hotmart() -> bool:
    client_id = os.getenv("HOTMART_CLIENT_ID", "")
    client_secret = os.getenv("HOTMART_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("[WARN] HOTMART_CLIENT_ID/HOTMART_CLIENT_SECRET no definidos. Se omite conexión Hotmart.")
        return False

    token_b64 = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {token_b64}",
    }

    response = requests.post(
        HOTMART_AUTH_URL,
        params={"grant_type": "client_credentials"},
        headers=headers,
        timeout=20,
    )

    if response.status_code == 200:
        token = response.json().get("access_token", "")
        print(f"[OK] Hotmart conectado. Token parcial: {token[:10]}...")
        return True

    print(f"[ERROR] Hotmart respondió {response.status_code}: {response.text}")
    return False


def run(topic: str, ebook_title: str, connect_hotmart_flag: bool) -> GeneratedAssets:
    pdf_path = generate_ebook(ebook_title, topic)
    posts_path = generate_posts_markdown(topic)

    if connect_hotmart_flag:
        connect_hotmart()

    return GeneratedAssets(pdf_path=pdf_path, posts_path=posts_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automatización de contenido + validación opcional de Hotmart")
    parser.add_argument("--topic", required=True, help="Tema principal de contenido")
    parser.add_argument("--ebook-title", default="Ebook automático 2026", help="Título del ebook")
    parser.add_argument("--connect-hotmart", action="store_true", help="Probar OAuth con variables de entorno")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    assets = run(topic=args.topic, ebook_title=args.ebook_title, connect_hotmart_flag=args.connect_hotmart)
    print("[OK] Activos generados:")
    print(f"- PDF: {assets.pdf_path}")
    print(f"- Posts: {assets.posts_path}")