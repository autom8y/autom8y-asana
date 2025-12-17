# PRD-DESIGN-PATTERNS-D: Async/Sync Method Generator

| Field | Value |
|-------|-------|
| **ID** | PRD-DESIGN-PATTERNS-D |
| **Title** | Async/Sync Method Generator |
| **Status** | Active |
| **Owner** | @orchestrator |
| **Priority** | P1 (High Value) |
| **Created** | 2025-12-16 |

---

## 1. Problem Statement

### 1.1 Current State

The SDK's client methods exhibit massive code duplication. Each method that supports both async and sync variants requires:

- 2 `@overload` declarations for async (raw=False returns Model, raw=True returns dict)
- 1 async implementation with `@error_handler`
- 2 `@overload` declarations for sync
- 1 sync public method wrapper
- 1 `_sync` private method with `@sync_wrapper`

**Example from SectionsClient.get()**: ~48 lines for a single operation.

### 1.2 Impact

| Metric | Current State |
|--------|---------------|
| Lines per method (with raw) | ~71 lines |
| Lines per method (no raw) | ~30 lines |
| Total duplicated lines | ~1,200+ across all clients |
| Maintenance burden | High - 6+ places to update per change |
| Error risk | High - easy to miss one variant |

### 1.3 Root Cause

No abstraction exists to generate async/sync pairs from a single definition while preserving:
- Type safety and IDE autocomplete
- `@overload` signatures for `raw` parameter
- `@error_handler` integration
- `@sync_wrapper` behavior

---

## 2. Requirements

### 2.1 Functional Requirements

#### FR-ASYNCGEN-001: Single Definition, Dual Access
The decorator SHALL generate both async and sync methods from a single async implementation.

**Acceptance Criteria:**
- Developer writes ONE async method definition
- Both `method_async()` and `method()` are accessible
- Behavior is identical to current manual pattern

#### FR-ASYNCGEN-002: Type Signature Preservation
The decorator SHALL preserve full type signatures for IDE support.

**Acceptance Criteria:**
- Return types correctly inferred
- Parameter types correctly inferred
- IDE autocomplete works for both async and sync variants
- mypy passes without errors

#### FR-ASYNCGEN-003: Overload Support for Raw Parameter
The decorator SHALL support methods with `raw: bool` parameter that changes return type.

**Acceptance Criteria:**
- `raw=False` (default) returns typed Model
- `raw=True` returns `dict[str, Any]`
- IDE shows correct overload based on literal type of `raw`

#### FR-ASYNCGEN-004: Error Handler Integration
The decorator SHALL integrate with `@error_handler` for observability.

**Acceptance Criteria:**
- Async method wrapped with error handling
- Error context preserved
- Logging/metrics work correctly

#### FR-ASYNCGEN-005: Sync Context Detection
The decorator SHALL fail fast when sync variant called from async context.

**Acceptance Criteria:**
- Raises `SyncInAsyncContextError` per ADR-0002
- Error message directs to async variant
- No resource leaks

### 2.2 Non-Functional Requirements

#### NFR-ASYNCGEN-001: Zero Runtime Overhead
The decorator SHALL not add measurable overhead beyond current implementation.

#### NFR-ASYNCGEN-002: Backward Compatibility
The decorator SHALL produce methods with identical signatures to existing hand-written methods.

#### NFR-ASYNCGEN-003: Incremental Migration
Clients SHALL be migratable one method at a time without breaking changes.

---

## 3. Scope

### 3.1 In Scope

- `@async_method` decorator implementation
- Type stubs or `@overload` generation for IDE support
- Integration with existing `@error_handler`
- Migration of SectionsClient as proof of concept
- Migration guide for remaining clients

### 3.2 Out of Scope

- Automatic migration of all clients (manual migration per client)
- PageIterator methods (different pattern - returns iterator, not awaitable)
- Changes to `@error_handler` or `@sync_wrapper` internals
- Breaking API changes to existing method signatures

---

## 4. Success Criteria

| Criteria | Target |
|----------|--------|
| Lines of code reduction per method | >50% |
| Type safety | 100% mypy compliance |
| IDE support | Autocomplete works for all variants |
| Test coverage | 100% for decorator logic |
| SectionsClient migration | Complete with no behavior change |

---

## 5. Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| typing module | Available | Required for overload support |
| functools | Available | Required for wraps |
| asyncio | Available | Required for sync detection |
| @error_handler | Exists | Must integrate seamlessly |
| @sync_wrapper | Exists | May be replaced or reused |

---

## 6. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| IDE autocomplete breaks | Medium | High | Extensive testing with VSCode/PyCharm |
| mypy errors | Medium | High | Type stub approach with explicit overloads |
| Runtime overhead | Low | Medium | Benchmark before/after |
| Subtle behavior differences | Medium | High | Comprehensive test coverage |

---

## 7. References

- Meta-Initiative: PROMPT-MINUS-1-DESIGN-PATTERNS.md (Initiative D)
- ADR-0002: Fail-fast async context detection
- TDD-DESIGN-PATTERNS-D: Technical design (to be created)
