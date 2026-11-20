"""Pruebas de la generación real de preguntas temporales de #35 (núcleo puro, sin datos)."""

import math
from datetime import UTC, datetime, timedelta

import pytest

from airaware.temporal_qa import ForecastTargetInterval, validate_qa_separated
from airaware.temporal_qa_real import (
    SITIO,
    construir_conjunto,
    elegir_tramos,
    identidad_series,
    inicios_validos,
    intervalos_objetivo,
    segmento,
    tramos_libres,
)

CODIGO_CAMPO_DE_MARTE = "90b36a172f1790cf2e37ac2063f80fd27439d4ecf871d72a20bf8e9786587a67"
ORIGEN = datetime(1970, 1, 1, tzinfo=UTC)


def bloque_con_hueco() -> dict:
    """Grilla de prueba: horas 0..99 y 125..239 (hueco de 25 horas), ambos canales finitos."""
    horas = [hora for hora in range(240) if not 100 <= hora <= 124]
    valores = [float(hora % 24) + 0.25 for hora in horas]
    return {
        "sitio": "prueba",
        "horas": horas,
        "pm25": valores,
        "pm10": [valor + 8.0 for valor in valores],
    }


def test_inicios_validos_exige_tramos_de_30_horas_bivariadas():
    bloque = bloque_con_hueco()
    inicios = inicios_validos(bloque["horas"], bloque["pm25"], bloque["pm10"])
    horas = bloque["horas"]
    assert horas[inicios[0]] == 0 and horas[inicios[-1]] == 210
    assert len(inicios) == 71 + 86
    for i in inicios:
        assert horas[i + 29] - horas[i] == 29
        assert all(
            math.isfinite(bloque["pm25"][j]) and math.isfinite(bloque["pm10"][j])
            for j in range(i, i + 30)
        )
    with pytest.raises(ValueError, match="únicas y ordenadas"):
        inicios_validos([5, 5], [1.0, 1.0], [1.0, 1.0])


def test_intervalos_objetivo_sigue_el_formato_de_las_ventanas_congeladas():
    bloque = bloque_con_hueco()
    inicios = inicios_validos(bloque["horas"], bloque["pm25"], bloque["pm10"])
    objetivos = intervalos_objetivo(bloque["horas"], inicios)
    assert objetivos[0] == (24, 29)
    assert len(objetivos) == len(inicios)
    assert all(fin - inicio == 5 for inicio, fin in objetivos)


def test_tramos_libres_cabecera_y_despues_del_hueco():
    bloque = bloque_con_hueco()
    inicios = inicios_validos(bloque["horas"], bloque["pm25"], bloque["pm10"])
    tramos = tramos_libres(bloque["horas"], bloque["pm25"], bloque["pm10"], inicios, 24)
    assert tramos == [(0, 23), (125, 148)]
    cortos = tramos_libres(bloque["horas"], bloque["pm25"], bloque["pm10"], inicios, 30)
    assert cortos == []


def test_elegir_tramos_toma_los_mas_recientes_en_orden_cronologico():
    tramos = [(0, 23), (125, 148), (200, 223), (300, 323), (380, 403)]
    assert elegir_tramos(tramos, cantidad=4) == [(125, 148), (200, 223), (300, 323), (380, 403)]
    with pytest.raises(ValueError, match="tramos libres"):
        elegir_tramos([(0, 23)], cantidad=2)


def test_identidad_series_reproduce_los_identificadores_del_release():
    assert identidad_series(CODIGO_CAMPO_DE_MARTE) == (
        "ae2485b1585f200b3d55be0ff285dedcb8f454b003433eb9ce6e7b948554ee80",
        "0773c46665a6e396b8acabd72faf708c2b1b332109417186fb50626cc2cea8c3",
    )


def test_segmento_extrae_valores_contiguos_con_instantes_utc():
    bloque = bloque_con_hueco()
    serie = segmento("serie-pm25", bloque["horas"], bloque["pm25"], 125, 148)
    assert serie.values == tuple(bloque["pm25"][100:124])
    assert len(serie.values) == 24
    assert serie.observation_ids == tuple(
        f"obs:serie-pm25:{(ORIGEN + timedelta(hours=hora)).isoformat()}" for hora in range(125, 149)
    )
    with pytest.raises(ValueError, match="dentro de la grilla"):
        segmento("serie-pm25", bloque["horas"], bloque["pm25"], 90, 240)
    with pytest.raises(ValueError, match="contiguo y completo"):
        segmento("serie-pm25", bloque["horas"], bloque["pm25"], 99, 125)


def bloque_con_cuatro_tramos() -> dict:
    """Grilla con cuatro huecos de 25 horas: genera cuatro tramos libres de 24 horas."""
    huecos = (60, 140, 220, 300)
    horas = [hora for hora in range(400) if not any(gap <= hora < gap + 25 for gap in huecos)]
    valores = [float((hora * 7) % 23) + 0.5 for hora in horas]
    return {
        "sitio": "prueba",
        "horas": horas,
        "pm25": valores,
        "pm10": [valor + 8.0 for valor in valores],
    }


def test_construir_conjunto_genera_cuatro_familias_verificadas_y_separadas():
    bloque = bloque_con_cuatro_tramos()
    series = identidad_series(CODIGO_CAMPO_DE_MARTE)
    inicios = inicios_validos(bloque["horas"], bloque["pm25"], bloque["pm10"])
    resultado = construir_conjunto(bloque, series, len(inicios))
    preguntas = resultado["preguntas"]
    assert [pregunta.family for pregunta in preguntas] == [
        "trend",
        "maximum",
        "moment",
        "comparison",
    ]
    comparacion = preguntas[-1]
    assert "(PM2.5)" in comparacion.prompt and "(PM10)" in comparacion.prompt
    assert all(resultado["verificaciones"])
    assert resultado["control_negativo"] is True
    assert resultado["intervalos_objetivo"] == 2 * len(inicios)
    objetivos = intervalos_objetivo(bloque["horas"], inicios)
    assert resultado["cobertura_objetivos"] == (
        datetime.fromtimestamp(min(inicio for inicio, _fin in objetivos) * 3600, UTC),
        datetime.fromtimestamp(max(fin for _inicio, fin in objetivos) * 3600, UTC),
    )
    for pregunta in preguntas:
        inicio = int((pregunta.window_start - ORIGEN).total_seconds() // 3600)
        fin_exclusiva = int((pregunta.window_end_exclusive - ORIGEN).total_seconds() // 3600)
        for objetivo_inicio, objetivo_fin in objetivos:
            assert not (inicio <= objetivo_fin and objetivo_inicio < fin_exclusiva), (
                pregunta.question_id
            )
    with pytest.raises(ValueError, match="no coinciden"):
        construir_conjunto(bloque, series, len(inicios) + 1)


def test_construir_conjunto_pasa_el_control_de_separacion_del_modulo():
    bloque = bloque_con_cuatro_tramos()
    series = identidad_series(CODIGO_CAMPO_DE_MARTE)
    inicios = inicios_validos(bloque["horas"], bloque["pm25"], bloque["pm10"])
    resultado = construir_conjunto(bloque, series, len(inicios))
    intervalos = [ForecastTargetInterval("otra-serie", ORIGEN, ORIGEN + timedelta(hours=24))]
    validate_qa_separated(resultado["preguntas"], intervalos)


def test_sitio_del_paquete_es_campo_de_marte():
    assert SITIO == "CAMPO_DE_MARTE"
