---
domain: feat/resource-clients
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/clients/**/*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.91
format_version: "1.0"
---

# Asana Resource Clients

## Purpose and Design Rationale

The resource clients subsystem (`src/autom8_asana/clients/`) is the Infrastructure layer's primary abstraction over the Asana REST API. It translates raw HTTP exchanges into typed Python operations, shields the codebase from API specifics, and enforces cross-cutting behaviors (caching, retry, rate limiting) on every outbound call.

Core design rationale: typed returns by default with `raw=True` opt-out; async-primary with sync twin via `@async_method`; cache check-before-HTTP/store-on-miss pattern (ADR-0119); SRP decomposition via extracted helpers; GID validation before network calls; `PageIterator[T]` for all list operations; `opt_fields` carried universally with guaranteed `parent.gid` inclusion.

## Conceptual Model

### Two Tiers

**Tier 1 (core, full cache)**: `TasksClient`, `ProjectsClient`, `SectionsClient`, `UsersClient`, `WorkspacesClient`, `CustomFieldsClient`

**Tier 2 (auxiliary)**: `WebhooksClient`, `GoalsClient`, `PortfoliosClient`, `TagsClient`, `StoriesClient`, `AttachmentsClient`, `TeamsClient`

**Utilities**: `BaseClient`, `NameResolver`, `TaskOperations`, `TaskTTLResolver`, `GoalRelationships`, `GoalFollowers`

### Cache Integration

Five clients (tasks, projects, sections, users, custom fields) integrate with the cache provider following the 6-step pattern: validate GID -> check cache -> return hit -> fetch API -> store -> return model. Cache failures always degrade gracefully.

### TTL Strategy

TasksClient uses entity-type-aware TTL via `TaskTTLResolver`: Business 3600s, Contact/Unit 900s, Offer 180s, Process 60s, generic 300s.

## Implementation Map

19 files in `src/autom8_asana/clients/`: base.py, tasks.py (929 lines), projects.py (551), sections.py (442), users.py (228), workspaces.py (132), webhooks.py (372), goals.py (502), portfolios.py (587), tags.py (377), stories.py (597), attachments.py (486), teams.py (299), custom_fields.py (715), task_operations.py (334), task_ttl.py (107), name_resolver.py (296), goal_followers.py (194), goal_relationships.py (299).

### Decorator Stack Pattern

```python
@async_method     # outermost: generates sync wrapper
@error_handler    # inner: translates transport errors
async def get(self, ...) -> Model | dict[str, Any]:
```

## Boundaries and Failure Modes

- **Cache failure**: degraded mode (log + continue to API), never error
- **Rate limiting**: AIMD adaptive semaphore in transport; `RateLimitError` after exhaustion
- **GID validation**: `GidValidationError` raised pre-network for malformed GIDs
- **Missing `@error_handler`** on some Tier 2 clients: transport errors propagate raw
- **`add_members` serialization**: `",".join(members)` may be incorrect (string vs array) -- potential bug in ProjectsClient, PortfoliosClient, GoalFollowers

## Knowledge Gaps

1. **`BatchClient`** interface and interaction with resource clients not observed.
2. **`clients/data/` (`DataServiceClient`)**: 14-file sub-package not in scope.
3. **`@error_handler` internal logic**: Not read directly.
4. **`load_stories_incremental()` merge logic**: Opaque from this reading.
