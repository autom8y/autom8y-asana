---
domain: feat/data-service-client
generated_at: "2026-04-01T17:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/clients/data/**/*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.82
format_version: "1.0"
---

# autom8_data Satellite Service Client (Ad Performance Insights)

## Purpose and Design Rationale

Cross-service HTTP client connecting `autom8_asana` to the `autom8_data` satellite service. Retrieves ad performance insights (campaigns, spend, leads, appointments, assets) keyed by `PhoneVerticalPair` (PVP): `(office_phone, vertical)`.

Primary consumer: `InsightsExportWorkflow` (12-table concurrent fetch per Offer). Secondary: GID push, conversation audit (CSV export), reconciliation executor.

## Conceptual Model

### PVP as Join Key

`(office_phone, vertical)` maps between Asana's entity model and autom8_data's analytics model. Canonical key format: `pv1:{phone}:{vertical}`.

### Factory as Query Dimension

14 named "factories" (account, ads, adsets, campaigns, spend, leads, appts, assets, targeting, payments, business_offers, ad_questions, ad_tests, base) mapped to `frame_type` via `FACTORY_TO_FRAME_TYPE`.

### Four Request Shapes

| Shape | Path | Use |
|-------|------|-----|
| Single PVP insights | POST `/api/v1/data-service/insights` | One business, one factory |
| Batch PVP insights | POST `/api/v1/data-service/insights` | Multiple businesses |
| Export CSV | GET `/api/v1/messages/export` | Conversation audit |
| Reconciliation | POST `/api/v1/insights/reconciliation/execute` | Payment matching |

### Resilience (Three Layers)

1. **Circuit breaker**: 5 failures to open, 30s recovery, 1 half-open probe
2. **Retry with backoff**: 2 retries, base 1.0s, retryable {429, 502, 503, 504}
3. **Stale cache fallback** (ADR-INS-004): When live request fails, return cached response with `is_stale=True`

### PII Contract (XR-003)

`mask_phone_number()` applied before all log emission. Pattern: `+17705753103 -> +1770***3103`.

## Implementation Map

17 files in `src/autom8_asana/clients/data/`: client.py (~550 lines), config.py, models.py, README.md, _cache.py, _metrics.py, _normalize.py, _pii.py, _policy.py (DefaultEndpointPolicy), _response.py, _retry.py, plus _endpoints/ (insights.py, batch.py, export.py, reconciliation.py, simple.py).

### Key Methods

`get_insights_async()`, `get_insights_batch_async()` (chunked to 500), `get_export_csv_async()`, `get_reconciliation_async()`, `get_appointments_async()`, `get_leads_async()`, `is_healthy()`.

### Auth

`ServiceTokenAuthProvider` wired in `api/dependencies.py` (SCAR-012 fix).

## Boundaries and Failure Modes

- **SCAR-012**: Client without auth_provider -- all joins returned zero. Fix: explicit ServiceTokenAuthProvider.
- **SCAR-028**: PII leakage in error logs. Fix: mask_pii_in_string().
- **Env Var Naming**: Must use `AUTOM8Y_` prefix (missing "Y" caused silent failure).
- **OpenAPI contract discrepancy**: Contract uses `/api/v1/factory/{name}`; implementation uses `/api/v1/data-service/insights`.

## Knowledge Gaps

1. `_policy.py` (DefaultEndpointPolicy) internals not read.
2. `_response.py` error mapping not verified.
3. `_cache.py` key format and TTL not read.
4. Batch chunking across partial failures not verified.
