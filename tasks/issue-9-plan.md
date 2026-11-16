# Plan de #9: adquisición acotada de OEFA y documentación

Estado: propuesta para comentarios de Keneth; sin implementación ni descargas nuevas autorizadas.
Responsable: @keneth-arias. Dependencias #5 y #7 cerradas; PR #45 integrado.
Lista de tareas: issue #9 en GitHub. Completar #8 primero para mantener una tarea activa.

## Insumos y correcciones del plan

La evidencia histórica de docs/sources/oefa.md registra un CSV de 1 317 949 839 bytes por Content-Range
(aproximadamente 1,23 GiB), y una porción inicial de 65 536 bytes con 123 filas completas de una estación.
No se volvió a consultar el servidor durante esta planificación: el tamaño/versionado pueden cambiar.
El prefijo no demuestra cobertura nacional, de Lima, continuidad ni representatividad.

El diccionario (54 517 bytes) y metadatos (16 025 bytes) descargados en la revisión de Keneth existen
en un directorio temporal de evidencia y coinciden entonces con los hashes del PR #45. Verificarlos y
preservarlos bajo data/raw/oefa/ en la ejecución aprobada, antes de que el temporal desaparezca.
No confundir esos archivos con una nueva descarga ni usar el canal de Keneth para atribuirse la
adquisición original de Cristopher. La muestra CSV y sus encabezados HTTP no están en esta copia;
no afirmar que se verificaron localmente ni leer/modificar su copia sin una entrega explícita.

## Dos prerrequisitos técnicos antes de transferir el CSV

1. **Dialecto CSV explícito (mediano, 3–5 archivos).** El CSV de OEFA usa punto y coma según la
   evidencia de #45; validate_format hoy usa csv.reader con coma. Agregar un delimitador declarado y
   acotado al contrato, valor predeterminado coma para compatibilidad, sin autodetección ni conversión
   de originales. La validación y la identidad de contrato/caché deben distinguir delimitadores;
   versionar/migrar manifiestos explícitamente cuando corresponda, manteniendo verificables los
   manifiestos SENAMHI previos. Pruebas primero: CSV con punto y coma/comillas, filas inconsistentes,
   delimitador equivocado, contrato/cache incompatibles y regresiones de coma/manifiestos históricos.
2. **Canal HTTP para recurso público estático (mediano, 3–5 archivos; PR separado si crece).**
   El motor acotado actual exige method=api y documentación API. El enlace del CSV no es una API:
   no falsificar method/api_documentation_url para hacerlo pasar. Propuesta sujeta a aprobación de
   Keneth: agregar un canal explícito de archivo público con URL de catálogo/procedencia, reutilizando
   las reglas HTTP, presupuesto, checksum, caché y publicación existentes. HTTPS, hosts exactos,
   DNS público, identidad de cliente honesta, sin credenciales/redirecciones ni proxies heredados.
   Lightpanda resuelve/revisa el catálogo primero; el canal de transferencia se documenta desde el
   inicio, no se usa como fallback silencioso después de un bloqueo. Registrar 403/418/autenticación
   y detenerse; no cambiar identidades para eludirlos. Si el canal seguro no se aprueba o no funciona,
   registrar bloqueo del CSV y continuar únicamente con documentación local verificada.

No ampliar el alcance a API genéricas, scraping, EAC, informes anexos masivos o normalización.
No repetir el comando curl histórico como un nuevo descargador sin límites compartidos.

## Ruta de adquisición propuesta después de aprobar

1. Inventariar evidencia local y promover por conservación los dos documentos; resolver las URL
   oficiales con Lightpanda y registrar fecha/canal. No descargar de nuevo una versión ya verificada.
2. Estimar sin red a partir de tamaños históricos, distinguiendo observado/declarado/desconocido.
   Tras aprobar los prerrequisitos, una consulta de rango de hasta 64 KiB al recurso confirma tamaño, validadores y
   soporte real de rango; incluir sus bytes en el presupuesto. Si faltan tamaño/validadores, registrar
   la limitación: sin tamaño confirmado o si supera el techo de la ejecución, detener para consultar;
   sin ETag fuerte no prometer reanudación, aunque sea posible una descarga completa acotada.
