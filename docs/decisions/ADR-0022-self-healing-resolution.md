# ADR-0022: Self-Healing Resolution System

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Deciders**: SDK Team
- **Consolidated From**: ADR-0095, ADR-0139, ADR-0144
- **Related**: [reference/DETECTION.md](reference/DETECTION.md), ADR-0020, PRD-DETECTION

## Context

Entities detected via Tiers 2-5 lack proper project membership, causing future detection to rely on fallback heuristics rather than the fast, deterministic Tier 1 path. To ensure future detections succeed via Tier 1 (O(1), 100% confidence), we need to "heal" these entities by adding them to their expected project.

### Business Value of Self-Healing

**Without self-healing**:
- Entity detected via Tier 2 (name pattern, 60% confidence, ~1ms)
- Every future detection repeats Tier 2 fallback
- Name changes or decorations can break detection
- No path to "upgrade" entity to Tier 1 detection

**With self-healing**:
- Entity detected via Tier 2 on first access
- Healing adds project membership automatically
- Future detections succeed via Tier 1 (100% confidence, <1ms)
- System self-corrects toward optimal state

### Design Challenges

1. **Trigger criteria**: When should healing be triggered?
2. **Opt-in vs automatic**: Should healing be explicit or transparent?
3. **Failure handling**: What happens when healing fails?
4. **Result visibility**: How should consumers know healing occurred?
5. **Integration point**: Where in the SDK lifecycle does healing fit?

## Decision

We will implement self-healing with **two trigger points**, **opt-in design**, **additive-only operations**, and **non-blocking failures**.

### Architecture: Two Trigger Points

```
┌─────────────────────┐
│   Consumer Code     │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
    v             v
┌───────────────┐ ┌────────────────────┐
│  SaveSession  │ │ heal_entity_async  │
│ (auto_heal)   │ │   (standalone)     │
└───────┬───────┘ └────────┬───────────┘
        │                  │
        v                  v
    ┌────────────────────────────┐
    │   Healing Execution        │
    │ - Check needs_healing flag │
    │ - Validate expected_gid    │
    │ - Call add_to_project API  │
    │ - Return HealingResult     │
    └────────────────────────────┘
```

**Trigger Point 1**: SaveSession integration (automatic with tracked entities)
**Trigger Point 2**: Standalone utility (explicit for single/batch healing)

### Trigger Point 1: SaveSession Integration

Heal tracked entities automatically during commit when enabled:

```python
class SaveSession:
    def __init__(
        self,
        client: AsanaClient,
        batch_size: int = 10,
        max_concurrent: int = 15,
        auto_heal: bool = False,  # Opt-in
        heal_dry_run: bool = False,  # Preview mode
    ) -> None:
        self._auto_heal = auto_heal
        self._heal_dry_run = heal_dry_run
        self._entity_heal_flags: dict[str, bool] = {}

    def track(
        self,
        entity: AsanaResource,
        heal: bool | None = None,  # Per-entity override
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

    async def commit_async(self) -> SaveResult:
        # 1. Execute normal operations (CREATE, UPDATE, DELETE)
        result = await self._pipeline.execute()

        # 2. Execute healing operations (if enabled)
        if self._auto_heal:
            await self._execute_healing(result, dry_run=self._heal_dry_run)

        return result
```

**Healing execution** happens AFTER normal save operations:

```python
async def _execute_healing(self, result: SaveResult, dry_run: bool) -> None:
    """Execute healing operations for entities needing repair."""
    for entity in self._tracker.get_all():
        heal_flag = self._entity_heal_flags.get(entity.gid)
        if not self._should_heal(entity, heal_flag):
            continue

        detection = entity._detection_result
        try:
            if not dry_run:
                await self._client.tasks.add_to_project_async(
                    entity.gid,
                    project_gid=detection.expected_project_gid,
                )
            result.healed_entities.append(entity.gid)
            logger.info(
                "Healed entity",
                entity_gid=entity.gid,
                project_gid=detection.expected_project_gid,
                dry_run=dry_run,
            )
        except Exception as e:
            result.healing_failures.append(
                HealingResult(
                    entity_gid=entity.gid,
                    expected_project_gid=detection.expected_project_gid,
                    success=False,
                    dry_run=False,
                    error=str(e),
                )
            )
            logger.warning(
                "Healing failed",
                entity_gid=entity.gid,
                error=str(e),
            )
```

### Trigger Point 2: Standalone Utility

Heal entities without save operations:

