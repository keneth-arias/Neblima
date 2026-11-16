"""Transporte explícito de API públicas; páginas y recursos web siguen en Lightpanda.

Fuentes: https://www.python-httpx.org/quickstart/#streaming-responses
https://www.python-httpx.org/advanced/transports/#mock-transports
"""

import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

from airaware.acquisition.models import AcquisitionError, AcquisitionResult, AcquisitionSpec
from airaware.acquisition.protocol import (
    _check_destination,
    _resolve,
    _response_chunks,
    _retry_delay,
)
from airaware.acquisition.store import ingest_chunks


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
                        current = spec.model_copy(
                            update={"acquired_at": clock(), "final_url": spec.resource_url}
                        )
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
