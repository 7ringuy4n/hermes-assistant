# memory / session

## Purpose

Fast **short-term** conversation state in Valkey: active messages per thread,
destination metadata, timing, and acknowledged artifact-delivery coordination.
Conversation and acknowledged receipt data expire with TTL. Ambiguous wire-send
claims deliberately remain quarantined until reconciled; they cannot be safely
treated as expired permission to resend without bridge idempotency.

## Profile

Must — container `session`.

## Main functions

| Function | Detail |
|----------|--------|
| Session CRUD | Create/read active conversation for `thread_id` |
| Idle rollover | A live session idle for `SESSION_IDLE_ROLLOVER_SECONDS` (default 1h) is archived to Memory Worker and replaced by a fresh session on the next turn |
| TTL | Keys expire (e.g. 1 day) — “new session after clear” is this store |
| Dest / helpers | Where to send replies when a social-app is attached |
| Artifact delivery | Content + conversation + original source identity; token-checked reservations and actual bridge receipts |

## Artifact delivery API

1. `POST /v1/files/claim` accepts `key`, `thread_id`, `thread_type`,
   `source_message_id` and a unique `token`. Its `first=false` result does not
   mean delivered: inspect `state` and the acknowledged `message_id`.
2. `POST /v1/files/transition` accepts that unchanged binding/token plus `state`:
   `sending`, `acknowledged` (requires actual bridge `message_id`), or `release`.
   Valkey atomically checks ownership and the original conversation/source.
   Release only a pre-send reservation or a definitively rejected send.
3. `GET /v1/files/receipts/{thread_id}` requires `thread_type` and exact
   `source_message_id`; it returns `acknowledged_count`, never pending claims.
   Document workflows use this receipt to avoid redundant final chat messages.

Scan before claiming where possible. A bridge timeout or worker crash after
`sending` must be reconciled against transport history, not blindly retried.
Coordination unavailability fails closed. Existing legacy claim keys are not
accepted as delivery evidence; all affected senders must update together.

## Keys

Prefix default: `conversation_active:{session_id}` (`SESSION_KEY_PREFIX`).

## Idle rollover (daily new session)

When `PUT /v1/sessions/{id}` appends to an existing session whose
`updated_at` is at least `SESSION_IDLE_ROLLOVER_SECONDS` in the past, the
service archives that short-term blob to the Memory Worker (`source`
`session-rollover`) and starts a new session for the incoming turn. `GET` after
the window archives and reports the session absent, so the caller hydrates an
empty context. The default of `3600` (1h) means each conversation that rests for
an hour — the normal daily gap — begins with a fresh session. Set
`SESSION_IDLE_ROLLOVER_SECONDS=0` to disable rollover. The `PUT` response reports
`rolled_over` and `archived`. Archive failure never blocks the turn; the new
session is still created.

## How it differs from long-term memory

| | session (Valkey) | Memory Worker (Postgres) |
|--|------------------|---------------------------|
| Lifetime | Hours–days (TTL) | Long-term |
| Content | Recent chat turns | Extracted / typed facts |
| Failure mode | Empty history | Still may recall preferences |

## Related

- [../README.md](../README.md)  
- [memory-worker](../memory-worker/README.md)
