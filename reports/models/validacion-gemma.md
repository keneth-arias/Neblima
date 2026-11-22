# Validación de Gemma para pronósticos de PM2.5

Resultados verificados al 22 de noviembre de 2026. La confirmación histórica de
Gemma 3 1B conserva el control de error absoluto medio (MAE) en unidades físicas.
Para Flamingo con Gemma 3 4B, la validación de la versión `v4` conserva el
control de error cuadrático medio (MSE) normalizado. La comparación de
ponderación por picos de `v5` está en curso.

Los resultados también están disponibles como archivos JSON.

- [Validación por punto de control](../../metadata/resultados-gemma-20261122/validacion.json)
  reúne los pasos seleccionados, las huellas y las métricas disponibles por horizonte.
- [Pruebas](../../metadata/resultados-gemma-20261122/pruebas.json) registra las
  verificaciones del repositorio, la paridad bilingüe y las recuperaciones sintéticas.
- [Benchmark](../../metadata/resultados-gemma-20261122/benchmark.json) incluye la
  confirmación histórica de 1B frente a persistencia, la validación interna y los
  tiempos de ejecución de Flamingo v4, y el estado del benchmark externo con la CNN.

## Gemma 3 1B en MicroK8s

Se usó `google/gemma-3-1b-pt` en la revisión
`fcf18a2a879aab110ca39f8bffbccd5d49d8eb29` con el entrenador OpenTSLM
`1bc3cb17cf431dd2d13e8632ff939d3406597096`. Todos los ajustes usaron 225 338
ventanas de entrenamiento, 6 664 de validación interna, 24 horas de historia y seis
de horizonte. El brazo ponderado asigna peso doble a los objetivos desde el
percentil 95 de cada estación, calculado solo con datos de entrenamiento.

Se evaluó cada 500 actualizaciones y se seleccionó por MAE global de validación.
Después del primer punto elegible, se requirió una mejora de al menos 0,02 µg/m³
para reemplazarlo. Los cinco ajustes terminaron por parada temprana tras cuatro
evaluaciones sin la mejora requerida. Cada variante tuvo 12 bloques de validación
con horas altas. El SHA-256 identifica el manifiesto del punto seleccionado.

| Semilla | Objetivo | Paso elegido | Paso final | MAE global (µg/m³) | MAE en horas altas (µg/m³) | SHA-256 del manifiesto seleccionado |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 27 | Error cuadrático medio (MSE) normalizado | 2 000 | 4 000 | 5,433 | 24,433 | `a741c2bca2b9169f5a2d7e2ce4382170900ecebae148d5810a2406f492ff4dd7` |
| 27 | MAE físico | 4 500 | 6 500 | 5,124 | 26,198 | `f1da0c412e9b918f8f4d8a11c8b6b5ee197150501b8e6ea97cd33be01d54304c` |
| 27 | MAE ponderado por picos | 4 500 | 6 500 | 5,103 | 24,382 | `b4e1959ff8731a371f5d52bc8d009f64f1eeee9ac5e3896824f251d6b15ef650` |
| 28 | MAE físico | 4 500 | 6 500 | 5,200 | 26,916 | `9a30bc75662e70d378739e316ab36ef26ec4aee286f144c490a4b31f04a18db1` |
| 28 | MAE ponderado por picos | 4 500 | 6 500 | 5,183 | 24,976 | `54a70f5b9dade415ddc59458d0eb4f73ff8bdeee33ebe00c003fb7e727629383` |

### Confirmación histórica

Los cuatro puntos de control de MAE de las semillas 27 y 28 se congelaron antes
de evaluar las 5 163 ventanas reservadas. La comparación tiene 30 978 pares de
ventana y horizonte, de los cuales 455 corresponden a 76 horas altas de estación.
La ponderación redujo el MAE en horas altas en 1,188 µg/m³, con un intervalo de
confianza al 95 % de 1,151 a 1,269 µg/m³ en cinco bloques semanales. El MAE global
aumentó 0,021 µg/m³. La regla registrada devolvió `retain_control`.

El registro de selección tiene SHA-256
`6019768d1a05bd5a77fe88590637d486d4f98b9dbc67d68d84dc96550797ba53`.
El informe de confirmación tiene SHA-256
`531a929333f7cdca619f8510de5889ff3502176768c40bcd8108c82d832c5988`.

### Pruebas de ejecución

- OpenTSLM aprobó 90 pruebas del entorno de pronóstico para esta revisión. La
  prueba local continua y la reanudada coincidieron en el estado del punto de
  control y la curva de 500 actualizaciones. MLflow registró 500 valores de
  pérdida únicos por ejecución.
- Dos restauraciones independientes devolvieron pronósticos idénticos para cinco
  historias sintéticas en los seis horizontes. También se restauró en un proceso
  nuevo cada uno de los tres puntos de control elegidos de la semilla 27.
- La prueba bilingüe comparó ocho casos en español e inglés y 43 tokens de
  referencia. Coincidieron los tokens elegidos y la diferencia máxima de
  log-verosimilitud negativa fue cero al repetir y al restaurar el punto sintético
  con manifiesto `f0ba9a51d8f685a6e4b0f6efeaac30aa6b2f0ead0f832f1df549424cf6b69895`.

