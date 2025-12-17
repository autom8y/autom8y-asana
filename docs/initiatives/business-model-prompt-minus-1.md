# Prompt -1: Initiative Scoping — Business Model Implementation

> **Purpose**: Validate readiness for the 4-agent workflow. Answer: "Do we know enough to write Prompt 0?"

---

## Initiative Summary

**One-liner**: Implement the domain-aware business model hierarchy (Business, Contact, Unit, Location, Hours) with typed custom fields, cascading field propagation, and SaveSession integration in the autom8_asana SDK.

**Sponsor**: Tom Tenuta

**Triggered by**: Need to migrate business model from legacy autom8 monolith to the new autom8_asana SDK, enabling rich domain models for Asana-based business operations.

---

## Pre-Flight Checklist

### 1. Problem Validation

| Question | Answer | Confidence |
|----------|--------|------------|
| Is there a real problem? | Yes - SDK lacks domain models; all business logic requires manual field access | High |
| Who experiences it? | Developers building on autom8_asana; operations teams using Asana | High |
| What's the cost of not solving? | Duplicated boilerplate, inconsistent field access, no type safety, manual cascade propagation | High |
| Is this the right time? | Yes - SDK foundation is complete (SaveSession, CustomFieldAccessor, async client) | High |

**Problem Statement Draft**:
> The autom8_asana SDK provides generic Asana task operations but lacks domain-aware models for the business hierarchy. Developers must manually navigate relationships, access custom fields without type safety, and propagate field changes across hierarchies. This results in error-prone code, inconsistent data, and significant boilerplate.

### 2. Scope Boundaries

| Dimension | In Scope | Out of Scope | Decision Rationale |
|-----------|----------|--------------|-------------------|
| **Models** | Business, Contact, Unit, Offer, Process, Location, Hours | 24+ Process subclasses (AdCreative, Budget, etc.) | Core hierarchy first; subclasses in Phase 2 |
| **Holders** | 7 holder types (Contact, Unit, Location, DNA, Reconciliations, AssetEdit, Videography) | Manager classes (AdManager, ReconcileBudget) | Holders enable navigation; managers are consumers |
| **Fields** | Typed accessors for 83+ custom fields | SQL fallback, webhook integration | SDK stays pure; integration layer separate |
| **Cascading** | Multi-level cascade with opt-in override | CascadeReconciler (drift repair) | Core cascade first; reconciler is optimization |
| **SaveSession** | recursive tracking, prefetch_holders, cascade_field() | Automatic cascade on field change | Explicit over magic |

### 3. Complexity Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| **Scope** | Service | Multiple models, relationships, infrastructure |
| **Technical Risk** | Medium | Building on proven SDK patterns, but new domain layer |
| **Integration Points** | Medium | SaveSession, CustomFieldAccessor, batch API |
| **Team Familiarity** | High | SDK patterns well-documented, skills created |
| **Unknowns** | Low | Architecture decisions made (ADR-0050 through ADR-0054) |

**Recommended Complexity Level**: Service

**Workflow Recommendation**: Full 4-agent workflow (7 sessions)

**Rationale**: Multi-model implementation with infrastructure changes (SaveSession extensions) warrants full workflow. Architecture decisions are already made, reducing discovery risk but implementation is substantial.

### 4. Dependencies & Blockers

| Dependency | Status | Owner | Blocking? |
|------------|--------|-------|-----------|
| SDK foundation (Task, SaveSession, CustomFieldAccessor) | Done | Tom | No |
| Architecture decisions (ADR-0050 through ADR-0054) | Done | Architect Agent | No |
| Skills documentation (4 business model skills) | Done | Context-Engineer | No |
| Custom field GID mappings | Partial (in dataframes) | Tom | No |
| Existing tests baseline | Unknown | - | No |

**Blockers**: None identified

### 5. Success Definition (Draft)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Type-safe field access | 0 fields | 83+ fields | Count of typed properties |
| Model coverage | 0 models | 7 models + 7 holders | Count of Task subclasses |
| Cascade propagation | Manual | Automated via cascade_field() | Feature exists |
| Test coverage | 0% (new code) | >80% | pytest-cov on business model code |
| Type safety | N/A | mypy passes | Zero type errors |
| Navigation depth | N/A | Full bidirectional | offer.unit.business works |

### 6. Rough Effort Estimate

| Phase | Effort | Confidence |
|-------|--------|------------|
| Discovery / Requirements | 1 session | High |
| Architecture / Design | 1 session (validation) | High (ADRs exist) |
| Implementation | 3 sessions | Medium |
| Validation / QA | 1 session | Medium |
| **Total** | 7 sessions | Medium-High |

**Note**: Architecture decisions are pre-made, reducing design risk. Implementation is the primary effort.

### 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SaveSession modifications break existing code | Low | High | Extend via new methods, don't modify existing |
| Custom field GIDs vary between environments | Medium | Medium | Resolve by name at runtime, not hardcoded GIDs |
| Cascade batch API hits rate limits | Medium | Medium | CascadeExecutor with chunking and retry logic |
| Circular imports in model hierarchy | Medium | Low | TYPE_CHECKING imports, forward references |
| Skills documentation doesn't match implementation needs | Low | Medium | Update skills during implementation (context-engineer) |

