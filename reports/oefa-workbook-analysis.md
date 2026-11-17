# Análisis completo de IPASH, EAC, EAF y EAT — aire

Revisión del 17/11/2026 UTC para #11. Se leyeron completas las cuatro hojas Aire (157 601 filas)
y se verificaron los hashes antes/después. No se reescribieron los originales, imputaron datos,
evaluaron fórmulas ni modificaron los límites del importador genérico.

Método reproducible: [herramienta de revisión](../tools/oefa-workbook-review/README.md).
Resultados resumidos y hashes: [metadata/oefa-workbook-analysis.json](../metadata/oefa-workbook-analysis.json).
Parquet/JSON detallados están en la ruta local indicada en ese registro, fuera de Git.

## Recomendación para AirAware

**Ninguno de estos cuatro archivos demuestra la meta de cuatro estaciones y 24 meses continuos
para el primer benchmark de Lima.** EAF es el candidato más útil para un piloto pequeño de eventos
en Lima, conservando su condición de campañas específicas. EAC aporta datos horarios adicionales
fuera de los contextos identificados textualmente como Lima, pero requiere revisión de calidad.
EAT e IPASH deben mantenerse como productos especializados separados del objetivo horario PM.
SENAMHI y la nueva exportación EAS siguen siendo candidatos prioritarios para investigar continuidad.
La selección científica sigue pendiente; esta revisión no habilita entrenamiento.

## Inventario y representación de valores

| Archivo | Filas | Parámetros (etiquetas) | Nombres de puntos | Fechas interpretables | Numéricos finitos | Censurados | Marcadores ausentes | Otros tokens |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| IPASH | 1 330 | 10 | 133 | 2019-04-13 a 2024-11-20 | 1 330 | 0 | 0 | 0 |
| EAC | 135 722 | 179 | 184 | 2017-03-02 a 2024-04-11 | 114 026 | 5 602 | 12 204 | 3 890 |
| EAF | 17 609 | 55 | 72 | 2018-04-12 a 2023-09-07 | 16 493 | 384 | 688 | 44 |
| EAT | 2 940 | 59 | 22 | 2017-05-08 a 2019-08-01 | 1 608 | 1 328 | 0 | 4 |

Las cuatro clases de valor son excluyentes y suman todas las filas. «Otros» no significa siempre
error: hay direcciones cardinales y nombres de minerales, además de códigos sin definición.
No se asume que todo parámetro deba ser numérico. Los puntos no son estaciones permanentes
homologadas; coordenadas/contextos producen 133/191/73/22 grupos provisionales respectivamente.
Los intervalos entre primera y última fecha no prueban continuidad dentro de esos años.

## Lectura por producto

### IPASH

Cada uno de sus 133 puntos tiene diez registros: mínimos/máximos/promedios de gases o propiedades
como O2, H2S, COV y límite inferior de explosividad. Las descripciones inspeccionadas corresponden
a mediciones breves en puntos/aberturas de pozos. Todas las filas tienen Periodo='-'; no hay series
PM10/PM2.5 horarias. Los 1 005 ceros se conservaron: no se convierten en ausencias ni en conclusiones
sanitarias. Su utilidad es de caracterización específica de sitio, separada del pronóstico ambiental PM.

### EAC

Incluye meteorología, gases, partículas y análisis de metales/minerales, con periodos horarios,
24 horas, 8 horas, mensuales o ausentes. Un metal medido en PM10 y el peso de un filtro no son
concentración total de PM10. Se mantienen esas familias fuera de los objetivos PM10/PM2.5.
Se observan tres contextos horarios para cada objetivo PM; su racha más larga es 542 horas.
No se identificaron entre ellos candidatos Lima con el criterio textual empleado.

### EAF

Tiene campañas focales y emergencias, incluyendo registros con menciones de San Juan de Lurigancho,
La Victoria y Lurigancho-Chosica. Los tres puntos OEFA P1/P2/P3 de enero–febrero 2019 pertenecen al
informe 00029-2019-OEFA/DEAM sobre una emergencia en San Juan de Lurigancho. Otros ejemplos son
CA-VIC-01 y CA-RZC-01 en marzo 2023, asociados a incendios urbano e industrial respectivamente.
Esto permite un piloto de episodios; no representa una red continua de observación rutinaria.

En los contextos candidatos Lima, las rachas PM2.5 más largas son 204 horas (P3), 110 (P1), 73 (P2),
40 (CA-RZC-01) y 20 (CA-VIC-01). El máximo de 204 h equivale a 8,5 días. La geografía se basa en
menciones textuales del registro, no en una homologación espacial o prueba de límites administrativos.
Las ventanas superpuestas no deben tratarse como ejemplos independientes ni dividirse aleatoriamente.

### EAT

Las 2 940 filas son muestras de 24 horas, con partículas, metales y otros parámetros de laboratorio.
1 328 valores (45,2%) están censurados: cadenas como <L.C. o <0.00013. Sustituirlos por cero o por
el límite alteraría la distribución. No se fabrican 24 mediciones horarias a partir de una muestra.
Puede aportar análisis de campañas/química atmosférica con un diseño distinto al objetivo horario.

## Ventanas estructurales y continuidad

