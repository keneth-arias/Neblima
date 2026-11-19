"""Emparejar pronósticos en µg/m³ con los objetivos de validación de #25."""

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from export_senamhi import sha256_file

HOURS = np.arange(1, 7)


def ordered_ids(values):
    ids = np.asarray(values)
    if ids.ndim != 1 or ids.dtype.kind != "U" or not len(ids) or np.any(ids == ""):
        raise ValueError("Se requieren identificadores de ventana de texto no vacíos")
    order = ids.argsort()
    ids = ids[order]
    if np.any(ids[1:] == ids[:-1]):
        raise ValueError("Hay identificadores de ventana duplicados")
    return ids, order


def pair_predictions(windows, reference, forecasts=None):
    ids, order = ordered_ids(windows["window_id"])
    table = reference.sort_by([("window_id", "ascending"), ("forecast_hour", "ascending")])
    expected = len(ids) * len(HOURS)
    targets = windows["targets"][order]
    history = windows["history"][order]
    if targets.shape != (len(ids), 6) or history.shape != (len(ids), 24):
        raise ValueError("Se requieren ventanas completas H24/F6")
    if not np.isfinite(history).all() or not np.isfinite(targets).all():
        raise ValueError("Hay mediciones no finitas")
    if (
        len(table) != expected
        or not np.array_equal(table["window_id"], ids.repeat(6))
        or not np.array_equal(table["forecast_hour"], np.tile(HOURS, len(ids)))
        or not np.array_equal(table["station_key"], windows["station_key"][order].repeat(6))
        or not np.array_equal(table["actual"], targets.ravel())
    ):
        raise ValueError("Las claves, estaciones u objetivos difieren de la referencia")
    origins = pa.array(windows["origin_at"][order].repeat(6)).cast(pa.timestamp("us", tz="UTC"))
    if not table["origin_at"].combine_chunks().equals(origins):
        raise ValueError("El origen UTC difiere de la referencia")
    prediction = history[:, -1].repeat(6)
    if not np.array_equal(table["persistence"], prediction):
        raise ValueError("El último valor difiere de persistencia")
    if forecasts is not None:
        forecast_ids, permutation = ordered_ids(forecasts["window_id"])
        values = forecasts["predicted"]
        if (
            not np.array_equal(ids, forecast_ids)
            or not np.array_equal(HOURS, forecasts["forecast_hour"])
            or values.shape != targets.shape
            or values.dtype.kind not in "fiu"
            or not np.isfinite(values).all()
        ):
            raise ValueError("Las predicciones deben cubrir cada ventana y sus seis horizontes")
        prediction = values[permutation].ravel()
    return table.append_column("predicted", pa.array(prediction, type=pa.float64()))


def verified_reference(baselines, policy):
    manifest = baselines / "manifest.json"
    if sha256_file(manifest) != policy["baseline_manifest_sha256"]:
        raise ValueError("El manifiesto de #25 difiere del aprobado")
    baseline = json.loads(manifest.read_text())
    source = baselines / "predictions.parquet"
    if (
        baseline["timef_manifest_sha256"] != policy["timef_manifest_sha256"]
        or sha256_file(source) != baseline["files"][source.name]
    ):
        raise ValueError("La referencia difiere de la versión TimeF aprobada")
    return baseline, source


def evaluate(inputs, baselines, output, config, forecasts=None, model=None, revision=None):
    if output.exists():
        raise FileExistsError(output)
    if forecasts is not None and not (model and revision):
        raise ValueError("Indicar el modelo y la revisión de las predicciones")
    policy = yaml.safe_load(config.read_text())
    baseline, source = verified_reference(baselines, policy)
    split_info = {}
    id_sets = {}
    for split in ("train", "validation"):
        path = inputs / f"{split}.npz"
        digest = sha256_file(path)
        if digest != policy["npz_sha256"][split]:
            raise ValueError(f"SHA-256 incorrecto para {split}")
        with np.load(path, allow_pickle=False) as data:
            ids, _ = ordered_ids(data["window_id"])
        if len(ids) != policy["windows"][split]:
            raise ValueError(f"Conteo de ventanas incorrecto en {split}")
        id_sets[split] = ids
        split_info[split] = {
            "windows": len(ids),
            "npz_sha256": digest,
            "ordered_ids_sha256": hashlib.sha256(
                json.dumps(ids.tolist(), separators=(",", ":")).encode()
            ).hexdigest(),
        }
    if np.intersect1d(id_sets["train"], id_sets["validation"], assume_unique=True).size:
        raise ValueError("Entrenamiento y validación comparten ventanas")
    reference = pq.read_table(source, filters=[("split", "=", "validation")])
    with np.load(inputs / "validation.npz", allow_pickle=False) as validation:
        if forecasts is None:
            model, revision = "persistence", baseline["version"]
            table = pair_predictions(validation, reference)
        else:
            with np.load(forecasts, allow_pickle=False) as predictions:
                table = pair_predictions(validation, reference, predictions)
    table = table.append_column("model", pa.repeat(model, len(table))).append_column(
        "model_revision", pa.repeat(revision, len(table))
    )
    mae = np.abs(np.asarray(table["predicted"]) - np.asarray(table["actual"])).mean()
    if forecasts is None and not np.isclose(
        mae, baseline["validation_mae"]["persistence"], rtol=1e-12
    ):
        raise ValueError("El MAE de persistencia difiere de #25")
    with TemporaryDirectory(dir=output.parent) as tmp:
        result_dir = Path(tmp) / "resultado"
        result_dir.mkdir()
        paired = result_dir / "paired.parquet"
        pq.write_table(table, paired)
        report = {
            "version": policy["version"],
            "config_sha256": sha256_file(config),
            "timef_manifest_sha256": policy["timef_manifest_sha256"],
            "baseline_manifest_sha256": policy["baseline_manifest_sha256"],
            "inputs": split_info,
            "model": model,
            "revision": revision,
            "predictions_sha256": sha256_file(forecasts) if forecasts else None,
            "split": "validation",
            "targets": len(table),
            "mae": float(mae),
            "unit": "ug/m3",
            "paired_sha256": sha256_file(paired),
        }
        (result_dir / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
        result_dir.rename(output)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "baselines", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).resolve().parents[2] / "configs/training.yaml"
    )
    parser.add_argument("--forecasts", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--revision")
    print(json.dumps(evaluate(**vars(parser.parse_args()))))
