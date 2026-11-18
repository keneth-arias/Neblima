# Adquisición meteorológica de Lima — ejecución y reconciliación real (#16)

Informe de ejecución real de la muestra de #16. La transferencia en vivo de los 14 recursos
Open-Meteo ocurrió en el intento previo (`acquired_at` **2026-11-17T23:41:45–48Z**, registrado en
los manifiestos bajo `data/raw/`); la contabilidad exacta de bytes de red de esa consola no es
recuperable y **no se inventa**. La continuación (attempt-02) verificó esos originales desde
disco y diagnosticó el bloqueo inicial de la ruta NOAA por redirección y techo local; attempt-03
elevó el techo por recurso NOAA a 5 000 000 bytes (autorización del gerente, aún muy por debajo
del techo total del asunto de 128 MiB) y transfirió el objeto NODD `2015/84691099999.csv`, cuyo
propio contenido reveló **«PISCO INTERNATIONAL, PE»**, no Lima: la adquisición fue real, pero la
estación no servía como muestra de Lima y quedó **rechazada por identidad desde contenido**.
La corrección final (attempt-04) reemplazó esa selección por la estación oficial
**84628099999 «JORGE CHAVEZ INTERNATIONAL, PE»** — identidad verificada leyendo el CSV
descargado antes de seleccionar — ejecutó la reutilización sin red del plan completo (15/15) y
actualizó el recibo
[metadata/weather-acquisition.json](../../metadata/weather-acquisition.json).
La comparación de fuentes está en [docs/sources/weather.md](../sources/weather.md) y el plan en
[tasks/issue-16-plan.md](../tasks/issue-16-plan.md).

## Resultado en una línea

Muestra de reanálisis (ERA5, 7 coordenadas), pronóstico archivado (GFS `previous_day1`,
7 coordenadas) **y medición de estación en Lima (NOAA ISD Global Hourly,
84628099999 «JORGE CHAVEZ INTERNATIONAL, PE»)** adquirida, verificada y reconciliada:
**15 recursos, 4 731 512 bytes publicados, todos los SHA-256 coinciden**; 0 valores faltantes en
las variables Open-Meteo muestreadas. La estación NOAA seleccionada se identifica desde su propio
CSV (no desde su ID): aeropuerto internacional Jorge Chávez, Callao, a **3,6–26,5 km**
(haversine aproximado) de las siete estaciones de aire. El objeto Pisco de attempt-03
(4 382 554 bytes) se conserva **rechazado** como evidencia histórica bajo `data/raw/`: no forma
parte de la selección ni de los totales publicados.

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
| 10 | `uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json --offline --budget-bytes 0` (plan completo de 15 recursos, attempt-03 con Pisco aún seleccionado) | **exit 0**; `completed: 15` (`reused: true` en todos), `errors: []`, `network_bytes: 0` |
| 11 | Conciliación local determinista del CSV NOAA (identidad, fechas, REPORT_TYPE, estructura de campos codificados y distancias haversine) | perfil y distancias escritos en el recibo; sin decodificación de unidades/escalas |
| 12 | Lectura del contenido del objeto de attempt-03: identidad real «PISCO INTERNATIONAL, PE» (84691099999), 191–223 km de Lima | **rechazo documentado**; la corrección quedó especificada para attempt-04 |
| 13 | Edición del plan: URL NOAA → `…/2015/84628099999.csv`, `expected_size_bytes` 4 629 175 (sin más cambios) | recibo y documentos actualizados en consecuencia |
| 14 | `uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json --source noaa-isd-global-hourly --dry-run` (attempt-04) | **exit 0**; `known_size_bytes: 4629175`, `unknown_count: 0`, `authorized_max_bytes: 5000000`; sin GET/HEAD/DNS |
| 15 | `uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json --source noaa-isd-global-hourly --budget-bytes 5000000 --allow-host noaa-global-hourly-pds.s3.amazonaws.com --workers 1 --deadline-seconds 60` (attempt-04: única transferencia en vivo de este intento) | **exit 0**; `completed: 1`, `reused: false`, `errors: []`, `network_bytes: 4694711`; original en disco mide exactamente 4 629 175 bytes (HTTP 200, `attempts: 1`) |
| 16 | Verificación desde disco (sha256sum, wc -c, manifiesto) y lectura del contenido del CSV | SHA-256 `1e5381f2…d9b92b`, 4 629 175 bytes; identidad «JORGE CHAVEZ INTERNATIONAL, PE» confirmada desde el propio archivo |
| 17 | `uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json --offline --budget-bytes 0` (plan completo de 15 recursos, attempt-04 con Lima) | **exit 0**; `completed: 15` (`reused: true` en todos), `errors: []`, `network_bytes: 0` |
| 18 | Conciliación local determinista del CSV NOAA Lima (identidad, fechas, instantes, REPORT_TYPE, campos codificados, ventana de 168 h y distancias haversine) | perfil y distancias escritos en el recibo; sin decodificación de unidades/escalas |

