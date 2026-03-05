#!/usr/bin/env bash
set -euo pipefail

echo "== Verificación NVIDIA / CUDA =="

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "[ERROR] 'nvidia-smi' no está disponible."
  echo "- Instala drivers NVIDIA en el host."
  echo "- Si usas Docker, instala nvidia-container-toolkit."
  exit 1
fi

echo "[OK] nvidia-smi encontrado: $(command -v nvidia-smi)"
echo
nvidia-smi || {
  echo "[ERROR] No se pudo ejecutar nvidia-smi correctamente."
  exit 1
}

echo
echo "== Verificación de dispositivos dentro del entorno =="
if ls /dev/nvidia* >/dev/null 2>&1; then
  echo "[OK] Dispositivos NVIDIA visibles en este entorno:"
  ls -1 /dev/nvidia*
else
  echo "[WARN] No se ven /dev/nvidia* en este entorno."
  echo "- Si estás en contenedor, inícialo con acceso GPU (ej. --gpus all)."
fi

echo
echo "== Resultado =="
echo "La aceleración NVIDIA está lista si viste tu GPU en nvidia-smi y no hubo errores."