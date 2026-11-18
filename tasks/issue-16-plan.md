# #16 · Verificación de fuentes meteorológicas y muestra por estación

Estado: **completada**. Muestra real de reanálisis (ERA5), pronóstico archivado (GFS
`previous_day1`) y medición de estación en Lima (NOAA ISD Global Hourly,
**84628099999 «JORGE CHAVEZ INTERNATIONAL, PE»**, objeto NODD directo) adquirida, verificada y
reconciliada: 15 recursos, 4 731 512 bytes publicados. La identidad de la estación NOAA
seleccionada se verificó leyendo su propio CSV descargado (no desde su ID): aeropuerto
internacional Jorge Chávez, Callao, a 3,6–26,5 km de las siete estaciones de aire de Lima
(haversine aproximado). El objeto adquirido en attempt-03 (`2015/84691099999.csv`) resultó ser,
desde su propio contenido, «PISCO INTERNATIONAL, PE» (a 191–223 km): quedó **rechazado** como
muestra de Lima y se conserva sin cambios como evidencia histórica bajo `data/raw/` (16 recursos
y 9 114 066 bytes acumulados en todos los intentos, contados por separado de la selección).
Evidencia: [docs/sources/weather.md](../sources/weather.md),
[reports/acquisition/weather.md](../reports/acquisition/weather.md),
[metadata/weather-acquisition.json](../metadata/weather-acquisition.json). Este archivo se cierra
con el estado real; no adelanta afirmaciones de cobertura, derechos ni adquisición. La tarea es
de adquisición y evidencia: no implementa la alineación de #17, ni entrenamiento, ni cambios de
particiones del benchmark.

## Objetivo y alcance

1. Comparar fuentes meteorológicas oficiales para Lima con evidencia fechada: observaciones de
   estaciones, productos históricos/reanálisis y pronósticos archivados, en
   `docs/sources/weather.md`.
2. Adquirir una muestra real, acotada y reproducible para las siete identidades provisionales de
   estaciones de SENAMHI con PM2.5, o registrar un bloqueo preciso con evidencia si toda ruta
   autorizada falla.
3. Documentar cobertura, variables, unidades, resolución espacial y temporal, derechos, tiempo de
   observación/validez, disponibilidad de publicación y hora de emisión cuando aplique.
4. Mantener separados medición de estación, reanálisis/salida de modelo y pronóstico archivado.

Fuera de alcance: #17 (alineación sin información futura), exportación TimeF, etiquetas
regulatorias y cambios en `configs/benchmark.yaml` o umbrales.

## Identidades provisionales de estación (derivadas, no supuestas)

