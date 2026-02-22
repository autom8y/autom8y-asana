# v1 Query Endpoint Sunset Inventory

**Sunset date**: 2026-06-01
**Assessed**: 2026-02-18
**Related item**: XR-004

## Affected Endpoints

| Endpoint | Status | Router File |
|----------|--------|-------------|
| `POST /v1/query/{entity_type}` | DEPRECATED (v1 only) | `api/routes/query.py:112` |
| `POST /v1/query/{entity_type}/rows` | SHADOWED by v2 | `api/routes/query.py:239` (dead code after QW-6 fix) |

### v2 Replacements (active)

| Endpoint | Router File |
|----------|-------------|
| `POST /v1/query/{entity_type}/rows` | `api/routes/query_v2.py:61` |
| `POST /v1/query/{entity_type}/aggregate` | `api/routes/query_v2.py:126` |

## Consumer Inventory

### Route Definitions
- `src/autom8_asana/api/routes/query.py` — v1 router (prefix `/v1/query`)
- `src/autom8_asana/api/routes/query_v2.py` — v2 router (prefix `/v1/query`)
- `src/autom8_asana/api/routes/__init__.py:30-31` — exports both routers
- `src/autom8_asana/api/main.py:184-185` — registration (v2 first after QW-6 fix)

### Test Files
| File | Target | Test Cases |
|------|--------|------------|
| `tests/api/test_routes_query.py` | `POST /v1/query/{entity_type}` (legacy) | TC-001 through TC-014 |
| `tests/api/test_routes_query_rows.py` | `POST /v1/query/{entity_type}/rows` | TC-I001 through TC-I020 |
| `tests/api/test_routes_query_aggregate.py` | `POST /v1/query/{entity_type}/aggregate` | TC-RA001 through TC-RA012 |

### Client Examples & Scripts
- `docs/examples/06-query-entities.py` — httpx client example targeting `/v1/query/{entity_type}/rows`
- `scripts/demo_query_layer.py` — direct QueryEngine invocation (labels endpoint paths)

### Documentation
- `docs/api-reference/endpoints/query.md` — endpoint reference with curl examples
- `docs/api-reference/README.md` — API overview
- `docs/design/TDD-dynamic-query-service.md` — technical design
- `docs/design/TDD-aggregate-endpoint.md` — aggregate spec
- `docs/guides/entity-query.md` — user guide

### Request/Response Models
- `src/autom8_asana/query/models.py` — `RowsRequest`, `RowsResponse`, `AggregateRequest`, `AggregateResponse`

## External Consumers

**None found in this repository.** All `/v1/query` endpoints are S2S-only (service token JWT auth). External consumer discovery requires auditing calling services.

## Sunset Risks

1. **v1 `/{entity_type}` endpoint**: Only endpoint with no v2 equivalent. Callers using flat `where` equality filtering must migrate to `/rows` with predicate trees.
2. **Test coverage**: `test_routes_query.py` (14 TCs) and `test_routes_query_rows.py` (20 TCs) test v1 behavior. After sunset, these tests should be removed or migrated.
3. **Deprecation headers**: Already emitted (`Sunset: 2026-06-01`, `Link` to successor). Confirm calling services are parsing these.
4. **Dead code after QW-6**: v1's `query_rows` handler (`query.py:239-369`) is now unreachable since v2 is registered first. Candidate for removal.

## Recommended Actions

| Priority | Action | Effort |
|----------|--------|--------|
| P1 | Audit calling services for `/v1/query/{entity_type}` usage | Medium |
| P2 | Remove dead `query_rows` from `query.py` (shadowed by v2) | Low |
| P2 | Migrate `test_routes_query_rows.py` to test v2 handler directly | Medium |
| P3 | Add sunset countdown logging/alerting | Low |
| P3 | Plan v1 router removal for 2026-06-01 | Low |
