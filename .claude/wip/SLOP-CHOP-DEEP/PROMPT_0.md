# PROMPT_0: SLOP-CHOP-DEEP

**Initiative**: Deep Codebase Quality Gate — autom8y-asana
**Date**: 2026-02-25
**Rite**: slop-chop (CODEBASE complexity)
**Scope**: `src/autom8_asana/` (primary), `tests/` (secondary)
**Non-goals**: See §3 — several items are explicitly deferred with active gate conditions

---

## 1. Initiative Overview

### Objective

Run a full CODEBASE-complexity slop-chop pass over `autom8y-asana` after four major hygiene initiatives have substantially improved the codebase. The goal is NOT to re-litigate resolved items. The goal is to find what remains — NEW findings that the prior passes missed, deferred items that now have cleared conditions, and pattern-level debt that only becomes visible once the surface-level cleanup is done.

The project is in a strong state. This pass should validate that strength, surface any remaining debt, and produce a verdict the team can act on.

### What Changed Since Last Pass

Four major initiatives completed since the last slop-chop (SLOP-CHOP-TESTS-P1, 2026-02-23):

| Initiative | Scope | Result |
|------------|-------|--------|
| ASANA-HYGIENE | 6 workstreams (httpx, params, exceptions, integration, overmock, slop) | COMPLETE — 9 merges, 0 conflicts |
| REM-ASANA-ARCH | Architecture health 68→91/100, 6/13 bidirectional cycles broken | COMPLETE — 12 merges |
| REM-HYGIENE | 12/13 P1 DEFECT findings from SLOP-CHOP-TESTS-P2 | COMPLETE — 7 merges, +629 tests |
| COMPAT-PURGE | 27/29 backward-compat shims eliminated, ~700 LOC removed | COMPLETE — 25 commits |

Current test baseline: **11,655 passed, 42 skipped, 2 xfailed** (COMPAT-PURGE Phase 2 final).

### Complexity Level

**CODEBASE** — full 5-phase pipeline applies:
```
hallucination-hunter --> logic-surgeon --> cruft-cutter --> remedy-smith --> gate-keeper
```

Artifacts produced in sequence:
- `SLOP-CHOP-DEEP/detection-report.md`
- `SLOP-CHOP-DEEP/analysis-report.md`
- `SLOP-CHOP-DEEP/decay-report.md`
- `SLOP-CHOP-DEEP/remedy-plan.md`
- `SLOP-CHOP-DEEP/gate-verdict.md`

---

## 2. Prior Art Register

### 2.1 Items That Are CLOSED — Do Not Reopen

These were consciously reclassified as **intentional design**, not debt. Any specialist that flags one of these as a new finding has either found new evidence (document that evidence explicitly) or is re-litigating a closed decision (escalate to stakeholder rather than proceed).

| Item | Decision | Rationale |
|------|----------|-----------|
| `CustomFieldAccessor strict=False` (DEP-03) | CLOSED — intentional design | 2 active production callers (`task.py:234`, `seeding.py:374`). Legacy lenient mode is active behavior, not dead code. |
| Cache dual-methods in `_defaults/cache.py` + `protocols/cache.py` (DP-02) | CLOSED — dual-purpose API | Both old and versioned method surfaces serve distinct caller types. Not redundancy. |
| Backend `connection_manager` fallback in `s3.py`/`redis.py` (DP-03) | CLOSED — forward scaffolding | Not a backward-compat shim. Runtime DI initialization order risk is active. |
| `HOLDER_KEY_MAP` fallback detection in `facade.py` (DP-05) | CLOSED — intentional resilience | Critical detection path; false negatives break entity classification. Production log analysis required before removal. |
| `D-032` SaveSession (1,853 LOC) decomposition | CLOSED — Coordinator pattern | SaveSession is documented as a 14-collaborator Coordinator, NOT a god object. Do not decompose. |
| ADR-0067 cache divergence (12/14 dimensions) | CLOSED — documented in ADR | Intentional. The divergence is the design. |

### 2.2 Items That Are OPS-GATED — Do Not Touch Without Gate Clearance

These items have explicit external gate conditions that have NOT been cleared. Specialists should flag them as still-open with gate conditions, not attempt remediation.

