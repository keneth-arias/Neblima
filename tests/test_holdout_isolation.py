"""Aislamiento del holdout de estaciones para la evaluación secundaria (#32).

Todas las identidades, fechas y coordenadas son sintéticas y deterministas;
ninguna prueba consulta la red ni lee particiones congeladas reales.
"""

import json
from collections.abc import MutableSequence
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from airaware.benchmarks.holdout import (
    HOLDOUT_PLAN_VERSION,
    HoldoutConfig,
    HoldoutIsolationError,
    HoldoutPlan,
    PeriodUtc,
    assert_isolation,
    plan_holdout,
    summarize_representativity,
    verify_isolation,
)
from airaware.senamhi_splits import SPLITS_VERSION
from airaware.senamhi_timeline import TIMELINE_VERSION

RESERVED_A = "a" * 64
RESERVED_B = "b" * 64
RESERVED_C = "c" * 64
TRAIN_D = "d" * 64
TRAIN_E = "e" * 64
TRAIN_F = "f" * 64

RESERVED_PERIOD = {
    "start": "2023-01-01T00:00:00+00:00",
    "end": "2023-06-30T23:00:00+00:00",
}
EXPECTED_HOURS_PERIOD = 4344


def station(key: str, name: str, latitude: float, longitude: float) -> dict:
    return {
        "station_key": key,
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
    }


def build_config(**overrides) -> dict:
    config = {
        "criterion": "Retención sintética de estaciones para evaluación secundaria nacional",
        "created_at_utc": "2026-11-20T00:00:00+00:00",
        "reserved_stations": [
            station(RESERVED_A, "RESERVA_A", 0.0, 0.0),
            station(RESERVED_B, "RESERVA_B", -12.05, -77.10),
        ],
        "training_stations": [
            station(TRAIN_D, "ENTRENO_D", 0.0, 2.0),
            station(TRAIN_E, "ENTRENO_E", -11.0, -75.0),
        ],
        "reserved_period": RESERVED_PERIOD,
        "min_distance_km": 50.0,
        "min_hours_per_station": 480,
    }
    config.update(overrides)
    return config


def splits_manifest(station_keys: list[str], version: str = SPLITS_VERSION) -> dict:
    counts = [
        {"station_key": key, "split": split, "purge_reason": None, "windows": 10}
        for key in station_keys
        for split in ("train", "validation", "test")
    ]
    return {"version": version, "counts": counts}


def isolated_manifests(**extra) -> dict[str, dict]:
    manifests = {
        "entrenamiento": splits_manifest([TRAIN_D, TRAIN_E]),
        "validación": splits_manifest([TRAIN_D, TRAIN_E]),
        "prueba": splits_manifest([TRAIN_D, TRAIN_E]),
        "preentrenamiento": splits_manifest([TRAIN_D, TRAIN_E]),
    }
    manifests.update(extra)
    return manifests


def disjoint_periods(**overrides) -> dict:
    periods = dict.fromkeys(isolated_manifests(), ("2021-01-01T00:00Z", "2022-12-31T23:00Z"))
    return {**periods, **overrides}


def grid_manifest(observed: dict[str, int], version: str = TIMELINE_VERSION) -> dict:
    counts = [
        {"station_key": key, "parameter_raw": "PM2_5", "status": "observed", "hours": hours}
        for key, hours in observed.items()
    ]
    return {"version": version, "counts": counts}


def test_plan_is_deterministic_and_versioned():
    first = plan_holdout(HoldoutConfig(**build_config()))
    second = plan_holdout(HoldoutConfig(**build_config()))
    assert first == second
    assert first.plan_sha256 == second.plan_sha256
    assert first.version == HOLDOUT_PLAN_VERSION
    payload = first.to_dict()
    assert payload["criterion"] == build_config()["criterion"]
    assert payload["created_at_utc"] == "2026-11-20T00:00:00+00:00"
    assert payload["reserved_period"] == {
        "start": "2023-01-01T00:00:00+00:00",
        "end": "2023-06-30T23:00:00+00:00",
    }
    assert payload["min_distance_km"] == 50.0
    assert payload["min_hours_per_station"] == 480
    assert [item["station_key"] for item in payload["reserved_stations"]] == [
        RESERVED_A,
        RESERVED_B,
    ]
    assert [item["station_key"] for item in payload["training_stations"]] == [TRAIN_D, TRAIN_E]
    assert json.loads(first.to_json()) == payload


def test_plan_hash_changes_with_declared_inputs():
    base = plan_holdout(HoldoutConfig(**build_config()))
    wider = plan_holdout(HoldoutConfig(**build_config(min_distance_km=80.0)))
    later = plan_holdout(HoldoutConfig(**build_config(created_at_utc="2026-11-21T00:00:00+00:00")))
    assert base.plan_sha256 != wider.plan_sha256
    assert base.plan_sha256 != later.plan_sha256


