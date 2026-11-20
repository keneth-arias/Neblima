"""Preparar historias verificadas y puntuar cada prueba externa de #88 por separado."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from export_senamhi import ROOT, sha256_file
from external_pm import PARAMS, digest_key, groups, label
from joint_validation import VIEWS, paired_table, read_predictions, summarize
from joint_windows import FREEZE, write_json
from verify_external_pm import verify

MODELS = ROOT / "metadata/validacion-pm25-pm10-congelacion.json"
SOURCES = ("openaq", "senamhi_horario")


def external_arrays(source, series):
    ids, stations, origins, histories, targets = [], [], [], [], []
    for (_, code, s25, s10), hours, values, starts in series:
        indexes = np.asarray(starts, dtype=int)
        origin = hours[indexes] + 23
        ids.extend(
            digest_key([source, code, s25, s10, label(h, source == "openaq")]) for h in origin
        )
        stations.extend([code] * len(indexes))
        origins.extend(origin)
        histories.append(values[indexes[:, None] + np.arange(24)])
        targets.append(values[indexes[:, None] + np.arange(24, 30)])
    keys = np.asarray(ids)
    if len(np.unique(keys)) != len(keys):
        raise ValueError("Identificadores externos repetidos")
    order = keys.argsort()
    inputs = dict(
        window_id=keys[order], channels=np.asarray(PARAMS), history=np.concatenate(histories)[order]
    )
    observations = dict(
        station_key=np.asarray(stations)[order],
        origin_hour=np.asarray(origins)[order],
        targets=np.concatenate(targets)[order],
    )
    return observations, inputs


def cohort(source):
    datasets = json.loads(FREEZE.read_text())["datasets"]
    return next(ds for ds in datasets if ds["source"] == source)


def prepare(registry, source, output):
    if output.exists():
        raise FileExistsError(output)
    ds = cohort(source)
    local = json.loads((registry / "resumen.json").read_text())
    if (
        local["source"] != source
        or local["manifest_sha256"] != ds["manifest_sha256"]
        or {Path(k).name: v for k, v in local["inputs"].items()} != ds["inputs"]
        or verify(registry) != ds["verified"]
    ):
        raise ValueError("El registro externo no corresponde a la versión congelada")
    with duckdb.connect(config={"threads": 2}) as db:
        series = groups(db, source, list(local["inputs"]), ds["begin"], ds["end_exclusive"])
        obs, inputs = external_arrays(source, series)
    ids_sha = digest_key(inputs["window_id"].tolist())
    if ids_sha != ds["verified"]["split_ids_sha256"]["test"]:
        raise ValueError("Cambió la cohorte de prueba")
    if {Path(k).name: sha256_file(Path(k)) for k in local["inputs"]} != ds["inputs"]:
        raise ValueError("Los insumos cambiaron durante la lectura")
    with TemporaryDirectory(dir=output.parent) as temp:
        stage = Path(temp) / "matrices"
        stage.mkdir()
        np.savez(stage / "observed.npz", **obs)
        np.savez(stage / "inputs.npz", **inputs)
        write_json(
            stage / "manifest.json",
            dict(
                source=source,
                ordered_ids_sha256=ids_sha,
                timef_sha256=ds["manifest_sha256"],
                files={p.name: sha256_file(p) for p in stage.glob("*.npz")},
            ),
        )
        stage.rename(output)


def score(source, matrices, predictions, scaler, output):
    if output.exists():
        raise FileExistsError(output)
    ds = cohort(source)
    frozen = json.loads(MODELS.read_text())
    manifest = json.loads((matrices / "manifest.json").read_text())
    if (
        manifest["source"] != source
        or manifest["timef_sha256"] != ds["manifest_sha256"]
        or sha256_file(scaler) != frozen["scaler_sha256"]
        or any(
            sha256_file(matrices / name) != manifest["files"][name]
            for name in ("inputs.npz", "observed.npz")
        )
    ):
        raise ValueError("Las matrices o el escalador difieren de su manifiesto")
    with np.load(matrices / "inputs.npz") as x, np.load(matrices / "observed.npz") as y:
        data = dict(x) | dict(y)
    keys = data["window_id"]
    if digest_key(keys.tolist()) != ds["verified"]["split_ids_sha256"]["test"]:
        raise ValueError("La lista ordenada de ventanas cambió")
    history = {s["site"]: s["code"] for s in cohort("historico")["stations"]}
    historical_p95 = json.loads(scaler.read_text())["p95"]
    thresholds = {s["code"]: historical_p95[history[s["site"]]] for s in ds["stations"]}
    forecasts, hashes = [], {}
    for view in VIEWS:
        path = predictions / f"{source}-{view}.npz"
        hashes[view] = sha256_file(path)
        with np.load(path) as pred:
            forecasts.append(
                read_predictions(
                    pred,
                    keys,
                    view,
                    frozen["models"][view]["checkpoint_sha256"],
                    frozen["scaler_sha256"],
                )
            )
    table = paired_table(data, *forecasts, thresholds, tz="UTC" if source == "openaq" else None)
    table = table.append_column(
        "source", pa.repeat(pa.scalar(source), len(table)).dictionary_encode()
    )
    with duckdb.connect(config={"threads": 1}) as db, TemporaryDirectory(dir=output.parent) as temp:
        db.register("pairs", table)
        summary = summarize(db)
        if summary["targets"] != ds["verified"]["target_values"]:
            raise ValueError("Denominador incorrecto")
        stage = Path(temp) / "resultados"
        stage.mkdir()
        pq.write_table(table, stage / "paired.parquet", compression="zstd")
        summary.update(
            source=source,
            clock="UTC" if source == "openaq" else "provider_wall_clock",
            windows=len(keys),
            matrices=manifest,
            models_freeze_sha256=sha256_file(MODELS),
            p95_by_station=thresholds,
            predictions_sha256=hashes,
            paired_sha256=sha256_file(stage / "paired.parquet"),
        )
        write_json(stage / "metrics.json", summary)
        stage.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for operation, names in [
        ("prepare", ("registry", "output")),
        ("score", ("matrices", "predictions", "scaler", "output")),
    ]:
        command = commands.add_parser(operation)
        command.add_argument("source", choices=SOURCES)
        for name in names:
            command.add_argument(name, type=Path)
    args = parser.parse_args()
    if args.operation == "prepare":
        prepare(args.registry, args.source, args.output)
    else:
        score(args.source, args.matrices, args.predictions, args.scaler, args.output)
