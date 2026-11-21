"""Puntuar los dos pares congelados de pronósticos directos de PM2.5."""

import argparse
import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from direct_cohorts import PROTOCOL, membership
from episode_calibration import align, check_file
from export_senamhi import sha256_file
from paired_forecasts import HOURS, ordered_ids

SEEDS = ("27", "28")
CONTROL = "normalized-mse"
CANDIDATE = "physical-mae"
OBJECTIVES = (CONTROL, CANDIDATE)
HISTORICAL_USE = "all_roles_previously_used_for_historical_training"


def block_interval(hours, high, differences, size):
    """Remuestrear bloques observados compartidos, ponderando cada par por igual."""
    keys, groups = np.unique((hours // size).ravel(), return_inverse=True)
    groups = groups.ravel()[high.ravel()]
    counts = np.bincount(groups, minlength=len(keys))
    support = int(np.count_nonzero(counts))
    report = {
        "blocks": len(keys),
        "high_blocks": support,
        "accepted": 0,
        "discarded": 0,
        "ci95": None,
    }
    if support < 4:
        return report
    sums = np.array(
        [np.bincount(groups, weights=delta[high], minlength=len(keys)) for delta in differences]
    )
    draws = []
    rng = np.random.default_rng(27)
    while len(draws) < 2000:
        indices = rng.integers(len(keys), size=(2000 - len(draws), len(keys)))
        pairs = counts[indices].sum(axis=1)
        valid = pairs > 0
        report["discarded"] += int((~valid).sum())
        per_seed = sums[:, indices[valid]].sum(axis=2) / pairs[valid]
        draws.extend(per_seed.mean(axis=0))
    report.update(
        accepted=len(draws), ci95=np.quantile(draws, [0.025, 0.975], method="linear").tolist()
    )
    return report


def metrics(errors, high):
    absolute = np.abs(errors)
    return {
        "mae": float(absolute.mean()),
        "high_mae": float(absolute[high].mean()) if high.any() else None,
        "mae_by_horizon": absolute.mean(axis=0).tolist(),
        "signed_error_by_horizon": errors.mean(axis=0).tolist(),
    }


def evaluate(origins, stations, history, targets, high, predictions):
    hours = origins[:, None] + HOURS
    sites = np.broadcast_to(stations[:, None], hours.shape)
    seeds = {}
    differences = []
    for seed in SEEDS:
        control = predictions[seed][CONTROL] - targets
        candidate = predictions[seed][CANDIDATE] - targets
        seeds[seed] = {CONTROL: metrics(control, high), CANDIDATE: metrics(candidate, high)}
        differences.append(np.abs(control) - np.abs(candidate))
    delta = np.array(differences)
    high_gain = float(delta[:, high].mean(axis=1).mean()) if high.any() else None
    global_gain = float(delta.mean(axis=(1, 2)).mean())
    blocks = {str(size): block_interval(hours, high, delta, size) for size in (84, 168, 336)}
    ci = blocks["168"]["ci95"]
    if ci is None:
        decision = "inconclusive"
    elif high_gain <= 0 or global_gain < 0:
        decision = "retain_control"
    elif ci[0] > 0:
        decision = "advance_to_calibration"
    else:
        decision = "inconclusive"
    return {
        "decision": decision,
        "windows": len(origins),
        "pairs": targets.size,
        "station_hours": len(set(zip(sites.ravel(), hours.ravel(), strict=True))),
        "high_station_hours": len(set(zip(sites[high], hours[high], strict=True))),
        "high_pairs": int(high.sum()),
        "global_improvement": global_gain,
        "high_improvement": high_gain,
        "seeds": seeds,
        "persistence": metrics(history[:, -1:] - targets, high),
        "blocks": blocks,
    }


def checked_matrix(values, shape):
    if values.shape != shape or values.dtype.kind not in "ifu" or not np.isfinite(values).all():
        raise ValueError("Se requiere una matriz numérica finita con las dimensiones previstas")
    return values.astype(np.float64, copy=False)


def read_cohort(folder, digest, protocol_path):
    protocol = json.loads(protocol_path.read_bytes())
    spec = json.loads(check_file(folder / "manifest.json", digest).read_bytes())
    expected = {
        "schema": "forecast-direct-cohort-v1",
        "unit": "ug/m3",
        "phase": "confirmation",
        "head": "direct",
        "historical_use": HISTORICAL_USE,
        "protocol_sha256": sha256_file(protocol_path),
        "source_manifest_sha256": protocol["source_manifest_sha256"],
        "weights_manifest_sha256": protocol["weights_manifest_sha256"],
        **protocol["cohorts"]["confirmation"],
    }
    if protocol["version"] != "lima-directo-cohortes-v1" or any(
        spec.get(k) != v for k, v in expected.items()
    ):
        raise ValueError("El rol o la procedencia de confirmación difiere del protocolo")
    files = spec["files"]
    thresholds = json.loads(
        check_file(folder / "thresholds.json", files["thresholds.json"]).read_bytes()
    )
    if (
        thresholds["fit_ids_sha256"] != protocol["cohorts"]["fit"]["ids_sha256"]
        or thresholds["method"] != "linear_p95_unique_fit_history_station_hours"
        or thresholds["unit"] != "ug/m3"
    ):
        raise ValueError("Los umbrales deben provenir del ajuste congelado")
    with np.load(check_file(folder / "data.npz", files["data.npz"]), allow_pickle=False) as data:
        ids, order = ordered_ids(data["window_id"])
        if membership(ids) != protocol["cohorts"]["confirmation"]:
            raise ValueError("Las ventanas difieren de la confirmación congelada")
        history = checked_matrix(data["history"], (len(ids), 24))[order]
        targets = checked_matrix(data["targets"], (len(ids), 6))[order]
        stations, origins = data["station_key"], data["origin_hour"]
        if (
            origins.dtype.kind != "i"
            or stations.dtype.kind != "U"
            or origins.shape != ids.shape
            or stations.shape != ids.shape
            or np.any(stations == "")
            or len(set(zip(stations, origins, strict=True))) != len(ids)
        ):
            raise ValueError("Estación u hora de origen inválida")
        stations, origins = stations[order], origins[order]
    limits = checked_matrix(
        np.array([thresholds["stations"][station] for station in stations]), (len(ids),)
    )
    return ids, origins, stations, history, targets, targets >= limits[:, None]


def require_pairs(mapping):
    if set(mapping) != set(SEEDS) or any(set(mapping[s]) != set(OBJECTIVES) for s in SEEDS):
        raise ValueError("Se requieren los dos objetivos de las semillas 27 y 28")


def score(
    selection_path,
    selection_sha,
    inventory_path,
    inventory_sha,
    cohort,
    output,
    *,
    protocol_path=PROTOCOL,
):
    if output.exists():
        raise FileExistsError(output)
    selection = json.loads(check_file(selection_path, selection_sha).read_bytes())
    inventory = json.loads(check_file(inventory_path, inventory_sha).read_bytes())
    if (
        selection["schema"] != "direct-confirmation-selection-v1"
        or inventory["schema"] != "direct-confirmation-predictions-v1"
    ):
        raise ValueError("Esquema desconocido de selección o inferencia")
    checkpoints = selection["checkpoints"]
    require_pairs(checkpoints)
    require_pairs(inventory["arms"])
    digests = [checkpoints[s][o] for s in SEEDS for o in OBJECTIVES]
    if (
        any(not isinstance(d, str) or not re.fullmatch("[0-9a-f]{64}", d) for d in digests)
        or len(set(digests)) != 4
    ):
        raise ValueError("Se requieren cuatro checkpoints distintos congelados por su huella")
    cohort_sha = selection["confirmation_manifest_sha256"]
    ids, origins, stations, history, targets, high = read_cohort(cohort, cohort_sha, protocol_path)
    folder = inventory_path.parent
    history_sha = sha256_file(folder / "history.npz")
    with np.load(folder / "history.npz", allow_pickle=False) as archive:
        if set(archive.files) != {"window_id", "history"} or not np.array_equal(
            align(archive, ids, "history"), history
        ):
            raise ValueError(
                "El insumo de inferencia debe contener solo las historias de confirmación"
            )
    predictions = {}
    for seed in SEEDS:
        predictions[seed] = {}
        for objective in OBJECTIVES:
            receipt = inventory["arms"][seed][objective]
            if receipt["history_sha256"] != history_sha:
                raise ValueError("La inferencia usó otro archivo de historias")
            path = check_file(folder / f"{seed}-{objective}.npz", receipt["output_sha256"])
            with np.load(path, allow_pickle=False) as archive:
                if (
                    set(archive.files)
                    != {"checkpoint_sha256", "window_id", "forecast_hour", "predicted"}
                    or archive["checkpoint_sha256"].shape != ()
                    or archive["checkpoint_sha256"].item() != checkpoints[seed][objective]
                    or not np.array_equal(archive["forecast_hour"], HOURS)
                ):
                    raise ValueError(
                        "El checkpoint, el tipo de salida o los horizontes difieren de la selección"
                    )
                predictions[seed][objective] = checked_matrix(
                    align(archive, ids, "predicted"), (len(ids), 6)
                )
    report = {
        "schema": "direct-confirmation-score-v1",
        "unit": "ug/m3",
        "historical_use": HISTORICAL_USE,
        "selection_sha256": selection_sha,
        "inventory_sha256": inventory_sha,
        "confirmation_manifest_sha256": cohort_sha,
        "checkpoints": checkpoints,
        **evaluate(origins, stations, history, targets, high, predictions),
    }
    # El enlace publica el informe completo sin reemplazar una decisión concurrente.
    with NamedTemporaryFile(dir=output.parent, mode="w", encoding="utf-8") as tmp:
        json.dump(report, tmp, allow_nan=False, sort_keys=True, indent=2)
        tmp.write("\n")
        tmp.flush()
        os.fsync(tmp.fileno())
        os.link(tmp.name, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "selection", type=Path, help="Selección congelada antes de abrir confirmación"
    )
    parser.add_argument("inventory", type=Path, help="Registro privado de las cuatro inferencias")
    parser.add_argument("cohort", type=Path, help="Carpeta scorer/confirmation del exportador")
    parser.add_argument("output", type=Path, help="Archivo de informe nuevo")
    parser.add_argument("--selection-sha256", required=True)
    parser.add_argument("--inventory-sha256", required=True)
    args = parser.parse_args()
    score(
        args.selection,
        args.selection_sha256,
        args.inventory,
        args.inventory_sha256,
        args.cohort,
        args.output,
    )
