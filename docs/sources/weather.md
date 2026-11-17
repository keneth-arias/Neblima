# Fuentes meteorológicas para Lima — comparación verificada (#16)

Revisión oficial con Lightpanda (`/usr/local/bin/lightpanda`, versión
`1.1.0-nightly.12173+18ff596e6`) el **17/11/2026 UTC**, según [el protocolo](../web-access.md).
Cada fila registra enlace oficial, fecha de revisión UTC y decisión para la muestra de #16.
Un acceso público no acredita licencia ni permisos de redistribución; lo desconocido queda
explícito. Resultado de la muestra de #16: 14 recursos Open-Meteo (reanálisis ERA5 y pronóstico
archivado GFS) adquiridos, verificados y reconciliados; la ruta de medición de estación (NOAA
ISD) quedó **bloqueada por techo de bytes**. La adquisición real y su reconciliación están en
[el informe de ejecución](../../reports/acquisition/weather.md) y en
[el plan de #16](../../tasks/issue-16-plan.md).

Clases separadas en todo el documento: **medición de estación** (ground measured),
**reanálisis/modelo** (reanalysis/modeled), **pronóstico archivado** (forecast). Un valor de
grilla de reanálisis no es una medición en la estación de aire; las estaciones meteorológicas
cercanas no son intercambiables con las estaciones de aire sin evidencia y distancia documentada.

## Siete identidades provisionales de referencia

Derivadas del original SENAMHI verificado (SHA-256
`896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4`) con la regla de #14;
detalle y station_key en [el plan de #16](../../tasks/issue-16-plan.md). Coordenadas originales:
CAMPO_DE_MARTE (-77.0432, -12.0705, 117 m), CARABAYLLO (-77.0336, -11.9022, 179 m),
SANTA_ANITA (-76.9714, -12.043, 253 m), SAN_BORJA (-77.0077, -12.1086, 128 m),
SAN_JUAN_DE_LURIGANCHO (-76.9992, -11.9816, 240 m), SAN_MARTIN_DE_PORRES (-77.0845, -12.0089,
56 m), VILLA_MARIA_DEL_TRIUNFO (-76.92, -12.1664, 272 m). Sistema de referencia de esas
coordenadas: no declarado en el CSV ni en el diccionario; permanece sin convertir.

## Decisiones de #16

| Fuente | Clase | Decisión para la muestra | Motivo exacto |
| --- | --- | --- | --- |
| senamhi-hourly-meteorology (GBON/RBON) | medición de estación | diferida | CSV monolítico de 48,14 MB (nacional); sin ruta por estación; cobertura Lima/2015 dentro del CSV sin verificar; desproporcionado para una muestra acotada |
| senamhi-station-network | contexto (inventario) | excluida como muestra | portal de inventario de estaciones; no acredita descarga histórica de datos |
| noaa-integrated-surface-database | medición de estación | seleccionada para intento acotado → **bloqueada por techo de bytes** | CSV por estación-año; la URL planificada responde 301 → distribución NODD en otro host y el original canónico mide 4 382 554 bytes > 4 194 304 autorizados (informe de ejecución); licencia sin declaración oficial verificada |
| noaa-atmospheric-soundings (IGRA2) | medición de estación (radiosondeo) | excluida | sondeos 12 h; no es clima superficial horario; incompatible con H24/F6 |
| open-meteo-historical-weather | reanálisis (ERA5/ERA5-Land/IFS) | **seleccionada** (grilla) | una solicitud por estación cubre 2015; sin cuenta; CC-BY-4.0 no comercial; explícitamente no es medición de estación |
| open-meteo-historical-forecasts | pronóstico archivado (costura de corridas) | diferida | cobertura ~2022+ sin hora de emisión por valor (corridas costuradas); semántica de emisión más débil que previous-runs |
| open-meteo-previous-model-runs | pronóstico archivado (advectado por adelanto) | **seleccionada** (pronóstico) | offsets `previous_dayN` = emitido N×24 h antes del tiempo válido; GFS 2 m desde 03/2021 permite muestra dentro de `train` |
| era5-and-era5-land (CDS directo) | reanálisis | bloqueada esta ruta | CDS exige cuenta y aceptación de licencia; cuentas nuevas no autorizadas; ERA5 se cubre por la ruta Open-Meteo |
| nasa-power | reanálisis meteorológico (MERRA-2/GEOS-IT) + radiación satelital | diferida | cubre 2015 (2001+) pero exige 7 solicitudes puntuales; no necesaria para la muestra; documentada para decisión futura |
| oefa-csv (campos meteorológicos ya adquiridos) | medición declarada, sin resolver | bloqueada | reloj, CRS (ESTE/NORTE), unidades y calidad por resolver; sin redescarga |

## Detalle por candidato (evidencia fechada 17/11/2026)

### senamhi-hourly-meteorology — SENAMHI vía datosabiertos

- Página oficial: https://www.datosabiertos.gob.pe/dataset/variables-meteorologicas-de-las-estaciones-autom%C3%A1ticas-de-intercambio-internacional-servicio — Lightpanda HTTP 200 el 17/11/2026 23:25 UTC. El intento previo del 16/11/2026 había quedado en `navigation timed out` (metadata/source-access.json); la revisión de hoy lo reactiva sin debilitar controles.
- Producto: «Variables Meteorologicas de las Estaciones automáticas de intercambio internacional — SENAMHI». Datos **horarios validados** de temperatura, humedad relativa y precipitación de estaciones automáticas de las redes GBON y RBON (declaración de la ficha). Recurso CSV 48,14 MB (creado 31/05/2024; actualizado 08/09/2025); diccionario XLSX 10,56 KB; metadatos DOCX 20,18 KB. Metadatos CKAN consultados por Lightpanda (package_show id b884a001-f444-4c87-91b2-bee1891e6eb7).
- Campos declarados por la ficha: nombre, latitud, longitud, altitud, departamento, provincia, distrito, ubigeo y red de la estación; fecha, hora, temperatura, humedad relativa y precipitación. La ficha declara precipitación en milímetros y exige filtrar registros vacíos. Unidades de temperatura y humedad: usuales (°C, %) pero **no declaradas explícitamente en la ficha revisada**; quedan como inferidas pendientes del diccionario.
- Descarga de los recursos binarios (XLSX/DOCX): la CLI de Lightpanda disponible (`fetch`, sin acción `download`) no preserva bytes originales de esos archivos; se registró la limitación y no se sustituyó la herramienta en silencio. La decisión de la muestra no dependía de ellos.
- Licencia: Open Data Commons Attribution License (ODC-BY) declarada en ficha y CKAN; el texto de
  esa licencia permite redistribuir con atribución. La decisión de redistribución del proyecto
  para esta fuente sigue pendiente: el catálogo mantiene `redistribution: unknown` hasta la
  decisión de integración.
- Disponibilidad/publicación: actualización declarada del recurso el 08/09/2025; semántica de `available_at` por hora no documentada.
- Riesgo de duplicación con senamhi-lima-csv: distinto instrumento/red (meteorológica GBON vs calidad de aire); no se asume correspondencia con las siete estaciones de aire.
- Decisión: **diferida** — la extracción de una muestra por estación exigiría transferir el CSV completo nacional (48,14 MB), desproporcionado para esta muestra y con cobertura Lima/2015 sin verificar; requiere decisión explícita de cobertura o una ruta por estación.

### senamhi-station-network — red de estaciones SENAMHI

- Página: https://www.senamhi.gob.pe/servicios/?p=estaciones — HTTP 200 verificado el 16/11/2026 (metadata/source-access.json).
- Es un inventario/contexto de la red; la revisión de #16 no identificó en él una descarga histórica acotada por estación. Decisión: **excluida como fuente de muestra**; se conserva como contexto de identidad.

### noaa-integrated-surface-database (ISD, Global Hourly) — NOAA NCEI

- Página oficial: https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database — HTTP 200 el 17/11/2026 (y 16/11/2026 por el catálogo). Producto: «Global Hourly - Integrated Surface Database»; observaciones **horarias y sinópticas** de superficie compiladas de más de 100 fuentes originales en formato ASCII común; parámetros declarados: velocidad y dirección del viento, racha, temperatura, punto de rocío, nubosidad, presión a nivel de la estación y del nivel del mar, tiempo presente, visibilidad, precipitación.
- Ruta de acceso acotada: archivo CSV por estación y año bajo https://www.ncei.noaa.gov/data/global-hourly/access/&lt;año&gt;/&lt;estación&gt;.csv; sin autenticación. El manifiesto oficial de producto (metadata geoportal gov.noaa.ncdc:C00532) declara distribución CSV; su sección Constraints no renderizó contenido textual en la revisión.
- Licencia: **sin declaración verificada** en las páginas oficiales revisadas (el intento de data-description devolvió 404; noaa.gov/disclaimer devolvió 403; el PDF de formato y los recursos de `/data/` devuelven `BadContentEncoding` al cargador de Lightpanda y se registró la limitación). `license` queda nula y `redistribution: unknown` en el catálogo; sin afirmación de dominio público sin evidencia.
- Tiempo: `DATE` ISO-8601 en UTC; `REPORT_TYPE` distingue Synop/METAR etc. (declarado por la
  documentación oficial); la frecuencia y los campos codificados **no se conciliaron con
  contenido real porque la transferencia fue bloqueada**: sin datos adquiridos no se reportan
  frecuencias observadas. Posición del intervalo (inicio/fin) sin documentación revisada:
  desconocida.
- Lima: estación WMO 84691 (Jorge Chávez, Callao) como candidato; la identidad del archivo (STATION/NAME/LATITUDE/LONGITUDE/ELEVATION en el propio CSV) sería la evidencia por estación. **No es ninguna de las siete estaciones de aire**: las distancias se documentarían con distancia y método, no como equivalencia. Sin contenido adquirido no se calculan distancias.
- Resultado de la adquisición del 17/11/2026: la URL planificada respondió **301** hacia
  `noaa-global-hourly-pds.s3.amazonaws.com` (distribución oficial NODD, otro host); el CSV
  `2015/84691099999.csv` existe allí (HTTP 200) pero mide **4 382 554 bytes**, por encima del
  techo por recurso autorizado en esta ejecución (4 194 304). Transferencia parcial truncaría
  filas y está prohibida. Detalle del error exacto, órdenes y exit codes en
  [el informe](../../reports/acquisition/weather.md).
- Decisión: **seleccionada para intento acotado → bloqueada por techo de bytes**; la clase de
  medición de estación queda sin muestra real en #16 y cualquier extensión del techo requiere
  autorización propia del responsable.

### noaa-atmospheric-soundings (IGRA2) — NOAA NCEI

- Página: https://www.ncei.noaa.gov/products/weather-balloon/integrated-global-radiosonde-archive — HTTP 200 el 16/11/2026 (catálogo). Producto de radiosondeos (globos) desde 1905 globalmente.
- Clase: medición de estación, pero **perfilería vertical dos veces al día**, no clima superficial horario. Decisión: **excluida** para covariables horarias del benchmark (resolución temporal incompatible); el archivo del sondeo de Lima no se demostró ni se requiere para esta decisión.

### open-meteo-historical-weather — Open-Meteo (ERA5/ERA5-Land/ECMWF IFS)

- Documentación oficial: https://open-meteo.com/en/docs/historical-weather-api — HTTP 200 el 17/11/2026. Endpoint: https://archive-api.open-meteo.com/v1/archive; sin cuenta para uso gratuito no comercial.
- Clase: **reanálisis**. La propia documentación: «based on reanalysis datasets … may not have had weather stations nearby». Modelos declarados: ECMWF IFS 9 km horario desde 2017; ERA5 0,25° (~25 km) horario desde 1940, actualización diaria con 5 días de retraso; ERA5-Land 0,1° desde 1950. La recomendación oficial para consistencia plurianual es usar ERA5 o ERA5-Land explícitamente (`models=`), evitando la mezcla por defecto (`best_match`).
- Variables horarias declaradas con unidades por omisión (página de parámetros, revisada el 17/11/2026): temperature_2m °C; relative_humidity_2m %; dewpoint_2m °C; precipitation mm (lluvia + nieve); surface_pressure y pressure_msl hPa; cloud_cover %; wind_speed_10m km/h (unidades alternativas ms/mph/kn); wind_direction_10m grados; wind_gusts_10m km/h.
- Tiempo: marca horaria ISO-8601; zona por omisión GMT+0 (UTC). Posición inicio/fin del intervalo horario: **no declarada en las páginas revisadas**; se registra desconocida. `available_at`: para ERA5, ~5 días (latencia declarada); para IFS, «every 6 hours with no delay» (declaración del proveedor de la tabla de fuentes).
- Licencia: CC-BY-4.0 para la API gratuita no comercial (<10 000 llamadas/día, 600/min; https://open-meteo.com/en/terms y /en/licence, HTTP 200 el 17/11/2026); atribución requerida con enlace a Open-Meteo; fuentes upstream con licencias propias (Copernicus C3S: «licence to use Copernicus products»). Los términos declarados permiten redistribuir los valores obtenidos con atribución dentro del uso no comercial; la decisión de redistribución del proyecto sigue pendiente y el catálogo mantiene `redistribution: unknown` (ver «Derechos y atribución» abajo).
- Identidad espacial: solicitudes por coordenadas decimales (WGS84; sin declaración explícita de EPSG en la página — desconocido formal); la respuesta devuelve latitud/longitud/elevación de la celda usada, lo que permite documentar resolución de celda real por estación.
- Decisión: **seleccionada** para la muestra gridded: cubre 2015-04 para las siete coordenadas con solicitudes acotadas; se solicita `models=era5` para proveniencia única. **No se etiqueta como medición de estación ni como pronóstico archivado.**

### open-meteo-historical-forecasts — Open-Meteo (pronósticos archivados)

- Documentación oficial: https://open-meteo.com/en/docs/historical-forecast-api — HTTP 200 el 17/11/2026. Endpoint: https://historical-forecast-api.open-meteo.com/v1/forecast.
- Clase: **pronóstico archivado**: «Archived High-Resolution Weather Forecasts … same models, same parameters». Cobertura declarada «starts around 2022»; los modelos se inicializan cada 1/3/6 h y «Each run's first few hours are stitched into a continuous hourly timeseries».
- Semántica de emisión: la serie archivada **no expone hora de emisión por valor** (es una costura de corridas); el tiempo válido es la marca horaria. Para el requisito de #16 («archived forecast availability must include issue/run and valid times»), esta propiedad la hace insuficiente como muestra de emisión explícita.
- Licencia: CC-BY-4.0 no comercial, igual que Historical Weather.
- Decisión: **diferida** — cobertura incompatible con la ventana 2015 y sin emisión por valor; el pronóstico archivado se demuestra con previous-runs, que sí declara adelanto.

### open-meteo-previous-model-runs — Open-Meteo (corridas anteriores)

- Documentación oficial: https://open-meteo.com/en/docs/previous-runs-api — HTTP 200 el 17/11/2026. Endpoint: https://previous-runs-api.open-meteo.com/v1/forecast.
- Clase: **pronóstico archivado con adelanto explícito**: «temperature_2m_previous_day1 returns the value predicted 24 hours before valid time … up to day 7». Hora de emisión = tiempo válido − N×24 h, sin ambigüedad de costura.
- Cobertura declarada: «Most models are archived from January 2024. GFS 2 m temperature extends back to March 2021».
- Variables (Day 0–7): temperatura 2 m, humedad relativa, punto de rocío, precipitación, presión (nivel del mar y superficie), nubosidad, viento (velocidad y dirección 10 m), entre otras; unidades por omisión idénticas a las demás API.
- Licencia: CC-BY-4.0 no comercial.
- Decisión: **seleccionada** para la muestra de pronóstico archivado con GFS (temperatura 2 m y previous_day1), en una ventana corta dentro de `train` (2022), documentada aparte de la muestra de reanálisis de 2015. No se rotula como reanálisis ni como medición.

### era5-and-era5-land — Copernicus C3S / ECMWF (CDS directo)

- Página oficial: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview — HTTP 200 el 17/11/2026. «ERA5 is the fifth generation ECMWF reanalysis … available from 1940 … updated daily with a latency of about 5 days»; ERA5T puede diferir de la versión final 2–3 meses.
- Clase: reanálisis. La descarga por CDS exige cuenta registrada y aceptación de la «licence to use Copernicus products» (enlazada desde https://open-meteo.com/en/licence).
- Decisión: **bloqueada esta ruta para este intento** (crear cuentas no está autorizado); ERA5 queda cubierto por la ruta acotada de Open-Meteo con `models=era5`. La ficha CDS queda verificada documentalmente.

### nasa-power — NASA POWER

- Documentación oficial revisada el 17/11/2026: hourly https://power.larc.nasa.gov/docs/services/api/temporal/hourly/ (HTTP 200) y fuentes meteorológicas https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/ (HTTP 200).
- Clase documentada: **reanálisis/modelo para meteorología** — «Meteorological parameters are derived from NASA's GMAO MERRA-2 assimilation model and GEOS-IT», grilla nativa ½° latitud × ⅝° longitud, MERRA-2 desde 1981, GEOS-IT cerca de tiempo real con ~2 días de latencia; la radiación proviene de productos satelitales (sección propia del sitio). No es medición de estación.
- Servicio horario: datos UTC/LST desde 2001-01-01; máximo 15 parámetros por solicitud; formatos JSON/CSV; precipitación en mm/hora; la API acepta punto único o caja regional (no listas de puntos).
- Licencia: sin declaración de licencia de datos en las páginas revisadas; uso del servicio sin cobro según la documentación; `redistribution: unknown`.
- Decisión: **diferida** — cubriría 2015, pero la muestra grided ya queda cubierta por ERA5 vía Open-Meteo; exigiría 7 solicitudes puntuales adicionales sin necesidad para #16. Clasificada por su producto subyacente documentado (MERRA-2), no como medición.

### Campos meteorológicos de OEFA (ya adquiridos; sin redescarga)

- Evidencia existente: catálogo `oefa-csv` (descargado 16/11/2026; 1 317 948 939 bytes) y `oefa-eas-aire` (17/11/2026); informe [oefa](../../reports/acquisition/oefa.md); análisis de libros [IPASH/EAC/EAF/EAT](../oefa-workbook-analysis.md) y [reports/oefa-workbook-analysis.md](../../reports/oefa-workbook-analysis.md).
- El CSV ancho adquirido contiene DIRECCION_VIENTO, VELOCIDAD_VIENTO, HUMEDAD_RELATIVA, PRECIPITACION, PRESION_BAROMETRICA, RADIACION_SOLAR y TEMPERATURA (columnas del perfil verificado en metadata/benchmark-selection.json). El libro EAF horario incluye meteorología en candidatos Lima (2018–2023).
- Bloqueos vigentes que impiden usar esos campos como covariables: `lima_timestamps_unresolved`, `timezone_and_interval_unverified`, `wide_table_parameter_units_unresolved`, `quality_flags_unverified`, `attribution_review_pending`; CRS de ESTE/NORTE sin resolver; la consulta institucional sigue pendiente. **Bloqueada** para la muestra; no se redescargó nada.

## Semántica temporal declarada por producto (resumen R3)

| Producto | Tiempo observado/válido | Emisión/adelanto | Disponibilidad de publicación |
| --- | --- | --- | --- |
| SENAMHI GBON | fecha + hora publicadas; reloj y posición del intervalo por confirmar con diccionario | no aplica | fecha de actualización del recurso (08/09/2025); `available_at` horario no documentado |
| NOAA ISD | `DATE` ISO-8601 UTC por registro (declarado); posición inicio/fin no documentada; sin contenido adquirido para conciliar | no aplica (observación) | sin declaración revisada |
| Open-Meteo Historical (ERA5) | marca horaria UTC; posición inicio/fin no declarada | no aplica (reanálisis) | ~5 días según tabla oficial |
| Open-Meteo Previous Runs | tiempo válido (marca horaria UTC) | emisión = válido − N×24 h (declarado) | archivo declarado por modelo (GFS desde 03/2021); `available_at` horario no documentado |
| ERA5 CDS | horario; ERA5T vs final 2–3 meses | no aplica | ~5 días |
| NASA POWER | horario UTC o LST (parámetro) | no aplica | GEOS-IT ~2 días; MERRA-2 reajustes periódicos |
| OEFA | fechas seriales sin época confirmada | no aplica | pendiente (bloqueos citados) |

`acquired_at` (momento de la descarga por AirAware) no se usa como `available_at` del proveedor
en ningún caso; los manifiestos de adquisición registran `acquired_at`/`verified_at` solo como
procedencia local.

## Derechos y atribución por producto seleccionado

Convención adoptada: los términos declarados de una licencia se citan como evidencia, pero el
campo `redistribution` del catálogo registra la **decisión del proyecto**, no el texto legal de
la licencia. Por eso todas las fuentes meteorológicas mantienen `redistribution: unknown` en
`configs/sources.yaml` mientras no exista una decisión explícita de integración (#17); lo
desconocido no se completa por inferencia. (Contraste: las fuentes SENAMHI de calidad de aire ya
integradas tienen su decisión registrada; no se cambian aquí.)

- Open-Meteo (ambas API): CC-BY-4.0 declarada por el proveedor del servicio; los términos exigen
  atribución con enlace y restringen la API gratuita a uso no comercial (10 000 llamadas/día).
  Fuentes upstream conservan sus licencias (Copernicus C3S para ERA5; NOAA NCEP para GFS). La
  atribución se registrará en DATA_ATTRIBUTION.md al integrarse en #17; esta muestra solo
  verifica la fuente.
- NOAA NCEI ISD: licencia sin declaración oficial verificada en este intento; sin datos
  adquiridos (bloqueo por techo de bytes). Atribución del producto («Global Hourly - Integrated
  Surface Database, NOAA NCEI») quedará registrada en informes solo si se adquiere;
  redistribución: unknown hasta evidencia documental.
- SENAMHI GBON: ODC-BY declarada (ficha y CKAN), cuyo texto permite redistribución con
  atribución; diferida, sin datos adquiridos y sin decisión de proyecto registrada.

## Limitaciones transversales

1. Ningún producto muestreado equivale a una medición en las estaciones de aire; la reanálisis
   representa celdas de ~25 km (ERA5) o ~½°×⅝° (MERRA-2) y el ISD mide en el aeropuerto.
2. La posición del intervalo horario (inicio/fin) no está documentada por Open-Meteo ni por ISD
   en las páginas revisadas; queda explícita como desconocida.
3. Las licencias sin evidencia (ISD, NASA POWER, campos OEFA) no se completan por inferencia.
4. Las decisiones de esta página son para #16 (verificación de fuente y muestra); la selección
   operativa de covariables para #17 requiere su propia aprobación y evidencia de disponibilidad.
