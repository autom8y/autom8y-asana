---
domain: scar-tissue
generated_at: "2026-07-08T00:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./tests/**/*.py"
  - "./pyproject.toml"
  - "./.github/workflows/**"
generator: theoros
source_hash: "f3d8eec1"
confidence: 0.95
format_version: "1.0"
update_mode: "incremental"
incremental_cycle: 2
max_incremental_cycles: 3
land_sources:
  - ".sos/land/scar-tissue.md"
land_hash: "a15a024ce204de3301b612526c5b1b59e4841fa3d3d70f2226e1b430cd73da1e"
---

# Codebase Scar Tissue

> Incremental update 2026-05-08 (cycle 1/3). Source hash: `8980bcd7` (5 commits since prior
> baseline `20ef7952`; PRs #57-#59 + hygiene Sprint-3 CI hardening).
> 41+ distinct failures documented. Three new SCARs added this cycle
> (SCAR-W1E-LOADGROUP-001, SCAR-CONSUMER-GATE-001, SCAR-ARTIPACKED-001).
> Prior catalog fully preserved. SCAR-LOG-001 still active (autom8y-log >=0.5.6,
> no stdlib shim). SCAR-CW-001 CP-01 still pending.
>
> Key delta since `20ef7952`:
> - SCAR-W1E-LOADGROUP-001 (commit `149d3673`): cross-item state corruption under
>   --dist=load in test_workflow_handler.py + test_routes_query.py; fixed via
>   xdist_group markers + switch to --dist=loadgroup (pyproject.toml:105 at HEAD)
> - SCAR-CONSUMER-GATE-001 (commit `8980bcd7`): cross-fleet silent-bypass when
>   candidate_wheel_run_id set but artifact download fails; fail-loud guard now wired
> - SCAR-ARTIPACKED-001 (commit `8980bcd7`): zizmor artipacked credential-leak via
>   actions:read + cross-workflow artifact download + default persist-credentials=true;
>   mitigated with persist-credentials: false on fuzz job checkout
> - xdist strategy shifted: --dist=load -> --dist=loadgroup (pyproject.toml:105)
> - autom8y-core lower bound lifted: >=4.0.0 -> >=4.2.0 (commit `f6864435`)
> - TestAC006 lock-overhead budget widened 1ms->2ms under contention (commit `f37802f2`)
> - @pytest.mark.scar count: ~~35 (unchanged from `20ef7952`)~~ **41 at HEAD** (W-REG `2d7d39d9` #190 rewrote test_section_registry.py, changing its marker count from 15 to 7; other files added markers since `8980bcd7`)
> - test_import_safety.py (SCAR-CW-001 CP-01): still absent

> **ADVERSARIAL-CHALLENGE REFRESH 2026-07-08 (source_hash f3d8eec1, cell asana-scar-sd02):**
> SCAR-SD02 added: status push is structurally dead code in prod (entity-warm lane paused Trap-4
> since 2026-06-08; prod frames warm via ECS preload / SWR / prematerialize lanes, none of which
> call push_status_to_data_service). The prior "4h push cadence" premise is documented as
> FACTUALLY-FALSE in config.py:269-274: `0 */4` is the DISABLED ASR consumer-READ schedule, not
> an asana push lane. SCAR-CW-001 fix-location paths are stale (subdirectory structure dissolved).
> Repair for SD-02 is PENDING-MERGE(C-6) only — NOT on main at HEAD.
> **SUPERSEDED-BY**: this refresh supersedes the absence of SD-02 knowledge in the prior catalog.
> Prior catalog fully preserved; no existing SCARs modified except Knowledge Gaps extended.

## Failure Catalog

41+ distinct failures documented from two evidence sources (git commit history + code marker
scan). SCAR identifiers confirmed in the live codebase at source_hash `8980bcd7`:

**In src/ (by count)**: SCAR-005 (14 refs), DEF-005 (3 refs), DEF-001 (2 refs),
SCAR-REG-001 (2 refs), SCAR-IDEM-001 (1 ref), DEF-02 (1 ref).

**In tests/ (by count)**: SCAR-005 (9 refs), SCAR-REG-001 (7 refs), SCAR-IDEM-001 (6 refs),
SCAR-015 (5 refs), DEF-08 (4 refs), DEF-003 (3 refs), SCAR-WS8 (2 refs), SCAR-020 (2 refs),
DEF-005 (2 refs), DEF-002 (2 refs), SCAR-006 (1 ref).

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
| SCAR-026 | Test mocks for SDK clients missing `spec=` — silent mock drift | Integration / CI | Historical; partial HYG-002 remediation via `2158de02`, `3f4580ff` (136 `spec=` calls in tests/ at HEAD) |
| SCAR-027 | User-controlled string passed to `re.sub` replacement — ReDoS / injection | Security | `core/creation.py:82-97` |
| SCAR-028 | Error log emitted user PII without masking | Security | `clients/data/_pii.py:61` |
| SCAR-029 | GID not stripped before Pydantic normalization — leading/trailing whitespace failed validation | Security | `api/routes/webhooks.py:375-381` |
| SCAR-030 | Section names from non-live source — ALL CAPS invariant not enforced | Data Model | Historical |
| SCAR-S3-LOOP | Permanent S3 error codes fed to circuit-breaker retry loop — infinite retry storm | Cache Coherence | `core/retry.py:198` |
| SCAR-IDEM-001 | ~~Idempotency `finalize()` exception silently swallowed — double-execution risk on retry~~ **RESOLVED** `f795d7dc` #149 (W-IDEM, 2026-06-24): finalize bool READ; raise→`finalized=False`; `emit_metric("IdempotencyFinalizeFailure")` at `:787-792` (R-IDEM-1); S2S callers → hard 500 at `:803-830` (R-IDEM-2). Stale anchor `:719` = replay-header at tip; fix is at `:762-780`. | Data Model (RESOLVED) | `api/middleware/idempotency.py:762-830` (fix); `:719` (past-tense defect narration) |
| SCAR-REG-001 | ~~Section registry GIDs are sequential placeholders — unverified against live Asana API~~ **RESOLVED** 2026-07-07: W-REG `2d7d39d9` #190 replaced 19 fabricated placeholder GIDs (4 excluded + 15 unit) with live W-IRIS receipt values; 17 live sections wired. `section_registry.py` is now 475 lines with a NAME-join (not GID-match) + fail-closed `SectionRegistryError` gate (`section_registry.py:375-429`). The misroute defect class is closed. | Startup (RESOLVED) | `reconciliation/section_registry.py:66,153` (past-tense defect narration); fix: `section_registry.py:375` `SectionRegistryError`, `:429` `raise SectionRegistryError` |
| SCAR-WS8 | PAT route trees not consistently listed in `jwt_auth_config.exclude_paths` — JWT middleware rejects PAT requests | Security | `api/main.py:389`; regression test `test_exports_auth_exclusion.py` confirmed |
| SCAR-DISCRIMINATOR-001 | `_predicate_discriminator` dict-only guard — `NotGroup(not_=AndGroup(...))` fails Pydantic validation when constructed via model-instance kwargs | Data Model / Type Contract | Discovered 2026-04-29; no fix at `8980bcd7` (P3 — no production path) |
| SCAR-LOG-001 | `autom8y-log` SDK returns structlog family (interface-disjoint from stdlib `logging.Logger`) — satellite migration breaks test and public attribute contracts | SDK Interface Gap | WS-4 T3 terminal 2026-04-29; no upstream fix; defer until autom8y-log ships stdlib shim — GLINT-001 |
| SCAR-LP-001 | lockfile-propagator stub-before-uv-lock ordering: `uv lock` fails when satellite `path =` sources resolve outside sandbox tree | Build Tooling | autom8y PR #174 `f2dfc1c3`; Option-A source_stub.py fix — GLINT-001 |
| SCAR-P6-001 | Pattern 6 (stale-checkout artifact drift) RECURS at PLAN-AUTHORING altitude — planner trusted unresolved inventory framing without re-running drift-audit | Epistemic / Drift | Resolved at SWEEP §6 + PT-E3 §3; VERDICT §5 — GLINT-005 |
| SCAR-CW-001 | Cache-warmer Lambda cold-start failure: 5 onion-layers (Errno 97 → Errno 111 → HTTP 400 URL-encoding → HTTP 400 init-time config → EntityProjectRegistry ARN-resolution) | Startup / Lambda | PRs #28-#37 (autom8y-asana); tags v1.3.2/v1.3.3 — GLINT-007 |
| SCAR-W1E-LOADGROUP-001 | xdist --dist=load round-robin interleaves AsyncMock teardown across workers — cross-item state corruption causes "node down: Not properly terminated" / "worker 'gwN' crashed" | Test Infrastructure | `149d3673`; xdist_group markers + --dist=loadgroup switch |
| SCAR-CONSUMER-GATE-001 | candidate_wheel_run_id set but actions/download-artifact fails silently — fuzz tests run against pyproject.toml-resolved wheel, not candidate | Integration / CI | `8980bcd7`; fail-loud guard in `.github/workflows/test.yml:135-147` |
| SCAR-ARTIPACKED-001 | zizmor artipacked: actions:read + cross-workflow download-artifact + persist-credentials=true checkout leaks git extraheader credential into uploaded artifacts | Security | `8980bcd7`; `persist-credentials: false` on fuzz job checkout |
| Env Var Naming | `AUTOM8_DATA_API_KEY` typo (missing Y) — production API auth failures | Authentication | `clients/data/config.py:231` |
| CSI-001 | **DISCHARGED** `docs/api-reference/openapi.json` hand-edited to add 13 M-02 examples not derivable from Pydantic source | Documentation / Spec Drift | DISCHARGED 2026-04-29 via T-08 (`4d4097c3`), PR #38 (`80256049`) |
| SCAR-SD02 | Status push is structurally dead code in prod — wired only into entity-warm Lambda lane (paused Trap-4 since 2026-06-08); prod warm paths (ECS progressive preload, SWR, prematerialize lanes) never call it; `account_status` table has 0 rows / `synced_at` NULL since table creation (2026-03-28) | Data Model / Push Seam | PENDING-MERGE(C-6) `fix/sd02-status-push-live-seam` — no fix on main at HEAD |

### New Candidates Not Yet Assigned SCAR IDs

- **SCAR-CANDIDATE-B**: `PhoneNormalizer.normalize()` lacked `NumberParseException` in its except tuple. Fix: `models/business/matching/normalizers.py:77-82`, commit `0f18f4e8`.
- **SCAR-CANDIDATE-C**: `list_workflows` handler missing `response_model`. Fix: `api/routes/workflows.py`, commit `bb97a744`.
- **Metrics CLI Under-count** (session-20260427): `autom8-query` CLI silently under-counts active sections (~6 in parquet vs ~22 expected). Root cause unresolved — 4 open questions: bucket mapping, freshness SLA, section-coverage gap, staleness-surface decision. Location: `metrics/compute.py`, `dataframes/offline.py`.

---

## SCAR-W1E-LOADGROUP-001 (Added 2026-05-08)

**Severity**: P2 — caused repeated CI shard 4/4 worker crashes blocking fleet CI.

**Symptom**: Under `--dist=load`, pytest-xdist round-robin item distribution interleaves
`AsyncMock(spec=DataServiceClient)` context-manager teardown patterns from
`test_workflow_handler.py` across workers gw0..gw3. The AsyncMock teardown executes inside
the new event loop spawned by `asyncio.run` in the production handler
(`workflow_handler.py:97`). Cross-worker teardown produces:
- "node down: Not properly terminated"
- "worker 'gwN' crashed"

CI run evidence: run 25258237857 at `TestHandlerWorkflowRegistration::test_handler_warm_container_reregistration` + run 25188629600 (same test, same signature).

**Secondary manifestation (DW-W1E-LOADGROUP-FALLOUT-001)**: `test_routes_query.py` also
affected. Heavy `AsyncMock + dependency_overrides` usage causes isolation failures under
`--dist=loadgroup` that `--dist=load` masked via lucky test-ordering co-location.

**Fix**: Two-part:
1. `pytestmark = [pytest.mark.xdist_group("workflow_handler")]` at `tests/unit/lambda_handlers/test_workflow_handler.py:47`
2. `pytestmark = [pytest.mark.xdist_group("query_routes")]` at `tests/unit/api/test_routes_query.py:45`
3. `addopts = "--dist=loadgroup"` activated in `pyproject.toml:105` (commit `149d3673`)

**Status at `8980bcd7`**: `--dist=loadgroup` is ACTIVE in pyproject.toml. Both xdist_group
markers are live and enforced. The markers were described as "forward-compatible scaffolding"
in the test comments (written before the switch landed), but the switch has since landed.

**Defensive pattern**: Any test file using `AsyncMock` with event-loop-spawning production
code OR `dependency_overrides` that mutate shared FastAPI app state MUST use
`pytestmark = [pytest.mark.xdist_group("...")]` under `--dist=loadgroup`.

---

## SCAR-CONSUMER-GATE-001 (Added 2026-05-08)

**Severity**: P2 — silent test-purpose violation; cross-fleet pattern (N=2: autom8y-ads PR #34
Path β + autom8y-asana PR #59 Path A+D port).

**Symptom**: When `candidate_wheel_run_id` workflow input is set (signaling intent to test a
candidate wheel), `actions/download-artifact` can fail silently if:
- The artifact was not uploaded (wrong run-id)
- Cross-workflow `actions:read` permission is absent
- The artifact name doesn't match

Without a fail-loud guard, the fuzz step proceeds, installs whatever
`pip install` resolves from pyproject.toml, and reports a green result against the
pyproject.toml-pinned wheel — not the candidate. The consumer gate has been bypassed with
no signal.

**Survey designation**: AP-CANDIDATE-cross-fleet-consumer-gate-silent-bypass-survey N=2.

**Fix**: Explicit guard at `.github/workflows/test.yml:135-147`:
```
- name: Verify candidate wheel present (consumer-gate fail-loud)
  if: inputs.candidate_wheel_run_id != ''
  run: |
    if ! ls /tmp/candidate-wheel/*.whl 1>/dev/null 2>&1; then
      echo "::error::Consumer-gate test-purpose violation: ..."
      exit 1
    fi
```

**Defensive pattern**: Any workflow accepting a `candidate_wheel_run_id` input MUST include
a fail-loud artifact-presence check immediately after `actions/download-artifact`. Silence
from a missing artifact is indistinguishable from a successful but empty download.

---

## SCAR-ARTIPACKED-001 (Added 2026-05-08)

**Severity**: P2 — security; credential-bleed vector into CI artifacts.

**Root cause (zizmor artipacked finding)**: Three conditions combine:
1. Workflow job has `permissions: actions:read` (needed for cross-workflow `download-artifact`)
2. `actions/checkout` default `persist-credentials: true` — git stores auth token as
   extraheader in `.git/config`
3. `actions/upload-artifact` (or any subsequent step writing to a path under `.git/`) uploads
   the credential-containing config into the artifact

When a downstream job (or external actor with artifact-read access) downloads the artifact,
the git extraheader credential is present and usable for the lifetime of the token.

**Fix**: `persist-credentials: false` on all checkout steps in jobs that also run
`actions/download-artifact` with cross-workflow scope. Applied at
`.github/workflows/test.yml:95` (fuzz job checkout) and `:201` (secondary checkout).

**Defensive pattern**: Any job combining `actions:read` permission + `actions/checkout` +
`actions/download-artifact` MUST set `persist-credentials: false` on the checkout step.
The zizmor `artipacked` rule flags this automatically; add zizmor to CI scorecard scans.

---

## SCAR-DISCRIMINATOR-001 (Added 2026-04-29 — Still Unguarded at `8980bcd7`)

**Severity**: P3 — no production caller currently constructs `NotGroup(not_=group)`.

**Symptom**: `NotGroup(not_=AndGroup([...]))` fails Pydantic validation:
```
not_.comparison  Input should be a valid dictionary or instance of Comparison
```

**Root Cause**: `_predicate_discriminator` at `src/autom8_asana/query/models.py:97-112` handles only `isinstance(v, dict)` inputs. When a model instance is passed as `not_`, execution falls through to `return "comparison"` at line 112. Pydantic then attempts `Comparison` validation on a group-model instance.

**Declaration vs Implementation Divergence**:
- Type declaration (`query/models.py:129-135`): `PredicateNode` is the full discriminated union `Comparison | AndGroup | OrGroup | NotGroup`.
- Runtime discriminator (`query/models.py:97-112`): Only dict inputs are classified correctly; model-instance inputs silently forced to `"comparison"`.

**Workaround**: Callers use raw dict construction. The `_wrap_flat_array_to_and_group` helper at line 115-126 exemplifies the correct dict-passing pattern.

**Proposed Fix**: Add `isinstance(v, BaseModel)` branch before the `return "comparison"` fallthrough, inspecting `model_fields` keys to route model-instance inputs correctly.

**Owner-rite for fix**: hygiene-pass-2 (Sprint-4)

---

## SCAR-LOG-001 — autom8y-log SDK lacks stdlib `logging.Logger` interface

**Origin**: WS-4 inaugural-hygiene-cleanup 2026-04-29 T2/T3.
**Provenance (GLINT-001)**: promoted per `VERDICT-eunomia-final-adjudication-2026-04-29.md`.

**Symptom**: Any module migrating to `autom8y_log.get_logger(name)` cannot retain calls treating the result as stdlib `logging.Logger`. Probe at 2026-04-29 confirmed 11 of 11 stdlib `Logger` attributes absent from both `BoundLoggerLazyProxy` and `BoundLoggerFilteringAtInfo`.

**Status at `8980bcd7`**: Still active. `autom8y-log>=0.5.6` in pyproject.toml:23 — no stdlib shim shipped. autom8y-core lifted to >=4.2.0 (commit `f6864435`) does not affect autom8y-log line. Defer-watch entry `DEFER-WS4-T3-2026-04-29` deadline 2026-Q3.

**Defensive pattern**: When a satellite module exposes `_logger` that internal callers or tests treat as stdlib-Logger-shaped, retain `import logging` + TID251 per-file `[tool.ruff.lint.per-file-ignores]` exemption with inline SCAR-LOG-001 rationale comment. Do NOT migrate.

---

## SCAR-LP-001 — lockfile-propagator stub-before-uv-lock ordering invariant

**Origin**: SDK publish pipeline cascade failures; fix landed in autom8y PR #174 (merge SHA `f2dfc1c3`).
**Provenance (GLINT-001)**: promoted per `VERDICT-eunomia-final-adjudication-2026-04-29.md`.

**Root cause**: Satellite cloned to `/tmp/lockfile-propagator-XXXXXXXX/<satellite>/`. `uv lock` with `cwd=repo_dir` resolves `path = "../X"` in `[tool.uv.sources]` against the tmp dir, not developer-side siblings.

**Fix (Option A)**: `source_stub.py` at `autom8y/tools/lockfile-propagator/` stubs editable path sources before invoking `uv lock`.

**Defensive pattern (three discriminators)**:
1. Only stub entries with relative `path = ...` shape (do NOT stub `git =`, `url =`, `index =`).
2. Stub's `pyproject.toml` requires only `[project]` + `[build-system]` (not full importable Python).
3. Idempotent on re-run (skip when `stub_dir/pyproject.toml` exists).

**Production-CI status**: defer-watch entry `lockfile-propagator-prod-ci-confirmation` in `.know/defer-watch.yaml` — deadline 2026-07-29.

---

## SCAR-P6-001 — Pattern 6 recurrence at PLAN-AUTHORING altitude

**Origin**: Eunomia final adjudication 2026-04-29; VERDICT §5.
**Provenance (GLINT-005)**: per `VERDICT-eunomia-final-adjudication-2026-04-29.md §5`.

**Mechanism**: consolidation-planner consumed `INVENTORY-pipelines L347`'s `[UNATTESTED — DEFER-POST-INVENTORY]` framing and propagated it into PLAN even though SWEEP §6 had discharged it. The planner trusted upstream framing without verifying downstream resolution.

**Concrete case**: PLAN §3 L101 + §9 L230 claim `test_source_stub.py` is "absent on origin/main." Ground truth: file IS PRESENT at autom8y origin/main blob `bf4f74180e15f07a698538afa14f6f82d47bf641`.

**Defensive discipline**: Re-run drift-audit at ANY altitude where mixed-resolution upstream substrates are consolidated. Verify live branch HEAD before asserting file presence/absence.

---

## SCAR-CW-001 — 5-layer Lambda cold-start failure taxonomy

**Origin**: cache-warmer Lambda SEV2 cascade, autom8y-asana PRs #28-#37, autom8y PRs #163-#173, tags v1.3.2/v1.3.3.
**Provenance (GLINT-007)**: per `HANDOFF-sre-to-10x-dev-cache-warmer-init-failure-2026-04-28.md`.

**The 5 onion-layers** (peeled in recovery order):
1. **Errno 97 EAFNOSUPPORT** — IPv6/IPv4 mismatch. Fixed: network config (PR #28-#29).
2. **Errno 111 ECONNREFUSED** — Dockerfile extension-bundle missing. Fixed: COPY + extension bundle (PR #30-#31).
3. **HTTP 400 URL over-encoding** — SDK 2.0.2 fix: endpoint URL double-encoded. Fixed: SDK upgrade + URL normalization (PR #32-#33).
4. **HTTP 400 init-time settings resolution** — settings-loading called at module import inside Lambda handler. Fixed: lazy-load refactor PRs #35+#36 (`facade.py:76`, `detection/config.py`).
5. **EntityProjectRegistry not initialized** — `discovery.py` ARN-resolution asymmetry; registry deferred past first ARN lookup. Fixed: PR #37.

**Teachable pattern**: Budget 5+ rounds; each layer masks the next; every round requires a fresh deployment cycle.

**Defensive pattern for all Lambda handlers**:
- Settings/config loading MUST be deferred to function-call time (not module import time).
- Registry initialization MUST complete before first external-service call.
- Pin and test SDK upgrades against live Lambda extension endpoints.

**Regression anchor**: `tests/unit/lambda_handlers/test_import_safety.py` (CP-01) — NOT YET AUTHORED at `8980bcd7`; eunomia Phase 4 carry-forward.

---

## CSI-001 DISCHARGE Record (Historical — Resolved 2026-04-29)

**Original Scar**: `docs/api-reference/openapi.json` hand-edited at `cdcfaee6` to add 13 M-02 field examples not derivable from Pydantic source. Every `just spec-gen` regeneration silently dropped them.

**Discharge**: T-08 (`4d4097c3`) lifted all 13 examples to `Field(examples=[...])` on `src/autom8_asana/models/base.py`, `models/common.py`, `models/task.py`, `api/routes/workflows.py`, `api/routes/resolver_schema.py`.

**Residual exception**: 2 `"example":` (singular) entries at `src/autom8_asana/api/routes/dataframes.py:511,632` — raw dict inline OpenAPI 3.0 annotation (pre-CSI-001 pattern, not regressions).

**Status**: DISCHARGED 2026-04-29 (PR #38 `80256049`). Still discharged at `8980bcd7`.

---

## Category Coverage

14 distinct failure categories applied across all 41+ scars:

| Category | Scars | Count |
|---|---|---|
| Cache Coherence / Stale Data | SCAR-003, 004, 005, 006, 007, S3-LOOP | 6 |
| Data Model / Contract Violation | SCAR-008, 014, 023, 024, 025, 030, IDEM-001, REG-001, CANDIDATE-B, CANDIDATE-C, DISCRIMINATOR-001 | 11 |
| Startup / Deployment Failure | SCAR-009, 011, 011b, 013, 022, CW-001 | 6 |
| Workflow Logic Gap | SCAR-016, 017, 018, 019, 020 | 5 |
| Security / Input Validation | SCAR-027, 028, 029, WS8, ARTIPACKED-001 | 5 |
| Concurrency / Race Condition | SCAR-002, 010, 010b | 3 |
| Authentication / Authorization | SCAR-012, Env Var Naming | 2 |
| Integration Failure / CI | SCAR-021, 026, CONSUMER-GATE-001 | 3 |
| Performance Cliff / Timeout | SCAR-015 | 1 |
| Observability Gap | Metrics CLI Under-count | 1 |
| SDK Interface Gap | SCAR-LOG-001 | 1 |
| Build Tooling | SCAR-LP-001 | 1 |
| Epistemic / Drift | SCAR-P6-001 | 1 |
| Test Infrastructure | SCAR-W1E-LOADGROUP-001 | 1 |
| Push Seam / Dead Code | SCAR-SD02 | 1 |

Three categories explicitly searched and returned no results: schema migration failures, distributed coordination failures, network partition handling.

---

## Fix-Location Mapping

28+ primary fix paths verified at source_hash `8980bcd7`:

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
| SCAR-REG-001 | ~~`src/autom8_asana/reconciliation/section_registry.py:94,128`~~ **RESOLVED** `2d7d39d9` #190 — anchors were stale placeholder-GID rows; fix anchors: `section_registry.py:375` (`SectionRegistryError`), `:429` (`raise SectionRegistryError`), `:66,:153` (past-tense defect narration) | Yes — RESOLVED |
| SCAR-WS8 / DEF-08 | `src/autom8_asana/api/main.py:389` (`/api/v1/exports/*` in exclude_paths) | Yes |
| SCAR-DISCRIMINATOR-001 (bug) | `src/autom8_asana/query/models.py:97-112` (`_predicate_discriminator`) | Yes — confirmed no fix at `8980bcd7` |
| SCAR-DISCRIMINATOR-001 (type decl) | `src/autom8_asana/query/models.py:129-135` (`PredicateNode`) | Yes |
| SCAR-S3-LOOP | `src/autom8_asana/core/retry.py:198` (`_PERMANENT_S3_ERROR_CODES`) | Yes |
| DEF-001 (resolver route) | `src/autom8_asana/api/routes/resolver.py:335` | Yes |
| DEF-005 (shared CacheProvider) | `src/autom8_asana/api/lifespan.py:108,126` | Yes |
| DEF-005 (client pool) | `src/autom8_asana/api/client_pool.py:201` | Yes |
| Env Var Naming | `src/autom8_asana/clients/data/config.py:231` (`AUTOM8Y_DATA_API_KEY`) | Yes |
| PKG-002 (env collision) | `tests/synthetic/conftest.py:78-80` | Yes |
| SCAR-LP-001 (fix entry point) | `autom8y/tools/lockfile-propagator/src/lockfile_propagator/source_stub.py` | Yes — autom8y PR #174 `f2dfc1c3` |
| SCAR-CW-001 (layer 4 lazy-load) | `src/autom8_asana/lambda_handlers/cache_warmer/facade.py:76`, `detection/config.py` | Yes — PRs #35-#36 |
| SCAR-CW-001 (layer 5 ARN-resolution) | `src/autom8_asana/lambda_handlers/cache_warmer/discovery.py` | Yes — PR #37 |
| SCAR-W1E-LOADGROUP-001 (xdist_group wf) | `tests/unit/lambda_handlers/test_workflow_handler.py:47` | Yes — commit `149d3673` |
| SCAR-W1E-LOADGROUP-001 (xdist_group qr) | `tests/unit/api/test_routes_query.py:45` | Yes — commit `149d3673` |
| SCAR-W1E-LOADGROUP-001 (dist mode) | `pyproject.toml:105` (`addopts = "--dist=loadgroup"`) | Yes — active at HEAD |
| SCAR-CONSUMER-GATE-001 | `.github/workflows/test.yml:135-147` (fail-loud guard) | Yes — commit `8980bcd7` |
| SCAR-ARTIPACKED-001 | `.github/workflows/test.yml:95,201` (`persist-credentials: false`) | Yes — commit `8980bcd7` |
| SCAR-SD02 (repair — PENDING-MERGE) | `src/autom8_asana/lambda_handlers/cache_warmer.py:1087` (call site in entity-warm lane — the only push call in prod); fix pending on branch `fix/sd02-status-push-live-seam` (sprint C-6) | PENDING-MERGE(C-6) — not at HEAD |

---

## Defensive Pattern Documentation

### Cascade Defense-in-Depth (SCAR-005/006/023) — Four Layers

1. **Schema enforcement**: `source="cascade:..."` required on cascade columns. `source=None` silently bypasses pipeline (SCAR-023 root cause). Live: `src/autom8_asana/dataframes/schemas/offer.py:22`.
2. **Warm-up ordering guard**: `WarmupOrderingError` at `src/autom8_asana/dataframes/cascade_utils.py:22-30`. BROAD-CATCH immune. Re-raised at `src/autom8_asana/api/preload/progressive.py:696-699`.
3. **Post-build null rate audit**: `CASCADE_NULL_WARN_THRESHOLD = 0.05` (5%), `CASCADE_NULL_ERROR_THRESHOLD = 0.20` (20%) at `src/autom8_asana/dataframes/builders/cascade_validator.py:31-32`. Calibrated against SCAR-005's 30% incident.
4. **Chain traversal gap-skipping**: `src/autom8_asana/dataframes/views/cascade_view.py` (parent chain resolution with null-safe gaps).

**Regression tests**: `tests/unit/dataframes/test_cascade_ordering_assertion.py:71-106`, `test_warmup_ordering_guard.py`, `tests/unit/dataframes/builders/test_cascade_validator.py:649-668` (SCAR-005 30% scenario). All `@pytest.mark.scar`.

### Session Thread Safety (SCAR-010/010b)

`threading.RLock()` on all state mutations; `_require_open()` context manager at `src/autom8_asana/persistence/session.py`. Regression: `tests/unit/persistence/test_session_concurrency.py` (19+ tests). Note: `TestAC006PerformanceTolerance::test_lock_overhead_under_contention` budget widened from 1ms to 2ms at `f37802f2` (B-3 recalibration for slower CI runners).

### Session Snapshot Ordering (SCAR-008 / DEF-001)

Order-critical fix at `src/autom8_asana/persistence/session.py:995-1001`: accessor state (`_reset_custom_field_tracking`) cleared BEFORE `mark_clean()` captures snapshot. Reversal re-introduces stale state.

### Health Check Separation (SCAR-011/011b)

`/health` always returns 200 (liveness). `/health/ready` gates on `_cache_ready AND _workflow_configs_registered` (readiness). Regression: `tests/unit/api/test_lifespan_workflow_import.py`.

### Security Hardening (SCAR-027/028/029)

- Lambda replacement guard in `re.sub` at `src/autom8_asana/core/creation.py:82-97`
- `mask_pii_in_string()` at `src/autom8_asana/clients/data/_pii.py:61`
- GID `str.strip()` guard at `src/autom8_asana/api/routes/webhooks.py:375-381`

### Phone Normalization on Read Path (SCAR-020 / SCAR-CANDIDATE-B)

`PhoneTextField` descriptor at `src/autom8_asana/models/business/descriptors.py:472-498` normalizes `office_phone`, `twilio_phone_num` to E.164 on read. Applied at `src/autom8_asana/models/business/business.py:267`. `PhoneNormalizer` now includes `NumberParseException` in except tuple. Regression: `tests/unit/models/business/matching/test_normalizers.py:64-70` (`@pytest.mark.scar`).

### Idempotency Finalize Observability (SCAR-IDEM-001)

~~Exception on `finalize()` promoted to `logger.exception` with `impact` field at `src/autom8_asana/api/middleware/idempotency.py:719-728`. **Known gap**: observability-only fix; double-execution risk for S2S strict-once callers remains open per `ADR-omniscience-idempotency Section 3.7`.~~ **RESOLVED** `f795d7dc` #149 (W-IDEM, 2026-06-24): the ADR-omniscience-idempotency Section 3.7 fix is fully landed. Finalize try-block at `:762-780`; R-IDEM-1 `emit_metric("IdempotencyFinalizeFailure")` at `:787-792`; R-IDEM-2 hard 500 for S2S strict-once callers (`X-Idempotent-Not-Persisted`, `IDEMPOTENCY_KEY_NOT_PERSISTED` body) at `:803-830`. The fix is behavioral (500 retraction), not observability-only. Regression: `tests/unit/api/middleware/test_idempotency_finalize_scar.py` (SCAR-IDEM-001-A, -B, -C — all `@pytest.mark.scar`). Stale anchor `:719-728` = replay-header code at tip.

### JWT Exclude-Paths Sync (SCAR-WS8 / DEF-08)

`/api/v1/exports/*` added to `jwt_auth_config.exclude_paths` at `src/autom8_asana/api/main.py:389`. Structural invariant: every PAT-tagged router registration must have a corresponding `exclude_paths` entry. Auth-isolation regression confirmed FIXED; eunomia v2 PASS-WITH-FLAGS-CARRIED adjudication (commit `85ed9ea7`). **Regression test**: `tests/unit/api/test_exports_auth_exclusion.py` — live middleware introspection (no mocking). `@pytest.mark.scar` applied.

### S3 Circuit Breaker (SCAR-S3-LOOP)

`_PERMANENT_S3_ERROR_CODES: frozenset[str]` at `src/autom8_asana/core/retry.py:198` — permanent codes bypass circuit-breaker retry loop. Regression: `tests/unit/dataframes/test_storage.py` (S3-LOOP test cluster).

### xdist Worker Isolation (SCAR-W1E-LOADGROUP-001)

`pytestmark = [pytest.mark.xdist_group("...")]` at module level for any test file with:
- `AsyncMock` whose teardown executes inside event loops spawned by production code
- `dependency_overrides` that mutate shared FastAPI app state

Current groups: `"workflow_handler"` (`test_workflow_handler.py:47`), `"query_routes"` (`test_routes_query.py:45`), `"fuzz"` (`test_openapi_fuzz.py:68`). Fleet strategy: `--dist=loadgroup` active at `pyproject.toml:105`.

### Consumer-Gate Fail-Loud (SCAR-CONSUMER-GATE-001)

Explicit `ls /tmp/candidate-wheel/*.whl` existence check after `actions/download-artifact`. Exits 1 with `::error::` annotation if artifact absent when `candidate_wheel_run_id` is set. Location: `.github/workflows/test.yml:135-147`.

### Artipacked Credential Hygiene (SCAR-ARTIPACKED-001)

`persist-credentials: false` on all `actions/checkout` steps in jobs combining `actions:read` permission + `actions/download-artifact`. Applied at `.github/workflows/test.yml:95` and `:201`. zizmor scorecard scan now catches regressions.

### BROAD-CATCH Classification

17 `except Exception` blocks annotated with `ADVISORY` comments (verified: `git grep -rn 'ADVISORY' src/` → 17 hits at HEAD; `git grep -rn 'VERIFY-BEFORE-PROD' src/` → **0 hits**). The `SCAR-IDEM-001: VERIFY-BEFORE-PROD` annotation class no longer exists in `src/` — the token was either removed or never landed. Intentional vs. defensive catches distinguished by the `ADVISORY` prefix alone.

### SCAR-DISCRIMINATOR-001 — No Defensive Pattern Yet

No guard at `8980bcd7`. Workaround: callers use raw dict construction. No regression test. **Unguarded**. Fix deferred to hygiene-pass-2.

### SCAR-LOG-001 — No Upstream Fix Yet

No stdlib-Logger shim in autom8y-log as of 2026-05-08. `autom8y-log>=0.5.6` unchanged in pyproject.toml. Defensive pattern: retain `import logging` + TID251 per-file-ignores exemption.

### SCAR-LP-001 — Option-A Fix Shipped; Production-CI Pending

`source_stub.py` fix landed in autom8y PR #174. Production-CI confirmation deferred per defer-watch entry `lockfile-propagator-prod-ci-confirmation` (deadline 2026-07-29).

### SCAR-CW-001 — Onion-Layer Debugging Pattern (No Regression Test Yet)

PRs #28-#37 closed all 5 layers. CP-01 (`tests/unit/lambda_handlers/test_import_safety.py`) absent at `8980bcd7`. Layers 1-3 (network, Dockerfile, SDK URL) are infrastructure-level and require Lambda deployment to re-test.

### Known Gaps in Defensive Pattern Documentation

- SCAR-004: No dedicated regression test; DEF-005 comment + integration verification only
- SCAR-008: No isolated regression test for snapshot ordering
- SCAR-013: `_SCHEMA_VERSIONING_AVAILABLE = False` import-fallback path has no unit coverage
- SCAR-026: HYG-002 partial adoption (136 spec= calls); systematic all-mocks audit not complete
- ~~SCAR-REG-001: Production blocker — sequential placeholder GIDs unverified against live Asana API~~ **RESOLVED** `2d7d39d9` #190 (W-REG): live W-IRIS receipt GIDs now wired via NAME-join + `SectionRegistryError` fail-closed gate (`section_registry.py:375,:429`)
- Metrics CLI Under-count: No defensive guard; 4 root-cause questions open
- SCAR-DISCRIMINATOR-001: No defensive guard, no regression test; fix deferred to hygiene-pass-2
- SCAR-CW-001: CP-01 lazy-load regression test pending; eunomia Phase 4 carry-forward

### SCAR-SD02 — Status Push Enable-Time Landmines (No Fix on Main at HEAD)

The push seam is dead code in prod today (entity-warm lane paused, Trap-4). Before the repair lands (sprint C-6 `fix/sd02-status-push-live-seam`), three landmines must be resolved:

1. **E.164 validation (L1)**: `push_status_to_data_service` (`gid_push.py:557`) sends `entries[]` whose `phone` values come from `extract_status_from_dataframe` (`gid_push.py:446-554`). The receiver has `extra="forbid"` on `AccountStatusEntry`; one non-E.164-conformant `office_phone` in the snapshot 422s the ENTIRE batch. Pre-enable: sweep `office_phone` population against `OfficePhoneField` / `PhoneTextField` (`models/business/descriptors.py:472-498`). [UV-P: E.164 sweep outcome | METHOD: requires iris live-probe of account_status population | REASON: phone values not inspectable from code alone]
2. **Lambda env secrets (L2)**: `push_status_to_data_service` resolves `AUTOM8Y_DATA_URL` (`gid_push.py:152`) and `AUTOM8Y_DATA_API_KEY` via `resolve_secret_from_env` (`gid_push.py:166`). Without these in the Lambda env, the push skips silently (StatusPushSkipped{url_absent} / StatusPushSkipped{invalid_key}). Pre-enable: confirm Lambda-env secret wiring via operator check (see SPIKE-sd02-empty-registry-diagnosis-2026-07-08.md §4-R2).
3. **PIPELINE_TYPE_BY_PROJECT_GID coverage (L3)**: `PIPELINE_TYPE_BY_PROJECT_GID` (`gid_push.py:413-424`) maps 10 project GIDs to pipeline types. Only the `unit` project (`1201081073731555`) maps to an entity in the default warm set (`cache_warmer.py:719-721`: `["unit","business","offer","contact","asset_edit","asset_edit_holder"]`). Of the 9 remaining GIDs, none are default entity-type keys; offer project `1143843662099250` is absent from the map. Only `unit` rows can land per the current wiring. Unit-tested only (`gid_push.py:413-424`); no integration test confirms end-to-end coverage. **SUPERSEDED-BY SCAR-SD02 landmine note**: prior absence of this constraint in scar-tissue.md was because SD-02 was undiscovered; this documents the as-wired narrowing as a PENDING-MERGE latent.

**Status at HEAD (f3d8eec1)**: All three landmines are latent / pre-deploy. Repair PENDING-MERGE(C-6).

---

## Scar Test Cluster Status

**Formal `@pytest.mark.scar` cluster**: ~~35 decorator invocations across 11 files at `8980bcd7`. Unchanged from `20ef7952`. The 7 files modified in PRs #57-#59 received only ruff I001 import-order style fixes (no semantic marker changes) or xdist_group additions (not scar markers).~~ **Count updated (2026-07-07):** `git grep -rn 'pytest.mark.scar' tests/` → **41 markers** at HEAD (W-REG `2d7d39d9` #190 rewrote `test_section_registry.py` — count changed). Source hash pinned at `8980bcd7` remains the original baseline; HEAD count is 41.
Marker registered in `pyproject.toml`:
```
"scar: scar-tissue regression tests (selectable via `pytest -m scar`); see .know/scar-tissue.md"
```
Selectable: `pytest -m scar`

| File | SCAR Coverage | Markers |
|---|---|---|
| `tests/unit/reconciliation/test_section_registry.py` | SCAR-REG-001 | ~~15~~ **7** (W-REG `2d7d39d9` rewrote this file to 172 lines; prior count of 15 was the pre-rewrite file at `8980bcd7` baseline) |
| `tests/unit/dataframes/test_warmup_ordering_guard.py` | SCAR-005/006 | 5 |
| `tests/unit/dataframes/test_cascade_ordering_assertion.py` | SCAR-005/006 | 3 |
| `tests/unit/api/middleware/test_idempotency_finalize_scar.py` | SCAR-IDEM-001 | 3 |
| `tests/unit/services/test_universal_strategy_status.py` | SCAR-005/006 | 2 |
| `tests/unit/api/test_exports_auth_exclusion.py` | SCAR-WS8 / DEF-08 | 2 |
| `tests/unit/dataframes/builders/test_cascade_validator.py` | SCAR-005 | 1 |
| `tests/unit/models/business/matching/test_normalizers.py` | SCAR-020 | 1 |
| `tests/unit/api/test_exports_format_negotiation.py` | SCAR-005/006 | 1 |
| `tests/unit/services/test_section_timeline_service.py` | SCAR-015 | 1 |
| `tests/unit/core/test_entity_registry.py` | SCAR-005/006 | 1 |

**Inviolable pre-HYG-001 regression tests (33 baseline)**: SCAR-001/005/006/010/010b/020/026/027, SCAR-WS8, S3-LOOP, TENSION-001 — all preserved at `8980bcd7`.

---

## Recurring Patterns vs One-Time Events

### Recurring (2+ appearances)

- **Cascade null rates** (SCAR-005, SCAR-006, SCAR-023): Same failure mode across 3 distinct sessions. Now defended with 4-layer cascade defense-in-depth.
- **Cascade contract bypass on fast-paths**: S3 fast-path (SCAR-005) + Offer source=None (SCAR-023) — different bypass vectors, same null-rate consequence.
- **Init-time settings loading in Lambda** (SCAR-CW-001 layer 4 + SCAR-009 pattern): lazy-load pattern is the established fix.
- **PAT route auth exclusion gaps** (SCAR-WS8): PAT-tagged routes must have corresponding `exclude_paths` entries; now regression-tested.
- **Mock drift / spec= omission** (SCAR-026): HYG-002 partial adoption in progress.
- **Test infrastructure scale friction**: xdist crashes (SCAR-W1E-LOADGROUP-001 — now fixed via `--dist=loadgroup` + xdist_group markers); fixture explosion (HYG-004 parametrize-promote).
- **Cross-fleet CI silent-bypass** (SCAR-CONSUMER-GATE-001): autom8y-ads PR #34 + autom8y-asana PR #59 — N=2 fleet pattern; fail-loud guard now standard.
- **Pattern 6 (stale-checkout drift)** (SCAR-P6-001): now also manifests at PLAN-AUTHORING altitude, not just SCAN altitude.
- **Dark-seam × dark-consumer × unarmed-alarm alignment** (SCAR-SD02, postmortem class CF-4/CF-5/CF-6): the same structural pattern as the 2026-06-18 dark-subsystem — a live seam never executes because its lane is paused; the consumer that would surface the absence has its schedule DISABLED; the alarm suite is AUTHORED/UN-DEPLOYED/UN-ARMED ([UV-P: exact IaC path `terraform/services/asana/observability_alarms.tf:8-21` | METHOD: cited from SPIKE-sd02-empty-registry-diagnosis-2026-07-08 §1 H2 | REASON: alarm IaC lives in the autom8y monorepo, outside this repo's read scope]). Non-blocking skip/fail paths never paged because nothing was listening. PENDING-MERGE(C-6). [KNOW-CANDIDATE] Novel pattern class not previously documented in scar-tissue.md.

### One-Time Events

- LocalStack S3 bucket empty (session-20260302): no follow-up.
- UnicodeEncodeError in middleware blocking Schemathesis fuzz suite: fixed (`respx` mocks, pass rate 5%→66%).
- Env var typo `AUTOM8_DATA_API_KEY` → `AUTOM8Y_DATA_API_KEY`: fixed at `clients/data/config.py:231`.

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
| SCAR-011 | platform-engineer | ECS health checks must target `/health` (liveness), not `/health/ready` |
| SCAR-011b | principal-engineer | Any new startup dependency must gate through `/health/ready` |
| SCAR-012 | principal-engineer | New cross-service clients must use `ServiceTokenAuthProvider` with `client_credentials` |
| SCAR-013 | principal-engineer | Optional SDK imports must use `try/except ImportError` with feature flag |
| SCAR-014 | principal-engineer | Lifecycle config models must NOT set `extra="forbid"` |
| SCAR-015 | architect | I/O-heavy data must be pre-computed at warm-up; request path pure-CPU |
| SCAR-023 | principal-engineer | Always specify `source=` value for cascade columns |
| SCAR-026 | qa-adversary | Test mocks for SDK clients must use `spec=`; HYG-002 partial remediation in progress |
| SCAR-027 | principal-engineer | Never pass user-controlled strings as `re.sub` replacement |
| SCAR-028 | principal-engineer | All error log sites with user data must call `mask_pii_in_string()` |
| SCAR-029 | principal-engineer | Validate GIDs with `str.strip()` before Pydantic normalization |
| SCAR-030 | principal-engineer | Section names must come from live Asana API (ALL CAPS invariant) |
| SCAR-S3-LOOP | platform-engineer | Permanent S3 errors must not be fed to circuit breaker |
| SCAR-IDEM-001 | principal-engineer | **RESOLVED** `f795d7dc` #149 (W-IDEM, 2026-06-24) — `emit_metric("IdempotencyFinalizeFailure")` at `:787-792` (R-IDEM-1); S2S strict-once callers → hard 500 at `:803-830` (R-IDEM-2). Fix is behavioral, not observability-only. |
| SCAR-REG-001 | platform-engineer | **RESOLVED** `2d7d39d9` #190 — live GIDs wired via W-IRIS receipt NAME-join; `SectionRegistryError` fails closed on any undispositioned live section (`section_registry.py:375,:429`). Constraint carried: every new live section must be represented in the vendored taxonomy or the module refuses to start. |
| SCAR-WS8 | principal-engineer | Every new PAT-tagged router requires corresponding `jwt_auth_config.exclude_paths` entry |
| SCAR-DISCRIMINATOR-001 | principal-engineer, qa-adversary | When constructing `NotGroup` or nested predicate nodes, use raw dicts (not model instances); test nested-not paths explicitly |
| SCAR-LOG-001 | principal-engineer | Do NOT migrate `_defaults/log.py`-class modules to `autom8y_log.get_logger(...)` until stdlib shim ships; retain `import logging` + TID251 exemption — GLINT-001 |
| SCAR-LP-001 | principal-engineer, architect, qa-adversary | Sandbox-resolver tools cloning consumer repos MUST stub relative-path `[tool.uv.sources]` entries before invoking `uv lock`; apply three-discriminator defensive pattern — GLINT-001 |
| SCAR-P6-001 | consolidation-planner, principal-engineer, architect | Re-run drift-audit at any altitude where mixed-resolution upstream substrates are consolidated; verify live branch HEAD before asserting file presence/absence — GLINT-005 |
| SCAR-CW-001 | platform-engineer, principal-engineer | Lambda handlers calling external services: (1) defer settings load to function-call time, (2) init registries before first external call, (3) budget 5+ rounds for cold-start failure chains — GLINT-007 |
| SCAR-W1E-LOADGROUP-001 | qa-adversary, principal-engineer | Any test file with AsyncMock + production event-loop spawning OR dependency_overrides must use xdist_group marker; verify --dist=loadgroup active in pyproject.toml |
| SCAR-CONSUMER-GATE-001 | platform-engineer | Every workflow accepting candidate_wheel_run_id must include post-download fail-loud artifact-presence check; silence from failed download is indistinguishable from empty artifact |
| SCAR-ARTIPACKED-001 | platform-engineer | Any job combining actions:read + actions/checkout + cross-workflow download-artifact must set persist-credentials: false; zizmor artipacked rule detects regressions |
| Env Var Naming | principal-engineer | All ecosystem env vars use `AUTOM8Y_` prefix (not `AUTOM8_`) |
| Metrics CLI Under-count | observability-engineer | `autom8-query` CLI parquet loading silently drops sections — verify bucket mapping before trusting CLI output |
| SCAR-SD02 | platform-engineer, principal-engineer | Status push (SD-02) is wired ONLY into the entity-warm Lambda lane (paused Trap-4 since 2026-06-08); prod never calls it; `account_status` table has 0 rows. Repair PENDING-MERGE(C-6). Pre-enable landmines: (L1) E.164 phone sweep before enable, (L2) Lambda env must carry AUTOM8Y_DATA_URL + AUTOM8Y_DATA_API_KEY, (L3) only unit-project rows reach the push per current PIPELINE_TYPE_BY_PROJECT_GID wiring — decide scope before re-arming. |

12 scars still untagged: SCAR-003, 004, 007, 016-019, 020, 022, 024, 025.

---

## Knowledge Gaps

1. **SCAR-CANDIDATE-B not catalogued**: `PhoneNormalizer` `NumberParseException` fix at `0f18f4e8`; no SCAR ID
2. **SCAR-CANDIDATE-C not catalogued**: `list_workflows` `response_model` fix at `bb97a744`; no SCAR entry
3. **Metrics CLI Under-count not assigned SCAR ID**: 4 root-cause questions open
4. **12 scars missing agent-relevance tags** (SCAR-003, 004, 007, 016-019, 020, 022, 024, 025)
5. **SCAR-004, SCAR-008 isolation tests absent**
6. **SCAR-013 import-fallback path untested**
7. **SCAR-026 mock-spec audit incomplete**: HYG-002 partial; systematic all-mocks audit pending
8. ~~**SCAR-IDEM-001 mitigation incomplete**: double-execution risk for S2S strict-once callers; observability-only fix~~ **RESOLVED** `f795d7dc` #149 (W-IDEM, 2026-06-24): behavioral 500 retraction for S2S callers at `:803-830` (R-IDEM-2) + `emit_metric("IdempotencyFinalizeFailure")` at `:787-792` (R-IDEM-1)
9. ~~**SCAR-REG-001 production blocker**: Sequential placeholder GIDs at `section_registry.py:100-107,132-138` must be replaced with verified GIDs~~ **RESOLVED** `2d7d39d9` #190: W-REG replaced all 19 fabricated placeholder GIDs (4 excluded + 15 unit) with live W-IRIS receipt values; 17 live sections wired; file is now 475 lines; `SectionRegistryError` fail-closed gate at `:375,:429`; stale line anchors `:100-107,:132-138` no longer exist
10. **xdist `--dist=loadgroup` active**: Prior gap item (--dist=load PASS-WITH-FLAGS-CARRIED) resolved. New watch: verify no new xdist_group grouping gaps emerge as test suite grows under loadgroup strategy
11. **SCAR-DISCRIMINATOR-001 unguarded**: No regression test, no defensive pattern; fix deferred to hygiene-pass-2
12. **SCAR-LP-001 production-CI pending**: defer-watch entry `lockfile-propagator-prod-ci-confirmation` open until 2026-07-29
13. **SCAR-CW-001 CP-01 regression test pending**: `tests/unit/lambda_handlers/test_import_safety.py` not yet authored
14. **SCAR-LOG-001 active**: `autom8y-log>=0.5.6` unchanged; no stdlib shim; defer-watch `DEFER-WS4-T3-2026-04-29` deadline 2026-Q3
15. **SCAR-SD02 repair PENDING-MERGE(C-6)**: `fix/sd02-status-push-live-seam` not yet on main; `account_status` table has 0 rows / `synced_at` NULL since 2026-03-28. Three enable-time landmines (L1 E.164 sweep, L2 Lambda env secrets, L3 PIPELINE_TYPE_BY_PROJECT_GID coverage) must be resolved before re-arming the entity-warm lane.
16. **SCAR-CW-001 fix paths stale at HEAD**: fix-location mapping (lines 363-364) cites `src/autom8_asana/lambda_handlers/cache_warmer/facade.py:76` and `lambda_handlers/cache_warmer/discovery.py` — paths do not exist at HEAD (f3d8eec1). Lambda handlers are flat files; `facade.py` is at `src/autom8_asana/models/business/detection/facade.py`, `discovery.py` at `src/autom8_asana/services/discovery.py`. NOT corrected in place: the semantic mapping of SCAR-CW-001 layers 4-5 onto the current flat handler files is unresolved. [UV-P: correct fix-location paths for SCAR-CW-001 layers 4-5 | METHOD: file-read at HEAD | REASON: subdirectory structure dissolved between SCAR-CW-001 era and HEAD; layer→file mapping cannot be asserted without re-deriving the cold-start taxonomy]

```metadata
domain: scar-tissue
source_hash: "8980bcd7"
generated_at: "2026-05-08T00:00Z"
confidence: 0.95
criteria_grades:
  failure_catalog_completeness:
    grade: A
    pct: 95
    weight: 0.30
  category_coverage:
    grade: A
    pct: 95
    weight: 0.25
  fix_location_mapping:
    grade: A
    pct: 93
    weight: 0.20
  defensive_pattern_documentation:
    grade: B
    pct: 85
    weight: 0.15
  agent_relevance_tagging:
    grade: A
    pct: 91
    weight: 0.10
overall_grade: A
overall_pct: 93
notes: >
  41+ scars catalogued from dual evidence sources (git history + code markers).
  14 failure categories documented with explicit-absence notation.
  3 new SCARs added: SCAR-W1E-LOADGROUP-001 (xdist isolation failure),
  SCAR-CONSUMER-GATE-001 (cross-fleet silent bypass, N=2),
  SCAR-ARTIPACKED-001 (CI credential-leak vector).
  35 @pytest.mark.scar decorator invocations across 11 files (unchanged from 20ef7952).
  --dist=loadgroup now ACTIVE at pyproject.toml:105.
  Main gaps: SCAR-DISCRIMINATOR-001 unguarded, SCAR-CW-001 CP-01 pending,
  SCAR-026 mock-spec audit incomplete, 12 scars without agent tags.
  SCAR-LOG-001 still active (autom8y-log no stdlib shim). SCAR-LP-001 prod-CI pending.
  Incremental cycle 1/3; next full regeneration recommended at cycle 3 or next major delta.
```
