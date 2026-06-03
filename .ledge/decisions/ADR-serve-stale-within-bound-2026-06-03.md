---
type: decision
status: accepted   # canonical lifecycle status; semantic state = RATIFIED (ratification_state below)
ratification_state: ratified
ratified_date: 2026-06-03
id: ADR-serve-stale-within-bound
date: 2026-06-03
author: platform-engineer + observability-engineer (sre)
initiative: cr3-fleet-data-plane-foundation-cutover
consumer_visible: true
review_required_before_impl: false   # the mechanism is additive + inert; RATIFICATION (calibrating the bound) is OQ-2-gated
ratification_gate: OQ-2 (elicited per-entity freshness contract from monolith owners) — DISCHARGED 2026-06-03 (see §OQ-2 ratification checklist; contract source autom8/config/thresholds/caching.py)
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

**RATIFIED 2026-06-03.** This ADR documents a freshness paradigm **already implemented** in
the receiver read path (see Context, V6), and as of this ratification the
`FRESHNESS_CONTRACT_MAX_AGE_SECONDS` knob is **CALIBRATED to the OQ-2 contract** (no longer
inert). The `meta.stale_served` attestation remains an additive boolean.

**OQ-2 is DISCHARGED.** The per-entity freshness contract was returned by the consumer/monolith
owners. It was verified at SOURCE — not from handoff framing — in the consumer repo
`autom8y/autom8` at `config/thresholds/caching.py`:

| OQ-2 entity tier | Consumer source constant | Source line | Value (h) | Seconds | Keyed here? |
|---|---|---|---|---|---|
| PROJECT | `PROJECT_DF_REFRESH_HOURS = 24` | `caching.py:33` | 24 | **86400** | YES — `"project"` |
| SECTION | `SECTION_DF_REFRESH_HOURS = 0.16` | `caching.py:39` | 0.16 | **576** | YES — `"section"` |
| ANALYTICS (base-factory) | `BASE_FACTORY_REFRESH_HOURS = 24` | `caching.py:15` | 24 | 86400 | NO — no receiver entity_type |
| BACKFILL (reconciliation) | `RECONCILIATION_REFRESH_HOURS = 24` | `caching.py:28` | 24 | 86400 | NO — no receiver entity_type |
| VERTICAL-SUMMARY | `VERTICAL_SUMMARY_REFRESH_HOURS = 720` | `caching.py:22` | 720 | 2592000 | NO — no receiver entity_type |

**Why only PROJECT and SECTION are keyed.** The knob is `.get()`-ed on `entry.entity_type` in
the STALE branch of `dataframe_cache.py`. The only entity_types served through that serve-stale
path are the receiver dataframe entities registered in `entity_registry.py` — `"project"` and
`"section"`. The other three OQ-2 tiers are **consumer-side (autom8 monolith) refresh cadences
with NO corresponding entity_type in this receiver's cache keyspace**. Keying them here would
produce **dead keys** — an arbitrary internal mapping masquerading as a contract, the precise
anti-pattern this ADR's "What this ADR does NOT do" section forbade. They are intentionally
OMITTED from the calibrated map (see config.py knob comment for the full receipt trail).

**Section value transcription note.** `caching.py:39` source is `0.16` hours = **576 s exactly**;
the inline comment there glosses it as "~10 minutes". We transcribe the SOURCE value (576 s),
NOT the gloss (600 s). A round 600 s, if intended, is a consumer-side contract amendment at
`caching.py` — the receiver does not round.

Evidence grade: **MODERATE** (self-referential — the sre rite authored both the underlying
implementation and this ADR; per the self-ref MODERATE ceiling, no PASS/compliance conclusion
here rises above MODERATE absent rite-disjoint corroboration). **EXCEPTION**: the two calibrated
values (`"project"`=86400, `"section"`=576) are **STRONG** — they are consumer-corroborated,
read directly from the consumer's own `caching.py` source of truth (rite-disjoint: the consumer
monolith owns those constants, not the sre rite). The *paradigm ratification* is MODERATE; the
*calibration values* are STRONG by consumer corroboration.

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

### LOAD-BEARING TENSION — the calibration is a DUAL-EDGE ceiling (L4 sizing input)

The knob is a **max_age CEILING**, so calibrating it moves the hard-reject threshold per entity
in OPPOSITE directions, and the section edge makes the 502 hotspot WORSE in isolation:

