---
domain: scar-tissue
generated_at: "2026-04-28T21:55:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "8c58f930"
confidence: 0.93
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/scar-tissue.md"
land_hash: "a15a024ce204de3301b612526c5b1b59e4841fa3d3d70f2226e1b430cd73da1e"
---

# Codebase Scar Tissue

## Failure Catalog

35+ distinct failures documented from two evidence sources (git commit history + code marker scan). The following SCAR identifiers are confirmed present in the live codebase at source_hash `8c58f930`: SCAR-005 (20+ refs), SCAR-REG-001 (9 refs), SCAR-IDEM-001 (7 refs), SCAR-015 (5 refs), SCAR-020 (2 refs), SCAR-006 (1 ref). DEF identifiers active: DEF-005 (5 refs), DEF-001 (3 refs), DEF-02 (1 ref).

### Full Scar Catalog

| SCAR ID | Failure Description | Category | Commit / Fix |
|---------|---------------------|----------|--------------|
| SCAR-001 | Entity/holder class missing `PRIMARY_PROJECT_GID` — silent resolution collision | Entity Resolution | Historical |
| SCAR-002 | Section persistence race: `in_progress_since` timeout not enforced | Concurrency | Historical |
| SCAR-003 | Stale S3 cache served after data change — cache coherence gap | Cache Coherence | Historical |
| SCAR-004 | DEF-005 origin: warm-up and request path used separate CacheProvider instances — cache split | Cache Coherence | `af10d98e` |
| SCAR-005 | CascadingFieldResolver 30% null rate on units — cascade warm-up ordering violated | Cache Coherence | Multiple cascade fix commits |
| SCAR-006 | Cascade hierarchy warming gaps — parent GID not stored | Cache Coherence | `088fe332`, `4d652720` |
| SCAR-007 | S3 build_result schema version drift — stale parquet deserialization failures | Cache Coherence | Historical |
| SCAR-008 | DEF-001 origin: `SaveSession` cleared snapshot before accessor reset — stale custom field state | Data Model | `session.py:995` |
| SCAR-009 | Tests missing `ASANA_WORKSPACE_GID` — sync auto-detect triggered in wrong context | Startup | Historical |
| SCAR-010 | Session state mutation race | Concurrency | Historical |
| SCAR-010b | `_require_open()` contract bypassed | Concurrency | Historical |
| SCAR-011 | ECS health check targeting `/health/ready` — service cycles on startup delays | Startup | Historical |
| SCAR-011b | New startup dependency gated on `/health` (wrong endpoint) | Startup | Historical |
| SCAR-012 | Cross-service client using PAT instead of `client_credentials` grant | Authentication | Historical |
| SCAR-013 | Optional SDK imported without `try/except ImportError` | Startup | Historical |
| SCAR-014 | Lifecycle config models using `extra="forbid"` — broke forward-compat | Data Model | `fe6bc978` |
| SCAR-015 | Timeline endpoint 504 at ~3,800 offers — per-request Asana I/O exceeded ALB 60s | Performance | `b85a604a` |
| SCAR-016/017/018/019 | Workflow logic gaps | Workflow Logic | Historical |
| SCAR-020 | `PhoneNormalizer` wired only into matching engine, not read path — reconciliation blindness | Workflow Logic | `09163c06` |
| SCAR-021 | CI integration failure | Integration / CI | Historical |
| SCAR-022 | `uv sync --frozen` incompatible with `--no-sources` in uv >=0.15.4 — Dockerfile failure | Startup | `2229f4a3` |
| SCAR-023 | Offer `office` column `source=None` bypassing cascade pipeline — 30-40% null rate | Data Model | `09163c06` |
| SCAR-024 | Phone field contract gap (related to SCAR-020) | Data Model | Historical |
| SCAR-025 | Data model contract gap | Data Model | Historical |
| SCAR-026 | Test mocks for SDK clients missing `spec=` — silent mock drift | Integration / CI | Historical |
| SCAR-027 | User-controlled string passed to `re.sub` replacement — ReDoS / injection | Security | `core/creation.py:82-97` |
| SCAR-028 | Error log emitted user PII without masking | Security | `clients/data/_pii.py:61` |
| SCAR-029 | GID not stripped before Pydantic normalization — leading/trailing whitespace failed validation | Security | `api/routes/webhooks.py:375-381` |
| SCAR-030 | Section names from non-live source — ALL CAPS invariant not enforced | Data Model | Historical |
| SCAR-S3-LOOP | Permanent S3 error codes fed to circuit-breaker retry loop — infinite retry storm | Cache Coherence | `core/retry.py:198` |
| SCAR-IDEM-001 | Idempotency `finalize()` exception silently swallowed — double-execution risk on retry | Data Model | `api/middleware/idempotency.py:719` |
| SCAR-REG-001 | Section registry GIDs are sequential placeholders — unverified against live Asana API | Startup | `reconciliation/section_registry.py:94,128` |
| SCAR-WS8 | PAT route trees not consistently listed in `jwt_auth_config.exclude_paths` — JWT middleware rejects PAT requests | Security | `api/main.py:389` |
| Env Var Naming | `AUTOM8_DATA_API_KEY` typo (missing Y) — production API auth failures | Authentication | `clients/data/config.py:231` |

