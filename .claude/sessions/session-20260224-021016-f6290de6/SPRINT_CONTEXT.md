---
sprint_id: P2-01
session_id: session-20260224-021016-f6290de6
status: ACTIVE
created_at: "2026-02-24T02:10:16Z"
started_at: "2026-02-24T02:10:16Z"
name: "Utility Extraction + EntityRegistry Fix"
goal: "Extract string utilities to core/string_utils.py, fix EntityRegistry self-registration, update all import sites"
effort_estimate: "2 hours"
---

# Sprint P2-01: Utility Extraction + EntityRegistry Fix

## Goal

Extract string utilities to `core/string_utils.py`, fix EntityRegistry to self-register via `register_holder()` at module level, and update all downstream import sites.

## Scope

| File | Action |
|------|--------|
| `core/string_utils.py` | CREATE — home for `slugify`, `normalize_name`, and related string helpers |
| `core/registry.py` | UPDATE — accept EntityRegistry self-registration |
| `core/entity_registry.py` | UPDATE — add `register_holder(key, cls)` call at module bottom |
| `services/resolver.py` | UPDATE — import from `core/string_utils` |
| `persistence/holder_construction.py` | UPDATE — import from `core/string_utils` |
| `cache/` import sites | UPDATE — repoint string util imports |
| `core/` import sites | UPDATE — repoint string util imports |
| `dataframes/` import sites | UPDATE — repoint string util imports |
| `models/business/` import sites | UPDATE — repoint string util imports |

## Done Gate

All 3 grep gates must pass AND full suite must be green:

```bash
# Gate 1: No stray string util imports outside canonical module
grep -r "slugify\|normalize_name" cache/ core/ dataframes/ models/business/
# Expected: zero hits outside core/string_utils.py

# Gate 2: EntityRegistry self-registers at module level
grep -r "register_holder" core/entity_registry.py
# Expected: at least one hit

# Gate 3: Full suite green
pytest tests/ -x -q
# Expected: exit 0
```

## Tasks

- [ ] Audit current `slugify`/`normalize_name` usage across codebase (identify all import sites)
- [ ] Create `core/string_utils.py` with extracted utilities
- [ ] Update `core/entity_registry.py` to call `register_holder()` at module level
- [ ] Update `core/registry.py` if needed to accommodate self-registration
- [ ] Update `services/resolver.py` imports
- [ ] Update `persistence/holder_construction.py` imports
- [ ] Update all import sites in `cache/`, `core/`, `dataframes/`, `models/business/`
- [ ] Run grep gates (all 3 must pass)
- [ ] Run full suite (`pytest tests/ -x -q`)

## Seed Reference

`.claude/wip/REM-ASANA-ARCH/WS-P2-01.md`

## Notes

Phase 0 gap analysis complete. Design artifacts skipped — seed doc is the plan.
Implementation begins directly.
