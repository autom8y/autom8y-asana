---
type: decision
artifact_class: adr
id: ADR-gfr-dynvocab-tail-scope
initiative: gfr-dynvocab
sprint: PT-02 (pre-sprint-3 design fork)
title: "Dynamic-tail interception scope — entry-owned partition for NAME-keyed resolution"
status: proposed
created: 2026-06-25
author: architect (10x-dev)
rite: 10x-dev
code_truth_anchor: "feat/gfr-engine 2092f7717ff6ba866c78df039627f4599cc32796 (worktree /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr) + UNCOMMITTED sprint-1 + sprint-2"
telos_ref: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/telos/gfr-dynvocab.md
tail_tdd_ref: .ledge/specs/gfr-dynvocab-tail-tdd.md
handoff_ref: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/handoffs/gfr-dynvocab-rnd-to-10x-handoff.md
evidence_grade: "[STRUCTURAL | MODERATE]"
escalation_flag: IN-SCOPE (no operator re-ratification required)
supersedes_decision: "tail-tdd §2 D-T1a partition criterion (owner is None) — corrected, not reversed"
---

# ADR — gfr-dynvocab dynamic-tail interception scope (PT-02 fork)

## Status

PROPOSED. Recognized-lifecycle ADR resolving the PT-02 design fork before sprint-3.
Design-only; no production code is written by this ADR. The implementing edit is
specified at file:line for the sprint-3 principal-engineer.

## The fork (what this ADR decides)

What is the correct **interception criterion** for the `is_identity=False` dynamic
tail (`dynvocab.resolve_dynamic_fields`), such that the initiative's worked example
— `asset_id` requested for an Offer entry — flows through the tail and resolves off
the Offer's own cf manifest, while the STRONG-certified identity spine stays
byte-identical and the all-or-nothing / governed-strict invariants hold?

## Context — verified by direct inspection (SVR)

The sprint-2 tail (`dynvocab.py`) and partition (`planner.py:128-138`) were built
on the premise — stated in the tail TDD §2 (`gfr-dynvocab-tail-tdd.md:136`,
`:143`) — that `asset_id` is a *"non-schema field"* for which
`_owning_entity("asset_id") is None`, and therefore routes to
`ResolutionPlan.dynamic_fields` and reaches the tail. **Direct inspection
falsifies that premise.**

Probe (`./.venv/bin/python` against the worktree at the code-truth anchor):

```
_owning_entity('asset_id')      -> 'asset_edit'      # NOT None
_owning_entity('offer_id')      -> 'offer'
_owning_entity('company_id')    -> 'business'
_owning_entity('totally_made_up') -> None            # the only thing routed to the tail today
dataframe_entities() order: ['business','unit','contact','offer','asset_edit','process_*',...,'asset_edit_holder']
```

```
plan_resolution(OFFER, ['asset_id'])
  field_plans:    [('asset_edit', parent-chain, is_identity=False, ['asset_id'])]
  dynamic_fields: []                # <-- empty: the tail NEVER runs
  identity_plans: []                # <-- empty: identity spine declines

plan_resolution(OFFER, ['company_id','asset_id'])
  field_plans:    [('business', parent-chain, True, ['company_id']),
                   ('asset_edit', parent-chain, False, ['asset_id'])]
  dynamic_fields: []                # <-- asset_id again schema-routed, dropped
```

The mechanism (each claim file-read-verified):

1. The **Offer dataframe schema does NOT declare `asset_id`** — only `offer`-owned
   columns (`offer_id`, `platforms`, `cost`, ...) — `dataframes/schemas/offer.py`
   (12 `name=` columns; no `asset_id`). The Offer *model* DOES declare it:
   `models/business/offer.py:144` `asset_id = TextField(field_name="Asset ID")`.
   This is the founding smell of the whole initiative (telos `:28-31`).
2. A **different** schema, `asset_edit`, DOES declare an `asset_id` column:
   `dataframes/schemas/asset_edit.py:106` (`name="asset_id"`, `source="cf:Asset ID"`).
