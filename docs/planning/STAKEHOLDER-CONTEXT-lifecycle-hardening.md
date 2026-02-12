# Stakeholder Context: Lifecycle Engine Hardening Sprint

**Initiative**: Workflow Resolution Platform (INIT-ER-001)
**Phase**: 10x-dev Production Hardening
**Stakeholder Interview**: 15 rounds, 2026-02-11
**Scope**: Full lifecycle rewrite + PCR absorption for stages 1-4

---

## 1. Sprint Scope & Boundaries

### IN SCOPE

- **Full rewrite** of all lifecycle engine modules (from TDD specs, production quality)
- **PCR absorption**: Migrate Sales→Onboarding conversion logic into lifecycle engine
- **Pipeline stages 1-4**: Sales, Outreach, Onboarding, Implementation
- **Both transition types**: CONVERTED and DID NOT CONVERT for all 4 stages
- **EntityCreationHandler**: Complete implementation for AssetEdit (template-based under AssetEditHolder)
- **Resolution cleanup + enhancement**: Dead code removal, add `resolve_holder_async()`, narrow catches
- **Central project registry**: New `core/project_registry.py` for ALL project GIDs
- **Integration tests**: Full workflow chain (PipelineTransitionWorkflow→engine→creation→Asana mock)
- **Comment generation**: Init action handler for transition comments (generalizable to all entity types)
- **Auto-cascade field seeding**: Smart defaults where matching field names cascade automatically
- **Structured audit logging**: Both AutomationResult + structured log events per transition

### OUT OF SCOPE

- **Trigger mechanism** (webhook/polling): Deferred. Focus on engine correctness first
- **CampaignHandler**: External API dependency not explored. Remains stub
- **Tag-based dispatch**: Deferred. No production usage currently
- **Self-loop iteration tracking**: Not needed for stages 1-4 (applies to Outreach/Reactivation only)
- **Stages 5-10**: Month1, Retention, Reactivation, AccountError, Expansion deferred
- **Observability metrics**: Separate initiative. Structured logging sufficient for now
- **Shadow mode / PCR comparison**: Not needed — direct absorption since only one active PCR instance

### DELIVERY MODEL

- **Direct commits to main** (no PR)
- **Architect defines quality gates** and module structure decisions
- **Improve on existing patterns** (better typing, stricter validation, cleaner abstractions)

---

## 2. Lifecycle Routing DAG (Stages 1-4)

### CONVERTED Transitions (create new process)

```
Outreach  →CONVERTED→  Sales       (create new Sales process)
Sales     →CONVERTED→  Onboarding  (create new Onboarding process) [PCR absorption]
Onboarding→CONVERTED→  Implementation (create new Implementation process)
Implementation→CONVERTED→ [TERMINAL for stages 1-4 scope]
```

### DID NOT CONVERT Transitions (mixed: create new OR reopen)

```
Sales       →DNC→  Outreach     (CREATE new Outreach process)
Onboarding  →DNC→  Sales        (REOPEN original Sales: mark incomplete, move to Opportunity section)
Implementation →DNC→ Outreach   (CREATE new Outreach process)
```

### DNC Reopen Mechanics

When Onboarding DNC triggers Sales reopen:
1. Search ProcessHolder subtasks for the most recent Sales process (not necessarily completed — "open" refers to section placement, not completion status)
2. Mark the process incomplete (`completed = false`)
3. Move to "Opportunity" section in Sales project
4. No entity creation occurs

### Key Distinction

