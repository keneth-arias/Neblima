"""Comparar FP32 y BF16 en el mismo lote de entrenamiento y cronometrar inferencia."""

import argparse
import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from opentslm.forecast import QwenForecaster
from opentslm.forecast_inference import forecast, forecast_batches
from transformers.models.qwen3_5 import modeling_qwen3_5


def probe(weights, data, digest, batch):
    with data.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
            raise ValueError("El archivo difiere de la partición de entrenamiento")
    with np.load(data, allow_pickle=False) as arrays:
        order = torch.randperm(
            len(arrays["window_id"]), generator=torch.Generator().manual_seed(27)
        )
        if batch < 1 or len(order) < 60 * batch:
            raise ValueError("Se requieren 60 lotes completos")
        selected = order[: batch * 60].numpy()
        history = torch.from_numpy(arrays["history"][selected]).float().unsqueeze(-1)
        targets = torch.from_numpy(arrays["targets"][selected]).float().unsqueeze(-1)
    torch.manual_seed(27)
    model = QwenForecaster.from_pretrained(
        checkpoint_path=str(weights), local_files_only=True
    ).cuda()
    model.eval()
    result = {
        "batch": batch,
        "seed": 27,
        "input_sha256": digest,
        "fast_recurrent_kernel_available": bool(modeling_qwen3_5.is_fast_path_available),
    }
    baseline = {}
    for precision in ("fp32", "bf16"):
        args = SimpleNamespace(precision=precision, batch=batch)
        model.zero_grad(set_to_none=True)
        predicted, center, scale = forecast(model, history[:batch].cuda(), args)
        loss = torch.nn.functional.mse_loss(predicted, (targets[:batch].cuda() - center) / scale)
        loss.backward()
        tensors = {
            "predictions": predicted,
            "loss": loss.reshape(1),
            "head_gradient": model.head.weight.grad,
            "projector_gradient": model.project.weight.grad,
            "first_decoder_gradient": model.decoder.layers[0].mlp.down_proj.weight.grad,
            "last_decoder_gradient": model.decoder.layers[-1].mlp.down_proj.weight.grad,
        }
        if precision == "fp32":
            baseline = {
                name: value.detach().float().cpu().clone() for name, value in tensors.items()
            }
        else:
            errors = {}
            for name, value in tensors.items():
                ref = baseline[name]
                norm = torch.linalg.vector_norm(ref)
                if not torch.isfinite(norm) or norm <= 0:
                    raise ValueError(f"Referencia inválida para {name}")
                errors[name] = float(
                    torch.linalg.vector_norm(value.detach().float().cpu() - ref) / norm
                )
            result["bf16_relative_l2"] = errors
            result["bf16_accepted"] = all(
                value <= (0.02 if name in ("loss", "predictions") else 0.05)
                for name, value in errors.items()
            )
        for label, subset in (
            ("warmup", slice(0, 10 * batch)),
            ("measured", slice(10 * batch, None)),
        ):
            actual = targets[subset]
            absolute = torch.zeros(6, dtype=torch.float64, device="cuda")
            torch.cuda.synchronize()
            start = time.monotonic()
            for index, output in forecast_batches(model, history[subset], args, 0, 1, "cuda"):
                absolute += (
                    (output - actual[index].cuda()).abs().sum(dim=(0, 2), dtype=torch.float64)
                )
            torch.cuda.synchronize()
            elapsed = time.monotonic() - start
            if not absolute.isfinite().all():
                raise ValueError("Error no finito durante la medición de inferencia")
            if label == "measured":
                result[f"{precision}_inference_windows_per_second"] = len(actual) / elapsed
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = probe(args.weights, args.data, args.digest, args.batch)
    with args.output.open("x") as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps(report))