- **Pre-calibration ceiling (both entities):** `LKG_MAX_STALENESS_MULTIPLIER (10.0) × ttl (300 s)
  = 3000 s = 50 min`. Both `project` and `section` carry `default_ttl_seconds = 300`
  (`entity_registry.py`), so both rode the same 50-min ceiling before this change.

- **`section` = 576 s TIGHTENS the ceiling 5.2×** (3000 → 576). Section frames now hard-reject and
  rebuild far sooner than before → **MORE over-ceiling cache-miss builds** → **MORE build pressure
  on the 4-slot semaphore** → the `POST /v1/query/section/rows` **502 hotspot gets WORSE**, not
  better. This is the direct, intended consequence of meeting the consumer's *real* 10-minute
  section freshness need — but it is a cost on the 502 axis.

- **`project` = 86400 s LOOSENS the ceiling 28.8×** (3000 → 86400 = 24 h). Project reads now ride
  serve-stale / LKG and almost never trip the hard-reject → **project over-ceiling rebuilds
  collapse toward zero** → project's contribution to 502 pressure largely disappears.

**Net for L4:** this knob ALONE does NOT relieve the section 502 — it INTENSIFIES it (tighter
section ceiling = more section rebuilds). The section 502 relief MUST come from a **≤10-min
section-tight warm lane** that keeps section frames warm *below* the 576 s ceiling so reads find
a fresh-or-within-bound entry instead of forcing an over-ceiling rebuild. **This ADR's section
value (576 s) is the hard sizing target L4 must design the section warm lane against**: the warm
cadence must be tight enough that a section entry's age stays under 576 s at read time across the
two heaviest GIDs. A dedicated fast lane for the two heaviest GIDs already exists in code
(`fast_lane_prematerialization_keys`, `core/project_registry.py:362`; `FAST_LANE_HEAVY_GIDS` =
DNA-holder + BusinessUnits, `:350`) — but its **invocation cadence is an EventBridge/IaC schedule
in the infra repo, not a source constant in this repo**, so its actual period is NOT verified here.
[UV-P: the existing heavy-GID fast lane runs on a ~15-min (≈900 s) cadence | METHOD: deferred-to-IaC-inspection (autom8y infra-TF EventBridge rule) | REASON: schedule is IaC-resident, not a src constant; not inspected this reversible pass]. **IF** that cadence is ≈900 s, it EXCEEDS the 576 s
section ceiling and is therefore NOT tight enough for the calibrated section contract — making
fast-lane re-sizing an explicit L4 input. The project edge needs no warm lane (24 h ceiling makes
project rebuilds rare by construction).

## Reversibility

Still a two-way door at the **code** layer: the calibrated `FRESHNESS_CONTRACT_MAX_AGE_SECONDS`
mapping is a source edit (revertible by restoring the empty mapping — that restores the
multiplier-only 50-min ceiling for both entities). This calibration PR is **REVERSIBLE-ONLY**:
PR opened, ADR ratified-in-doc, code calibrated — but **nothing landed**: NOT merged, NOT
deployed, NO terraform apply, NO config value pushed to a running env. The behavioral effect
(tighter section ceiling / looser project ceiling) only takes hold at deploy of the merged
calibration — which is a separate, human/IC-gated land step. Until then this is doc + source
diff on an unmerged branch.

## OQ-2 ratification checklist (DISCHARGED 2026-06-03 except deploy-gated items)

- [x] OQ-2 returned: per-entity freshness tolerance from monolith/consumer owners (handoff_back E).
      Source-verified in consumer repo `autom8y/autom8` at `config/thresholds/caching.py` (see Status table).
- [x] `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` calibrated to the elicited per-entity contract:
      `"project"`=86400 (caching.py:33), `"section"`=576 (caching.py:39). Other 3 tiers intentionally
      omitted (no receiver entity_type — dead-key avoidance).
- [ ] Consumer bridge confirmed to accept the additive `meta.stale_served` key. **STILL OWED** —
      cross-repo consumer-side check; not discharged by this calibration pass.
- [ ] Dual-lever effect re-measured: post-calibration over-ceiling build rate change (PQ-1).
      **DEPLOY-GATED** — measurable only after the calibration is merged + deployed; this pass lands nothing.
      WARNING per §Consequences: section edge is expected to INCREASE section over-ceiling builds until the
      L4 section-tight warm lane is sized to keep section age < 576 s.
- [x] ADR status flipped `authored-not-ratified` → `ratified` (frontmatter `status: accepted`);
      the bound recorded as a consumer contract with per-value caching.py receipts.
