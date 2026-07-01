---
type: review  # arch architecture-assessment (sprint-3 health/anti-pattern classification artifact)
artifact_subtype: arch-architecture-assessment
initiative: dyn-enum-contract
rite: arch
sprint: 3-of-5 (topology -> dependency -> STRUCTURE -> remediation -> adversary)
generated_by: structure-evaluator
created: 2026-06-30
status: draft  # WIP-uncommitted per operator no-auto-commit discipline
rung: assessed  # G-RUNG: this artifact reaches "ASSESSED" only — anti-patterns CLASSIFIED, NOT ranked/recommended (sprint-4) and NOT validated/proven (10x-dev beyond the seam)
producer_truth_anchor: "autom8y-asana origin/main (ca28251d) — NOT cwd chore/bump-core-4.6.0 (f4f924d2, OFF-ANCHOR)"
consumer_truth_anchor: "autom8y-data HEAD (92d3606d, branch main)"
legacy_source_anchor: "autom8 monorepo main (5c749c11) — NON-CANONICAL frozen-legacy"
ec1_status: "MySQL (authoritative receipt inherited from dependency-map §4; NOT re-litigated)"
evidence_grade_ceiling: "MODERATE (self-ref per G-CRITIC; STRONG requires rite-disjoint arch-adversary downstream)"
upstream: dependency-analyst (sprint-2)
downstream: remediation-planner (sprint-4)
---

# Architecture Assessment — dyn-enum-contract sync seam

Architectural-health classification of the `dyn-enum-contract` telos: *one typed, additive,
FK-safe sync contract carrying an Asana enum-option-set change into `autom8y-data.verticals`*.
This station CLASSIFIES the coupling/topology the prior maps assembled — boundary alignment,
anti-pattern disposition, SPOF/cascade severity, the DEFER-1 boundary-as-structural-decision,
and a risk register (severity AND leverage). It does **not** re-trace edges, rank remediations,
or recommend solutions (sprint-4 territory).

**Rung discipline (G-RUNG):** ASSESSED only. No finding here is validated/proven/ready-to-build.
Every classification carries a LIVE `{path}:{line}` inherited from the maps (G-PROVE) and a
falsifiable RED-then-GREEN framing the 10x build will later fire (G-THEATER). Adjective-without-
receipt is rejected.

Anchor legend (inherited verbatim from the maps; spike numbers are STALE and NOT used):
- **[P]** producer `autom8y-asana` @ origin/main (ca28251d)
- **[C]** consumer `autom8y-data` @ HEAD (92d3606d)
- **[SDK]** SDK host `autom8y` @ HEAD · **[ads]/[sms]/[sched]** downstream Python consumers · **[L]** legacy `autom8`

Confidence rubric (this station): **High** = corroborated by dependency-map coupling data AND
topology-inventory structural evidence; **Medium** = structural pattern with partial corroboration;
**Low** = single-source text match. Evidence grades cite `arch-ref` (AQ/DP/AV registry).

---

## 0 · Method + False-Positive Three-Check Gate (anti-pattern-inflation guard)

Every detected pattern passes a three-check gate BEFORE it enters the risk register as an
anti-pattern (correction for anti-pattern inflation; per `dk-evaluator-calibration`):

1. **Intentional-trade-off check** — could this be a deliberate architectural decision?
2. **Bounded-context / context-aware-coupling check** — did the dependency-map already clear this
   coupling as intentional + bounded-context-aligned? (If so, do not re-flag.)
3. **Evidence-sufficiency check** — is the evidence strong enough to distinguish from a false positive?

The dependency-map already ran the coupling-context three-check on the `verticals` hub (§5.a) and
cleared it as **intentional, bounded-context-aligned, unidirectional (no cycle)**. This station
HONORS that clearance: the hub's high afferent coupling is NOT re-flagged as a coupling anti-pattern.
What this station classifies is the *consequence* of the (correct) hub topology — its blast-radius —
and the *write-path integrity* the contract must carry. Disposition tokens: **FLAGGED** (genuine
anti-pattern/hazard), **CLEARED** (passes gate as non-pattern or accepted trade-off), **ACCEPTED-
TRADE-OFF** (real tension, deliberately borne, watch-registered).

---

## 1 · BOUNDARY ALIGNMENT — does the contract boundary match the domain?

### 1.a Route `/vocabularies/sync` THROUGH `VerticalService` — **ALIGNED** (bespoke store MIS-ALIGNED)

**Verdict: ALIGNED.** Routing the sync through the existing canonical writer is the boundary-
preserving choice; a bespoke `vocab_upsert` store is MIS-ALIGNED (it fragments write-ownership and
manufactures the exact second-writer condition the maps were watching for). Confidence: **High**
(corroborated by topology structural evidence AND dependency-map coupling data).

Evidence chain:
- `verticals` is a GLOBAL bounded-context stable reference hub: Ca HIGH, Ce≈0, **I≈0.0** (maximally
  stable) [dependency-map §5.a] [AQ:SRC-006 Martin 2002 — package metrics]. GLOBAL-entity scoping at
  [C] `routes/factory.py:354`.
- **SINGLE canonical writer**: `VerticalService.create` — `self._session.add(vertical)` at
  [C] `services/vertical.py:212` (in `create()` [C] `:149`). No other writer to the dimension
  (U-3 DuckDB-write RESOLVED NEGATIVE [dependency-map §7]).
- **No-delete invariant ALREADY modeled** across all three surfaces: service [C] `services/vertical.py:9`
  ("No Delete operation (verticals are permanent)"), proto [C] `proto/autom8/data/v1/__init__.py:667`,
  gRPC handler [C] `grpc/handlers/vertical.py:128` (create handler, no delete handler).

The additive-upsert, DELETE-forbidden contract IS already the domain's stated invariant [PV BONUS].
By DDD bounded-context + aggregate-root discipline [DP:SRC-005 Evans 2003], the Vertical entity is a
single aggregate with a single canonical writer; routing the sync through `VerticalService` preserves
the single-writer invariant (SRP [DP:SRC-002 Martin 2003]). A bespoke store would create a SECOND
writer to the SPOF hub — multiplying the corruption surface (§2.2) and breaking the additive-upsert
exclusivity the entire contract depends on (the G-HALT FORK-3 watch condition [dependency-map §10]).

