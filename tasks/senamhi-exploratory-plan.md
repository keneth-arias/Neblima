# Uso exploratorio SENAMHI basado en dos referencias

Solicitud de Keneth: adaptar métodos de Cristhianbgf y DataGabo para comprender y usar SENAMHI.
Responsable de esta entrega: Keneth. Ref #11/#43; no sustituye la normalización #13 de Cristopher.

1. Fijar revisiones externas y leer código/cuaderno, sin ejecutar ni copiar código de terceros.
   Reutilizar revisión anterior de Cristhian y contrastar implementación real con README de DataGabo.
2. Implementar análisis local propio: identidad provisional existente, conflictos por señal,
   grilla horaria sin imputación, medias diarias con conteo/umbral 18, medias mensuales/anuales
   con denominadores explícitos, ciclos horarios y nombres distritales normalizados solo para análisis.
   Separar reloj crudo y escenario crudo−5 h. No inferir zona de producción ni reglas normativas.
3. Probar faltantes, cero, conflictos de otra señal, borde de día, estaciones sin valores,
   diferencias de reloj y agregación anual independiente. Ejecutar original completo, verificar SHA
   y registrar Parquet local, recibo y reporte. make check/build/audit antes de PR.
4. Entregar hallazgos/gráfico y guía de uso a #11/#13; conservar bloqueos científicos de #43.
   No incorporar ciclovías estáticas de 2023 como covariable de todo 2015–2024 ni atribuir causalidad.

Aceptación: reproducción sin red, originales intactos, conteos diarios reconciliados con la grilla,
ningún relleno de valores, códigos/filas conservados y decisiones temporal/calidad explícitas.

## Resultado

Implementado airaware.senamhi_exploration y ejecutado el original completo, con grillas y cinco
productos por señal/reloj, sin imputación. Cuatro pruebas nuevas aprobadas en 3.11 y 3.13;
274 pruebas totales, make check/build/audit aprobados. La mutación 18→17 horas fue detectada y
restaurada. Resultados y comparación de las 18 medias externas en reports/senamhi-exploration.md.
