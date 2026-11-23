# Observation contract v1

[`airaware.schemas`](../../src/airaware/schemas.py) defines `Observation`,
`Provenance`, `Source`, `Station`, `Sensor`, and `Relocation`. The Pydantic
models reject extra fields. Use `Observation.model_json_schema()` for the
JSON schema and `model_dump(mode="json")` for JSON-compatible output.

## Values and original records

Keep `raw_fields`, `value_raw`, `parameter_raw`, `unit_raw`, and
`time_raw` as supplied. Only `value_status="finite"` carries a numeric
`value`. The statuses `censored`, `missing`, `unresolved`, and
`nonfinite` preserve distinct cases. Zero remains a numeric value.
Apply sign or detection-limit rules only when the source supports them.

`provenance` records the source, the original SHA-256 checksum, and a
record number. Count the CSV header as row 1. For an Excel workbook,
preserve the worksheet and row. Preserve campaign context in
`raw_fields`. Use `parent_ids` to trace derived and imputed observations
to their inputs.

## Time, quality, and identity

`observed_at` can hold a published timestamp with its time zone and
supporting evidence. Leave it null if the clock can't be interpreted.
An observed timestamp can exist while the interval boundaries remain
unknown. Set `start` and `end` only when supported, with an end after
the start. Record `available_at` only when publication evidence exists.

Keep `quality="unknown"` until evidence supports a quality judgment.
The `kind` field distinguishes measured, derived, modeled, reanalysis,
forecast, and imputed values. The schema can represent imputed values. The
Lima benchmark uses complete observed windows.

Leave `station_id` and `sensor_id` unresolved when names are the only
identity evidence. `Station` retains original coordinates and requires
evidence for an interpreted latitude-longitude pair. `Relocation` accepts
an unknown date and requires evidence of the relocation. `Source`
records a license separately from evidence of data rights.

Model validation checks structure and consistency. Review units, clocks,
rights, and benchmark eligibility against source evidence.
[Schema tests](../../tests/test_observation_schema.py) ·
[Historical SENAMHI policy (Spanish)](../decisions/005-senamhi-operating-policy.md)
