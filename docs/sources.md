# Inventario de fuentes

`configs/sources.yaml` es el inventario vigente y `airaware.catalog.Source` define su esquema.
Valídalo con `uv run --locked airaware catalog validate`.
Los campos opcionales desconocidos permanecen nulos, vacíos o en `unknown`; no se deducen sin evidencia.
`metadata/sources.csv` es una plantilla anterior. Los 37 enlaces incluyen datos, diccionarios y
metadatos: no representan 37 conjuntos de mediciones independientes.

Prioridad 0: mediciones oficiales; 1: otras observaciones o agregaciones; 2: meteorología;
3: productos atmosféricos o satelitales; 4: contexto. La categoría permanece en `unknown` hasta
verificarla. `catalog_url` conserva el enlace de partida. Completa `resource_urls` solo después de
resolver los archivos o las API reales. No pongas credenciales en las URL.

Cada registro admite publicador, descripción, cobertura geográfica/temporal, resolución, variables,
unidades, metodología, categoría, formatos, tamaño, autenticación, límites de acceso, frecuencia de
actualización, licencia, atribución, permisos de redistribución, limitaciones, prioridad, estado,
fecha y notas. Los nombres de campo se mantienen en inglés para conservar el contrato técnico.

| Estado interno | Significado |
| --- | --- |
| discovered | Fuente identificada, aún sin verificar |
| verified | Información verificada con evidencia |
| downloaded | Archivo descargado e inspeccionado |
| profiled | Calidad y cobertura analizadas |
| integrated | Fuente integrada con derechos y metodología documentados |
| blocked | Bloqueada; explicar el motivo |
| duplicate | Duplicada; explicar la coincidencia |
| excluded | Excluida; explicar la decisión |

Los estados avanzados requieren una fecha con zona horaria y notas. El validador comprueba que la
evidencia esté registrada, pero no que sea verdadera: sigue siendo necesaria la revisión humana.

Las líneas sin una fuente concreta siguen como investigación: tránsito/movilidad, emisiones,
generación eléctrica, construcción/polvo, feriados, uso del suelo, elevación y forma urbana.
No inventes enlaces para convertir temas en conjuntos de datos. NASA FIRMS ya figura como candidato
para incendios. Verifica disponibilidad, derechos y pertinencia antes de integrar cada fuente.

## Revisión vigente

Los 37 candidatos tienen [evidencia de acceso fechada](sources/inventory-review.md).
La revisión documental deja 29 verified, uno downloaded, cuatro discovered con acceso parcial y tres
blocked. verified se limita a las afirmaciones de la ficha; no significa calidad o licencia aprobadas.
La evidencia de cada ID está en metadata/source-access.json. Las pruebas comprueban su correspondencia
con el catálogo sin red. Para nuevas consultas y descargas web usa [Lightpanda](web-access.md).
La ficha [SENAMHI](sources/senamhi.md) y el manifiesto distinguen descarga, estructura y pendientes de #4.
