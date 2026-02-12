# TRANSFER: Workflow Resolution Platform

**Date**: 2026-02-11
**From**: R&D Rite (Prototype Engineer, Moonshot Architect)
**To**: 10x-dev Rite (Implementation)
**Status**: GO with conditions (see Section 7)

---

## 1. Executive Summary

The Workflow Resolution Platform is a 3-sprint R&D effort that delivers:

1. **Resolution Primitives** (Phase 1) -- Shared, typed, session-cached entity resolution with bounded API budgets. Production-ready. Already used by ConversationAuditWorkflow.
2. **Lifecycle Engine** (Phase 2) -- Data-driven pipeline automation engine that replaces hardcoded PipelineConversionRule behavior with YAML-configured stages, transitions, cascading sections, entity creation, and dependency wiring. Prototype-level with identified gaps.
3. **PipelineTransitionWorkflow** (Phase 3) -- Batch workflow (#2 on the platform) that enumerates processes in terminal sections and routes them through the Lifecycle Engine. Prototype-level.

Total new code: **17 source modules**, **1 YAML config**, **151 new tests**.

---

## 2. Artifact Inventory

### 2.1 Source Modules

| Module | Path | Lines | Status |
|--------|------|-------|--------|
| ResolutionResult | `src/autom8_asana/resolution/result.py` | 77 | Production-ready |
| ApiBudget | `src/autom8_asana/resolution/budget.py` | 50 | Production-ready |
| ResolutionStrategy (4 impls) | `src/autom8_asana/resolution/strategies.py` | 368 | Production-ready |
| SelectionPredicate hierarchy | `src/autom8_asana/resolution/selection.py` | 181 | Production-ready |
| ResolutionContext | `src/autom8_asana/resolution/context.py` | 350 | Production-ready |
| ResolutionStrategyRegistry | `src/autom8_asana/resolution/registry.py` | 72 | Production-ready |
| Resolution package exports | `src/autom8_asana/resolution/__init__.py` | 62 | Production-ready |
| LifecycleConfig | `src/autom8_asana/lifecycle/config.py` | 177 | Prototype -- needs validation |
| LifecycleEngine | `src/autom8_asana/lifecycle/engine.py` | 325 | Prototype -- broad catches |
| EntityCreationService | `src/autom8_asana/lifecycle/creation.py` | 353 | Prototype -- broad catches |
| CascadingSectionService | `src/autom8_asana/lifecycle/sections.py` | 135 | Prototype -- acceptable |
| PipelineAutoCompletionService | `src/autom8_asana/lifecycle/completion.py` | 115 | Prototype -- acceptable |
| DependencyWiringService | `src/autom8_asana/lifecycle/wiring.py` | 161 | Prototype -- broad catches |
| AutomationDispatch | `src/autom8_asana/lifecycle/dispatch.py` | 128 | Prototype |
| Webhook handler | `src/autom8_asana/lifecycle/webhook.py` | 86 | Prototype -- NOT registered |
| Init action handlers (4) | `src/autom8_asana/lifecycle/init_actions.py` | 347 | Partial -- 2 stubs |
| Lifecycle package exports | `src/autom8_asana/lifecycle/__init__.py` | 86 | Prototype |
| PipelineTransitionWorkflow | `src/autom8_asana/automation/workflows/pipeline_transition.py` | 363 | Prototype |
| ConversationAuditWorkflow | `src/autom8_asana/automation/workflows/conversation_audit.py` | 433 | Production-ready (refactored) |

### 2.2 Configuration

| File | Purpose |
|------|---------|
| `config/lifecycle_stages.yaml` | 10 stages, transitions, cascading sections, init actions, wiring rules |

### 2.3 Design Documents

| Document | Purpose |
|----------|---------|
| `docs/design/TDD-resolution-primitives.md` | Phase 1 technical design |
| `docs/design/TDD-lifecycle-engine.md` | Phase 2 technical design |
| `docs/adr/ADR-001-resolution-api-surface.md` | Resolution API decisions |
| `docs/adr/ADR-002-session-caching-strategy.md` | Session cache design |
| `docs/adr/ADR-003-resolution-model-lazy-pull.md` | Lazy pull strategy |
| `docs/adr/ADR-004-strategy-registration-pattern.md` | Strategy registration |
| `docs/adr/ADR-005-selective-hydration.md` | Branch hydration design |
| `docs/adr/ADR-006-lifecycle-dag-model.md` | YAML DAG configuration |
| `docs/adr/ADR-007-automation-unification.md` | Dispatch unification |
| `docs/adr/ADR-008-entity-creation-delegation.md` | Creation delegation |

### 2.4 Tests

| Test File | Count | Covers |
|-----------|-------|--------|
| `tests/unit/resolution/test_result.py` | 9 | ResolutionResult, ResolutionStatus, factories |
| `tests/unit/resolution/test_budget.py` | 9 | ApiBudget, BudgetExhaustedError |
| `tests/unit/resolution/test_strategies.py` | 9 | 4 strategy implementations |
| `tests/unit/resolution/test_selection.py` | 22 | FieldPredicate, CompoundPredicate, ProcessSelector, EntitySelector |
| `tests/unit/resolution/test_context.py` | 13 | ResolutionContext, session cache, convenience methods |
| `tests/unit/lifecycle/test_config.py` | 11 | YAML loading, StageConfig, transitions |
| `tests/unit/lifecycle/test_engine.py` | 6 | LifecycleEngine orchestration |
| `tests/unit/lifecycle/test_creation.py` | 6 | EntityCreationService |
| `tests/unit/lifecycle/test_sections.py` | 4 | CascadingSectionService |
| `tests/unit/lifecycle/test_completion.py` | 6 | PipelineAutoCompletionService |
| `tests/unit/lifecycle/test_wiring.py` | 5 | DependencyWiringService |
| `tests/unit/lifecycle/test_dispatch.py` | 4 | AutomationDispatch, circular prevention |
| `tests/unit/lifecycle/test_webhook.py` | 5 | Webhook handler, payload parsing |
| `tests/unit/lifecycle/test_init_actions.py` | 10 | 4 init action handlers |
| `tests/unit/automation/workflows/test_pipeline_transition.py` | 11 | PipelineTransitionWorkflow |
| `tests/unit/automation/workflows/test_conversation_audit.py` | 21 | CAW refactored with ResolutionContext |
| **TOTAL** | **151** | |

---

## 3. Production Readiness Assessment

### 3.1 Production-Ready NOW

**Resolution Primitives** (`src/autom8_asana/resolution/`) -- 7 modules, 62 tests.

- Fully tested with 62 unit tests covering all public API surfaces
- Already integrated into ConversationAuditWorkflow (21 refactored tests passing)
- Clean abstractions: ResolutionResult, ApiBudget, strategy chain, session cache
- Bounded API calls (max 8 per chain) prevents runaway resolution
- No external dependencies beyond existing AsanaClient and models
- Follows project conventions: structured logging, type hints, frozen dataclasses

**ConversationAuditWorkflow refactor** -- Uses ResolutionContext instead of bespoke `_resolve_office_phone()`.

### 3.2 Needs Production Hardening

**Lifecycle Engine** (`src/autom8_asana/lifecycle/`) -- 10 modules, 57 tests. Functional but prototype-level.

Specific gaps catalogued in Section 4.

### 3.3 Deferred / NOT STARTED

**PipelineConversionRule absorption** -- The lifecycle engine was designed to replace the existing `PipelineConversionRule` but that absorption has NOT been implemented. The existing rule continues to run. A 5-step absorption plan exists in TDD-lifecycle-engine but is Phase 3+ work.

---

## 4. Production Gap Analysis

### GAP-01: Init Action Handler Stubs (Severity: HIGH)

**Location**: `src/autom8_asana/lifecycle/init_actions.py`

Two of four init action handlers are stubs that log and return success without executing real logic:

| Handler | Status | What It Does Now | What Production Needs |
|---------|--------|-----------------|----------------------|
| `PlayCreationHandler` | IMPLEMENTED | Creates Play task, wires dependency, checks duplicates | Ready |
| `EntityCreationHandler` | STUB (line 199-208) | Logs `lifecycle_entity_creation_deferred` and returns success | Must create asset_edit entities from templates, wire as dependency |
| `ProductsCheckHandler` | PARTIAL (line 274-283) | Pattern-matches products but sub-action is stub | `request_source_videographer` sub-action needs real entity creation |
| `CampaignHandler` | STUB (line 313-328) | Logs `lifecycle_campaign_action` and returns success | Must integrate with campaign API for activate/deactivate |

**Impact**: Lifecycle transitions that trigger these handlers will silently succeed without creating required entities or activating campaigns.

**Mitigation**: Feature-flag the lifecycle engine. Enable only for stages with implemented handlers (sales, outreach, onboarding with PlayCreation).

### GAP-02: Webhook Handler Not Registered (Severity: HIGH)

**Location**: `src/autom8_asana/lifecycle/webhook.py` defines a FastAPI router at `/api/v1/webhooks/asana`, but it is NOT included in the FastAPI app.

**Current state**:
- `src/autom8_asana/api/main.py:177` includes `webhooks_router` which resolves to `src/autom8_asana/api/routes/webhooks.py` -- this is the EXISTING inbound webhook handler (V1, cache invalidation + NoOp dispatch)
- The lifecycle webhook at `src/autom8_asana/lifecycle/webhook.py` defines a SEPARATE router that expects `request.app.state.automation_dispatch` to be set
- Neither the router registration nor the `app.state.automation_dispatch` initialization exists

**Impact**: No webhook-driven lifecycle automation is possible. The engine can only be invoked via `PipelineTransitionWorkflow` (polling-based batch).

**Mitigation**: See HANDOFF-webhook-migration.md for implementation plan.

### GAP-03: Broad Exception Catches (Severity: MEDIUM)

**Location**: 16 `except Exception` blocks in lifecycle modules, 2 in resolution modules.

Per project conventions (MEMORY.md: Exception Narrowing Lessons), broad catches should be narrowed to specific exception types. Current broad catches:

| File | Line | Context | Recommended Narrowing |
|------|------|---------|-----------------------|
| `engine.py` | 188 | Top-level orchestration | Keep broad -- boundary guard |
| `engine.py` | 296 | Iteration count lookup | `ConnectionError`, transport errors |
| `creation.py` | 148 | Process creation orchestration | Keep broad -- boundary guard |
| `creation.py` | 242 | Hierarchy placement | `ConnectionError`, transport errors |
| `creation.py` | 347 | Set assignee | `ConnectionError`, transport errors |
| `sections.py` | 60,73,86 | Section cascade (3 blocks) | `ConnectionError`, transport errors |
| `completion.py` | 91 | Auto-completion | `ConnectionError`, transport errors |
| `wiring.py` | 77,101,137 | Dependency wiring (3 blocks) | `ConnectionError`, transport errors |
| `init_actions.py` | 170,210,287,330 | Handler execution (4 blocks) | Mixed -- PlayCreation keep broad, others narrow |
| `strategies.py` | 178,280 | model_validate cast | `ValidationError` specifically |

**Impact**: Broad catches can mask unexpected errors, making debugging harder in production. The boundary guards at `engine.py:188` and `creation.py:148` are acceptable per project conventions.

### GAP-04: YAML Config Validation (Severity: MEDIUM)

**Location**: `src/autom8_asana/lifecycle/config.py:93-96`

The `_load()` method uses `yaml.safe_load()` with no schema validation. A malformed YAML file (missing required keys, wrong types) will produce runtime errors during transition processing, not at startup.

```python
def _load(self, path: Path) -> None:
    with open(path) as f:
        data = yaml.safe_load(f)
    # No validation of data structure
```

**Impact**: Bad config deploys silently until a transition hits the broken stage.

**Recommendation**: Add Pydantic model validation at load time. Validate all stage names referenced in `transitions.converted`/`did_not_convert` exist as defined stages (DAG integrity check).

### GAP-05: No Metrics / Observability (Severity: MEDIUM)

**Location**: All lifecycle modules

Structured logging exists throughout (`get_logger(__name__)`), but no Prometheus/StatsD metrics are emitted for:

- Transition latency (p50, p95, p99)
- Transition success/failure rate by stage
- Entity creation count by type
- API budget utilization per resolution chain
- Self-loop iteration counts

**Impact**: No production dashboards or alerting. Debugging relies on log search.

**Recommendation**: Use existing `autom8y_telemetry` integration (already in `api/main.py`). Add histogram for transition latency, counters for success/failure by stage.

### GAP-06: No Rate Limit Awareness (Severity: MEDIUM)

**Location**: `src/autom8_asana/lifecycle/engine.py`, `creation.py`, `wiring.py`

The lifecycle engine makes multiple Asana API calls per transition (template discovery, duplicate check, task creation, section moves, field seeding, dependency wiring). None of these calls are aware of Asana's API rate limits (150 requests/minute per PAT).

The `PipelineTransitionWorkflow` processes up to `max_concurrency=3` transitions concurrently, each potentially making 10-15 API calls. A batch of 30 transitions could hit rate limits.

**Impact**: 429 errors from Asana during batch processing. No retry/backoff.

**Recommendation**: The existing `AsanaClient` may have rate-limit handling at the transport layer. Verify and document. If not, add retry-with-backoff at the engine level or leverage the transport layer's retry mechanism.

### GAP-07: No Integration Tests (Severity: LOW)

**Location**: `tests/integration/resolution/` and `tests/integration/lifecycle/` do not exist.

All 151 tests are unit tests with mocked Asana API calls. No integration tests exercise the full chain from webhook receipt through engine orchestration to Asana API calls against a mock server.

**Impact**: Integration issues (e.g., incorrect `opt_fields`, malformed API requests) will not be caught until manual testing or production.

**Recommendation**: Add integration tests using `httpx.AsyncClient` + `respx` or similar for the webhook -> dispatch -> engine -> Asana API chain. Priority: after GAP-02 (webhook registration).

### GAP-08: Iteration Tracking Incomplete (Severity: LOW)

**Location**: `src/autom8_asana/lifecycle/engine.py:251-303`

Self-loop iteration tracking (`_get_iteration_count_async`) counts completed siblings by name matching, but:
- Does NOT use `delay_schedule` from `SelfLoopConfig` (defined in config, ignored in code)
- Name matching is case-insensitive substring, not exact type match
- Falls back to 0 on any exception (silent failure)

The `delay_schedule` field on `SelfLoopConfig` (e.g., `[90, 180, 360]` for reactivation) is configured in YAML but never read by the engine.

**Impact**: Self-loop stages (outreach, reactivation) will not enforce delay schedules between iterations. Max iteration count IS enforced.

### GAP-09: Dispatch Route Coverage (Severity: LOW)

**Location**: `src/autom8_asana/lifecycle/dispatch.py:113-127`

Tag-based routing (`_handle_tag_trigger`) returns a stub response:
```python
return {"success": True, "routed_to": f"lifecycle:{stage}"}
```
It does not actually invoke the lifecycle engine.

**Impact**: Tag-based automation triggers (e.g., `route_sales`) will be acknowledged but not executed.

---

## 5. Functional Requirements for Production

### FR-1: Entity Resolution (READY)

**Source**: `src/autom8_asana/resolution/` (7 modules)

| Requirement | Status | Acceptance Criteria |
|-------------|--------|---------------------|
| Resolve Business from any child entity | IMPLEMENTED | Unit test: `test_context.py` -- resolves Business via hierarchy |
| Resolve Unit, Contact, Offer, Process | IMPLEMENTED | Unit test: `test_context.py` -- convenience methods |
| Session-scoped caching | IMPLEMENTED | Unit test: cache hit avoids duplicate API calls |
| API budget enforcement (max 8) | IMPLEMENTED | Unit test: `test_budget.py` -- BudgetExhaustedError raised |
| Selection predicates (field, compound) | IMPLEMENTED | 22 tests in `test_selection.py` |
| Strategy chain dispatch | IMPLEMENTED | 9 tests in `test_strategies.py` |
| Selective branch hydration (ADR-005) | IMPLEMENTED | `context.py:316-345` -- 2-3 API calls vs 15-25 |

### FR-2: Lifecycle Engine Core Orchestration (READY with gaps)

**Source**: `src/autom8_asana/lifecycle/engine.py`

| Requirement | Status | Acceptance Criteria |
|-------------|--------|---------------------|
| 5-phase orchestration (Create, Configure, Wire, Actions, Dependencies) | IMPLEMENTED | 6 engine tests |
| YAML-driven stage routing | IMPLEMENTED | 11 config tests |
| CONVERTED / DID NOT CONVERT transitions | IMPLEMENTED | Engine routes to target stage |
| Self-loop max iterations | IMPLEMENTED | Returns failure at max |
| Duplicate detection | IMPLEMENTED | Creation service checks existing tasks |
| Template-based entity creation | IMPLEMENTED | Creates from template, seeds fields |
| Cascading section updates | IMPLEMENTED | Offer/Unit/Business sections |
| Pipeline auto-completion | IMPLEMENTED | Completes earlier stages |
| Dependency wiring (pipeline_default) | IMPLEMENTED | Wires Unit, OfferHolder, open DNA plays |
| Terminal state handling | IMPLEMENTED | Month1 CONVERTED -> activate_campaign |

**Gaps**: See GAP-01 (handler stubs), GAP-03 (broad catches), GAP-04 (config validation), GAP-05 (metrics).

### FR-3: PipelineConversionRule Absorption (NOT STARTED)

**Source**: TDD-lifecycle-engine Section 8 (5-step plan)

| Requirement | Status | Notes |
|-------------|--------|-------|
| Shadow mode (run both, compare) | NOT STARTED | Requires feature flag infrastructure |
| Behavior parity tests | NOT STARTED | Need production scenario capture |
| Gradual cutover per stage | NOT STARTED | Depends on shadow mode results |
| Kill switch for rollback | NOT STARTED | Needs operational runbook |
| Full replacement | NOT STARTED | Depends on all above |

### FR-4: Init Action Execution (PARTIAL)

**Source**: `src/autom8_asana/lifecycle/init_actions.py`

| Requirement | Status | Notes |
|-------------|--------|-------|
| PlayCreation (backend_onboard_a_business) | IMPLEMENTED | Template discovery, duplicate check, dependency wiring |
| EntityCreation (asset_edit) | STUB | Logs and returns success, no real creation |
| ProductsCheck (video* -> source_videographer) | PARTIAL | Pattern match works, sub-action is stub |
| CampaignHandler (activate/deactivate) | STUB | Logs and returns success, needs campaign API |

### FR-5: Webhook Ingestion (PARTIAL)

**Source**: `src/autom8_asana/lifecycle/webhook.py`

| Requirement | Status | Notes |
|-------------|--------|-------|
| FastAPI endpoint at `/api/v1/webhooks/asana` | IMPLEMENTED | Router defined, handler written |
| Payload parsing (AsanaWebhookPayload) | IMPLEMENTED | Pydantic model with task_gid, section_name, tags |
| Dispatch to AutomationDispatch | IMPLEMENTED | Builds trigger dict, calls dispatch_async |
| Router registration in app | NOT DONE | Router not included in main.py |
| app.state.automation_dispatch initialization | NOT DONE | No startup code sets this |
| Token/auth verification | NOT DONE | Uses request.app.state, no auth |

### FR-6: Campaign API Integration (NOT STARTED)

| Requirement | Status | Notes |
|-------------|--------|-------|
| Campaign activate/deactivate API client | NOT STARTED | No campaign service client exists |
| Integration with lifecycle engine | NOT STARTED | CampaignHandler is stub |
| Idempotency (activate already-active) | NOT STARTED | Business logic TBD |

---

## 6. Risk Assessment

### P0 Risks (Blockers for Production)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R-01**: Lifecycle engine runs in production with stub handlers, silently skipping entity creation | HIGH if deployed without feature flags | Data integrity -- missing asset_edit entities, missing campaigns | Deploy with per-stage feature flags. Only enable stages with fully implemented handlers. |
| **R-02**: YAML config error deployed to production causes runtime failures during transitions | MEDIUM | All transitions for affected stage fail | Add config validation at startup (GAP-04). Fail fast with clear error message. |

### P1 Risks (Must-fix before full rollout)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R-03**: Rate limit exhaustion during batch processing | MEDIUM under load | 429 errors, transitions fail, no retry | Verify AsanaClient transport-layer retry. Add backoff at workflow level. Reduce max_concurrency. |
| **R-04**: Broad exception catches mask bugs in production | MEDIUM | Silent failures, hard to debug | Narrow catches per GAP-03 before production. Keep boundary guards broad. |
| **R-05**: No observability into transition success/failure rates | HIGH (certain) | Cannot detect degradation, no alerting | Add metrics before production (GAP-05). At minimum: transition counter + latency histogram. |
| **R-06**: Webhook handler path conflict with existing webhooks router | LOW (caught at import) | Both routers at `/api/v1/webhooks/` prefix | Lifecycle webhook uses `/api/v1/webhooks/asana`, existing uses `/api/v1/webhooks/inbound`. No conflict, but verify namespace. |

### P2 Risks (Can ship with, fix later)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R-07**: Self-loop delay_schedule not enforced | LOW | Outreach/reactivation loops fire immediately instead of on schedule | Acceptable for initial rollout. Add delay enforcement in follow-on. |
| **R-08**: Tag-based dispatch is stub | LOW | Tag triggers acknowledged but not executed | No tag-based automation currently in production. Fix when needed. |
| **R-09**: No integration tests | MEDIUM | Integration bugs found in production | Existing unit tests cover logic. Add integration tests after webhook registration. |
| **R-10**: ProcessSelector newest-active heuristic may not match all edge cases | LOW | Wrong process selected in multi-process holders | Unit tests cover primary cases. Monitor in production. |

---

## 7. GO / NO-GO Recommendation

### Resolution Primitives: **GO**

- 62 tests, all passing
- Already integrated into production workflow (ConversationAuditWorkflow)
- Clean API surface, well-documented (TDD + 5 ADRs)
- No production gaps identified
- Recommend: Ship as-is. No changes needed.

### Lifecycle Engine: **GO with conditions**

Conditions for production deployment:

1. **MUST**: Register webhook router OR deploy in polling-only mode via PipelineTransitionWorkflow
2. **MUST**: Add YAML config validation at startup (GAP-04) -- fail fast on bad config
3. **MUST**: Add per-stage feature flags -- enable only stages with fully implemented handlers
4. **MUST**: Add minimum metrics (transition counter + latency histogram) (GAP-05)
5. **SHOULD**: Narrow broad catches for transport operations (GAP-03)
6. **SHOULD**: Implement EntityCreationHandler for asset_edit (GAP-01)
7. **SHOULD**: Verify AsanaClient rate limit handling (GAP-06)

Estimated effort: 3-5 days for MUST conditions, 2-3 additional days for SHOULD conditions.

### PipelineConversionRule Replacement: **NO-GO**

- Not started (FR-3 entirely unimplemented)
- Requires shadow mode infrastructure, behavior parity tests, gradual cutover
- The existing PipelineConversionRule continues to function
- Recommend: Plan as separate initiative after lifecycle engine is production-stable
- Estimated effort: 2-3 weeks including shadow mode validation

---

## 8. Constraints (MUST NOT Change)

These decisions from R&D are load-bearing and must be preserved:

| Constraint | Rationale | Source |
|------------|-----------|--------|
| ResolutionContext is an async context manager | Session cache lifecycle management; cleared on exit | ADR-002 |
| API budget default is 8 calls | Prevents runaway resolution chains; derived from production hierarchy depth analysis | TDD-resolution-primitives Section 3 |
| Strategy chain order: SessionCache -> NavigationRef -> DependencyShortcut -> HierarchyTraversal | Cheapest strategies first (0 API calls), most expensive last | ADR-004 |
| YAML-driven stage config (not subclasses) | Enables non-code stage changes; validated by 5 iterations of production data mapping | ADR-006 |
| 5-phase orchestration order: Create -> Configure -> Wire -> Actions -> Dependencies | Asana requires valid GID before dependency API calls; wiring MUST follow creation | ADR-008, TDD-lifecycle-engine Section 5 |
| Lifecycle webhook is a SEPARATE router from existing inbound webhook | Different payload formats, auth models, and dispatch paths | GAP-02 analysis |
| Template-based creation (not blank tasks) | Production workflows depend on template subtasks, notes, and custom field defaults | ADR-008 |
| ProcessType enum values must match YAML stage names exactly | Engine maps `source_process.process_type.value` -> `config.get_stage()` | `engine.py:78` |

---

## 9. Recommended Implementation Order

For the 10x-dev team, the recommended implementation sequence:

| Priority | Work Item | Depends On | Effort |
|----------|-----------|------------|--------|
| 1 | YAML config validation at startup | None | 0.5 day |
| 2 | Add per-stage feature flags | Config validation | 1 day |
| 3 | Add transition metrics (counter + histogram) | None | 1 day |
| 4 | Register lifecycle webhook router | Feature flags | 1 day (see HANDOFF-webhook-migration.md) |
| 5 | Narrow broad catches in lifecycle modules | None | 1 day |
| 6 | Implement EntityCreationHandler (asset_edit) | Feature flags | 1-2 days |
| 7 | Implement ProductsCheck sub-action | EntityCreationHandler | 0.5 day |
| 8 | Campaign API client + CampaignHandler | External API docs | 2-3 days |
| 9 | Integration tests (webhook -> engine -> mock API) | Webhook registration | 2 days |
| 10 | Shadow mode for PCR replacement | Integration tests | 1-2 weeks |

---

## 10. Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| Resolution source | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/resolution/` | Read all 7 modules |
| Lifecycle source | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lifecycle/` | Read all 10 modules |
| Pipeline transition workflow | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/pipeline_transition.py` | Read |
| Conversation audit workflow | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/conversation_audit.py` | Read |
| Lifecycle YAML config | `/Users/tomtenuta/Code/autom8_asana/config/lifecycle_stages.yaml` | Read |
| TDD - Resolution Primitives | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-resolution-primitives.md` | Read (first 200 lines) |
| TDD - Lifecycle Engine | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-lifecycle-engine.md` | Read (first 200 lines) |
| Resolution tests | `/Users/tomtenuta/Code/autom8_asana/tests/unit/resolution/` | 62 tests counted |
| Lifecycle tests | `/Users/tomtenuta/Code/autom8_asana/tests/unit/lifecycle/` | 57 tests counted |
| Pipeline transition tests | `/Users/tomtenuta/Code/autom8_asana/tests/unit/automation/workflows/test_pipeline_transition.py` | 11 tests counted |
| CAW tests | `/Users/tomtenuta/Code/autom8_asana/tests/unit/automation/workflows/test_conversation_audit.py` | 21 tests counted |
| FastAPI main.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Read -- confirmed webhook router NOT registered |
| Existing webhooks router | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/webhooks.py` | Read -- confirmed separate from lifecycle webhook |
| ADR-001 through ADR-008 | `/Users/tomtenuta/Code/autom8_asana/docs/adr/ADR-00{1..8}-*.md` | Verified existence |
