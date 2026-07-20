---
type: review
artifact_role: attribution-receipt
slug: attribution-receipt-asana-429-storm
status: accepted
rite: sre
phase: coordinate (attribution discharge); READ-ONLY forensics + one in-lane non-paging observability mutation (AL-5)
date: 2026-07-13
aws_account: 696318035277
aws_region: us-east-1
baseline: origin/main f713dd30
discipline: "No claim without a pasted LIVE receipt. Rungs named, never rounded: attributed < specified < cured. G-DENOM: no proven-zero from silence; consumer-identity dimension proven present before absence is read."
telos: TELOS-asana-substrate-freshness-2026-07-13.md (C1 keystone)
evidence_grade: MODERATE (self-authored; STRONG requires the rite-disjoint critic)
---

# ATTRIBUTION RECEIPT — the 2026-07-10 asana 429 storm (C1 keystone)

> **Verdict in one line:** the storm is **asana-LOCAL and self-inflicted on a single shared
> bot PAT with no cross-consumer arbitration** — not an external initiative eating the budget,
> and **not** onset by the 2026-07-10T15:50Z EBI Phase-A flip (that hypothesis is **falsified**
> by the log envelope). The founding ticket of the substrate-freshness owned class is discharged
> at rung **attributed**.

---

## C1 acceptance (from the handoff W1 + telos C1)

> "A dated per-consumer breakdown of Asana API consumption for the onset window + today; a named
> owner for the dominant consumer; escalation filed if it is client-serving." + "C1 also answers
> the felt-line question."

All three delivered below with pasted live receipts.

---

## §1 — WHO consumes the shared budget (per-consumer breakdown)

**The budget is one shared bot PAT.** `ASANA_PAT` (resolved via `get_bot_pat()`,
`src/autom8_asana/auth/bot_pat.py:57-75` — docstring verbatim: *"the single credential that
autom8_asana uses to call the Asana API on behalf of all S2S callers"*) backs **every** consumer:
the ECS serve path, all three cache-warmer lanes, and the EBI receipts route. One PAT = **one
1500 req/60s budget** (`ASANA_RATELIMIT_MAX_REQUESTS` default 1500 / `window_seconds` 60,
`config/settings.py:526-540`), with **no deployed override** on either the ECS task def
(`autom8y-asana-service:638`, 24 env vars, none rate-related) or the warmer lambda (only
`SECRETS_MANAGER_TTL=300`) — so the code default is the live ceiling everywhere.

**Consumer-identity dimension (G-DENOM positive selection):** the CloudWatch log-group axis is a
valid consumer-identity dimension *for the processes that call Asana directly*. Proven present by
a live warmer 429 line — the bulk warmer hits `app.asana.com` itself:

```
/aws/lambda/autom8-asana-cache-warmer-bulk  @2026-07-13T14:18:45Z
  [sdk-5bd7f664-b2c1] TasksClient.get(1212622981789017) failed: You have made too many requests
  recently. ... (HTTP 429)
```

(The earlier "warmer emits 0 `app.asana.com` lines" reading was a **log-FORMAT artifact**, not
zero calls — the warmer logs `TasksClient.get(...) failed`, not the httpx `HTTP Request: GET
https://app.asana.com/...` INFO line the service emits. G-DENOM trap identified and resolved.)

**6-hour 429/rate-limit log-lines by consumer** (CloudWatch Logs Insights, 8 log groups scanned,
`recordsMatched=108,645`, run 2026-07-13):

| Consumer (log group) | 429/rate-limit lines (6h) |
|---|---|
| `/ecs/autom8y-asana-service` | **79,881** |
| `/aws/lambda/autom8-asana-cache-warmer-bulk` | **25,669** |
| `/aws/lambda/autom8-asana-cache-warmer` | **3,095** |
| insights-export, unit-reconciliation, conversation-audit, pr-frames-refresh | **0** |

**Actual Asana call volume (budget spend), last 1h:** `/ecs/autom8y-asana-service` =
**17,449** `app.asana.com` requests (~291/min against the 1500/min ceiling ≈ **19%** of the
sustained budget). The storm is therefore **burst-driven** (warmer fan-out spikes), **not**
sustained-average exhaustion — the hourly average sits well under the ceiling while 60-second
bursts blow through it.

**The burst mechanism (self-infliction, code-proven at f713dd30):**
- Per-process rate limiting only: `TokenBucketRateLimiter` is constructed once per `AsanaClient`
  (`src/autom8_asana/client.py:160-163`); the AIMD `AsyncAdaptiveSemaphore` is
  per-client (`transport/asana_http.py:200-213`, ceilings `config.py:392-413`).
- **Cross-consumer arbitration CONFIRMED ABSENT.** Each process runs an independent 1500/60s
  bucket + independent AIMD against the **same real Asana budget**; a lane that trips 429 halves
  *its own* window but cannot signal the others. In-tree acknowledgement, verbatim:
  *"the proven ROOT-1a self-inflicted 429 storm"* (`transport/adaptive_semaphore.py:75`).
- Warmer fan-out magnitude: the bulk sweep enumerates **34 GIDs × 2 arms = 68 keys**; warming
  one starved key's hierarchy costs ≈ **3,291 `GET /tasks/{gid}`** calls (the live
  `parent_gids_count=3291`), recursing to depth 5, partly via an **unbounded** `asyncio.gather`
  (`src/autom8_asana/cache/providers/unified.py:638-641`). The in-tree PAUSED-lane comment
  (`config.py:184-191`) documents the exact failure mode: the section ≤10-min lane *"hit ~896
  Asana rate_limit_429 ... raising the lane's reserved_concurrency WORSENS it (more parallel
  links → more concurrent 429s on the same token bucket). The lane is PAUSED."*

