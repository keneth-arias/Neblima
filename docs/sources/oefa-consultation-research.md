# Investigación complementaria y consulta OEFA para #11

Revisión: 16/11/2026 UTC, Keneth. Consultas web con Lightpanda, sin descargas masivas.
Se contrastaron búsquedas de contacto, fechas/horas, Lima y fuentes recientes con páginas oficiales;
los resultados ajenos a fuentes oficiales no se usaron para definir semántica del CSV.

## Hallazgos comprobados

1. El [catálogo nacional EAS](https://www.datosabiertos.gob.pe/dataset/vigilancia-y-seguimiento-ambiental-en-la-calidad-del-aire-organismo-de-evaluaci%C3%B3n-y)
   lista Enrique Manco y emanco@oefa.gob.pe como contacto, DEAM como responsable funcional en la
   descripción y ODC-By como licencia. El correo se comprobó también mediante extracción del enlace
   mailto con Lightpanda. Es contacto publicado, no confirmación de vigencia del buzón o de disponibilidad
   personal para asesoría. Es apropiado pedir orientación o derivación al equipo técnico.
2. El [catálogo institucional data.json](https://datosabiertos.oefa.gob.pe/data.json) contiene
   «EAS - Componente ambiental Aire», cobertura declarada 01/2018–06/2024, y contacto institucional
   earangoitia@oefa.gob.pe. Solo se extrajeron título/descripción/ficha/contacto; no se reutilizaron
   parámetros de acceso de los enlaces API del catálogo. También declara EAC, EAF y EAT como productos
   diferentes; no agregarlos a EAS ni transferir licencias automáticamente.
3. La [ficha EAS institucional](https://datosabiertos.oefa.gob.pe/dataviews/263773/eas-componente-ambiental-aire/)
   abrió con título y cobertura hasta junio 2024, pero sus dos iframes no cargaron en Lightpanda.
   No se pudo verificar tabla, timestamps, granularidad, volumen ni calidad. El pie enlaza PDDL;
   no demuestra licencia específica del recurso ni reemplaza ODC-By del conjunto nacional.
   Es un candidato a verificar con el publicador, no una nueva adquisición validada.
4. [PIFA](https://sistemas.oefa.gob.pe/pifa/mfe/) anuncia vigilancia de aire en tiempo real; abrió su
   portada y un iframe no cargó. Una portada no establece exportación histórica ni API de series.
   Pedir el canal oficial de históricos validados, evitando inferir acceso por observar un visor.

## Evidencia local que cambia la prioridad

Entradas y hashes de #10: metadata/profiling-run.json. Consulta de solo lectura de stations.parquet
unida a signals.parquet por station_key, agrupando nombre/contexto y sumando finite_count y
parsed_finite_count para PM2.5/PM10; geografía según station_context original.

| Punto etiquetado Lima / Lurigancho | Filas de origen | Celdas finitas PM2.5 | Celdas finitas PM10 | Celdas finitas con inicio interpretable (cada señal) |
| --- | ---: | ---: | ---: | ---: |
| CA-HU-04 | 4 350 | 561 | 561 | 0 |
| CA-HU-09 | 3 566 | 460 | 460 | 0 |
| CA-RZC-01 | 102 346 | 450 | 450 | 0 |
| CA-RZC-02 | 102 200 | 500 | 500 | 0 |

En grupos CALLAO también se observan cero celdas PM2.5/PM10 finitas con inicio interpretable.
Los únicos dos contextos PM2.5 con puntos horarios admisibles son CA-HUA-01 (7 137) y CA-MAC-01
(7 893), ambos etiquetados PIURA / PAITA / LA HUACA. Son conteos de puntos, no ventanas.
Con el parser/política actual no hay puntos horarios PM2.5 admisibles de Lima para construir ventanas
OEFA. No atribuir esos ceros a inexistencia de mediciones; pueden faltar horas/exportaciones adecuadas.

En todo el archivo hay 2 715 954 tokens HORA_INICIO=NA y 1 577 173 repeticiones de campos completos
sin decidir borrado. Tres fechas rechazadas tienen precedencia sobre la clasificación de hora; por eso
la categoría de fecha válida y hora faltante de #10 contiene 2 715 953 filas, no 2 715 954.
La fecha máxima local es 2022-12-31, frente a 2021 declarado en metadatos históricos y junio 2024
anunciado por la ficha nueva. Son diferencias de cobertura/versiones, no evidencia de errores del proveedor.

## Qué sigue faltando y qué pedir

- Prioridad 1: exportación validada con timestamps de PM2.5/PM10 en Lima, estaciones/fechas disponibles,
  zona horaria y si el sello representa inicio/fin de intervalo; aclarar fechas base 1899 y horas NA.
- Prioridad 2: identificador de observación, repetición por tipo de análisis/muestra y vinculación de la
  columna ancha con UNIDAD_MEDIDA. Evitar que conteos de filas se presenten como mediciones únicas.
- Prioridad 3: banderas de validación, mantenimiento/calibración, marcadores/no aplica, periodos móviles
  y disponibilidad efectiva de productos agregados (riesgo de información futura al pronosticar).
- Prioridad 4: historial de estaciones/reubicaciones, CRS/hemisferio y cambios de altitud; no pedir una
  definición ausente de FECHA_CORTE, que ya está documentada como fecha de generación.
- Prioridad 5: relación/versionado entre catálogo nacional, ficha EAS nueva y PIFA; licencia/atribución
  aplicable a cada descarga y exportaciones derivadas. No solicitar autorización que sustituya leer una
  licencia ya publicada; sí aclarar contradicciones entre productos y avisos de atribución.

Borrador: docs/consultations/oefa-consulta-borrador.md. No enviado ni creado en Outlook.
No hay garantía de respuesta, asesoría o existencia de un archivo que complete las horas.
