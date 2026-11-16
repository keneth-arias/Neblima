# Adquisición local con trazabilidad (#6 y #7)

Esta herramienta conserva bytes originales y registra su procedencia. No normaliza observaciones
ni confirma unidades, tiempos o derechos. Las aclaraciones SENAMHI siguen en #43.

## Preparar cada copia local

Keneth, Cristopher y Jordan ejecutan desde la raíz de su propia copia, después de actualizarla:

```bash
make setup
make init
uv run --locked airaware acquire --help
```

Usar Python/uv según CONTRIBUTING.md. La implementación de bloqueo y publicación corresponde a Linux
(el entorno local del equipo y los ejecutores Ubuntu de CI). No se probó soporte para Windows.
Cada copia mantiene datos, credenciales y entorno propios. AIRAWARE_DATA_DIR selecciona otra carpeta
base; --data-dir tiene precedencia. Los JSON de solicitudes se pueden guardar en data/staging/;
los datos y manifiestos generados quedan excluidos de Git.

## Registrar un archivo obtenido con Lightpanda

Primero consultar/descargar el recurso con Lightpanda siguiendo [el protocolo](web-access.md).
La CLI no instala ni invoca el navegador o las herramientas MCP del agente. Registrar el canal
real: lightpanda para esa descarga, local para otro original local identificado explícitamente.
La procedencia declarada por quien importa el archivo sigue necesitando evidencia de la fuente.

Crear una solicitud JSON. Ejemplo sintético para un CSV pequeño, con contenido de al menos dos
columnas y una fila de datos:

```json
{
  "source_id": "demo",
  "resource_url": "https://example.org/data.csv",
  "method": "lightpanda",
  "format": "csv",
  "max_bytes": 1000000
}
```

Guardar como data/staging/request.json y ejecutar, reemplazando la ruta por el archivo adquirido:

```bash
uv run --locked airaware acquire import-file --spec data/staging/request.json --file ruta/al/original.csv
```

max_bytes es obligatorio y nunca puede superar **1000 GiB (1 073 741 824 000 bytes)**. expected_sha256 es opcional, pero debe usarse
cuando existe una suma previa confiable. acquired_at requiere zona horaria si se conoce la fecha
real de obtención; dejarlo nulo si se desconoce. verified_at se registra al comprobar bytes. final_url
es opcional para la URL resuelta por Lightpanda: no inventarla. Las URL no admiten usuario/contraseña,
fragmentos ni parámetros con nombres de credenciales habituales. No incluir secretos en ningún campo,
ni siquiera bajo nombres de parámetros diferentes. Esta versión no admite API autenticadas ni firmas URL.

## Reutilizar el CSV SENAMHI existente sin descargarlo

El original está en data/raw/senamhi/, mientras su ID de catálogo es senamhi-lima-csv. No se renombra
ni se duplica. Este ejemplo usa la procedencia ya registrada en #3:

```bash
uv run --locked python - <<'PY'
import json
from pathlib import Path
original = json.loads(Path('metadata/senamhi-lima-download.json').read_text())
request = {
    'source_id': 'senamhi-lima-csv',
    'resource_url': original['source_url'],
    'method': 'lightpanda',
    'format': 'csv',
    'max_bytes': 70000000,
    'expected_sha256': original['sha256'],
    'acquired_at': original['retrieved_at_utc'],
}
p = Path('data/staging/senamhi-acquisition-request.json')
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(request, indent=2) + '\n')
PY
uv run --locked airaware acquire import-file --spec data/staging/senamhi-acquisition-request.json --file data/raw/senamhi/senamhi_lima_monitoreo_1.csv
```

Salida JSON: artifact (original verificado), manifest (registro local) y reused. Para un original ya
bajo raw, reused es true desde el primer registro: se reutilizan sus bytes, aunque se cree el primer
manifiesto de adquisición. Repetir la operación verifica otra vez tamaño, suma, formato y manifiesto,
sin reescribir el registro previo. Si cambia el contrato/procedencia incompatible o el destino está
corrupto, falla y conserva los archivos para revisión.

## API públicas documentadas

Usar acquire api solo al elegir explícitamente una API documentada. No usarlo para sustituir
Lightpanda después de un 403 ni para descargar páginas. Esta es una plantilla, no una API real:

