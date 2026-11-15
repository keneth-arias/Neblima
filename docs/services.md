# Servicios, herramientas y accesos

Decisión inicial: almacenamiento local y GitHub Actions, sin servicios de pago.
Estado revisado el 15/11/2026; vuelve a verificar accesos antes de depender de ellos.

| Herramienta o servicio | Estado | Siguiente acción |
| --- | --- | --- |
| Git y GitHub CLI | Instalados para los tres usuarios; solo Keneth está autenticado | Cada integrante configura su propia cuenta; no compartir tokens |
| uv | Versión 0.11.20 disponible para todos | En otra máquina, seguir la [instalación oficial](https://docs.astral.sh/uv/getting-started/installation/) |
| Python | 3.13.13 instalado por separado para cada usuario; versión fijada en .python-version | `uv python install` y `make setup` |
| Repositorio | Público: keneth-arias/airaware | Subir código, documentación y solo muestras pequeñas permitidas |
| Tablero | 35 tareas; 18 reservadas para el equipo y 17 a cargo de Keneth | Mantener prioridades, dependencias y bloqueos |
| GitHub Actions | Pasaron controles de Python 3.11, Python 3.13.13 y auditoría | Conservar los tres controles aprobados |
| Datos locales | Carpetas independientes por integrante | Revisar espacio disponible antes de descargar; usar AIRAWARE_DATA_DIR si corresponde |
| Respaldo | No configurado | Definirlo y probarlo antes de una recolección irremplazable |
| SENAMHI/OEFA | Enlaces candidatos; acceso y derechos pendientes | Revisar #4/#5 y registrar recursos, términos y bloqueos |
| OpenAQ | Opcional para #31; sin clave configurada | Seguir la [guía oficial](https://docs.openaq.org/using-the-api/api-key) cuando se necesite |
| TimeNet | Código inspeccionado y revisión fijada; SDK no instalado | Preparar un entorno aislado para #21 |
| OpenTSLM | Revisión remota anotada; interfaz de entrenamiento pendiente | Esperar #27 y la validación de datos |
| Hackathon | Lista de entrega documentada | Cada integrante se registra; aquí no se confirma su inscripción |

La protección de main exige aprobar `quality (3.11)`, `quality (3.13.13)` y `audit` con la rama
actualizada. Impide forzar actualizaciones y eliminar la rama. El dueño conserva una excepción de
administrador. No hay aprobación de revisión obligatoria; CODEOWNERS solo solicita revisiones.
Los nombres técnicos de estos controles se mantienen para no cambiar la protección.

qriqs y J0r-PS tienen permiso de administrador del tablero. Su invitación de escritura al repositorio
personal sigue pendiente. Se reservan tareas mediante etiquetas `owner:qriqs` y `owner:J0r-PS` hasta
que acepten. Consulta la [guía del equipo](team-onboarding.md). No se copiaron credenciales.

Referencias oficiales para la configuración:

- [uv con GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/).
- [Generación de paquetes con uv](https://docs.astral.sh/uv/concepts/build-backend/).
- [Validación de modelos de Pydantic](https://docs.pydantic.dev/latest/concepts/models/).
- [Pruebas de comandos con Typer](https://typer.tiangolo.com/tutorial/testing/).
