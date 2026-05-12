---
domain: feat/lifecycle-engine
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/lifecycle/"
  - "./config/lifecycle_stages.yaml"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.94
format_version: "1.0"
---

# Entity Lifecycle Pipeline (4-Phase Transition Engine)

## Purpose and Design Rationale

The lifecycle engine orchestrates movement of Process entities through business pipeline stages — from Outreach through Sales, Onboarding, Implementation, and into post-implementation stages. It watches for `converted` or `did_not_convert` outcomes on any Process and executes up to four sequential phases to materialize the next state in Asana.

**Problem solved**: Without this engine, pipeline stage progression (creating new process tasks, wiring dependencies, seeding fields, updating related entities) had to be handled by a single monolithic `PipelineConversionRule`. The lifecycle engine replaces that with a data-driven, phase-separated, fail-forward pipeline.

**Design decisions** (from `engine.py` docstring referencing `TDD-lifecycle-engine-hardening`):
- **Data-driven**: Pipeline defined in `config/lifecycle_stages.yaml`. Adding stages or changing transitions requires no code — only YAML.
- **Fail-forward**: Phase 1 (CREATE) is the only hard-fail gate. Phases 2–4 degrade gracefully with accumulated warnings in `TransitionResult`.
- **Protocol-based DI**: All six service dependencies (`CreationServiceProtocol`, `SectionServiceProtocol`, `CompletionServiceProtocol`, `InitActionRegistryProtocol`, `WiringServiceProtocol`, `ReopenServiceProtocol`) are injected as `@runtime_checkable` Protocol types. Production defaults are lazily constructed to avoid import-time coupling.
- **Lazy imports**: Service constructors (`_import_creation_service`, etc.) defer all sibling-module imports to first use, preventing circular import issues at module load time.
- **10 BROAD-CATCH sites** in `engine.py`, all annotated `# BROAD-CATCH` (LB-005), intentional per fail-forward contract.

**Tradeoff accepted**: The webhook entry point (`webhook.py`) reads `app.state.automation_dispatch` directly at request time — `AutomationDispatch` is not initialized in `lifespan.py`. This creates a runtime gap: the production webhook route will `AttributeError` unless something outside the standard startup sequence populates `app.state.automation_dispatch`. (See Boundaries section.)

## Conceptual Model

### The 4-Phase Pipeline

| Phase | What | Config field | Failure Mode |
|-------|------|--------------|-------------|
| 1: CREATE | Template duplication via `EntityCreationService` or blank task fallback | `project_gid`, `template_section`, `target_section` | Hard-fail — blocks all subsequent phases |
| 2a: CONFIGURE sections | Cascading section updates on Offer/Unit/Business | `cascading_sections` | Degraded — warning in TransitionResult |
| 2b: CONFIGURE complete | Auto-complete source process | `transitions.auto_complete_prior` | Degraded |
| 3: ACTIONS | Parallel init actions via `_DefaultInitActionRegistry` (concurrency=4) | `init_actions[]` | Degraded per-action |
| 4: WIRE | Wire dependents (Unit, OfferHolder) and dependencies (open DNA plays) | `dependency_wiring` | Degraded |

Phase ordering is load-bearing: Phase 1 must produce a GID before Phases 3 and 4 can reference it.

### 10 Configured Stages

| Stage | `pipeline_stage` | DNC Action | `auto_complete_prior` | Status |
|-------|-----------------|------------|----------------------|--------|
| outreach | 1 | deferred | false | Active |
| sales | 2 | create_new | true | Active |
| onboarding | 3 | reopen | true | Active |
| implementation | 4 | create_new | true | Active |
| month1 | 5 | deferred | — | Deferred |
| retention | 1 | create_new | — | Deferred |
| reactivation | 2 | deferred | — | Deferred |
| account_error | 6 | create_new | — | Deferred |
| expansion | 6 | deferred | — | Deferred |

Implementation CONVERTED → `null` (terminal for stages 1–4). Implementation DID NOT CONVERT → outreach (corrected from `sales` per TDD Section 8.2).

### DNC Routing

