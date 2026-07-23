---
domain: scar-tissue
generated_at: "2026-07-23T14:56:44Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./mcp/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "70d45434e1e79ce7bc380936e47a4e265447ffd4db88dc37cd8b37edc70b862f"
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

> Fresh full regeneration at synced HEAD `d0c8b662` (2026-07-23). Prior catalog (41+ scars) verified against live code and preserved; **5 new scars + 1 new defensive-only gate** added. `@pytest.mark.scar` count: **41→46** markers across **11→17** files (grep-confirmed). AL-5/hierarchy-warm 429-storm cure CONFIRMED PRESENT at this HEAD (unlike the earlier stale checkout).

## What Changed Since the Prior Pass

1. **NEW SCAR-REDIS-WARMER-001** — 3-layer redis warmer dead-cache class (`10d7c559`, `bfa4aedb`, `b3da9d8c`).
2. **NEW SCAR-L2GATE-001** — L2 pre-phase gate vs frame-less cascade provider wedge (#192).
3. **NEW SCAR-FRESH-001** — freshness-verification-recency silent-corruption class (ADR-006, T11-T16).
4. **NEW SCAR-AUTHSPECIES-001** — unrecognized JWT token species misrouted 500→401 (#262).
5. **EXTENDS SCAR-AUTHSIG-001** — fail-clean on S2S mint 401 (#264, `mcp/asana_mcp/bridge.py`) — error-opacity lineage N=3.
6. **NEW defensive-only gate: RB-1 confirm-before-firing** (#263, `mcp/asana_mcp/tools/confirm_gate.py`) — addresses SCAR-CANDIDATE-PLAY-CONSUMED-TRIGGER from the pre-fire angle.
7. **query503/C3 taxonomy re-confirmed** — `mcp/asana_mcp/errors.py` + `mcp/tests/test_errors_c3.py` (5 tests): "503 → warming (retryable), NEVER auth; 401/403 → auth, NEVER warming."
8. **AL-5/hierarchy-warm cure CONFIRMED PRESENT** — `cache/integration/hierarchy_warmer.py`, `dataframes/builders/hierarchy_warmer.py`, and their tests all present and non-empty.
9. **SCAR-DISCRIMINATOR-001 — UNCHANGED, still unguarded** — `query/models.py:102` dict-only guard, no fix.
10. **SCAR-REG-001, SCAR-IDEM-001, SCAR-TG-LIVENESS-001, SCAR-VOCAB-PARITY-001 — all remain RESOLVED/CURED**; no regression.
11. **GLINT-002 (config-during-init cold-start) — documented in conventions.md, NO entry in scar-tissue** — [KNOW-CANDIDATE] cross-domain gap; the pattern is scar-shaped.

## SCAR-REDIS-WARMER-001 — 3-layer redis warmer dead-cache class (P1)

Live symptom: `CurrItems=0` always; 34x `backend_entering_degraded_mode` "Too many connections" on the F1a bulk warmer; hierarchy-warm banked into a cache that silently discards everything. Three onion-layers (each masks the next):
1. **Packaging omission** (`b3da9d8c`): prod Dockerfile omitted `--extra redis` → `RedisCacheProvider` hits `except ImportError` → NO-OP cache → warmers bank into a dead cache. Fix: add `--extra redis`; loud `cache_degraded_mode` ERROR (was quiet WARNING).
2. **Connection-pool kwarg leak** (`bfa4aedb`): `ssl=`/`ssl_cert_reqs=` forwarded straight to `redis.ConnectionPool` → `TypeError` at checkout; pool increments `_created_connections` before construction → one leaked slot per op → `MaxConnectionsError` misclassified as transport failure → sticky degraded mode; zero commands ever reached ElastiCache. Fix: `connection_class=SSLConnection`; `BlockingConnectionPool` with bounded `pool_timeout`; boot tripwire.
3. **Dead setting** (`10d7c559`): `create_autom8_cache_provider` hardcoded `max_connections=20`, leaving `settings.cache.redis_max_connections` a zero-consumer dead setting. Fix: wire `ASANA_CACHE_REDIS_MAX_CONNECTIONS`.

Regression (two-sided, real redis-py 7.2.1): `tests/unit/packaging/test_dockerfile_prod_extras.py`, `test_import_failure_announces_degraded_mode_loudly`, `tests/unit/cache/test_backends_with_manager.py` (24-way fan-out vs cap-20 pool). **Defensive pattern**: any prod Docker image building a venv via `uv sync --extra X` MUST be tested against its exact declared extras set; any `redis.ConnectionPool` kwargs MUST select `connection_class` explicitly, never forward TLS kwargs generically.

## SCAR-L2GATE-001 — L2 pre-phase gate vs frame-less cascade provider (P1)

`WarmupOrderingError` on every service start. #192 flagged the frame-less `unit_holder` HOLDER as a cascade provider (OFFER_SCHEMA 1.6.0); the warm-phase planner (`cascade_utils.py:162`) schedules only frame-warmable entities, so `unit_holder` is in NO phase — but the L2 gate demanded the UNFILTERED provider set, making `offer`'s preload structurally unsatisfiable. Fix: `get_frame_warm_providers` (`cascade_utils.py:308`) unifies planner+gate on one predicate; `assert_l2_pre_phase_gate` (`:341`). Test: `tests/unit/dataframes/test_l2_gate_frameless_provider.py` (4 scar markers, two-sided). **Defensive pattern**: any new cascade provider classification must go through `get_frame_warm_providers`, never a second hand-maintained provider list (5th layer of the SCAR-005/006 cascade defense family).

## SCAR-FRESH-001 — freshness-verification-recency silent-corruption (ADR-006, P2)

6 anti-theater sub-cases (T11-T16) in `tests/unit/dataframes/test_freshness_verification_recency.py` (7 scar markers): all-names-null must raise loud `section_name_contract_violation`; content edits register `CONTENT_CHANGED`; stamp gates on `applied_gids`; `name`+`last_verified_at` survive completion; a COMPLETE section with `prior.name=None` re-seeds. Fix: `dataframes/builders/freshness.py`, `progressive.py`. **Defensive pattern**: freshness/staleness stamping MUST fail loud on null-name and re-seed edges, never silent-pass.

## SCAR-AUTHSPECIES-001 — unrecognized JWT species misrouted 500→401 (P1)

A bearer JWT clearing JWKS/signature/expiry but whose claims don't fit `ServiceClaims` (e.g. wrong-typed `scope`) makes `autom8y-auth` raise a pydantic `ValidationError` (a `ValueError`, NOT an `AuthError`), which slipped the except chain in `get_auth_context` and surfaced as a 500. Fix: `api/dependencies.py:215` `except ValidationError` → 401 path; pydantic detail never logged. Test: `tests/unit/auth/test_dependencies.py` (two-sided). **Defensive pattern**: any auth boundary catching an SDK's typed error hierarchy MUST also catch the SDK's own validation-layer exceptions (pydantic `ValidationError`) explicitly.

## SCAR-AUTHSIG-001 (N=3) — fail-clean on S2S mint 401

Before `a8f97c8a` (#264), a revoked/invalid `sa_*` credential erupted from the httpx event-hook as a raw `InvalidServiceKeyError` traceback on the read tools; the composite write receipt mislabeled it "transport error." Fix: `mcp/asana_mcp/bridge.py:48-59` → `McpToolError(kind=auth, status=401, retryable=False, code=S2S_MINT_CREDENTIALS_INVALID)`; message names remediation by env KEY (`CLIENT_ID`/`CLIENT_SECRET`, never values). Test: `mcp/tests/test_bridge_401_fail_clean.py`. Error-opacity lineage → N=3.

## RB-1 Confirm-Before-Firing Gate (defensive-only, NOT a scar)

Operator ruling R5 — automation-triggering writes must "pause for a human yes." `mcp/asana_mcp/tools/confirm_gate.py`: two-phase; Phase 1 (no token) = zero backend calls + `confirmation_required` envelope with single-use TTL-bound (600s) fingerprint token; Phase 2 (token + byte-identical intent) executes; mismatch refuses (zero writes) and burns the token. V1: ALL tags trigger-capable (deliberately unowned). Complementary to the discharged PLAY-3 post-fire confirmation. Test: `mcp/tests/test_confirm_gate_rb1.py`. THROWAWAY/REFERENCE-POSTURE.

## Category Coverage (15 categories, 3 new)

Cache Coherence (6), Data Model/Contract (11), Startup/Deployment (7), Workflow Logic (5), Security/Input Validation (5), Authentication/Error Opacity (4), Concurrency (3), Integration/CI (3), **Cache Backend/Connection Pool (NEW: REDIS-WARMER-001)**, **Freshness Stamping/Silent Corruption (NEW: FRESH-001)**, **Cascade Planner/Gate Coherence (NEW: L2GATE-001)**, Performance Cliff (1), Observability Gap (1), SDK Interface Gap (1), Registry Drift (1), Push Seam/Dead Code (1), Epistemic/Drift (1), Test Infrastructure (1), Build Tooling (1). Explicit absences (unchanged): schema-migration, distributed-coordination, network-partition.

## Scar Test Cluster (46 markers, 17 files)

Top files: `test_section_registry.py` (7, SCAR-REG-001), `test_freshness_verification_recency.py` (7, FRESH-001 NEW), `test_warmup_ordering_guard.py` (5, SCAR-005/006), `test_idempotency_finalize_scar.py` (5, IDEM-001), `test_l2_gate_frameless_provider.py` (4, L2GATE-001 NEW), `test_cascade_ordering_assertion.py` (3), `test_register_drift_guard.py` (3), plus single/double markers across `test_entity_registry.py`, `test_cascade_validator.py`, `test_normalizers.py`, `test_tags_auth_exclusion.py`, `test_exports_auth_exclusion.py` (2), `test_progressive_cascade.py`, `test_exports_format_negotiation.py`, `test_section_timeline_service.py`, `test_universal_strategy_status.py` (2). `--dist=loadgroup` active (`pyproject.toml:118`). New non-marker regression anchors: `mcp/tests/{test_errors_c3.py, test_bridge_401_fail_clean.py, test_confirm_gate_rb1.py}`, `tests/unit/auth/test_dependencies.py`, `tests/unit/packaging/test_dockerfile_prod_extras.py`.

## Agent-Relevance Tagging (new)

| Scar | Roles | Constraint |
|---|---|---|
| SCAR-REDIS-WARMER-001 | platform-engineer, principal-engineer | Prod Docker images tested vs their exact `uv sync --extra` set; redis pool selects `connection_class` explicitly |
| SCAR-L2GATE-001 | principal-engineer, architect | New cascade provider classifications via `get_frame_warm_providers` only |
| SCAR-FRESH-001 | principal-engineer, qa-adversary | Freshness stamping fails loud on null-name/re-seed; keep T11-T16 green |
| SCAR-AUTHSPECIES-001 | principal-engineer, security-reviewer | Auth deps wrapping SDK claims models catch the SDK's own validation exceptions |
| SCAR-AUTHSIG-001 (N=3) | platform-engineer, principal-engineer | Credential-mint failures via httpx hooks → `McpToolError(kind=auth)`, never raw traceback |

18 legacy scars remain untagged (unchanged).

## Knowledge Gaps

- **GLINT-002 cross-domain gap**: documented in conventions.md, no scar-tissue entry despite being scar-shaped (production cold-start failure) — [KNOW-CANDIDATE].
- **SCAR-CW-001 fix-path staleness persists** across two full-regen cycles — `facade.py` actually at `models/business/detection/facade.py`, `discovery.py` at `services/discovery.py`, handlers flat under `lambda_handlers/`. The layer→file re-mapping (UV-P) still not performed.
- **SCAR-CANDIDATE-PLAY-CONSUMED-TRIGGER at N=1** — RB-1 (pre-fire) + PLAY-3 (post-fire) mitigate but don't constitute a 3rd independent recurrence; ≥3 promotion floor unmet.
- **BROAD-CATCH ADVISORY count grew 17→22** with no per-site intentional-vs-defensive audit yet.
