# Verificación real de la metodología de etiquetas de episodios (#20)

Fecha de ejecución: 20 de noviembre de 2026, 22:48–22:49 UTC. Responsable de esta corrida:
Cristopher (@qriqs). Commit base: `4dd2244` (main, incluye la corrección del verificador del
PR #113: límites horarios exactos, una etiqueta por ventana y conciliación con series totalmente
descartadas). Informe complementario: `metadata/event-labels-real-20261120.json`.

## Alcance

Ejecución independiente de la metodología de `docs/methodology/event-labels.md` sobre el paquete
real de #13/#18 (grilla horaria y ventanas H24/F24 reconstruidas desde el CSV histórico de
SENAMHI), tomado del árbol compartido de Keneth en modo solo lectura. La corrida usa
`evaluate_windows` de `src/airaware/senamhi_event_labels.py`, que integra `verify_no_label_leakage`
y la conciliación de descartes por serie con fail closed: cualquier descuadre detiene la entrega y
no se publica nada. No se ajustó ningún dato para que cuadre.

Las ventanas H24/F6 del paquete `lima-postcorte-20261118` y las tareas bivariadas de
`pm-bivariado-20261120` no se etiquetan: por la metodología, un paquete con horizonte 6 no admite
`forecast_24h` y se informa incompatible, nunca se rellena. Se verificó su integridad y se dejó
registrada; son insumos de la evaluación externa y de #88, no de esta verificación.

## Comando exacto

Ejecutado desde la raíz del checkout (`feat/issue-20-verificacion-real`, base `origin/main`):

```sh
UV_OFFLINE=true nice -n 10 /usr/bin/time -f 'Tiempo=%e s Memoria residente maxima=%M KiB' \
  uv run --locked airaware labels senamhi \
  --timeline /home/shared/github/keneth-arias/airaware/data/processed/lima-procedencia-20261120/timeline \
  --windows /home/shared/github/keneth-arias/airaware/data/processed/lima-procedencia-20261120/windows-24 \
  --output data/labels-real-20261120
```

Código de salida 0. Tiempo: 76,22 s; memoria residente máxima: 1 750 032 KiB. Sin GPU, sin red,
con `nice -n 10` por los entrenamientos en curso en el servidor compartido. El árbol compartido no
recibió ninguna escritura.

## Integridad de las entradas

| Entrada | Verificación | Resultado |
| --- | --- | --- |
| Grilla `lima-procedencia-20261120/timeline` | SHA-256 físico `2e8fa784cea645b8eb97b42f3fe36e6c532b5959cc8ae66da0ea416df513413c` vs `output_sha256` del manifiesto; `input_sha256` = `86170e033b81bd6b53fdf0b044df3df36243ae2c4819a41821ecb839c13ee661` (auditoría de curatoría); UTC y frecuencia 1 h | OK |
| Ventanas `lima-procedencia-20261120/windows-24` | SHA-256 físico `39abf1656905144a61c310f6acde356f7f75eb859846dd6164496b5bc24e39d8` vs `output_sha256`; `input_sha256` = SHA-256 de la grilla; H24/F24/paso 1 | OK |
| Paquete `lima-postcorte-20261118` | `sha256sum -c SHA256SUMS`: 17 de 17 archivos OK (incluye `ventanas-h24-f6.parquet`, `observaciones.parquet`, `contraste-reloj.csv`) | OK |
| Paquete `pm-bivariado-20261120` | `evidencia.json`: CSV histórico con SHA-256 `896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4` comprobado en el original compartido; `baseline_receipts_sha256` `a0121b70…` coincide con `manifest-fuentes.jsonl`; el agregado `refresh_receipts_sha256` `cf29254a…` no se recalculó porque `evidencia.json` no declara la regla de agregación | OK parcial, registrado |
| Política `configs/thresholds.yaml` | SHA-256 `d2931c04249aba99330aa3f1ffc628ce5adb9e6d153dce0813c16e95cd5266a0`, igual al de los recibos previos | OK |

El módulo volvió a verificar versión y SHA-256 de grilla y ventanas, el vínculo `input_sha256`,
la zona UTC y el horizonte al inicio de la corrida (`verify_bundle`), y al final comprobó que
ningún archivo de entrada cambió durante la evaluación.

## Resultados por serie y conciliación de descartes

La inspección estructural reconstruyó las 324 463 ventanas del paquete y las 7 787 112 horas
objetivo (24 por ventana, todas medidas, sin imputación). Para cada serie se exigieron, con fail
closed, `candidatos == completa + historia_faltante + futuro_faltante` y
`completa == ventanas_en_paquete`; cualquier descuadre habría detenido la corrida con error.

