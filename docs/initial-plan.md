# AirAware Perú: ingeniería de conjuntos de datos ambientales temporales

## 1. Rol y objetivo

Trabajar con criterios de ingeniería de datos, ciencia ambiental, plataformas de aprendizaje automático
y contribución a código abierto. Diseñar e implementar una secuencia reproducible y eficiente para
investigar, recolectar, analizar, comparar, validar, normalizar e integrar series ambientales de
Lima, Callao y el Perú para el hackathon de TimeNet.

Referencias principales:

- Hackathon: https://challenge.timenet.ai/
- TimeNet: https://github.com/OpenTSLM/TimeNet
- OpenTSLM: https://github.com/OpenTSLM/OpenTSLM
- Documentación: https://docs.timenet.ai/

El resultado será uno o más conjuntos TimeF versionados para entrenar o ajustar modelos temporales
basados en modelos de lenguaje de pesos abiertos. El primer caso de uso es pronosticar PM2.5 y
episodios de alta contaminación en Lima Metropolitana. La arquitectura debe permitir la ampliación
nacional. Priorizar calidad, validez científica, reproducibilidad y licencias sobre tamaño.

Este plan describe trabajo propuesto. El estado implementado se consulta en README.md y GitHub.
Keneth dirige datos y plataforma; la distribución vigente está en docs/team-work-allocation.md.

## 2. Principios de ingeniería

- Preferir software libre y datos accesibles, respetando las condiciones de cada fuente.
- Procesamiento reproducible y determinista; originales inmutables.
- Procedencia y trazabilidad explícitas desde cada resultado hasta el archivo de origen.
- Descargas idempotentes, reanudables e incrementales, con límites de recursos.
- Esquemas y controles automáticos de calidad; configuración versionada.
- Procesamiento eficiente en memoria, sin infraestructura distribuida innecesaria.
- Sin fuga de información entre entrenamiento, validación y prueba.
- Sin imputación no documentada ni mediciones, coordenadas, fechas o unidades inventadas.
- Sin redistribuir datos con licencias incompatibles.
- Implementaciones sencillas, mantenibles y con dependencias justificadas.

El idioma principal es español del Perú. Conservar nombres técnicos, identificadores, comandos y
campos de API; preservar los campos y metadatos originales en español de los archivos fuente.
La política vigente está en ADR-002 y reemplaza la indicación inicial de documentación en inglés.
El historial de Git conserva el documento original previo a esta adaptación.

## 3. Fase 0: investigar el repositorio y la arquitectura de TimeNet

Antes de implementar conectores:

1. Inspeccionar la copia de trabajo y el código existente.
2. Revisar TimeNet, documentación, ejemplos, AGENTS.md y CONTRIBUTING.md vigentes.
3. Determinar Python compatible, dependencias e interfaces.
4. Revisar BaseConnector, TimeFDataset, Signal, Source, Record, ForecastingTask, ClassificationTask y AnswerTask.
5. Revisar hello-world y TSQA y buscar conectores ambientales reutilizables.
6. Verificar datos faltantes, ejes, metadatos, anotaciones, composición, trazabilidad, particiones y licencias.
7. Fijar commits externos y versiones de dependencias.
8. Confirmar los requisitos vigentes de entrega del hackathon.

No deducir firmas de API a partir de versiones antiguas. Entregar PLAN.md, ARCHITECTURE.md,
docs/timenet-integration.md y una lista ordenada con dependencias y criterios de aceptación.
La preparación actual registra inspección de código; las pruebas TimeF en ejecución siguen pendientes.

## 4. Fase 1: investigar fuentes e inventariar datos

Buscar en español e inglés en portales públicos, repositorios científicos y universitarios,
organismos internacionales y API. Los enlaces siguientes son candidatos, no integraciones verificadas.

### Prioridad 0: Mediciones físicas oficiales de calidad del aire

