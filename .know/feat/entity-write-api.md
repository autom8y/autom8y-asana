---
domain: feat/entity-write-api
generated_at: "2026-04-01T16:50:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/api/routes/entity_write.py"
  - "./src/autom8_asana/services/field_write_service.py"
  - "./src/autom8_asana/resolution/field_resolver.py"
  - "./src/autom8_asana/resolution/write_registry.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.88
format_version: "1.0"
---

# Entity Write API (Field Coercion and Partial Success)

## Purpose and Design Rationale

Service-level abstraction for writing business-domain fields to Asana tasks. Resolves human-readable field names to Asana custom field GIDs, coerces types, and supports partial-failure tolerance at the field level.

**ADR-EW-002**: EntityWriteRegistry is additive overlay on EntityRegistry -- does not modify read-path registry. **ADR-EW-003**: FieldResolver extracted from FieldSeeder for reuse. **D-EW-001**: Explicit cache invalidation before refetch when `include_updated=True`. **D-EW-002**: Short numeric strings treated as option names, not GIDs (13+ digits = GID passthrough).

Auth: S2S JWT (`require_service_claims`), bot PAT for Asana communication. Single `tasks.update_async()` call batches all field updates.

## Conceptual Model

### Resolution Priority

Core field (name, assignee, due_on, completed, notes) -> Descriptor index (snake_case O(1)) -> Display name scan (case-insensitive) -> Not found (fuzzy suggestions via difflib).

### Type Coercion

text: passthrough (append mode: comma-delimited merge with dedup). number: passthrough. enum: case-insensitive name lookup -> option GID. multi_enum: per-item resolution (append mode: merge with existing). date: wrapped `{"date": "YYYY-MM-DD"}`. people: passthrough. null: clears field.

### Partial Success Model

Per-field: resolution errors get "skipped"/"error" status but don't block other fields. Request-level failures: all fields fail (422), task not found (404), type mismatch (404), Asana API errors (429/5xx).

### List Mode

`replace` (default): overwrites. `append`: multi_enum merges with existing selections; text comma-splits and deduplicates.

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/api/routes/entity_write.py` | Route: `PATCH /api/v1/entity/{entity_type}/{gid}` (S2S JWT, hidden from schema) |
| `src/autom8_asana/services/field_write_service.py` | 9-step pipeline: registry lookup -> fetch -> verify membership -> resolve -> build payload -> update -> optional refetch -> invalidate |
| `src/autom8_asana/resolution/field_resolver.py` | Stateless per-request resolver with 4-step cascade + enum/multi_enum/text coercion |
| `src/autom8_asana/resolution/write_registry.py` | Auto-discovery registry built at startup from `CustomFieldDescriptor` introspection |
| `src/autom8_asana/services/errors.py` | `TaskNotFoundError`, `EntityTypeMismatchError`, `NoValidFieldsError` |

### EntityWriteRegistry

Built once at startup (lifespan step 11). Introspects entity model classes for `CustomFieldDescriptor` properties. Excludes holders. Entity writable only if it has descriptors AND `primary_project_gid`. Abbreviation-aware display name derivation (mrr -> "MRR", company_id -> "Company ID").

**Test files**: route tests, service pipeline tests, resolver unit tests, integration smoke tests.

## Boundaries and Failure Modes

### Scope Boundaries

- Single GID per request (no batch)
- Write-only (no create)
- No optimistic locking (last write wins)
- Holder entities excluded from registry
- Multi-enum partial resolution is silent (unresolved items logged but don't produce field-level error unless ALL fail)
- Text append uses comma delimiter (no escaping -- values with commas split incorrectly on round-trip)

### Error Paths

| Failure | HTTP | Recovery |
|---------|------|----------|
| Entity type unknown | 404 | Use valid writable type |
| Registry not initialized | 503 | Retry after startup |
| Task not found | 404 | Verify GID |
| Task in wrong project | 404 | Match entity_type to project |
| All fields fail resolution | 422 | Inspect field_results |
| Rate limit | 429 | Use Retry-After header |
| Cache invalidation failure | (none) | Logged warning; TTL expires |

### Two Distinct Cache Invalidation Paths

1. `_cache_invalidate()` on `self._client.tasks` -- per-task cache entry (for refetch freshness)
2. `MutationInvalidator` -- fire-and-forget DataFrame cache invalidation

## Knowledge Gaps

1. `CustomFieldDescriptor` internals (public_name/field_name attributes) not read.
2. Disabled enum option write behavior unclear.
3. `BOT_PAT_UNAVAILABLE` error code origin path not traced.
4. Multi-enum partial resolution edge case test coverage scope unknown.
