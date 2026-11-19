"""Ejecutar un paso de Qwen con una tarea de entrenamiento verificada de TimeNet."""

import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import torch
import transformers
from opentslm import forecast

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    args = parser.parse_args()

    fork = Path(forecast.__file__).resolve().parents[2]
    revision = subprocess.check_output(["git", "-C", fork, "rev-parse", "HEAD"], text=True).strip()
    lock = json.loads((ROOT / "configs/upstream.lock.json").read_text())
    if revision != lock["opentslm"]["forecast_fork"]["commit"]:
        raise ValueError("La revisión de la bifurcación difiere de la configuración")
    subprocess.run(
        ["git", "-C", fork, "diff", "--quiet", "HEAD", "--", "src", "environments/forecast"],
        check=True,
    )

    sdk = ROOT / "tools/timenet-smoke"
    window = json.loads(
        subprocess.check_output(
            [
                "uv",
                "run",
                "--offline",
                "--locked",
                "--project",
                sdk,
                "python",
                sdk / "qwen_window.py",
                args.release.resolve(),
            ]
        )
    )
    torch.manual_seed(27)
    model = forecast.QwenForecaster.from_pretrained(local_files_only=True).cuda()
    history = torch.tensor(window.pop("history"), device="cuda", dtype=torch.float32).view(1, 24, 1)
    mask = torch.tensor(window.pop("observed"), device="cuda", dtype=torch.bool).view_as(history)
    original_targets = window.pop("targets")
    target = torch.tensor(original_targets, device="cuda", dtype=torch.float32).view(1, 6, 1)
    center = history.mean()
    dispersion = history.std(correction=0)
    scale = torch.where(dispersion > 0, dispersion, torch.ones_like(dispersion))
    torch.cuda.synchronize()
    start = time.perf_counter()
    step = forecast.smoke_step(model, (history - center) / scale, mask, (target - center) / scale)
    torch.cuda.synchronize()
    seconds = time.perf_counter() - start
    predicted = (
        torch.tensor(step.pop("prediction_before_step")).flatten() * scale.item() + center.item()
    )
    report = {
        **window,
        **step,
        "model": forecast.MODEL_ID,
        "model_revision": forecast.MODEL_REVISION,
        "fork_revision": revision,
        "run_lock_sha256": hashlib.sha256(
            (fork / "environments/forecast/uv.lock").read_bytes()
        ).hexdigest(),
        "python": platform.python_version(),
        "torch": str(torch.__version__),
        "transformers": transformers.__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(),
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "step_seconds": seconds,
        "seed": 27,
        "steps": 1,
        "batch_size": 1,
        "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad),
        "history_mean": center.item(),
        "history_scale": scale.item(),
        "observed_hours": mask.sum().item(),
        "prediction_before_step_ug_m3": predicted.tolist(),
        "target_ug_m3": original_targets,
    }
    print(json.dumps(report, indent=2, allow_nan=False, ensure_ascii=False))


if __name__ == "__main__":
    main()