Regla de #14: `station_key = sha256('senamhi-lima-csv' || to_json(list_value(ESTACION, LONGITUD,
LATITUD, ALTITUD, DEPARTAMENTO, PROVINCIA, DISTRITO)))` sobre los campos originales como texto.

Original: `.worktrees/issue-13-senamhi-normalization-plan/data/raw/senamhi/senamhi_lima_monitoreo_1.csv`
(68 501 558 bytes; SHA-256 `896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4`),
leído en modo solo lectura. Filas totales 577 794; contextos de estación distintos en todo el
archivo: 7; contextos con PM2.5 finito en Lima: 7. Las siete identidades coinciden con las
documentadas por #11/#14:

| station_key | ESTACION | LONGITUD | LATITUD | ALTITUD | DISTRITO |
| --- | --- | --- | --- | --- | --- |
| 90b36a172f1790cf2e37ac2063f80fd27439d4ecf871d72a20bf8e9786587a67 | CAMPO_DE_MARTE | -77.0432 | -12.0705 | 117.0 | JESUS_MARIA |
| 8436576ff150fd696edbc1cd625bc97696321bc9c57b24b906d0d4a12b71bfff | CARABAYLLO | -77.0336 | -11.9022 | 179.0 | CARABAYLLO |
| 2a0d574b25a5dc8c7f6edda9836225860faaa160763d8bea15d95646794f0bd8 | SANTA_ANITA | -76.9714 | -12.043 | 253.0 | SANTA_ANITA |
| 8e88d45c03f25f49b84c98cc4916bd60b67383961e186497f4d77570c2f75d34 | SAN_BORJA | -77.0077 | -12.1086 | 128.0 | SAN_BORJA |
| 22c516fbe293a54c1cb5ddc7727d32430200221562cd01af8a40cc4b5de227d4 | SAN_JUAN_DE_LURIGANCHO | -76.9992 | -11.9816 | 240.0 | SAN_JUAN_DE_LURIGANCHO |
| 35170dbfe2a7135c1cecbae1e367374a284578533740ff5461d40fc764851e07 | SAN_MARTIN_DE_PORRES | -77.0845 | -12.0089 | 56.0 | SAN_MARTIN_DE_PORRES |
| 1e58bb71f42f67bfedae1bad1e35b0aea5f84078da4f3a6f06c695aac1fb99e4 | VILLA_MARIA_DEL_TRIUNFO | -76.92 | -12.1664 | 272.0 | VILLA_MARIA_DEL_TRIUNFO |

Coordenadas originales del CSV; no se inventan altitudes ni nombres para otras fuentes. La
correspondencia con estaciones meteorológicas o celdas de grilla de terceros se documenta como
mapeo con distancia y limitación, no como equivalencia.

## Contrato de muestra determinista (fijado antes de solicitar datos meteorológicos)

- Regla de intervalo, derivada solo de la cobertura de PM2.5 de SENAMHI: el primer intervalo
  consecutivo de 168 horas UTC (barrido horario ascendente desde la primera hora con las siete
  estaciones) dentro de `train` — antes del corte de validación 2022-03-16 08:00 UTC — en el que
  las siete identidades tienen al menos un valor finito de PM2.5 en cada hora. Desempate: inicio
  más temprano. El resultado del barrido sobre el original verificado es:
  **2015-04-16T18:00:00Z a 2015-04-23T17:00:00Z inclusive** (168 horas).
- Este intervalo se eligió sin ver valores meteorológicos de ninguna fuente externa y sin usar
  desempeño de modelos, calidad de clima ni particiones de prueba.
- Para productos de grilla/API: solicitar las siete coordenadas exactas de las estaciones.
- Para estaciones de terceros: registrar ID del proveedor, coordenadas, distancia a cada estación
  de aire pertinente y limitación del mapeo; no se fabrica correspondencia uno a uno.
- Variables iniciales cuando la fuente las documenta: temperatura, humedad relativa, velocidad y
  dirección del viento, presión y precipitación. Punto de rocío, radiación, nubosidad o altura de
  capa límite solo con uso claro y evidencia.
- La muestra verifica la fuente; no selecciona modelos ni muta el benchmark. Sin imputación,
  divisiones aleatorias ni información futura.
- Pronósticos archivados: si el producto no cubre 2015, se usa una muestra acotada separada y
  documentada por su propio periodo; no se rotula reanálisis como pronóstico.

## Límites duros de esta ejecución (autorización acotada)

- Transferencia total nueva de clima: ≤ 134 217 728 bytes (128 MiB) acumulados entre todos los
  recursos e intentos; se registra el acumulado después de cada solicitud.
- Máximo 32 recursos/solicitudes seleccionados de clima en este intento.
- `max_bytes` explícito y proporcionado por recurso; plazo por recurso ≤ 120 s.
- Concurrencia 1; nunca más de 2.
- Sin archivo mundial, extracto plurianual masivo ni consulta sin límites.
- Detener transferencias si la contabilidad acumulada deja de ser cierta. Nunca reintentar a
  ciegas una transferencia incierta: conciliar primero archivos y manifiestos locales.
- `--authorize-unknown` solo para respuestas de API acotadas apropiadas, dentro de los techos.
- Sin cuentas nuevas, pagos, credenciales ni publicación externa.

## Rutas seleccionadas y presupuestos por recurso (registrados antes de transferir)

Muestra planificada con tres productos independientes, uno por clase; **tres entregados**
(detalle por ruta abajo). Coordenadas solicitadas:
las siete originales de las estaciones (sección anterior), sin redondeos.

1. Grilla/reanálisis — `open-meteo-historical-weather` (ERA5 explícito, `models=era5`):
   `https://archive-api.open-meteo.com/v1/archive?latitude=<lat>&longitude=<lon>&start_date=2015-04-16&end_date=2015-04-23&hourly=temperature_2m,relative_humidity_2m,precipitation,surface_pressure,wind_speed_10m,wind_direction_10m&models=era5`
   — 7 solicitudes (una por estación; la API solo acepta una lista de coordenadas si la
   respuesta fuera un objeto, y el validador JSON exige objeto raíz). Ventana solicitada: dos
   días completos de borde que contienen el intervalo de 168 h (2015-04-16T18:00Z a
   2015-04-23T17:00Z); el recorte exacto se hace en la reconciliación local, nunca en el
   proveedor. `max_bytes` 131 072 por recurso; tamaño esperado ~20 000.
