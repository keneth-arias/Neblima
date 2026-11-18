# Alineación GFS `previous_day1` con ventanas de PM2.5 — evidencia real sin red (#17)

Informe de ejecución real de la conversión y verificación de la muestra fijada por #16. **No
hay descargas nuevas ni consultas a proveedores**; los originales se leyeron desde los
paquetes locales verificados por SHA-256. La unión a ventanas congeladas se ejercitó de
extremo a extremo con datos sintéticos construidos con los comandos reales del proyecto
(`benchmark windows`, `benchmark split`); las ventanas congeladas reales no estaban presentes
en este entorno (véanse las limitaciones).

## Ejecución

Directorio: raíz del worktree de `feat/issue-17-weather-alignment` (base
`74c8ae38811dd6d23ff84126bd5fa1dae01dc20c`). Los 7 paquetes GFS del checkout raíz se copiaron
byte a byte a `data/raw/open-meteo-previous-model-runs/` (ignorado por Git) tras verificar sus
SHA-256 contra `configs/acquisition/weather-lima-sample-plan.json`; los originales del checkout
raíz permanecieron intactos y se re-verificaron después de las corridas.

| # | Comando | Resultado |
| --- | --- | --- |
| 1 | `uv run --locked airaware align weather --config configs/weather-alignment.yaml --data-dir data --output data/alignment/gfs-prevday1-run1` | **exit 0** |
| 2 | `UV_OFFLINE=true uv run --locked airaware align weather --config configs/weather-alignment.yaml --data-dir data --output data/alignment/gfs-prevday1-run2` | **exit 0**; sin red |
| 3 | Comparación de corridas | `weather_rows.parquet` lógicamente idéntico (`Table.equals` verdadero) y `manifest.json` byte a byte idéntico |
| 4 | `sha256sum` de los 7 originales antes y después (worktree y checkout raíz) | 7/7 sin cambios |

## Conciliación de la muestra real

- **Filas**: 1176 = 7 estaciones × 168 marcas horarias
  (2022-03-09T00:00Z a 2022-03-15T23:00Z), sin duplicados por estación.
- **Mapeos**: 7/7 coordenadas solicitadas conciliadas con recursos del plan; 0 estaciones sin
  recurso; 0 recursos de otra procedencia.
- **Valores**: 0 faltantes en `temperature_2m_previous_day1` (unidad °C declarada por el
  proveedor y verificada contra la configuración); rango observado 20,8–29,7 °C.
- **Razones de rechazo en conversión**: 0 (la política temporal se evalúa en la unión y está
  probada con sintéticos: rechazo por emisión tardía, por publicación tardía, igualdad
  admitida en el borde y clima futuro solo como pronóstico).
- **Semántica temporal**: `issued_at` = `valid_at` − 24 h (2022-03-08T00:00Z a
  2022-03-14T23:00Z); adelanto nominal uniforme de 24 h; `available_at` nulo;
  `acquired_at` (2026-11-17T23:41:45–48Z) registrado solo como procedencia local.
- **Distancias haversine aproximadas** solicitado→celda devuelta: **2,48–10,041 km**
  (CRS de las coordenadas SENAMHI sin declarar; aproximación geográfica, sin equivalencia).

## Celdas de grilla: lo que dicen los bytes

Los 7 paquetes concilian **4 celdas (lat, lon) distintas** — no un mapeo uno a uno — y las
celdas compartidas quedan visibles con sus estaciones:

| Celda devuelta (lat, lon) | Estaciones que comparten la celda |
| --- | --- |
| (−12.124954, −76.99219) | SAN_BORJA, CAMPO_DE_MARTE |
| (−12.124954, −76.875) | VILLA_MARIA_DEL_TRIUNFO |
| (−12.007805, −76.99219) | SAN_JUAN_DE_LURIGANCHO, SANTA_ANITA, SAN_MARTIN_DE_PORRES |
| (−11.8906555, −76.99219) | CARABAYLLO |

Esto concilia fila por fila con el recibo de #16 (`metadata/weather-acquisition.json`, una
celda por estación). La frase «3 columnas de grilla» del informe de #16 agrupa las celdas de
longitud compartida −76.99219 (3 latitudes distintas); su propia tabla ya registraba la celda
−76.875 de VILLA_MARIA_DEL_TRIUNFO. Este informe conserva ambos hechos sin reetiquetar #16.

- Espaciamiento mínimo observado entre celdas: **0,117149° de latitud** y **0,11719° de
  longitud**. Resolución declarada por el proveedor: no declarada en la respuesta → **nula**
  (no se inventa); las elevaciones devueltas difieren por estación dentro de una celda
  compartida (ajuste del DEM del proveedor; no prueba celdas independientes).

## Paridad de configuraciones (sintética, cadena real)

Con la cadena real grilla→ventanas→particiones sobre datos sintéticos de dos estaciones, el
manifiesto de unión registra `identical_window_id_set: true`, la igualdad de huellas SHA-256
del conjunto de `window_id` (total y elegible, splits vs resumen) y la huella de objetivos
elegibles compartida por ambas configuraciones. Las ventanas con clima faltante permanecen con
estado `missing`/`partial` y conteos explícitos; ninguna se descarta.

## Limitaciones

1. Experimento retrospectivo por tiempo de emisión; **no prueba disponibilidad operativa
   estricta** (`available_at` no documentado por hora por el proveedor).
2. Las ventanas/particiones congeladas reales no estaban presentes en este entorno
   (`data/benchmarks`, `data/timef`, `data/curated` vacíos; el original SENAMHI ya no está
   bajo `data/raw`): sin ventanas reales no se ejecutó una unión real ni se calcularon
   métricas; tampoco se afirma mejora de desempeño alguna.
3. La muestra cubre una semana de 2022 dentro de `train`; toda ventana fuera de esa semana
   queda con clima faltante explícito.
4. CRS SENAMHI sin declarar: distancias aproximadas; celdas compartidas no son observaciones
   independientes ni mediciones en la estación de aire.
