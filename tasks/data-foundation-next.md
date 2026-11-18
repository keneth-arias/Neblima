# Contrato común y diagnóstico EAS: implementación aprobada

> Estado de entrega: #11, #12 y #13 cerradas. La [ruta de primera ronda](plan.md) indica las dependencias actuales.
>
> Actualización del 17/11/2026: Keneth eliminó el requisito de cuatro estaciones/24 meses.
> Para SENAMHI se adopta UTC por confirmación del responsable, unidades inferidas aceptadas y
> ODC-BY-1.0 con atribución. Las afirmaciones de bloqueo anteriores son históricas; ver
> [decisión vigente](../docs/sources/senamhi-normalization-handoff.md).

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

## Resultado de implementación

- Incremento 1 integrado en PR #66; #12 completado con doce pruebas del contrato y guía.
- Incrementos 2/3 implementados en PR #67: 11 407 394 filas EAS, seis pruebas y reporte real;
  hipótesis de fecha explícita, hashes intactos, sin selección científica.
- Incremento 4 pendiente de evidencia institucional/documental y entregas #13/#14; no se
  puede acreditar reloj/calidad/derechos mediante una decisión técnica. #11/#20 siguen abiertos.
- 270 pruebas completas, build y auditoría aprobados; 47 pruebas focalizadas también en 3.11.
