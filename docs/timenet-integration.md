# Integración con TimeNet: revisión de código completada

Revisión documental ejecutada el 15/11/2026 para la tarea #1. Commit inspeccionado:
[`9bd1613019ee61fbc52e02106a1a45990ead7a54`](https://github.com/OpenTSLM/TimeNet/tree/9bd1613019ee61fbc52e02106a1a45990ead7a54).
La copia externa está limpia; `git rev-parse HEAD` y `git ls-remote origin HEAD` coincidieron.
La copia externa no se modificó. La suite de TimeNet no se ejecutó. La verificación sintética
posterior usa un entorno independiente y se registra al final de este documento.
Las pruebas enlazadas se **leyeron**, no se presentan como ejecuciones.

## Versiones y reglas confirmadas

| Elemento | Resultado | Evidencia fijada |
| --- | --- | --- |
| timenet | 0.12.0, Python >=3.11 declarado | [packages/timenet/pyproject.toml](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/pyproject.toml#L1) |
| timenet-connectors | 0.12.0, Python >=3.11 declarado | [packages/timenet-connectors/pyproject.toml](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/pyproject.toml#L1) |
| Reglas de contribución | Python 3.11–3.13 probados por upstream; dependencias aisladas por conector | [CONTRIBUTING.md](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/CONTRIBUTING.md#L1) |
| Reglas para agentes | Usar uv, revisar código si contradice docs, no reparar datos de forma sintética | [AGENTS.md](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/AGENTS.md#L1) |
| Licencia del código externo | MIT; las contribuciones recibidas usan MIT | [LICENSE](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/LICENSE#L1) y [CONTRIBUTING.md](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/CONTRIBUTING.md#L1) |

Para una futura contribución externa: `make check`, `make lint-fix`, `make test`, `make test-connectors`
y `make license-check`; `make check-ci` y `make test-unit` reproducen controles rápidos.
Estos comandos pertenecen a TimeNet. Neblima usa sus propios controles de CONTRIBUTING.md.
La selección de Python 3.13.13 local y compatibilidad de 3.11 no necesita cambiar.
OpenTSLM mantiene su revisión anotada, pero su adaptador y compatibilidad se estudian en #27.

## Matriz de API, invariantes y consecuencias

Las firmas abreviadas con puntos suspensivos no enumeran todos los argumentos opcionales; el enlace
al código es la referencia completa. Las columnas de pruebas indican evidencia inspeccionada.

| Elemento | Contrato o invariante observado | Definición en el commit | Prueba de referencia leída | Consecuencia para Neblima |
| --- | --- | --- | --- | --- |
| BaseConnector: descarga | `download(cache_dir: Path) -> list[TRaw]`; alternativa `download_async`. Devuelve referencias y es idempotente; no interpreta las observaciones. | [BaseConnector.download](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/connectors/base.py#L89) | [test_async_connector_download_bridges_to_download_async](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/connectors/test_base.py#L57) | Separar adquisición y conversión; implementar una variante de descarga. |
| BaseConnector: conversión | `convert(raw_refs: list[TRaw]) -> TimeFDataset`. Implementar convert o compose; sin red en conversión. | [BaseConnector.convert](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/connectors/base.py#L144) | [test_connector_without_convert_or_compose_fails_at_construction](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/connectors/test_base.py#L10) | El conector no debe descargar dentro de convert. |
| Ficha y composición | `compose(raw_refs, context) -> TimeFDataset`; por defecto llama convert. metadata lee dataset.yaml; los padres declarados requieren compose. | [BaseConnector.compose](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/connectors/base.py#L125) | [test_build_prepares_parents_before_the_isolated_child](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/tests/test_build_plan.py#L540) | Usar lectores de context.parents, sin invocar conectores ajenos directamente. |
| TimeFDataset | `TimeFDataset(*, metadata: DatasetMetadata)`; add_record(record=...) y add_task(task=...). | [TimeFDataset.__init__](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/dataset/dataset.py#L75) | [test_get_split_accessors_select_tasks_by_split](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/dataset/test_dataset.py#L924) | No suponer un constructor basado en listas de filas ni particiones en Record. |
| Record y Source | Source exige name; contiene sources, signals, annotations y metadata. Record usa sources, start_time y metadatos. | [Source](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/dataset/source.py#L40) | [test_record_rejects_source_reused_under_two_parents](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/dataset/test_source.py#L35) | Mantener jerarquía y propiedad única; no reutilizar la misma fuente bajo dos padres. |
| Señales y lectura diferida | `from_loader(*, spec, time_axis, name, loader, n_values, null_count=None, ...)`. La llamada no lee los valores. | [Signal.from_loader](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/dataset/time_series.py#L287) | [test_loader_is_lazy](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/dataset/test_time_series.py#L67) | Adjuntar lectores acotados de Arrow y n_values correcto; no materializar todo el conjunto. |
| Ejes temporales | RegularAxis usa period_us: Fraction; IrregularAxis declara first_us/last_us y la señal conserva los desfases. | [RegularAxis](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/dataset/axis.py#L62) | [test_from_rate_hz_is_exact](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/dataset/test_axis.py#L30) | Respetar frecuencia y origen; no copiar OrdinalAxis de TSQA para fechas físicas. |
| Pronóstico y respuesta | ForecastingTask y AnswerTask heredan inputs, targets, prompt y split de Task. None y objetivo vacío no son equivalentes. | [ForecastingTask](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/types/tasks.py#L485) | [test_none_and_an_explicit_empty_target_remain_distinct](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/types/test_tasks.py#L73) | El horizonte y la historia se expresan con ventanas/objetivos; no inventar parámetros horizon/lookback. |
| Clasificación | `label_set: LabelSet` es obligatorio. Las etiquetas objetivo se comprueban contra ese conjunto. | [ClassificationTask](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/types/tasks.py#L374) | [test_a_classification_task_requires_a_label_set](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/types/test_label_sets.py#L25) | Definir etiquetas explícitas antes de crear tareas de episodios. |
| Datos nulos | to_arrow conserva nulos; to_numpy lanza TimeFNullValuesError, subclase de TimeFValidationError. Declarar missing no imputa valores. | [Signal.to_numpy](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/dataset/time_series.py#L573) | [test_to_numpy_points_null_values_to_arrow](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/dataset/test_time_series.py#L529) | Conservar máscaras y preparar entradas explícitamente antes de NumPy/PyTorch; objetivos medidos completos. |
| Particiones | split pertenece a Task. La selección por partición no valida la separación temporal de nuestras ventanas. | [Task](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/types/tasks.py#L139) | [test_get_split_rejects_a_dataset_that_assigns_no_splits](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/dataset/test_dataset.py#L940) | Neblima debe probar límites, purgas, duplicados y disponibilidad temporal en #19. |
| Padres y trazabilidad | `import_from(parent, *, alias=None, records=(), signals=(), tasks=(), load=LoadPlan.ALL_LAZY)`. El padre debe estar declarado; las copias no modifican el padre. | [TimeFDataset.import_from](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/dataset/dataset.py#L106) | [test_reimporting_a_whole_record_changes_nothing_and_keeps_child_edits](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/dataset/test_composition.py#L562) | Fijar versiones y mantener las dependencias de archivos reutilizados; no publicar un hijo aislado de sus padres. |
| Escritor y lector | `write(*, path, values_backend=ValuesBackend.PARQUET) -> Path`; lector `TimeFReader.open(path, *, sources_root=None)` y verify(). | [TimeFDataset.write](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/dataset/dataset.py#L308) | [test_verify_accepts_an_intact_dataset_and_detects_a_changed_artifact](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/reader/test_reader.py#L565) | Escribir con herramientas oficiales, leer y verificar hashes en #21–#23. |
| Acceso y publicación | La construcción admite open_access_only; las restricciones de fuente y padres no se eliminan por convertir a TimeF. | [build](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/producer.py#L24) | [test_open_access_only_refuses_a_gated_parent_before_any_step](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/tests/test_producer.py#L127) | Revisar la licencia de cada fuente y antecesor antes de redistribuir. |

Además de las filas anteriores se inspeccionaron [Record](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/dataset/record.py#L21),
[Signal.__init__](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/dataset/time_series.py#L263), [AnswerTask](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/types/tasks.py#L436),
[IrregularAxis](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/dataset/axis.py#L266), [TimeFReader.open](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/reader/reader.py#L118),
[TimeFReader.verify](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/reader/reader.py#L191) y [TimeFNullValuesError](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/errors.py#L211).
El tratamiento PyTorch debe evitar nulos reales; no basta con declarar metadatos de faltantes.
El detalle está en [docs/data-model/time-series.md](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/docs/data-model/time-series.md#L1) y [packages/timenet/src/timenet/torch.py](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/torch.py#L1) del adaptador externo.

El formato contiene manifest.json y control.duckdb con valores Parquet/Zarr. La carga de una muestra
real de Neblima y su reproducibilidad siguen pendientes de #21–#23.
No se detectó contradicción en los contratos aquí contrastados entre el código fijado y sus docs.
Esto no afirma que toda la documentación pública corresponda siempre a ese commit.

## Ejemplos revisados y reutilización

**Hello-world:** [packages/timenet-connectors/src/timenet_connectors/datasets/timenet/hello_world/connector.py](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/src/timenet_connectors/datasets/timenet/hello_world/connector.py#L1), [packages/timenet-connectors/src/timenet_connectors/datasets/timenet/hello_world/dataset.yaml](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/src/timenet_connectors/datasets/timenet/hello_world/dataset.yaml#L1) y [packages/timenet-connectors/src/timenet_connectors/datasets/timenet/hello_world/tests/test_connector.py](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/src/timenet_connectors/datasets/timenet/hello_world/tests/test_connector.py#L1).

**TSQA:** [packages/timenet-connectors/src/timenet_connectors/datasets/chengsenwang/tsqa/connector.py](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/src/timenet_connectors/datasets/chengsenwang/tsqa/connector.py#L1), [packages/timenet-connectors/src/timenet_connectors/datasets/chengsenwang/tsqa/dataset.yaml](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/src/timenet_connectors/datasets/chengsenwang/tsqa/dataset.yaml#L1) y [packages/timenet-connectors/src/timenet_connectors/datasets/chengsenwang/tsqa/tests/test_connector.py](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/src/timenet_connectors/datasets/chengsenwang/tsqa/tests/test_connector.py#L1).

| Ejemplo | Qué reutilizar | Qué no copiar |
| --- | --- | --- |
| Hello-world 1.0.0, CC-BY-4.0 según su ficha | Conector sin red, construcción determinista, jerarquías y anotaciones; pruebas test_download_is_deterministic_and_offline y test_convert_is_deterministic | Sus señales sintéticas no son observaciones ambientales ni validan cobertura de Lima |
| TSQA 1.2.0, Apache-2.0 según su ficha | Revisión de fuente fijada, lector Parquet con validación de filas, AnswerTask y comprobaciones de ida/vuelta | Usa OrdinalAxis y partición estratificada agrupada 80/10/10 con semilla 42; no sirve como separación temporal de Lima |

TSQA prueba repetibilidad, aislamiento de series y conservación de split al guardar, incluyendo
`test_generated_splits_balance_categories_and_keep_signals_together`,
`test_split_assignments_are_repeatable` y `test_splits_survive_storage_round_trip`.
No confundir chengsenwang/tsqa con tsaqa/tsaqa_benchmark.

### Búsqueda ambiental acotada

Se buscaron `weather|climate|air.?quality|meteorolog|pollution|senamhi|oefa` sin distinguir mayúsculas en 12 fichas dataset.yaml y
12 archivos connector.py bajo `packages/timenet-connectors/src/timenet_connectors/datasets/`.
Coincidencias: 0. No se encontró un conector ambiental directamente reutilizable en ese
alcance y revisión; no es una conclusión sobre repositorios externos ni sobre texto no examinado.

Hay utilidades genéricas de descarga: [download_http](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/src/timenet_connectors/download/http.py#L66) y
[is_cached](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/src/timenet_connectors/download/http.py#L46). Son candidatas para evaluar en #6, no una decisión de
acoplar Neblima a timenet-connectors. En particular, is_cached acepta un archivo existente cuando
no hay hash esperado: Neblima aún debe registrar su SHA-256 calculado y validar contenido y manifiesto.
No se ha verificado aquí que estas utilidades cubran reanudación, todos los límites o todo el contrato #6/#7.

## Licencias y decisiones

La licencia del software TimeNet no concede derechos sobre SENAMHI, OEFA u otras fuentes.
La ficha admite SPDX y los casos OTHER/NONE; OTHER requiere URL y NONE no significa permiso.
La redistribución debe respetar la fuente y, para el registro alojado, el acceso abierto del conjunto
y todos sus antecesores. Evidencia: [docs/catalog/licensing.md](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/docs/catalog/licensing.md#L1).

Se mantiene la revisión fijada y la separación adquisición/conversión ya aprobadas. No se introducen
servicios, bibliotecas pesadas, un formato TimeF propio ni particiones aleatorias.
La granularidad definitiva de registros, el esquema de observaciones y el presupuesto de entrenamiento
se decidirán con datos reales en #12/#27/#28. No hacen falta para cerrar esta investigación.
Keneth eligió AGPL-3.0-only para el código propio. No cambia los permisos de ninguna fuente.
Una contribución a TimeNet bajo MIT debe tener autoría y permiso adecuados por separado; este
repositorio no concede una excepción ni licencia dual. Ver [ADR-003](decisions/003-licencia-agpl-v3.md).

## Qué se verificó y qué falta ejecutar

Ejecutado: consultas Git de revisión/estado, extracción de definiciones y firmas por AST, búsqueda
acotada de fichas/conectores e inspección manual de código, pruebas, licencias y reglas.
No ejecutado: suite de tests de TimeNet, descargas de proveedores ni escritura/lectura de un conjunto
ambiental de Neblima. El ejemplo sintético sí se construyó y leyó en la verificación posterior.
Las 31 pruebas propias de Neblima son controles separados de esas verificaciones.

## Actualización: verificación sintética en ejecución

Después de integrar #40 se instaló la revisión fijada en el entorno independiente
[tools/timenet-smoke](../tools/timenet-smoke/README.md). Se ejecutó el constructor oficial de
timenet/hello-world@1.0.0, TimeFReader.verify(), lectura y carga con SDK desde un registro local.
Se compararon valores y commits instalados. Resultado: tres registros, cinco señales, cinco tareas
y 4 478 280 bytes, bajo CC-BY-4.0. Informe local: data/timef/hello-world-validation.json.
Esta ejecución posterior amplía la inspección anterior: la suite de tests de TimeNet sigue sin
ejecutarse y el conector/datos reales de SENAMHI siguen pendientes en #21–#23.
