# Documentation Structure: Search Interface v2.0

Version: 1.0
Date: 2025-12-27
Author: Information Architect Agent
Status: Ready for Tech Writer

---

## Executive Summary

This specification defines the documentation structure for the Search Interface v2.0 Query Builder feature. The implementation is complete (commit `818e33e`) and includes:

- **SearchService**: Primary search interface with async/sync APIs
- **SearchCriteria/FieldCondition**: Query specification models
- **SearchResult/SearchHit**: Result models with matched field tracking
- **Entity convenience methods**: `find_offers_async()`, `find_units_async()`, `find_businesses_async()`

**Design Principle**: Documentation follows the Information Architecture Spec (2025-12-24) with flat structure, clear audience targeting, and 30-second findability.

---

## Document Inventory

| Document | Path | Audience | Priority |
|----------|------|----------|----------|
| User Guide | `docs/guides/search-query-builder.md` | SDK users | P1 - Critical |
| API Reference | `docs/reference/REF-search-api.md` | Developers implementing | P1 - Critical |
| Migration Guide | `docs/migration/MIGRATION-search-v2.md` | Existing v1.0 users | P2 - High |
| Cookbook | `docs/guides/search-cookbook.md` | SDK users (intermediate) | P2 - High |
| CHANGELOG Entry | `CHANGELOG.md` (update) | All users | P1 - Critical |

---

## Document Outlines

### 1. User Guide

**Path**: `docs/guides/search-query-builder.md`

**Audience**: SDK users who need to find entities by field values

**Purpose**: Teach users how to search for Asana entities (Offers, Units, Businesses) using field-value matching

**Prerequisites**: [quickstart.md](concepts.md), [concepts.md](concepts.md)

**Estimated Length**: 800-1200 words

**Sections**:

```
1. Introduction
   - What Search v2.0 does (field-based GID lookup)
   - When to use it (finding entities by custom field values)
   - Performance characteristics (Polars-backed, sub-millisecond)

2. Quick Start
   - Minimal example: find by single field
   - Via AsanaClient access pattern
   - Code snippet with output

3. Basic Usage
   3.1 Finding Entities by Field Value
       - Dictionary criteria (simple case)
       - Multiple field AND matching
       - Code example with explanation

   3.2 Using Convenience Methods
       - find_offers_async() / find_offers()
       - find_units_async() / find_units()
       - find_businesses_async() / find_businesses()
       - Snake_case to Title Case normalization
       - Code example with output

4. Advanced Usage
   4.1 SearchCriteria for Complex Queries
       - Building explicit SearchCriteria
       - FieldCondition operators (eq, contains, in)
       - Combinator logic (AND default, OR available)

   4.2 Limiting Results
       - limit parameter
       - find_one_async() for single-match queries

   4.3 Entity Type Filtering
       - entity_type parameter
       - Combining with field criteria

5. Working with Results
   - SearchResult structure (hits, total_count, query_time_ms, from_cache)
   - SearchHit structure (gid, entity_type, name, matched_fields)
   - Iterating results
   - Code example

6. Async vs Sync APIs
   - When to use async (recommended for most cases)
   - Sync wrapper availability
   - Performance considerations

7. Error Handling
   - Graceful degradation (empty results on error)
   - find_one_async raises on multiple matches
   - Logging for debugging

8. Related Documentation
   - [API Reference](../reference/REF-search-api.md)
   - [Search Cookbook](search-cookbook.md)
   - [Migration Guide](../migration/MIGRATION-search-v2.md) (if upgrading)
```

---

### 2. API Reference

**Path**: `docs/reference/REF-search-api.md`

**Audience**: Developers needing complete method signatures and parameter details

**Purpose**: Exhaustive reference for all SearchService methods and models

**Estimated Length**: 1500-2000 words

**Sections**:

```
1. Overview
   - Module location: autom8_asana.search
   - Public exports: SearchService, SearchCriteria, SearchResult, SearchHit, FieldCondition

2. SearchService Class
   2.1 Constructor
       - Parameters: cache (CacheProvider), dataframe_integration (optional)
       - Default behavior

   2.2 Primary Methods
       - find_async(project_gid, criteria, entity_type, limit) -> SearchResult
       - find_one_async(project_gid, criteria, entity_type) -> SearchHit | None
       - find(project_gid, criteria, entity_type, limit) -> SearchResult [sync]
       - find_one(project_gid, criteria, entity_type) -> SearchHit | None [sync]

       For each:
       - Full signature with types
       - Parameter descriptions
       - Return type
       - Raises (if any)
       - Example

   2.3 Convenience Methods
       - find_offers_async(project_gid, **field_values) -> list[str]
       - find_units_async(project_gid, **field_values) -> list[str]
       - find_businesses_async(project_gid, **field_values) -> list[str]
       - Sync variants: find_offers(), find_units(), find_businesses()

       For each:
       - Signature
       - Automatic entity_type filtering behavior
       - Field name normalization (snake_case -> Title Case)
       - Example

   2.4 Cache Management
       - set_project_dataframe(project_gid, df) -> None
       - clear_project_cache(project_gid=None) -> None
       - DEFAULT_PROJECT_DF_TTL constant (300 seconds)

3. Model Classes
   3.1 FieldCondition
       - field: str (field name)
       - value: str | list[str] (match value(s))
       - operator: Literal["eq", "contains", "in"] (default: "eq")
       - Operator behavior table
       - Examples for each operator

   3.2 SearchCriteria
       - conditions: list[FieldCondition]
       - combinator: Literal["AND", "OR"] (default: "AND")
       - project_gid: str
       - entity_type: str | None
       - limit: int | None
       - Example construction

   3.3 SearchHit
       - gid: str
       - entity_type: str | None
       - name: str | None
       - matched_fields: dict[str, str]
       - Usage example

   3.4 SearchResult
       - hits: list[SearchHit]
       - total_count: int
       - query_time_ms: float
       - from_cache: bool
       - Iteration example

4. Field Name Normalization
   - Automatic case-insensitive matching
   - Snake_case to Title Case conversion
   - NameNormalizer usage (internal)
   - Examples of successful matches

5. Error Handling
   - Graceful degradation behavior
   - ValueError from find_one_async on multiple matches
   - Logging configuration

6. Related Documentation
   - [User Guide](../guides/search-query-builder.md)
   - [Search Cookbook](../guides/search-cookbook.md)
```

---

### 3. Migration Guide

**Path**: `docs/migration/MIGRATION-search-v2.md`

**Audience**: Users upgrading from any prior search patterns or no search to v2.0

**Purpose**: Provide clear upgrade path with before/after examples

**Estimated Length**: 600-800 words

**Sections**:

```
1. What's New in Search v2.0
   - Polars-based DataFrame filtering (vs previous approaches)
   - Unified SearchService API
   - Async-first with sync wrappers
   - Automatic field name normalization

2. Breaking Changes
   - None (new feature, additive)
   - OR: List any deprecated patterns if applicable

3. Migration Path
   3.1 From Manual DataFrame Filtering
       Before: Direct Polars filter expressions
       After: SearchService.find_async()
       Side-by-side code example

   3.2 From Loop-Based Searching
       Before: Iterating tasks and checking fields
       After: SearchService with field criteria
       Side-by-side code example

   3.3 From No Search
       - Getting started checklist
       - Link to User Guide

4. API Mapping Table
   | Old Pattern | New Pattern |
   |-------------|-------------|
   | df.filter(pl.col("Field") == val) | search.find_async(project_gid, {"Field": val}) |
   | Manual GID extraction | SearchResult.hits[].gid |
   | ... | ... |

5. Cache Pre-population
   - When to use set_project_dataframe()
   - Integration with ProjectDataFrameBuilder
   - TTL considerations (5-minute default)

6. Testing Your Migration
   - Validation checklist
   - Common issues and fixes

7. Related Documentation
   - [User Guide](../guides/search-query-builder.md)
   - [API Reference](../reference/REF-search-api.md)
```

---

### 4. Cookbook

**Path**: `docs/guides/search-cookbook.md`

**Audience**: SDK users who understand basics and want common patterns/recipes

**Purpose**: Provide copy-paste solutions for common search scenarios

**Estimated Length**: 1000-1400 words

**Sections**:

```
1. Introduction
   - How to use this cookbook
   - Prerequisites: User Guide familiarity

2. Common Patterns

   2.1 Find Entity by Phone Number
       - Use case: CRM lookup
       - Code with field normalization example
       - Handling multiple matches

   2.2 Find All Active Offers in Vertical
       - Use case: Pipeline filtering
       - Compound criteria example
       - Result iteration

   2.3 Find Single Entity (Unique Match)
       - Use case: Lookup by unique identifier
       - find_one_async with error handling
       - Graceful handling of no-match

   2.4 Search Multiple Values (OR within field)
       - Use case: Finding entities in any of several statuses
       - FieldCondition with list value
       - operator="in" usage

   2.5 Substring Matching
       - Use case: Partial name search
       - operator="contains" usage
       - Performance considerations

   2.6 Pre-populating Cache for Batch Operations
       - Use case: Bulk search operations
       - set_project_dataframe pattern
       - TTL management

3. Integration Patterns

   3.1 Search + Update Workflow
       - Find entities, modify, commit via SaveSession
       - Complete code example

   3.2 Search with DataFrame Builder
       - Build DataFrame, cache it, search multiple times
       - Code example with ProjectDataFrameBuilder

4. Performance Tips
   - Cache pre-population for repeated searches
   - Batch multiple criteria vs multiple searches
   - Async usage for concurrent operations

5. Troubleshooting
   - "Empty results when I expect matches"
     - Check field name casing
     - Verify DataFrame is cached
     - Check project_gid

   - "Multiple matches when expecting one"
     - Use more specific criteria
     - Consider limit parameter

   - "Search is slow"
     - Pre-populate cache
     - Reduce DataFrame size if possible

6. Related Documentation
   - [User Guide](search-query-builder.md)
   - [API Reference](../reference/REF-search-api.md)
```

