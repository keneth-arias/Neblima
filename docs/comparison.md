# Comparación local y preparación de ventanas (#11)

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

## Puntuación fijada antes del cálculo

Solo puntúan candidatos sin bloqueos y con alguna ventana completa. La escala es 0–1, con saturación
a 1. No se normaliza respecto al mejor candidato observado:

1. Volumen: ventanas completas / (4 estaciones × 24 meses × 720 horas), peso 0,35.
2. Continuidad: ventanas completas / orígenes candidatos, peso 0,25; cero si no hay candidatos.
3. Estaciones: identidades provisionales con ventanas / 4, peso 0,15.
4. Extensión: mayor racha continua de puntos / (24 × 720 horas), peso 0,15.
5. Trazabilidad/validación: 0,5 por la adquisición verificada; 1 al resolver también las condiciones
   institucionales requeridas, peso 0,10. Mientras hay bloqueos no se publica puntuación científica.

La convención fija de 720 horas es un denominador de puntuación, no una equivalencia de 24 meses
calendario ni evidencia de cumplimiento de esa meta. El informe debe indicar su diferencia con
cobertura común y periodos continuos reales. La sensibilidad usa pesos iguales de 0,2 sin alterar
filtros; las puntuaciones bloqueadas siguen nulas. La selección siempre requiere revisión científica;
no se promueve automáticamente a ganador una fuente sin aclaraciones ni se elige H/F por desempeño.

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

La composición de las cuatro estaciones simultáneas puede cambiar entre horas; este diagnóstico
no demuestra una cohorte fija de cuatro estaciones con 24 meses de ventanas comunes.
