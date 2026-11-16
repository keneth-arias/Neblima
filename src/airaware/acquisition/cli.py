"""Entradas explícitas para originales descargados y API documentadas."""

import json
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from airaware.acquisition.batch import BatchPlan, estimate_jobs, execute_jobs, select_jobs
from airaware.acquisition.budget import ByteBudget
from airaware.acquisition.models import AcquisitionError, AcquisitionResult, AcquisitionSpec
from airaware.acquisition.public_file import fetch_public_file
from airaware.acquisition.store import ingest_file
from airaware.acquisition.transfer import fetch_cached_api as fetch_api

acquisition_app = typer.Typer(
    no_args_is_help=True, help="Adquirir originales con integridad y procedencia verificables."
)
DataDirectory = Annotated[Path, typer.Option(envvar="AIRAWARE_DATA_DIR")]
SpecFile = Annotated[Path, typer.Option("--spec", help="Solicitud JSON local con límite de bytes.")]


def _read_spec(path: Path) -> AcquisitionSpec:
    with path.open("rb") as stream:
        content = stream.read(64 * 1024 + 1)
    if len(content) > 64 * 1024:
        raise AcquisitionError("La solicitud supera el límite de configuración")
    return AcquisitionSpec.model_validate_json(content)


def _show_result(result: AcquisitionResult, network_bytes: int | None = None) -> None:
    typer.echo(
        json.dumps(
            {
                "artifact": str(result.artifact),
                "manifest": str(result.manifest),
                "reused": result.reused,
                **({"network_bytes": network_bytes} if network_bytes is not None else {}),
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
    offline: Annotated[bool, typer.Option(help="Verificar caché local sin red ni DNS.")] = False,
    refresh: Annotated[
        bool, typer.Option(help="Consultar sin condición de caché y reiniciar parcial.")
    ] = False,
    budget_bytes: Annotated[
        int | None, typer.Option(help="Presupuesto total de payload e intentos.")
    ] = None,
    deadline_seconds: Annotated[
        float, typer.Option(help="Presupuesto temporal; máximo 86400 s.")
    ] = 60,
) -> None:
    """Consultar una API documentada con límites; no sustituye a Lightpanda para páginas web."""
    try:
        _show_result(
            fetch_api(
                _read_spec(spec_file),
                data_dir,
                allowed_hosts=set(allow_host),
                offline=offline,
                refresh=refresh,
                network_budget=ByteBudget(budget_bytes) if budget_bytes is not None else None,
                deadline_seconds=deadline_seconds,
            )
        )
    except (AcquisitionError, ValidationError, OSError, ValueError):
        _fail()


@acquisition_app.command("batch")
def acquire_batch(
    plan: Annotated[Path, typer.Option(help="Plan JSON de recursos; máximo 2 MiB.")],
    data_dir: DataDirectory = Path("data"),
    source: Annotated[
        list[str] | None, typer.Option(help="ID de fuente exacto; repetible.")
    ] = None,
    region: Annotated[
        list[str] | None, typer.Option(help="Región declarada exacta; repetible.")
    ] = None,
    start: Annotated[str | None, typer.Option(help="Inicio inclusivo YYYY-MM-DD.")] = None,
    end: Annotated[str | None, typer.Option(help="Fin inclusivo YYYY-MM-DD.")] = None,
    dry_run: Annotated[
        bool, typer.Option(help="Estimar sin GET/HEAD/DNS ni crear adquisiciones.")
    ] = False,
    offline: Annotated[
        bool, typer.Option(help="Solo originales locales verificados; sin red.")
    ] = False,
    allow_host: Annotated[
        list[str] | None, typer.Option(help="Host de API autorizado; repetible.")
    ] = None,
    budget_bytes: Annotated[int, typer.Option(help="Presupuesto total de payload de red.")] = 0,
    workers: Annotated[int, typer.Option(help="Tareas simultáneas, de 1 a 4.")] = 1,
    authorize_unknown: Annotated[
        bool, typer.Option(help="Autorizar tamaños desconocidos dentro de límites explícitos.")
    ] = False,
    deadline_seconds: Annotated[float, typer.Option(help="Presupuesto temporal por recurso.")] = 60,
) -> None:
    """Seleccionar recursos por metadatos; no recorta filas ni inventa cobertura."""
    try:
        with plan.open("rb") as stream:
            content = stream.read(2 * 1024 * 1024 + 1)
        if len(content) > 2 * 1024 * 1024:
            raise AcquisitionError("El plan supera 2 MiB")
        request = BatchPlan.model_validate_json(content)
        selected = select_jobs(
            request.jobs,
            sources=set(source) if source else None,
            regions=set(region) if region else None,
            start=date.fromisoformat(start) if start else None,
            end=date.fromisoformat(end) if end else None,
        )
        if dry_run:
            typer.echo(
                json.dumps(
                    {
                        **estimate_jobs(selected),
                        "input_count": len(request.jobs),
                        "selected_count": len(selected),
                    },
                    indent=2,
                )
            )
            return
        outcome = execute_jobs(
            selected,
            data_dir,
            budget_bytes=budget_bytes,
            workers=workers,
            offline=offline,
            allowed_hosts=set(allow_host or []),
            authorize_unknown=authorize_unknown,
            deadline_seconds=deadline_seconds,
        )
        typer.echo(
            json.dumps(
                {
                    "completed": [
                        {
                            "artifact": str(r.artifact),
                            "manifest": str(r.manifest),
                            "reused": r.reused,
                        }
                        for r in outcome["completed"]
                    ],
                    "errors": outcome["errors"],
                    "network_bytes": outcome["network_bytes"],
                },
                indent=2,
            )
        )
        if outcome["errors"]:
            raise typer.Exit(1)
    except (AcquisitionError, ValidationError, OSError, ValueError):
        _fail()


@acquisition_app.command("file")
def acquire_public_file(
    spec_file: SpecFile,
    allow_host: Annotated[list[str], typer.Option(help="Host exacto autorizado del archivo.")],
    budget_bytes: Annotated[
        int, typer.Option(help="Presupuesto compartido de consulta y transferencia.")
    ],
    data_dir: DataDirectory = Path("data"),
    offline: Annotated[
        bool, typer.Option(help="Solo verificar caché local, sin consultar el recurso.")
    ] = False,
    deadline_seconds: Annotated[
        float, typer.Option(help="Plazo cooperativo del recurso, hasta 86400 s.")
    ] = 1200,
) -> None:
    """Adquirir un archivo público estático resuelto previamente con Lightpanda."""
    try:
        if budget_bytes < 0 or (not offline and budget_bytes == 0):
            raise AcquisitionError("Se requiere presupuesto explícito para transferir")
        budget = ByteBudget(budget_bytes or 1)
        result = fetch_public_file(
            _read_spec(spec_file),
            data_dir,
            allowed_hosts=set(allow_host),
            network_budget=budget,
            offline=offline,
            deadline_seconds=deadline_seconds,
        )
        _show_result(result, budget.used)
    except (AcquisitionError, ValidationError, OSError, ValueError):
        _fail()
