"""Transferencia condicional con parciales identificados y presupuesto compartido.

Protocolo: RFC 9110, secciones 13.1, 14 y 15. No sustituye al canal web Lightpanda.
"""

import hashlib
import math
import os
import re
import shutil
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
from pydantic import ValidationError

from airaware.acquisition.budget import ByteBudget
from airaware.acquisition.cache import CacheState, TransferCache, safe_etag
from airaware.acquisition.models import AcquisitionError, AcquisitionResult, AcquisitionSpec
from airaware.acquisition.protocol import (
    _check_destination,
    _resolve,
    _response_length,
    _retry_delay,
)
from airaware.acquisition.store import _chunks, _safe_path, ingest_chunks, verify_bundle

CHECKPOINT_BYTES = 4 * 1024 * 1024


def _modified(value: str | None) -> str | None:
    if value is None or len(value) > 128 or "\r" in value or "\n" in value:
        return None
    try:
        return value if parsedate_to_datetime(value).utcoffset() is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


def _receive(
    response: httpx.Response,
    cache: TransferCache,
    state: CacheState,
    budget: ByteBudget,
    check_time: Callable[[], None],
    available_space: Callable[[Path], int],
    clock: Callable[[], datetime],
    reusable: bool,
) -> None:
    spec = cache.spec
    length = _response_length(response, spec)
    etag = safe_etag(response.headers.get("etag"))
    if response.status_code == 206:
        match = re.fullmatch(
            r"bytes ([0-9]+)-([0-9]+)/([0-9]+)", response.headers.get("content-range", "")
        )
        if not match or not state.partial_size or etag != state.partial_etag:
            raise AcquisitionError("El rango o su validador no corresponde al parcial")
        try:
            start, end, total = map(int, match.groups())
        except ValueError as error:
            raise AcquisitionError("Content-Range contiene números inválidos") from error
        if (
            start != state.partial_size
            or end < start
            or end >= total
            or total > spec.max_bytes
            or (state.partial_total is not None and total != state.partial_total)
            or (length is not None and length != end - start + 1)
        ):
            raise AcquisitionError("Content-Range no cumple el contrato de reanudación")
        response_bytes = end - start + 1
    else:
        total = length
        response_bytes = length
    required = (total if total is not None else spec.max_bytes) * 2 - state.partial_size
    if available_space(cache.directory) < required + 65536:
        raise AcquisitionError(
            "No hay espacio local suficiente para preservar y publicar el recurso"
        )
    if response.status_code == 200:
        cache.reset_partial(state)
        state.partial_etag = etag
        state.acquired_at = clock()
    state.partial_total = total
    state.partial_reusable = reusable
    cache.save(state)
    digest = hashlib.sha256()
    if state.partial_size:
        for chunk in _chunks(cache.partial):
            digest.update(chunk)
    mode = "ab" if state.partial_size else "xb"
    initial = state.partial_size
    checkpoint = state.partial_size
    with cache.partial.open(mode) as stream:

        def save_progress() -> None:
            stream.flush()
            os.fsync(stream.fileno())
            state.partial_sha256 = digest.hexdigest()
            cache.save(state)

        try:
            for chunk in response.iter_raw():
                budget.consume(len(chunk))
                check_time()
                if state.partial_size + len(chunk) > spec.max_bytes:
                    raise AcquisitionError("La respuesta supera el límite por archivo")
                if (
                    response_bytes is not None
                    and state.partial_size - initial + len(chunk) > response_bytes
                ):
                    raise AcquisitionError("La respuesta excede la longitud declarada")
                stream.write(chunk)
                digest.update(chunk)
                state.partial_size += len(chunk)
                if state.partial_size - checkpoint >= CHECKPOINT_BYTES:
                    save_progress()
                    checkpoint = state.partial_size
        finally:
            save_progress()
    check_time()
    received = state.partial_size - initial
    if response_bytes is not None and received != response_bytes:
        raise httpx.ReadError("Respuesta truncada")
    if state.partial_total is None:
        state.partial_total = state.partial_size
        cache.save(state)
    if state.partial_size != state.partial_total:
        raise httpx.ReadError("Falta parte de la representación")


def _publish(
    cache: TransferCache,
    state: CacheState,
    attempt: int,
    etag: str | None,
    modified: str | None,
    cacheable: bool,
    http_status: int,
) -> AcquisitionResult:
    current = cache.spec.model_copy(
        update={"acquired_at": state.acquired_at, "final_url": cache.spec.resource_url}
    )
    result = ingest_chunks(
        current, _chunks(cache.partial), cache.root, http_status=http_status, attempts=attempt
    )
    manifest_digest = result.manifest.parent.name
    cache.reset_partial(state)
    state.complete_sha256 = manifest_digest if cacheable else None
    state.complete_etag = etag if cacheable else None
    state.complete_modified = modified if cacheable else None
    cache.save(state)
    return result


