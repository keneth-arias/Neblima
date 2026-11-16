# Plan revisado de #11: comparación con evidencia y selección condicionada

Responsable: Keneth. Propuesta del 16/11/2026, pendiente de feedback antes de implementar.
Seguimiento: issue #11; dependencias #9/#10 cerradas, PR #57/#58 integrados en main.
Se conserva el alcance original: ventanas, puntuación y comparación/solapamientos reales.

## Insumos actuales

Reutilizar configs/profiling.json, metadata/profiling-run.json y los originales/manifiestos de #8/#9.
Comprobar hashes y versión raw-profile-v2; no volver a descargar los CSV. Los agregados Parquet
no bastan para contar ventanas: leer los instantes originales y reconstruir puntos comparables.
SENAMHI: 577 794 filas, siete grupos en Lima, 2015–2024, con huecos/conflictos.
OEFA: 2 883 877 filas, 38 grupos provisionales y 353 contextos por señal. Los dos contextos
con PM2.5 horario admisible son CA-HUA-01 y CA-MAC-01, ambos Piura. Ninguna celda PM2.5/PM10
finita de los grupos etiquetados LIMA/CALLAO tiene inicio interpretable por el parser actual.
No equivale a ausencia de mediciones ni prueba que no puedan recuperarse con documentación.
Investigación y consultas: docs/sources/oefa-consultation-research.md.

## Contrato propuesto y decisiones de Keneth

- Objetivo inicial propuesto: PM2.5 horaria univariada; PM10 como escenario separado. No elegir
  automáticamente el mejor resultado entre objetivos. Confirmar PM2.5 antes de fijar benchmark.yaml.
- Geografía principal: provincia LIMA, no todo el departamento LIMA. Proponer CALLAO como escenario
  adicional separado, pendiente de decisión; no ampliar a Piura para alcanzar una cuota de estaciones.
- Grilla: una hora, sin imputación; series por identidad provisional y contexto de #10. Los negativos
  y extremos no se eliminan por una regla estadística sin fundamento. No mezclar periodos/unidades.
- Para origen t, historia [t−(H−1)h,t] y objetivo [t+1h,t+Fh]. Evaluar las 16 parejas
  H=24/48/72/168 y F=6/12/24/48; cada celda requerida debe tener un valor finito inequívoco.
  No elegir H/F por desempeño del conjunto de prueba. Coordinar contrato con #18 sin cambiar su rama.
- Separar conteos estructurales en reloj original de ventanas científicamente válidas. Unidades,
  zona/instante del intervalo, calidad y derechos sin resolver generan estado bloqueado, no aprobación
  ni conteos presentados como ventanas válidas. Si no se puede determinar, usar nulo con motivo.
- Cuatro estaciones y 24 meses son metas, no hechos ni umbrales que se relajen silenciosamente.
  Medir continuidad, periodo común y ventanas; cualquier cambio de alcance requiere justificación y feedback.

## Incrementos pequeños, secuenciales

1. Contrato/configuración y pruebas de ventanas (3–5 archivos).
   Campos: hash de entrada, fuente, estación/contexto, señal, geografía, H/F, estado semántico,
   candidatos, pérdidas por filtro y conteos finales. Fijar versión de política y orden de filtros.
   Pruebas primero: orden invertido, límites inclusivos, huecos, valores ausentes, conflictos,
   cambio de contexto, mismas horas en estaciones diferentes, cero ventanas y semántica desconocida.
   Aceptación: fixture conocido produce conteos manualmente verificables para las 16 parejas.
2. Ejecución de conteos y trazas reales (3–5 archivos).
   Filtrar por fuente/contexto/geografía y reportar descartes disjuntos en orden fijo: fuera del ámbito,
   contexto/periodo no comparable, reloj no interpretable/no alineado, celda no finita o ambigua,
   historia incompleta, objetivo incompleto. Contar pérdidas de filas y ventanas por separado;
   la suma debe reconciliar con el universo de cada etapa. No sumar filtros superpuestos.
   Consolidar repeticiones idénticas solo en una vista diagnóstica trazable; originales intactos.
   Publicar forecasting-readiness.parquet bajo reports/generated/, no dentro de Git.
   Aceptación: ambas fuentes reportadas, con ceros medidos y nulos/bloqueos diferenciados.
3. Comparación, solapamiento y selección (3–5 archivos).
   Proponer puntuación entre candidatos elegibles, escala 0–1 y pesos: 35% ventanas completas,
   25% continuidad, 15% estaciones, 15% extensión temporal, 10% trazabilidad/validación.
   Definir fórmulas y denominadores en configuración ANTES de calcular; no normalizar respecto al
   mejor candidato observado. Análisis de sensibilidad con alternativas documentadas, sin usar objetivos
   reservados de prueba. Un bloqueo de derechos o significado excluye antes de puntuar y no recibe cero.
   Medir solapamiento por instantes comparables por señal/contexto; sin relojes compatibles, nulo.
   No homologar estaciones entre redes (#14) ni convertir UTM por intuición.
   Aceptación: informe dataset-comparison.md y source-overlap.parquet local, decisión justificada o
   selección explícitamente pendiente por respuesta institucional. No cerrar #11 sin selección defendible.

## Verificación y entrega

En cada incremento: pruebas sin red y sin originales masivos en CI; make check/build/audit.
Al final: verificación SHA de entradas, resultados reales con política fijada, sumas de pérdidas,
pruebas 3.11/3.13 y revisión. No usar datos futuros para rellenar historias o ajustar criterios.
Los conteos no crean splits (#19), ventanas de entrenamiento (#18) ni etiquetas (#20).

## Investigación externa y decisiones pendientes

Nueva ficha EAS de OEFA declara cobertura hasta junio 2024; tabla no cargada, estructura/horas/licencia
por recurso sin verificar. No descargar masivamente ni sustituir silenciosamente el CSV.
Consulta preparada para Enrique Manco, contacto publicado del conjunto. Envío pendiente de instrucción
expresa; no se ha enviado. Pedir orientación hacia DEAM y archivos/metadata existentes, no presumir
asesoría disponible ni pedir que OEFA genere una base nueva. La respuesta puede resolver reglas de
horas, calidad y acceso; su ausencia no bloquea contratos/pruebas ni conteos diagnósticos.

Feedback solicitado: PM2.5 como objetivo inicial; Lima provincia como ámbito principal con Callao
separado; política estricta sin imputación; pesos propuestos; autorización para enviar la consulta.
