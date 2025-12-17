# PRD: Architecture Hardening Initiative A - Foundation

## Metadata
- **PRD ID**: PRD-HARDENING-A
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-16
- **Last Updated**: 2025-12-16
- **Stakeholders**: SDK Users, autom8 Integration Team
- **Related PRDs**: None (first in Hardening Sprint)
- **Discovery Document**: `/docs/initiatives/DISCOVERY-HARDENING-A.md`
- **Initiative Prompt**: `/docs/initiatives/PROMPT-0-HARDENING-A-FOUNDATION.md`

---

## Problem Statement

The autom8_asana SDK has accumulated technical debt in its foundation layer that impacts developer experience, debuggability, and API hygiene:

1. **Exception naming conflict**: `ValidationError` conflicts with `pydantic.ValidationError`, causing import shadowing
2. **Missing exports**: Some exceptions are defined but not exported, creating an incomplete public API
3. **Private function leakage**: 3 private functions are incorrectly exported in `__all__`, polluting the API surface
4. **Incomplete type coverage**: 3 stub holders return untyped `Task` children, reducing type safety
5. **Inconsistent logging**: 22+ modules have varying logging patterns with no structured format
6. **No observability hooks**: No protocol exists for integrating telemetry/metrics beyond `@error_handler`

**Impact of Not Solving**:
- Users encounter confusing import conflicts when using Pydantic
- Debugging is harder without consistent, structured logging
- Internal APIs may be accidentally used as public APIs
- Type checkers cannot provide accurate hints for stub holder children
- Production monitoring requires ad-hoc instrumentation

**Target Users**:
- SDK consumers integrating with autom8
- Developers maintaining the SDK
- Operations teams monitoring SDK usage in production

---

## Goals & Success Metrics

### Goals

| Goal | Description |
|------|-------------|
| **G1** | Eliminate exception naming conflicts with common libraries |
| **G2** | Ensure all defined exceptions are properly exported |
| **G3** | Clean API surface with only public functions in `__all__` |
| **G4** | Provide typed models for all holder children |
| **G5** | Establish consistent, structured logging pattern |
| **G6** | Define extensibility point for observability integration |

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Exception import conflicts | 0 | No shadowing when `from pydantic import ValidationError` |
| Private functions in `__all__` | 0 | Grep for `_` prefixed items in all `__all__` lists |
| Stub holders with typed children | 3/3 | DNA, Reconciliation, Videography have typed models |
| Modules with structured logging | 100% of modified | All modules use standard format |
| ObservabilityProtocol defined | Yes | Protocol exists in `protocols/` |

---

## Scope

### In Scope

| Issue # | Description | Scope |
|---------|-------------|-------|
| 9 | Exception hierarchy | Rename ValidationError, add missing exports, document SyncInAsyncContextError |
| 10 | Naming patterns | Document intentional patterns in SDK guide (no code changes) |
| 11 | Private `__all__` | Remove 3 private functions from `models/business/__init__.py` |
| 12 | Stub holders | Create minimal typed models for DNA, Reconciliation, Videography |
| 13 | Logging | Standardize logger naming, add structured logging format |
| 14 | Observability | Define `ObservabilityProtocol` interface |

### Out of Scope

| Item | Reason |
|------|--------|
| Concrete observability implementations | Deferred to future initiative (integration-specific) |
| Changing `SyncInAsyncContextError` inheritance | Intentional per ADR-0002 (only document it) |
| Renaming `TimeoutError` | Intentional SDK-specific exception |
| Full domain modeling for stub holder children | Custom fields unknown; minimal models sufficient |
| Restructuring exception hierarchy | Would break backward compatibility |
| Adding logging to all modules | Only standardize existing logging patterns |

---

## Requirements

### Functional Requirements - Issue 9: Exception Hierarchy

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-EXC-001 | Rename `ValidationError` to `GidValidationError` in `persistence/exceptions.py` | Must | Class renamed; all internal usages updated; type hints correct |
| FR-EXC-002 | Maintain backward compatibility alias for `ValidationError` | Must | `ValidationError = GidValidationError` alias exists with deprecation warning |
| FR-EXC-003 | Export `PositioningConflictError` in `persistence/__init__.py` | Must | Exception importable via `from autom8_asana.persistence import PositioningConflictError` |
| FR-EXC-004 | Export `GidValidationError` in `persistence/__init__.py` | Must | Exception importable via `from autom8_asana.persistence import GidValidationError` |
| FR-EXC-005 | Document `SyncInAsyncContextError` inheritance in SDK guide | Should | SDK guide explains why it inherits from `RuntimeError` not `AsanaError` |
| FR-EXC-006 | Add type alias in root `__init__.py` for `GidValidationError` | Should | Importable via `from autom8_asana import GidValidationError` |

