# ADR-0016: Business Entity Seeding and Field Population

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Deciders**: Architect, Requirements Analyst
- **Consolidated From**: ADR-0099, ADR-0105
- **Related**: reference/OPERATIONS.md, ADR-0015 (Process Pipeline Architecture)

## Context

Consumer applications (webhook handlers, Calendly integration) need to create complete business entity hierarchies from external triggers. A typical flow:

1. External webhook fires (Calendly booking, form submission)
2. Handler extracts business name, contact info, process details
3. Handler needs to create: Business > Unit > ProcessHolder > Process
4. Process must be in correct pipeline state

Currently, consumers must:
- Manually navigate hierarchy (find parent, create child, repeat)
- Handle find-or-create logic themselves (avoid duplicates)
- Manage multiple SaveSession operations
- Compute field values from multiple sources (cascade, carry-through, computed)

For pipeline conversion (Process moves from Sales to Onboarding), fields must be populated from three sources:
1. **Cascade**: Business/Unit fields that flow down the hierarchy
2. **Carry-through**: Fields copied from the source Process
3. **Computed**: Values derived at runtime (e.g., started_at = today)

No unified pattern exists for either hierarchy creation or field computation.

## Decision

### 1. BusinessSeeder Factory Pattern

**Create BusinessSeeder factory class with find-or-create pattern for complete hierarchy creation.**

```python
class BusinessSeeder:
    """Factory for creating complete business entity hierarchies."""

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def seed_async(
        self,
        business: BusinessData,
        process: ProcessData,
        *,
        contact: ContactData | None = None,
        unit_name: str | None = None,
    ) -> SeederResult:
        """Create or find Business > Unit > ProcessHolder > Process hierarchy.

        Find-or-create algorithm:
        - Business: Find by company_id (exact), then by name (exact)
        - Unit: Find under Business by name
        - ProcessHolder: Find under Unit (always named "Processes")
        - Process: Always created (not idempotent for process itself)

        Args:
            business: Business data (name, company_id, optional fields)
            process: Process data (name, process_type, initial_state)
            contact: Optional contact data (full_name, contact_email)
            unit_name: Optional unit name (defaults from business or process)

        Returns:
            SeederResult with all entities and creation flags
        """
        # Implementation uses SaveSession internally for transactional execution

    def seed(self, ...) -> SeederResult:
        """Sync wrapper via run_sync()."""
        return run_sync(self.seed_async(...))
```

**Input data models** (Pydantic validation):

```python
class BusinessData(BaseModel):
    """Business creation data."""
    name: str
    company_id: str | None = None
    # Optional creation fields

class ProcessData(BaseModel):
    """Process creation data."""
    name: str
    process_type: ProcessType
    initial_state: ProcessSection = ProcessSection.OPPORTUNITY

class ContactData(BaseModel):
    """Contact creation data."""
    full_name: str
    contact_email: str | None = None
```

**SeederResult** (dataclass):

```python
@dataclass
class SeederResult:
    """Result of business seeding operation."""
    business: Business
    unit: Unit
    process_holder: ProcessHolder
    process: Process
    contact: Contact | None = None
    created_business: bool = False
    created_unit: bool = False
    created_process_holder: bool = False
    # Process always created, so no created_process flag
```

**Why process always created**: Each seed call represents a new business event (sale opportunity, booking, etc.). Even if Business exists, a new Process should be created for the new event.

**Rationale**:
- **Idempotency critical for webhook retries**: Same input produces same result (no duplicates)
- **Factory encapsulates complexity**: Multi-step creation and hierarchy navigation hidden
- **Pydantic input models**: Provide validation and clear schema
- **Creation flags**: Enable consumer logic branching (e.g., send welcome email only if business created)
- **SaveSession integration**: Transactional batch execution consistent with SDK patterns

### 2. FieldSeeder Service

**Create dedicated FieldSeeder service for field computation separate from entity creation.**

```python
class FieldSeeder:
    """Computes field values from hierarchy and carry-through."""

    # === FIELD CATEGORIZATION ===

    # Cascade from Business
    BUSINESS_CASCADE_FIELDS = [
        "Office Phone",
        "Company ID",
        "Business Name",
        "Primary Contact Phone"
    ]

    # Cascade from Unit
    UNIT_CASCADE_FIELDS = [
        "Vertical",
        "Platforms",
        "Booking Type"
    ]

    # Carry-through from source Process
    PROCESS_CARRY_THROUGH_FIELDS = [
        "Contact Phone",
        "Priority",
        "Assigned To"
    ]

    # === COMPUTATION METHODS ===

    async def cascade_from_hierarchy_async(
        self,
        business: Business | None,
        unit: Unit | None
    ) -> dict[str, Any]:
        """Extract cascading fields from Business and Unit.

        Reads field values from Business and Unit entities that should
        propagate down to child Process entities.

        Returns:
            Dict mapping field names to values (field_name: value)
        """

    async def carry_through_from_process_async(
        self,
        source_process: Process
    ) -> dict[str, Any]:
        """Extract carry-through fields from source Process.

        Copies specific field values from source Process that should
        be preserved when creating converted Process.

        Returns:
            Dict mapping field names to values
        """

    async def compute_fields_async(
        self,
        source_process: Process
    ) -> dict[str, Any]:
        """Compute derived field values.

        Calculates runtime values such as:
        - Started At = today's date
        - Converted At = now timestamp
        - Other computed values

        Returns:
            Dict mapping field names to computed values
        """

    async def seed_fields_async(
        self,
        business: Business | None,
        unit: Unit | None,
        source_process: Process
    ) -> dict[str, Any]:
        """Combine all field sources with correct precedence.

        Field precedence (later overrides earlier):
        1. Cascade from Business (lowest priority)
        2. Cascade from Unit
        3. Carry-through from source Process
        4. Computed fields (highest priority)

        Returns:
            Dict mapping field names to final values
        """
        fields = {}
        fields.update(await self.cascade_from_hierarchy_async(business, unit))
        fields.update(await self.carry_through_from_process_async(source_process))
        fields.update(await self.compute_fields_async(source_process))
        return fields
```

