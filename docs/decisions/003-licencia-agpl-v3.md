# ADR-003: AGPL v3 para el código propio de Neblima

## Estado y decisión

Aceptada el 15/11/2026 por indicación expresa de Keneth: «agpl v3».
Se adopta **AGPL-3.0-only**, solo la versión 3. No se añade la opción de versiones posteriores
porque no formó parte de la solicitud. Los derechos de autor permanecen con sus titulares.

LICENSE contiene el texto completo de la licencia publicado por SPDX, sin traducir ni modificar.
NOTICE identifica el proyecto, la titularidad y el alcance. pyproject.toml declara el identificador
SPDX y empaqueta ambos archivos. Las guías del equipo siguen en español del Perú; el texto legal
original en inglés se conserva para evitar sustituirlo por una traducción no oficial.

## Alcance

La elección cubre el código propio de Neblima y sus contribuciones bajo esa licencia.
No cambia las licencias de dependencias, archivos de terceros ni datos de SENAMHI, OEFA u otras
fuentes. Cada fuente requiere su propia verificación de derechos. Generar datos con el programa
no concede permisos sobre la fuente ni vuelve automáticamente AGPL todas las salidas.

## Consecuencia para TimeNet

TimeNet licencia su código bajo MIT y exige MIT para las contribuciones que recibe, según su
CONTRIBUTING.md en la revisión fijada. Neblima no autoriza una publicación MIT de su código AGPL
mediante este cambio. No copiar componentes AGPL ni agregar una dependencia de Neblima AGPL al
repositorio MIT como si tuvieran una licencia permisiva.

Antes de preparar el PR externo de #24, definir una contribución separada cuyo código pueda
licenciarse expresamente bajo MIT por sus titulares, o conseguir las autorizaciones de licencia
necesarias. No se otorga aquí una excepción ni licencia dual. Documentar autoría, procedencia y
permisos de los archivos concretos antes de enviarlos. Los adaptadores locales pueden seguir
investigándose sin afirmar que están autorizados para publicarse bajo otra licencia.

## Referencias

- [AGPL-3.0-only y texto completo en SPDX](https://spdx.org/licenses/AGPL-3.0-only.html).
- [Fuente del texto de LICENSE](https://github.com/spdx/license-list-data/blob/main/text/AGPL-3.0-only.txt).
- [Reglas de contribución de TimeNet, revisión fijada](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/CONTRIBUTING.md).

La licencia incluye condiciones de distribución y de interacción por red en su sección 13.
Las decisiones de implementación y publicación deberán revisarse contra el texto completo,
no solo contra el resumen de este documento.
