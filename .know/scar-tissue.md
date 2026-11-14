---
domain: scar-tissue
generated_at: "2026-11-14T18:06:21Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "gitidx-v1:5a15438a45d829aa10eb9e8b5c92b387fa17dfd228b999cba199073a9191b1e9"
source_commit: "584c8f79b5f7d0087a28a982a3ed4290cb98647d"
evidence_hash: "gitidx-v1:c8c695a3549b771ae18474dfae112eaceb71c9b46b5220ef4df1c6aab3e96155"
anchor_source: "stamp-pin"
stamp: {pin_id: "d55b30ac3e8e8159", pin_commit: "584c8f79b5f7d0087a28a982a3ed4290cb98647d", body_sha256: "a3fbd34ddfe70eff5e6167fa9a6f5e9218b2b2194dbbb8081cf5bf63b14f5a74"}
confidence: 0.84
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
observed_ref: "origin/main@584c8f79"
land_sources:
  - ".sos/land/scar-tissue.md"
land_hash: "a15a024ce204de3301b612526c5b1b59e4841fa3d3d70f2226e1b430cd73da1e"
---

# Codebase Scar Tissue

> Observed at `origin/main@584c8f79` (detached worktree; 1,752 commits by `git rev-list --count HEAD`; observation date 2026-11-14). Git evidence: 503 commits whose subject starts `fix` or `hotfix` (`git log -i -E --grep='^(fix|hotfix)'`), 25 commits whose message matches `revert` of which 3 are genuine reverts (`b9cf6dbc`, `a609762a`, `fe6bc978`), 122 matching `regress|hotfix`. Of the 32 commits since the prior pass (`c29f58f4..HEAD`), 9 have a `fix` subject and all 32 were read by subject; the 9 fixes plus 8 CI/security/refactor commits were read by body and diffstat. Code markers were counted by a stdlib AST-free text walk of the tracked `src/`, `mcp/`, `tests/`, `terraform/`, `.github/` files plus `pyproject.toml` and the Semgrep config (manifest `filtered-ls.txt`): `@pytest.mark.scar` 46 uses in 17 files (unchanged), `SCAR-` lines 25 `src/` + 2 `mcp/` + 59 `tests/` + 3 `terraform/` + 1 `.github/` + 1 `pyproject.toml`; `DEF-0` 15 `src/` lines; `CRITICAL` 18 `src/` lines; `BROAD-CATCH` 216 `src/` + 22 `tests/` lines; `FIXME`/`HACK`/`WORKAROUND` 0. Legacy scar IDs from the prior pass are preserved verbatim; no ID is retired. Every fix-location line number below was re-derived at `584c8f79`; entries marked `[carry]` have no in-repo anchor and are carried from earlier catalogs. All paths are relative to the repo root.

## Failure Catalog Completeness

### 1. What changed in meaning since `c29f58f4` (status dashboard)

