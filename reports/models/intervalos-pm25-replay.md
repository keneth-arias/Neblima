# Intervalos horarios de PM2.5 en Lima

El intervalo central nominal de 80 % del Qwen directo con LoRA de rango 4 cubrió el 90,68 % de los 151 830 pares ventana-hora de selección (25 305 ventanas). La cobertura fue de 88,71 % en +1 h y 91,82 % en +6 h; las amplitudes medias fueron 15,39 y 35,33 µg/m³. El MAE global fue 6,238 µg/m³. En los 13 313 pares cuya concentración observada alcanzó el P95 de su estación, la cobertura cayó al 55,76 % y el MAE fue 15,787 µg/m³. Los extremos publicados se acotan a cero para expresar concentraciones físicas. Las ventanas se solapan. Esta repetición histórica usa un periodo ya utilizado para elegir el modelo de #28. Una comparación de finalistas requiere otra prueba intacta. [Desglose por estación y horizonte](../../metadata/intervalos-pm25-replay-v1.json)

El exportador tomó los archivos univariados de #28 de entrenamiento, validación y prueba, con sus huellas congeladas. Los cortes UTC fueron el 16/03/2022 a las 08 h, el 01/09/2022 a las 00 h y el 25/02/2023 a las 18 h. Quedaron 237 397 ventanas de entrenamiento, 25 201 de calibración, 25 305 de selección y 50 789 en el bloque final. Se purgaron 200 porque parte de sus 30 horas cruzaba un corte. El ajuste del intervalo y este informe usaron únicamente calibración y selección. Los coeficientes son los percentiles 10 y 90 del residuo «observado menos pronosticado» por hora en calibración. El archivo de predicciones fuente fue `fits/direct-lora/validation.npz` y los objetivos se emparejaron por `window_id`.

## Reproducción desde las matrices de #28

Desde la raíz de AirAware, ejecutar el comando con la carpeta original de #28 y una carpeta nueva. Las tres huellas se comprueban contra los [insumos de entrenamiento y selección](../../configs/training.yaml) y el [recibo público de la prueba de #28](../../metadata/qwen-heldout-lima.json).

```sh
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/replay_episode_intervals.py "$origen_qwen_v1" "$salida"
```

El comando genera bloques, calibrador, predicciones, informe de cobertura por estación, horizonte y nivel observado, y archivos de intersección exacta de IDs y horas por estación con cada uso previo. Las 50 789 ventanas del bloque final coinciden con la prueba ya evaluada (53 863 horas-estación entre historias y objetivos). El evaluador de esta repetición admite únicamente selección. Cada fila del índice conserva la hora original, la estación y la posición del archivo original en la lista de fuentes del manifiesto. El exportador de #25 verificó las unidades y la procedencia en el TimeF de origen. El cotejo posterior de los 338 892 IDs recuperó las siete series de origen. Las siete tienen `sensor_id` nulo en la grilla histórica. La elegibilidad de episodios reales sigue pendiente de evidencia instrumental y de calidad. [Verificación por serie y bloque](procedencia-episodios-lima.md)

El ajuste opcional de probabilidad acepta `--eligible-labels`, un NPZ de evaluación con `window_id`, `event` (0, 1, o −1 para no evaluable), `manifest_sha256` y `thresholds_sha256`. Usar etiquetas con elegibilidad establecida por el responsable de los datos. La prueba sintética contrasta cada positivo con los seis objetivos y fija el calibrador logístico de pendiente no negativa. La salida señala las estaciones sin umbral conocido. Esta repetición real produjo únicamente intervalos de concentración.

## Comparación entre cabezales con dos semillas

Para cada semilla (27 y 28), calibrar los residuos del control directo en calibración y aplicar ese calibrador en selección. Entregar su archivo de intervalos como referencia a `episode_quantiles.py`. El informe contiene las medidas de ambos cabezales y sus diferencias pareadas. Para calcular la decisión histórica correr desde la raíz con las rutas a los dos informes, los manifiestos de los puntos de control finales de cada cabezal y los paquetes de entrenamiento directo.

```sh
regla=configs/training/lima-comparacion-cuantiles-v1.yaml
uv run --locked python -m airaware.episode_forecast_selection "$regla" "$huella_regla_preinscrita" seleccion.json \
  --pair "$informe27" "$cuantiles27/manifest.json" "$directo27/manifest.json" "$paquete27/manifest.json" \
  --pair "$informe28" "$cuantiles28/manifest.json" "$directo28/manifest.json" "$paquete28/manifest.json"
```

La salida conserva las huellas de los insumos y la decisión sobre la media de las semillas. Verifica que cada comparación usó su control directo pareado, que ambos ajustes terminaron la misma época y que las dos semillas cubren la misma cohorte. La decisión indica qué cabezal pasaría a una prueba posterior con horas nuevas. [Criterios congelados](../../configs/training/lima-comparacion-cuantiles-v1.yaml)
