# Insights Export -- Smoke Test Playbook

**Date**: 2026-02-20
**Target offer**: `1211872268838349`
**Context**: `INSIGHTS_EXPORT-CANONICAL-2026-02-20.md`

---

## Pre-conditions

### 1. Environment Variables

Source credentials in order (each file may override earlier values):

```bash
cd /Users/tomtenuta/Code/autom8y-asana
source .env/shared
source .env/production
```

Required variables after sourcing:

| Variable | Source | Purpose |
|----------|--------|---------|
| `ASANA_PAT` | `.env/production` | Asana Personal Access Token |
| `ASANA_SERVICE_KEY` | `.env/production` | Key for auth token exchange |
| `AUTOM8_DATA_URL` | `.env/shared` or hardcode | `https://data.api.autom8y.io` |

### 2. Auth Token Exchange

The Lambda handler uses `AUTOM8_DATA_API_KEY` as a Bearer token to call autom8y-data. Exchange the service key for an access token:

```bash
export AUTH_URL="https://auth.api.autom8y.io"

# Exchange service key for access token
ACCESS_TOKEN=$(curl -s -X POST "${AUTH_URL}/internal/service-token" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${ASANA_SERVICE_KEY}" \
  -d '{"service_name": "autom8y-asana"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

export AUTOM8_DATA_API_KEY="${ACCESS_TOKEN}"
```

Verify the token is set:
```bash
echo "Token length: ${#AUTOM8_DATA_API_KEY}"
# Expected: non-zero (typically 100+ chars)
```

### 3. Feature Flag

Ensure the export is enabled (it defaults to enabled, but check):

```bash
export AUTOM8_EXPORT_ENABLED=true
```

### 4. Verify Connectivity

Quick health check against autom8y-data:

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${AUTOM8_DATA_API_KEY}" \
  "${AUTOM8_DATA_URL}/health"
# Expected: 200
```

---

## Trigger the Lambda Handler

### Option A: Python Script (Recommended)

Create a temporary smoke test script. The handler calls `asyncio.run()` internally -- do NOT wrap in asyncio.run.

```python
#!/usr/bin/env python3
"""Smoke test: invoke insights export handler for a single offer."""
import json
import sys
import os

# Ensure the source tree is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from autom8_asana.lambda_handlers.insights_export import handler

event = {
    "entity_ids": ["1211872268838349"],
    "dry_run": True,  # Set False to actually upload to Asana
}

print(f"Invoking handler with event: {json.dumps(event, indent=2)}")
result = handler(event, None)

print(f"\nStatus code: {result['statusCode']}")
body = json.loads(result["body"])
print(f"Response body:\n{json.dumps(body, indent=2)}")

# Extract report preview if dry_run
if body.get("metadata", {}).get("report_preview"):
    for offer_gid, preview_html in body["metadata"]["report_preview"].items():
        filename = f"smoke_test_{offer_gid}.html"
        with open(filename, "w") as f:
            f.write(preview_html)
        print(f"\nWrote HTML preview to: {filename}")
```

Run it:
```bash
cd /Users/tomtenuta/Code/autom8y-asana
python3 smoke_test_runner.py
```

### Option B: Python One-liner

```bash
cd /Users/tomtenuta/Code/autom8y-asana
python3 -c "
import json, sys, os
sys.path.insert(0, 'src')
from autom8_asana.lambda_handlers.insights_export import handler
result = handler({'entity_ids': ['1211872268838349'], 'dry_run': True}, None)
body = json.loads(result['body'])
print(json.dumps(body, indent=2))
if body.get('metadata', {}).get('report_preview'):
    for gid, html in body['metadata']['report_preview'].items():
        with open(f'smoke_{gid}.html', 'w') as f: f.write(html)
        print(f'Wrote smoke_{gid}.html')