### New Candidates Not Yet Assigned SCAR IDs

- **SCAR-CANDIDATE-B**: `PhoneNormalizer.normalize()` previously lacked `NumberParseException` in its except tuple. Fix: `models/business/matching/normalizers.py:77-82`, commit `0f18f4e8`.
- **SCAR-CANDIDATE-C**: `list_workflows` handler missing `response_model`. Fix: `api/routes/workflows.py`, commit `bb97a744`.
- **Metrics CLI Under-count** (session-20260427): `autom8-query` CLI silently under-counts active sections (~6 in parquet vs ~22 expected). Root cause unresolved — 4 open questions: bucket mapping, freshness SLA, section-coverage gap, staleness-surface decision. Location: `metrics/compute.py`, `dataframes/offline.py`.

## Category Coverage

10 distinct failure categories applied across all 35+ scars:

| Category | Scars | Count |
|---|---|---|
| Cache Coherence / Stale Data | SCAR-003, 004, 005, 006, 007, S3-LOOP | 6 |
| Data Model / Contract Violation | SCAR-008, 014, 023, 024, 025, 030, IDEM-001, REG-001, CANDIDATE-B, CANDIDATE-C | 10 |
| Startup / Deployment Failure | SCAR-009, 011, 011b, 013, 022 | 5 |
| Workflow Logic Gap | SCAR-016, 017, 018, 019, 020 | 5 |
| Security / Input Validation | SCAR-027, 028, 029, WS8 | 4 |
| Concurrency / Race Condition | SCAR-002, 010, 010b | 3 |
| Authentication / Authorization | SCAR-012, Env Var Naming | 2 |
| Integration Failure / CI | SCAR-021, 026 | 2 |
| Performance Cliff / Timeout | SCAR-015 | 1 |
| Observability Gap | Metrics CLI Under-count | 1 |

Three categories explicitly searched and returned no results: schema migration failures, distributed coordination failures, network partition handling. SCAR-WS8 moved from Integration to Security (more precise classification).

## Fix-Location Mapping

All major scars have file:line or function-level locations. 21 primary fix paths verified present at source_hash `8c58f930`:

| Scar | Primary Fix Path | Verified |
|---|---|---|
| SCAR-005/006 | `dataframes/builders/progressive.py:161,466` | Yes |
| SCAR-005/006 | `dataframes/cascade_utils.py:27,289` | Yes |
| SCAR-005/006 (cascade contract) | `dataframes/schemas/offer.py:22` (`source="cascade:Office Phone"`) | Yes |
| SCAR-005/006 (cascade validator) | `dataframes/builders/cascade_validator.py:30-32` | Yes |
| SCAR-005/006 (post-build) | `dataframes/builders/post_build_validation.py:90-105` | Yes |
| SCAR-005/006 (WarmupOrderingError) | `dataframes/cascade_utils.py:22-30` | Yes |
| SCAR-005/006 (WarmupOrderingError re-raise) | `api/preload/progressive.py:696-699` | Yes |
| SCAR-008 / DEF-001 | `persistence/session.py:995-1001` | Yes |
| SCAR-015 | `services/section_timeline_service.py` (pre-computed timelines) | Yes |
| SCAR-020 / SCAR-023 (PhoneTextField) | `models/business/descriptors.py:472-498` | Yes |
| SCAR-020 / SCAR-023 (PhoneTextField applied) | `models/business/business.py:267` | Yes |
| SCAR-022 / DEF-009 | `Dockerfile` (`--no-sources` flag, commit `2229f4a3`) | Yes |
| SCAR-IDEM-001 | `api/middleware/idempotency.py:719` | Yes |
| SCAR-REG-001 | `reconciliation/section_registry.py:94,128` | Yes |
| SCAR-WS8 / DEF-08 | `api/main.py:389` (`/api/v1/exports/*` in exclude_paths) | Yes |
| SCAR-S3-LOOP | `core/retry.py:198` (`_PERMANENT_S3_ERROR_CODES`) | Yes |
| DEF-001 (resolver route) | `api/routes/resolver.py:335` | Yes |
| DEF-005 (shared CacheProvider) | `api/lifespan.py:108,126` | Yes |
| DEF-005 (client pool) | `api/client_pool.py:201` | Yes |
| Env Var Naming | `clients/data/config.py:231` (`AUTOM8Y_DATA_API_KEY`) | Yes |
| PKG-002 (env collision) | `tests/synthetic/conftest.py:78-80` | Yes |

