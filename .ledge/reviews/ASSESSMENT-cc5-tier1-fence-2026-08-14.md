---
type: review
subtype: architecture-assessment
artifact_id: ASSESSMENT-cc5-tier1-fence-2026-08-14
artifact_type: architecture-assessment
initiative: chain-of-custody-closure
wave: chain-of-custody-closure (Phase 2)
sprint: CC-5 second-read (PHASE-3 rite-disjoint arch)
session: coc-phase-2
author: structure-evaluator (arch), rite-disjoint second seat
date: 2026-08-14
status: accepted
rung: rung-ASSESSED (read-only; no git write verb invoked; not committed)
second_reads: BUILD-cc5-tier1-offers-warm-2026-08-14
self_assessment_cap: MODERATE
scoped_blocking_axis: Tier-1 fence integrity
verdict: CONCUR-WITH-FLAGS
substrate_of_record: origin/main d7560153
under_test: coc-cc5-tier1-warm @ 6b75279f
---

# ASSESSMENT — CC-5 Tier-1 fence integrity (structural / boundary second-read)

> Rite-disjoint PHASE-3 arch second-read of `BUILD-cc5-tier1-offers-warm-2026-08-14`.
> I shaped none of this. Read-only: no git write verb invoked; the only files
> written are this assessment in the main tree's `.ledge/reviews/`. Every finding
> carries a `story_warmer.py:line` (worktree, post-change) or `artifact:line`
> anchor. Self-assessment ceiling MODERATE (single arch seat; no STRONG on the
> author). Tests were NOT re-run as evidence; I reason from the code structure
> (origin/main vs worktree diff) and the ruled fence.

---

## §0 SCOPED-BLOCKING VERDICT (Tier-1 fence integrity)

**CONCUR-WITH-FLAGS.** The change reorders the shared story-warm iteration, but
the reorder is the **budget-conserving, minimal-touch mechanism that executes the
ruled Tier-1 offers warm** — an unavoidable consequence of warming offer inside
one conserved invocation (charge disposition **(i)**), NOT a fleet-ordering
redesign smuggled under a Tier-1 label (charge disposition **(ii)**). The fence
holds. It does not BLOCK. Three flags ride the fence and are listed in §5.

The one sentence that decides it: **on a conserved single-invocation budget that
the mechanism table proves is fully consumed every run (`SLATE §1:60-63`, dies at
~7,460 tasks inside entities 1–4), there is no offers warm — not even the
SLATE's own literally-worded O-A "targeted second pass" — that does NOT displace
entities 1–4.** Displacement is entailed by the *decision to warm offer at all*
(ruled Tier-1 by `RULINGS R-1:16-24`), not introduced by the reorder. The reorder
is merely the only viable executor of that ruled decision.

---

## §1 What the change is, structurally (origin/main vs worktree)

**Pre-CC-5 (`git show origin/main:.../story_warmer.py`):** one sequential,
time-bound, first-come budget cascade — `for entity_type in completed_entities:`
drains each entity's story warms chunk-by-chunk until `_should_exit_early`
fires, then `break`. Budget exhausts inside the first four entities; offer
(cumulative slice 10,617–14,808) and entities 5–16 are enumerated but never
warmed. Sharing discipline: **whoever is first in the queue drains the budget;
the tail starves.**

**CC-5 (`story_warmer.py` @ `6b75279f`):** the loop now iterates
`warm_order = _build_warm_order(completed_entities, priority_entities)`
(`:428`, consumed at `:430`). `_build_warm_order` (`:115-153`) places priority
entities first (`:141-145`), then the remaining `completed_entities` **in their
original relative order** (`:147-151`). Default priority set is `("offer",)`
(`:68`). The budget MECHANISM is byte-for-byte unchanged: one
`asyncio.Semaphore(_STORY_WARM_CONCURRENCY)` with `_STORY_WARM_CONCURRENCY = 3`
(`:79`, `:425`), `_STORY_WARM_CHUNK_SIZE = 100` (`:82`), the same per-chunk
`_should_exit_early(context)` break (`:326-340`), no per-entity quota, no
interleaving, no fan-out, no second invocation.

**Structural fingerprint:** the sharing discipline is IDENTICAL (drain-in-order,
first-come, tail-starves). The ONLY thing that moved is **one entity's position
in the same unchanged queue** — offer hoisted from #5 to #0; entities 1–4 pushed
down by one slot with their relative order preserved. This is a
single-entity queue-position change, not a change to the sharing mechanism.

