---
type: spec
status: draft
author: architect (10x-dev rite)
date: 2026-06-28
impact: high
impact_categories: [security, auth, api_contract, cross_service, pii]
supersedes: TDD-gap1-asana-operator-rewire-2026-06-28.md
consumes_scope_from: PRD-gap1-export-scope-relitigation-2026-06-28.md
pinned_trees:
  autom8y-asana: origin/main e7d71fa8
  autom8y-data: origin/main 3169fa96
  autom8y (auth @ services/auth): origin/main 3df3298a
---

# TDD v2 — GAP-1 insights-export realization at TRUE Option-1 scope (de-identified aggregates only)

> **Status:** DRAFT — design-only, NO code mutation. Reads pinned to `origin/main` for all three repos (`git show <tree>:<path>`); local trees are stale (asana on `chore/bump-core-4.6.0`, data on `main`).
> **Author:** architect (10x-dev rite) · **Date:** 2026-06-28
> **Supersedes:** `TDD-gap1-asana-operator-rewire-2026-06-28.md` (predated the operator's Option-1 scope re-frame; its "intersection = ∅ → GAP-1b escalation" verdict is corrected here — see §0.3).
> **Consumes:** `PRD-gap1-export-scope-relitigation-2026-06-28.md` (the triage + Option-1 litigation; operator-ratified scope, rite-disjoint vet STRONG on the decision).
> **Cross-refs:** `autom8y-data/.ledge/specs/TDD-machine-operator-mint-capability-2026-06-28.md` (the auth+data mint BUILD this consumes), `autom8y-data/.ledge/specs/TDD-gap1-gap2-lean-realization-2026-06-27.md` (operator-route design), ADR-0040 (security gate).

---

## Grandeur Anchor

> "We are 10x-dev, building GAP-1 at its true scope — the asana insights-export mints an OperatorClaims token (via the deployed C-6 endpoint, role `autom8-asana-insights-export-lambda-role`) and consumes the operator-plane route for the 8 DE-IDENTIFIED AGGREGATE tables (+2 allowlist names), DROPPING the 4 per-patient/financial tables from the cross-tenant view (no fall-back to fleet-read) — toward merged + deployed-INERT, NO FURTHER. NEVER weaken DATA-VAL-003/c1b/REC-3/the C-1 PII wall. The counter moves only at the operator FLIP."

---

## 0. Executive verdict (read this first)

### 0.1 The realization, in one paragraph

The operator's Option-1 ruling **collapses the prior GAP-1b escalation into a buildable initiative.** The cross-tenant agency-BI export = the **8 de-identified aggregate tables**, served via the deployed operator plane (mint `OperatorClaims` → `POST /api/v1/insights/operator/execute-batch`, bounded to the owned set `O`); the **4 PII tables** (APPOINTMENTS, LEADS, LIFETIME + T14 RECONCILIATION) are **dropped from the cross-tenant view and NOT kept on the SA fleet-read** (keeping them there re-asserts DATA-VAL-003 and defeats the telos). The data-plane delta is **+2 allowlist names** (`offer_level_stats`, `question_level_stats`); no new insight is built.

### 0.2 The sharpest finding the PRD did NOT have (this TDD's load-bearing correction)

**8/8 is NOT cleanly reachable in one PR at origin/main.** The PRD established admissibility (all 8 are de-identified) and that the registered insights already exist. But admissibility ≠ shape-equivalence. Reading the operator route's executor directly shows it **bypasses `insights_service` entirely** — it calls `engine.get_batch(...)` with `dimensions = insight.dimensions + office_phone` and **does not** carry the three transforms the factory-frame path applies:

| Transform (factory-frame path) | Where it lives | In the batch executor? | Tables that depend on it |
|---|---|---|---|
| `aggregate_by_time_bucket` (period series) | `insights_service.py:467-543` | **NO** | BY QUARTER / MONTH / WEEK |
| `apply_activity_filter` (drop zero-activity rows) | `_insights_helpers.py:275`, called `insights_service.py:541,554` | **NO** | ASSET TABLE, AD QUESTIONS |
| `_enrich_with_missing_assets` (Category-B) | `insights_service.py:574,583+` | **NO** | UNUSED ASSETS |

So only **4 of the 8** tables are clean-1:1 over the batch route (SUMMARY, OFFER TABLE, AD QUESTIONS, ASSET TABLE — the last two needing a *trivial* asana-side activity filter). The other **4** need an affordance (BY-period series — OQ-3; UNUSED ASSETS Category-B — OQ-4). **Recommendation: ship the 4-clean subset first; BY-period (3) + UNUSED ASSETS (1) are a ruled fast-follow.** See §7.

### 0.3 Superseded / corrected premises (each re-verified on origin/main)

1. **Prior TDD: "intersection = ∅ → GAP-1 infeasible as a rewire."** CORRECTED. The ∅ holds only at the *wire-route/response-envelope* level. At the *insight-computation* level the intersection is large: `FrameTypeMapper._FRAME_TYPE_TO_INSIGHT` routes `base→unit→account_level_stats`, `assets→asset→asset_level_stats`, `business_offers→offer→offer_level_stats`, `ad_questions→question→question_level_stats` and derives dims/metrics from the **same** `InsightRegistry` (`frame_type_mapper.py:78-84`). The export's factory tables ARE those registered insights.
2. **Prior memory: "`operator_insights.py` is #213-only, absent on origin/main."** STALE. **#214 merged** the operator-admit route + REC-3 `OperatorClaims` widen + default-deny allowlist onto **data `origin/main` @ `3169fa96`** (`3169fa96 feat(authz): data-plane operator-admit …`). The route is LIVE on main; the data edits no longer "stack on #213."
3. **PRD OQ-3: "BY-period may use `business_summary` (already allowlisted)."** REFUTED. `business_summary` metrics = `[spend, lclicks, cps, convs]` (`library.py:370`); the BY-period deck requires `leads, cpl, scheds, booking_rate, conv_rate, ltv` (`tables.py:165-177`) — all present on `account_level_stats` (`library.py:411-441`), none addable from `business_summary`. The BY-period source is `account_level_stats`, which has **no `date` dimension** (`library.py:455`).
4. **PRD OQ-4: "add an `include_unused` field to the operator request."** REFINED. The `include_unused` field is **not needed for the clean subset**: the activity-filter gap (ASSET TABLE, AD QUESTIONS) is solved by a trivial asana-side predicate; only UNUSED ASSETS' Category-B enrichment is genuinely data-plane-only — and it is dropped/deferred.
5. **PRD: "8/8 = +2 names + sign-off + rewire."** REFINED per §0.2 — only 4/8 are clean after the +2 names.

---

## 1. The build DAG

```
PR-D1  (autom8y-data) — the +2-name allowlist extension
   │   add {offer_level_stats, question_level_stats} to _OPERATOR_INSIGHT_ALLOWLIST
   │   (operator_insights.py:172-178). data-owner-ratified de-identified (§2).
   │   ── ADR-0040 security gate INVOKED (FEATURE+, PII/auth) ──
   │   INERT (allowlist additions are inert until a minted operator token requests
   │   an owned office; auth OPERATOR_ARN_ALLOWLIST=[] keeps the whole plane dark).
   ▼
PR-A   (autom8y-asana) — the mint client + the 4-arm clean rewire   [DEPENDS ON PR-D1 for the offer/question round-trip]
   │   A1  _operator_mint.py        (SigV4 → /operator/token; no SDK floor)        §5.1
   │   A2  DataServiceClient.get_operator_insights_batch_async  (consume route)     §5.2
   │        ├─ batch-over-O call pattern + per-office distribution adapter (OQ-2)    §5.3
   │        ├─ asana-side activity filter for {asset, question}  (OQ-4a)            §4
   │        └─ token-reuse (mint-once + single-retry) + G-NO-FALLBACK              §5.4
   │   A3  rewire 4 INSIGHTS arms → operator route (SUMMARY/OFFER/AD-Q/ASSET)       §5.5
   │   A4  DROP the 4 PII arms from the cross-tenant path (NOT kept on SA)          §5.6
   │   A5  deploy-INERT + graceful-INERT typed errors                               §6.1-6.2
   │   A6  H-A off-prod REAL round-trip (RT-1/2/3, ≥1 NEW name)  ← G-THEATER bar    §6.3
   │   A7  AT-IMG-1 deployed-image import probe                  ← deploy-scar      §6.4
   ▼
  ▶  merged + deployed-INERT  (RUNG CEILING — STOP; counter = 4/8 on owned offices, RED until FLIP)

PR-FF  (FAST-FOLLOW — ruled here, not built in PR-A)                                §3, §4b, §7
   FF-1  BY QUARTER/MONTH/WEEK   → OQ-3 ruling: asana N-window (bounded-lookback)   §3
         [escalate to data-plane date-grain port ONLY if full-history is required]
   FF-2  UNUSED ASSETS          → OQ-4b ruling: DROP (or data-plane Category-B)     §4b
```

**Ordering rationale:** PR-A is INERT regardless of PR-D1 (empty `OPERATOR_ARN_ALLOWLIST` 403s the mint). But the **round-trip proof** (AC-4) and eventual live correctness for OFFER/AD-QUESTIONS require the +2 names. PR-D1 merges FIRST so the off-prod harness can exercise a newly-added name. The two-way-door cost of PR-D1 is low (an allowlist add is reversible); the one-way-door is the *meaning* of "de-identified" the data owner ratifies (§10).

---

## 2. Design A — the data-plane +2-name extension (autom8y-data, PR-D1)

### 2.1 The change

Add two names to `_OPERATOR_INSIGHT_ALLOWLIST` (`operator_insights.py:172-178`):

```
post-add = frozenset({
    "business_summary", "account_level_stats", "asset_level_stats",   # existing
    "offer_level_stats", "question_level_stats",                       # ADD
})
```

No new `InsightDefinition`, no new route, no schema change, no executor change. The existing `BatchInsightExecutor` already serves any registered name (`operator_insights.py:430-432`, `executor.execute(insight_name=body.insight_name, request=body)`).

### 2.2 The de-identification assertion (data-owner RATIFIES; architect ASSERTS from source)

Both additions carry `office_phone` (the tenant key the operator owns) on the SAME footing as the already-allowlisted `account_level_stats`/`asset_level_stats`. Neither carries a patient/lead grain:

- `offer_level_stats` (`library.py:1295`): grain `offer_id × office_phone × vertical`; dimension `office_phone` (`library.py:1318`); metrics are spend/leads/scheds/`convs`/ltv aggregates. **NOTE for the data owner:** the `convs` metric carries the inline comment "Total conversions (patients)" (`library.py:1308`) — it is an aggregate *count*, not a patient-grain dimension; the ADR-0040 review must confirm no row explodes to patient grain.
- `question_level_stats` (`library.py:1483`): grain `question_key × office_phone × vertical`; dimension `office_phone` (`library.py:1511`); per-screening-question performance aggregate.

This clears the allowlist's OWN admission criterion (`operator_insights.py:159-163`: "add only after the owner confirms no patient-grain / PII dimension"). `reconciliation` stays EXCLUDED (`operator_insights.py:165-171`; financial PII, OD-5-reserved).

### 2.3 The security gate (architect INVOKES + HANDS OFF; does NOT consume)

This change satisfies `complexity >= FEATURE` AND touches PII + auth (a new cross-tenant operand class). The architect **INVOKES** the ADR-0040 gate (security-rite: threat-modeler / compliance-architect / security-reviewer) and **HANDS OFF** the `security-verdict` envelope to tiered delegation (principal-engineer default; potnia on escalation). The architect does NOT interpret `blocking_findings[]` or the verdict enum. The gate's question: *does admitting these two names widen the cross-tenant non-PHI surface?*

### 2.4 Canary (PR-D1, two-sided, on the data plane)

| ID | GREEN (admit) | RED (correctly refused) | Proves |
|----|---------------|--------------------------|--------|
| CN-D1-1 | operator token + owned office + `insight_name=offer_level_stats` → 200 `BatchInsightResponse` | same with `insight_name=question_level_stats` (pre-add) → bare 404 | the 2 names are admitted; nothing else changed |
| CN-D1-2 | `insight_name=account_level_stats` (pre-existing) → 200 | `insight_name=reconciliation` → bare 404-as-oracle (`operator_insights.py:353`) | C-1 still default-deny; reconciliation still excluded |
| CN-D1-3 | operator token → reaches the allowlist check | a **ServiceClaims/bare-SA** token → `operator_claim is None` → bare 404 (`operator_insights.py:~325`) | REC-3 intact; the +2 names do not widen *who* may call |

---

## 3. Design B — OQ-3 ruling: the BY-period time-series gap

### 3.1 The gap (verified)

BY QUARTER/MONTH/WEEK (`tables.py:159,180,201`) are `factory=base, period=quarter|month|week`. On the data side these are **period-aggregation** requests: `insights_service._execute_engine_query` detects `is_period_agg`, fetches **daily grain** via `engine.execute_insight(account_level_stats, period=None, require_date_grain=True)` (`insights_service.py:472-476`), then runs `aggregate_by_time_bucket(...)` to produce one row per `(office × period-bucket)` (`insights_service.py:525`). The display columns `period_label/period_start/period_end` (`tables.py:165-167`) are that series.

The operator route's `BatchInsightExecutor` has **NO** date-grain path: it groups by `insight.dimensions + office_phone` and calls `engine.get_batch(...)` once (`batch_insight_executor.py:122,183-194`). For `account_level_stats` (`dimensions=[office_phone, office, vertical]`, no `date` — `library.py:455`) that yields **one window-aggregate per office** — not a series. `business_summary` (the only `date`-dimensioned allowlisted insight) is metric-incompatible (§0.3 #3).

### 3.2 Options (enumerated)

- **(a) ASANA-side N-window loop.** Mint once; for each BY-period table call `execute-batch(insight_name=account_level_stats, phones=O, start_date=Wᵢ.start, end_date=Wᵢ.end)` once per period bucket Wᵢ; assemble the `(office × period)` series asana-side from the per-window aggregates. The route accepts `start_date`/`end_date` (`models.py:2025-2026`) and returns per-office results (`BatchInsightResponse`). **No data-plane change.** Cost: one call per bucket (each call covers ALL owned offices, so cost = bucket-count, NOT bucket-count × offices).
- **(b) DATA-plane date-grain port.** Add `require_date_grain` + `aggregate_by_time_bucket` to the batch executor behind a new typed request flag (porting `insights_service.py:467-543` into the batch path). One call per BY-period table. **Data-plane change** → new ADR-0040 surface on the operator request model + executor.
- **(c) `business_summary`.** REJECTED — metric-incompatible (§0.3 #3).

### 3.3 DoS / rate-limit assessment (the decisive axis)

The operator route is `@limiter.limit(LIMIT_HEAVY_ANALYTICS)` = **`"10/minute"`** (`rate_limit.py:21`) — a STATIC budget with no role/SA lever. Under option (a) the call count = number of period buckets. The OLD path buckets **all available history** (`period=None`), so an **unbounded BY WEEK ≈ weeks-of-history calls** (52–104+) against 10/min ⇒ 5–10+ min wall-clock + 429 backoff per run. BY MONTH (~12–24) and BY QUARTER (~4–8) are tractable; **BY WEEK full-history is rate-infeasible** under (a).

### 3.4 RULING

**Option (a), gated by a BOUNDED-LOOKBACK contract.** (a) is the minimal-data-disturbance mechanism and is CHOSEN — it keeps the data-plane surface lean (no new ADR-0040 surface). It is conditional on the BY-period deck declaring a **bounded bucket count** (default: last **4 quarters / 12 months / 13 weeks** ⇒ ≤29 calls ≈ 3 min, within budget). **If the product requires full-history BY WEEK**, (a) becomes rate-infeasible and the ruling **escalates to option (b)** (data-plane port collapses N calls → 1 per table; carries its own ADR-0040 review). **The BY-period tables ship in the FAST-FOLLOW (FF-1), not the initial clean subset** — they are the only tables whose mechanism is unsettled pending the bounded-lookback product call (OQ-3 → operator).

---

## 4. Design C — OQ-4 ruling: `include_unused` (both asset behaviors)

### 4.1 The gap splits into TWO independent sub-problems (verified)

`apply_activity_filter` (`_insights_helpers.py:275-305`) is a post-query Polars staticmethod scoped to `frame_type ∈ {question, asset}` that keeps rows where `spend>0 OR leads>0` (`_insights_helpers.py:298-304`). The factory-frame path applies it when `include_unused=False` (`insights_service.py:541,554`); the batch executor never calls it.

- **(4a) ASSET TABLE + AD QUESTIONS over-include.** Both are `frame ∈ {question, asset}` with `include_unused=False` (default) → the OLD path drops zero-activity rows; the batch route does not → over-inclusion.
- **(4b) UNUSED ASSETS Category-B.** `include_unused=True` (`tables.py:262`) means (i) SKIP the activity filter (free on the batch route — it never applies it) AND (ii) `_enrich_with_missing_assets` — append assets ABSENT from `ads_insights` with zero metrics via a **DB inventory query** (`insights_service.py:574,583+`). asana has **no DB access**; this is structurally data-plane-only.

### 4.2 Options + RULING (4a — activity filter)

- (i) **asana-side filter** in the response adapter (keep `spend>0 OR leads>0`). The predicate is trivial + stable, the returned rows carry `spend`+`leads` (both in `asset_level_stats`/`question_level_stats` metrics), drift risk negligible. **No data-plane change.**
- (ii) add the filter to the executor (data-plane; drift-free but heavier + new ADR-0040 surface).
- (iii) product-accepts-over-inclusion (sign-off only).

**RULING: (i) asana-side filter** — minimal disturbance, low drift, no data-plane change, preserves de-identification (it only *removes* rows). ASSET TABLE + AD QUESTIONS thereby join the clean subset.

### 4.3 Options + RULING (4b — Category-B / UNUSED ASSETS)

The operator request has **no** `include_unused` field (`OperatorBatchInsightRequest(BatchInsightExecuteRequest)` + `extra="forbid"`; `include_unused` lives only on the factory-frame model `data_service_models/_insights.py:47,93`). Options: (i) data-plane affordance (add `include_unused` typed field + wire `_enrich_with_missing_assets` into the batch path — ADR-0040); (ii) **DROP** UNUSED ASSETS from the agency deck (lowest-value table per PRD EC-2); (iii) asana-side — IMPOSSIBLE (no DB).

**RULING: (ii) DROP from the initial deck (FF-2).** If product requires it, the fast-follow adds the data-plane affordance (i) under its own ADR-0040 review. **The `include_unused` request field is NOT needed for the clean subset at all.**

---

## 5. Design D — the asana rewire (autom8y-asana, PR-A)

### 5.1 The SigV4 mint client (carried from the prior TDD §2, re-verified @ `3df3298a`)

New private module `src/autom8_asana/clients/data/_operator_mint.py`:

1. `creds = boto3.Session().get_credentials().get_frozen_credentials()` — ambient execution-role creds (`autom8-asana-insights-export-lambda-role`; AWS-rotated; no secret at rest).
2. `AWSRequest(method="POST", url="https://sts.amazonaws.com/", data="Action=GetCallerIdentity&Version=2011-06-15", headers={"Content-Type":"application/x-www-form-urlencoded"})`.
3. `SigV4Auth(creds, "sts", "us-east-1").add_auth(request)` — signs in place (`Authorization` + `X-Amz-Date` + `Host`). Sign **immediately before** POST (auth freshness window `OPERATOR_STS_MAX_SKEW_SECONDS=60`, `config.py:113`).
4. POST `{iam_request_method, iam_request_body, iam_request_headers, nonce=uuid4}` to `${AUTOM8Y_AUTH_OPERATOR_TOKEN_URL}` (NEW env var) → `/operator/token` (`operator.py:75,83`).
5. Parse `SuccessResponse[TokenResponse]` → return `(access_token, expires_in)`.

Contract facts (auth `3df3298a`): body MUST equal `_GET_CALLER_IDENTITY_BODY` (`operator_identity.py:44`); signed `Host` must equal the pinned STS host (`_assert_host_pin`, `operator_identity.py:121-129`) ⇒ sign for `sts.amazonaws.com` (`config.py:106`), not a regional host; empty `OPERATOR_ARN_ALLOWLIST` (`config.py:110`) 403s every mint (the INERT gate); TTL 300s (`config.py:90`); mint rate 30/min/IP (`config.py:115` — ample for mint-once).

**No `autom8y-auth` SDK floor on asana** — it sends a token STRING and never deserializes `OperatorClaims` (the data plane does, at the REC-3 recognizer). Signer = botocore `SigV4Auth` (already in-image: `boto3>=1.42.19` at `pyproject.toml:41`, `[project.dependencies]`). Hand-rolled SigV4 / `aws-requests-auth` REJECTED (defect surface / needless dep).

### 5.2 The consume method

New `DataServiceClient.get_operator_insights_batch_async(insight_name, phones, *, period=None, start_date=None, end_date=None, limit=None) -> dict[str, list[dict]]` (phone → row-list): mints/reuses (§5.4) a token; POSTs `OperatorBatchInsightRequest` (`{phones, period|start_date+end_date, limit, insight_name}`) to `POST /api/v1/insights/operator/execute-batch` with `Authorization: Bearer {operator_token}`; parses `SuccessResponse[BatchInsightResponse]`; returns the per-office distribution (§5.3). It carries its OWN `Authorization` header; it does NOT route through `_get_auth_token` (`client.py:450`) or the SA Bearer seam (`client.py:439`).

### 5.3 OQ-2 — per-office distribution adapter + the call pattern (RULED)

**The shape adapter.** `BatchInsightResponse` returns per-phone `PhoneInsightResult{phone, data: StandardResponse|None, status}` (`models.py:2087+`). `PhoneInsightResult.data.data` is a `list[dict]` (`StandardResponse.data`, `models.py:2066`) — the SAME row-of-dicts the export reads today as `response.data` (`workflow.py:673`). The adapter folds `BatchInsightResponse → {phone: result.data.data}`; an `error`/None result → that phone's empty list (no data loss; a failed office yields an empty deck, not a crash).

**The call pattern — batch-over-O (RULED), not per-office.** The route is a batch over offices; the export is per-office. Two patterns:
- per-office: `execute-batch(phones=[one office])` per office per table ⇒ `N_offices × N_tables` calls (≈75×4 = 300) against 10/min ≈ 30 min. **REJECTED (rate-infeasible).**
- batch-over-O: one `execute-batch(phones=O)` per table ⇒ `N_tables` calls (4) ≈ steady-state. **CHOSEN.** Mint once (§5.4); for each clean insight, one batch call over the agency's owned offices; distribute per-office via the adapter.

**EC-4 — the all-or-nothing × ownership-drift hazard.** `authorize_targets` is all-or-nothing (`operator_insights.py:393-408`): ONE requested office ∉ `O` → the WHOLE batch 404s, and `O` is server-internal (not exposed to asana). **RULING:** asana batches over its intended set; on an all-or-nothing 404, perform a **single bounded per-office sweep over the intended set on the operator route** (to serve the owned subset and skip the drift office). The sweep stays on the operator route — it is **NOT** an SA fleet-read fallback (G-NO-FALLBACK holds, §5.4). Steady-state (no drift) cost = `N_tables` calls; the sweep fires only on the rare 404. The sweep MAY be staged into FF if drift is operationally proven rare (documented risk RK-1).

### 5.4 Token reuse + G-NO-FALLBACK

Mint once per run, hold in process memory (never disk/SM/log; dies with the Lambda invocation). Single re-mint + retry on near-expiry or 401 (a run may exceed 300s); bounded single retry, no loop. **G-NO-FALLBACK (invariant):** on mint-403 or route-404/denial the method raises a typed error and NEVER calls `/data-service/insights`, `/appointments`, or `/leads` as a fallback — a fleet-read fallback re-asserts DATA-VAL-003. Test-enforced (AT-INERT-3).

### 5.5 The 4-arm clean rewire (the INSIGHTS dispatch arm, `workflow.py:659-667`)

Rewire the clean-subset arms from `get_insights_async(factory=…)` to `get_operator_insights_batch_async(insight_name=<mapped>)` (mapping = `frame_type_mapper` resolution, `client.py:659-674` + `frame_type_mapper.py:78-84`):

| Table | factory | → insight_name | period | asana-side filter (OQ-4a) |
|-------|---------|----------------|--------|---------------------------|
| SUMMARY | base | `account_level_stats` | lifetime | none |
| OFFER TABLE | business_offers | `offer_level_stats` (PR-D1) | t30 | none (offer ∉ {question,asset}) |
| AD QUESTIONS | ad_questions | `question_level_stats` (PR-D1) | lifetime | `spend>0 OR leads>0` |
| ASSET TABLE | assets | `asset_level_stats` | t30 | `spend>0 OR leads>0` |

ASSET TABLE's existing display-time `exclude_columns` (office_phone/transcript/etc., `tables.py:238-249`) are unaffected (post-fetch display logic).

### 5.6 DROP the 4 PII arms (M4)

Remove APPOINTMENTS / LEADS / RECONCILIATION×2 from the cross-tenant export path (`workflow.py:618-631` arms). They are **NOT** produced on the cross-tenant agency deck and **NOT** kept on the SA fleet-read (keeping them re-asserts DATA-VAL-003 — the precise telos antithesis). If a per-office operational need is later confirmed (OQ-1 → Option-4), the disposition mechanism is a per-office-scoped path (PRD OQ-6), explicitly NOT this agency operator token and NOT the SA path.

### 5.7 Retire the OLD SA path FOR THE REWIRED TABLES

The export's 4 rewired arms no longer hit `/data-service/insights` (the `AUTOM8Y_DATA_API_KEY` ServiceClaims/SA Bearer path, `client.py:439/450`). That seam stays intact for any OTHER `DataServiceClient` consumer; the operator method is separate. M3 (SA-path retirement) = grep-zero `/data-service/insights` calls from the export for SUMMARY/OFFER/AD-QUESTIONS/ASSET (AC-3).

---

## 6. Design E — deploy-INERT, proof, deployed-image discipline

### 6.1 INERT gate

The empty `OPERATOR_ARN_ALLOWLIST` (`config.py:110`) 403s the mint for everyone, including the asana role, pre-FLIP — the natural INERT gate (no new asana flag). The operator method additionally honors the existing `AUTOM8Y_DATA_INSIGHTS_ENABLED` kill-switch (`client.py:102`) for the live era. The whole rewire is dark until the operator allowlists the asana role ARN at FLIP.

### 6.2 Graceful-INERT (fail closed + quiet, NEVER SA-fallback)

mint 403 → typed `OperatorMintRefusedError` (new, repo-local), WARNING, no crash. route 404 → typed `OperatorAccessDeniedError`, WARNING. No SA fallback (G-NO-FALLBACK). Pre-FLIP, with the arms rewired but the mint 403ing, the export produces an **empty agency deck gracefully** for the 4 rewired tables (the counter stays RED with zero regression on the dropped PII tables, which simply no longer appear).

### 6.3 Round-trip proof (the G-THEATER bar — NOT a green CI)

- **H-A — off-prod REAL round-trip against a synthetic-ARN-allowlisted auth (DECISIVE).** Stand up auth/data off-prod with `OPERATOR_ARN_ALLOWLIST=[<harness role ARN>]`, the real STS pin, **and PR-D1's +2 names merged**. The harness (running under an allowlisted role) executes the FULL chain: ambient creds → SigV4 GetCallerIdentity → `/operator/token` → real Bearer → `execute-batch` for a **newly-added** name (`offer_level_stats` or `question_level_stats`) over a seeded synthetic owned office → assert a real `BatchInsightResponse`. Exercises STS signature validity, host-pin, freshness, REC-3, C-1 (incl. the +2 names), owned-set authorize, executor. Production FLIP untouched.
- **H-B — CI integration with stub STS** — wiring regression only; NOT a substitute for H-A's real-STS leg (a stub cannot validate the SigV4 signature semantics).

Discriminating canaries (two-sided, per discriminating-canary doctrine):
- **RT-1 (mint):** allowlisted role → token (GREEN); stale `X-Amz-Date` (>60s) → 403 (RED-correct). Proves freshness is real.
- **RT-2 (consume, exercises the EXTENSION):** `insight_name=offer_level_stats` for an owned office → 200 (GREEN); `insight_name=reconciliation` → bare 404 (RED-correct). Proves the +2 names AND that C-1 still bites.
- **RT-3 (ownership):** owned office → authorized; non-owned office → bare 404 (no oracle). Proves the bounded-O / DATA-VAL-003 sidestep.

### 6.4 Deployed-image discipline (the scar — auth crashed TWICE on a startup-path test-only dep)

All PR-A imports (`boto3`, `botocore.auth`, `botocore.awsrequest`, the HTTP client, repo-local errors) MUST be runtime deps — `boto3` already is (§5.1). No test/dev-only module on any import path reachable from `lambda_handlers/insights_export.py → workflow_handler → DataServiceClient`. **Verification (AT-IMG-1):** `python -c "import autom8_asana.lambda_handlers.insights_export"` succeeds **in the built prod image / non-dev dependency set** (asana's `uv sync --no-dev` equivalent — the Dockerfile's resolution), NOT the dev venv.

---

## 7. Which tables are clean-1:1 vs need-affordance — and the AC-2 (8/8) reachability recommendation

| # | Table | insight_name | allowlist | batch-route gap | Disposition |
|---|-------|--------------|-----------|-----------------|-------------|
| 1 | SUMMARY | account_level_stats | have | none | **CLEAN — PR-A** |
| 11 | OFFER TABLE | offer_level_stats | **+add (PR-D1)** | none | **CLEAN — PR-A** |
| 9 | AD QUESTIONS | question_level_stats | **+add (PR-D1)** | activity filter (OQ-4a) → asana-side | **CLEAN — PR-A** |
| 10 | ASSET TABLE | asset_level_stats | have | activity filter (OQ-4a) → asana-side | **CLEAN — PR-A** |
| 6 | BY QUARTER | account_level_stats | have | period series (OQ-3) | **FAST-FOLLOW FF-1** |
| 7 | BY MONTH | account_level_stats | have | period series (OQ-3) | **FAST-FOLLOW FF-1** |
| 8 | BY WEEK | account_level_stats | have | period series (OQ-3); rate-sharp | **FAST-FOLLOW FF-1** |
| 12 | UNUSED ASSETS | asset_level_stats | have | Category-B (OQ-4b) → data-plane-only | **FAST-FOLLOW FF-2 (drop default)** |

### AC-2 reachability recommendation

**8/8 is NOT cleanly achievable in one PR at origin/main. Ship the 4-clean subset first** (SUMMARY, OFFER TABLE, AD QUESTIONS, ASSET TABLE) — this is the genuine "counter moves on the admissible subset" win (4/8 of the agency deck served via the operator plane, bounded to `O`, SA path retired for those 4). Then **FF-1** (BY-period 3, OQ-3 ruling: asana N-window + bounded-lookback) and **FF-2** (UNUSED ASSETS: drop default, or data-plane Category-B) as ruled fast-follows. Forcing 8/8 into PR-A would either smuggle data-plane changes (OQ-3-(b), OQ-4-(b)) past their ADR-0040 reviews or accept a rate-infeasible BY-WEEK loop — both regress the discipline. Counter ceiling in this initiative = 4/8 on owned offices at merged+deployed-INERT; it moves only at the operator FLIP.

---

## 8. Contracts → named acceptance tests

| ID | Contract | Test | Repo |
|----|----------|------|------|
| AT-D1-1 | allowlist = exactly the 5 de-identified names; reconciliation absent | assert `_OPERATOR_INSIGHT_ALLOWLIST == {business_summary, account_level_stats, asset_level_stats, offer_level_stats, question_level_stats}`; `reconciliation ∉` | data |
| AT-D1-2 | the +2 names admit; non-allowlisted still 404 (CN-D1-1/2) | offer/question → 200; reconciliation → bare 404 (`operator_insights.py:353`) | data |
| AT-D1-3 | REC-3 unchanged (CN-D1-3) | ServiceClaims/bare-SA token → `operator_claim is None` → bare 404 | data |
| AT-MINT-1 | GetCallerIdentity body is exactly the allowed action | `iam_request_body == "Action=GetCallerIdentity&Version=2011-06-15"`; mutate 1 byte → auth 403 | asana |
| AT-MINT-2 | Host signed for the pinned STS host | signed `Host`/scope targets `sts.amazonaws.com`; regional host → auth 403 (`_assert_host_pin`) | asana |
| AT-MINT-3 | Freshness (RT-1) | sign→POST <60s GREEN; injected stale `X-Amz-Date` → 403 | asana |
| AT-MINT-4 | No SDK floor / no secret at rest | ambient `boto3` creds only; grep-zero for any operator token persisted to SM/disk/log | asana |
| AT-CONSUME-1 | operator Bearer, not the SA token | operator method's Authorization == minted token; `_get_auth_token` NOT called on the operator path | asana |
| AT-CONSUME-2 | request shape (RT-2, exercises a NEW name) | body validates `OperatorBatchInsightRequest`; `offer_level_stats` → real `BatchInsightResponse` | asana |
| AT-CONSUME-3 | OQ-2 adapter (no data loss) | `BatchInsightResponse{PhoneInsightResult}` → `{phone: rows}`; error result → empty list, no crash | asana |
| AT-FILTER-1 | OQ-4a activity filter (two-sided) | a zero-activity asset/question row (`spend==0 ∧ leads==0`) dropped; a `spend>0` row kept | asana |
| AT-BATCH-1 | batch-over-O call pattern | one `execute-batch(phones=O)` per clean table (not per-office); assert call count == clean-table count | asana |
| AT-EC4-1 | all-or-nothing drift sweep (NOT SA-fallback) | a batch with one non-owned office → 404 → bounded per-office sweep on the operator route serves the owned subset; assert NO `/data-service/insights` call | asana |
| AT-DROP-1 | M4 — PII arms dropped, not kept on SA | grep-zero: cross-tenant path invokes none of `get_appointments_async`/`get_leads_async`/`get_reconciliation_async`; no SA fleet-read survives for any of the 12 tables on the cross-tenant path | asana |
| AT-INERT-1 | empty allowlist → graceful 403 | against empty-allowlist auth, mint → `OperatorMintRefusedError`, WARNING, no crash | asana |
| AT-INERT-2 | no production call-site beyond the 4 clean arms | grep: only the 4 rewired arms invoke `get_operator_insights_batch_async`; PII arms removed | asana |
| AT-INERT-3 | G-NO-FALLBACK | on mint-403/404 the operator path emits NO `/data-service/insights`//`/appointments`//`/leads` fallback request | asana |
| AT-IMG-1 | deployed-image import-cleanliness | handler imports in the prod image with zero dev deps (§6.4) | asana |
| RT-1/2/3 | real round-trip canaries | §6.3, discharged by the H-A off-prod run (G-THEATER bar) | asana+data |

---

## 9. ADR-deltas

- **ADR-Δ1 (scope):** GAP-1 realized at TRUE Option-1 — 8 de-identified aggregate tables; the 4 PII tables DROPPED from the cross-tenant view and NOT kept on SA fleet-read. Supersedes the prior TDD's "GAP-1b escalation."
- **ADR-Δ2 (computation-level intersection):** the operator route and the export share the SAME `InsightRegistry` via `FrameTypeMapper`; the export's factory tables ARE registered insights. The prior "intersection = ∅" was a wire-route artifact, not a computation fact. Corrected.
- **ADR-Δ3 (clean-vs-affordance split):** only 4/8 are clean over the batch route; BY-period (OQ-3) and UNUSED ASSETS (OQ-4b) need affordances. Ship the 4-clean subset; fast-follow the rest. (The acid test: in 18 months, "we shipped 4 clean + ruled the other 4 honestly" reads obviously-right; "we forced 8/8 with a rate-infeasible week loop + un-reviewed data-plane changes" reads as the regret.)
- **ADR-Δ4 (OQ-3):** BY-period = asana-side N-window (option a) + bounded-lookback contract; escalate to data-plane date-grain port (option b) only on a full-history requirement. `business_summary` rejected (metric-incompatible).
- **ADR-Δ5 (OQ-4):** activity filter = asana-side (4a, no data-plane change); UNUSED ASSETS Category-B = data-plane-only → drop default (4b). The `include_unused` request field is NOT added for the clean subset.
- **ADR-Δ6 (mint transport):** botocore `SigV4Auth` on `sts:GetCallerIdentity` → `/operator/token`; no `autom8y-auth` SDK floor on asana (sends a token string).
- **ADR-Δ7 (call pattern):** batch-over-O (mint once, one call per insight over the owned set, distribute per-office) — forced by the 10/min `LIMIT_HEAVY_ANALYTICS`; per-office rejected. EC-4 drift resolved by a bounded per-office sweep on the operator route (NOT an SA fallback).
- **ADR-Δ8 (G-NO-FALLBACK):** the operator path NEVER falls back to a fleet-read on refusal/denial. Test-enforced (AT-INERT-3). Preserves DATA-VAL-003 / c1b / REC-3.
- **ADR-Δ9 (security gate):** PR-D1's +2 names trigger ADR-0040 (FEATURE+, PII/auth). Architect INVOKES + HANDS OFF the `security-verdict`; does not consume it. OQ-3-(b) and OQ-4-(b) each carry their own ADR-0040 surface if elected in FF.

### Reversibility assessment

| Decision | Door | Note |
|---|---|---|
| +2 allowlist names (PR-D1) | two-way | an allowlist removal reverts; the *de-identification ratification* (§10) is the load-bearing, harder-to-revert commitment |
| DROP the 4 PII arms | two-way (code) | reversible in code; but re-adding cross-tenant PII is an Option-4 re-litigation (one-way at the *product* level — needs OD-5 + BAA/consent) |
| asana-side activity filter (4a) | two-way | a pure asana predicate |
| batch-over-O call pattern | two-way | internal to the consume method |

---

## 10. Residual operator calls (the seam)

- **OQ-1 (the hinge — operator CONFIRM):** is the agency's use of this export aggregate-analytical (→ Option-1 stands, this TDD builds) or a live cross-office per-patient/financial OPERATIONAL function (→ refute to Option-4, a separate heavier initiative)? PR-A proceeds on the Option-1 default; a refutation re-opens §5.6.
- **Data-owner ratification of the +2 names (PR-D1 blocker):** confirm `offer_level_stats` + `question_level_stats` carry no patient-grain / PII dimension (esp. the `convs` "Total conversions (patients)" comment, `library.py:1308`). ADR-0040 / OD-style. Architect ASSERTS de-identified from source; the data owner RATIFIES.
- **OQ-3 product call:** is bounded-lookback (4Q/12M/13W) acceptable for the BY-period deck (→ FF-1 asana-only), or is full-history BY WEEK required (→ FF-1 escalates to the data-plane date-grain port)?
- **OQ-4b product call:** drop UNUSED ASSETS (default) or fund the data-plane Category-B affordance?
- **FLIP-time (operator-terminal):** allowlist the asana role ARN. The Lambda presents an `assumed-role` session ARN; auth `normalize_arn` (operator_identity.py) collapses it to the `role/` form — the operator must allowlist `arn:aws:iam::696318035277:role/autom8-asana-insights-export-lambda-role` (the collapsed form). Verify in H-A (UV-P below).

---

## 11. SVR ledger (file-read against the pinned trees; verified at authorship)

| # | Claim | source (`git show <tree>:<path>`) | line | marker_token (verbatim) |
|---|-------|-----------------------------------|------|--------------------------|
| R1 | operator allowlist = the 3 de-id names | data:operator_insights.py | 172-178 | `_OPERATOR_INSIGHT_ALLOWLIST: frozenset[str] = frozenset(` |
| R2 | reconciliation deliberately excluded | data:operator_insights.py | 165-171 | `C-1 EXCLUSION` (`reconciliation` is DELIBERATELY NOT seeded) |
| R3 | non-allowlisted insight → bare 404 before DB | data:operator_insights.py | 353 | `if body.insight_name not in _OPERATOR_INSIGHT_ALLOWLIST:` |
| R4 | route serves via BatchInsightExecutor (no new insight) | data:operator_insights.py | 430-432 | `executor = BatchInsightExecutor(engine=engine)` |
| R5 | owned-set bounded + all-or-nothing | data:operator_insights.py | 384,393-408 | `if not result.all_authorized:` |
| R6 | route rate-limited HEAVY = 10/min | data:rate_limit.py | 21 | `LIMIT_HEAVY_ANALYTICS = "10/minute"` |
| R7 | OperatorBatchInsightRequest = batch req + insight_name | data:operator_insights.py | ~185 | `class OperatorBatchInsightRequest(BatchInsightExecuteRequest):` |
| R8 | batch req fields + extra=forbid (no include_unused) | data:models.py | 1982-2034 | `model_config = {"extra": "forbid"}` |
| R9 | batch executor = get_batch, no date-grain/filter/enrich | data:batch_insight_executor.py | 122,183-194 | `batch_result = await self._engine.get_batch(` |
| R10 | OLD BY-period branch (date-grain + time-bucket) | data:insights_service.py | 467-543 | `period=None,\n                require_date_grain=True,` |
| R11 | activity filter = post-query, frame ∈ {question,asset} | data:_insights_helpers.py | 275,298-304 | `pl.col("spend").fill_null(0) > 0) | (pl.col("leads")` |
| R12 | activity filter applied in insights_service only | data:insights_service.py | 541,554 | `df = self._apply_activity_filter(df, frame_type)` |
| R13 | Category-B enrichment (DB inventory), insights_service only | data:insights_service.py | 574,583 | `entity_metrics = await self._enrich_with_missing_assets(` |
| R14 | frame_type → insight map (delegates to registry) | data:frame_type_mapper.py | 78-84 | `"offer": "offer_level_stats",` |
| R15 | account_level_stats full metrics, no date dim | data:library.py | 411-455 | `dimensions=["office_phone", "office", "vertical"],` |
| R16 | business_summary narrow metrics + date dim | data:library.py | 370-371 | `metrics=["spend", "lclicks", "cps", "convs"]` |
| R17 | offer_level_stats office-grain de-id | data:library.py | 1295,1318 | `name="offer_level_stats",` |
| R18 | question_level_stats office-grain de-id | data:library.py | 1483,1511 | `name="question_level_stats",` |
| R19 | include_unused on factory-frame model only | data:data_service_models/_insights.py | 47,93 | `include_unused: bool = Field(` |
| R20 | 12 TableSpecs; BY-period period=quarter/month/week | asana:tables.py | 124-266 | `period="quarter",` |
| R21 | INSIGHTS arm → get_insights_async(factory,…) | asana:workflow.py | 659-667 | `response = await self._data_client.get_insights_async(` |
| R22 | factory→frame map | asana:client.py | 659-674 | `"base": "unit",` |
| R23 | export per-office (single phone_vertical_pair) | asana:_endpoints/insights.py | 182,189 | `path = "/api/v1/data-service/insights"` |
| R24 | SA Bearer seam (not touched by operator method) | asana:client.py | 439,450 | `def _get_auth_token(self) -> str | None:` |
| R25 | boto3 runtime dep | asana:pyproject.toml | 41 | `"boto3>=1.42.19", # S3 for progressive cache warming` |
| R26 | mint endpoint + request model | auth:routers/operator.py | 48,75,83 | `class OperatorTokenRequest(BaseModel):` |
| R27 | mint mounted /operator | auth:app/main.py | 296 | `app.include_router(operator.router, prefix="/operator", tags=["operator"])` |
| R28 | GetCallerIdentity body const + host pin | auth:services/operator_identity.py | 44,121-129 | `_GET_CALLER_IDENTITY_BODY = "Action=GetCallerIdentity&Version=2011-06-15"` |
| R29 | STS pin + empty ARN allowlist (INERT) + TTL + skew | auth:app/config.py | 90,106,110,113,115 | `OPERATOR_STS_ENDPOINT: str = "https://sts.amazonaws.com"` |
| R30 | data origin/main carries the merged operator route (#214) | data:git log | 3169fa96 | `feat(authz): data-plane operator-admit — REC-3 OperatorClaims sibling` |

---

## 12. Open UV-Ps (carried forward)

- [UV-P: the C-6 mint + operator route are DEPLOYED and reachable from the asana Lambda's network/identity at FLIP | METHOD: deferred-to-flip-integration | REASON: source presence verified on origin/main (R26-R30); live reachability + the asana role's allowlist entry are FLIP-time facts]
- [UV-P: the asana role ARN allowlisted at FLIP equals `arn:aws:iam::696318035277:role/autom8-asana-insights-export-lambda-role` after `normalize_arn` collapses the assumed-role session | METHOD: deferred-to-H-A-round-trip | REASON: the Lambda presents an assumed-role ARN; verify the collapsed form in RT-1]
- [UV-P: STS region for SigV4 credential scope (`us-east-1`) is accepted by the global `sts.amazonaws.com` endpoint for the asana role | METHOD: deferred-to-H-A-round-trip | REASON: confirm in the real round-trip, not unit mocks]
- [UV-P: the registered-insight output (at the export's default parameterization) is an acceptable product substitute for the factory-frame output for each of the 4 clean tables (OQ-2 equivalence) | METHOD: deferred-to-product-signoff | REASON: same engine/registry (R14), but envelope + default params need product sign-off before dry_run=false]
- [UV-P: ownership drift (an asana-listed office ∉ O) is operationally rare enough to stage the EC-4 per-office sweep into FF | METHOD: deferred-to-operational-evidence | REASON: O is server-internal; drift frequency unknown until live]

---

*End TDD v2. Reads pinned: asana `e7d71fa8`, data `3169fa96`, auth `3df3298a`. No code mutated. Supersedes `TDD-gap1-asana-operator-rewire-2026-06-28.md`.*
