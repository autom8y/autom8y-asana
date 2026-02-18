# Entry-Point Bootstrap Audit (U-005)

**Sprint:** session-20260218-172712-e748524b
**Date:** 2026-02-18
**Branch:** sprint/arch-u005-si5-u001

---

## Bootstrap Mechanism

`models/business/__init__.py:64-66` calls `register_all_models()` at import time.
`_bootstrap.py` implements an idempotency guard (`_BOOTSTRAP_COMPLETE` flag) — repeated
calls are safe. Tier 1 detection (`tier1.py:91-105`) has a defensive re-bootstrap guard
that fires if `is_bootstrap_complete()` is False.

**Key rule:** Bootstrap runs if and only if `autom8_asana.models.business` (the package
`__init__.py`) is imported. Importing submodules directly (e.g., `models.business.contact`,
`models.business.detection`) does NOT trigger bootstrap.

---

## Audit Table

| Entry Point | Explicit Guard | Import Chain to `models.business`? | Uses Detection? | Risk |
|---|---|---|---|---|
| `lambda_handlers/cache_warmer.py` | YES (`_ensure_bootstrap()`) | Via guard | Yes | **COVERED** |
| `lambda_handlers/cache_invalidate.py` | NO | No path | No — cache ops only | **LOW RISK** |
| `lambda_handlers/insights_export.py` | NO | No path (deferred workflow import) | No — hardcoded project GID | **LOW RISK** |
| `lambda_handlers/conversation_audit.py` | NO | No — imports `models.business.contact` not `models.business` | YES — via `hydrate_from_gid_async` | **MEDIUM RISK** |
| `lambda_handlers/checkpoint.py` | NO | No | No — S3 checkpoint ops | **N/A** |
| `lambda_handlers/workflow_handler.py` | NO | No | No — generic factory | **N/A** |
| `api/main.py` | YES (line 35: explicit side-effect import) | Yes | Yes | **COVERED** |
| `entrypoint.py` | NO | No | No — thin dispatch shim | **N/A** |

---

## Detailed Analysis

### cache_warmer.py — COVERED
`_ensure_bootstrap()` called at the top of both `handler()` and `handler_async()`.
Pattern: lazy `import autom8_asana.models.business` with `ImportError` handling and
cross-registry validation. Gold-standard Lambda handler pattern.

### cache_invalidate.py — LOW RISK
Imports `cache.providers.tiered`, `cache.backends.redis`, `cache.dataframe.factory`.
None reach `models.business.__init__`. No entity type detection performed — only
clears Redis keys and S3 objects.

### insights_export.py — LOW RISK
Defers workflow import inside `_create_workflow()`. The `InsightsExportWorkflow` enumerates
Offers by hardcoded `OFFER_PROJECT_GID` string, not via `ProjectTypeRegistry` detection.

### conversation_audit.py — MEDIUM RISK
Handler imports `workflow_handler` → `WorkflowAction` (base only). At runtime,
`_create_workflow()` imports `ConversationAuditWorkflow`, which imports `ContactHolder`
from `models.business.contact` (NOT `models.business.__init__`). The workflow calls
`hydrate_from_gid_async` → `detect_entity_type_async` → Tier 1 detection.

**Safety net:** The `tier1.py:100-105` defensive guard ensures bootstrap runs before first
detection. But this is reactive, not proactive — inconsistent with `cache_warmer.py` pattern.

### checkpoint.py — N/A
Utility module, no Lambda handler, no registry use.

### workflow_handler.py — N/A
Generic handler factory. Not deployed as a Lambda handler directly.

### api/main.py — COVERED
Explicit side-effect import at line 35:
`import autom8_asana.models.business  # noqa: F401`

### entrypoint.py — N/A
Thin dispatch shim. ECS path → uvicorn → `api/main.py` (which has guard).

---

## Supporting Checks

### `tier1.py` Defensive Guard (lines 91-105)

```python
if not is_bootstrap_complete():
    logger.info("tier1_bootstrap_triggered", extra={"trigger": "detection_guard"})
    register_all_models()
```

Valid last-resort safety net. Should not be primary bootstrap mechanism.

### `core/system_context.py` — `reset_bootstrap()`

`SystemContext.reset_all()` calls `reset_bootstrap()` (sets `_BOOTSTRAP_COMPLETE = False`).
Intentional for test isolation. No production concern.

---

## Recommendations

### 1. Add bootstrap guard to `conversation_audit.py` (WARRANTED)

**File:** `src/autom8_asana/lambda_handlers/conversation_audit.py`

Add after existing imports:
```python
import autom8_asana.models.business  # noqa: F401 - bootstrap side effect
```

**Rationale:** Uses detection at runtime via `hydrate_from_gid_async`. Tier 1 defensive
guard saves it today, but explicit guard is more legible, consistent, and future-safe.

### 2. Do NOT add guards to other handlers

`cache_invalidate.py`, `insights_export.py`, `checkpoint.py`, `workflow_handler.py` —
none use the ProjectTypeRegistry. Adding bootstrap imports would be misleading.

### 3. Document tier1.py guard intent (OPTIONAL)

Add comment noting this is the last-resort guard, and handlers using detection should
have their own proactive guard.

---

## Summary

| Count | Status |
|---|---|
| 2 | COVERED (`cache_warmer.py`, `api/main.py`) |
| 1 | MEDIUM RISK — needs guard (`conversation_audit.py`) |
| 2 | LOW RISK — no guard needed (`cache_invalidate.py`, `insights_export.py`) |
| 3 | N/A — not entry points or no registry use |

**Single code change recommended:** Add bootstrap import to `conversation_audit.py`.