```python
async def heal_entity_async(
    entity: BusinessEntity,
    client: AsanaClient,
    dry_run: bool = False,
) -> HealingResult:
    """Heal a single entity by adding to expected project.

    Args:
        entity: Entity with detection result indicating healing needed
        client: AsanaClient for API calls
        dry_run: If True, return what would be healed without making changes

    Returns:
        HealingResult with outcome details

    Raises:
        ValueError: If entity doesn't need healing or lacks expected_project_gid

    Example:
        >>> result = await detect_entity_type_async(task, client)
        >>> if result.needs_healing:
        ...     healing = await heal_entity_async(entity, client)
        ...     print(f"Healed: {healing.success}")
    """
    # Validate healing is needed
    detection = getattr(entity, "_detection_result", None)
    if detection is None:
        raise ValueError(f"Entity {entity.gid} has no detection result")
    if not detection.needs_healing:
        raise ValueError(f"Entity {entity.gid} does not need healing")
    if not detection.expected_project_gid:
        raise ValueError(f"Entity {entity.gid} has no expected_project_gid")

    if dry_run:
        return HealingResult(
            entity_gid=entity.gid,
            expected_project_gid=detection.expected_project_gid,
            success=True,
            dry_run=True,
            error=None,
        )

    try:
        await client.tasks.add_to_project_async(
            entity.gid,
            project_gid=detection.expected_project_gid,
        )
        return HealingResult(
            entity_gid=entity.gid,
            expected_project_gid=detection.expected_project_gid,
            success=True,
            dry_run=False,
            error=None,
        )
    except Exception as e:
        return HealingResult(
            entity_gid=entity.gid,
            expected_project_gid=detection.expected_project_gid,
            success=False,
            dry_run=False,
            error=str(e),
        )
```

### Batch Healing Utility

```python
async def heal_entities_async(
    entities: list[BusinessEntity],
    client: AsanaClient,
    dry_run: bool = False,
    max_concurrent: int = 5,
) -> list[HealingResult]:
    """Heal multiple entities with concurrency control.

    Args:
        entities: Entities to heal (only those needing healing are processed)
        client: AsanaClient for API calls
        dry_run: If True, return what would be healed
        max_concurrent: Maximum concurrent API calls

    Returns:
        List of HealingResult for each entity processed
    """
    # Filter to entities needing healing
    to_heal = [
        e for e in entities
        if hasattr(e, "_detection_result")
        and e._detection_result
        and e._detection_result.needs_healing
        and e._detection_result.expected_project_gid
    ]

    if not to_heal:
        return []

    # Execute with semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)

    async def heal_one(entity: BusinessEntity) -> HealingResult:
        async with semaphore:
            return await heal_entity_async(entity, client, dry_run)

    return await asyncio.gather(*[heal_one(e) for e in to_heal])
```

### Result Types

```python
@dataclass(frozen=True, slots=True)
class HealingResult:
    """Outcome of a healing operation.

    Consolidated from ADR-0144 to use string errors for serializability.
    """
    entity_gid: str
    expected_project_gid: str
    success: bool
    dry_run: bool
    error: str | None  # String error message, not Exception

    def __bool__(self) -> bool:
        """True if healing succeeded or was a successful dry run."""
        return self.success


@dataclass
class SaveResult:
    # ... existing fields ...

    # Healing outcomes
    healed_entities: list[str] = field(default_factory=list)
    healing_failures: list[HealingResult] = field(default_factory=list)

    @property
    def healing_success(self) -> bool:
        """True if all healing operations succeeded."""
        return len(self.healing_failures) == 0
```

### Healing Trigger Criteria

Healing is triggered when ALL conditions are met:

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

### Dry-Run Mode

Preview healing actions without executing:

```python
# Preview what would be healed
async with SaveSession(client, auto_heal=True, heal_dry_run=True) as session:
    session.track(entity)
    preview = await session.commit()
    print(f"Would heal: {preview.healed_entities}")

# Execute actual healing
async with SaveSession(client, auto_heal=True) as session:
    session.track(entity)
    result = await session.commit()
    print(f"Healed: {result.healed_entities}")

# Standalone dry-run
healing = await heal_entity_async(entity, client, dry_run=True)
print(f"Would heal {healing.entity_gid} → {healing.expected_project_gid}")
```

## Rationale

### Why Two Trigger Points?

| Scenario | SaveSession | Standalone |
|----------|-------------|------------|
| Healing during save | ✓ Automatic | Manual call needed |
| Healing without changes | Manual session needed | ✓ Direct |
| Batch healing | Multiple tracks | ✓ heal_entities_async |
| Preview before commit | ✓ dry_run flag | ✓ dry_run flag |

Two trigger points serve different use cases:
- **SaveSession**: Natural integration for entities being modified
- **Standalone**: Explicit healing for orphaned entities or batch repair

### Why Opt-In (Not Automatic)?

- **Principle of least surprise**: Healing modifies entity state (adds project membership)
- **Existing consumers**: Should not get surprise behavior on upgrade
- **Explicit control**: Consumer decides when healing is appropriate
- **Testing**: Easier to test when behavior is explicit

### Why Additive-Only (Never Remove)?

- **Safety**: Removing project memberships could break workflows
- **Multi-project entities**: Entity may legitimately be in multiple projects
- **Domain knowledge required**: Deciding which memberships to remove requires business context
- **Idempotency**: Adding to a project entity is already in is safe (no-op)

### Why Execute After Normal Operations?

