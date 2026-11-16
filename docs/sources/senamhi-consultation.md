# Consulta técnica preparada para SENAMHI

Estado: revisada, pendiente de revisión final de Keneth y de autorización de envío. No enviada.
Destinatario propuesto: info.sgd@senamhi.gob.pe, contacto consignado en el DOCX del conjunto.
Su publicación en el documento no confirma la disponibilidad actual del buzón.
Remitente propuesto: Keneth Arias, responsable de datos y plataforma de AirAware Perú.

**Asunto:** Aclaraciones sobre unidades, tiempo y reutilización del conjunto de calidad del aire de Lima

Estimado equipo de la Subdirección de Gestión de Datos del SENAMHI:

Somos el equipo de AirAware Perú. Participamos en el hackathon TimeNet y estamos preparando un conjunto
reproducible para investigación de series temporales de calidad del aire de Lima y el Perú.

Consultamos el conjunto «Monitoreo de los contaminantes del aire en Lima Metropolitana» publicado en
https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de,
su diccionario y metadatos. El CSV utilizado tiene 68 501 558 bytes y SHA-256
896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4.
No hemos publicado esa exportación ni una versión derivada. Agradeceríamos aclarar:

1. **Unidades.** ¿Qué unidad utiliza cada columna PM10, PM2_5 y NO2 en esta exportación? El diccionario
   no la especifica. MT-DRD-005 v01, tabla 1, usa NO2 en ppb, mientras el boletín de febrero de 2018
   muestra concentraciones en µg/m³. ¿El CSV contiene NO2 convertido? De ser así, ¿qué condiciones
   de temperatura/presión y procedimiento se aplicaron y hubo cambios por estación o periodo?
2. **Tiempo.** ¿FECHA/HORA corresponden a UTC, hora peruana u otra referencia? ¿Cada registro representa
   inicio o fin del promedio horario y qué criterio mínimo de disponibilidad se exige para ese promedio?
   Como ejemplo, el máximo NO2 de Campo de Marte del 16/02/2018 aparece con 36.6 a las 08:00 en el
   boletín (página 9), y con el mismo valor a HORA=130000 en el CSV (ID=27417). Cuatro casos adicionales
   presentan la misma diferencia de cinco horas. ¿Esta convención aplica a todo el periodo 2015–2024?
3. **Calidad y ausencias.** ¿Qué versión del proceso de validación se aplicó a la exportación? ¿Los valores
   vacíos son la única codificación de ausencia o existen otros códigos? ¿Es posible obtener los
   banderines y registros de mantenimiento/cambios instrumentales por estación y periodo?
4. **Ubicación y códigos.** ¿Cuál es el sistema geodésico de LATITUD/LONGITUD y están expresadas en grados
   decimales? El diccionario describe grados/minutos/segundos. ¿Existe un historial de reubicaciones?
   UBIGEO está declarado alfanumérico de seis posiciones, pero observamos 150113.0: ¿cuál es su
   representación canónica y cómo deben tratarse los códigos faltantes?
5. **Condiciones de reutilización.** Catálogo y metadatos declaran Open Data Commons Attribution License.
   ¿Confirman que ODC-BY v1.0 aplica a esta exportación y qué avisos/atribución debemos conservar para
   redistribuir una base derivada normalizada y particionada en TimeF, acompañada de procedencia y
   descripción de cambios? ¿Existe alguna condición adicional aplicable a sus contenidos o componentes?

Si hay documentación pública que ya resuelva estas preguntas, agradeceremos las referencias y su versión.
Nuestro objetivo es representar fielmente los datos y sus condiciones, diferenciando la licencia de la
base de datos de la del código del proyecto.

Saludos cordiales,
Keneth Arias
AirAware Perú — https://github.com/keneth-arias/airaware

## Revisión del borrador

Revisión técnica y editorial realizada el 16/11/2026:

- Preguntas contrastadas con XLSX/DOCX y documentos oficiales; se retiraron datos ya resueltos,
  como significado de FECHA_CORTE, para no solicitar aclaraciones innecesarias.
- Se identifica la versión por tamaño y SHA-256; no se adjuntan datos masivos ni se incluyen claves.
- El contraste de cinco horas se presenta como observación, sin afirmar UTC ni una unidad del CSV.
- Se pide aclarar condiciones declaradas, sin afirmar que la licencia prohíba reutilizar datos.
- El contacto proviene del DOCX; no se afirma haber confirmado el buzón ni recibido una respuesta.
- No se promete una publicación ni se confunden licencias del software y de la base.

La revisión anterior la realizó el mismo agente que investigó las fuentes; no es una revisión externa
ni una respuesta de SENAMHI. El envío requiere autorización expresa de Keneth.
