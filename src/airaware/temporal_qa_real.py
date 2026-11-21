"""Generar el conjunto real de preguntas temporales de #35 sobre registros observados.

Lee en solo lectura la grilla horaria depurada del paquete TimeF verificado de la
preparación `pm-bivariado-20261120` (fuente `historico`, estaciones de SENAMHI Lima), coteja
los archivos del release contra su manifiesto y contra `resumen.json`, elige tramos
completos de 24 horas libres de los objetivos congelados del pronóstico y construye las
cuatro familias con `airaware.temporal_qa`, con verificación de ida y vuelta y control de
separación. La regla de ventanas (30 horas consecutivas bivariadas finitas) y la fórmula de
identidad de serie reproducen exactamente las de `tools/timenet-smoke/external_pm.py`, cuyo
verificador oficial contrastó cada valor del release con esta misma grilla.

La exportación del conjunto como paquete TimeF versionado queda como entrega posterior de
la issue #35; este módulo solo escribe el conjunto local y su evidencia ligera.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from airaware.temporal_qa import (
    PM25_UNIT,
    QA_FAMILIES,
    ForecastTargetInterval,
    ObservedSeries,
    TemporalQuestion,
    build_temporal_question,
    validate_qa_separated,
    verify_answer,
)

FUENTE = "historico"
SITIO = "CAMPO_DE_MARTE"
INICIO = datetime(2015, 1, 1)
FIN = datetime(2024, 6, 1)
HISTORIA_HORAS = 24
OBJETIVO_HORAS = 6
TRAMO_HORAS = 24
FAMILIAS_CON_TRAMO = 4
ATRIBUCION = "SENAMHI, Lima; licencia de datos ODC-BY-1.0; unidad inferida según ADR-005"
VERSION_CONJUNTO = "tqa-real-v1"

_GRILLA = """
WITH raw AS (
    SELECT sitio, id_estacion, id_sensor, parametro, valor, fila,
           CASE WHEN fuente = 'senamhi_horario' THEN hora_nativa
                ELSE observado_utc END AS hora
    FROM read_parquet(?) WHERE fuente = ? AND grupo = 'benchmark' AND unidad = 'µg/m³'
      AND parametro IN ('pm25','pm10') AND sitio = ?
), cells AS (
    SELECT sitio, id_estacion, hora, parametro,
           CASE WHEN count(DISTINCT id_sensor)<=1
                  AND count(DISTINCT valor) FILTER (WHERE isfinite(valor))=1
                  AND count(*) FILTER (WHERE valor IS NOT NULL AND NOT isfinite(valor))=0
                THEN min(valor) END AS valor
    FROM raw WHERE date_trunc('hour', hora)=hora AND hora >= ? AND hora < ?
    GROUP BY sitio,id_estacion,hora,parametro
)
SELECT epoch(hora)::BIGINT//3600 AS h,
       max(valor) FILTER (WHERE parametro='pm25') AS pm25,
       max(valor) FILTER (WHERE parametro='pm10') AS pm10
FROM cells GROUP BY sitio,id_estacion,hora HAVING pm25 IS NOT NULL AND pm10 IS NOT NULL
ORDER BY h
"""

_IDENTICIDAD = """
SELECT DISTINCT r.metadata->'series_ids'->>0 AS serie_pm25,
                r.metadata->'series_ids'->>1 AS serie_pm10
