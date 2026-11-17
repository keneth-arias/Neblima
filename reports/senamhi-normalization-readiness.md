# Preparación validada para #13 — 17/11/2026

Por decisión explícita de Keneth, no se exige una cohorte fija ni meses continuos mínimos.
La política comparison-v2 retiró los denominadores de tamaño y publica puntuaciones nulas, sin
sustituir la cuota por otro umbral. Se ejecutó de nuevo la comparación sobre los originales;
se conservaron hashes y métricas estructurales. El recibo está en metadata/senamhi-normalization-decision.json.

Se verificó con Lightpanda la declaración Open Data Commons Attribution License del catálogo y el
enlace al mismo CSV adquirido. Redistribución ODC-BY-1.0 con atribución registrada en catálogo;
DATA_ATTRIBUTION.md acompaña la base, sin cambiar la licencia del código propio.

La prevalidación recorrió **577 794 filas y 1 733 382 observaciones por señal**, sin rechazos de
estructura/fecha/hora y con SHA fuente intacto. No eliminó duplicados ni exportó el normalizador
Parquet de Cristopher: es una comprobación de que el contrato/política permiten iniciar #13.

| Señal | Valores finitos | Valores ausentes |
| --- | ---: | ---: |
| PM10 | 380 982 | 196 812 |
| PM2.5 | 367 591 | 210 203 |
| NO2 | 299 192 | 278 602 |

No son puntos horarios únicos: aquí se preservan todas las filas. Son unidades ug/m3 inferidas
aceptadas; no se multiplicó NO2 por factores de gases. observed_at es UTC por confirmación de Keneth;
start/end son nulos porque no se conoce la posición del intervalo. quality queda unknown sin
fabricar flags. Estos campos desconocidos no impiden normalización ni distribución con atribución.

Cristopher debe ejecutar la lectura por lotes, salida determinista/particionada, registro de rechazos
y validación completa de #13 usando el contrato y funciones preparados. La guía está en
[la entrega operativa](../docs/sources/senamhi-normalization-handoff.md). #11/#43 continúan para
los usos científicos que requieren posición del promedio y reglas de calidad, no como permisos
adicionales para convertir la base. No se modificaron copias locales de compañeros ni hubo correos.