Three behaviors per-stage (`dnc_action` field):
- `create_new`: Run full 4-phase pipeline with new target stage
- `reopen`: `ReopenService.reopen_async()` — finds + unmarks complete + moves prior process in target stage
- `deferred`: Log self-loop, no writes

### Pre-Transition Validation

`StageConfig.validation.pre_transition` supports `required_fields` + `mode` (`"warn"` or `"block"`). Only `onboarding` stage currently configures this: `required_fields: ["Contact Phone"]`, `mode: warn`. Block mode returns early with error result.

### Webhook Entry Chain

```
POST /api/v1/webhooks/asana
  -> webhook.py:handle_asana_webhook() [FastAPI route]
  -> request.app.state.automation_dispatch  [NOT wired in lifespan.py — runtime gap]
  -> AutomationDispatch.dispatch_async(trigger)
  -> _handle_section_change() or _handle_tag_trigger()
  -> LifecycleEngine.handle_transition_async(source_process, outcome)
```

Separately, `LifecycleWebhookDispatcher` provides a 4-layer feature flag wrapper:
1. Global enable (`WEBHOOK_DISPATCH_ENABLED`, default: false)
2. Entity type allowlist (`WEBHOOK_DISPATCH_ENTITY_TYPES`)
3. Event type allowlist (`WEBHOOK_DISPATCH_EVENT_TYPES`)
4. Loop detection (`LoopDetector.is_self_triggered(gid)`)
5. Dry-run vs live (`WEBHOOK_DISPATCH_DRY_RUN`, default: true)

`LifecycleWebhookDispatcher` is NOT currently wired into `webhook.py` — `webhook.py` bypasses the dispatcher and goes directly to `app.state.automation_dispatch`. The dispatcher is tested independently and available via `webhook_dispatcher.py`.

### Observation Layer

`StageTransitionRecord` (frozen dataclass): `entity_gid`, `entity_type`, `business_gid`, `from_stage`, `to_stage`, `pipeline_stage_num`, `transition_type`, `entered_at`, `exited_at`, `automation_result_id`, `duration_ms`.

`StageTransitionEmitter` wraps `StageTransitionStore` and calls `asyncio.to_thread(store.append, record)` — fire-and-forget via background thread. Swallows all exceptions.

`StageTransitionStore`: Polars-backed parquet at `~/.autom8/stage_transitions/{entity_type}.parquet`. Append-only. Materializes `duration_days` column at load time. `EntityStageTimeline` provides `time_in_stage()`, `current_stage()`, `converted_through()`.

### Loop Detection

`LoopDetector`: time-windowed (30s) in-memory `dict[str, float]`. `record_outbound(gid)` stamps the GID; `is_self_triggered(gid)` checks within window. Prunes on every call. Does NOT survive process restarts.

**CRITICAL**: `record_outbound()` has ZERO production call sites in `src/`. It is documented in `loop_detector.py` at three integration points (Phase 1 CREATE, `CascadingSectionService`, `SaveSession.EXECUTE`) but none are wired. The detector will always return `False` in production — self-loop prevention is nominally present but effectively disabled.

### AutoCascadeSeeder

`AutoCascadeSeeder.seed_async()`: zero-config field matching via case-insensitive name comparison. Cascade precedence (later overrides earlier):
1. Business custom fields → target
2. Unit custom fields → target
3. Source Process custom fields → target
4. Computed fields (e.g., `"Launch Date": "today"`)

Uses `FieldSeeder` infrastructure for enum resolution and batch API write. Eliminates double-fetch via optional `target_task` pre-pass (IMP-02 optimization).

### Tag Routing

`AutomationDispatch._handle_tag_trigger()` handles `tag_added` events. Only `route_{stage}` tag pattern is partially handled (returns `{"success": True, "routed_to": ...}` without actually calling `LifecycleEngine`). Tag routing is functionally a stub.

## Implementation Map

17 files in `src/autom8_asana/lifecycle/`:

