# Tarea #3: inventario de fuentes ambientales

Responsable: Keneth. Depende de #2 (cerrada). Entrega en [PR #41](https://github.com/keneth-arias/airaware/pull/41).

## Plan ejecutado

- [x] Conservar y agrupar los 37 recursos candidatos del plan sin tratarlos como 37 conjuntos independientes.
- [x] Consultar cada enlace con Lightpanda; registrar URL original/final, fecha UTC, HTTP disponible y bloqueos.
- [x] Completar categoría, cobertura documental, licencia declarada, limitaciones y siguientes acciones;
  conservar nulos cuando no exista evidencia. Resolver enlaces reales SENAMHI/OEFA sin descargar OEFA.
- [x] Registrar la descarga SENAMHI ya realizada, su suma y tamaño medido, separando estructura y ciencia.
- [x] Vincular catálogo y evidencia mediante pruebas sin servicios externos.
- [x] Actualizar el protocolo de acceso para todo el equipo y el plan inicial.

La [revisión completa](../docs/sources/inventory-review.md) detalla resultados y límites.
El [protocolo Lightpanda](../docs/web-access.md) aplica a páginas y descargas web en las copias de todos.
La consulta anterior que devolvió 403 usó otra herramienta; Lightpanda sí permitió descargar el CSV.

## Criterios cubiertos

Los 37 candidatos tienen ficha y fecha; tres bloqueos conservan motivo y siguiente acción, cuatro
accesos parciales permanecen discovered. Los valores documentales no se presentan como mediciones.
Se conserva la referencia aproximada de tamaño del plan separada del tamaño real del CSV SENAMHI.
La evidencia de aceptación queda en configs/sources.yaml, metadata/source-access.json y los informes.
El cierre de GitHub se vincula a la integración de #41.

## Trabajo posterior

#4 verifica SENAMHI: diccionario XLSX, metadatos DOCX, unidades, fechas, controles y derechos.
#5 sigue con Cristopher para OEFA y coordenadas. #6/#7 implementan adquisición atómica/reanudable;
#8 reutilizará el CSV local después de verificar su suma, en lugar de descargar otra copia innecesaria.
#10/#11 medirán calidad y elegirán el conjunto; #14/#31 resolverán duplicados y agregadores.
No se publican datos masivos ni se infieren permisos a partir del acceso público.

Los originales están en data/raw/senamhi y el hello-world sintético verificado en data/timef.
Consultar a Keneth ante cuentas/pagos, cambios de esquema o descargas costosas; registrar bloqueos
no requiere autorización adicional. AGPL del código no concede derechos sobre las fuentes.
