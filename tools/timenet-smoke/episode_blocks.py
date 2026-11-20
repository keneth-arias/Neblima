"""Construir los cuatro bloques de Lima a partir de ventanas PM2.5 horarias verificadas."""

import argparse
import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from export_senamhi import sha256_file
from joint_windows import write_json

BLOCKS = ("train", "calibration", "selection", "test")
VERSION = "lima-pm25-h24-f6-episodes-v1"


@lru_cache(maxsize=8192)
def utc_hour(text):
    stamp = datetime.fromisoformat(str(text))
    if stamp.utcoffset() is None:
        raise ValueError("Se requiere zona horaria explícita")
    stamp = stamp.astimezone(UTC)
    if stamp.minute or stamp.second or stamp.microsecond:
        raise ValueError("Se requiere una hora exacta")
    return int(stamp.timestamp()) // 3600


def load_windows(sources):
    fields = ("window_id", "station_key", "origin_at", "history", "targets")
    chunks = {key: [] for key in fields}
    for path, digest in sources:
        if sha256_file(path) != digest:
            raise ValueError(f"La huella difiere para {path}")
        with np.load(path, allow_pickle=False) as data:
            count = len(data["window_id"])
            for key in fields:
                values = data[key]
                if key in ("history", "targets"):
                    width = 24 if key == "history" else 6
                    if values.shape != (count, width) or values.dtype.kind not in "iuf":
                        raise ValueError(f"Dimensiones o tipo inválidos en {key}")
                    if not np.isfinite(values).all():
                        raise ValueError(f"Hay lecturas no finitas en {key}")
                elif values.shape != (count,) or values.dtype.kind != "U" or (values == "").any():
                    raise ValueError(f"Campo de texto inválido en {key}")
                chunks[key].append(values)
    data = {key: np.concatenate(values) for key, values in chunks.items()}
    if len(np.unique(data["window_id"])) != len(data["window_id"]):
        raise ValueError("Identificadores duplicados entre insumos")
    data["origin_hour"] = np.array([utc_hour(t) for t in data.pop("origin_at")], dtype=np.int64)
    return data


def training_thresholds(stations, origins, history):
    thresholds = {}
    for station in np.unique(stations):
        mask = stations == station
        hours = (origins[mask, None] + np.arange(-23, 1)).ravel()
        order = hours.argsort(kind="stable")
        hours, values = hours[order], history[mask].ravel()[order]
        repeated = hours[1:] == hours[:-1]
        if np.any(values[1:][repeated] != values[:-1][repeated]):
            raise ValueError(f"Mediciones discordantes en la estación {station}")
        thresholds[str(station)] = float(np.quantile(values[np.r_[True, ~repeated]], 0.95))
    return thresholds


def export_blocks(sources, cuts, output):
    if output.exists():
        raise FileExistsError(output)
    bounds = [utc_hour(cut) for cut in cuts]
    if len(bounds) != 3 or not np.all(np.diff(bounds) > 0):
        raise ValueError("Se requieren tres cortes cronológicos distintos")
    data = load_windows(sources)
    origins = data["origin_hour"]
    first = np.searchsorted(bounds, origins - 23, side="right")
    last = np.searchsorted(bounds, origins + 6, side="right")
    manifest = {
        "version": VERSION,
        "unit": "ug/m3",
        "cuts": cuts,
        "source_sha256": [s for _, s in sources],
        "purged": int(np.sum(first != last)),
        "blocks": {},
    }
    with TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp) / "blocks"
        stage.mkdir()
        dropped = first != last
        np.savez(
            stage / "purged.npz",
            window_id=data["window_id"][dropped],
            station_key=data["station_key"][dropped],
            origin_hour=origins[dropped],
            first_block=first[dropped],
            last_block=last[dropped],
        )
        manifest["purged_sha256"] = sha256_file(stage / "purged.npz")
        for i, name in enumerate(BLOCKS):
            ix = np.flatnonzero((first == i) & (last == i))
            if not len(ix):
                raise ValueError(f"El bloque {name} está vacío")
            ix = ix[np.argsort(data["window_id"][ix])]
            folder = stage / name
            folder.mkdir()
            ids, stations, hours = (
                data[k][ix] for k in ("window_id", "station_key", "origin_hour")
            )
            history = data["history"][ix]
            if len(set(zip(stations.tolist(), hours.tolist(), strict=True))) != len(ix):
                raise ValueError("Estación y hora de origen duplicadas")
            if name == "train":
                write_json(
                    stage / "thresholds.json",
                    {
                        "version": VERSION,
                        "unit": "ug/m3",
                        "method": "linear_p95_unique_training_station_hours",
                        "stations": training_thresholds(stations, hours, history),
                    },
                )
            np.savez(folder / "index.npz", window_id=ids, station_key=stations, origin_hour=hours)
            np.savez(folder / "history.npz", window_id=ids, history=history)
            np.savez(folder / "observed.npz", window_id=ids, targets=data["targets"][ix])
            if name == "train":
                np.savez(
                    folder / "fit.npz", window_id=ids, history=history, targets=data["targets"][ix]
                )
            manifest["blocks"][name] = {
                "windows": len(ix),
                "first_hour": int(hours.min() - 23),
                "last_hour": int(hours.max() + 6),
                "files": {p.name: sha256_file(p) for p in sorted(folder.iterdir())},
            }
        manifest["thresholds_sha256"] = sha256_file(stage / "thresholds.json")
        write_json(stage / "manifest.json", manifest)
        stage.rename(output)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", nargs=2, action="append", required=True, metavar=("NPZ", "SHA256")
    )
    parser.add_argument("--cuts", nargs=3, required=True)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = export_blocks([(Path(p), h) for p, h in args.source], args.cuts, args.output)
    print(json.dumps(result))
