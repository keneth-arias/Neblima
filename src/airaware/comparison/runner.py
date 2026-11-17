"""Comparar originales locales verificados y publicar diagnósticos completos de forma atómica."""

import hashlib
import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import duckdb

from airaware.comparison.inputs import digest, load_source, prepare_points
from airaware.comparison.metrics import common_coverage, count_windows, records, score
from airaware.comparison.models import Policy
from airaware.profiling.engine import ProfileSpec

READINESS = {
    "source_id": "VARCHAR",
    "input_sha256": "VARCHAR",
    "policy_sha256": "VARCHAR",
    "geography": "VARCHAR",
    "signal": "VARCHAR",
    "series_id": "VARCHAR",
    "station_key": "VARCHAR",
    "station_label": "VARCHAR",
    "series_context": "VARCHAR",
    "history_hours": "BIGINT",
    "horizon_hours": "BIGINT",
    "candidate_origins": "BIGINT",
    "history_missing": "BIGINT",
    "future_missing": "BIGINT",
    "structural_complete": "BIGINT",
    "scientific_valid_windows": "BIGINT",
    "accepted_forecasting_windows": "BIGINT",
    "blockers": "VARCHAR",
    "first_clock": "TIMESTAMP",
    "last_clock": "TIMESTAMP",
}
OVERLAP = {
    "geography": "VARCHAR",
    "signal": "VARCHAR",
    "left_source": "VARCHAR",
    "right_source": "VARCHAR",
    "raw_clock_intersection": "BIGINT",
    "scientific_intersection": "BIGINT",
    "reason": "VARCHAR",
    "policy_sha256": "VARCHAR",
}


def _write(c, rows, schema, destination: Path):
    scratch = destination.with_suffix(".json")
    scratch.write_text(json.dumps(rows, default=str, ensure_ascii=False))
    c.execute(
        "CREATE OR REPLACE TEMP TABLE export_rows AS SELECT * "
        "FROM read_json(?,format='array',columns=?)",
        [str(scratch), schema],
    )
    c.execute("COPY export_rows TO ? (FORMAT PARQUET,COMPRESSION ZSTD)", [str(destination)])
    scratch.unlink()


