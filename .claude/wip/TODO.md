# Deferred Work Items: Entity DataFrame Extensibility

Per TDD-ENTITY-EXT-001 Task 8. Items identified during implementation but
explicitly out of scope for this sprint.

## cascade:MRR Source Annotation Investigation

**Context**: OFFER_SCHEMA declares `mrr` with `source="cascade:MRR"` and `dtype="Utf8"`.
UNIT_SCHEMA declares `mrr` with `source="cf:MRR"` and `dtype="Decimal"`. The Offer cascade
implies MRR is resolved by walking the parent chain to the Unit ancestor. However, MRR is
often directly populated on the Offer task itself.

**Issue**: The dtype mismatch (Utf8 vs Decimal) means Offer MRR values may be string
representations while Unit MRR values are numeric Decimals. This affects aggregation
queries that join Offer and Unit data.

**Action**: Investigate whether `cascade:MRR` should be `cf:MRR` (direct custom field)
and whether dtype should be `Decimal` to match Unit. Consider unit-of-work save pattern
implications for field overwrite enforcement when parent value changes.

## Traversal Unification Initiative

**Context**: Multiple entity types need parent-chain traversal for derived fields:
- Offer: `office` (walk to Business ancestor), `vertical_id` (walk to Vertical model)
- AssetEdit: `office_phone`, `vertical`, `offer_id` (walk through holder -> unit -> offer chain)
- Business: `name` (derived from task.name, but could need hierarchy context)
- UnitExtractor already implements `_extract_office_async()` for Business ancestor resolution

**Issue**: Each entity's traversal needs are different. AssetEdit may need to walk
`[office_phone, vertical, offer_id] -> ... -> unit -> offer` with all 3 fields. A
one-size-fits-all parent-chain walker does not capture this nuance.

**Action**: Design a generalized traversal mechanism that supports multi-field resolution
across entity hierarchies. This should be a separate initiative with its own PRD/TDD cycle.

## MRR Deduplication Documentation

**Context**: MRR should be aggregated at the Unit level, not the Offer level. Multiple
Offers under a single Unit share the same MRR value. Summing MRR across Offers without
dedup inflates the total.

**Action**: Document the correct aggregation pattern: `group_by(office_phone, vertical)`
at Unit level, then join Offer counts. Add this to query examples documentation.

## Query CLI Utility

**Context**: Ad-hoc queries like "sum MRR for active offers" require boilerplate setup
(build registry, create builder, run query). A script-level entry point would reduce
friction for one-off data exploration.

**Action**: Create a CLI tool or script entry point for common aggregation queries.
Low priority -- not blocking production workloads.

## B6: is_completed vs completed Naming Documentation

**Context**: BASE_SCHEMA uses column name `is_completed` with `source="completed"`. The
Asana API field is `completed` (boolean). TaskRow uses `is_completed` as the field name.
This naming asymmetry is intentional (Python convention for boolean properties) but
undocumented.

**Action**: Add a note to BASE_SCHEMA or TaskRow explaining the naming convention.

## Audit Entity Traversal Needs

**Context**: Business, AssetEdit, and AssetEditHolder schemas currently use SchemaExtractor,
which returns None for all derived fields (source=None). When traversal logic is needed for
these entities, they should graduate from SchemaExtractor to hand-coded extractors.

**Entities to audit**:
- Business: Does it need parent-chain traversal for any field?
- AssetEdit: `vertical` and `office_phone` are cascade: fields (handled). Are there
  derived fields needed in the future (e.g., offer resolution)?
- AssetEditHolder: Currently only `office_phone` (cascade:). Any future derived needs?

**Action**: When the traversal unification initiative begins, audit these entities to
determine which need dedicated extractors vs which can stay on SchemaExtractor.
