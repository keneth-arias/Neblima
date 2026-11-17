# Adaptación de métodos externos para explorar SENAMHI

> Decisión vigente del 17/11/2026: [SENAMHI listo para #13](senamhi-normalization-handoff.md).
> UTC confirmado por Keneth, unidades inferidas aceptadas y ODC-BY-1.0 con atribución.
> Esta revisión previa se conserva como evidencia histórica, no como bloqueo de normalización.

Revisión del 17/11/2026; implementación propia, sin ejecutar notebooks ajenos ni copiar código.

## Referencias fijadas

- [Cristhianbgf/calidad-aire-lima](https://github.com/Cristhianbgf/calidad-aire-lima/tree/8d2deaa70c9e6c4d0d4b2b6699cda3b3a6dfa85f),
  commit 8d2deaa70c9e6c4d0d4b2b6699cda3b3a6dfa85f, confirmado como HEAD al revisar.
  La [revisión previa](metadata-methods-review.md) identifica métodos y límites sobre el mismo SHA
  SENAMHI. Se reutiliza esa evidencia; no se repiten ni amplían sus conclusiones temporales.
- [DataGabo/Analisis-de-la-calidad-del-aire-y-la-movilidad-urbana-en-la-ciudad-de-Lima](https://github.com/DataGabo/Analisis-de-la-calidad-del-aire-y-la-movilidad-urbana-en-la-ciudad-de-Lima/tree/4f287870b7e90e562e498fddabd264854f1eb335),
  commit 4f287870b7e90e562e498fddabd264854f1eb335. Se leyó README y todo el código de
  Analisis_Aire_Ciclovias.ipynb (blob 876dec7ba163f1b3dbbc38a0baf4367beb40dedc), sin ejecutarlo.
  El árbol raíz no contiene LICENSE y la API informa license=null: no asumir permiso para copiarlo.

## Qué reutilizamos conceptualmente

| Método | Referencia | Aplicación propia |
| --- | --- | --- |
| Grilla horaria y conteos de cobertura | Cristhian | Grilla sin imputación por identidad provisional, conservando días sin valores |
| Media diaria con al menos 18 horas | Cristhian | Diagnóstico explícito, separado de forecast_24h y de cualquier certificación normativa |
| Ciclos horarios y resúmenes temporales | Cristhian | Reloj crudo y crudo−5 h como escenarios separados; no rotularlos ambos como hora local |
| Nombres distritales sin tildes/guiones bajos | DataGabo | Etiqueta analítica adicional, nunca sustituto del nombre original ni identidad de estación |
| Resumen de cada contaminante por distrito | DataGabo | Tabla cruda reproducible y separada de estadísticas por estación/año |

## Límites encontrados al leer DataGabo

El notebook carga aire.csv y ciclovias.csv locales en Latin-1. La copia SENAMHI de AirAware se
lee con el contrato UTF-8 ya verificado; no se renombra ni descarga otra copia. El notebook no
publica los CSV ni sus hashes, por lo que 577 794 filas y el nombre de origen son indicios de
correspondencia, no prueba de igualdad de bytes como en la referencia de Cristhian.

La limpieza usa dropna(how='all') sobre PM10/PM2_5/NO2, lo cual evita borrar una fila por faltar
una sola señal. Sin embargo, el resumen final usa df_aire original, no df_aire_analisis. Aunque
los promedios omiten nulos, no corrige duplicados ni conflictos ni mide calendario faltante.
AirAware conserva todas las filas y aplica la política existente por señal para puntos diagnósticos.

El README describe agregación anual, pero el groupby del cruce final agrupa solo por DISTRITO_NORM,
sin FECHA/año: produce un promedio de todas las filas disponibles a lo largo del periodo. Se pondera
por cantidad de lecturas, no por años o estaciones con igual peso; no es una media anual.
Nuestra tabla cruda distrital reproduce esa idea descriptiva sin presentarla como serie temporal.
Las tablas annual/monthly sí separan año y estación, con denominadores y fechas de cobertura.

El inner join elimina distritos sin coincidencia con ciclovías y muestra seis distritos: no prueba
que los demás tengan cero infraestructura ni cubre toda la ciudad. Se requerirían CSV, año, versión,
licencia y auditoría de claves con left/anti joins antes de adoptar ese cruce. No se descargaron
ciclovías para esta entrega; el objetivo de AirAware sigue siendo calidad del aire horaria.

Las gráficas comparan concentraciones y kilómetros en un mismo eje numérico; magnitudes de unidades
distintas no expresan una proporción física. Además, infraestructura de 2023 frente a contaminación
agrupada de 2015–2024 no permite inferencia temporal ni causal. No asumir que NO2 mide exclusivamente
tráfico ni que una estación representa la exposición media de todo un distrito. Una eventual
covariable de movilidad debe tener fecha de disponibilidad y no introducir información futura.

## Interpretación temporal y promedios

El desplazamiento −5 h se sustenta como hipótesis en los controles independientes del boletín
2018 de la revisión previa, no en etiquetas de gráficos externos. No confirma toda la serie ni
la posición inicio/fin del intervalo. Las medias diarias aquí agrupan etiquetas de reloj por fecha;
no sustituyen la convención de horas terminadas de calendar_day de #20.

La grilla empieza a las 00:00 del primer día con timestamp de cada identidad y termina a las 23:00
del último. Así incluye bordes parciales de día, pero no inventa años anteriores/posteriores.
Los años intermedios completos tienen su calendario completo; el primer/último año pueden ser
parciales. annual.mean y monthly.mean resumen horas observadas inequívocas, sin filtro normativo
ni imputación. daily_mean exige 18 horas; su media sin filtro también se conserva con otro nombre.
No confundir promedio de horas con promedio de medias diarias. No redondear antes de comparar.

## Uso reproducible

```bash
uv run --locked python -m airaware.senamhi_exploration \
  --output reports/generated/senamhi-exploration/una-carpeta-nueva
```

Usa el contrato SENAMHI existente de configs/profiling.json, su manifiesto y SHA. Exporta las
filas fuente sin descartarlas (incluyendo ID y tokens), grillas y tablas daily/annual/monthly/cycle
por contaminante y escenario. Las grillas tienen observed=false y value=null donde falta valor;
no son mediciones nuevas. El manifiesto referencia el SHA fuente y cada salida. Los agregados se
pueden trazar por serie/reloj/señal hacia source-rows.parquet y finalmente el original inmutable.

Las salidas no reemplazan #13 ni habilitan splits, entrenamiento o etiquetas reales. #11/#43
siguen abiertos por semántica/calidad/derechos; los nombres normalizados no cierran #14.
