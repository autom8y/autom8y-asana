# ADR-0009: Cascading Custom Fields

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0054, ADR-0113
- **Related**: reference/CUSTOM-FIELDS.md

## Context

The Business Model hierarchy requires custom fields that flow across levels for data consistency and operational efficiency. For example, "Office Phone" from Business should cascade to all Units, Offers, and Processes. "Platforms" from Unit should cascade to Offers.

### Hierarchy Structure

```
Business
├── ContactHolder → Contact[]
├── UnitHolder → Unit[]
│   ├── OfferHolder → Offer[]
│   └── ProcessHolder → Process[]
├── LocationHolder → Location → Hours
└── (other holders...)
```

### Multi-Level Cascading Insight

Cascading can originate from **any level** in the hierarchy, not just Business (root):

| Source | Target(s) | Example Field | Override Allowed? |
|--------|-----------|---------------|-------------------|
| Business | Unit, Offer, Process, Contact | `office_phone` | NO (default) |
| Business | Unit, Offer, Process | `company_id` | NO (default) |
| Unit | Offer | `platforms` | YES (explicit opt-in) |
| Unit | Offer, Process | `vertical` | NO (default) |

### Critical Design Constraint: Override is Opt-In

**DEFAULT BEHAVIOR**: Cascading fields do NOT permit local overrides. Descendants always accept the parent value.

**Override is EXPLICIT OPT-IN**: Only fields explicitly configured with `allow_override=True` permit descendants to have local values that take precedence.

Examples:
- `office_phone`: Should NEVER permit local overrides - descendant always accepts parent value
- `platforms` on Unit→Offer: Explicit opt-in - Offer can override if it has a non-null value

### Rep Field Inheritance Pattern

New Process creation requires assignee from representative field. Both Unit and Business have `rep` custom field. The resolution follows specificity principle:

**Resolution Order**:
1. Try Unit.rep first (more specific)
2. Fall back to Business.rep
3. Return None if both empty (log warning, leave unassigned)

This pattern prefers more specific values and provides graceful fallback.

## Decision

**Implement denormalized storage with explicit cascade operations using multi-level cascading with opt-in override. Cascade scope is relative to the source entity, and allow_override=False is the default.**

### Pattern 1: Cascading Fields (Multi-Level with Default No Override)

Fields can be declared at **any level** in the hierarchy and cascade to specified descendants. The critical design principle is that **override is opt-in** (disabled by default).

```python
class Business(Task):
    """Business entity with cascading field declarations."""

    class CascadingFields:
        """Fields that cascade to descendants.

        CRITICAL: allow_override=False is the DEFAULT.
        Parent value ALWAYS wins unless override is explicitly enabled.
        """
        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={Unit, Offer, Process},
            # allow_override=False is DEFAULT - descendant value always overwritten
        )
        COMPANY_ID = CascadingFieldDef(
            name="Company ID",
            target_types=None,  # None = all descendants
            # allow_override=False - no local overrides permitted
        )
        BUSINESS_NAME = CascadingFieldDef(
            name="Business Name",
            target_types={Unit, Offer},
            source_field="name",  # Maps from Task.name
        )


class Unit(Task):
    """Unit entity with its own cascading fields."""

    class CascadingFields:
        """Fields that cascade from Unit to its descendants."""
        PLATFORMS = CascadingFieldDef(
            name="Platforms",
            target_types={Offer},  # Only cascade to Offers
            allow_override=True,  # EXPLICIT OPT-IN: Offer can override if non-null
        )
        VERTICAL = CascadingFieldDef(
            name="Vertical",
            target_types={Offer, Process},
            # allow_override=False - Offer/Process always get Unit's vertical
        )
```

### Cascade Behavior Based on allow_override

| `allow_override` | Cascade Behavior |
|------------------|------------------|
| `False` (DEFAULT) | **Always overwrite** descendant value with parent value |
| `True` (explicit) | Only overwrite if descendant value is `None`/null |

### Storage Strategy: Denormalized with Source Tracking

Each descendant stores the field value for fast reads (O(1) access):

```json
{
    "gid": "offer_123",
    "custom_fields": [
        {"gid": "cf_office_phone", "text_value": "555-1234"},
        {"gid": "cf_vertical", "enum_value": {"name": "Retail"}},
        {"gid": "cf_platforms", "multi_enum_value": [{"name": "Google"}]}
    ]
}
```

