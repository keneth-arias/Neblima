"""Probar la selección registrada antes de puntuar los dos pares de semillas."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from airaware.episode_forecast_selection import decide, read_pair

SPEC = yaml.safe_load(
    (
        Path(__file__).resolve().parents[1] / "configs/training/lima-comparacion-cuantiles-v1.yaml"
    ).read_bytes()
)


def pair(seed):
    def metrics(m, h, c, ch):
        return {
            "all": {"targets": 60, "mae": m, "coverage": c},
            "high": {"targets": 10, "mae": h, "coverage": ch},
        }

    return {
        "training_data_sha256": "b" * 64,
        "base_weights_sha256": "c" * 64,
        "model_revision": "rev",
        "seed": seed,
        "direct": metrics(6, 16, 0.90, 0.55),
        "quantile": metrics(5, 14, 0.80, 0.70),
    }


def test_mean_decision_at_frozen_seed_and_tie():
    rows = [pair(28), pair(27)]
    rows[0]["quantile"]["all"]["mae"] = 7  # La media, igual a la directa, cumple el margen.
    answer = decide(SPEC, rows)
    assert answer["selected"] == "quantile" and answer["seed"] == 27
    assert answer["gates"]["global_mae"]
    for row in rows:
        row["quantile"]["high"]["mae"] = row["direct"]["high"]["mae"]
    assert decide(SPEC, rows)["selected"] == "direct"


def test_reject_duplicate_seed_different_cohorts_and_missing_measures():
    with pytest.raises(ValueError, match="semillas"):
        decide(SPEC, [pair(27), pair(27)])
    rows = [pair(27), pair(28)]
    rows[1]["direct"]["high"]["targets"] = 0
    with pytest.raises(ValueError, match="cohorte"):
        decide(SPEC, rows)
    rows[1] = pair(28)
    rows[1]["direct"]["high"]["mae"] = float("nan")
    with pytest.raises(ValueError, match="finita"):
        decide(SPEC, rows)


def test_pair_checks_real_checkpoints_and_training_bundle(tmp_path):
    def save(name, obj):
        path = tmp_path / name
        path.write_text(json.dumps(obj, sort_keys=True))
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    fit_sha = "a" * 64
    ident = {
        "head": "quantile",
        "input_manifest_sha256": fit_sha,
        "data": "b" * 64,
        "weights": "c" * 64,
        "model": "rev",
        "seed": 27,
        "batch": 16,
        "schedule": 14838,
        "world": 1,
        "mode": "single",
        "lora": True,
        "precision": "fp32",
        "validate_at": "final",
        "task_schema": {"lora_rank": 4, "lora_alpha": 8},
    }
    q, qs = save("q.json", {"step": 14838, "identity": ident})
    bundle, bs = save(
        "fit.json",
        {
            "head": "direct",
            "phase": "fit",
            "block": "train",
            "split_sha256": SPEC["blocks_sha256"],
            "point_control_of": fit_sha,
            "files": {
                "quantile-fit.json": fit_sha,
                "quantile-checkpoint.json": qs,
                "data.npz": ident["data"],
            },
        },
    )
    dc = {k: v for k, v in ident.items() if k != "task_schema"}
    dc.update(head="direct", matched_point="complete_epoch_v1", input_manifest_sha256=bs)
    d, ds = save("d.json", {"step": 14838, "identity": dc})
    row = pair(27)
    report = {
        "version": "lima-quantile-comparison-v2",
        "block": "selection",
        "purpose": "historical_replay",
        "manifest_sha256": SPEC["blocks_sha256"],
        "checkpoint_sha256": qs,
        "reference_checkpoint_sha256": ds,
        "overall": row["quantile"],
        "reference_overall": row["direct"],
        "crossed": 0,
    }
    p, _ = save("report.json", report)
    assert read_pair(SPEC, p, q, d, bundle)["seed"] == 27
    dc["data"] = "d" * 64
    d, ds = save("d.json", {"step": 14838, "identity": dc})
    report["reference_checkpoint_sha256"] = ds
    p, _ = save("report.json", report)
    with pytest.raises(ValueError, match="entrenamiento"):
        read_pair(SPEC, p, q, d, bundle)
