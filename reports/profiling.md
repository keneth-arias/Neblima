# Perfilamiento real de SENAMHI y OEFA — #10

Ejecutado el 16/11/2026 en la copia de Keneth, sin descargar datos ni modificar originales.
Algoritmo `raw-profile-v2`, DuckDB 1.5.6. [Metodología y denominadores](../docs/profiling.md).
Evidencia estructurada, configuración y hashes de las salidas:
[metadata/profiling-run.json](../metadata/profiling-run.json).

## Cobertura de los archivos completos

| Fuente | Filas | Columnas | Grupos provisionales / nombres | Fechas originales | Inicio con reloj interpretable |
| --- | ---: | ---: | --- | --- | --- |
| SENAMHI | 577 794 | 15 | 7 / 7 | 2015-01-01 a 2024-05-31 | 577 794 |
| OEFA | 2 883 877 | 36 | 38 / 33 | 2018-01-01 a 2022-12-31 | 159 453 |

Los grupos no son estaciones homologadas. La cobertura es del archivo, no implica continuidad
ni cobertura de todo el Perú. OEFA conserva 353 contextos de serie por señal, separados por evaluación,
periodo, unidad y análisis/muestra. SENAMHI tiene siete contextos por señal.

SENAMHI no tiene fechas/horas rechazadas. OEFA tiene 3 fechas no interpretables,
2 715 953 filas con fecha válida y hora faltante, y 8 468 con fecha válida y hora no admitida:
2 724 424 inicios no interpretables en total. Las últimas dos categorías son excluyentes de las
fechas rechazadas. El token HORA_INICIO=NA aparece 2 715 954 veces si se incluye una fila sin fecha.
No se asume medianoche para el token de fecha base `1899-12-31`.

El subconjunto OEFA con inicio interpretable va de 2021-12-08 18:00 a 2022-12-31 23:00;
no representa la cobertura completa de fechas. Todos los relojes siguen sin zona confirmada.

## Celdas de contaminantes

Los vacíos/marcadores se cuentan dentro de todas las filas; OEFA es una tabla ancha y un marcador
puede representar una señal que no corresponde al tipo de análisis. No usar estas proporciones
como pérdida científica sin resolver esa semántica. No hubo tokens numéricos inválidos ni valores
no finitos en las señales configuradas. Se preservan negativos, ceros y todos los valores finitos.

| Fuente / señal | Celdas finitas | Vacías | Marcadores | Conflictos de intervalo | Marcas IQR |
| --- | ---: | ---: | ---: | ---: | ---: |
| SENAMHI / NO2 | 299 192 | 278 602 | 0 | 23 | 2 614 |
| SENAMHI / PM10 | 380 982 | 196 812 | 0 | 20 | 2 121 |
| SENAMHI / PM2_5 | 367 591 | 210 203 | 0 | 20 | 3 576 |
| OEFA / DIOXIDO_AZUFRE | 432 135 | 0 | 2 451 742 | 0 | 36 745 |
| OEFA / MONOXIDO_CARBONO | 183 641 | 0 | 2 700 236 | 0 | 11 180 |
| OEFA / OZONO | 117 086 | 0 | 2 766 791 | 0 | 15 561 |
| OEFA / PM10 | 202 057 | 0 | 2 681 820 | 0 | 8 977 |
| OEFA / PM2.5 | 94 371 | 0 | 2 789 506 | 0 | 2 212 |
| OEFA / SULFURO_HIDROGENO | 188 264 | 0 | 2 695 613 | 0 | 10 169 |

Los siete parámetros meteorológicos OEFA también fueron perfilados (13 señales en total).
Sus resultados completos están en Parquet y en el registro JSON. Las marcas IQR son exploratorias,
no diagnósticos de mediciones inválidas. No se borraron episodios.

## Repeticiones y continuidad

SENAMHI tiene cero repeticiones exactas de todos los campos decodificados. Tiene 84 filas
adicionales por intervalo/serie; los conflictos dependen de la señal (20 PM10, 20 PM2_5, 23 NO2).
OEFA tiene 1 577 173 repeticiones exactas decodificadas; sin horas/identificadores suficientes
no se puede afirmar que sean observaciones duplicadas que deban borrarse. En su subconjunto
con reloj se cuentan 17 833 filas adicionales por intervalo/serie, sin conflictos numéricos.
Estos conteos no se suman entre señales como observaciones diferentes.

| Fuente / señal | Instantes horarios admisibles | Huecos internos (suma de series) | Mayor hueco (horas) | Mayor racha constante (horas) |
| --- | ---: | ---: | ---: | ---: |
| SENAMHI / NO2 | 299 125 | 238 430 | 31 055 | 8 |
| SENAMHI / PM10 | 380 909 | 190 044 | 25 695 | 4 |
| SENAMHI / PM2_5 | 367 518 | 207 679 | 21 125 | 6 |
| OEFA / PM10 | 15 030 | 3 578 | 1 710 | 3 |
| OEFA / PM2.5 | 15 030 | 3 578 | 1 710 | 3 |

Los huecos están limitados al primer/último punto admisible de cada contexto y no comparan
fuentes con una rejilla nacional común. PM10 y PM2.5 OEFA solo tienen dos contextos horarios
admisibles cada una. Para SO2, CO, O3, H2S y radiación solar no hay puntos finitos con reloj
interpretable: los huecos horarios son nulos, no cero. Ninguna serie SENAMHI es totalmente
constante. Algunas series OEFA sí son constantes; revisar los denominadores en Parquet antes
de atribuirlo al equipo o sensor. Las rachas no atraviesan conflictos ni huecos.

## Reproducción y comprobaciones

```bash
uv run --locked airaware profile run --config configs/profiling.json
make check
make build
make audit
```

Se generaron cuatro Parquet por fuente y un manifiesto por ejecución. Las ocho sumas SHA-256
de Parquet se comprobaron después de escribir; la suma original se comprueba antes y después.
Los originales conservaron sus hashes de adquisición. Las salidas locales de esta ejecución son:

- `reports/generated/profiling/senamhi-lima-csv-1d3bd8a030d04241a8b0fb74af27c6dc` (3.888 s).
- `reports/generated/profiling/oefa-csv-ea35801b052142c089362c448a4f3089` (32.929 s).

Las carpetas generadas no se suben a Git. Otra ejecución crea carpetas nuevas. Los manifiestos
registran el contrato de entrada completo, hashes, versión y duración. El perfil se verificó con
195 pruebas sin servicios externos en Python 3.11 y 3.13; formato, tipos, catálogo, build y auditoría
aprobaron, sin vulnerabilidades conocidas. Los datos reales no se requieren en CI.

## Entrega a #11 y bloqueos semánticos

La adquisición y el perfil local ya tienen evidencia real para ambas fuentes. #11 debe comparar
las series elegibles conservando las limitaciones: unidades y zona/intervalo de reloj SENAMHI
pendientes de aclaración (#43); horas ausentes y contextos heterogéneos OEFA; identidad espacial
provisional (#14). No declarar ventanas reales aptas (#18), convertir UTM, fijar unidades o unir
fuentes a partir de estos diagnósticos. La tabla de calidad no resuelve permisos de redistribución.

Estado: implementación y evidencia listas para revisión mediante PR #57 y su continuación;
#10 permanece abierta hasta integrar la entrega. #20/PR #50 conserva su bloqueo separado de #18.
