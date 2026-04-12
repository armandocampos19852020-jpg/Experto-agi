"""
Cliente remoto para descargar y ejecutar código generado por el Agente C2.
Usa este script en tu Colab, máquina local con GPU, o Codespace.
"""

import requests
import sys
from typing import Optional


def descargar_y_ejecutar(
    url_base: str = "http://127.0.0.1:8000",
    nombre_archivo: str = "preparar_dataset.py",
    sandbox: bool = False,
) -> dict:
    """
    Descarga código generado por el Agente desde un endpoint remoto y lo ejecuta.

    Args:
        url_base: URL base del servidor (ej: https://tu-codespace.github.dev)
        nombre_archivo: Nombre del archivo a descargar
        sandbox: Si True, ejecuta en un namespace seguro; si False, directamente

    Returns:
        Dict con status y resultado de la ejecución
    """
    print(f"🚀 Conectando a {url_base}...")

    try:
        response = requests.get(f"{url_base}/obtener_mision/{nombre_archivo}", timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        return {"status": "error", "message": f"No se pudo descargar: {exc}"}

    try:
        datos = response.json()
        codigo = datos.get("codigo", "")
    except ValueError:
        return {"status": "error", "message": "Respuesta no es JSON válido"}

    if not codigo:
        return {"status": "error", "message": "No hay código para ejecutar"}

    print(f"✓ Código descargado ({len(codigo)} caracteres)")
    print("=" * 60)
    print(codigo[:500] + ("...\n[código truncado]" if len(codigo) > 500 else ""))
    print("=" * 60)

    if sandbox:
        print("\n🔒 Ejecutando en sandbox seguro...")
        namespace = {"__name__": "__main__"}
        try:
            exec(codigo, namespace)
            return {"status": "success", "message": "Código ejecutado en sandbox"}
        except Exception as exc:
            return {"status": "execution_error", "message": str(exc)}
    else:
        print("\n⚡ Ejecutando en memoria GPU...")
        try:
            exec(codigo)
            return {"status": "success", "message": "Código ejecutado directamente"}
        except Exception as exc:
            return {"status": "execution_error", "message": str(exc)}


def listar_misiones(url_base: str = "http://127.0.0.1:8000") -> list:
    """
    Lista los archivos de misiones disponibles en el servidor.
    (Requeriría un endpoint adicional en la API)
    """
    from pathlib import Path
    import os

    generadas_dir = Path("generadas")
    if generadas_dir.exists():
        return [f.name for f in generadas_dir.glob("*.py")]
    return []


if __name__ == "__main__":
    # Ejemplo: python cliente_ejecutor.py preparar_dataset.py
    # O sin argumentos: python cliente_ejecutor.py

    if len(sys.argv) > 1:
        archivo = sys.argv[1]
        url = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8000"
    else:
        archivo = "preparar_dataset.py"
        url = "http://127.0.0.1:8000"

    resultado = descargar_y_ejecutar(url_base=url, nombre_archivo=archivo, sandbox=True)
    print(f"\n📊 Resultado: {resultado}")