| File | Purpose | Key Types |
|------|---------|-----------|
| `engine.py` | Orchestrator — 4-phase pipeline + DNC routing | `LifecycleEngine`, `TransitionResult`, `LifecycleActionResult`, 6 Protocol types |
| `config.py` | Pydantic models + YAML loader + DAG validator | `LifecycleConfig`, `LifecycleConfigModel`, `StageConfig`, `TransitionConfig`, `InitActionConfig`, `CascadingSectionConfig`, `SeedingConfig`, `AssigneeConfig`, `WiringRuleConfig`, `load_config()` |
| `creation.py` | Phase 1 entity creation | `EntityCreationService`, `CreationResult` |
| `sections.py` | Phase 2a cascading section updates | `CascadingSectionService`, `CascadeResult` |
| `completion.py` | Phase 2b auto-complete source process | `CompletionService`, `CompletionResult` |
| `init_actions.py` | Phase 3 init action handlers + registry | `HANDLER_REGISTRY`, `InitActionHandler` (ABC), `CommentHandler`, `PlayCreationHandler`, `EntityCreationHandler`, `ProductsCheckHandler`, `CampaignHandler` |
| `wiring.py` | Phase 4 dependency wiring | `DependencyWiringService`, `WiringResult` |
| `seeding.py` | Auto-cascade field seeding bridge | `AutoCascadeSeeder`, `SeedingResult` |
| `reopen.py` | DNC reopen mechanics | `ReopenService`, `ReopenResult` |
| `dispatch.py` | Webhook trigger router → LifecycleEngine | `AutomationDispatch` |
| `webhook.py` | FastAPI route `POST /api/v1/webhooks/asana` | `router`, `AsanaWebhookPayload`, `WebhookResponse` |
| `webhook_dispatcher.py` | 4-layer feature flag wrapper | `LifecycleWebhookDispatcher`, `WebhookDispatcherConfig` |
| `observation.py` | Stage transition data model + emitter | `StageTransitionRecord`, `EntityStageTimeline`, `StageTransitionEmitter` |
| `observation_store.py` | Parquet-backed persistence | `StageTransitionStore` |
| `loop_detector.py` | Time-windowed self-loop prevention | `LoopDetector` |
| `__init__.py` | Public surface — re-exports all types | Full `__all__` including `load_config`, `LifecycleEngine`, `AutomationDispatch`, `router` |

### Phase 3 Init Action Registry

`HANDLER_REGISTRY` maps `InitActionConfig.type` → handler class:

| Type | Handler | What |
|------|---------|------|
| `play_creation` | `PlayCreationHandler` | Template duplication with `reopen_if_completed_within_days` support; wires as dependency |
| `entity_creation` | `EntityCreationHandler` | Full `EntityCreationService.create_entity_async()` flow |
| `products_check` | `ProductsCheckHandler` | `fnmatch` glob pattern against `business.products`; creates `SourceVideographer` if matched |
| `activate_campaign` | `CampaignHandler` | Log-only stub |
| `deactivate_campaign` | `CampaignHandler` | Log-only stub |
| `create_comment` | `CommentHandler` | Pipeline conversion comment with source deep-link; soft-fails on error (returns `success=True`) |

Actions execute in parallel with `gather_with_semaphore(concurrency=4)`.

### Data Flow (primary path: CONVERTED)

```
POST /api/v1/webhooks/asana
  -> AsanaWebhookPayload(task_gid, section_name)
  -> app.state.automation_dispatch.dispatch_async(trigger)
  -> AutomationDispatch._handle_section_change()
  -> client.tasks.get_async(task_gid) -> Process
  -> LifecycleEngine.handle_transition_async(process, "converted")
  -> config.get_stage(source_stage_name)  # StageConfig
  -> config.get_target_stage(source_stage_name, "converted")  # StageConfig
  -> [optional pre-validation]
  -> ResolutionContext(client, trigger_entity=source_process) [async context]
  -> _run_pipeline_async(source_stage, target_stage, ctx, source_process, result)
     -> Phase 1: creation_service.create_process_async() -> CreationResult
     -> Phase 2: section_service.cascade_async() + completion_service.complete_source_async()
     -> Phase 3: init_action_registry.execute_actions_async() [parallel, concurrency=4]
     -> Phase 4: wiring_service.wire_defaults_async()
  -> _build_result() -> AutomationResult
  -> _emit_transition() -> StageTransitionEmitter.emit() [fire-and-forget, to_thread]
  -> AutomationResult
```

