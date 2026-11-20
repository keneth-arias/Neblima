# ¿Cuánto aporta el historial de PM10 al pronóstico en Lima?

En 44 458 ventanas de validación histórica de Lima, añadir 24 horas de historial de PM10 redujo el error absoluto medio (MAE) de su propio pronóstico de **19,62 a 9,65 µg/m³**, una mejora de **50,82 %**. La persistencia de PM10 obtuvo 12,61 µg/m³. La mejora frente al modelo sin historial de PM10 se observó en las siete estaciones y en los seis horizontes.

Para PM2.5, el MAE pasó de **4,985 a 4,965 µg/m³** (0,40 % menos). El error aumentó alrededor de 0,05 µg/m³ en las horas +1 y +2 y disminuyó entre +3 y +6. Al agrupar por estación, aumentó en San Borja y Villa María del Triunfo y disminuyó en las otras cinco.

## Comparación en las mismas ventanas

La variante A recibió el historial de PM2.5. La variante B recibió los historiales de PM2.5 y PM10. Ambas pronosticaron los dos contaminantes de la hora +1 a la +6. La referencia de persistencia repitió la última lectura de cada contaminante. Todas las columnas de error se expresan en µg/m³. Un valor negativo en B − A indica menor error al añadir el historial de PM10.

| Contaminante | Objetivos | MAE de A | MAE de B | Persistencia | B − A |
| --- | ---: | ---: | ---: | ---: | ---: |
| PM2.5 | 266 748 | 4,99 | 4,97 | 6,45 | -0,02 |
| PM10 | 266 748 | 19,62 | 9,65 | 12,61 | -9,97 |

Las 44 458 ventanas abarcan siete estaciones. Sus horizontes se solapan y reúnen 44 948 horas de estación distintas. La comparación describe este corte histórico y una semilla de entrenamiento. La prueba externa de SENAMHI y OpenAQ queda pendiente.

## Error por horizonte

Cada fila contiene 44 458 objetivos. La columna de persistencia muestra el error de repetir la última lectura disponible en cada horizonte.

| Contaminante | Hora | MAE de A | MAE de B | Persistencia | B − A |
| --- | ---: | ---: | ---: | ---: | ---: |
| PM2.5 | +1 | 2,90 | 2,95 | 3,19 | +0,05 |
| PM2.5 | +2 | 4,33 | 4,39 | 5,07 | +0,05 |
| PM2.5 | +3 | 5,14 | 5,12 | 6,38 | -0,02 |
| PM2.5 | +4 | 5,61 | 5,55 | 7,37 | -0,05 |
| PM2.5 | +5 | 5,88 | 5,81 | 8,09 | -0,08 |
| PM2.5 | +6 | 6,05 | 5,98 | 8,62 | -0,08 |
| PM10 | +1 | 18,55 | 6,00 | 6,51 | -12,55 |
| PM10 | +2 | 19,05 | 8,65 | 10,09 | -10,39 |
| PM10 | +3 | 19,60 | 10,02 | 12,53 | -9,58 |
| PM10 | +4 | 19,91 | 10,71 | 14,33 | -9,20 |
| PM10 | +5 | 20,20 | 11,13 | 15,66 | -9,08 |
| PM10 | +6 | 20,43 | 11,41 | 16,56 | -9,02 |

## Error por estación

| Estación | Contaminante | Objetivos | MAE de A | MAE de B | Persistencia | B − A |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Campo de Marte | PM2.5 | 21 312 | 3,77 | 3,75 | 4,46 | -0,02 |
| Campo de Marte | PM10 | 21 312 | 12,81 | 8,17 | 9,88 | -4,64 |
| Carabayllo | PM2.5 | 44 430 | 6,35 | 6,26 | 9,04 | -0,08 |
| Carabayllo | PM10 | 44 430 | 21,79 | 8,70 | 12,11 | -13,09 |
| Santa Anita | PM2.5 | 51 270 | 4,99 | 4,94 | 6,70 | -0,06 |
| Santa Anita | PM10 | 51 270 | 19,39 | 7,34 | 9,56 | -12,05 |
| San Borja | PM2.5 | 46 218 | 3,93 | 4,00 | 4,64 | +0,07 |
| San Borja | PM10 | 46 218 | 23,29 | 12,39 | 15,81 | -10,89 |
| San Juan de Lurigancho | PM2.5 | 29 640 | 5,58 | 5,53 | 7,39 | -0,06 |
| San Juan de Lurigancho | PM10 | 29 640 | 17,39 | 11,95 | 16,34 | -5,44 |
| San Martín de Porres | PM2.5 | 32 748 | 5,00 | 4,95 | 6,30 | -0,05 |
| San Martín de Porres | PM10 | 32 748 | 15,66 | 8,49 | 10,88 | -7,17 |
| Villa María del Triunfo | PM2.5 | 41 130 | 4,88 | 4,92 | 5,86 | +0,04 |
| Villa María del Triunfo | PM10 | 41 130 | 21,75 | 10,51 | 13,47 | -11,23 |

