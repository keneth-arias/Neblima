"""Ejecución explícita local de la comparación aprobada."""

from pathlib import Path
from typing import Annotated

import duckdb
import typer
import yaml

from airaware.comparison.models import Policy
from airaware.comparison.runner import compare
from airaware.profiling.cli import ProfilePlan

comparison_app = typer.Typer(
    no_args_is_help=True, help="Comparar cobertura sin inventar elegibilidad."
)


def _read(path: Path) -> bytes:
    with path.open("rb") as stream:
        body = stream.read(65537)
    if len(body) > 65536:
        raise ValueError("Configuración excesiva")
    return body


@comparison_app.command("run")
def run_comparison(
    policy: Path = Path("configs/benchmark.yaml"),
    inputs: Path = Path("configs/profiling.json"),
    output_root: Path = Path("reports/generated/comparison"),
    data_dir: Annotated[Path | None, typer.Option(envvar="AIRAWARE_DATA_DIR")] = None,
) -> None:
    """Verificar originales, contar las 16 parejas y publicar Parquet/JSON con hashes."""
    try:
        configuration = Policy.model_validate(yaml.safe_load(_read(policy)))
        specs = ProfilePlan.model_validate_json(_read(inputs)).datasets
        if data_dir is not None:
            specs = [
                s.model_copy(
                    update={
                        "manifest": data_dir
                        / "raw"
                        / s.manifest.resolve().relative_to(s.raw_root.resolve()),
                        "raw_root": data_dir / "raw",
                    }
                )
                for s in specs
            ]
        result = compare(specs, configuration, output_root)
    except (OSError, ValueError, yaml.YAMLError, duckdb.Error):
        typer.echo("No se pudo verificar o completar la comparación local", err=True)
        raise typer.Exit(1) from None
    typer.echo(str(result))
