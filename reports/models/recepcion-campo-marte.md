# Recepción de PM2.5 en Campo de Marte

El 20 de noviembre de 2026 se consultó el mismo gráfico de SENAMHI para la estación Campo de Marte (112194), parámetro N_PM25 y fechas publicadas del 18 al 20 de noviembre. Se eligió la estación porque tiene observaciones recientes y un código que también figura en la prueba externa. Las tres capturas locales tienen horas de recepción UTC. Las etiquetas del gráfico se conservan en el reloj publicado por el proveedor.

| Recepción UTC | Lecturas finitas vistas por primera vez en esta serie de capturas | SHA-256 de los bytes |
| --- | ---: | --- |
| 2026-11-20T01:24:05.447014+00:00 | 45 | `c64943ee5c3d35c587fb06a32f72f3e90812d705429b840f963281cdaba42150` |
| 2026-11-20T17:59:34.823969+00:00 | 16 | `c9cc280b22a34d545913665531de2739b187cfadd8bbf6f3d54a4ac496954d33` |
| 2026-11-20T18:02:54.437970+00:00 | 1 | `4e5ffbe3eede0dd5ecc5291ddf264410873cf647804e0d72ac1a5f5d10008376` |

En la primera captura había 45 horas con lectura y se desconoce desde cuándo estaban publicadas. Otras 17 aparecieron en capturas posteriores del mismo rango. Las consultas previas omitían esas etiquetas horarias. El primer instante exacto de publicación se desconoce. Una hora omitida conserva su última lectura conocida para detectar revisiones, y solo un nulo explícito posterior cuenta como retiro. Las tres capturas contienen 62 horas distintas con lectura, cero revisiones de valor y cero retiros. Hace falta confirmar la referencia horaria de la estación antes de calcular la demora absoluta de las lecturas o la anticipación operativa. El contraste histórico encontró desplazamientos distintos según el periodo. [Fuente oficial](https://www.senamhi.gob.pe/site/sea/www/site/sea/graficas/esta_conta.php?estacion=112194&conta=N_PM25) · [Evidencia del reloj](../prueba-externa-pm.md)

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
