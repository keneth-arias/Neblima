# Etiquetas de referencia para episodios PM2.5

Revisión: 16/11/2026 UTC. Responsable: Keneth. Regla `pe-pm25-reference-2017-v1`.
Implementación: `airaware.event_labels`; configuración: `configs/thresholds.yaml`.

## Fuentes oficiales y alcance

- [DS 003-2017-MINAM, registro MINAM](https://www.gob.pe/institucion/minam/normas-legales/3670-003-2017-minam),
  [PDF oficial](https://cdn.www.gob.pe/uploads/document/file/12871/DS-003-2017-MINAM.pdf?v=1530656701).
  Anexo en página PDF 4, impresa 9: PM2.5, referencia de 50 µg/m³ para 24 h y 25 µg/m³ anual;
  el criterio diario incluye no exceder más de siete veces al año.
- [DS 010-2019-MINAM, registro oficial MINEM](https://www.gob.pe/institucion/minem/normas-legales/4773310-010-2019-minam),
  [archivo oficial con protocolo](https://cdn.www.gob.pe/uploads/document/file/5323993/4773310-d-s-n-10-2019-minam.7z?v=1698186349).
  Anexo 1, apartado c.i, página PDF 93, impresa 90: promedio diario automático con mínimo 18 horas
  válidas, desde la hora terminada a la 01:00 hasta la terminada a las 00:00 del día siguiente.
  c.iii repite el criterio para campañas; c.ii/c.iv distinguen muestreo manual, mínimo 22 horas.
  El apartado a.i (PDF 90) exige al menos 45 minutos válidos para formar una media horaria automática.
- [DS 011-2023-MINAM](https://www.gob.pe/institucion/minam/normas-legales/4880911-0011-2023-minam)
  incorpora estándares para cadmio, arsénico y cromo en PM10; no sustituye en este módulo la
  referencia PM2.5 del DS 003-2017. La búsqueda dirigida no identificó una referencia PM2.5 posterior
  que la reemplace; esto no equivale a un análisis exhaustivo de toda obligación ambiental aplicable.

Se consultaron páginas y descargaron archivos con Lightpanda. Los enlaces originales MINAM/SINIA
presentaron fallas de navegación o bloqueo por robots; se usaron copias oficiales Gob.pe, manteniendo
el mismo canal. `metadata/event-labels-legal-sources.json` registra fecha de revisión, tamaños, hashes,
páginas inspeccionadas y limitaciones. Archivos completos locales en data/raw/normativa/, fuera de Git.
Se verificaron visualmente la tabla del ECA y el apartado de suficiencia diaria.

## Dos resultados distintos

| Tipo | Intervalo | Suficiencia aplicada | Interpretación |
| --- | --- | --- | --- |
| forecast_24h | Cualquier bloque futuro de 24 h, incluido uno que cruce días | 24/24 objetivos medidos y válidos | Etiqueta del benchmark, no excedencia regulatoria diaria |
| calendar_day | Medianoche local hasta medianoche siguiente | Al menos 18/24 medias horarias automáticas válidas | Comparación diaria con la referencia, no certificación legal |

El límite de 18 es suficiencia del promedio diario automático, no permiso para entrenar con objetivos
faltantes. El constructor de #18 mantiene 100 % de objetivos. Ninguna de estas funciones construye
ventanas, selecciona particiones o utiliza valores futuros como entrada del modelo.

El cálculo toma la media aritmética de valores válidos; nunca rellena horas, convierte valores ausentes
en cero ni pondera de nuevo por minutos. Los promedios horarios de entrada ya deben estar validados
por el proveedor/proceso de calidad. El mínimo de 45 minutos no se puede comprobar con datos horarios
sin evidencia adicional. El módulo no evalúa filtros manuales, campañas ni métodos equivalentes.

Etiquetas:

- `above_reference`: media estrictamente mayor que 50 µg/m³.
- `not_above_reference`: media menor o igual a 50 µg/m³; **no significa aire seguro ni libre de riesgo**.
- `not_evaluable`: faltan horas válidas para el tipo solicitado. La media queda nula y se conserva el
  motivo `insufficient_valid_hours`; no cuenta como caso negativo.

Se comparan los valores numéricos antes de cualquier redondeo de presentación; no se añade una
­tolerancia al umbral. La representación numérica es float de Python; la media usa statistics.mean.
El control `quality_valid=False`, None, NaN, infinito o concentraciones negativas excluye la hora.
Esta exclusión de negativos es una regla de calidad del proyecto, no una interpretación normativa
de todo posible valor instrumental. Se conservan IDs de todos los registros y de los efectivamente
usados, cantidad válida y cantidad requerida, contexto y versión de regla.

## Contrato para #18

`SeriesContext` identifica una única fuente/estación y exige unit=`ug/m3`, timezone IANA documentada,
method=`automatic_hourly` y semantic_evidence no vacío (ruta/ID de evidencia de unidades, reloj,
método y calidad). Declarar estos campos no demuestra por sí solo su veracidad: el integrador debe
verificar la evidencia. No se afirma que hoy existan estas garantías en el CSV SENAMHI; sigue #43.
No se mezclan estaciones ni se infiere unidad o zona horaria desde la ubicación geográfica.

Cada `HourlyPM25` contiene end con zona horaria, value medido, quality_valid e ID único de observación.
El instante representa el **fin** del promedio horario. El adaptador de #18 debe resolver explícitamente
si el reloj original marca inicio o fin; no trasladar filas sin esa comprobación. No alimentar la
función con pronósticos, valores imputados ni medias móviles ya agregadas.

`label_window` recibe start con zona horaria, records, kind, context y la política cargada. Acepta
registros de horas terminadas dentro de (start, start+24h]; start no se incluye y medianoche final sí.
Las comparaciones de instantes se hacen en UTC; el día calendario se determina en la zona documentada.
Rechaza duplicados, IDs repetidos, horas no alineadas, registros fuera del intervalo, calidad no booleana,
semántica desconocida y días locales que no duren exactamente 24 horas. El orden de entrada no altera
el resultado. Ausencias pueden representarse como filas nulas o huecos; se cuentan igual.

Ejemplo sintético desde la raíz (no describe datos reales ni acredita unidades de SENAMHI):

```python
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from airaware.event_labels import HourlyPM25, SeriesContext, label_window, load_policy

start = datetime(2024, 1, 1, tzinfo=ZoneInfo('America/Lima'))
context = SeriesContext('fixture', 'station-1', 'ug/m3', 'America/Lima',
                        'automatic_hourly', 'fixture:semantics-v1')
records = [HourlyPM25(start + timedelta(hours=i+1), 60.0, True, f'obs-{i}')
           for i in range(18)]
policy = load_policy(Path('configs/thresholds.yaml'))
for kind in ('forecast_24h', 'calendar_day'):
    result = label_window(records, start=start, kind=kind, context=context, policy=policy)
    print(kind, result.label, result.valid_hours)
# forecast_24h not_evaluable 18
# calendar_day above_reference 18
```

## Límites científicos y regulatorios

Una ventana móvil no se convierte en día calendario por durar 24 h. Una comparación diaria no basta
para decidir el criterio anual de frecuencia; el módulo no implementa el conteo anual ni declara
cumplimiento/incumplimiento legal. Tampoco compara medias anuales con 50 ni calcula alertas sanitarias,
INCA, recomendaciones OMS o diagnósticos de salud. Aplicar esta referencia a datos previos a 2017
solo permite una comparación homogénea del benchmark, no una conclusión legal histórica. Conservar
versiones y fechas de reglas si se implementa después un análisis regulatorio histórico.

## Validación y pendiente

Pruebas sin servicios externos: límites 49,999/50/50,001, 17/18/23/24 horas válidas, falta completa,
calidad, valores inválidos, duplicados/alias UTC, linaje, medianoche y días con cambio de hora.
Comando enfocado: `uv run --locked pytest tests/test_event_labels.py`.

#18 sigue abierta. Se entrega un contrato independiente; falta probar con el constructor real que
solo entran objetivos medidos, sin imputación ni mezcla de estaciones, y que los rechazos se contabilizan
junto con los de construcción de ventanas. No se generaron etiquetas de datos reales ni se eligieron
particiones o estaciones. #20 conserva ese bloqueo por decisión explícita de Keneth: mantener abierta hasta verificar integración.
