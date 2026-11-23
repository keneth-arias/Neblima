# Pronóstico web Gemma 3 1B

La captura conserva el reloj publicado de SENAMHI y exporta solo historias completas de 24 horas. El predictor usa el checkpoint de la semilla 27 en el paso 4500 y el corrector de picos congelado antes de exportar los seis valores puntuales por origen. Los modelos históricos y la CNN conservan su identidad en las comparaciones.

`refresh.py capture DIRECTORIO` consulta como máximo doce gráficos de SENAMHI
con Lightpanda (45 segundos y 1 MB por consulta). Verifica nombre, contaminante,
fechas, valores y duplicados. Conserva cada original y su recibo. Una ventana
usa un solo código de estación; no une instrumentos ni imputa datos.
El origen común es la última lectura publicada. Si todas tienen más de seis
horas de retraso respecto del reloj de referencia de Lima, falla y conserva
la versión pública anterior. Las estaciones sin captura quedan sin lectura.

`refresh.py predict DIRECTORIO` restaura Gemma en una GPU local con los pesos y la generación seleccionada de solo lectura.
`refresh.py correct DIRECTORIO` aplica la corrección congelada en CPU y verifica las huellas del checkpoint, las historias y la corrección.
`refresh.py export DIRECTORIO` comprueba identificadores, seis horizontes,
dimensiones y valores finitos antes de escribir `actual.json`.

El archivo usa `schema_version: 2`, `clock: provider_wall_clock`,
`generated_at_utc`, `source_revision`, `model`, `timeline` y `stations`.
Cada estación tiene recibos, código elegido, última lectura y ocho ventanas
alineadas con `timeline`. Cada ventana separa `history` (24), `observed` (6),
`forecast` (6 o `null`), `origin` y `target_times`. No se asigna UTC a las
etiquetas del gráfico: SENAMHI no declara el desfase. Solo las horas de
captura y cálculo son UTC. La web conserva las fechas publicadas, incluidos
los cambios de día, y acredita a SENAMHI bajo ODC-BY 1.0.

Pruebas sin red desde la raíz:

```sh
uv run --project tools/timenet-smoke --locked python -m unittest discover -s tools/web-refresh -p 'test_*.py'
uv run --locked ruff check tools/web-refresh
uv run --locked ruff format --check tools/web-refresh
make check
make build
make audit
```

La ejecución pertenece a MicroK8s en `bm`. El renderizador y la publicación
en `qriqs/airaware-web` están en `ml-infra/workloads/web-refresh/`.
La variable `NOT_BEFORE=2026-11-23T14:00:00Z` impide consultas programadas
antes del 23 de noviembre a las 09:00 en `America/Lima`. Una ejecución manual
sin esa variable permite validar una actualización inmediata.