| Recurso candidato | Enlace de partida |
| --- | --- |
| Calidad del aire en Lima — SENAMHI | https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de |
| Datos CSV de SENAMHI Lima | https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de-0 |
| Diccionario de datos de SENAMHI | https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de-1 |
| Metadatos de SENAMHI | https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de-2 |
| Calidad del aire a nivel nacional — OEFA | https://www.datosabiertos.gob.pe/dataset/vigilancia-y-seguimiento-ambiental-en-la-calidad-del-aire-organismo-de-evaluaci%C3%B3n-y |
| Datos CSV de OEFA | https://www.datosabiertos.gob.pe/dataset/vigilancia-y-seguimiento-ambiental-en-la-calidad-del-aire-organismo-de-evaluaci%C3%B3n-y-0 |
| Portal de monitoreo de OEFA | https://sistemas.oefa.gob.pe/pifa/mfe/ |
| Servicio de monitoreo de SENAMHI | https://www.gob.pe/9433 |
| Datos históricos de Lima — DIGESA | https://www.digesa.minsa.gob.pe/DCOVI/mapas/DIGESA_AIR_MR_CalidadAireAnual_LIMA.html |
| Informes de SENAMHI | https://www.gob.pe/institucion/senamhi/colecciones/51679-vigilancia-de-la-calidad-del-aire-en-el-area-metropolitana-de-lima-y-callao |

El catálogo inicial mencionaba aproximadamente 65 MB para SENAMHI y 1.23 GB para OEFA. Son cifras
de catálogo: no tratarlas como tamaños reales hasta descargar e inspeccionar los archivos.

### Prioridad 1: Observaciones adicionales y conjuntos procesados

| Recurso candidato | Enlace de partida |
| --- | --- |
| Explorador OpenAQ | https://explore.openaq.org/ |
| API v3 de OpenAQ | https://docs.openaq.org/ |
| Archivo S3 de OpenAQ | https://registry.opendata.aws/openaq/ |
| Documentación del archivo OpenAQ | https://docs.openaq.org/aws/about |
| Índice Mundial de Calidad del Aire — Perú | https://aqicn.org/country/peru/es/ |
| Datos históricos de WAQI | https://aqicn.org/historical/ |
| AirNow International | https://gispub.epa.gov/airnowembassy/ |
| Calidad Aire Lima | https://github.com/Cristhianbgf/calidad-aire-lima |
| Limaair | https://github.com/quishqa/limaair |
| Base de datos de calidad del aire de la OMS | https://www.who.int/data/gho/data/themes/air-pollution |
| Estadísticas ambientales del INEI | https://www1.inei.gob.pe/biblioteca-virtual/boletines/estadisticas-ambientales/ |
| SINIA — MINAM | https://sinia.minam.gob.pe/portal/datos-abiertos/ |

Distinguir mediciones originales, copias de datos oficiales, estadísticas agregadas, datos derivados
y valores modelados. Verificar si AirNow tiene estaciones históricas pertinentes en el Perú antes
de implementar una integración.

### Prioridad 2: Meteorología

| Recurso candidato | Enlace de partida |
| --- | --- |
| Meteorología horaria de SENAMHI | https://www.datosabiertos.gob.pe/dataset/variables-meteorologicas-de-las-estaciones-autom%C3%A1ticas-de-intercambio-internacional-servicio |
| Red de estaciones de SENAMHI | https://www.senamhi.gob.pe/servicios/?p=estaciones |
| Meteorología histórica de Open-Meteo | https://open-meteo.com/en/docs/historical-weather-api |
| Pronósticos históricos de Open-Meteo | https://open-meteo.com/en/docs/historical-forecast-api |
| ERA5 y ERA5-Land | https://cds.climate.copernicus.eu/ |
| NASA POWER | https://power.larc.nasa.gov/docs/services/api/temporal/hourly/ |
| Base integrada de datos de superficie de NOAA | https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database |
| Sondeos atmosféricos de NOAA | https://www.ncei.noaa.gov/products/weather-balloon/integrated-global-radiosonde-archive |

Investigar temperatura, humedad relativa, punto de rocío, presión, velocidad y dirección del viento,
precipitación, radiación solar, nubosidad, altura de capa límite, estabilidad, inversiones y visibilidad.

### Prioridad 3: Satélites y reanálisis atmosférico

