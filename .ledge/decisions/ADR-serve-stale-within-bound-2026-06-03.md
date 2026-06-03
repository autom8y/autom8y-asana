---
type: decision
status: draft   # canonical lifecycle status; semantic state = AUTHORED-NOT-RATIFIED (ratification_state below)
ratification_state: authored-not-ratified
id: ADR-serve-stale-within-bound
date: 2026-06-03
author: platform-engineer + observability-engineer (sre)
initiative: cr3-fleet-data-plane-foundation-cutover
consumer_visible: true
review_required_before_impl: false   # the mechanism is additive + inert; RATIFICATION (calibrating the bound) is OQ-2-gated
ratification_gate: OQ-2 (elicited per-entity freshness contract from monolith owners)
supersedes: none
related:
  - ADR-honest-empty-200-serving-2026-06-02
  - ADR-warm-set-reconcile-and-converge-2026-06-02
  - HANDOFF-autom8-to-asana-sre-cr3-producer-work-queue-ingest-2026-06-03
grounding: .sos/wip/cr3-verified-findings-2026-06-03.md  # V6
evidence_grade: moderate   # self-referential (sre rite authored the impl + this ADR) — MODERATE ceiling per self-ref rule
---

# ADR — Serve-stale-within-bound as the ratified freshness paradigm

## Status

**AUTHORED — NOT RATIFIED.** This ADR documents and proposes to *ratify* a freshness
paradigm that is **already implemented** in the receiver read path (see Context, V6). The
two code mechanisms it introduces (`meta.stale_served` attestation + a
`FRESHNESS_CONTRACT_MAX_AGE_SECONDS` per-entity ceiling override) ship **additive and inert**
— the override defaults to *no override*, preserving today's behavior exactly.

**Ratification is gated on OQ-2**: the per-entity freshness contract elicited from the
monolith/consumer owners. Until that contract is returned (handoff_back item E,
`HANDOFF-autom8-to-asana-sre-cr3-producer-work-queue-ingest-2026-06-03.md` §6), the bound
**MUST NOT be calibrated** and this ADR **MUST NOT be marked `accepted`**. An uncalibrated
bound is an arbitrary internal default masquerading as a consumer contract — exactly the
anti-pattern the ratified LICENSE forbids ("never relax the consumer = *meet the real need*";
the 50-min LKG default is a correctable internal policy, **not** a consumer contract).

Evidence grade: **MODERATE** (self-referential — the sre rite authored both the underlying
implementation and this ADR; per the self-ref MODERATE ceiling, no PASS/compliance conclusion
here rises above MODERATE absent rite-disjoint corroboration).

## Context

