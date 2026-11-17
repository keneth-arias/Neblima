"""Salida Parquet determinista de #13: escritura incremental por lotes y publicación atómica.

Mapeo físico documentado en docs/decisions/006-senamhi-parquet.md: campos anidados como
map/list/struct, instantes como timestamp('us', 'UTC') y particiones source_id/año/mes UTC
derivadas de observed_at. La semántica contractual permanece en reader/convert.
"""

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Iterator
from datetime import UTC
from importlib.metadata import version
from pathlib import Path
from typing import Literal, Self

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import Field, model_validator

from airaware.normalization.convert import SIGNALS, RowOutcomes
from airaware.schemas import Observation, Record
from airaware.senamhi_preparation import PreparationPolicy

CHUNK = 1 << 20
REJECTION_TRACE = "rejections.jsonl"
MANIFEST = "manifest.json"
VALUE_STATUSES = ("finite", "censored", "missing", "unresolved", "nonfinite")

INSTANT = pa.timestamp("us", tz="UTC")
OBSERVATION_SCHEMA = pa.schema(
    [
        pa.field("schema_version", pa.int64(), nullable=False),
        pa.field("observation_id", pa.string(), nullable=False),
        pa.field("station_id", pa.string()),
        pa.field("sensor_id", pa.string()),
        pa.field("parameter_raw", pa.string(), nullable=False),
        pa.field("parameter", pa.string()),
        pa.field("unit_raw", pa.string()),
        pa.field("unit", pa.string()),
        pa.field("value_raw", pa.string()),
        pa.field("value", pa.float64()),
        pa.field("value_status", pa.string(), nullable=False),
        pa.field("kind", pa.string(), nullable=False),
        pa.field("time_raw", pa.map_(pa.string(), pa.string()), nullable=False),
        pa.field("observed_at", INSTANT),
        pa.field("start", INSTANT),
        pa.field("end", INSTANT),
        pa.field("timezone", pa.string()),
        pa.field("available_at", INSTANT),
        pa.field("quality", pa.string(), nullable=False),
        pa.field(
            "semantic_evidence",
            pa.list_(pa.field("item", pa.string(), nullable=False)),
            nullable=False,
        ),
        pa.field(
            "provenance",
            pa.struct(
                [
                    pa.field("source_id", pa.string(), nullable=False),
                    pa.field("sha256", pa.string(), nullable=False),
                    pa.field("record", pa.int64(), nullable=False),
                    pa.field("sheet", pa.string()),
                ]
            ),
            nullable=False,
        ),
        pa.field(
            "parent_ids", pa.list_(pa.field("item", pa.string(), nullable=False)), nullable=False
        ),
        pa.field("raw_fields", pa.map_(pa.string(), pa.string()), nullable=False),
    ]
)


class OutputFile(Record):
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    rows: int = Field(ge=0, strict=True)


class RejectionTrace(Record):
    path: Literal["rejections.jsonl"]
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    rows: int = Field(ge=0, strict=True)


class ObservationCounts(Record):
    total: int = Field(ge=0, strict=True)
    by_signal: dict[str, int]
    by_class: dict[str, int]


class RejectionCounts(Record):
    total: int = Field(ge=0, strict=True)
    by_signal: dict[str, int]


class ManifestCounts(Record):
    input_rows: int = Field(ge=0, strict=True)
    observations: ObservationCounts
    rejections: RejectionCounts


