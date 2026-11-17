"""Conteos sin imputación sobre instantes horarios únicos por serie."""

import math

import duckdb


def records(c: duckdb.DuckDBPyConnection, query: str, params=None) -> list[dict]:
    result = c.execute(query, params)
    names = [item[0] for item in result.description]
    return [dict(zip(names, row, strict=True)) for row in result.fetchall()]


def count_windows(c: duckdb.DuckDBPyConnection, history: int, horizon: int) -> list[dict]:
    """Requiere tabla points(series_id,ts) con instantes horarios distintos y sin conflictos."""
    if not (1 <= history <= 168 and 1 <= horizon <= 48):
        raise ValueError("Historia u horizonte fuera del contrato")
    return records(
        c,
        f"""WITH ordered AS (
      SELECT *,ts-row_number() OVER(PARTITION BY series_id ORDER BY ts)*INTERVAL '1 hour' run
      FROM points), runs AS (
      SELECT series_id,min(ts) a,max(ts) b,count(*) n FROM ordered GROUP BY series_id,run),
      bounds AS (SELECT series_id,min(a) first_clock,max(b) last_clock,
        greatest(date_diff('hour',min(a),max(b))+2-{history}-{horizon},0)::BIGINT candidates
        FROM runs GROUP BY series_id), counts AS (
      SELECT r.series_id,sum(greatest(n-{history}-{horizon}+1,0))::BIGINT complete,
        sum(greatest(date_diff('hour',greatest(a+INTERVAL '{history - 1} hours',
          first_clock+INTERVAL '{history - 1} hours'),
          least(b,last_clock-INTERVAL '{horizon} hours'))+1,0))::BIGINT history_pass
        FROM runs r JOIN bounds USING(series_id) GROUP BY r.series_id)
      SELECT b.*,c.complete,b.candidates-c.history_pass history_missing,
        c.history_pass-c.complete future_missing FROM bounds b JOIN counts c USING(series_id)
      ORDER BY series_id""",
    )


def score(
    components: list[float],
    *,
    eligible: bool,
    weights: tuple[float, ...] = (0.35, 0.25, 0.15, 0.15, 0.10),
) -> float | None:
    if len(components) != 5 or len(weights) != 5 or not math.isclose(sum(weights), 1):
        raise ValueError("La puntuación requiere cinco pesos que sumen uno")
    if any(not math.isfinite(x) or not 0 <= x <= 1 for x in (*components, *weights)):
        raise ValueError("Componentes fuera de escala 0–1")
    return sum(x * w for x, w in zip(components, weights, strict=True)) if eligible else None


def common_coverage(c: duckdb.DuckDBPyConnection, station_target: int) -> dict:
    """Cobertura simultánea de puntos, no ventanas ni estaciones homologadas."""
    if station_target < 1:
        raise ValueError("La meta de estaciones debe ser positiva")
    return records(
        c,
        """WITH identities AS (SELECT DISTINCT series_id,station_key FROM base),
      quorum AS (SELECT ts FROM points JOIN identities USING(series_id) GROUP BY ts
        HAVING count(DISTINCT station_key)>=?),
      ordered AS (SELECT ts,ts-row_number() OVER(ORDER BY ts)*INTERVAL '1 hour' run FROM quorum),
      runs AS (SELECT count(*) n FROM ordered GROUP BY run)
      SELECT (SELECT count(*) FROM quorum)::BIGINT common_hour_slots,
        (SELECT min(ts) FROM quorum) first_common_clock,
        (SELECT max(ts) FROM quorum) last_common_clock,
        coalesce(max(n),0)::BIGINT longest_common_run_hours FROM runs""",
        [station_target],
    )[0]