def test_plan_rejects_ambiguous_or_malformed_config():
    shared = station(RESERVED_A, "DUAL", -20.0, -70.0)
    with pytest.raises(ValidationError, match="reservada"):
        HoldoutConfig(**build_config(training_stations=[shared, station(TRAIN_E, "E", 5.0, 5.0)]))
    with pytest.raises(ValidationError):
        HoldoutConfig(**build_config(reserved_stations=[station("z", "CORTA", 0.0, 0.0)]))
    naive = {
        "start": "2023-01-01T00:00:00",
        "end": "2023-06-30T23:00:00",
    }
    with pytest.raises(ValidationError, match="UTC"):
        HoldoutConfig(**build_config(reserved_period=naive))
    inverted = {"start": RESERVED_PERIOD["end"], "end": RESERVED_PERIOD["start"]}
    with pytest.raises(ValidationError):
        HoldoutConfig(**build_config(reserved_period=inverted))
    with pytest.raises(ValidationError):
        HoldoutConfig(**build_config(reserved_stations=[station(RESERVED_A, "A", 95.0, 0.0)]))


def test_station_isolation_passes_without_reserved_keys():
    plan = plan_holdout(HoldoutConfig(**build_config()))
    report = verify_isolation(plan, isolated_manifests(), disjoint_periods())
    assert report["violations"] == []
    assert report["isolated"] is True
    assert_isolation(plan, isolated_manifests(), disjoint_periods())


@pytest.mark.parametrize("label", ["entrenamiento", "validación", "prueba", "preentrenamiento"])
def test_station_isolation_fails_closed_with_detail(label):
    plan = plan_holdout(HoldoutConfig(**build_config()))
    manifests = isolated_manifests()
    manifests[label] = splits_manifest([TRAIN_D, TRAIN_E, RESERVED_A])
    report = verify_isolation(plan, manifests, disjoint_periods())
    leakage = [
        item
        for item in report["violations"]
        if item["type"] == "station_leakage" and item["manifest"] == label
    ]
    assert report["isolated"] is False
    assert leakage == [
        {
            "type": "station_leakage",
            "manifest": label,
            "station_key": RESERVED_A,
            "split": split,
        }
        for split in ("train", "validation", "test")
    ]
    with pytest.raises(HoldoutIsolationError) as raised:
        assert_isolation(plan, manifests, disjoint_periods())
    assert str(RESERVED_A) in str(raised.value)
    assert "train" in str(raised.value)
    assert label in str(raised.value)
    assert raised.value.violations == report["violations"]


def test_station_isolation_rejects_manifests_outside_the_contract():
    plan = plan_holdout(HoldoutConfig(**build_config()))
    stale = isolated_manifests(entrenamiento=splits_manifest([TRAIN_D], version="otro-v0"))
    with pytest.raises(HoldoutIsolationError, match="contrato"):
        assert_isolation(plan, stale, disjoint_periods())
    incomplete = isolated_manifests(prueba={"version": SPLITS_VERSION})
    with pytest.raises(HoldoutIsolationError, match="counts"):
        assert_isolation(plan, incomplete, disjoint_periods())


def test_spatial_isolation_enforces_declared_threshold():
    close = HoldoutConfig(
        **build_config(
            reserved_stations=[station(RESERVED_A, "CERCA", 0.0, 0.0)],
            training_stations=[station(TRAIN_D, "D", 0.0, 1.0)],
            min_distance_km=150.0,
        )
    )
    plan = plan_holdout(close)
    manifests = {label: splits_manifest([TRAIN_D]) for label in isolated_manifests()}
    report = verify_isolation(plan, manifests, disjoint_periods())
    assert report["isolated"] is False
    assert report["violations"] == [
        {
            "type": "spatial_proximity",
            "reserved_station_key": RESERVED_A,
            "training_station_key": TRAIN_D,
            "distance_km": pytest.approx(111.195, abs=0.05),
            "threshold_km": 150.0,
        }
    ]
    with pytest.raises(HoldoutIsolationError, match="dista"):
        assert_isolation(plan, manifests, disjoint_periods())
    farther = close.model_copy(update={"min_distance_km": 100.0})
    same_geometry = plan_holdout(farther)
    assert verify_isolation(same_geometry, manifests, disjoint_periods())["violations"] == []


