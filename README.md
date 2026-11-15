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

La base del proyecto valida 37 recursos candidatos, prepara las carpetas locales y revisa el entorno.
Todas las fuentes siguen pendientes de verificación. Todavía no se han recolectado observaciones
ambientales. La descarga, el análisis de calidad, la normalización, la exportación TimeF y el
entrenamiento están en las tareas siguientes.

## Organización y próximos pasos

- `configs/sources.yaml`: inventario vigente; [campos y estados](docs/sources.md).
- `src/airaware/` y `tests/`: herramientas locales y pruebas sin servicios externos.
- `data/`: datos originales, intermedios, normalizados, depurados, conjuntos de evaluación y TimeF.
  Los archivos de datos no se suben a Git.
- `metadata/*.csv`: plantillas iniciales de columnas; no son exportaciones TimeNet.
- `docs/`: metodología, decisiones y guías del equipo.
- `.github/`: integración continua (CI), responsables y plantillas de tareas y PR.

Empiecen por verificar SENAMHI en [#4](https://github.com/keneth-arias/airaware/issues/4) y OEFA en
[#5](https://github.com/keneth-arias/airaware/issues/5). Implementen la descarga antes de recolectar datos.
El [plan vigente](tasks/plan.md), el [tablero](https://github.com/users/keneth-arias/projects/1) y las
[tareas](https://github.com/keneth-arias/airaware/issues) muestran el trabajo pendiente.
La [arquitectura](ARCHITECTURE.md) diferencia lo implementado de lo propuesto.
El [plan inicial completo](docs/initial-plan.md) también está adaptado al español. Sus comandos
propuestos aún no están implementados. El texto original se conserva en el historial de Git.

No subas credenciales ni datos masivos. Verifica las licencias antes de redistribuir datos.
Que el repositorio sea público no concede derechos sobre las fuentes. El código propio se distribuye bajo
[AGPL-3.0-only](LICENSE); consulta [la decisión y los límites para TimeNet](docs/decisions/003-licencia-agpl-v3.md).
No se atribuye una licencia a los datos candidatos.
