# #14 · Identidad provisional y depuración horaria de SENAMHI

La primera entrega de Keneth aplica la política de pronóstico retrospectivo a SENAMHI en Lima.
El [ADR-005](../docs/decisions/005-senamhi-operating-policy.md) fija el alcance y
[el informe de #13](../reports/senamhi-normalization.md) documenta el insumo.

## Ejecutar y consultar

```bash
uv run --locked airaware curate senamhi \
  --input data/normalized/senamhi/senamhi-normalization-20261117-v1 \
  --output data/curated/senamhi-lima-audit.parquet
```

El comando verifica los archivos y rechazos del manifiesto de #13 antes de leer Parquet.
Publica un archivo local nuevo, con una fila por observación normalizada. Para #15, filtrar
`parameter_raw = 'PM2_5'` y consultar `decision = 'kept'` para recuperar el valor admisible.
Las otras decisiones permiten identificar horas observadas con datos faltantes o en conflicto.
Los registros rechazados por la normalización se consultan en su propia traza.

## Identidad y precedencia

- `station_key` es la suma SHA-256 del ID de fuente seguido de la lista JSON ordenada de
  estación, longitud, latitud, altitud, departamento, provincia y distrito originales.
  Reutiliza los mismos campos y el mismo orden de `comparison-v3`. Un cambio en cualquiera de
  estos campos abre otra identidad provisional. Confirmar una reubicación o cambio de
  instrumento requiere documentación fechada. El nombre y la proximidad por sí solos no
  justifican una fusión.
- La precedencia se aplica por identidad, instrumento, señal, unidad e intervalo. Dentro de
  ese grupo se usa la etiqueta `observed_at` en tiempo universal coordinado (UTC) sin
  desplazarla. Un valor finito inequívoco conserva `kept`. Las repeticiones numéricamente
  iguales conservan `duplicate` y apuntan a la observación con el menor número de registro
  admisible. Valores finitos distintos quedan como `conflict` sin observación seleccionada.
- Un valor ausente, censurado, no interpretable o no finito lleva `unusable_value`. Un valor
  ausente y una lectura válida pueden coexistir en una hora. El cero medido se conserva.
  Quedan registradas por separado una identidad desconocida, una hora desalineada y una fila
  fuera de Lima. Cada fila conserva su identificador y procedencia, incluidos el hash del
  original y el número de registro, para consultar las evidencias de unidad y los campos
  crudos en #13.
- Para agregar otra fuente, documentar el proveedor original y el solapamiento por estación,
  intervalo, señal, instrumento y unidad. Una copia demostrada de un agregador cede
  precedencia al registro original y conserva su vínculo. Mediciones independientes se
  mantienen en series distintas. Las equivalencias entre fuentes quedan pendientes de
  evidencia institucional o del estudio de OpenAQ en #31.

## Verificación local

Entrada verificada en `/tmp/airaware-pr71-data.aXl3c7/normalized`, con SHA-256 del manifiesto
`fcb427601777342217bad48518cdcd386f91fde7792799a5dfb622e201ad32fb`. Se ejecutó dos veces
el comando con salidas nuevas. Ambas generaron el mismo SHA-256
`86170e033b81bd6b53fdf0b044df3df36243ae2c4819a41821ecb839c13ee661`. La ejecución medida
duró 2,88 segundos con 2 383 228 KiB de memoria residente máxima en este equipo.

| Señal | Conservadas | Repeticiones | Conflictos | Valores no utilizables |
| --- | ---: | ---: | ---: | ---: |
| PM2.5 | 367 518 | 3 | 70 | 210 203 |
| PM10 | 380 909 | 3 | 70 | 196 812 |
| NO2 | 299 125 | 3 | 64 | 278 602 |

Las 1 733 382 filas concilian con #13 y los conteos de PM2.5 coinciden con `comparison-v3`
en las siete identidades provisionales. En el original, los registros 330116, 330117, 330120 y
330121 de San Borja publican 50,29 µg/m³ a las 00:00 UTC del 30/05/2024. La auditoría conserva
el 330116 y vincula los otros tres a su identificador. El número de registro incluye el
encabezado como registro 1.

`make check` pasó con 341 pruebas en Python 3.13.13. La suite también pasó con Python 3.11.
`make build` generó ambas distribuciones y `make audit` reportó cero vulnerabilidades conocidas.
