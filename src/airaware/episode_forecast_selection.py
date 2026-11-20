"""Elegir el pronóstico de concentraciones en selección con dos semillas pareadas."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import mean
from tempfile import NamedTemporaryFile

import yaml


def read_pair(spec, report_path, quantile_checkpoint, direct_checkpoint, direct_bundle):
    def load(path):
        raw = path.read_bytes()
        return json.loads(raw), hashlib.sha256(raw).hexdigest()

    r, report_sha = load(report_path)
    q, q_sha = load(quantile_checkpoint)
    d, d_sha = load(direct_checkpoint)
    bundle, bundle_sha = load(direct_bundle)
    if (
        r["version"] != "lima-quantile-comparison-v2"
        or r["block"] != "selection"
        or r["purpose"] != "historical_replay"
        or r["manifest_sha256"] != spec["blocks_sha256"]
        or r["checkpoint_sha256"] != q_sha
        or r["reference_checkpoint_sha256"] != d_sha
        or r["crossed"] != 0
    ):
        raise ValueError("La comparación no corresponde a los puntos de control y a la selección")
    quantile, direct = q["identity"], d["identity"]
    common = {
        "world": 1,
        "mode": "single",
        "precision": "fp32",
        "lora": True,
        "validate_at": "final",
        "batch": spec["batch"],
        "schedule": spec["optimizer_steps"],
    }
    if (
        q["step"] != common["schedule"]
        or d["step"] != common["schedule"]
        or any(quantile.get(k) != v or direct.get(k) != v for k, v in common.items())
        or any(quantile[k] != direct[k] for k in ("data", "seed", "weights", "model"))
        or quantile["head"] != "quantile"
        or direct["head"] != "direct"
        or quantile["task_schema"]["lora_rank"] != 4
        or quantile["task_schema"]["lora_alpha"] != 8
        or direct.get("matched_point") != "complete_epoch_v1"
        or direct["input_manifest_sha256"] != bundle_sha
        or (bundle["head"], bundle["phase"], bundle["block"]) != ("direct", "fit", "train")
        or bundle["split_sha256"] != spec["blocks_sha256"]
        or bundle["files"]["data.npz"] != direct["data"]
        or bundle["point_control_of"] != quantile["input_manifest_sha256"]
        or bundle["files"]["quantile-fit.json"] != bundle["point_control_of"]
        or bundle["files"]["quantile-checkpoint.json"] != q_sha
    ):
        raise ValueError("Los puntos de control difieren de la receta de entrenamiento pareada")
    return {
        "seed": quantile["seed"],
        "report_sha256": report_sha,
        "quantile_checkpoint_sha256": q_sha,
        "direct_checkpoint_sha256": d_sha,
        "training_data_sha256": direct["data"],
        "base_weights_sha256": direct["weights"],
        "model_revision": direct["model"],
        "direct_bundle_sha256": bundle_sha,
        "direct": {s: r["reference_overall"][s] for s in ("all", "high")},
        "quantile": {s: r["overall"][s] for s in ("all", "high")},
    }


def decide(spec, pairs):
    if (
        spec["version"] != "lima-comparacion-cuantiles-v1"
        or spec["scope"] != "retrospective_selection"
        or spec["tie"] != "retain_direct"
        or spec["epochs"] != 1
        or not spec["include_final_partial_batch"]
        or not spec["high_mae_must_improve"]
        or not spec["high_coverage_error_must_decrease"]
        or spec["test_policy"] != "new_unseen_station_hours_required_before_pilot"
    ):
        raise ValueError("Regla de elección desconocida")
    expected = sorted(spec["seeds"])
    if (
        len(set(expected)) != 2
        or len(expected) != 2
        or sorted(p["seed"] for p in pairs) != expected
        or spec["deployable_seed_if_qualified"] not in expected
    ):
        raise ValueError("Se requieren las dos semillas pareadas preinscritas")
    for key in ("training_data_sha256", "base_weights_sha256", "model_revision"):
        if len({p[key] for p in pairs}) != 1:
            raise ValueError("Las semillas corresponden a otro entrenamiento")
    methods = ("direct", "quantile")
    for stratum in ("all", "high"):
        cohorts = [p[m][stratum] for p in pairs for m in methods]
        if len({r["targets"] for r in cohorts}) != 1 or cohorts[0]["targets"] < 1:
            raise ValueError("La cohorte pareada debe tener observaciones en cada estrato")
        if any(
            not all(
                isinstance(r[k], (int, float)) and math.isfinite(r[k]) for k in ("mae", "coverage")
            )
            or r["mae"] < 0
            or not 0 <= r["coverage"] <= 1
            for r in cohorts
        ):
            raise ValueError("Se requiere una medida finita y válida por semilla y estrato")
    means = {
        method: {
            s: {k: mean(p[method][s][k] for p in pairs) for k in ("mae", "coverage")}
            for s in ("all", "high")
        }
        for method in methods
    }
    q, d = means["quantile"], means["direct"]
    nominal = spec["nominal_hourly_coverage"]
    gates = {
        "global_mae": q["all"]["mae"] - d["all"]["mae"] <= spec["global_mae_max_increase_ug_m3"],
        "high_mae": q["high"]["mae"] < d["high"]["mae"],
        "global_coverage": nominal - spec["global_coverage_absolute_tolerance"]
        <= q["all"]["coverage"]
        <= nominal + spec["global_coverage_absolute_tolerance"],
        "high_coverage": abs(q["high"]["coverage"] - nominal)
        < abs(d["high"]["coverage"] - nominal),
    }
    return {
        "version": "lima-eleccion-concentracion-v1",
        "scope": spec["scope"],
        "selected": "quantile" if all(gates.values()) else "direct",
        "seed": spec["deployable_seed_if_qualified"],
        "gates": gates,
        "means": means,
        "seeds": sorted(pairs, key=lambda p: p["seed"]),
        "test_policy": spec["test_policy"],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("rule", type=Path)
    p.add_argument("rule_sha256")
    p.add_argument("output", type=Path)
    p.add_argument(
        "--pair",
        nargs=4,
        action="append",
        required=True,
        type=Path,
        metavar=("INFORME", "CUANTILES", "DIRECTO", "PAQUETE_DIRECTO"),
    )
    a = p.parse_args()
    raw = a.rule.read_bytes()
    if hashlib.sha256(raw).hexdigest() != a.rule_sha256:
        p.error("La huella de la regla preinscrita difiere")
    config = yaml.safe_load(raw)
    result = decide(config, [read_pair(config, *pair) for pair in a.pair])
    result["rule_sha256"] = a.rule_sha256
    result["blocks_sha256"] = config["blocks_sha256"]
    with NamedTemporaryFile(dir=a.output.parent) as tmp:
        tmp.write((json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n").encode())
        tmp.flush()
        os.link(tmp.name, a.output)
