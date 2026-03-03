# COMP-5: include_unused Consumer Migration

```yaml
status: IMPLEMENTED
verdict: MIGRATE — data-service is authoritative
date: 2026-02-27
session: session-20260227-175851-a3aa2c27
```

---

## Decision

The data-service `include_unused=true` definition supersedes the client-side approximation.
The 3 behavioral differences are improvements, not regressions:

| Difference | Old (client-side) | New (data-service) | Why new is better |
|-----------|-------------------|-------------------|-------------------|
| Activity column | `imp` (impressions) | `leads` | Leads is the business-relevant metric; impressions is a proxy |
| Disabled/generic | Excluded client-side | Included by server | Server owns asset classification; consumer should not second-guess |
| Category B assets | Missing entirely | Enriched from inventory | Inventory-only assets are genuinely unused — hiding them was a gap |

## Implementation

Replaced client-side 4-condition filter (`insights_export.py:817-848`) with a dedicated
API call using `factory="assets", period="t30", include_unused=True`. UNUSED ASSETS is
now the 12th independent concurrent fetch in `_fetch_all_tables()`, decoupled from
ASSET TABLE success/failure.

### Files changed
- `src/autom8_asana/clients/data/models.py` — added `include_unused: bool` to InsightsRequest
- `src/autom8_asana/clients/data/_endpoints/insights.py` — wire `include_unused` into request body
- `src/autom8_asana/clients/data/client.py` — added `include_unused` param to `get_insights_async()`
- `src/autom8_asana/automation/workflows/insights_export.py` — replaced derivation with API call
- `src/autom8_asana/automation/workflows/insights_formatter.py` — updated subtitle

### Dead code removed
- Client-side filter: `spend==0 AND imp==0 AND NOT disabled AND NOT is_generic` (35 lines)
- ASSET TABLE failure inheritance logic for UNUSED ASSETS (17 lines)
- `missing_dependency` fallback branch (7 lines)
