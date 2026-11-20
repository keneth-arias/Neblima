"""Conversión UTM verificada de OEFA (#30): valores dorados, rechazos tipados y extra geo.

El valor dorado usa la muestra registrada en docs/sources/oefa.md (revisión del 2026-11-16):
CA-HUA-01 con ESTE=504395, NORTE=9456762, ZONA=17, DATUM=WGS84. La referencia independiente
(Snyder/OGP) contrasta pyproj sin circularidad: ambas deben coincidir a menos de 1e-7 grados
(alrededor de 1 cm en superficie).
"""

import math

import pytest

from airaware.normalization.oefa_coords import (
    CRS_DESTINO,
    CRS_ORIGEN,
    DATUM_VERIFICADO,
    METODO,
    ZONA_VERIFICADA,
    ConversionCoordenada,
    RechazoConversion,
    convertir_utm17_sur,
)

MUESTRA_ESTE = "504395"
MUESTRA_NORTE = "9456762"
DORADO_LATITUD = -4.9147225518
DORADO_LONGITUD = -80.9603584686
TOLERANCIA_GRADOS = 1e-7

_A = 6378137.0
_F = 1 / 298.257223563
_E2 = _F * (2 - _F)
_K0 = 0.9996
_LON0 = -81.0


def _snyder_inversa(este: float, norte: float) -> tuple[float, float]:
    """UTM zona 17 sur WGS84 a lat/lon con las fórmulas de Snyder, sin usar pyproj."""
    x = este - 500000.0
    m = (norte - 10000000.0) / _K0
    mu = m / (_A * (1 - _E2 / 4 - 3 * _E2**2 / 64 - 5 * _E2**3 / 256))
    e1 = (1 - math.sqrt(1 - _E2)) / (1 + math.sqrt(1 - _E2))
    phi1 = mu
    phi1 += (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
    phi1 += (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
    phi1 += (151 * e1**3 / 96) * math.sin(6 * mu)
    phi1 += (1097 * e1**4 / 512) * math.sin(8 * mu)
    sin1, cos1, tan1 = math.sin(phi1), math.cos(phi1), math.tan(phi1)
    ep2 = _E2 / (1 - _E2)
    c1 = ep2 * cos1**2
    t1 = tan1**2
    n1 = _A / math.sqrt(1 - _E2 * sin1**2)
    r1 = _A * (1 - _E2) / (1 - _E2 * sin1**2) ** 1.5
    d = x / (n1 * _K0)
    lat = phi1 - (n1 * tan1 / r1) * (
        d**2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * ep2) * d**4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * ep2 - 3 * c1**2) * d**6 / 720
    )
    lon = _LON0 + math.degrees(
        (
            d
            - (1 + 2 * t1 + c1) * d**3 / 6
            + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * ep2 + 24 * t1**2) * d**5 / 120
        )
        / cos1
    )
    return math.degrees(lat), lon


def test_conversion_verificada_coincide_con_el_valor_dorado():
    pytest.importorskip(
        "pyproj",
        reason="CI instala sin extras; la conversión UTM exige el extra opcional 'geo'",
    )
    resultado = convertir_utm17_sur(MUESTRA_ESTE, MUESTRA_NORTE, ZONA_VERIFICADA, DATUM_VERIFICADO)
    assert isinstance(resultado, ConversionCoordenada)
    assert resultado.latitud == pytest.approx(DORADO_LATITUD, abs=TOLERANCIA_GRADOS)
    assert resultado.longitud == pytest.approx(DORADO_LONGITUD, abs=TOLERANCIA_GRADOS)
    assert resultado.crs_origen == CRS_ORIGEN
    assert resultado.crs_destino == CRS_DESTINO
    assert resultado.metodo == METODO
    assert resultado.este_original == MUESTRA_ESTE
    assert resultado.norte_original == MUESTRA_NORTE
    assert resultado.zona == ZONA_VERIFICADA
    assert resultado.datum == DATUM_VERIFICADO


def test_pyproj_coincide_con_la_implementacion_independiente():
    pytest.importorskip(
        "pyproj",
        reason="CI instala sin extras; la conversión UTM exige el extra opcional 'geo'",
    )
    casos = ((504395.0, 9456762.0), (530000.0, 9012345.0))
    for este, norte in casos:
        resultado = convertir_utm17_sur(f"{este:.0f}", f"{norte:.0f}", "17", "WGS84")
        assert isinstance(resultado, ConversionCoordenada)
        lat_referencia, lon_referencia = _snyder_inversa(este, norte)
        assert resultado.latitud == pytest.approx(lat_referencia, abs=TOLERANCIA_GRADOS)
        assert resultado.longitud == pytest.approx(lon_referencia, abs=TOLERANCIA_GRADOS)


