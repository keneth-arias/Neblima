# Validación histórica del pronóstico de PM2.5 y PM10 en Lima

Las dos variantes de Qwen pronostican seis horas de PM2.5 y PM10. La variante A recibe 24 horas de PM2.5 y la variante B recibe 24 horas de ambos contaminantes. El protocolo fija el paso 15 745 de cada ajuste para la comparación. La tabla recoge la referencia de persistencia mientras se completan los dos ajustes. [Protocolo del experimento](../../configs/training/lima-pm25-pm10-ajuste-v1.json)

## Referencia de persistencia

Se repitió la última lectura de cada contaminante en las seis horas siguientes. El error absoluto medio (MAE) se calculó sobre 44 458 ventanas de las mismas siete estaciones. Cada contaminante tiene 266 748 objetivos que corresponden a 44 948 horas de estación distintas por el solapamiento entre ventanas. En las seis horas, el MAE fue de **6,453 µg/m³ para PM2.5** y **12,611 µg/m³ para PM10**.

| Horizonte | MAE de PM2.5 (µg/m³) | MAE de PM10 (µg/m³) |
| --- | ---: | ---: |
| +1 | 3,189 | 6,507 |
| +2 | 5,072 | 10,090 |
| +3 | 6,384 | 12,525 |
| +4 | 7,365 | 14,326 |
| +5 | 8,094 | 15,659 |
| +6 | 8,616 | 16,561 |

Cada fila reúne 44 458 observaciones por contaminante. La matriz de validación tiene SHA-256 `12d94d2a3c2ad36972aba46f661cdd00315e7f4b953f21edada4bfb348f7190e`. El cálculo por horizonte equivale a `abs(targets - history[:, -1:, :]).mean(axis=0)` para las matrices en orden de canales `[pm25, pm10]`. El escalador de entrenamiento no interviene en esta referencia. [Particiones y procedencia](../prueba-externa-pm.md)

Los errores de los dos modelos se publicarán tras verificar las predicciones de ambos estados restaurados sobre estas mismas ventanas. El conjunto externo de cada proveedor está reservado para una evaluación posterior. [Seguimiento del ajuste](https://github.com/keneth-arias/airaware/issues/104) · [Comparación y congelación](https://github.com/keneth-arias/airaware/issues/105)
