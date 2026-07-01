---
type: decision
status: proposed
id: ADR-0040
title: Insights-Export Drift Elimination (Lever-1) — O_asana ↔ O_data Source Alignment
date: 2026-06-29
authoring_rite: 10x-dev
authoring_agent: architect
security_gate: ADR-0040 (this is the SEAM-2 10x-dev→security input artifact)
ratification_required_by: [threat-modeler, security-reviewer]
supersedes: none
relates_to:
  - d801dbcd (Lever-2, branch 10xdev/insights-export-batch-backoff-cure — CONTAINS, does not eliminate)
  - ADR-AUTH-MULTI-TARGET-OPERATOR-PLANE-004 (operator-plane authorization)
  - ADR-account-status-state-projection (account-status sync pipe)
complexity: SYSTEM
---

# ADR-0040: Insights-Export Drift Elimination (Lever-1)

> **GRANDEUR ANCHOR (verbatim):** "We are 10x-dev, drafting the DURABLE fix that
> ELIMINATES the insights-export drift at its source — so the partner's report
> needs no bounded-bisection containment — under the all-or-nothing
> existence-oracle and the 10/min DoS guard, both INVIOLATE. DESIGN ONLY (an ADR
> draft for security ratification); we do NOT build (Lever-1 is
> ADR-0040-security-gated)."

> **DESIGN ONLY.** This ADR is the input to the SEAM-2 (10x-dev → security)
> handoff. No code is built under this document. The recommended option is
> buildable ONLY after the security rite (threat-modeler → security-reviewer)
> ratifies the §7 security-ratification criteria. The existence-oracle is NOT
> weakened by any recommendation herein.

---

## 1. Context

### 1.1 The defect (the partner-report symptom)

The cross-tenant BI insights-export (operator/asana fleet-read) self-limits to
**0 rows served** when the office set it enumerates contains even one office the
data plane does not recognize. A single ownership-drift office trips the route's
all-or-nothing 404, which the asana client historically answered with an O(N)
per-office re-probe sweep (`4·(1+N) ≈ 64` wire calls/run) that breaches the
`10/min` `LIMIT_HEAVY_ANALYTICS` guard, so ~54 calls `429` and the partner's
deck is empty.

### 1.2 The two sets and the drift

| Symbol | Definition | Source of truth | Anchor (verified) |
|--------|-----------|-----------------|-------------------|
| **O_asana** | The active-Offer office set the insights-export enumerates | Asana **OFFER project** tasks classified `ACTIVE` by **section name** via `OFFER_CLASSIFIER` | `autom8y-asana src/autom8_asana/automation/workflows/insights/workflow.py:417-441` (`_enumerate_offers`); per-office resolution `:481-525` |
| **O_data** | Data's owned set the route resolves against | DB `account_status` rows where `pipeline_type='unit'`, joined on `office_phone` | `autom8y-data src/autom8_data/core/repositories/business.py:186` (`AccountStatus.pipeline_type == "unit"`); recurs at :263/:320/:400 |

The drift `O_asana \ O_data` is the set of offices that are **active OFFERS in
Asana** but have **no active `unit` `account_status` row in the data DB**. This
drift fires the all-or-nothing 404 → the sweep.

### 1.3 ROOT CAUSE — a grain mismatch, not a sync lag (decisive finding)

The drift is **not merely** "asana's view is stale relative to data's view." The
two sets are computed from **different Asana projects at different pipeline
grains**:

- **O_asana** enumerates the **OFFER** project (`OFFER_PROJECT_GID`,
  `OFFER_CLASSIFIER`) — `workflow.py:417`.
- **O_data** (`pipeline_type='unit'`) is populated by asana's own cache-warmer
  from the **Business Units** project
  (`PIPELINE_TYPE_BY_PROJECT_GID = {"1201081073731555": "unit"}`,
  `autom8y-asana src/autom8_asana/services/gid_push.py:326`), pushed to data via
  `POST /api/v1/account-status/sync` (`gid_push.py:529`).