| Item | Gate Condition | Status |
|------|---------------|--------|
| D-002: POST `/v1/query/{entity_type}` deprecated endpoint | CloudWatch: zero traffic on `deprecated_query_endpoint_used` for 30 days | NOT CLEARED — ops access required |
| D-QUERY | Same as D-002 | NOT CLEARED |
| D-PRELOAD: `api/preload/legacy.py` (613 LOC, ADR-011) | S3 >= 99.9% uptime for 90 days | NOT CLEARED — active degraded-mode fallback |
| DEP-03: `strict=False` callers | Migrate `task.py:234` and `seeding.py:374` to strict mode first | NOT CLEARED |
| HW-02: `key_columns` default (annotated TODO(COMPAT-PURGE)) | Dedicated migration to add explicit args across 26 callers | NOT CLEARED |

### 2.3 Items That Are OPEN AND ELIGIBLE — Prior Art, Not Yet Resolved

These were identified in prior passes and deferred for good reasons, but those reasons may have expired. Specialists should re-evaluate whether the gate condition or deferral rationale still holds.

| Item | Prior Finding | Deferral Reason | Re-Evaluate? |
|------|--------------|-----------------|--------------|
| `D-004`: Error handling v1 per-exception vs v2 dict-mapping | LEDGER | Style inconsistency across 4 route files | YES — check if routes have been touched since |
| `D-005`: DI wiring `Request` vs `RequestId` in 3 route files | LEDGER | Legacy pattern still present in `query.py`, `entity_write.py`, `resolver.py` | YES — PRIORITY item |
| `D-007`: Deprecated DI deps `get_asana_pat()`/`get_asana_client()` still exported | LEDGER | ~90 LOC, dual-mode auth gap | YES — PRIORITY item |
| `D-008`: Webhooks `HTTPException` instead of `raise_api_error` | LEDGER | 3 raise sites, no `request_id` in response | YES — small fix |
| `D-009`: Logging import source inconsistency (5 files use legacy path) | LEDGER | Cosmetic, low priority | LOW — verify still 5 files |
| `D-015`: `UnitExtractor` stub methods always return `None` | LEDGER | Pending team input | YES — data quality risk |
| `D-016`: Commented-out metric imports | LEDGER | 2 lines, trivial | YES — either implement or remove |
| `D-017`: Deprecated aliases (hours model, detection facade, persistence ValidationError, Task hearts fields) | LEDGER | ~150 LOC collective | YES — re-audit consumer counts |
| `D-018`: `entity_write.py` inline `request.app.state` access | LEDGER | DI bypass anti-pattern | YES — PRIORITY item |
| `D-019`: `resolver.py` no DI, inline client construction | LEDGER | ~50 LOC migration | YES — PRIORITY item |
| `D-020`/`D-021`: Side-effect import + barrel `__init__.py` files | LEDGER | Architecture-level, complex | LOW — scope assessment only |
| `D-022a`/`D-022b`: Pipeline hierarchy/assignee in `pipeline.py` | MEMORY | ~1 day, small items | YES — these are ready |
| `D-033`: Pipeline creation duplicated 7-step process | LEDGER | Requires D-022 scaffolding | ASSESS — check D-022a/b status |
| `RS-021`: HierarchyAwareResolver cache miss (fetch_count=4, expected=2) | REM-HYGIENE blocker | Performance investigation needed | YES — still open |
| `LS-009..LS-024`: Copy-paste clusters in tests (16 findings, ~600-800 LOC) | SLOP-CHOP-TESTS-P1 smell | Referred to hygiene rite | YES — eligible now |
| `LS-025..LS-027`: Broad `pytest.raises(Exception)` in tests (16 occurrences) | SLOP-CHOP-TESTS-P1 smell | Referred to hygiene rite | YES — eligible now |
| `H-001`/`H-002`: Phantom httpx patch targets in test_client.py + test_gid_push.py | SLOP-CHOP-TESTS-P1 CONDITIONAL | MANUAL instructions provided but not applied | VERIFY — check if fixed |

### 2.4 Deferred Items Register (For Record Only)

Track these but do NOT attempt resolution in this initiative:

| Item | Trigger to Revisit |
|------|-------------------|
| SI-3: Circular deps (915 deferred imports, 6 cycles) | Production incident or greenfield |
| D-027: Heavy mock usage (540 sites) | Dedicated test architecture initiative |
| D-030: DataServiceClient god object (2,175 LOC) | Dedicated decomposition initiative with WS5-A scaffolding |
| D-034: Broad exception catches (136 instances) | Per-site audit initiative |

---

## 3. Non-Goals (Explicit Scope Exclusions)

The following are out of scope for this initiative and must NOT be included in findings:

