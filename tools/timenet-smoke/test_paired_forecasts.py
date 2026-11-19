"""Comprobar el emparejamiento de las predicciones con las ventanas congeladas."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from export_senamhi import sha256_file
from paired_forecasts import evaluate, pair_predictions


class PairedForecastTest(TestCase):
    def setUp(self):
        ids = np.array(["b", "a"])
        self.windows = {
            "window_id": ids,
            "station_key": np.array(["lima"] * 2),
            "origin_at": np.array(["2020-01-01T23:00:00+00:00"] * 2),
            "history": np.ones((2, 24)),
            "targets": np.vstack([np.full(6, 7.0), np.full(6, 3.0)]),
        }
        self.reference = pa.table(
            {
                "window_id": ids.repeat(6),
                "forecast_hour": np.tile(np.arange(1, 7), 2),
                "station_key": ["lima"] * 12,
                "origin_at": pa.array(self.windows["origin_at"].repeat(6)).cast(
                    pa.timestamp("us", "UTC")
                ),
                "actual": self.windows["targets"].flatten(),
                "persistence": np.ones(12),
            }
        ).take(list(reversed(range(12))))
        self.forecasts = {
            "window_id": ids[::-1],
            "forecast_hour": np.arange(1, 7),
            "predicted": np.vstack([np.full(6, 3.0), np.full(6, 7.0)]),
        }

    def test_pairs_even_when_all_orders_differ(self):
        table = pair_predictions(self.windows, self.reference, self.forecasts)
        self.assertEqual(table["predicted"].to_pylist(), table["actual"].to_pylist())
        self.assertEqual(len(table), 12)
        baseline = pair_predictions(self.windows, self.reference)
        self.assertEqual(baseline["predicted"].to_pylist(), [1.0] * 12)

    def test_rejects_missing_duplicated_or_different_targets(self):
        for reference in [
            self.reference.slice(1),
            self.reference.take([0, *range(11)]),
            self.reference.set_column(4, "actual", pa.array([100.0] * 12)),
        ]:
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                pair_predictions(self.windows, reference)
        for column, value in [
            ("forecast_hour", np.arange(6)),
            ("window_id", ["b", "b"]),
            ("predicted", np.full((2, 6), np.inf)),
        ]:
            with self.subTest(column=column), self.assertRaises(ValueError):
                pair_predictions(self.windows, self.reference, {**self.forecasts, column: value})

    def test_validates_pinned_inputs_and_exports_each_model(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            np.savez(root / "train.npz", window_id=np.array(["c"]))
            np.savez(root / "validation.npz", **self.windows)
            np.savez(root / "model.npz", **self.forecasts)
            reference = self.reference.append_column("split", pa.array(["validation"] * 12))
            pq.write_table(reference, root / "predictions.parquet")
            baseline = {
                "version": "baseline-v1",
                "timef_manifest_sha256": "test",
                "files": {"predictions.parquet": sha256_file(root / "predictions.parquet")},
                "validation_mae": {"persistence": 4.0},
            }
            (root / "manifest.json").write_text(json.dumps(baseline))
            config = root / "config.yaml"
            policy = {
                "version": "test",
                "timef_manifest_sha256": "test",
                "baseline_manifest_sha256": sha256_file(root / "manifest.json"),
                "windows": {"train": 1, "validation": 2},
                "npz_sha256": {s: sha256_file(root / f"{s}.npz") for s in ("train", "validation")},
            }
            config.write_text(yaml.safe_dump(policy))
            report = evaluate(root, root, root / "control", config)
            self.assertEqual(report["mae"], 4.0)
            report = evaluate(
                root, root, root / "candidate", config, root / "model.npz", "direct", "revision"
            )
            self.assertEqual(report["mae"], 0)
            self.assertEqual(
                report["paired_sha256"], sha256_file(root / "candidate/paired.parquet")
            )
            with self.assertRaises(FileExistsError):
                evaluate(root, root, root / "candidate", config)
            np.savez(root / "train.npz", window_id=np.array(["a"]))
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                evaluate(root, root, root / "bad", config)
            policy["npz_sha256"]["train"] = sha256_file(root / "train.npz")
            config.write_text(yaml.safe_dump(policy))
            with self.assertRaisesRegex(ValueError, "comparten"):
                evaluate(root, root, root / "bad", config)
            self.assertFalse((root / "bad").exists())
