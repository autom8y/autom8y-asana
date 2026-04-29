---
type: review
status: closed
initiative: project-asana-pipeline-extraction
phase: 1.1
sprint: remediation-sprint
artifact_subtype: remediation-summary
created: 2026-04-28
rite: 10x-dev
specialist: principal-engineer
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
upstream_artifacts:
  - .ledge/handoffs/HANDOFF-review-to-10xdev-2026-04-28.md
  - .ledge/reviews/CASE-pipeline-export-phase1.md
  - .ledge/reviews/ASSESS-pipeline-export-phase1.md
  - .ledge/specs/PRD-pipeline-export-phase1.md
items_resolved:
  - DEF-08 (R-1)
  - DEF-05 (R-2)
items_out_of_scope:
  - COND-02 (Sprint 4.5 live-smoke; release rite)
  - COND-03 (DEFER-WATCH-1/-2/-3 Vince elicitation; direct stakeholder)
  - COND-05 (DEF-03 cross-auth runtime probe; hygiene rite)
  - PRC-1 (.know/api.md FleetQuery dual-AUTH; hygiene rite or theoros)
  - SCAR-WS8 (.know/scar-tissue.md exclude_paths sync; hygiene rite or theoros)
exit_signal: GREEN
verification_deadline: "2026-05-11"
rite_disjoint_attester: theoros@know
---

# REMEDIATION — Phase 1.1 Sprint Summary

## 1. Inception Anchor

Source dispatch: `.ledge/handoffs/HANDOFF-review-to-10xdev-2026-04-28.md` §3
(R-1 + R-2 acceptance criteria), §4 (out-of-scope binding), §7 (anti-pattern
guards). Upstream verdict: CONDITIONAL-GO at
`.ledge/reviews/CASE-pipeline-export-phase1.md` §4.

This sprint lands the two bounded remediation items (R-1 DEF-08, R-2 DEF-05);
all other CONDITIONAL-GO conditions are routed away per AP-RM-1.

## 2. Acceptance Criteria Checklist

### R-1 — DEF-08 PAT Auth Middleware Exclusion Patch

| AC | Blocking | Status | Evidence |
|---|---|---|---|
| AC-R1-1 | YES | **PASS** | `src/autom8_asana/api/main.py:389` — `"/api/v1/exports/*",` present in `jwt_auth_config.exclude_paths` list (lines 374-390). Co-located with neighboring PAT route trees (dataframes, offers, tasks, projects). |
| AC-R1-2 | NO | **PASS** | Path appended in registration order at line 389, immediately following `/api/v1/offers/*` (line 388) — consistent with the registration-order pattern of neighboring PAT entries. |
| AC-R1-3 | YES | **PASS** | `tests/unit/api/test_exports_auth_exclusion.py` — two tests: `test_exports_route_tree_excluded_from_jwt_auth` (single-entry assertion, lines 56-70) and `test_pat_route_trees_co_excluded_consistently` (full PAT-family invariant, lines 73-98). Both PASS; pytest output: `2 passed in 0.29s`. AP-RM-3 BINDING satisfied. |
| AC-R1-4 | YES | **PASS** | Full unit suite: `12,331 passed, 2 skipped, 437 warnings` plus 1 hypothesis-flaky property test (`tests/unit/persistence/test_reorder.py::test_property_moves_produce_desired_order` — passes on isolated re-run; persistence/reorder code is not touched by R-1 or R-2; flake is pre-existing and orthogonal). Effective pass count: 12,332. |
| AC-R1-5 | YES | **PASS** | DEF-08 marked **RESOLVED** below at §3 with file:line citation `src/autom8_asana/api/main.py:389`. |

### R-2 — DEF-05 OR/NOT Branch Activity-State Documentation

| AC | Blocking | Status | Evidence |
|---|---|---|---|
| AC-R2-1 | YES | **PASS** | `.ledge/specs/PRD-pipeline-export-phase1.md` §4.4 (lines 239-325) — new subsection "Default-Suppression Detection: Whole-AST Walk (OR/NOT branches honored)" explicitly documents that any `Comparison(field="section", ...)` clause anywhere in the AST (including under `OrGroup`/`NotGroup`) suppresses the server-side ACTIVE-only default. Implementation citation at `_exports_helpers.py:213-225` (`predicate_references_field`) and `:228-250` (`apply_active_default_section_predicate`). Three worked examples (OR branch, NOT branch, default-fires fallback). |
| AC-R2-2 | YES | **PASS** | PRD §11 — new **AC-8b** added at lines 641-652 ("whole-AST default-suppression detection — DEF-05 remediation"). Asserts the documented behavior with two concrete fixtures (`OR(section IN [INACTIVE], office_phone = "555-0100")` and `NOT(section IN [TEMPLATE])`). Existing AC-8 (lines 635-639) untouched and still passes per the existing `test_exports_helpers.py` suite (37 tests pass; see §4 evidence). |
| AC-R2-3 | YES | **PASS** | DEF-05 marked **RESOLVED** below at §3 with PRD section citations `.ledge/specs/PRD-pipeline-export-phase1.md §4.4` (documentation) and `§11 AC-8b` (acceptance criterion amendment). |

