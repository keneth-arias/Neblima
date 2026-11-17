# ADR-006: PyArrow para el escritor Parquet incremental de #13

## Estado y fecha

Aceptada el 17/11/2026 dentro de la entrega 2 de #13. Ref: #13; complementa ADR-004, que sigue
gobernando el perfilamiento con DuckDB y no se modifica. Verificada contra documentación oficial
de la versión aplicable mediante Lightpanda según `docs/web-access.md`.

## Contexto

La entrega 2 de #13 necesita una salida Parquet que consuma los lotes del lector aprobado de forma
incremental, sin materializar la entrada completa, con esquema físico explícito para los campos
anidados del contrato (`raw_fields`, `time_raw`, `semantic_evidence`, `parent_ids`, `provenance`),
particionado por `source_id/año/mes` de `observed_at` UTC, publicable atómicamente en una carpeta
nueva y con bytes reproducibles en el entorno fijado. DuckDB 1.5.6 ya está fijada por ADR-004;
añadir PyArrow solo se justifica si su escritor incremental y control de esquema son necesarios.

## Decisión

Añadir `pyarrow>=25,<26` como dependencia directa, fijada por uv.lock a **25.0.1**, y usarla
exclusivamente como escritor/lector físico Parquet de #13. La conversión contractual, la política
y la numeración de registros siguen en el código aprobado de la entrega 1; PyArrow no participa en
la semántica de los datos. Se elige 25.0.1 porque es la última serie con documentación oficial
versionada publicada (`arrow.apache.org/docs/25.0/`): la serie 26 no tiene documentos versionados
publicados (`/docs/26.0/` responde 404; solo existe `dev`) y los puntos de API usados deben
verificarse contra la versión aplicable. Los wheels registrados por uv.lock para 25.0.1 cubren
CPython 3.11 y 3.13, las dos versiones que verifica CI.

Elecciones fijas de escritura: todas adoptan los valores por defecto documentados de la versión
fijada; el código construye `ParquetWriter(where, schema)` sin redeclarar opciones, de modo que
estos valores quedan anclados a la versión fijada en `uv.lock`:

- `ParquetWriter(where, schema)` por partición: escritura incremental, un `write_table` por lote;
  cada llamada produce un row group, de modo que la memoria queda acotada por lote.
- `version="2.6"` (por defecto), `compression="snappy"` (por defecto), `write_statistics=True`,
  `store_schema=True` (conserva `ARROW:schema` y permite reconstruir el esquema Arrow al leer),
  `write_page_index=False`, `write_page_checksum=False`. `ParquetWriter.write_table(table,
  row_group_size=None)` escribe la tabla completa de la llamada como un row group.
- Los instantes usan `pa.timestamp("us", tz="UTC")`; con `version="2.6"` se escriben sin pérdida
  de resolución y la lectura devuelve `datetime` con zona.
- `raw_fields` y `time_raw` se mapean a `map<string, string>` con ítems nulos
  (`pa.map_(pa.string(), pa.string())`, `keys_sorted=False`), conservando el orden de inserción;
  `semantic_evidence` y `parent_ids` a `list<string>` no nula con ítems no nulos; `provenance` a
  `struct<source_id: string, sha256: string, record: int64, sheet: string>` con nulabilidad según
  el contrato. El orden de columnas replica la declaración de `Observation`.
- Las observaciones se escriben en el orden de consumo de los lotes (número de registro, luego
  PM10, PM2_5, NO2); un único archivo `part-00000.parquet` por partición;
  rutas `source_id=<valor>/year=<YYYY>/month=<MM>`, con año y mes derivados de `observed_at` en UTC.
- Rechazos: `rejections.jsonl` en la raíz de la carpeta de salida, una línea por rechazo en orden
  de consumo, `json.dumps(model_dump(mode="json"), ensure_ascii=False)` más `\n`; sin valores
  flotantes, por lo que la serialización es byte a byte estable.
- Manifiesto `manifest.json`: JSON canónico (`sort_keys=True`, `indent=2`, `ensure_ascii=False`,
  terminado en `\n`) con ID y SHA de fuente y política (SHA-256 de `model_dump_json()` canónico de
  la política), SHA de entrada, biblioteca y versión, conteos de filas de entrada, observaciones y
  rechazos (totales, por señal y por clase `value_status`), y lista de archivos de salida con
  SHA-256, filas y número de rechazos. No contiene marcas de tiempo ni rutas absolutas.

