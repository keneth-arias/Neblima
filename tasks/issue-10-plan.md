# Plan actualizado de #10: perfilamiento local reproducible

Responsable: Keneth. Autorización: mejorar el plan y comenzar implementación, sin nueva adquisición.
Dependencias #8/#9 cerradas. Fuente de tareas: issue #10 en GitHub. No tocar ramas del equipo.

## Insumos y contratos

- SENAMHI: data/raw/senamhi/senamhi_lima_monitoreo_1.csv, 68 501 558 bytes, 577 794 filas,
  15 columnas; metadata/senamhi-lima-download.json y manifiesto de adquisición de #8.
- OEFA: data/raw/oefa/oefa_eas_20261116.csv, 1 317 949 839 bytes, 2 883 877 filas,
  36 columnas; metadata/oefa-lightpanda-download.json. Descarga Lightpanda completa, no prefijo.
- Hashes/manifiestos comprobados antes de procesar; columnas/delimitadores exactos, sin inferir tipos.
  No descargar otra vez. Lectura de originales solamente; salidas generadas locales, fuera de Git.

## Decisiones de metodología

1. Identidad provisional por nombre + coordenadas/datum/zona y ubicación textual de la fuente.
   Es una agrupación de filas, no homologación de estaciones (#14). No convertir UTM ni unir fuentes.
2. OEFA separa series por evaluación, periodo, unidad, análisis, tipo/procedencia de muestra.
   No mezclar muestras de una hora con promedios móviles o 24 h ni confundir filas con mediciones
   simultáneas de todos los contaminantes. Informar celdas por señal y categorías de análisis.
3. Parseo temporal solo sintáctico en reloj original **sin zona confirmada**: SENAMHI FECHA/HORA;
   OEFA FECHA_INICIO/HORA_INICIO y FECHA_FIN/HORA_FIN. Conservar cadenas y contar fallas.
   Las fechas base 1899 de horas OEFA se reconocen como forma textual, no como fecha de medición.
   Huecos son diagnósticos de rejilla horaria del reloj crudo; no ventanas válidas ni cobertura UTC.
4. Distinguir vacío, marcador literal y no numérico; no convertirlos en cero. Registrar tokens y sus
   frecuencias, sin asumir significado de '-', NA o banderas. No convertir unidades/decimales.
5. Duplicado de fila exacta y candidato de misma serie/intervalo son métricas separadas. Conflicto
   significa varios valores numéricos finitos en el mismo intervalo comparable, no decisión de borrado.
6. Constantes y rachas se calculan sobre valores finitos de instantes únicos no conflictivos, sin
   atravesar huecos/ausencias. Extremos se describen con mínimo/máximo y regla exploratoria IQR;
   se retienen episodios, negativos y ceros. Ninguna marca declara mala calidad por sí sola.
7. No usar estadísticas globales del perfil para imputar/escalar modelos o seleccionar umbrales
   retrospectivamente: entrenamiento/particiones se definen después en #19 y tareas relacionadas.

## Incrementos y verificación

A. Contrato/lectura determinista con DuckDB local, columnas VARCHAR, memoria 768 MiB, 2 hilos,
   temporales en disco local y extensiones automáticas deshabilitadas. Se añade DuckDB solo porque
   ejecuta agregaciones y exporta Parquet sin cargar el CSV de 1,3 GB completo en Python.
   Pruebas primero con muestras sintéticas claramente identificadas: dialectos, espacios/vacíos,
   marcadores, formatos temporales, grupos comparables y rechazo de entradas alteradas.
B. Métricas y salidas: datasets.parquet, stations.parquet, signals.parquet y tokens.parquet,
   con IDs de fuente/suma/versiones y definiciones explícitas de denominadores. Reportar errores
   sin descartar silenciosamente filas ni convertir datos desconocidos en cobertura confirmada.
   Pruebas: huecos reales/orden invertido/duplicados, conflictos vs repeticiones idénticas,
   constantes/rachas interrumpidas, valores negativos/no finitos y extremos conservados.
C. Comando CLI y configuración portable por fuente; publicar en carpeta nueva por ejecución,
   nunca sobre raw ni sobre informes previos. Pruebas sin internet leen de vuelta Parquet y comprueban
   conteos/schemas; CI nunca requiere los originales masivos ni DuckDB remoto.
D. Ejecutar ambas fuentes reales y generar informe pequeño en español con rutas/hash y métricas;
   Parquet/base temporal bajo reports/generated/ fuera de Git. Comparar conteos con #8/#9 y registrar
   tiempo/archivos de salida. No elegir benchmark #11 ni declarar elegibilidad científica.

Archivos: src/airaware/profiling/, configs/profiling.json, tests/test_profiling.py,
reports/profiling.md, actualización de CLI y dependencias fijadas. Dividir PR si excede una revisión.
Puntos de control: primero fixtures; luego datos completos; después make check/build/audit y revisión.

## Cierre y límites

Cerrar solo con informes Parquet reproducibles de ambas fuentes, conteos/intervalos reales, pruebas y
bloqueos semánticos documentados. Si no puede medirse una métrica, dejarla nula con motivo, sin afirmar
cierre total. #43 mantiene las aclaraciones SENAMHI; dudas OEFA siguen en docs/sources/oefa.md.
Los IDs provisionales y el reloj sintáctico no autorizan por sí solos normalización, ventanas o publicación.