So the export asks data for offices selected by **Offer-activity**, but data's
ownership predicate keys on **Unit-activity**. An office can be Offer-active yet
Unit-absent (never warmed as a `unit`, or unit-inactive). **That structural
grain gap is the drift.** Any Lever-1 that only "syncs faster" without
reconciling the grain will leave residual drift.

### 1.4 The reconciliation substrate ALREADY EXISTS (keystone finding)

A snapshot-replace pipe from asana → data is **already in production**:

- **Producer (asana):** `cache_warmer.py:1073-1078` → `push_orchestrator.py:129`
  (`_push_account_status_for_completed_entities`) → `gid_push.py:476-529`
  (`push_account_status`, `POST /api/v1/account-status/sync`). The warmer
  classifies each `(phone, vertical)` row with the **same** `SectionClassifier`
  family (`get_classifier(entity_type)`, `gid_push.py:397`) and emits
  `{phone, vertical, pipeline_type, account_activity, pipeline_section,
  stage_entered_at}` (`gid_push.py:376`).
- **Receiver (data):** `POST /api/v1/account-status/sync`
  (`autom8y-data src/autom8_data/api/data_service_models/_account_status_sync.py`,
  docstring: "Receives account status snapshots pushed by autom8_asana's cache
  warmer"). `AccountStatusEntry` carries `pipeline_section` (= raw Asana section
  name) and `account_activity`.
- **Store (data):** `account_status_store.py:67` — `DELETE FROM account_status
  WHERE source = :source` then bulk INSERT — a **source-keyed snapshot replace**.

This means O_data is **already a projection of an Asana classification** — just a
*different* one (Unit) than O_asana (Offer). The fix is to make the two
projections coherent, NOT to invent a new cross-tenant read path.

### 1.5 The named security invariant (INVIOLATE)

The **all-or-nothing existence-oracle** is a deliberate security control. Its
canonical implementation is the operator-plane recognizer:

- `authorize_targets(claim, selected_guids, required_verb)` —
  `autom8y-data src/autom8_data/api/auth/operator_plane.py:348`. It is **pure set
  membership** of *server-derived* guids against the **mint-validated carried
  set** `claim.authorized_sets` (NOT a request-time recompute of O), plus a verb
  conjunct. Contract clause 3 (`operator_plane.py` docstring): "**All-or-nothing
  membership.** Any selected guid outside the carried set denies the WHOLE
  request (no partial grant; ... avoids a partial-result oracle)."
- Enforcement site (CA-compare route): `comparison.py:483` (`result =
  authorize_targets(...)`) → `:486` (`if not result.all_authorized:`) → bare
  `404` = `_ORACLE_404_DETAIL` (`comparison.py:141`). The `denied` set goes to an
  append-only audit sink ONLY; the HTTP body is byte-identical to a genuine
  absence (`comparison.py:486-500`).

**Rationale (verbatim intent):** "pre-intersecting selected ∩ O would let a
partial batch silently succeed." A partial success is itself an oracle: it tells
the caller *which* offices it does/does not own. The all-or-nothing 404 denies
that signal.

### 1.6 Oracle-topology correction (load-bearing — the mandate conflated two routes)

The mandate names `comparison.py:434/482 authorize_targets` as the oracle the
export's sweep reacts to. **Verified ground truth: the insights-export does NOT
ride that route.**

- `comparison.py` is the **CA-compare** route — verb `analytics:compare`,
  `authorize_targets` against the carried set. The export does not call it.
- The **insights-export batch** hits `POST /api/v1/data-service/insights` →
  `autom8y-data src/autom8_data/analytics/routes/data_service.py:298`
  (`post_insights`). The operator/asana export rides the
  **`is_fleet_read(request)`** branch (`data_service.py:341`), which **SKIPS** the
  own-tenant PVP intersect so the full `phone_vertical_pairs` batch is honored
  fleet-wide. `is_fleet_read` reads `request.state.bypass_scope`, set ONLY by the
  autom8y-auth SDK on an FGA-gated bypass SA — a tenant token can never set it
  (`autom8y-data src/autom8_data/api/auth/fleet_read_admission.py:48-74`). The
  all-or-nothing 404 the EC-4 sweep reacts to is **this fleet-read batch path's**
  failure on a drift office.

