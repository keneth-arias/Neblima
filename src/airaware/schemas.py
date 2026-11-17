"""Contrato v1 de intercambio; validar estructura no acredita semántica científica."""

import math
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(min_length=1, pattern=r"\S")]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Provenance(Record):
    source_id: Identifier
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    record: int = Field(ge=1, strict=True)
    sheet: str | None = None


class Source(Record):
    source_id: Identifier
    url: Identifier
    license: str | None = None
    rights_evidence: list[Identifier] = Field(default_factory=list)


class Station(Record):
    station_id: Identifier
    name_raw: Identifier
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    coordinates_raw: dict[str, str | None] = Field(default_factory=dict)
    coordinate_evidence: list[Identifier] = Field(default_factory=list)
    identity_evidence: list[Identifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def coordinate_pair(self) -> Self:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Las coordenadas verificadas se declaran como par")
        if self.latitude is not None and not self.coordinate_evidence:
            raise ValueError("Las coordenadas requieren evidencia del sistema y conversión")
        return self


class Sensor(Record):
    sensor_id: Identifier
    station_id: Identifier
    method: str | None = None
    parameter: str | None = None
    evidence: list[Identifier] = Field(default_factory=list)


class Relocation(Record):
    station_id: Identifier
    effective_at: datetime | None = None
    previous_station_id: str | None = None
    evidence: list[Identifier] = Field(min_length=1)

    @model_validator(mode="after")
    def aware_date(self) -> Self:
        if self.effective_at is not None and self.effective_at.utcoffset() is None:
            raise ValueError("La reubicación requiere zona horaria documentada")
        return self


class Observation(Record):
    schema_version: Literal[1]
    observation_id: Identifier
    station_id: str | None
    sensor_id: str | None
    parameter_raw: str
    parameter: str | None
    unit_raw: str | None
    unit: str | None
    value_raw: str | None
    value: float | None
    value_status: Literal["finite", "censored", "missing", "unresolved", "nonfinite"]
    kind: Literal["measured", "derived", "modeled", "reanalysis", "forecast", "imputed"]
    time_raw: dict[str, str | None]
    start: datetime | None
    end: datetime | None
    timezone: str | None
    available_at: datetime | None
    quality: Literal["unknown", "valid", "invalid"]
    semantic_evidence: list[Identifier]
    provenance: Provenance
    parent_ids: list[Identifier]
    raw_fields: dict[str, str | None]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.value_status == "finite") != (self.value is not None):
            raise ValueError("Solo finite admite y exige un valor numérico")
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("El valor debe ser finito")
        for instant in (self.start, self.end, self.available_at):
            if instant is not None and instant.utcoffset() is None:
                raise ValueError("Los instantes interpretados requieren zona horaria")
        if self.start is not None and self.end is not None and self.end <= self.start:
            raise ValueError("El fin debe ser posterior al inicio")
        if self.kind in {"derived", "imputed"} and not self.parent_ids:
            raise ValueError("Datos derivados o imputados requieren registros padres")
        if (self.start is not None or self.end is not None) and (
            not self.timezone or not self.semantic_evidence
        ):
            raise ValueError("Interpretar el reloj requiere zona y evidencia")
        return self
