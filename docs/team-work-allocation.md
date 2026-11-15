# Responsables y orden de trabajo

El 15/11/2026 se reservaron 18 de las 35 tareas abiertas para el equipo mediante etiquetas y notas
de entrega. Las asignaciones nativas esperan que acepten las invitaciones; Keneth indicó mantener
estas reservas mientras tanto. Es una lista de trabajo futuro, no 18 tareas simultáneas.
GitHub conserva responsables, criterios y dependencias. Una tarea activa por persona es el límite inicial.

| Responsable | Función | Tareas reservadas |
| --- | --- | --- |
| Keneth / keneth-arias | Liderazgo de datos y plataforma; contratos comunes, decisiones científicas, CI, prevención de fuga de información y publicaciones | #1, #2, #3, #4, #6, #7, #11, #12, #14, #19, #20, #21, #22, #23, #27, #28, #32 |
| Cristopher / qriqs | Dedicación completa; investigación de fuentes e implementación acotada con pruebas | #5, #8, #9, #10, #13, #15, #16, #17, #18, #25, #26, #30, #31, #33, #34, #35 |
| Jordan / J0r-PS | Dedicación parcial; documentación guiada y preparación de la presentación | #24, #29 |

## Qué puede empezar cada uno

- Cristopher: #5, revisar enlaces y diccionarios de OEFA y registrar evidencia y dudas en
  docs/sources/oefa.md. No descargar datos masivos ni suponer coordenadas. El cambio final del
  catálogo espera #3. Keneth revisa licencias y sistema de referencia de coordenadas (CRS).
  Si OEFA no responde, puede investigar meteorología/OpenAQ (#16/#31); la descarga sigue sujeta
  a las dependencias originales.
- Jordan: #29, preparar un esquema de presentación y una lista de enlaces de entrega, indicando
  claramente lo pendiente. No necesita métricas ni publicar en redes para hacer el primer PR.
  La versión final espera #24/#28. Luego puede preparar la plantilla de ficha del conjunto de datos
  de #24. Keneth aporta y aprueba los datos científicos, licencias y código del conector.
- Keneth: revisar la base #1–#3 y SENAMHI #4; definir las interfaces de descarga #6/#7, los esquemas,
  la precedencia de fuentes y la separación temporal. El resto implementa sobre esos acuerdos.

La investigación y los borradores pueden comenzar antes de cumplir las dependencias de cierre.
El código que use una interfaz pendiente debe esperar o usar un contrato de prueba acordado.
Por ejemplo, se pueden preparar pruebas de calidad con datos sintéticos identificados como tales,
pero no reportar cobertura real antes de adquirir archivos reales. Ninguna reserva permite saltarse
controles de derechos, presupuesto, validez científica, fuga de información o publicación.

## Cómo entregar sin bloquear a los demás

Cada tarea reservada indica una primera entrega pequeña y las condiciones de revisión.
Trabaja en documentos o módulos propios de la fuente. Coordina cambios de configs/sources.yaml,
esquemas y comandos compartidos. Si el archivo común está en revisión, entrega primero el documento
con evidencia; Keneth coordina su integración al catálogo.

Ante un bloqueo, registra el insumo faltante y el siguiente paso; luego toma investigación o
redacción independiente. No modifiques el módulo de otra persona para evitar una dependencia.
Meteorología opcional, ampliación nacional, satélites y preguntas temporales no retrasan el primer
conjunto de evaluación basado solo en contaminación.

Keneth revisa unidades, CRS, licencias, datos faltantes, esquemas y fuga de información.
Los primeros PR de Jordan son de documentación, sin inventar resultados ni exigirle desarrollar el
conector o publicar externamente. Reservar tareas no cambia su disponibilidad ni impone un plazo.
