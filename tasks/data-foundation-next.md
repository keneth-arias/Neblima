# Contrato común y diagnóstico EAS: implementación aprobada

Keneth aprobó la planificación e implementación el 17/11/2026. Tareas en GitHub #12/#11;
se conserva el resto de tasks/plan.md. No se cambia el objetivo PM2.5 de Lima.

1. #12: modelos versionados de procedencia, observaciones, fuentes, sensores, estaciones y
   reubicaciones. Separar valor original, censura, interpretación y evidencia; distinguir
   medición, derivación, modelo, reanálisis, pronóstico e imputación. Pruebas válidas e inválidas
   y guía para Cristopher. Aceptación: round-trip sin pérdida y rechazo de contradicciones;
   campos desconocidos nulos, sin exigir una selección anticipada de #11.
2. #11: lector de CSV largo EAS con vocabulario explícito, fechas como hipótesis separada,
   códigos desconocidos preservados, contexto/linaje y conflictos. Pruebas antes de lógica.
   Aceptación: ninguna fecha interpretada se presenta como confirmada por XLSX ajenos.
3. #11: ejecución completa local con DuckDB, hashes, conteos reconciliados y las 16 parejas H/F.
   Exportar resultados fuera de Git, comparar continuidad sin unir campañas; científico=nulo.
   Aceptación: todas las filas contabilizadas y originales intactos.
4. Revisar evidencia temporal/calidad/derechos pendiente de #43/OEFA; solo entonces seleccionar
   benchmark y continuar #13/#14/#15/#18/#19 e integración #20. Preparar lista de dudas por informe;
   no reenviar correos sin instrucción. Las decisiones de alcance vuelven a Keneth.

Cada entrega usa pruebas sin red, make check/build/audit y revisión antes de PR. Dos PR pequeñas
apiladas: contrato y diagnóstico EAS. No modificar copias de compañeros ni dependencias principales.
#20 permanece abierto hasta integración real #18; #11 hasta selección defendible.
