---
domain: scar-tissue
generated_at: "2026-04-29T00:04Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./tests/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "80256049"
confidence: 0.95
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Scar Tissue

> Regenerated 2026-04-29 (FULL mode). Source hash: `80256049` (post-PR38 merge).
> 36+ distinct failures documented. One new scar added (SCAR-DISCRIMINATOR-001).
> One scar discharged (CSI-001). SCAR-WS8 regression test confirmed committed.

## Failure Catalog

36+ distinct failures documented from two evidence sources (git commit history + code marker scan). The following SCAR identifiers are confirmed present in the live codebase at source_hash `80256049`: SCAR-005 (20+ refs), SCAR-REG-001 (9 refs), SCAR-IDEM-001 (7 refs), SCAR-015 (5 refs), SCAR-020 (2 refs), SCAR-006 (1 ref). DEF identifiers active: DEF-005 (5 refs), DEF-001 (3 refs), DEF-02 (1 ref).

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
| SCAR-DISCRIMINATOR-001 | `_predicate_discriminator` dict-only guard — `NotGroup(not_=AndGroup(...))` fails Pydantic validation when constructed via model-instance kwargs | Data Model / Type Contract | Discovered 2026-04-29; no fix committed (P3 — no production caller reaches this path) |
| Env Var Naming | `AUTOM8_DATA_API_KEY` typo (missing Y) — production API auth failures | Authentication | `clients/data/config.py:231` |
| CSI-001 | **DISCHARGED** `docs/api-reference/openapi.json` hand-edited at `cdcfaee6` to add 13 M-02 examples not derivable from Pydantic source | Documentation / Spec Drift | DISCHARGED 2026-04-29 via T-08 (`4d4097c3`), PR #38 (`80256049`) |

### New Candidates Not Yet Assigned SCAR IDs

- **SCAR-CANDIDATE-B**: `PhoneNormalizer.normalize()` previously lacked `NumberParseException` in its except tuple. Fix: `models/business/matching/normalizers.py:77-82`, commit `0f18f4e8`.
- **SCAR-CANDIDATE-C**: `list_workflows` handler missing `response_model`. Fix: `api/routes/workflows.py`, commit `bb97a744`.
- **Metrics CLI Under-count** (session-20260427): `autom8-query` CLI silently under-counts active sections (~6 in parquet vs ~22 expected). Root cause unresolved — 4 open questions: bucket mapping, freshness SLA, section-coverage gap, staleness-surface decision. Location: `metrics/compute.py`, `dataframes/offline.py`.

---

## SCAR-DISCRIMINATOR-001 (New — Added 2026-04-29)

**Severity**: P3 — no production caller currently constructs `NotGroup(not_=group)`; the bug is only reachable via test code.

**Symptom**: `NotGroup(not_=AndGroup([...]))` and `NotGroup(not_=OrGroup([...]))` fail Pydantic validation with error:
```
not_.comparison  Input should be a valid dictionary or instance of Comparison
```

**Root Cause**: `_predicate_discriminator` at `src/autom8_asana/query/models.py:97-112` handles only `isinstance(v, dict)` inputs (line 102 guard). When a model instance (e.g., `AndGroup`, `OrGroup`, `NotGroup`) is passed as the `not_` argument instead of a raw dict, the `isinstance(v, dict)` branch is skipped and execution falls through to `return "comparison"` at line 112. Pydantic then attempts `Comparison` validation on a group-model instance, which fails.

**Declaration vs Implementation Divergence**:
- **Type declaration** (line 129-135): `PredicateNode` is the full discriminated union — `Comparison | AndGroup | OrGroup | NotGroup`.
- **Runtime enforcement** (line 102-112): Only `dict` inputs are classified to `and`/`or`/`not` variants; model-instance inputs are silently forced to `"comparison"`, making nested-group-via-instance construction non-functional.

