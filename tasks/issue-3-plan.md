# Plan de la tarea #3: inventario de fuentes, empezando por SENAMHI

Tarea principal: [#3](https://github.com/keneth-arias/airaware/issues/3), inventario ambiental.
Primera verificación de fuente: [#4](https://github.com/keneth-arias/airaware/issues/4), SENAMHI.
Responsable: Keneth. La base de herramientas #2 y la investigación #1 ya están integradas.
Este documento inicia la planificación; no declara completada #3 ni verificados datos de SENAMHI.

## Estado y alcance

Existe un catálogo de 37 recursos candidatos y un validador con estados, ID únicos, notas y fechas.
No son 37 conjuntos independientes: incluye páginas, CSV, diccionarios y metadatos de una misma fuente.
El objetivo de #3 es que cada candidato tenga información y estado verificables, conservando bloqueos.
SENAMHI es el primer caso completo antes de extender el mismo procedimiento a las demás fuentes.
OEFA sigue a cargo de Cristopher en #5; no se modifica esa asignación ni se espera esa investigación
para preparar este caso SENAMHI.

## Primera evidencia de acceso

El 15/11/2026, una consulta mediante la herramienta de lectura web al enlace base de SENAMHI devolvió
HTTP 403. Es un resultado de ese canal de acceso, no una prueba de que el servidor rechace todos los
navegadores o métodos. No se descargó el CSV, no se comprobó su cobertura ni se verificó su licencia.
La próxima ejecución deberá reproducir/documentar el acceso con medios permitidos, sin eludir controles.

## Paso 1. Agrupar recursos y definir evidencia mínima

Identificar la relación de estos ID, conservando los actuales:

- senamhi-lima: página base del conjunto candidato.
- senamhi-lima-csv: recurso candidato de observaciones.
- senamhi-data-dictionary: diccionario candidato.
- senamhi-metadata: metadatos candidatos.

Usar senamhi-monitoring-service y senamhi-reports como referencias complementarias, sin tratarlas
como nuevas mediciones independientes. La meteorología SENAMHI es otra línea del catálogo.
Documentar roles/relaciones en docs/sources/senamhi.md antes de proponer cambios al esquema común.

**Aceptación:** recursos agrupados sin duplicar conteos de estaciones/mediciones ni renombrar ID
silenciosamente; tabla de datos desconocidos y evidencia mínima acordada.
**Verificación:** comparar el inventario vigente con páginas y documentación oficial accesible.
**Archivos previstos:** configs/sources.yaml, docs/sources/senamhi.md.
**Depende de:** #2, ya cerrada. **Tamaño:** pequeño.

## Paso 2. Comprobar accesos y resolver recursos oficiales, junto con #4

Registrar por recurso URL original, redirección y URL real, fecha/hora, canal de consulta, estado HTTP,
formato observado, autenticación y límites si se publican. Una página HTML no es una descarga CSV.
Primero usar páginas y solicitudes acotadas; no descargar todo el conjunto para identificar un enlace.
Si no hay acceso, documentar el bloqueo y probar enlaces oficiales alternativos o catálogos/API
públicos documentados, respetando restricciones del proveedor.

**Aceptación:** cada recurso SENAMHI queda accesible con evidencia o bloqueado con motivo y siguiente
acción. No se marca downloaded sin archivo inspeccionado ni se estima tamaño real a partir de una etiqueta.
**Verificación:** comprobación manual y solicitudes pequeñas con respuesta identificada; registrar
403, tiempos de espera u otros errores por separado, sin confundirlos con datos válidos.
**Archivos previstos:** docs/sources/senamhi.md, configs/sources.yaml.
**Depende de:** paso 1. **Tamaño:** pequeño.

### Punto de control

Revisar los enlaces y su significado antes de adquirir observaciones. Un bloqueo documentado permite
continuar con otra fuente; no habilita suponer licencia, cobertura ni mediciones.

## Paso 3. Registrar metodología, metadatos y derechos sin inventar cobertura

Con el diccionario y los metadatos accesibles, registrar publicador, estaciones/coordenadas,
contaminantes, unidades, significado de fechas e intervalos, zona horaria, método, frecuencia,
códigos faltantes, cobertura declarada, actualización, licencia, URL de términos y atribución.
Distinguir explícitamente dato declarado por catálogo, verificado en documentos y medido en archivos.
Conservar nulos donde no haya evidencia. No convertir AQI en concentración ni datos modelados en mediciones.
La licencia AGPL del programa no concede derechos para redistribuir datos de SENAMHI.

**Aceptación:** cada afirmación tiene referencia y fecha; incertidumbres registradas; licencia y permiso
de redistribución no se dan por compatibles solo porque exista acceso público. #4 conserva la revisión
sustantiva de derechos y significado de mediciones.
**Verificación:** lectura de diccionario/metadatos/términos oficiales; no se necesita descargar el conjunto
masivo. Si la documentación es insuficiente, registrar el motivo y mantener el estado pendiente/bloqueado.
**Archivos previstos:** docs/sources/senamhi.md, configs/sources.yaml.
**Depende de:** paso 2 o documentos oficiales disponibles de forma independiente. **Tamaño:** mediano.

## Paso 4. Validar el catálogo y repetir el procedimiento

Incorporar evidencia SENAMHI sin alterar recursos de OEFA que Cristopher esté revisando.
Ejecutar el validador y agregar pruebas primero si cambia el contrato: distinguir acceso documental,
descarga y análisis; preservar fuentes blocked, duplicate y excluded con explicación.
Aplicar después la misma ficha mínima a los demás candidatos. La tarea #3 no termina solo por revisar SENAMHI.
No elevar estados de candidatos restantes por analogía con esta fuente.

**Aceptación:** catálogo válido con estados sustentados y cobertura/tamaño desconocidos conservados como
tales; restantes candidatos con estado y próxima acción; #3 enlaza la evidencia sin cerrarse prematuramente.
**Verificación:** `uv run --locked airaware catalog validate`, pruebas enfocadas y `make check`;
`make build` y `make audit` antes de la entrega, de acuerdo con AGENTS.md.
**Archivos previstos:** configs/sources.yaml, tests/test_catalog.py, docs/sources/senamhi.md, docs/sources.md.
**Depende de:** paso 3 para SENAMHI; otras fuentes pueden revisarse en documentos separados. **Tamaño:** mediano.

## Qué se deja para las siguientes tareas

El descargador idempotente y reanudable corresponde a #6/#7; adquirir observaciones a #8; medir filas,
estaciones, cobertura real y ventanas a #10/#11. No afirmar esos resultados desde el catálogo.
Los originales se guardarán en `data/raw/senamhi/`; las versiones TimeF, en `data/timef/`.
Actualmente solo existe el conjunto sintético hello-world, verificado en ese registro local.

## Decisiones que ameritan consultar a Keneth

Solicitar decisión si los documentos no permiten determinar derechos/semántica, si es necesario
cambiar el esquema o los identificadores, si una alternativa exige cuenta o pago, o si una descarga
supera un alcance acotado conocido. No pedir confirmación para registrar evidencia o un bloqueo.
No contratar servicios, eludir restricciones ni publicar datos durante esta planificación.
