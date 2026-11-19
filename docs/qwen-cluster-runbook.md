# Ajuste y reanudación de Qwen en el clúster local

El entrenamiento usa una imagen del perfil SkyPilot de ml-infra, un pod en `bm` y un proceso por GPU. El [plan operativo](../tasks/issue-28-cluster.md) describe la secuencia. El entrenador y la configuración se revisan en el [PR de OpenTSLM](https://github.com/keneth-arias/OpenTSLM/pull/3) y el [PR de ml-infra](https://github.com/keneth-arias/ml-infra/pull/1).

## Preparar la entrada

Montar la versión TimeF congelada y la revisión fijada de Qwen desde el almacenamiento local. Desde AirAware, después de instalar el entorno fijado de TimeNet, exportar dos archivos nuevos en la carpeta de insumos del volumen. Omitir `--sample` para exportar una partición completa.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked \
  python tools/timenet-smoke/export_qwen_windows.py "$inputs/timef" "$inputs/train.npz" \
  --split train --sample 512
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked \
  python tools/timenet-smoke/export_qwen_windows.py "$inputs/timef" "$inputs/validation.npz" \
  --split validation --sample 128
```

El lector verifica el manifiesto congelado y conserva identificador, estación, origen, historia y objetivos. Las muestras son reproducibles por identificador y semilla 27. El preprocesamiento del modelo calcula el centro y la escala solo con la historia de la ventana. Las pruebas cambian los objetivos futuros y comprueban la independencia de la entrada.

## Recuperar el ajuste

Elegir un identificador lógico distinto por variante y semilla. Mantenerlo al reanudar, igual que la imagen, lote, datos, número de procesos y duración del planificador. La aplicación bloquea escritores simultáneos para ese identificador. Cuando el pod publica un estado, el archivo `manifest.json` permite identificar los fragmentos y comprobar sus sumas. El estado se recupera de la última generación completa y compatible. Para reanudar las generaciones del primer ensayo, seleccionar su imagen con `--image-id docker:ml-infra/training:qwen-10c5fdfa1cca-r2`. El perfil nuevo fija el entrenador con LoRA y se usa para ejecuciones nuevas.

Para reproducir la comprobación, guardar los registros del ajuste continuo y el reanudado con SkyPilot. Ejecutar el comparador en el entorno PyTorch 2.9.1, con acceso de lectura a las carpetas del paso final.

```bash
python tools/training/check_resume.py continuo.log reanudado.log \
  /ruta/al/continuo/step-00000004 /ruta/al/reanudado/step-00000004
```

El comparador comprueba las ventanas, pérdida, tasa de aprendizaje, error final de validación y pesos seleccionados del cabezal y decodificador. El volumen de MicroK8s conserva el estado al retirar un pod. Para recuperar ante pérdida de `bm`, hace falta una copia verificada en otro equipo o dispositivo.

## Repetir la comparación piloto

Fijar lote global 4, semilla 27 y cuatro pasos, con las mismas matrices para persistencia, Qwen directo, Qwen residual y la red convolucional. Usar `tools/training/compare_cnn.py` en el entorno PyTorch para la referencia convolucional. La comparación piloto verifica el flujo de datos y las métricas. La selección para #28 requiere el entrenamiento presupuestado y validación cronológica completa, con predicciones por estación y horizonte.

## Evidencia del piloto

Se tomaron 512 ventanas de la partición de entrenamiento y 128 de validación. Los cuatro pasos consumieron 16 ventanas de entrenamiento. El ensayo FSDP2 ejecutó 4 pasos continuos y 2 + 2 con pods separados. El segundo pod retomó el paso 2 en presencia de una carpeta de escritura incompleta. Coincidieron los identificadores, tasa y pérdida de los pasos 3 y 4, el MAE final y todos los valores de los dos tensores inspeccionados. El [registro reproducible](../metadata/qwen-cluster-drill.json) contiene revisiones de imágenes, sumas de matrices y métricas.

En los tres modos con el cabezal directo, las pérdidas del lote global coincidieron con una tolerancia relativa de 0,0001. La comparación de rendimiento incluye tres pasos medidos después del primero. La memoria indicada es el pico asignado por PyTorch en el rango de mayor consumo.

| Modo de ajuste completo | Ventanas/s | GiB por GPU |
| --- | ---: | ---: |
| Una GPU | 18,66 | 8,44 |
| Dos GPU, DDP | 15,39 | 10,30 |
| Dos GPU, FSDP2 | 9,30 | 5,46 |

El estado completo de FSDP2 ocupó 6,52 GiB y tardó entre 6,1 y 7,4 s en las ejecuciones continua y reanudada. Con cuatro generaciones simultáneas y 20 % de margen, prever unos 31,3 GiB para un ajuste completo, más los insumos y otros experimentos. El ensayo inicial usó el PVC de 32 GiB. Se migraron y verificaron ocho generaciones en la nueva solicitud `training/airaware-checkpoints` de 64 GiB, con política de retención `Retain`. Un pod SkyPilot que montó el nuevo volumen restauró el paso 2 y reprodujo los pasos 3 y 4, incluido el MAE y los tensores de control. El perfil actualizado usa el volumen de 64 GiB. Se conserva la copia original.

| Pronóstico sobre 128 ventanas | MAE (µg/m³) |
| --- | ---: |
| Persistencia | 10,0107 |
| Red convolucional temporal | 10,4782 |
| Qwen directo con FSDP2 | 13,5589 |
| Qwen con corrección de persistencia y FSDP2 | 9,8225 |

La evidencia mide el funcionamiento y la reanudación con un presupuesto de cuatro pasos. La comparación con calentamiento y repeticiones, la evaluación completa de #28 y la restauración desde una copia fuera de `bm` siguen pendientes.

LoRA híbrida verificó 114 proyecciones en las 24 capas del decodificador. En dos GPU con DDP reanudó desde el paso 2, completó el paso 4 y guardó 18,65 MB de estado. El modelo base congelado se reconstruye desde la revisión verificada de los insumos.

## Preparar la validación completa de #28

La versión `qwen-pm25-v1` contiene todas las ventanas de entrenamiento y validación. Desde la raíz de AirAware, usar una carpeta nueva para conservar el piloto y verificar la referencia antes del ajuste.

```bash
inputs=data/benchmarks/qwen-pm25-v1
release=data/timef/airaware/lima-pm25-forecast/0.1.0
mkdir -p "$inputs"
for split in train validation; do
  UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python \
    tools/timenet-smoke/export_qwen_windows.py "$release" "$inputs/$split.npz" --split "$split"
done
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python \
  tools/timenet-smoke/paired_forecasts.py "$inputs" data/benchmarks/lima-pm25-h24-f6-baselines \
  "$inputs/persistence"
```

El comparador comprueba los SHA-256 fijados en [la configuración](../configs/training.yaml) y verifica identificadores, estación, origen UTC, objetivo y valor al origen por cada horizonte. Para comparar un modelo, usar otra carpeta de salida y agregar `--forecasts <archivo.npz> --model <nombre> --revision <revision>`. El NPZ requiere `window_id` (texto), `forecast_hour` (vector de 1 a 6) y `predicted` (una fila con seis valores en µg/m³ por ventana). El resultado conserva las filas emparejadas en `paired.parquet` y las sumas y el MAE en `manifest.json`. El [control de persistencia](../metadata/qwen-validation-inputs.json) registra la comprobación con datos completos.
