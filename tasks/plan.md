# Plan de implementación de AirAware Perú

Fuente: [plan inicial completo](../docs/initial-plan.md), adaptado al español del Perú.
El estado vigente está en las [tareas de GitHub](https://github.com/keneth-arias/airaware/issues) y el
[tablero](https://github.com/users/keneth-arias/projects/1). Este documento es un índice ordenado;
distingue evidencia documental, descargas y resultados de modelos.

## Ruta vigente para la primera ronda (18/11/2026)

La [matriz del jurado](../docs/hackathon.md) registra el conjunto y el enlace del aporte.
#15, #18, #19 y #21–#25 están cerradas. La [cola vigente de Keneth](keneth-work-queue.md)
prioriza #27 y #28. La entrega de #29 reúne la ficha, la contribución de TimeNet,
los resultados temporales y las evidencias de difusión previstas en la guía.

**Fechas internas propuestas (hora del Perú).** Priorizar la prueba acotada del modelo
y el reporte medido. El 22 de noviembre, comprobar que un revisor pueda abrir la demo
y los enlaces exigidos. La fecha oficial se registra en la guía del hackathon.

| Tarea | Frente | Evidencia o condición para retomarla |
| --- | --- | --- |
| [#11](https://github.com/keneth-arias/airaware/issues/11) | Decisión aprobada | Para un analista ambiental de Lima, formular la pregunta retrospectiva: con 24 horas de PM2.5, ¿cuánto mejora el pronóstico de las seis horas siguientes frente a repetir la última medición? ADR-005 admite 339 205 ventanas solapadas en siete identidades provisionales antes de las particiones. Citar comparison-v3 y distinguir cobertura, desempeño medido y utilidad por validar. |
| [#14](https://github.com/keneth-arias/airaware/issues/14) | Datos | Entregar una tabla auditable por señal con identidad provisional, fila de origen, duplicado exacto o conflicto y decisión. Seguir un caso desde el archivo original hasta la vista depurada y conciliar los conteos. |
| [#15](https://github.com/keneth-arias/airaware/issues/15) | Datos | Mostrar una serie horaria en tiempo universal coordinado (UTC) con un cero observado, un valor nulo y una hora ausente. Verificar sus máscaras y conciliar horas utilizables y descartadas por estación. |
| [#16](https://github.com/keneth-arias/airaware/issues/16) | Ampliación | Muestra fijada y verificada con #79. Se conservan las limitaciones de disponibilidad y derechos por producto. |
| [#17](https://github.com/keneth-arias/airaware/issues/17) | Ampliación | El PR #85 integró la paridad de objetivos, el rechazo de emisiones tardías y las máscaras en pruebas. Queda por verificar la unión real y la disponibilidad horaria. |
| [#18](https://github.com/keneth-arias/airaware/issues/18) | Datos | Preparar primero historias completas de 24 h y objetivos completos de 6 h según ADR-005. Conciliar ventanas antes de particionar con comparison-v3 y explicar diferencias por identidad, conflicto, hueco o paso. Los demás horizontes quedan identificados por configuración. |
| [#19](https://github.com/keneth-arias/airaware/issues/19) | Evaluación | Congelar fechas de corte en UTC y un manifiesto de identificadores antes de seleccionar modelos. Documentar ventanas purgadas y demostrar con una prueba de frontera que ninguna hora de entrada u objetivo se comparte entre particiones para una serie. |
| [#20](https://github.com/keneth-arias/airaware/issues/20) | Condicional | Integración estructural verificada con 324 463 ventanas 24/24 reales. Mantener abierta hasta acreditar la posición del intervalo y la calidad individual; solo entonces emitir etiquetas. Diferir etiquetas regulatorias diarias y métricas de episodios sin respaldo. |
| [#21](https://github.com/keneth-arias/airaware/issues/21) | TimeNet | Con #13 integrado, verificar el manifiesto Parquet antes de convertir una muestra local. Reabrirla con TimeFReader.verify() y Arrow; comprobar eje UTC, identidad, cero, nulo, procedencia, unidad inferida y atribución. Comparar dos conversiones por contenido lógico. |
| [#22](https://github.com/keneth-arias/airaware/issues/22) | TimeNet | Con #19 y #21, abrir una ForecastingTask con el lector oficial y reconstruir sus 24 entradas y 6 objetivos. Comparar identificadores, límites y conteos de cada partición con el manifiesto congelado; registrar la versión del conjunto base. |
| [#23](https://github.com/keneth-arias/airaware/issues/23) | Ejecución técnica | Desde un entorno fijado, reproducir sin red el recorrido de una muestra hasta una tarea leída por el kit de desarrollo de TimeNet. Guardar comando, revisión, hashes, tiempo, memoria y resultado de controles; comprobar que un archivo alterado falla. |
| [#24](https://github.com/keneth-arias/airaware/issues/24) | Contribución | Ficha integrada en #83 y contribución autorizada en el borrador externo TimeNet #796. Código MIT y datos ODC-By-1.0 con atribución. |
| [#25](https://github.com/keneth-arias/airaware/issues/25) | Evaluación | Comparar persistencia y referencia diaria sobre idénticos identificadores. Registrar error absoluto medio (MAE), raíz del error cuadrático medio (RMSE), número de objetivos y unidad por estación y hora futura. Fijar en validación la referencia principal antes de evaluar la prueba. |
| [#26](https://github.com/keneth-arias/airaware/issues/26) | Condicional | Comparar el modelo tabular en las mismas ventanas de #25. Evaluar episodios únicamente si #20 sustenta la etiqueta; informar positivos, negativos y métricas indefinidas. Priorizar #27–#28 para la primera ronda. |
| [#27](https://github.com/keneth-arias/airaware/issues/27) | Modelo temporal | Fijar revisión, licencia y presupuesto del modelo. Leer un lote desde #22, verificar dimensiones y objetivos y demostrar un paso de ajuste con pérdida finita dentro del presupuesto aprobado. Registrar memoria, duración y comando. |
| [#28](https://github.com/keneth-arias/airaware/issues/28) | Resultados | Entrenar o ajustar el modelo temporal y elegir configuración en validación. Guardar semilla, revisión, costo y predicciones de prueba enlazadas a #19. Comparar con #25 por estación y horizonte; mostrar la diferencia en MAE, un caso de error y el efecto del solapamiento al interpretar la incertidumbre. |
| [#29](https://github.com/keneth-arias/airaware/issues/29) | Presentación | Preparar una demo que abra TimeF, muestre 24 h de historia y superponga seis predicciones, referencia y observaciones reservadas. Explicar un acierto y un error, límites y aportes durante el reto. Preparar textos para X, LinkedIn y Discord; con autorización, compartir avances temprano, guardar enlaces y capturas fechadas de métricas disponibles y verificar el recibo del formulario del equipo. |
| [#30](https://github.com/keneth-arias/airaware/issues/30) | Ampliación | Retomar la extensión nacional con una matriz de compatibilidad por serie de OEFA, derechos y cobertura. Registrar exclusiones antes de mezclar fuentes o afirmar generalización fuera de Lima. |
| [#31](https://github.com/keneth-arias/airaware/issues/31) | Ampliación | Para una muestra peruana acotada, rastrear cada serie de OpenAQ al proveedor y cuantificar copias de observaciones ya incluidas; documentar elegibilidad y atribución. |
| [#32](https://github.com/keneth-arias/airaware/issues/32) | Ampliación | Con #19 y #30, identificar estaciones reservadas y auditar su ausencia del entrenamiento y preentrenamiento. Informar cobertura y error por estación en una evaluación secundaria separada. |
| [#33](https://github.com/keneth-arias/airaware/issues/33) | Ampliación | Elegir un producto atmosférico con licencia, máscara y disponibilidad temporal verificadas. Medir su aporte en objetivos compartidos con #25 y registrar el cambio de cobertura. |
| [#34](https://github.com/keneth-arias/airaware/issues/34) | Ampliación | Elegir una variable de contexto con fechas históricas de disponibilidad demostrables. Comparar con y sin ella sobre los mismos casos y documentar costo e incertidumbre. |
| [#35](https://github.com/keneth-arias/airaware/issues/35) | Ampliación | Generar preguntas con respuesta calculable desde una serie TimeF trazable y comprobar las respuestas automáticamente. Mantener separados los casos de prueba del pronóstico y los ejemplos para demostración. |
| [#43](https://github.com/keneth-arias/airaware/issues/43) | Seguimiento | Registrar evidencia institucional fechada si llega y enumerar los campos o decisiones que cambia. Mantener visibles calidad individual, posición del intervalo y disponibilidad desconocidas; un nuevo contacto requiere autorización de Keneth. |

## Decisiones de ejecución

- Mantener el nombre airaware. Empezar por PM2.5 medido en Lima/Callao y ampliar con evidencia.
- Verificar las API y fijar revisiones antes de implementar; separar AirAware del conector externo mínimo.
- Priorizar M0–M3, la primera entrega TimeF de M5 y las referencias/modelo temporal de M8.
  M4 depende de meteorología verificada. El primer flujo completo puede usar solo contaminación.
- Licencias incompatibles y significado de medición desconocido son motivos de exclusión.
  No hay cuota fija de estaciones ni meses continuos; se mide cobertura real sin imputación.
  La frecuencia es horaria y las historias/horizontes se evalúan por separado.
- Esta preparación no autoriza publicar datos masivos, abrir PR externos ni ejecutar descargas o
  entrenamientos costosos o sin límites. Se mantienen las autorizaciones expresas del plan.
- Usar Lightpanda para páginas y descargas web, según [el protocolo](../docs/web-access.md).
- Empezar con Python/uv y dependencias mínimas. Incorporar Polars, DuckDB, HTTPX, herramientas
  geoespaciales o de ráster cuando se utilicen. No usar infraestructura distribuida sin necesidad medida.

## Orden y dependencias

M0: investigar API y fuentes → M1: adquisición reproducible → M2: comparación medida → M3:
normalización común → M5: ventanas y particiones sin fugas, exportación y lectura TimeF → M8:
referencias, adaptador, experimento temporal y entrega.
M3 y fuentes meteorológicas verificadas habilitan M4. M6 nacional y M7 complementario vienen después.

## Índice de tareas
- [#1: Verificar las API de TimeNet y los requisitos del hackathon](https://github.com/keneth-arias/airaware/issues/1)
- [#2: Preparar las herramientas de Python y la integración continua sin servicios externos](https://github.com/keneth-arias/airaware/issues/2)
- [#3: Construir y validar el inventario de fuentes ambientales](https://github.com/keneth-arias/airaware/issues/3)
- [#4: Verificar los recursos de SENAMHI y los derechos de redistribución](https://github.com/keneth-arias/airaware/issues/4)
- [#5: Verificar los recursos de OEFA y sus coordenadas](https://github.com/keneth-arias/airaware/issues/5)
- [#6: Implementar descargas atómicas con trazabilidad](https://github.com/keneth-arias/airaware/issues/6)
- [#7: Agregar reanudación y límites a la descarga](https://github.com/keneth-arias/airaware/issues/7)
- [#8: Recolectar una muestra reproducible de SENAMHI Lima](https://github.com/keneth-arias/airaware/issues/8)
- [#9: Recolectar datos acotados de OEFA y su documentación](https://github.com/keneth-arias/airaware/issues/9)
- [#10: Analizar la cobertura de estaciones y la calidad de las señales](https://github.com/keneth-arias/airaware/issues/10)
- [#11: Comparar fuentes y seleccionar el primer conjunto de evaluación de Lima](https://github.com/keneth-arias/airaware/issues/11)
- [#12: Definir el esquema común de observaciones y estaciones](https://github.com/keneth-arias/airaware/issues/12)
- [#13: Normalizar SENAMHI a Parquet validado y particionado](https://github.com/keneth-arias/airaware/issues/13)
- [#14: Resolver identidades de estaciones y duplicados entre fuentes](https://github.com/keneth-arias/airaware/issues/14)
- [#15: Construir líneas temporales de contaminación y máscaras de datos faltantes](https://github.com/keneth-arias/airaware/issues/15)
- [#16: Verificar fuentes meteorológicas y recolectar una muestra por estación](https://github.com/keneth-arias/airaware/issues/16)
- [#17: Alinear meteorología y contaminación sin información futura](https://github.com/keneth-arias/airaware/issues/17)
- [#18: Construir ventanas de pronóstico de PM2.5 con objetivos completos](https://github.com/keneth-arias/airaware/issues/18)
- [#19: Fijar particiones cronológicas y comprobar fugas de información](https://github.com/keneth-arias/airaware/issues/19)
- [#20: Validar la metodología para etiquetar episodios de contaminación](https://github.com/keneth-arias/airaware/issues/20)
- [#21: Implementar el conector base de SENAMHI para TimeNet](https://github.com/keneth-arias/airaware/issues/21)
- [#22: Exportar el conjunto de evaluación de Lima a TimeF sin fugas](https://github.com/keneth-arias/airaware/issues/22)
- [#23: Verificar la entrega del conjunto de datos de extremo a extremo sin servicios externos](https://github.com/keneth-arias/airaware/issues/23)
- [#24: Documentar la metodología y preparar la contribución a TimeNet](https://github.com/keneth-arias/airaware/issues/24)
- [#25: Evaluar modelos de referencia de persistencia y estacionalidad](https://github.com/keneth-arias/airaware/issues/25)
- [#26: Evaluar un modelo tabular y métricas de episodios](https://github.com/keneth-arias/airaware/issues/26)
- [#27: Implementar el adaptador de OpenTSLM y una prueba acotada de modelo](https://github.com/keneth-arias/airaware/issues/27)
- [#28: Entrenar y evaluar el experimento temporal del hackathon](https://github.com/keneth-arias/airaware/issues/28)
- [#29: Preparar la presentación y la entrega del hackathon](https://github.com/keneth-arias/airaware/issues/29)
- [#30: Normalizar OEFA y validar la compatibilidad de mediciones nacionales](https://github.com/keneth-arias/airaware/issues/30)
- [#31: Investigar OpenAQ Perú y duplicaciones de agregadores](https://github.com/keneth-arias/airaware/issues/31)
- [#32: Evaluar estaciones separadas y particiones seguras para preentrenamiento nacional](https://github.com/keneth-arias/airaware/issues/32)
- [#33: Probar información atmosférica y satelital complementaria](https://github.com/keneth-arias/airaware/issues/33)
- [#34: Evaluar incendios, movilidad y otras variables de contexto opcionales](https://github.com/keneth-arias/airaware/issues/34)
- [#35: Generar preguntas temporales con respuestas verificables como ampliación](https://github.com/keneth-arias/airaware/issues/35)

## Puntos de control

- Tras API/herramientas/catálogo: controles sin servicios externos aprobados; fechas y bloqueos registrados.
- Tras consultas iniciales y descargador: probar formatos y fallas antes de descargar datos reales.
- Tras adquisición/análisis/selección: inspeccionar archivos, derechos, métricas y ventanas; registrar
  la elección en una decisión de arquitectura (ADR).
- Tras esquemas/normalización/duplicados: revisar procedencia, frecuencia, unidades, estaciones y máscaras.
- Tras ventanas/particiones/TimeF: probar fugas y lectura estándar; fijar insumos y manifiestos de evaluación.
- Antes de entrenar/presentar: aprobar datos, acotar cómputo, comparar objetivos idénticos y explicar límites.

## Riesgos y decisiones pendientes

Enlaces, tamaños, derechos y cobertura son candidatos hasta verificarse. Una falla debe quedar como
bloqueo, no como progreso inventado. Definir estaciones, fechas, método regulatorio, licencias de los datos, nombres externos,
alojamiento de archivos y presupuesto de cómputo con evidencia. El código propio usa AGPL-3.0-only
por decisión de Keneth; ADR-003 define la separación respecto de contribuciones externas MIT.
Los comandos del plan inicial son propuestas, no API implementadas.

## Preparación y distribución del equipo

Keneth lidera datos y plataforma. La decisión inicial es almacenamiento local y GitHub Actions (ADR-001).
El PR #36 ya está integrado en main y cerró #2. Preparó la evidencia inicial de #1/#3,
las herramientas, el catálogo, los comandos, CI y las guías.
El inventario #3 ya tiene evidencia de acceso para los 37 candidatos. Continúan #4/#5 y el descargador #6/#7.

Se reservaron 18 de las 35 tareas: 16 para qriqs y dos para J0r-PS, mediante etiquetas y notas de
entrega mientras sus invitaciones están pendientes. Keneth conserva 17 tareas. Mantener una tarea
activa por persona y las dependencias originales. Consulta la [distribución](../docs/team-work-allocation.md),
la [guía de inicio](../docs/team-onboarding.md) y los [servicios](../docs/services.md).
El idioma vigente es español del Perú (ADR-002), incluidos tareas, documentación y PR.

## Antecedente completado: tarea #1

El [plan y resultado de #1](issue-1-plan.md) documenta cuatro pasos ejecutados:
confirmar revisión, completar matriz de API, revisar ejemplos y vincular requisitos del hackathon.
Responsable: Keneth. La investigación quedó integrada en #40 y #1 está cerrada. La prueba TimeF sintética ya se ejecutó.
Cristopher ya tiene asignadas sus 16 tareas de forma nativa; Jordan conserva sus dos reservas
mientras acepta la invitación. Estos avances no modifican las dependencias.

## Antecedente completado: inventario con SENAMHI

#40 está integrado y #1 cerrada. La prueba sintética hello-world ya se ejecutó, con datos en data/timef
y entorno aislado en tools/timenet-smoke. Continúa [el plan de #3](issue-3-plan.md), empezando por
SENAMHI en coordinación con #4; OEFA #5 sigue con Cristopher. El primer acceso web al catálogo
SENAMHI devolvió 403 con otra herramienta. Lightpanda permitió descargar el CSV y revisar los 37 enlaces;
la [evidencia](../docs/sources/inventory-review.md) distingue metadatos, estructura y pendientes de derechos.

## Investigación completada de #4: SENAMHI

#3 quedó integrada en #41. El [plan de #4](issue-4-plan.md) ordena la preservación de documentos,
el contraste de derechos, la matriz de significado de campos y la entrega de evidencia.
La lista de trabajo se mantiene en GitHub #4. Keneth aprobó la ejecución y pidió búsqueda profunda
ante vacíos. La investigación quedó ejecutada con documentos originales, contraste adicional y consulta
revisada y enviada con autorización de Keneth; el informe de #4 distingue resultados de preguntas pendientes.

## Siguiente paso de Keneth: #6, adquisición atómica

#42 está integrado y #4 quedó cerrada. La consulta SENAMHI se envió con autorización de Keneth;
las aclaraciones pendientes pasan a [#43](https://github.com/keneth-arias/airaware/issues/43).
Este cierre no confirma unidades, zona horaria ni publicación. No se esperará la respuesta para
implementar herramientas que solo preservan bytes y procedencia.

El [plan de #6](issue-6-plan.md) propone cuatro entregas: contrato y pruebas; validación/publicación
atómica; transporte API acotado con HTTP simulado; CLI y guía para el equipo. La implementación
quedó ejecutada con pruebas y demostración local sin nuevas descargas. #7 continúa con reanudación y capacidades adicionales. #5 sigue con Cristopher;
no se cambia la asignación de Jordan ni las ramas de sus copias locales.

## Entrega de #6

La [guía de adquisición](../docs/acquisition.md) documenta acquire import-file y acquire api,
almacenamiento atómico y referencias a originales existentes. #44 entrega #6 con HTTP simulado,
pruebas sin internet y verificación local SENAMHI. Las fuentes no cambian a integrated por registrar
sus bytes. El siguiente trabajo de plataforma es #7; las aclaraciones SENAMHI permanecen en #43.

## Trabajo autorizado de Keneth

La [cola de trabajo](keneth-work-queue.md) ordena las 13 tareas abiertas asignadas y sus dependencias.
Comienza [#7](issue-7-plan.md), con límite por archivo de 1000 GiB indicado por Keneth, presupuestos
explícitos por lote y pruebas sin descargas masivas. Los siguientes pasos científicos requieren las
entregas de Cristopher y las aclaraciones de #43; no se declaran completados por anticipación.

## #20: metodología y etiquetas (16/11/2026; integración 18/11/2026)

Plan detallado en [issue-20-plan.md](issue-20-plan.md): normas oficiales verificadas, ventana
futura completa separada del día calendario y módulo puro con pruebas. La integración estructural
con #18 se verificó el 18/11/2026 sobre 324 463 ventanas 24/24 reales, con conteos, límites,
estación y promedios reconstruidos. No se etiquetaron datos SENAMHI: la posición del intervalo y
la calidad individual siguen sin evidencia (`labeling_evidence_missing`). Detalle en
[metadata/issue-20-label-integration.json](../metadata/issue-20-label-integration.json).

## Planes #8 y #9 para feedback de Keneth

Planes revisados, sin comenzar implementación ni nuevas adquisiciones:
[reutilización SENAMHI #8](issue-8-plan.md) y [OEFA #9](issue-9-plan.md).
Orden: #8 y #9 → #10 → #11. Responsable vigente: Keneth para las cuatro tareas.
#8 propone cero descarga y evidencia de reutilización local. #9 propone CSV completo con 2 GiB
por ejecución, pero requiere aprobar alcance/presupuesto y primero resolver dialecto CSV y canal
público estático en el motor. La lista de ejecución y los bloqueos se mantienen en issues #8/#9.
Esperar respuesta de Keneth antes de cambiar código o transferir datos. El techo de 1000 GiB por
archivo no autoriza por sí solo una transferencia de ese tamaño ni elimina presupuestos por lote.

Verificación de esta propuesta documental: make check aprobado (146 pruebas sobre main con PR #45),
make build aprobado y make audit sin vulnerabilidades conocidas. No se cambió código ni se ejecutó
acquire/import-file/batch para #8/#9 durante la planificación. No se hicieron consultas o descargas
nuevas a los proveedores. PR #50 de etiquetas sigue siendo una entrega separada, no incluida aquí.

## Ejecución aprobada de #8/#9

Keneth aprobó ambos planes. #8 se ejecutó sin descargas y se integró en PR #52. Los prerrequisitos
OEFA de dialecto y canal explícito se integraron en #53/#54. reports/acquisition/oefa.md y
metadata/oefa-acquisition-check.json registran documentación verificada y CSV bloqueado por HTTP 418.
Estado histórico del primer intento. Posteriormente Keneth pidió la descarga completa con Lightpanda:
PR #56 integró la evidencia del CSV completo y cerró #9; el 418 ya no bloquea el perfilamiento.

## #10: perfilamiento de originales locales completos

Plan adaptado en [issue-10-plan.md](issue-10-plan.md). #8/#9 cerradas y archivos completos disponibles.
Implementación autorizada por Keneth: perfiles por fuente/estación/serie y señales con Parquet local,
pruebas sintéticas y ejecución real posterior, sin normalizar incertidumbres ni escoger el benchmark.

La implementación y ejecución real de #10 están en revisión: [metodología](../docs/profiling.md),
[configuración](../configs/profiling.json) y [resultados](../reports/profiling.md). Las salidas Parquet
permanecen locales. La selección de #11 conserva las incertidumbres de reloj/unidades.

## Plan #11 adaptado después del perfilamiento

#10 cerrada con PR #57/#58 integrados. La propuesta de [issue-11-plan.md](issue-11-plan.md)
separa conteos estructurales de elegibilidad científica, geografía Lima/Callao y escenarios nacionales.
Plan aprobado e implementado. Consulta OEFA enviada desde Outlook el 16/11/2026, 23:52:57 UTC.
[Comparación real](../reports/dataset-comparison.md) y [método](../docs/comparison.md) entregan
conteos estructurales con bloqueos; la selección científica de #11 permanece pendiente.

## Revisión de libros IPASH/EAC/EAF/EAT

Por solicitud de Keneth se analizaron completos los cuatro libros descargados en PR #64.
[Plan y alcance](oefa-workbook-analysis.md), [resultados](../reports/oefa-workbook-analysis.md)
y [herramienta reproducible](../tools/oefa-workbook-review/README.md). La revisión conserva originales,
separa productos/campañas, censura y categorías, y no habilita selección científica de #11.
## Siguientes pasos revisados tras los libros OEFA (17/11/2026)

Propuesta para revisión de Keneth; no iniciar normalización ni cambiar el objetivo por estos conteos.

1. **Keneth — #12: contrato común antes de transformar.** Preparar un esquema independiente de fuente con valor original, valor numérico opcional, censura/código, unidad original y verificada, intervalo/reloj y estado de evidencia, calidad, fuente/hash/fila y contexto de campaña. No imponer datos desconocidos. Aceptación: fixtures de SENAMHI, EAS largo, EAF horario y EAT diario conservan el original; registros ambiguos quedan explícitamente sin resolver. Una PR pequeña de contrato/documentación y otra de validación; 3–5 archivos por entrega. La adopción científica sigue dependiendo de #11.
2. **Keneth — #11: diagnóstico EAS largo, separado del parser ancho.** Contrastar seriales de fecha contra registros/informes verificables; no inferir la época del CSV a partir de XLSX distintos. Definir etiquetas PM inequívocas, unidades, horas y contextos. Ejecutar luego las 16 parejas H/F sobre las 11 407 394 filas locales con conteos reconciliados, conflictos, ventanas y continuidad por estación; mantener nulo lo científicamente no confirmado. Dos entregas: parser con fixtures y ejecución/informe con hashes, sin red ni cambios de originales. Criterio: conocer si CA-HU-04/09 aportan continuidad real a Lima, sin concatenar campañas ni duplicar fuentes.
3. **Keneth — #43/#11: cerrar evidencias de reloj, calidad y derechos.** Incorporar respuestas institucionales ya solicitadas; preparar una lista concreta de dudas con filas/informes para OEFA. Sin reenviar correos automáticamente. Afinar por señal el bloqueo de unidades del CSV ancho conforme al diccionario; no habilitar otras dimensiones por inferencia. Criterio: matriz fuente/señal/contexto con evidencia y bloqueos, luego nueva comparación reproducible.
4. **Cristopher — #13/#30/#14: entregas coordinadas.** Tras estabilizar #12, priorizar normalización SENAMHI y su trazabilidad; OEFA nacional permanece separado y requiere identidad/compatibilidad. EAF solo se propone como piloto de eventos (204 h máximas en candidatos Lima), no sustituto del benchmark. No cambiar asignaciones ni iniciar ramas ajenas. Jordan puede revisar instrucciones y reproducibilidad de fixtures, sin quedar en la ruta crítica ni reasignar tareas existentes.
5. **Punto de decisión — #11.** Mantener PM2.5 y Lima, sin cuota fija de estaciones ni meses continuos (decisión de Keneth del 17/11/2026). Elegir periodos por cobertura real y registrar faltantes. Con selección justificada: #15/#18 → #19 → integración #20 → #21/#22/#23. #20 permanece abierto hasta verificar ventanas reales de #18.

Verificación en cada entrega ejecutable: pruebas sin red, make check/build/audit, SHA antes/después y conciliación de pérdidas. Metadatos desconocidos quedan nulos con motivo; no imputar, convertir censura en cero ni publicar observaciones masivas. El rastreador de tareas es GitHub Issues; esta propuesta amplía #11/#12 y conserva los criterios existentes.

## Implementación aprobada de los siguientes pasos (17/11/2026)

[Contrato común y diagnóstico EAS](data-foundation-next.md): ejecución autorizada por Keneth,
con trazabilidad en #12/#11, pruebas por incremento y decisiones científicas pendientes explícitas.

## SENAMHI: exploración reproducible adaptada de dos referencias

[Plan acotado](senamhi-exploratory-plan.md), solicitado por Keneth: grillas y resúmenes trazables
sin imputación, evidencia fijada de Cristhianbgf/DataGabo y escenarios de reloj separados.
No sustituye #13 ni declara elegibilidad de #11.


## Decisión vigente para desbloquear #13 (17/11/2026)

Keneth retiró la cuota fija de estaciones/meses, confirmó UTC para toda la exportación y aceptó
las unidades inferidas. ODC-BY-1.0 documentada; atribución en DATA_ATTRIBUTION.md.
Guía operativa: [entrega a qriqs](../docs/sources/senamhi-normalization-handoff.md).
Política tipada y helpers listos, sin modificar su copia ni completar su normalizador.
#43 conserva solo dudas de intervalo/calidad y no bloquea normalización.


## #11: selección operativa aprobada por Keneth

[ADR-005](../docs/decisions/005-senamhi-operating-policy.md): SENAMHI/Lima/PM2.5 con etiquetas
UTC publicadas; aceptación explícita de calidad y posición del intervalo desconocidas. Se difieren
etiquetas regulatorias diarias. comparison-v3 distingue ventanas aceptadas operativamente de
validación científica. #13/#14/#18/#19 continúan como entregas propias; #20/#43 no se cierran.

## Adaptación después de #79

#16 cerró con la [adquisición meteorológica verificable](../reports/acquisition/weather.md).
El [PR #85](https://github.com/keneth-arias/airaware/pull/85) integró la alineación de GFS
`previous_day1` por `window_id`. La unión real queda como comprobación local
cuando estén disponibles los siete paquetes y los artefactos congelados.

Se cruzó el intervalo publicado del 09/03/2022 a las 00:00 UTC al 16/03/2022 a
las 00:00 UTC (extremo superior exclusivo) con la historia y seis objetivos de
cada ventana de #19. En entrenamiento, 1232 ventanas tocan esa semana y 973 quedan
completamente contenidas. Validación y prueba tienen cero ventanas con solapamiento.
Los conteos expresan cobertura por calendario y preceden a la validación del clima
por estación, emisión y disponibilidad. La muestra permite probar la unión y las
máscaras en entrenamiento. Una evaluación meteorológica requiere cobertura
verificada en validación y prueba y una comparación sobre objetivos comunes.

El [PR #86](https://github.com/keneth-arias/airaware/pull/86) integró la verificación del contrato
estructural de etiquetas para un horizonte de 24 horas. La emisión sigue condicionada
por la evidencia temporal y de calidad de #20 y #43. El benchmark principal usa el
horizonte de seis horas y conserva su [ficha](../docs/dataset-cards/lima-pm25-forecast.md).

## Entrenamiento con Qwen3.5 en dos GPU

El [plan de la bifurcación de OpenTSLM y del experimento con entradas comparables](issue-27-qwen-plan.md)
ordena las entregas de #27, #28 y la extensión opcional #88. Incluye un control de pronóstico
con las mismas entradas y una medición independiente del costo de distribuir el entrenamiento.

En #28, comparar primero los cabezales directo y de corrección de persistencia. Medir después LoRA híbrida y los núcleos recurrentes con controles independientes. En #88, comprobar que el escalado y la reconstrucción de PM10 respeten la máscara de cada brazo.

El [plan operativo de MicroK8s y SkyPilot para #28](issue-28-cluster.md) fija el orden de preparación de insumos, uso de ambas RTX 5070 Ti, ensayo de reanudación y dimensionamiento del volumen antes del entrenamiento.

Con el piloto y la imagen por digest verificados, el [plan de evaluación de #28](issue-28-evaluacion.md) ordena los cinco PR restantes. La exportación de entrenamiento y validación puede avanzar junto con la inferencia desde un punto de control. La medición de dos ajustes simultáneos decide el uso de las tarjetas. La selección en validación habilita la prueba reservada y la presentación de #29. La extensión con PM10 queda en #88.