**Why this matters for Lever-1:** `authorize_targets` is the *named invariant and
the design precedent* ("no partial silent success") that any alignment mechanism
must honor — but the export's enforcement point is the fleet-read batch route, not
the CA recognizer. A Lever-1 mechanism is "oracle-safe" iff it neither (a)
introduces a partial-success path on the fleet-read batch nor (b) emits the
membership of O (which offices are/are not owned) to any non-operator surface.
Both oracles share the SAME safety property; Lever-1 must preserve it on both.

### 1.7 Lever-2 relationship (already shipped, CONTAINS)

`d801dbcd` (branch `10xdev/insights-export-batch-backoff-cure`, **not** merged to
asana HEAD `chore/bump-core-4.6.0`) replaces the linear sweep with a bounded
bisection under a run-shared `OperatorCallPacer` capping aggregate wire calls at
`B_run=9 < 10`. Its commit message states: "G-NO-FALLBACK and the existence-oracle
invariant are untouched; the data plane is not modified." **Lever-2 makes the
drift survivable (the export self-limits under the guard); it does NOT eliminate
the drift.** With drift still present, the export still serves a *subset* (the
owned half of each bisected branch) — better than 0 rows, but not the full deck.
Lever-1 is the durable fix that makes the batch `200` in 4 calls with no sweep.

---

## 2. Decision

**Adopt Option 3 — Shared reconciliation source-of-truth, realized by extending
the EXISTING account-status sync pipe to carry the OFFER-grain active set so that
`O_data ⊇ O_asana` by construction.**

Concretely: asana's cache-warmer — which **already** classifies Asana projects
and pushes `account_status` snapshots to data (`gid_push.py:529`) — additionally
projects the **Offer** project's active set into the data DB through the **same
source-keyed snapshot-replace pipe** (`/api/v1/account-status/sync`,
`account_status_store.py:67`), under a distinct `source` and the existing
`pipeline_type`/`account_activity` schema. The insights-export route's ownership
predicate is then satisfied for every office in O_asana because the **same Asana
classification that produced O_asana also produced the O_data rows** — they can no
longer drift, because they are projections of one enumeration through one pipe.

**Decisive reason:** Option 3 is the only option that (a) eliminates drift at the
**source** (the grain mismatch of §1.3), (b) requires **zero new request-time
read path** and therefore cannot leak the owned-set or weaken either oracle (the
oracle still receives a fully-pre-populated O and still answers all-or-nothing —
it is never asked to partial-succeed), (c) **reuses an already-deployed,
already-security-reviewed pipe** (`/account-status/sync`) rather than minting new
attack surface, and (d) is `10/min`-guard-neutral because reconciliation runs on
the warmer's existing schedule, entirely out-of-band from the export's
per-identity heavy-analytics budget. It is the design that "looks obviously right
in 18 months": the two sets are *defined* to agree, not *reconciled* after the
fact.

The competing options either move the owned-set membership decision onto a new
request-time path (Options 1, 2 — owned-set leakage and oracle-coupling risk) or
relax the all-or-nothing answer toward a drift-disclosing partial (Option 4 —
direct oracle weakening, **rejected**).

---

## 3. Options Considered

Four genuinely distinct alignment architectures. Each represents a different
*locus* of the alignment (producer-side pre-filter, request-time enumeration
endpoint, shared source-of-truth, or response-time drift disclosure) — not the
same design re-parameterized.

### Option 1 — Asana pre-filters O_asana to O_data BEFORE the batch

Asana learns O_data (a new asana→data read of the owned set) and sends only
`O_asana ∩ O_data` in the batch.

- **Mechanism:** new asana client call to a data "is-this-office-owned?" or
  "give-me-the-owned-set" read, invoked before `_enumerate_offers` hands off the
  batch; asana drops drift offices client-side.
