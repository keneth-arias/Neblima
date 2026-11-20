"""Conversión UTM verificada para coordenadas OEFA (#30); rechazo tipado, sin supuestos.

Lo único verificado en la fuente registrada (docs/sources/oefa.md, revisión del 2026-11-16)
es la muestra inicial del CSV de EAS: los 123 registros completos de CA-HUA-01 llevan
ZONA=17 y DATUM=WGS84, con ESTE=504395 y NORTE=9456762. Esa muestra no demuestra que toda
la fuente comparta zona y datum: los informes citados en el mismo documento usan otras
bandas (WGS-84 Zona 18L en CA-CC-01 y CA-SB-01; WGS-84 Zona 19K en CA-SOC-01). Por eso
este módulo convierte únicamente cuando ZONA y DATUM coinciden con lo verificado, y en
cualquier otro caso produce un rechazo tipado; nunca convierte bajo una interpretación
asumida.

Interpretación documentada del par verificado: ZONA=17 con DATUM=WGS84 corresponde a UTM
zona 17 sur (EPSG:32717) porque la cobertura declarada del conjunto es Perú —hemisferio
sur, según los metadatos revisados— y el NORTE de la muestra (9 456 762) solo es coherente
con ese hemisferio. La confirmación sobre el conjunto completo sigue pendiente del
perfilamiento científico; la definición del CRS con el responsable queda en la matriz de
compatibilidad de docs/sources/oefa.md.

pyproj es un extra opcional (geo): la validación y los rechazos no lo requieren, y solo
las conversiones verificadas importan la librería, siguiendo el patrón documentado del
extra tabular. En CI, que instala sin extras, las pruebas de conversión se omiten con
pytest.importorskip.
"""

import functools
import importlib
import math
from typing import Any, Final, Literal

from pydantic import Field

from airaware.schemas import Record

ZONA_VERIFICADA: Final[str] = "17"
DATUM_VERIFICADO: Final[str] = "WGS84"
CRS_ORIGEN: Final[str] = "EPSG:32717"  # WGS 84 / UTM zona 17S
CRS_DESTINO: Final[str] = "EPSG:4326"  # WGS 84 (latitud, longitud)
METODO: Final[str] = "pyproj.Transformer.from_crs('EPSG:32717', 'EPSG:4326', always_xy=True)"

MotivoRechazo = Literal[
    "zona_ausente",
    "zona_no_verificada",
    "datum_ausente",
    "datum_no_verificado",
    "este_invalido",
    "norte_invalido",
]


class ConversionCoordenada(Record):
    """Conversión verificada: conserva los originales y registra la operación."""

    este_original: str
    norte_original: str
    este: float
    norte: float
    zona: str
    datum: str
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    crs_origen: str
    crs_destino: str
    metodo: str


class RechazoConversion(Record):
    """Rechazo trazable: conserva los originales y el motivo tipado del rechazo."""

    este_original: str | None
    norte_original: str | None
    zona: str | None
    datum: str | None
    motivo: MotivoRechazo
    error: str = Field(min_length=1)


Resultado = ConversionCoordenada | RechazoConversion


def _limpiar(valor: str | None) -> str | None:
    """Quitar espacios de borde; vacío o solo espacios equivale a campo ausente."""
    if valor is None:
        return None
    limpio = valor.strip()
    return limpio or None


def _decimal(crudo: str | None) -> float:
    """Parsear un número finito; cualquier otra cosa es un rechazo del campo."""
    limpio = _limpiar(crudo)
    if limpio is None:
        raise ValueError("campo ausente o vacío")
    try:
        valor = float(limpio)
    except ValueError as error:
        raise ValueError(f"valor no numérico: {limpio!r}") from error
    if not math.isfinite(valor):
        raise ValueError(f"valor no finito: {limpio!r}")
    return valor


@functools.lru_cache(maxsize=1)
def _transformador() -> Any:
    """Transformer perezoso: solo exige el extra geo cuando hay una conversión verificada."""
    try:
        pyproj: Any = importlib.import_module("pyproj")
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "La conversión UTM exige el extra opcional 'geo': uv sync --locked --extra geo"
        ) from error
    return pyproj.Transformer.from_crs(CRS_ORIGEN, CRS_DESTINO, always_xy=True)


def convertir_utm17_sur(
    este: str | None,
    norte: str | None,
    zona: str | None,
    datum: str | None,
) -> Resultado:
    """Convertir ESTE/NORTE de UTM zona 17 sur WGS84 a latitud/longitud verificados.

    Orden de validación determinista: zona, datum, este, norte. Los originales se
    conservan verbatim tanto en la conversión como en el rechazo.
    """
    zona_limpia = _limpiar(zona)
    datum_limpio = _limpiar(datum)
    if zona_limpia is None:
        return RechazoConversion(
            este_original=este,
            norte_original=norte,
            zona=zona,
            datum=datum,
            motivo="zona_ausente",
            error="ZONA ausente o vacía; la conversión exige la zona verificada '17'",
        )
    if zona_limpia != ZONA_VERIFICADA:
        return RechazoConversion(
            este_original=este,
            norte_original=norte,
            zona=zona,
            datum=datum,
            motivo="zona_no_verificada",
            error=(
                f"ZONA={zona_limpia!r} no coincide con la única zona verificada en la "
                f"muestra registrada ({ZONA_VERIFICADA!r}); los informes citados usan otras zonas"
            ),
        )
    if datum_limpio is None:
        return RechazoConversion(
            este_original=este,
            norte_original=norte,
            zona=zona,
            datum=datum,
            motivo="datum_ausente",
            error="DATUM ausente o vacío; la conversión exige el datum verificado 'WGS84'",
        )
    if datum_limpio != DATUM_VERIFICADO:
        return RechazoConversion(
            este_original=este,
            norte_original=norte,
            zona=zona,
            datum=datum,
            motivo="datum_no_verificado",
            error=(
                f"DATUM={datum_limpio!r} no coincide con el único verificado en la muestra "
                f"registrada ({DATUM_VERIFICADO!r})"
            ),
        )
    try:
        este_valor = _decimal(este)
    except ValueError as error:
        return RechazoConversion(
            este_original=este,
            norte_original=norte,
            zona=zona,
            datum=datum,
            motivo="este_invalido",
            error=f"ESTE inválido: {error}",
        )
    try:
        norte_valor = _decimal(norte)
    except ValueError as error:
        return RechazoConversion(
            este_original=este,
            norte_original=norte,
            zona=zona,
            datum=datum,
            motivo="norte_invalido",
            error=f"NORTE inválido: {error}",
        )
    longitud, latitud = _transformador().transform(este_valor, norte_valor)
    if not (math.isfinite(latitud) and math.isfinite(longitud)):
        raise ValueError("La conversión no produjo coordenadas finitas")
    return ConversionCoordenada(
        este_original=este or "",
        norte_original=norte or "",
        este=este_valor,
        norte=norte_valor,
        zona=zona_limpia,
        datum=datum_limpio,
        latitud=latitud,
        longitud=longitud,
        crs_origen=CRS_ORIGEN,
        crs_destino=CRS_DESTINO,
        metodo=METODO,
    )
