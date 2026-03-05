# Experto AGI

Activación práctica de dos frentes:

- Computación acelerada con NVIDIA (verificación y diagnóstico rápido).
- Automatización de contenido (ebook + ideas de posts) sin credenciales hardcodeadas.

## 1) Requisitos

- Python 3.10+
- GPU NVIDIA con drivers instalados en el host
- (Opcional) credenciales de Hotmart para probar OAuth

## 2) Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Verificar aceleración NVIDIA

```bash
bash scripts/enable_nvidia_acceleration.sh
```

Este script valida:

- Si `nvidia-smi` está disponible
- Información de GPU y versión CUDA del driver
- Si el contenedor tiene acceso a `/dev/nvidia*`

## 4) Ejecutar automatización de contenido

Genera un ebook en PDF + un archivo Markdown con ideas de publicaciones:

```bash
python automation/content_automation.py --topic "IA para negocios" --ebook-title "Guía IA 2026"
```

Salida esperada:

- `output/ebook_YYYYMMDD_HHMMSS.pdf`
- `output/posts_YYYYMMDD_HHMMSS.md`

## 5) (Opcional) Probar conexión Hotmart

Define variables de entorno:

```bash
export HOTMART_CLIENT_ID="tu_client_id"
export HOTMART_CLIENT_SECRET="tu_client_secret"
python automation/content_automation.py --topic "IA para marketing" --connect-hotmart
```

## 6) Nota rápida sobre Docker/devcontainer

Si ejecutas fuera de este contenedor y quieres GPU en Docker:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Si ese comando falla, instala o corrige `nvidia-container-toolkit` en el host.
