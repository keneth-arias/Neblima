# AirAware Perú

Proyecto de ingeniería de datos de calidad del aire para Lima, Callao y el Perú. Participamos en el
[hackathon de TimeNet](https://challenge.timenet.ai/). El primer caso de uso es pronosticar PM2.5
usando mediciones reales. Keneth Arias (`@keneth-arias`) lidera datos y plataforma.

El idioma de trabajo del equipo es el **español del Perú**. La documentación, las tareas y los PR se
redactan en español claro. Los comandos, identificadores y nombres técnicos conservan su forma original.

## Empieza en tu equipo

Instala Git, Make y [uv](https://docs.astral.sh/uv/getting-started/installation/). Desde la carpeta raíz:

```bash
uv python install
make setup
make init
make doctor
make check
```

Usamos Python 3.13.13 y dependencias fijadas en `uv.lock`. La instalación descarga herramientas;
las pruebas y la validación del catálogo funcionan sin internet después de la instalación.
Para estos comandos no necesitas servicios de pago ni claves de proveedores.
Consulta [cómo contribuir](CONTRIBUTING.md) para generar el paquete y revisar dependencias.

```bash
uv run --locked airaware catalog validate
uv run --locked airaware workspace init
uv run --locked airaware doctor
```

`AIRAWARE_DATA_DIR` permite elegir otra carpeta de datos. El archivo `.env` no se carga automáticamente.
Revisa la [guía del responsable](docs/lead-handbook.md), los [servicios](docs/services.md),
la [guía de inicio del equipo](docs/team-onboarding.md) y la [distribución de tareas](docs/team-work-allocation.md).

Si recién empiezas, consulta el [glosario práctico](docs/glossary.md).

## Qué funciona hoy

La base del proyecto valida 38 recursos candidatos, prepara las carpetas locales y revisa el entorno.
Los 37 recursos iniciales tienen revisión documental con Lightpanda y bloqueos registrados.
El candidato adicional EAS_Aire fue verificado documentalmente con Lightpanda e importado desde una
copia aportada por Keneth; [adquisición y límites](reports/acquisition/oefa-eas-aire.md). El CSV SENAMHI
ya se descargó localmente y pasó una comprobación estructural; sus unidades, calidad y derechos
siguen en revisión. Consulta [el inventario y la evidencia](docs/sources/inventory-review.md).
El [perfilamiento local](docs/profiling.md) mide cobertura y calidad sin modificar originales.
La normalización, la exportación TimeF y el entrenamiento siguen pendientes.

La [prueba sintética de TimeNet](tools/timenet-smoke/README.md) ya se ejecutó en un entorno aislado.
El conjunto hello-world está en data/timef; no contiene observaciones ambientales reales.

## Organización y próximos pasos

- `configs/sources.yaml`: inventario vigente; [campos y estados](docs/sources.md).
- `src/airaware/` y `tests/`: herramientas locales y pruebas sin servicios externos.
- `data/`: datos originales, intermedios, normalizados, depurados, conjuntos de evaluación y TimeF.
  Los archivos de datos no se suben a Git.
- `metadata/*.csv`: plantillas iniciales de columnas; no son exportaciones TimeNet.
- `docs/`: metodología, decisiones y guías del equipo.
- `.github/`: integración continua (CI), responsables y plantillas de tareas y PR.

SENAMHI y OEFA ya tienen originales locales verificados (#8/#9). Consulten los
[resultados de perfilamiento](reports/profiling.md) para preparar la selección de #11. Sigan el [protocolo Lightpanda](docs/web-access.md) y la [guía de adquisición](docs/acquisition.md).
La CLI acquire de #6 ya registra originales y consulta API públicas explícitas con integridad;
caché, reanudación y lotes acotados se describen en la guía de adquisición (#7).
El [plan vigente](tasks/plan.md), el [tablero](https://github.com/users/keneth-arias/projects/1) y las
[tareas](https://github.com/keneth-arias/airaware/issues) muestran el trabajo pendiente.
La [arquitectura](ARCHITECTURE.md) diferencia lo implementado de lo propuesto.
El [plan inicial completo](docs/initial-plan.md) también está adaptado al español. Sus comandos
propuestos aún no están implementados. El texto original se conserva en el historial de Git.

No subas credenciales ni datos masivos. Verifica las licencias antes de redistribuir datos.
Que el repositorio sea público no concede derechos sobre las fuentes. El código propio se distribuye bajo
[AGPL-3.0-only](LICENSE); consulta [la decisión y los límites para TimeNet](docs/decisions/003-licencia-agpl-v3.md).
No se atribuye una licencia a los datos candidatos.