| Recurso candidato | Enlace de partida |
| --- | --- |
| Reanálisis global CAMS EAC4 | https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4 |
| Copernicus Sentinel-5P | https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-5p |
| NASA MODIS MAIAC MCD19A2 | https://www.earthdata.nasa.gov/ |
| PM2.5 superficial global de ACAG | https://sites.wustl.edu/acag/surface-pm2-5/ |
| Calidad del aire CAMS — Open-Meteo | https://open-meteo.com/en/docs/air-quality-api |
| Conjunto procesado CAMS para Lima | https://zenodo.org/records/18673925 |
| Observaciones de incendios de NASA FIRMS | https://firms.modaps.eosdis.nasa.gov/ |

Separar observación satelital, reanálisis y modelado atmosférico. Ninguno equivale por sí solo a una
medición física independiente de contaminación al nivel del suelo.

### Prioridad 4: contexto adicional

Investigar series históricas de tránsito y movilidad, emisiones industriales, incendios y quema de
biomasa, generación eléctrica, actividad industrial, construcción y polvo, feriados, uso del suelo,
elevación y forma urbana. Agregar información estática solo con una relación documentada con el
problema de pronóstico. No inventar fuentes para completar esta lista.

### Requisitos del catálogo

Mantener configs/sources.yaml con identificador único, nombre, descripción, publicador, URL original,
recursos reales o API, geografía, cobertura histórica, resolución temporal y espacial, variables y
unidades, metodología, categoría, formatos y tamaño, autenticación, límites, actualización, licencia,
atribución, permisos de redistribución, limitaciones, prioridad, estado y fecha de verificación.

Estados técnicos: discovered, verified, downloaded, profiled, integrated, blocked, duplicate y excluded.
Conservar las fuentes inaccesibles con explicación. La configuración actual distingue información
sin verificar mediante valores nulos; registrar hechos desconocidos sin inventarlos.

## 5. Fase 2: adquisición de datos

Implementar módulos para HTTP/HTTPS, API REST y almacenamiento S3 público. Admitir CSV, CSV comprimido,
JSON y Parquet; XLSX para diccionarios y metadatos. Agregar NetCDF, GRIB y Zarr cuando sean necesarios.
Comenzar con SENAMHI y OEFA, incluyendo toda su documentación.

Resolver enlaces reales desde el catálogo y rechazar respuestas HTML guardadas como CSV.
Implementar lectura por bloques, concurrencia acotada, tiempos máximos de conexión y lectura,
reintentos con espera exponencial, respeto de límites del proveedor, reanudación cuando sea posible,
SHA-256, escritura atómica, verificación de tipo/formato, manifiestos, caché y filtros de fecha y región.
Las credenciales opcionales deben provenir de variables de entorno.

En OpenAQ, identificar ubicaciones del Perú antes de descargar objetos; no adquirir el archivo mundial.
Para satélites y reanálisis, limitar región, coordenadas, variables y periodo.
Estimar volumen y almacenamiento antes de una descarga grande. Pedir autorización expresa para
adquisiciones costosas o sin límites. No eludir autenticación, restricciones ni límites de acceso.

## 6. Fase 3: almacenamiento original y trazabilidad

Usar carpetas por etapa:

```text
data/
├── raw/
│   ├── senamhi/
│   ├── oefa/
│   ├── digesa/
│   ├── openaq/
│   ├── weather/
│   └── satellite/
├── staging/
├── normalized/
├── curated/
├── benchmarks/
└── timef/
```

- raw: bytes originales sin modificar; registrar URL, fecha UTC, suma, longitud, licencia y versión.
- staging: interpretar esquema, codificación, nombres y fechas por fuente; conservar campos para auditar.
- normalized: observaciones estandarizadas y validadas en Parquet particionado.
- curated: series compatibles, depuradas y sin duplicaciones indebidas.
- benchmarks: tareas, objetivos, ventanas reproducibles y particiones explícitas.
- timef: resultados del escritor oficial de TimeNet.

No subir datos masivos, credenciales, cachés ni pesos de modelos a Git. Cada integrante usa carpetas
propias; no comparte entornos ni credenciales como parte de la instalación.

