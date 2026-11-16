"""Entradas explícitas para originales descargados y API documentadas."""

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from airaware.acquisition.http import fetch_api
from airaware.acquisition.models import AcquisitionError, AcquisitionResult, AcquisitionSpec
from airaware.acquisition.store import ingest_file

acquisition_app = typer.Typer(
    no_args_is_help=True, help="Adquirir originales con integridad y procedencia verificables."
)
DataDirectory = Annotated[Path, typer.Option(envvar="AIRAWARE_DATA_DIR")]
SpecFile = Annotated[Path, typer.Option("--spec", help="Solicitud JSON local con límite de bytes.")]


def _read_spec(path: Path) -> AcquisitionSpec:
    if path.stat().st_size > 64 * 1024:
        raise AcquisitionError("La solicitud supera el límite de configuración")
    return AcquisitionSpec.model_validate_json(path.read_bytes())


def _show_result(result: AcquisitionResult) -> None:
    typer.echo(
        json.dumps(
            {
                "artifact": str(result.artifact),
                "manifest": str(result.manifest),
                "reused": result.reused,
            },
            indent=2,
        )
    )


def _fail() -> None:
    typer.echo(
        "No se pudo validar o completar la adquisición; revisa la solicitud y la integridad",
        err=True,
    )
    raise typer.Exit(1) from None


@acquisition_app.command("import-file")
def import_file(
    spec_file: SpecFile,
    file: Annotated[Path, typer.Option("--file", help="Archivo original obtenido previamente.")],
    data_dir: DataDirectory = Path("data"),
) -> None:
    """Preservar o verificar un original local sin volver a descargarlo."""
    try:
        _show_result(ingest_file(_read_spec(spec_file), file, data_dir))
    except (AcquisitionError, ValidationError, OSError, ValueError):
        _fail()


@acquisition_app.command("api")
def acquire_api(
    spec_file: SpecFile,
    allow_host: Annotated[list[str], typer.Option(help="Host exacto de API pública autorizado.")],
    data_dir: DataDirectory = Path("data"),
) -> None:
    """Consultar una API documentada con límites; no sustituye a Lightpanda para páginas web."""
    try:
        _show_result(fetch_api(_read_spec(spec_file), data_dir, allowed_hosts=set(allow_host)))
    except (AcquisitionError, ValidationError, OSError, ValueError):
        _fail()