def test_temporal_isolation_rejects_overlap_and_inclusive_boundary():
    plan = plan_holdout(HoldoutConfig(**build_config()))
    inside = {
        "preentrenamiento": (
            datetime(2022, 6, 1, tzinfo=UTC),
            datetime(2023, 2, 15, 12, tzinfo=UTC),
        )
    }
    report = verify_isolation(plan, isolated_manifests(), periods=disjoint_periods(**inside))
    assert report["isolated"] is False
    assert report["violations"] == [
        {
            "type": "temporal_overlap",
            "period_label": "preentrenamiento",
            "period": {
                "start": "2022-06-01T00:00:00+00:00",
                "end": "2023-02-15T12:00:00+00:00",
            },
            "reserved_period": {
                "start": "2023-01-01T00:00:00+00:00",
                "end": "2023-06-30T23:00:00+00:00",
            },
        }
    ]
    with pytest.raises(HoldoutIsolationError, match="solapa"):
        assert_isolation(plan, isolated_manifests(), periods=disjoint_periods(**inside))
    touching = {
        "preentrenamiento": (
            datetime(2022, 1, 1, tzinfo=UTC),
            datetime(2023, 1, 1, tzinfo=UTC),
        )
    }
    boundary = verify_isolation(plan, isolated_manifests(), periods=disjoint_periods(**touching))
    assert boundary["isolated"] is False
    assert boundary["violations"][0]["type"] == "temporal_overlap"
    disjoint = {
        "preentrenamiento": (
            datetime(2021, 1, 1, tzinfo=UTC),
            datetime(2022, 12, 31, 23, tzinfo=UTC),
        )
    }
    clear = verify_isolation(plan, isolated_manifests(), periods=disjoint_periods(**disjoint))
    assert clear["violations"] == []
    assert clear["isolated"] is True


def test_temporal_isolation_requires_explicit_utc_periods():
    plan = plan_holdout(HoldoutConfig(**build_config()))
    naive = {"preentrenamiento": (datetime(2022, 1, 1), datetime(2022, 3, 1))}
    with pytest.raises(HoldoutIsolationError, match="UTC"):
        verify_isolation(plan, isolated_manifests(), periods=disjoint_periods(**naive))


def test_representativity_reports_coverage_and_marks_insufficiency():
    reserved = [station(RESERVED_A, "A", 0.0, 0.0), station(RESERVED_B, "B", -12.05, -77.10)]
    plan = plan_holdout(
        HoldoutConfig(
            **build_config(
                reserved_stations=reserved,
                training_stations=[
                    station(TRAIN_D, "D", 0.0, 2.0),
                    station(TRAIN_E, "E", -11.0, -75.0),
                ],
            )
        )
    )
    counts = grid_manifest({RESERVED_A: 600, RESERVED_B: 100})
    counts["counts"].append(
        {"station_key": RESERVED_A, "parameter_raw": "PM2_5", "status": "absent_hour", "hours": 24}
    )
    summary = summarize_representativity(plan, counts)
    assert summary["plan_sha256"] == plan.plan_sha256
    assert summary["expected_hours_per_station"] == EXPECTED_HOURS_PERIOD
    assert summary["minimum_hours_per_station"] == 480
    assert summary["stations"] == [
        {
            "station_key": RESERVED_A,
            "name": "A",
            "latitude": 0.0,
            "longitude": 0.0,
            "available_hours": 600,
            "expected_hours": EXPECTED_HOURS_PERIOD,
            "coverage_ratio": pytest.approx(600 / EXPECTED_HOURS_PERIOD, abs=1e-6),
            "minimum_hours_declared": 480,
            "sufficient": True,
        },
        {
            "station_key": RESERVED_B,
            "name": "B",
            "latitude": -12.05,
            "longitude": -77.10,
            "available_hours": 100,
            "expected_hours": EXPECTED_HOURS_PERIOD,
            "coverage_ratio": pytest.approx(100 / EXPECTED_HOURS_PERIOD, abs=1e-6),
            "minimum_hours_declared": 480,
            "sufficient": False,
        },
    ]
    assert summary["insufficient_station_keys"] == [RESERVED_B]
    assert summary["all_sufficient"] is False
    assert json.dumps(summary, sort_keys=True)


def test_representativity_counts_absent_stations_as_zero_without_inventing_hours():
    reserved = [
        station(RESERVED_A, "A", 0.0, 0.0),
        station(RESERVED_B, "B", -12.05, -77.10),
        station(RESERVED_C, "C", -10.0, -79.0),
    ]
    plan = plan_holdout(
        HoldoutConfig(
            **build_config(
                reserved_stations=reserved,
                training_stations=[station(TRAIN_D, "D", 0.0, 2.0)],
            )
        )
    )
    summary = summarize_representativity(plan, grid_manifest({RESERVED_A: 600}))
    by_key = {item["station_key"]: item for item in summary["stations"]}
    assert by_key[RESERVED_C]["available_hours"] == 0
    assert by_key[RESERVED_C]["sufficient"] is False
    assert summary["insufficient_station_keys"] == [RESERVED_B, RESERVED_C]


