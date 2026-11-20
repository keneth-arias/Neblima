# Selección histórica del pronóstico de PM2.5 en Lima

La regla registrada eligió el cabezal **directo con la semilla 27** para la prueba externa de concentraciones. Se compararon dos variantes de Qwen3.5-0.8B con LoRA de rango 4 y alfa 8. Cada ajuste recorrió las mismas 237 397 ventanas de entrenamiento en 14 838 pasos, incluido el último lote parcial. Las dos semillas fueron 27 y 28. Cada ajuste usó una RTX 5070 Ti durante 0.94 a 0.98 horas según MLflow. La referencia directa usa los residuos de calibración por horizonte para construir el intervalo del 80 %. El candidato predice los cuantiles 10, 50 y 90. [Regla registrada](../../configs/training/lima-comparacion-cuantiles-v1.yaml)

## Resultados en selección

Los dos cabezales se puntuaron en los mismos 25 305 orígenes de siete estaciones. Hubo 151 830 pares origen–horizonte observados y 13 313 en horas altas según el percentil 95 de cada estación en entrenamiento. Al deduplicar por estación y hora objetivo quedan 25 570 horas distintas, de ellas 2 234 altas. El error absoluto medio (MAE) y la amplitud se expresan en µg/m³. La cobertura indica la fracción observada dentro del intervalo.

| Semilla | Cabezal | MAE global | MAE alto | Cobertura global | Cobertura alta | Amplitud global | Corrida |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 27 | Directo | 6.238 | 15.788 | 90.68 % | 55.77 % | 28.347 | [MLflow](http://bm.degu-fir.ts.net:5000/#/experiments/2/runs/7d09aac2b99943b78fe9c309f26a123f) |
| 27 | Cuantiles | 6.158 | 17.135 | 78.47 % | 57.60 % | 19.081 | [MLflow](http://bm.degu-fir.ts.net:5000/#/experiments/2/runs/bb32b92dc0394f8bb435cae736ac6fe3) |
| 28 | Directo | 6.287 | 15.653 | 90.57 % | 55.26 % | 28.330 | [MLflow](http://bm.degu-fir.ts.net:5000/#/experiments/2/runs/e5547072e3a34028a7cc796044f7ced3) |
| 28 | Cuantiles | 6.164 | 16.952 | 78.88 % | 58.43 % | 19.430 | [MLflow](http://bm.degu-fir.ts.net:5000/#/experiments/2/runs/af35ec3e9ed74c729ab723294e94cd97) |

En el promedio de las dos semillas, el cabezal de cuantiles redujo el MAE global de 6,263 a 6,161 µg/m³ y elevó el MAE en horas altas de 15,720 a 17,044 µg/m³. Este último resultado determinó la elección del directo. La cobertura en horas altas fue 55,51 % para el directo y 58,01 % para cuantiles, por debajo del 80 % nominal en ambos casos. [Decisión y medias completas](../../metadata/seleccion-concentracion-lima-v1/seleccion.json)

| Semilla | Estrato | Diferencia de MAE, cuantiles menos directo | Intervalo del 95 % | Bloques de 168 h |
| --- | --- | ---: | --- | ---: |
| 27 | Todos | -0.080 | -0.105 a -0.056 | 26 |
| 27 | Horas altas | 1.347 | 1.296 a 1.413 | 25 |
| 28 | Todos | -0.123 | -0.147 a -0.099 | 26 |
| 28 | Horas altas | 1.300 | 1.251 a 1.359 | 25 |

El remuestreo usa bloques de calendario compartidos por las estaciones. Los informes por semilla conservan los resultados por horizonte, estación y longitudes de bloque de 84, 168 y 336 horas. Estas medidas describen selección retrospectiva. El resultado de la semana futura de Campo de Marte determinará si corresponde revisar un piloto privado en esa estación. [Semilla 27](../../metadata/seleccion-concentracion-lima-v1/semilla-27.json) · [Semilla 28](../../metadata/seleccion-concentracion-lima-v1/semilla-28.json) · [Protocolo de prueba](prueba-futura-campo-marte.md)

## Artefacto reservado

El sello se emitió el 2026-11-20T19:40:38.579459+00:00. Su SHA-256 es `05247b30009d94399d68cfeff86a2449c6f3d936ab59270122751e0d23fde059`. La decisión tiene la huella `291e4edc20b1146aac07a2e16594b1c2fe30b64e69511f3e72de0b041be1056f` y la versión retenida en bm tiene la huella `fd7c047dbacb311d80424f1c2e5841a868b916fcf75ca5c6e68f28044e1daf10`. La generación seleccionada es `step-00014838`, con manifiesto `d42dc1d91dce1abc6284f9cff68df3d0ff7ccbc08ede744865cde1762e53658e`. La copia conserva el modelo y sus componentes fuera de la rotación de los ajustes. La publicación de este registro precede a la adquisición de los datos reservados. [Sello](../../metadata/seleccion-concentracion-lima-v1/sello.json) · [Versión retenida](../../metadata/seleccion-concentracion-lima-v1/release.json) · [Corridas y consumo medido](../../metadata/seleccion-concentracion-lima-v1/corridas.json)
