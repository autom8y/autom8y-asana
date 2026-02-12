---
artifact_id: PRD-lifecycle-engine-hardening
title: "Lifecycle Engine Hardening: Full Rewrite + PCR Absorption (Stages 1-4)"
created_at: "2026-02-11T20:00:00Z"
author: requirements-analyst
status: draft
complexity: SERVICE
impact: high
impact_categories: [data_model, api_contract, cross_service]
related_adrs:
  - ADR-002-session-caching-strategy
  - ADR-004-strategy-registration-pattern
  - ADR-006-lifecycle-dag-model
  - ADR-008-entity-creation-delegation
stakeholders:
  - product-owner
  - engineering
success_criteria:
  - id: SC-001
    description: "All 8 transition paths (4 CONVERTED + 4 DNC) produce correct business outcomes per routing table"
    testable: true
    priority: must-have
  - id: SC-002
    description: "PCR is fully absorbed -- Sales to Onboarding conversion handled by lifecycle engine, not PipelineConversionRule"
    testable: true
    priority: must-have
  - id: SC-003
    description: "Auto-cascade field seeding works with zero config for matching field names"
    testable: true
    priority: must-have
  - id: SC-004
    description: "Integration tests cover full workflow chain (PipelineTransitionWorkflow -> engine -> creation -> Asana mock)"
    testable: true
    priority: must-have
  - id: SC-005
    description: "All pre-existing 8588+ tests continue passing with zero regressions"
    testable: true
    priority: must-have
  - id: SC-006
    description: "Structured audit logging emitted for every transition via autom8y_log"
    testable: true
    priority: must-have
  - id: SC-007
    description: "Malformed YAML config causes fail-fast at startup, not runtime errors during transitions"
    testable: true
    priority: must-have
  - id: SC-008
    description: "QA validates all acceptance criteria across all functional requirements"
    testable: true
    priority: must-have
schema_version: "1.0"
---

## 1. Executive Summary

The lifecycle engine hardening initiative is a full production rewrite of all lifecycle engine modules (from TDD specs) combined with absorption of the PipelineConversionRule (PCR) for pipeline stages 1 through 4 (Outreach, Sales, Onboarding, Implementation). The existing prototype delivered by R&D provides working resolution primitives and a functional-but-stub-laden lifecycle engine. This sprint replaces prototype code with production-quality implementations covering both CONVERTED and DID NOT CONVERT transitions, entity creation (Process, AssetEdit, BOAB, Videographer), auto-cascade field seeding, YAML-configurable assignee resolution, duplicate detection, dependency wiring, structured audit logging, and config validation -- all driven by a central project registry and Pydantic-validated YAML configuration.

**Source**: Stakeholder Context Section 1; Transfer doc Section 7 (GO with conditions); Audit report Section 3.

---

## 2. Scope

### 2.1 In Scope

| Area | Description | Source |
|------|-------------|--------|
| Full lifecycle module rewrite | Production-quality rewrite of all lifecycle engine modules from TDD specs | SC-1 |
| PCR absorption | Migrate Sales-to-Onboarding conversion logic into lifecycle engine | SC-1 |
| Pipeline stages 1-4 | Outreach, Sales, Onboarding, Implementation | SC-1 |
| Both transition types | CONVERTED and DID NOT CONVERT for all 4 stages | SC-1 |
| EntityCreationHandler | Complete implementation for AssetEdit (template-based under AssetEditHolder) | SC-1 |
| Resolution cleanup | Dead code removal, `resolve_holder_async()`, narrow exception catches | SC-11 |
| Central project registry | New `core/project_registry.py` for all project GIDs | SC-10 |
| Integration tests | Full workflow chain (PipelineTransitionWorkflow -> engine -> creation -> Asana mock) | SC-1, SC-15 |
| Comment generation | Init action handler for transition comments (generalizable) | SC-7 |
| Auto-cascade field seeding | Smart defaults where matching field names cascade automatically | SC-4 |
| Structured audit logging | AutomationResult + structured log events per transition | SC-10, SC-24 |
| Duplicate detection | ProcessType + Unit match, reopen-or-create pattern | SC-3 |
| YAML config validation | Pydantic model validation at startup, DAG integrity check | SC-10, Audit GAP-04 |
| DNC reopen mechanics | Onboarding DNC reopens existing Sales process | SC-12, SC-13, SC-14 |

**Source**: Stakeholder Context Section 1 "IN SCOPE".

### 2.2 Out of Scope

| Area | Rationale | Source |
|------|-----------|--------|
| Trigger mechanism (webhook/polling registration) | Deferred -- focus on engine correctness first | SC-1, Interview R1 |
| CampaignHandler | External API dependency not explored; remains stub | SC-1 |
| Tag-based dispatch | Deferred -- no production usage currently | SC-1 |
| Self-loop iteration tracking | Not needed for stages 1-4 (applies to Outreach/Reactivation only) | SC-1, Interview R10 |
| Stages 5-10 (Month1, Retention, Reactivation, AccountError, Expansion) | Deferred to future sprint | SC-1 |
| Observability metrics (Prometheus/StatsD) | Separate initiative; structured logging sufficient | SC-1, Interview R10 |
| Shadow mode / PCR comparison | Not needed -- direct absorption since only one active PCR instance | SC-1, Interview R1 |
| Rate limit handling | Verify at transport layer; engine-level retry deferred | Audit GAP-06 |
| Webhook HMAC auth | Deferred with webhook registration | Audit GAP-02 |

