# Procedencia de las ventanas de PM2.5 de Lima

El 20 de noviembre de 2026 se reconstruyeron la grilla horaria de #18 y las particiones de #25 desde el CSV histórico de SENAMHI aprobado en el ADR-005. Las huellas de la grilla y las particiones coincidieron con las del ejemplo Qwen de #25. Para cada fila de los índices del experimento de seis horas se verificaron ID, estación, hora UTC y partición original. El cotejo incluyó la purga de la repetición y exigió una correspondencia uno a uno en ambos sentidos. Solo se leyeron índices y metadatos para hacer el cotejo. [Procedencia del ejemplo de #25](../../metadata/qwen-smoke.json)

| Bloque del experimento H24/F6 | Ventanas con serie de origen identificada |
| --- | ---: |
| Entrenamiento | 237 397 |
| Calibración | 25 201 |
| Selección | 25 305 |
| Prueba histórica de #28 | 50 789 |
| Purga entre calibración y selección | 200 |
| Total | 338 892 |

Las siete series recuperadas tienen una estación provisional y un identificador de serie. El campo de instrumento físico (`sensor_id`) está vacío en las siete. El CSV aporta el contexto de estación y la política de normalización conserva el instrumento como desconocido. Identificar cambios de equipo o vincular estos instrumentos con una estación operativa requiere documentación de la fuente. [Conteos por estación, serie y bloque](../../metadata/procedencia-episodios-h6-v1.json) · [Política histórica](../../docs/decisions/005-senamhi-operating-policy.md)

También se ejecutó el adaptador de #20 con los controles de #113 sobre las 324 463 ventanas históricas H24/F24. Las siete series conciliaron las ventanas completas y las descartadas. Se comprobaron 7 787 112 posiciones objetivo contando solapamientos. Hubo cero violaciones de límites, cero IDs compartidos entre la historia y el objetivo de una ventana y cero columnas derivadas de etiquetas en las entradas. La calidad individual registrada sigue siendo `unknown` y la posición del intervalo continúa indocumentada. El adaptador emitió un informe de compatibilidad con cero etiquetas. [Resultado por serie](../../metadata/issue-20-verificacion-antifuga.json)

## Reproducción

Desde la raíz de AirAware, definir `RAW` como la ruta del CSV aprobado y `BLOCKS` como la carpeta `blocks` de la repetición histórica. El normalizador verifica el SHA-256 del original. El auditor H24/F6 verifica las huellas congeladas de las particiones, la grilla y cada índice antes de cruzarlos. [Preparación de los bloques](intervalos-pm25-replay.md)

```sh
set -eu
D=$(mktemp -d)
uv run --locked airaware normalize senamhi --input "$RAW" --output "$D/normalized"
uv run --locked airaware curate senamhi --input "$D/normalized" --output "$D/audit.parquet"
uv run --locked airaware align senamhi --input "$D/audit.parquet" --output "$D/timeline"
for h in 6 24; do
    uv run --locked airaware benchmark windows --input "$D/timeline" --output "$D/windows-$h" --history 24 --horizon "$h" --step 1
done
uv run --locked airaware benchmark split --input "$D/windows-6" --timeline "$D/timeline" --output "$D/splits-6"
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/episode_source_audit.py "$BLOCKS" "$D/splits-6/splits.parquet" "$D/timeline/hours.parquet" > "$D/trace.json"
cmp "$D/trace.json" metadata/procedencia-episodios-h6-v1.json
uv run --locked airaware labels senamhi --timeline "$D/timeline" --windows "$D/windows-24" --output "$D/labels-24"
cmp "$D/labels-24/compatibility.json" metadata/issue-20-verificacion-antifuga.json
```
