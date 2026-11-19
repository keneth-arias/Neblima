"""Comprobar errores pareados y solapamiento sobre resultados pequeños."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import pyarrow as pa
import pyarrow.parquet as pq
from export_senamhi import sha256_file
from forecast_errors import summarize


class ForecastErrorsTest(TestCase):
    def test_high_concentrations_overlap_and_artifact_identity(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            predictions = folder / "paired.parquet"
            table = pa.table(
                {
                    "station_key": ["a", "a", "b"],
                    "target_at": [5, 5, 5],
                    "forecast_hour": [1, 2, 1],
                    "high_concentration": [True, True, False],
                    "actual": [9.0, 9.0, 4.0],
                    "persistence": [1.0, 5.0, 3.0],
                    "predicted": [7.0, 10.0, 4.0],
                }
            )
            pq.write_table(table, predictions)
            manifest = folder / "manifest.json"
            manifest.write_text(
                json.dumps({"targets": 3, "paired_sha256": sha256_file(predictions)})
            )
            report = summarize(folder)
            self.assertEqual(report["overall"]["targets"], 3)
            self.assertEqual(report["overall"]["station_hours"], 2)
            self.assertEqual(report["overall"]["mae"], 1.0)
            self.assertAlmostEqual(report["overall"]["delta_mae"], -10 / 3)
            self.assertEqual(report["by_station"]["a"]["mae"], 1.5)
            self.assertEqual(report["by_horizon"]["2"]["persistence_mae"], 4.0)
            self.assertEqual(report["high_concentration"], report["by_station"]["a"])
            pq.write_table(table.slice(0, 1), predictions)
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                summarize(folder)
            manifest.write_text(
                json.dumps({"targets": 3, "paired_sha256": sha256_file(predictions)})
            )
            with self.assertRaisesRegex(ValueError, "conteo"):
                summarize(folder)
            broken = table.set_column(6, "predicted", pa.array([None, 10.0, 4.0]))
            pq.write_table(broken, predictions)
            manifest.write_text(
                json.dumps({"targets": 3, "paired_sha256": sha256_file(predictions)})
            )
            with self.assertRaisesRegex(ValueError, "Faltan"):
                summarize(folder)
