"""Publicación local por cambio de nombre de carpeta en el mismo sistema de archivos.

Referencia: https://docs.python.org/3/library/os.html#os.rename
"""

import errno
import fcntl
import hashlib
import os
import shutil
import stat
import tempfile
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from airaware.acquisition.formats import validate_format
from airaware.acquisition.models import (
    AcquisitionError,
    AcquisitionResult,
    AcquisitionSpec,
    Manifest,
)

CHUNK_SIZE = 64 * 1024


def _safe_path(root: Path, relative: str) -> Path:
    path = root / relative
    if path.is_absolute() and not path.is_relative_to(root):
        raise AcquisitionError("La ruta sale de la carpeta de datos")
    current = root
    for part in path.relative_to(root).parts:
        if part in {".", ".."}:
            raise AcquisitionError("Ruta de datos inválida")
        current = current / part
        if current.is_symlink():
            raise AcquisitionError("No se admiten enlaces simbólicos en el destino")
    return path


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            os.fsync(descriptor)
        except OSError as error:
            if error.errno not in {errno.EINVAL, errno.ENOTSUP}:
                raise
    finally:
        os.close(descriptor)


def _chunks(path: Path) -> Iterator[bytes]:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise AcquisitionError("El origen debe ser un archivo regular")
        while chunk := stream.read(CHUNK_SIZE):
            yield chunk
        after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise AcquisitionError("El archivo de origen cambió durante la lectura")


def _measure(chunks: Iterable[bytes], max_bytes: int, output: Path | None) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    stream = output.open("xb") if output else None
    try:
        for chunk in chunks:
            size += len(chunk)
            if size > max_bytes:
                raise AcquisitionError("El archivo supera el límite de bytes autorizado")
            digest.update(chunk)
            if stream:
                stream.write(chunk)
        if not size:
            raise AcquisitionError("No se admite un archivo vacío")
        if stream:
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if stream:
            stream.close()
    return digest.hexdigest(), size


def _identity(spec: AcquisitionSpec) -> tuple[object, ...]:
    identity = (
        spec.source_id,
        str(spec.resource_url),
        spec.method,
        spec.format,
        spec.json_required_keys,
    )
    # Conservar claves históricas y contratos de coma sin reescribir manifiestos.
    return (
        identity
        if spec.csv_delimiter == ","
        else (*identity, ("csv_delimiter", spec.csv_delimiter))
    )


def verify_bundle(spec: AcquisitionSpec, raw: Path, directory: Path) -> AcquisitionResult:
    """Comprobar manifiesto y original cada vez; no confía en el nombre SHA-256."""
    try:
        manifest_path = _safe_path(raw, str(directory.relative_to(raw) / "manifest.json"))
        if manifest_path.stat().st_size > 64 * 1024:
            raise AcquisitionError("El manifiesto supera el límite permitido")
        manifest = Manifest.model_validate_json(manifest_path.read_bytes())
        if _identity(manifest.spec) != _identity(spec):
            raise AcquisitionError("El destino contiene otra procedencia o contrato")
        artifact = _safe_path(raw, manifest.artifact_path)
        if manifest.storage == "bundle" and artifact != directory / f"original.{spec.format}":
            raise AcquisitionError("El manifiesto no apunta al original del paquete")
        if any(part.startswith(".") for part in artifact.relative_to(raw).parts):
            raise AcquisitionError("No se admiten referencias a archivos temporales u ocultos")
        digest, size = _measure(_chunks(artifact), spec.max_bytes, None)
        if (
            digest != manifest.sha256
            or size != manifest.size_bytes
            or directory.name != digest
            or (spec.expected_sha256 and digest != spec.expected_sha256)
        ):
            raise AcquisitionError("El original y el manifiesto no coinciden")
        validate_format(artifact, spec)
        return AcquisitionResult(artifact, manifest_path, True)
    except (OSError, ValidationError, ValueError) as error:
        raise AcquisitionError("No se pudo verificar el destino; no se sobrescribió") from error


def ingest_chunks(
    spec: AcquisitionSpec,
    chunks: Iterable[bytes],
    data_dir: Path,
    *,
    existing: Path | None = None,
    http_status: int | None = None,
    attempts: int = 0,
    original_name: str | None = None,
) -> AcquisitionResult:
    """Consumir bytes acotados y publicar un paquete completo o una referencia verificada."""
    root = data_dir.expanduser().resolve()
    pending: Path | None = None
    try:
        raw = _safe_path(root, "raw")
        source = _safe_path(root, f"raw/{spec.source_id}")
        source.mkdir(parents=True, exist_ok=True)
        lock_path = _safe_path(root, f"raw/{spec.source_id}/.acquisition.lock")
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "a") as lock:
            if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
                raise AcquisitionError("El bloqueo de adquisición no es un archivo regular")
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            pending = Path(tempfile.mkdtemp(prefix=".pending-", dir=source))
            staged = pending / f"original.{spec.format}"
            digest, size = _measure(chunks, spec.max_bytes, None if existing else staged)
            if spec.expected_sha256 and digest != spec.expected_sha256:
                raise AcquisitionError("La suma SHA-256 no coincide con la esperada")
            artifact = existing if existing else staged
            validate_format(artifact, spec)
            destination = _safe_path(root, f"raw/{spec.source_id}/{digest}")
            if destination.exists():
                return verify_bundle(spec, raw, destination)
            final_artifact = existing if existing else destination / staged.name
            relative = str(final_artifact.relative_to(raw))
            manifest = Manifest(
                spec=spec,
                sha256=digest,
                size_bytes=size,
                verified_at=datetime.now(UTC),
                artifact_path=relative,
                original_name=original_name,
                storage="reference" if existing else "bundle",
                http_status=http_status,
                attempts=attempts,
            )
            serialized = manifest.model_dump_json(indent=2) + "\n"
            if len(serialized.encode("utf-8")) > 64 * 1024:
                raise AcquisitionError("El manifiesto supera el límite permitido")
            with (pending / "manifest.json").open("x", encoding="utf-8") as stream:
                stream.write(serialized)
                stream.flush()
                os.fsync(stream.fileno())
            _sync_directory(pending)
            os.rename(pending, destination)
            pending = None
            _sync_directory(source)
            return AcquisitionResult(final_artifact, destination / "manifest.json", bool(existing))
    except (OSError, ValidationError) as error:
        raise AcquisitionError("No se pudo completar la adquisición local") from error
    finally:
        if pending is not None:
            # Solo nuestra carpeta creada por mkdtemp; nunca rutas de manifiestos o del usuario.
            shutil.rmtree(pending)


def ingest_file(spec: AcquisitionSpec, original: Path, data_dir: Path) -> AcquisitionResult:
    """Registrar una descarga previa sin afirmar que se obtuvo por la red en esta operación."""
    if spec.method in {"api", "http_file"}:
        raise AcquisitionError("La adquisición API requiere el transporte explícito")
    root = data_dir.expanduser().resolve()
    path = original.expanduser().absolute()
    raw_root = root / "raw"
    existing = path if path.is_relative_to(raw_root) else None
    if existing:
        _safe_path(root, str(path.relative_to(root)))
        if any(part.startswith(".") for part in path.relative_to(raw_root).parts):
            raise AcquisitionError("No se admiten referencias a temporales u originales ocultos")
    safe_name = "".join(
        char if char.isprintable() and char not in "/\\" else "_" for char in path.name
    )[:255]
    return ingest_chunks(spec, _chunks(path), data_dir, existing=existing, original_name=safe_name)
