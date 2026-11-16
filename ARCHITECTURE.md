# Arquitectura inicial de AirAware

AirAware tendrá una secuencia reproducible de descarga, revisión y preparación de observaciones.
Un conector mínimo para TimeNet convertirá las versiones aprobadas usando las API oficiales de TimeF.
Están implementados el entorno local, catálogo, diagnóstico y adquisición acotada de #6.
Lightpanda consulta páginas/recursos web; la CLI registra originales o consulta API públicas explícitas.
SENAMHI se preserva localmente; no hay todavía normalización ni procesamiento científico de producción.

## Componentes actuales

- `src/airaware/catalog.py`: contrato de fuentes con Pydantic y lectura segura de YAML.
  Un valor nulo indica información desconocida.
- `src/airaware/cli.py`: catálogo, entorno y entrada al grupo acquire; errores sin valores de configuración.
- `src/airaware/acquisition/`: contrato, validación de formatos, almacenamiento atómico, transporte API
  y CLI; [guía y límites](docs/acquisition.md). La red está separada de la normalización.
- `configs/sources.yaml`: 37 recursos con evidencia de revisión y bloqueos conservados.
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

## Contratos confirmados al ejecutar la tarea #1

La [revisión de código](docs/timenet-integration.md) vincula cada contrato a un commit y una prueba
fuente inspeccionada. Se mantiene la revisión 9bd1613 de TimeNet: no hay actualización de dependencias.

- El conector externo separará download/download_async de convert/compose. La secuencia independiente
  de AirAware no dependerá del registro de TimeNet para adquirir o normalizar sus fuentes.
- Las series usarán origen y ejes temporales físicos verificados; OrdinalAxis de TSQA no se trasladará
  directamente a mediciones con fecha/hora. El esquema y la granularidad final se fijan en #12.
- Las tareas contendrán la partición; #19 debe comprobar que sus entradas/objetivos no se superpongan
  indebidamente. El SDK no determina por nosotros los límites cronológicos ni la disponibilidad de variables.
- La clasificación exige LabelSet. Los objetivos escalares pueden usar ScalarPredictionTask y unidad;
  el pronóstico temporal y las respuestas usan sus tipos propios. No inventar parámetros de ventana.
- Se preservarán los valores nulos y máscaras. La conversión a NumPy/PyTorch requiere preparación
  explícita; no se reparan observaciones silenciosamente para satisfacer al formato.
- Las bases por fuente seguirán separadas cuando difieran derechos o significado. La composición
  fijará padres y mantendrá trazabilidad y archivos requeridos; su lectura/escritura se probará en #21–#23.
- Los ayudantes de descarga de TimeNet son referencia para #6, no un reemplazo ya aprobado de los
  manifiestos, controles de contenido, caché verificable y límites que necesita AirAware.

No apareció una contradicción bloqueante en los contratos examinados. El código propio usa AGPL-3.0-only
por decisión de Keneth; la inspección de MIT de TimeNet no concede derechos sobre datos externos.
La contribución MIT externa necesita revisar autoría y permisos por separado según
[ADR-003](docs/decisions/003-licencia-agpl-v3.md).