**Traceability**: Discovery Issue 9, Section "Identified Issues" items 2, 4

### Functional Requirements - Issue 10: Naming Documentation

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-NAM-001 | Document list method naming pattern in SDK guide | Should | Explains `list_async()` vs `list_for_*_async()` pattern |
| FR-NAM-002 | Document `get_custom_fields()` semantics in docstring | Should | Docstring clarifies this returns local data, not API fetch |

**Traceability**: Discovery Issue 10, Section "Client Method Naming Audit"

### Functional Requirements - Issue 11: Private `__all__` Cleanup

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-ALL-001 | Remove `_traverse_upward_async` from `models/business/__init__.py` `__all__` | Must | Function not in `__all__`; still importable directly if needed |
| FR-ALL-002 | Remove `_convert_to_typed_entity` from `models/business/__init__.py` `__all__` | Must | Function not in `__all__`; still importable directly if needed |
| FR-ALL-003 | Remove `_is_recoverable` from `models/business/__init__.py` `__all__` | Must | Function not in `__all__`; still importable directly if needed |
| FR-ALL-004 | Verify no other `__init__.py` files export private functions | Must | Grep confirms no `_` prefixed names in any `__all__` |

**Traceability**: Discovery Issue 11, Section "Audit Results"

### Functional Requirements - Issue 12: Stub Holder Typed Models

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-STUB-001 | Create `DNA` model as minimal `BusinessEntity` subclass | Must | Class exists in `models/business/dna.py`; inherits from `BusinessEntity` |
| FR-STUB-002 | Create `Reconciliation` model as minimal `BusinessEntity` subclass | Must | Class exists in `models/business/reconciliation.py`; inherits from `BusinessEntity` |
| FR-STUB-003 | Create `Videography` model as minimal `BusinessEntity` subclass | Must | Class exists in `models/business/videography.py`; inherits from `BusinessEntity` |
| FR-STUB-004 | Update `DNAHolder` to return `list[DNA]` from `children` property | Must | Type annotation and runtime return typed `DNA` instances |
| FR-STUB-005 | Update `ReconciliationsHolder` to return `list[Reconciliation]` | Must | Type annotation and runtime return typed `Reconciliation` instances |
| FR-STUB-006 | Update `VideographyHolder` to return `list[Videography]` | Must | Type annotation and runtime return typed `Videography` instances |
| FR-STUB-007 | Update `CHILD_TYPE` class variable on each updated holder | Must | `CHILD_TYPE` matches the typed model class |
| FR-STUB-008 | Add bidirectional navigation (`_business`, `_holder` refs) to new models | Should | New models have private attributes for parent navigation |
| FR-STUB-009 | Export new models from `models/business/__init__.py` | Must | Models importable via `from autom8_asana.models.business import DNA, Reconciliation, Videography` |
| FR-STUB-010 | Minimal models should NOT define custom field accessors | Must | No `@property` accessors for custom fields (unknown domain) |

**Traceability**: Discovery Issue 12, Section "Stub Holder Inventory"

### Functional Requirements - Issue 13: Logging Standardization

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-LOG-001 | Define standard logger naming convention: `autom8_asana.{module_path}` | Must | Convention documented; new loggers follow pattern |
| FR-LOG-002 | Create `LogContext` dataclass for structured log context | Should | Dataclass with `correlation_id`, `operation`, `entity_gid`, `duration_ms` fields |
| FR-LOG-003 | Update `DefaultLogProvider` to support structured context via `extra` | Should | `debug()`, `info()`, `warning()`, `error()` accept `extra: dict` |
| FR-LOG-004 | Migrate existing inline `logging.getLogger(__name__)` to standard pattern | Should | Existing loggers renamed to `autom8_asana.{module}` pattern |
| FR-LOG-005 | Logging must be zero-cost when disabled | Must | No string formatting unless log level enabled |
| FR-LOG-006 | Document logging configuration in SDK guide | Should | Guide explains how to configure log levels and handlers |

**Traceability**: Discovery Issue 13, Section "Identified Gaps"

