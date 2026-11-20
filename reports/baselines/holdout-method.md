# Método de retención (holdout) de estaciones para la evaluación secundaria

Entrega inicial de la issue #32 (Refs #32): el contrato y las garantías probadas
de una evaluación secundaria nacional donde las estaciones reservadas quedan
completamente excluidas del entrenamiento, la validación, la prueba y el
preentrenamiento. El paquete real de datos de #19/#30 sigue pendiente; nada de
este documento evalúa datos reales todavía.

## Alcance y estado

- Código nuevo: `src/airaware/benchmarks/holdout.py` con el subpaquete
  `airaware.benchmarks`; pruebas en `tests/test_holdout_isolation.py`
  (16 pruebas, todas sintéticas, deterministas y sin red).
- No se modificó ningún archivo existente: `senamhi_splits.py`,
  `senamhi_windows.py` y las particiones congeladas de Lima se conservan
  intactos. No hay dependencias nuevas.
- La ejecución real queda pendiente del paquete de datos (#19/#30). Este módulo
  opera sobre el contrato de manifiestos; no lee Parquet ni declara mediciones.

## Plan declarativo y auditable (R1)

`plan_holdout(HoldoutConfig)` fija el plan a partir de una configuración
declarativa: criterio escrito, fecha de elaboración en UTC explícito (no se
consulta el reloj), estaciones reservadas y de entrenamiento con identidad
(`station_key` de 64 hex, nombre, latitud y longitud), periodo reservado de
horas UTC exactas, umbral espacial mínimo en kilómetros y mínimo de horas por
estación. El resultado es un `HoldoutPlan` versionado
(`senamhi-holdout-plan-v1`) cuyo `plan_sha256` cubre todo el contenido
declarado en JSON canónico (claves ordenadas, sin espacios). Dos
configuraciones idénticas producen planes y hash idénticos; cambiar cualquier
entrada cambia el hash. Se rechaza una estación a la vez reservada y de
entrenamiento, claves duplicadas, claves fuera del patrón de identidad,
coordenadas imposibles y periodos mal ordenados o sin zona UTC.

## Aislamiento de estaciones probado (R2)

`verify_isolation(plan, manifests)` comprueba que ninguna estación reservada
aparece en los `counts` de los manifiestos de entrenamiento, validación, prueba
ni preentrenamiento, según el esquema fijado por `senamhi_splits.py`
(`version` `senamhi-pm25-splits-v1` y filas `station_key`/`split`). Una fila de
la estación reservada en cualquier split del paquete —incluida la purga— es una
violación `station_leakage` con el `station_key`, el manifiesto infractor y el
`split`. `assert_isolation` falla cerrado: lanza `HoldoutIsolationError` con el
detalle de cada violación. Un manifiesto con versión distinta o sin `counts`
también falla cerrado. La prueba inyecta la estación reservada en cada manifiesto
(entrenamiento, validación, prueba y preentrenamiento) y exige el fallo con
detalle exacto.

## Aislamiento espacial probado (R3)

El plan declara `min_distance_km`. La verificación calcula la distancia
haversine (radio 6371.0088 km) entre cada estación reservada y cada estación de
entrenamiento; cualquier par por debajo del umbral produce una violación
`spatial_proximity` con la distancia y el par involucrado. La prueba usa una
geometría sintética de distancia conocida (un grado de longitud en el ecuador,
111,195 km) y comprueba tanto el fallo con umbral 150 km como el paso con
100 km sobre la misma geometría.

## Aislamiento temporal probado (R4)

El plan declara el periodo reservado con inicio y fin UTC explícitos sobre la
grilla horaria (solo horas exactas). `verify_isolation(plan, manifests,
periods)` acepta los periodos de entrenamiento o preentrenamiento declarados y
reporta cada solape como `temporal_overlap` con ambos intervalos. Decisión de
frontera documentada: la igualdad exacta de instante se considera solape
(verificación inclusiva), coherente con la purga de fronteras de #19, donde la
hora de un corte pertenece al bloque siguiente; ante una hora compartida se
prefiere rechazar antes que permitir ambigüedad. Las pruebas cubren solape
interior, frontera que se toca exactamente (falla) y periodo disjunto (pasa),
además del rechazo de instantes sin zona UTC.

## Representatividad honesta (R5)

`summarize_representativity(plan, period_grid_manifest)` produce un resumen
serializable con la cobertura de cada estación reservada: horas con medición
observada de PM2.5 dentro del periodo reservado según el esquema de counts de
la grilla de #15 (`senamhi-hourly-v1`), horas esperadas del periodo cerrado,
cobertura, mínimo declarado y marca `sufficient`. Las estaciones por debajo del
mínimo se listan en `insufficient_station_keys` y `all_sufficient` queda en
falso; una estación sin filas se reporta con cero horas disponibles. Nunca se
inventan horas ni se imputa: la insuficiencia se informa, no se corrige. En la
ejecución real, las horas del periodo deben contarse del `hours.parquet` del
paquete de #19/#30 filtrando `observed_at` dentro del periodo reservado y
`status = 'observed'`, tras verificar los SHA-256 de los archivos con
`derived_artifacts.sha256_file`; el manifiesto resultante se entrega tal cual a
esta función.

## Pendiente para cerrar #32

- Ejecutar la retención sobre el paquete real de manifiestos cuando #30
  entregue los datos nacionales: elegir estaciones reservadas con criterio
  documentado, verificar aislamiento contra las particiones congeladas y
  producir el informe de representatividad real.
- Definir el criterio geográfico de selección (representatividad por zona) con
  datos reales; este intento entrega las garantías de exclusión, no la elección
  de estaciones específicas.
- El preentrenamiento nacional mencionado en la issue depende de datos que aún
  no existen en el repositorio; esta entrega no evalúa ni preentrena nada.

## Verificación ejecutada (2026-11-20)

```bash
export PATH="$HOME/.local/bin:$PATH"
make check   # exit 0: 422 passed (406 de la base + 16 nuevas)
make build   # exit 0: sdist y wheel; el wheel incluye airaware/benchmarks/holdout.py
make audit   # exit 0: sin vulnerabilidades conocidas (requiere internet)
```

Las 16 pruebas nuevas están en `tests/test_holdout_isolation.py` y no consultan
la red ni leen particiones reales.
