# Etiquetas de referencia para episodios PM2.5

Revisión: 20/11/2026 UTC. Responsable: Keneth. Regla `pe-pm25-reference-2017-v1`.
Implementación: `airaware.event_labels`; configuración: `configs/thresholds.yaml`.

## Fuentes oficiales y alcance

- [DS 003-2017-MINAM, registro MINAM](https://www.gob.pe/institucion/minam/normas-legales/3670-003-2017-minam),
  [PDF oficial](https://cdn.www.gob.pe/uploads/document/file/12871/DS-003-2017-MINAM.pdf?v=1530656701).
  Anexo en página PDF 4, impresa 9: PM2.5, referencia de 50 µg/m³ para 24 h y 25 µg/m³ anual;
  el criterio diario incluye no exceder más de siete veces al año.
- [DS 010-2019-MINAM, registro oficial MINEM](https://www.gob.pe/institucion/minem/normas-legales/4773310-010-2019-minam),
  [archivo oficial con protocolo](https://cdn.www.gob.pe/uploads/document/file/5323993/4773310-d-s-n-10-2019-minam.7z?v=1698186349).
  Anexo 1, apartado c.i, página PDF 93, impresa 90: promedio diario automático con mínimo 18 horas
  válidas, desde la hora terminada a la 01:00 hasta la terminada a las 00:00 del día siguiente.
  c.iii repite el criterio para campañas; c.ii/c.iv distinguen muestreo manual, mínimo 22 horas.
  El apartado a.i (PDF 90) exige al menos 45 minutos válidos para formar una media horaria automática.
- [DS 011-2023-MINAM](https://www.gob.pe/institucion/minam/normas-legales/4880911-0011-2023-minam)
  incorpora estándares para cadmio, arsénico y cromo en PM10; no sustituye en este módulo la
  referencia PM2.5 del DS 003-2017. La búsqueda dirigida no identificó una referencia PM2.5 posterior
  que la reemplace; esto no equivale a un análisis exhaustivo de toda obligación ambiental aplicable.

Se consultaron páginas y descargaron archivos con Lightpanda. Los enlaces originales MINAM/SINIA
presentaron fallas de navegación o bloqueo por robots; se usaron copias oficiales Gob.pe, manteniendo
el mismo canal. `metadata/event-labels-legal-sources.json` registra fecha de revisión, tamaños, hashes,
páginas inspeccionadas y limitaciones. Archivos completos locales en data/raw/normativa/, fuera de Git.
Se verificaron visualmente la tabla del ECA y el apartado de suficiencia diaria.

## Dos resultados distintos

| Tipo | Intervalo | Suficiencia aplicada | Interpretación |
| --- | --- | --- | --- |
| forecast_24h | Cualquier bloque futuro de 24 h, incluido uno que cruce días | 24/24 objetivos medidos y válidos | Etiqueta del benchmark, no excedencia regulatoria diaria |
| calendar_day | Medianoche local hasta medianoche siguiente | Al menos 18/24 medias horarias automáticas válidas | Comparación diaria con la referencia, no certificación legal |

El límite de 18 es suficiencia del promedio diario automático, no permiso para entrenar con objetivos
faltantes. El constructor de #18 mantiene 100 % de objetivos. Ninguna de estas funciones construye
ventanas, selecciona particiones o utiliza valores futuros como entrada del modelo.

El cálculo toma la media aritmética de valores válidos; nunca rellena horas, convierte valores ausentes
en cero ni pondera de nuevo por minutos. Los promedios horarios de entrada ya deben estar validados
por el proveedor/proceso de calidad. El mínimo de 45 minutos no se puede comprobar con datos horarios
sin evidencia adicional. El módulo no evalúa filtros manuales, campañas ni métodos equivalentes.

Etiquetas:

- `above_reference`: media estrictamente mayor que 50 µg/m³.
- `not_above_reference`: media menor o igual a 50 µg/m³; **no significa aire seguro ni libre de riesgo**.
- `not_evaluable`: faltan horas válidas para el tipo solicitado. La media queda nula y se conserva el
  motivo `insufficient_valid_hours`; no cuenta como caso negativo.

Se comparan los valores numéricos antes de cualquier redondeo de presentación; no se añade una
­tolerancia al umbral. La representación numérica es float de Python; la media usa statistics.mean.
El control `quality_valid=False`, None, NaN, infinito o concentraciones negativas excluye la hora.
Esta exclusión de negativos es una regla de calidad del proyecto, no una interpretación normativa
de todo posible valor instrumental. Se conservan IDs de todos los registros y de los efectivamente
usados, cantidad válida y cantidad requerida, contexto y versión de regla.

## Contrato para #18

`SeriesContext` identifica una única fuente/estación y exige unit=`ug/m3`, timezone IANA documentada,
method=`automatic_hourly` y semantic_evidence no vacío (ruta/ID de evidencia de unidades, reloj,
método y calidad). Declarar estos campos no demuestra por sí solo su veracidad: el integrador debe
verificar la evidencia. No se afirma que hoy existan estas garantías en el CSV SENAMHI; sigue #43.
No se mezclan estaciones ni se infiere unidad o zona horaria desde la ubicación geográfica.

Cada `HourlyPM25` contiene end con zona horaria, value medido, quality_valid e ID único de observación.
El instante representa el **fin** del promedio horario. El adaptador de #18 debe resolver explícitamente
si el reloj original marca inicio o fin; no trasladar filas sin esa comprobación. No alimentar la
función con pronósticos, valores imputados ni medias móviles ya agregadas.

`label_window` recibe start con zona horaria, records, kind, context y la política cargada. Acepta
registros de horas terminadas dentro de (start, start+24h]; start no se incluye y medianoche final sí.
Las comparaciones de instantes se hacen en UTC; el día calendario se determina en la zona documentada.
Rechaza duplicados, IDs repetidos, horas no alineadas, registros fuera del intervalo, calidad no booleana,
semántica desconocida y días locales que no duren exactamente 24 horas. El orden de entrada no altera
el resultado. Ausencias pueden representarse como filas nulas o huecos; se cuentan igual.

Ejemplo sintético desde la raíz (no describe datos reales ni acredita unidades de SENAMHI):

```python
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from airaware.event_labels import HourlyPM25, SeriesContext, label_window, load_policy

start = datetime(2024, 1, 1, tzinfo=ZoneInfo('America/Lima'))
context = SeriesContext('fixture', 'station-1', 'ug/m3', 'America/Lima',
                        'automatic_hourly', 'fixture:semantics-v1')
records = [HourlyPM25(start + timedelta(hours=i+1), 60.0, True, f'obs-{i}')
           for i in range(18)]
policy = load_policy(Path('configs/thresholds.yaml'))
for kind in ('forecast_24h', 'calendar_day'):
    result = label_window(records, start=start, kind=kind, context=context, policy=policy)
    print(kind, result.label, result.valid_hours)
# forecast_24h not_evaluable 18
# calendar_day above_reference 18
```

## Adaptador de ventanas #18 y elegibilidad

`airaware.senamhi_event_labels` integra el paquete de #18 sin modificarlo. Ejecuta la CLI:

```bash
uv run --locked airaware labels senamhi \
  --timeline data/curated/senamhi-lima-hourly \
  --windows data/benchmarks/lima-pm25-h24-f24 \
  --output data/benchmarks/lima-pm25-h24-f24-labels
```

Antes de leer ventanas verifica versión y SHA-256 de la grilla y del paquete, el vínculo
`input_sha256`, la zona UTC, la frecuencia de una hora y el horizonte. Reconstruye cada objetivo
por `series_id` entre `origin_at + 1 h` y `origin_at + 24 h`, ambos inclusive, exige 24 horas
únicas y medidas, la misma estación y un promedio que coincida con `target_mean`; también
reconcilia candidatos, ventanas completas y descartes con el manifiesto. Solo `horizon_hours == 24`
admite `forecast_24h`: un paquete 24/6 u otro horizonte se informa incompatible, nunca se rellena.

La elegibilidad es una comprobación distinta de la estructura. `--evidence` acepta un JSON con
`source_id`, `timezone`, `method=automatic_hourly`, `interval_position=hour_ending`, cadenas no
vacías de evidencia de unidades/calidad y `quality_valid_values`. Sin ese archivo el resultado es
`blocked` con `labeling_evidence_missing`. La posición del intervalo distinta de hora final no se
puede declarar; la calidad nula bloquea con `quality_missing`; un valor no admitido bloquea con
`quality_values_not_admissible`. Por ADR-005, `unknown` no puede admitirse como válido: un archivo
que intente incluirlo se bloquea con `quality_evidence_unknown_not_admissible`. `quality_valid=True`
solo se asigna a horas cuyo valor de calidad figura en la evidencia admitida.

Si la etiqueta es inadmisible se publican únicamente `compatibility.json` y `manifest.json`, con
conteos, conciliación y motivos. Si es admisible, se escribe de forma atómica un paquete nuevo con
`labels.parquet` (`window_id`, serie/estación, `policy_id`, límites, media, etiqueta, horas
válidas/requeridas, motivo, IDs seleccionados/válidos y de origen) y un manifiesto con hashes de
entrada y política, evidencia, horizonte/historia/paso, conteos por etiqueta y por motivo, y hash
de salida. Una falla no publica un paquete parcial.

Ejecución real del 18/11/2026 sobre el original verificado: 324 463 ventanas 24/24 en siete
series, 7 787 112/7 787 112 horas objetivo medidas y conteos conciliados. No se generaron
etiquetas: la posición del intervalo y la calidad individual siguen sin evidencia
(`labeling_evidence_missing`; con una evidencia sintética de prueba, `quality_values_not_admissible`).
El registro compacto está en `metadata/issue-20-label-integration.json`; los datos masivos quedan
fuera de Git. El benchmark principal 24/6 no es un conjunto de episodios etiquetables.

## Verificación antifuga y reconciliación de descartes

`verify_no_label_leakage` comprueba, sobre los archivos del paquete y antes de publicar, que
ningún campo derivado de etiquetas (`label`, `mean_ug_m3`, `valid_hours`, `required_hours`,
`policy_id`, `kind`, `reason`, `observation_ids`, `valid_observation_ids`,
`source_observation_ids`) aparece en el esquema de las entradas (`windows.parquet`); que la
historia declarada termina en `origin_at` y el objetivo empieza después (`history_start <=
origin_at < target_start`, objetivo de exactamente `horizon_hours`); que ningún identificador de
observación del bloque futuro repite uno de la historia; y, si se pasa un archivo de etiquetas,
que cada `observation_ids` publicado refiere horas estrictamente posteriores a `origin_at` y que
la media de cada etiqueta `evaluated` con todas las horas válidas se reconstruye con el promedio
del bloque futuro. Cualquier violación detiene la evaluación sin publicar nada. El manifiesto
registra el resumen en `leakage`.

La emisión de etiquetas reconcilia los descartes por serie con el constructor de #18:
`complete == labels_evaluated + labels_discarded` y
`candidates == complete + history_missing + future_missing` para cada serie; una discrepancia
detiene el proceso antes de escribir. El manifiesto publicado incluye `labels_reconciliation`
con los conteos del constructor y de la emisión por serie; los candidatos descartados por el
constructor (sin historia o sin objetivo completo) no pueden originar etiquetas.

## Matriz de verificación (#20)

Estado al 20/11/2026. «Probado» significa prueba automatizada offline sobre paquetes sintéticos
(`uv run --locked pytest tests/test_senamhi_event_labels.py`); no equivale a validación de datos
reales ni a afirmaciones de cumplimiento legal o ausencia de riesgo.

| Comprobación | Estado | Evidencia |
| --- | --- | --- |
| Umbrales y regla de etiqueta (49,999/50/50,001; 17/18/23/24 horas; negativos y no finitos) | Probado estructuralmente | `tests/test_event_labels.py`; `test_threshold_remains_strict_through_the_adapter` |
| Ventana móvil ≠ excedencia regulatoria diaria; `not_evaluable` ≠ negativo | Probado estructuralmente | `tests/test_event_labels.py`; `test_zero_is_measured_and_negative_value_is_not_a_negative_label` |
| `quality=unknown` jamás válido; calidad nula bloquea; posición del intervalo no coercible | Probado estructuralmente | `test_unknown_quality_and_interval_position_cannot_be_coerced`; `test_evidence_cannot_admit_unknown_quality`; `test_missing_quality_never_becomes_valid_quality`; ADR-005 |
| Reconstrucción exacta del objetivo 24/24, límites, estación, hashes y vínculos | Probado estructuralmente | `test_horizon24_bundle_reconstructs_targets_and_labels`; `test_structural_inconsistencies_are_rejected` |
| `origin_at` excluido del objetivo; objetivos solo de horas > `origin_at` | Probado estructuralmente | `test_origin_at_is_excluded_and_bounds_included`; `verify_no_label_leakage` en `test_history_after_origin_is_rejected_as_leakage` |
| Ningún campo derivado de etiquetas en las entradas del modelo | Probado estructuralmente | `test_label_fields_never_enter_the_model_inputs` (inyección de columna `label` detiene la evaluación sin publicar) |
| Identificadores del objetivo distintos de los de la historia | Probado estructuralmente | `test_label_observations_cannot_reference_history_hours` |
| Media publicada reconstruible solo con el bloque futuro; la historia no altera la etiqueta | Probado estructuralmente | `test_published_mean_and_ids_come_from_the_future_block_only`; `test_history_values_cannot_change_a_target_only_label` |
| Reconciliación de conteos del constructor vs manifiesto (candidatos y descartes por serie) | Probado estructuralmente | `inspect_structure` en `test_structural_inconsistencies_are_rejected[missing_hour]` y conciliación por serie del manifiesto |
| Suma exacta por serie: `complete == elegidas + descartadas(reason)`; discrepancia detiene el proceso (fail closed) | Probado estructuralmente | `test_discard_counts_reconcile_per_series`; `test_missing_window_group_stops_label_publication` |
| Sin evidencia no se emiten etiquetas; fallas no publican paquetes parciales; repetición determinista | Probado estructuralmente | `test_structurally_complete_window_stays_scientifically_inadmissible`; `test_failed_write_publishes_no_partial_bundle`; `test_failure_during_label_write_publishes_nothing`; `test_repeated_execution_is_logically_and_binarily_identical` |
| Conciliación antifuga y por serie sobre el paquete real de #13/#18 con esta versión del código | Exige paquete real (fuera de Git; servidor inaccesible hoy) | Corrida del 18/11/2026 registrada en `metadata/issue-20-label-integration.json` con el código previo; falta re-ejecutar con `leakage` y `labels_reconciliation` |
| Decisión de emitir etiquetas reales sobre datos SENAMHI | Exige evidencia institucional (#43) | Posición del intervalo (`hour_ending`), calidad individual y unidades acreditadas por la fuente; sin ello solo se publica `compatibility.json` |

La verificación estructural no sustituye la evidencia de #43 ni la ejecución sobre el paquete
real: acredita coherencia interna del método de etiquetado, no la semántica de las mediciones
originales ni conclusiones sobre el aire de Lima.

## Límites científicos y regulatorios

Una ventana móvil no se convierte en día calendario por durar 24 h. Una comparación diaria no basta
para decidir el criterio anual de frecuencia; el módulo no implementa el conteo anual ni declara
cumplimiento/incumplimiento legal. Tampoco compara medias anuales con 50 ni calcula alertas sanitarias,
INCA, recomendaciones OMS o diagnósticos de salud. Aplicar esta referencia a datos previos a 2017
solo permite una comparación homogénea del benchmark, no una conclusión legal histórica. Conservar
versiones y fechas de reglas si se implementa después un análisis regulatorio histórico.

## Validación y pendiente

Pruebas sin servicios externos: límites 49,999/50/50,001, 17/18/23/24 horas válidas, falta completa,
calidad, valores inválidos, duplicados/alias UTC, linaje, medianoche y días con cambio de hora.
Comando enfocado: `uv run --locked pytest tests/test_event_labels.py`.

El adaptador agrega pruebas de reconstrucción exacta 24/24, exclusión de `origin_at`, cruce de
medianoche UTC, aislamiento de serie/estación, horizontes distintos de 24, hashes y vínculos,
calidad nula/desconocida, conteos por motivo, paquete vacío, escritura atómica y repetición
determinista, más la verificación antifuga reutilizable (entradas sin campos derivados de
etiquetas, historia antes de `origin_at`, objetivos después, identificadores de historia y futuro
disjuntos, media publicada reconstruible con el futuro) y la reconciliación exacta por serie
entre los descartes del constructor y las etiquetas emitidas:
`uv run --locked pytest tests/test_senamhi_event_labels.py`.

La integración estructural con #18 está verificada con datos reales y sin modificar el paquete de
ventanas. #20 sigue abierta por decisión explícita de Keneth: los criterios de conteos comunes y
antifuga quedan probados de forma estructural (matriz anterior), pero falta acreditar la posición
del intervalo y la calidad individual para emitir etiquetas reales, y re-ejecutar la conciliación
sobre el paquete real con esta versión. Hasta entonces no se generan
etiquetas, no se eligen particiones por desempeño y #26 no debe usar etiquetas no sustentadas.
