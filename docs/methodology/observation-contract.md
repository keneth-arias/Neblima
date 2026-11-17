# Contrato común v1 (#12)

`airaware.schemas` define Observation, Provenance, Source, Station, Sensor y Relocation.
Los modelos Pydantic rechazan campos extra y permiten exportación JSON mediante model_dump(mode='json').
El esquema JSON se obtiene con Observation.model_json_schema(); no se mantiene una copia duplicada.

- Conservar raw_fields, value_raw, parameter_raw, unit_raw y time_raw sin transformación.
- value solo existe cuando value_status=finite. Censura, ausencias, códigos sin interpretar y
  no finitos se distinguen; cero sigue siendo un número. No se impone signo por intuición.
- provenance identifica fuente, SHA-256 y número de registro (CSV: encabezado=1) o fila/hoja XLSX.
- station_id y sensor_id son nulos hasta resolver identidad; un nombre de punto no prueba permanencia.
- observed_at conserva el timestamp publicado con zona/evidencia aunque la posición del intervalo
  sea desconocida; no implica inicio/fin. Es opcional y compatible con registros v1 anteriores.
- start/end son instantes con zona, evidencia y fin posterior. Los relojes hipotéticos se conservan
  fuera de estos campos en diagnósticos separados. available_at no se inventa desde la fecha medida.
- quality=unknown no equivale a valid. kind distingue measured, derived, modeled, reanalysis,
  forecast e imputed; derived/imputed requieren parent_ids. No se habilita imputación por definirla.
- Station conserva coordenadas originales; latitud/longitud requieren par y evidencia de conversión.
  Relocation permite fecha desconocida, pero exige evidencia. Source separa licencia y pruebas de derechos.

Los adaptadores #13/#30 deben conservar el contexto de campaña en raw_fields y evitar homologaciones
implícitas. Validar el contrato no confirma unidad, reloj, derechos ni elegibilidad de #11. Este
incremento no normaliza fuentes masivas ni cambia las interfaces existentes de Cristopher.

Verificación: tests/test_observation_schema.py; make check, make build y make audit.
