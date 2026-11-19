"""Evaluar en prueba los modelos y referencias elegidos en validación."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from export_senamhi import sha256_file
from forecast_errors import summarize
from paired_forecasts import pair_predictions, verified_reference


def record(folder, table, name, revision, prediction_sha=None):
    folder.mkdir()
    table = table.append_column("model", pa.repeat(name, len(table))).append_column(
        "model_revision", pa.repeat(revision, len(table))
    )
    paired = folder / "paired.parquet"
    pq.write_table(table, paired)
    manifest = {
        "model": name,
        "revision": revision,
        "predictions_sha256": prediction_sha,
        "paired_sha256": sha256_file(paired),
        "targets": len(table),
        "split": "test",
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return {**manifest, **summarize(folder)}


def evaluate(inputs, baselines, config, output):
    if output.exists():
        raise FileExistsError(output)
    frozen = yaml.safe_load(config.read_text())
    baseline, source = verified_reference(baselines, frozen)
    export = json.loads((inputs / "export.json").read_text())
    test = inputs / "test.npz"
    if (
        frozen["split_used_for_selection"] != "validation"
        or export["split"] != "test"
        or export["windows"] != frozen["test"]["windows"]
        or export["manifest_sha256"] != frozen["timef_manifest_sha256"]
        or sha256_file(test) != export["output_sha256"]
    ):
        raise ValueError("La partición de prueba difiere de la selección congelada")
    reference = pq.read_table(source, filters=[("split", "=", "test")])
    models = {}
    with (
        TemporaryDirectory(dir=output.parent) as temp,
        np.load(test, allow_pickle=False) as windows,
    ):
        stage = Path(temp) / "resultado"
        stage.mkdir()
        common = pair_predictions(windows, reference).drop_columns(["predicted"])
        if (
            len(windows["window_id"]) != export["windows"]
            or len(common) != frozen["test"]["targets"]
        ):
            raise ValueError("El conteo difiere del plan de prueba")
        for name in frozen["baseline_models"]:
            table = common.append_column("predicted", common[name])
            models[name] = record(stage / name, table, name, baseline["version"])
        for key, name, revision in (
            ("cnn", "cnn", frozen["cnn_weights_sha256"]),
            ("qwen", frozen["qwen"]["model"], frozen["qwen"]["checkpoint_manifest_sha256"]),
        ):
            forecasts = inputs / f"{key}.npz"
            with np.load(forecasts, allow_pickle=False) as predictions:
                if (
                    "checkpoint_sha256" not in predictions
                    or predictions["checkpoint_sha256"].item() != revision
                ):
                    raise ValueError(f"El punto de control de {name} difiere de la selección")
                table = pair_predictions(windows, reference, predictions)
            models[name] = record(stage / name, table, name, revision, sha256_file(forecasts))
        result = {
            "selection": frozen["version"],
            "selection_sha256": sha256_file(config),
            "baseline_manifest_sha256": frozen["baseline_manifest_sha256"],
            "test": export,
            "unit": "ug/m3",
            "models": models,
        }
        (stage / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        stage.rename(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("inputs", "baselines", "config", "output"):
        parser.add_argument(key, type=Path)
    result = evaluate(**vars(parser.parse_args()))
    print(json.dumps({name: row["overall"] for name, row in result["models"].items()}))
