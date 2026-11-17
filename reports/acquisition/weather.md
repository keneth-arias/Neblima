# Adquisición meteorológica de Lima — ejecución y reconciliación real (#16)

Informe de ejecución real de la muestra de #16. La transferencia en vivo de los 14 recursos
Open-Meteo ocurrió en el intento previo (`acquired_at` **2026-11-17T23:41:45–48Z**, registrado en
los manifiestos bajo `data/raw/`); la contabilidad exacta de bytes de red de esa consola no es
recuperable y **no se inventa**. La continuación (attempt-02) verificó esos originales desde
disco, intentó la única adquisición NOAA autorizada, ejecutó la reutilización sin red y produjo
el recibo [metadata/weather-acquisition.json](../../metadata/weather-acquisition.json).
La comparación de fuentes está en [docs/sources/weather.md](../sources/weather.md) y el plan en
[tasks/issue-16-plan.md](../tasks/issue-16-plan.md).

## Resultado en una línea

Muestra de reanálisis (ERA5, 7 coordenadas) y de pronóstico archivado (GFS `previous_day1`,
7 coordenadas) adquirida, verificada y reconciliada: **14 recursos, 102 337 bytes publicados,
todos los SHA-256 coinciden, 0 valores faltantes** en las variables muestreadas. La ruta de
medición de estación (NOAA ISD) queda **bloqueada** con evidencia exacta; ninguna observación
medida fue descargada.

## Comandos ejecutados en esta continuación (con exit codes)

Registrados desde la raíz del repositorio (`/home/cristopher/github/airaware`, rama
`feat/issue-16-weather-sample`). Los artefactos Open-Meteo NO se solicitaron en línea de nuevo.

| # | Comando / acción | Resultado |
| --- | --- | --- |
| 1 | `uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json --source noaa-isd-global-hourly --budget-bytes 4194304 --allow-host www.ncei.noaa.gov --workers 1 --deadline-seconds 60` | **exit 1**; `errors: [{source_id: noaa-isd-global-hourly, error: "No se pudo completar o verificar el recurso"}]`, `network_bytes: 0`; sin escritura en disco |
| 2 | Diagnóstico por la misma ruta (`fetch_public_file`, mismos techos: presupuesto 4 194 304, plazo 60 s) para obtener el error exacto que el lote enmascara | `AcquisitionError`: **«Recurso público respondió HTTP 301; transferencia detenida»** |
| 3 | Diagnóstico solo-cabeceras (HEAD, sin carga) a la URL planificada | **301**; `location: https://noaa-global-hourly-pds.s3.amazonaws.com/index.html` |
| 4 | Diagnóstico solo-cabeceras (HEAD) al recurso equivalente en la ubicación canónica NODD | **200**; `content-length: 4382554`; `etag: "1776345dd1a99dfe8300e11bdf803a1b"`; `last-modified: 2023-07-30T08:45:24Z`; `accept-ranges: bytes` |
| 5 | `uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json --source open-meteo-historical-weather --offline --budget-bytes 0` | **exit 0**; `completed: 7` (`reused: true` en todos), `errors: []`, `network_bytes: 0` |
| 6 | `uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json --source open-meteo-previous-model-runs --offline --budget-bytes 0` | **exit 0**; `completed: 7` (`reused: true`), `errors: []`, `network_bytes: 0` |
| 7 | Conciliación local determinista (lectura de los 14 originales + manifiestos; recálculo SHA-256, tamaños, estadísticas por variable, corte de 168 h) | `ALL_HASHES_MATCH: True`; `TOTAL_PUBLISHED_BYTES: 102337`; recibo escrito |

Los comandos en vivo del intento previo (mismo plan, lote de 15 recursos con
`--budget-bytes 5570560 --workers 1 --deadline-seconds 60` y los hosts autorizados) ejecutaron
solo los 14 recursos Open-Meteo; su salida de consola exacta no es recuperable de la
interrupción y no se reproduce de memoria.

