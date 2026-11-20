"""Comparar los cuantiles de Qwen con el pronóstico directo en la misma selección."""

import argparse
import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from episode_calibration import align, check_file, verify_candidate_bundle
from episode_score import block_difference, scores
from paired_forecasts import ordered_ids


def read_quantiles(path, digest, ids, manifest_sha):
    with np.load(check_file(path, digest), allow_pickle=False) as z:
        if (
            z["unit"].item() != "ug/m3"
            or z["task"].item() != "quantile"
            or z["schema_version"].item() != 2
            or z["input_manifest_sha256"].item() != manifest_sha
            or not np.array_equal(z["levels"], [0.1, 0.5, 0.9])
            or not np.array_equal(z["forecast_hour"], np.arange(1, 7))
        ):
            raise ValueError("Esquema de cuantiles o procedencia incompatibles")
        q = align(z, ids, "quantiles")
        if (
            q.shape != (len(ids), 6, 3)
            or not np.isfinite(q).all()
            or np.any(np.diff(q, axis=-1) < 0)
            or not np.array_equal(q[:, :, 1], align(z, ids, "predicted"))
        ):
            raise ValueError("Cuantiles con cruce, valor no finito o mediana incompatible")
        checkpoint = z["checkpoint_sha256"].item()
        if not isinstance(checkpoint, str) or not re.fullmatch("[a-f0-9]{64}", checkpoint):
            raise ValueError("Huella de punto de control inválida")
        return q, checkpoint


def compare(
    blocks,
    manifest_sha,
    candidate,
    candidate_sha,
    input_manifest_sha,
    reference,
    reference_sha,
    input_manifest,
):
    from episode_blocks import VERSION

    m = json.loads(check_file(blocks / "manifest.json", manifest_sha).read_text())
    if m["version"] != VERSION or m["unit"] != "ug/m3":
        raise ValueError("Particiones incompatibles")
    folder = blocks / "selection"
    files = m["blocks"]["selection"]["files"]

    def block(name):
        return np.load(check_file(folder / name, files[name]), allow_pickle=False)

    with block("index.npz") as idx:
        ids, order = ordered_ids(idx["window_id"])
        stations, hours = idx["station_key"][order], idx["origin_hour"][order]
    with block("observed.npz") as z:
        y = align(z, ids, "targets")
    thresholds = json.loads(
        check_file(blocks / "thresholds.json", m["thresholds_sha256"]).read_text()
    )
    limits = np.array([thresholds["stations"].get(s, np.nan) for s in stations])
    archive_sha = verify_candidate_bundle(
        blocks, "selection", manifest_sha, m, input_manifest, input_manifest_sha, "quantile", ids
    )
    with np.load(check_file(candidate, candidate_sha), allow_pickle=False) as raw:
        if raw["input_sha256"].item() != archive_sha:
            raise ValueError("Los cuantiles proceden de otras historias")
    q, checkpoint = read_quantiles(candidate, candidate_sha, ids, input_manifest_sha)
    with np.load(check_file(reference, reference_sha), allow_pickle=False) as z:
        if z["manifest_sha256"].item() != manifest_sha or z["block"].item() != "selection":
            raise ValueError("La referencia procede de otra selección")
        reference_checkpoint = z["checkpoint_sha256"].item()
        calibrator_sha = z["calibrator_sha256"].item()
        rp, rl, ru = (align(z, ids, k) for k in ("predicted", "lower", "upper"))
    predicted = q[:, :, 1]
    lower, upper = np.maximum(q[:, :, 0], 0.0), np.maximum(q[:, :, 2], 0.0)

    def report(mask):
        return scores(
            y[mask], predicted[mask], lower[mask], upper[mask], limits[mask], np.zeros(mask.sum())
        )

    # Agregar contribuciones dentro de cada bloque de calendario antes del remuestreo.
    # Cada sorteo reutiliza los mismos bloques para todas las estaciones y ambos modelos.
    def interval(mask, delta, block_hours):
        valid = mask & np.isfinite(y)
        which = np.broadcast_to(hours[:, None], y.shape)[valid] // block_hours
        return block_difference(which, delta[valid], 1)

    strata = {"all": np.isfinite(y), "high": y >= limits[:, None]}
    diffs = {
        "mae": np.abs(predicted - y) - np.abs(rp - y),
        "coverage": ((lower <= y) & (y <= upper)).astype(float) - ((rl <= y) & (y <= ru)),
        "width": (upper - lower) - (ru - rl),
    }
    return {
        "version": "lima-quantile-comparison-v2",
        "block": "selection",
        "purpose": "historical_replay",
        "checkpoint_sha256": checkpoint,
        "candidate_sha256": candidate_sha,
        "reference_sha256": reference_sha,
        "reference_checkpoint_sha256": reference_checkpoint,
        "reference_calibrator_sha256": calibrator_sha,
        "reference_overall": scores(y, rp, rl, ru, limits, np.zeros(len(y))),
        "input_manifest_sha256": input_manifest_sha,
        "manifest_sha256": manifest_sha,
        "crossed": 0,
        "overall": report(np.ones(len(y), bool)),
        "stations": {s: report(stations == s) for s in np.unique(stations)},
        "paired_differences": {
            str(size): {
                k: {metric: interval(mask, delta, size) for metric, delta in diffs.items()}
                for k, mask in strata.items()
            }
            for size in (84, 168, 336)
        },
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-manifest", type=Path, required=True)
    for name in ("blocks", "candidate", "reference", "output"):
        p.add_argument(name, type=Path)
    for name in ("manifest", "candidate", "input-manifest", "reference"):
        p.add_argument("--" + name + "-sha256", required=True)
    a = p.parse_args()
    result = compare(
        a.blocks,
        a.manifest_sha256,
        a.candidate,
        a.candidate_sha256,
        a.input_manifest_sha256,
        a.reference,
        a.reference_sha256,
        a.input_manifest,
    )
    with NamedTemporaryFile(dir=a.output.parent) as tmp:
        tmp.write((json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
        tmp.flush()
        os.link(tmp.name, a.output)