## 7. Fase 4: análisis exploratorio y comparación de fuentes

Analizar cada conjunto adquirido antes de integrarlo.

### Métricas del conjunto

Contar filas originales/válidas, tamaños comprimido y descomprimido, estaciones, cobertura geográfica,
fechas válidas inicial/final, variables, distribución de frecuencias, horas-estación medidas,
mediciones únicas, años/meses disponibles e inconsistencias de esquema.

### Métricas por estación

Registrar coordenadas, elevación, división administrativa y UBIGEO, contaminantes, clase e instrumentos
cuando estén documentados, periodos de operación y frecuencia. Medir integridad por mes/año,
secuencia válida más larga, mayor hueco, duplicados y conflictos.

### Métricas por señal

Medir datos faltantes/inválidos, negativos, códigos especiales documentados, mínimos, máximos,
percentiles, extremos candidatos a revisión, tramos constantes, patrones diarios/estacionales,
autocorrelación, correlaciones entre contaminantes, relación meteorológica y frecuencia de episodios.
No eliminar automáticamente episodios extremos por ser valores atípicos estadísticos.

### Preparación para pronóstico

Contar ventanas por estación y contaminante para historias de 24, 48, 72 y 168 horas y horizontes de
6, 12, 24 y 48 horas, con varios requisitos de integridad de entradas. Por defecto, objetivos
completamente observados. Informar cuántas ventanas se pierden con cada regla.

### Comparación de fuentes

| Criterio | Peso propuesto |
| --- | --- |
| Integridad de mediciones válidas | 25 % |
| Ventanas utilizables | 20 % |
| Cobertura histórica | 15 % |
| Resolución temporal | 10 % |
| Cobertura geográfica y estaciones | 10 % |
| Licencia y redistribución | 10 % |
| Metadatos y procedencia | 5 % |
| Confiabilidad de adquisición | 5 % |

Documentar fórmulas con propiedades medidas. Una licencia incompatible o mediciones de significado
no verificado excluyen la fuente; una buena puntuación en otros aspectos no compensa ese problema.
Clasificar por separado fuentes de objetivos, preentrenamiento nacional, meteorología, validación
independiente y contexto espacial/satelital.

Comparar periodos comunes con unidades y agregaciones compatibles usando sesgo, MAE, RMSE y correlación.
Distinguir observaciones independientes de copias de una misma medición.

Entregar reports/dataset-comparison.md, dataset-profile.parquet, station-coverage.parquet,
signal-quality.parquet, source-overlap.parquet y forecasting-readiness.parquet bajo reports/.
Agregar mapas de estaciones, gráficos de cobertura y datos faltantes.

## 8. Fase 5: modelo común de datos

Diseñar un esquema independiente del proveedor. Campos propuestos:

```text
observation_id
source_id
source_record_id
source_artifact_sha256
provider_station_id
canonical_station_id
sensor_id
latitude
longitude
altitude_m
department
province
district
ubigeo
parameter
original_parameter
value
unit
original_value
original_unit
timestamp_utc
timestamp_local
interval_start_utc
interval_end_utc
sampling_interval_seconds
aggregation_method
measurement_method
observation_type
quality_flag
is_valid
is_imputed
available_at_utc
forecast_issue_time_utc
source_version
```

Mantener tablas separadas de estaciones, sensores, fuentes, licencias y reubicaciones.
Distinguir datos medidos en suelo, derivados de mediciones, satelitales, modelados, reanálisis,
pronósticos e imputados. Conservar nulos cuando una fuente no proporcione un campo.
Usar WGS84 solo si se conoce el CRS original y preservar coordenadas y CRS originales.
Para OEFA, revisar este/norte UTM, zona y datum antes de transformar.
Normalizar nombres/unidades solo con justificación científica. Las conversiones de gases entre
masa y volumen requieren condiciones de referencia documentadas.

## 9. Fase 6: normalización, duplicados y alineamiento

