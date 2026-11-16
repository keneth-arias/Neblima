# Plan de #8: adquisición reproducible de SENAMHI Lima

Estado: plan aprobado por Keneth y ejecución local completada; entrega para revisión/integración.
Responsable: @keneth-arias. Dependencias #4 y #7 cerradas. Lista de tareas: issue #8 en GitHub.

## Qué cambia respecto del plan inicial

El CSV y su documentación ya existen en la copia de Keneth y fueron registrados por #6/#7.
No volver a descargarlos para demostrar adquisición. Se debe entregar un procedimiento repetible,
un inventario revisable y evidencia de reutilización que otra copia local pueda reproducir.
La revisión de planificación solo comprobó existencia/tamaño: no es una nueva verificación de hashes.

| Recurso existente | Tamaño registrado (bytes) | Tratamiento propuesto |
| --- | --- | --- |
| CSV original SENAMHI | 68 501 558 | Verificar y reutilizar por referencia, sin copiar |
| Diccionario XLSX | 10 471 | Verificar y reutilizar por referencia |
| Metadatos DOCX | 41 626 | Verificar y reutilizar por referencia |
| Manual de calidad / evaluación / boletín PDF | 831 789 / 2 291 577 / 3 282 212 | Conservar evidencia documental existente, sin importarlos como CSV/Office |

Fuentes de procedencia: metadata/senamhi-lima-download.json y metadata/senamhi-documentation.json;
las rutas están allí y en docs/acquisition.md. Los PDF no son formatos admitidos por el importador:
conservar sus manifiestos de investigación, sin ampliar el motor para simular que sí lo son.

## Pasos después de aprobar

1. **Preflight local y plan explícito (pequeño, 1–2 archivos).** Resolver AIRAWARE_DATA_DIR;
   comprobar rutas/archivos regulares y contrastar tamaño/hash con evidencia histórica. Confirmar los
   tres manifiestos de adquisición existentes y preservar bytes, nombre y fechas históricas. No usar
   una fecha de verificación como fecha desconocida de descarga. Si hay corrupción o falta un recurso,
   detener ese recurso y reportarlo; no reemplazarlo ni descargarlo silenciosamente.
2. **Registro y repetición sin red (mediano, 3–4 archivos).** Preparar un plan JSON reutilizable de
   CSV/XLSX/DOCX compatible con acquire batch, y ejecutarlo dos veces con --offline --budget-bytes 0.
   Registrar SHA-256, tamaños, rutas de originales/manifiestos y reused. Los dos recorridos verifican
   los mismos archivos; el segundo no modifica sus manifiestos. Usar límites de 70 000 000 bytes para
   CSV y 1 MiB por documento. --dry-run informa tamaños locales sin DNS/HTTP ni escrituras de adquisición.
3. **Informe, catálogo y entrega a #10 (pequeño, 2–3 archivos).** Publicar únicamente plan, informe y
   metadatos pequeños; originales y salidas locales masivas permanecen fuera de Git. Actualizar tamaños,
   enlaces de evidencia y estado de adquisición en configs/sources.yaml sin inventar unidades, reloj,
   permiso de publicación ni estado científico. Mantener informes separados si hay recursos bloqueados.

## Entregas y verificación

Archivos previstos: configs/acquisition/senamhi-local.json (plan declarativo, no secretos),
reports/acquisition/senamhi.md, actualización puntual de docs/sources/senamhi.md y configs/sources.yaml.
Los resultados locales de ejecución quedan bajo data/, fuera de Git. El plan usa rutas relativas a
la raíz de cada copia; la guía explica la configuración para las copias de Cristopher y Jordan.
No se copian datos a sus carpetas ni se presupone que ya los tienen.

- [x] CSV/XLSX/DOCX con tamaño, suma, canal real y manifiesto comprobados; faltantes registrados.
- [x] Dos ejecuciones locales, network_bytes=0, sin cambios a originales/manifiestos existentes.
- [x] Registro documental de PDF conservado con sus formatos reales, sin nueva descarga.
- [x] Catálogo válido e informe suficiente para que #10 encuentre los insumos y sus límites.
- [x] make check, make build y make audit aprobados antes de entregar; pruebas enfocadas solo si
  se modifica lógica. No crear un descargador paralelo ni pruebas que solo repitan constantes.

## Presupuesto, bloqueos y cierre

Recomendación: **0 bytes de descarga**. No hay una autorización nueva de transferencia dentro de #8.
La validación por referencia no requiere duplicar el CSV ni reservar el máximo de 1000 GiB.
No se normalizan fechas/unidades, convierten coordenadas, imputan mediciones ni publican datos.
#43 conserva aclaraciones científicas/de derechos. Una adquisición estructural puede cerrarse con
estos límites documentados; eso no habilita automáticamente normalización o selección en #11.
Si algún original falta en la ejecución, consultar primero si se recupera de evidencia local o se
aprueba una descarga concreta con Lightpanda. No reabrir la consulta institucional sin instrucción.

Evidencia: metadata/senamhi-acquisition-check.json y reports/acquisition/senamhi.md. No hubo nuevas transferencias.
