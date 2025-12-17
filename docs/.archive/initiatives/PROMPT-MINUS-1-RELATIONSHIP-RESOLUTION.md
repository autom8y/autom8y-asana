# Prompt -1: Initiative Scoping - Cross-Holder Relationship Resolution

> **Purpose**: Validate readiness for the 4-agent workflow. Answer: "Do we know enough to write Prompt 0?"

---

## Initiative Summary

**One-liner**: Enable the SDK to resolve cross-holder relationships (e.g., `asset_edit -> unit -> offer`) without requiring users to manually orchestrate multi-step lookups.

**Sponsor**: SDK Usability / Developer Experience

**Triggered by**: Architect analysis identifying that while hierarchical "fast-paths" (offer.unit, unit.business) already exist and work well, cross-holder resolution patterns require domain-specific logic that doesn't fit the existing navigation model.

---

## Pre-Flight Checklist

### 1. Problem Validation

| Question | Answer | Confidence |
|----------|--------|------------|
| Is there a real problem? | **Yes** - AssetEdit entities need to find their "owning" Unit and Offer, but the relationship is not direct hierarchical containment. Multiple resolution strategies exist (dependent tasks, custom field mapping, explicit offer_id). | Medium |
| Who experiences it? | SDK consumers processing AssetEdits who need to correlate them with Units/Offers for reporting, workflow automation, or cascading updates. | Medium |
| What's the cost of not solving? | Users must implement domain-specific resolution logic themselves, leading to duplicated code, inconsistent behavior, and potential bugs when resolution rules change. | Medium |
| Is this the right time? | **Uncertain** - Depends on how frequently this pattern is needed. Discovery should validate use case frequency. | Low |

**Problem Statement Draft**:
> The SDK's business model layer provides excellent hierarchical navigation (offer.unit, unit.business, contact.business). However, some entity relationships are not strictly hierarchical. For example, an AssetEdit (a process task) needs to resolve to its "owning" Unit and Offer, but this relationship requires domain-specific logic: checking dependent tasks, matching custom fields, or reading explicit offer_id fields. Currently, users must implement this resolution logic themselves, which duplicates domain knowledge and may produce inconsistent results.

### 2. Scope Boundaries

| Dimension | In Scope | Out of Scope | Decision Rationale |
|-----------|----------|--------------|-------------------|
| **Entity Types** | AssetEdit as initial use case; generalizable pattern | All process types upfront | Start small, prove pattern works |
| **Resolution Types** | Cross-holder resolution (not hierarchical) | Improving existing fast-paths (already work) | Fast-paths already solved |
| **API Surface** | Resolution capability with strategy transparency | Batch resolution optimization (initially) | Get correctness before performance |
| **AssetEdit Typing** | May need to type AssetEdit entity | Typing all untyped process types | Only what's needed for this initiative |

### 3. Complexity Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| **Scope** | Module | New resolution framework, possibly new entity type |
| **Technical Risk** | Medium-High | Domain logic encapsulation is tricky; multiple resolution strategies with priority ordering |
| **Integration Points** | Medium | SaveSession awareness, client access for fetching dependents/fields |
| **Team Familiarity** | High | Codebase well-documented; patterns exist from hydration work |
| **Unknowns** | High | Resolution strategy correctness, ambiguity handling, performance characteristics |

**Recommended Complexity Level**: Module

**Workflow Recommendation**: Full 4-agent workflow

**Rationale**: This introduces a new pattern (strategy-based resolution) that doesn't exist in the codebase. Architectural decisions needed for strategy definition, priority ordering, and ambiguity handling.

### 4. Dependencies & Blockers

| Dependency | Status | Owner | Blocking? |
|------------|--------|-------|-----------|
| AssetEdit entity typing | Not started | TBD | **Possibly** - Need typed entity to add resolution methods |
| TasksClient methods for fetching dependents | Unknown | - | **Discovery needed** - May need `dependents_async()` or similar |
| Custom field accessor for field mapping strategy | Done | - | No - CustomFieldAccessor exists |
| Existing Business/Unit/Offer types | Done | - | No - Navigation targets exist |