**Structural caveat (FLAGGED, carried to risk register R3):** `VerticalService.create` is **create-only
today** ([C] `:149/:212` — `add(vertical)`, no update path). Composing-with therefore requires
EXTENDING the service with an `update-name` (upsert) path. The compose-with is aligned; the update-name
half is **net-new behavior**, and it is precisely where the dual-unique rename-collision hazard (§2.5)
concentrates. Aligned boundary, net-new write-surface.

**Falsifier (build will fire):** assert the `/vocabularies/sync` write path resolves to
`VerticalService` (single writer preserved) — grep that no new vocab-store class/table writes
`verticals` outside `services/vertical.py`. RED = a second writer (bespoke `vocab_upsert`) appears →
write-ownership fragmented → exclusivity broken.

### 1.b Generic `/vocabularies/sync` + `field_key` discriminator vs vertical-specific — **ALIGNED-WITH-WATCH** (justified thin hedge, NOT speculative generality — provided it stays thin)

**Verdict: a bounded forward-compatibility hedge, NOT speculative generality — CONDITIONAL on the
discriminator staying thin.** This is the calibration **boundary case** (reasonable assessors disagree);
per ATAM the generic boundary must be evaluated against the quality attribute it serves before
classifying [AQ:SRC-003 Kazman et al. 2000]. Confidence: **Medium** (boundary case, partial
corroboration).

The trade-off surfaced explicitly:
- **For speculative-generality (YAGNI risk):** DEFER-1 N≥3 is **NOT FIRED** — vocab would be the 2nd
  `field_key`-class binding and data the 1st vocab consumer [PV PREMISE-5]. Only ONE vocab (vertical)
  crosses the seam today. A generic multi-vocab endpoint for a single instance is the textbook
  premature-generalization shape.
- **For justified-hedge:** the expensive generality (the fleet registry that would unify the 4
  read-consumers) is correctly DEFERRED (§4). What remains generic is THIN — an endpoint path plus one
  discriminator field, NOT a registry/dispatch abstraction. A generic path lets a future 2nd vocab bind
  the same endpoint with a different `field_key`, no new route.
- **Denominator correction:** the 4-consumer fragmentation does **NOT** directly justify the generic
  *write* endpoint — the 4 consumers bind on the READ side (SDK/local/FK), not via `/vocabularies/sync`.
  The only structural justification for generic is the **future-vocab** axis (other `asana_configured`
  fields; `values_source` door carries 3 modes at [P] `annotations.py:50`). That is a single forward bet
  leaning on a not-yet-fired trigger.

**Disposition:** ALIGNED as a thin hedge; the line it must not cross is **hedge-creep** — if the
`field_key` path accretes per-vocab dispatch/branching logic at build time, it crosses from naming-hedge
into speculative generality (and into registry-by-stealth, violating G-DEFER).

**Falsifier:** assert the `field_key` discriminator carries NO per-vocab branching at build (one code
path, discriminator is data not control-flow). RED = `if field_key == "vertical": … elif …` dispatch
machinery → speculative generality confirmed → the hedge became the registry without the N≥3 gate.

### 1.c Ownership direction asana → data — **ALIGNED** (correct dependency direction)

**Verdict: ALIGNED.** Confidence: **High**.

