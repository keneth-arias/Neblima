# Bitácora de búsqueda para #4

Fecha de búsqueda e inspección: 16/11/2026 UTC. Alcance: exportación SENAMHI Lima y vacíos de
unidades, tiempo, calidad y licencia. Búsqueda por índice web para descubrir documentos; Lightpanda
para consultar páginas y descargar. No se usó otro descargador cuando falló una página.
Los resultados del índice solo orientaron la búsqueda; las conclusiones usan documentos oficiales
inspeccionados. Esto no es un barrido exhaustivo de toda la documentación de SENAMHI.

## Consultas y resultados

| Familia de consultas ejecutadas | Resultado y uso |
| --- | --- |
| site:senamhi.gob.pe + calidad aire + UTC / UTC-5 / hora local / zona horaria | Sin declaración localizada que vincule inequívocamente FECHA/HORA del CSV a una zona; referencias meteorológicas no se trasladaron a contaminación |
| "Monitoreo de los contaminantes del aire" + unidades; SENAMHI + PM2 + datos abiertos | Diccionario y metadatos asociados: no especifican unidades de concentración |
| SENAMHI + calidad aire + validación datos horarios metodología | Manual MT-DRD-005; se descargó y revisó, con especial atención a páginas 6–7 |
| SENAMHI + NO2 + ppb + µg/m3; 00711SENA-91 + unidades | Tabla instrumental en ppb; no prueba que el CSV esté en esa unidad |
| SENAMHI + calidad aire + febrero 2018 | Colección oficial y boletín; se resolvió paginación y se inspeccionó visualmente el PDF |
| SENAMHI + PM10 + WGS + hora; HORA + hhmmss | Sin confirmación localizada del sistema geodésico ni del reloj de esta exportación |
| SENAMHI + datos abiertos + licencia; ODC attribution 1.0 database contents | Declaración del DOCX y cadena Open Definition → texto oficial ODC-BY v1.0 |
| SENAMHI + calidad aire + condiciones estándar | Información contextual; no se aplicó temperatura/presión de otro conjunto ni se convirtió NO2 |

## Fuentes primarias comprobadas

1. Catálogo y recursos CSV/XLSX/DOCX: URL en configs/sources.yaml. XLSX: DiccionarioDatos!A4:F19.
   DOCX: fuente SGD/DRD, versión 1.0, creación y actualización 2024-05-24. Esa fecha no reemplaza la
   modificación 2025-09-08 que mostró el catálogo en #3; pueden ser versiones documentales distintas.
2. [Manual MT-DRD-005 v01](https://www.senamhi.gob.pe/load/file/00711SENA-91.pdf): 12 páginas;
   lectura de texto y verificación visual de página 6. Reglas generales no equivalen a trazas del CSV.
3. [Ficha de Santa Anita](https://www.senamhi.gob.pe/?e=112208&p=calidad_del_aire-estadistica):
   Lightpanda HTTP 200; instrumentos identificados sin vigencias históricas completas.
4. [Evaluación 2013](https://www.senamhi.gob.pe/load/file/01403SENA-5.pdf): 62 páginas; portada y edición
   Lima 2015 comprobadas localmente. No es un informe de 2025 aunque el índice sugiera publicación reciente.
5. [Colección de boletines](https://www.gob.pe/institucion/senamhi/colecciones/51675-boletin-vigilancia-de-la-calidad-del-aire-en-lima-metropolitana-y-el-callao?sheet=5)
   → [febrero 2018](https://www.gob.pe/institucion/senamhi/informes-publicaciones/6613132-boletin-vigilancia-de-la-calidad-del-aire-en-lima-metropolitana-y-el-callao-febrero-2018).
   PDF de 13 páginas, etiqueta 3.3 MB; se inspeccionaron visualmente 2, 3, 9 y 10.
   pypdf extrajo muy poco texto en esas páginas: no se interpretó ese resultado como ausencia de contenido.
6. [Open Definition](http://opendefinition.org/licenses/odc-by/)
   → http://opendatacommons.org/licenses/by/1.0/
   → [texto final](https://opendatacommons.org/licenses/by/1-0/). Lightpanda confirmó ambas páginas HTTP 200.
   Las secciones revisadas y la decisión operativa están en el manifiesto documental.

## Fallas, alternativas y descartes

- Consultas que devolvían páginas extranjeras, servicios no relacionados o normas de otra entidad:
  descartadas como evidencia de este CSV.
- La página educativa https://www.senamhi.gob.pe/?p=calidad-de-aire-aprendiendo redirigió a
  https://www.gob.pe/senamhi. El texto indexado no se trató como contenido observado en esa URL actual.
- La colección sheet=4 no contenía el enlace de febrero 2018 en el DOM consultado. Se siguió la
  paginación oficial a sheet=5 y se resolvió el PDF desde su ficha; no se inventó la URL del archivo.
- pdftotext no está instalado. Para lectura local se usaron pypdf y PyMuPDF en entornos efímeros uv,
  sin modificar pyproject.toml ni los archivos uv.lock. No es un cambio de canal de descarga.
- Repositorios derivados y agregadores pueden orientar, pero no se usaron como confirmación de
  unidades, licencia o tiempo de la exportación original. La comparación con el boletín se reprodujo
  con el CSV local, sin adoptar resultados calculados por terceros.

## Vacíos que justifican la consulta

La corroboración de cinco máximos aporta evidencia concreta para preguntar por unidades y +5 horas,
pero no fija la semántica de toda la serie. Siguen sin confirmación para el CSV: unidad por señal,
reloj/intervalo, condiciones de conversión, trazas de validación, códigos completos de ausencia,
sistema geodésico y alcance de avisos para la entrega derivada.
Se preparó una consulta limitada a estas preguntas, revisada y no enviada.