**The caller seam is unchanged.** `_warm_story_caches_for_completed_entities`
keeps its exact pre-CC-5 signature (`:376-383` vs origin/main): same params,
same `context=None` default. `cache_warmer.py` calls it identically. The only
behavioral change is internal to how the function orders its own work; its
contract to the rest of the fleet is preserved.

---

## §2 The blocking adjudication in full (charge decomposition)

**Q: SCOPED to offers, or a RE-ORDER of the shared fleet cascade?**
It is a re-order of the shared story-warm iteration order (offer → head). The
builder is transparent about this; it did not attempt an appended second pass,
and correctly (`BUILD §2.1:91-104`): a pass placed *after* the cascade inherits
an already-exhausted clock and breaks on its first chunk check — reproducing the
exact defect. So "scoped additive pass" and "reorder" are not two available
choices here; on a conserved budget the only implementable O-A IS a reorder.

**Q: If it reorders — inside or outside the Tier-1 fence? Test = "does it change
the warm CONTRACT for any non-offer entity."**

Entities 1–4's *treatment* changes: their budget share drops (they now warm
after offer's ~4,192-task pass consumes the front of a ~7,460-task budget). But
there is **no warm CONTRACT for entities 1–4's stories to breach.** The story
warmer is by construction best-effort — a "Strategy E" piggyback whose declared
contract is only that "story warming failures never affect the cache warmer
result" (`:393-394`, unchanged from origin/main). There is no per-entity
story-warm SLA, no completeness guarantee; entities 1–4's pre-CC-5 full-budget
position was an **emergent, incidental** consequence of cascade order, never a
declared guarantee. (The `freshness_sla_seconds` governance from substrate-v2
binds the FRAME/DataFrame cache, not the STORY cache this warmer fills.)
Changing an incidental treatment is not breaching a contract. **No contract →
no breach → not (ii) → not BLOCK.**

**Q: Is the displacement (i) unavoidable, or (ii) a smuggled redesign?**
**(i).** Proof by conservation: the budget is fixed (concurrency `:79` unchanged,
chunk `:82` unchanged, `_should_exit_early` `:326` unchanged; the builder's
budget-neutrality claim `BUILD §2.2:106-134` is confirmed by the code). It is
fully consumed every run (`SLATE §1:60-63`). Therefore warming offer's 4,192
tasks inside this invocation MUST take ~4,192 tasks of budget from someone; the
only occupant ahead of offer is entities 1–4. The SLATE's own literal O-A
("independent of whether entities 1–4 exhausted the budget", `SLATE §3:131-133`)
is arithmetically impossible on a conserved budget WITHOUT displacing 1–4. So
displacement is a property of the Tier-1 task, not of the placement choice.

**Why it is not (ii) a fleet redesign:** a redesign changes the ordering
DISCIPLINE for the fleet. This changes ONE entity's position via a parameterized
lever whose default is exactly `("offer",)` (`:68`) and whose other-11 relative
order is untouched (`:147-151`). Contrast the genuine Tier-2 moves the SLATE
names: O-F round-robin/interleave (`SLATE §3:158-161`) REPLACES drain-in-order
with a per-entity-slice discipline across all 12+ entities — that is "changing
how the 12 entity types share budget"; O-C adds a second invocation topology;
O-G raises the envelope. NONE shipped. The diff has zero `terraform/**` bytes,
holds `Semaphore(3)`, ships an offer-only default, and preserves the drain
discipline.

**What would have moved this to BLOCK** (none present): (a) raised
concurrency/budget — `:79` is pinned; (b) a multi-entity default priority set —
`:68` is `("offer",)`; (c) interleaving/round-robin/fan-out — the loop `:430-454`
still drains in order; (d) a second invocation / schedule / IAM / Terraform —
zero infra bytes. Any one is a Tier-2 breach; the build carries none.

