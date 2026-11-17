# Adquisición OEFA: CSV completo con Lightpanda e historial de canales (#9)

Ejecución aprobada por Keneth, 16/11/2026 UTC. Evidencia fechada y rutas/hash:
metadata/oefa-acquisition-check.json. Presupuesto autorizado de recursos: 2 GiB (2 147 483 648 bytes),
una tarea de red, plazo cooperativo de 1200 s y mínimo 5 GiB libres antes de transferir.
Se implementaron primero los prerrequisitos de dialecto CSV y canal público explícito (#53/#54).

## Resultado del primer intento por canal controlado

| Recurso | Resultado real |
| --- | --- |
| Catálogo | Lightpanda HTTP 200; se resolvieron nuevamente los tres enlaces oficiales |
| Diccionario XLSX | 54 517 bytes; SHA coincide con #45; conservado desde la evidencia local de revisión |
| Metadatos DOCX | 16 025 bytes; SHA coincide con #45; conservado desde la misma evidencia local |
| CSV nacional | **Bloqueado por HTTP 418** en la primera consulta de rango; no hay original completo |

Los documentos se publicaron localmente en carpetas raw por recurso/SHA con manifiestos de
adquisición. No se volvieron a descargar y no se atribuyen a una descarga nueva. La hora exacta de
la descarga previa se conserva como desconocida; las fechas actuales corresponden a verificación.
Dos ejecuciones offline del plan documental reutilizaron ambos recursos con network_bytes=0,
sin cambios en originales o manifiestos. El plan documental es reproducible desde cualquier copia
que disponga de esos originales con las rutas y sumas declaradas.

## Bloqueo del CSV, sin generalizaciones

URL: la registrada como resource_url en configs/acquisition/oefa-csv.json y en la evidencia.
Canal: http_file de AirAware, host www.datosabiertos.gob.pe, HTTPS, User-Agent honesto AirAware,
Range bytes=0-65535, sin autenticación, cookies heredadas, redirecciones ni cambio de identidad.
El servidor respondió 418, por lo que se cerró la respuesta sin consumir/publicar su cuerpo,
sin reintentar ni pasar a curl/otro canal. No se descargó la porción de 64 KiB solicitada ni el CSV.
El contador de payload de recursos quedó en 0; no es una medida de tráfico físico: excluye TLS,
cabeceras, buffers de transporte y la consulta de catálogo de Lightpanda, cuyo tráfico no fue expuesto.

El tamaño de 1 317 949 839 bytes y la muestra de 123 filas registrados en #45 siguen siendo evidencia
histórica, no una medición de esta ejecución. No se confirma el tamaño/ETag actual ni se importa
ese prefijo como conjunto representativo. La portada accesible no prueba acceso del canal al archivo;
418 aquí tampoco demuestra que el proveedor entero o todos los canales estén caídos.
El catálogo distingue el CSV bloqueado de la familia documental verificada y conserva las URLs.

## Reproducción local y siguiente paso

```bash
uv run --locked airaware acquire batch --plan configs/acquisition/oefa-documents-local.json --offline --budget-bytes 0
uv run --locked airaware acquire batch --plan configs/acquisition/oefa-documents-local.json --offline --budget-bytes 0
```

El comando de transferencia aprobado, para ejecutar solo cuando se resuelva el acceso o se acuerde
una nueva consulta, es:

```bash
uv run --locked airaware acquire file --spec configs/acquisition/oefa-csv.json --allow-host www.datosabiertos.gob.pe --budget-bytes 2147483648 --deadline-seconds 1200
```

No reiniciarlo automáticamente para evadir el bloqueo ni renovar el presupuesto. Hace falta una
vía de acceso oficial compatible con los controles o una entrega local verificable del original.
No se enviaron consultas institucionales ni se usaron credenciales/cuentas nuevas.
Si el proveedor entrega otro recurso/versión o cambia el tamaño, registrar su procedencia y límites
antes de transferir. Consultar a Keneth antes de cambiar el canal aprobado, el presupuesto o el alcance.

En ese primer intento, #9 quedó abierta por el CSV pendiente. La documentación y el soporte de adquisición están entregados,
pero no permiten afirmar cobertura o calidad de señales OEFA para #10/#11. #10 puede comenzar con
el SENAMHI adquirido en #8 y mantener el bloqueo OEFA por separado. No se eligieron estaciones ni
se convirtieron UTM, tiempo, unidades o marcadores de ausencia. ODC-BY-1.0 corresponde a la base;
los avisos/atribución para una publicación concreta permanecen pendientes de revisión.

## Validación de entrega

make check aprobado (179 pruebas y controles estáticos), make build aprobado y make audit sin
vulnerabilidades conocidas; 179 pruebas también aprobadas en Python 3.11. Un wheel instalado en
un entorno independiente reutilizó ambos documentos con cero bytes de red. La prueba del catálogo
mantiene la evidencia histórica de 37 candidatos y exige la evidencia nueva, fechada, del 418 del
CSV; no se reescribe la historia ni se ignora la diferencia entre portada y recurso.


## Resultado actual: descarga completa con Lightpanda

Keneth solicitó expresamente usar Lightpanda download y proceder sin objeción de tamaño para esta
transferencia. La herramienta guardó 1 317 949 839 bytes; no expuso el código HTTP exacto del archivo,
por lo que se conserva como nulo. El resultado exitoso no borra el 418 anterior del otro canal.

Original local: data/raw/oefa/oefa_eas_20261116.csv. SHA-256 completo:
1f09a8064ee0aed0b3a9a0a90b96f63ce226b45a969dace49f73e45134f26d92.
La validación completa aceptó UTF-8 BOM, punto y coma, 36 columnas y 2 883 877 filas de datos,
rectangulares. Se registró por referencia sin copiar el archivo masivo; la repetición local verificó
otra vez suma/estructura y reutilizó el mismo original/manifiesto sin reescribirlos.

Evidencia: metadata/oefa-lightpanda-download.json. Plan local portable:
configs/acquisition/oefa-csv-local.json. La hora exacta de descarga no fue expuesta; se registra la
hora observada de verificación, sin presentarla como metadato científico de la fuente.

```bash
uv run --locked airaware acquire batch --plan configs/acquisition/oefa-csv-local.json --offline --budget-bytes 0
```

El CSV ya está disponible para #10 junto con los documentos de #9. Los conteos estructurales no
acreditan estaciones válidas, continuidad, zona horaria, sistema geodésico ni unidades de cada señal.
La publicación permanece pendiente de revisión de derechos/atribución. No se normalizó ni se subió
el CSV a Git. #9 puede cerrarse con esta adquisición al integrar la evidencia actualizada.

Verificación de esta actualización: make check (180 pruebas y controles estáticos), make build y
make audit aprobados; 180 pruebas también en Python 3.11. Las pruebas exigen el estado adquirido
actual y conservan por separado la evidencia del fallo histórico del otro canal.
