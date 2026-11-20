"""Conservar las capturas horarias de PM2.5 en Campo de Marte y auditar su primera recepción."""

import argparse
import fcntl
import hashlib
import json
import math
import re
import subprocess
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlencode, urlsplit

from stage_external_pm import readings

ENDPOINT = "https://www.senamhi.gob.pe/site/sea/www/site/sea/graficas/dato_hora.php"


def chart_url(first: date, last: date) -> str:
    return (
        ENDPOINT
        + "?"
        + urlencode(
            {
                "estacion": "112194",
                "cont": "N_PM25",
                "f1": first.strftime("%d/%m/%Y"),
                "f2": last.strftime("%d/%m/%Y"),
            }
        )
    )


def validate(raw, receipt):
    parts = urlsplit(receipt["url"])
    fields = parse_qs(parts.query, strict_parsing=True)
    if (
        receipt["url"].partition("?")[0] != ENDPOINT
        or parts.fragment
        or set(fields) != {"estacion", "cont", "f1", "f2"}
        or any(len(v) != 1 for v in fields.values())
        or fields["estacion"] != ["112194"]
        or fields["cont"] != ["N_PM25"]
    ):
        raise ValueError("URL de otra fuente, estación o parámetro")
    first, last = (datetime.strptime(fields[k][0], "%d/%m/%Y").date() for k in ("f1", "f2"))
    if not 0 <= (last - first).days <= 2:
        raise ValueError("La consulta admite de uno a tres días")
    arrival = datetime.fromisoformat(receipt["recuperado_utc"])
    if arrival.tzinfo is None:
        raise ValueError("La recepción requiere una hora UTC inequívoca")
    if (
        receipt["http_status"] not in (None, 200, 201, 202, 203)
        or len(raw) > 1_000_000
        or len(raw) != receipt["bytes"]
        or hashlib.sha256(raw).hexdigest() != receipt["sha256"]
    ):
        raise ValueError("La huella o el tamaño difieren de los bytes recibidos")
    html = raw.decode("latin-1")
    if not re.search(r"title:\s*\{\s*text:\s*'[^']*CAMPO DE MARTE[^']*'", html):
        raise ValueError("El gráfico no identifica la estación y el contaminante esperados")
    points = {}
    for hour, value in readings(
        html, expected_series="Material Particulado menor a 2.5 micras (PM2.5)"
    ):
        if (
            hour in points
            or hour.minute
            or not first <= hour.date() <= last
            or (value is not None and not math.isfinite(value))
        ):
            raise ValueError("Hora repetida, fuera de la consulta o con lectura no finita")
        points[hour] = value
    return arrival.astimezone(UTC), first, last, points


