---
domain: feat/dataframe-layer
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/dataframes/**/*.py"
  - "./src/autom8_asana/api/routes/dataframes.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.82
format_version: "1.0"
---

# Polars DataFrame Analytics Layer

## Purpose and Design Rationale

The DataFrame layer transforms Asana task data into typed, queryable Polars DataFrames. It bridges Asana's schema-free custom fields and downstream consumers (query engine, REST API, export workflows) that require structured tabular data.

**Why Polars**: Strongly-typed, zero-copy columnar format with lazy evaluation. Lazy mode auto-selected above 100 tasks (ADR-0031).
**Why schemas**: Asana custom field GIDs differ across workspaces. `CustomFieldResolver` maps human-readable names to GIDs at runtime.
**Why progressive building**: `ProgressiveProjectBuilder` writes completed sections to S3 parquet immediately, enabling resume after container restarts.
**Why cascade fields**: `cascade:` source prefix enables async parent-chain traversal for inherited fields.

## Conceptual Model

### Schema-Extractor-Builder Pipeline

Schema (ColumnDef list) -> Extractor (per entity type) -> Builder (lazy/eager) -> pl.DataFrame

**Column source taxonomy**: `None` (derived method), `"attr_name"` (direct getattr), `"cf:Name"` (custom field by name), `"gid:123"` (literal GID), `"cascade:Field"` (parent chain traversal).

**7 built-in schemas**: base (13 cols), business, unit, contact, offer, asset_edit, asset_edit_holder. Process schema exists but not registered in API route.

### Cascade Defense-in-Depth (SCAR-005/006/023)

1. Schema enforcement: cascade columns must use `source="cascade:..."` 
2. `parent_gid` in BASE_SCHEMA for S3 resume
3. Post-build `CascadeValidator` (WARN 5%, ERROR 20% null rate)
4. Gap-skipping chain traversal with grandparent fallback
5. `WarmupOrderingError` (immune to broad-catch)

## Implementation Map

~60 files across: builders/ (base, progressive, section, cascade_validator, fields, hierarchy_warmer, parallel_fetch), extractors/ (base + 9 concrete), models/ (registry, schema, task_row), resolver/ (cascading, coercer, default, protocol, normalizer), schemas/ (base + 7 entity schemas), views/ (cascade_view, cf_utils, dataframe_view), plus annotations.py, cache_integration.py, exceptions.py, storage.py, watermark.py, section_persistence.py, offline.py.

### Extractor Factory

Registry-driven (not hardcoded): iterates `EntityRegistry.all_descriptors()`, imports extractor at `descriptor.extractor_class_path`. Falls back to `SchemaExtractor` (dynamic) or `DefaultExtractor` (base only).

## Boundaries and Failure Modes

- `DataFrameConstructionError` -> HTTP 422 via `safe_dataframe_construct()` (SCAR-025 fix)
- Concurrency: `gather_with_limit(max=25)` for extraction, `max_concurrent_sections=8` for progressive build
- Section stale timeout: 5 min for IN_PROGRESS sections on resume (SCAR-002)
- Force-rebuild purge via `POST /admin/force-rebuild` (SCAR-003)

## Knowledge Gaps

1. Process schema API availability unclear (intentional omission or gap).
2. Several builder files not read in full (parallel_fetch pacing model, TaskCacheCoordinator overlap).
3. HierarchyWarmer pre-warming scope not confirmed.