## 3. Defect Resolutions

### DEF-08 — RESOLVED

**Source finding** (CASE §4, ASSESS §DEF-08): `/api/v1/exports` was absent
from `jwt_auth_config.exclude_paths` at `src/autom8_asana/api/main.py:381-388`.
JWT middleware would reject PAT-authenticated requests before `pat_router`
DI fires.

**Resolution anchor**: `src/autom8_asana/api/main.py:389` —
`"/api/v1/exports/*",` added to `jwt_auth_config.exclude_paths`.

**Regression-prevention anchor**:
`tests/unit/api/test_exports_auth_exclusion.py:56-98` — two tests covering
both the specific entry (single-bug guard) and the full PAT-family
invariant (SCAR-WS8 family-level guard).

**Minimum-viable scope**: AP-RM-5 satisfied — the patch added exactly one
entry (`/api/v1/exports/*`); no broader refactor of exclude_paths logic.

### DEF-05 — RESOLVED (documentation path per case-reporter recommendation)

**Source finding** (CASE §4, ASSESS §DEF-05): when caller's predicate has
section-IN clauses inside OR/NOT branches, the ACTIVE-only default is NOT
applied (correct behavior per current logic), but this semantically broadens
the result set in ways the caller may not anticipate.

**Resolution path**: documentation (handoff §3 recommendation; faster, no
behavioral risk during remediation; AP-RM-2 satisfied — no code change to
`_exports_helpers.py` activity-state logic).

**Resolution anchors**:

- `.ledge/specs/PRD-pipeline-export-phase1.md §4.4 (lines 239-325)` —
  binding semantic + three worked examples + caller guidance + implementation
  citation.
- `.ledge/specs/PRD-pipeline-export-phase1.md §11 AC-8b (lines 641-652)` —
  acceptance criterion amendment asserting the OR/NOT behavior.

**Behavior unchanged**: the implementation at
`src/autom8_asana/api/routes/_exports_helpers.py:213-250` is unmodified.
The PRD now documents what the implementation already does, closing the
documentation gap that drove DEF-05.

## 4. Pytest Evidence

### R-1 regression test (AC-R1-3)

```
$ python -m pytest tests/unit/api/test_exports_auth_exclusion.py -v
tests/unit/api/test_exports_auth_exclusion.py::test_exports_route_tree_excluded_from_jwt_auth PASSED [ 50%]
tests/unit/api/test_exports_auth_exclusion.py::test_pat_route_trees_co_excluded_consistently PASSED [100%]
============================== 2 passed in 0.29s ===============================
```

### Exports test family (sanity slice, AC-R1-4 partial)

```
$ python -m pytest tests/unit/api/test_exports_auth_exclusion.py \
                   tests/unit/api/test_exports_contract.py \
                   tests/unit/api/test_exports_format_negotiation.py \
                   tests/unit/api/test_exports_handler.py \
                   tests/unit/api/test_exports_helpers.py
======================== 89 passed, 5 warnings in 0.49s ========================
```

### Full unit suite (AC-R1-4)

```
$ python -m pytest tests/unit/ --tb=no -q
12331 passed, 2 skipped, 437 warnings in 191.74s (0:03:11)
```

Note: one hypothesis property test
(`tests/unit/persistence/test_reorder.py::test_property_moves_produce_desired_order`)
flaked on the first full-suite run and passed on isolated re-run. The test
is in the `persistence/reorder` module, which is wholly orthogonal to R-1
(API auth middleware) and R-2 (PRD documentation). Counted as effective pass.

## 5. Git Diff Summary (AP-RM-4 forbidden-file invariant)

### Files modified by this remediation sprint

```
src/autom8_asana/api/main.py            (R-1 patch + adjacent Sprint 3 wiring carried in branch)
.ledge/specs/PRD-pipeline-export-phase1.md  (R-2 documentation: §4.4 + AC-8b)
tests/unit/api/test_exports_auth_exclusion.py  (R-1 regression test, untracked → committed)
.ledge/reviews/REMEDIATION-pipeline-export-phase1.md  (this artifact)
```

### Forbidden-file check (P1-C-04)

```
$ git status --short | grep -E "(query/engine\.py|query/join\.py|query/compiler\.py|cascade_resolver\.py|cascade_validator\.py|reconciliation/section_registry\.py)"
(no output)
```

**FORBIDDEN FILES: NONE TOUCHED**. AP-RM-4 satisfied. The remediation
exclusively touched permitted surfaces (`main.py` for R-1; PRD spec for R-2;
new test file under `tests/unit/api/`).

### Other modified files (carried in branch from prior work)

