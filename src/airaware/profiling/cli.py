"""Ejecutar perfiles locales por fuente; un fallo no oculta las otras entregas."""

import json
from pathlib import Path
from typing import Annotated, Literal

import duckdb
import typer
from pydantic import BaseModel, ConfigDict, Field

from airaware.profiling.engine import ProfileSpec, profile

profile_app = typer.Typer(
    no_args_is_help=True, help="Medir cobertura y calidad sin normalizar datos."
)


class ProfilePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    datasets: list[ProfileSpec] = Field(min_length=1, max_length=8)


@profile_app.command("run")
def run_profiles(
    config: Annotated[Path, typer.Option(help="Plan JSON local, hasta 64 KiB.")] = Path(
        "configs/profiling.json"
    ),
    output_root: Annotated[
        Path, typer.Option(help="Carpeta de nuevos informes; nunca sobre raw.")
    ] = Path("reports/generated/profiling"),
    source: Annotated[
        list[str] | None, typer.Option(help="Fuente exacta; opción repetible.")
    ] = None,
    data_dir: Annotated[
        Path | None,
        typer.Option(
            envvar="AIRAWARE_DATA_DIR", help="Reubicar la carpeta base de originales/manifiestos."
        ),
    ] = None,
) -> None:
    """Comprobar adquisición, perfilar cada fuente y publicar Parquet con procedencia."""
    try:
        with config.open("rb") as stream:
            content = stream.read(65537)
        if len(content) > 65536:
            raise ValueError("Configuración excesiva")
        plan = ProfilePlan.model_validate_json(content)
        if source and not set(source) <= {s.source_id for s in plan.datasets}:
            raise ValueError("Fuente desconocida")
        selected = [s for s in plan.datasets if not source or s.source_id in source]
        if data_dir is not None:
            selected = [
                s.model_copy(
                    update={
                        "manifest": data_dir
                        / "raw"
                        / s.manifest.resolve().relative_to(s.raw_root.resolve()),
                        "raw_root": data_dir / "raw",
                    }
                )
                for s in selected
            ]
    except (OSError, ValueError):
        typer.echo("No se pudo validar el plan local de perfilamiento", err=True)
        raise typer.Exit(1) from None
    completed = []
    errors = []
    for spec in selected:
        try:
            report = profile(
                spec, output_root, progress=lambda message: typer.echo(message, err=True)
            )
            completed.append({"source_id": spec.source_id, "report": str(report)})
        except (OSError, ValueError, duckdb.Error):
            errors.append(
                {"source_id": spec.source_id, "error": "No se pudo completar o verificar el perfil"}
            )
    typer.echo(json.dumps({"completed": completed, "errors": errors}, indent=2))
    if errors:
        raise typer.Exit(1)
