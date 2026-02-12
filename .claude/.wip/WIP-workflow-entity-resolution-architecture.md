# WIP: Workflow Entity Resolution Architecture

**Created**: 2026-02-11
**Source**: Spike `docs/spikes/SPIKE-workflow-automation-progress.md` + follow-up analysis
**Status**: Design notes for next major initiative
**Scope**: How batch workflows should resolve entity fields across the holder hierarchy

---

## 1. Problem Statement

The ConversationAuditWorkflow (our first batch workflow) bypasses the entity model layer entirely. It uses raw Asana API calls and manual `custom_fields` string matching to resolve `office_phone` from the parent Business. This works for the single-field, single-hop case but does not generalize.

The real need is **cross-holder field resolution** — where an entry point entity needs data from a sibling branch of the hierarchy:

```
ContactHolder ─^→ Business ─v→ LocationHolder ─v→ Address.time_zone
ContactHolder ─^→ Business ─v→ UnitHolder ─v→ Unit.vertical
ContactHolder ─^→ Business.office_phone  (current, simplest case)
Unit ─^→ Business ─v→ ContactHolder ─v→ Contact(is_owner=True).email
```

The `─^→` (upward) and `─v→` (downward) arrows represent navigation through the hierarchy tree, crossing between sibling holders through the Business root.

---

## 2. What Exists Today

### 2.1 Entity Model Layer (Mature)

The full descriptor + hydration system is production-grade:

| Component | File | Purpose |
|-----------|------|---------|
| `CustomFieldDescriptor` | `models/business/descriptors.py` | Declarative field access (`business.office_phone`) |
| `TextField`, `EnumField`, `NumberField`, etc. | `models/business/descriptors.py` | Type-specific coercion (str, Decimal, Arrow dates) |
| `ParentRef[T]` | `models/business/descriptors.py` | Lazy upward navigation with cache (`contact.business`) |
| `HolderRef[T]` | `models/business/descriptors.py` | Direct holder reference (`contact.contact_holder`) |
| `Business.from_gid_async()` | `models/business/business.py` | Full/partial hierarchy hydration |
| `CascadingFieldDef` | `models/business/fields.py` | Downward field propagation definitions |
| `HolderFactory` | `models/business/holder_factory.py` | Declarative holder configuration |
| `_populate_children()` | `models/business/base.py` | Typed children with bidirectional refs |

**Business custom fields (19 descriptors declared):**

```python
# business.py lines 280-299
company_id = TextField()
office_phone = TextField(cascading=True)      # ← what workflow needs
owner_name = TextField()
vertical = EnumField()                         # ← inherited from mixin
stripe_id = TextField()
# ... 14 more
```

**Navigation graph (already wired):**

```python
contact.business          # ParentRef[Business] — lazy via contact_holder
contact.contact_holder    # HolderRef[ContactHolder] — direct
business.contact_holder   # property → _contact_holder
business.location_holder  # property → _location_holder
business.contacts         # shortcut → contact_holder.contacts
business.units            # shortcut → unit_holder.units
business.address          # shortcut → location_holder.primary_location
```

### 2.2 ConversationAuditWorkflow (Current Implementation)

```python
# conversation_audit.py — BYPASSES model layer entirely

# Enumeration: raw API, returns dicts not entities
tasks = await self._asana_client.tasks.list_for_project_async(PROJECT_GID, ...)
holders = [{"gid": t.gid, "name": t.name} for t in tasks]

# Resolution: raw API + manual string matching
holder_task = await self._asana_client.tasks.get_async(holder_gid, ...)
parent_task = await self._asana_client.tasks.get_async(parent_ref.gid, ...)
for cf in parent_task.custom_fields:
    if cf_dict.get("name") == "Office Phone":  # hardcoded string
        return cf_dict.get("display_value")
```

**API call count per holder**: 2 (get holder for parent ref, get parent for custom_fields)
**Fields accessible**: 1 (office_phone only, hardcoded)

### 2.3 Business.get_insights_async() (Established Pattern)

```python
# business.py:730-791 — USES model layer correctly
async def get_insights_async(self, client, ...):
    if not self.office_phone:      # descriptor access
        raise InsightsValidationError(...)
    if not self.vertical:           # descriptor access
        raise InsightsValidationError(...)
    return await client.get_insights_async(
        office_phone=self.office_phone,
        vertical=self.vertical,
    )
```

This is the pattern workflows should follow.

---

## 3. Architectural Gaps

### Gap 1: No Cross-Holder Resolution Path

The entity model supports **upward** (child → Business) and **downward** (Business → holder → children) navigation, but there's no ergonomic pattern for **lateral** traversal through the Business root.

**Current**: Each field resolution is a bespoke method per workflow.
**Needed**: A resolution strategy that expresses paths like:

```
resolve(contact_holder, "business.office_phone")
resolve(contact_holder, "business.location_holder.primary_location.time_zone")
resolve(contact_holder, "business.contact_holder.owner.email")
```