def test_la_conversion_es_coherente_en_ida_y_vuelta():
    pytest.importorskip(
        "pyproj",
        reason="CI instala sin extras; la conversión UTM exige el extra opcional 'geo'",
    )
    pyproj = pytest.importorskip(
        "pyproj",
        reason="La ida lat/lon a UTM también exige el extra opcional 'geo'",
    )
    resultado = convertir_utm17_sur(MUESTRA_ESTE, MUESTRA_NORTE, ZONA_VERIFICADA, DATUM_VERIFICADO)
    assert isinstance(resultado, ConversionCoordenada)
    ida = pyproj.Transformer.from_crs(CRS_DESTINO, CRS_ORIGEN, always_xy=True)
    este, norte = ida.transform(resultado.longitud, resultado.latitud)
    assert este == pytest.approx(resultado.este, abs=0.01)
    assert norte == pytest.approx(resultado.norte, abs=0.01)


def test_zona_distinta_a_la_verificada_se_rechaza_sin_convertir():
    resultado = convertir_utm17_sur(MUESTRA_ESTE, MUESTRA_NORTE, "18", DATUM_VERIFICADO)
    assert isinstance(resultado, RechazoConversion)
    assert resultado.motivo == "zona_no_verificada"
    assert resultado.zona == "18"
    assert resultado.datum == DATUM_VERIFICADO
    assert resultado.este_original == MUESTRA_ESTE
    assert resultado.norte_original == MUESTRA_NORTE
    assert resultado.error


def test_la_zona_con_letra_no_verificada_en_la_muestra_se_rechaza():
    resultado = convertir_utm17_sur(MUESTRA_ESTE, MUESTRA_NORTE, "18L", DATUM_VERIFICADO)
    assert isinstance(resultado, RechazoConversion)
    assert resultado.motivo == "zona_no_verificada"


def test_datum_distinto_al_verificado_se_rechaza():
    resultado = convertir_utm17_sur(MUESTRA_ESTE, MUESTRA_NORTE, ZONA_VERIFICADA, "SIRGAS")
    assert isinstance(resultado, RechazoConversion)
    assert resultado.motivo == "datum_no_verificado"
    assert resultado.datum == "SIRGAS"
    assert resultado.zona == ZONA_VERIFICADA


def test_el_datum_en_minusculas_no_se_acepta_como_verificado():
    resultado = convertir_utm17_sur(MUESTRA_ESTE, MUESTRA_NORTE, ZONA_VERIFICADA, "wgs84")
    assert isinstance(resultado, RechazoConversion)
    assert resultado.motivo == "datum_no_verificado"


def test_campos_ausentes_o_vacios_se_rechazan_sin_convertir():
    for este, norte, zona, datum in (
        (MUESTRA_ESTE, MUESTRA_NORTE, "", DATUM_VERIFICADO),
        (MUESTRA_ESTE, MUESTRA_NORTE, "  ", DATUM_VERIFICADO),
        (MUESTRA_ESTE, MUESTRA_NORTE, None, DATUM_VERIFICADO),
        (MUESTRA_ESTE, MUESTRA_NORTE, ZONA_VERIFICADA, None),
        (MUESTRA_ESTE, MUESTRA_NORTE, ZONA_VERIFICADA, ""),
        (None, MUESTRA_NORTE, ZONA_VERIFICADA, DATUM_VERIFICADO),
        (MUESTRA_ESTE, None, ZONA_VERIFICADA, DATUM_VERIFICADO),
    ):
        resultado = convertir_utm17_sur(este, norte, zona, datum)
        assert isinstance(resultado, RechazoConversion), (este, norte, zona, datum)
        assert resultado.motivo in {
            "zona_ausente",
            "datum_ausente",
            "este_invalido",
            "norte_invalido",
        }
        assert resultado.error


def test_este_y_norte_no_numericos_o_no_finitos_se_rechazan():
    for crudo in ("CA-HUA-01", "50.439,5", "nan", "inf", "-inf", "1e400"):
        este = convertir_utm17_sur(crudo, MUESTRA_NORTE, ZONA_VERIFICADA, DATUM_VERIFICADO)
        assert isinstance(este, RechazoConversion), crudo
        assert este.motivo == "este_invalido"
        norte = convertir_utm17_sur(MUESTRA_ESTE, crudo, ZONA_VERIFICADA, DATUM_VERIFICADO)
        assert isinstance(norte, RechazoConversion), crudo
        assert norte.motivo == "norte_invalido"


def test_el_orden_de_validacion_es_determinista():
    resultado = convertir_utm17_sur("x", "y", "19", "PSAD56")
    assert isinstance(resultado, RechazoConversion)
    assert resultado.motivo == "zona_no_verificada"
    resultado = convertir_utm17_sur("x", "y", ZONA_VERIFICADA, "PSAD56")
    assert isinstance(resultado, RechazoConversion)
    assert resultado.motivo == "datum_no_verificado"


def test_los_espacios_de_borde_no_impiden_la_conversion():
    pytest.importorskip(
        "pyproj",
        reason="CI instala sin extras; la conversión UTM exige el extra opcional 'geo'",
    )
    con_bordes = convertir_utm17_sur(f" {MUESTRA_ESTE} ", f" {MUESTRA_NORTE} ", " 17 ", " WGS84 ")
    assert isinstance(con_bordes, ConversionCoordenada)
    assert con_bordes.latitud == pytest.approx(DORADO_LATITUD, abs=TOLERANCIA_GRADOS)
