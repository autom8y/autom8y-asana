# Sprint C: Insights Export Structural Improvements

**Initiative**: Structural refactoring of the insights export pipeline (3 findings from prior review)
**Rite**: 10x-dev (requirements-analyst -> architect -> principal-engineer -> qa-adversary)
**Codebase**: ~120K LOC async Python, FastAPI, ~11,100+ tests
**Entry**: requirements-analyst (interview phase to surface design decisions before implementation)
**Prior work**: Sprint A+B shipped 10 quick-win + robustness fixes (commit `5092d2d`). 347 workflow tests passing, mypy clean.

---

## 1. Background

The insights export pipeline generates HTML reports by fetching 12 tables of business data
from the autom8y-data service, formatting them, and uploading to Asana as attachments. An
architectural review (`.claude/wip/SPIKE-INSIGHTS-CONSUMER/EXPORT-FLOW-REVIEW.md`) produced
17 findings. Sprints A and B addressed 10 of them. Three structural findings remain.

### Source Review

The full review with all 17 findings, severity rationale, and recommended sprint plan:
```
Read(".claude/wip/SPIKE-INSIGHTS-CONSUMER/EXPORT-FLOW-REVIEW.md")
```

### Codebase Knowledge

Load before making any code modifications:
```
Read(".know/architecture.md")    -- package structure, layers, entry points
Read(".know/conventions.md")     -- error handling, file organization, naming
```

---

## 2. The Three Findings

### F-03: `_fetch_all_tables` + `_fetch_table` Is a Routing Monolith (P2 STRUCTURAL)

**File**: `src/autom8_asana/automation/workflows/insights_export.py`
**Lines**: ~717-964

`_fetch_all_tables` manually constructs 12 `_fetch_table` calls, each with a different
combination of keyword arguments. `_fetch_table` then uses a 4-branch if/elif chain to
route to the correct DataServiceClient method based on a `method` string parameter. Adding
a 13th table requires editing both functions and understanding which combination of
parameters applies.

Current shape:
- `_fetch_all_tables`: 130 lines, 12 hand-written `_fetch_table(...)` calls inside `asyncio.gather()`
- `_fetch_table`: 115 lines, 4-way dispatch on `method` param (appointments / leads / reconciliation / default)

The 12 table configurations encode these dimensions:
- Table name (display label)
- Dispatch method (4 distinct API endpoints)
- Factory name (base / ad_questions / assets / business_offers)
- Period (lifetime / quarter / month / week / t30)
- Detail parameters (days, limit, exclude_appointments, window_days, include_unused)

**Review recommendation**: Extract a `TableSpec` frozen dataclass and `TABLE_SPECS` module constant. Replace `_fetch_all_tables` with a loop over specs. Collapse `_fetch_table` dispatch.

**Open design questions** (for interview):
- Should specs be a flat frozen dataclass, a NamedTuple, or typed per dispatch method (e.g., union of `InsightsSpec | AppointmentsSpec | LeadsSpec | ReconciliationSpec`)?
- Should the dispatcher remain a method on the workflow class, or become a standalone function that takes a DataServiceClient?
- Should the gather pattern stay as-is (all 12 concurrent), or should specs declare dependency/ordering constraints for future flexibility?
- How should row_limits interact with the spec -- baked in per table, or applied as an overlay at call time?
- The reconciliation phone-filtering logic (lines ~909-935) is currently inside `_fetch_table`. Should it stay in the dispatcher, move into the spec as a post-processor, or become a separate concern?

### F-04: `compose_report` Adapter Mixes Five Concerns (P2 STRUCTURAL)

