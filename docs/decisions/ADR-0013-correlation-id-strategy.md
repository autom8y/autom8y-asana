# ADR-0013: Correlation ID Strategy for SDK Observability

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0001 (FR-SDK-044, FR-SDK-045), TDD-0007

## Context

The autom8_asana SDK needs request tracing capability for debugging and observability. Per PRD-0001:
- FR-SDK-044: Provide ErrorHandler decorator for consistent handling
- FR-SDK-045: Log errors with correlation IDs

The SDK already captures Asana's `X-Request-Id` from API responses and includes it in error messages. However, this ID is only available *after* a request completes, and multiple SDK operations may fan out into multiple HTTP requests (e.g., paginated operations, batch operations).

We need an SDK-generated correlation ID that:
1. Is available before any HTTP request is made
2. Groups all activity for a single SDK operation
3. Can be included in logs and exceptions
4. Can be correlated with Asana's X-Request-Id when available

Key forces:
- **Debuggability**: Engineers need to trace a single SDK call through all its activity
- **Simplicity**: Avoid complex distributed tracing infrastructure
- **Performance**: ID generation must be fast (called on every operation)
- **Thread-safety**: SDK is used concurrently; IDs must not collide
- **Compatibility**: Must work with existing LogProvider protocol

## Decision

Generate SDK correlation IDs using the format: `sdk-{timestamp_hex}-{random_hex}`

Key design choices:

1. **SDK-generated IDs** (not passed in by caller): The SDK generates a new correlation ID for each operation. This is simpler than requiring callers to manage IDs, and ensures every operation is traceable.

2. **Timestamp-based prefix**: Include lower 32 bits of Unix timestamp (milliseconds) as 8 hex characters. This provides rough temporal ordering for debugging.

3. **Random suffix**: Include 4 hex characters (16 bits) of randomness to avoid collisions within the same millisecond.

4. **Per-operation scope**: Each top-level SDK operation (e.g., `client.tasks.get_async()`) gets one correlation ID. All HTTP requests, retries, and pagination within that operation share the same ID.

5. **Decorator-based injection**: Use an `@error_handler` decorator on client methods to generate and propagate correlation IDs. This is explicit and avoids hidden state.

6. **No global context**: Use explicit parameter passing rather than contextvars or thread-locals. This is simpler and more testable.

## Rationale

### Why SDK-generated IDs?

Asana's X-Request-Id is valuable but insufficient:
- Only available after HTTP request completes
- Changes on each retry
- Paginated operations have multiple X-Request-Ids
- Not available when request fails before reaching Asana (e.g., rate limit)

SDK-generated IDs provide consistent tracing regardless of what happens at the HTTP layer.

### Why timestamp + random?

This format balances several concerns:

| Approach | Pros | Cons |
|----------|------|------|
| UUID v4 | Very unique | Long (36 chars), no ordering, overkill |
| Incrementing counter | Short, ordered | Requires shared state, thread-safety concerns |
| Timestamp only | Short, ordered | Collisions within same ms |
| Timestamp + random | Short, ordered, unique enough | 4 random chars may collide (1/65536) |

The timestamp + random approach is:
- Short enough for readable logs (18 characters)
- Ordered for debugging (earlier operations sort first in logs)
- Unique enough (collision requires same ms + same random = ~1 in 65536 per ms)
- Fast to generate (no locks, no I/O)

### Why explicit decorators?

Alternatives considered:

1. **Class decorator that wraps all methods**: Implicit, wraps internal methods unnecessarily
2. **BaseClient magic in `__getattribute__`**: Clever but hard to understand
3. **Manual context creation in each method**: Verbose, easy to forget

Explicit `@error_handler` decorator:
- Clear what gets error handling
- Easy to understand and debug
- Standard Python pattern
- Works with type checkers

### Why per-operation scope (not per-request)?

A single SDK operation may involve multiple HTTP requests:
- Paginated list operations fetch multiple pages
- Retries send the same request multiple times
- Batch operations may chunk into multiple API calls

Using the same correlation ID for all of these groups related activity together, which is what engineers need for debugging.

## Alternatives Considered

### Alternative 1: Use OpenTelemetry

- **Description**: Integrate with OpenTelemetry for distributed tracing
- **Pros**: Industry standard, rich ecosystem, automatic instrumentation
- **Cons**: Heavy dependency (OpenTelemetry SDK is large), requires infrastructure (collector), overkill for SDK-level tracing
- **Why not chosen**: Violates minimal dependency principle; consumers can integrate OTel at their level if needed

### Alternative 2: Pass correlation ID from caller

- **Description**: Require callers to generate and pass correlation IDs
- **Pros**: Caller controls ID format, can integrate with existing tracing
- **Cons**: Burdens all callers, easy to forget, optional IDs lead to inconsistent tracing
- **Why not chosen**: SDK should be easy to use; tracing should be automatic

### Alternative 3: Use contextvars for implicit propagation

- **Description**: Store correlation ID in contextvars, automatically propagate
- **Pros**: No need to pass context explicitly, works across async boundaries
- **Cons**: Magic (implicit state), harder to test, potential issues with thread pools
- **Why not chosen**: Explicit is better than implicit; passing context is not burdensome in our design

### Alternative 4: Pure UUID v4

- **Description**: Generate standard UUIDs for each operation
- **Pros**: Guaranteed unique, widely understood
- **Cons**: Long (36 chars with dashes), no temporal information, harder to read in logs
- **Why not chosen**: Our shorter format is unique enough and more readable

## Consequences

### Positive

- **Consistent tracing**: Every SDK operation is traceable by default
- **No caller burden**: SDK handles correlation ID generation
- **Debuggable**: Timestamp in ID helps order events mentally
- **Low overhead**: ID generation is fast and allocation-free (mostly)
- **Testable**: Explicit decorator pattern is easy to test
- **Log-friendly**: Short IDs don't clutter log output

### Negative

- **Collision risk**: Small chance of ID collision (~1/65536 per ms); acceptable for debugging purposes, not suitable for distributed transaction IDs
- **Not externally correlated**: SDK IDs don't automatically correlate with caller's tracing system; callers who want this must log the SDK's correlation ID alongside their own
- **Decorator overhead**: Small runtime cost for decorator invocation on every operation

### Neutral

- **Asana X-Request-Id still useful**: We capture and log Asana's ID alongside ours; they serve complementary purposes
- **Consumers can override**: Advanced consumers can wrap clients to add their own correlation

## Compliance

How we ensure this decision is followed:

1. **Code review**: Verify `@error_handler` decorator on all public async client methods
2. **Test coverage**: Unit tests verify correlation ID generation and propagation
3. **Grep check**: `grep -r "async def.*_async" --include="*.py" src/autom8_asana/clients/` should show `@error_handler` on preceding line
4. **Documentation**: TDD-0007 specifies which methods need the decorator