"
```

### dry_run Behavior

- `dry_run: True` -- fetches all data, composes HTML, stores preview in `metadata.report_preview`, but does NOT upload to Asana or delete old attachments. Use this for validation.
- `dry_run: False` -- full pipeline: upload HTML attachment to Asana, delete old attachments.

---

## Response Validation

### Step 1: Top-Level Response Shape

```
statusCode: 200
body.status: "completed"
body.total: 1
body.succeeded: 1
body.failed: 0
body.total_tables_succeeded: >= 10  (12 ideal, 10 minimum if recon pending)
body.total_tables_failed: <= 2
```

If `statusCode` is not 200, check:
- 500 with `error_type: "CircuitBreakerOpenError"` -- autom8y-data is down
- 200 with `status: "skipped"` -- feature flag disabled or validation failed
- Check `body.errors` for per-offer error details

### Step 2: HTML File Inspection

Open the HTML file in a browser. Verify each section exists and renders correctly.

---

## Per-Table Assertions

### Table 1: SUMMARY

| Check | Expected |
|-------|----------|
| Section exists | `<section id="summary">` present |
| Row count | Exactly 1 row |
| Badge | `<span class="badge">1</span>` |
| Key columns present | `leads`, `appts`, `spend`, `cpl`, `cps` |
| Currency format | `spend` displays as `$X,XXX.XX` |
| Rate format | `conversion_rate` displays as `X.XX%` |
| Not 97 rows | Verify badge shows 1, NOT 97 (H-03 regression check) |

### Table 2: APPOINTMENTS

| Check | Expected |
|-------|----------|
| Section exists | `<section id="appointments">` present |
| Row count | Up to 250 rows (post WS-B) |
| Truncation note | If >250 rows: "Showing 250 of N rows" |
| Time range | Data from last 90 days |

### Table 3: LEADS

| Check | Expected |
|-------|----------|
| Section exists | `<section id="leads">` present |
| Row count | Up to 250 rows (post WS-B) |
| Truncation note | If >250 rows: "Showing 250 of N rows" |
| Time range | Data from last 30 days |

### Table 4: LIFETIME RECONCILIATIONS

| Check | Expected |
|-------|----------|
| Section exists | `<section id="lifetime-reconciliations">` present |
| If payment data available | Normal table with `collected`, `spend`, `variance` columns |
| If payment data pending | Info message: "Payment reconciliation data is pending..." (post WS-A) |
| Column order | `office_phone`, `vertical`, `num_invoices`, `collected`, `spend`, `variance`, `variance_pct` leading (per COLUMN_ORDER) |

### Table 5: T14 RECONCILIATIONS

| Check | Expected |
|-------|----------|
| Section exists | `<section id="t14-reconciliations">` present |
| If payment data available | Normal table with windowed periods |
| If payment data pending | Info message (same as table 4) |
| Column order | `period`, `period_label`, `period_start`, `period_end`, `period_len` leading |

### Table 6: BY QUARTER

| Check | Expected |
|-------|----------|
| Section exists | `<section id="by-quarter">` present |
| Row count | Multiple rows (one per quarter with data) |
| Column order | `period_label`, `period_start`, `period_end` leading (leftmost columns) |
| Period labels | P0 = most recent quarter |
| Metrics present | `leads`, `appts`, `spend`, etc. |

### Table 7: BY MONTH

| Check | Expected |
|-------|----------|
| Section exists | `<section id="by-month">` present |
| Column order | `period_label`, `period_start`, `period_end` leading |
| Period labels | P0 = most recent month |

### Table 8: BY WEEK

| Check | Expected |
|-------|----------|
| Section exists | `<section id="by-week">` present |
| Column order | `period_label`, `period_start`, `period_end` leading |
| Period labels | P0 = most recent week |

### Table 9: AD QUESTIONS

| Check | Expected |
|-------|----------|
| Section exists | `<section id="ad-questions">` present |
| Question-level columns | `question_key` and `priority` columns present (NOT offer-level columns) |
| Frame type verification | If you see `offer_id` as a column, H-02 has regressed |
| Metric: n_distinct_ads | Column header should be override label (post WS-C) or "N Distinct Ads" |

### Table 10: ASSET TABLE

| Check | Expected |
|-------|----------|
| Section exists | `<section id="asset-table">` present |
| Row count | Up to 150 rows (post WS-D), sorted by spend desc |
| Truncation note | If >150 source rows: "Showing 150 of N rows" |
| Transcript column | Long text clipped with CSS overflow (post WS-D) |
| Columns | `asset_id`, `spend`, `imp`, `ctr`, etc. |

### Table 11: OFFER TABLE

| Check | Expected |
|-------|----------|
| Section exists | `<section id="offer-table">` present |
| Columns | `offer_id`, `offer_cost`, etc. |
| Currency format | `offer_cost` displays as `$X,XXX.XX` |

### Table 12: UNUSED ASSETS

| Check | Expected |
|-------|----------|
| Section exists | `<section id="unused-assets">` present |
| Filter criteria | All rows have `spend == 0` AND `imp == 0` |
| Exclusions | No rows with `disabled == True` or `is_generic == True` |
| Empty case | If no unused assets: "No unused assets found" message |

---

## Cross-Cutting Checks

### Formatting

| Check | How to verify |
|-------|--------------|
| Currency fields | Search HTML for `$` -- all should match `$X,XXX.XX` pattern |
| Rate fields | Search HTML for `%` -- rates should be `X.XX%` (not `0.0342`) |
| None values | Search for dash indicator -- should be styled, not literal "None" |
| Integer formatting | Large integers should have commas: `45,000` not `45000` |

### HTML Structure

| Check | How to verify |
|-------|--------------|
| Self-contained | No `<link>` or `<script src>` tags (all CSS inlined) |
| XSS safety | No unescaped `<` or `>` in data cells |
| Section count | Exactly 12 `<section>` elements |
| Footer present | Duration, Tables count (e.g., "10/12"), Version string |

### Header

| Check | Expected |
|-------|----------|
| Phone | Masked format: `***-***-XXXX` (last 4 visible) |
| Vertical | Business vertical string |
| Generated | ISO timestamp |
| Title | "Insights Export: {Business Name}" |

---

## Upload to Asana (Full Run)

After validating with `dry_run: True`, run again with `dry_run: False`:

```python
event = {
    "entity_ids": ["1211872268838349"],
    "dry_run": False,
}
result = handler(event, None)
```

### Post-Upload Verification

1. Open Asana task `1211872268838349` in browser: `https://app.asana.com/0/0/1211872268838349`
2. Verify new attachment named `insights_export_YYYYMMDD_HHMMSS.html`
3. Download and open the attachment -- should match dry_run preview
4. Verify old `insights_export_*.html` and `insights_export_*.md` attachments were deleted

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `statusCode: 500` | Auth token expired or missing | Re-run token exchange (Step 2 of Pre-conditions) |
| `status: "skipped"` | `AUTOM8_EXPORT_ENABLED=false` | `export AUTOM8_EXPORT_ENABLED=true` |
| SUMMARY shows 97 rows | `_PERIOD_NOT_SET` sentinel regression | Check autom8y-data `insight_executor.py:22` |
| AD QUESTIONS shows offer columns | H-02 frame_type regression | Check `FACTORY_TO_FRAME_TYPE["ad_questions"]` == `"question"` |
| All recon columns null | Expected (Stripe REC-8 not shipped) | WS-A should add pending indicator |
| `CircuitBreakerOpenError` | autom8y-data degraded | Wait and retry, or check data service health |
| Timeout on ASSET TABLE | Large dataset, 30s read timeout | Expected for high-asset accounts; check if data returns within 30s |
| `InsightsNotFoundError` for a table | No data for this phone/vertical combo | Expected for new accounts; table renders as empty section |