3. `_owning_entity` (`planner.py:54-79`) iterates `registry.dataframe_entities()`
   and returns the **first resolvable schema** whose `get_column(field)` is
   non-None (`planner.py:69-78`). `asset_edit` is the only owner of `asset_id`, so
   it wins — `asset_id` gets a **foreign-entity schema owner**.
4. Because `owner is not None`, `plan_resolution` (`planner.py:131-138`) puts
   `asset_id` into a `FieldPlan(owner="asset_edit", is_identity=False)` and NOT into
   `dynamic_fields`.
5. **The engine resolves ONLY identity plans.** `engine.py:265` reads
   `plan.identity_plans`; nothing in `resolve_async` ever executes a non-identity
   `FieldPlan`. So a non-identity schema plan is computed and then **silently
   dropped** (this is QA finding F-2, and it is PRE-EXISTING: the old engine stub
   did the same — sprint-2 preserved it exactly).
6. Net: `resolve(offer_gid, ["asset_id"])` -> `UnresolvedError(no-identity-path)`
   (`engine.py:296`); `resolve(offer_gid, ["company_id","asset_id"])` -> returns
   only `company_id`, **silently dropping `asset_id`** (no error, because the
   `asset_edit` plan is never executed and `asset_id` never entered the tail).

Two further verified facts bound the blast radius and the manifest reachability:

- **No external production caller of GFR `resolve_async` exists** (grep over `src/`
  excluding `resolution/gfr/` finds only the unrelated `CascadeViewPlugin.resolve_async`;
  telos `code_or_artifact_landed: []`). The engine is built but not yet wired to a
  consumer. Blast radius of changing the partition on real callers is therefore
  **zero today**; the only consumers are the GFR unit tests.
- **The "Asset ID" cf is present 15/15** on real Offer task manifests via the bare
  `STANDARD_TASK_OPT_FIELDS` (PT-01 live probe; tail-TDD frontmatter `pt01_verdict`).
  The value IS reachable off `anchor.entry_task` — only the routing misses it.

### What the tail can and cannot see (load-bearing constraint)

The tail (`DynVocabResolver.__init__`, `dynvocab.py:192-211`) builds its manifest
from **`anchor.entry_task.custom_fields` ONLY** — the single hydrated entry task.
It is cache-only and issues zero new Asana calls. Therefore:

- The tail **CAN** resolve any cf that is physically present on the entry task's own
  manifest — which, for an Offer entry, includes "Asset ID" (15/15 present).
- The tail **CANNOT** resolve a field that lives only on a **parent** entity's task
  and is absent from the entry task's manifest. The tail sees the entry-task
  manifest, not the parent chain. Any criterion that routes a genuinely
  parent-owned field to the tail would make the tail raise `unknown-field` for it
  (governed-strict: absent from THIS manifest). That is correct behavior for the
  tail, but it means the tail is **not** a parent-hop resolver — it is an
  entry-task-manifest resolver. This constraint is the discriminator between the
  options below.

## Options considered

### Option A — Entry-scoped ownership (RECOMMENDED)

Change the partition criterion from *"owned by ANY resolvable schema"* to *"owned
by the ENTRY entity's OWN schema."* A requested non-identity field routes to the
dynamic tail unless the **entry entity's own schema** declares it (or it is an
identity field). Concretely, in `plan_resolution` the owner lookup becomes
entry-scoped: `asset_id` for an Offer entry has no column on the *Offer* schema, so
it routes to `dynamic_fields` and reaches the tail — regardless of the fact that
the foreign `asset_edit` schema happens to declare an `asset_id` column.

- **North-star:** SATISFIED. `asset_id` resolves off the Offer's own cf manifest
  (the tail), honoring *"resolve ANY field the entity's task carries"* and the
  realization predicate *"asset_id resolves to a SET off the REAL canary."* The cf
  is present 15/15, so the tail produces PRESENT_BUT_NULL today (populated 0/15)
  and PRESENT once sprint-3's override + opt-fields land.
