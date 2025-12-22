# autom8_asana Automation Platform

> Async-first Asana client evolving from SDK to full automation platform: Asana as Database + Automation + Pipeline Management.

---

## Activation Triggers

**Use this skill when**:
- Working with SaveSession, Unit of Work, or batch save patterns
- Implementing Business, Contact, Unit, Offer, Address, Hours entities
- Using holder patterns or entity hierarchies
- Detecting entity types from Asana tasks
- Working with cascading or inherited fields
- Adding cache backends or transport layer modifications
- Writing Pydantic v2 models for Asana resources
- **Implementing automation rules or the AutomationEngine**
- **Building pipeline conversion logic (stage advancement triggers)**
- **Working with TemplateDiscovery or fuzzy template matching**
- **Configuring FieldSeeder for cascade or carry-through propagation**
- **Adding post-commit hooks to SaveSession**

**Keywords**: SaveSession, Business, Contact, Unit, Offer, holder, detect_entity_type, cascade_field, ActionOperation, batch operation, async client, custom field, **AutomationRule**, **AutomationEngine**, **PipelineConversionRule**, **TemplateDiscovery**, **FieldSeeder**, **post-commit hook**, **pipeline conversion**, **ProcessType**, **ProcessSection**

**File patterns**: `src/autom8_asana/**/*.py`, `src/autom8_asana/automation/**/*.py`, `tests/**/*.py`

---

## Quick Reference