| Item | Prior claim | Verified at `584c8f79` |
|---|---|---|
| SCAR-METRICS-SELECT-FILTER-001 | **OPEN**, "no regression test found", 6 of 9 metrics raise on a full frame | **RESOLVED** by `c9891cf6` (#512, 2026-10-05, a `fix` that landed one commit after the prior pass's base). `src/autom8_asana/metrics/compute.py:99-107` now carries filter-referenced columns (`extra_cols` from `fe.meta.root_names()`) through `df.select`, filters at `:116-125`, then drops them (`:128`). In-code marker `src/autom8_asana/metrics/compute.py:99`. Regression test `tests/unit/metrics/test_compute_filter_columns.py` (4 targeted cases at `:36,:48,:53,:68`, plus `test_every_registered_metric_computes` at `:106` which runs all registered metrics). The `.ledge/reviews/DEFECT-metrics-select-before-filter-2026-08-12.md` record is now stale on status |
| SCAR-IDEM-001 | guard live on the default path | **Guard dormant by default.** `df867da3` (#535) set `DEFAULT_IDEMPOTENCY_BACKEND = "noop"` (`src/autom8_asana/api/main.py:90`); the finalize-failure guard (`src/autom8_asana/api/middleware/idempotency.py:751-775`) only runs under an opted-in `dynamodb` or `memory` backend. See SCAR-IDEM-DEFAULT-001 |
| SCAR-DISCRIMINATOR-001 | open, `src/autom8_asana/query/models.py:136-152` | **Still open, unguarded.** `_predicate_discriminator` at `src/autom8_asana/query/models.py:136`; dict-only branch `:141-149`; fall-through `return "comparison"` `:151`; helper `_wrap_flat_array_to_and_group` `:154`. Last commits touching the file (`412376f4`, `a87ae1ca`, `ae9701ca`) are all earlier than the prior pass; no fix commit |
| SCAR-WS8 | `src/autom8_asana/api/main.py:454`, comment `:471` | moved: `exclude_paths=list(DEFAULT_EXCLUDE_PATHS)` `src/autom8_asana/api/main.py:461`, scar comment `:478` |
| SCAR-W1E-LOADGROUP-001 | `pyproject.toml:124`, marker `:131` | `--dist=loadgroup` `pyproject.toml:125` (rationale `:123`); `worker_isolated` marker `:132`; CI quarantine job `.github/workflows/test.yml:308`, single-process run `:389-402`, shard exclusion `:134-137` |
| SCAR-CONSUMER-GATE-001 / SCAR-ARTIPACKED-001 | `.github/workflows/test.yml:245-257` / `:157-160` | `.github/workflows/test.yml:262` (step "Verify candidate wheel present (consumer-gate fail-loud)"); `persist-credentials: false` at `.github/workflows/test.yml:176` (rationale `:173`), repeated `:332,:425,:472,:540` and in `.github/workflows/merge-surface-sweep.yml:28`, `.github/workflows/nightly-live-smoke.yml:107`, `.github/workflows/semgrep-layer-rules.yml:34` |
| SCAR-SD02 / STATUSPUSH | `src/autom8_asana/api/lifespan.py:384-390` | `AccountStatusPushLoop` constructed `src/autom8_asana/api/lifespan.py:388`, started `:389`, stopped `:431-435`; `seconds_until_next_fire` `src/autom8_asana/api/status_push.py:114` (moved from `:61-122`); `ServiceTokenMintError` `src/autom8_asana/services/gid_push.py:223` (moved from `:187-223`) |
| SCAR-LOG-001 | `autom8y-log>=0.7.0` | unchanged `pyproject.toml:24`; the comment there says 0.7.0 exports `sanitize_log_extra()`; stdlib-shim status still unverified |
| `RESOLVED_SCAR_IDS` drift guard | 2 IDs | still `{SCAR-REG-001, SCAR-IDEM-001}` at `tests/unit/knowledge/register_drift_checks.py:36`; the newly resolved SCAR-METRICS-SELECT-FILTER-001 is not added |

### 2. Legacy catalog (IDs preserved; anchors re-verified at `584c8f79` unless `[carry]`)

| SCAR ID | Failure | Category | Fix / current location |
|---|---|---|---|
| SCAR-001 | Entity/holder class missing `PRIMARY_PROJECT_GID`: silent resolution collision | Entity Resolution | Historical `[carry]`; registry validation `src/autom8_asana/core/entity_registry.py` (DEF-02 syntax check, line not re-derived) |
| SCAR-002 | Section persistence race: `in_progress_since` timeout not enforced | Concurrency | Historical `[carry]` |
| SCAR-003 | Stale S3 cache served after data change | Cache Coherence | Historical `[carry]` |
| SCAR-004 | DEF-005 origin: warm-up and request path used separate `CacheProvider` instances | Cache Coherence | `af10d98e`; guard sites listed in the prior pass (`src/autom8_asana/api/lifespan.py`, `src/autom8_asana/api/client_pool.py`, `src/autom8_asana/query/engine.py`, `src/autom8_asana/services/intake_task_handlers.py`) not re-derived this pass |
| SCAR-005 | `CascadingFieldResolver` 30% null on units: warm-up ordering violated | Cache Coherence | multiple cascade commits; 15 `SCAR-005` lines in `src/` (e.g. `src/autom8_asana/dataframes/cascade_utils.py:27,372,422`, `src/autom8_asana/dataframes/builders/progressive.py:193,1025`, `src/autom8_asana/core/entity_registry.py:359`, `src/autom8_asana/dataframes/builders/cascade_validator.py:30`) and 14 in `tests/`; tests `tests/unit/dataframes/test_warmup_ordering_guard.py` (5 markers), `tests/unit/dataframes/test_cascade_ordering_assertion.py` (3) |
| SCAR-006 | Cascade hierarchy warming gaps: parent GID not stored | Cache Coherence | `088fe332`, `4d652720`; same wound as SCAR-CASCADE-HIER-001 (404 flavor); `SCAR-005/006` joint citations at `src/autom8_asana/api/preload/progressive.py:851` (must never be caught by BROAD-CATCH), `src/autom8_asana/services/universal_strategy.py:458,504,515` |
| SCAR-007 | S3 build_result schema-version drift: stale parquet deserialization failures | Cache Coherence | Historical `[carry]`; `schema_version` metadata in `src/autom8_asana/dataframes/storage.py` not re-derived |
| SCAR-008 | DEF-001 origin: `SaveSession` cleared snapshot before accessor reset | Data Model | `src/autom8_asana/persistence/session.py:995` ("DEF-001 FIX: Order matters - clear accessor BEFORE capturing snapshot") |
| SCAR-009 | Tests missing `ASANA_WORKSPACE_GID`: sync auto-detect in wrong context | Startup | Historical `[carry]` |
| SCAR-010 / 010b | Session state mutation race; `_require_open()` bypass | Concurrency | `with self._require_open()` at `src/autom8_asana/persistence/session.py:439,517,547` (also `:1370,:1445,:1560,:1647,:1711`); definition `:1703` |
| SCAR-011 / 011b | ECS health-check/startup dependency gated on wrong endpoint (`/health` vs `/ready`) | Startup | Historical; readiness probe `src/autom8_asana/api/routes/health.py` (`readiness_check` `:423`, now rate-limit-exempt and JWKS-cached, see SCAR-PROBE-429-001); fleet TG fix = SCAR-TG-LIVENESS-001 |
| SCAR-012 | Cross-service client using PAT instead of `client_credentials` | Authentication | Historical `[carry]` |
| SCAR-013 | Optional SDK imported without `try/except ImportError` | Startup | Historical `[carry]`; mirror failure (ImportError swallowed to NO-OP) is SCAR-REDIS-WARMER-001 layer 1 |
| SCAR-014 | Lifecycle config models `extra="forbid"` broke forward-compat | Data Model | `fe6bc978` (2026-03-12, a genuine revert) |
| SCAR-015 | Timeline endpoint 504 at ~3,800 offers (per-request Asana I/O exceeded the ALB 60 s) | Performance Cliff | `b85a604a`; compute-on-read-then-cache `src/autom8_asana/services/section_timeline_service.py:7-10`; scale regression `tests/unit/services/test_section_timeline_service.py:723-818` (4,000 offers must compute in under 5 s, asserted `:745`); also cited as the design reason in `terraform/services/asana/observability_alarms.tf:349,509` (per-GID dead-man alarms) |
| SCAR-016/017/018/019 | Workflow logic gaps | Workflow Logic | Historical `[carry]`; not individually described in any retained source (gap) |
| SCAR-020 | `PhoneNormalizer` only in matching engine, not read path | Workflow Logic | `09163c06`; `NumberParseException` caught `src/autom8_asana/models/business/matching/normalizers.py:80`; test `tests/unit/models/business/matching/test_normalizers.py` (1 marker) |
| SCAR-021 | CI integration failure | Integration / CI | Historical `[carry]` (undescribed) |
| SCAR-022 | `uv sync --frozen` incompatible with `--no-sources` (uv 0.15.4+) | Startup | `2229f4a3` |
| SCAR-023 | Offer `office` column `source=None` bypassed cascade: 30-40% null | Data Model | `09163c06` |
| SCAR-024 / 025 | Phone-field / data-model contract gaps | Data Model | Historical `[carry]` (undescribed); possibly related to SCAR-PHONE-TYPE-001 below `[INFERRED]`, not evidenced |
| SCAR-026 | SDK-client test mocks lacking `spec=`: silent drift | Integration / CI | `2158de02`, `3f4580ff` (partial HYG-002) |
| SCAR-027 | User string in `re.sub` replacement: backref injection / ReDoS | Security | `src/autom8_asana/core/creation.py:83,93` (lambda replacement) |
| SCAR-028 | Error log emitted user PII unmasked | Security | `src/autom8_asana/clients/data/_pii.py:21` (`mask_phone_number`), `:45` (`mask_canonical_key`); marker `src/autom8_asana/automation/workflows/leads_skip.py:9` |
| SCAR-029 | GID not stripped before Pydantic normalization | Security | `src/autom8_asana/api/routes/webhooks.py:465-471` |
| SCAR-030 | Section names from non-live source: ALL CAPS invariant | Data Model | Historical `[carry]` |
| SCAR-S3-LOOP | Permanent S3 error codes fed to retry loop: storm | Cache Coherence | `src/autom8_asana/core/retry.py:198` (`_PERMANENT_S3_ERROR_CODES`), consumed `:267` |
| SCAR-IDEM-001 | Idempotency `finalize()` failure swallowed: double-exec on retry | Data Model (RESOLVED; dormant by default) | `f795d7dc` #149; `src/autom8_asana/api/middleware/idempotency.py:751-775`; tests `tests/unit/api/middleware/test_idempotency_finalize_scar.py` (5 markers); RUF100 exemption note `pyproject.toml:492`, workflow note `.github/workflows/test.yml:488` |
| SCAR-REG-001 | Section-registry GIDs fabricated placeholders | Startup (RESOLVED) | `2d7d39d9` #190; `src/autom8_asana/reconciliation/section_registry.py:375` (`SectionRegistryError`), raise `:429`; `tests/unit/reconciliation/test_section_registry.py` (7 markers) |
| SCAR-WS8 | PAT route trees missing from JWT `exclude_paths` | Security | `src/autom8_asana/api/main.py:461,478`; tests `tests/unit/api/test_tags_auth_exclusion.py` (1), `tests/unit/api/test_exports_auth_exclusion.py` (2) |
| SCAR-DISCRIMINATOR-001 | `NotGroup(not_=AndGroup(...))` fails via model-instance construction | Data Model / Type Contract | **OPEN**: `src/autom8_asana/query/models.py:136-153`; P3, no production caller; workaround is a raw dict; no guard, no test |
| SCAR-LOG-001 | `autom8y-log` structlog family differs from stdlib `Logger` | SDK Interface Gap | `pyproject.toml:24`; ruff TID251 per-file ignores in `pyproject.toml`; defer-watch `DEFER-WS4-T3-2026-04-29` |
| SCAR-LP-001 | lockfile-propagator stub-before-`uv lock` ordering | Build Tooling | out-of-repo (autom8y PR #174 `f2dfc1c3`) |
| SCAR-P6-001 | Stale-checkout drift recurs at plan-authoring altitude | Epistemic / Drift | out-of-repo VERDICT; recurs again this pass (see Knowledge Gaps) |
| SCAR-CW-001 | Cache-warmer Lambda cold-start, 5 onion layers | Startup / Lambda | PRs #28-#37; markers `src/autom8_asana/services/universal_strategy.py:60` (CP-01), `src/autom8_asana/services/business_by_email_service.py:79`; CP-01 regression `tests/unit/lambda_handlers/test_import_safety.py:1-53` (asserts `get_settings` is not called on import) |
| SCAR-W1E-LOADGROUP-001 | xdist `--dist=load` AsyncMock teardown corrupts across workers | Test Infrastructure | `149d3673`; see dashboard for sites |
| SCAR-CONSUMER-GATE-001 | `candidate_wheel_run_id` set but artifact download silently fails | Integration / CI | `8980bcd7`; `.github/workflows/test.yml:262` |
| SCAR-ARTIPACKED-001 | checkout `persist-credentials` default leaks extraheader into artifacts | Security | `8980bcd7`; `.github/workflows/test.yml:173-176` |
| Env-var typo | `AUTOM8_DATA_API_KEY` (missing Y) caused prod auth failures | Authentication | `src/autom8_asana/clients/data/config.py:231` (not re-read this pass; prior pass confirmed) |
| CSI-001 | openapi.json hand-edited; regen dropped examples | Doc / Spec Drift (DISCHARGED) | T-08 `4d4097c3`, PR #38 `80256049`; see also SCAR-TC002-FWDREF-001 as an OpenAPI-regeneration relative |
| SCAR-SD02 | Status push dead code in prod | Push Seam (RESOLVED) | `1be1a8e6` #215 |
| SCAR-VOCAB-PARITY-001 | Introspection advertised pipelines that execution rejected | Registry Drift (CURED) | `2eb830ca` #245; guard `tests/unit/services/test_entity_vocabulary_parity.py` |
| SCAR-AUTHSIG-001 (N=3) | `sa_*` mint failures misread as expired credentials; SDK flattened bodies | Auth / Error Opacity | `a8f97c8a` #264; `mcp/asana_mcp/bridge.py:27` (`_classify_mint_failure`), `:49` (`McpToolError`); tests `mcp/tests/test_bridge_401_fail_clean.py`, `mcp/tests/test_errors_c3.py` |
| SCAR-TG-LIVENESS-001 | ALB target group health-checked liveness `/health`: traffic shifted to cold tasks | Startup / Deployment (CURED) | fleet autom8y #1157, #1154, a8 #104; satellite `6edc83d5` (#248) four-state `/ready` |

### 3. Cataloged 2026-07-23 pass (anchors re-derived)

| SCAR ID | Failure | Category | Fix / location at `584c8f79` |
|---|---|---|---|
| SCAR-REDIS-WARMER-001 (P1) | 3-layer dead cache: prod Dockerfile omitted `--extra redis`; `ssl=` kwargs leaked into `redis.ConnectionPool`; hardcoded `max_connections=20` | Cache Backend / Pool | `b3da9d8c`, `bfa4aedb`, `10d7c559`; tests `tests/unit/packaging/test_dockerfile_prod_extras.py`, `tests/unit/cache/test_backends_with_manager.py` |
| SCAR-L2GATE-001 (P1) | `WarmupOrderingError` on every start: gate demanded unfiltered provider set incl. frame-less `unit_holder` | Cascade Planner / Gate | #192; `src/autom8_asana/dataframes/cascade_utils.py:325` (`get_frame_warm_providers`), `:362` (`assert_l2_pre_phase_gate`); `tests/unit/dataframes/test_l2_gate_frameless_provider.py` (4 markers) |
| SCAR-FRESH-001 (P2) | freshness-verification-recency silent corruption | Freshness / Silent Corruption | `src/autom8_asana/dataframes/builders/freshness.py`; markers `src/autom8_asana/metrics/__main__.py:789`, `src/autom8_asana/dataframes/offline.py:39`; `tests/unit/dataframes/test_freshness_verification_recency.py` (7 markers) |
| SCAR-SEAM1-PROBER-001 (P1) | `SectionFreshnessProber` entity-blind: v2/legacy plane split | Freshness / Plane Split | `bdbf86cb` #276; `src/autom8_asana/dataframes/builders/freshness.py:158` (`entity_type` threaded; explanation `:167-173`), `src/autom8_asana/dataframes/offline.py:54` (`PlaneDivergenceError`), `:150` (`_resolve_section_keys`); tests `tests/unit/dataframes/test_offline_entity_aware_read.py`; no literal `SCAR-SEAM1` string in code |
| SCAR-AUTHSPECIES-001 (P1) | Unrecognized JWT species (pydantic `ValidationError`) slipped the except chain: 500 | Auth / Error Opacity | `b79ae3cc` #262; `src/autom8_asana/api/dependencies.py:240`; `tests/unit/auth/test_dependencies.py` |
| SCAR-ALARM-BINDING-001 (N=5) | Detection-to-notification chain unbound | Observability Gap | see section 7 |
| RB-1 confirm gate (defensive only) | pre-fire human confirmation for automation-triggering writes | n/a | `8e77c9a0` #263; `mcp/asana_mcp/tools/confirm_gate.py:49` (`DEFAULT_CONFIRMATION_TTL_S = 600.0`), `:78` (`intent_fingerprint`) |

### 4. Scars cataloged 2026-10-05 pass (anchors re-derived)

| SCAR ID | Failure | Category | Fix commit | Current location / regression test |
|---|---|---|---|---|
| SCAR-CASCADE-HIER-001 (P1) | One deleted (404) ancestor zeroed the contact-hierarchy warm; cure unclearable because gate denominator included parentless rows | Cascade / Cache Coherence | `55e69d78` #386, `56375c5b` #387, `a1b046a9` #389 | tolerant fault set `src/autom8_asana/dataframes/builders/hierarchy_warmer.py:56-79`, `src/autom8_asana/cache/providers/unified.py:44-48`, `src/autom8_asana/cache/integration/hierarchy_warmer.py:25-31,108`; denominator `src/autom8_asana/dataframes/builders/cascade_validator.py:199` (`CascadeDenominatorCollapsedError`), raise `:724`; tests `tests/unit/dataframes/builders/test_hierarchy_gap_warm_ancestor_fault.py`, `tests/unit/cache/test_ancestor_permanent_fault.py`, `tests/unit/dataframes/builders/test_cascade_denominator_rescope.py` |
| SCAR-MANIFEST-TOMBSTONE-001 (P1) | Sections deleted in Asana lingered in the manifest; probes 404 each cycle, `min(last_verified_at)` pinned | Freshness / Silent Corruption | `3c851253` #395, `e9c68636` #396 | `src/autom8_asana/dataframes/section_persistence.py:181` (`prune_absent_sections`), `:637` (`reconcile_manifest_sections_async`); call site `src/autom8_asana/dataframes/builders/progressive.py:350-351`; test `tests/unit/dataframes/test_manifest_tombstone_reconciliation.py` |
| SCAR-FRESHCLOCK-001 (P1, N=4) | Synthetic-fresh generators: (i) preload stamped boot `now()` (`41f1fa80` #339); (ii) null watermark replaced by `now()` (`2601c8c5` #338); (iii) empty sections never stamped on hash-CLEAN (`5d62d0b8` #299); (iv) push-loop phase anchored to process boot (`53f1abb2`) | Freshness / Silent Corruption | see left | (i) `src/autom8_asana/api/preload/progressive.py:642-665` (`created_at=s3_watermark`), test `tests/unit/api/preload/test_fixn_c1_preload_stamp_honesty.py`; (ii) `src/autom8_asana/cache/dataframe/tiers/progressive.py:64` (`NULL_WATERMARK_DECAY_ANCHOR`), test `tests/unit/cache/dataframe/test_fixn_b_null_watermark_decay.py`; (iii) `src/autom8_asana/dataframes/builders/progressive.py:421-423,555-580` (coherence clause rows==0 and gid_hash equals hash of the empty set); (iv) `src/autom8_asana/api/status_push.py:114`, test `tests/unit/api/test_status_push_anchor.py` |
| SCAR-CFWRITE-001 (P1, "200 and writes nothing") | `TasksClient.update` builds `json={"data": kwargs}`; passing `data={...}` double-nests; Asana returns 200, writes nothing | Data Model / Contract | `f6adecbb` #327, `e043a939` #328, `d3c4e3fe` #330 | `src/autom8_asana/services/intake_create_service.py:384,676,750,792` and `src/autom8_asana/services/intake_custom_field_service.py:130` (all `custom_fields=`); transport-seam tests `tests/unit/api/routes/test_intake_create.py`, `tests/unit/api/routes/test_intake_custom_fields.py` |
| SCAR-RESOLVE-REGISTRY-001 | `/v1/resolve/business` probed a key set the registry did not define: frozenset miss on every request | Registry Drift | `ddc4bd0b` #325, `69f33d42` #332 | `src/autom8_asana/services/intake_resolve_service.py:105-116` (key columns read from the registry descriptor); `tests/unit/services/test_intake_resolve_business_index.py` |
| SCAR-F9-TRISTATE-001 | Resolve producer stamped `has_unit` / `has_contact_holder` as asserted false on index lag: unattended revert | Data Model / Contract | `e3aab8d4` #382 | `src/autom8_asana/services/intake_resolve_service.py:87` (`SubtaskObservationError`); route 503 `SUBTASK_OBSERVATION_FAILED` `src/autom8_asana/api/routes/intake_resolve.py:121,188`; `tests/unit/api/routes/test_intake_resolve_f9_semantics.py` |
| SCAR-POLARS-INFER-001 | Bare `pl.DataFrame(rows)` inference: late-string after nulls raises `ComputeError` | Data Model / Contract | `dbd46378` #313, `39830565` #351, `3d0b91f9` #318 | `src/autom8_asana/dataframes/builders/fields.py:186` (`safe_dataframe_construct`); use `src/autom8_asana/substrate/live.py:721-724`; `tests/unit/substrate/test_prov_sweep.py` |
| SCAR-WARM-DEADLINE-001 (P1) | Warmer 429 retry loops slept into the 900 s Lambda wall | Performance Cliff | `bc620e18` #312 | `src/autom8_asana/core/warm_deadline.py:82` (`WarmDeadlineExceeded(BaseException)`); `tests/unit/core/test_warm_deadline.py` |
| SCAR-WARM-STARVE-001 | Piggyback story warmer budget exhausted by the first cascade entities; `offer` got 0 tasks | Performance Cliff | `43d766f6` #369 | `src/autom8_asana/lambda_handlers/story_warmer.py:68` (`DEFAULT_STORY_WARM_PRIORITY_ENTITIES = ("offer",)`), receipt `:200`; `tests/unit/lambda_handlers/test_story_warm_priority_offer.py:419` |
| SCAR-TEMPORAL-IMPUTED-001 | Imputed interval satisfied non-empty transition filters: false "moved" positives | Data Model / Contract | `49cf12ca` #360 | `src/autom8_asana/query/temporal.py:62-69`; `.ledge/decisions/DEFECT-temporal-filter-imputed-false-move-2026-08-12.md`; `tests/unit/api/test_imputation_discriminator.py` |
| SCAR-STATUSPUSH-001 | (a) boot-anchored loop phase; (b) service-account-only ECS runtime: every push built a snapshot then skipped | Push Seam / Auth | `53f1abb2`; `3cd2bf85` #507 | `src/autom8_asana/services/gid_push.py:187,223` (half-configured SA never falls back to the legacy key); pyjwt floor `pyproject.toml:53` |
| SCAR-R7-001 | Canary tenant's reserved sentinel phone absent from the offer roster by construction: permanent +1 divergence; tripwire also passed on a dead traffic leg | Observability Gap | `f8bd78c9` #326, `61a8f01d` | `src/autom8_asana/lambda_handlers/traffic_offer_divergence_tripwire.py:271` (`CANARY_SENTINEL_PHONE`); `tests/unit/lambda_handlers/test_traffic_offer_divergence_tripwire.py` |
| SCAR-BUDGET-LEDGER-001 | Parity budget ledger fail-open on corrupt JSON; unlocked load-check-write | Concurrency | `1276b732` #301 | `tests/harness/substrate_gate/budget.py:69` (`BudgetLedgerCorrupt`); `tests/harness/substrate_gate/test_budget.py` (harness only, no `src/` change) |
| SCAR-CI-DISPATCH-001 (extended) | (a) docs-only pushes to main redeployed prod `6c3ed718` #411; (b) dispatch and push runs shared a concurrency group and canceled each other `408cbc37` #458; (c) `workflow_run` trusted any successful Test run `31eeaff0` #491; **(d) NEW** the `sdk-published` `repository_dispatch` trigger turned any SDK publish into a deploy of unchanged main `eebac9da` #523; **(e) NEW** root-secret-inventory-only, test-workflow-only and scanner-config-only pushes redeployed or produced no Test run `d912fa0d` #525, `ede2f116` | Integration / CI | listed | `.github/workflows/satellite-dispatch.yml:3` (removal note), `:12` (`workflow_run`), `:26-27` (concurrency group `asana-satellite-deploy`), `:39-43` (push-to-main, same-repo filter); `.github/workflows/test.yml:41-51` (`paths-ignore` deny-list incl. the root secret inventory file, the test workflow, the gitleaks workflow, `.gitleaksignore`); no automated test (workflow level) |
| SCAR-SEC-001 | Any holder of a valid fleet service JWT could drive any Asana write route | Security | `54431c18` #391 | `src/autom8_asana/api/write_authz.py`; `src/autom8_asana/api/routes/internal.py:118` (`require_service_claims`); `tests/unit/api/test_write_authz_coverage.py`; allowlist population is operator state |
| SCAR-TASKCACHE-PHE-001 | TASK cache key opt_fields-blind: a narrower first read poisons later wider reads | Cache Coherence | `79285c78` #217 | `src/autom8_asana/clients/tasks.py:202,306` (`stored_projection` coverage gate); `tests/unit/cache/test_coverage_predicate.py` |
| SCAR-VACUOUS-PASS-001 | A "pass" over an empty or short population (`all()` over empty set; per-page `length()`) | Observability / Instrument Honesty | `afd22b38` #469, `7858b7df` #465 | docs-only evidence `.ledge/reviews/SOAK-read-the-name-s1-2026-09-14.md`; procedure fix, no src anchor |

Also on record, low severity: `71e07f17` #490 (anyio CVE floor, now `pyproject.toml:13`), `3696358a` #495 (gitleaks pin), `fc4d95f6` #410 (namespace storage anchor).

### 5. NEW scars from the 32 commits since `c29f58f4` (IDs new; doc-level IDs, no `SCAR-` string exists in code for any of them)

The API hardening series (#533, #534, #535, #537, #538) landed in one day (2026-11-10) as a connected set of defects in the request-admission boundary (rate limiter, idempotency, probes). Commit bodies state the root causes; the code confirms each fix.

| SCAR ID | What failed | Root cause (from commit and code) | Fix commit | Fix location at `584c8f79` | Guard / regression test |
|---|---|---|---|---|---|
| SCAR-RATELIMIT-IDENTITY-001 (P1, security) | The service rate limiter chose its bucket from raw token bytes **before** the token was verified, and every JWT caller shared one prefix-keyed bucket; PATs were keyed by a raw prefix | `create_fleet_app` documents "JWT before rate-limiting", but Starlette `add_middleware` stacks each new layer outside the earlier ones, so SlowAPI became the outer layer | `45412996` #533 | `src/autom8_asana/api/rate_limit.py:270` (`ensure_rate_limit_runs_after_auth`: reorders, is idempotent, raises `RuntimeError` if either middleware is missing or duplicated); `:142` (`_bound_verified_payload`: token payload accepted only when `sub`/`iat`/`exp` equal the verified claims); `:168` (`_verified_identity_key`); `:209` (`_pat_key`: keyed HMAC of the whole token, per-process random key); `:221` (`_get_rate_limit_key`); wired `src/autom8_asana/api/main.py:551` | `tests/unit/api/test_rate_limit_verified_key.py` (11 tests: built-app order `:177`, reorder idempotence `:188`, unsigned and wrong-key tokens claiming the resolver identity do not get the service bucket `:218,:235`, genuinely signed one does `:250`, distinct services and business ids separate buckets `:282,:295`, junk prefix-sharing tokens do not drain the verified bucket `:318`, PAT prefix collision `:345`, IP key for unauthenticated `:361`) |
| SCAR-LIMITER-CONFIG-001 (security) | SlowAPI `Limiter` loaded settings from a dotenv-style file in the process working directory whenever one existed, and `RATELIMIT_*` environment values could redirect storage | Library default `config_filename` reads the working directory; storage URI was implicit | `12da7a7c` #534, `93ccb168` #537 | `src/autom8_asana/api/rate_limit.py:336-345` (`LIMITER_CONFIG_FILENAME` points at a fixed absent path), `:348` (`LIMITER_STORAGE_URI = "memory://"`), `_build_limiter` `:345-360` passes both; `.dockerignore` ignore list widened (both commits); 429 handler logs namespace only, never the key: `src/autom8_asana/api/errors.py:723` | `tests/unit/api/test_limiter_config_file.py` (`:20,:27,:45,:49`), `tests/unit/api/test_limiter_hardening.py` (`test_limiter_storage_uri_is_pinned_in_process`, `test_429_handler_logs_namespace_but_never_the_key`) |
| SCAR-IDEM-DEFAULT-001 (security) | Idempotency store-and-replay defaulted to DynamoDB while the middleware runs before request authentication (stated in the PR #535 rationale comment `src/autom8_asana/api/main.py:403-406`; order established by an out-of-tree check, see Knowledge Gaps), so a replayed response could be keyed without a verified caller | Middleware order: `IdempotencyMiddleware` wraps `JWTAuthMiddleware` (established); default chosen when the store was added | `df867da3` #535 | `src/autom8_asana/api/main.py:90` (`DEFAULT_IDEMPOTENCY_BACKEND = "noop"`), `:403-407` (rationale), `:409-442` (backend dispatch); middleware wired `:544` | `tests/unit/api/middleware/test_idempotency_store_default.py` (`:33,:37,:41`: default is passthrough; unconfigured app wires passthrough; configured backend still opts in) |
| SCAR-PROBE-429-001 | A flood of requests from one address could get `/health` and `/ready` answered 429 by the SlowAPI default limit, which a load balancer reads as an unhealthy task; once exempt, `/ready` made an unauthenticated outbound JWKS call, so a probe flood could become an outbound flood | Probes under the default limit; exemption is keyed by the handler's module and function name, so a rename silently restores the limit | `a9929f63` #538 (D-AF3 part 1) | `src/autom8_asana/api/rate_limit.py:376` (`exempt_from_rate_limit`); `src/autom8_asana/api/routes/health.py:392` (`health_check`) and `:422` (`readiness_check`) decorated; `/health/deps` `:530` deliberately NOT exempt; single-flight TTL cache `:230` (`_SingleFlightTTLCache`), `READY_DEPENDENCY_TTL_SECONDS = 5.0` `:224`, `_ready_jwks_check` `:370`, `reset_readiness_dependency_cache` `:382` | `tests/unit/api/test_health_limiter_exempt.py` (name pin `:116`, built-app handler pin `:121`, only the pinned probes are exempt `:129`, `/health/deps` not exempt `:143`, `/docs` exists so the teeth twin is not vacuous `:151`, probe flood never 429 `:165`, same flood to a limited route 429 `:174`), `tests/unit/api/test_ready_dependency_cache.py` |
| SCAR-PHONE-TYPE-001 | Three phone-carrying fields (enrollment intent office phone, the resolved-business office phone, the booking contact phone) were plain `str`, bypassing the canonical `autom8y_api_schemas` phone types | Contract drift against the shared schema package | `15f6b15a` #528 (R03 "bench cure") | `src/autom8_asana/enrollment/intent_projection.py:455` (`office_phone: OfficePhoneField`), wrap `:730`; `src/autom8_asana/automation/workflows/leads_consumer.py:79,297`; `scripts/certification/landing_receipt.py:345,446` | `tests/unit/enrollment/test_r03_phone_field_contract.py` (two-sided: valid E.164 passes `:30`, malformed refused `:35`, NewType wrap is identity at runtime `:40`). Annotation-only; the commit states no runtime behavior change |
| SCAR-CI-TOKEN-MASK-001 | The CodeArtifact auth token was written into `GITHUB_ENV` inside a composed index URL without first being registered as a masked value | Missing `::add-mask::` before the `GITHUB_ENV` write | `889661a7` #532 | `.github/workflows/test.yml:221,370,577` (mask line before each write); `.github/workflows/durations-refresh.yml:60` | none (workflow); the gitleaks workflow is the detector |
| SCAR-CERTIFI-GHSA-001 (low) | certifi before 2026.10.19 bundled root CAs with compromised intermediates (GHSA-6q48-6c7w-9gw2); the deploy image scan refused it and blocked deploys | Locked dependency version | `cf32e033` #524 | `uv.lock` (lock-only, certifi block) | the image scan in the deploy build |
| SCAR-CRED-PRINTERS-001 | Developer recipes printed a suffix fragment of the Asana PAT and the workspace id; a docs step fetched the whole secret instead of its metadata | Value printers in `check-env` and `fetch-secrets` recipes and atuin runbook validation blocks | `8ff0ae35` #520 (A4(b)) | recipes and runbooks (value printers removed; `check-env` prints presence state only; `fetch-secrets` refuses while the companion version variable is set); declaration file named in the commit; loader notes in `.know/env-loader.md` | none (recipe level) `[INFERRED]` from the commit body; recipe text was not re-read |
| SCAR-TC002-FWDREF-001 (retro-cataloged; revert `b9cf6dbc`, 2026-04-29) | Ruff TC002 autofix moved `from fastapi.responses import Response` into a `TYPE_CHECKING` block; with `from __future__ import annotations` pydantic could not resolve the forward ref at OpenAPI generation (`PydanticUserError ... not fully defined`) | Lint autofix outside plan scope | `b9cf6dbc` | `src/autom8_asana/api/routes/exports.py:45` (`# noqa: TC002 — pydantic resolves at OpenAPI emit time`) | spec-drift CI job on `docs/api-reference/openapi.json` (`.github/workflows/test.yml:141` passes the spec path); no dedicated unit test |
| SCAR-CI-ASANA-PAT-INJECT-001 (retro-cataloged; revert `a609762a`, 2026-04-10) | `secrets` context referenced inside a `with:` block is not allowed; the workflow failed | CI syntax constraint | `a609762a` | `.github/workflows/test.yml` (single hunk, not re-derived) | none (historical) |
| SCAR-LAYER-DRIFT-001 (prophylactic series, not a runtime failure) | Lower layers imported `api` (Semgrep rule `asana-no-lower-imports-api` counted 22 sites) | Wire models, exception types, settings and metrics lived under `api/` but were consumed by `services/`, `core/`, `cache/` | `c09422ed` #514 (22 to 5 sites in four moves, each with a re-export shim), `773aa98a` #515 (Semgrep layer rules run on every PR, whole-repo scan), `fcf8d954` #539 / `d10c2330` #540 (import-linter contracts for the new `trigger` package) | `.github/workflows/semgrep-layer-rules.yml`; `tests/arch/test_import_contracts.py`; `tests/arch/test_trigger_adapter_placement.py`; `tests/arch/test_trigger_asana_client_ast.py`; `pyproject.toml` `[tool.importlinter]` (`:109` dev dependency, `:237` AST-guard note, `:317` pending-contracts block) | the contract tests above: each contract has a synthetic broken package that must report BROKEN with exactly the planted pairs plus a clean twin that must report KEPT (commit body of #539); 5 residual Semgrep sites remain per the #514 body (not re-run here) |

Commits in the 32 that are NOT scars (classified and excluded): #541 (D6 registration, dark, feature), #531 (floodgates onboarding-deck recipes, feature; its D9 name-match and D10(b) rendered-deck gates are defensive additions to a feature, not responses to a recorded failure), #542 (replaces a real-looking phone example with a fictional stand-in in OpenAPI examples and tests; PII-hygiene sweep, 11 files), and 14 docs-only commits (#511, #513, #518, #516, #517, #519, #521, #522, #527, #529, `437762e9`, `d28b2799`, the read-the-name soak rows).

### 6. Reconciliation of the catalog against in-code markers

| Marker family | Count at `584c8f79` (method) | Catalog coverage |
|---|---|---|
| `@pytest.mark.scar` | 46 uses in 17 files (text walk); list: `tests/unit/reconciliation/test_section_registry.py` 7, `tests/unit/dataframes/test_freshness_verification_recency.py` 7, `tests/unit/dataframes/test_warmup_ordering_guard.py` 5, `tests/unit/api/middleware/test_idempotency_finalize_scar.py` 5, `tests/unit/dataframes/test_l2_gate_frameless_provider.py` 4, `tests/unit/dataframes/test_cascade_ordering_assertion.py` 3, `tests/unit/knowledge/test_register_drift_guard.py` 3, `tests/unit/api/test_exports_auth_exclusion.py` 2, `tests/unit/services/test_universal_strategy_status.py` 2, 7 singles (`tests/unit/api/preload/test_progressive_cascade.py`, `tests/unit/api/test_exports_format_negotiation.py`, `tests/unit/api/test_tags_auth_exclusion.py`, `tests/unit/core/test_entity_registry.py`, `tests/unit/dataframes/builders/test_cascade_validator.py`, `tests/unit/models/business/matching/test_normalizers.py`, `tests/unit/services/test_section_timeline_service.py`) plus 1 in `tests/unit/knowledge/register_drift_checks.py` | All map to SCAR-REG-001, FRESH-001, 005/006, IDEM-001, L2GATE-001, WS8, 020, 015 and the register-drift guard. None of the 17 section-4 scars or the 11 section-5 entries carries the marker |
| Distinct `SCAR-` IDs in code | 18 string forms found; after removing non-IDs (`SCAR-TISSUE` in `src/autom8_asana/dataframes/builders/null_number_recovery.py:61`, a prose use; `SCAR-marked`; `SCAR-NEW-999` and `SCAR-REG-001-narration`, test fixtures in `tests/unit/knowledge/test_register_drift_guard.py`) 14 real IDs: 005, 005-006 (joint), 006, 015, 020, 028, CW-001, FRESH-001, IDEM-001, METRICS-SELECT-FILTER-001, REG-001, W1E-LOADGROUP-001, WS8, CANDIDATE-PLAY-CONSUMED-TRIGGER | All 13 non-candidate IDs are in the catalog. SCAR-CANDIDATE-PLAY-CONSUMED-TRIGGER (`mcp/asana_mcp/tools/workflows.py:20`) remains a candidate at N=1 |
| Catalog IDs with **no** `SCAR-` string in code | All 17 section-4 IDs, all 11 section-5 IDs, and from the earlier sections SEAM1-PROBER, REDIS-WARMER, L2GATE, AUTHSIG, AUTHSPECIES, SD02, VOCAB-PARITY, TG-LIVENESS, CONSUMER-GATE, ARTIPACKED, S3-LOOP, DISCRIMINATOR, RB-1 (text-walk found no `SCAR-` string for them) | Findable by symbol name in the "Fix location" column, not by `grep SCAR-` |
| `DEF-0` | 15 `src/` lines, 23 `tests/` lines | DEF-001 (SCAR-008, `src/autom8_asana/persistence/session.py:995`) and DEF-005 (SCAR-004) are mapped; other DEF numbers not individually mapped (gap) |
| `CRITICAL` | 18 `src/` lines, 21 `tests/` lines, 1 `.github/` line | not individually reviewed (gap: tone markers, not scar IDs) |
| `BROAD-CATCH` | 216 `src/` lines, 22 `tests/` lines (prior pass: 207 `src/`) | intentional-catch annotations, not scars; the deliberate non-catchables are `WarmDeadlineExceeded(BaseException)` and `CancelledError` in the idempotency finalize path |
| `BUG-` | 4 `tests/` lines | not mapped (gap) |
| `FIXME` / `HACK` / `WORKAROUND` | 0 | n/a |

### 7. SCAR-ALARM-BINDING-001 (N=5): binding-blind alarm class (P1, satellite-local)

Unchanged in substance since the prior pass; re-verified at `584c8f79`: variable `ticket_sns_topic_arn` `terraform/services/asana/observability_alarms.tf:100`, opt-in `require_alarm_binding` `:144`, resolution `:192` (prior pass), AL-5 precondition `:668-671` (prior pass; not re-read this pass, treat as `[carry]`). Occurrences 1-4 as in the prior pass; occurrence 5 = stratum source-health series publishing `1` on fault and nothing otherwise (`55f81e0b` #334). Default remains non-enforcing; the class is detectable, not unconstructable. Apply state is operator-gated and not observable from the repo. No new occurrence since `c29f58f4`; the elevation watch (an instance outside the asana satellite) is unmet.

## Category Coverage

Taxonomy applied to every catalog entry (legacy, 2026-07, 2026-10 and the new section 5 entries). Categories with 3 or more entries are flagged SYSTEMIC. "Not searched" is distinguished from "not found" at the end.

| Category | Count | Entries | Flag |
|---|---|---|---|
| Data Model / Contract | 14 | 008, 014, 023, 024, 025, 030, IDEM-001, DISCRIMINATOR-001 (open), CFWRITE-001, F9-TRISTATE-001, POLARS-INFER-001, TEMPORAL-IMPUTED-001, METRICS-SELECT-FILTER-001 (resolved), PHONE-TYPE-001 | SYSTEMIC (largest; 1 open) |
| Cache Coherence | 7 | 003, 004, 005, 006, 007, S3-LOOP, TASKCACHE-PHE-001 | SYSTEMIC |
| Startup / Deployment | 8 | 009, 011/011b, 013, 022, REG-001, CW-001, TG-LIVENESS-001 | SYSTEMIC |
| Freshness / Silent Corruption | 5 | FRESH-001, SEAM1-PROBER-001, FRESHCLOCK-001 (N=4), MANIFEST-TOMBSTONE-001, VACUOUS-PASS-001 | SYSTEMIC |
| Workflow Logic | 5 | 016-019 (undescribed), 020 | SYSTEMIC but 4 of 5 undescribed |
| Authentication / Error Opacity | 5 | 012, Env-var typo, AUTHSIG-001, AUTHSPECIES-001, STATUSPUSH-001(b) | SYSTEMIC |
| Supply Chain / CI Secret Hygiene (new grouping) | 7 | ARTIPACKED-001, anyio CVE floor, certifi GHSA-001, CI-TOKEN-MASK-001, CRED-PRINTERS-001, gitleaks pin and baseline (`3696358a`, `ede2f116`), CI-ASANA-PAT-INJECT-001 | SYSTEMIC (4 of the 7 are from this window: certifi, token mask, value printers, gitleaks baseline) |
| Request-Admission Boundary / Hardening (new grouping) | 4 | RATELIMIT-IDENTITY-001, LIMITER-CONFIG-001, IDEM-DEFAULT-001, PROBE-429-001 | SYSTEMIC (all four on 2026-11-10) |
| Integration / CI | 4 | 021, 026, CONSUMER-GATE-001, CI-DISPATCH-001 (now 5 sub-failures a-e) | SYSTEMIC |
| Concurrency | 4 | 002, 010/010b, BUDGET-LEDGER-001 | SYSTEMIC |
| Security / Input Validation | 5 | 027, 028, 029, WS8, SEC-001 | SYSTEMIC |
| Performance Cliff | 3 | 015, WARM-DEADLINE-001, WARM-STARVE-001 | SYSTEMIC |
| Cascade Planner / Gate | 2 | L2GATE-001, CASCADE-HIER-001 | not systemic by itself; wound shared with Cache Coherence 005/006 |
| Registry Drift | 2 | VOCAB-PARITY-001, RESOLVE-REGISTRY-001 | 2 |
| Observability Gap | 2 | ALARM-BINDING-001 (N=5), R7-001 | 2 (the class itself has N=5 occurrences) |
| Push Seam | 2 | SD02 (resolved), STATUSPUSH-001 | 2 |
| Build / Lint Tooling | 2 | LP-001, TC002-FWDREF-001 | 2 |
| Architecture / Layer Drift (new) | 1 | LAYER-DRIFT-001 (prophylactic) | only 1 observed |
| Single-instance | 1 each | SDK Interface Gap (LOG-001), Epistemic / Drift (P6-001), Test Infrastructure (W1E-LOADGROUP-001), Doc / Spec Drift (CSI-001), Entity Resolution (001), Cache Backend / Pool (REDIS-WARMER-001) | only 1 observed |

Moves versus the prior pass's grouping: the prior "Security / Input Validation" (7) is split into "Security / Input Validation" (5) and "Supply Chain / CI Secret Hygiene"; ARTIPACKED-001 and the anyio CVE moved with it. Data Model rose 13 to 14 (PHONE-TYPE-001 added; METRICS-SELECT-FILTER-001 moved from open to resolved within the category).

**Systemic recurrences across categories (3 or more).**
1. **Documented control silently inert or mis-ordered** (new, N=6): RATELIMIT-IDENTITY-001 (documented "JWT before rate-limiting" order was inverted), IDEM-DEFAULT-001 (idempotency runs before auth; the #535 comment is correct and three other in-repo order statements are stale or wrong, see Knowledge Gaps), PROBE-429-001, LIMITER-CONFIG-001 (limiter reading ambient config), ALARM-BINDING-001 (default non-enforcing, `require_alarm_binding` false), CONSUMER-GATE-001. Shape: the architecture states an invariant in a comment or factory doc; nothing asserts it until a bug.
2. **Silent no-op masquerading as success**: CFWRITE-001 (HTTP 200, zero write), REDIS-WARMER-001 layer 1, STATUSPUSH-001 (skip), AL-5, VACUOUS-PASS-001.
3. **Freshness-clock lies**: FRESHCLOCK-001 (N=4), SEAM1, MANIFEST-TOMBSTONE, FRESH-001.
4. **Error and measurement opacity**: AUTHSIG-001 (N=3), ALARM-BINDING-001, VACUOUS-PASS, R7, F9.
5. **Hand-enumerated list drifting from a registry**: VOCAB-PARITY, RESOLVE-REGISTRY, L2GATE, the classifier roster in MANIFEST-TOMBSTONE.
6. **Cascade wound at N parent-chain sites**: 005/006, CASCADE-HIER, L2GATE.
7. **CI trigger scope creep** (SCAR-CI-DISPATCH-001, now 5 sub-failures a-e over 2026-09 to 2026-10): each fix narrowed what may deploy; the paths-ignore deny-list in `.github/workflows/test.yml:41-51` grows with every non-build input.

**Searched, not found (explicit absence):** schema-migration failures, distributed-lock-service bugs, network-partition handling. Evidence: no `fix` subject and no marker for these in the git history subjects and `src/` markers scanned. **Not searched:** `terraform/` beyond `terraform/services/asana/observability_alarms.tf`, `.github/workflows/` beyond `.github/workflows/test.yml`, `.github/workflows/satellite-dispatch.yml`, `.github/workflows/semgrep-layer-rules.yml`, `docs/`, `runbooks/`, the 503-fix tail older than 2026-07 (subjects not re-triaged individually this pass).

## Fix-Location Mapping

**Method.** Every fix location in the three catalog tables and section 5 was re-derived at `584c8f79` by a text walk over the manifest files (function, class or constant name matched to a line) and by direct reads of the changed regions. 27 of 27 sampled regression-test paths named in this document were confirmed present in the manifest. Entries marked `[carry]` have no in-repo anchor to derive.

**Moved anchors found this pass (all re-pointed above):**

| Anchor | Prior line | Now |
|---|---|---|
| `src/autom8_asana/api/main.py` JWT `exclude_paths` (SCAR-WS8) | `:454`, comment `:471` | `:461`, comment `:478` |
| `src/autom8_asana/api/status_push.py` `seconds_until_next_fire` | `:61-122` | `:114` |
| `src/autom8_asana/services/gid_push.py` `ServiceTokenMintError` | `:187-223` | class at `:223` (comment block `:187`) |
| `src/autom8_asana/query/models.py` `_predicate_discriminator` | `:136-152` | `:136-153` (helper `:154`, was `:155`) |
| `pyproject.toml` `--dist=loadgroup` / `worker_isolated` | `:124` / `:131` | `:125` / `:132` |
| `.github/workflows/test.yml` candidate-wheel step / `persist-credentials` | `:245-257` / `:157-160` | `:262` / `:173-176`; quarantine job `:308` (was `:291`) |
| `src/autom8_asana/metrics/__main__.py` FRESH-001 marker | `:788` | `:789` |
| `src/autom8_asana/api/lifespan.py` status push | `:384-390`, stop `:431-435` | construct `:388`, start `:389`, stop `:431-435` |
| `src/autom8_asana/lambda_handlers/story_warmer.py` priority tuple | `:57-71` | `:68`, receipt `:200` |

**No fix location found broken (deleted or moved file).** Every file path in the prior catalog that this pass re-checked still exists. `src/autom8_asana/metrics/compute.py` is now a fix location rather than a defect location.

**Compound fixes (multi-site):**
- SCAR-RATELIMIT-IDENTITY-001: four cooperating sites in `src/autom8_asana/api/rate_limit.py` (`:142`, `:168`, `:209`, `:270`) plus the wiring call `src/autom8_asana/api/main.py:551` and the metric namespace in `src/autom8_asana/observability/prometheus_metrics.py` (diffstat of `45412996`; line not re-derived).
- SCAR-PROBE-429-001: `src/autom8_asana/api/rate_limit.py:376` + `src/autom8_asana/api/routes/health.py:392,422,370` (three coordinated pieces: exemption wrapper, decorators, TTL cache).
- SCAR-CASCADE-HIER-001: three fetch sites (`src/autom8_asana/dataframes/builders/hierarchy_warmer.py:56`, `src/autom8_asana/cache/providers/unified.py:44`, `src/autom8_asana/cache/integration/hierarchy_warmer.py:25,108`) plus the denominator (`src/autom8_asana/dataframes/builders/cascade_validator.py:199,724`).
- SCAR-FRESHCLOCK-001: four sites, listed in section 4.
- SCAR-CW-001: five onion layers; layers 1-3 (network, Dockerfile, SDK) have no in-repo code anchor; layers 4-5 map to `src/autom8_asana/services/universal_strategy.py:60` and `src/autom8_asana/models/business/detection/facade.py` (not re-derived this pass).
- SCAR-CI-DISPATCH-001: two workflow files (`.github/workflows/test.yml`, `.github/workflows/satellite-dispatch.yml`).

**Findable only by another name** (no `SCAR-` string in code): all section-4 and section-5 entries, SEAM1-PROBER-001 (search `PlaneDivergenceError` or `SEAM-1`), REDIS-WARMER-001, CASCADE-HIER-001 (search `CascadeDenominatorCollapsedError`), MANIFEST-TOMBSTONE-001 (search `prune_absent_sections`).

## Defensive Pattern Documentation

Each row: scar, then guard (location), then regression test, then explicit gap if none. "Teeth" means the test has a broken or negative twin that fails when the guard is removed.

| Scar | Guard | Regression test | Gap |
|---|---|---|---|
| RATELIMIT-IDENTITY-001 | startup assertion `ensure_rate_limit_runs_after_auth` fails loudly on missing or duplicated middleware (`src/autom8_asana/api/rate_limit.py:270`); payload accepted only if bound to verified claims (`:142`) | `tests/unit/api/test_rate_limit_verified_key.py` (spoofed-identity tests assert the spoofed token does NOT get the service bucket, and the genuine one does) | teeth present |
| LIMITER-CONFIG-001 | fixed absent config path and pinned `memory://` storage (`src/autom8_asana/api/rate_limit.py:336-348`) | `tests/unit/api/test_limiter_config_file.py`, `tests/unit/api/test_limiter_hardening.py` | no test that `.dockerignore` keeps ambient config files out of the image (file-level; not read) |
| IDEM-DEFAULT-001 | `DEFAULT_IDEMPOTENCY_BACKEND = "noop"` (`src/autom8_asana/api/main.py:90`) | `tests/unit/api/middleware/test_idempotency_store_default.py` | the underlying defect (idempotency running before auth) is **not fixed**, only defaulted off; opting in re-opens it. One test pins the position relative to SlowAPI only (`tests/unit/api/middleware/test_idempotency_contracts.py:591-593`: idempotency index below SlowAPI index in `user_middleware`, i.e. outer); none pins it relative to `JWTAuthMiddleware` |
| PROBE-429-001 | exemption wrapper + decorators + 5 s single-flight JWKS cache | `tests/unit/api/test_health_limiter_exempt.py` (names pinned; both-sided flood test, with a `/docs` twin guarding against vacuity), `tests/unit/api/test_ready_dependency_cache.py` | rename safety rests on the name-pin test only |
| PHONE-TYPE-001 | canonical `NewType` annotations and wraps | `tests/unit/enrollment/test_r03_phone_field_contract.py` (two-sided) | mypy enforcement is the real guard; not run here |
| METRICS-SELECT-FILTER-001 | `src/autom8_asana/metrics/compute.py:99-128` carries and drops filter columns | `tests/unit/metrics/test_compute_filter_columns.py` (4 cases + all-registered-metrics sweep `:106`) | not added to `RESOLVED_SCAR_IDS` (`tests/unit/knowledge/register_drift_checks.py:36`) and not `@pytest.mark.scar`-marked |
| CI-TOKEN-MASK-001 | `::add-mask::` before every `GITHUB_ENV` write (`.github/workflows/test.yml:221,370,577`) | none | no workflow test; no check that a fourth write site gets a mask |
| CI-DISPATCH-001 | paths-ignore deny-list `.github/workflows/test.yml:41-51`; same-repo push-to-main filter `.github/workflows/satellite-dispatch.yml:39-43`; dedicated concurrency group `:26-27` | none | workflow-level; the `paths-ignore` set is an allow-by-omission list: any new non-build input redeploys until added |
| CRED-PRINTERS-001 | printers removed; presence-only output | none found | no test; recipe text not re-read |
| LAYER-DRIFT-001 | Semgrep rule on every PR; import-linter contracts with broken-twin fixtures | `tests/arch/test_import_contracts.py`, `tests/arch/test_trigger_adapter_placement.py`, `tests/arch/test_trigger_asana_client_ast.py` | `allow_indirect_imports = true`: the contracts forbid direct imports only (#539 body); transitive guard is a runtime class check in each adapter |
| 005/006/023, L2GATE | provider predicate (`src/autom8_asana/dataframes/cascade_utils.py:325,362`); `src/autom8_asana/dataframes/builders/cascade_validator.py:30`; `src/autom8_asana/api/preload/progressive.py:851` (never BROAD-CATCH) | `tests/unit/dataframes/test_warmup_ordering_guard.py` (5), `tests/unit/dataframes/test_cascade_ordering_assertion.py` (3), `tests/unit/dataframes/test_l2_gate_frameless_provider.py` (4) | none |
| 008, 010/010b | accessor-clear-before-snapshot (`src/autom8_asana/persistence/session.py:995`); `_require_open()` (`:439,517,547`) | none marked scar | no scar-marked test |
| 020 | `src/autom8_asana/models/business/matching/normalizers.py:80` | `tests/unit/models/business/matching/test_normalizers.py` (1 marker) | none |
| 027, 029, 028 | `src/autom8_asana/core/creation.py:83,93`; `src/autom8_asana/api/routes/webhooks.py:465-471`; `src/autom8_asana/clients/data/_pii.py:21,45` | none marked | no scar-marked test for any of the three |
| S3-LOOP | `src/autom8_asana/core/retry.py:198,267` | none marked | no scar-marked test |
| IDEM-001 | `src/autom8_asana/api/middleware/idempotency.py:751-775` | `tests/unit/api/middleware/test_idempotency_finalize_scar.py` (5), drift guard `tests/unit/knowledge/register_drift_checks.py:36` | now dormant on the default path |
| REG-001 | fail-closed `src/autom8_asana/reconciliation/section_registry.py:375,429` | `tests/unit/reconciliation/test_section_registry.py` (7), `tests/unit/knowledge/test_register_drift_guard.py` (3) | none |
| WS8 | `src/autom8_asana/api/main.py:461,478` | `tests/unit/api/test_exports_auth_exclusion.py` (2), `tests/unit/api/test_tags_auth_exclusion.py` (1) | none |
| FRESH/SEAM1/FRESHCLOCK/MANIFEST-TOMBSTONE | `PlaneDivergenceError` `src/autom8_asana/dataframes/offline.py:54`; `created_at` anchor; decay anchor `src/autom8_asana/cache/dataframe/tiers/progressive.py:64`; prune fence | tests named in section 4 | only FRESH-001's file is scar-marked |
| CASCADE-HIER | per-GID tolerance, per-chunk isolation, fail-closed denominator | 3 test files | no scar marker |
| CFWRITE | transport-seam tests assert the real marshaled body | `tests/unit/api/routes/test_intake_create.py`, `tests/unit/api/routes/test_intake_custom_fields.py` | other `TasksClient.update(data=...)` callers not swept `[INFERRED gap]` |
| AUTHSPECIES / AUTHSIG / RB-1 | `src/autom8_asana/api/dependencies.py:240`; `mcp/asana_mcp/bridge.py:27,49`; `mcp/asana_mcp/tools/confirm_gate.py:49,78` | `tests/unit/auth/test_dependencies.py`; `mcp/tests/test_bridge_401_fail_clean.py`; `mcp/canary/test_broken_fixture_canary.py` | none |
| W1E, CONSUMER-GATE, ARTIPACKED | `pyproject.toml:123-132`; `.github/workflows/test.yml:262,176,308` | n/a (infrastructure) | no workflow test |
| DISCRIMINATOR-001 | none (open) | none | **open and unguarded** |
| ALARM-BINDING | IaC precondition and binding report | none (IaC) | default non-enforcing |
| Unguarded (no guard, no test) | CI-TOKEN-MASK-001, CRED-PRINTERS-001, CERTIFI-GHSA-001 (image scan only), CI-ASANA-PAT-INJECT-001, SCAR-DISCRIMINATOR-001, SCAR-TC002-FWDREF-001 (CI spec-drift job only), 016-019 | | stated plainly |

**Scar-marker coverage:** The 46 `@pytest.mark.scar` uses attach to the older scar families only (REG-001, FRESH-001, 005/006, IDEM-001, L2GATE, WS8, 020, 015 and the register-drift guard, per the marker table). `pytest -m scar` therefore under-reports regression coverage of the 28 later scars (17 + 11 entries in sections 4 and 5); most have tests that run outside that selector, a few (listed as unguarded above) have none.

## Agent-Relevance Tagging

| Scar(s) | Roles | Why (constraint the agent must honor) |
|---|---|---|
| RATELIMIT-IDENTITY-001, LIMITER-CONFIG-001, PROBE-429-001, IDEM-DEFAULT-001 | principal-engineer, security-reviewer, qa-adversary | Do not change middleware registration order in `create_app` without re-running the order test; never key a limiter on unverified token bytes; a new always-on probe must be exempted by name and the name pinned; idempotency must not be switched on without first moving it behind authentication (it currently wraps the JWT middleware) |
| PROBE-429-001 | platform-engineer, sre | `/ready` is the ALB target-group probe and now serves a 5 s cached JWKS result; treat a probe 429 as an outage, not a limit |
| 005/006/023, L2GATE, CASCADE-HIER | principal-engineer, architect | New cascade provider goes through `get_frame_warm_providers`; any parent-chain fetch tolerates 404, 410 and 403 per GID; gate denominators are scoped in-frame |
| REDIS-WARMER | platform-engineer | Test the prod image against its exact `uv sync --extra` set; pick `connection_class` for TLS explicitly |
| FRESH-001, SEAM1, FRESHCLOCK, MANIFEST-TOMBSTONE | principal-engineer, qa-adversary | Thread `entity_type` through every S3-writing builder; never synthesize `now()` for an unknown watermark; prune deleted sections by live-listing membership |
| CFWRITE | principal-engineer, qa-adversary | Never pass `data=` to `TasksClient.update`; test at the transport seam, not by stubbing `update_async` |
| METRICS-SELECT-FILTER-001 | principal-engineer | New metric filters may reference unselected columns; keep the carry-then-drop pattern in `src/autom8_asana/metrics/compute.py:99-128` |
| RESOLVE-REGISTRY, VOCAB-PARITY | principal-engineer | Derive keys and vocabulary from the registry descriptor, never from a literal |
| F9-TRISTATE, TEMPORAL-IMPUTED, VACUOUS-PASS | principal-engineer, qa-adversary | Absence of evidence must not serialize as an asserted false; a pass over an empty set is not a pass |
| POLARS-INFER, PHONE-TYPE-001 | principal-engineer | Use `safe_dataframe_construct`; annotate phone fields with the canonical schema types and wrap construction sites |
| WARM-DEADLINE, WARM-STARVE | platform-engineer, sre | Warm loops yield to the Lambda deadline; budget-bound warmers need per-entity zero receipts |
| ALARM-BINDING, R7 | observability-engineer, platform-engineer | One receipted end-to-end fire per alarm; real-0 companions for fire-only series |
| AUTHSIG, AUTHSPECIES, SEC-001, STATUSPUSH | security-reviewer, principal-engineer | Catch SDK validation-layer exceptions; remediation text names env keys never values; write routes need the deny-by-default gate; configured service account implies no silent fallback to the legacy key |
| CI-DISPATCH, CONSUMER-GATE, ARTIPACKED, CI-TOKEN-MASK, CERTIFI-GHSA, CRED-PRINTERS | platform-engineer, releaser, security-reviewer | Deploy triggers are push-to-main only, path-filtered by deny-list, per-dispatch concurrency; mask any token before writing it to `GITHUB_ENV`; recipes print presence, never value fragments; scanner or workflow config changes belong in `paths-ignore` |
| LAYER-DRIFT-001 | architect, principal-engineer | New package code must not import `api`; new `trigger` code is bound by import-linter and an AST guard (`tests/arch/`) |
| TC002-FWDREF-001 | principal-engineer | Do not let a lint autofix move a pydantic or FastAPI forward-referenced type under `TYPE_CHECKING`; keep the `noqa` at `src/autom8_asana/api/routes/exports.py:45` |
| TASKCACHE-PHE, BUDGET-LEDGER | principal-engineer, qa-adversary | Cache hits must be projection-covering; ledger code fails closed on corrupt state |
| SCAR-001..030 legacy undescribed (016-019, 021, 024, 025) | platform-wide / historical only | No retained rationale; treat as historical until re-derived |

## Knowledge Gaps

### Experiential observations (`.sos/land/scar-tissue.md`, generated 2026-04-28; 10 sessions) `[EXPERIENTIAL]`

Verified against the code at `584c8f79`:
- The `AUTOM8_DATA_API_KEY` typo is cured: `src/autom8_asana/clients/data/config.py:231` reads `AUTOM8Y_DATA_API_KEY`.
- CascadingFieldResolver 30% and Offer `office` 30-40% null: maps to SCAR-005/023 and the extension SCAR-CASCADE-HIER-001.
- xdist worker crashes in `tests/unit/lambda_handlers/test_workflow_handler.py`: **superseded**; root cause attributed (SCAR-W1E-LOADGROUP-001; quarantine `pyproject.toml:132`, `.github/workflows/test.yml:308`). The land file's "root-cause not yet attributed" is stale.
- PhoneNormalizer read-path blindness: SCAR-020.
- The land blocker "EntityWriteRequest lacks `extra="forbid"`" is **contradicted by code**: `src/autom8_asana/api/routes/entity_write.py:76` sets `model_config = ConfigDict(extra="forbid")`. Land file marks it "planned"; it landed. Preferring the code.
- UnicodeEncodeError cure is present as ASCII sanitization (`src/autom8_asana/transport/asana_http.py:279-281`, `src/autom8_asana/api/middleware/core.py:147-149`); the 5% to 66% Schemathesis pass-rate claim cannot be verified from code.
Unverifiable from the repo `[EXPERIENTIAL]`: consumer-gate 900 s to 2400 s timeout (autom8y repo); the metrics-CLI under-count open questions about bucket mapping and freshness SLA (only the plane-split part is explained by SEAM1); "33 inviolable scar tests" (the marker count is 46 in 17 files). The land file has no post-April scars; it is 6.5 months old relative to this pass and contributed no new catalog entries.

### Corrections to the prior pass (c29f58f4 -> 584c8f79)

1. **SCAR-METRICS-SELECT-FILTER-001 was reported OPEN and unguarded; it is RESOLVED.** Evidence: `c9891cf6` (#512), `src/autom8_asana/metrics/compute.py:99-128`, `tests/unit/metrics/test_compute_filter_columns.py`. The prior "no `src/autom8_asana/metrics/compute.py` commit since 2026-04-13" was true at its base and false at HEAD.
2. **Prior "Open, unguarded" list shrinks from 2 to 1** (only SCAR-DISCRIMINATOR-001 remains).
3. **SCAR-IDEM-001 "guard live" needs a qualifier:** the guard is dormant on the default path since `df867da3`.
4. **Prior "17 scars lack markers" is now 28** (17 + 11) because section 5 adds 11 entries with no marker; the marker count itself is unchanged (46 in 17 files).
5. **Prior `BROAD-CATCH` 207 lines in `src/`** is now 216 by the same text-walk method; this pass also records `tests/` 22 and `DEF-0` 15 `src/` lines (prior said "DEF-NNN 16 src", a different pattern; not comparable).
6. **Prior "`SCAR-` 23 src + 2 mcp + 58 tests"** is now 25 / 2 / 59, plus 3 in `terraform/services/asana/observability_alarms.tf` (SCAR-015 cure), 1 in `.github/workflows/test.yml` and 1 in `pyproject.toml` that the prior count did not include.
7. **Prior fix-subject count 492 of 1,720 commits** is now 503 of 1,752 by the `^(fix|hotfix)` subject method run this pass; the prior method may differ, so the +11 delta (versus 9 fix subjects in the 32 new commits) is not reconciled.
8. **Anchor moves** are in the Fix-Location Mapping table; none was a deletion.
9. **Retro-cataloged** scars not in the prior catalog although old: SCAR-TC002-FWDREF-001 (`b9cf6dbc`), SCAR-CI-ASANA-PAT-INJECT-001 (`a609762a`). SCAR-014's `fe6bc978` is the third genuine revert.
10. **Experiential claim superseded:** `EntityWriteRequest` now forbids extra fields (see above).

### Open gaps

- **SCAR-P6-001 recurrence (stale checkout).** The session checkout of this repository is 20 commits behind `origin/main` with a dirty tree; this document was built only from the detached worktree at `584c8f79`. A reader of the session checkout would see the prior state (e.g. SCAR-METRICS-SELECT-FILTER-001 open).
- **Open, unguarded:** SCAR-DISCRIMINATOR-001 (P3).
- **Middleware order: established by an OUT-OF-TREE check (installed dependencies; no app constructed or run).** `IdempotencyMiddleware` wraps `JWTAuthMiddleware`, so it runs before authentication; the #535 comment at `src/autom8_asana/api/main.py:403-406` is correct. Evidence: (1) `uv.lock` in the worktree pins `autom8y-api-middleware` 0.3.0 and `starlette` 1.3.1, and the installed copies used had those same versions; (2) module `autom8y_api_middleware._factory`, lines 224-274, registers CORS, `JWTAuthMiddleware`, `SlowAPIMiddleware`, then each `extra_middleware` entry, and `src/autom8_asana/api/main.py:488-545` passes `IdempotencyMiddleware` as the only extra; (3) `starlette.applications`, line 101, `add_middleware` does `user_middleware.insert(0, ...)`, so the last registered is outermost; (4) after the factory the outermost-first order is Idempotency, SlowAPI, JWT, CORS, and `ensure_rate_limit_runs_after_auth` (`src/autom8_asana/api/rate_limit.py:270`, called `src/autom8_asana/api/main.py:551`) moves only SlowAPI inside JWT, giving Idempotency, JWT, SlowAPI, CORS (the layers `src/autom8_asana/api/main.py` adds after the factory sit further out). **Stale or wrong in-repo statements:** `src/autom8_asana/api/middleware/idempotency.py:474-504` (`_get_service_name`, claims JWT runs before idempotency) and the module header `src/autom8_asana/api/middleware/idempotency.py:14-20` (a third order with no JWT layer) disagree with the established order; the SDK's own module docstring (`autom8y_api_middleware._factory`, lines 23-32) claims extras are innermost, contradicting the Starlette rule it quotes; the comment in `tests/unit/api/middleware/test_idempotency_contracts.py:583-590` says idempotency executes innermost while its assertion (`:593`) correctly pins it outer of SlowAPI. `[INFERRED]` consequence, not run: because `JWTAuthMiddleware` is inside idempotency, `request.state.claims` is likely not yet populated when `_get_service_name` reads it on the way in, which would silently yield the default service discriminator; unverified.
- **IDEM-DEFAULT-001 is a mitigation, not a fix:** the commit makes store-and-replay opt-in because the middleware runs before authentication (established above); the ordering defect itself is unchanged. If an operator sets `IDEMPOTENCY_STORE_BACKEND=dynamodb`, pre-auth keying returns. Which backend production sets is not observable from the repo.
- **Rate-limiter storage is per-process** (`LIMITER_STORAGE_URI = "memory://"`, `src/autom8_asana/api/rate_limit.py:348`; the `_pat_key` docstring at `:209` notes the HMAC key must become shared if storage moves). Effective limits therefore scale with task count; not a scar, a latent constraint.
- **Marker debt:** 28 later scars carry no `SCAR-` string in code and no `@pytest.mark.scar`; `pytest -m scar` and radar-unguarded-scars undercount. `RESOLVED_SCAR_IDS` (`tests/unit/knowledge/register_drift_checks.py:36`) holds 2 IDs while at least 7 scars are resolved.
- **Legacy descriptions missing** for SCAR-001/002/003/007/009/012/016-019/021/024/025/030; no `git log -S` archaeology was done (time-boxed).
- **Not re-read this pass** (existence confirmed by manifest, content not read): `.ledge/` DEFECT and SOAK records cited as evidence; most regression test bodies other than the API-hardening and metrics ones; `.dockerignore` content beyond the commit diffs; the `.github/workflows/gitleaks.yml` and `.gitleaksignore` contents (a credential-name floor applies to the latter's neighbors; only commit-message descriptions were used, and no values are transcribed here).
- **Operator-state scars not repo-verifiable:** AL-5 and alarm apply status; SEC-001 allowlist population; whether autom8y-log 0.7.x ships a stdlib shim (SCAR-LOG-001); `terraform apply` state.
- **Candidates:** SCAR-CANDIDATE-PLAY-CONSUMED-TRIGGER (`mcp/asana_mcp/tools/workflows.py:20`) and SCAR-CANDIDATE-OPTFIELDS remain at N=1; OPTFIELDS has a corroborating site class in TASKCACHE-PHE-001 [KNOW-CANDIDATE?]. The new class "documented control silently inert or mis-ordered" (7 above, N=6) is a promotion candidate under the scar-tissue-promotion discipline [KNOW-CANDIDATE].
- **Not searched:** `terraform/` beyond the alarm file, `docs/`, `runbooks/`, workflows other than the three named; the pre-2026-07 `fix` tail of the 503 subjects was not re-triaged.
- **Not read by design:** floored credential and env files (an operator's act); the root mise config symlink (3a-bis); no outward calls (no `gh`, `aws`, fetch) were made, so PR numbers come from commit subjects only and PR review threads are unobserved.
