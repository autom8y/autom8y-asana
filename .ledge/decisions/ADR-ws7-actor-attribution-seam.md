---
artifact_id: ADR-ws7-actor-attribution-seam
title: "WS-7 actor-attribution seam: audit must name the human on the reactive axis"
created_at: "2026-07-23T10:05:00Z"
author: structure-evaluator (arch co-seat)
status: proposed
type: decision
schema_version: "1.0"
consumption_predicate: SHAPE
phase: "design-only (VISIONARY / Phase-2 precondition) — NO production code"
evidence_ceiling: MODERATE  # design-reasoning over a self-authored option slate; self-ref-evidence-grade-rule
context: >
  Request-triggered actions carry sub=human + act=agent from an inbound RFC-8693 JWT,
  but event-woken (SQS / polling / webhook) actions have NO inbound JWT. The Phase-2
  K3/WS-4 consumption+audit schema therefore risks locking an attribution model that
  names only request-triggered humans and structurally forecloses event-actor
  attribution — audit would stop naming the human the moment an action is reactive.
decision: >
  The Phase-2 consumption/audit schema MUST carry BOTH sub=human (delegating_user) and
  act=agent (acting_agent) for EVERY authorized action, request- OR event-triggered.
  Event-woken actions carry the delegated identity via a durable delegation-grant
  REFERENCE embedded in the EventEnvelope, re-exchanged to a fresh token at action time
  (NOT a live bearer token stored in the envelope). The human-named audit-of-record row
  is written cross-repo in the auth service audit_log (acting_agent_id / delegating_user_id),
  never in autom8y-asana, which has no persistence layer. The schema MUST NOT be locked
  until an actor-modeling claims contract exists SDK-side.
consequences:
  - type: positive
    description: "Audit-names-the-human is preserved on the reactive axis, not only the request axis; the K3 schema lock cannot silently drop the human for event-woken agent actions."
  - type: positive
    description: "The recommended grant-reference carrier keeps the EventEnvelope thin (ADR-GAP03-003) and avoids storing bearer secrets at rest in SQS."
  - type: negative
    description: "Action-time grant re-exchange introduces a runtime dependency on the auth/grant substrate at action-execution time (an availability coupling and a fail-open/fail-closed decision for Phase-2)."
    mitigation: "Phase-2 must decide the attribution-unavailable policy explicitly; surfaced here as an open question, not decided in this SHAPE ADR."
  - type: neutral
    description: "The seam requires a new EventEnvelope field and a cross-repo grant store; both are Phase-2 build items this ADR constrains but does not implement."
related_artifacts:
  - "autom8y: services/auth/autom8y_auth_server/routers/tokens.py (agent_token_exchange, RFC-8693)"
  - "autom8y: services/auth/autom8y_auth_server/models/audit_log.py (audit-of-record columns, migration 028)"
  - "autom8y: sdks/python/autom8y-auth/src/autom8y_auth/claims.py (fleet token-contract gap)"
  - ".know/feat/webhooks.md (webhook_dispatcher bypass constraint)"
tags:
  - security
  - auth
  - delegation
  - audit
  - event-driven
  - ws7
  - phase-2-precondition
---

# ADR — WS-7 actor-attribution seam: audit must name the human on the reactive axis

- **Date**: 2026-07-23
- **Rite / seat**: arch co-seat (structure-evaluator), design-only sprint D1
- **Slug**: ws7-actor-attribution-seam
- **Consumption-predicate**: **SHAPE** — ensures audit-names-the-human extends to the reactive axis; prevents a Phase-2 (K3/WS-4) schema lock from foreclosing event-actor attribution.
- **Scope guard**: This ADR is **DESIGN-ONLY**. It designs the seam and constrains the future schema. It does **NOT** build the reactive consumer, the grant store, the EventEnvelope field, or any migration. No production code accompanies it.
- **Evidence ceiling**: **MODERATE** per `self-ref-evidence-grade-rule` — this is design reasoning over a self-authored option slate; the file:line facts below are directly probed (SVR), but the recommendation itself is an argued design choice, not an empirically validated outcome. STRONG requires an independent Phase-2 build + a rite-disjoint attestation.
- **SVR note**: Every file:line anchor in §5 and §10 was re-derived by direct read at authoring time against `origin/main` @ `8e77c9a0` (autom8y-asana) and the sibling `autom8y` monorepo working tree. Where a design input handed to this sprint did not resolve on direct probe, the discrepancy is recorded verbatim in §10 rather than propagated.

