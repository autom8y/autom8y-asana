# PRD: Automation Layer

## Metadata
- **PRD ID**: PRD-AUTOMATION-LAYER
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-18
- **Last Updated**: 2025-12-18
- **Stakeholders**: SDK developers, automation consumers, pipeline operators
- **Related PRDs**: None (foundational capability)
- **Discovery**: [DISCOVERY-AUTOMATION-LAYER.md](/docs/analysis/DISCOVERY-AUTOMATION-LAYER.md)

## Problem Statement

**What problem are we solving?**

The autom8_asana SDK currently operates as an Asana API wrapper. Pipeline automation logic (e.g., creating follow-up Processes when a Sales Process converts) must be orchestrated externally by consumers. This forces consumers to:

1. Implement their own webhook handlers
2. Write boilerplate for entity creation and field seeding
3. Manually coordinate multi-step workflows
4. Handle edge cases (duplicate prevention, field inheritance, section matching)

**For whom?**

- **SDK consumers**: Developers building pipeline automation on top of the SDK
- **Pipeline operators**: Business users who expect consistent, automated state transitions
- **The SDK itself**: Evolution from "API wrapper" to "Asana Automation Platform"

**What's the impact of not solving it?**

- Consumers duplicate automation logic across implementations
- Inconsistent field seeding leads to data quality issues
- Pipeline conversions require manual intervention or brittle external scripts
- SDK remains a low-level tool rather than a business automation platform

## Goals & Success Metrics

| Goal | Metric | Target |
|------|--------|--------|
| Zero-code pipeline conversion | Common patterns require no consumer code | 100% for template-based conversions |
| Automation performance | Time to evaluate rules after commit | < 100ms single rule |
| Field seeding accuracy | Fields correctly inherited/cascaded | 100% |
| Developer experience | Lines of consumer code for pipeline automation | 80% reduction vs. manual orchestration |
| Reliability | Automation failures not breaking primary commits | 100% isolation |

## Scope

### In Scope

- Post-commit hook infrastructure in SaveSession/EventSystem
- AutomationEngine with rule evaluation after commit
- PipelineConversionRule for section-change-triggered Process creation
- Template discovery and fuzzy section matching
- Field seeding from Business/Unit cascade and Process carry-through
- AutomationConfig in AsanaConfig
- AutomationResult in SaveResult
- Loop detection via max depth and visited set tracking
- Rule registry for custom rule registration

### Out of Scope

- **Webhook server implementation**: External to SDK; SDK receives events, doesn't host endpoints
- **Cross-workspace automation**: Rules operate within single workspace
- **Real-time dashboard/UI**: Observability is via AutomationResult and hooks, not built-in UI
- **Undo/rollback mechanisms**: Automation actions are forward-only; consumers handle reversals
- **Conditional branching logic**: V1 supports linear trigger-to-action; complex workflows deferred
- **External integrations**: No Slack, email, or third-party triggers in V1

## Requirements

### Functional Requirements

#### MUST HAVE (P1) - Core Infrastructure

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-001 | AutomationEngine evaluates registered rules after SaveSession commit completes | Must | Given rules are registered, when `commit_async()` succeeds, then AutomationEngine.evaluate() is called with SaveResult |
| FR-002 | Post-commit hooks receive full SaveResult including succeeded entities, action results, cascade results, and healing report | Must | Given a post-commit hook is registered, when commit completes, then hook receives SaveResult with all fields populated |
| FR-003 | PipelineConversionRule triggers when Process section changes to CONVERTED | Must | Given Sales Process moves to CONVERTED section, when commit completes, then PipelineConversionRule fires |
| FR-004 | Template discovery finds template sections in target project using fuzzy matching | Must | Given Onboarding project has "Template" section, when rule executes, then new Process is discovered and cloned from template |
| FR-005 | Field seeding populates new Process from Business/Unit cascade and source Process carry-through | Must | Given Sales converts, when Onboarding Process is created, then Business Name, Company ID, Vertical, Office Phone, Contact Phone are populated |
| FR-006 | AutomationConfig added to AsanaConfig for automation settings | Must | Given AsanaConfig instance, when automation attribute accessed, then AutomationConfig with enabled, max_cascade_depth, rules_source fields is available |
| FR-007 | AutomationResult included in SaveResult after automation execution | Must | Given automation rules execute, when commit returns, then SaveResult.automation_results contains AutomationResult for each rule evaluated |

#### SHOULD HAVE (P2) - Extensibility

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-008 | Rule registry allows registering custom automation rules | Should | Given custom rule class, when registered via `engine.register(rule)`, then rule is evaluated on matching commits |
| FR-009 | TriggerCondition supports entity type, event type, and filter predicates | Should | Given TriggerCondition with `entity_type="Process", event="section_changed", filters={"section": "converted"}`, when matching entity committed, then rule triggers |
| FR-010 | Action types include create_process, add_to_project, set_field | Should | Given rule with action `type="create_process"`, when triggered, then new Process entity is created with specified parameters |
| FR-011 | Max cascade depth configuration prevents circular trigger chains | Should | Given max_cascade_depth=5, when automation triggers nested automation, then evaluation stops at depth 5 |
| FR-012 | Visited set tracking prevents same entity triggering same rule twice in chain | Should | Given Process A triggers rule R, when R creates Process B which would re-trigger R on A, then second trigger is skipped |

