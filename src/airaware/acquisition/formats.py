"""Validación estructural acotada; nunca corrige o reescribe los originales."""

import csv
import json
import zlib
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from airaware.acquisition.models import AcquisitionError, AcquisitionSpec

JSON_LIMIT = 8 * 1024 * 1024
XML_LIMIT = 8 * 1024 * 1024
ZIP_LIMIT = 32 * 1024 * 1024


def _json_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Clave JSON duplicada")
        result[key] = value
    return result


def _invalid_constant(value: str) -> object:
    raise ValueError("Constante JSON inválida")


def validate_format(path: Path, spec: AcquisitionSpec) -> None:
    """Aceptar CSV rectangular, JSON con claves o contenedores Office mínimos."""
    try:
        if spec.format == "csv":
            with path.open(encoding="utf-8-sig", newline="") as stream:
                rows = csv.reader(stream, delimiter=spec.csv_delimiter, strict=True)
                header = next(rows)
                if len(header) < 2 or len(set(header)) != len(header) or not all(header):
                    raise ValueError("Encabezado CSV inválido")
                if any("<" in field or ">" in field or "\x00" in field for field in header):
                    raise ValueError("HTML no es CSV")
                count = 0
                for row in rows:
                    if len(row) != len(header) or any("\x00" in field for field in row):
                        raise ValueError("Fila CSV inconsistente")
                    count += 1
                if count == 0:
                    raise ValueError("CSV sin observaciones")
        elif spec.format == "json":
            if path.stat().st_size > JSON_LIMIT:
                raise ValueError("JSON supera el límite de análisis")
            data = json.loads(
                path.read_text(encoding="utf-8-sig"),
                object_pairs_hook=_json_pairs,
                parse_constant=_invalid_constant,
            )
            if not isinstance(data, dict) or not all(k in data for k in spec.json_required_keys):
                raise ValueError("JSON no cumple el contrato de claves")
        else:
            member = "xl/workbook.xml" if spec.format == "xlsx" else "word/document.xml"
            expected = (
                "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}workbook"
                if spec.format == "xlsx"
                else "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document"
            )
            required = {"[Content_Types].xml", "_rels/.rels", member}
            with ZipFile(path) as archive:
                entries = archive.infolist()
                if (
                    len(entries) > 512
                    or len({e.filename for e in entries}) != len(entries)
                    or sum(e.file_size for e in entries) > ZIP_LIMIT
                    or not required <= set(archive.namelist())
                ):
                    raise ValueError("Contenedor Office inválido")
                for entry in entries:
                    if (
                        entry.file_size > XML_LIMIT
                        or entry.flag_bits & 1
                        or "vbaproject" in entry.filename.lower()
                        or entry.file_size > max(1, entry.compress_size) * 200
                    ):
                        raise ValueError("Contenedor Office no admitido")
                if archive.testzip() is not None:
                    raise ValueError("Suma ZIP inválida")
                for name in required:
                    content = archive.read(name)
                    if (
                        b"\x00" in content
                        or b"<!DOCTYPE" in content.upper()
                        or b"<!ENTITY" in content.upper()
                    ):
                        raise ValueError("Declaraciones XML no admitidas")
                    root = ElementTree.fromstring(content)
                    if name == member and root.tag != expected:
                        raise ValueError("Documento Office incorrecto")
    except (
        ValueError,
        OSError,
        UnicodeError,
        csv.Error,
        StopIteration,
        BadZipFile,
        zlib.error,
        ElementTree.ParseError,
        RuntimeError,
        RecursionError,
    ) as error:
        raise AcquisitionError(
            "El archivo no cumple el formato y los límites declarados"
        ) from error
