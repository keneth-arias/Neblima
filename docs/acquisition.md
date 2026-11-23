# Acquire data with provenance

The `airaware acquire` command preserves original bytes and records where
they came from. Source evidence governs units, timestamps, and rights.
The [SENAMHI follow-up](https://github.com/keneth-arias/Neblima/issues/43)
tracks unresolved questions.

## Prepare your workspace

Run these commands from the root of your own Linux checkout. The acquisition
locking and publishing logic uses local filesystem semantics.

```bash
make setup
make init
uv run --locked airaware acquire --help
```

Keep data, credentials, and environments separate per checkout. Use
`AIRAWARE_DATA_DIR` or the overriding `--data-dir` option to set the data
root. Store requests in `data/staging/` if needed. Git excludes generated
data and manifests.

## Register a file downloaded with Lightpanda

Follow the [web access protocol](web-access.md) to resolve and download an
authorized resource. The command imports the downloaded file. Use
`method: lightpanda` for a Lightpanda download or `method: local` for a
separately identified local original. Keep evidence for the declared
provenance. Here is a request template for a small comma-separated values
(CSV) file.

```json
{
  "source_id": "lima-sample",
  "resource_url": "https://example.org/lima-sample.csv",
  "method": "lightpanda",
  "format": "csv",
  "max_bytes": 1000000
}
```

Save the real request as `data/staging/request.json` and pass the path to
the original file.

```bash
uv run --locked airaware acquire import-file \
  --spec data/staging/request.json --file /path/to/original.csv
```

Set `max_bytes` near the expected size, up to the ceiling of 1,000 GiB
(1,073,741,824,000 bytes). Set `expected_sha256` when you have a trusted
checksum. Set `acquired_at` with a time zone when known. The verifier
records `verified_at`. Use `final_url` only when you have the resolved URL.
Keep user information, fragments, credentials, and signed parameters out
of URLs and secrets out of all fields. The current transport supports
public resources.

## Reuse the original SENAMHI CSV

With the approved original already under `data/raw/senamhi/`, build the
request from the receipt. This example keeps the original filename and
uses the catalog ID `senamhi-lima-csv`.

```bash
uv run --locked python - <<'PY'
import json
from pathlib import Path
original = json.loads(Path('metadata/senamhi-lima-download.json').read_text())
request = {
    'source_id': 'senamhi-lima-csv',
    'resource_url': original['source_url'],
    'method': 'lightpanda',
    'format': 'csv',
    'max_bytes': 70000000,
    'expected_sha256': original['sha256'],
    'acquired_at': original['retrieved_at_utc'],
}
p = Path('data/staging/senamhi-acquisition-request.json')
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(request, indent=2) + '\n')
PY
uv run --locked airaware acquire import-file --spec data/staging/senamhi-acquisition-request.json --file data/raw/senamhi/senamhi_lima_monitoreo_1.csv
```

The result contains `artifact`, `manifest`, and `reused`. An original
already under `raw/` returns `reused: true` even when the operation writes
its first acquisition manifest. Repeating the import verifies the size,
checksum, format, and manifest. An incompatible request or corrupt
destination fails and preserves the files for review.

## Use a documented public API

Use `acquire api` for a reviewed public application programming interface
(API). Keep a blocked website download in the access log and follow its
documented access path. The following request shows the fields to supply
for a documented JSON endpoint.

```json
{
  "source_id": "demo-api",
  "resource_url": "https://api.example.org/data?region=lima",
  "api_documentation_url": "https://api.example.org/docs",
  "method": "api",
  "format": "json",
  "json_required_keys": ["results"],
  "max_bytes": 1000000
}
```

```bash
uv run --locked airaware acquire api --spec data/staging/api-request.json --allow-host api.example.org
```

The adapter requires HTTPS on port 443 and exact allowed hosts. All
resolved addresses must be public and non-multicast. It rejects redirects,
cookies between attempts, and compressed responses. It accepts 200, 206,
or 304 as applicable and retries specific transient failures. It ignores
environment proxies and sends no authentication headers. Domain Name
System (DNS) checks occur separately from the connection. Use this local
command for approved endpoints.

The defaults are three attempts, a five-second connection timeout,
ten-second read, write, and pool timeouts, and a 60-second budget checked
between operations and chunks. An in-flight operation can finish after the
budget expires. A valid `Retry-After` can specify seconds or an HTTP date
up to 30 seconds away. Without that header, retries wait one and two
seconds. Retried statuses are 429, 500, 502, 503, and 504, plus transport
failures. A format error, checksum mismatch, limit violation, 403, or 404
stops the acquisition.

## Check formats and storage

Format checks identify expected structures before publication. Semantic
validation happens downstream.

- CSV accepts UTF-8 with or without a byte order mark. It requires at
  least two columns, unique nonempty headers, and one data row. Rows
  must have equal lengths. It rejects HTML in headers and NUL bytes.
  Field sizes follow Python's standard CSV reader limit.
- JSON requires an object with the declared `json_required_keys`, unique
  keys, and no NaN or infinity constants. Parsing is limited to 8 MiB.
- XLSX and DOCX require the ZIP structure, essential XML, and valid
  checksums. The verifier rejects encryption, macros, XML with NUL bytes,
  and `DOCTYPE` or `ENTITY` declarations. Limits are 512 members, 8 MiB
  per member, 32 MiB uncompressed, and a compression ratio of 200.
  Verification runs without extracting or executing the content.

New acquisitions outside `raw/` are prepared in a `.pending-*` directory.
After verification and filesystem synchronization where supported, the
directory is renamed on the same filesystem.

```text
data/raw/<source_id>/<sha256>/original.csv
data/raw/<source_id>/<sha256>/manifest.json
```

A file already under `raw/` uses `storage: reference` with a relative path.
Keep the original and manifest together and preserve the original bytes.
New copies use `storage: bundle`. A manifest is limited to 64 KiB and can
record a sanitized `original_name` separately from the storage path.

Nonblocking locks prevent two writers from publishing for the same source.
The operating system releases the lock when the process closes its
descriptor or exits. A crash can leave a pending directory or, after
rename, a complete bundle. The next run verifies a complete bundle
before reuse. Pending directories remain outside the acquisition
inventory and need separate cleanup. Destination and reference symlinks
are rejected. Atomicity and durability depend on the local filesystem.

## Reuse and resume API acquisitions

The command checks the checksum, structure, and request contract before
reusing a cached original. It can send a conditional request using
`ETag` or `Last-Modified`. A 304 still requires local verification.
Without a validator, the request fetches the complete representation.

```bash
uv run --locked airaware acquire api --spec data/staging/api-request.json --allow-host api.example.org --budget-bytes 2000000 --deadline-seconds 120
uv run --locked airaware acquire api --spec data/staging/api-request.json --allow-host api.example.org --offline
```

Use `--offline` to verify local originals without network or DNS access.
Use `--refresh` to clear a partial download and fetch without a condition.
These options are mutually exclusive. `--budget-bytes` covers response
payloads across failed attempts, retries, and resumed requests. The API
defaults to the request's `max_bytes` for the total budget. A chunk crossing
the limit is counted before the transfer stops. In-flight requests can
also return a chunk after a shared budget is exhausted. The budget excludes
transport headers and encryption overhead. The per-resource deadline
supports up to 86,400 seconds and remains cooperative.

Partials live under `data/.acquisition-cache/<key>/`. Checkpoints record
size and SHA-256. After a crash, the downloader trims an uncommitted
suffix only after verifying the saved prefix. It rejects an altered
partial or one without provenance. Resuming requires an identical strong
`ETag`, status 206, and coherent `Content-Range`. A 200 restarts the
transfer, while a 416 does not establish integrity. Without a strong
`ETag`, the downloader starts over.

Disk checks cover the partial, a temporary publication copy, and 64 KiB
of metadata. Without `Content-Length`, the check uses `max_bytes`.
A write failure leaves no published partial. Changed content gets its
own checksum-addressed version. `Cache-Control: no-store` blocks reusable
HTTP indexes and partials. A deliberately acquired original is managed
separately with its provenance. After a crash, a marked partial can be
removed on the next access once its ownership is verified. [HTTP conditions
and ranges](https://www.rfc-editor.org/rfc/rfc9110.html) ·
[HTTP cache rules](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2.5)

## Select and estimate a batch

A batch plan is a JSON object with `schema_version: 1` and `jobs`. Each
job has a `spec`, a `local_file` for Lightpanda or local resources, and
optional `region`, `start`, `end`, and `expected_size_bytes`. Coverage
dates describe the whole resource and require both ordered bounds.
Paths are relative to the working directory. A plan can contain up to
1,000 jobs and 2 MiB of JSON.

The following example uses the SENAMHI request above. The first command
estimates the batch. The second verifies the local file offline.

```bash
uv run --locked python - <<'PY'
import json
from pathlib import Path
spec = json.loads(Path('data/staging/senamhi-acquisition-request.json').read_text())
plan = {'schema_version': 1, 'jobs': [{
    'spec': spec,
    'local_file': 'data/raw/senamhi/senamhi_lima_monitoreo_1.csv',
    'region': 'Lima',
    'expected_size_bytes': 68501558,
}]}
Path('data/staging/senamhi-batch.json').write_text(json.dumps(plan, indent=2) + '\n')
PY
uv run --locked airaware acquire batch --plan data/staging/senamhi-batch.json --source senamhi-lima-csv --region Lima --dry-run
uv run --locked airaware acquire batch --plan data/staging/senamhi-batch.json --offline --budget-bytes 0
```

Repeat `--source` and `--region` to select exact matches. Date filters
use inclusive overlap and omit resources with unknown coverage. Filters
select whole resources. Duplicate requests are removed after filtering.
The first selected entry wins when policy fields differ, so check your
plan for conflicting requests.

A dry run uses declared sizes or local filesystem metadata. It reports
`known_size_bytes`, `unknown_count`, and the sum of the declared ceilings
as `authorized_max_bytes`. It skips network access and creates no
acquisition folders. Offline mode accepts a zero budget and rejects
missing originals.

Network batches require a positive `--budget-bytes` and one
`--allow-host` per approved host. Add `--authorize-unknown` if sizes are
missing. The limits still apply. `--workers` accepts one to four jobs
and defaults to one. Jobs for a single source run in sequence. A failed
job appears in `errors`, produces a nonzero exit status, and leaves
already verified results available.

## Set the delimiter for OEFA CSV files

Set `"csv_delimiter": ";"` for a semicolon-delimited resource from Peru's
Agency for Environmental Assessment and Enforcement (OEFA). The default
is a comma. The importer preserves the bytes and applies the declared
delimiter to structural checks. The delimiter is part of the request and
cache identity. Existing comma-delimited manifests keep their identities.

## Retrieve a bounded static public file

Use `method: http_file` for a static file resolved with Lightpanda. The
request needs `source_page_url`, `resource_url`, `format`, `max_bytes`,
and `csv_delimiter` where applicable. The first URL is the official
page on which you found the resource.

```bash
uv run --locked airaware acquire file --spec data/staging/oefa-request.json --allow-host www.datosabiertos.gob.pe --budget-bytes 2147483648 --deadline-seconds 1200
uv run --locked airaware acquire file --spec data/staging/oefa-request.json --allow-host www.datosabiertos.gob.pe --budget-bytes 0 --offline
```

The probe reads up to 64 KiB to confirm the size from `Content-Length` or
`Content-Range`. If the server ignores the range, the probe stops after
the prefix. The transfer requires a known bounded size and valid range
metadata. An unsupported status, including 403 or 418, stops acquisition.
The probe and transfer share a byte budget. The probe has a cooperative
20-second deadline within the overall deadline. Requests use the
`AirAware/0.1` user agent.

The full body uses the same cache, resumption, and publication checks as
API downloads and can't exceed the probed size. A later increase requires
a new probe. The final manifest describes the received bytes. Offline mode
verifies the local cache without DNS. Only the static-file transport can
produce a manifest with `method: http_file`. A batch treats it as a
network job and requires an explicit shared budget.

## Verify the acquisition

`make check` tests formats, limits, malformed manifests, storage failures,
concurrent publication, and HTTP behavior with simulated transport.
The versioned verification records cover the 68,501,558-byte SENAMHI
original, its offline reuse, and locally referenced workbook and document
files. [SENAMHI acquisition report (Spanish)](../reports/acquisition/senamhi.md) ·
[OEFA acquisition report (Spanish)](../reports/acquisition/oefa.md)