Implementar transformaciones deterministas de fechas verificadas con America/Lima a UTC,
conservando fechas locales. Diferenciar inicio/fin de observación y frecuencia original.
Normalizar parámetros y unidades compatibles; interpretar solo códigos faltantes documentados.
Detectar conflictos, estandarizar metadatos y registrar reubicaciones/cambios de instrumentos.
Relacionar estaciones entre proveedores con identificadores, coordenadas y procedencia, no solo cercanía.

Distinguir duplicados exactos, observaciones repetidas por agregadores, conflictos del mismo sensor
y mediciones independientes en el mismo lugar. Aplicar precedencia documentada, dando preferencia a
la fuente autorizada y validada cuando sea la misma medición original.

Generar datos horarios solo si lo respalda la frecuencia original. No convertir mediciones diarias
en objetivos horarios artificiales. Mantener máscaras de faltantes e imputados; no usar cero como
contaminación faltante. Si se imputan entradas, usar únicamente información anterior al momento
del pronóstico y conservar método y máscara.

## 10. Fase 7: construcción de series ambientales multivariadas

Usar contaminación medida como línea temporal de referencia. Añadir cuando estén disponibles PM2.5,
PM10, NO₂ y otros contaminantes medidos, meteorología de estaciones, clima histórico de reanálisis,
pronósticos archivados, calendario, estaciones vecinas, satélites/aerosoles, elevación y metadatos.

Usar cruces espaciales apropiados: estación meteorológica validada cercana o interpolación
documentada. Guardar distancias, resolución de grilla, desfases, identificadores y método.
No atribuir resolución de barrio a un modelo atmosférico de grilla gruesa.

Mantener configuraciones experimentales separadas:

1. Solo contaminación observada.
2. Contaminación y meteorología histórica.
3. Contaminación, meteorología y estaciones vecinas.
4. Contaminación, meteorología y reanálisis atmosférico.
5. Contaminación, meteorología y satélites.
6. Pronóstico operativo con pronósticos meteorológicos disponibles en ese momento.

Comparar configuraciones para medir el aporte de cada grupo de variables.

## 11. Fase 8: tareas de pronóstico

Caso inicial: pronóstico de PM2.5 para las próximas 24 horas en Lima Metropolitana.

```yaml
target: pm2_5
frequency: 1h
lookback_hours: 72
forecast_horizon_hours: 24
stride_hours: 24
minimum_input_completeness: 0.90
minimum_target_completeness: 1.00
timezone: America/Lima
```

Son valores iniciales configurables; ajustarlos con el análisis de datos reales.

### A. Pronóstico de varios pasos

Entradas: 72 horas anteriores de contaminación medida y meteorología.
Objetivo: siguientes 24 horas de PM2.5 medido.

### B. Predicción escalar

Predecir el promedio de PM2.5 de las siguientes 24 horas.

### C. Clasificación de episodios

Determinar si el promedio de las siguientes 24 horas supera un umbral documentado.
Verificar el estándar peruano en la norma oficial:
https://www.gob.pe/institucion/minam/normas-legales/3670-003-2017-minam

Revisar periodo de promedio, integridad e interpretación regulatoria. Diferenciar un evento de
ventana móvil de una excedencia por día calendario. No llamar incumplimiento legal del ECA a un
cálculo que no satisfaga la metodología normativa. Un umbral no equivale a ausencia de riesgo sanitario.

### D. Preguntas y respuestas temporales, opcional

Después del pronóstico funcional, generar preguntas deterministas sobre tendencias, máximos,
momento de episodios, diferencias entre estaciones, relaciones observadas con viento/precipitación
y pronósticos. Calcular respuestas verificables; no inventarlas con un modelo ni afirmar causalidad
sin respaldo.

## 12. Fase 9: particiones y prevención de fuga de información

Elegir fechas después de inspeccionar cobertura real. Estrategia inicial cronológica:
70 % más antiguo para entrenamiento, siguiente 15 % para validación y último 15 % para prueba.
Usar límites temporales, no asignación aleatoria de filas.

