# Ejecución de normalización SENAMHI (#13, entrega 3) — 17/11/2026

Implementación y ejecución real de `airaware normalize senamhi` sobre el original identificado,
con reconciliación independiente. Registro máquina completo: metadata/senamhi-normalization-run.json.
Rama `feat/issue-13-senamhi-normalization`, HEAD `a8ca7f7`. Responsable de la ejecución:
Cristopher (@qriqs); decisiones de contrato y política: Keneth (@keneth-arias).

## Alcance de código (entrega 3)

- `src/airaware/normalization/cli.py`: subcomando `airaware normalize senamhi` mínimo que acepta
  `--input`, `--policy`, `--output` y `--batch-size` (positivo, 500 por defecto), reutiliza la ruta
  aprobada `load_policy` → `stream_observations` (que verifica el SHA antes de convertir) →
  `write_parquet_output` (carpeta nueva, publicación atómica), imprime un resumen JSON conciso con
  conteos y ruta del manifiesto, y devuelve errores claros con código distinto de cero sin volcar
  observaciones. Registro mínimo en `src/airaware/cli.py`.
- `tests/test_senamhi_cli.py`: 8 pruebas sintéticas (éxito con salida resumida, SHA distinto,
  salida existente sin sobrescribir, tamaño de lote inválido, entrada ausente, política ausente,
  comando registrado en la CLI pública con ayuda en español). Sin red ni datos reales.
- No se modificaron el lector, el convertidor, el escritor Parquet, las pruebas aprobadas de las
  entregas 1–2, la política ni el plan.

## Adquisición acotada del original

El original estaba ausente en esta copia. Se obtuvo **una sola vez** el recurso documentado en
metadata/senamhi-lima-download.json con Lightpanda (`lightpanda mcp`, herramienta `download` de
la versión 1.1.0-nightly.12173), tras abrir la página oficial del catálogo:

- Página del catálogo: HTTP 200, 17/11/2026 (~18:27 UTC).
- CSV solicitado: la URL exacta documentada; la herramienta no expuso el código HTTP del archivo
  (solo conserva respuestas 200–203); se registra `null` con esa razón.
- Verificado al terminar la descarga (18:28:40 UTC): archivo regular, **68 501 558 bytes** y
  SHA-256 `896ae8a1…5c40d4`, iguales a los esperados. Un intento, cero reintentos, dentro del
  techo autorizado de 70 000 000 bytes y un solo archivo.
- Registro documentado con el fluido de adquisición: `airaware acquire import-file`
  (`reused=true`), manifiesto en
  `data/raw/senamhi-lima-csv/896ae8a106…/manifest.json` y solicitud en
  `data/staging/senamhi-acquisition-request.json`. Nada de esto entra a Git.

## Ejecución única real

```bash
sha256sum data/raw/senamhi/senamhi_lima_monitoreo_1.csv   # R1, antes: 896ae8a1…5c40d4
uv run --locked airaware normalize senamhi \
  --input data/raw/senamhi/senamhi_lima_monitoreo_1.csv \
  --policy configs/normalization/senamhi.yaml \
  --output data/normalized/senamhi/senamhi-normalization-20261117-v1 \
  --batch-size 5000                                        # exit 0, 18:29:38–18:30:16 UTC, ~38 s
sha256sum data/raw/senamhi/senamhi_lima_monitoreo_1.csv   # R2, después: mismo SHA, mismo inodo/mtime/tamaño
```

Resumen del comando: `input_rows: 577 794`, `observations: 1 733 382`, `rejections: 0`.

## Reconciliación independiente (R4/R5)

Relectura directa de los 113 Parquet publicados —no de los contadores del manifiesto— con
PyArrow 25.0.1. Todos los valores coinciden con la prevalidación del contrato:

| Señal | Valores finitos | Valores ausentes | Otras clases |
| --- | ---: | ---: | ---: |
| PM10 | 380 982 | 196 812 | 0 |
| PM2.5 | 367 591 | 210 203 | 0 |
| NO2 | 299 192 | 278 602 | 0 |

- Total leído: **1 733 382** filas en Parquet (3 × 577 794), con repeticiones conservadas en
  linaje; `rejections.jsonl` con 0 líneas.
- Particiones `source_id=senamhi-lima-csv/year=AAAA/month=MM` en **UTC** de `observed_at`,
  2015-01 a 2024-05: 0 filas fuera de su partición (verificación completa, no muestreada).
- SHA-256 de cada archivo Parquet y de `rejections.jsonl` contra disco: coinciden con el
  manifiesto; filas por archivo y suma total (1 733 382) coinciden; rutas relativas;
  `policy_id`, `source_id`, `policy_sha256`, `input_sha256` y `library_version` verificados.
- Contrato `Observation` validado con Pydantic sobre una **muestra acotada de 200 filas** leídas
  de vuelta; no se afirma validación contractual Pydantic de las 1 733 382.

## Salida retenida (fuera de Git)

`data/normalized/senamhi/senamhi-normalization-20261117-v1/`: 115 archivos (113 Parquet +
`manifest.json` + `rejections.jsonl` vacío), 72 739 669 bytes en total, SHA del manifiesto
`fcb42760…ad32fb`. La carpeta es nueva; no se sobrescribió ninguna salida previa.

## Verificación completa y límites

- Pruebas enfocadas: `tests/test_senamhi_cli.py`, `tests/test_senamhi_normalization.py`,
  `tests/test_senamhi_parquet.py`, `tests/test_senamhi_preparation.py`,
  `tests/test_observation_schema.py`, `tests/test_cli.py` — 85 aprobadas.
- `make check`, `make build` y `make audit` aprobados después de todos los cambios de código
  (ver detalle exacto en metadata/senamhi-normalization-run.json y en el reporte de intento).
- Límites: ejecución única (sin segundas corridas); calidad individual y posición del intervalo
  siguen desconocidas (#43); identidad de estaciones sigue en #14; `station_id`/`sensor_id`
  nulos por diseño; esta salida no resuelve elegibilidad de #11 ni etiquetas normativas.
- Sin publicación externa. Cualquier distribución futura de la base o sus derivados debe
  acompañar [DATA_ATTRIBUTION.md](../DATA_ATTRIBUTION.md) (licencia ODC-BY-1.0 del conjunto);
  la licencia del código propio sigue siendo AGPL-3.0-only.
