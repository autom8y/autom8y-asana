---
type: handoff
handoff_type: implementation
status: accepted
from: sre (W-COLDFRAME-VERIFY procession)
to: 10x-dev / platform
created: 2026-06-24
initiative: asana-cutover-readiness
session: session-20260624-122743-279749db
---

# Cross-Rite HANDOFF — sre W-COLDFRAME-VERIFY → 10x-dev/platform

> **Grandeur anchor (RED — incident NOT closed):** The W-COLDFRAME heal (KeyError version-skew, fixed by the `2f75d79` deploy) was NECESSARY-BUT-NOT-SUFFICIENT. A live ASR consumer canary STILL 503s — a SECOND, distinct blocker: a warm-CADENCE vs STALENESS-CEILING mismatch on the offer frame. Drive the offer-frame warm to stay fresh within its read-freshness ceiling so ASR `offer_fetch` returns 2xx. Proven ONLY by a live ASR run with `offer_fetch` 2xx + `3_of_3` recovery — NOT by frame-warm-alone.

## VERIFY RESULT — RED (FORK-2), with live receipts

A controlled ASR **dry-run** canary (set `ASR_DRY_RUN=true` → async invoke `autom8y-account-status-recon` → **reverted env clean**; dry-run suppresses Slack+EventBridge, so no 99-critical firehose) at 2026-06-24 22:31:38Z returned, 13s later:
- Consumer side (`/aws/lambda/autom8y-account-status-recon`): `offer_fetch_failed status=503` "asana service unavailable during query_rows" — trace `248006d8`, 22:31:51Z.
- Asana side (`/ecs/autom8y-asana-service`, SAME trace `248006d8`): `dataframe_cache_s3_lkg_max_staleness_exceeded` `project_gid=1143843662099250 entity_type=offer age_seconds=3450 max_age_seconds=1800 staleness_ratio=19` (also `dataframe_cache_memory_lkg_max_staleness_exceeded age=2559`).

**The offer frame's LKG was ~57 min old against a 30-min (1800s) ceiling → asana refuses to serve the stale LKG and sheds the read as 503.**

## ROOT (distinct from the two prior layers)

| Layer | Status |
|---|---|
| #151 insights auth-wiring | merged (separate Lambda; auth session owns the residual ServiceAccount enrollment) |
| W-COLDFRAME KeyError (version skew) | **fixed-live** by the `2f75d79` deploy (0 KeyErrors since 21:31Z) |
| **THIS: warm-cadence vs staleness-ceiling** | **OPEN — the live blocker** |

The offer frame (`1143843662099250`, `entity_type=offer`, ~4075 rows + 1056-task hierarchy warm) warms **~every 70 min** (observed `dataframe_cache_put` at 20:39Z and 21:49Z) but the read-freshness ceiling is **1800s (30 min)** — so the frame is STALE ~40 of every ~70 min, and any consumer read landing in that window is shed 503. **Plausibly aggravated** by the 429-throttled hierarchy-gap warming (R5: `RateLimitError`/`TimeoutError` on LARGE sibling projects `1200836133305610`/`1205526136594283`/`1201627461398630` …) slowing the offer-frame refresh below the ceiling cadence.

## ASK (10x-dev/platform — design the resilience fix; do NOT prescribe-then-skip)

Candidate directions (architect to weigh — RED-first per the PR bar):
1. **Warm the offer frame more often** (cadence < the 1800s ceiling) so it never goes stale between reads.
2. **Raise / tune the offer-frame staleness ceiling** (the `ceiling_source=multiplier` knob) so a ~57-min LKG is served — trading freshness for availability (evaluate the BI-correctness impact).
3. **Serve-stale-LKG on a slow/throttled refresh** (graceful degradation) instead of shedding 503 — i.e. the `honest_refusal` vs serve-LKG policy at the read path.
4. **Make the hierarchy-gap warm resilient to Asana 429** (AIMD backoff/retry) so the refresh completes within the ceiling.

This is the **shared warm/AIMD substrate** (G-PROPAGATE) — not a per-frame band-aid. **CONSTRAINT: SCAR-005/006** — do NOT change warm ORDERING / cascade priority; this is a cadence/ceiling/serve-policy change, not a reorder.

## Realization rungs (honest; never round up)
- KeyError root: `fixed-live`.
- W-COLDFRAME incident: **STILL OPEN — NOT `protecting-prod`** (live ASR `offer_fetch` 503 at 22:31Z, staleness-shed).
- node-4 (ASR schedule-enable, `autom8y-account-status-recon-schedule`, cron `0 */4`, currently **DISABLED**): **STAYS DEFERRED** — enabling now would 503 intermittently (ASR's 4-hourly read vs the ~70-min warm is a timing coin-flip) → intermittent 99-critical firehose. The enable command, surfaced for the operator (do NOT fire until a live ASR 2xx): `aws events enable-rule --name autom8y-account-status-recon-schedule`.

## Production-mutating levers — status
The ASR dry-run was authorized (grant) and executed READ-only: `ASR_DRY_RUN=true` set → invoked → **reverted verbatim** (confirmed `ASR_DRY_RUN=None`, `LastUpdateStatus=Successful`); Slack/EventBridge suppressed (dry-run). No node-4 enable, no alarm-arm, no deploy. All confirm-first levers untouched.

## Watch-registered DEFER (distinct; do NOT scope-creep into the cadence fix)
- 429/Timeout on LARGE sibling projects (the same throttle family that may slow the offer warm — assess whether the fix #4 covers it).
- `asctime` absent from #150's reserved-key set (know/SDK track).
- R8: `1143843662099250` absent from warmer-bulk/section coverage.
- Inherited: FORK-2 interop (2026-09-29), H-4 cache_warmer decomposition, W-REG/SCAR-REG-001 (until W-IRIS), stale `test_fleet_query_adapter.py:370`.

## Inherited receipts / context
`autom8y-asana-query503-coldframe` (operator memory — RESOLUTION + this VERIFY RESULT); `@.ledge/reviews/handoffs/cross-rite-handoff-10x-wcoldframe-to-sre-2026-06-24.md`; canary trace `248006d8`; ASR fn `autom8y-account-status-recon`; offer frame `project_gid=1143843662099250`.
