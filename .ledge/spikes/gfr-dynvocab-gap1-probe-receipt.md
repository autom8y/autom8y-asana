---
type: spike-receipt
initiative: gfr-dynvocab
sprint: sprint-1
probe: GAP-1
canary: b167331c-536f-4996-9b2d-2f696f35f556
mode: offline
source: fixture
fired_by: ci
fired_at: 2026-06-25T12:41:17.762534+00:00
opt_fields_ref: "src/autom8_asana/models/business/fields.py:232-251 (STANDARD_TASK_OPT_FIELDS)"
verdict: OFFLINE_DRY_RUN
---

# GAP-1 Probe Receipt — does bare custom_fields return asset_id populated?

## Verdict
OFFLINE_DRY_RUN — fixture-based; live fire pending operator command

## Evidence (verbatim)
- mode / source: offline / fixture
- asset_id cf entry (verbatim slice): {"gid": "1210000000000001", "name": "Asset ID", "resource_subtype": "text", "text_value": "asset-001, asset-002"}
- asset_id present: True
- asset_id populated: True
- total custom_fields returned: 2
- opt_fields requested: src/autom8_asana/models/business/fields.py:232-251 (STANDARD_TASK_OPT_FIELDS)

## PT-01 fork input
- HYP1_CONFIRMED → OPTION A (free-tail): proceed to sprint-2 task-based tail. Default.
- HYP1_REFUTED   → OPTION B (frame-based fallback ~2x): re-shape sprint-2 before tail build.
- OFFLINE_DRY_RUN → verdict pending; operator must run the live fire (TDD §3.6).