En el seguimiento del optimizador, la receta con calentamiento y tasas separadas
restauró el paso 19 con manifiesto
`ab88997398305e8fd12a0fc7770101987c9b55820fdf5c3ec3f22834dd4f1eea`.
Coincidieron el estado y las 500 actualizaciones de la prueba sintética frente
a la ejecución continua. La comparación real de las tres recetas con MAE físico
tiene dos ajustes iniciados y el de tasas separadas en cola en el último registro.

## Flamingo con Gemma 3 4B en Nebius

La imagen firmada `v4` usa la revisión de pronóstico
`0791047d28c28117a5a9f5e5a7591022f36c4648` y el índice
`sha256:ed9664a2ea2f23f9c16b1be9d7132ed085498c26285b8d7444c5442b12e95011`.
La prueba bilingüe registró una diferencia máxima de log-verosimilitud negativa de
cero entre repeticiones.

La prueba sintética reanudó desde la actualización 2 con el manifiesto
`6629d9c53e582acf70e8333e7424f15a2e0240f650546cac6c55376dc3b36395` y completó
500 actualizaciones. La ejecución continua y la reanudada coincidieron en 138
tensores del modelo, 414 del optimizador, dos del estado aleatorio, las
evaluaciones de los pasos 0 y 500 y los seis horizontes de pronóstico. El informe
de comparación tiene SHA-256
`eaa12339e47c86d2f3f38f55c8aa24e676b939a8db7bb081dcc86ece2695d841`.

### Ajustes reales de la semilla 27 en v4

Ambos ajustes terminaron por parada temprana en el paso 9 500. Cada punto
seleccionado en el paso 7 500 pasó dos restauraciones nuevas. La misma validación
interna aportó 6 664 ventanas, 39 984 pares de ventana y horizonte y 1 179 pares
de horas altas en 12 bloques semanales.

| Objetivo | MAE global (µg/m³) | MAE en horas altas (µg/m³) | SHA-256 del manifiesto seleccionado |
| --- | ---: | ---: | --- |
| MSE normalizado | 6,028 | 32,804 | `749902d8f49ffee36c208c85e3db3b3735a63f8ea49819298189f062f555ae5b` |
| MAE físico | 6,043 | 33,815 | `871dfa9cbc856c4e7f1c2d559526d8d55d1e2d37c4ecf1475395a78be14639e7` |

El criterio registrado devolvió `retain-control`. La comparación de `v4`
cerró sin replicación de semilla 28 ni evaluación de confirmación. El registro
de decisión tiene SHA-256
`78ddbd8214f23648387f8e692828ccdcbe0ede326f7ff07853dffa0436a3c7bd`.

### Calificación de v5

El índice de la imagen firmada es
`sha256:80d3c62e3dc7f4b4bcbae3f1165d68b2d0880c54d56fe0ac8c5d0153fedd94ee`.
La prueba bilingüe se completó con diferencia cero de log-verosimilitud
negativa entre repeticiones. La prueba sintética restauró el paso 2 con
manifiesto `e3edae3927a0bef39f1ca58aca9d0dfbdf5167611977dce9796d90dcb5b19c87`
y reprodujo las 500 actualizaciones de la referencia, incluidos el orden de los
lotes, la pérdida y la tasa de aprendizaje. Coincidieron las dos evaluaciones
y los seis horizontes, sin huecos en el registro de pérdida ni de tasa de
aprendizaje. El informe de comparación tiene SHA-256
`485a9bd36dbc7887413c8dbe00c036866fbd6d41954774337f32450102e69618`.
Los ajustes reales de la semilla 27 con MAE físico y MAE ponderado por picos
completaron la primera evaluación en el paso 500. Se verificó el mismo orden
de lotes en las primeras 500 actualizaciones de ambos ajustes. Sus resultados
terminales están pendientes.

## Evaluación por fuente

La red neuronal convolucional (CNN) entrenada es la referencia principal. El
conjunto histórico de calibración de 25 201 ventanas y sus tres pliegues
cronológicos purgados pasaron la verificación de entrada. Los dos archivos
históricos tienen insumos y pronósticos de la CNN verificados para una comparación
separada de PM2.5. [Registro de datos y huellas](../../metadata/lima-pm-externa-gemma-20261122.json).

| Fuente | Ventanas | Pares ventana–horizonte | Último objetivo completo | Reloj |
| --- | ---: | ---: | --- | --- |
| OpenAQ | 85 538 | 513 228 | 15/09/2026 11:00 | UTC |
| SENAMHI horario | 102 768 | 616 608 | 19/11/2026 20:00 | Hora publicada por SENAMHI |

La consulta acotada del archivo público de OpenAQ el 22/11/2026 a las 21:02 UTC
encontró cero archivos diarios para las ocho ubicaciones del conjunto entre
el 30/10 y el 22/11 inclusive. La fecha de la última lectura finita conocida
de PM sigue siendo el 29/10 a las 00:00 UTC. Las ventanas completas tienen un
corte anterior. [Archivo público de OpenAQ](https://docs.openaq.org/aws/about).

La captura operativa de SENAMHI para Campo de Marte incorpora 40 originales
verificados y 112 horas con lecturas finitas, hasta el 22/11 a las 15:00
en la hora publicada. La última recepción fue a las 20:09 UTC. Esta serie
operativa queda separada del archivo congelado y del futuro conjunto
independiente. Los intervalos por punto de control y las métricas de Gemma
contra la CNN por fuente siguen pendientes.

Las copias de los archivos congelados y las capturas operativas están bajo
`data/` en bm. Git registra los conteos y las huellas de verificación. Los
pesos, las predicciones y los registros detallados se conservan en
almacenamiento privado.