**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`
**Lines**: ~749-882

The `compose_report` function iterates TABLE_ORDER and handles:
1. Table result validation (missing / error / empty branching)
2. Reconciliation pending detection (`_is_payment_data_pending`)
3. ASSET TABLE sort + column exclusion
4. Row limit application + truncation detection
5. Period table column filtering

These five concerns are interleaved in a single loop body with nested conditionals. The function
is ~130 lines and its cyclomatic complexity grows with each table-specific behavior.

**Review recommendation**: Extract a `_prepare_display_rows` function that handles per-table
row preparation (sort, filter, limit). Keep `compose_report` as a clean iteration with delegation.

**Open design questions** (for interview):
- Should preparation be a single function with table-name branching, or should each table type register its own prep strategy (mirroring the F-03 declarative approach)?
- The reconciliation pending check currently short-circuits the entire section. Should it be modeled as a validation concern (pre-loop) or a display concern (within prep)?
- `full_rows` (for Copy TSV) must bypass display filtering but still get PII-masked. Where does this concern live in the extracted design?
- Period column filtering currently checks column presence across all rows. Should this move to a schema-level declaration (e.g., `PERIOD_TABLE_DISPLAY_COLUMNS`) or remain dynamic?

### F-07: ResolutionContext Mock Boilerplate Duplicated 31+ Times (P2 TEST GAP / MAINTAINABILITY)

**File**: `tests/unit/automation/workflows/test_insights_export.py`
**Lines**: Throughout (~361-372 pattern repeated)

The following 6-line mock setup block is copy-pasted across 31+ test methods:
```python
with patch("...ResolutionContext") as mock_rc:
    mock_ctx = AsyncMock()
    mock_business = _make_mock_business()
    mock_ctx.business_async = AsyncMock(return_value=mock_business)
    mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)
```

This adds ~200 lines of boilerplate and makes interface changes require updating 31 sites.
The test file self-documents this as SM-008 (deferred).

**Review recommendation**: Extract a `@pytest.fixture` or context manager that provides
a pre-configured ResolutionContext patch.

**Open design questions** (for interview):
- Should the fixture yield the mock_business (so tests can customize business attributes), yield the mock_ctx (for tests that need to configure business_async behavior), or yield both?
- Some tests need to vary business attributes (e.g., missing phone, missing vertical). Should the fixture accept parameters (factory fixture pattern), or should tests patch the returned mock after getting it from the fixture?
- Should the fixture live in the test file's module scope or move to a conftest.py (making it available to future test modules)?
- The `_make_mock_business()` helper already exists. Should the fixture compose with it, or replace it?

---

## 3. Scope Boundaries

### IN SCOPE

- F-03: Declarative table spec extraction from `_fetch_all_tables` + `_fetch_table`
- F-04: Concern extraction from `compose_report`
- F-07: Test fixture consolidation for ResolutionContext mock
- Tests for any new abstractions introduced
- Existing test maintenance (updating tests that break due to structural changes)

### OUT OF SCOPE (Do NOT Touch)

| Item | Reason |
|------|--------|
| F-11 (column_align_class perf) | Sprint D backlog, P3 |
| F-12 (inline CSS/JS extraction) | Sprint D backlog, P3 |
| F-17 (renderer singleton reset) | Sprint D backlog, P3 |
| ResolutionContext itself (src) | Only the test mock is in scope |
| DataServiceClient endpoints | Consumed, not modified |
| HtmlRenderer internals | Called by compose_report but not restructured |
| Other workflow files | File scope is insights_export.py + insights_formatter.py + test file |

### Guardrails

1. **Behavior preservation**: All 12 tables must produce identical output. Byte-for-byte report equality is the gold standard; semantic equivalence with documented delta is acceptable.
2. **Green-to-green**: 347 workflow tests passing before and after. Full test suite baseline maintained.
3. **No new dependencies**: Use stdlib + existing project patterns only.
4. **Atomic commits**: One finding per commit (F-03, F-04, F-07 are independent).
5. **No premature generalization**: Solve for the 12 current tables. Do not design for hypothetical future table types unless the interview surfaces a concrete near-term need.

---

## 4. Key Files

| File | Role | Findings |
|------|------|----------|
| `src/autom8_asana/automation/workflows/insights_export.py` | Export workflow class | F-03 |
| `src/autom8_asana/automation/workflows/insights_formatter.py` | Report composition | F-04 |
| `tests/unit/automation/workflows/test_insights_export.py` | Export workflow tests | F-07 |
| `tests/unit/automation/workflows/test_insights_formatter.py` | Formatter tests | (may need updates for F-04) |
| `src/autom8_asana/clients/data/client.py` | DataServiceClient API surface | (reference only, do not modify) |
| `src/autom8_asana/clients/data/models.py` | InsightsResponse, TableResult models | (reference only) |

---

## 5. Workflow Execution Model

### 5.1 Phase Flow

This initiative uses the 10x-dev rite with requirements-analyst as entry point:

```
[requirements-analyst]   Interview phase: surface design decisions for F-03, F-04, F-07
       |                   Artifact: lightweight PRD with design choices documented
       v
