# WS-QW: Quick Wins Sprint

**Objective**: Verify two Lambda bootstrap guards, document lifecycle canonical status
in code, and extract three duplicated helper methods to shared utilities.

**Rite**: hygiene
**Complexity**: PATCH
**Recommendations**: R-001, R-002, R-003, R-007
**Preconditions**: None (Phase 0 -- no dependencies)
**Estimated Effort**: 3-6 hours (single session)

---

## R-001: Verify conversation_audit.py Bootstrap Guard (15 min)

**Resolves**: U-003 (bootstrap guard status)
**Evidence**: ARCHITECTURE-REPORT.md Section 4, R-001; ARCHITECTURE-ASSESSMENT.md Risk 5

### Steps

1. Read `src/autom8_asana/lambda_handlers/conversation_audit.py`
2. Search for `import autom8_asana.models.business` or `_ensure_bootstrap()` or
   equivalent bootstrap call at module top level (not inside handler function)
3. **If present**: Mark R-001 DONE. Update `.claude/wip/ENTRY-POINT-AUDIT.md`
   to confirm guard verified.
4. **If absent**: Add bootstrap guard at module level:
   ```python
   import autom8_asana.models.business  # noqa: F401  # bootstrap entity detection
   ```
5. Run: `pytest tests/unit/lambda_handlers/ -k conversation_audit`

### Green-to-Green Gate
- All existing conversation_audit tests pass
- Handler can initialize without prior bootstrap (add assertion test if missing)

---

## R-007: Verify cloudwatch.py Bootstrap Status (15 min)

**Resolves**: U-007 (cloudwatch handler purpose and bootstrap)
**Evidence**: ARCHITECTURE-REPORT.md Section 4, R-007; TOPOLOGY-INVENTORY.md Section 3.2

### Steps

1. Read `src/autom8_asana/lambda_handlers/cloudwatch.py`
2. Determine: (a) what CloudWatch event it handles, (b) whether it imports from
   `models.business` or calls entity detection
3. **If it uses entity detection**: Add bootstrap guard identical to cache_warmer
4. **If no entity detection**: Document as "no bootstrap required"
5. Update `.claude/wip/ENTRY-POINT-AUDIT.md` with findings

### Green-to-Green Gate
- If modified, all cloudwatch handler tests pass
- Entry-point audit document updated with complete Lambda coverage

---

## R-003: Document Lifecycle Canonical Status in Code (30-60 min)

**Evidence**: ARCHITECTURE-REPORT.md Section 4, R-003; ARCHITECTURE-ASSESSMENT.md Gap 6

### Steps

1. Add module docstring to `src/autom8_asana/lifecycle/__init__.py`:
   ```
   Canonical pipeline engine for CRM/Process lifecycle transitions.
   New pipeline features belong here. For the legacy automation path
   retained for specific scenarios, see automation/pipeline.py.
   ```
2. Add notice to top of `src/autom8_asana/automation/pipeline.py`:
   ```
   # LEGACY: This pipeline handles automation-specific conversion scenarios.
   # For new lifecycle features, use lifecycle/creation.py.
   # See D-022 closure in docs/debt/LEDGER-cleanup-modernization.md.
   ```
3. If `docs/guides/patterns.md` exists and is maintained, add a "Pipeline
   Selection" entry referencing lifecycle as canonical.
4. Run: `pytest tests/unit/lifecycle/ tests/unit/automation/ -x`

### Green-to-Green Gate
- No functional code changed -- docstrings and comments only
- All lifecycle and automation tests still pass

---

## R-002: Extract 3 Duplicated Helpers to core/creation.py (2-4 hrs)

**Evidence**: ARCHITECTURE-REPORT.md Section 4, R-002; ARCHITECTURE-ASSESSMENT.md AP-5

### Steps

1. Read `src/autom8_asana/lifecycle/creation.py` -- locate:
   - `_extract_user_gid()` (lines ~700-706)
   - `_extract_first_rep()` (lines ~712-719)
   - `_resolve_assignee_gid()` (lines ~601-647)
2. Read `src/autom8_asana/automation/pipeline.py` -- locate equivalent methods:
   - `_extract_user_gid()` (lines ~730-742)
   - `_extract_first_rep()` (lines ~744-756)
   - `_resolve_assignee_gid()` (lines ~612-668)
3. Confirm they are identical or near-identical in logic
4. Add to `src/autom8_asana/core/creation.py` as module-level functions:
   - `extract_user_gid(task_data: dict) -> str | None`
   - `extract_first_rep(task_data: dict) -> str | None`
   - `resolve_assignee_gid(...) -> str | None`
5. Replace private methods in both files with calls to shared functions
6. Run: `pytest tests/unit/lifecycle/ tests/unit/automation/ tests/unit/core/ -x`
7. Run: `pytest tests/integration/ -x` (broader check for callers)

### Do NOT
- Touch the seeding strategy (FieldSeeder vs AutoCascadeSeeder)
- Modify the 7-step creation flow structure
- Change the method signatures beyond removing `self`

### Green-to-Green Gate
- `pytest tests/` full suite passes (10,552+ tests)
- No new deferred imports introduced
- Both pipelines produce identical output for shared helper calls

---

## Definition of Done

- [ ] R-001: conversation_audit.py bootstrap guard verified or added
- [ ] R-007: cloudwatch.py bootstrap status documented
- [ ] R-003: Lifecycle canonical status documented in code (docstrings)
- [ ] R-002: 3 helper methods extracted to core/creation.py
- [ ] Entry-point audit updated with complete Lambda coverage
- [ ] Full test suite green
- [ ] MEMORY.md updated with "WS-QW Quick Wins: DONE [date]"
