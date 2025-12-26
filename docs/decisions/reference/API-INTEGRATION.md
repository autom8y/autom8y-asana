# ADR Summary: API Integration & Error Handling

> Consolidated decision record for external integration, API design, and error resilience. Individual ADRs archived.

## Overview

The SDK's integration with the Asana API balances control, resilience, and developer experience. Rather than fully adopting or completely replacing the official Asana SDK, we implement a hybrid approach: custom HTTP transport for async operations, rate limiting, and concurrency control, while retaining the official SDK for type reference and API compatibility. This architectural choice enables precise control over network behavior while maintaining alignment with Asana's evolving API contracts.

Error handling follows a commit-and-report philosophy: operations that partially succeed preserve their successful work and report failures explicitly through structured result types. The SDK prioritizes graceful degradation over fail-fast rigidity, enabling applications to continue functioning even when Asana's API experiences transient failures or when cache layers become temporarily unavailable.

API design emphasizes progressive disclosure and explicitness. The public API surface is carefully controlled through `__all__` exports, with clear boundaries between stable public interfaces, power-user submodules, and internal implementation details. Hydration and batch resolution APIs return rich metadata about what succeeded and what failed, allowing callers to make informed decisions about recovery strategies.

## Key Decisions

### 1. SDK Integration: HTTP Layer Design
**Context**: Need async-first transport with rate limiting and retry logic incompatible with official SDK's sync-only design

**Decision**: Replace Asana SDK's HTTP layer with httpx-based transport, retain SDK for type definitions and error patterns

**Rationale**: Official SDK lacks async support, custom rate limiting, and configurable retry strategies. Keeping it as a dependency provides type reference for API compatibility verification and battle-tested error parsing patterns.

**Source ADRs**: ADR-0003 (HTTP Layer), ADR-0007 (Client Pattern)

**Consequences**: Full control over transport, async operations, custom rate limiting. Requires maintenance of parallel type definitions (Pydantic models vs SDK types).

**Implementation**: `AsyncHTTPClient` with httpx handles all HTTP; official SDK types used for reference only; all resource clients follow consistent pattern (async-first, `raw` parameter, PageIterator for lists).

---

### 2. Specialized Protocol Handling: Webhooks & Attachments
**Context**: Webhook signature verification and attachment uploads require specialized handling distinct from standard JSON API operations

**Decision**:
- Webhook signature verification as static utility methods on `WebhooksClient`
- Attachment uploads via `post_multipart()` method on `AsyncHTTPClient`
- Streaming downloads for large files

**Rationale**: Static verification methods require no client state and work across web frameworks. Multipart upload support extends HTTP client cleanly without creating separate upload infrastructure. Streaming prevents memory exhaustion on large files.

**Source ADRs**: ADR-0008 (Webhooks), ADR-0009 (Attachments)

**Consequences**: Framework-agnostic signature verification; efficient memory usage for file operations; transport layer gains multipart encoding capability.

**Implementation**: `WebhooksClient.verify_signature()` uses HMAC-SHA256 with timing-safe comparison; `post_multipart()` leverages httpx's built-in multipart support; downloads use `async with response.aiter_bytes()`.

---

### 3. Observability: Correlation IDs
**Context**: SDK operations may fan out into multiple HTTP requests; need to trace activity for a single SDK call

**Decision**: Generate SDK-scoped correlation IDs using format `sdk-{timestamp_hex}-{random_hex}`, propagate via `@error_handler` decorator

**Rationale**: Asana's `X-Request-Id` is valuable but insufficient (only available after request completes, changes on retry, multiple IDs for pagination). SDK-generated IDs provide consistent tracing regardless of HTTP layer behavior. Timestamp prefix enables temporal ordering in logs; random suffix prevents collisions.

**Source ADRs**: ADR-0013

**Consequences**: Every SDK operation traceable by default; correlation IDs short enough for readable logs (18 chars); small collision risk acceptable for debugging purposes (~1/65536 per millisecond).

**Implementation**: Per-operation scope (each `get_async()` call gets one ID for all its HTTP requests); decorator-based injection for explicit error handling boundary; explicit parameter passing (no contextvars).

---

### 4. Batch Operations: Request Format & API Design
**Context**: Batch API enables bulk operations but requires specific request format and efficient resolution strategies

**Decision**:
- Wrap batch actions in `{"data": {"actions": [...]}}` structure
- Implement batch resolution as module-level functions in `resolution.py`
- Optimize via shared lookups and concurrent fetches

**Rationale**: Asana API requires `data` wrapper for batch requests. Module functions provide clear API for collection operations without artificial class constraints. Shared lookups (fetch Business.units once) and concurrent dependents fetching minimize API calls.

