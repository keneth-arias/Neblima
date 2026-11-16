# Plan de #7: reanudación, caché y presupuestos de adquisición

Responsable: Keneth. Depende de #6 (cerrada). Autorización: planificar e implementar tareas asignadas.
Decisión del usuario: máximo **1000 GiB por archivo**; presupuesto total explícito por lote.
No se necesitan datos nuevos ni aclaraciones de #43 para probar el protocolo con respuestas simuladas.

## Contrato de ejecución

- Mantener acquire import-file y acquire api compatibles. Ampliar API con opciones de caché/reanudación
  sin sustituir Lightpanda para páginas/recursos web. Caché y parciales quedan locales, fuera de Git.
- Parciales con tamaño/hash registrado y validador fuerte ETag. If-Range con Range bytes=<offset>-;
  solo anexar 206 con Content-Range y ETag coherentes. Un 200 reinicia desde cero; 416 no prueba integridad.
  Sin validador fuerte no reanudar automáticamente. Contenido final pasa validación y publicación de #6.
- Caché condicional con ETag o Last-Modified; 304 solo reutiliza un paquete que vuelva a pasar SHA-256,
  formato y contrato. No asumir que un nombre de carpeta o estado de caché acredita bytes correctos.
- Un presupuesto de bytes de red por ejecución y tiempo/reintentos acotados; contabilizar intentos,
  reinicios y respuestas completas. Verificar espacio libre antes de transferir cuando el tamaño se conozca;
  detenerse si el espacio no alcanza. No reservar/copiar un archivo de 1000 GiB para probar el límite.
- Lotes seleccionables por fuente, fecha y región desde entradas de un plan explícito; filtrar metadatos
  de recursos, no filas de observaciones ni cobertura científica. Carpeta elegida por AIRAWARE_DATA_DIR.
- Modo estimación/dry-run sin GET/HEAD ni DNS: tamaños declarados/locales separados de desconocidos.
  El máximo autorizado no se presenta como tamaño esperado. Modo offline solo devuelve originales
  verificados; si falta alguno, falla sin red. Concurrencia acotada por opción y mismo recurso sin duplicar.

## Entregas verificables

1. Estado local y contrato: ampliar límite, metadatos de recurso/lote y pruebas de filtros/presupuesto.
   Archivos: models.py, batch.py, tests/test_acquisition_batch.py; pequeño/mediano.
2. Caché y reanudación: pruebas primero de 304, 206, 200 al ignorar Range, ETag cambiado/débil,
   Content-Range erróneo, 416, parciales alterados, interrupciones y caché corrupta. Estado atómico,
   exclusión por recurso y originales intactos. Archivos: transfer.py, http.py, pruebas HTTP; mediano.
3. Lotes/CLI: planificación sin red, offline comprobado, filtros inclusivos documentados y concurrencia
   limitada, presupuesto de red compartido. Archivos: batch.py, cli.py y pruebas; mediano.
4. Guía del equipo y entrega: make check, build, audit, Python 3.11/3.13 y caso SENAMHI sin red ni copias.
   Actualizar #7 con evidencia y conservar los límites científicos de #43.

## Fuentes del protocolo

RFC 9110, secciones 13.1.2/13.1.5, 14 y 15.3.7/15.4.5/15.5.17:
https://www.rfc-editor.org/rfc/rfc9110.html. Consultado con Lightpanda al iniciar implementación.
HTTPX streaming y transporte simulado: fuentes fijadas en el módulo de #6.
Documentar cómo se aplican las condiciones; no interpretar rango/304 como aprobación científica.

## Puntos de control

- No ampliar código de red antes de pasar pruebas de selección, presupuesto y contrato local.
- No publicar un parcial ni concatenar versiones diferentes; verificar todos los caminos de reinicio.
- No ejecutar lotes reales grandes para probar controles. Consultar decisiones de ámbito, semántica,
  almacenamiento o costes si no quedan resueltas con la autorización existente.


## Resultado local: 16/11/2026

Implementados los cuatro incrementos. La decisión de 1000 GiB es el techo por archivo, separado del
presupuesto total de lote. Motor API con caché verificada, reanudación fuerte y publicación de #6;
CLI con filtros, estimación sin red, offline y hasta cuatro tareas. No-store no conserva parciales
reutilizables; los originales adquiridos se mantienen como archivos del proyecto.

make check: 146 pruebas aprobadas en Python 3.13.13, formato, tipos y catálogo sin errores.
Las pruebas de regresión incluyen parcial corrupto, no-store tras caída, presupuesto agotado antes
de nueva solicitud, 304/206 inválidos y preservación de versiones. SENAMHI offline: 68 501 558 bytes,
reused=true, errors=[], network_bytes=0. El presupuesto no cuenta TLS/cabeceras y puede excederse por
el chunk ya recibido; esta limitación se declara en docs/acquisition.md.

La documentación incluye los comandos para las tres copias locales. No se cambian ramas ni entornos
de Cristopher/Jordan. Los PR se separan por fundamento, refactor HTTP, motor y CLI/lotes; #7 se cierra
al integrar toda la cadena. #11 sigue esperando #9/#10; la investigación normativa #20 puede avanzar
sin escoger unidades/reloj ni completar etiquetas antes de #18.

Verificación adicional: 146 pruebas aprobadas en Python 3.11 después de sincronizar el entorno
con uv sync --locked; make build generó sdist/wheel y make audit no encontró vulnerabilidades
conocidas. La primera ejecución de Python 3.11 detectó un entorno antiguo sin HTTPX; se actualizaron
sus dependencias fijadas y se repitió la suite completa, sin cambiar código ni controles.

Revisión de entrega: corrección (rangos, caché, reinicios y ausencia de red), legibilidad por módulos,
separación transporte/publicación, límites frente a respuestas no confiables y lectura por chunks.
Sin dependencias nuevas ni supresiones. Se revisaron las limitaciones DNS, tiempo cooperativo,
conteo de payload, archivo deliberado de no-store y bloqueos Linux; están declaradas en la guía.
Pruebas de cada corte desde git archive: fundamento 119, refactor 119 y motor 139 aprobadas.
Wheel instalado en entorno independiente: acquire batch --dry-run reconoce el SENAMHI local.
