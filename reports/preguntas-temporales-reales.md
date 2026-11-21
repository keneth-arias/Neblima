# Preguntas temporales con registros reales para #35

Ejecución del 20/11/2026 (fecha UTC de cierre: 2026-11-20T23:06:26Z), a cargo de
@qriqs como entrega acotada de la
[issue #35](https://github.com/keneth-arias/airaware/issues/35). El conjunto sintético de
[PR #112](https://github.com/keneth-arias/airaware/pull/112) se generó ahora sobre
**registros reales**: cuatro familias de preguntas (tendencia, máximo, momento y
comparación) con respuestas recalculadas y verificadas de ida y vuelta, en tiempo universal
coordinado (UTC). [Evidencia ligera](../metadata/preguntas-temporales-reales-20261120.json).

## Paquete usado e identidad de la serie

Paquete TimeF `airaware/lima-pm25-pm10-forecast@0.1.0` (fuente `historico`) de la
preparación pm-bivariado del 20/11/2026, leído **en solo lectura** desde el árbol compartido
de @keneth-arias. Es el único de los tres registros con reloj UTC explícito, identidad de
estación SENAMHI y atribución con derechos compatibles documentados (ODC-BY-1.0, según
[DATA_ATTRIBUTION](../DATA_ATTRIBUTION.md)), como exige el criterio de la issue. La unidad
permanece inferida según ADR-005 y se declara en cada pregunta.

| Campo | Valor |
| --- | --- |
| Estación | `CAMPO_DE_MARTE`, código `90b36a17…587a67` |
| Serie principal (PM2.5) | `ae2485b1…54ee80` |
| Serie de comparación (PM10) | `0773c466…2cea8c3` |
| Manifiesto del release | `d0aeb64d…c76a5` |
| Insumo `historico.parquet` | `6e5274eb…13c4d` |

Antes de usar el paquete se ejecutó el verificador oficial
`tools/timenet-smoke/verify_external_pm.py` (salida 0; 296 373 tareas, 14 225 904 valores de
historia y 3 556 476 objetivos, con las mismas huellas de identificadores por partición que
la [evidencia del paquete](../metadata/lima-pm-externa-20261120.json)). El módulo generador
vuelve a cotejar insumo, manifiesto y archivos contra las sumas declaradas y contrasta la
identidad de serie y el conteo de ventanas con `control.duckdb` en solo lectura.

## Comando exacto

Desde la raíz del proyecto, con el árbol compartido en su lugar:

```bash
nice -n 10 env UV_OFFLINE=true uv run --locked python -m airaware.temporal_qa_real \
  --insumo /home/shared/github/keneth-arias/airaware/data/processed/pm-bivariado-20261120/insumos/historico.parquet \
  --release /home/shared/github/keneth-arias/airaware/data/processed/pm-bivariado-20261120/timef/historico/airaware/lima-pm25-pm10-forecast/0.1.0 \
  --resumen /home/shared/github/keneth-arias/airaware/data/processed/pm-bivariado-20261120/timef/historico/resumen.json \
  --salida data/qa/preguntas-temporales-reales-campo-de-marte.json
```

La lectura del paquete se separa del cómputo local determinista: sin red y con `nice -n 10`,
sin GPU. Dos ejecuciones produjeron el mismo SHA-256 del conjunto.

## Emplazamiento de las ventanas

Los objetivos congelados del pronóstico cubren, para esta serie, del 2015-01-15T05:00 al
2024-05-29T23:00 UTC sin huecos mayores a 24 horas: no existe ningún tramo libre finito de
48 horas o más, así que el diseño canónico consecutivo (tendencia de 48 horas) no cabe fuera
de los objetivos. La regla elegida, determinista y documentada: **tramos contiguos de 24
horas con ambos canales finitos que ningún objetivo congelado cubre; se toman las últimas
24 horas de los cuatro tramos completos más recientes y se asignan a las familias en orden
canónico**. La ventana de tendencia usa dos
mitades de 12 horas; `answer_trend` admite cualquier longitud par y las pruebas cubren ese
caso. Conjunto local: `data/qa/preguntas-temporales-reales-campo-de-marte.json`,
SHA-256 `30d8bdd3…ce2cd`, 18 101 bytes.

## Conteos por familia y respuestas

| Familia | Ventana (UTC) | Observaciones | Respuesta |
| --- | --- | ---: | --- |
| tendencia | 2024-03-04T14:00 → 2024-03-05T14:00 | 24 | `aumento` |
| máximo | 2024-03-11T02:00 → 2024-03-12T02:00 | 24 | `28.83 ug/m3` |
| momento | 2024-05-01T05:00 → 2024-05-02T05:00 | 24 | `2024-05-02T04:00:00+00:00` |
| comparación | 2024-05-18T18:00 → 2024-05-19T18:00 | 48 | serie PM10 (`0773c466…2cea8c3`) |

La comparación contrasta la media de PM2.5 de la estación con la media de PM10 de la misma
estación; el prompt nombra cada serie con su contaminante para no atribuir a PM2.5 lo que es
PM10. Cada observación queda identificada como `obs:<serie>:<instante UTC>`, clave que junto
a la fuente, estación, sensor y contaminante recupera la fila original en los Parquet de
insumos. Un cotejo independiente contra la grilla (fuera del módulo) reprodujo el máximo
28.83 y las medias 30.1671 (PM2.5) frente a 39.6521 (PM10).

## Verificación de ida y vuelta

Para cada pregunta, `verify_answer` recalcula la respuesta desde los segmentos extraídos de
la grilla verificada y la ventana declarada. Las cuatro coinciden. El control negativo —
alterar una respuesta guardada y volver a verificar — se rechaza como se espera. Las pruebas
de `tests/test_temporal_qa.py` (43) y `tests/test_temporal_qa_real.py` (9) fijan estos
comportamientos sin depender de los datos compartidos.

## Control de separación frente a los objetivos del pronóstico

- `validate_qa_separated` recibió los 102 550 intervalos objetivo congelados de las dos
  series (51 275 ventanas por canal, particiones train y validation) y no encontró solape:
  las cuatro ventanas de QA están en huecos entre esos intervalos objetivo, dentro del rango
  global 2015-01-15T05:00 / 2024-05-29T23:00 UTC, y entre sí son disjuntas.
- Las ventanas de QA terminan el 2024-05-19T18:00 UTC, antes del inicio de los objetivos de
  prueba externa de openaq y senamhi_horario (ambas desde el 2024-06-02), y sus series tienen
  identificadores distintos; ningún caso de prueba del pronóstico entra al conjunto.
- **Distinción demo/prueba que exige la issue**: este conjunto es material de demostración y
  evaluación. Los casos de prueba del pronóstico (matrices congeladas de #28 y objetivos de
  los dos registros externos) y el ejemplo de presentación de #88 —el del horizonte con
  métricas públicas— permanecen fuera del conjunto y de sus entradas.

## Qué cambió en el código

Ajuste pequeño con pruebas, sin cambiar el diseño de #112 ni debilitar la verificación:

- `src/airaware/temporal_qa.py`: `ObservedSeries` (serie real con atribución obligatoria e
  identificadores por instante UTC), protocolo `HourlySeries`, `build_temporal_question` y
  `generate_questions_for_windows`; `generate_questions` sintética queda como envoltorio con
  el diseño canónico y sus 33 pruebas anteriores pasan sin cambios. El módulo de QA sigue
  sin importar duckdb ni módulos de pronóstico.
- `src/airaware/temporal_qa_real.py` (nuevo): lectura de la grilla con la regla de
  `external_pm.py`, cotejo de sumas, identidad de serie, tramos libres, construcción del
  conjunto y control de separación. Núcleo puro probado sin datos compartidos.

## Bloqueos y pendientes

- Ningún bloqueo: el paquete pasó la verificación declarada y la generación corrió sin red.
- La **exportación del conjunto como paquete TimeF versionado** queda como entrega posterior
  de #35 (pendiente declarado, no improvisado aquí), junto con la validación contra el
  runtime de TimeNet y la cobertura de más estaciones y de las fuentes openaq y
  senamhi_horario cuando se resuelva su reloj y sus derechos.

## Ajustes de revisión (21/11/2026)

La selección toma ahora exactamente las últimas 24 horas de cada tramo libre elegido.
Antes devolvía el tramo entero: una longitud impar podía detener la pregunta de tendencia y
una longitud mayor a 24 no respetaba la regla declarada. Dos pruebas nuevas cubren tramos
largos y la generación completa con longitudes impares.

La repetición sin red sobre los mismos insumos compartidos, leídos en solo lectura, produjo
el mismo SHA-256 `30d8bdd39332ad14685a68a5a2a01a4e5e9e6b80b2e10fe5403ad61e3f9ce2cd`.
Las cuatro respuestas y la separación de los 102 550 intervalos objetivo quedaron verificadas;
la evidencia original se conserva. Los huecos elegidos están dentro del rango global de
fechas del pronóstico, fuera de sus intervalos objetivo individuales.
