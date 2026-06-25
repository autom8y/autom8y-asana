---
type: spec
artifact_class: tdd
initiative: gfr-dynvocab
sprint: sprint-1
title: "Probe + Seam — GAP-1 probe harness + GAP-2 EntryAnchor threading"
status: draft
created: 2026-06-25
author: architect (10x-dev)
rite: 10x-dev
code_truth_anchor: "feat/gfr-engine 2092f771 (worktree /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr)"
keying_axis: NAME
evidence_grade: "[STRUCTURAL | MODERATE]"
frame_ref: .sos/wip/frames/gfr-dynvocab.md
shape_ref: .sos/wip/frames/gfr-dynvocab.shape.md
telos_ref: .know/telos/gfr-dynvocab.md
handoff_ref: .ledge/reviews/handoffs/gfr-dynvocab-rnd-to-10x-handoff.md
addresses: ["GAP-1", "GAP-2"]
pr_boundary: "ONE strictly-additive asana-engine PR on feat/gfr-engine; sprint-1 contributes the probe harness + EntryAnchor seam only"
regression_floor: "105 passed (tests/unit/resolution/gfr/ + tests/integration/test_gfr_tenant_roundtrip.py) — re-confirmed GREEN this pass at 2092f771"
---

# TDD-delta — gfr-dynvocab sprint-1 (Probe + Seam)

> Foundation sprint of a 5-sprint, ONE-additive-PR build. Two additive pieces:
> (1) the **GAP-1 probe harness** (operator-fireable; offline-fixture for CI, single
> operator command for the live fire); (2) the **GAP-2 EntryAnchor threading** that
> exposes the already-hydrated entry task to the future sprint-2 tail resolver.
> NO production code is written here — this delta is the design + test plan the
> principal-engineer implements. Sprint internals are non-prescriptive (shape §2);
> this delta fixes ONLY the seam shape, the frozen-surface attestation, and the
> RED→GREEN test contract.

---

## 1. Context & Constraints (binding — not re-litigated)

Read the frame/shape/handoff/telos; this delta does not re-derive them. The
load-bearing constraints that gate every design decision below:

- **Strictly-additive.** ZERO edits to `query/{engine,join,compiler}.py`, the
  `@pytest.mark.scar` tests, `_resolve_identity_plan_async`, or
  `guard.py::assert_rows_tenant_identity`. Crossing any frozen surface requires an
  explicit ADR + rite-disjoint corroboration — never a silent diff.
- **NAME-keyed, never gid-keyed** (operator correction supersedes the recon's
  gid-keying). Sprint-1 introduces no keying surface at all — it threads a *task
  object*, not a field index — so this constraint is satisfied vacuously here and
  becomes load-bearing in sprint-2.
- **Cache-only.** No new Asana call beyond the already-accounted entry read. The
  entry fetch at `hydration.py:281-284` already uses full opt-fields
  (`fields.py:232-251 STANDARD_TASK_OPT_FIELDS`, aliased
  `_BUSINESS_FULL_OPT_FIELDS` at `hydration.py:69`). HYP-1's code layer is
  confirmed (SVR below). Sprint-1 adds NO fetch.
- **Certified suite stays GREEN at sprint exit** — `./.venv/bin/python -m pytest`,
  NEVER `uv run` (CodeArtifact 401).

### 1.1 SVR receipts (direct inspection this pass, worktree `feat/gfr-engine` `2092f771`)

