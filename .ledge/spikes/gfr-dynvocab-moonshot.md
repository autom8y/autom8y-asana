---
type: spike
status: draft
slug: gfr-dynvocab
artifact_kind: moonshot-plan
rite: rnd
phase: future-architecture
agent: moonshot-architect
created: 2026-06-25
time_horizon: 2 years
g_rung: "feasibility-proven + paradigm-recommended (this rite CANNOT build/merge/lock — 10x-dev + MINE)"
self_grade: "[STRUCTURAL | MODERATE]"  # self-ref cap per self-ref-evidence-grade-rule + rnd-dk MODERATE ceiling; a STRONG paradigm-LOCK verdict needs the rite-disjoint corroboration at the transfer seam — named, never self-granted
critic_stance: "vantage-DISJOINT of the technology-scout recon (G-CRITIC). The recon's verdict was CONFIRM/meta-optimal; this artifact pressure-tests that verdict against 2-yr futures and dissents where the futures expose it."
upstream:
  - .ledge/specs/gfr-dynvocab-alignment-brief.md         # LOCKED INCEPTION (12 decisions; do NOT re-litigate)
  - .ledge/spikes/gfr-dynvocab-recon.md                  # technology-scout recommendation (the subject of this critique)
  - .ledge/spikes/gfr-dynvocab-integration.md            # integration-researcher map (hidden deps + phased migration)
  - .ledge/spikes/gfr-dynvocab-prototype-findings.md     # prototype-engineer feasibility-proven (HYP-1/HYP-2 LIVE-on-fixture)
  - .ledge/decisions/ADR-gfr-seam1-ride-options.md       # SEAM1 key shape + Option E (cross-tenant guard)
certified_base:
  worktree: /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr
  branch: feat/gfr-engine
  tip: 2092f771
  status: FROZEN CLEAN; 105 tests GREEN — strictly-additive-protected; the throwaway prototype MUST NEVER commit here
grandeur_anchor: >
  gfr-dynvocab makes any fleet caller resolve a gid to ANY field the entity
  actually carries — reflectively, heuristically-typed from cf-type metadata,
  governed-strict (so 'unknown' means genuinely absent) — on top of the
  STRONG-certified identity spine, never regressing it.
---

# MOONSHOT-gfr-dynvocab — Dynamic-Vocabulary Paradigm at the 2-Year Horizon

## Executive Summary

The recommended paradigm — **(f) Asana cf-type reflective coercion + (d-bounded)
dynamic-ORM-style tail + (b) Iceberg-style dataframe-coherence governance** — is
**feasibility-proven** (prototype resolves `asset_id`→set off the canary fixture)
and **paradigm-recommended** (recon, four-ecosystem convergence). This artifact
asks the only question those upstream rites could not: **does the chosen paradigm
hold when the world changes underneath it?**

**Headline verdict across five plausible 2-yr futures:**

| # | Future | Verdict | One-line reason |
|---|--------|---------|-----------------|
| 1 | 100x fields per entity | **SURVIVES (with one ADAPT)** | tail resolution is O(1) per requested field; the *risk is payload width on the entry fetch + the manifest-build cost*, both bounded and observable, not the resolver |
| 2 | New EntityTypes without code change | **ADAPTS** | the resolver is generic via the `custom_field_resolver_class_path` hook, but "without code change" is FALSE today — a new EntityType still needs an `EntityConfig` registration + the per-entity override/dtype context. The tail-resolution layer is generic; the *registration* is not |
| 3 | EU per-region schema / data-residency | **ADAPTS — and is the sharpest test of the recommendation** | the tail reads off the in-memory hydrated task, so it composes cleanly with a region-prefixed SEAM1 key; BUT Option E's cross-tenant gid re-assertion is the load-bearing guard, and a region dimension widens the key shape it must re-assert against. Composes, but the guard must be re-certified per-region |
| 4 | Fleet-scale schema governance (coherence as platform doctrine) | **BREAKS as chosen / ADAPTS as re-scoped** | Option A (per-repo CI drift gate) does NOT scale to a fleet doctrine — it is a per-repo, allow-list-maintained check with no cross-service contract registry. This is where a *different recon candidate* (SRC-002 Iceberg field-ID + a real schema/contract registry) looks better at horizon than the recon admitted |
| 5 | Asana cf-type model evolution (new types, formula, dependent fields) | **SURVIVES (degrades gracefully) — with one confirmed live gap** | the `case _ → display_value` fallback means new cf types never crash; they silently lose typing. BUT the `date` case already reads a sub-field (`date_value`) that is NOT in the live opt-fields tuple — a graceful-degradation gap that is real TODAY, not hypothetical |

**Net:** the paradigm is **robust where it claims to be (the tail resolver) and
brittle where the recon under-examined (the dataframe-coherence layer at fleet
scale, and the registration story behind "all-entities-generic")**. None of the
five futures BREAKS the *tail* paradigm; one (Future 4) breaks the *coherence
mechanism* the recon paired with it. The dissent is therefore **scoped**: keep
the tail, re-open the coherence-layer paradigm choice before it becomes a fleet
doctrine.

**Evidence grade: [STRUCTURAL | MODERATE]** — self-ref ceiling + rnd-dk MODERATE
cap. A STRONG verdict on the *coherence-layer re-scope* (Future 4) needs the
rite-disjoint corroboration at the transfer seam — named below, never
self-granted. This artifact does NOT lock, merge, or build anything; those levers
are the user's (10x-dev + MINE).