2. Pronóstico archivado — `open-meteo-previous-model-runs` (GFS):
   `https://previous-runs-api.open-meteo.com/v1/forecast?latitude=<lat>&longitude=<lon>&start_date=2022-03-09&end_date=2022-03-15&hourly=temperature_2m,temperature_2m_previous_day1&models=gfs_seamless`
   — 7 solicitudes. Ventana separada y documentada: 2022-03-09T00:00Z a 2022-03-15T23:00Z,
   dentro de `train` (todas las marcas válidas < 2022-03-16 08:00 UTC); adelanto explícito
   previous_day1 (emisión = válido − 24 h). `max_bytes` 65 536 por recurso; tamaño esperado 8 000.
3. Medición de estación — `noaa-isd-global-hourly`:
   `https://noaa-global-hourly-pds.s3.amazonaws.com/2015/84628099999.csv`
   (canal http_file con `source_page_url` = página del producto ISD; la ruta de acceso NCEI
   `/data/global-hourly/access/` respondía 301 hacia el mismo canal NODD — historia
   preservada). Un archivo, un año, una estación. Techo autorizado por el gerente:
   **`max_bytes` 5 000 000** (muy por debajo del techo del asunto de 128 MiB) con tamaño
   esperado **4 629 175** (Content-Length del HEAD previo del gerente).
   **Historia (attempt-03, rechazada):** el objeto `2015/84691099999.csv` se transfirió con
   éxito (HTTP 200, 4 382 554 bytes, SHA-256
   `6e6f79a85c70adb7669be1ed6d2f0ae5a1cf2995358b6268fd0867307e37832e`), pero la lectura de su
   propio contenido identificó «PISCO INTERNATIONAL, PE» (-13.744864, -76.220284, 11,88 m),
   a 191,2–223,1 km de las siete estaciones de aire: **rechazado por identidad desde
   contenido**, preservado sin cambios bajo `data/raw/` y excluido de la selección y de los
   totales publicados (contado por separado en la contabilidad de todos los intentos).
   **Resultado vigente (18/11/2026, attempt-04): SELECCIONADA LIMA.** Transferencia única
   HTTP 200 sin redirección, original de exactamente 4 629 175 bytes, SHA-256
   `1e5381f2fce145f949456e5749345c38ba6c52db357f1a554448c86c86d9b92b` verificado; la selección
   procedió solo tras leer el CSV descargado: estación 84628099999 «JORGE CHAVEZ
   INTERNATIONAL, PE» (-12.021889, -77.114319, 34,44 m), distancias haversine aproximadas a las
   siete estaciones de aire: **3,6–26,5 km** (CRS SENAMHI no declarado; sin mapeo ni
   equivalencia). Estructura conciliada (11 441 filas; 8 803 instantes distintos + 2 638
   duplicados por pares FM-12/FM-15 y FM-15/FM-16; REPORT_TYPE FM-12 2 652, FM-15 8 674,
   FM-16 115; subcampos WND 5, CIG/VIS 4, TMP/DEW/SLP 2; 135 filas del año fuera de hora
   reportadas sin reasignar) sin decodificar unidades ni escalas; en la semana de la muestra la
   cobertura no es continua (167 instantes en punto de 168 posibles más 12 SPECI). Detalle:
   `reports/acquisition/weather.md`.

