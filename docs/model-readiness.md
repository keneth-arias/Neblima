# Primer paso de entrenamiento con PM2.5 de Lima

Se ejecutó un paso de AdamW en una RTX 5070 Ti con el decodificador de texto de Qwen3.5-0.8B, el proyector temporal y el cabezal numérico de la [bifurcación de OpenTSLM](https://github.com/keneth-arias/OpenTSLM/pull/1). Los pesos publicados por Qwen tienen licencia Apache-2.0, la bifurcación usa MIT y la integración de AirAware usa AGPL-3.0-only. Los datos de SENAMHI conservan su licencia ODC-BY-1.0 y su [atribución](../DATA_ATTRIBUTION.md). [Revisión del modelo](https://huggingface.co/Qwen/Qwen3.5-0.8B/tree/2fc06364715b967f1860aea9cf38778875588b17).

## Ventana y resultado

La prueba usa la primera tarea de entrenamiento que entrega el lector de la versión congelada de #25. Se compara el SHA-256 del manifiesto con el publicado en el [informe de referencias](../reports/baselines/lima-pm25.md) y se ejecuta `TimeFReader.verify()`. Se comprueban la señal y su unidad, la estación provisional, la serie, el eje horario y el límite entre historia y objetivos. Las 24 casillas históricas de la ventana están medidas. El último dato corresponde al 02/01/2015 a las 04:00 UTC y los seis objetivos corresponden a las 05:00–10:00 UTC.

La media y la desviación estándar poblacional se calculan sobre la historia de esa ventana. Cuando la desviación es cero, la escala vale uno. Se aplica esa misma transformación a los seis objetivos para calcular el error cuadrático medio. Se conservan en µg/m³ las predicciones anteriores al paso y los objetivos originales. El decodificador solo recibe la historia y su máscara.

La pérdida normalizada fue 0,6275. El cambio máximo absoluto en el peso inspeccionado del decodificador fue aproximadamente 0,0001, al igual que en el cabezal. La asignación máxima de memoria registrada por PyTorch fue 8,46 GiB. Se usó un solo ejemplo, un cabezal recién inicializado y un solo paso en precisión de 32 bits. Uno de los seis pronósticos previos al ajuste fue negativo. La precisión y la comparación con persistencia quedan para #28. La [evidencia de ejecución](../metadata/qwen-smoke.json) conserva los valores originales del modelo, el tiempo del paso sincronizado, el entorno y los identificadores de procedencia.

## Reproducir

Desde la raíz de AirAware, preparar el entorno de TimeNet con `uv sync --project tools/timenet-smoke --locked`. El siguiente comando usa una copia local de la bifurcación en el commit fijado por [la configuración](../configs/upstream.lock.json). Para otras máquinas, clonar la bifurcación y descargar una vez la revisión del modelo según las [instrucciones del adaptador](https://github.com/keneth-arias/OpenTSLM/blob/20573a0f67f0f53bcd7d06a28869379e80d2d652/environments/forecast/README.md). El entrenamiento lee los pesos de la caché local y usa el entorno separado del lector de TimeNet.

```bash
fork=/home/shared/github/keneth-arias/OpenTSLM
PYTHONPATH="$fork/src" uv run --offline --locked --project "$fork/environments/forecast" \
  python tools/training/qwen_smoke.py \
  --release data/timef/airaware/lima-pm25-forecast/0.1.0
```

La salida JSON incluye los SHA-256 de la versión TimeF, la auditoría de fugas, las particiones, la grilla y el entorno de entrenamiento. El paso de verificación descarta los pesos actualizados al terminar. Las pruebas sin GPU reconstruyen dos versiones sintéticas con objetivos distintos para verificar que la historia y la máscara permanezcan idénticas.
