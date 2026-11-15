# ADR-001: Local storage and GitHub Actions for the foundation

## Status and date
Accepted, 2026-11-15. The user selected local storage and GitHub Actions for the initial setup.

## Context
The first issues need source discovery, licensing evidence and reproducible developer tools.
Coverage, download sizes and future compute requirements are not yet measured.

## Decision
Use uv with Python 3.13.13 locally, maintain compatibility with TimeNet's Python 3.11 floor,
and lock Pydantic, PyYAML and Typer plus test/lint/type/audit tools. Use local layered artifact storage
and a public GitHub repo with CI. Keneth Arias owns data contracts and platform decisions.
Do not install heavy analytical, geospatial or training dependencies until a task uses them.

## Alternatives
Cloud object storage and orchestration would add credentials, cost and administration before there
is a verified data slice. An unversioned notebook-only setup would make provenance and reproducibility
harder to enforce. Both remain possible later if measured requirements justify them.

## Consequences
Current setup requires no paid account or provider API key. Environmental data access still requires
per-source verification; public links imply no license grant. Local storage is not a backup system.
The lead must choose a backup/artifact-sharing strategy before the first irreplaceable acquisition.