**Why the BLOCK steelman self-defeats:** the steelman's remedy ("make the offers
pass additive/scoped, not a reorder") requires FREE budget to be additive.
There is none. Making it truly additive forces O-G (raise envelope, 429
confound), O-C (second invocation, Terraform, violates R-1's ONE-Lambda rule),
or a longer Lambda — every one HEAVIER and more Tier-2-ward than the reorder.
The reorder is the lightest-touch, most Tier-1-faithful realization of the
ruled task. BLOCK would push the builder OUT of Tier-1, not into it.

Confidence: **HIGH** — corroborated by origin/main-vs-worktree structural diff
AND the documented fence (`RULINGS R-1`, `SLATE §2`, `GATE §3`).

---

## §3 O-A vs O-D / O-F reading (does the label match what shipped?)

**Shipped = O-A (offers-only targeted, GID-keyed), with a disclosed placement
correction from "after the cascade" to "priority-first."** Not O-D, not O-F,
not O-B.

- **Not O-D (consumer-demand ordering):** priority-first uses a static,
  operator-configured entity NAME resolved to a project GID
  (`get_project_gid(entity_type)`, `:433`; default `("offer",)`, `:68`). It reads
  no demand/traffic signal — and per `SLATE §3:148-150` no such signal exists
  (the endpoint has zero traffic). O-D is structurally absent.
- **Not O-F (round-robin/interleave):** the loop drains offer FULLY before the
  next entity (`:430-454`, same break-on-timeout discipline `:326-340`). It does
  NOT give every entity a per-run slice; the tail starves exactly as before.
  O-F's defining "N tasks of each entity per cycle" is absent.
- **Not O-B (rotate start offset):** offer leads EVERY run, not 1-in-N runs.
- **Is O-A:** warms offer specifically, keyed on offer's own project GID,
  achieving O-A's stated property ("independent of whether entities 1–4
  exhausted the budget"). The sole deviation is placement (first vs. appended),
  which `SLATE §3 O-A`'s literal wording made non-implementable on a conserved
  clock — and the builder recorded the deviation openly (`BUILD §2.1:91-104`)
  rather than performing it silently.

**Operator mental-model flag (for the operator, not a breach):** the O-A the
operator priced in the SLATE reads as "*after* the cascade, a targeted second
pass" (`SLATE §3:131-132`). What shipped is "*before* the cascade, a hoist."
Functionally the "after" placement is impossible (it inherits the exhausted
clock), so the shipped form is the only faithful realization of O-A's PROPERTY —
but the operator should register that the placement flipped from after→before.
Disclosed, not smuggled. Confidence: **HIGH**.

---

## §4 Seam health (+406/−98)

**GOOD — coupling reduced, not increased; no cross-seam reach.**

- The change is confined to `story_warmer.py` (handler layer) + one new test
  file. It consumes `dataframe_cache.get_async` (`:274`),
  `client.stories.list_for_task_cached_async` (`:303-306`), the injected
  `get_project_gid` callable (`:433`), and `_should_exit_early` / `emit_metric`
  (`:51-52`) through the SAME seams as origin/main. It does NOT reach into
  `cache/integration/stories.py`, `clients/stories.py`, `cascade_utils.py`, or
  `cache_warmer.py`. No new cross-module coupling.
- The pre-CC-5 god-function is decomposed into testable pure/near-pure helpers
  (`_resolve_priority_entities` `:89`, `_build_warm_order` `:115`,
  `_new_entity_receipt` `:156`, `_emit_entity_receipt` `:186`,
  `_warm_entity_stories` `:220`). The per-entity body no longer closes over loop
  variables. This is a modifiability improvement (Clean-Architecture-ward
  decomposition), not new structure.
- New `import os` (`:45`) for the env lever follows the existing repo idiom
  (`ASANA_VERTICAL_BACKFILL_ENABLED`). `import asyncio` remains function-local
  (`:260`, `:411`), preserving the pre-existing pattern.

**Minor flag (low severity):** `__all__` grew from one symbol to six (`:56-63`),
promoting underscore-prefixed internals (`_build_warm_order`,
`_resolve_priority_entities`, `_warm_entity_stories`) onto the module's public
export surface for test reach. Test-driven publicization of internals is a mild
boundary smell; it is within-module and the only symbol the caller needs remains
`_warm_story_caches_for_completed_entities`. Confidence: **HIGH** (code-visible),
severity LOW.

---

## §5 Risk register — flags that ride the fence (non-blocking)

Leverage = impact / effort, both 1–5. All three passed the three-check gate
(intentional trade-off? bounded context? evidence sufficiency?) and are recorded
as **accepted trade-offs / watch-items**, not anti-patterns.

### FLAG-1 — Latent Tier-2 affordance now lives in the codebase (config-gated)
- **Finding:** `_resolve_priority_entities` (`:89-112`) parses an arbitrary
  comma-separated list and `_build_warm_order` (`:115-153`) handles an arbitrary
  priority tuple. The code is therefore fully capable of prioritizing MULTIPLE
  entities — i.e., executing a fleet reorder (the forbidden Tier-2). The
  Tier-1/Tier-2 boundary is now enforced by a **default value (`:68`) + one
  pinning test + an env var (`:74`)**, i.e. a CONFIGURATION boundary, not a
  STRUCTURAL one. Setting `ASANA_STORY_WARM_PRIORITY_ENTITIES="offer,contact,..."`
  would silently run a fleet reorder with no code change and no new review.
- **Why it is NOT a breach:** shipped default is offer-only and test-pinned; env
  changes are operator-reserved (charter fence + `GATE §4.7`). A dormant
  capability behind an operator-reserved lever is a standard feature-flag
  pattern. But the *boundary moved from "not built" to "built-but-defaulted-off,"*
  which the operator's risk register should hold.
- **Severity:** MEDIUM (impact 3 / likelihood low). **Leverage:** watch-item
  (no code action wanted — the fence is deliberate; the ask is operator awareness
  + keeping the env lever operator-reserved). Confidence: **HIGH**.

### FLAG-2 — Entities 1–4 displacement is material and NOT on an alarmable series
- **Finding:** offer-first roughly HALVES entities 1–4's warm coverage
  (pre-CC-5 they received ~7,460 of ~10,616; post-CC-5 ~3,268 after offer takes
  ~4,192 — figures inherited from `SLATE §1:58-63`). The per-entity receipt
  (`:199-202`) MEASURES this in the structured log, but the dimensioned
  CloudWatch series is emitted ONLY for the priority entity (offer) — the
  early-return gate at `:204-205` suppresses `emit_metric` for non-priority
  entities. So the change's own COST (entities 1–4 coverage drop) is the one
  signal NOT placed on an alarmable series; it is visible only via Logs Insights.
- **Why it is NOT a breach:** no story-warm SLA exists for entities 1–4 (§2), and
  the builder carries the trade-off openly (`BUILD §8`) with an
  `ASANA_STORY_WARM_PRIORITY_ENTITIES=""` revert. It is an accepted Tier-1 cost.
- **The genuine gap:** no named-consumer analysis exists for whether staler
  1–4 stories harm a live reader (the builder flags this himself as next-read
  (b)). This is an ATAM-style trade-off — offer-freshness vs. entities-1–4
  freshness — that is the OPERATOR's to accept, not the builder's to decide
  unilaterally. See Unknown-1.
- **Severity:** MEDIUM (impact 3 / likelihood medium under bad-budget runs).
  **Leverage:** strategic (the observability asymmetry is cheap to close later
  but out of Tier-1 scope; the consumer analysis is the higher-impact,
  higher-effort piece). Confidence on direction **HIGH**; on ~halving magnitude
  **MEDIUM** (rests on UV-P PROBE-derived populations, not re-measured).

### FLAG-3 — Bad-budget failure mode redistributed toward entities 1–4
- **Finding:** pre-CC-5, a severely truncated budget warmed the front of
  entities 1–4 and starved the rest. Post-CC-5, the same truncated budget is
  consumed by OFFER first (`:430-454`), so on a short-enough run entities 1–4 can
  receive ZERO warming while offer gets the whole slice. The cascade "fails
  differently for the fleet": offer moves from always-starved-by-position to
  never-starved; entities 1–4 move from partially-warmed to (worst case)
  zero-warmed. Symmetric observation: offer's positional SPOF is REMOVED.
- **Why it is NOT a SPOF in the availability sense:** per-entity isolation
  (`:357-370`) and the top-level broad-catch (`:482-495`) are preserved, so
  story warming still cannot cascade-fail the frame warmer. This is a
  redistribution of *starvation risk*, not a new hard failure path.
- **Severity:** LOW-MEDIUM. **Leverage:** watch-item (intrinsic to the ruled
  Tier-1 trade; measured by the receipt). Confidence: **HIGH** (pure
  control-flow consequence).

### OBSERVATION — SLATE §4 "always-emitted" is SATISFIED for offer; NARROWED for the other 11
- The load-bearing §4 requirement is that OFFER's zero be *measured, not absent*
  (`SLATE §4:184-194`). For offer (always priority) BOTH the structured log
  (`:199`) AND the dimensioned series (`:210-217`) are emitted unconditionally
  every run — fully satisfying §4 on both channels. §4's own "and/or" wording
  (`SLATE §4:185`) permits log-only for the rest, and bounding the dimensioned
  series to Tier-1 is affirmatively fence-consistent (minting a CloudWatch series
  per fleet entity would itself be a fleet-instrumentation gesture toward Tier-2
  and toward the spend fence). So this is a deliberate, §4-conformant narrowing —
  NOT a breach — but it is the mechanism BEHIND FLAG-2's observability asymmetry
  and is recorded so the operator knows entities 5–16's zeros live only in logs.
  Confidence: **HIGH** (code-visible `:199-217`).

---

## §6 Cross-domain observations (for remediation-planner / operator, not adjudicated here)

- **DF-4 / AL-5 producer-deploy interaction** is a deploy-TIMING concern, not a
  structural one, and is explicitly operator-reserved (merge/deploy word withheld,
  `RULINGS R-4:54-60`; `GATE §4.7`). The build correctly refuses any "clean
  regime" claim (`BUILD §0`, `§6`) and carries the R-9 trap verbatim. Structurally
  nothing here changes my verdict; noted so the planner routes the timing decision
  to the operator.
- **CF-3 residual** (`BUILD §4`): a `success` counts "warm call returned True,"
  which includes cache-hit-no-fetch (`cache/integration/stories.py:163-167`), so
  the receipt measures *reached-and-warm*, not *cold→warm transitions*. Carried
  as UV-P by the builder; it is an instrumentation-fidelity note, not a boundary
  finding. No cross-seam change was made to chase it (correctly out of Tier-1
  scope).

---

## §7 Unknowns (structural decisions requiring operator context)

### Unknown-1: Is entities 1–4's halved story-warm coverage acceptable?
- **Question:** Does any live consumer depend on entities 1–4
  (business / unit_holder / unit / asset_edit_holder) stories being warmed to
  their pre-CC-5 depth each run?
- **Why it matters:** the Tier-1 verdict holds because no *contract* binds
  entities 1–4's story freshness. But an emergent behavior can still have de-facto
  consumers. If one exists, the accepted trade-off (FLAG-2) needs the operator's
  explicit acceptance, not the builder's default.
- **Evidence:** `story_warmer.py:430-454` (drain-in-order, offer at head);
  `BUILD §2.2:128-134` and `§8` (displacement accepted, unmeasured for named
  consumers); `SLATE §1:58` (entities 1–4 = 10,616 tasks).
- **Suggested source:** operator / product owner of the 1–4 entity consumers;
  the per-entity receipt once deployed will supply the empirical coverage delta.

### Unknown-2: Should the latent multi-entity priority capability be structurally fenced?
- **Question:** Is a config-gated fleet-reorder capability (FLAG-1) an acceptable
  residence for the forbidden Tier-2 mechanism, or should the code hard-cap the
  priority set to a single entity until Tier-2 is separately ruled?
- **Why it matters:** the Tier-1/Tier-2 line is now an env-var default, not a
  structural bound. That is defensible (operator-reserved lever) but is a
  standing "one config away from Tier-2" surface.
- **Evidence:** `story_warmer.py:68` (default), `:89-112` (arbitrary list parse),
  `:115-153` (arbitrary priority tuple).
- **Suggested source:** operator — this is a scope-fence policy call, not an
  engineering one.

---

## §8 Handoff readiness

- Scoped-blocking axis rendered explicitly (§0, §2): **CONCUR-WITH-FLAGS**, fence
  holds, not a Tier-2 breach.
- O-A-vs-O-D/O-F reading rendered (§3): faithfully **O-A** with a disclosed
  placement correction; not O-D, not O-F, not O-B.
- Non-blocking axes covered: seam health (§4, GOOD), receipt-shape §4 conformance
  (§5 OBSERVATION, satisfied-for-offer / narrowed-for-fleet),
  SPOF/cascade-risk (§5 FLAG-3, redistributed not new-SPOF).
- Three flags with severity + leverage + confidence; two operator unknowns.
- Read-only honored: no git write verb; no target-repo mutation; no test re-run
  as evidence; every finding anchored. Self-assessment ceiling MODERATE.
