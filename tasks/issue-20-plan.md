# Plan de #20: etiquetas de episodios PM2.5

Responsable: Keneth. Investigación y módulo independiente autorizados por el usuario.
Se aplican planificación, implementación incremental y pruebas antes de código.

## Alcance y dependencias

#18 está cerrada: su constructor de ventanas reales existe y se verificó contra una ejecución
local. #20 integra ese paquete sin modificarlo. No asumir unidades, reloj ni validación de
calidad en los datos SENAMHI (#43); la elegibilidad de etiquetas reales sigue cerrada.
Decisión explícita de Keneth: mantener #20 abierta hasta acreditar la semántica del intervalo
y la calidad individual, no solo la correspondencia estructural.
No cambiar tareas/ramas de Cristopher ni el constructor de #18.

## Entregas

1. Verificar fuentes oficiales: DS 003-2017-MINAM, anexo (PM2.5 24 h, anual y frecuencia),
   DS 010-2019-MINAM, anexo 1 c.i/c.iii (día y suficiencia automática/manual).
   Evidencia local inmutable y sumas; archivos normativos fuera de Git.
2. Definir dos etiquetas independientes con contrato de entradas explícito: ventana futura de 24 h
   con 24 objetivos medidos válidos; día calendario de referencia con mínimo 18 horas automáticas.
   Sin afirmar cumplimiento legal anual ni ausencia de riesgo. No redondear antes de comparar.
3. Pruebas primero: igualdad/encima/debajo de 50, 17/18/23/24 válidos, negativos/no finitos,
   calidad inválida, duplicados, husos equivalentes, medianoche final, ventana móvil no diaria,
   unidades/semántica no sustentadas y conservación de IDs de observación.
4. Implementar módulo puro y configuración versionada; documentar límites y ejemplo reproducible.
   Separar resultado no evaluable de resultado no superior al umbral.
5. Revisar corrección, interfaces, seguridad y memoria. make check, build y audit; compatibilidad 3.11.
   PR con evidencia; no cerrar la emisión de etiquetas reales usando solo datos sintéticos.

## Investigación y decisiones

Revisión: 16/11/2026 UTC. SINIA/MINAM: páginas con navegación fallida, PDF bloqueados por robots
con Lightpanda. Alternativa oficial Gob.pe: catálogo MINAM 3670-003-2017-minam y catálogo MINEM
4773310-010-2019-minam; descargas CDN mediante Lightpanda, no fallback HTTP silencioso.
Protocolo inspeccionado en PDF página 93 (numeración impresa 90), anexo 1 c.i; umbrales en PDF
página 4 del DS 003-2017 (impresa 9). Anexo: 50 µg/m³ en 24 h, 25 anual, no más de 7
excedencias por año para el criterio diario. El módulo no evalúa el criterio anual.
Método automático: mínimo 18 horas válidas por día y promedios terminados 01:00 a 00:00 siguiente.
Método manual: muestra de 24 h con mínimo 22 h; no aplicar 18 de 24 a filtros gravimétricos.
El 100 % de objetivos de pronóstico es política de #18, independiente de suficiencia normativa.

## Integración estructural verificada (18/11/2026)

El adaptador `airaware.senamhi_event_labels` y la CLI `airaware labels senamhi` verifican el
manifiesto y el SHA-256 de la grilla y de las ventanas, el vínculo `input_sha256`, la frecuencia
horaria y el horizonte. Reconstruyen cada objetivo por `series_id` y límites exactos
(`origin_at + 1 h` a `origin_at + 24 h`, ambos inclusive), comprueban estación, horas únicas,
valores medidos y promedio, y concilian candidatos/ventanas con los conteos manifiestos. Solo
`horizon_hours == 24` admite `forecast_24h`; otros horizontes se informan incompatibles.

Ejecución local sin red, desde el original ya verificado (SHA-256
`896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4`), con política
`senamhi-normalization-20261117-v1`:

| Etapa | SHA-256 de salida |
| --- | --- |
| Auditoría de curatoría | `86170e033b81bd6b53fdf0b044df3df36243ae2c4819a41821ecb839c13ee661` |
| Grilla horaria | `2e8fa784cea645b8eb97b42f3fe36e6c532b5959cc8ae66da0ea416df513413c` |
| Ventanas 24/24 paso 1 | `39abf1656905144a61c310f6acde356f7f75eb859846dd6164496b5bc24e39d8` |

Las ventanas 24/24 suman 574 868 candidatos: 324 463 completos, 230 437 sin historia completa
y 19 968 sin objetivo completo. La inspección reconstruyó las 324 463 ventanas y
7 787 112/7 787 112 horas objetivo medidas en siete series; los conteos por serie coinciden con
el manifiesto y la repetición produjo bytes idénticos. Detalle en
`metadata/issue-20-label-integration.json`.

La etiqueta real sigue bloqueada: no existe evidencia explícita de posición del intervalo y la
calidad publicada es `unknown`. Sin archivo de evidencia el informe registra
`labeling_evidence_missing`; con una evidencia sintética de prueba, el bloqueo pasa a
`quality_values_not_admissible`. En ambos casos se publica solo `compatibility.json` y
`manifest.json`, sin `labels.parquet` ni valores `quality_valid=True` para datos reales.

## Avance y revisión de entrega

- [x] Investigación de fuentes primarias, páginas/tablas inspeccionadas y manifiesto de archivos locales.
- [x] Contrato y configuración versionados para PM2.5, sin nuevas dependencias de ejecución.
- [x] 29 pruebas enfocadas de reglas, integridad, fechas, calidad y procedencia.
- [x] make check: 175 pruebas y controles estáticos aprobados; Python 3.11: 175 aprobadas.
- [x] make build: sdist y wheel generados. make audit: sin vulnerabilidades conocidas.
- [x] Revisión local: reglas normativas contrastadas, biblioteca pura acotada a 24 registros,
  tipos explícitos, sin lectura de datos reales ni modificación del constructor/ramas de Cristopher.
- [x] Integrar con el constructor real de #18: correspondencia temporal, estación y promedio
  reconstruidos en 324 463 ventanas h24/f24 reales.
- [x] Probar con objetivos medidos y sin imputación: 7 787 112 horas objetivo, descartes de
  historia/objetivo contabilizados y conteos conciliados.
- [ ] Acreditar posición del intervalo y calidad individual para emitir etiquetas reales
  (ADR-005/#43); la completitud estructural no sustituye esa evidencia.

No se declara cumplimiento legal anual ni se etiqueta concentración como libre de riesgo.
Cambiar la referencia de 2017 o relajar suficiencia exige una versión de política revisada.
La implementación no recibe historias ni crea entradas de modelos: #18 conserva esa responsabilidad.
La integración estructural con datos reales está verificada; la emisión de etiquetas reales no.

El benchmark principal 24/6 no es un conjunto de etiquetas de episodios: un objetivo de seis horas
no puede recibir `forecast_24h`. Solo ventanas con horizonte de 24 h y evidencia semántica
admitida podrían etiquetarse. La etiqueta diaria regulatoria sigue diferida por ADR-005; #26 no
debe usar etiquetas no sustentadas. Ver la [ruta de evaluación](plan.md).