3. Descargar el CSV completo solo con el ámbito/budget aprobados. Leer por chunks, preservar parciales
   identificados y versiones; reanudar únicamente con ETag fuerte y Content-Range coherentes. No usar
   un hash del prefijo como hash del archivo completo ni un ETag como prueba de integridad.
4. Validar CSV rectangular con dialecto explícito y estructura Office, sin alterar bytes ni fechas.
   Registrar SHA-256 propio completo, tamaño real, URL/canal, versión/validadores, recurso y manifiesto.
   Una versión nueva produce otro original; la diferencia de tamaño no se oculta como la misma versión.
5. Verificar reutilización offline dos veces, sin otra transferencia ni copias del original; registrar
   que reused por integridad local no equivale a una respuesta 304 del servidor.
6. Entregar informe/catálogo de fuente y documentación para #10/#11, sin subir datos masivos.
   No convertir UTM ni afirmar unidades/reloj/códigos especiales antes de resolver su significado.

## Presupuesto recomendado para decisión de Keneth

- Ámbito recomendado: un CSV nacional completo, diccionario y metadatos, ya que un prefijo no permite
  medir cobertura para #10/#11. No adquirir EAC ni anexos del repositorio.
- **Máximo total: 2 GiB (2 147 483 648 bytes) de payload de red para la ejecución**, incluidas consultas,
  documentos que falten, fallos y reinicios. Máximo por CSV en esa ejecución: 2 GiB; por documento: 1 MiB.
  Estos son límites propuestos; el techo global de 1000 GiB por archivo se mantiene, no se reserva.
- Una tarea de red a la vez, hasta tres intentos y plazo cooperativo de 1200 s para el CSV. Presupuesto
  agotado/plazo/bloqueo: detener y registrar. No reiniciar el contador automáticamente para seguir.
- Exigir al menos 5 GiB libres y volver a verificar espacio para parcial + publicación; no prometer
  disponibilidad permanente ni descargas gratis de tráfico. Contador de payload excluye TLS/cabeceras;
  el chunk ya recibido puede exceder el límite antes de abortar, igual que el contrato de #7.
- Si el recurso crece por encima del techo, cambia de esquema o no hay un tamaño confirmado, presentar
  nueva estimación y pedir feedback antes de transferir. No aprobar tamaños desconocidos por defecto.

Alternativa de alcance: documentación + muestra realmente acotada y etiquetada como prefijo; cumple
una entrega de investigación/bloqueos, pero no permite prometer perfilamiento completo ni cobertura
para cerrar #10/#11. No convertir esa alternativa en selección de fuente por conveniencia.

## Entregas y verificación

Prerrequisitos: pruebas enfocadas y cambios mínimos en acquisition/{models,formats,store,cache,transfer,cli}
según contrato final; separar PR por dialecto/canal cuando superen una entrega revisable.
Adquisición: plan declarativo sin secretos, reports/acquisition/oefa.md, actualización de
configs/sources.yaml y docs/sources/oefa.md; originales/manifiestos operativos bajo data/, fuera de Git.

- [ ] Compatibilidad CSV/dialecto y canal público explícito aprobados y probados antes de transferir.
- [ ] Cada recurso tiene bytes comprobados y manifiesto, o bloqueo concreto fechado y separado.
- [ ] Parciales se identifican como parciales; no se publican como CSV completos ni representativos.
- [ ] Segundo recorrido offline reutiliza originales/manifiestos; presupuesto real queda documentado.
- [ ] Catálogo e informe separan adquisición, licencia de base y permiso operativo de publicar.
- [ ] make check, make build y make audit aprobados; pruebas de fallo/reanudación con respuestas
  simuladas, sin descargar gigabytes para probar límites. No reducir controles para aceptar OEFA.

ODC-By documentada en #5 no equivale a aprobar atribución final o redistribución en TimeNet.
El significado de fechas, unidades, zonas/datum y marcadores sigue en docs/sources/oefa.md.
#9 entrega insumos verificables o un bloqueo honesto; no sustituye el perfilamiento de #10.
