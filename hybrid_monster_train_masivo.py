import argparse
import os
from dataclasses import dataclass

import torch
import torch.distributed as dist
import torch.nn as nn
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, Dataset, DistributedSampler

from hybrid_quantum import QTransformerElite, QUBITS


class SyntheticEliteDataset(Dataset):
    def __init__(self, size: int, input_dim: int = 1024, num_classes: int = 10):
        self.x = torch.randn(size, input_dim)
        self.y = torch.randint(0, num_classes, (size,))

    def __len__(self):
        return self.x.shape[0]

    def __getitem__(self, idx):
        return self.x[idx], self.y[idx]


@dataclass
class DistInfo:
    rank: int
    local_rank: int
    world_size: int
    is_main: bool


def parse_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "y"}


def setup_distributed() -> DistInfo:
    rank = int(os.environ.get("RANK", "0"))
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    world_size = int(os.environ.get("WORLD_SIZE", "1"))

    if world_size > 1:
        dist.init_process_group(backend="nccl", init_method="env://")

    if torch.cuda.is_available():
        torch.cuda.set_device(local_rank)

    return DistInfo(
        rank=rank,
        local_rank=local_rank,
        world_size=world_size,
        is_main=(rank == 0),
    )


def cleanup_distributed(world_size: int) -> None:
    if world_size > 1 and dist.is_initialized():
        dist.destroy_process_group()


def maybe_init_wandb(enabled: bool, args, dist_info: DistInfo):
    if not enabled or not dist_info.is_main:
        return None
    try:
        import wandb

        wandb.init(
            project="elite-quantum-transformer",
            config=vars(args),
            name=f"rank0-nodes{os.environ.get('SLURM_NNODES', '1')}-gpus{dist_info.world_size}",
        )
        return wandb
    except Exception as exc:
        print(f"[WARN] W&B no disponible: {exc}")
        return None


def configure_optimizer(model: nn.Module, name: str, lr: float) -> torch.optim.Optimizer:
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    opt_name = name.lower()
    if opt_name in {"quantum_adam", "adam"}:
        return torch.optim.Adam(trainable_params, lr=lr)
    if opt_name == "adamw":
        return torch.optim.AdamW(trainable_params, lr=lr)
    if opt_name == "sgd":
        return torch.optim.SGD(trainable_params, lr=lr, momentum=0.9)
    raise ValueError(f"Optimizador no soportado: {name}")


def evaluate(model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device):
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total_samples = 0
    with torch.no_grad():
        for xb, yb in loader:
            xb = xb.to(device, non_blocking=True)
            yb = yb.to(device, non_blocking=True)
            logits = model(xb)
            loss = criterion(logits, yb)
            total_loss += loss.item() * yb.size(0)
            total_correct += (logits.argmax(dim=1) == yb).sum().item()
            total_samples += yb.size(0)
    return total_loss / max(total_samples, 1), total_correct / max(total_samples, 1)


def main():
    parser = argparse.ArgumentParser(description="Entrenamiento distribuido del QTransformerElite")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--qubits", type=int, default=QUBITS)
    parser.add_argument("--optimizer", type=str, default="quantum_adam")
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--train_samples", type=int, default=8192)
    parser.add_argument("--val_samples", type=int, default=2048)
    parser.add_argument("--log_wandb", type=str, default="false")
    parser.add_argument("--save_path", type=str, default="/home/models/quantum_weights_v1.pt")
    args = parser.parse_args()

    if args.qubits != QUBITS:
        raise ValueError(
            f"--qubits={args.qubits} no coincide con QUBITS={QUBITS} en hybrid_quantum.py"
        )

    dist_info = setup_distributed()
    device = torch.device(
        f"cuda:{dist_info.local_rank}" if torch.cuda.is_available() else "cpu"
    )

    torch.backends.cudnn.benchmark = True

    model = QTransformerElite().to(device)

    # La capa cuántica actual usa sample() con conversion a lista (no diferenciable).
    # Desactivamos gradiente para evitar gasto inútil y warnings de entrenamiento.
    model.q_params.requires_grad_(False)

    if dist_info.world_size > 1:
        model = DDP(model, device_ids=[dist_info.local_rank], output_device=dist_info.local_rank)

    train_ds = SyntheticEliteDataset(size=args.train_samples)
    val_ds = SyntheticEliteDataset(size=args.val_samples)

    train_sampler = (
        DistributedSampler(train_ds, num_replicas=dist_info.world_size, rank=dist_info.rank, shuffle=True)
        if dist_info.world_size > 1
        else None
    )
    val_sampler = (
        DistributedSampler(val_ds, num_replicas=dist_info.world_size, rank=dist_info.rank, shuffle=False)
        if dist_info.world_size > 1
        else None
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        sampler=train_sampler,
        shuffle=(train_sampler is None),
        num_workers=4,
        pin_memory=True,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        sampler=val_sampler,
        shuffle=False,
        num_workers=2,
        pin_memory=True,
    )

    criterion = nn.CrossEntropyLoss()
    wrapped = model.module if isinstance(model, DDP) else model
    optimizer = configure_optimizer(wrapped, args.optimizer, args.lr)
    wandb_mod = maybe_init_wandb(parse_bool(args.log_wandb), args, dist_info)

    if dist_info.is_main:
        print(
            f"[INFO] rank={dist_info.rank} world_size={dist_info.world_size} "
            f"batch_size={args.batch_size} epochs={args.epochs} device={device}"
        )

    for epoch in range(args.epochs):
        if train_sampler is not None:
            train_sampler.set_epoch(epoch)

        model.train()
        running_loss = 0.0
        running_correct = 0
        running_samples = 0

        for xb, yb in train_loader:
            xb = xb.to(device, non_blocking=True)
            yb = yb.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * yb.size(0)
            running_correct += (logits.argmax(dim=1) == yb).sum().item()
            running_samples += yb.size(0)

        train_loss = running_loss / max(running_samples, 1)
        train_acc = running_correct / max(running_samples, 1)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)

        if dist_info.is_main:
            print(
                f"[EPOCH {epoch + 1:03d}] "
                f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
                f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
            )
            if wandb_mod is not None:
                wandb_mod.log(
                    {
                        "epoch": epoch + 1,
                        "train_loss": train_loss,
                        "train_acc": train_acc,
                        "val_loss": val_loss,
                        "val_acc": val_acc,
                    }
                )

    if dist_info.is_main:
        save_dir = os.path.dirname(args.save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        torch.save(wrapped.state_dict(), args.save_path)
        print(f"[EXITO] Pesos guardados en {args.save_path}")
        if wandb_mod is not None:
            wandb_mod.finish()

    cleanup_distributed(dist_info.world_size)


if __name__ == "__main__":
    main()