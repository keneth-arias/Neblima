# Cómo contribuir

En la máquina compartida, revisa primero la [guía del equipo](docs/team-onboarding.md) y la
[distribución de tareas](docs/team-work-allocation.md). Usa tu propia copia y tus credenciales.
Después consulta la [guía del responsable](docs/lead-handbook.md), el [plan](tasks/plan.md) y tu tarea.

Trabajamos en español del Perú. Escribe documentación, tareas y PR en español claro; explica las
siglas. Conserva comandos, rutas y nombres de API. Usa inglés solo cuando una contribución externa
lo requiera. La [decisión de idioma](docs/decisions/002-espanol-peru.md) detalla el criterio.

El desarrollo se verifica en Linux; macOS está contemplado en las herramientas. En Windows usa WSL
para ejecutar Make. Instala Git, Make, uv >=0.11.20 y, de ser necesario, GitHub CLI. uv administra Python.

```bash
uv python install
make setup
make init
make doctor
make check
make build
make audit
```

La instalación y la generación del paquete pueden descargar herramientas. `make check` no usa datos
ambientales remotos y funciona con `UV_OFFLINE=true` después de la instalación.
`make audit` sí consulta un servicio de alertas de seguridad. CI repite los controles en Python
3.11 y 3.13.13 y ejecuta la auditoría por separado.

El [glosario](docs/glossary.md) explica PR, CI, ventanas y fuga de información con ejemplos.

Crea una rama por entrega, vincula la tarea en el PR y solicita revisión de Keneth.
CODEOWNERS solicita revisión, pero no exige una aprobación por sí solo; no puedes aprobar tu propio PR.
Mantén las fuentes en `discovered` hasta reunir evidencia. Revisa `AGENTS.md` para las reglas de datos.

La herramienta actual implementa `catalog validate`, `workspace init` y `doctor`. Los comandos de
descarga, análisis, normalización y TimeF del documento inicial siguen siendo propuestas.
No publiques datos ni abras un PR externo sin la autorización prevista en el plan.
El código propio usa AGPL-3.0-only; las contribuciones a Neblima se reciben bajo esa misma licencia
y cada autor conserva sus derechos. Un repositorio público no define la licencia de sus fuentes.
Antes de contribuir código a TimeNet bajo MIT, revisa [ADR-003](docs/decisions/003-licencia-agpl-v3.md):
no se concede una excepción ni licencia dual al código AGPL de Neblima.
