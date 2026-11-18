# Adquisición meteorológica de Lima — ejecución y reconciliación real (#16)

Informe de ejecución real de la muestra de #16. La transferencia en vivo de los 14 recursos
Open-Meteo ocurrió en el intento previo (`acquired_at` **2026-11-17T23:41:45–48Z**, registrado en
los manifiestos bajo `data/raw/`); la contabilidad exacta de bytes de red de esa consola no es
recuperable y **no se inventa**. La continuación (attempt-02) verificó esos originales desde
disco y diagnosticó el bloqueo inicial de la ruta NOAA por redirección y techo local; la
corrección final (attempt-03) elevó el techo por recurso NOAA a 5 000 000 bytes (autorización del
gerente, aún muy por debajo del techo total del asunto de 128 MiB), transfirió el objeto oficial
NODD directo, ejecutó la reutilización sin red del plan completo (15/15) y produjo el recibo
[metadata/weather-acquisition.json](../../metadata/weather-acquisition.json).
La comparación de fuentes está en [docs/sources/weather.md](../sources/weather.md) y el plan en
[tasks/issue-16-plan.md](../tasks/issue-16-plan.md).

## Resultado en una línea

Muestra de reanálisis (ERA5, 7 coordenadas), pronóstico archivado (GFS `previous_day1`,
7 coordenadas) **y medición de estación (NOAA ISD Global Hourly)** adquirida, verificada y
reconciliada: **15 recursos, 4 484 891 bytes publicados, todos los SHA-256 coinciden**; 0 valores
faltantes en las variables Open-Meteo muestreadas. La estación NOAA adquirida es, según su
propio contenido, **«PISCO INTERNATIONAL, PE» (84691099999)**, no una estación de Lima: queda a
191–223 km (haversine aproximado) de las siete estaciones de aire; es evidencia real de la clase
medida y de la ruta de adquisición, **no un proxy de Lima**.

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
| 8 | `uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json --source noaa-isd-global-hourly --dry-run` (attempt-03, tras autorizar techo 5 000 000 y URL NODD directa) | **exit 0**; `known_size_bytes: 4382554`, `unknown_count: 0`, `authorized_max_bytes: 5000000`; sin GET/HEAD/DNS |
| 9 | `uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json --source noaa-isd-global-hourly --budget-bytes 5000000 --allow-host noaa-global-hourly-pds.s3.amazonaws.com --workers 1 --deadline-seconds 60` | **exit 0**; `completed: 1`, `reused: false`, `errors: []`, `network_bytes: 4448090`; original en disco mide exactamente 4 382 554 bytes (HTTP 200, `attempts: 1`) |
| 10 | `uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json --offline --budget-bytes 0` (plan completo de 15 recursos) | **exit 0**; `completed: 15` (`reused: true` en todos), `errors: []`, `network_bytes: 0` |
| 11 | Conciliación local determinista del CSV NOAA (identidad, fechas, REPORT_TYPE, estructura de campos codificados y distancias haversine) | perfil y distancias escritos en el recibo; sin decodificación de unidades/escalas |

Los comandos 1–7 corresponden a attempt-02 y a la transferencia en vivo del intento previo
(mismo plan de entonces, lote con `--budget-bytes 5570560 --workers 1 --deadline-seconds 60` y
los hosts autorizados de ese momento) que ejecutó solo los 14 recursos Open-Meteo; su salida de
consola exacta no es recuperable de la interrupción y no se reproduce de memoria. Los comandos
8–11 corresponden a attempt-03 con el plan actualizado (URL NODD directa, `max_bytes` 5 000 000).

## Verificación de integridad y bytes publicados (R4)

Recalculados ahora desde disco; los Open-Meteo coinciden con la verificación independiente del
gerente:

| Fuente | Recursos | Bytes originales publicados | SHA-256 | Ventana solicitada (UTC) | Marcas por recurso |
| --- | --- | --- | --- | --- | --- |
| `open-meteo-historical-weather` (ERA5, `models=era5`) | 7 | 65 867 | 7/7 coinciden | 2015-04-16 a 2015-04-23 | 192 horarias |
| `open-meteo-previous-model-runs` (GFS, `models=gfs_seamless`) | 7 | 36 470 | 7/7 coinciden | 2022-03-09 a 2022-03-15 | 168 horarias |
| `noaa-isd-global-hourly` (ISD Global Hourly, objeto NODD directo) | 1 | 4 382 554 | 1/1 coincide | 2015-01-01T00:00 a 2015-12-31T23:00 (contenido real) | 11 408 filas |
| **Total** | **15** | **4 484 891** | 15/15 | — | — |

Manifiestos con `http_status: 200`, `attempts: 1`, `validation: structure_only` y
`acquired_at`/`verified_at` locales (Open-Meteo: 2026-11-17T23:41:45–48Z; NOAA:
2026-11-17T23:59:25–26Z). El contador de red del lote NOAA reportó 4 448 090 bytes; el original
en disco mide exactamente 4 382 554 (igual al `Content-Length` del HEAD previo); la diferencia
de 65 536 no se interpreta. Los originales permanecen bajo `data/raw/` (ignorado por Git):
**ningún dato masivo entra al repositorio**; en Git solo entran plan, documentación, recibos y
este informe.

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
- **Medición de estación** (NOAA ISD): adquirida (objeto NODD directo, attempt-03). `DATE`
  ISO-8601 sin sufijo Z en las 11 408 filas; UTC según la documentación oficial del producto
  (declarado). La posición del intervalo horario (inicio vs fin) sigue sin documentación
  revisada: desconocida.
- `available_at` del proveedor por hora no está documentado en ninguna de las tres fuentes
  muestreadas y queda como desconocido; **`acquired_at` de los manifiestos (Open-Meteo
  2026-11-17T23:41Z; NOAA 2026-11-17T23:59Z) es solo procedencia local de AirAware y nunca se
  usa como `available_at`**.
- Posición del intervalo horario (inicio vs fin de la hora) no declarada por Open-Meteo en las
  páginas revisadas: desconocida, sin inferencia.

## Ruta NOAA ISD: bloqueo inicial (historia) y adquisición final real

### Historia preservada: bloqueo del 17/11/2026 por redirección y techo local (attempt-02)

La adquisición planificada originalmente (única solicitud autorizada entonces;
`max_bytes=4194304`, plazo 60 s, 1 worker, host `www.ncei.noaa.gov`) falló así:

1. **Error exacto del acquirer**: «Recurso público respondió HTTP **301**; transferencia
   detenida». El contrato de adquisición no sigue redirecciones por política de host exacto.
   La transferencia consumió **0 bytes de red** y no escribió nada en disco.
2. **Diagnóstico solo-cabeceras**: la URL planificada
   `https://www.ncei.noaa.gov/data/global-hourly/access/2015/84691099999.csv` responde
   **301 → `https://noaa-global-hourly-pds.s3.amazonaws.com`**: NOAA redirige el acceso del
   producto a su distribución oficial NODD (otro host).
3. **El recurso existe en la ubicación canónica**
   (`https://noaa-global-hourly-pds.s3.amazonaws.com/2015/84691099999.csv`, HTTP 200) y mide
   **4 382 554 bytes**, superior al techo local entonces vigente (**4 194 304 bytes**). El
   gerente revisó ese bloqueo, lo clasificó como techo local —no del presupuesto del asunto— y
   autorizó **5 000 000 bytes por recurso** para attempt-03.

### Adquisición final (attempt-03): objeto NODD directo

Con el techo autorizado y la URL oficial NODD directa en el plan (`--dry-run` previo sin red:
tamaño declarado 4 382 554 ≤ 5 000 000), la transferencia única terminó **HTTP 200**,
`attempts: 1`, `final_url` idéntica a la URL solicitada (sin redirección), original en disco de
**4 382 554 bytes** y **SHA-256 `6e6f79a85c70adb7669be1ed6d2f0ae5a1cf2995358b6268fd0867307e37832e`**
verificado; manifiesto bajo
`data/raw/noaa-isd-global-hourly/6e6f79a8…/manifest.json`. La `source_page_url` (página oficial
del producto ISD en NCEI) se conserva como procedencia del producto.