[architect]              Technical design: resolve choices into concrete contracts
       |                   Artifact: TDD with before/after signatures, dataclass shapes
       v
[principal-engineer]     Implementation: execute per TDD, one commit per finding
       |                   Artifact: code changes + tests
       v
[qa-adversary]           Validation: verify behavior preservation, test coverage
       |                   Artifact: QA verdict
```

### 5.2 Interview Phase Guidance

The requirements-analyst interview should surface genuine design decisions, not rubber-stamp
a predetermined approach. The open questions listed under each finding in Section 2 are
starting points, not exhaustive lists.

The interview should:
- Present the current code structure to the user (read relevant line ranges)
- Ask 2-3 focused questions at a time
- Listen for constraints the review may not have captured (e.g., planned 13th table, performance requirements, team preferences on frozen dataclass vs NamedTuple)
- Document decisions in the PRD artifact for the architect to consume

The interview should NOT:
- Pre-decide the implementation approach
- Skip questions by assuming the review's recommendation is final
- Ask about things that are clearly the architect's or engineer's domain (e.g., import organization, variable naming)

### 5.3 Estimated Effort

| Finding | Review Estimate | Notes |
|---------|----------------|-------|
| F-03 | 2-3 hours | Largest refactor. Most design surface area. |
| F-04 | 1-2 hours | Extraction pattern is straightforward once F-03 approach is settled. |
| F-07 | 1 hour | Mechanical fixture extraction. Lowest design risk. |
| **Total** | **4-6 hours** | Interview + design add ~1 hour overhead for better outcomes. |

---

## 6. Prior Work References

| Artifact | Location | Relevance |
|----------|----------|-----------|
| Export flow review | `.claude/wip/SPIKE-INSIGHTS-CONSUMER/EXPORT-FLOW-REVIEW.md` | Full findings table, all 17 items |
| Sprint A+B commit | `5092d2d` | 10 findings resolved, current baseline |
| Spike findings | `.claude/wip/SPIKE-INSIGHTS-CONSUMER/FINDINGS.md` | CG-4, OPP-4, COMP-5 evaluation |
| COMP-5 evaluation | `.claude/wip/SPIKE-INSIGHTS-CONSUMER/COMP-5-EVALUATION.md` | Migration context |
| Codebase architecture | `.know/architecture.md` | Package structure, layer boundaries |
| Conventions | `.know/conventions.md` | Error handling, naming, file organization |
| Scar tissue | `.know/scar-tissue.md` | Past regressions (load if touching error paths) |

---

## 7. Anti-Patterns for This Initiative

- **Rubber-stamping the review**: The review's recommendations are starting points. The interview exists to challenge or refine them based on user input.
- **Over-abstracting F-03**: A 12-entry list of frozen dataclasses is simpler than a registry/plugin system. Resist the urge to build an extensible framework for a finite set of tables.
- **Coupling F-03 and F-04**: The table spec (F-03) and the display prep (F-04) are related but should be independently committable. Do not create a single abstraction that spans both unless the interview reveals a strong reason.
- **Breaking the mock contract silently**: F-07 changes test infrastructure. Ensure every test that currently uses the boilerplate pattern is migrated -- no half-migrations where some tests use the fixture and others use the inline pattern.
- **Scope creep into Sprint D**: F-11 (column_align_class perf) and F-12 (CSS/JS extraction) are tempting to bundle. They are out of scope.

---

## 8. Next Commands

### Start the initiative (fresh session)

```
/go
```

When prompted for work description, provide:

```
@.claude/wip/frames/sprint-c-export-structural.md

Sprint C of the insights export structural improvements. Start with the interview phase
(requirements-analyst) to surface design decisions for F-03, F-04, and F-07 before
implementation.
```

### Alternative: Direct interview start (if session is already active)

```
/task Start the Sprint C interview phase for insights export structural improvements.
Read the framing document at .claude/wip/frames/sprint-c-export-structural.md for full
context. Route to requirements-analyst for the interview.
```

### Resume after interview (when PRD is produced)

```
/task Route the Sprint C PRD to architect for technical design. The PRD is at
.claude/wip/SPIKE-INSIGHTS-CONSUMER/PRD-SPRINT-C.md (or wherever the requirements-analyst
placed it).
```