- **F-2 silent-drop:** CLOSED for the entry-owned case. Fields that the entry
  schema does not own no longer land in an un-executed non-identity FieldPlan; they
  land in `dynamic_fields`, which the engine DOES execute (`engine.py:282-290`).
  (See "Residual" below for the narrow remaining case.)
- **Parent-owned fields:** A field genuinely owned by a PARENT entity and absent
  from the entry-task manifest routes to the tail and raises `unknown-field`
  (governed-strict). This is **truthful** — the GFR engine has no executor for
  non-identity parent hops today, so the honest answer is "not resolvable here,"
  not a silent drop. Option A converts a silent drop into a governed-strict
  `unknown-field`, which is strictly better and invariant-preserving.
- **Additivity / spine risk:** The identity spine is UNTOUCHED. The change is
  confined to the owner-lookup predicate in `planner.py` (NOT a frozen surface —
  the frozen resolution surfaces are `_resolve_identity_plan_async` +
  `assert_rows_tenant_identity`; the frozen query surfaces are
  `query/{engine,join,compiler}.py`). `company_id` still partitions to a Business
  identity plan with `is_identity=True`; `identity_plans` is unchanged; the
  gid-exact read and the GAP-1 guard are byte-identical. The tail stays
  `is_identity=False` and invisible to the guard.
- **Blast radius:** One existing test asserts the old behavior:
  `test_engine.py:390-401` expects `resolve(offer, ["office_phone"])` ->
  `no-identity-path`. Under Option A, `office_phone` IS on the Offer's own schema
  (`offer.py` schema declares `office_phone`), so it remains schema-routed and the
  test's verdict is **unchanged** (an own-schema non-identity field still has no
  executor and still terminates `no-identity-path`). Verified: `office_phone` is an
  Offer-schema column, so Option A does not perturb that test. No `@pytest.mark.scar`
  test asserts the partition internals (tail-TDD §9 line 461).

### Option B — Manifest-first for all non-identity fields

Any non-identity field tries the tail FIRST off the entry-task manifest; present ->
resolve; absent-from-manifest -> fall through to schema/hop or `unknown-field`. The
tail becomes the general non-identity resolver.

- **North-star:** SATISFIED for `asset_id` (and more).
- **F-2 silent-drop:** CLOSED broadly — every non-identity field gets a real
  executor (the tail) instead of an ignored FieldPlan.
- **Risk — this is the strongest objection:** Option B makes the **heuristic
  manifest typing** the primary path for fields that today have a **certified
  schema dtype** (e.g. `offer_id`, `cost`, `mrr` on the Offer schema). A
  schema-declared column carries a curated `dtype` (`Utf8`, numeric, ...) and a
  declared `source`; the tail's `_extract_raw_value` heuristic dispatch
  (`default.py:234-287`) is a *fallback* typing, not the certified one. Routing
  certified columns through the heuristic tail is a **regression of typing
  fidelity** and inverts the telos's own architecture: *"a typed certified core +
  a heuristically-typed dynamic tail"* (telos `:30`). The certified core must stay
  primary; the tail is the complement, not the front door.
- **Scope:** Option B also **exceeds** the ratified telos: it changes resolution
  semantics for every schema-owned non-identity field, not just the drifted ones.
  That is a larger behavioral surface than "make the vocabulary reflect what the
  entity actually carries."
- **Verdict:** REJECTED as default. It over-reaches the fork (which is about the
  *drifted* field `asset_id`), demotes certified typing to heuristic, and is harder
  to reason about for the all-or-nothing merge.

### Option C — Keep ownerless-only (status quo) + relocate the proof

`asset_id` stays schema-routed to the `asset_edit` plan; the proof override
attaches elsewhere (e.g. teach the engine to execute the `asset_edit` non-identity
plan via a parent hop, or attach the override to a schema-resolved value).

