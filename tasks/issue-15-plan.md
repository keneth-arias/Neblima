# #15 · Grilla horaria SENAMHI y máscaras de datos faltantes

La grilla consume el Parquet de auditoría de [#73](issue-14-plan.md). Usa las etiquetas
publicadas en tiempo universal coordinado (UTC) conforme al
[ADR-005](../docs/decisions/005-senamhi-operating-policy.md).

```bash
uv run --locked airaware align senamhi \
  --input data/curated/senamhi-lima-audit.parquet \
  --output data/curated/senamhi-lima-hourly
```

El comando publica `hours.parquet` y `manifest.json` en una carpeta nueva. El manifiesto
contiene las sumas SHA-256 de la auditoría y la grilla y los conteos por estación, señal y
estado. Cada `series_id` depende de la identidad provisional de estación, el instrumento,
el parámetro original, el parámetro interpretado y la unidad. El comando usa observaciones
horarias de SENAMHI sin extremos de intervalo documentados. La grilla empieza y termina
en las horas publicadas de cada serie, inclusive.

| Estado | Valor en la grilla | Procedencia |
| --- | --- | --- |
| `observed` | Medición conservada, incluido el cero | Identificador seleccionado y lista de identificadores de la hora en la auditoría |
| `unusable_value` | Nulo | Había al menos una fila publicada, con valor no utilizable |
| `conflict` | Nulo | Identificadores de las lecturas en conflicto |
| `absent_hour` | Nulo | Lista vacía, sin fila para esa hora |

`is_missing` indica falta de un valor utilizable. `is_imputed` es falso para toda la grilla.
Se conservan `available_at` y `quality` del registro seleccionado. En la exportación real
la disponibilidad sigue desconocida y la calidad de las mediciones permanece `unknown`.

## Validación y entrega a #18

Se ejecutó el comando dos veces con la auditoría de SHA-256
`86170e033b81bd6b53fdf0b044df3df36243ae2c4819a41821ecb839c13ee661`.
Los manifiestos y los Parquet coincidieron byte a byte. SHA-256 de la grilla
`2e8fa784cea645b8eb97b42f3fe36e6c532b5959cc8ae66da0ea416df513413c`.

Las siete identidades de PM2.5 suman 577 717 horas. Hay 367 518 con valor, 20 horas en
conflicto, 210 172 con filas pero sin valor utilizable y siete horas sin fila. Las 70
lecturas en conflicto de la auditoría corresponden a esas 20 horas. Los conteos por estación
y señal quedan en el manifiesto local.

El constructor de #18 puede verificar la suma del Parquet contra el manifiesto, ordenar
las observaciones por `series_id` y `observed_at`, y exigir todos los valores de la
historia y del objetivo dentro de la misma serie.

`make check` aprobó 342 pruebas. La prueba nueva cubre el cero, la repetición con dato
ausente, el conflicto, el hueco, un intervalo incompatible y un instrumento independiente.
`make build` generó el paquete fuente y la rueda. `make audit` reportó cero vulnerabilidades
conocidas.