1. Items covered by active ADRs (ADR-011 legacy preload, ADR-0067 cache divergence) without new evidence that the ADR basis has changed.
2. Ops-gated items listed in §2.2 without confirmation that the gate has cleared.
3. Architecture-level redesigns requiring multi-sprint planning (D-030 DataServiceClient decomp, SI-3 circular deps). Specialists may NOTE these in findings with referral to debt-triage — they should not attempt remediation plans.
4. Anything explicitly reclassified as intentional design in §2.1.
5. Paradigm shifts or framework migrations. This is a quality gate, not a rewrite proposal.

---

## 4. Discovery Mandate

Prior initiatives addressed known debt. This pass must look BEYOND what is already cataloged.

### What "New Findings" Means Here

The project has evolved significantly. New debt surfaces from:

- **Migration drift**: Code paths updated in one place but not another. REM-ASANA-ARCH moved types, created protocols, extracted utilities. Are all callers updated? Are any now calling into removed/relocated things?
- **Post-refactor orphans**: After COMPAT-PURGE removed 27 shims, are there now callers referencing the shim locations that survived? Are there tests mocking the old locations?
- **Patterns introduced by the initiatives themselves**: New protocols, new shared utilities, new CLI surface — do they carry the same patterns as the rest of the codebase, or did they introduce new ones?
- **Test coverage gaps on new code**: AUTOM8_QUERY added substantial new code. ASANA_DATA added metrics infrastructure. Has the test surface kept pace?
- **Staleness of comments referencing prior initiative names**: Comments referencing "COMPAT-PURGE", "REM-ASANA-ARCH", or "ASANA-HYGIENE" may be ephemeral artifacts if they describe already-completed work.
- **DEP-03 residue**: The `strict=False` parameter is CLOSED, but are there places in the codebase where `strict=False` was added during testing and left in? Those call sites are eligible findings even if the parameter itself is intentional.
- **Surviving legacy comments after shim removal**: When a shim is removed, sometimes comments referencing it survive. COMPAT-PURGE removed 27 shims — are there orphaned comments?

### Discovery Priority Order

Specialists should weight their discovery effort as follows:

1. **Primary**: `src/autom8_asana/` — full tree
2. **Secondary (test quality)**: `tests/unit/` — carry-forward smell items from P1 + new test coverage gaps
3. **Tertiary (new code)**: `query/`, `metrics/`, `dataframes/offline.py` — introduced since last slop-chop

---

## 5. Stakeholder Interview Phase

**This is the most critical protocol in this document.**

The slop-chop specialists WILL encounter findings that are genuinely ambiguous — things that look like debt but might be intentional design, or things that look safe to remove but have non-obvious callers. The prior initiatives demonstrated this: DEP-03 was a SMELL-REPORT finding, but had active production callers that the initial scan missed. Getting this wrong caused a rollback.

### When to Surface for Interview (Not Autonomous Resolution)

Any specialist who encounters any of the following MUST surface the finding for stakeholder triage before including it in a remediation plan:

1. **Caller uncertainty**: "I found 0 internal callers, but I cannot confirm external consumer status"
2. **ADR adjacency**: "This looks like dead code, but I notice an ADR number nearby that I cannot fully evaluate"
3. **Runtime behavior dependency**: "This code path looks unreachable statically, but it may be triggered by runtime conditions I cannot verify"
4. **Performance trade-off ambiguity**: "This looks like a redundant computation, but it might be intentional caching behavior"
5. **Test-only usage**: "This is only used in tests — is the test testing something real, or testing the deprecated thing?"
6. **High blast radius**: Any finding where the estimated consumer count exceeds 10 across src/ and tests/ combined, and the fix is not mechanical

### Interview Protocol

When surfacing for interview, the specialist (or Pythia, if coordinating) should produce a structured question set:

```
INTERVIEW ITEM [ID]
Finding: [Brief description]
Location: [File:line]
Evidence: [What I observed]
My assessment: [What I think is true]
Why I'm uncertain: [What I cannot verify]
Question: [Specific yes/no or choice question for the user]
If YES: [What the specialist will do]
If NO: [What the specialist will do]
```

Pythia should batch interview items (3-5 at a time, maximum) and present them together rather than in one-item-per-turn drip. The user should not have to answer 40 individual questions. Batch by theme.

### Items That Do NOT Require Interview

The following categories are autonomous — specialists may classify and act without escalation:

- Clear phantom imports (the import path demonstrably does not exist)
- Provably dead code (zero callers, no ADR, no runtime trigger, confirmed by grep + file existence check)
- Ephemeral comment artifacts (ticket refs, resolved TODO markers, initiative tags for completed initiatives)
- Copy-paste bloat (parametrization opportunity, no behavioral change)
- Tautological assertions (mock returns the value; assertion checks the value)
- Broad `pytest.raises(Exception)` where the specific exception type is clearly determinable from context

