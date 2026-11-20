# Pronóstico privado de PM2.5 en Campo de Marte

El 20 de noviembre de 2026 comenzó la emisión privada de seis pronósticos horarios para la estación Campo de Marte (112194). Se usó el ajuste directo de Qwen con LoRA de rango 4, semilla 27 y paso 14 838. La primera emisión quedó guardada a las 20:33:38 UTC con insumos recibidos a las 20:32:57 UTC. Su origen lleva la etiqueta 15:00 en el reloj de la estación. Las huellas permiten comprobar la emisión en bm sin publicar las lecturas ni las predicciones operativas. [Recibo de la primera emisión](../../metadata/campo-marte-inmediato-v1/primera-emision.json) · [Selección del modelo](seleccion-concentracion-lima.md)

## Comparación retrospectiva

El diagnóstico cubre la semana del 13 al 19 de noviembre. El inventario documenta los recibos y el corte usados para reconstruirla. Tres consultas al gráfico de SENAMHI cubrieron las fechas del 12 al 20, con última recepción a las 20:25:58 UTC del día 20. Para el archivo se tomaron todas las ventanas completas del gráfico horario con historia y objetivos dentro del periodo del 1 de junio de 2024 al 11 de noviembre de 2026 inclusive. Ambas cohortes usaron la misma generación del modelo y los residuos de calibración congelados. Persistencia repite la última lectura de la historia. Los errores son errores absolutos medios (MAE) en µg/m³. La cobertura es la fracción de mediciones que quedan dentro del intervalo nominal de 80 %.

| Cohorte | Orígenes | Pares origen–horizonte | Horas objetivo distintas | MAE de Qwen | MAE de persistencia | Cobertura |
|---|---:|---:|---:|---:|---:|---:|
| Semana reciente | 168 | 1 008 | 173 | 2,202 | 3,171 | 99,90 % |
| Archivo completo | 17 927 | 107 562 | 18 307 | 5,382 | 6,424 | 93,28 % |
| Horas altas del archivo | — | 10 655 | 1 817 | 15,278 | 15,753 | 60,45 % |

La semana reciente tuvo cero horas objetivo iguales o superiores al umbral histórico de la estación de 34,95 µg/m³. En el archivo la diferencia de MAE, Qwen menos persistencia, fue −1,042 µg/m³, con intervalo de confianza de 95 % de −1,270 a −0,782. En las horas altas, la diferencia fue −0,475, con intervalo de −1,557 a +0,912. Se remuestrearon bloques calendario emparejados de 168 horas por origen. El resultado en horas altas admite tanto una mejora como un empeoramiento. En #88 ya figuraban los 17 927 orígenes del archivo y 159 de los 168 recientes. Esta comparación aporta un diagnóstico retrospectivo sobre datos previamente utilizados. [Puntaje reciente](../../metadata/campo-marte-inmediato-v1/reciente.json) · [Archivo](../../metadata/campo-marte-inmediato-v1/archivo.json) · [Intersección con #88](../../metadata/campo-marte-inmediato-v1/interseccion-88.json)

## Recalibración evaluada

Se registró un candidato después de conocer los resultados agregados del archivo y antes de ajustar sus intervalos. Por horizonte, se dividieron los pronósticos del bloque temprano en cuartiles y se estimaron los percentiles 10 y 90 del residuo en cada grupo. El corte del 1 de enero de 2026 separó 12 048 orígenes de calibración de 5 850 de comparación. Se purgaron 29 ventanas que cruzaban el corte con alguna hora de su historia u objetivo. [Protocolo](../../metadata/campo-marte-inmediato-v1/recalibracion/protocolo.json) · [Coeficientes del candidato](../../metadata/campo-marte-inmediato-v1/recalibracion/candidato.json)

Sobre las 35 100 comparaciones del bloque posterior, la cobertura pasó de 95,62 % a 83,78 % y la amplitud media de 27,90 a 15,08 µg/m³. En los 1 998 pares con objetivo alto, correspondientes a 346 horas distintas, la cobertura cayó de 53,35 % a 46,20 %. La diferencia pareada fue de −7,16 puntos porcentuales, con intervalo de confianza de 95 % de −13,32 a −3,83 puntos por remuestreo de bloques de 168 horas. Se descartó el candidato por incumplir la regla de conservar la cobertura en horas altas. [Comparación por horizonte y nivel pronosticado](../../metadata/campo-marte-inmediato-v1/recalibracion/comparacion.json)

## Decisión y operación

Persistencia queda como referencia principal. Qwen se emite en paralelo para observar su desempeño con datos que llegan después de emitir. La regla del diagnóstico requería menor MAE que persistencia y cobertura global entre 75 % y 85 % inclusive en la semana reciente. El exceso de cobertura dejó a Qwen fuera de ese rango. Cada emisión usa el calibrador original. El temporizador de bm quedó programado hasta el 22 de noviembre a las 23:09 UTC. La emisión y el primer recibo de cada objetivo tienen marcas UTC propias. SENAMHI describe los valores del gráfico como datos crudos sin control de calidad. La correspondencia entre la hora nativa del gráfico y UTC sigue abierta. La utilidad para anticipar episodios o emitir mensajes a la población requiere otras verificaciones. La semana independiente del 24 al 30 conserva su cierre el 2 de diciembre a las 19:00 UTC. [Gráfico de SENAMHI](https://www.senamhi.gob.pe/site/sea/www/site/sea/graficas/esta_conta.php?estacion=112194&conta=N_PM25) · [Evidencia de la fuente](https://github.com/keneth-arias/airaware/issues/43#issuecomment-7049518923) · [Protocolo de la semana independiente](prueba-futura-campo-marte.md)

## Reproducción en bm

Desde la raíz de esta revisión, con los archivos de adquisición y predicción ya guardados en bm, se pueden reconstruir las cohortes y comprobar los resultados por horizonte y estrato, las horas distintas, la intersección con #88, los cuartiles, las diferencias pareadas de cobertura y amplitud y la decisión del candidato. Para la primera emisión se cotejan el recibo de SENAMHI, la identidad de la corrida y las seis predicciones con sus intervalos contra el archivo privado de bm. La comprobación usa CPU y archivos locales. Los resúmenes bajo `metadata/campo-marte-inmediato-v1/` permiten comprobar los vínculos de huellas en otra máquina.

```bash
D=/home/shared/github/keneth-arias/airaware/data
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python \
  tools/timenet-smoke/verify_campo_replay.py "$D"
```
