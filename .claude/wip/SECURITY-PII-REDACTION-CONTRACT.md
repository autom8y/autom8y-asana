# PII Redaction Contract: DataServiceClient

**Sprint**: XR-003 | **Scope**: `src/autom8_asana/clients/data/`

## 1. What Constitutes PII

| PII Type | Format | Example |
|----------|--------|---------|
| E.164 phone number | `+{country}{digits}` (10-15 digits) | `+17705753103` |
| Canonical key | `pv1:{phone}:{vertical}` | `pv1:+17705753103:chiropractic` |
| Cache key (insights) | `insights:{factory}:{canonical_key}` | `insights:account:pv1:+17705753103:chiropractic` |
| Cache key (simple) | `{endpoint}:{phone}` | `appointments:+17705753103` |

Phone numbers are the **only** PII type handled by this module. Verticals, factory names, request IDs, and metric tags are not PII.

## 2. PII Pipeline: Entry and Redaction Points

### Entry Points (raw PII enters the system)

| Entry Point | Parameter | Consumers |
|-------------|-----------|-----------|
| `get_insights_async(office_phone=...)` | Raw E.164 | insights endpoint, cache key |
| `get_insights_batch_async(pairs=[...])` | PVP list with raw phones | batch endpoint |
| `get_export_csv_async(office_phone=...)` | Raw E.164 | export endpoint, retry callbacks |
| `get_appointments_async(office_phone=...)` | Raw E.164 | simple endpoint, cache key |
| `get_leads_async(office_phone=...)` | Raw E.164 | simple endpoint, cache key |

### Redaction Boundary

**Rule**: PII must be redacted before crossing any of these boundaries:

1. **Log messages** — all log calls (debug, info, warning, error) must use masked values
2. **Log extras/structured fields** — `extra={}` dicts must contain masked values
3. **Exception attributes** — exception objects stored on classes (e.g., `ExportError.office_phone`) must be masked
4. **Error strings propagated to callers** — `str(exception)` in error results must be sanitized
5. **Metric tags** — metric tag values must never contain phone numbers or canonical keys

PII **may** remain raw in:
- HTTP request parameters (required for API calls)
- Cache keys used for lookup (required for cache hit)
- Function-local variables that never cross a boundary

## 3. Redaction Functions

### `mask_phone_number(phone: str) -> str`
- **Location**: `client.py:73`
- **Input**: E.164 phone string (e.g., `+17705753103`)
- **Output**: `+1770***3103` (first 5 chars + `***` + last 4 chars)
- **Edge cases**: Returns input unchanged if `len(phone) < 9` or not `+`-prefixed

### `_mask_canonical_key(canonical_key: str) -> str`
- **Location**: `client.py:105`
- **Input**: `pv1:+17705753103:chiropractic`
- **Output**: `pv1:+1770***3103:chiropractic`
- **Edge cases**: Returns input unchanged if not `pv1:` prefixed or fewer than 3 colon-parts

### `_mask_pii_in_string(s: str) -> str`
- **Location**: `client.py` (added by XR-003)
- **Input**: Any string that may contain E.164 phone numbers
- **Output**: Same string with all phone number matches replaced via `mask_phone_number`
- **Use case**: Cache keys, error messages, and any freeform string that might contain PII

## 4. Leakage Vectors Fixed (XR-003)

| # | File | Issue | Fix |
|---|------|-------|-----|
| 1 | `_cache.py` | Cache keys logged at DEBUG/INFO with raw phone | Mask cache_key in all log messages and extras |
| 2 | `_retry.py` via `export.py` | `error_kwargs={"office_phone": raw}` merged into log extras | Pass masked phone in error_kwargs |
| 3 | `export.py` | `ExportError.office_phone` stores raw phone | Use masked phone in all ExportError constructions |
| 4 | `simple.py` | Cache keys `f"appointments:{raw_phone}"` | Mask phone in cache key before passing to error handler |
| 5 | `batch.py` / `client.py` | `str(e)` in error results may echo phone | Sanitize error strings via `_mask_pii_in_string` |

## 5. Invariants for Future Development

1. **No raw phone in logs**: Any new log call in `clients/data/` that includes a phone number or canonical key MUST use `mask_phone_number`, `_mask_canonical_key`, or `_mask_pii_in_string`.

2. **No raw phone in exceptions**: Exception attributes that store phone numbers MUST contain masked values. This prevents PII leakage through Sentry, Datadog, or any error serialization.

3. **No raw phone in error results**: When converting exceptions to error strings (e.g., `str(e)` for `BatchInsightsResult.error`), sanitize with `_mask_pii_in_string`.

4. **Cache keys are internal-only**: Cache keys may contain raw phone for lookup correctness, but MUST be masked before logging or including in error messages.

5. **Metric tags are phone-free**: Metric tags use factory names, error types, and status codes — never phone numbers or canonical keys.

6. **Regex pattern is canonical**: Use `_PHONE_PATTERN` (`\+\d{10,15}`) for phone detection. Do not create alternative patterns.
