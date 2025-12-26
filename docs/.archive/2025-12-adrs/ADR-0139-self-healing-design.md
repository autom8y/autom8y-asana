# ADR-0139: Self-Healing Opt-In Design

## Metadata

- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-19
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-TECH-DEBT-REMEDIATION (FR-DET-006), ADR-0095 (Self-Healing Integration), TDD-TECH-DEBT-REMEDIATION

## Context

ADR-0095 established the self-healing integration with SaveSession. This ADR addresses the remaining design question: **Where should self-healing be triggered?**

Options:
1. **Detection layer**: During `detect_entity_type()` calls
2. **Session layer**: During `SaveSession.commit()` (ADR-0095 approach)
3. **Hydration layer**: During business hierarchy hydration
4. **Standalone utility**: Explicit `heal_entity()` function

### Current State (ADR-0095)

ADR-0095 proposes self-healing integrated with SaveSession:
- `SaveSession(auto_heal=True)` enables healing
- Healing executes after normal save operations
- Results reported in `SaveResult.healed_entities` and `SaveResult.healing_failures`

### Gap Analysis

ADR-0095 does not address:
1. **Healing without save**: What if entity needs healing but has no pending changes?
2. **Detection-time healing**: Should we heal during detection, not just commit?
3. **Dry-run mode**: How to preview what would be healed?
4. **Healing scope**: Per-entity, per-session, or global configuration?

## Decision

Implement self-healing with **two trigger points** and **dry-run support**:

1. **SaveSession integration** (ADR-0095): Heal tracked entities during commit
2. **Standalone utility function**: Explicit `heal_entity_async()` for on-demand healing

Detection layer SHALL NOT trigger healing (violates zero-API-call guarantee).

### Architecture

```
                    +-------------------+
                    |   Consumer Code   |
                    +-------------------+
                           |
              +------------+------------+
              |                         |
              v                         v
    +------------------+      +------------------+
    |   SaveSession    |      | heal_entity_async|
    | (auto_heal=True) |      | (standalone)     |
    +------------------+      +------------------+
              |                         |
              v                         v
    +-------------------------------------------+
    |            Healing Execution              |
    | - Check needs_healing flag                |
    | - Validate expected_project_gid           |
    | - Call add_to_project API                 |
    | - Return HealingResult                    |
    +-------------------------------------------+
```

### Trigger Point 1: SaveSession (per ADR-0095)

```python
class SaveSession:
    def __init__(
        self,
        client: AsanaClient,
        auto_heal: bool = False,  # Opt-in
        heal_dry_run: bool = False,  # NEW: Preview mode
    ) -> None:
        self._auto_heal = auto_heal
        self._heal_dry_run = heal_dry_run

    async def commit_async(self) -> SaveResult:
        # 1. Execute normal operations
        result = await self._pipeline.execute()

        # 2. Execute healing (if enabled)
        if self._auto_heal:
            await self._execute_healing(result, dry_run=self._heal_dry_run)

        return result
```

### Trigger Point 2: Standalone Utility

For healing entities without save operations:

```python
async def heal_entity_async(
    entity: BusinessEntity,
    client: AsanaClient,
    dry_run: bool = False,
) -> HealingResult:
    """Heal a single entity by adding to expected project.

    Args:
        entity: Entity with detection result indicating healing needed.
        client: AsanaClient for API calls.
        dry_run: If True, return what would be healed without making changes.

    Returns:
        HealingResult with outcome details.

    Raises:
        ValueError: If entity doesn't need healing or lacks expected_project_gid.

    Example:
        >>> result = detect_entity_type(task)
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
            error=e,
        )
```

### Batch Healing Utility

For healing multiple entities efficiently:

```python
async def heal_entities_async(
    entities: list[BusinessEntity],
    client: AsanaClient,
    dry_run: bool = False,
    max_concurrent: int = 5,
) -> list[HealingResult]:
    """Heal multiple entities with concurrency control.

    Args:
        entities: Entities to heal (only those needing healing are processed).
        client: AsanaClient for API calls.
        dry_run: If True, return what would be healed.
        max_concurrent: Maximum concurrent API calls.

    Returns:
        List of HealingResult for each entity processed.
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
    """Outcome of a healing operation."""
    entity_gid: str
    expected_project_gid: str
    success: bool
    dry_run: bool
    error: Exception | None

    def __bool__(self) -> bool:
        """True if healing succeeded or was a successful dry run."""
        return self.success
```

### Dry-Run Mode

Enables previewing healing actions before execution:

```python
# Preview what would be healed
async with client.save_session(auto_heal=True, heal_dry_run=True) as session:
    session.track(entity)
    result = await session.commit_async()
    print(f"Would heal: {result.healed_entities}")  # Dry-run list

# Execute actual healing
async with client.save_session(auto_heal=True) as session:
    session.track(entity)
    result = await session.commit_async()
    print(f"Healed: {result.healed_entities}")  # Actually healed
```

### Why Detection Layer is NOT a Trigger Point

Detection functions (`detect_entity_type()`, `detect_entity_type_async()`) SHALL NOT trigger healing because:

1. **Zero-API guarantee**: Tiers 1-3 promise no API calls; healing requires API
2. **Side effects**: Detection is a query; healing is a command (CQS violation)
3. **Caller control**: Consumer should decide when/if to heal
4. **Testability**: Detection should be deterministic without network

## Alternatives Considered

### Alternative A: Detection-Time Healing (Auto-Heal in detect_entity_type_async)

- **Description**: Optionally heal during async detection
- **Pros**: Immediate repair; single call heals
- **Cons**: Violates detection's read-only nature; surprises caller; breaks CQS
- **Why not chosen**: Detection should be query-only

### Alternative B: Hydration-Time Healing

- **Description**: Heal entities during business hierarchy hydration
- **Pros**: Natural integration point; entities loaded = ready to heal
- **Cons**: Hydration is also read-focused; adds complexity to hydration flow
- **Why not chosen**: Hydration should remain read-focused

### Alternative C: Global Auto-Heal Configuration

- **Description**: `AsanaClient(auto_heal=True)` enables healing globally
- **Pros**: Simple configuration; applies everywhere
- **Cons**: Too broad; no control; may heal unexpectedly
- **Why not chosen**: Per-session/per-call control is safer

### Alternative D: Healing Middleware

- **Description**: Register healing as request/response middleware
- **Pros**: Transparent; extensible
- **Cons**: Healing is not a request/response concern; middleware is wrong abstraction
- **Why not chosen**: Middleware is for cross-cutting HTTP concerns

## Consequences

### Positive

- **Two clear trigger points**: SaveSession and standalone utility
- **Dry-run support**: Preview healing before execution
- **No detection pollution**: Detection remains side-effect-free
- **Batch support**: `heal_entities_async()` for multiple entities
- **Consumer control**: Opt-in at session or call level

### Negative

- **Two APIs to learn**: SaveSession healing vs standalone healing (documented clearly)
- **Manual detection required**: Must call `detect_entity_type()` before standalone healing

### Neutral

- Builds on ADR-0095 SaveSession integration
- HealingResult type added to persistence module
- Detection layer unchanged

## Compliance

- Detection functions (`detect_entity_type`, `detect_entity_type_async`) MUST NOT call healing
- SaveSession healing MUST be disabled by default (`auto_heal=False`)
- Dry-run mode MUST be available via `heal_dry_run=True`
- Standalone `heal_entity_async()` MUST validate detection result before healing
- Batch healing MUST use semaphore for concurrency control
- All healing operations MUST be logged with structured logging
- Tests MUST cover: SaveSession healing, standalone healing, dry-run mode, batch healing
