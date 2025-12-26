# ADR-0104: Loop Prevention Strategy

## Status

Accepted

## Context

Automation rules can trigger other rules (cascade effect). Without safeguards, this creates potential for:
1. **Circular references**: Rule A triggers Rule B which triggers Rule A
2. **Unbounded recursion**: Rule chains that never terminate
3. **Resource exhaustion**: API rate limits exceeded from runaway automation

**Requirements**:
- FR-011: Max cascade depth configuration
- FR-012: Visited set tracking prevents same trigger twice
- NFR-002: Respect Asana rate limits

**Options Considered**:

1. **Option A: Depth Limit Only** - Simple counter, stop at max depth
2. **Option B: Visited Set Only** - Track (entity_gid, rule_id) pairs
3. **Option C: Dual Protection** - Both depth limit AND visited set

## Decision

**We will use Option C: Dual Protection.**

AutomationContext tracks both:
- `depth: int` - Current cascade depth (compared against `max_cascade_depth`)
- `visited: set[tuple[str, str]]` - Set of (entity_gid, rule_id) already processed

Both checks must pass for automation to continue.

## Consequences

### Positive

- **Defense in Depth**: Two independent safeguards catch different failure modes
- **Clear Semantics**: Depth prevents unbounded chains; visited prevents true cycles
- **Debuggability**: Skipped reasons clearly indicate which safeguard triggered
- **Configurability**: max_cascade_depth can be tuned per use case

### Negative

- **Memory**: Visited set grows with chain length (bounded by depth)
- **Complexity**: Two mechanisms to understand and maintain

### Implementation

```python
@dataclass
class AutomationContext:
    client: AsanaClient
    config: AutomationConfig
    depth: int = 0
    visited: set[tuple[str, str]] = field(default_factory=set)

    def can_continue(self, entity_gid: str, rule_id: str) -> bool:
        # Depth check
        if self.depth >= self.config.max_cascade_depth:
            return False

        # Visited check
        if (entity_gid, rule_id) in self.visited:
            return False

        return True

    def child_context(self) -> AutomationContext:
        """Create child with depth+1, shared visited set."""
        return AutomationContext(
            client=self.client,
            config=self.config,
            depth=self.depth + 1,
            visited=self.visited,  # Shared reference
        )
```

### Skip Reasons

When automation is skipped, AutomationResult includes `skipped_reason`:
- `"max_depth_exceeded"` - depth >= max_cascade_depth
- `"circular_reference_prevented"` - (entity_gid, rule_id) already visited

## References

- TDD-AUTOMATION-LAYER (Loop Prevention Flow diagram)
- PRD-AUTOMATION-LAYER (FR-011, FR-012, NFR-002)
- Risk Assessment: Circular trigger loops
