# #21 · Conector base de SENAMHI para TimeNet

Responsable: Keneth. El cierre de #1 aporta un entorno TimeNet 0.12.0 ya probado.
Los dos paquetes instalados declaran el commit
`9bd1613019ee61fbc52e02106a1a45990ead7a54` en direct_url.json.
La [revisión de interfaces](../docs/timenet-integration.md) es la referencia para la implementación.
El alcance de datos sigue la [política aprobada](../docs/decisions/005-senamhi-operating-policy.md).
El seguimiento está en [#21](https://github.com/keneth-arias/airaware/issues/21).

## Entrega 1 · Ida y vuelta con una muestra sintética

#13 quedó integrada mediante #71. Usar una entrada local sintética que represente
el contrato de observación. Verificar nombres, tipos de señal, unidades y metadatos contra el
SDK fijado en tools/timenet-smoke. Probar un identificador provisional de registro y una señal
PM2.5 con valor medido, cero y nulo. Usar RegularAxis para una grilla horaria explícita en UTC.
Si faltan horas en el insumo, representar el hueco mediante una casilla nula en la grilla,
sin desplazar las observaciones. Mantener una serie por identidad provisional y contexto.
Escribir con TimeFDataset.write, reabrir con TimeFReader, ejecutar verify y comprobar valores,
nulos y eje con Arrow. Ejecutar mediante el entorno aislado, con los paquetes ya instalados y
sin red. Archivos previstos: src/airaware/timenet/, tools/timenet-smoke/ y pruebas de integración.

## Entrega 2 · Adaptar la salida real de #13 y verificar una muestra acotada

Con el contrato Parquet de #13 disponible, cotejar columnas, tipos, particiones, manifiesto y
rechazos. Verificar integridad antes de convertir. Reutilizar adquisición de AirAware para
obtener referencias locales. Mantener convert determinista, sin descargas, leyendo solo la
muestra seleccionada y preservando procedencia, hash, identificación provisional y versión
de la política. Probar archivo ausente, hash incorrecto y rechazo trazable de conflictos de
una misma señal/hora. Confirmar en la muestra real que cero, nulo y valor se conservan, que la
unidad tipada representa µg/m³ y que el carácter inferido queda en metadatos. La licencia
ODC-BY-1.0 y el aviso DATA_ATTRIBUTION.md acompañan la salida local.

La marca de tiempo es observed_at UTC. La posición del intervalo y la calidad conservan el
estado desconocido. Repetir la escritura en dos carpetas nuevas y comparar contenido lógico,
orden e identificadores. Registrar los hashes de cada salida y comprobarlos con el lector.
Usar un nombre y versión locales conforme al SDK. Verificar nombres del registro compartido
y versiones de padres al preparar #22. Ejecutar make check, make build y make audit y registrar
el comando y el alcance de la prueba TimeF. Archivos previstos: adaptador Parquet, pruebas
de integración y guía de ejecución con el recibo de la muestra.

## Límite entre #21 y #22

#21 entrega un conjunto base local que el SDK puede escribir, verificar y leer. #22 usa ese
conjunto y las particiones de #19 para materializar tareas ForecastingTask, comprobar fugas y
fijar versiones de padres donde corresponda. El código local sigue ADR-003 (AGPL-3.0-only).
El aporte externo se gestiona en #24 con las condiciones de licencia allí registradas.
