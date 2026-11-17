# SENAMHI: exploración y uso reproducible con dos referencias

Ejecución completa del 17/11/2026: 577 794 filas, siete identidades provisionales, original y hashes
intactos. [Método y comando](../docs/sources/senamhi-reference-adaptation.md),
[recibo](../metadata/senamhi-exploration.json). No se ejecutó código externo ni se copiaron licencias.

## Reproducción independiente de DataGabo

Los 18 promedios PM10/PM2.5/NO2 mostrados en seis distritos de su notebook coinciden a seis decimales
con la agregación propia de las filas originales. Eso corrobora el cálculo agregado, no prueba
identidad de los archivos externos ni confirma las conclusiones sobre movilidad o causalidad.
Nuestra tabla conserva Carabayllo, que no figura en aquel cruce final con ciclovías.

| Distrito | PM10 crudo | PM2.5 crudo | NO2 crudo |
| --- | ---: | ---: | ---: |
| Carabayllo | 71,792 | 27,850 | 22,568 |
| Jesús María | 30,715 | 16,908 | 17,860 |
| Santa Anita | 62,944 | 30,043 | 25,373 |
| San Borja | 58,769 | 18,667 | 20,955 |
| San Juan de Lurigancho | 74,875 | 31,385 | 31,384 |
| San Martín de Porres | 41,513 | 18,684 | 23,082 |
| Villa María del Triunfo | 97,433 | 26,257 | 17,746 |

Estos números son promedios de filas disponibles de todo el histórico, conservando repeticiones
para reproducir el cálculo de referencia. No son medias anuales ni promedios de toda la población
distrital; cada señal tiene diferentes faltantes. Las unidades no se certifican por reproducir
números externos. Las tablas horarias/diarias de AirAware sí resuelven conflictos por señal.

## Cobertura y completitud sin imputación

La grilla por estación entre los días extremos contiene 577 752 casillas por señal/escenario.
El denominador incluye horas ausentes y bordes diarios parciales, sin extender años fuera del periodo.
Las filas originales permanecen en source-rows.parquet; las casillas nulas no son nuevas mediciones.

| Señal | Horas únicas inequívocas | Cobertura en grilla | Días con ≥18 h, reloj crudo | Días con ≥18 h, crudo−5 h |
| --- | ---: | ---: | ---: | ---: |
| PM10 | 380 909 | 65,93% | 15 655 | 15 551 |
| PM2.5 | 367 518 | 63,61% | 15 103 | 15 009 |
| NO2 | 299 125 | 51,77% | 12 161 | 12 110 |

Los días son pares estación/día, no días distintos de toda Lima. Los dos escenarios conservan
las mismas horas inequívocas; el cambio de frontera diaria altera completitud y agregados.
No se etiquetan automáticamente como hora local. La evidencia del boletín 2018 favorece la hipótesis
UTC, pero no confirma todo el histórico, calidad, gases o posición del intervalo de medición.

Los conflictos se resuelven por señal usando el método existente de #10/#11. Un conflicto PM10
no borra una PM2.5 inequívoca. Ceros se conservan; no se convierten ausencias en cero ni se anulan
extremos por estadística. Los valores sin interpretación quedan en la copia de filas fuente.

## Cómo usar lo entregado

1. Explorar monthly/annual para comparar años y estaciones sin mezclar calendarios. Cada fila
   conserva número esperado/observado; annual incluye fechas exactas y proporción de cobertura.
   No interpretar un primer/último año parcial como un año entero ni aplicar criterios normativos.
2. Usar daily_mean solo junto a valid_hours; el umbral exploratorio es 18. La media sin filtro
   está separada. Para pronóstico #18, seguir exigiendo objetivos completos, sin sustituirlos por
   una media diaria incompleta. No usar aquí etiquetas normativas de #20.
3. Consultar cycle para patrones por hora con denominadores, separando reloj crudo/hipótesis.
4. Usar hourly y observed para inspeccionar huecos; el consumo de entrenamiento sigue bloqueado
   hasta documentar semántica/calidad y fijar particiones cronológicas. No interpolar para declarar
   que existen las horas exigidas ni concatenar estaciones por distrito normalizado.

Se exportaron 30 tablas Parquet de análisis (cinco productos × tres señales × dos relojes), una
copia Parquet de las filas originales, summary.json y manifest.json. Los microdatos quedan fuera
de Git. Un lector local puede abrirlos con DuckDB ya instalado, sin servicios pagos ni pandas extra.

## Estado y próximos pasos

Esta entrega permite comprender y explorar SENAMHI con métodos similares y mejores trazas de sus
supuestos. No reemplaza #13 de Cristopher ni cierra #11/#43. La normalización puede reutilizar la
interpretación del archivo y las pruebas, pero cualquier reloj/unidad/identidad de producción exige
evidencia documentada. Movilidad permanece opcional: hacen falta versión/fecha/derechos y auditoría
de uniones antes de añadirla, sin usar datos de 2023 para predecir años anteriores.
