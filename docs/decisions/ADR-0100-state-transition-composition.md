# ADR-0100: State Transition Composition with SaveSession

## Metadata
- **Status**: Superseded by [ADR-0101](ADR-0101-process-pipeline-correction.md)
- **Author**: Architect
- **Date**: 2025-12-17
- **Deciders**: Architect, Requirements Analyst
- **Related**: [PRD-PROCESS-PIPELINE](../requirements/PRD-PROCESS-PIPELINE.md), [TDD-PROCESS-PIPELINE](../design/TDD-PROCESS-PIPELINE.md), [ADR-0097](ADR-0097-processsection-state-machine.md)

---

## Context

Process entities need to move between pipeline states (Opportunity -> Active -> Converted). In Asana, this is a "move to section" operation. SaveSession already provides `move_to_section()`:

```python
session.move_to_section(task, section_gid)
```

**Forces at play**:

1. **Developer ergonomics**: Working with ProcessSection enum is nicer than raw GIDs
2. **Reuse existing primitives**: SaveSession already handles section moves
3. **Section GID lookup**: Need to map ProcessSection -> section_gid
4. **Extension vs. composition**: Add new SaveSession method vs. Process helper method
5. **Error handling**: What if section GID not configured?

SaveSession is the central persistence API. Adding methods to it should be done sparingly.

---

## Decision

**Compose state transitions via Process.move_to_state() helper that wraps SaveSession.move_to_section().**

**Do NOT add new methods to SaveSession.**

**Section GID lookup uses ProcessProjectRegistry.**

The implementation:

1. **Process.move_to_state() method**:
   ```python
   def move_to_state(
       self,
       session: SaveSession,
       target_state: ProcessSection,
   ) -> SaveSession:
       # Determine process_type from current pipeline membership
       # Look up section GID from ProcessProjectRegistry
       # Delegate to session.move_to_section()
       # Return session for fluent chaining
   ```

2. **ProcessProjectRegistry.get_section_gid()**:
   ```python
   def get_section_gid(
       self,
       process_type: ProcessType,
       section: ProcessSection,
   ) -> str | None:
       # Return configured section GID or None
       # Configuration via ASANA_SECTION_{TYPE}_{SECTION} env var
   ```

3. **Error handling**:
   ```python
   # ValueError if process not in pipeline project
   if process_type == ProcessType.GENERIC:
       raise ValueError("Cannot move_to_state: Process not in registered pipeline")

   # ValueError if section GID not configured
   if section_gid is None:
       raise ValueError(f"Section '{target_state.value}' not found...")
   ```

---

## Rationale

**Why composition over extension?**

| Approach | Pros | Cons |
|----------|------|------|
| Extend SaveSession | Discoverable on session | Bloats SaveSession API, Process-specific in generic class |
| Process helper method | Domain-appropriate, keeps SaveSession focused | Less discoverable |

SaveSession is a generic persistence layer. Adding Process-specific methods would:
- Break single responsibility
- Create precedent for other entity-specific methods
- Bloat the SaveSession API

Process.move_to_state() is domain-appropriate: it's a Process operation, not a generic task operation.

**Why require section GID configuration?**

While we could query sections via API, this would:
- Require async operation in a sync context
- Add latency to every state transition
- Require caching logic

Environment variable configuration:
- Matches ProcessProjectRegistry pattern
- Fast O(1) lookup
- Explicit (configuration visible in deployment)
- Cacheable (set at startup)

**Why ValueError for unconfigured sections?**

Failing fast with clear message:
- Reveals configuration issues immediately
- Error message guides fix ("Set ASANA_SECTION_SALES_CONVERTED=...")
- Consumer can catch ValueError if they expect this possibility

Alternative (return False, log warning) would hide configuration issues.

**Why return SaveSession?**

Enables fluent chaining:
```python
process.move_to_state(session, ProcessSection.CONVERTED)
session.track(other_entity)
await session.commit_async()
```

Consistent with SaveSession method signatures.

---

## Alternatives Considered

### Alternative 1: Extend SaveSession with move_to_state()

- **Description**: Add `SaveSession.move_to_state(process, target_state)` method
- **Pros**: Discoverable on session, consistent with other session methods
- **Cons**: Process-specific logic in generic class, bloats SaveSession, violates SRP
- **Why not chosen**: SaveSession should remain entity-agnostic

### Alternative 2: Dynamic Section Lookup via API

- **Description**: Query sections from project when move_to_state() called
- **Pros**: No configuration needed, always up-to-date
- **Cons**: Adds latency, requires async, needs caching
- **Why not chosen**: Configuration is acceptable, avoids API complexity

### Alternative 3: Process Subclass per Type

- **Description**: SalesProcess.move_to_converted() with hardcoded section logic
- **Pros**: Type-specific methods, no section lookup
- **Cons**: Explosion of classes and methods, not flexible
- **Why not chosen**: Over-engineering; enum + registry is sufficient

### Alternative 4: Standalone Function

- **Description**: `move_process_to_state(session, process, target_state)` function
- **Pros**: Doesn't pollute Process class
- **Cons**: Less discoverable, not fluent, separate import
- **Why not chosen**: Process method is more ergonomic and discoverable

---

## Consequences

**Positive**:
- SaveSession remains focused and entity-agnostic
- Process.move_to_state() is domain-appropriate
- Reuses existing move_to_section() implementation
- Fast section lookup via configuration
- Clear error messages for misconfiguration

**Negative**:
- Requires section GID configuration per environment
- Less discoverable than SaveSession method
- Configuration errors surface at runtime

**Neutral**:
- Process gains new method (acceptable coupling)
- Fluent chaining preserved
- Consumer can still use move_to_section() directly if preferred

---

## Compliance

- [ ] move_to_state() queues move_to_section action per FR-TRANS-001
- [ ] Section lookup uses current process_type per FR-TRANS-002
- [ ] ValueError for non-pipeline process per FR-TRANS-003
- [ ] ValueError for missing section per FR-TRANS-004
- [ ] Section GIDs configurable via env vars per FR-TRANS-005
- [ ] No new SaveSession methods added
- [ ] Returns SaveSession for fluent chaining
- [ ] Error messages include actionable information
