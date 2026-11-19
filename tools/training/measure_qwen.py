"""Medir el entrenador fijado sobre una partición local de entrenamiento."""

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory


def summarize(path: Path, warmup: int, measured: int, batch: int) -> dict:
    steps = []
    checkpoint = None
    decoder = json.JSONDecoder()
    with path.open() as stream:
        for line in stream:
            while line.startswith("{"):
                row, end = decoder.raw_decode(line)
                line = line[end:].lstrip()
                if "windows_per_second" in row:
                    steps.append(row)
                elif "checkpoint_bytes" in row:
                    checkpoint = row
    if [s["step"] for s in steps] != list(range(1, warmup + measured + 1)):
        raise ValueError("Faltan pasos o el registro está desordenado")
    if checkpoint is None or checkpoint["checkpoint"] != f"step-{warmup + measured:08d}":
        raise ValueError("Falta el último punto de control")
    digest = hashlib.sha256()
    for step in steps:
        if (
            len(step["window_ids"]) != batch
            or not math.isfinite(step["loss"])
            or not math.isfinite(step["windows_per_second"])
            or step["windows_per_second"] <= 0
        ):
            raise ValueError("Lote, pérdida o tiempo de paso incorrectos")
        digest.update(json.dumps(step["window_ids"], separators=(",", ":")).encode() + b"\n")
    seconds = sum(batch / s["windows_per_second"] for s in steps[warmup:])
    return {
        "window_order_sha256": digest.hexdigest(),
        "measured_windows": batch * measured,
        "compute_windows_per_second": batch * measured / seconds,
        "peak_bytes_per_rank": steps[-1]["peak_bytes_per_rank"],
        "checkpoint_seconds": checkpoint["checkpoint_seconds"],
        "checkpoint_bytes": checkpoint["checkpoint_bytes"],
    }


def trial(args, repetition, mode, head, devices):
    log = args.output / f"{repetition}-{mode}-{head}.log"
    steps = args.warmup + args.measured
    ranks = 1 if mode in ("single", "pair") else 2
    environment = {**os.environ, "CUDA_VISIBLE_DEVICES": devices, "PYTHONPATH": "/opt/forecast/src"}
    with (
        TemporaryDirectory(prefix=".calibracion-", dir=args.scratch) as scratch,
        log.open("x") as stream,
    ):
        command = [
            sys.executable,
            "-m",
            "torch.distributed.run",
            "--standalone",
            f"--nproc-per-node={ranks}",
            "/opt/forecast/train_qwen_forecast.py",
            "--mode",
            mode if ranks > 1 else "single",
            "--head",
            head,
            "--precision",
            args.precision,
            "--run-dir",
            scratch,
            "--weights",
            str(args.weights),
            "--data",
            str(args.data),
            "--stop-step",
            str(steps),
            "--schedule-steps",
            str(steps),
            "--seed",
            "27",
            "--batch",
            str(args.batch),
            "--save-seconds",
            "86400",
        ]
        if args.lora:
            command.append("--lora")
        started = time.monotonic()
        subprocess.run(
            command, env=environment, stdout=stream, stderr=subprocess.STDOUT, check=True
        )
        elapsed = time.monotonic() - started
    return {
        "head": head,
        "seconds": elapsed,
        **summarize(log, args.warmup, args.measured, args.batch),
    }


def measure(args):
    devices = os.environ.get("CUDA_VISIBLE_DEVICES", "0,1").split(",")
    if len(devices) != 2 or len(set(devices)) != 2 or args.batch % 2 or args.batch < 2:
        raise ValueError("Se requieren dos GPU distintas y un lote divisible entre dos")
    if min(args.warmup, args.measured, args.repeats) < 1:
        raise ValueError("Cada etapa requiere al menos una repetición o un paso")
    with args.data.open("rb") as file:
        if hashlib.file_digest(file, "sha256").hexdigest() != args.sha256:
            raise ValueError("Los datos difieren de la partición de entrenamiento fijada")
    args.output.mkdir(exist_ok=False)
    if args.lora and "fsdp" in args.modes:
        raise ValueError("La adaptación LoRA requiere una GPU o DDP")
    records = []
    modes = args.modes
    order_hash = None
    for repetition in range(args.repeats):
        first = repetition % len(modes)
        for mode in modes[first:] + modes[:first]:
            started = time.monotonic()
            if mode == "pair":
                with ThreadPoolExecutor(max_workers=2) as pool:
                    workers = [
                        pool.submit(trial, args, repetition, mode, head, device)
                        for head, device in zip(("direct", "persistence"), devices, strict=True)
                    ]
                    runs = [w.result() for w in workers]
            else:
                visible = devices[0] if mode == "single" else ",".join(devices)
                runs = [trial(args, repetition, mode, "direct", visible)]
            for run in runs:
                order_hash = order_hash or run["window_order_sha256"]
                if run["window_order_sha256"] != order_hash:
                    raise ValueError("El orden de exposición difiere entre ejecuciones")
            record = {
                "mode": mode,
                "repetition": repetition + 1,
                "seconds": time.monotonic() - started,
                "runs": runs,
            }
            records.append(record)
            print(json.dumps(record), flush=True)
    report = {
        "input_sha256": args.sha256,
        "trainer": os.environ.get("FORECAST_SOURCE_REVISION"),
        "precision": args.precision,
        "lora": args.lora,
        "batch": args.batch,
        "warmup": args.warmup,
        "measured": args.measured,
        "seed": 27,
        "trials": records,
    }
    (args.output / "measurements.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--precision", choices=["fp32", "bf16"], default="fp32")
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["single", "ddp", "fsdp", "pair"],
        default=["single", "ddp", "fsdp", "pair"],
    )
    parser.add_argument("--lora", action="store_true")
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--measured", type=int, default=50)
    parser.add_argument("--repeats", type=int, default=3)
    measure(parser.parse_args())
