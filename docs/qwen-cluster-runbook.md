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

Elegir un identificador lógico distinto por variante y semilla. Mantenerlo al reanudar, igual que la imagen, lote, datos, número de procesos y duración del planificador. La aplicación bloquea escritores simultáneos para ese identificador. Cuando el pod publica un estado, el archivo `manifest.json` permite identificar los fragmentos y comprobar sus sumas. El estado se recupera de la última generación completa y compatible.

Para reproducir la comprobación, guardar los registros del ajuste continuo y el reanudado con SkyPilot. Ejecutar el comparador en el entorno PyTorch 2.9.1, con acceso de lectura a las carpetas del paso final.

```bash
python tools/training/check_resume.py continuo.log reanudado.log \
  /ruta/al/continuo/step-00000004 /ruta/al/reanudado/step-00000004
```

El comparador comprueba las ventanas, pérdida, tasa de aprendizaje, error final de validación y pesos seleccionados del cabezal y decodificador. El volumen de MicroK8s conserva el estado al retirar un pod. Para recuperar ante pérdida de `bm`, hace falta una copia verificada en otro equipo o dispositivo.

## Repetir la comparación piloto

Fijar lote global 4, semilla 27 y cuatro pasos, con las mismas matrices para persistencia, Qwen directo, Qwen residual y la red convolucional. Usar `tools/training/compare_cnn.py` en el entorno PyTorch para la referencia convolucional. La comparación piloto verifica el flujo de datos y las métricas. La selección para #28 requiere el entrenamiento presupuestado y validación cronológica completa, con predicciones por estación y horizonte.
