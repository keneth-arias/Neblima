# Validación pareada del pronóstico de PM2.5 y PM10 en Lima

**Pregunta.** Con el mismo modelo y las mismas ventanas, ¿cuánto cambia el error de pronosticar cada contaminante cuando se incorpora la historia de PM10? Keneth coordina cuatro entregas de [#88](https://github.com/keneth-arias/Neblima/issues/88). El registro histórico que preparó #101 permite empezar el experimento mientras avanza el conector público. [Datos y procedencia](../reports/prueba-externa-pm.md)

| Variante | Historia de 24 horas | Salida directa para las horas +1 a +6 |
| --- | --- | --- |
| A | PM2.5 con el canal PM10 enmascarado | PM2.5 y PM10 |
| B | PM2.5 y PM10 | PM2.5 y PM10 |

## 1. Exportar las ventanas y fijar la escala · [#102](https://github.com/keneth-arias/Neblima/issues/102)

En Neblima, extender la exportación de `tools/timenet-smoke/export_qwen_windows.py` con un lector para `airaware/lima-pm25-pm10-forecast@0.1.0`. El lector antiguo espera una sola señal y seis escalares. El nuevo contrato lee por nombre dos señales de un registro de entrada y dos de un registro de objetivos. Preparar la exportación en lotes. Conservar `window_id`, estación y origen UTC. Exportar en µg/m³ las matrices de historia `[N,24,2]` y objetivos `[N,6,2]`, en orden `[pm25, pm10]`. Verificar nombres, unidades, origen y posición de cada valor contra TimeF.

Aceptar únicamente el registro histórico y las particiones `train` y `validation`. Comprobar el SHA-256 del manifiesto, el corte del 02/04/2023 07:00 UTC y las huellas de identificadores ordenados de #101. Se esperan 251 915 ventanas de entrenamiento y 44 458 de validación, sin horas compartidas entre particiones. Registrar también el hash físico de cada matriz. [Huellas de referencia](../metadata/lima-pm-externa-20261120.json)

Ajustar **un escalador común** antes de formar las variantes. Para cada contaminante, contar una vez cada par `(station_key, hora UTC)` en las **historias de entrenamiento**. Comprobar igualdad de las copias solapadas y conservar ceros. Hay 268 567 pares distintos por contaminante en siete estaciones, según los intervalos del registro histórico. Calcular media y desviación estándar poblacional en float64, con escala 1 si la desviación es cero. Guardar fórmula, unidad, orden, conteos, huellas del entrenamiento y SHA-256 del escalador. Usar las mismas constantes para transformar las entradas visibles y los objetivos, y para volver a µg/m³. Para el desglose por concentraciones altas, fijar aparte el percentil 95 por estación y contaminante sobre esas mismas horas de entrenamiento.

**Aceptación.** Con un fixture, duplicar la aparición de una misma hora conserva el escalador. Alterar objetivos o validación también lo conserva. Una copia contradictoria, una hora fuera del lado permitido del corte o un identificador repetido hacen fallar la exportación. Un fixture con señales distintas detecta canales u horizontes intercambiados. El lector anterior conserva sus pruebas.

## 2. Conectar el entrenador y restaurar las dos salidas · [#103](https://github.com/keneth-arias/Neblima/issues/103)

En la bifurcación de OpenTSLM, `QwenForecaster` ya admite `channels=2, targets=2, horizon=6`. Conectar esas dimensiones a `scripts/train_qwen_forecast.py` y `src/opentslm/forecast_inference.py`. Hoy la carga agrega un eje de tamaño uno, `forecast()` calcula la escala de cada ventana, la restauración crea el modelo con dimensiones predeterminadas y la exportación conserva solo el primer canal. Seleccionar el comportamiento por contrato de versión para poder restaurar también el experimento de #28. [Modelo](https://github.com/keneth-arias/OpenTSLM/blob/9b58825f348ebe6df35265c6f81af95bedcbf290/src/opentslm/forecast.py) · [Inferencia](https://github.com/keneth-arias/OpenTSLM/blob/9b58825f348ebe6df35265c6f81af95bedcbf290/src/opentslm/forecast_inference.py)

Ambas variantes parten de la misma revisión base de Qwen3.5-0.8B y de tensores iniciales idénticos para los adaptadores de bajo rango (LoRA), el proyector y el cabezal. A descarta los valores de la historia de PM10 antes de transformarlos y entrega al proyector cero con máscara falsa en ese canal. B transforma ambos canales y marca las observaciones presentes. Cada variante devuelve `[lote,6,2]`. La pérdida es el promedio de los dos errores cuadrados medios normalizados, cada uno calculado sobre ejemplos y seis horizontes. La inferencia recibe solo identificadores e historias y usa el escalador congelado para invertir las dos salidas.

**Aceptación.** En un modelo restaurado, permutar o sustituir toda la historia de PM10 en A deja idénticas las 12 predicciones en µg/m³. En B, una prueba controlada verifica que el proyector recibe los valores de PM10 y su máscara. Probar un paso con pérdida y gradientes finitos, lectura de historias sin objetivos en inferencia y paridad antes y después de restaurar. Una máscara, orden de canales, versión o SHA-256 de escalador incompatibles deben impedir la restauración. El trabajo con datos sintéticos puede empezar junto con la entrega 1.

## 3. Ejecutar A y B con igual exposición · [#104](https://github.com/keneth-arias/Neblima/issues/104)

Con las entregas 1 y 2, adaptar `runtime/airaware.py` y el modo `pair` de SkyPilot en ml-infra. El lanzador actual arranca dos cabezales distintos y el runtime verifica la versión antigua de TimeF. Usar dos procesos independientes de una GPU, uno por RTX 5070 Ti, ambos con cabezal directo. Montar la versión histórica de solo lectura y separar las carpetas de los dos ajustes en el volumen de estado. El trabajo debe poder completarse con los registros de prueba externos desmontados. [Lanzador de referencia](https://github.com/keneth-arias/ml-infra/blob/a0494072988a19814452b225c2ad5d7018024b9a/workloads/sky/airaware.yaml)

Se propone para ambos brazos LoRA de rango 4 y alfa 8, FP32, semilla 27, lote 16, AdamW con tasa inicial `1e-4`, sin decaimiento de pesos, recorte de gradiente en 1 y calendario coseno. Mantener el paso final como única evaluación programada. Una pasada completa son **15 745 actualizaciones**, con 11 ventanas en la última. El entrenador actual divide por el tamaño del lote redondeando hacia abajo. Conservar la política anterior en su versión y, en la nueva, calcular la pérdida del último lote sobre sus 11 ejemplos. Comparar por SHA-256 los pesos iniciales y la secuencia real de identificadores por lote entre A y B.

Medir primero velocidad, memoria y tiempo de guardado y restauración sobre entrenamiento. Incluir en el presupuesto la inferencia de validación y el guardado, con el tope vigente de cuatro horas-GPU por variante. Si la pasada completa excede el tope, fijar por adelantado el mismo prefijo de lotes y calendario en ambos brazos, y registrar denominador y motivo. Reiniciar desde los mismos pesos base tras la calibración. Guardar cada 15 minutos y al final con publicación atómica. Comprobar que un ensayo interrumpido y reanudado recupera el siguiente lote, el paso y la tasa de aprendizaje.

**Aceptación.** Antes de medir la validación real, versionar configuración, revisión de pesos, digest de imagen, revisión del entrenador, hashes del manifiesto, escalador y permutación, presupuesto y regla de selección. En cada estado guardar también brazo, dimensiones y cursor. Antes de comparar resultados, exigir igualdad de exposición y restaurar los dos pasos finales desde sus respectivas carpetas.

## 4. Comparar la validación y congelar los dos estados · [#105](https://github.com/keneth-arias/Neblima/issues/105)

Preparar en Neblima el evaluador pareado con un fixture mientras se desarrollan los otros PR. Generar la referencia de persistencia de cada contaminante repitiendo su última lectura durante seis horas. La persistencia de PM10 necesita esa lectura y se calcula como referencia independiente de A. Extender el emparejamiento de `tools/timenet-smoke/paired_forecasts.py` con la clave `(window_id, contaminante, horizonte)` y verificar estación, origen UTC, unidad, valor observado y SHA-256 del punto de control. Probar filas desordenadas, duplicadas y faltantes.

| Control exigido por variante en validación | Cantidad |
| --- | ---: |
| Ventanas comunes en siete estaciones | 44 458 |
| Último lote de inferencia a tamaño 16 | 10 ventanas |
| Objetivos de PM2.5 / objetivos de PM10 | 266 748 / 266 748 |
| Predicciones finitas con clave única | 533 496 |
| Horas de estación distintas entre los objetivos | 44 948 |

Publicar el error absoluto medio (MAE) en µg/m³ de A, B y persistencia por contaminante, horizonte y estación, con sus denominadores. Calcular B − A sobre los errores absolutos de las mismas claves. Un valor negativo favorece a B. Informar por separado si la historia de PM10 ayuda a pronosticar PM2.5 y si ayuda a pronosticar PM10. El solapamiento de ventanas produce objetivos repetidos para una hora de estación. Los conteos anteriores permiten interpretar esta comparación descriptiva.

**Criterio de cierre de esta fase.** Congelar los dos puntos de control del paso final acordado, incluso si una variante empeora. Registrar SHA-256 de estados, pesos base, escalador, insumos, predicciones y configuración, junto con el brazo, código, imagen, paso y exposición. Restaurar y reproducir las predicciones de validación con esos identificadores. Un experimento posterior de prueba externa consume ese manifiesto y reporta las dos fuentes por separado. El resultado de esta fase es exclusivamente de validación.

En cada PR de Neblima, ejecutar `make check`, `make test-timef-offline`, `make build` y `make audit`. En OpenTSLM, ejecutar la batería del entorno fijado `environments/forecast` y la prueba de un paso. En ml-infra, verificar el lanzador y el runtime con el contrato nuevo y el anterior antes del piloto en GPU.
