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


def checkpoint_pair(tmp_path, seed=27, high_mae=14):
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
        "seed": seed,
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
    row = pair(seed)
    row["quantile"]["high"]["mae"] = high_mae
    calibrator, cs = save(
        "calibrator.json",
        {
            "version": "pm25-six-hour-calibration-v1",
            "unit": "ug/m3",
            "manifest_sha256": SPEC["blocks_sha256"],
            "checkpoint_sha256": ds,
            "thresholds_sha256": "60767fb660521ecbd392cd0fd8f455f8941f97cae30108da2c3936db0d76fecd",
            "residual_q10_q90": [[-1] * 6, [2] * 6],
        },
    )
    report = {
        "reference_calibrator_sha256": cs,
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
    return (p, q, d, bundle), calibrator


def test_pair_checks_real_checkpoints_and_training_bundle(tmp_path):
    paths, _ = checkpoint_pair(tmp_path)
    assert read_pair(SPEC, *paths)["seed"] == 27
    p, _, d, _ = paths
    direct = json.loads(d.read_bytes())
    direct["identity"]["data"] = "d" * 64
    d.write_text(json.dumps(direct))
    report = json.loads(p.read_bytes())
    report["reference_checkpoint_sha256"] = hashlib.sha256(d.read_bytes()).hexdigest()
    p.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="entrenamiento"):
        read_pair(SPEC, *paths)


@pytest.mark.parametrize(("high_mae", "head"), [(14, "quantile"), (16, "direct")])
def test_freeze_verified_pairs_and_matching_intervals(tmp_path, high_mae, head):
    from airaware.holdout_release import bind

    folder = Path(__file__).resolve().parents[1] / "configs/training"
    protocol = folder / "lima-prueba-futura-campo-marte-v1.json"
    rule = folder / "lima-comparacion-cuantiles-v1.yaml"
    paths = []
    for seed in (28, 27):
        root = tmp_path / str(seed)
        root.mkdir()
        pair_paths, _ = checkpoint_pair(root, seed, high_mae)
        paths.append(pair_paths)

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    rows = [read_pair(SPEC, *p) for p in paths]
    decision = decide(SPEC, rows)
    decision.update(rule_sha256=digest(rule), blocks_sha256=SPEC["blocks_sha256"])
    receipt = tmp_path / "decision.json"
    receipt.write_text(json.dumps(decision))

    def freeze():
        return bind(protocol, digest(protocol), rule, receipt, digest(receipt), paths, calibrator)

    calibrator = tmp_path / "27" / "calibrator.json"
    binding, deadline = freeze()
    assert binding["checkpoint_sha256"] == rows[1][head + "_checkpoint_sha256"]
    assert binding["head"] == head and binding["seed"] == 27
    assert binding["protocol_sha256"] == digest(protocol)
    assert binding["direct_calibrator_sha256"] == digest(calibrator)
    assert deadline.isoformat() == "2026-11-22T00:00:00+00:00"
    calibrator = tmp_path / "28" / "calibrator.json"
    with pytest.raises(ValueError, match="huella"):
        freeze()
    calibrator = tmp_path / "27" / "calibrator.json"
    receipt.write_text(json.dumps({**decision, "seed": 28}))
    with pytest.raises(ValueError, match="selección registrada"):
        freeze()


def test_seal_is_once_only_and_checks_actual_time(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from datetime import UTC, datetime, timedelta

    from airaware.holdout_release import publish

    path = tmp_path / "sello.json"
    binding = {"version": "fixture", "head": "direct"}
    now = datetime.now(UTC)
    deadline = now + timedelta(hours=1)
    with pytest.raises(ValueError, match="plazo"):
        publish(path, binding, now)
    assert not path.exists()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: publish(path, binding, deadline), range(8)))
    assert [json.loads(path.read_text())] * 8 == results
    assert now <= datetime.fromisoformat(results[0]["sealed_at_utc"]) < deadline
    with pytest.raises(ValueError, match="otra versión"):
        publish(path, {**binding, "head": "quantile"}, deadline)
