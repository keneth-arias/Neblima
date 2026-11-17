from datetime import datetime, timedelta

import duckdb
import pytest

from airaware.comparison.metrics import count_windows, score


def test_complete_run_has_exact_inclusive_window_counts():
    start = datetime(2024, 1, 1)
    with duckdb.connect() as c:
        c.execute("CREATE TABLE points(series_id VARCHAR,ts TIMESTAMP)")
        c.executemany(
            "INSERT INTO points VALUES (?,?)",
            [("a", start + timedelta(hours=i)) for i in reversed(range(240))],
        )
        result = count_windows(c, 24, 6)[0]
        assert result["candidates"] == 211
        assert result["complete"] == 211
        assert result["history_missing"] == result["future_missing"] == 0
        assert len(count_windows(c, 168, 48)) == 1
        assert count_windows(c, 168, 48)[0]["complete"] == 25


def test_gaps_and_series_boundaries_do_not_fill_each_other():
    start = datetime(2024, 1, 1)
    with duckdb.connect() as c:
        c.execute("CREATE TABLE points(series_id VARCHAR,ts TIMESTAMP)")
        hours = [0, 1, 2, 4, 5, 6, 7]
        c.executemany(
            "INSERT INTO points VALUES (?,?)",
            [("a", start + timedelta(hours=i)) for i in hours]
            + [("b", start + timedelta(hours=3))],
        )
        r = {r["series_id"]: r for r in count_windows(c, 2, 1)}
        assert r["a"]["candidates"] == 6
        assert r["a"]["complete"] == 3
        assert r["a"]["history_missing"] == 2
        assert r["a"]["future_missing"] == 1
        assert r["b"]["complete"] == 0
        assert count_windows(c, 24, 6)[0]["complete"] == 0


def test_no_points_returns_no_fake_series():
    with duckdb.connect() as c:
        c.execute("CREATE TABLE points(series_id VARCHAR,ts TIMESTAMP)")
        assert count_windows(c, 24, 6) == []


def test_score_blocks_unknown_semantics_and_uses_fixed_denominators():
    assert score([1, 1, 1, 1, 1], eligible=False) is None
    assert score([1, 1, 1, 1, 1], eligible=True) == 1
    assert score([1, 0, 0, 0, 0], eligible=True) == 0.35
    with pytest.raises(ValueError):
        score([2, 0, 0, 0, 0], eligible=True)


@pytest.mark.parametrize("history", [24, 48, 72, 168])
@pytest.mark.parametrize("horizon", [6, 12, 24, 48])
def test_all_sixteen_pairs_match_manual_count(history, horizon):
    with duckdb.connect() as c:
        c.execute(
            """CREATE TABLE points AS SELECT 'a' series_id,TIMESTAMP '2024-01-01'
            + i*INTERVAL '1 hour' ts FROM range(240) t(i)"""
        )
        assert count_windows(c, history, horizon)[0]["complete"] == 241 - history - horizon


def test_small_random_grids_match_brute_force():
    import random

    rng = random.Random(11)
    for _ in range(12):
        hours = sorted(rng.sample(range(40), 28))
        h, f = rng.randint(1, 5), rng.randint(1, 4)
        origins = range(min(hours) + h - 1, max(hours) - f + 1)
        good = set(hours)
        histories = [t for t in origins if all(i in good for i in range(t - h + 1, t + 1))]
        complete = [t for t in histories if all(i in good for i in range(t + 1, t + f + 1))]
        with duckdb.connect() as c:
            c.execute("CREATE TABLE points(series_id VARCHAR,ts TIMESTAMP)")
            c.executemany(
                "INSERT INTO points VALUES (?,?)",
                [("a", datetime(2024, 1, 1) + timedelta(hours=i)) for i in hours],
            )
            r = count_windows(c, h, f)[0]
            assert (r["candidates"], r["history_missing"], r["future_missing"], r["complete"]) == (
                len(origins),
                len(origins) - len(histories),
                len(histories) - len(complete),
                len(complete),
            )