Serve-stale-within-bound is **NOT new architecture** — it is the receiver's *existing*
read-path behavior. The CR-3 producer work-queue (item 5 in the monolith's vantage) implicitly
treated serve-stale as something to *build*; verifier **V6** (`wf_91d1efdc`,
`.sos/wip/cr3-verified-findings-2026-06-03.md`) REFUTED that: it is already implemented up to
the Last-Known-Good (LKG) ceiling. Source-verified mechanism (canonical `src/`, this worktree):

The cache serve path implements a **3-state freshness paradigm** with a hard-reject ceiling, in
`DataFrameCache._check_tier_freshness` (`src/autom8_asana/cache/integration/dataframe_cache.py`):

1. **FRESH** (`age ≤ ttl`) — serve immediately, no refresh
   (`dataframe_cache.py:471-494`, `FreshnessState.FRESH`).
2. **APPROACHING_STALE** (`ttl < age ≤ SWR_GRACE_MULTIPLIER × ttl`, grace multiplier = `3.0`,
   `config.py:96`) — serve the cached frame **AND** trigger a stale-while-revalidate background
   refresh (`dataframe_cache.py:496-523`, `_trigger_swr_refresh`).
3. **STALE** (`age > grace`, structurally valid) — serve the entry as **LKG** + trigger refresh,
   **subject to the ceiling**: if `LKG_MAX_STALENESS_MULTIPLIER > 0` (default `10.0`,
   `config.py:115`) and `age > LKG_MAX_STALENESS_MULTIPLIER × ttl`, the entry is **hard-rejected**
   (evicted from memory, returns `None`) → cache-miss → `_build_on_miss` → **503 + Retry-After**
   honest backpressure (`dataframe_cache.py:525-546`). Below the ceiling it is served as LKG
   (`:548-584`) and `record_serving_stale` makes the stale-serve VISIBLE (`:557-562`, TD-007).

Beyond STALE: `SCHEMA_INVALID` / `WATERMARK_BEHIND` are unconditional hard-rejects
(`dataframe_cache.py:586-598`).

The honest-attestation surface already exists on the response model: `RowsMeta` carries
`freshness`, `data_age_seconds`, and `staleness_ratio`
(`src/autom8_asana/query/models.py:354-427`), plumbed from the serve-path `FreshnessInfo`
side-channel via `EntityQueryEngine._get_freshness_meta` (`query/engine.py:498-507`) and spread
into the response at `engine.py:268-280`.

So the *only* genuinely-new work to ratify this paradigm is:
**(a)** an explicit `meta.stale_served: bool` attestation (was the served frame past TTL?), and
**(b)** a per-entity contract-driven ceiling override knob, calibrated to the elicited contract.

## Decision

Ratify **serve-stale-within-bound** as the receiver's freshness paradigm: the 3-state model
(FRESH / APPROACHING_STALE+SWR / STALE+LKG) with a **hard-reject ceiling that backpressures
(503+Retry-After) rather than serving unbounded-stale data as a flattered 2xx**. The ceiling is
the *honesty boundary*: below it we serve LKG and attest staleness; above it we refuse.

Two additive code mechanisms (this sprint, shipped inert):

1. **`meta.stale_served: bool`** on `RowsMeta` (`query/models.py`). Default `False`. Set `True`
   when the served frame's freshness state is **not FRESH** (i.e. served in APPROACHING_STALE or
   STALE/LKG). Derived in `engine._get_freshness_meta` from the serve-path `FreshnessInfo.freshness`
   string — never fabricated. This is the *boolean* companion to the existing `freshness` /
   `staleness_ratio` fields: a single unambiguous "was this read served stale?" signal for the
   consumer and for the S7 disaggregation (it lets the GetDfFallback-cause split distinguish a
   stale-serve from a fresh-serve without re-parsing the `freshness` enum string).