- **North-star:** FAILS honestly. The realization predicate requires `asset_id` to
  resolve *"off the already-hydrated entry task"* (telos `:43`) — the free-tail.
  Routing it through `asset_edit` means resolving it off a **foreign entity's
  frame**, not the Offer's own manifest. That is a different, un-probed path: the
  PT-01 live evidence (present 15/15 on the **Offer** task manifest) does not
  underwrite an `asset_edit`-frame read. It also requires the engine to grow a
  non-identity parent-hop executor — net-new query machinery the telos explicitly
  scopes OUT (the engine is a thin assembler; the tail is the additive mechanism).
- **F-2 silent-drop:** NOT closed — it would require building the missing
  non-identity executor, which is a larger change than Option A and reintroduces
  query-path complexity GFR was designed to avoid.
- **Verdict:** REJECTED. It contradicts the realization predicate's "off the entry
  task" requirement and grows the engine instead of using the certified-additive
  tail.

### Option D (hybrid) — Entry-scoped ownership + explicit own-schema non-identity terminal

Option A, plus: make the engine's handling of an **own-schema non-identity**
FieldPlan (e.g. `office_phone` on Offer) an explicit, named terminal rather than an
incidental drop. Today such a plan is computed and silently ignored, terminating at
`no-identity-path` only because `identity_plans` is empty. Under D, the engine
explicitly recognizes "this field is own-schema, non-identity, and GFR has no
non-identity schema executor in this rung" and raises a precise reason.

- This is Option A's routing (so the north-star + asset_id are satisfied
  identically) with a small clarity hardening on the **residual** F-2 surface that
  Option A leaves: an own-schema non-identity field still has no executor.
- **Decision:** Adopt Option A's partition now; record the explicit-terminal
  hardening as a **harden-on-touch** item (below), NOT a sprint-3 requirement,
  because (a) there is no caller exercising it, (b) the reason code change touches
  the closed `errors.py` vocabulary and deserves its own decision, and (c) it is
  orthogonal to the asset_id worked example. Folding it in now would widen sprint-3
  beyond the fork.

## Decision

**Adopt Option A — entry-scoped ownership.** The dynamic tail intercepts a
requested non-identity field when the **entry entity's own schema** does not
declare it. Foreign-schema ownership (e.g. `asset_edit` declaring `asset_id`) no
longer suppresses tail routing for an Offer entry.

This **corrects** the tail-TDD §2 D-T1a criterion (`owner is None`) rather than
reversing the D-T1a *decision*. D-T1a's architecture — partition at plan time,
defer the absent/unknown verdict to the manifest-aware tail, preserve the
caller-visible `unknown-field` — is RIGHT and stands. Only the **owner predicate**
that feeds the partition was built on a falsified premise (that `asset_id` is
ownerless). The fix narrows the owner test from "any resolvable schema" to "the
entry entity's own schema."

### The exact additive change (file:line)

`src/autom8_asana/resolution/gfr/planner.py` — the partition in `plan_resolution`
(`:130-138`) consults an **entry-scoped** owner test instead of the global
`_owning_entity`. Two additive shapes are admissible; the principal-engineer picks
the lower-churn one at build:

1. **Parameterize the owner lookup** — add `entry_entity_type` to the owner
   resolution so a field is "owned" only if the **entry entity's** schema (or, for
   identity, the Business schema) declares it. Pseudocode at `:131`:
   ```
   owner = _owning_entity_for_entry(field, entry_entity_type)   # NEW, entry-scoped
   #   -> entry_entity_type.value if the ENTRY schema declares `field`
   #   -> "business" if field in IDENTITY_FIELDS (unchanged identity carve-out)
   #   -> None otherwise  => routes to dynamic_fields (the tail)
   ```
   `IDENTITY_FIELDS` handling (`planner.py:39`, `:143`) is UNCHANGED — `company_id`
   still resolves to a Business identity plan with `is_identity=True`.

2. Keep `_owning_entity` as-is for the identity carve-out and add a guard: a
   non-identity field is partitioned to `dynamic_fields` unless the **entry
   entity's own** schema (`registry.get(entry_entity_type.value)` -> schema
   `get_column(field)`) declares it.