def compare(specs: list[ProfileSpec], policy: Policy, output_root: Path) -> Path:
    """Preserva el reloj fuente; no elige una fuente con bloqueos científicos."""
    if not specs or len({s.source_id for s in specs}) != len(specs):
        raise ValueError("Fuentes vacías o duplicadas")
    if set(policy.blockers) != {s.source_id for s in specs}:
        raise ValueError("Declarar elegibilidad/bloqueos de cada fuente explícitamente")
    if any(output_root.resolve().is_relative_to(s.raw_root.resolve()) for s in specs):
        raise ValueError("Los informes no pueden escribirse dentro de raw")
    approved = policy.operating_selection
    if approved is not None:
        matches = [s for s in specs if s.source_id == approved.source_id]
        if len(matches) != 1 or matches[0].sha256 != approved.input_sha256:
            raise ValueError("La aprobación no corresponde al original seleccionado")
        if not set(policy.blockers[approved.source_id]).issubset(approved.accepted_unknowns):
            raise ValueError("Hay bloqueos no aceptados por la política operativa")
    policy_json = policy.model_dump_json()
    policy_hash = hashlib.sha256(policy_json.encode()).hexdigest()
    output_root.mkdir(parents=True, exist_ok=True)
    pending = Path(tempfile.mkdtemp(prefix=".pending-", dir=output_root))
    c = None
    try:
        c = duckdb.connect(
            str(pending / "work.duckdb"),
            config={
                "memory_limit": "768MB",
                "threads": 2,
                "temp_directory": str(pending / "spill"),
                "max_temp_directory_size": "10GB",
                "autoload_known_extensions": False,
                "autoinstall_known_extensions": False,
            },
        )
        c.execute("""CREATE TABLE all_points(source_id VARCHAR,geography VARCHAR,signal VARCHAR,
            series_id VARCHAR,ts TIMESTAMP)""")
        readiness, summaries, inputs = [], [], []
        for spec in specs:
            original = load_source(c, spec)
            inputs.append((original, spec.sha256))
            blockers = policy.blockers[spec.source_id]
            for geography in policy.geographies:
                for signal in policy.signals:
                    field = (
                        ("PM2_5" if spec.kind == "senamhi" else "PM2.5")
                        if signal == "pm25"
                        else "PM10"
                    )
                    operating_accepted = bool(
                        approved is not None
                        and approved.source_id == spec.source_id
                        and approved.geography == geography
                        and approved.signal == signal
                    )
                    trace = prepare_points(c, field, geography)
                    common = common_coverage(c, policy.target_stations or 1)
                    common["quorum_stations"] = policy.target_stations or 1
                    total = c.execute("SELECT count(*) FROM base").fetchone()
                    assert total is not None
                    assert (
                        sum(
                            trace.get(k, 0)
                            for k in (
                                "outside",
                                "period",
                                "clock",
                                "value",
                                "ambiguous",
                                "accepted_rows",
                            )
                        )
                        == total[0]
                    )
                    c.execute(
                        "INSERT INTO all_points SELECT ?,?,?,series_id,ts FROM points",
                        [spec.source_id, geography, signal],
                    )
                    series = records(
                        c,
                        """SELECT DISTINCT series_id,station_key,station_label,
                      series_context FROM base WHERE geography=? ORDER BY series_id""",
                        [geography],
                    )
                    extent = records(
                        c,
                        """WITH ordered AS (SELECT *,ts-row_number() OVER(
                      PARTITION BY series_id ORDER BY ts)*INTERVAL '1 hour' run FROM points),
                      runs AS (SELECT series_id,run,count(*) n FROM ordered GROUP BY series_id,run)
                      SELECT coalesce(max(n),0) longest_run FROM runs""",
                    )[0]["longest_run"]
                    for h in policy.histories:
                        for f in policy.horizons:
                            windows = {r["series_id"]: r for r in count_windows(c, h, f)}
                            complete, candidates, station_keys = 0, 0, set()
                            for s in series:
                                w = windows.get(s["series_id"], {})
                                n = w.get("complete", 0)
                                assert w.get("candidates", 0) == n + w.get(
                                    "history_missing", 0
                                ) + w.get("future_missing", 0)
                                if n:
                                    station_keys.add(s["station_key"])
                                complete += n
                                candidates += w.get("candidates", 0)
                                readiness.append(
                                    dict(
                                        source_id=spec.source_id,
                                        input_sha256=spec.sha256,
                                        policy_sha256=policy_hash,
                                        geography=geography,
                                        signal=signal,
                                        **s,
                                        history_hours=h,
                                        horizon_hours=f,
                                        candidate_origins=w.get("candidates", 0),
                                        history_missing=w.get("history_missing", 0),
                                        future_missing=w.get("future_missing", 0),
                                        structural_complete=n,
                                        scientific_valid_windows=None
                                        if blockers or operating_accepted
                                        else n,
                                        accepted_forecasting_windows=n
                                        if operating_accepted
                                        else None,
                                        blockers=json.dumps(blockers),
                                        first_clock=w.get("first_clock"),
                                        last_clock=w.get("last_clock"),
                                    )
                                )
                            components = None
                            if (
                                policy.target_stations is not None
                                and policy.target_months is not None
                            ):
                                denominator = (
                                    policy.target_stations
                                    * policy.target_months
                                    * policy.hours_per_month
                                )
                                components = [
                                    min(complete / denominator, 1),
                                    complete / candidates if candidates else 0,
                                    min(len(station_keys) / policy.target_stations, 1),
                                    min(
                                        extent / (policy.target_months * policy.hours_per_month), 1
                                    ),
                                    0.5 if blockers else 1,
                                ]
                            eligible = not blockers and complete > 0
                            summaries.append(
                                dict(
                                    source_id=spec.source_id,
                                    geography=geography,
                                    signal=signal,
                                    history_hours=h,
                                    horizon_hours=f,
                                    structural_complete=complete,
                                    accepted_forecasting_windows=complete
                                    if operating_accepted
                                    else None,
                                    candidate_origins=candidates,
                                    stations_with_windows=len(station_keys),
                                    longest_run_hours=extent,
                                    components=components,
                                    scientific_score=score(
                                        components, eligible=eligible, weights=policy.weights
                                    )
                                    if components is not None
                                    else None,
                                    sensitivity_equal=score(
                                        components, eligible=eligible, weights=(0.2,) * 5
                                    )
                                    if components is not None
                                    else None,
                                    blockers=blockers,
                                    rows_trace=trace,
                                    common_coverage=common,
                                )
                            )
            if digest(original) != spec.sha256:
                raise ValueError("El original cambió durante el conteo")
        overlap = []
        for i, left in enumerate(specs):
            for right in specs[i + 1 :]:
                for geo in policy.geographies:
                    for signal in policy.signals:
                        n = c.execute(
                            """SELECT count(*) FROM (
                          SELECT DISTINCT ts FROM all_points
                            WHERE source_id=? AND geography=? AND signal=?
                          INTERSECT SELECT DISTINCT ts FROM all_points
                            WHERE source_id=? AND geography=? AND signal=?)""",
                            [left.source_id, geo, signal, right.source_id, geo, signal],
                        ).fetchone()
                        assert n is not None
                        overlap.append(
                            dict(
                                geography=geo,
                                signal=signal,
                                left_source=left.source_id,
                                right_source=right.source_id,
                                raw_clock_intersection=n[0],
                                scientific_intersection=None,
                                reason="cross_source_clock_compatibility_unverified",
                                policy_sha256=policy_hash,
                            )
                        )
        _write(c, readiness, READINESS, pending / "forecasting-readiness.parquet")
        _write(c, overlap, OVERLAP, pending / "source-overlap.parquet")
        c.close()
        c = None
        for name in ("work.duckdb", "work.duckdb.wal"):
            (pending / name).unlink(missing_ok=True)
        if (pending / "spill").exists():
            shutil.rmtree(pending / "spill")
        selected = sorted({s["source_id"] for s in summaries if s["scientific_score"] is not None})
        if approved is not None and not any(s["accepted_forecasting_windows"] for s in summaries):
            raise ValueError("La selección aprobada no tiene ventanas completas")
        summary = dict(
            policy=policy.model_dump(mode="json"),
            policy_sha256=policy_hash,
            selection_status="selected_under_operating_policy"
            if approved
            else ("blocked" if not selected else "eligible_candidates_require_review"),
            selected_source=approved.source_id if approved else None,
            selected_signal=approved.signal if approved else None,
            selected_geography=approved.geography if approved else None,
            sources=summaries,
            overlap=overlap,
        )
        (pending / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        manifest = dict(
            algorithm=policy.version,
            policy_sha256=policy_hash,
            verified_at_utc=datetime.now(UTC).isoformat(),
            duckdb_version=duckdb.__version__,
            profile_specs=[s.model_dump(mode="json") for s in specs],
            inputs_unchanged=True,
            files={
                p.name: dict(sha256=digest(p), size_bytes=p.stat().st_size)
                for p in pending.iterdir()
                if p.is_file()
            },
        )
        # Verifica también fuentes procesadas antes mientras se analizó la siguiente.
        if any(digest(p) != expected for p, expected in inputs):
            raise ValueError("Un original cambió antes de publicar")
        (pending / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        )
        destination = output_root / ("comparison-" + uuid4().hex)
        os.rename(pending, destination)
        return destination
    finally:
        if c is not None:
            c.close()
        if pending.exists():
            shutil.rmtree(pending)
