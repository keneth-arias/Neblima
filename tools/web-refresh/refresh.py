"""Capturar SENAMHI y exportar un pronóstico público pequeño con Gemma 3 1B."""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import unicodedata
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

ENDPOINT = "https://www.senamhi.gob.pe/site/sea/www/site/sea/graficas/dato_hora.php"
CHECKPOINT = "f1da0c412e9b918f8f4d8a11c8b6b5ee197150501b8e6ea97cd33be01d54304c"
CORRECTION = "93bc57abc4b3840c4e59fc2d705fc91fa5b7d6872fd9bb81efdecc7bcd686ffc"
RELEASE = "3b0eb55dada3fa67e68248c46c39b6c9f00f1006f53a7c5b92af39305a3d7de6"
STATIONS = {
    "CARABAYLLO": ["113260"],
    "CAMPO_DE_MARTE": ["112194"],
    "SAN_JUAN_DE_LURIGANCHO": ["113258"],
    "SAN_MARTIN_DE_PORRES": ["00112272"],
    "SANTA_ANITA": ["00112271"],
    "SAN_BORJA": ["00112270"],
    "VILLA_MARIA_DEL_TRIUNFO": ["112233"],
}
HOUR = timedelta(hours=1)


def started(now, first):
    return datetime.fromisoformat(now) >= datetime.fromisoformat(first.replace("Z", "+00:00"))


def parse_chart(raw, station):
    # Reutilizar el lector del archivo horario de AirAware; no evaluar JavaScript remoto.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "timenet-smoke"))
    from stage_external_pm import readings

    html = raw.decode("latin-1")
    title = re.search(r"title:\s*\{\s*text:\s*'([^']+)'", html)
    normalized = unicodedata.normalize("NFKD", title[1] if title else "")
    normalized = re.sub("[^A-Z]+", "_", normalized.encode("ascii", "ignore").decode().upper())
    if station not in normalized:
        raise ValueError("El gráfico no identifica la estación esperada")
    points = {}
    for label, value in readings(
        html, expected_series="Material Particulado menor a 2.5 micras (PM2.5)"
    ):
        if label in points or label.minute or label.second:
            raise ValueError("Hora duplicada o fuera de la grilla horaria")
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError("Lectura no finita o negativa")
        points[label] = value
    return points


def window_at(points, origin):
    return {
        "origin": origin.isoformat(),
        "history": [points.get(origin + i * HOUR) for i in range(-23, 1)],
        "observed": [points.get(origin + i * HOUR) for i in range(1, 7)],
        "target_times": [(origin + i * HOUR).isoformat() for i in range(1, 7)],
        "forecast": None,
    }


def eligible(window):
    return all(value is not None for value in window["history"])


def choose_series(candidates):
    # Una historia nunca combina instrumentos. Gana el último origen completo;
    # los empates conservan el código menor, como en la captura retrospectiva.
    def key(candidate):
        code, points = candidate
        complete = [label for label in points if eligible(window_at(points, label))]
        return (max(complete, default=datetime.min), len(complete))

    return max(sorted(candidates), key=key)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def download(url, directory):
    commands = [
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
        for i, (name, args) in enumerate(commands, 1)
    )
    result = subprocess.run(
        [
            os.environ.get("LIGHTPANDA", "/opt/fresh-peak/lightpanda"),
            "mcp",
            "--block-private-networks",
            "--load-resources",
            "none",
            "--http-max-response-size",
            "1000000",
        ],
        input=requests,
        text=True,
        cwd=directory,
        capture_output=True,
        timeout=45,
        check=True,
    )
    responses = {v["id"]: v for v in map(json.loads, result.stdout.splitlines()) if "id" in v}
    if set(responses) != {1, 2} or any(
        "result" not in v or "error" in v or v["result"].get("isError") for v in responses.values()
    ):
        raise ValueError("Falló la descarga acotada con Lightpanda")
    raw = (directory / "chart.html").read_bytes()
    status = responses[2]["result"].get("structuredContent", {}).get("httpStatus")
    if status not in (None, 200) or len(raw) > 1_000_000:
        raise ValueError("Respuesta inesperada de SENAMHI")
    return raw, status


