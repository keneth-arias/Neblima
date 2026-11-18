# Referencias de pronóstico de PM2.5 para Lima

Las referencias consumen la [versión TimeF completa](../../tasks/issue-22-plan.md) y
verifican sus identificadores, particiones y objetivos contra el
[Parquet congelado](../../tasks/issue-19-plan.md). La historia y los parámetros de ajuste
provienen de la [grilla verificada](../../tasks/issue-15-plan.md).

## Método

- **Persistencia** repite el valor de PM2.5 medido en el origen.
- **Día anterior** repite el valor de la misma hora del día anterior para cada objetivo.
  Para horizontes de una a seis horas esa medición pertenece a la historia de 24 horas.
- **Promedio estacional diario** usa el promedio por serie y hora UTC de las observaciones
  publicadas antes del corte de validación. Cada hora medida contribuye una vez al ajuste.
- El error absoluto medio (MAE) de validación elige la referencia principal. Se calcula
  también la raíz del error cuadrático medio (RMSE). El error absoluto escalado medio
  (MASE) divide cada error absoluto por el error medio de la referencia de 24 horas,
  calculado con pares medidos del bloque de entrenamiento de la misma serie. La cobertura
  del escalado se informa con `n_mase`. Si falta escala o es cero, MASE queda indefinido.
- Para la inspección de concentraciones altas se fija un percentil 95 por serie con
  entrenamiento. Esta agrupación es exploratoria y conserva el alcance retrospectivo.
  Las métricas se guardan por partición, estación, horizonte, trimestre meteorológico y
  grupo de concentración. Se incluye el cruce estación-horizonte.

Las tres referencias cubren los mismos 2 033 352 objetivos. Sus tamaños por partición
son 1 424 382 en entrenamiento, 304 236 en validación y 304 734 en prueba.
Las ventanas solapadas comparten observaciones y los conteos corresponden a pares
ventana-hora. Cada predicción se compara con el objetivo de su propio par.

## Resultados

| Referencia | MAE de validación (µg/m³) | MAE de prueba (µg/m³) | RMSE de prueba (µg/m³) | MASE de prueba |
| --- | ---: | ---: | ---: | ---: |
| **Persistencia** | **9,5291** | **6,4459** | **10,2993** | **0,6657** |
| Día anterior | 11,2818 | 7,0384 | 10,9172 | 0,7326 |
| Promedio estacional diario | 13,2633 | 8,2694 | 11,6800 | 0,8432 |

Persistencia queda seleccionada por validación. En prueba, su MAE por horizonte es
3,2149, 5,0852, 6,3827, 7,3523, 8,0709 y 8,5696 µg/m³, respectivamente.
Cada hora futura aporta 50 789 objetivos. Entre los 10 574 objetivos de prueba sobre el
percentil 95 de su serie, el MAE de persistencia es 19,6156 µg/m³. Los cortes por estación
y temporada se consultan en `metrics.parquet`.

## Reproducir y entregar a #27 y #28

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked \
  python tools/timenet-smoke/evaluate_baselines.py \
  --release data/timef/airaware/lima-pm25-forecast/0.1.0 \
  --timeline data/curated/senamhi-lima-hourly \
  --splits data/benchmarks/lima-pm25-h24-f6-splits \
  --output data/benchmarks/lima-pm25-h24-f6-baselines
```

La carpeta nueva contiene `predictions.parquet`, `metrics.parquet`, `fit.parquet` y
`manifest.json`. Para comparar con el modelo temporal, unir las predicciones por
`window_id` y `forecast_hour` y verificar partición, objetivo y cobertura. El manifiesto
fija la referencia primaria, las sumas de los insumos y los archivos de salida. Se verificaron
dos ejecuciones idénticas, con 5,62 s y 2 516 000 KiB de memoria residente en la primera.
El SHA-256 del manifiesto TimeF de entrada es
`29135340efb377a59d695e05fb6f8848fd0e56481123f5b54e987da77e9adc97`.
SHA-256 de predicciones `0897715db89a7bfdab00be6b327753a029a9db65c96f622f0200af8fc7f62412`.
SHA-256 de métricas `9236a257a5ad8495b8b57c79d588178569c4b81f1afa012628f981a36bac1e8c`.

Pasaron 347 pruebas de AirAware, el empaquetado y la auditoría de dependencias.
Pasaron seis pruebas TimeF con red deshabilitada, entre ellas desfases de una hora y un
día, selección de datos de entrenamiento y escalado indefinido para series constantes.
