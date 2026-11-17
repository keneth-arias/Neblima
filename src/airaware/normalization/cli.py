"""Comando de normalización SENAMHI al contrato Observation."""

import json
from pathlib import Path
from typing import Annotated

import typer

from airaware.normalization import stream_observations, write_parquet_output
from airaware.senamhi_preparation import load_policy

normalization_app = typer.Typer(
    no_args_is_help=True, help="Normalizar originales verificados al contrato Observation."
)


@normalization_app.command("senamhi")
def normalize_senamhi(
    input: Annotated[
        Path, typer.Option(help="CSV original SENAMHI verificado contra el SHA de la política.")
    ] = Path("data/raw/senamhi/senamhi_lima_monitoreo_1.csv"),
    policy: Annotated[
        Path, typer.Option(help="Política YAML con el SHA esperado del original.")
    ] = Path("configs/normalization/senamhi.yaml"),
    output: Annotated[
        Path, typer.Option(help="Carpeta de salida nueva; nunca se sobrescribe.")
    ] = Path("data/normalized/senamhi/senamhi-normalization-20261117-v1"),
    batch_size: Annotated[int, typer.Option(help="Filas por lote; entero positivo.")] = 500,
) -> None:
    """Convertir el original SENAMHI a Parquet contractual en una carpeta nueva."""
    if batch_size < 1:
        typer.echo("No se pudo normalizar: batch_size debe ser positivo", err=True)
        raise typer.Exit(1) from None
    try:
        loaded = load_policy(policy)
        manifest = write_parquet_output(
            stream_observations(input, loaded, batch_size=batch_size), loaded, output
        )
    except (OSError, ValueError) as error:
        typer.echo(f"No se pudo normalizar: {error}", err=True)
        raise typer.Exit(1) from None
    typer.echo(
        json.dumps(
            {
                "input": str(input),
                "input_sha256": manifest.input_sha256,
                "policy_id": manifest.policy_id,
                "output": str(output),
                "manifest": str(output / "manifest.json"),
                "counts": {
                    "input_rows": manifest.counts.input_rows,
                    "observations": manifest.counts.observations.total,
                    "rejections": manifest.counts.rejections.total,
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
