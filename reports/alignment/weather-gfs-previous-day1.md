# Alineación GFS `previous_day1` con ventanas de PM2.5 — evidencia real sin red (#17)

Informe de ejecución real de la conversión y verificación de la muestra fijada por #16. **No
hay descargas nuevas ni consultas a proveedores**; los originales se leyeron desde los
paquetes locales verificados por SHA-256. La unión a ventanas congeladas se ejercitó de
extremo a extremo con datos sintéticos construidos con los comandos reales del proyecto
(`benchmark windows`, `benchmark split`); las ventanas congeladas reales no estaban presentes
en este entorno (véanse las limitaciones).

## Ejecución

Directorio: raíz del worktree de `feat/issue-17-weather-alignment` (base
`74c8ae38811dd6d23ff84126bd5fa1dae01dc20c`). Los 7 paquetes GFS del checkout raíz se copiaron
byte a byte a `data/raw/open-meteo-previous-model-runs/` (ignorado por Git) tras verificar sus
SHA-256 contra `configs/acquisition/weather-lima-sample-plan.json`; los originales del checkout
raíz permanecieron intactos y se re-verificaron después de las corridas.

| # | Comando | Resultado |
| --- | --- | --- |
| 1 | `uv run --locked airaware align weather --config configs/weather-alignment.yaml --data-dir data --output data/alignment/gfs-prevday1-run1` | **exit 0** |
| 2 | `UV_OFFLINE=true uv run --locked airaware align weather --config configs/weather-alignment.yaml --data-dir data --output data/alignment/gfs-prevday1-run2` | **exit 0**; sin red |
| 3 | Comparación de corridas | `weather_rows.parquet` lógicamente idéntico (`Table.equals` verdadero) y `manifest.json` byte a byte idéntico |
| 4 | `sha256sum` de los 7 originales antes y después (worktree y checkout raíz) | 7/7 sin cambios |

## Conciliación de la muestra real

- **Filas**: 1176 = 7 estaciones × 168 marcas horarias
  (2022-03-09T00:00Z a 2022-03-15T23:00Z), sin duplicados por estación.
- **Mapeos**: 7/7 coordenadas solicitadas conciliadas con recursos del plan; 0 estaciones sin
  recurso; 0 recursos de otra procedencia.
- **Valores**: 0 faltantes en `temperature_2m_previous_day1` (unidad °C declarada por el
  proveedor y verificada contra la configuración); rango observado 20,8–29,7 °C.
- **Razones de rechazo en conversión**: 0 (la política temporal se evalúa en la unión y está
  probada con sintéticos: rechazo por emisión tardía, por publicación tardía y por emisión
  desconocida, igualdad admitida en el borde, clima futuro solo como pronóstico, y `value`
  expuesto únicamente en filas admisibles; toda fila rechazada o sin valor utilizable queda
  con `value` nulo).
- **Semántica temporal**: `issued_at` = `valid_at` − 24 h (2022-03-08T00:00Z a
  2022-03-14T23:00Z); adelanto nominal uniforme de 24 h; `available_at` nulo;
  `acquired_at` (2026-11-17T23:41:45–48Z) registrado solo como procedencia local.
- **Distancias haversine aproximadas** solicitado→celda devuelta: **2,48–10,041 km**
  (CRS de las coordenadas SENAMHI sin declarar; aproximación geográfica, sin equivalencia).

## Celdas de grilla: lo que dicen los bytes

Los 7 paquetes concilian **4 celdas (lat, lon) distintas** — no un mapeo uno a uno — y las
celdas compartidas quedan visibles con sus estaciones:

| Celda devuelta (lat, lon) | Estaciones que comparten la celda |
| --- | --- |
| (−12.124954, −76.99219) | SAN_BORJA, CAMPO_DE_MARTE |
| (−12.124954, −76.875) | VILLA_MARIA_DEL_TRIUNFO |
| (−12.007805, −76.99219) | SAN_JUAN_DE_LURIGANCHO, SANTA_ANITA, SAN_MARTIN_DE_PORRES |
| (−11.8906555, −76.99219) | CARABAYLLO |

Esto concilia fila por fila con el recibo de #16 (`metadata/weather-acquisition.json`, una
celda por estación). La frase «3 columnas de grilla» del informe de #16 agrupa las celdas de
longitud compartida −76.99219 (3 latitudes distintas); su propia tabla ya registraba la celda
−76.875 de VILLA_MARIA_DEL_TRIUNFO. Este informe conserva ambos hechos sin reetiquetar #16.

- Espaciamiento mínimo observado entre celdas: **0,117149° de latitud** y **0,11719° de
  longitud**. Resolución declarada por el proveedor: no declarada en la respuesta → **nula**
  (no se inventa); las elevaciones devueltas difieren por estación dentro de una celda
  compartida (ajuste del DEM del proveedor; no prueba celdas independientes).

## Paridad de configuraciones (sintética, cadena real)

