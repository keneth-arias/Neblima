# Cola de trabajo de Keneth: datos y plataforma

Estado revisado el 17/11/2026. Consulta la [ruta de primera ronda](plan.md). El usuario autorizó planificar e implementar sus tareas asignadas,
investigar información faltante y consultar decisiones pendientes. Conserva el idioma español del Perú
en el repositorio; respuestas y resúmenes para Keneth en inglés.

## Solicitudes de incorporación para las 12 tareas abiertas de Keneth

Estado al 17/11/2026. El [PR #73](https://github.com/keneth-arias/airaware/pull/73)
ya está en `main`. Su auditoría horaria de SENAMHI satisface la dependencia de datos de #15.
La conciliación entre proveedores de #14 sigue abierta. El [PR #72](https://github.com/keneth-arias/airaware/pull/72)
organiza el trabajo documental. Las entregas que siguen son PR propuestos, cada uno con su
propia revisión. El orden recomendado para Keneth es #15, #18 y #19; #21 se puede adelantar
cuando una de esas entregas esté en revisión. Después confluyen en #22.

### Datos de Lima

| PR propuesto | Insumo y cambio | Prueba que permite cerrar la tarea al integrar |
| --- | --- | --- |
| **#15 · Construir la grilla horaria con máscaras** | Leer la auditoría de #73 en `data/curated/`. Crear una fila por identidad provisional, señal compatible y hora entre sus extremos publicados en tiempo universal coordinado (UTC). Conservar el vínculo a la auditoría, el cero medido y las máscaras de ausencia e imputación. | Probar cero, repetición con celda vacía, conflicto y hora sin fila. Repetir la construcción y comparar claves, valores y máscaras. Para PM2.5, conciliar por estación las **577 717** horas de grilla que se detallan debajo. Entregar el Parquet local y su manifiesto a #18. |
| **#18 · Generar ventanas completas con objetivos medidos** | Consumir la grilla de #15. Configurar historia, horizonte y paso. Guardar identidad, origen, límites y referencias a las horas de cada ventana. Entregar secuencia futura y objetivo escalar para el horizonte configurado, incluido el promedio de 24 h cuando corresponda. | Con paso de 1 h, 30 horas consecutivas aportan exactamente una ventana de historia 24 h y futuro 6 h. Un hueco en la historia o en el objetivo la invalida. Verificar límites de estación y conciliar **339 205** ventanas antes de particionar con `comparison-v3`. Guardar desglose de descartes y validar los demás pares configurados contra el informe de #11. |
| **#19 · Congelar las particiones y probar las fronteras** | Consumir identificadores de #18. Proponer dos cortes UTC comunes a Lima alrededor de 70/15/15 según la cobertura temporal. Registrar fechas, asignación y ventanas purgadas por estación; congelar la versión antes de comparar modelos. | Probar ventanas que terminan en el corte y que lo cruzan, duplicados y variables con disponibilidad posterior al origen. Comprobar que ninguna hora de historia u objetivo de una serie aparece en dos particiones, que toda ventana recibe una decisión y que el preprocesamiento se ajusta solo en entrenamiento. Reproducir el manifiesto y publicar las proporciones efectivas tras la purga. |

Para #15, la auditoría con SHA-256 `86170e033b81bd6b53fdf0b044df3df36243ae2c4819a41821ecb839c13ee661`
da siete identidades. Agrupando PM2.5 por identidad y hora, hay **367 518** horas con valor,
**20** horas en conflicto y **210 172** horas con filas pero sin valor utilizable. Dentro del
intervalo de cada estación faltan **7** horas sin fila en total. Los **70** de #73 cuentan
lecturas en conflicto, algunas de la misma hora. Estos conteos corresponden a la entrada
verificada en [la entrega de #14](issue-14-plan.md).

### TimeNet, validación y modelo

| PR propuesto | Dependencia y entrega | Evidencia de aceptación |
| --- | --- | --- |
| **#21 · Escribir y leer una serie sintética** | Disponible con #1 y #13 cerradas. En `tools/timenet-smoke`, usar el escritor oficial de TimeNet 0.12.0 con un eje horario UTC y una identidad provisional. | Reabrir con `TimeFReader.verify()` y comparar en Arrow un valor finito, un cero, un nulo y sus horas. Este PR referencia #21; el cierre corresponde al siguiente. |
| **#21 · Convertir una muestra real de SENAMHI** | Sobre el PR sintético, verificar el manifiesto y la traza de #13, seleccionar localmente una muestra reproducible y aplicar las decisiones por señal de #73. Conservar procedencia, unidad inferida y atribución ODC-BY-1.0. | Rechazar un archivo alterado, verificar dos conversiones en carpetas nuevas y leer la misma serie desde el registro local. Comparar identificación, orden, reloj, valores y nulos. Registrar comando, selección y hashes. Cierra #21. [Plan del conector](issue-21-plan.md). |
| **#22 · Exportar las tareas de pronóstico de Lima a TimeF** | Con #19 y #21 integradas, materializar el conjunto base para la cobertura elegida, fijar su versión y escribir `ForecastingTask` con identificadores, cortes y partición de #19. | Cargar por versión con el kit de desarrollo oficial. Conciliar **todas** las tareas exportadas con su manifiesto, reconstruir entradas y objetivos en cada partición y comprobar integridad y repetibilidad. Una muestra acotada debe declarar su selección y cobertura. Entregar a #23 y a Cristopher para #25. |
| **#23 · Reproducir el flujo completo sin red** | Con #22, ejecutar desde una muestra pequeña en un entorno limpio y fijado: adquisición local, normalización, depuración, grilla, ventanas, particiones, TimeF y lectura oficial. Incorporar la prueba a la integración continua. | Ejecutar después de instalar las dependencias con la red deshabilitada. Verificar esquema, procedencia y purga; provocar un fallo con un artefacto alterado. Registrar salida, duración, memoria y versiones. Entregar el recibo a #24 y #27. |
| **#27 · Adaptar OpenTSLM y verificar un paso de ajuste** | Con #23 y las referencias de #25, comprobar interfaz, revisión y licencia del modelo propuesto. Mapear cada tarea TimeF a entrada, máscara y objetivo. Acordar con Keneth presupuesto de descarga, tiempo, memoria y costo antes de la ejecución con pesos. | Probar dimensiones y ausencia de objetivos futuros en entradas; ejecutar un lote real de entrenamiento dentro del presupuesto, registrar pérdida finita y recursos usados. Cierra #27 y deja configuración reproducible para #28. |
| **#28 · Ajustar y evaluar contra las referencias** | Con #27, fijar semilla, revisión, presupuesto y objetivos de #19/#25. Ajustar el modelo en entrenamiento y seleccionar la configuración en validación. | Evaluar la configuración elegida en prueba. Conciliar los identificadores con los de persistencia y referencia diaria. Entregar predicciones locales y una tabla de error absoluto medio y raíz del error cuadrático medio en µg/m³ por estación y hora futura, con denominadores. Registrar tiempo, costo, limitaciones y un caso de error para #29, incluso si gana la referencia. |

### Tareas con evidencia pendiente o posteriores a la primera ronda

| PR propuesto | Qué puede prepararse | Cuándo corresponde cerrar |
| --- | --- | --- |
| **#14 · Resolver identidades y procedencia entre proveedores** | Usar #73 como base. Contrastar una muestra acotada con la fuente original, documentar códigos, instrumento, ubicación y vigencias. Probar copia exacta, copia confirmada de agregador, lectura en conflicto y sensor independiente. Registrar por fila la decisión y sus fuentes. | Cerrar cuando la vista depurada y su tabla de correspondencias justifiquen las uniones y exclusiones con evidencia revisable. Una ficha actual sirve como pista; una mudanza o cambio histórico requiere evidencia fechada. Las muestras de #30/#31 pueden usar la auditoría ya integrada mientras se resuelven correspondencias. |
| **#20 · Integrar etiquetas con ventanas reales de #18** | Reutilizar el módulo ya probado y una configuración con 24 horas futuras medidas. Verificar identidad, periodo, integridad y motivos de exclusión. El pronóstico principal de seis horas sigue por su propia ruta. | Cerrar tras una prueba de integración real y evidencia temporal y de calidad suficiente para el uso declarado. Mantener diferidas las etiquetas de día calendario mientras falte la posición del intervalo. [Plan de etiquetas](issue-20-plan.md). |
| **#43 · Incorporar evidencia institucional al contrato** | El seguimiento al SENAMHI se envió el 17/11. Registrar fuente, fecha y alcance al recibir una aclaración; contrastar por periodo la etiqueta horaria, marcas de calidad, instrumentación y condiciones de unidad de NO2. | Actualizar solo los campos respaldados y, si la interpretación cambia, versionar la política y reproducir el caso afectado. Registrar preguntas todavía abiertas. El envío del correo por sí solo no completa la tarea. |
| **#32 · Evaluar estaciones reservadas en el conjunto nacional** | Después de #19 y de la normalización compatible de #30, generar una partición secundaria por identidad física y por tiempo. Rastrear copias de agregadores y datos usados en preentrenamiento. | Probar con un duplicado conocido el rechazo de contaminación entre entrenamiento y prueba. Verificar ausencia de las estaciones y objetivos reservados en entrenamiento y preentrenamiento. Entregar cobertura geográfica y evaluación reproducible por estación. Si #30 documenta exclusiones sin una cohorte compatible, registrar el bloqueo. |

### Revisión, integración y entrega al equipo

- Crear cada rama desde `main` actualizado con la entrega que consume. Si se apila un PR durante la revisión de su base, declarar la rama base y volver a comprobar el cambio al integrarla. Una tarea activa por persona permite alternar #15 y #21 durante revisiones.
- Escribir primero las pruebas del comportamiento. En cada PR de implementación adjuntar comandos, insumos, versiones y resultados de `make check`, `make build` y `make audit`. Comprobar los controles de Python 3.11 y 3.13.13 en GitHub. Versionar evidencia compacta y dejar artefactos grandes en almacenamiento local.
- Cristopher puede preparar #25 contra el contrato de #22; sus métricas finales requieren la versión exportada. Jordan puede adelantar la ficha de #24 y el guion de #29. Para la entrega final necesita el recorrido de #23, los resultados de #28 y los enlaces autorizados. La contribución externa requiere resolver autoría y permisos según [ADR-003](../docs/decisions/003-licencia-agpl-v3.md).
- Referenciar la tarea en avances parciales. Usar el cierre automático solo en el PR cuya evidencia complete los criterios en GitHub. Los PR de planificación, una prueba sintética o una consulta pendiente se registran como avances.

## Decisiones y búsqueda

Keneth fijó un máximo de **1000 GiB por archivo** para #7. Cada lote requiere presupuesto total explícito;
no es una orden de transferir ese volumen. Verificar espacio local y límites antes de adquisición.
Para incógnitas: documentos oficiales primero, búsqueda adicional, comparación de fuentes/versiones,
registro de evidencia y consulta a Keneth si queda una elección. No reiterar correos SENAMHI sin instrucción.
Las decisiones de unidades, reloj, publicación, particiones reales y cómputo no se suponen resueltas
por cerrar tareas de plataforma. Las licencias AGPL del código y de los datos siguen separadas.

Decisión vigente 17/11/2026: #13 integrada por #71; sin cuota de estaciones/meses, UTC confirmado
por Keneth y ug/m3 inferidos aceptados. Ver docs/sources/senamhi-normalization-handoff.md.
