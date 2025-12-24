# Platform Infrastructure

> Transport, cache, resource clients, automation configuration, and repository organization.

---

## Table of Contents

1. [Repository Map](#repository-map)
2. [Resource Clients](#resource-clients)
3. [Transport Layer](#transport-layer)
4. [Cache Layer](#cache-layer)
5. [Batch API](#batch-api)
6. [Automation Configuration](#automation-configuration)
7. [Tech Stack](#tech-stack)

---

## Repository Map

```
src/autom8_asana/
+-- __init__.py           # Public API exports
+-- client.py             # AsanaClient (main entry point)
+-- config.py             # Configuration dataclasses
+-- exceptions.py         # SDK exception hierarchy
|
+-- batch/                # Batch API operations
|   +-- client.py         # BatchClient for /batch endpoint
|   +-- models.py         # BatchRequest, BatchResult
|
+-- cache/                # Caching layer
|   +-- protocol.py       # CacheProtocol interface
|   +-- backends/
|       +-- memory.py     # InMemoryCache (default)
|       +-- redis.py      # RedisCache (optional)
|
+-- clients/              # Resource-specific API clients
|   +-- base.py           # BaseClient with common methods
|   +-- tasks.py          # TasksClient
|   +-- projects.py       # ProjectsClient
|   +-- sections.py       # SectionsClient
|   +-- custom_fields.py  # CustomFieldsClient
|   +-- tags.py, users.py, teams.py, workspaces.py...
|
+-- models/               # Pydantic v2 resource models
|   +-- base.py           # AsanaResource base class
|   +-- task.py, project.py, section.py...
|   +-- business/         # Business entity hierarchy
|       +-- detection.py  # 5-tier entity type detection
|       +-- registry.py   # ProjectTypeRegistry singleton
|       +-- process.py    # Process, ProcessType, ProcessSection
|       +-- business.py, contact.py, unit.py, offer.py...
|
+-- persistence/          # SaveSession (Unit of Work)
|   +-- session.py        # SaveSession class
|   +-- tracker.py        # ChangeTracker
|   +-- graph.py          # DependencyGraph (Kahn's algorithm)
|   +-- pipeline.py       # SavePipeline
|   +-- hooks.py          # PostCommitHook protocol
|   +-- action_executor.py
|
+-- automation/           # Automation Layer (NEW)
|   +-- base.py           # AutomationRule protocol, AutomationEngine
|   +-- pipeline.py       # PipelineConversionRule
|   +-- templates.py      # TemplateDiscovery (fuzzy matching)
|   +-- config.py         # AutomationConfig, PipelineConfig
|   +-- seeding.py        # FieldSeeder (cascade + carry-through)
|
+-- transport/            # HTTP layer
    +-- retry.py          # Retry with exponential backoff
    +-- sync.py           # sync_wrapper decorator
```

### Where to Put New Code

| Creating... | Location |
|-------------|----------|
| New Asana resource client | `clients/{resource}.py` |
| New Pydantic model | `models/{resource}.py` |
| Business entity model | `models/business/{entity}.py` |
| Cache backend | `cache/backends/{backend}.py` |
| SaveSession feature | `persistence/` |
| Protocol interface | `protocols/{protocol}.py` |
| New automation rule | `automation/{rule}.py` |
| Automation config | `automation/config.py` |

---

## Resource Clients

All resource clients follow a consistent pattern with `list()`, `get()`, `create()`, `update()`, `delete()`.

### Usage

```python
# List with filters and opt_fields
tasks = await client.tasks.list(project_gid, opt_fields=["name", "completed"])

# Get single resource
task = await client.tasks.get(task_gid)

# Create
new_task = await client.tasks.create({"name": "New Task", "projects": [project_gid]})

# Update
await client.tasks.update(task_gid, {"name": "Updated Name"})

# Delete
await client.tasks.delete(task_gid)
```

### opt_fields

Asana returns minimal data by default. Use `opt_fields` to expand responses:

```python
opt_fields=["name", "completed", "assignee.name", "custom_fields"]
```

### Pagination

Resource clients return `AsyncIterator` for list operations. Pagination is automatic:

```python
async for task in client.tasks.list(project_gid):
    print(task.name)
```

---

## Transport Layer

### Async-First Pattern

All primary interfaces are async. Sync wrappers provided via decorator:

```python
# Primary (use this)
async def commit_async(self) -> SaveResult: ...

# Sync wrapper (auto-generated)
def commit(self) -> SaveResult:
    return sync_wrapper(self.commit_async)()
```

**Convention**: Async methods end with `_async` suffix. Sync wrappers omit it.

### Retry with Backoff

Transport layer handles retry with exponential backoff on 429 (rate limit) responses.

### Rate Limits

| Limit | Value |
|-------|-------|
| Requests per minute | 1,500 per PAT |
| Batch actions | 10 per request |
| Concurrent connections | 50 recommended |

---

## Cache Layer

### CacheProtocol

SDK defines the protocol; consumers implement:

```python
class CacheProtocol(Protocol):
    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def clear(self) -> None: ...
```

### Implementations

| Backend | Use Case |
|---------|----------|
| `InMemoryCache` | Default, single-process |
| `RedisCache` | Multi-process, distributed |
| `S3Cache` | Persistent, cross-session |

### TaskCacheCoordinator

For DataFrame builds, a specialized coordinator manages Task-level caching:

```python
from autom8_asana.dataframes.builders.task_cache import TaskCacheCoordinator

coordinator = TaskCacheCoordinator(cache_provider)

# Batch lookup (returns hits + miss GIDs)
result = await coordinator.lookup_tasks_async(task_gids)
# result.cached_tasks: list[Task]  - cache hits
# result.miss_gids: list[str]      - GIDs not in cache

# Populate after fetch
await coordinator.populate_tasks_async(fetched_tasks)

# Merge cached + fetched
all_tasks = coordinator.merge_results(result.cached_tasks, fetched_tasks)
```

### Cache Population Strategy (ADR-0130)

Cache population occurs at **builder level** after API fetch:

```
1. Enumerate GIDs (lightweight API call)
2. Batch cache lookup
3. Fetch only cache misses (targeted API calls)
4. Populate cache with fetched tasks
5. Return merged results
```

**Key Insight**: Population at builder level enables graceful degradation - cache failures never break the primary fetch path.

### Path Selection

| Cache State | Path | API Calls |
|-------------|------|-----------|
| Cold (0% hit) | `fetch_all()` | All sections |
| Partial | `fetch_by_gids()` | Miss GIDs only |
| Warm (100% hit) | Skip fetch | 0 (GID enum only) |

### Performance Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| Warm fetch latency | <1s | <1s |
| Cache hit rate | >90% | 100% on warm |
| API calls (warm) | 0 | 0 |

---

## Batch API

### BatchClient

Chunks operations for Asana's `/batch` endpoint (max 10 per request):

```python
# SDK handles chunking automatically
batch_client = client.batch
results = await batch_client.execute(operations)
```

### Action Operations

Some operations use action endpoints (not batchable):

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Add tag | `POST /tasks/{gid}/addTag` | `session.add_tag()` |
| Remove tag | `POST /tasks/{gid}/removeTag` | `session.remove_tag()` |
| Add to project | `POST /tasks/{gid}/addProject` | `session.add_to_project()` |
| Move to section | `POST /tasks/{gid}/setParent` | `session.move_to_section()` |
| Add dependency | `POST /tasks/{gid}/addDependencies` | `session.add_dependency()` |

---

## Automation Configuration

The automation layer uses dataclass-based configuration for type safety and validation.

### AutomationConfig

Top-level configuration for the AutomationEngine:

```python
from dataclasses import dataclass, field
from autom8_asana.automation.config import AutomationConfig, PipelineConfig

@dataclass
class AutomationConfig:
    """Configuration for the AutomationEngine."""

    enabled: bool = True
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    dry_run: bool = False  # Log actions without executing
    max_rules_per_commit: int = 100  # Safety limit
```

### PipelineConfig

Configuration for pipeline conversion rules:

```python
@dataclass
class PipelineConfig:
    """Configuration for pipeline conversion automation."""

    # Stage advancement settings
    enabled_stages: list[ProcessType] = field(
        default_factory=lambda: list(ProcessType)
    )
    auto_advance: bool = True

    # Template discovery settings
    template_project_suffix: str = " Templates"
    fuzzy_match_threshold: float = 0.8  # 0.0-1.0

    # Field seeding settings
    cascade_fields: list[str] = field(default_factory=list)
    carry_through_fields: list[str] = field(default_factory=list)
```

### Configuration Patterns

**Environment-based configuration**:

```python
import os
from autom8_asana.automation.config import AutomationConfig, PipelineConfig

config = AutomationConfig(
    enabled=os.getenv("AUTOMATION_ENABLED", "true").lower() == "true",
    dry_run=os.getenv("AUTOMATION_DRY_RUN", "false").lower() == "true",
    pipeline=PipelineConfig(
        fuzzy_match_threshold=float(
            os.getenv("TEMPLATE_MATCH_THRESHOLD", "0.8")
        ),
    ),
)
```

**Per-environment configs**:

```python
# Development: dry run, verbose logging
dev_config = AutomationConfig(dry_run=True)

# Production: full automation
prod_config = AutomationConfig(
    pipeline=PipelineConfig(
        cascade_fields=["office_phone", "company_id"],
        carry_through_fields=["vertical", "platforms"],
    ),
)
```

### Rule-Specific Configuration

Each rule type may define its own config dataclass:

```python
@dataclass
class PipelineConversionRuleConfig:
    """Configuration specific to PipelineConversionRule."""

    source_stage: ProcessType
    target_stage: ProcessType
    template_project_gid: str | None = None  # Override auto-discovery
    field_mapping: dict[str, str] = field(default_factory=dict)
```

---

## Tech Stack

### Runtime Dependencies

| Package | Purpose |
|---------|---------|
| **httpx** >=0.25.0 | Async HTTP client |
| **pydantic** >=2.0.0 | Type-safe models |
| **polars** >=0.20.0 | DataFrame operations |
| **arrow** >=1.3.0 | Date/time handling |

### Dev Dependencies

| Package | Purpose |
|---------|---------|
| **pytest** + **pytest-asyncio** | Testing |
| **mypy** | Type checking |
| **ruff** | Linting and formatting |
| **respx** | httpx mocking |

### Configuration

```toml
# pytest
[tool.pytest.ini_options]
asyncio_mode = "auto"

# mypy
[tool.mypy]
python_version = "3.10"
strict = true

# ruff
[tool.ruff]
line-length = 88
target-version = "py310"
```

---

## Exception Hierarchy

```python
AsanaSDKError          # Base
+-- AsanaAPIError      # API response errors
|   +-- RateLimitError # 429 with retry_after
+-- SessionClosedError # Operation on closed SaveSession
```

Usage:

```python
try:
    result = await session.commit_async()
except RateLimitError as e:
    await asyncio.sleep(e.retry_after or 60)
except AsanaAPIError as e:
    logger.error(f"API error {e.status_code}: {e.errors}")
```
