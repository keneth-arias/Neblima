# Perfilamiento local de las fuentes

Este diagnóstico de #10 mide los originales adquiridos en #8/#9. No normaliza datos,
selecciona estaciones ni declara series aptas para entrenamiento. El plan vigente está en
[tasks/issue-10-plan.md](../tasks/issue-10-plan.md); los resultados reales, en
[reports/profiling.md](../reports/profiling.md).

## Ejecución

Desde la raíz, después de `make setup`, con los originales y manifiestos locales:

```bash
uv run --locked airaware profile run --config configs/profiling.json
uv run --locked airaware profile run --source senamhi-lima-csv
AIRAWARE_DATA_DIR=/ruta/airaware-data uv run --locked airaware profile run
```

`AIRAWARE_DATA_DIR` contiene `raw/` con la misma estructura de adquisición. Cada integrante
puede usar su propio disco sin editar el plan. Los datos masivos no vienen con Git: conservar
las rutas y manifiestos de adquisición o ejecutar primero su adquisición autorizada.
El comando no necesita internet. Seleccionar una fuente desconocida falla antes de procesar.
Una fuente que falla se informa en `errors`, permite terminar las demás y produce salida 1.

Cada ejecución publica una carpeta nueva en `reports/generated/profiling/`, ignorada por Git.
No sobrescribe informes anteriores ni escribe dentro de `raw/`. Se comprueban SHA-256,
columnas, delimitador y conteo esperado. Se vuelve a verificar el original antes de publicar.
Una falla elimina solamente los temporales propios; no publica informes parciales.

DuckDB procesa columnas VARCHAR y exporta Parquet Zstandard. La lectura es estricta:
no omite filas mal formadas y conserva cadenas vacías y marcadores. Usa dos hilos,
`memory_limit=768MB`, temporales locales con límite de 10 GB y extensiones automáticas
inactivas. El límite de memoria de DuckDB no es un límite absoluto del proceso; disponer
además de espacio para la base de trabajo. La dependencia fijada es DuckDB 1.5.6.

## Archivos y denominadores

| Archivo | Una fila representa | Contenido |
| --- | --- | --- |
| datasets.parquet | Una fuente | Filas, columnas, repeticiones exactas, grupos de estación, fechas y estados de reloj |
| stations.parquet | Un grupo provisional de estación | Nombre/contexto original, filas, series, fechas y relojes interpretables |
| signals.parquet | Una señal en un contexto comparable | Celdas, distribución, conflictos, huecos y constantes |
| tokens.parquet | Un token literal por contexto y dimensión | Marcadores/no numéricos y fechas/horas no interpretables |
| manifest.json | Una ejecución de fuente | Entrada verificada, algoritmo, versión DuckDB, duración y hashes de Parquet |

Todos los Parquet incluyen `source_id`, `input_sha256` y `algorithm`. El manifiesto y la
configuración fijada permiten rastrear las entradas. El tiempo de ejecución y el nombre de
carpeta cambian entre ejecuciones; las métricas son deterministas para entradas/versiones iguales.

La identidad provisional agrupa nombre, coordenadas, altitud y ubicación textual. OEFA añade
zona y datum. No se corrigen coordenadas ni se homologan estaciones (#14). `series_context`
es un arreglo JSON de OEFA con este orden: evaluación, periodo, unidad, tipo de análisis,
tipo de muestra y procedencia. SENAMHI usa `[]`. Una misma estación puede tener varios contextos.
Las estadísticas y huecos se calculan por señal dentro de cada contexto, nunca mezclando unidades.

Cada señal conserva como denominador todas las filas de su contexto. Las clases excluyentes son
`finite_count`, `empty_count`, `marker_count`, `invalid_numeric_count` y `nonfinite_count`.
Su suma es `rows`. Un marcador en una columna ancha de OEFA puede indicar que la señal no
corresponde al análisis de esa fila: no se interpreta como porcentaje científico de pérdida.
Los tokens se conservan literalmente; para clasificarlos se recortan espacios y reconocen
`-`, `NA`, `N/A`, `ND`, `NAN`, `NULL`. No se inventa su significado institucional.
No se convierte coma decimal ni se reemplazan vacíos por cero.

## Tiempo y calidad

Las fechas y horas se interpretan sintácticamente en el reloj original, sin zona confirmada.
SENAMHI admite FECHA de ocho dígitos y HORA de hasta seis dígitos con ceros a la izquierda.
OEFA admite fecha ISO y hora HH:MM:SS, opcionalmente precedida por fecha base 1899-12-30/31.
Una hora que contiene solo una fecha base no se convierte en medianoche. `first_date/last_date`
usan la fecha aun si falta hora; `first_parsed_clock/last_parsed_clock` cubren solo la parte
con reloj interpretable. Nunca son una afirmación de cobertura UTC.

`unparsed_start_rows` se divide en fecha no interpretable, hora faltante y hora no admitida
(con precedencia en ese orden). `tokens.parquet` separa dimensiones `start_date`, `start_clock`
y `signal`; los tokens de fecha y reloj no se suman entre sí como filas diferentes.

`exact_duplicate_rows` cuenta filas adicionales con todos los campos decodificados iguales.
No prueba duplicación física de observaciones cuando faltan identificadores u horas.
`duplicate_extra_rows` cuenta repeticiones de serie/inicio/fin con inicio interpretable;
`conflict_slots` cuenta esos grupos con más de un valor finito distinto. No se elimina nada.

Las métricas horarias solo admiten SENAMHI y OEFA con PERIODO exactamente `1 hora`, valores
finitos, inicio alineado y sin ambigüedad de intervalo. `expected_hour_slots` es la extensión
inclusiva entre el primer y último punto admisible, no toda la fecha publicada por la fuente.
`missing_hour_slots` resta instantes admisibles distintos; `longest_gap_hours` mide el mayor
hueco interno. Sin puntos admisibles, las métricas son nulas. Las rachas constantes exigen
horas consecutivas de igual valor y se interrumpen ante huecos o conflictos.

Mínimo, máximo y cuantiles incluyen todas las celdas finitas, con ceros, negativos y repeticiones.
`is_constant` es nulo si no hay valores finitos. `extreme_count` aplica la regla exploratoria
Q1−3×IQR/Q3+3×IQR dentro del contexto. Las marcas no son límites sanitarios, no descartan
picos válidos y no se usan para imputar o ajustar modelos: evitar fuga temporal en #19.

Persisten las aclaraciones de unidades, reloj, intervalos y banderas SENAMHI (#43), y las
limitaciones OEFA documentadas en [sources/oefa.md](sources/oefa.md). #11 debe decidir fuentes
con esta evidencia; #12/#14/#18 definen esquema, identidad y ventanas más adelante.

## Referencias de implementación

- [Lectura CSV de DuckDB 1.5](https://duckdb.org/docs/1.5/data/csv/overview): esquema explícito,
  conservación de cadenas y lectura estricta.
- [Memoria de DuckDB 1.5](https://duckdb.org/docs/1.5/guides/performance/how_to_tune_workloads):
  memoria de trabajo y operaciones que pueden exceder el límite del administrador de búferes.
