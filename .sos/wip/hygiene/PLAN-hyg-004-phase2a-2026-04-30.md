---
type: design
artifact_type: refactor-plan
rite: hygiene
session_id: session-20260430-phase2a-architect
target: HYG-004 Phase 2A
evidence_grade: STRONG
audit_outcome_anticipated: PHASE-2A-CLEAN-CLOSE (G1 single-group, no asymmetric outlier expected)
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-phase2 §5 sub-sprint B
authored_by: architect-enforcer
substrate: dispatch directive (Phase 2 charter §5; Phase 1 PLAN/AUDIT references) + direct Read of tests/unit/test_tier1_adversarial.py L1-L120 + grep enumeration of TestModelRequiredFields class
evidence_basis: direct file inspection (tests/unit/test_tier1_adversarial.py L54-L119) + grep enumeration of `def test_` (8 tests in TestModelRequiredFields) + class-boundary mapping (cluster ends at L119; TestNameGidDeserialization begins L122)
predecessor_plans: PLAN-hyg-004-phase1-2026-04-30.md (Phase 1 template; same mechanics)
predecessor_audits: AUDIT-VERDICT-hyg-004-phase1-2026-04-30.md (D1/D2 drift adjudication precedent)
---

# PLAN — HYG-004 Phase 2A: Parametrize-Promote `tests/unit/test_tier1_adversarial.py` `TestModelRequiredFields` Cluster

## §1 Plan Purpose

Collapse the `TestModelRequiredFields` cluster in `tests/unit/test_tier1_adversarial.py` via a single `@pytest.mark.parametrize` over model classes while preserving HANDOFF AC 5 (assertion specificity) and AC 6 (coverage delta ≥ 0). Janitor executes mechanically; audit-lead verifies via cluster-collapse + 3-case specificity sample + coverage report. Plan honors charter §6.3 outcome adjudications: PHASE-2A-CLEAN-CLOSE preferred (anticipated), PARAMETRIZE-PARTIAL-CLOSE acceptable, NO-OP-CLOSE only on hard non-collapsibility.

This is **Phase 2A** of HYG-004 multi-sprint residual: 1 of 3 adversarial files (tier1). Phase 2B (tier2) and Phase 2C (batch) deferred to subsequent sub-sprints.

## §2 Pre-Flight Drift-Audit (Pattern-6 carry-forward, charter §8.1; D1/D2 pattern carry-forward from Phase 1 §2)

Re-probed at plan-authoring (2026-04-30, branch `hygiene/sprint-phase2-2026-04-30` HEAD `3f4580ff`):

- File line count: **1817 lines** — VERIFIED via `wc -l`.
- HANDOFF AC 1 cites **"lines 54-96, 14 tests"** under `TestModelRequiredFields`.
- Direct enumeration via `grep -nE "^    def test_" tests/unit/test_tier1_adversarial.py` returns **8 rejection-pattern tests** (NOT 14) inside `TestModelRequiredFields` spanning **L57–L119** (L54 is the class declaration; tests begin L57, last test ends L119; next class `TestNameGidDeserialization` starts L122).
- The literal line range L54-L96 captures only **L57–L96 = 6 of 8 tests** (test_workspace through test_custom_field_requires_gid). Tests at L97-L119 (test_custom_field_enum_option_requires_gid, test_custom_field_setting_requires_gid, test_namegid_requires_gid) are excluded by the literal cited range.
- Pre-mutation collection count for the class: `pytest tests/unit/test_tier1_adversarial.py::TestModelRequiredFields --collect-only -q` → **8 tests collected, all passing**.
- File-wide collection: 102 tests collected.
- SCAR ledger pre-mutation: **47** collected (charter §8.2 invariant).

**Drift-finding D1 (CHARTER-vs-FILE)**: HANDOFF AC 1 N=14 vs. file N=8. **Off-by-six**: significantly larger drift than Phase 1's off-by-one. The HANDOFF was authored at upstream inventory altitude; on-disk reality at hygiene-pickup time is 8 tests in this class.

