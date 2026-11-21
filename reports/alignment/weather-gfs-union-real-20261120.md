# Unión real meteorología–PM2.5 sobre ventanas congeladas (#17)

Informe de la primera unión real del pronóstico archivado GFS `temperature_2m_previous_day1`
con la grilla horaria real de PM2.5, usando el módulo vigente `src/airaware/weather_alignment.py`
sin modificaciones. Ejecutada por Cristopher (@qriqs) el **2026-11-20**. Evidencia compacta
correlata: `metadata/weather-union-real-20261120.json`.

## Ejecución

- **Rama/base**: `feat/issue-17-union-real` desde `origin/main` (`4dd2244`, merge de #133).
- **Insumos meteorológicos**: los 7 paquetes `open-meteo-previous-model-runs` fijados por
  `configs/acquisition/weather-lima-sample-plan.json`, copiados byte a byte al worktree
  (`data/raw/open-meteo-previous-model-runs/`, ignorado por Git) tras verificar cada SHA-256
  contra el plan; verificación repetida después de la corrida (7/7 sin cambios). El árbol de
  datos de Keneth no tiene copia de esta fuente bajo `data/raw`, por lo que la mejor
  procedencia disponible es esta (adquirida el 2026-11-17, con manifiestos de adquisición).
- **Insumos de PM2.5 (solo lectura)**: árbol
  `keneth-arias/airaware/data/processed/lima-procedencia-20261120` — `timeline/`,
  `windows-6/` y `splits-6/`, con SHA-256 verificados contra sus manifiestos antes de usarlos:

| Artefacto | SHA-256 | Versión del manifiesto |
| --- | --- | --- |
| `timeline/hours.parquet` | `2e8fa784cea645b8eb97b42f3fe36e6c532b5959cc8ae66da0ea416df513413c` | `senamhi-hourly-v1` |
| `windows-6/windows.parquet` | `fdbbe324f4674a176bc2b865adb191f8acee409719ccbf5bf8f240903782c862` | `senamhi-pm25-windows-v1` (historia 24 h, horizonte 6 h) |
| `splits-6/splits.parquet` | `a02e001795bf84985c087766ee46ea7acc53d86e5d2ed96b0974a5c6fd62502d` | `senamhi-pm25-splits-v1` (`validation_start` 2022-03-16T08:00Z, `test_start` 2023-02-25T18:00Z) |

La configuración `configs/weather-alignment.yaml` cubre exactamente las 7 identidades de
estación presentes en `splits-6` (conciliación previa a la corrida; sin estaciones faltantes
ni sobrantes).

| # | Comando (desde la raíz del worktree) | Resultado |
| --- | --- | --- |
| 1 | `uv run --locked airaware align weather --config configs/weather-alignment.yaml --data-dir data --output data/alignment/gfs-prevday1-union-real-20261120 --windows /home/shared/github/keneth-arias/airaware/data/processed/lima-procedencia-20261120/windows-6 --timeline /home/shared/github/keneth-arias/airaware/data/processed/lima-procedencia-20261120/timeline --splits /home/shared/github/keneth-arias/airaware/data/processed/lima-procedencia-20261120/splits-6` (bajo `nice -n 10`) | **exit 0**; inicio 2026-11-20T22:59:23Z, fin 2026-11-20T22:59:30Z |
| 2 | Misma corrida con `UV_OFFLINE=true` sobre salida nueva (`…-run2`) | **exit 0**; sin red |
| 3 | Comparación de corridas | `weather_rows.parquet`, `window_weather.parquet`, `windows_weather_summary.parquet` y `manifest.json` **byte a byte idénticos** (4/4) |

Salidas (bajo `data/alignment/gfs-prevday1-union-real-20261120/`, fuera de Git):
`weather_rows.parquet` `f742fa94da67e1e5fe7c884413770db6cb0e35f5e51c219eabaf95d13d031537`,
`window_weather.parquet` `cd33eb1f9fd2047711d7eec9f25889813f9317017573ac458f29a4ee4908608e`,
`windows_weather_summary.parquet` `3bb39f5531642dc84e1b1408c0cd6825a54fa187e38903ec6b88adb7d8dea641`,
`manifest.json` `565efed86bbc0c93642d06e2a2906ef4dfc3949dfe61823fc28d1d1f23ea1d68`.

## Conciliación de la unión real

- **Filas unidas**: 10 176 150 = 339 205 ventanas × 30 horas (historia 24 h + horizonte 6 h);
  **ninguna ventana descartada** (313 purgadas incluidas, con su `purge_reason`).
- **Estados de alineación**: `admissible` 35 280; `missing_weather` 10 140 870;
  `rejected_issue_unknown` / `rejected_issue_after_origin` / `rejected_available_after_origin`
  **0**.
- **Desglose de `admissible` por split**: train 33 663; purgadas 1 617;
  validation 0; test 0. La semana meteorológica (2022-03-09T00:00Z a 2022-03-15T23:00Z) es
  anterior a `validation_start`, de modo que esta variante aporta características solo a
  ventanas de `train`.
- **Verificación aritmética**: 35 280 = 168 marcas horarias × 30 ventanas que contienen cada
  marca × 7 estaciones; por estación son 5 040 filas admisibles con 168 horas distintas.
- **Ventanas elegibles por estado meteorológico** (`windows_weather_summary.parquet`,
  `split <> 'purged'`): `complete` 973, `partial` 259, `missing` 337 660 (total 338 892).
  Las 1 232 elegibles que tocan la semana son 139 `complete` + 37 `partial` por estación.

| Estación | Filas admisibles | Horas distintas | complete | partial | missing |
| --- | --- | --- | --- | --- | --- |
| CAMPO_DE_MARTE | 5 040 | 168 | 139 | 37 | 53 045 |
| CARABAYLLO | 5 040 | 168 | 139 | 37 | 42 723 |
| SANTA_ANITA | 5 040 | 168 | 139 | 37 | 47 254 |
| SAN_BORJA | 5 040 | 168 | 139 | 37 | 49 989 |
| SAN_JUAN_DE_LURIGANCHO | 5 040 | 168 | 139 | 37 | 59 596 |
| SAN_MARTIN_DE_PORRES | 5 040 | 168 | 139 | 37 | 41 874 |
| VILLA_MARIA_DEL_TRIUNFO | 5 040 | 168 | 139 | 37 | 43 179 |
| **Total** | **35 280** | 168 | **973** | **259** | **337 660** |

Las horas `partial` faltantes están en los bordes de la semana (historia anterior al
2022-03-09T00:00Z u objetivos posteriores al 2022-03-15T23:00Z, fuera de la cobertura fijada
por #16); quedan nulas y contadas, nunca imputadas.

## Evidencia de publicación por valor: retrospectivo vs operativo

Cada valor meteorológico conserva en la conversión y en la unión su emisión, su disponibilidad
y la huella del original:

| Campo por valor | Valor observado en esta corrida |
| --- | --- |
| `issued_at` (emisión) | `valid_at` − 24 h (rango 2022-03-08T00:00Z a 2022-03-14T23:00Z), regla `previous_day1_nominal_lead` |
| `available_at` (disponibilidad) | **nulo en los 1 176 valores** (el proveedor no documenta publicación por hora; política `undocumented_null`) |
| `acquired_at` (recuperación registrada) | 2026-11-17T23:41:47–49Z por paquete; procedencia local, nunca sustituye a `available_at` |
| `original_sha256` (huella del original) | 7 huellas distintas, una por paquete, propagadas fila por fila en la unión |
| Manifiesto de adquisición | SHA-256 por paquete registrado en `metadata/weather-union-real-20261120.json` (`recursos[].manifesto_adquisicion_sha256`) |

Clasificación honesta:

- **Experimento retrospectivo (acreditado)**: los 1 176 valores y sus 35 280 usos unidos.
  La emisión es nominal (adelanto fijo de 24 h); en las filas admisibles `issued_at` precede
  al origen de la ventana entre **18 y 47 horas** (mínimo 18 h en horas objetivo,
  máximo 47 h en historia).
- **Uso operativo (no acreditado)**: **0 valores**. No existe evidencia por valor de que el
  dato ya estaba publicado al emitir el pronóstico: `available_at` es nulo y `acquired_at` es
  de 2026, posterior a todos los orígenes (2022); usarlo como publicación rechazaría el 100 %
  de los valores, que es justo por qué el módulo mantiene ambos campos separados.

**Rechazo de un valor publicado después del origen — caso real**: no existe en estos datos.
Con emisión nominal de 24 h y horizonte de 6 h ningún valor puede emitirse después del origen,
y sin `available_at` del proveedor la cláusula `rejected_available_after_origin` no puede
activarse. El salvaguarda queda demostrado por las pruebas existentes del módulo, que cubren
los tres rechazos con casos construidos: `test_join_rejects_issue_after_origin_and_accepts_boundary_equality`,
`test_join_rejects_late_publication_with_earlier_valid_time` (con máscara de `value` y
metadatos íntegros en `test_join_masks_feature_value_of_late_issue_and_late_publication`) y
`test_join_fails_closed_when_issue_time_is_unknown`.

## Variante con meteorología frente a la referencia

El alcance del módulo acredita la **paridad sobre los mismos objetivos elegibles**, no métricas
de desempeño (el diseño no incluye entrenamiento; calcularlo sería código nuevo fuera de este
alcance). Salidas citadas del manifiesto de la corrida:

- `identical_window_id_set: true`; huellas del conjunto de `window_id` (total y elegible)
  iguales entre `splits.parquet` y el resumen unido (`d47f5064…` total, `b5027fd1…` elegible).
- `eligible_targets_sha256: 14871eb8a810b8403f5dd8aea0a8168df2dbfb14274b4739a0a9202091f8e899`:
  los objetivos elegibles de la referencia `pm25_only`
  (`configs/benchmark.yaml`, `comparison-v3`, SHA-256 `f2f71fb714f21b9de308fd1c07e0732a90a5cafcf6d5dcb07dfa6f49296dd66f`)
  y de la variante `pm25_gfs_previous_day1` son idénticos; la unión no reescribe objetivos.
- La variante añade sobre esos mismos objetivos 35 280 horas de característica meteorológica
  (973 ventanas `complete`, 259 `partial`, 337 660 `missing` con máscara explícita).

## Limitaciones

1. Uso operativo no acreditado por valor: sigue pendiente la hora de publicación del
   proveedor (mismo resto de la matriz de verificación).
2. La cobertura meteorológica fijada por #16 (una semana de 2022, dentro de `train`) limita el
   aporte de la variante a ventanas de entrenamiento; validation y test quedan sin clima.
3. Las celdas de grilla compartidas (4 celdas para 7 estaciones) no son observaciones
   independientes ni mediciones en la estación de aire; CRS SENAMHI sin declarar.
4. No se calcularon métricas de desempeño: la comparación citada es de paridad de objetivos,
   conforme al alcance del módulo.
