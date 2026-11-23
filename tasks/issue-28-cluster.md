# Ejecutar y reanudar el entrenamiento de Neblima en MicroK8s

Responsable: Keneth. Alcance local para [#28](https://github.com/keneth-arias/Neblima/issues/28). Este plan complementa el [diseño experimental](issue-27-qwen-plan.md). Los PR de plataforma se preparan en `ml-infra`, el entrenador genérico en la bifurcación de OpenTSLM y las ventanas, configuraciones y métricas en Neblima.

## Punto de partida verificado

En el nodo `bm` se verificó MicroK8s v1.35.6, dos RTX 5070 Ti de 16 303 MiB por tarjeta y una cuota usada de 0/2 GPU en `training`. Flux tenía ambas reconciliaciones listas en la revisión `0db10dd80c27c52ec9c399178691331ea65f81f9` de ml-infra. SkyPilot 0.14.3 dispone del contexto dedicado `dev-bm` y del perfil `rtx5070ti:2`. Los pods de prueba para DDP, FSDP y reanudación finalizaron correctamente.

La [tarea SkyPilot existente](https://github.com/keneth-arias/ml-infra/blob/0db10dd80c27c52ec9c399178691331ea65f81f9/workloads/sky/lora.yaml) utiliza dos GPU en un pod, monta `/checkpoints` y ejecuta LoRA sobre un Llama sintético. El [Job de FSDP](https://github.com/keneth-arias/ml-infra/blob/0db10dd80c27c52ec9c399178691331ea65f81f9/workloads/smoke/fsdp.yaml) usa FSDP1 con `LlamaDecoderLayer`. La imagen `dev2` fija Transformers 4.57.6; el entorno de Qwen ya probado usa 5.5.4 y PyTorch 2.9.1 con CUDA 12.8.

## Entregas en orden

| Entrega | Acción | Evidencia para avanzar |
| --- | --- | --- |
| 1 · ml-infra y Neblima | Derivar una imagen con etiqueta inmutable por revisión, importarla en containerd y registrar su digest. Incluir el entorno fijado del entrenador y las versiones compatibles de seguimiento; mantener el lector TimeNet en su propio entorno. Copiar una sola vez la versión TimeF y la revisión de Qwen a almacenamiento local de insumos. | Desde un pod nuevo, verificar SHA-256 del manifiesto TimeF de #25, ejecutar la verificación del lector y comprobar hashes de los archivos del modelo antes de cargar sin red. Leer la misma ventana registrada en #27. |
| 2 · OpenTSLM y ml-infra | Crear un perfil SkyPilot dedicado sobre `k8s/dev-bm`, namespace `training`, un nodo y `rtx5070ti:2`. Usar `torchrun --standalone --nproc-per-node=2`, con un proceso por tarjeta. Montar insumos de solo lectura, estado de escritura y memoria compartida acotada para NCCL. Mantener `remote_identity: NONE`. Medir RAM de carga de pesos, memoria compartida y uso de CPU antes de fijar los recursos del trabajo largo. | Identificar dos GPU distintas, comprobar una reducción NCCL con resultado 3 para los valores 1 y 2, ejecutar un paso real de Qwen con FSDP2 y verificar fragmentos locales de pesos, gradientes y AdamW. Comparar la actualización con el control de una GPU a igual lote efectivo. |
| 3 · OpenTSLM y Neblima | Implementar guardado y restauración al límite de una actualización del optimizador; medir tamaño y latencia en el PVC. Ejecutar cuatro pasos continuos y, por separado, dos pasos, liberar el pod y completar dos pasos en una nueva ejecución SkyPilot. | Coinciden identificadores y orden de las ventanas posteriores, paso global, tasa de aprendizaje y próxima actualización dentro de tolerancias registradas. Simular además una escritura incompleta y recuperar el último paso publicado. Verificar pronósticos tras restaurar el modelo elegido. |
| 4 · Neblima | Ejecutar por turnos los controles de una GPU, DDP y FSDP2 con ambas GPU. Mantener igual el lote efectivo, la precisión y la exposición a ventanas; medir ventanas/s, memoria máxima por rango y tiempo de guardado. Liberar el clúster SkyPilot de cada ejecución tras verificar el último punto de control. | Lanzar la comparación de #28 con los mismos identificadores y presupuesto para cada cabezal. Registrar MAE en validación y costo en MLflow. Congelar configuración antes de prueba. Usar el mismo contrato de reanudación para la variante LoRA. |

Para la primera ejecución usar el kubeconfig de envío indicado en el [procedimiento de ml-infra](https://github.com/keneth-arias/ml-infra/blob/0db10dd80c27c52ec9c399178691331ea65f81f9/README.md). El comando de lanzamiento del nuevo perfil se documentará en su PR con `sky launch`; después de liberar el pod, un nuevo lanzamiento deberá aceptar el mismo identificador lógico de experimento y otro identificador de intento. La prueba existente de #27 termina después de un paso y descarta los pesos; el primer ensayo distribuido parte del modelo fijado.

## Entrega piloto

El [procedimiento y la evidencia del piloto](../docs/qwen-cluster-runbook.md) registran el ajuste con ambas RTX 5070 Ti, la verificación de FSDP2 y LoRA, y los controles DDP y de una GPU. La entrega de #28 continúa con las mediciones repetidas y el entrenamiento y validación completos.

## Qué guardar y dónde

| Ubicación | Contenido y ciclo de vida |
| --- | --- |
| Insumos locales de solo lectura | Versión TimeF de 44 MiB con atribución, pesos base fijados y archivos de configuración. Prepararlos por revisión mediante una tarea de carga y montarlos en el pod. Reutilizarlos en todos los intentos. |
| PVC `training/checkpoints`, montado en `/checkpoints` | Un directorio `airaware/<run_id>/` por combinación de datos, modelo, modo y semilla. Cada intento usa un identificador SkyPilot distinto. Un solo trabajo escritor por ejecución, con ambos rangos participando en la escritura colectiva. |
| MLflow en `ml-platform` | Rango cero registra parámetros, métricas agregadas de ambos rangos, identificadores del intento, SHA-256, tamaño y ruta del punto de control. PostgreSQL conserva metadatos; el almacén de objetos conserva manifiestos, métricas resumidas y exportaciones compactas seleccionadas. Evitar duplicar allí cada estado de AdamW. |
| Disco efímero del pod | Cachés regenerables, descargas intermedias y temporales descartables. Los fragmentos que se van a publicar se escriben en el mismo PVC que su destino final. |

Para FSDP2, guardar con PyTorch Distributed Checkpoint los pesos y el optimizador distribuidos; incluir planificador, paso, configuración de precisión y escalador si se usa, estado aleatorio por rango y cursor del muestreador con época, semilla y posición. Para LoRA guardar adaptadores, proyector, token de lectura y cabezal, además del estado necesario para continuar AdamW sobre esos parámetros y la revisión/hash exactos del modelo base. Distinguir en el manifiesto una exportación para inferencia y un estado completo de reanudación. [PyTorch Distributed Checkpoint](https://docs.pytorch.org/docs/2.9/distributed.checkpoint.html).

Escribir en una carpeta temporal por intento y paso. Una vez finalizada la escritura de todos los rangos, comprobar archivos, tamaños y sumas; publicar con renombrado dentro del PVC y actualizar `latest` de forma atómica. Actualizar `best` solo con la métrica de validación acordada. Al reanudar, cotejar el manifiesto con datos, código, modelo, arquitectura, topología y configuración esperados. Si falla la verificación, registrar el fallo y usar la última generación completa compatible. Conservar un historial de intentos en MLflow.

## Presupuesto y recuperación

El PVC de checkpoints está ligado al nodo, solicita 32 GiB en modo RWO y contenía unos 7,6 MiB en la inspección. Los PVC de objetos (32 GiB) y PostgreSQL (8 GiB) comparten con checkpoints el mismo sistema de archivos, con aproximadamente 1,8 TiB disponibles en ese momento. La clase `microk8s-hostpath` usa `Delete` y tiene la expansión deshabilitada. El tamaño solicitado de hostpath no impone un límite físico. Medir el uso de los directorios y el espacio libre del dispositivo. [MicroK8s hostpath](https://microk8s.io/docs/addon-hostpath-storage).

Como estimación conservadora, 752 millones de parámetros por 12 bytes (pesos FP32 y dos momentos FP32 de AdamW) dan unos 8,4 GiB por generación completa antes de otros estados. El tamaño depende de los parámetros con estado de optimizador y de la serialización. Particionar entre GPU reparte el estado entre archivos. Medir la suma de todos los archivos antes de decidir la capacidad.

Para el ensayo usar la capacidad existente y conservar sus pruebas previas. Para entrenamiento, presupuestar por separado los dos últimos estados válidos, el mejor si es distinto, una generación en escritura y margen operativo del 20 %. Con 8,4 GiB por generación el presupuesto de un solo ajuste completo sería de unos 40 GiB; agregar los demás experimentos retenidos. Si excede el presupuesto, definir por Flux un PVC nuevo dimensionado con mediciones, copiar y verificar las generaciones elegidas y ensayar su restauración antes de cambiar el montaje. Conservar el PVC anterior durante la transición.

Propuesta inicial: guardar cada 15 minutos en el siguiente límite de actualización y al terminar. Ajustar según latencia y pérdida de trabajo tolerada. Ante falta de espacio detener el siguiente guardado preservando la última generación válida. Aplicar la rotación solo después de validar el nuevo estado y respetar los marcadores de mejor y último. Para recuperación ante pérdida del nodo, seleccionar un destino independiente autorizado y verificar una copia por hash y restauración. Hasta disponer de ese destino, la recuperación demostrable cubre reinicios de pod en `bm`.
