# Guion de grabación de la demo (primera ronda)

Plan de grabación toma por toma para la demostración de AirAware en la primera ronda del reto
[TimeNet](https://challenge.timenet.ai/). Este archivo es un borrador interno: **no se ha grabado
ni publicado nada** y la grabación espera la autorización prevista en el plan (Keneth valida las
afirmaciones; matriz en [docs/hackathon.md](../hackathon.md)). Después de grabar, registrar el
enlace y el comprobante en [enlaces.md](enlaces.md).

Solo se usan insumos existentes y versionados:

- Figura [reports/models/lima-pm25-prueba.png](../../reports/models/lima-pm25-prueba.png)
  (curva de MAE de prueba por hora y los dos ejemplos de validación, con 24 horas de historia,
  seis lecturas observadas, persistencia y Qwen).
- Flujo de verificación de
  [tools/timenet-smoke/README.md](../../tools/timenet-smoke/README.md) (lectura y verificación
  con `TimeFReader` y `LocalRegistry` sin red).
- Mapa de estaciones [web/estaciones.html](../../web/estaciones.html) como apoyo visual de
  contexto: **solo se muestra o enlaza; no se modifica en esta entrega**.

## Dónde se graba

La grabación ocurre en el entorno donde exista el paquete de datos, es decir, la máquina y carpeta
que contienen `data/timef/airaware/lima-pm25-forecast/0.1.0` (la copia local de Cristopher con los
datos restaurados), ejecutando desde la raíz de esa copia de AirAware. **No grabar desde un
checkout de trabajo cualquiera**: la carpeta `data/` no está versionada en Git y sin ella la
verificación no corre. El video se guarda en almacenamiento local; no se sube al repositorio.

Preparación antes de grabar:

1. Completar la instalación del entorno aislado una vez, con red:
   `uv sync --project tools/timenet-smoke --python 3.13.13 --locked` (la primera instalación
   requiere internet; después de esto, la demo completa corre sin red).
2. Verificar una vez que `data/timef/airaware/lima-pm25-forecast/0.1.0` existe y pasa
   `TimeFReader.verify()` con el comando de la toma 2.
3. Grabadora de pantalla a 1920×1080, micrófono probado, notificaciones desactivadas, fuente de
   terminal grande (16 pt o más).
4. Una vez sin grabar, ensayar el recorrido completo; cronometrar (objetivo: 3 a 5 minutos).
5. Reloj y zona: la primera ronda cierra el 23/11/2026 a las 2:59 a. m. en America/Lima; dejar
   margen para volver a consultar la página oficial antes de enviar.

## Tomas

### Toma 1 — Portada, problema y contexto (30–45 s)

- En pantalla: navegador con el mapa local `web/estaciones.html` (solo se muestra; no se edita).
- Qué decir: "Somos el equipo Cuybernautas, de Perú. Trabajamos con mediciones horarias de
  partículas finas (PM2.5) de siete estaciones de Lima. La pregunta: con las últimas 24 horas de
  una estación, ¿qué concentración habrá en cada una de las seis horas siguientes? La evaluación
  de este proyecto es retrospectiva, sobre horas ya publicadas; no es un sistema en tiempo real."
- En voz y en pantalla: "Los datos provienen del Servicio Nacional de Meteorología e Hidrología
  del Perú (SENAMHI), base Monitoreo de los contaminantes del aire en Lima Metropolitana, bajo la
  licencia ODC-By-1.0 con atribución obligatoria."

### Toma 2 — Verificación del conjunto con el lector oficial de TimeNet (60–90 s)

- En pantalla: terminal, desde la raíz de la copia con datos. Ejecutar:

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python - <<'PY'
from pathlib import Path
import timenet
from timenet.reader import TimeFReader
from timenet.registry import LocalRegistry

registry = Path.cwd() / "data/timef"
release = registry / "airaware/lima-pm25-forecast/0.1.0"
with TimeFReader.open(release) as reader:
    reader.verify()
    dataset = reader.read()

client = timenet.TimeNet(sources=[LocalRegistry(registry)])
dataset = client.load("airaware/lima-pm25-forecast", version="0.1.0")
print("Registros:", len(dataset.records), "Tareas:", len(dataset.tasks))
PY
```

- Qué decir: "Este es el mismo flujo de verificación documentado en
  `tools/timenet-smoke/README.md`: `TimeFReader.verify()` comprueba los archivos de la versión y
  la carga por `LocalRegistry` reproduce la lectura, todo sin red tras instalar las
  dependencias." Al ver la salida: "El conjunto `airaware/lima-pm25-forecast@0.1.0` tiene 338 892
  tareas: 237 397 de entrenamiento, 50 706 de validación y 50 789 de prueba. Cada tarea presenta
  24 horas de historia y seis objetivos ordenados, con etiquetas en tiempo universal coordinado
  (UTC)."
- Control: la cifra esperada de tareas es 338 892 (ficha del conjunto,
  [docs/dataset-cards/lima-pm25-forecast.md](../dataset-cards/lima-pm25-forecast.md)). Si la
  salida difiere, detener la grabación y revisar; no grabar una cifra distinta sin explicarla.
- Nota: este comando es el flujo del README de `tools/timenet-smoke` ("Leer y verificar con el
  SDK") apuntado a la versión de Lima; no es un comando nuevo.

### Toma 3 — Figura de resultados y denominador (60 s)

- En pantalla: abrir la figura
  [reports/models/lima-pm25-prueba.png](../../reports/models/lima-pm25-prueba.png) a tamaño
  completo.
- Qué decir: "Fijamos modelos, referencias y regla de evaluación antes de exportar la prueba. Los
  cinco métodos se evaluaron sobre los mismos 50 789 orígenes de prueba. El modelo Qwen3.5-0.8B
  con adaptación de bajo rango (LoRA) obtuvo un error absoluto medio (MAE) de 4,994 microgramos
  por metro cúbico, frente a 6,446 de la referencia de persistencia: una reducción de 22,52 por
  ciento. En concentraciones altas, la reducción fue de 6,34 por ciento y el MAE siguió siendo
  elevado: 18,371 microgramos por metro cúbico."
- Denominador, obligatorio en esta toma: "Un detalle de honestidad: el denominador común son
  304 734 pares ventana-hora; como las ventanas se solapan, representan 51 319 horas de estación
  distintas. No son observaciones independientes."

### Toma 4 — Acierto: Carabayllo (30–45 s)

- En pantalla: el panel derecho de la figura, ejemplo de Carabayllo (24 horas de historia, seis
  lecturas observadas, persistencia y Qwen superpuestas).
- Qué decir: "Este es un acierto. En Carabayllo, con la misma historia de 24 horas, el modelo
  anticipa parte del descenso y reduce el MAE de la ventana en 3,04 microgramos por metro cúbico
  frente a persistencia. Los dos ejemplos que mostramos se eligieron en validación, con una regla
  de mediana, antes de tocar la prueba."

### Toma 5 — Error: San Juan de Lurigancho (30–45 s)

- En pantalla: el ejemplo de San Juan de Lurigancho en la misma figura.
- Qué decir: "Y este es un error, a propósito. En San Juan de Lurigancho el modelo pronostica un
  descenso y pierde la subida de las últimas horas; persistencia obtiene un MAE menor por 2,03
  microgramos por metro cúbico. Mostramos el fallo porque la comparación honesta incluye dónde el
  modelo no sirve."

### Toma 6 — Límites, atribución y cierre (45–60 s)

- En pantalla: figura completa o terminal con la salida de la toma 2.
- Qué decir: "Los límites: la evaluación es retrospectiva, sobre las horas publicadas por
  SENAMHI; la disponibilidad histórica en tiempo real no está confirmada institucionalmente; la
  posición del intervalo y la calidad de cada lectura son desconocidas; las identidades de
  estación son provisionales; y no afirmamos uso regulatorio ni recomendaciones de salud. Durante
  el reto aportamos el conjunto en formato TimeF y su verificación con el lector oficial; el
  PR externo a TimeNet está en borrador y lo citamos solo como referencia. Gracias: equipo
  Cuybernautas. Datos de SENAMHI bajo ODC-By-1.0."
- No mencionar premios, jurado ni resultados esperados del concurso.

## Verificación contra la matriz del jurado

Correspondencia con los criterios oficiales registrados en
[docs/hackathon.md](../hackathon.md):

| Criterio oficial | Toma que lo evidencia |
| --- | --- |
| Caso de uso e impacto | Toma 1 (analista que anticipa la evolución horaria de PM2.5 en Lima) |
| Ejecución técnica | Toma 2 (recorrido repetible con el lector oficial, sin red) |
| Datos y TimeNet | Toma 2 (TimeF, atribución y licencia en pantalla) |
| Resultados y evaluación | Tomas 3, 4 y 5 (métricas en µg/m³, tamaños de muestra, acierto y error) |
| Presentación e interacción social | Guion completo más los textos de [publicaciones.md](publicaciones.md) (enlaces tras autorización) |

Lista de verificación antes de cerrar la grabación:

- [ ] Cada cifra dicha en voz aparece con su unidad (µg/m³) en pantalla o en la voz.
- [ ] Se distinguieron 304 734 pares ventana-hora y 51 319 horas de estación distintas.
- [ ] La atribución a SENAMHI (ODC-By-1.0) se dijo y quedó visible.
- [ ] El alcance retrospectivo quedó explícito; no se dijo tiempo real, uso regulatorio ni
      recomendaciones de salud.
- [ ] Se mostró el error de San Juan de Lurigancho, no solo el acierto de Carabayllo.
- [ ] No se prometieron premios ni créditos del organizador.
- [ ] La cifra de tareas mostrada coincide con 338 892 o se explicó la diferencia.
- [ ] El mapa `web/estaciones.html` solo se mostró o enlazó; no se modificó nada del repositorio
      durante la grabación.
- [ ] El video quedó en almacenamiento local; no se subió al repositorio.

## Después de grabar

- Registrar en [enlaces.md](enlaces.md) el enlace del video o demo, la fecha y el comprobante;
  actualizar la fila "Demo grabada" sin borrar el estado anterior.
- Enviar a Keneth el video para validación de afirmaciones antes de cualquier publicación.
- Volver a consultar la página oficial y el plazo antes de enviar el formulario de la ronda.