**Source ADRs**: ADR-0015 (Request Format), ADR-0073 (Batch Resolution API)

**Consequences**: Fixed batch format matches Asana expectations; batch resolution works with any AssetEdit collection; returns dict mapping GID to result for O(1) lookup.

**Implementation**: `BatchClient` wraps actions in data envelope; `resolve_units_async()` and `resolve_offers_async()` as module functions returning `dict[str, ResolutionResult[T]]`; internal optimization groups by Business to minimize redundant fetches.

---

### 5. Error Classification: Retryability & Recovery
**Context**: Users need to determine if failed operations are worth retrying vs. requiring manual intervention

**Decision**:
- Classify errors as retryable based on HTTP status code (429, 5xx retryable; 4xx not retryable)
- Provide `is_retryable` property on `SaveError` and `ActionResult`
- Extract classification logic into `RetryableErrorMixin` to eliminate duplication

**Rationale**: HTTP status codes have well-defined semantics (RFC 7231). Rate limits (429) are explicitly designed for retry; server errors (5xx) are transient by nature. Client errors (4xx) indicate payload issues requiring fixes, not retries.

**Source ADRs**: ADR-0079 (Classification), ADR-0091 (Mixin)

**Consequences**: Users get advisory guidance on retry eligibility; classification follows HTTP standards; mixin eliminates ~90 lines of duplication between `SaveError` and `ActionResult`.

**Classification Table**:
| Status | Retryable | Reason |
|--------|-----------|--------|
| 400-409, 410+ | No | Client error - fix payload/permissions |
| 429 | Yes | Rate limit - retry after delay |
| 500-504 | Yes | Server error - transient |

---

### 6. Exception Taxonomy: Naming & Hierarchy
**Context**: Need clear exception names that don't conflict with Pydantic's `ValidationError` and accurately describe failure modes

**Decision**:
- Rename `ValidationError` to `GidValidationError` with backward-compatible alias
- Create `SaveSessionError` for convenience method failures
- Provide metaclass-based deprecation warnings

**Rationale**: `ValidationError` conflicts with Pydantic's exception. `GidValidationError` accurately describes its purpose (GID format validation). Metaclass warnings catch all usage patterns (except clauses, isinstance checks, attribute access) while maintaining inheritance.

**Source ADRs**: ADR-0084 (Rename Strategy), ADR-0065 (SaveSessionError)

**Consequences**: No import conflicts with Pydantic; clear semantic names; smooth migration path via deprecation warnings; convenience methods fail explicitly when operations don't succeed.

**Implementation**: `GidValidationError` is canonical; `ValidationError` alias uses metaclass to warn on access; `SaveSessionError` wraps `SaveResult` with descriptive message; both in `SaveOrchestrationError` hierarchy.

---

### 7. Partial Failure Handling: Commit-and-Report
**Context**: Asana Batch API returns per-action results; some operations may succeed while others fail

**Decision**:
- Commit all successful operations, report failures in `SaveResult`
- No rollback (Asana lacks transaction support)
- Return `SaveResult` with succeeded/failed lists
- Optional `raise_on_failure()` for exception-based handling

**Rationale**: Asana doesn't support transactions or rollback. Successful operations are already committed to Asana. Throwing away successful work because of unrelated failures wastes effort. Structured result type enables caller to decide response (retry, log, escalate).

**Source ADRs**: ADR-0040 (SaveSession), ADR-0070 (Hydration)

**Consequences**: Preserves successful work; full information about successes and failures; caller controls error handling strategy; partial state may require cleanup (developer responsibility).

**Result Structure**:
```python
@dataclass
class SaveResult:
    succeeded: list[EntityResult]
    failed: list[SaveError]
    action_results: list[ActionResult]

    @property
    def success(self) -> bool  # True if zero failures
    @property
    def partial(self) -> bool  # True if some success, some failure
```

Hydration follows same pattern with `HydrationResult` including succeeded/failed branches.

---

### 8. Resilience: Circuit Breaker & Graceful Degradation
**Context**: Need protection against cascading failures when Asana API degrades or cache infrastructure fails

**Decision**:
- Opt-in circuit breaker for HTTP transport (disabled by default for backward compatibility)
- Cache failures log warnings without raising exceptions
- Treat cache errors as cache misses, continue with API fallback

**Rationale**: Circuit breaker prevents hammering failing services; fast-fails when service is known-bad; auto-recovery when service recovers. Cache is optimization layer - failures shouldn't break user-facing operations. Logged warnings provide visibility without disrupting operations.

