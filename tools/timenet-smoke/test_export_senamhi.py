"""Verificar la conversión local y el rechazo de Parquet alterado."""

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main

import pyarrow as pa
import pyarrow.parquet as pq
from export_senamhi import read_sample, sha256_file
from timenet.types import License


class ExportTest(TestCase):
    def test_verified_grid_produces_annotated_hourly_record(self):
        start = datetime(2024, 5, 1, tzinfo=UTC)
        with TemporaryDirectory() as temp:
            root = Path(temp)
            pq.write_table(
                pa.table(
                    {
                        "station_key": ["lima", "lima"],
                        "series_id": ["pm", "pm"],
                        "parameter_raw": ["PM2_5", "PM2_5"],
                        "unit": ["ug/m3", "ug/m3"],
                        "observed_at": [
                            start,
                            datetime(2024, 5, 1, 1, tzinfo=UTC),
                        ],
                        "value": pa.array([5.25, None], type=pa.float64()),
                        "status": ["observed", "conflict"],
                        "observation_id": ["original1", None],
                        "source_observation_ids": [["original1"], ["original2", "original3"]],
                    }
                ),
                root / "hours.parquet",
            )
            digest = sha256_file(root / "hours.parquet")
            (root / "manifest.json").write_text(
                json.dumps(
                    {"version": "senamhi-hourly-v1", "output_sha256": digest, "input_sha256": "a"}
                )
            )
            dataset = read_sample(
                root, station_key="lima", start=start, hours=2, source={"input_sha256": "b"}
            )
            self.assertEqual(dataset.metadata.license, License.ODC_BY_1_0)
            record = dataset.records[0]
            self.assertEqual(record.signals[0].to_arrow().to_pylist(), [5.25, None])
            self.assertEqual(
                record.metadata["provenance"]["source_observation_ids"][1],
                ["original2", "original3"],
            )
            with (root / "hours.parquet").open("ab") as stream:
                stream.write(b"alterado")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                read_sample(
                    root, station_key="lima", start=start, hours=2, source={"input_sha256": "b"}
                )


if __name__ == "__main__":
    main()
