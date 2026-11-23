# Revisión de métodos SENAMHI y diccionario OEFA

> Decisión vigente del 17/11/2026: [SENAMHI listo para #13](senamhi-normalization-handoff.md).
> UTC confirmado por Keneth, unidades inferidas aceptadas y ODC-BY-1.0 con atribución.
> Esta revisión previa se conserva como evidencia histórica, no como bloqueo de normalización.

Revisión: 17/11/2026 UTC, Keneth. Evidencia para #11/#43; no cambia reglas ni originales.
Registro numérico reproducido: [metadata-methods-review.json](../../metadata/metadata-methods-review.json).
Se leyó código externo, sin ejecutarlo ni instalar sus requisitos en Neblima. No se copió su código.

## SENAMHI: referencia externa identificada

Repositorio [Cristhianbgf/calidad-aire-lima](https://github.com/Cristhianbgf/calidad-aire-lima), revisión
[8d2deaa70c9e6c4d0d4b2b6699cda3b3a6dfa85f](https://github.com/Cristhianbgf/calidad-aire-lima/tree/8d2deaa70c9e6c4d0d4b2b6699cda3b3a6dfa85f).
Su README fija el mismo SHA-256 y tamaño que nuestra adquisición SENAMHI: por tanto las decisiones
son comparables sobre los mismos bytes, no solo conjuntos con nombres parecidos. Su código usa MIT;
los derechos de datos se describen por separado. No es documentación institucional del exportador.

### Qué aportan sus métodos

[preparar_datos.py](https://github.com/Cristhianbgf/calidad-aire-lima/blob/8d2deaa70c9e6c4d0d4b2b6699cda3b3a6dfa85f/src/preparar_datos.py)
construye una grilla horaria completa por estación, distingue cobertura de medias y cuenta horas
para medias diarias. Exige 18 horas para conservar una media diaria. Es útil como método candidato
para #20; no convierte una historia incompleta en una ventana completa para #11/#18.

Sus denominadores diarios incluyen horas del calendario completo; Neblima limita ciertos diagnósticos
al primer/último punto admisible. Comparar porcentajes exige igualar denominadores. Sus coordenadas
se toman del primer registro por nombre: no sustituye la identidad provisional ni un historial de #14.

### Hallazgos que impiden adoptarlo sin revisión

- La hora se obtiene dividiendo el campo por 10 000 y truncando; no valida minutos/segundos como
  nuestro parser. El archivo actual está alineado a horas, pero el método ocultaría otros valores futuros.
- Convierte errores numéricos a ausentes y anula negativos. Neblima conserva tokens y banderas;
  este archivo no tenía negativos finitos, pero la política no debe generalizarse a otras fuentes.
- Resuelve repeticiones comparando las tres señales juntas y descarta toda la estación/hora si algún
  vector difiere. Eso puede retirar una señal inequívoca por conflicto en otra. Neblima distingue
  conflictos por señal y conserva los originales; no copiar sus conteos como si fueran nuestra política.
- El README sitúa los 42 grupos conflictivos el 1 de mayo de 2024. La reproducción local encontró
  **35 el 01/05 (00–04 h, siete estaciones) y siete el 30/05 (00 h)**. El código cuenta grupos sin
  afirmar esa fecha; la discrepancia es del resumen documental. No equivale a 42 filas adicionales.
- [verificar_boletin.py](https://github.com/Cristhianbgf/calidad-aire-lima/blob/8d2deaa70c9e6c4d0d4b2b6699cda3b3a6dfa85f/src/verificar_boletin.py)
  contrasta solo tres máximos PM10 y no convierte el reloj. Busca el máximo antes de exigir 18 horas;
  ese filtro solo se usa allí para contar excedencias. No prueba las unidades de todos los contaminantes.
- [construir_dashboard.py](https://github.com/Cristhianbgf/calidad-aire-lima/blob/8d2deaa70c9e6c4d0d4b2b6699cda3b3a6dfa85f/src/construir_dashboard.py)
  rotula el ciclo como hora local UTC−5, aunque la preparación no localiza ni convierte los timestamps.
  Una etiqueta del gráfico no confirma la zona de los datos.
- [cumplimiento.py](https://github.com/Cristhianbgf/calidad-aire-lima/blob/8d2deaa70c9e6c4d0d4b2b6699cda3b3a6dfa85f/src/cumplimiento.py)
  redondea la media anual antes de compararla en el resumen con los límites. La regla del README de
  comparar antes de redondear sí se conserva en medias diarias, pero no en esa ruta anual. Es un riesgo
  de frontera, no una afirmación de cuántos resultados del archivo cambian: no se cuantificó ese efecto.
  Su 75% anual es una decisión implementada; no se adopta como requisito normativo sin fuente primaria.

## Contraste independiente con el boletín SENAMHI

Se reutilizó el PDF oficial local de [febrero 2018](https://www.gob.pe/institucion/senamhi/informes-publicaciones/6613132-boletin-vigilancia-de-la-calidad-del-aire-en-lima-metropolitana-y-el-callao-febrero-2018),
páginas 6–7, inspeccionadas visualmente además de extraer su texto. PM10 y PM2.5 están allí en µg/m³.
El contraste anterior de cinco máximos horarios NO2 ya sustentaba una diferencia de cinco horas;
se eligió ese desplazamiento antes del nuevo contraste PM, no se ajustó buscando el mejor máximo.

Se reprodujo con DuckDB propio la vista de vectores distintos y exclusión de estación/hora conflictiva
para comparar con la referencia. Solo es una vista temporal: no sustituye nuestra política por señal.
Se calcularon medias por día en dos relojes: crudo y crudo−5 h. Para el contraste ampliado se exigieron
al menos 18 valores del contaminante por día; también se registraron máximos sin ese filtro para
mostrar su efecto. No se ejecutó el código de terceros.

| Estación | PM10 boletín | PM10 crudo−5 h (día) | PM2.5 boletín | PM2.5 crudo−5 h (día) |
| --- | ---: | --- | ---: | --- |
| Campo de Marte | 40,4 | 40,352917 (03) | 17,4 | 17,420833 (01) |
| Carabayllo | 89,5 | 89,460833 (24) | 49,5 | 49,475000 (23) |
| San Borja | 67,7 | 67,705417 (03) | 17,1 | 17,142857 (16) |
| San Juan de Lurigancho | 106,1 | 106,086250 (24) | 34,6 | 34,570833 (23) |
| San Martín de Porres | 95,4 | 95,389167 (13) | 19,9 | 19,854167 (23) |

Los diez valores coinciden a la precisión de una decimal del boletín y coinciden sus fechas.
San Borja/PM2.5 tiene 21 horas; los otros nueve controles tienen 24. Sin filtrar días incompletos,
Campo de Marte/PM2.5 mostraría un máximo de 13 horas en otra fecha: no debe usarse para concluir
que el boletín difiere. En reloj crudo, Carabayllo/PM10 da 97,252083, no 89,5; la diferencia se explica
por el límite del día en este contraste, sin necesitar atribuirla a una revisión de valores.

**Conclusión acotada:** evidencia fuerte y consistente con exportación UTC y concentraciones PM en
µg/m³ para estos casos de febrero 2018, reforzada por el contraste previo de NO2. No confirma todo
2015–2024, la definición inicio/fin del promedio, factores de conversión de gases o banderas perdidas.
Por eso no se convierte el reloj de producción ni se habilita el benchmark a partir del repositorio.

## OEFA: qué resuelve el XLSX proporcionado

Se inspeccionaron las celdas XML originales del [diccionario oficial](https://www.datosabiertos.gob.pe/sites/default/files/1c_Formato_DiccionarioDatos_Vigilancia%20y%20Seguimiento%20ambiental%20en%20la%20calidad%20del%20aire.xlsx).
Es el mismo archivo ya preservado: SHA-256 4f2fe50d1166ca23e0447ea5dbe9051a4e4731600b2f5bec007ae5d75017c5bb.
No fue necesario descargarlo otra vez. La lectura cubrió todas las filas definidas, no una muestra.

| Filas del XLSX | Información explícita | Límite de la definición |
| --- | --- | --- |
| 19–21 | Tipo de muestra, análisis y periodo de recopilación; ejemplos horarios y móviles | No define completamente vocabularios ni cuándo está disponible un promedio móvil |
| 22–25 | Fechas/horas de inicio y fin de monitoreo; formatos aaaammdd y HH:MM | El CSV difiere de formato y tiene NA/fechas base 1899; no permite reconstruir horas ausentes ni zona |
| 26 | Unidad asociada al parámetro; ejemplo ug/m3 | No asigna una unidad universal a todas las columnas meteorológicas/gases |
| 27–39 | Identidad de parámetros y precisión decimal indicada para algunos | No equivale a resolución real del instrumento ni banderas de validación |
| 9–13 | Este/Norte, datum, zona y altitud en metros sobre el nivel del mar | No declara por sí solo un EPSG/hemisferio completo para cada estación |
| 40 | Fecha de generación del conjunto | No es fecha de medición ni un campo sin documentar |

Cruce local de signals.parquet por unidad y tipo de análisis, conservando el contexto de cada serie:

- PM2.5: las 94 371 celdas finitas tienen unidad ug/m3 y análisis específico de partículas PM2.5.
- PM10: las 202 057 celdas finitas tienen unidad ug/m3; 165 520 bajo análisis específico PM10,
  36 525 bajo la categoría general de material particulado y 12 con análisis NA.
- Temperatura: las 223 493 celdas finitas tienen unidad °c y análisis meteorológico. No aplicar ug/m3
  a las variables meteorológicas por ser un ejemplo del diccionario.

**Lo que se puede precisar ahora:** las etiquetas de unidad de PM2.5/PM10 están documentadas y
corroboradas en todos sus valores finitos del archivo. No deben seguir describiéndose como unidades
PM totalmente desconocidas. Se mantienen grupos de análisis separados; los 12 PM10 con análisis NA
requieren una política explícita de contexto/calidad. No se infieren condiciones de referencia de gases.

**Lo que sigue abierto:** hora/intervalo efectivos y zona, recuperación de los inicios faltantes de Lima,
marcadores/no aplica, identidad de observaciones y repeticiones, banderas de calidad, historia espacial,
atribución y diferencias entre productos. El diccionario no contiene esas respuestas ni nuevos registros.

## Aplicación a las tareas

1. #43: agregar los diez controles PM al contraste NO2; no repetir el correo ni formular preguntas
   sobre definiciones ya presentes. Usar esta evidencia al interpretar la respuesta institucional.
2. #11: distinguir confirmación oficial de la etiqueta de unidad OEFA, evidencia empírica de reloj SENAMHI
   y dudas restantes. En una próxima revisión de la política, reemplazar el bloqueo global de unidades
   OEFA por reglas por señal/contexto; el archivo benchmark.yaml actual es conservador y no se cambia
   ni se vuelve a puntuar en esta revisión documental. Todos los bloqueos temporales/calidad siguen activos.
3. #12/#13/#18: proponer metadatos de unidad por señal, hipótesis con evidencia/versiones y separación
   del reloj crudo; no convertir implícitamente a hora local ni eliminar señales sanas por conflictos ajenos.
4. #20: estudiar agregados diarios con completitud explícita y comparaciones sin redondeo previo,
   usando las fuentes normativas primarias y manteniendo aparte el objetivo de pronóstico horario.

La revisión no declara cerradas #11/#43 ni cambia puntuaciones, etiquetas, datos o licencias.
