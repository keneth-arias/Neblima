# Cohortes para comparar dos objetivos de ajuste directo

El [protocolo de Lima](../../configs/training/lima-directo-cohortes-v1.json) fija el manifiesto del entrenamiento histórico, los cortes horarios en tiempo universal coordinado (UTC) y las huellas de los identificadores. Los dos ajustes parten del mismo modelo base. Las ventanas de confirmación ya participaron en entrenamientos históricos. Se revisaron las curvas de entrenamiento y los resultados finales de selección de cuatro ajustes históricos. Para escoger los cortes nuevos se revisaron identificadores, fechas y cobertura por estación. La confirmación se reserva para comparar los nuevos checkpoints congelados.

Desde la raíz de AirAware, generar una entrega en una carpeta local nueva. El primer argumento apunta a la carpeta que contiene el manifiesto histórico y `train/`.

```sh
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/direct_cohorts.py "$bloques" "$salida"
```

| Salida | Uso | Ventanas |
| --- | --- | ---: |
| `trainer/fit/` | Ajuste y muestra fija para la curva | 225 338 |
| `trainer/inner_validation/` | Evaluación periódica y selección del paso | 6 664 |
| `scorer/confirmation/` | Comparación posterior entre checkpoints congelados | 5 163 |
| `purged.json` | Ventanas con seis objetivos completos que cruzan un corte | 232 |

Cada ventana usa las horas del origen −23 al origen +6, ambas inclusive. El archivo histórico de ajuste solo incluye ventanas con seis objetivos completos. Para cada una, el exportador busca su identificador en el índice y recupera su estación y hora de origen. El índice puede incluir ventanas adicionales. El protocolo comprueba el conteo y la huella de cada rol. Calcula el percentil 95 de cada estación con horas únicas de las historias de ajuste. `graph_sample` identifica las 6 664 filas de ajuste elegidas por el orden de la huella de cada ID. La huella de pertenencia ordena los identificadores como texto UTF-8 y añade un salto de línea después de cada uno.

Cada carpeta de rol contiene `data.npz`, `thresholds.json` y `manifest.json`. El esquema `forecast-direct-cohort-v1` vincula el rol, las unidades, los pesos base, la procedencia, los archivos y el protocolo. El manifiesto raíz registra las huellas de los tres manifiestos y del archivo de ventanas purgadas. El consumidor debe verificar la huella esperada y el rol antes de abrir los datos. El entrenamiento recibe únicamente las dos carpetas de `trainer/`. La confirmación corresponde al proceso de puntuación y necesita permisos de almacenamiento separados.

Los archivos con mediciones permanecen en almacenamiento local. Una transferencia requiere verificar los derechos de uso aplicables y el acceso efectivo del destinatario.

## Confirmación de los cuatro checkpoints

Antes de abrir la confirmación, guardar en un registro independiente la huella SHA-256 de la selección. El archivo JSON de selección lleva `schema: direct-confirmation-selection-v1`, `confirmation_manifest_sha256` (la huella que registró el exportador para este rol) y `checkpoints`. Este último objeto contiene las claves `"27"` y `"28"`. Cada semilla tiene dos claves, `normalized-mse` (control) y `physical-mae` (candidato). El valor de cada una es la huella de `manifest.json` de la generación **seleccionada** de ese brazo. Contrastarlas con los recibos de selección antes de congelar el archivo.

Al abrir la cohorte para la única comparación prevista, el responsable de puntuación prepara un solo `history.npz` con `window_id` e `history`. Los cuatro trabajos de inferencia directa reciben ese mismo archivo con `--require-history-only`. Conservar la huella del insumo entregado a cada trabajo y la huella que emite OpenTSLM para su salida. En la carpeta privada del inventario se guardan `history.npz` y las cuatro salidas `<semilla>-<objetivo>.npz`. El JSON del inventario lleva `schema: direct-confirmation-predictions-v1` y `arms`, con la misma estructura de semillas y objetivos. Cada brazo registra `history_sha256` y `output_sha256` de la ejecución. La huella del inventario se registra al cerrar las cuatro inferencias. El archivo directo de OpenTSLM contiene la identidad del checkpoint y los horizontes; la procedencia de la historia depende del registro independiente de ejecución.

```sh
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/direct_confirmation.py \
  "$seleccion" "$inventario" "$salida/scorer/confirmation" "$informe" \
  --selection-sha256 "$huella_seleccion" --inventory-sha256 "$huella_inventario"
```

El informe compara el error absoluto medio (MAE, µg/m³) de ambos objetivos y de persistencia sobre las mismas ventanas a una, dos, tres, cuatro, cinco y seis horas. La persistencia repite la última medición de la historia. Una observación alta alcanza o supera el umbral de ajuste de su estación. Dos pronósticos de la misma estación y hora contribuyen dos errores y una sola hora de soporte.

La mejora es el MAE del control menos el del candidato, promediada con igual peso por semilla. El bloque principal agrupa la **hora objetivo UTC** desde la época Unix por división entera entre 168. Con al menos cuatro bloques con observaciones altas, se remuestrean todos los bloques observados con reemplazo, usando los mismos bloques para las dos semillas, objetivos y estaciones. En cada réplica se ponderan los errores por número de pares. Con el generador de NumPy y semilla 27 se conservan 2000 réplicas con pares altos; el informe cuenta los descartes y calcula los percentiles lineales 2,5 y 97,5. También informa la sensibilidad a bloques de 84 y 336 horas.

Con soporte semanal insuficiente, el resultado es `inconclusive`. Con soporte suficiente, se conserva el control si la mejora en horas altas es nula o negativa, o aumenta el MAE global. Se avanza a calibración si la mejora en horas altas tiene límite inferior estrictamente positivo y se cumple el criterio global. Si la mejora observada es positiva y el intervalo incluye cero, el resultado es inconcluso. La decisión usa solo el bloque de 168 horas. Conservar el informe y las dos huellas bajo el control de acceso del evaluador y cerrar la confirmación para este experimento. La elegibilidad de un paquete requiere evaluar por separado la calibración, la selección histórica y la capacidad lingüística de ambos checkpoints.
