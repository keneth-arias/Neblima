"""Puntuar una sola cohorte reservada contra persistencia y los criterios prefijados."""

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from episode_calibration import check_file
from episode_quantiles import read_quantiles
from episode_score import scores
from export_senamhi import sha256_file


def metrics(spec, origins, ids, history, y, point, lo, hi, threshold):
    first = datetime.fromisoformat(spec["origin_start_inclusive"])
    dates = [(first + timedelta(days=i)).date().isoformat() for i in range(7)]
    starts = [datetime.fromisoformat(key.split("/", 1)[1]) for key in ids]
    available = np.isfinite(y)
    complete = available.all(axis=1)
    days = {
        day: sum(
            1
            for start, full in zip(starts, complete, strict=True)
            if full and start.date().isoformat() == day
        )
        for day in dates
    }
    table = scores(y, point, lo, hi, np.full(len(y), threshold))
    persistence = np.broadcast_to(history[:, -1:], y.shape)
    err = np.abs(y - persistence)

    def mean(mask):
        return float(err[mask].mean()) if mask.any() else None

    for name, mask in (("all", available), ("high", available & (y >= threshold))):
        table[name]["mae_persistence"] = mean(mask)
        horizons = table["by_horizon" if name == "all" else "high_by_horizon"]
        for h, summary in enumerate(horizons):
            summary["mae_persistence"] = mean(mask & (np.arange(6) == h))
    hours = {starts[i] + timedelta(hours=int(j) + 1) for i, j in np.argwhere(available)}
    mae = table["all"]["mae"]
    coverage = table["all"]["coverage"]
    lower, upper = spec["global_coverage_range"]
    checks = {
        "lower_mae_than_persistence": None
        if mae is None
        else mae < table["all"]["mae_persistence"],
        "coverage_in_band": None if coverage is None else lower <= coverage <= upper,
    }
    if not all(days.values()):
        decision = "inconclusive"
    else:
        decision = spec["pass_action"] if all(checks.values()) else spec["fail_action"]
    return {
        "scheduled_origins": len(origins),
        "eligible_histories": len(ids),
        "distinct_observed_target_hours": len(hours),
        "complete_origins_by_date": days,
        "concentration": table,
        "gates": checks,
        "decision": decision,
    }


