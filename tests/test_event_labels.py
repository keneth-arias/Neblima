from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from airaware.event_labels import HourlyPM25, SeriesContext, label_window, load_policy

LIMA = ZoneInfo("America/Lima")
START = datetime(2024, 1, 1, tzinfo=LIMA)


def context(**changes):
    return SeriesContext(
        **{
            "source_id": "fixture",
            "station_id": "station-1",
            "unit": "ug/m3",
            "timezone": "America/Lima",
            "method": "automatic_hourly",
            "semantic_evidence": "fixture:semantics-v1",
            **changes,
        }
    )


def hours(value=50.0):
    return [HourlyPM25(START + timedelta(hours=i + 1), value, True, f"obs-{i}") for i in range(24)]


def classify(records, kind="forecast_24h", start=START, ctx=None):
    return label_window(
        records,
        start=start,
        kind=kind,
        context=ctx or context(),
        policy=load_policy(Path("configs/thresholds.yaml")),
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [(49.999, "not_above_reference"), (50.0, "not_above_reference"), (50.001, "above_reference")],
)
def test_threshold_is_strict_and_not_rounded(value, expected):
    result = classify(hours(value))
    assert result.label == expected
    assert result.mean_ug_m3 == value
    assert result.valid_hours == 24


@pytest.mark.parametrize(
    ("n", "kind", "expected"),
    [
        (17, "calendar_day", "not_evaluable"),
        (18, "calendar_day", "above_reference"),
        (23, "forecast_24h", "not_evaluable"),
        (24, "forecast_24h", "above_reference"),
    ],
)
def test_forecast_and_calendar_have_different_completeness(n, kind, expected):
    result = classify(hours(60)[:n], kind)
    assert result.label == expected
    assert result.valid_hours == n
    assert (result.mean_ug_m3 is None) == (expected == "not_evaluable")


@pytest.mark.parametrize("bad", [None, -1, float("nan"), float("inf"), float("-inf")])
def test_invalid_measurements_do_not_become_negative_labels(bad):
    records = hours()
    records[7] = replace(records[7], value=bad)
    result = classify(records)
    assert result.label == "not_evaluable" and result.valid_hours == 23
    assert result.reason == "insufficient_valid_hours"


def test_invalid_quality_is_excluded_and_cannot_use_a_high_value():
    records = hours(40)
    records[0] = replace(records[0], value=10000, quality_valid=False)
    result = classify(records, "calendar_day")
    assert result.mean_ug_m3 == 40 and result.label == "not_above_reference"


def test_duplicate_instants_are_rejected_even_with_different_offsets():
    records = hours()
    records.append(replace(records[0], end=records[0].end.astimezone(UTC)))
    with pytest.raises(ValueError, match="duplicad"):
        classify(records)


def test_outside_hour_and_naive_or_unaligned_timestamps_are_rejected():
    for end in [
        START,
        START + timedelta(hours=25),
        START + timedelta(minutes=90),
        START.replace(tzinfo=None) + timedelta(hours=1),
    ]:
        with pytest.raises(ValueError):
            classify([replace(hours()[0], end=end)])


def test_calendar_requires_midnight_but_forecast_can_cross_days():
    start = START + timedelta(hours=12)
    records = [replace(h, end=h.end + timedelta(hours=12)) for h in hours()]
    assert classify(records, start=start).label == "not_above_reference"
    with pytest.raises(ValueError, match="medianoche"):
        classify(records, "calendar_day", start=start)


def test_hour_ending_midnight_belongs_to_preceding_day_and_preserves_lineage():
    result = classify(list(reversed(hours(60))), "calendar_day")
    assert result.calendar_date == START.date()
    assert result.end == START + timedelta(days=1)
    assert result.observation_ids == tuple(f"obs-{i}" for i in range(24))
    assert result.context == context()
    assert result.policy_id == "pe-pm25-reference-2017-v1"


def test_utc_inputs_produce_same_calendar_day():
    expected = classify(hours(), "calendar_day")
    result = classify(
        [replace(h, end=h.end.astimezone(UTC)) for h in hours()],
        "calendar_day",
        start=START.astimezone(UTC),
    )
    assert result == expected


@pytest.mark.parametrize(
    "changes",
    [{"unit": "unknown"}, {"timezone": ""}, {"semantic_evidence": ""}, {"method": "manual_24h"}],
)
def test_unknown_or_unsupported_semantics_are_rejected(changes):
    with pytest.raises(ValueError):
        classify(hours(), ctx=context(**changes))


def test_policy_cannot_silently_relax_forecast_targets(tmp_path):
    original = Path("configs/thresholds.yaml").read_text()
    file = tmp_path / "policy.yaml"
    file.write_text(
        original.replace("forecast_min_valid_hours: 24", "forecast_min_valid_hours: 18")
    )
    with pytest.raises(ValueError):
        load_policy(file)


def test_duplicate_alias_in_a_full_window_cannot_replace_a_missing_hour():
    records = hours()
    records[1] = replace(records[0], end=records[0].end.astimezone(UTC), observation_id="other")
    with pytest.raises(ValueError, match="duplicad"):
        classify(records)


def test_all_missing_is_unknown_even_for_calendar_day():
    result = classify(hours(None), "calendar_day")
    assert result.label == "not_evaluable" and result.mean_ug_m3 is None
    assert result.valid_hours == 0 and result.valid_observation_ids == ()
    assert len(result.observation_ids) == 24


def test_arithmetic_mean_of_targets_is_used_not_any_individual_exceedance():
    records = hours(0)
    records[0] = replace(records[0], value=1200)
    result = classify(records)
    assert result.mean_ug_m3 == 50 and result.label == "not_above_reference"


def test_invalid_observation_identity_and_quality_are_rejected():
    for changes in [{"observation_id": ""}, {"observation_id": "obs-1"}, {"quality_valid": 1}]:
        records = hours()
        records[0] = replace(records[0], **changes)
        with pytest.raises(ValueError):
            classify(records)


def test_unknown_timezone_fails_with_a_clear_validation_error():
    with pytest.raises(ValueError, match="zona"):
        classify(hours(), ctx=context(timezone="Not/A_Zone"))


def test_non_24_hour_calendar_days_are_not_silently_reinterpreted():
    start = datetime(2024, 3, 10, tzinfo=ZoneInfo("America/New_York"))
    with pytest.raises(ValueError, match="24 horas"):
        classify([], "calendar_day", start=start, ctx=context(timezone="America/New_York"))
