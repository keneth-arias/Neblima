from datetime import datetime

import duckdb
import pytest

from airaware.senamhi_exploration import build_view, normalize_name


def fixture(c):
    c.execute("""CREATE TABLE base AS SELECT 's' series_id,'s' station_key,'ESTACION' station_label,
        'DISTRITO_UNO' DISTRITO,'lima' geography,true hourly,NULL::TIMESTAMP end_ts,
        TIMESTAMP '2024-01-01'+i*INTERVAL '1 hour' ts,
        CASE WHEN i<17 OR (i>=24 AND i<42) THEN '10' ELSE '' END PM2_5,
        '20' PM10,'30' NO2 FROM range(48) t(i)""")


def test_daily_completeness_and_per_signal_conflicts_do_not_impute():
    with duckdb.connect() as c:
        fixture(c)
        c.execute(
            "INSERT INTO base SELECT * REPLACE('999' AS PM10) FROM base "
            "WHERE ts=TIMESTAMP '2024-01-01'"
        )
        result = build_view(c, "PM2_5", 0)
        daily = c.execute("SELECT valid_hours,daily_mean FROM daily ORDER BY day").fetchall()
        assert daily == [(17, None), (18, 10.0)]
        assert result["expected_hours"] == 48 and result["valid_hours"] == 35
        assert result["daily_eligible"] == 1
        assert c.execute("SELECT count(*) FROM hourly WHERE value IS NULL").fetchone() == (13,)
        build_view(c, "PM10", 0)
        assert c.execute("SELECT valid_hours FROM daily ORDER BY day").fetchall() == [(23,), (24,)]


def test_clock_hypothesis_moves_day_boundaries_without_changing_source():
    with duckdb.connect() as c:
        fixture(c)
        build_view(c, "PM10", -5)
        assert c.execute("SELECT count(*) FROM hourly").fetchone() == (72,)
        assert c.execute("SELECT min(clock_ts) FROM hourly").fetchone() == (datetime(2023, 12, 31),)
        assert c.execute("SELECT min(ts) FROM base").fetchone() == (datetime(2024, 1, 1),)
        with pytest.raises(ValueError):
            build_view(c, "PM10", 3)


def test_station_without_measurements_is_retained_and_zero_is_valid():
    with duckdb.connect() as c:
        fixture(c)
        c.execute("UPDATE base SET PM2_5=''")
        assert build_view(c, "PM2_5", 0)["valid_hours"] == 0
        assert c.execute("SELECT count(*) FROM daily WHERE daily_mean IS NULL").fetchone() == (2,)
        c.execute("UPDATE base SET PM2_5='0'")
        assert build_view(c, "PM2_5", 0)["valid_hours"] == 48
        assert c.execute("SELECT max(daily_mean) FROM daily").fetchone() == (0.0,)


def test_years_and_names_are_not_pooled_or_used_as_station_identity():
    assert normalize_name("  JESÚS_MARÍA  ") == "JESUS MARIA"
    assert normalize_name(None) is None
    with duckdb.connect() as c:
        fixture(c)
        c.execute(
            "INSERT INTO base SELECT * REPLACE(ts+INTERVAL '1 year' AS ts,'40' AS PM10) FROM base"
        )
        build_view(c, "PM10", 0)
        assert c.execute("SELECT year,mean FROM annual ORDER BY year").fetchall() == [
            (2024, 20.0),
            (2025, 40.0),
        ]