### Identidad y contenido real del archivo (reconciliación desde contenido)

- **Identidad constante en las 11 408 filas**: `STATION` **84691099999**, `NAME`
  **«PISCO INTERNATIONAL, PE»**, `LATITUDE` **-13.744864**, `LONGITUDE` **-76.220284**,
  `ELEVATION` **11.88**; `SOURCE` 4, `CALL_SIGN` 99999, `QUALITY_CONTROL` V020 en todas las
  filas. **La estación NO es Jorge Chávez/Callao** (candidato conjeturado antes de adquirir en
  la comparación de fuentes): es el aeropuerto internacional de Pisco.
- **Fechas**: `DATE` de 2015-01-01T00:00:00 a 2015-12-31T23:00:00; formato ISO-8601 sin sufijo
  Z en las 11 408 filas (UTC declarado por la documentación oficial del producto); **8 798
  instantes distintos y 2 610 instantes duplicados** — cada duplicado aparece exactamente dos
  veces, correspondiente a pares simultáneos FM-12/FM-15 (y FM-16 en algunos horarios); no se
  eliminó ninguna fila.
- **REPORT_TYPE**: FM-12 (Synop) 2 642 filas; FM-15 (METAR) 8 480; FM-16 (SPECI) 286.
- **Estructura de campos codificados** (conteos crudos, sin decodificar unidades, escalas ni
  validez — la documentación de formato ISD no pudo cargarse durante la revisión oficial):
  WND 5 subcampos por fila; CIG y VIS 4 subcampos; TMP, DEW y SLP 2 subcampos (valor+calidad).
  Tokens compuestos solo por dígitos 9 (marcadores usuales de ausente): WND 1 998
  (980 filas con primer subcampo `999`); CIG 21 408 (5 245 filas con `99999`); VIS 28 438
  (2 811 filas con `999999`); TMP 22 tokens (11 filas con `+9999`); DEW 60 (30 filas con
  `+9999`); SLP 8 788 filas con primer subcampo `99999`. Columnas reales observadas: las 33
  declaradas en el recibo (STATION…EQD). **No se decodifica ningún valor científico** porque la
  evidencia oficial citada no declara escalas/unidades por subcampo.
- **Ventana del intervalo de la muestra (2015-04-16T18:00Z a 2015-04-23T17:00Z)**: 202 filas en
  155 horas distintas (FM-12 54, FM-15 144, FM-16 4): la cobertura horaria de la estación en esa
  semana **no es continua ni exclusivamente horaria**.

### Distancias aproximadas a las siete estaciones de aire (haversine)

Distancia geográfica aproximada lat/lon (fórmula haversine, R = 6 371,0088 km) desde las
coordenadas declaradas por la propia estación NOAA (-13.744864, -76.220284) a las siete
coordenadas originales SENAMHI. El CRS de las coordenadas SENAMHI no está declarado en el
original, por lo que la equivalencia de sistemas de referencia queda sin resolver: los valores
son **aproximaciones geográficas**, no distancias operativas, y **no implican intercambiabilidad
ni equivalencia de estaciones**. No se mapea ni se fusiona ninguna estación.

| Estación SENAMHI | Distancia aproximada (km) |
| --- | --- |
| CAMPO_DE_MARTE | 206,4 |
| CARABAYLLO | 223,1 |
| SANTA_ANITA | 206,0 |
| SAN_BORJA | 201,0 |
| SAN_JUAN_DE_LURIGANCHO | 213,5 |
| SAN_MARTIN_DE_PORRES | 214,6 |
| VILLA_MARIA_DEL_TRIUNFO | 191,2 |

