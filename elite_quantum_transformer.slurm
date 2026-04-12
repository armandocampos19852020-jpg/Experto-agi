#!/bin/bash
#SBATCH --job-name=ELITE_QUANTUM_TRANSFORMER
#SBATCH --nodes=25
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:4
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=48
#SBATCH --mem=500G
#SBATCH --partition=quantum_elite
#SBATCH --output=logs/monster_%j.log
#SBATCH --error=logs/monster_%j.err

set -euo pipefail

mkdir -p logs

# --- CONFIGURACION DE ENTORNO ---
export CUDA_VISIBLE_DEVICES=0,1,2,3
export NCCL_DEBUG=INFO
export NCCL_ASYNC_ERROR_HANDLING=1
export CUQUANTUM_SDK_PATH=/opt/nvidia/cuquantum
export MPICH_MAX_THREAD_SAFETY=multiple

# Selecciona la interfaz correcta si tu cluster la requiere (ejemplo: ib0, eno1)
# export NCCL_SOCKET_IFNAME=ib0

# --- MLOPS (opcional): sincroniza codigo si corresponde al flujo del cluster ---
echo "[INFO] Sincronizando codigo desde origin/main..."
git pull --ff-only origin main

IMAGE="nvidia/cuda-quantum:latest-ironman"
TRAIN_SCRIPT="hybrid_monster_train_masivo.py"

if [[ ! -f "$TRAIN_SCRIPT" ]]; then
  echo "[ERROR] No existe $TRAIN_SCRIPT en $(pwd)."
  echo "[ERROR] Crea ese archivo o cambia TRAIN_SCRIPT en este job."
  exit 1
fi

# master_addr: hostname del primer nodo asignado
MASTER_ADDR=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -n 1)
MASTER_PORT=29500

echo "[FUEGO] Iniciando entrenamiento distribuido en ${SLURM_NNODES} nodos x 4 GPUs..."
echo "[INFO] MASTER_ADDR=$MASTER_ADDR MASTER_PORT=$MASTER_PORT"

# Ejecutamos UNA tarea por nodo; torchrun levanta 4 workers locales por nodo.
srun --ntasks="$SLURM_NNODES" --ntasks-per-node=1 \
  --container-image="$IMAGE" \
  --container-mounts=/home/data:/data,/home/models:/models,"$PWD":"$PWD" \
  --container-workdir="$PWD" \
  torchrun \
    --nproc_per_node=4 \
    --nnodes="$SLURM_NNODES" \
    --node_rank="$SLURM_NODEID" \
    --master_addr="$MASTER_ADDR" \
    --master_port="$MASTER_PORT" \
    "$TRAIN_SCRIPT" \
    --epochs 100 \
    --batch_size 1024 \
    --qubits 20 \
    --optimizer quantum_adam \
    --log_wandb true

echo "[EXITO] Job finalizado. Revisa logs/ y /home/models para artefactos."