| Claim | Method | Anchor | Verbatim marker |
|-------|--------|--------|-----------------|
| Entry fetch uses full opt-fields (HYP-1 code layer) | file-read | `src/autom8_asana/models/business/hydration.py:281-284` | `entry_task = await client.tasks.get_async(` … `opt_fields=_BUSINESS_FULL_OPT_FIELDS,` |
| `_BUSINESS_FULL_OPT_FIELDS` is exactly `STANDARD_TASK_OPT_FIELDS` | file-read | `src/autom8_asana/models/business/hydration.py:69` | `_BUSINESS_FULL_OPT_FIELDS: list[str] = list(STANDARD_TASK_OPT_FIELDS)` |
| Bare `custom_fields` + typed value subfields present; `date_value` ABSENT | file-read | `src/autom8_asana/models/business/fields.py:240-250` | `"custom_fields",` … `"custom_fields.text_value",` (no `date_value` member) |
| `EntryAnchor` is a frozen slotted dataclass with 4 fields | file-read | `src/autom8_asana/resolution/gfr/entry.py:45-64` | `@dataclass(frozen=True, slots=True)` / `gid: str` … `path_len: int` |
| EntryAnchor is constructed at lines 111-116 (the GAP-2 thread point) | file-read | `src/autom8_asana/resolution/gfr/entry.py:111-116` | `anchor = EntryAnchor(` … `path_len=len(result.path),` |
| The hydrated entry task is ALREADY in hand and currently DISCARDED | file-read | `src/autom8_asana/models/business/hydration.py:152` + `entry.py:103-110` | `entry_entity: BusinessEntity \| None = None` ; entry.py reads `result.entry_type`, `result.business.gid`, `result.path` but not `result.entry_entity` |
| `entry_entity` is `None` when the entry gid IS a Business | file-read | `src/autom8_asana/models/business/hydration.py:319-322` | `entry_entity = None  # Started at Business` |
| The cf manifest lives on `Task.custom_fields` (sprint-2 reads this) | file-read | `src/autom8_asana/models/task.py:146` | `custom_fields: list[dict[str, Any]] \| None = Field(` |
| `assert_rows_tenant_identity` reads ONLY `row["gid"]` from query rows — never EntryAnchor | file-read | `src/autom8_asana/resolution/gfr/guard.py:220-222` | `row_gid = row.get(_ROW_GID_KEY)` ; `_ROW_GID_KEY: Final[str] = "gid"` |
| Engine no-identity stub (sprint-2 target, NOT sprint-1) | file-read | `src/autom8_asana/resolution/gfr/engine.py:230-235` | `if not identity_plans:` … `raise UnresolvedError(fields=field_list, reason="no-identity-path")` |
| Regression floor GREEN | bash-probe | `./.venv/bin/python -m pytest tests/unit/resolution/gfr/ tests/integration/test_gfr_tenant_roundtrip.py -q` | `105 passed in 0.34s` (exit 0) |

> **Note on line drift vs the shape.** The shape cites `hydration.py:283` for the
> entry fetch; direct inspection puts the `get_async` call at `281-284` (the
> `opt_fields=` kwarg is line 283). The shape cites `entry.py:111-116` for the
> threading point; direct inspection confirms the `EntryAnchor(...)` constructor
> spans `entry.py:111-116` verbatim. Both shape anchors are correct to within the
> multi-line construct; this delta uses the inspected line spans.

---

## 2. Piece 1 — GAP-2 EntryAnchor threading (the seam)

### 2.1 The gap, precisely

The entry phase (`entry.py::_fetch_and_anchor_async`) consumes
`hydrate_from_gid_async(..., hydrate_full=False)`, whose `HydrationResult` already
carries `entry_entity: BusinessEntity | None` — the hydrated entry task, fetched
with full opt-fields, **carrying every custom field with its typed values**
(HYP-1). Today the entry phase extracts `result.entry_type`, `result.business.gid`,
and `len(result.path)` into `EntryAnchor`, and **silently discards
`result.entry_entity`**. The sprint-2 tail resolver has no hydrated task to read
the cf manifest off. GAP-2 closes that by threading the task onto `EntryAnchor`.

### 2.2 Additive shape decision

`EntryAnchor` is `@dataclass(frozen=True, slots=True)` (`entry.py:45`). Add ONE
optional field with a default, so all existing positional/keyword constructions
remain valid and the dataclass stays frozen+slotted:

```python
# entry.py — additive field on EntryAnchor (sprint-1)
entry_task: BusinessEntity | None = None
```