Lectura honesta: la estación ISD adquirida es **medición real de superficie** y prueba la ruta
de adquisición por estación-año, pero está **~190–225 km al sur de Lima**; no sirve como proxy
meteorológico de las siete estaciones de aire. Elegir una estación ISD próxima a Lima exigiría
identificar y autorizar otro ID de estación: fuera del alcance de #16 y sin solicitarlo aquí.

## Efectos externos reales y presupuestos (contabilidad honesta)

- Intento previo (transferencia en vivo): 14 solicitudes HTTP 200 a los dos hosts de Open-Meteo;
  payload original publicado verificado desde disco: **102 337 bytes**. El contador exacto de
  bytes de red de esa consola no es recuperable; se reporta el vacío sin inventarlo. Techos del
  asunto (32 recursos, 128 MiB) respetados con amplio margen.
- Attempt-02: **1 intento de transferencia NOAA** (0 bytes de carga; respuesta 301),
  **2 solicitudes solo-cabeceras** de diagnóstico (0 carga útil descargada), **0 solicitudes
  Open-Meteo**. Ningún recurso NOAA parcial ni cacheado quedó en disco.
- Attempt-03: **1 `--dry-run` sin red**, **1 transferencia NOAA única** al host NODD autorizado
  (HTTP 200; payload publicado 4 382 554 bytes verificado desde disco; contador del lote
  4 448 090 bytes, diferencia de 65 536 no interpretada), **0 solicitudes Open-Meteo**. Acumulado
  total del asunto ≈ 4,28 MiB de payload publicado sobre el techo de 128 MiB. Ninguna otra
  escritura externa; sin cuentas, pagos ni publicaciones.
- Reutilización offline (R5): **15/15 recursos** del plan completo reutilizados con
  `--offline --budget-bytes 0`, `network_bytes: 0`, exit 0, sin modificaciones de manifiestos u
  originales.

## Derechos y atribución

- Open-Meteo (ambas API): CC-BY-4.0 declarada por el proveedor para la API gratuita no comercial
  con atribución obligatoria; fuentes upstream (Copernicus C3S para ERA5; NOAA NCEP para GFS)
  conservan sus términos. Los valores muestreados permanecen bajo `data/raw/` local; su
  republicación no forma parte de #16.
- NOAA NCEI ISD: sin declaración de licencia verificada en las páginas oficiales revisadas; se
  adquirió el objeto NODD directo (4 382 554 bytes) y la atribución del producto se registra
  aquí: «Global Hourly - Integrated Surface Database, NOAA NCEI». Licencia y decisión de
  redistribución permanecen sin evidencia documental (`unknown`); los valores permanecen bajo
  `data/raw/` local y su republicación no forma parte de #16.
- SENAMHI: sin descargas nuevas; los bloqueos de OEFA y las decisiones del catálogo se detallan
  en [docs/sources/weather.md](../sources/weather.md).

## Bloqueos y desconocidos vivos

1. La estación ISD adquirida es Pisco Internacional (identidad desde contenido), a 191–223 km de
   las siete estaciones de aire de Lima: sin muestra de medición **en Lima**; una estación ISD
   próxima a Lima requeriría identificar y autorizar otro ID de estación (fuera del alcance de
   #16).
2. Semántica de los subcampos codificados ISD (unidades, escalas, códigos de calidad) sin
   decodificar: la documentación de formato no pudo cargarse durante la revisión oficial; solo
   se reportan conteos estructurales.
3. Posición del intervalo horario (inicio/fin) no documentada por Open-Meteo ni ISD.
4. `available_at` horario no documentado por los proveedores muestreados (tampoco por ISD).
5. Licencia/redistribución de ISD sin evidencia documental; catálogo mantiene `unknown`.
6. Un valor de celda de reanálisis (una celda ERA5 para toda la muestra) no representa gradientes
   urbanos entre las siete estaciones de aire.
7. Contabilidad exacta de bytes de red de la transferencia Open-Meteo del intento previo no
   recuperable (consola no recuperable); el contador NOAA de attempt-03 reporta 4 448 090 bytes
   frente a 4 382 554 en disco: diferencia registrada sin interpretar.
