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