**Named owner of the dominant consumer:** the **autom8y-asana service + its own cache-warmer
lanes** (this repo). The storm is in-lane; there is no external budget to arbitrate elsewhere.

## §2 — The onset hypothesis is FALSIFIED

The handoff's onset arithmetic (last successful ASR-GID warm ≈ 2026-07-10T15:50Z, "the same day
the EBI Phase-A flip went live") was flagged an **UNVERIFIED HYPOTHESIS**. The log envelope
**contradicts** it. `RateLimitError`/`HTTP 429` by 3h bin on `/ecs/autom8y-asana-service`:

```
2026-07-08 21:00Z → 895     2026-07-09 18:00Z →  963     2026-07-10 15:00Z → 723  ← "onset"
2026-07-09 00:00Z → 944     2026-07-09 21:00Z → 1010     2026-07-10 21:00Z → 838
2026-07-09 15:00Z → 746     2026-07-10 00:00Z →  890     2026-07-11 00:00Z → 749
                            [07-11 midday → 07-12: ~0 (lull)]        2026-07-13 15:00Z → 902
```

The storm was **already raging on 07-08/07-09 — ≥2 days before** the hypothesized onset, and the
07-10 15:00Z "onset" bin (723) is **lower** than 07-09 21:00Z (1010). The pattern is
**diurnal-bursty** (15:00–00:00Z high, 03:00–12:00Z low) with a lull on 07-11 midday→07-12 —
the signature of a **scheduled/business-hours workload**, not a one-time flip. The
"onset ≈ 07-10T15:50Z" reflects **when the ASR GID specifically fell behind**, not when the
storm began.

## §3 — EBI: ruled IN as contributor, ruled OUT as sole onset

EBI (external initiative in the sibling `autom8y` monorepo) POSTs nudge "receipts" to this
service at `POST /v1/receipts`; the service then makes the Asana calls (`tasks/search` + comment)
using **the same bot PAT** — `AsanaClient(token=auth_context.asana_pat)`
(`src/autom8_asana/api/routes/receipts.py:160`, docstring `:28-29`). EBI **holds no own Asana
token** and gets **no own log stream** — its load is **folded into the
`/ecs/autom8y-asana-service` line**.

- **Ruled IN as a contributor:** each nudge = one live uncached `tasks/search` on the shared PAT,
  concurrent with the warmer sweep.
