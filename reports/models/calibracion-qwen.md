# Costo del ajuste de Qwen y presupuesto para Lima

Para [#28](https://github.com/keneth-arias/airaware/issues/28) se eligió un proceso por tarjeta y un cabezal por proceso. Las dos RTX 5070 Ti completaron ambos ajustes de 60 pasos en una mediana de **30,92 s**. Dividir el estado con FSDP2 redujo el pico de memoria a **6,46 GiB por tarjeta**. El ajuste individual completo con lote 16 ya cabe en una tarjeta.

## Medición del 19 de noviembre de 2026

Se usaron únicamente ventanas de entrenamiento de la versión TimeF congelada. En cada repetición, los primeros 10 pasos calentaron el modelo y los siguientes 50 procesaron 800 ventanas. Los 60 pasos siguieron el mismo orden y semilla, con lote global 16, FP32 y el mismo optimizador. Se alternó el orden de los modos entre las tres repeticiones. La tabla resume las tres mediciones. Para el par independiente se informa la velocidad de cada cabezal. [Registro por ejecución](../../metadata/qwen-calibration.json).

| Modo | Ventanas/s de cálculo, mediana (mín.–máx.) | Pico asignado por GPU (GiB) | Tiempo total mediano (s) |
| --- | ---: | ---: | ---: |
| Una GPU, directo | 64,36 (63,38–70,88) | 10,43 | 26,76 |
| Dos GPU, réplicas DDP, directo | 56,11 (56,03–59,07) | 10,39 | 28,36 |
| Dos GPU, estado repartido FSDP2, directo | 35,53 (35,49–35,60) | 6,46 | 38,40 |
| Un cabezal por GPU, directo | 61,48 (60,22–64,29) | 10,43 | 30,92 por el par |
| Un cabezal por GPU, corrección de persistencia | 61,22 (60,21–62,67) | 10,43 | 30,92 por el par |

Las ventanas/s dividen la exposición medida por la suma de tiempos de cálculo sincronizados del entrenador. El tiempo total incluye el arranque de procesos, la lectura, los 60 pasos, el guardado y la liberación del estado temporal. Los tiempos de creación del pod y el registro por paso en MLflow se miden aparte en la ejecución de producción. La prueba adicional de LoRA con un proceso dio 74,63 ventanas/s y 6,57 GiB asignados. Corresponde a una sola repetición de capacidad.

Se compararon FP32 y BF16 con el mismo modelo y lote de entrenamiento antes del ajuste. Se fijaron tolerancias de 2 % para el error relativo de predicciones y pérdida y de 5 % para los gradientes inspeccionados. En BF16, las predicciones difirieron en 5,19 %, el gradiente del proyector en 8,95 % y el del primer bloque del decodificador en 10,56 %. Se eligió FP32. La imagen fijada utilizó el núcleo recurrente de PyTorch para los siete tokens de la serie. La implementación opcional acelerada estaba ausente y su rendimiento queda sin medir.

## Presupuesto fijado antes de la selección

La [configuración de ajuste](../../configs/training/lima-pm25-fit-v1.yaml) registra **14 837 actualizaciones** por variante. Se consumen 237 392 de las 237 397 ventanas de entrenamiento. Las cinco del último lote incompleto se omiten en todas las variantes. El SHA-256 del orden se calculó con la permutación del entrenador fijado y la semilla 27. Cada lote se codifica como un arreglo JSON compacto de identificadores seguido por un salto de línea.

En la repetición más lenta del par se procesaron al menos 30,67 ventanas/s por cabezal al incluir el costo de iniciar y guardar cada ensayo corto. En una GPU se midieron 234,94 ventanas/s de inferencia FP32 sobre datos de entrenamiento. A esas velocidades, una pasada de entrenamiento y dos pasadas de 50 706 ventanas para validación y exportación tomarían **unas 2,27 horas por GPU**. Es una estimación. Registrar el tiempo real, incluir los intentos previos al reanudar y respetar el máximo de cuatro horas-GPU por ajuste.

El cabezal directo y el de corrección de persistencia comparten el pod y leen el mismo archivo verificado. Cada uno guarda su estado por separado en `training/airaware-model-state`. El volumen local de 64 GiB conservó un archivo entre dos pods distintos. La red convolucional usa el mismo orden de ventanas en CPU. La comparación de LoRA emplea el cabezal de menor error absoluto medio en validación. Se conserva el directo en empate de cabezales y se elige LoRA en empate de estrategias. La primera comparación de calidad usa los 304 236 objetivos de validación. La inferencia de prueba espera la selección y el registro de las sumas de los puntos de control.

## Reproducción

Con la imagen por digest indicada en la configuración, copiar `tools/training` al directorio de trabajo del pod y montar los insumos de solo lectura. Usar rutas nuevas para las salidas y una carpeta de escritura en el mismo volumen para medir el guardado. Verificar antes las sumas del modelo base. El comando completo guarda las métricas y los registros de cada proceso. Los estados temporales se retiran tras cada medición.

```bash
export PYTHONPATH=/opt/forecast/src OMP_NUM_THREADS=2 HF_HUB_OFFLINE=1
train=/inputs/windows/lima-pm25-qwen-v1/train.npz
digest=945bb4c0fb6fd5490891f0986faf42aa37682f1fe05bf5700ebac3847a86f6fb
(cd /inputs/qwen && sha256sum --check SHA256SUMS)
/opt/conda/bin/python measure_qwen.py --data "$train" --sha256 "$digest" \
  --weights /inputs/qwen/weights --scratch /checkpoints --output /checkpoints/medicion-fp32
/opt/conda/bin/python probe_qwen_precision.py --data "$train" --digest "$digest" \
  --weights /inputs/qwen/weights --output /checkpoints/medicion-fp32/precision.json
```

Para la prueba de capacidad de LoRA, usar otra carpeta de salida y añadir `--lora --modes single --repeats 1`. La inferencia de validación y la escritura de predicciones desde puntos de control siguen el [procedimiento del clúster](../../docs/qwen-cluster-runbook.md).
