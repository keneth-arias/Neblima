"""Verificar una ronda de prueba independiente con pesos y referencias fijados."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from evaluate_finalists import evaluate
from export_senamhi import sha256_file


class HeldoutTest(TestCase):
    def test_paired_round_and_checkpoint_substitution(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            ids = np.array(["a"])
            date = np.array(["2023-01-01T00:00:00+00:00"])
            np.savez(
                root / "test.npz",
                window_id=ids,
                history=np.ones((1, 24)),
                station_key=ids,
                origin_at=date,
                targets=np.ones((1, 6)),
            )
            table = pa.table(
                {
                    "window_id": ["a"] * 6,
                    "station_key": ["a"] * 6,
                    "split": ["test"] * 6,
                    "forecast_hour": np.arange(1, 7),
                    "target_at": np.arange(1, 7),
                    "origin_at": pa.array(date.repeat(6)).cast(pa.timestamp("us", tz="UTC")),
                    "actual": [1.0] * 6,
                    "persistence": [1.0] * 6,
                    "daily": [4.0] * 6,
                    "seasonal": [3.0] * 6,
                    "high_concentration": [False] * 6,
                }
            )
            pq.write_table(table, root / "predictions.parquet")
            baseline = {
                "version": "v1",
                "timef_manifest_sha256": "timef",
                "files": {"predictions.parquet": sha256_file(root / "predictions.parquet")},
            }
            (root / "manifest.json").write_text(json.dumps(baseline))
            export = {
                "split": "test",
                "windows": 1,
                "manifest_sha256": "timef",
                "output_sha256": sha256_file(root / "test.npz"),
            }
            (root / "export.json").write_text(json.dumps(export))
            freeze = {
                "split_used_for_selection": "validation",
                "version": "finalistas",
                "timef_manifest_sha256": "timef",
                "baseline_manifest_sha256": sha256_file(root / "manifest.json"),
                "test": {"windows": 1, "targets": 6},
                "qwen": {"model": "qwen-direct-lora", "checkpoint_manifest_sha256": "modelo"},
                "cnn_weights_sha256": "cnn",
                "baseline_models": ["persistence", "daily", "seasonal"],
            }
            config = root / "finalistas.yaml"
            config.write_text(yaml.safe_dump(freeze))

            def forecast(name, revision):
                np.savez(
                    root / f"{name}.npz",
                    checkpoint_sha256=revision,
                    window_id=ids,
                    forecast_hour=np.arange(1, 7),
                    predicted=np.full((1, 6), 2.0),
                )

            forecast("cnn", "cnn")
            forecast("qwen", "otro")
            with self.assertRaisesRegex(ValueError, "punto de control"):
                evaluate(root, root, config, root / "reporte")
            self.assertFalse((root / "reporte").exists())
            np.savez(root / "qwen.npz", window_id=ids)
            with self.assertRaisesRegex(ValueError, "punto de control"):
                evaluate(root, root, config, root / "reporte")
            forecast("qwen", "modelo")
            result = evaluate(root, root, config, root / "reporte")
            self.assertEqual(result["models"]["daily"]["overall"]["mae"], 3.0)
            self.assertEqual(result["models"]["qwen-direct-lora"]["overall"]["delta_mae"], 1.0)
            self.assertEqual(result["models"]["cnn"]["overall"]["station_hours"], 6)
            with self.assertRaises(FileExistsError):
                evaluate(root, root, config, root / "reporte")
            (root / "export.json").write_text(json.dumps({**export, "split": "validation"}))
            with self.assertRaisesRegex(ValueError, "partición de prueba"):
                evaluate(root, root, config, root / "otra")
            (root / "export.json").write_text(json.dumps(export))
            (root / "predictions.parquet").write_bytes(b"alterado")
            with self.assertRaisesRegex(ValueError, "referencia"):
                evaluate(root, root, config, root / "otra")
