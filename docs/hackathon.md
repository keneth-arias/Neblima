# Requisitos y evidencia para el hackathon de TimeNet

Fuente principal: [página oficial del reto](https://challenge.timenet.ai/), consultada el 15/11/2026.
El equipo usa esta matriz para preparar evidencias, sin afirmar que ya completó la entrega.
Las responsabilidades internas son acuerdos de AirAware, no reglas del organizador.

## Plazo y hora del Perú

Primera ronda: 22/11/2026 a las 11:59 p. m. PST (UTC−8).
Conversión a America/Lima: **23/11/2026 a las 2:59 a. m.** (07:59 UTC).
La conversión se comprobó con zoneinfo de Python. Volver a consultar la fuente antes de enviar.

## Matriz de requisitos

| Requisito oficial | Evidencia que debemos reunir | Tarea y responsable interno | Estado comprobado |
| --- | --- | --- | --- |
| Registro individual y equipo de 2–4 personas | Confirmación de cada integrante, sin publicar datos personales | #29; cada integrante se registra, Keneth coordina | Equipo planificado de tres; inscripciones no verificadas |
| Preparar datos en TimeNet y entregar el enlace del PR del conjunto | Construcción validada y URL del PR externo | #21–#24; Keneth prepara integración, Jordan apoya documentación | Sin conjunto TimeF de AirAware ni PR externo |
| Entrenar o ajustar un modelo temporal y evaluar con datos separados | Revisión/configuración del modelo, particiones fijas y resultados | #19, #25–#28; Keneth y Cristopher según su tarea | Pendiente; no hay métricas de entrenamiento |
| Presentación, demostración, página u otro formato que muestre el proyecto | Enlace al material y explicación de utilidad y límites | #29; Jordan prepara el borrador, Keneth valida afirmaciones | Pendiente de preparar evidencia final |
| Publicaciones públicas en X y LinkedIn; ambas requeridas | Enlaces y capturas de métricas disponibles | #29; Jordan redacta, Keneth autoriza publicación | No verificadas ni autorizadas por esta investigación |
| Compartir en Discord del hackathon | Enlace o comprobante del mensaje publicado | #29; coordinación de Keneth | No verificado; no se envió un mensaje aquí |
| Formulario oficial por equipo y por ronda antes del cierre | Confirmación y enlaces exigidos | #29; coordinación de Keneth | Pendiente de entrega; no se envió el formulario |
| Repositorio del proyecto, si corresponde | URL de AirAware; figura como enlace opcional en la página | #29 | Repositorio público disponible; no equivale a una entrega |

Los controles de calidad, las metas de cobertura y los porcentajes de integridad son decisiones del
proyecto, no requisitos oficiales añadidos al hackathon. La página indica que se evalúan impacto,
ejecución técnica, datos/TimeNet, resultados y presentación/interacción social; conservar evidencia
sin prometer premios ni créditos.

## Revisión antes de entregar

- [ ] Cada integrante confirma su registro y el equipo mantiene el tamaño permitido.
- [ ] Las fuentes tienen derechos compatibles y el conjunto genera TimeF válido.
- [ ] El PR externo del conjunto está preparado y su apertura fue autorizada.
- [ ] Hay resultados reales con objetivos y particiones comparables; se explican límites.
- [ ] Presentación, enlaces y capturas corresponden al trabajo efectivamente realizado.
- [ ] Publicaciones, Discord y formulario cuentan con la autorización prevista en el plan.
- [ ] Se revisa nuevamente la página oficial y se confirma el envío antes del plazo.

## Referencias técnicas

[Guía de inicio](https://docs.timenet.ai/get-started.html) y
[repositorio TimeNet](https://github.com/OpenTSLM/TimeNet).
La versión inspeccionada requiere Python >=3.11. Cliente: timenet; herramienta de construcción:
timenet-connectors. La revisión técnica está en [las notas de integración](timenet-integration.md).
