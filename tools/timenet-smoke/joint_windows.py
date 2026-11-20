"""Exportar la cohorte histórica bivariada y ajustar su escalador de entrenamiento."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from export_senamhi import ROOT, sha256_file
from external_pm import HOUR, PARAMS, SPECS
from timenet.reader import TimeFReader

VERSION = "lima-pm25-pm10-v1"
FREEZE = ROOT / "metadata/lima-pm-externa-20261120.json"


def fit_scaler(stations, origins, histories):
    stations, origins = np.asarray(stations), np.asarray(origins)
    unique_values = []
    thresholds = {}
    for station in np.unique(stations):
        selected = stations == station
        times = (origins[selected, None] + np.arange(-23, 1)).ravel()
        order = times.argsort(kind="stable")
        times = times[order]
        values = histories[selected].reshape(-1, 2)[order]
        repeated = np.diff(times) == 0
        if not np.array_equal(values[1:][repeated], values[:-1][repeated]):
            raise ValueError("Las copias de una hora discrepan en entrenamiento")
        distinct = values[np.r_[True, ~repeated]]
        unique_values.append(distinct)
        thresholds[str(station)] = np.quantile(distinct, 0.95, axis=0).tolist()
    values = np.concatenate(unique_values)
    if not np.isfinite(values).all():
        raise ValueError("Historia incompleta en el escalador")
    std = values.std(axis=0)
    return {
        "channels": list(PARAMS),
        "unit": "ug/m3",
        "station_hours": len(values),
        "mean": values.mean(axis=0).tolist(),
        "scale": np.where(std == 0, 1, std).tolist(),
        "method": "unique_training_history_station_hours_population_std",
        "p95": thresholds,
    }


def read_split(reader, split, count, cut):
    if split not in ("train", "validation"):
        raise ValueError("Se requiere una partición histórica")
    histories = np.empty((count, 24, 2), dtype=np.float64)
    targets = np.empty((count, 6, 2), dtype=np.float64)
    ids, stations, origins = [], [], []
    for i, task in enumerate(reader.iter_tasks(split=split, batch_size=512)):
        if i >= count:
            raise ValueError("Sobran tareas")
        (history,), (future,) = task.inputs, task.targets
        start = history.start_time.timestamp
        if start is None or start % HOUR or future.start_time.timestamp != start + 24 * HOUR:
            raise ValueError("Inicio o desfase horario incompatible")
        origin = start // HOUR + 23
        if (split == "train" and origin + 6 >= cut) or (
            split == "validation" and origin - 23 < cut
        ):
            raise ValueError("Una ventana cruza el corte cronológico")
        if task.metadata["clock"] != "UTC" or datetime.fromisoformat(
            task.metadata["origin_at"]
        ) != datetime.fromtimestamp(origin * 3600, UTC):
            raise ValueError("Origen incompatible")
        station = history.metadata["station_key"]
        for record, slot in ((history, histories[i]), (future, targets[i])):
            if (
                record.metadata["station_key"] != station
                or record.metadata["source"] != "historico"
            ):
                raise ValueError("Fuente o estación incompatible")
            signals = {signal.name: signal for signal in record.signals}
            if set(signals) != set(PARAMS) or len(record.signals) != 2:
                raise ValueError("Se requieren los dos contaminantes")
            for j, (name, spec) in enumerate(zip(PARAMS, SPECS, strict=True)):
                signal = signals[name]
                axis = signal.time_axis
                if (
                    signal.spec != spec
                    or axis.period_us != HOUR
                    or axis.offset_us
                    or axis.start_index
                ):
                    raise ValueError("Unidad o eje incompatible")
                values = signal.to_arrow().to_numpy(zero_copy_only=False)
                if values.shape != (len(slot),):
                    raise ValueError("Longitud incorrecta")
                slot[:, j] = values
        ids.append(task.metadata["window_id"])
        stations.append(station)
        origins.append(origin)
    keys = np.asarray(ids)
    if (
        len(keys) != count
        or len(np.unique(keys)) != count
        or not all(np.isfinite(a).all() for a in (histories, targets))
    ):
        raise ValueError("Cohorte incompleta o repetida")
    order = keys.argsort()
    return dict(
        window_id=keys[order],
        station_key=np.asarray(stations)[order],
        origin_hour=np.asarray(origins)[order],
        history=histories[order],
        targets=targets[order],
        channels=np.asarray(PARAMS),
    )


def write_json(path, body):
    path.write_text(
        json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    )


def export(release, output):
    if output.exists():
        raise FileExistsError(output)
    freeze = json.loads(FREEZE.read_text())
    parent = next(s for s in freeze["datasets"] if s["source"] == "historico")
    digest = sha256_file(release / "manifest.json")
    if digest != parent["manifest_sha256"]:
        raise ValueError("El registro difiere del histórico congelado")
    cut = int(datetime.fromisoformat(parent["cut_utc"]).timestamp()) // 3600
    manifest = {
        "version": VERSION,
        "timef_manifest_sha256": digest,
        "cut_utc": parent["cut_utc"],
        "channels": list(PARAMS),
        "inputs": {},
    }
    with TemporaryDirectory(dir=output.parent) as temporary, TimeFReader.open(release) as reader:
        stage = Path(temporary) / "matrices"
        stage.mkdir()
        reader.verify()
        for split in ("train", "validation"):
            arrays = read_split(reader, split, freeze["split_policy"][split], cut)
            keys = arrays["window_id"].tolist()
            ids_sha = hashlib.sha256(json.dumps(keys, separators=(",", ":")).encode()).hexdigest()
            if ids_sha != parent["verified"]["split_ids_sha256"][split]:
                raise ValueError("Los identificadores difieren de la cohorte congelada")
            path = stage / f"{split}.npz"
            np.savez(path, **arrays)
            manifest["inputs"][split] = {
                "windows": len(keys),
                "ordered_ids_sha256": ids_sha,
                "npz_sha256": sha256_file(path),
            }
            if split == "train":
                scaler = fit_scaler(arrays["station_key"], arrays["origin_hour"], arrays["history"])
                if scaler["station_hours"] != 268567:
                    raise ValueError("Cobertura del escalador distinta de la aprobada")
                scaler.update(version=VERSION, cut_utc=parent["cut_utc"], train_ids_sha256=ids_sha)
                write_json(stage / "scaler.json", scaler)
                manifest["scaler_sha256"] = sha256_file(stage / "scaler.json")
            del arrays
        write_json(stage / "manifest.json", manifest)
        stage.rename(output)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(export(args.release, args.output)))