Límites de ejecución: 15 recursos ≤ 32 autorizados; presupuesto total del lote
`--budget-bytes 6376256` (suma de los techos por recurso; 6,08 MiB de 128 MiB autorizados);
`--workers 1`; `--deadline-seconds 60` por recurso (≤ 120 s); hosts autorizados:
`archive-api.open-meteo.com`, `previous-runs-api.open-meteo.com`,
`noaa-global-hourly-pds.s3.amazonaws.com` (el host NCEI inicial quedó fuera tras la
redirección 301 documentada). Sin `--authorize-unknown`: los tamaños esperados se declaran en
el plan. Si un recurso falla con 403/404 o formato no admitido, se registra una vez y continúan
los independientes.

## Comandos: previstos y ejecutados

```bash
make check                                    # línea base antes de editar (aprobado: 345 pruebas) — EJECUTADO, exit 0
uv run --locked airaware catalog validate     # EJECUTADO al cierre (ver registro de verificación)
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json --dry-run
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json \
  --budget-bytes 5570560 --allow-host archive-api.open-meteo.com \
  --allow-host previous-runs-api.open-meteo.com --allow-host www.ncei.noaa.gov \
  --workers 1 --deadline-seconds 60           # EJECUTADO en el intento previo: completó los 14 Open-Meteo;
                                              # NOAA falló (301); consola exacta no recuperable
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json \
  --source noaa-isd-global-hourly --budget-bytes 4194304 --allow-host www.ncei.noaa.gov \
  --workers 1 --deadline-seconds 60           # EJECUTADO en attempt-02: exit 1, network_bytes 0 (301; historia preservada)
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json \
  --source noaa-isd-global-hourly --dry-run   # EJECUTADO en attempt-03: exit 0; tamaño declarado 4382554 ≤ 5000000
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json \
  --source noaa-isd-global-hourly --budget-bytes 5000000 \
  --allow-host noaa-global-hourly-pds.s3.amazonaws.com --workers 1 --deadline-seconds 60
                                              # EJECUTADO en attempt-03 (objeto Pisco, luego RECHAZADO por identidad
                                              # desde contenido): exit 0; HTTP 200; 4382554 bytes en disco
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json \
  --source open-meteo-historical-weather --offline --budget-bytes 0   # exit 0, 7/7 reused, network 0
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json \
  --source open-meteo-previous-model-runs --offline --budget-bytes 0  # exit 0, 7/7 reused, network 0
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json \
  --offline --budget-bytes 0                  # EJECUTADO en attempt-03: exit 0, 15/15 reused, network 0
                                              # (plan de entonces, con Pisco aún seleccionado)
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json \
  --source noaa-isd-global-hourly --dry-run   # EJECUTADO en attempt-04 (URL Lima 84628099999, esperado 4629175): exit 0
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json \
  --source noaa-isd-global-hourly --budget-bytes 5000000 \
  --allow-host noaa-global-hourly-pds.s3.amazonaws.com --workers 1 --deadline-seconds 60
                                              # EJECUTADO en attempt-04: exit 0; HTTP 200; attempts 1; única
                                              # transferencia en vivo del intento; network_bytes 4694711
                                              # (= 4629175 original + 65536 prefijo Range); identidad Lima
                                              # verificada leyendo el CSV antes de seleccionar
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json \
  --offline --budget-bytes 0                  # EJECUTADO en attempt-04 sobre el plan vigente: exit 0, 15/15 reused, network 0
make check && make build && make audit        # EJECUTADOS al cierre (ver registro de verificación)
git diff --check                              # EJECUTADO al cierre (sin salidas)
```

