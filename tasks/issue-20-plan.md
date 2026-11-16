# Plan de #20: etiquetas de episodios PM2.5

Responsable: Keneth. Investigación y módulo independiente autorizados por el usuario.
Se aplican planificación, implementación incremental y pruebas antes de código.

## Alcance y dependencias

#18 sigue abierta: no existe todavía un constructor de ventanas reales que integrar.
No asumir unidades, reloj ni validación de calidad en los datos SENAMHI (#43).
Mantener #20 abierta hasta verificar integración, salvo decisión explícita de separar esa entrega.
No cambiar tareas/ramas de Cristopher ni implementar el constructor de #18.

## Entregas

1. Verificar fuentes oficiales: DS 003-2017-MINAM, anexo (PM2.5 24 h, anual y frecuencia),
   DS 010-2019-MINAM, anexo 1 c.i/c.iii (día y suficiencia automática/manual).
   Evidencia local inmutable y sumas; archivos normativos fuera de Git.
2. Definir dos etiquetas independientes con contrato de entradas explícito: ventana futura de 24 h
   con 24 objetivos medidos válidos; día calendario de referencia con mínimo 18 horas automáticas.
   Sin afirmar cumplimiento legal anual ni ausencia de riesgo. No redondear antes de comparar.
3. Pruebas primero: igualdad/encima/debajo de 50, 17/18/23/24 válidos, negativos/no finitos,
   calidad inválida, duplicados, husos equivalentes, medianoche final, ventana móvil no diaria,
   unidades/semántica no sustentadas y conservación de IDs de observación.
4. Implementar módulo puro y configuración versionada; documentar límites y ejemplo reproducible.
   Separar resultado no evaluable de resultado no superior al umbral.
5. Revisar corrección, interfaces, seguridad y memoria. make check, build y audit; compatibilidad 3.11.
   PR con evidencia; no cerrar integración con #18 usando solo datos sintéticos.

## Investigación y decisiones

Revisión: 16/11/2026 UTC. SINIA/MINAM: páginas con navegación fallida, PDF bloqueados por robots
con Lightpanda. Alternativa oficial Gob.pe: catálogo MINAM 3670-003-2017-minam y catálogo MINEM
4773310-010-2019-minam; descargas CDN mediante Lightpanda, no fallback HTTP silencioso.
Protocolo inspeccionado en PDF página 93 (numeración impresa 90), anexo 1 c.i; umbrales en PDF
página 4 del DS 003-2017 (impresa 9). Anexo: 50 µg/m³ en 24 h, 25 anual, no más de 7
excedencias por año para el criterio diario. El módulo no evalúa el criterio anual.
Método automático: mínimo 18 horas válidas por día y promedios terminados 01:00 a 00:00 siguiente.
Método manual: muestra de 24 h con mínimo 22 h; no aplicar 18 de 24 a filtros gravimétricos.
El 100 % de objetivos de pronóstico es política de #18, independiente de suficiencia normativa.
