"""Validate source discovery records without network access.

Pydantic model patterns: https://docs.pydantic.dev/latest/concepts/models/
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, model_validator


class Source(BaseModel):
    """A candidate source; null fields explicitly mean unverified information."""

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
        """Prevent credentialed URLs and unsupported source-readiness claims."""
        for url in [self.catalog_url, *self.resource_urls, self.license_url]:
            if url and (url.username is not None or url.password is not None):
                raise ValueError("URLs must not contain credentials")
        if self.last_verified_at is not None and self.last_verified_at.utcoffset() is None:
            raise ValueError("Verification timestamps must include a timezone")
        progressed = self.status in {"verified", "downloaded", "profiled", "integrated"}
        if progressed and (
            self.last_verified_at is None or not self.notes or not self.notes.strip()
        ):
            raise ValueError("Progress requires a verification timestamp and evidence notes")
        if self.status in {"blocked", "excluded", "duplicate"} and (
            not self.notes or not self.notes.strip()
        ):
            raise ValueError("Inactive sources require an explanation")
        if self.status == "integrated" and (
            self.redistribution != "allowed"
            or not self.license
            or not self.license_url
            or self.data_category in {"unknown", "mixed"}
        ):
            raise ValueError("Integration requires documented rights and measurement semantics")
        return self


class Catalog(BaseModel):
    """Versioned source inventory with stable unique identifiers."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    sources: list[Source] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        """Reject ambiguous source identifiers."""
        ids = [source.source_id for source in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("Source identifiers must be unique")
        return self


class CatalogError(ValueError):
    """A safe user-facing catalog error with no raw configuration values."""


def load_catalog(path: Path) -> Catalog:
    """Load trusted-size local YAML safely and report errors without echoing its values."""
    try:
        if path.stat().st_size > 2_000_000:
            raise CatalogError("Catalog exceeds the 2 MB configuration limit")
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Catalog.model_validate(content)
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError, RecursionError) as error:
        raise CatalogError(
            "Cannot read or validate catalog; check YAML, required fields, unique IDs and evidence"
        ) from error
