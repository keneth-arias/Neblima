"""Comandos de datos, entorno y adquisición explícita de originales.

Referencia de comandos y pruebas de Typer: https://typer.tiangolo.com/tutorial/testing/
"""

import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import typer

from airaware.acquisition.cli import acquisition_app
from airaware.catalog import CatalogError, load_catalog
from airaware.comparison.cli import comparison_app
from airaware.normalization.cli import normalization_app
from airaware.profiling.cli import profile_app

app = typer.Typer(
    no_args_is_help=True, help="Herramientas locales de datos y plataforma de AirAware."
)
catalog_app = typer.Typer(
    no_args_is_help=True, help="Revisar el inventario de fuentes sin usar la red."
)
workspace_app = typer.Typer(
    no_args_is_help=True, help="Preparar las carpetas locales de datos y resultados."
)
app.add_typer(acquisition_app, name="acquire")
app.add_typer(profile_app, name="profile")
app.add_typer(comparison_app, name="compare")
app.add_typer(catalog_app, name="catalog")
app.add_typer(workspace_app, name="workspace")
app.add_typer(normalization_app, name="normalize")
LAYERS = ("raw", "staging", "normalized", "curated", "benchmarks", "timef")
DataDirectory = Annotated[Path, typer.Option(envvar="AIRAWARE_DATA_DIR")]


@catalog_app.command("validate")
def catalog_validate(path: Path = Path("configs/sources.yaml")) -> None:
    """Validar metadatos y resumir estados de verificación sin hacer consultas de red."""
    try:
        catalog = load_catalog(path)
    except CatalogError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from None
    typer.echo(
        json.dumps(
            {
                "total": len(catalog.sources),
                "statuses": dict(Counter(source.status for source in catalog.sources)),
            },
            indent=2,
            sort_keys=True,
        )
    )


@workspace_app.command("init")
def workspace_init(data_dir: DataDirectory = Path("data")) -> None:
    """Crear las carpetas de cada etapa sin modificar los archivos existentes."""
    try:
        for layer in LAYERS:
            (data_dir.expanduser() / layer).mkdir(parents=True, exist_ok=True)
    except OSError:
        typer.echo(
            "No se pudieron crear las carpetas de trabajo; revisa la ruta y los permisos", err=True
        )
        raise typer.Exit(1) from None
    typer.echo("Carpetas de trabajo listas")


@app.command()
def doctor(
    catalog: Path = Path("configs/sources.yaml"),
    data_dir: DataDirectory = Path("data"),
) -> None:
    """Revisar el entorno local sin usar la red, escribir archivos ni mostrar credenciales."""
    try:
        load_catalog(catalog)
        catalog_ok = True
    except CatalogError:
        catalog_ok = False
    try:
        ZoneInfo("America/Lima")
        timezone_ok = True
    except ZoneInfoNotFoundError:
        timezone_ok = False
    root = data_dir.expanduser()
    checks = {
        "python": (3, 11) <= sys.version_info[:2] < (3, 14),
        "git": shutil.which("git") is not None,
        "uv": shutil.which("uv") is not None,
        "catalog": catalog_ok,
        "timezone": timezone_ok,
        "storage": all(
            (root / layer).is_dir() and os.access(root / layer, os.W_OK) for layer in LAYERS
        )
        and os.access(root, os.W_OK),
    }
    ready = all(checks.values())
    typer.echo(
        json.dumps(
            {
                "ready": ready,
                "python": sys.version.split()[0],
                "checks": checks,
                "github_cli_available": shutil.which("gh") is not None,
                "optional_credentials": {"OPENAQ_API_KEY": bool(os.environ.get("OPENAQ_API_KEY"))},
            },
            indent=2,
            sort_keys=True,
        )
    )
    if not ready:
        raise typer.Exit(1)