### Gap 2: Batch Hydration Cost

Full `Business.from_gid_async(hydrate=True)` fetches the entire hierarchy (all 7 holders + all children). For a batch workflow processing 100 ContactHolders that only needs `office_phone`, this is massively wasteful.

**Options to evaluate:**

| Approach | API Calls | Fields Available | Complexity |
|----------|-----------|-----------------|------------|
| Current raw approach | 2/holder | 1 (hardcoded) | Low |
| `Business.from_gid_async(hydrate=False)` | 2/holder | All 19 Business fields | Low |
| Selective hydration (hydrate specific holders) | 2-4/holder | Business + specific holder branch | Medium |
| Full hydration | 10-30/holder | Everything | High (batch-prohibitive) |
| Shared Business cache (hydrate once per Business, reuse across holders) | Amortized 1-2/holder | Everything | Medium |

The **shared Business cache** approach is likely the sweet spot for batch workflows: since multiple ContactHolders share the same parent Business, hydrating the Business once and reusing it across all its holders eliminates redundant API calls.

### Gap 3: Workflow Operates on Dicts, Not Entities

`_enumerate_contact_holders()` returns `list[dict]` — raw GID/name pairs. Workflows never touch the typed entity layer. This means:

- No access to descriptors, navigation refs, or cascading fields
- Every field resolution must be reimplemented per workflow
- No type safety or validation from the model layer

### Gap 4: No "Selective Hydration" API

`Business.from_gid_async()` is all-or-nothing: `hydrate=True` loads everything, `hydrate=False` loads nothing below Business. There's no way to say "hydrate only LocationHolder" or "hydrate ContactHolder + LocationHolder but skip the rest."

### Gap 5: Monthly Scheduling + CLI Workflow Execution