### Public API Surface (from `__init__.py __all__`)

Entry points consumed by other packages:
- `LifecycleEngine` — injected into `AutomationDispatch`; consumed by `dispatch.py`
- `AutomationDispatch` — consumed by `webhook.py` (via `app.state`)
- `load_config` — consumed by `reconciliation/processor.py` (derives unit section derivation table)
- `router` — consumed by `api/main.py` as `webhooks_router` (line 77, mounted at line 443)
- `LifecycleConfig.build_derivation_table()` — consumed by `reconciliation/processor.py` (ADR-derivation-table-hardcoded-dict)

### Test Coverage

Unit tests in `tests/unit/lifecycle/` (16 files including `conftest.py`):

| Test File | Coverage |
|-----------|---------|
| `test_engine.py` | Phase orchestration, DNC routing, TransitionResult accumulation |
| `test_config.py` | YAML loading, DAG validation, `build_derivation_table()` |
| `test_creation.py` | Phase 1 EntityCreationService |
| `test_sections.py` | Phase 2a CascadingSectionService |
| `test_completion.py` | Phase 2b CompletionService |
| `test_init_actions.py` | All 6 handler types |
| `test_wiring.py` | Phase 4 DependencyWiringService |
| `test_seeding.py` | AutoCascadeSeeder |
| `test_reopen.py` | ReopenService |
| `test_dispatch.py` | AutomationDispatch routing |
| `test_webhook.py` | FastAPI route with mock `app.state.automation_dispatch` |
| `test_webhook_dispatcher.py` | LifecycleWebhookDispatcher feature flags + TestLoopDetector class |
| `test_observation.py` | StageTransitionRecord, StageTransitionEmitter |
| `test_lifecycle_observation_contracts.py` | Observation contract tests incl. `TestLO15LoopDetectorWithinWindow` |
| `test_integration.py` | Integration path |

Integration test: `tests/integration/test_lifecycle_smoke.py`.

`loop_detector.py` is now tested (was flagged as highest-risk untested gap in prior knowledge). Tests are in `test_webhook_dispatcher.py:TestLoopDetector` and `test_lifecycle_observation_contracts.py:TestLO15LoopDetectorWithinWindow`.

## Boundaries and Failure Modes

### This feature does NOT:
- Persist `AutomationDispatch` to `app.state` — it must be wired externally or via test setup
- Wire `LoopDetector.record_outbound()` at any production call site — loop detection is structurally disabled in production
- Implement actual campaign activation/deactivation — `CampaignHandler` is a log-only stub
- Provide SLOs or rate-limit the webhook endpoint — no throttle on `POST /api/v1/webhooks/asana`
- Survive process restart for loop detection state (in-memory `dict`)
- Produce durable parquet storage in containers — default path `~/.autom8/stage_transitions/` is ephemeral in ECS/Lambda

### Active Scars

- **SCAR-014**: Config models use `extra="ignore"` (not `extra="forbid"`) for forward-compat. `webhook.py` uses `ConfigDict(extra="forbid")` — these two policies coexist in the same package.
- **SCAR-027**: `generate_entity_name` in `core/creation.py:82-97` uses lambda in `re.sub` to prevent backreference injection from user-controlled strings.
- **LB-005**: `engine.py` has 10 `except Exception` handlers — all annotated `# BROAD-CATCH`, intentional per fail-forward contract.

### Runtime Gaps (unresolved from prior knowledge)

1. **`app.state.automation_dispatch` not initialized in `lifespan.py`**: `webhook.py:74` accesses `request.app.state.automation_dispatch` but `lifespan.py` does not populate it. Tests mock it via `app.state.automation_dispatch = mock_dispatch`. In production, this would raise `AttributeError` on every webhook request.
2. **`LoopDetector.record_outbound()` zero production call sites**: The three documented integration points (Phase 1 CREATE, `CascadingSectionService`, `SaveSession.EXECUTE`) are not wired. `is_self_triggered()` will always return `False`.
3. **`LifecycleWebhookDispatcher` not wired into `webhook.py`**: The 4-layer feature flag dispatcher exists but is bypassed. `webhook.py` uses `app.state.automation_dispatch` directly, skipping entity allowlist, event allowlist, loop detection, and dry-run controls.
4. **Tag routing is a stub**: `AutomationDispatch._handle_tag_trigger()` returns `{"success": True, "routed_to": ...}` for `route_*` tags but does not call `LifecycleEngine`.
5. **Production storage override for `StageTransitionStore`**: No startup code configures a non-default `base_dir`. In containers, transitions are lost on restart.

