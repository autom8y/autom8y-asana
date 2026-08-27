---
type: spike
status: accepted
initiative: north-facing-crusades (post realization-tail-convergence)
generated_at: 2026-07-08
generator: strategy rite (potnia → business-model-analyst → roadmap-strategist)
source: .sos/wip/glints/glint-full-2026-07-08.md (myron, 14 glints @ f3d8eec1)
lens: internal + north-star-aligned (market/competitive held)
self_assessment_cap: MODERATE
---

# SPIKE — Next North-Facing Crusades

Time-boxed strategic read of the myron opportunity report, sequenced against the business
north star: **real-time per-offer revenue & unit economics** — dashboards showing real dollars
*per offer*, not book-wide sums, so leadership can KILL / SCALE / REPRICE / ALLOCATE offers on
real data.

## The one insight that changes the timeline

**The path to the north star is weeks, not quarters — because two of its three blockers are
already solved-in-code, and the defense against the "$0 dashboard" is already built.** Confirmed
by direct code inspection, not inference:

- **Blocker-A (payment→offer link) — GENUINE build, and the only one.** Nothing joins a payment
  amount to an `offer_id` anywhere. `metrics/definitions/offer.py:26-65` produces only
  `active_mrr` + `active_ad_spend`, both deduped up to `(office_phone, vertical)` — a
  *company-level* P&L line, not an offer-level one. The north-star number has **no producer**.
- **Blocker-B (active-accounts registry empty) — likely a flag already ON.**
  `gid_push.py:439-443 _is_status_push_enabled()` is **enabled-by-default**; the push machinery
  (`enumerate_active_offers`, `push_status_to_data_service [SD-02]`) exists. The registry may
  already be populating in prod — a **live-state probe**, not a build, resolves it.
- **The $0-dashboard guardrails already exist (undocumented).** `null_number_recovery.py`
  (cures the silent-$0 GID-only warm path), `post_build_population_receipt.py` (0.80 population
  floor, ACTIVE-scoped, WARN-first), `fail_closed_write` — a built three-part defense for the
  exact feared failure mode. It needs **capture + activation**, not construction.
- **Denominator risk:** the vertical enum-set sync (`contracts/vocabulary_sync.py`) is
  **SHIP-DARK** (`VOCAB_SYNC_ENABLED` defaults OFF) — the `(office_phone, vertical)` denominator
  both offer metrics depend on may silently drift. Another **probe**, not a build.

## Why this is the north star (the value case)

An offer-based (Hormozi-style portfolio) business's atomic decision unit is **the individual
offer**. Today leadership sees book-wide MRR and a single ad-spend pool — no per-offer ROAS, no
per-offer contribution margin, no per-offer LTV:CAC. Every reallocation is intuition. The number
unblocks: **KILL** (offers with per-offer ROAS < 1), **SCALE** (highest-margin / best LTV:CAC),
**REPRICE** (pricing headroom vs margin-negative floors), **ALLOCATE** (rank the full offer set
for the marginal dollar and marginal unit of capacity). Cost of the status quo: mis-steered ad
spend, unpriceable offers, and a dashboard nobody can trust.

## The crusade slate (denominator-before-probe sequenced)

| # | Crusade | Disposition | Value | Effort | Glints |
|---|---|---|---|---|---|
| **0** | **Critical-Path Denominator Probe** — is blocker-B a live flag? is the SHIP-DARK vertical-enum denominator active? is blocker-A an extractor-column vs metric-def vs upstream-contract gap? | **PURSUE-NEXT** | Tier-1 (path-determining) | **XS** (no code; live probes) | active-accounts-registry · vocabulary-sync-ship-dark |
| **1** | **The North-Star Producer** — a per-offer payment-linked revenue metric | SEQUENCE-AFTER-0 | Tier-1 (direct revenue) | M–L (**scope set by Crusade-0**) | per-offer-revenue-metric-absent |
| **2** | **Guardrail Activation & Registration** — capture + wire the built $0-defense as a live alarm | PARALLEL-CHEAP | Tier-1 (correctness multiplier) | S–M (capture, not construct) | population-receipt · null-number-recovery · economics-value-population-domain |
| **3** | **Records-Truth Wave 2** — feature-census refresh + close the toothless "schema-only" drift-guard | SEQUENCE-AFTER | Tier-2 (foundation hygiene) | M | census-hash-drift · drift-guard-schema-only-gap |
| **4** | **Revenue Delivery Observability** — OBS-EXPORTS-001 on the exports pipe | PARK-WITH-TRIGGER (self-fires when the number ships) | Tier-2 (delivery) | S–M | obs-exports-001 |
| **5** | **Per-Business Anti-IDOR Capture** — document + test the credential-isolation invariant | PARALLEL-CHEAP (rides census refresh) | Tier-2 (security) | S | per-business-token-anti-idor |
| — | onboarding-walkthrough (9 files) · scheduling-stratum — **PARKED** (off-path; census-refresh targets, not crusades) | PARK | Tier-3 | — | (tag-and-route) |

## The OKR (H1, north-star-direct)

**Objective:** Leadership makes per-offer KILL/SCALE/REPRICE decisions on real revenue data,
not book-wide sums.
- **KR1 (producer):** a per-offer payment-linked revenue metric is registered and joins a
  payment amount to `offer_id`.
- **KR2 (denominator):** the ACTIVE-set registry + vertical-enum denominator are confirmed live
  in prod (or activated).
- **KR3 (trust):** the population-receipt floor (0.80, ACTIVE-scoped) is wired as a live alarm so
  the number is actionable, not silently degraded.

## First move — Crusade-0 probes (route to theoros/iris; a /spike, not a build)

1. **Registry population:** is `STATUS_PUSH_ENABLED` on in prod AND is the `[SD-02]` active-only
   registry actually receiving rows in autom8_data? (Collapses blocker-B if yes.)
2. **Denominator drift:** has the SHIP-DARK vertical enum-option-SET ever synced? Is the
   `(office_phone, vertical)` denominator congruent with autom8_data's view?
3. **Blocker-A shape:** is the payment→offer join a missing *extractor column*, a missing
   *metric definition*, or an upstream *autom8_data contract* gap? (Sizes Crusade-1.)

## Open questions (must answer before committing build capacity)
- EXTRACTOR-vs-METRIC-vs-CONTRACT (theoros) · REGISTRY-POPULATION (iris live-probe) ·
  DENOMINATOR-DRIFT (theoros/iris) · EXPORTS-OBS-COVERAGE — do the post-census
  `sli_heartbeat.py` + `event_loop_monitor.py` already cover it? (theoros/know) ·
  DRIFT-GUARD-SOURCE-BINDING (theoros) · IDOR-TEST-PRESENCE (security-audit).

**Evidence grade:** `[STRUCTURAL | MODERATE]` — code-inspected, not premise-propagated; the two
denominator questions need a live prod/data probe to confirm, which is exactly Crusade-0.