**Source**: Stakeholder Context Section 1 "OUT OF SCOPE"; Interview Decision Log.

---

## 3. Functional Requirements

### 3.1 Routing (FR-ROUTE)

#### FR-ROUTE-001: Outreach CONVERTED to Sales

**Description**: When an Outreach process transitions to CONVERTED, the engine creates a new Sales process.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: A new Sales process is created as a subtask of the ProcessHolder
- AC-2: The new process is placed after the source Outreach process (`insert_after`)
- AC-3: Template from Sales project's TEMPLATE section is used; blank task with generated name if no template found
- AC-4: Cascading sections are updated: Offer="Sales Process", Unit="Next Steps", Business="OPPORTUNITY"
- AC-5: Source Outreach process is auto-completed if `auto_complete_prior: true` in YAML

**Source**: Stakeholder Context Section 2 (Routing DAG), Appendix A, Appendix C.

#### FR-ROUTE-002: Sales CONVERTED to Onboarding (PCR Absorption)

**Description**: When a Sales process transitions to CONVERTED, the engine creates a new Onboarding process. This replaces the existing PipelineConversionRule behavior.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: A new Onboarding process is created as a subtask of the ProcessHolder
- AC-2: The new process is placed after the source Sales process (`insert_after`)
- AC-3: Template from Onboarding project's TEMPLATE section is used; blank task fallback
- AC-4: Cascading sections are updated: Offer="ACTIVATING", Unit="Onboarding", Business="ONBOARDING"
- AC-5: Due date is set to today + 14 days
- AC-6: Init actions execute: products_check (conditional on `video*` in Unit.products), create_comment
- AC-7: This path produces identical business outcomes to the existing PCR for Sales-to-Onboarding

**Source**: Stakeholder Context Section 2, Section 4.4, Appendix A, Appendix B; Interview R1 (PCR absorption), R2.

#### FR-ROUTE-003: Onboarding CONVERTED to Implementation

**Description**: When an Onboarding process transitions to CONVERTED, the engine creates a new Implementation process.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: A new Implementation process is created as a subtask of the ProcessHolder
- AC-2: The new process is placed after the source Onboarding process (`insert_after`)
- AC-3: Template from Implementation project's TEMPLATE section is used; blank task fallback
- AC-4: Cascading sections are updated: Offer="IMPLEMENTING", Unit="Implementing", Business="IMPLEMENTING"
- AC-5: Due date is set to today + 30 days
- AC-6: Init actions execute: play_creation (BOAB, reopen-or-create), entity_creation (AssetEdit), create_comment

**Source**: Stakeholder Context Section 2, Appendix A, Appendix B.

#### FR-ROUTE-004: Implementation CONVERTED (Terminal)

**Description**: When an Implementation process transitions to CONVERTED, no new process is created within stages 1-4 scope. Terminal actions only.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: No new process is created (stages 5+ deferred)
- AC-2: Source process auto-completion follows YAML config
- AC-3: Engine returns a terminal result indicating successful transition with no forward routing

**Source**: Stakeholder Context Section 2 (TERMINAL for stages 1-4 scope), Interview R1.

### 3.2 DNC Routing (FR-DNC)

#### FR-DNC-001: Sales DNC to Outreach

**Description**: When a Sales process transitions to DID NOT CONVERT, the engine creates a new Outreach process.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: A new Outreach process is created (not a reopen)
- AC-2: Process is created as subtask of ProcessHolder, placed after source
- AC-3: Template from Outreach project's TEMPLATES section is used; blank task fallback
- AC-4: Cascading sections are updated: Offer="Sales Process", Unit="Engaged", Business="OPPORTUNITY"
- AC-5: Field seeding cascades from source Sales process to new Outreach process

**Source**: Stakeholder Context Section 2 (DNC Transitions), Appendix A; Interview R13, R14.

#### FR-DNC-002: Onboarding DNC Reopens Sales

**Description**: When an Onboarding process transitions to DID NOT CONVERT, the engine reopens the most recent Sales process under the ProcessHolder instead of creating a new process.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Engine searches ProcessHolder subtasks for the most recent Sales process (by ProcessType match)
- AC-2: The found Sales process is marked incomplete (`completed = false`)
- AC-3: The found Sales process is moved to the "Opportunity" section in the Sales project
- AC-4: No new entity creation occurs
- AC-5: If no Sales process is found in the ProcessHolder, the engine logs a warning and returns a diagnostic result (fail-forward)

**Source**: Stakeholder Context Section 2 (DNC Reopen Mechanics), Section 2 (Key Distinction); Interview R12, R13, R14.

#### FR-DNC-003: Implementation DNC to Outreach

**Description**: When an Implementation process transitions to DID NOT CONVERT, the engine creates a new Outreach process.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: A new Outreach process is created (not a reopen)
- AC-2: Process is created as subtask of ProcessHolder, placed after source
- AC-3: Template from Outreach project's TEMPLATES section is used; blank task fallback
- AC-4: Cascading sections are updated: Offer="Sales Process", Unit="Engaged", Business="OPPORTUNITY"
- AC-5: Field seeding cascades from source Implementation process to new Outreach process

**Note**: The current prototype YAML (`lifecycle_stages.yaml`) incorrectly routes Implementation DNC to `sales`. The stakeholder confirmed the correct target is `outreach` (Interview R13, R14). The YAML must be corrected.

