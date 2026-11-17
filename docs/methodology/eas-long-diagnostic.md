# Diagnóstico reproducible de EAS largo (#11)

Ejecutar sobre el original local conservado (no descarga ni conversión de producción):

```bash
uv run --locked python -m airaware.eas_review \
  --input data/raw/oefa-eas-aire-local/EAS_Aire_0.csv \
  --output reports/generated/eas-long/una-carpeta-nueva
```

La herramienta procesa todas las filas con DuckDB fijado en uv.lock, un hilo, 1 GB de memoria
operativa y hasta 16 GB de desborde temporal en disco. Rechaza CSV malformados y salidas existentes
o ubicadas dentro de la carpeta de entrada. Publica la carpeta al terminar, verifica SHA antes/después
y registra hashes de salidas; no modifica originales ni descarga extensiones.

## Interpretación conservadora

Las fechas de cinco dígitos se prueban como seriales Excel 1900, **sin confirmar esa época**.
Los instantes calculados son reloj hipotético sin zona, separados del contrato Observation de #12.
No se introduce ese reloj en start/end ni se habilita elegibilidad, entrenamiento o etiquetado.
Un acierto de formato no equivale a interpretación institucional acreditada.

El vocabulario PM usa etiquetas explícitas de concentración total, no metales ni pesos de filtro.
«25 micras» se conserva ambiguo; el inventario publica todas las etiquetas/unidades/periodos,
incluso las no reconocidas. Unidades equivalentes solo se agrupan en la selección diagnóstica;
series distintas conservan la unidad original en su identidad, sin conversiones ni mezcla.

Las series incluyen informe/evaluación, ubicación original, muestra, etapa, análisis, parámetro,
unidad y periodo. Solo se cuentan puntos con periodo literal 1 hora, hora alineada, valor finito
inequívoco y sin fin declarado. Los intervalos con fin declarado se excluyen conservadoramente
hasta agregar interpretación verificada de ambas fechas/horas. Las filas permanecen contabilizadas.
Repeticiones idénticas se colapsan solo para el conteo; conflictos, censura y códigos desconocidos
impiden admitir el punto. No rellenar horas ni concatenar campañas. La prueba de Lima es una
mención textual, no una homologación administrativa; no sirve para declarar ubicación confirmada.

## Salidas y trazabilidad

- summary.json: conteos de valor, vocabulario completo, cobertura y las 16 parejas H/F por serie.
- points.parquet: puntos diagnósticos únicos; identities.parquet identifica sus contextos.
- row-diagnostics.parquet: número de registro lógico CSV (encabezado=1), serie y estado para etiquetas
  PM reconocidas o ambiguas. Las demás filas se contabilizan en el resumen y permanecen en el original.
- manifest.json: SHA de entrada y salidas. Registrar el SHA del código en el recibo de ejecución.

Todas las ventanas son estructurales hipotéticas; scientific_valid_windows es nulo. La ausencia
de ventanas bajo estas reglas no demuestra ausencia histórica de mediciones. Keneth retiró la cuota
de estaciones/meses el 17/11/2026; medir cobertura real sin imputar ni adoptar automáticamente EAF.

## Evidencia pendiente

Contrastar registros concretos con informes originales para época, zona y posición del intervalo;
confirmar calidad, códigos y atribución por recurso. Las consultas SENAMHI #43 y OEFA ya enviadas
no se reenvían automáticamente. Un resultado hipotético prometedor sirve para priorizar esas
verificaciones, no para declararlas resueltas. Después: ajustar solo reglas sustentadas, repetir
comparación #11 y continuar #13/#14/#18. #20 mantiene la integración pendiente.