| Serie | Candidatos | Completas | Historia faltante | Futuro faltante | Ventanas en paquete |
| --- | ---: | ---: | ---: | ---: | ---: |
| `1976b93c…46bd2ada` | 80 276 | 41 284 | 36 762 | 2 230 | 41 284 |
| `5cff99d2…332df9f8` | 82 484 | 40 415 | 39 771 | 2 298 | 40 415 |
| `769147bd…ef37e60a` | 82 484 | 47 486 | 31 268 | 3 730 | 47 486 |
| `7f6d0108…4e8f8e3a` | 82 484 | 41 164 | 38 328 | 2 992 | 41 164 |
| `828df888…262618ec` | 82 484 | 45 751 | 34 383 | 2 350 | 45 751 |
| `956cc6f9…792fdbb57` | 82 484 | 58 217 | 22 133 | 2 134 | 58 217 |
| `ae2485b1…454b0034` | 82 172 | 50 146 | 27 792 | 4 234 | 50 146 |
| **Total** | **574 868** | **324 463** | **230 437** | **19 968** | **324 463** |

Las dos identidades se cumplen en las siete series (574 868 = 324 463 + 230 437 + 19 968), sin
excepciones y sin ajustes. La conciliación incluye las series cuya historia se descarta por
completo; ninguna desaparece del resumen.

Sobre la identidad de emisión `completa == elegidas + descartadas(motivo)`: la emisión no se
alcanzó, porque la elegibilidad está cerrada (ver abajo) y el proceso se detiene antes de escribir
etiquetas. En esta corrida elegidas = 0 y descartadas por emisión = 0. La identidad se exige en
`_write_labels` antes de publicar y está probada en `test_discard_counts_reconcile_per_series` y
`test_missing_window_group_stops_label_publication`; con calidad `unknown` no existe evidencia
admitible que la active sobre datos reales, y no se fabricó ninguna.

## Verificación antifuga

`verify_no_label_leakage` se ejecutó integrada en `evaluate_windows`, sobre los archivos del
paquete real y antes de cualquier decisión de publicación:

| Comprobación | Resultado |
| --- | --- |
| Campos derivados de etiquetas en `windows.parquet` (entradas) | 0 |
| Ventanas revisadas | 324 463 |
| Infracciones de límites (`origin_at`, historia, objetivo) | 0 |
| Identificadores compartidos entre historia y objetivo | 0 |
| Etiquetas revisadas (no se publicaron) | 0 |

## Elegibilidad y etiquetas

`labeling: inadmissible`, motivo `labeling_evidence_missing`. No se generó ninguna etiqueta: ni
`above_reference`, ni `not_above_reference`, ni `not_evaluable`. La calidad publicada de los
objetivos sigue siendo `unknown`, que por ADR-005 jamás se admite como válida, y la posición del
intervalo (`hour_ending`) sigue sin evidencia institucional (#43). Por coherencia con esa decisión,
las etiquetas regulatorias diarias (`calendar_day`) siguen diferidas y no se emitieron.

## Relación con los recibos previos

La `compatibility.json` de esta corrida es idéntica byte a byte a
`metadata/issue-20-verificacion-antifuga.json` (recibo de la corrida de Keneth del 20/11/2026 a las
18:38 UTC, fusionado en main en `22a866c`) y a la salida `labels-24/` del árbol compartido; el
`manifest.json` también es idéntico. Tres ejecuciones en entornos distintos con la misma versión
del código produjeron salidas idénticas: la repetición determinista queda comprobada sobre el
paquete real, además de la prueba sintética existente.

## Verificado y pendiente

Verificado en esta corrida: versiones y hashes del paquete real, antifuga integrada, reconstrucción
de 324 463 objetivos 24/24 medidos, conciliación de descartes por serie con fail closed y salida
determinista sin etiquetas. La integridad de los paquetes compartidos `lima-postcorte-20261118` y
`pm-bivariado-20261120` quedó comprobada en lo declarado por sus propios recibos.

Sigue pendiente y no se afirma aquí: la evidencia institucional de #43 (posición del intervalo,
calidad individual y unidades acreditadas por la fuente) para emitir etiquetas reales; la emisión
de etiquetas de episodio y la emisión de etiquetas regulatorias diarias; cualquier conclusión de
cumplimiento legal o de seguridad del aire. La tarea #20 permanece **abierta**; este trabajo usa
`Refs #20` y no la cierra.

## Reproducción

El comando de arriba, desde un checkout de `main` con `make setup`, reproduce las salidas en una
carpeta propia; el paquete real puede apuntarse donde resida el árbol compartido con solo lectura.
Los derivados quedan fuera de Git (`data/labels-real-20261120/` es local). El registro compacto con
hashes y resultados está en `metadata/event-labels-real-20261120.json`.
