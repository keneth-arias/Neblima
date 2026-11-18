# #19 · Particiones cronológicas y purga de fronteras

La partición usa los orígenes de [las ventanas completas de #18](issue-18-plan.md) en
tiempo universal coordinado (UTC). Lee la grilla de #15 para comprobar los tiempos de
publicación disponibles. Verifica ambos archivos contra sus manifiestos y verifica
que las ventanas se construyeron sobre esa misma grilla.

```bash
uv run --locked airaware benchmark split \
  --input data/benchmarks/lima-pm25-h24-f6 \
  --timeline data/curated/senamhi-lima-hourly \
  --output data/benchmarks/lima-pm25-h24-f6-splits
```

Los cortes son los percentiles discretos 70 y 85 de los orígenes de todas las ventanas
completas. Comparten las mismas fechas todas las estaciones. Cada ventana conserva
su identificador y se asigna a entrenamiento, validación o prueba si el intervalo
completo desde la primera hora de historia hasta el último objetivo cae en un solo bloque.
La hora de un corte pertenece al bloque siguiente. Las ventanas que cruzan un corte
se conservan como `purged` con su motivo en el Parquet de salida.

El origen de emisión en esta evaluación es la última hora de historia. Se excluye una
ventana si alguna hora de la historia tiene una fecha documentada de publicación
posterior a ese origen. Bajo ADR-005 se conservan las observaciones retrospectivas de
publicación desconocida. El modelo debe ajustar cualquier transformación solo con
`train`, elegir configuración con `validation` y reservar `test` para la evaluación
final. La versión actual contiene únicamente la señal medida de PM2.5 en Lima.

## Resultado real

| Partición | Ventanas | Proporción entre las asignadas |
| --- | ---: | ---: |
| Entrenamiento | 237 397 | 70,05 % |
| Validación | 50 706 | 14,96 % |
| Prueba | 50 789 | 14,99 % |
| Purga | 313 | — |

Validación empieza el 16/03/2022 a las 08:00 UTC. Prueba empieza el 25/02/2023
a las 18:00 UTC. Las tres particiones contienen las siete identidades. La comprobación
sobre el Parquet completo encontró cero pares de particiones con intervalos superpuestos
para una misma serie. Se conciliaron las 339 205 ventanas de #18 y todas las purgas reales
fueron por cruce de corte.

Dos ejecuciones produjeron Parquet y manifiestos idénticos. El SHA-256 del Parquet es
`a02e001795bf84985c087766ee46ea7acc53d86e5d2ed96b0974a5c6fd62502d`.
`make check` pasó con 345 pruebas. La prueba de particiones incluye retrasos de publicación
respecto del origen y cruces de frontera. `make build` y `make audit` aprobaron.
