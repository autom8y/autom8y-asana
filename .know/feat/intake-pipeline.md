---
domain: feat/intake-pipeline
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/api/routes/intake_*.py"
  - "./src/autom8_asana/services/intake_*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# Intake Business Creation Pipeline

## Purpose and Design Rationale

The intake pipeline is the S2S JWT-authenticated boundary for provisioning and looking up business records in Asana. Three concerns: **Creation** (7-phase hierarchy construction), **Resolution** (phone/email -> GID lookup), **Custom field writes** (named field -> GID resolution + partial success).

Hidden from OpenAPI spec (`include_in_schema=False`). Primary caller: `autom8y-data` service.

Key design decisions: `found=False` instead of 404 (ADR-INT-001), email-then-phone priority with no name matching (ADR-INT-002), idempotent process routing, 7-phase strictly ordered creation with Phase 2 parallel holder creation.

## Implementation Map

### Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/intake/business` | POST | Full 7-phase hierarchy creation |
| `/v1/intake/route` | POST | Idempotent process routing |
| `/v1/resolve/business` | POST | Phone -> GID via DynamicIndexCache |
| `/v1/resolve/contact` | POST | Email/phone -> contact within business |
| `/v1/tasks/{gid}/custom-fields` | POST | Named custom field writes |

### Services

`IntakeCreateService` (7-phase orchestration + process routing), `IntakeResolveService` (business + contact resolution), `IntakeCustomFieldService` (field name -> GID resolution + write).

### Key Files

3 route files (`intake_create.py`, `intake_resolve.py`, `intake_custom_fields.py`), 3 service files, 3 model files.

## Boundaries and Failure Modes

- Per-request `AsanaClient` (bypasses `ClientPool`) -- divergence from shared-cache pattern
- `DynamicIndexCache` and `EntityProjectRegistry` accessed via module-level functions that catch all exceptions and return empty/None
- Interop contract with `autom8y-interop/asana/models.py` not mechanically enforced in CI
- Contact holder detection by name substring (`"contact_holder"` in subtask name)
- `consultation` process type absent from `VALID_PROCESS_TYPES`

## Knowledge Gaps

1. `DynamicIndexCache` internals (warming lifecycle, eviction) not read.
2. Interop contract validation mechanism unknown.
3. Per-request AsanaClient performance impact under high volume not characterized.
