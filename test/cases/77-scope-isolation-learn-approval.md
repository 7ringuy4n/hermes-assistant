# Case 77: scoped-record authorization and knowledge-learn approval

**Goal:** Prove that records never cross a conversation boundary and that a
channel user's learn ask waits for the operator admin, while a channel-less
Hermes operator can learn without an approval step.

## A. Scoped records (notes + schedules)

Actors: operator admin, group member B, group member C, DM user D, two groups
(Group A, Group B).

1. As member B in Group B, look up and list notes/schedules without a scope
   selector. Only Group B records may be returned.
2. As member B, ask for another group (Group A), another DM (D), or `all`.
   Expect a refusal (`record_scope_forbidden`); no records are fetched.
3. As member D (DM), ask for a group, another DM, or `all`. Expect refusal.
4. As the admin, ask for Group A, D, and `all`. Expect the registered
   conversation's records only, and `all` to be read-only (mutations refused).
5. A Group A schedule must never appear in member D's DM list, and vice versa.

Pass criteria: no cross-scope record, no requester-id leak, `all` read-only.

## B. Knowledge-learn approval

1. With the message/Zalo worker installed (`LEARN_REQUIRE_APPROVE=active`): a Zalo
   user asks to learn new knowledge. The host stages a pending item
   (`/v1/learn/submit`) and notifies the current admin with
   `Approve: !zalo learn approve <id>`; nothing is indexed before approval.
   The admin approves and the item becomes retrievable.
2. With no messaging channel (`LEARN_REQUIRE_APPROVE=inactive`): the default
   Hermes operator submits knowledge (`/v1/learn/scan`) and it is auto-ingested
   with no approval step.
3. With approval active, a scan does not auto-ingest; it stages pending and
   notifies the admin.

Pass criteria: a channel user cannot learn without admin approval, and no
channel means no approval is required.
