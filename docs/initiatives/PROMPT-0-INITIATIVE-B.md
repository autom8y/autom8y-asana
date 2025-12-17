# Prompt 0: Initiative B - Error Classification Mixin

> **Initiative ID**: DESIGN-PATTERNS-B
> **Parent**: PROMPT-MINUS-1-DESIGN-PATTERNS.md
> **Complexity**: Quick Win (1 session)
> **Risk**: Low

---

## Mission Objective

Eliminate duplicated error classification logic (`is_retryable`, `recovery_hint`, `retry_after_seconds`) from `SaveError` and `ActionResult` by extracting a `RetryableErrorMixin`.

### Success Criteria

| ID | Criterion | Validation |
|----|-----------|------------|
| SC-B-001 | `RetryableErrorMixin` provides `is_retryable`, `recovery_hint`, `retry_after_seconds` | Unit tests pass |
| SC-B-002 | `HasError` protocol defines the `_get_error()` contract | Protocol is runtime checkable |
| SC-B-003 | `SaveError` uses mixin, maintains all existing behavior | All existing tests pass |
| SC-B-004 | `ActionResult` uses mixin, maintains all existing behavior | All existing tests pass |
| SC-B-005 | Code duplication eliminated | ~150 lines removed |
| SC-B-006 | Zero breaking changes to public API | All tests pass without modification |

---

## Context

### Current State (Duplication)

Both `SaveError` and `ActionResult` in `/src/autom8_asana/persistence/models.py` implement nearly identical:

1. **`is_retryable`** property (~30 lines each):
   - Network error detection (TimeoutError, ConnectionError, OSError)
   - Status code extraction and classification
   - 429 rate limit handling
   - 5xx server error handling
   - 4xx client error rejection

2. **`recovery_hint`** property (~40 lines each):
   - Network error hints
   - Status code-specific hints dictionary
   - Fallback hints for unknown codes

3. **`retry_after_seconds`** property (~5 lines each):
   - Extract `retry_after` attribute from error

4. **`_extract_status_code`** helper (~15 lines each):
   - AsanaError status code extraction
   - Generic `status_code` attribute extraction

**Total duplication**: ~180 lines (90 lines x 2 classes)

### Target State

Single `RetryableErrorMixin` class providing all error classification behavior, with a `HasError` protocol defining the contract for classes that use the mixin.

---

## Deliverables

| ID | Deliverable | Location |
|----|-------------|----------|
| D-B-001 | `RetryableErrorMixin` class | `src/autom8_asana/patterns/error_classification.py` |
| D-B-002 | `HasError` protocol | `src/autom8_asana/patterns/error_classification.py` |
| D-B-003 | Updated `SaveError` | `src/autom8_asana/persistence/models.py` |
| D-B-004 | Updated `ActionResult` | `src/autom8_asana/persistence/models.py` |
| D-B-005 | Mixin unit tests | `tests/unit/patterns/test_error_classification.py` |
| D-B-006 | ADR documenting the pattern | `docs/decisions/ADR-DESIGN-B-001-retryable-error-mixin.md` |

---

## Session Plan

Since this is a quick-win initiative, the workflow is compressed:

### Session 1: Full Implementation (Combined Discovery/Requirements/Architecture/Implementation/Validation)

**Goal**: Complete the mixin extraction in a single session.

**Steps**:
1. Create `patterns/` module directory
2. Implement `HasError` protocol and `RetryableErrorMixin`
3. Update `SaveError` to use mixin
4. Update `ActionResult` to use mixin
5. Verify all existing tests pass
6. Add mixin-specific tests
7. Write ADR documenting the decision

**Quality Gate**: All tests pass, no API changes, duplication eliminated.

---

## Constraints

| Constraint | Rationale |
|------------|-----------|
| No public API changes | Existing code must continue working |
| Existing test assertions unchanged | Proves behavioral equivalence |
| Mixin must be optional | Classes can still override if needed |
| Recovery hint text preserved | Some tests check exact wording |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Slight behavior differences in edge cases | Low | Medium | Run all existing tests without modification |
| MRO issues with dataclass + mixin | Low | Low | Test inheritance order explicitly |
| Import cycle with AsanaError | Low | Low | Keep lazy import pattern |

---

## References

- **Parent Initiative**: [PROMPT-MINUS-1-DESIGN-PATTERNS.md](./PROMPT-MINUS-1-DESIGN-PATTERNS.md)
- **Design Pattern Analysis**: [DESIGN-PATTERN-OPPORTUNITIES.md](../architecture/DESIGN-PATTERN-OPPORTUNITIES.md) - Opportunity 4
- **ADR-0079**: Retryable error classification (original implementation decision)
- **Existing Tests**: `tests/unit/persistence/test_models.py` - TestSaveErrorRetryable, TestActionResultRetryable

---

## Execution Authorization

This initiative is authorized for autonomous execution per the Meta-Initiative guidance:
- Quick-win classification
- Low risk
- Clear deliverables
- No external dependencies

**Proceed with implementation.**
