# Recepción de PM2.5 en Campo de Marte

El 20 de noviembre de 2026 se consultó el mismo gráfico de SENAMHI para la estación Campo de Marte (112194), parámetro N_PM25 y fechas publicadas del 18 al 20 de noviembre. Se eligió la estación porque tiene observaciones recientes y un código que también figura en la prueba externa. Las tres capturas locales tienen horas de recepción UTC. Las etiquetas del gráfico se conservan en el reloj publicado por el proveedor.

| Recepción UTC | Lecturas finitas vistas por primera vez en esta serie de capturas | SHA-256 de los bytes |
| --- | ---: | --- |
| 2026-11-20T01:24:05.447014+00:00 | 45 | `c64943ee5c3d35c587fb06a32f72f3e90812d705429b840f963281cdaba42150` |
| 2026-11-20T17:59:34.823969+00:00 | 16 | `c9cc280b22a34d545913665531de2739b187cfadd8bbf6f3d54a4ac496954d33` |
| 2026-11-20T18:02:54.437970+00:00 | 1 | `4e5ffbe3eede0dd5ecc5291ddf264410873cf647804e0d72ac1a5f5d10008376` |

En la primera captura había 45 horas con lectura y se desconoce desde cuándo estaban publicadas. Otras 17 aparecieron en capturas posteriores del mismo rango. Las consultas previas omitían esas etiquetas horarias. Ninguna de las 17 tenía un nulo explícito en el gráfico anterior. El informe conserva por hora la última consulta que la abarcó y señala si siguió dentro de la consulta más reciente. El primer instante exacto de publicación se desconoce. Una hora omitida conserva su última lectura conocida para detectar revisiones, y solo un nulo explícito posterior cuenta como retiro. Las tres capturas contienen 62 horas distintas con lectura, cero revisiones de valor y cero retiros. Hace falta confirmar la referencia horaria de la estación antes de calcular la demora absoluta de las lecturas o la anticipación operativa. El contraste histórico encontró desplazamientos distintos según el periodo. [Fuente oficial](https://www.senamhi.gob.pe/site/sea/www/site/sea/graficas/esta_conta.php?estacion=112194&conta=N_PM25) · [Evidencia del reloj](../prueba-externa-pm.md)

## Reproducción

Los originales y sus recibos se guardan localmente en `data/raw/prepiloto-campo-marte-v1`. Desde Neblima, el comando `capture` usa el ejecutable Lightpanda para una consulta acotada de los últimos tres días de calendario. Cada ejecución guarda los bytes y la hora UTC de recepción en un nuevo directorio. Se puede importar una captura previa con `import ROOT RECIBO ORIGINAL`. El informe se reconstruye sin red, contrasta las huellas y distingue ausencias, cambios de valor y retiros dentro del rango que cubre cada consulta.

```sh
R="${AIRAWARE_DATA_DIR:-data}/raw/prepiloto-campo-marte-v1"
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/station_receipts.py audit "$R" \
  --through 2026-11-20T18:02:54.437970+00:00

# Para probar una captura nueva, usar una carpeta separada.
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/station_receipts.py capture "$(mktemp -d)"
```

Los recibos sirven para caracterizar la fuente antes del piloto. La calibración de episodios y el puntaje de la prueba futura usan una cohorte con su elegibilidad y periodo fijados por separado.

## Cierre de las 48 consultas programadas

Al corte del **22/11/2026 a las 18:10 UTC**, bm tenía recibos para **39 de los 48 turnos (81,25 %)** de Campo de Marte. El primer turno, el 20/11 a las 19:05, usó la unidad de usuario `lima-pm25-prepilot-20261120-r2.service`. Desde las 20:05 correspondía `lima-pm25-prepiloto-20261120.service`, con 38 recepciones. Para cada turno se cotejaron la invocación en ambos diarios, la ruta que imprimió el servicio, la marca UTC del recibo y su directorio. En las 43 capturas se verificaron el tamaño y SHA-256 del HTML y se calculó el SHA-256 de los bytes del recibo. Los cuatro recibos anteriores a las 19:05 se conservaron como consultas fuera del calendario. Cada uno de los 39 recibos posteriores quedó vinculado a una sola invocación. [Inventario por turno, horas efectivas y huellas de cada archivo](../../metadata/prepiloto-campo-marte-20261122.json)

Faltaron **nueve turnos consecutivos**, del 21/11 a las 04:05 hasta las 12:05 UTC inclusive. Ninguno tuvo inicio de servicio ni recibo en los diarios disponibles. El registro del arranque previo termina a las 03:24 UTC y el siguiente comienza a las 12:17. El temporizador de usuario volvió a activarse a las 12:17:25 con `Persistent=false`. A las 13:05:01.590925 se recibió la siguiente captura. Este vacío pertenece al registro de bm y no demuestra una caída de SENAMHI.

| Medida al corte | Denominador | Resultado |
|---|---:|---|
| Tiempo del turno programado hasta la recepción local | 39 capturas programadas | Mínimo 1,59 s, mediana 13,47 s, percentil 90 de 14,43 s y máximo 18,94 s |
| Horas con valor finito visto por primera vez durante las consultas previas | 4 capturas | 45, 16, 1 y 0, respectivamente (62 horas) |
| Horas con valor finito visto por primera vez durante el calendario | 39 capturas | 38 capturas aportaron una hora cada una y la del 21/11 a las 13:05 aportó diez (48 horas) |
| Tiempo desde la consulta previa que abarcó la etiqueta y la omitió hasta la primera recepción finita | 48 horas nuevas del calendario | Mínimo 49,27 min, mediana 60,01 min, percentil 90 y máximo 599,94 min. Diez horas comparten el intervalo largo de sondeo |
| Cambios observados después del primer valor | 110 horas con lectura en las 43 capturas | Cero revisiones y cero retiros explícitos |

Las primeras 45 horas ya estaban en la primera captura. Para las otras 65, la consulta previa abarcó la hora pero omitió su etiqueta. Ninguna de ellas había figurado con un nulo explícito. La primera y última recepción programadas fueron el 20/11 a las 19:05:02.037725 y el 22/11 a las 18:05:14.136481 UTC. Los percentiles interpolan linealmente las observaciones ordenadas. Cada hora pesa una vez en la distribución de primeras recepciones, aun cuando varias llegaran en la misma captura.

**La evidencia no permite fijar una espera de maduración para la estación.** La distribución mide el intervalo entre dos consultas en UTC. La página oficial describe datos crudos sin control de calidad y el gráfico identifica horas sin declarar el huso ni qué extremo del promedio horario rotula. El cotejo histórico también encontró desplazamientos distintos según el periodo. Para las 48 horas nuevas, el seguimiento desde su primera recepción hasta la última consulta que aún cubría esa hora tuvo una mediana de 23,50 h y un mínimo de cero. Podrían haberse producido cambios entre capturas o después del corte. El puntaje privado conserva por separado la primera lectura y la última disponible; su interpretación sigue siendo provisional. Para medir demora desde la exposición o emitir avisos operativos quedan pendientes una correspondencia horaria confirmada y evidencia de estabilidad. [Gráfico de SENAMHI](https://www.senamhi.gob.pe/site/sea/www/site/sea/graficas/esta_conta.php?estacion=112194&conta=N_PM25) · [Contraste histórico](../prueba-externa-pm.md) · [Seguimiento de metadatos](https://github.com/keneth-arias/Neblima/issues/43)

### Reproducir el cierre en bm

El conciliador local tiene SHA-256 `60bfdf6b5e64d364ed7ce8b56246625bd68d9983d386c377394fc2d98430a802`. Con los diarios conservados y la carpeta original en la ruta que imprimió systemd, la salida debe coincidir byte por byte con el inventario versionado (SHA-256 `7808a01bd2241a139dca5a542ac44ebfac7d1c0de599b483f27d33952d324707`). Se reprodujeron los cuatro turnos del corte parcial del 20/11 a las 22:10 UTC y los cinco del corte de las 23:10 UTC, incluidas sus huellas y las cuatro recepciones previas.

En bm, exportar solo los registros de las dos unidades con la cuenta que instaló los temporizadores. La copia privada conservada, `diarios-cierre-20261122T181000Z.jsonl`, tiene SHA-256 `8f4aeab99fa94c52475f53e15f7a1f8b38b90050d2c74478d6f492ef3012afa8`. Usarla permite repetir la conciliación después de una rotación del diario.

```bash
journalctl --user -u lima-pm25-prepilot-20261120-r2.service \
  -u lima-pm25-prepiloto-20261120.service -o json --no-pager \
  --since '2026-11-20 19:05:00.000000 UTC' --until '2026-11-22 18:10:00.000000 UTC' \
  > "${TMPDIR:-/tmp}/diarios-cierre-20261122T181000Z.jsonl"
```

Para el cálculo se usó un pod de CPU del perfil local de puntuación de ml-infra, en el espacio `qwen-local-scoring`, con cuenta sin token y sin GPU. Antes de crearlo, comprobar el nodo Ready y los recursos con `kubectl --context microk8s get node bm -o wide` y `kubectl --context microk8s describe node bm`. Copiar al pod la carpeta de recibos en la **misma ruta absoluta** que imprimieron las unidades; en `/tmp/input`, colocar el conciliador local, el diario exportado y la copia del repositorio en `src`. Usar el entorno fijado de `tools/timenet-smoke` (en este ejemplo, `/tmp/.venv`). Desde el pod, este comando verifica los insumos y reproduce la respuesta de la única consulta de diario que hace el conciliador. El pod no requiere acceso al diario general de bm.

```bash
set -eu
cd /tmp/input
sha256sum -c <<'SUMAS'
60bfdf6b5e64d364ed7ce8b56246625bd68d9983d386c377394fc2d98430a802  conciliar_capturas.py
8f4aeab99fa94c52475f53e15f7a1f8b38b90050d2c74478d6f492ef3012afa8  diarios-cierre-20261122T181000Z.jsonl
300948499c6fe4231d49e377913fd2848f13214f6eeff819dc3916becdbc1679  src/tools/timenet-smoke/station_receipts.py
SUMAS
export R=/home/shared/github/keneth-arias/airaware/data/raw/prepiloto-campo-marte-v1
/tmp/.venv/bin/python - <<'PY' > /tmp/cierre.json
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path("src/tools/timenet-smoke").resolve()))
import conciliar_capturas as c

def leer_diario(argumentos):
    esperado = ["journalctl", "--user", "-u", c.UNITS[0], "-u", c.UNITS[1],
                "-o", "json", "--no-pager", "--since", "2026-11-20 19:05:00.000000 UTC",
                "--until", "2026-11-22 18:10:00.000000 UTC"]
    assert argumentos == esperado
    return Path("diarios-cierre-20261122T181000Z.jsonl").read_bytes()

with patch.object(c.subprocess, "check_output", leer_diario):
    print(json.dumps(c.reconcile(Path(os.environ["R"]), c.END), indent=2, sort_keys=True))
PY
cmp /tmp/cierre.json src/metadata/prepiloto-campo-marte-20261122.json
/tmp/.venv/bin/python src/tools/timenet-smoke/station_receipts.py audit "$R" \
  --through 2026-11-22T18:10:00Z > /tmp/cambios.json
/tmp/.venv/bin/python - <<'PY'
import json
from datetime import datetime
from pathlib import Path
from statistics import median, quantiles

cierre = json.loads(Path("/tmp/cierre.json").read_bytes())
cambios = json.loads(Path("/tmp/cambios.json").read_bytes())
turnos = {r["seen_utc"]: t["scheduled_at_utc"] for t in cierre["slots"]
          for a in t["attempts"] for r in a["receipts"]}
primeras = [x for x in cambios["changes"] if x["kind"] == "first_value"
            and x["seen_utc"] in turnos]
def segundos(fin, inicio):
    return (datetime.fromisoformat(fin) - datetime.fromisoformat(inicio)).total_seconds()

for muestra in ([segundos(fin, inicio) for fin, inicio in turnos.items()],
                [segundos(x["seen_utc"], x["previous_check_utc"]) for x in primeras],
                [segundos(cambios["coverage_by_station_hour"][x["station_hour"]]["last_queried_utc"],
                          x["seen_utc"]) for x in primeras]):
    print(len(muestra), min(muestra), median(muestra),
          quantiles(muestra, n=10, method="inclusive")[8], max(muestra))
PY
```

## Puntaje provisional durante la emisión privada

Para cada pronóstico de +1 a +6 horas, el puntaje empareja Qwen y persistencia con la misma medición de Campo de Marte. Presenta dos vistas al corte elegido. La primera conserva la primera lectura recibida estrictamente después de emitir. La última incorpora las correcciones disponibles y excluye del denominador una lectura retirada. Si ya se conocía el objetivo al emitir, ninguna de las vistas lo usa. Un campo de error o cobertura vacío indica que todavía faltan pares para calcularlo.

El informe muestra pares y horas objetivo distintas, error absoluto medio en µg/m³, cobertura y amplitud del intervalo del 80 %, tanto globalmente como por horizonte. El tiempo hasta la primera recepción se mide entre las marcas UTC de emisión y llegada. La etiqueta horaria del gráfico identifica el objetivo. La interpretación de anticipación respecto de la exposición sigue pendiente de la correspondencia entre el reloj del gráfico y UTC.

En bm, el comando usa las emisiones privadas y los recibos operativos guardados. El corte incluye las observaciones recibidas y las emisiones publicadas hasta ese instante. El puntaje coteja la última lectura del origen con la versión que ya estaba disponible al corte de insumos de cada emisión. Las huellas de ambos conjuntos permiten reproducir el informe. El servicio publica cada JSON de emisión de forma atómica y conserva sus bytes. Un archivo ilegible en esa carpeta interrumpe la verificación. Para repetir un corte anterior también deben conservarse los archivos de emisión legibles. Una carpeta vacía de emisiones da cero pronósticos. Si las emisiones al corte corresponden a dos generaciones del modelo, el comando interrumpe el cálculo para evitar mezclar sus resultados. Los datos conservarán su carácter provisional mientras se evalúa la maduración de la fuente.

```bash
D="${AIRAWARE_DATA_DIR:-/home/shared/github/keneth-arias/airaware/data}"
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/live_concentration_scores.py \
  "$D/processed/evaluacion-inmediata-campo-marte-20261120/en-vivo/issuances" \
  "$D/raw/campo-marte-operativo-20261120" --through 2026-11-20T21:00:00+00:00
```

El servicio horario de bm actualiza `en-vivo/puntaje-por-horizonte.json` después de procesar la consulta. La etiqueta `latest_live_horizon_report` de la primera corrida de emisión en MLflow identifica el archivo privado correspondiente al último corte procesado. Cada archivo conserva su huella en el nombre. Las horas sin medición quedan pendientes.

En bm se puede inspeccionar el comando instalado con `systemctl --user show lima-pm25-pronostico-privado-20261120.service -p ExecStartPost`. El publicador local `operacion/publicar_puntaje.py` toma como corte el instante UTC más reciente entre la última consulta procesada y la última emisión. Para reproducir una versión concreta, descargar el archivo identificado por la etiqueta de MLflow en una ruta privada y usar su propio corte. El comando siguiente compara todos los bytes con esa copia guardada.

```bash
D="${AIRAWARE_DATA_DIR:-/home/shared/github/keneth-arias/airaware/data}"
F=/ruta/privada/al/puntaje-horario-descargado.json
CORTE=$(jq -er .through_utc "$F")
set -o pipefail
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/live_concentration_scores.py \
  "$D/processed/evaluacion-inmediata-campo-marte-20261120/en-vivo/issuances" \
  "$D/raw/campo-marte-operativo-20261120" --through "$CORTE" | cmp - "$F"
```
