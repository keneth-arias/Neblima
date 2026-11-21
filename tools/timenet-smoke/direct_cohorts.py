"""Congelar insumos separados de ajuste, validación interna y confirmación de PM2.5."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from episode_blocks import VERSION, training_thresholds, utc_hour
from episode_calibration import check_file
from export_senamhi import sha256_file
from joint_windows import write_json
from paired_forecasts import ordered_ids

ROLES = ("fit", "inner_validation", "confirmation", "purged")
PROTOCOL = Path(__file__).resolve().parents[2] / "configs/training/lima-directo-cohortes-v1.json"


def membership(sorted_ids):
    digest = hashlib.sha256()
    for value in sorted_ids:
        if "\n" in value or "\r" in value:
            raise ValueError("Identificador de ventana con salto de línea")
        digest.update(value.encode("utf-8") + b"\n")
    return {"windows": len(sorted_ids), "ids_sha256": digest.hexdigest()}


def load_training(blocks, source_hash):
    source = json.loads(check_file(blocks / "manifest.json", source_hash).read_bytes())
    if source.get("version") != VERSION or source.get("unit") != "ug/m3":
        raise ValueError("Versión o unidad inesperada en los bloques históricos")
    files = source["blocks"]["train"]["files"]
    folder = blocks / "train"
    with (
        np.load(check_file(folder / "index.npz", files["index.npz"]), allow_pickle=False) as index,
        np.load(check_file(folder / "fit.npz", files["fit.npz"]), allow_pickle=False) as fit,
    ):
        ids, index_order = ordered_ids(index["window_id"])
        fit_ids, fit_order = ordered_ids(fit["window_id"])
        if not np.array_equal(ids, fit_ids):
            raise ValueError("Los identificadores de ajuste difieren del índice")
        rows = {"window_id": ids}
        for name in ("station_key", "origin_hour"):
            values = index[name]
            if values.shape != ids.shape:
                raise ValueError(f"Dimensiones incorrectas en {name}")
            rows[name] = values[index_order]
        for name, width in (("history", 24), ("targets", 6)):
            values = fit[name]
            if (
                values.shape != (len(ids), width)
                or values.dtype.kind not in "ifu"
                or not np.isfinite(values).all()
            ):
                raise ValueError(f"Se requieren {width} valores finitos por fila en {name}")
            rows[name] = values[fit_order]
    stations, hours = rows["station_key"], rows["origin_hour"]
    if stations.dtype.kind != "U" or np.any(stations == "") or hours.dtype.kind != "i":
        raise ValueError("Estación u hora de origen inválida")
    if len(set(zip(stations.tolist(), hours.tolist(), strict=True))) != len(ids):
        raise ValueError("Estación y hora de origen duplicadas")
    return rows


def export(blocks, protocol_path, output):
    if output.exists():
        raise FileExistsError(output)
    raw = protocol_path.read_bytes()
    protocol = json.loads(raw)
    if protocol["version"] != "lima-directo-cohortes-v1" or not re.fullmatch(
        "[0-9a-f]{64}", protocol["weights_manifest_sha256"]
    ):
        raise ValueError("Versión del protocolo o huella del modelo inválida")
    rows = load_training(blocks, protocol["source_manifest_sha256"])
    ids, hours = rows["window_id"], rows["origin_hour"]
    cuts = [utc_hour(value) for value in protocol["cuts_utc"]]
    if len(cuts) != 3 or not np.all(np.diff(cuts) > 0) or np.any(hours + 6 >= cuts[-1]):
        raise ValueError("Cortes inválidos o ventana fuera del entrenamiento histórico")
    first = np.searchsorted(cuts[:2], hours - 23, side="right")
    last = np.searchsorted(cuts[:2], hours + 6, side="right")
    part = np.where(first == last, first, 3)
    groups = {role: np.flatnonzero(part == i) for i, role in enumerate(ROLES)}
    for role, indices in groups.items():
        if membership(ids[indices]) != protocol["cohorts"][role]:
            raise ValueError(f"El conteo o la huella de {role} difiere del protocolo")
    fit = groups["fit"]
    sample = protocol["fit_graph_sample"]
    if not 0 < sample["windows"] <= len(fit):
        raise ValueError("Tamaño inválido de la muestra fija")
    ranked = sorted(
        range(len(fit)), key=lambda i: (hashlib.sha256(ids[fit[i]].encode()).digest(), ids[fit[i]])
    )
    mask = np.zeros(len(fit), dtype=bool)
    mask[ranked[: sample["windows"]]] = True
    if membership(ids[fit][mask]) != sample:
        raise ValueError("La muestra fija de ajuste difiere del protocolo")

    thresholds = {
        "method": "linear_p95_unique_fit_history_station_hours",
        "fit_ids_sha256": protocol["cohorts"]["fit"]["ids_sha256"],
        "unit": "ug/m3",
        "stations": training_thresholds(rows["station_key"][fit], hours[fit], rows["history"][fit]),
    }
    record = {
        "version": protocol["version"],
        "protocol_sha256": hashlib.sha256(raw).hexdigest(),
        "historical_use": "all_roles_previously_used_for_historical_training",
        "source_manifest_sha256": protocol["source_manifest_sha256"],
        "cohorts": protocol["cohorts"],
        "fit_graph_sample": sample,
        "manifests": {},
    }
    with TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp) / "cohortes"
        stage.mkdir(mode=0o700)
        for role in ROLES[:3]:
            owner = "scorer" if role == "confirmation" else "trainer"
            folder = stage / owner / role
            folder.mkdir(parents=True)
            data = {name: values[groups[role]] for name, values in rows.items()}
            if role == "fit":
                data["graph_sample"] = mask
            np.savez(folder / "data.npz", **data)
            write_json(folder / "thresholds.json", thresholds)
            write_json(
                folder / "manifest.json",
                {
                    "schema": "forecast-direct-cohort-v1",
                    "unit": "ug/m3",
                    "head": "direct",
                    "phase": role,
                    "protocol_sha256": record["protocol_sha256"],
                    "source_manifest_sha256": record["source_manifest_sha256"],
                    "historical_use": record["historical_use"],
                    "weights_manifest_sha256": protocol["weights_manifest_sha256"],
                    **protocol["cohorts"][role],
                    "files": {f: sha256_file(folder / f) for f in ("data.npz", "thresholds.json")},
                },
            )
            record["manifests"][role] = sha256_file(folder / "manifest.json")
        write_json(stage / "purged.json", ids[groups["purged"]].tolist())
        write_json(stage / "manifest.json", record)
        stage.rename(output)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blocks", type=Path, help="Carpeta de los bloques históricos verificados")
    parser.add_argument("output", type=Path, help="Carpeta local nueva para publicar la entrega")
    args = parser.parse_args()
    print(json.dumps(export(args.blocks, PROTOCOL, args.output), sort_keys=True))