- **Existence-oracle impact:** **WEAKENS by relocation.** The membership decision
  (`office ∈ O`) moves from the server-side oracle to an asana-side pre-filter.
  Whatever surface answers "is this owned?" *is* the oracle, now exposed as an
  enumerable read. The route's all-or-nothing 404 becomes vestigial (asana
  pre-removed the drift), which means the real control now lives in the new read —
  and a read that returns the owned set is exactly the partial-success oracle the
  invariant exists to deny.
- **Cross-tenant existence leak:** **YES.** The owned-set read tells asana (and
  anything that can replay asana's credential) precisely which offices are/aren't
  owned — the canonical leak.
- **C-1 PII wall / DATA-VAL-003:** the new read would itself need fleet-read
  admission; it inherits the bypass-SA surface and widens it from "export
  insights" to "enumerate ownership." Net increase in what the fleet-read SA can
  do.
- **10/min guard:** adds a pre-batch round-trip per run; bounded but non-zero, and
  competes for the same heavy-analytics budget if routed through the guarded path.
- **Blast radius:** asana (new client method + pre-filter) + data (new owned-set
  read endpoint + its authz). Two-repo, new endpoint.

### Option 2 — Data exposes an authoritative O_data enumeration endpoint asana calls first

Data publishes `GET /owned-targets` (the authoritative active set); asana fetches
it and intersects before batching.

- **Mechanism:** new data route returning the enumerated owned set for the
  fleet-read principal; asana calls it, intersects, then batches.
- **Existence-oracle impact:** **WEAKENS — most directly.** This endpoint *is* the
  existence oracle materialized as a bulk read. The entire point of the
  all-or-nothing 404 is that O is never enumerable; a `/owned-targets` endpoint
  publishes O wholesale.
- **Cross-tenant existence leak:** **YES, maximal.** Returns the full owned set in
  one call.
- **C-1 PII wall / DATA-VAL-003:** the endpoint must be FGA-gated like every
  fleet-read; but even gated, it converts the oracle from "probe-and-get-404" to
  "list-everything," which is a strictly larger disclosure to any holder of the
  bypass SA.
- **10/min guard:** one extra call/run; modest.
- **Blast radius:** data (new endpoint, new authz, new audit) + asana (new client
  call). New attack surface on the data plane — exactly what ADR-0040 gating is
  meant to scrutinize.

### Option 3 — Shared source-of-truth / reconciliation (RECOMMENDED)

The two sets are made coherent at the source via the EXISTING account-status sync
pipe, so they cannot drift. (Full description in §2.)

- **Mechanism:** asana warmer projects the Offer-grain active set into data through
  `POST /api/v1/account-status/sync` (`gid_push.py:529`) under a distinct
  `source`; data's `account_status_store.py:67` snapshot-replaces it; the
  export's ownership predicate is satisfied for all of O_asana by construction.
  **No new endpoint, no new request-time read.**
- **Existence-oracle impact:** **NONE.** The oracle is never asked to
  partial-succeed and never enumerated. It still receives a server-derived O (now
  pre-aligned) and still answers all-or-nothing. The control is untouched; only
  the *contents* of O are made to cover O_asana.
- **Cross-tenant existence leak:** **NONE.** Reconciliation is an asana→data push
  on the warmer's existing trust path; no party learns the membership of O via any
  read. (Residual: see §8 R-2 — the sync payload itself crosses the asana→data
  boundary, but that boundary and payload already exist and are already reviewed.)
- **C-1 PII wall / DATA-VAL-003:** **preserved.** No SA-fallback is introduced; the
  export still rides the FGA-gated fleet-read bypass exactly as today
  (`fleet_read_admission.py:48-74`); the C-1 PII de-identification wall on the
  export payload is entirely unaffected (reconciliation moves *which offices
  exist*, never PII rows).
- **10/min guard:** **neutral.** Reconciliation runs on the warmer schedule,
  out-of-band from the per-identity `LIMIT_HEAVY_ANALYTICS` budget. The export
  itself then needs only its 4 batch calls (no sweep), strictly under the guard.
- **Blast radius:** asana (warmer projects one more set through an existing pipe) +
  data (accepts one more `source` through an existing endpoint/store). **No new
  endpoint, no new authz path.** Smallest security-relevant surface of the four.

### Option 4 — Route returns the drift-set in the 404 so asana self-corrects

On all-or-nothing failure, the route's 404 body enumerates the offending
(non-owned) offices; asana removes them and retries.

- **Mechanism:** enrich the `_ORACLE_404_DETAIL` body (or a sibling field) with the
  `denied` set; asana subtracts and re-batches deterministically.
- **Existence-oracle impact:** **DIRECTLY WEAKENS — this is the precise thing the
  invariant forbids.** `comparison.py:486-500` is explicit that `denied` goes to
  the audit sink ONLY and the body is byte-identical to a genuine absence
  *because* disclosing `denied` is a cross-tenant existence oracle.
- **Cross-tenant existence leak:** **YES, by design.** The drift-set response tells
  the caller exactly which requested offices it does not own — converting the 404
  into the membership oracle.
- **C-1 PII wall / DATA-VAL-003:** orthogonal, but the existence leak alone is
  disqualifying.
- **10/min guard:** would actually *reduce* calls (one corrective retry) — but at
  the cost of breaking the named control. Not a tradeoff we are permitted to make.
- **Blast radius:** data (oracle response contract change — a one-way security
  regression) + asana (consume drift-set). **REJECTED — violates the inviolable
  invariant.**

### 3.1 Option Matrix

| Option | Alignment locus | Weakens existence-oracle? | Cross-tenant existence leak? | C-1 PII / DATA-VAL-003 | 10/min guard interaction | Blast radius (security surface) |
|--------|-----------------|---------------------------|------------------------------|------------------------|--------------------------|---------------------------------|
| **1 — asana pre-filters via owned-set read** | asana request-time | YES (by relocation — pre-filter becomes the oracle) | YES (owned-set read) | widens bypass SA scope | +1 guarded-ish round-trip/run | asana + data **new read endpoint** |
| **2 — data O_data enumeration endpoint** | data request-time (new route) | YES (most directly — publishes O) | YES (maximal — bulk O) | gated but enlarges disclosure | +1 call/run | data **new endpoint + authz** + asana |
| **3 — shared source-of-truth (RECOMMENDED)** | source / out-of-band sync | **NO** | **NO** | **preserved (no SA-fallback)** | **neutral (out-of-band)** | asana + data **existing pipe only** |
| **4 — drift-set in 404** | data response-time | YES (**direct** — the forbidden disclosure) | YES (by design) | orthogonal but disqualified | −calls (irrelevant) | data **oracle contract regression** — REJECTED |

---

## 4. Why Option 3 over the runner-up

The runner-up is not Options 1/2/4 (all leak or weaken). The runner-up is the
**null option: ship Lever-2 only and accept residual drift.** Option 3 beats it
because Lever-2 leaves the partner deck *partial* (owned half of each bisected
branch) whenever drift is present, and the drift is **structural** (a grain
mismatch, §1.3) — it will recur every time an office is Offer-active but
Unit-absent, which is a permanent class, not a transient. Option 3 makes the deck
**complete and sweep-free** durably. The cost asymmetry is favorable: Option 3
reuses a deployed pipe (low build, low security-surface) to retire a recurring
operational failure.

---

## 5. Consequences

### 5.1 Positive
- Drift eliminated at source; export `200`s in 4 calls, no sweep, comfortably
  under `10/min`.
- Neither existence-oracle is touched, enumerated, or relocated.
- No new endpoint, no new authz path, no new fleet-read surface.
- Lever-2 (`d801dbcd`) remains valuable as **defense-in-depth**: even with Option
  3 live, the pacer caps any *future* drift (e.g., a sync gap window) strictly
  under the guard. The two levers compose; Option 3 does not obsolete Lever-2.

### 5.2 Negative / costs
- Adds an Offer-grain projection to the warmer's responsibilities and a new
  `source` partition in data's `account_status` (snapshot-replace is already
  source-keyed, so this is additive, not a schema migration of existing rows —
  **two-way door**).
