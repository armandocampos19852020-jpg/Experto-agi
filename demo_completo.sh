#!/bin/bash
set -e

# --- TUS CREDENCIALES ---
export NVIDIA_API_KEY="TU_NVIDIA_KEY"
export STRIPE_API_KEY="TU_STRIPE_KEY"
export STRIPE_WEBHOOK_SECRET="TU_WEBHOOK_SECRET"
export KAGGLE_USERNAME="TU_USER"
export KAGGLE_KEY="TU_KAGGLE_KEY"

echo "🏟️  [$(date)] Forjando el Imperio EXPERTO-AGI..."

# 1. Limpieza de mina (vital para tus 32GB de disco)
rm -rf /workspaces/Experto-agi/temp_*
docker system prune -f --volumes

# 2. Instalación de armamento pesado
pip install -q fastapi uvicorn openai stripe kagglehub datasets

# 3. Lanzar la API en segundo plano
nohup python nim_c2_agent_api.py --host 0.0.0.0 --port 8000 > empire.log 2>&1 &
echo "🚀 API ONLINE en puerto 8000"

# 4. Sincronizar con el ejecutor remoto
echo "🤖 Sincronizando agentes remotos..."
python -c "import os; os.makedirs('generadas', exist_ok=True)"

echo "💵 La Consulta Cuántica (prod_UH45ySzQNmoRtq) está lista para facturar."
echo "Check log: tail -f empire.log"
