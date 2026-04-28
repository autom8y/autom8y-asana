---
domain: scar-tissue
generated_at: "2026-04-24T00:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "acff02ab"
confidence: 0.91
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/scar-tissue.md"
land_hash: "0a21b8d2148d7837d02525e91044995b417a2a2f282f4439282f157d9c27b46b"
---

# Codebase Scar Tissue

## Failure Catalog Completeness

Evidence gathered via two full passes: (1) `git log --oneline --all -n 500` filtered for fix/bug/regression/revert/hotfix keywords — yielding 130+ matching commits; (2) `rg` scan of all `src/` and `tests/` for CRITICAL, HACK, FIXME, BUG-, SCAR-, DEF-, WORKAROUND markers — yielding 85 matching lines across 40+ files.

The prior `.know/scar-tissue.md` (generated 2026-04-04, `source_hash: 55aaab5`) documents 33 named scars: SCAR-001 through SCAR-030, SCAR-S3-LOOP, SCAR-IDEM-001, SCAR-REG-001, SCAR-WS8, plus the Env Var Naming scar. Code marker scan confirms the following SCAR identifiers are present in the live codebase: SCAR-005 (20 refs), SCAR-REG-001 (9 refs), SCAR-IDEM-001 (7 refs), SCAR-015 (5 refs), SCAR-020 (2 refs), SCAR-006 (1 ref). DEF identifiers active: DEF-005 (5 refs), DEF-003 (3 refs), DEF-001 (3 refs), DEF-002 (2 refs). All cross-referenced to catalog entries.

### New Candidate Scars (post-2026-04-04, not yet catalogued)

**SCAR-CANDIDATE-A**: OpenAPI E.164 phone pattern not enforced at property level. Commits: `e1cd59c4` (fix(spectral): elevate E164 pattern on ResolutionCriterion phone fields), `4889d3a9` (fix(openapi): lift office_phone pattern to property level for spectral e164 rule). Fix location: `docs/api-reference/openapi.json` (generated artifact). May relate to but is distinct from SCAR-020/024 phone normalization.

**SCAR-CANDIDATE-B**: `PhoneNormalizer.normalize` previously did not catch `NumberParseException`. Commit: `0f18f4e8` (fix(matching): catch NumberParseException in PhoneNormalizer.normalize). Fix location: `src/autom8_asana/models/business/matching/normalizers.py:77-82` (now includes `phonenumbers.phonenumberutil.NumberParseException` in the except tuple).

**SCAR-CANDIDATE-C**: `list_workflows` handler missing `response_model`. Commit: `bb97a744` (fix(api): add typed response_model to list_workflows handler). Fix location: `src/autom8_asana/api/routes/workflows.py`. Causes OpenAPI spec drift and unvalidated response payloads.

**Completeness assessment**: 33 of approximately 35 observable distinct failures documented = ~94%. Three candidates missing.

## Category Coverage

10 distinct failure categories applied across all 33+ scars, with explicit "searched but not found" notation for schema migration failures, distributed coordination failures, and network partition handling.

| Category | Scars | Count |
|---|---|---|
| Cache Coherence / Stale Data | SCAR-003, 004, 005, 006, 007, S3-LOOP | 6 |
| Data Model / Contract Violation | SCAR-008, 014, 023, 024, 025, 030, IDEM-001, REG-001 | 8 |
| Startup / Deployment Failure | SCAR-009, 011, 011b, 013, 022 | 5 |
| Workflow Logic Gap | SCAR-016, 017, 018, 019, 020 | 5 |
| Security / Input Validation | SCAR-027, 028, 029 | 3 |
| Concurrency / Race Condition | SCAR-002, 010, 010b | 3 |
| Authentication / Authorization | SCAR-012, Env Var Naming | 2 |
| Integration Failure / CI | SCAR-021, 026 | 2 |
| Entity Resolution / Collision | SCAR-001 | 1 |
| Performance Cliff / Timeout | SCAR-015 | 1 |

All 10 categories have 2+ scars except Entity Resolution and Performance Cliff (1 each). Three categories explicitly searched and returned no results. The SCAR-CANDIDATE entries (phone parsing exception, untyped route) would map to Data Model / Contract Violation and Integration Failure / CI respectively.

## Fix-Location Mapping

Every scar in the catalog includes at minimum one file path. Verification spot-checks against live codebase:

| Scar | Primary Fix Path | Verified Present |
|---|---|---|
| SCAR-005/006 | `src/autom8_asana/dataframes/builders/progressive.py:161,466` | Yes |
| SCAR-005/006 | `src/autom8_asana/dataframes/cascade_utils.py:27,289` | Yes |
| SCAR-IDEM-001 | `src/autom8_asana/api/middleware/idempotency.py:719` | Yes |
| SCAR-REG-001 | `src/autom8_asana/reconciliation/section_registry.py:94,128` | Yes |
| SCAR-020 | `src/autom8_asana/api/routes/resolver.py:335` | Yes (DEF-001 reference) |
| SCAR-015 | `src/autom8_asana/services/section_timeline_service.py` | Yes |
| DEF-005 | `src/autom8_asana/api/lifespan.py:108,126` | Yes |
| DEF-001 | `src/autom8_asana/persistence/session.py:995` | Yes |
| DEF-009/SCAR-022 | `Dockerfile:11,53-54` | Yes |

All documented primary fix-file paths verified present. Some older scars (SCAR-001–013) reference commits outside the 500-commit window but their fix files exist.

## Defensive Pattern Documentation

The catalog documents defensive patterns for all major scars, grouped into five named clusters:

**Cascade Defense-in-Depth (SCAR-005/006/023)** — Four layers:
1. Schema enforcement: `source="cascade:..."` required — enforced by `DataFrameSchema`
2. Warm-up ordering guard: `WarmupOrderingError` at `src/autom8_asana/dataframes/cascade_utils.py:22` — BROAD-CATCH immune; explicitly re-raised at `src/autom8_asana/api/preload/progressive.py:696-699`
3. Post-build null rate audit: `CASCADE_NULL_WARN_THRESHOLD = 0.05`, `CASCADE_NULL_ERROR_THRESHOLD = 0.20` at `src/autom8_asana/dataframes/builders/cascade_validator.py:31-32` — calibrated against SCAR-005's 30% production incident
4. Chain traversal gap-skipping: `src/autom8_asana/dataframes/views/cascade_view.py:356`

Regression tests: `tests/unit/dataframes/test_cascade_ordering_assertion.py:71-106`, `tests/unit/dataframes/test_warmup_ordering_guard.py`, `tests/unit/dataframes/builders/test_cascade_validator.py:649-668`

**Session Thread Safety (SCAR-010/010b)** — `threading.RLock()` on all state mutations; `_require_open()` context manager at `src/autom8_asana/persistence/session.py`. Regression: `tests/unit/persistence/test_session_concurrency.py` (19+ tests)

**Health Check Separation (SCAR-011/011b)** — `/health` always 200; `/health/ready` gates on `_cache_ready AND _workflow_configs_registered`. Regression: `tests/unit/api/test_lifespan_workflow_import.py`

**Security Hardening (SCAR-027/028/029)** — Lambda replacement in `re.sub` at `src/autom8_asana/core/creation.py:82-97`; `mask_pii_in_string()` at `src/autom8_asana/clients/data/_pii.py:61`; GID `str.strip()` guard at `src/autom8_asana/api/routes/webhooks.py:375-381`

**BROAD-CATCH Classification** — 20+ `except Exception` blocks annotated with `ADVISORY` or `SCAR-IDEM-001: VERIFY-BEFORE-PROD` at `src/autom8_asana/api/middleware/idempotency.py:719`

**S3 Circuit Breaker (SCAR-S3-LOOP)** — `_PERMANENT_S3_ERROR_CODES: frozenset[str]` at `src/autom8_asana/core/retry.py:198`

### Known gaps in defensive pattern documentation

- SCAR-004: no dedicated regression test documented
- SCAR-008: no isolated regression test
- SCAR-013: `_SCHEMA_VERSIONING_AVAILABLE = False` path not tested
- SCAR-026: no systematic mock-spec audit
- SCAR-WS8: route ordering has no regression test (acknowledged in entry)
- SCAR-IDEM-001: observability-only fix; double-execution risk not mitigated for S2S callers

## Agent-Relevance Tagging

22 of 34+ scars tagged with agent-relevance + explicit "why" statements:

| Scar | Relevant Roles | Constraint |
|---|---|---|
| SCAR-001 | principal-engineer, architect | New entity/holder classes must define `PRIMARY_PROJECT_GID` |
| SCAR-002 | principal-engineer | Section persistence must use `in_progress_since` + stale timeout |
| SCAR-005/006 | principal-engineer | New cascade columns must use `source="cascade:..."` and appear in BASE_SCHEMA |
| SCAR-008 | principal-engineer | In `SaveSession`, always clear accessor state BEFORE capturing snapshot |
| SCAR-009 | principal-engineer, qa-adversary | Tests must set `ASANA_WORKSPACE_GID`; never rely on sync auto-detect |
| SCAR-010/010b | principal-engineer | All `SaveSession` state access through `_require_open()` context manager |
| SCAR-011 | platform-engineer | ECS health checks must target `/health` (liveness), never `/health/ready` |
| SCAR-011b | principal-engineer | Any new startup dependency must gate through `/health/ready`, not `/health` |
| SCAR-012 | principal-engineer | New cross-service clients must use `ServiceTokenAuthProvider` with `client_credentials` grant |
| SCAR-013 | principal-engineer | Optional SDK imports must use `try/except ImportError` with feature flag |
| SCAR-014 | principal-engineer | Lifecycle config models must NOT set `extra="forbid"` (D-LC-002) |
| SCAR-015 | architect | I/O-heavy data for request handlers must be pre-computed at warm-up |
| SCAR-023 | principal-engineer | `source=None` silently bypasses cascade pipeline |
| SCAR-026 | qa-adversary | Test mocks for SDK clients must use `spec=` |
| SCAR-027 | principal-engineer | Never pass user-controlled strings as `re.sub` replacement |
| SCAR-028 | principal-engineer | All error log sites with user data must call `mask_pii_in_string()` |
| SCAR-029 | principal-engineer | Validate GIDs with `str.strip()` before Pydantic normalization |
| SCAR-030 | principal-engineer | Section names must come from live Asana API verification (ALL CAPS) |
| SCAR-S3-LOOP | platform-engineer | Permanent S3 errors must not be fed to circuit breaker |
| SCAR-IDEM-001 | principal-engineer | S2S callers with strict-once semantics need an error metric on finalize failure |
| SCAR-REG-001 | platform-engineer | Section GIDs require live API verification before production |
| Env Var | principal-engineer | All ecosystem env vars use `AUTOM8Y_` prefix |

Scars not yet tagged: SCAR-003, SCAR-004, SCAR-007, SCAR-016, SCAR-017, SCAR-018, SCAR-019, SCAR-020, SCAR-021, SCAR-022, SCAR-024, SCAR-025, SCAR-WS8. 13 scars untagged (37%).

**[KNOW-CANDIDATE]** SCAR-WS8 route ordering constraint is missing from agent-relevance despite being an active production blocker for engineers touching `src/autom8_asana/api/main.py`.

## Knowledge Gaps

1. **SCAR-CANDIDATE-B not catalogued**: `PhoneNormalizer.normalize()` previously lacked `NumberParseException` in its except tuple (commit `0f18f4e8`). Fix live at `src/autom8_asana/models/business/matching/normalizers.py:77-82`; no SCAR identifier assigned.
2. **SCAR-CANDIDATE-C not catalogued**: `list_workflows` handler missing `response_model` (commit `bb97a744`). Integration Failure / CI category. No SCAR entry.
3. **13 scars missing agent-relevance tags**: SCAR-003, 004, 007, 016–022, 024, 025, WS8.
4. **SCAR-004, SCAR-008 isolation tests absent**: No dedicated regression tests. SCAR-004 gap relies on DEF-005 comment + manual verification.
5. **SCAR-013 import-fallback path untested**: `_SCHEMA_VERSIONING_AVAILABLE = False` branch has no unit coverage.
6. **SCAR-026 mock-spec audit missing**: No systematic review confirms all workflow test mocks use `spec=`.
7. **SCAR-WS8 regression test absent**: Route ordering constraint (intake_resolve_router before resolver_router) documented in `src/autom8_asana/api/main.py:335-338` and LB-003 but not protected by a test.
8. **SCAR-IDEM-001 mitigation incomplete**: Observability-only fix. Double-execution risk for S2S strict-once callers remains open per `ADR-omniscience-idempotency Section 3.7`.
9. **SCAR-REG-001 production blocker**: Sequential placeholder GIDs in `src/autom8_asana/reconciliation/section_registry.py:100-107,132-138` must be replaced with verified GIDs before production.