---

## 1. Context — the delegation asymmetry

The fleet has a working answer for "who did this?" on the **request axis**. When a human drives an agent through an HTTP request, the auth server mints an RFC-8693 delegation token: `sub` = the delegating human, `act` = the acting agent. That token rides the inbound request, and the action it authorizes can be audited against both identities.

Event-woken actions have **no inbound HTTP request and therefore no bearer JWT**. In autom8y-asana the reactive axis is:

- SQS-delivered events (the `EventTransport` / SQS-direct-via-boto3 path), and
- polling-evaluated triggers (`TriggerEvaluator`), and
- (nominally) inbound webhooks.

When an agent acts because a *rule fired* — a task went stale, a deadline approached, a webhook arrived — there is no token in scope. Today the `EventEnvelope` carries a `source` provenance **string** (e.g. `"save_session"`, `"webhook_inbound"`) but **no delegated identity** (§5.4). So the reactive path can name the *mechanism* that woke it, but it cannot name the *human on whose behalf* the agent is acting.

This is a **bounded-context boundary problem** [DP:SRC-005 Evans 2003] [MODERATE]: identity is an auth-domain concept that today only crosses into the action domain through the request boundary. The reactive boundary has no identity contract crossing it. If the Phase-2 K3/WS-4 consumption+audit schema is locked while that gap stands, it will encode "attribution = the request's token," and the reactive axis will be permanently second-class: agent actions triggered by events will be attributable to an agent (or a service) but not to a human.

**The construct this ADR constrains**: "actor attribution" = the pair (delegating human, acting agent) recoverable for *every* authorized action regardless of what woke it. An attribution schema that can represent this pair only when an inbound JWT is present **under-represents the construct** [AV:SRC-001 Messick 1989] [STRONG] — it measures request-axis attribution and silently omits reactive-axis attribution.

---

## 2. Decision — the actor-attribution schema constraint (normative)

### 2.1 The constraint (SHAPE-level, binding on Phase-2)

> **C-1.** The Phase-2 K3/WS-4 consumption+audit schema **MUST** carry BOTH `sub` = human (delegating_user) AND `act` = agent (acting_agent) for **every authorized action**, whether request-triggered or event-triggered. No authorized action may be recorded with an agent identity alone, or a service identity alone, when it was in fact performed by an agent on behalf of a human.

> **C-2.** Request-triggered actions derive `(sub, act)` from the inbound RFC-8693 delegation token (the existing `agent_token_exchange` mint — §5.2). This path already works and is not re-designed here.

> **C-3.** Event-triggered actions, which have no inbound token, derive `(sub, act)` by dereferencing a **durable delegation grant** that is *referenced* from the `EventEnvelope`. The grant is established when a human authors/owns the automation rule or subscription that will later fire; the reference travels with the event; the concrete token is minted fresh **at action time**, not carried in the message. (Carrier options and the recommendation are in §3.)

> **C-4.** The human-named audit-of-record row **MUST** be written by a component that holds persistence. autom8y-asana holds none (§5.4); the row of record is the auth service `audit_log` (`acting_agent_id` / `delegating_user_id`, §5.2). The K3 consumption schema MUST carry both columns end-to-end so the cross-repo write is not lossy.

> **C-5.** The schema **MUST NOT be locked** until an actor-modeling claims contract exists SDK-side (§4, PRECONDITION-1). Locking `(sub)`-only today would foreclose `(sub, act)` tomorrow.

### 2.2 What this deliberately does not decide

Remediation ordering, the concrete grant-store technology, the EventEnvelope field name/type, and the fail-open-vs-fail-closed attribution policy are **out of scope** for this SHAPE ADR. They belong to Phase-2 build and to the remediation-planner. §9 records the intent questions that must be answered by a human before Phase-2 locks them.

---

## 3. Options — carrying the delegated identity onto an event-woken action

The problem C-3 must solve: an event-woken action has no inbound JWT; how does the `(sub=human, act=agent)` pair reach it? Four options, with the trade-off each one makes.

