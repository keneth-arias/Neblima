"""Leer una ventana de entrenamiento H24/F6 del benchmark congelado."""

import argparse
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

from export_senamhi import sha256_file
from senamhi_timef import PM25
from timenet.dataset.axis import RegularAxis
from timenet.reader import TimeFReader

MANIFEST_SHA256 = "29135340efb377a59d695e05fb6f8848fd0e56481123f5b54e987da77e9adc97"


def training_window(release: Path) -> dict:
    with TimeFReader.open(release) as reader:
        reader.verify()
        task = next(reader.iter_tasks(split="train", batch_size=1), None)
        if task is None or task.split != "train":
            raise ValueError("Falta una ventana de entrenamiento")
        return decode_window(task)


def decode_window(task) -> dict:
    (record,) = task.inputs
    (signal,) = record.signals
    axis = signal.time_axis
    if signal.spec != PM25 or not isinstance(axis, RegularAxis):
        raise ValueError("Se requiere la señal horaria de PM2.5 en µg/m³")
    if axis.period_us != 3_600_000_000 or axis.offset_us != 0 or axis.start_index != 0:
        raise ValueError("El eje no corresponde al inicio de la historia horaria")
    history = signal.to_arrow().to_pylist()
    targets = list(task.targets)
    if len(history) != 24 or len(targets) != 6:
        raise ValueError("La prueba requiere 24 mediciones de historia y seis objetivos")
    if any(v is None or not math.isfinite(v) for v in history + targets):
        raise ValueError("La política del benchmark exige ventanas completas")
    start = datetime(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=record.start_time.timestamp)
    origin = start + timedelta(hours=23)
    metadata = task.metadata
    if (
        datetime.fromisoformat(metadata["origin_at"]) != origin
        or datetime.fromisoformat(metadata["target_start"]) != origin + timedelta(hours=1)
        or metadata["series_id"] != record.metadata["provenance"]["series_id"]
        or record.metadata["station_key"] != record.sources[0].name
    ):
        raise ValueError("La identidad o los límites temporales difieren de la tarea")
    return {
        **metadata,
        "station_key": record.metadata["station_key"],
        "provenance": record.metadata["provenance"],
        "split": task.split,
        "history": history,
        "observed": [v is not None for v in history],
        "targets": targets,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    args = parser.parse_args()
    digest = sha256_file(args.release / "manifest.json")
    if digest != MANIFEST_SHA256:
        raise ValueError("El manifiesto difiere de la versión aprobada en #25")
    print(json.dumps(dict(training_window(args.release), manifest_sha256=digest), allow_nan=False))


if __name__ == "__main__":
    main()