### Functional Requirements - Issue 14: Observability Protocol

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-OBS-001 | Define `ObservabilityHook` protocol in `protocols/observability.py` | Must | Protocol class exists with method signatures |
| FR-OBS-002 | Protocol includes `on_request_start` method | Must | `async def on_request_start(self, method: str, path: str, correlation_id: str) -> None` |
| FR-OBS-003 | Protocol includes `on_request_end` method | Must | `async def on_request_end(self, method: str, path: str, status: int, duration_ms: float) -> None` |
| FR-OBS-004 | Protocol includes `on_request_error` method | Must | `async def on_request_error(self, method: str, path: str, error: Exception) -> None` |
| FR-OBS-005 | Protocol includes `on_rate_limit` method | Should | `async def on_rate_limit(self, retry_after_seconds: int) -> None` |
| FR-OBS-006 | Protocol includes `on_circuit_breaker_state_change` method | Should | `async def on_circuit_breaker_state_change(self, old_state: str, new_state: str) -> None` |
| FR-OBS-007 | Protocol includes `on_retry` method | Should | `async def on_retry(self, attempt: int, max_attempts: int, error: Exception) -> None` |
| FR-OBS-008 | Export `ObservabilityHook` from `protocols/__init__.py` | Must | Importable via `from autom8_asana.protocols import ObservabilityHook` |
| FR-OBS-009 | Export `ObservabilityHook` from root `__init__.py` | Should | Importable via `from autom8_asana import ObservabilityHook` |
| FR-OBS-010 | Create `NullObservabilityHook` default implementation | Must | No-op class that satisfies protocol for default usage |
| FR-OBS-011 | Add `observability_hook` parameter to `AsanaClient.__init__` | Should | Optional parameter accepting `ObservabilityHook` instance |
| FR-OBS-012 | Document `ObservabilityHook` usage in SDK guide | Should | Guide shows how to implement and register custom hooks |

**Traceability**: Discovery Issue 14, Section "Proposed Hook Architecture"

---

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-001 | Backward compatibility for exception handling | 100% | Existing `except ValidationError` still works via alias |
| NFR-002 | No new external dependencies | 0 new deps | `pyproject.toml` unchanged except dev deps |
| NFR-003 | Logging zero-cost when disabled | <1% overhead | Benchmark shows negligible impact with logging off |
| NFR-004 | Type checker compatibility | mypy passes | `mypy src/autom8_asana` exits 0 |
| NFR-005 | Test coverage maintained | >=current | No decrease in coverage percentage |

---

## User Stories / Use Cases

### US-001: Import Without Conflicts

**As a** developer using both autom8_asana and Pydantic,
**I want** to import `ValidationError` from Pydantic without SDK conflicts,
**So that** I can use both libraries in the same file without import aliasing.

**Current**: `from autom8_asana.persistence import ValidationError` shadows Pydantic.
**After**: `GidValidationError` is the SDK exception; `ValidationError` alias warns.

### US-002: Catch All SDK Errors

**As a** developer handling SDK errors,
**I want** to catch `AsanaError` for all SDK-generated exceptions,
**So that** I have predictable error handling.

**Note**: `SyncInAsyncContextError` intentionally inherits from `RuntimeError` (per ADR-0002) and will NOT be caught by `except AsanaError`. This is documented.

### US-003: Type-Safe Holder Children

**As a** developer navigating the Business hierarchy,
**I want** `business.dna_holder.children` to return typed `DNA` instances,
**So that** my type checker provides accurate completions and warnings.

**Current**: Returns `list[Task]` (untyped).
**After**: Returns `list[DNA]` (typed, minimal model).

### US-004: Structured Log Filtering

**As an** operations engineer,
**I want** SDK logs to include structured context (correlation_id, entity_gid),
**So that** I can filter and trace requests in log aggregation tools.

**Current**: Logs are unstructured format strings.
**After**: Logs include `extra={}` dict with standard fields.

### US-005: Custom Metrics Integration

**As a** platform team member,
**I want** to plug in our metrics library (e.g., StatsD, Prometheus),
**So that** we can monitor SDK behavior in production dashboards.

**Current**: No hook points exist.
**After**: `ObservabilityHook` protocol allows custom implementations.

---

## Assumptions

