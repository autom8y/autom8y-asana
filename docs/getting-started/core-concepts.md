# Core Concepts

Before using the autom8_asana SDK, you need to understand four fundamental abstractions. This guide builds the mental model you'll use when working with business data in Asana.

## The Entity Hierarchy

The SDK models business data as a nested tree of Asana tasks. Each node in the tree represents a different business concept.

```
Business
  └── UnitHolder
        └── Unit
              ├── OfferHolder
              │     └── Offer
              ├── ContactHolder
              │     └── Contact
              └── ProcessHolder
                    └── Process
```

### What Each Entity Represents

| Entity | Business Meaning | Example |
|--------|-----------------|---------|
| **Business** | Customer account or company | "Acme Dental Clinic" |
| **Unit** | Location or service line | "Downtown Office" |
| **Offer** | Ad campaign or placement | "Facebook Lead Generation - Teeth Whitening" |
| **Contact** | Patient or lead | "John Smith - New Patient Inquiry" |
| **Process** | Workflow or procedure | "New Patient Onboarding - Jan 2024" |

### Holders: The Invisible Containers

Notice the tree includes "Holder" nodes: `UnitHolder`, `OfferHolder`, `ContactHolder`, `ProcessHolder`. These are parent tasks that group children.

**Key characteristics:**
- Holders exist in Asana as tasks but have no business meaning themselves
- You don't create or interact with holders directly
- The SDK manages them automatically when you work with their children
- Each holder's name follows the pattern `[Entity Type]s` (e.g., "Units", "Offers")

**Example in Asana UI:**
```
Business: Acme Dental Clinic
  ├── Units
  │     ├── Downtown Office
  │     └── Suburbs Office
  ├── Contacts
  │     ├── John Smith
  │     └── Jane Doe
  ...
```

The "Units" and "Contacts" tasks are holders. They organize the hierarchy but don't carry business data.

## Custom Fields and Descriptors

Asana custom fields store structured data on tasks. The SDK exposes these as Python properties using descriptors.

### Field Types

The SDK provides six descriptor types, each handling conversion between Python and Asana's API:

```python
from autom8_asana.models.business import Business, Offer

class Business(BusinessEntity):
    company_id = TextField()           # str | None
    mrr = NumberField()                # Decimal | None
    vertical = EnumField()             # str | None (single selection)
    platforms = MultiEnumField()       # list[str] (multi-selection)
    num_units = IntField()             # int | None
    contract_end_date = DateField()    # Arrow | None
```

| Descriptor | Python Type | Asana Type | Use Case |
|-----------|-------------|------------|----------|
| `TextField` | `str \| None` | Text | Names, IDs, URLs |
| `NumberField` | `Decimal \| None` | Number | Currency, percentages (precise math) |
| `IntField` | `int \| None` | Number | Counts, durations (truncates decimals) |
| `EnumField` | `str \| None` | Enum (single-select) | Categories, statuses |
| `MultiEnumField` | `list[str]` | Multi-Enum | Tags, platforms, features |
| `DateField` | `Arrow \| None` | Date | Due dates, start dates |

### Name Derivation

Custom field descriptors auto-derive the Asana field name from the Python property name:

```python
class Offer(BusinessEntity):
    campaign_id = TextField()          # Maps to "Campaign ID"
    weekly_ad_spend = NumberField()    # Maps to "Weekly Ad Spend"
    num_ai_copies = IntField()         # Maps to "Num AI Copies"
```

**Rules:**
1. Convert `snake_case` to `Title Case`
2. Preserve known abbreviations in uppercase: `id` → `ID`, `url` → `URL`, `ai` → `AI`
3. Override with explicit `field_name` parameter when needed

```python
mrr = NumberField(field_name="MRR")  # Explicit override
```

### Reading Field Values

Access custom fields as properties:

```python
business = await client.tasks.get_async("business_gid")

# Read fields
company_id = business.company_id        # str | None
revenue = business.mrr                  # Decimal | None
vertical = business.vertical            # str | None ("Medical", "Dental", etc.)
platforms = business.platforms          # list[str] (e.g., ["Facebook", "Google"])
```

### Writing Field Values

Modify fields through assignment within a SaveSession:

```python
from autom8_asana.persistence import SaveSession
from decimal import Decimal

async with SaveSession(client) as session:
    session.track(business)

    # Update fields
    business.company_id = "ACME-001"
    business.mrr = Decimal("5000.00")
    business.vertical = "Medical"
    business.platforms = ["Facebook", "Google"]

    await session.commit_async()
```

**Important:** Fields must be modified within a SaveSession after calling `track()`. Direct assignment outside a session has no effect.

## SaveSession Pattern

The SaveSession implements the Unit of Work pattern for batched operations. Think of it as a "shopping cart" for changes.

### Why Use SaveSession?

Without SaveSession, each change requires a separate API call:

```python
# ❌ Inefficient: 3 separate API calls
await client.tasks.update_async(task.gid, name="New Name")
await client.tasks.add_tag_async(task.gid, tag_gid)
await client.tasks.update_async(task.gid, completed=True)
```

With SaveSession, changes are batched:

```python
# ✅ Efficient: Changes combined into optimized batches
async with SaveSession(client) as session:
    session.track(task)
    task.name = "New Name"
    task.completed = True
    session.add_tag(task, tag_gid)
    await session.commit_async()  # All changes sent together
```

### The Three Steps

Every SaveSession follows this pattern:

```python
async with SaveSession(client) as session:
    # 1. Track entities you want to modify
    session.track(task)

    # 2. Make changes (field updates, action operations)
    task.name = "Updated"
    session.add_tag(task, "urgent_tag_gid")

    # 3. Commit to send changes to Asana
    result = await session.commit_async()
```

