# Glossary

> Unified terminology for autom8_asana platform (SDK + Automation).

---

## Core Concepts

### SaveSession
Unit of Work pattern. Collects entity changes, executes in optimized batches.

### Business Entity
Typed wrapper around Asana Task with custom field properties. Types: Business, Contact, Unit, Offer, Address, Hours.

### Holder
Task subtask grouping related children. Types: ContactHolder, UnitHolder, LocationHolder, OfferHolder, ProcessHolder.

### GID (Global ID)
Asana's unique identifier. Format: numeric string. Temporary GIDs: `temp_{uuid}`.

---

## Persistence Terms

### ChangeTracker
Snapshots on `track()`, compares at `commit()` to detect dirty entities.

### DependencyGraph
Orders SaveSession operations. Parents save before children (Kahn's algorithm).

### EntityState
Lifecycle state: `NEW` (temp GID, will POST), `CLEAN` (unmodified), `MODIFIED` (pending changes), `DELETED`.

### ActionOperation
Operation using action endpoints: `ADD_TAG`, `REMOVE_TAG`, `ADD_TO_PROJECT`, `MOVE_TO_SECTION`, `ADD_DEPENDENCY`, `SET_PARENT`.

### SaveResult
Commit result: `success`, `succeeded`, `failed`, `gid_map` (temp to real GIDs).

---

## Detection Terms

### Detection Tier
Method for identifying entity type (1-5): project membership, name pattern, parent inference, structure inspection, unknown.

### ProjectTypeRegistry
Singleton mapping project GIDs to EntityTypes for O(1) Tier 1 lookups.

### DetectionResult
Result: `entity_type`, `confidence` (0.0-1.0), `tier_used`, `needs_healing`, `expected_project_gid`.

### Self-Healing
Auto-registration when lower tiers succeed but Tier 1 would fail. Enables future O(1) lookups.

---

## Entity Terms

### Composite Entity
Entity that is both child and parent. Unit is composite: under UnitHolder, contains OfferHolder/ProcessHolder.

### Sibling Relationship
Address and Hours are siblings under LocationHolder. Cross-reference via `address.hours`, `hours.address`.

### HOLDER_KEY_MAP
Class attribute mapping holder property names to (name_pattern, emoji) tuples.

---

## Field Terms

### Cascading Field
Value propagated from parent to descendants. Stored redundantly for O(1) read. Example: office_phone.

### Inherited Field
Resolved from parent chain at read time. Not stored on child. Example: vertical on Offer.

### allow_override
Cascade flag. False: always overwrite. True: skip non-null descendants.

---

## API Terms

### opt_fields
Query parameter requesting specific fields from Asana API.

### Pagination Cursor
Opaque string for next page. SDK handles automatically via AsyncIterator.

### Membership
Task's relationship to project, including section. Multi-homing: task in multiple projects.

### Batch Request
Request to `/batch` endpoint. Limit: 10 actions per request.

---

## Protocol Terms

### AuthProtocol
Interface for token providers. Implementations: PAT (Personal Access Token), OAuth.

### CacheProtocol
Interface for cache backends. Methods: `get()`, `set()`, `delete()`, `clear()`. Implementations: InMemoryCache, RedisCache.

---

## Cache Terms

### EntryType
Enum defining cache entry categories. 15 types: TASK, SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS, DATAFRAME, PROJECT, SECTION, USER, CUSTOM_FIELD, DETECTION, PROJECT_SECTIONS, GID_ENUMERATION. Location: `cache/entry.py`.

### CacheEntry
Dataclass representing cached data. Fields: `key`, `data`, `entry_type`, `version`, `cached_at`, `ttl`. Methods: `is_expired()`, `is_current(version)`.

### TTL (Time-To-Live)
Seconds until cache entry expires. Entity-specific values in `config.py:DEFAULT_ENTITY_TTLS`. Range: 60s (process) to 3600s (business).

### TaskCacheCoordinator
Encapsulates task-level cache operations for DataFrame builds. Methods: `lookup_tasks_async()`, `populate_tasks_async()`, `merge_results()`. Location: `dataframes/builders/task_cache.py`.

### GID Enumeration
Lightweight fetch of task GIDs only (not full task data). Cached separately via `GID_ENUMERATION` entry type to enable fast warm fetches. Key learning: caching this enabled 187x speedup.

### Two-Phase Cache Strategy
Pattern for cache-aware fetching: enumerate GIDs (lightweight) → batch cache lookup → fetch only misses → batch cache populate → merge results.

### Graceful Degradation
Cache failure handling pattern. Cache failures log WARNING and return empty result; primary operation continues. Never blocks or fails due to cache unavailability.

### Cache Invalidation
Removing stale entries after mutations. SaveSession invalidates all relevant entry types for modified GIDs on commit.

### Warm Fetch
Second fetch of same data (cache populated). Performance target: <1s. Achieved: 0.11s (187x improvement).

### Cold Fetch
First fetch when cache is empty. Performance same as uncached (~11-20s for large projects).

---

## Automation Terms

### AutomationEngine
Post-commit hook consumer that orchestrates rule execution. Receives SaveResult after commit, evaluates rules against changed entities, spawns nested SaveSessions for automation changes.

### AutomationRule
Protocol for automation rules. Methods: `should_trigger(entity, result)` and `execute(session, entity, result)`. Implementations: PipelineConversionRule, custom rules.

### PipelineConversionRule
Rule that triggers when a Process reaches COMPLETE section. Creates new Process in next pipeline stage using TemplateDiscovery and FieldSeeder.

### TemplateDiscovery
Service for finding template tasks in target stage projects. Uses fuzzy matching (configurable threshold) to locate templates by name pattern. Templates define default field values for new Processes.

### FieldSeeder
Component that propagates field values to newly created Processes. Two modes:
- **Cascade**: Copy specific fields from source to target (e.g., office_phone)
- **Carry-through**: Inherit contextual fields from parent hierarchy (e.g., vertical from Unit)

### Post-Commit Hook
Extension point on SaveSession. Protocol method `on_commit(session, result)` called after successful commit. Primary consumer: AutomationEngine.

### Pipeline Conversion
Automatic creation of a new Process when an existing Process advances to COMPLETE. The core automation use case.

---

## Pipeline Terms

### ProcessType
Enum representing the 7 pipeline stages: LEAD, SALES, ONBOARDING, PRODUCTION, RETENTION, OFFBOARDING, ARCHIVE. Each Process has exactly one ProcessType.

### ProcessSection
Enum representing visual state within a stage: BACKLOG, IN_PROGRESS, BLOCKED, REVIEW, COMPLETE. Maps to Asana project sections.

### PipelineState
Computed property on Process combining ProcessType and ProcessSection. Used by automation rules to detect advancement eligibility.

### Stage Advancement
Movement from one ProcessType to the next (e.g., SALES to ONBOARDING). Triggers when Process section becomes COMPLETE and ProcessType is not terminal.

### Terminal Stage
ARCHIVE ProcessType. Processes in terminal stage cannot advance further.

---

## Configuration Terms

### AutomationConfig
Top-level configuration dataclass for AutomationEngine. Contains enabled flag, dry_run mode, PipelineConfig, and safety limits.

### PipelineConfig
Configuration for pipeline conversion: enabled stages, template discovery settings (project suffix, fuzzy threshold), field seeding settings (cascade/carry-through field lists).

### Dry Run
Automation mode where rules evaluate and log actions without executing. Useful for testing automation logic.

---

## Acronyms

| Acronym | Expansion |
|---------|-----------|
| GID | Global ID |
| PAT | Personal Access Token |
| UoW | Unit of Work |
| MRR | Monthly Recurring Revenue |
