---
domain: scar-tissue
generated_at: "2026-10-05T02:59:02Z"
expires_after: "7d"
source_scope:
  - "./src/autom8_asana/__init__.py"
  - "./src/autom8_asana/client.py"
  - "./src/autom8_asana/config.py"
  - "./src/autom8_asana/entrypoint.py"
  - "./src/autom8_asana/errors.py"
  - "./src/autom8_asana/settings.py"
  - "./src/autom8_asana/storage_namespace.py"
  - "./mcp/asana_mcp/__init__.py"
  - "./mcp/asana_mcp/assembly.py"
  - "./mcp/asana_mcp/bridge.py"
  - "./mcp/asana_mcp/context.py"
  - "./mcp/asana_mcp/envelopes.py"
  - "./mcp/asana_mcp/errors.py"
  - "./mcp/asana_mcp/observability.py"
  - "./mcp/asana_mcp/schemas.py"
  - "./mcp/asana_mcp/server.py"
  - "./mcp/asana_mcp/settings.py"
  - "./mcp/asana_mcp/timeouts.py"
  - "./mcp/canary/test_broken_fixture_canary.py"
  - "./mcp/probes/c2_sandbox_reput_probe.py"
  - "./mcp/tests/conftest.py"
  - "./mcp/tests/test_assembly_floor.py"
  - "./mcp/tests/test_bridge_401_fail_clean.py"
  - "./mcp/tests/test_budget_partition_and_rate_cap.py"
  - "./mcp/tests/test_cold_frame_mapping.py"
  - "./mcp/tests/test_composite_write_s3.py"
  - "./mcp/tests/test_confirm_gate_rb1.py"
  - "./mcp/tests/test_discovery_tools.py"
  - "./mcp/tests/test_errors_c3.py"
  - "./mcp/tests/test_errors_passthrough.py"
  - "./mcp/tests/test_errors_substrate_424.py"
  - "./mcp/tests/test_fences.py"
  - "./mcp/tests/test_honesty_passthrough.py"
  - "./mcp/tests/test_import_safety_obs.py"
  - "./mcp/tests/test_import_safety.py"
  - "./mcp/tests/test_instrument_seam.py"
  - "./mcp/tests/test_postures.py"
  - "./mcp/tests/test_query_tools.py"
  - "./mcp/tests/test_readiness_gate.py"
  - "./mcp/tests/test_resolve_tool.py"
  - "./mcp/tests/test_schema_canary.py"
  - "./mcp/tests/test_seam_conformance.py"
  - "./mcp/tests/test_span_and_traceparent.py"
  - "./mcp/tests/test_tag_dual_key_wsb2.py"
  - "./mcp/tests/test_timeout_cascade_invariant.py"
  - "./mcp/tests/test_workflows_disclosure.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "6a8debe2b2650bf405b8e8a3a03e3c969e935410abcd9c5b1c21410fbd76784d"
confidence: 0.88
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
observed_ref: "origin/main@c29f58f4"
land_sources:
  - ".sos/land/scar-tissue.md"
land_hash: "a15a024ce204de3301b612526c5b1b59e4841fa3d3d70f2226e1b430cd73da1e"
---

# Codebase Scar Tissue

