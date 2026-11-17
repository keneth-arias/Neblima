# Adquisición local de EAS_Aire_0.csv — alternativa OEFA para #11

Verificación del 17/11/2026 UTC. Recurso solicitado por Keneth:
[Evaluaciones ambientales de seguimiento (EAS)](https://www.datosabiertos.gob.pe/dataset/evaluaciones-ambientales-de-seguimiento-eas),
[CSV EAS_Aire_0.csv](https://www.datosabiertos.gob.pe/sites/default/files/EAS_Aire_0.csv).

## Procedencia y conservación

Lightpanda abrió la ficha y el [recurso](https://www.datosabiertos.gob.pe/dataset/evaluaciones-ambientales-de-seguimiento-eas/resource/509ddd93-3e75-4735-8fb8-cf03ebc7c325).
Dos entradas del catálogo apuntan a la misma URL: se registra una fuente, no dos conjuntos.
El catálogo muestra 4,8 GB, actualización de la información hasta junio 2024 y licencia ODC-By;
esto no prueba cobertura temporal efectiva, calidad, ni autoriza por sí solo publicación de datos.

Dos intentos de descarga Lightpanda agotaron el plazo. El descargador HTTP acotado no completó
la adquisición; una sonda de diagnóstico confirmó HTTP 418 y se detuvo ese canal. Una navegación
con Lightpanda CLI local también agotó el plazo; no llegó a transferir el CSV. No se cambiaron
identidades del navegador ni se eludió la respuesta HTTP. No hay un código HTTP exitoso del archivo
que atribuir a esas operaciones. Después Keneth descargó el archivo y lo proporcionó localmente.

Se mantuvo su copia `/home/shared/github/keneth-arias/EAS_Aire_0.csv` sin modificar. Se guardó una
copia de bytes idénticos en `data/raw/oefa-eas-aire-local/EAS_Aire_0.csv`; se comprobó SHA-256 antes
de publicar ese nombre. El motor existente validó el CSV completo y registró una referencia local:

- Fuente independiente: `oefa-eas-aire`; no reemplaza `oefa-csv` ni se mezcla con el CSV ancho anterior.
- Método de adquisición: `local`, archivo proporcionado por el usuario; no una descarga exitosa del agente.
- Tamaño real: **5 153 626 505 bytes**.
- SHA-256: `81b219665c12cd1f2e72fa5c93deb6ffd3255fd73465bc02e38b087deda66d6a`.
- CSV: UTF-8, delimitador coma, **23 columnas y 11 407 394 filas** de datos.
- Manifiesto: `data/raw/oefa-eas-aire/81b219665c12cd1f2e72fa5c93deb6ffd3255fd73465bc02e38b087deda66d6a/manifest.json`.

No se dispone de un checksum publicado por OEFA para autenticar los bytes contra el servidor;
la suma identifica y preserva la copia proporcionada. No se cambia su procedencia a Lightpanda.

## Inspección estructural inicial

Esta versión es una tabla larga con campos `Parámetro`, `Valor` y `Unidad.de.medida` por fila,
además de evaluación, informe, punto, coordenadas, periodo y fechas/horas de inicio/fin.
La lectura estricta completa con DuckDB confirmó el mismo conteo, sin omitir filas defectuosas.
Hay 81 etiquetas de parámetro, 129 códigos de informe y 151 nombres de puntos. Se observan 171
combinaciones de nombre/Este/Norte/Zona/Datum; no equivalen a 171 estaciones homologadas permanentes.
8 535 307 filas tienen Valor numérico finito; las demás requieren clasificar los tokens, no convertirlos a cero.

Todas las fechas de inicio tienen cinco dígitos enteros, de 43101 a 45657. Son compatibles con seriales
de hoja de cálculo. **Si** se adopta la época 1899-12-30, sus extremos serían 2018-01-01 y 2024-12-31;
se registra como hipótesis diagnóstica, sin confirmar época ni convertir datos de producción.
No equiparar estos extremos automáticamente con la cobertura de junio 2024 anunciada en la ficha.

3 512 243 filas tienen Hora.inicio con forma HH:MM:SS estricta y 422 tienen un marcador faltante
entre los reconocidos en esta inspección. El resto no se clasifica como ausente: puede contener
otras representaciones que deberán inspeccionarse antes de fijar el parser. No se deduce zona horaria.

## Disponibilidad potencial en puntos conocidos de Lima

Coincidencia inicial por código de punto con #10 y descripción de Lurigancho/Lima; falta comprobar
identidad espacial/histórica. No se transforma esto en cobertura de toda Lima ni en ventanas válidas.
Para la etiqueta explícita de material particulado de 2,5 micras, unidad µg/m³ y periodo `1 hora`:

| Punto | Filas | Valores finitos con hora HH:MM:SS |
| --- | ---: | ---: |
| CA-HU-04 | 8 760 | 6 871 |
| CA-HU-09 | 8 761 | 4 461 |

Los seriales de estos grupos van de 44927 a 45291 (compatibles con 2023 bajo la hipótesis indicada).
Estos son valores por fila, no instantes únicos, series sin conflictos ni ventanas completas. No se
comprobó todavía la presencia de duplicados en estos grupos; 8 761 filas no prueban un año horario único.
Es evidencia prometedora frente al CSV anterior, que no tenía puntos PM horarios interpretables de Lima.

Otras etiquetas mezclan descripciones de «25 micras» con identificadores PM2,5/PM25. No corregirlas ni
unificarlas silenciosamente con PM2.5. También existen distintas representaciones de unidad y periodos
no horarios. El diccionario anterior de 36 columnas orienta conceptos, pero no documenta por sí solo
esta nueva exportación de 23 campos ni sus seriales.

## Archivos para el equipo y siguiente paso

- `configs/acquisition/oefa-eas-aire-local.json`: plan portable de reutilización sin red.
- `metadata/oefa-eas-aire-local.json`: evidencia pequeña, columnas, conteos, procedencia y hashes.
- Inspección local completa: ruta y SHA-256 de `structure.json` en el registro anterior. Permanece bajo
  `reports/generated/oefa-eas-aire/`, fuera de Git, junto con los originales masivos ignorados.

Para comprobar la copia disponible en la carpeta de datos, ejecutar desde la raíz:

```bash
uv run --locked airaware acquire batch --plan configs/acquisition/oefa-eas-aire-local.json --budget-bytes 5153626505 --offline
```

La configuración no incluye los bytes en Git. Cada integrante debe disponer de su copia local y
manifiesto o importarla con el plan bajo la carpeta de datos acordada.

Próximo trabajo de #11: contrato específico de formato largo; fechas seriales y representaciones de
hora; identidad/contexto; correspondencia de parámetros/unidades; duplicados/conflictos y conteos
estrictos de ventanas en Lima. El parser ancho actual debe seguir rechazando esta entrada incompatible.
No se modifica benchmark.yaml, ni se promueve este recurso a scientifically ready, ni se publican sus
mediciones. El estado del catálogo es downloaded, no integrated ni benchmark seleccionado.

## Validación de la entrega

El comando offline anterior completó la reutilización verificada, sin errores y con cero bytes de red.
Pasaron make check (223 pruebas, formato, tipos y catálogo), las 223 pruebas en Python 3.11,
make build y make audit (sin vulnerabilidades conocidas). El catálogo registra 38 recursos, cinco
con originales disponibles. La nueva prueba verifica procedencia local y separación de formato/fuente,
sin requerir el CSV masivo en CI.