```json
{
  "source_id": "demo-api",
  "resource_url": "https://api.example.org/data?region=lima",
  "api_documentation_url": "https://api.example.org/docs",
  "method": "api",
  "format": "json",
  "json_required_keys": ["results"],
  "max_bytes": 1000000
}
```

Con una solicitud real revisada y un host exacto autorizado:

```bash
uv run --locked airaware acquire api --spec data/staging/api-request.json --allow-host api.example.org
```

El adaptador exige HTTPS en puerto 443 y una lista explícita de hosts; comprueba que todas las IP
resueltas sean públicas y no multicast. Rechaza redirecciones, cookies entre intentos, compresión HTTP
y respuestas distintas de 200/206/304 (salvo errores transitorios que se reintentan). No hereda proxies del
entorno ni envía cabeceras de autenticación. La comprobación DNS y la conexión son operaciones
separadas: no fija la IP frente a cambios DNS entre ambas. Es una CLI local para fuentes autorizadas,
no un servicio de descarga para URL suministradas por terceros.

Máximo: tres intentos por recurso; connect timeout de 5 s, lectura/escritura/pool
de 10 s y presupuesto de 60 s comprobado entre operaciones/chunks. Una operación de red o DNS ya
iniciada puede terminar después del presupuesto; no se promete un corte de proceso a los 60 s.
Retry-After admite segundos o fecha HTTP hasta 30 s; valores inválidos/excesivos detienen la operación.
Sin esa cabecera se esperan 1 y 2 s antes de los intentos segundo y tercero. Solo 429, 500, 502, 503,
504 y fallas del transporte se reintentan. Formato, suma, límites y 403/404 no generan otro intento.

## Formatos y almacenamiento

- CSV UTF-8/UTF-8 BOM: encabezados no vacíos/únicos, dos o más columnas y filas de igual longitud,
  al menos una fila de datos. Rechaza HTML en encabezados y bytes NUL. No interpreta medidas ni fechas.
  Los campos están sujetos al límite estándar del lector csv de Python; no se amplía globalmente.
- JSON: objeto con las claves json_required_keys, sin claves duplicadas ni constantes NaN/Infinity;
  hasta 8 MiB para análisis. Es una comprobación de claves, no validación científica de valores/tipos.
- XLSX/DOCX: contenedor ZIP y XML esenciales, CRC, sin cifrado/macros/DOCTYPE/ENTITY; XML con NUL
  (incluido UTF-16) se rechaza. Máximo 512 miembros, 8 MiB por miembro, 32 MiB descomprimidos y razón
  de compresión 200. No extrae archivos ni ejecuta contenido; no certifica todo el documento Office.

Para adquisiciones nuevas desde fuera de raw, se prepara una carpeta .pending-* dentro de la fuente,
con original.<formato> y manifest.json. Se verifican suma y formato, se vacían archivos/directorios
con fsync cuando se admite y se publica la carpeta mediante rename en el mismo sistema de archivos:

```text
data/raw/<source_id>/<sha256>/original.csv
data/raw/<source_id>/<sha256>/manifest.json
```

Los originales que ya están bajo raw se registran mediante storage: reference y ruta relativa al
raw local; no se copian ni se vuelven inmutables por software. Deben mantenerse sin cambios y conservarse
junto con sus manifiestos. Los paquetes nuevos usan storage: bundle. Un manifiesto ocupa como máximo
64 KiB; original_name conserva el nombre local saneado cuando se recibe, sin usarlo para construir rutas.
El resultado es completo o ausente ante fallas previas a publicación. Una falla posterior a rename
puede dejar un paquete completo: la siguiente operación lo verifica antes de reutilizarlo.

Se rechazan enlaces simbólicos en destinos/referencias y se excluyen escritores simultáneos por fuente
mediante flock no bloqueante: un segundo escritor falla sin sobrescribir. El archivo de bloqueo puede
permanecer; el sistema libera el bloqueo al cerrar el descriptor o terminar el proceso. Ante una caída
abrupta pueden quedar carpetas .pending-*; no son adquisiciones completas ni se usan como referencias.
No se borran automáticamente carpetas de otras ejecuciones. Atomicidad/durabilidad dependen del
sistema de archivos local; no se asume ese comportamiento en almacenamiento remoto o distribuido.

## Verificación y entrega de #6