FROM records r WHERE r.metadata->>'station_key' = ?
"""

_CONTEO_TAREAS = """
SELECT t.split, count(*) FROM tasks t
JOIN task_record_refs ref ON ref.task_id = t.task_id AND ref.field = 'inputs'
JOIN records r ON r.record_id = ref.record_id
WHERE r.metadata->>'station_key' = ? GROUP BY t.split
"""


def sha256_archivo(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as handle:
        for bloque in iter(lambda: handle.read(1 << 20), b""):
            digest.update(bloque)
    return digest.hexdigest()


def instante(hora: int) -> datetime:
    return datetime.fromtimestamp(hora * 3600, UTC)


def leer_grilla(insumo: Path, sitio: str = SITIO) -> dict[str, Any]:
    """Leer la grilla bivariada de una estación con la regla de celdas de external_pm."""
    with duckdb.connect() as db:
        db.execute("SET threads=2")
        db.execute("SET TimeZone='UTC'")
        filas = db.execute(_GRILLA, [str(insumo), FUENTE, sitio, INICIO, FIN]).fetchall()
    if not filas:
        raise ValueError(f"La grilla de {sitio} quedó vacía con los límites declarados")
    return {
        "sitio": sitio,
        "horas": [fila[0] for fila in filas],
        "pm25": [fila[1] for fila in filas],
        "pm10": [fila[2] for fila in filas],
    }


def inicios_validos(horas: list[int], pm25: list[float], pm10: list[float]) -> list[int]:
    """Índices de inicio de ventanas de 30 horas consecutivas con ambos canales finitos.

    Reproduce la regla de `valid_starts` de `tools/timenet-smoke/external_pm.py`, que define
    las ventanas congeladas del pronóstico y quedó contrastada por su verificador oficial.
    """
    if any(después <= antes for antes, después in zip(horas, horas[1:], strict=False)):
        raise ValueError("Se requieren horas únicas y ordenadas por serie")
    inicios = []
    for i in range(len(horas) - HISTORIA_HORAS - OBJETIVO_HORAS + 1):
        if (
            horas[i + HISTORIA_HORAS + OBJETIVO_HORAS - 1] - horas[i]
            != HISTORIA_HORAS + OBJETIVO_HORAS - 1
        ):
            continue
        tramo = range(i, i + HISTORIA_HORAS + OBJETIVO_HORAS)
        if all(math.isfinite(pm25[j]) and math.isfinite(pm10[j]) for j in tramo):
            inicios.append(i)
    return inicios


def intervalos_objetivo(horas: list[int], inicios: list[int]) -> list[tuple[int, int]]:
    """Intervalos objetivo [h+24, h+29] de cada ventana congelada, en horas desde el origen."""
    return [
        (horas[i] + HISTORIA_HORAS, horas[i] + HISTORIA_HORAS + OBJETIVO_HORAS - 1) for i in inicios
    ]


def tramos_libres(
    horas: list[int], pm25: list[float], pm10: list[float], inicios: list[int], minimo: int
) -> list[tuple[int, int]]:
    """Tramos contiguos de horas finitas que ningún objetivo congelado cubre."""
    objetivos: set[int] = set()
    for inicio, fin in intervalos_objetivo(horas, inicios):
        objetivos.update(range(inicio, fin + 1))
    libres = [
        hora
        for hora, valor25, valor10 in zip(horas, pm25, pm10, strict=True)
        if math.isfinite(valor25) and math.isfinite(valor10) and hora not in objetivos
    ]
    tramos: list[tuple[int, int]] = []
    for hora in libres:
        if tramos and hora == tramos[-1][1] + 1:
            tramos[-1] = (tramos[-1][0], hora)
        else:
            tramos.append((hora, hora))
    return [tramo for tramo in tramos if tramo[1] - tramo[0] + 1 >= minimo]


def elegir_tramos(
    tramos: list[tuple[int, int]], cantidad: int = FAMILIAS_CON_TRAMO
) -> list[tuple[int, int]]:
    """Elegir los últimos tramos disponibles y devolverlos en orden cronológico.

    Regla determinista: se toman las últimas 24 horas de los `cantidad` tramos completos
    más recientes y se asignan a las familias en su orden canónico.
    """
    elegidos = sorted(
        (fin - TRAMO_HORAS + 1, fin) for inicio, fin in tramos if fin - inicio + 1 >= TRAMO_HORAS
    )[-cantidad:]
    if len(elegidos) < cantidad:
        raise ValueError(
            f"La serie no ofrece {cantidad} tramos libres de {TRAMO_HORAS} horas; "
            f"disponibles: {len(elegidos)}"
        )
    return elegidos


def identidad_series(codigo: str) -> tuple[str, str]:
    """Fórmula de identidad de serie del paquete historico (misma de external_pm.series_key)."""

    def digest(campos: list[Any]) -> str:
        return hashlib.sha256(json.dumps(campos, separators=(",", ":")).encode()).hexdigest()

    return (
        digest([codigo, None, "PM2_5", "PM2.5", "ug/m3"]),
        digest([codigo, None, "PM10", "PM10", "ug/m3"]),
    )


def segmento(
    serie_id: str,
    horas: list[int],
    valores: list[float],
    inicio: int,
    fin: int,
    pollutant: str = "PM2.5",
) -> ObservedSeries:
    """Extraer un tramo horario contiguo (límites inclusivos) como serie observada."""
    if inicio not in horas or fin not in horas:
        raise ValueError("El tramo elegido debe estar dentro de la grilla")
    primero = horas.index(inicio)
    último = horas.index(fin)
    datos = tuple(valores[primero : último + 1])
    if len(datos) != fin - inicio + 1 or horas[primero : último + 1] != list(
        range(inicio, fin + 1)
    ):
        raise ValueError("El tramo elegido debe ser contiguo y completo")
    return ObservedSeries(
        series_id=serie_id,
        start=instante(inicio),
        values=datos,
        attribution=ATRIBUCION,
        pollutant=pollutant,
    )


def verificar_release(release: Path, resumen: dict[str, Any], insumo: Path) -> None:
    """Cotejar insumo, manifiesto y archivos del release contra las sumas declaradas."""
    declarado = resumen["inputs"]
    if str(insumo) not in declarado:
        raise ValueError("El insumo indicado no figura en resumen.json")
    if sha256_archivo(insumo) != declarado[str(insumo)]:
        raise ValueError("El insumo cambió desde la exportación del paquete")
    manifiesto = release / "manifest.json"
    if sha256_archivo(manifiesto) != resumen["manifest_sha256"]:
        raise ValueError("El manifiesto del release cambió respecto de resumen.json")
    declarado_manifiesto = json.loads(manifiesto.read_text(encoding="utf-8"))["files"]
    for grupo in ("control", "time_series"):
        for entrada in declarado_manifiesto.get(grupo, []):
            ruta = release / entrada["path"]
            esperado = entrada["checksum"].removeprefix("sha256:")
            if entrada["size"] != ruta.stat().st_size or sha256_archivo(ruta) != esperado:
                raise ValueError(f"El archivo del release no coincide con el manifiesto: {ruta}")


def cruzar_identidad(release: Path, codigo: str, series: tuple[str, str]) -> dict[str, int]:
    """Contrastar la identidad calculada con los registros del release y contar tareas."""
    with duckdb.connect(str(release / "control.duckdb"), read_only=True) as db:
        db.execute("SET TimeZone='UTC'")
        identidad = db.execute(_IDENTICIDAD, [codigo]).fetchall()
        if identidad != [(series[0], series[1])]:
            raise ValueError(f"La identidad de serie no coincide con el release: {identidad}")
        conteos = dict(db.execute(_CONTEO_TAREAS, [codigo]).fetchall())
    return conteos


def construir_conjunto(
    bloque: dict[str, Any],
    series: tuple[str, str],
    tareas_esperadas: int,
) -> dict[str, Any]:
    """Núcleo puro: tramos, preguntas, verificación de ida y vuelta y separación."""
    horas, pm25, pm10 = bloque["horas"], bloque["pm25"], bloque["pm10"]
    inicios = inicios_validos(horas, pm25, pm10)
    if len(inicios) != tareas_esperadas:
        raise ValueError(
            f"Las ventanas recalculadas ({len(inicios)}) no coinciden con el release "
            f"({tareas_esperadas})"
        )
    tramos = elegir_tramos(tramos_libres(horas, pm25, pm10, inicios, TRAMO_HORAS))
    ventanas = dict(zip(QA_FAMILIES, tramos, strict=True))
    preguntas: list[TemporalQuestion] = []
    segmentos_por_pregunta: list[dict[str, ObservedSeries]] = []
    for familia in QA_FAMILIES:
        inicio, fin = ventanas[familia]
        segmentos = {series[0]: segmento(series[0], horas, pm25, inicio, fin)}
        if familia == "comparison":
            segmentos[series[1]] = segmento(series[1], horas, pm10, inicio, fin, pollutant="PM10")
        preguntas.append(
            build_temporal_question(
                familia,
                segments=segmentos,
                window_start=instante(inicio),
                window_end_exclusive=instante(fin + 1),
            )
        )
        segmentos_por_pregunta.append(segmentos)
    verificaciones = [
        verify_answer(pregunta, segmentos)
        for pregunta, segmentos in zip(preguntas, segmentos_por_pregunta, strict=True)
    ]
    control_negativo = not verify_answer(
        TemporalQuestion(
            question_id=preguntas[0].question_id,
            family=preguntas[0].family,
            series_ids=preguntas[0].series_ids,
            observation_ids=preguntas[0].observation_ids,
            window_start=preguntas[0].window_start,
            window_end_exclusive=preguntas[0].window_end_exclusive,
            prompt=preguntas[0].prompt,
            answer="respuesta alterada",
        ),
        segmentos_por_pregunta[0],
    )
    intervalos = [
        ForecastTargetInterval(
            series_id=serie,
            target_start=instante(inicio),
            target_end=instante(fin),
        )
        for inicio, fin in intervalos_objetivo(horas, inicios)
        for serie in series
    ]
    validate_qa_separated(preguntas, intervalos)
    objetivos = intervalos_objetivo(horas, inicios)
    cobertura = (
        instante(min(inicio for inicio, _fin in objetivos)),
        instante(max(fin for _inicio, fin in objetivos)),
    )
    return {
        "preguntas": preguntas,
        "verificaciones": verificaciones,
        "control_negativo": control_negativo,
        "intervalos_objetivo": len(intervalos),
        "cobertura_objetivos": cobertura,
        "ventanas": ventanas,
    }


def generar_conjunto(*, insumo: Path, release: Path, resumen: Path, salida: Path) -> dict[str, Any]:
    """Generar el conjunto QA real y escribirlo como JSON determinista en `salida`."""
    declarado = json.loads(resumen.read_text(encoding="utf-8"))
    if declarado["source"] != FUENTE or declarado["dataset_version"] != "0.1.0":
        raise ValueError("El resumen no corresponde al paquete historico 0.1.0")
    verificar_release(release, declarado, insumo)
    estacion = next(fila for fila in declarado["stations"] if fila["site"] == SITIO)
    bloque = leer_grilla(insumo)
    bloque["codigo"] = estacion["code"]
    bloque["sensores"] = estacion["sensors"]
    series = identidad_series(estacion["code"])
    conteos = cruzar_identidad(release, estacion["code"], series)
    esperadas = conteos.get("train", 0) + conteos.get("validation", 0)
    if esperadas != estacion["train"] + estacion["validation"]:
        raise ValueError("Los conteos por partición no coinciden con resumen.json")
    if estacion.get("purged", 0) != 0:
        raise ValueError("La estación elegida no admite ventanas purgadas en este flujo")
    resultado = construir_conjunto(bloque, series, esperadas)
    cuerpo = {
        "version": VERSION_CONJUNTO,
        "issue": 35,
        "paquete": {
            "dataset_id": declarado["dataset_id"],
            "dataset_version": declarado["dataset_version"],
            "fuente": FUENTE,
            "manifest_sha256": declarado["manifest_sha256"],
            "insumo_sha256": declarado["inputs"][str(insumo)],
        },
        "serie": {
            "sitio": SITIO,
            "codigo_estacion": estacion["code"],
            "sensores": estacion["sensors"],
            "series_ids": {"pm25": series[0], "pm10": series[1]},
            "atribucion": ATRIBUCION,
            "unidad": PM25_UNIT,
            "reloj": "UTC",
        },
        "regla_tramos": (
            "Tramos contiguos de 24 horas con ambos canales finitos que ningún intervalo "
            "objetivo congelado cubre; se eligen los cuatro más recientes y se asignan a las "
            "familias en orden canónico (tendencia, máximo, momento, comparación)."
        ),
        "ventanas": {
            familia: [instante(inicio).isoformat(), instante(fin + 1).isoformat()]
            for familia, (inicio, fin) in resultado["ventanas"].items()
        },
        "preguntas": [
            {
                "question_id": pregunta.question_id,
                "family": pregunta.family,
                "series_ids": list(pregunta.series_ids),
                "observation_ids": list(pregunta.observation_ids),
                "window_start": pregunta.window_start.isoformat(),
                "window_end_exclusive": pregunta.window_end_exclusive.isoformat(),
                "prompt": pregunta.prompt,
                "answer": pregunta.answer,
            }
            for pregunta in resultado["preguntas"]
        ],
        "verificacion_ida_y_vuelta": {
            "por_pregunta": dict(
                zip(
                    (p.question_id for p in resultado["preguntas"]),
                    resultado["verificaciones"],
                    strict=True,
                )
            ),
            "control_negativo_detecta_alteracion": resultado["control_negativo"],
        },
        "separacion": {
            "intervalos_objetivo_congelados": resultado["intervalos_objetivo"],
            "cobertura_objetivos_utc": [
                resultado["cobertura_objetivos"][0].isoformat(),
                resultado["cobertura_objetivos"][1].isoformat(),
            ],
            "resultado": "sin solape entre ventanas de QA y objetivos congelados de la misma serie",
        },
    }
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(cuerpo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "salida": str(salida),
        "sha256": sha256_archivo(salida),
        "familias": {
            familia: {
                "preguntas": 1,
                "observaciones": len(pregunta.observation_ids),
                "ventana": [
                    pregunta.window_start.isoformat(),
                    pregunta.window_end_exclusive.isoformat(),
                ],
            }
            for familia, pregunta in zip(QA_FAMILIES, resultado["preguntas"], strict=True)
        },
        "verificaciones": resultado["verificaciones"],
        "control_negativo": resultado["control_negativo"],
        "intervalos_objetivo": resultado["intervalos_objetivo"],
        "cobertura_objetivos": [
            resultado["cobertura_objetivos"][0].isoformat(),
            resultado["cobertura_objetivos"][1].isoformat(),
        ],
    }


def principal() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--insumo", type=Path, required=True, help="Parquet de insumos verificado")
    parser.add_argument("--release", type=Path, required=True, help="Carpeta del release TimeF")
    parser.add_argument("--resumen", type=Path, required=True, help="resumen.json del registro")
    parser.add_argument("--salida", type=Path, required=True, help="JSON del conjunto QA (local)")
    argumentos = parser.parse_args()
    resumen = generar_conjunto(
        insumo=argumentos.insumo,
        release=argumentos.release,
        resumen=argumentos.resumen,
        salida=argumentos.salida,
    )
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    principal()
