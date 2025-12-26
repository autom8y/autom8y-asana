# ADR-0109: Lazy Discovery Timing for WorkspaceProjectRegistry

## Metadata

- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-18
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-WORKSPACE-PROJECT-REGISTRY, ADR-0108 (WorkspaceProjectRegistry Architecture)

## Context

WorkspaceProjectRegistry needs to discover workspace projects to register pipeline projects for Process entity detection. The timing of this discovery is a critical design decision affecting:

1. **Developer Experience**: Explicit init requirements impede DX (PRD constraint)
2. **Latency**: Discovery takes ~1-3 seconds for typical workspace (<100 projects)
3. **API Usage**: Discovery requires Asana API call

**Open Question from PRD (Q2)**: What is the exact lazy discovery trigger point?
- On unknown GID lookup?
- On first detection call?
- On client init?

### Forces

1. **PRD FR-DISC-003**: Discovery can be lazy or automatic, but MUST NOT impede DX
2. **PRD FR-DISC-003**: Explicit-call-only is explicitly rejected
3. **PRD NFR-PERF-001**: Discovery <3 seconds for typical workspace
4. **User Decision**: Projects are stable - no frequent spin-up/spin-down
5. **Existing Pattern**: Detection has sync and async paths
6. **Existing Pattern**: Sync detection does not make API calls

## Decision

We will trigger discovery **on first async detection for an unregistered project GID**, with explicit `discover_async()` available for eager initialization.

### Trigger Point: Async Detection Tier 1

Discovery is triggered inside `lookup_or_discover_async()` when:
1. The project GID is NOT in the static registry
2. Discovery has NOT already been performed
3. An AsanaClient is available (async path only)

```python
# In detection.py (async path)
async def _detect_tier1_project_membership_async(
    task: Task,
    client: AsanaClient,
) -> DetectionResult | None:
    """Tier 1 with lazy workspace discovery."""
    project_gid = _extract_project_gid(task)
    if not project_gid:
        return None

    # Use workspace registry for dynamic discovery
    workspace_registry = get_workspace_registry()
    entity_type = await workspace_registry.lookup_or_discover_async(
        project_gid,
        client,
    )

    if entity_type is None:
        return None

    return DetectionResult(
        entity_type=entity_type,
        confidence=CONFIDENCE_TIER_1,
        tier_used=1,
        needs_healing=False,
        expected_project_gid=project_gid,
    )
```

### Sync Path Unchanged

The synchronous `detect_entity_type()` function continues to use only the static ProjectTypeRegistry:
- No API calls in sync path (existing guarantee)
- Processes in undiscovered pipeline projects fall through to Tier 2+
- Users needing sync detection with full registry should call `discover_async()` first

```python
# detect_entity_type() - UNCHANGED
def detect_entity_type(task: Task, parent_type: EntityType | None = None) -> DetectionResult:
    """Sync detection using static registry only."""
    result = detect_by_project(task)  # Uses ProjectTypeRegistry only
    if result:
        return result
    # ... Tier 2-5 fallbacks
```

### Explicit Discovery API

Consumers can eagerly initialize if desired:

```python
# Eager initialization (optional)
await get_workspace_registry().discover_async(client)

# Or continue with lazy (recommended)
result = await detect_entity_type_async(task, client)  # Discovery happens automatically
```

### Idempotency

Discovery is idempotent - repeated calls refresh the registry:
- First call populates name-to-GID mapping
- Subsequent calls update with any new projects
- Static registrations are never overwritten

```python
async def discover_async(self, client: AsanaClient) -> None:
    """Discover workspace projects (idempotent)."""
    workspace_gid = client.default_workspace_gid
    if not workspace_gid:
        logger.warning("No default workspace GID for discovery")
        return

    # Fetch all projects
    projects = await client.projects.list_async(
        workspace=workspace_gid,
        archived=False,
    ).collect()

    # Register all projects
    self._populate_from_projects(projects)
    self._discovered_workspace = workspace_gid
```

## Rationale

**Why trigger on async detection rather than registry lookup?**
- Detection is the consumer-facing API; registry is internal
- Async detection already has client parameter for API calls
- Clear integration point: detection triggers discovery

**Why not trigger on sync detection?**
- Sync path guarantees no API calls (existing contract)
- Would require converting sync detection to async (breaking change)
- Sync consumers can explicitly call `discover_async()` first if needed

**Why on first unregistered GID rather than every unregistered GID?**
- Discovery populates ALL workspace projects in one API call
- After discovery, any unknown GID is truly unknown (not in workspace)
- Prevents redundant API calls

**Why idempotent refresh rather than fail-if-discovered?**
- Allows explicit refresh: `await registry.refresh_async(client)`
- Handles rare case of projects added during long session
- Simple semantics: "ensure discovered" vs "discover exactly once"

## Alternatives Considered

### Alternative A: Trigger at Client Init (Eager)

- **Description**: Discover when AsanaClient is instantiated
- **Pros**: Predictable timing; no surprise latency on first detection
- **Cons**: API call even if detection not needed; slower client startup
- **Why not chosen**: Lazy is better DX; eager available as explicit option

### Alternative B: Trigger on First Any Detection Call

- **Description**: Discover on first call to `detect_entity_type_async()` regardless of project
- **Pros**: Simpler trigger logic; consistent behavior
- **Cons**: Discovery even for known static projects; unnecessary API calls
- **Why not chosen**: Wasteful for known entities; trigger on unknown GID is more efficient

### Alternative C: Explicit-Only Discovery

- **Description**: Require consumers to call `discover_async()` before detection
- **Pros**: Explicit lifecycle; predictable
- **Cons**: Easy to forget; breaks DX (PRD explicitly rejects this)
- **Why not chosen**: PRD FR-DISC-003 explicitly rejects explicit-call-only

### Alternative D: Background Discovery Thread

- **Description**: Start discovery in background when client initializes
- **Pros**: Async latency hidden; ready when needed
- **Cons**: Complex threading; race conditions; Python GIL limitations
- **Why not chosen**: Complexity outweighs benefits; simple lazy is sufficient

## Consequences

### Positive

- **Good DX**: No explicit initialization required
- **Efficient**: Discovery only when actually needed
- **Sync unchanged**: Existing sync detection code unaffected
- **Explicit option**: `discover_async()` available for eager init
- **Idempotent**: Safe to call multiple times

### Negative

- **First detection latency**: ~1-3 seconds on first unknown GID detection
- **Async only**: Full registry only available in async path
- **Client required**: Discovery needs AsanaClient for API access

### Neutral

- Discovery happens once per process lifetime (projects stable)
- Sync detection continues with static registry only
- Consumers can choose lazy or explicit timing

## Compliance

- Detection MUST trigger discovery on first unregistered GID in async path
- Sync detection MUST NOT trigger discovery (no API calls)
- `discover_async()` MUST be available for explicit initialization
- Discovery MUST be idempotent (refresh, not fail)
- Discovery MUST NOT overwrite static PRIMARY_PROJECT_GID registrations
- First discovery MAY incur 1-3 second latency (acceptable per NFR-PERF-001)
