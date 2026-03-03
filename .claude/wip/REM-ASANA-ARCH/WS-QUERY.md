# WS-QUERY: Query Engine Decoupling via Protocol

**Objective**: Decouple `query/engine.py` from the services layer by introducing
a `DataFrameProvider` protocol, enabling the query engine to be tested and
potentially extracted independently.

**Rite**: 10x-dev
**Complexity**: MODULE
**Recommendations**: R-010
**Preconditions**: Best done after WS-DFEX (R-006) for clean service boundaries
**Estimated Effort**: 3 days

---

## Problem

`query/engine.py` directly imports:
- `services.query_service.EntityQueryService`
- `services.resolver.to_pascal_case`

This means the query engine (a computational subsystem) depends on the services
layer (an orchestration layer), inverting the expected dependency direction.
The engine cannot be tested without the full services layer.

**Evidence**: ARCHITECTURE-ASSESSMENT.md Section 3.7, Risk 9 (leverage 2/10)

---

## Artifact References

- Boundary assessment: `ARCHITECTURE-ASSESSMENT.md` Section 3.7
- Risk register: `ARCHITECTURE-ASSESSMENT.md` Section 8, Risk 9
- Query subsystem profile: `TOPOLOGY-INVENTORY.md` Section 5.8
- Query data flow: `DEPENDENCY-MAP.md` Section 5.2

### Key Source Files

- `src/autom8_asana/query/engine.py` (QueryEngine)
- `src/autom8_asana/services/query_service.py` (EntityQueryService)
- `src/autom8_asana/services/universal_strategy.py` (UniversalStrategy)
- `src/autom8_asana/api/routes/query.py` (query endpoints)

---

## Implementation Sketch

### Step 1: Define DataFrameProvider protocol

Create in `src/autom8_asana/protocols/dataframe_provider.py` (or `query/protocols.py`):
```python
class DataFrameProvider(Protocol):
    async def get_dataframes(
        self, entity_type: str, ...
    ) -> list[DataFrame]: ...
```

### Step 2: Implement protocol on UniversalStrategy

Modify `services/universal_strategy.py` to satisfy `DataFrameProvider`.
This should require minimal changes -- the method likely already exists
with a compatible signature.

### Step 3: Refactor QueryEngine constructor

Change `query/engine.py` to accept `DataFrameProvider` instead of
importing `EntityQueryService`:
- Constructor takes `provider: DataFrameProvider`
- Remove direct import of `services.query_service`
- Replace `to_pascal_case` import with local utility or protocol method

### Step 4: Update API route DI

In `api/routes/query.py`, inject `UniversalStrategy` as the `DataFrameProvider`
via FastAPI `Depends()`.

### Step 5: Verify

- Run: `pytest tests/unit/query/ -x`
- Run: `pytest tests/api/ -k query -x`
- Run: `pytest tests/integration/ -x`
- Write a test that creates QueryEngine with a mock DataFrameProvider

---

## Do NOT

- Change the query predicate AST or compilation logic
- Modify the aggregation engine
- Change API response shapes
- Alter the query guards or limits

---

## Green-to-Green Gates

- All query tests pass unchanged
- API integration tests for query endpoints pass
- QueryEngine can be instantiated with a mock provider (new test)
- No imports of `services/` in `query/engine.py`

---

## Definition of Done

- [ ] DataFrameProvider protocol defined
- [ ] UniversalStrategy implements DataFrameProvider
- [ ] QueryEngine accepts provider via constructor (no direct service import)
- [ ] API routes inject provider via FastAPI DI
- [ ] Mock-based QueryEngine test added
- [ ] Full test suite green
- [ ] MEMORY.md updated: "WS-QUERY: query engine decoupling DONE"
