# Plan de implementación de AirAware Perú

Fuente: [plan inicial completo](../docs/initial-plan.md), adaptado al español del Perú.
El estado vigente está en las [tareas de GitHub](https://github.com/keneth-arias/airaware/issues) y el
[tablero](https://github.com/users/keneth-arias/projects/1). Este documento es un índice ordenado;
distingue evidencia documental, descargas y resultados de modelos.

## Decisiones de ejecución

- Mantener el nombre airaware. Empezar por PM2.5 medido en Lima/Callao y ampliar con evidencia.
- Verificar las API y fijar revisiones antes de implementar; separar AirAware del conector externo mínimo.
- Priorizar M0–M3, la primera entrega TimeF de M5 y las referencias/modelo temporal de M8.
  M4 depende de meteorología verificada. El primer flujo completo puede usar solo contaminación.
- Licencias incompatibles y significado de medición desconocido son motivos de exclusión.
  Cuatro estaciones, 24 meses, frecuencia horaria y ventanas 72/24 son metas provisionales.
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

## #20: metodología y etiquetas (16/11/2026)

Plan detallado en [issue-20-plan.md](issue-20-plan.md): verificar normas oficiales, separar ventana
futura completa de día calendario, implementar módulo puro con pruebas y mantener explícita la
integración pendiente con #18. No normalizar ni etiquetar todavía datos SENAMHI de semántica incierta.

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