- **Ruled OUT as sole onset:** the storm predates the EBI flip (§2).
- **G-DENOM limit (stated, not hidden):** the log-group axis **cannot** separate EBI-driven
  service calls from other service calls. Finer attribution requires the per-route
  `forwarding_receipt_request.caller_service` field (`receipts.py:127`) — a
  **DEFER-registered** runtime query, out of scope for this receipt.

## §4 — Felt-line answer: NO (internal-only), with a code-path receipt

**Is the starved offer substrate client-felt? NO.** The two paths are provably disjoint at
`f713dd30`:

- **Client render path:** the insights offer-coverage table's only offer-data source is
  `src/autom8_asana/automation/workflows/insights/workflow.py:786` →
  `_data_client.get_operator_insights_batch_with_meta_async` → the **external `autom8_data`
  service** at `AUTOM8Y_DATA_URL` (POST `/api/v1/insights/operator/execute-batch`,
  `clients/data/_endpoints/operator.py:47,432-440`). The #230/#231/#232 coverage/weights/band
  additions all ride this same external hop.
- **Starved path:** `src/autom8_asana/cache/integration/dataframe_cache.py:767-776` emits
  `dataframe_cache_memory_lkg_serve` (offer, project `1143843662099250`), served **only** to the
  asana `/query` API surface (`query_rows` engine) — which the render never invokes.
- **Disjointness grep-proven both directions:** `clients/data/` has zero refs to `dataframe_cache`;
  `insights/` has zero refs to the LKG cache. Re-checked at `f713dd30` after #232 (which touches
  `operator.py`, the external path) — holds. Additional backstop: the operator plane is
  **deploy-INERT** (`operator_token_url` defaults `None`).

**Consequence:** the crusade stays **foundation-hardening** under the substrate telos; **F2 does
NOT trigger** (no Pillar-9 live-client fire, no immediate operator escalation). A client seeing
wrong coverage numbers — the Pillar-5 worst-case — is **not** in play on the traced evidence.

## §5 — Freshness semantics (for artifact honesty)

code-**FRESH** ≤ TTL (offer **180s**, default 300s); **STALE** > 3×TTL — for offer that is
**540s** (`SWR_GRACE_MULTIPLIER=3.0` × 180, `config.py:137` + `dataframe_cache.py:1247-1258`); the
900s figure is the **default-TTL** value (300×3), not offer's. The offer LKG serve ceiling is the
**freshness contract 16,200s** (`FRESHNESS_CONTRACT_MAX_AGE_SECONDS["offer"]`, `config.py:304`),
applied at `dataframe_cache.py:684-686` where `ceiling_source="freshness_contract"` **overrides**
the 1,800s multiplier fallback (10 × 180). **The "<3600s" cure bar is LOOSER than code-fresh** —
a frame satisfying it is "served-and-under-an-hour-old, still code-STALE, well within the 16,200s
LKG ceiling," not "fresh." No artifact in this wave presents <3600s as fresh.

## §6 — Routing (F1) & rung

- **F1 outcome → CURE IN-LANE HERE.** No external consumer holds a separate token; there is no
  cross-consumer budget to route elsewhere. The cure mechanism is specified for 10x-dev in
  `HANDOFF-substrate-to-10x-dev-cure-2026-07-13.md` (shared-budget-no-arbitration → extend the
  PR #97 fast-lane pattern to the ASR GID **paired with** a budget partition; durable end-state =
  a cross-consumer arbitrator ADR). NEVER throttle a client path on agent authority — moot here,
  felt-line is NO.
- **Rung (un-rounded):** C1 is **attributed** (discharged). It is not "cured" — the cure is
  C3, specified-not-shipped this wave.

## §7 — Discipline ledger

- **G-PROVE:** every §-claim carries a pasted aws/gh output or a `file:line` at `f713dd30`.
- **G-DENOM:** the consumer-identity dimension was proven present (warmer's own 429 line) before
  any per-consumer count was read; the EBI-folds-into-service limit is stated, not hidden.
- **G-RUNG:** attribution is `attributed`, never rounded to `cured`.
- **Evidence grade:** MODERATE (self-authored). STRONG requires the rite-disjoint critic's
  independent re-query (bound at the wave exit gate).
