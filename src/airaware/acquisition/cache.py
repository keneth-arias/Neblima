"""Estado local acotado de caché y parciales; nunca se presenta como un original completo."""

import fcntl
import hashlib
import json
import os
import re
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from airaware.acquisition.models import AcquisitionError, AcquisitionSpec
from airaware.acquisition.store import CHUNK_SIZE, _identity, _safe_path, _sync_directory


class CacheState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    request_key: str = Field(pattern=r"^[a-f0-9]{64}$")
    complete_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    complete_etag: str | None = Field(default=None, max_length=1024)
    complete_modified: str | None = Field(default=None, max_length=128)
    partial_size: int = Field(default=0, ge=0, le=1073741824000)
    partial_sha256: str = Field(default=hashlib.sha256(b"").hexdigest(), pattern=r"^[a-f0-9]{64}$")
    partial_reusable: bool = True
    partial_total: int | None = Field(default=None, gt=0, le=1073741824000)
    partial_etag: str | None = Field(default=None, max_length=1024)
    acquired_at: AwareDatetime | None = None


def safe_etag(value: str | None) -> str | None:
    return value if value and re.fullmatch(r'(?:W/)?"[\x21\x23-\x7e]{0,1000}"', value) else None


class TransferCache:
    def __init__(self, spec: AcquisitionSpec, data_dir: Path):
        self.spec = spec
        self.root = data_dir.expanduser().resolve()
        encoded = json.dumps((*_identity(spec), spec.expected_sha256), ensure_ascii=True).encode()
        self.key = hashlib.sha256(encoded).hexdigest()
        self.directory = _safe_path(self.root, f".acquisition-cache/{self.key}")
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.partial = _safe_path(self.root, f".acquisition-cache/{self.key}/partial")
        self.record = _safe_path(self.root, f".acquisition-cache/{self.key}/state.json")

    @contextmanager
    def locked(self):
        path = _safe_path(self.root, f".acquisition-cache/{self.key}/lock")
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "a") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise AcquisitionError("El bloqueo de caché no es un archivo regular")
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

    def load(self) -> CacheState:
        try:
            if not self.record.exists():
                if self.partial.exists():
                    raise AcquisitionError("Existe un parcial sin procedencia; no se sobrescribió")
                return CacheState(request_key=self.key)
            if self.record.stat().st_size > 65536:
                raise ValueError("Estado excesivo")
            state = CacheState.model_validate_json(self.record.read_bytes())
            if state.request_key != self.key or state.partial_size > self.spec.max_bytes:
                raise ValueError("Estado de otro recurso o presupuesto")
            for etag in [state.partial_etag, state.complete_etag]:
                if etag is not None and safe_etag(etag) != etag:
                    raise ValueError("Validador inválido")
            return state
        except (OSError, ValueError, ValidationError) as error:
            raise AcquisitionError("No se pudo verificar el estado de caché") from error

    def save(self, state: CacheState) -> None:
        validated = CacheState.model_validate(state.model_dump())
        name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", dir=self.directory, delete=False, encoding="utf-8", prefix="state-"
            ) as stream:
                name = Path(stream.name)
                stream.write(validated.model_dump_json(indent=2) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.record)
            name = None
            _sync_directory(self.directory)
        finally:
            if name is not None:
                name.unlink(missing_ok=True)

    def verify_partial(self, state: CacheState) -> None:
        if not self.partial.exists():
            if state.partial_size:
                raise AcquisitionError("Falta el parcial registrado")
            return
        digest = hashlib.sha256()
        with self.partial.open("rb") as stream:
            remaining = state.partial_size
            while remaining:
                chunk = stream.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    raise AcquisitionError("El parcial está truncado")
                digest.update(chunk)
                remaining -= len(chunk)
        if digest.hexdigest() != state.partial_sha256:
            raise AcquisitionError("El parcial cambió; no se concatenaron bytes")
        # Cola no confirmada por un checkpoint tras una caída; solo nuestro parcial identificado.
        if self.partial.stat().st_size > state.partial_size:
            with self.partial.open("r+b") as stream:
                stream.truncate(state.partial_size)

    def reset_partial(self, state: CacheState) -> None:
        self.verify_partial(state)
        self.partial.unlink(missing_ok=True)
        state.partial_size = 0
        state.partial_sha256 = hashlib.sha256(b"").hexdigest()
        state.partial_reusable = True
        state.partial_total = None
        state.partial_etag = None
        state.acquired_at = None
        self.save(state)
