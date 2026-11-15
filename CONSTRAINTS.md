# Acuerdo de calidad inicial

Definido el 15/11/2026 a partir del plan y el alcance local. Responsable: @keneth-arias.
Los objetivos adicionales de cobertura y rendimiento se definirán después de medir el sistema real.

| Control | Condición para aprobar | Comando |
| --- | --- | --- |
| Dependencias fijadas | El archivo de versiones está actualizado | `uv lock --check` |
| Formato y análisis estático | Cero errores de las reglas configuradas | `uv run --locked ruff format --check src tests` y `uv run --locked ruff check src tests` |
| Tipos | Cero errores con la compatibilidad mínima de Python 3.11 | `uv run --locked ty check src tests` |
| Catálogo | Esquema válido, ID únicos y evidencia de avance | `uv run --locked airaware catalog validate` |
| Comportamiento | Todas las pruebas sin servicios externos aprueban | `uv run --locked pytest` |
| Paquetes | Se generan distribución fuente y wheel | `make build` |
| Seguridad de dependencias | Sin vulnerabilidades conocidas en el entorno instalado | `make audit` (requiere internet) |

`make check` ejecuta las cinco primeras filas en local y en CI. La auditoría incluye herramientas
de desarrollo; omite el paquete local editable porque no está publicado.
No hay todavía un porcentaje mínimo de cobertura. La protección de main exige los dos controles
por versión de Python y la auditoría; Keneth conserva la excepción de administrador.
Consulta el estado en la [lista de servicios](docs/services.md).

La revisión también exige: no subir secretos, añadir supresiones para ocultar errores, dejar código
sin implementar, omitir/eliminar pruebas sin motivo documentado ni debilitar controles.
Estas reglas de revisión no equivalen a un escáner automático completo. No cambies este acuerdo
para hacer pasar un cambio que falla. La traducción no reduce ninguna exigencia técnica.
