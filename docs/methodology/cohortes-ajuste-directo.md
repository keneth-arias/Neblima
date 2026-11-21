# Cohortes para comparar dos objetivos de ajuste directo

El [protocolo de Lima](../../configs/training/lima-directo-cohortes-v1.json) fija el manifiesto del entrenamiento histórico, los cortes horarios en tiempo universal coordinado (UTC) y las huellas de los identificadores. Los dos ajustes parten del mismo modelo base. Las ventanas de confirmación ya participaron en entrenamientos históricos. Sirven para confirmar la comparación entre estos dos ajustes nuevos.

Desde la raíz de AirAware, generar una entrega en una carpeta local nueva. El primer argumento apunta a la carpeta que contiene el manifiesto histórico y `train/`.

```sh
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/direct_cohorts.py "$bloques" "$salida"
```

| Salida | Uso | Ventanas |
| --- | --- | ---: |
| `trainer/fit/` | Ajuste y muestra fija para la curva | 225 338 |
| `trainer/inner_validation/` | Evaluación periódica y selección del paso | 6 664 |
| `scorer/confirmation/` | Comparación posterior entre checkpoints congelados | 5 163 |
| `purged.json` | Auditoría local de las ventanas que cruzan un corte | 232 |

Cada ventana usa las horas del origen −23 al origen +6, ambas inclusive. El exportador une índice y mediciones por identificador y comprueba el conteo y la huella de cada rol. Calcula el percentil 95 de cada estación con horas únicas de las historias de ajuste. `graph_sample` identifica las 6 664 filas de ajuste elegidas por el orden de la huella de cada ID. La huella de pertenencia ordena los identificadores como texto UTF-8 y añade un salto de línea después de cada uno.

Cada carpeta de rol contiene `data.npz`, `thresholds.json` y `manifest.json`. El esquema `forecast-direct-cohort-v1` vincula el rol, las unidades, los pesos base, la procedencia, los archivos y el protocolo. El manifiesto raíz registra las huellas de los tres manifiestos. El consumidor debe verificar la huella esperada y el rol antes de abrir los datos. El entrenamiento recibe únicamente las dos carpetas de `trainer/`. La confirmación corresponde al proceso de puntuación y necesita permisos de almacenamiento separados.

Los archivos con mediciones permanecen en almacenamiento local. Una transferencia requiere verificar los derechos de uso aplicables y el acceso efectivo del destinatario.