## Verificación de integridad y bytes publicados (R4)

Recalculados ahora desde disco; coincide con la verificación independiente del gerente:

| Fuente | Recursos | Bytes originales publicados | SHA-256 | Ventana solicitada (UTC) | Marcas por recurso |
| --- | --- | --- | --- | --- | --- |
| `open-meteo-historical-weather` (ERA5, `models=era5`) | 7 | 65 867 | 7/7 coinciden | 2015-04-16 a 2015-04-23 | 192 horarias |
| `open-meteo-previous-model-runs` (GFS, `models=gfs_seamless`) | 7 | 36 470 | 7/7 coinciden | 2022-03-09 a 2022-03-15 | 168 horarias |
| **Total** | **14** | **102 337** | 14/14 | — | — |

Manifiestos con `http_status: 200`, `attempts: 1`, `validation: structure_only` y
`acquired_at`/`verified_at` locales (2026-11-17T23:41:45–48Z). Los originales permanecen bajo
`data/raw/` (ignorado por Git): **ningún dato masivo entra al repositorio**; en Git solo entran
plan, documentación, recibos y este informe. `NOAA`: 0 recursos y 0 bytes publicados.

## Reconciliación por estación (R2, R5)

Siete identidades provisionales SENAMHI PM2.5 (derivadas con la regla #14; detalle en el plan).
Cada estación recibió su propia solicitud con sus coordenadas originales sin redondear.
Variables ERA5 (unidades declaradas en las respuestas): `temperature_2m` °C,
`relative_humidity_2m` %, `precipitation` mm, `surface_pressure` hPa, `wind_speed_10m` km/h,
`wind_direction_10m` °. GFS: `temperature_2m` °C y `temperature_2m_previous_day1` °C.

| Estación | Solicitado (lat, lon) | Celda devuelta ERA5 (lat, lon, elev m) | Celda devuelta GFS (lat, lon, elev m) | Marcas ERA5 | Marcas GFS |
| --- | --- | --- | --- | --- | --- |
| CAMPO_DE_MARTE | (-12.0705, -77.0432) | (-12.0, -77.0, 123) | (-12.124954, -76.99219, 123) | 192, 0 faltantes | 168, 0 faltantes |
| CARABAYLLO | (-11.9022, -77.0336) | (-12.0, -77.0, 179) | (-11.8906555, -76.99219, 179) | 192, 0 faltantes | 168, 0 faltantes |
| SANTA_ANITA | (-12.043, -76.9714) | (-12.0, -77.0, 256) | (-12.007805, -76.99219, 256) | 192, 0 faltantes | 168, 0 faltantes |
| SAN_BORJA | (-12.1086, -77.0077) | (-12.0, -77.0, 130) | (-12.124954, -76.99219, 130) | 192, 0 faltantes | 168, 0 faltantes |
| SAN_JUAN_DE_LURIGANCHO | (-11.9816, -76.9992) | (-12.0, -77.0, 237) | (-12.007805, -76.99219, 237) | 192, 0 faltantes | 168, 0 faltantes |
| SAN_MARTIN_DE_PORRES | (-12.0089, -77.0845) | (-12.0, -77.0, 54) | (-12.007805, -76.99219, 54) | 192, 0 faltantes | 168, 0 faltantes |
| VILLA_MARIA_DEL_TRIUNFO | (-12.1664, -76.92) | (-12.0, -77.0, 272) | (-12.124954, -76.875, 272) | 192, 0 faltantes | 168, 0 faltantes |

Sin marcas duplicadas en ninguna serie (`time` sin repetidos). Conteos finitos/faltantes por
variable: ERA5, 6 variables × 192 valores finitos por estación (0 faltantes); GFS, 2 variables ×
168 valores finitos por estación (0 faltantes). Detalle completo y SHA-256 por recurso en
[metadata/weather-acquisition.json](../../metadata/weather-acquisition.json).

### Identidad de celda: siete solicitudes NO son siete celdas

- **ERA5: todas las siete respuestas devuelven la misma celda redondeada (-12.0, -77.0)**.
  Son un único valor de reanálisis compartido, no siete observaciones independientes. La
  `elevation` distinta por respuesta (54–272 m) es coherente con una consulta de modelo digital
  de elevación en la coordenada solicitada, no con celdas distintas; NO se interpreta como
  siete celdas. Resolución ERA5 declarada 0,25° (~25 km), mucho mayor que la extensión urbana
  de las siete estaciones.
- **GFS: las siete respuestas colapsan en 3 columnas de grilla distintas**:
  (-12.124954, -76.99219) para CAMPO_DE_MARTE/SAN_BORJA/VILLA_MARIA_DEL_TRIUNFO;
  (-12.007805, -76.99219) para SANTA_ANITA/SAN_JUAN_DE_LURIGANCHO/SAN_MARTIN_DE_PORRES;
  (-11.8906555, -76.99219) para CARABAYLLO. La resolución efectiva observada entre columnas es
  ~0.12° de longitud y ~0.10°–0.13° de latitud. Las `elevation` coinciden con las de ERA5 por
  estación (misma observación de DEM, no prueba de celdas independientes).

### Corte del intervalo seleccionado de 168 h (ERA5)

Ventana solicitada al proveedor: 8 días completos (192 marcas). El corte local determinista al
intervalo fijado antes de solicitar datos — **2015-04-16T18:00Z a 2015-04-23T17:00Z inclusive,
168 horas** — da exactamente **168 marcas por estación y 168 valores finitos por variable**
(0 faltantes), con primera/última marca exactas en las siete estaciones. El corte se hace en la
reconciliación local; el proveedor nunca recorta filas.

## Clases separadas y semántica temporal (R3)

- **Reanálisis** (`open-meteo-historical-weather`/ERA5): marca horaria UTC (`GMT`,
  `utc_offset_seconds: 0`), ventana 2015-04-16T00:00 a 2015-04-23T23:00. No es medición de
  estación ni pronóstico. Latencia de publicación declarada por Open-Meteo: ~5 días para ERA5.
- **Pronóstico archivado** (`open-meteo-previous-model-runs`/GFS): tiempo válido = marca horaria
  (2022-03-09T00:00 a 2022-03-15T23:00 UTC); **hora de emisión de `temperature_2m_previous_day1`
  = tiempo válido − 24 h** (semántica declarada por la documentación de la API; primera emisión
  de la muestra: 2022-03-08T00:00Z para la primera marca válida). Archivo GFS declarado desde
  03/2021 para temperatura 2 m. No es reanálisis ni medición.
- **Medición de estación** (NOAA ISD): **sin datos adquiridos**; ver bloqueo abajo.
- `available_at` del proveedor por hora no está documentado en ninguna de las dos API muestreadas
  y queda como desconocido; **`acquired_at` de los manifiestos (2026-11-17T23:41Z) es solo
  procedencia local de AirAware y nunca se usa como `available_at`**.
- Posición del intervalo horario (inicio vs fin de la hora) no declarada por Open-Meteo en las
  páginas revisadas: desconocida, sin inferencia.

## Bloqueo exacto de NOAA ISD (medición de estación)

La adquisición planificada (única solicitud autorizada de esta continuación;
`max_bytes=4194304`, plazo 60 s, 1 worker, host `www.ncei.noaa.gov`) falló así:

1. **Error exacto del acquirer**: «Recurso público respondió HTTP **301**; transferencia
   detenida». El contrato de adquisición no sigue redirecciones por política de host exacto.
   La transferencia consumió **0 bytes de red** y no escribió nada en disco (verificado antes
   de cualquier otra acción; sin reintentos a ciegas).
2. **Diagnóstico solo-cabeceras**: la URL planificada
   `https://www.ncei.noaa.gov/data/global-hourly/access/2015/84691099999.csv` responde
   **301 → `https://noaa-global-hourly-pds.s3.amazonaws.com`**: NOAA redirigió el acceso del
   producto a su distribución oficial NODD (otro host, fuera de los hosts autorizados).
3. **El recurso existe en la ubicación canónica**
   (`https://noaa-global-hourly-pds.s3.amazonaws.com/2015/84691099999.csv`, HTTP 200) pero mide
   **4 382 554 bytes**, superior al techo por recurso fijado e inamovible de esta ejecución
   (**4 194 304 bytes**; el plan esperaba ~1 600 000). Ampliar el techo no está autorizado;
   una transferencia parcial (HTTP Range) truncaría filas CSV de forma arbitraria y el contrato
   de adquisición lo prohíbe («no recorta filas»).

Decisión: **ruta de medición de estación BLOQUEADA** por techo de bytes, sin débiles ni
excepciones. Consecuencias honestas: no se descargó ninguna observación medida; no hay identidad
NOAA verificada desde contenido (STATION/NAME/LATITUDE/LONGITUDE/ELEVATION, REPORT_TYPE,
frecuencia ni campos codificados); **no se calculan distancias** a las siete estaciones de aire
ni se afirma equivalencia alguna; licencia/redistribución de ISD sigue `unknown`. La muestra
entregada cubre R2 con productos de grilla/reanálisis y pronóstico archivado; la clase de
medición queda documentada como bloqueada, no como completada.

## Efectos externos reales y presupuestos (contabilidad honesta)

- Intento previo (transferencia en vivo): 14 solicitudes HTTP 200 a los dos hosts de Open-Meteo;
  payload original publicado verificado desde disco: **102 337 bytes**. El contador exacto de
  bytes de red de esa consola no es recuperable; se reporta el vacío sin inventarlo. Techos del
  asunto (32 recursos, 128 MiB) respetados con amplio margen.
- Esta continuación: **1 intento de transferencia NOAA** (0 bytes de carga; respuesta 301),
  **2 solicitudes solo-cabeceras** de diagnóstico (0 carga útil descargada), **0 solicitudes
  Open-Meteo**. Ninguna otra escritura externa; sin cuentas, pagos ni publicaciones.
- Reutilización offline (R5): 14/14 recursos reutilizados con `--offline --budget-bytes 0`,
  `network_bytes: 0`, exit 0, sin modificaciones de manifiestos u originales.

## Derechos y atribución

- Open-Meteo (ambas API): CC-BY-4.0 declarada por el proveedor para la API gratuita no comercial
  con atribución obligatoria; fuentes upstream (Copernicus C3S para ERA5; NOAA NCEP para GFS)
  conservan sus términos. Los valores muestreados permanecen bajo `data/raw/` local; su
  republicación no forma parte de #16.
- NOAA NCEI ISD: sin declaración de licencia verificada; no se adquirieron datos; atribución del
  producto no aplicable aún.
- SENAMHI: sin descargas nuevas; los bloqueos de OEFA y las decisiones del catálogo se detallan
  en [docs/sources/weather.md](../sources/weather.md).

## Bloqueos y desconocidos vivos

1. NOAA ISD bloqueado por techo de bytes en su ubicación canónica NODD (detalle arriba);
   alternativa futura: decisión explícita del responsable subiendo `max_bytes` a ≥ 4 382 554 o
   extracción por rangos oficiales del proveedor; ambas requieren autorización propia.
2. Posición del intervalo horario (inicio/fin) no documentada por Open-Meteo ni ISD.
3. `available_at` horario no documentado por los proveedores muestreados.
4. Licencia/redistribución de ISD sin evidencia documental; catálogo mantiene `unknown`.
5. Un valor de celda de reanálisis (una celda ERA5 para toda la muestra) no representa gradientes
   urbanos entre las siete estaciones de aire.