Noted in the spike but separate from entity resolution:
- Config schema only supports `daily`/`weekly` frequencies
- CLI creates PollingScheduler without `workflow_registry` (can't run workflows)
- Each workflow needs a copy-paste Lambda handler (no generic dispatcher)

---

## 4. Design Direction

### 4.1 Short-Term: Use Business Entity in Existing Workflow

Replace `_resolve_office_phone()` with:

```python
async def _resolve_parent_business(self, holder_gid: str) -> Business | None:
    holder_task = await self._asana_client.tasks.get_async(
        holder_gid, opt_fields=["parent", "parent.gid"],
    )
    if not holder_task.parent or not holder_task.parent.gid:
        return None
    return await Business.from_gid_async(
        self._asana_client, holder_task.parent.gid, hydrate=False,
    )
```

**Cost**: Same 2 API calls. **Benefit**: Access to all 19 Business descriptors. All future workflows that need any Business field (office_phone, vertical, company_id, stripe_id, etc.) use the same resolution.

### 4.2 Medium-Term: Shared Business Cache for Batch Workflows

Multiple ContactHolders often share the same parent Business. A per-workflow Business cache eliminates redundant fetches:

```python
class _BusinessCache:
    """Per-execution cache of hydrated Business entities."""
    def __init__(self, client: AsanaClient):
        self._client = client
        self._cache: dict[str, Business] = {}

    async def get(self, business_gid: str, hydrate_holders: list[str] | None = None) -> Business:
        if business_gid not in self._cache:
            self._cache[business_gid] = await Business.from_gid_async(
                self._client, business_gid, hydrate=False,
            )
        business = self._cache[business_gid]
        # Selective hydration: only fetch requested holder branches
        if hydrate_holders:
            await self._ensure_holders(business, hydrate_holders)
        return business
```

This also opens the door for cross-holder resolution: if a workflow needs both `office_phone` (from Business) and `time_zone` (from LocationHolder → Address), the cache hydrates the LocationHolder branch on first access and reuses it for subsequent holders under the same Business.

### 4.3 Long-Term: Selective Hydration on Business

Extend `Business.from_gid_async()` with holder selection:

```python
business = await Business.from_gid_async(
    client, gid,
    hydrate=["contact_holder", "location_holder"],  # only these branches
)
# business.contact_holder → populated
# business.location_holder → populated
# business.unit_holder → None (not requested)
```

This keeps the existing hydration infrastructure but makes it batch-friendly by avoiding unnecessary holder + children fetches.

### 4.4 Long-Term: Field Resolution Paths

For workflows that need fields from arbitrary hierarchy positions, a declarative resolution path:

```python
class WorkflowFieldRequirements:
    """Declare what fields a workflow needs and where they live."""
    fields = {
        "office_phone": "business.office_phone",
        "time_zone": "business.location_holder.primary_location.time_zone",
        "owner_email": "business.contact_holder.owner.email",
        "vertical": "business.vertical",
    }
```

The runtime resolves these paths by:
1. Navigating upward to Business (via parent ref)
2. Selectively hydrating only the holders mentioned in paths
3. Walking the descriptor chain to extract values
4. Caching the Business graph for reuse across batch items

This turns per-workflow bespoke resolution into declarative configuration.

---

## 5. Cross-Holder Resolution Example

**Use case**: A workflow attached to ContactHolder needs `time_zone` from the Location entity under LocationHolder.

**Hierarchy path**:
```
ContactHolder ─parent─→ Business ─holder─→ LocationHolder ─child─→ Location.time_zone
     (entry)              (root)             (sibling holder)        (target field)
```

**Current approach** (would require):
```python
# 4 raw API calls + 2 manual custom_field lookups
holder = await client.tasks.get_async(holder_gid, opt_fields=["parent.gid"])
business = await client.tasks.get_async(holder.parent.gid, opt_fields=["subtasks"])
# Find LocationHolder subtask by name/emoji...
location_holder = await client.tasks.get_async(loc_holder_gid, opt_fields=["subtasks"])
# Find Address subtask by name/emoji...
address = await client.tasks.get_async(address_gid, opt_fields=["custom_fields"])
# Manual string match for "Time Zone"...
```

**With selective hydration** (proposed):
```python
business = await business_cache.get(
    parent_gid,
    hydrate_holders=["location_holder"],
)
tz = business.address.time_zone  # descriptor chain, fully typed
```

**API calls**: 3 (Business + LocationHolder subtasks + Location subtask children) — cached and reused across all holders sharing the same Business.

---

## 6. Smoke Test Notes

For running a one-off smoke test of ConversationAuditWorkflow:

**Required env vars**: `ASANA_PAT`, `AUTOM8_DATA_URL`, `AUTOM8_DATA_API_KEY`

**Entry point**: `workflow._process_holder(holder_gid, holder_name, attachment_pattern)` — the `office_phone` is resolved internally via `_resolve_office_phone()` (2 Asana API calls per holder).

**No HTTP endpoint exists** for on-demand workflow triggers. Script-only for now.

**The `_process_holder` internal flow**:
1. `_resolve_office_phone(holder_gid)` → parent Business → "Office Phone" custom field
2. `data_client.get_export_csv_async(office_phone, ...)` → CSV from data.api.autom8y.io
3. `attachments_client.upload_async(...)` → multipart upload to Asana
4. `_delete_old_attachments(...)` → cleanup old conversations_*.csv

**When this gets refactored**, step 1 becomes `Business.from_gid_async(hydrate=False)` and the workflow gains access to all Business fields for free.

---

## 7. Action Items for Next Initiative

### Must-Do (Before Workflow #2)

- [ ] **Replace `_resolve_office_phone` with `Business.from_gid_async(hydrate=False)`** — same API cost, gains all 19 descriptors, eliminates manual custom_field parsing
- [ ] **Rename to `_resolve_parent_business()`** — returns `Business | None` instead of `str | None`, caller extracts whatever fields it needs

### Should-Do (Enables Cross-Holder Workflows)

- [ ] **Add selective hydration to `Business.from_gid_async()`** — `hydrate` accepts `bool | list[str]` for holder names
- [ ] **Build `_BusinessCache` for batch workflows** — avoids redundant Business fetches when multiple holders share a parent
- [ ] **Evaluate enumeration via Business hydration** — instead of raw `list_for_project_async`, load Businesses and iterate their typed holders

### Could-Do (Full Generalization)

- [ ] **Declarative `WorkflowFieldRequirements`** — workflows declare field paths, runtime resolves and caches
- [ ] **Add HTTP trigger endpoint** — `POST /api/v1/workflows/trigger` for on-demand invocation
- [ ] **Generic Lambda dispatcher** — single handler that routes by `workflow_type` in event payload
- [ ] **Monthly scheduling support** — extend `ScheduleConfig` validator and `_should_run_schedule()`
- [ ] **CLI workflow execution** — pass `workflow_registry` to PollingScheduler in CLI

---

## 8. Key Files

| File | Relevance |
|------|-----------|
| `automation/workflows/conversation_audit.py` | Current workflow with raw resolution |
| `models/business/business.py` | Business entity with 19 descriptors + hydration |
| `models/business/descriptors.py` | CustomFieldDescriptor system (TextField, EnumField, etc.) |
| `models/business/base.py` | BusinessEntity base, HolderMixin, `_populate_children()` |
| `models/business/holder_factory.py` | Declarative holder configuration |
| `models/business/fields.py` | CascadingFieldDef, InheritedFieldDef |
| `models/business/contact.py` | ContactHolder + Contact entities |
| `models/business/location.py` | LocationHolder + Location (has time_zone, address fields) |
| `models/business/hydration.py` | Hydration utilities, opt_fields |
| `clients/data/client.py:1434-1583` | `get_export_csv_async()` — data service integration |
| `lambda_handlers/conversation_audit.py` | Lambda entry point |
