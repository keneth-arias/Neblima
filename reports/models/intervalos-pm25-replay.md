# Intervalos horarios de PM2.5 en Lima

El intervalo central nominal de 80 % del Qwen directo con LoRA de rango 4 cubrió el 90,68 % de los 151 830 pares ventana-hora de selección (25 305 ventanas). La cobertura fue de 88,71 % en +1 h y 91,82 % en +6 h; las amplitudes medias fueron 15,39 y 35,91 µg/m³. El MAE global fue 6,238 µg/m³. Las ventanas se solapan. Esta repetición histórica usa un periodo ya utilizado para elegir el modelo de #28. Una comparación de finalistas requiere otra prueba intacta. [Desglose por estación y horizonte](../../metadata/intervalos-pm25-replay-v1.json)

El exportador tomó los archivos univariados de #28 de entrenamiento, validación y prueba, con sus huellas congeladas. Los cortes UTC fueron el 16/03/2022 a las 08 h, el 01/09/2022 a las 00 h y el 25/02/2023 a las 18 h. Quedaron 237 397 ventanas de entrenamiento, 25 201 de calibración, 25 305 de selección y 50 789 en el bloque final. Se purgaron 200 porque parte de sus 30 horas cruzaba un corte. El ajuste del intervalo y este informe usaron únicamente calibración y selección. Los coeficientes son los percentiles 10 y 90 del residuo «observado menos pronosticado» por hora en calibración. El archivo de predicciones fuente fue `fits/direct-lora/validation.npz` y los objetivos se emparejaron por `window_id`.

## Reproducción desde las matrices de #28

En el entorno bloqueado de `tools/timenet-smoke`, ejecutar `episode_blocks.py` con una opción `--source ARCHIVO SHA256` por matriz, `--cuts` con las tres fechas ISO anteriores y una carpeta nueva de salida. Las huellas originales están en [la configuración de entrenamiento](../../configs/training.yaml) y en el recibo `holdout-v1/export.json`. Cada bloque publica un índice con estación, ID y hora UTC, un archivo de historias para inferencia y otro de objetivos para evaluación. La tabla de umbrales toma una sola copia de cada hora-estación de las historias de entrenamiento. Las huellas de archivos quedan en `manifest.json`.

Extraer, para cada uno de los dos bloques evaluados, las filas de la predicción original en el orden de su índice. Conservar `window_id`, `predicted`, `forecast_hour` y `checkpoint_sha256`. Desde la carpeta de los scripts ejecutar lo siguiente con las rutas y huellas correspondientes.

```sh
python episode_calibration.py fit "$bloques" calibration.npz calibrador.json --manifest-sha256 "$manifest_sha"
python episode_calibration.py apply "$bloques" selection.npz intervalos.npz --block selection \
  --manifest-sha256 "$manifest_sha" --calibrator calibrador.json --calibrator-sha256 "$cal_sha"
```

El ajuste opcional de probabilidad acepta `--eligible-labels`, un NPZ de evaluación con `window_id`, `event` (0, 1, o −1 para no evaluable), `manifest_sha256` y `thresholds_sha256`. Usar etiquetas con elegibilidad establecida por el responsable de los datos. La prueba sintética contrasta cada positivo con los seis objetivos y fija el calibrador logístico de pendiente no negativa. La salida señala las estaciones sin umbral conocido. Esta repetición real produjo únicamente intervalos de concentración.