- Introduces a *temporal* coupling: O_data covers O_asana only as fresh as the
  last successful sync. A sync failure re-opens a bounded drift window (mitigated
  by Lever-2 + §8 R-1).
- The export's ownership grain shifts from "Unit-active" toward "Offer-active ∪
  Unit-active" for the affected offices — a **product-semantics** change the
  requirements owner must confirm is intended (see §6 OQ-1).

### 5.3 Reversibility
- **Two-way door.** The new `source` projection can be disabled (stop pushing it;
  data's next snapshot-replace for that source clears it) without touching the
  oracle, the export route, or existing Unit rows. No public API contract changes.
  Contrast Option 4, which is a **one-way door** (an oracle-response disclosure,
  hard to walk back once consumers depend on it).

---

## 6. Open Questions (for requirements + security)

- **OQ-1 (requirements-analyst):** Is the intended ownership grain for the
  insights-export "active OFFER" or "active UNIT"? Option 3 aligns O_data toward
  O_asana (Offer); the alternative framing would align O_asana toward O_data
  (enumerate Units, not Offers). The *direction* of alignment is a product
  decision, not an architectural one. **This ADR assumes Offer-grain is correct
  because the export's user-visible artifact is the per-Offer deck**
  (`workflow.py:417` enumerates Offers); confirm.
- **OQ-2 (security):** Does projecting the Offer active-set into `account_status`
  change what any *other* consumer of `account_status WHERE pipeline_type=...`
  sees? The new rows must use a `source`/`pipeline_type` that the owned-set query
  (`business.py:186`, keyed on `pipeline_type='unit'`) will actually honor — which
  means either (a) the Offer projection writes `pipeline_type='unit'` rows (risk:
  pollutes the Unit set for non-export consumers) or (b) the export's predicate is
  widened to accept the Offer `pipeline_type` (a route change — see §7 C-3). This
  is the crux security/architecture question; §7 gates on it.

---

## 7. Security-Ratification Criteria (what the security rite MUST verify)

The recommended Option 3 is **buildable only after** the security rite confirms
ALL of the following. These are the conditions that make the chosen alignment
safe. (threat-modeler authors the verification; security-reviewer grants the
verdict per the ADR-0040 `Approve | Request-Changes | Reject` grammar.)

- **SR-1 (oracle non-relocation):** Confirm Option 3 introduces **no new
  request-time read** of the owned set and **no new enumeration endpoint** — i.e.,
  the membership decision stays exactly where it is today (server-side,
  all-or-nothing, on the fleet-read batch path `data_service.py:341` and on the
  CA recognizer `authorize_targets`/`comparison.py:483`). The reconciliation is
  push-only on the existing `/account-status/sync` pipe.
- **SR-2 (no partial-success path):** Confirm the export's fleet-read batch
  (`data_service.py:298`) still answers **all-or-nothing** after alignment — that
  making O_data ⊇ O_asana removes the *cause* of the 404, and does not add a code
  path where a partial batch silently succeeds. The all-or-nothing answer is
  preserved; we change inputs (O), never the recognizer.
- **SR-3 (no existence disclosure):** Confirm no surface (response body, log,
  metric, error) gains the ability to disclose which offices are/are not owned.
  Specifically confirm the 404 body remains `_ORACLE_404_DETAIL`
  (`comparison.py:141`) byte-identical to a genuine absence and that `denied`
  stays audit-sink-only (`comparison.py:486-500`).
- **SR-4 (account_status grain isolation — resolves OQ-2):** Confirm the Offer
  projection's `source`/`pipeline_type` choice does NOT corrupt the Unit owned-set
  for any *other* consumer of `account_status` (`business.py:186/263/320/400`,
  `messages.py:397`, `reconciliation.py:234/311`). Ratify EITHER (a) a distinct
  `pipeline_type` for the Offer projection **plus** an explicit, audited widening
  of the export route's predicate to accept it (a scoped data-route change), OR
  (b) a justification that writing into the Unit set is correct. The architect's
  default recommendation is **(a)** — keep the Unit set pure, widen only the
  export's predicate — because it confines the blast radius to the one route that
  needs it.
- **SR-5 (fleet-read bypass unchanged):** Confirm the FGA-gated fleet-read
  admission (`fleet_read_admission.py:48-74`, `request.state.bypass_scope` set only
  by the auth SDK on a bypass SA) is **not modified** and the bypass SA gains **no
  new capability** (it still only reads insights; it does not gain ownership
  enumeration). DATA-VAL-003 (no SA-fallback) holds — no new SA-fallback path is
  created.
- **SR-6 (C-1 PII wall intact):** Confirm the export payload's C-1 PII
  de-identification wall is untouched — reconciliation moves office-existence
  rows, never PII, and the export's per-row de-id path is byte-unchanged.
- **SR-7 (sync-trust integrity):** Confirm the `/account-status/sync` ingress
  authz is sufficient for the *additional* `source` (the producer is the same
  warmer principal; threat-model the case where the snapshot is spoofed/poisoned —
  a poisoned snapshot could *inflate* O_data, admitting an office into the owned
  set. Verify the sync ingress is authenticated such that only the warmer
  principal can write account_status, and that an inflated O_data still cannot
  exfiltrate cross-tenant PII because the export's per-tenant de-id wall (SR-6) is
  the actual PII control, not O membership). **This is the sharpest residual
  threat and the reason Lever-1 is SYSTEM-complexity / ADR-0040-gated.**
- **SR-8 (Lever-2 coexistence):** Confirm Option 3 + Lever-2 (`d801dbcd`) compose
  without the pacer masking a reconciliation failure (a silent sync gap that the
  pacer quietly absorbs as "partial deck" instead of surfacing). Verify a sync-gap
  drift is observably surfaced, not silently paced over.

**Buildable predicate:** SR-1…SR-8 all `Approve` (or `Approve` with attested
`signoff_conditions[]`). Any `Request-Changes` recedes to architect for redesign
of the affected criterion. `Reject` on SR-2/SR-3/SR-7 halts Lever-1 (the oracle
or the trust boundary cannot be made safe under the proposed mechanism).

---

## 8. Residual Risks

- **R-1 (temporal drift window):** O_data covers O_asana only as fresh as the last
  successful sync. A warmer/sync failure re-opens bounded drift. **Mitigation:**
  Lever-2 caps the cost of any such window under the guard (defense-in-depth); add
  a freshness/coverage signal (SR-8) so a stale sync is alarmed, not silently
  paced over. Severity: MODERATE (bounded, observable).
- **R-2 (sync payload boundary):** Option 3 pushes more data across the asana→data
  sync boundary. The boundary and payload schema already exist
  (`_account_status_sync.py`), so this is additive volume on a reviewed channel,
  not a new channel. Severity: LOW.
- **R-3 (O_data inflation via poisoned snapshot):** A spoofed sync could admit a
  non-owned office into O_data. **This does NOT directly leak cross-tenant PII** —
  the export's per-tenant C-1 de-id wall (SR-6) is the PII control, and O
  membership only gates *which offices are enumerated*, not *whose PII is
  returned*. But it could cause an office's aggregate insights to be served to a
  principal that should not see them. **Mitigation:** SR-7 (authenticate the sync
  ingress to the warmer principal only). Severity: HIGH if sync ingress is
  under-authenticated → this is the gating threat-model item.
- **R-4 (grain-semantics drift over time):** If the Offer and Unit classifiers
  later diverge in *meaning* (not just membership), the alignment's product
  semantics (OQ-1) could silently shift. **Mitigation:** name the alignment
  direction explicitly in code + a `pipeline_section` audit trail (already carried,
  `gid_push.py:376`). Severity: LOW (slow, auditable).
- **R-5 (Option-3 product-grain assumption unconfirmed):** §6 OQ-1 — if the
  intended grain is Unit (not Offer), the alignment direction must flip
  (enumerate Units in O_asana instead of widening O_data). **Mitigation:**
  requirements sign-off before build. Severity: MODERATE (scoping, pre-build).

---

## 9. Critical-Path Honesty: does Lever-1 unblock the partner report faster?

**No. Lever-1 is the DURABLE fix; it is almost certainly NOT the critical path to
the partner's row_count>0.**

- The **fastest** path to a non-empty deck is operational, not architectural: the
  operator applies **WS-1** (whatever populates/refreshes O_data —
  `account_status` `pipeline_type='unit'` rows via the existing
  `/account-status/sync` warmer run) so the drift offices acquire owned-set rows,
  AND/OR merges **Lever-2** (`d801dbcd`) so the export self-limits under the guard
  and serves the *owned* subset immediately. Lever-2 + a warmer run can yield rows
  **today**, with no security gate.
- **Lever-1 sits behind the security gate (SR-1…SR-8)** and a build cycle. By
  construction it cannot be faster than the ungated operational levers.
- Therefore the honest sequencing is: **(1)** unblock the report NOW via Lever-2
  merge + operator WS-1 apply (ungated); **(2)** ratify + build Lever-1 (this ADR)
  to make the drift *never recur* so no future report needs bounded-bisection
  containment. Lever-1's value is **elimination of a recurring failure class**, not
  **time-to-first-row**. Conflating the two would over-claim Lever-1's urgency and
  under-serve the partner who needs rows this week.

> row_count>0 is unblocked by WS-1 + Lever-2 (ungated, near-term). Lever-1 (this
> ADR, gated) makes row_count>0 **drift-proof and sweep-free** — a durability
> property, delivered after the near-term unblock, not instead of it.

---

## 10. Verified Anchors (every load-bearing claim)

| Claim | Anchor (verified at autom8y-data 92d3606d / autom8y-asana f4f924d2) |
|-------|---------------------------------------------------------------------|
| O_asana enumeration (Offer project, ACTIVE-by-section) | `autom8y-asana .../insights/workflow.py:417-441` |
| O_data owned-set predicate (`pipeline_type='unit'`) | `autom8y-data .../core/repositories/business.py:186` |
| Existence-oracle recognizer (mint-validated carried set, all-or-nothing) | `autom8y-data .../api/auth/operator_plane.py:348` |
| CA-route oracle enforcement (bare 404) | `autom8y-data .../analytics/routes/comparison.py:483/486/141` |
| `denied` → audit-sink-only, body byte-identical to absence | `autom8y-data .../analytics/routes/comparison.py:486-500` |
| Insights-EXPORT route (the path the export actually rides) | `autom8y-data .../analytics/routes/data_service.py:298` |
| Fleet-read branch SKIPs own-tenant intersect | `autom8y-data .../analytics/routes/data_service.py:341` |
| Fleet-read admission (bypass SA only, tenant cannot set) | `autom8y-data .../api/auth/fleet_read_admission.py:48-74` |
| Existing reconciliation receiver (`/account-status/sync`) | `autom8y-data .../api/data_service_models/_account_status_sync.py` |
| Source-keyed snapshot-replace store | `autom8y-data .../api/services/account_status_store.py:67` |
| Existing reconciliation producer (warmer push) | `autom8y-asana .../services/gid_push.py:476-529` (`push_account_status`) |
| Warmer classifier + Offer/Unit grain (`PIPELINE_TYPE_BY_PROJECT_GID`) | `autom8y-asana .../services/gid_push.py:326/397/376` |
| Warmer → push orchestration | `autom8y-asana .../lambda_handlers/cache_warmer.py:1073-1078` → `push_orchestrator.py:129` |
| Lever-2 (CONTAINS, not merged to HEAD) | `autom8y-asana` commit `d801dbcd`, branch `10xdev/insights-export-batch-backoff-cure` |
| Batch wire protocol already supports 207 partial | `autom8y-asana .../clients/data/_endpoints/batch.py:101` |

> **Anchor caveat (corrected vs. mandate):** the mandate's `comparison.py:434/482`
> is the CA-compare oracle and is the correct *named invariant / design
> precedent*, but the insights-export rides the **fleet-read batch**
> (`data_service.py:298/341`), not that route. Both oracles share the same safety
> property; Lever-1 preserves it on both. The mandate's `owned_targets.py:20-22`
> does not exist as a file — O_data lives in `business.py:186`. Packages are
> `autom8_data`/`autom8_asana` (no `y`).
