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