**Blockers**:
- **Discovery needed**: What TasksClient capabilities exist for fetching task dependents? This affects feasibility of DEPENDENT_TASKS strategy.
- **Discovery needed**: Is AssetEdit typing a prerequisite, or can resolution work on plain Tasks initially?

### 5. Success Definition (Draft)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Can resolve AssetEdit to Unit | No | Yes | `resolver.resolve_unit(asset_edit)` returns Unit |
| Can resolve AssetEdit to Offer | No | Yes | `resolver.resolve_offer(asset_edit)` returns Offer |
| Resolution strategy is transparent | N/A | Yes | Result includes which strategy succeeded |
| Ambiguity is handled gracefully | N/A | Yes | Clear behavior when multiple matches found |

### 6. Rough Effort Estimate

| Phase | Effort | Confidence |
|-------|--------|------------|
| Discovery / Requirements | 1 session | Medium |
| Architecture / Design | 1 session | Medium |
| Implementation | 2-3 sessions | Low |
| Validation / QA | 1 session | Medium |
| **Total** | 5-6 sessions | Low |

**Note**: Low confidence on implementation because we don't know yet if this requires new TasksClient methods, new entity types, or significant framework code.

### 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Resolution ambiguity** - Multiple Units/Offers match | Medium | High | Define clear ambiguity handling (fail, first-match, configurable) |
| **Expensive API calls** - Dependents fetch may be costly | Medium | Medium | Consider lazy/on-demand resolution; architect to assess |
| **Stale resolution cache** - Relationships change over time | Low | Medium | Different cache semantics than hierarchical (TTL? No cache?) |
| **Domain logic brittleness** - Resolution rules may change | Medium | Medium | Make strategies explicit and configurable |
| **Circular resolution** - A resolves to B which resolves to A | Low | High | Architect to prevent in design |

---

## Open Questions for Discovery/Architecture Phases

### Must Answer (Blocking)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 1 | **Is AssetEdit typing required first?** | (a) Type AssetEdit before resolution, (b) Build resolution on plain Task, (c) Parallel work | Discovery to assess | ? |
| 2 | **What TasksClient capabilities exist for dependents?** | May need new method similar to subtasks_async | Discovery to audit | ? |
| 3 | **How should ambiguity be handled?** | (a) Error, (b) First match, (c) Return all matches, (d) Configurable | Architect to decide | ? |

### Should Answer (Informing)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 4 | **What resolution strategies are actually needed?** | DEPENDENT_TASKS, CUSTOM_FIELD_MAPPING, EXPLICIT_OFFER_ID - validate priority | Discovery to confirm with use cases | ? |
| 5 | **Should resolution be lazy or eager?** | (a) Resolve on-demand, (b) Resolve when tracking, (c) Configurable | Architect to assess trade-offs | ? |
| 6 | **How common is this use case?** | Need to validate frequency before investing | Discovery to assess | ? |

### Nice to Answer (Context)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 7 | **What other process types might need this pattern?** | Future-proofing vs. YAGNI | Architect can consider extensibility | ? |
| 8 | **Should batch resolution be part of initial scope?** | Performance optimization vs. complexity | Defer to Phase 2 if needed | ? |

---

## Spike Recommendations

Before committing to Prompt 0, consider these targeted investigations:

### Spike 1: Resolution Use Case Validation (1-2 hours)

**Goal**: Validate how frequently cross-holder resolution is actually needed.

**Tasks**:
1. Review existing integration code or scripts that work with AssetEdits
2. Document what resolution logic currently exists (if any)
3. Identify other process types that might need similar resolution

**Output**: Use case frequency assessment, priority validation

### Spike 2: TasksClient Capabilities Audit (1 hour)

**Goal**: Determine if existing TasksClient supports dependent task fetching.

**Tasks**:
1. Review TasksClient methods in `src/autom8_asana/clients/tasks.py`
2. Check Asana API documentation for dependents endpoint
3. Assess effort to add `dependents_async()` if needed

