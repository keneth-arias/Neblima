"""Exportar una muestra verificada de SENAMHI a un registro TimeF local."""

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timedelta
from hashlib import file_digest
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
from senamhi_timef import pm25_record
from timenet.dataset import TimeFDataset
from timenet.reader import TimeFReader
from timenet.types import DatasetMetadata, License

ROOT = Path(__file__).resolve().parents[2]
DATASET_ID = "airaware/senamhi-lima-pm25-sample"
CATALOG = (
    "https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-"
    "lima-metropolitana-servicio-nacional-de"
)


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def read_sample(
    grid: Path, *, station_key: str, start: datetime, hours: int, source: dict
) -> TimeFDataset:
    """Seleccionar un intervalo explícito y conservar nulos y procedencia por casilla."""
    if start.utcoffset() != timedelta(0) or (start.minute or start.second or start.microsecond):
        raise ValueError("La muestra debe empezar en una hora exacta UTC")
    if not 1 <= hours <= 744:
        raise ValueError("La muestra debe contener entre 1 y 744 horas")
    parquet = grid / "hours.parquet"
    manifest = json.loads((grid / "manifest.json").read_text(encoding="utf-8"))
    digest = sha256_file(parquet)
    if manifest["version"] != "senamhi-hourly-v1" or manifest["output_sha256"] != digest:
        raise ValueError("La versión o el SHA-256 de la grilla difiere del manifiesto")
    with duckdb.connect(config={"threads": 2}) as db:
        db.execute("SET TimeZone = 'UTC'")
        table = db.execute(
            """
            SELECT series_id, observed_at, value, status, observation_id, source_observation_ids
            FROM read_parquet(?, hive_partitioning = false)
            WHERE station_key = ? AND parameter_raw = 'PM2_5' AND unit = 'ug/m3'
              AND observed_at >= ? AND observed_at < ?
            ORDER BY observed_at
            """,
            [str(parquet), station_key, start, start + timedelta(hours=hours)],
        ).to_arrow_table()
    if sha256_file(parquet) != digest:
        raise ValueError("La grilla cambió durante la lectura")
    times = table["observed_at"].to_pylist()
    expected = [start + timedelta(hours=i) for i in range(hours)]
    if times != expected or len(set(table["series_id"].to_pylist())) != 1:
        raise ValueError("La selección debe contener una sola serie horaria completa en el eje")
    dataset = TimeFDataset(
        metadata=DatasetMetadata(
            dataset_id=DATASET_ID,
            dataset_version="0.1.0",
            name="Muestra horaria de PM2.5 de Lima",
            description="Muestra local de SENAMHI con depuración y nulos explícitos de AirAware.",
            license=License.ODC_BY_1_0,
            license_url="https://opendatacommons.org/licenses/by/1-0/",
            source_url=CATALOG,
            source_revision=source["input_sha256"],
            citation=(
                "SENAMHI, Monitoreo de los contaminantes del aire en Lima Metropolitana. "
                "Adaptación horaria de AirAware con depuración y nulos explícitos."
            ),
        )
    )
    dataset.add_record(
        record=pm25_record(
            station_key=station_key,
            start=start,
            values=table["value"].combine_chunks(),
            provenance={
                **source,
                "grid_sha256": digest,
                "audit_sha256": manifest["input_sha256"],
                "series_id": table["series_id"][0].as_py(),
                "observation_ids": table["observation_id"].to_pylist(),
                "source_observation_ids": table["source_observation_ids"].to_pylist(),
                "hour_status": table["status"].to_pylist(),
                "unit_basis": "inferred_accepted_by_project_lead",
                "interval_position": "unknown",
                "quality": "unknown",
            },
        )
    )
    return dataset


def build_from_normalized(
    normalized: Path, *, station_key: str, start: datetime, hours: int
) -> TimeFDataset:
    """Verificar y preparar el insumo con los comandos de AirAware antes de convertir."""
    manifest_file = normalized / "manifest.json"
    digest = sha256_file(manifest_file)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    with TemporaryDirectory(prefix="airaware-timef-") as temp:
        audit = Path(temp) / "audit.parquet"
        grid = Path(temp) / "grid"
        command = ["uv", "run", "--locked", "--offline", "airaware"]
        subprocess.run(
            [*command, "curate", "senamhi", "--input", str(normalized), "--output", str(audit)],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            [*command, "align", "senamhi", "--input", str(audit), "--output", str(grid)],
            cwd=ROOT,
            check=True,
        )
        if sha256_file(manifest_file) != digest:
            raise ValueError("El manifiesto de normalización cambió durante la conversión")
        return read_sample(
            grid,
            station_key=station_key,
            start=start,
            hours=hours,
            source={
                "source_id": manifest["source_id"],
                "input_sha256": manifest["input_sha256"],
                "normalization_manifest_sha256": digest,
                "policy_id": manifest["policy_id"],
                "rejections": manifest["rejection_trace"]["rows"],
                "rejection_trace_sha256": manifest["rejection_trace"]["sha256"],
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--station-key", required=True)
    parser.add_argument("--start", type=datetime.fromisoformat, required=True)
    parser.add_argument("--hours", type=int, required=True)
    args = parser.parse_args()
    dataset = build_from_normalized(
        args.normalized.resolve(), station_key=args.station_key, start=args.start, hours=args.hours
    )
    release = dataset.write(path=args.registry)
    shutil.copyfile(ROOT / "DATA_ATTRIBUTION.md", release / "DATA_ATTRIBUTION.md")
    with TimeFReader.open(release) as reader:
        reader.verify()
    print(f"Versión TimeF verificada: {release}")


if __name__ == "__main__":
    main()