- **Entity must exist**: CREATE operations must complete first
- **GID resolution**: Temporary GIDs must be resolved to real GIDs
- **Clean separation**: Save operations succeed independently of healing
- **Failure isolation**: Healing failures don't fail saves

### Why Non-Blocking Failures?

- **Healing is supplementary**: Not critical to save operation success
- **Consumer loses data if save fails**: Should get save results even if healing fails
- **Retry is consumer responsibility**: Consumer can inspect failures and retry
- **Observability**: All failures logged and reported in SaveResult

### Why Detection Layer is NOT a Trigger Point

Detection functions SHALL NOT trigger healing because:

1. **Zero-API guarantee**: Tiers 1-3 promise no API calls; healing requires API
2. **Command-Query Separation**: Detection is a query; healing is a command
3. **Caller control**: Consumer should decide when/if to heal
4. **Testability**: Detection should be deterministic without network

## Alternatives Considered

### Alternative A: Automatic Healing (No Opt-In)

Always heal entities needing repair.

**Why not chosen**:
- Violates principle of least surprise
- May not be desired in all contexts
- Testing becomes harder (unexpected API calls)

### Alternative B: Detection-Time Healing

Optionally heal during `detect_entity_type_async()`.

**Why not chosen**:
- Violates detection's read-only nature
- Breaks Command-Query Separation
- Adds side effects to query operation

### Alternative C: Healing via Batch Pipeline

Add healing as ActionOperation through existing batch system.

**Why not chosen**:
- `add_to_project` doesn't batch well
- Healing volume doesn't justify pipeline complexity
- Sequential execution acceptable for expected volume

### Alternative D: Blocking Failures

`commit_async()` raises if any healing fails.

**Why not chosen**:
- Could lose save results
- Healing is supplementary to core saves
- Consumer should decide if healing failure is critical

### Alternative E: Global Auto-Heal Configuration

`AsanaClient(auto_heal=True)` enables healing globally.

**Why not chosen**:
- Too broad; no per-operation control
- May heal unexpectedly in some code paths
- Per-session/per-call control is safer

## Consequences

### Positive

- **Opt-in safety**: No surprise behavior for existing consumers
- **Two use cases served**: SaveSession (integrated) + standalone (explicit)
- **Observable**: Full visibility into healing outcomes via SaveResult
- **Non-destructive**: Only adds memberships; never removes
- **Resilient**: Healing failures don't break saves
- **Dry-run capable**: Preview before execution
- **Batch support**: `heal_entities_async()` for multiple entities
- **Self-correcting**: System upgrades entities to Tier 1 over time

### Negative

- **Two APIs to learn**: SaveSession vs standalone (mitigated by documentation)
- **Sequential execution**: Healing ops not batched (acceptable for expected volume)
- **Detection required**: Entity must have detection result (typical flow)
- **API calls**: Each healing is one API call (acceptable; healing is rare)

### Neutral

- SaveResult gains two new fields (`healed_entities`, `healing_failures`)
- SaveSession gains two new constructor parameters (`auto_heal`, `heal_dry_run`)
- `track()` gains one new optional parameter (`heal`)
- HealingResult type added to persistence module

## Compliance

How do we ensure this decision is followed?

1. **Healing MUST be disabled by default** (`auto_heal=False`) - verified by unit tests
2. **Healing MUST be additive-only** (never remove memberships) - enforced by implementation
3. **Healing failures MUST be logged as warnings** - verified by log assertions
4. **Healing failures MUST NOT raise from `commit_async()`** - verified by exception tests
5. **Detection functions MUST NOT trigger healing** - verified by mock assertions
6. **Dry-run MUST NOT make API calls** - verified by mock call counts
7. **`SaveResult.healed_entities` MUST contain GIDs** - verified by integration tests
8. **`SaveResult.healing_failures` MUST contain HealingResult** - verified by schema tests

## Implementation Notes

**SaveSession integration example**:

```python
# Opt-in healing during commit
async with SaveSession(client, auto_heal=True) as session:
    session.track(entity)  # Detection result must have needs_healing=True
    result = await session.commit()

    if result.healed_entities:
        logger.info(f"Healed {len(result.healed_entities)} entities")

    if result.healing_failures:
        for failure in result.healing_failures:
            logger.warning(f"Failed to heal {failure.entity_gid}: {failure.error}")
```

**Standalone healing example**:

```python
# Heal specific entity
result = await detect_entity_type_async(task, client)
if result.needs_healing:
    healing = await heal_entity_async(entity, client)
    if not healing.success:
        logger.error(f"Healing failed: {healing.error}")

# Batch healing
entities = await fetch_orphaned_entities()
results = await heal_entities_async(entities, client, max_concurrent=5)
success_count = sum(1 for r in results if r.success)
```

**Error handling**:

```python
result = await session.commit()

for failure in result.healing_failures:
    if "already in project" in failure.error:
        # Idempotent - entity already healed
        continue
    elif "permission denied" in failure.error:
        # Escalate to user
        await notify_permission_issue(failure.entity_gid)
    else:
        # Retry with exponential backoff
        await retry_healing(failure)
```
