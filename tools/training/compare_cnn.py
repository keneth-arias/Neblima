"""Ajustar una red temporal pequeña sobre las mismas ventanas del piloto de Qwen."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn


def read_windows(path):
    with np.load(path, allow_pickle=False) as array:
        ids = array["window_id"]
        history = torch.tensor(array["history"], dtype=torch.float32)
        targets = torch.tensor(array["targets"], dtype=torch.float32)
    center = history.mean(dim=1, keepdim=True)
    scale = history.std(dim=1, correction=0, keepdim=True)
    scale = torch.where(scale > 0, scale, torch.ones_like(scale))
    normalized = (history - center) / scale
    inputs = torch.stack((normalized, torch.ones_like(normalized)), dim=1)
    return ids, inputs, targets, center, scale


def benchmark(train_path, validation_path, steps, batch, seed):
    torch.manual_seed(seed)
    ids, inputs, y, center, scale = read_windows(train_path)
    valid_ids, valid_inputs, valid_y, valid_center, valid_scale = read_windows(validation_path)
    if np.intersect1d(ids, valid_ids).size:
        raise ValueError("Las particiones comparten identificadores")
    batches = len(ids) // batch
    if not batches or steps < 1:
        raise ValueError("Se requiere al menos un lote completo y un paso")
    model = nn.Sequential(
        nn.Conv1d(2, 16, kernel_size=3, padding=1),
        nn.GELU(),
        nn.Conv1d(16, 16, kernel_size=3, padding=1),
        nn.GELU(),
        nn.Flatten(),
        nn.Linear(16 * 24, 6),
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0)
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=steps)
    order = torch.arange(len(ids))
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
        print(json.dumps({"step": cursor + 1, "window_ids": ids[index.numpy()].tolist()}))
    with torch.no_grad():
        predicted = model(valid_inputs) * valid_scale + valid_center
        absolute = (predicted - valid_y).abs()
    return {
        "validation_windows": len(valid_ids),
        "mae": absolute.mean().item(),
        "mae_by_horizon": absolute.mean(dim=0).tolist(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train_path", type=Path)
    parser.add_argument("validation_path", type=Path)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--seed", type=int, default=27)
    print(json.dumps(benchmark(**vars(parser.parse_args()))))
