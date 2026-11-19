# Pronóstico de PM2.5 en Lima a seis horas

El cabezal directo de Qwen3.5-0.8B obtuvo el menor error absoluto medio (MAE) entre los dos cabezales con ajuste completo. Por la [regla fijada antes del entrenamiento](../../configs/training/lima-pm25-fit-v1.yaml), se eligió el directo para la comparación con la adaptación de bajo rango (LoRA). La evaluación usa la historia de PM2.5 de las 24 horas anteriores, incluida la lectura en el origen. [Evidencia por modelo y estación](../../metadata/qwen-validation-heads.json).

## Comparación en validación

Cada modelo pronosticó las mismas 50 706 ventanas de siete estaciones provisionales. Los 304 236 pares ventana-hora corresponden a 51 231 horas de estación distintas porque los horizontes se solapan. La tabla presenta MAE en µg/m³. El cambio se calcula como el error del modelo menos el de persistencia sobre cada objetivo. La referencia repite la última lectura disponible en la historia. [Referencias de #25](../baselines/lima-pm25.md).

| Modelo | MAE global | Cambio frente a persistencia | MAE a 1 h | MAE a 6 h | MAE con concentración alta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Persistencia | 9,529 | 0,000 | 4,629 | 12,760 | 17,502 |
| Red convolucional temporal | 7,914 | −1,615 | 4,483 | 9,681 | 15,665 |
| Qwen con corrección de persistencia | 7,708 | −1,821 | 4,406 | 9,437 | 15,708 |
| Qwen directo | **7,684** | **−1,845** | **4,302** | 9,460 | **15,625** |

El directo redujo el MAE global en 19,36 % frente a persistencia y en 0,024 µg/m³ frente al otro cabezal. El de corrección tuvo menor error en las horas cinco y seis. El directo mejoró sobre persistencia en las siete estaciones. La reducción osciló entre 0,82 µg/m³ en Campo de Marte y 2,86 µg/m³ en San Juan de Lurigancho. Las comparaciones son descriptivas sobre esta partición cronológica.

La última columna cubre los 48 013 pares ventana-hora (8066 horas de estación distintas) cuyo valor observado alcanzó o superó el percentil 95 de su serie, calculado con entrenamiento. Incluso con el cabezal directo, el MAE en ese subconjunto fue aproximadamente el doble que el global. Las etiquetas horarias y las unidades siguen la [política operativa de SENAMHI](../../docs/decisions/005-senamhi-operating-policy.md). El uso retrospectivo y la calidad desconocida de las observaciones limitan la interpretación.

## Entrenamiento y comprobación

La red convolucional y ambos cabezales completaron 14 837 actualizaciones con 237 392 ventanas, en el orden de la configuración fijada. Se cotejó el SHA-256 de los identificadores de cada lote en ambos registros y en la salida de la red convolucional. SkyPilot registró 75 min 23 s desde el inicio del trabajo hasta la exportación de ambas predicciones. Equivale a 2,51 horas-GPU reservadas entre los dos cabezales. Cada uno ocupó una RTX 5070 Ti, con un pico de 10,43 GiB asignados. El directo procesó 59,78 ventanas/s de cálculo y el de corrección 64,00. Cada punto de control final ocupó 6,52 GiB. La red convolucional se entrenó en CPU. Los puntos de control completos, sus registros y las predicciones están en almacenamiento local.

El archivo de evidencia registra la revisión de cada modelo, los hashes de los pronósticos y el MAE global, por horizonte, estación y concentración alta. Para reproducir el cálculo, usar las salidas de inferencia en µg/m³ y el nombre de modelo del registro. En Qwen, la revisión es el SHA-256 del manifiesto del punto de control. En la red convolucional es la suma de sus pesos. El siguiente ejemplo corresponde al cabezal directo.

```bash
inputs=data/benchmarks/qwen-pm25-v1
fit="$inputs/fits/direct"
revision=1a9bc980ff4f165d6ccb77742f93982763b8c94777f16fae715c3b5bfd7ab0f0
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python \
  tools/timenet-smoke/paired_forecasts.py "$inputs" \
  data/benchmarks/lima-pm25-h24-f6-baselines "$fit/verificacion" \
  --forecasts "$fit/validation.npz" --model qwen-full-direct --revision "$revision"
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python \
  tools/timenet-smoke/forecast_errors.py "$fit/verificacion"
```

La comparación con LoRA emplea el mismo cabezal, semilla, exposición y precisión. Su resultado en validación decidirá qué revisión de Qwen pasará a la ronda de prueba junto con la red convolucional y las referencias.
