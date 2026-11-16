# Plan de #4: verificar SENAMHI y los derechos de redistribución

Responsable: Keneth (@keneth-arias). Dependencia: #3 cerrada mediante #41.
Seguimiento y lista de trabajo: [issue #4](https://github.com/keneth-arias/airaware/issues/4).
Estado: planificación; pendiente de decisión de Keneth antes de ejecutar la investigación.

## Objetivo y alcance

Contrastar el CSV existente con el diccionario XLSX, los metadatos DOCX y documentos oficiales;
registrar qué significan las mediciones y qué condiciones aplican a su redistribución.
Revisar PM10, PM2_5 y NO2, manteniendo PM2.5 como objetivo inicial del proyecto.
No incluye normalización, imputación, selección de estaciones, evaluación de cobertura útil ni
publicación de datos: corresponden a #8/#10/#12/#13 y a sus puntos de decisión.

## Evidencia disponible

- configs/sources.yaml contiene las URL reales del CSV, XLSX y DOCX resueltas con Lightpanda.
- El CSV original está en data/raw/senamhi/senamhi_lima_monitoreo_1.csv, excluido de Git.
- metadata/senamhi-lima-download.json registra SHA-256, 68 501 558 bytes y estructura comprobada.
  No es necesario volver a descargarlo. Los extremos textuales de FECHA no prueban continuidad.
- El catálogo declara Open Data Commons Attribution License y frecuencia horaria para las mediciones;
  son declaraciones documentales, todavía sin contraste completo ni permiso aprobado en AirAware.
- Lightpanda permitió acceder al catálogo. El 403 previo fue de otro canal; no es un bloqueo vigente
  demostrado de SENAMHI. El acceso a los documentos se comprobará al ejecutar este plan.

## Secuencia de trabajo

### 1. Preservar los documentos oficiales

**Acción:** con Lightpanda, comprobar los enlaces vigentes y descargar únicamente XLSX y DOCX.
Usar consultas de 10–20 segundos y un máximo inicial de 5 MiB por documento; si la herramienta
no permite limitar la transferencia, verificar primero el tamaño declarado y detenerse si resulta
incierto o supera ese alcance. Registrar URL original/final, fecha UTC, tamaño real, formato y SHA-256.
Reutilizar el CSV tras comprobar su suma. Leer XLSX/DOCX como datos, sin ejecutar contenido incrustado.

**Aceptación:** los tres recursos tienen procedencia verificable o un bloqueo explicado; originales
intactos y fuera de Git. No se confunde HTML de error con un documento.
**Verificación:** firmas de formato y lectura local, suma del CSV contra manifiesto; registrar fallas
por canal sin inventar códigos HTTP. No instalar bibliotecas si basta la biblioteca estándar para
inspeccionar los XML de los contenedores XLSX/DOCX.
**Archivos:** data/raw/senamhi/ (local), metadata/senamhi-documentation.json (nuevo, metadatos).
**Dependencia:** aprobación del plan. **Tamaño:** pequeño.

### 2. Contrastar los derechos declarados

**Acción:** seguir con Lightpanda el enlace de licencia publicado por el catálogo y sus términos
oficiales. Registrar versión si se identifica, atribución requerida, avisos, condiciones y alcance
sobre el conjunto/archivo. Contrastar metadatos, catálogo y restricciones adicionales, incluyendo
la posible entrega derivada en TimeNet. Separar licencia de datos y AGPL del programa.

**Aceptación:** matriz de evidencia con referencia, fecha, condición y discrepancia; no establecer
redistribution: allowed solo por acceso público o por una etiqueta de licencia.
**Verificación:** lectura cruzada de documentos oficiales y términos; registrar nulo lo no resuelto.
**Archivos:** docs/sources/senamhi.md, configs/sources.yaml, manifiesto documental.
**Dependencia:** paso 1, o términos oficiales accesibles de forma independiente. **Tamaño:** pequeño.

### Punto de control: derechos y evidencia insuficiente

Presentar a Keneth obligaciones encontradas y cualquier conflicto. Si no hay evidencia suficiente,
propuesta pendiente de su decisión: mantener derechos/unidades desconocidos, registrar el bloqueo
y preparar un borrador de consulta a SENAMHI. No enviar mensajes ni publicar datos sin autorización
expresa. Una fuente secundaria puede orientar la búsqueda, sin sustituir evidencia oficial faltante.
No se requiere cerrar todos los desconocidos para entregar un informe honesto; un bloqueo no equivale
a una fuente aprobada para integración. El cierre de #4 dependerá de que sus criterios documenten
el resultado y sus límites, sin declarar cumplida una verificación que no se logró.

### 3. Construir la matriz de significado de los campos

**Acción:** contrastar las 15 columnas del CSV con diccionario/metadatos. Documentar definición,
tipo, unidad cuando conste, fuente y confianza para cada campo. Revisar PM10/PM2_5/NO2, FECHA/HORA,
FECHA_CORTE, zona horaria, intervalo de promediación, faltantes, validación y metodología instrumental.
Registrar significado declarado de estaciones, coordenadas, altitud y UBIGEO; homologación y
reubicaciones quedan en #14. Consultar informes oficiales acotados solo para resolver discrepancias.

**Aceptación:** todos los campos quedan documentados o explícitamente desconocidos; distinguir
frecuencia de medición, agregación, actualización y corte. No inferir unidades por magnitud ni zona
horaria por ubicación; no transformar valores ni copiar conclusiones de terceros como propias.
**Verificación:** tabla campo → afirmación → documento/sección → fecha → discrepancia; cotejo de
encabezados con el manifiesto del CSV, sin análisis masivo de cobertura.
**Archivos:** docs/sources/senamhi.md, configs/sources.yaml.
**Dependencia:** paso 1; puede seguir documentalmente aunque derechos permanezcan sin resolver.
**Tamaño:** mediano.

### 4. Entregar evidencia y habilitar las tareas siguientes

**Acción:** actualizar solo campos sustentados y estados del catálogo, conservando ID y desconocidos.
Registrar resultados, bloqueos y qué puede usar #8/#10/#13. Adaptar pruebas de consistencia si los
metadatos verificados cambian sus expectativas, sin debilitar restricciones del esquema.

**Aceptación:** informe revisable y catálogo coherente; ninguna transición a integrated ni publicación
implícita. La issue distingue verificaciones logradas de preguntas abiertas y próximos responsables.
**Verificación:** make check, make build, make audit; pruebas nuevas antes de cualquier cambio de lógica.
Las pruebas seguirán sin red y sin necesitar los originales locales.
**Archivos:** docs/sources/senamhi.md, configs/sources.yaml, tests/test_catalog.py si corresponde.
**Dependencia:** pasos 2 y 3 con resultados o bloqueos documentados. **Tamaño:** pequeño.

## Decisión antes de ejecutar

Keneth debe confirmar si, ante documentación oficial insuficiente, se mantienen los campos desconocidos
y se prepara una consulta para su revisión (recomendado), o se detiene toda la tarea hasta obtener
respuesta oficial. En ambos casos, no se asumirá permiso ni se enviará la consulta automáticamente.
La aprobación autoriza la investigación acotada de los pasos anteriores, no publicar datos ni contratar
servicios. No se han descargado documentos ni iniciado la verificación sustantiva en esta planificación.
