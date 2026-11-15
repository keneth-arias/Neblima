# ADR-001: Almacenamiento local y GitHub Actions al inicio

## Estado y fecha

Aceptada el 15/11/2026. Keneth eligió almacenamiento local y GitHub Actions para la preparación inicial.

## Contexto

Las primeras tareas requieren investigar fuentes, registrar licencias y preparar herramientas
reproducibles. Aún no se han medido cobertura, volumen real de descargas ni necesidades de cómputo.

## Decisión

Usar uv y Python 3.13.13 en local, con compatibilidad mínima de Python 3.11 como TimeNet.
Fijar Pydantic, PyYAML, Typer y herramientas de pruebas, formato, tipos y auditoría.
Mantener datos en carpetas locales por etapa y el código en un repositorio público con CI.
Keneth dirige los contratos de datos y las decisiones de plataforma. No instalar dependencias
analíticas, geoespaciales o de entrenamiento hasta que una tarea las necesite.

## Alternativas

El almacenamiento remoto y la orquestación agregarían cuentas, costos y administración sin contar
con una muestra verificada. Trabajar solo con cuadernos sin versiones dificultaría la trazabilidad.
Se podrán reconsiderar estas opciones con mediciones concretas.

## Consecuencias

La preparación actual no necesita cuentas de pago ni claves de proveedores.
Cada fuente debe verificarse: un enlace público no concede permiso de redistribución.
El almacenamiento local no es una copia de respaldo. Antes de una recolección irremplazable,
el responsable debe definir y probar un procedimiento de respaldo e intercambio de archivos.
