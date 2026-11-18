"""Prueba local de adquisición a pronóstico TimeF con un original ficticio."""

import csv
import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import pyarrow.parquet as pq
import yaml
from export_benchmark import sha256_file
from timenet import TimeNet
from timenet.reader import TimeFReader
from timenet.registry import LocalRegistry
from timenet.types import TimeOrigin

ROOT = Path(__file__).resolve().parents[2]
START = datetime(2024, 1, 1, tzinfo=UTC)


def run(*args: str | Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "UV_OFFLINE": "true"}
    env.pop("VIRTUAL_ENV", None)
    result = subprocess.run(
        [str(arg) for arg in args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        raise AssertionError(f"Falló {args}:\n{result.stdout}\n{result.stderr}")
    return result


def airaware(*args: str | Path) -> str:
    return run("uv", "run", "--locked", "airaware", *args).stdout


def fixture(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "FECHA",
                "HORA",
                "PM10",
                "PM2_5",
                "NO2",
                "ESTACION",
                "LONGITUD",
                "LATITUD",
                "ALTITUD",
                "DEPARTAMENTO",
                "PROVINCIA",
                "DISTRITO",
            ]
        )
        attrs = [30, "FICTICIA", "-77", "-12", "100", "LIMA", "LIMA", "FICTICIO"]
        for hour in range(72):
            stamp = START + timedelta(hours=hour)
            clock = [stamp.strftime("%Y%m%d"), stamp.strftime("%H%M%S"), 50]
            writer.writerow([*clock, "" if hour == 9 else hour, *attrs])
            if hour == 20:
                writer.writerow([*clock, 200, *attrs])


class OfflinePipelineTest(TestCase):
    def test_local_fixture_to_verified_timef_then_reject_tampering(self):
        with TemporaryDirectory(prefix="airaware-offline-") as temp:
            self.exercise_pipeline(Path(temp))

    def exercise_pipeline(self, root: Path) -> None:
        original = root / "original.csv"
        fixture(original)
        digest = sha256_file(original)
        spec = root / "request.json"
        spec.write_text(
            json.dumps(
                {
                    "source_id": "senamhi-lima-csv",
                    "resource_url": "https://example.invalid/ficticio.csv",
                    "method": "local",
                    "format": "csv",
                    "max_bytes": original.stat().st_size,
                    "expected_sha256": digest,
                }
            )
        )
        acquired = json.loads(
            airaware(
                "acquire",
                "import-file",
                "--spec",
                spec,
                "--file",
                original,
                "--data-dir",
                root / "data",
            )
        )
        receipt = json.loads(Path(acquired["manifest"]).read_text())
        self.assertEqual(receipt["sha256"], digest)
        policy = yaml.safe_load((ROOT / "configs/normalization/senamhi.yaml").read_text())
        policy["input_sha256"] = digest
        policy_file = root / "policy.yaml"
        policy_file.write_text(yaml.safe_dump(policy))
        normalized = root / "normalized"
        row_count = json.loads(
            airaware(
                "normalize",
                "senamhi",
                "--input",
                acquired["artifact"],
                "--policy",
                policy_file,
                "--output",
                normalized,
            )
        )["counts"]
        self.assertEqual(row_count, {"input_rows": 73, "observations": 219, "rejections": 0})
        self.assertEqual(sha256_file(original), digest)

        audit, grid, windows, splits = (
            root / "audit.parquet",
            root / "grid",
            root / "windows",
            root / "splits",
        )
        airaware("curate", "senamhi", "--input", normalized, "--output", audit)
        airaware("align", "senamhi", "--input", audit, "--output", grid)
        airaware(
            "benchmark",
            "windows",
            "--input",
            grid,
            "--output",
            windows,
            "--history",
            "2",
            "--horizon",
            "2",
        )
        airaware("benchmark", "split", "--input", windows, "--timeline", grid, "--output", splits)
        frozen = pq.read_table(splits / "splits.parquet").to_pylist()
        selected = {row["window_id"]: row for row in frozen if row["split"] != "purged"}
        self.assertTrue(any(row["split"] == "purged" for row in frozen))
        blocks = [
            [row for row in selected.values() if row["split"] == split]
            for split in ("train", "validation", "test")
        ]
        for left, right in pairwise(blocks):
            self.assertLess(
                max(row["target_end"] for row in left), min(row["history_start"] for row in right)
            )

        export = [
            "uv",
            "run",
            "--project",
            "tools/timenet-smoke",
            "--locked",
            "python",
            ROOT / "tools/timenet-smoke/export_benchmark.py",
            "--synthetic",
            "--timeline",
            grid,
            "--splits",
            splits,
            "--audit",
            audit,
        ]
        registry = root / "registry"
        run(*export, "--registry", registry)
        dataset_id = "airaware/lima-pm25-synthetic"
        with TimeFReader.open(registry / dataset_id / "0.1.0") as reader:
            reader.verify()
        dataset = TimeNet(sources=[LocalRegistry(registry)]).load(dataset_id, version="0.1.0")
        self.assertEqual(len(dataset.tasks), len(selected))
        self.assertEqual(dataset.metadata.source_revision, digest)
        for task in dataset.tasks:
            frozen_row = selected.pop(task.metadata["window_id"])
            (record,) = task.inputs
            history_start = frozen_row["history_start"]
            offset = (history_start - START) // timedelta(hours=1)
            self.assertEqual(record.start_time.timestamp, TimeOrigin(history_start).timestamp)
            self.assertEqual(record.signals[0].to_arrow().to_pylist(), [offset, offset + 1])
            self.assertEqual(task.targets, tuple(frozen_row["target_values"]))
            self.assertEqual(task.split, frozen_row["split"])
        self.assertEqual(selected, {})

        with (splits / "splits.parquet").open("ab") as stream:
            stream.write(b"modificado")
        result = run(*export, "--registry", root / "invalid", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHA-256 incorrecto para splits.parquet", result.stderr)
        self.assertFalse((root / "invalid").exists())