---

## Time Horizon

**2 years** (through ~2028-Q2). Anchored to the autom8y fleet's plausible growth:
more tenants, more EntityTypes, EU expansion pressure, and Asana's own custom-field
model evolution (it ships new cf subtypes roughly yearly).

---

## Current State

### Architecture Overview (verified at HEAD f4f924d2 + certified worktree)

```
                    ┌─────────────────────────────────────────┐
   gid ─────────────▶│ certified GFR spine (feat/gfr-engine)    │
                    │  entry.py → planner → guard → identity   │ ◀── STRONG-certified
                    │  (gid-exact company_id, parent-chain)    │     105 tests; SEAM1 Option E
                    └───────────────────┬─────────────────────┘
                                        │ EntryAnchor (4 fields; entry task DISCARDED at entry.py:111)
                                        │
   ┌────────────────────────────────────▼──────────────────────────────┐
   │ dynvocab TAIL (additive, is_identity=False branch — TO BE BUILT)   │
   │  reads entry-task.custom_fields (free, HYP-1) → heuristic_table     │
   │  (_extract_raw_value match resource_subtype) → overrides → set/typed│
   └────────────────────────────────────┬──────────────────────────────┘
                                        │ (separate layer)
   ┌────────────────────────────────────▼──────────────────────────────┐
   │ dataframe-coherence layer (curated schemas; ADR-S4-001 forbids     │
   │  codegen). Drift = model fields ⊅ schema columns (systemic).       │
   │  storage key: dataframes/{project_gid}/{entity_type}/…  (SEAM1)     │
   └────────────────────────────────────────────────────────────────────┘
```

### Key Constraints (load-bearing, verified)

- **The STRONG-certified spine is frozen-additive.** Nothing in this plan may
  regress the 105 tests; the throwaway prototype must never commit to
  `feat/gfr-engine`. (`gfr-tdd.md` §0.1 INVARIANT GFR-IDENTITY-1.)
- **ADR-S4-001: schemas are NOT generated from descriptor metadata** — a
  documented, one-way-door-on-reversal decision (`entity_registry.py:430-432`).
  The recon/integration map treat schema codegen (Option B) as the escalation
  path; this plan agrees it is one-way and treats Option A (CI drift gate) as the
  baseline — *and dissents that Option A scales to a fleet doctrine (Future 4).*
- **SEAM1 key shape `dataframes/{project_gid}/{entity_type}/…` is MANDATORY**
  (`ADR-seam1-entity-identity-key.md:103-104`); cross-tenant safety on the legacy
  fallback rests on Option E's gid re-assertion (`ADR-gfr-seam1-ride-options.md`).
- **`body_parameterized=False` offer-domain cache-only HARD line** — the tail
  inherits it (no new Asana call beyond the accounted entry read).

### Technical Debt Affecting the Future (verified, not asserted)

