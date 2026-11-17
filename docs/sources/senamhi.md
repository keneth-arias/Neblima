# SENAMHI Lima: revisión documental y preguntas pendientes

> Decisión vigente del 17/11/2026: [SENAMHI listo para #13](senamhi-normalization-handoff.md).
> UTC confirmado por Keneth, unidades inferidas aceptadas y ODC-BY-1.0 con atribución.
> Esta revisión previa se conserva como evidencia histórica, no como bloqueo de normalización.

Revisión: 16/11/2026 UTC, tarea #4, responsable Keneth. Investigación autorizada por Keneth,
incluida búsqueda adicional y preparación de consulta si persistían vacíos.

## Resultado para el equipo

CSV, diccionario XLSX y metadatos DOCX están resueltos y preservados localmente. Los documentos
acreditan una serie declarada horaria y una publicación de actualización mensual, formatos de
fecha/hora y licencia de base de datos. Persisten preguntas sobre la exportación histórica: unidades
de contaminantes, zona horaria, intervalo, calidad y alcance de avisos/derechos para publicación.
La [consulta revisada](senamhi-consultation.md) fue enviada con autorización de Keneth; seguimiento en [#43](https://github.com/keneth-arias/airaware/issues/43).

El catálogo conserva unidades de contaminantes sin asignar y redistribution: unknown. Se puede
continuar preparando adquisición reproducible y análisis estructural; convertir, alinear con
meteorología, evaluar umbrales o publicar requiere resolver las incógnitas aplicables.
No se creó un descargador ni se normalizaron observaciones en esta tarea.

## Recursos y procedencia

senamhi-lima agrupa el conjunto. senamhi-lima-csv es la exportación de observaciones;
senamhi-data-dictionary y senamhi-metadata son documentos asociados. Servicio de monitoreo e
informes son contexto de esa red, sin nuevas mediciones independientes.

- [Catálogo oficial](https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de).
- Las URL exactas de CSV/XLSX/DOCX están en configs/sources.yaml.
- [Manifiesto del CSV](../../metadata/senamhi-lima-download.json): descarga del 15/11, 68 501 558 bytes,
  577 794 filas y 15 columnas; suma SHA-256 confirmada de nuevo el 16/11.
- [Manifiesto documental](../../metadata/senamhi-documentation.json): tamaño, SHA-256, URL, formato,
  ubicación local, fecha de verificación y referencias de cinco documentos. La fecha de verificación
  no pretende ser la hora exacta de descarga. Lightpanda no expuso el código HTTP exacto de los archivos.

Los originales permanecen en data/raw/senamhi/, excluidos de Git. No se volvió a descargar el CSV.
Se preservaron XLSX (10 471 bytes), DOCX (41 626), manual de calidad (831 789), evaluación histórica
(2 291 577) y boletín febrero 2018 (3 282 212). Son tamaños observados, no etiquetas del portal.
No hay evidencia de bloqueo de esos recursos en esta ejecución; el 403 anterior fue de otro canal.

## Matriz de los 15 campos

Referencia primaria: hoja DiccionarioDatos del XLSX oficial. Las filas son referencias de Excel.
La transcripción técnica de tipos y formatos se conserva también en el manifiesto documental.

| Campo | Significado documentado | Referencia | Límite para convertir |
| --- | --- | --- | --- |
| ID | Identificador de registro | fila 5 | No prueba unicidad científica |
| ESTACION | Nombre de estación automática | fila 6 | Homologación/reubicación en #14 |
| FECHA | Fecha de medición, aaaammdd | fila 7 | Sin zona horaria |
| HORA | Hora de medición, hhmmss | fila 8 | Sin zona ni inicio/fin del intervalo |
| LONGITUD | Posición respecto de Greenwich | fila 9 | Diccionario habla de grados/minutos/segundos; CSV muestra decimales |
| LATITUD | Posición respecto del ecuador | fila 10 | Confirmar representación y sistema geodésico |
| ALTITUD | Elevación, metros sobre nivel medio del mar | fila 11 | No confundir con altura de toma |
| PM10 | Material particulado menor a 10 micras | fila 12 | Unidad de concentración ausente |
| PM2_5 | Material particulado menor a 2.5 micras | fila 13 | Unidad de concentración ausente |
| NO2 | Dióxido de nitrógeno | fila 14 | Unidad y conversión por aclarar |
| DEPARTAMENTO | Departamento de la estación | fila 15 | Referencia INEI |
| PROVINCIA | Provincia de la estación | fila 16 | Referencia INEI |
| DISTRITO | Distrito de la estación | fila 17 | Referencia INEI |
| UBIGEO | Código geográfico | fila 18 | Declarado alfanumérico de seis posiciones |
| FECHA_CORTE | Día de generación del conjunto, aaaammdd | fila 19 | Distinto de última observación |

Una muestra de las primeras filas contiene HORA=50000 y UBIGEO=150113.0; se preservaron así.
El diccionario no autoriza quitar decimales de cualquier código ni convertir horas a UTC por ubicación.
El DOCX declara cobertura Lima Metropolitana, 2015–2024 y señala que se omitan registros vacíos de
contaminantes para el análisis. No define todos los posibles códigos de ausencia ni reglas por versión.
Una casilla vacía sigue siendo ausencia de dato; nunca se convierte automáticamente en cero.

## Búsqueda adicional y contraste de unidades/tiempo

La [bitácora](senamhi-research-log.md) registra consultas, fuentes, redirecciones y límites.
Se examinaron fuentes oficiales y se separaron documentos generales de la exportación concreta.

El [manual MT-DRD-005 v01](https://www.senamhi.gob.pe/load/file/00711SENA-91.pdf), tabla 1,
página 6, expresa PM10/PM2.5 en µg/m³ y NO2 en ppb. Se verificó visualmente la tabla.
La página 7 contempla banderines C/D/M/ND/SC y NA. El CSV no tiene una columna de banderines:
no puede reconstruirse su validación individual a partir de la palabra «validados» del DOCX.
El manual no demuestra que su procedimiento se aplicó a cada fila desde 2015.

La [ficha de Santa Anita](https://www.senamhi.gob.pe/?e=112208&p=calidad_del_aire-estadistica)
identifica TEOM para PM10, atenuación beta para PM2.5 y quimioluminiscencia para NO2.
Es información de una estación, no un historial instrumental de las siete cadenas del CSV.
La [evaluación 2013](https://www.senamhi.gob.pe/load/file/01403SENA-5.pdf), portada y página legal,
es una edición de 2015; una fecha reciente de indexación no la convierte en metodología de 2024.

El [boletín febrero 2018](https://www.gob.pe/institucion/senamhi/informes-publicaciones/6613132-boletin-vigilancia-de-la-calidad-del-aire-en-lima-metropolitana-y-el-callao-febrero-2018),
página 9 inspeccionada visualmente, presenta máximos horarios NO2 en µg/m³. Se contrastaron
exclusivamente esos cinco casos con máximos de febrero 2018 en el CSV local, sin convertir valores:

| Estación | Fecha | Valor CSV y boletín | Hora boletín | HORA CSV | ID CSV |
| --- | --- | --- | --- | --- | --- |
| Campo de Marte | 2018-02-16 | 36.6 | 08:00 | 13:00 | 27417 |
| Carabayllo | 2018-02-24 | 103.6 | 10:00 | 15:00 | 110153 |
| San Borja | 2018-02-19 | 58.8 | 15:00 | 20:00 | 275122 |
| San Juan de Lurigancho | 2018-02-24 | 95.4 | 09:00 | 14:00 | 357778 |
| San Martín de Porres | 2018-02-03 | 14.3 | 09:00 | 14:00 | 439816 |

**Inferencia acotada:** coincidencia de valores/fechas y diferencia constante +5 horas, compatible
con NO2 exportado en µg/m³ y CSV en UTC frente al horario del boletín. No confirma la convención de
todo el histórico, ni el intervalo horario, ni una conversión física. Por eso no se completan units
ni una zona horaria de producción. El boletín excluye ciertas estaciones por mantenimiento: tampoco
es un patrón de verdad absoluto para la serie validada. Datos de reproducción en el manifiesto.

## Licencia y atribución

Catálogo y DOCX declaran la misma licencia. El [enlace publicado](http://opendefinition.org/licenses/odc-by/)
remite a ODC-BY v1.0; el [texto oficial](https://opendatacommons.org/licenses/by/1-0/) se revisó con
Lightpanda y respondió HTTP 200. Se registró ODC-BY-1.0 como licencia documentada de la base.

Las secciones 3.1 y 4 permiten reutilización con condiciones; 4.2–4.4 exigen conservar licencia,
avisos y atribución aplicables. La sección 2.4 distingue derechos sobre contenidos individuales.
Esto no indica una prohibición de SENAMHI: la aclaración pendiente es el alcance de la declaración
sobre la exportación y qué avisos concretos conservar. No corresponde relicenciar la base como MIT
o AGPL por las licencias del software. La revisión operativa mantiene pendiente la publicación.

Propuesta de atribución para revisar antes de publicar: SENAMHI, nombre completo del conjunto,
URL original, ODC-BY-1.0 con enlace, fecha de obtención y descripción de cambios de AirAware.
La futura contribución TimeNet debe separar licencia del código, base y componentes añadidos;
#21/#24 verificarán los requisitos de entrega antes de proponer publicación externa.

## Entrega y bloqueos

Los tres recursos exigidos están resueltos; frecuencia, significado y licencia tienen evidencia
fechada. Las preguntas no resueltas se conservaron y se preparó una consulta revisada.
La investigación #4 queda completa con su entrega y el envío autorizado de la consulta.
El seguimiento de respuestas pasa a #43; el cierre no equivale a integración autorizada.
Tras respuesta de SENAMHI, registrar evidencia nueva y actualizar únicamente las afirmaciones
confirmadas. #8 reutiliza el CSV; #10 mide cobertura/calidad; #13 necesita semántica suficiente.

## Reproducir el contraste acotado

Ejecutar desde la raíz; solo lee el CSV, no crea ni modifica datos:

```bash
uv run --locked python - <<'PY'
import csv, json
from pathlib import Path
review = json.loads(Path('metadata/senamhi-documentation.json').read_text())
expected = {r['station']: r for r in review['no2_crosscheck']}
peaks = {}
with open('data/raw/senamhi/senamhi_lima_monitoreo_1.csv', newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        station = row['ESTACION']
        if station in expected and row['FECHA'].startswith('201802') and row['NO2'].strip():
            if station not in peaks or float(row['NO2']) > float(peaks[station]['NO2']):
                peaks[station] = row
for station, evidence in expected.items():
    row = peaks[station]
    assert row['ID'] == evidence['csv_record_id']
    assert row['FECHA'] == evidence['date']
    assert float(row['NO2']) == evidence['bulletin_value']
    assert int(row['HORA']) // 10000 - int(evidence['bulletin_hour']) // 10000 == 5
print('Cinco casos coinciden; inferencia acotada, sin modificar unidades ni tiempo.')
PY
```

No se añadieron dependencias al paquete. XLSX/DOCX se inspeccionaron con zipfile/ElementTree;
PDF con pypdf y PyMuPDF en entornos efímeros de uv; las páginas indicadas se revisaron visualmente.
make check valida catálogo y coherencia documental sin originales ni navegador. make build y make audit
siguen siendo obligatorios antes de la entrega.

## Reutilización reproducible de #8

El plan configs/acquisition/senamhi-local.json y el informe reports/acquisition/senamhi.md registran
la adquisición local aprobada. metadata/senamhi-acquisition-check.json comprueba seis originales y
la reutilización de CSV/XLSX/DOCX en dos recorridos offline; cero bytes de red y archivos/manifiestos
previos intactos. No se cambian las conclusiones científicas ni los pendientes de #43.

## Revisión posterior de métodos externos y controles diarios

La [evaluación del repositorio y nuevo contraste](metadata-methods-review.md) identifica el mismo
CSV por SHA-256. Diez máximos diarios PM10/PM2.5 coinciden con fechas y precisión del boletín de
febrero 2018 al usar una vista diagnóstica crudo−5 h con al menos 18 observaciones diarias.
Esto refuerza la hipótesis temporal anterior, sin confirmar todo el histórico ni convertir producción.