#### COULD HAVE (P3) - Advanced Features

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-013 | File-based rule configuration loads rules from YAML/JSON files | Could | Given rules.yaml file path in AutomationConfig, when engine initializes, then rules are loaded from file |
| FR-014 | Rules can be enabled/disabled at runtime without restart | Could | Given rule R is registered, when `engine.disable("R")` called, then R is not evaluated until re-enabled |
| FR-015 | Observability hooks emit automation metrics (rule evaluations, execution time, failures) | Could | Given observability hook configured, when automation executes, then metrics are emitted with rule_id, execution_time_ms, success |

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-001 | Automation evaluation latency | < 100ms per rule | Time from commit complete to rule evaluation finish, measured via AutomationResult.execution_time_ms |
| NFR-002 | Rate limit compliance | 1500 req/min Asana limit respected | Automation operations batch where possible, observe RateLimitConfig |
| NFR-003 | Failure isolation | Automation failures do not fail primary commit | SaveResult.success reflects CRUD success; automation_results may contain failures independently |
| NFR-004 | Audit trail completeness | All automation actions recorded | AutomationResult captures rule_id, triggered_by_gid, actions_executed, entities_created, entities_updated |

## User Stories / Use Cases

### UC-001: Sales to Onboarding Pipeline Conversion

**Actor**: Pipeline automation system (webhook-triggered)

**Precondition**: Sales Process exists with associated Business, Unit, and Contact. Onboarding project exists with Template section containing Process template.

**Flow**:
1. External webhook notifies system that Sales Process moved to CONVERTED section
2. System loads Sales Process with parent hierarchy (Business, Unit, Contact)
3. System calls `session.save(sales_process)` to persist section change
4. SaveSession commits and fires post-commit hooks
5. AutomationEngine evaluates PipelineConversionRule
6. Rule matches: entity_type=Process, event=section_changed, section=CONVERTED
7. Rule action executes:
   - Discovers template in Onboarding project
   - Creates new Onboarding Process from template
   - Seeds fields: Business Name, Company ID, Vertical from Business/Unit cascade
   - Seeds fields: Contact Phone, Priority carry-through from Sales Process
   - Adds new Process to appropriate section in Onboarding project
8. SaveResult returned with automation_results showing created entity

**Postcondition**: Onboarding Process exists with correct field values, associated to same Business/Unit hierarchy.

### UC-002: Custom Rule Registration

**Actor**: SDK consumer developer

**Flow**:
1. Developer defines custom rule class extending AutomationRule
2. Developer registers rule with engine: `client.automation.register(CustomRule())`
3. Developer configures trigger: section change to "scheduled" for Offer entities
4. Developer configures action: set "Scheduled Date" field to current date
5. When Offer moves to "scheduled", custom rule fires and sets date

### UC-003: Loop Prevention

**Actor**: System (internal safeguard)

**Flow**:
1. Rule A triggers on Process P1 creation, creates Process P2
2. Rule B triggers on Process P2 creation, would create Process P1
3. Visited set contains P1's GID
4. Rule B evaluation skips P1 creation (already visited)
5. AutomationResult records skipped action with reason "circular_reference_prevented"

## Assumptions

| Assumption | Basis |
|------------|-------|
| Webhook delivery is external | SDK receives events via method calls, not HTTP endpoints |
| Template sections contain "template" in name (case-insensitive) | Current project naming convention |
| Process types map to project names predictably | ProcessType enum aligns with project naming |
| SaveSession is synchronous per-transaction | No cross-session automation in V1 |
| Asana custom field GIDs may change | Use field names for resolution, not hardcoded GIDs |

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| EventSystem post-commit hook (FR-002) | SDK infrastructure | Discovery complete, implementation needed |
| ProcessSection.from_name() fuzzy matching | SDK infrastructure | Exists (process.py) |
| CascadingFieldDef/InheritedFieldDef | SDK infrastructure | Exists (fields.py) |
| AsanaConfig extension pattern | SDK infrastructure | Exists (config.py) |
| SaveResult extension pattern | SDK infrastructure | Exists (models.py - cascade_results, healing_report precedent) |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should automation execution be async-only or support sync mode? | Architect | TDD phase | Pending |
| How to handle partial automation failures (some actions succeed, some fail)? | Architect | TDD phase | Pending |
| Should field seeding use BusinessSeeder or new FieldSeeder abstraction? | Architect | TDD phase | Pending |
| What's the template section naming convention for different process types? | Product | Before implementation | Pending |

## Constraints

### Asana API Constraints
- Batch API limited to 10 requests per call
- 1500 requests/minute rate limit
- Section operations are not batchable

### SDK Architecture Constraints
- SaveSession is per-transaction (no cross-session automation)
- CascadeExecutor updates in-memory only (requires separate commit)
- No built-in rollback mechanism

### Business Logic Constraints
- ProcessType enum must match project name patterns
- Pipeline transitions require explicit section movement

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Circular trigger loops | High | Medium | Max recursion depth (FR-011), visited set tracking (FR-012) |
| Rate limiting during cascades | Medium | Medium | Batch operations, respect RateLimitConfig (NFR-002) |
| Partial failures in multi-step automation | Medium | Medium | AutomationResult records per-action success/failure, isolation (NFR-003) |
| Section name mismatch | Low | Low | ProcessSection.from_name() with OTHER fallback |
| Custom field GID changes | Low | Low | Field name resolution, not hardcoded GIDs |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | Requirements Analyst | Initial draft from DISCOVERY-AUTOMATION-LAYER findings |