---

## 6. Agent-Specific Scope Guidance

Each specialist operates within its established Exousia (jurisdiction). This section provides project-specific focus areas — it does NOT change the specialist's domain or methodology.

### 6.1 hallucination-hunter — Focus Areas

**Primary focus**: Post-migration phantom references from the four recent initiatives.

- **httpx phantoms** (PRIORITY): Verify H-001 and H-002 from SLOP-CHOP-TESTS-P1 were actually fixed. `tests/unit/clients/data/test_client.py` and `tests/unit/services/test_gid_push.py` had phantom `httpx.AsyncClient` patch targets. If not fixed, these are carry-forward HALLUCINATION findings.
- **autom8y_http migration drift**: ASANA-HYGIENE migrated the codebase from `httpx` to `autom8y_http`. Check for any remaining `httpx` patch targets across all test files. Prior scan covered tests/unit/; check tests/api/ and tests/integration/ if they exist.
- **REM-ASANA-ARCH import drift**: The architecture refactoring moved types to `core/types.py`, `core/string_utils.py`, `core/field_utils.py`, `core/registry.py`, and created protocol files. Are there any remaining imports pointing to the OLD locations? COMPAT-PURGE removed the re-export shims — any remaining old-path imports are now broken references.
- **New module surface**: `query/offline_provider.py`, `query/temporal.py`, `query/saved.py`, `query/cli.py`, `dataframes/offline.py`, `metrics/__main__.py` — these are new files introduced since P1. Verify their imports are real.
- **Dependency manifest consistency**: Verify `pyproject.toml` or `requirements*.txt` — any packages imported in the new modules that aren't declared?

**Do not re-scan**: Items already verified clean in SLOP-CHOP-TESTS-P1 detection report (zero phantom imports, zero orphaned fixtures, zero dead API references in that scope).

### 6.2 logic-surgeon — Focus Areas

**Primary focus**: Behavioral correctness in new code + carry-forward test quality debt.

- **Carry-forward test smells** (PRIORITY): LS-009 through LS-027 from SLOP-CHOP-TESTS-P1 were deferred to hygiene. This is now a hygiene-eligible pass. Re-evaluate these 40 SMELL findings. The copy-paste clusters (LS-009..LS-024, ~600-800 LOC) and broad exception assertions (LS-025..LS-027, 16 occurrences) are primary targets.
- **New test coverage on new code**: `query/` and `metrics/` were built since P1. Are their tests present? Are the tests behavioral (asserting outputs) or vibes-only (asserting call counts)?
- **RS-021 investigation**: `HierarchyAwareResolver.resolve_batch` has a confirmed cache miss — `fetch_count=4` when expected is 2. This was deferred from REM-HYGIENE as needing architect investigation. Logic-surgeon should analyze the cache population logic and whether the miss is a genuine bug or a test assumption error. This is a MANUAL finding either way but needs behavioral analysis.
- **D-015 stub analysis**: `UnitExtractor._extract_vertical_id()` and `_extract_max_pipeline_stage()` always return `None`. Analyze what downstream code does with those `None` values — is it handled, or does it produce silent data quality issues?
- **Security anti-patterns in new CLI surface**: `query/__main__.py` and `metrics/__main__.py` accept user input. Are inputs validated before being passed to query engine? Are there injection risks?
- **Unreviewed-output signals in new modules**: The query and metrics code is entirely new. Check for idioms inconsistent with the established codebase conventions (patterns.md, canonical DI, error handling patterns).

**Do not re-analyze**: The 28 DEFECT findings from SLOP-CHOP-TESTS-P1 were all addressed in REM-HYGIENE. Do not re-open them unless you find evidence of regression.

### 6.3 cruft-cutter — Focus Areas

**Primary focus**: Initiative-era temporal artifacts from the four recent initiatives.