---

## Quick Validation Script

After the full run, this script validates the HTML output programmatically:

```python
#!/usr/bin/env python3
"""Validate smoke test HTML output."""
import re
import sys

html_file = sys.argv[1] if len(sys.argv) > 1 else "smoke_1211872268838349.html"

with open(html_file) as f:
    html = f.read()

# Section IDs to check
expected_sections = [
    "summary", "appointments", "leads",
    "lifetime-reconciliations", "t14-reconciliations",
    "by-quarter", "by-month", "by-week",
    "ad-questions", "asset-table", "offer-table", "unused-assets",
]

print(f"Validating: {html_file}")
print(f"HTML length: {len(html):,} chars\n")

ok = True
for section_id in expected_sections:
    found = f'id="{section_id}"' in html
    status = "PASS" if found else "FAIL"
    if not found:
        ok = False
    print(f"  [{status}] Section: {section_id}")

# Check SUMMARY row count
summary_match = re.search(r'id="summary".*?<span class="badge">(\d+)</span>', html, re.DOTALL)
if summary_match:
    count = int(summary_match.group(1))
    status = "PASS" if count == 1 else f"FAIL (got {count})"
    if count != 1:
        ok = False
    print(f"  [{status}] SUMMARY row count: {count}")

# Check for unescaped None
none_count = html.count(">None<")
status = "PASS" if none_count == 0 else f"FAIL ({none_count} occurrences)"
if none_count > 0:
    ok = False
print(f"  [{status}] No raw 'None' values in cells")

# Check for external resources
has_link = "<link " in html and 'rel="stylesheet"' in html
has_script_src = re.search(r'<script\s+src=', html)
status = "PASS" if not has_link and not has_script_src else "FAIL"
if has_link or has_script_src:
    ok = False
print(f"  [{status}] Self-contained (no external CSS/JS)")

# Check footer
has_footer = "report-footer" in html
status = "PASS" if has_footer else "FAIL"
if not has_footer:
    ok = False
print(f"  [{status}] Footer present")

# Currency format spot check
currency_pattern = re.search(r'\$[\d,]+\.\d{2}', html)
status = "PASS" if currency_pattern else "WARN (no currency values found)"
print(f"  [{status}] Currency formatting ($X,XXX.XX)")

# Rate format spot check
rate_pattern = re.search(r'[\d.]+%', html)
status = "PASS" if rate_pattern else "WARN (no rate values found)"
print(f"  [{status}] Rate formatting (X.XX%)")

print(f"\n{'ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'}")
sys.exit(0 if ok else 1)
```

Usage:
```bash
python3 validate_smoke.py smoke_1211872268838349.html
```
