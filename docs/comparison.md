# Comparación local y preparación de ventanas (#11)

> Política operativa aprobada: [ADR-005](decisions/005-senamhi-operating-policy.md). comparison-v3 selecciona SENAMHI/Lima/PM2.5
> para pronóstico con etiquetas UTC publicadas y acepta calidad/posición del intervalo desconocidas.
> Esto no bloquea #13 ni #18; las etiquetas regulatorias diarias siguen diferidas.

Ejecutar desde la raíz, después de `make setup`, con las adquisiciones de #8/#9:

```bash
uv run --locked airaware compare run
AIRAWARE_DATA_DIR=/ruta/datos uv run --locked airaware compare run
```

La configuración aprobada es configs/benchmark.yaml y las entradas se fijan en configs/profiling.json.
`--policy`, `--inputs` y `--output-root` permiten elegir rutas; cada archivo de configuración admite
hasta 64 KiB. No se requiere internet. Cada integrante usa sus propios originales/manifiestos y disco;
Git no distribuye los originales. La CLI devuelve salida 1 si no puede verificar/procesar el contrato.

Se reutilizan identidad, contextos y parser temporal de #10, sin homologación ni conversión horaria.
Cada origen t usa H instantes [t−(H−1),t] y F instantes [t+1,t+F], todos horarios y finitos,
sin ambigüedad. Se evalúan las 16 parejas H=24/48/72/168, F=6/12/24/48. PM2.5 es el objetivo
principal aprobado; PM10 es un escenario separado. Lima significa provincia LIMA del departamento
LIMA. Callao es un escenario adicional separado. No se amplía la geografía para completar una cuota.

## Denominadores y filtros

La traza de filas sigue orden fijo: fuera del ámbito, periodo no horario, reloj no interpretable
(o no alineado), valor no finito, intervalo ambiguo, filas aceptadas. Estas categorías son disjuntas
y suman las filas originales. Las filas aceptadas menos repeticiones consolidadas equivalen a puntos
únicos. La cobertura simultánea cuenta identidades distintas con puntos en un mismo instante; no cuenta
varios contextos de la misma estación como estaciones diferentes. No demuestra que todas esas
estaciones tengan ventanas completas en los mismos orígenes. La consolidación solo existe en la vista diagnóstica: no cambia originales ni presume que
todas las repeticiones completas son observaciones duplicadas que deban borrarse.

Para cada serie el universo de orígenes se limita al primer/último punto admisible, dejando espacio
para H y F. No se cuenta como cobertura confirmada toda la extensión de fechas publicada.
La ausencia de puntos se reporta como cero puntos/ventanas estructurales, sin inventar una serie.
Las ventanas se separan en historia incompleta, futuro incompleto entre historias completas y
completas. Estas tres cantidades suman los candidatos. Se usan rachas consecutivas para contar sin
materializar todas las ventanas ni rellenar huecos. Los periodos/contextos/estaciones no se mezclan.
Los límites exteriores que no permiten H+F instantes quedan fuera del universo de candidatos.

`forecasting-readiness.parquet` contiene fuente/hash, política/hash, estación/contexto, señal,
geografía, H/F, conteos, límites del reloj y bloqueos. Si falta una definición científica,
`scientific_valid_windows` es nulo aunque haya ventanas estructurales. Los conteos no sustituyen las
ventanas de entrenamiento de #18 ni los splits de #19. Las estadísticas no determinan filtros usando
resultados de prueba futuros. No se descartan negativos ni extremos solo por su magnitud.

## Política vigente comparison-v2 (17/11/2026)

Keneth eliminó la cuota fija de estaciones y meses continuos. No hay denominador de 4×24×720
ni puntuación de tamaño sustituta. Se publican ventanas, estaciones, rachas y pérdidas reales;
components, scientific_score y sensitivity_equal quedan nulos en v2. Los pesos históricos no
se aplican. La cobertura simultánea se informa para al menos una estación (quorum_stations=1),
como disponibilidad del archivo y no como una nueva condición de aceptación.

La política comparison-v1 conserva compatibilidad de lectura con denominadores explícitos para
reproducir informes históricos; no es la configuración vigente. No cambiar hashes ni resultados
viejos para simular que se calcularon con v2. Los bloqueos científicos siguen siendo independientes
de tener más o menos datos. Para SENAMHI, UTC y unidades operativas están en la decisión #13;
la posición del intervalo y la calidad individual quedan pendientes, sin bloquear normalización.

## Solapamientos y publicación

`source-overlap.parquet` cuenta intersección de instantes distintos en el reloj original por señal y
geografía; no empareja estaciones de redes distintas. La intersección científica permanece nula
porque no está verificada la compatibilidad de relojes entre fuentes. Cero en el diagnóstico no
prueba ausencia histórica de mediciones cuando los timestamps están ausentes.

Cada ejecución crea una carpeta nueva en reports/generated/comparison/ con ambos Parquet,
summary.json y manifest.json. Se verifica el original antes, después de procesar cada fuente y
antes de publicar; las salidas se publican juntas por renombrado. Un error elimina únicamente los
temporales de esa ejecución. DuckDB usa dos hilos, memoria configurada 768 MB (no límite absoluto
del proceso), temporales de hasta 10 GB y extensiones automáticas deshabilitadas. No hay servidor.

Los bloqueos declarados por fuente deben ser explícitos en configuración, incluso si la lista está
vacía tras revisión documentada. Cambiarla no aporta por sí mismo evidencia de unidades, reloj,
calidad o derechos. Toda revisión debe conservar la procedencia institucional que justifique el cambio.
La configuración y su versión forman parte de los hashes de cada entrega.

La cobertura simultánea no implica una cohorte fija. En v2 se informa disponibilidad con al menos
una estación; no se exige un número de estaciones o meses continuos.
