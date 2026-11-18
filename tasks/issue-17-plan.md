# #17 · Alinear meteorología y contaminación sin información futura

Estado: **entregada para revisión** (PR interno; no se fusiona). Primera entrega pequeña y
acotada: conversión determinista del pronóstico archivado GFS `temperature_2m_previous_day1`
(muestra fijada por #16), unión validada por manifiestos a las ventanas y particiones
congeladas de PM2.5 por `window_id`, política temporal sin información futura probada con
datos sintéticos, y evidencia real sin red. Esta entrega **no** reescribe ventanas, objetivos,
cortes, purgas, artefactos TimeF ni métricas de referencia; **no** afirma mejoras de desempeño
ni disponibilidad operativa estricta.

## Alcance real entregado

1. `src/airaware/weather_alignment.py`: conversión de los paquetes Open-Meteo
   `open-meteo-previous-model-runs` ya adquiridos en filas horarias con procedencia
   (`issued_at` = `valid_at` − 24 h por el adelanto nominal `previous_day1` documentado;
   `available_at` nulo porque el proveedor no documenta disponibilidad horaria; el
   `acquired_at` local nunca lo sustituye), identidad de estación separada de la identidad de
   celda, coordenadas solicitadas y celda devuelta con elevación, distancia haversine
   aproximada con CRS sin declarar, clase de producto, unidad, hash del original y estado por
   valor. Unión DuckDB por `window_id` contra la cadena congelada grilla→ventanas→particiones
   (versiones y SHA-256 verificados), con admisión temporal por origen de ventana y máscara
   explícita por hora; resumen por ventana que nunca descarta ventanas por falta de clima; y
   paridad de configuraciones (`pm25_only` vs `pm25_gfs_previous_day1`) con el mismo conjunto
   de `window_id` elegibles y objetivos intactos.
2. `configs/weather-alignment.yaml`: dos configuraciones explícitas y separadas; referencia
   de la política vigente `configs/benchmark.yaml` (comparison-v3, sin claves nuevas allí);
   siete identidades provisionales de #14 con coordenadas originales y CRS sin declarar.
3. `src/airaware/cli.py`: registro mínimo del comando `airaware align weather`.
4. `tests/test_weather_alignment.py`: 14 pruebas enfocadas, todas sintéticas y sin red.
5. `reports/alignment/weather-gfs-previous-day1.md`: evidencia real de la muestra GFS sin red.
6. `DATA_ATTRIBUTION.md`: atribución Open-Meteo/GFS comprometida por la documentación de #16.

Fuera de alcance (explícito): ERA5, NOAA ISD, OEFA y SENAMHI GBON quedan excluidos de la
variante inicial; sin entrenamiento ni métricas nuevas; sin TimeNet; sin publicar datos.

## Contrato temporal implementado y probado

- Rechazo de `issued_at > origin_at`; rechazo de `available_at > origin_at` aunque el
  instante válido sea anterior; igualdad exacta en el origen admitida.
- El clima con `valid_at > origin_at` solo es admisible como pronóstico (rol
  `target_forecast`); la variable realizada `temperature_2m` queda excluida.
- Faltantes nulos con estado y máscara por hora y por ventana; sin cero, sin relleno y sin
  interpolación; no se descarta ninguna ventana por falta de clima.
- Las dos configuraciones exponen exactamente el mismo conjunto de `window_id` elegibles y
  objetivos idénticos (huellas SHA-256 en el manifiesto).

## Comandos ejecutados y resultados

```bash
uv run --locked pytest                                # 361 pruebas OK (14 nuevas de #17)
uv run --locked ruff format --check src tests && uv run --locked ruff check src tests
uv run --locked ty check src tests
uv run --locked airaware catalog validate             # 40 fuentes, OK
uv run --locked airaware align weather --config configs/weather-alignment.yaml \
  --data-dir data --output data/alignment/gfs-prevday1-run1     # exit 0
UV_OFFLINE=true uv run --locked airaware align weather --config configs/weather-alignment.yaml \
  --data-dir data --output data/alignment/gfs-prevday1-run2     # exit 0, sin red
```

Conciliación real (detalle en el informe): 7/7 coordenadas mapeadas; 1176 filas = 7 × 168
marcas (2022-03-09T00:00Z a 2022-03-15T23:00Z); 0 faltantes; determinismo exacto entre
corridas (Parquet lógico y `manifest.json` byte a byte); hashes de los 7 originales
re-verificados antes y después, sin cambios y sin descargas nuevas.

## Limitaciones declaradas

1. Experimento retrospectivo por tiempo de emisión: `issued_at` se deriva del adelanto
   nominal `previous_day1` y **no prueba disponibilidad operativa estricta**;
   `available_at` permanece nulo (no documentado por hora).
2. CRS de las coordenadas SENAMHI sin declarar: distancias haversine aproximadas, sin
   equivalencia estación–celda; las celdas compartidas no son observaciones independientes.
3. La muestra GFS cubre solo la semana fijada por #16 dentro de `train`; toda ventana fuera
   de esa semana queda con clima faltante explícito (nulo y contado, nunca imputado).
4. Las ventanas y particiones congeladas reales no estaban presentes en este entorno
   (`data/benchmarks`, `data/timef` y `data/curated` vacíos; el original SENAMHI ya no está
   bajo `data/raw`): la unión se ejercitó de extremo a extremo con ventanas sintéticas
   construidas con los comandos reales `benchmark windows` y `benchmark split`, y la muestra
   real se verificó en la conversión. Ninguna descarga fue autorizada ni necesaria.

## Rutas

| Producto | Ruta |
| --- | --- |
| Módulo de conversión y unión | `src/airaware/weather_alignment.py` |
| Configuración de las dos variantes | `configs/weather-alignment.yaml` |
| Pruebas enfocadas | `tests/test_weather_alignment.py` |
| Informe de evidencia real | `reports/alignment/weather-gfs-previous-day1.md` |
| Atribución Open-Meteo/GFS | `DATA_ATTRIBUTION.md` |
