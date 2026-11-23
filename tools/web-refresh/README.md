# Datos públicos de la web

La actualización usa la CNN pública congelada de AirAware, con 24 lecturas
horarias y seis salidas. Los pesos deben tener SHA-256
`9ceb6dcd793f661720fd58606992581857993f66109dc3024480e164316b7315`.
Los pesos, originales y credenciales se mantienen fuera de Git.

`refresh.py capture DIRECTORIO` consulta como máximo doce gráficos de SENAMHI
con Lightpanda (45 segundos y 1 MB por consulta). Verifica nombre, contaminante,
fechas, valores y duplicados. Conserva cada original y su recibo. Una ventana
usa un solo código de estación; no une instrumentos ni imputa datos.
El origen común es la última lectura publicada. Si todas tienen más de seis
horas de retraso respecto del reloj de referencia de Lima, falla y conserva
la versión pública anterior. Las estaciones sin captura quedan sin lectura.

`refresh.py predict DIRECTORIO` restaura la CNN en CPU y verifica los pesos.
Requiere `compare_cnn.py` en `PYTHONPATH` y `/model/model.pt` de solo lectura.
`refresh.py export DIRECTORIO` comprueba identificadores, seis horizontes,
dimensiones y valores finitos antes de escribir `actual.json`.

El archivo usa `schema_version: 1`, `clock: provider_wall_clock`,
`generated_at_utc`, `source_revision`, `model`, `timeline` y `stations`.
Cada estación tiene recibos, código elegido, última lectura y ocho ventanas
alineadas con `timeline`. Cada ventana separa `history` (24), `observed` (6),
`forecast` (6 o `null`), `origin` y `target_times`. No se asigna UTC a las
etiquetas del gráfico: SENAMHI no declara el desfase. Solo las horas de
captura y cálculo son UTC. La web conserva las fechas publicadas, incluidos
los cambios de día, y acredita a SENAMHI bajo ODC-BY 1.0.

Pruebas sin red desde la raíz:

```sh
uv run --locked python -m unittest discover -s tools/web-refresh -p 'test_*.py'
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
