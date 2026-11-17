"""Contrato de adquisición: procedencia de bytes, sin semántica científica."""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Self
from urllib.parse import parse_qsl

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class AcquisitionError(ValueError):
    """Falla segura: los mensajes públicos no incluyen datos de entrada."""


class AcquisitionSpec(BaseModel):
    """Solicitud explícita y acotada; no determina permisos de redistribución."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    source_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    resource_url: HttpUrl
    final_url: HttpUrl | None = None
    api_documentation_url: HttpUrl | None = None
    source_page_url: HttpUrl | None = None
    method: Literal["lightpanda", "api", "local", "http_file"]
    format: Literal["csv", "json", "xlsx", "docx"]
    max_bytes: int = Field(strict=True, gt=0, le=1_073_741_824_000)
    expected_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    acquired_at: datetime | None = None
    json_required_keys: tuple[str, ...] = ()
    csv_delimiter: Literal[",", ";"] = ","

    @model_validator(mode="after")
    def check_contract(self) -> Self:
        if self.format != "csv" and self.csv_delimiter != ",":
            raise ValueError("El delimitador solo describe recursos CSV")
        if self.method == "api" and self.api_documentation_url is None:
            raise ValueError("La API requiere una referencia de documentación")
        if self.method == "http_file" and self.source_page_url is None:
            raise ValueError("El archivo público requiere página oficial de procedencia")
        for url in [
            self.resource_url,
            self.final_url,
            self.api_documentation_url,
            self.source_page_url,
        ]:
            if url is not None:
                self._check_public_url(url)
        if self.acquired_at is not None and self.acquired_at.utcoffset() is None:
            raise ValueError("La fecha debe incluir zona horaria")
        if self.format == "json" and not self.json_required_keys:
            raise ValueError("JSON requiere claves obligatorias explícitas")
        return self

    @staticmethod
    def _check_public_url(url: HttpUrl) -> None:
        if (
            url.username
            or url.password
            or url.fragment
            or any(
                re.search(r"token|key|secret|password|signature|credential|auth", key, re.I)
                for key, _ in parse_qsl(url.query or "")
            )
        ):
            raise ValueError("No se admiten URL con credenciales ni fragmentos")


class Manifest(BaseModel):
    """Registro inmutable de una adquisición o referencia a un original previo."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    spec: AcquisitionSpec
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    size_bytes: int = Field(strict=True, gt=0)
    verified_at: datetime
    artifact_path: str
    original_name: str | None = Field(default=None, max_length=255)
    storage: Literal["bundle", "reference"]
    http_status: int | None = None
    attempts: int = Field(default=0, ge=0, le=3)
    validation: Literal["structure_only"] = "structure_only"

    @model_validator(mode="after")
    def check_manifest(self) -> Self:
        path = Path(self.artifact_path)
        if path.is_absolute() or ".." in path.parts or len(path.parts) < 2:
            raise ValueError("Ruta del original inválida")
        if self.verified_at.utcoffset() is None or self.size_bytes > self.spec.max_bytes:
            raise ValueError("Evidencia de adquisición inválida")
        return self


@dataclass(frozen=True)
class AcquisitionResult:
    """Rutas locales verificadas; reused no significa caché del servidor."""

    artifact: Path
    manifest: Path
    reused: bool