| I need to... | See |
|--------------|-----|
| Understand SaveSession (Unit of Work) | [persistence.md](persistence.md) |
| Work with Business/Contact/Unit/Offer | [entities.md](entities.md) |
| Detect entity types from tasks | [entities.md#detection](entities.md#detection) |
| Understand transport, cache, clients | [infrastructure.md](infrastructure.md) |
| **Implement automation rules or pipelines** | [automation.md](automation.md) |
| Look up terminology | [glossary.md](glossary.md) |

---

## The Core Insight: Asana as Automation Platform

Think **Asana as Salesforce**: a platform that combines Database + Automation + Pipeline Management.

| Layer | Asana Concept | Platform Analog | Purpose |
|-------|---------------|-----------------|---------|
| **Database** | Task | Row/Record | Each task = one business entity |
| **Database** | Custom Field | Column | 127+ typed fields define schemas |
| **Database** | Subtask | Foreign Key | Holder relationships (Business > Unit > Offer) |
| **Database** | Project | Table/Index | Entity type registry + pipeline stages |
| **Automation** | Post-commit hook | Trigger | Rule execution after SaveSession.commit() |
| **Automation** | AutomationRule | Workflow Rule | Extensible rule interface for custom behavior |
| **Pipeline** | ProcessType enum | Stage | 7 pipeline stages from lead to offboard |
| **Pipeline** | Section | Pipeline Column | Visual state within a project |

### Evolution Path

```
Phase 1 (Current): Asana as Database
  - Entities, holders, SaveSession
  - Detection, custom fields, batch operations

Phase 2 (In Progress): Asana as Automation Platform
  - AutomationEngine with post-commit hooks
  - PipelineConversionRule for stage advancement
  - TemplateDiscovery for fuzzy template matching
  - FieldSeeder for cascade + carry-through
```

The SDK is evolving from pure CRUD to **event-driven automation** where entity changes trigger downstream processes automatically.

---

## Architecture Overview

```
Consumer Applications (autom8 platform, services)
                    |
+------------------------------------------+
|         autom8_asana Platform            |
|  +------------------------------------+  |
|  | Business Model Layer               |  |
|  | Business > Unit > Offer > Process  |  |
|  | Contact, Address, Hours            |  |
|  | 127+ Custom Field Descriptors      |  |
|  +------------------------------------+  |
|  +------------------------------------+  |
|  | Persistence Layer                  |  |
|  | SaveSession (Unit of Work)         |  |
|  | Change Tracking, Batch Operations  |  |
|  | Post-Commit Hooks (extension point)|  |
|  +------------------------------------+  |
|  +------------------------------------+  |
|  | Automation Layer (NEW)             |  |
|  | AutomationEngine, AutomationRule   |  |
|  | PipelineConversionRule             |  |
|  | TemplateDiscovery, FieldSeeder     |  |
|  +------------------------------------+  |
|  +------------------------------------+  |
|  | Detection Layer                    |  |
|  | 5-Tier Entity Type Detection       |  |
|  +------------------------------------+  |
+------------------------------------------+
                    |
            Asana REST API
```

### Automation Flow

```
SaveSession.commit()
        |
        v
  Post-Commit Hook
        |
        v
  AutomationEngine
        |
        +---> Rule 1: PipelineConversionRule
        |         - Detect stage advancement
        |         - Find template via TemplateDiscovery
        |         - Create new Process in next stage
        |         - Seed fields via FieldSeeder
        |
        +---> Rule 2: (Custom rules...)
        |
        v
  Nested SaveSession (automation changes)
```

---

## Entity Hierarchy

```
Business (root, 19 fields)
    +-- ContactHolder --> Contact[] (19 fields)
    +-- UnitHolder --> Unit[] (31 fields, composite)
    |                    +-- OfferHolder --> Offer[] (39 fields)
    |                    +-- ProcessHolder --> Process[]
    +-- LocationHolder
            +-- Address (12 fields)
            +-- Hours (7 fields)
```

All entities inherit from Task. The SDK provides typed wrappers with custom field properties.

---

## Core Pattern: SaveSession

```python
async with client.save_session() as session:
    # 1. Track business (prefetch holders by default)
    session.track(business)
    await session.prefetch_pending()

    # 2. Navigate and modify
    for contact in business.contacts:
        print(contact.full_name)

    business.company_id = "NEW-ID"
    session.track(contact_to_update)
    contact_to_update.contact_email = "new@example.com"

    # 3. Commit all changes
    result = await session.commit_async()
```

See [persistence.md](persistence.md) for complete patterns.

---

## Key Constraints

- **Python 3.10+** (not 3.12+ - must support autom8 runtime)
- **Async-first** with sync wrappers via `sync_wrapper` decorator
- **No business logic in SDK** - pure API wrapper, domain rules stay in consumers
- **Protocol-based DI** - consumers implement `AuthProtocol`, `CacheProtocol`
- **Pydantic v2** for all models
- **httpx** for HTTP transport

---

## Repository Structure

```
src/autom8_asana/
+-- client.py             # AsanaClient (main entry point)
+-- batch/                # Batch API operations
+-- cache/                # CacheProtocol, InMemoryCache, RedisCache
+-- clients/              # Resource clients (tasks, projects, sections...)
+-- models/               # Pydantic v2 resource models
|   +-- business/         # Business entity hierarchy
|       +-- detection.py  # 5-tier entity type detection
|       +-- process.py    # Process entity with ProcessType, ProcessSection
+-- persistence/          # SaveSession (Unit of Work)
|   +-- session.py        # SaveSession class
|   +-- tracker.py        # ChangeTracker
|   +-- graph.py          # DependencyGraph
|   +-- hooks.py          # Post-commit hook protocol (extension point)
+-- automation/           # Automation Layer (NEW)
|   +-- base.py           # AutomationRule protocol, AutomationEngine
|   +-- pipeline.py       # PipelineConversionRule
|   +-- templates.py      # TemplateDiscovery (fuzzy matching)
|   +-- config.py         # AutomationConfig, PipelineConfig
|   +-- seeding.py        # FieldSeeder (cascade + carry-through)
+-- transport/            # HTTP layer, retry, sync wrappers
```

---

## Common Commands

```bash
pip install -e ".[dev]"           # Install dev dependencies
pytest                            # Run tests
pytest --cov=autom8_asana         # Run with coverage
mypy src/autom8_asana             # Type check
ruff check src/ && ruff format src/  # Lint and format
```

---

## Progressive References

| Document | Purpose |
|----------|---------|
| [persistence.md](persistence.md) | SaveSession, post-commit hooks - the ONE canonical source |
| [entities.md](entities.md) | Business hierarchy, detection, ProcessType/ProcessSection |
| [automation.md](automation.md) | AutomationEngine, rules, pipeline conversion, FieldSeeder |
| [infrastructure.md](infrastructure.md) | Transport, cache, resource clients, automation config |
| [glossary.md](glossary.md) | All SDK, business, and automation terminology |
