"""Selección de recursos y presupuestos explícitos; no interpreta observaciones."""

import threading
from datetime import date
from pathlib import Path
from typing import Literal, Self, TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator

from airaware.acquisition.models import AcquisitionError, AcquisitionSpec


class ResourceEstimate(TypedDict):
    source_id: str
    size_bytes: int | None
    size_origin: Literal["local_stat", "declared", "unknown"]


class BatchEstimate(TypedDict):
    known_size_bytes: int
    unknown_count: int
    authorized_max_bytes: int
    resources: list[ResourceEstimate]


class ByteBudget:
    """Contabilizar payload recibido entre tareas e intentos, de manera sincronizada."""

    def __init__(self, limit: int):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise AcquisitionError("El presupuesto de red debe ser un entero positivo")
        self.limit = limit
        self.used = 0
        self._lock = threading.Lock()

    def consume(self, size: int) -> None:
        with self._lock:
            self.used += size
            if self.used > self.limit:
                raise AcquisitionError("Se agotó el presupuesto total de bytes de red")


class AcquisitionJob(BaseModel):
    """Fechas y región describen el recurso completo, nunca filtros de filas."""

    model_config = ConfigDict(extra="forbid")
    spec: AcquisitionSpec
    local_file: Path | None = None
    start: date | None = None
    end: date | None = None
    region: str | None = None
    expected_size_bytes: int | None = Field(default=None, strict=True, ge=0)

    @model_validator(mode="after")
    def check_resource(self) -> Self:
        if (self.start is None) != (self.end is None) or (
            self.start is not None and self.end is not None and self.start > self.end
        ):
            raise ValueError("La cobertura del recurso requiere un intervalo completo y válido")
        if self.spec.method != "api" and self.local_file is None:
            raise ValueError(
                "Los recursos Lightpanda/local requieren un archivo previamente adquirido"
            )
        return self


def select_jobs(
    jobs: list[AcquisitionJob],
    *,
    sources: set[str] | None = None,
    regions: set[str] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> list[AcquisitionJob]:
    """Seleccionar metadatos conocidos por coincidencia exacta y solapamiento inclusivo."""
    if start and end and start > end:
        raise AcquisitionError("El intervalo de selección no es válido")
    selected, seen = [], set()
    for job in jobs:
        if sources and job.spec.source_id not in sources:
            continue
        if regions and job.region not in regions:
            continue
        if start or end:
            if job.start is None or job.end is None:
                continue
            if (start and job.end < start) or (end and job.start > end):
                continue
        key = (
            job.spec.source_id,
            str(job.spec.resource_url),
            job.spec.format,
            job.spec.json_required_keys,
            job.spec.method,
            job.spec.expected_sha256,
        )
        if key not in seen:
            selected.append(job)
            seen.add(key)
    return selected


def estimate_jobs(jobs: list[AcquisitionJob]) -> BatchEstimate:
    """Sin GET/HEAD/DNS: distinguir tamaños declarados, stat local y máximos autorizados."""
    resources: list[ResourceEstimate] = []
    known, unknown = 0, 0
    for job in jobs:
        size = job.expected_size_bytes
        origin: Literal["local_stat", "declared", "unknown"] = "declared"
        if job.local_file is not None:
            try:
                size, origin = job.local_file.stat().st_size, "local_stat"
            except OSError:
                size, origin = None, "unknown"
        if size is None:
            unknown += 1
            origin = "unknown"
        else:
            known += size
        resources.append(
            ResourceEstimate(source_id=job.spec.source_id, size_bytes=size, size_origin=origin)
        )
    return BatchEstimate(
        known_size_bytes=known,
        unknown_count=unknown,
        authorized_max_bytes=sum(j.spec.max_bytes for j in jobs),
        resources=resources,
    )
