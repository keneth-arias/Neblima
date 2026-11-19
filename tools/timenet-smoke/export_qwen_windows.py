"""Preparar matrices offline a partir de las particiones congeladas de TimeF."""

import argparse
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from export_senamhi import sha256_file
from qwen_window import MANIFEST_SHA256, decode_window
from timenet.reader import TimeFReader


def export_windows(release: Path, output: Path, split: str, sample: int | None) -> dict:
    digest = sha256_file(release / "manifest.json")
    if digest != MANIFEST_SHA256:
        raise ValueError("El manifiesto difiere de la versión aprobada en #25")
    if output.exists():
        raise FileExistsError(output)
    with TimeFReader.open(release) as reader:
        reader.verify()
        tasks = reader.read_task_table().select(["split", "metadata"])
        selected = None
        if sample is not None:
            keys = sorted(
                json.loads(row["metadata"])["window_id"]
                for row in tasks.filter(np.array(tasks["split"]) == split).to_pylist()
            )
            if sample < 1 or sample > len(keys):
                raise ValueError("Tamaño de muestra fuera de la partición")
            generator = np.random.default_rng(27)
            selected = set(generator.choice(keys, sample, replace=False).tolist())
        rows = [
            decode_window(task)
            for task in reader.iter_tasks(split=split)
            if selected is None or task.metadata["window_id"] in selected
        ]
    rows.sort(key=lambda window: window["window_id"])
    columns = {
        key: np.array([row[key] for row in rows])
        for key in ("window_id", "station_key", "origin_at", "history", "targets")
    }
    if not rows or len(np.unique(columns["window_id"])) != len(rows):
        raise ValueError("La muestra tiene identificadores repetidos o está vacía")
    if selected is not None and len(rows) != sample:
        raise ValueError("Faltan ventanas de la muestra")
    with NamedTemporaryFile(dir=output.parent) as temporary:
        np.savez(temporary, **columns)
        temporary.flush()
        os.link(temporary.name, output)
    return {
        "split": split,
        "windows": len(rows),
        "manifest_sha256": digest,
        "output_sha256": sha256_file(output),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--split", choices=("train", "validation", "test"), required=True)
    parser.add_argument("--sample", type=int)
    args = parser.parse_args()
    print(json.dumps(export_windows(args.release, args.output, args.split, args.sample)))
