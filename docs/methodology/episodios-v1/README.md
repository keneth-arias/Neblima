# Ejemplo de intercambio para episodios de seis horas

Estas cinco ventanas son inventadas. Los dos umbrales son constantes ilustrativas y las fechas separan casos independientes. La carpeta `inferencia` contiene únicamente información conocida al origen. La carpeta `evaluacion` guarda las seis observaciones posteriores y el resultado esperado por ID, en un orden distinto.

| ID | Caso | Resultado esperado |
| --- | --- | --- |
| w1 | Alcanza el umbral en +1 h | Positivo, inicio anticipable. |
| w2 | Episodio de más de seis horas, activo en el origen | Positivo, sin crédito por anticipación. |
| w3 | Alcanza exactamente el umbral en +6 h | Positivo, inicio anticipable en el límite. |
| w4 | Falta +3 h, se supera el umbral en +6 h | Indeterminado bajo la regla de seis objetivos completos. |
| w5 | Misma historia y mismos objetivos que w1, umbral de otra estación | Negativo. |

Verificar los resultados con `uv run --locked pytest -q tests/test_ejemplo_episodios.py` en la raíz de AirAware. Para preparar el archivo de inferencia del cabezal directo, ejecutar desde esa raíz con una ruta de salida nueva.

```sh
uv run --project tools/timenet-smoke --locked python - <<'PY'
import json
from pathlib import Path
import numpy as np

inputs = json.loads(Path("docs/methodology/episodios-v1/inferencia/ventanas.json").read_text())
with open("history.npz", "xb") as output:
    np.savez(output, window_id=inputs["window_id"], history=np.asarray(inputs["history"], dtype=np.float32))
PY
```

OpenTSLM recibe `history.npz` con `--require-history-only`. Se esperan cinco filas en orden w4, w1, w5, w2, w3 y seis columnas para las horas +1 a +6; comparar las predicciones antes y después de restaurar el mismo punto de control. El modelo experimental de episodios recibirá también un vector `threshold_ug_m3` en unidades originales, en el mismo orden que los IDs, mediante su esquema versionado. Este ejemplo comprueba la interfaz. Para medir calibración hacen falta bloques independientes con suficientes eventos.

## Casos de aceptación para la regla de aviso

Cada fila es un escenario independiente en una estación. Las horas son relativas al primer origen; el cotejo en el piloto utilizará la emisión efectiva.

| Escenario | Intentos y observaciones | Resultado esperado |
| --- | --- | --- |
| Reintento | Dos disparos para el mismo origen 0, inicio en +2 | Una emisión, un acierto, dos horas de anticipación si se emitió en 0. |
| Pausa | Intentos en 0 y +2, inicio en +4 | Cuenta el aviso en 0. El segundo intento queda suprimido. |
| Dos inicios | Un aviso en 0, inicios en +2 y +5 separados por una hora baja | Se anticipa el primero. El segundo queda omitido. |
| En curso | Última hora medida alta al emitir | Mostrar estado en curso y contabilizar el origen aparte. |
| Seguimiento incompleto | Un aviso en 0, falta la lectura en +3 | Un aviso indeterminado. |
| Ningún inicio | Un aviso en 0, seis objetivos bajo el umbral | Un aviso falso. |
| Demora | Cálculo nominal en 0, inicio en +2 y emisión efectiva en +3 | Cero aciertos anticipados para ese inicio. Consignar la demora. |

## Repetición del aviso y puntuación

El siguiente comando aplica a las cinco historias sintéticas una regla que siempre propone un aviso cuando la última lectura está por debajo del umbral. Cada inicio puede acreditarse una sola vez. Se obtienen dos aciertos, un falso y un aviso de seguimiento incompleto. La estación con episodio en curso produce un estado. Los resultados comprueban la contabilidad de la regla.

```sh
uv run --locked python -m airaware.episode_warnings \
  docs/methodology/episodios-v1/inferencia/ventanas.json \
  docs/methodology/episodios-v1/evaluacion/objetivos.json
```

`Pilot` en `airaware.pilot_issue` registra las revisiones horarias de una serie en SQLite. Una clave de fuente debe identificar inequívocamente proveedor, sensor, estación y escala temporal. La primera transacción por fuente, estación y origen fija el insumo y el modelo. La publicación posterior conserva la hora efectiva y el resultado. La maduración cierra la cohorte en origen + seis horas + demora declarada. La prueba de integración incluye una lectura tardía, reinicio de proceso, corte sin datos, conflicto de modelo y corrección posterior al cierre. El responsable de la fuente debe fijar la demora según llegadas observadas antes de usarla en el piloto.

En el entorno bloqueado de TimeF, `episode_quantiles.py` compara en selección la mediana y los intervalos del candidato con el directo congelado. Verifica IDs, niveles y huellas. El desglose por estación y las diferencias de MAE, cobertura y amplitud incluyen el estrato alto. El remuestreo empareja ambos métodos por bloques calendario de 84, 168 y 336 horas. Para puntuar el clasificador, `episode_calibration.py` admite `--episode-logits NPZ SHA256 MANIFIESTO MANIFIESTO_SHA256` en ajuste y aplicación. La revisión de #20 y #43 sigue siendo necesaria para usar etiquetas de episodios reales.

El [protocolo de comparación de cuantiles](../../../configs/training/lima-comparacion-cuantiles-v1.yaml) se fijó durante el entrenamiento, antes de producir pronósticos de selección de estos candidatos. Se comparan las medias de dos semillas emparejadas. La referencia permanece si el candidato empeora el MAE global, no reduce el MAE en horas altas, queda fuera de ±5 puntos de la cobertura global nominal o no acerca la cobertura en horas altas a ese objetivo. El resultado frente al único punto de control histórico de #28 es descriptivo. La repetición no autoriza el piloto.
