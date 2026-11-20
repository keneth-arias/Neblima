# Pronóstico de PM2.5 y PM10 en Lima con prueba externa

Para pronosticar las seis horas siguientes en una estación, cada tarea TimeF contiene 24 horas de historia y seis de objetivos en ambos contaminantes, en µg/m³. La unidad del histórico es inferida según ADR-005. El corte cronológico reserva para validación el tramo final del archivo histórico y usa datos nuevos para la prueba. La comparación A/B de #88 usa los mismos identificadores por partición y fuente.

| Conjunto | Partición | Ventanas | Objetivos escalares | Último objetivo disponible |
| --- | --- | ---: | ---: | --- |
| SENAMHI histórico | Entrenamiento | 251 915 | 3 022 980 | Antes del 02/04/2023 07:00 UTC |
| SENAMHI histórico | Validación | 44 458 | 533 496 | 30/05/2024 02:00 UTC |
| OpenAQ | Prueba principal | 85 538 | 1 026 456 | 15/09/2026 11:00 UTC |
| SENAMHI horario | Prueba complementaria | 102 768 | 1 233 216 | 19/11/2026 20:00, hora publicada |

## Corte y cobertura

El CSV histórico llega al 31/05/2024 23:00 UTC. Se reconstruyeron todas las ventanas completas antes del 01/06/2024. Para cada posible corte horario global se cuentan las ventanas cuyo último objetivo queda antes del corte y las que comienzan en él o después. Se elige la proporción de entrenamiento más cercana a 85 % entre las ventanas retenidas. En caso de empate se escoge la hora más temprana. La regla considera disponibilidad, sin optimizar errores de pronóstico. El 02/04/2023 a las 07:00 UTC separa 84,9993 % y 15,0007 % y purga 145 de 296 518 ventanas.

Antes de la purga nueva se cotejaron los identificadores y los 30 valores de PM2.5 de cada ventana común con las matrices congeladas de #28. Coincidieron las 198 320, 50 046 y 47 839 ventanas del diagnóstico anterior en sus respectivas particiones.

En la prueba se exige que la **primera hora de la historia** pertenezca al periodo externo. La consulta cubrió del 01/06/2024 al 20/11/2026, hasta las lecturas disponibles al recuperar cada fuente. Lightpanda consultó 24 gráficos de SENAMHI para dos contaminantes y 12 códigos provisionales, del 18 al 20 de noviembre, y 27 inventarios anuales del archivo de OpenAQ para nueve ubicaciones. La actualización no encontró objetos nuevos o modificados de OpenAQ. Allí hubo lecturas aisladas hasta el 29/10/2026 00:00 UTC. Para formar una ventana se necesitan 30 horas consecutivas de ambas señales.

En SENAMHI hay ventanas para siete sitios y en OpenAQ para seis. Carabayllo tiene observaciones de OpenAQ sin una ventana bivariada completa. Las dos ubicaciones de San Juan de Lurigancho conservan sus identificadores de OpenAQ. Una diferencia de código o de sensor impide unir tramos. El manifiesto registra los conteos por identidad, los sensores y las huellas de los identificadores. [Manifiesto de la preparación](../metadata/lima-pm-externa-20261120.json)

## Reloj, trazabilidad y evaluación

OpenAQ conserva los desplazamientos publicados y permite evaluar en UTC. Los gráficos directos de SENAMHI tienen etiquetas sin zona explícita. El contraste con el histórico da desplazamientos distintos según el periodo. En esas tareas el origen absoluto de TimeF es desconocido, se conserva la hora publicada y el eje del objetivo empieza 24 horas después del inicio relativo de la historia. Este conjunto admite pronósticos basados en las concentraciones. Las variables de calendario en UTC requieren resolver primero el reloj. OpenAQ puede republicar las mismas observaciones de SENAMHI. Informar errores separados por fuente, contaminante, estación y horizonte.