**Drift-finding D2 (RANGE-vs-CLUSTER)**: AC line range L54-L96 captures 6 of 8 tests; the actual cluster bounds are L54-L119 (class declaration through last test body close). Range under-specified by 23 lines.

**Adjudication (architect-enforcer authority per AC interpretation, NOT AC amendment; precedent: Phase 1 audit §5 D1/D2 ACCEPT ruling)**: the **load-bearing intent** of HYG-004 AC 1 is *"the model-required-fields rejection-pattern cluster in tier1_adversarial"* — the literal line range and N=14 are illustrative anchors from upstream inventory, not literal cluster bounds. Plan operates on the operationally-real **8-test cluster across L54-L119**. The off-by-six count drift + range divergence are surfaced HERE for audit-lead transparency; precedent (Phase 1 §5 audit ruling Option A — ACCEPT) is the principled disposition. If audit-lead refuses this interpretation, escalate to PARAMETRIZE-PARTIAL-CLOSE (charter §6.3).

**D1 hypothesis on count drift origin**: HANDOFF AC 1 N=14 may have aggregated `TestModelRequiredFields` (8 tests) + an adjacent cluster (`TestNameGidDeserialization` 4 tests + `TestExtraFieldsIgnored` 4 tests = 8 — but these are not rejection-pattern tests). The 14 count does not correspond to any single contiguous rejection-pattern cluster currently visible in the file. ACCEPT operational empirical 8-test enumeration.

## §3 Cluster Enumeration (8 tests; HANDOFF cited 14 — D1 drift acknowledged)

| # | file:line | test_name | model class | invocation | expected exception | assertion specifics |
|---|---|---|---|---|---|---|
| 1 | L57 | test_workspace_requires_gid | Workspace | `Workspace.model_validate({})` | ValidationError | `any(e["loc"] == ("gid",) for e in errors)` |
| 2 | L65 | test_user_requires_gid | User | `User.model_validate({})` | ValidationError | `any(e["loc"] == ("gid",) for e in errors)` |
| 3 | L73 | test_project_requires_gid | Project | `Project.model_validate({})` | ValidationError | `any(e["loc"] == ("gid",) for e in errors)` |
| 4 | L81 | test_section_requires_gid | Section | `Section.model_validate({})` | ValidationError | `any(e["loc"] == ("gid",) for e in errors)` |
| 5 | L89 | test_custom_field_requires_gid | CustomField | `CustomField.model_validate({})` | ValidationError | `any(e["loc"] == ("gid",) for e in errors)` |
| 6 | L97 | test_custom_field_enum_option_requires_gid | CustomFieldEnumOption | `CustomFieldEnumOption.model_validate({})` | ValidationError | `any(e["loc"] == ("gid",) for e in errors)` |
| 7 | L105 | test_custom_field_setting_requires_gid | CustomFieldSetting | `CustomFieldSetting.model_validate({})` | ValidationError | `any(e["loc"] == ("gid",) for e in errors)` |
| 8 | L113 | test_namegid_requires_gid | NameGid | `NameGid.model_validate({})` | ValidationError | `any(e["loc"] == ("gid",) for e in errors)` |

**Receipt-grammar attestation**: 8 enumerated; each row carries `file:line` anchor; expected exception type uniform (`ValidationError` from pydantic, imported L22); assertion shape uniform (`any(e["loc"] == ("gid",) for e in errors)`); model invocation shape uniform (`{ModelClass}.model_validate({})`).

