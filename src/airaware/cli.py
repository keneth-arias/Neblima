"""Offline foundation commands; acquisition commands are implemented in later issues.

Typer command/testing patterns: https://typer.tiangolo.com/tutorial/testing/
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

from airaware.catalog import CatalogError, load_catalog

app = typer.Typer(no_args_is_help=True, help="AirAware local data and platform tools.")
catalog_app = typer.Typer(no_args_is_help=True, help="Inspect the offline source inventory.")
workspace_app = typer.Typer(no_args_is_help=True, help="Prepare local artifact directories.")
app.add_typer(catalog_app, name="catalog")
app.add_typer(workspace_app, name="workspace")
LAYERS = ("raw", "staging", "normalized", "curated", "benchmarks", "timef")
DataDirectory = Annotated[Path, typer.Option(envvar="AIRAWARE_DATA_DIR")]


@catalog_app.command("validate")
def catalog_validate(path: Path = Path("configs/sources.yaml")) -> None:
    """Validate source metadata and summarize verification status, without making requests."""
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
    """Create missing layer directories, preserving all existing files."""
    try:
        for layer in LAYERS:
            (data_dir.expanduser() / layer).mkdir(parents=True, exist_ok=True)
    except OSError:
        typer.echo("Cannot create workspace directories; check path and permissions", err=True)
        raise typer.Exit(1) from None
    typer.echo("Workspace layers ready")


@app.command()
def doctor(
    catalog: Path = Path("configs/sources.yaml"),
    data_dir: DataDirectory = Path("data"),
) -> None:
    """Check local readiness without network calls, writes, or credential disclosure."""
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
