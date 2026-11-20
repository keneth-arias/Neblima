# Modelo tabular de PM2.5 con datos reales en la prueba externa de Lima

El modelo tabular ajustado solo con entrenamiento y seleccionado en validación obtuvo un
**error absoluto medio (MAE) de 5,5278 µg/m³ en OpenAQ y 6,3090 µg/m³ en SENAMHI horario**,
frente a 7,1695 y 6,9058 µg/m³ de persistencia. Superó a persistencia en las dos fuentes
(−1,6417 y −0,5968 µg/m³). Frente al modelo temporal A de [#88](../models/prueba-externa-pm25-pm10.md)
lo superó en OpenAQ (−0,2663 µg/m³) y quedó por debajo en SENAMHI horario (+0,7301 µg/m³).
La comparación usa los objetivos externos congelados, unidos por `window_id` y `forecast_hour`
con las predicciones ya registradas, y se ejecutó una sola vez por fuente. Las métricas de
episodios siguen **pendientes de [#20](https://github.com/keneth-arias/airaware/issues/20)**.
Plan del método y contrato del módulo: [tabular-plan.md](tabular-plan.md).

## Método y selección en validación

Las características por par ventana-horizonte son los 24 lags horarios de PM2.5 de la historia,
el horizonte y el calendario UTC de la hora objetivo, más el desfase respecto de la media de
entrenamiento por estación (`airaware.benchmarks.features` y `processing`). El ajuste usa
LightGBM 4.7.0 con pérdida L1, parada temprana y elección de iteraciones sobre el MAE de
validación (`airaware.benchmarks.model`), con un hilo y modo determinista. El criterio de
selección es el mismo que eligió persistencia en [#25](lima-pm25.md): el MAE global de
validación en µg/m³. Los tres candidatos se declararon en el script antes de tocar la prueba;
el cómputo acotado del servidor compartido limitó la búsqueda a esa grilla pequeña.

| Candidato | Configuración | MAE de validación (µg/m³) | Rondas elegidas | Ajuste (s) |
| --- | --- | ---: | ---: | ---: |
| `lgbm-base` | tasa 0,1 · 15 hojas · mínimo 10 | 4,8009 | 300 | 29,4 |
| `lgbm-hojas-31` | tasa 0,1 · 31 hojas · mínimo 20 | 4,7852 | 297 | 30,4 |
| **`lgbm-paso-005`** | **tasa 0,05 · 31 hojas · mínimo 20** | **4,7775** | **462** | **43,2** |

Persistencia calculada sobre los mismos 266 748 pares de validación obtuvo 6,4532 µg/m³,
idéntico al valor registrado en la congelación de ajuste de #88 (6,453224793957586). El
tabular seleccionado mejora ese MAE de validación en 1,6757 µg/m³.

## Datos y verificación

Los datos provienen del árbol compartido de Keneth (`data/benchmarks/lima-pm25-pm10-v1` y
`data/benchmarks/lima-pm25-pm10-externa-v1`), en solo lectura. Antes de usar cualquier matriz
se verificó el SHA-256 de cada archivo y la huella de identificadores ordenados contra su
manifiesto; el `paired.parquet` de cada fuente coincide con el `paired_sha256` de su
`metrics.json` registrado y ambos resultados apuntan a la congelación de modelos
`6727c884…f31b`. Los npz crudos de predicciones del servidor no son accesibles por permisos y
no hicieron falta: la comparación usa las predicciones registradas en el Parquet pareado.

| Conjunto | Partición | Ventanas | Pares ventana-hora | Verificación |
| --- | --- | ---: | ---: | --- |
| `lima-pm25-pm10-v1/train.npz` | Entrenamiento | 251 915 | 1 511 490 | SHA-256 e identificadores OK |
| `lima-pm25-pm10-v1/validation.npz` | Validación | 44 458 | 266 748 | SHA-256 e identificadores OK |
| `externa-v1/openaq` | Prueba congelada | 85 538 | 513 228 | SHA-256, identificadores y Parquet OK |
| `externa-v1/senamhi_horario` | Prueba congelada | 102 768 | 616 608 | SHA-256, identificadores y Parquet OK |

Dos comprobaciones de protocolo confirmaron que los objetivos son los mismos que los de las
referencias registradas: la persistencia de validación coincide con la congelación de ajuste y,
en cada fuente, la persistencia y el modelo A leídos del Parquet pareado reproducen los MAE
registrados de [#88](../models/prueba-externa-pm25-pm10.md) con diferencia menor a 1e−9. La
cobertura coincidió por completo: **ninguna ventana quedó excluida** en ninguna fuente. La
unión exige la misma estación y el mismo valor objetivo por par (`paired_join` del módulo,
contrato endurecido en el PR #111).

## Resultados

Denominadores explícitos: cada fila de "pares" cuenta pares ventana-horizonte con solapamiento
entre ventanas consecutivas; "horas de estación" cuenta las horas objetivo distintas por
estación dentro de los mismos pares.

| Fuente | Modelo | MAE (µg/m³) | RMSE (µg/m³) | Pares | Horas de estación |
| --- | --- | ---: | ---: | ---: | ---: |
| OpenAQ | **Tabular** | **5,5278** | **9,2888** | 513 228 | 87 648 |
| OpenAQ | Temporal A | 5,7941 | 9,4015 | 513 228 | 87 648 |
| OpenAQ | Persistencia | 7,1695 | 11,4758 | 513 228 | 87 648 |
| SENAMHI horario | **Tabular** | **6,3090** | **10,0447** | 616 608 | 105 333 |
| SENAMHI horario | Temporal A | 5,5789 | 9,0618 | 616 608 | 105 333 |
| SENAMHI horario | Persistencia | 6,9058 | 11,1123 | 616 608 | 105 333 |

Los MAE de persistencia y del temporal A son los valores ya registrados en #88, reproducidos
aquí sobre los pares comunes. La diferencia tabular − persistencia fue de −1,6417 µg/m³
(−22,90 %) en OpenAQ y −0,5968 µg/m³ (−8,64 %) en SENAMHI horario. Frente al temporal A, el
tabular fue 0,2663 µg/m³ mejor (−4,60 %) en OpenAQ y 0,7301 µg/m³ peor (+13,09 %) en SENAMHI
horario.

### MAE por horizonte (µg/m³)

| Horizonte | OpenAQ: tabular | OpenAQ: A | OpenAQ: persistencia | SENAMHI: tabular | SENAMHI: A | SENAMHI: persistencia |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| +1 h | 3,3860 | 3,3808 | 3,5938 | 3,7339 | 3,2564 | 3,4613 |
| +2 h | 4,8523 | 5,0183 | 5,6684 | 5,5293 | 4,8286 | 5,4555 |
| +3 h | 5,6571 | 5,9502 | 7,0923 | 6,5492 | 5,7267 | 6,8279 |
| +4 h | 6,1284 | 6,5248 | 8,1612 | 7,0870 | 6,2827 | 7,8602 |
| +5 h | 6,4495 | 6,8393 | 8,9602 | 7,3790 | 6,5855 | 8,6340 |
| +6 h | 6,6935 | 7,0511 | 9,5412 | 7,5757 | 6,7936 | 9,1959 |

En OpenAQ el tabular supera al temporal A desde +2 horas y pierde por 0,0052 µg/m³ en +1;
supera a persistencia en los seis horizontes. En SENAMHI horario supera a persistencia de +3 a
+6 horas y pierde con ella en +1 y +2; el temporal A lo supera en los seis horizontes.

### MAE por estación (µg/m³)

Los nombres de sitio provienen de la tabla registrada en
[prueba-externa-pm25-pm10.md](../models/prueba-externa-pm25-pm10.md); los códigos se conservan
por fuente.

| Fuente | Estación | Pares | Tabular | Temporal A | Persistencia |
| --- | --- | ---: | ---: | ---: | ---: |
| OpenAQ | Villa María del Triunfo (`2302`) | 75 738 | **4,4074** | 4,6909 | 5,4574 |
| OpenAQ | San Martín de Porres (`2351`) | 89 898 | **5,0543** | 5,3250 | 6,5272 |
| OpenAQ | Santa Anita (`2397`) | 89 184 | **6,2701** | 6,5058 | 8,6197 |
| OpenAQ | San Borja (`2402`) | 91 602 | **6,4219** | 6,7526 | 8,1504 |
| OpenAQ | Campo de Marte (`2415`) | 91 146 | **5,5266** | 5,7239 | 6,7480 |
| OpenAQ | San Juan de Lurigancho (`6501061`) | 18 | 12,7715 | **10,1247** | 11,9083 |
| OpenAQ | San Juan de Lurigancho (`7464`) | 75 642 | **5,2542** | 5,5397 | 7,2563 |
| SENAMHI | Campo de Marte (`112194`) | 108 696 | 6,0707 | **5,4066** | 6,3919 |
| SENAMHI | Carabayllo (`113260`) | 12 252 | 6,9365 | **6,0480** | 7,8979 |
| SENAMHI | San Borja (`00112270`) | 103 098 | 7,1670 | **6,4905** | 7,8219 |
| SENAMHI | San Juan de Lurigancho (`113258`) | 91 080 | 6,4542 | **5,4375** | 7,0617 |
| SENAMHI | San Martín de Porres (`00112272`) | 106 662 | 5,8555 | **5,1908** | 6,3876 |
| SENAMHI | Santa Anita (`00112271`) | 103 674 | 7,4307 | **6,3346** | 8,3917 |
| SENAMHI | Villa María del Triunfo (`112233`) | 91 146 | 4,6481 | **4,4263** | 5,1096 |

En OpenAQ el tabular supera al temporal A en seis de siete estaciones; la excepción
(`6501061`) solo tiene 18 pares de tres ventanas y su comparación es inestable. En SENAMHI
horario el temporal A supera al tabular en las siete estaciones. El desglose completo por
estación y horizonte, con RMSE, está en la
[evidencia JSON](../../metadata/tabular-datos-reales.json).

## Métricas de episodios

**Pendiente de [#20](https://github.com/keneth-arias/airaware/issues/20).** No existen aún
etiquetas de episodio verificadas para estos objetivos: los positivos y negativos son
desconocidos, por lo que precisión, exhaustividad, F1, PR-AUC y calibración no se calcularon.
La evidencia registra el estado `pendiente-de-20` con valores nulos. El umbral p95 por
estación que el módulo calcula con entrenamiento solo sustentaría una agrupación exploratoria;
una comparación de detección exige las etiquetas de #20 y quedará para una ronda posterior.

## Protocolo y decisiones

- **Objetivos ya gastados una vez.** Las dos cohortes externas se usaron para la comparación
  A/B de #88. El protocolo permite una comparación nueva sin fuga porque el tabular no recibió
  ninguna información de prueba antes de evaluarse: candidatos e iteraciones se fijaron con
  validación, la evaluación se ejecutó una sola vez por fuente y el corredor rechaza una
  segunda ejecución (la evidencia no se sobrescribe).
- **Identidad de objetivos.** La unión uno a uno por `window_id`/`forecast_hour` exige la misma
  estación y el mismo valor objetivo; de haber faltado un horizonte en cualquier lado, su
  ventana completa habría salido con la exclusión contada. No hubo exclusiones.
- **Referencias de #25.** Las referencias históricas de #25 (prueba de 304 734 pares) no están
  en este entorno. La comparación usa la prueba externa bivariada, cuyos valores de
  persistencia (7,170 y 6,906 µg/m³) son los que el issue #26 cita como referencia separada.
  Los denominadores y las claves de esa versión quedan registrados en la evidencia.
- **Desfase por estación en cero.** Los códigos de proveedor de la prueba externa no están
  vinculados a las estaciones históricas del entrenamiento en los datos entregados, así que la
  característica de desfase queda en 0,0 en toda la prueba, como define el contrato del módulo.
  La señal principal son los lags crudos. Vincular identidades de estación es parte del
  trabajo de identidad en curso y no se improvisó aquí.
- **Cómputo acotado.** Un hilo, modo determinista, `nice -n 10`, sin GPU: 125 s en total para
  tres ajustes y dos evaluaciones. No se subieron datos ni pesos; la evidencia solo contiene
  agregados.

## Reproducir

```bash
nice -n 10 uv run --locked --extra tabular python tools/training/eval_tabular_real.py \
  --data "$COMPARTIDO/data/benchmarks/lima-pm25-pm10-v1" \
  --externa "$COMPARTIDO/data/benchmarks/lima-pm25-pm10-externa-v1" \
  --ejecucion "$COMPARTIDO/data/benchmarks/lima-pm25-pm10-ejecucion" \
  --output metadata/tabular-datos-reales.json
```

El corredor verifica cada manifiesto antes de leer los npz, ajusta y selecciona solo con
entrenamiento y validación, evalúa una vez y coteja cada MAE de referencia contra los valores
registrados; cualquier discrepancia termina con un bloqueo explícito y sin evidencia.

## Trazabilidad

Ejecución del 20/11/2026 entre las 22:52:33 y 22:54:38 UTC sobre el commit `4dd2244` (main de
ese momento), Python 3.13.13, NumPy 2.5.5, LightGBM 4.7.0 del archivo de versiones bloqueado.
Comando, hashes de entrada, configuración elegida, resultados por estación y horizonte y
estado de episodios: [metadata/tabular-datos-reales.json](../../metadata/tabular-datos-reales.json).
Fuente de los datos: Servicio Nacional de Meteorología e Hidrología del Perú (SENAMHI), con
republicaciones de OpenAQ en la cohorte externa. Datos bajo ODC-BY-1.0 según
[DATA_ATTRIBUTION.md](../../DATA_ATTRIBUTION.md). Las predicciones individuales permanecen en
el almacenamiento compartido, fuera de Git.
