# Cola de trabajo de Keneth: datos y plataforma

Estado revisado el 16/11/2026. El usuario autorizó planificar e implementar sus tareas asignadas,
investigar información faltante y consultar decisiones pendientes. Conserva el idioma español del Perú
en el repositorio; respuestas y resúmenes para Keneth en inglés.

## Orden de entrega y dependencias

| Tarea | Primera entrega y verificación | Dependencias y estado |
| --- | --- | --- |
| #7 | Caché/reanudación y selección por lotes, límites, estimación y modo sin red; HTTP simulado | #6/#7 cerradas; PR #46–#49 integrados |
| #8 | Reutilizar CSV/documentación SENAMHI con plan repetible e informe local | #8 ejecutada e integrada en PR #52; originales intactos, cero red |
| #9 | Documentación OEFA y CSV acotado; resolver dialecto/canal antes de transferir | #9 cerrada; PR #56 integrado, CSV completo Lightpanda verificado |
| #10 | Perfilamiento de cobertura/calidad con datos reales y límites por fuente | #10 cerrada; PR #57/#58 integrados, perfiles reales verificados |
| #11 | Plan de comparación, conteo real de ventanas y puntuación con trazas de filtros | Plan aprobado e implementación diagnóstica ejecutada; selección científica pendiente de aclaraciones institucionales |

| #12 | Contrato de observaciones/estaciones, nulabilidad, procedencia y disponibilidad | #12 completada; contrato y política operativa SENAMHI listos para #13 |
| #14 | Reglas de identidad, reubicación y duplicados; regresiones de procedencia | Espera normalización #13, a cargo de Cristopher |
| #19 | Particiones cronológicas y purga de ventanas, sin fuga ni ajuste fuera de entrenamiento | Espera #18; fechas reales requieren cobertura verificada |
| #20 | Investigación oficial peruana de umbrales, promedios y completitud | Metodología/módulo independientes implementados; falta integración #18. Mantener abierta por decisión de Keneth |
| #21 | Conector TimeNet fijado, descarga separada de conversión, muestra tipada | Espera #13 y aclaraciones pertinentes de #43; #1 ya cerrada |
| #22 | Exportación TimeF con padres/particiones fijos y lectura SDK | Espera #19/#21 |
| #23 | Flujo pequeño sin red en CI y medición de memoria/tiempo | Espera #22 |
| #27 | Verificar interfaz/licencias OpenTSLM y adaptador; prueba acotada aprobada | Espera #23/#25; no descargar pesos ni entrenar sin presupuesto y datos aprobados |
| #28 | Experimento reproducible frente a referencias con mismos objetivos | Espera #27; cómputo/coste y configuración requieren decisión informada |
| #32 | Evaluación espacial con estaciones excluidas y preentrenamiento sin objetivos reservados | Espera #19/#30; ampliación nacional posterior |
| #43 | Registrar respuesta SENAMHI y actualizar solo afirmaciones sustentadas | Espera externa; consulta enviada, sin respuesta localizada en la búsqueda inicial de este trabajo |

#8/#9/#10 fueron transferidas a Keneth por su solicitud. #13/#18/#25/#30 siguen con Cristopher;
#24/#29 conservan la reserva de Jordan. PR #45 de investigación OEFA aprobado e integrado; #5 cerrada.
Coordinar contratos comunes sin cambiar ramas de otras personas.
No cerrar una tarea posterior por preparar un contrato sintético sin cumplir su criterio con datos reales.
Una tarea de implementación activa por persona; al llegar a una dependencia, avanzar en investigación
independiente y mantener evidencia del bloqueo.

## Decisiones y búsqueda

Keneth fijó un máximo de **1000 GiB por archivo** para #7. Cada lote requiere presupuesto total explícito;
no es una orden de transferir ese volumen. Verificar espacio local y límites antes de adquisición.
Para incógnitas: documentos oficiales primero, búsqueda adicional, comparación de fuentes/versiones,
registro de evidencia y consulta a Keneth si queda una elección. No reiterar correos SENAMHI sin instrucción.
Las decisiones de unidades, reloj, publicación, particiones reales y cómputo no se suponen resueltas
por cerrar tareas de plataforma. Las licencias AGPL del código y de los datos siguen separadas.

Decisión vigente 17/11/2026: #13 listo para @qriqs; sin cuota de estaciones/meses, UTC confirmado
por Keneth y ug/m3 inferidos aceptados. Ver docs/sources/senamhi-normalization-handoff.md.
