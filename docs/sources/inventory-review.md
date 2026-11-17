# Revisión del inventario ambiental

Se consultaron los 37 recursos del plan inicial con Lightpanda entre el 15 y el 16/11/2026 (UTC).
La evidencia por recurso incluye URL original/final, fecha, título, estado HTTP cuando se expuso,
resultado, motivo y próxima acción en [source-access.json](../../metadata/source-access.json).
El catálogo conserva categoría, cobertura y licencia declaradas con calificadores explícitos;
lo que no se pudo verificar queda nulo o unknown. No se descargaron los conjuntos restantes.

## Resultado y alcance (captura histórica de #3)

30 páginas con contenido accesible, cuatro accesos parciales y tres bloqueos de navegación.
Estados del catálogo: 29 verified (revisión documental), un downloaded (CSV SENAMHI), cuatro discovered
(contenido parcial) y tres blocked. Ninguna fuente está integrada ni tiene redistribución aprobada.
verified significa que se revisó la información indicada en las notas; no acredita mediciones válidas,
licencia compatible ni continuidad de la serie. Los documentos y portales no son nuevas observaciones.
La categoría context identifica documentación auxiliar; unknown evita clasificar productos no resueltos.
NASA POWER conserva mixed porque no se revisó el origen de cada variable.

Los catálogos SENAMHI/OEFA declaran Open Data Commons Attribution License. Se registró el enlace
publicado sin interpretar sus obligaciones ni aprobar redistribución; #4/#5 harán esa revisión.
ACAG declara CC BY 4.0 para V6.GL.02.04; EAC4 muestra CC-BY sin versión confirmada en esta consulta.
MIT en los repositorios de terceros corresponde al código; no se trasladó a los datos.

## Bloqueos y accesos parciales

| Recurso | Resultado | Siguiente acción |
| --- | --- | --- |
| openaq-explorer | La aplicación muestra Error | Uncaught Client Exception. | #31: reintentar aplicación o usar documentación/API oficial; comprobar cobertura peruana. |
| airnow-international | Solo se observa la interfaz del mapa; no se confirmó una estación ni un archivo peruano. | #11: confirmar estaciones y disponibilidad histórica para Perú antes de integrar. |
| inei-environmental-statistics | Lightpanda: navigation failed | Reintentar enlace con Lightpanda y buscar alternativa oficial; no inferir indisponibilidad general. #11/#31: resolver recursos, cobertura peruana, derechos y posibles duplicados. |
| minam-sinia | Lightpanda: navigation failed | Reintentar enlace con Lightpanda y buscar alternativa oficial; no inferir indisponibilidad general. #11/#31: resolver recursos, cobertura peruana, derechos y posibles duplicados. |
| senamhi-hourly-meteorology | Lightpanda: navigation timed out | Reintentar enlace con Lightpanda y buscar alternativa oficial; no inferir indisponibilidad general. #16: comprobar estaciones/modelos, términos y muestra pertinente para Perú. |
| era5-and-era5-land | El enlace es la portada CDS; falta resolver productos ERA5 y ERA5-Land concretos. | #16: resolver fichas específicas, cuenta, términos y muestra acotada. |
| nasa-modis-maiac-mcd19a2 | El enlace es la portada Earthdata; no identifica el producto MCD19A2 concreto. | #33: resolver ficha oficial y versión MCD19A2; verificar derechos y cobertura. |

No se interpretaron errores de navegación como HTTP 403 ni como indisponibilidad general del proveedor.
No se excluyó ni eliminó ningún candidato. Los grupos SENAMHI, OEFA y OpenAQ incluyen referencias
relacionadas; se comprobarán duplicados de observaciones en #14/#31 antes de combinarlas.
WAQI histórico presenta índices AQI: no debe convertirse directamente en concentración.
CAMS, ACAG y el depósito procesado de Lima aportan productos modelados/derivados, no estaciones nuevas.

## Tamaño y cobertura

| Recurso | Declarado en plan/catálogo | Comprobado localmente |
| --- | --- | --- |
| SENAMHI CSV | Plan: aproximadamente 65 MB; página: 65.33 MB | 68 501 558 bytes; SHA-256 y estructura en manifiesto |
| OEFA | Plan: aproximadamente 1.23 GB | No descargado; size_bytes permanece nulo |
| Resto | Coberturas documentales calificadas en catálogo | Sin archivos ni tamaño real medido |

SENAMHI tiene 577 794 filas, 15 columnas, siete cadenas de estación y extremos textuales de FECHA
20150101–20240531. No se verificó continuidad ni se homologaron estaciones. El manifiesto estructural
es [público](../../metadata/senamhi-lima-download.json); el archivo original permanece fuera de Git.
Las unidades, zona horaria y derechos se revisan en #4; calidad/cobertura útil se miden en #10.

## Verificación reproducible

`make check` valida el esquema, estados, correspondencia de los 37 ID con la evidencia y fechas con
zona horaria sin acceder a internet. `make build` genera el paquete; `make audit` revisa dependencias.
Las pruebas no requieren archivos originales ni Lightpanda instalado. La evidencia es una captura
fechada, no una promesa de que los proveedores mantengan los mismos enlaces.

## Actualización posterior: #4

La revisión SENAMHI del 16/11/2026 descargó diccionario y metadatos; el catálogo vigente tiene
27 verified y tres downloaded, además de cuatro discovered y tres blocked. El registro de acceso
de #3 conserva su fecha original. La evidencia posterior está en metadata/senamhi-documentation.json;
la licencia de la base ya está documentada, pero unidades/tiempo y publicación conservan preguntas.

## Candidato adicional del 17/11/2026

El inventario vigente suma 38 registros. EAS_Aire se agregó por solicitud de Keneth: ficha accesible
con Lightpanda, descargas del agente fallidas y archivo completo proporcionado por el usuario.
La [evidencia específica](../../reports/acquisition/oefa-eas-aire.md) separa esos resultados;
no se reescribe la revisión histórica de los 37 recursos iniciales.