## Defensive Pattern Documentation

### Cascade Defense-in-Depth (SCAR-005/006/023) — Four Layers

1. **Schema enforcement**: `source="cascade:..."` required on cascade columns. `source=None` silently bypasses pipeline (SCAR-023 root cause). Live: `dataframes/schemas/offer.py:22` (post-fix).
2. **Warm-up ordering guard**: `WarmupOrderingError` at `dataframes/cascade_utils.py:22-30`. BROAD-CATCH immune. Re-raised at `api/preload/progressive.py:696-699`.
3. **Post-build null rate audit**: `CASCADE_NULL_WARN_THRESHOLD = 0.05` (5%), `CASCADE_NULL_ERROR_THRESHOLD = 0.20` (20%) at `dataframes/builders/cascade_validator.py:31-32`. Calibrated against SCAR-005's 30% incident.
4. **Chain traversal gap-skipping**: `dataframes/views/cascade_view.py` (parent chain resolution with null-safe gaps).

**Regression tests**: `tests/unit/dataframes/test_cascade_ordering_assertion.py:71-106`, `test_warmup_ordering_guard.py`, `tests/unit/dataframes/builders/test_cascade_validator.py:649-668` (SCAR-005 30% scenario).

### Session Thread Safety (SCAR-010/010b)

`threading.RLock()` on all state mutations; `_require_open()` context manager at `persistence/session.py`. Regression: `tests/unit/persistence/test_session_concurrency.py` (19+ tests).

### Session Snapshot Ordering (SCAR-008 / DEF-001)

Order-critical fix at `persistence/session.py:995-1001`: accessor state (`_reset_custom_field_tracking`) cleared BEFORE `mark_clean()` captures snapshot. Reversal re-introduces stale state.

### Health Check Separation (SCAR-011/011b)

`/health` always returns 200 (liveness). `/health/ready` gates on `_cache_ready AND _workflow_configs_registered` (readiness). Regression: `tests/unit/api/test_lifespan_workflow_import.py`.

### Security Hardening (SCAR-027/028/029)

- Lambda replacement guard in `re.sub` at `core/creation.py:82-97`
- `mask_pii_in_string()` at `clients/data/_pii.py:61`
- GID `str.strip()` guard at `api/routes/webhooks.py:375-381`

### Phone Normalization on Read Path (SCAR-020 / SCAR-CANDIDATE-B)

`PhoneTextField` descriptor at `models/business/descriptors.py:472-498` normalizes `office_phone`, `twilio_phone_num` to E.164 on read. Applied at `models/business/business.py:267`. `PhoneNormalizer` now includes `NumberParseException` in except tuple. Regression: `tests/unit/models/business/matching/test_normalizers.py:64-70` (SCAR-020 guard).

### Idempotency Finalize Observability (SCAR-IDEM-001)

Exception on `finalize()` promoted to `logger.exception` with `impact` field at `api/middleware/idempotency.py:719-728`. **Known gap**: observability-only fix; double-execution risk for S2S strict-once callers remains open per `ADR-omniscience-idempotency Section 3.7`. Regression: `tests/unit/api/middleware/test_idempotency_finalize_scar.py` (SCAR-IDEM-001-A, -B, -C).

### JWT Exclude-Paths Sync (SCAR-WS8 / DEF-08)

`/api/v1/exports/*` added to `jwt_auth_config.exclude_paths` at `api/main.py:389`. Structural invariant: every PAT-tagged router registration must have a corresponding `exclude_paths` entry. Regression: `tests/unit/api/test_exports_auth_exclusion.py` (live middleware introspection, no mocking).

### S3 Circuit Breaker (SCAR-S3-LOOP)

`_PERMANENT_S3_ERROR_CODES: frozenset[str]` at `core/retry.py:198` — permanent codes bypass circuit-breaker retry loop. Regression: `tests/unit/dataframes/test_storage.py` (S3-LOOP test cluster).

### BROAD-CATCH Classification

20+ `except Exception` blocks annotated with `ADVISORY` or `SCAR-IDEM-001: VERIFY-BEFORE-PROD` comments to distinguish intentional vs. defensive catches.