**Anchor**:
- Implementation: `src/autom8_asana/query/models.py:97-112` (`_predicate_discriminator` function)
- Type declaration: `src/autom8_asana/query/models.py:129-135` (`PredicateNode = Annotated[...]`)
- Discovered: 2026-04-29 during eunomia rite CHANGE-001 (recorded in `.sos/wip/eunomia-verdict-2026-04-29.md`)
- Related commit antecedent: `321909c1` (eunomia rite attempt that surfaced this failure)
- Glint: `glint-scar-discriminator-001-absent` in `.sos/wip/glints/post-PR38-knowledge-gaps-2026-04-29.md`

**Workaround**: Callers construct nested groups by passing raw dicts (not model instances), OR avoid nested-not patterns entirely. The `_wrap_flat_array_to_and_group` helper at line 115-126 exemplifies the correct dict-passing pattern.

**Proposed Fix**: Add `isinstance(v, BaseModel)` branch before the `return "comparison"` fallthrough that inspects `model_fields` keys (check for `"and_"`, `"or_"`, `"not_"`, `"field"`/`"operator"`) to route model-instance inputs correctly.

**Owner-rite for fix**: hygiene-pass-2 (Sprint-4)

**Related throughline**: `canonical-source-integrity` — declared type contract (`PredicateNode` full union) diverges from runtime discriminator behavior (dict-only classification).

---

## CSI-001 DISCHARGE Record (Historical — Resolved 2026-04-29)

**Original Scar**: `docs/api-reference/openapi.json` was hand-edited at commit `cdcfaee6` to add 13 M-02 field examples not derivable from Pydantic source declarations. This created a spec-drift gap: every `just spec-gen` regeneration would silently drop the 13 examples, requiring manual re-insertion.

**Discharge**: T-08 (commit `4d4097c3`) lifted all 13 examples to `Field(examples=[...])` declarations on:
- `src/autom8_asana/models/base.py:50` (Task)
- `src/autom8_asana/models/common.py:52` (NameGid)
- `src/autom8_asana/models/task.py:47,54,59,70,85` (multiple fields)
- `src/autom8_asana/api/routes/workflows.py:75,80,85,135,140,145,150,156,161,178,183` (WorkflowEntry/SchemaFieldInfo)
- `src/autom8_asana/api/routes/resolver_schema.py:72,76,346,350` (EnumValueInfo)

**Verification**: `just spec-gen` reproduces all 13 examples natively post-discharge. `docs/api-reference/openapi.json` now carries 136 `"examples":` entries. Spec-check PASS.

