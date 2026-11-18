"""Pruebas sin red del modelo de datos TimeF para la señal de Lima."""

from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main

import pyarrow as pa
from senamhi_timef import pm25_record
from timenet.dataset import TimeFDataset
from timenet.reader import TimeFReader
from timenet.types import DatasetMetadata, TimeOrigin, ureg


class SenamhiTimeFTest(TestCase):
    def test_round_trip_keeps_hourly_clock_zero_null_and_source(self):
        start = datetime(2024, 1, 1, 12, tzinfo=UTC)
        values = pa.array([12.125, 0.0, None, 3.25], type=pa.float64())
        dataset = TimeFDataset(
            metadata=DatasetMetadata(
                dataset_id="airaware/senamhi-synthetic",
                dataset_version="0.1.0",
                name="Prueba sintética de AirAware",
                description="Señal ficticia para verificar el eje horario.",
                license="NONE",
            )
        )
        provenance = {"source_id": "synthetic", "record_ids": ["r1", "r2", None, "r4"]}
        dataset.add_record(
            record=pm25_record(
                station_key="lima-provisional",
                start=start,
                values=values,
                provenance=provenance,
            )
        )

        with TemporaryDirectory() as temporary:
            release = dataset.write(path=Path(temporary) / "release")
            with TimeFReader.open(release) as reader:
                reader.verify()
                restored = reader.read().records[0]
                signal = restored.signals[0]
                self.assertEqual(restored.start_time.timestamp, TimeOrigin(start).timestamp)
                self.assertEqual(restored.metadata["station_key"], "lima-provisional")
                self.assertEqual(restored.metadata["provenance"], provenance)
                self.assertEqual(signal.time_axis.period_us, 3_600_000_000)
                self.assertEqual(signal.time_axis.start_index, 0)
                self.assertEqual(signal.spec.unit_value, ureg.microgram / ureg.meter**3)
                self.assertTrue(signal.to_arrow().equals(values))
                self.assertEqual(signal.null_count, 1)


if __name__ == "__main__":
    main()
