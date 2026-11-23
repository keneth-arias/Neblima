# CAMS EAC4: investigación documental de información atmosférica complementaria

Tarea: [#33 — Probar información atmosférica y satelital complementaria](https://github.com/keneth-arias/Neblima/issues/33).
Revisión: 20/11/2026 UTC. Alcance: solo documentación oficial; sin descargas de datos ni
muestras, sin cuentas nuevas y sin claves. Esta entrega investiga la fuente y propone; la
implementación de adquisición espera #17/#25 y el catálogo (`configs/sources.yaml`) y el
registro de acceso (`metadata/source-access.json`) se actualizan en un cambio coordinado.

Producto elegido: **CAMS global reanalysis (EAC4)**, el reanálisis global de composición
atmosférica del Copernicus Atmosphere Monitoring Service (CAMS, servicio implementado por el
ECMWF dentro del programa Copernicus). Es una fuente de **modelado** (reanálisis con
asimilación de observaciones, incluidas recuperaciones satelitales): no es medición de
estación ni un producto satelital en sí mismo.

## Método y herramienta de consulta

Este entorno de ejecución no tenía Lightpanda disponible (no existe el binario ni una sesión
compartida). La regla de [web-access](../web-access.md) exige no cambiar de herramienta en
silencio: se usó `curl` HTTP puntual y documentado como alternativa explícita, con URL, fecha
UTC, código HTTP y resultado registrados abajo. Fueron 10 intentos HTTP en total (7 con
contenido, 1 error 404 corregido con la ruta oficial y 2 fallos de DNS en la misma URL de
licencias); ninguno descargó datos ni muestras. No hubo más reintentos que los registrados.
La evidencia de esta página es una captura fechada; los proveedores pueden cambiar enlaces y
contenidos después de la fecha de cada fila.

| # | URL consultada | Fecha UTC | HTTP | Resultado para esta revisión |
| --- | --- | --- | --- | --- |
| 1 | https://atmosphere.copernicus.eu/about-cams | 2026-11-20T11:31:57Z | 200 | Portal oficial de CAMS: «consistent and quality-controlled information related to air pollution and health … everywhere in the world»; implementado por ECMWF dentro de Copernicus. |
| 2 | https://confluence.ecmwf.int/display/CKB/CAMS+Global+Reanalysis+%28EAC4%29 | 2026-11-20T11:31:58Z | 404 | Ruta supuesta de Confluence inexistente; la página oficial válida se resolvió desde el enlace de documentación del ADS (fila 8). |
| 3 | https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4?tab=overview | 2026-11-20T11:31:59Z | 200 | Ficha ADS de EAC4: grilla global 0,75°×0,75°; 60 niveles modelo; cobertura 2003–2025 declarada; 3-hourly; GRIB con conversión opcional a NetCDF; DOI 10.24381/d58bbf47; licencia CC-BY; variables PM2.5 y AOD 550 nm. |
| 4 | https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4?tab=documentation | 2026-11-20T11:33:08Z | 200 | Pestaña de documentación: enlaza «CAMS Reanalysis data documentation» (Confluence), «Known issues», informes EQA y la cita de datos (Inness et al. 2019). |
| 5 | https://licences.copernicus.eu/licence-to-use-copernicus-products | 2026-11-20T11:33:09Z | 000 | Error de DNS («Could not resolve host»): el host de licencias Copernicus no resolvió; primer intento. |
| 6 | https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4-monthly?tab=overview | 2026-11-20T11:33:10Z | 200 | Ficha ADS del dataset de medias mensuales: DOI 10.24381/fd75fff2; licencia CC-BY (SPDX CC-BY-4.0 en el JSON del catálogo); tipos `monthly_mean` y `monthly_mean_by_hour_of_day`. |
| 7 | https://licences.copernicus.eu/licence-to-use-copernicus-products | 2026-11-20T11:33:18Z | 000 | Reintento único con el mismo error de DNS; el texto legal general de Copernicus queda sin descargar (véase «Licencia»). |
| 8 | https://confluence.ecmwf.int/x/OIX4B | 2026-11-20T11:33:38Z | 200 | Página oficial «CAMS Reanalysis data documentation» (Confluence CKB): resolución nativa ~80 km (T255/N128) interpolada a 0,75°×0,75° en ADS; 60 niveles híbridos con tope 0,1 hPa; asimilación 4D-Var con ventanas de 12 h; tabla de recuperaciones satelitales asimiladas con banderas de calidad y criterios de lista negra; problemas conocidos. |
| 9 | https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4-monthly?tab=overview | 2026-11-20T11:33:40Z | 200 | Duplicado accidental de la fila 6 (misma URL y contenido); se conserva en el registro por honestidad del conteo. |
| 10 | https://ads.atmosphere.copernicus.eu/datasets/cams-global-atmospheric-composition-forecasts?tab=overview | 2026-11-20T11:34:42Z | 200 | Ficha ADS de los pronósticos globales de CAMS (línea de producto distinta del reanálisis): 0,4°×0,4°; 2015–presente; corridas nuevas 00 y 12 UTC cada día; DOI 10.24381/04a0b097; CC-BY. |

## Resultado para el equipo

CAMS produce dos líneas globales de composición atmosférica que no deben mezclarse: los
**pronósticos globales** (modelado en tiempo casi real, corridas 00/12 UTC, grilla 0,4°×0,4°,
cobertura declarada desde 2015) y el **reanálisis EAC4** (pasado consolidado con asimilación,
grilla 0,75°×0,75°, desde 2003). Para Neblima el candidato es EAC4: ofrece historia
compatible con las ventanas del benchmark (2015) y cobertura global que incluye Lima. La
cuenta del Atmosphere Data Store (ADS) es obligatoria para descargar y está pendiente de
autorización de Keneth, igual que la clave de OpenAQ en #116: sin ella no hay evidencia de
descarga y esta entrega no afirma disponibilidad operativa.

## (a) Clasificación explícita: modelado, reanálisis y satélites

- **CAMS** es un servicio de modelado atmosférico: describe su información como
  «consistent and quality-controlled information related to air pollution and health, solar
  energy, greenhouse gases and climate forcing, everywhere in the world»
  (atmosphere.copernicus.eu/about-cams, consultado el 20/11/2026).
- **EAC4** («ECMWF Atmospheric Composition Reanalysis 4») es **reanálisis**: la cuarta
  generación del reanálisis global de composición del ECMWF. La ficha ADS lo define como la
  combinación de «model data with observations from across the world into a globally complete
  and consistent dataset», con asimilación 4D-Var en ventanas de 12 horas y salida cada
  3 horas (ADS EAC4, consultado el 20/11/2026). No es medición de estación ni pronóstico.
- **Satélites**: en EAC4 los satélites son **entrada de la asimilación**, no el producto. La
  documentación oficial lista las recuperaciones satelitales asimiladas (ozono, CO, NO2, AOD
  entre otros) con sus instrumentos y periodos (Confluence CKB, consultado el 20/11/2026).
  Un producto satelital de nivel 2 (p. ej. Sentinel-5P TROPOMI) sería una clase distinta y
  queda como alternativa sin revisar para #34.

## (b) Licencia y condiciones de uso

- La ficha ADS declara «Licence **CC-BY licence**» y su catálogo interno identifica la
  licencia con el identificador SPDX **CC-BY-4.0** (`"license": "CC-BY-4.0"` y enlace
  https://spdx.org/licenses/CC-BY-4.0 en el JSON de la ficha de EAC4 y del dataset mensual;
  consultado el 20/11/2026). La misma ficha declara
  `"conditionsOfAccess": "Free access upon acceptance of applicable licences and terms of
  use"` y `isAccessibleForFree: true`.
- Atribución declarada en la propia ficha ADS («Citation and attribution», consultado el
  20/11/2026): además de la licencia aplicable, el usuario **debe** «cite the ADS catalogue
  entry; provide clear and visible attribution to the Copernicus programme and attribute each
  data product used». El formato sugerido de cita es «Copernicus Atmosphere Monitoring
  Service (2020): CAMS global reanalysis (EAC4). Copernicus Atmosphere Monitoring Service
  (CAMS) Atmosphere Data Store, DOI: 10.24381/d58bbf47 (Accessed on DD-MMM-YYYY)». La cita
  científica del producto es Inness et al. (2019), Atmos. Chem. Phys., 19, 3515–3556,
  https://doi.org/10.5194/acp-19-3515-2019.
- **Fallo registrado**: el texto legal general de Copernicus
  (https://licences.copernicus.eu/licence-to-use-copernicus-products) no se pudo descargar:
  el host no resolvió por DNS en dos intentos (filas 5 y 7). La identificación CC-BY-4.0 de
  esta revisión proviene de las fichas ADS fechadas arriba, no de ese texto legal; este
  documento no completa vacíos por inferencia.
- **Decisión de redistribución del proyecto**: pendiente. Por la convención registrada en
  [weather.md](weather.md), el campo `redistribution` del catálogo registra la decisión del
  proyecto, no el texto legal de la licencia; para CAMS no existe aún decisión de integración
  (#17) y no se editó `configs/sources.yaml` en esta entrega.

## (c) Cobertura, grilla y semántica temporal (declaradas en la ficha ADS)

| Propiedad | Declaración revisada (20/11/2026 UTC) |
| --- | --- |
| Cobertura horizontal | Global (caja −180..180, −90..90 en los metadatos de la ficha); Lima queda incluida |
| Resolución de grilla | 0,75°×0,75° en ADS; resolución nativa «approximately 80 km» (T255/N128), interpolada a la grilla regular lat/lon (Confluence CKB) |
| Cobertura vertical | 60 niveles modelo híbridos con tope 0,1 hPa; también 25 niveles de presión (1000–1 hPa) y superficie/columna total |
| Cobertura temporal | «2003 to 2025» en la ficha (metadatos: 2003-01-01 a 2025-12-31); «EAC4 is only available from 2003 onwards» por la escasez de redes previas |
| Resolución temporal | 3-hourly (análisis); el reanálisis incluye además pronósticos de 48 h inicializados diariamente a las 00 UTC (Confluence CKB) |
| Actualización | «Twice a year with 4-6 month delay» (ficha ADS) |
| Formato | GRIB nativo de MARS; «optional conversion to netCDF»; el formulario del ADS ofrece «Zipped netCDF (experimental)» |
| DOI / fechas | 10.24381/d58bbf47; publicación 2020-02-06; última actualización declarada 2026-08-24 |

Escala en la práctica de Lima: una celda de 0,75° equivale a unas decenas de kilómetros
(~83 km en latitud). Para identificar qué celdas corresponden a las estaciones de Lima
hace falta cruzar sus coordenadas con la grilla. El producto no resuelve variaciones por distrito.

Dataset derivado revisado en la misma sesión: «CAMS global reanalysis (EAC4) monthly averaged
fields» (DOI 10.24381/fd75fff2), misma grilla 0,75°×0,75°, tipos `monthly_mean` y
`monthly_mean_by_hour_of_day`, solo nivel modelo 60 («Level 60 is the surface level»).

## (d) Variables relevantes para PM2.5

Listadas como variables principales en la ficha ADS (consultada el 20/11/2026):

- **Particulate matter d < 2.5 µm (PM2.5)**, kg m⁻³, variable de superficie/nivel único
  (identificador declarado en el formulario ADS: `particulate_matter_2.5um`). También PM10
  (`particulate_matter_10um`) kg m⁻³.
- **Aerosol optical depth at 550 nm** (adimensional): variable total
  (`total_aerosol_optical_depth_550nm`) y por componente — polvo, carbono negro, materia
  orgánica, sal marina y sulfato — además de AOD total en 469, 670, 865 y 1240 nm.
- Masas verticales integradas por componente de aerosol (kg m⁻²) y gases reactivos (NO2, O3,
  SO2, CO, entre otros) en mezcla o columna.

Precaución semántica: el PM2.5 de EAC4 es una **concentración superficial modelada** con
emisiones y química acopladas; su significado no es intercambiable con la medición horaria de
una estación SENAMHI/OEFA, ni en unidad, ni en representatividad espacial.

## (e) Máscaras de calidad y control de calidad documentado

- **Asimilación**: la ficha ADS declara que el sistema «is able to estimate biases between
  observations and to sift good-quality data from poor data» (consultado el 20/11/2026).
- **Máscaras de lista negra sobre entradas satelitales**: la documentación oficial de Confluence
  tabula cada recuperación satelital asimilada con su banda de calidad y **criterios de lista
  negra** explícitos, p. ej. «QR > 0» (bandera de calidad del proveedor), «MODORO > 6000»
  (orografía del modelo), «LAT<-60. and LSMASK = land» y criterios de elevación solar (SOE)
  (consultado el 20/11/2026). Estas máscaras se aplican dentro de la asimilación: el usuario
  del reanálisis recibe campos ya asimilados, no las banderas originales.
- **Máscara disponible como variable**: el dataset incluye «Land-sea mask (0 - 1)»
  (`land_sea_mask`, `lsm`), útil para documentar la clase de celda.
- **Validación**: la pestaña de documentación enlaza los informes «Evaluation and quality
  assurance (EQA) reports» de CAMS (atmosphere.copernicus.eu/node/325 vía ADS) y la página de
  documentación remite al sitio de Quality Assurance de CAMS. El mismo documento registra
  hallazgos de validación de AOD contra Aeronet: «hot spots» de AOD alto cerca de volcanes
  activos (en particular Mauna Loa y Ciudad de México) que degradan el RMSE global.
- **Problemas conocidos declarados** («Known issues», Confluence CKB, 20/11/2026): las
  emisiones antropogénicas del reanálisis **no** fueron ajustadas por los confinamientos
  COVID-19 de 2020; el análisis de ozono tiene calidad degradada en 2003 y entre marzo y
  agosto de 2004 no hubo perfiles de ozono disponibles para asimilación; la variable
  «Lifting threshold speed» fue retirada el 16/12/2024.
- **Guía de uso**: para meteorología sin composición, la documentación recomienda usar ERA5
  («Users who want to use meteorological data only are advised to use the ERA5 meteorological
  reanalysis») — coherente con la separación de clases de [weather.md](weather.md).

## (f) Vía de acceso (verificada documentalmente; sin descargas)

- El acceso a EAC4 es por el **Atmosphere Data Store (ADS)** de Copernicus/ECMWF:
  https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4 (y el dataset
  mensual `cams-global-reanalysis-eac4-monthly`). La propia ficha declara pertenecer al ADS
  (`isPartOf: Atmosphere Data Store`) y expone el endpoint de recuperación por API
  (`/api/retrieve/v1/processes/cams-global-reanalysis-eac4`) junto al formulario web.
- El portal requiere sesión: las páginas muestran «Login ‒ Register» y el acceso declarado es
  «Free access upon acceptance of applicable licences and terms of use». **No se creó cuenta,
  no se solicitó clave y no se descargó nada** (ni archivos de prueba): crear una cuenta ADS
  queda registrado como **pendiente de autorización de Keneth**, igual que la clave de OpenAQ
  en #116.
- Formato de entrega declarado: GRIB nativo de MARS con conversión opcional a NetCDF
  (el formulario del ADS etiqueta la opción NetCDF como «experimental»). El descargador
  reproducible acotado para esta fuente corresponde a #6/#7 y no se ejecutó aquí.
- EADS/otros almacenes no se consultaron: para esta composición global el ADS es la vía
  declarada en la ficha; no se afirma nada sobre otros almacenes.

## (g) Por qué EAC4 y no otro producto

Criterios aplicados por esta revisión (evidencia fechada arriba):

1. **Licencia declarada**: CC-BY-4.0 identificada por SPDX en las fichas ADS, con requisitos
   de atribución explícitos y acceso gratuito condicionado a aceptar los términos.
2. **Cobertura Lima/Perú**: grilla global sin recortes regionales; Lima queda dentro de la
   cobertura declarada (los productos europeos de CAMS, como el reanálisis de calidad del
   aire europeo ENS, no cubren Perú).
3. **Disponibilidad histórica**: 2003–2025 declarado, compatible con la ventana de 2015 del
   benchmark y con las particiones `train` del proyecto, a diferencia del archivo de
   pronósticos (desde 2015 y con semántica de corrida, no de reanálisis).
4. **Costo de acceso**: gratuito con cuenta ADS; la barrera es la cuenta (pendiente de
   autorización), no un pago.
5. **Documentación verificable**: grilla, máscaras de asimilación, validación y problemas
   conocidos publicados en páginas oficiales estáticas revisables.

Alternativas registradas **sin revisar** para #34 (ninguna afirmación de licencia o cobertura
aquí): pronósticos globales de CAMS (línea distinta, útil para prueba de adelanto, no para
historia), reanálisis europeo de calidad del aire de CAMS (ENS; cobertura europea), Sentinel-5P
TROPOMI (satelital; columnas, no PM2.5 superficial) y AOD de MODIS (satelital).

## (h) Límites explícitos

1. **Resolución baja**: EAC4 es reanálisis global de ~80 km nativo / 0,75°×0,75° público.
   **Nunca atribuir «resolución de barrio»**: la grilla no resuelve diferencias a escala de
   distritos, corredores viales o gradientes urbano-costeros.
2. **No sustituye estaciones**: el PM2.5 de EAC4 es modelado con asimilación; no es medición
   de estación y no reemplaza las series SENAMHI/OEFA ni la identidad por estación documentada
   en #14/#16. Toda comparación debe mantener las clases separadas como exige
   [weather.md](weather.md).
3. **Latencia incompatible con alertas**: actualización declarada «Twice a year with 4-6
   month delay». Para evaluar un pronóstico histórico, cada campo debe acreditar que ya
   estaba publicado al emitirlo. Un campo publicado después solo sirve para análisis
   retrospectivo y se excluye de las entradas de ese pronóstico.
4. **Comparación complementaria pendiente**: medir el aporte de una configuración
   complementaria aislada con **solo contaminación** sobre los objetivos compartidos de #25
   espera #17/#25 y la autorización de la cuenta ADS; este PR no ejecuta esa comparación ni
   anticipa resultados.
5. **Texto legal no descargado**: el host de licencias Copernicus falló por DNS (2 intentos
   registrados); la identificación CC-BY-4.0 proviene de las fichas ADS fechadas. La decisión
   de redistribución del proyecto sigue sin tomarse.
6. **Problemas conocidos heredados**: sin ajuste de emisiones por confinamientos de 2020 y
   degradaciones puntuales declaradas en los primeros años de la serie (2003–2004).

## Pendientes registradas

- Cuenta ADS: creación y aceptación de licencias pendiente de autorización de Keneth (mismo
  tratamiento que la clave de OpenAQ en #116).
- Comparación complementaria con solo contaminación sobre los objetivos de #25: espera #17/#25.
- Revisión de los informes EQA de CAMS y del texto legal CC-BY de Copernicus (host no
  resolvió): quedan como lectura pendiente; no se afirmó nada que dependa de ellos.
