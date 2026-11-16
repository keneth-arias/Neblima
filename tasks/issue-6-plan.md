# Plan de #6: adquisición atómica con trazabilidad

Responsable: Keneth (@keneth-arias), liderazgo de datos y plataforma.
Seguimiento y lista de trabajo: [#6](https://github.com/keneth-arias/airaware/issues/6).
Dependencias: #2 y #4. La investigación #4 quedó cerrada con #42; las aclaraciones externas siguen en #43.
Estado: plan aprobado por Keneth; implementación de #6 ejecutada y verificada.
Entrega en PR #44; sin nuevas descargas SENAMHI/OEFA.

## Objetivo

Convertir cada adquisición autorizada en un original local verificable: bytes sin cambios, SHA-256,
manifiesto y resultado completo o ausente ante fallas. El primer caso real reutiliza los originales
SENAMHI disponibles; no requiere descargarlos de nuevo ni resolver sus unidades para preservar bytes.
No se normalizan observaciones, asignan zonas horarias o aprueban derechos en este módulo.

## Decisiones propuestas

- Mantener almacenamiento local, Python/uv y GitHub Actions. Pruebas sin internet y datos sintéticos.
- Lightpanda sigue siendo el canal de páginas y recursos web según docs/web-access.md. El paquete
  Python podrá recibir un archivo de una adquisición Lightpanda explícita y su procedencia; no
  intentará invocar herramientas MCP del agente desde la CLI ni cambiar de canal silenciosamente.
- Separar transferencia de validación/publicación local. Para API documentadas, un adaptador HTTP
  explícito admitirá streaming y transporte simulado. Antes de implementarlo, verificar documentación
  oficial del cliente elegido; agregar una dependencia solo cuando se use. No procesar páginas HTML
  como API ni usar ese adaptador como alternativa automática a una falla de Lightpanda.
- La primera versión no automatiza un navegador completo. La captura Lightpanda y el ingreso local
  deben quedar identificados como operaciones distintas. No registrar como descargado por Python
  un archivo obtenido previamente por otro canal.
- Conservar el CSV y manifiestos SENAMHI existentes. Verificar su suma para reutilización; no moverlos,
  sobrescribirlos ni reescribir metadatos históricos. Un registro de ingreso nuevo apunta al original.
- Evitar un par CSV/JSON parcialmente publicado: preparar archivo y manifiesto en una carpeta temporal
  del mismo sistema de archivos y publicar la carpeta completa mediante cambio de nombre atómico.
  Propuesta para adquisiciones nuevas: data/raw/<source_id>/<sha256>/ con original y manifest.json.
  El manifiesto guarda nombre original seguro, sin usarlo para construir rutas fuera de esa carpeta.
  Incluir vaciado/fsync de archivos y directorios donde se admita; documentar los límites de
  durabilidad del sistema de archivos y probar interrupciones de proceso.
- No sobrescribir destinos: ante uno existente, comprobar bytes/manifiesto y devolver reutilización,
  o fallar si difieren. Definir exclusión entre escritores del mismo recurso antes de publicar.
- Conservar códigos HTTP desconocidos como nulos. Filtrar credenciales y parámetros sensibles de
  registros públicos; autenticación nunca forma parte del manifiesto publicable ni de errores.

## Entregas ordenadas

### 1. Contrato y pruebas de integridad local

Definir entrada, resultado y errores: source_id, URL del recurso, canal de adquisición, ruta temporal,
formato esperado, límite de bytes y SHA-256 esperado opcional. El manifiesto incluye fecha UTC,
URL final cuando se conoce, tamaño real, suma, versión del esquema y validación de formato.
No inventar una fecha de descarga: distinguir obtención, verificación e ingreso.

**Aceptación:** contrato documentado y pruebas escritas primero para éxito, origen incompleto,
rutas peligrosas, cambio de bytes y manifiesto inválido; procedencia sin secretos.
**Verificación:** pytest con archivos sintéticos en tmp_path; cero acceso externo.
**Archivos previstos:** src/airaware/acquisition.py (o paquete pequeño si hace falta),
tests/test_acquisition.py, docs/acquisition.md. **Tamaño:** pequeño.
**Dependencia:** ninguna adicional a #2/#4; no esperar la respuesta de #43.

### 2. Validación y publicación atómica

Implementar copia/lectura acotada y cálculo de suma sin cargar todo el archivo en memoria. Validar
estructura del formato declarado. CSV: rechazar HTML, incluidos errores con HTTP 200 y etiquetas
engañosas; MIME application/octet-stream por sí solo no invalida el CSV SENAMHI. XLSX/DOCX: comprobar
contenedor y miembros esenciales sin ejecutar contenido. JSON de API: comprobar sintaxis y contrato
configurado sin inventar esquema de observaciones. Rechazar formatos no soportados explícitamente.

**Aceptación:** bytes originales idénticos, conjunto archivo/manifiesto visible completo o ausente,
sin daño a originales previos; fallo seguro ante suma incorrecta, tamaño excedido, formato engañoso
o interrupción durante copia/publicación. La reutilización comprueba integridad antes de omitir trabajo.
**Verificación:** simular fallas antes/después del cálculo y antes de publicar; comprobar que un destino
previo conserva bytes y que temporales no se presentan como adquisiciones válidas. Probar colisión de escritores.
**Archivos previstos:** módulo y pruebas del paso 1. **Tamaño:** pequeño.
**Dependencia:** contrato del paso 1.

### Punto de control: integridad antes de red

Revisar el contrato y comprobar con pruebas que una falla no deja datos aparentando estar completos.
No introducir excepciones para hacer pasar el CSV actual. Una fuente sin semántica confirmada puede
preservarse; no puede declararse normalizada ni publicable.

### 3. Transferencia HTTP acotada para API documentadas

Implementar el adaptador explícito con streaming, tiempos de espera y límites. Propuesta inicial:
una transferencia simultánea, hasta tres intentos totales para fallas transitorias; no reintentar 403/404,
fallas de formato ni sumas incorrectas. Respetar Retry-After dentro de una espera máxima propuesta de
30 segundos; si la supera, informar y detenerse. Inyectar reloj/espera para que las pruebas no duerman.
Validar destinos y redirecciones; no reenviar credenciales a otro origen. Usar un límite obligatorio
antes de la transferencia, que siga vigente aunque Content-Length falte o sea incorrecto.

**Aceptación:** HTTP simulado demuestra 200 válido, 200 HTML, 403/404, 429, 5xx, timeout, caída de flujo,
redirección rechazada y contenido excedido; no se publica una adquisición parcial ni se exceden intentos.
No hacer descargas reales de SENAMHI/OEFA para aprobar esta etapa.
**Verificación:** pruebas con transporte simulado y reloj falso; sumar pruebas de suma esperada incorrecta.
**Archivos previstos:** módulo de adquisición, tests/test_acquisition.py y archivo de dependencias/lock
solo si se usa un nuevo cliente. **Tamaño:** mediano.
**Dependencia:** paso 2. La verificación del cliente elegido forma parte del inicio de implementación.

### 4. Entrada de usuario y entrega al equipo

Agregar una entrada mínima en la CLI para registrar/verificar un archivo adquirido con Lightpanda y
para ejecutar una transferencia API explícita. Confirmar los nombres de comandos en el contrato del
paso 1: el plan no los presenta como ya implementados. Errores y ayuda en español del Perú.
Ejemplo SENAMHI: demostrar reutilización del archivo local con su SHA-256, sin red ni cambio del original.

**Aceptación:** rutas basadas en AIRAWARE_DATA_DIR, comandos y guía reproducibles para las tres copias
locales del equipo; salida sin claves; pruebas CLI prueban éxito, reutilización y errores. No modificar
las ramas ni los entornos de Cristopher/Jordan durante la entrega.
**Verificación:** make check, make build, make audit; comandos de la guía probados. El caso real es una
comprobación manual local; CI no depende del CSV descargado ni de Lightpanda instalado.
**Archivos previstos:** src/airaware/cli.py, tests/test_cli.py, docs/acquisition.md.
**Tamaño:** pequeño. **Dependencia:** pasos 2 y 3.

## Límites respecto de #7 y de las tareas científicas

#6 cubre intentos acotados y publicación segura. #7 agrega reanudación por rangos, caché basada en
validadores del servidor, concurrencia configurable, filtros, estimaciones y modo sin red completo.
La reutilización por suma de un archivo ya presente sí es necesaria en #6 para no sobrescribirlo.
#8/#9 usan estas interfaces al adquirir muestras; #10 mide calidad. #13/#17 y la publicación mantienen
los bloqueos específicos de #43. No se puede convertir el cierre de #4 en una licencia confirmada
para cualquier distribución ni en confirmación de UTC.

## Decisiones y bloqueos

No hay bloqueo externo para implementar el núcleo con entradas sintéticas y originales locales.
Los valores de intentos/espera y la disposición por suma son propuestas revisables al aprobar el plan.
Si se quiere automatizar Lightpanda desde las tres máquinas como parte de la CLI, definir primero
su instalación, proceso y protocolo disponible: es una ampliación respecto de esta primera entrega,
no una capacidad que se pueda asumir a partir de las herramientas del agente.
No se contratarán servicios ni se harán adquisiciones masivas durante la implementación.

## Resultado de ejecución

- [x] Contrato Pydantic, errores seguros y manifiesto versionado.
- [x] Validación CSV/JSON/XLSX/DOCX, SHA-256, límites y publicación atómica con exclusión por fuente.
- [x] API públicas explícitas con host autorizado, streaming, tiempos/reintentos y HTTP simulado.
- [x] CLI acquire import-file / acquire api y guía para las copias locales del equipo.
- [x] Reutilización real de CSV, XLSX y DOCX SENAMHI sin red, nuevas copias ni cambios de originales.

Las referencias previas pueden estar bajo raw/<familia> aunque el ID sea de un recurso distinto;
se verifican y se registran por ruta relativa dentro de raw. El límite de JSON de análisis es 8 MiB
y el manifiesto es de hasta 64 KiB. Son controles adicionales documentados, sin reducir el contrato.
Los valores propuestos de intentos/espera se adoptaron. Guía y límites efectivos: docs/acquisition.md.
La reanudación/caché/filtros y concurrencia configurable siguen en #7. #43 mantiene las aclaraciones
externas; la adquisición no confirma semántica ni derechos. Verificación final en la entrega del PR.
