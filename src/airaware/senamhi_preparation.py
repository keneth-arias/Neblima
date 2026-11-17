"""Contrato listo para #13; no transforma el original ni infiere extremos del intervalo."""

import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from airaware.schemas import Observation, Provenance

SENAMHI_STATION_FIELDS = (
    "ESTACION",
    "LONGITUD",
    "LATITUD",
    "ALTITUD",
    "DEPARTAMENTO",
    "PROVINCIA",
    "DISTRITO",
)


class PreparationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1]
    policy_id: str
    source_id: Literal["senamhi-lima-csv"]
    input_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    timezone: Literal["UTC"]
    timezone_basis: str
    interval_position: Literal["unknown"]
    units: dict[Literal["PM10", "PM2_5", "NO2"], Literal["ug/m3"]]
    units_basis: Literal["inferred_accepted_by_project_lead"]
    units_evidence: str
    license: Literal["ODC-BY-1.0"]
    license_url: str
    catalog_url: str
    quality_default: Literal["unknown"]
    imputation: Literal[False]


def load_policy(path: Path = Path("configs/normalization/senamhi.yaml")) -> PreparationPolicy:
    with path.open("rb") as stream:
        content = stream.read(65537)
    if len(content) > 65536:
        raise ValueError("La política supera 64 KiB")
    policy = PreparationPolicy.model_validate(yaml.safe_load(content))
    if set(policy.units) != {"PM10", "PM2_5", "NO2"}:
        raise ValueError("Declarar unidades de las tres señales")
    return policy


def timestamp_utc(day: str, hour: str) -> datetime:
    if not re.fullmatch(r"\d{8}", day) or not re.fullmatch(r"\d{1,6}", hour):
        raise ValueError("Fecha/hora fuera del formato fuente")
    clock = hour.zfill(6)
    if not re.fullmatch(r"([01]\d|2[0-3])[0-5]\d[0-5]\d", clock):
        raise ValueError("Hora inválida")
    return datetime.strptime(day + clock, "%Y%m%d%H%M%S").replace(tzinfo=UTC)


def observation(
    row: dict[str, str], signal: str, record: int, policy: PreparationPolicy
) -> Observation:
    if signal not in policy.units:
        raise ValueError("Señal no declarada")
    token = row[signal]
    clean = token.strip()
    value = None
    if clean.upper() in {"", "-", "NA", "N/A", "NULL"}:
        status = "missing"
    elif re.match(r"^[<>≤≥]", clean):
        status = "censored"
    else:
        try:
            number = float(clean)
        except ValueError:
            status = "unresolved"
        else:
            if math.isfinite(number):
                status = "finite"
                value = number
            else:
                status = "nonfinite"
    return Observation.model_validate(
        dict(
            schema_version=1,
            observation_id=f"{policy.input_sha256}:{record}:{signal}",
            station_id=None,
            sensor_id=None,
            parameter_raw=signal,
            parameter="PM2.5" if signal == "PM2_5" else signal,
            unit_raw=None,
            unit=policy.units[signal],
            value_raw=token,
            value=value,
            value_status=status,
            kind="measured",
            time_raw={"FECHA": row["FECHA"], "HORA": row["HORA"]},
            observed_at=timestamp_utc(row["FECHA"], row["HORA"]),
            start=None,
            end=None,
            timezone="UTC",
            available_at=None,
            quality="unknown",
            semantic_evidence=[
                policy.policy_id + ":UTC_confirmed_by_lead",
                policy.policy_id + ":units_inferred",
                policy.units_evidence,
            ],
            provenance=Provenance(
                source_id=policy.source_id, sha256=policy.input_sha256, record=record
            ),
            parent_ids=[],
            raw_fields=dict(row),
        )
    )
