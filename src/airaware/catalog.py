"""Validación de registros de fuentes sin acceso a la red.

Referencia de modelos Pydantic: https://docs.pydantic.dev/latest/concepts/models/
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, model_validator


class Source(BaseModel):
    """Fuente candidata: los campos nulos indican información sin verificar."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1)
    catalog_url: HttpUrl
    description: str | None = None
    publisher: str | None = None
    resource_urls: list[HttpUrl] = Field(default_factory=list)
    geographic_coverage: str | None = None
    historical_coverage: str | None = None
    temporal_resolution: str | None = None
    spatial_resolution: str | None = None
    variables: list[str] = Field(default_factory=list)
    units: dict[str, str] = Field(default_factory=dict)
    measurement_methodology: str | None = None
    data_category: Literal[
        "unknown",
        "ground_measured",
        "derived",
        "satellite",
        "modeled",
        "reanalysis",
        "forecast",
        "context",
        "mixed",
    ] = "unknown"
    file_formats: list[str] = Field(default_factory=list)
    size_bytes: Annotated[int, Field(strict=True, ge=0)] | None = None
    authentication: str | None = None
    rate_limits: str | None = None
    update_frequency: str | None = None
    license: str | None = None
    license_url: HttpUrl | None = None
    attribution: str | None = None
    redistribution: Literal["unknown", "allowed", "restricted", "prohibited"] = "unknown"
    limitations: str | None = None
    priority: Annotated[int, Field(strict=True, ge=0, le=4)] = 0
    status: Literal[
        "discovered",
        "verified",
        "downloaded",
        "profiled",
        "integrated",
        "blocked",
        "duplicate",
        "excluded",
    ] = "discovered"
    last_verified_at: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        """Rechazar URL con credenciales y avances sin evidencia registrada."""
        for url in [self.catalog_url, *self.resource_urls, self.license_url]:
            if url and (url.username is not None or url.password is not None):
                raise ValueError("Las URL no deben contener credenciales")
        if self.last_verified_at is not None and self.last_verified_at.utcoffset() is None:
            raise ValueError("Las fechas de verificación deben incluir zona horaria")
        progressed = self.status in {"verified", "downloaded", "profiled", "integrated"}
        if progressed and (
            self.last_verified_at is None or not self.notes or not self.notes.strip()
        ):
            raise ValueError("El avance requiere fecha de verificación y notas con evidencia")
        if self.status in {"blocked", "excluded", "duplicate"} and (
            not self.notes or not self.notes.strip()
        ):
            raise ValueError("Las fuentes inactivas requieren una explicación")
        if self.status == "integrated" and (
            self.redistribution != "allowed"
            or not self.license
            or not self.license_url
            or self.data_category in {"unknown", "mixed"}
        ):
            raise ValueError(
                "La integración requiere derechos y significado de las mediciones documentados"
            )
        return self


class Catalog(BaseModel):
    """Inventario versionado con identificadores estables y únicos."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    sources: list[Source] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        """Rechazar identificadores de fuente ambiguos."""
        ids = [source.source_id for source in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("Los identificadores de fuente deben ser únicos")
        return self


class CatalogError(ValueError):
    """Error seguro del catálogo que no muestra valores de configuración."""


def load_catalog(path: Path) -> Catalog:
    """Leer YAML local de tamaño acotado e informar errores sin mostrar sus valores."""
    try:
        if path.stat().st_size > 2_000_000:
            raise CatalogError("El catálogo supera el límite de configuración de 2 MB")
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Catalog.model_validate(content)
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError, RecursionError) as error:
        raise CatalogError(
            "No se pudo leer o validar el catálogo; revisa YAML, campos obligatorios, "
            "ID únicos y evidencia"
        ) from error
