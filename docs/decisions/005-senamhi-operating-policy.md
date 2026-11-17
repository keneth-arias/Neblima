# ADR-005: SENAMHI como base inicial de pronóstico bajo política operativa

Estado: aprobado por Keneth el 17/11/2026, por aceptación explícita en la conversación del proyecto.
Ref: #11; configura comparison-v3. Esta aprobación no es una respuesta institucional de SENAMHI.

## Decisión y alcance

Seleccionar senamhi-lima-csv, objetivo PM2.5, geografía Lima y SHA
896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4 como base inicial de pronóstico.
Utilizar el timestamp publicado como etiqueta horaria UTC, sin trasladarlo una hora ni inventar
extremos del intervalo. Se aceptan calidad individual desconocida y posición inicio/fin desconocida
para este uso. Se preservan observed_at, originales, inferencias de unidad y evidencia de aprobación.
La licencia ODC-BY-1.0 y atribución están documentadas; unidades ug/m3 inferidas fueron aceptadas.
No se exigen estaciones fijas ni meses continuos mínimos y no se imputa para aumentar cobertura.

## Reglas de admisión

- Contar por identidad provisional/contexto y señal; no concatenar estaciones ni campañas.
- Admitir horas alineadas con valor finito inequívoco. Consolidar repeticiones idénticas solo en
  vista derivada; conservar todas las filas de origen y sus identificadores.
- Valores ausentes/no finitos y conflictos de valor no proporcionan una medición admisible.
  Una repetición vacía no invalida otra lectura finita inequívoca de la misma señal, según #10/#11.
- Exigir historia y objetivos completos por hora para cada pareja H/F. No rellenar huecos ni
  escoger H/F por desempeño del conjunto de prueba. No imponer umbrales estadísticos de extremos
  sin fundamento; la calidad desconocida nunca se convierte en quality=valid.
- Usar orden cronológico de etiquetas publicadas y separar particiones evitando solapamientos.
  No afirmar disponibilidad en tiempo real: available_at permanece desconocido. La evaluación es
  retrospectiva; covariables externas requieren confirmar intervalos y disponibilidad antes de alinearlas.

## Diferenciar aceptación operativa y validación científica

accepted_forecasting_windows contiene el conteo admitido por esta política en el escenario
SENAMHI/Lima/PM2.5. scientific_valid_windows sigue nulo mientras no haya evidencia suficiente;
no renombrar aprobación del responsable como validación instrumental. Las preguntas de #43 siguen
abiertas, pero no bloquean seleccionar la base ni normalizar #13 y preparar pronóstico #18.
Los bloqueos de otras fuentes o usos no se eliminan y la aprobación no se transfiere a otro SHA.

**Se difieren etiquetas regulatorias diarias** hasta establecer la posición del intervalo y reglas
adecuadas de calidad. daily_regulatory_labels=false. El módulo puro de #20 puede conservarse,
pero no se aplica al conjunto real por cerrar #11. #20 sigue abierto hasta integración verificada
con #18 y metadatos compatibles con su uso. Agregados exploratorios diarios conservan ese carácter.

## Consecuencias y entregas posteriores

#11 queda completo al integrar esta decisión y su comparación verificada. #13 sigue siendo el
normalizador Parquet de qriqs; #14 resuelve identidad; #15/#18 generan series/ventanas; #19 fija
particiones, y #21/#22 exportan. No se afirma que esos entregables estén construidos por seleccionar
la fuente. #43 incorpora aclaraciones posteriores por nueva versión sin modificar evidencia vieja.
