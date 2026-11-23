# OpenAQ Perú: investigación documental y plan de solapamientos

Tarea: [#31 — Investigar OpenAQ Perú y duplicaciones de agregadores](https://github.com/keneth-arias/Neblima/issues/31).
Revisión: 20/11/2026 UTC. Alcance: documentación oficial y evidencia local de #88; sin descargas de mediciones,
sin cuentas nuevas y sin claves. Esta entrega propone; el catálogo (`configs/sources.yaml`) y el
registro de acceso (`metadata/source-access.json`) se actualizan en un cambio coordinado.

## Método y herramienta de consulta

Este entorno de ejecución no tenía Lightpanda disponible (no existe el binario ni una sesión
compartida). La regla de [acceso web](../web-access.md) exige no cambiar de herramienta en silencio:
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

El archivo público de OpenAQ ya aportó datos de Lima a la [prueba externa de #88](../../reports/prueba-externa-pm.md).
Esa preparación documentó 27 inventarios anuales para nueve ubicaciones y 85 538 ventanas
completas de PM2.5 y PM10 a partir del 01/06/2024. La clave es necesaria para consultar
la interfaz de programación (API) v3 y ampliar el inventario nacional. Los identificadores,
sensores y recibos ya registrados permiten iniciar el rastreo de la muestra limeña sin clave.

Para #31 siguen pendientes la procedencia y los derechos por serie, así como la medición de
copias frente a las fuentes primarias. OpenAQ se mantiene separado por fuente en #88.

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
  cuerpo citado en la tabla (20/11/2026T11:17:18Z). Las consultas a esa API quedan detenidas
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
  en un día** (formato estrecho). La tabla documenta `location_id`, `sensor_id`, `location`, `datetime`
  (con desfase de zona), `lat`, `lon` (EPSG:4326), `parameter`, `unit` y `value`. El ejemplo
  de la misma página usa `sensors_id` y `units`. Comprobar la cabecera del original.
- Los archivos se escriben 72 horas después del cierre del día en la zona de la ubicación y pueden
  corregirse retroactivamente. Hay tema SNS de creación de objetos y guía de consulta con Athena.

Por qué no se descarga el archivo mundial:

1. Es el acopio histórico global de OpenAQ, sin índice de Perú en las rutas: las particiones son
   por `locationid` numérico. El manifiesto de #88 identifica ubicaciones concretas de Lima.
   Listar el bucket completo para descubrirlos sería un recorrido sin límite, prohibido por las
   reglas de descargas del proyecto.
2. La política vigente reserva descargas costosas o sin límites a autorización del plan. El tamaño
   mundial no se midió (medirlo exigiría recorrer el bucket) y no se necesita para decidir: basta
   la estructura documentada arriba.
3. Para los identificadores conocidos se pueden seleccionar objetos diarios de una ubicación.
   Para ampliar la lista se prevé consultar la API por país cuando se autorice una clave.
   En ambos casos se fijarán por adelantado los límites de objetos, bytes y fechas.

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
la de cada proveedor primario (los permisos documentados para el CSV histórico de SENAMHI y el CSV de seguimiento de OEFA
deben comprobarse de nuevo para cada producto republicado), más la atribución a OpenAQ como canal. Qué licencias tiene
registradas OpenAQ para ubicaciones peruanas se consulta con clave vía `/v3/licenses` y el campo
`licenses` de cada ubicación: queda pendiente y sin afirmar.

## (d) Proveedores y ubicaciones de Perú: evidencia disponible

El explorador devolvió una página de error el 16/11/2026 (`openaq-explorer` en
`metadata/source-access.json`). El 401 de la consulta 10 afecta a la API. El archivo
histórico tiene evidencia separada en el [manifiesto del 20/11/2026](../../metadata/lima-pm-externa-20261120.json).
En `datasets[source=openaq].stations` figuran, entre otros, estos pares de sensores:

| Ubicación de Lima | ID de ubicación | Sensor PM2.5 | Sensor PM10 | Ventanas completas de #88 |
| --- | ---: | ---: | ---: | ---: |
| Carabayllo | 2277 | 4171 | 4163 | 0 |
| Villa María del Triunfo | 2302 | 4165 | 4611 | 12 623 |
| San Juan de Lurigancho | 7464 | 23128 | 21669 | 12 607 |
| San Juan de Lurigancho | 6501061 | 17336555 | 17336560 | 3 |

Carabayllo tuvo observaciones. El cero cuenta ventanas bivariadas de 30 horas completas.
Las dos ubicaciones de San Juan de Lurigancho se conservan separadas. Estos identificadores
sustentan cobertura local. Para atribuir cada serie a una agencia y decidir si republica
mediciones oficiales hacen falta metadatos y una comparación trazable.

Contraste documental del 20/11/2026 UTC con Lightpanda. Las URL solicitadas y finales
coincidieron en ambas consultas (HTTP 200): [About Open Data on AWS](https://docs.openaq.org/aws/about)
confirma la partición diaria y la diferencia de cabeceras de (b);
[Locations](https://docs.openaq.org/resources/locations) documenta propietario, proveedor,
instrumentos y licencias por ubicación.

## (e) PLAN de medición de solapamientos (no ejecutado)

Objetivo: clasificar cada serie peruana que OpenAQ exponga frente a las identidades provisionales
de Neblima, siguiendo la política de #14 (una copia demostrada de un agregador cede precedencia
al registro original y conserva su vínculo; las mediciones independientes quedan en series
distintas y una fusión requiere evidencia institucional fechada).

Identidades de referencia actuales de Neblima:

| Fuente | Identidad provisional | Serie | Ventana declarada |
| --- | --- | --- | --- |
| CSV de SENAMHI Lima (`senamhi-lima-csv`) | `station_key` = SHA-256 del ID de fuente más la lista JSON ordenada de estación, longitud, latitud, altitud, departamento, provincia y distrito; siete identidades vigentes | PM2.5, PM10, NO2 horarios en UTC (ADR-005) | 2015-01-01 a 2024-05-31 (extremos textuales del CSV) |
| OEFA EAS ancho (`oefa-csv`) | `NOMBRE_EVALUACION` y códigos de estación; coordenadas de origen `ESTE`/`NORTE`/`ZONA`/`DATUM` con WGS84 observado | Parámetros horarios con `ug/m3` | 2018–2021 declarado por la fuente; zona horaria pendiente (#5/#11) |

Pasos previstos, cada consulta con URL, fecha UTC y resultado registrados:

1. **Inventario.** Partir de los identificadores y recibos de #88. Para ampliar la lista con clave
   autorizada, resolver el país `PE` con `GET /v3/countries` y listar sus ubicaciones con `GET /v3/locations` paginado. Capturar por ubicación: `id`, `name`,
   `country.code`, `coordinates` (WGS84), `provider`, `owner`, `sensors` (parámetro y unidades),
   `licenses`, `timezone`, `isMobile`, `isMonitor` (campos según el recurso `locations`,
   consultado el 20/11/2026).
2. **Rastreo al proveedor primario.** En OpenAQ, `provider` es quien facilita los datos y `owner`
   quien los posee o los produce; pueden coincidir o no (recurso `providers`, 20/11/2026). El
   cruce es contra `owner` (agencia responsable), con `provider` como antecedente del canal.
   Una ubicación cuyo `owner` sea SENAMHI u OEFA es candidata a copia de una fuente que Neblima
   ya tiene. Con otro propietario se conserva una identidad provisional hasta rastrear el origen.
3. **Candidatos espaciales.** Comparar `coordinates` (WGS84 decimal) contra las identidades:
   SENAMHI ya tiene latitud/longitud en sus campos de identidad; para OEFA hay que convertir UTM
   solo si hay evidencia del sistema de referencia de coordenadas aplicable al punto (#5/#30).
   Umbrales de radio (p. ej. 100 m, 500 m, 2 km) solo generan **candidatos**, nunca identidad.
4. **Comparación de series en ventana acotada.** Para cada par candidato con parámetro y unidades
   comparables, documentar la conversión de unidades y el intervalo medido. Alinear las horas
   en UTC usando el desfase publicado de OpenAQ solo cuando se conozca también el reloj de la
   otra fuente. Elegir el periodo a partir de los recibos con solape efectivo.
   Reutilizar primero los originales locales. Para ampliar la muestra, el archivo S3 ofrece
   un objeto diario por ubicación y la API ofrece `GET /v3/sensors/{id}/hours`. Fijar máximos
   de páginas, objetos y bytes antes de consultar.
5. **Clasificación por rama del resultado:**
   - Una coincidencia exacta o por redondeo identifica un candidato. Para clasificarlo como
     copia, documentar el origen común y la correspondencia entre instrumento, señal,
     unidad e intervalo según [la política de #14](../../tasks/issue-14-plan.md). Una copia
     demostrada cede precedencia al original y conserva el vínculo y la atribución.
   - Si los valores difieren, revisar instrumento, redondeo, reubicación y control de
     calidad. Conservar separadas las series mientras falte evidencia de identidad.
   - Si falta solape o el reloj de una fuente sigue sin resolver, registrar el motivo y
     dejar el resultado sin determinar.

Artefacto propuesto (no generado en esta entrega): `reports/source-overlap.parquet`, una fila por
par de series y ventana comparada con `airaware_source`, identidad Neblima, `openaq_location_id`,
`openaq_sensor_id`, parámetro, unidad, ventana UTC comparada, horas comparadas, fracción de
coincidencia exacta, error absoluto medio y rama resultante con evidencia (URL y fechas). Se
genera solo cuando existan datos reales medidos con este método; queda pendiente la comparación.

## (f) Decisión de integración y pendientes

La prueba externa de #88 conserva OpenAQ y SENAMHI en conjuntos separados. Para #31 sigue
pendiente demostrar la procedencia y medir el solapamiento antes de combinar series
o contabilizarlas como independientes.

1. Usar el manifiesto local para localizar los originales y elegir pares con horas
   comparables. Registrar el producto exacto de SENAMHI u OEFA, los relojes y las unidades.
2. Para ampliar el inventario nacional y verificar `owner`, `provider` y licencias por periodo,
   solicitar a Keneth autorización para la cuenta de la API v3. Revisar los límites de tasa y
   los términos antes de diseñar nuevas consultas.
3. Generar el informe de solapamientos únicamente con pares comparados y recibos trazables.
   La atribución y una eventual actualización del catálogo quedan para revisión de Keneth.