| # | Assumption | Basis |
|---|------------|-------|
| A1 | DNA, Reconciliation, Videography entities have no known custom fields | Discovery audit; domain model not defined |
| A2 | Existing code does not rely on `ValidationError` name specifically | Standard practice; rename with alias is safe |
| A3 | `SyncInAsyncContextError` behavior is intentional | ADR-0002 documents the design decision |
| A4 | Structured logging via `extra` dict is sufficient | Standard Python logging pattern |
| A5 | Protocol-based observability is preferred over ABC | Aligns with existing `protocols/` pattern |

---

## Dependencies

| Dependency | Owner | Notes |
|------------|-------|-------|
| ADR-0002 (Async design) | Existing | Documents `SyncInAsyncContextError` inheritance |
| Python `typing.Protocol` | Python stdlib | Used for `ObservabilityHook` |
| `warnings.warn` | Python stdlib | Used for deprecation alias |
| Existing `BusinessEntity` base class | SDK | New stub models inherit from it |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| ~~Rename ValidationError to what?~~ | User | 2025-12-16 | **Resolved**: `GidValidationError` |
| ~~Stub holder strategy?~~ | User | 2025-12-16 | **Resolved**: Create minimal typed models |
| ~~ObservabilityProtocol scope?~~ | User | 2025-12-16 | **Resolved**: Define protocol only, no concrete impl |
| ~~SyncInAsyncContextError change?~~ | User | 2025-12-16 | **Resolved**: Keep as RuntimeError, document |

*All blocking questions resolved per user decisions.*

---

## Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| No breaking changes to public API | Cannot remove `ValidationError` entirely | Provide alias with deprecation warning |
| No new external dependencies | Cannot use structured logging libraries | Use stdlib `logging` with `extra` dict |
| Logging must be zero-cost when disabled | Cannot eagerly format log messages | Use lazy formatting (`%s`) or guards |
| Backward compatibility required | Cannot change exception inheritance | Only add, rename with alias, document |

---

## Implementation Notes

### Exception Rename Strategy

```python
# persistence/exceptions.py
class GidValidationError(SaveOrchestrationError):
    """Raised when entity GID validation fails at track time."""
    pass

# Backward compatibility alias with deprecation
import warnings

def _deprecated_validation_error():
    warnings.warn(
        "ValidationError is deprecated, use GidValidationError instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return GidValidationError

ValidationError = GidValidationError  # Simple alias, warn on access is complex
```

### Minimal Stub Model Pattern

```python
# models/business/dna.py
class DNA(BusinessEntity):
    """DNA entity - child of DNAHolder.

    Minimal typed model. Custom field accessors may be added
    when domain model is defined.
    """

    _dna_holder: "DNAHolder | None" = PrivateAttr(default=None)
    _business: "BusinessEntity | None" = PrivateAttr(default=None)

    @property
    def dna_holder(self) -> "DNAHolder | None":
        """Navigate to parent DNAHolder."""
        return self._dna_holder

    @property
    def business(self) -> "BusinessEntity | None":
        """Navigate to root Business."""
        return self._business
```

### ObservabilityHook Protocol Pattern

```python
# protocols/observability.py
from typing import Protocol

class ObservabilityHook(Protocol):
    """Protocol for observability integration.

    Implement this protocol to receive SDK operation events
    for metrics, tracing, or logging integration.
    """

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        """Called before an HTTP request is made."""
        ...

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        """Called after an HTTP request completes successfully."""
        ...

    # ... additional methods
```

---

## Success Criteria Checklist

- [ ] `from pydantic import ValidationError` works without conflict when SDK imported
- [ ] `from autom8_asana.persistence import GidValidationError` works
- [ ] `from autom8_asana.persistence import PositioningConflictError` works
- [ ] No `_` prefixed names in any `__all__` export
- [ ] `business.dna_holder.children` returns `list[DNA]`
- [ ] `business.reconciliations_holder.children` returns `list[Reconciliation]`
- [ ] `business.videography_holder.children` returns `list[Videography]`
- [ ] `from autom8_asana.protocols import ObservabilityHook` works
- [ ] `mypy src/autom8_asana` passes
- [ ] Existing tests continue to pass
- [ ] SDK guide documents `SyncInAsyncContextError` inheritance
- [ ] SDK guide documents list method naming patterns

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Requirements Analyst | Initial draft based on Discovery findings and user decisions |

---

## Appendix A: Traceability Matrix

