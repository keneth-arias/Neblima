"""Política explícita fijada antes de contar datos reales."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from airaware.comparison.metrics import score


class OperatingSelection(BaseModel):
    """Aprobación acotada a bytes, objetivo y uso; no certifica calidad instrumental."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str = Field(min_length=1)
    input_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    geography: Literal["lima", "callao"]
    signal: Literal["pm25", "pm10"]
    authorized_by: Literal["keneth-arias"]
    approval_reference: str = Field(min_length=1)
    timestamp_basis: Literal["published_utc"]
    accepted_unknowns: list[Literal["interval_position_unverified", "quality_flags_unverified"]]
    quality: Literal["unknown"]
    interval_position: Literal["unknown"]
    daily_regulatory_labels: Literal[False]

    @model_validator(mode="after")
    def explicit_unknowns(self):
        if (
            set(self.accepted_unknowns)
            != {"interval_position_unverified", "quality_flags_unverified"}
            or len(self.accepted_unknowns) != 2
        ):
            raise ValueError("Declarar las dos incógnitas aceptadas sin duplicarlas")
        return self


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["comparison-v1", "comparison-v2", "comparison-v3"] = "comparison-v2"
    histories: list[Literal[24, 48, 72, 168]] = [24, 48, 72, 168]
    horizons: list[Literal[6, 12, 24, 48]] = [6, 12, 24, 48]
    geographies: list[Literal["lima", "callao"]] = ["lima", "callao"]
    signals: list[Literal["pm25", "pm10"]] = ["pm25", "pm10"]
    operating_selection: OperatingSelection | None = None
    blockers: dict[str, list[str]] = Field(default_factory=dict)
    weights: tuple[float, float, float, float, float] = (0.35, 0.25, 0.15, 0.15, 0.10)
    target_stations: int | None = Field(default=None, gt=0)
    target_months: int | None = Field(default=None, gt=0)
    hours_per_month: Literal[720] = 720

    @model_validator(mode="after")
    def validate_policy(self):
        if self.version in {"comparison-v2", "comparison-v3"} and (
            self.target_stations is not None or self.target_months is not None
        ):
            raise ValueError("La política vigente no admite cuotas de tamaño")
        if self.version == "comparison-v1" and (
            self.target_stations is None or self.target_months is None
        ):
            raise ValueError("La política histórica requiere denominadores explícitos")
        selected = self.operating_selection
        if (self.version == "comparison-v3") != (selected is not None):
            raise ValueError("Solo v3 admite y exige selección operativa explícita")
        if selected is not None and (
            selected.geography not in self.geographies or selected.signal not in self.signals
        ):
            raise ValueError("La selección debe estar dentro de los escenarios configurados")
        score([0] * 5, eligible=False, weights=self.weights)
        for values in (self.histories, self.horizons, self.geographies, self.signals):
            if not values or len(set(values)) != len(values):
                raise ValueError("Listas vacías o repetidas")
        return self
