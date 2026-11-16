# Instrucciones para contribuir a AirAware

Lee `CONSTRAINTS.md` antes de escribir código. No debilites los controles para aprobar un cambio.
Revisa `tasks/plan.md` y la tarea correspondiente. Conserva el trabajo pendiente de otras personas.

## Equipo e idioma

Keneth Arias (`@keneth-arias`) es el responsable principal de datos y plataforma.
Consulta `docs/lead-handbook.md` y `docs/team-work-allocation.md` para conocer responsables y entregas.
Cada persona usa su propia copia y entorno; no cambies la rama dentro de la carpeta de otra persona.
El idioma principal es español latinoamericano, con vocabulario usual en el Perú: archivo, carpeta,
equipo, datos faltantes, tarea y responsable. Explica las siglas al usarlas por primera vez.
Documentación, tareas, títulos/descripciones de PR y mensajes visibles se escriben en español.
Mantén identificadores, rutas, comandos, campos de esquemas y nombres de API en su forma técnica
original. Los tipos de Conventional Commits se conservan; el resumen puede ir en español.
Preserva los archivos originales de las fuentes. Sigue el idioma exigido por TimeNet en contribuciones
externas. La política de idioma actual reemplaza la indicación en inglés del plan original, conservado en Git.

## Comandos

Ejecuta desde la raíz: `make setup`, `make init`, `make check`, `make build`, `make audit`, `make doctor`.
Usa uv y la versión de `.python-version`. CI verifica Python 3.11 y 3.13.13.
Las pruebas y la validación del catálogo deben funcionar sin internet después de instalar dependencias.

## Límites

- `configs/sources.yaml` y `airaware.catalog` definen el inventario y su esquema.
- `metadata/*.csv` son plantillas antiguas, no el inventario vigente.
- Usa Lightpanda para consultar páginas web y descargar sus recursos; sigue docs/web-access.md.
- Separa la descarga por red de la conversión local determinista.
- Conserva los datos originales sin cambios y registra la procedencia de cada observación derivada.
- No inventes unidades, fechas, coordenadas, mediciones faltantes ni permisos de uso.
- No dividas filas al azar para evaluar series temporales ni uses información futura como entrada.
- No subas datos masivos, claves, salidas de cuadernos, cachés ni pesos de modelos.
- Verifica las API de TimeNet contra la revisión fijada en `configs/upstream.lock.json`.
- Agrega dependencias solo cuando se utilicen. Registra decisiones en `docs/decisions/`.
- Conserva las autorizaciones del plan para publicar datos, abrir PR externos, contratar servicios
  o hacer descargas costosas o sin límites. Por ahora usamos almacenamiento local y GitHub Actions.

## Entregas

Trabaja en ramas y PR pequeños; escribe pruebas antes de cambiar la lógica.
Antes de entregar ejecuta `make check`, `make build` y `make audit`. Registra comandos, resultados y
bloqueos. No omitas pruebas, ocultes errores ni afirmes haber revisado datos que no están disponibles.

## Licencia del código

El código propio usa AGPL-3.0-only (LICENSE y NOTICE). Lee ADR-003 antes de copiar código hacia
TimeNet u otro proyecto MIT: no hay excepción ni licencia dual implícita. Las fuentes de datos
y las dependencias mantienen licencias independientes.
