# Verificación local de TimeNet con hello-world

Entorno independiente de la aplicación AirAware. Instala timenet y timenet-connectors desde el
commit `9bd1613019ee61fbc52e02106a1a45990ead7a54`, con dependencias fijadas en su propio uv.lock.
No instala PyTorch ni cambia el entorno principal. La primera instalación requiere internet.
Los datos sintéticos generados conservan CC-BY-4.0 según la ficha del conector; no son datos de Lima
ni quedan cubiertos automáticamente por la AGPL del código de AirAware.

## Construir en la carpeta de datos del proyecto

Ejecutar desde la raíz de AirAware:

```bash
uv sync --project tools/timenet-smoke --python 3.13.13 --locked

TIMENET_CACHE="$PWD/data/cache/timenet" \
UV_OFFLINE=true \
uv run --project tools/timenet-smoke --locked timenet-build build \
  timenet/hello-world@1.0.0 \
  --local-registry "$PWD/data/timef" \
  --remote-registry "$PWD/data/timef" \
  --no-isolation
```

`--no-isolation` evita que TimeNet cree un segundo entorno para el conector: el comando ya se ejecuta
en el entorno aislado de esta carpeta. Ambos registros apuntan a la carpeta local. El ejemplo es
sintético y no descarga observaciones. No usar `--force` para reemplazar versiones existentes.

## Leer y verificar con el SDK

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python - <<'PY'
from pathlib import Path
import timenet
from timenet.reader import TimeFReader
from timenet.registry import LocalRegistry

registry = Path.cwd() / "data/timef"
release = registry / "timenet/hello-world/1.0.0"
with TimeFReader.open(release) as reader:
    reader.verify()
    dataset = reader.read()
    expected = dataset.records[0].signals[0].to_arrow().slice(0, 8).to_pylist()

client = timenet.TimeNet(sources=[LocalRegistry(registry)])
dataset = client.load("timenet/hello-world", version="1.0.0")
assert dataset.records[0].signals[0].to_arrow().slice(0, 8).to_pylist() == expected
print("Registros:", len(dataset.records), "Tareas:", len(dataset.tasks))
PY
```

## Resultado ejecutado el 15/11/2026

- Construcción oficial y verificación de archivos aprobadas.
- Lectura con TimeFReader y carga con TimeNet desde LocalRegistry aprobadas; valores comparados.
- Proveniencia instalada comprobada mediante direct_url.json: ambos paquetes usan el commit fijado.
- Tres registros, cinco señales y cinco tareas; archivos de la versión: 4 478 280 bytes.
- Versión: `data/timef/timenet/hello-world/1.0.0/`.
- Informe de la ejecución: `data/timef/hello-world-validation.json`, con fecha, paquetes, controles,
  conteos, tamaños y SHA-256 de cada archivo. El bloque de lectura anterior verifica el conjunto,
  pero no regenera por sí solo ese informe detallado.

Los datos, el informe de ejecución y .venv están excluidos de Git. La configuración y uv.lock sí se
versionan para reproducir el entorno. La carpeta `data/timef` será el registro local para otros
conjuntos; los originales de SENAMHI irán en `data/raw/senamhi` cuando se implemente su adquisición.
Esta prueba no sustituye la validación del futuro conector SENAMHI ni ejecuta la suite de TimeNet.

Referencia: [guía oficial en la revisión fijada](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/docs/get-started.md).

## Ida y vuelta horaria de PM2.5 para #21

Después de instalar el entorno fijado, ejecutar desde la raíz de AirAware:

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked \
  python tools/timenet-smoke/test_senamhi_timef.py
```

La prueba crea un registro sintético con una identidad provisional, un origen de reloj
absoluto en tiempo universal coordinado (UTC) y un paso de una hora. Escribe con
`TimeFDataset.write`, verifica con `TimeFReader.verify()` y compara los cuatro valores
con Arrow. Conserva un cero, un nulo, valores con doble precisión, la unidad tipada
en µg/m³ y un ejemplo de procedencia. El registro y el archivo temporal son sintéticos.
Los metadatos reales, la atribución y la verificación del Parquet se incorporan en la
segunda entrega de #21.