Design decisions (each with rationale — these are the load-bearing choices the
principal-engineer must honor, not invent around):

- **D-1 — Optional with `None` default.** A default keeps every existing
  `EntryAnchor(...)` call site and every test construction valid without edit, and
  preserves `slots=True` (slotted frozen dataclasses permit field defaults). This
  is what makes the change strictly-additive at the type level.

- **D-2 — Type is `BusinessEntity | None`, matching `HydrationResult.entry_entity`
  exactly.** No new type is introduced. The threaded object is the SAME object
  hydration already produced; sprint-1 only stops discarding it. `BusinessEntity`
  subclasses `Task`, which declares `custom_fields: list[dict] | None`
  (`task.py:146`) — the manifest carrier the sprint-2 tail consumes. Import under
  `TYPE_CHECKING` (it is annotation-only on the dataclass) to avoid a runtime
  import-cost / cycle; `from __future__ import annotations` is already in force at
  `entry.py:27`.

- **D-3 — Thread the cf-CARRYING task in BOTH entry topologies (the surprise —
  see §6).** `result.entry_entity` is `None` when the entry gid IS a Business
  (`hydration.py:319-322`: "Started at Business"). In that case the cf manifest
  lives on `result.business`, not on `entry_entity`. To give the sprint-2 tail a
  uniform, non-None carrier whenever one exists, the threading reads:

  ```python
  # entry.py:111-116 — the additive thread (conceptual; PE implements)
  anchor = EntryAnchor(
      gid=gid,
      entity_type=entity_type,
      business_gid=business_gid,
      path_len=len(result.path),
      entry_task=result.entry_entity if result.entry_entity is not None else result.business,
  )
  ```

  Rationale: for a non-Business entry (Offer canary `b167331c-...`), `entry_entity`
  is the hydrated Offer task carrying its cfs. For a Business entry, `business` IS
  the hydrated entry task carrying its cfs. Either way `entry_task` is the
  cf-bearing task for the entry gid, and the sprint-2 tail has a single uniform
  source. This is a one-line conditional, still additive, still zero new fetch
  (both objects already exist in `result`).

  > **DEFER-NOTE (PT-01-adjacent).** If the sprint-2 tail design later prefers the
  > strict literal (`entry_task = result.entry_entity`, i.e. `None` for a Business
  > entry, leaving the Business-cf path to a separate branch), that is a sprint-2
  > tail-contract decision, not a sprint-1 seam decision. The seam SHAPE
  > (`entry_task: BusinessEntity | None`) is identical either way; only the value
  > assigned at the construct site differs. D-3 (the cf-carrying-in-both-topologies
  > assignment) is the recommended default because it gives the tail a uniform
  > carrier; PE may surface to PT-01/sprint-2 if the tail wants the literal. The
  > frozen-surface attestation (§4) holds under either assignment.

- **D-4 — Update the `EntryAnchor` docstring** (`entry.py:47-58`) with the new
  attribute, marking it explicitly: *"Carries the hydrated entry task (cf manifest)
  for the `is_identity=False` dynamic tail (sprint-2). NOT part of the identity
  spine; never read by `assert_rows_tenant_identity`."* Documentation-only;
  reinforces the invisibility invariant for future readers.

### 2.3 Exact file:line seam point

| What | File:line (worktree `2092f771`) |
|------|-----------------------------------|
| Add `entry_task` field + docstring line | `src/autom8_asana/resolution/gfr/entry.py:60-64` (field block) + `entry.py:47-58` (docstring) |
| `TYPE_CHECKING` import of `BusinessEntity` | `src/autom8_asana/resolution/gfr/entry.py:39-40` (existing `if TYPE_CHECKING:` block) |
| Thread the task at the constructor | `src/autom8_asana/resolution/gfr/entry.py:111-116` (the `EntryAnchor(...)` call) |