- Asana owns the AUTHORITATIVE source-of-record: `enum_options` at [P] `models/custom_field.py:113`
  (Vertical custom-field GID `1182735041547604`) [dependency-map §1.d #4].
- The producer structurally DEFERS the vertical vocabulary to Asana: `values_source:"asana_configured"`
  + `valid_values:"dynamic"` at [P] `dataframes/annotations.py:222/:232` [topology §5 #5].
- data `verticals` is the terminal CANONICAL store [C] `_platform.py:131/:142`; direction is
  **unidirectional** producer → consumer [dependency-map §1.a].

This is correct dependency direction per Clean Architecture [DP:SRC-003 Martin 2017]: the authoritative
source owns the vocabulary; the store is a downstream MATERIALIZATION. One-way ingestion is correct —
data must NOT write back to Asana. The no-delete/create-only posture of `verticals` is the structural
*expression* of upstream ownership: data cannot delete a vertical because it does not own the vocabulary
authority; it can only additively mirror what Asana defines. **Additive-upsert (DELETE-forbidden) IS
"Asana owns, data ingests" rendered as a write-constraint.**

**Noted nuance (not a misalignment):** "canonical" is overloaded across the seam — Asana is
*authoritative-for-the-vocabulary* (membership/naming authority) while data.verticals is
*canonical-for-the-fleet* (the FK-parent everyone joins). This is a sound CQRS-shaped split (upstream
write-authority, downstream distribution-hub) and is precisely WHY the contract must be additive: data
may neither invent nor delete verticals, only reflect the upstream set.

**Falsifier:** assert no write path from data → Asana for vocabulary (one-way holds); assert the
producer reads `enum_options` as source-of-record and never treats data.verticals as authority. RED = a
back-write or a data-authoritative branch → ownership inverted.

---

## 2 · ANTI-PATTERN CLASSIFICATION

### 2.1 Distributed-monolith risk — **CLEARED** at runtime/deploy; **residual schema-drift sub-risk FLAGGED** (conditional)

**Disposition: CLEARED** as a distributed monolith; one conditional residual flagged.
Three-check: intentional (flag-gated expand/contract) ✓ · bounded (unidirectional, no cycle) ✓ ·
evidence sufficient ✓ → CLEARED.

Reasoning:
- The dependency is **UNIDIRECTIONAL** (asana → data), **no cycle** — ADP not violated
  [dependency-map §5.a directionality check].
- The deploy ordering (data endpoint must exist before the producer enables push) is standard
  **expand/contract (parallel-change)** sequencing — the CORRECT pattern for additive API evolution,
  the *opposite* of distributed-monolith lockstep.
- The producer push is **flag-gated**: `GID_PUSH_ENABLED` at [P] `services/gid_push.py:62` (gate read
  `:95`). The flag DECOUPLES enable-from-deploy: producer ships with flag off, data ships the endpoint,
  the flag then flips. The flag is a structural decoupler, not a coupling.

**Residual sub-risk (FLAGGED, conditional → R6):** the typed contract introduces a shared request/response
SCHEMA across two repos. Today the "contract" is an untyped hand-built dict — `"vertical": str(vertical)`
at [P] `gid_push.py:490` → `vertical: str` at [C] `api/models_comparison.py:62`. If the typed models are
DUPLICATED on each side rather than shared via the existing typed conduit (autom8y-core SDK,
[SDK] `clients/data_intake.py:473`), then schema changes require coordinated cross-repo edits =
hidden release-coupling. This is a **potential distributed-monolith (Low-Medium confidence, conditional
on implementation choice, which is 10x-dev's).** The SDK is the live de-duplication reuse point (§6).

**Falsifier:** (a) data endpoint deploys and serves with producer flag OFF (no producer dependency);
(b) producer flips flag against an already-deployed endpoint with NO data redeploy. RED on either =
lockstep confirmed. For the sub-risk: assert the typed contract model is imported from ONE home (SDK),
not defined twice. RED = two divergent model definitions across repos.

### 2.2 FK-parent SPOF + CASCADE PATH — **ACCEPTED-TRADE-OFF hub / HIGH-severity blast-radius**; write-path integrity is the actionable risk

**Disposition: the HUB is an ACCEPTED architectural trade-off (centralized reference data — NOT a
coupling anti-pattern); the CASCADE is a HIGH-severity SPOF/reliability concern that elevates write-path
integrity to safety-critical.** Confidence: **High** (corroborated by dependency-map §2 FK fan-in + §6
data-flow + topology §3 DuckDB read). This is the **highest-leverage finding**.

**Why the hub is NOT a coupling anti-pattern (three-check honored):** the dependency-map §5.a coupling-
context check already cleared the high Ca as intentional, domain-cohesive, unidirectional, ADP-clean.
I≈0 is the CORRECT posture for shared reference data [AQ:SRC-006 Martin 2002]. "De-coupling the hub"
would be the WRONG move — it would manufacture the very 4-way vocabulary divergence that §2.3 flags as a
hazard. Per ATAM [AQ:SRC-003 Kazman et al. 2000], the hub trades modifiability for consistency/single-
source-of-truth; that trade-off is DEFENSIBLE for reference data. The cost it concentrates is blast-radius.

**CASCADE PATH — trace of a mis-keyed / orphaned vertical (magnitude, inherited from the maps):**

1. **Lead-enrichment PRIMARY** — `Campaign.vertical_id == Vertical.vertical_id` join at
   [C] `core/repositories/dimension_enrichment.py:144` (J1). A mis-keyed vertical breaks campaign→vertical
   enrichment → paid leads enriched with wrong/NULL vertical.
2. **Lead-enrichment FALLBACK** — `Business.default_vertical_id == Vertical.vertical_id` at
   [C] `dimension_enrichment.py:166` (J2). The organic-lead fallback joins the SAME parent dimension —
   so a corrupt vertical breaks BOTH lead routes. **There is no independent redundancy: the "fallback"
   shares the single point.** (Reverse joins J3/J4 at `:328/:340` carry the same exposure.)
3. **7 FK edges** [dependency-map §2.a] — Campaign E1 [C] `_advertising.py:80`, AssetVertical junction
   E2 `:322/:326`, **Offer.category STRING FK** E3 [C] `_platform.py:162`, Business FALLBACK E4 `:72`,
   Question E5 `:451`, Payment soft/generated E6 `:419`, cross-repo scheduling E7 [sched] `shared.py:48`.
   Int-id FKs survive a wrong-NAME/right-ID row (referential integrity holds, semantics corrupt) but
   fail on a MISSING row; the **STRING FK (E3, `verticals.key`)** orphans on any key rename (§2.4); the
   **soft/generated ref (E6)** silently de-aligns (no enforcement).
4. **4 downstream consumers** [dependency-map §1.b] — SDK #1 serves `VerticalsListResponse`; ads #2
   validates against its own LOCAL list (drift); sms #3 carries denormalized fields; scheduling #4 shares
   the FK. The mis-key propagates fleet-wide via 4 conduits.
5. **DuckDB analytics READ** — `LEFT JOIN verticals` at [C] `analytics/core/infra/enrichment_views.py:152`
   propagates vertical key DOWNWARD onto fact tables (leads/calls/messages/payments) [dependency-map §6].
   Because it is a LEFT JOIN, a MISSING vertical → NULL attribution (silent loss); a MIS-KEYED vertical →
   WRONG attribution (silent corruption). **The cascade fails silently, not loudly.**

**Cumulative anti-pattern multiplier** [AQ:SRC-004 Mo et al. 2019]: the write target carries (a) god-hub
fan-in, (b) dual-unique collision surface (§2.5), (c) string-FK fragility (E3), (d) soft-ref non-
enforcement (E6). Accumulation multiplies error-proneness — which is why the *write-path integrity* (not
the hub topology) is the actionable structural risk.

**SEVERITY: HIGH** (fleet-wide + silent). **Actionable structural risk = write-path integrity**
(hard-refuse §2.6 + additive-upsert correctness + rename guard §2.5), NOT hub decoupling.
**Magnitude UV-P:** exact blast-radius row counts (`asset_verticals` ~43K asserted, unverified) are
DEFERRED — no DB creds in env [dependency-map §7 U-1]. Severity is classified on structural reach, not
fabricated counts.

**Falsifier:** build writes a mis-keyed vertical (and separately renames an existing key) → assert the
producer referential-coverage hard-refuse (§2.6) blocks it BEFORE it reaches the dimension; a LEFT-JOIN
attribution test asserts no silent NULL/wrong vertical lands on fact rows. RED = a bad vertical publishes
and cascades silently to facts.

### 2.3 Vocabulary fragmentation (4-conduit) — **FLAGGED** (real anti-pattern); per-instance contract is NEUTRAL-to-REDUCING on source, does NOT entrench, does NOT collapse read-side

**Disposition: FLAGGED** as a fragmentation anti-pattern; the per-instance contract neither entrenches
nor collapses the read-side split. Confidence: **High** (each conduit carries a live receipt; divergence
documented in dependency-map §9 Shared Model Registry).

The SAME vertical vocabulary is materialized **four divergent ways** [dependency-map §1.b/§5.c]:
- #1 SDK typed — `VerticalsListResponse` [SDK] `clients/data_intake.py:473` (the "good" conduit).
- #2 ads-LOCAL — `VerticalNormalizer.normalize(body.vertical_key)` [ads] `api/creative_performance.py:90`
  (import `:24` `from autom8_ads.intelligence.vertical_scoring`). **A PARALLEL CANONICAL LIST** — a second
  source of truth that can DRIFT from data.verticals [dependency-map §9: "diverged (ads owns a parallel
  vocab)"]. This is the most acute fragment.
- #3 sms-LOCAL — denormalized `default_vertical_key: str` + `vertical_id: int` [sms] `models/conversation.py:169`.
- #4 scheduling — shared-schema FK `verticals.id` [sched] `models/shared.py:48` (no local table; shared-DB).

Per DDD [DP:SRC-005 Evans 2003], a single bounded-context concept should have ONE canonical representation
with consumers binding through a consistent anti-corruption layer. Four materializations (one of them an
independently-owned parallel authority) is a fleet-wide consistency hazard.

**Does the per-instance contract REDUCE or ENTRENCH it?**
- The contract governs the **WRITE seam** (asana → data.verticals). It REDUCES *source-side* fragmentation:
  it replaces the untyped `str` write (§2.1) with a typed, integrity-guarded materialization, hardening
  the canonical store the consumers COULD unify around.
- It does NOT touch the **READ side** — ads still owns its normalizer, sms still denormalizes, scheduling
  still shares-FK. So it is **NEUTRAL to the 4-way read fragmentation**.
- It does **NOT ENTRENCH** — it adds no 5th conduit (it is a write path, not a new read materialization).
- It does **NOT COLLAPSE** the read split either — only the deferred fleet registry (§4) would do that.

**Classification: real anti-pattern, partially addressed (source hardened) and watch-registered for the
read side (DEFER-1).** Severity **MODERATE** (drift risk, not acute correctness — ads' parallel list is
the locus). This is the structural INPUT to the DEFER-1 assessment (§4).

**Falsifier:** post-contract, assert the producer→data write carries a typed/validated vocab payload
(no `str(vertical)` passthrough at [P] `gid_push.py:490`). Separately, the drift hazard is falsifiable by
diffing ads' `VerticalNormalizer` list against data.verticals — RED = ads carries a vertical data does not
(or vice versa) → active drift confirmed.

### 2.4 Six-sources fragmentation — **CLEARED** (no 7th materialization; authoritative pipeline formalized)

**Disposition: CLEARED.** The contract does NOT add a 7th materialization and does NOT worsen source
fragmentation (this was the G-HALT FORK-3 condition, checked and cleared [dependency-map §10]).
Confidence: **High**.

The 6 sources [dependency-map §1.d / topology §5] resolve to a clean live pipeline:
- #1/#2/#3 legacy (`Vertical(Enum)` [L] `…/vertical/main.py:19`, `VERTICAL_NAMES` `:261`, `db_verticals()`
  `:12`) — **frozen, ISOLATED, zero inbound import edges** (grep-confirmed [dependency-map §3]). Inert residue.
- #4 Asana `enum_options` [P] `custom_field.py:113` — AUTHORITATIVE source (contract reads here).
- #5 asana `SEMANTIC_ANNOTATIONS` [P] `annotations.py:50` — the producer-internal DOOR that points #4
  at the vertical field (not a separate vocabulary source).
- #6 data `verticals` [C] `_platform.py:131/:142` — the TARGET (contract writes here).

The contract establishes a clean **#4 (authority) → #6 (store)** pipeline; #5 is the producer door. It
does NOT garbage-collect the 3 frozen-legacy sources, but those are already severed (no live edge), so
their non-collapse is benign — frozen residue, not live fragmentation. Effectively the contract COLLAPSES
the *live* source picture to a single authoritative pipeline; legacy GC is a separate concern, not this
contract's job.

**Falsifier:** grep that the contract introduces NO new vocab-storing table/enum/list beyond data.verticals
(producer reads #4, writes #6, full stop). RED = a new vocab cache/table appears → 7th materialization →
fragmentation worsened.

### 2.5 Dual-unique rename → UPDATE-collision — **FLAGGED** (real write-path hazard on the net-new update path)

**Disposition: FLAGGED** as a genuine correctness hazard on the net-new UPDATE-name path. Confidence:
**High** (both unique constraints carry live receipts; the additive-upsert-on-key-also-writes-name shape
is structurally confirmed).

The dimension carries TWO unique constraints [dependency-map §2.c]:
- `vertical_key` UNIQUE — [C] `_platform.py:146` (`Field(unique=True, sa_column_kwargs={"name":"key"})`) —
  the upsert MATCH key (portable, stable).
- `vertical_name` UNIQUE — [C] `_platform.py:147` (`Field(unique=True, …{"name":"name"})`) — a SECOND
  unique index.

An additive upsert keyed on `vertical_key` that ALSO writes `vertical_name` has a structural collision
surface on the `name` index. Three concrete hazards the build's update-name path MUST guard:
1. **Rename collision** — Asana renames a vertical (same option-GID, new display name); upsert matches on
   key, UPDATEs name → throws if the new name is already held by another key row.
2. **Name-swap collision** — Asana swaps two names (A→B, B→A); sequential single-statement UPDATEs collide
   mid-swap on the name unique index (classic unique-update ordering problem).
3. **First-sync key-mismatch** (see R7) — if `vertical_key` is derived from name on first sync against a
   pre-populated table, derivation skew collides on key or name.

This hazard concentrates on the UPDATE-name path, which is **net-new** (VerticalService.create is
create-only today, §1.a) — and it is the locus of the NAME-keying compose-up lock (§4). It connects to
ownership direction (§1.c): because Asana OWNS rename authority, renames WILL occur and the contract MUST
handle them. **SEVERITY: MODERATE-HIGH** — fails loudly (constraint throws, not silent corruption) but can
BLOCK syncs (availability) or, if mishandled by catch-and-skip, leave the store stale.

**Falsifier:** build fires (a) rename a vertical to a name held by another key → assert deterministic
handling (two-phase update OR refuse-with-clear-error — NOT a raw constraint throw and NOT a silent skip);
(b) a name-swap A↔B test. RED = naive single-statement `ON DUPLICATE KEY UPDATE name=…` throws on the
name unique index.

### 2.6 Empty/truncated-publish blast-radius — **FLAGGED as a structural NECESSITY** (producer referential-coverage hard-refuse REQUIRED; leaf-calibration is WRONG for the hub)

**Disposition: FLAGGED** — the producer referential-coverage hard-refuse is a structural NECESSITY, and
the existing leaf-calibrated guard is the WRONG posture for the vertical contract. Confidence: **High**
(leaf-guard receipts live; additive-upsert necessity PV-confirmed; cascade surface dependency-mapped).

The existing producer guard treats "nothing to push" as success: `return True  # Nothing to push is not a
failure` at [P] `services/gid_push.py:328` and `:554`. This is correctly **leaf-calibrated** for the
gid-mappings / account-status paths, where an empty push is a benign no-op.

For the VERTICAL vocabulary contract that calibration INVERTS, because of the §2.2 cascade:
- The additive-upsert (DELETE-forbidden) design ALREADY mitigates the catastrophic **empty-WIPE** case:
  additive means an empty read ADDS nothing and DELETES nothing → no-op, not a dimension wipe. This is WHY
  additive-upsert is mandatory — `verticals` has **no `source` column** (snapshot-replace is structurally
  impossible; account-status' `DELETE … WHERE source=…` at [C] `_platform.py:497-498` cannot be applied)
  [PV PREMISE-3].
- The RESIDUAL the additive design does NOT cover is **TRUNCATED-with-rename / partial coverage**: a
  partial Asana read (API hiccup, pagination truncation, transient error) that applies a SUBSET of renames
  can de-align the string-FK (Offer.category, E3) and leave the dimension internally inconsistent.

So the structural necessity: the producer needs a **referential-coverage hard-refuse** — refuse to publish
when the read is incomplete relative to the referential surface, rather than fall through to "nothing to
push is not a failure." The leaf guard says "empty is fine"; the hub contract requires "under-covered is a
FAILURE," because the downstream is a SPOF hub (§2.2), not a leaf. **SEVERITY: HIGH** (this is the guard
that prevents an upstream read-glitch from triggering the cascade). **High leverage** — a producer-boundary
guard, low effort, fleet-wide blast-radius prevention.

**Falsifier:** build mocks Asana returning an empty/truncated `enum_options` → assert the producer
HARD-REFUSES the publish (does NOT reach the `gid_push.py:328/:554` "nothing to push is not a failure"
fall-through on the vocab path); assert additive-upsert holds (no existing vertical deleted even if a
partial slips). RED = producer publishes a truncated vocabulary that renames a subset and orphans
Offer.category references.

---

## 3 · SPOF / Cascade Register (consolidated)

| SPOF node | Failure mode | Cascade path (traced, inherited) | Redundancy? | Severity |
|-----------|--------------|----------------------------------|-------------|----------|
| `verticals` dimension [C] `_platform.py:131/:142` | mis-keyed / orphaned / renamed row | J1 campaign-PRIMARY `dimension_enrichment.py:144` → J2 business-FALLBACK `:166` (shared parent) → 7 FK (E1–E7) → 4 consumers → DuckDB `enrichment_views.py:152` LEFT-JOIN onto facts | **NONE** — fallback shares the single point; LEFT-JOIN fails silently | **HIGH** (fleet-wide, silent) |
| `VerticalService.create` sole writer [C] `services/vertical.py:212` | single write-path; net-new update-name path unguarded | dual-unique throw (§2.5) blocks sync; or silent-skip leaves store stale | single-writer is intentional (protects hub) | **MOD-HIGH** |
| producer push conduit [P] `gid_push.py:163` (flag `:62`) | truncated/empty upstream read published | empty-WIPE mitigated by additive-upsert; truncated-rename de-aligns string-FK (§2.6) | flag-gate + additive-upsert partial | **HIGH** (pre-hard-refuse) |
| Offer.category STRING-FK E3 [C] `_platform.py:162` | key rename orphans string references | string FK does not cascade like int FK → dangling category | none | **MOD-HIGH** |

The SPOF concentration is the *consequence* of the (correctly) centralized reference hub. The mitigation
posture is **write-path integrity**, not hub decoupling (decoupling would re-introduce the §2.3
fragmentation). Single-writer + additive-upsert + hard-refuse + rename-guard together form the integrity
envelope around the SPOF.

---

## 4 · DEFER-1 BOUNDARY AS A STRUCTURAL DECISION (ASSESS-ONLY; G-DEFER honored — registry NOT recommended into scope)

**Structural verdict: the per-instance compose-up-ready contract is the RIGHT boundary at N<3, and the
3 compose-up locks are a SOUND hedge that keeps the fleet registry a future option without committing to
the one-way door. The 4-consumer fragmentation does NOT structurally force the registry SOONER.**
Confidence: **High** on the reasoning (N<3 state PV-confirmed; one-way-door discipline sound).

The DEFER-1 decision: ship a per-instance vertical contract now; defer the fleet vocabulary registry until
N≥3 fires (2nd `field_key`-class binding AND 3rd vocab consumer) [PV PREMISE-5].

**Does the fragmentation (§2.3) argue the registry is needed sooner? — Assessed: NO.**
1. **Read/write separability** — the 4-consumer fragmentation is a READ-side concern; the telos is a
   WRITE-side contract. The immediate typed/FK-safe write does not require the registry. They are
   separable structural problems.
2. **One-way-door discipline** — the registry is a high-cost, hard-to-reverse commitment. The N≥3 gate is
   the correct trigger-discipline for one-way doors: do not walk through until a 2nd concrete instance
   proves the generalization. Building it on a single instance is the speculative-generality failure (§1.b).
3. **The hedge keeps the option open** — deferral costs little because the per-instance contract is
   registry-COMPATIBLE by construction.

**Do the 3 locks SUFFICE as the hedge?**
- **Generic path `/vocabularies/sync`** — SUFFICIENT: a 2nd vocab binds the same endpoint with a different
  `field_key`, no new route. (Caveat §1.b: keep thin.)
- **`field_key` discriminator** — SUFFICIENT for endpoint generalization. (Caveat: must not accrete
  per-vocab dispatch before N≥3, or it becomes registry-by-stealth.)
- **NAME-keying** — SUFFICIENT as a uniform cross-vocab identity scheme (a registry would key every vocab
  uniformly), BUT it is the LOCUS of the dual-unique rename-collision hazard (§2.5). The hedge carries a
  hazard: registry-compatible keying is also the collision surface.

**Disposition:** the DEFER-1 boundary is structurally sound; the locks suffice to avoid one-way-door
lock-in; the fragmentation is watch-registered, **escalate-only**. Per G-DEFER, I ASSESS and do NOT
recommend the registry into scope. **Escalation trigger (for remediation/future, not this scope):** when a
2nd vocab crosses the seam (N→2 `field_key`) OR a 3rd vocab consumer materializes, the registry re-enters
assessment. Residual watch: the hedge must stay thin (no dispatch machinery behind `field_key`).

**Falsifier:** assert the per-instance contract is registry-compatible without registry machinery — the
endpoint is generic, the discriminator is data-not-control-flow, the keying is uniform. RED (premature) =
registry/dispatch machinery present at N<3; RED (lock-in) = a vertical-specific endpoint that a 2nd vocab
could not reuse without a breaking change.

---

## 5 · RISK REGISTER (severity + leverage [impact/effort, 1–5] + receipt + falsifiable framing)

Leverage = impact / effort (PLATFORM-HEURISTIC: impact 1–5, effort 1–5; quick-win ≥3, strategic 1–3 &
impact≥4, long-term <1). Severity and leverage are CLASSIFICATION INPUTS; remediation-planner (sprint-4)
does the final RANK. Every risk carries a RED-then-GREEN the 10x build will fire (G-THEATER).

| ID | Risk | Sev | Impact | Effort | Leverage | Class | Receipt | Falsifier (RED-then-GREEN) |
|----|------|-----|--------|--------|----------|-------|---------|----------------------------|
| **R1** | FK-parent SPOF **silent** cascade (§2.2) | HIGH | 5 | 3 | 1.67 | strategic | [C] `dimension_enrichment.py:144`+`:166`; 7 FK §2.a; `enrichment_views.py:152` | write a mis-keyed vertical → assert producer hard-refuse blocks pre-cascade; LEFT-JOIN test asserts no silent NULL/wrong vertical on facts |
| **R2** | Empty/truncated-publish blast-radius — hard-refuse REQUIRED (§2.6) | HIGH | 5 | 2 | 2.5 | strategic | [P] `gid_push.py:328`/`:554` (leaf-calibration to invert); PV PREMISE-3 | mock empty/truncated `enum_options` → assert HARD-REFUSE (not "nothing to push is not a failure"); assert DELETE-forbidden holds |
| **R3** | Dual-unique rename → UPDATE collision on net-new update path (§2.5, §1.a) | MOD-HIGH | 4 | 2 | 2.0 | strategic | [C] `_platform.py:146` (key uq) + `:147` (name uq); writer `services/vertical.py:212` | rename to a name held by another key → assert deterministic handling (2-phase / refuse-clear), not throw/silent-skip; name-swap A↔B test |
| **R4** | offers.category STRING-FK fragility on key rename (§2.2 E3) | MOD-HIGH | 4 | 2 | 2.0 | strategic | [C] `_platform.py:162` `foreign_key="verticals.key"` (col `category`) | rename `vertical_key` → assert Offer.category refs blocked (key immutable) or propagated; RED = orphaned category strings |
| **R5** | Vocabulary fragmentation — ads parallel canonical list drift (§2.3) | MODERATE | 3 | 5 | 0.6 | long-term | [ads] `creative_performance.py:90`; [sms] `conversation.py:169`; [sched] `shared.py:48`; reg §9 "diverged" | diff ads `VerticalNormalizer` list vs data.verticals → assert no drift; RED = ads carries a vertical data lacks (DEFER-1 watch — ASSESS only) |
| **R6** | Schema-drift release-coupling (distributed-monolith residual) (§2.1) | LOW-MOD | 3 | 2 | 1.5 | strategic | [SDK] `data_intake.py:473` (shared-via-SDK reuse) vs [P] `gid_push.py:490` (hand-built dict) | assert typed contract model imported from ONE home (SDK), not duplicated; RED = two divergent model defs cross-repo |
| **R7** | First-sync key-mismatch vs pre-populated dimension (§2.5) | MODERATE | 3 | 2 | 1.5 | strategic | [C] `_platform.py:146` (upsert match key); [P] `gid_push.py:123` (`parts[2]` untyped derive) | first sync against pre-populated verticals → assert existing rows match on key (no dup inserts); RED = derivation skew → duplicate verticals |
| **R8** | Untyped `str` seam (current state; the telos target) (§2.1) | MODERATE | 3 | 2 | 1.5 | strategic | [P] `gid_push.py:490` `"vertical": str(vertical)` → [C] `models_comparison.py:62` `vertical: str` | post-contract assert seam carries typed/validated vocab payload (no raw `str(vertical)`); RED = untyped str still crosses |

**Known-risk-map coverage check** (carried from the brief): additive-upsert DELETE-forbidden → the
mandatory invariant underpinning R1/R2 (no-delete [C] `services/vertical.py:9`); hard-refuse → R2;
rename-collision → R3; first-sync key-mismatch → R7; offers.category STRING edge → R4; empty-publish →
R2; FK-parent SPOF cascade → R1; fragmentation → R5. All known risks have a register entry + falsifier.

---

## 6 · LEVERAGE / REUSE SIGNALS (structural; real reuse vs false-friend — for remediation to rank)

| Signal | Receipt | Classification | Note |
|--------|---------|----------------|------|
| shape-B MySQL `INSERT … ON DUPLICATE KEY UPDATE` live exemplar | [C] `api/services/forwarding_binding_store.py:155/:218/:252/:315` | **REAL reuse (mechanism)** + **PARTIAL-friend** | The idempotent-write idiom transfers for the KEY match. It does NOT exercise the DUAL-unique (name) collision (§2.5) — the build cannot copy-and-done; the rename path is net-new. |
| `VerticalService.create` compose-with (single writer) | [C] `services/vertical.py:212` (in `create()` `:149`); no-delete `:9` | **REAL reuse (single-writer composition)** | Create + permanence invariant reuse directly. **Update-name half is NET-NEW** (create-only today) — compose means EXTEND, not just call. |
| `account-status/sync` typed-contract precedent | [C] `api/data_service_models/_account_status_sync.py:70/:113`; route `routes/account_status.py:4`; producer `gid_push.py:375/:564` | **REAL reuse (typed envelope/transport SHAPE)** + **EXPLICIT FALSE-FRIEND (semantics)** | The typed req/resp envelope shape is the right template. Its WRITE SEMANTICS are **snapshot-replace scoped by a `source` column** ([C] `_platform.py:497-498`). `verticals` has **no `source` column** → copying snapshot-replace would DELETE the SPOF hub. **Reuse the shape; DO NOT reuse the semantics — verticals is additive-only.** |
| autom8y-core SDK typed conduit | [SDK] `clients/data_intake.py:473` `VerticalsListResponse` | **REAL reuse (model home)** | The place to HOME the shared typed vocab model so the contract is not duplicated cross-repo (mitigates R6 schema-drift). The existing "good" typed conduit (#1). |

**The highest-value distinction:** the account-status precedent is RIGHT for the contract SHAPE and
DANGEROUS for the contract SEMANTICS. A build that mirrors account-status wholesale would inherit
snapshot-replace and wipe `verticals`. The reuse boundary is: envelope/transport YES, write-semantics NO.

---

## 7 · DEEP-DIVE: Architectural Philosophy + Module-to-Domain Alignment + Boundary-Decision Analysis

### 7.a Implicit architectural philosophy (extracted)

The seam encodes a **modular-monolith reference-data philosophy with upstream-source-of-record**, not a
service-autonomous microservices philosophy:
- **Reference-data-as-shared-stable-hub** — `verticals` is a GLOBAL ([C] `factory.py:354`), maximally
  stable (I≈0), single-writer, permanent (no-delete) dimension. The fleet FKs INTO one canonical store
  rather than each service owning its copy. Tell: scheduling SHARES the schema (FK into `verticals.id`,
  no local table — [sched] `shared.py:48`) — shared-DB reference sharing, a modular-monolith move.
- **Source-of-record upstream, materialize downstream** — Asana owns vocabulary authority; data
  materializes (CQRS-shaped read-model split, §1.c).
- **Additive-only permanence for reference data** — no-delete invariant + additive-upsert; reference data
  is treated as append-only ([C] `services/vertical.py:9`, proto `:667`).
- **Typed contracts at seams (aspirational) — untyped vertical seam (current)** — the account-status typed
  precedent + SDK typed conduit express a typed-seam aspiration; the vertical seam still rides untyped str
  ([P] `:490` → [C] `:62`).

### 7.b Where practice DIVERGES from philosophy

| Divergence | Philosophy says | Practice shows | Closed by |
|-----------|-----------------|----------------|-----------|
| D-α Typed seams | typed contracts (account-status, SDK) | untyped `str` on vertical seam ([P] `:490`→[C] `:62`) | **the dyn-enum-contract telos itself** |
| D-β Single canonical vocab | one canonical `verticals` store | 4-way read fragmentation; ads owns a parallel list ([ads] `creative_performance.py:90`) | the **deferred** registry (DEFER-1, §4) — NOT this scope |
| D-γ Single writer | one canonical writer (`VerticalService`) | a bespoke `vocab_upsert` store would diverge | the **compose-with** decision (§1.a) KEEPS practice aligned |

The telos closes D-α (the producer-edge divergence). D-β is correctly watch-registered (escalate-only).
D-γ is held aligned by routing through `VerticalService`.

### 7.c Module-to-domain alignment scoring (structural)

| Module | Domain it should own | Alignment | Evidence |
|--------|----------------------|-----------|----------|
| `verticals` + `VerticalService` | vocabulary distribution/materialization | **STRONG** | single writer [C] `vertical.py:212`, GLOBAL scope `factory.py:354`, I≈0, clean boundary |
| DuckDB analytics read | lead-enrichment (read) | **STRONG** | read-only join-through-verticals, no write (U-3 NEGATIVE); `enrichment_views.py:152` |
| producer push conduit (`gid_push`) | vocabulary-authority ingestion | **MODERATE** | vocab payload ENTANGLED in a general-purpose 2-path push helper ([P] `gid_push.py:163` shared by gid-mappings `:338` + account-status `:563`); rides as untyped str on the account-status path — the vocab-sync concern is not cleanly modularized |
| ads consumption | ad scoring (should CONSUME, not own vocab) | **WEAK** | ads OWNS a parallel canonical list (`VerticalNormalizer`) — a domain-boundary violation: ad-scoring should not hold vocabulary authority |
| sms / scheduling consumption | their service domains | **MODERATE** | sms denormalizes (acceptable for its bounded context); scheduling shared-FK crosses the service boundary (shared-DB coupling) |

**Net:** alignment is STRONG at the core (the verticals dimension + analytics read) and DEGRADES at the
edges (producer-conduit entanglement; ads parallel-ownership). The telos improves the producer edge (a
typed contract de-entangles the vocab payload from the general push); the deferred registry would improve
the ads/consumer edge.

### 7.d Deep boundary-decision analysis — WHY the boundaries exist where they do

- **Why `verticals` lives in data (not asana)** — data is the FK-parent hub for the fleet's lead-
  enrichment + analytics (7 FK children + DuckDB joins). The store sits where join-density is highest
  (data gravity); Asana is the AUTHORITY but not the STORE. Co-location with FK children + analytics is
  correct. Boundary exists at the join-density maximum.
- **Why single-writer (`VerticalService`)** — `verticals` is a SPOF hub; multiple writers multiply the
  corruption surface (§2.2). Single-writer concentrates write-integrity where the hard-refuse + rename
  guard belong. Boundary exists to protect the high-blast-radius hub.
- **Why additive-only (no delete)** — Asana owns vocabulary authority and `verticals` has 7 FK children;
  deleting a vertical orphans children. Boundary (no-delete) exists because of FK fan-in + upstream
  authority — and because `verticals` lacks a `source` column, snapshot-replace is structurally impossible
  ([C] `_platform.py:497-498` vs `verticals` schema), forcing additive.
- **Why per-instance contract (not registry)** — N<3; only one vocab crosses the seam. Boundary exists at
  the YAGNI/one-way-door line; the 3 locks keep the registry a deferred option (§4).

---

## 8 · Unknowns — structural decisions requiring human / business context (G-CRITIC: escalate, do not assume intent)

### Unknown: U-1 (carried) — FK fan-in row counts size the cascade blast-radius
- **Question**: actual row counts on `asset_verticals` (~43K asserted, unverified) and the other inbound
  verticals FK tables.
- **Why it matters**: weights the SEVERITY of R1/R2 (a 43K-row junction vs a 50-row table changes the
  blast-radius magnitude, not the structural classification).
- **Evidence**: structural FK edges confirmed [dependency-map §2.a]; no DB creds in env to run
  `SELECT COUNT(*)` → carried `[UV-P: inbound-FK row counts | METHOD: bash-probe (live MySQL) | REASON:
  no DB creds at this altitude]`.
- **Suggested source**: live MySQL query by operator / dependency-analyst with creds.

### Unknown: U-A — is there a committed 2nd `asana_configured` vocab on the roadmap?
- **Question**: does product have a committed second vocabulary (beyond `vertical`) to sync through the
  seam in the foreseeable horizon?
- **Why it matters**: resolves the §1.b boundary case — a committed 2nd vocab moves the generic endpoint
  from "thin forward hedge" toward "justified by near-term reality"; no 2nd vocab keeps it a speculative-
  generality watch. It also informs the DEFER-1 N≥3 escalation timing (§4).
- **Evidence**: `values_source` door carries 3 modes ([P] `annotations.py:50`) but only `vertical` is
  `asana_configured`/`dynamic` on the traced surface; DEFER-1 N<3 [PV PREMISE-5].
- **Suggested source**: product roadmap owner / platform architecture.

### Unknown: U-B — is ads' `VerticalNormalizer` an INTENTIONAL parallel authority or accidental drift?
- **Question**: does ad-scoring legitimately need vertical groupings that differ from data.verticals
  (intentional bounded-context divergence), or is the local list accidental duplication that should bind
  the canonical store?
- **Why it matters**: distinguishes an accepted trade-off (ads owns a domain-specific vocab) from the R5
  fragmentation anti-pattern (accidental drift). Changes whether R5 is "accept + document" or "watch for
  the registry."
- **Evidence**: [ads] `api/creative_performance.py:90` + import `:24` `from autom8_ads.intelligence.vertical_scoring`;
  [dependency-map §9] "diverged (ads owns a parallel vocab)".
- **Suggested source**: ads-service domain owner.

### Unknown: U-C — `values_source:"mixed"` semantics the contract must handle
- **Question**: when is a field's `values_source` `"mixed"` vs `"asana_configured"` (the third frozenset
  value at [P] `annotations.py:50`)?
- **Why it matters**: the vocab-sync contract must handle every `values_source` mode; `"mixed"` is
  undefined-in-code (zero dispatch logic [dependency-map §7 U-7]). The vertical field is `asana_configured`
  (so `"mixed"` is OFF the vertical path today), but a generic `/vocabularies/sync` (§1.b) would eventually
  meet it.
- **Evidence**: sole occurrence [P] `annotations.py:50`; no consumer logic traced.
- **Suggested source**: producer-domain owner / git history of `annotations.py`.

---

## 9 · Cross-Rite Observations (noted for remediation-planner to convert into referrals — not classified here)

- **Quality lens** — the untyped `str` seam ([P] `gid_push.py:490` → [C] `models_comparison.py:62`) is a
  type-safety surface; the typed contract closes it but the broader fleet pattern of untyped vocab payloads
  may interest a code-quality review.
- **Quality / consistency lens** — ads/sms maintaining LOCAL vertical vocabularies (own normalizer /
  denormalized fields) is a fleet-wide vocabulary-drift surface beyond this contract's write seam (R5).
- **Reliability lens** — the GET_LOCK/RELEASE_LOCK serialization primitive is PROSPECTIVE (0 hits in the
  consumer tree [dependency-map §4]); concurrent sync serialization on the SPOF hub is an SRE-adjacent
  concern the 10x build introduces.

---

## 10 · Handoff Status + Evidence-Grade Ceiling + Acid Test

### Exit-criterion completeness

| # | Exit criterion | Present? | Evidence-complete? |
|---|----------------|----------|--------------------|
| 1 | Boundary alignment (1a route-through-VerticalService / 1b generic endpoint / 1c ownership) | **YES** (§1) | YES — each verdict + receipt + falsifier |
| 2 | Anti-pattern classification (distributed-monolith / FK-SPOF cascade / fragmentation / six-sources / dual-unique / empty-publish) | **YES** (§2) | YES — each FLAGGED or CLEARED with receipt + three-check |
| 3 | DEFER-1 boundary as structural decision (ASSESS-only, G-DEFER) | **YES** (§4) | YES — locks assessed, registry NOT recommended into scope |
| 4 | Risk register (severity + leverage + falsifiable) | **YES** (§5) | YES — 8 risks, each sev+impact/effort+leverage+receipt+RED-then-GREEN |
| 5 | Leverage/reuse signals (real vs false-friend) | **YES** (§6) | YES — 4 signals classified, account-status false-friend surfaced |
| + | DEEP-DIVE: philosophy + module-to-domain alignment + boundary-decision analysis | **YES** (§7) | YES |
| + | SPOF register with cascade paths | **YES** (§3) | YES |
| + | Unknowns (structural decisions needing human context) | **YES** (§8) | YES — U-1 carried, U-A/B/C escalated |

### Gates bound

- **G-PROVE** — every classification carries a LIVE `{path}:{line}` inherited from the maps; no
  adjective-without-receipt. ✓
- **G-CRITIC** — see ceiling below. ✓
- **G-DEFER** — DEFER-1 ASSESSED (§4); registry NOT recommended into scope; escalate-only. ✓
- **G-THEATER** — every risk/finding carries a falsifiable RED-then-GREEN. ✓
- **G-RUNG** — rung ASSESSED; nothing validated/proven/ready-to-build. ✓
- **G-DENOM** — classified against the REAL consumer set (4 vocab consumers + DuckDB read); 66 `*-wt-*`
  worktrees excluded; 2 border consumers (admin-ui/fe-skeleton, junction-CRUD) excluded. ✓

### Evidence-grade ceiling (explicit)

**MODERATE (self-referential ceiling, per G-CRITIC `self-ref-evidence-grade-rule`).** This station's own
architecture verdict caps at MODERATE — a STRONG architecture verdict requires rite-disjoint external
critique, which is the **arch-adversary (sprint-5)** downstream. I do NOT self-grade STRONG. Individual
upstream receipts (the maps' coupling/topology evidence) are High-confidence at their stations; the
synthetic CLASSIFICATION here is MODERATE-ceilinged. Findings classified `[STRUCTURAL | MODERATE]` per
`evidence-grade-vocabulary` — they concern boundary decisions, coupling topology, and write-path integrity
(architecture-level), not sprint-local code edits.

### Acid test

*Can remediation-planner RANK and prioritize recommendations using ONLY this assessment + the prior
artifacts, WITHOUT re-classifying any structural concern?*
→ **YES.** Every risk register entry (§5) carries severity, impact/effort, leverage, a `{path}:{line}`
receipt, and a falsifiable framing. Every boundary verdict (§1) is decided (aligned / aligned-with-watch /
mis-aligned) with evidence. Every anti-pattern (§2) is dispositioned (FLAGGED / CLEARED / ACCEPTED-TRADE-
OFF) with the three-check shown. The DEFER-1 boundary (§4) is assessed with the escalation trigger named
but not recommended. Reuse signals (§6) are pre-classified real-vs-false-friend. The remediation-planner
ranks; it does not need to re-evaluate any structural concern.

**Rung:** ASSESSED. **Status:** draft (WIP-uncommitted; no auto-commit; dirty tree not staged).
