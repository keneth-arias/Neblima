# Cola de trabajo de Keneth para TimeNet

Estado al 18/11/2026. Las [asignaciones de GitHub](https://github.com/keneth-arias/airaware/issues?q=is%3Aissue%20is%3Aopen%20assignee%3Akeneth-arias)
dejan nueve tareas abiertas con Keneth. #15, #18 y #19 están cerradas por
[#74](https://github.com/keneth-arias/airaware/pull/74),
[#75](https://github.com/keneth-arias/airaware/pull/75) y
[#76](https://github.com/keneth-arias/airaware/pull/76). El insumo de evaluación es el
[manifiesto 24/6](issue-19-plan.md) con 237 397 ventanas de entrenamiento, 50 706 de
validación y 50 789 de prueba. Conserva otras 313 ventanas purgadas.

## Ruta para la primera ronda

La ruta principal es #21 → #22 → #23 y #25 → #27 → #28. #24 puede adelantar su ficha
y coordinar la vía de aporte mientras se implementa la exportación. Su verificación final
usa el recibo de #23. La demo y la entrega de #29 reúnen los resultados de #24 y #28.
La matriz de entrega y el plazo oficial están en [la guía del hackathon](../docs/hackathon.md).

| Orden | PR y entrega | Verificación para integrar o cerrar |
| --- | --- | --- |
| 1 | **#21, [PR #77](https://github.com/keneth-arias/airaware/pull/77)**. Ida y vuelta sintética con TimeNet 0.12.0 en el entorno fijado. | Actualizar la rama con `main` y verificar el nuevo commit. Los tres controles pasaron en `5994513`, anterior a la integración del plan #72. La prueba offline confirma eje horario UTC, origen, unidad, procedencia, valor finito, cero y nulo. Cierra la entrega sintética; #21 continúa en el siguiente PR. |
| 2 | **#21, PR de conversión real**. Leer una selección explícita de estación y horas de SENAMHI. Verificar manifiesto y rechazos de #13 y reutilizar la depuración y grilla de main. Escribir una versión local con atribución, unidad inferida y vínculo a la fuente y a las filas de auditoría. | Dos ejecuciones nuevas deben producir el mismo contenido lógico. Comprobar valores y nulos con el lector oficial y rechazar un archivo alterado. Registrar la selección y sus sumas SHA-256. El cero ya tiene prueba sintética; la grilla real de PM2.5 carece de ceros observados. Cierra #21. [Plan del conector](issue-21-plan.md). |
| 3 | **#22, PR de exportación TimeF**. Materializar la base para la cobertura evaluada, fijar su versión y comprobar en el kit de desarrollo la representación de intervalos de entrada y objetivo. Exportar `ForecastingTask` con las decisiones exactas de #19 y un índice que vincule cada tarea a `window_id`. | La historia contiene 24 valores hasta el origen inclusive; el objetivo empieza una hora después y contiene seis valores. Verificar con el lector oficial todas las asignaciones e identificadores de la cobertura entregada, reconstruir ejemplos de las tres particiones y excluir las 313 purgas del experimento completo. Probar repetibilidad, nombre y versión del conjunto y resolución local del padre si se usa composición. Cierra #22. |
| 4 | **#23, PR de reproducción offline**. Incorporar a la integración continua una muestra pequeña desde adquisición local hasta lectura de una tarea TimeF. Mantener fijados el entorno de AirAware y el de TimeNet. | Después de instalar dependencias, reproducir de extremo a extremo con la red deshabilitada. Comprobar procedencia, ventanas, fugas y lectura; alterar un artefacto y comprobar el fallo. Guardar comandos, versiones, hashes, duración y memoria. Cierra #23. |
| 5 | **#25, PR de modelos de referencia**. Con la versión de #22, evaluar persistencia, valor de la misma hora del día anterior y promedio estacional ajustado con entrenamiento. Para 24/6, las seis observaciones del día anterior están dentro de la propia historia de 24 horas. | Verificar con una serie sintética los índices y las métricas. Fijar la referencia principal con validación y aplicar la misma transformación a prueba. Entregar predicción e ID por ventana y hora futura, conteos, error absoluto medio (MAE), raíz del error cuadrático medio (RMSE) y error absoluto escalado medio (MASE) cuando el denominador de entrenamiento sea válido. Registrar cobertura, resultados por estación y temporada y errores en concentraciones altas con un criterio fijado en entrenamiento. Cierra #25. |
| 6 | **#27, PR de adaptador y prueba de ajuste**. Una vez verificadas #23 y #25, confirmar que la revisión candidata de OpenTSLM admita el objetivo de seis valores y comprobar licencia de código y pesos. Ejecutar un lote aprobado desde TimeF dentro del presupuesto de Keneth. | Probar dimensiones, orden, máscaras y ausencia de objetivos futuros en la entrada. Requerir pérdida finita en un paso de ajuste y registrar revisión, comando, tiempo y memoria. Si la interfaz elegida no soporta pronóstico numérico, elevar la elección de modelo con evidencia antes de descargar pesos. Cierra #27. |
| 7 | **#28, PR de experimento y evaluación**. Fijar revisión, semilla, recursos y manifiesto de #19/#22. Ajustar en entrenamiento, seleccionar la configuración en validación y evaluar en prueba. | Unir predicciones y referencias por ID y hora futura. Registrar predicciones inválidas y su cobertura, métricas en µg/m³ sobre objetivos comunes, tamaño de muestra por estación y horizonte y un ejemplo de error para #29. Documentar costo y límites, incluso si gana la persistencia. Cierra #28. |

#23 y #25 dependen de #22 y se pueden invertir según el estado de revisión. Con una sola
implementación activa para Keneth, conviene terminar y verificar #23 y luego ejecutar #25.
Para #22, comenzar con una muestra local que abarque las tres particiones y usarla para
medir costo de escritura y lectura antes de escalar. Si hace falta limitar el tamaño de
la entrega, fijar la regla de muestreo por estación, fecha y partición antes de evaluar.
Publicar cobertura y hashes del conjunto elegido. #25, #27 y #28 deben consumir esa misma versión.

## Aporte a TimeNet y decisiones de Keneth

| PR propuesto | Entrega y criterio de cierre |
| --- | --- |
| **#24, PR de ficha y reproducción en AirAware** | Documentar fuente, atribución, cobertura efectiva, datos faltantes, deduplicación, cortes, límites de uso y comando de reproducción. Pasar el borrador a los responsables de #29. Completar las cifras con los manifiestos de #22 y la evidencia de ejecución con #23. |
| **#24, PR externo de datos y conector en TimeNet** | Preparar el aporte mínimo separado y comprobarlo contra la revisión acordada. Registrar autoría y permiso de los archivos, según [ADR-003](../docs/decisions/003-licencia-agpl-v3.md). Abrirlo tras la autorización externa y registrar la URL en #24 y #29. Para cerrar #24, acreditar la ficha, la contribución preparada y los controles de la revisión fijada. El enlace externo es un requisito adicional para la entrega del hackathon. |

Resolver con Keneth la autoría y licencia del aporte externo y el permiso para publicarlo.
Antes de #27, acordar revisión y licencia del modelo, límite total de descarga, duración y
costo. Si el equipo de #29 prepara difusión o envío del formulario, confirmar las
autorizaciones correspondientes. Las demás decisiones de implementación siguen los
manifiestos, [las interfaces fijadas](../docs/timenet-integration.md) y ADR-005.

## Seguimiento fuera de la ruta principal

| Tarea de Keneth | PR condicionado a evidencia |
| --- | --- |
| **#14** | La depuración SENAMHI se integró en #73. El siguiente PR debe justificar correspondencias entre proveedores por código, ubicación, instrumento y vigencia. Probar precedencia de una copia demostrada y separación de sensores independientes. Las fichas actuales orientan la búsqueda; los cambios históricos requieren evidencia fechada. |
| **#43** | Registrar evidencia institucional sobre etiqueta horaria, calidad, cambios de equipos o ubicación y unidades. El seguimiento al SENAMHI del 17/11 también se remitió a José Luis Rodríguez. Si una aclaración cambia la interpretación, versionar la política y reproducir el caso afectado. Documentar preguntas que sigan abiertas. |

Cristopher tiene #20 y #32. #20 conserva el requisito de integración real y metadatos
compatibles para etiquetas. #32 depende de datos nacionales compatibles de #30.
Cristopher y Jordan llevan #29. Las asignaciones vigentes se consultan en GitHub.

## Integración de cada PR

Actualizar la rama base con la entrega que consume. Escribir pruebas antes de cambiar la
lógica y registrar `make check`, `make build` y `make audit`. Confirmar en GitHub ambos
controles por versión de Python y la auditoría. Versionar sumas y recibos compactos; los
datos y pesos grandes quedan en almacenamiento local. Referenciar la tarea en un avance
parcial y usar la palabra clave de cierre en el PR que acredita sus criterios.