No other production file changes for GAP-2. The engine (`engine.py`) does NOT need
to read `anchor.entry_task` in sprint-1 — the field is threaded and dormant until
the sprint-2 tail consumes it. (The engine no-identity stub at `engine.py:230-235`
is the sprint-2 target and is UNTOUCHED here.)

---

## 3. Piece 2 — GAP-1 probe harness (operator-fireable)

### 3.1 The question the probe settles

The single HIGH platform UV-P (R-GAP1, shape §9): **does the bare `custom_fields`
opt-field return `asset_id` POPULATED for the live canary
`b167331c-536f-4996-9b2d-2f696f35f556`?** HYP-1's *code layer* is SVR-confirmed
(opt-fields request bare `custom_fields` + typed subfields); the residual unknown
is the *Asana platform semantic* — whether the live API actually returns the
`asset_id` cf with a value on that fetch. This is NOT statically confirmable; only
a live fetch settles it. It is the PT-01 fork input (free-tail vs ~2x frame-based
fallback).

### 3.2 Design principle — the live fire is the OPERATOR's lever

The harness MUST satisfy three properties (dispatch-binding):

1. **Offline-by-default for CI.** The default code path runs against a
   recorded/guarded fixture and emits a receipt — NO live Asana call. This is what
   the certified suite (if it references the harness at all) exercises.
2. **Live fire is a single clearly-marked operator command.** One explicit command,
   gated behind an env flag, that the operator runs out-of-band. It is NOT invoked
   by any `pytest` collection, fixture, or CI step.
3. **Nothing in the certified test suite ever fires a live Asana call.** The
   live-fire entrypoint is guarded so that even if imported under pytest, it
   refuses to fire without the explicit operator env flag set.

### 3.3 Harness placement & shape

Place the harness OUTSIDE `tests/` so pytest never auto-collects it, and outside
`src/autom8_asana/` so it is not shipped engine code:

| Artifact | Path | Role |
|----------|------|------|
| Probe harness module | `scripts/gfr_dynvocab/gap1_probe.py` | The operator-fireable probe + offline-fixture path |
| Offline fixture | `scripts/gfr_dynvocab/fixtures/gap1_canary_custom_fields.json` | Recorded/guarded `custom_fields` array shape for offline mode + CI |
| Receipt (emitted) | `.ledge/spikes/gfr-dynvocab-gap1-probe-receipt.md` | The exit artifact (shape §2 sprint-1 exit_artifacts) |

> **Placement rationale.** `scripts/` is not on the pytest `testpaths` and not in
> the shipped package. If the project has no `scripts/` convention, PE may use
> `.sos/wip/spikes/gfr-dynvocab/` (the same throwaway-spike location the rnd
> prototype used, never committed to engine code) — but `scripts/` is preferred
> because the harness is a *retained* operator tool, not a throwaway. PE confirms
> the repo convention at build (UV-P, §7).

### 3.4 Harness contract (two modes, one receipt format)

```
python scripts/gfr_dynvocab/gap1_probe.py --mode=offline
    → reads fixtures/gap1_canary_custom_fields.json
    → runs the SAME assertion logic (asset_id present? populated?)
    → emits receipt with mode=offline, source=fixture
    → ALWAYS safe; this is what CI / a non-operator run does

GFR_GAP1_LIVE_FIRE=1 python scripts/gfr_dynvocab/gap1_probe.py --mode=live \
    --canary=b167331c-536f-4996-9b2d-2f696f35f556
    → REFUSES unless env GFR_GAP1_LIVE_FIRE=1 is set (operator's explicit lever)
    → constructs a real AsanaClient, calls client.tasks.get_async(
        canary, opt_fields=STANDARD_TASK_OPT_FIELDS)   # the SAME opt-fields the entry phase uses
    → asserts asset_id (cf name "Asset ID") is present AND value-populated
    → emits receipt with mode=live, source=asana-live, the verbatim cf slice
```

Design decisions:

