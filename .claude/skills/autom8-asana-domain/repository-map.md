# Repository Map

> Where SDK code lives and how it's organized

---

## Package Structure

```
src/autom8_asana/
|
+-- __init__.py           # Public API exports
+-- client.py             # AsanaClient (main entry point)
+-- config.py             # Configuration dataclasses
+-- exceptions.py         # SDK exception hierarchy
+-- _compat.py            # Python version compatibility
|
+-- batch/                # Batch API operations
|   +-- client.py         # BatchClient for /batch endpoint
|   +-- models.py         # BatchRequest, BatchResult, BatchSummary
|
+-- cache/                # Caching layer
|   +-- protocol.py       # CacheProtocol interface
|   +-- backends/         # Cache implementations
|       +-- memory.py     # InMemoryCache (default)
|       +-- redis.py      # RedisCache (optional)
|
+-- clients/              # Resource-specific API clients
|   +-- base.py           # BaseClient with common methods
|   +-- tasks.py          # TasksClient
|   +-- projects.py       # ProjectsClient
|   +-- sections.py       # SectionsClient
|   +-- custom_fields.py  # CustomFieldsClient
|   +-- tags.py           # TagsClient
|   +-- users.py          # UsersClient
|   +-- teams.py          # TeamsClient
|   +-- workspaces.py     # WorkspacesClient
|   +-- webhooks.py       # WebhooksClient
|   +-- attachments.py    # AttachmentsClient
|   +-- goals.py          # GoalsClient
|   +-- portfolios.py     # PortfoliosClient
|   +-- stories.py        # StoriesClient
|
+-- dataframes/           # Polars DataFrame layer
|   +-- ...               # DataFrame conversion utilities
|
+-- models/               # Pydantic v2 resource models
|   +-- base.py           # AsanaResource base class
|   +-- common.py         # NameGid, pagination types
|   +-- task.py           # Task model
|   +-- project.py        # Project model
|   +-- section.py        # Section model
|   +-- custom_field.py   # CustomField, CustomFieldValue
|   +-- tag.py            # Tag model
|   +-- user.py           # User model
|   +-- team.py           # Team model
|   +-- workspace.py      # Workspace model
|   +-- webhook.py        # Webhook model
|   +-- attachment.py     # Attachment model
|   +-- goal.py           # Goal model
|   +-- portfolio.py      # Portfolio model
|   +-- story.py          # Story model
|
+-- observability/        # Logging, metrics, tracing
|   +-- ...               # Observability utilities
|
+-- persistence/          # SaveSession (Unit of Work)
|   +-- session.py        # SaveSession class
|   +-- tracker.py        # ChangeTracker (dirty detection)
|   +-- models.py         # EntityState, PlannedOperation, SaveResult
|   +-- graph.py          # DependencyGraph (Kahn's algorithm)
|   +-- pipeline.py       # SavePipeline (execution orchestration)
|   +-- executor.py       # Batch execution
|   +-- action_executor.py # Action endpoint execution
|   +-- events.py         # Event hooks (pre-save, post-save)
|   +-- exceptions.py     # Persistence-specific exceptions
|
+-- protocols/            # Abstract interfaces for DI
|   +-- auth.py           # AuthProtocol
|   +-- ...               # Other protocols
|
+-- transport/            # HTTP layer
    +-- retry.py          # Retry with exponential backoff
    +-- sync.py           # sync_wrapper for sync wrappers
    +-- ...               # Connection pooling, etc.
```

---

## Where to Put New Code

| I'm creating... | Put it in... |
|-----------------|--------------|
| New Asana resource client | `clients/{resource}.py` |
| New Pydantic model | `models/{resource}.py` |
| Cache backend implementation | `cache/backends/{backend}.py` |
| SaveSession feature | `persistence/` |
| Transport modification | `transport/` |
| New protocol interface | `protocols/{protocol}.py` |
| SDK-level exception | `exceptions.py` |
| Persistence exception | `persistence/exceptions.py` |

---

## Tests Structure

```
tests/
|
+-- conftest.py           # Shared fixtures
+-- unit/                 # Pure logic tests (no I/O)
|   +-- test_models.py
|   +-- test_tracker.py
|   +-- test_graph.py
|   +-- ...
|
+-- integration/          # Tests requiring mocked HTTP
    +-- test_client.py
    +-- test_batch.py
    +-- ...
```

---

## Key Entry Points

| What | Location |
|------|----------|
| Main client | `client.py` -> `AsanaClient` |
| SaveSession | `persistence/session.py` -> `SaveSession` |
| Resource models | `models/*.py` |
| Resource clients | `clients/*.py` |
| Batch operations | `batch/client.py` -> `BatchClient` |

---

## Module Dependencies

```
AsanaClient (client.py)
    |
    +-- ResourceClients (clients/*.py)
    |       |
    |       +-- Transport (transport/)
    |       +-- Models (models/*.py)
    |
    +-- SaveSession (persistence/session.py)
    |       |
    |       +-- ChangeTracker (persistence/tracker.py)
    |       +-- DependencyGraph (persistence/graph.py)
    |       +-- SavePipeline (persistence/pipeline.py)
    |       +-- ActionExecutor (persistence/action_executor.py)
    |
    +-- BatchClient (batch/client.py)
    |
    +-- CacheProtocol (cache/protocol.py)
            |
            +-- InMemoryCache (cache/backends/memory.py)
            +-- RedisCache (cache/backends/redis.py)
```
