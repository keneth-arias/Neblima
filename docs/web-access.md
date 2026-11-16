# Consulta web y descarga con Lightpanda

Por decisión de Keneth, Lightpanda es el medio inicial para consultar páginas web y descargar
sus recursos. Esta regla aplica al equipo completo: las carpetas locales no incluyen un navegador
ni una sesión compartida. Quien no tenga Lightpanda debe configurar su propia instalación o pedir
que Keneth ejecute la consulta y entregue la evidencia. La validación local y CI no lo necesitan.
No agregar claves, cookies ni sesiones de otra persona al repositorio.

1. Abrir la página oficial con Lightpanda goto y un tiempo de espera acotado (10–20 segundos).
2. Registrar URL solicitada, URL final, fecha UTC, código HTTP si está disponible, título y resultado.
   Inspeccionar tree/extract/evaluate para distinguir contenido, portada genérica y página de error.
3. Resolver enlaces de recursos con links o extract. Un HTTP 200 de una portada no verifica el conjunto.
4. Descargar un recurso autorizado con Lightpanda download. Crear primero la carpeta de destino;
   si la herramienta solo admite un nombre relativo, mover luego el archivo a data/raw/<fuente>/.
5. Mantener los bytes originales; registrar URL, tamaño real, SHA-256, formato observado y fecha.
   Dejar nulo el código HTTP del archivo si download no lo expone. Verificar que no sea una página HTML.
6. Si hay 403, 404, autenticación o tiempo agotado, registrar el canal y el motivo; conservar el candidato
   y proponer una alternativa oficial. No eludir controles ni dar por caído el proveedor entero.

Las API y los archivos masivos requieren un descargador reproducible acotado (#6/#7), separado de la
conversión local. Lightpanda sirve para resolver y comprobar páginas/recursos; esta decisión no instala
una dependencia de navegador en el paquete Python ni en las pruebas sin servicios externos.
No cambiar de herramienta silenciosamente cuando Lightpanda falle. Documentar cualquier alternativa.
Las descargas grandes, cuentas nuevas y pagos mantienen las autorizaciones del plan inicial.

El registro revisable de esta ejecución es metadata/source-access.json. Cada resultado tiene fecha y
próxima acción; un acceso público no determina licencia ni permisos de redistribución.
