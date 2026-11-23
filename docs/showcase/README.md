# Esquema de presentación para el hackathon de TimeNet

Este documento organiza la presentación del proyecto Neblima para la primera ronda del reto
[TimeNet](https://challenge.timenet.ai/). El marco de requisitos oficiales y el plazo están en
[docs/hackathon.md](../hackathon.md); el inventario de enlaces de entrega está en
[enlaces.md](enlaces.md). Nada de lo descrito aquí está publicado todavía: las publicaciones en
redes, el formulario oficial y la grabación de la demo esperan autorización (ver
[Pendientes](#pendientes)).

Responsabilidad interna acordada: Cristopher y Jordan preparan el material y Keneth valida las
afirmaciones (matriz de [docs/hackathon.md](../hackathon.md)). Todas las cifras de este esquema se
copian de reportes versionados en este repositorio y se citan por ruta; no se simularon métricas.
La indisponibilidad del servidor antiguo de datos no afecta esta entrega, porque solo se citan
reportes ya registrados en Git.

## Mensajes clave

- Con 24 horas de historia de PM2.5, el modelo temporal evaluado (Qwen3.5-0.8B con adaptación de bajo rango (LoRA)) obtuvo un
  error absoluto medio (MAE) de **4,994 µg/m³** frente a **6,446 µg/m³** de la referencia de persistencia en la prueba
  cronológica reservada: una reducción de **1,452 µg/m³ (22,52 %)**. Fuente:
  [reports/models/prueba-reservada-lima.md](../../reports/models/prueba-reservada-lima.md).
- En concentraciones altas (percentil 95 fijado en entrenamiento), la reducción fue **1,244 µg/m³
  (6,34 %)** y el MAE de Qwen siguió siendo elevado: **18,371 µg/m³**. Fuente:
  [reports/models/prueba-reservada-lima.md](../../reports/models/prueba-reservada-lima.md).
- Los cinco métodos comparten un denominador de **304 734 pares ventana-hora**, que por ventanas
  solapadas representan **51 319 horas de estación distintas**; en la presentación hay que
  distinguir siempre ambas cifras y no presentarlas como observaciones independientes. Fuente:
  [reports/models/prueba-reservada-lima.md](../../reports/models/prueba-reservada-lima.md).
- El alcance es **retrospectivo**: se pronostica sobre las horas publicadas por SENAMHI; no se
  afirma disponibilidad en tiempo real ni uso regulatorio diario. Fuentes:
  [docs/decisions/005-senamhi-operating-policy.md](../decisions/005-senamhi-operating-policy.md) y
  [DATA_ATTRIBUTION.md](../../DATA_ATTRIBUTION.md).
- Los datos provienen del **Servicio Nacional de Meteorología e Hidrología del Perú (SENAMHI)**,
  base *Monitoreo de los contaminantes del aire en Lima Metropolitana*, bajo **ODC-By-1.0** con
  atribución obligatoria. Fuente: [DATA_ATTRIBUTION.md](../../DATA_ATTRIBUTION.md).

## Esquema de la presentación

Secciones en orden sugerido. Cada una indica el mensaje central, la evidencia citada por ruta y su
estado actual.

### 1. Portada y equipo

- Mensaje: equipo **Cuybernautas** (tres integrantes) y problema de partida: la calidad del aire en
  Lima y la utilidad de anticipar la evolución horaria de PM2.5.
- Evidencia: registro del equipo e inscripciones por confirmar en
  [docs/hackathon.md](../hackathon.md).
- Estado: mensaje listo; inscripciones individuales pendientes de confirmación.

### 2. Problema y caso de uso

- Mensaje: dado un bloque de 24 horas consecutivas de PM2.5 de una estación, estimar las seis
  horas siguientes; caso de uso de un analista ambiental que revisa la evolución retrospectiva.
- Evidencia: selección de la fuente y del objetivo en
  [reports/benchmark-selection.md](../../reports/benchmark-selection.md) y política aprobada en
  [docs/decisions/005-senamhi-operating-policy.md](../decisions/005-senamhi-operating-policy.md).
- Estado: listo.

### 3. Datos y atribución

- Mensaje: base SENAMHI bajo ODC-By-1.0 con atribución; grilla de **577 717 horas** entre siete
  series, de las cuales **367 518** tienen valor; primer valor el 01/01/2015 a las 05:00 UTC y
  último el 31/05/2024 a las 23:00 UTC. La unidad µg/m³ es una inferencia aceptada y la calidad
  individual de cada lectura sigue desconocida; sin imputación para crear observaciones.
- Evidencia: [docs/dataset-cards/lima-pm25-forecast.md](../dataset-cards/lima-pm25-forecast.md),
  [DATA_ATTRIBUTION.md](../../DATA_ATTRIBUTION.md),
  [docs/decisions/005-senamhi-operating-policy.md](../decisions/005-senamhi-operating-policy.md).
- Estado: listo.

### 4. Conjunto en formato TimeF y aporte a TimeNet

- Mensaje: `airaware/lima-pm25-forecast@0.1.0` presenta tareas de pronóstico con 24 horas de
  historia y seis objetivos ordenados por hora; **338 892 tareas** verificadas con el lector
  oficial (suma de 237 397 de entrenamiento, 50 706 de validación y 50 789 de prueba). La
  construcción y verificación se repiten sin red; el aporte a TimeNet está en el PR externo
  [#796](https://github.com/OpenTSLM/TimeNet/pull/796) (borrador, solo se enlaza).
- Evidencia:
  [docs/dataset-cards/lima-pm25-forecast.md](../dataset-cards/lima-pm25-forecast.md) (tabla de
  particiones), [tasks/issue-22-plan.md](../../tasks/issue-22-plan.md) (suma de tareas) y
  [tools/timenet-smoke/README.md](../../tools/timenet-smoke/README.md) (lectura y verificación
  con `TimeFReader` y `LocalRegistry` sin red).
- Estado: listo; el PR externo #796 permanece como borrador y no se comenta ni modifica.

### 5. Método de evaluación

- Mensaje: los modelos, las referencias y la regla de evaluación se fijaron antes de exportar la
  prueba (selección congelada del 19/11/2026); los cinco métodos se evaluaron sobre los mismos
  objetivos de los mismos **50 789 orígenes** de prueba (del 26/02/2023 a las 17:00 UTC al
  29/05/2024 a las 20:00 UTC), con partición cronológica y sin fuga.
- Evidencia:
  [reports/models/prueba-reservada-lima.md](../../reports/models/prueba-reservada-lima.md)
  (selección congelada y cobertura de orígenes),
  [reports/baselines/lima-pm25.md](../../reports/baselines/lima-pm25.md) (referencias y
  particiones de 2 033 352 objetivos).
- Estado: listo.

### 6. Resultados

- Mensaje: tabla de MAE en µg/m³ sobre el denominador común de 304 734 pares ventana-hora
  (51 319 horas de estación distintas por solapamiento):

  | Método | MAE global (µg/m³) | Diferencia frente a persistencia | MAE con concentración alta (µg/m³) |
  | --- | ---: | ---: | ---: |
  | Qwen directo con LoRA | **4,994** | **−1,452** | **18,371** |
  | Red convolucional temporal | 5,158 | −1,288 | 18,434 |
  | Persistencia | 6,446 | 0,000 | 19,616 |
  | Misma hora del día anterior | 7,038 | +0,592 | 23,086 |
  | Promedio de entrenamiento por serie y hora UTC | 8,269 | +1,823 | 34,144 |

  Reducción total de **22,52 %** frente a persistencia; en concentraciones altas (10 574 objetivos
  que corresponden a 1772 horas de estación distintas), **6,34 %**. La reducción se mantuvo en las
  siete estaciones (de 0,768 µg/m³ en San Borja a 2,603 µg/m³ en Carabayllo) y en las seis horas
  futuras (de 0,272 µg/m³ a una hora a 2,542 µg/m³ a seis).
- Evidencia: tabla copiada de
  [reports/models/prueba-reservada-lima.md](../../reports/models/prueba-reservada-lima.md); los
  MAE de prueba de las tres referencias coinciden con
  [reports/baselines/lima-pm25.md](../../reports/baselines/lima-pm25.md) (persistencia 6,4459).
- Estado: listo.

### 7. Demo y ejemplos

- Mensaje previsto: abrir el conjunto con el lector oficial de TimeNet, mostrar las 24 horas de
  historia y superponer las seis predicciones de Qwen, la referencia de persistencia y las
  observaciones de cada ventana de validación. Explicar un acierto y un error: en **Carabayllo** Qwen anticipa parte
  del descenso y reduce el MAE de la ventana en 3,04 µg/m³; en **San Juan de Lurigancho** pierde
  la subida final y persistencia obtiene 2,03 µg/m³ menos. Ambos ejemplos se eligieron en
  validación, antes de la prueba.
- Evidencia: figura [reports/models/lima-pm25-prueba.png](../../reports/models/lima-pm25-prueba.png),
  informe [reports/models/prueba-reservada-lima.md](../../reports/models/prueba-reservada-lima.md)
  y regla de selección de ejemplos en
  [reports/models/validacion-cabezales-qwen.md](../../reports/models/validacion-cabezales-qwen.md);
  apoyo visual del mapa de estaciones en [web/estaciones.html](../../web/estaciones.html) (solo se
  enlaza; no se modifica en esta entrega).
- Estado: insumos listos; la grabación de la demo está pendiente (ver [Pendientes](#pendientes)).

### 8. Límites y alcance

- Mensaje: la evaluación es retrospectiva sobre las horas publicadas; la disponibilidad histórica
  en tiempo real no está confirmada institucionalmente, la posición del intervalo y la calidad
  individual son desconocidas, las identidades de estación son provisionales y las ventanas se
  solapan. Las etiquetas regulatorias diarias permanecen diferidas mientras #20 siga abierta.
- Evidencia:
  [docs/decisions/005-senamhi-operating-policy.md](../decisions/005-senamhi-operating-policy.md),
  [docs/dataset-cards/lima-pm25-forecast.md](../dataset-cards/lima-pm25-forecast.md),
  [reports/models/prueba-reservada-lima.md](../../reports/models/prueba-reservada-lima.md).
- Estado: listo.

### 9. Aportes realizados durante el reto

- Mensaje: identificar los cambios hechos durante el hackathon: integración y verificación del
  conjunto en TimeNet (PR externo [#796](https://github.com/OpenTSLM/TimeNet/pull/796), en
  borrador), evaluación reservada fusionada
  ([PR #97](https://github.com/keneth-arias/Neblima/pull/97)) y recorrido reproducible desde la
  observación hasta la predicción sin red.
- Evidencia: [docs/hackathon.md](../hackathon.md) (criterios que el jurado puede comprobar),
  [tools/timenet-smoke/README.md](../../tools/timenet-smoke/README.md).
- Estado: listo.

### 10. Cierre

- Mensaje: qué sigue (demo grabada, capturas y publicaciones autorizadas), créditos al equipo
  Cuybernautas y atribución obligatoria a SENAMHI (ODC-By-1.0), sin prometer premios.
- Evidencia: [DATA_ATTRIBUTION.md](../../DATA_ATTRIBUTION.md),
  [docs/hackathon.md](../hackathon.md), inventario en [enlaces.md](enlaces.md).
- Estado: mensaje listo; los enlaces de entrega pendientes están en
  [enlaces.md](enlaces.md).

## Reglas de redacción para el material

- Copiar cifras solo de los reportes citados por ruta, siempre con su unidad (µg/m³); no inventar
  ni extrapolar métricas.
- Distinguir siempre los 304 734 pares ventana-hora (objetivos repetidos por ventanas solapadas)
  de las 51 319 horas de estación distintas.
- Mantener visible el carácter retrospectivo y la atribución a SENAMHI con su licencia
  ODC-By-1.0 en cada diapositiva o publicación.
- No afirmar disponibilidad en tiempo real, uso regulatorio diario ni recomendaciones de salud;
  no prometer premios ni créditos del organizador.
- Mostrar también un error del modelo (San Juan de Lurigancho), no solo aciertos.
- Nada se publica ni se envía sin la autorización prevista en el plan.

## Pendientes

### Listo en esta entrega

- Esquema de presentación con evidencia citada por ruta (este documento).
- Inventario de enlaces de entrega con su estado ([enlaces.md](enlaces.md)).
- Matriz de requisitos y plazo ya registrados en [docs/hackathon.md](../hackathon.md).

### Espera datos o trabajo interno

- Grabar la demo con TimeF (24 horas de historia, seis predicciones, referencia y observaciones
  reservadas): los insumos ya existen (figura y reportes; #24, #27 y #28 están cerradas y el
  PR #97 está fusionado), pero la grabación no se ha hecho.
- Preparar los textos definitivos para X, LinkedIn y Discord y las capturas fechadas de métricas
  (alcance de #29).
- La indisponibilidad del servidor antiguo de datos no bloquea esta entrega: todas las cifras
  provienen de reportes versionados en el repositorio; reexportar datos sería un trabajo aparte.

### Espera autorización o acción personal

- Publicar en X y LinkedIn (ambas requeridas por la página oficial): no se ha publicado nada;
  espera la autorización de Keneth.
- Compartir en el Discord del hackathon: no se ha enviado ningún mensaje; espera autorización.
- Enviar el formulario oficial por equipo y ronda: pendiente de envío autorizado; sin comprobante.
- Confirmar la inscripción individual de cada integrante (equipo Cuybernautas, tres personas,
  inscripciones por confirmar).

### Dependencias verificadas de otras issues

- #24, #27 y #28: **cerradas**; su evidencia está en el repositorio (PR #97 fusionado).
- #20 (etiquetas de episodios de contaminación): **abierta**; mientras siga abierta, la
  presentación no incluye afirmaciones regulatorias diarias.
- Antes de cualquier envío: volver a consultar la página oficial y el plazo; la última revisión
  registrada es del 17/11/2026 y el cierre de la primera ronda es el 23/11/2026 a las 2:59 a. m.
  en America/Lima ([docs/hackathon.md](../hackathon.md)).
