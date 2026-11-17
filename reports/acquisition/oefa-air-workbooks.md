# Descarga de IPASH, EAC, EAF y EAT — componente aire

Los cuatro recursos solicitados por Keneth se descargaron con Lightpanda el 17/11/2026 UTC.
Las URL indicadas se resolvieron a archivos XLSX, no CSV. Cada archivo permanece separado y con
sus bytes originales; no se une a EAS ni se transforma en mediciones normalizadas.

## Archivos preservados

| Recurso | Archivo local | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| IPASH | data/raw/oefa-air-evaluation/IPASH_Aire.xlsx | 146 427 | 9f7032e246992fd28e066916191481c7b6afb6c07179adeaa7cd9e35bae88ea1 |
| EAC | data/raw/oefa-air-evaluation/EAC_Aire_0.xlsx | 13 682 203 | 068ade20115394200d18be9ad759477941c382e988da218c90b350348a22a7d5 |
| EAF | data/raw/oefa-air-evaluation/EAF_Aire_0.xlsx | 1 776 627 | edbb5e45087a4dbb99c6d905643b901069726e55193f6ea89bb8bafd184831aa |
| EAT | data/raw/oefa-air-evaluation/EAT - Aire.xlsx | 294 972 | 5b7f27e399912cd5efd7fc2049fcda6421859e028f4d9cbf397a6994c568e0fa |

Las URL resueltas, fichas solicitadas, tamaño real, fecha, encabezados y límites de importación están
en [metadata/oefa-air-workbooks-download.json](../../metadata/oefa-air-workbooks-download.json).
Lightpanda informó bytes guardados y MIME XLSX; no expuso un código HTTP exacto del archivo.
No se inventó HTTP 200. Los fragmentos vacíos de las URL solicitadas se omitieron al consultar.

## Verificación de formato

Se comprobó SHA-256 de cada copia contra el archivo descargado, apertura ZIP, miembros sin cifrado
ni macros, estructura de libro y CRC de todos los miembros. Los cuatro tienen una hoja llamada Aire.
Se inspeccionó su XML por streaming, sin ejecutar macros ni fórmulas ni añadir dependencias al proyecto.
La inspección de estos cuatro archivos conocidos se limitó a 256 MiB descomprimidos por archivo;
no sustituye ni modifica los límites del importador de producción.

IPASH y EAT tienen 23 encabezados; EAC y EAF tienen 24, incluyendo Caracterización de la muestra.
Todos presentan campos de parámetro/valor/unidad y de inicio/fin. El conteo de elementos XML de fila,
incluyendo encabezado, es 1 331 / 135 723 / 17 610 / 2 941 respectivamente. No es un conteo validado
de observaciones únicas, celdas completas ni ventanas horarias.

## Importación genérica y límites conservados

IPASH y EAT se registraron con el motor existente y tienen manifiestos verificables. El plan
[compatible-local](../../configs/acquisition/oefa-air-workbooks-compatible-local.json) incluye
**solo esos dos recursos** para reutilización sin red:

```bash
uv run --locked airaware acquire batch --plan configs/acquisition/oefa-air-workbooks-compatible-local.json --offline
```

EAC y EAF están descargados y comprobados por hash/CRC, pero aún no tienen manifiesto del importador
genérico. Este limita cada miembro Office a 8 MiB y el total a 32 MiB. EAC tiene un miembro de
137 535 869 bytes y EAF uno de 17 595 436 bytes; EAC también supera el total. No se quitó ni aumentó
el guard ni se etiquetó como importación exitosa una operación rechazada por ese contrato.
Una futura tarea de lectura XLSX grande deberá agregar soporte por streaming y pruebas antes de
integrarlos en el motor. Los originales quedan disponibles para esa tarea.

## Alcance científico y trazabilidad

Las cuatro descargas están completas. No se evaluó aún licencia por producto, continuidad, geografía,
zonas horarias, unidades por parámetro ni relación/duplicación con otras exportaciones. No se hereda
la licencia o diccionario de EAS a IPASH/EAC/EAF/EAT ni se habilita un benchmark por descargar archivos.
Se conservan los ID de adquisición separados: oefa-ipash-aire, oefa-eac-aire, oefa-eaf-aire y oefa-eat-aire.
Los nuevos recibos amplían los recursos locales; no se modifican todavía el inventario científico ni
los candidatos de configs/benchmark.yaml. Los libros masivos permanecen fuera de Git.

Validación de entrega: make check (222 pruebas, formato, tipos y catálogo), make build y make audit
aprobaron. La reutilización offline de IPASH/EAT completó sin errores y con cero bytes de red;
se volvieron a comprobar las cuatro sumas SHA-256. Ningún libro se agregó al repositorio Git.
