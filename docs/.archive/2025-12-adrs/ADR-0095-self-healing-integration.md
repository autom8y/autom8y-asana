# ADR-0095: Self-Healing Integration with SaveSession

## Metadata

- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-17
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-DETECTION, TDD-DETECTION, ADR-0035 (Unit of Work), ADR-0093, ADR-0094

## Context

Entities detected via Tiers 2-5 lack proper project membership, causing detection to rely on fallback heuristics. To ensure future detection succeeds via Tier 1 (deterministic, O(1)), we need to "heal" these entities by adding them to their expected project.

**Key design questions:**

1. **Trigger criteria**: When should healing be triggered?
2. **Operation batching**: Should healing operations go through the batch pipeline?
3. **Result reporting**: How should healing outcomes be reported to consumers?
4. **Failure handling**: What happens when healing fails?

### Forces

1. **Non-destructive**: Healing should only add memberships, never remove (safety)
2. **Opt-in**: Consumers must explicitly enable healing (no surprises)
3. **Observable**: Healing outcomes must be visible in SaveResult
4. **Non-blocking**: Healing failures should not fail the overall commit
5. **Batched**: Healing should leverage existing batching infrastructure
6. **Idempotent**: Adding to a project the entity is already in should be safe

## Decision

We will implement self-healing as an **opt-in SaveSession feature** with **additive-only operations**, executed **after normal save operations** and **reported in SaveResult**.

### Healing Trigger Criteria

Healing is triggered when ALL conditions are met:

1. `SaveSession(auto_heal=True)` is set
2. Entity is a `BusinessEntity` subclass
3. Entity has `needs_healing=True` from detection
4. `expected_project_gid` is not None
5. Per-entity override `heal=False` was not specified

```python
def _should_heal(self, entity: AsanaResource, entity_heal_flag: bool | None) -> bool:
    """Determine if entity should be healed."""
    # Check session-level flag
    if not self._auto_heal:
        return False

    # Check per-entity override
    if entity_heal_flag is False:
        return False

    # Must be a BusinessEntity
    if not isinstance(entity, BusinessEntity):
        return False

    # Must have detection result with healing needed
    detection = getattr(entity, "_detection_result", None)
    if detection is None or not detection.needs_healing:
        return False

    # Must have expected project GID
    if detection.expected_project_gid is None:
        return False

    return True
```

### SaveSession API Changes

```python
class SaveSession:
    def __init__(
        self,
        client: AsanaClient,
        batch_size: int = 10,
        max_concurrent: int = 15,
        auto_heal: bool = False,  # NEW
    ) -> None:
        self._auto_heal = auto_heal
        self._entity_heal_flags: dict[str, bool] = {}

    def track(
        self,
        entity: AsanaResource,
        heal: bool | None = None,  # NEW: per-entity override
    ) -> None:
        """Track entity for persistence.

        Args:
            entity: Entity to track
            heal: Override auto_heal for this entity
                  None = use session default
                  True = force healing
                  False = skip healing
        """
        # ... existing tracking logic ...

        if heal is not None:
            self._entity_heal_flags[entity.gid] = heal
```

### Healing Execution

Healing operations execute **after** normal save operations complete, using the existing `add_to_project` action:

```python
async def commit_async(self) -> SaveResult:
    # 1. Execute normal operations (CREATE, UPDATE, DELETE)
    result = await self._pipeline.execute()

    # 2. Execute healing operations (if enabled)
    if self._auto_heal:
        await self._execute_healing(result)

    return result

async def _execute_healing(self, result: SaveResult) -> None:
    """Execute healing operations for entities needing repair."""
    for entity in self._tracker.get_all():
        heal_flag = self._entity_heal_flags.get(entity.gid)
        if not self._should_heal(entity, heal_flag):
            continue

        detection = entity._detection_result
        try:
            await self._client.tasks.add_to_project_async(
                entity.gid,
                project_gid=detection.expected_project_gid,
            )
            result.healed_entities.append(entity.gid)
            logger.info(
                "Healed entity %s: added to project %s",
                entity.gid,
                detection.expected_project_gid,
            )
        except Exception as e:
            result.healing_failures.append(
                HealingFailure(
                    entity_gid=entity.gid,
                    expected_project_gid=detection.expected_project_gid,
                    error=e,
                )
            )
            logger.warning(
                "Healing failed for entity %s: %s",
                entity.gid,
                str(e),
            )
```

### Result Reporting

