# Plan del conjunto de datos

## Alcance

Empezar con Lima y Callao y ampliar al Perú cuando la cobertura lo permita.
Priorizar PM2.5 y PM10 medidos. Confirmar estaciones, fechas, intervalo y horizonte después del análisis.

## Investigación de fuentes

Revisar SENAMHI, OEFA, el Portal Nacional de Datos Abiertos y OpenAQ como candidatos.
Registrar enlaces reales, requisitos de acceso, cobertura y derechos antes de importar datos.

## Recolección y normalización

- Conservar originales y registrar parámetros, fecha UTC y suma de verificación SHA-256.
- Preservar fechas y zona horaria originales; normalizar a UTC y usar America/Lima para calendario.
- Registrar coordenadas, contaminante, unidad, periodo de promedio, método y marcas de calidad.
- Conservar datos faltantes como tales. Documentar negativos, límites de detección y conversiones.
- El CSV de observaciones es una plantilla interna, no un archivo TimeNet validado.

## Calidad y evaluación

Medir cobertura, datos faltantes, huecos, duplicados y conflictos por estación, contaminante,
fecha y periodo. Resolver conflictos con procedencia documentada.
Separar entrenamiento, validación y prueba cronológicamente. Ajustar el procesamiento solo con
entrenamiento. Comparar con persistencia y referencias estacionales; informar MAE y RMSE por
estación, contaminante y horizonte.

## Entrega TimeNet

Revisar el modelo de datos y los conectores vigentes antes de implementar. Mapear fuentes, señales,
ejes temporales, metadatos y tareas. Validar una construcción local y preparar el PR externo,
cuya apertura requiere la autorización del plan. La plantilla CSV por sí sola no es un conjunto TimeNet.

## Condiciones del primer conjunto

Derechos confirmados, recolección reproducible, procedencia trazable, informe de calidad,
particiones cronológicas definidas y una construcción TimeF validada.