## Concentraciones altas

Se considera alta la concentración observada que alcanza o supera el percentil 95 del contaminante en la estación. Los umbrales se calcularon con las horas de historia usadas para entrenar.

| Contaminante | Objetivos | MAE de A | MAE de B | Persistencia | B − A |
| --- | ---: | ---: | ---: | ---: | ---: |
| PM10 | 4 439 | 61,62 | 33,84 | 37,54 | -27,78 |
| PM2.5 | 6 682 | 20,73 | 20,58 | 21,89 | -0,14 |

Las ventanas proceden de las observaciones históricas de SENAMHI y conservan la unidad inferida del conjunto de origen. [Fuente y atribución](../../DATA_ATTRIBUTION.md)

## Entrenamiento y reproducción

El corte global del 02/04/2023 a las 07:00 UTC dejó 251 915 ventanas para entrenar y 44 458 para validar. Se purgaron 145 ventanas que cruzaban la frontera. El escalador se ajustó con 268 567 horas de estación distintas de los historiales de entrenamiento. [Particiones y fuentes](../prueba-externa-pm.md)

Los dos ajustes de Qwen3.5-0.8B partieron de los mismos pesos y usaron adaptadores de bajo rango (LoRA), semilla 27 y una pasada con el mismo orden de ventanas. Tras los reinicios del nodo se verificaron los archivos del paso 3783 de A y del paso 3985 de B. La reanudación ejecutó A y luego B, con una RTX 5070 Ti por variante. El primer tramo de la reanudación usó un límite de 36 GiB de RAM y 12 GiB por tarjeta. Después se elevaron los topes a 55 GB de RAM y 16 GB por tarjeta. El límite de PyTorch dejó un margen mínimo de 256 MiB sobre la memoria libre de cada tarjeta al inicio del proceso. El verificador cotejó los identificadores y la tasa de aprendizaje de cada paso, incluidos los lotes repetidos. Ambas llegaron al paso 15 745 con un lote final de 11 ventanas. [Protocolo fijado antes del ajuste](../../configs/training/lima-pm25-pm10-ajuste-v1.json)

Al contar también los lotes repetidos tras los reinicios, los registros contienen 19 580 actualizaciones de A y 19 636 de B. Para cada actualización se dividió la cantidad de ventanas por la velocidad registrada. La suma fue 74,84 minutos de cómputo de entrenamiento en A y 73,10 en B. El intervalo medido comprende el cálculo del pronóstico, los gradientes y la actualización de los pesos. El máximo reservado por PyTorch durante el entrenamiento fue 6,63 GiB por variante.

Se restauró cada estado final y se repitió la inferencia a partir de los identificadores, los canales y los historiales. En A se sustituyó toda la historia de PM10 por valores faltantes. Las 533 496 predicciones de cada restauración coincidieron exactamente con las del mismo modelo. Los pesos y las predicciones por ventana se conservan en almacenamiento local. [Instrucciones de reproducción](../../tools/timenet-smoke/README.md#verificar-el-ajuste-pareado-de-88)

El contenedor montó el lanzador de ml-infra de la revisión `a714eac` para recuperar los estados y reproducir la inferencia. Las huellas SHA-256 verificadas dentro del pod fueron `c7d1dbe4dfed45702bb588a04c01b3bfb6f9b25dcad2333cd0c9e5ba6d478b73` para `airaware.py` y `894bba3e140e6162c566eb0b868ffe0d68d0208ff74df521b1822157cdae69db` para `gpu_worker.py`. [Configuración de memoria](https://github.com/keneth-arias/ml-infra/pull/5)

El manifiesto identifica los dos estados finales, sus predicciones y la tabla pareada mediante SHA-256. El archivo de métricas incluye también el cruce de estación y horizonte y el número de horas de estación distintas de cada grupo. [Manifiesto de congelación](../../metadata/validacion-pm25-pm10-congelacion.json) · [Métricas completas](../../metadata/validacion-pm25-pm10-metricas.json)
