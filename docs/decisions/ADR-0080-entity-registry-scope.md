# ADR-0080: Entity Registry Scope

## Metadata

| Field | Value |
|-------|-------|
| **Status** | Accepted |
| **Author** | Architect |
| **Date** | 2025-12-16 |
| **Deciders** | Architect, Principal Engineer |
| **Related** | PRD-HARDENING-F, TDD-HARDENING-F, ADR-0078 |

---

## Context

With the move to GID-based entity tracking (ADR-0078), we must decide the scope of the entity registry. Two primary options exist:

1. **Per-SaveSession**: Each `SaveSession` instance has its own isolated registry
2. **Global/Client-scoped**: A single registry shared across all sessions (per client or globally)

The choice impacts:
- Memory usage patterns
- Session isolation semantics
- Entity lifecycle management
- Concurrency behavior
- User mental model

The PRD resolved this as "per-session" in OQ-1, but the rationale warrants documentation.

---

## Decision

**Registry scoped to SaveSession instance.**

Each `SaveSession` has its own independent `ChangeTracker` with its own entity registry:

```python
class SaveSession:
    def __init__(self, client: AsanaClient, ...) -> None:
        # Each session gets its own tracker instance
        self._tracker = ChangeTracker()
```

### Implications

1. **Entities tracked in Session A are not visible in Session B**
2. **Same GID can be tracked independently in multiple sessions**
3. **Registry is garbage collected when session exits**
4. **No cross-session entity sharing or synchronization**

### Lifecycle

```
Session A created    --> Tracker A created (empty)
Session A tracks X   --> X in Tracker A
Session B created    --> Tracker B created (empty)
Session B tracks X   --> X in Tracker B (independent copy)
Session A commits    --> X saved, Tracker A marks clean
Session B commits    --> X saved again (no awareness of A's commit)
Session A exits      --> Tracker A garbage collected
```

---

## Rationale

### Why per-session?

1. **Matches ORM patterns**: SQLAlchemy, Django ORM use session-scoped identity maps
2. **Predictable isolation**: Sessions don't interfere with each other
3. **Clear lifecycle**: Registry lives and dies with session
4. **No concurrency complexity**: No locks or synchronization needed
5. **Memory bounded**: Registry size bounded by single session's entities

### Why not global?

1. **Unpredictable side effects**: Tracking in one session affects another
2. **Memory growth**: Registry grows unboundedly across all sessions
3. **Cleanup complexity**: When to evict entities? Reference counting?
4. **Concurrency hazards**: Multiple sessions modifying same entity registry

### Why not client-scoped?

1. **Still has sharing problems**: Multiple sessions per client would share
2. **Client lifecycle unclear**: When does client's registry clear?
3. **Most of global's problems**: Memory growth, concurrency, side effects

---

## Alternatives Considered

### Alternative 1: Global entity registry

- **Description**: Single registry for all entities across all sessions
- **Pros**: True deduplication; any code can find any tracked entity
- **Cons**: Memory leaks; concurrency issues; unclear ownership; surprising behavior
- **Why not chosen**: Violates session isolation principle; too many edge cases

### Alternative 2: Client-scoped registry

- **Description**: One registry per `AsanaClient` instance
- **Pros**: Bounded scope; natural lifecycle
- **Cons**: Sessions sharing state is confusing; still has memory growth
- **Why not chosen**: Sessions within same client should still be isolated

### Alternative 3: Opt-in shared registry

- **Description**: Per-session by default, but allow `SaveSession(shared_registry=True)`
- **Pros**: Flexibility for power users
- **Cons**: Complexity; two modes to test/document; edge cases multiply
- **Why not chosen**: YAGNI; no demonstrated need

### Alternative 4: Weak reference registry (global)

- **Description**: Global registry using weak references; entities evicted when no strong refs
- **Pros**: Automatic cleanup; deduplication without memory growth
- **Cons**: Confusing lifecycle; entity disappears when user doesn't expect; complex
- **Why not chosen**: Too clever; hard to reason about; surprising behavior

---

## Consequences

### Positive

1. **Session isolation**: Sessions are truly independent units of work
2. **Predictable memory**: Registry bounded by session lifetime
3. **Simple mental model**: Track in session, commit session, done
4. **No synchronization**: Thread-safe without locks (sessions not shared)
5. **ORM familiarity**: Developers familiar with Django/SQLAlchemy feel at home

### Negative

1. **No cross-session deduplication**: Same entity tracked twice across sessions means duplicate work
   - *Mitigation*: Document that sessions should be short-lived
2. **Re-track after session exit**: New session requires re-tracking entities
   - *Mitigation*: This is expected behavior; sessions are work units

### Neutral

1. Users can still implement their own cross-session coordination if needed
2. `find_by_gid()` only works within same session (by design)
3. Temp GID transitions are session-local

---

## Compliance

### How to enforce this decision

1. **Code review**: Ensure `ChangeTracker` is instantiated per-session
2. **Architecture tests**: Verify no global registry patterns
3. **Documentation**: Clearly state session-scoped semantics

### Validation

- [ ] Each `SaveSession` creates its own `ChangeTracker`
- [ ] Tracking in Session A doesn't affect Session B's `find_by_gid()`
- [ ] Session exit clears its registry (no memory leak)
- [ ] Concurrent sessions don't interfere

---

## Example: Session Isolation

```python
async def demonstrate_isolation():
    """Sessions are isolated - same GID tracked independently."""

    # Session A tracks and modifies task
    async with SaveSession(client) as session_a:
        task_a = await client.tasks.get_async("12345")
        session_a.track(task_a)
        task_a.name = "Name from A"

        # Session B tracks same GID independently
        async with SaveSession(client) as session_b:
            # session_b.find_by_gid("12345") returns None
            # because B has its own empty registry
            assert session_b.find_by_gid("12345") is None

            task_b = await client.tasks.get_async("12345")
            session_b.track(task_b)
            task_b.notes = "Notes from B"

            # Session B commits its version
            await session_b.commit_async()
            # Task now has notes="Notes from B"

        # Session A commits its version (overwrites notes)
        await session_a.commit_async()
        # Task now has name="Name from A", notes reset to original

    # This is by design: sessions are isolated work units
    # To coordinate, use a single session or external coordination
```
