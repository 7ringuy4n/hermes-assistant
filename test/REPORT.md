# Test reports index

Generated evidence lives under `reports/<run>/` (summaries, logs, artifacts).
Reports omit hostnames, IPs, and account names. List everything with
`ls test/reports`.

## Key summaries

| Area | Summary |
|------|---------|
| Offline case index (units) | `reports/run-case-index-lab/SUMMARY.md` |
| Two-pass profile matrix | `reports/run-05-two-pass/SUMMARY.md` |
| Zalo DM/group concurrency | `reports/run-zalo-dm-group-concurrency/` |
| Zalo latency SLO | `reports/run-zalo-latency/` |
| Zalo continuous messages | `reports/run-zalo-continuous-messages/` |
| Zalo queue failover | `reports/run-zalo-queue-failover/` |
| Zalo scheduled composed image | `reports/run-zalo-scheduled-composed-image/` |
| Visual weather PDF | `reports/run-zalo-tn-visual-weather-pdf/` |
| Flexible composed layout | `reports/run-zalo-flexible-composed-layout/` |
| File pipeline security | `reports/run-file-pipeline-security/` |
| Memory scale (10m) | `reports/run-memory-scale-10m/` |
| Embedding + compaction | `reports/run-embedding-compact/` |
| OpenBao KV rotation | `reports/run-openbao-kv/` |
| Env obsolete cleanup | `reports/run-env-obsolete-cleanup/` |
| Grafana integration | `reports/run-grafana-integration/` |
| Vision OCR smoke | `reports/run-vision-ocr-smoke/` |

## Contract

The offline units are run by `test/scripts/run_case_index_lab.py` (with
`SKIP_VPS=1` for offline-only). Evidence requirements, artifact evaluation, and
the merge gate are in [`README.md`](./README.md) (verification contract).

## Latest results

| Scope | Result |
|-------|--------|
| Offline unit suite (VPS, `ASSISTANT_TEST_LOCAL=1 SKIP_VPS=1`) | **148/148 PASS** (`reports/run-case-index-lab/SUMMARY.md`) |
| Local self-run (strategy units) | **21/21 PASS** |

New invariant units: `queue_fifo_recovery_unit` (INV-CONV-001 / INV-QUEUE-001/002),
`archive_member_path_unit` (INV-SEC-001/003/006/007), `ssrf_guard_unit`
(INV-SEC-002), `invariant_registry_unit`.

Update this file after completing test cases.