## Muestra local real de SENAMHI

Con las dependencias de ambos entornos instaladas y el Parquet de #13 disponible:

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked \
  python tools/timenet-smoke/export_senamhi.py \
  --normalized data/normalized/senamhi/senamhi-normalization-20261117-v1 \
  --registry data/timef \
  --station-key 2a0d574b25a5dc8c7f6edda9836225860faaa160763d8bea15d95646794f0bd8 \
  --start 2024-05-01T00:00:00Z --hours 24
```

La conversión ejecuta la depuración y la alineación locales en el entorno AirAware
para verificar los archivos y la traza de #13. El registro base de muestra es
`airaware/senamhi-lima-pm25-sample@0.1.0`. El reloj conserva las etiquetas UTC
publicadas. La unidad tipada sigue siendo una inferencia aprobada y tanto la posición
del intervalo como la calidad de las lecturas siguen desconocidas. Los nulos proceden
de la grilla, con identificadores de auditoría por casilla. La licencia de datos figura
como `ODC-By-1.0` en TimeNet y la atribución acompaña la versión.

En la verificación real se conservaron 19 valores finitos y cinco nulos por conflicto.
La grilla de PM2.5 carece de ceros medidos y la prueba sintética cubre el cero. Una
copia de la normalización con la traza alterada se rechazó antes de publicar el registro.
Dos ejecuciones en registros nuevos aprobaron `TimeFReader.verify()` y
`LocalRegistry`. Coincidieron la identidad, el reloj, los valores Arrow y la procedencia.
Las sumas SHA-256 de los manifiestos fueron
`0c457bc4b7452da794c3980c1681e4d3c0d361d0073babf72a38f40929724371` y
`dbb6f2c621c4bde20ee571eb2f2db49800ca15783b91a6e96af8e673c16e9d42`.
La diferencia se limita a la suma del archivo de control DuckDB que escribe TimeNet.

## Reproducción de extremo a extremo de #23

Instalar los entornos desde la raíz. La instalación puede acceder a sus fuentes de
dependencias. La prueba se ejecuta después en un espacio de red aislado de Linux y
con los permisos del usuario de trabajo.

```bash
uv sync --locked
uv sync --project tools/timenet-smoke --python 3.13.13 --locked
sudo -n --preserve-env=HOME,PATH,UV_CACHE_DIR unshare --net \
  --setuid "$(id -u)" --setgid "$(id -g)" -- make test-timef-offline
```

El objetivo ejecuta las pruebas aisladas del kit de desarrollo de TimeNet y verifica
estilo y formato de sus scripts. La prueba de extremo a extremo crea un CSV ficticio
de 73 filas con un cero, un nulo y un conflicto. Importa el original, verifica su
suma, normaliza, depura, alinea, genera ventanas, purga cruces y escribe TimeF.
`TimeFReader.verify()` y `LocalRegistry` comprueban la versión. Se comparan valores,
identificadores, reloj y particiones de todas las tareas ficticias. Una copia de
particiones alterada se rechaza antes de escribir otra versión.

En un checkout limpio con entornos fijados, el comando aprobó cuatro pruebas
en 3,03 s y usó hasta 203 920 KiB de memoria residente. El control de integración
continua registra esos recursos por ejecución. La auditoría de dependencias se
ejecuta aparte con acceso a su servicio de alertas. La corrida local principal
también aprobó 345 pruebas, el empaquetado y la auditoría.

## Exportación histórica de PM2.5 y PM10

Desde la raíz, indicar el directorio de la versión histórica y un destino nuevo en disco local.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python \
  tools/timenet-smoke/export_qwen_windows.py "$release" "$salida" --joint
```

