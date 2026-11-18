"""Construcción de registros horarios de PM2.5 con el SDK fijado de TimeNet."""

from datetime import datetime, timedelta
from fractions import Fraction

import pyarrow as pa
from timenet.dataset import Record, Signal, Source
from timenet.dataset.axis import RegularAxis
from timenet.json import JsonMapping
from timenet.types import TimeOrigin, TimeSeriesSpec, ureg

PM25 = TimeSeriesSpec(
    spec_type="pm25",
    name="PM2.5",
    unit_value=ureg.microgram / ureg.meter**3,
    dtype="float64",
    missing={
        "reason": "not_recorded",
        "description": "Casilla horaria sin medición utilizable en la vista derivada.",
    },
)


def pm25_record(
    *, station_key: str, start: datetime, values: pa.Array, provenance: JsonMapping
) -> Record:
    """Convertir una serie con una casilla por hora y conservar su procedencia."""
    if start.utcoffset() != timedelta(0) or (start.minute or start.second or start.microsecond):
        raise ValueError("La serie debe empezar en una hora exacta UTC")
    if not station_key.strip() or len(values) == 0:
        raise ValueError("Se requiere identidad provisional y al menos una casilla horaria")
    signal = Signal(
        spec=PM25,
        name="pm25",
        time_axis=RegularAxis(period_us=Fraction(3_600_000_000)),
        data=values,
    )
    return Record(
        sources=(Source(name=station_key, signals=(signal,)),),
        start_time=TimeOrigin(start),
        metadata={"station_key": station_key, "provenance": provenance},
    )
