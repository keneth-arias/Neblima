# #22 · Conjunto TimeF de pronóstico de PM2.5 de Lima

El exportador toma la auditoría SENAMHI, la [grilla](issue-15-plan.md) y las
[particiones congeladas](issue-19-plan.md). Comprueba los manifiestos de grilla y
particiones, sus vínculos SHA-256 con la auditoría y el original aprobado. No ejecuta
descargas. La conversión usa la revisión fijada de TimeNet 0.12.0 y se ejecuta con las
dependencias instaladas del entorno [timenet-smoke](../tools/timenet-smoke/README.md).

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked \
  python tools/timenet-smoke/export_benchmark.py \
  --timeline data/curated/senamhi-lima-hourly \
  --splits data/benchmarks/lima-pm25-h24-f6-splits \
  --audit data/curated/senamhi-lima-audit.parquet \
  --registry data/timef --version 0.1.0
```

La versión local completa es `airaware/lima-pm25-forecast@0.1.0`. Cada
`ForecastingTask` recibe un registro propio con las 24 horas de historia, la última
como origen. Sus seis objetivos escalares corresponden a las seis horas consecutivas
siguientes. Los metadatos de tarea conservan `window_id`, `series_id`, el origen y la
primera hora futura. El registro de entrada lleva el identificador provisional y los
hashes de auditoría, grilla y particiones. La unidad en µg/m³ sigue siendo inferida.

La versión se puede leer sin un padre TimeF porque materializa únicamente los rangos
de entrada por tarea. Su referencia de origen es el SHA-256 del original, y la procedencia
registra los hashes exactos de los artefactos intermedios. La base #21 conserva su
identificador y versión de muestra. La licencia de la serie sigue siendo ODC-By-1.0
con la atribución de SENAMHI incluida.

## Validación y entregas a #23 y #25

Las 338 892 tareas del conjunto completo equivalen a 237 397 de entrenamiento, 50 706
de validación y 50 789 de prueba. Se excluyeron las 313 ventanas purgadas. La comparación
con el Parquet congelado verificó todos los `window_id`, sus particiones y los seis
objetivos. Se releyó con `TimeFReader` una historia por partición y se comparó con su
grilla. El escritor completo tardó 63,09 s y usó hasta 3 246 820 KiB de memoria residente
en el equipo de verificación.

Para pruebas, `--limit-per-station-split 128` selecciona el primer origen de cada bloque
ordenado de tamaño similar dentro de estación y partición. Guarda una versión de muestra
con nombre distinto. Su carga mediante `LocalRegistry` devolvió 2688 tareas. El modo
`--synthetic` etiqueta las pruebas ficticias con otro nombre y licencia de origen sin
especificar. El candidato de evaluación para #25 es el conjunto completo.

Cada versión debe pasar `TimeFReader.verify()`. La repetibilidad se evalúa sobre las
tablas Arrow de tareas y objetivos y las sumas de los archivos de valores. TimeNet
puede generar otra suma para el archivo interno de control DuckDB y su manifiesto.
El comando de arriba reproduce el conjunto desde exactamente los artefactos identificados
en la [grilla](issue-15-plan.md) y las [particiones](issue-19-plan.md).

`make check` pasó con 345 pruebas. También pasaron `make build`, `make audit` y las
tres pruebas del entorno TimeF ejecutadas con `UV_OFFLINE=true`.

Las dos ejecuciones completas produjeron tablas Arrow y archivos de valores idénticos.
Las sumas de los manifiestos fueron
`29135340efb377a59d695e05fb6f8848fd0e56481123f5b54e987da77e9adc97` y
`7db97691e46d552423b7e47fee013f2f56294ebe9c99ab75438fe54f563034ad`.
Se verificó una copia de la primera versión completa en el registro local `data/timef`.