Se conservaron informe/evaluación, punto/coordenadas, etapa, muestra, análisis, caracterización,
parámetro, unidad y periodo. No se concatenaron campañas de un mismo nombre de punto.
Solo entran valores finitos inequívocos con inicio alineado a la hora y periodo 1 hora. Los grupos
con valores censurados/ausentes, conflictos de valor o intervalos ambiguos no generan puntos.
Si el fin es interpretable se exige duración de 3600 s; si falta, no se inventa.

| Archivo / objetivo | Ventanas 24 h → 6 h, todos los contextos | Subconjunto con mención Lima | Ventanas 168 h → 24 h con mención Lima |
| --- | ---: | ---: | ---: |
| EAC PM2.5 | 1 645 | 0 | 0 |
| EAC PM10 | 1 645 | 0 | 0 |
| EAF PM2.5 | 647 | 491 | 13 |
| EAF PM10 | 951 | 491 | 13 |
| IPASH / EAT | 0 | 0 | 0 |

Se calcularon las 16 combinaciones de historias 24/48/72/168 h y horizontes 6/12/24/48 h. Las tablas
locales conservan conteos por contexto y pérdidas por historia/futuro incompletos. «Ventana completa»
aquí es estructura en el reloj de origen: **scientific_valid_windows permanece nulo**. Faltan confirmar
zona/convención del intervalo, calidad, identidad espacial y derechos. Cero del subconjunto textual
no prueba ausencia de mediciones de Lima en otros archivos, etiquetas o representaciones temporales.

## Hallazgos de calidad que requieren revisión

- EAC tiene 10 506 filas adicionales con todos los campos decodificados iguales; EAT tiene 80.
  No se eliminaron y no se afirma que todas sean observaciones físicas duplicadas. EAF/IPASH no
  mostraron repeticiones de ese tipo. La igualdad decodificada no equivale a igualdad de XML/estilos.
- EAC contiene 126 celdas de fórmula en Fecha fin. No se evaluaron ni se sustituyeron por caché;
  las filas se mantienen y el timestamp candidato se deja sin resolver de forma conservadora.
- EAC tiene 13 549 inicios no resueltos bajo este parser. Entre ellos hay 2 554 horas almacenadas
  como datetime con fechas de 1900 distintas de las bases admitidas, 10 838 horas marcadas ausentes,
  25 fechas de texto no admitidas y casos con fórmula/otros formatos. Las categorías de fecha/hora
  se superponen: consultar la tabla conjunta, no sumar los números sin considerar su intersección.
- Hay 18 intervalos negativos interpretables en EAC y nueve en EAF. Pueden requerir corregir fechas
  finales o documentación; no se suma un día automáticamente para hacerlos válidos.
- Códigos como N.D., NC, IE e ID quedan separados sin inventar significado. Los puntos cardinales
  de Dirección de Viento y nombres de Mineral pueden ser categorías legítimas, no errores numéricos.

Ejemplos trazables en la hoja Aire de EAC, conservados para revisión y sin borrado automático:

| Fila XLSX | Campo declarado | Valor / unidad | Qué revisar |
| ---: | --- | --- | --- |
| 46 339 | Humedad relativa | −100 % | Posible marcador o error de calidad; conservar y consultar |
| 89 859 | Velocidad del viento | 359,8 m/s | Posible problema de etiqueta, unidad o valor |
| 79 742 | Radiación solar | 23 576 W/m2 | Escala, unidad o captura del dato |
| 64 053 | Presión atmosférica | 1 011 mmHg | Consistencia de la unidad declarada |

Son señales de revisión, no diagnósticos certificados de falla instrumental. No se corrigen a partir
de valores «típicos» ni se convierten unidades por intuición. Los informes/códigos de punto están
registrados en el resumen para consultar el documento institucional correspondiente.

## Fechas, seguridad y reproducibilidad

Los cuatro libros declaran la época Excel de 1900 (1899-12-30 en el lector). Eso permite interpretar
sus propias celdas seriales/formateadas sin adivinar época. Excel no aporta por ello una zona horaria.
Tampoco confirma por sí solo que el CSV EAS independiente use la misma convención: contrastar registros
emparejados antes de fijar ese parser. Las fórmulas y errores Excel se conservan sin ejecutarse.

La herramienta usa openpyxl 3.1.5 read_only, defusedxml 0.7.1, et-xmlfile 2.0.0 y DuckDB 1.5.6 del
proyecto. El análisis es independiente del importador genérico: no se modifican sus límites Office
ni se presentan EAC/EAF como importaciones genéricas exitosas. Hay nueve pruebas de interpretación,
fixture XLSX y reconciliación, además de los controles del repositorio. Los archivos locales contienen
proveniencia por fuente/hoja/fila; no se publican observaciones masivas en Git.

## Próximos pasos recomendados para #11

1. Priorizar el parser largo de EAS y sus datos de Lima antes de sustituir el benchmark SENAMHI.
2. Conservar EAF como piloto de emergencias con objetivos/alcance separados y validación temporal.
3. Revisar en EAC unidades, códigos, fórmulas e intervalos contra los informes originales; documentar
   correcciones por regla y evidencia antes de transformar datos.
4. Mantener EAT/IPASH como productos especializados. Si se usan valores censurados o datos espaciales
   aislados, definir tareas compatibles en vez de forzarlos a un pronóstico horario.
5. Incorporar respuestas institucionales de #43/OEFA y revisar licencias por producto. No cerrar #11
   ni declarar elegibilidad científica con esta inspección solamente.
