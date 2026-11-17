"""Lectura CSV en streaming: SHA y encabezado validados antes de convertir."""

import csv
import hashlib
import io
from collections.abc import Iterator
from pathlib import Path

from airaware.normalization.convert import RowOutcomes, convert_row
from airaware.senamhi_preparation import PreparationPolicy

CHUNK = 1 << 20
REQUIRED_COLUMNS = ("FECHA", "HORA", "PM10", "PM2_5", "NO2")


def verify_source_sha(path: Path, expected_sha256: str) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK):
            digest.update(chunk)
    found = digest.hexdigest()
    if found != expected_sha256:
        raise ValueError(f"SHA-256 del original no coincide: {found}")
    return found


def validate_header(raw: list[str]) -> list[str]:
    if not raw or not all(raw):
        raise ValueError("Encabezado CSV vacío")
    if len(set(raw)) != len(raw):
        raise ValueError(f"Encabezado CSV con columnas duplicadas: {raw}")
    missing = [column for column in REQUIRED_COLUMNS if column not in raw]
    if missing:
        raise ValueError(f"Encabezado CSV sin columnas requeridas: {missing}")
    return raw


def iter_batches(
    records: Iterator[list[str]],
    header: list[str],
    policy: PreparationPolicy,
    batch_size: int,
) -> Iterator[list[RowOutcomes]]:
    """Numerar registros con encabezado=1 y agrupar tres resultados por fila en lotes."""
    if batch_size < 1:
        raise ValueError("batch_size debe ser positivo")
    return _batches(records, header, policy, batch_size)


def _batches(
    records: Iterator[list[str]],
    header: list[str],
    policy: PreparationPolicy,
    batch_size: int,
) -> Iterator[list[RowOutcomes]]:
    iterator = iter(records)
    batch: list[RowOutcomes] = []
    record = 1
    while True:
        record += 1
        try:
            values = next(iterator)
        except StopIteration:
            break
        except csv.Error as exc:
            message = f"registro CSV ilegible: {exc}"
            batch.append(convert_row(record, [], header, policy, forced_error=message))
        else:
            batch.append(convert_row(record, values, header, policy))
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def stream_observations(
    path: Path, policy: PreparationPolicy, batch_size: int = 500
) -> Iterator[list[RowOutcomes]]:
    """Verificar el SHA y devolver lotes por fila sin acumular el original completo."""
    verify_source_sha(path, policy.input_sha256)
    return _stream(path, policy, batch_size)


class _HashingInput(io.RawIOBase):
    """Registrar los bytes entregados al decodificador CSV."""

    def __init__(self, source: io.FileIO) -> None:
        super().__init__()
        self.source = source
        self.digest = hashlib.sha256()

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        count = self.source.readinto(buffer)
        if count is None:
            raise OSError("No se pudo leer el original")
        self.digest.update(memoryview(buffer)[:count])
        return count


def _stream(path: Path, policy: PreparationPolicy, batch_size: int) -> Iterator[list[RowOutcomes]]:
    with io.FileIO(path, "r") as source:
        hashed = _HashingInput(source)
        with io.TextIOWrapper(
            io.BufferedReader(hashed), encoding="utf-8-sig", newline=""
        ) as stream:
            reader = csv.reader(stream, delimiter=",", strict=True)
            header = validate_header(next(reader, []))
            yield from iter_batches(reader, header, policy, batch_size)
        if hashed.digest.hexdigest() != policy.input_sha256:
            raise ValueError("SHA-256 de los bytes convertidos no coincide con la política")