make check ejecuta pruebas sin red: contrato, archivos engañosos, contenedores corruptos, límites,
manifiesto inválido, caída de copia/publicación, escritor competidor y HTTP simulado con reloj/espera
inyectados. make build y make audit completan los controles. No se descargan conjuntos en CI.

Demostración local: CSV SENAMHI verificado y comando repetido con reused=true, 68 501 558 bytes y
SHA-256 896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4. También se validaron
XLSX/DOCX reales por referencia, sin red, copias nuevas ni cambios en sus originales/manifiestos previos.
El manifiesto de adquisición es nuevo y distinto de la evidencia histórica de #3/#4, que se conserva.

La CLI API agrega caché condicional, reanudación y presupuestos mediante #7 (ver abajo).
Las decisiones de unidades, reloj y publicación continúan en #43.

Referencias verificadas con Lightpanda: [HTTPX streaming](https://www.python-httpx.org/quickstart/#streaming-responses),
[transportes simulados](https://www.python-httpx.org/advanced/transports/#mock-transports) y
[rename de Python](https://docs.python.org/3/library/os.html#os.rename).


## Caché, reanudación y límites de API (#7)

El máximo de 1000 GiB por archivo es un techo autorizado por Keneth, no una estimación de tamaño,
una reserva de disco ni una descarga solicitada. Conviene fijar max_bytes cerca del tamaño previsto.
Los límites estructurales de JSON y Office siguen siendo más pequeños y no cambian.

La CLI `acquire api` usa el motor con caché; la función histórica `http.fetch_api` conserva su
comportamiento simple para consumidores anteriores. Se verifican suma, estructura y contrato antes
de reutilizar un original. ETag o Last-Modified permiten una consulta condicional; un 304 no evita
la verificación local. Sin validador se solicita la representación completa.

```bash
uv run --locked airaware acquire api --spec data/staging/api-request.json --allow-host api.example.org --budget-bytes 2000000 --deadline-seconds 120
uv run --locked airaware acquire api --spec data/staging/api-request.json --allow-host api.example.org --offline
```

`--offline` no consulta red ni DNS; falla si no existe un original verificable. `--refresh` reinicia
el parcial y consulta sin condición; no se combina con offline. El presupuesto de payload incluye
bytes recibidos en intentos fallidos, reinicios y reanudaciones. Sin --budget-bytes, una consulta API
usa max_bytes como presupuesto total. No es un contador de tráfico físico: excluye TLS/cabeceras;
el chunk que supera el límite ya se recibió y se contabiliza antes de abortar. Con concurrencia,
las respuestas que ya estaban en curso también pueden entregar un chunk. No se inician solicitudes
nuevas cuando el presupuesto ya está agotado. El plazo configurable admite hasta 86 400 segundos
por recurso y sigue siendo cooperativo entre operaciones.

Los parciales y su estado atómico quedan en data/.acquisition-cache/<clave>/, fuera de Git.
Cada checkpoint registra tamaño y SHA-256; una cola no confirmada tras una caída se recorta solo
cuando el prefijo registrado pasa la verificación. Un parcial alterado o sin procedencia falla sin
sobrescribirse. Se anexa únicamente con ETag fuerte idéntico y 206/Content-Range coherentes.
Un 200 reinicia desde cero; un 416 no prueba integridad. Sin ETag fuerte se reinicia la transferencia.
La publicación final mantiene la validación de #6 y registra el estado HTTP realmente observado.

Se comprueba espacio libre para el parcial y la copia temporal de publicación más 64 KiB; si falta
Content-Length, se usa max_bytes para el cálculo conservador. No se preasigna el tamaño autorizado.
El espacio puede cambiar durante una transferencia: una falla de escritura no publica un parcial.
Un cambio de contenido produce otra versión por SHA-256 sin reemplazar los originales anteriores.
Cache-Control: no-store impide conservar un índice HTTP reutilizable o un parcial para otra solicitud;
el archivo adquirido deliberadamente se conserva como original del proyecto, separado de esa caché.
No se implementa un proxy ni una caché HTTP general; un cierre abrupto puede dejar un parcial marcado
para eliminación al siguiente acceso, después de verificar que pertenece a este recurso.

Protocolo consultado con Lightpanda el 16/11/2026:
[RFC 9110: condiciones y rangos](https://www.rfc-editor.org/rfc/rfc9110.html) y
[RFC 9111: no-store](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2.5).