class Manifest(Record):
    schema_version: Literal[1]
    policy_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    policy_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    input_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    library: Literal["pyarrow"]
    library_version: str = Field(min_length=1)
    counts: ManifestCounts
    files: list[OutputFile]
    rejection_trace: RejectionTrace

    @model_validator(mode="after")
    def reconciled(self) -> Self:
        counts = self.counts
        if counts.observations.total + counts.rejections.total != counts.input_rows * len(SIGNALS):
            raise ValueError("los resultados contractuales no reconcilian con las filas de entrada")
        if set(counts.observations.by_signal) != set(SIGNALS):
            raise ValueError("el conteo de observaciones debe cubrir las tres señales")
        if set(counts.rejections.by_signal) != set(SIGNALS):
            raise ValueError("el conteo de rechazos debe cubrir las tres señales")
        if sum(counts.observations.by_signal.values()) != counts.observations.total:
            raise ValueError("el conteo de observaciones por señal no reconcilia")
        if sum(counts.rejections.by_signal.values()) != counts.rejections.total:
            raise ValueError("el conteo de rechazos por señal no reconcilia")
        for senal in SIGNALS:
            if (
                counts.observations.by_signal[senal] + counts.rejections.by_signal[senal]
                != counts.input_rows
            ):
                raise ValueError(f"la señal {senal} no reconcilia con la entrada")
        if set(counts.observations.by_class) != set(VALUE_STATUSES):
            raise ValueError("el conteo por clase debe cubrir las cinco clases del contrato")
        if sum(counts.observations.by_class.values()) != counts.observations.total:
            raise ValueError("el conteo por clase no reconcilia con las observaciones")
        if sum(entry.rows for entry in self.files) != counts.observations.total:
            raise ValueError(
                "las filas de los archivos Parquet no reconcilian con las observaciones"
            )
        if self.rejection_trace.rows != counts.rejections.total:
            raise ValueError("las líneas de la traza no reconcilian con los rechazos")
        for entry in [*self.files, self.rejection_trace]:
            if os.path.isabs(entry.path) or ".." in Path(entry.path).parts:
                raise ValueError(
                    "las rutas del manifiesto deben ser relativas a la carpeta publicada"
                )
        return self


