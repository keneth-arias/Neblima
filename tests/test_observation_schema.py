from copy import deepcopy

import pytest
from pydantic import ValidationError

from airaware.schemas import Observation, Relocation, Sensor, Source, Station


def observation():
    return dict(
        schema_version=1,
        observation_id="o1",
        station_id=None,
        sensor_id=None,
        parameter_raw="PM2,5",
        parameter=None,
        unit_raw="µg/m³",
        unit=None,
        value_raw="<0.1",
        value=None,
        value_status="censored",
        kind="measured",
        time_raw={"Fecha.inicio": "44927"},
        observed_at=None,
        start=None,
        end=None,
        timezone=None,
        available_at=None,
        quality="unknown",
        semantic_evidence=[],
        provenance=dict(source_id="eas", sha256="a" * 64, record=2, sheet=None),
        parent_ids=[],
        raw_fields={"Valor": "<0.1"},
    )


def test_unknown_observation_round_trips_without_inventing_values():
    data = observation()
    assert Observation.model_validate(data).model_dump(mode="json") == data


@pytest.mark.parametrize(
    "change",
    [
        {"value": 0},
        {"value_status": "finite", "value": None},
        {"value_status": "finite", "value": float("nan")},
        {"start": "2023-01-01T00:00:00"},
        {"start": "2023-01-02T00:00:00Z", "end": "2023-01-01T00:00:00Z"},
        {"kind": "imputed"},
        {"invented": True},
    ],
)
def test_contradictory_observations_are_rejected(change):
    data = observation() | change
    with pytest.raises(ValidationError):
        Observation.model_validate(data)


def test_provenance_requires_valid_hash_and_positive_record():
    for change in ({"sha256": "wrong"}, {"record": 0}):
        data = deepcopy(observation())
        data["provenance"].update(change)
        with pytest.raises(ValidationError):
            Observation.model_validate(data)


def test_finite_zero_and_derived_lineage_are_preserved():
    data = observation() | {
        "value_status": "finite",
        "value": 0,
        "kind": "derived",
        "parent_ids": ["parent"],
    }
    assert Observation.model_validate(data).value == 0


def test_entities_allow_unknown_metadata_without_inventing_location():
    assert Station(station_id="s", name_raw="CA-01").latitude is None
    assert Source(source_id="eas", url="https://example.org").license is None
    assert Sensor(sensor_id="sensor", station_id="s").method is None
    assert Relocation(station_id="s", evidence=["report"]).effective_at is None


def test_coordinates_and_relocation_evidence_are_validated():
    with pytest.raises(ValidationError):
        Station(station_id="s", name_raw="CA-01", latitude=91, longitude=0)
    with pytest.raises(ValidationError):
        Station(station_id="s", name_raw="CA-01", latitude=-12)
    with pytest.raises(ValidationError):
        Relocation(station_id="s", evidence=[])