- Definir límites antes de construir o asignar ventanas.
- Evitar solapamiento de entradas y objetivos entre particiones en la evaluación principal.
- Purgar límites según longitud de historia y horizonte.
- Ajustar escaladores, imputadores, selección de variables y transformaciones aprendidas solo en entrenamiento.
- No exponer PM2.5 futuro como entrada ni reemplazar pronósticos históricos por clima futuro realizado.
- Guardar emisión/disponibilidad de pronósticos y considerar retrasos reales de publicación.
- Evitar duplicados entre particiones y fijar prueba antes de experimentar.

Agregar evaluación espacial secundaria con estaciones totalmente reservadas.
El preentrenamiento nacional seguido de ajuste en Lima es opcional y debe excluir los objetivos de
la evaluación reservada. Entregar manifiestos inmutables y pruebas automáticas de fugas.

## 13. Fase 10: integración con TimeNet y TimeF

Seguir documentación oficial de conectores, tareas, construcción, formato y licencias:

- https://docs.timenet.ai/connectors.html
- https://docs.timenet.ai/data-model/tasks.html
- https://docs.timenet.ai/build.html
- https://docs.timenet.ai/timef-format.html
- https://docs.timenet.ai/catalog/licensing.html

| Identificador propuesto | Propósito |
| --- | --- |
| airaware/lima-senamhi | Observaciones oficiales de Lima |
| airaware/peru-oefa | Observaciones ambientales nacionales |
| airaware/peru-openaq | Observaciones adicionales en suelo |
| airaware/peru-weather | Meteorología observada o productos derivados |
| airaware/peru-atmospheric | Productos atmosféricos y satelitales |
| airaware/lima-air-quality | Evaluación de pronóstico para Lima |
| airaware/peru-air-quality | Futuro conjunto nacional de evaluación |

Verificar reglas y disponibilidad de nombres. Preferir bases independientes y un conjunto compuesto
con versiones padres fijadas cuando TimeNet lo permita. No unir fuentes con licencias o significados
científicos incompatibles.

La estructura siguiente es una propuesta sujeta a la revisión externa fijada:

```text
timenet_connectors/datasets/airaware/
├── lima_senamhi/
│   ├── __init__.py
│   ├── dataset.yaml
│   ├── connector.py
│   ├── requirements.txt
│   └── tests/
├── peru_oefa/
└── lima_air_quality/
```

Usar la interfaz de conector adecuada. Separar adquisición de conversión determinista sin red.
Definir jerarquías de registros, fuentes/sensores, señales/unidades tipadas, origen/ejes temporales
regulares o irregulares, faltantes, estaciones, anotaciones, tareas de pronóstico/clasificación,
particiones, fichas versionadas, trazabilidad, licencias y atribución.

Reutilizar descriptores de señales y referencias a registros/intervalos cuando se admita para evitar
duplicar ventanas superpuestas. Usar escritor, lector y validación oficiales, no un formato imitador.
Los archivos esperados incluyen manifest.json, control.duckdb y valores Parquet o Zarr.
Comprobar carga con el SDK estándar. Investigar señales nulas y tratarlas antes de convertir a PyTorch.

## 14. Fase 11: modelos de referencia y preparación para entrenamiento

Antes de un modelo de lenguaje temporal, implementar último valor observado, persistencia de la
misma hora del día anterior, promedios estacionales y LightGBM o XGBoost. Una red temporal pequeña
es opcional.

Informar MAE, RMSE y MASE cuando corresponda; error por horizonte, estación y temporada; precisión,
exhaustividad, F1 y PR-AUC de episodios; calibración de probabilidades y desempeño en episodios graves.
Usar los mismos objetivos y particiones fijas para todos los modelos.

Preparar un adaptador de tareas TimeNet a OpenTSLM. Investigar modelos compatibles de pesos abiertos
de 270M a 3B, priorizando uno de 1B y entrenamiento eficiente en memoria. No empezar entrenamiento
costoso antes de aprobar calidad y fugas. El ajuste completo es un hito posterior, pero el conjunto
debe estar listo para consumirlo.

## 15. Herramientas recomendadas

