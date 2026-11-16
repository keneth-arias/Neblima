"""Canal explícito y acotado para archivos públicos resueltos desde páginas oficiales."""

import hashlib
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from airaware.acquisition.budget import ByteBudget
from airaware.acquisition.cache import safe_etag
from airaware.acquisition.models import AcquisitionError, AcquisitionResult, AcquisitionSpec
from airaware.acquisition.protocol import _check_destination, _resolve, _response_length
from airaware.acquisition.transfer import _fetch_cached_http

PREFIX_LIMIT = 65536
USER_AGENT = "AirAware/0.1 (+https://github.com/keneth-arias/airaware)"


@dataclass(frozen=True)
class ResourceProbe:
    size_bytes: int
    etag: str | None
    range_supported: bool
    http_status: int
    prefix_size_bytes: int
    prefix_sha256: str


def probe_public_file(
    spec: AcquisitionSpec,
    *,
    allowed_hosts: set[str],
    network_budget: ByteBudget,
    transport: httpx.BaseTransport | None = None,
    resolve: Callable[[str], list[str]] = _resolve,
) -> ResourceProbe:
    """Consultar hasta 64 KiB sin publicar un original ni asumir que es muestra representativa."""
    if spec.method != "http_file":
        raise AcquisitionError("La consulta requiere method=http_file")
    network_budget.check_remaining()
    deadline = time.monotonic() + 20
    _check_destination(spec, allowed_hosts, resolve)
    try:
        with httpx.Client(
            transport=transport,
            follow_redirects=False,
            trust_env=False,
            timeout=httpx.Timeout(10, connect=5),
            headers={"Accept-Encoding": "identity", "User-Agent": USER_AGENT},
        ) as client:
            with client.stream(
                "GET", str(spec.resource_url), headers={"Range": "bytes=0-65535"}
            ) as response:
                code = response.status_code
                if code not in {200, 206}:
                    raise AcquisitionError(
                        f"Recurso público respondió HTTP {code}; transferencia detenida"
                    )
                length = _response_length(response, spec)
                total = length
                if code == 206:
                    match = re.fullmatch(
                        r"bytes 0-([0-9]{1,20})/([0-9]{1,20})",
                        response.headers.get("content-range", ""),
                    )
                    if not match:
                        raise AcquisitionError("Content-Range de consulta inválido")
                    end, total = map(int, match.groups())
                    if (
                        not 0 < total <= spec.max_bytes
                        or end != min(total, PREFIX_LIMIT) - 1
                        or (length is not None and length != end + 1)
                    ):
                        raise AcquisitionError("El rango no coincide con el tamaño acotado")
                if total is None:
                    raise AcquisitionError(
                        "No se confirmó el tamaño; no se autorizan bytes desconocidos"
                    )
                limit = min(total, PREFIX_LIMIT)
                digest = hashlib.sha256()
                size = 0
                for chunk in response.iter_raw(chunk_size=PREFIX_LIMIT):
                    network_budget.consume(len(chunk))
                    if time.monotonic() >= deadline or size + len(chunk) > limit:
                        raise AcquisitionError("La consulta excedió su presupuesto")
                    digest.update(chunk)
                    size += len(chunk)
                    if size == limit:
                        break
                if size != limit or time.monotonic() >= deadline:
                    raise AcquisitionError("La consulta quedó truncada o excedió su plazo")
                return ResourceProbe(
                    total,
                    safe_etag(response.headers.get("etag")),
                    code == 206,
                    code,
                    size,
                    digest.hexdigest(),
                )
    except httpx.TransportError as error:
        raise AcquisitionError("No se pudo consultar el archivo público") from error


def fetch_public_file(
    spec: AcquisitionSpec,
    data_dir: Path,
    *,
    allowed_hosts: set[str],
    network_budget: ByteBudget,
    offline: bool = False,
    deadline_seconds: float = 1200,
    transport: httpx.BaseTransport | None = None,
    resolve: Callable[[str], list[str]] = _resolve,
) -> AcquisitionResult:
    """Compartir presupuesto entre consulta y GET; no ampliar el tamaño confirmado."""
    if (
        spec.method != "http_file"
        or not math.isfinite(deadline_seconds)
        or not 0 < deadline_seconds <= 86400
    ):
        raise AcquisitionError("Política de archivo público inválida")
    started = time.monotonic()
    current = spec
    if not offline:
        probe = probe_public_file(
            spec,
            allowed_hosts=allowed_hosts,
            network_budget=network_budget,
            transport=transport,
            resolve=resolve,
        )
        current = spec.model_copy(update={"max_bytes": probe.size_bytes})
    remaining = deadline_seconds - (time.monotonic() - started)
    if remaining <= 0:
        raise AcquisitionError("Se agotó el presupuesto temporal del archivo público")
    return _fetch_cached_http(
        current,
        data_dir,
        allowed_hosts=allowed_hosts,
        network_budget=network_budget,
        offline=offline,
        deadline_seconds=remaining,
        transport=transport,
        resolve=resolve,
    )
