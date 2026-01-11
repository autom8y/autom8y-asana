---
sprint_id: sprint-asset-edit-resolution-20260111
session_id: session-20260107-180258-f44cd3cb
sprint_name: AssetEdit & AssetEditHolder Resolution Support
initiative: EntityTypeDetectionFix
created_at: 2026-01-11T12:00:00Z
status: active
goal: "Add AssetEdit and AssetEditHolder entity types to the /resolve/{entity} API endpoint"
complexity: MODULE
active_rite: 10x-dev-pack
source_analysis: "Gap analysis from deep-dive exploration of /resolve/ and Asana entity models"
schema_version: "1.0"
current_task: TASK-001
last_updated: 2026-01-11T12:00:00Z
---

# Sprint: AssetEdit & AssetEditHolder Resolution Support

## Sprint Goal

Enable resolution of AssetEdit and AssetEditHolder entities via the `/resolve/{entity}` API endpoint,
following existing patterns from unit, business, offer, and contact entities.

## Context Summary

**AssetEdit** and **AssetEditHolder** are fully implemented at the model layer:
- `AssetEditHolder`: Defined in `business.py:97-113`, PRIMARY_PROJECT_GID: `1203992664400125`
- `AssetEdit`: Defined in `asset_edit.py`, PRIMARY_PROJECT_GID: `1202204184560785`
- Both entities are registered in the EntityType enum and support 5-tier detection

**Gap**: Resolution layer components are missing:
1. No DataFrame schema for AssetEdit or AssetEditHolder
2. Not registered in SchemaRegistry
3. Not in ENTITY_MODEL_MAP
4. No DEFAULT_KEY_COLUMNS defined
5. No ENTITY_ALIASES defined

## Requirements Gathered

| Aspect | Decision |
|--------|----------|
| **Scope** | Both asset_edit and asset_edit_holder |
| **asset_edit lookup key** | `offer_id` (integer, validated) |
| **asset_edit_holder lookup key** | `office_phone` only (cascading from Business) |
| **Field aliases** | Inherit process aliases (asset_edit → process normalization) |
| **Enrichment** | All 20 fields (9 Process + 11 AssetEdit) |
| **Multi-match behavior** | Follow existing patterns (return all matches) |
| **Cross-entity resolution** | Not included in response |
| **Testing** | Both unit and integration tests |

## Success Criteria

- [ ] AssetEdit DataFrame schema with 20 fields (9 Process + 11 AssetEdit)
- [ ] AssetEditHolder DataFrame schema with office_phone lookup
- [ ] Both schemas registered in SchemaRegistry
- [ ] `POST /v1/resolve/asset_edit` returns matching GIDs
- [ ] `POST /v1/resolve/asset_edit_holder` returns matching GIDs
- [ ] Field enrichment works for all 20 AssetEdit fields
- [ ] All existing resolver tests pass
- [ ] New unit and integration tests pass

## Task Breakdown

### TASK-001: Create AssetEdit DataFrame Schema
- **Status**: in_progress
- **Agent**: principal-engineer
- **Complexity**: MEDIUM
- **Depends On**: none
- **Produces**: `src/autom8_asana/dataframes/schemas/asset_edit.py`
- **Details**:
  - 20 columns total: 9 Process fields + 11 AssetEdit fields
  - Process fields: started_at, process_completed_at, process_notes, status, priority, process_due_date, assigned_to, vertical (from mixin), specialty
  - AssetEdit fields: asset_approval, asset_id, editor, reviewer, offer_id, raw_assets, review_all_ads, score, specialty (multi-enum), template_id, videos_paid

### TASK-002: Create AssetEditHolder DataFrame Schema
- **Status**: pending
- **Agent**: principal-engineer
- **Complexity**: SMALL
- **Depends On**: none
- **Produces**: `src/autom8_asana/dataframes/schemas/asset_edit_holder.py`
- **Details**:
  - Extends BASE_SCHEMA
  - Lookup key: office_phone (cascading from Business)

### TASK-003: Register Schemas in Registry
- **Status**: pending
- **Agent**: principal-engineer
- **Complexity**: SMALL
- **Depends On**: TASK-001, TASK-002
- **Produces**: Updates to `dataframes/models/registry.py`, `dataframes/schemas/__init__.py`
- **Details**:
  - Add ASSET_EDIT_SCHEMA and ASSET_EDIT_HOLDER_SCHEMA to _ensure_initialized()
  - Export from __init__.py

