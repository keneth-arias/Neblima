"""Exportar ventanas congeladas de SENAMHI como tareas de pronóstico TimeF."""

import argparse
import json
import math
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pyarrow as pa
from export_senamhi import CATALOG, ROOT, sha256_file
from senamhi_timef import pm25_record
from timenet.dataset import TimeFDataset
from timenet.reader import TimeFReader
from timenet.types import DatasetMetadata, ForecastingTask, License

ONE_HOUR = timedelta(hours=1)
PARTITIONS = ("train", "validation", "test")


def benchmark_metadata(
    source_sha: str, version: str, *, synthetic: bool, sample: bool = False
) -> DatasetMetadata:
    dataset = "lima-pm25-synthetic" if synthetic else "lima-pm25-forecast"
    return DatasetMetadata(
        dataset_id=f"airaware/{dataset}" + ("-sample" if sample and not synthetic else ""),
        dataset_version=version,
        name="Pronóstico horario de PM2.5 en Lima",
        description=(
            "Prueba ficticia del contrato de pronóstico."
            if synthetic
            else "Evaluación retrospectiva con particiones cronológicas fijas."
        ),
        license=License.NONE if synthetic else License.ODC_BY_1_0,
        license_url=None if synthetic else "https://opendatacommons.org/licenses/by/1-0/",
        source_url=None if synthetic else CATALOG,
        source_revision=source_sha,
        citation=None
        if synthetic
        else (
            "SENAMHI, Monitoreo de los contaminantes del aire en Lima Metropolitana. "
            "Adaptación horaria y tareas de pronóstico de AirAware."
        ),
    )


@dataclass(frozen=True)
class HourlySeries:
    station_key: str
    start: datetime
    values: pa.Array

    def read(self, start: datetime, length: int) -> pa.Array:
        offset, remainder = divmod(start - self.start, ONE_HOUR)
        if remainder or offset < 0 or offset + length > len(self.values):
            raise ValueError("La ventana está fuera de la grilla horaria")
        result = self.values.slice(offset, length)
        if result.null_count or not all(map(math.isfinite, result.to_pylist())):
            raise ValueError("La ventana contiene un valor sin medición finita")
        return result


def add_window_task(
    dataset: TimeFDataset,
    series: HourlySeries,
    window: dict,
    *,
    history: int,
    horizon: int,
    provenance: dict,
) -> None:
    start = window["history_start"]
    origin = start + (history - 1) * ONE_HOUR
    future = origin + ONE_HOUR
    if (
        series.station_key != window["station_key"]
        or origin != window["origin_at"]
        or future != window["target_start"]
        or future + (horizon - 1) * ONE_HOUR != window["target_end"]
    ):
        raise ValueError("La identidad o los límites de la ventana difieren de la grilla")
    values = series.read(start, history)
    targets = series.read(future, horizon).to_pylist()
    if targets != window["target_values"]:
        raise ValueError("Los valores del objetivo difieren de la grilla")
    record = dataset.add_record(
        record=pm25_record(
            station_key=series.station_key,
            start=start,
            values=values,
            provenance={**provenance, "series_id": window["series_id"]},
        )
    )
    dataset.add_task(
        task=ForecastingTask(
            inputs=(record,),
            targets=tuple(targets),
            split=window["split"],
            metadata={
                "window_id": window["window_id"],
                "origin_at": origin.isoformat(),
                "target_start": future.isoformat(),
                "series_id": window["series_id"],
            },
        )
    )


def verified_parquet(bundle: Path, name: str, version: str) -> tuple[Path, dict]:
    file = bundle / name
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    if manifest["version"] != version or manifest["output_sha256"] != sha256_file(file):
        raise ValueError(f"Versión o SHA-256 incorrecto para {name}")
    return file, manifest