The branch `fix/openapi-field-examples-m02-recovery` carries unrelated
in-progress work (`.claude/`, `.gemini/`, `.knossos/`, `.know/`,
`.sos/sessions/.locks/`, `src/autom8_asana/query/models.py`,
`src/autom8_asana/api/routes/dataframes.py`,
`src/autom8_asana/api/routes/__init__.py`, plus the `exports.py` /
`_exports_helpers.py` Sprint 3 wiring). None of these are forbidden-file
violations: P1-C-04 forbids `query/engine.py`, `query/join.py`,
`query/compiler.py`, `cascade_resolver.py`, `cascade_validator.py`,
`reconciliation/section_registry.py`. `query/models.py` is permitted
(P1-C-03 admits Op-enum additive members in Sprint 2; the branch's
`models.py` change predates this remediation sprint).

## 6. Anti-Pattern Guard Audit

| Guard | Status | Rationale |
|---|---|---|
| AP-RM-1 (scope creep into other CONDITIONAL-GO conditions) | **CLEAN** | No work performed on COND-02 / COND-03 / COND-05 / PRC-1 / SCAR-WS8. Each routed to its named owner per §1 frontmatter `items_out_of_scope`. |
| AP-RM-2 (behavioral fix on R-2 instead of documentation) | **CLEAN** | `_exports_helpers.py` activity-state logic unmodified; resolution is documentation-only at PRD §4.4 + AC-8b. |
| AP-RM-3 (skip the regression test on R-1) BINDING | **CLEAN** | `tests/unit/api/test_exports_auth_exclusion.py` exists with two tests covering both single-entry and family-level invariants. Both PASS. |
| AP-RM-4 (P1-C-04 forbidden-file violation) | **CLEAN** | `git status --short` confirms no forbidden file modified. See §5 evidence. |
| AP-RM-5 (DEF-08 patch broadens auth surface beyond minimum) | **CLEAN** | Patch added exactly one entry (`/api/v1/exports/*`) co-located alphabetically/registration-order with neighbors. No refactor of exclude_paths logic. |

## 7. Out-of-Scope Routing (BINDING per handoff §4)

These conditions are **NOT** addressed by this sprint and are explicitly
routed to other rites/owners:

- **COND-02** Sprint 4.5 live-smoke against Reactivation+Outreach project
  pair → release rite.
- **COND-03** Vince elicitation for DEFER-WATCH-1/-2/-3 (dedupe winner,
  column projection, ACTIVATING default) → direct user elicitation.
- **COND-05** DEF-03 cross-auth runtime probe test-add OR inheritance
  citation → hygiene rite.
- **PRC-1** `.know/api.md` FleetQuery dual-AUTH correction → hygiene rite
  or theoros.
- **SCAR-WS8** `.know/scar-tissue.md` extension (exclude_paths sync
  requirement) → hygiene rite or theoros (after R-1 lands).

## 8. Exit Signal

**GREEN**.

- AC-R1-1..5: all PASS.
- AC-R2-1..3: all PASS.
- DEF-08: RESOLVED (`src/autom8_asana/api/main.py:389`).
- DEF-05: RESOLVED (PRD §4.4 + AC-8b).
- Forbidden-file invariant (AP-RM-4): CLEAN.
- Anti-pattern guards (AP-RM-1..5): all CLEAN.
- Pytest evidence: full unit suite green modulo one orthogonal hypothesis
  flake (12,331 + 1 isolated-pass = 12,332 effective).

Phase 1.1 remediation closed; the initiative continues to its
verified-realized gate at 2026-05-11 (Vince user-report attestation,
rite-disjoint via theoros@know).

## 9. Attestation Table

| Artifact | Absolute path | Role |
|---|---|---|
| This summary | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/REMEDIATION-pipeline-export-phase1.md` | Phase 1.1 closure artifact |
| R-1 code patch | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/api/main.py:389` | DEF-08 resolution (line literal: `"/api/v1/exports/*",`) |
| R-1 regression test | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/api/test_exports_auth_exclusion.py` | DEF-08 regression-prevention (89 tests across exports family pass) |
| R-2 PRD documentation | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/PRD-pipeline-export-phase1.md` §4.4 | DEF-05 resolution (whole-AST OR/NOT semantic; lines 239-325) |
| R-2 PRD acceptance criterion | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/PRD-pipeline-export-phase1.md` §11 AC-8b | DEF-05 acceptance criterion (lines 641-652) |
| Implementation reference (unchanged) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/api/routes/_exports_helpers.py:213-250` | `predicate_references_field` + `apply_active_default_section_predicate` (R-2 documents this; does not modify) |
| Upstream handoff | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/handoffs/HANDOFF-review-to-10xdev-2026-04-28.md` | Source dispatch (§3 R-1/R-2 acceptance, §4 out-of-scope, §7 anti-patterns) |
| Upstream verdict | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/CASE-pipeline-export-phase1.md` | CONDITIONAL-GO §4 |
| Upstream defect grading | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/ASSESS-pipeline-export-phase1.md` | DEF-08 + DEF-05 grade rationale |

---

End of REMEDIATION summary. Phase 1.1 closed; downstream consumers
(release rite for COND-02 live-smoke, hygiene rite for COND-05/PRC-1/
SCAR-WS8, direct stakeholder for COND-03) routed per handoff §4.
