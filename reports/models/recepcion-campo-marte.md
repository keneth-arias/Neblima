# Recepción de PM2.5 en Campo de Marte

El 20 de noviembre de 2026 se consultó el mismo gráfico de SENAMHI para la estación Campo de Marte (112194), parámetro N_PM25 y fechas publicadas del 18 al 20 de noviembre. Se eligió la estación porque tiene observaciones recientes y un código que también figura en la prueba externa. Las tres capturas locales tienen horas de recepción UTC. Las etiquetas del gráfico se conservan en el reloj publicado por el proveedor.

| Recepción UTC | Lecturas finitas vistas por primera vez en esta serie de capturas | SHA-256 de los bytes |
| --- | ---: | --- |
| 2026-11-20T01:24:05.447014+00:00 | 45 | `c64943ee5c3d35c587fb06a32f72f3e90812d705429b840f963281cdaba42150` |
| 2026-11-20T17:59:34.823969+00:00 | 16 | `c9cc280b22a34d545913665531de2739b187cfadd8bbf6f3d54a4ac496954d33` |
| 2026-11-20T18:02:54.437970+00:00 | 1 | `4e5ffbe3eede0dd5ecc5291ddf264410873cf647804e0d72ac1a5f5d10008376` |

En la primera captura había 45 horas con lectura y se desconoce desde cuándo estaban publicadas. Otras 17 aparecieron en capturas posteriores del mismo rango. Las consultas previas omitían esas etiquetas horarias. Ninguna de las 17 tenía un nulo explícito en el gráfico anterior. El informe conserva por hora la última consulta que la abarcó y señala si siguió dentro de la consulta más reciente. El primer instante exacto de publicación se desconoce. Una hora omitida conserva su última lectura conocida para detectar revisiones, y solo un nulo explícito posterior cuenta como retiro. Las tres capturas contienen 62 horas distintas con lectura, cero revisiones de valor y cero retiros. Hace falta confirmar la referencia horaria de la estación antes de calcular la demora absoluta de las lecturas o la anticipación operativa. El contraste histórico encontró desplazamientos distintos según el periodo. [Fuente oficial](https://www.senamhi.gob.pe/site/sea/www/site/sea/graficas/esta_conta.php?estacion=112194&conta=N_PM25) · [Evidencia del reloj](../prueba-externa-pm.md)

## Reproducción

Los originales y sus recibos se guardan localmente en `data/raw/prepiloto-campo-marte-v1`. Desde AirAware, el comando `capture` usa el ejecutable Lightpanda para una consulta acotada de los últimos tres días de calendario. Cada ejecución guarda los bytes y la hora UTC de recepción en un nuevo directorio. Se puede importar una captura previa con `import ROOT RECIBO ORIGINAL`. El informe se reconstruye sin red, contrasta las huellas y distingue ausencias, cambios de valor y retiros dentro del rango que cubre cada consulta.

```sh
R="${AIRAWARE_DATA_DIR:-data}/raw/prepiloto-campo-marte-v1"
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/station_receipts.py audit "$R" \
  --through 2026-11-20T18:02:54.437970+00:00

# Para probar una captura nueva, usar una carpeta separada.
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/station_receipts.py capture "$(mktemp -d)"
```

Los recibos sirven para caracterizar la fuente antes del piloto. La calibración de episodios y el puntaje de la prueba futura usan una cohorte con su elegibilidad y periodo fijados por separado.

## Puntaje provisional durante la emisión privada

Para cada pronóstico de +1 a +6 horas, el puntaje empareja Qwen y persistencia con la misma medición de Campo de Marte. Presenta dos vistas al corte elegido. La primera conserva la primera lectura recibida estrictamente después de emitir. La última incorpora las correcciones disponibles y excluye del denominador una lectura retirada. Si ya se conocía el objetivo al emitir, ninguna de las vistas lo usa. Un campo de error o cobertura vacío indica que todavía faltan pares para calcularlo.

El informe muestra pares y horas objetivo distintas, error absoluto medio en µg/m³, cobertura y amplitud del intervalo del 80 %, tanto globalmente como por horizonte. El tiempo hasta la primera recepción se mide entre las marcas UTC de emisión y llegada. La etiqueta horaria del gráfico identifica el objetivo. La interpretación de anticipación respecto de la exposición sigue pendiente de la correspondencia entre el reloj del gráfico y UTC.

En bm, el comando usa las emisiones privadas y los recibos operativos guardados. El corte incluye las observaciones recibidas y las emisiones publicadas hasta ese instante. Las huellas de ambos conjuntos permiten reproducir el informe. Una carpeta vacía de emisiones da cero pronósticos. Los datos conservarán su carácter provisional mientras se evalúa la maduración de la fuente.

```bash
D=/home/shared/github/keneth-arias/airaware/data
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/live_concentration_scores.py \
  "$D/processed/evaluacion-inmediata-campo-marte-20261120/en-vivo/issuances" \
  "$D/raw/campo-marte-operativo-20261120" --through 2026-11-20T21:00:00+00:00
```

El servicio horario de bm actualiza `en-vivo/puntaje-por-horizonte.json` después de procesar la consulta. La etiqueta `latest_live_horizon_report` de la primera corrida de emisión en MLflow identifica el archivo privado correspondiente al último corte procesado. Cada archivo conserva su huella en el nombre. Las horas sin medición quedan pendientes.