**Source**: Stakeholder Context Section 2, Appendix A; Interview R13, R14.

#### FR-DNC-004: Outreach DNC (Self-Loop Deferred)

**Description**: Outreach DNC self-loop behavior is deferred from this sprint.

**Priority**: P2 (deferred)

**Acceptance Criteria**:
- AC-1: Engine recognizes the transition target but takes no action (or logs that self-loop is deferred)
- AC-2: No error is raised for this transition path

**Source**: Stakeholder Context Section 1 (OUT OF SCOPE), Appendix A; Interview R10.

### 3.3 Entity Creation (FR-CREATE)

#### FR-CREATE-001: Process Creation (Forward Transitions)

**Description**: For all CONVERTED and DNC transitions that create new processes, the engine follows a standardized creation flow.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Template discovered from target project's template section (section name per YAML config)
- AC-2: If no template found, a blank task is created with a generated name containing `[Business Name]` and `[Unit Name]` placeholders replaced
- AC-3: Template fallback logs a warning for ops visibility
- AC-4: New process is placed under ProcessHolder as subtask via `resolve_holder_async()`
- AC-5: New process is inserted after the source process (`insert_after=source_process`)
- AC-6: `[Business Name]` and `[Unit Name]` placeholders in template name are replaced with actual values

**Source**: Stakeholder Context Section 3.1.

#### FR-CREATE-002: AssetEdit Creation (Implementation Init Action)

**Description**: When Implementation process is created, an AssetEdit entity is created from a template and placed under the Business's AssetEditHolder.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: AssetEdit is created from template in AssetEditHolder project (GID: 1203992664400125)
- AC-2: AssetEdit is placed as subtask of Business's AssetEditHolder via `resolve_holder_async()`
- AC-3: Fields are seeded, assignee set, due date set (same patterns as process creation)
- AC-4: AssetEdit is wired as dependency of the Implementation process
- AC-5: Duplicate detection checks AssetEditHolder for existing AssetEdit before creating

**Source**: Stakeholder Context Section 3.3, Section 6 (init action wiring).

#### FR-CREATE-003: BackendOnboardABusiness Play Creation (Implementation Init Action)

**Description**: When Implementation process is created, a BOAB play is created or reopened using the reopen-or-create pattern.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: If no completed BOAB in last 90 days exists in DNAHolder, create new from template in DNAHolder project
- AC-2: If a completed BOAB exists within 90 days, reopen existing (mark incomplete)
- AC-3: BOAB is placed as subtask of Business's DNAHolder via `resolve_holder_async()`
- AC-4: BOAB is wired as dependency of the Implementation process
- AC-5: Reopen threshold is configurable: `reopen_if_completed_within_days: 90`

**Source**: Stakeholder Context Section 3.4, Section 6; Interview R12.

#### FR-CREATE-004: SourceVideographer Creation (Onboarding Init Action, Conditional)

**Description**: When Onboarding process is created, a SourceVideographer entity is conditionally created based on the Unit's products field.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Condition check: Unit.products field is matched against `video*` pattern (fnmatch)
- AC-2: If condition is true, SourceVideographer is created from template in VideographyHolder project (GID: 1207984018149338)
- AC-3: SourceVideographer is placed as subtask of Business's VideographyHolder via `resolve_holder_async()`
- AC-4: No dependency wiring (standalone entity)
- AC-5: If condition is false, no entity is created and no error is raised

**Source**: Stakeholder Context Section 3.5, Appendix B; Interview R9.

### 3.4 Duplicate Detection (FR-DUP)

#### FR-DUP-001: Process Duplicate Detection

**Description**: Before creating a new process, the engine checks the ProcessHolder for existing processes with the same ProcessType and Unit.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Similarity criteria: same ProcessType + same Unit (BusinessUnit level, not Business level)
- AC-2: Check location: ProcessHolder subtasks (not dependency links)
- AC-3: Only non-completed processes are considered duplicates (completed processes are not candidates)
- AC-4: Processes in DID NOT CONVERT sections are terminal and cannot be reopened

**Source**: Stakeholder Context Section 3.2; Interview R12.

#### FR-DUP-002: Reopen-or-Create Pattern

**Description**: A configurable pattern that checks for existing entities before creating new ones. Used by BOAB, AssetEdit, and Onboarding DNC reopen.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: If existing non-completed entity found AND within staleness threshold, reopen existing
- AC-2: If no match found OR entity is stale, create new
- AC-3: Configurable per init action: `reopen_if_completed_within_days: N` or `always_create_new: true`
- AC-4: Only CONVERTED processes can be reopened; DNC state is terminal

**Source**: Stakeholder Context Section 3.2 (Reopen-or-create pattern); Interview R12, R14.

### 3.5 Field Seeding (FR-SEED)

#### FR-SEED-001: Auto-Cascade Matching

**Description**: Fields with matching names on both source and target entities cascade automatically with zero explicit configuration.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: When a custom field name exists on both source entity and target entity, the value cascades automatically
- AC-2: Field name matching is case-insensitive
- AC-3: No explicit YAML config entry is required for matching-name cascades
- AC-4: YAML config is only needed for exclusions (fields that should NOT cascade) and computed fields

**Source**: Stakeholder Context Section 4.1, Section 4.3; Interview R3, R9.

