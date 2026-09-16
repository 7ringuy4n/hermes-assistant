# security / av-gateway

## Purpose

HTTP gateway in front of ClamAV (and similar). Scans uploaded or inbound files and returns clean / infected before any extract or OCR.

## Profile

Optional antivirus component (`ENABLE_ANTIVIRUS=active`).

Activate with `bash run.sh install antivirus`. The flag enables both the
ClamAV/gateway profile and required inbound/outbound scanning in Hermes and
Dispatcher. A scanner outage or unfinished verdict blocks parsing/conversion
and delivery; it is not an implicit clean verdict. Each inbound file owns a
separate scan session so an infected upload cannot poison later clean files.
Cold starts may require signature downloads. Verify `/health` has `clamd: true`,
then test a harmless clean upload and the standard EICAR antivirus fixture.

## Main functions

Capacity is bounded independently of scanner readiness: files up to 50 MiB,
128 MiB total queued/scanning bytes, 16 queued jobs, 2 concurrent upload reads,
2,048 retained sessions and 64 files per session by default. Completed scan
records expire after one hour; queued/active records never expire mid-scan.
Overload returns HTTP 429 and oversized files return HTTP 413 before a verdict
can authorize parsing. Unexpected scanner errors block the file, release the
occupied capacity and leave the worker available for later jobs.
Multipart uploads require a valid `Content-Length` (HTTP 411 otherwise); requests
over the file limit plus 1 MiB multipart overhead are rejected before parser
spooling. Concurrent multipart parsing is capped by `AV_QUEUE_WORKERS` and
saturation rejects with HTTP 429 before reading the body. Chunked uploads are
not supported. The file itself must still meet the
stricter file-size limit after the multipart envelope is parsed.

Tune `AV_MAX_FILE_BYTES`, `AV_MAX_PENDING_BYTES`, `AV_MAX_QUEUE`,
`AV_MAX_SESSIONS`, `AV_MAX_SESSION_FILES`, `AV_SESSION_TTL_SECONDS` and
`AV_QUEUE_WORKERS` through the canonical Compose environment. Pending capacity
must cover one maximum-sized file; all limits must be positive. Quarantine uses
sanitized basenames. Quarantine retention remains `AV_QUARANTINE_DAYS` (7 days)
and is independent of in-memory verdict retention.

| Function | Detail |
|---|---|
| Scan by path or upload | Returns status for pipeline |
| Fail closed | On scanner down, prefer block or skip ingest (config) |

## Related

- [../README.md](../README.md)  
- [security-manager](../security-manager/README.md)
