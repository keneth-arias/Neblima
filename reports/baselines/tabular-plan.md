# Plan del modelo tabular para PM2.5 en Lima

Estado al 20/11/2026: módulo entregado y verificado con datos sintéticos deterministas
(`tests/test_tabular_benchmark.py`). La **ejecución real se completó el 20/11/2026** sobre las
ventanas históricas de [#19](../../tasks/issue-19-plan.md) y los objetivos externos congelados de
[#88](../models/prueba-externa-pm25-pm10.md): los resultados, denominadores y decisiones de protocolo
están en [tabular-datos-reales.md](tabular-datos-reales.md). Este documento no reporta cifras propias:
todo número citado aquí proviene de [las referencias de #25](lima-pm25.md) o de las particiones de #19.

## Método

- **Características por par ventana-horizonte** (`airaware.benchmarks.features`): los 24 lags
  horarios de PM2.5 de la historia de la ventana (el valor del origen es `lag_00`), el horizonte
  numérico y el calendario UTC de la hora objetivo (seno y coseno de la hora del día). La hora
  válida se deriva del origen más el horizonte, información disponible en el momento de emitir.
  Los objetivos y las etiquetas futuras nunca participan de las características; una prueba
  verifica que dos ventanas con la misma historia y objetivos distintos producen el mismo vector.
- **Procesamiento ajustado solo con entrenamiento** (`airaware.benchmarks.processing`): por
  estación, media, desviación y percentil 95 de los objetivos de entrenamiento. El desfase
  `(valor del origen − media de entrenamiento) / desviación` entra como característica; si una
  estación no aparece en entrenamiento o tiene desviación cero, el desfase queda en 0.0. Las
  estadísticas se exponen en un diccionario serializable para el manifiesto. Una prueba comprueba
  que alterar objetivos e historia de validación deja las estadísticas idénticas.
- **Ajuste con selección en validación** (`airaware.benchmarks.model`): LightGBM con pérdida L1
  (MAE), parada temprana sobre el MAE de validación y elección de iteraciones en validación.
  Sin lightgbm instalado, el doble mínimo documentado `fit_mean_double` elige entre media global
  y media por horizonte (ambas ajustadas solo con entrenamiento) por MAE de validación; ambos
  caminos comparten el contrato inyectable `TabularPredictor`.
- **Evaluación del bloque reservado** (`airaware.benchmarks.predictions`): las predicciones de
  prueba se generan desde las características; una prueba verifica que alterar los objetivos de
  prueba no cambia ninguna predicción.
- **Métricas honestas** (`airaware.benchmarks.metrics`): MAE y RMSE globales, por estación y por
  horizonte con sus conteos. Precisión, exhaustividad, F1 y PR-AUC (precisión media) en Python
  puro, con la predicción puntual como puntuación contra el umbral p95 por estación de
  entrenamiento (agrupación exploratoria calculada sobre pares ventana-hora). Sin etiquetas
  o sin positivos, el informe registra `no_labels` o `no_positives` y métricas `None`.
  Si hay positivos y ninguna alerta, la precisión queda indefinida y tanto la exhaustividad
  como F1 valen cero. La precisión media agrupa los empates en un mismo umbral.
  La calibración usa intervalos de ancho igual. En los intervalos vacíos, la media y la tasa
  quedan indefinidas.

## Contrato de entradas

1. Ventanas completas de #18 con historia de 24 horas y seis objetivos, congeladas en el Parquet
   de [TimeF](../../tasks/issue-22-plan.md) y verificadas contra su manifiesto (en #25 el manifiesto TimeF
   de entrada tuvo SHA-256 `29135340efb377a59d695e05fb6f8848fd0e56481123f5b54e987da77e9adc97`).
2. Particiones de #19 (`splits.parquet` + `manifest.json` de
   `data/benchmarks/lima-pm25-h24-f6-splits`): cada ventana lleva `window_id`, `station_key`,
   `origin_at` y `split`. Solo participan `train`, `validation` y `test`; las ventanas `purged`
   se excluyen siempre.
3. Valores en µg/m³, tiempos UTC con zona confirmada, sin imputaciones por parte del modelo: las
   ventanas completas de #18 ya garantizan historia y objetivos completos.
4. Los identificadores de episodios provendrán de #20; hoy no existen etiquetas emitidas, por lo
   que toda métrica de episodios contra datos reales queda indefinida explícita.

## Selección y comparación con las referencias de #25

- La configuración y las iteraciones se eligen por MAE global de validación en µg/m³, el mismo
  criterio que seleccionó persistencia en #25.
- La comparación se hace sobre objetivos idénticos: unión uno a uno por `window_id` y
  `forecast_hour` contra las predicciones de persistencia de #25 (`predictions.parquet`), con
  verificación exacta del objetivo de cada par. La comparación exige la misma cobertura y estación en
  ambos lados y rechaza objetivos discordantes o claves duplicadas.
- El reporte de la ejecución real incluirá MAE y RMSE globales, por estación y por horizonte, y
  el conteo de pares comunes por partición, citando los MAE publicados de #25 como referencia
  (persistencia: 9,5291 en validación y 6,4459 en prueba).

## Pendientes

- Datos del servidor: resuelto el 20/11/2026 con el árbol compartido en solo lectura; ver
  [tabular-datos-reales.md](tabular-datos-reales.md).
- Etiquetas de episodios de #20 no emitidas: precisión, exhaustividad, F1 y PR-AUC solo podrán
  informarse cuando existan; con los p95 de entrenamiento la detección es una agrupación
  exploratoria, no una etiqueta regulatoria.
- Configuración de hiperparámetros definitiva: propongo añadir a `configs/benchmark.yaml` un
  bloque `tabular` (tasa de aprendizaje, hojas, rondas máximas y parada temprana); el archivo no
  se editó en este PR por ser de solo lectura para esta tarea. La grilla acotada usada en la
  ejecución real quedó declarada en `tools/training/eval_tabular_real.py`.
- Al ejecutarse, seguir el flujo de #28: unir por `window_id`/`forecast_hour`, reportar conteos y
  registrar sumas y SHA-256 de entradas y salidas en el manifiesto. Hecho en la ejecución del
  20/11/2026; la evidencia queda en `metadata/tabular-datos-reales.json`.

## Cómo ejecutar cuando haya datos

```bash
uv sync --locked --extra tabular
uv run --locked --extra tabular pytest tests/test_tabular_benchmark.py
```

El módulo se usa desde Python: `design_rows` por ventana, `ProcessingStats.fit` con las filas de
entrenamiento, `fit_lightgbm` (o `fit_mean_double`) con entrenamiento y validación, y
`predictions_from` sobre el bloque reservado; `paired_evaluation` contra las predicciones de #25
y `episode_metrics` solo cuando #20 haya emitido etiquetas.