**Output**: Capability assessment, dependency identification

---

## Go/No-Go Decision

### Criteria for "Go"

- [x] Problem is validated and worth solving (tentatively - needs Discovery confirmation)
- [x] Scope is bounded and achievable
- [ ] No blocking dependencies (Discovery needed for TasksClient capabilities)
- [x] Complexity level appropriate for chosen workflow
- [x] Success metrics are measurable
- [ ] Rough effort estimate acceptable (Low confidence, may increase)
- [x] High-risk items have mitigation plans

### Recommendation

**CONDITIONAL GO** - Proceed to Prompt 0 with Discovery focus

**Rationale**:
- Problem appears valid based on architect analysis
- Pattern is generalizable and valuable if use case frequency is confirmed
- Existing codebase provides good foundation (hydration initiative, entity patterns)
- However, several unknowns need Discovery resolution before full commitment

**Conditions for full GO**:
1. Discovery confirms use case frequency justifies investment
2. Discovery identifies TasksClient capabilities or acceptable workarounds
3. Discovery clarifies AssetEdit typing dependency

---

## Next Steps

1. **Generate Prompt 0** with Discovery-focused first session
   - Emphasize validation of use case frequency
   - Include TasksClient audit as Discovery task
   - Leave architectural decisions open

2. **Session 1 (Discovery)** should:
   - Validate how frequently cross-holder resolution is needed
   - Audit TasksClient capabilities for dependents fetching
   - Assess AssetEdit typing as prerequisite vs. parallel work
   - Surface any additional blockers
   - Recommend Go/No-Go based on findings

3. **If Discovery validates**:
   - Session 2 defines requirements with confirmed scope
   - Session 3 designs resolution framework
   - Sessions 4+ implement

4. **If Discovery does not validate**:
   - Document findings
   - Defer initiative or descope significantly

---

## Appendix: Architect's Input Summary

The following analysis from the architect informed this Prompt -1:

### Problem Identified

- Fast-paths for hierarchical navigation already work (offer.unit, unit.business)
- Cross-holder resolution is the real gap
- Specific pattern: `asset_edit -> unit -> offer`
- AssetEdit currently untyped (plain Task under AssetEditHolder)

### Resolution Strategies Suggested

| Strategy | Description | Priority |
|----------|-------------|----------|
| DEPENDENT_TASKS | Process tasks have dependents pointing to Unit | 1 (most reliable?) |
| CUSTOM_FIELD_MAPPING | Vertical field matches | 2 |
| EXPLICIT_OFFER_ID | Explicit offer_id field on task | 3 |
| AUTO | Try strategies in priority order | Default |

### Considerations Raised

- Lazy vs. eager resolution trade-offs
- Batch resolution for processing many entities
- Caching with different semantics than hierarchical cache (TTL, staleness)
- Ambiguity handling when multiple Units match

### ADRs Suggested

- Relationship Resolution Strategy Pattern
- AssetEdit Entity Typing Decision

### Phasing Suggested

- Phase 1: Type AssetEdit entity (small, follows existing patterns)
- Phase 2: Resolution framework (medium, new pattern)
- Phase 3: Batch optimization (optional, performance)

**Note**: These are architect recommendations, not requirements. Discovery and Architecture phases should validate or refine this phasing.

---

## Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Hydration Initiative Prompt -1 | `docs/initiatives/PROMPT-MINUS-1-HYDRATION.md` | Prior art for similar initiative |
| Hydration Initiative Prompt 0 | `docs/initiatives/PROMPT-0-HYDRATION.md` | Prior art for session structure |
| Relationship Patterns | `.claude/skills/autom8-asana-business-relationships/patterns-relationships.md` | Existing navigation patterns |
| Holder Pattern | `.claude/skills/autom8-asana-business-relationships/holder-pattern.md` | How holders work |

---

*This Prompt -1 provided a **CONDITIONAL GO** recommendation. Proceed to Prompt 0 with Discovery as the validation gate. Discovery findings will inform whether to continue or defer.*