### Known Gaps in Defensive Pattern Documentation

- SCAR-004: No dedicated regression test; DEF-005 comment + integration verification only
- SCAR-008: No isolated regression test for snapshot ordering
- SCAR-013: `_SCHEMA_VERSIONING_AVAILABLE = False` import-fallback path has no unit coverage
- SCAR-026: No systematic mock-spec audit confirming all workflow test mocks use `spec=`
- SCAR-REG-001: Production blocker — sequential placeholder GIDs unverified against live Asana API
- Metrics CLI Under-count: No defensive guard exists yet; 4 root-cause questions open

## Agent-Relevance Tagging

| Scar | Relevant Roles | Constraint |
|---|---|---|
| SCAR-001 | principal-engineer, architect | New entity/holder classes must define `PRIMARY_PROJECT_GID` |
| SCAR-002 | principal-engineer | Section persistence must use `in_progress_since` + stale timeout |
| SCAR-005/006 | principal-engineer | New cascade columns must use `source="cascade:..."`; `source=None` silently bypasses pipeline |
| SCAR-008 | principal-engineer | In `SaveSession`, always clear accessor state BEFORE capturing snapshot |
| SCAR-009 | principal-engineer, qa-adversary | Tests must set `ASANA_WORKSPACE_GID`; never rely on sync auto-detect |
| SCAR-010/010b | principal-engineer | All `SaveSession` state access through `_require_open()` |
| SCAR-011 | platform-engineer | ECS health checks must target `/health` (liveness) |
| SCAR-011b | principal-engineer | Any new startup dependency must gate through `/health/ready` |
| SCAR-012 | principal-engineer | New cross-service clients must use `ServiceTokenAuthProvider` with `client_credentials` |
| SCAR-013 | principal-engineer | Optional SDK imports must use `try/except ImportError` with feature flag |
| SCAR-014 | principal-engineer | Lifecycle config models must NOT set `extra="forbid"` |
| SCAR-015 | architect | I/O-heavy data must be pre-computed at warm-up; request path pure-CPU |
| SCAR-023 | principal-engineer | Always specify `source=` value for cascade columns |
| SCAR-026 | qa-adversary | Test mocks for SDK clients must use `spec=` |
| SCAR-027 | principal-engineer | Never pass user-controlled strings as `re.sub` replacement |
| SCAR-028 | principal-engineer | All error log sites with user data must call `mask_pii_in_string()` |
| SCAR-029 | principal-engineer | Validate GIDs with `str.strip()` before Pydantic normalization |
| SCAR-030 | principal-engineer | Section names must come from live Asana API (ALL CAPS invariant) |
| SCAR-S3-LOOP | platform-engineer | Permanent S3 errors must not be fed to circuit breaker |
| SCAR-IDEM-001 | principal-engineer | S2S strict-once callers need error metric on finalize failure |
| SCAR-REG-001 | platform-engineer | Section GIDs require live API verification before production |
| SCAR-WS8 | principal-engineer | Every new PAT-tagged router requires corresponding `jwt_auth_config.exclude_paths` entry |
| Env Var Naming | principal-engineer | All ecosystem env vars use `AUTOM8Y_` prefix (not `AUTOM8_`) |
| Metrics CLI Under-count | observability-engineer | `autom8-query` CLI parquet loading silently drops sections — verify bucket mapping |

12 scars (34%) still untagged: SCAR-003, 004, 007, 016–019, 020, 022, 024, 025.

## Knowledge Gaps

1. **SCAR-CANDIDATE-B not catalogued**: `PhoneNormalizer` `NumberParseException` fix at `0f18f4e8`; no SCAR ID assigned
2. **SCAR-CANDIDATE-C not catalogued**: `list_workflows` `response_model` fix at `bb97a744`; no SCAR entry
3. **Metrics CLI Under-count not assigned SCAR ID**: 4 root-cause questions open
4. **12 scars missing agent-relevance tags**
5. **SCAR-004, SCAR-008 isolation tests absent**
6. **SCAR-013 import-fallback path untested**
7. **SCAR-026 mock-spec audit missing**
8. **SCAR-IDEM-001 mitigation incomplete**: observability-only fix; double-execution risk for S2S strict-once callers remains open
9. **SCAR-REG-001 production blocker**: Sequential placeholder GIDs at `section_registry.py:100-107,132-138` must be replaced with verified GIDs before production
10. **xdist re-enabled (CHANGE-003)**: `test_parallel: true` restored by commit `affbf5a5`. CI verification deferred to sprint-5 post-merge