- **DNC from Sales**: Creates NEW Outreach (tracks individual re-engagement effort)
- **DNC from Onboarding**: REOPENS existing Sales (wasn't a true sale, revert)
- **DNC from Implementation**: Creates NEW Outreach (full re-engagement needed)

---

## 3. Entity Creation Rules

### 3.1 Process Creation (forward transitions)

1. **Template discovery**: Find template task in target project's template section
2. **Fallback**: If no template found, create blank task with generated name (name only, no subtasks)
3. **Name generation**: Replace `[Business Name]`, `[Unit Name]` placeholders from template name
4. **Hierarchy placement**: Place under ProcessHolder as subtask (resolved via `resolve_holder_async()`)
5. **Insert order**: After the trigger process (`insert_after=source_process`)

### 3.2 Duplicate Detection (Generalized)

**Similarity criteria**: Same ProcessType + same Unit (BusinessUnit level, not Business level)

**Check location**: ProcessHolder subtasks (not dependency links — those are shortcuts, not canonical)

**Reopen-or-create pattern** (configurable per init action):
- Check holder for existing non-completed similar processes
- If found AND within staleness threshold → reopen existing
- If not found OR stale → create new
- Configurable: `reopen_if_completed_within_days: 90` or `always_create_new: true`

**Note**: Processes in DID NOT CONVERT sections are terminal — cannot be "un-DNC'd" or reopened from DNC state. Only CONVERTED processes can be reopened.

### 3.3 AssetEdit (Implementation init action)

- Created from template in AssetEditHolder project (GID: 1203992664400125)
- Placed as subtask of Business's AssetEditHolder
- Fields seeded, assignee set, due date set (same as process creation)
- Wired as dependency of the Implementation process
- Uses generalized duplicate detection (check AssetEditHolder for existing)

### 3.4 BackendOnboardABusiness Play (Implementation init action)

- Created from template in DNAHolder project
- Placed as subtask of Business's DNAHolder
- **Special condition**: Require new BOAB if no completed BOAB in last 90 days, otherwise reopen existing
- Wired as dependency of Implementation process
- Uses the reopen-or-create pattern with `reopen_if_completed_within_days: 90`

### 3.5 SourceVideographer (Onboarding init action, conditional)

- **Condition**: Products field on Unit contains `video*` pattern (fnmatch)
- Created from template in VideographyHolder project (GID: 1207984018149338)
- Placed as subtask of Business's VideographyHolder
- No dependency wiring (standalone)

### 3.6 Hierarchy Placement (generalized)

All entity creation uses resolution-based hierarchy placement:
- Resolve appropriate holder via `resolve_holder_async(holder_type)`
- Use `set_parent()` to place entity under holder
- Entity types → holder targets:
  - Process → ProcessHolder
  - DNA/Play → DNAHolder
  - AssetEdit → AssetEditHolder
  - Videography → VideographyHolder

---

## 4. Field Seeding Architecture

### 4.1 Auto-Cascade Design

**Principle**: Fields with matching names on both source and target entities cascade automatically (zero config).

**YAML config only needed for**:
- **Exclusions**: Fields that should NOT cascade despite matching names
- **Computed fields**: Values derived at transition time (e.g., `Launch Date = today`)

**Field name mappings**: NOT needed — field names are consistent across projects (confirmed by stakeholder).

### 4.2 Cascade Precedence (later overrides earlier)

1. **Business cascade**: Fields from Business entity → target
2. **Unit cascade**: Fields from Unit entity → target (overrides Business)
3. **Process carry-through**: Fields from source process → target (overrides Unit)
4. **Computed fields**: Engine-generated values (overrides everything)

### 4.3 Auto-Cascade Matching

When field name exists on both source entity and target entity:
- Match by custom field name (case-insensitive)
- Cascade value automatically
- No explicit config entry needed

### 4.4 Due Date Configuration

Per stage, configurable in YAML:
- Sales: 0 days (today)
- Onboarding: +14 days
- Implementation: +30 days

---

## 5. Assignee Rules

### 5.1 YAML-Configurable with Convention Fallback

Each stage config specifies `assignee_source`:

```yaml
stages:
  sales:
    assignee_source: rep  # default cascade
  onboarding:
    assignee_source: onboarding_specialist  # stage-specific field
  implementation:
    assignee_source: implementation_lead  # stage-specific field
```

### 5.2 Resolution Order

1. **Stage-specific field** (from YAML `assignee_source`) — if populated on source process
2. **Fixed GID** (from YAML `assignee_gid`) — for stages with a known assignee
3. **Unit.rep[0]** — first user in Unit's rep field
4. **Business.rep[0]** — fallback if Unit.rep empty
5. **None** — log warning, continue (graceful degradation)

---

## 6. Dependency Wiring

### Default Rules (all pipeline processes)

- **Dependents**: Unit, OfferHolder
- **Dependencies**: Open (non-completed) DNA plays from DNAHolder

### Init Action Wiring

- BackendOnboardABusiness → wired as dependency of Implementation process
- AssetEdit → wired as dependency of Implementation process
- SourceVideographer → no dependency wiring

### Correct for all stages 1-4 (stakeholder confirmed).

---

## 7. Comment Generation

### Init Action Pattern

Comments are implemented as init action handlers (not a built-in engine phase).

**Generalizable**: Different entity types get different comment templates:
- Pipeline processes get conversion lineage comments
- AssetEdit gets its own unique comment format (review legacy for specifics)

### Pipeline Process Comment

```
Pipeline Conversion

This {target_type} process was automatically created when "{source_name}" was converted on {date}.

Source: https://app.asana.com/0/{project_gid}/{task_gid}
Business: {business_name}
```

---

## 8. Validation Rules

### Configurable Per-Stage in YAML

```yaml
stages:
  sales:
    validation:
      pre_transition:
        required_fields: ["Contact Phone"]
        mode: warn  # warn or block
      post_transition:
        verify_fields: ["Vertical", "Contact Phone"]
```

### Modes

- **warn**: Log warning, continue transition (forgiving system default)
- **block**: Fail transition, return error result

---

## 9. Error Handling Philosophy

### Fail-Forward with Diagnostics

- **Never halt** a transition for non-critical failures
- Log detailed diagnostics (what failed, why, what was skipped)
- Return success with warnings via result accumulator pattern
- Each phase returns a result → engine accumulates → final result = success if creation succeeded

### Boundary Guards

- Narrow catches where safe (ValidationError for model casting in resolution)
- Keep broad catches at operation boundaries (top-level engine, per-item workflow processing)
- All errors logged via `autom8y_log` structured logging

### Template Fallback

- If template not found → create blank task with name only (not a hard failure)
- Log warning for ops team visibility

---

## 10. Configuration Architecture

### Central Project Registry (`core/project_registry.py`)

- **All** project GIDs centralized in one module
- Migrate PRIMARY_PROJECT_GID from entity classes to registry
- Entity classes reference registry (backward compatible)
- Lifecycle YAML references logical names, resolved via registry

### Lifecycle YAML

- Stage definitions with transitions, cascading sections, init actions
- Per-transition `auto_complete_prior` flag (explicit, not automatic)
- Assignee source per stage
- Validation rules per stage
- Due date offsets per stage

### Auto-Complete Rules

- Explicit per-transition in YAML: `auto_complete_prior: true/false`
- NOT automatic based on stage number comparison

---

## 11. Resolution Module Enhancements

### Cleanup

- Remove dead `ResolutionStrategyRegistry` (registry.py, 71 LOC)
- Remove unused `from_entity` param from `get_cached()`
- Remove unused `process_type` param from `process_async()` (or implement it)
- Narrow 2 broad catches in strategies.py to `ValidationError`
- Fix async mock warning in test_context.py

### Enhancements

- Add `resolve_holder_async(holder_type)` generic method to ResolutionContext
- Any additional convenience methods needed by lifecycle engine rewrite
- Better error reporting/diagnostics for resolution failures

---

## 12. Architectural Decisions (Stakeholder Delegated to Architect)

The stakeholder explicitly delegated these decisions to the architect:

1. **Module structure**: Whether to keep separate service classes, consolidate, use pipeline pattern, etc.
2. **Asana abstraction**: Whether to call AsanaClient directly, build a facade, extend ResolutionContext, or use SaveSession
3. **Orchestration phases**: Current 5-phase can merge Wire into Configure (both are PUT calls). Also needs set_subtask for hierarchy placement
4. **Error handling pattern**: Fail-forward with diagnostics vs result accumulator — architect chooses optimal implementation
5. **Quality gates**: Architect defines appropriate gates for each workstream

---

## 13. Legacy Pipeline Behaviors to Preserve

The architect should explore `src/autom8_asana/automation/pipeline.py` during implementation for:

- **Field seeding exact behavior**: FieldSeeder value resolution, enum handling, missing field handling
- **Comment generation details**: Exact format per entity type, timing, metadata included
- **Overall orchestration + edge cases**: Full flow, error paths, retry behavior
- **AssetEdit comment format**: Unique comment template used for asset_edit init from Implementation

---

## 14. Key Constraints (Must Not Change)

| Constraint | Rationale |
|------------|-----------|
| ResolutionContext is async context manager | Session cache lifecycle (ADR-002) |
| API budget default = 8 calls | Prevents runaway chains |
| Strategy order: Cache→Nav→Dep→Hierarchy | Cheapest first (ADR-004) |
| Template-based creation (with blank fallback) | Production workflows depend on template defaults |
| ProcessType enum = YAML stage names | Engine maps `process_type.value` → `config.get_stage()` |
| 5-phase order (with Configure/Wire merge OK) | Asana requires valid GID before wiring |
| Lifecycle webhook = separate from existing inbound | Different payloads, auth, dispatch (ADR analysis) |

---

## 15. Test Strategy

- **Keep existing tests** where modules are unchanged (resolution, models)
- **Rewrite tests** alongside rewritten lifecycle modules
- **Add integration tests** for full workflow chain (PipelineTransitionWorkflow→engine→Asana mock)
- **Behavior-driven**: Tests should validate business outcomes, not implementation details

---

## Appendix A: Complete DNC Routing Table (Stages 1-4)

| Source Stage | Outcome | Target | Action |
|-------------|---------|--------|--------|
| Outreach | CONVERTED | Sales | Create new Sales process |
| Outreach | DNC | Outreach | [Self-loop — deferred from this sprint] |
| Sales | CONVERTED | Onboarding | Create new Onboarding process |
| Sales | DNC | Outreach | **Create new** Outreach process |
| Onboarding | CONVERTED | Implementation | Create new Implementation process |
| Onboarding | DNC | Sales | **Reopen** most recent Sales (incomplete + Opportunity section) |
| Implementation | CONVERTED | [Terminal] | Terminal actions only (stages 5+ deferred) |
| Implementation | DNC | Outreach | **Create new** Outreach process |

## Appendix B: Init Actions by Stage (Stages 1-4)

| Stage | Init Action | Condition | Entity | Placement |
|-------|-------------|-----------|--------|-----------|
| Onboarding | products_check | `video*` in Unit.products | SourceVideographer | VideographyHolder |
| Onboarding | create_comment | Always | — | On new process |
| Implementation | play_creation (BOAB) | Reopen-or-create (90d threshold) | BackendOnboardABusiness | DNAHolder |
| Implementation | entity_creation | Duplicate check in holder | AssetEdit | AssetEditHolder |
| Implementation | create_comment | Always | — | On new process |
| All stages | create_comment | On CONVERTED creation | — | On new process |

## Appendix C: Cascading Sections (Stages 1-4)

| Stage | Offer Section | Unit Section | Business Section |
|-------|--------------|--------------|------------------|
| Outreach | Sales Process | Engaged | OPPORTUNITY |
| Sales | Sales Process | Next Steps | OPPORTUNITY |
| Onboarding | ACTIVATING | Onboarding | ONBOARDING |
| Implementation | IMPLEMENTING | Implementing | IMPLEMENTING |

## Appendix D: Interview Decision Log

| Round | Topic | Decision |
|-------|-------|----------|
| 1 | Deploy model | Defer — engine correctness first |
| 1 | Stub priority | EntityCreation only |
| 1 | PCR strategy | Absorb into lifecycle engine |
| 1 | Stage scope | Sales through Implementation (1-4) |
| 2 | Validation | Configurable per-stage in YAML |
| 2 | Comments | Preserve as init action handler |
| 2 | Field seeding | Auto-cascade matching names + review/rewrite |
| 2 | PCR instances | Sales→Onboarding only |
| 3 | Seed defaults | Auto-cascade matching names (zero config) |
| 3 | AssetEdit flow | Template-based under AssetEditHolder |
| 3 | Hierarchy wiring | Rewrite to use ResolutionContext |
| 3 | Assignee rules | YAML-configurable with convention fallback |
| 4 | Assignee config | YAML per stage with ProcessType fallback |
| 4 | Error handling | Narrow where safe |
| 4 | Rewrite strategy | Selective rewrite → full rewrite |
| 4 | GID config | Central config module |
| 5 | Rewrite scope | Full rewrite of all lifecycle modules |
| 5 | Test strategy | Keep existing + rewrite alongside modules |
| 5 | Resolution scope | Cleanup + enhance for lifecycle |
| 5 | Integration tests | Full workflow chain |
| 6 | Phase ordering | Merge Wire into Configure, add set_subtask |
| 6 | Section names | Accurate for stages 1-4 |
| 6 | Templates | Mixed reliability — blank fallback needed |
| 6 | Auto-completion | Explicit per-transition in YAML |
| 7 | set_subtask | Generalized hierarchy placement (any entity→holder) |
| 7 | Auto-complete rules | Explicit per-transition YAML config |
| 7 | Template fallback | Create blank task with name only |
| 7 | GID registry scope | All project GIDs centralized |
| 8 | Module structure | Architect decides |
| 8 | Asana abstraction | Architect decides |
| 8 | Comments implementation | Init action handler (generalizable) |
| 8 | Error philosophy | Fail-forward / result accumulator (architect decides) |
| 9 | Field mappings | Not needed — names consistent |
| 9 | Due dates | Correct as documented |
| 9 | Product rules | Only video*→SourceVideographer |
| 9 | DNC scope | Both CONVERTED and DNC for all stages |
| 10 | Self-loops | Deferred — not needed for stages 1-4 |
| 10 | Wiring rules | Correct as documented |
| 10 | Audit trail | Both result object + structured log |
| 10 | Monitoring | Structured logging sufficient; observability separate initiative |
| 11 | Resolution API | Add generic resolve_holder_async() |
| 11 | Registry scope | All project GIDs centralized |
| 11 | Delivery | Main branch commits |
| 11 | Conventions | Improve on existing patterns |
| 12 | DNC behavior | Create new (Sales/Impl DNC) or reopen (Onboarding DNC) |
| 12 | Similarity check | ProcessType + same Unit match |
| 12 | Reopen-or-create | Generic configurable pattern |
| 12 | Legacy review | Architect explores during sprint |
| 13 | DNC routing | Confirmed: Sales→Outreach, Onboarding→reopen Sales, Impl→Outreach |
| 13 | Reopen find | Most recent Sales in ProcessHolder (section-based, not completion-based) |
| 14 | Reopen mechanic | Mark incomplete + move to Opportunity section |
| 14 | DNC Outreach | Same as forward-path creation |
| 14 | YAML routing | Add both DNC→Outreach routes |
| 14 | Reopen scope | Only CONVERTED processes can be reopened (DNC is terminal) |
| 15 | DNC confirm | Final routing verified |
| 15 | Legacy review | Architect explores during sprint |
| 15 | Quality gates | Architect defines |
