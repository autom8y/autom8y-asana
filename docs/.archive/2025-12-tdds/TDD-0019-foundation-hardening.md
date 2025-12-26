# TDD: Architecture Hardening Initiative A - Foundation

## Metadata
- **TDD ID**: TDD-HARDENING-A
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-16
- **Last Updated**: 2025-12-16
- **PRD Reference**: [PRD-HARDENING-A](/docs/requirements/PRD-HARDENING-A.md)
- **Related TDDs**: None
- **Related ADRs**:
  - [ADR-HARDENING-A-001](/docs/decisions/ADR-HARDENING-A-001-exception-rename-strategy.md) - Exception Rename Strategy
  - [ADR-HARDENING-A-002](/docs/decisions/ADR-HARDENING-A-002-observability-protocol-design.md) - ObservabilityHook Protocol Design
  - [ADR-HARDENING-A-003](/docs/decisions/ADR-HARDENING-A-003-logging-standardization.md) - Logging Standardization
  - [ADR-HARDENING-A-004](/docs/decisions/ADR-HARDENING-A-004-minimal-stub-model-pattern.md) - Minimal Stub Model Pattern

## Overview

This TDD defines the technical design for the Hardening-A Foundation initiative, addressing 6 low-severity issues to establish clean SDK foundations: exception hierarchy fixes, API surface cleanup, stub holder typing, logging standardization, and observability protocol definition. All changes maintain backward compatibility with zero new external dependencies.

## Requirements Summary

Per PRD-HARDENING-A, the initiative addresses:

| Issue | Goal | Requirements |
|-------|------|--------------|
| **Exception Hierarchy** | Eliminate naming conflicts, export all exceptions | FR-EXC-001 through FR-EXC-006 |
| **API Surface** | Remove private functions from `__all__` | FR-ALL-001 through FR-ALL-004 |
| **Stub Holders** | Type stub holder children | FR-STUB-001 through FR-STUB-010 |
| **Logging** | Standardize naming and format | FR-LOG-001 through FR-LOG-006 |
| **Observability** | Define protocol for telemetry integration | FR-OBS-001 through FR-OBS-012 |

Constraints:
- No breaking changes to public API
- Zero new external dependencies
- Backward compatibility required (NFR-001 through NFR-005)

## System Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            autom8_asana SDK                              │
│                                                                          │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────┐    │
│  │ exceptions/ │     │ protocols/  │     │    models/business/     │    │
│  │             │     │             │     │                          │    │
│  │ GidValid...◄──────│ Observ...   │     │ DNA, Reconciliation,    │    │
│  │ (renamed)   │     │ Hook        │     │ Videography (new)       │    │
│  │             │     │ (new)       │     │                          │    │
│  └─────────────┘     └──────┬──────┘     └───────────┬──────────────┘    │
│         │                   │                        │                   │
│         │                   │                        │                   │
│  ┌──────▼──────┐     ┌──────▼──────┐     ┌──────────▼──────────────┐    │
│  │ persistence/│     │ transport/  │     │    business.py          │    │
│  │             │     │             │     │                          │    │
│  │ __init__.py │     │ http.py     │     │ DNAHolder (typed),       │    │
│  │ (exports)   │     │ retry.py    │     │ ReconciliationsHolder,   │    │
│  │             │     │ circuit.py  │     │ VideographyHolder        │    │
│  └─────────────┘     └─────────────┘     └──────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                        Logging (standardized)                        │ │
│  │  autom8_asana.{module} pattern, zero-cost, structured context        │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │     User Application          │
                    │                               │
                    │ - from autom8_asana import    │
                    │   GidValidationError          │
                    │ - Custom ObservabilityHook    │
                    │ - logging.getLogger()         │
                    │   .setLevel(DEBUG)            │
                    └──────────────────────────────┘