- **D-5 — Reuse `STANDARD_TASK_OPT_FIELDS` verbatim.** The live probe MUST request
  the identical opt-field set the entry phase uses (`fields.py:232-251`), so the
  probe faithfully tests HYP-1's actual production fetch — not a hand-rolled
  opt-field list that could mask or fabricate the answer.
- **D-6 — The assertion logic is shared between modes.** A single
  `assess_custom_fields(custom_fields: list[dict]) -> ProbeVerdict` function is
  called by both modes; only the *source* of `custom_fields` differs (fixture vs
  live API). This guarantees the offline receipt and the live receipt are
  produced by identical evaluation code — the offline mode is a faithful dry-run.
- **D-7 — Double-guard the live fire.** Both `--mode=live` AND env
  `GFR_GAP1_LIVE_FIRE=1` are required; absent the env flag the live path raises and
  exits non-zero with a clear message ("live Asana fire is the operator's lever;
  set GFR_GAP1_LIVE_FIRE=1 to confirm"). This is the structural guarantee that no
  pytest collection / CI path can fire live.
- **D-8 — The receipt is the verdict of record.** The harness writes
  `.ledge/spikes/gfr-dynvocab-gap1-probe-receipt.md` with the PT-01 fork input.

### 3.5 Receipt format (`.ledge/spikes/gfr-dynvocab-gap1-probe-receipt.md`)

```markdown
---
type: spike-receipt
initiative: gfr-dynvocab
sprint: sprint-1
probe: GAP-1
canary: b167331c-536f-4996-9b2d-2f696f35f556
mode: {offline | live}
source: {fixture | asana-live}
fired_by: {ci | operator}
fired_at: {ISO-8601}
opt_fields_ref: "src/autom8_asana/models/business/fields.py:232-251 (STANDARD_TASK_OPT_FIELDS)"
verdict: {HYP1_CONFIRMED | HYP1_REFUTED | OFFLINE_DRY_RUN}
---

# GAP-1 Probe Receipt — does bare custom_fields return asset_id populated?

## Verdict
{HYP1_CONFIRMED — asset_id present and value-populated on the live canary fetch}
{HYP1_REFUTED — asset_id absent/empty; PT-01 must pivot to frame-based fallback (~2x)}
{OFFLINE_DRY_RUN — fixture-based; live fire pending operator command}

## Evidence (verbatim)
- opt_fields requested: {the STANDARD_TASK_OPT_FIELDS tuple, verbatim}
- asset_id cf entry (verbatim slice): { {"name": "Asset ID", "text_value": "..."} | ABSENT }
- total custom_fields returned: {N}

## PT-01 fork input
- HYP1_CONFIRMED → OPTION A (free-tail): proceed to sprint-2 task-based tail. Default.
- HYP1_REFUTED   → OPTION B (frame-based fallback ~2x): re-shape sprint-2 before tail build.
- OFFLINE_DRY_RUN → verdict pending; operator must run the live fire (§3.6).
```

### 3.6 The operator-fire command (surface, do NOT execute)

> **OPERATOR LEVER — the architect/PE does NOT run this; the operator does, out of band.**

```bash
cd /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr
GFR_GAP1_LIVE_FIRE=1 ./.venv/bin/python scripts/gfr_dynvocab/gap1_probe.py \
    --mode=live \
    --canary=b167331c-536f-4996-9b2d-2f696f35f556
# → writes .ledge/spikes/gfr-dynvocab-gap1-probe-receipt.md with the live verdict
# → NEVER uv run (CodeArtifact 401)
```

The offline/CI form (safe, no live call, run by anyone including the certified
suite harness if it chooses):

```bash
cd /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr
./.venv/bin/python scripts/gfr_dynvocab/gap1_probe.py --mode=offline
```

---

## 4. Frozen-surface attestation (proof: design touches ZERO G-FROZEN surface)

The G-FROZEN surfaces (frame §"Binding Constraints", shape §7 `prescribed`):

| Frozen surface | Sprint-1 design touches it? | Proof |
|----------------|------------------------------|-------|
| `query/engine.py` | NO | Sprint-1 edits only `entry.py` + new `scripts/` files. No query/* edit. |
| `query/join.py` | NO | Same. |
| `query/compiler.py` | NO | Same. |
| `@pytest.mark.scar` tests | NO | New tests are additive (§5); no `scar`-marked test is modified. PE verifies via `grep -rl "pytest.mark.scar" tests/` — none are in the GAP-2 edit set. |
| `_resolve_identity_plan_async` | NO | Lives in `engine.py`; sprint-1 makes ZERO engine edits. The threaded `entry_task` is dormant until sprint-2. |
| `guard.py::assert_rows_tenant_identity` | NO | Guard is UNTOUCHED. **Invisibility proof below.** |

### 4.1 Invisibility proof — the seam is invisible to `assert_rows_tenant_identity`

`assert_rows_tenant_identity(rows, business_gid)` (`guard.py:183-237`) iterates the
**query-result rows** and reads only `row.get(_ROW_GID_KEY)` where
`_ROW_GID_KEY = "gid"` (`guard.py:68`, `guard.py:220-222`). It NEVER receives or
inspects an `EntryAnchor`. The new `entry_task` field:

1. is on `EntryAnchor`, a type the guard never sees;
2. carries `is_identity=False` semantics by construction — it is enrichment-task
   data, not an identity plan element (`FieldPlan.is_identity` defaults `False`,
   `models.py:128`; no identity plan is created for it);
3. is dormant in sprint-1 (no engine code reads it), so it cannot enter
   `_resolve_identity_plan_async`, `assert_plan_identity_pure`, or
   `assert_rows_tenant_identity`.

Therefore the seam is structurally invisible to the identity guard and the identity
spine. The mechanical proof is the regression floor: the 105 certified tests
(which exercise the guard) stay GREEN with the field added (§5 RED→GREEN contract).

### 4.2 Cache-only attestation

Sprint-1 adds NO production Asana call. GAP-2 threads an object that
`hydrate_from_gid_async` ALREADY produced (the entry fetch is the single accounted
read; `entry_entity`/`business` are in `result`). The GAP-1 probe's live fetch is
NOT production code — it is an out-of-band operator-fired script under `scripts/`,
guarded so the certified suite never fires it. The cache-only contract (no new
Asana call beyond the accounted entry read) holds.

---

## 5. Test-delta — the RED→GREEN contract for principal-engineer

> Sprint-1 is strictly-additive, so the dominant gate is **the 105 certified tests
> stay GREEN** (the additive field must not regress anything). The NEW tests below
> are the GAP-2 / GAP-1 coverage the PE writes. Test grain follows the existing
> `tests/unit/resolution/gfr/test_entry.py` + `conftest.py` patterns.

### 5.1 GAP-2 EntryAnchor threading tests (`tests/unit/resolution/gfr/test_entry.py`)

| Test | RED (before impl) | GREEN (after impl) |
|------|-------------------|---------------------|
| `test_entry_anchor_has_entry_task_field` | `AttributeError` / TypeError — field absent | `EntryAnchor(...)` accepts/exposes `entry_task`; default `None` |
| `test_offer_entry_threads_hydrated_task` | fails — `anchor.entry_task is None` | for a non-Business entry, `anchor.entry_task is result.entry_entity` (the hydrated Offer task) |
| `test_business_entry_threads_business_as_task` | fails — `anchor.entry_task is None` | for a Business entry (`entry_entity is None`), `anchor.entry_task is result.business` (D-3) |
| `test_entry_task_carries_custom_fields` | fails | the threaded task exposes `.custom_fields` (the cf manifest carrier sprint-2 reads) |
| `test_existing_entry_anchor_fields_unchanged` | n/a (regression) | `gid/entity_type/business_gid/path_len` unchanged for the canonical Offer case (proves additivity) |

**Fixture delta (`conftest.py::make_hydration_result`).** The helper currently
hardcodes `entry_entity=None` (`conftest.py:56`). Add an optional
`entry_entity: BusinessEntity | None = None` parameter (additive, default preserves
all existing callers) so the GAP-2 tests can supply a hydrated entry task carrying
`custom_fields`. PE may add a small `make_entry_task(custom_fields=[...])` helper
returning a `BusinessEntity` (or the project's task model) with a populated
`custom_fields` list for the threading + cf-carrier assertions.

### 5.2 GAP-2 guard-invisibility test (additive — `tests/unit/resolution/gfr/test_guard.py` or `test_entry.py`)

| Test | Asserts |
|------|---------|
| `test_entry_task_invisible_to_identity_guard` | constructing an `EntryAnchor` WITH a populated `entry_task` does not change `assert_rows_tenant_identity` behavior — the guard still passes/fails purely on `row["gid"]`, never reading the anchor. (Drives home §4.1; cheap, high-signal.) |

### 5.3 GAP-1 probe harness tests (`tests/unit/.../test_gap1_probe.py` — offline only)

> These test the harness's OFFLINE path + the live-fire guard. They NEVER fire a
> live Asana call (D-7 guarantees this even under pytest).

| Test | Asserts |
|------|---------|
| `test_offline_mode_reads_fixture_and_emits_verdict` | `--mode=offline` against the fixture produces a `ProbeVerdict` (CONFIRMED/REFUTED shape) without any client call |
| `test_assess_custom_fields_detects_populated_asset_id` | `assess_custom_fields([{"name":"Asset ID","text_value":"a,b"}])` → asset_id present + populated |
| `test_assess_custom_fields_detects_absent_asset_id` | `assess_custom_fields([])` / no Asset ID → REFUTED-shaped verdict |
| `test_live_fire_refuses_without_operator_env_flag` | calling the live path WITHOUT `GFR_GAP1_LIVE_FIRE=1` raises / exits non-zero and makes NO client call (the double-guard, D-7) |
| `test_live_path_never_invoked_by_default_collection` | importing/collecting the module under pytest triggers no live call (module import is side-effect-free) |

### 5.4 Mechanical regression gate (every sprint, frame constraint 5 / GAP-11)

```bash
cd /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr
./.venv/bin/python -m pytest tests/unit/resolution/gfr/ tests/integration/test_gfr_tenant_roundtrip.py
# MUST stay GREEN (baseline 105 passed at 2092f771; new additive tests raise the count).
# NEVER uv run (CodeArtifact 401).
```

> **On the "105" figure (frame UV-P, carried).** The realization predicate treats
> the gate as *the suite passing*, not an exact integer. Sprint-1 adds new
> additive test functions, so the count rises above 105; the binding gate is GREEN,
> and that the pre-existing 105 still pass (no regression). PE re-confirms the
> running count at build.

---

## 6. What surprised me (UV-Ps I could not settle by inspection)

1. **`entry_entity` is `None` for a Business entry — the cf carrier diverges by
   topology.** I expected `HydrationResult.entry_entity` to always be the hydrated
   entry task. It is not: `hydration.py:319-322` sets `entry_entity = None` when the
   entry gid IS a Business (the cf manifest then lives on `result.business`). This
   forced design decision D-3 (thread the cf-carrying task in BOTH topologies via a
   one-line conditional) rather than the naive `entry_task = result.entry_entity`.
   The seam SHAPE is unchanged either way; only the construct-site value differs.
   **This is the single most load-bearing surprise — PE must not blindly assign
   `result.entry_entity`.** Surfaced to PT-01/sprint-2 as a DEFER-NOTE (§2.2 D-3).

2. **[UV-P: live-Asana asset_id population on bare custom_fields | METHOD:
   deferred-to-operator-live-fire | REASON: Asana platform semantic; not statically
   confirmable. The HYP-1 *code layer* is SVR-confirmed (opt-fields request bare
   custom_fields + typed subfields, fields.py:232-251), but whether the live API
   returns asset_id POPULATED for canary b167331c-... is settled ONLY by the §3.6
   operator-fire. This is R-GAP1 / the PT-01 fork input — by design unsettled at
   sprint-1 architecture time.]**

3. **[UV-P: `scripts/` convention existence | METHOD: deferred-to-build | REASON:
   I did not confirm whether the repo has an established `scripts/` directory /
   testpaths exclusion. PE confirms at build; fallback placement is
   `.sos/wip/spikes/gfr-dynvocab/` (the rnd throwaway-spike location). Either
   placement satisfies the "never auto-collected by pytest" requirement.]**

4. **The shape's `entry.py:111-116` and `hydration.py:283` anchors are correct to
   within a multi-line construct** (the `EntryAnchor(...)` call literally spans
   111-116; the `opt_fields=` kwarg is line 283 inside the 281-284 `get_async`
   call). No re-litigation needed; noted for PE precision.

---

## 7. Handoff checklist for principal-engineer

Implementation is GREEN-ready when ALL hold:

- [ ] **GAP-2 field added.** `entry_task: BusinessEntity | None = None` on
      `EntryAnchor` (`entry.py:60-64`); `TYPE_CHECKING` import of `BusinessEntity`
      added (`entry.py:39-40`); docstring updated (D-4).
- [ ] **GAP-2 threaded.** The `EntryAnchor(...)` construct at `entry.py:111-116`
      passes `entry_task=` per D-3 (cf-carrying task in both topologies). No engine
      edit.
- [ ] **GAP-2 tests GREEN** (§5.1, §5.2), including the additive-no-regression test
      and the guard-invisibility test.
- [ ] **`conftest.py::make_hydration_result` extended** with an additive
      `entry_entity` param (default `None`); optional `make_entry_task` helper.
- [ ] **GAP-1 harness built** at `scripts/gfr_dynvocab/gap1_probe.py` (or the
      confirmed fallback path) with: shared `assess_custom_fields` (D-6),
      offline+live modes, the double-guard (D-7) reusing `STANDARD_TASK_OPT_FIELDS`
      (D-5), and receipt emission (§3.5).
- [ ] **Offline fixture committed** at `scripts/gfr_dynvocab/fixtures/gap1_canary_custom_fields.json`.
- [ ] **GAP-1 harness tests GREEN** (§5.3) — offline-only, live-fire-refusal proven.
- [ ] **NO production Asana call added; NO frozen-surface edit** (§4 attestation
      re-verified: `grep`-confirm zero edits to `query/{engine,join,compiler}.py`,
      `_resolve_identity_plan_async`, `assert_rows_tenant_identity`, and any
      `@pytest.mark.scar` test).
- [ ] **Certified suite GREEN** — `./.venv/bin/python -m pytest tests/unit/resolution/gfr/ tests/integration/test_gfr_tenant_roundtrip.py` (NEVER `uv run`); pre-existing 105 still pass.
- [ ] **Operator-fire surfaced, NOT executed.** The §3.6 command is documented for
      the operator; the architect/PE does not fire it. The probe RECEIPT
      (`.ledge/spikes/gfr-dynvocab-gap1-probe-receipt.md`) is emitted by the
      offline run at build; the live verdict is appended when the operator fires.
- [ ] **PT-01 input ready.** The receipt records the fork input
      (HYP1_CONFIRMED/REFUTED/OFFLINE_DRY_RUN) so PT-01 can decide free-tail vs
      ~2x frame-based fallback.

---

## 8. Acid test

*"Will this seam look obviously right in 18 months?"* Yes: GAP-2 adds one optional
field that stops discarding an object hydration already builds — the minimum
additive surface, dormant until sprint-2 consumes it, structurally invisible to the
identity guard. GAP-1's probe is an out-of-band operator tool that can never fire
live from CI by construction. The one non-obvious choice (D-3, cf-carrier in both
topologies) is documented with its rationale and flagged for the sprint-2 tail
contract. No one-way door is opened.