---

### 5. CHANGELOG Entry

**Path**: `CHANGELOG.md` (update existing file)

**Audience**: All users reviewing release notes

**Purpose**: Announce v2.0 search capability

**Estimated Length**: 150-250 words

**Content Specification**:

```
## [Unreleased] or [X.X.X] - YYYY-MM-DD

### Added

- **Search Interface v2.0**: New SearchService for field-based entity lookup
  - `SearchService.find_async()` and `find()` for flexible queries
  - `SearchService.find_one_async()` for single-entity lookups
  - Convenience methods: `find_offers_async()`, `find_units_async()`, `find_businesses_async()`
  - Automatic field name normalization (snake_case to Title Case)
  - Polars-backed filtering for sub-millisecond query performance
  - SearchCriteria model with support for `eq`, `contains`, `in` operators
  - AND/OR combinator support for complex queries
  - Entity type filtering
  - Result limiting
  - Async-first API with sync wrappers
  - Automatic DataFrame caching with 5-minute TTL
  - See [Search Query Builder Guide](docs/guides/search-query-builder.md)
```

---

## Dependencies and Creation Order

```
Phase 1 (Parallel - P1 Critical):
  [1] CHANGELOG Entry - Can be written immediately
  [2] API Reference - Defines terminology for other docs

Phase 2 (Sequential - P1/P2):
  [3] User Guide - References API Reference terminology
      Depends on: [2] API Reference

Phase 3 (Parallel - P2):
  [4] Cookbook - References User Guide patterns
      Depends on: [3] User Guide
  [5] Migration Guide - Standalone, references User Guide
      Depends on: [3] User Guide
```

**Recommended Writing Order**:
1. CHANGELOG Entry (quick win, announces feature)
2. API Reference (establishes canonical terminology)
3. User Guide (core learning document)
4. Cookbook (can parallel with Migration Guide)
5. Migration Guide (can parallel with Cookbook)

---

## Cross-Reference Strategy

### Inline Links
- User Guide links to API Reference for method details
- Cookbook links to User Guide for prerequisites
- Migration Guide links to User Guide for getting started

### See Also Sections
Each document ends with "Related Documentation" linking to:
- The other documents in this set
- Core concepts: `docs/guides/concepts.md`
- SaveSession for workflow integration: `docs/guides/save-session.md`

### INDEX.md Updates
Add entries to `docs/INDEX.md`:
- Reference: REF-search-api.md
- Guides: search-query-builder.md, search-cookbook.md
- Migration: MIGRATION-search-v2.md

---

## Naming Convention Compliance

| Document | Convention | Verified |
|----------|------------|----------|
| search-query-builder.md | kebab-case, descriptive | Yes |
| REF-search-api.md | REF- prefix per IA spec | Yes |
| MIGRATION-search-v2.md | MIGRATION- prefix per IA spec | Yes |
| search-cookbook.md | kebab-case, descriptive | Yes |

---

## Audience Mapping

| Audience | Entry Point | Key Documents |
|----------|-------------|---------------|
| New SDK user | User Guide | search-query-builder.md |
| Experienced developer | API Reference | REF-search-api.md |
| Existing user upgrading | Migration Guide | MIGRATION-search-v2.md |
| Looking for patterns | Cookbook | search-cookbook.md |

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| DOC-STRUCTURE-search-v2.md | /Users/tomtenuta/Code/autom8_asana/docs/plans/DOC-STRUCTURE-search-v2.md | Yes |

---

## Handoff to Tech Writer

This structure plan is ready for Tech Writer execution.

**Priority Order**:
1. CHANGELOG Entry (P1) - Immediate visibility
2. API Reference (P1) - Foundation for other docs
3. User Guide (P1) - Primary learning path
4. Cookbook (P2) - Extended patterns
5. Migration Guide (P2) - Upgrade support

**Source Files for Reference**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/search/service.py` - SearchService implementation
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/search/models.py` - Pydantic models
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/search/__init__.py` - Public API
- `/Users/tomtenuta/Code/autom8_asana/tests/unit/search/test_service.py` - Test examples

**Style Requirements**:
- Follow existing guide format (see `docs/guides/quickstart.md` as template)
- Code examples should be copy-paste ready
- Include async AND sync examples where applicable
- Use consistent terminology per API Reference
