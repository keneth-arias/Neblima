"""Conversión de coordenadas OEFA con respaldo del sistema de referencia de origen.

La muestra de CA-HUA-01 declara ZONA=17 y DATUM=WGS84. El diccionario de EAS no
confirma su proyección ni su hemisferio (docs/sources/oefa.md). Para convertir, quien
llama debe aportar la referencia que acredita EPSG:32717 para el punto de origen.
"""

from __future__ import annotations

import functools
import math
from typing import TYPE_CHECKING, Final, Literal

from pydantic import Field

from airaware.schemas import Identifier, Record

if TYPE_CHECKING:
    from pyproj import Transformer

ZONA_ADMITIDA: Final[str] = "17"
DATUM_ADMITIDO: Final[str] = "WGS84"
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
    "crs_sin_evidencia",
    "fuera_del_dominio",
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
    evidencia_epsg_32717: Identifier
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
def _transformador() -> Transformer:
    """Transformer perezoso: solo exige el extra geo cuando hay una conversión verificada."""
    try:
        from pyproj import Transformer
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "La conversión UTM exige el extra opcional 'geo': uv sync --locked --extra geo"
        ) from error
    return Transformer.from_crs(CRS_ORIGEN, CRS_DESTINO, always_xy=True)


def convertir_utm17_sur(
    este: str | None,
    norte: str | None,
    zona: str | None,
    datum: str | None,
    *,
    evidencia_epsg_32717: str | None = None,
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
    if zona_limpia != ZONA_ADMITIDA:
        return RechazoConversion(
            este_original=este,
            norte_original=norte,
            zona=zona,
            datum=datum,
            motivo="zona_no_verificada",
            error=(
                f"ZONA={zona_limpia!r} no coincide con la zona admitida para la "
                f"muestra registrada ({ZONA_ADMITIDA!r}); los informes citados usan otras zonas"
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
    if datum_limpio != DATUM_ADMITIDO:
        return RechazoConversion(
            este_original=este,
            norte_original=norte,
            zona=zona,
            datum=datum,
            motivo="datum_no_verificado",
            error=(
                f"DATUM={datum_limpio!r} no coincide con el datum admitido para la muestra "
                f"registrada ({DATUM_ADMITIDO!r})"
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
    if evidencia_epsg_32717 is None or not evidencia_epsg_32717.strip():
        return RechazoConversion(
            este_original=este,
            norte_original=norte,
            zona=zona,
            datum=datum,
            motivo="crs_sin_evidencia",
            error="Falta la referencia que acredita EPSG:32717 para este punto.",
        )

    # Evitar que la proyección inversa envuelva coordenadas proyectadas imposibles.
    if 0 < este_valor < 1_000_000 and 0 < norte_valor <= 10_000_000:
        longitud, latitud = _transformador().transform(este_valor, norte_valor)
        # Área de uso de WGS 84 / UTM zona 17S, incluidos el ecuador y los meridianos límite.
        if -84 <= longitud <= -78 and -80 <= latitud <= 0:
            return ConversionCoordenada(
                este_original=este or "",
                norte_original=norte or "",
                este=este_valor,
                norte=norte_valor,
                zona=zona or "",
                datum=datum or "",
                latitud=latitud,
                longitud=longitud,
                evidencia_epsg_32717=evidencia_epsg_32717,
                crs_origen=CRS_ORIGEN,
                crs_destino=CRS_DESTINO,
                metodo=METODO,
            )
    return RechazoConversion(
        este_original=este,
        norte_original=norte,
        zona=zona,
        datum=datum,
        motivo="fuera_del_dominio",
        error="El punto queda fuera del dominio de UTM zona 17 sur.",
    )
