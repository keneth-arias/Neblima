# Inventario de enlaces de entrega del hackathon

Registro central de lo que se puede entregar y de lo que falta para la primera ronda del reto
[TimeNet](https://challenge.timenet.ai/). Este archivo no envía ni publica nada: solo indica dónde
está cada evidencia y su estado. Cada envío requiere la autorización prevista en el plan y debe
dejar aquí su fecha y comprobante. Requisitos oficiales y plazo: [docs/hackathon.md](../hackathon.md)
(página consultada por última vez el 17/11/2026; cierre de la primera ronda: 23/11/2026 a las
2:59 a. m. en America/Lima, volver a consultar la fuente antes de enviar).

## Enlaces y materiales disponibles

| Enlace o material | Referencia | Estado | Uso previsto en la entrega |
| --- | --- | --- | --- |
| Repositorio del proyecto | <https://github.com/keneth-arias/airaware> | Listo (público) | Enlace opcional que admite la página oficial; no equivale por sí solo a una entrega |
| PR interno de evaluación reservada | <https://github.com/keneth-arias/airaware/pull/97> | Fusionado | Soporte técnico de los resultados que muestra la presentación |
| Ficha del conjunto `airaware/lima-pm25-forecast@0.1.0` | [docs/dataset-cards/lima-pm25-forecast.md](../dataset-cards/lima-pm25-forecast.md) | Listo | Fuente de cobertura, particiones, licencia y límites del conjunto |
| Informe de la prueba cronológica reservada | [reports/models/prueba-reservada-lima.md](../../reports/models/prueba-reservada-lima.md) | Listo | Métricas de la presentación (MAE 4,994 frente a 6,446 µg/m³; mejoras 22,52 % y 6,34 %) |
| Evaluación externa de PM2.5 y PM10 | [Informe por fuente, contaminante y horizonte](../../reports/models/prueba-externa-pm25-pm10.md) | Listo | Evidencia complementaria sobre el aporte del historial de PM10 en Lima |
| Figura para la demo | [reports/models/lima-pm25-prueba.png](../../reports/models/lima-pm25-prueba.png) | Listo | Base visual de la diapositiva de resultados y de la demo |
| Referencias (baselines) | [reports/baselines/lima-pm25.md](../../reports/baselines/lima-pm25.md) | Listo | Comparación contra persistencia y detalles de particiones |
| Selección inicial y política de la fuente | [reports/benchmark-selection.md](../../reports/benchmark-selection.md) · [docs/decisions/005-senamhi-operating-policy.md](../decisions/005-senamhi-operating-policy.md) | Listo | Justificar la elección de SENAMHI/Lima/PM2.5 y el alcance retrospectivo |
| Atribución de datos | [DATA_ATTRIBUTION.md](../../DATA_ATTRIBUTION.md) | Listo | Aviso ODC-By-1.0 y crédito a SENAMHI, obligatorio en material difundido |
| Verificación con el lector oficial de TimeNet | [tools/timenet-smoke/README.md](../../tools/timenet-smoke/README.md) | Listo | Demostrar lectura y verificación de TimeF sin red |
| Mapa web de las siete estaciones | [web/estaciones.html](../../web/estaciones.html) | Listo (material interno) | Apoyo visual de contexto; en esta entrega solo se enlaza, no se modifica |
| PR externo TimeNet #796 (borrador) | <https://github.com/OpenTSLM/TimeNet/pull/796> | Abierto como borrador | Enlace del aporte de datos a TimeNet para el formulario de la ronda |

## Pendientes de envío o autorización

| Elemento | Estado | Nota |
| --- | --- | --- |
| Formulario oficial por equipo y ronda | **Pendiente de envío autorizado** | No se ha enviado; al enviarlo, registrar aquí fecha y comprobante |
| Publicación en X | Sin enlace; texto por preparar | Requerida por la página oficial; espera autorización de Keneth; no se ha publicado nada |
| Publicación en LinkedIn | Sin enlace; texto por preparar | Requerida por la página oficial; espera autorización de Keneth; no se ha publicado nada |
| Discord del hackathon | Sin enlace; mensaje no enviado | Espera autorización; guardar aquí el enlace o comprobante del mensaje |
| Demo grabada | Sin enlace; insumos listos | Grabación pendiente; insumos en [README.md](README.md) (sección 7) |
| Inscripción individual | Por confirmar | Cada integrante confirma su registro; equipo Cuybernautas de tres personas |
| Página oficial del reto (verificación vigente) | <https://challenge.timenet.ai/> | Volver a consultar reglas, fecha límite y PR de datos antes de cada envío; última revisión registrada: 17/11/2026 |

## Notas

- Ningún elemento de la tabla anterior se envía desde este repositorio; el registro solo indica
  disponibilidad. Publicar, compartir o enviar formularios requiere la autorización prevista en el
  plan y la validación de afirmaciones por Keneth.
- Al completar un envío, actualizar su fila con fecha, enlace y comprobante, sin borrar el estado
  anterior.
- La indisponibilidad del servidor antiguo de datos no afecta este inventario: las evidencias
  listadas están versionadas en el repositorio.
