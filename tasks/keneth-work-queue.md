# Cola de trabajo de Keneth para TimeNet

Estado al 18/11/2026. Las [asignaciones de GitHub](https://github.com/keneth-arias/airaware/issues?q=is%3Aissue%20is%3Aopen%20assignee%3Akeneth-arias)
dejan cuatro tareas abiertas con Keneth. El [manifiesto 24/6](issue-19-plan.md)
conserva 237 397 ventanas de entrenamiento, 50 706 de validación, 50 789 de prueba
y 313 purgas. #21–#25 cerraron con la [exportación TimeF](issue-22-plan.md), la
[reproducción offline](../tools/timenet-smoke/README.md), el
[aporte en borrador](https://github.com/OpenTSLM/TimeNet/pull/796) y las
[referencias congeladas](../reports/baselines/lima-pm25.md).

## Ruta para la primera ronda

| Tarea | Entrega | Verificación |
| --- | --- | --- |
| **#27** | Adaptar el modelo temporal al TimeF completo de #22. Confirmar revisión, licencia de código y pesos, interfaz de seis valores y presupuesto antes de descargar pesos o ajustar. | Verificar dimensiones, máscaras, orden y ausencia de objetivos en la entrada. Registrar un paso de ajuste con pérdida finita, comando, revisión, duración y memoria. |
| **#28** | Ajustar con entrenamiento, seleccionar con validación y evaluar la configuración elegida en prueba. Conservar los identificadores de #25 y reportar el caso de uso y los límites. | Unir por `window_id` y `forecast_hour`, comprobar los valores objetivo, documentar cobertura y reportar errores por estación y horizonte. Persistencia es la referencia primaria seleccionada en validación. Documentar presupuesto, semilla y ejemplo de error para #29. |

Cristopher y Jordan llevan #29. Pueden usar ahora la [ficha y sus límites](../docs/dataset-cards/lima-pm25-forecast.md),
el enlace del borrador y los resultados de las referencias. El modelo y sus resultados
quedan pendientes de #27 y #28. La [guía de entrega](../docs/hackathon.md) distingue el
material preparado de los enlaces y autorizaciones pendientes.

## Ampliaciones y seguimiento

- **#14.** #73 integró la depuración SENAMHI. Las fusiones entre proveedores requieren
  correspondencias sustentadas por identidad, equipo y vigencia.
- **#43.** Registrar aclaraciones institucionales sobre intervalo, calidad, cambios de equipos
  y unidades. La consulta de seguimiento del 17/11 también se remitió a José Luis Rodríguez.
- **#17.** Cristopher lleva [la alineación meteorológica](https://github.com/keneth-arias/airaware/pull/85).
  La muestra de #79 solo toca entrenamiento. El [plan de implementación](plan.md) registra
  el alcance del cruce y los requisitos de una evaluación posterior.
- **#20.** Cristopher lleva [la integración de etiquetas](https://github.com/keneth-arias/airaware/pull/86).
  La prueba estructural de ventanas de 24 horas y la emisión de etiquetas tienen criterios propios.

## Integración de cada PR

Actualizar la rama base con la entrega que consume. Escribir pruebas antes de cambiar
la lógica y registrar `make check`, `make build` y `make audit`. Confirmar en GitHub ambos
controles por versión de Python y la auditoría. Versionar evidencia compacta y mantener
los artefactos grandes en almacenamiento local. Referenciar la tarea en un avance parcial
y cerrar cuando la evidencia acredite sus criterios.