### Propagation Mechanism

```python
@dataclass(frozen=True)
class CascadeOperation:
    """Represents a field cascade to be executed.

    Supports multi-level cascading from any source entity.
    """
    source: AsanaResource  # Entity that owns the value (Business, Unit, etc.)
    field_name: str        # "Office Phone", "Platforms", etc.
    new_value: Any         # Value to propagate
    target_types: set[type] | None  # {Offer, Process} or None for all
    allow_override: bool   # If True, skip descendants with non-null values


class SaveSession:
    """Extended with cascade support."""

    def cascade_field(
        self,
        entity: AsanaResource,
        field_name: str,
        *,
        target_types: set[type] | None = None,
    ) -> SaveSession:
        """Explicitly cascade a field change to descendants.

        IMPORTANT: Cascade scope is relative to the source entity.
        - cascade_field(unit, "platforms") only affects that unit's offers
        - cascade_field(business, "office_phone") affects all business descendants

        The allow_override behavior is determined by the field's CascadingFieldDef.

        Args:
            entity: Source entity (Business, Unit, etc.)
            field_name: Field to cascade (e.g., "Office Phone", "Platforms")
            target_types: Optional filter of target entity types. If None, uses
                         field's declared target_types from CascadingFields.

        Returns:
            Self for fluent chaining.

        Example - Business field (no override):
            business.office_phone = "555-9999"
            session.cascade_field(business, "Office Phone")
            await session.commit_async()
            # All descendants get "555-9999" regardless of their current value

        Example - Unit field (with override opt-in):
            unit.platforms = ["Google", "Meta"]
            session.cascade_field(unit, "Platforms")
            await session.commit_async()
            # Only offers with null platforms get updated
            # Offers with existing platforms keep their value
        """
        field_def = self._get_cascade_field_def(entity, field_name)

        self._pending_cascades.append(
            CascadeOperation(
                source=entity,
                field_name=field_name,
                new_value=entity.get_custom_fields().get(field_name),
                target_types=target_types or (field_def.target_types if field_def else None),
                allow_override=field_def.allow_override if field_def else False,
            )
        )
        return self
```

### Batch Execution Strategy

Cascades execute via Asana Batch API for efficiency:

```python
async def _execute_cascades(
    self,
    cascades: list[CascadeOperation],
) -> list[BatchResult]:
    """Execute cascade operations in batches.

    Strategy:
    1. Collect all descendant GIDs to update (scoped to source entity)
    2. Apply allow_override filtering
    3. Group by field (same field → same batch request)
    4. Execute in chunks of 10 (Asana batch limit)
    5. Handle rate limits with exponential backoff

    CRITICAL: Descendants are scoped to the source entity.
    - cascade from Unit X only affects Unit X's children
    - cascade from Business affects all Business descendants
    """
    all_updates: list[tuple[str, dict]] = []

    for cascade in cascades:
        # Get descendants of THIS SPECIFIC source entity
        descendants = await self._get_descendants(
            cascade.source,
            cascade.target_types,
        )

        for descendant in descendants:
            # Handle allow_override behavior
            if cascade.allow_override:
                # Only update if descendant value is null
                current_value = descendant.get_custom_fields().get(cascade.field_name)
                if current_value is not None:
                    continue  # Skip - descendant has override value

            # Default (allow_override=False): Always update
            all_updates.append((
                descendant.gid,
                {"custom_fields": {
                    cascade.field_gid: cascade.new_value
                }}
            ))

    # Use existing BatchClient for chunked execution
    return await self._client.batch.update_tasks_async(all_updates)
```

### Rep Field Cascade Pattern

```python
def resolve_rep_for_process(unit: Unit, business: Business) -> str | None:
    """Resolve representative for new Process.

    Resolution order (specificity principle):
    1. Unit.rep (most specific)
    2. Business.rep (fallback)
    3. None (log warning)

    Args:
        unit: Parent Unit entity
        business: Root Business entity

    Returns:
        GID of representative, or None if both empty
    """
    # Try Unit first (more specific)
    unit_rep = unit.get_custom_fields().get("Representative")
    if unit_rep:
        return unit_rep

    # Fall back to Business
    business_rep = business.get_custom_fields().get("Representative")
    if business_rep:
        return business_rep

    # Both empty - log warning
    logger.warning(
        f"No representative found for Process creation "
        f"(Unit: {unit.gid}, Business: {business.gid})"
    )
    return None
```

