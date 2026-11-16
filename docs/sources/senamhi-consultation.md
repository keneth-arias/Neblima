# Consulta enviada a SENAMHI

Envío autorizado expresamente por Keneth y realizado mediante Outlook desde keneth.arias@outlook.com
hacia info.sgd@senamhi.gob.pe. Outlook confirmó la operación y se encontró el mensaje por asunto y
destinatario, con marca de correo 2026-11-16T01:02:04Z. No confirma recepción ni respuesta de SENAMHI.
Seguimiento: [#43](https://github.com/keneth-arias/airaware/issues/43).
No reenviar ni programar recordatorios sin una nueva instrucción de Keneth.

**Asunto:** Consulta académica sobre datos de calidad del aire para el proyecto Air Aware — Hackathon TimeNet

## Texto enviado

Estimado equipo de la Subdirección de Gestión de Datos del SENAMHI:

Reciban un cordial saludo. Mi nombre es Keneth Arias, soy docente peruano de Tecnologías de la Información y la Comunicación (TIC). Junto con dos estudiantes peruanos estamos desarrollando Air Aware (AirAware Perú), un proyecto con el que participamos en el hackathon TimeNet.

Nuestro propósito es aprender y aportar, desde un trabajo académico y colaborativo, al estudio de la calidad del aire en Lima y el Perú mediante el análisis de series temporales. Para ello, estamos preparando un conjunto de datos reproducible que permita investigar y evaluar modelos de pronóstico, procurando respetar tanto el significado de las mediciones como las condiciones de uso de la información.

Agradecemos que el SENAMHI ponga a disposición estos datos. Hemos revisado el conjunto «Monitoreo de los contaminantes del aire en Lima Metropolitana», junto con su diccionario y metadatos:
https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de

También consultamos el manual MT-DRD-005 y boletines oficiales. Sin embargo, todavía tenemos algunas dudas que preferimos aclarar antes de transformar o compartir los datos. Si estuviera a su alcance, agradeceríamos mucho su orientación sobre los siguientes puntos:

1. Unidades de las mediciones. ¿Qué unidades utilizan PM10, PM2_5 y NO2 en el CSV publicado? El diccionario no las precisa. Observamos que el manual MT-DRD-005 expresa NO2 en ppb, mientras que el boletín de febrero de 2018 lo presenta en µg/m³. ¿El CSV contiene valores convertidos? De ser así, ¿qué procedimiento y condiciones de temperatura y presión se aplicaron, y hubo cambios por estación o periodo?

2. Fecha y hora. ¿Los campos FECHA y HORA están expresados en UTC o en hora peruana? ¿La hora indica el inicio o el final del promedio horario y cuál es el mínimo de datos requerido para calcularlo? Como referencia, el máximo de NO2 de Campo de Marte del 16/02/2018 figura con un valor de 36.6 a las 08:00 en el boletín, y con el mismo valor a las 13:00 en el CSV (ID 27417). Encontramos la misma diferencia de cinco horas en otros cuatro casos. Quisiéramos confirmar su interpretación y si se mantiene durante todo el periodo.

3. Validación y datos faltantes. ¿Qué procedimiento de validación se aplicó a esta exportación? ¿Las celdas vacías son la única forma de representar datos faltantes o existen otros códigos? ¿Hay banderines de calidad o registros de mantenimiento y cambios de instrumentos que podamos consultar?

4. Ubicación de estaciones y códigos. ¿Podrían confirmarnos el sistema geodésico y si LATITUD y LONGITUD están expresadas en grados decimales? ¿Existe un historial de reubicación de estaciones? Asimismo, ¿cuál es la representación correcta de UBIGEO, considerando que el diccionario indica seis posiciones alfanuméricas y en el archivo aparecen valores como 150113.0?

5. Reutilización y disponibilidad. El catálogo y los metadatos indican Open Data Commons Attribution License. ¿Podrían confirmarnos la versión aplicable y la atribución o los avisos que debemos conservar si compartimos una versión derivada para investigación, normalizada y organizada en el formato TimeF de TimeNet? También agradeceríamos saber si existen condiciones adicionales o series más recientes y archivos complementarios disponibles para este propósito.

Para identificar el archivo consultado: el CSV tiene 68 501 558 bytes y su SHA-256 es:
896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4

Por el momento, no hemos publicado el archivo ni una versión derivada. Si estas consultas ya están resueltas en alguna guía o documento, nos sería de mucha ayuda conocer la referencia. Si corresponde dirigirlas a otra área, agradeceremos que nos indiquen el canal adecuado.

Entendemos que su equipo tiene diversas responsabilidades; cualquier orientación que puedan brindarnos será muy valiosa para nosotros. Muchas gracias por su tiempo y por el trabajo que realizan.

Atentamente,

Keneth Arias
Docente de Tecnologías de la Información y la Comunicación
Equipo Air Aware — dos estudiantes peruanos y un docente peruano
keneth.arias@outlook.com
https://github.com/keneth-arias/airaware

## Revisión y alcance

El texto enviado adapta la consulta investigada a un tono cordial en español del Perú e identifica
al equipo como dos estudiantes peruanos y un docente peruano de TIC, según indicó Keneth.
Las cinco preguntas se contrastaron con fuentes oficiales y con el CSV identificado por SHA-256.
El desfase horario se describe como observación; no se declara confirmada la semántica del histórico.
No se adjuntaron datos masivos ni se publicaron credenciales, identificadores privados o enlaces del buzón.
La revisión técnica y editorial la realizó el mismo agente; no es revisión externa ni respuesta de SENAMHI.