> Fresh full regeneration observed at `origin/main` **`c29f58f4`** (1,720 commits; 492 `fix*` subjects, 24 revert-matching subjects; observation date 2026-10-04). Prior version (generated 2026-07-23) is a delta-only document (the 831-line catalog at `b0cb45f0` was collapsed to ~100 lines by `c5c71c02`/#269), so this pass **re-assembles the full catalog** — legacy IDs preserved verbatim from `b0cb45f0` and re-verified against the worktree — and appends **17 new scars** from commits 2026-07-23..2026-10-02 plus 3 status corrections to legacy entries. `@pytest.mark.scar`: **46 markers / 17 files** (unchanged vs prior; grep-confirmed). Code markers on main: `SCAR-` 23 src + 2 mcp + 58 tests lines; `DEF-NNN` 16 src; `CRITICAL` 18 src; `BROAD-CATCH` 207 src lines (see Knowledge Gaps); `FIXME`/`HACK`/`WORKAROUND` 0.

## 1. Status Dashboard (what changed in meaning, not just in count)

| Item | Prior claim | Verified at `c29f58f4` |
|---|---|---|
| SCAR-SD02 (status push dead code) | "PENDING-MERGE(C-6), no fix on main" | **RESOLVED on main** — `1be1a8e6` (#215, 2026-07-08): `AccountStatusPushLoop` started at `api/lifespan.py:384-390`, stopped `:431-435`. Successor failures now tracked in SCAR-STATUSPUSH-001 below |
| SCAR-CW-001 CP-01 regression anchor | "`test_import_safety.py` NOT YET AUTHORED" | **EXISTS** — `tests/unit/lambda_handlers/test_import_safety.py` (`44b935fc` 2026-06-01, `3017a7fc`, `ff74d9ea`); asserts `universal_strategy` import calls no `get_settings()`. Prior "absent" claim was stale across ≥3 cycles |
| SCAR-DISCRIMINATOR-001 | unguarded at `query/models.py:102` | **Still unguarded**, site moved to `query/models.py:136-152` (`isinstance(v, dict)` branch only; model-instance falls through to `"comparison"` at `:152`). No fix commit |
| SCAR-AUTHSPECIES-001 anchor | `api/dependencies.py:215` | moved → `api/dependencies.py:240` (`except ValidationError`) |
| SCAR-L2GATE-001 anchors | `cascade_utils.py:308/:341` | moved → `get_frame_warm_providers` `:325`, `assert_l2_pre_phase_gate` `:362` |
| SCAR-W1E-LOADGROUP-001 | `pyproject.toml:105`, `test_routes_query.py` marker | `--dist=loadgroup` now `pyproject.toml:124` (rationale comment `:122`); `test_routes_query.py` was split — `xdist_group("query_routes")` now in `tests/unit/api/test_routes_query_section_missing_selector_guard.py:43` and `test_routes_query_body_parameterized_unregistered.py:44`; new `worker_isolated` marker (`pyproject.toml:131`) quarantines `test_workflow_handler_auth_injection.py:50` / `..._dataframe_cache_init.py:58` from the sharded run |
| SCAR-WS8 | `api/main.py:389` | `exclude_paths=list(DEFAULT_EXCLUDE_PATHS)` at `api/main.py:454`, scar comment `:471` |
| SCAR-029 (GID strip) | `webhooks.py:375-381` | moved → `api/routes/webhooks.py:465-471` |
| SCAR-IDEM-001 | `idempotency.py:762-830` | finalize read at `:763`; metric/500 path intact (`:787-830`) — no regression |
| SCAR-ALARM-BINDING-001 cure | "staged on branch `fix/al5-alarm-actions-staging`, not applied" | **MERGED to main** `eb9dfc09` (#341, 2026-08-11): `terraform/services/asana/observability_alarms.tf:100` (`ticket_sns_topic_arn`), `:144` (`require_alarm_binding`), `:192` (resolution), `:668-671` (AL-5 precondition), `alarm_binding_report` output `:115`. Whether `terraform apply` ran is **not observable from the repo** (operator-gated) |
| SCAR-LOG-001 | `autom8y-log>=0.5.6`, no shim | `pyproject.toml:24` now `autom8y-log>=0.7.0,<1.0.0`; whether 0.7.x ships a stdlib shim is **unverified** (UV-P); `import logging` remains in 1 src file; no `SCAR-LOG-001` code marker in src |
| Env-var typo scar | `AUTOM8Y_DATA_API_KEY` at `clients/data/config.py:231` | confirmed `config.py:231` |

## 2. Failure Catalog (all IDs; evidence sources = git history + code markers + tests)

Legend: **Fix** = commit or "Historical (no sha in any retained catalog; marker/test evidence only)". Locations are re-verified on main unless marked `[carry]` (carried from prior catalog, not re-verified this pass).

### 2a. Legacy catalog (IDs preserved)

| SCAR ID | Failure | Category | Fix / current location |
|---|---|---|---|
| SCAR-001 | Entity/holder class missing `PRIMARY_PROJECT_GID` — silent resolution collision | Entity Resolution | Historical `[carry]`; registry validation `core/entity_registry.py:1242` (DEF-02 syntax check) |
| SCAR-002 | Section persistence race: `in_progress_since` timeout not enforced | Concurrency | Historical `[carry]` |
| SCAR-003 | Stale S3 cache served after data change | Cache Coherence | Historical `[carry]` |
| SCAR-004 | DEF-005 origin: warm-up and request path used separate `CacheProvider` instances | Cache Coherence | `af10d98e`; guard sites `api/lifespan.py:158,176`, `api/client_pool.py:201`, `query/engine.py:305,634,752`, `services/intake_task_handlers.py:27,198` |
| SCAR-005 | `CascadingFieldResolver` 30% null on units — warm-up ordering violated | Cache Coherence | multiple cascade commits; 29 `SCAR-005` refs across src/tests; `dataframes/cascade_utils.py:27,372,422`, `builders/progressive.py:193,1025`, `core/entity_registry.py:359`, `builders/cascade_validator.py:30`; tests `test_warmup_ordering_guard.py` (5 markers), `test_cascade_ordering_assertion.py` (3) |
| SCAR-006 | Cascade hierarchy warming gaps — parent GID not stored | Cache Coherence | `088fe332`, `4d652720`; see also SCAR-CASCADE-HIER-001 (same wound, 404 flavour) |
| SCAR-007 | S3 build_result schema-version drift — stale parquet deserialization failures | Cache Coherence | Historical `[carry]`; `dataframes/storage.py` carries `schema_version` metadata (`:135,:976,:1107`) |
| SCAR-008 | DEF-001 origin: `SaveSession` cleared snapshot before accessor reset | Data Model | `persistence/session.py:995` ("DEF-001 FIX: clear accessor BEFORE capturing snapshot") |
| SCAR-009 | Tests missing `ASANA_WORKSPACE_GID` — sync auto-detect in wrong context | Startup | Historical `[carry]` |
| SCAR-010 / 010b | Session state mutation race; `_require_open()` bypass | Concurrency | `persistence/session.py:439,517,547` (`with self._require_open()`) |
| SCAR-011 / 011b | ECS health-check/startup dependency gated on wrong endpoint (`/health` vs `/ready`) | Startup | Historical; `/ready` readiness probe `api/routes/health.py:8` (cache-warmth 200/503); fleet TG fix = SCAR-TG-LIVENESS-001 |
| SCAR-012 | Cross-service client using PAT instead of `client_credentials` | Authentication | Historical `[carry]` |
| SCAR-013 | Optional SDK imported without `try/except ImportError` | Startup | Historical `[carry]`; the mirror failure (ImportError swallowed → NO-OP) is SCAR-REDIS-WARMER-001 layer 1 |
| SCAR-014 | Lifecycle config models `extra="forbid"` broke forward-compat | Data Model | `fe6bc978` |
| SCAR-015 | Timeline endpoint 504 at ~3,800 offers (per-request Asana I/O > ALB 60s) | Performance Cliff | `b85a604a`; compute-on-read-then-cache `services/section_timeline_service.py:7-10`; scale regression `tests/unit/services/test_section_timeline_service.py:723` |
| SCAR-016/017/018/019 | Workflow logic gaps | Workflow Logic | Historical `[carry]` — **not individually described in any retained source** (gap) |
| SCAR-020 | `PhoneNormalizer` only in matching engine, not read path | Workflow Logic | `09163c06`; `NumberParseException` now caught `models/business/matching/normalizers.py:80` (CANDIDATE-B `0f18f4e8`); test `tests/unit/models/business/matching/test_normalizers.py:66` |
| SCAR-021 | CI integration failure | Integration / CI | Historical `[carry]` (undescribed) |
| SCAR-022 | `uv sync --frozen` incompatible with `--no-sources` (uv ≥0.15.4) | Startup | `2229f4a3` |
| SCAR-023 | Offer `office` column `source=None` bypassed cascade — 30-40% null | Data Model | `09163c06` |
| SCAR-024 / 025 | Phone-field / data-model contract gaps | Data Model | Historical `[carry]` (undescribed) |
| SCAR-026 | SDK-client test mocks lacking `spec=` — silent drift | Integration / CI | `2158de02`, `3f4580ff` (partial HYG-002) |
| SCAR-027 | User string in `re.sub` replacement — backref injection/ReDoS | Security | `core/creation.py:82-92` (lambda replacement) |
| SCAR-028 | Error log emitted user PII unmasked | Security | `clients/data/_pii.py:21` (`mask_phone_number`), `:45`; marker `automation/workflows/leads_skip.py:9` |
| SCAR-029 | GID not stripped before Pydantic normalization | Security | `api/routes/webhooks.py:465-471` |
| SCAR-030 | Section names from non-live source — ALL CAPS invariant | Data Model | Historical `[carry]` |
| SCAR-S3-LOOP | Permanent S3 error codes fed to retry loop → storm | Cache Coherence | `core/retry.py:198` (`_PERMANENT_S3_ERROR_CODES`, incl. `NoSuchKey` `:200`); classification `:180,:252` |
| SCAR-IDEM-001 | Idempotency `finalize()` failure swallowed — double-exec on retry | Data Model (RESOLVED) | `f795d7dc` #149; `api/middleware/idempotency.py:751-830`; tests `test_idempotency_finalize_scar.py` (5 markers) |
| SCAR-REG-001 | Section-registry GIDs fabricated placeholders | Startup (RESOLVED) | `2d7d39d9` #190; `reconciliation/section_registry.py:375` `SectionRegistryError`, gate `:403-429`; `test_section_registry.py` (7 markers); 18 refs repo-wide (src ref `api/routes/projects.py:397`) |
| SCAR-WS8 | PAT route trees missing from JWT `exclude_paths` | Security | `api/main.py:454,471`; tests `test_tags_auth_exclusion.py`, `test_exports_auth_exclusion.py` (2) |
| SCAR-DISCRIMINATOR-001 | `NotGroup(not_=AndGroup(...))` fails via model-instance construction | Data Model / Type Contract | **OPEN** `query/models.py:136-152` (dict-only guard); P3, no prod caller; workaround raw dict; helper `_wrap_flat_array_to_and_group` `:155` |
| SCAR-LOG-001 | `autom8y-log` structlog family ≠ stdlib `Logger` | SDK Interface Gap | See §1; ruff TID251 per-file ignores `pyproject.toml:259-298`; defer-watch `DEFER-WS4-T3-2026-04-29` |
| SCAR-LP-001 | lockfile-propagator stub-before-`uv lock` ordering | Build Tooling | autom8y PR #174 `f2dfc1c3` (out-of-repo) |
| SCAR-P6-001 | Stale-checkout drift recurs at plan-authoring altitude | Epistemic / Drift | VERDICT §5 (out-of-repo); **note: this very pass is the 3rd+ instance of the class** — the session checkout is 89 commits behind main (see Knowledge Gaps) |
| SCAR-CW-001 | Cache-warmer Lambda cold-start, 5 onion layers (Errno 97 → 111 → URL over-encoding → init-time settings → registry ARN) | Startup / Lambda | PRs #28-#37; settings lazy-resolution `models/business/detection/facade.py:70-82`; **CP-01 test now exists** `tests/unit/lambda_handlers/test_import_safety.py`; `services/universal_strategy.py:60` marker |
| SCAR-W1E-LOADGROUP-001 | xdist `--dist=load` AsyncMock teardown corrupts across workers | Test Infrastructure | `149d3673`; see §1 for moved sites |
| SCAR-CONSUMER-GATE-001 | `candidate_wheel_run_id` set but artifact download silently fails | Integration / CI | `8980bcd7`; `.github/workflows/test.yml:245-257` ("Verify candidate wheel present") |
| SCAR-ARTIPACKED-001 | `actions:read` + checkout `persist-credentials` default leaks extraheader into artifacts | Security | `8980bcd7`; `test.yml:157-160` (`persist-credentials: false`) |
| Env-var typo | `AUTOM8_DATA_API_KEY` (missing Y) → prod auth failures | Authentication | `clients/data/config.py:231` |
| CSI-001 | openapi.json hand-edited; regen dropped examples | Doc / Spec Drift (DISCHARGED) | T-08 `4d4097c3`, PR #38 `80256049`; residual singular `"example":` `api/routes/dataframes.py:511,632` (not regressions) |
| SCAR-SD02 | Status push dead code in prod (entity-warm lane paused) | Push Seam (RESOLVED, extended) | `1be1a8e6` #215; `api/lifespan.py:384-390`; successors → SCAR-STATUSPUSH-001 |
| SCAR-VOCAB-PARITY-001 | Introspection advertised process_* pipelines that execution rejected (3rd dyn-enum strike) | Registry Drift (CURED) | `2eb830ca` #245; descriptor-driven `services/resolver.py:246,354-357`; guard `tests/unit/services/test_entity_vocabulary_parity.py` |
| SCAR-AUTHSIG-001 (N=3) | `sa_*` mint failures misread as expired creds; SDK flattened diagnosable bodies; raw `InvalidServiceKeyError` traceback | Auth / Error Opacity | `a8f97c8a` #264; `mcp/asana_mcp/bridge.py:42-59` → `McpToolError(kind=auth,status=401,code=S2S_MINT_CREDENTIALS_INVALID)`; `mcp/asana_mcp/errors.py`; tests `mcp/tests/test_bridge_401_fail_clean.py`, `test_errors_c3.py` |
| SCAR-TG-LIVENESS-001 | ALB TG health-checked liveness `/health` → traffic shifted to cold tasks | Startup / Deployment (CURED) | fleet autom8y #1157 `d502398d`, #1154 `e8079654`, a8 #104 `80402fd3`; satellite `6edc83d5` (#248) four-state `/ready` (`api/routes/health.py:8`) |

### 2b. Scars catalogued in the 2026-07-23 pass (re-verified)

| SCAR ID | Failure | Category | Fix / location (main) |
|---|---|---|---|
| SCAR-REDIS-WARMER-001 (P1) | 3-layer dead-cache: prod Dockerfile omitted `--extra redis`; `ssl=` kwargs leaked into `redis.ConnectionPool` (leaked slots → `MaxConnectionsError`); `max_connections=20` hardcoded, dead setting | Cache Backend / Pool | `b3da9d8c`, `bfa4aedb`, `10d7c559` (2026-07-21..22); test `tests/unit/packaging/test_dockerfile_prod_extras.py` (exists), `tests/unit/cache/test_backends_with_manager.py` |
| SCAR-L2GATE-001 (P1) | `WarmupOrderingError` on every start: L2 gate demanded unfiltered provider set incl. frame-less `unit_holder` | Cascade Planner/Gate | #192; `dataframes/cascade_utils.py:325` `get_frame_warm_providers`, `:362` `assert_l2_pre_phase_gate`; `tests/unit/dataframes/test_l2_gate_frameless_provider.py` (4 markers) |
| SCAR-FRESH-001 (P2) | freshness-verification-recency silent corruption (ADR-006, T11-T16) | Freshness / Silent Corruption | `dataframes/builders/freshness.py`, `progressive.py`; `tests/unit/dataframes/test_freshness_verification_recency.py` (7 markers); code markers `metrics/__main__.py:788`, `dataframes/offline.py:39` |
| SCAR-SEAM1-PROBER-001 (P1) | `SectionFreshnessProber` entity-blind → v2/legacy plane split; `active_mrr` 14-day-stale under "verified 1m ago" | Freshness / Plane Split | `bdbf86cb` #276 (2026-07-27); `builders/freshness.py:158-178` (`entity_type` threaded), `dataframes/offline.py:54` `PlaneDivergenceError`, `:150-221` `_resolve_section_keys`; tests `test_offline_entity_aware_read.py`, `test_seam1_callsite_inventory.py`; `.ledge/reviews/DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27.md`. **No `SCAR-SEAM1` string exists in code** — the scar is findable only by `SEAM-1`/`PlaneDivergenceError` |
| SCAR-AUTHSPECIES-001 (P1) | Unrecognized JWT species (pydantic `ValidationError`, a `ValueError`) slipped except chain → 500 | Auth / Error Opacity | `b79ae3cc` #262; `api/dependencies.py:240`; `tests/unit/auth/test_dependencies.py` |
| SCAR-ALARM-BINDING-001 (N=4 now) | Detection-to-notification chain unbound: alarm exists, tells no one | Observability Gap | see §3 |
| RB-1 confirm gate (defensive-only) | pre-fire human "yes" for automation-triggering writes | n/a | `8e77c9a0` #263; `mcp/asana_mcp/tools/confirm_gate.py:49` (`DEFAULT_CONFIRMATION_TTL_S = 600.0`), `:78` `intent_fingerprint`; `mcp/tests/test_confirm_gate_rb1.py` |

### 2c. NEW scars since 2026-07-23 (appended; IDs new)

| SCAR ID | Failure | Category | Fix commit | Current location / regression test |
|---|---|---|---|---|
| SCAR-CASCADE-HIER-001 (P1) | One deleted (404) ancestor zeroed the whole contact-hierarchy warm → contact `office_phone` 96.7% null → `/v1/resolve/business-by-email` 503 on every call; cure unclearable because gate denominator included 62% parentless rows | Cascade / Cache Coherence | `55e69d78` #386, `56375c5b` #387, `a1b046a9` #389 (2026-08-19..22) | tolerant set `dataframes/builders/hierarchy_warmer.py:56-79` (404/410/403 per-fetch), `cache/providers/unified.py:44-65`, `cache/integration/hierarchy_warmer.py:32,92`; denominator `dataframes/builders/cascade_validator.py:199` `CascadeDenominatorCollapsedError`, raise `:724`; tests `tests/unit/dataframes/builders/test_hierarchy_gap_warm_ancestor_fault.py`, `tests/unit/cache/test_ancestor_permanent_fault.py`, `test_cascade_denominator_rescope.py` |
| SCAR-MANIFEST-TOMBSTONE-001 (P1) | Sections deleted in Asana lingered in manifest; probes 404 every cycle, never stamped → `min(last_verified_at)` pinned (2026-08-26 offers stall); `OFFER_CLASSIFIER` still named 19 deleted sections → verification axis refused | Freshness / Silent Corruption | `3c851253` #395, `e9c68636` #396 (2026-08-27) | `dataframes/section_persistence.py:181` `SectionManifest.prune_absent_sections` (fence: empty live set prunes nothing `:220`), `reconcile_manifest_sections_async`; call site `builders/progressive.py:348-352`; `models/business/activity.py:181` (roster follows board); tests `test_manifest_tombstone_reconciliation.py` (520 lines), `tests/unit/models/business/test_activity.py` |
| SCAR-FRESHCLOCK-001 (P1, class N=4) | **Synthetic-fresh generators**: a freshness reading anchored on something other than data age — (i) preload put stamped boot `now()` (`41f1fa80` #339); (ii) `ProgressiveTier` substituted `now()` for a null watermark (`2601c8c5` #338); (iii) empty sections never stamped on hash-CLEAN, pinning the floor (`5d62d0b8` #299, FIX-1); (iv) status-push loop phase anchored to process boot (`53f1abb2`) | Freshness / Silent Corruption | see left | (i) `cache/integration/dataframe_cache.py:812,839,911` (`created_at` kwarg, default-preserving) + `api/preload/progressive.py:646-665`, test `tests/unit/api/preload/test_fixn_c1_preload_stamp_honesty.py`; (ii) `cache/dataframe/tiers/progressive.py:64` `NULL_WATERMARK_DECAY_ANCHOR = datetime.min`, test `tests/unit/cache/dataframe/test_fixn_b_null_watermark_decay.py`; (iii) `builders/progressive.py:553-575` coherence clause (rows==0 AND gid_hash==hash(∅)), `.ledge/reviews/DEFECT-delta-path-empty-poison-2026-08-03.md`; (iv) `api/status_push.py:61-122` `seconds_until_next_fire`, `tests/unit/api/test_status_push_anchor.py` |
| SCAR-CFWRITE-001 (P1, "200 and writes NOTHING") | `TasksClient.update` builds `json={"data": kwargs}`; passing `data={...}` double-nests → Asana returns 200, writes nothing; HTTP status cannot discriminate. Office-phone stamp, vertical/social/address CFs, process assignee silent no-ops since baseline; also nested `{"gid": opt}` enum READ shape on WRITE path | Data Model / Contract | `f6adecbb` #327, `e043a939` #328, `d3c4e3fe` #330 (2026-08-09..10) | `services/intake_create_service.py:384,676,750,792` (`custom_fields=`), `services/intake_custom_field_service.py:130`; **transport-seam tests** (mock `_http.put`, real marshaling): `tests/unit/api/routes/test_intake_create.py:1684,1757,1780`, `test_intake_custom_fields.py:452` and pre-cure red-form `:570`. Lesson: prior tests stubbed `update_async` wholesale and asserted the same buggy kwarg |
| SCAR-RESOLVE-REGISTRY-001 | `/v1/resolve/business` probed `("office_phone","vertical")` but registry keys business on `office_phone` alone → frozenset miss on every request since `36db3ae6`; unit-fallback returned a UNIT gid as business_gid; fresh unit not a member of Business Units project so Vertical CF write silent no-op | Registry Drift | `ddc4bd0b` #325, `69f33d42` #332 (2026-08-08..10) | `services/intake_resolve_service.py:107-131` (key columns read from registry descriptor, refuse loudly if unsuppliable); tests `tests/unit/services/test_intake_resolve_business_index.py`, `test_br3_unit_vertical_carry.py` |
| SCAR-F9-TRISTATE-001 | Resolve producer stamped `has_unit`/`has_contact_holder` as asserted `false` on ordinary index lag → consumer tripwire read written(True)≠read(False) → unattended revert | Data Model / Contract | `e3aab8d4` #382 (2026-08-19) | `services/intake_resolve_service.py:87` `SubtaskObservationError`; route 503 `SUBTASK_OBSERVATION_FAILED` `api/routes/intake_resolve.py:188`; `tests/unit/api/routes/test_intake_resolve_f9_semantics.py` |
| SCAR-POLARS-INFER-001 | Bare `pl.DataFrame(rows)` inference: a Utf8 column null for >`infer_schema_length` rows then a late string → Null builder `ComputeError` (first live parity sweep died exit 30; PROV digest re-derivation same class) | Data Model / Contract | `dbd46378` #313 (2026-08-05), `39830565` #351 (2026-08-12); `3d0b91f9` #318 (population floor must evaluate classifier-active rows) | `substrate/live.py:73,721-724` (`safe_dataframe_construct(rows, OFFER_SCHEMA)`); `substrate/prov_sweep.py:75-80` (value columns only); tests `tests/unit/substrate/test_prov_sweep.py`, `test_live.py`; `.ledge/reviews/DEFECT-prov-digest-bare-inference-2026-08-12.md` |
| SCAR-WARM-DEADLINE-001 (P1) | Warmer 429 retry loops slept into the 900s Lambda wall (24.6% of invocations SIGKILL'd; drove ~68% of ASR aborts, `OfferFrameAgeSeconds` sawtooth); offer frame deferred past key budget | Performance Cliff | `bc620e18` #312 (2026-08-05) | `core/warm_deadline.py:82` `WarmDeadlineExceeded(BaseException)` (deliberately not swallowable by BROAD-CATCH, `:33`); funnel `transport/asana_http.py:34,802`; tests `tests/unit/core/test_warm_deadline.py`, `tests/unit/lambda_handlers/test_cache_warmer_deadline_yield.py`, `test_project_registry_freshness_priority.py` |
| SCAR-WARM-STARVE-001 | Piggyback story warmer's time budget exhausted inside first 4 cascade entities; `offer` (#5) got 0 of 4,192 tasks warmed across 324+ runs / 14 days | Performance Cliff | `43d766f6` #369 (2026-08-14) | `lambda_handlers/story_warmer.py:57-71` (`DEFAULT_STORY_WARM_PRIORITY_ENTITIES=("offer",)`, env override), per-entity `story_warm_entity_complete` receipt incl. explicit zeros; `tests/unit/lambda_handlers/test_story_warm_priority_offer.py`. Tier-2 fleet redesign explicitly NOT done |
| SCAR-TEMPORAL-IMPUTED-001 | Imputed interval (`story_count==0`) satisfied non-empty transition filters → false "moved over the weekend" positives | Data Model / Contract | `49cf12ca` #360 (2026-08-13) | `query/temporal.py:62-76` guard; `models/business/section_timeline.py` (`imputed`, `ImputationSummary`); tests `tests/unit/api/test_imputation_discriminator.py`, `tests/unit/query/test_temporal.py` |
| SCAR-STATUSPUSH-001 (extends SD02) | After SD02 gave the push a live home: (a) loop fired on boot-anchored phase so ~half of boot instants left ASR's freshness window (`53f1abb2`); (b) ECS runtime has only service-account creds, no legacy key → every push built a snapshot then **skipped** (`3cd2bf85` #507, 2026-10-02; pyjwt floor `pyproject.toml:53`) | Push Seam / Auth | as left | `services/gid_push.py:187-223,315` (`ServiceTokenMintError`; half-configured SA never falls back to legacy key); sync mint offloaded via `to_thread` (concurrency allowlist sanctioned in same PR) |
| SCAR-R7-001 | R7 traffic-vs-offer divergence tripwire: canary tenant's reserved phone `+15550000000` absent from offer roster by construction → +1 `TradingWithoutActiveOfferCount` forever; also passed on a dead traffic leg / 403 baseline | Observability Gap | `f8bd78c9` #326, `61a8f01d` | `lambda_handlers/traffic_offer_divergence_tripwire.py:271,276` (single clause carried by BOTH legs); `tests/unit/lambda_handlers/test_traffic_offer_divergence_tripwire.py`, `..._residuals.py` |
| SCAR-BUDGET-LEDGER-001 | S8-2 parity budget ledger fail-open: corrupt JSON silently reset day to 0; load→check→write unlocked (lost-update overshoot); `units>1` could overshoot | Concurrency | `1276b732` #301 (2026-08-03) | `tests/harness/substrate_gate/budget.py` (`BudgetLedgerCorrupt`, `fcntl.flock`), `test_budget.py` (harness-side only; no `src/` change) |
| SCAR-CI-DISPATCH-001 | (a) docs-only pushes to main redeployed prod (`05fac7c1` 2026-09-05 → blue/green swap paged two alarms; 12 of last 40 main commits same shape) `6c3ed718` #411; (b) `workflow_dispatch` and push runs shared a concurrency group and cancelled each other (PUB-001; "silent half" = undeployed merge) `408cbc37` #458; (c) `workflow_run` dispatch trusted any successful Test run → restricted to push-to-main, sha whole-string regex `31eeaff0` #491 | Integration / CI | listed | `.github/workflows/test.yml` (paths-ignore deny-list), `.github/workflows/satellite-dispatch.yml`; no automated test (workflow-level) |
| SCAR-SEC-001 | Any holder of a valid fleet service JWT could drive any Asana write route (shared bot PAT); `require_service_claims` authenticated but did not authorize; `client_id` dropped before routes | Security | `54431c18` #391 (2026-08-24) | `api/write_authz.py` (deny-by-default, issuer-asserted principal), `api/routes/internal.py:39-47` (claims carried); coverage guard `tests/unit/api/test_write_authz_coverage.py`. **Allowlist population is operator state, not repo state** — empty allowlists under ENFORCE would deny every S2S write (unverified here) |
| SCAR-TASKCACHE-PHE-001 | TASK cache key opt_fields-blind: a narrower first read poisons later wider reads (floodgates `office_phone` None; resume preflight `section=None`) — green tests / red live | Cache Coherence | `79285c78` #217 (2026-07-08, PHE) | `clients/tasks.py:202-229,275-276` (hit gated on `stored_projection` coverage; miss fetches superset); tests `tests/unit/cache/test_coverage_predicate.py`, `test_writer_projection_census.py`; defect docs `.ledge/reviews/DEFECT-floodgates-optfields-blind-cache-poisoning-2026-07-07.md`, `DEFECT-taskcache-cross-reader-section-starvation-2026-07-08.md` (status `proposed` in doc, but code fix present). Companion unverified: `ASANA_CACHE_*` env knobs not binding on default `AsanaClient()` |
| SCAR-METRICS-SELECT-FILTER-001 (**OPEN**) | `compute_metric` selects columns first then applies `filter_expr` → 6 of 9 registered metrics raise `ColumnNotFoundError` even on a full frame | Data Model / Contract | none | `metrics/compute.py:81-107` (select `:97` precedes filter `:107`); `.ledge/reviews/DEFECT-metrics-select-before-filter-2026-08-12.md`; no `compute.py` commit since 2026-04-13 (`git log`); no regression test found |
| SCAR-VACUOUS-PASS-001 (instrument class; docs-only evidence) | A "pass" computed over an empty/short population: `all()` over empty alarm set = True; JMESPath `--query length()` per page undercounts; `\| limit N` hit returns short set | Observability / Instrument Honesty | `afd22b38` #469, `7858b7df` #465 (2026-09-15/16) | `.ledge/reviews/SOAK-read-the-name-s1-2026-09-14.md` (§2, §3c) — cure is cardinality-before-grading; no src/test anchor (procedure fix). Same family as SCAR-ALARM-BINDING-001 sub-mechanism (b) |

Also on record, low severity: `71e07f17` #490 (anyio CVE-2026-63374 → floor `pyproject.toml:13`); `3696358a` #495 gitleaks pin; `fc4d95f6` #410 storage anchor `:342→:347` (`storage_namespace.py:288`, namespace registry drift).

## 3. SCAR-ALARM-BINDING-001 (N=5) — binding-blind alarm class (P1, satellite-local)

Mechanism: the detection-to-notification chain is silently unbound — the alarm *appears* configured, may even detect, but tells no one, or reads OK for the wrong reason. Sub-mechanisms: (a) **action-binding empty** (`AlarmActions=[]`); (b) **signal-binding wrong/vacuous** (alarm reads OK while the guarded thing fails). Occurrences (promoted 2026-08-11 under the scar-tissue-promotion discipline; occurrences 1-4 carried from the prior pass, marked `[carry]` where evidence lives outside the repo):

1. AL-5 `asana-AL5-offer-frame-stale-1143843662099250` authored with `Actions=[]` at inception (2026-07-13) — `.ledge/reviews/STATE-OF-PLAY.md` `[carry]`.
2. `autom8-asana-unit-reconciliation` errors-alarm read OK while the lambda errored 3/3 (signal-binding blind) — monorepo SPIKE `[carry]`; **CONTESTED** later the same day (alarm read ALARM with 1 action).
3. AL-5 in unobserved ALARM 2026-08-09T23:40Z → 2026-08-11 (34h); root `ticket_sns_topic_arn` default `""` → `al5_actions == []` — now `terraform/services/asana/observability_alarms.tf:100,192`.
4. Systemic: 7 of 20 live `asana-*` alarms zero actions, all authored by `terraform/services/asana/`; 13 authored elsewhere bound (measured live 2026-08-11 per `eb9dfc09` message).
5. **NEW** — three stratum source-health series (`SchedulingStratumSnapshotDegenerateSource`/`...Refused`/`...SchemaLag`) published `1` on fault and NOTHING otherwise, with `treat_missing_data=notBreaching`; every healthy tick was "OK by the missing-data rule", byte-identical to a dead emitter or revoked `PutMetricData`. Cure `55f81e0b` #334: real 0 every tick (template: `SchedulingStratumSnapshotPushFailed`); companion `b90d6a5a` (alarm-bindable producer health metrics).

**Cure status on main**: structural surface landed `eb9dfc09` #341 — `ticket_topic_arn` resolution (`observability_alarms.tf:192`), always-on `alarm_binding_report` output (`:115`), opt-in `require_alarm_binding` precondition (`:144`, enforced for AL-5 at `:668-671`). **Default remains non-enforcing** (`require_alarm_binding` default false), so the class is detectable, not unconstructable. Apply state is operator-gated and not observable from the repo. The 2026-09-15 triage `.ledge/` commit `18ec8f81` ("four muted SEV1 deadmen on the asana surface") is further evidence the class persists operationally `[commit subject only, body not read]`.

**Defensive pattern**: an alarm is not DONE at resource creation — DoD includes one receipted end-to-end fire (signal → alarm → action → human surface). Any `*_sns_topic_arn`-style variable defaulting `""` is a staged-dark alarm needing an activation note. A fire-only metric (publishes only on fault) MUST be paired with a real-0 companion on every healthy tick. Every errors-alarm must be teeth-proven against a real induced error.

**Elevation watch (defer)**: promote to fleet-canonical only if an instance appears OUTSIDE the asana satellite (requires rite-disjoint attester). Occurrence 5 is still inside the satellite.

## 4. Category Coverage (grouped by failure mode; each row counts catalog entries in §2)

| Category | Count | Entries | Absence / thinness note |
|---|---|---|---|
| Cache Coherence | 7 | 003, 004, 005, 006, 007, S3-LOOP, TASKCACHE-PHE-001 | — |
| Cache Backend / Connection Pool | 1 | REDIS-WARMER-001 | only 1 observed |
| Cascade Planner / Gate | 2 | L2GATE-001, CASCADE-HIER-001 | — |
| Freshness / Silent Corruption | 5 | FRESH-001, SEAM1-PROBER-001, FRESHCLOCK-001 (N=4 sub-sites), MANIFEST-TOMBSTONE-001, VACUOUS-PASS-001 (instrument) | densest area since 2026-07 |
| Data Model / Contract | 13 | 008, 014, 023, 024, 025, 030, IDEM-001, DISCRIMINATOR-001, CFWRITE-001, F9-TRISTATE-001, POLARS-INFER-001, TEMPORAL-IMPUTED-001, METRICS-SELECT-FILTER-001 | 2 open (DISCRIMINATOR, METRICS-SELECT-FILTER) |
| Registry Drift | 2 | VOCAB-PARITY-001, RESOLVE-REGISTRY-001 | same shape: hand-enumerated list drifts from registry |
| Startup / Deployment | 8 | 009, 011, 011b, 013, 022, REG-001, CW-001, TG-LIVENESS-001 | — |
| Concurrency | 4 | 002, 010, 010b, BUDGET-LEDGER-001 | — |
| Security / Input Validation | 7 | 027, 028, 029, WS8, ARTIPACKED-001, SEC-001, anyio CVE | — |
| Authentication / Error Opacity | 5 | 012, Env-var typo, AUTHSIG-001, AUTHSPECIES-001, STATUSPUSH-001(b) | — |
| Workflow Logic | 5 | 016-019 (undescribed), 020 | 016-019 undescribed |
| Integration / CI | 4 | 021, 026, CONSUMER-GATE-001, CI-DISPATCH-001 | — |
| Performance Cliff | 3 | 015, WARM-DEADLINE-001, WARM-STARVE-001 | — |
| Observability Gap | 2 | ALARM-BINDING-001 (N=5), R7-001 | — |
| Push Seam | 2 | SD02 (resolved), STATUSPUSH-001 | — |
| Single-instance: SDK Interface Gap (LOG-001), Build Tooling (LP-001), Epistemic/Drift (P6-001), Test Infrastructure (W1E-LOADGROUP-001), Doc/Spec Drift (CSI-001), Entity Resolution (001) | 1 each | | "only 1 observed" |

**Searched, not found (explicit absences)**: schema-migration failures, distributed-coordination/lock-service bugs, network-partition handling — no `fix`/marker evidence on main (grep over `src/` markers + `git log --grep` subjects). **Not searched**: `terraform/` beyond `observability_alarms.tf`, `.github/workflows/` beyond `test.yml`/`satellite-dispatch.yml`, `docs/`, `runbooks/`.

**Systemic recurrences (≥3, per radar-recurring-scars)**: (1) **error/measurement opacity** — AUTHSIG (N=3), ALARM-BINDING (N=5), VACUOUS-PASS, R7, F9 (asserted-false-from-lag): "a well-formed answer to a narrower question than the one asked"; (2) **freshness-clock lies** — FRESHCLOCK (N=4), SEAM1, MANIFEST-TOMBSTONE, FRESH-001; (3) **hand-enumerated list drifting from a registry/descriptor** — VOCAB-PARITY, RESOLVE-REGISTRY, L2GATE (second provider list), OFFER_CLASSIFIER roster (MANIFEST-TOMBSTONE); (4) **silent no-op masquerading as success** — CFWRITE (HTTP 200, zero write), REDIS-WARMER layer 1 (NO-OP cache), STATUSPUSH (skip), AL-5; (5) **cascade wound at N parent-chain sites** — SCAR-005/006, CASCADE-HIER, L2GATE.

## 5. Fix-Location Mapping notes

- **Broken/moved links found this pass** (all re-pointed in §1/§2): `api/dependencies.py:215→240`; `cascade_utils.py:308/341→325/362`; `pyproject.toml:105/118→124`; `webhooks.py:375→465`; `query/models.py:97-112→136-152`; `test_routes_query.py` (file split); `api/main.py:389→454`.
- **SCAR-CW-001 layer→file mapping now resolvable**: detection facade at `models/business/detection/facade.py:70-82` (lazy `_detection_cache_ttl`), discovery at `services/discovery.py`, handlers flat under `lambda_handlers/` (cache_warmer.py, cache_invalidate.py, story_warmer.py …). Layers 1-3 (network/Dockerfile/SDK) have no in-repo code anchor.
- **Findable-only-by-other-name scars**: SEAM1 (no `SCAR-SEAM1` in code); FRESH-001 marker at `metrics/__main__.py:788`/`dataframes/offline.py:39`; REDIS-WARMER, CASCADE-HIER, CFWRITE, MANIFEST-TOMBSTONE have **no `SCAR-` marker in src or `@pytest.mark.scar` in tests** (their tests exist but run outside `pytest -m scar`). Recommend marker backfill (see Gaps).
- **Compound fixes**: CASCADE-HIER = 3 fetch sites (`dataframes/builders/hierarchy_warmer.py`, `cache/providers/unified.py`, `cache/integration/hierarchy_warmer.py`) + denominator (`cascade_validator.py`); FRESHCLOCK = 4 sites listed in §2c; CW-001 = 5 layers.

## 6. Defensive Pattern Documentation (scar → guard → test)

| Scar | Guard (location) | Regression test | Gap |
|---|---|---|---|
| 005/006/023, L2GATE | `cascade_utils.py` provider predicate; `builders/cascade_validator.py:30`; `api/preload/progressive.py:851` (must NEVER be caught by BROAD-CATCH) | `test_warmup_ordering_guard.py` (5), `test_cascade_ordering_assertion.py` (3), `test_l2_gate_frameless_provider.py` (4) | — |
| 008 | accessor-clear-before-snapshot `session.py:995` | none marked scar | **no scar-marked test** |
| 010/010b | `_require_open()` `session.py:439/517/547` | none marked scar | **no scar-marked test** |
| 020/NumberParse | `normalizers.py:80` | `test_normalizers.py:66` (1 marker) | — |
| 027/029 | lambda replacement `creation.py:85`; strip `webhooks.py:465-471` | none marked | **no scar-marked test** |
| 028 | `_pii.py:21,45` | none scar-marked (only the `automation/workflows/leads_skip.py:9` comment marker) | **no scar-marked test** |
| S3-LOOP | `retry.py:198-200,252` | none marked | **no scar-marked test** |
| IDEM-001 | `idempotency.py:763-830` | `test_idempotency_finalize_scar.py` (5) + drift guard `tests/unit/knowledge/register_drift_checks.py:36` (`RESOLVED_SCAR_IDS={REG-001, IDEM-001}`; blocks open-status wording beside resolved IDs) | VOCAB-PARITY/TG-LIVENESS/SD02 resolved but **not added to `RESOLVED_SCAR_IDS`** |
| REG-001 | `section_registry.py:375-429` fail-closed | `test_section_registry.py` (7), `test_register_drift_guard.py` (3) | — |
| WS8 | `api/main.py:454,471` | `test_exports_auth_exclusion.py` (2), `test_tags_auth_exclusion.py` (1) | — |
| W1E | `pyproject.toml:122-124`; `worker_isolated` marker `:131`; CI quarantine job `test.yml:291` | n/a (infra) | — |
| CONSUMER-GATE / ARTIPACKED | `test.yml:245-257`, `:157-160` | none (workflow) | no workflow test |
| REDIS-WARMER | `--extra redis` Dockerfile; `connection_class=SSLConnection`; boot tripwire | `test_dockerfile_prod_extras.py`, `test_backends_with_manager.py` | no scar marker |
| FRESH/SEAM1/FRESHCLOCK | fail-loud `PlaneDivergenceError` (`offline.py:54`); `created_at` anchor; decay anchor `progressive.py:64` | `test_freshness_verification_recency.py` (7), `test_offline_entity_aware_read.py`, `test_seam1_callsite_inventory.py`, `test_fixn_c1_*`, `test_fixn_b_*` | only FRESH-001 file is scar-marked |
| CASCADE-HIER | per-fetch tolerance + per-chunk isolation + fail-CLOSED denominator | 3 test files (§2c) | no scar marker |
| CFWRITE | transport-seam tests assert real marshaled body | `test_intake_create.py:1684+`, `test_intake_custom_fields.py:452,570` | other `TasksClient.update(data=…)` callers not swept (UV-P) |
| AUTHSPECIES / AUTHSIG / RB-1 | `dependencies.py:240`; `bridge.py:48-59`; `confirm_gate.py` | `tests/unit/auth/test_dependencies.py`; `mcp/tests/test_bridge_401_fail_clean.py`, `test_errors_c3.py`, `test_confirm_gate_rb1.py`; `mcp/canary/test_broken_fixture_canary.py` (`6dfd2cca`, wired `test.yml`) | — |
| DISCRIMINATOR-001, METRICS-SELECT-FILTER-001 | **none (open)** | **none** | open scars, unguarded |
| ALARM-BINDING | TF precondition `observability_alarms.tf:668-671`, binding report | none (IaC) | default non-enforcing |

**BROAD-CATCH**: 207 `BROAD-CATCH` comment lines in `src/` (22 in `tests/`) on main; the prior "ADVISORY count 22" counted a different population (likely lint advisories) and is not comparable — still no per-site intentional-vs-defensive audit. `WarmDeadlineExceeded(BaseException)` (`core/warm_deadline.py:82`) and `CancelledError` handling in `idempotency.py` are the deliberate exceptions.

## 7. Scar Test Cluster (46 markers, 17 files — grep-confirmed)

`test_section_registry.py` 7 (REG-001) · `test_freshness_verification_recency.py` 7 (FRESH-001) · `test_warmup_ordering_guard.py` 5 · `test_idempotency_finalize_scar.py` 5 · `test_l2_gate_frameless_provider.py` 4 · `test_cascade_ordering_assertion.py` 3 · `tests/unit/knowledge/test_register_drift_guard.py` 3 (+1 in `register_drift_checks.py`) · `test_exports_auth_exclusion.py` 2 · `test_universal_strategy_status.py` 2 · singles: `test_entity_registry.py`, `test_cascade_validator.py`, `test_normalizers.py`, `test_tags_auth_exclusion.py`, `test_exports_format_negotiation.py`, `test_progressive_cascade.py`, `test_section_timeline_service.py`. **Not** in the 46: all 17 scars of §2c, which are guarded by unmarked tests — `pytest -m scar` therefore under-reports regression coverage of post-July scars. MCP-island suite (`mcp/tests/`, 27 files) + discriminating canary (`mcp/canary/`) wired in CI by `6dfd2cca`. `--dist=loadgroup` active `pyproject.toml:124`.

## 8. Agent-Relevance Tagging

| Scar | Roles | Why (constraint) |
|---|---|---|
| 005/006/023, L2GATE, CASCADE-HIER | principal-engineer, architect | New cascade provider/entity goes through `get_frame_warm_providers`; any parent-chain fetch site tolerates 404/410/403 per-GID; gate denominators scoped in-frame (never join-mediated) |
| REDIS-WARMER | platform-engineer, principal-engineer | Test the prod image against its exact `uv sync --extra` set; pick `connection_class` explicitly for TLS |
| FRESH-001, SEAM1, FRESHCLOCK, MANIFEST-TOMBSTONE | principal-engineer, seam-engineer, qa-adversary | Every S3-writing builder threads `entity_type`; never synthesize `now()` for an unknown watermark; stale/absent plane fails loud; deleted sections are pruned by live-listing membership |
| CFWRITE | principal-engineer, qa-adversary | Never pass `data=` to `TasksClient.update`; test at the transport seam, not by stubbing `update_async` |
| RESOLVE-REGISTRY, VOCAB-PARITY | principal-engineer | Derive key columns/vocabulary from the registry descriptor, never a literal |
| F9-TRISTATE, TEMPORAL-IMPUTED, VACUOUS-PASS | principal-engineer, qa-adversary | An absence of evidence must not serialize as an asserted false; a pass over an empty set is not a pass |
| POLARS-INFER | principal-engineer | Build frames with `safe_dataframe_construct(rows, SCHEMA)`; never bare `pl.DataFrame(rows)` on sparse columns |
| WARM-DEADLINE, WARM-STARVE | platform-engineer, sre | Warm loops must yield to the Lambda deadline; budget-bound warmers need per-entity zero receipts and priority ordering |
| ALARM-BINDING, R7 | observability-engineer, platform-engineer | One receipted end-to-end fire per alarm; real-0 companions for fire-only series; sentinel exclusion carried by both legs |
| AUTHSIG, AUTHSPECIES, SEC-001, STATUSPUSH | security-reviewer, principal-engineer | Catch SDK validation-layer exceptions; remediation names env KEYS never values; write routes need the deny-by-default gate; SA configured ⇒ no silent fallback to legacy key |
| CI-DISPATCH, CONSUMER-GATE, ARTIPACKED | platform-engineer, releaser | Deploy triggers must be push-to-main only, path-filtered by deny-list, with per-dispatch concurrency groups |
| SCAR-001..030 legacy (undescribed 016-019, 021, 024, 025) | platform-wide / historical-only | No retained rationale; treat as historical until re-derived |
| TASKCACHE-PHE | principal-engineer | Cache hits must be projection-covering; new `opt_fields` consumers go through the coverage predicate |
| BUDGET-LEDGER | qa-adversary, platform-engineer | Budget/ledger code fails closed on corrupt state and locks across processes |

## 9. Experiential Observations (`.sos/land/scar-tissue.md`, generated 2026-04-28, dionysus; 10 sessions)

Verified against code: (a) `AUTOM8_DATA_API_KEY` typo cured → `clients/data/config.py:231` reads `AUTOM8Y_DATA_API_KEY` ✔; (b) CascadingFieldResolver 30%/30-40% null (cascade + Offer `office` source=None) → SCAR-005/023, extended by CASCADE-HIER-001 ✔; (c) xdist worker crashes in `test_workflow_handler.py` → SCAR-W1E-LOADGROUP-001 + `worker_isolated` quarantine (`pyproject.toml:131`, `test.yml:291`) ✔ — the experiential "root-cause not yet attributed" is **superseded**; (d) metrics CLI under-count (22 expected vs ~6 in parquet) → the 4 open questions are explained by SCAR-SEAM1-PROBER-001 plane split (prior pass), though the *bucket-mapping/freshness-SLA* questions are not independently re-verified; (e) `PhoneNormalizer` read-path → SCAR-020 ✔. Unverified (attributed as experiential only): `EntityWriteRequest` lacking `extra="forbid"` (class at `api/routes/entity_write.py:63`; config not read); UnicodeEncodeError in middleware (ASCII-sanitization present at `transport/asana_http.py:280` and `api/middleware/core.py:147`, consistent with a cure; Schemathesis pass-rate 5%→66% claim not verifiable); consumer-gate 900s→2400s timeout (autom8y repo); `asana-test-rationalization` 33 inviolable scar tests (marker count now 46). Land-source friction themes (cascade null rate, test-suite scale, stale-cache observability) remain the top recurring clusters and are consistent with §4 systemic recurrences. Land data is 5+ months old relative to this pass and contains no post-April scars.

## Knowledge Gaps

### Changes since prior version (2026-07-23 → `c29f58f4`)

1. **17 new scars appended** (§2c); ALARM-BINDING-001 N=3→5; STATUSPUSH-001 extends SD02.
2. **Status corrections**: SD02 resolved (`1be1a8e6`), CW-001 CP-01 test exists, ALARM-BINDING cure merged (`eb9dfc09`), TASKCACHE defect docs marked `proposed` but code fix merged (`79285c78`); DISCRIMINATOR-001 unchanged/open.
3. **Anchor drift** (11 locations, §1). No fix was found regressed; all legacy resolved scars (IDEM-001, REG-001, VOCAB-PARITY, TG-LIVENESS, AUTHSIG) intact.
4. **Structure correction**: the prior `.know/scar-tissue.md` was delta-only (93-116 lines) and dropped the 41-row legacy catalog, category counts "15 categories", and the "18 legacy scars untagged" arithmetic; this version restores a complete table. Prior category counts (e.g., "Data Model 11") are superseded by §4 (grouping differs).
5. Prior "marker count 41→46" retained as correct (46/17).

### Open gaps

- **Session-checkout staleness (SCAR-P6-001 recurrence)**: the session checkout is on a feature branch 89 commits behind `c29f58f4`; this document was built only from the detached worktree. Any consumer reading the session checkout will see SD02 as "pending", DISCRIMINATOR line numbers wrong, etc.
- **Marker debt**: 17 new scars carry no `SCAR-` string in `src/` and no `@pytest.mark.scar`; `pytest -m scar` and `radar-unguarded-scars` will undercount. Only SEAM1/FRESH have discoverable markers; `RESOLVED_SCAR_IDS` (`register_drift_checks.py:36`) guards only 2 of ≥5 resolved scars.
- **Open, unguarded**: SCAR-DISCRIMINATOR-001 (P3), SCAR-METRICS-SELECT-FILTER-001 (HIGH latent: 6/9 metrics; no compute.py change since 2026-04-13).
- **Legacy descriptions missing** for SCAR-001/002/003/007/009/012/016-019/021/024/025/030 — "Historical" with no sha in any retained catalog; a `git log -S` archaeology pass was not done (time-boxed).
- **Operator-state scars not repo-verifiable**: AL-5/alarm apply status; SEC-001 allowlist population; whether autom8y-log 0.7.x ships a stdlib shim (SCAR-LOG-001); SCAR-CFWRITE sweep of remaining `TasksClient.update(data=…)` callers.
- **GLINT-002 (config-during-init cold-start)** is documented in conventions.md but has no scar entry — scar-shaped; [KNOW-CANDIDATE] cross-domain.
- **SCAR-CANDIDATE-PLAY-CONSUMED-TRIGGER** (marker `mcp/asana_mcp/tools/workflows.py:20`) and **SCAR-CANDIDATE-OPTFIELDS** remain candidates at N=1; OPTFIELDS now has a corroborating second site class (TASKCACHE-PHE-001 is the same opt_fields-projection family in a different layer) — promotion review warranted [KNOW-CANDIDATE?].
- **Evidence limits**: `.ledge/` read-the-name docs (VACUOUS-PASS-001, 18ec8f81 triage) were sampled from commit bodies, not fully read; several fix commit bodies were read only in the first 15-30 lines.
