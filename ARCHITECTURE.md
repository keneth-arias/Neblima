# Arquitectura inicial de AirAware

AirAware tendrá una secuencia reproducible de descarga, revisión y preparación de observaciones.
Un conector mínimo para TimeNet convertirá las versiones aprobadas usando las API oficiales de TimeF.
Actualmente solo están implementados el entorno local, la validación del catálogo y el diagnóstico.
Todavía no hay descarga ni procesamiento científico de datos.

## Componentes actuales

- `src/airaware/catalog.py`: contrato de fuentes con Pydantic y lectura segura de YAML.
  Un valor nulo indica información desconocida.
- `src/airaware/cli.py`: comandos sin acceso a red; los errores no muestran valores de configuración.
- `configs/sources.yaml`: 37 recursos candidatos del plan inicial, aún sin verificar.
- `configs/upstream.lock.json`: revisiones externas inspeccionadas; no instala el SDK.
- `uv.lock`: dependencias exactas del proyecto y de desarrollo. Python se fija por separado.
- `.github/workflows/ci.yml`: instalación, controles, generación de paquetes y auditoría de dependencias.

## Flujo propuesto de datos

`raw` (archivos originales inmutables) → `staging` (lectura por fuente) → `normalized` (Parquet con
esquema común) → `curated` (observaciones compatibles y sin duplicados) → `benchmarks` (ventanas y
particiones fijas de evaluación) → `timef` (salida del escritor oficial).

`AIRAWARE_DATA_DIR` elige la carpeta de datos; por defecto es `./data` desde la ubicación actual.
Ejecuta los comandos desde la raíz del repositorio. Git ignora los datos y conserva solo marcadores.
Si usas otra carpeta, evita ubicarla dentro de un repositorio ajeno. Cada descarga deberá registrar
URL, fecha, SHA-256, parámetros y derechos de uso.

## Decisiones

Empezamos con archivos locales y añadiremos herramientas analíticas cuando sean necesarias.
No se configura ahora un servicio de base de datos, orquestación, almacenamiento remoto ni modelos.
Consulta [ADR-001](docs/decisions/001-local-first-foundation.md), la [política de idioma](docs/decisions/002-espanol-peru.md)
y las [notas de TimeNet](docs/timenet-integration.md).
