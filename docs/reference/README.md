# Reference Documentation

## What Are Reference Docs?

Reference docs provide **authoritative, single-source-of-truth reference data** used across multiple features and documents. They are extracted when 3+ PRDs/TDDs duplicate the same explanation.

## When to Create a Reference Doc

Extract to reference when:
- Same concept explained in 3+ PRDs or TDDs
- Reference data needed by multiple systems (entity types, field catalogs)
- Algorithm specification used across features (cache staleness, TTL calculation)
- Protocol or interface shared by multiple clients

## Reference Doc Types

### Data Catalogs
Authoritative lists of entities, fields, or resources.

Examples:
- [REF-entity-type-table.md](REF-entity-type-table.md) - Business model hierarchy
- [REF-custom-field-catalog.md](REF-custom-field-catalog.md) - 108 custom fields

### Algorithm Specifications
Detailed specifications of algorithms used across features.

Examples:
- [REF-cache-staleness-detection.md](REF-cache-staleness-detection.md) - Staleness algorithms
- [REF-cache-ttl-strategy.md](REF-cache-ttl-strategy.md) - TTL calculation rules

### Protocol Specifications
Interface contracts and protocol definitions.

Examples:
- [REF-cache-provider-protocol.md](REF-cache-provider-protocol.md) - CacheProvider interface

## How to Use Reference Docs

### In PRDs/TDDs
Instead of duplicating explanations, link to reference:

**Before** (duplicated in 5 PRDs):
```markdown
## TTL Calculation
Base TTL is 3600 seconds for tasks, 7200 for projects...
[500 words of TTL logic]
```

**After** (single reference):
```markdown
## TTL Calculation
See [REF-cache-ttl-strategy](../reference/REF-cache-ttl-strategy.md) for TTL calculation details.
```

## Current Reference Docs

| Document | Type | Description |
|----------|------|-------------|
| [REF-entity-type-table.md](REF-entity-type-table.md) | Data Catalog | Business model entity hierarchy |
| [REF-custom-field-catalog.md](REF-custom-field-catalog.md) | Data Catalog | 108 custom fields across 5 models |
| [REF-cache-staleness-detection.md](REF-cache-staleness-detection.md) | Algorithm | Staleness detection algorithms |
| [REF-cache-ttl-strategy.md](REF-cache-ttl-strategy.md) | Algorithm | TTL calculation and progressive extension |
| [REF-cache-provider-protocol.md](REF-cache-provider-protocol.md) | Protocol | CacheProvider interface specification |

## Creating a New Reference Doc

1. Identify duplication across 3+ PRDs/TDDs
2. Extract common content to `REF-topic-name.md`
3. Write comprehensive, authoritative version
4. Update source PRDs/TDDs to link instead of duplicate
5. Add entry to this README and [INDEX.md](../INDEX.md)

## See Also

- [PRD README](../requirements/README.md) - When to create PRDs
- [INDEX.md](../INDEX.md) - Full documentation registry
