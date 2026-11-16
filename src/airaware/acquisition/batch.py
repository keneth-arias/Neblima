"""Selección de recursos y presupuestos explícitos; no interpreta observaciones."""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Literal, Self, TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator

from airaware.acquisition.budget import ByteBudget
from airaware.acquisition.models import AcquisitionError, AcquisitionResult, AcquisitionSpec
from airaware.acquisition.store import _identity, ingest_file
from airaware.acquisition.transfer import fetch_cached_api


class ResourceEstimate(TypedDict):
    source_id: str
    size_bytes: int | None
    size_origin: Literal["local_stat", "declared", "unknown"]


class BatchEstimate(TypedDict):
    known_size_bytes: int
    unknown_count: int
    authorized_max_bytes: int
    resources: list[ResourceEstimate]


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
        key = (*_identity(job.spec), job.spec.expected_sha256)
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


class BatchFailure(TypedDict):
    source_id: str
    error: str


class BatchOutcome(TypedDict):
    completed: list[AcquisitionResult]
    errors: list[BatchFailure]
    network_bytes: int


def execute_jobs(
    jobs: list[AcquisitionJob],
    data_dir: Path,
    *,
    budget_bytes: int,
    allowed_hosts: set[str],
    workers: int = 1,
    offline: bool = False,
    authorize_unknown: bool = False,
    deadline_seconds: float = 60,
    fetcher: Callable[..., AcquisitionResult] | None = None,
) -> BatchOutcome:
    """Ejecutar hasta cuatro tareas con un presupuesto de payload compartido."""
    if (
        isinstance(workers, bool)
        or not isinstance(workers, int)
        or not 1 <= workers <= 4
        or isinstance(budget_bytes, bool)
        or not isinstance(budget_bytes, int)
        or budget_bytes < 0
        or len(jobs) > 1000
    ):
        raise AcquisitionError("La política de ejecución del lote no es válida")
    selected = select_jobs(jobs)
    network_jobs = [j for j in selected if j.spec.method == "api"]
    if network_jobs and not offline:
        if budget_bytes <= 0:
            raise AcquisitionError("El lote de API requiere un presupuesto total explícito")
        estimate = estimate_jobs(network_jobs)
        if estimate["known_size_bytes"] > budget_bytes:
            raise AcquisitionError("La estimación declarada supera el presupuesto total")
        if estimate["unknown_count"] and not authorize_unknown:
            raise AcquisitionError(
                "Faltan tamaños; se requiere autorización explícita para el lote acotado"
            )
    budget = ByteBudget(budget_bytes or 1)
    source_locks = {job.spec.source_id: threading.Lock() for job in selected}
    fetch = fetcher if fetcher is not None else fetch_cached_api

    def run(job: AcquisitionJob) -> tuple[AcquisitionResult | None, BatchFailure | None]:
        try:
            with source_locks[job.spec.source_id]:
                if job.spec.method == "api":
                    result = fetch(
                        job.spec,
                        data_dir,
                        allowed_hosts=allowed_hosts,
                        network_budget=budget,
                        offline=offline,
                        deadline_seconds=deadline_seconds,
                    )
                else:
                    if job.local_file is None:
                        raise AcquisitionError("Falta el original local del recurso")
                    result = ingest_file(job.spec, job.local_file, data_dir)
            return result, None
        except (AcquisitionError, OSError, ValueError):
            return None, BatchFailure(
                source_id=job.spec.source_id, error="No se pudo completar o verificar el recurso"
            )

    completed, errors = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for result, error in pool.map(run, selected):
            if result is not None:
                completed.append(result)
            if error is not None:
                errors.append(error)
    return BatchOutcome(
        completed=completed, errors=errors, network_bytes=budget.used if not offline else 0
    )


class BatchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    jobs: list[AcquisitionJob] = Field(min_length=1, max_length=1000)