Con la cadena real grilla→ventanas→particiones sobre datos sintéticos de dos estaciones, el
manifiesto de unión registra `identical_window_id_set: true`, la igualdad de huellas SHA-256
del conjunto de `window_id` (total y elegible, splits vs resumen) y la huella de objetivos
elegibles compartida por ambas configuraciones. Las ventanas con clima faltante permanecen con
estado `missing`/`partial` y conteos explícitos; ninguna se descarta.

## Limitaciones

1. Experimento retrospectivo por tiempo de emisión; **no prueba disponibilidad operativa
   estricta** (`available_at` no documentado por hora por el proveedor).
2. Las ventanas/particiones congeladas reales no estaban presentes en este entorno
   (`data/benchmarks`, `data/timef`, `data/curated` vacíos; el original SENAMHI ya no está
   bajo `data/raw`): sin ventanas reales no se ejecutó una unión real ni se calcularon
   métricas; tampoco se afirma mejora de desempeño alguna.
3. La muestra cubre una semana de 2022 dentro de `train`; toda ventana fuera de esa semana
   queda con clima faltante explícito.
4. CRS SENAMHI sin declarar: distancias aproximadas; celdas compartidas no son observaciones
   independientes ni mediciones en la estación de aire.

## Matriz de verificación de los criterios de #17 (auditoría del 20/11/2026)

Auditoría criterio por criterio contra la evidencia fusionada en `main` (`94bbad9`): el módulo
`src/airaware/weather_alignment.py` (775 líneas), las 17 pruebas de
`tests/test_weather_alignment.py` (contadas con `pytest` y `grep '^def test_'`; sin red), la
configuración `configs/weather-alignment.yaml` y la política de comparación
`configs/benchmark.yaml` (`comparison-v3`, referencia solo contaminación). Ninguna prueba
existente fue modificada. Controles ejecutados en la rama de esta auditoría: `make check`
(salida 0; 406 pruebas aprobadas, 17 de este módulo), `make build` (salida 0) y `make audit`
(salida 0, sin vulnerabilidades conocidas).

| Criterio de #17 | Campo de configuración | Registro en el módulo | Prueba exacta | Evidencia en este informe |
| --- | --- | --- | --- | --- |
| (1) Distancias o interpolación espacial | `stations[].coordinate_reference: undeclared` para las 7 estaciones | columnas `requested_latitude`/`requested_longitude`, `returned_cell_latitude`/`returned_cell_longitude`/`returned_cell_elevation_m`, `distance_km_haversine`, `spatial_method=open_meteo_grid_cell_lookup` y `distance_note` en `WEATHER_ROWS_SCHEMA`; cálculo `_haversine_km` | `test_conversion_records_temporal_semantics_and_provenance`; `test_conversion_maps_requested_stations_to_shared_grid_cells` | «Distancias haversine aproximadas … 2,48–10,041 km» y tabla de celdas compartidas |
| (1) Desfases temporales | `nominal_lead_hours: 24`; `issued_at_rule: previous_day1_nominal_lead` | columnas `valid_at`, `issued_at` (= `valid_at` − 24 h), `lead_hours` e `issued_at_rule` | `test_conversion_records_temporal_semantics_and_provenance` | «Semántica temporal: `issued_at` = `valid_at` − 24 h …» |
| (1) Resolución del producto | sin campo: el proveedor no declara resolución en la respuesta | `declared_grid_resolution: null` (honesto, no se inventa) y `observed_grid_spacing_deg` en la reconciliación del manifiesto | `test_conversion_reports_observed_grid_spacing_per_dimension` | «Espaciamiento mínimo observado …; resolución declarada … nula» |
| (2) Solo variables disponibles al momento del pronóstico | `excluded_realized_variables: [temperature_2m]`; `product_class: archived_forecast`; `experiment_class: retrospective_issue_time` | cláusula de admisión en `JOIN_QUERY` (`rejected_issue_unknown`, `rejected_issue_after_origin`, `rejected_available_after_origin`); `value` expuesto solo en filas `admissible` (fail-closed); `hour_role` separa `history_input` de `target_forecast`; validador `explicit_exclusions` bloquea la variable realizada | `test_join_rejects_issue_after_origin_and_accepts_boundary_equality`; `test_join_rejects_late_publication_with_earlier_valid_time`; `test_join_masks_feature_value_of_late_issue_and_late_publication`; `test_join_fails_closed_when_issue_time_is_unknown`; `test_join_classifies_present_rows_without_usable_value_as_missing`; `test_join_allows_future_valid_time_only_as_forecast` | «Razones de rechazo en conversión» |
| (2) Conservar fechas de emisión y disponibilidad | `issued_at_rule`; `available_at_policy: undocumented_null` | columnas `issued_at`, `available_at` y `acquired_at` separadas en `WEATHER_ROWS_SCHEMA`. La unión proyecta `issued_at`, `available_at` y la huella del original; `available_at` permanece nulo y `acquired_at` (procedencia local) nunca lo sustituye | `test_conversion_records_temporal_semantics_and_provenance` (conserva las tres fechas); `test_join_masks_feature_value_of_late_issue_and_late_publication` (metadatos íntegros en filas rechazadas); `test_repository_config_matches_pinned_acquisition_plan` (`available_at_policy == "undocumented_null"`) | «Semántica temporal» y limitación 1 |
| (3) Configuraciones separadas solo contaminación / con meteorología | `configs/weather-alignment.yaml` (variante `pm25_gfs_previous_day1`) + `comparison_policy: configs/benchmark.yaml` (`comparison-v3`) | manifiesto: `experiment.reference_configuration: pm25_only` frente a `experiment.weather_configuration`; `AlignmentConfig` con `extra="forbid"` y estaciones únicas | `test_repository_config_matches_pinned_acquisition_plan` (configuración del repositorio válida y conciliada con el plan fijado de 7 coordenadas) | «Paridad de configuraciones (sintética, cadena real)» |
| (3) Pruebas de cruce | — (la paridad se calcula, no se configura) | bloque `parity` del manifiesto: `identical_window_id_set`, huellas SHA-256 del conjunto de `window_id` (total y elegible, splits frente a resumen) y `eligible_targets_sha256`; la unión nunca descarta ventanas ni reescribe objetivos | `test_full_chain_end_to_end_is_deterministic_and_parity_holds`; `test_missing_weather_stays_null_with_explicit_mask` | «Paridad de configuraciones (sintética, cadena real)» |

