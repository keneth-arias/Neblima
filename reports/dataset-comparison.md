# Comparación real de fuentes y preparación del benchmark — #11

> Actualización del 17/11/2026: Keneth eliminó el requisito de cuatro estaciones/24 meses.
> Para SENAMHI se adopta UTC por confirmación del responsable, unidades inferidas aceptadas y
> ODC-BY-1.0 con atribución. Las afirmaciones de bloqueo anteriores son históricas; ver
> [decisión vigente](../docs/sources/senamhi-normalization-handoff.md).

Ejecutada con la política aprobada en configs/benchmark.yaml. Método y denominadores:
[docs/comparison.md](../docs/comparison.md). Evidencia y hashes: [metadata/benchmark-run.json](../metadata/benchmark-run.json).
La consulta a consultas@oefa.gob.pe se envió el 16/11/2026 a las 23:52:57 UTC desde Outlook de
Keneth, sin CC/BCC ni adjuntos; se localizó copia del mensaje. No hay respuesta registrada aún.

## Decisión y alcance

**No hay un benchmark científicamente elegible seleccionado todavía.** SENAMHI es el candidato
prioritario para continuar la preparación técnica de Lima, condicionado a aclaraciones #43 y revisión
institucional/de derechos. OEFA queda excluido del benchmark horario inicial de Lima con este archivo
y parser: sus mediciones locales no tienen inicios horarios interpretables. No es una declaración
sobre inexistencia de mediciones OEFA ni excluye una exportación futura con timestamps completos.

La aprobación de la metodología no confirma unidades, zona horaria, intervalo o banderas. Las
puntuaciones científicas, su sensibilidad y las ventanas científicamente válidas permanecen nulas;
no se sustituyen por cero ni se puntúa una fuente bloqueada para forzar una ganadora.

## Conteos estructurales SENAMHI en Lima

Cada fila suma series provisionales sin mezclar estaciones; son ventanas superpuestas en reloj
original, no ejemplos independientes ni ventanas finales de entrenamiento. PM2.5 es el objetivo
principal; PM10 se muestra por separado. No se aplicó imputación ni se descartaron extremos.

| Historia (h) | Horizonte (h) | PM2.5 completas | PM10 completas |
| ---: | ---: | ---: | ---: |
| 24 | 6 | 339,205 | 359,251 |
| 24 | 12 | 334,134 | 355,183 |
| 24 | 24 | 324,463 | 347,302 |
| 24 | 48 | 306,645 | 332,414 |
| 48 | 6 | 319,839 | 343,502 |
| 48 | 12 | 315,339 | 339,753 |
| 48 | 24 | 306,645 | 332,414 |
| 48 | 48 | 290,492 | 318,405 |
| 72 | 6 | 302,448 | 328,844 |
| 72 | 12 | 298,360 | 325,321 |
| 72 | 24 | 290,492 | 318,405 |
| 72 | 48 | 275,694 | 304,949 |
| 168 | 6 | 246,651 | 277,307 |
| 168 | 12 | 243,740 | 274,486 |
| 168 | 24 | 238,014 | 268,936 |
| 168 | 48 | 227,053 | 258,151 |

OEFA tiene cero ventanas estructurales PM2.5/PM10 en Lima y Callao para las 16 parejas.
SENAMHI no tiene estaciones etiquetadas Callao en este archivo. Los periodos y geografía se filtran
antes de interpretar horas; no se usa Piura para completar la meta de estaciones de Lima.

## Cobertura simultánea y meta de cuatro estaciones / 24 meses

SENAMHI aporta siete grupos provisionales con ventanas. La cobertura simultánea de al menos cuatro
identidades se mide sobre puntos admisibles, no sobre ventanas completas en los mismos orígenes:

| Señal | Horas con al menos cuatro estaciones | Mayor racha simultánea (h) | Primer / último reloj del subconjunto |
| --- | ---: | ---: | --- |
| pm25 | 55,857 | 5,718 | 2015-01-01 05:00:00 / 2024-05-31 23:00:00 |
| pm10 | 58,362 | 6,329 | 2015-01-01 05:00:00 / 2024-05-31 23:00:00 |

Un intervalo entre extremos de varios años no demuestra 24 meses continuos comunes. Las rachas
observadas no alcanzan 24 meses continuos sin huecos; no se reduce la meta ni se confunde el
denominador de puntuación (24×720 horas) con meses calendario. La decisión sobre la duración del
benchmark sigue pendiente de elegibilidad y posterior fijación de periodos/splits (#18/#19).

## Pérdidas por filtro

El JSON conserva trazas de filas para los ocho escenarios fuente/geografía/señal. Sus categorías
disjuntas suman el original; repeticiones consolidadas se reportan aparte. El Parquet conserva por
serie/H/F las pérdidas por historia incompleta y futuro incompleto, cuya suma con ventanas completas
equivale al universo de orígenes candidatos. No se suman filas descartadas como si fueran ventanas.

Para Lima/OEFA, 2 671 415 filas quedan fuera de geografía, 31 656 por periodo y 180 806 por reloj.
No se llega al filtro de valor en ese escenario; no se presenta esa ausencia como cero valores faltantes.
La misma traza aplica a ambas señales por la precedencia de filtros.

## Solapamientos y reproducción

La intersección entre fuentes en reloj crudo es cero para las dos señales y los dos ámbitos.
La intersección científica queda nula: falta compatibilidad de reloj confirmada. No se emparejan
estaciones ni se deduce cobertura histórica ausente por carecer de timestamps.

```bash
uv run --locked airaware compare run
make check
make build
make audit
```

Salidas locales: `reports/generated/comparison/comparison-fe066c1522014c03a2d753cea3bd2e4c`.

Incluyen forecasting-readiness.parquet, source-overlap.parquet, summary.json y manifest.json.
Los originales se verificaron antes/después y antes de publicar; hashes de ambas salidas Parquet y
summary.json comprobados de nuevo. Los archivos masivos permanecen fuera de Git.

Validación: 222 pruebas sin servicios externos en Python 3.13 y 3.11; formato, tipos, catálogo,
build y auditoría aprobados. No se ejecutó entrenamiento ni se crearon splits. #11 conserva pendiente
la selección científica; implementación y evidencia diagnóstica están completas para revisión.

La composición de las cuatro estaciones simultáneas puede cambiar entre horas; este diagnóstico
no demuestra una cohorte fija de cuatro estaciones con 24 meses de ventanas comunes.
