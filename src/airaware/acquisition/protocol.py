"""Reglas comunes de transporte HTTP público; sin caché ni almacenamiento."""

import ipaddress
import socket
from collections.abc import Callable, Iterator
from datetime import datetime
from email.utils import parsedate_to_datetime

import httpx

from airaware.acquisition.models import AcquisitionError, AcquisitionSpec


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
        if not addresses or any(
            not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast
            for ip in addresses
        ):
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
    for chunk in response.iter_raw():
        check_time()
        size += len(chunk)
        if size > spec.max_bytes:
            raise AcquisitionError("La respuesta supera el límite autorizado")
        yield chunk
    check_time()
    if expected_size is not None and expected_size != size:
        raise AcquisitionError("La longitud recibida no coincide con Content-Length")
