# Borradores de publicaciones para la primera ronda del hackathon

Textos propuestos para X, LinkedIn y el Discord del hackathon de
[TimeNet](https://challenge.timenet.ai/). **Nada se ha publicado ni enviado**: cada texto de
este archivo está marcado "Borrador — sin publicar" y espera la autorización prevista en el
plan (Keneth valida las afirmaciones y autoriza cada publicación; matriz en
[docs/hackathon.md](../hackathon.md) y reglas de redacción en
[README.md](README.md)). Después de publicar, registrar enlace, fecha y comprobante en
[enlaces.md](enlaces.md), sin borrar el estado anterior.

## Reglas aplicadas a los tres textos

- Todas las cifras se copian con su unidad de
  [reports/models/prueba-reservada-lima.md](../../reports/models/prueba-reservada-lima.md):
  MAE de 4,994 µg/m³ frente a 6,446 µg/m³ de persistencia; reducción de 22,52 % global y
  6,34 % en concentraciones altas (percentil 95); MAE alto restante de 18,371 µg/m³;
  ejemplos elegidos en validación antes de la prueba (Carabayllo, −3,04 µg/m³ de MAE de
  ventana; San Juan de Lurigancho, persistencia 2,03 µg/m³ menos).
- Cuando se menciona el tamaño de la evaluación, se distinguen los 304 734 pares
  ventana-hora de las 51 319 horas de estación distintas (ventanas solapadas, no
  observaciones independientes).
- El alcance retrospectivo es visible en cada texto; ningún texto afirma disponibilidad en
  tiempo real, uso regulatorio diario ni recomendaciones de salud.
- Cada texto atribuye los datos a SENAMHI bajo ODC-By-1.0.
- Cada texto incluye un caso de error del modelo (San Juan de Lurigancho), no solo aciertos.
- Ningún texto promete premios ni créditos del organizador.

## X

**Estado: Borrador — sin publicar.**

Texto propuesto (277 caracteres, dentro del límite de 280; el texto va en una sola línea):

```
Con 24 h de historia de PM2.5, error absoluto medio de 4,994 µg/m³ frente a 6,446 de persistencia (−22,52 %) en Lima; en concentraciones altas, 6,34 %. En San Juan de Lurigancho pierde una subida y persistencia gana 2,03 µg/m³ menos. Retrospectivo. Datos: SENAMHI (ODC-By-1.0).
```

Notas para la publicación:

- El límite de 280 caracteres impide glosar las siglas: PM2.5 (partículas finas) y el error
  absoluto medio se explican en los textos de LinkedIn y Discord, que no tienen ese límite.
- Imagen sugerida: la figura
  [reports/models/lima-pm25-prueba.png](../../reports/models/lima-pm25-prueba.png), que
  muestra unidad y fechas. Adjuntarla solo con autorización.
- La matriz de [docs/hackathon.md](../hackathon.md) pide capturas fechadas de las métricas
  disponibles: guardar la captura del texto publicado y de la figura tal como se mostró.

## LinkedIn

**Estado: Borrador — sin publicar.**

Texto propuesto:

> Nuestro equipo Cuybernautas participa en la primera ronda del hackathon online de TimeNet
> (noviembre de 2026) con un caso de calidad del aire en Lima, Perú.
>
> Con 24 horas consecutivas de historia de partículas finas (PM2.5) de una estación,
> evaluamos retrospectivamente el pronóstico de las seis horas siguientes. El conjunto
> `airaware/lima-pm25-forecast@0.1.0`, construido con datos del Servicio Nacional de
> Meteorología e Hidrología del Perú (SENAMHI) bajo la licencia ODC-By-1.0 con atribución,
> tiene 338 892 tareas en formato TimeF verificadas con el lector oficial (237 397 de
> entrenamiento, 50 706 de validación y 50 789 de prueba).
>
> El modelo temporal evaluado (Qwen3.5-0.8B con adaptación de bajo rango (LoRA)) obtuvo un
> error absoluto medio (MAE) de 4,994 µg/m³ frente a 6,446 µg/m³ de la referencia de
> persistencia en la prueba cronológica reservada: una reducción de 22,52 %. En
> concentraciones altas (percentil 95 fijado en entrenamiento), la reducción fue 6,34 % y
> el MAE siguió siendo elevado: 18,371 µg/m³. La evaluación comparte un denominador de
> 304 734 pares ventana-hora, que por ventanas solapadas representan 51 319 horas de
> estación distintas; no son observaciones independientes.
>
> El modelo no acierta siempre. En un ejemplo de validación de Carabayllo anticipa parte
> del descenso y reduce el MAE de la ventana en 3,04 µg/m³ frente a persistencia; en San
> Juan de Lurigancho pierde la subida final y persistencia obtiene un MAE menor por
> 2,03 µg/m³. Ambos ejemplos se eligieron antes de la prueba.
>
> Alcance: retrospectivo, sobre las horas publicadas por SENAMHI. No afirmamos
> disponibilidad en tiempo real ni uso regulatorio diario; la unidad µg/m³ es una
> inferencia aceptada y la calidad individual de cada lectura sigue desconocida.
>
> Código y evidencia: https://github.com/keneth-arias/airaware
> Datos: SENAMHI, base Monitoreo de los contaminantes del aire en Lima Metropolitana
> (ODC-By-1.0). Derivaciones y pronósticos: equipo Cuybernautas.
>
> #TimeSeries #CalidadDelAire #PM25 #Perú

Notas para la publicación:

- El enlace al repositorio ya es público según
  [enlaces.md](enlaces.md); no añadir otros enlaces (demo o capturas) hasta que existan y
  estén autorizados.
- Guardar captura fechada del texto publicado y de las métricas visibles, como pide la
  matriz de [docs/hackathon.md](../hackathon.md).

## Discord del hackathon

**Estado: Borrador — sin publicar.**

Texto propuesto:

> Hola, somos el equipo Cuybernautas (Perú). Esta es nuestra entrada a la ronda 1:
> pronóstico retrospectivo de partículas finas (PM2.5) para las seis horas siguientes en
> estaciones de Lima.
>
> - Conjunto: `airaware/lima-pm25-forecast@0.1.0` en formato TimeF, con datos del SENAMHI
>   bajo ODC-By-1.0; 338 892 tareas verificadas sin red con `TimeFReader` y
>   `LocalRegistry`. Aporte de datos a TimeNet, en borrador:
>   https://github.com/OpenTSLM/TimeNet/pull/796
> - Resultados de la prueba cronológica reservada: error absoluto medio (MAE) de 4,994
>   µg/m³ frente a 6,446 µg/m³ de persistencia (−22,52 %); en concentraciones altas, la
>   reducción fue 6,34 % y el MAE siguió alto (18,371 µg/m³). El denominador común es de
>   304 734 pares ventana-hora, es decir 51 319 horas de estación distintas por el
>   solapamiento de ventanas.
> - Un acierto y un error: en Carabayllo el modelo reduce el MAE de la ventana en 3,04
>   µg/m³ frente a persistencia; en San Juan de Lurigancho pierde la subida final y
>   persistencia obtiene un MAE menor por 2,03 µg/m³.
> - Alcance retrospectivo sobre las horas publicadas; sin tiempo real ni uso regulatorio.
>
> Repositorio: https://github.com/keneth-arias/airaware
> Atribución obligatoria: datos de SENAMHI (ODC-By-1.0); derivaciones y pronósticos del
> equipo Cuybernautas.

Notas para la publicación:

- El enlace del PR externo se incluye solo como referencia; el PR #796 permanece como
  borrador y no se comenta ni modifica (regla de
  [README.md](README.md), sección 4).
- Guardar el enlace permanente del mensaje o su captura fechada como comprobante en
  [enlaces.md](enlaces.md).

## Pendientes comunes

- Autorización explícita de Keneth para publicar cada texto; ningún envío desde este
  repositorio.
- Antes de cualquier envío: volver a consultar la página oficial y el plazo; la última
  revisión registrada está en [enlaces.md](enlaces.md) y el cierre de la primera ronda en
  [docs/hackathon.md](../hackathon.md).
- Después de publicar: registrar en [enlaces.md](enlaces.md) fecha, enlace y comprobante de
  cada publicación, y adjuntar las capturas fechadas de métricas exigidas por la matriz.
