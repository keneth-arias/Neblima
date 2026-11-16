# Consulta a OEFA — borrador para revisión de Keneth

Estado: no enviado. Destinatario: Servicio de Información y Atención al Ciudadano del OEFA
<consultas@oefa.gob.pe>, verificado en su página institucional de contacto. Remitente propuesto: Keneth Arias <keneth.arias@outlook.com>.
Sin copia a otros contactos ni archivos adjuntos. Envío requiere instrucción de Keneth.

Asunto: Consulta y orientación sobre datos de calidad del aire para proyecto educativo AirAware Perú

Estimado equipo del Servicio de Información y Atención al Ciudadano del OEFA:

Reciba un cordial saludo. Mi nombre es Keneth Arias, soy profesor peruano de Tecnologías de la
Información y Comunicación. Junto con dos estudiantes peruanos estamos desarrollando AirAware Perú,
un proyecto educativo de análisis y pronóstico de calidad del aire para nuestra participación en el
hackathon TimeNet (https://challenge.timenet.ai/), con interés inicial en Lima y posible extensión al Perú.

Nos dirigimos a su canal institucional para solicitar orientación sobre el conjunto «Vigilancia y
Seguimiento ambiental en la calidad del aire» de la Plataforma Nacional de Datos Abiertos.
Les agradeceríamos que, de corresponder, pudieran derivar esta consulta a la Dirección de Evaluación
Ambiental (DEAM) o al equipo responsable de los datos. Agradecemos que el OEFA ponga esta
información a disposición de la ciudadanía. Hemos revisado el CSV y sus documentos procurando
conservar los originales y evitar interpretaciones que no estén sustentadas.

En el archivo descargado encontramos fechas entre 2018 y 2022; muchas filas tienen HORA_INICIO=NA
y otras contienen horas precedidas por fechas base de 1899. En los puntos de Lima CA-HU-04,
CA-HU-09, CA-RZC-01 y CA-RZC-02 encontramos valores de PM2.5 y PM10, pero no hemos podido
establecer sus instantes horarios con la documentación revisada. Es posible que nos falte conocer
la estructura o una exportación más adecuada; por ello agradeceríamos su orientación.

Si estuviera a su alcance, ¿podrían ayudarnos con estas consultas o derivarnos al equipo correspondiente?

1. ¿Existe un archivo o canal oficial de históricos validados de PM2.5 y PM10 para Lima, con fecha,
   hora y banderas de calidad? Nos serviría conocer estaciones, periodo disponible y enlace de descarga.
   También encontramos la ficha institucional EAS que anuncia datos hasta junio de 2024; ¿qué relación
   tiene con el CSV nacional y con los históricos que puedan consultarse en PIFA?
2. ¿Cómo deben interpretarse HORA_INICIO/HORA_FIN, sus valores NA y las fechas base de 1899?
   ¿Qué zona horaria usan y el sello temporal corresponde al inicio o fin del periodo medido?
3. ¿Qué representa cada fila cuando hay distintos TIPO_ANALISIS y valores repetidos? ¿Existe un
   identificador para relacionar cada observación con su parámetro/unidad y distinguir registros legítimos?
4. ¿Hay una guía de marcadores como «-» o NA, validación, mantenimiento y reglas para promedios
   horarios, de 24 horas y móviles? Queremos evitar tratar «no aplica» como dato perdido o usar
   información que aún no estaba disponible al momento de un pronóstico.
5. ¿Podrían indicarnos un registro de estaciones, cambios de ubicación y sistema de coordenadas
   que permita interpretar ESTE, NORTE, ZONA y DATUM de forma segura?
6. El catálogo nacional indica ODC-By. ¿Qué aviso de atribución recomiendan y qué licencia corresponde
   a los archivos de la ficha institucional EAS, cuyo pie enlaza otra licencia?

No buscamos que preparen una base nueva: cualquier documentación, enlace existente o recomendación
breve que nos permita usar correctamente los datos sería de gran ayuda. Si lo consideran pertinente
 y cuentan con disponibilidad, también agradeceríamos una breve orientación técnica con el equipo responsable.

Comprendemos la carga de trabajo que tienen y valoramos mucho el tiempo que puedan brindarnos.
Nuestro repositorio es https://github.com/keneth-arias/airaware. Con gusto podemos compartir ejemplos
pequeños de los campos que nos generan dudas, sin adjuntar el archivo completo.

Muchas gracias por su atención y por el trabajo que realizan.

Atentamente,
Keneth Arias
Profesor de Tecnologías de la Información y Comunicación
Equipo AirAware Perú
keneth.arias@outlook.com
