# Plan de #13: normalización SENAMHI a Parquet validado y particionado

Responsable: Cristopher (@qriqs). Revisión de contratos y decisiones científicas: Keneth
(@keneth-arias). Rastreador: [issue #13](https://github.com/keneth-arias/Neblima/issues/13).
Rama de esta entrega documental: `docs/issue-13-senamhi-normalization-plan`.
Base revisada: `origin/main` en `081a3ec`, con PR #69 integrado.

Estado: **listo para implementar por entregas pequeñas**. Este plan reemplaza el borrador del
16/11/2026, preparado cuando #12 todavía estaba abierta. La entrega actual contiene únicamente el
plan; no implementa el normalizador ni genera Parquet.

## Decisiones vigentes

La [guía operativa de #13](../docs/sources/senamhi-normalization-handoff.md) gobierna esta ejecución.
#12 está cerrada y entrega `airaware.schemas.Observation`. #43 permanece abierta solo para seguir
la posición del intervalo, calidad individual y aclaraciones futuras; **no bloquea #13**.

- Aplicar la política `senamhi-normalization-20261117-v1` mediante
  `airaware.senamhi_preparation.load_policy` y `observation`, sin duplicar sus reglas.
- Interpretar `FECHA`/`HORA` como UTC según la confirmación explícita de Keneth para toda la
  exportación. `observed_at` conserva ese instante con zona; no restar cinco horas al valor canónico.
  Las vistas locales pueden usar `astimezone` con `America/Lima` sin reemplazar el original.
- PM10, PM2_5 y NO2 usan `ug/m3` como unidades inferidas aceptadas. `unit_raw` permanece nulo y
  `semantic_evidence` registra `units_inferred`; no aplicar una conversión física de NO2 desde ppb.
- Mantener `start`, `end`, `available_at`, `station_id` y `sensor_id` nulos mientras falte evidencia.
  `quality=unknown`; no fabricar banderines, extremos del promedio, identidades ni imputaciones.
- Conservar `raw_fields`, `value_raw`, `parameter_raw`, `time_raw`, SHA-256 y número de registro.
  Cero es finito; ausencias, censura, códigos sin resolver y valores no finitos conservan clases distintas.
- No imponer un mínimo de estaciones o meses continuos, eliminar repeticiones ni descartar una señal
  válida por el conflicto de otra. La resolución de identidades corresponde a #14 y cualquier vista
  derivada de conflictos debe mantener linaje.
- ODC-BY-1.0 permite la distribución con atribución. `DATA_ATTRIBUTION.md` acompaña cualquier
  distribución derivada; esto no cambia la licencia AGPL-3.0-only del código.

El original esperado es `data/raw/senamhi/senamhi_lima_monitoreo_1.csv`, excluido de Git, con SHA-256
`896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4`. Esta copia no lo contiene:
la ejecución real requiere adquirirlo por el flujo documentado o solicitar a Keneth una copia con ese
SHA. No se afirma haber procesado datos reales en esta entrega.

## Arquitectura de la solución

Mantener separadas cuatro responsabilidades pequeñas:

1. **Entrada:** comprobar archivo, tamaño y SHA; leer `utf-8-sig` con coma mediante `csv` en streaming;
   validar encabezado/forma de fila y asignar el número lógico CSV con encabezado=1.
2. **Conversión:** para cada fila invocar `observation` con PM10, PM2_5 y NO2; no modificar el contrato
   común ni la política para resolver errores del adaptador.
3. **Salida:** serializar el contrato con un mapeo Arrow explícito, conservar campos estructurados y
   nulos, ordenar de forma determinista y escribir por lotes en particiones fuente/año/mes UTC.
4. **Control:** registrar política y sus hashes, conteos de entrada/observaciones/rechazos por señal y
   clase, errores trazables y hashes antes/después. La publicación de una carpeta nueva es atómica;
   una falla deja la ejecución incompleta identificable y no sobrescribe resultados aprobados.

Los archivos iniciales previstos son `src/airaware/normalization/`, `tests/test_senamhi_normalization.py`
y una entrada acotada de CLI solo si simplifica la ejecución reproducible. La dependencia Parquet se
agrega cuando se implementa la segunda entrega, fijada con uv y respaldada por documentación oficial de
la versión elegida. Registrar esa elección en `docs/decisions/`; no añadir PyArrow por anticipado.

## Entrega 1: lectura streaming y conversión por señal

**Objetivo:** transformar filas sintéticas en tres observaciones contractuales, o rechazos trazables,
sin cargar el CSV completo ni escribir Parquet.

**Trabajo:**
- Escribir primero pruebas de dialecto, encabezado, SHA y números de registro.
- Implementar un iterador por lotes con tamaño configurable y agregación de errores sin pérdida silenciosa.
- Reutilizar `load_policy`, `timestamp_utc` y `observation`; probar que la adaptación no cambia sus valores.

**Criterios de aceptación:**
- [ ] La entrada se recorre incrementalmente y cada fila produce tres resultados contabilizables.
- [ ] UTC, unidades inferidas, minutos/segundos, valores originales y procedencia coinciden con la política.
- [ ] Fechas/horas inválidas y filas mal formadas generan errores explícitos con registro y contenido
  original disponible; no se omiten ni reparan silenciosamente.
- [ ] Un SHA distinto detiene la ejecución antes de convertir; las pruebas no necesitan red ni originales.

**Verificación:**
`uv run --locked pytest tests/test_senamhi_normalization.py tests/test_senamhi_preparation.py tests/test_observation_schema.py -q`,
luego `make check`, `make build` y `make audit`.

**Dependencias:** ninguna externa; usar datos sintéticos. **Tamaño previsto:** mediano, 3–5 archivos.

### Punto de control 1

Revisión de Keneth del contrato de rechazos y reconciliación antes de introducir el escritor Parquet.
No marcar completo #13 por terminar esta entrega.

## Entrega 2: Parquet determinista, particionado y atómico

**Objetivo:** agregar la salida columnar sobre el iterador aprobado, sin materializar todo el conjunto.

**Trabajo:**
- Seleccionar y fijar la biblioteca Parquet; verificar escritura por lotes, esquema, metadatos y límites
  en su documentación oficial antes de codificar.
- Definir con pruebas el mapeo `Observation`↔Arrow, incluidos `raw_fields`, `time_raw`, listas y nulos.
- Establecer orden, tamaño de lote/grupo y serialización deterministas; particionar por
  `source_id/year/month` derivados de `observed_at` UTC.
- Escribir en una carpeta temporal nueva, validar la lectura de vuelta y publicarla atómicamente solo
  cuando todos los archivos, rechazos y manifiesto sean coherentes. No reemplazar una salida existente.

**Criterios de aceptación:**
- [ ] Dos ejecuciones con idénticos bytes, política, versión de dependencias y configuración producen
  el mismo conjunto ordenado y el criterio de determinismo binario comprobado en el entorno fijado.
- [ ] Las particiones son fuente/año/mes UTC; no se usan fechas locales ni particiones aleatorias.
- [ ] La lectura de vuelta conserva esquema, clases de valor, nulos, tokens y procedencia.
- [ ] La memoria permanece acotada por lotes; una prueba de varios lotes demuestra que no se acumula
  el dataset completo. El umbral de rendimiento se registra después de medir, no se inventa.
- [ ] Un fallo simulado no publica una carpeta aparentemente válida ni modifica el original.

**Verificación:** pruebas sintéticas de ida/vuelta, partición límite de mes/año, repetibilidad, varios
lotes, rechazo de sobrescritura e interrupción; controles completos `make check/build/audit`.

**Dependencias:** entrega 1 aprobada y decisión documentada de la biblioteca. **Tamaño:** mediano.

### Punto de control 2

Keneth revisa el esquema físico, determinismo, procedencia y manifiesto antes de ejecutar el original.
Las salidas sintéticas permanecen en `tmp_path` y no se incorporan a Git.

## Entrega 3: ejecución completa y reconciliación

**Objetivo:** ejecutar el original identificado y demostrar que la exportación conserva todas las filas
y señales sin modificar la fuente.

**Trabajo:**
- Adquirir o recibir el original por un canal autorizado y comprobar su SHA antes de ejecutar.
- Calcular y guardar hashes de entrada antes/después; ejecutar con política y configuración registradas.
- Reconciliar por registro y señal observaciones/rechazos, clases de valor y particiones; inspeccionar
  lectura de vuelta y conservar repeticiones en linaje, sin declarar puntos horarios únicos.
- Entregar solo código, pruebas, manifiesto y resumen pequeño. Datos y Parquet masivos quedan fuera de Git;
  toda distribución incluye `DATA_ATTRIBUTION.md` y los avisos aplicables.

**Criterios de aceptación:**
- [ ] 577 794 filas producen 1 733 382 resultados contractuales: tres observaciones o rechazos por fila.
- [ ] Con el mismo original y política, los conteos se contrastan con la prevalidación: PM10
  380 982 finitos/196 812 ausentes; PM2_5 367 591/210 203; NO2 299 192/278 602. Cualquier diferencia
  se explica y detiene la entrega, sin ajustar datos para coincidir.
- [ ] El SHA original permanece intacto; no hay pérdida silenciosa, sobrescritura ni imputación.
- [ ] El manifiesto permite repetir la ejecución y relacionar cada salida con política, entrada y código.
- [ ] Se completan los tres criterios de #13 o se registra exactamente qué falta; #43 sigue abierto para
  sus preguntas sin convertirlas en falsos metadatos.

**Verificación:** comandos de las entregas anteriores, ejecución CLI real, reconciliación independiente,
hashes antes/después y `make check`, `make build`, `make audit` en la rama final.

**Dependencias:** entregas 1–2 aprobadas y original local verificado. **Tamaño:** mediano.

## Matriz mínima de pruebas sintéticas

| Grupo | Casos obligatorios |
| --- | --- |
| CSV | BOM UTF-8, coma, comillas, encabezado incorrecto, columnas de más/menos, lotes múltiples |
| Procedencia | SHA correcto/incorrecto, encabezado=1, ID determinista por registro/señal, original intacto |
| Tiempo | UTC, conversión separada a America/Lima, `50000`, minutos/segundos, fecha y hora inválidas |
| Valores | `0`, decimal, vacío, `-`, `NA`, `N/A`, `NULL`, `ND`, `<1`, `NaN`, infinito |
| Semántica | `unit_raw=null`, `units_inferred`, `quality=unknown`, `start/end` nulos, sin imputación |
| Identidad | estaciones repetidas o con nombres parecidos sin homologar; IDs nulos y campos originales intactos |
| Parquet | esquema/nulos/listas, fuente/año/mes UTC, cambio de mes/año, orden y determinismo |
| Fallos | varios lotes, interrupción, carpeta existente, lectura de vuelta y rechazos reconciliados |

## Riesgos y límites

- **Dependencia Parquet nueva:** fijar versión y revisar su API oficial; no elegirla por familiaridad.
- **Determinismo binario:** comprobarlo en el entorno fijado y registrar metadatos variables si la
  biblioteca los introduce; no afirmar reproducibilidad entre versiones sin evidencia.
- **Campos anidados:** validar su serialización de ida/vuelta, sin perder tokens ni aplanar identidades.
- **Rechazos:** deben conservar procedencia sin filtrar filas inválidas; su formato se fija con pruebas
  en la primera entrega y se reutiliza en el manifiesto final.
- **Ausencia local del CSV:** bloquea solo la entrega 3. No sustituirla con fixtures ni reportar la
  prevalidación de Keneth como ejecución propia.
- **Usos posteriores:** esta salida no resuelve calidad individual, inicio/fin del promedio, identidad de
  estaciones, elegibilidad de #11, ventanas de entrenamiento ni etiquetas normativas.

## Entrega inmediata

Esta rama documental contiene solo `tasks/issue-13-plan.md`. Tras su revisión e integración, crear la
primera rama de implementación desde el `origin/main` vigente y comenzar por las pruebas sintéticas de
la entrega 1. Mantener una tarea activa por persona, PR pequeños contra `main` y revisión de Keneth.
