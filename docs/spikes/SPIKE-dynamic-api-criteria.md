# SPIKE: Dynamic API Criteria for Schema-Driven Resolution

---
id: SPIKE-dynamic-api-criteria
title: Dynamic API Criteria Patterns
status: complete
created: 2026-01-08
timebox: 1h
decision: ADOPT Option B (Hybrid Approach)
---

## Research Question

What is the best approach to expose dynamic/flexible query criteria in our resolver REST API, following industry standards and modern best practices?

### Context

The backend (`UniversalResolutionStrategy` + `DynamicIndex`) already supports querying by ANY column in the entity schema. However, the API layer constrains this with a fixed Pydantic model:

```python
class ResolutionCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: str | None = None      # Hardcoded
    vertical: str | None = None   # Hardcoded
    offer_id: str | None = None   # Hardcoded
    # ... only 6 fields exposed
```

Meanwhile, schemas define 20+ queryable columns per entity type.

---

## Industry Survey

### Elasticsearch Query DSL

Uses nested filter objects with explicit field names:

```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "office_phone": "+15551234567" } },
        { "term": { "vertical": "dental" } }
      ]
    }
  }
}
```

**Pros**: Extremely flexible, supports operators
**Cons**: Complex, overkill for simple equality lookups

### Stripe Search API

Uses a query string DSL:

```
GET /v1/customers/search?query=email:"jenny@example.com" AND metadata["key"]:"value"
```

**Pros**: Powerful, single string
**Cons**: Requires parser, learning curve

### GraphQL Filtering

Uses typed input objects with dynamic fields:

```graphql
query {
  units(where: { office_phone: { eq: "+15551234567" }, vertical: { eq: "dental" } }) {
    gid
    name
  }
}
```

**Pros**: Strongly typed, self-documenting via schema
**Cons**: Requires GraphQL infrastructure

### OData / JSON:API

Uses query parameters with standardized filter syntax:

```
GET /units?$filter=office_phone eq '+15551234567' and vertical eq 'dental'
```

**Pros**: Standardized, well-documented
**Cons**: String parsing, complex operators

### Airtable / Notion APIs

Use simple key-value filter objects:

```json
{
  "filter": {
    "office_phone": "+15551234567",
    "vertical": "dental"
  }
}
```

**Pros**: Simple, intuitive, easy to validate
**Cons**: Limited to equality (sufficient for our use case)

---

## Options Comparison

| Criteria | Option A: `extra="allow"` | Option B: Hybrid | Option C: Filter Syntax | Option D: Query DSL |
|----------|---------------------------|------------------|-------------------------|---------------------|
| **Implementation** | 1 line change | ~20 lines | ~50 lines | ~200 lines |
| **Type Safety** | Weak (accepts anything) | Strong (validated) | Strong | Strong |
| **OpenAPI Docs** | Poor (no schema) | Good (additionalProperties) | Good | Complex |
| **Error Messages** | Backend only | Clear field errors | Clear | Complex |
| **Breaking Changes** | None | None | Minor | Major |
| **Operator Support** | Equality only | Equality only | Extensible | Full |
| **Industry Alignment** | Common | Airtable/Notion | Elasticsearch | OData |

---

## Recommendation: Option B (Hybrid Approach)

### Rationale

1. **Simplicity**: Our use case is equality-based lookups, not complex queries
2. **Backwards Compatible**: Existing clients continue working unchanged
3. **Type Safe**: Pydantic validates structure, backend validates field names
4. **Discoverable**: Schema endpoint enables API consumers to find valid fields
5. **Industry Aligned**: Matches Airtable/Notion patterns for simple filtering

### Implementation

#### 1. Update ResolutionCriterion Model

```python
class ResolutionCriterion(BaseModel):
    """Single lookup criterion - accepts any schema column.

    Common fields are typed for validation and documentation.
    Additional schema columns accepted via extra="allow".
    """
    model_config = ConfigDict(extra="allow")  # <-- Key change

    # Documented common fields (with validation)
    phone: str | None = None
    vertical: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_e164(cls, v: str | None) -> str | None:
        # Existing E.164 validation
        ...
```

#### 2. Add Schema Discovery Endpoint

```python
@router.get("/{entity_type}/schema")
async def get_entity_schema(
    entity_type: str,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> dict:
    """Return queryable fields for entity type.

    Enables API consumers to discover valid criterion fields.
    """
    from autom8_asana.dataframes.models.registry import SchemaRegistry

    registry = SchemaRegistry.get_instance()
    schema = registry.get_schema(entity_type.capitalize())

    return {
        "entity_type": entity_type,
        "version": schema.version,
        "queryable_fields": [
            {
                "name": col.name,
                "type": col.dtype,
                "description": col.description,
            }
            for col in schema.columns
            if col.source is not None or col.name == "gid"
        ],
    }
```

#### 3. Backend Validation (Already Exists)

The `UniversalResolutionStrategy.validate_criterion()` method already validates criterion fields against the schema:

```python
def validate_criterion(self, criterion: dict[str, Any]) -> list[str]:
    """Validate criterion fields exist in schema."""
    schema = self._get_schema()
    valid_columns = set(schema.column_names())

    errors = []
    for field in criterion.keys():
        mapped_field = LEGACY_FIELD_MAPPING.get(field, field)
        if mapped_field not in valid_columns:
            errors.append(f"Unknown field '{field}'. Valid: {sorted(valid_columns)}")

    return errors
```

---

## Migration Strategy

### Phase 1: Enable Dynamic Fields (Non-Breaking)

1. Change `extra="forbid"` → `extra="allow"`
2. Existing requests continue working (phone, vertical, etc.)
3. New fields immediately available (mrr, specialty, etc.)

### Phase 2: Add Schema Discovery

1. Add `GET /v1/resolve/{entity_type}/schema` endpoint
2. Document in API reference
3. Update client SDKs (if any)

### Phase 3: Deprecate Legacy Field Names (Optional)

1. Log warnings when legacy names used (phone → office_phone)
2. Update documentation to prefer schema column names
3. Eventually remove legacy mapping (major version bump)

---

## OpenAPI Documentation

With `extra="allow"`, OpenAPI 3.0 generates:

```yaml
ResolutionCriterion:
  type: object
  properties:
    phone:
      type: string
      description: E.164 phone number (maps to office_phone)
    vertical:
      type: string
      description: Business vertical
  additionalProperties: true  # <-- Indicates dynamic fields accepted
```

The schema discovery endpoint provides runtime documentation for valid fields.

---

## Security Considerations

| Risk | Mitigation |
|------|------------|
| Field injection | Backend validates against schema allowlist |
| SQL injection | Not applicable (Polars DataFrame, no SQL) |
| DoS via complex queries | Max 1000 criteria per request (existing limit) |
| Enumeration attacks | Schema endpoint requires authentication |

---

## Follow-Up Actions

1. [ ] Implement Option B changes to `ResolutionCriterion`
2. [ ] Add schema discovery endpoint
3. [ ] Update API documentation
4. [ ] Add integration test for dynamic field resolution

---

## Conclusion

**ADOPT Option B (Hybrid Approach)** - Change `extra="forbid"` to `extra="allow"` on the ResolutionCriterion model and add a schema discovery endpoint. This unlocks full dynamic querying with minimal code change, no breaking changes, and good developer experience.

The implementation is approximately 20 lines of code changes to fully expose the backend's existing capabilities.