def fetch_cached_api(
    spec: AcquisitionSpec,
    data_dir: Path,
    *,
    allowed_hosts: set[str],
    network_budget: ByteBudget | None = None,
    offline: bool = False,
    refresh: bool = False,
    deadline_seconds: float = 60,
    transport: httpx.BaseTransport | None = None,
    resolve: Callable[[str], list[str]] = _resolve,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
    available_space: Callable[[Path], int] = lambda path: shutil.disk_usage(path).free,
) -> AcquisitionResult:
    """Caché siempre verificada; reanudación solo con ETag fuerte. Offline no resuelve DNS."""
    if (
        not math.isfinite(deadline_seconds)
        or not 0 < deadline_seconds <= 86400
        or spec.method != "api"
        or (offline and refresh)
    ):
        raise AcquisitionError("La política de transferencia API no es válida")
    try:
        cache = TransferCache(spec, data_dir)
        with cache.locked():
            state = cache.load()
            if not state.partial_reusable:
                cache.reset_partial(state)
            cached = None
            if state.complete_sha256:
                directory = _safe_path(cache.root, f"raw/{spec.source_id}/{state.complete_sha256}")
                cached = verify_bundle(spec, cache.root / "raw", directory)
            if offline:
                if cached is None:
                    raise AcquisitionError("No hay un original verificado disponible sin red")
                return cached
            cache.verify_partial(state)
            if refresh:
                cache.reset_partial(state)
            deadline = monotonic() + deadline_seconds

            def check_time() -> None:
                if monotonic() >= deadline:
                    raise AcquisitionError("Se agotó el presupuesto temporal de transferencia")

            budget = network_budget if network_budget is not None else ByteBudget(spec.max_bytes)
            with httpx.Client(
                transport=transport,
                follow_redirects=False,
                trust_env=False,
                timeout=httpx.Timeout(10, connect=5),
                headers={"Accept-Encoding": "identity"},
            ) as client:
                for attempt in range(1, 4):
                    check_time()
                    budget.check_remaining()
                    _check_destination(spec, allowed_hosts, resolve)
                    headers = {}
                    if (
                        state.partial_size
                        and state.partial_etag
                        and not state.partial_etag.startswith("W/")
                    ):
                        headers = {
                            "Range": f"bytes={state.partial_size}-",
                            "If-Range": state.partial_etag,
                        }
                    else:
                        if state.partial_size:
                            cache.reset_partial(state)
                        if not refresh and state.complete_etag:
                            headers = {"If-None-Match": state.complete_etag}
                        elif not refresh and state.complete_modified:
                            headers = {"If-Modified-Since": state.complete_modified}
                    client.cookies.clear()
                    delay = float(attempt)
                    try:
                        with client.stream(
                            "GET", str(spec.resource_url), headers=headers
                        ) as response:
                            code = response.status_code
                            if code == 304:
                                if (
                                    cached is None
                                    or not any(h.startswith("If-") for h in headers)
                                    or "Range" in headers
                                ):
                                    raise AcquisitionError(
                                        "304 sin una representación verificada y condición válida"
                                    )
                                tag = safe_etag(response.headers.get("etag"))
                                if (
                                    tag
                                    and state.complete_etag
                                    and tag.removeprefix("W/")
                                    != state.complete_etag.removeprefix("W/")
                                ):
                                    raise AcquisitionError("304 con un validador contradictorio")
                                if "no-store" in response.headers.get("cache-control", "").lower():
                                    state.complete_sha256 = None
                                    state.complete_etag = None
                                    state.complete_modified = None
                                    cache.save(state)
                                return verify_bundle(
                                    spec, cache.root / "raw", cached.manifest.parent
                                )
                            if code in {429, 500, 502, 503, 504}:
                                delay = _retry_delay(
                                    response.headers.get("retry-after"), attempt, clock
                                )
                            elif code in {200, 206}:
                                if code == 206 and "Range" not in headers:
                                    raise AcquisitionError("No se solicitó una respuesta parcial")
                                cacheable = (
                                    "no-store"
                                    not in response.headers.get("cache-control", "").lower()
                                )
                                try:
                                    _receive(
                                        response,
                                        cache,
                                        state,
                                        budget,
                                        check_time,
                                        available_space,
                                        clock,
                                        cacheable,
                                    )
                                except BaseException:
                                    if not cacheable:
                                        cache.reset_partial(state)
                                    raise
                                return _publish(
                                    cache,
                                    state,
                                    attempt,
                                    safe_etag(response.headers.get("etag")),
                                    _modified(response.headers.get("last-modified")),
                                    cacheable,
                                    code,
                                )
                            else:
                                raise AcquisitionError(
                                    "Respuesta no admitida; no se publicaron bytes parciales"
                                )
                    except httpx.TransportError:
                        pass
                    if attempt == 3:
                        break
                    if monotonic() + delay >= deadline:
                        raise AcquisitionError("La espera excede el presupuesto temporal")
                    sleep(delay)
        raise AcquisitionError("La transferencia no se completó tras tres intentos")
    except (OSError, ValidationError) as error:
        raise AcquisitionError("No se pudo completar o verificar la transferencia local") from error
