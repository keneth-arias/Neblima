# Glosario práctico del proyecto

Usamos términos en español para trabajar juntos. Los nombres de archivos, comandos y API conservan
su forma técnica para poder copiarlos sin errores.

| Término | Qué significa aquí |
| --- | --- |
| Tarea o issue | Trabajo con un objetivo, criterios de aceptación y una forma de comprobarlo |
| PR (pull request) | Solicitud para revisar e integrar cambios de una rama a otra |
| Rama | Línea de trabajo separada; permite cambiar archivos sin afectar la rama principal |
| Commit | Versión registrada de un grupo de cambios; no equivale a subirlos a GitHub |
| CI, integración continua | Controles automáticos que se ejecutan al subir cambios o abrir un PR |
| Entorno virtual (.venv) | Dependencias de Python propias de una copia del proyecto |
| CLI | Herramienta que se usa escribiendo comandos en una terminal |
| API | Interfaz con reglas para que un programa use datos o funciones de otro |
| Conjunto de datos o dataset | Datos y metadatos organizados para un propósito definido |
| Serie temporal | Mediciones ordenadas por fecha y hora |
| Frecuencia de muestreo | Cada cuánto se obtiene una medición; no confundir con el periodo usado para promediar |
| Entrada o variable | Información disponible al momento de hacer el pronóstico |
| Objetivo o target | Valor que queremos predecir; debe venir de mediciones válidas |
| Historia de 72 horas | Las 72 horas anteriores utilizadas para construir las entradas |
| Horizonte de 24 horas | Las siguientes 24 horas que se quieren pronosticar |
| Entrenamiento, validación y prueba | Datos para aprender, elegir configuraciones y evaluar el resultado final, respectivamente |
| Fuga de información | Uso indebido de información del futuro o del conjunto reservado que hace parecer mejor al modelo |
| Máscara de datos faltantes | Indicador de qué valores están presentes y cuáles no |
| Imputación | Estimación de un dato faltante; debe justificarse, documentarse y no usar información futura |
| Modelo de referencia o baseline | Método sencillo con el que se compara un modelo más complejo |
| Benchmark | Conjunto y procedimiento fijo para comparar métodos con los mismos objetivos |
| Procedencia y trazabilidad | Registro que permite llegar desde un resultado hasta su fuente y transformaciones |
| SHA-256 | Suma de verificación para detectar si cambió el contenido de un archivo |
| CRS | Sistema de referencia que permite interpretar coordenadas; no se debe suponer |
| Parquet | Formato de archivos por columnas para almacenar y consultar datos |
| TimeF | Formato de TimeNet; se genera y valida con sus herramientas oficiales |
| PM2.5 | Material particulado fino; conservar unidad, método y periodo de promedio documentados por la fuente |
| Bloqueo | Insumo o permiso que falta para avanzar; se registra con el siguiente paso concreto |

Ejemplo: una ventana de 72/24 usa 72 horas de historia para pronosticar las siguientes 24.
La lluvia que recién se observó después del inicio de esas 24 horas no es una entrada disponible
para un pronóstico operativo. Un pronóstico meteorológico emitido antes puede evaluarse como entrada
si se conserva cuándo estuvo disponible.