```

## Design

### Component Architecture

| Component | Responsibility | Files |
|-----------|----------------|-------|
| **Exception Hierarchy** | Rename ValidationError, add exports | `persistence/exceptions.py`, `persistence/__init__.py` |
| **API Surface** | Remove private exports | `models/business/__init__.py` |
| **Stub Models** | Minimal typed models for DNA, Reconciliation, Videography | `models/business/dna.py`, `reconciliation.py`, `videography.py` |
| **Holder Updates** | Update CHILD_TYPE and children return types | `models/business/business.py` |
| **ObservabilityHook** | Protocol for telemetry integration | `protocols/observability.py` |
| **NullObservabilityHook** | Default no-op implementation | `_defaults/observability.py` |
| **LogContext** | Structured logging context | `observability/context.py` (new) |
| **DefaultLogProvider** | Enhanced with `extra` support | `_defaults/log.py` |

### Component 1: Exception Hierarchy (FR-EXC-*)

Per [ADR-HARDENING-A-001](/docs/decisions/ADR-HARDENING-A-001-exception-rename-strategy.md):

```
persistence/exceptions.py
├── SaveOrchestrationError (existing base)
├── GidValidationError (FR-EXC-001: renamed from ValidationError)
│   └── ValidationError (deprecated alias with metaclass warning)
├── PositioningConflictError (existing, needs export)
└── (other exceptions unchanged)

persistence/__init__.py
└── __all__ += ["GidValidationError", "PositioningConflictError"]  # FR-EXC-003, FR-EXC-004

__init__.py (root)
└── __all__ += ["GidValidationError"]  # FR-EXC-006
```

**Implementation Details:**

```python
# persistence/exceptions.py

class GidValidationError(SaveOrchestrationError):
    """Raised when entity GID validation fails at track time.

    Per ADR-0049: Fail-fast on invalid GIDs.
    Per FR-VAL-001: Validate GID format at track() time.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# Backward compatibility with deprecation warning
class _DeprecatedValidationErrorMeta(type):
    """Metaclass that warns on ValidationError access."""

    _warned = False  # Warn only once per session

    def __instancecheck__(cls, instance: object) -> bool:
        cls._warn()
        return isinstance(instance, GidValidationError)

    def __subclasscheck__(cls, subclass: type) -> bool:
        cls._warn()
        return issubclass(subclass, GidValidationError)

    @classmethod
    def _warn(cls) -> None:
        if not cls._warned:
            import warnings
            warnings.warn(
                "ValidationError is deprecated. Use GidValidationError instead. "
                "ValidationError will be removed in v2.0.",
                DeprecationWarning,
                stacklevel=4,
            )
            cls._warned = True


class ValidationError(GidValidationError, metaclass=_DeprecatedValidationErrorMeta):
    """Deprecated alias for GidValidationError.

    .. deprecated:: 1.x
        Use :class:`GidValidationError` instead.
    """
    pass
```

### Component 2: API Surface Cleanup (FR-ALL-*)

Per PRD FR-ALL-001 through FR-ALL-004:

```python
# models/business/__init__.py
# REMOVE from __all__:
# - "_traverse_upward_async"  (FR-ALL-001)
# - "_convert_to_typed_entity" (FR-ALL-002)
# - "_is_recoverable"         (FR-ALL-003)

# These functions remain in the module for internal use,
# but are not part of the public API.
```

**Verification Script:**

```python
# FR-ALL-004: Verify no private functions in any __all__
import ast
from pathlib import Path

def audit_all_exports(src_dir: Path) -> list[str]:
    violations = []
    for init_file in src_dir.rglob("__init__.py"):
        tree = ast.parse(init_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if getattr(target, "id", None) == "__all__":
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and elt.value.startswith("_"):
                                    violations.append(f"{init_file}: {elt.value}")
    return violations
```

### Component 3: Stub Models (FR-STUB-*)

Per [ADR-HARDENING-A-004](/docs/decisions/ADR-HARDENING-A-004-minimal-stub-model-pattern.md):

**New Files:**

```
src/autom8_asana/models/business/
├── dna.py              # FR-STUB-001: DNA minimal model
├── reconciliation.py   # FR-STUB-002: Reconciliation minimal model
└── videography.py      # FR-STUB-003: Videography minimal model
```

**DNA Model (FR-STUB-001):**

```python
# models/business/dna.py
"""DNA entity - minimal typed model for DNAHolder children."""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business, DNAHolder


class DNA(BusinessEntity):
    """DNA entity - child of DNAHolder.

    Minimal typed model providing type-safe children and bidirectional navigation.
    Custom field accessors intentionally omitted per FR-STUB-010.
    """

    _dna_holder: DNAHolder | None = PrivateAttr(default=None)
    _business: Business | None = PrivateAttr(default=None)

    @property
    def dna_holder(self) -> DNAHolder | None:
        """Navigate to parent DNAHolder."""
        return self._dna_holder

    @property
    def business(self) -> Business | None:
        """Navigate to root Business."""
        return self._business
```

**Holder Updates (FR-STUB-004 through FR-STUB-007):**

```python
# models/business/business.py (updated)
from autom8_asana.models.business.dna import DNA
from autom8_asana.models.business.reconciliation import Reconciliation
from autom8_asana.models.business.videography import Videography


class DNAHolder(Task, HolderMixin[DNA]):
    """Holder task containing DNA children."""

    CHILD_TYPE: ClassVar[type[DNA]] = DNA  # FR-STUB-007
    _children: list[DNA] = PrivateAttr(default_factory=list)
    _business: BusinessEntity | None = PrivateAttr(default=None)

    @property
    def children(self) -> list[DNA]:  # FR-STUB-004
        """All DNA children (typed)."""
        return self._children

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate DNA children with bidirectional refs (FR-STUB-008)."""
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )
        self._children = []
        for task in sorted_tasks:
            dna = DNA.model_validate(task.model_dump())
            dna._dna_holder = self
            dna._business = self._business
            self._children.append(dna)