La verificación sin red final corrió sobre el plan completo de 15 recursos (15/15 `reused`,
`network_bytes: 0`, exit 0). Los recibos y conteos por estación viven en
`metadata/weather-acquisition.json`; la evidencia de ejecución en
`reports/acquisition/weather.md`. Los bytes originales de la muestra quedan bajo `data/raw/`
(ignorado por Git); nunca se suben al repositorio.

## Rutas y evidencia

| Producto | Ruta |
| --- | --- |
| Comparación de fuentes con evidencia fechada | `docs/sources/weather.md` |
| Metadatos verificados de fuentes seleccionadas | `configs/sources.yaml` (solo entradas nuevas o correcciones de clima) |
| Especificaciones acotadas no secretas | `configs/acquisition/weather-*.json` |
| Recibos de adquisición/validación | `metadata/weather-*.json` |
| Informe de ejecución y reconciliación real | `reports/acquisition/weather.md` |
| Este plan y estado final | `tasks/issue-16-plan.md` |

## Registro de verificación de páginas web

Toda consulta de páginas oficiales usa Lightpanda (`/usr/local/bin/lightpanda`, versión
`1.1.0-nightly.12173+18ff596e6`) según `docs/web-access.md`: URL solicitada y final, fecha UTC,
título y resultado. La transferencia de datos de API pública usa `airaware acquire api` con
documentación oficial revisada. Los archivos obtenidos por Lightpanda se registran con
`airaware acquire import-file`.

## Lista de verificación de aceptación

- [x] R1 Comparación: `docs/sources/weather.md` distingue observación, reanálisis/modelo y
      pronóstico con evidencia oficial fechada, derechos y limitaciones por decisión. La
      redistribución del proyecto se separa de los términos declarados de cada licencia; el
      catálogo mantiene `unknown` para las fuentes meteorológicas.
- [x] R2 Muestra de siete estaciones: contenido real adquirido e inspeccionado para las siete
      coordenadas con tres productos elegibles (ERA5 reanálisis, GFS `previous_day1` y medición
      NOAA ISD), con reconciliación por estación y celda (`reports/acquisition/weather.md`,
      `metadata/weather-acquisition.json`): 15 recursos, 4 731 512 bytes, SHA-256 15/15, 0
      faltantes en las variables Open-Meteo muestreadas. La estación NOAA seleccionada es
      «JORGE CHAVEZ INTERNATIONAL, PE» (84628099999), verificada desde su propio CSV, a
      3,6–26,5 km de las estaciones de aire; el objeto Pisco de attempt-03 quedó rechazado por
      identidad desde contenido y preservado como historia (nunca como selección de Lima).
- [x] R3 Semántica temporal: observación/validez, emisión = válido − 24 h (previous_day1) y
      disponibilidad declarada (~5 días ERA5) documentadas por producto; `DATE` ISD en formato
      ISO-8601 sin sufijo Z (UTC declarado) con 8 803 instantes distintos y 2 638 duplicados
      simultáneos conciliados (más 135 filas del año fuera de hora reportadas sin reasignar);
      `acquired_at` de manifiestos nunca se usa como `available_at`; posición del intervalo
      horario y `available_at` horario quedan explícitos como desconocidos.
- [x] R4 Procedencia y derechos: originales intactos bajo `data/raw/` (fuera de Git),
      SHA-256 recalculado 15/15 coincidentes, manifiestos con HTTP 200 y `acquired_at`, comandos
      y exit codes registrados; atribución citada de los términos oficiales sin derechos
      inferidos (ISD mantiene licencia `null` y `redistribution: unknown`).