El manifiesto fija las huellas de las matrices de entrenamiento y validación, de sus identificadores y de `scaler.json`. El orden de los canales de historia y objetivos es `pm25, pm10`. `origin_hour` cuenta horas desde 1970-01-01 00:00 UTC. El escalador y los percentiles 95 por estación usan las 268 567 horas de estación distintas presentes en las historias de entrenamiento. Las matrices mantienen las concentraciones publicadas, incluido el cero. [Evidencia de la exportación](../../metadata/ventanas-pm25-pm10-entrenamiento.json)

## Verificar el ajuste pareado de #88

`joint_validation.py` recibe las matrices históricas, las carpetas de los dos ajustes (A y B), dos exportaciones independientes de inferencia desde los estados restaurados y una carpeta nueva de salida. La reconstrucción de A puede recibir toda la historia de PM10 enmascarada. Ambas exportaciones deben contener exactamente las mismas predicciones por ventana que en la primera restauración.

Para reproducir la prueba de A, crear los dos insumos de inferencia desde la misma validación. El siguiente comando recibe la carpeta de matrices exportadas y una carpeta de salida nueva. Conserva los identificadores en su orden original y excluye los objetivos.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python - "$matrices" "$historias" <<'PY'
import sys
from pathlib import Path
import numpy as np

matrices, salida = map(Path, sys.argv[1:])
salida.mkdir()
with np.load(matrices / "validation.npz", allow_pickle=False) as datos:
    for vista in ("both", "first"):
        historia = datos["history"]
        if vista == "first":
            historia[:, :, 1] = np.nan
        np.savez(salida / f"{vista}.npz", window_id=datos["window_id"],
                 channels=datos["channels"], history=historia)
PY
```

En el perfil de entrenamiento de SkyPilot, ejecutar este comando una vez por variante (`first` para A y `both` para B), con la carpeta del ajuste correspondiente en `$ajuste`. El perfil monta `gpu_worker.py` en `/opt/airaware` para aplicar el presupuesto de memoria de la GPU también durante la inferencia. Las revisiones de los pesos base y del entrenador figuran en la [configuración congelada](../../configs/training/lima-pm25-pm10-ajuste-v1.json).

```bash
PYTHONPATH=/opt/forecast/src /opt/conda/bin/python /opt/airaware/gpu_worker.py \
  -m opentslm.forecast_inference \
  --input-view "$vista" --data "$historias/$vista.npz" --scaler "$matrices/scaler.json" \
  --checkpoint "$ajuste/step-00015745" --weights /inputs/qwen/weights --batch 16 \
  --output "$ajuste/replay-validation.npz"
```

Desde la raíz de AirAware, comparar los cuatro archivos de predicciones y generar el informe numérico.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python \
  tools/timenet-smoke/joint_validation.py "$matrices" "$ajuste_a" "$ajuste_b" \
  "$ajuste_a/replay-validation.npz" "$ajuste_b/replay-validation.npz" "$salida"
```

El verificador coteja el último paso, las sumas de los archivos del estado, el registro efectivo de lotes, el escalador y las concentraciones del conjunto congelado. `paired.parquet` permite revisar cada par de errores. `metrics.json` desglosa por contaminante, estación, horizonte y concentración alta. `freeze.json` identifica ambos modelos y los archivos verificados. La entrada de evaluación es exclusivamente la partición histórica de validación.

Si el nodo se apaga durante el ajuste, el archivo de eventos puede terminar en bytes NUL después de la última línea JSON completa. El verificador registra el nombre, el SHA-256 del archivo original y la cantidad de esos bytes en `recovered_log_tails`. Una línea JSON incompleta o dañada interrumpe la verificación. Para congelar el modelo, todos los pasos deben estar documentados y cada lote repetido después de reanudar debe conservar los mismos identificadores y la misma tasa de aprendizaje.