### Option A — Delegation-grant *reference* in the envelope, re-exchanged at action time  *(RECOMMENDED)*
The `EventEnvelope` carries a **stable reference** (e.g. `delegation_grant_ref`) to a durable delegation grant. The grant is minted when a human authors/owns the automation rule or subscription and is stored in the cross-repo grant/audit substrate. At action time the consumer dereferences the grant and re-exchanges it (via the existing `agent_token_exchange` machinery) to obtain a fresh `(sub, act)` token.
- **Pros**: envelope stays thin (honors ADR-GAP03-003, §5.4); no token-expiry problem (token minted fresh at action time); no bearer secret stored at rest in SQS; revocation is centralized (revoke the grant); the human of record is the rule's owner, which matches the causal reality of a rule-fired action.
- **Cons**: an action-time dereference/re-exchange round-trip to the grant/auth substrate (a runtime coupling and availability dependency); requires a new grant store (cross-repo, since autom8y-asana has no DB).

### Option B — Live delegation *token* embedded in the envelope
The wake payload carries the RFC-8693 delegation token itself; the agent re-presents it at action time.
- **Pros**: self-contained; no dereference round-trip; directly reuses the minted token.
- **Cons**: **violates thin-payload ADR-GAP03-003**; **token-expiry**: SQS/polling latency routinely exceeds token TTL, so the token is frequently dead by action time; **secret-at-rest**: a bearer token sitting in an SQS message is a credential-exposure surface (a security cross-rite concern, §8); no clean revocation. **Rejected.**

### Option C — Rule-owner identity resolved from the rule record (no envelope identity at all)
The automation rule / subscription record durably stores its `(human owner, agent)` pair. The event carries only its triggering `rule_id`; the action resolves `(sub, act)` from the rule record.
- **Pros**: matches causal semantics; no token lifecycle in the message; revocation = disable/reassign the rule.
- **Cons**: attribution granularity is *rule-owner*, which may differ from the specific human who caused a given event; still needs a persistence-holding component to store the pair and write the audit row. **This is the identity *source* that Option A's grant reference points at** — A and C compose rather than compete.

### Option D — Service identity + provenance-only  *(status quo / null option — the anti-pattern)*
Event-woken actions run under autom8y-asana's own service token; audit records only the `source` string. No human is named.
- This is essentially today's state (§5.4) and is exactly the outcome C-1 exists to prevent. Included as the rejected baseline: it **forecloses** audit-names-the-human on the reactive axis. **Rejected.**

### Recommendation
**Adopt Option A** (delegation-grant reference in the envelope, re-exchanged at action time), sourced by **Option C**'s rule-record `(human, agent)` pair. Concretely: the rule/subscription record is the durable grant (C), the `EventEnvelope` carries a thin reference to it (A), and the token is minted fresh at action time from that grant (A). **Reject Option B** (token-in-envelope) on thin-payload, token-expiry, and secret-at-rest grounds. **Reject Option D** (service-only) because it is the foreclosure this seam exists to prevent.

Rationale: Option A is the only option that simultaneously (i) preserves the thin-payload invariant the event system was designed around (§5.4), (ii) avoids a credential-at-rest security surface, (iii) survives the latency of the SQS/polling wake without a dead-token failure, and (iv) keeps autom8y-asana persistence-free by locating the grant store and the audit write in the repo that already owns them (§5.2, §5.4). Its one real cost — an action-time availability dependency on the grant substrate — is a trade-off surfaced explicitly in §6 and left for Phase-2 to resolve as a policy choice.

---

## 4. Phase-2 / K3 preconditions (the schema-lock guard)

These are the named conditions that must hold before the K3/WS-4 consumption+audit schema is locked, so that a lock does not foreclose event-actor attribution.