## Rationale

### Why Denormalized Storage?

| Approach | Read Performance | Write Complexity | Query Capability |
|----------|-----------------|------------------|------------------|
| Virtual properties (compute on access) | O(n) traversal | O(1) | Cannot query |
| **Denormalized storage** | **O(1)** | **O(descendants)** | **Can query/filter** |

For our domain:
- **Reads are frequent**: Display Office Phone on every Offer card
- **Writes are infrequent**: Business phone changes rarely (monthly?)
- **Eventual consistency acceptable**: A few seconds of stale data is fine
- **Asana constraints**: Asana custom fields are per-task, not relational

This points strongly toward denormalized storage.

### Why Explicit Cascade Over Automatic?

```python
# Explicit is clear
session.cascade_field(business, "Office Phone")

# vs. Automatic (hidden behavior)
business.office_phone = "555"  # Secretly queues 50 updates?
```

Advantages of explicit:
1. **No magic**: Developer sees exactly what's happening
2. **Performance control**: Large hierarchies don't auto-cascade on every change
3. **Atomic commits**: Cascade happens within same commit transaction
4. **Testing**: Easy to unit test cascade logic in isolation

### Why allow_override=False as Default?

The default behavior should be safe and predictable:

**Safer default**: Parent value always wins (no descendant overrides)
- Ensures data consistency across hierarchy
- Prevents accidental divergence
- Clear source of truth (parent owns the value)

**Explicit opt-in for override**: Only when you actually need descendants to have their own values
- Documents intent in code
- Forces developers to think about whether override is appropriate
- Prevents bugs from unexpected local overrides

### Why Unit-First for Rep Cascade?

Specificity principle: more specific values override less specific

1. Unit-level assignment overrides business-level default
2. Aligns with hierarchy (Unit is child of Business)
3. Graceful fallback maximizes assignee coverage
4. Explicit resolution order is clear and debuggable

## Alternatives Considered

### Alternative 1: Virtual Properties (Compute on Access)

```python
@property
def office_phone(self) -> str | None:
    return self.business.office_phone  # Always traverse up
```

**Pros**:
- No denormalization
- Always consistent

**Cons**:
- O(n) traversal on every read
- Requires Business loaded for every Offer access
- Cannot query/filter by cascaded fields in Asana
- Performance degrades with hierarchy depth

**Why not chosen**: Read performance critical; denormalization preferred.

### Alternative 2: Event-Driven Propagation

```python
@business.office_phone.on_change
def propagate(new_value):
    for descendant in business.all_descendants:
        descendant.office_phone = new_value
```

**Pros**:
- Automatic propagation

**Cons**:
- Complex event wiring
- Hard to batch (events fire individually)
- Testing complexity
- Implicit behavior (magic)
- Difficult to control timing

**Why not chosen**: Explicit cascade is simpler and more controllable.

### Alternative 3: Database-Style Foreign Keys

Store only at root, descendants reference via GID:
```python
offer.business_gid  # Reference to Business
offer.office_phone  # -> Business.get(offer.business_gid).office_phone
```

**Pros**:
- Single source of truth
- No denormalization

**Cons**:
- Asana doesn't support relational queries
- Would require loading Business for every Offer display
- No native support in Asana UI
- Performance degrades quickly

**Why not chosen**: Asana is not a relational database.

### Alternative 4: Hybrid Cache Layer

Cache cascade values in SDK memory, sync to Asana periodically.

**Pros**:
- Fast reads
- Reduced API calls

**Cons**:
- Adds complexity (cache invalidation)
- SDK should be stateless between sessions
- Would require persistent cache infrastructure
- Cache coherency problems

**Why not chosen**: Over-engineered; denormalization is simpler.

### Alternative 5: allow_override=True as Default

**Pros**:
- More "flexible"

