"""Repetir los intervalos de #28 con sus insumos verificados y el evaluador por estación."""

import argparse
import json
from argparse import Namespace
from pathlib import Path

import numpy as np
import yaml
from episode_blocks import BLOCKS, export_blocks
from episode_calibration import check_file, run
from episode_score import evaluate
from export_senamhi import sha256_file
from joint_windows import write_json
from paired_forecasts import ordered_ids

ROOT = Path(__file__).resolve().parents[2]
CUTS = ["2022-03-16T08:00:00Z", "2022-09-01T00:00:00Z", "2023-02-25T18:00:00Z"]


def overlap(blocks, sources, output):
    """Archivar horas e IDs compartidos con cada uso anterior de la cohorte."""
    from episode_blocks import utc_hour

    def hours(origins):
        return np.unique(np.asarray(origins, dtype=np.int64)[:, None] + np.arange(-23, 7))

    prior = {}
    for name, (path, digest) in sources.items():
        with np.load(check_file(path, digest), allow_pickle=False) as raw:
            origins = np.array([utc_hour(t) for t in raw["origin_at"]])
            prior[name] = (
                raw["window_id"],
                {s: hours(origins[raw["station_key"] == s]) for s in np.unique(raw["station_key"])},
            )
    report = {}
    for role in BLOCKS:
        with np.load(blocks / role / "index.npz", allow_pickle=False) as idx:
            role_hours = {
                s: hours(idx["origin_hour"][idx["station_key"] == s])
                for s in np.unique(idx["station_key"])
            }
            rows = {}
            for name, (ids, by_station) in prior.items():
                shared = {"window_id": np.intersect1d(idx["window_id"], ids)}
                for s, h in role_hours.items():
                    shared["station_" + s] = np.intersect1d(h, by_station.get(s, [])).astype(
                        np.int64
                    )
                outfile = output / f"overlap-{role}-{name}.npz"
                np.savez(outfile, **shared)
                rows[name] = {
                    "windows": len(shared["window_id"]),
                    "station_hours": sum(len(shared["station_" + s]) for s in role_hours),
                    "sha256": sha256_file(outfile),
                }
            report[role] = rows
    return report


def replay(source, output):
    training = yaml.safe_load((ROOT / "configs/training.yaml").read_text())
    test = json.loads((ROOT / "metadata/qwen-heldout-lima.json").read_text())["test"]
    validation = json.loads((ROOT / "metadata/qwen-validation-lora.json").read_text())
    if test["manifest_sha256"] != training["timef_manifest_sha256"]:
        raise ValueError("La prueba anterior tiene otro manifiesto")
    sources = {
        name: (source / (name + ".npz"), digest) for name, digest in training["npz_sha256"].items()
    }
    sources["test"] = (source / "holdout-v1/test.npz", test["output_sha256"])
    output.mkdir(parents=True, exist_ok=False)
    blocks = output / "blocks"
    m = export_blocks(list(sources.values()), CUTS, blocks)
    shared = overlap(blocks, sources, output)
    forecast = source / "fits/direct-lora/validation.npz"
    with np.load(check_file(forecast, validation["predictions_sha256"]), allow_pickle=False) as f:
        ids, order = ordered_ids(f["window_id"])
        for role in ("calibration", "selection"):
            with np.load(blocks / role / "index.npz", allow_pickle=False) as idx:
                keys = idx["window_id"]
            take = ids.searchsorted(keys)
            if (take >= len(ids)).any() or not np.array_equal(ids[take], keys):
                raise ValueError("Faltan predicciones de #28")
            np.savez(
                output / (role + ".npz"),
                window_id=keys,
                predicted=f["predicted"][order[take]],
                forecast_hour=f["forecast_hour"],
                checkpoint_sha256=f["checkpoint_sha256"],
            )
    manifest_sha = sha256_file(blocks / "manifest.json")
    cal = output / "calibrator.json"
    run(
        Namespace(
            command="fit",
            blocks=blocks,
            forecasts=output / "calibration.npz",
            output=cal,
            eligible_labels=None,
            manifest_sha256=manifest_sha,
        )
    )
    prediction = output / "selection-intervals.npz"
    run(
        Namespace(
            command="apply",
            block="selection",
            blocks=blocks,
            forecasts=output / "selection.npz",
            calibrator=cal,
            calibrator_sha256=sha256_file(cal),
            manifest_sha256=manifest_sha,
            output=prediction,
        )
    )
    table = evaluate(blocks, manifest_sha, prediction, sha256_file(prediction))
    table.update(
        source_sha256={k: v[1] for k, v in sources.items()},
        timef_manifest_sha256=training["timef_manifest_sha256"],
        prior_overlap=shared,
        calibrator_sha256=sha256_file(cal),
        cuts=CUTS,
        purged=m["purged"],
        windows={k: v["windows"] for k, v in m["blocks"].items()},
    )
    write_json(output / "summary.json", table)
    return table


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path, help="Carpeta de qwen-pm25-v1")
    p.add_argument("output", type=Path)
    a = p.parse_args()
    print(json.dumps(replay(a.source, a.output)["overall"]["all"]))
