# Análisis de los cuatro libros OEFA solicitados

Autorizado por Keneth el 17/11/2026. Dependencia: recibos y originales de PR #64.
Alcance: IPASH/EAC/EAF/EAT completos, sin reescribir XLSX ni relajar límites del importador general.

1. Verificar hashes, época y estructura; lectura read_only con openpyxl 3.1.5, fórmulas sin evaluar.
   Herramienta de investigación aislada con dependencias explícitas, pruebas de fechas/horas/valores.
2. Perfilar valores finitos, censurados, ausentes, errores, periodos, parámetros/unidades y campos.
   Conservar tokens y contexto de informe/evaluación/punto/muestra; no convertir censura a cero.
3. Contar repeticiones exactas y conflictos por intervalo, cobertura/rachas y ventanas estructurales
   por contexto para PM10 y PM2.5 inequívoco. No fragmentar muestras de 24 horas en horas ficticias.
4. Evaluar geografía mediante menciones textuales identificadas como candidatas; no son homologación
   ni prueba de estar dentro de Lima. No transformar coordenadas sin CRS confirmado.
5. Publicar informe pequeño y Parquet/JSON locales con procedencia y verificación de integridad final.
   Comparar aptitud para pronóstico; mantener desconocidas zona/convención temporal, calidad y derechos.

Verificación: fuentes oficiales del lector, pruebas de casos límite y fixture XLSX; controles del repo;
reconciliar clases/filas y revisar resultados por las cuatro fuentes. No consultas o envíos nuevos a OEFA.
