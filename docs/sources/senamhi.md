# SENAMHI Lima: procedencia y límites de la verificación

## Recursos relacionados

senamhi-lima es la página del conjunto; senamhi-lima-csv identifica las observaciones.
senamhi-data-dictionary y senamhi-metadata son referencias complementarias del mismo conjunto.
Los enlaces con sufijos -0/-1/-2 son páginas de recursos; Lightpanda permitió resolver los enlaces
CSV, XLSX y DOCX desde la página base. Las URL reales están en el catálogo.
senamhi-monitoring-service y senamhi-reports son referencias institucionales, sin nuevas mediciones
independientes. La meteorología de SENAMHI se mantiene como otra línea de investigación.

## Descarga comprobada

El 15/11/2026 Lightpanda permitió acceder al catálogo (HTTP 200) y descargar el CSV que indicó Keneth.
El 403 previo correspondía a otra herramienta de lectura web; no implica indisponibilidad general.
La URL exacta, fecha UTC, tamaño, SHA-256 y comprobación estructural están en
[el manifiesto público](../../metadata/senamhi-lima-download.json). Los bytes originales permanecen
localmente en data/raw/senamhi/senamhi_lima_monitoreo_1.csv, fuera de Git.
La descarga no expuso el código HTTP exacto del archivo: se conserva nulo.

Se leyeron 577 794 filas de datos con 15 campos y ninguna fila de longitud inconsistente.
Hay siete cadenas distintas en ESTACION. Los extremos textuales de FECHA son 20150101 y 20240531.
Estas son observaciones estructurales del archivo, no cobertura horaria continua ni siete estaciones
científicamente identificadas. No se infieren zona horaria, frecuencia o validez de las mediciones.
El tamaño medido es 68 501 558 bytes; los aproximadamente 65 MB del plan eran una referencia de catálogo.
No se volvió a descargar el archivo para revisar el inventario.

## Pendiente en #4

| Aspecto | Estado y siguiente acción |
| --- | --- |
| PM10, PM2_5 y NO2 | Encabezados observados; verificar definiciones y unidades en diccionario oficial |
| FECHA/HORA y FECHA_CORTE | Verificar zona horaria, significado, intervalos y fecha de corte |
| Estaciones/coordenadas | Resolver identidades, reubicaciones y coordenadas con documentos oficiales |
| Faltantes y controles | Confirmar códigos y metodología antes de normalizar |
| Licencia/redistribución | El catálogo declara Open Data Commons Attribution License; revisar términos y aplicación al CSV |
| Cobertura útil | Medir por estación/señal en #10; no usar extremos textuales como continuidad |

La licencia AGPL del programa no concede derechos sobre los datos. Esta descarga no autoriza publicar
el CSV ni exportarlo a TimeNet. #4 sigue abierta para revisar derechos y significado de mediciones;
#6/#7 implementan adquisición reproducible y #8 reutilizará el original cuando se verifique su suma.
