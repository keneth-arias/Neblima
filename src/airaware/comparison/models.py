"""Política explícita fijada antes de contar datos reales."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from airaware.comparison.metrics import score


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["comparison-v1", "comparison-v2"] = "comparison-v2"
    histories: list[Literal[24, 48, 72, 168]] = [24, 48, 72, 168]
    horizons: list[Literal[6, 12, 24, 48]] = [6, 12, 24, 48]
    geographies: list[Literal["lima", "callao"]] = ["lima", "callao"]
    signals: list[Literal["pm25", "pm10"]] = ["pm25", "pm10"]
    blockers: dict[str, list[str]] = Field(default_factory=dict)
    weights: tuple[float, float, float, float, float] = (0.35, 0.25, 0.15, 0.15, 0.10)
    target_stations: int | None = Field(default=None, gt=0)
    target_months: int | None = Field(default=None, gt=0)
    hours_per_month: Literal[720] = 720

    @model_validator(mode="after")
    def validate_policy(self):
        if self.version == "comparison-v2" and (
            self.target_stations is not None or self.target_months is not None
        ):
            raise ValueError("comparison-v2 no admite cuotas de tamaño")
        if self.version == "comparison-v1" and (
            self.target_stations is None or self.target_months is None
        ):
            raise ValueError("La política histórica requiere denominadores explícitos")
        score([0] * 5, eligible=False, weights=self.weights)
        for values in (self.histories, self.horizons, self.geographies, self.signals):
            if not values or len(set(values)) != len(values):
                raise ValueError("Listas vacías o repetidas")
        return self