Los comandos 1–7 corresponden a attempt-02 y a la transferencia en vivo del intento previo
(mismo plan de entonces, lote con `--budget-bytes 5570560 --workers 1 --deadline-seconds 60` y
los hosts autorizados de ese momento) que ejecutó solo los 14 recursos Open-Meteo; su salida de
consola exacta no es recuperable de la interrupción y no se reproduce de memoria. Los comandos
8–11 corresponden a attempt-03 con el plan de entonces (URL NODD de Pisco, `max_bytes`
5 000 000); los comandos 12–18 corresponden a attempt-04 con el plan corregido (URL NODD de
Jorge Chávez, tamaño esperado 4 629 175). Ninguna solicitud Open-Meteo en línea ni nuevas
consultas del objeto Pisco en attempt-04.

## Verificar la muestra fijada sin red

El plan vigente fija los 15 SHA-256 del recibo. Los comandos históricos de adquisición y caché
anteriores corresponden a la configuración anterior a esta fijación. Para reutilizar sus
paquetes existentes bajo `raw/`, indicar la carpeta de datos que los contiene.

```bash
uv run --locked python -m airaware.acquisition.weather_sample --data-dir data
```

El verificador lee cada paquete por fuente y hash, comprueba su contrato, procedencia y bytes, y
sale con error ante una ausencia o discrepancia. El índice de caché incluye el hash esperado en
su clave y los paquetes originales se pueden verificar directamente con este comando.

## Verificación de integridad y bytes publicados (R4)

Recalculados ahora desde disco; los Open-Meteo coinciden con la verificación independiente del
gerente:

| Fuente | Recursos | Bytes originales publicados | SHA-256 | Ventana solicitada (UTC) | Marcas por recurso |
| --- | --- | --- | --- | --- | --- |
| `open-meteo-historical-weather` (ERA5, `models=era5`) | 7 | 65 867 | 7/7 coinciden | 2015-04-16 a 2015-04-23 | 192 horarias |
| `open-meteo-previous-model-runs` (GFS, `models=gfs_seamless`) | 7 | 36 470 | 7/7 coinciden | 2022-03-09 a 2022-03-15 | 168 horarias |
| `noaa-isd-global-hourly` (ISD Global Hourly, objeto NODD directo de **Lima/Jorge Chávez**) | 1 | 4 629 175 | 1/1 coincide | 2015-01-01T00:00 a 2015-12-31T23:00 (contenido real) | 11 441 filas |
| **Total seleccionado** | **15** | **4 731 512** | 15/15 | — | — |

Manifiestos con `http_status: 200`, `attempts: 1`, `validation: structure_only` y
`acquired_at`/`verified_at` locales (Open-Meteo: 2026-11-17T23:41:45–48Z; NOAA Lima:
2026-11-18T00:14:08–09Z). El contador de red del lote NOAA de attempt-04 reportó 4 694 711
bytes = 4 629 175 del original en disco (igual al `Content-Length` del HEAD previo) + 65 536 del
prefijo de la consulta `Range` inicial (`bytes=0-65535`) que el canal `http_file` consume del
mismo presupuesto antes del GET completo (misma aritmética que el 65 536 de diferencia registrado
en attempt-03; ahora explicable por el código del canal y no por pérdida de datos). Los
originales permanecen bajo `data/raw/` (ignorado por Git): **ningún dato masivo entra al
repositorio**; en Git solo entran plan, documentación, recibos y este informe.