- **PRECONDITION-1 — SDK actor-claim contract (the fleet gap).** An `act` / actor-modeling claims contract MUST exist in the `autom8y_auth` SDK claims module before the K3 schema is locked. Today the SDK models `BaseClaims` / `ServiceClaims` / `UserClaims` and **none carries an `act` claim** (§5.1). Until the SDK models the actor claim, a K3 lock would encode only `sub` and would have no typed contract for `act` — foreclosing event-actor attribution at the type level. **K3 MUST NOT lock the actor column set until this SDK contract lands.**
- **PRECONDITION-2 — EventEnvelope identity seam.** The `EventEnvelope` MUST gain a thin delegation-grant reference field (a `grant_ref` string, honoring ADR-GAP03-003) so event-woken actions have a carrier for the `(human, agent)` pair. Without an envelope field there is no seam on the reactive axis (§5.4).
- **PRECONDITION-3 — Cross-repo audit-of-record binding.** Because autom8y-asana has no DB/ORM/migration layer (§5.4), the human-named row is written in the auth service `audit_log` (`acting_agent_id` / `delegating_user_id`, §5.2). Phase-2 MUST bind the event-woken action's grant dereference to a persistence-holding component and MUST carry BOTH columns through the K3 consumption schema so the cross-repo write is not lossy. (Note the observed column type asymmetry in §8.)
- **PRECONDITION-4 — Do-not-assume-the-dispatcher constraint.** The lifecycle `webhook_dispatcher` is presently **bypassed** (a `dispatch()` vs `handle_event()` Protocol/signature mismatch — §5.3). The identity seam MUST ride the `EventEnvelope` / SQS transport and the polling `TriggerEvaluator` path, and MUST NOT depend on the webhook dispatcher being wired. A Phase-2 design that installs the grant reference only in the dispatcher would be inert until an unrelated adapter is built.

---

## 5. Design constraints (verified facts)

### 5.1 Fleet SDK token-contract gap — no `act` claim
`sdks/python/autom8y-auth/src/autom8y_auth/claims.py` (379 lines) models the claims classes `BaseClaims` (`:110`), `ServiceClaims` (`:142`), and `UserClaims` (`:272`). A full-module grep for `act` / `actor` / `on_behalf` / `impersonat` returns **no actor field** on any claims class (the only near-hit is a UserClaims docstring at `:289` that *mentions* a "delegated-agent path" without modeling it structurally). The fleet token-contract has no way to carry `act` = agent. This is the load-bearing gap behind PRECONDITION-1.

### 5.2 Cross-repo audit-of-record reality — where the human-named row is written
The human→agent mint exists auth-server-side: `services/auth/autom8y_auth_server/routers/tokens.py:403` `agent_token_exchange` is the RFC-8693 exchange (`sub` = the delegating human, taken from `current_user["sub"]`; the acting agent verified against `agent_registrations`; single-hop). The audit substrate lives at `services/auth/autom8y_auth_server/models/audit_log.py`: `acting_agent_id` (`:45`, `String(255)`) and `delegating_user_id` (`:46`, `uuid.UUID`), the columns the class docstring (`:5`) names as `(acting_agent_id, delegating_user_id)`, with partial indexes at `:73`–`:79`. **This substrate is in the `autom8y` monorepo, not in autom8y-asana.** The human-named row of record is written *there*.

### 5.3 Event-path bypass — do not assume the webhook dispatcher
`.know/feat/webhooks.md:100` records the "Critical gap": the inbound route calls `_dispatcher.dispatch(task: Task)` via the `WebhookDispatcher` Protocol, but `LifecycleWebhookDispatcher` exposes `handle_event(event_type, entity_type, entity_gid, payload)` — a **different signature** — and does **not** implement `dispatch()`. The `set_dispatcher()` seam therefore requires an adapter that is not yet implemented, and the module-level default remains `NoOpDispatcher` (logs and discards). The lifecycle dispatcher that would route to `AutomationDispatch.dispatch_async()` is **bypassed**. The seam in this ADR must not assume it is wired (PRECONDITION-4).

### 5.4 autom8y-asana has no persistence layer; the envelope is thin and identity-free
- **No DB/ORM/migration layer**: no `alembic.ini`, no `migrations/` directory, no `sqlalchemy` import in `src/`, and no DB driver in `pyproject.toml`. autom8y-asana cannot write the audit-of-record row locally — hence the cross-repo write in C-4 / PRECONDITION-3.
- **Thin, identity-free envelope**: `src/autom8_asana/automation/events/transport.py:4` documents "Per ADR-GAP03-004: SQS direct transport via boto3." The `EventEnvelope` (`src/autom8_asana/automation/events/envelope.py:35`–`:44`) carries `schema_version, event_id, event_type, entity_type, entity_gid, timestamp, source, correlation_id, causation_id, payload` under "Per ADR-GAP03-003: Thin payloads (GID + metadata only)." It has a `source` provenance string but **no `sub`, no `act`, no grant reference** — there is no identity carrier on the reactive axis today. `src/autom8_asana/automation/polling/trigger_evaluator.py` evaluates stale/deadline/age triggers against tasks and likewise wakes actions with no inbound token.

