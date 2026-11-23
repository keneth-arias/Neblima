# Atribución de los datos SENAMHI

Fuente: Servicio Nacional de Meteorología e Hidrología del Perú — SENAMHI.
Conjunto: **Monitoreo de los contaminantes del aire en Lima Metropolitana**.

- [Catálogo y aviso de licencia](https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de).
- Licencia de la base: [Open Data Commons Attribution License v1.0 (ODC-BY-1.0)](https://opendatacommons.org/licenses/by/1-0/).
- Original identificado por SHA-256: 896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4.
- Adquisición y fecha: metadata/senamhi-lima-download.json; decisión vigente:
  metadata/senamhi-normalization-decision.json, 17/11/2026.

Neblima conserva el original e incorpora lecturas de fecha/hora UTC, unidades inferidas aceptadas
por el responsable, clasificación de tokens, control de duplicados y agregados derivados. Las futuras
entregas normalizadas deben detallar sus cambios reales, versión de política y fecha de generación.
SENAMHI no avala por ello las inferencias ni los resultados de Neblima.

Conservar este aviso, el enlace de licencia y la atribución de fuente en distribuciones de la base
y derivados, incluyendo documentación de exportaciones y avisos accesibles desde aplicaciones.
Mantener los avisos de origen aplicables. No atribuir a SENAMHI cambios realizados por Neblima.
La licencia AGPL-3.0-only del código es independiente de la licencia de estos datos.
No extender esta declaración a otros conjuntos OEFA o fuentes ajenas.

# Atribución de la meteorología archivada de Open-Meteo (GFS, #17)

Proveedor del servicio: **Open-Meteo**, API Previous Model Runs
(https://open-meteo.com/en/docs/previous-runs-api). Modelo aguas arriba: **GFS — NOAA NCEP**,
que conserva sus propios términos. La API gratuita no comercial se declara bajo
**CC-BY-4.0 con atribución obligatoria** (https://open-meteo.com/en/licence), revisada el
17/11/2026 en docs/sources/weather.md. La variante integrada en #17 usa únicamente la variable
`temperature_2m_previous_day1` de la muestra fijada por #16
(`configs/acquisition/weather-lima-sample-plan.json`); procedencia por recurso en
`metadata/weather-acquisition.json` y evidencia en reports/alignment/weather-gfs-previous-day1.md.

Open-Meteo no avala las inferencias ni los resultados de Neblima. La decisión de
redistribución del proyecto permanece `unknown` en configs/sources.yaml mientras no exista una
decisión explícita de integración; los valores permanecen bajo almacenamiento local. La
licencia AGPL-3.0-only del código es independiente de estas licencias de datos.
