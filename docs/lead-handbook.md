# Guía del responsable de datos y plataforma

Keneth Arias (`@keneth-arias`) lidera datos y plataforma. CODEOWNERS dirige las solicitudes de revisión
hacia él. Es responsable de seleccionar fuentes, aprobar contratos de datos, calidad científica,
procedencia, particiones de evaluación, herramientas, CI y preparación de publicaciones.
Cristopher (`@qriqs`) aporta a tiempo completo en fuentes e implementación con pruebas.
Jordan (`@J0r-PS`) aporta a tiempo parcial en documentación guiada y presentación.
Revisa [responsables y tareas](team-work-allocation.md) y la [guía de inicio](team-onboarding.md).

## Primera sesión

Desde la raíz del repositorio:

```bash
make setup
make init
make doctor
make check
```

`doctor` revisa Python, Git, uv, zona horaria, catálogo y carpetas escribibles sin acceder a la red
ni crear archivos. Solo informa si hay una clave opcional; nunca muestra su valor.
Un resultado correcto indica que la base local está lista. No verifica acceso a proveedores,
autenticación de GitHub, respaldo, disponibilidad real de datos ni derechos de uso.
Las claves JSON son técnicas: `ready` indica disponibilidad y `checks` contiene los controles.

Keneth verifica `senamhi-lima` en #4; Cristopher investiga `oefa-national` en #5.
Resuelvan recursos reales y diccionarios, revisen licencias y registren fechas y evidencia.
La cobertura o las unidades desconocidas permanecen nulas. Mantengan las fuentes bloqueadas con
su explicación. Los estados avanzados requieren evidencia con fecha y zona horaria;
`integrated` exige además permiso documentado de redistribución y categoría de medición conocida.

El núcleo de adquisición #6 está implementado; #7 agrega reanudación y capacidades adicionales antes
de ampliar adquisiciones #8/#9. Consulta docs/acquisition.md y conserva los bloqueos científicos de #43.
Se inspeccionan los archivos, se miden calidad y cobertura #10/#11 y recién se define el conjunto
inicial de evaluación. Cuatro estaciones, 24 meses y ventanas de 72/24 horas son metas provisionales.

## Servicios y credenciales

Consulta [servicios y accesos](services.md). No se necesita una clave para los comandos actuales.
`.env` está excluido de Git y no se carga automáticamente. Puedes definir otra carpeta:

```bash
export AIRAWARE_DATA_DIR="$HOME/airaware-data"
make init
make doctor
```

No incluyas claves en URL del catálogo, tareas, cuadernos ni Git. OpenAQ se integra más adelante;
cada persona usa su propia cuenta. Los datos locales no se respaldan automáticamente.
Define y prueba el respaldo antes de depender de una recolección irremplazable.
Conserva los archivos originales sin cambios y haz reproducibles los derivados.

## Decisiones y revisiones

- Aprueba fuentes tras revisar licencia y metodología; registra decisiones importantes en ADR.
- Cada PR debe explicar alcance, comandos ejecutados, resultados y dudas pendientes.
- Revisa esquemas, precedencia de fuentes, filtros de calidad y fechas de partición antes de usarlos.
- Fija los límites del conjunto de prueba antes de experimentar; no ajustes el procesamiento con él.
- Antes de publicar, revisa licencias, trazabilidad, calidad, pruebas de fuga, lectura con SDK y modelos
  de referencia. Publica solo con la autorización prevista en el plan.
- Usa GitHub como estado vigente y el plan como índice ordenado de tareas.

## Alcance actual

La preparación incluye entorno fijado, catálogo, tres comandos sin red, pruebas y CI.
La entrega inicial #2 no implementó adquisición ni procesamiento científico. #6 incorpora ahora
adquisición con manifiestos; análisis, normalización y entrega TimeF real siguen en las tareas respectivas.
Las notas de integración distinguen inspección del código externo de validación en ejecución.