| Requirement ID | Discovery Section | Issue # |
|----------------|-------------------|---------|
| FR-EXC-001 | Issue 9: Identified Issues #2 | 9 |
| FR-EXC-002 | Issue 9: Proposed Corrections | 9 |
| FR-EXC-003 | Issue 9: Identified Issues #4 | 9 |
| FR-EXC-004 | Issue 9: Identified Issues #4 | 9 |
| FR-EXC-005 | Issue 9: Proposed Corrections | 9 |
| FR-EXC-006 | Issue 9: Proposed Corrections | 9 |
| FR-NAM-001 | Issue 10: Client Method Naming Audit | 10 |
| FR-NAM-002 | Issue 10: Client Method Naming Audit | 10 |
| FR-ALL-001 | Issue 11: Audit Results | 11 |
| FR-ALL-002 | Issue 11: Audit Results | 11 |
| FR-ALL-003 | Issue 11: Audit Results | 11 |
| FR-ALL-004 | Issue 11: Audit Results | 11 |
| FR-STUB-001 | Issue 12: Stub Holder Inventory | 12 |
| FR-STUB-002 | Issue 12: Stub Holder Inventory | 12 |
| FR-STUB-003 | Issue 12: Stub Holder Inventory | 12 |
| FR-STUB-004 | Issue 12: Stub Holder Inventory | 12 |
| FR-STUB-005 | Issue 12: Stub Holder Inventory | 12 |
| FR-STUB-006 | Issue 12: Stub Holder Inventory | 12 |
| FR-STUB-007 | Issue 12: Incompleteness Details | 12 |
| FR-STUB-008 | Issue 12: Missing Functionality #4 | 12 |
| FR-STUB-009 | Issue 12: Stub Holder Inventory | 12 |
| FR-STUB-010 | Scope: Out of Scope | 12 |
| FR-LOG-001 | Issue 13: Identified Gaps #4 | 13 |
| FR-LOG-002 | Issue 13: Proposed Improvements | 13 |
| FR-LOG-003 | Issue 13: Proposed Improvements | 13 |
| FR-LOG-004 | Issue 13: Identified Gaps #4 | 13 |
| FR-LOG-005 | Constraint: Performance | 13 |
| FR-LOG-006 | Issue 13: Proposed Improvements | 13 |
| FR-OBS-001 | Issue 14: Proposed Hook Architecture | 14 |
| FR-OBS-002 | Issue 14: Proposed Hook Architecture | 14 |
| FR-OBS-003 | Issue 14: Proposed Hook Architecture | 14 |
| FR-OBS-004 | Issue 14: Proposed Hook Architecture | 14 |
| FR-OBS-005 | Issue 14: Missing Observability Hooks | 14 |
| FR-OBS-006 | Issue 14: Missing Observability Hooks | 14 |
| FR-OBS-007 | Issue 14: Missing Observability Hooks | 14 |
| FR-OBS-008 | Issue 14: Proposed Hook Architecture | 14 |
| FR-OBS-009 | Issue 14: Proposed Hook Architecture | 14 |
| FR-OBS-010 | Implementation pattern | 14 |
| FR-OBS-011 | Issue 14: Integration Points | 14 |
| FR-OBS-012 | Documentation requirement | 14 |

---

## Appendix B: Files to Modify

| File | Changes |
|------|---------|
| `src/autom8_asana/persistence/exceptions.py` | Rename ValidationError to GidValidationError |
| `src/autom8_asana/persistence/__init__.py` | Add PositioningConflictError, GidValidationError exports |
| `src/autom8_asana/__init__.py` | Add GidValidationError export (optional) |
| `src/autom8_asana/models/business/__init__.py` | Remove private functions from `__all__`; add new model exports |
| `src/autom8_asana/models/business/dna.py` | **NEW** - DNA minimal model |
| `src/autom8_asana/models/business/reconciliation.py` | **NEW** - Reconciliation minimal model |
| `src/autom8_asana/models/business/videography.py` | **NEW** - Videography minimal model |
| `src/autom8_asana/models/business/business.py` | Update DNAHolder, ReconciliationsHolder, VideographyHolder |
| `src/autom8_asana/protocols/observability.py` | **NEW** - ObservabilityHook protocol |
| `src/autom8_asana/protocols/__init__.py` | Add ObservabilityHook export |
| `src/autom8_asana/_defaults/observability.py` | **NEW** - NullObservabilityHook default |
| `src/autom8_asana/_defaults/__init__.py` | Add NullObservabilityHook export |
| SDK Guide (location TBD) | Document SyncInAsyncContextError, list methods, ObservabilityHook |
