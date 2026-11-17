# Diagnóstico completo del CSV EAS largo — 17/11/2026

Se procesaron las **11 407 394 filas** del original aportado por Keneth, sin red y sin modificarlo.
SHA-256: 81b219665c12cd1f2e72fa5c93deb6ffd3255fd73465bc02e38b087deda66d6a.
Método y ejecución: [diagnóstico EAS](../docs/methodology/eas-long-diagnostic.md).
Recibo verificable: [metadata/eas-long-diagnostic.json](../metadata/eas-long-diagnostic.json).

## Conteos reconciliados

| Interpretación del valor | Filas |
| --- | ---: |
| Numérico finito | 8 535 307 |
| Marcador ausente | 2 798 558 |
| Código/formato sin resolver | 64 968 |
| Censurado | 8 561 |
| Total | 11 407 394 |

Se inventariaron 333 combinaciones parámetro/unidad/periodo. El reloj pudo construirse para
3 512 243 filas **solo bajo la hipótesis Excel 1900**; 7 895 151 quedaron sin reloj hipotético.
No equivale a que sean errores o no puedan interpretarse con documentación. Se encontraron
476 casillas horarias con más de un valor finito distinto entre los objetivos/periodos/unidades
admitidos. Los conteos no se suman como pérdidas independientes: se refieren a universos diferentes.

## Ventanas diagnósticas

| Ámbito | PM2.5, 24 h → 6 h | PM10, 24 h → 6 h |
| --- | ---: | ---: |
| Todos los contextos admitidos, sin geografía validada | 99 720 | 139 334 |

Son ventanas superpuestas, no ejemplos independientes. Se calcularon las 16 parejas H/F y sus
pérdidas; el resumen local conserva todas las series y conteos. No se agregan a los resultados
anteriores de OEFA ancho, porque puede existir solapamiento de observaciones entre exportaciones.

Dos puntos de interés del informe REAS-002-2024-STEC, que deben homologarse con #14:

| Punto | Horas PM2.5 únicas | Racha máxima (h) | Ventanas 24 h → 6 h |
| --- | ---: | ---: | ---: |
| CA-HU-04 | 6 871 | 357 | 5 582 |
| CA-HU-09 | 4 461 | 354 | 3 457 |

El reloj hipotético sitúa CA-HU-04 en 2023 y CA-HU-09 entre enero y septiembre 2023.
Los nombres/evaluaciones mencionan Huachipa/Nievería, pero no se asigna automáticamente provincia
ni equivalencia de estación. La prueba textual literal Lima no identificó contextos PM horarios
admitidos: eso **no prueba ausencia de datos de Lima**. Las descripciones pueden variar entre
registros, años o parámetros. Revisar geografía y contexto con coordenadas/datum/informe antes de
aplicar filtros científicos. La mayor racha de cualquier contexto admitido fue 1 668 horas en
CA-CHA-01 (PM10 y PM2.5), fuera de los puntos anteriores y sin afirmar pertenencia a Lima.

## Decisión vigente

No se demuestra una cohorte fija de cuatro estaciones de Lima durante 24 meses continuos.
scientific_valid_windows sigue nulo: faltan época y convención temporal documentadas, calidad,
identidad/geografía y revisión de derechos. Los XLSX usan época Excel, pero eso no certifica la
del CSV EAS independiente. Se excluyeron conservadoramente los intervalos con fin declarado del
conteo horario; no se interpretaron ni corrigieron automáticamente. No se modificó benchmark.yaml,
no se imputaron faltantes, ni se creó un conjunto de entrenamiento o etiquetas reales de #20.

Siguiente trabajo permitido: revisar documentación/informes y evidencia, integrar el contrato #12
en adaptadores #13/#30 y resolver identidades #14. Si sigue sin alcanzarse la meta tras confirmar
los metadatos, consultar a Keneth antes de proponer un benchmark menor o de eventos.

Validación: seis pruebas del diagnóstico, doce del contrato común y 29 de etiquetas aprobadas
en Python 3.11; controles completos del repositorio, build y auditoría. La prueba inicial de
ventanas no detectaba por sí sola la admisión de un conflicto porque otra hora censurada ya
rompía la racha; se agregó comprobación directa de ausencia del punto conflictivo. La mutación
posterior fue detectada y restaurada. Los resultados reales corresponden al código sin mutación.