# Similar updates for ReconciliationsHolder and VideographyHolder
```

**Export Updates (FR-STUB-009):**

```python
# models/business/__init__.py
from autom8_asana.models.business.dna import DNA
from autom8_asana.models.business.reconciliation import Reconciliation
from autom8_asana.models.business.videography import Videography

__all__ = [
    # ... existing exports ...
    "DNA",
    "Reconciliation",
    "Videography",
]
```

### Component 4: Logging Standardization (FR-LOG-*)

Per [ADR-HARDENING-A-003](/docs/decisions/ADR-HARDENING-A-003-logging-standardization.md):

**LogContext Dataclass (FR-LOG-002):**

```python
# observability/context.py (new file)
"""Structured logging context for SDK operations."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class LogContext:
    """Structured logging context.

    Per FR-LOG-002: Provides standard fields for structured logging.

    Usage:
        ctx = LogContext(correlation_id="abc123", operation="track")
        logger.info("Processing", extra=ctx.to_dict())
    """

    correlation_id: str | None = None
    operation: str | None = None
    entity_gid: str | None = None
    entity_type: str | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for logging extra parameter."""
        return {k: v for k, v in asdict(self).items() if v is not None}
```

**DefaultLogProvider Enhancement (FR-LOG-003):**

```python
# _defaults/log.py (updated)
class DefaultLogProvider:
    """Default logging provider using stdlib logging.

    Per FR-LOG-003: Enhanced to support structured context via extra parameter.
    """

    def __init__(self, name: str = "autom8_asana") -> None:
        self._logger = logging.getLogger(name)

    def debug(
        self, msg: str, *args: Any, extra: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Log debug message with optional structured context."""
        self._logger.debug(msg, *args, extra=extra, **kwargs)

    def info(
        self, msg: str, *args: Any, extra: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Log info message with optional structured context."""
        self._logger.info(msg, *args, extra=extra, **kwargs)

    def warning(
        self, msg: str, *args: Any, extra: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Log warning message with optional structured context."""
        self._logger.warning(msg, *args, extra=extra, **kwargs)

    def error(
        self, msg: str, *args: Any, extra: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Log error message with optional structured context."""
        self._logger.error(msg, *args, extra=extra, **kwargs)

    def exception(
        self, msg: str, *args: Any, extra: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Log exception with traceback and optional structured context."""
        self._logger.exception(msg, *args, extra=extra, **kwargs)
```

**Zero-Cost Pattern (FR-LOG-005):**

```python
# Correct pattern for zero-cost logging
logger.debug("Entity %s tracked with %d changes", entity.gid, len(changes))

# Use guard for expensive operations
if logger.isEnabledFor(logging.DEBUG):
    summary = compute_expensive_debug_info(entity)
    logger.debug("Debug info: %s", summary)
```

### Component 5: ObservabilityHook Protocol (FR-OBS-*)

Per [ADR-HARDENING-A-002](/docs/decisions/ADR-HARDENING-A-002-observability-protocol-design.md):

**Protocol Definition (FR-OBS-001 through FR-OBS-007):**

```python
# protocols/observability.py (new file)
"""Observability hook protocol for telemetry integration."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ObservabilityHook(Protocol):
    """Protocol for observability integration.

    Per FR-OBS-001: Define ObservabilityHook protocol.
    Implement this protocol to receive SDK operation events.
    """

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        """Called before HTTP request (FR-OBS-002)."""
        ...

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        """Called after HTTP request completes (FR-OBS-003)."""
        ...

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None:
        """Called on HTTP request error (FR-OBS-004)."""
        ...

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        """Called on rate limit 429 (FR-OBS-005)."""
        ...

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        """Called on circuit breaker state change (FR-OBS-006)."""
        ...

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None:
        """Called before retry attempt (FR-OBS-007)."""
        ...
```

**NullObservabilityHook (FR-OBS-010):**

```python
# _defaults/observability.py (new file)
"""Default no-op observability hook."""
from __future__ import annotations


class NullObservabilityHook:
    """No-op observability hook (default).

    Per FR-OBS-010: Default implementation that performs no operations.
    """

    async def on_request_start(
        self, method: str, path: str, correlation_id: str
    ) -> None:
        pass

    async def on_request_end(
        self, method: str, path: str, status: int, duration_ms: float
    ) -> None:
        pass

    async def on_request_error(
        self, method: str, path: str, error: Exception
    ) -> None:
        pass

    async def on_rate_limit(self, retry_after_seconds: int) -> None:
        pass

    async def on_circuit_breaker_state_change(
        self, old_state: str, new_state: str
    ) -> None:
        pass

    async def on_retry(
        self, attempt: int, max_attempts: int, error: Exception
    ) -> None:
        pass
```

**Export Updates (FR-OBS-008, FR-OBS-009):**

```python
# protocols/__init__.py
from autom8_asana.protocols.observability import ObservabilityHook

__all__ = [
    # ... existing ...
    "ObservabilityHook",  # FR-OBS-008
]

# __init__.py (root)
from autom8_asana.protocols import ObservabilityHook  # FR-OBS-009
```

**Client Integration (FR-OBS-011):**

```python
# client.py (updated)
from autom8_asana._defaults.observability import NullObservabilityHook
from autom8_asana.protocols.observability import ObservabilityHook

class AsanaClient:
    def __init__(
        self,
        auth: AuthProvider,
        *,
        # ... existing params ...
        observability_hook: ObservabilityHook | None = None,  # FR-OBS-011
    ) -> None:
        self._observability = observability_hook or NullObservabilityHook()

    @property
    def observability(self) -> ObservabilityHook:
        """Observability hook for metrics and tracing."""
        return self._observability
```

### Data Model

No database or persistent data model changes. Changes are limited to:

1. **Exception class names** - `GidValidationError` (renamed)
2. **Protocol interface** - `ObservabilityHook` (new)
3. **Model classes** - `DNA`, `Reconciliation`, `Videography` (new)
4. **Dataclass** - `LogContext` (new)

### API Contracts

**New Public API:**

| Location | Export | Description |
|----------|--------|-------------|
| `persistence` | `GidValidationError` | Renamed exception for GID validation |
| `persistence` | `PositioningConflictError` | Existing exception, now exported |
| `protocols` | `ObservabilityHook` | Protocol for telemetry integration |
| `models.business` | `DNA` | Minimal typed model |
| `models.business` | `Reconciliation` | Minimal typed model |
| `models.business` | `Videography` | Minimal typed model |
| `observability` | `LogContext` | Structured logging context |

**Deprecated API:**

| Location | Export | Replacement | Removal |
|----------|--------|-------------|---------|
| `persistence` | `ValidationError` | `GidValidationError` | v2.0 |

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Exception rename strategy | Metaclass deprecation warning | Warns on any usage pattern | ADR-HARDENING-A-001 |
| Observability interface | Protocol over ABC | Matches SDK patterns, duck typing | ADR-HARDENING-A-002 |
| Logging format | `extra` dict, lazy formatting | Zero-cost, stdlib compatible | ADR-HARDENING-A-003 |
| Stub model scope | Navigation only, no fields | Domain unknown, future extensible | ADR-HARDENING-A-004 |

## Complexity Assessment

**Level**: Module

This initiative is **Module-level complexity** because:

1. **Bounded scope**: Changes are limited to specific files, not system-wide
2. **No new services**: All changes within existing SDK boundaries
3. **Minimal abstractions**: Protocol, dataclass, simple classes
4. **Clear interfaces**: Public API surface is small and well-defined
5. **Low risk**: Backward compatible changes, no data migrations

**Not Script** because:
- Multiple components affected
- New Protocol interface
- Deprecation strategy with timeline

**Not Service** because:
- No external APIs
- No deployment changes
- No runtime dependencies

## Implementation Plan

### Phase 1: Exception Hierarchy (Day 1)

| Task | Files | Requirements |
|------|-------|--------------|
| Rename ValidationError to GidValidationError | `persistence/exceptions.py` | FR-EXC-001 |
| Add deprecation metaclass for ValidationError | `persistence/exceptions.py` | FR-EXC-002 |
| Export PositioningConflictError | `persistence/__init__.py` | FR-EXC-003 |
| Export GidValidationError | `persistence/__init__.py` | FR-EXC-004 |
| Optional root export | `__init__.py` | FR-EXC-006 |
| Update internal usages | All files using ValidationError | FR-EXC-001 |
| Tests: deprecation warning emitted | `tests/unit/persistence/` | NFR-001 |

### Phase 2: API Surface Cleanup (Day 1)

| Task | Files | Requirements |
|------|-------|--------------|
| Remove `_traverse_upward_async` from `__all__` | `models/business/__init__.py` | FR-ALL-001 |
| Remove `_convert_to_typed_entity` from `__all__` | `models/business/__init__.py` | FR-ALL-002 |
| Remove `_is_recoverable` from `__all__` | `models/business/__init__.py` | FR-ALL-003 |
| Audit all `__init__.py` files | All packages | FR-ALL-004 |
| Tests: private functions not importable via `__all__` | `tests/unit/` | FR-ALL-004 |

### Phase 3: Stub Models (Day 2)

| Task | Files | Requirements |
|------|-------|--------------|
| Create DNA model | `models/business/dna.py` | FR-STUB-001 |
| Create Reconciliation model | `models/business/reconciliation.py` | FR-STUB-002 |
| Create Videography model | `models/business/videography.py` | FR-STUB-003 |
| Update DNAHolder.children return type | `models/business/business.py` | FR-STUB-004 |
| Update ReconciliationsHolder.children | `models/business/business.py` | FR-STUB-005 |
| Update VideographyHolder.children | `models/business/business.py` | FR-STUB-006 |
| Update CHILD_TYPE on holders | `models/business/business.py` | FR-STUB-007 |
| Add bidirectional navigation refs | `dna.py`, etc. | FR-STUB-008 |
| Export new models | `models/business/__init__.py` | FR-STUB-009 |
| Tests: typed children, navigation | `tests/unit/models/` | FR-STUB-* |

### Phase 4: Logging Standardization (Day 2-3)

| Task | Files | Requirements |
|------|-------|--------------|
| Create LogContext dataclass | `observability/context.py` | FR-LOG-002 |
| Enhance DefaultLogProvider with `extra` | `_defaults/log.py` | FR-LOG-003 |
| Migrate existing loggers to standard naming | Multiple modules | FR-LOG-001, FR-LOG-004 |
| Verify zero-cost pattern in hot paths | Transport, session | FR-LOG-005 |
| Tests: structured logging output | `tests/unit/` | FR-LOG-* |

### Phase 5: Observability Protocol (Day 3)

| Task | Files | Requirements |
|------|-------|--------------|
| Create ObservabilityHook protocol | `protocols/observability.py` | FR-OBS-001-007 |
| Export from protocols | `protocols/__init__.py` | FR-OBS-008 |
| Optional root export | `__init__.py` | FR-OBS-009 |
| Create NullObservabilityHook | `_defaults/observability.py` | FR-OBS-010 |
| Add observability_hook param to AsanaClient | `client.py` | FR-OBS-011 |
| Tests: protocol satisfaction, null behavior | `tests/unit/` | FR-OBS-* |

### Phase 6: Documentation (Day 4)

| Task | Files | Requirements |
|------|-------|--------------|
| Document SyncInAsyncContextError inheritance | SDK guide | FR-EXC-005 |
| Document list method naming patterns | SDK guide | FR-NAM-001 |
| Document get_custom_fields() semantics | Docstrings | FR-NAM-002 |
| Document ObservabilityHook usage | SDK guide | FR-OBS-012 |
| Document logging configuration | SDK guide | FR-LOG-006 |

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Deprecation warning noise annoys users | Med | Med | Single warning per session, clear migration path |
| Breaking internal code using ValidationError | High | Low | Grep audit, update all internal usages first |
| Circular imports with new models | Med | Med | Use TYPE_CHECKING guards, test import order |
| mypy issues with metaclass | Med | Low | Test with mypy, document any type: ignore |
| ObservabilityHook not called in all paths | Med | Med | Integration tests for each hook point |

## Observability

### Metrics (via ObservabilityHook)

- `on_request_start/end` enables: request count, latency histogram, status code distribution
- `on_rate_limit` enables: rate limit events counter
- `on_circuit_breaker_state_change` enables: circuit state gauge
- `on_retry` enables: retry attempts counter

### Logging

- All SDK modules use `autom8_asana.*` namespace
- Structured context via `LogContext.to_dict()` in `extra`
- Configuration example in SDK guide

### Alerting

Not applicable - SDK does not generate alerts. Users configure their own alerting via ObservabilityHook implementations.

## Testing Strategy

### Unit Testing

| Area | Coverage Focus |
|------|----------------|
| Exception rename | Deprecation warning, inheritance, catching |
| API surface | Private functions not in namespace |
| Stub models | Type checking, navigation, holder population |
| LogContext | Serialization, None handling |
| ObservabilityHook | Protocol satisfaction, NullObservabilityHook |

### Integration Testing

| Area | Coverage Focus |
|------|----------------|
| Exception backward compat | Existing `except ValidationError` still works |
| Holder children | `business.dna_holder.children` returns `list[DNA]` |
| Client observability | Hook methods called at correct lifecycle points |

### Type Checking

```bash
mypy src/autom8_asana  # Must pass
```

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| ~~Exception new name?~~ | Team | 2025-12-16 | Resolved: `GidValidationError` |
| ~~Stub model scope?~~ | Team | 2025-12-16 | Resolved: Navigation only |
| ~~Protocol vs ABC?~~ | Team | 2025-12-16 | Resolved: Protocol |

All blocking questions resolved.

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Architect | Initial draft |

---

## Appendix A: File Change Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `persistence/exceptions.py` | Modify | Rename ValidationError, add deprecation |
| `persistence/__init__.py` | Modify | Add exports |
| `models/business/__init__.py` | Modify | Remove private exports, add new models |
| `models/business/business.py` | Modify | Update holder types |
| `models/business/dna.py` | Create | DNA minimal model |
| `models/business/reconciliation.py` | Create | Reconciliation minimal model |
| `models/business/videography.py` | Create | Videography minimal model |
| `protocols/observability.py` | Create | ObservabilityHook protocol |
| `protocols/__init__.py` | Modify | Export ObservabilityHook |
| `_defaults/observability.py` | Create | NullObservabilityHook |
| `_defaults/__init__.py` | Modify | Export NullObservabilityHook |
| `_defaults/log.py` | Modify | Add `extra` support |
| `observability/context.py` | Create | LogContext dataclass |
| `client.py` | Modify | Add observability_hook param |
| `__init__.py` (root) | Modify | Optional exports |

## Appendix B: Requirement Traceability

| Requirement | Design Section | Status |
|-------------|----------------|--------|
| FR-EXC-001 | Component 1 | Designed |
| FR-EXC-002 | Component 1 | Designed |
| FR-EXC-003 | Component 1 | Designed |
| FR-EXC-004 | Component 1 | Designed |
| FR-EXC-005 | Phase 6 (docs) | Planned |
| FR-EXC-006 | Component 1 | Designed |
| FR-ALL-001 | Component 2 | Designed |
| FR-ALL-002 | Component 2 | Designed |
| FR-ALL-003 | Component 2 | Designed |
| FR-ALL-004 | Component 2 | Designed |
| FR-STUB-001 | Component 3 | Designed |
| FR-STUB-002 | Component 3 | Designed |
| FR-STUB-003 | Component 3 | Designed |
| FR-STUB-004 | Component 3 | Designed |
| FR-STUB-005 | Component 3 | Designed |
| FR-STUB-006 | Component 3 | Designed |
| FR-STUB-007 | Component 3 | Designed |
| FR-STUB-008 | Component 3 | Designed |
| FR-STUB-009 | Component 3 | Designed |
| FR-STUB-010 | Component 3 | Designed (excluded) |
| FR-LOG-001 | Component 4 | Designed |
| FR-LOG-002 | Component 4 | Designed |
| FR-LOG-003 | Component 4 | Designed |
| FR-LOG-004 | Component 4 | Designed |
| FR-LOG-005 | Component 4 | Designed |
| FR-LOG-006 | Phase 6 (docs) | Planned |
| FR-OBS-001 | Component 5 | Designed |
| FR-OBS-002 | Component 5 | Designed |
| FR-OBS-003 | Component 5 | Designed |
| FR-OBS-004 | Component 5 | Designed |
| FR-OBS-005 | Component 5 | Designed |
| FR-OBS-006 | Component 5 | Designed |
| FR-OBS-007 | Component 5 | Designed |
| FR-OBS-008 | Component 5 | Designed |
| FR-OBS-009 | Component 5 | Designed |
| FR-OBS-010 | Component 5 | Designed |
| FR-OBS-011 | Component 5 | Designed |
| FR-OBS-012 | Phase 6 (docs) | Planned |
| FR-NAM-001 | Phase 6 (docs) | Planned |
| FR-NAM-002 | Phase 6 (docs) | Planned |
| NFR-001 | Component 1 | Addressed (deprecation alias) |
| NFR-002 | All | Verified (no new deps) |
| NFR-003 | Component 4 | Designed (lazy formatting) |
| NFR-004 | All | Verified (mypy passing) |
| NFR-005 | Testing Strategy | Planned |
