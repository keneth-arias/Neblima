"""Lectura de investigación, separada del importador genérico; no escribe los libros."""

import math
import re
import unicodedata
from datetime import date, datetime, time, timedelta
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

MISSING = {"", "-", "NA", "N/A", "NULL", "ND", "N/D"}


def fold(value):
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(value)).lower() if not unicodedata.combining(c)
    )


def numeric_value(value):
    token = "" if value is None else str(value).strip()
    if token.upper() in MISSING:
        return "missing", None
    if re.match(r"^[<>≤≥]", token):
        return "censored", None
    if isinstance(value, bool):
        return "unparsed", None
    try:
        number = float(token)
    except ValueError:
        return "unparsed", None
    return ("finite", number) if math.isfinite(number) else ("nonfinite", None)


def date_value(value, epoch):
    if isinstance(value, datetime):
        return value.date(), "native_datetime"
    if isinstance(value, date):
        return value, "native_date"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isfinite(value) and 25000 <= value <= 60000 and value % 1 == 0:
            return from_excel(value, epoch).date(), "numeric_with_workbook_epoch"
        return None, "unsupported_numeric_date"
    token = "" if value is None else str(value).strip()
    if token.upper() in MISSING:
        return None, "missing"
    for fmt, pattern in (("%Y-%m-%d", r"\d{4}-\d{2}-\d{2}"), ("%Y%m%d", r"\d{8}")):
        if re.fullmatch(pattern, token):
            try:
                return datetime.strptime(token, fmt).date(), "iso_or_yyyymmdd"
            except ValueError:
                return None, "invalid_date"
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", token)
    if match:
        first, second, year = map(int, match.groups())
        if first <= 12 and second <= 12:
            return None, "ambiguous_text_date"
        try:
            if first > 12:
                return date(year, second, first), "unambiguous_dmy"
            return date(year, first, second), "unambiguous_mdy"
        except ValueError:
            return None, "invalid_date"
    return None, "unsupported_date"


def clock_value(value):
    if isinstance(value, time):
        return value, "native_time"
    if isinstance(value, datetime):
        if value.date() in {date(1899, 12, 30), date(1899, 12, 31), date(1900, 1, 1)}:
            return value.time(), "base_date_and_clock"
        return None, "unresolved_datetime_clock"
    if isinstance(value, timedelta):
        value = value.total_seconds() / 86400
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isfinite(value) and 0 <= value < 1:
            micros = round(value * 86400 * 1_000_000)
            if micros >= 86400 * 1_000_000:
                return None, "clock_rollover"
            return (datetime(2000, 1, 1) + timedelta(microseconds=micros)).time(), "excel_fraction"
        return None, "unsupported_numeric_clock"
    token = "" if value is None else str(value).strip()
    if token.upper() in MISSING:
        return None, "missing"
    match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?", token)
    if match:
        h, m, s, us = match.groups()
        try:
            return time(int(h), int(m), int(s or 0), int((us or "").ljust(6, "0"))), "text_clock"
        except ValueError:
            return None, "invalid_clock"
    return None, "unsupported_clock"


def parameter_family(value):
    token = fold(value)
    if "25 micra" in token and re.search(r"\bpm\s*2", token):
        return "pm25_ambiguous"
    is_concentration = bool(
        re.match(
            r"^(material\s+particulado\b|concentracion\s+de\s+particulas\b|particulas\s+pm)",
            token,
        )
        or re.fullmatch(r"pm\s*(10|2[,.]\s*5|25)", token)
    )
    if not is_concentration:
        return "pm_related_non_target" if re.search(r"\bpm\s*(10|2|25)", token) else "other"
    if re.search(r"\bpm\s*10\b", token):
        return "pm10"
    if "25 micra" in token or re.search(r"\bpm\s*25\b", token):
        return "pm25_ambiguous"
    if re.search(r"\bpm\s*2[,.]\s*5\b", token):
        return "pm25"
    return "other"


def iter_records(path: Path):
    wb = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    try:
        for ws in wb.worksheets:
            ws.reset_dimensions()
            rows = ws.iter_rows()
            header = [str(c.value).strip() if c.value is not None else "" for c in next(rows)]
            if not all(header) or len(set(header)) != len(header):
                raise ValueError("Encabezados vacíos o repetidos")
            for row_number, row in enumerate(rows, 2):
                if not any(c.value is not None for c in row):
                    continue
                if len(row) > len(header):
                    raise ValueError("Columnas fuera del contrato")
                values = {header[i]: c.value for i, c in enumerate(row)}
                yield {
                    "sheet": ws.title,
                    "row": row_number,
                    "epoch": wb.epoch,
                    "values": values,
                    "formula_fields": [header[i] for i, c in enumerate(row) if c.data_type == "f"],
                    "error_fields": [header[i] for i, c in enumerate(row) if c.data_type == "e"],
                }
    finally:
        wb.close()
