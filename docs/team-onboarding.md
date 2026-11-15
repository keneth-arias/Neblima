# Guía de inicio del equipo

Cada integrante usa las mismas herramientas y configuración versionadas, pero una copia local
independiente. En la máquina compartida entra con tu usuario de Linux; no trabajes en la carpeta
ni cambies la rama de otra persona.

| Integrante | Usuario de Linux | GitHub | Carpeta del proyecto |
| --- | --- | --- | --- |
| Keneth | kymai | keneth-arias | /home/shared/github/keneth-arias/airaware |
| Cristopher | cristopher | qriqs | /home/cristopher/github/airaware |
| Jordan | jordan | J0r-PS | /home/jordan/github/airaware |

Cristopher y Jordan tienen Python 3.13.13, su propia `.venv`, caché de uv, archivo `.env` privado y
carpeta de datos. Git, gh, Make y uv están disponibles para todos los usuarios. Cada copia tiene la
identidad de Git de su responsable, con correo noreply de GitHub. `git pull` solo acepta avance
directo, sin crear una fusión automática, y el primer `push` configura la rama remota.
No se comparten credenciales entre usuarios.

## Tu primera sesión

Entra con tu usuario y ejecuta:

```bash
cd ~/github/airaware
make doctor
make check
```

En otra computadora, clona el repositorio público y sigue CONTRIBUTING.md.
La base está en el PR #36, rama `chore/platform-foundation`; las copias preparadas usan esa rama.
Después de integrar el PR, cambia a main antes de empezar otra tarea:

```bash
git fetch origin
git switch main
git pull --ff-only
```

Antes de esa integración, crea tus ramas desde `origin/chore/platform-foundation` y solicita revisión
contra esa rama. Después, usa `origin/main`. Keneth coordina los cambios de rama base de los PR ya
abiertos para no revisar dos veces los mismos cambios.

Cristopher puede iniciar con `docs/issue-5-oefa-review`; Jordan, con
`docs/issue-29-showcase-outline`. Crea tu rama cuando empieces la tarea:

```bash
git switch -c docs/issue-5-oefa-review
```

Jordan debe usar el nombre de su rama de la tarea #29. El primer PR debe incluir solo la primera
entrega indicada en la tarea, no todo el trabajo de golpe. Marca un criterio de aceptación solo
cuando tengas evidencia. Mantén **una tarea activa por persona**.

## Acceso personal a GitHub

Las invitaciones de qriqs y J0r-PS al repositorio siguen pendientes según la última verificación.
Deben aceptarlas con sus propias cuentas antes de subir cambios o recibir asignaciones nativas.
Mientras tanto, las etiquetas `owner:qriqs` y `owner:J0r-PS` reservan sus tareas, como indicó Keneth.
Ambos tienen permiso de administrador del tablero. En el repositorio personal, su permiso es de
colaborador con escritura. Son permisos distintos.

`gh` está instalado, pero aún no se ha autenticado en los usuarios locales de Cristopher y Jordan.
Ya pueden clonar el repositorio público, editar, probar y generar paquetes. Cada uno debe configurar
su propio acceso antes de subir cambios o crear PR. No reutilicen la sesión ni el token de Keneth.

## Configuración común y archivos privados

Los cambios de pyproject.toml, uv.lock, configs, Makefile, AGENTS.md y CI se comparten mediante Git y PR.
Después de actualizar tu copia, ejecuta `make setup`. El programa no carga `.env` automáticamente;
exporta las variables que necesites. Los datos se guardan por defecto en tu propia copia.
No copies credenciales, entornos, cachés ni datos originales de otro integrante para preparar tu equipo.
Comparte evidencia y muestras pequeñas permitidas mediante PR para que el trabajo sea reproducible.

El 15/11/2026 ambos usuarios aprobaron doctor, 29 pruebas sin servicios externos, formato, análisis
estático, tipos, catálogo, generación de paquetes y auditoría de dependencias. La traducción agrega
pruebas de idioma; los resultados actuales se registran en el PR. El acceso a proveedores y los
derechos de sus datos siguen sin verificar. Consulta la [distribución de tareas](team-work-allocation.md).
