# FIRMS (NASA): investigación documental de la variable de contexto de incendios

Tarea: [#34 — Evaluar incendios, movilidad y otras variables de contexto opcionales](https://github.com/keneth-arias/airaware/issues/34). Refs #34.
Revisión: 20/11/2026 UTC. Alcance: solo documentación oficial; sin descargas de datos ni
muestras, sin cuentas nuevas y sin claves. Esta entrega investiga la fuente y propone; la
implementación de adquisición espera los acuerdos de #33 y la comparación contra la
referencia de #25 queda pendiente hasta disponer de entradas verificadas. El catálogo
(`configs/sources.yaml`) y el registro de acceso (`metadata/source-access.json`) se
actualizan en un cambio coordinado posterior.

Producto elegido: **NASA FIRMS (Fire Information for Resource Management System)**, el
servicio de la NASA que distribuye detecciones de incendios activos y anomalías térmicas de
los instrumentos MODIS (Moderate Resolution Imaging Spectroradiometer, a bordo de Terra y Aqua)
y VIIRS (Visible Infrared Imaging Radiometer Suite, con series de S-NPP, NOAA-20 y NOAA-21), con archivo histórico público. Es una fuente **satelital de
detección por pasada**: cada registro proviene de una observación térmica del satélite en
un momento concreto, y no es una medición de estación ni un producto de modelado.

## Método y herramienta de consulta

Este entorno de ejecución no tenía Lightpanda disponible (no existe el binario ni una sesión
compartida). La regla de [web-access](../web-access.md) exige no cambiar de herramienta en
silencio: se usó `curl` HTTP puntual y documentado como alternativa explícita, con URL, fecha
UTC, código HTTP y resultado registrados abajo. La consulta inicial hizo 12 solicitudes: 5 con
respuesta 200, 2 con error de aplicación (400 de endpoints sin parámetros) y 5
fallos documentados (403 de CloudFront en tres URLs del host `earthdata.nasa.gov`, 404 de la
ruta histórica de la FAQ y fallo de cadena TLS en `modis-fire.umd.edu`). Ninguna solicitud
descargó datos ni muestras. No hubo reintentos: cada URL se consultó una sola vez, dentro del
tope de 12 fetches; el host bloqueado no se insistió más allá de lo registrado y no se eludió
la validación del certificado TLS, prohibida por la política de acceso. La evidencia de esta
página es una captura fechada; los proveedores pueden cambiar enlaces y contenidos después de
la fecha de cada fila.

| # | URL consultada | Fecha UTC | HTTP | Resultado para esta revisión |
| --- | --- | --- | --- | --- |
| 1 | https://firms.modaps.eosdis.nasa.gov/ | 2026-11-20T11:43:30Z | 200 | Portal oficial: FIRMS distribuye datos NRT (tiempo casi real, Near Real-Time) de incendios activos de MODIS (Terra/Aqua) y VIIRS (NOAA-20/NOAA-21); «Globally these data are available within 3 hours of satellite observation»; formatos SHP, KML, TXT, WMS; FIRMS forma parte de NASA LANCE desde 2012; fue desarrollado por la Universidad de Maryland con fondos de NASA Applied Sciences y la FAO. |
| 2 | https://www.earthdata.nasa.gov/faq/firms-faq | 2026-11-20T11:43:30Z | 403 | Bloqueo CloudFront («ERROR: The request could not be satisfied … Request blocked»): el host de la FAQ rechazó la consulta anónima de este entorno. |
| 3 | https://firms.modaps.eosdis.nasa.gov/api/map_key/ | 2026-11-20T11:43:30Z | 200 | La API y los mapservices exigen un MAP_KEY gratuito solicitado por correo («sign up for free MAP_KEY using your email»); límite declarado de 5000 transacciones por intervalo de 10 minutos; las transacciones grandes pueden contar como varias (p. ej. pedir 7 días). |
| 4 | https://firms.modaps.eosdis.nasa.gov/download/ | 2026-11-20T11:43:30Z | 200 | Archive Download: archivo histórico de detecciones «older than the last 7 days» en SHP, CSV o JSON; autenticación por Earthdata Login o código enviado por correo; «NRT data are replaced with standard science quality data as they become available (with approximately a 5 month lag)»; cobertura temporal declarada por producto: MODIS Collection 6.1 desde 01/11/2000, VIIRS S-NPP 375 m del 20/01/2012 al 02/11/2026, VIIRS NOAA-20 375 m desde 01/04/2018, VIIRS NOAA-21 375 m desde 01/03/2023 y LANDSAT 30 m desde 20/06/2022; área quemada de MODIS/VIIRS distribuida por sftp de la Universidad de Maryland; enlaces a las guías de usuario (MODIS y VIIRS) y un resumen anual por país en CSV, no descargado. |
| 5 | https://www.earthdata.nasa.gov/data/tools/firms/faq | 2026-11-20T11:44:21Z | 403 | URL vigente de la FAQ de FIRMS, resuelta desde los enlaces del propio sitio (filas 1 y 4); mismo bloqueo CloudFront, esta vez con cabecera de navegador estándar declarada en la solicitud. |
| 6 | https://www.earthdata.nasa.gov/data/projects/lance | 2026-11-20T11:44:21Z | 403 | Página de LANCE en earthdata con las anclas «#ed-firms-citation» (citación de FIRMS) y «#ed-lance-disclaimer», enlazadas desde el portal y la página de descargas; mismo bloqueo CloudFront. El texto de citación y descargo queda sin capturar. |
| 7 | https://firms.modaps.eosdis.nasa.gov/api/areas/ | 2026-11-20T11:44:21Z | 400 | Cuerpo «Invalid API call.»: el endpoint existe pero exige parámetros; sin contenido documental en la respuesta. |
| 8 | https://firms.modaps.eosdis.nasa.gov/api/available_dates/ | 2026-11-20T11:44:22Z | 400 | Cuerpo «Invalid API call.»: igual que la fila 7. |
| 9 | https://firms.modaps.eosdis.nasa.gov/web-services/ | 2026-11-20T11:44:56Z | 200 | Página de servicios web sin contenido estático útil (se renderiza por JavaScript; solo título y recursos de interfaz): la referencia de los servicios queda como lectura pendiente. |
| 10 | https://modis-fire.umd.edu/ | 2026-11-20T11:44:56Z | 000 | curl error 60: cadena de certificados TLS incompleta en el sitio de productos de incendio de la Universidad de Maryland; no se reintentó ni se desactivó la verificación del certificado (prohibido por web-access). Las guías de usuario enlazadas desde la fila 4 viven en ese host. |
| 11 | https://firms.modaps.eosdis.nasa.gov/faq/ | 2026-11-20T11:45:45Z | 404 | Ruta histórica de la FAQ inexistente («Page not found»); la página de error remite a Fire Map, datos activos y descargas; la FAQ vigente vive en el host bloqueado (filas 2 y 5). |
| 12 | https://firms.modaps.eosdis.nasa.gov/content/manifest/firms.json | 2026-11-20T11:46:38Z | 200 | Manifiesto PWA del sitio (nombre corto, iconos y URL de inicio del mapa); sin contenido documental. Se conserva en el registro por honestidad del conteo. |

### Verificación posterior con Lightpanda

El 20/11/2026 UTC se abrieron las siguientes páginas oficiales. Las cuatro devolvieron
HTTP 200 con contenido y la URL final coincidió con la solicitada.

| Página y título | Evidencia revisada |
| --- | --- |
| [Archive Download - NASA / LANCE / FIRMS](https://firms.modaps.eosdis.nasa.gov/download/) | Fechas por producto y reemplazo del dato en tiempo casi real por la versión científica con unos cinco meses de retraso. |
| [Land, Atmosphere Near real-time Capability for Earth observation](https://www.earthdata.nasa.gov/data/projects/lance) | Reconocimiento de LANCE y descargo de responsabilidad. |
| [FIRMS / NASA Earthdata](https://www.earthdata.nasa.gov/data/tools/firms) | Pautas de atribución cuando se comparten datos o imágenes, y descargo aplicable a FIRMS. |
| [FIRMS FAQ / NASA Earthdata](https://www.earthdata.nasa.gov/data/tools/firms/faq) | Centro y tamaño nominal del píxel, confianza por instrumento, nubes, datos faltantes y latencia de entrega. |

## Resultado para el equipo

MODIS C6.1 y VIIRS S-NPP tienen cobertura temporal declarada durante toda la ventana de
Lima (01/01/2015 a 31/05/2024). NOAA-20 y NOAA-21 solo cubren parte del periodo. La
presencia de detecciones sobre una estación y la fecha de publicación de cada versión
siguen sin comprobarse. Solicitar la clave o el acceso por correo queda pendiente de autorización. Para incorporar la variable al pronóstico habrá que reconstruir lo que
ya estaba publicado en cada origen y medir su aporte sobre casos comparables con la
[referencia de Lima](../../reports/baselines/lima-pm25.md).

## (a) Clasificación explícita: qué es y qué no es FIRMS

- **FIRMS** es un sistema de distribución de la NASA dentro de **LANCE** (Land, Atmosphere
  Near real-time Capability for EO): «uses satellite observations from the MODIS and VIIRS
  instruments to detect active fires and thermal anomalies and deliver this information in
  near real-time» (portal, consultado el 20/11/2026). El producto se denomina «active fire /
  hotspot» (incendios activos / puntos calientes).
- **NRT frente a estándar**: hay dos calidades que no deben mezclarse. La NRT (tiempo casi
  real) está disponible globalmente «within 3 hours of satellite observation» (portal); la
  de **calidad estándar** (science quality) reemplaza a la NRT en el archivo con
  «approximately a 5 month lag» (página de descargas). La versión para cada origen se elige según su fecha de
  publicación verificable. El reemplazo posterior puede modificar una detección.
- **No es una medición de estación**: la unidad es una detección por pasada satelital con
  coordenada y hora, no una lectura en un punto fijo con continuidad horaria como SENAMHI.
- **No es un producto de modelado**: a diferencia del reanálisis CAMS EAC4 investigado en
  #33/PR #119, no hay modelo atmosférico entre la observación y el registro.
- **No es área quemada**: los productos de área quemada de MODIS/VIIRS son una línea distinta
  (distribuida por sftp de la Universidad de Maryland con credenciales publicadas en sus
  guías, según la página de descargas, consultada el 20/11/2026); su semántica post-evento es
  otra clase de variable y quedó postergada (véase (g)).

## (b) Licencia y condiciones de uso

- **Capturado con fecha**: la página del MAP_KEY declara el registro «free» por correo con
  un límite de 5000 transacciones por intervalo de 10 minutos (20/11/2026); la página de
  descargas declara autenticación por Earthdata Login o código por correo para el archivo
  histórico (20/11/2026); el portal declara que FIRMS forma parte de NASA LANCE (20/11/2026).
- **Atribución y uso.** La ficha de FIRMS de NASA Earthdata pide reconocer a FIRMS, a LANCE
  y al sistema de información de ciencias de la Tierra (ESDIS) al compartir datos o imágenes.
  También remite al descargo de responsabilidad del usuario. La FAQ pide acreditar las
  imágenes a NASA FIRMS. Las páginas se pudieron leer con Lightpanda durante la revisión.
- **Decisión del proyecto.** Antes de redistribuir un producto concreto, registrar su versión,
  la cita correspondiente y la decisión de Keneth sobre los derechos de uso. El campo
  `redistribution` del catálogo sigue pendiente.

## (c) Cobertura declarada (capturada el 20/11/2026 UTC)

| Propiedad | Declaración revisada |
| --- | --- |
| Cobertura geográfica | Global: «Globally these data are available within 3 hours of satellite observation» (portal); el mapa global y la pestaña GLOBAL del portal lo confirman. Perú y Lima quedan incluidas. La entrega en tiempo real inmediato («real-time») es un canal distinto y solo para EE. UU. y Canadá. |
| MODIS Collection 6.1 | 01/11/2000 – presente (página de descargas) |
| VIIRS S-NPP 375 m | 20/01/2012 – 02/11/2026 (página de descargas; la fecha de fin es la declarada por la fuente en la consulta y no se interpretó su motivo) |
| VIIRS NOAA-20 375 m | 01/04/2018 – presente (página de descargas) |
| VIIRS NOAA-21 375 m | 01/03/2023 – presente (página de descargas) |
| LANDSAT 30 m | 20/06/2022 – presente (página de descargas); no cubre la ventana histórica de Lima, se descarta para esta variable |
| Resolución espacial | Píxel nominal de aproximadamente 1 km para MODIS y 375 m para VIIRS. La coordenada señala el centro. El tamaño real varía con el barrido (FAQ, 20/11/2026) |
| Resolución temporal | Detecciones por pasada del satélite; disponibilidad NRT global dentro de ~3 horas de la observación; el archivo histórico contiene lo anterior a los últimos 7 días (página de descargas) |
| Actualización del archivo | NRT se reemplaza por calidad estándar con aproximadamente 5 meses de desfase (página de descargas) |
| Formatos | SHP, KML, TXT (texto separado por comas), JSON y WMS (portal y página de descargas) |
| Ventana de Lima (2015-01-01 a 2024-05-31) | Completa en las fechas declaradas de MODIS C6.1 y VIIRS S-NPP. Parcial para NOAA-20 desde abril de 2018 y NOAA-21 desde marzo de 2023 |

Cobertura temporal y procedencia: las fechas anteriores son las **declaradas** por la fuente
en la página de descargas de este entorno; que el archivo responda peticiones reales sobre
Lima en esa ventana se demostrará con acceso autorizado, no se afirma aquí.

## (d) Qué representa un registro: detección térmica, no incendio confirmado

- Un registro es una **detección térmica** (anomalía de brillo/temperatura observada por
  MODIS o VIIRS en una pasada, con coordenada, marca de tiempo, instrumento y nivel de
  confianza). El propio portal describe el producto como «active fire / hotspot data» y
  atribuye las detecciones a «thermal anomalies» (consultado el 20/11/2026).
- La coordenada ubica el centro de un píxel con una anomalía térmica candidata. Confirmar
  un incendio en terreno requiere evidencia adicional. La FAQ describe confianza de 0 a
  100 % para MODIS y categorías baja, nominal y alta para VIIRS. Conservar el campo y el
  instrumento al comparar detecciones.
- La cobertura depende de la pasada, las nubes y los datos faltantes. Un archivo vacío o
  una hora sin registros no demuestra ausencia de incendios. Para contar cero detecciones
  se necesita evidencia de observación utilizable del área durante la ventana. Si falta,
  registrar cobertura desconocida. Esta revisión documental no midió detecciones en Lima.

## (e) Vía de acceso (documentada; sin descargas ni cuentas)

- **Servicios en vivo con MAP_KEY**: la API y los mapservices exigen un MAP_KEY solicitado
  por correo; la clave se envía al correo registrado («The key will be sent to your email»).
  Límite declarado de 5000 transacciones por intervalo de 10 minutos, y las transacciones
  grandes (p. ej. 7 días) pueden contar como varias (página map_key, 20/11/2026). Los
  endpoints observados (`api/areas/`, `api/available_dates/`) responden «Invalid API call.»
  sin parámetros (filas 7 y 8); la referencia completa de los servicios se publica en una
  página renderizada por JavaScript (fila 9) y queda como lectura pendiente.
- **Archivo histórico**: la página de descargas entrega las detecciones con más de 7 días en
  SHP, CSV o JSON tras autenticarse con Earthdata Login o con un código enviado por correo
  (20/11/2026). También ofrece un resumen anual por país en CSV, no descargado en esta
  entrega. El tamaño de los archivos del archivo histórico no se midió ni está declarado en
  las páginas capturadas (medirlo exigiría iniciar una solicitud de descarga o recorrer el
  almacén): no se afirma tamaño.
- **Pendiente de autorización**: obtener el MAP_KEY exige registrar un correo y el archivo
  admite Earthdata Login o un código por correo. No se creó cuenta, no se pidió
  clave y no se descargó nada. Quedan registrados como **pendientes de autorización de
  Keneth**, con el mismo tratamiento que la cuenta del ADS (#33/PR #119) y la clave de
  OpenAQ (#31/PR #116). La adquisición futura será el descargador reproducible acotado de
  #6/#7 por región y ventana temporal, separada de la conversión local.

## (f) Utilidad para el pronóstico (evaluación honesta; nada ejecutado)

- **Cómo entraría la variable**: como una agregación espacial acotada alrededor de las
  estaciones de la referencia. Por ejemplo, por estación y ventana temporal retroactiva
  (p. ej. 24–72 h), contar las detecciones dentro de un radio fijo en torno a la estación y
  separar por producto (MODIS frente a VIIRS) para no mezclar calidades de pixel. Estos
  valores son ejemplos de diseño para discutir, no decisiones: el radio y la ventana se
  fijarían con evidencia y revisión en la entrega de adquisición.
- **Disponibilidad en el origen.** Conservar hora de observación, producto, versión y
  evidencia de cuándo se publicó esa versión. Una detección solo entra si ya se había
  observado y publicado al emitir el pronóstico. Las tres horas de la entrega casi en
  tiempo real son una estimación del servicio. El archivo estándar puede contener una
  revisión publicada meses después. Si solo se conserva esa revisión y se desconoce su
  fecha de publicación, excluirla de la entrada y registrar la pérdida de cobertura.
- **Comparación pendiente**: el aporte real se medirá como configuración con y sin la
  variable sobre los mismos casos de la referencia fija (persistencia y las otras dos
  referencias de [reports/baselines/lima-pm25.md](../../reports/baselines/lima-pm25.md);
  2 033 352 objetivos entre las tres particiones). Registrar cuántos objetivos de prueba
  conservan cobertura y comparar ambas configuraciones sobre esos mismos identificadores. Este PR no ejecuta esa comparación ni
  anticipa resultados.
- **Criterio de postergación**: si el acceso autorizado no demuestra disponibilidad histórica
  real del archivo para la ventana de Lima, la fuente se posterga, como exige la issue #34
  para las fuentes sin respaldo.

## (g) Por qué esta fuente y no otra

Criterios aplicados por esta revisión (evidencia fechada arriba):

1. **Disponibilidad histórica declarada**: el archivo cubre la ventana de Lima completa con
   MODIS C6.1 y VIIRS S-NPP (fechas capturadas en la fila 4), cosa que las alternativas no cumplen
   o no declaran en páginas públicas verificadas en esta revisión.
2. **Costo de acceso**: gratuito con barrera solo de registro (MAP_KEY «free», Earthdata
   Login); la barrera es una autorización pendiente, no un pago ni un servicio contratado.
3. **Formato y adquisición acotada**: CSV/JSON/SHP permiten pedir región y ventana por
   fecha; el límite de tasa declarado (5000 transacciones/10 min) deja margen para una
   adquisición acotada por bbox y fechas con el descargador de #6/#7.
4. **Respaldo institucional**: FIRMS es de NASA (LANCE) y ya figura como candidato oficial de
   incendios en [docs/sources.md](../sources.md), que exige exactamente esta verificación.

Alternativas con su motivo registrado:

- **Movilidad/tránsito**: postergada en esta entrega. #34 limita la recolección masiva y la
  contratación de servicios.
  [senamhi-reference-adaptation.md](senamhi-reference-adaptation.md) ya señalaba que una
  covariable de movilidad exige fecha de disponibilidad declarada y no introducir información
  futura, y el inventario la mantiene como línea de investigación sin fuente concreta.
  Alternativa por ahora: ninguna.
- **CAMS EAC4** (investigada en #33/PR #119): clase distinta (reanálisis de modelado de
  composición, no detecciones de eventos); complementaria, cubierta por otra entrega.
- **Área quemada de MODIS/VIIRS (UMD)**: semántica post-evento con otra unidad y una
  distribución por sftp cuyas condiciones no pudieron verificarse (fallo TLS, fila 10);
  postergada.
- **LANDSAT 30 m en FIRMS**: solo desde el 20/06/2022 (fila 4); no cubre la ventana histórica
  de Lima; descartado para esta variable.
- **AOD de MODIS o Sentinel-5P TROPOMI**: candidatos del inventario sin revisar en esta
  entrega; #33 ya registró AOD de MODIS como alternativa sin revisar.

## (h) Límites explícitos

1. **Confianza.** Cada instrumento publica su propia escala. El umbral para Lima sigue pendiente.
2. **Uso del producto.** La atribución general está documentada en (b). Queda por revisar
   la cita del producto elegido y acordar una eventual redistribución.
3. **Resolución.** Las coordenadas y tamaños nominales de píxel limitan la precisión espacial de
   la asociación con una estación.
4. **Versiones históricas.** Falta demostrar qué versión estaba disponible en cada origen.
5. **Densidad de detecciones sobre Lima sin verificar**: sin descargas no hay conteo de
   registros por día en la región; la utilidad real se demuestra en la comparación de (f).
6. **Fin declarado de VIIRS S-NPP (02/11/2026)**: es la fecha que publicó la fuente en la
   consulta; el motivo no se interpretó y queda pendiente de los anuncios oficiales.
7. **Documentación parcial de la API**: la referencia de servicios es una página de
   JavaScript sin contenido estático (fila 9); el contrato exacto de `api/areas/` y
   `api/available_dates/` sigue sin leerse.
8. **Umbrales propuestos, no adoptados**: los radios y ventanas de (f) son diseño para
   discutir; nada quedó fijado en configs/ ni en el código.

## Pendientes registradas

- Autorización de Keneth para el correo con MAP_KEY y/o la cuenta Earthdata Login (mismo
  tratamiento que la cuenta ADS de #33 y la clave de OpenAQ de #31). Sin cuentas nuevas por
  parte de agentes.
- Registrar con el producto elegido la cita específica y las condiciones de la versión.
- Revisar las guías de usuario para decidir cómo evaluar la confianza y las falsas alarmas
  en la región seleccionada.
- Lectura de la documentación de la API de FIRMS y diseño del descargador reproducible
  acotado por región y ventana con los controles de #6/#7.
- Comparación con y sin la variable contra la referencia fija de
  [#25](../../reports/baselines/lima-pm25.md), cuando #33 y la evidencia de disponibilidad lo permitan.
- Alta de la fuente en `configs/sources.yaml` y en `metadata/source-access.json` en un
  cambio coordinado con revisión; esta entrega no editó esos archivos.
