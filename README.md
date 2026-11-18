# AirAware Perú

Proyecto de ingeniería de datos de calidad del aire para Lima, Callao y el Perú. Participamos en el
[hackathon de TimeNet](https://challenge.timenet.ai/). El primer caso de uso es pronosticar PM2.5
usando mediciones reales. Participamos como el equipo **Cuybernautas**. Keneth Arias (`@keneth-arias`) lidera datos y plataforma.

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

El [catálogo](configs/sources.yaml) registra 40 recursos candidatos, con evidencia y
bloqueos por fuente. El flujo local de SENAMHI normaliza, depura, alinea y exporta
[338 892 tareas TimeF de PM2.5](docs/dataset-cards/lima-pm25-forecast.md) con 24 horas
de historia, seis horas de horizonte y particiones cronológicas. La integración
continua reproduce la cadena con datos sintéticos y la red deshabilitada.

La evaluación ya tiene [tres referencias](reports/baselines/lima-pm25.md) sobre el conjunto
congelado. Validación seleccionó persistencia. El trabajo del modelo temporal se sigue en
[#27](https://github.com/keneth-arias/airaware/issues/27) y [#28](https://github.com/keneth-arias/airaware/issues/28).
El conector de Cuybernautas está en [revisión como borrador de TimeNet](https://github.com/OpenTSLM/TimeNet/pull/796).

La [adquisición meteorológica de #16](reports/acquisition/weather.md) habilita el análisis
de una semana de pronósticos archivados. Su cobertura queda dentro de entrenamiento,
por lo que la [alineación en revisión](https://github.com/keneth-arias/airaware/pull/85)
sirve para comprobar contratos y procedencia. La comparación de modelos de la primera
ronda usa la versión congelada de PM2.5.

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