### TASK-004: Add to ENTITY_MODEL_MAP
- **Status**: pending
- **Agent**: principal-engineer
- **Complexity**: SMALL
- **Depends On**: TASK-003
- **Produces**: Updates to `api/main.py`
- **Details**:
  - Add "asset_edit": AssetEdit
  - Add "asset_edit_holder": AssetEditHolder

### TASK-005: Add DEFAULT_KEY_COLUMNS
- **Status**: pending
- **Agent**: principal-engineer
- **Complexity**: SMALL
- **Depends On**: none
- **Produces**: Updates to `services/universal_strategy.py`
- **Details**:
  - Add "asset_edit": ["offer_id"]
  - Add "asset_edit_holder": ["office_phone"]

### TASK-006: Add ENTITY_ALIASES
- **Status**: pending
- **Agent**: principal-engineer
- **Complexity**: SMALL
- **Depends On**: none
- **Produces**: Updates to `services/resolver.py`
- **Details**:
  - Add "asset_edit": ["process"] for Process field inheritance

### TASK-007: Create Unit Tests
- **Status**: pending
- **Agent**: principal-engineer
- **Complexity**: MEDIUM
- **Depends On**: TASK-001, TASK-002, TASK-003
- **Produces**: `tests/unit/dataframes/schemas/test_asset_edit_schema.py`

### TASK-008: Create Integration Tests
- **Status**: pending
- **Agent**: principal-engineer
- **Complexity**: MEDIUM
- **Depends On**: TASK-004, TASK-005, TASK-006
- **Produces**: Updates to `tests/api/test_routes_resolver.py`

### TASK-009: Run Full Test Suite
- **Status**: pending
- **Agent**: qa-adversary
- **Complexity**: SMALL
- **Depends On**: TASK-007, TASK-008
- **Produces**: Test report

## Dependency Graph

```
TASK-001 (AssetEdit Schema)  TASK-002 (AssetEditHolder Schema)  TASK-005  TASK-006
      │                              │                            │         │
      └──────────┬───────────────────┘                            │         │
                 │                                                │         │
                 ▼                                                │         │
           TASK-003 (Register)                                    │         │
                 │                                                │         │
                 ▼                                                │         │
           TASK-004 (Model Map)                                   │         │
                 │                                                │         │
                 │                                                │         │
                 ▼                                                ▼         ▼
           TASK-007 (Unit Tests) ◄─────────────────────── TASK-008 (Integration)
                 │                                                │
                 └──────────────────────┬─────────────────────────┘
                                        │
                                        ▼
                                  TASK-009 (QA)
```

## Field Mapping Reference

### Process Fields (9 from process.py)
| Field | Asana Source | Type |
|-------|--------------|------|
| started_at | cf:Started At | Utf8 |
| process_completed_at | cf:Process Completed At | Utf8 |
| process_notes | cf:Process Notes | Utf8 |
| status | cf:Status | Utf8 |
| priority | cf:Priority | Utf8 |
| process_due_date | cf:Due Date | Utf8 |
| assigned_to | cf:Assigned To | List[Utf8] |
| vertical | cascade:Vertical | Utf8 |
| specialty | cf:Specialty | Utf8 |

### AssetEdit Fields (11 from asset_edit.py)
| Field | Asana Source | Type |
|-------|--------------|------|
| asset_approval | cf:Asset Approval | Utf8 |
| asset_id | cf:Asset ID | Utf8 |
| editor | cf:Editor | List[Utf8] |
| reviewer | cf:Reviewer | List[Utf8] |
| offer_id | cf:Offer ID | Int64 |
| raw_assets | cf:Raw Assets | Utf8 |
| review_all_ads | cf:Review All Ads | Boolean |
| score | cf:Score | Decimal |
| template_id | cf:Template ID | Int64 |
| videos_paid | cf:Videos Paid | Int64 |
| specialty | cf:Specialty | List[Utf8] |

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| offer_id type mismatch | Low | Medium | Validate as Int64, error on string |
| Missing cascading fields | Low | Low | Use Process pattern for inheritance |
| Schema version conflict | Low | Low | Use 1.0.0 for new schemas |

## Out of Scope

- Cross-entity resolution (unit_gid/offer_gid in response)
- OpenAPI documentation updates
- Additional holder types (DNA, Reconciliation, Videography)
