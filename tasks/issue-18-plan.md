# #18 · Ventanas completas de pronóstico de PM2.5

Generar ventanas desde la [grilla horaria](issue-15-plan.md). El constructor verifica la
versión y la suma SHA-256 del Parquet contra su manifiesto. Usa una sola señal compatible
por serie y valores observados finitos. Los valores en conflicto, ausentes e imputados no
aportan entradas ni objetivos.

```bash
uv run --locked airaware benchmark windows \
  --input data/curated/senamhi-lima-hourly \
  --output data/benchmarks/lima-pm25-h24-f6 \
  --history 24 --horizon 6 --step 1
```

La última hora de la historia es `origin_at`. El objetivo empieza una hora después. Los
rangos incluyen sus extremos. `series_id` y los límites permiten reconstruir la historia
en la grilla verificada sin duplicar ese arreglo en cada ventana. Cada ventana contiene
`target_values` en orden horario y `target_mean` para evaluar un objetivo escalar en el
horizonte elegido. El promedio con horizonte de 24 horas es móvil y conserva el propósito
retrospectivo aprobado.

El paso se ancla en el primer origen candidato por serie. Para conciliar con
`comparison-v3`, se buscan candidatos entre el primer y último valor utilizable. Los
descartes se contabilizan una vez por ventana, primero por falta en la historia y luego,
si la historia está completa, por falta en el objetivo.

## Verificación y entrega a #19

Parquet de entrada con SHA-256 `2e8fa784cea645b8eb97b42f3fe36e6c532b5959cc8ae66da0ea416df513413c`.
Se construyeron las 16 parejas del [informe de selección](../metadata/benchmark-selection.json)
con paso de una hora. Coincidieron los candidatos y las ventanas completas en todas las parejas.
Para 24/6 se verificaron 574 994 candidatos, de los cuales 230 545 se descartaron por historia,
5 244 por objetivo y 339 205 resultaron completos.

Una segunda ejecución 24/6 reprodujo el manifiesto y los bytes de `windows.parquet`.
SHA-256 `fdbbe324f4674a176bc2b865adb191f8acee409719ccbf5bf8f240903782c862`.
#19 consume esa versión del Parquet y su manifiesto para asignar y purgar las particiones.

`make check` pasó con 344 pruebas, incluidas pruebas de fronteras, huecos de historia y
objetivo, paso y manipulación del insumo. `make build` y `make audit` también aprobaron.
