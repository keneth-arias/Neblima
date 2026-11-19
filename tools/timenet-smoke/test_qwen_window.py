"""Comprobar la separación temporal al preparar un paso de entrenamiento."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import pyarrow as pa
from export_benchmark import HourlySeries, add_window_task, benchmark_metadata
from qwen_window import training_window
from timenet.dataset import TimeFDataset


class QwenWindowTest(TestCase):
    def write_release(self, root, future):
        start = datetime(2020, 1, 1, tzinfo=UTC)
        dataset = TimeFDataset(metadata=benchmark_metadata("sintético", "0.1.0", synthetic=True))
        for split in ("validation", "train"):
            history = list(range(24)) if split == "train" else [-9] * 24
            series = HourlySeries("lima", start, pa.array(history + future, type=pa.float64()))
            window = {
                "window_id": split,
                "series_id": "serie",
                "station_key": "lima",
                "history_start": start,
                "origin_at": start + timedelta(hours=23),
                "target_start": start + timedelta(hours=24),
                "target_end": start + timedelta(hours=29),
                "target_values": future,
                "split": split,
            }
            add_window_task(dataset, series, window, history=24, horizon=6, provenance={})
        return dataset.write(path=root)

    def test_targets_do_not_change_history_mask_or_station(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            a = training_window(self.write_release(root / "a", [2.0] * 6))
            b = training_window(self.write_release(root / "b", [5.0] * 6))
            self.assertEqual(a["history"], list(range(24)))
            self.assertEqual(a["observed"], [True] * 24)
            self.assertEqual(a["station_key"], "lima")
            self.assertEqual(a["window_id"], "train")
            self.assertEqual(a["origin_at"], "2020-01-01T23:00:00+00:00")
            self.assertEqual(a["history"], b["history"])
            self.assertEqual(a["observed"], b["observed"])
            self.assertNotEqual(a["targets"], b["targets"])
