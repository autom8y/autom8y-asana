---
domain: design-constraints
generated_at: "2026-07-23T14:56:44Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./mcp/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "70d45434e1e79ce7bc380936e47a4e265447ffd4db88dc37cd8b37edc70b862f"
confidence: 0.86
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/initiative-history.md"
land_hash: "62e88f60226e924b7fc0298605ce934fc6c36a3b4090ed524a4ef0d3cc4a05ff"
---

# Codebase Design Constraints

> Fresh full refresh at synced HEAD `d0c8b662` (2026-07-23). Re-verified prior anchors against current code. Headline deltas vs the prior 2026-07-20 pass: StorageNamespaceContract fully documented (was absent); TENSION-002 grew 4→5 files; a semgrep layer-coverage gap identified; SCAR cluster 35→93 collected tests; FLEET-SHA-SKEW-001 RESOLVED; M-07 floor still breached; RB-1 gate + fail-clean-401 auth + redis-warmer fixes newly landed.

## Tension Catalog

**TENSION-001: Dual Config System** — `config.py:22-65`, `transport/config_translator.py`. Unchanged. High cost.

**TENSION-002: Services→API Layer Imports — NOW 5 FILES** — `services/intake_create_service.py:23`, `matching_service.py:21`, `intake_resolve_service.py:18`, `intake_custom_field_service.py:16`, **NEW** `services/receipts_service.py:40`. All bare, no `TYPE_CHECKING`/`nosemgrep`. Medium cost.

**TENSION-003: Models→Persistence Import** — `models/task.py:414,417`, `custom_field_accessor.py:421`; `nosemgrep: autom8y.no-models-import-upper` present + correctly spelled. Medium.

**TENSION-004..007** — Lambda-handlers-as-service-overflow; entity GID duplication; autom8y_interop protocol gap; Polars-primary + pandas bridge. Carried forward, not re-verified.

**TENSION-008: Auth→API Import — NOW STRUCTURALLY INVISIBLE TO SEMGREP** — `auth/dual_mode.py:24` (unguarded); `cache/dataframe/decorator.py:147,192,212,247` (function-body, in-scope, live unsuppressed hit). `auth/` is NOT in the semgrep include list (TENSION-014). Fix: move `ApiAuthError` to `core/`.

**TENSION-009: Fleet /v1/query Mount-Order** — `api/main.py:316` (`_assert_fleet_query_mount_order`), called `:517`. Re-verified present.

**TENSION-010: ExportOptions extra="allow"** — `exports.py:150`, P1-C-02 BINDING. **TENSION-011: ExportsSuccessResponse extra="ignore"** — carried. **TENSION-012: UP046/UP047 stale ruff comments** — `pyproject.toml:233-234`, still say `>=3.11` while `:10` is `>=3.12` (3rd consecutive confirmation — permanent low-priority drift).

**TENSION-013: StorageNamespaceContract — 12-Namespace SSOT with Discriminating-Canary Suite [NEW, was undocumented for multiple prior passes]** — `storage_namespace.py` (630 lines, `REGISTRY_NAMESPACE_COUNT=12`), `tests/arch/test_namespace_contract.py` (t1-t5), `test_namespace_gen.py`. The declared SSOT for every autom8-s3 namespace; t3 forbids any S3 prefix literal in `src/` outside it, t2 forbids IAM grants on unregistered namespaces. Minted to dissolve the "triple-defect saga" (phantom cold tier, overloaded `ASANA_CACHE_S3_PREFIX`, IAM drift). Intentional, not debt.

