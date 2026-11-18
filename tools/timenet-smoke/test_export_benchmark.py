"""Probar que cada tarea escrita recibe solo las horas de historia."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main

import pyarrow as pa
from export_benchmark import HourlySeries, add_window_task, benchmark_metadata
from timenet.dataset import TimeFDataset
from timenet.reader import TimeFReader


class BenchmarkTimeFTest(TestCase):
    def test_written_task_preserves_split_targets_and_input_boundary(self):
        start = datetime(2024, 1, 1, tzinfo=UTC)
        series = HourlySeries("lima", start, pa.array([1.0, 0.0, 3.0, 4.0, 5.0]))
        window = {
            "window_id": "ventana-a",
            "series_id": "serie-a",
            "station_key": "lima",
            "history_start": start,
            "origin_at": start + timedelta(hours=1),
            "target_start": start + timedelta(hours=2),
            "target_end": start + timedelta(hours=3),
            "target_values": [3.0, 4.0],
            "split": "validation",
        }
        dataset = TimeFDataset(metadata=benchmark_metadata("synthetic", "0.1.0", synthetic=True))
        add_window_task(dataset, series, window, history=2, horizon=2, provenance={})
        with TemporaryDirectory() as temporary:
            release = dataset.write(path=Path(temporary))
            with TimeFReader.open(release) as reader:
                reader.verify()
                (task,) = reader.iter_tasks()
                self.assertEqual(task.metadata["window_id"], "ventana-a")
                self.assertEqual(task.split, "validation")
                self.assertEqual(task.targets, (3.0, 4.0))
                self.assertEqual(task.inputs[0].signals[0].to_arrow().to_pylist(), [1.0, 0.0])
        window["target_values"] = [3.0, 8.0]
        with self.assertRaisesRegex(ValueError, "objetivo"):
            add_window_task(dataset, series, window, history=2, horizon=2, provenance={})


if __name__ == "__main__":
    main()