Both are additive: `ResolutionPlan.dynamic_fields` already exists (`models.py:146`);
the engine's tail branch (`engine.py:282-290`) and merge (`engine.py:298`) already
consume it. No new model field, no new engine branch, no widened error vocabulary.

### Harden-on-touch (folds in QA F-1 + Option-D residual)

These are NOTED for the sprint-3 PE as harden-on-touch, not new scope:

- **F-1 disjointness assert in `_merge_resolved`** (`engine.py:192-195`): the
  `{**id_row, **dyn_row}` union silently clobbers on key overlap. Unreachable today
  (identity owns `company_id`; the tail owns disjoint dynamic names), but a latent
  footgun. Add a cheap `assert id_row.keys().isdisjoint(dyn_row.keys())` (or an
  explicit `AmbiguousCardinalityError`-class raise) when the PE is already editing
  the merge. This makes the all-or-nothing INVARIANT I4 boundary defensive.
- **Option-D explicit terminal** for own-schema non-identity fields
  (`engine.py:294-296`): leave the current `no-identity-path` terminal as-is for
  now; if a future rung grows a non-identity schema executor, give it a precise
  reason code under its own decision.

## What this does NOT change (frozen surfaces — byte-identical)

- `_resolve_identity_plan_async` (`engine.py:94-165`) — UNCHANGED. Identity still
  routes Vector-A gid-exact through the certified Business read.
- `assert_rows_tenant_identity` / the GAP-1 guard (`guard` module) — UNCHANGED;
  still fires RED-on-bypass.
- `query/{engine,join,compiler}.py` — UNTOUCHED (the frozen query substrate).
- `IDENTITY_FIELDS` and the identity-plan partition — UNCHANGED; `company_id` is
  Business-only and still `is_identity=True`.
- The dynvocab three-state contract (`DynFieldState` PRESENT / PRESENT_BUT_NULL /
  ABSENT, `dynvocab.py:68-81`) — UNCHANGED; the tail's NAME-keyed manifest, the
  `_extract_raw_value` reuse seam, and the `_apply_override` sprint-3 hook are all
  as built. The fix is upstream of the tail (which field reaches it), not in the
  tail.
- The closed `errors.py` reason vocabulary — NOT widened. Genuine absence still
  raises `unknown-field`; a field with no executor still terminates
  `no-identity-path`.
- `is_identity=False` tail stays invisible to the identity guard.

## `asset_id` worked example — end-to-end under Option A

```
resolve(offer_gid, ["asset_id"])                      truth_tier=CACHE
  1. ENTRY  _fetch_and_anchor_async(offer_gid)         (engine.py:249)
            -> anchor.entity_type = OFFER
            -> anchor.entry_task = the hydrated Offer task
               (STANDARD_TASK_OPT_FIELDS already pulled "Asset ID" cf — present)
  2. PLAN   plan_resolution(OFFER, ["asset_id"])       (engine.py:252)
            entry-scoped owner test: Offer's OWN schema declares "asset_id"? NO
            (offer schema has no asset_id column)       -> owner = None
            -> dynamic_fields = ["asset_id"]            (was [] under the old criterion)
            -> field_plans = []   identity_plans = []
  3. GUARD  assert_plan_identity_pure(plan)             (engine.py:255) — passes (no identity plan)
  4. IDENTITY  identity_plans empty -> identity_result = None   (engine.py:267-279)
  5. TAIL   plan.dynamic_fields non-empty               (engine.py:282)
            resolve_dynamic_fields(anchor, ["asset_id"], CACHE)   (engine.py:286-290)
            -> DynVocabResolver builds NAME-keyed manifest off anchor.entry_task.custom_fields
            -> normalize("asset_id") matches cf name "Asset ID"
            -> _extract_raw_value(cf)  (default.py:234-287, REUSED)
            -> sprint-3 _apply_override turns text "a,b,c" -> {"a","b","c"} (SET)
            -> TODAY (pre-sprint-3, populated 0/15): PRESENT_BUT_NULL
               => FieldWithProvenance(value=None, status=FRESH, source=CACHE) present in the row
            dynamic_result = ResolvedFields(rows=[{"asset_id": ...}], row_count=1)
  6. MERGE  _merge_resolved(None, dynamic_result) -> dynamic_result   (engine.py:298, :184-187)
  7. return ResolvedFields with asset_id resolved off the Offer's own manifest.

resolve(offer_gid, ["company_id","asset_id"])  (the mixed case, F-2 closed):
  PLAN -> identity_plans=[business/company_id], dynamic_fields=["asset_id"]
  IDENTITY -> gid-exact Business read resolves company_id (spine UNCHANGED)
  TAIL     -> asset_id resolved off the manifest
  MERGE    -> {**company_id_row, **asset_id_row}  (disjoint; F-1 assert hardens this)
  -> BOTH fields returned. No silent drop.
```

