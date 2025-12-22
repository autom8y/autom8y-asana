# ADR-0105: Field Seeding Architecture

## Status

Accepted

## Context

When pipeline conversion creates a new Process (e.g., Onboarding from Sales), fields must be populated from multiple sources:
1. **Cascade**: Business/Unit fields that flow down the hierarchy
2. **Carry-through**: Fields copied from the source Process
3. **Computed**: Values derived at runtime (e.g., started_at = today)

Existing SDK has CascadingFieldDef/InheritedFieldDef in business entities, but these operate at the field descriptor level. Automation needs explicit field value computation.

**Requirements**:
- FR-005: Field seeding from Business/Unit cascade and source Process carry-through

**Options Considered**:

1. **Option A: Extend BusinessSeeder** - Add seeding logic to existing BusinessSeeder class
2. **Option B: New FieldSeeder Class** - Dedicated service for field computation
3. **Option C: Inline in PipelineConversionRule** - Compute fields directly in rule

## Decision

**We will use Option B: New FieldSeeder Class.**

Create a dedicated FieldSeeder service that computes field values for new entities. This separates field computation concerns from entity creation (BusinessSeeder) and rule execution (PipelineConversionRule).

## Consequences

### Positive

- **Single Responsibility**: FieldSeeder only computes values; doesn't create entities
- **Testability**: Can unit test field seeding independently
- **Reusability**: Same seeder works for any automation rule, not just pipeline conversion
- **Clarity**: Field sources (cascade vs carry-through vs computed) are explicit

### Negative

- **New Abstraction**: Another class to understand and maintain
- **Coordination**: Rule must orchestrate seeder + entity creation

### Implementation

```python
class FieldSeeder:
    """Computes field values from hierarchy and carry-through."""

    # Cascade from Business
    BUSINESS_CASCADE_FIELDS = [
        "Office Phone", "Company ID", "Business Name", "Primary Contact Phone"
    ]

    # Cascade from Unit
    UNIT_CASCADE_FIELDS = ["Vertical", "Platforms", "Booking Type"]

    # Carry-through from source Process
    PROCESS_CARRY_THROUGH_FIELDS = ["Contact Phone", "Priority", "Assigned To"]

    async def cascade_from_hierarchy_async(
        self, business: Business | None, unit: Unit | None
    ) -> dict[str, Any]: ...

    async def carry_through_from_process_async(
        self, source_process: Process
    ) -> dict[str, Any]: ...

    async def compute_fields_async(
        self, source_process: Process
    ) -> dict[str, Any]:
        """Compute derived values (e.g., Started At = today)."""

    async def seed_fields_async(
        self, business, unit, source_process
    ) -> dict[str, Any]:
        """Combine all sources: cascade + carry-through + computed."""
        fields = {}
        fields.update(await self.cascade_from_hierarchy_async(business, unit))
        fields.update(await self.carry_through_from_process_async(source_process))
        fields.update(await self.compute_fields_async(source_process))
        return fields
```

### Field Precedence

Later sources override earlier:
1. Cascade from Business (lowest priority)
2. Cascade from Unit
3. Carry-through from source Process
4. Computed fields (highest priority)

## References

- TDD-AUTOMATION-LAYER (FieldSeeder Component section)
- PRD-AUTOMATION-LAYER (FR-005)
- DISCOVERY-AUTOMATION-LAYER (Section 4: Field Seeding Inventory)
- ADR-0054: Cascading Custom Fields (existing cascade patterns)
