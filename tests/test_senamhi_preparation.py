from datetime import UTC, datetime

import pytest

from airaware.senamhi_preparation import load_policy, observation, timestamp_utc


def test_timestamp_is_utc_not_lima_and_does_not_truncate_minutes():
    assert timestamp_utc("20150101", "50000") == datetime(2015, 1, 1, 5, tzinfo=UTC)
    assert timestamp_utc("20240531", "153045").minute == 30
    for hour in ("240000", "126000", "1234567", "-1"):
        with pytest.raises(ValueError):
            timestamp_utc("20240101", hour)


def test_inferred_units_unknown_quality_and_interval_do_not_block_observation():
    policy = load_policy()
    for signal in ("PM10", "PM2_5", "NO2"):
        row = {"FECHA": "20150101", "HORA": "50000", signal: "12.5", "ESTACION": "CAMPO_DE_MARTE"}
        out = observation(row, signal, 2, policy)
        assert out.observed_at == datetime(2015, 1, 1, 5, tzinfo=UTC)
        assert out.unit == "ug/m3" and out.unit_raw is None
        assert out.start is None and out.end is None and out.quality == "unknown"
        assert out.raw_fields == row
        assert out.value == 12.5
        assert "units_inferred" in "|".join(out.semantic_evidence)


@pytest.mark.parametrize(
    ("token", "status"),
    [
        ("", "missing"),
        ("ND", "unresolved"),
        ("<1", "censored"),
        ("NaN", "nonfinite"),
        ("0", "finite"),
    ],
)
def test_missing_censored_unknown_and_zero_remain_distinct(token, status):
    row = {"FECHA": "20240101", "HORA": "0", "PM2_5": token}
    result = observation(row, "PM2_5", 2, load_policy())
    assert result.value_status == status
    assert result.value_raw == token


def test_current_comparison_has_no_size_quota_or_size_score():
    from pathlib import Path

    import yaml

    from airaware.comparison.models import Policy

    policy = Policy.model_validate(yaml.safe_load(Path("configs/benchmark.yaml").read_text()))
    assert policy.version == "comparison-v2"
    assert policy.target_stations is None and policy.target_months is None
    with pytest.raises(ValueError):
        Policy(version="comparison-v2", target_stations=4, target_months=24)