- [x] R5 Reproducibilidad: reutilización sin red ejecutada sobre el plan completo
      (`--offline --budget-bytes 0`): 15/15 `reused` (7 ERA5 + 7 GFS + 1 NOAA), `network_bytes:
      0`, exit 0; los originales y manifiestos no se modificaron; conciliación local
      determinista repetible desde el recibo.
- [x] R6 Alcance: sin alineación #17, entrenamiento ni cambios de benchmark; sin datos masivos
      en Git; sin dependencias nuevas ni código de adquisición adicional (los canales existentes
      `api`/`http_file` fueron suficientes, incluido para diagnosticar el bloqueo inicial NOAA);
      sin edición global.
- [x] R7 Calidad: `tests/test_catalog.py` conserva el invariante estricto
      `len(rows) == len(catalog.sources)`, la unicidad y la igualdad de conjuntos
      fuente/evidencia sin ninguna cota numérica dura de inventario; `make check` (345
      pruebas), `make build`, `make audit`, `uv run --locked airaware catalog validate`
      (40 fuentes) y `git diff --check` aprobados con exit 0 al cierre.
- [x] R8 Entrega: commits pequeños en Conventional Commits en español sobre
      `feat/issue-16-weather-sample`, sin push ni merge.

## Estado final

- **Rama**: `feat/issue-16-weather-sample`; sin push, PR ni merge.
- **Entregado**: comparación fechada de 10 candidatos (`docs/sources/weather.md`); catálogo
  actualizado y validado (40 fuentes; `noaa-isd-global-hourly` en estado `downloaded` con la URL
  NODD directa de Lima y la evidencia Lightpanda conservada); plan de adquisición acotado de 15
  recursos (techo NOAA autorizado 5 000 000 bytes; presupuesto del lote 6 376 256); muestra real
  verificada de 15 recursos (4 731 512 bytes: 65 867 ERA5 + 36 470 GFS + 4 629 175 NOAA Lima)
  con reconciliación por estación, celda y corte de 168 h, identidad NOAA desde el propio CSV
  (Jorge Chávez/Lima) y distancias haversine aproximadas (3,6–26,5 km); corrección attempt-04
  tras el rechazo por contenido del objeto Pisco de attempt-03 (preservado sin cambios como
  historia: 16 recursos y 9 114 066 bytes acumulados en todos los intentos, contados por
  separado); bloqueo inicial NOAA (301 + techo local) preservado como historia; recibo
  `metadata/weather-acquisition.json`; informe `reports/acquisition/weather.md`; prueba de
  catálogo sin cotas numéricas duras.
- **Clasificación para #17**: reanálisis ERA5 vía Open-Meteo — «investigación retrospectiva»
  hasta decidir disponibilidad operativa y derechos de integración; pronóstico archivado GFS
  `previous_day1` — con emisión explícita, misma condición de decisión; medición de estación —
  ruta ISD por estación-año demostrada con una estación real de Lima/Callao (aeropuerto Jorge
  Chávez, 3,6–26,5 km de las estaciones de aire), pero **sin equivalencia automática**: su
  cobertura horaria en la semana de la muestra no es continua (167 instantes en punto de 168
  posibles, más SPECI fuera de hora), no es una estación de aire y la decisión de integrarla
  requiere evidencia de disponibilidad y derechos en #17; SENAMHI GBON — diferida (CSV
  monolítico nacional); OEFA — bloqueada por reloj, unidades y calidad sin resolver.
- **No entregado (explícito)**: unidades/escalas de los subcampos codificados ISD sin
  decodificar; contabilidad exacta de bytes de red del intento Open-Meteo previo no recuperable
  (la diferencia de 65 536 bytes de los contadores NOAA quedó explicada en attempt-04 desde el
  código del canal); correspondencia entre la estación ISD de aeropuerto y las estaciones de
  aire sin resolver (fuera del alcance de #16).
- **Rutas protegidas**: `.worktrees/` y `reports/acquisition/senamhi-lima-2026-11-16.md` sin
  agregar, editar, mover ni eliminar.
