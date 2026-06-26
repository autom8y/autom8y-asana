---
type: spec
artifact_class: tdd
initiative: gfr-dynvocab
sprint: sprint-2
title: "Dynamic tail resolver — the NAME-keyed contract S3/S4 attach to"
status: draft
created: 2026-06-25
author: architect (10x-dev)
rite: 10x-dev
code_truth_anchor: "feat/gfr-engine 2092f771 (worktree /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr) + UNCOMMITTED sprint-1 (EntryAnchor.entry_task threading + GAP-1 probe harness)"
keying_axis: NAME
evidence_grade: "[STRUCTURAL | MODERATE]"
frame_ref: .sos/wip/frames/gfr-dynvocab.md
shape_ref: .sos/wip/frames/gfr-dynvocab.shape.md
telos_ref: .know/telos/gfr-dynvocab.md
sprint1_tdd_ref: .ledge/specs/gfr-dynvocab-sprint1-tdd.md
handoff_ref: .ledge/reviews/handoffs/gfr-dynvocab-rnd-to-10x-handoff.md
pt01_verdict: "OPTION A — FREE-TAIL CONFIRMED (live probe: Asset ID present 15/15 in bare STANDARD_TASK_OPT_FIELDS; populated 0/15 = genuine present-but-null)"
addresses: ["FRAME-001 (tail)", "GAP-3", "GAP-10", "GAP-11"]
regression_floor: "118 passed (tests/unit/resolution/gfr/ + tests/integration/test_gfr_tenant_roundtrip.py) — re-confirmed GREEN this pass at 2092f771 + sprint-1"
---

# TDD-delta — gfr-dynvocab sprint-2 (Dynamic Tail Resolver — the CONTRACT)

> The core sprint. Builds the additive **`is_identity=False`, NAME-keyed dynamic
> tail** that resolves a requested field off the hydrated `entry_task` (sprint-1's
> seam), heuristically typed from each cf's `resource_subtype`, governed-strict.
> **The deliverable is a CONTRACT** — the typed boundary that sprint-3 (override
> registry / date-hole / provenance) and sprint-4 (drift gate / generality) attach
> to. NO production code is written here; this delta fixes the contract shape, the
> exact slots, the reuse seam, the three-state result model, and the RED→GREEN test
> plan the principal-engineer implements.

---

## 0. The contract S3/S4 attach to (the spine — read this first)

Everything below elaborates this. The contract is four bindings:

1. **Entry point.** A NAME-keyed dynamic field is resolved by a new
   `is_identity=False` tail path in `engine.py::resolve_async`, reached ONLY after
   the identity spine declines the field. The tail consumes `anchor.entry_task`
   (sprint-1) and the `DynVocabResolver` (new). It NEVER touches
   `_resolve_identity_plan_async`, the planner's identity plans, or the guard.

