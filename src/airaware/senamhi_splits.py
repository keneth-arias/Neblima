"""Particiones retrospectivas UTC con purga de ventanas completas."""

import json
from pathlib import Path
from typing import Annotated

import duckdb
import typer

from airaware.derived_artifacts import new_bundle, sha256_file
from airaware.senamhi_timeline import HOURS_FILE, TIMELINE_VERSION
from airaware.senamhi_windows import WINDOWS_FILE, WINDOWS_VERSION

SPLITS_FILE = "splits.parquet"
SPLITS_VERSION = "senamhi-pm25-splits-v1"

ASSIGN = """
WITH availability AS (
    SELECT series_id, observed_at,
           max(available_at) OVER (
               PARTITION BY series_id ORDER BY observed_at
               ROWS BETWEEN {lookback} PRECEDING AND CURRENT ROW
           ) AS last_publication
    FROM read_parquet(?) WHERE parameter_raw = 'PM2_5' AND unit = 'ug/m3'
), cuts AS (
    SELECT ?::TIMESTAMPTZ AS validation_start, ?::TIMESTAMPTZ AS test_start
), classified AS (
    SELECT windows.*,
           CASE
               WHEN target_end < validation_start THEN 'train'
               WHEN history_start >= validation_start AND target_end < test_start
                    THEN 'validation'
               WHEN history_start >= test_start THEN 'test'
               ELSE 'purged'
           END AS time_split,
           coalesce(last_publication > origin_at, false) AS late
    FROM windows CROSS JOIN cuts
    JOIN availability ON windows.series_id = availability.series_id AND origin_at = observed_at
)
SELECT * EXCLUDE (time_split, late),
       CASE WHEN late THEN 'purged' ELSE time_split END AS split,
       CASE WHEN time_split = 'purged' THEN 'crosses_cutoff'
            WHEN late THEN 'late_publication' END AS purge_reason
FROM classified
"""


def freeze_splits(windows_dir: Path, timeline: Path, output: Path) -> None:
    """Asignar cada ventana a un intervalo UTC disjunto o a la lista de purga."""
    windows = windows_dir / WINDOWS_FILE
    hours = timeline / HOURS_FILE
    source = json.loads((windows_dir / "manifest.json").read_text(encoding="utf-8"))
    grid = json.loads((timeline / "manifest.json").read_text(encoding="utf-8"))
    windows_hash = sha256_file(windows)
    hours_hash = sha256_file(hours)
    if (
        source["version"] != WINDOWS_VERSION
        or grid["version"] != TIMELINE_VERSION
        or source["output_sha256"] != windows_hash
        or grid["output_sha256"] != hours_hash
        or source["input_sha256"] != hours_hash
    ):
        raise ValueError("Versión, vínculo o SHA-256 distinto del manifiesto")
    history = source["history_hours"]
    if type(history) is not int or not 1 <= history <= 168:
        raise ValueError("Historia fuera del contrato")

    with new_bundle(output) as staging, duckdb.connect(config={"threads": 2}) as db:
        db.execute("SET TimeZone = 'UTC'")
        db.read_parquet(str(windows), hive_partitioning=False).create_view("windows")
        cutoffs = db.execute("""
            SELECT quantile_disc(origin_at, 0.70)::VARCHAR,
                   quantile_disc(origin_at, 0.85)::VARCHAR, count(*), count(DISTINCT window_id)
            FROM windows
        """).fetchone()
        assert cutoffs is not None
        validation, test, total, unique = cutoffs
        if not validation or not test or validation >= test or total != unique:
            raise ValueError("Ventanas duplicadas o cobertura insuficiente para dos cortes UTC")
        db.execute(
            "CREATE TEMP TABLE assigned AS " + ASSIGN.format(lookback=history - 1),
            [str(hours), validation, test],
        )
        counts = db.execute("""
            SELECT station_key, split, purge_reason, count(*) AS windows
            FROM assigned GROUP BY ALL ORDER BY ALL
        """).fetchall()
        if sum(row[3] for row in counts) != total:
            raise ValueError("La grilla no reconcilia con las ventanas")
        if {row[1] for row in counts} - {"purged"} != {"train", "validation", "test"}:
            raise ValueError("Cobertura insuficiente después de purgar")
        if sha256_file(windows) != windows_hash or sha256_file(hours) != hours_hash:
            raise ValueError("El insumo cambió durante la partición")
        db.execute(
            """COPY (SELECT * FROM assigned ORDER BY series_id, origin_at, window_id)
               TO ? (FORMAT PARQUET)""",
            [str(staging / SPLITS_FILE)],
        )
        manifest = {
            "version": SPLITS_VERSION,
            "input_sha256": windows_hash,
            "timeline_sha256": hours_hash,
            "output_sha256": sha256_file(staging / SPLITS_FILE),
            "validation_start": validation,
            "test_start": test,
            "history_hours": history,
            "horizon_hours": source["horizon_hours"],
            "step_hours": source["step_hours"],
            "availability_policy": "retrospective_with_known_delays_purged",
            "counts": [
                {"station_key": key, "split": split, "purge_reason": reason, "windows": count}
                for key, split, reason, count in counts
            ],
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def split(
    input: Annotated[Path, typer.Option(help="Carpeta con ventanas completas.")],
    timeline: Annotated[Path, typer.Option(help="Grilla que dio origen a las ventanas.")],
    output: Annotated[Path, typer.Option(help="Carpeta nueva para las particiones.")],
) -> None:
    """Congelar particiones cronológicas para la evaluación retrospectiva."""
    try:
        freeze_splits(input, timeline, output)
    except (OSError, ValueError, KeyError, duckdb.Error) as error:
        typer.echo(f"No se pudieron fijar particiones: {error}", err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Particiones SENAMHI: {output}")
