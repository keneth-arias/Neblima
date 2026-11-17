# ADR-004: DuckDB para el perfilamiento local

## Estado y fecha

Aceptada el 16/11/2026 dentro de la implementación autorizada de #10.

## Contexto

Los CSV verificados tienen 577 794 filas SENAMHI y 2 883 877 filas OEFA; este último ocupa
1,3 GB. #10 necesita agrupaciones, ventanas, cuantiles y Parquet con procedencia, sin servicios
pagados ni cargar todos los objetos de fila en memoria Python.

## Decisión

Añadir DuckDB (MIT), fijado en uv.lock a 1.5.6, para lectura VARCHAR estricta, agregación local
y exportación Parquet. El proceso usa una base temporal por ejecución, dos hilos y derrame a disco
acotado; no expone servidor. Las extensiones automáticas están deshabilitadas. El límite configurado
de memoria de DuckDB no es un límite absoluto del consumo del proceso.

## Alternativas

La biblioteca csv sigue verificando la estructura en adquisición, pero no escribe Parquet ni resuelve
agregaciones/ventanas con derrame sin implementar infraestructura adicional. pandas/PyArrow añadirían
más dependencias y exigirían otra estrategia para agrupar el archivo completo. No se necesita un
servicio PostgreSQL ni almacenamiento remoto para esta tarea.

## Consecuencias

La instalación tiene una dependencia binaria adicional; CI comprueba Python 3.11 y 3.13.
Los datos masivos y las bases temporales permanecen fuera de Git. El algoritmo y la versión de DuckDB
se registran por ejecución. Las estadísticas no corrigen relojes/unidades desconocidos ni autorizan
redistribuir datos. La metodología y los denominadores están en [profiling.md](../profiling.md).