def capture(root):

    now = datetime.now(UTC)
    root.mkdir(parents=True, exist_ok=True)
    if os.environ.get("NOT_BEFORE") and not started(now.isoformat(), os.environ["NOT_BEFORE"]):
        (root / "skip").touch()
        print("Pendiente hasta las 09:00 del 23/11/2026 en America/Lima", flush=True)
        return
    local = now.astimezone(ZoneInfo("America/Lima")).replace(
        tzinfo=None, minute=0, second=0, microsecond=0
    )
    first, last = local.date() - timedelta(days=2), local.date()
    stations, selected = {}, {}
    for station, codes in STATIONS.items():
        receipts, candidates = {}, []
        for code in codes:
            url = (
                ENDPOINT
                + "?"
                + urlencode(
                    {
                        "estacion": code,
                        "cont": "N_PM25",
                        "f1": first.strftime("%d/%m/%Y"),
                        "f2": last.strftime("%d/%m/%Y"),
                    }
                )
            )
            directory = root / code
            directory.mkdir()
            receipt = {"url": url, "retrieval": "Lightpanda"}
            try:
                raw, status = download(url, directory)
                receipt.update(
                    sha256=hashlib.sha256(raw).hexdigest(),
                    bytes=len(raw),
                    http_status=status,
                    retrieved_at_utc=datetime.now(UTC).isoformat(),
                )
                points = parse_chart(raw, station)
                if any(not first <= label.date() <= last or label > local for label in points):
                    raise ValueError(
                        "Etiqueta fuera de la consulta o posterior al reloj de referencia de Lima"
                    )
                if not any(value is not None for value in points.values()):
                    raise ValueError("El gráfico no contiene lecturas")
                candidates.append((code, points))
            except Exception as error:
                receipt["error"] = f"{type(error).__name__}: {error}"
            receipts[code] = receipt
            write_json(directory / "receipt.json", receipt)
        stations[station] = {"receipts": receipts, "source_code": None, "windows": []}
        if candidates:
            code, points = choose_series(candidates)
            stations[station]["source_code"] = code
            selected[station] = points
    if not selected:
        raise ValueError("No hay capturas verificadas; conservar el último archivo público")
    origin = max(
        label for points in selected.values() for label, v in points.items() if v is not None
    )
    if local - origin > 6 * HOUR:
        raise ValueError("Todas las observaciones tienen más de seis horas de retraso")
    timeline = [origin + i * HOUR for i in range(-7, 1)]
    for station, record in stations.items():
        points = selected.get(station, {})
        record["latest_observed_at"] = max(
            (t for t, v in points.items() if v is not None), default=None
        )
        if record["latest_observed_at"] is not None:
            record["latest_observed_at"] = record["latest_observed_at"].isoformat()
        record["windows"] = [window_at(points, label) for label in timeline]
    snapshot = {
        "schema_version": 2,
        "generated_at_utc": now.isoformat(),
        "clock": "provider_wall_clock",
        "unit": "µg/m³",
        "source_revision": os.environ["AIRAWARE_REVISION"],
        "timeline": [label.isoformat() for label in timeline],
        "stations": stations,
    }
    write_history(root, snapshot)
    write_json(root / "capture.json", snapshot)
    print(f"Captura verificada: {len(selected)}/7 estaciones", flush=True)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_history(root, snapshot):
    import numpy as np

    ids, histories = [], []
    for station, record in snapshot["stations"].items():
        for window in record["windows"]:
            if eligible(window):
                if record["source_code"] not in STATIONS[station]:
                    raise ValueError("Instrumento fuera de la nómina de Gemma")
                ids.append(station + "/" + window["origin"])
                histories.append(window["history"])
    np.savez(
        root / "history.npz",
        window_id=np.asarray(ids, dtype=str),
        history=np.asarray(histories, dtype="float64").reshape(-1, 24),
    )


def predict(root):
    import numpy as np

    with np.load(root / "history.npz", allow_pickle=False) as data:
        if not len(data["window_id"]):
            return
    subprocess.run(
        [
            sys.executable,
            "-u",
            "-m",
            "opentslm.forecast_inference",
            "--head",
            "direct",
            "--backbone",
            "gemma-1b",
            "--require-history-only",
            "--weights",
            "/model/weights",
            "--checkpoint",
            "/model/step-00004500",
            "--selected-manifest-sha256",
            CHECKPOINT,
            "--data",
            str(root / "history.npz"),
            "--output",
            str(root / "raw.npz"),
            "--batch",
            "16",
        ],
        check=True,
    )


def correct(root):
    from types import SimpleNamespace

    import numpy as np
    from direct_bias_correction import apply

    history = root / "history.npz"
    hp = digest(history)
    with np.load(history, allow_pickle=False) as data:
        if not len(data["window_id"]):
            np.savez(
                root / "predictions.npz",
                window_id=np.array([], dtype=str),
                predicted=np.empty((0, 6)),
                forecast_hour=np.arange(1, 7),
                history_sha256=hp,
                checkpoint_sha256=CHECKPOINT,
                correction_sha256=CORRECTION,
            )
            return
    raw = root / "raw.npz"
    receipt = apply(
        SimpleNamespace(
            history=history,
            history_sha256=hp,
            forecast=raw,
            forecast_sha256=digest(raw),
            correction=Path("/model/correction.json"),
            correction_sha256=CORRECTION,
            output=root / "predictions.npz",
        )
    )
    print(json.dumps(receipt), flush=True)


def export(root):
    import numpy as np

    snapshot = json.loads((root / "capture.json").read_bytes())
    with np.load(root / "predictions.npz", allow_pickle=False) as data:
        ids, predictions = data["window_id"].tolist(), data["predicted"]
        if (
            data["checkpoint_sha256"].item() != CHECKPOINT
            or data["history_sha256"].item() != digest(root / "history.npz")
            or data["correction_sha256"].item() != CORRECTION
            or predictions.shape != (len(ids), 6)
            or len(set(ids)) != len(ids)
            or not np.isfinite(predictions).all()
            or not np.array_equal(data["forecast_hour"], np.arange(1, 7))
        ):
            raise ValueError("Pronósticos incompatibles con Gemma o sus seis horizontes")
        forecasts = dict(zip(ids, predictions.tolist(), strict=True))
    expected = set()
    for station, record in snapshot["stations"].items():
        for window in record["windows"]:
            if eligible(window):
                key = station + "/" + window["origin"]
                expected.add(key)
                window["forecast"] = forecasts[key]
    if set(forecasts) != expected:
        raise ValueError("Los identificadores de predicción difieren de las historias")
    snapshot["model"] = {
        "name": "Gemma 3 1B",
        "release_sha256": RELEASE,
        "correction_sha256": CORRECTION,
        "checkpoint_sha256": CHECKPOINT,
        "computed_at_utc": datetime.now(UTC).isoformat(),
    }
    write_json(root / "actual.json", snapshot)
    print(f"Exportados {len(expected)} pronósticos de seis horas", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["capture", "predict", "correct", "export"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    if args.command == "capture" or not (args.root / "skip").exists():
        {"capture": capture, "predict": predict, "correct": correct, "export": export}[
            args.command
        ](args.root)