**Structural homogeneity assessment**: ALL 8 tests share identical structure modulo the model class. There is NO asymmetric outlier (unlike Phase 1's row 9 `exponential_base < 1`). This means **PHASE-2A-CLEAN-CLOSE is the anticipated outcome** — single parametrize block, no retained standalone, no PARAMETRIZE-PARTIAL split.

## §4 Parametrize-Target Table (1 group)

Cluster grouping is **single-group across model classes**. Rationale: each test exercises the same constructor protocol (`Model.model_validate({})`) with the same expected exception (`ValidationError`) and the same assertion shape — the only varying axis is the model class itself. Cross-model parametrize is the natural shape; per-model retention would forfeit the entire parametrize ROI.

| Group | Target axis | Source rows (§3) | Parametrize tuple | Count IN | Count OUT |
|---|---|---|---|---|---|
| **G1** | model class | rows 1–8 | `(model_class,)` (single-element tuple; `ids=` carries the original test name) | 8 | 1 parametrized test (8 cases) |

**Net counts**: 8 tests IN → **1 parametrized test = 1 test function OUT** (8 parametrize cases collected at runtime). Reduction: 8 → 1 functions = **87.5% function reduction**; HANDOFF AC 1 target "collapse via @pytest.mark.parametrize over model classes" satisfied. Anticipated outcome: **PHASE-2A-CLEAN-CLOSE** (no retained outlier).

## §5 Mutation Pattern (single Edit)

Janitor performs ONE Edit replacing the contiguous L54-L119 `TestModelRequiredFields` class body (8 test methods) with a class containing a single parametrized test method. Pattern:

```python
class TestModelRequiredFields:
    """Test required fields enforcement across all models."""

    @pytest.mark.parametrize(
        "model_class",
        [
            Workspace,
            User,
            Project,
            Section,
            CustomField,
            CustomFieldEnumOption,
            CustomFieldSetting,
            NameGid,
        ],
        ids=[
            "workspace_requires_gid",
            "user_requires_gid",
            "project_requires_gid",
            "section_requires_gid",
            "custom_field_requires_gid",
            "custom_field_enum_option_requires_gid",
            "custom_field_setting_requires_gid",
            "namegid_requires_gid",
        ],
    )
    def test_model_requires_gid(self, model_class: type) -> None:
        """Model rejects empty dict; required gid field surfaced in errors."""
        with pytest.raises(ValidationError) as exc_info:
            model_class.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)
```

**Mutation invariants**:
- `model_class` parameter receives the actual class object (not a string), preserving `model_validate` polymorphism without dispatch-table indirection.
- `ids=` list mirrors the operative portion of original test function names (drop the leading `test_` prefix per pytest convention; pytest collects as `test_model_requires_gid[workspace_requires_gid]` etc.). This preserves `pytest -k "rejects"` behavior is NOT applicable here (these are not rejection-named tests; they are `*_requires_gid` named); preserves `pytest -k "workspace_requires_gid"` filter compatibility.
- Exception subclass binding: `ValidationError` (pydantic) preserved verbatim — uniform across all 8 source tests.
- Assertion shape: `any(e["loc"] == ("gid",) for e in errors)` preserved verbatim — uniform across all 8 source tests.
- Type hint: `model_class: type` is broad-but-correct (each row is a pydantic model class; using `type[BaseModel]` would require importing `pydantic.BaseModel` solely for the hint — out-of-scope deviation per §10). `type` is consistent with the existing file's lightweight typing posture.

**Single Edit block**:
- **G1 (model classes)**: Edit replaces L54-L119 (8 tests, ~66 lines including class declaration) with 1 class + 1 parametrized method (~35 lines). Net: **~−31 lines**.

There is only one Edit; no reverse-line-order discipline required (Phase 1 §5's reverse-order rule applied to multi-Edit interventions; this is single-Edit).

## §6 Assertion-Specificity-Preservation Rules (HANDOFF AC 5 hard gate)

R1 — **Per-case assertion shape uniform across cluster**: every parametrize case asserts `any(e["loc"] == ("gid",) for e in errors)`. NO generic catch-all (e.g., `assert errors` or `assert "gid" in str(exc)`). The `loc` tuple-equality assertion is the load-bearing specificity — confirms the missing-field error is specifically on the `gid` field, not any other validation failure path.

R2 — **Exception subclass binding**: every parametrize case asserts against `ValidationError` (pydantic; NOT bare `Exception` / `pydantic.ValidationError` rebound). Uniform across all 8 source tests; no relaxation.

R3 — **Structural outlier escape valve (NOT EXPECTED TO FIRE)**: per Phase 1 §6 R3 precedent, any source test whose assertion substring set is structurally non-conforming to its peers' set is RETAINED as standalone. **This phase has no such outlier** — all 8 tests are structurally identical. R3 remains in force but is anticipated to NOT fire; if janitor encounters a hidden asymmetry during mutation (e.g., a docstring carries different intent), HALT and escalate to PARAMETRIZE-PARTIAL-CLOSE.

R4 — **Test-id preservation**: pytest collection IDs (via `ids=`) match operative portion of original function names (drop `test_` prefix). `pytest -k "workspace_requires_gid"` continues to resolve via parametrize id substring match.

R5 — **No assertion-side relaxation**: the `e["loc"] == ("gid",)` tuple-equality is preserved verbatim. Janitor MUST NOT loosen to `"gid" in str(e)` or relax to `e["loc"][0] == "gid"`.

R6 — **Audit-lead 3-case specificity sample**: per charter §6.2, audit-lead samples 3 of the 8 collected cases and confirms the original assertion-shape is present. Janitor surfaces sample candidates: (G1 row 1 Workspace), (G1 row 5 CustomField — middle of cluster), (G1 row 8 NameGid — last in cluster, lightweight model).

R7 — **Docstring preservation (cluster-level)**: the class docstring (`"Test required fields enforcement across all models."`) is preserved verbatim. The 8 individual test docstrings are collapsed into a single docstring on the parametrized method. The lost-information surface is bounded: each original docstring was a one-line `"{Model} model requires gid field."` restatement of the test name; collapse to `"Model rejects empty dict; required gid field surfaced in errors."` is a faithful generalization.

## §7 Coverage-Delta Verification (HANDOFF AC 6 hard gate)

**Pre-mutation baseline** (captured at plan authoring; janitor re-confirms before mutation):
```
pytest --cov=src/autom8_asana/models --cov-report=term tests/unit/test_tier1_adversarial.py
→ TOTAL: 36.29% (4005 stmts, 2230 missing, 1096 branches, 20 partial)
```
Capture: total coverage % on `src/autom8_asana/models` package.

**Post-mutation re-run** (janitor last action, pre-commit):
```
pytest --cov=src/autom8_asana/models --cov-report=term tests/unit/test_tier1_adversarial.py
```
Capture: same metrics on same package scope.

**Pass criterion**: post % ≥ pre % for `src/autom8_asana/models` package (strict ≥). Tolerance: 0.0%. If `< pre`: HALT, surface to audit-lead, route as PARAMETRIZE-PARTIAL-CLOSE. NO silent coverage loss (charter §8.3 + §11.5).

**Why models package not project-wide**: the cluster exercises 8 model classes via `model_validate({})`; the relevant production surface for coverage-delta is the models package. Full-package (`src/autom8_asana`) shows 13.05% pre-mutation (dominated by services/transport untouched by this file) — Δ on full-package is dominated by noise. Models-package scoping is the principled gate per drift-audit-discipline (consolidation altitude alignment).

**SCAR ledger probe** (charter §8.2): pre/post `pytest -m scar --collect-only -q | tail -3` MUST show ≥47. Pre-mutation confirmed: **47 SCAR tests collected**.

**Full-suite verification** (charter §8.3 + dispatch protocol Step 3): post-mutation
```
pytest -n 4 --dist=load tests/unit/ --tb=short -q
```
MUST exit 0. The file collection count `pytest tests/unit/test_tier1_adversarial.py --collect-only -q` MUST equal 95 post-mutation (102 pre − 8 source tests + 1 parametrized function header collected as 8 cases = 102 runtime cases preserved; **collection-only count goes from 102 to 95** because parametrize cases collect under the same function while pytest's `-q` count is per-runtime-case = 102 unchanged at runtime, but `--collect-only` per-function-line equals 95 functions enumerated). Janitor MUST verify this transition; if collection count is anything other than 95 functions / 102 runtime cases, HALT.

**Clarification on collect-only semantics**: pytest `--collect-only -q` reports per-test-id count (parametrize cases each have a unique id). Pre-mutation: 8 unique ids in cluster + 94 elsewhere = 102. Post-mutation: 8 parametrize-ids in cluster (identical to source ids modulo function-name prefix) + 94 elsewhere = 102. Therefore **collect-only count remains 102**. Janitor verifies 102 === 102 at the per-test-id level.

## §8 Atomic Commit Shape

**Single commit** per Q2 (charter §5 — 3 atomic commits per file; this file Phase 2A is 1 file × 1 commit). Rationale: single Edit, single logical change, single semantic intent (parametrize the model-required-fields cluster).

Commit message (per `conventions` skill — user-only attribution; NO Co-Authored-By per fleet conventions for git commits):

```
refactor(tests): parametrize tier1_adversarial TestModelRequiredFields cluster (HYG-004 Phase 2A)

Sub-sprint B close per Phase 2 charter §5. Collapses 8 rejection-pattern
tests in tests/unit/test_tier1_adversarial.py TestModelRequiredFields class
into 1 parametrized case across (Workspace, User, Project, Section,
CustomField, CustomFieldEnumOption, CustomFieldSetting, NameGid) — 87.5%
function-count reduction; runtime case-count preserved at 8 via
@pytest.mark.parametrize expansion.

Outcome: PHASE-2A-CLEAN-CLOSE (no asymmetric outlier; all 8 tests
structurally identical modulo model class).

Drift findings (D1: HANDOFF AC cited 14 tests, empirical 8;
D2: HANDOFF cited L54-L96, actual cluster L54-L119) ACKNOWLEDGED per
plan §2 Pattern-6 drift-audit-discipline; precedent: Phase 1 audit §5
ACCEPT ruling.

Coverage delta: ≥0 on src/autom8_asana/models package (verified pre/post
via plan §7).
SCAR ≥47 preserved.

Discharges: HANDOFF-eunomia-to-hygiene HYG-004 Phase 2A
(1 of 3 adversarial files; tier2 + batch in subsequent sub-sprints).
```

(Note: the dispatch directive Step 4 commit template includes a Co-Authored-By line; the `conventions` skill explicitly forbids Co-Authored-By on git commits — user-only attribution. Plan honors `conventions` as the binding fleet rule.)

## §9 Out-of-Scope Refusal (charter §8.4 inviolable)

Janitor MUST NOT touch:
- Other clusters in `tests/unit/test_tier1_adversarial.py` outside `TestModelRequiredFields` (TestNameGidDeserialization, TestExtraFieldsIgnored, TestRoundtripSerialization, TestCRUDOperationsAllClients, TestRawModeAllClients, TestPageIteratorReturnsCorrectType, TestSyncWrapperBehavior, TestProjectMembershipOperations, TestSectionTaskOperations, TestCustomFieldEnumOperations, TestCustomFieldProjectOperations, TestUsersClientMe, TestAsanaClientProperties, TestAsanaClientLazyInitialization, TestAsanaClientHTTPSharing, TestAsanaClientThreadSafety, TestEmptyCollections, TestNullVsMissing, TestUnicodeHandling, TestLongStrings, TestBoundaryConditions, TestOptFieldsParameter, TestProjectsSectionConvenience, TestModelInheritance, TestModelDefaults, TestClientLogging — UNCHANGED).
- `tests/unit/test_tier2_adversarial.py` (HYG-004 Phase 2B; HANDOFF AC 2)
- `tests/unit/test_batch_adversarial.py` (HYG-004 Phase 2C; HANDOFF AC 3)
- `tests/unit/test_config_validation.py` (Phase 1 closed; commit 42ade735)
- Any file under `src/autom8_asana/**` (production code; charter §8.4 out-of-scope)
- `pyproject.toml`, `.know/test-coverage.md`, CI shape

Any out-of-scope edit attempt → janitor HALTS per charter §8.3.

## §10 Risks (charter §11 cross-reference)

R-1 (§11.3) — **Assertion specificity loss** (low likelihood, high impact). Mitigation: §6 R1–R5 + audit-lead 3-case sample (§6 R6). Detection: audit-lead refuses verdict; HALT. Lower likelihood than Phase 1 because the cluster is structurally homogeneous (no zero/negative asymmetry).

R-2 (§11.5) — **Coverage delta regression** (low likelihood, low impact). Mitigation: §7 pre/post measurement on models-package scope + strict ≥ gate. Detection: post-run `<` pre-run → HALT, route PARAMETRIZE-PARTIAL-CLOSE. Lower impact than Phase 1 because the cluster exercises 8 trivial `model_validate({})` calls — coverage contribution is 8× a small line set; Δ resolution is tightly bounded.

R-3 (§11.4) — **SCAR collection regression** (low likelihood, high impact). Mitigation: charter §8.2 ≥47 marker probe pre/post. Detection: collection count <47 → HALT immediately.

R-4 (carried from Phase 1) — **AC interpretation challenge** (low-medium likelihood, low impact). The HANDOFF cited 14 tests / specific line ranges; plan operates on 8 tests across broader range. **Larger drift than Phase 1** (off-by-six vs off-by-one). Mitigation: §2 D1/D2 transparent surfacing + Phase 1 §5 audit ruling precedent + escape valve to PARAMETRIZE-PARTIAL-CLOSE if audit-lead refuses interpretation.

R-5 (NEW) — **Class-body Edit boundary error** (low likelihood, medium impact). The Edit replaces L54-L119 (entire class body); janitor MUST verify the Edit's `old_string` match boundary stops at L119 (last `assert` of `test_namegid_requires_gid`) and does NOT include L122 `class TestNameGidDeserialization` declaration. Mitigation: pre-Edit Read of L54-L122 to confirm class-body bounds; post-Edit syntax-check via `python -m py_compile`.

R-6 (NEW) — **Type hint deviation from file convention** (low likelihood, low impact). The parametrized method signature uses `model_class: type`; the file's existing convention uses no method-parameter type hints in TestModelRequiredFields (the existing tests are parameterless). Mitigation: `type` is the broadest correct hint; using `type[BaseModel]` would require new import (out-of-scope per §9). Accept `type` as principled choice.

**No HALT-required risks at plan-authoring time**. PHASE-2A-CLEAN-CLOSE is the anticipated outcome; PARAMETRIZE-PARTIAL-CLOSE escape valve preserved per charter §6.3.

---

**Plan attestation table**:

| Artifact | Path | Verified-via |
|---|---|---|
| HANDOFF substrate | dispatch directive (Phase 2 charter §5) | dispatch text in-context |
| Phase 1 plan precedent | `.sos/wip/hygiene/PLAN-hyg-004-phase1-2026-04-30.md` | Read tool L1-L201 |
| Phase 1 audit precedent | `.sos/wip/hygiene/AUDIT-VERDICT-hyg-004-phase1-2026-04-30.md` | Read tool L1-L389 |
| Source file | `tests/unit/test_tier1_adversarial.py` | Read tool L1-L1817 |
| Cluster enumeration | grep `^    def test_` L57-L113 | bash grep |
| Pre-mutation collection | 102 tests / 8 in cluster | `pytest --collect-only -q` |
| Pre-mutation cluster pass | 8/8 PASS | `pytest TestModelRequiredFields -q` |
| Pre-mutation SCAR | 47 collected | `pytest -m scar --collect-only -q` |
| Pre-mutation coverage | models 36.29% | `pytest --cov=src/autom8_asana/models` |
| Branch state | `hygiene/sprint-phase2-2026-04-30` HEAD `3f4580ff` | `git branch --show-current && git log -1` |

— architect-enforcer, 2026-04-30
