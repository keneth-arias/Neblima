# Entrega lista para Cristopher (@qriqs): SENAMHI #13

Decisiones de Keneth del 17/11/2026, operativas para el original identificado por SHA en
[el registro](../../metadata/senamhi-normalization-decision.json):

- Sin número fijo de estaciones ni mínimo de meses continuos. Conservar cobertura y huecos reales.
- Toda la exportación se interpreta como **UTC**, confirmado por Keneth. Es decisión del responsable,
  no una afirmación de que el diccionario institucional lo documente. Convertir a America/Lima solo
  para vistas locales mediante astimezone; no restar cinco horas y volver a rotular como UTC.
- PM10, PM2_5 y NO2 usan **ug/m3** como unidades inferidas aceptadas. unit_raw permanece nulo porque
  el CSV no contiene unidades. Incluir evidencia units_inferred; no convertir NO2 desde ppb.
  El boletín respalda esta inferencia aunque el manual instrumental menciona ppb.
- ODC-BY-1.0 documentada por catálogo; redistribución permitida conservando atribución/licencia,
  [aviso preparado](../../DATA_ATTRIBUTION.md). No esperar un permiso adicional para #13.
- Calidad individual desconocida y posición inicio/fin sin especificar: conservar esos nulos;
  no exigir una respuesta institucional para ejecutar la normalización estructural.

## Insumos y herramientas reutilizables

Contrato Pydantic: airaware.schemas.Observation, ahora con observed_at opcional, consciente de zona.
Este campo es el timestamp publicado, sin afirmar inicio/fin de un intervalo. start y end siguen nulos
si no hay evidencia. Los consumidores de versiones anteriores pueden seguir omitiendo observed_at.

Política tipada: configs/normalization/senamhi.yaml. Funciones listas para pruebas/uso:

```python
from airaware.senamhi_preparation import load_policy, observation
policy = load_policy()
# row es dict[str, str] original; record es número lógico CSV, encabezado=1.
result = observation(row, 'PM2_5', record=2, policy=policy)
result.model_dump(mode='json')
```

observed_at queda UTC; identificador determinista SHA:registro:señal; valor original, campos completos,
procedencia y evidencia se conservan. Cero es finito; vacíos y marcadores se clasifican, ND queda
sin interpretación, censura no se sustituye por cero. Fechas/horas inválidas se rechazan, sin truncar
minutos/segundos; #13 debe conservarlas en una salida de rechazos trazable, no perderlas.
station_id/sensor_id quedan nulos hasta #14: guardar códigos y coordenadas originales en raw_fields
permite separar identidades provisionales. No agrupar por nombre distrital normalizado.

## Orden recomendado de PR pequeñas

1. Lectura CSV en lotes/streaming, validación del SHA y aplicación del contrato por señal; pruebas
   sintéticas y de unidades/UTC. Reutilizar los fixtures y la política, no cambiar decisiones.
2. Salida Parquet determinista, particionada por fuente/año/mes de observed_at UTC, con política/hash,
   contador por clase y archivo de rechazos. Originales inmutables y escritura atómica en carpeta nueva.
3. Ejecutar las 577 794 filas y reconciliar tres registros por fila entre observaciones/rechazos.
   Preservar repeticiones en una capa de linaje; una vista horaria puede resolver conflictos por señal
   como #10/#11. No borrar una señal válida por conflicto de otra. Verificar hashes antes/después.

No es necesario completar #11, #14 ni recibir respuesta de #43 para estas entregas. No cerrar #14
por llenar station_id con un nombre; no crear ventanas científicas o etiquetas normativas sin
resolver semántica/calidad para ese uso. Aquí se desbloquea #13, no se inventan extremos del promedio.

## Verificación local (cada integrante usa su propia copia)

```bash
git pull --ff-only
make setup
uv run --locked pytest tests/test_senamhi_preparation.py tests/test_observation_schema.py -q
make check
make build
make audit
```

Original esperado: data/raw/senamhi/senamhi_lima_monitoreo_1.csv (fuera de Git). Si falta, obtener
el archivo de la fuente con el flujo documentado de adquisición o solicitar a Keneth su copia con
SHA. No compartir credenciales ni copiar entornos virtuales. No se modificó la carpeta de qriqs.

Exploración previa: reports/senamhi-exploration.md y configs/profiling.json. Los informes viejos
con hipótesis o cuotas se preservan como evidencia histórica; este documento gobierna #13.

## Prevalidación ya ejecutada por Keneth

577 794 filas × tres señales = 1 733 382 observaciones contractuales, sin rechazos de timestamp o
estructura y con SHA intacto. Contadores y ejecución comparison-v2 en
metadata/senamhi-normalization-decision.json; informe reports/senamhi-normalization-readiness.md.
No equivalen a puntos únicos ni sustituyen la exportación Parquet pendiente. Las pruebas completas
aprobaron 283 casos en Python 3.11 y 3.13, además de build/auditoría. La mutación de UTC a timestamp
sin zona fue detectada y restaurada. El CSV original y los resultados antiguos se conservaron.
