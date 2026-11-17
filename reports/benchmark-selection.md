# Selección inicial completada — #11

Keneth aprobó la política operativa el 17/11/2026. Se selecciona **SENAMHI, Lima, PM2.5 horaria**
para el primer conjunto de pronóstico retrospectivo, bajo [ADR-005](../docs/decisions/005-senamhi-operating-policy.md).
La comparación real se repitió con comparison-v3 y se verificaron hashes de originales y salidas.
Recibo completo: [metadata/benchmark-selection.json](../metadata/benchmark-selection.json).

## Alcance aceptado

- Timestamp publicado UTC, sin inventar si es inicio/fin de promedio; observed_at conserva la etiqueta.
- Unidades ug/m3 inferidas aceptadas, ODC-BY-1.0 con atribución, originales inmutables.
- Calidad individual unknown; ausencia de flags no se interpreta como validación instrumental.
- Sin cuota fija de estaciones o meses; sin imputación para crear observaciones o completar objetivos.
- Duplicados/conflictos por señal, ventanas con historia y futuro completos, particiones cronológicas.
- Sin habilitar etiquetas regulatorias diarias ni afirmar disponibilidad operativa en tiempo real.

## Evidencia de disponibilidad

| Historia (h) | Futuro (h) | Ventanas aceptadas por la política |
| ---: | ---: | ---: |
| 24 | 6 | 339 205 |
| 24 | 24 | 324 463 |
| 72 | 24 | 290 492 |
| 168 | 24 | 238 014 |

Se conservaron las 16 parejas H/F en el recibo y siete identidades provisionales con ventanas.
Estos conteos se superponen y no son ejemplos independientes ni particiones de entrenamiento.
No se eligió H/F por resultados de modelos. Identidad/normalización y ventanas materializadas se
implementan en #13/#14/#18; cerrar selección no afirma haber completado esas tareas.

accepted_forecasting_windows registra la aceptación operativa exclusivamente para el SHA, fuente,
geografía y señal aprobados. scientific_valid_windows permanece nulo para este escenario: aceptar
el uso bajo incertidumbre no certifica la calidad de mediciones. No se generan puntuaciones basadas
en cuotas; componentes/puntuaciones permanecen nulos. Los bloqueos OEFA o de otros usos no se borran.
Una configuración con otro SHA, otro ámbito o bloqueos no aceptados es rechazada; sin ventanas
completas tampoco se publica selección aprobada.

## Cierre y seguimiento

#11 está completo con una selección justificada y una política explícita aprobada. #43 continúa para
posición del intervalo y calidad; #20 sigue abierto hasta integración real de #18 y metadatos compatibles
con etiquetas diarias. No se requieren esas respuestas para normalizar o preparar el pronóstico
retrospectivo aceptado. No se enviaron correos ni se modificaron copias de compañeros.

Validación: cinco pruebas nuevas de selección, incluyendo no transferir aprobación, rechazar
bloqueos ajenos, prohibir etiquetas regulatorias y exigir ventanas completas. La mutación que
presentaba los conteos como validación científica fue detectada y restaurada. Controles del proyecto,
pruebas en Python 3.11/3.13, build y auditoría aprobados; hashes de entradas/salidas comprobados.
