"""Conversión contractual por señal con rechazos trazables; sin pérdida silenciosa."""

from typing import Literal

from pydantic import Field

from airaware.schemas import Observation, Provenance, Record
from airaware.senamhi_preparation import PreparationPolicy, observation, timestamp_utc

Signal = Literal["PM10", "PM2_5", "NO2"]
SIGNALS: tuple[Signal, Signal, Signal] = ("PM10", "PM2_5", "NO2")


class Rejection(Record):
    """Rechazo trazable de una señal: conserva procedencia, contenido disponible y error."""

    provenance: Provenance
    signal: Signal
    raw: str | None
    raw_fields: dict[str, str | None]
    extra_fields: list[str]
    error: str = Field(min_length=1)


Outcome = Observation | Rejection
RowOutcomes = tuple[Outcome, Outcome, Outcome]


def _provenance(record: int, policy: PreparationPolicy) -> Provenance:
    return Provenance(source_id=policy.source_id, sha256=policy.input_sha256, record=record)


def _rejection(
    record: int,
    fields: dict[str, str],
    extras: list[str],
    policy: PreparationPolicy,
    error: str,
    signal: Signal,
) -> Rejection:
    return Rejection(
        provenance=_provenance(record, policy),
        signal=signal,
        raw=fields.get(signal),
        raw_fields=fields,
        extra_fields=extras,
        error=error,
    )


def convert_row(
    record: int,
    values: list[str],
    header: list[str],
    policy: PreparationPolicy,
    *,
    forced_error: str | None = None,
) -> RowOutcomes:
    """Convertir una fila en exactamente tres resultados contabilizados."""
    fields = dict(zip(header, values, strict=False))
    extras = values[len(header) :]
    error = forced_error
    if error is None:
        if len(values) < len(header):
            error = f"fila incompleta: esperadas {len(header)} columnas, presentes {len(values)}"
        elif extras:
            error = f"fila con columnas de más: esperadas {len(header)}, recibidas {len(values)}"
        else:
            try:
                timestamp_utc(fields["FECHA"], fields["HORA"])
            except ValueError as exc:
                error = f"FECHA/HORA inválida: {exc}"
    if error is not None:
        rejections = [_rejection(record, fields, extras, policy, error, s) for s in SIGNALS]
        return (rejections[0], rejections[1], rejections[2])
    outcomes: list[Outcome] = []
    for signal in SIGNALS:
        outcomes.append(observation(fields, signal, record, policy))
    return (outcomes[0], outcomes[1], outcomes[2])