```python
@dataclass
class HealingFailure:
    """A failed healing operation."""
    entity_gid: str
    expected_project_gid: str
    error: Exception


@dataclass
class SaveResult:
    # ... existing fields ...

    # NEW: Healing outcomes
    healed_entities: list[str] = field(default_factory=list)
    healing_failures: list[HealingFailure] = field(default_factory=list)

    @property
    def healing_success(self) -> bool:
        """True if all healing operations succeeded."""
        return len(self.healing_failures) == 0
```

### Failure Handling

Healing failures are **non-blocking**:

1. Individual healing failures are logged as warnings
2. Failures are collected in `SaveResult.healing_failures`
3. Overall `commit_async()` does not raise on healing failure
4. Consumer can inspect `result.healing_failures` for retry logic

```python
result = await session.commit_async()

if result.healing_failures:
    for failure in result.healing_failures:
        logger.error(
            "Could not heal %s: %s",
            failure.entity_gid,
            failure.error,
        )
    # Consumer decides whether to retry
```

## Rationale

**Why opt-in via `auto_heal=True`?**
- Healing modifies entity state (adds project membership)
- Existing consumers should not get surprise behavior
- Explicit opt-in follows principle of least surprise

**Why per-entity override?**
- Some entities may intentionally lack project membership
- Consumers may want to heal some entities but not others
- Override pattern is common (e.g., `commit(dry_run=True)`)

**Why additive-only (no removal)?**
- Removing project memberships could break workflows
- Entity may legitimately be in multiple projects
- Adding is always safe; removing requires domain knowledge

**Why execute after normal operations?**
- Entity may not exist yet (CREATE must complete first)
- GID resolution must be complete (temp GIDs resolved)
- Clean separation of concerns (save first, heal second)

**Why not batch healing operations?**
- `add_to_project` is not a batch-supported endpoint
- Healing is expected to be rare (most entities are healthy)
- Sequential execution is acceptable for small numbers

**Why non-blocking failures?**
- Healing is supplementary to core save operations
- Consumer should not lose their save if healing fails
- Retry logic is consumer's responsibility

## Alternatives Considered

### Alternative A: Automatic Healing (No Opt-In)

- **Description**: Always heal entities needing repair
- **Pros**: No configuration needed; entities always correct
- **Cons**: Surprise behavior; may not be desired in all contexts
- **Why not chosen**: Violates principle of least surprise; explicit is better

### Alternative B: Healing via Batch Pipeline

- **Description**: Add healing as ActionOperation through existing batch system
- **Pros**: Consistent with other action operations
- **Cons**: `add_to_project` doesn't batch well; complicates pipeline
- **Why not chosen**: Healing volume doesn't justify complexity

### Alternative C: Blocking Failures (Raise on Heal Failure)

- **Description**: `commit_async()` raises if any healing fails
- **Pros**: Ensures all entities are healed or explicitly fails
- **Cons**: Could lose save results; healing is supplementary
- **Why not chosen**: Save should succeed even if healing fails

### Alternative D: Separate heal() Method

- **Description**: `session.heal_async()` separate from `commit_async()`
- **Pros**: Complete separation of concerns; explicit
- **Cons**: Consumer must remember to call both; easy to forget
- **Why not chosen**: Integration with commit is more ergonomic

### Alternative E: Healing as Middleware/Hook

- **Description**: Register healing as post-save hook
- **Pros**: Leverages existing event system; extensible
- **Cons**: Healing is core enough to warrant first-class support
- **Why not chosen**: Hook system is for consumer customization; healing is SDK feature

## Consequences

### Positive

- **Opt-in safety**: No surprise behavior for existing consumers
- **Observable**: Full visibility into healing outcomes via SaveResult
- **Non-destructive**: Only adds memberships; never removes
- **Resilient**: Healing failures don't break saves
- **Ergonomic**: Single `commit_async()` handles save and heal

### Negative

- **Sequential execution**: Healing ops not batched (acceptable for expected volume)
- **Detection required**: Entity must have been detected before tracking (typical flow)
- **API calls**: Each healing op is one API call (acceptable; healing is rare)

### Neutral

- SaveResult gains two new fields (`healed_entities`, `healing_failures`)
- SaveSession gains one new constructor parameter (`auto_heal`)
- `track()` gains one new optional parameter (`heal`)

## Compliance

- Healing MUST be disabled by default (`auto_heal=False`)
- Healing MUST be additive-only (never remove project memberships)
- Healing failures MUST be logged as warnings
- Healing failures MUST NOT raise exceptions from `commit_async()`
- `SaveResult.healed_entities` MUST contain GIDs of successfully healed entities
- `SaveResult.healing_failures` MUST contain details of failed healing attempts
- Tests MUST verify healing execution order (after normal save)
- Tests MUST verify per-entity override behavior
