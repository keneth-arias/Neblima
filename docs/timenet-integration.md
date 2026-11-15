# Notas verificadas de integración con TimeNet

Revisión del 15/11/2026 sobre la copia sin cambios del commit
[`9bd1613019ee61fbc52e02106a1a45990ead7a54`](https://github.com/OpenTSLM/TimeNet/tree/9bd1613019ee61fbc52e02106a1a45990ead7a54).
El SHA local coincidió con HEAD remoto. Ambos paquetes declaran versión 0.12.0 y Python >=3.11;
las instrucciones de contribución prueban Python 3.11–3.13.
Se inspeccionó código: esto no constituye una validación de TimeF en ejecución.
El SDK y la herramienta de construcción aún no están instalados en AirAware.

## Contratos inspeccionados

Las rutas son relativas al repositorio externo en la revisión indicada.

| Componente | Contrato verificado | Ruta externa |
| --- | --- | --- |
| BaseConnector | `download(cache_dir: Path) -> list[TRaw]`, o variante asíncrona; `convert(raw_refs) -> TimeFDataset` no usa la red | `packages/timenet/src/timenet/connectors/base.py` |
| Composición | Redefinir `compose(raw_refs, context)` con padres declarados; acceso por `context.parents` e importación mediante `dataset.import_from` | El mismo archivo y `docs/connectors.md` |
| Conjunto de datos | `TimeFDataset(metadata=...)`; agregar con `add_record(record=...)` y `add_task(task=...)` | `packages/timenet/src/timenet/dataset/dataset.py` |
| Record y Source | Clases de datos con argumentos nombrados; Record contiene fuentes raíz y TimeOrigin; Source contiene fuentes hijas y señales | `dataset/record.py`, `dataset/source.py` dentro del paquete |
| Signal | Argumentos nombrados `spec`, `time_axis`, `name`, `data`; admite lectura diferida con `from_loader` | `dataset/time_series.py` |
| Tareas | ForecastingTask, ClassificationTask y AnswerTask heredan inputs, targets, prompt y split; clasificación usa etiquetas | `packages/timenet/src/timenet/types/tasks.py` |
| Almacenamiento | `dataset.write(path=..., values_backend=...)` usa el escritor oficial; `TimeFReader.open(version_dir)` permite leerlo | `docs/timef-writer.md`, `docs/timef-reader.md` |

El escritor genera manifest.json, control.duckdb y valores de señales en Parquet o Zarr.
El lector se usa como administrador de contexto. `TimeFReader.verify()` verifica las sumas de los
archivos. No crear un formato propio que imite TimeF. Las plantillas internas de observaciones no son TimeF.

## Datos faltantes, particiones y licencias

- `to_arrow` conserva valores nulos. `to_numpy` y el adaptador PyTorch rechazan nulos reales.
  Deben tratarse las máscaras y cualquier imputación causal justificada antes de convertir a tensores.
  Referencia: `docs/data-model/time-series.md` de la revisión fijada.
- Las particiones pertenecen a Task, no a Record. Un registro puede servir a varias particiones;
  nuestro constructor debe evitar que entradas y objetivos se compartan entre entrenamiento y prueba.
  No copiar la partición estratificada de TSQA para un problema cronológico de contaminación.
  Referencias: `docs/data-model/tasks.md` y `docs/connectors.md`.
- `compose` y los padres declarados permiten trazabilidad con versiones fijadas. Confirmar los nombres
  disponibles y el esquema de ficha al implementar el conector.
- El código de TimeNet usa MIT; los datos conservan sus propias licencias. El registro alojado exige
  acceso abierto del conjunto y sus antecesores. `NONE` no autoriza redistribución.
  Referencia: `docs/catalog/licensing.md`. La licencia de AirAware sigue pendiente.

## Ejemplos y controles

Se revisaron AGENTS.md, CONTRIBUTING.md, los pyproject de ambos paquetes, el conector y la ficha de
hello-world y la ficha y orientación de particiones de TSQA. Hello-world es sintético y no usa red.
TSQA muestra metadatos de tareas y fichas. La búsqueda de weather/climate/air-quality/meteorology en
las fichas no encontró un conector ambiental directamente reutilizable en esa revisión.
Esto no equivale a una búsqueda exhaustiva fuera del repositorio.

Para contribuir a TimeNet, seguir sus dependencias por conector y comandos: `make check`,
`make lint-fix`, `make test`, `make test-connectors` y controles de licencia.
No confundirlos con los de AirAware, documentados en CONTRIBUTING.md.

Quedan #21–#23: conector de fuente, escritura y lectura de una muestra, nombres disponibles,
tratamiento de nulos antes de tensores y carga con el SDK estándar. Aún no hay datos recolectados.

## Requisitos del hackathon

La [página oficial](https://challenge.timenet.ai/), revisada el 15/11/2026, exige incorporar un conjunto
a TimeNet, entrenar o ajustar un modelo temporal, preparar una presentación y entregar los enlaces
de `docs/hackathon.md`. Cada persona debe registrarse. Revisar las reglas y el plazo antes de enviar;
estas notas no constituyen una entrega.