#### FR-SEED-002: Cascade Precedence Layers

**Description**: When multiple sources provide values for the same field, later layers override earlier ones.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Layer 1 (lowest priority): Business entity fields cascade to target
- AC-2: Layer 2: Unit entity fields cascade to target (overrides Business)
- AC-3: Layer 3: Source process fields cascade to target (overrides Unit)
- AC-4: Layer 4 (highest priority): Computed fields from engine (overrides everything)
- AC-5: Each layer only overrides when it has a non-empty value for the field

**Source**: Stakeholder Context Section 4.2.

#### FR-SEED-003: Due Date Configuration

**Description**: Each stage has a configurable due date offset applied at creation time.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Sales: due date = today (0 days offset)
- AC-2: Onboarding: due date = today + 14 days
- AC-3: Implementation: due date = today + 30 days
- AC-4: Due date offsets are configurable per stage in YAML (`due_date_offset_days`)

**Source**: Stakeholder Context Section 4.4.

### 3.6 Assignee (FR-ASSIGN)

#### FR-ASSIGN-001: YAML-Configurable Assignee Resolution

**Description**: Each stage specifies an assignee source in YAML, with a cascade fallback chain.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Resolution order: (1) Stage-specific field from YAML `assignee_source` if populated on source, (2) Fixed GID from YAML `assignee_gid`, (3) `Unit.rep[0]` (first user in Unit's rep field), (4) `Business.rep[0]` (fallback if Unit.rep empty), (5) None with warning logged
- AC-2: Sales uses `assignee_source: rep` (default cascade)
- AC-3: Onboarding uses `assignee_source: onboarding_specialist`
- AC-4: Implementation uses `assignee_source: implementation_lead`
- AC-5: If all sources are empty, the engine logs a warning and continues (graceful degradation, no error)

**Source**: Stakeholder Context Section 5.

### 3.7 Hierarchy Placement (FR-HIER)

#### FR-HIER-001: Resolution-Based Hierarchy Placement

**Description**: All entity creation uses resolution-based hierarchy placement via `resolve_holder_async()`.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Process entities are placed under ProcessHolder
- AC-2: DNA/Play entities are placed under DNAHolder
- AC-3: AssetEdit entities are placed under AssetEditHolder
- AC-4: Videography entities are placed under VideographyHolder
- AC-5: Placement uses `set_parent()` after resolving the appropriate holder
- AC-6: `resolve_holder_async(holder_type)` is a generic method on ResolutionContext

**Source**: Stakeholder Context Section 3.6, Section 11; Interview R7.

### 3.8 Comments (FR-COMMENT)

#### FR-COMMENT-001: Pipeline Process Conversion Comment

**Description**: When a pipeline process is created via a CONVERTED transition, a comment is added to the new process documenting the conversion lineage.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Comment is added as an init action handler (not a built-in engine phase)
- AC-2: Comment includes: target process type, source process name, conversion date, source Asana URL, business name
- AC-3: Comment format matches the template specified in Stakeholder Context Section 7
- AC-4: Comment handler is generalizable -- different entity types can have different comment templates

**Source**: Stakeholder Context Section 7, Appendix B; Interview R2, R8.

#### FR-COMMENT-002: AssetEdit Comment

**Description**: When an AssetEdit entity is created, a comment with its own unique format is added.

**Priority**: P1

**Acceptance Criteria**:
- AC-1: AssetEdit gets a comment using a format derived from legacy behavior (architect to review during sprint)
- AC-2: Comment handler reuses the generalizable init action pattern from FR-COMMENT-001

**Source**: Stakeholder Context Section 7, Section 13; Interview R8.

### 3.9 Validation (FR-VALID)

#### FR-VALID-001: Per-Stage Configurable Validation

**Description**: Each stage can define pre-transition and post-transition validation rules in YAML, with configurable warn/block behavior.

**Priority**: P1

**Acceptance Criteria**:
- AC-1: YAML config supports `validation.pre_transition.required_fields` and `validation.post_transition.verify_fields` per stage
- AC-2: Mode `warn`: logs warning and continues transition (default behavior)
- AC-3: Mode `block`: fails the transition and returns an error result
- AC-4: Validation rules are evaluated before (pre) and after (post) the transition phase they guard

**Source**: Stakeholder Context Section 8; Interview R2.

### 3.10 Auto-Completion (FR-COMPLETE)

#### FR-COMPLETE-001: Explicit Per-Transition Auto-Completion

**Description**: Whether the source process is auto-completed after a transition is controlled explicitly per transition in YAML, not derived from stage ordering.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Each transition in YAML has an `auto_complete_prior` flag (true/false)
- AC-2: When `auto_complete_prior: true`, the source process is marked complete after successful creation of the target
- AC-3: When `auto_complete_prior: false`, the source process is left in its current state
- AC-4: Auto-completion is NOT automatic based on stage number comparison

**Source**: Stakeholder Context Section 10; Interview R6, R7.

### 3.11 Templates (FR-TMPL)

#### FR-TMPL-001: Template-Based Creation with Blank Fallback

**Description**: Entity creation attempts to use a template from the target project; falls back to blank task creation if no template is found.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Template discovery searches the target project's template section (section name per YAML)
- AC-2: If template is found, new entity is created by duplicating the template task
- AC-3: If no template is found, a blank task is created with a generated name only (no subtasks)
- AC-4: Template fallback logs a warning for operational visibility
- AC-5: Name generation replaces `[Business Name]` and `[Unit Name]` placeholders

**Source**: Stakeholder Context Section 3.1, Section 9; Interview R6, R7.

### 3.12 Configuration (FR-CONFIG)

#### FR-CONFIG-001: Central Project Registry

**Description**: All project GIDs are centralized in a single module (`core/project_registry.py`), replacing scattered GID constants across entity classes.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: A new `core/project_registry.py` module contains all project GIDs
- AC-2: `PRIMARY_PROJECT_GID` references from entity classes are migrated to use the registry
- AC-3: Entity classes remain backward compatible (can still reference their own constant, which delegates to registry)
- AC-4: Lifecycle YAML references logical stage names; GID resolution happens via the registry

**Source**: Stakeholder Context Section 10; Interview R4, R7, R11.

#### FR-CONFIG-002: Pydantic YAML Validation

**Description**: Lifecycle YAML configuration is validated at load time using Pydantic models, failing fast on malformed input.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: YAML config is validated against Pydantic models at startup
- AC-2: Missing required keys produce clear error messages at load time (not at transition time)
- AC-3: Invalid types, missing stage definitions, and malformed transition targets are caught at startup
- AC-4: Stage names referenced in transitions must exist as defined stages (DAG integrity check)

**Source**: Stakeholder Context Section 10; Audit Report GAP-04; Interview R2.

#### FR-CONFIG-003: ProcessType-to-Stage Mapping

**Description**: ProcessType enum values must match YAML stage names exactly, enabling `process_type.value` to `config.get_stage()` mapping.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: `ProcessType` enum values map 1:1 to YAML stage name keys
- AC-2: Engine uses `source_process.process_type.value` to look up stage config
- AC-3: DAG validation at startup confirms all ProcessType values have corresponding stage definitions (for stages 1-4)

**Source**: Stakeholder Context Section 14 (Constraints); Transfer doc Section 8.

### 3.13 Dependency Wiring (FR-WIRE)

#### FR-WIRE-001: Pipeline Default Wiring

**Description**: All pipeline processes are wired with standard dependents and dependencies.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Dependents: Unit and OfferHolder are wired as dependents of the new process
- AC-2: Dependencies: Open (non-completed) DNA plays from DNAHolder are wired as dependencies
- AC-3: Wiring rules apply to all stages 1-4

**Source**: Stakeholder Context Section 6; Interview R10.

#### FR-WIRE-002: Init Action Dependency Wiring

**Description**: Specific init action entities are wired as dependencies of the process that triggered them.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: BackendOnboardABusiness (BOAB) is wired as dependency of the Implementation process
- AC-2: AssetEdit is wired as dependency of the Implementation process
- AC-3: SourceVideographer has no dependency wiring (standalone)

**Source**: Stakeholder Context Section 6; Interview R10.

### 3.14 Error Handling (FR-ERR)

#### FR-ERR-001: Fail-Forward with Diagnostics

**Description**: The engine never halts a transition for non-critical failures. It logs diagnostics and returns success with warnings.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Non-critical failures (field seeding misses, assignee not found, comment creation failure) are logged and skipped
- AC-2: Each engine phase returns a result; engine accumulates results into a final composite result
- AC-3: Final result = success if entity creation succeeded, regardless of non-critical phase failures
- AC-4: Detailed diagnostics include: what failed, why, what was skipped
- AC-5: Narrow exception catches where safe (e.g., `ValidationError` for model casting in resolution)
- AC-6: Broad catches retained at operation boundaries (top-level engine, per-item workflow processing)

**Source**: Stakeholder Context Section 9; Interview R4, R8.

#### FR-ERR-002: Template Not Found Fallback

**Description**: When a template is not found, the engine creates a blank task instead of failing.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Missing template results in blank task creation with generated name
- AC-2: A warning is logged with the stage name and project GID for ops visibility
- AC-3: The transition continues to completion (field seeding, wiring, comments all proceed)

**Source**: Stakeholder Context Section 9; Interview R6, R7.

### 3.15 Audit Trail (FR-AUDIT)

#### FR-AUDIT-001: Structured Transition Logging

**Description**: Every transition produces both a result object and structured log events for operational visibility.

**Priority**: P0

**Acceptance Criteria**:
- AC-1: Each transition emits structured log events via `autom8y_log` including: source stage, target stage, outcome type, entity GIDs created, duration
- AC-2: Each transition produces an `AutomationResult` object capturing full lifecycle tracking
- AC-3: Warning-level events are emitted for non-critical failures (missing fields, template fallback, assignee not found)
- AC-4: Error-level events are emitted for critical failures (entity creation failure, holder resolution failure)

**Source**: Stakeholder Context Section 10; Interview R10.

---

## 4. DNC Routing Table (Formal Requirement)

This table defines the complete routing DAG for stages 1-4. All 8 paths are formally required.

| Source Stage | Outcome | Target Stage | Action | Init Actions | Source |
|-------------|---------|-------------|--------|-------------|--------|
| Outreach | CONVERTED | Sales | Create new Sales process | create_comment | SC-2, App A |
| Sales | CONVERTED | Onboarding | Create new Onboarding process (PCR absorption) | products_check (conditional), create_comment | SC-2, App A |
| Onboarding | CONVERTED | Implementation | Create new Implementation process | play_creation (BOAB), entity_creation (AssetEdit), create_comment | SC-2, App A |
| Implementation | CONVERTED | [Terminal] | Terminal actions only (stages 5+ deferred) | -- | SC-2, App A |
| Sales | DNC | Outreach | Create new Outreach process | -- | SC-2, App A |
| Onboarding | DNC | Sales | Reopen most recent Sales (mark incomplete, move to Opportunity) | -- | SC-2, App A |
| Implementation | DNC | Outreach | Create new Outreach process | -- | SC-2, App A |
| Outreach | DNC | [Deferred] | Self-loop deferred from this sprint | -- | SC-1 (OOS) |

### YAML Correction Required

The current `lifecycle_stages.yaml` has `implementation.transitions.did_not_convert: sales`. Per stakeholder confirmation (Interview R13, R14), the correct target is `outreach`. This must be corrected as part of this sprint.

**Source**: Stakeholder Context Section 2, Appendix A; Interview R13, R14, R15.

---

## 5. Init Actions by Stage

This table defines all init actions for stages 1-4, their conditions, and entity placement.

| Stage | Init Action | Type | Condition | Entity Created | Placement Target | Dep Wiring |
|-------|-------------|------|-----------|---------------|-----------------|------------|
| All stages | create_comment | Comment | On CONVERTED creation | -- (comment on process) | On new process | None |
| Onboarding | products_check | Conditional entity | `video*` in Unit.products (fnmatch) | SourceVideographer | VideographyHolder (GID: 1207984018149338) | None (standalone) |
| Onboarding | create_comment | Comment | Always on creation | -- (comment on process) | On new process | None |
| Implementation | play_creation (BOAB) | Reopen-or-create | No completed BOAB in 90 days | BackendOnboardABusiness | DNAHolder (GID: 1207507299545000) | Dependency of Implementation |
| Implementation | entity_creation | Duplicate check | Not already in AssetEditHolder | AssetEdit | AssetEditHolder (GID: 1203992664400125) | Dependency of Implementation |
| Implementation | create_comment | Comment | Always on creation | -- (comment on process) | On new process | None |

**Source**: Stakeholder Context Appendix B.

---

## 6. Cascading Sections by Stage

This table defines the section names applied to Offer, Unit, and Business entities when a process is created at each stage.

| Stage | Offer Section | Unit Section | Business Section |
|-------|--------------|--------------|------------------|
| Outreach | Sales Process | Engaged | OPPORTUNITY |
| Sales | Sales Process | Next Steps | OPPORTUNITY |
| Onboarding | ACTIVATING | Onboarding | ONBOARDING |
| Implementation | IMPLEMENTING | Implementing | IMPLEMENTING |

**Source**: Stakeholder Context Appendix C; Interview R6.

---

## 7. Non-Functional Requirements

### NFR-001: Zero Test Regressions

**Description**: All pre-existing 8588+ tests must continue passing after the rewrite.

**Acceptance Criteria**:
- All existing tests in the test suite pass without modification to tests outside lifecycle/ and resolution/ modules
- Tests for rewritten modules are rewritten alongside the modules
- No net reduction in test coverage

**Source**: Stakeholder Context Section 15; Success Criteria SC-005.

### NFR-002: Structured Logging for All Transitions

**Description**: Every transition emits structured log events via `autom8y_log`.

**Acceptance Criteria**:
- All log events include: transition source stage, target stage, outcome, timestamp
- Log events use structured fields (not string interpolation)
- Warning and error levels are used appropriately per FR-AUDIT-001

**Source**: Stakeholder Context Section 9, Section 10; Interview R10.

### NFR-003: Config Validation at Startup (Fail-Fast)

**Description**: Malformed YAML configuration is detected at load time, not at transition time.

**Acceptance Criteria**:
- Pydantic validation runs when `LifecycleConfig` is instantiated
- Missing required keys raise `ValidationError` with field path
- Startup fails with a clear error message before any transitions are processed

**Source**: Audit Report GAP-04; Interview R2.

### NFR-004: DAG Integrity Check

**Description**: All transition targets in the YAML must reference defined stages.

**Acceptance Criteria**:
- At config load time, every value in `transitions.converted` and `transitions.did_not_convert` is verified to exist as a defined stage key (or null for terminal)
- Invalid references produce a clear error with the offending stage name and transition

**Source**: Audit Report GAP-04; Stakeholder Context Section 10.

### NFR-005: No Circular Imports

**Description**: No circular import dependencies between resolution/, lifecycle/, and models/ packages.

**Acceptance Criteria**:
- Import graph: `lifecycle/` may import from `resolution/` and `models/`
- Import graph: `resolution/` may import from `models/business/`
- No reverse dependencies (`models/` does not import from `lifecycle/` or `resolution/`)
- Verified by import tracing or static analysis

**Source**: Audit Report Section 2.1 (clean import graph); Stakeholder Context Section 11.

---

## 8. Constraints (Must Not Change)

These constraints are load-bearing architectural decisions from R&D. Violating any of them requires escalation.

| ID | Constraint | Rationale | Source |
|----|-----------|-----------|--------|
| C-001 | ResolutionContext is an async context manager | Session cache lifecycle (ADR-002) | SC-14, Transfer S8 |
| C-002 | API budget default = 8 calls | Prevents runaway resolution chains | SC-14, Transfer S8 |
| C-003 | Strategy order: Cache -> Nav -> Dep -> Hierarchy | Cheapest first (ADR-004) | SC-14, Transfer S8 |
| C-004 | Template-based creation with blank fallback | Production workflows depend on template defaults | SC-14, Transfer S8 |
| C-005 | ProcessType enum = YAML stage names | Engine maps `process_type.value` to `config.get_stage()` | SC-14, Transfer S8 |
| C-006 | 5-phase order (Create -> Configure -> Wire -> Actions -> Dependencies) with Configure/Wire merge OK | Asana requires valid GID before wiring | SC-14, Transfer S8 |
| C-007 | Lifecycle webhook = separate from existing inbound | Different payloads, auth, dispatch | SC-14, Audit GAP-02 |

**Source**: Stakeholder Context Section 14; Transfer doc Section 8.

---

## 9. Out of Scope (Explicit Boundaries)

These items are explicitly deferred to prevent scope creep. Any request to include them must be escalated.

| Item | Rationale | Planned For |
|------|-----------|-------------|
| Webhook registration in `api/main.py` | Deferred -- engine correctness first | Post-hardening sprint |
| CampaignHandler implementation | External API dependency not explored | Post-hardening sprint |
| Tag-based dispatch routing | No production usage currently | Post-hardening sprint |
| Self-loop iteration tracking / delay schedules | Not needed for stages 1-4 | Post-hardening sprint |
| Stages 5-10 (Month1 through Expansion) | Future sprint scope | TBD |
| Observability metrics (Prometheus/StatsD) | Separate initiative; structured logging sufficient for now | Observability initiative |
| Shadow mode / PCR comparison testing | Not needed -- direct absorption | N/A |
| Rate limit retry at engine level | Verify transport layer first | Post-hardening if needed |
| Per-stage feature flags | Architect decides if needed for rollout | Architect discretion |

**Source**: Stakeholder Context Section 1 (OUT OF SCOPE); Interview Decision Log R1, R10.

---

## 10. Success Criteria

### What "Done" Looks Like

| ID | Criterion | Verification | Priority |
|----|-----------|-------------|----------|
| SC-001 | All 8 transition paths (4 CONVERTED + 4 DNC) produce correct business outcomes per Section 4 routing table | Integration tests + unit tests per transition | must-have |
| SC-002 | PCR is fully absorbed -- Sales-to-Onboarding handled by lifecycle engine | Integration test demonstrating Sales CONVERTED producing Onboarding process with all fields, sections, and init actions | must-have |
| SC-003 | Auto-cascade field seeding works with zero config for matching field names | Unit tests with mock entities having overlapping custom fields; verify cascade without explicit config | must-have |
| SC-004 | Integration tests cover full workflow chain | PipelineTransitionWorkflow -> LifecycleEngine -> EntityCreationService -> Asana mock, verifying end-to-end outcomes | must-have |
| SC-005 | All pre-existing 8588+ tests continue passing | Full test suite run: `.venv/bin/pytest tests/ -x -q --timeout=60` | must-have |
| SC-006 | Structured audit logging emitted for every transition | Log capture tests verify structured fields per transition | must-have |
| SC-007 | Malformed YAML causes fail-fast at startup | Unit tests with intentionally malformed configs; verify `ValidationError` at load time | must-have |
| SC-008 | QA validates all acceptance criteria | QA Adversary reviews all FR-* acceptance criteria and signs off | must-have |

**Source**: Stakeholder Context Sections 1, 15; Transfer doc Section 7.

---

## 11. Resolution Module Cleanup (Supporting Requirements)

These are not new features but cleanup tasks required to support the lifecycle engine rewrite.

| ID | Task | Current State | Required State | Source |
|----|------|---------------|----------------|--------|
| RES-001 | Remove dead `ResolutionStrategyRegistry` | 71 LOC, never used | Deleted | Audit S4 |
| RES-002 | Remove unused `from_entity` param from `get_cached()` | Declared but never used | Removed | Audit S4 |
| RES-003 | Remove unused `process_type` param from `process_async()` | Declared but ignored | Removed or implemented | Audit S4 |
| RES-004 | Narrow 2 broad catches in `strategies.py` to `ValidationError` | `except Exception` at lines 178, 280 | `except ValidationError` | Audit S6 |
| RES-005 | Fix async mock warning in `test_context.py` | RuntimeWarning for unawaited coroutine | Clean test output | Audit S5 |
| RES-006 | Add `resolve_holder_async(holder_type)` to ResolutionContext | Does not exist | Generic method for any holder type | SC-11 |

**Source**: Stakeholder Context Section 11; Audit Report Sections 4, 5, 6.

---

## 12. Stakeholder Alignment Record

### Confirmed Decisions (Interview Decision Log)

| Decision | Round | Confirmed By | Status |
|----------|-------|-------------|--------|
| PCR absorption strategy (not shadow mode) | R1 | Stakeholder | Confirmed |
| Stage scope: 1-4 only | R1 | Stakeholder | Confirmed |
| Full rewrite (not selective) | R4-R5 | Stakeholder | Confirmed |
| Auto-cascade field seeding (zero config for matching names) | R3, R9 | Stakeholder | Confirmed |
| DNC routing: Sales->Outreach, Onboarding->reopen Sales, Impl->Outreach | R12-R15 | Stakeholder | Confirmed |
| Reopen mechanic: mark incomplete + move to Opportunity | R14 | Stakeholder | Confirmed |
| Architecture decisions delegated to architect | R8 | Stakeholder | Confirmed |
| Quality gates defined by architect | R15 | Stakeholder | Confirmed |
| Comments as init action handler (generalizable) | R8 | Stakeholder | Confirmed |
| Explicit auto-completion per-transition YAML | R6, R7 | Stakeholder | Confirmed |
| Central project registry for all GIDs | R7, R11 | Stakeholder | Confirmed |

### Resolved Conflicts

None. The 15-round interview achieved alignment on all points without unresolved stakeholder conflicts.

### Assumptions

| Assumption | Basis | Confirmation Status |
|------------|-------|---------------------|
| Field names are consistent across projects (no mappings needed) | Stakeholder confirmation, Interview R9 | Confirmed |
| Only `video*` product pattern triggers SourceVideographer | Stakeholder confirmation, Interview R9 | Confirmed |
| Due date offsets (0, 14, 30 days) are correct per stage | Stakeholder confirmation, Interview R9 | Confirmed |
| Standard wiring (Unit + OfferHolder dependents, DNA dependencies) applies to all stages 1-4 | Stakeholder confirmation, Interview R10 | Confirmed |

### Open Questions

None. All questions were resolved during the 15-round stakeholder interview.

---

## 13. Requirements Traceability

| FR-ID | Stakeholder Source | Interview Round | Audit/Transfer Reference |
|-------|-------------------|-----------------|--------------------------|
| FR-ROUTE-001 | SC Section 2 | R1 | Transfer FR-2 |
| FR-ROUTE-002 | SC Section 2 | R1, R2 | Transfer FR-3 (PCR) |
| FR-ROUTE-003 | SC Section 2 | R1 | Transfer FR-2 |
| FR-ROUTE-004 | SC Section 2 | R1 | Transfer FR-2 |
| FR-DNC-001 | SC Section 2 | R13, R14 | -- |
| FR-DNC-002 | SC Section 2 | R12-R14 | -- |
| FR-DNC-003 | SC Section 2 | R13, R14 | -- |
| FR-DNC-004 | SC Section 1 (OOS) | R10 | -- |
| FR-CREATE-001 | SC Section 3.1 | R6, R7 | Transfer FR-2 |
| FR-CREATE-002 | SC Section 3.3 | R3 | Transfer GAP-01 |
| FR-CREATE-003 | SC Section 3.4 | R12 | Transfer FR-4 |
| FR-CREATE-004 | SC Section 3.5 | R9 | Transfer FR-4 |
| FR-DUP-001 | SC Section 3.2 | R12 | Transfer FR-2 |
| FR-DUP-002 | SC Section 3.2 | R12, R14 | Transfer FR-2 |
| FR-SEED-001 | SC Section 4.1, 4.3 | R3, R9 | Transfer FR-2 |
| FR-SEED-002 | SC Section 4.2 | R3 | Transfer FR-2 |
| FR-SEED-003 | SC Section 4.4 | R9 | Transfer FR-2 |
| FR-ASSIGN-001 | SC Section 5 | R3, R4 | Transfer FR-2 |
| FR-HIER-001 | SC Section 3.6 | R7 | Transfer FR-2 |
| FR-COMMENT-001 | SC Section 7 | R2, R8 | Transfer FR-2 |
| FR-COMMENT-002 | SC Section 7, 13 | R8 | Transfer FR-2 |
| FR-VALID-001 | SC Section 8 | R2 | Transfer GAP-04 |
| FR-COMPLETE-001 | SC Section 10 | R6, R7 | Transfer FR-2 |
| FR-TMPL-001 | SC Section 3.1, 9 | R6, R7 | Transfer FR-2 |
| FR-CONFIG-001 | SC Section 10 | R4, R7, R11 | Audit S7 |
| FR-CONFIG-002 | SC Section 10 | R2 | Transfer GAP-04 |
| FR-CONFIG-003 | SC Section 14 | -- | Transfer S8 |
| FR-WIRE-001 | SC Section 6 | R10 | Transfer FR-2 |
| FR-WIRE-002 | SC Section 6 | R10 | Transfer FR-2 |
| FR-ERR-001 | SC Section 9 | R4, R8 | Transfer GAP-03 |
| FR-ERR-002 | SC Section 9 | R6, R7 | Transfer FR-2 |
| FR-AUDIT-001 | SC Section 10 | R10 | Transfer GAP-05 |

Key: SC = Stakeholder Context document; R# = Interview Round.

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| Stakeholder Context (source) | `/Users/tomtenuta/Code/autom8_asana/docs/planning/STAKEHOLDER-CONTEXT-lifecycle-hardening.md` | Read |
| Audit Report (source) | `/Users/tomtenuta/Code/autom8_asana/docs/planning/AUDIT-workflow-resolution-platform.md` | Read |
| Transfer Doc (source) | `/Users/tomtenuta/Code/autom8_asana/docs/transfer/TRANSFER-workflow-resolution-platform.md` | Read |
| Lifecycle YAML (source) | `/Users/tomtenuta/Code/autom8_asana/config/lifecycle_stages.yaml` | Read |
| PRD Schema | `/Users/tomtenuta/Code/autom8_asana/.claude/skills/templates/doc-artifacts/schemas/prd-schema.md` | Read |
| This PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-lifecycle-engine-hardening.md` | Written |