- **D1 — name-keyed override registry (prototype shortcut #4).** The prototype
  keys overrides by normalized name; production must key by cf `gid`
  (Iceberg/SRC-002 discipline). Until it does, *every rename of an Asana cf
  silently re-routes or drops the override.* This is the Future-2/Future-5
  fragility seam. (`default.py:81-97` keys `_index` by normalized name → gid;
  `_gid_to_info` already carries the gid.)
- **D2 — `date_value` is NOT in `STANDARD_TASK_OPT_FIELDS`.** Verified: a grep for
  `date_value` in `models/business/fields.py` returns **zero matches**, yet the
  heuristic table's `case "date"` reads `date_value` (`default.py:272-276`). On the
  LIVE entry fetch a `date` cf coerces to `None`, not its value. The prototype's
  "date → date_value: tested yes" is a *fixture* artifact; the live tail has a
  date-shaped hole TODAY. (Future-5 trigger fires already.)
- **D3 — first-match-wins on normalized-name collision** (`default.py:84-90`).
  Silent at present scale; a latent correctness bug at 100x fields (Future 1) and
  across heterogeneous new EntityTypes (Future 2).
- **D4 — per-entity dtype divergence of shared cf names** (integration map §4.1.6:
  `offer_id` is `Utf8` on Offer, `Int64` on AssetEdit). The heuristic table is
  per-entity-context, NOT global — the override registry must be EntityType-aware,
  which the prototype's single flat `OVERRIDE_REGISTRY` is not.

---

## Scenario Definitions

> Planning depth is allocated **proportional to probability** (anti-pattern guard:
> no multi-page roadmap for a <20% future while a >50% future gets a one-liner).
> Futures 1, 2, 5 are HIGH/MEDIUM probability and get full migration treatment;
> Future 4 is MEDIUM but HIGHEST-impact (it is where the recommendation may be
> wrong) and gets the deepest critique; Future 3 is MEDIUM-low probability and
> gets a contingency-grade path with explicit triggers.

### Scenario 1 — 100x fields per entity

**Probability**: MEDIUM-HIGH (tenants accrete custom fields monotonically; Asana's
own `total_fields` ceilings exist precisely because this happens)
**Impact if True**: MEDIUM

**Assumptions**:
- An entity's task carries 100x its current cf count (Offer: ~20 → ~2000 cf,
  approaching Asana's per-workspace field ceilings).
- Callers still request a small slice (the `resolve(gid, [fields])` shape).

**Triggers/Signals** (external, observable):
- **S1a**: Asana surfaces `total_fields.limit`-class warnings, OR a tenant's entry
  fetch payload (the `custom_fields` array on the entry task) crosses ~500 fields —
  measurable by logging `len(task.custom_fields)` at the entry seam.
- **S1b**: p99 of `build_index` / manifest-build time crosses ~5ms (today: 5.5µs
  for 20 fields per the prototype; linear, so ~550µs at 2000 — still cheap, but the
  *signal* is when the linear scan stops being free relative to the ~200ms fetch).
- **S1c**: the entry-fetch wire payload (not resolution) becomes the latency
  dominator — observable as entry-fetch bytes/latency growth uncorrelated with
  tree depth.

### Scenario 2 — New EntityTypes added without code change

**Probability**: HIGH (the brief's north-star is explicitly "all-entities by
design"; new EntityTypes are the expected growth vector)
**Impact if True**: MEDIUM-HIGH

**Assumptions**:
- A new EntityType (e.g. a future "Campaign" or "Creative" task type) is onboarded
  and expected to resolve its tail fields with zero GFR-tail code change.

**Triggers/Signals**:
- **S2a**: a PR adds a new `EntityConfig` to `entity_registry.py` (the registration
  event itself is the signal — grep the registry diff).
- **S2b**: a new EntityType's tail field is requested and returns
  `UnresolvedError(unknown-field)` for a field the entity *demonstrably carries* —
  the governed-strict contract violated by a registration gap, not a genuine absence.
- **S2c**: an override or dtype-context that was Offer-specific silently mis-fires
  on the new EntityType (D4 manifesting).

### Scenario 3 — EU per-region schema / data-residency

**Probability**: MEDIUM-LOW (plausible within 2 yr if the fleet takes EU tenants;
not yet on a roadmap visible in-repo)
**Impact if True**: HIGH (regulatory; cross-region leak is a compliance incident,
not a bug)

**Assumptions**:
- Data-residency requires region-partitioned storage:
  `dataframes/{region}/{project_gid}/{entity_type}/…` or a parallel per-region
  store, with a hard guarantee that an EU tenant's frame is never read from a
  US partition.

**Triggers/Signals**:
- **S3a**: a signed EU tenant, OR legal/compliance files a data-residency
  requirement — the inception of the requirement is the trigger, not "we feel like
  scaling."
- **S3b**: a region field appears in tenant config or the SEAM1 key shape proposal
  gains a `{region}` segment.
- **S3c**: Asana announces an EU data-hosting / regional API endpoint (external,
  Asana-side signal).

### Scenario 4 — Fleet-scale schema governance as platform doctrine

**Probability**: MEDIUM (the brief itself scopes "BOTH layers"; the autom8y
ecosystem is 5 services — model↔schema coherence is a natural fleet doctrine
candidate). **HIGHEST IMPACT** — this is where the recommendation is most exposed.
**Impact if True**: HIGH

**Assumptions**:
- The model↔schema coherence guarantee is promoted from a per-repo nicety to a
  fleet-wide contract: every autom8y-* service that consumes Asana entities must
  prove its schema is coherent with the shared model, enforced at a fleet altitude
  (a shared contract registry, not 5 independent CI checks).

**Triggers/Signals**:
- **S4a**: a SECOND autom8y service adopts the dataframe-schema pattern and hits
  the same drift class (the `asset_id`-smell recurs in a sibling repo).
- **S4b**: a cross-service field contract breaks in production — a field renamed in
  the model breaks a downstream consumer that bound by name, not gid.
- **S4c**: a platform doctrine RFC proposes "schema coherence" as a fleet standard
  (the doctrine-authoring event itself).

### Scenario 5 — Asana cf-type model evolution

**Probability**: HIGH (Asana ships new cf subtypes ~yearly: formula fields and
dependent/lookup-style fields are live or announced platform directions)
**Impact if True**: MEDIUM

**Assumptions**:
- Asana introduces cf subtypes the heuristic table does not enumerate (formula,
  dependent, relationship, or a new scalar), and/or deprecates a value sub-field.

**Triggers/Signals**:
- **S5a**: a `resource_subtype` value appears in a live task that hits the
  `case _` fallback — observable by logging fallthrough counts in `_extract_raw_value`.
- **S5b**: Asana developer-docs / changelog announces a new custom-field subtype
  (external, Asana-side).
- **S5c**: `display_value` becomes the resolved value for a field a caller expected
  typed — a typing-origin-tag `heuristic`/`fallback` ratio shift.

---

## Per-Scenario Stress Test (SURVIVES / ADAPTS / BREAKS)

### Future 1 — 100x fields: **SURVIVES**, with one ADAPT

**What breaks / what holds:**
- The *resolver* holds. `resolve(gid, [fields])` is an O(1) dict lookup per
  requested field against the gid-keyed index; 100x more fields the caller does NOT
  request cost nothing at resolve time. The prototype's 5.5µs/20-field figure
  scales linearly to sub-millisecond at 2000 fields — never the latency dominator.
- The *manifest build* (`build_index`, `default.py:59`) is a one-time O(N) scan
  over all the entity's cf — this is the only part that grows with field count.
  At 100x it is still ~sub-millisecond, but D3 (first-match-wins collision) becomes
  a real correctness risk: 100x fields → higher odds of two cf normalizing to the
  same name, and the loser is *silently dropped with only a warning*.
- The *real* pressure is the **entry-fetch payload width** — at 2000 cf the wire
  payload of the entry task grows, and that read is the certified, accounted one.
  This is an ADAPT, not a BREAK: it argues for a projected opt-fields fetch (request
  only the cf the caller needs) rather than the bare `custom_fields` that pulls all.
  But projecting defeats HYP-1's "free tail" — a genuine tension to surface, not
  resolve here.

**Verdict: SURVIVES.** The resolver paradigm is correct for this future. The ADAPT
is (a) promote D3 from warn to a collision-resolution policy, and (b) decide the
fetch-all-vs-project tradeoff when S1c fires.

**Reversibility**: the resolve path is a two-way door (internal implementation). A
projected-fetch optimization is a two-way door behind the entry seam. No one-way
commitments here.

### Future 2 — New EntityTypes without code change: **ADAPTS** (the claim is half-true)

**Disjoint finding — the recon and brief overstate "all-entities-generic."** The
*tail resolution mechanism* is genuinely generic: it is injected per-EntityType via
`custom_field_resolver_class_path` (`entity_registry.py:136`) and the prototype
proved the same `DynVocabResolver` class resolves Offer and Business with no
special-casing. **But "without code change" is false at three points I verified:**
1. A new EntityType requires a new `EntityConfig` registration (the dataclass at
   `entity_registry.py:142+` — name, pascal_name, schema_module_path, resolver
   class path, etc.). That is code.
2. Per-entity **dtype context** (D4): `offer_id` is `Utf8` on Offer but `Int64` on
   AssetEdit. A new EntityType that shares a cf name with a divergent business-type
   needs an EntityType-aware override entry — the prototype's flat name-keyed
   `OVERRIDE_REGISTRY` cannot express this.
3. The `case _ → display_value` fallback means a new EntityType's *novel* cf types
   degrade to strings silently — "resolves" but mistyped.

**Verdict: ADAPTS.** The tail layer is generic; the *registration + override
context* is not. The honest claim is "new EntityTypes resolve their tail fields
generically once registered, with EntityType-scoped overrides." The migration must
make the override registry gid-keyed AND EntityType-scoped (closes D1 + D4
together).

**Reversibility**: EntityType registration is config (two-way door — add/remove an
`EntityConfig`). Making the override registry EntityType-aware is a two-way door
(internal data structure). No one-way commitments.

### Future 3 — EU per-region data-residency: **ADAPTS** — the sharpest composition test

**Why this is the recommendation's sharpest test, not its easiest:** the recon
never examined region/residency. The tail's saving grace is *architectural luck*:
it reads off the **in-memory hydrated entry task**, not off a storage frame
(integration map §1.4). So the tail does NOT touch SEAM1 storage keys at all — a
region prefix on `dataframes/{region}/{project_gid}/{entity_type}/…` is invisible
to tail resolution. **The tail composes with per-region frames for free.**

**But the load-bearing risk is the identity spine, not the tail.** The certified
spine's cross-tenant guard is Option E's **gid-identity re-assertion on the legacy
fallback** (`ADR-gfr-seam1-ride-options.md` Option E). A region dimension:
- Widens the key shape the re-assertion must validate against (served-row gid ==
  anchored gid is gid-exact and region-agnostic, so the *re-assertion itself*
  survives — gid is globally unique). **GOOD: the gid-exact guard is region-robust
  by construction.**
- BUT the *legacy project-only fallback partition* is already multi-tenant; if it
  becomes multi-tenant AND multi-region, an EU tenant's row in a US legacy
  partition is now a *residency* violation even if the gid re-assertion would have
  rejected it on *tenant* grounds. The re-assertion guards tenant-correctness, NOT
  residency. **A region-scoped read-gate is a NEW guard the spine does not have.**

**Verdict: ADAPTS** — the tail composes cleanly; the spine needs a region-scoped
read-gate that is OUT of the tail's scope and OUT of this initiative's scope. This
is a **route-back-to-spine-owner** finding, not a dynvocab finding. The dynvocab
paradigm does not BREAK; it is residency-neutral. The dependency it surfaces (the
spine's region guard) is the user/spine-owner's, escalated.

**Reversibility**: a region prefix on the SEAM1 key is a one-way door for the
*storage layout* (data physically relocates; consumers bind to the new shape) —
this is the migration owner's call (the ADR already flags `legacy_fallback_enabled`
retirement as the one one-way door). The tail's region-neutrality is a two-way door
(it simply continues reading off the task).

### Future 4 — Fleet-scale schema governance: **BREAKS as chosen / ADAPTS as re-scoped**

**This is the dissent.** The recon paired the tail with **Option A (a per-repo CI
drift gate extending `_validate_extractor_coverage`, `registry.py:168`)** and
graded the whole composite "meta-optimal, CONFIRM." That grade is correct for a
*single repo*. It does **not** hold when coherence becomes a fleet doctrine, and the
recon's own counter-case evidence (SRC-002 Iceberg, SRC-005 Elastic) actually
points at a *different* answer than the one it recommended for the coherence layer:

1. **Option A does not compose across services.** It is a per-repo import-time
   check with a *hand-maintained allow-list* (integration map §3.2: "+2 days if the
   allow-list must be hand-curated per-entity for ~60 drifted fields"). Five
   services each maintaining an independent allow-list is not a doctrine — it is
   five drift gates that can disagree. There is no cross-service field *contract
   registry*; a field renamed in the shared model breaks any consumer binding by
   name (S4b), and Option A in repo X cannot see repo Y's binding.
2. **The recon's own SRC-002 (Iceberg) is the better fleet answer and it
   under-weighted it.** Iceberg's discipline is *type-by-field-ID + a schema/contract
   registry as the cross-consumer source of truth.* The recon folded only the
   "field-ID not name" refinement into Option A and dropped the *registry* half —
   precisely the half that matters at fleet scale. At horizon, a real **shared
   field-contract registry** (the cf `gid` → typed-contract mapping, versioned,
   consumed by all 5 services) is what makes coherence a doctrine. Option A is the
   single-repo shadow of that.
3. **This is NOT an argument to reverse ADR-S4-001 (codegen).** Codegen (Option B)
   is still a one-way door and still cannot synthesize cascade/derived columns. The
   re-scope is orthogonal: a *contract registry* governs the cf-`gid`→type mapping
   the tail and the schemas both consume; it does not generate schema files.

**Verdict: BREAKS as chosen (Option A as fleet doctrine), ADAPTS as re-scoped (Option
A stays the per-repo gate; a fleet contract-registry is the doctrine layer above
it).** The tail paradigm is unaffected — it consumes whichever contract source
exists. The dissent is confined to the coherence-layer paradigm choice, and it
fires only when S4a/S4c trigger (a second service or a doctrine RFC). Until then,
Option A is correct and the dissent stays a contingency.

**Reversibility**: Option A (per-repo drift gate) is a two-way door (delete the
check). A fleet contract registry is a **one-way door once 2+ services depend on
it** — which is exactly why it must be escalated to user/leadership before the
second service binds, not after. Building it speculatively for one repo would be
the low-probability over-investment anti-pattern; building it reactively after S4b
fires in prod is a cross-tenant/cross-service incident. The trigger (S4a: second
service hits the drift class) is the decision point.

### Future 5 — Asana cf-type model evolution: **SURVIVES (graceful degradation)** — with a live gap

**What holds:** the `case _ → display_value` fallback (`default.py:285-287`) is the
graceful-degradation mechanism. Any new `resource_subtype` Asana ships falls through
to `display_value` (a human-readable string) — the resolver never crashes, the field
still resolves to *something*, and the typing-origin tag would mark it `heuristic`/
`fallback`. This is exactly the degradation behavior a 2-yr-robust paradigm needs.
The brief's per-field override registry is the escape hatch to type a new subtype
correctly once it appears.

**What is already broken (D2 — verified live gap, not hypothetical):** the `case
"date"` reads `date_value`, but `date_value` is **NOT** in `STANDARD_TASK_OPT_FIELDS`
(grep: zero matches in `fields.py`). So a `date` cf on the live entry fetch is *not
requested* and coerces to `None` — a silent typing hole that exists at HEAD, masked
in the prototype by a fixture that hand-supplied `date_value`. Future 5's S5a/S5c
triggers are, in effect, **already firing for the `date` subtype.** This is the
single most concrete actionable finding in this plan: it is fixable now, in the
opt-fields tuple, independent of any future.

**Verdict: SURVIVES.** The fallback makes the paradigm robust to *unknown* future
subtypes. The immediate action is to close the *known* `date_value` opt-fields gap
and add a fallthrough counter so S5a is observable.

**Reversibility**: adding `custom_fields.date_value` to the opt-fields tuple is a
two-way door (one tuple entry; widens the fetch payload trivially). Adding override
entries for new subtypes is a two-way door (registry entries). No one-way doors.

---

## Future Architecture (the target the paradigm converges to)

### Vision

A **gid → any-field resolver** where the *tail is genuinely paradigm-stable* (it
will not need re-architecting under any of the five futures) sitting on a
**coherence layer that is explicitly two-tier**: a per-repo drift gate (Option A,
exists at horizon-start) AND a fleet field-contract registry (the doctrine layer,
built only when the second service triggers it). The override registry is gid-keyed
and EntityType-scoped. The opt-fields fetch is complete for every enumerated cf
subtype, with a fallthrough counter for the unenumerated.

### Key Changes

| Area | Current (HEAD) | Future (2yr) | Rationale |
|------|----------------|--------------|-----------|
| Override registry key | normalized name (proto shortcut #4) | cf `gid`, EntityType-scoped | survives renames (D1) + dtype divergence (D4); Iceberg field-ID discipline |
| opt-fields completeness | `date_value` missing (D2) | all enumerated subtypes requested | closes the live date-typing hole |
| New-subtype handling | `case _ → display_value` | same + fallthrough counter + typing-origin `fallback` tag | makes S5a observable; degradation already correct |
| Coherence governance | per-repo Option A only | Option A + fleet contract registry (gid→type) | per-repo gate does not scale to a 5-service doctrine (Future 4 dissent) |
| Name collision | first-match-wins + warn (D3) | explicit collision policy (gid-disambiguated) | 100x fields makes collisions probable |
| Region | project-partitioned only | spine gains region-scoped read-gate (OUT of dynvocab scope) | residency is a spine guard, not a tail concern (Future 3) |

### Technology Dependencies

| Technology | Purpose | Maturity | Risk |
|------------|---------|----------|------|
| Asana `resource_subtype` model | tail typing ground truth | mature/stable; evolves ~yearly | LOW — `case _` fallback absorbs evolution; D2 date gap is the known hole |
| cf `gid` as stable field identity | rename-survival + dtype context | live (`_gid_to_info` already keyed by gid) | LOW — already present, just unused by the proto override |
| Fleet field-contract registry | coherence doctrine across 5 services | **does NOT exist** — would be net-new | HIGH if built speculatively; this is the escalation, not a default |
| Region-scoped storage + spine guard | data-residency | does NOT exist; SEAM1 is project-partitioned | MED — owned by spine/migration owner, not dynvocab |

### Scaling Implications

- **10x fields**: no architectural change; resolve stays O(1)/field, manifest build
  stays sub-ms.
- **100x fields**: ADAPT D3 (collision policy) + decide fetch-all-vs-project at S1c.
- **10x EntityTypes**: ADAPT — registration + EntityType-scoped overrides; the tail
  resolver itself is unchanged.
- **5x services (fleet)**: the tail is unaffected; the coherence layer needs the
  registry (Future 4 dissent).

---

## Migration Path

> Builds on the integration map's P0–P5 (which this plan does not duplicate) and
> adds the *future-conditioned* phases F-A … F-D that the five scenarios surface.
> Each carries an explicit reversibility class and the trigger that opens it.

### Phase F-A — Close the known live gaps (do now, future-independent)
**Goal**: remove D1, D2, D4 before they become future-amplified incidents.
**Deliverables**:
- gid-keyed, EntityType-scoped override registry (closes D1 + D4).
- `custom_fields.date_value` added to `STANDARD_TASK_OPT_FIELDS` (closes D2).
- fallthrough counter + typing-origin `fallback` tag in `_extract_raw_value` wrapper.
**Investment**: ~2–3 dev-days (small, additive; on top of integration-map P1–P2).
**Reversibility**: TWO-WAY DOOR (all additive; revert by reverting the entries).
**Trigger**: none — these are correct regardless of which future arrives (the acid
test: if any future arrives in 18mo we will wish date typing worked; cost is trivial
→ do now).

### Phase F-B — Collision + scale hardening (when S1a/S1b fire)
**Goal**: make the manifest build correct and observable at 100x fields.
**Deliverables**: explicit normalized-name collision policy (gid-disambiguated, not
first-match-wins); `len(custom_fields)` + manifest-build-time metrics at the entry
seam.
**Investment**: ~2 dev-days.
**Reversibility**: TWO-WAY DOOR (internal policy in `build_index`).
**Trigger**: S1a (Asana field-limit warnings) OR S1b (manifest-build p99 > 5ms).

### Phase F-C — EntityType generality proof (when S2a fires)
**Goal**: prove "new EntityType resolves tail fields generically once registered."
**Deliverables**: a second+third EntityType resolves tail fields through the hook
with only an `EntityConfig` + override-context addition; an integration test that a
newly-registered EntityType's carried field resolves (catches S2b registration gaps).
**Investment**: ~2 dev-days per EntityType (integration-map G-DENOM figure).
**Reversibility**: TWO-WAY DOOR (config add/remove).
**Trigger**: S2a (a new `EntityConfig` lands).

### Phase F-D — Fleet coherence registry (ESCALATE; only when S4a/S4c fire)
**Goal**: promote coherence from per-repo gate to fleet doctrine via a shared
cf-`gid`→typed-contract registry.
**Deliverables**: a versioned field-contract registry consumed by ≥2 services;
per-repo Option A drift gate validates against it instead of a local allow-list.
**Investment**: LARGE / unscoped at this altitude — order-of-magnitude weeks, not
days; spans repos.
**Reversibility**: **ONE-WAY DOOR once 2+ services bind to it.** This is the
strategic bet requiring resource commitment — **escalate to user/leadership BEFORE
the second service binds.** Building it before S4a is the over-investment
anti-pattern; building it after S4b (a prod cross-service break) is firefighting.
**Trigger**: S4a (a second autom8y service hits the drift class) OR S4c (a doctrine
RFC). NOT before.

### Region-residency (NOT a dynvocab phase — route to spine owner)
The tail is residency-neutral; the spine needs a region-scoped read-gate. This is
escalated to the spine/migration owner if S3a fires, not built here.

### Decision Points

| Decision | When (trigger, not date) | Options | Implications |
|----------|--------------------------|---------|--------------|
| Fetch-all vs projected opt-fields | S1c (entry-fetch payload dominates latency) | keep free-tail / project per request | projecting defeats HYP-1 free-tail; only worth it at extreme width |
| Build fleet contract registry | S4a (2nd service) or S4c (doctrine RFC) | per-repo Option A only / + fleet registry | one-way once 2+ bind; ESCALATE |
| Region-scoped spine guard | S3a (EU tenant signed) | spine-owner scope | residency guard ≠ tenant guard; spine's call, not dynvocab's |
| Type a new cf subtype | S5a (fallthrough counter spikes) / S5b (Asana announces) | override entry / leave as display_value fallback | two-way; default to fallback until a caller needs it typed |

---

## Risk Analysis

### Scenario Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| 100x fields silently drop a collided cf (D3) | M | M | F-B collision policy; gid-disambiguation |
| New EntityType returns false `unknown-field` (S2b registration gap) | M | M | F-C registration integration test |
| EU tenant row read cross-region via legacy fallback | L (no EU yet) | CRITICAL (compliance) | spine region read-gate (escalated, F-3 route-back); gid re-assertion is tenant-safe but NOT residency-safe |
| Per-repo drift gates diverge across fleet (Future 4) | M | H | F-D contract registry — but ONLY on trigger; do not over-build |
| New Asana cf subtype mistyped as string | H | L | `case _` fallback already correct; F-A fallthrough counter makes it observable; override on demand |
| `date` cf resolves to None TODAY (D2) | **realized now** | M | F-A opt-fields fix (immediate) |

### Execution Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Over-build the fleet registry speculatively | M | H (wasted weeks + premature one-way door) | trigger-gate F-D on S4a/S4c; escalate, do not default |
| Tail change regresses certified spine | L | CRITICAL | 105-test gate; tail is `is_identity=False`, invisible to identity guard (integration map §1.1) |
| HYP-1 free-tail premise wrong at scale (fetch-all too wide at 100x) | M | M | S1c trigger + fetch-all-vs-project decision point; reversible |

---

## Investment Summary

| Phase | Trigger | Duration (order-of-magnitude) | Reversibility |
|-------|---------|-------------------------------|---------------|
| F-A (close live gaps) | none — do now | ~2–3 dev-days | two-way |
| F-B (collision/scale) | S1a/S1b | ~2 dev-days | two-way |
| F-C (EntityType generality) | S2a | ~2 dev-days/entity | two-way |
| F-D (fleet contract registry) | S4a/S4c — ESCALATE | weeks, cross-repo | **one-way** |
| Region spine guard | S3a — route to spine owner | (not dynvocab) | one-way (storage) |

**Total pre-trigger investment (F-A only): ~2–3 dev-days.** Everything else is
trigger-gated and reversible except F-D and region, both of which are explicit
escalations. **The plan's deliberate posture is minimal pre-commitment:** close the
known gaps now (cheap, future-independent), and hold the expensive one-way doors
behind observable external triggers.

---

## Strategic Implications

The dynvocab tail is a **safe long-horizon bet**: none of the five futures forces a
tail re-architecture, and its graceful-degradation fallback means Asana's own model
evolution cannot break it. The strategic exposure is entirely in the **coherence
layer**, which the recon under-examined: as the autom8y fleet grows from 1 to 5
schema-consuming services, "model↔schema coherence" stops being a per-repo CI nicety
and becomes a fleet contract problem that Option A cannot solve. The organization
should treat F-D as a *named future commitment with a defined trigger*, not as a
surprise — so that when the second service hits the drift class, the registry is a
considered investment, not an incident response.

---

## Disjoint Critique of the Technology-Scout Recommendation (G-CRITIC)

**The recon's verdict was "CONFIRM, meta-optimal, ADOPT the (f)+(d-bounded)+
(b-governance) composite." Reviewed from a vantage the recon did not occupy (the
2-yr horizon), the verdict holds for the tail and is incomplete for the coherence
layer. Specifically:**

1. **CONCUR on the tail (f)+(d-bounded).** Four-ecosystem convergence is real, the
   in-tree 80% is real, and all five futures confirm the tail is paradigm-stable.
   No recon candidate looks better than (f) for the tail at horizon — (c) GraphQL
   resolves only declared fields (the very limitation being escaped), (e) Elastic is
   the unbounded counter-case. The recon was right here.

2. **DISSENT on the coherence layer (b-as-Option-A).** The recon graded Option A
   (per-repo CI drift gate) as the meta-optimal coherence mechanism and folded only
   *half* of its own SRC-002 (Iceberg) evidence — the "field-ID not name" half — while
   dropping the *contract-registry* half. At single-repo scale this is fine. At fleet
   scale (Future 4, MEDIUM probability, HIGH impact) Option A **breaks as a doctrine**:
   5 services with 5 independent hand-maintained allow-lists is not coherence. The
   recon's own counter-case literature (Iceberg's registry, Elastic's mapping
   explosion under unbounded growth) points at a **shared field-contract registry** as
   the horizon answer — a candidate the recon had the evidence for but did not surface.
   This is a truncated-option-slate gap (per `option-enumeration-discipline`): the
   coherence-layer option set was enumerated for one repo, not for the fleet the brief
   itself scopes ("BOTH layers", 5-service ecosystem).

3. **CONCUR that codegen (Option B) stays escalated.** The dissent does NOT reopen
   ADR-S4-001; the contract registry is orthogonal to codegen and does not generate
   schema files. The recon and integration map were right to flag B as a one-way door.

4. **SURFACE two live gaps the upstream rites' fixtures masked.** D2 (`date_value`
   not in opt-fields → `date` cf resolves None on the live fetch) and D1+D4 (name-keyed,
   non-EntityType-scoped override registry) are *realized today*, not hypothetical
   futures. The prototype's "feasibility-PROVEN" is proven *on fixtures that
   hand-supplied the missing sub-fields*; the live tail has a date-shaped hole. This
   does not overturn feasibility — it scopes it: the tail is feasible AND has two
   known, cheap, future-independent fixes (F-A) that should precede any scaling work.

**Does a different recon candidate look better at horizon?** For the *tail*: no, (f)
is correct. For the *coherence layer*: yes — SRC-002 Iceberg *in full* (field-ID +
contract registry), not the half the recon adopted, is the better fleet-horizon
answer, and it should be the F-D escalation target. **The recommendation is
CONFIRMED-WITH-SCOPED-DISSENT, not CONFIRMED.**

---

## Recommendations

### Immediate Actions (do now, future-independent — the acid test passes for all)
1. **Close D2**: add `custom_fields.date_value` to `STANDARD_TASK_OPT_FIELDS`
   (`fields.py:232-251`). A `date` cf resolves to `None` on the live fetch today.
2. **Close D1+D4**: make the override registry cf-`gid`-keyed AND EntityType-scoped
   (the prototype's flat name-keyed registry is shortcut #4 + cannot express the
   `offer_id` Utf8/Int64 divergence).
3. **Add a fallthrough counter + typing-origin `fallback` tag** to the
   `_extract_raw_value` wrapper so Future-5 (S5a) becomes observable.

### Decisions Needed (with timing triggers, not dates)
1. **Fleet contract registry (F-D)**: escalate to user/leadership the moment S4a
   fires (a second autom8y service hits the drift class) — BEFORE the second service
   binds, because the registry is a one-way door. Do not build speculatively.
2. **Region residency**: route to the spine/migration owner if S3a fires (EU tenant
   signed); the tail is residency-neutral, the spine needs a region read-gate.
3. **Fetch-all vs projected opt-fields**: revisit when S1c fires; default to free-tail.

### What to Watch (the observable trigger board)
1. `len(task.custom_fields)` at the entry seam crossing ~500 (S1a/S1b — 100x onset).
2. A new `EntityConfig` landing in `entity_registry.py` (S2a — generality test due).
3. A second autom8y service adopting the dataframe-schema pattern (S4a — F-D trigger).
4. `_extract_raw_value` `case _` fallthrough count rising (S5a — new cf subtype live).
5. Asana developer-changelog announcing a new custom-field subtype (S5b — external).
6. A signed EU tenant or a compliance data-residency requirement (S3a — region route).

---

## Black Swan Section (what this plan cannot predict)

Scenario planning assumes the technology landscape evolves predictably. Paradigm
shifts that would invalidate these scenarios wholesale:
- **Asana deprecates the REST custom-fields model** (e.g. a GraphQL-only or
  event-stream API) — would force the tail's data-source, not its logic, to change;
  the heuristic table (resource_subtype → typed value) likely survives, the fetch
  path does not.
- **autom8y migrates off Asana as the system-of-record** — the entire (f) paradigm
  is platform-coupled (PLATFORM-HEURISTIC grade); a different SoR re-opens the whole
  recon. The cf-`gid` identity discipline (Iceberg-style) is the transferable part;
  the resource_subtype table is not.
- **A regulatory change requiring field-level provenance/audit** beyond the
  typing-origin tag (e.g. GDPR right-to-explanation on derived fields) — would
  promote the provenance tag from a nicety to a contract, intersecting Future 3.

These are acknowledged as outside the planning frame, not mitigated.

---

## Handoff / Attestation

**G-RUNG**: this rite reaches **feasibility-proven + paradigm-recommended-with-
scoped-dissent**. It CANNOT build, merge, or lock the paradigm — those levers are
the user's (10x-dev + MINE). The certified `feat/gfr-engine` spine was never touched.

**Self-grade**: `[STRUCTURAL | MODERATE]` — self-ref ceiling + rnd-dk MODERATE cap.
A **STRONG** verdict on the Future-4 coherence-layer dissent (the one place this plan
overrides the recon) requires the **rite-disjoint corroboration at the transfer
seam** — named here, never self-granted: the **tech-transfer → review-rite external
critic** (rite-disjoint from this rnd author) is the binding attester for the
coherence-layer re-scope, per the same R1 binding the GFR telos uses
(`.know/telos/gfr.md` `rite_disjoint_attester`).

### Artifact Attestation Table

| Artifact | Path | Verification |
|----------|------|--------------|
| This moonshot plan | `.ledge/spikes/gfr-dynvocab-moonshot.md` | authored this pass; structurally verified against live code below |
| Live code: `_extract_raw_value` match table + `case _` fallback | `src/autom8_asana/dataframes/resolver/default.py:234-287` | READ this pass — confirms D3 (first-match-wins :84-90), `case _ → display_value` (:285-287) |
| Live code: opt-fields tuple (D2 gap) | `src/autom8_asana/models/business/fields.py:232-251` | READ this pass + grep `date_value` → **0 matches** (D2 confirmed live) |
| Live code: EntityConfig + resolver hook | `src/autom8_asana/core/entity_registry.py:120-159` | READ this pass — confirms Future-2 "registration is code" |
| SEAM1 key shape + Option E guard | `.ledge/decisions/ADR-gfr-seam1-ride-options.md` | READ this pass — Future-3 region composition + residency-vs-tenant guard distinction |
| Upstream recon (critique subject) | `.ledge/spikes/gfr-dynvocab-recon.md` | READ this pass — the CONFIRM verdict under dissent |
| Upstream integration map (migration base) | `.ledge/spikes/gfr-dynvocab-integration.md` | READ this pass — P0–P5 phases, hidden deps D1/D3/D4 |
| Upstream prototype findings | `.ledge/spikes/gfr-dynvocab-prototype-findings.md` | READ this pass — feasibility-proven; date-fixture masking of D2 identified |
| Certified GFR telos (R1 attester binding) | `.know/telos/gfr.md` | READ this pass — rite-disjoint attester pattern carried |

*moonshot-architect | rnd rite | terminal phase | self-grade [STRUCTURAL | MODERATE]
(self-ref + rnd-dk cap) | STRONG on the coherence-layer dissent needs the
rite-disjoint transfer-seam corroboration — named (tech-transfer → review-rite
critic), never self-granted. This rite does NOT build/merge/lock — user-sovereign.*
</content>
</invoke>