def register(root, raw, receipt):
    arrival, _, _, _ = validate(raw, receipt)
    # La ruta del archivo en la adquisición anterior no forma parte de esta identidad.
    keep = {k: receipt[k] for k in ("url", "recuperado_utc", "bytes", "sha256", "http_status")}
    keep["recuperado_utc"] = arrival.isoformat()
    root.mkdir(parents=True, exist_ok=True)
    target = root / arrival.strftime("%Y%m%dT%H%M%S.%fZ")
    with (root / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if target.exists():
            if (
                json.loads((target / "receipt.json").read_bytes()) != keep
                or (target / "chart.html").read_bytes() != raw
            ):
                raise ValueError("Recepción en conflicto con la captura anterior")
            return target
        with TemporaryDirectory(dir=root) as tmp:
            stage = Path(tmp) / "snapshot"
            stage.mkdir()
            (stage / "chart.html").write_bytes(raw)
            (stage / "receipt.json").write_text(json.dumps(keep, sort_keys=True, indent=2) + "\n")
            stage.rename(target)
    return target


def audit(root, through=None, *, include_receipts=False, allow_empty=False):
    receipts = []
    last_check, last_listed, changes, previous_change = {}, {}, [], {}
    counts = {"first_value": 0, "revision": 0, "withdrawn": 0}
    snapshots = sorted(root.glob("????????T??????.??????Z"))
    if through is not None:
        cutoff = datetime.fromisoformat(through)
        if cutoff.tzinfo is None:
            raise ValueError("El corte de auditoría requiere una zona horaria")
        key = cutoff.astimezone(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        snapshots = [path for path in snapshots if path.name <= key]
    if not snapshots and not (allow_empty and root.is_dir()):
        raise ValueError("No hay capturas para auditar")
    for path in snapshots:
        receipt_bytes = (path / "receipt.json").read_bytes()
        r = json.loads(receipt_bytes)
        arrival, first, last, points = validate((path / "chart.html").read_bytes(), r)
        if path.name != arrival.strftime("%Y%m%dT%H%M%S.%fZ"):
            raise ValueError("La hora del recibo difiere de su directorio")
        seen = arrival.isoformat()
        if include_receipts:
            receipts.append(
                {
                    "seen_utc": seen,
                    "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
                    "chart_sha256": r["sha256"],
                }
            )
        start = datetime.combine(first, time.min)
        for i in range(24 * ((last - first).days + 1)):
            hour = start + timedelta(hours=i)
            value = points.get(hour)
            state = "unlisted" if hour not in points else "null" if value is None else "finite"
            preceding_state, checked_at = last_check.get(hour, (None, None))
            last_check[hour] = state, seen
            if state == "unlisted":
                continue
            old = last_listed.get(hour)
            last_listed[hour] = value
            if old == value:
                continue
            if value is None:
                kind = "withdrawn"
            elif hour in previous_change:
                kind = "revision"
            else:
                kind = "first_value"
            counts[kind] += 1
            changes.append(
                {
                    "station_hour": hour.isoformat(),
                    "kind": kind,
                    "value": value,
                    "seen_utc": seen,
                    "preceding_query_state": preceding_state,
                    "last_checked_without_value_utc": checked_at
                    if preceding_state == "null"
                    else None,
                    "previous_check_utc": checked_at,
                    "source_sha256": r["sha256"],
                    "previous_change_utc": previous_change.get(hour),
                }
            )
            previous_change[hour] = seen
    return {
        "source": "senamhi_horario",
        "station": "112194",
        "parameter": "pm25",
        "observation_timezone": None,
        "snapshots": len(snapshots),
        **({"receipts": receipts} if include_receipts else {}),
        "coverage_by_station_hour": {
            h.isoformat(): {
                "last_queried_utc": at,
                "last_query_state": state,
                "in_latest_query": at == seen,
            }
            for h, (state, at) in sorted(last_check.items())
        },
        "counts": counts,
        "changes": changes,
    }


def capture(root):
    today = datetime.now(UTC).date()
    url = chart_url(today - timedelta(days=2), today)
    calls = [
        ("goto", {"url": "about:blank", "timeout": 15000, "waitUntil": "domcontentloaded"}),
        ("download", {"url": url, "path": "chart.html"}),
    ]
    requests = "".join(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {"name": name, "arguments": args},
            }
        )
        + "\n"
        for i, (name, args) in enumerate(calls, 1)
    )
    with TemporaryDirectory() as tmp:
        result = subprocess.run(
            ["lightpanda", "mcp"],
            input=requests,
            text=True,
            cwd=tmp,
            capture_output=True,
            timeout=45,
            check=True,
        )
        responses = {v["id"]: v for v in map(json.loads, result.stdout.splitlines()) if "id" in v}
        if set(responses) != {1, 2} or any(
            "result" not in v or "error" in v or v["result"].get("isError")
            for v in responses.values()
        ):
            raise ValueError("Lightpanda no completó la consulta")
        arrival = datetime.now(UTC).isoformat()
        raw = (Path(tmp) / "chart.html").read_bytes()
        return register(
            root,
            raw,
            {
                "url": url,
                "recuperado_utc": arrival,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "http_status": responses[2]["result"]
                .get("structuredContent", {})
                .get("httpStatus"),
            },
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("capture", "import", "audit"):
        cmd = commands.add_parser(name)
        cmd.add_argument("root", type=Path)
        if name == "audit":
            cmd.add_argument("--through", help="Última recepción UTC incluida (ISO 8601)")
        if name == "import":
            cmd.add_argument("receipt", type=Path)
            cmd.add_argument("chart", type=Path)
    a = p.parse_args()
    if a.command == "import":
        print(register(a.root, a.chart.read_bytes(), json.loads(a.receipt.read_bytes())))
    elif a.command == "capture":
        print(capture(a.root))
    else:
        print(
            json.dumps(audit(a.root, through=a.through), allow_nan=False, sort_keys=True, indent=2)
        )