**Status**: DISCHARGED 2026-04-29 (PR #38 merge `80256049`).

**Residual exception**: 2 `"example":` (singular) entries remain at `src/autom8_asana/api/routes/dataframes.py:511,632` — raw dict inline OpenAPI 3.0 annotation (pre-existing pattern, not Pydantic `Field()`). These predate CSI-001 and are an exception to the `examples=[...]` convention, not a regression.

---

## Category Coverage

10 distinct failure categories applied across all 36+ scars:

| Category | Scars | Count |
|---|---|---|
| Cache Coherence / Stale Data | SCAR-003, 004, 005, 006, 007, S3-LOOP | 6 |
| Data Model / Contract Violation | SCAR-008, 014, 023, 024, 025, 030, IDEM-001, REG-001, CANDIDATE-B, CANDIDATE-C, SCAR-DISCRIMINATOR-001 | 11 |
| Startup / Deployment Failure | SCAR-009, 011, 011b, 013, 022 | 5 |
| Workflow Logic Gap | SCAR-016, 017, 018, 019, 020 | 5 |
| Security / Input Validation | SCAR-027, 028, 029, WS8 | 4 |
| Concurrency / Race Condition | SCAR-002, 010, 010b | 3 |
| Authentication / Authorization | SCAR-012, Env Var Naming | 2 |
| Integration Failure / CI | SCAR-021, 026 | 2 |
| Performance Cliff / Timeout | SCAR-015 | 1 |
| Observability Gap | Metrics CLI Under-count | 1 |

Three categories explicitly searched and returned no results: schema migration failures, distributed coordination failures, network partition handling. SCAR-WS8 classified under Security (more precise than Integration).

---

## Fix-Location Mapping

All major scars have file:line or function-level locations. 22 primary fix paths verified present at source_hash `80256049`:

| Scar | Primary Fix Path | Verified |
|---|---|---|
| SCAR-005/006 | `src/autom8_asana/dataframes/builders/progressive.py:161,466` | Yes |
| SCAR-005/006 | `src/autom8_asana/dataframes/cascade_utils.py:27,289` | Yes |
| SCAR-005/006 (cascade contract) | `src/autom8_asana/dataframes/schemas/offer.py:22` (`source="cascade:Office Phone"`) | Yes |
| SCAR-005/006 (cascade validator) | `src/autom8_asana/dataframes/builders/cascade_validator.py:30-32` | Yes |
| SCAR-005/006 (post-build) | `src/autom8_asana/dataframes/builders/post_build_validation.py:90-105` | Yes |
| SCAR-005/006 (WarmupOrderingError) | `src/autom8_asana/dataframes/cascade_utils.py:22-30` | Yes |
| SCAR-005/006 (WarmupOrderingError re-raise) | `src/autom8_asana/api/preload/progressive.py:696-699` | Yes |
| SCAR-008 / DEF-001 | `src/autom8_asana/persistence/session.py:995-1001` | Yes |
| SCAR-015 | `src/autom8_asana/services/section_timeline_service.py` (pre-computed timelines) | Yes |
| SCAR-020 / SCAR-023 (PhoneTextField) | `src/autom8_asana/models/business/descriptors.py:472-498` | Yes |
| SCAR-020 / SCAR-023 (PhoneTextField applied) | `src/autom8_asana/models/business/business.py:267` | Yes |
| SCAR-022 / DEF-009 | `Dockerfile` (`--no-sources` flag, commit `2229f4a3`) | Yes |
| SCAR-IDEM-001 | `src/autom8_asana/api/middleware/idempotency.py:719` | Yes |
| SCAR-REG-001 | `src/autom8_asana/reconciliation/section_registry.py:94,128` | Yes |
| SCAR-WS8 / DEF-08 | `src/autom8_asana/api/main.py:389` (`/api/v1/exports/*` in exclude_paths) | Yes |
| SCAR-DISCRIMINATOR-001 (bug location) | `src/autom8_asana/query/models.py:97-112` (`_predicate_discriminator`) | Yes — empirically verified 2026-04-29 |
| SCAR-DISCRIMINATOR-001 (type declaration) | `src/autom8_asana/query/models.py:129-135` (`PredicateNode`) | Yes — empirically verified 2026-04-29 |
| SCAR-S3-LOOP | `src/autom8_asana/core/retry.py:198` (`_PERMANENT_S3_ERROR_CODES`) | Yes |
| DEF-001 (resolver route) | `src/autom8_asana/api/routes/resolver.py:335` | Yes |
| DEF-005 (shared CacheProvider) | `src/autom8_asana/api/lifespan.py:108,126` | Yes |
| DEF-005 (client pool) | `src/autom8_asana/api/client_pool.py:201` | Yes |
| Env Var Naming | `src/autom8_asana/clients/data/config.py:231` (`AUTOM8Y_DATA_API_KEY`) | Yes |
| PKG-002 (env collision) | `tests/synthetic/conftest.py:78-80` | Yes |

---

## Defensive Pattern Documentation

### Cascade Defense-in-Depth (SCAR-005/006/023) — Four Layers

1. **Schema enforcement**: `source="cascade:..."` required on cascade columns. `source=None` silently bypasses pipeline (SCAR-023 root cause). Live: `src/autom8_asana/dataframes/schemas/offer.py:22` (post-fix).
2. **Warm-up ordering guard**: `WarmupOrderingError` at `src/autom8_asana/dataframes/cascade_utils.py:22-30`. BROAD-CATCH immune. Re-raised at `src/autom8_asana/api/preload/progressive.py:696-699`.
3. **Post-build null rate audit**: `CASCADE_NULL_WARN_THRESHOLD = 0.05` (5%), `CASCADE_NULL_ERROR_THRESHOLD = 0.20` (20%) at `src/autom8_asana/dataframes/builders/cascade_validator.py:31-32`. Calibrated against SCAR-005's 30% incident.
4. **Chain traversal gap-skipping**: `src/autom8_asana/dataframes/views/cascade_view.py` (parent chain resolution with null-safe gaps).

**Regression tests**: `tests/unit/dataframes/test_cascade_ordering_assertion.py:71-106`, `test_warmup_ordering_guard.py`, `tests/unit/dataframes/builders/test_cascade_validator.py:649-668` (SCAR-005 30% scenario).

### Session Thread Safety (SCAR-010/010b)

`threading.RLock()` on all state mutations; `_require_open()` context manager at `src/autom8_asana/persistence/session.py`. Regression: `tests/unit/persistence/test_session_concurrency.py` (19+ tests).

### Session Snapshot Ordering (SCAR-008 / DEF-001)

Order-critical fix at `src/autom8_asana/persistence/session.py:995-1001`: accessor state (`_reset_custom_field_tracking`) cleared BEFORE `mark_clean()` captures snapshot. Reversal re-introduces stale state.

### Health Check Separation (SCAR-011/011b)

`/health` always returns 200 (liveness). `/health/ready` gates on `_cache_ready AND _workflow_configs_registered` (readiness). Regression: `tests/unit/api/test_lifespan_workflow_import.py`.

### Security Hardening (SCAR-027/028/029)

- Lambda replacement guard in `re.sub` at `src/autom8_asana/core/creation.py:82-97`
- `mask_pii_in_string()` at `src/autom8_asana/clients/data/_pii.py:61`
- GID `str.strip()` guard at `src/autom8_asana/api/routes/webhooks.py:375-381`

### Phone Normalization on Read Path (SCAR-020 / SCAR-CANDIDATE-B)

`PhoneTextField` descriptor at `src/autom8_asana/models/business/descriptors.py:472-498` normalizes `office_phone`, `twilio_phone_num` to E.164 on read. Applied at `src/autom8_asana/models/business/business.py:267`. `PhoneNormalizer` now includes `NumberParseException` in except tuple. Regression: `tests/unit/models/business/matching/test_normalizers.py:64-70` (SCAR-020 guard).

### Idempotency Finalize Observability (SCAR-IDEM-001)

Exception on `finalize()` promoted to `logger.exception` with `impact` field at `src/autom8_asana/api/middleware/idempotency.py:719-728`. **Known gap**: observability-only fix; double-execution risk for S2S strict-once callers remains open per `ADR-omniscience-idempotency Section 3.7`. Regression: `tests/unit/api/middleware/test_idempotency_finalize_scar.py` (SCAR-IDEM-001-A, -B, -C).

### JWT Exclude-Paths Sync (SCAR-WS8 / DEF-08) — Updated 2026-04-29

`/api/v1/exports/*` added to `jwt_auth_config.exclude_paths` at `src/autom8_asana/api/main.py:389`. Structural invariant: every PAT-tagged router registration must have a corresponding `exclude_paths` entry.

**Regression test**: `tests/unit/api/test_exports_auth_exclusion.py` — live middleware introspection (no mocking). **Committed post-PR38** (T-09). Status confirmed at source_hash `80256049`.

### S3 Circuit Breaker (SCAR-S3-LOOP)

`_PERMANENT_S3_ERROR_CODES: frozenset[str]` at `src/autom8_asana/core/retry.py:198` — permanent codes bypass circuit-breaker retry loop. Regression: `tests/unit/dataframes/test_storage.py` (S3-LOOP test cluster).

### BROAD-CATCH Classification

20+ `except Exception` blocks annotated with `ADVISORY` or `SCAR-IDEM-001: VERIFY-BEFORE-PROD` comments to distinguish intentional vs. defensive catches.

### SCAR-DISCRIMINATOR-001 — No Defensive Pattern Yet

No guard added. Workaround: callers use raw dict construction (not model-instance kwargs). No regression test covering `NotGroup(not_=AndGroup([...]))` via model-instance path. This path is syntactically valid per type declaration but fails at runtime. **Unguarded at source_hash `80256049`**. [KNOW-CANDIDATE] Novel scar with no defensive pattern; hygiene-pass-2 regression test needed.

### Known Gaps in Defensive Pattern Documentation

- SCAR-004: No dedicated regression test; DEF-005 comment + integration verification only
- SCAR-008: No isolated regression test for snapshot ordering
- SCAR-013: `_SCHEMA_VERSIONING_AVAILABLE = False` import-fallback path has no unit coverage
- SCAR-026: No systematic mock-spec audit confirming all workflow test mocks use `spec=`
- SCAR-REG-001: Production blocker — sequential placeholder GIDs unverified against live Asana API
- Metrics CLI Under-count: No defensive guard exists yet; 4 root-cause questions open
- SCAR-DISCRIMINATOR-001: No defensive guard, no regression test; fix deferred to hygiene-pass-2

---

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
| SCAR-DISCRIMINATOR-001 | principal-engineer, qa-adversary | When constructing `NotGroup` or any nested predicate node, use raw dicts (not model instances) as kwargs to avoid discriminator fallthrough; test nested-not paths explicitly |
| Env Var Naming | principal-engineer | All ecosystem env vars use `AUTOM8Y_` prefix (not `AUTOM8_`) |
| Metrics CLI Under-count | observability-engineer | `autom8-query` CLI parquet loading silently drops sections — verify bucket mapping |

12 scars still untagged (reduced from 12 at prior hash): SCAR-003, 004, 007, 016–019, 020, 022, 024, 025. [KNOW-CANDIDATE?] These 12 may warrant agent-relevance tags in a subsequent hygiene pass if any touch active development paths.

---

## Knowledge Gaps

1. **SCAR-CANDIDATE-B not catalogued**: `PhoneNormalizer` `NumberParseException` fix at `0f18f4e8`; no SCAR ID assigned
2. **SCAR-CANDIDATE-C not catalogued**: `list_workflows` `response_model` fix at `bb97a744`; no SCAR entry
3. **Metrics CLI Under-count not assigned SCAR ID**: 4 root-cause questions open
4. **12 scars missing agent-relevance tags** (SCAR-003, 004, 007, 016-019, 020, 022, 024, 025)
5. **SCAR-004, SCAR-008 isolation tests absent**
6. **SCAR-013 import-fallback path untested**
7. **SCAR-026 mock-spec audit missing**
8. **SCAR-IDEM-001 mitigation incomplete**: observability-only fix; double-execution risk for S2S strict-once callers remains open
9. **SCAR-REG-001 production blocker**: Sequential placeholder GIDs at `section_registry.py:100-107,132-138` must be replaced with verified GIDs before production
10. **xdist re-enabled (CHANGE-003)**: `test_parallel: true` restored by commit `affbf5a5`. CI verification deferred to sprint-5 post-merge
11. **SCAR-DISCRIMINATOR-001 unguarded**: No regression test, no defensive pattern, fix deferred to hygiene-pass-2

---

<!-- [KNOW-CANDIDATE] SCAR-LOG-001 — authored by janitor at WS-4 T3 terminal closure 2026-04-29. Candidate for absorption into a dedicated ## Scar Entries section on next /know cycle. -->

### SCAR-LOG-001: autom8y-log SDK lacks stdlib `logging.Logger` interface (TENSION-021 candidate)

**Origin**: WS-4 inaugural-hygiene-cleanup 2026-04-29 T2/T3 compounding-gap pattern.

**Symptom**: any module migrating from `logging.getLogger(name)` to
`autom8y_log.get_logger(name)` cannot retain calls or attribute accesses that
treat the result as a stdlib `logging.Logger`. Direct probe at
2026-04-29 against `autom8y-log==0.5.x` confirmed 11 of 11 stdlib `Logger`
attributes (`name`, `isEnabledFor`, `level`, `handlers`, `propagate`,
`getEffectiveLevel`, `addHandler`, `setLevel`, `removeHandler`,
`hasHandlers`, `callHandlers`) are ABSENT from both `BoundLoggerLazyProxy`
(pre-bind) and `BoundLoggerFilteringAtInfo` (post-bind). The SDK returns a
structlog object family that is interface-disjoint from stdlib `Logger` by
design.

**Defensive pattern**: when a satellite module exposes a `_logger` attribute
that internal callers OR tests treat as stdlib-Logger-shaped (e.g.,
`provider._logger.name`, `provider._logger.isEnabledFor(level)`), do NOT
migrate the module body to `autom8y_log.get_logger(...)`. The migration
breaks the test contract AND the public attribute contract. Retain
`import logging` + a file-level `[tool.ruff.lint.per-file-ignores]` TID251
exemption with an inline rationale comment pointing at this scar entry.

**Vector**: SDK-enhancement initiative at autom8y-log to add a stdlib-Logger-
compatibility shim — either a `StdlibLoggerAdapter` exposing the 11 attributes
above by delegation to `logging.getLogger(name)` under the hood, OR a
`get_stdlib_compatible_logger(name)` factory returning a stdlib-shaped object
with structured-log fan-out behind the scenes. Until shipped, satellite
migration of `_defaults/log.py`-class modules is architecturally infeasible.

---

<!-- [KNOW-CANDIDATE] SCAR-LP-001 — authored by principal-engineer at Phase 4 cleanup-and-attest 2026-04-29 for PT-3 verdict A (CLOSE-WITH-FLAGS) on lockfile-propagator path-resolution fix. Candidate for absorption into the canonical Failure Catalog table on next /know cycle. -->

### SCAR-LP-001: lockfile-propagator stub-before-uv-lock ordering invariant

**Origin**: SDK publish pipeline cascade failures observed in workflow runs `25052186961` (autom8y-config 2.0.1) and `25062121802` (autom8y-config 2.0.2); fix landed in autom8y PR #174 (merge SHA `f2dfc1c3`); attestation closed under PT-3 verdict A on 2026-04-29.

**Pre-fix failure mode (verbatim)**: `error: Distribution not found at: file:///tmp/lockfile-propagator-4qdmcw0j/autom8y-api-schemas` — emitted by `uv lock` exit-2 inside the `Notify Satellite Repos` job at `autom8y/.github/workflows/sdk-publish-v2.yml:1051-1087` for ALL 5 satellites (autom8y-asana, autom8y-data, autom8y-scheduling, autom8y-sms, autom8y-ads). Wrapped as `LockfileError` at `autom8y/tools/lockfile-propagator/src/lockfile_propagator/lockfile_updater.py:113-117`; surfaced in the per-satellite `status="failed"` verdict.

**Root cause (path-resolution under sandboxed temp clone)**: each satellite is cloned by the propagator into `/tmp/lockfile-propagator-XXXXXXXX/<satellite>/` via `SubprocessGitOps.clone_shallow` at `autom8y/tools/lockfile-propagator/src/lockfile_propagator/repo_clone.py:99-125`. `uv lock` is then invoked with `cwd=repo_dir` at `autom8y/tools/lockfile-propagator/src/lockfile_propagator/lockfile_updater.py:96-105`. Each satellite's `pyproject.toml` declares `[tool.uv.sources]` editable references of shape `path = "../X"` (verified at `pyproject.toml:326-331` for autom8y-asana plus the four sibling satellite files). uv resolves `..` against `repo_dir` — but from the sandboxed clone, `..` resolves to `/tmp/lockfile-propagator-XXX/`, which contains only OTHER satellite clones — NOT the developer-side siblings (`autom8y-api-schemas`, `autom8y/sdks/python/...`). Resolution fails. **TDD §5.3 ordering invariant**: stub directories MUST be visible to the uv runner BEFORE `uv lock` fires; the fix prescribes a single insertion point between the post-`checkout_branch` line and the `pyproject_changed = False` line in `propagator.py`.

**Fix shape (in-tool source stubbing — Option A)**: new module `autom8y/tools/lockfile-propagator/src/lockfile_propagator/source_stub.py` exporting `stub_editable_path_sources(repo_dir, work_root)` that parses `[tool.uv.sources]`, discriminates path-shape entries from git/url/index-shape entries, and writes minimal `pyproject.toml`-only stubs (with `[project]` + `[build-system]` hatchling, no Python sources) at the resolved relative-path locations inside `work_root`. Single integration call site in `propagator.py` per TDD §3.5. Stub creation precedes the uv-runner invocation by construction (TDD §5.3 ordering test at `tools/lockfile-propagator/tests/test_propagator.py:359` (`TestPathSourcesStubbedBeforeUvLockRuns`); §5.2 integration test at `tools/lockfile-propagator/tests/test_source_stub.py:366` (`test_integration_autom8y_asana_failure_mode`) reproduces the autom8y-asana failure mode pre-stub then asserts post-stub `uv lock` succeeds).

**Defensive pattern for future propagator-style tools**: any tool that (a) clones consumer repositories into a sandboxed temp directory AND (b) invokes a resolver tool with `cwd=clone_dir` AND (c) the consumer declares relative-path source references resolving outside its own tree — MUST materialize the resolution surface inside the sandbox before invoking the resolver. The trust boundary is the satellite repo's own branch-protected `pyproject.toml`; stubbing inside the sandbox preserves that boundary while making the resolver call viable. Three discriminators MUST be honored: (1) only stub entries where the source-shape declares a relative `path = ...` (do NOT stub `git = ...`, `url = ...`, `index = ...` shapes); (2) the stub's `pyproject.toml` only requires `[project]` + `[build-system]` for `uv lock` (importable Python modules are required only by `uv sync`, NOT by `uv lock` — empirically confirmed in TDD §4 OQ-A); (3) idempotency on re-run of the same `work_root` (skip when `stub_dir/pyproject.toml` exists). The api-schemas-stub composite action at `autom8y/.github/actions/api-schemas-stub/action.yml:1-103` is the precedent at publish-job altitude; SCAR-LP-001 extends the same pattern down to sub-clone altitude.

**Vector**: post-merge production-CI verification is DEFERRED. Two post-merge runs (`25083219816` autom8y-meta and `25084290648` autom8y-google 0.1.0) each FAILED at the `Publish` step (CodeArtifact 409 / version-already-exists) — DIFFERENT step from the `Notify Satellite Repos` step the fix targets — and Notify was therefore SKIPPED on both. Mechanical equivalence is ATTESTED (5/5 satellites' `[tool.uv.sources]` shapes verified for path-shape applicability per TDD §4 OQ-C; canonical autom8y-asana case verified end-to-end via §5.2 integration test). Production-CI green-on-Notify confirmation is tracked at defer-watch entry `lockfile-propagator-prod-ci-confirmation` in `.know/defer-watch.yaml` with deadline 2026-07-29. Closing trigger: any of the 5 satellites' next push-triggered SDK version bump producing a workflow run with `Notify-Satellite-Repos = SUCCESS` AND the `uv-lock` step completing without `Distribution not found`.

**Agent-relevance**: principal-engineer (when modifying or extending the propagator); architect (when designing similar sandbox-resolver tools — apply the three-discriminator defensive pattern); qa-adversary (the §5.2 integration test is a hermetic-CI-without-uv guard via `pytest.mark.skipif(shutil.which("uv") is None, ...)`).

**Cross-reference**: `.ledge/decisions/inaugural-hygiene-cleanup-disposition-WS4-T3-terminal-2026-04-29.md` §4.
