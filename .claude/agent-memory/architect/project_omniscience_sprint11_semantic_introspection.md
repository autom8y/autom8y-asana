---
name: Omniscience Sprint 11 Semantic Introspection ADR
description: Architecture decision for embedding YAML semantic annotations into ColumnDef.description and exposing via introspection endpoints
type: project
---

Sprint 11 ADR produced at `.ledge/decisions/ADR-omniscience-semantic-introspection.md`.

**Why:** AI agents and n8n workflows need self-describing field metadata (business meaning, enum values, cascade behavior, numeric ranges) discoverable through existing introspection endpoints, without reading documentation files.

**How to apply:** Four decisions:
- D1: YAML annotations appended after `\n---\n` delimiter in ColumnDef.description (Strategy A from Sprint 7)
- D2: Centralized annotation registry at `src/autom8_asana/dataframes/annotations.py` -- enrichment applied lazily at introspection time, NOT at schema definition time. Schema files unchanged.
- D3: Existing endpoints enhanced with `include_semantic` / `semantic_type` / `include_enums` query params. New enum detail endpoint at `GET /v1/resolve/{entity_type}/schema/enums/{field_name}`.
- D4: Contract tests verify cascade annotation presence, consistency with CascadingFieldDef registry, and backward compatibility of `split("---")[0]` parsing.

Scope: 19 column-schema combinations (12 cascade from Sprint 9, 7 HD-02 priority from Sprint 7).
Constraint: No changes to ColumnDef model class (frozen=True).
