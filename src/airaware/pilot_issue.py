"""Conservar el insumo disponible, la primera emisión y las observaciones maduras del piloto."""

import hashlib
import json
import math
import re
import sqlite3
from pathlib import Path


def _encoded(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value) -> str:
    return hashlib.sha256(_encoded(value).encode()).hexdigest()


class Pilot:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(path, timeout=30)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS measurements (
                feed TEXT, station TEXT, hour INTEGER, revision INTEGER,
                value REAL, arrival INTEGER,
                source TEXT, PRIMARY KEY(feed,station,hour,revision));
            CREATE TABLE IF NOT EXISTS issues (
                feed TEXT, station TEXT, origin INTEGER, snapshot TEXT NOT NULL,
                result TEXT, mature TEXT, PRIMARY KEY(feed,station,origin));
        """)

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        self.db.close()

    def receive(
        self,
        feed: str,
        station: str,
        hour: int,
        revision: int,
        value: float | None,
        arrival: int,
        source: str,
    ) -> None:
        if (
            not feed
            or not station
            or hour % 3600
            or arrival < hour
            or revision < 0
            or not re.fullmatch("[0-9a-f]{64}", source)
            or (value is not None and not math.isfinite(value))
        ):
            raise ValueError("Medición, procedencia o recepción inválidas")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            key = (feed, station, hour, revision)
            prior = self.db.execute(
                "SELECT value,source,arrival FROM measurements WHERE feed=? AND station=? "
                "AND hour=? AND revision=?",
                key,
            ).fetchone()
            if prior:
                if prior[:2] != (value, source) or arrival < prior[2]:
                    raise ValueError("Revisión en conflicto con la primera recepción")
                return
            self.db.execute(
                "INSERT INTO measurements VALUES(?,?,?,?,?,?,?)", (*key, value, arrival, source)
            )

    def _view(self, feed: str, station: str, start: int, count: int, cutoff: int):
        rows = self.db.execute(
            """
            SELECT hour,revision,value,arrival,source FROM measurements
            WHERE feed=? AND station=? AND hour BETWEEN ? AND ? AND arrival<=?
            ORDER BY hour,revision
        """,
            (feed, station, start, start + (count - 1) * 3600, cutoff),
        )
        by_hour = {r[0]: r for r in rows}
        return [by_hour.get(start + 3600 * n) for n in range(count)]

    def begin(
        self, feed: str, station: str, origin: int, release: str, cutoff: int, *, max_age: int
    ):
        if (
            origin % 3600
            or cutoff < origin
            or max_age < 0
            or not feed
            or not station
            or not re.fullmatch("[0-9a-f]{64}", release)
        ):
            raise ValueError("Corte, origen o versión inválidos")
        key = (feed, station, origin)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            existing = self.db.execute(
                "SELECT snapshot FROM issues WHERE feed=? AND station=? AND origin=?", key
            ).fetchone()
            if existing:
                snapshot = json.loads(existing[0])
                if snapshot["release"] != release:
                    raise ValueError("El primer intento fijó otra versión")
                return snapshot
            rows = self._view(feed, station, origin - 23 * 3600, 24, cutoff)
            values = [r[2] if r else None for r in rows]
            reason = None
            if cutoff - origin > max_age:
                reason = "stale"
            elif any(v is None for v in values):
                reason = "missing_history"
            snapshot = {
                "feed": feed,
                "station": station,
                "origin": origin,
                "release": release,
                "cutoff": cutoff,
                "reason": reason,
                "history": values,
                "vintage_sha256": _digest(rows),
                "measurements": rows,
            }
            body = _encoded(snapshot)
            self.db.execute(
                "INSERT INTO issues(feed,station,origin,snapshot) VALUES(?,?,?,?)", (*key, body)
            )
            return json.loads(body)

    def _issue(self, issue):
        key = tuple(issue[k] for k in ("feed", "station", "origin"))
        saved = self.db.execute(
            "SELECT snapshot,result,mature FROM issues WHERE feed=? AND station=? AND origin=?", key
        ).fetchone()
        if not saved or saved[0] != _encoded(issue):
            raise ValueError("El insumo difiere del primer intento")
        return key, saved

    def publish(self, issue, result: dict, issued: int):
        if issued < issue["cutoff"]:
            raise ValueError("Emisión anterior al corte")
        if issue["reason"] is not None and result != {"abstained": issue["reason"]}:
            raise ValueError("El insumo requiere una abstención")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            key, saved = self._issue(issue)
            if saved[1]:
                first = json.loads(saved[1])
                if _encoded(first["result"]) != _encoded(result):
                    raise ValueError("El resultado difiere de la emisión inicial")
                return first
            body = {
                "issued": issued,
                "release": issue["release"],
                "snapshot_sha256": _digest(issue),
                "result_sha256": _digest(result),
                "result": result,
            }
            self.db.execute(
                "UPDATE issues SET result=? WHERE feed=? AND station=? AND origin=?",
                (_encoded(body), *key),
            )
            return body

    def mature(self, issue, now: int, *, delay: int):
        if delay < 0:
            raise ValueError("Demora de maduración negativa")
        cutoff = issue["origin"] + 6 * 3600 + delay
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            key, saved = self._issue(issue)
            if saved[1] is None:
                raise ValueError("Falta la primera emisión")
            if saved[2]:
                vintage = json.loads(saved[2])
                if cutoff != vintage["cutoff"]:
                    raise ValueError("La demora difiere del corte congelado")
                return vintage
            if now < cutoff:
                return None
            rows = self._view(issue["feed"], issue["station"], issue["origin"] + 3600, 6, cutoff)
            vintage = {
                "cutoff": cutoff,
                "observed": [r[2] if r else None for r in rows],
                "vintage_sha256": _digest(rows),
                "measurements": rows,
            }
            body = _encoded(vintage)
            self.db.execute(
                "UPDATE issues SET mature=? WHERE feed=? AND station=? AND origin=?", (body, *key)
            )
            return json.loads(body)
