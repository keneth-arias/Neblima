"""Transporte explícito de API públicas; páginas y recursos web siguen en Lightpanda.

Fuentes: https://www.python-httpx.org/quickstart/#streaming-responses
https://www.python-httpx.org/advanced/transports/#mock-transports
"""

import ipaddress
import socket
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

from airaware.acquisition.models import AcquisitionError, AcquisitionResult, AcquisitionSpec
from airaware.acquisition.store import CHUNK_SIZE, ingest_chunks


def _resolve(host: str) -> list[str]:
    return list({str(row[4][0]) for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})


def _check_destination(
    spec: AcquisitionSpec,
    allowed_hosts: set[str],
    resolve: Callable[[str], list[str]],
) -> None:
    host = spec.resource_url.host or ""
    if (
        spec.method != "api"
        or spec.resource_url.scheme != "https"
        or spec.resource_url.port != 443
        or host not in allowed_hosts
    ):
        raise AcquisitionError("La API requiere HTTPS y un host autorizado explícitamente")
    try:
        addresses = resolve(host)
        if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
            raise AcquisitionError("El destino no resuelve exclusivamente a direcciones públicas")
    except (OSError, ValueError) as error:
        raise AcquisitionError("No se pudo validar el destino público de la API") from error


def _retry_delay(value: str | None, attempt: int, clock: Callable[[], datetime]) -> float:
    if value is None:
        return float(attempt)
    try:
        if value.isdigit():
            delay = float(value)
        else:
            parsed = parsedate_to_datetime(value)
            if parsed.utcoffset() is None:
                raise ValueError("Fecha sin zona")
            delay = max(0.0, (parsed - clock()).total_seconds())
        if not 0 <= delay <= 30:
            raise ValueError("Espera fuera del presupuesto")
        return delay
    except (ValueError, TypeError, OverflowError) as error:
        raise AcquisitionError(
            "Retry-After no admite una espera acotada; se detuvo la descarga"
        ) from error


def _response_chunks(
    response: httpx.Response,
    spec: AcquisitionSpec,
    check_time: Callable[[], None],
) -> Iterator[bytes]:
    content_type = response.headers.get("content-type", "").split(";")[0].lower().strip()
    if content_type in {"text/html", "application/xhtml+xml"}:
        raise AcquisitionError("La API respondió HTML en lugar de datos")
    if response.headers.get("content-encoding", "identity").lower() != "identity":
        raise AcquisitionError("La API respondió una codificación de transporte no admitida")
    length = response.headers.get("content-length")
    try:
        expected_size = int(length) if length is not None else None
        if expected_size is not None and not 0 < expected_size <= spec.max_bytes:
            raise ValueError("Longitud fuera del límite")
    except ValueError as error:
        raise AcquisitionError("Content-Length no cumple el límite de adquisición") from error
    size = 0
    for chunk in response.iter_raw(chunk_size=CHUNK_SIZE):
        check_time()
        size += len(chunk)
        if size > spec.max_bytes:
            raise AcquisitionError("La respuesta supera el límite autorizado")
        yield chunk
    check_time()
    if expected_size is not None and expected_size != size:
        raise AcquisitionError("La longitud recibida no coincide con Content-Length")


def fetch_api(
    spec: AcquisitionSpec,
    data_dir: Path,
    *,
    allowed_hosts: set[str],
    transport: httpx.BaseTransport | None = None,
    resolve: Callable[[str], list[str]] = _resolve,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
) -> AcquisitionResult:
    """Hasta tres intentos y 60 s de presupuesto; rechaza redirecciones y no usa cookies/claves."""
    deadline = monotonic() + 60

    def check_time() -> None:
        if monotonic() >= deadline:
            raise AcquisitionError("Se agotó el presupuesto temporal de la adquisición")

    with httpx.Client(
        transport=transport,
        follow_redirects=False,
        trust_env=False,
        timeout=httpx.Timeout(10.0, connect=5.0),
        headers={"Accept-Encoding": "identity"},
    ) as client:
        for attempt in range(1, 4):
            check_time()
            _check_destination(spec, allowed_hosts, resolve)
            check_time()
            delay = float(attempt)
            client.cookies.clear()
            try:
                with client.stream("GET", str(spec.resource_url)) as response:
                    if response.status_code in {429, 500, 502, 503, 504}:
                        delay = _retry_delay(response.headers.get("retry-after"), attempt, clock)
                    elif response.status_code == 200:
                        current = spec.model_copy(update={"acquired_at": clock()})
                        return ingest_chunks(
                            current,
                            _response_chunks(response, spec, check_time),
                            data_dir,
                            http_status=200,
                            attempts=attempt,
                        )
                    else:
                        raise AcquisitionError("La API rechazó la solicitud o intentó redirigirla")
            except httpx.TransportError:
                # Nunca se exponen URL, cabeceras ni mensajes del transporte.
                pass
            if attempt == 3:
                break
            if monotonic() + delay >= deadline:
                raise AcquisitionError("La espera excede el presupuesto temporal")
            sleep(delay)
    raise AcquisitionError("La transferencia API falló tras tres intentos acotados")