def score(
    protocol,
    protocol_sha,
    seal,
    seal_sha,
    cohort,
    cohort_sha,
    thresholds,
    calibration,
    output,
    *,
    tracking=None,
    now=None,
):
    def read(path, digest):
        return json.loads(check_file(path, digest).read_bytes())

    spec = read(protocol, protocol_sha)
    release = read(seal, seal_sha)
    vintage = datetime.fromisoformat(spec["observation_vintage_utc"])
    if (now or datetime.now(UTC)) < vintage:
        raise ValueError("El periodo reservado todavía está abierto")
    rec = read(cohort / "receipt.json", cohort_sha)
    if (
        spec["version"] != "lima-prueba-futura-campo-marte-v1"
        or spec["scope"] != "retrospective_concentration_only"
        or spec["baseline"] != "repeat_last_history_value"
        or spec["sparse_result"] != "inconclusive_if_any_origin_date_has_no_complete_scored_window"
        or spec["require_lower_mae_than_persistence"] is not True
        or release["version"] != "lima-concentracion-prueba-congelada-v1"
        or release["head"] not in ("direct", "quantile")
        or datetime.fromisoformat(release["sealed_at_utc"])
        >= datetime.fromisoformat(spec["seal_before_utc"])
        or release["scope"] != spec["scope"]
        or release["protocol_sha256"] != protocol_sha
        or release["thresholds_sha256"] != spec["thresholds_sha256"]
        or release["image"] != spec["image"]
        or rec["version"] != "lima-cohorte-campo-marte-v1"
        or rec["seal_sha256"] != seal_sha
        or rec["protocol_sha256"] != protocol_sha
        or datetime.fromisoformat(rec["observation_vintage_utc"])
        != datetime.fromisoformat(spec["observation_vintage_utc"])
    ):
        raise ValueError("La cohorte, la regla o el sello difieren del protocolo")
    head = release["head"]
    bundle_sha = rec["files"]["infer/manifest.json"]
    bundle = read(cohort / "infer/manifest.json", bundle_sha)
    if (
        (bundle["schema"], bundle["phase"], bundle["head"], bundle["block"], bundle["unit"])
        != ("forecast-input-v1", "infer", head, "external_test", "ug/m3")
        or bundle["checkpoint_sha256"] != release["checkpoint_sha256"]
        or bundle["weights_manifest_sha256"] != release["base_weights_sha256"]
        or bundle["seal_sha256"] != seal_sha
    ):
        raise ValueError("La inferencia no corresponde al modelo o a la cohorte")
    limits = read(thresholds, spec["thresholds_sha256"])
    threshold = limits["stations"][spec["historical_station_key"]]
    if limits["unit"] != spec["unit"] or not np.isfinite(threshold):
        raise ValueError("Umbral de concentración inválido")
    origins = read(cohort / "scoring/origins.json", rec["files"]["scoring/origins.json"])
    start = datetime.fromisoformat(spec["origin_start_inclusive"])
    expected = [
        f"{spec['station_code']}/{(start + timedelta(hours=i)).isoformat()}" for i in range(168)
    ]
    if [r["window_id"] for r in origins] != expected:
        raise ValueError("La cohorte debe inventariar todos los orígenes fijados")
    ids = np.asarray([r["window_id"] for r in origins if r["eligible"]], dtype=str)
    data_sha = bundle["files"]["data.npz"]
    with np.load(check_file(cohort / "infer/data.npz", data_sha), allow_pickle=False) as data:
        if set(data.files) != {"window_id", "history"} or not np.array_equal(
            data["window_id"], ids
        ):
            raise ValueError("Las historias difieren de los orígenes elegibles")
        history = data["history"]
    with np.load(
        check_file(cohort / "scoring/observed.npz", rec["files"]["scoring/observed.npz"]),
        allow_pickle=False,
    ) as data:
        if not np.array_equal(data["window_id"], ids):
            raise ValueError("Los objetivos difieren de las historias")
        y = data["observed"]
    if (
        history.shape != (len(ids), 24)
        or not np.isfinite(history).all()
        or y.shape != (len(ids), 6)
        or np.isinf(y).any()
    ):
        raise ValueError("Ventanas de prueba incompatibles")
    output_sha = intent_sha = receipt_sha = tracked_sha = run_id = None
    if len(ids):
        if output is None:
            raise ValueError("Se requiere la salida original de inferencia")
        step = "step-00014838"
        intent_path = output / f".infer-{step}.intent.json"
        intent_sha = sha256_file(intent_path)
        intent = read(intent_path, intent_sha)
        if (
            intent["phase"],
            intent["head"],
            intent["bundle_sha256"],
            intent["image"],
            intent["step"],
        ) != ("infer", head, bundle_sha, release["image"], 14838):
            raise ValueError("El trabajo publicado corresponde a otra inferencia")
        receipt_path = output / f".infer-{step}.receipt.json"
        receipt_sha = sha256_file(receipt_path)
        output_sha = read(receipt_path, receipt_sha)
        pred = check_file(output / f"predictions-{step}.npz", output_sha)
        if tracking is None:
            raise ValueError("Se requiere el registro independiente de MLflow")
        tracked_path, tracked_sha = tracking
        run = read(tracked_path, tracked_sha)["run"]
        params = {row["key"]: row["value"] for row in run["data"]["params"]}
        tags = {row["key"]: row["value"] for row in run["data"]["tags"]}
        run_id = run["info"]["run_id"]
        keys = ("phase", "head", "bundle_sha256", "image", "step", "seed", "run_id")
        if (
            run["info"]["status"] != "FINISHED"
            or not run_id
            or intent["seed"] != release["seed"]
            or any(params.get(k) != str(intent[k]) for k in keys)
            or tags.get("artifact_sha256") != output_sha
            or tags.get("checkpoint_sha256") != release["checkpoint_sha256"]
        ):
            raise ValueError("MLflow no vincula esta salida con la inferencia congelada")
        with np.load(pred, allow_pickle=False) as data:
            if (
                data["checkpoint_sha256"].item() != release["checkpoint_sha256"]
                or not np.array_equal(data["window_id"], ids)
                or not np.array_equal(data["forecast_hour"], np.arange(1, 7))
            ):
                raise ValueError("La salida difiere del punto de control o de los orígenes")
            point = data["predicted"]
            if head == "quantile" and (
                data["input_sha256"].item() != data_sha
                or data["model_revision"].item() != release["model_revision"]
            ):
                raise ValueError("Los cuantiles proceden de otra matriz o versión de Qwen")
        if head == "quantile":
            q, _ = read_quantiles(pred, output_sha, ids, bundle_sha)
            lo, hi = np.maximum(0.0, q[:, :, 0]), np.maximum(0.0, q[:, :, 2])
        elif head == "direct":
            cal = read(calibration, release["direct_calibrator_sha256"])
            if cal["checkpoint_sha256"] != release["checkpoint_sha256"]:
                raise ValueError("Se requiere el calibrador del modelo directo")
            residuals = np.asarray(cal["residual_q10_q90"])
            if (
                residuals.shape != (2, 6)
                or not np.isfinite(residuals).all()
                or (residuals[0] > residuals[1]).any()
            ):
                raise ValueError("Los residuos del calibrador deben estar ordenados y ser finitos")
            lower, upper = residuals
            lo, hi = np.maximum(0.0, point + lower), np.maximum(0.0, point + upper)
        else:
            raise ValueError("Cabezal de concentración desconocido")
    else:
        point = lo = hi = np.empty((0, 6), dtype=float)
    report = metrics(spec, origins, ids, history, y, point, lo, hi, threshold)
    return {
        **report,
        "version": "lima-puntuacion-campo-marte-v1",
        "unit": spec["unit"],
        "station": spec["station_code"],
        "head": head,
        "protocol_sha256": protocol_sha,
        "seal_sha256": seal_sha,
        "cohort_sha256": cohort_sha,
        "infer_manifest_sha256": bundle_sha,
        "predictions_sha256": output_sha,
        "mlflow_run_id": run_id,
        "mlflow_record_sha256": tracked_sha,
        "worker_intent_sha256": intent_sha,
        "worker_receipt_sha256": receipt_sha,
        "checkpoint_sha256": release["checkpoint_sha256"],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("protocol", "seal", "cohort", "thresholds", "calibrator", "report"):
        p.add_argument(arg, type=Path)
    for arg in ("protocol", "seal", "cohort"):
        p.add_argument(f"--{arg}-sha256", required=True)
    p.add_argument("--worker-output", type=Path)
    p.add_argument("--mlflow-record", nargs=2, metavar=("ARCHIVO", "SHA256"))
    a = p.parse_args()
    result = score(
        a.protocol,
        a.protocol_sha256,
        a.seal,
        a.seal_sha256,
        a.cohort,
        a.cohort_sha256,
        a.thresholds,
        a.calibrator,
        a.worker_output,
        tracking=(Path(a.mlflow_record[0]), a.mlflow_record[1]) if a.mlflow_record else None,
    )
    with NamedTemporaryFile(dir=a.report.parent) as tmp:
        tmp.write((json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n").encode())
        tmp.flush()
        os.link(tmp.name, a.report)
    print(sha256_file(a.report))