**Rationale**:
- **Single responsibility**: FieldSeeder only computes values; doesn't create entities
- **Testability**: Can unit test field seeding independently from entity creation
- **Reusability**: Same seeder works for any automation rule, not just pipeline conversion
- **Explicit sources**: Field sources (cascade vs carry-through vs computed) are clear
- **Precedence clarity**: Later sources override earlier; no ambiguity

## Alternatives Considered

### Alternative A: Client Extension Method

- **Description**: Add `client.seed_business()` method to AsanaClient
- **Pros**: Discoverable; no new import
- **Cons**: Bloats AsanaClient; mixes core API with business logic
- **Why not chosen**: AsanaClient should remain focused on API operations; seeding is domain-specific

### Alternative B: Builder Pattern

- **Description**: `BusinessSeeder.for_business(data).with_unit(...).with_process(...).build()`
- **Pros**: Flexible; self-documenting
- **Cons**: Overly complex for common case; more code to write
- **Why not chosen**: Single seed_async() call is simpler for the 90% use case

### Alternative C: Extend BusinessSeeder with Field Logic

- **Description**: Add field seeding logic to existing BusinessSeeder class
- **Pros**: Single class; simpler API
- **Cons**: Mixes entity creation and field computation; harder to test; violates single responsibility
- **Why not chosen**: Separate concerns enable independent testing and reuse

### Alternative D: Inline Field Computation in Rules

- **Description**: Compute fields directly in PipelineConversionRule execution
- **Pros**: No new abstraction
- **Cons**: Duplicates logic across rules; hard to test; no reusability
- **Why not chosen**: Field computation is complex enough to warrant dedicated service

## Consequences

### Positive

- **Simple API for common operation**: Single seed_async() call creates entire hierarchy
- **Idempotent for Business/Unit/ProcessHolder**: Safe retries for webhook handlers
- **Clear result object**: Creation flags enable consumer logic branching
- **Async-first with sync wrapper**: Consistent with SDK patterns
- **Encapsulates dual membership**: No consumer knowledge of membership setup required
- **Testable independently**: FieldSeeder can be unit tested without entity creation
- **Reusable across rules**: Same field computation works for any automation
- **Clear precedence**: Field sources have explicit priority order

### Negative

- **New classes and data models**: BusinessSeeder, FieldSeeder, input models, SeederResult to maintain
- **Find logic requires search API**: May be slow for large workspaces
- **Not idempotent for Process**: Each seed call creates new Process (intentional)
- **Coordination required**: Rules must orchestrate seeder + entity creation

### Neutral

- SaveSession used internally (consistent with SDK patterns)
- ContactData optional (covers both with/without contact cases)
- unit_name parameter for non-default unit naming
- Field lists require maintenance as requirements evolve

## Implementation Guidance

### When creating business entities from webhooks:

1. Use BusinessSeeder.seed_async() for complete hierarchy creation
2. Rely on find-or-create idempotency for safe retries
3. Check SeederResult.created_* flags for conditional logic (e.g., send welcome email)
4. Process always created - represents new business event

### When populating fields for pipeline conversion:

1. Use FieldSeeder for all field computation
2. Call cascade_from_hierarchy_async() for Business/Unit fields
3. Call carry_through_from_process_async() for source Process fields
4. Call compute_fields_async() for runtime-derived values
5. Use seed_fields_async() for combined result with correct precedence

### When adding new cascade/carry-through fields:

1. Add to appropriate field list (BUSINESS_CASCADE_FIELDS, UNIT_CASCADE_FIELDS, PROCESS_CARRY_THROUGH_FIELDS)
2. Update tests to verify field appears in result
3. Document field source in field definition

## Compliance

- [ ] seed_async() creates Business if not found
- [ ] Find by company_id, then name for Business
- [ ] Unit created under Business
- [ ] ProcessHolder created under Unit
- [ ] Process created in ProcessHolder
- [ ] Process receives membership in canonical project
- [ ] SeederResult returned with all entities
- [ ] SaveSession used internally for transactional execution
- [ ] Async-first with sync wrapper
- [ ] Optional ContactData supported
- [ ] Idempotent for same Business input
- [ ] FieldSeeder cascade/carry-through/computed methods implemented
- [ ] Field precedence order enforced in seed_fields_async()
- [ ] Tests verify each field source independently
