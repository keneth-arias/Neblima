# Adquisición reproducible SENAMHI Lima (#8)

Se ejecutó el plan aprobado reutilizando originales de #3/#4 y manifiestos de #6/#7.
Evidencia fechada: metadata/senamhi-acquisition-check.json. Plan portable:
configs/acquisition/senamhi-local.json. Ejecutar desde la raíz de cada copia que tenga los archivos.

## Resultado comprobado

Seis originales conservan tamaño y SHA-256 históricos: CSV, XLSX, DOCX y tres PDF documentales.
CSV: 68 501 558 bytes, SHA-256 896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4.
No se copiaron ni descargaron otra vez. Los tres PDF conservan los manifiestos documentales de #4;
no se hicieron pasar por formatos admitidos del importador.

Para CSV/XLSX/DOCX, dos ejecuciones de acquire batch terminaron sin errores, con reused=true en
los tres recursos y network_bytes=0. Se compararon otra vez las sumas de los seis originales y de
los tres manifiestos previos después de cada ejecución; todos permanecen idénticos.
Las rutas del informe son relativas; la fecha de comprobación no sustituye la fecha de descarga.

## Reproducción local

```bash
uv run --locked airaware acquire batch --plan configs/acquisition/senamhi-local.json --dry-run
uv run --locked airaware acquire batch --plan configs/acquisition/senamhi-local.json --offline --budget-bytes 0
uv run --locked airaware acquire batch --plan configs/acquisition/senamhi-local.json --offline --budget-bytes 0
```

No usar --data-dir/AIRAWARE_DATA_DIR para asumir que los originales relativos se trasladan solos:
esas opciones eligen la carpeta de salida; local_file se resuelve desde la carpeta de ejecución.
En otra copia, preparar los originales con procedencia y verificar sus hashes, o generar un plan con
rutas reales y ajustar la carpeta base. Si faltan/cambian archivos, el comando falla sin descargarlos
ni sobrescribirlos. No se modificaron las carpetas ni entornos de Cristopher/Jordan.

## Handoff a #10 y límites

La entrada de perfilamiento es el CSV original, con diccionario/metadatos y los documentos de #4.
Los 577 794 registros/15 columnas son conteos estructurales históricos, no nuevas afirmaciones de
continuidad ni ventanas válidas. #10 debe informar huecos, conflictos y cobertura con trazas propias.
La adquisición no normaliza ni convierte unidades/reloj/CRS, no imputa y no publica datos. #43 mantiene
las aclaraciones de semántica y alcance de derechos. ODC-BY-1.0 documenta la base; no cambia a AGPL
por la licencia del código. El catálogo conserva esas incertidumbres.

Verificación de entrega: make check aprobado (146 pruebas y controles estáticos), make build aprobado
y make audit sin vulnerabilidades conocidas. No se modificó lógica ni se agregaron dependencias.
