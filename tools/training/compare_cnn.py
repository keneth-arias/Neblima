"""Ajustar una red temporal pequeña sobre las mismas ventanas del piloto de Qwen."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import numpy as np
import torch
from torch import nn


def read_history(array):
    ids = array["window_id"]
    history = torch.tensor(array["history"], dtype=torch.float32)
    if (
        ids.ndim != 1
        or not len(ids)
        or len(np.unique(ids)) != len(ids)
        or history.shape != (len(ids), 24)
        or not torch.isfinite(history).all()
    ):
        raise ValueError("Se requieren historias finitas de 24 horas con identificadores únicos")
    center = history.mean(dim=1, keepdim=True)
    scale = history.std(dim=1, correction=0, keepdim=True)
    scale = torch.where(scale > 0, scale, torch.ones_like(scale))
    normalized = (history - center) / scale
    inputs = torch.stack((normalized, torch.ones_like(normalized)), dim=1)
    return ids, inputs, center, scale


def read_windows(path, target_dtype=torch.float32):
    with np.load(path, allow_pickle=False) as data:
        ids, inputs, center, scale = read_history(data)
        targets = torch.tensor(data["targets"], dtype=target_dtype)
    if targets.shape != (len(ids), 6) or not torch.isfinite(targets).all():
        raise ValueError("Se requieren seis objetivos finitos por ventana")
    return ids, inputs, targets, center, scale


def cnn():
    return nn.Sequential(
        nn.Conv1d(2, 16, kernel_size=3, padding=1),
        nn.GELU(),
        nn.Conv1d(16, 16, kernel_size=3, padding=1),
        nn.GELU(),
        nn.Flatten(),
        nn.Linear(16 * 24, 6),
    )


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@torch.no_grad()
def predict(model, inputs, center, scale, batch):
    model.eval()
    chunks = []
    for start in range(0, len(inputs), batch):
        end = start + batch
        chunks.append(model(inputs[start:end]) * scale[start:end] + center[start:end])
    predicted = torch.cat(chunks)
    if not torch.isfinite(predicted).all():
        raise ValueError("La red generó valores no finitos")
    return predicted


def publish_predictions(path, ids, values, digest):
    with NamedTemporaryFile(dir=path.parent) as tmp:
        np.savez(
            tmp,
            window_id=ids,
            forecast_hour=np.arange(1, 7),
            predicted=values.numpy(),
            checkpoint_sha256=digest,
        )
        tmp.flush()
        os.link(tmp.name, path)


def predict_from_checkpoint(checkpoint, windows, output, batch):
    if output.exists():
        raise FileExistsError(output)
    if batch < 1:
        raise ValueError("El tamaño de lote debe ser positivo")
    model = cnn()
    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
    with np.load(windows, allow_pickle=False) as data:
        ids, inputs, center, scale = read_history(data)
    publish_predictions(
        output, ids, predict(model, inputs, center, scale, batch), sha256(checkpoint)
    )


def benchmark(train_path, validation_path, steps, batch, seed, output=None):
    if output is not None and output.exists():
        raise FileExistsError(output)
    if batch < 1:
        raise ValueError("El tamaño de lote debe ser positivo")
    torch.manual_seed(seed)
    ids, inputs, y, center, scale = read_windows(train_path)
    valid_ids, valid_inputs, valid_y, valid_center, valid_scale = read_windows(
        validation_path, torch.float64
    )
    if np.intersect1d(ids, valid_ids).size:
        raise ValueError("Las particiones comparten identificadores")
    batches = len(ids) // batch
    if not batches or steps < 1:
        raise ValueError("Se requiere al menos un lote completo y un paso")
    model = cnn()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0)
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=steps)
    order = torch.arange(len(ids))
    exposure = hashlib.sha256()
    for cursor in range(steps):
        epoch, position = divmod(cursor, batches)
        if position == 0:
            order = torch.randperm(len(ids), generator=torch.Generator().manual_seed(seed + epoch))
        index = order[position * batch : (position + 1) * batch]
        optimizer.zero_grad(set_to_none=True)
        loss = nn.functional.mse_loss(
            model(inputs[index]), (y[index] - center[index]) / scale[index]
        )
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1, error_if_nonfinite=True)
        optimizer.step()
        schedule.step()
        used = ids[index.numpy()].tolist()
        exposure.update(json.dumps(used, separators=(",", ":")).encode() + b"\n")
        print(json.dumps({"step": cursor + 1, "window_ids": used}))
    predicted = predict(model, valid_inputs, valid_center, valid_scale, batch)
    absolute = (predicted.double() - valid_y.double()).abs()
    report = {
        "validation_windows": len(valid_ids),
        "mae": absolute.mean().item(),
        "mae_by_horizon": absolute.mean(dim=0).tolist(),
    }
    if output is not None:
        with TemporaryDirectory(dir=output.parent) as temp:
            folder = Path(temp) / "resultado"
            folder.mkdir()
            weights = folder / "model.pt"
            torch.save(model.state_dict(), weights)
            digest = sha256(weights)
            publish_predictions(folder / "validation.npz", valid_ids, predicted, digest)
            report.update(
                {
                    "seed": seed,
                    "batch": batch,
                    "updates": steps,
                    "windows_seen": steps * batch,
                    "window_order_sha256": exposure.hexdigest(),
                    "torch": str(torch.__version__),
                    "checkpoint_sha256": digest,
                    "predictions_sha256": sha256(folder / "validation.npz"),
                    "train_sha256": sha256(train_path),
                    "validation_sha256": sha256(validation_path),
                }
            )
            (folder / "manifest.json").write_text(
                json.dumps(report, indent=2, allow_nan=False) + "\n"
            )
            folder.rename(output)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train_path", type=Path)
    parser.add_argument("validation_path", type=Path)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--seed", type=int, default=27)
    parser.add_argument("--output", type=Path)
    print(json.dumps(benchmark(**vars(parser.parse_args()))))