---

## Open Questions to Resolve Before Prompt 0

### Must Answer (Blocking)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 1 | Should SaveSession be modified or wrapped? | Modify / Wrap | Modify (add methods) | Resolved: Modify with new methods |
| 2 | Are all 83+ field definitions documented? | Yes / Partial / No | Partial (in dataframes + skills) | Resolved: Discovery will complete mapping |
| 3 | Holder stub models (DNA, Reconciliations, etc.) - full or stub? | Full / Stub | Stub (core holders first) | Resolved: Stub |

### Should Answer (Informing)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 4 | Field GID resolution timing | Definition time / Runtime | Runtime (by name) | Resolved: Runtime |
| 5 | Test isolation approach | Unit / Integration / Both | Both (unit for models, integration for SaveSession) | Resolved: Both |
| 6 | Package structure | Flat / Nested | Nested (models/business/, models/fields/) | Resolved: Nested |

### Nice to Answer (Context)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 7 | Process subclass timeline | Phase 2 / Later | Phase 2 (separate initiative) | Deferred |
| 8 | CascadeReconciler priority | Phase 1 / Phase 2 | Phase 2 (optimization) | Deferred |

---

## Spike Recommendations (If Applicable)

No spikes needed - architecture decisions are complete and SDK patterns are well-understood.

**Completed Pre-Work**:
- Architecture TDD: `docs/architecture/business-model-tdd.md`
- ADRs: `docs/decisions/ADR-0050` through `ADR-0054`
- Skills: 4 business model skills with implementation patterns
- Implementation guide: `docs/architecture/cascading-fields-implementation.md`

---

## Go/No-Go Decision

### Criteria for "Go"

- [x] Problem is validated and worth solving
- [x] Scope is bounded and achievable
- [x] No blocking dependencies
- [x] Complexity level appropriate for chosen workflow
- [x] Success metrics are measurable
- [x] Rough effort estimate acceptable
- [x] High-risk items have mitigation plans

### Recommendation

**GO** — Initiative is well-scoped with pre-completed architecture decisions

**Rationale**:
- SDK foundation is complete and stable
- All 5 architecture decisions are documented in ADRs
- Skills provide implementation patterns (reduces discovery)
- Scope is bounded (7 models + 7 holders, no Process subclasses)
- No blocking dependencies identified

**Conditions**: None - clear Go

---

## Next Steps

1. **Generate Prompt 0**
   - Use `docs/initiatives/business-model-prompt-0.md` (already created)

2. **Start Fresh Session**
   - Open new Claude Code session in autom8_asana project
   - Provide Prompt 0 to initialize orchestrator

3. **Execute 7 Sessions**
   - Discovery → Requirements → Architecture → Implementation (3 phases) → Validation
   - Approve each phase before execution

---

## Appendix: Quick Reference

### Business Model Hierarchy

```
Business (root)
├── CASCADING_FIELDS: Office Phone, Company ID, Business Name
├── ContactHolder → Contact[] (owner detection)
├── UnitHolder → Unit[]
│   ├── CASCADING_FIELDS: Platforms (allow_override), Vertical
│   ├── OfferHolder → Offer[]
│   └── ProcessHolder → Process[]
├── LocationHolder → Location → Hours
├── DNAHolder (stub)
├── ReconciliationsHolder (stub)
├── AssetEditHolder (stub)
└── VideographyHolder (stub)
```

### Architecture Decisions Summary

| ADR | Decision | Key Points |
|-----|----------|------------|
| ADR-0050 | Holder Lazy Loading | Fetch on `track()` with `prefetch_holders=True` |
| ADR-0051 | Custom Field Type Safety | Hybrid typed properties → CustomFieldAccessor |
| ADR-0052 | Bidirectional Reference Caching | Cache upward refs, explicit invalidation |
| ADR-0053 | Composite SaveSession | Optional `recursive=True` flag |
| ADR-0054 | Cascading Custom Fields | Multi-level, `allow_override=False` default |

### Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Original Spec | `docs/initiatives/skilify.md` | Initiative origin |
| Architecture TDD | `docs/architecture/business-model-tdd.md` | Technical design |
| Cascade Implementation | `docs/architecture/cascading-fields-implementation.md` | Cascade patterns |
| ADRs | `docs/decisions/ADR-005*.md` | Architecture decisions |
| Prompt 0 | `docs/initiatives/business-model-prompt-0.md` | Orchestrator initialization |

### Skills Reference

| Skill | Purpose | Key Files |
|-------|---------|-----------|
| `autom8-asana-business-schemas` | Model definitions | business-model.md, contact-model.md, unit-model.md |
| `autom8-asana-business-relationships` | Holder patterns | holder-pattern.md, bidirectional-navigation.md |
| `autom8-asana-business-fields` | Field accessors | field-accessor-pattern.md, cascading-inherited-fields.md |
| `autom8-asana-business-workflows` | SaveSession patterns | composite-savesession.md, cascade-operations.md |

---

*This Prompt -1 **validated** that the initiative is ready for the full 4-agent workflow. **Proceed to Prompt 0**.*