| Componente | Herramienta propuesta |
| --- | --- |
| Lenguaje y dependencias | Python y uv |
| Transformación y consultas | Polars y DuckDB |
| Almacenamiento columnar | Parquet y PyArrow |
| Descarga HTTP | HTTPX |
| Validación | Pydantic y esquemas explícitos |
| Geoespacial | GeoPandas, Shapely y PyProj |
| Ráster científico | Xarray |
| Análisis exploratorio | Jupyter |
| Gráficos | Plotly o Matplotlib |
| Comandos | Typer |
| Pruebas | pytest e Hypothesis |
| Formato y análisis estático | Ruff |
| Tipos | Herramienta compatible con TimeNet |
| Integración continua | GitHub Actions |
| Almacenamiento remoto opcional | Compatible con S3 |

Instalar dependencias cuando se necesiten. No introducir Spark, Kafka, Airflow o Kubernetes sin un
problema medido que los justifique. Para datos mayores que la memoria, usar lectura por bloques,
consultas diferidas, selección de particiones y escritura incremental de Parquet.

## 16. Organización propuesta del repositorio

Adaptar a la estructura existente de airaware. Conservar AGENTS.md, README.md, PLAN.md,
ARCHITECTURE.md, CONTRIBUTING.md, pyproject.toml, uv.lock, Makefile, .env.example y .gitignore.
LICENSE contiene AGPL-3.0-only para el código propio, elegida por Keneth. Revisar ADR-003 antes
de preparar contribuciones externas bajo MIT.

```text
configs/
├── sources.yaml
├── schemas/
├── quality.yaml
├── geography.yaml
├── thresholds.yaml
└── benchmark.yaml
src/airaware/
├── cli.py
├── catalog/
├── acquisition/
├── profiling/
├── schemas/
├── normalization/
├── quality/
├── geospatial/
├── alignment/
├── benchmarks/
└── timenet/
tests/
├── unit/
├── integration/
├── fixtures/
└── regression/
notebooks/
reports/
docs/
├── sources/
├── methodology/
└── dataset-cards/
data/
.github/workflows/
```

Los módulos propuestos pueden ser archivos mientras sean pequeños, como catalog.py.
Separar AirAware de la contribución mínima al repositorio externo de TimeNet.

## 17. Comandos y experiencia de desarrollo

La interfaz propuesta debe cubrir las operaciones siguientes. Solo están implementados actualmente
catalog validate, workspace init y doctor; no presentar los otros comandos como disponibles.

```bash
uv sync --locked
uv run airaware discover
uv run airaware catalog validate
uv run airaware download --source senamhi-lima
uv run airaware download --source oefa-peru
uv run airaware download --priority core
uv run airaware profile --source senamhi-lima
uv run airaware profile --all
uv run airaware compare
uv run airaware normalize --all
uv run airaware validate --all
uv run airaware deduplicate
uv run airaware align --region lima
uv run airaware benchmark build --name lima-pm25
uv run airaware benchmark validate --name lima-pm25
uv run airaware export timef --dataset lima-air-quality
uv run airaware report
```

Soportar simulación sin descarga, modo sin red, filtros de fecha/fuente/región, concurrencia limitada,
carpeta de salida y reanudación. Añadir objetivos sencillos de Makefile.
Validar el conector externo por separado con el CLI fijado de TimeNet y sus comandos documentados.

## 18. Fase 12: pruebas e integración continua

Probar catálogo, errores HTTP, sumas de verificación, descargas repetidas/interrumpidas, codificación
y separadores CSV, diccionarios, fechas, unidades, CRS, estaciones, duplicados, faltantes,
remuestreo, objetivos, particiones, fugas, escritura/lectura TimeF y reproducibilidad.

Las pruebas unitarias no dependen de servicios externos. Usar datos sintéticos pequeños y muestras
reales solo si su licencia lo permite. Identificar por separado las pruebas con proveedores reales.
CI debe verificar formato, tipos, pruebas, esquemas, fugas y una construcción TimeF pequeña sin red.
No descargar OEFA completo en cada PR. Ejecutar los controles de contribución de TimeNet antes
de preparar el PR del conjunto.

## 19. Fase 13: documentación y publicación