Publicación atómica: se escribe en una carpeta temporal hermana nueva creada con
`tempfile.mkdtemp`; al cerrar se valida legibilidad, conteos por archivo y reconciliación
(3 resultados por fila), y solo entonces se renombra al destino con `os.rename` después de
comprobar que el destino no existe. La validación fallida o una excepción elimina únicamente la
carpeta temporal creada por esta ejecución; la salida existente y el original nunca se tocan.

## Alternativas

- **DuckDB 1.5.6 (ya fijada):** su salida Parquet se produce con `COPY TO` a partir de una
  consulta/tabla en el momento de la sentencia; `PARTITION_BY`, `PER_THREAD_OUTPUT`, `APPEND` y
  `FILE_SIZE_BYTES` son opciones de esa escritura y no un escritor incremental por lotes. Para
  alimentarla desde los lotes Python aprobados habría que insertar antes toda la entrada en una
  tabla (materialización que R1 excluye) o registrar objetos Arrow (lo que requiere PyArrow de
  todos modos). DuckDB queda para perfilamiento según ADR-004; no se duplica.
- **PyArrow 26.x:** sin documentación oficial versionada publicada al momento de la decisión;
  el punto de API debería verificarse contra `dev`, que puede cambiar.
- **Escritor propio del formato Parquet:** riesgo y esfuerzo desproporcionados; el formato exige
  codificación de columnas, estadísticas y metadatos que la biblioteca ya verifica.

## Verificación documental (Lightpanda, 17/11/2026 UTC)

| URL solicitada | URL final | HTTP | Resultado |
| --- | --- | --- | --- |
| `https://arrow.apache.org/docs/26.0/python/generated/pyarrow.parquet.ParquetWriter.html` | igual | 404 | No existe la serie 26 versionada; motivó elegir 25.0 |
| `https://arrow.apache.org/docs/25.0/python/generated/pyarrow.parquet.ParquetWriter.html` | igual | 200 | «Class for incrementally building a Parquet file for Arrow tables»; firma con `version='2.6'`, `compression='snappy'`, `write_statistics=True`, `store_schema=True`; `write_table(table, row_group_size=None)`; `close()` |
| `https://arrow.apache.org/docs/25.0/python/generated/pyarrow.parquet.ParquetFile.html` | igual | 200 | Lectura de vuelta (`ParquetFile(source, ...)`, `read`, row groups) para validación |
| `https://arrow.apache.org/docs/25.0/python/generated/pyarrow.map_.html` | igual | 200 | `pa.map_(key_type, item_type, keys_sorted=False)` para `raw_fields`/`time_raw` |
| `https://arrow.apache.org/docs/25.0/python/generated/pyarrow.RecordBatch.html` | igual | 200 | Construcción por lote (`from_pylist`/`record_batch`) |
| `https://arrow.apache.org/docs/25.0/python/generated/pyarrow.timestamp.html` | igual | 200 | `pa.timestamp(unit, tz)`; se usa `('us', 'UTC')` |
| `https://duckdb.org/docs/stable/sql/statements/copy` | `https://duckdb.org/docs/2.0/sql/statements/copy.html` | 200 | `COPY TO` Parquet desde consulta; `APPEND` solo regenera nombres de archivo en escrituras multifile; sin escritor incremental de row groups |

Un intento de consulta simultánea de tres páginas devolvió salida vacía (fallo de transporte
transitorio); se reintentó una única vez de forma secuencial y todas las páginas respondieron 200.

## Consecuencias

- Dependencia binaria adicional (ruedas cp311 y cp313 verificadas en la resolución de uv para
  `requires-python = ">=3.11,<3.14"`); pip-audit la incluye en `make audit`.
- La determinismo binario se afirma **solo** para bytes de entrada, política, configuración,
  tamaño de lote y versión de PyArrow idénticos en el entorno fijado: la cabecera `created_by` del
  archivo incluye la versión de parquet-cpp-arrow, estable dentro de la versión fijada; el formato
  Parquet no registra marcas de tiempo de escritura. La reproducibilidad entre versiones distintas
  de PyArrow no se afirma sin evidencia.
- El manifiesto registra la versión usada; la reconstrucción requiere esa versión para garantizar
  lectura idéntica de los campos anidados (mapas ordenados por inserción, listas, struct).
- Los archivos Parquet, el JSONL de rechazos y el manifiesto generados en pruebas permanecen en
  `tmp_path` y no se incorporan a Git.
