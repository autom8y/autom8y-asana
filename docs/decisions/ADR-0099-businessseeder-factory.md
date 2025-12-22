# ADR-0099: BusinessSeeder Factory Pattern

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-17
- **Deciders**: Architect, Requirements Analyst
- **Related**: [PRD-PROCESS-PIPELINE](../requirements/PRD-PROCESS-PIPELINE.md), [TDD-PROCESS-PIPELINE](../design/TDD-PROCESS-PIPELINE.md), [ADR-0098](ADR-0098-dual-membership-model.md)

---

## Context

Consumer applications (webhook handlers, Calendly integration) need to create complete business entity hierarchies from external triggers. A typical flow:

1. Calendly booking webhook fires
2. Handler extracts business name, contact info
3. Handler needs to create: Business > Unit > ProcessHolder > Process
4. Process must be added to pipeline project

Currently, consumers must:
- Manually navigate hierarchy
- Handle find-or-create logic themselves
- Manage multiple SaveSession operations
- Remember dual membership setup

**Forces at play**:

1. **Developer ergonomics**: Common operation should be simple
2. **Idempotency**: Same input should produce same result (no duplicates)
3. **Flexibility**: Support various data inputs (with/without contact, etc.)
4. **Async-first**: Follow SDK convention of async primary, sync wrapper
5. **SaveSession integration**: Must compose with existing persistence layer

---

## Decision

**Create BusinessSeeder factory class with find-or-create pattern for complete hierarchy creation.**

**Seeder returns SeederResult with all entities and creation flags.**

**All operations use SaveSession internally for transactional batch execution.**

The implementation:

1. **BusinessSeeder class**:
   ```python
   class BusinessSeeder:
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
           ...

       def seed(self, ...) -> SeederResult:
           # Sync wrapper via run_sync()
   ```

2. **Input data models**:
   ```python
   class BusinessData(BaseModel):
       name: str
       company_id: str | None = None
       # Optional creation fields

   class ProcessData(BaseModel):
       name: str
       process_type: ProcessType
       initial_state: ProcessSection = ProcessSection.OPPORTUNITY

   class ContactData(BaseModel):
       full_name: str
       contact_email: str | None = None
   ```

3. **SeederResult**:
   ```python
   @dataclass
   class SeederResult:
       business: Business
       unit: Unit
       process_holder: ProcessHolder
       process: Process
       contact: Contact | None = None
       created_business: bool = False
       created_unit: bool = False
       created_process_holder: bool = False
   ```

4. **Find-or-create algorithm**:
   - Business: Find by company_id (exact), then by name (exact)
   - Unit: Find under Business by name
   - ProcessHolder: Find under Unit (always named "Processes")
   - Process: Always created (not idempotent for process itself)

---

## Rationale

**Why factory pattern?**

| Pattern | Pros | Cons |
|---------|------|------|
| Factory (BusinessSeeder) | Single entry point, encapsulates complexity | New class to maintain |
| Builder | Fluent API, incremental construction | Complex for simple case |
| Static methods | No instance needed | Hard to inject dependencies |
| Extension methods on client | Discoverable | Pollutes client API |

Factory encapsulates the multi-step creation while allowing dependency injection (AsanaClient).

**Why find-or-create?**

Idempotency is critical for webhook handlers:
- Webhooks may retry on failure
- Same booking may trigger multiple calls
- Duplicate entities cause data quality issues

Find-or-create ensures:
- Existing Business reused if found
- New Business created only if needed
- Result always contains valid entity hierarchy

**Why process always created?**

Each seed call represents a new business event (sale opportunity, booking, etc.). Even if Business exists, a new Process should be created for the new event. The Process name includes distinguishing information (e.g., timestamp, booking ID).

**Why SeederResult over tuple/dict?**

Dataclass provides:
- Named access to all entities
- Type safety
- Creation flags for consumer logic
- Extensible (can add fields later)

**Why input data models?**

Pydantic models provide:
- Input validation
- Clear schema for consumers
- Serialization for logging/debugging
- Optional fields with defaults

---

## Alternatives Considered

### Alternative 1: Client Extension Method

- **Description**: Add `client.seed_business()` method to AsanaClient
- **Pros**: Discoverable, no new import
- **Cons**: Bloats AsanaClient, mixes core API with business logic
- **Why not chosen**: AsanaClient should remain focused on API operations; seeding is domain-specific

### Alternative 2: Builder Pattern

- **Description**: `BusinessSeeder.for_business(data).with_unit(...).with_process(...).build()`
- **Pros**: Flexible, self-documenting
- **Cons**: Overly complex for common case, more code to write
- **Why not chosen**: Single seed_async() call is simpler for the 90% use case

### Alternative 3: Static Factory Functions

- **Description**: `seed_business(client, business_data, process_data)` module function
- **Pros**: Simple, no class instantiation
- **Cons**: Hard to test (client injection), no state for future extensions
- **Why not chosen**: Class allows dependency injection and potential future state (e.g., caching)

### Alternative 4: Process-First Seeding

- **Description**: Start from Process, auto-create parents as needed
- **Pros**: Bottom-up matches mental model
- **Cons**: Complex parent detection, unclear ownership
- **Why not chosen**: Top-down (Business first) matches hierarchy and is clearer

---

## Consequences

**Positive**:
- Simple API for common operation
- Idempotent for Business/Unit/ProcessHolder (safe retries)
- Clear result object with creation flags
- Async-first with sync wrapper
- Encapsulates dual membership setup

**Negative**:
- New class and data models to maintain
- Find logic requires search API (may be slow)
- Not idempotent for Process creation (intentional)
- Limited flexibility for complex hierarchies

**Neutral**:
- SaveSession used internally (consistent with SDK patterns)
- ContactData optional (covers both with/without contact cases)
- unit_name parameter for non-default unit naming

---

## Compliance

- [ ] seed_async() creates Business if not found per FR-SEED-001
- [ ] Find by company_id, then name per FR-SEED-002
- [ ] Unit created under Business per FR-SEED-003
- [ ] ProcessHolder created under Unit per FR-SEED-004
- [ ] Process created in ProcessHolder per FR-SEED-005
- [ ] Process added to pipeline project per FR-SEED-006
- [ ] SeederResult returned per FR-SEED-007
- [ ] SaveSession used per FR-SEED-008
- [ ] Async-first with sync wrapper per FR-SEED-009
- [ ] Optional ContactData per FR-SEED-010
- [ ] Idempotent for same Business input per FR-SEED-011