**Source ADRs**: ADR-0048 (Circuit Breaker), ADR-0127 (Cache Degradation), ADR-0090 (Demo Error Handling)

**Consequences**: Protection from cascading failures (opt-in); backward compatible (disabled by default); cache failures visible in logs but don't propagate to users; slightly slower responses when cache fails until infrastructure recovers.

**Circuit States**: CLOSED → OPEN (after failure threshold) → HALF_OPEN (after recovery timeout) → CLOSED (after successful probe)

**Cache Degradation**: All cache operations wrapped in `try/except Exception`; failures logged at WARNING level; metrics incremented for monitoring; operations proceed as if cache unavailable.

---

### 9. API Surface Design: Public vs. Internal
**Context**: Need clear boundaries between stable API, power-user features, and internal implementation

**Decision**:
- Three-tier visibility: Public (root exports), Semi-public (submodule exports), Internal (underscore prefix)
- Public API in `autom8_asana/__init__.py.__all__`
- Internal modules prefixed with underscore (`_defaults/`, `_internal/`)

**Rationale**: Clear public surface enables stable semantic versioning. Power users can access submodules when needed. Underscore convention signals private implementation following Python standards. IDE autocomplete shows only stable APIs from root import.

**Source ADRs**: ADR-0012

**Consequences**: Clear API contract for users; refactoring freedom for internals; semantic versioning applies to public tier only; users may import internals anyway (Python doesn't prevent it).

**Tiers**:
- **Tier 1 (Public)**: Exported from root, stable, semantic versioning applies
- **Tier 2 (Semi-public)**: Submodule imports, stable signatures, changes in changelog
- **Tier 3 (Internal)**: Underscore prefix, no stability guarantees

---

### 10. Comment & Positioning: Storage & Validation
**Context**: Comments and positioning parameters need storage between queue and commit; validation timing affects error attribution

**Decision**:
- Store comment text/html_text in `ActionOperation.extra_params`
- Validate positioning conflicts at queue time (when method called)
- Fail-fast with clear error messages pointing to call site

**Rationale**: `extra_params` established as mechanism for action-specific data (ADR-0044). Queue-time validation provides immediate feedback with stack trace pointing to mistake. Positioning validation at queue time consistent with comment text validation pattern.

**Source ADRs**: ADR-0046 (Comment Storage), ADR-0047 (Positioning Validation)

**Consequences**: Consistent use of `extra_params` pattern; validation logic lives in SaveSession methods; early error detection with clear attribution; no wasted operations for invalid input.

**Positioning**: `PositioningConflictError` raised immediately if both `insert_before` and `insert_after` specified. Error includes both GIDs for debugging.

---

### 11. Hydration API: Entry Points & Partial Results
**Context**: Need flexible entry points for loading business model hierarchies; must handle partial failures

**Decision**:
- Factory method: `Business.from_gid_async(client, gid, hydrate=True)`
- Navigation methods: `Contact.to_business_async(client, hydrate_full=True)`
- Generic entry: `hydrate_from_gid_async(client, gid)` returns `HydrationResult`
- Fail-fast by default; opt-in `partial_ok` for resilient use cases

**Rationale**: Multiple entry points support different use cases (known Business GID, webhook with unknown GID, navigation from leaf entity). Factory methods return typed entities; generic entry returns rich metadata. Fail-fast default is safe; partial tolerance available when needed.

**Source ADRs**: ADR-0069 (API Design), ADR-0070 (Partial Failure), ADR-0128 (Field Normalization)

**Consequences**: Discoverable APIs via class methods and instance methods; type-safe returns for common cases; metadata available for advanced scenarios; partial hierarchies may have inconsistent references when `partial_ok=True`.

**HydrationResult**: Includes `business`, `entry_entity`, `succeeded`/`failed` branches, `is_complete` property. Concurrent holder fetching with failure isolation.

**Field Standardization**: Single `STANDARD_TASK_OPT_FIELDS` constant in `models/business/fields.py` ensures all detection paths have consistent field sets, eliminating class of bugs from field set drift.

---

### 12. Client Reference Storage: Strong vs. Weak
**Context**: Task convenience methods (save_async, refresh_async) need access to client; storage strategy affects memory and lifecycle

**Decision**: Store strong reference to client in `Task._client` PrivateAttr (not WeakReference)

**Rationale**: Simple implementation using standard Python assignment; acceptable memory impact (tasks short-lived, client lightweight); no circular reference issue (one-way link); matches existing pattern (`_custom_fields_accessor` in Task, client reference in SaveSession).

**Source ADRs**: ADR-0063

**Consequences**: Simple O(1) access; no weakref dereferencing overhead; task holds strong reference (keeps client alive); pattern matches existing codebase conventions.

**Alternative Rejected**: WeakReference adds unnecessary complexity (client outlives task in typical use), extra function call overhead, harder debugging.

---

## Cross-References

**Related Summaries**:
- ADR-SUMMARY-PATTERNS: SaveSession, Unit of Work, action queuing
- ADR-SUMMARY-SAVESESSION: Persistence layer, lifecycle, batch execution

**Key Patterns**:
- Commit-and-Report: Used in SaveSession (ADR-0040), Hydration (ADR-0070)
- Graceful Degradation: Used in Circuit Breaker (ADR-0048), Cache (ADR-0127), Demo Scripts (ADR-0090)
- Static Utilities: Webhook verification (ADR-0008), error classification helpers
- Progressive Disclosure: Public/semi-public/internal tiers (ADR-0012)

**Error Hierarchy**:
```
AsanaError (base)
├── SaveOrchestrationError
│   ├── GidValidationError (ValidationError deprecated)
│   ├── SaveSessionError
│   ├── PositioningConflictError
│   └── PartialSaveError
├── HydrationError
└── [Transport errors: RateLimitError, TimeoutError, ServerError...]
```

---

## Archived Individual ADRs

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| ADR-0003 | Replace Asana SDK HTTP Layer | 2025-12-08 | Custom httpx transport, retain SDK for types |
| ADR-0007 | Consistent Client Pattern | 2025-12-08 | All clients follow TasksClient pattern |
| ADR-0008 | Webhook Signature Verification | 2025-12-08 | Static utility methods, HMAC-SHA256 |
| ADR-0009 | Attachment Multipart Handling | 2025-12-08 | post_multipart method, streaming downloads |
| ADR-0012 | Public API Surface Definition | 2025-12-08 | Three-tier visibility model |
| ADR-0013 | Correlation ID Strategy | 2025-12-08 | SDK-generated IDs, decorator propagation |
| ADR-0015 | Batch API Request Format Fix | 2025-12-09 | Wrap actions in data envelope |
| ADR-0040 | Commit and Report on Partial Failure | 2025-12-10 | Preserve successful work, report failures |
| ADR-0046 | Comment Text Storage Strategy | 2025-12-10 | Store in extra_params, validate at queue time |
| ADR-0047 | Positioning Validation Timing | 2025-12-10 | Fail-fast at queue time |
| ADR-0048 | Circuit Breaker Pattern | 2025-12-10 | Opt-in composition-based, per-client scope |
| ADR-0063 | Client Reference Storage | 2025-12-12 | Strong reference in PrivateAttr |
| ADR-0065 | SaveSessionError Exception | 2025-12-12 | Wrap SaveResult with descriptive message |
| ADR-0069 | Hydration API Design | 2025-12-16 | Factory + navigation + generic entry points |
| ADR-0070 | Hydration Partial Failure Handling | 2025-12-16 | HydrationResult with succeeded/failed tracking |
| ADR-0073 | Batch Resolution API Design | 2025-12-16 | Module functions returning dict[gid, result] |
| ADR-0079 | Retryable Error Classification | 2025-12-16 | HTTP status-based, is_retryable property |
| ADR-0084 | Exception Rename Strategy | 2025-12-16 | GidValidationError with deprecated alias |
| ADR-0090 | Demo Error Handling | 2025-12-12 | Graceful degradation, manual recovery guidance |
| ADR-0091 | RetryableErrorMixin | 2024-12-16 | DRY error classification via mixin |
| ADR-0127 | Cache Graceful Degradation | 2025-12-22 | Log warnings, treat as misses, continue |
| ADR-0128 | Hydration opt_fields Normalization | 2025-12-23 | Single STANDARD_TASK_OPT_FIELDS constant |

---

## Decision Principles

The decisions in this summary reflect several core principles:

1. **Async-First**: All I/O operations are async with sync wrappers, not sync with async wrappers
2. **Fail Explicitly**: Errors surface clearly rather than being silently swallowed
3. **Preserve Work**: Successful operations retained even when related operations fail
4. **Degrade Gracefully**: Optional components (cache, circuit breaker) fail without disrupting core functionality
5. **Standard Protocols**: Follow HTTP semantics (status codes), Python conventions (underscores for private)
6. **Progressive Disclosure**: Simple cases simple, advanced features available when needed
7. **Observability**: Operations traceable via correlation IDs, errors logged with context
8. **Type Safety**: Strong typing with Pydantic models, overloads for `raw` parameter
9. **API Consistency**: Patterns established in one client propagate to all clients

These principles guide future API decisions and refactoring efforts.
