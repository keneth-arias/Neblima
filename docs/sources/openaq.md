# OpenAQ Perú: investigación documental y plan de solapamientos

Tarea: [#31 — Investigar OpenAQ Perú y duplicaciones de agregadores](https://github.com/keneth-arias/airaware/issues/31).
Revisión: 20/11/2026 UTC. Alcance: solo documentación oficial; sin descargas de mediciones,
sin cuentas nuevas y sin claves. Esta entrega propone; el catálogo (`configs/sources.yaml`) y el
registro de acceso (`metadata/source-access.json`) se actualizan en un cambio coordinado.

## Método y herramienta de consulta

Este entorno de ejecución no tenía Lightpanda disponible (no existe el binario ni una sesión
compartida). La regla de [web-access](web-access.md) exige no cambiar de herramienta en silencio:
se usó `curl` HTTP puntual y documentado como alternativa explícita, con URL, fecha UTC, código
HTTP y resultado registrados abajo. Fueron 10 solicitudes en total, ninguna descargó mediciones;
no se crearon cuentas ni se solicitaron claves. No hubo reintentos: ninguna consulta falló por red.
La evidencia de esta página es una captura fechada; los proveedores pueden cambiar enlaces y
contenidos después de la fecha de cada fila.

| # | URL consultada | Fecha UTC | HTTP | Resultado para esta revisión |
| --- | --- | --- | --- | --- |
| 1 | https://docs.openaq.org/ | 2026-11-20T11:15:26Z | 200 | Portada de la documentación; enlaza el índice `sitemap-index.xml`. |
| 2 | https://docs.openaq.org/sitemap.xml | 2026-11-20T11:15:41Z | 404 | Ruta inexistente; el sitio expone `sitemap-index.xml` en su lugar. |
| 3 | https://docs.openaq.org/sitemap-index.xml | 2026-11-20T11:15:50Z | 200 | Apunta a `sitemap-0.xml`. |
| 4 | https://docs.openaq.org/sitemap-0.xml | 2026-11-20T11:15:54Z | 200 | 74 páginas documentales; definió las consultas 5–9. |
| 5 | https://docs.openaq.org/using-the-api/api-key | 2026-11-20T11:16:32Z | 200 | Clave obligatoria en el encabezado `X-API-Key`; alta en `explore.openaq.org/register`. |
| 6 | https://docs.openaq.org/aws/about | 2026-11-20T11:16:32Z | 200 | Estructura del bucket `openaq-data-archive` (S3) y del archivo por ubicación. |
| 7 | https://docs.openaq.org/about/faq | 2026-11-20T11:16:54Z | 200 | Licencias por fuente original y criterios de ingesta de OpenAQ. |
| 8 | https://docs.openaq.org/resources/locations | 2026-11-20T11:16:54Z | 200 | Campos del recurso `locations` (proveedor, propietario, coordenadas, sensores, licencias). |
| 9 | https://docs.openaq.org/resources/providers | 2026-11-20T11:17:18Z | 200 | Campos del recurso `providers` y distinción proveedor/propietario. |
| 10 | https://api.openaq.org/v3/locations?limit=1 | 2026-11-20T11:17:18Z | 401 | Cuerpo: `{"message": "Unauthorized. A valid API key must be provided in the X-API-Key header."}` |

La consulta 10 es la verificación anónima acordada para #31: sin clave, la API v3 responde 401.
Ese resultado se registra como bloqueo verificado, no como indisponibilidad del proveedor.

## Resultado para el equipo

OpenAQ es un agregador: recompila datos de agencias gubernamentales y otras fuentes, y la licencia
aplicable de cada ubicación es la de su fuente original. Consultar sus datos exige una clave de API
(verificada: 401 anónimo) y obtener esa clave exige crear una cuenta, lo que este proyecto reserva a
la autorización de Keneth. Sin clave no hay evidencia citable hoy de proveedores ni ubicaciones
peruanas en OpenAQ: el explorador falló en la revisión previa del 16/11/2026 y la API no responde
sin clave. Por tanto esta entrega no afirma conteos, nombres de proveedores peruanos ni cobertura;
deja documentados el método de enumeración, el plan de medición de solapamientos contra SENAMHI
Lima y OEFA EAS, y la decisión de integración condicionada a esa clave. El archivo mundial de S3
no se descarga ni se lista: queda prohibido por política de descargas y no aporta la evidencia
peruana, que vive en los metadatos de la API.

## (a) API v3: funcionamiento y requisito de clave

- La API v3 de OpenAQ es una API REST en `https://api.openaq.org/v3/` con recursos jerárquicos:
  countries, locations, sensors, measurements (por sensor), providers, owners, manufacturers,
  instruments, parameters y licenses (sitemap del 20/11/2026, consultas 4 y 8).
- Toda solicitud requiere autenticación: «The OpenAQ API uses API keys to authenticate requests
  and manage access» (docs.openaq.org/using-the-api/api-key, consultado el 20/11/2026). La clave
  viaja en el encabezado `X-API-Key` de cada pedido.
- La clave se obtiene registrándose en `explore.openaq.org/register` y se rota en la cuenta del
  explorador. Crear esa cuenta es una cuenta nueva: según las reglas del proyecto requiere
  autorización que este intento no tiene. No se creó ninguna cuenta ni se pidió clave.
- Bloqueo verificado: la llamada anónima `GET /v3/locations?limit=1` respondió HTTP 401 con el
  cuerpo citado en la tabla (20/11/2026T11:17:18Z). Cualquier plan de consultas queda detenido
  hasta tener una clave autorizada.
- Para Perú el recorrido documentado (no ejecutado) sería: `GET /v3/countries` para resolver el
  país con código ISO 3166-1 alpha-2 `PE`, y después `GET /v3/locations` filtrado por ese país,
  con paginación y respetando los límites de tasa. Los detalles de límites de tasa no se
  consultaron en esta entrega (la página `using-the-api/rate-limits` queda como lectura pendiente).

## (b) Archivo histórico en S3: estructura y por qué no se descarga

Según docs.openaq.org/aws/about (consultado el 20/11/2026):

- La raíz pública es `https://openaq-data-archive.s3.amazonaws.com/`.
- Particionado estilo Apache Hive bajo `records/csv.gz/`:
  `records/csv.gz/locationid={id}/year={aaaa}/month={mm}/location-{id}-{aaaammdd}.csv.gz`;
  ejemplo documentado: `/records/csv.gz/locationid=2178/year=2022/month=05/location-2178-20220503.csv.gz`.
- Cada archivo comprimido (csv.gz) guarda las mediciones de **todos los sensores de una ubicación
  en un día** (formato estrecho). Columnas: `location_id`, `sensors_id`, `location`, `datetime`
  (ISO-8601 con desfase de zona), `lat`, `lon` (EPSG:4326), `parameter`, `unit`, `value`.
- Los archivos se escriben 72 horas después del cierre del día en la zona de la ubicación y pueden
  corregirse retroactivamente. Hay tema SNS de creación de objetos y guía de consulta con Athena.

Por qué no se descarga el archivo mundial:

1. Es el acopio histórico global de OpenAQ, sin índice de Perú en las rutas: las particiones son
   por `locationid` numérico, y los IDs peruanos son precisamente lo que no sabemos sin la API.
   Listar el bucket completo para descubrirlos sería un recorrido sin límite, prohibido por las
   reglas de descargas del proyecto.
2. La política vigente reserva descargas costosas o sin límites a autorización del plan. El tamaño
   mundial no se midió (medirlo exigiría recorrer el bucket) y no se necesita para decidir: basta
   la estructura documentada arriba.
3. La ruta correcta y acotada, cuando haya clave, es enumerar primero las ubicaciones peruanas
   vía API y descargar solo los prefijos `locationid={id}` de los candidatos del plan de
   solapamientos, con el descargador reproducible acotado previsto en #6/#7. No se ejecutó aquí.

## (c) Licencias: qué declara OpenAQ y qué depende del proveedor primario

De la sección de licencias de docs.openaq.org/about/faq (consultado el 20/11/2026):

- «OpenAQ aggregates air quality data from government agencies and other sources worldwide. The
  data on our platform come with different licensing terms … depending on the original source.»
  La licencia efectiva de cada ubicación la fija la fuente original, no OpenAQ.
- La API expone la licencia relevante por ubicación de monitoreo (recurso `licenses`; el recurso
  `locations` incluye una lista de licencias con información de atribución y periodo de vigencia).
- El usuario es responsable de revisar y cumplir los términos del propietario original; muchas
  fuentes exigen atribución (licencias Creative Commons, licencias de gobierno abierto o términos
  propios). También hay que acreditar a OpenAQ como punto de acceso.
- OpenAQ avisa que solo agrega datos que cree disponibles para redistribución pública, pero «we
  cannot guarantee that all data is free from third-party claims»; el cumplimiento legal es
  responsabilidad del usuario.

Criterios de ingesta declarados (misma página, misma fecha): OpenAQ solo incorpora datos con
licencia abierta (ejemplos citados: CC0, CC BY 4.0), que reporten concentraciones (no índices de
calidad del aire), con coordenadas y fechas completas, frecuencia entre 10 minutos y 24 horas,
estacionarios y a nivel del suelo; prioriza PM2.5, PM10, NO2, NOx, NO, O3, SO2, CO y BC con la
temperatura y humedad relativa que acompañen a la fuente.

Consecuencia para Perú: si OpenAQ ingesta datos de SENAMHI u OEFA, la licencia de esas copias sería
la de cada proveedor primario (el catálogo nacional declara ODC-By para los conjuntos SENAMHI y
OEFA, según la revisión de #3/#4/#5), más la atribución a OpenAQ como canal. Qué licencias tiene
registradas OpenAQ para ubicaciones peruanas se consulta con clave vía `/v3/licenses` y el campo
`licenses` de cada ubicación: queda pendiente y sin afirmar.

## (d) Proveedores y ubicaciones de Perú: evidencia disponible

Esta entrega no aporta evidencia nueva de ubicaciones peruanas y no afirma ninguna:

- El explorador `explore.openaq.org` fue revisado el 16/11/2026 con Lightpanda y respondió HTTP 200
  con la aplicación en error («Error | Uncaught Client Exception»); registro
  `openaq-explorer` en `metadata/source-access.json`, resultado `partial`. Esa revisión no confirmó
  cobertura peruana.
- La API v3 exige clave (bloqueo verificado en la consulta 10 de esta revisión), y las páginas
  documentales consultadas no publican listas de países, proveedores ni ubicaciones: esos listados
  viven en los propios extremos de la API.
- El archivo S3 no permite identificar países sin recorrer particiones por ID numérico (ver b),
  recorrido prohibido.

Con evidencia citable solo queda esto: las condiciones de ingesta declaradas (concentraciones
horarias o subhorarias de estaciones fijas con licencia abierta) describen el tipo de fuente que
OpenAQ incorpora, y las redes oficiales peruanas que ya usamos (SENAMHI Lima, horaria, 2015–2024;
OEFA EAS, declarada horaria, 2018–2021) encajan en esa descripción. Que OpenAQ efectivamente haya
ingerido alguna de esas fuentes es una hipótesis a verificar con clave, no un resultado. La
enumeración documentada en (a) es la primera consulta pendiente tras una clave autorizada.

## (e) PLAN de medición de solapamientos (no ejecutado)

Objetivo: clasificar cada serie peruana que OpenAQ exponga frente a las identidades provisionales
de AirAware, siguiendo la política de #14 (una copia demostrada de un agregador cede precedencia
al registro original y conserva su vínculo; las mediciones independientes quedan en series
distintas y una fusión requiere evidencia institucional fechada).

Identidades de referencia actuales de AirAware:

| Fuente | Identidad provisional | Serie | Ventana declarada |
| --- | --- | --- | --- |
| SENAMHI Lima (senamhi-lima) | `station_key` = SHA-256 del ID de fuente más la lista JSON ordenada de estación, longitud, latitud, altitud, departamento, provincia y distrito; siete identidades vigentes | PM2.5, PM10, NO2 horarios en UTC (ADR-005) | 2015-01-01 a 2024-05-31 (extremos textuales del CSV) |
| OEFA EAS (oefa-eas-aire) | `NOMBRE_EVALUACION` y códigos de estación; coordenadas UTM `ESTE`/`NORTE`/`ZONA`/`DATUM` con WGS84 observado | Parámetros horarios con `ug/m3` | 2018–2021 declarado por la fuente; zona horaria pendiente (#5/#11) |

Pasos previstos, cada consulta con URL, fecha UTC y resultado registrados:

1. **Enumeración (con clave autorizada).** Resolver el país `PE` con `GET /v3/countries`; listar
   sus ubicaciones con `GET /v3/locations` paginado. Capturar por ubicación: `id`, `name`,
   `country.code`, `coordinates` (WGS84), `provider`, `owner`, `sensors` (parámetro y unidades),
   `licenses`, `timezone`, `isMobile`, `isMonitor` (campos según el recurso `locations`,
   consultado el 20/11/2026).
2. **Rastreo al proveedor primario.** En OpenAQ, `provider` es quien facilita los datos y `owner`
   quien los posee o los produce; pueden coincidir o no (recurso `providers`, 20/11/2026). El
   cruce es contra `owner` (agencia responsable), con `provider` como antecedente del canal.
   Una ubicación cuyo `owner` sea SENAMHI u OEFA es candidata a copia de una fuente que AirAware
   ya tiene; un `owner` distinto (gobierno local, red independiente) abre línea propia.
3. **Candidatos espaciales.** Comparar `coordinates` (WGS84 decimal) contra las identidades:
   SENAMHI ya tiene latitud/longitud en sus campos de identidad; para OEFA hay que convertir UTM
   (zonas 17/18/19 observadas en informes de #5) tras decidir el CRS, pendiente en #5/#11.
   Umbrales de radio (p. ej. 100 m, 500 m, 2 km) solo generan **candidatos**, nunca identidad.
4. **Comparación de series en ventana acotada.** Para cada par candidato con parámetro y unidades
   comparables (conversión documentada si difieren), alinear por hora en UTC según el `timezone`
   de OpenAQ y la convención ya confirmada de la fuente AirAware, en una ventana con solape real
   (p. ej. un trimestre de 2021, donde coinciden SENAMHI y la cobertura EAS declarada). Datos de
   OpenAQ: preferir el archivo S3 público por `locationid` (estructura en (b)) para no gastar
   cuota de API; alternativamente `GET /v3/sensors/{id}/hours`. Presupuesto acotado: enumeración
   de unas pocas páginas más una descarga por ubicación candidata y mes de ventana; sin recorrer
   el archivo mundial.
5. **Clasificación por rama del resultado:**
   - Coincidencia exacta o trivialmente redondeada en el solape → **copia del oficial**: la serie
     OpenAQ cede precedencia ante el registro original de AirAware y se conserva su vínculo y
     atribución; no suma observaciones independientes.
   - Valores distintos en la misma ubicación y hora → **independencia sin demostrar**: puede ser
     otro instrumento (`isMonitor`), una reubicación o diferencias de control de calidad; exige
     evidencia institucional fechada antes de tratarla como sensor independiente.
   - Sin solape temporal ni espacial → **sin conclusión**: se documentan las ventanas y no se
     fusiona ni se descarta nada.

Artefacto propuesto (no generado en esta entrega): `reports/source-overlap.parquet`, una fila por
par fuente–ubicación con `airaware_source`, identidad AirAware, `openaq_location_id`,
`openaq_sensor_id`, parámetro, unidad, ventana UTC comparada, horas comparadas, fracción de
coincidencia exacta, error absoluto medio y rama resultante con evidencia (URL y fechas). Se
genera solo cuando existan datos reales medidos con este método; sin clave no hay archivo.

## (f) Decisión de integración

- **No se integra OpenAQ en esta entrega.** Sin clave no hay evidencia de cobertura peruana ni de
  solapamientos, y sin esa evidencia cualquier integración violaría la regla de #31: demostrar
  solapamientos antes de considerar independientes las observaciones.
- **Queda bloqueado y quién lo desbloquea:** crear la cuenta y obtener la clave de API v3 exige
  una cuenta nueva, decisión que corresponde a Keneth conforme a las autorizaciones del plan. La
  alternativa del archivo S3 sin clave no resuelve el bloqueo: sin IDs de ubicación peruanos, el
  único camino sería recorrer el bucket mundial, prohibido.
- **Qué se puede avanzar sin clave:** esta documentación (estructura de API y archivo, licencias,
  método de solapamiento y esquema del artefacto); nada de datos. La entrada `openaq-explorer`
  sigue `discovered` en el catálogo y así se propone conservarla hasta la verificación con clave.
- **Tras una clave autorizada**, el orden sería: enumeración acotada de Perú (a), rastreo de
  `owner` y solapamientos según (e), revisión de Keneth del resultado, y solo entonces la
  decisión de integración y precedencia, coordinando el alta del catálogo y del registro de
  acceso en un cambio propio.

## Pendientes

1. Autorización de Keneth para cuenta y clave de API v3 (bloqueo verificado: 401 anónimo del
   20/11/2026). Sin cuenta nueva por parte de agentes.
2. Enumerar ubicaciones y proveedores peruanos con clave y registrar la evidencia en
   `metadata/source-access.json` a cargo de Keneth (esta entrega no editó ese archivo).
3. Leer `docs.openaq.org/using-the-api/rate-limits` y `about/terms` antes de diseñar el
   descargador acotado; no consultadas en esta revisión por el tope de 10 solicitudes.
4. Decidir el CRS y la conversión UTM→WGS84 de OEFA (pendiente de #5/#11) antes del paso 3 del plan.
5. Ejecutar el plan de solapamientos y generar `reports/source-overlap.parquet` solo con datos
   reales; hoy el archivo no existe y no debe crearse vacío.