2. **The three-state result model (the contract's load-bearing surface).** Every
   tail-resolved field lands in exactly ONE of three first-class states:

   | State | Meaning | Carrier | S3/S4 dependency |
   |-------|---------|---------|------------------|
   | **PRESENT** | cf exists on the task AND carries a non-null typed value | `FieldWithProvenance(value=<typed>, status, source, as_of)` | S3 override rewrites `value`; S3 provenance stamps `typing_origin` |
   | **PRESENT_BUT_NULL** | cf exists on the task but its typed value slot is null/empty | `FieldWithProvenance(value=None, status, source, as_of)` + a present-but-null discriminator | S3 date-hole closes a subset of these (date cfs null today because `date_value` absent from opt-fields); S4 drift gate must NOT count these as drift |
   | **ABSENT_UNKNOWN** | cf is genuinely not on the task's manifest | `UnresolvedError(reason="unknown-field")` (all-or-nothing) | S4 generality proves this is truthful across ≥2 EntityTypes |

   **PRESENT_BUT_NULL is distinct from ABSENT_UNKNOWN and from a silent `None`.**
   This is the realization-predicate's *"UNKNOWN distinguishable from
   present-but-null"* — and it is exactly what the live PT-01 probe surfaced
   (Asset ID present 15/15, populated 0/15). The contract makes the
   present-vs-populated split first-class; sprint-3 FRAME-004 attaches the full
   provenance tag, but the SHAPE (a present-but-null result is NOT an error) is
   fixed here.

3. **The NAME-keying grain.** A field is matched against the task's cf manifest by
   `NameNormalizer.normalize(<requested>) == NameNormalizer.normalize(cf.name)`.
   cf `gid` is a runtime intra-task value handle only — used to locate the value
   slot AFTER the name match, never to key the request or the override registry.

4. **The typing seam.** Once a cf is name-matched, its typed value is extracted by
   `DefaultCustomFieldResolver._extract_raw_value(cf_dict)` (`default.py:234-287`)
   — REUSED, not reimplemented. `_extract_raw_value` already dispatches on
   `resource_subtype` (text/number/enum/multi_enum/date/people + `_` fallthrough).
   The tail's "heuristic typing table" IS that match block; sprint-2 wires a seam
   that calls into it.

S3 attaches at the `value`/`typing_origin` of state PRESENT (override rewrite +
provenance). S4 attaches at the manifest boundary (drift gate compares the model's
declared `field_name` set against the schema; generality re-runs the SAME tail
across EntityTypes). Neither S3 nor S4 may widen the three-state enum or move the
NAME-key off `normalize(cf.name)`.

---

## 1. Context & Constraints (binding — not re-litigated)

Inherit the frame/shape/handoff/telos/sprint-1-TDD. Load-bearing gates:

- **Strictly-additive.** ZERO edits to `query/{engine,join,compiler}.py`, the
  `@pytest.mark.scar` tests, `_resolve_identity_plan_async`, or
  `guard.py::assert_rows_tenant_identity`. The tail is a NEW branch + a NEW module;
  it adds to `resolve_async` without altering the identity path.
- **NAME-keyed, never gid-keyed.** `NameNormalizer.normalize(cf.name)` is the grain
  (`default.py:81,92`; `field_resolver.py:61` precedent). cf `gid` locates the value
  slot post-match only.
- **Cache-only.** ZERO new Asana call. The tail reads `anchor.entry_task`, an object
  `hydrate_from_gid_async` ALREADY produced and sprint-1 threaded. No fetch.
- **ADR-S4-001 holds.** No schema codegen. The tail does NOT generate or mutate any
  `SchemaRegistry` schema; it resolves OUTSIDE the schema, off the live manifest.
- **Certified suite GREEN at exit** — `./.venv/bin/python -m pytest`, NEVER
  `uv run` (CodeArtifact 401). Floor: 118 passed.

### 1.1 SVR receipts (direct inspection this pass, worktree `2092f771` + sprint-1)

| Claim | Method | Anchor | Verbatim marker |
|-------|--------|--------|-----------------|
| Engine no-identity stub is the additive slot | file-read | `src/autom8_asana/resolution/gfr/engine.py:230-235` | `if not identity_plans:` … `raise UnresolvedError(fields=field_list, reason="no-identity-path")` |
| **The planner raises `unknown-field` for a non-schema field BEFORE the engine reaches the stub** | file-read | `src/autom8_asana/resolution/gfr/planner.py:127-129` | `if unknown:` … `raise UnresolvedError(fields=unknown, reason="unknown-field")` |
| `_owning_entity` returns None for a field on no resolvable schema | file-read | `src/autom8_asana/resolution/gfr/planner.py:78-80` | `if schema.get_column(field) is not None:` … `return None` |
| `asset_id` is on the Offer task MODEL | file-read | `src/autom8_asana/models/business/offer.py:144` | `asset_id = TextField(field_name="Asset ID")` |
| `asset_id` is ABSENT from the Offer dataframe SCHEMA (the smell) | bash-probe | `grep -c "asset_id\|Asset ID" src/autom8_asana/dataframes/schemas/offer.py` | `0` (exit 1) |
| `_extract_raw_value` dispatches on `resource_subtype` (the typing table — REUSE) | file-read | `src/autom8_asana/dataframes/resolver/default.py:250-287` | `match resource_subtype:` … `case "text":` … `case _:` `return get_attr("display_value")` |
| `resource_subtype` IS in the bare opt-fields (typing ground truth fetched) | file-read | `src/autom8_asana/models/business/fields.py:249` | `"custom_fields.resource_subtype",` |
| `date_value` is ABSENT from opt-fields (S3 FRAME-003 hole; tail must treat as present-but-null) | file-read | `src/autom8_asana/models/business/fields.py:240-250` | (no `custom_fields.date_value` member) |
| cf manifest lives on `Task.custom_fields: list[dict]` | file-read | `src/autom8_asana/models/task.py:146` | `custom_fields: list[dict[str, Any]] \| None = Field(` |
| `EntryAnchor.entry_task` threaded (sprint-1), cf-carrier in both topologies | file-read | `src/autom8_asana/resolution/gfr/entry.py:73,127` | `entry_task: BusinessEntity \| None = None` ; `entry_task = result.entry_entity if result.entry_entity is not None else result.business` |
| resolver-class-path hook + consumer | file-read | `src/autom8_asana/services/universal_strategy.py:1328-1333` | `if descriptor and descriptor.custom_field_resolver_class_path:` … `return getattr(module, class_name)()` |
| `UnresolvedError.reason` is a CLOSED vocabulary (tail must fit within it) | file-read | `src/autom8_asana/resolution/gfr/errors.py:30-38` | `UNRESOLVED_REASONS: Final[frozenset[str]] = frozenset(` … `"unknown-field",` |
| `FieldWithProvenance` is `extra="forbid"` (S3 provenance must add additively) | file-read | `src/autom8_asana/resolution/gfr/models.py:73` | `model_config = ConfigDict(extra="forbid")` |
| `ResolvedFields` is the return type the tail must also produce | file-read | `src/autom8_asana/resolution/gfr/models.py:84-98` | `rows: list[dict[str, FieldWithProvenance]]` |
| Regression floor GREEN | bash-probe | `./.venv/bin/python -m pytest tests/unit/resolution/gfr/ tests/integration/test_gfr_tenant_roundtrip.py -q` | `118 passed in 0.39s` (exit 0) |

---

## 2. THE SURPRISE — the planner, not the engine stub, is the real interception point

The shape and the rnd handoff both frame sprint-2 as *"replace the engine.py:230-235
no-identity-path stub additively."* Direct inspection shows that framing is
**incomplete in a load-bearing way**, and the contract must account for it.

**The flow today (`engine.py::resolve_async`):**

```
resolve_async(gid, fields)
  1. anchor = _fetch_and_anchor_async(...)        # entry; threads entry_task (sprint-1)
  2. plan = plan_resolution(anchor.entity_type, fields)   # planner.py
        └─ _owning_entity(field) is None for a non-schema field (e.g. "asset_id")
        └─ raises UnresolvedError(reason="unknown-field")  ← FIRES HERE, planner.py:127-129
  3. guard.assert_plan_identity_pure(plan)
  4. if not plan.identity_plans:
        raise UnresolvedError(reason="no-identity-path")   ← the shape's named stub, engine.py:230-235
```

A request for a dynamic (non-schema) field like `asset_id` **never reaches the
no-identity-path stub** — it dies one step earlier at the planner's `unknown-field`
raise (`planner.py:127-129`). The stub at 230-235 is only reachable by a field that
IS on a schema but is non-identity (a different, narrower case).

**Contract consequence (DECISION D-T1 — the spine decision).** The tail must
intercept the planner's `unknown-field` verdict, not (only) the engine's
no-identity-path stub. The additive shape:

- **D-T1a (RECOMMENDED — the contract's default): plan-time partition into
  `dynamic_plans`.** `plan_resolution` is extended additively: instead of raising
  `unknown-field` immediately, fields with no resolvable schema owner are collected
  into a new `ResolutionPlan.dynamic_fields: list[str]` (additive field, default
  `[]`, `extra="forbid"`-safe). The planner raises `unknown-field` ONLY if a field
  is neither schema-owned NOR a candidate for the dynamic tail — but since the tail
  decides genuine-absence at resolution time (it needs the manifest), the planner
  CANNOT pre-judge absence. Therefore: **the planner stops raising on no-schema-owner
  and instead routes the field to `dynamic_fields`; the tail makes the
  governed-strict absent/unknown call against the real manifest.** The engine then,
  after the identity plans, resolves `dynamic_fields` via the tail and merges.

  > **Frozen-surface note.** `planner.py` is NOT in the frozen set (the frozen query
  > surfaces are `query/{engine,join,compiler}.py`; the frozen resolution surfaces
  > are `_resolve_identity_plan_async` + `assert_rows_tenant_identity`). Extending
  > `plan_resolution` to PARTITION rather than RAISE is additive and leaves the
  > identity-plan path byte-identical. BUT it changes a behavior that existing tests
  > assert (a non-schema field today raises `unknown-field` at plan time). The PE
  > MUST audit `test_planner*`/`test_engine*` for tests asserting the old
  > raise-at-plan behavior and confirm none are `@pytest.mark.scar`. If a non-scar
  > test asserts the old behavior, it is updated additively (the field now resolves
  > or raises `unknown-field` at the TAIL with the same reason code — the caller-
  > visible `UnresolvedError(reason="unknown-field")` for a genuinely-absent field
  > is PRESERVED; only the interception point moves).

- **D-T1b (alternative — REJECTED as the default, documented for completeness):
  resolve dynamic fields entirely after the stub, leaving the planner raising.**
  This keeps `planner.py` untouched but means a dynamic-only request raises
  `unknown-field` at the planner and the tail never runs — the tail would have to be
  invoked from a `try/except UnresolvedError` wrapper around `plan_resolution`, which
  is structurally uglier (control flow by exception) and makes the mixed case
  (`resolve(gid, ["company_id", "asset_id"])`) impossible to satisfy in one call.
  REJECTED: it cannot serve a mixed identity+dynamic field set, which the contract
  must support.

**The contract picks D-T1a.** The caller-visible failure for a genuinely-absent
field stays `UnresolvedError(reason="unknown-field")` — the closed vocabulary
(`errors.py:30-38`) is NOT widened. Only the point at which that verdict is REACHED
moves from plan-time (premature, manifest-blind) to tail-time (manifest-aware,
governed-strict). This is the realization-predicate's governed-strict requirement:
*absence is judged against the manifest, not guessed from schema-absence.*

---

## 3. Module layout & where the tail slots (exact file:line)

### 3.1 New module — `resolution/gfr/dynvocab.py`

A new sibling to `engine.py`/`posture.py`/`planner.py`, holding the
`is_identity=False` tail. Keeping it OUT of `engine.py` keeps the engine thin
(its stated design, `engine.py:1-28`) and keeps the tail provably separable from the
identity spine for the sprint-5 disjoint critic.

| Symbol | Role |
|--------|------|
| `class DynVocabResolver` | The tail resolver. Builds the NAME-keyed manifest off `entry_task.custom_fields`; resolves a requested field to a three-state result; reuses `_extract_raw_value`. |
| `def resolve_dynamic_fields(...) -> ResolvedFields \| None` | Tail entry the engine calls with `(anchor, dynamic_fields, source, as_of, ...)`. Returns a `ResolvedFields` for the dynamic subset, or raises `UnresolvedError(reason="unknown-field")` on genuine absence (governed-strict, all-or-nothing within the dynamic subset). |
| `def _build_manifest(custom_fields) -> dict[str, dict]` | NAME-keyed index: `normalize(cf["name"]) -> cf_dict`. First-match-wins (mirrors `default.py:84-90`). The manifest is the governed-strict absence oracle. |
| `class DynFieldState(StrEnum)` | `PRESENT \| PRESENT_BUT_NULL \| ABSENT`. The three-state discriminator (see §4). |

### 3.2 The engine slot (additive branch in `resolve_async`)

The tail is invoked from `engine.py::resolve_async` AFTER the identity plans are
resolved (or after the identity-plan block is skipped). The current stub block:

```
# engine.py:230-235 (CURRENT)
identity_plans = plan.identity_plans
if not identity_plans:
    raise UnresolvedError(fields=field_list, reason="no-identity-path")
```

becomes (CONCEPTUAL — PE implements; additive, no edit to
`_resolve_identity_plan_async`):

```
identity_plans = plan.identity_plans
identity_result = None
if identity_plans:
    identity_result = await _resolve_identity_plan_async(...)   # UNCHANGED path

dynamic_result = None
if plan.dynamic_fields:                                          # NEW (D-T1a)
    dynamic_result = resolve_dynamic_fields(
        anchor=anchor,
        fields=plan.dynamic_fields,
        source=TruthTier.CACHE,        # cache-only; the entry read is the only I/O
        as_of=<frame watermark or None>,
    )

# merge: a field set with neither an identity plan nor a dynamic field nor a
# resolvable schema enrichment is genuinely empty -> the SAME terminal verdict.
if identity_result is None and dynamic_result is None:
    raise UnresolvedError(fields=field_list, reason="no-identity-path")

result = _merge_resolved(identity_result, dynamic_result)        # NEW helper
```

| What | File:line (worktree `2092f771` + sprint-1) |
|------|----------------------------------------------|
| New tail module | `src/autom8_asana/resolution/gfr/dynvocab.py` (new file) |
| Planner partition (D-T1a) | `src/autom8_asana/resolution/gfr/planner.py:118-129` (collect `dynamic_fields` instead of raising) |
| `ResolutionPlan.dynamic_fields` additive field | `src/autom8_asana/resolution/gfr/models.py:144-145` (add to `ResolutionPlan`) |
| Engine tail branch + merge | `src/autom8_asana/resolution/gfr/engine.py:229-235` (additive branch replacing the bare stub) |
| `_extract_raw_value` reuse | called FROM `dynvocab.py` into `src/autom8_asana/dataframes/resolver/default.py:234-287` |
| entity_registry wiring | `src/autom8_asana/core/entity_registry.py:136` (`custom_field_resolver_class_path`) — see §6 |

The merge helper `_merge_resolved(identity, dynamic)` zips per-row field maps; both
are `ResolvedFields` keyed by field name, so the merge is a per-row dict union.
Because identity is gid-exact single-row and the dynamic tail is single-task (the
entry task is one entity), `row_count` is 1 in the driving case; the merge asserts
row-count agreement and is row-set-native-safe (INVARIANT I5 preserved).

---

## 4. The governed-strict three-state result model (the contract's heart)

### 4.1 `DynFieldState` — the discriminator

```python
# dynvocab.py (CONCEPTUAL)
class DynFieldState(StrEnum):
    PRESENT = "present"                    # cf on manifest, typed value non-null
    PRESENT_BUT_NULL = "present-but-null"  # cf on manifest, typed value null/empty
    ABSENT = "absent"                      # cf not on manifest -> unknown-field
```

Resolution of one requested field `f` against the NAME-keyed manifest:

```
norm = NameNormalizer.normalize(f)
if norm not in manifest:            -> DynFieldState.ABSENT
else:
    cf = manifest[norm]
    raw = DefaultCustomFieldResolver()._extract_raw_value(cf)   # REUSE (§5)
    if _is_null(raw):               -> DynFieldState.PRESENT_BUT_NULL  (value=None)
    else:                           -> DynFieldState.PRESENT           (value=raw)
```

`_is_null(raw)` mirrors the probe's `_is_populated` inverse
(`scripts/gfr_dynvocab/gap1_probe.py:86-110`): `None`, empty string, and empty list
count as null. (The probe already encodes this present-vs-populated split — the tail
formalizes the SAME predicate. Aligning the two is deliberate: the live PT-01
verdict and the production tail judge "populated" identically.)

### 4.2 How the three states map onto the EXISTING return types

The contract does NOT introduce a parallel result type. It maps onto
`FieldWithProvenance` + `UnresolvedError`, so callers and S3/S4 see one shape:

- **PRESENT** → `FieldWithProvenance(value=<typed>, status=FRESH, source=CACHE, as_of=...)`.
- **PRESENT_BUT_NULL** → `FieldWithProvenance(value=None, ...)` PLUS a present-but-null
  discriminator the caller can read. **Discriminator decision (D-T2):** sprint-2 does
  NOT add a field to the `extra="forbid"` `FieldWithProvenance` (that is sprint-3
  FRAME-004's `typing_origin` — adding it here would pre-empt S3 and risk a
  double-add). Instead, sprint-2 distinguishes present-but-null from a hypothetical
  silent-None **structurally**: a PRESENT_BUT_NULL field IS in the result rows with
  `value=None`; an ABSENT field is NOT in the result at all — it has already raised
  `UnresolvedError(reason="unknown-field")`. The contract guarantee:
  > **If a field name appears as a key in a returned `ResolvedFields` row, the cf
  > EXISTS on the task (PRESENT or PRESENT_BUT_NULL). If it is genuinely absent, the
  > whole call raised `unknown-field` and there is no row. A `value=None` in a
  > returned row therefore ALWAYS means present-but-null, NEVER absent.**

  This is the three-state contract expressed in the existing types with ZERO schema
  churn. Sprint-3 FRAME-004 then ENRICHES the PRESENT_BUT_NULL row with
  `typing_origin` (additive to `FieldWithProvenance`); the structural guarantee above
  is what S3 builds on, and it holds before S3 lands.

- **ABSENT** → contributes to `UnresolvedError(fields=[...absent...],
  reason="unknown-field")`. Governed-strict + all-or-nothing within the dynamic
  subset: if ANY requested dynamic field is genuinely absent, the whole call raises
  (consistent with INVARIANT I4 and the planner's prior `unknown-field` semantics).

### 4.3 Why PRESENT_BUT_NULL must be first-class (the S3/S4 dependency)

- **S3 FRAME-003 (date hole):** a `date` cf resolves to `None` TODAY because
  `date_value` is absent from opt-fields (`fields.py` SVR: 0 matches). Under this
  contract that date cf is **PRESENT_BUT_NULL**, NOT absent — it is on the manifest
  (its `resource_subtype` is present), its value slot is just unfetched. S3 adds
  `date_value` to opt-fields and the SAME cf flips PRESENT_BUT_NULL → PRESENT with no
  contract change. If the contract collapsed present-but-null into absent/unknown,
  S3 could not tell "we didn't fetch the value" from "the field doesn't exist."
- **S4 FRAME-005 (drift gate):** the gate compares the model's declared `field_name`
  set against schema coverage. A PRESENT_BUT_NULL field is NOT drift (the model field
  exists and the cf exists; the value is merely null on this instance). The gate must
  read the manifest's present-set, which the three-state model exposes.

---

## 5. The `_extract_raw_value` reuse seam (typing from `resource_subtype`)

### 5.1 The seam (do NOT reimplement)

`DefaultCustomFieldResolver._extract_raw_value(cf_data)` (`default.py:234-287`) is
the typing table. It takes a single cf dict and dispatches on `resource_subtype`:

| `resource_subtype` | extracted value | tail-typed result |
|--------------------|-----------------|-------------------|
| `text` | `text_value` (str) | `str` |
| `number` | `number_value` | `float`/`int` |
| `enum` | `enum_value.name` | `str` (label) |
| `multi_enum` | `[opt.name for opt in multi_enum_values]` | `list[str]` |
| `date` | `date_value.date` | `str` (date) — **null today (S3 FRAME-003)** |
| `people` | `[p.gid for p in people_value]` | `list[str]` |
| `_` (fallthrough) | `display_value` | `str` — **S3 FRAME-003 adds a fallthrough counter + `typing_origin:'fallback'`** |

This table IS the "heuristic typing from cf-type metadata" the frame calls for. The
tail does NOT author its own table; it calls `_extract_raw_value`.

### 5.2 How the tail calls in (D-T3)

`_extract_raw_value` is an INSTANCE method on `DefaultCustomFieldResolver`, but it
reads nothing from `self` (it operates purely on the passed `cf_data` dict —
verified: `default.py:234-287` references only `cf_data` via the local `get_attr`).
The tail therefore instantiates one `DefaultCustomFieldResolver()` (cheap, no
`build_index` needed for raw extraction) and calls `._extract_raw_value(cf)` per
matched cf. Deferred import inside the method (the strategies.py pattern, per the
architect-memory convention) avoids a module-level cycle:

```python
# dynvocab.py (CONCEPTUAL)
def _typed_value(cf: dict) -> object:
    from autom8_asana.dataframes.resolver.default import DefaultCustomFieldResolver
    return DefaultCustomFieldResolver()._extract_raw_value(cf)
```

> **UV-P (typing-seam coupling):** `_extract_raw_value` is a private method
> (leading underscore). Reusing it cross-module couples the tail to a private API.
> [UV-P: whether to promote `_extract_raw_value` to a module-level pure function
> `extract_raw_value(cf_dict)` for clean cross-module reuse | METHOD:
> deferred-to-build | REASON: a one-line additive refactor (extract the method body
> to a module function, have the method delegate) is cleaner but touches
> `default.py` which is shared dataframe code; PE decides at build whether the
> private-method call or the additive promotion is lower-risk. Either satisfies the
> "do not reimplement" constraint. The CONTRACT (reuse the existing dispatch) holds
> under both.]

The override hook for sprint-3 FRAME-002 (asset_id text → comma-split set) attaches
HERE: an EntityType-scoped, NAME-keyed override registry runs AFTER `_extract_raw_value`
to post-process the raw value (text "a,b,c" → `{"a","b","c"}`). Sprint-2 leaves a
seam (`_apply_override(field_name, entity_type, raw) -> value`, default identity) so
S3 fills it without re-opening the tail.

---

## 6. entity_registry wiring (`entity_registry.py:136`)

The descriptor field `custom_field_resolver_class_path` (`entity_registry.py:189`,
documented at `:136`) is consumed by `universal_strategy.py:1328-1333`
(`_get_custom_field_resolver` — dynamic import + instantiate). Every offer-domain
descriptor already points at `DefaultCustomFieldResolver` (`entity_registry.py:461`
etc.).

**Wiring decision (D-T4).** The tail does NOT need a NEW resolver class on the
descriptor in sprint-2 — it reuses `DefaultCustomFieldResolver._extract_raw_value`
directly (§5). The `custom_field_resolver_class_path` hook is the **generality seam
for sprint-4 FRAME-006**: it is how a per-EntityType resolver (with EntityType-scoped
overrides) is selected without entity-special-casing in the engine. Sprint-2's
contract obligation is narrow and precise:

- The tail resolves `anchor.entity_type` → descriptor →
  `descriptor.custom_field_resolver_class_path`, and uses THAT class's
  `_extract_raw_value`/override behavior (defaulting to `DefaultCustomFieldResolver`
  when the path is the default). This keeps the typing/override policy
  **descriptor-driven**, so sprint-4 generality is "register an `EntityConfig` +
  set the resolver-class-path" — NOT an engine edit. The honest claim (FRAME-006):
  a new EntityType needs a descriptor entry, which IS code, NOT "zero code change."
- Sprint-2 does NOT add or change any descriptor's `custom_field_resolver_class_path`
  value. It only READS the hook. (Adding an EntityType-scoped override resolver is
  sprint-3/4.)

> **UV-P (resolver instantiation path):** `_get_custom_field_resolver` lives on
> `UniversalResolutionStrategy` (`universal_strategy.py:1315`), not on a standalone
> function. [UV-P: whether the tail reuses `_get_custom_field_resolver` or
> replicates the 3-line descriptor→import→instantiate in `dynvocab.py` | METHOD:
> deferred-to-build | REASON: importing `UniversalResolutionStrategy` into the GFR
> tail may pull a heavy dependency graph; PE confirms at build whether to call the
> existing method or inline the descriptor-driven instantiation. The CONTRACT
> (descriptor-driven resolver selection via the `:136` hook) holds either way.]

---

## 7. Structured logging + metric shape (GAP-10) at the entry seam

The frame (GAP-10) requires structured logging on resolution + a manifest-build /
`len(custom_fields)` metric at the entry seam. The tail emits:

| Signal | Shape | Where |
|--------|-------|-------|
| manifest-build | `logger.debug("GFR tail: manifest built", extra={"gid", "entity_type", "custom_fields_count": len(custom_fields), "manifest_size": len(manifest), "build_us": <elapsed µs>})` | `dynvocab.py::_build_manifest` |
| per-field resolution | `logger.debug("GFR tail: field resolved", extra={"gid", "field", "state": DynFieldState, "cf_subtype": cf.get("resource_subtype")})` | per requested field |
| governed-strict absence | `logger.info("GFR tail: unknown field (governed-strict)", extra={"gid", "absent_fields", "manifest_size"})` before raising `unknown-field` | on ABSENT |
| present-but-null | `logger.debug("GFR tail: present-but-null", extra={"gid", "field", "cf_subtype"})` | on PRESENT_BUT_NULL (feeds S3 date-hole observability) |

`manifest_size` and `custom_fields_count` are the metric the frame asks for; they
also feed the DEFER-2 name-collision trigger (S1a: payload > ~500 cf) and DEFER-3
(S1c: payload dominates latency) — surfaced, not built. Logger is the existing
`autom8y_log.get_logger(__name__)` (the package convention).

---

## 8. Frozen-surface attestation (proof: design touches ZERO G-FROZEN surface)

| Frozen surface | Sprint-2 design touches it? | Proof |
|----------------|------------------------------|-------|
| `query/engine.py` | NO | Tail is new `dynvocab.py` + additive `gfr/engine.py` branch. No `query/*` edit. |
| `query/join.py` | NO | Same. The tail never builds a `RowsRequest` or a join — it reads the in-hand task. |
| `query/compiler.py` | NO | Same. |
| `@pytest.mark.scar` tests | NO | New tests additive (§9). PE confirms `grep -rl "pytest.mark.scar" tests/` — none in the edit set. The planner-partition (D-T1a) audit (§2) checks no scar test asserts the old plan-time raise. |
| `_resolve_identity_plan_async` | NO | UNCHANGED. The new engine branch calls it identically when identity plans exist; the dynamic branch is parallel and never enters it. |
| `guard.py::assert_rows_tenant_identity` | NO | UNTOUCHED. **Invisibility proof §8.1.** |
| `assert_plan_identity_pure` | NO | Still runs on the plan; `dynamic_fields` carry NO `is_identity` marker (they are not `FieldPlan`s, they are bare field names) so the guard's identity-purity check sees the same identity plan set as before. |
| ADR-S4-001 (no schema codegen) | NO | The tail resolves OUTSIDE the schema off the live manifest; it generates/mutates no schema. |

### 8.1 Invisibility proof — the tail is invisible to `assert_rows_tenant_identity`

`assert_rows_tenant_identity(rows, business_gid)` (`guard.py`) reads only
`row.get("gid")` from **query-result rows** and is called ONLY inside
`_resolve_identity_plan_async` (`engine.py:138`). The dynamic tail:

1. produces its `ResolvedFields` from `anchor.entry_task.custom_fields` (an in-hand
   task), never from `execute_rows`, so its rows never pass through the guard;
2. carries `is_identity=False` by construction — `dynamic_fields` are not
   `FieldPlan` elements and create no identity plan;
3. runs in a branch parallel to (never inside) `_resolve_identity_plan_async`.

The mechanical proof is the regression floor: the 118 certified tests (which
exercise the guard and the identity path) stay GREEN with the tail added.

### 8.2 Cache-only attestation

Sprint-2 adds NO Asana call. The tail reads `anchor.entry_task` — threaded by
sprint-1 from the single accounted entry fetch. `_build_manifest`, `_extract_raw_value`,
and override post-processing are pure in-memory operations on the in-hand cf list.
PT-01 confirmed the cfs (including Asset ID) are already in the bare opt-fields
fetch (present 15/15), so the free-tail premise holds: zero new I/O.

---

## 9. Test-delta — the RED→GREEN contract for principal-engineer

> The dominant gate is **the 118 certified tests stay GREEN** (additive must not
> regress). New tests below cover the tail. Grain follows
> `tests/unit/resolution/gfr/test_entry.py` + `conftest.py`.

### 9.1 Three-state contract tests (`tests/unit/resolution/gfr/test_dynvocab.py` — new)

| Test | RED (before impl) | GREEN (after impl) |
|------|-------------------|---------------------|
| `test_present_field_resolves_typed` | import/attr error — no tail | `resolve(offer_gid, ["asset_id"])` on a manifest with `{"name":"Asset ID","resource_subtype":"text","text_value":"a"}` → `FieldWithProvenance(value="a")` |
| `test_present_but_null_is_distinct_from_absent` | n/a | a cf present with null value slot → row with `value=None` (PRESENT_BUT_NULL); a genuinely-absent field → `UnresolvedError(reason="unknown-field")`. The two are NOT conflated. |
| `test_present_but_null_field_appears_in_rows` | n/a | the present-but-null field's NAME is a key in the returned row (the §4.2 structural guarantee: `value=None` in a row ⇒ present-but-null, never absent) |
| `test_absent_field_raises_unknown_field` | n/a | a field not on the manifest → `UnresolvedError(reason="unknown-field")`, `fields=[<absent>]` (governed-strict; closed vocab unchanged) |
| `test_name_keying_normalizes` | n/a | `resolve(gid, ["asset_id"])` matches cf name `"Asset ID"` via `NameNormalizer.normalize` (NAME-keyed; not gid-keyed) |
| `test_each_cf_type_extracts_via_reuse` | n/a | text/number/enum/multi_enum/people each resolve through `_extract_raw_value` to the §5.1 typed result (date is present-but-null pre-S3 — asserted as such) |
| `test_date_cf_is_present_but_null_pre_s3` | n/a | a `date` cf (no `date_value` fetched) resolves PRESENT_BUT_NULL, NOT absent (locks the S3 FRAME-003 contract dependency) |
| `test_mixed_identity_and_dynamic_fields` | n/a | `resolve(gid, ["company_id","asset_id"])` resolves both — identity via the gid-exact path, asset_id via the tail — and merges (D-T1a's mixed-case requirement) |

### 9.2 Planner partition tests (`tests/unit/resolution/gfr/test_planner.py` — additive)

| Test | Asserts |
|------|---------|
| `test_non_schema_field_routed_to_dynamic` | a field on no resolvable schema goes to `ResolutionPlan.dynamic_fields`, NOT an immediate `unknown-field` raise (D-T1a) |
| `test_schema_field_still_planned_normally` | a schema field still produces its `FieldPlan` (identity path untouched) |
| `test_existing_unknown_field_behavior_preserved_at_caller` | a genuinely-absent field STILL surfaces `UnresolvedError(reason="unknown-field")` to the caller (interception point moved, caller contract preserved) |
| **planner-scar audit** | PE confirms no `@pytest.mark.scar` test asserts the old plan-time raise; any non-scar test asserting it is updated additively (§2) |

### 9.3 Invisibility / cache-only tests (additive)

| Test | Asserts |
|------|---------|
| `test_tail_invisible_to_identity_guard` | resolving dynamic fields never calls `assert_rows_tenant_identity` and never builds a `RowsRequest` (the tail rows never enter the guard) |
| `test_tail_makes_no_asana_call` | the tail resolves off `anchor.entry_task` with zero `client.*` calls (cache-only; baseline the client call count, assert post-entry delta zero — mirrors the PT-03 RED proof pattern, `engine.py:26-27`) |

### 9.4 Fixture delta (`conftest.py`)

Extend `make_entry_task`/`make_hydration_result` (sprint-1) to supply a hydrated
entry task with a populated `custom_fields` manifest (Asset ID text, an enum, a
multi_enum, a present-but-null date, an absent control). Additive params, defaults
preserve all existing callers.

### 9.5 Mechanical regression gate (every sprint)

```bash
cd /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr
./.venv/bin/python -m pytest tests/unit/resolution/gfr/ tests/integration/test_gfr_tenant_roundtrip.py
# MUST stay GREEN (floor 118 passed at 2092f771 + sprint-1; new additive tests raise the count).
# NEVER uv run (CodeArtifact 401).
```

---

## 10. Handoff checklist for principal-engineer

Implementation is GREEN-ready when ALL hold:

- [ ] **`dynvocab.py` built** — `DynVocabResolver`, `resolve_dynamic_fields`,
      `_build_manifest` (NAME-keyed, first-match-wins), `DynFieldState`
      (PRESENT/PRESENT_BUT_NULL/ABSENT).
- [ ] **Planner partitions (D-T1a)** — `plan_resolution` routes no-schema fields to
      `ResolutionPlan.dynamic_fields` (additive field, default `[]`) instead of
      raising `unknown-field` at plan time. Planner-scar audit clean (§2).
- [ ] **Engine tail branch (additive)** — `resolve_async` resolves `dynamic_fields`
      via the tail after the identity block; merges; preserves the
      no-identity/no-dynamic terminal `UnresolvedError`. `_resolve_identity_plan_async`
      UNTOUCHED.
- [ ] **Three-state result model honored** — PRESENT → `FieldWithProvenance(value=…)`;
      PRESENT_BUT_NULL → row with `value=None` (structural §4.2 guarantee); ABSENT →
      `UnresolvedError(reason="unknown-field")`. Closed reason vocab NOT widened.
- [ ] **`_extract_raw_value` REUSED** (not reimplemented) — per §5; UV-P
      (private-method call vs additive promotion) resolved at build.
- [ ] **NAME-keyed throughout** — `NameNormalizer.normalize`; cf `gid` only locates
      the value slot post-match.
- [ ] **Override seam left for S3** — `_apply_override(field_name, entity_type, raw)`
      default-identity hook present (FRAME-002 fills it).
- [ ] **Descriptor-driven resolver selection** — tail reads
      `custom_field_resolver_class_path` (`entity_registry.py:136`); adds/changes NO
      descriptor value (§6); UV-P (instantiation path) resolved at build.
- [ ] **Logging + metric emitted** (§7) — manifest-build + `len(custom_fields)` at
      the entry seam; per-field state; present-but-null observable.
- [ ] **All new tests GREEN** (§9.1-9.4); **certified suite GREEN** (floor 118).
- [ ] **NO Asana call added; NO frozen-surface edit** (§8 re-verified by grep).

---

## 11. UV-Ps (could not settle by inspection)

1. **[UV-P: `_extract_raw_value` reuse mechanism | METHOD: deferred-to-build |
   REASON: private-method cross-module call vs a one-line additive promotion to a
   module-level pure function in `default.py`; PE picks the lower-risk form at build.
   The contract (reuse the existing dispatch, do not reimplement) holds under both.]**
   (§5.2)

2. **[UV-P: resolver-instantiation path | METHOD: deferred-to-build | REASON: reuse
   `UniversalResolutionStrategy._get_custom_field_resolver` vs inline the 3-line
   descriptor→import→instantiate in `dynvocab.py`; depends on the dependency-graph
   weight of importing `universal_strategy`. The descriptor-driven CONTRACT holds
   either way.]** (§6)

3. **[UV-P: planner-partition test-surface | METHOD: deferred-to-build | REASON:
   D-T1a moves the `unknown-field` interception from plan-time to tail-time. Existing
   non-scar tests asserting the old plan-time raise must be audited and updated
   additively. I confirmed the planner raise exists (`planner.py:127-129`) but did
   not enumerate every test asserting it. PE enumerates at build; the caller-visible
   `unknown-field` verdict for a genuinely-absent field is PRESERVED.]** (§2, §9.2)

4. **[UV-P: live asset_id population | METHOD: settled-by-PT-01 | REASON: the
   present-but-null state is not hypothetical — PT-01's live fire showed Asset ID
   present 15/15, populated 0/15. The contract's PRESENT_BUT_NULL state is the
   first-class home for that observed reality; sprint-3 FRAME-002's comma-split
   override flips it to PRESENT-as-SET once a populated canary is selected.]**

---

## 12. Acid test

*"Will this contract look obviously right in 18 months?"* Yes. The three-state model
(PRESENT / PRESENT_BUT_NULL / ABSENT) names a distinction the live platform actually
exhibits (PT-01: present-but-null is real), expressed in the EXISTING result types
with zero schema churn — so S3 can enrich PRESENT_BUT_NULL → PRESENT (date hole) and
PRESENT.value (override) without re-opening the contract, and S4 reads the same
manifest the tail builds. The one non-obvious decision (D-T1a: intercept at the
planner, not the engine stub, because the stub is unreachable for non-schema fields)
is the kind of thing that would be a silent 18-month landmine if undocumented — it is
the §2 surprise, made load-bearing. No one-way door: the tail is additive,
`is_identity=False`, cache-only, and the closed `unknown-field` vocabulary is
preserved, not widened.
