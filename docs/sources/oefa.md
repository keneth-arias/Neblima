# Verificación de recursos de OEFA y coordenadas

Tarea: [#5 — Verificar los recursos de OEFA y sus coordenadas](https://github.com/keneth-arias/airaware/issues/5).
Revisión: 2026-11-16 (UTC). Responsable: Cristopher (`@qriqs`). Revisión científica y de licencias pendiente de Keneth.

## Alcance y resultado

Se resolvieron los recursos oficiales del conjunto de calidad del aire de OEFA mediante consultas
acotadas. Se descargaron el diccionario de datos y los metadatos, y solo los primeros 65 536 bytes
del CSV. No se descargó el conjunto completo ni se modificó `configs/sources.yaml`.

El acceso público al CSV y a los documentos quedó demostrado. El catálogo declara Open Data Commons
Attribution License (ODC-By). Los campos `ESTE`, `NORTE`, `ZONA` y `DATUM` existen; los 123 registros
completos de la muestra inicial contienen `ZONA=17` y `DATUM=WGS84`. Esta muestra no basta para afirmar
que todas las estaciones usan la misma zona o datum.

Según el publicador, el conjunto contiene Evaluaciones Ambientales de Seguimiento (EAS) de 34
estaciones. Los metadatos declaran cobertura de Perú para 2018–2021. Estas cifras son declaraciones
de la fuente, no resultados de un perfilamiento completo de AirAware.

## Recursos oficiales resueltos

Todos los enlaces se revisaron el 2026-11-16 (UTC).

| Recurso | URL y evidencia |
| --- | --- |
| Catálogo | [Vigilancia y Seguimiento ambiental en la calidad del aire](https://www.datosabiertos.gob.pe/dataset/vigilancia-y-seguimiento-ambiental-en-la-calidad-del-aire-organismo-de-evaluaci%C3%B3n-y). Publicador OEFA; acceso público; modificación del catálogo 2026-06-15. |
| API del catálogo | [`package_show`](https://www.datosabiertos.gob.pe/api/3/action/package_show?id=1cb938b1-f9ec-4a36-88e7-4a7333e7f134), identificador `1cb938b1-f9ec-4a36-88e7-4a7333e7f134`. Resolvió las URL y los tamaños declarados de los tres recursos. |
| Mediciones CSV | [Archivo CSV](https://www.datosabiertos.gob.pe/sites/default/files/1a_Vigilancia%20y%20Seguimiento%20ambiental%20en%20la%20calidad%20del%20aire.csv), recurso `61ecaa36-6319-4e75-8a8c-bcf13343e5a9`. El servidor informó 1 317 949 839 bytes. |
| Diccionario | [Diccionario XLSX](https://www.datosabiertos.gob.pe/sites/default/files/1c_Formato_DiccionarioDatos_Vigilancia%20y%20Seguimiento%20ambiental%20en%20la%20calidad%20del%20aire.xlsx), recurso `cda6e809-36a3-44a2-ae92-c475589ecf97`, 53,24 KB declarados. Describe campos, tipos, formatos y unidades. |
| Metadatos | [Metadatos DOCX](https://www.datosabiertos.gob.pe/sites/default/files/1b_Formato_Metadatos_Vigilancia%20y%20Seguimiento%20ambiental%20en%20la%20calidad%20del%20aire.docx), recurso `34e8c580-dc55-46ea-98cd-7744a5fa1d34`, 15,65 KB declarados. Declara cobertura 2018–2021, actualización anual y licencia ODC-By. |
| Portal OEFA | [Portal Interactivo de Fiscalización Ambiental (PIFA)](https://sistemas.oefa.gob.pe/pifa/mfe/). Respondió con la portada; esta revisión no resolvió una API ni atribuyó sus contenidos al CSV. |

La respuesta de `package_show` enumera exactamente tres recursos asociados a este conjunto: CSV,
diccionario y metadatos. No hay otros archivos asociados que falten en esa lista. Los portales e
informes siguientes son recursos relacionados, no componentes adicionales del mismo conjunto.

## Recursos institucionales relacionados

- El [anuncio oficial de publicación](https://www.gob.pe/institucion/oefa/noticias/946815-el-oefa-pone-a-disposicion-informacion-registrada-por-sus-34-estaciones-de-monitoreo-de-la-calidad-del-aire),
  fechado 2024-04-30, confirma que DEAM captura, sistematiza, valida y visualiza los parámetros de
  las 34 estaciones. No publica un archivo adicional ni resuelve las diferencias de fecha y hora.
- La [colección Monitoreo ambiental del repositorio OEFA](https://repositorio.oefa.gob.pe/collections/71ffa96c-1100-4c5d-bd18-7ede20e97b9b)
  mostraba 966 ítems al revisarla. La colección mezcla aire, agua, suelo, ruido y otros componentes;
  no representa 966 recursos de calidad del aire ni se descargó o recorrió masivamente.
- La [colección Vigilancia ambiental](https://repositorio.oefa.gob.pe/collections/44498aba-74ef-4fbe-958c-701559d5558c)
  es más específica y mostraba 190 ítems. Incluye evaluaciones de seguimiento y anexos de aire, pero
  también otros componentes; tampoco se la recorrió ni descargó completamente.
- El [Protocolo Nacional de Monitoreo de la Calidad Ambiental del Aire](https://sinia.minam.gob.pe/normas/decreto-supremo-que-aprueba-protocolo-nacional-monitoreo-calidad)
  establece criterios para generar información comparable, compatible, confiable y representativa. Es
  el marco metodológico general, no evidencia de que todas las filas del CSV cumplan un método concreto.
- [Evaluaciones ambientales de causalidad (EAC)](https://www.datosabiertos.gob.pe/dataset/evaluaciones-ambientales-de-causalidad-eac)
  es un conjunto independiente, no otro recurso del CSV de seguimiento (EAS). Su
  [API](https://www.datosabiertos.gob.pe/api/3/action/package_show?id=53861025-509f-469f-b1d9-ddeefd33a934)
  incluye `EAC_Aire_0.xlsx`, recurso `949cad62-77f9-4e92-a210-abec9f926e9a`, de 13,05 MB declarados.
  No se descargó ni se combinó con el CSV de EAS porque sus objetivos y esquemas son distintos.
- El [informe de Bayóvar 00008-2020-OEFA/DEAM-STEC](https://repositorio.oefa.gob.pe/items/bc430a12-889b-4551-85b8-3bd875880184)
  incluye mapas, datos de campo, verificación y calibración de equipos, cálculos, datos meteorológicos
  y cadena de custodia. Puede servir para estudiar procedencia y metodología de esa evaluación.
- El [informe de Apurímac–Cusco 00004-2021-OEFA/DEAM-STEC](https://repositorio.oefa.gob.pe/items/94a7f126-da3c-44f1-b4a6-134ff1818e42)
  incluye registros crudos, sistematización de datos, alertas y certificados de calibración. Es otra
  evaluación concreta, no una copia ni una versión adicional del CSV nacional.

Los dos registros del repositorio muestran la etiqueta general «Licencia Creative Commons», pero la
página extraída no precisa la variante. No se les aplicó automáticamente la licencia ODC-By del CSV.
Antes de reutilizar un informe o anexo se debe revisar su registro y licencia propios, identificar su
relación con `NOMBRE_EVALUACION` y evitar duplicar mediciones ya presentes en el conjunto nacional.

## Acceso real y volumen

Una solicitud `HEAD` al CSV respondió `HTTP 418`. Una descarga `GET` sin agente de usuario ni referente
también respondió `HTTP 418`. Las solicitudes acotadas posteriores con agente de usuario `Mozilla/5.0`
y el catálogo como referente respondieron correctamente. Esto describe el comportamiento observado;
no demuestra una política permanente del servidor.

La solicitud de rango al CSV respondió `HTTP 206 Partial Content` con:

```text
Content-Length: 65536
Content-Range: bytes 0-65535/1317949839
Last-Modified: Wed, 17 Jul 2024 14:15:04 GMT
ETag: "6697d1e8-4e8e518f"
```

El volumen actual del objeto es 1 317 949 839 bytes (aproximadamente 1,318 GB decimales o 1,23 GiB),
coherente con el tamaño de 1,23 GB mostrado por el catálogo. La descarga completa queda pendiente de
la tarea de adquisición y de sus controles; esta investigación transfirió únicamente 64 KiB del CSV.

La comprobación acotada del CSV descrita aquí se realizó con `curl`. No se registró una
comprobación inicial con Lightpanda. Se usó `curl` para solicitar un rango de bytes acotado y
conservar los encabezados HTTP; esta alternativa al flujo inicial acordado queda registrada de
forma explícita. Durante la revisión de Keneth del 16/11/2026, el catálogo respondió HTTP 200 y
se descargaron el diccionario XLSX y los metadatos DOCX con Lightpanda; sus SHA-256 coinciden con
los registrados abajo. Esa revisión no volvió a descargar la muestra del CSV ni comprobó su
respuesta de rango.

Comando principal de comprobación, con las URL abreviadas solo en esta explicación:

```bash
curl -fsSL --max-time 45 --max-filesize 65536 --range 0-65535 \
  -A 'Mozilla/5.0' -e '<URL_DEL_CATALOGO>' -D data/raw/oefa/csv-range-headers.txt \
  '<URL_DEL_CSV>' -o data/raw/oefa/csv-primeros-64k.bin
```

Los archivos originales pequeños y la porción acotada se conservan localmente en `data/raw/oefa/`,
carpeta excluida de Git. La porción no es un CSV completo ni una muestra representativa.

| Archivo local | SHA-256 |
| --- | --- |
| `diccionario-datos.xlsx` | `4f2fe50d1166ca23e0447ea5dbe9051a4e4731600b2f5bec007ae5d75017c5bb` |
| `metadatos.docx` | `886fca1668115cd10ef1f966aa5784d062cb780125ac1699908bf245bcae70d1` |
| `csv-primeros-64k.bin` | `a658527f37adc8eea1c1589b2362f900ec29e47347646275341fc1318667dd51` |

## Coordenadas y campos medidos

El diccionario define `ESTE` y `NORTE` como coordenadas de la estación asociadas al campo `DATUM`,
`ALTITUD` en metros sobre el nivel del mar, `ZONA` como subdivisión geográfica y `DATUM` como código
de referencia de las coordenadas. La definición de `ZONA` no menciona UTM expresamente.

La porción inicial se decodificó como UTF-8 con marca de orden de bytes y se separó por punto y coma.
Contiene 123 filas completas de la estación `CA-HUA-01`, con estos valores constantes:

| Campo | Valor observado |
| --- | --- |
| `ESTE` | `504395` |
| `NORTE` | `9456762` |
| `ALTITUD` | `32` |
| `ZONA` | `17` |
| `DATUM` | `WGS84` |

La combinación Este/Norte, zona y WGS84 es compatible con una representación UTM. No se asignó un
código EPSG ni se convirtió la coordenada: primero se debe comprobar la interpretación y la variedad
de `ZONA` y `DATUM` en el conjunto completo. No se infiere cobertura nacional a partir de una estación.

Informes oficiales independientes aportan evidencia UTM para estaciones concretas:

- El [informe 0018-2019-OEFA/DEAM-STEC](https://repositorio.oefa.gob.pe/items/4ae5ab05-c7e8-48a5-bb18-f53879aef94e),
  tabla 4.2, identifica `CA-CC-01` con «Coordenadas UTM» y «WGS-84 Zona 18L».
- El [reporte 00003-2021-OEFA/DEAM-STEC](https://repositorio.oefa.gob.pe/items/e01e67e5-236d-40f4-9d17-11d1d8d53108),
  tabla 3.2, identifica `CA-SB-01` con «Coordenadas UTM WGS-84 Zona 18 L».
- El [reporte 00026-2022-OEFA/DEAM-STEC](https://repositorio.oefa.gob.pe/items/f6a65eda-faaa-422c-bf57-4c6ef592e8c0)
  documenta `CA-SOC-01` con «WGS-84 Zona 19 K».

Por tanto, no se debe fijar toda la fuente a la zona 17. Estos informes no demuestran qué valores están
presentes en todas las filas del CSV ni que su `DATUM` sea uniforme. Además, la muestra del CSV contiene
solo el número `17`, mientras los informes añaden bandas como `L` o `K`; la correspondencia entre esos
formatos y el hemisferio debe quedar explícita antes de construir un CRS.

## Diferencias y datos faltantes observados

- El diccionario documenta `FECHA_CORTE` en la fila 40 como «Día en que se generó el dataset.»,
  con formato `aaaammdd`. En las filas revisadas aparece como `20240429`. Es una fecha de generación
  del conjunto; no debe usarse como fecha de medición.
- El diccionario indica `aaaammdd` para `FECHA_INICIO` y `FECHA_FIN`; la muestra usa `AAAA-MM-DD`.
- El diccionario indica `HH:MM` para las horas; la muestra presenta valores como
  `1899-12-31 18:00:00`. Falta confirmar la interpretación y la zona horaria antes de normalizar.
- La unidad observada es `ug/m3`; `PM2.5` contiene `-` en las primeras filas. Algunas tablas metodológicas
  del informe 0018-2019 explican `-` como «No aplica», pero eso no define el marcador en las mediciones
  del CSV: también podría representar otra condición. El tratamiento de datos faltantes y la compatibilidad
  de unidades requieren reglas explícitas, no imputación silenciosa.
- Los informes confirman productos horarios, de 24 horas y promedios móviles de 3 horas en evaluaciones
  concretas. No definen el vocabulario completo de `PERIODO` en el CSV ni si su fecha y hora marcan el
  inicio, el fin u otro instante de la ventana.
- La definición oficial de `FECHA_CORTE` está disponible en el diccionario; no se requiere consultar
  a OEFA por la ausencia de esa definición. Sigue pendiente confirmar la zona horaria de las
  mediciones y la interpretación de las horas. No se adoptó UTC−5 solo por ser la zona horaria nacional.
- Los metadatos DOCX indican última actualización 2024-04-29; el catálogo indica modificación
  2026-06-15 y el CSV informa `Last-Modified` 2024-07-17. No se equiparan estas fechas porque pueden
  describir eventos distintos.

## Licencia y redistribución

El catálogo y los metadatos declaran **Open Data Commons Attribution License (ODC-By)**. El
[texto oficial de ODC-By 1.0](https://opendatacommons.org/licenses/by/1-0/) permite usar, extraer,
reutilizar y distribuir la base de datos, incluidas bases derivadas, bajo sus condiciones (sección 3).
Al distribuirla se deben conservar los avisos, incluir la licencia o su URI y usar los mismos términos
(sección 4.2). Los productos derivados deben incluir una atribución razonable (sección 4.3).

La propia licencia advierte que los contenidos individuales pueden tener otros derechos no cubiertos
por ella (sección 2.4). Por tanto, la licencia está identificada y las condiciones iniciales son
claras, pero Keneth debe revisar la atribución y los derechos antes de una publicación. Esta tarea no
autoriza por sí sola publicar datos masivos.

Para el conjunto independiente EAC, la página visible indica `License Not Specified`, mientras su API
devuelve el identificador ODC-By. Es una discrepancia de metadatos que debe resolverse antes de afirmar
permisos sobre `EAC_Aire_0.xlsx`; no se transfiere la licencia verificada del CSV de EAS. La API de EAC
también etiqueta el recurso XLSX como `format: csv`, otra diferencia que debe conservarse como advertencia.

## Criterios de la tarea

- [x] Datos y documentación resueltos mediante consultas acotadas.
- [x] Licencia y acceso real comprobados; campos `ESTE`, `NORTE`, `ZONA` y `DATUM` inspeccionados en
  una porción limitada, sin generalizar sus valores a todo el conjunto.
- [x] Volumen medido mediante `Content-Range` y bloqueos de acceso registrados antes de adquirir el
  conjunto completo.

## Pendientes para adquisición o normalización

1. Perfilar todas las combinaciones de `ZONA` y `DATUM`, valores vacíos y coordenadas inválidas cuando
   se autorice una descarga completa o se disponga de consultas acotadas por estación.
2. Consultar a OEFA sobre las diferencias de formato de fecha/hora y la zona horaria de las
   mediciones si la evidencia disponible no las resuelve.
3. Definir con Keneth el sistema de referencia de coordenadas (CRS), la atribución y el tratamiento de
   datos faltantes antes de integrar o redistribuir datos.
4. Establecer una relación determinista entre `NOMBRE_EVALUACION`, los códigos de estación y los informes
   del repositorio antes de usar anexos para completar metodología, calibración o coordenadas.
5. Actualizar el catálogo en un cambio coordinado. La dependencia #3 ya está cerrada, pero esta primera
   entrega se limita al documento de evidencia previsto en la tarea.

## Validación local de la entrega

Ejecutado el 2026-11-16 desde la raíz del repositorio:

- `make check`: aprobado; formato, análisis estático, tipos y catálogo válidos; 31 pruebas aprobadas.
- `make build`: aprobado; se generaron la distribución fuente y el wheel de `airaware-0.1.0`.
- `make audit`: aprobado; `pip-audit` no encontró vulnerabilidades conocidas. Se omitió el paquete
  local editable conforme a la configuración del proyecto.

## Ejecución controlada posterior de #9

El plan aprobado se ejecutó con los prerrequisitos de dialecto y canal público explícito.
metadata/oefa-acquisition-check.json y reports/acquisition/oefa.md registran documentos preservados
con sumas verificadas y dos recorridos offline. El CSV respondió HTTP 418 en la sonda controlada:
se detuvo sin otro intento/canal, no se descargó el archivo completo ni se confirmó el tamaño actual.
La evidencia histórica de rango de #5 no se reemplaza ni se presenta como medición de esta ejecución.
#9 conserva el bloqueo; el catálogo diferencia acceso documental y acceso al archivo CSV.


## Descarga completa posterior con Lightpanda

Por instrucción explícita de Keneth, Lightpanda download obtuvo el CSV completo: 1 317 949 839 bytes.
metadata/oefa-lightpanda-download.json registra SHA-256, 36 columnas, 2 883 877 filas de datos,
validación estructural y reutilización local del original/manifiesto sin cambios. El código HTTP del
archivo queda nulo porque la herramienta no lo expuso. El CSV no se normalizó ni se publicó en Git.
Este resultado resuelve la adquisición de #9; el 418 del canal http_file permanece como historial,
no como bloqueo actual del archivo disponible localmente. #10 mantiene el perfilamiento científico.

## Relectura completa del diccionario para #11

La [revisión por celdas y cruce de unidades](metadata-methods-review.md) confirma el significado
oficial de los campos temporales y de UNIDAD_MEDIDA. Todas las celdas PM2.5/PM10 finitas del archivo
actual llevan ug/m3; no corresponde describir su etiqueta de unidad como totalmente desconocida.
Esto no recupera las horas faltantes de Lima ni resuelve banderas, repeticiones o todos los contextos.

## Matriz de compatibilidad por producto de OEFA (#30)

Revisión del 2026-11-20 (UTC). Responsable de la entrega: Cristopher (`@qriqs`). Esta matriz se
construye **solo con las revisiones fechadas ya registradas en el repositorio**: la revisión de
recursos del 2026-11-16 (secciones anteriores de este documento), el análisis de IPASH, EAC, EAF y
EAT del [17/11/2026](../../reports/oefa-workbook-analysis.md) (resumen y hashes en
`metadata/oefa-workbook-analysis.json`) y el diagnóstico del CSV EAS largo del
[17/11/2026](../../reports/eas-long-diagnostic.md) (recibo en `metadata/eas-long-diagnostic.json`).
La confirmación completa exige resolver el reloj, la identidad geográfica (#14), la calidad y los
derechos de cada producto; hasta entonces ninguna fila de esta matriz acredita mezclar fuentes ni
generalizar fuera de Lima.

| Producto | Frecuencia observada | Significado de la medición | Derechos | Cobertura | Decisión |
| --- | --- | --- | --- | --- | --- |
| EAS (CSV) | 333 combinaciones parámetro/unidad/periodo; PM2.5/PM10 horarios en µg/m³; el reloj solo se construyó bajo la hipótesis Excel 1900 sin confirmar (3 512 243 filas con reloj hipotético) | Concentración de material particulado, objetivo ambiental del proyecto | ODC-By declarado en catálogo y metadatos (revisión 16/11); atribución y derechos pendientes de Keneth | 34 estaciones declaradas a nivel nacional; la muestra completa está en una sola estación con ZONA=17/DATUM=WGS84; informes citan zonas 18L y 19K en otras estaciones | **No mezclar aún**: `scientific_valid_windows` sigue nulo porque faltan época y convención temporal, calidad, identidad geográfica y derechos. Es el candidato prioritario para el objetivo horario (diagnóstico del 17/11). |
| EAC | Periodos horarios, 24 h, 8 h, mensuales o ausentes; racha horaria PM más larga: 542 h | Meteorología, gases, partículas y análisis de metales/minerales; un metal medido en PM10 y el peso de un filtro no son concentración total de PM10 | Discrepancia sin resolver: la página dice `License Not Specified` y la API devuelve ODC-By; el recurso XLSX está etiquetado `format: csv` | 184 nombres de puntos; los tres contextos horarios PM no incluyeron candidatos Lima con el criterio textual del 17/11 | **Excluir del objetivo horario PM de Lima**: sin candidatos Lima identificados textualmente y con calidad sin revisar (13 549 inicios sin resolver, 126 celdas de fórmula en fecha fin, 18 intervalos negativos, valores atípicos conservados). |
| EAF | Campañas focales y emergencias; rachas PM2.5 en contextos Lima textuales de 20 a 204 h | Concentraciones de campañas específicas; no es una red de observación rutinaria | «Licencia Creative Commons» general en el repositorio, variante sin precisar (revisión 16/11) | Menciones textuales de San Juan de Lurigancho, La Victoria y Lurigancho-Chosica; 13 ventanas 168→24 h con mención Lima; sin homologación espacial | **Excluir de la mezcla horaria; reservar como piloto de eventos** con objetivos separados y validación temporal propia: las ventanas superpuestas no se tratan como ejemplos independientes. |
| EAT | Muestras de 24 horas (2 940 filas) | Química de campaña: partículas, metales y otros parámetros de laboratorio; 1 328 valores censurados (45,2 %) como `<L.C.` | «Licencia Creative Commons» general, variante sin precisar | 22 nombres de puntos de evaluación; sin asociación con Lima evidenciada en el 17/11 | **Excluir del objetivo horario**: no se fabrican series horarias desde muestras de 24 h ni se sustituyen censura por cero o límite; producto especializado de campañas. |
| IPASH | Sin periodo declarado: `Periodo='-'` en las 1 330 filas | Mínimos/máximos/promedios de gases y propiedades de pozos (O2, H2S, COV, límite inferior de explosividad); no son concentraciones ambientales | «Licencia Creative Commons» general, variante sin precisar | 133 puntos o aberturas de pozos; sin series PM10/PM2.5 | **Excluir del objetivo horario PM**: sin series horarias de particulado ni significado compatible con el pronóstico ambiental; caracterización específica de sitio. |

Las exclusiones de EAC, EAF, EAT e IPASH citan el análisis del 17/11/2026; la decisión de no mezclar
EAS cita el diagnóstico del 17/11/2026. Los conteos de «ventanas estructurales» (EAC 1 645 ventanas
24→6 h sin mención Lima; EAF 647/951 con 491 contextos textuales Lima y 13 semanales) son
estructura en el reloj de origen, no elegibilidad científica. La ausencia de menciones Lima en un
archivo no prueba ausencia de mediciones de Lima en otras etiquetas o representaciones.

## Conversión verificada de coordenadas UTM de OEFA (#30)

Lo único verificado en la fuente es la muestra inicial del CSV de EAS (revisión del 16/11, más
arriba): `ZONA=17` y `DATUM=WGS84` en los 123 registros completos de `CA-HUA-01`. La conversión se
implementa en `src/airaware/normalization/oefa_coords.py` con estas reglas:

1. **Solo el par verificado convierte.** `ZONA=17` con `DATUM=WGS84` se interpreta como UTM zona 17
   sur (EPSG:32717) hacia EPSG:4326, porque la cobertura declarada es Perú —hemisferio sur, según
   los metadatos revisados— y el NORTE de la muestra (9 456 762) solo es coherente con ese
   hemisferio. Otro valor de zona o datum, ausente o vacío, produce un rechazo tipado
   (`zona_ausente`, `zona_no_verificada`, `datum_ausente`, `datum_no_verificado`, `este_invalido`,
   `norte_invalido`); nunca se convierte bajo una interpretación asumida.
2. **Los originales se conservan verbatim** en la salida, junto con los valores convertidos y el
   registro de la operación (`crs_origen`, `crs_destino`, `metodo`). El valor dorado registrado es
   el punto de la muestra: ESTE=504395, NORTE=9456762 → latitud −4,9147225518, longitud
   −80,9603584686, contrastado con una implementación independiente de las fórmulas de Snyder con
   acuerdo mejor que 1e−7 grados. Ese punto no pertenece a Lima y no se le atribuye pertenencia.
3. **pyproj es el extra opcional `geo`** (`pyproject.toml`), sin entrar a las dependencias base. La
   validación y los rechazos no importan pyproj; solo la conversión verificada lo importa de forma
   perezosa, siguiendo el patrón del extra `tabular` (#26). En CI, que instala sin extras, las
   pruebas de conversión se omiten con `pytest.importorskip("pyproj", reason=...)` y las pruebas de
   rechazo se ejecutan igual.
4. **La definición del CRS del catálogo sigue pendiente de Keneth** (pendiente 3 de la sección
   «Pendientes», más arriba): esta entrega no modifica `configs/sources.yaml` ni
   `tasks/plan.md`; la propuesta se registra en el cuerpo del PR. El adaptador hacia `Station` del
   contrato de observaciones (`coordinate_evidence`) queda para la integración siguiente.

Verificación local de esta entrega, ejecutada el 2026-11-20 desde la raíz del repositorio:

```text
uv sync --locked --extra geo
uv run --locked --extra geo pytest tests/test_oefa_coords.py
  → 11 passed (exit 0): 4 de conversión y dorado, 7 de rechazos y conservación de originales
uv sync --locked && make check   (modo CI, sin extras)
  → exit 0: uv lock --check, ruff format, ruff check, ty, catálogo y
    pytest 413 passed, 4 skipped (las conversiones omitidas con importorskip)
make build → exit 0 (dist/airaware-0.1.0.tar.gz y wheel generados)
make audit → exit 0 (pip-audit: No known vulnerabilities found)
```

