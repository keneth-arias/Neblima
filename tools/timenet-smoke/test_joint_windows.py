"""Controles de lectura bivariada y ajuste exclusivo en historia."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from external_pm import add_group
from joint_windows import fit_scaler, read_split
from timenet.dataset import TimeFDataset
from timenet.reader import TimeFReader
from timenet.types import DatasetMetadata, License


class JointWindowsTest(unittest.TestCase):
    def test_distinct_hours_ignore_repeats_and_future(self):
        x = np.arange(25, dtype=float)
        pair = np.column_stack((x, np.full_like(x, 8)))
        history = np.stack((pair[:-1], pair[1:]))
        stats = fit_scaler(["s", "s"], [23, 24], history)
        np.testing.assert_allclose(stats["mean"], [12, 8])
        np.testing.assert_allclose(stats["scale"], [x.std(), 1])
        self.assertEqual(stats["station_hours"], 25)
        history[1, 0, 1] = 4
        with self.assertRaises(ValueError):
            fit_scaler(["s", "s"], [23, 24], history)

    def test_roundtrip_channels_and_split_boundary(self):
        with TemporaryDirectory() as tmp:
            ds = TimeFDataset(
                metadata=DatasetMetadata(
                    dataset_id="example/hist",
                    dataset_version="0.1.0",
                    name="Fixture",
                    description="Lima",
                    license=License.NONE,
                )
            )
            hours = np.arange(100)
            values = np.column_stack((hours, 1000 + hours)).astype(float)
            add_group(ds, ("Lima", "s", None, None), hours, values, np.arange(71), "historico", 50)
            release = ds.write(path=Path(tmp))
            with TimeFReader.open(release) as reader:
                train = read_split(reader, "train", 21, 50)
                for i, h in enumerate(train["origin_hour"]):
                    np.testing.assert_array_equal(train["history"][i], values[h - 23 : h + 1])
                    np.testing.assert_array_equal(train["targets"][i], values[h + 1 : h + 7])
                with self.assertRaises(ValueError):
                    read_split(reader, "train", 21, 49)