def test_representativity_rejects_grid_outside_the_contract():
    plan = plan_holdout(HoldoutConfig(**build_config()))
    with pytest.raises(HoldoutIsolationError, match="contrato"):
        summarize_representativity(plan, grid_manifest({}, version="otra-v0"))
    duplicated = grid_manifest({RESERVED_A: 600})
    duplicated["counts"].append(
        {"station_key": RESERVED_A, "parameter_raw": "PM2_5", "status": "observed", "hours": 5}
    )
    with pytest.raises(HoldoutIsolationError, match="duplicada"):
        summarize_representativity(plan, duplicated)
    negative = grid_manifest({RESERVED_A: -1})
    with pytest.raises(HoldoutIsolationError, match="hours"):
        summarize_representativity(plan, negative)


def test_period_and_verifications_stay_serializable():
    period = PeriodUtc(**RESERVED_PERIOD)
    assert period.to_dict() == {
        "start": "2023-01-01T00:00:00+00:00",
        "end": "2023-06-30T23:00:00+00:00",
    }
    plan = plan_holdout(HoldoutConfig(**build_config()))
    report = verify_isolation(plan, isolated_manifests(), disjoint_periods())
    assert json.dumps(report, sort_keys=True)


@pytest.mark.parametrize(
    "missing",
    [
        "manifests",
        "periods",
        "no_period_argument",
        "one_period",
        "training",
        "pretraining",
        "empty_counts",
        "orphan_period",
    ],
)
def test_full_isolation_requires_evidence_for_each_package(missing):
    plan = plan_holdout(HoldoutConfig(**build_config()))
    manifests = isolated_manifests()
    periods = disjoint_periods()
    if missing == "manifests":
        manifests.clear()
    elif missing == "periods":
        periods.clear()
    elif missing == "one_period":
        del periods["entrenamiento"]
    elif missing in ("training", "pretraining"):
        label = "entrenamiento" if missing == "training" else "preentrenamiento"
        del manifests[label], periods[label]
    elif missing == "empty_counts":
        manifests["entrenamiento"] = splits_manifest([])
    elif missing == "orphan_period":
        periods["otro"] = periods["entrenamiento"]
    with pytest.raises(HoldoutIsolationError):
        if missing == "no_period_argument":
            verify_isolation(plan, manifests)
        else:
            verify_isolation(plan, manifests, periods)


def test_pretraining_station_must_have_declared_coordinates():
    plan = plan_holdout(HoldoutConfig(**build_config()))
    manifests = isolated_manifests(preentrenamiento=splits_manifest([TRAIN_F]))
    with pytest.raises(HoldoutIsolationError, match=TRAIN_F):
        assert_isolation(plan, manifests, disjoint_periods())


def test_available_hours_cannot_exceed_the_reserved_period():
    plan = plan_holdout(HoldoutConfig(**build_config()))
    full = summarize_representativity(plan, grid_manifest({RESERVED_A: EXPECTED_HOURS_PERIOD}))
    assert full["stations"][0]["coverage_ratio"] == 1.0
    with pytest.raises(HoldoutIsolationError, match=RESERVED_A):
        summarize_representativity(plan, grid_manifest({RESERVED_A: EXPECTED_HOURS_PERIOD + 1}))


def test_frozen_plan_keeps_its_declared_stations():
    plan = plan_holdout(HoldoutConfig(**build_config()))
    for stations in (plan.reserved_stations, plan.training_stations):
        assert not isinstance(stations, MutableSequence)


def test_loading_a_plan_verifies_its_fingerprint():
    plan = plan_holdout(HoldoutConfig(**build_config()))
    assert HoldoutPlan.model_validate_json(plan.to_json()) == plan
    changed = {**plan.to_dict(), "min_distance_km": 0.1}
    with pytest.raises(ValidationError, match="SHA-256"):
        HoldoutPlan.model_validate(changed)


@pytest.mark.parametrize("change", ["missing_split", "unknown_split", "zero_windows"])
def test_split_manifest_requires_populated_partitions(change):
    plan = plan_holdout(HoldoutConfig(**build_config()))
    manifests = isolated_manifests()
    counts = manifests["entrenamiento"]["counts"]
    if change == "missing_split":
        counts[:] = [row for row in counts if row["split"] != "test"]
    elif change == "unknown_split":
        counts[0]["split"] = "otro"
    else:
        counts[0]["windows"] = 0
    with pytest.raises(HoldoutIsolationError, match="entrenamiento"):
        verify_isolation(plan, manifests, disjoint_periods())