---

## 6. Trade-offs surfaced (ATAM)

Per ATAM, an attribution decision is incomplete without naming the quality-attribute trade-off it makes [AQ:SRC-003 Kazman et al. 2000] [STRONG].

- **Auditability (name the human) vs. thin-payload/decoupling (ADR-GAP03-003) vs. security (secret-at-rest).** Option B maximizes self-containment but sacrifices thin-payload and creates a credential-at-rest surface. Option A preserves both at the cost of an action-time dereference. The recommendation weights **auditability + security** over **execution-time independence**.
- **Attribution completeness vs. action-time availability (a SPOF consideration).** Option A introduces a dependency on the grant/auth substrate *at action-execution time*. If that substrate is unavailable, the event-woken action must either block (an availability hit) or proceed unattributed (an attribution hit). This is a genuine fail-closed-vs-fail-open trade-off that Phase-2 must decide; it is **not** decided here (§9). Naming it is required so the K3 builder does not encounter it as a surprise.
- **Attribution granularity vs. simplicity.** Option C's rule-owner granularity is simpler but may not equal the specific human who triggered a given event. The recommendation accepts rule-owner granularity as the Phase-2 default while leaving finer granularity open (§9).

---

## 7. Consequences

**Positive**
- Audit-names-the-human is preserved on the reactive axis; a K3 schema lock cannot silently demote event-woken agent actions to human-less attribution.
- The recommended carrier keeps the `EventEnvelope` thin and keeps bearer secrets out of SQS.
- The cross-repo audit-of-record reality is made explicit, so Phase-2 does not attempt (and fail) to write the row in a repo with no persistence.

**Negative**
- Action-time grant re-exchange couples action execution to the availability of the grant/auth substrate (mitigation: Phase-2 policy decision, §9).
- The seam requires two Phase-2 build items (an EventEnvelope field and a cross-repo grant store) that do not exist yet.

**Neutral**
- The request axis is unchanged; only the reactive axis gains a new identity carrier.
- The recommendation composes two options (A carrier + C source) rather than selecting a single mechanism.

---

## 8. Cross-rite observations (for remediation-planner → security)

Noted as observations, **not** audited here (structure-evaluator does not run security analysis):
- **Secret-at-rest**: Option B (rejected) would place bearer tokens in SQS messages — a credential-exposure surface for a security review if ever reconsidered.
- **Delegation-grant revocation & TTL**: the grant store implied by Option A needs a revocation and expiry model; that is a security-domain design question.
- **Audit-column type asymmetry (FW-A3 type-drift)**: `acting_agent_id` is `String(255)` while `delegating_user_id` is `uuid.UUID` (`audit_log.py:45`–`:46`). The K3 schema should be aware of this asymmetry so the cross-repo write does not silently coerce or truncate. Flagged for the owning rite; not adjudicated here.

---

## 9. Unknowns (escalate to human — intent questions Phase-2 must not silently answer)

### Unknown: Attribution-unavailable policy (fail-open vs fail-closed)
- **Question**: When the grant/auth substrate is unavailable at action time, must the event-woken action block (fail-closed on attribution) or proceed unattributed (fail-open)?
- **Why it matters**: it is the difference between an availability incident and an audit gap; it changes the SLA of the reactive path and the meaning of the audit record.
- **Evidence**: Option A's action-time dereference (§3) creates the dependency; nothing in the current event path (§5.4) implies a policy.
- **Suggested source**: product/compliance owner of the audit requirement + Phase-2 architect.