Cada registro contiene el código de estación, los dos identificadores de serie y sensor en orden `[pm25, pm10]`, la primera etiqueta horaria, el estado de la unidad, la calidad desconocida y la disponibilidad nula. La combinación de fuente, estación, sensor, contaminante y hora permite recuperar las filas y archivos originales en los Parquet de insumos. El manifiesto de fuentes y los recibos de actualización registran URL, fecha de recuperación y SHA-256. En el histórico, `fila` cuenta la cabecera como línea 1. En los gráficos, cuenta desde 1 los puntos de la serie publicada. Se conservan nulos en las observaciones largas y se excluyen horas faltantes, conflictos y valores no finitos al construir ventanas. Las ventanas consecutivas pueden solaparse dentro de cada partición.

Se verificaron los 12 147 archivos del manifiesto anterior y los 51 recursos de la actualización. La atribución y ODC-BY-1.0 documentadas en AirAware cubren el CSV histórico. Los productos posteriores se conservan localmente con atribución a SENAMHI y, en el archivo republicado, a OpenAQ y a su proveedor original. Una distribución de esos productos requiere documentar los permisos de cada fuente. [Atribución de datos](../DATA_ATTRIBUTION.md) · [Servicio de SENAMHI](https://www.senamhi.gob.pe/site/sea/www/site/sea/graficas/esta_conta.php?estacion=112194&conta=N_PM25) · [Archivo público de OpenAQ](https://docs.openaq.org/aws/about)

## Reproducción sin red

Desde la raíz y con el entorno bloqueado de TimeNet 0.12.0 instalado, usar una carpeta de salida nueva. Los originales y sus recibos se conservan en el almacenamiento compartido indicado en el ejemplo. El script de la consulta y las instrucciones de adquisición anteriores están en `$D/processed/pm-bivariado-20261120/reproduccion/actualizar.py` y `$B/reproduccion/`. La copia preparada se encuentra en `$D/processed/pm-bivariado-20261120/timef`.

```bash
D=/home/shared/github/keneth-arias/airaware/data
B="$D/processed/lima-postcorte-20261118"
R=$(mktemp -d)
T=tools/timenet-smoke
P="$T/.venv/bin/python"
"$P" "$T/stage_external_pm.py" "$D/raw/senamhi/senamhi_lima_monitoreo_1.csv" \
  "$B" "$D/raw/lima-postcorte-20261118" "$D/raw/lima-postcorte-20261120" "$R/insumos"
"$P" "$T/external_pm.py" historico "$R/historico" "$R/insumos/historico.parquet" \
  --begin 2015-01-01 --end 2024-06-01
"$P" "$T/external_pm.py" openaq "$R/openaq" "$B/observaciones.parquet" \
  --begin 2024-06-01 --end 2026-11-20T01:24:00
"$P" "$T/external_pm.py" senamhi_horario "$R/senamhi_horario" \
  "$B/observaciones.parquet" "$R/insumos/actualizacion.parquet" \
  --begin 2024-06-01 --end 2026-11-21
for fuente in historico openaq senamhi_horario; do
  "$P" "$T/verify_external_pm.py" "$R/$fuente" || exit 1
done
```

Cada registro tiene `resumen.json` y una versión `0.1.0` bajo `airaware/<nombre>/`. Abrir esa carpeta con `TimeFReader.open()`, ejecutar `verify()` y leer con `iter_tasks(split=...)`. Para entrenar, acceder por nombre a las señales de `task.inputs[0]`. Los valores futuros están en `task.targets[0]`. El verificador adicional recorre todos los bloques de ambos canales, contrasta los valores con las observaciones por estación y hora, comprueba relojes, unidades, particiones y unicidad y calcula la huella de identificadores ordenados por partición.

Dos construcciones completas reprodujeron los mismos conteos, identificadores y valores en los tres registros. Los SHA-256 físicos de sus manifiestos difieren y se conservan ambos en la evidencia. Los controles locales aprobaron 406 pruebas de AirAware y 17 del entorno TimeF, la construcción de paquetes y la auditoría de dependencias.

El [informe de las pruebas externas](models/prueba-externa-pm25-pm10.md) enlaza la verificación del conector hermano y compara los dos modelos congelados en cada proveedor. [Plan de #88](../tasks/issue-88-pm10.md)
