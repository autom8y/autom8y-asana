---
type: handoff
handoff_type: validation
status: accepted
from: 10x-dev (W-COLDFRAME-RESILIENCE procession)
to: sre
created: 2026-06-25
initiative: asana-cutover-readiness
session: session-20260624-122743-279749db
---

# Cross-Rite HANDOFF — 10x-dev W-COLDFRAME-RESILIENCE → sre

> **Grandeur anchor (closed at the offer axis):** ASR's `offer_fetch` 503 — the 3rd/final layer of the offer-consumption incident — is RESOLVED. The offer frame's ceiling↔cadence mismatch is fixed ((b)+(c), PR #156, deployed `376e1edd`), proven by a live ASR dry-run with ZERO `offer_fetch_failed:503` and the recon proceeding through the offer axis on 154 records. The residual ASR-health gap is now DATA-SIDE (three_way denominator + budget), NOT the offer frame.

## DONE — offer-fetch 503 = `protecting-prod` (proven live)
- **Fix:** PR **#156** (`fix(cache): offer-frame warm-resilience — freshness contract + populated-LKG seam`), squash-merged to `376e1edd06f1baa10e8c07ff604a6f8e9a5f0dc9`. (b) `config.py` `FRESHNESS_CONTRACT_MAX_AGE_SECONDS["offer"]=16200.0`; (c) `dataframe_cache.py` serve-stale-LKG for populated/healthy cache-only frames over the ceiling (+ SWR refresh), DEGRADED/EMPTY still shed None (INV-C5). RED-first proven; qa + rite-disjoint critic GREEN (a false "4h cadence" comment premise was caught + remediated to the real ~70-min cadence; (c) is the cadence-independent load-bearing half — the 16200 value is non-load-bearing).
- **Deployed:** satellite-receiver run 28164168701 — `Deploy to ECS (a8 CLI)` **SUCCESS**, receiver task-def `:556`, image `376e1edd`, rollout COMPLETED 10:50Z. (The `Metrics-Smoke Gate` was RED but is `continue-on-error`/NON-BLOCKING — a separate /metrics-export concern; see Watch-register.)
- **Verified (controlled ASR dry-run, 10:55Z, `ASR_DRY_RUN` env set→invoke→REVERTED CLEAN):** **0 `offer_fetch_failed:503`** (trace `3ad47c3f`); no asana-side `staleness_exceeded` shed; the recon reached the three-way/budget axes on 154 records (offer data in hand). Offer-starvation gone.
- Rung: **`protecting-prod`** for the offer-fetch 503. The full chain is peeled + closed: auth (#151) → idempotency (#149) → KeyError version-skew (deploy-healed) → cadence/ceiling (#156).

## NOT DONE — 3_of_3 NOT clean; node-4 STAYS DEFERRED (the SRE re-eval, with the data-side axes)
The same dry-run showed the broader reconciliation is gated by **data-side** axes (distinct from the offer frame; masked while offer 100%-starved, unmasked by the fix — NOT a regression):
- `three_way_axis_suppressed: suppressed_count=87 / total_records=154` via many `three_way_denominator_null` — the **autom8y-data `three_way_denominator` reconciler** (per scar: a null/empty denominator for low-traffic/test phones is EXPECTED, not a defect — needs the SRE expected-null baseline to separate expected from real gaps).
- `budget_unavailable indeterminate:44` — the **billing/budget axis** data-not-evaluable (advisory, NOT critical per `models.py:229`); plausibly downstream of the still-open insights/data lineage (W-AUTH-2, owned by the auth session).
- The 99-critical firehose was OFFER-STARVATION (now gone). The remaining are SUPPRESSED/INDETERMINATE (advisory), so the firehose is very likely gone — but I did **not** prove the live critical count (Autom8y/Reconciliation metrics are dimensioned; the un-dimensioned query was empty). **node-4 enable is the SRE re-eval's call**, with the dimensioned metrics + the expected-null baseline.

## VALIDATION ASK (sre)
1. **Re-eval node-4** (`autom8y-account-status-recon-schedule`, cron `0 */4`, DISABLED): with the dimensioned `Autom8y/Reconciliation` metrics (HighSeverityAnomalyCount / three_wayVerdict / budgetVerdict) + the expected-null baseline for low-traffic phones, is the critical count now firehose-safe? Enable is **user-sovereign**: `aws events enable-rule --name autom8y-account-status-recon-schedule` (surfaced; do NOT fire without the operator).
2. **Assess the data-side axes** — separate the EXPECTED `three_way_denominator_null` (low-traffic phones) from real autom8y-data grain gaps; and the 44 `budget_unavailable` — confirm whether it's downstream of the W-AUTH-2 insights/data lineage (coordinate with the auth session) or a distinct data-side defect.

## Watch-registered (distinct; do NOT scope-creep)
- **Metrics-Smoke Gate RED** on run 28164168701 (NON-BLOCKING `continue-on-error`) — the /metrics-export SEAL (zero-/metrics) for the asana ECS task; likely the known ECS-Exec/SSM transport flakiness, but could be a real export regression. A non-paging GitHub issue was auto-filed by the workflow. Distinct from the offer fix.
- The inherited DEFER set: `asctime` gap in #150's reserved-key set (know/SDK); H-4 cache_warmer decomposition; FORK-2 interop (2026-09-29); W-REG/SCAR-REG-001 (until W-IRIS); stale `test_fleet_query_adapter.py:370`.

## Production-mutating levers — status
Merged #156 (green CI + critic-clean) + deployed via satellite-receiver + the controlled ASR dry-run (env set→invoke→REVERTED-CLEAN) were all executed under the grant with receipts. node-4 enable, alarm-arming, rollback, token rotation, the Asana section-GID WRITE — untouched, user-sovereign.

## Inherited receipts / context
`autom8y-asana-query503-coldframe` (operator memory — RESOLUTION recorded); `@.ledge/reviews/handoffs/cross-rite-handoff-sre-wcoldframe-verify-to-10x-2026-06-24.md`; merge `376e1edd`; receiver task-def `:556`; verify trace `3ad47c3f`; ASR fn `autom8y-account-status-recon`; offer frame `1143843662099250`.
