# Prueba futura de concentración en Campo de Marte

La regla histórica compara dos cabezales Qwen con adaptadores LoRA de rango 4 en siete estaciones. Para verificar si el elegido mejora a la persistencia en horas nuevas, reservamos una semana completa en Campo de Marte, código 112194. Es la estación en la que iniciamos los recibos verificables de SENAMHI. La decisión de pasar a un piloto privado solo podrá aplicarse a esa estación. [Regla histórica](../../configs/training/lima-comparacion-cuantiles-v1.yaml) · [Procedencia de la fuente](recepcion-campo-marte.md) · [Protocolo registrado](../../configs/training/lima-prueba-futura-campo-marte-v1.json)

| Hito | Reloj y criterio |
| --- | --- |
| Congelación | Antes del 22/11/2026 a las 00:00 UTC. Reproducir la comparación de las semillas 27 y 28 y conservar el cabezal elegido con la semilla prefijada 27. Publicar la huella del sello antes de recoger los datos reservados. |
| Orígenes | Todas las horas desde el 24/11 a las 00:00 hasta el 30/11 a las 23:00, inclusive. Son 168 orígenes en las etiquetas horarias nativas del gráfico. |
| Historia y objetivos | La primera historia comienza el 23/11 a la 01:00. El último objetivo corresponde al 01/12 a las 05:00. La historia incluye la hora del origen. |
| Recepción en bm | Diez capturas diarias, del 23/11 al 02/12 a las 18:10 UTC, con `lima-pm25-prueba-campo-marte-20261123.timer`. Cada consulta solicita tres fechas. Se preservan los bytes, su huella y la hora de recepción en la carpeta exclusiva `data/raw/prueba-campo-marte-20261123-v1`. |
| Cierre de observaciones | 02/12/2026 a las 19:00 UTC. Se toma la última lectura explícita recibida hasta ese instante inclusive. Un nulo explícito retira el valor. Una hora omitida conserva el último valor listado. |

Se conocen las etiquetas del gráfico y el instante UTC de cada recepción. La correspondencia exacta entre ambos relojes sigue abierta. Esta prueba reconstruye concentraciones con las revisiones disponibles al cierre y mide la calidad del pronóstico en esa versión del registro. La anticipación operativa requerirá una emisión real con las lecturas disponibles en su momento.

## Congelar y preparar

El sello enlaza los dos informes pareados, la decisión, el punto de control, la versión de Qwen, el calibrador directo y la imagen privada por sus huellas SHA-256. El programa coteja los insumos de ambas semillas. Un reintento idéntico devuelve la primera hora de congelación. Usar las huellas publicadas al emitir la decisión y el sello.

```bash
P=configs/training/lima-prueba-futura-campo-marte-v1.json
R=configs/training/lima-comparacion-cuantiles-v1.yaml
uv run --locked python -m airaware.holdout_release "$P" "$R" "$DECISION" "$CALIBRADOR_27" "$SELLO" \
  --protocol-sha256 "$SHA_PROTOCOLO" --decision-sha256 "$SHA_DECISION" \
  --pair "$INFORME_27" "$CK_CUANTILES_27" "$CK_DIRECTO_27" "$PAQUETE_DIRECTO_27" \
  --pair "$INFORME_28" "$CK_CUANTILES_28" "$CK_DIRECTO_28" "$PAQUETE_DIRECTO_28"

uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/holdout_station_windows.py \
  "$P" "$SELLO" "$RECEPCIONES" "$COHORTE" --protocol-sha256 "$SHA_PROTOCOLO" --seal-sha256 "$SHA_SELLO"
```

La segunda orden abre la cohorte a partir del cierre del 02/12 y verifica los recibos originales. Los 168 orígenes quedan inventariados, con conteos de lecturas ausentes y lecturas fuera del rango numérico de la imagen. Si no hay historias aptas, se registra un resultado inconcluso sin asignar GPU. Se entrega al proceso de inferencia únicamente `infer/`, con el ID y las 24 lecturas finitas de cada historia completa. Los objetivos faltantes conservan su lugar en `scoring/observed.npz`; un objetivo faltante nunca descarta una historia apta. La carpeta de puntuación queda fuera del montaje de inferencia.

## Decisión registrada

Calcular el error absoluto medio (MAE) del modelo y de repetir la última lectura sobre los mismos pares origen–horizonte observados. Medir cobertura inclusiva y amplitud de los intervalos entre los cuantiles 10 y 90, globalmente y para cada hora de +1 a +6. En el control directo usar los residuos congelados por horizonte y truncar los límites inferiores y superiores en cero, como en selección. Contar las horas-estación distintas además de los pares solapados. Desglosar las horas altas según el percentil 95 histórico congelado de Campo de Marte. Una sola semana ofrece una única unidad para el remuestreo de 168 horas.

Si cualquiera de las siete fechas de origen carece de ventanas puntuables en las seis horas, el resultado será **inconcluso**. Con cobertura suficiente, el MAE global debe ser estrictamente menor que el de persistencia y la cobertura global del intervalo debe estar entre 75 % y 85 %, inclusive. Un incumplimiento veta esta versión para el piloto. Si cumple, corresponde revisar las medidas por horizonte y la disponibilidad de la estación antes de autorizar un piloto de concentraciones. La probabilidad de episodio y el desempeño de avisos conservan los requisitos de evidencia de #20 y #43.

## Puntuar al cierre

El trabajo de ml-infra ejecuta primero la verificación por CPU de la huella del paquete, los pesos y el punto de control de la semilla 27. Usar el `infer/` de la cohorte y la generación retenida como orígenes de los montajes de solo lectura de este trabajo. `launch-episode.sh job infer` recibe el cabezal del sello, la imagen exacta, la huella de `infer/manifest.json`, `--step 14838` y `--seed 27`. Con cero historias aptas se pasa directamente al puntaje sin salida de inferencia.

```bash
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/score_station_holdout.py \
  "$P" "$SELLO" "$COHORTE" "$UMBRALES" "$CALIBRADOR_27" "$INFORME" \
  --protocol-sha256 "$SHA_PROTOCOLO" --seal-sha256 "$SHA_SELLO" \
  --cohort-sha256 "$SHA_RECIBO_COHORTE" --worker-output "$SALIDA"
```

`$SHA_RECIBO_COHORTE` identifica `receipt.json`, publicado al preparar las ventanas. `$SALIDA` contiene la predicción, el registro de entrada original del worker y su recibo de salida; se omite `--worker-output` para cero historias. El informe vincula la predicción con ese proceso y su cohorte, y cuenta objetivos observados y horas distintas. La unidad del MAE y la amplitud es µg/m³. Se informa la cobertura como fracción de los objetivos realmente medidos. El puntaje de persistencia repite el valor de la última hora tal como se entregó al modelo.