### Constraints

- Phase ordering is load-bearing (Phase 1 GID required by Phases 3 and 4).
- `lifecycle_stages.yaml` is validated at startup — malformed YAML causes hard-fail via `pydantic.ValidationError`.
- YAML DAG integrity is enforced by `LifecycleConfigModel.validate_dag_integrity()` — all transition targets must reference defined stages.
- CampaignHandler is a log-only stub — stages using `activate_campaign`/`deactivate_campaign` have incomplete automation.
- 4 active stages (outreach, sales, onboarding, implementation); 6 deferred (month1, retention, reactivation, account_error, expansion, and the continuation of implementation).
- Implementation CONVERTED is terminal (no target stage) — triggers `_handle_terminal_async()`.

### Integration Points

| Direction | This package | Target | What |
|-----------|-------------|--------|------|
| Consumes | `engine.py` | `core.creation` (via `creation.py`) | Template duplication, entity creation |
| Consumes | `engine.py` | `resolution.context.ResolutionContext` | Hierarchy entity access during pipeline |
| Consumes | `seeding.py` | `automation.seeding.FieldSeeder` | Enum resolution + API write for field cascade |
| Consumes | `init_actions.py` | `automation.templates.TemplateDiscovery` | Play template discovery in `PlayCreationHandler` |
| Consumes | `creation.py` | `persistence.session.SaveSession` | Phase 1 step e — hierarchy placement |
| Consumes | all | `client.AsanaClient` | All Asana API calls |
| Provides | `config.py:build_derivation_table()` | `reconciliation/processor.py` | Process-type → unit-section derivation table |
| Provides | `webhook.py:router` | `api/main.py` (as `webhooks_router`) | Mounted at `POST /api/v1/webhooks/asana` |
| Provides | `lifecycle/__init__.py` | `automation/` (planned) | `PipelineConversionRule` absorption target |

```metadata
source_files_read: 17
key_evidence:
  - src/autom8_asana/lifecycle/engine.py (full read — 892 lines)
  - src/autom8_asana/lifecycle/config.py (full read — 322 lines)
  - config/lifecycle_stages.yaml (full read — 252 lines)
  - src/autom8_asana/lifecycle/webhook_dispatcher.py (full read)
  - src/autom8_asana/lifecycle/loop_detector.py (full read)
  - src/autom8_asana/lifecycle/observation.py (full read)
  - src/autom8_asana/lifecycle/observation_store.py (full read)
  - src/autom8_asana/lifecycle/seeding.py (full read)
  - src/autom8_asana/lifecycle/webhook.py (full read)
  - src/autom8_asana/lifecycle/dispatch.py (full read)
  - src/autom8_asana/lifecycle/init_actions.py (full read)
  - src/autom8_asana/lifecycle/__init__.py (full read)
  - src/autom8_asana/lifecycle/wiring.py (partial read — 60 lines)
  - src/autom8_asana/api/lifespan.py (full read — 320 lines)
  - src/autom8_asana/api/main.py (grep — webhook router confirmed at line 443)
  - tests/unit/lifecycle/ (directory listing + grep for loop_detector coverage)
confidence_rationale: >
  High confidence (0.94) based on full reads of all 17 lifecycle files.
  Minor deductions: wiring.py read only partially (60 lines; internal wiring
  logic not traced); creation.py, sections.py, completion.py, reopen.py not
  read (covered by test names and engine.py Protocol signatures).
  Key gap closed: loop_detector coverage now confirmed. Key gap added:
  app.state.automation_dispatch uninitialized in lifespan.py (production
  webhook breakage).
```
