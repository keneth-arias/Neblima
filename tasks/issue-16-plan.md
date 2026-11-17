# #16 · Verificación de fuentes meteorológicas y muestra por estación

Estado: **completada con un bloqueo explícito**. Muestra real de reanálisis (ERA5) y pronóstico
archivado (GFS `previous_day1`) adquirida, verificada y reconciliada para las siete coordenadas;
la ruta de medición de estación (NOAA ISD) quedó bloqueada por techo de bytes con evidencia
exacta. Evidencia: [docs/sources/weather.md](../sources/weather.md),
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

Muestra planificada con tres productos independientes, uno por clase; dos entregados y uno
bloqueado (detalle por ruta abajo). Coordenadas solicitadas:
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
   `https://www.ncei.noaa.gov/data/global-hourly/access/2015/84691099999.csv`
   (canal http_file con `source_page_url` = página del producto ISD). Un archivo, un año, una
   estación. `max_bytes` 4 194 304; tamaño esperado ~1 600 000.
   **Resultado (17/11/2026, intento único): BLOQUEADA.** El acquirer respondió
   «Recurso público respondió HTTP 301; transferencia detenida» con 0 bytes de red y sin
   escritura local. Diagnóstico solo-cabeceras: la URL responde 301 hacia
   `noaa-global-hourly-pds.s3.amazonaws.com` (NODD) y el CSV canónico mide 4 382 554 bytes,
   por encima del techo fijado (4 194 304); una transferencia parcial truncaría filas y está
   prohibida. Sin reintentos; sin datos medidos adquiridos. Detalle:
   `reports/acquisition/weather.md`.

Límites de ejecución: 15 recursos ≤ 32 autorizados; presupuesto total del lote
`--budget-bytes 5570560` (suma de los techos por recurso; 5,31 MiB de 128 MiB autorizados);
`--workers 1`; `--deadline-seconds 60` por recurso (≤ 120 s); hosts autorizados:
`archive-api.open-meteo.com`, `previous-runs-api.open-meteo.com`, `www.ncei.noaa.gov`.
Sin `--authorize-unknown`: los tamaños esperados se declaran en el plan. Si un recurso falla
con 403/404 o formato no admitido, se registra una vez y continúan los independientes.

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
  --workers 1 --deadline-seconds 60           # EJECUTADO en la continuación: exit 1, network_bytes 0 (error exacto en el informe)
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json \
  --source open-meteo-historical-weather --offline --budget-bytes 0   # exit 0, 7/7 reused, network 0
uv run --locked airaware acquire batch --plan configs/acquisition/weather-lima-sample-plan.json \
  --source open-meteo-previous-model-runs --offline --budget-bytes 0  # exit 0, 7/7 reused, network 0
make check && make build && make audit        # EJECUTADOS al cierre (ver registro de verificación)
git diff --check                              # EJECUTADO al cierre (sin salidas)
```

El lote completo de 15 recursos con `--offline` no se ejecuta: la verificación sin red se corrió
por selección de fuente (las dos Open-Meteo) porque NOAA no tiene original local que reutilizar.
Los recibos y conteos por estación viven en `metadata/weather-acquisition.json`; la evidencia de
ejecución en `reports/acquisition/weather.md`. Los bytes originales de la muestra quedan bajo
`data/raw/` (ignorado por Git); nunca se suben al repositorio.

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
      coordenadas con dos productos elegibles (ERA5 reanálisis y GFS `previous_day1`), con
      reconciliación por estación y celda (`reports/acquisition/weather.md`,
      `metadata/weather-acquisition.json`): 14 recursos, 102 337 bytes, SHA-256 14/14, 0
      faltantes en las variables muestreadas. La ruta de medición de estación (NOAA ISD) queda
      bloqueada con error exacto y evidencia de techo de bytes; no se disimula ni se sustituye
      con datos sintéticos.
- [x] R3 Semántica temporal: observación/validez, emisión = válido − 24 h (previous_day1) y
      disponibilidad declarada (~5 días ERA5) documentadas por producto; `acquired_at` de
      manifiestos (2026-11-17T23:41:45–48Z) nunca se usa como `available_at`; posición del
      intervalo horario y `available_at` horario quedan explícitos como desconocidos.
- [x] R4 Procedencia y derechos: originales intactos bajo `data/raw/` (fuera de Git),
      SHA-256 recalculado 14/14 coincidentes, manifiestos con HTTP 200 y `acquired_at`, comandos
      y exit codes registrados; atribución citada de los términos oficiales sin derechos
      inferidos.
- [x] R5 Reproducibilidad: reutilización sin red ejecutada por selección de fuente
      (`--offline --budget-bytes 0`): 7/7 + 7/7 `reused`, `network_bytes: 0`, exit 0; los
      originales y manifiestos no se modificaron; conciliación local determinista repetible
      desde el recibo.
- [x] R6 Alcance: sin alineación #17, entrenamiento ni cambios de benchmark; sin datos masivos
      en Git; sin dependencias nuevas ni código de adquisición adicional (los canales existentes
      `api`/`http_file` fueron suficientes, incluido para diagnosticar el bloqueo NOAA); sin
      edición global.
- [x] R7 Calidad: la única prueba modificada (`tests/test_catalog.py`) reemplaza el número
      duro 40 por el invariante estricto `len(rows) == len(catalog.sources)` con cota
      `>= 40`, conservando la verificación de identidad fuente/evidencia; `make check` (345
      pruebas), `make build`, `make audit`, `uv run --locked airaware catalog validate`
      (40 fuentes) y `git diff --check` aprobados con exit 0 al cierre.
- [x] R8 Entrega: commits pequeños en Conventional Commits en español sobre
      `feat/issue-16-weather-sample`, sin push ni merge.

## Estado final

- **Rama**: `feat/issue-16-weather-sample`; HEAD de partida `f4f19af` (baseline de
  `origin/main`); sin push, PR ni merge.
- **Entregado**: comparación fechada de 10 candidatos (`docs/sources/weather.md`); catálogo
  actualizado y validado (40 fuentes; `noaa-isd-global-hourly` añadido como evidencia del
  recurso accesado); plan de adquisición acotado de 15 recursos; muestra real verificada de 14
  recursos Open-Meteo (102 337 bytes) con reconciliación por estación, celda y corte de 168 h;
  bloqueo NOAA ISD documentado con error exacto, redirección NODD y evidencia de tamaño; recibo
  `metadata/weather-acquisition.json`; informe `reports/acquisition/weather.md`; prueba de
  catálogo menos frágil.
- **Clasificación para #17**: reanálisis ERA5 vía Open-Meteo — «investigación retrospectiva»
  hasta decidir disponibilidad operativa y derechos de integración; pronóstico archivado GFS
  `previous_day1` — con emisión explícita, misma condición de decisión; medición de estación —
  bloqueada en la ruta ISD por techo de bytes (extender el techo requiere autorización del
  responsable); SENAMHI GBON — diferida (CSV monolítico nacional); OEFA — bloqueada por reloj,
  unidades y calidad sin resolver.
- **No entregado (explícito)**: ninguna observación medida adquirida; sin distancias
  estación-aire (no hay identidad NOAA desde contenido); contabilidad exacta de bytes de red del
  intento previo no recuperable (se reporta el vacío sin inventarlo).
- **Rutas protegidas**: `.worktrees/` y `reports/acquisition/senamhi-lima-2026-11-16.md` sin
  agregar, editar, mover ni eliminar.