def test_row_filters_reconcile_and_conflicts_are_not_resolved_by_order():
    from airaware.comparison.inputs import prepare_points

    with duckdb.connect() as c:
        c.execute("""CREATE TABLE base AS SELECT 'a' series_id,
          TIMESTAMP '2024-01-01' + hr*INTERVAL '1 hour' ts,NULL::TIMESTAMP end_ts,
          geo geography,period hourly,raw PM10 FROM (VALUES
          (0,'lima',true,'1'),(0,'lima',true,'1'),(1,'lima',true,'2'),
          (1,'lima',true,'3'),(2,'lima',true,'NA'),(3,'outside',true,'5'),
          (4,'lima',false,'4')) v(hr,geo,period,raw)""")
        r = prepare_points(c, "PM10", "lima")
        assert r == {
            "outside": 1,
            "period": 1,
            "value": 1,
            "ambiguous": 2,
            "accepted_rows": 2,
            "unique_points": 1,
            "collapsed_repetitions": 1,
        }
        assert c.execute("SELECT value FROM points").fetchall() == [(1.0,)]


def test_an_unknown_clock_is_dropped_before_numeric_filter():
    from airaware.comparison.inputs import prepare_points

    with duckdb.connect() as c:
        c.execute("""CREATE TABLE base AS SELECT 'a' series_id,NULL::TIMESTAMP ts,
        NULL::TIMESTAMP end_ts,'lima' geography,true hourly,'NA' PM10""")
        r = prepare_points(c, "PM10", "lima")
        assert r["clock"] == 1 and r["unique_points"] == 0 and "value" not in r


def test_comparison_run_verifies_input_and_keeps_semantically_blocked_counts_null(tmp_path):
    import json

    from airaware.comparison.models import Policy
    from airaware.comparison.runner import compare
    from tests.test_profiling import fixture

    spec = fixture(tmp_path, [(f"{i:02d}0000", "10") for i in range(24)])
    policy = Policy(
        histories=[24], horizons=[6], signals=["pm25"], blockers={"fixture": ["clock_unverified"]}
    )
    output = compare([spec], policy, tmp_path / "reports")
    summary = json.loads((output / "summary.json").read_text())
    assert summary["sources"][0]["scientific_score"] is None
    with duckdb.connect() as c:
        row = c.execute(
            "select scientific_valid_windows,structural_complete from read_parquet(?) limit 1",
            [str(output / "forecasting-readiness.parquet")],
        ).fetchone()
        assert row == (None, 0)
    assert json.loads((output / "manifest.json").read_text())["inputs_unchanged"]
    assert spec.manifest.exists()


def test_policy_rejects_silent_source_eligibility_and_weights_outside_scale():
    from pydantic import ValidationError

    from airaware.comparison.models import Policy

    with pytest.raises(ValidationError):
        Policy(weights=[0.9, 0.9, 0, 0, 0])


def test_cli_has_offline_comparison_command_and_rejects_missing_configuration(tmp_path):
    from typer.testing import CliRunner

    from airaware.cli import app

    r = CliRunner().invoke(app, ["compare", "run", "--policy", str(tmp_path / "absent.yaml")])
    assert r.exit_code == 1
    assert "No se pudo" in r.output
    assert not (tmp_path / "reports").exists()


def test_common_coverage_counts_distinct_stations_not_contexts():
    from airaware.comparison.metrics import common_coverage

    with duckdb.connect() as c:
        c.execute(
            """CREATE TABLE base AS SELECT * FROM
            (VALUES ('a','s1'),('b','s1'),('c','s2')) v(series_id,station_key)"""
        )
        c.execute("""CREATE TABLE points AS SELECT series_id,
          TIMESTAMP '2024-01-01' + hr*INTERVAL '1 hour' ts
          FROM (VALUES ('a',0),('b',0),('c',0),('a',1),('c',1),('a',3)) v(series_id,hr)""")
        r = common_coverage(c, 2)
        assert r["common_hour_slots"] == 2
        assert r["longest_common_run_hours"] == 2
