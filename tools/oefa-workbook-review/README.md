# Revisión de los cuatro libros de aire OEFA

Herramienta de investigación de #11, independiente del importador genérico. Lee los XLSX conocidos
por streaming, verifica sus hashes antes/después y conserva trazabilidad por fuente/hoja/fila.
No escribe los originales, no evalúa fórmulas, no relaja los límites Office de producción ni
reemplaza sus manifiestos. Las dependencias del lector se fijan en requirements.txt; DuckDB y las
funciones de ventanas provienen del proyecto y uv.lock. No se agrega openpyxl al paquete principal.

Desde la raíz, con los originales adquiridos en PR #64:

```bash
uv run --with-requirements tools/oefa-workbook-review/requirements.txt python -m unittest discover -s tools/oefa-workbook-review -p 'test_*.py'
uv run --with-requirements tools/oefa-workbook-review/requirements.txt python tools/oefa-workbook-review/analyze.py --output reports/generated/oefa-workbooks/nueva-ejecucion
```

La carpeta de salida debe ser nueva y estar fuera de raw. La instalación inicial de las dependencias
puede requerir internet; el análisis y sus pruebas no consultan fuentes externas. Cada integrante usa
sus propios archivos y rutas del recibo; los libros masivos no vienen con Git.

## Contrato de investigación

- Fecha: interpreta celdas nativas y seriales enteros usando la época declarada en el libro. Las fechas
  de texto ambiguas D/M frente a M/D quedan sin interpretar. No se asigna zona horaria.
- Hora: acepta time nativo, HH:MM[:SS], fracciones Excel dentro de un día y fechas base explícitas.
  No convierte duraciones de varios días ni fechas sin hora en un reloj válido. Conflictos entre la
  hora de una fecha datetime y Hora inicio se conservan sin resolver.
- Valor: distingue finito, censurado, marcador ausente, no finito, token no interpretado, fórmula y
  error Excel. Textos de minerales o puntos cardinales pueden ser categorías válidas; no se etiquetan
  todos los tokens no numéricos como errores. No se reemplaza censura por cero ni se imputan horas.
- PM: solo etiquetas explícitas de concentración de partículas se agrupan como candidatas PM10/PM2.5.
  Metales en PM10 y pesos de filtros conservan una familia distinta, aunque su etiqueta contenga PM.
- Series: contexto de informe/evaluación, punto/coordenadas, etapa, muestra, análisis, caracterización,
  periodo, parámetro y unidad. No se unen campañas por compartir nombre de estación.
- Repeticiones: son campos decodificados por el lector iguales, no igualdad byte a byte del XLSX.
  Las copias adicionales y los conflictos se cuentan; no se eliminan registros originales.
- Puntos horarios: periodo exactamente 1 hora (tras minúsculas/espacios), inicio alineado, intervalo
  único, valor finito inequívoco y sin celdas censuradas/ausentes en ese mismo grupo; si el fin es
  interpretable, debe corresponder a 3600 s. Un fin ausente se mantiene como tal, no se fabrica.
- Ventanas: reutiliza el conteo de #11 para 16 parejas H/F; todas son diagnósticas. La cifra de ventanas
  científicamente válidas permanece nula por reloj, calidad, geografía y derechos pendientes.
- Lima/Callao: se guardan menciones textuales como candidatas. No sustituyen un filtro geográfico
  validado ni una homologación. El límite de palabra evita confundir «climático» con «Lima».

## Evidencia generada

observations.parquet conserva valores interpretados y raw_values_json tipado con el número de fila.
Los bytes originales siguen en XLSX. tokens.parquet y summary.json contienen los perfiles y contextos;
manifest.json registra entradas y hashes de salida. Todo permanece bajo reports/generated/, fuera de Git.
Los resúmenes pequeños y la interpretación se publican en reports/oefa-workbook-analysis.md.

Se comprueban el CRC, macros/cifrado y el total descomprimido de hasta 256 MiB de estos archivos
conocidos antes de leer. Es un alcance explícito de investigación, no una ampliación del importador
genérico (8 MiB por miembro / 32 MiB total). El lector utiliza defusedxml en este entorno fijado.

Referencias oficiales: [lectura read-only](https://openpyxl.readthedocs.io/en/stable/optimized.html),
[fechas/épocas y ausencia de zona en Excel](https://openpyxl.readthedocs.io/en/stable/datetime.html).
