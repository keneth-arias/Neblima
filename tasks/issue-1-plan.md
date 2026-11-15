# Plan de la tarea #1: verificar TimeNet y los requisitos del hackathon

Tarea: [#1](https://github.com/keneth-arias/airaware/issues/1).
Responsable: Keneth (`@keneth-arias`). Estado: los cuatro pasos de investigación están ejecutados y documentados; el cierre de la tarea
queda sujeto a revisión e integración del PR. No se afirma validación TimeF en ejecución. El PR #36 está integrado en main desde el 15/11/2026,
commit `4585d7542bbc8836ee85cf76cce1d84312827056`; cerró la tarea #2 de herramientas.
Las tareas se mantienen en GitHub; este documento detalla su orden, sin duplicar un tablero de estado.

## Objetivo y alcance

Dejar una base verificable para implementar los conectores de AirAware con las API correctas y
entregar al hackathon. La entrega es investigación documentada y decisiones de integración.
No incluye recolectar datos, desarrollar el conector, ejecutar entrenamiento ni publicar un PR externo.
La escritura/lectura de un conjunto TimeF de AirAware se verifica en #21–#23, no se declara realizada aquí.

## Evidencia que ya existe

| Evidencia | Ubicación | Situación |
| --- | --- | --- |
| Revisiones de TimeNet/OpenTSLM | `configs/upstream.lock.json` | Registradas; OpenTSLM solo tiene revisión remota, sin inspección del adaptador |
| API, nulos, particiones, composición y licencias | `docs/timenet-integration.md` | Notas preliminares; faltan referencias precisas y una matriz completa de invariantes |
| Reglas y alcance técnico | `ARCHITECTURE.md`, `CONTRIBUTING.md`, `CONSTRAINTS.md` | Integrados en main |
| Entrega y hora del Perú | `docs/hackathon.md` | Lista inicial; falta vincular cada requisito con la evidencia que deberá producir el equipo |
| Revisión de versiones para este plan | Consulta Git de solo lectura el 15/11/2026 | La copia TimeNet está limpia; su HEAD y HEAD remoto siguen en `9bd1613019ee61fbc52e02106a1a45990ead7a54` |

Se volvieron a consultar [la página del hackathon](https://challenge.timenet.ai/) y la
[documentación de conectores](https://docs.timenet.ai/connectors.html) para planificar.
Las páginas públicas pueden cambiar: para API, resolver diferencias contra el commit fijado y
registrarlas, sin actualizar dependencias de manera silenciosa.

## Paso 1. Confirmar la revisión y las reglas de contribución

Revisar la revisión fijada, Python y versiones de ambos paquetes; contrastar AGENTS.md,
CONTRIBUTING.md y pyproject.toml. Si hay cambios externos, documentar diferencias y decidir si se
mantiene el commit actual o se propone otro. No actualizar todo el repositorio externo ni su entorno.

**Aceptación:** SHA completo y fecha, Python compatible, versiones de paquetes y comandos de revisión
registrados con enlaces permanentes. Ninguna modificación en fuentes o dependencias de AirAware.

**Verificación:** `git status --short`, `git rev-parse HEAD`, `git ls-remote origin HEAD` desde la copia
externa; inspección de archivos en esa revisión. No confundir versión declarada con paquete instalado.
**Depende de:** ninguna. **Archivos previstos:** `configs/upstream.lock.json`, `docs/timenet-integration.md`.
**Tamaño:** pequeño. Primera entrega: tabla de versiones y enlaces al commit inspeccionado.

## Paso 2. Completar la matriz de API e invariantes

Registrar símbolo, módulo, firma, comportamiento relevante, prueba de referencia, enlace al commit
y consecuencia para AirAware. Cubrir como mínimo:

- BaseConnector: download/download_async, convert/compose, metadata y separación de red/conversión.
- TimeFDataset, Record, Source y Signal: creación, jerarquías, unidades, ejes y carga diferida.
- ForecastingTask, ClassificationTask y AnswerTask: entradas, objetivos, etiquetas y particiones.
- Nulos: conservación en Arrow, rechazo al convertir a NumPy/PyTorch y tratamiento explícito de máscaras.
- Composición: padres, versiones, importación y trazabilidad; requisitos de licencia/redistribución.
- Escritor/lector y validación oficiales: contratos que deberán probar #21–#23.

**Aceptación:** cada decisión técnica tiene una definición o prueba fuente identificable; diferencias
entre documentación y código quedan resueltas o señaladas. No se inventan firmas ni resultados.
**Verificación:** leer declaraciones y pruebas existentes del commit fijado. La inspección de una
prueba no se registra como prueba ejecutada; cualquier ejecución adicional se informa por separado.
**Depende de:** paso 1. **Archivos previstos:** `docs/timenet-integration.md`, `ARCHITECTURE.md`.
**Tamaño:** mediano.

### Punto de control tras los pasos 1–2

Keneth revisa que los enlaces correspondan al mismo commit y que nulos, tiempos y particiones estén
separados de las decisiones científicas aún pendientes. Resolver contradicciones antes de recomendar
una interfaz a quien implemente #6, #12 o #21.

## Paso 3. Comparar ejemplos y posibilidades de reutilización

Revisar connector.py, dataset.yaml y pruebas de:

- `timenet/hello-world`: construcción sintética sin red y uso de metadatos/escritor.
- `chengsenwang/tsqa`: tareas y organización del conector; no reutilizar particiones aleatorias para Lima.
- Conectores ambientales/meteorológicos: buscar en código y catálogo, registrar consulta y alcance.

Rutas base: `packages/timenet-connectors/src/timenet_connectors/datasets/`.
No confundir `chengsenwang/tsqa` con `tsaqa/tsaqa_benchmark`, que es otro conector.

**Aceptación:** tabla de componentes reutilizables, restricciones y elementos que no deben copiarse.
Una búsqueda sin coincidencias se informa con su alcance; no demuestra ausencia en todo el ecosistema.
**Verificación:** revisar los tres tipos de archivo por ejemplo y guardar rutas/enlaces de pruebas;
no ejecutar descargas ni instalar dependencias de todos los conectores.
**Depende de:** paso 2. **Archivos previstos:** `docs/timenet-integration.md`, `ARCHITECTURE.md`.
**Tamaño:** mediano.

## Paso 4. Vincular requisitos oficiales con la entrega y cerrar decisiones

Contrastar reglas vigentes con docs/hackathon.md. Crear una matriz requisito → evidencia necesaria →
tarea responsable → estado. Incluir registro individual, tamaño del equipo, PR del conjunto TimeNet,
modelo temporal evaluado, presentación, publicaciones X/LinkedIn, Discord y formulario.
La fecha y la hora deben incluir fuente oficial y conversión a America/Lima. No asumir que una
inscripción, publicación o envío ya se realizó. La página oficial es la fuente del requisito; el
plan del equipo define cómo cumplirlo.

Consolidar decisiones sobre conector independiente, revisión fijada, faltantes, fuentes/licencias y
particiones temporales. Registrar límites: la disponibilidad real de fuentes es #4/#5, los contratos
de observaciones son #12 y los modelos/adaptador son #27/#28.

**Aceptación:** requisitos verificables y decisiones coherentes con la arquitectura, sin afirmar
publicaciones o validaciones todavía no realizadas. Los tres criterios originales de #1 tienen
referencias suficientes para que Keneth pueda aprobarlos.
**Verificación:** páginas oficiales con fecha de consulta y revisión cruzada de documentos.
**Depende de:** paso 3. **Archivos previstos:** `docs/hackathon.md`, `docs/timenet-integration.md`,
`ARCHITECTURE.md`. **Tamaño:** pequeño.

## Orden y condiciones de cierre

Pasos 1 → 2 → revisión → 3 → 4 → revisión final. Mantener una entrega pequeña por PR cuando corresponda.
GitHub #1 conserva los criterios oficiales y las casillas; este plan no los marca como completados.
Antes de proponer su cierre:

- Presentar matriz de API, ejemplos, evidencia y decisiones con enlaces permanentes y fechas.
- Dejar desconocidos y bloqueos explícitos; no transferir la validación TimeF pendiente a una afirmación.
- Ejecutar los controles exigidos por el repositorio: `make check`, `make build` y `make audit`.
  Estos verifican AirAware; no equivalen a ejecutar las pruebas de TimeNet.

## Coordinación

Keneth ejecuta esta investigación. Cristopher puede avanzar en evidencia OEFA (#5) y Jordan en el
borrador de presentación (#29) sin esperar el cierre de #1. Compartir cambios de API antes de que
alguien los implemente; no bloquear investigación por revisiones de documentación.
No añadir servicios de pago, entornos de entrenamiento ni descargas masivas para completar esta tarea.

## Resultado de la ejecución (15/11/2026)

| Paso | Resultado verificable | Entrega |
| --- | --- | --- |
| 1. Revisión y reglas | Copia limpia y HEAD remoto coinciden con el commit fijado; paquetes 0.12.0 y Python >=3.11 confirmados | configs/upstream.lock.json y notas de integración |
| 2. Matriz de API | 14 filas de contratos, invariantes y consecuencias con definiciones y pruebas fuente | docs/timenet-integration.md |
| 3. Ejemplos y reutilización | Hello-world y TSQA revisados; búsqueda acotada en 12 fichas y 12 conectores sin coincidencias ambientales | docs/timenet-integration.md |
| 4. Requisitos y decisiones | Matriz de evidencias/estado/responsables, plazo convertido y consecuencias de arquitectura | docs/hackathon.md y ARCHITECTURE.md |

Las pruebas externas se inspeccionaron, no se ejecutaron. No se instaló el SDK ni se descargaron
datos. Se mantiene la revisión y la arquitectura ya aceptadas. Keneth eligió AGPL-3.0-only para el código propio. Se documentó la separación de permisos respecto
a las contribuciones MIT de TimeNet en ADR-003; no queda pendiente esa elección.
Las decisiones de esquema científico, cobertura real y cómputo siguen en #12, #4/#5 y #27/#28.
