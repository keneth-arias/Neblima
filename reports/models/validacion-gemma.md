# Validación de Gemma para pronósticos de PM2.5

Resultados verificados al 22 de noviembre de 2026. La confirmación histórica de
Gemma 3 1B conserva el control de error absoluto medio (MAE) en unidades físicas.
Flamingo con Gemma 3 4B completó la prueba sintética de recuperación en Nebius.

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

- OpenTSLM aprobó 90 pruebas del entorno de pronóstico. La prueba local continua
  y la reanudada coincidieron en el estado del punto de control y la curva de
  500 actualizaciones. MLflow registró 500 valores de pérdida únicos por ejecución.
- Dos restauraciones independientes devolvieron pronósticos idénticos para cinco
  historias sintéticas en los seis horizontes. También se restauró en un proceso
  nuevo cada uno de los tres puntos de control elegidos de la semilla 27.
- La prueba bilingüe comparó ocho casos en español e inglés y 43 tokens de
  referencia. Coincidieron los tokens elegidos y la diferencia máxima de
  log-verosimilitud negativa fue cero al repetir y al restaurar el punto sintético
  con manifiesto `f0ba9a51d8f685a6e4b0f6efeaac30aa6b2f0ead0f832f1df549424cf6b69895`.

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

Los ajustes reales de la semilla 27 con MSE normalizado y MAE físico seguían
en curso en el último registro verificado. Sus puntos seleccionados y resultados
terminales están pendientes. La imagen firmada `v5` para el contraste ponderado
está preparada y su calificación en Nebius queda pendiente.

## Evaluación por fuente

La red neuronal convolucional (CNN) entrenada es la referencia principal. El
conjunto histórico de calibración de 25 201 ventanas y sus tres pliegues
cronológicos purgados pasaron la verificación de entrada. Quedan pendientes el
ajuste y la evaluación de intervalos por punto de control elegible y las
comparaciones con la CNN por separado para OpenAQ, el archivo horario de SENAMHI
y las nuevas horas de estación independientes. Los pesos, las predicciones y los
registros detallados de los puntos de control se conservan en almacenamiento privado.