La ficha completa del conjunto debe explicar propósito, organizaciones fuente y atribución,
metodología de medición, cobertura geográfica e histórica real, variables, frecuencia, controles de
calidad, datos faltantes, sesgos, distribución de estaciones, particiones temporales/espaciales,
licencias/restricciones, reproducción, usos previstos/inadecuados y límites de predicción de riesgos.

Preparar código, instrucciones reproducibles y archivos de datos compatibles con sus derechos.
La contribución mínima a TimeNet incluye conector, ficha, pruebas y documentación pertinente.
**No publicar datos ni abrir PR externos sin autorización explícita.**

## 20. Hitos y prioridades

- M0: investigar TimeNet y fuentes, preparar estructura/versiones y registrar dudas.
- M1: descargar SENAMHI/OEFA y documentación, verificar archivos/sumas y analizar estructura.
- M2: medir calidad/cobertura, comparar estaciones/contaminantes, contar ventanas y seleccionar Lima.
- M3: definir esquema, normalizar unidades/CRS/fechas, deduplicar con procedencia y generar Parquet validado.
- M4: adquirir meteorología por estación y validar cruces espaciales/temporales.
- M5: conector SENAMHI, evaluación Lima, particiones sin fugas, lectura oficial y contribución preparada.
- M6: integrar OEFA, investigar OpenAQ y compatibilidad y construir bases nacionales.
- M7: reanálisis, satélites, incendios/movilidad y comparación de configuraciones opcionales.
- M8: referencias, métricas fijas, adaptador OpenTSLM y preparación del ajuste temporal.

La ruta crítica es M0 a M5, seguida de referencias y experimento temporal en M8.
Resolver ese núcleo antes de invertir esfuerzo importante en contexto opcional.

## 21. Criterios de aceptación generales

La ingeniería inicial se completa cuando:

- Las fuentes identificadas están inventariadas con estado de acceso verificado.
- SENAMHI/OEFA se descargaron y analizaron, o existen bloqueos concretos documentados.
- Las comparaciones usan estadísticas medidas, no suposiciones del catálogo.
- Cada observación depurada tiene procedencia y la licencia está documentada.
- Los esquemas/reglas tienen pruebas y los duplicados se resuelven o marcan explícitamente.
- Los objetivos usan mediciones válidas; las particiones aprueban pruebas de fuga.
- Al menos un conjunto TimeF nativo se genera de forma reproducible y carga con el SDK estándar.
- Un modelo de referencia consume el conjunto; otra persona puede reproducir los resultados.
- La contribución externa está lista para revisión, sin implicar autorización para abrirla.

Metas iniciales: cuatro estaciones utilizables en Lima, 24 meses de observaciones,
90 % de integridad de entradas y objetivos horarios de 24 horas totalmente medidos.
Debe haber suficientes episodios positivos para evaluar clasificación en datos reservados.
Son metas provisionales, no requisitos oficiales del hackathon: informar resultados reales y
justificar cualquier ajuste.

## 22. Instrucciones de ejecución

Comenzar por inspección y planificación: repositorio, TimeNet y disponibilidad de fuentes.
Producir un plan y dependencias antes de una implementación extensa.

1. Dividir en tareas pequeñas que se puedan verificar por separado.
2. Priorizar M0, M1 y M2.
3. Validar SENAMHI/OEFA reales antes de fijar el problema final de pronóstico.
4. Registrar decisiones en ADR y mantener PLAN.md con avances, bloqueos y pendientes.
5. Ejecutar controles después de cada paso y usar commits pequeños con Conventional Commits.
6. Informar mediciones y dudas; no afirmar una recolección o validación sin inspeccionar sus archivos.
7. Evitar entrenamiento e infraestructura prematuros.
8. Ante fuentes inaccesibles, documentar el fallo, intentar alternativas permitidas y continuar con
   tareas independientes. Respetar responsables, disponibilidad y una tarea activa por persona.

El primer resultado práctico debe ser una adquisición reproducible, un inventario completo y una
comparación de calidad de SENAMHI Lima y OEFA Perú. Esas mediciones decidirán el contenido del primer
conjunto TimeF de AirAware Perú.
