"""Normalización SENAMHI (#13): lectura streaming y conversión contractual por señal."""

from airaware.normalization.convert import (
    SIGNALS,
    Outcome,
    Rejection,
    RowOutcomes,
    Signal,
    convert_row,
)
from airaware.normalization.parquet import (
    Manifest,
    iter_observations,
    write_parquet_output,
)
from airaware.normalization.reader import (
    REQUIRED_COLUMNS,
    iter_batches,
    stream_observations,
    validate_header,
    verify_source_sha,
)

__all__ = [
    "REQUIRED_COLUMNS",
    "SIGNALS",
    "Manifest",
    "Outcome",
    "Rejection",
    "RowOutcomes",
    "Signal",
    "convert_row",
    "iter_batches",
    "iter_observations",
    "stream_observations",
    "validate_header",
    "verify_source_sha",
    "write_parquet_output",
]