## Alcance de las pruebas retrospectivas

Las pruebas cubren la unión retrospectiva por hora de emisión. Con `available_at` nulo,
la consulta admite un valor si cumple las demás condiciones. Para verificar disponibilidad
operativa hace falta conocer la hora de publicación del proveedor y exigir que sea anterior
o igual al origen. Inventario de las 17 pruebas revisadas:

1. `test_conversion_records_temporal_semantics_and_provenance` — semántica temporal
   (`issued_at`, `lead_hours`, `issued_at_rule`, `available_at` nulo, `acquired_at` del
   manifiesto), clase de producto, unidad, exclusión de la variable realizada y distancia
   haversine en la conversión.
2. `test_conversion_maps_requested_stations_to_shared_grid_cells` — mapeo de estaciones
   solicitadas a celdas devueltas, incluidas celdas compartidas por varias estaciones.
3. `test_conversion_reports_observed_grid_spacing_per_dimension` — espaciado de grilla
   observado por dimensión y `declared_grid_resolution` nulo honesto.
4. `test_conversion_is_deterministic_and_refuses_existing_output` — determinismo de la
   conversión y rechazo de una carpeta de salida existente.
5. `test_conversion_verifies_pinned_bytes_and_detects_tampering` — verificación de los bytes
   fijados por SHA-256 y detección de manipulación posterior.
6. `test_conversion_rejects_uncovered_station_and_extra_bundle` — rechazo de estaciones sin
   recurso y de recursos ajenos a la configuración.
7. `test_join_rejects_issue_after_origin_and_accepts_boundary_equality` — rechazo de emisión
   posterior al origen con igualdad exacta admitida en el borde.
8. `test_join_rejects_late_publication_with_earlier_valid_time` — rechazo de publicación
   tardía aunque el instante válido sea anterior al origen.
9. `test_join_masks_feature_value_of_late_issue_and_late_publication` — máscara de `value` en
   filas rechazadas con metadatos temporales conservados para auditoría.
10. `test_join_classifies_present_rows_without_usable_value_as_missing` — filas con estado
    `present` pero sin valor utilizable clasificadas `missing_weather` con `value` nulo.
11. `test_join_fails_closed_when_issue_time_is_unknown` — `rejected_issue_unknown` cuando
    `issued_at` es nulo; la fila no es admisible.
12. `test_join_allows_future_valid_time_only_as_forecast` — clima con instante válido posterior
    al origen admitido solo como `target_forecast`, nunca como insumo histórico.
13. `test_missing_weather_stays_null_with_explicit_mask` — máscara explícita por hora y por
    ventana sin descartar ventanas (cubre `complete`, `partial` y `missing`).
14. `test_full_chain_end_to_end_is_deterministic_and_parity_holds` — cadena completa
    determinista con paridad de ventanas y objetivos entre configuraciones.
15. `test_join_validates_weather_manifest_and_frozen_chain` — validación de versión y SHA-256
    del paquete meteorológico y de la cadena congelada grilla→ventanas→particiones.
16. `test_cli_requires_join_arguments_together` — la unión exige ventanas, grilla y particiones
    juntas o falla.
17. `test_repository_config_matches_pinned_acquisition_plan` — la configuración del
    repositorio concilia con el plan de adquisición fijado (7 coordenadas) y conserva la
    política `undocumented_null`.

## Qué falta para cerrar #17

1. **Unión real meteorología–contaminación** sobre las ventanas y particiones congeladas del
   paquete de datos (#13/#18): en este entorno `data/benchmarks`, `data/timef` y `data/curated`
   están vacíos, de modo que la paridad quedó demostrada con la cadena real y datos
   sintéticos. Ejecutar la unión sobre los datos reales y registrar su reconciliación cuando
   el servidor esté disponible.
2. **Disponibilidad horaria del producto archivado**: el proveedor no documenta `available_at`
   por hora (política `undocumented_null`); verificarla contra el servidor para sustituir el
   experimento retrospectivo por tiempo de emisión por disponibilidad operativa estricta.
