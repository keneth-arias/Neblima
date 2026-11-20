# AirAware Perú

Proyecto de ingeniería de datos de calidad del aire para Lima, Callao y el Perú. Participamos en el
[hackathon de TimeNet](https://challenge.timenet.ai/). El primer caso de uso es pronosticar PM2.5
usando mediciones reales. Participamos como el equipo **Cuybernautas**. Keneth Arias (`@keneth-arias`) lidera datos y plataforma.

El idioma de trabajo del equipo es el **español del Perú**. La documentación, las tareas y los PR se
redactan en español claro. Los comandos, identificadores y nombres técnicos conservan su forma original.

## Mapa de las siete estaciones de Lima

Selecciona un marcador para ver el nombre de la estación. Las ubicaciones históricas son
referenciales porque el archivo original no declara el sistema de referencia de las coordenadas.
[Fuente y licencia del Servicio Nacional de Meteorología e Hidrología del Perú](DATA_ATTRIBUTION.md).

```geojson
{
  "type": "FeatureCollection",
  "features": [
    {"type": "Feature", "id": "CAMPO_DE_MARTE", "properties": {"Estación": "Campo de Marte"}, "geometry": {"type": "Point", "coordinates": [-77.0432, -12.0705]}},
    {"type": "Feature", "id": "CARABAYLLO", "properties": {"Estación": "Carabayllo"}, "geometry": {"type": "Point", "coordinates": [-77.0336, -11.9022]}},
    {"type": "Feature", "id": "SANTA_ANITA", "properties": {"Estación": "Santa Anita"}, "geometry": {"type": "Point", "coordinates": [-76.9714, -12.043]}},
    {"type": "Feature", "id": "SAN_BORJA", "properties": {"Estación": "San Borja"}, "geometry": {"type": "Point", "coordinates": [-77.0077, -12.1086]}},
    {"type": "Feature", "id": "SAN_JUAN_DE_LURIGANCHO", "properties": {"Estación": "San Juan de Lurigancho"}, "geometry": {"type": "Point", "coordinates": [-76.9992, -11.9816]}},
    {"type": "Feature", "id": "SAN_MARTIN_DE_PORRES", "properties": {"Estación": "San Martín de Porres"}, "geometry": {"type": "Point", "coordinates": [-77.0845, -12.0089]}},
    {"type": "Feature", "id": "VILLA_MARIA_DEL_TRIUNFO", "properties": {"Estación": "Villa María del Triunfo"}, "geometry": {"type": "Point", "coordinates": [-76.92, -12.1664]}}
  ]
}
```

### Insertar el mapa en tu sitio

Crea una carpeta `mapas/` junto a la página que mostrará el mapa y copia allí
[estaciones.html](web/estaciones.html). Inserta este bloque en esa página. La ruta relativa
también funciona si el sitio se publica en una subcarpeta.

```html
<iframe src="./mapas/estaciones.html" title="Siete estaciones de calidad del aire en Lima"
  height="720" loading="lazy" style="display: block; width: 100%; border: 0"></iframe>
```

El navegador carga Leaflet desde `unpkg.com` y el fondo de OpenStreetMap desde
`tile.openstreetmap.org`. La integración funciona sin compilación ni claves. Los enlaces de las estaciones
también funcionan sin JavaScript. Las ubicaciones provienen de la sección `stations` de
[la configuración de alineación](configs/weather-alignment.yaml). Conserva los créditos del mapa
y el [aviso de atribución de los datos](DATA_ATTRIBUTION.md) al integrarlo.

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
por lo que la [alineación retrospectiva integrada](https://github.com/keneth-arias/airaware/pull/85)
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
