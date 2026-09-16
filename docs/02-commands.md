# 02b — Operations command reference

```bash
cd /opt/assistant
bash run.sh <command> [args…]
```

## First installation

File creation and conversion require `install media` and
`OFFICE_FILE_GEN=active`; direct use does not require `install message` or Zalo.
Ask Hermes to convert an attached file (for example PPTX to PDF, selected PDF
pages to images, or Excel to Word). Native print conversion preserves print
layout; editable cross-format conversion reports content-reflow limitations.
Do not install Office libraries in Hermes or rename file extensions manually.

```bash
sudo timedatectl set-timezone Asia/Ho_Chi_Minh
cp .env.example .env
bash run.sh up
bash run.sh first-setup-omnirouter
bash run.sh install schedule media security notify message monitor
bash scripts/main/setup-zalo.sh
bash run.sh install-timers
```

`first-setup-omnirouter` initializes OmniRoute only. It must not run probes that
generate images or send Zalo messages. Provider/combo changes are operator
configuration; update does not replace them.

## Lifecycle

| Command | Data safety and behavior |
|---|---|
| `up` | Reconcile core and enabled-worker compose services. |
| `down` | Stop services; preserve volumes and host data. |
| `destroy` | Create and verify a backup, then remove project containers and networks. Volumes and `/data/assistant` remain. |
| `update` | Create and verify a backup, rebuild/reconcile services, clean supported obsolete environment keys, and preserve OmniRoute/OpenBao state. |
| `backup` | Load OpenBao retention settings, create a verified stamp, retain seven days by default, then remove the transient export. |
| `compact` | Load OpenBao retention settings, prune expired staged memory, and refresh vector indexes through combo `embedding`. |
| `ps` | Show service state. |
| `logs [service]` | Read service logs. |

Standalone `down`, `ps`, and `logs` hydrate their required Compose values from
OpenBao after plaintext environment cleanup and remove the transient export
when the command exits. Post-ready knowledge synchronization uses a
noninteractive privilege boundary and fails the lifecycle command instead of
silently leaving the knowledge index stale.

Clean redeploy of current data:

```bash
bash run.sh backup
bash run.sh verify
bash run.sh workers          # capture enabled workers
bash run.sh destroy
bash run.sh up               # reads retained worker state
bash run.sh ps
```

Do not remove named volumes or `/data/assistant` as part of this sequence.

## Worker lifecycle

```bash
bash run.sh install list
bash run.sh install schedule media security notify message monitor
bash run.sh uninstall notify
bash run.sh workers
```

Every mutating worker/config command backs up and verifies first. On a running
host, apply supported core settings with:

```bash
bash run.sh add-components HERMES_REPLICAS=2 --update
bash run.sh add-components ZALO_INBOUND_QUEUE=1 --update
```

## Backup and restore

```bash
bash run.sh backup
bash run.sh verify
bash run.sh verify 20260905_120000
bash run.sh restore 20260905_120000
bash run.sh migrate
```

A valid stamp covers data/config, OmniRoute, OpenBao, the Zalo login credential,
and Zalo identity/allowlist files. PostgreSQL carries the channel/member
registry. Reports show presence/checksums and membership counts without
printing identities, tokens, or provider keys.

## Knowledge, memory, and schedule

The renamed Memory Worker keeps `bash run.sh update memory` and the `memory`
Compose service key. Direct notes use the notes skill's `scripts/notes.py` with
a structured plan on stdin; `HERMES_RECORD_SCOPE` comes from host configuration.
This is a trusted local command, not a public multi-user API. Direct schedules
use the shared schedule service with `origin.platform=hermes`. Direct document
generation uses `send_zalo=false` without `thread_id`; formatted documents
require `draft=true`, native-text/page-image review and then selected-artifact
delivery. Direct sessions attach the reviewed file natively. Conversion can
also target an explicitly quoted file (for example, quote a PPTX and ask to
convert it to PDF); only the requested converted outputs are delivered.
Do not enable a messaging integration for direct capability use.

```bash
bash run.sh auto-learn
bash run.sh learn-status
bash run.sh compact
bash run.sh optimize-memory
sudo bash run.sh install-timers
systemctl list-timers 'assistant-*'
```

Compact/optimization and ingest must prove calls through the `embedding` combo.
Scheduler tests are separate from setup and use a maximum two-minute target.

## Runtime observation

```bash
docker compose ps
docker compose logs --since 15m hermes router-worker omni-router
journalctl --user -u com.hermes.zaloplugin --since '15 minutes ago'
systemctl --user status com.hermes.zaloplugin
```

Also inspect dispatcher/jobs, schedule-worker, and watchers when their test is
in scope. Classify provider quota/queue saturation separately from service
hangs and restart loops.

## Updating from `main`

```bash
cd /opt/assistant
git fetch origin
git checkout main
git pull --ff-only origin main
bash run.sh update
bash run.sh ps
```

Do not use `git reset --hard` on an operator checkout unless its local changes
have been reviewed and explicitly discarded.
