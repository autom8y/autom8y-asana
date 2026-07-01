---
type: spec
status: draft
title: "TDD — Insights-Export Operator-Batch Over-Call Cure (drift-resilient bounded batch under the intact 10/min guard)"
slug: insights-export-batch-backoff-cure
author: architect (WS-2 PRIZE)
date: 2026-06-29
base_asana: origin/main @ 6551aee0  # GAP-1 PR-A — asana export -> operator plane (4 clean tables)
base_data: origin/main @ dafbb136   # #215 — admit offer_level_stats + question_level_stats to operator allowlist
supersedes: none
related:
  - TDD-gap1-asana-operator-rewire-v2-2026-06-28.md
  - PRD-gap1-export-scope-relitigation-2026-06-28.md
---

# TDD — Insights-Export Operator-Batch Over-Call Cure

> GRANDEUR ANCHOR (verbatim): "We are 10x-dev, executing the CURE that unblocks the
> partner's first real report — fixing insights-export to deliver `row_count>0` UNDER
> the intact 10/min DoS guard. The 10/min DoS guard is NEVER weakened; the
> export-schedule re-enable stays the operator's. We produce MERGE-READY only."

## 0. CRITICAL IMPLEMENTATION PREMISE (read first)

This design targets **autom8y-asana origin/main @ `6551aee0`** ("GAP-1 PR-A — asana
export -> operator plane (4 clean tables, drop PII) (#165)") and **autom8y-data
origin/main @ `dafbb136`** ("#215 — admit offer_level_stats + question_level_stats
to operator allowlist").

The working tree this TDD was authored against (`chore/bump-core-4.6.0` @ `f4f924d2`)
**diverged BEFORE GAP-1 PR-A** — its `workflow.py` is the OLD 12-table, per-office
single-call path (`get_insights_async` / `get_appointments_async` / `get_leads_async`
/ `get_reconciliation_async`), which differs from `6551aee0` by 448 lines
(`git diff 6551aee0 f4f924d2 -- src/autom8_asana/automation/workflows/insights/workflow.py`).

**The implementer MUST branch from `origin/main` (`6551aee0`), not the current working
tree.** Merging the cure onto the stale tree would re-introduce the per-office SA
fleet-read path and regress DATA-VAL-003 (the telos antithesis the operator plane
sidesteps). All asana file:line anchors below are at `6551aee0`.

---

## 1. Problem statement (grounded mechanism, not the stated premise)

### 1.1 The stated premise was partially mis-identified

The WS-2 anchor states: "~64 execute-batch calls/run (54->429, 10->404) ... Client call
site `clients/data/client.py` ~line 951 `_execute_batch_request`."

Direct inspection refutes the call site: `_execute_batch_request`
(`src/autom8_asana/clients/data/client.py:1041` @6551aee0; :951 in the stale tree) is
reached only via `get_insights_batch_async`
(`src/autom8_asana/clients/data/client.py:860`), which the operator export **does NOT
call**. The operator export's wire path is the **operator-plane batch endpoint**, not
the SA `/insights/{name}/execute/batch` endpoint. The "~64 / 54->429 / 10->404"
observation is real; its mechanism is the operator drift-sweep (1.3), and the cure
follows from that mechanism — not from the SA batch chunker.

### 1.2 The live operator export call graph @6551aee0

```
insights_export.handler
  -> InsightsExportWorkflow.execute_async                              (workflow.py:205)
       -> _prefetch_operator_tables(entities, params)                  (workflow.py:626)
            office_set = _resolve_owned_office_set(entities, params)   (workflow.py:723)
              # O_asana = {office_phone for each ACTIVE Asana Offer}    (workflow.py:748-749)
            phones = sorted(office_set)                                 (workflow.py:660)
            for spec in [4 OPERATOR_INSIGHTS specs]:                    (workflow.py:662-663)
              get_operator_insights_batch_async(insight_name, phones=O) (workflow.py:672)
                -> _endpoints.operator.execute_operator_batch          (operator.py:188)
                     POST /api/v1/insights/operator/execute-batch       (operator.py:41,127)
       -> per-offer pass reads self._operator_batch (NO wire call)     (workflow.py:786,801)
```

Table inventory @6551aee0 is **4 clean operator tables** (`TOTAL_TABLE_COUNT = 4`,
`workflow.py:87`), all `DispatchType.OPERATOR_INSIGHTS` (`tables.py:155-199`):

| Table        | insight_name           | period   | tables.py |
|--------------|------------------------|----------|-----------|
| SUMMARY      | `account_level_stats`  | lifetime | :158-161  |
| AD QUESTIONS | `question_level_stats` | lifetime | :165-168  |
| ASSET TABLE  | `asset_level_stats`    | t30      | :173-176  |
| OFFER TABLE  | `offer_level_stats`    | t30      | :196-199  |

So **I_op = 4 operator insights**, each issuing **ONE batch-over-O call** carrying all
offices (`operator.py:9-11`, the "NOT per-office-per-table" rule).

### 1.3 The over-call is the EC-4 drift-sweep, not the batch

The data operator route is **all-or-nothing**: one requested office not resolvable to a
`chiropractors.guid` (step 2b, `operator_insights.py:383-393` @dafbb136) OR not in the
operator's data-resolved owned set `O` (step 2c, `authorize_targets ... all_authorized`,
`operator_insights.py:413-428`) makes the **WHOLE batch return the bare 404-as-oracle**
(`operator_insights.py:363,374,393,428`). The all-or-nothing is a **deliberate security
invariant** — the route comment explicitly rejects intersect-filtering: "pre-intersecting
selected n O would let a partial batch silently succeed instead of denying the whole"
(`operator_insights.py:411-412`).

Because asana cannot pre-filter `O` (it does not know the server-internal owned set,
`operator.py:13-16`), a single drift office 404s the whole batch and triggers the EC-4
fallback `_drift_sweep` (`operator.py:144-185`): a **per-office loop**
(`for phone in phones:`, `operator.py:164`) re-issuing the SAME operator route once per
office. With I_op insights each falling into the sweep, the wire-call count is:

```
worst_case_calls = I_op * (1 + N_offices)        # 1 batch (404) + N sweep, per insight
```

All these calls share **one** per-identity 10/min bucket
(`@limiter.limit(LIMIT_HEAVY_ANALYTICS)`, `operator_insights.py:309`;
`LIMIT_HEAVY_ANALYTICS = "10/minute"`, `rate_limit.py:21`). The first ~10 land (mostly
drift 404s), the remaining ~54 are rejected 429, every batch already 404'd -> **0 served
rows -> empty decks**.

This is NOT a batch-size problem. The batch is already maximal (all offices in one call,
one call per insight). The over-call is the **O(N) sweep fired by an all-or-nothing 404
on a drift-bearing selection.**

---

## 2. Call-count math

Let `N` = active offices in `O_asana`, `I_op` = 4 operator insights, `C` = server
office-batch ceiling.

**Server ceiling `C` = 100** offices/call: `OperatorBatchInsightRequest`
(`operator_insights.py:201`) inherits `BatchInsightExecuteRequest`, whose `phones` /
`phone_vertical_pairs` fields are `max_length = MAX_BATCH_SIZE = 100`
(`models.py:1979, 2004, 2015`). **Multi-insight batching is NOT available**:
`OperatorBatchInsightRequest` carries exactly one `insight_name` (`operator_insights.py:223`,
single `str` field), so I_op cannot be collapsed below 4 without a data-route model change
(cross-repo + new surface — see Option D, rejected).

**Current (base 6551aee0), drift present on every insight:**
```
calls = I_op * (1 + N) = 4 * (1 + 15) = 64          # matches the observed ~64
landed ~10 (drift 404s) ; rejected ~54 (429)        # matches 10->404 / 54->429 with N~=15
served_rows = 0
```
The ~64 reproduces exactly at `N ~= 15`; the 10/54 split is the 10/min budget admitting
~10 calls/window and rejecting the rest. (`N` is whatever the active-Offer enumeration
yields; 15 is the value that reconstructs the anchor. The structure `4*(1+N)` is the
load-bearing fact, not the specific 15.)

**Clean (drift-free) floor:**
```
calls = I_op * ceil(N / C) = 4 * ceil(15/100) = 4   # one 200 per insight
4 <= 10  -> the guard never trips, rows served
```

**Target ceiling (this cure):** total operator wire calls/run `<= B_run`, where
`B_run <= 10` enforced by a shared token bucket (Section 4). Drift-free runs converge to
`I_op * ceil(N/C)`; drift-bearing runs are bounded by `B_run` via bisection + cap.

---

## 3. The 404 diagnosis (root cause + scope)

### 3.1 Why calls 404

The operator route returns the bare 404-as-oracle (`_ORACLE_404_DETAIL`,
`operator_insights.py:139`) at four gates — in evaluation order:

1. `operator_claim is None` (non-operator token) — `operator_insights.py:345`. **Not the
   cause here**: the anchor confirms mint+authz succeed (`jwt_auth_success`), so the
   operator claim is present.
2. `insight_name not in _OPERATOR_INSIGHT_ALLOWLIST` — `operator_insights.py:373`. **Not
   the cause at the mandate base**: all 4 names are allowlisted (account/asset pre-#215;
   offer/question admitted by `dafbb136` / #215). *Was* a cause before `dafbb136` — any
   pre-#215 asana run would have 404'd offer/question on every office.
3. `resolved_guids is None` — any requested `office_phone` does not resolve to a
   `chiropractors.guid` — `operator_insights.py:383-393`.
4. `not result.all_authorized` — any requested guid is not in the owned set `O` —
   `operator_insights.py:413-428`.

Gates 3 and 4 are the live cause: **ownership/resolution drift** between the two
active-office sources of truth.

### 3.2 Root cause: two divergent "active office" sources

- `O_asana` is built from **Asana active-Offer enumeration**: `_resolve_owned_office_set`
  resolves every active Offer task to an `office_phone` (`workflow.py:723-750`).
- `O_data` is built **data-side** from `account_status`:
  `O = { chiropractors.guid : EXISTS account_status row WHERE
  account_status.office_phone == chiropractors.office_phone AND
  account_status.pipeline_type == 'unit' }`
  (`src/autom8_data/api/auth/owned_targets.py:20-22` @dafbb136;
  `resolve_owned_targets`, :105).

Any office in `O_asana \ O_data` (an active Offer whose phone does not resolve to a guid,
or whose guid lacks a `pipeline_type='unit'` `account_status` row) drifts -> all-or-nothing
404 -> sweep. The "10 -> 404" are precisely the drift offices surfaced individually during
the per-office sweep; the "54 -> 429" are the sweep calls beyond the 10/min budget.

### 3.3 Is the 404 in scope?

The 404 is the **proximate trigger** of the over-call (it is what fires the sweep), so
neutralizing its blast radius IS the cure's core and is **in scope** for asana. There are
two distinct neutralizations, with different ownership:

- **Tolerate the 404 without exploding** (asana-only, merge-ready): bound + pace + cap
  the sweep so a 404 costs O(drift . log N) calls under a hard <=10/min budget, never
  O(N). This ships in asana now (Section 4, Lever 2).
- **Eliminate the 404** (durable): align `O_asana` with `O_data` so the batch authorizes
  cleanly. Every realization of this touches the existence-oracle invariant
  (`operator_insights.py:411-412`) and is therefore **cross-repo + security-gated**
  (Section 4, Lever 1; ADR-004).

### 3.4 The empty-O failure mode (decisive disambiguation)

If `O_data` is **empty** for the operator (`resolve_owned_targets -> frozenset()` —
absent/unsynced active fleet, `owned_targets.py:48-50`), **every** office 404s — drift
AND non-drift alike — and **no asana call-pattern change can yield `row_count>0`**. This
is a data-side `account_status` population problem, not an asana over-call problem. The
proof design (Section 6) MUST disambiguate empty-O from drift before any asana-only cure
is declared sufficient.

---

## 4. Option enumeration and recommendation

Two invariants are INVIOLATE and bound the whole option space:

- **INV-1 (the DoS guard):** `LIMIT_HEAVY_ANALYTICS = "10/minute"` (`rate_limit.py:21`),
  per-identity, must keep firing at the 11th call/min. Raising / removing / bypassing =
  REJECTED.
- **INV-2 (the existence-oracle / all-or-nothing):** the operator route denies the whole
  batch rather than partial-serving a drift-bearing selection
  (`operator_insights.py:411-412`, D-M1a). Weakening this is a security change, not a free
  lever — the structural twin of INV-1.

### Option A — "bigger server batch" (mandate option 1)
Increase offices-per-call and/or insights-per-call to fit <=10 calls/min.
- Offices/call already maximal at `C=100` (`models.py:1979`); for N<=100 the insights
  batch is already 1 call each. Insights/call is fixed at 1 (`OperatorBatchInsightRequest`
  single `insight_name`, `operator_insights.py:223`). So the clean floor is already
  `I_op=4` calls — there is no batch-size headroom to reclaim.
- The over-call is the sweep, not the batch; bigger batches do not touch it.
- **Verdict: does not address the defect.** (It only helps the latent N>100 case, which
  the cure handles via <=100 chunking anyway, FILE-3.)

### Option B — "pace + 429 backoff" on the existing sweep (mandate option 2)
Keep all-or-nothing + per-office sweep; client self-limits <=10/min, honors `Retry-After`,
exponential backoff.
- Holds INV-1 and INV-2. Pure asana, merge-ready.
- But the linear O(N) sweep, paced at <=10/min, costs `N/10` minutes wall-clock and serves
  a **deterministic prefix** of offices (sorted phones, `workflow.py:660`): the tail
  starves every run -> those offices never get a non-empty deck. Under empty-O it spends
  minutes to return 0 rows.
- **Verdict: necessary primitives (pacer, Retry-After, backoff), insufficient shape.**

### Option C — HYBRID: drift-resilient bounded batch (RECOMMENDED)
Asana-only, merge-ready; converges to the clean floor as the security-gated alignment
(Lever 1) lands.
- **Lever 2 (ships now, pure asana):** replace the O(N) per-office `_drift_sweep`
  (`operator.py:144-185`) with a **bounded BISECTION** under a **run-shared token-bucket
  pacer** and a **hard aggregate call cap** `B_run`:
  - On a >1-office batch 404, binary-split the phone set and recurse on each half. An
    all-owned sub-batch 200s in ONE call (serving every office in it); a drift-bearing
    sub-batch 404s and splits further. Cost is `O(drift . log N)` calls for clustered
    drift vs `O(N)` for the linear sweep.
  - A single shared `OperatorCallPacer` (token bucket, refill 10/60s, conservative ceiling
    `B_run` default 9 < 10) is threaded across **all 4 insights AND the bisection
    recursion**, so the AGGREGATE per-run wire count is capped — not per-insight (the
    current code can sweep N per insight independently = 4N).
  - `Retry-After` is honored on any 429 (`RetryableErrorMixin.retry_after_seconds`,
    `patterns/error_classification.py`, ADR-0079; conventions.md:65); when the bucket /
    cap is exhausted, unreached offices render empty THIS run (graceful, prior decks
    intact — Section 5 / RISK-4), and the run is flagged partial.
  - Add <=100 chunking of `phones` before the first batch (FILE-3) so N>100 never 422s.
- **Lever 1 (durable, cross-repo, SECURITY-GATED — flagged, NOT required to ship Lever 2):**
  give asana a way to send a drift-free `O` so the batch 200s in `I_op` calls with no
  sweep at all. Both realizations touch INV-2 and require the ADR-0040 security gate
  (ADR-004): (1a) a data-side owned-set resolution surface asana intersects against, or
  (1b) the route's intersect-serve change. Until Lever 1 lands, Lever 2 carries the prize.
- **Verdict: RECOMMENDED.** Decisive reason in 4.1.

### Option D — multi-insight batch (one call for all 4 insights x all offices)
Collapse `I_op` 4 -> 1.
- Requires a NEW data request model accepting a list of `insight_name`
  (`operator_insights.py:223` is single) -> cross-repo + new attack surface, and still
  404s on drift (does not touch the sweep). Marginal benefit (4 is already <=10).
- **Verdict: rejected** (cost >> benefit; does not address the defect).

### Option E — security-ratified scoped limit (mandate option 4)
- A higher scoped limit for the export role **weakens INV-1** -> REJECTED by hard
  constraint. The legitimate security touchpoint here is NOT raising the limit; it is
  ratifying the **existence-oracle change** that enables drift-free batching (Lever 1).
- Named review for Lever 1: **security-rite ADR-0040 gate** (threat-modeler ->
  security-reviewer verdict; `Approve | Request-Changes | Reject`). Complexity tier:
  **FEATURE/SYSTEM** (operator auth, cross-tenant aggregate, new data-handling path).
- **Verdict: do NOT raise the 10/min limit.** Route Lever 1 (only) through ADR-0040.

### 4.1 Recommendation and decisive reason

**RECOMMENDED: Option C (Hybrid), shipping Lever 2 now and flagging Lever 1 behind the
ADR-0040 gate.**

Decisive reason: Option C is the **only** option that simultaneously (a) ships entirely
within the asana mandate (merge-ready, no cross-repo blocker, no security gate to ship
Lever 2), (b) holds **both** invariants inviolate — it self-limits strictly BELOW the
10/min guard (INV-1 stays armed and fires at the 11th call) and it only ever asks the
operator route its OWN all-or-nothing question, more efficiently (INV-2 untouched), and
(c) delivers `row_count>0` by serving every owned office reachable within the per-run
budget. Plain pace+backoff (Option B) matches (a)/(b) but starves the tail of offices and
melts wall-clock; bigger-batch (A) and multi-insight (D) do not touch the sweep that is
the actual over-caller; scoped-limit (E) weakens INV-1. Option C strictly dominates B on
coverage-per-call and wall-clock at equal guard-safety, and dominates A/D/E on
correctness/safety.

---

## 5. Detailed design

### 5.1 New component: `OperatorCallPacer` (run-scoped budget governor)
A small object constructed once per export run and threaded into the operator endpoint:
- Token bucket: capacity 10, refill 10 tokens / 60s (mirrors the server window). A
  conservative `ceiling` (default 9) caps the AGGREGATE wire calls per run below the
  server limit, leaving headroom for clock skew between client and server windows.
- `await acquire()` blocks until a token is available OR raises `BudgetExhausted` if the
  per-run hard cap is hit. On a server 429 with `Retry-After`, the pacer sleeps the
  advertised interval (clamped) before refunding.
- Idempotent and stateless across runs (fresh per `_prefetch_operator_tables`).

### 5.2 Bisection sweep (replaces `_drift_sweep`)
`operator.py` `_drift_sweep` (`:144-185`) is replaced by `_bounded_bisect_serve(client,
insight_name, phones, pacer, ...)`:
1. `await pacer.acquire()`; POST the batch over `phones` via `_post_operator_batch`
   (`operator.py:110`, unchanged — same operator Bearer, no SA token ever).
2. `200` -> `distribute_per_office(body)` (`operator.py:44`, unchanged); return rows for
   ALL offices in this sub-batch.
3. `404` and `len(phones) == 1` -> drift office; return `{}` (empty deck, no oracle leak).
4. `404` and `len(phones) > 1` -> split `phones` in half; recurse left then right; merge.
5. `429` -> honor `Retry-After` via the pacer; on repeated 429 or `BudgetExhausted` ->
   stop, return what was served so far (partial), flag the run partial.
6. `403` / other 4xx-5xx -> fail closed as today (`OperatorMintRefusedError` /
   `OperatorAccessDeniedError`, `operator.py:255-268`); NEVER an SA fleet-read
   (G-NO-FALLBACK, `operator.py:19-22`).
The "first try the whole batch; bisect only on 404" shape preserves the drift-free fast
path (one 200 call) and bounds the drift-present path.

### 5.3 Aggregate budget across insights
`_prefetch_operator_tables` (`workflow.py:626`) constructs ONE `OperatorCallPacer` and
passes it into each of the 4 `get_operator_insights_batch_async` calls
(`workflow.py:672`), so the cap is per-RUN, not per-insight. When the pacer raises
`BudgetExhausted` mid-run, remaining insights/offices are left empty (graceful), the run
is flagged partial, and the existing `_operator_plane_refused` INERT no-op semantics
(`workflow.py:653,684`) are preserved for the whole-plane refusal case.

### 5.4 <=100 chunking
Before the first batch, chunk `phones` into groups of `C=100` (`models.py:1979`) and run
the bisection-serve per chunk under the shared pacer. Fixes the latent N>100 -> 422 bug
(today `operator.py` sends all phones in one body with no chunk).

### 5.5 Exact files to change

| # | File (autom8y-asana @6551aee0) | Change |
|---|--------------------------------|--------|
| FILE-1 | `src/autom8_asana/clients/data/_endpoints/operator.py` | Replace `_drift_sweep` (`:144-185`) with `_bounded_bisect_serve`; thread `pacer` through `execute_operator_batch` (`:188`) and `_post_operator_batch` (`:110`); add <=100 chunking; on 404 over >1 office call bisection instead of linear loop (`:235-249`). |
| FILE-2 | `src/autom8_asana/clients/data/client.py` | `get_operator_insights_batch_async` (`:1383`) accepts and forwards a `pacer`; expose an `OperatorCallPacer` factory on the client (run-scoped). |
| FILE-3 | `src/autom8_asana/automation/workflows/insights/workflow.py` | `_prefetch_operator_tables` (`:626`) builds one pacer/run and passes it into all 4 insight calls (`:672`); flag partial runs in metadata; preserve `_operator_plane_refused` no-op (`:653,684`). |
| FILE-4 | `src/autom8_asana/clients/data/_endpoints/__init__.py` / a new `_pacer.py` | Define `OperatorCallPacer` + `BudgetExhausted`; reuse `RetryableErrorMixin.retry_after_seconds` (`patterns/error_classification.py`, ADR-0079, conventions.md:65). |
| FILE-5 | tests (Section 6) | Bisection coverage, aggregate-cap, guard-armed, empty-O probe, partial-run deck-preservation. |

**Cross-repo dependency (FLAGGED, not in this PR):** Lever 1 (durable drift elimination)
is a **data-repo** change behind the **ADR-0040 security gate** — either (1a) a new
operator owned-set resolution surface or (1b) the operator route's intersect-serve. Both
modify INV-2 (`operator_insights.py:411-412`) and MUST carry a `security-verdict`
(threat-modeler -> security-reviewer) before merge. No data-route batch-ceiling change is
required for Lever 2.

---

## 6. Verification design

### 6.1 PROOF-1 — owned-set non-emptiness probe (empty-O vs drift disambiguation) [GATING]
Mint the operator token; POST `/api/v1/insights/operator/execute-batch` with
`phones=[ONE office known-active in account_status pipeline_type='unit']`,
`insight_name="account_level_stats"`. Assert **HTTP 200 AND >=1 row**.
- **200+rows** -> `O_data` is non-empty; drift is the cause; the asana cure is applicable.
- **404** -> `O_data` is empty/misresolved for this operator -> the wall is DATA-side
  `account_status` population (`owned_targets.py:20-22,48`), NOT asana over-calling.
  ESCALATE; do NOT declare the asana-only cure sufficient. This is the denominator-integrity
  gate: a green asana unit test on a probe-excluded/empty fleet is NOT proof.

### 6.2 PROOF-2 — `row_count>0` on REAL data (the prize) [DECISIVE]
With Lever 2 merged and the export run against the REAL active fleet (schedule stays
operator-disabled; invoke once manually / dry-run preview, `workflow.py:562-575`):
- Assert total operator wire calls/run `<= B_run` (default 9) AND no minute-window exceeds
  10 (from the pacer's own emitted counter).
- Assert at least one office's rendered deck has `row_count > 0` (read the
  `insights_export_table_fetched` `row_count` events, `workflow.py:803-809`, or the dry-run
  preview HTML). NEVER a green unit test on the bisection function alone — REAL fleet,
  non-empty rows on a real owned office.
- Assert the export emits the partial flag iff any office was budget-skipped, and that
  budget-skipped offices keep their PRIOR deck (no destructive delete — RISK-4).

### 6.3 PROOF-3 — the guard still fires at the 11th call [INVARIANT INV-1]
- **Behavioral:** from the export operator identity, fire 11 operator-route calls within
  60s via a raw client loop (bypassing the pacer). Assert call #11 -> **HTTP 429**. Proves
  the server guard is intact (not raised/removed/bypassed).
- **Static:** assert `LIMIT_HEAVY_ANALYTICS == "10/minute"` (`rate_limit.py:21`) UNCHANGED
  and the operator route still carries `@limiter.limit(LIMIT_HEAVY_ANALYTICS)`
  (`operator_insights.py:309`). Any diff to either = the cure is REJECTED.
- **Self-limit:** assert the cured export's own per-minute wire count `<= B_run < 11`
  (the export never trips the guard because it self-limits below it, while the guard
  remains armed for anything that would).

### 6.4 PROOF-4 — bisection bounds (two-sided)
- Drift-free O -> exactly `I_op * ceil(N/100)` calls, zero 404 (fast path intact).
- One drift office among N -> `<= I_op * (2*ceil(log2 N) + 1)` calls, all owned offices
  served (clustered-drift efficiency).
- Sprinkled drift (every other office) -> bisection degrades; assert the aggregate cap
  holds (`<= B_run`) and `row_count>0` still holds for >=1 served owned office (coverage
  may be partial — RISK-2).

---

## 7. ADRs (embedded)

**ADR-001 — Hold the all-or-nothing existence-oracle (INV-2) as inviolate as the DoS guard.**
Context: the cleanest call-count reduction is to make the route partial-serve owned
offices. Decision: do NOT design around weakening `operator_insights.py:411-412`; treat it
as a security invariant equal in standing to INV-1. Consequence: drift elimination (Lever 1)
is routed through the ADR-0040 gate; the merge-ready cure (Lever 2) respects the route's
all-or-nothing semantics exactly. Reversibility: two-way (Lever 1 can later supersede the
sweep). Alternative rejected: route intersect-serve without a gate (silent partial success;
existence-oracle leak).

**ADR-002 — Bisection over linear sweep for the drift fallback.**
Context: the O(N) linear sweep is the over-caller. Decision: bisect on 404 under a shared
budget. Rationale: O(drift . log N) for clustered drift; full-coverage within budget vs the
linear sweep's deterministic-prefix starvation. Consequence: more code than a paced linear
sweep; degrades to O(N) under sprinkled drift (mitigated by the hard cap). Reversibility:
two-way.

**ADR-003 — Run-scoped AGGREGATE pacer, not per-insight.**
Context: today each insight can independently sweep N (4N aggregate). Decision: one token
bucket per run threaded across all insights + recursion, hard ceiling `B_run` (default 9 <
10). Rationale: only an aggregate cap provably holds INV-1 across the 4 insights.
Consequence: under heavy drift the run is partial (some offices empty this run).
Reversibility: two-way (ceiling is config).

**ADR-004 — Lever 1 (durable drift elimination) is cross-repo + ADR-0040-gated.**
Context: eliminating the 404 needs `O_asana == O_data`. Decision: defer to a data-repo
change behind the security gate (threat-modeler -> security-reviewer `security-verdict`),
FEATURE/SYSTEM complexity (operator auth, cross-tenant aggregate, new data path). Do NOT
raise the 10/min limit. Consequence: the prize ships on Lever 2 now; Lever 1 converges the
export to a deterministic `I_op`-call clean floor later. Reversibility: one-way at the
route-semantics layer (hence the gate).

---

## 8. Residual risk register (for qa-adversary)

- **RISK-1 (empty-O BLOCKER, HIGH):** if `O_data` is empty/misresolved (`owned_targets.py:48`),
  no asana change yields `row_count>0`. PROOF-1 is the gate; if it 404s, the wall is
  data-side `account_status` sync, not this cure. Adversary: run PROOF-1 FIRST; do not
  accept a green bisection unit test as the prize.
- **RISK-2 (sprinkled-drift partial coverage, MED):** bisection degrades to ~O(N) when
  drift is interleaved; the cap then serves only a subset -> some offices render empty.
  `row_count>0` holds (>=1 owned office) but coverage < 100%. Adversary: construct an
  interleaved-drift fixture and assert the cap holds AND coverage is reported honestly.
- **RISK-3 (>100 offices, MED):** without FILE-3 chunking, N>100 -> 422 (no sweep, silent
  empty). Adversary: test N in {1, 100, 101, 250}.
- **RISK-4 (destructive partial run, HIGH):** the export is upload-first then delete-old
  (`workflow.py:543-561`). A budget-capped partial run MUST NOT delete the prior good deck
  of an office it could not serve this run. Adversary: assert a partial run leaves prior
  attachments intact for unreached offices (mirror the `_operator_plane_refused` no-op
  guard semantics, `workflow.py:274-289`).
- **RISK-5 (per-insight vs aggregate cap regression, HIGH):** if the pacer is threaded
  per-insight instead of per-run, the aggregate is 4*B and INV-1 can trip. Adversary:
  assert the pacer instance is shared across all 4 `get_operator_insights_batch_async`
  calls and across recursion (single counter).
- **RISK-6 (clock-skew window straddle, MED):** client and server 10/min windows are not
  phase-aligned; a client that times to exactly 10/min can still present 11 in a server
  window. The `B_run<=9` ceiling is the margin. Adversary: drive bursts straddling a window
  boundary; assert no server 429 from the cured export AND that the guard still 429s a raw
  11th (PROOF-3).
- **RISK-7 (Retry-After / circuit-breaker interaction, MED):** the operator client has its
  own circuit breaker; honoring `Retry-After` plus breaker backoff must not deadlock or
  double-sleep. Adversary: inject 429-with-Retry-After and assert single honored sleep,
  no breaker trip on a pure rate signal.
- **RISK-8 (stale-base merge, HIGH):** implementing against the working tree (`f4f924d2`,
  12-table per-office path) instead of `origin/main` (`6551aee0`, 4-table operator path)
  re-introduces the SA fleet-read and regresses DATA-VAL-003. Adversary: assert the merged
  workflow has `TOTAL_TABLE_COUNT == 4` and zero `get_appointments/leads/reconciliation/
  get_insights` calls on the cross-tenant path (`workflow.py:786` reads cache only).
- **RISK-9 (G-NO-FALLBACK erosion, HIGH):** any new error branch must NEVER fall back to
  `/data-service/insights` (the SA fleet-read) — that re-asserts DATA-VAL-003
  (`operator.py:19-22`). Adversary: assert every failure path in `_bounded_bisect_serve`
  raises the typed operator error or yields empty; grep for SA-path calls inside the
  operator endpoint = zero.

---

## 9. Handoff checklist

- [x] Mechanism grounded to file:line at the correct base (asana 6551aee0 / data dafbb136).
- [x] >=4 genuine options enumerated with trade-offs; recommendation + decisive reason.
- [x] Call-count math reconciles the observed ~64 / 54->429 / 10->404.
- [x] 404 root cause named (drift between `O_asana` and `O_data`) + scope ruling.
- [x] Both invariants (INV-1 DoS guard, INV-2 existence-oracle) declared inviolate; neither
      designed-around; Lever 1 routed to the ADR-0040 gate.
- [x] Exact asana files + the cross-repo dependency flagged.
- [x] `row_count>0` REAL-data proof + empty-O disambiguation + guard-fires-at-11th proof.
- [x] Residual risk register for qa-adversary.
- [ ] principal-engineer: branch from `origin/main` @6551aee0 (NOT the working tree).
- [ ] operator-terminal: export-schedule re-enable stays the operator's.
