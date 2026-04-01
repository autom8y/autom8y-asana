---
domain: feat/lifecycle-engine
generated_at: "2026-04-01T16:20:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/lifecycle/**/*.py"
  - "./config/lifecycle_stages.yaml"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# Entity Lifecycle Pipeline (4-Phase Transition Engine)

## Purpose and Design Rationale

The lifecycle engine orchestrates movement of Process entities through business pipeline stages -- from Outreach through Sales, Onboarding, Implementation, and into post-implementation stages. It watches for `converted` or `did_not_convert` outcomes on any Process and executes up to four sequential phases to materialize the next state in Asana.

**Data-driven**: Pipeline defined in `config/lifecycle_stages.yaml`. Adding stages or changing transitions requires no code -- only YAML.

**Fail-forward**: Phase 1 (CREATE) is the only hard-fail gate. Phases 2-4 degrade gracefully with accumulated warnings in `TransitionResult`.

## Conceptual Model

### The 4-Phase Pipeline

| Phase | What | Failure Mode |
|-------|------|-------------|
| 1: CREATE | Template duplication or blank task fallback | Hard-fail |
| 2: CONFIGURE | (2a) Cascading section updates on Offer/Unit/Business; (2b) Auto-complete source | Degraded |
| 3: ACTIONS | Parallel init actions: play_creation, entity_creation, products_check, campaigns, comments | Degraded |
| 4: WIRE | Wire dependents (Unit, OfferHolder) and dependencies (open DNA plays) | Degraded |

### 10 Configured Stages

outreach -> sales -> onboarding -> implementation (fully hardened). month1, retention, reactivation, account_error, expansion (defined for DAG integrity, deferred for hardening).

### DNC Routing

Three behaviors per-stage: `create_new` (run 4-phase with new target), `reopen` (find + unmark + move prior process), `deferred` (log self-loop, no writes).

### Webhook Entry Chain

```
POST /api/v1/webhooks/asana
  -> LifecycleWebhookDispatcher (4-layer feature flag: enabled, entity allowlist, event allowlist, loop_detector)
  -> AutomationDispatch.dispatch_async()
  -> LifecycleEngine.handle_transition_async(source_process, outcome)
```

Defaults: `WEBHOOK_DISPATCH_ENABLED=false`, `WEBHOOK_DISPATCH_DRY_RUN=true`.

### Observation Layer

`StageTransitionRecord` emitted to parquet-backed `StageTransitionStore` at `~/.autom8/stage_transitions/`. Fire-and-forget via `asyncio.to_thread`. Supports time-in-stage analytics.

### Loop Detection

`LoopDetector`: time-windowed (30s) in-memory set. `record_outbound(gid)` on writes; `is_self_triggered(gid)` on webhook receipt. Prevents Asana webhook self-loops. Does not survive process restarts.

## Implementation Map

16 files in `src/autom8_asana/lifecycle/`: engine.py (orchestrator, TransitionResult accumulator), config.py (Pydantic models + YAML loader + DAG validator), creation.py (Phase 1), sections.py (Phase 2a cascading sections), completion.py (Phase 2b auto-complete), init_actions.py (Phase 3, 6 handler types), wiring.py (Phase 4), seeding.py (AutoCascadeSeeder zero-config field matching), reopen.py (DNC reopen), dispatch.py (section-changed/tag-added routing), webhook.py (FastAPI route), webhook_dispatcher.py (4-layer feature flag), observation.py (StageTransitionRecord/Emitter), observation_store.py (parquet store), loop_detector.py.

### Phase 3 Init Action Registry

| Type | Handler | What |
|------|---------|------|
| play_creation | PlayCreationHandler | Template duplication with reopen-if-recent support |
| entity_creation | EntityCreationHandler | Full EntityCreationService flow |
| products_check | ProductsCheckHandler | Glob pattern match on business.products |
| activate_campaign | CampaignHandler | Log-only stub |
| deactivate_campaign | CampaignHandler | Log-only stub |
| create_comment | CommentHandler | Pipeline conversion comment with source link |

### AutoCascadeSeeder

Zero-config: any custom field with same name (case-insensitive) on source entities and target task is cascaded automatically. Precedence: Business -> Unit -> Source Process -> Computed fields.

## Boundaries and Failure Modes

### Integration Points

- **Entity creation**: delegates to `core.creation` functions
- **Hierarchy resolution**: `resolution.context.ResolutionContext`
- **Asana API calls**: via injected `AsanaClient`
- **Persistence**: `SaveSession` for hierarchy placement (Phase 1 step e)
- **automation/ package**: designed to eventually absorb `PipelineConversionRule`

### Active Scars

- **SCAR-014**: Config models use `extra="ignore"` (not `extra="forbid"`) for forward-compat
- **SCAR-027**: `generate_entity_name` uses lambda in `re.sub` to prevent backreference injection
- **LB-005**: engine.py has 10 `except Exception` handlers -- all annotated `# BROAD-CATCH`, intentional

### Constraints

- CampaignHandler is a log-only stub -- stages using it have incomplete automation
- Observation store default path (`~/.autom8/`) doesn't persist in containers
- 4 active stages, 6 deferred

## Knowledge Gaps

1. **Webhook router registration** in `api/main.py` unconfirmed.
2. **`app.state.automation_dispatch` initialization** location unconfirmed.
3. **`LoopDetector.record_outbound()` wiring** at all 3 documented call sites unconfirmed.
4. **Production storage override** for StageTransitionStore unconfirmed.
5. **Tag routing** (`_handle_tag_trigger`) appears to be a stub.
6. **Stages 5-10** (post-implementation) defined but deferred for hardening.