### Unknown: Attribution granularity (rule-owner vs event-triggerer)
- **Question**: Is rule-owner attribution sufficient, or must the specific human who caused a given event be named when they differ?
- **Why it matters**: determines whether the grant is rule-scoped (Option C) or must carry finer per-event identity.
- **Evidence**: Option C grants rule-owner granularity; the envelope's thin payload (§5.4) does not carry a per-event human today.
- **Suggested source**: the human who defines the audit/attribution requirement.

### Unknown: Is the SDK `act` contract owned by autom8y or a shared SDK release?
- **Question**: Who lands PRECONDITION-1's SDK actor-claim contract, and on what release cadence, given it gates the K3 lock?
- **Why it matters**: the K3 schema cannot lock until it exists; this is a cross-repo sequencing dependency.
- **Evidence**: §5.1 — the gap is in the shared `autom8y-auth` SDK, consumed fleet-wide.
- **Suggested source**: fleet auth/SDK owner.

---

## 10. Evidence anchors (SVR) and provenance corrections

**Directly verified at authoring time** (`origin/main` @ `8e77c9a0` for autom8y-asana; sibling `autom8y` working tree for cross-repo):

| Claim | Anchor | Method |
|---|---|---|
| SQS-direct transport, thin payloads | `src/autom8_asana/automation/events/transport.py:4` | file-read |
| Envelope carries `source` but no identity field | `src/autom8_asana/automation/events/envelope.py:35`–`:44` | file-read |
| Polling trigger evaluator wakes actions without a token | `src/autom8_asana/automation/polling/trigger_evaluator.py:1`–`:20` | file-read |
| webhook_dispatcher bypassed (dispatch/handle_event mismatch) | `.know/feat/webhooks.md:100` | file-read |
| autom8y-asana has no DB/ORM/migration layer | `pyproject.toml` (no db deps); no `alembic.ini`/`migrations/`/`sqlalchemy` in `src/` | bash-probe (grep/find negative) |
| RFC-8693 human→agent mint (sub=human) | `autom8y: services/auth/autom8y_auth_server/routers/tokens.py:403` | file-read |
| Audit-of-record columns | `autom8y: services/auth/autom8y_auth_server/models/audit_log.py:45`–`:46` (+ docstring `:5`, indexes `:73`–`:79`) | file-read |
| SDK claims classes; no `act` field | `autom8y: sdks/python/autom8y-auth/src/autom8y_auth/claims.py:110/142/272`; grep-negative for `act`/`actor` module-wide | file-read + bash-probe |

**Provenance corrections (design inputs handed to this sprint that did not resolve on direct probe — recorded, not propagated):**
- Design input #1 cited the SDK classes as `BaseClaims/ServiceClaims/UserClaims/OperatorClaims` at `claims.py:133/165/295/401`. On direct probe the classes resolve at `:110/:142/:272`; the cited lines `:133/:165/:295` are *field* lines inside those classes, and `:401` is **beyond EOF** (the file is 379 lines). **No `OperatorClaims` class exists** in the SDK module (grep-negative). The load-bearing claim — *no claims class models an `act`/actor field* — is confirmed; the anchors above supersede the input's line numbers.
- Design input #2 located the audit substrate under "`autom8y-auth models/audit_log.py`." The resolved path is `services/auth/autom8y_auth_server/models/audit_log.py` (auth-server, not the SDK). Columns and lines otherwise confirmed exactly.
- Design input #3 described the live inbound route as going "straight to automation_dispatch." Direct probe shows the lifecycle dispatcher that routes to `AutomationDispatch.dispatch_async()` is **not** wired (the module default `_dispatcher` is `NoOpDispatcher`, which discards); the reactive wake that reaches automation today is the SQS `EventTransport` + polling `TriggerEvaluator` path. The design-constraint intent — *do not assume the webhook dispatcher is wired* — is confirmed and carried as PRECONDITION-4.

---

## 11. References
- RFC 8693 — OAuth 2.0 Token Exchange (the `act` claim / delegation model).
- ADR-GAP03-003 — thin event payloads (GID + metadata only).
- ADR-GAP03-004 — SQS direct transport via boto3.
- `.know/feat/webhooks.md` — webhook dispatch seam and the bypass gap.
- Domain grounding: bounded-context boundaries [Evans 2003]; ATAM quality-attribute trade-offs [Kazman et al. 2000]; construct validity / under-representation [Messick 1989].