2. **`FRESHNESS_CONTRACT_MAX_AGE_SECONDS`** (`config.py`): a **per-entity** absolute max-age
   ceiling (seconds) that **overrides** the multiplier-derived ceiling
   (`LKG_MAX_STALENESS_MULTIPLIER × entity_ttl`) for entities that have a calibrated contract.
   Ships as **an empty mapping / `None` sentinel** = *no per-entity override anywhere* → today's
   multiplier-derived ceiling applies unchanged for every entity. The mechanism is **inert until
   a value is calibrated per OQ-2.** When a per-entity value is present, the STALE branch uses
   the explicit contract value as the authoritative ceiling for that entity (it expresses the
   consumer's actual tolerance), overriding the internal multiplier default.

**The dual lever (load-bearing reframe, V1×V6).** A *looser-but-validated* bound = fewer reads
trip the hard-reject ceiling = fewer over-ceiling cache-miss builds = less pressure on the
4-slot build semaphore (`build_coordinator.py:130-131`) = **fewer 502s** (PQ-1). A *tighter*
validated bound = more honest backpressure. Either way the bound is calibrated to the **real
need** (OQ-2), not chosen to flatter a metric. The freshness contract is the linchpin tying
freshness AND the 502 together — which is precisely why the bound must be *elicited*, not
guessed.

## What this ADR does NOT do (anti-strawman discipline)

It does **NOT** bake any concrete tier values. The monolith-vantage strawman tiers (e.g. a
4h / 60m / 15m / 24h per-entity schedule) are **explicitly NOT adopted** as real values — wiring
them in now would be OQ-fake: an internal guess presented as a consumer contract. The knob ships
with **value = None / empty mapping** (no override) and stays that way until OQ-2 returns the
actual per-entity freshness tolerance. This ADR is the *mechanism + paradigm ratification
proposal*; the *calibration* is a separate, OQ-2-gated change.

## Alternatives considered

1. **Status quo (no `stale_served`, multiplier-only ceiling).** The paradigm already works; do
   nothing. Rejected: the consumer cannot cheaply tell a stale-serve from a fresh-serve (must
   parse the `freshness` enum string), and the S7 GetDfFallback-cause disaggregation
   (`S7-GATE-FIDELITY`) needs a clean boolean to separate stale-serve from fresh-serve. And the
   ceiling is a *single* internal multiplier — there is no seam to express a per-entity consumer
   contract when OQ-2 returns one. Rejected because it leaves no calibration seam and no clean
   attestation.

2. **Calibrate the bound NOW with an internal best-guess (the strawman tiers).** Ship the knob
   *with* values (e.g. project=15m, section=15m, …). Rejected outright: this is the OQ-fake
   anti-pattern — an arbitrary internal default masquerading as a consumer contract, the exact
   thing the LICENSE forbids. The real freshness need is UNKNOWN; calibrating before eliciting
   relaxes the consumer on a guess.

3. **Relax `LKG_MAX_STALENESS_MULTIPLIER` globally (raise 10.0 → higher).** A single global lever
   does relieve build pressure (dual lever), but it is *not per-entity* and *not contract-bound*:
   it relaxes freshness uniformly for entities that may have tighter real tolerances. Rejected as
   the calibration mechanism; the per-entity override is the right seam. (The global multiplier
   stays as the *default* ceiling for un-contracted entities.)

4. **Derive `stale_served` at the API layer from `staleness_ratio > 1.0`.** Compute the boolean
   in the route handler instead of the serve path. Rejected: `staleness_ratio` is age/ttl and is
   `> 1.0` for both APPROACHING_STALE and STALE — but the *authoritative* served-state already
   exists as `FreshnessInfo.freshness` at the serve site; re-deriving it downstream from a ratio
   risks drift if the state thresholds change. Derive at the single source (`_get_freshness_meta`).

**Selected: 1's mechanisms done right = (a) `stale_served` derived at the serve-path source +
(b) a per-entity contract-override knob shipped inert.** Each rejected alternative is a genuinely
different locus (do-nothing / calibrate-early / global-relax / API-layer-derive), not a strawman.

## Consequences

- `meta.stale_served` is a new additive, consumer-visible response field. Additive only —
  `RowsMeta` is `extra="forbid"` on the **producer** side (it constructs the model), and the
  consumer bridge reads `meta` by key and ignores unknowns (verified for the sibling
  `honest_empty` field, ADR-honest-empty-200 §"Consumer coordination"). **Pre-ratification
  verification owed**: confirm the consumer's `bridge_response_to_df` does not strict-reject the
  additive `meta.stale_served` key (same owed-check as `honest_empty`).
- `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` is a new config seam. Shipped inert (no override) → **zero
  behavior change** at deploy. It only changes behavior once OQ-2 calibrates a per-entity value.
- The paradigm is now *named and ratifiable*: the honesty boundary (serve LKG below ceiling /
  backpressure above) is explicit, and the calibration seam is per-entity and contract-bound.
- Operability: `meta.stale_served` + the existing `record_serving_stale` EMF feed the
  `S7-GATE-FIDELITY` GetDfFallback-cause disaggregation (stale-serve vs honest-refusal vs
  capacity-502 read as distinct causes).

## Reversibility

Fully two-way door at the code layer this sprint: `meta.stale_served` is an additive boolean
(revertible); `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` ships as a no-op empty mapping (removing it
restores the multiplier-only ceiling). **No value is committed.** Ratification (calibrating the
bound to OQ-2) is the only one-way-door step, and it is deliberately deferred behind the OQ-2
gate. This is a REVERSIBLE-ONLY sprint deliverable: PR opened, ADR authored, **not** ratified,
**not** deployed-with-a-calibrated-bound.

## OQ-2 ratification checklist (deferred — do not complete this sprint)

- [ ] OQ-2 returned: per-entity freshness tolerance from monolith/consumer owners (handoff_back E).
- [ ] `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` calibrated to the elicited per-entity contract.
- [ ] Consumer bridge confirmed to accept the additive `meta.stale_served` key.
- [ ] Dual-lever effect re-measured: post-calibration over-ceiling build rate ↓ (PQ-1 relief).
- [ ] ADR status flipped `authored-not-ratified` → `accepted`; the bound recorded as a contract.