def write_parquet_output(
    batches: Iterator[list[RowOutcomes]],
    policy: PreparationPolicy,
    target: Path,
) -> Manifest:
    """Consumir lotes incrementales y publicar Parquet, rechazos y manifiesto sin sobrescribir."""
    if target.exists():
        raise ValueError(f"la carpeta de salida ya existe: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    provisional = Path(tempfile.mkdtemp(prefix=f".{target.name}.tmp-", dir=target.parent))
    try:
        manifest = _fill(provisional, batches, policy)
    except BaseException:
        shutil.rmtree(provisional)
        raise
    if target.exists():
        shutil.rmtree(provisional)
        raise ValueError(f"la carpeta de salida ya existe: {target}")
    os.rename(provisional, target)
    return manifest


def verify_output(target: Path) -> Manifest:
    """Verificar los archivos y rechazos listados en el manifiesto publicado."""
    manifest = Manifest.model_validate_json((target / MANIFEST).read_bytes())
    root = target.resolve()
    for entry in [*manifest.files, manifest.rejection_trace]:
        artifact = root / entry.path
        if (
            not artifact.resolve().is_relative_to(root)
            or not artifact.is_file()
            or _sha256(artifact) != entry.sha256
        ):
            raise ValueError(f"Artefacto ausente o distinto del manifiesto: {entry.path}")
    return manifest


def iter_observations(target: Path, batch_size: int = 1000) -> Iterator[Observation]:
    """Leer de vuelta las observaciones publicadas, en orden determinista de partición y archivo."""
    if batch_size < 1:
        raise ValueError("batch_size debe ser positivo")
    root = target.resolve()
    manifest = verify_output(root)
    for entry in sorted(manifest.files, key=lambda item: item.path):
        parquet = pq.ParquetFile(root / entry.path)
        for batch in parquet.iter_batches(batch_size=batch_size):
            for record in batch.to_pylist():
                restored = dict(record)
                restored["time_raw"] = dict(record["time_raw"])
                restored["raw_fields"] = dict(record["raw_fields"])
                yield Observation.model_validate(restored)


def _fill(
    provisional: Path,
    batches: Iterator[list[RowOutcomes]],
    policy: PreparationPolicy,
) -> Manifest:
    input_rows = 0
    observations_total = 0
    observations_by_signal: dict[str, int] = {senal: 0 for senal in SIGNALS}
    observations_by_class: dict[str, int] = {status: 0 for status in VALUE_STATUSES}
    rejections_total = 0
    rejections_by_signal: dict[str, int] = {senal: 0 for senal in SIGNALS}
    rows_per_file: dict[str, int] = {}
    writers: dict[str, pq.ParquetWriter] = {}
    with (provisional / REJECTION_TRACE).open("wb") as trace:
        try:
            for batch in batches:
                pendientes: dict[str, list[dict]] = {}
                for row in batch:
                    input_rows += 1
                    for outcome in row:
                        if isinstance(outcome, Observation):
                            observations_total += 1
                            observations_by_signal[outcome.parameter_raw] += 1
                            observations_by_class[outcome.value_status] += 1
                            pendientes.setdefault(_partition(outcome), []).append(_record(outcome))
                        else:
                            rejections_total += 1
                            rejections_by_signal[outcome.signal] += 1
                            trace.write(_line(outcome.model_dump(mode="json")))
                for partition in sorted(pendientes):
                    relative = f"{partition}/part-00000.parquet"
                    writer = writers.get(relative)
                    if writer is None:
                        (provisional / partition).mkdir(parents=True, exist_ok=True)
                        writer = pq.ParquetWriter(provisional / relative, OBSERVATION_SCHEMA)
                        writers[relative] = writer
                        rows_per_file[relative] = 0
                    record_batch = pa.RecordBatch.from_pylist(
                        pendientes[partition], schema=OBSERVATION_SCHEMA
                    )
                    writer.write_table(pa.Table.from_batches([record_batch]))
                    rows_per_file[relative] += len(pendientes[partition])
        finally:
            for writer in writers.values():
                writer.close()
    _validate(provisional, rows_per_file, rejections_total)
    manifest = Manifest(
        schema_version=1,
        policy_id=policy.policy_id,
        source_id=policy.source_id,
        policy_sha256=hashlib.sha256(policy.model_dump_json().encode("utf-8")).hexdigest(),
        input_sha256=policy.input_sha256,
        library="pyarrow",
        library_version=version("pyarrow"),
        counts=ManifestCounts(
            input_rows=input_rows,
            observations=ObservationCounts(
                total=observations_total,
                by_signal=observations_by_signal,
                by_class=observations_by_class,
            ),
            rejections=RejectionCounts(total=rejections_total, by_signal=rejections_by_signal),
        ),
        files=[
            OutputFile(
                path=relative, sha256=_sha256(provisional / relative), rows=rows_per_file[relative]
            )
            for relative in sorted(rows_per_file)
        ],
        rejection_trace=RejectionTrace(
            path=REJECTION_TRACE,
            sha256=_sha256(provisional / REJECTION_TRACE),
            rows=rejections_total,
        ),
    )
    (provisional / MANIFEST).write_bytes(_json_bytes(manifest.model_dump(mode="json")))
    return manifest


def _validate(provisional: Path, rows_per_file: dict[str, int], rejections_total: int) -> None:
    for relative in sorted(rows_per_file):
        parquet = pq.ParquetFile(provisional / relative)
        if parquet.metadata.num_rows != rows_per_file[relative]:
            raise ValueError(f"filas inesperadas en {relative}")
        if not parquet.schema_arrow.equals(OBSERVATION_SCHEMA):
            raise ValueError(f"esquema físico inesperado en {relative}")
    with (provisional / REJECTION_TRACE).open("rb") as trace:
        lines = sum(chunk.count(b"\n") for chunk in iter(lambda: trace.read(CHUNK), b""))
    if lines != rejections_total:
        raise ValueError("la traza de rechazos no coincide con el conteo")


def _partition(observation: Observation) -> str:
    instant = observation.observed_at
    if instant is None:
        raise ValueError(
            f"observación {observation.observation_id} sin observed_at no tiene partición UTC"
        )
    utc = instant.astimezone(UTC)
    return f"source_id={observation.provenance.source_id}/year={utc.year:04d}/month={utc.month:02d}"


def _record(observation: Observation) -> dict:
    return {
        "schema_version": observation.schema_version,
        "observation_id": observation.observation_id,
        "station_id": observation.station_id,
        "sensor_id": observation.sensor_id,
        "parameter_raw": observation.parameter_raw,
        "parameter": observation.parameter,
        "unit_raw": observation.unit_raw,
        "unit": observation.unit,
        "value_raw": observation.value_raw,
        "value": observation.value,
        "value_status": observation.value_status,
        "kind": observation.kind,
        "time_raw": dict(observation.time_raw),
        "observed_at": observation.observed_at,
        "start": observation.start,
        "end": observation.end,
        "timezone": observation.timezone,
        "available_at": observation.available_at,
        "quality": observation.quality,
        "semantic_evidence": list(observation.semantic_evidence),
        "provenance": {
            "source_id": observation.provenance.source_id,
            "sha256": observation.provenance.sha256,
            "record": observation.provenance.record,
            "sheet": observation.provenance.sheet,
        },
        "parent_ids": list(observation.parent_ids),
        "raw_fields": dict(observation.raw_fields),
    }


def _line(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


def _json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()
