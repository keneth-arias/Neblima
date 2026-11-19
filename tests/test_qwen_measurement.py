"""Verificar la contabilidad de una medición del entrenador."""

import json
from pathlib import Path
from runpy import run_path

import pytest
import yaml

summary = run_path(str(Path(__file__).resolve().parents[1] / "tools/training/measure_qwen.py"))[
    "summarize"
]


def log(tmp_path, steps):
    path = tmp_path / "entrenamiento.log"
    events = [
        {
            "step": step,
            "window_ids": [str(step)],
            "windows_per_second": speed,
            "peak_bytes_per_rank": [[10, 12]],
            "loss": 1.0,
        }
        for step, speed in steps
    ]
    events.append(
        {"checkpoint": "step-00000003", "checkpoint_seconds": 1.0, "checkpoint_bytes": 13}
    )
    path.write_text("\n".join(json.dumps(e) for e in events))
    return path


def test_throughput_uses_elapsed_time_and_excludes_warmup(tmp_path):
    result = summary(log(tmp_path, [(1, 1000), (2, 2), (3, 6)]), 1, 2, 1)
    assert result["compute_windows_per_second"] == pytest.approx(3.0)
    assert result["peak_bytes_per_rank"] == [[10, 12]]
    assert result["measured_windows"] == 2


def test_rejects_incomplete_or_reordered_steps(tmp_path):
    with pytest.raises(ValueError):
        summary(log(tmp_path, [(1, 10), (3, 20)]), 1, 2, 1)


def test_two_rank_announcements_can_share_a_line(tmp_path):
    path = log(tmp_path, [(1, 10), (2, 20), (3, 20)])
    path.write_text('{"rank": 0}{"rank": 1}\n' + path.read_text())
    assert summary(path, 1, 2, 1)["measured_windows"] == 2


def test_frozen_budget_matches_the_measured_cohort_and_release():
    root = Path(__file__).resolve().parents[1]
    policy = yaml.safe_load((root / "configs/training.yaml").read_text())
    fit = yaml.safe_load((root / "configs/training/lima-pm25-fit-v1.yaml").read_text())
    evidence = json.loads((root / "metadata/qwen-calibration.json").read_text())
    training = fit["training"]
    assert training["global_batch"] == evidence["batch"]
    steps, unused = divmod(policy["windows"]["train"], training["global_batch"])
    assert steps == training["updates"] == training["schedule_steps"]
    assert unused == training["incomplete_batch_windows"]
    assert steps * training["global_batch"] == training["windows_seen"]
    assert policy["npz_sha256"]["train"] == evidence["input_sha256"]
    assert fit["trainer_commit"] == evidence["trainer"]
    assert training["precision"] == evidence["precision"]
    assert fit["image"] == evidence["image"]
    assert fit["selection"]["targets"] == policy["windows"]["validation"] * 6
