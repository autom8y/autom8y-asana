# SDK Glossary

> Canonical definitions for autom8_asana-specific terms

---

## Core Concepts

### SaveSession

**Definition**: Unit of Work pattern implementation for batched Asana operations. Collects entity changes and executes them in optimized batches rather than immediately.

**Usage**:
```python
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    await session.commit_async()
```

**Also known as**: Unit of Work, UoW, batch session
**Not to be confused with**: Database session, HTTP session

---

### ActionOperation

**Definition**: An operation that uses Asana's action endpoints (add_tag, move_to_section, etc.) rather than standard CRUD endpoints.

**Types**: `ADD_TAG`, `REMOVE_TAG`, `ADD_TO_PROJECT`, `REMOVE_FROM_PROJECT`, `MOVE_TO_SECTION`, `ADD_DEPENDENCY`, `REMOVE_DEPENDENCY`, `SET_PARENT`

**Why it matters**: Action operations cannot be batched via the /batch endpoint; they execute individually via SaveSession's ActionExecutor.

---

### EntityState

**Definition**: The lifecycle state of a tracked entity within SaveSession.

**States**:
| State | Meaning |
|-------|---------|
| `NEW` | Entity has temp GID, will be created via POST |
| `CLEAN` | Entity tracked but unmodified since last save |
| `MODIFIED` | Entity has pending changes to save |
| `DELETED` | Entity marked for deletion via DELETE |

---

### GID (Global ID)

**Definition**: Asana's globally unique identifier for every resource.

**Format**: Numeric string (e.g., `"1234567890123456"`)
**Temporary GIDs**: `temp_{uuid}` for entities not yet created

---

### ChangeTracker

**Definition**: Component that detects which tracked entities have been modified since their snapshot.

**How it works**: Takes snapshot when `track()` called, compares current state at `commit()` time.

---

### DependencyGraph

**Definition**: Graph structure that orders SaveSession operations based on parent-child relationships.

**Why it matters**: New subtasks must be created after their parent task. Graph ensures correct execution order using Kahn's algorithm for topological sort.

---

### PlannedOperation

**Definition**: A planned operation returned by `session.preview()` before actual execution.

**Contains**: Entity, operation type (CREATE/UPDATE/DELETE), payload, dependency level

---

## API Concepts

### opt_fields

**Definition**: Query parameter requesting specific fields from Asana API.

**Why it matters**: Asana returns minimal data by default. Use opt_fields to expand response.

**Example**: `opt_fields=["name", "completed", "assignee.name"]`

---

### Pagination Cursor

**Definition**: Opaque string pointing to next batch of results in paginated responses.

**Format**: Base64-encoded string (treat as opaque)
**SDK handling**: AsyncIterator automatically fetches next pages

---

### Membership

**Definition**: A task's relationship to a project, including which section it belongs to.

**Structure**: `{"project": {"gid": "..."}, "section": {"gid": "..."}}`

---

### Batch Request

**Definition**: Request to Asana's `/batch` endpoint containing multiple sub-requests.

**Limit**: 10 actions per batch request
**SDK handling**: BatchClient chunks larger batches automatically

---

## SDK Components

### AsanaClient

**Definition**: Main entry point to the SDK. Holds configuration and provides access to resource clients.

**Location**: `src/autom8_asana/client.py`

---

### Resource Client

**Definition**: Type-safe client for a specific Asana resource type (TasksClient, ProjectsClient, etc.).

**Pattern**: All clients provide `list()`, `get()`, `create()`, `update()`, `delete()`

**Location**: `src/autom8_asana/clients/`

---

### CacheProtocol

**Definition**: Abstract interface for cache backends that consumers can implement.

**Methods**: `get()`, `set()`, `delete()`, `clear()`
**Implementations**: InMemoryCache (default), RedisCache (optional)

---

### AuthProtocol

**Definition**: Abstract interface for authentication providers.

**Methods**: `get_token()`, `refresh_token()` (if applicable)
**Implementations**: PAT (Personal Access Token), OAuth (future)

---

### SaveResult

**Definition**: Result object returned by `session.commit()` containing success/failure details.

**Fields**:
- `success`: bool - All operations succeeded
- `succeeded`: list - Successfully saved entities
- `failed`: list - Failed operations with errors
- `gid_map`: dict - Mapping of temp GIDs to real GIDs

---

### ActionResult

**Definition**: Result of a single action operation (add_tag, etc.).

**Fields**: `success`, `task_gid`, `action_type`, `error`

---

## Acronyms

| Acronym | Expansion | Definition |
|---------|-----------|------------|
| GID | Global ID | Asana's unique identifier |
| PAT | Personal Access Token | API authentication method |
| UoW | Unit of Work | Design pattern for batched persistence |
| SDK | Software Development Kit | This library |