- **Initiative comment artifacts**: Comments referencing "COMPAT-PURGE", "REM-ASANA-ARCH", "ASANA-HYGIENE", "WS-PARAM", "WS-HTTPX", "WS-EXCEPT", "WS-INTEG", "WS-OVERMOCK", "WS-SLOP2", "WS-REEXPORT", "WS-DEAD", "WS-DEPRECATED", "WS-DUALPATH", "WS-BESPOKE" — if these describe completed work, they are ephemeral comment artifacts.
- **TODO(COMPAT-PURGE) annotations**: HW-02 left `TODO(COMPAT-PURGE)` annotations at `key_columns` call sites (26 callers, 4 src + 22 test). These are legitimate carry-forward markers, but verify they're actually present and not already addressed.
- **Post-shim removal orphaned comments**: When COMPAT-PURGE removed shims, did any comments in neighboring code still reference those shims? E.g., "Uses the backward-compat alias from X" where X is now deleted.
- **Stale ADR references in comments**: Comments referencing ADR numbers for decisions that have been superseded. ADR-010 was superseded by ADR-0067. ADR-0067 is active. Any code comment still referencing "ADR-010 cache design" is stale.
- **D-022a/D-022b migration comments**: `pipeline.py` has hierarchy placement and assignee resolution logic that should migrate to `resolve_holder_async` and `AssigneeConfig`. Are there TODO markers referencing this planned migration?
- **Migration-era test skips**: REM-HYGIENE left 8 named skips in workspace switching tests (`WS-WSISO`). Verify they have proper skip reasons. If workspace isolation has since been implemented (check recent commits), they may be stale.
- **LEGACY/DEPRECATED annotation density**: After COMPAT-PURGE, there should be far fewer. Measure what remains. Items like `D-017` (deprecated aliases in hours model, detection facade, etc.) — are any of these surrounded by temporal artifacts?

**Critical boundary**: cruft-cutter does NOT flag code that was always dead, never alive, or has never served a temporal purpose. That is logic-surgeon's lane. Only flag code that OUTLIVED A SPECIFIC CONTEXT.

### 6.4 remedy-smith — Focus Areas

**Classification guidance for this codebase's specifics**:

- **AUTO-eligible categories in this project**: Phantom import corrections (where the correct path is unambiguous), ephemeral comment removal, `TODO(COMPAT-PURGE)` annotation removal (only after gate clearance on HW-02), dead test helper deletion (zero callers confirmed), and parametrization patches for clear copy-paste clusters.
- **ALWAYS MANUAL in this project**: Any change touching `protocols/`, `core/types.py`, `core/registry.py` (high blast radius from REM-ASANA-ARCH work), any change to `lifecycle/engine.py` or `lifecycle/creation.py` (complex state machine), any change to `persistence/session.py` (Coordinator pattern, 14 collaborators), any change to `api/routes/resolver.py` or `api/routes/entity_write.py` (DI bypass — requires understanding of FastAPI lifecycle).
- **Effort calibration**: In this codebase, "small" means one route file and its tests (4-8h). "Medium" means a module boundary with 5-15 files (2-4 days). "Large" means a cross-cutting pattern across multiple modules (1+ sprint). Calibrate to these anchors, not generic estimates.
- **File-scope contracts required**: For any MANUAL fix involving more than 3 files, remedy-smith MUST produce a file-scope contract table specifying which files each workstream touches. This is the proven pattern from COMPAT-PURGE (zero merge conflicts across 30+ merges). Format:

```markdown
### File-Scope Contract: WS-[ID]
| File | Operation | Scope |
|------|-----------|-------|
| src/.../foo.py | Modify: remove deprecated param | lines 34-67 only |
| tests/.../test_foo.py | Modify: update test assertions | lines 112-145 only |
```

### 6.5 gate-keeper — Verdict Guidance

**Verdict thresholds for this initiative**:

- **FAIL**: Any confirmed hallucination (import path that does not exist and was not previously known), any confirmed behavioral bug in new code (logic error with evidence of incorrect output), any security anti-pattern in the new CLI surface.
- **CONDITIONAL-PASS**: Blocking findings that are all AUTO-fixable or have MANUAL instructions with clear remediation path and effort < 1 sprint total.
- **PASS**: No blocking findings. Advisory findings documented.

**Cross-rite referrals to include**:
- Logic errors in architecture-level code (RS-021 cache miss, D-015 stubs) → debt-triage or 10x-dev
- Copy-paste cluster parametrization (LS-009..LS-024) → hygiene if not addressed this pass
- Broad exception assertions (LS-025..LS-027) → hygiene if not addressed this pass
- Security findings in CLI input handling → security rite
- Pattern inconsistencies across route files (D-004..D-008) → hygiene if scope is too large for this pass

**Trend report requirement** (CODEBASE mode): Gate-keeper should include a temporal debt accumulation rate — are we accumulating debt faster than we're resolving it? Given four major initiatives, the expected trend is strongly positive. Confirm this with data.

---

## 7. Evaluation Principles

### What Constitutes Debt vs. Intentional Design

The COMPAT-PURGE initiative produced the most concrete learnings on this distinction. Four items were reclassified from "debt" to "intentional design" mid-execution:

1. **DEP-03 (strict=False)**: Looked like a deprecated parameter. Turned out to have active production callers. Lesson: always verify consumer count before classifying as dead.
2. **DP-02 (cache dual-methods)**: Looked like redundant API surface. The dual surface serves distinct caller types (backward-compat consumers and new consumers). Lesson: dual surface is not always compat debt.
3. **DP-03 (connection manager fallback)**: Looked like a legacy fallback. It is actually forward scaffolding for async DI initialization ordering. Lesson: temporal direction matters — is this "for the old world" or "for a world not yet complete"?
4. **DP-05 (HOLDER_KEY_MAP fallback)**: Looked like dead detection code. It is intentional resilience on a critical production path. Lesson: production log analysis required before removing fallback logic on critical paths.

**The evaluation test**: Before classifying something as debt, ask:
- "Is this code for a context that NO LONGER EXISTS?" (temporal debt — cruft-cutter's lane)
- "Is this code that NEVER served a valid purpose?" (logic error — logic-surgeon's lane)
- "Is this code for a context that EXISTS AND IS ACTIVE?" (intentional design — do not flag)
- "Is this code for a context that DOES NOT YET EXIST?" (forward scaffolding — do not flag unless it's accumulating unreasonably)

### The Reclassification Protocol

If a specialist believes a finding should be reclassified mid-analysis, they should:
1. Note the finding with `[RECLASSIFICATION CANDIDATE]` marker
2. State their original classification and the evidence that changes it
3. State their proposed new classification and why
4. Surface it via the interview protocol if uncertain
5. Do NOT silently skip the finding

---

## 8. Non-Prescriptive Workflow

This PROMPT_0 defines phases and gates. It does NOT define what specialists will find. The specialists discover — the PROMPT_0 only ensures the process is sound.

### Phase Sequence

```
PHASE 0: Pre-Flight (main thread)
  - Capture test baseline: pytest --co -q (count only)
  - Verify no uncommitted changes on main: git status
  - Confirm test baseline is green or note pre-existing failures

PHASE 1: Detection (hallucination-hunter)
  - Scope: src/autom8_asana/ + tests/
  - Artifact: SLOP-CHOP-DEEP/detection-report.md
  - Gate: All files in scope scanned, severity assigned

PHASE 2: Analysis (logic-surgeon)
  - Receives: detection-report.md
  - Scope: src/autom8_asana/ (primary), tests/ (carry-forward smells)
  - Artifact: SLOP-CHOP-DEEP/analysis-report.md
  - Gate: Logic + test quality assessed, bloat map complete

PHASE 3: Decay (cruft-cutter)
  - Receives: detection-report.md + analysis-report.md
  - Scope: Full codebase + initiative artifacts
  - Artifact: SLOP-CHOP-DEEP/decay-report.md
  - Gate: Temporal debt inventory complete, staleness tiers assigned

[INTERVIEW GATE]
  - Pythia batches ambiguous findings from Phases 1-3
  - User resolves interview items (3-5 at a time)
  - Specialists update classifications based on responses
  - Then proceed to Phase 4

PHASE 4: Remediation (remedy-smith)
  - Receives: All prior artifacts + interview resolutions
  - Artifact: SLOP-CHOP-DEEP/remedy-plan.md
  - Requirement: File-scope contracts for any multi-file MANUAL fix
  - Gate: Every finding has remedy or explicit waiver

PHASE 5: Verdict (gate-keeper)
  - Receives: All prior artifacts
  - Artifact: SLOP-CHOP-DEEP/gate-verdict.md
  - Includes: CI JSON, cross-rite referrals, trend report
  - Gate: PASS/FAIL/CONDITIONAL-PASS with evidence chains
```

### Phase Gates

Each phase must satisfy its handoff criteria before the next phase begins. Pythia enforces gates via the consultation protocol. If a specialist's artifact is incomplete (missing severity ratings, missing file paths, missing evidence), Pythia routes back for completion rather than advancing.

Pythia may batch non-blocking advisory findings across phases — findings that clearly belong to one specialist's output but were surfaced by another.

---

## 9. File-Scope Contract Pattern

**This is a hard requirement for any execution workstream following this initiative.**

The file-scope contract pattern produced zero merge conflicts across 30+ merges in three consecutive initiatives. It must be applied to any execution that results from this quality gate.

### Why It Works

When each workstream has an explicit, non-overlapping set of files, parallel execution is safe. When scopes overlap, merge conflicts become likely. The contract forces explicit coordination at the planning stage rather than the conflict stage.

### Template

```markdown
## Workstream: WS-[ID] — [Name]

**Scope contract**: The following files are the EXCLUSIVE domain of this workstream.
No other workstream may modify these files simultaneously.

| File | Change Type | Scope |
|------|-------------|-------|
| `src/autom8_asana/foo/bar.py` | Modify | Remove deprecated param + callers |
| `tests/unit/foo/test_bar.py` | Modify | Update 3 test assertions |
| `src/autom8_asana/foo/protocol.py` | Modify | Remove param from protocol |

**Files explicitly excluded from this workstream** (modified by other workstreams):
- `src/autom8_asana/other_module/` — owned by WS-[X]
```

### When Contracts Are Required

- Any MANUAL fix touching 3+ files
- Any fix touching protocol definitions or shared utilities in `core/`
- Any fix that spans a module boundary (src/ + tests/)
- Any fix affecting route files + their test files simultaneously

---

## 10. Green-to-Green Protocol

### Baseline Capture (Phase 0)

Before any work begins:
```
pytest --co -q  # count tests
pytest -x --tb=no -q  # run to get baseline pass/fail count
```

Record: `{passed}, {failed}, {skipped}, {xfailed}` as the initiative baseline.

### Per-Workstream Verification

Each workstream (following from this quality gate) must:
1. Run tests scoped to the files it touched before merging
2. Confirm zero new failures in that scope
3. Log the pass count delta in the merge log

### Full-Suite Gate

Before the initiative is declared COMPLETE:
1. Full suite run with the SAME options as Phase 0 baseline
2. Pass count must be >= baseline (new tests can only add, not subtract net)
3. Newly deleted tests are acceptable if the corresponding production code was deleted
4. Pre-existing failures are acceptable if unchanged from baseline

**The REM-HYGIENE protocol** is the reference implementation: 7 merges, 0 conflicts, +629 tests, zero regressions. Follow that pattern.

---

## 11. Paradigm Awareness

The following architectural shifts are in progress or relevant. Specialists should flag findings that would interact with these — they may change the appropriate fix approach.

### Active Architectural Directions

| Direction | Status | Implication for This Pass |
|-----------|--------|--------------------------|
| Protocol-first DI (`protocols/*.py`) | IN PROGRESS (REM-ASANA-ARCH broke 6 cycles) | New code should use protocols; code that still uses concrete types in cross-module boundaries is a finding |
| `RequestId` over `Request` in routes | IN PROGRESS (D-005) | Three route files still use `Request`; these are eligible findings |
| Dict-based error handling (`_ERROR_STATUS`) | CANONICAL (patterns.md) | Route files using per-exception `except` blocks are eligible findings |
| `Annotated[T, Depends(...)]` type alias DI | CANONICAL (patterns.md) | Inline `Depends()` in route signatures is a pattern inconsistency |
| Shared utility extraction (`core/`) | IN PROGRESS | Code that duplicates logic already in `core/string_utils.py`, `core/field_utils.py`, `core/registry.py`, `core/types.py` is eligible finding |
| Query CLI offline mode | COMPLETE | `OfflineDataFrameProvider` is the reference for offline usage; any code that tries to re-implement offline loading is redundant |

### Paradigm Shift Signals (Surface But Do Not Implement)

If a specialist finds that a finding would require more than a mechanical fix — that it signals a structural problem requiring architectural redesign — they should:
1. Document the finding with `[PARADIGM-SHIFT]` marker
2. Describe the structural issue in one paragraph
3. Propose the finding as a cross-rite referral to debt-triage or 10x-dev
4. Do NOT attempt the architectural fix in the remedy plan

Examples of paradigm-shift signals:
- "This entire route file's error handling approach requires rewriting 8 handlers atomically"
- "Removing this circular dependency requires extracting a shared interface, which affects 12 files"
- "This stub method's `None` return propagates through 6 downstream transformers in ways I cannot trace without a full data flow analysis"

---

## 12. Anti-Patterns (Explicitly Forbidden)

The following are explicitly forbidden in this initiative's execution:

### Discovery Phase Anti-Patterns

- **Re-opening closed items without new evidence**: Do not flag `strict=False`, cache dual-methods, connection manager fallback, or HOLDER_KEY_MAP as findings. These are CLOSED. If you have NEW evidence that the basis for closure has changed, state it explicitly and surface via interview.
- **ADR violation without ops clearance**: Do not propose removing `api/preload/legacy.py` or the deprecated query endpoint. Both have active ADR coverage and ops-gated conditions.
- **Autonomous resolution of ambiguous items**: If you're not sure, surface it for interview. The rollback cost of a wrong autonomous decision exceeds the interview cost.
- **Blast-radius underestimation**: Do not mark a change as LOW blast radius if it touches shared utilities, protocol definitions, or route DI patterns. These are MEDIUM at minimum.

### Execution Phase Anti-Patterns (For Any Follow-On Workstreams)

- **No file-scope contracts**: If you're touching 3+ files and there's no scope contract, stop. Define the contract first.
- **Force-removing git worktrees**: Before removing any worktree, run `git -C <worktree-path> status` and confirm zero uncommitted/unstaged changes. Get explicit user confirmation before any `git worktree remove`. This rule has no exceptions. Data was lost on 2026-02-24 from violating this.
- **Making changes without test verification**: Every workstream verifies its test scope passes before merging. No exceptions.
- **Scope expansion without explicit approval**: If you discover that a fix requires touching more files than the scope contract covers, stop. Surface the expanded scope for approval. Do not expand autonomously.
- **Prescribing solutions before completing discovery**: Do not propose remediation during the detection or analysis phases. Complete discovery first.

---

## 13. Session Architecture Guidance

### Context Management

This is a CODEBASE-level run. The full pipeline will generate 5 artifacts across multiple agent sessions. Token budget is a real constraint.

**For Pythia**: Keep CONSULTATION_RESPONSE compact (~400-500 tokens). Specialist prompts should front-load file paths and scope boundaries; let agents read context via CLAUDE.md and the artifacts chain. Do not inline large amounts of file content in the prompt.

**For specialists**: Load context progressively. Read CLAUDE.md first for project conventions. Read prior artifacts for context. Do not pre-load the entire codebase — read specific files as discovery demands.

**Natural session boundaries**: After Phase 3 (decay-report complete) is a natural handoff point. The interview gate is also a natural boundary. If context is getting heavy, consider whether a fresh session with the artifact chain (detection-report + analysis-report + decay-report as starting context) is cleaner than continuing.

### Handoff Documents

If a session must hand off to a fresh session, the departing session should produce a brief session-state document:

```markdown
## Session Handoff — [timestamp]
**Completed phases**: [list]
**Artifacts produced**: [paths]
**Interview items resolved**: [summary]
**Interview items pending**: [if any]
**Next phase**: [name]
**Next specialist**: [name]
**Critical context to carry**: [decisions made that affect next phase]
```

---

## 14. Initiative State Tracking

Produce a TRACKER.md at `.claude/wip/SLOP-CHOP-DEEP/TRACKER.md` following the same format as the successful prior initiatives. Minimum fields:

| Field | Purpose |
|-------|---------|
| Phase | Current phase name |
| Specialist | Agent responsible |
| Status | PENDING / IN-PROGRESS / COMPLETE |
| Artifact | Path to artifact |
| Gate | Handoff criteria status |

Update within 5 minutes of any status change. The TRACKER is the initiative's single source of truth for progress.

---

## 15. Quick Reference

### Key Paths

| Purpose | Path |
|---------|------|
| Initiative artifacts | `.claude/wip/SLOP-CHOP-DEEP/` |
| Prior COMPAT-PURGE smell report | `.claude/wip/COMPAT-PURGE/SMELL-REPORT.md` |
| Prior COMPAT-PURGE audit | `.claude/wip/COMPAT-PURGE/AUDIT-REPORT.md` |
| Prior P1 gate verdict | `.claude/wip/SLOP-CHOP-TESTS-P1/phase5-verdict/GATE-VERDICT.md` |
| Prior REM-HYGIENE tracker | `.claude/wip/REM-HYGIENE/TRACKER.md` |
| Debt ledger | `docs/debt/LEDGER-cleanup-modernization.md` |
| Canonical patterns | `docs/guides/patterns.md` |
| Agent prompts | `.claude/agents/` |
| Project memory | `/Users/tomtenuta/.claude/projects/-Users-tomtenuta-Code-autom8y-asana/memory/MEMORY.md` |

### Closed Items Summary (Do Not Reopen)

`strict=False` | cache dual-methods | connection_manager fallback | `HOLDER_KEY_MAP` fallback | SaveSession Coordinator | ADR-0067 cache divergence

### Ops-Gated Summary (Do Not Touch)

D-002 deprecated query endpoint | D-PRELOAD legacy preload (ADR-011) | HW-02 key_columns default (26 callers)

### Test Baseline (as of COMPAT-PURGE Phase 2)

`11,655 passed, 42 skipped, 2 xfailed, 0 failed`