def build_benchmark(
    timeline: Path,
    partitions: Path,
    audit: Path,
    *,
    version: str,
    limit: int | None = None,
    synthetic: bool = False,
) -> TimeFDataset:
    if limit is not None and limit < 1:
        raise ValueError("El límite por estación y partición debe ser positivo")
    grid, grid_meta = verified_parquet(timeline, "hours.parquet", "senamhi-hourly-v1")
    splits, split_meta = verified_parquet(partitions, "splits.parquet", "senamhi-pm25-splits-v1")
    if (
        sha256_file(audit) != grid_meta["input_sha256"]
        or grid_meta["output_sha256"] != split_meta["timeline_sha256"]
    ):
        raise ValueError("El SHA-256 no vincula auditoría, grilla y particiones")
    provenance = {
        "audit_sha256": grid_meta["input_sha256"],
        "timeline_sha256": grid_meta["output_sha256"],
        "splits_sha256": split_meta["output_sha256"],
        "unit_basis": "inferred_accepted_by_project_lead",
        "interval_position": "unknown",
        "quality": "unknown",
    }
    with duckdb.connect(config={"threads": 2}) as db:
        db.execute("SET TimeZone = 'UTC'")
        sources = db.execute(
            "SELECT DISTINCT provenance.source_id, provenance.sha256 FROM read_parquet(?)",
            [str(audit)],
        ).fetchall()
        if len(sources) != 1 or sources[0][0] != "senamhi-lima-csv":
            raise ValueError("La auditoría requiere una exportación de SENAMHI")
        source_sha = sources[0][1]
        if not synthetic:
            policy = json.loads(
                (ROOT / "metadata/benchmark-selection.json").read_text(encoding="utf-8")
            )
            if source_sha != policy["approval"]["input_sha256"]:
                raise ValueError("El original difiere de la selección operativa aprobada")
        metadata = benchmark_metadata(source_sha, version, synthetic=synthetic, sample=bool(limit))
        dataset = TimeFDataset(metadata=metadata)
        series_by_id = {}
        for row in db.execute(
            """
            SELECT series_id, min(station_key), min(observed_at)::VARCHAR,
                   list(value ORDER BY observed_at), count(DISTINCT station_key),
                   count(DISTINCT observed_at),
                   date_diff('hour', min(observed_at), max(observed_at)) + 1
            FROM read_parquet(?) WHERE parameter_raw = 'PM2_5' AND unit = 'ug/m3'
            GROUP BY series_id ORDER BY series_id
            """,
            [str(grid)],
        ).fetchall():
            series_id, station_key, start, values, stations, unique, span = row
            if stations != 1 or len(values) != unique or unique != span:
                raise ValueError("La grilla requiere una estación y una casilla por hora")
            series_by_id[series_id] = HourlySeries(
                station_key, datetime.fromisoformat(start), pa.array(values, type=pa.float64())
            )
        db.read_parquet(str(splits)).create_view("splits")
        invalid = db.execute(
            """
            SELECT count(*) - count(DISTINCT window_id),
                   count(*) FILTER (WHERE NOT coalesce(CASE split
                       WHEN 'train' THEN target_end < ?::TIMESTAMPTZ
                       WHEN 'validation' THEN history_start >= ?::TIMESTAMPTZ
                                              AND target_end < ?::TIMESTAMPTZ
                       WHEN 'test' THEN history_start >= ?::TIMESTAMPTZ
                       WHEN 'purged' THEN true
                       ELSE false END, false))
            FROM splits
            """,
            [
                split_meta["validation_start"],
                split_meta["validation_start"],
                split_meta["test_start"],
                split_meta["test_start"],
            ],
        ).fetchone()
        if invalid != (0, 0):
            raise ValueError("Hay ventanas duplicadas o con fugas entre particiones")
        selection = "SELECT * FROM splits WHERE split <> 'purged'"
        if limit is not None:
            selection = f"""
                SELECT * EXCLUDE (bucket) FROM (
                    SELECT *, ntile(?) OVER (
                       PARTITION BY station_key, split ORDER BY origin_at, window_id
                    ) AS bucket FROM ({selection})
                )
                QUALIFY row_number() OVER (
                    PARTITION BY station_key, split, bucket ORDER BY origin_at, window_id
                ) = 1
            """
        batches = db.execute(
            f"{selection} ORDER BY series_id, origin_at, window_id",
            [] if limit is None else [limit],
        ).to_arrow_reader(batch_size=4096)
        for batch in batches:
            for window in batch.to_pylist():
                add_window_task(
                    dataset,
                    series_by_id[window["series_id"]],
                    window,
                    history=split_meta["history_hours"],
                    horizon=split_meta["horizon_hours"],
                    provenance=provenance,
                )
    if {task.split for task in dataset.tasks} != set(PARTITIONS):
        raise ValueError("Se requieren tareas en entrenamiento, validación y prueba")
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--splits", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--limit-per-station-split", type=int)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    dataset = build_benchmark(
        args.timeline,
        args.splits,
        args.audit,
        version=args.version,
        limit=args.limit_per_station_split,
        synthetic=args.synthetic,
    )
    release = dataset.write(path=args.registry)
    if not args.synthetic:
        shutil.copyfile(ROOT / "DATA_ATTRIBUTION.md", release / "DATA_ATTRIBUTION.md")
    with TimeFReader.open(release) as reader:
        reader.verify()
    print(f"Tareas TimeF verificadas: {len(dataset.tasks)} en {release}")


if __name__ == "__main__":
    main()