**Cons**:
- Unsafe: descendants can silently diverge from parent
- Defeats purpose of cascading (maintain consistency)
- Hard to debug: "Why doesn't my Offer have the Business phone?"
- Requires explicit `allow_override=False` on most fields

**Why not chosen**: Default should be safe. Opt-in to flexibility is better than opt-out from safety.

## Consequences

### Positive

1. **Fast reads**: O(1) field access on any entity in hierarchy
2. **Explicit control**: Developer decides when cascades happen
3. **Batch efficiency**: Uses existing BatchClient for bulk updates
4. **Queryable**: Cascaded fields visible in Asana views/reports
5. **Testable**: Cascade logic isolated and deterministic
6. **Safe default**: `allow_override=False` prevents accidental divergence
7. **Multi-level support**: Cascading can originate from any hierarchy level
8. **Specificity principle**: Unit.rep precedence over Business.rep is logical

### Negative

1. **Storage redundancy**: Same value stored N times (acceptable tradeoff)
2. **Eventual consistency**: Brief window of stale data
3. **API calls**: Cascade requires O(descendants) API calls
4. **Manual cascade**: Developer must explicitly cascade (not automatic)
5. **Rate limit risk**: Large hierarchies may hit Asana limits
   - *Mitigation*: Exponential backoff, chunking per ADR-0010

### Neutral

1. **Cascade scope is relative**: Unit cascade doesn't affect other Units
2. **Override is explicit**: Clear when descendants can have their own values
3. **Reconciliation available**: Can detect and repair drift if needed

## Compliance

### How This Decision Is Enforced

1. **Code patterns**:
   - [ ] `CascadingFieldDef` used for all cascading fields (any level)
   - [ ] `allow_override=False` is DEFAULT - do not change unless explicitly needed
   - [ ] `cascade_field()` called when modifying cascading fields
   - [ ] Rep resolution follows Unit-first pattern

2. **Lint rules** (optional):
   ```python
   # Detect cascading field change without cascade_field()
   if field_name in entity.CascadingFields and not session.has_cascade(field_name):
       warn("Cascading field modified without cascade_field() call")
   ```

3. **Unit tests**:
   ```python
   # Test 1: Default behavior (no override) - parent always wins
   async def test_cascade_no_override_always_overwrites():
       """Default: allow_override=False means parent value always wins."""
       offer.get_custom_fields().set("Office Phone", "555-OLD")

       business.office_phone = "555-NEW"
       session.cascade_field(business, "Office Phone")
       await session.commit_async()

       assert offer.get_custom_fields().get("Office Phone") == "555-NEW"

   # Test 2: Explicit override opt-in - null values updated
   async def test_cascade_with_override_updates_null_only():
       """allow_override=True: Only update descendants with null values."""
       offer_a.get_custom_fields().set("Platforms", None)
       offer_b.get_custom_fields().set("Platforms", ["Bing"])

       unit.platforms = ["Google", "Meta"]
       session.cascade_field(unit, "Platforms")
       await session.commit_async()

       assert offer_a.get_custom_fields().get("Platforms") == ["Google", "Meta"]
       assert offer_b.get_custom_fields().get("Platforms") == ["Bing"]  # KEPT

   # Test 3: Cascade scope limited to source descendants
   async def test_cascade_scope_limited_to_source_descendants():
       """Cascade from Unit A does not affect Unit B's children."""
       unit_a.platforms = ["Google"]
       session.cascade_field(unit_a, "Platforms")
       await session.commit_async()

       assert offer_from_unit_a.platforms == ["Google"]
       assert offer_from_unit_b.platforms is None  # Unchanged

   # Test 4: Rep resolution follows Unit-first pattern
   def test_rep_resolution_unit_first():
       """Unit.rep takes precedence over Business.rep."""
       unit.get_custom_fields().set("Representative", "unit_rep_gid")
       business.get_custom_fields().set("Representative", "business_rep_gid")

       rep = resolve_rep_for_process(unit, business)
       assert rep == "unit_rep_gid"
   ```

4. **Documentation**:
   - [ ] "Cascading Fields" section in Business Model guide
   - [ ] Multi-level cascading patterns and examples
   - [ ] "allow_override=False is DEFAULT" emphasized prominently
   - [ ] Rep field resolution pattern documented
   - [ ] "Consistency and Reconciliation" guide
