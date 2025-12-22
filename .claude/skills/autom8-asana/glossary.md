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