**Contabilidad separada de artefactos de todos los intentos (no seleccionados dos veces)**:
además de los 15 recursos seleccionados, el objeto Pisco 84691099999 de attempt-03
(4 382 554 bytes, SHA-256 `6e6f79a85c70adb7669be1ed6d2f0ae5a1cf2995358b6268fd0867307e37832e`)
sigue preservado bajo `data/raw/` como evidencia histórica rechazada. El acumulado de
artefactos adquiridos en todos los intentos es **16 recursos y 9 114 066 bytes**
(102 337 Open-Meteo + 4 629 175 NOAA Lima + 4 382 554 NOAA Pisco); el recibo lo registra en
`totals.all_attempts_artifacts` sin contarlo dentro de la selección vigente.

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
  Sus series provienen de la misma celda, con elevaciones de ajuste de 54 a 272 m.
  Open-Meteo aplica ajuste estadístico por elevación de forma predeterminada. Se conserva cada
  serie por solicitud. Para compartir una serie en #17 se deben comparar las marcas y los
  valores por variable. La resolución nominal de la celda es 0,25° (~25 km).
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
  (2022-03-09T00:00 a 2022-03-15T23:00 UTC). `temperature_2m_previous_day1` identifica
  el adelanto nominal de 24 h. El archivo combina corridas, con varios tiempos válidos por
  inicialización. La respuesta muestreada no expone el instante exacto de inicialización ni la
  emisión por valor. Ambos quedan desconocidos junto con `available_at`. Véase la
  [explicación del proveedor](https://github.com/open-meteo/open-meteo/issues/1750).
- **Medición de estación** (NOAA ISD): adquirida (objeto NODD directo de Lima/Jorge Chávez,
  attempt-04; el objeto Pisco de attempt-03 quedó rechazado y preservado). `DATE` ISO-8601 sin
  sufijo Z en las 11 441 filas; UTC según la documentación oficial del producto (declarado).
  La posición del intervalo horario (inicio vs fin) sigue sin documentación revisada:
  desconocida.
- `available_at` del proveedor por hora no está documentado en ninguna de las tres fuentes
  muestreadas y queda como desconocido; **`acquired_at` de los manifiestos (Open-Meteo
  2026-11-17T23:41Z; NOAA Lima 2026-11-18T00:14Z) es solo procedencia local de AirAware y nunca
  se usa como `available_at`**.
- Posición del intervalo horario (inicio vs fin de la hora) no declarada por Open-Meteo en las
  páginas revisadas: desconocida, sin inferencia.

## Ruta NOAA ISD: bloqueo inicial, rechazo de Pisco y corrección Lima (historia completa)

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

### Adquisición de attempt-03 (historia): objeto NODD directo — luego rechazado por identidad

Con el techo autorizado y la URL oficial NODD directa en el plan (`--dry-run` previo sin red:
tamaño declarado 4 382 554 ≤ 5 000 000), la transferencia única terminó **HTTP 200**,
`attempts: 1`, `final_url` idéntica a la URL solicitada (sin redirección), original en disco de
**4 382 554 bytes** y **SHA-256 `6e6f79a85c70adb7669be1ed6d2f0ae5a1cf2995358b6268fd0867307e37832e`**
verificado; manifiesto bajo
`data/raw/noaa-isd-global-hourly/6e6f79a8…/manifest.json`. La `source_page_url` (página oficial
del producto ISD en NCEI) se conserva como procedencia del producto. **La lectura del propio CSV
reveló que la estación era PISCO INTERNATIONAL, PE (84691099999)**, no Lima: el objeto queda
**rechazado** como muestra de Lima y preservado sin cambios como evidencia histórica; no se
renombró ni se reetiquetó.

### Corrección de attempt-04: estación Lima/Jorge Chávez verificada desde su propio contenido

La especificación de attempt-04 fijó el objeto oficial NODD del candidato Lima con evidencia
HEAD previa del gerente (HTTP 200, `Content-Length` 4 629 175,
`Last-Modified` 2023-07-30T08:50:30Z; este intento no repitió la consulta). Tras editar solo el
trabajo NOAA del plan (URL `2015/84628099999.csv`, tamaño esperado 4 629 175), un `--dry-run`
sin red confirmó 4 629 175 ≤ 5 000 000 y la **única transferencia en vivo** terminó HTTP 200,
`attempts: 1`, `network_bytes` 4 694 711 (4 629 175 del original + 65 536 del prefijo de la
consulta `Range` inicial; misma aritmética de attempt-03), original en disco de exactamente
**4 629 175 bytes**, **SHA-256 `1e5381f2fce145f949456e5749345c38ba6c52db357f1a554448c86c86d9b92b`**
verificado y manifiesto bajo `data/raw/noaa-isd-global-hourly/1e5381f2…/manifest.json`.
**La selección solo procedió después de leer el CSV descargado**: `STATION` **84628099999**,
`NAME` **«JORGE CHAVEZ INTERNATIONAL, PE»**, `LATITUDE` **-12.021889**, `LONGITUDE`
**-77.114319**, `ELEVATION` **34.44** — constantes en las 11 441 filas y coordenadas plausibles
para Lima/Callao. Sin solicitudes Open-Meteo ni nuevas consultas del objeto Pisco.

### Identidad y contenido real del archivo Lima (reconciliación desde contenido)

- **Identidad constante en las 11 441 filas**: `STATION` **84628099999**, `NAME`
  **«JORGE CHAVEZ INTERNATIONAL, PE»**, `LATITUDE` **-12.021889**, `LONGITUDE` **-77.114319**,
  `ELEVATION` **34.44**; `SOURCE` 4, `CALL_SIGN` 99999, `QUALITY_CONTROL` V020 en todas las
  filas. Identidad confirmada desde el contenido descargado, no asumida desde el ID.
- **Fechas**: `DATE` de 2015-01-01T00:00:00 a 2015-12-31T23:00:00; formato ISO-8601 sin sufijo
  Z en las 11 441 filas (UTC declarado por la documentación oficial del producto); **8 803
  instantes distintos y 2 638 instantes duplicados** — cada duplicado aparece exactamente dos
  veces (2 622 pares FM-12/FM-15 y 16 pares FM-15/FM-16 simultáneos); no se eliminó ninguna fila.
  Además, 135 filas del año llevan instante fuera de hora (minuto distinto de cero: FM-16 SPECI
  115, FM-15 20); se reportan sin reasignarlas a la hora.
- **REPORT_TYPE**: FM-12 (Synop) 2 652 filas; FM-15 (METAR) 8 674; FM-16 (SPECI) 115.
- **Estructura de campos codificados** (conteos crudos, sin decodificar unidades, escalas ni
  validez — la documentación de formato ISD no pudo cargarse durante la revisión oficial):
  WND 5 subcampos por fila; CIG y VIS 4 subcampos; TMP, DEW y SLP 2 subcampos (valor+calidad).
  Tokens compuestos solo por dígitos 9 (marcadores usuales de ausente): WND 636
  (312 filas con primer subcampo `999`); CIG 16 483 (2 728 filas con `99999`); VIS 25 756
  (1 437 filas con `999999`); SLP 17 620 tokens (8 810 filas con primer subcampo `99999`);
  TMP 7 tokens estrictos y 7 filas con primer subcampo `+9999` (marcador con signo); DEW 12
  tokens estrictos y 12 filas con `+9999`. Columnas reales observadas: las 33 declaradas en el
  recibo (STATION…EQD). **No se decodifica ningún valor científico** porque la
  evidencia oficial citada no declara escalas/unidades por subcampo.
- **Ventana del intervalo de la muestra (2015-04-16T18:00Z a 2015-04-23T17:00Z)**: 234 filas en
  **179 instantes distintos: 167 en punto (de los 168 posibles) + 12 fuera de hora** (SPECI);
  FM-12 55, FM-15 167, FM-16 12. La cobertura horaria de la estación en esa semana **no es
  continua ni exclusivamente horaria**.

### Historia preservada: contenido rechazado PISCO INTERNATIONAL, PE (attempt-03)

El objeto de attempt-03 (`2015/84691099999.csv`, 4 382 554 bytes,
SHA-256 `6e6f79a8…37832e`) identificó desde su contenido `STATION` 84691099999, `NAME`
«PISCO INTERNATIONAL, PE», `LATITUDE` -13.744864, `LONGITUDE` -76.220284, `ELEVATION` 11.88,
constantes en sus 11 408 filas: 8 798 instantes distintos, 2 610 duplicados (pares FM-12/FM-15),
FM-12 2 642 / FM-15 8 480 / FM-16 286; ventana de la muestra con 202 filas en 155 instantes
distintos. Está a **191,2–223,1 km** de las siete estaciones de aire de Lima: por identidad
desde contenido quedó **rechazado** como muestra de Lima en attempt-04. El original y su
manifiesto permanecen **sin cambios** bajo
`data/raw/noaa-isd-global-hourly/6e6f79a8…/`; se conserva en el recibo
(`totals.noaa_isd.rejected_candidates`) y se contabiliza por separado en
`totals.all_attempts_artifacts` (16 recursos y 9 114 066 bytes en todos los intentos), nunca
como seleccionado.

### Distancias aproximadas de la estación Lima a las siete estaciones de aire (haversine)

Distancia geográfica aproximada lat/lon (fórmula haversine, R = 6 371,0088 km) desde las
coordenadas declaradas por la propia estación NOAA (-12.021889, -77.114319) a las siete
coordenadas originales SENAMHI. El CRS de las coordenadas SENAMHI no está declarado en el
original, por lo que la equivalencia de sistemas de referencia queda sin resolver: los valores
son **aproximaciones geográficas**, no distancias operativas, y **no implican intercambiabilidad
ni equivalencia de estaciones**. No se mapea ni se fusiona ninguna estación.

| Estación SENAMHI | Distancia aproximada (km) |
| --- | --- |
| SAN_MARTIN_DE_PORRES | 3,6 |
| CAMPO_DE_MARTE | 9,4 |
| SAN_JUAN_DE_LURIGANCHO | 13,3 |
| SAN_BORJA | 15,1 |
| SANTA_ANITA | 15,7 |
| CARABAYLLO | 15,9 |
| VILLA_MARIA_DEL_TRIUNFO | 26,5 |

Lectura honesta: la estación ISD seleccionada es **medición real de superficie en el aeropuerto
de Lima/Callao**, a distancias geográficas pequeñas de las siete estaciones de aire
(3,6–26,5 km, aproximación haversine sin CRS resuelto). Eso **no** convierte la serie en
covariable de las estaciones de aire: medición meteorológica de aeropuerto no equivale a
medición de aire urbano, la cobertura horaria observada no es continua (167 instantes en punto
de 168 posibles en la semana de la muestra, más SPECI fuera de hora) y la decisión de integrar
esta fuente como covariable es de #17 con su propia evidencia de disponibilidad y derechos.

## Efectos externos reales y presupuestos (contabilidad honesta)

- Intento previo (transferencia en vivo): 14 solicitudes HTTP 200 a los dos hosts de Open-Meteo;
  payload original publicado verificado desde disco: **102 337 bytes**. El contador exacto de
  bytes de red de esa consola no es recuperable; se reporta el vacío sin inventarlo. Techos del
  asunto (32 recursos, 128 MiB) respetados con amplio margen.
- Attempt-02: **1 intento de transferencia NOAA** (0 bytes de carga; respuesta 301),
  **2 solicitudes solo-cabeceras** de diagnóstico (0 carga útil descargada), **0 solicitudes
  Open-Meteo**. Ningún recurso NOAA parcial ni cacheado quedó en disco.
- Attempt-03: **1 `--dry-run` sin red**, **1 transferencia NOAA única** al host NODD autorizado
  (HTTP 200; payload publicado 4 382 554 bytes verificado desde disco — objeto Pisco, luego
  rechazado; contador del lote 4 448 090 bytes, diferencia de 65 536 explicada en attempt-04
  desde el código del canal), **0 solicitudes Open-Meteo**. Acumulado total del asunto ≈ 4,28 MiB
  de payload publicado sobre el techo de 128 MiB. Ninguna otra escritura externa; sin cuentas,
  pagos ni publicaciones.
- Attempt-04: **1 edición local del plan**, **1 `--dry-run` sin red**, **1 transferencia NOAA
  única** al host NODD autorizado (HTTP 200; payload publicado 4 629 175 bytes verificado desde
  disco; contador del lote 4 694 711 = original + 65 536 del prefijo `Range`), **0 solicitudes
  Open-Meteo**, **0 consultas nuevas del objeto Pisco**. Reutilización offline del plan completo
  15/15 con presupuesto 0. Acumulado total del asunto ≈ 8,69 MiB de payload publicado sobre el
  techo de 128 MiB. Ninguna otra escritura externa; sin cuentas, pagos ni publicaciones.
- Reutilización offline (R5): **15/15 recursos** del plan completo reutilizados con
  `--offline --budget-bytes 0`, `network_bytes: 0`, exit 0, sin modificaciones de manifiestos u
  originales (ejecutada en attempt-03 con el plan de entonces y repetida en attempt-04 con el
  plan corregido; ambos exit 0).

## Derechos y atribución

- Open-Meteo (ambas API): CC-BY-4.0 declarada por el proveedor para la API gratuita no comercial
  con atribución obligatoria; fuentes upstream (Copernicus C3S para ERA5; NOAA NCEP para GFS)
  conservan sus términos. Los valores muestreados permanecen bajo `data/raw/` local; su
  republicación no forma parte de #16.
- NOAA NCEI ISD: sin declaración de licencia verificada en las páginas oficiales revisadas; se
  adquirió el objeto NODD directo de Lima/Jorge Chávez (4 629 175 bytes, attempt-04) y la
  atribución del producto se registra aquí: «Global Hourly - Integrated Surface Database, NOAA
  NCEI». Licencia y decisión de redistribución permanecen sin evidencia documental (`unknown`);
  los valores permanecen bajo `data/raw/` local y su republicación no forma parte de #16.
  El objeto Pisco rechazado de attempt-03 (4 382 554 bytes) permanece preservado localmente con
  la misma condición de derechos.
- SENAMHI: sin descargas nuevas; los bloqueos de OEFA y las decisiones del catálogo se detallan
  en [docs/sources/weather.md](../sources/weather.md).

## Bloqueos y desconocidos vivos

1. La estación ISD seleccionada está en Lima/Callao (identidad desde contenido) pero **no es
   una estación de aire**: aeropuerto a 3,6–26,5 km de las siete estaciones de aire
   (aproximación haversine, CRS SENAMHI sin declarar). Su cobertura horaria en la semana de la
   muestra no es continua (167 instantes en punto de 168 posibles, más SPECI fuera de hora) y
   la decisión de usarla como covariable corresponde a #17 con su propia evidencia. El objeto
   Pisco rechazado (attempt-03) permanece preservado como historia, nunca como muestra de Lima.
2. Semántica de los subcampos codificados ISD (unidades, escalas, códigos de calidad) sin
   decodificar: la documentación de formato no pudo cargarse durante la revisión oficial; solo
   se reportan conteos estructurales.
3. ISD conserva posición del intervalo desconocida. ERA5 conserva la semántica por variable.
   GFS conserva inicialización y emisión exactas desconocidas.
4. `available_at` horario no documentado por los proveedores muestreados (tampoco por ISD).
5. Licencia/redistribución de ISD sin evidencia documental; catálogo mantiene `unknown`.
6. Las series ERA5 comparten una celda y conservan ajustes por elevación. Su comparación por
   variable queda para #17 antes de compartir series entre estaciones.
7. Contabilidad exacta de bytes de red de la transferencia Open-Meteo del intento previo no
   recuperable (consola no recuperable). La diferencia de 65 536 bytes de los contadores NOAA de
   attempt-03/04 quedó explicada en attempt-04 desde el código del canal `http_file` (prefijo
   `Range` de la consulta inicial compartido con el GET completo); la diferencia Open-Meteo
   sigue sin recuperarse y no se inventa.
