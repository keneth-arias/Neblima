# Pronóstico horario de PM2.5 en Lima

`airaware/lima-pm25-forecast@0.1.0` permite evaluar retrospectivamente el pronóstico de
seis horas de partículas finas (PM2.5) a partir de 24 horas consecutivas de la misma
serie. Cada tarea presenta únicamente su historia y separa los seis objetivos ordenados.
Las etiquetas horarias se conservan en tiempo universal coordinado (UTC).

## Fuente, cobertura y calidad

El Servicio Nacional de Meteorología e Hidrología del Perú (SENAMHI) publica la base
*Monitoreo de los contaminantes del aire en Lima Metropolitana* bajo la licencia de
[atribución de Open Data Commons 1.0](https://opendatacommons.org/licenses/by/1-0/).
La [atribución del original](../../DATA_ATTRIBUTION.md) acompaña las versiones locales.
La ficha de TimeNet usa `ODC-By-1.0`, el identificador admitido por la revisión fijada.
El SHA-256 del original seleccionado es
`896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4`.

El primer valor de PM2.5 admitido corresponde al 01/01/2015 a las 05:00 UTC y el último
al 31/05/2024 a las 23:00 UTC. La grilla tiene 577 717 horas entre las siete series.
Se conservaron 367 518 horas con valor. Hay 210 172 horas con filas sin valor utilizable,
20 horas con lecturas en conflicto y siete horas sin fila. Los estados, valores y
vínculos a filas quedan en la [auditoría y grilla](../../tasks/issue-15-plan.md).

El conjunto está limitado a estaciones y periodos monitoreados en Lima. Las identidades
siguen siendo provisionales y la cobertura y la pérdida de ventanas varían por estación.
La unidad µg/m³ es una inferencia aceptada conforme al
[ADR-005](../decisions/005-senamhi-operating-policy.md). La posición del intervalo, la
validación de cada lectura y el retraso de publicación son desconocidos. El alcance es
pronóstico retrospectivo con las horas publicadas. Una interpretación regulatoria diaria
requiere evidencia temporal y de calidad adicional.

## Particiones y cobertura

Los cortes UTC corresponden al 16/03/2022 a las 08:00 y al 25/02/2023 a las 18:00.
La hora exacta del corte pertenece al bloque que empieza. Se purgan ventanas
que comparten el intervalo de historia y objetivo con más de un bloque.

| Identidad provisional | Entrenamiento | Validación | Prueba | Purga |
| --- | ---: | ---: | ---: | ---: |
| Campo de Marte | 42 988 | 5 342 | 4 891 | 29 |
| Carabayllo | 27 189 | 7 452 | 8 258 | 58 |
| Santa Anita | 30 219 | 7 223 | 9 988 | 58 |
| San Borja | 34 643 | 7 461 | 8 061 | 58 |
| San Juan de Lurigancho | 47 058 | 7 715 | 4 999 | 29 |
| San Martín de Porres | 27 956 | 7 783 | 6 311 | 52 |
| Villa María del Triunfo | 27 344 | 7 730 | 8 281 | 29 |
| **Total** | **237 397** | **50 706** | **50 789** | **313** |

Las ventanas cercanas de una misma partición se solapan. Los conteos reflejan ventanas,
no muestras independientes. Fijar cualquier ajuste de datos con entrenamiento, seleccionar
modelos con validación y reservar prueba para el informe final. El manifiesto de
[particiones](../../tasks/issue-19-plan.md) registra fechas, cantidades y hashes.

## Reproducir

1. Obtener la copia identificada por la suma del original y registrar sus bytes con la
   [adquisición local](../acquisition.md).
2. Normalizar con la [política y el flujo de #13](../../reports/senamhi-normalization.md),
   depurar con [#14](../../tasks/issue-14-plan.md), alinear con
   [#15](../../tasks/issue-15-plan.md), generar ventanas con [#18](../../tasks/issue-18-plan.md)
   y congelar los cortes con [#19](../../tasks/issue-19-plan.md).
3. Exportar con el [comando de #22](../../tasks/issue-22-plan.md). Verificar archivos y
   contenido lógico con TimeNet 0.12.0 y conservar el manifiesto junto con los datos.
4. Para reproducir con un original ficticio y red deshabilitada, usar
   [la prueba de #23](../../tools/timenet-smoke/README.md).

## Licencias y aporte a TimeNet

La base SENAMHI y su versión convertida conservan ODC-By-1.0 y el aviso de origen.
El código de Neblima sigue AGPL-3.0-only. El aporte para TimeNet se escribió por separado
contra su API y sigue MIT conforme al [ADR-003](../decisions/003-licencia-agpl-v3.md).
Ver [el recibo de preparación del aporte](../../tasks/issue-24-plan.md).