**TENSION-014: Semgrep Layer-Model Coverage Gap [NEW]** — `.semgrep.yml:29-49`. The `no-lower-imports-api` include list covers 19 packages; **6 non-api packages are absent**: `auth/`, `contracts/`, `domain/`, `lambda_handlers/`, `normalizer/`, `reconciliation/`. Any `autom8_asana.api` import from these is invisible to CI. Secondary: two `nosemgrep` comments (`auth/__init__.py:14`, `auth/audit.py:31`) cite the WRONG rule ID (`autom8y.no-lower-imports-api` vs the real `autom8y.asana-no-lower-imports-api`) — dead/misleading (harmless only because `auth/` isn't scanned anyway). Fix: add 6 paths + fix 2 IDs (then triage the `auth/dual_mode.py` hit that surfaces).

**TENSION-015 / MCP-RB1-CONFIRM-GATE-001: MCP Composite-Write Two-Phase Gated [NEW]** — `mcp/asana_mcp/tools/confirm_gate.py` (#263), `composite_write.py:82-118`. Every `add_tag` needs two round-trips (token issue → confirm). Trigger-classification allowlist ownership DELIBERATELY UNASSIGNED (ruling R5) — v1 treats ALL tags trigger-capable. In-process store, restart clears (fails safe).

## Operational Constraints

- **M07-MONITOR-001: M-07 Constraint Coverage — ACTIVE BREACH, UNCHANGED** — `.ci/semantic-baseline.json` M-07 = 0.5714 (4/7, floor 0.6, `pass: false`), `regression_safe: true` (non-blocking). Identical across 3 audit cycles / ~2.5 months. P2.
- **FLEET-SHA-SKEW-001 — RESOLVED** — all 5 security workflows now pin `f5601acbe3905270dfcb9069854c78c0f940ad05` (was 4-of-5 skew). `test.yml` consumes a different pin lineage (`satellite-ci-reusable.yml@c824da59`), never part of the claim.
- **Branch Protection Posture [NEW]** — `main` requires: `gitleaks`, `dependency-review`, `ci / Test (shard 1..4/4)`, `ci / Lint & Type Check`, `ci / Fleet Conformance Gate`, `CodeQL`. `enforce_admins: true`, `required_linear_history: true`, `allow_force_pushes: false`, `allow_deletions: false`, `required_conversation_resolution: false`. `trufflehog`/`zizmor`/`scorecard`/`dockerfile-lint`/`aegis`/`con2-freeze`/`durations-refresh`/`post-merge-coverage`/`nightly-live-smoke`/`satellite-dispatch` run but are NOT required checks (cannot block a merge). **Direct pushes to main are rejected — landing requires a PR + passing required checks.**
- **MCP-BUDGET-PARTITION-001** (`observability.py:265` `validate_partition`, `:179` `BudgetPartitionError`) — re-verified. **MCP-WRITE-FLAG-001** re-anchored: `WRITE_SURFACE_ENV` now `composite_write.py:98`, `write_surface_enabled()` `:102`, `register()` `:458` (grew from RB-1/#249 landings; flag defaults OFF, never persists). **MCP-REFERENCE-POSTURE-001** — probe due 2026-08-03; `mcp/` absent from ALL CI (semgrep/mypy/coverage/test-collection); carries its own `mcp/pyproject.toml`.
- **AUTH-FAIL-CLEAN-VALIDATIONERROR-001 [NEW, ruling R21 Lane-1, #262]** — `api/dependencies.py` new `except ValidationError` in `get_auth_context`: a bearer JWT clearing JWKS/signature/expiry but with claims that don't fit `ServiceClaims` (pydantic `ValidationError`, a `ValueError` not an `AuthError`) previously escaped as a 500; now refused as 401 `INVALID_TOKEN`. Rejection-only; detail not logged.
- HYG-001, RITE-SUBSTRATE-INTEGRITY-001, CI-CONCURRENCY/XDIST/CONSUMER-GATE/PERF-BUDGET — carried forward (no touching commits in range), MODERATE confidence. WORKTREE-001: `.knossos/worktrees/` holds 20+ stale checkouts.

## Trade-off Documentation

- **TRADE-008 / EC-008 (deprecated `POST /v1/query/{entity_type}`) — CORRECTED: REMOVED** — retired in `5e31bb48` (2026-06-24), a full month BEFORE the prior doc's own source_hash. The prior "witness-arc refresh" patched MCP entries but didn't re-verify this pre-existing claim. No longer live.
- **TRADE-012** — `autom8y-core>=4.2.0,<5.0.0` re-verified.
- **TRADE-013: Redis Prod-Image Packaging Single-Line Omission [NEW]** — `Dockerfile:100` built `uv sync … --extra api --extra auth --extra lambda`, omitting `--extra redis`. `RedisCacheProvider` fails open on `ImportError` → silent NO-OP warmer cache. Fixed (`b3da9d8c`, `--extra redis` + loud `cache_degraded_mode` ERROR), guarded by `tests/unit/packaging/test_dockerfile_prod_extras.py` (two-sided).
- TRADE-001..007/009..011 — carried, not re-verified.

## Abstraction Gap Mapping

- **GAP-011: RedisConnectionPool Kwarg-Forwarding Lazy-Fail [NEW]** — `cache/backends/redis.py`. `redis.ConnectionPool(ssl=…, ssl_cert_reqs=…)` accepted kwargs at construction but forwarded them to `Connection.__init__` only at first checkout → `TypeError`, misclassified as transport failure, leaking a pool slot per op until `MaxConnectionsError`. Fix (`bfa4aedb`): select `connection_class=SSLConnection` explicitly; eager boot-time tripwire fails loud on kwarg drift. See LBC-016.
- GAP-001..010 — carried, GAP-002 RESOLVED per prior pass.

## Load-Bearing Code

- **LBC-015: StorageNamespaceContract REGISTRY is a Frozen Gateway [NEW]** — adding a raw S3 prefix in `src/` fails t3; an unregistered IAM grant fails t2; a 13th namespace without registration fails t1. Any new namespace MUST be added to `REGISTRY` (with `WriterOwner`, `Lifecycle`, IAM matrix) first.
- **LBC-016: Redis Pool Boot Tripwire [NEW]** — the eager unconnected-connection construction converts a future kwarg regression from "silent slot leak" to "loud `cache_degraded_mode` at boot." Removing it reintroduces the cured defect.
- **LBC-017: F1a Floor-Gate Now on the Production Warmer Path [NEW]** — `transport/budget_allocator.py`, `dataframes/builders/hierarchy_warmer.py` (`d11ae574`). `WarmerFloorGate.admit`/`observe_admission` now have real call sites (previously inert). Keys on `AWS_LAMBDA_FUNCTION_NAME` so ECS can't accidentally throttle. Per-chunk banking bounds truncation loss to one chunk under the 900s Lambda wall (truncation GUARANTEED for large gap sets).
- LBC-001..014 — carried, LBC-011 mount-order re-confirmed.

## Evolution Constraints

- **EC-008 — REMOVED** (see TRADE-008). **EC-010** — `>=3.12` no upper bound; stale UP046/UP047 comments. **EC-017/018** — `autom8y-core>=4.2.0`, `--dist=loadgroup` re-verified.
- **EC-020: WS-7 Actor-Attribution Seam Constrains Future Cross-Repo Schema [NEW]** — `ADR-ws7-actor-attribution-seam.md` (design-only, VISIONARY/Phase-2 precondition, in the AUTH repo). Any future event-woken (SQS/polling/webhook) write path in THIS repo wanting delegated-human attribution cannot assume a bearer token in the envelope — must plan for a durable delegation-grant reference re-exchanged at action time. No code implements this yet.
- **EC-021: Two ADRs Describe Not-Yet-Implemented Architecture [NEW]** — `ADR-entity-resolution-primitive-2026-07-08.md` (`HierarchyFirstOfficeResolver`) and `ADR-taskcache-projection-coverage-2026-07-08.md` landed via `1a3a3023` as documentation ONLY ("no src/ or tests/ touched"). Direct grep confirms neither symbol exists in `src/` at this HEAD. Aspirational, not current state.
- **EC-013** — telos deadline 2026-05-11 long passed; status not re-verified this pass (likely stale).

## Risk Zone Mapping

- **RISK-013: M-07 floor — active breach, unchanged** (3rd confirmation).
- **RISK-016: `required_conversation_resolution: false` [NEW]** — unresolved PR review threads don't block merge; a blocking comment can be merged past if the reviewer doesn't also withhold approval. Structural gap (not an evidenced incident).
- **RISK-017: 6 Packages Invisible to the API Layer-Violation Rule [NEW]** — see TENSION-014; `auth/dual_mode.py:24` is a live confirmed instance.
- **RISK-018: Redis Cache Degradation Was Silent Pre-Fix [NEW]** — TRADE-013 + GAP-011 stacked two independent root causes for the same NO-OP-warmer symptom (CurrItems=0), neither loud enough to alarm before this pass's fixes. No metric counter exists for this class; a CloudWatch Logs metric filter on `cache_degraded_mode` is recommended (not confirmed provisioned).

## Experiential Observations (from `.sos/land/initiative-history.md`)

- SCAR cluster: prior sessions documented 35/11; direct `pytest -m scar --collect-only` at `d0c8b662` = **93 tests / 17 files** (~2.7x growth, consistent with the high commit volume: redis/warmer, auth fail-clean, MCP RB-1/S2S hardening).
- F1a advisory-floor allocator: was MERGED-INERT + CANARY + LIVE-LEG-PROVEN (2026-07-20), HALTED at operator GO-LIVE; `d11ae574` (2026-07-21) appears to be the GO-LIVE wiring (LBC-017). [KNOW-CANDIDATE?] no explicit operator GO-LIVE record cited this pass.
- MCP write-surface: PT-09 eunomia FLAG-ADVISORY/MODERATE (2026-07-20); this window added RB-1/#263, S2S-401-fail-clean/#264, workflow disclosure/#268 (all post-PT-09). Next disposition: MCP-REFERENCE-POSTURE-001 probe due 2026-08-03.

## Knowledge Gaps

1. EC-013 telos status post-deadline not re-verified (likely stale).
2. The bulk of TRADE-001..007/009..012, GAP-001..010, LBC-001..014, RISK-001..015, EC-001..019 carried forward WITHOUT direct re-inspection (no touching commits in the `f6a72824..d0c8b662` range) — MODERATE confidence, not STRONG.
3. `bridge.py` #264 and `tools/workflows.py` #268 identified via commit log + file existence, not deep-read for constraint extraction.
4. RISK-016 has no evidenced incident (structural-gap observation).
5. `.sos/wip/defer-watch/DEFER-2026-050/051*.md` (gitignored) summarized from the landing commit only.
6. `ADR-entity-resolution-primitive` / `ADR-taskcache-projection-coverage` full content not deep-read beyond the "documentation-only, not implemented" fact.
7. `.knossos/worktrees/` staleness not assessed at file-timestamp granularity.
