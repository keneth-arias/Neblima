# #24 · Ficha y preparación del aporte a TimeNet

La [ficha de Lima](../docs/dataset-cards/lima-pm25-forecast.md) describe la versión completa
con sus particiones, cobertura, datos faltantes, usos y reproducción. El código nuevo del
aporte se preparó en una copia separada de TimeNet en
`9bd1613019ee61fbc52e02106a1a45990ead7a54`. Usa MIT para el conector y mantiene
ODC-By-1.0 para los datos, con el aviso de SENAMHI. Se implementó con la interfaz pública
de TimeNet y la especificación de entradas y objetivos de AirAware. El conector carece de
dependencias del proyecto AGPL.

## Recibo de verificación

- Commit local `0d5c17edf88ba814ddabf6fab6dcc5e5b38c3a25`.
- Parche local `data/staging/timenet-lima-pm25-mit.patch`, SHA-256
  `5b2dcaee6810016e5df93f5478b7f0804cefeb83895f21087f11c3befff8e328`.
- `timenet-build build airaware/lima-pm25-forecast@0.1.0 --no-isolation` se ejecutó
  con el original verificado en caché, registros locales y la red deshabilitada.
  El segundo ensayo con las dependencias del archivo uv.lock de TimeNet tomó 66,01 s y
  2 868 360 KiB de memoria residente máxima.
- El lector verificó 338 892 tareas. Las tablas Arrow de tareas y objetivos coincidieron
  con la versión interna de #22. Se verificó también una historia por partición.
  SHA-256 del manifiesto de esta corrida
  `fbde4e2f8b2028e24a9a9f5d52c78a10bb5f90d50b0b3d3e1e9897e0ee4c2910`.
- En la revisión fijada, pasaron formato, lint y tipos del conector en Python 3.13 y
  3.11, y 974 pruebas sin red de conectores, tipos y conjuntos, incluidas las tres nuevas.
  El control general `make check` verificó esquemas y pasó formato y lint.
  La fase global de tipos reportó importaciones faltantes de Torch, Zarr y herramientas
  de documentación ajenas al conector en el entorno local. Queda por verificar el
  conjunto completo de controles del repositorio externo con sus extras instalados.

El código, la ficha, las pruebas y la documentación del aporte están en inglés.
El PR externo queda sujeto a autorización de publicación. Se propone publicar
el aporte de código y documentación a través de un fork y usar una copia verificada
del original durante las pruebas. Los artefactos masivos quedan en almacenamiento local.