The realization predicate is met: `asset_id` resolves off the already-hydrated
entry task (the free-tail), NAME-keyed, with the SET shape arriving in sprint-3's
override — no new Asana call, identity spine untouched.

## Risk note

- **Primary risk:** the entry-scoped owner test must treat the identity carve-out
  correctly — `company_id` is Business-owned, NOT entry-owned, yet MUST still route
  to the identity plan. Mitigation: `IDENTITY_FIELDS` is checked BEFORE the
  entry-scoped fallthrough (it already is, `planner.py:143`); the change touches
  only the *non-identity* owner branch. A PE test must assert `company_id` for an
  Offer entry still yields `is_identity=True` (existing
  `test_mixed_identity_and_dynamic_fields` covers this; extend it to assert
  asset_id now lands in `dynamic_fields`).
- **Test-surface delta:** the tail-TDD §9 worked-example tests (`:502`, `:509`) were
  written EXPECTING `asset_id` to reach the tail; against the as-built planner they
  would FAIL (asset_id was schema-routed). Option A makes those tests PASS as
  originally intended. The PE re-confirms the floor (154 passed) plus the new
  partition assertions.
- **Residual (named, accepted):** own-schema non-identity fields (e.g.
  `office_phone` on Offer) still have no executor and still terminate
  `no-identity-path`. This is unchanged from status quo and out of this fork's
  scope; tracked as the Option-D harden-on-touch item.
- **Reversibility:** two-way door. The change is a predicate swap in a non-frozen
  pure function; reverting restores the global owner test. No schema migration, no
  API contract change, no irreversible commitment.

## Telos-scope adjudication — escalation flag

**IN-SCOPE. No operator re-ratification required.**

The operator-ratified telos (`gfr-dynvocab.md`, RATIFIED 2026-06-25) states the
user-visible surface as *"resolve(gid, fields) resolves ANY field the entity's task
carries — not just the hand-curated schema columns"* (`:35-39`) and the realization
predicate as *"asset_id resolves to a SET via the whitespace-agnostic comma-split
override, off the already-hydrated entry task"* (`:43`). Option A is the criterion
that makes precisely that true and nothing more. It:

- does NOT change the verification_method, deadline, or attester;
- does NOT widen the error vocabulary or the three-state contract;
- does NOT touch the certified identity spine (telos constraint *"strictly-additive
  ... must never re-open"* the spine, `:76`);
- corrects an internal partition predicate that was built on a falsified factual
  premise (asset_id ownerless) — a build-time correction, not a scope change.

By contrast, **Option B would require re-ratification** (it changes resolution
semantics for ALL schema-owned non-identity fields, demoting certified typing to
heuristic — beyond *"reflect what the entity actually carries"*), and **Option C
fails the ratified realization predicate** (resolves off a foreign frame, not the
entry task). Both are rejected; the recommended Option A is squarely within the
ratified telos.

Evidence grade: `[STRUCTURAL | MODERATE]` — design-time ADR; the asset_id
end-to-end SET realization is attested LIVE by the rite-disjoint review-rite critic
at close (telos `verified_realized`), not by this author.