**Step 1: Track** — Register entities with the session. The SDK captures a snapshot of current state to detect changes.

**Step 2: Modify** — Change field values or queue action operations. Nothing is sent to Asana yet.

**Step 3: Commit** — Execute all pending changes in optimized batches. Returns a result object with success/failure details.

### Automatic Dependency Ordering

SaveSession automatically orders operations to respect parent-child relationships:

```python
# Works correctly even though parent is tracked after child
session.track(child_task)
session.track(parent_task)

child_task.parent = parent_task

await session.commit_async()
# SDK creates parent first, then child (correct order)
```

### Partial Failure Handling

If some operations succeed and others fail, SaveSession reports details:

```python
result = await session.commit_async()

if result.success:
    print("All operations succeeded")
elif result.partial:
    print(f"{len(result.succeeded)} succeeded, {len(result.failed)} failed")
    for entity, error in result.failed:
        print(f"Failed to save {entity.gid}: {error}")
else:
    print("All operations failed")
```

## Sync vs Async

Every client method provides both synchronous and asynchronous APIs.

### Async Version (Recommended)

Use async when you're already in an async context:

```python
async def main():
    async with AsanaClient() as client:
        task = await client.tasks.get_async("task_gid")

        async with SaveSession(client) as session:
            session.track(task)
            task.completed = True
            result = await session.commit_async()
```

### Sync Version

Use sync for simple scripts or synchronous code:

```python
def main():
    with AsanaClient() as client:
        task = client.tasks.get("task_gid")

        with SaveSession(client) as session:
            session.track(task)
            task.completed = True
            result = session.commit()
```

**The pattern:** Every method ending in `_async()` has a sync equivalent without the suffix:
- `client.tasks.get_async()` → `client.tasks.get()`
- `session.commit_async()` → `session.commit()`

**Limitation:** Sync methods cannot be called from async code. Attempting to do so raises `SyncInAsyncContextError`.

## Authentication Modes

The SDK supports two authentication patterns.

### Personal Access Token (PAT)

For scripts, testing, and development:

```python
# Explicit token
client = AsanaClient(token="0/abcdef123456...")

# Or via environment variable
# export ASANA_PAT=0/abcdef123456...
client = AsanaClient()
```

### Service-to-Service JWT

For production services with `/v1/*` API routes:

```python
from my_auth import CustomAuthProvider

client = AsanaClient(auth_provider=CustomAuthProvider())
```

The auth provider must implement `get_secret(key: str) -> str` to return tokens on demand.

## Cache Behavior

The SDK caches reads to reduce API calls. Understanding cache behavior helps avoid stale data.

### Cache-First Reads

When you fetch an entity, the SDK checks the cache first:

```python
# First call: Cache miss, fetches from API
task = await client.tasks.get_async("task_gid")

# Second call: Cache hit, returns cached value
task = await client.tasks.get_async("task_gid")  # No API call
```

Each entity type has a default TTL (time-to-live):
- Tasks: 300 seconds (5 minutes)
- Projects: 600 seconds (10 minutes)
- Users: 3600 seconds (1 hour)

### Writes Don't Auto-Invalidate

Updating an entity via SaveSession does **not** automatically clear its cache entry:

```python
# Update task
async with SaveSession(client) as session:
    session.track(task)
    task.name = "New Name"
    await session.commit_async()

# This may return stale data (old name)
task = await client.tasks.get_async(task.gid)
```

**Workaround:** Manually invalidate after writes if you need fresh data:

```python
await session.commit_async()
client._cache_provider.invalidate(task.gid, EntryType.TASK)
task = await client.tasks.get_async(task.gid)  # Fresh fetch
```

**Future improvement:** The SDK will add `include_updated=True` parameter to auto-invalidate during commit.

## Key Terms Glossary

| Term | Definition |
|------|-----------|
| **GID** | Global ID — Asana's 13+ digit numeric string identifier for all resources (tasks, projects, etc.) |
| **Holder** | Parent task that groups child entities (e.g., UnitHolder contains Unit children). Managed automatically by SDK. |
| **Hydration** | Process of fetching and populating the full entity hierarchy from Asana API, including all nested holders and children |
| **Detection** | Identifying entity type from project membership. Business entities are detected by PRIMARY_PROJECT_GID. |
| **Resolution** | Finding entity GIDs from business identifiers (e.g., phone number + vertical → Business GID) |
| **Cascading** | Field inheritance from parent to child entities. Values set on Business propagate to Units and Offers. |
| **Descriptor** | Python descriptor that maps a property (e.g., `mrr`) to an Asana custom field (e.g., "MRR") |
| **SaveSession** | Unit of Work pattern for batching multiple operations into optimized API calls with dependency ordering |
| **Track** | Register an entity with SaveSession to enable change detection and deferred saves |

## What You've Learned

You now understand:

1. **Entity hierarchy** — Business → Unit → Offer/Contact/Process, with holders as organizational containers
2. **Custom fields** — Six descriptor types that map Python properties to Asana custom fields with automatic name derivation
3. **SaveSession** — Track entities, make changes, commit in batches with automatic dependency ordering
4. **Sync/Async** — Every method has both versions; use async when possible
5. **Authentication** — PAT for development, custom providers for production
6. **Cache behavior** — Reads are cached, writes don't auto-invalidate

## Next Steps

- **[Quick Start Guide](quick-start.md)** — Build your first SDK integration in 5 minutes
- **[SaveSession Deep Dive](save-session.md)** — Event hooks, result handling, previewing changes
- **[Custom Fields Guide](custom-fields.md)** — Advanced field patterns, cascading, inheritance
- **[Troubleshooting](troubleshooting.md)** — Common issues and solutions
