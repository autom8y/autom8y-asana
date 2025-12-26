# ADR-0003: Replace Asana SDK HTTP Layer, Retain Types and Error Parsing

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md), [TDD-0001](../design/TDD-0001-sdk-architecture.md), FR-COMPAT-007

## Context

The PRD requires the official `asana` Python SDK (5.0.3+) as a dependency (FR-COMPAT-007). We need to decide how to integrate with it:

The official `asana` SDK provides:
1. **HTTP client**: Request building, authentication, response handling
2. **Type definitions**: Classes for Task, Project, User, etc.
3. **Error parsing**: Structured error objects from API responses
4. **Pagination helpers**: Iterator classes for paginated endpoints
5. **API method wrappers**: Pre-built methods for each endpoint

Our SDK needs:
1. **Custom HTTP transport**: httpx with connection pooling, async-first (FR-SDK-001, FR-SDK-002)
2. **Rate limiting**: Token bucket at 1500 req/min (FR-SDK-006)
3. **Retry logic**: Exponential backoff with jitter (FR-SDK-007-011)
4. **Concurrency control**: Semaphores for read/write limits (FR-SDK-013-014)

The official SDK's HTTP layer doesn't support:
- Async operations (it's sync-only)
- Custom rate limiting
- Configurable retry strategies
- Connection pooling configuration

## Decision

**Replace the Asana SDK's HTTP layer with our own httpx-based transport, but retain the SDK for type definitions and error response parsing.**

Integration approach:

```python
# We import types from asana SDK for reference/compatibility
from asana.models import Task as AsanaTask  # For type reference only

# But we define our own Pydantic models that are API-compatible
from autom8_asana.models import Task  # Our Pydantic model

# Our transport layer handles all HTTP
class AsyncHTTPClient:
    async def request(self, method: str, path: str, **kwargs) -> dict:
        # Use httpx for HTTP
        # Apply our rate limiting
        # Apply our retry logic
        # Return raw dict response
        ...

# Error parsing can leverage asana SDK's error classes
from asana.errors import AsanaError as UpstreamAsanaError

def parse_error_response(status_code: int, body: dict) -> Exception:
    """Convert API error response to appropriate exception."""
    # Can reference upstream error parsing logic
    # But wrap in our own exception hierarchy
    ...
```

We keep `asana` as a dependency for:
1. Reference for type structures (ensuring API compatibility)
2. Error response parsing patterns
3. Future compatibility (if Asana changes API, their SDK updates first)

We replace:
1. All HTTP request handling (use httpx)
2. Authentication injection (use our AuthProvider protocol)
3. Pagination (use our PageIterator)
4. All sync/async handling

## Rationale

This hybrid approach gives us:

1. **Full control over transport**: We can implement exactly the rate limiting, retry, and concurrency behavior we need.

2. **Async-first design**: The official SDK is sync-only. We need async for performance.

3. **Type safety without coupling**: We reference Asana SDK types to ensure our models are compatible, but our Pydantic models are independent.

4. **Easier updates**: When Asana releases API changes, their SDK updates. We can compare our models against theirs to catch drift.

5. **Error handling patterns**: The official SDK has battle-tested error parsing. We can reference it without using their HTTP layer.

## Alternatives Considered

### Full Adoption (Use Asana SDK Directly)

- **Description**: Use the official SDK as-is, wrapping its methods.
- **Pros**:
  - Less code to write
  - Automatic updates when Asana releases changes
  - Battle-tested implementation
- **Cons**:
  - Sync-only (can't use in async code without threads)
  - No custom rate limiting control
  - No custom retry logic
  - No connection pooling configuration
  - Can't meet FR-SDK-001 through FR-SDK-015
- **Why not chosen**: The official SDK doesn't support our async-first, custom-transport requirements.

### Complete Replacement (No Asana SDK Dependency)

- **Description**: Remove `asana` dependency entirely. Implement everything from scratch.
- **Pros**:
  - Complete independence
  - No unused code in dependency tree
  - Full control over everything
- **Cons**:
  - Must track API changes manually
  - No reference implementation for error parsing
  - Higher maintenance burden
  - Violates FR-COMPAT-007 (SDK should keep asana as dependency)
- **Why not chosen**: PRD explicitly requires `asana` dependency. Keeping it provides valuable reference.

### Fork Asana SDK

- **Description**: Fork the official SDK and modify it.
- **Pros**:
  - Start with working code
  - Can add async incrementally
- **Cons**:
  - Maintenance burden of keeping fork updated
  - License considerations
  - Significant refactoring needed for async
  - Still inherits sync-first design decisions
- **Why not chosen**: Forks are maintenance nightmares. Better to build clean from scratch.

### Async Wrapper Around Sync SDK

- **Description**: Use official SDK but wrap in `asyncio.to_thread()` calls.
- **Pros**:
  - Quick to implement
  - Uses battle-tested SDK code
- **Cons**:
  - Thread overhead for every call
  - Doesn't solve rate limiting/retry requirements
  - Connection pooling doesn't work across threads
  - Just hiding sync code, not truly async
- **Why not chosen**: Thread-per-call defeats the purpose of async. Doesn't meet performance goals.

## Consequences

### Positive
- **Full async support**: httpx provides native async HTTP
- **Custom rate limiting**: Token bucket exactly as specified
- **Custom retry logic**: Exponential backoff with jitter
- **Connection pooling**: httpx handles this efficiently
- **Type reference**: Can verify our models match Asana's expectations
- **Future-proofing**: Can compare against SDK updates to catch API changes

### Negative
- **More code to maintain**: We own the transport layer
- **Potential drift**: Our models might diverge from Asana's over time
- **Dependency not fully utilized**: We include `asana` but don't use most of it
- **Duplicate type definitions**: Our Pydantic models overlap with SDK classes

### Neutral
- **Two type systems**: Asana SDK has its classes, we have Pydantic models
- **Error hierarchy**: We define our own exceptions but can reference Asana's patterns
- **Documentation**: Must document that we're httpx-based, not using official transport

## Compliance

To ensure this decision is followed:

1. **No direct Asana SDK HTTP calls**: Code review blocks `asana.Client` usage
2. **Import auditing**: CI checks that `asana` imports are only for types/errors, not transport
3. **Architecture tests**: Verify `httpx` is the only HTTP library making requests
4. **Model comparison**: Periodic script to compare our models against Asana SDK types
5. **Documentation**: README explains the relationship with official SDK
