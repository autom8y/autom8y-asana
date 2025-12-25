# Prompt -1: Initiative Scoping - Membership-Based Model Detection System

> **Purpose**: Validate readiness for the 4-agent workflow. Answer: "Do we know enough to write Prompt 0?"

---

## Initiative Summary

**One-liner**: Replace broken name-based entity type detection with deterministic project-membership detection to enable reliable model instantiation across the business entity hierarchy.

**Sponsor**: SDK maintainers / autom8 platform consumers

**Triggered by**: Complete detection failure in production - current name-based heuristics achieve ~0% accuracy because Asana task names are decorated with business context, emoji, and custom prefixes rather than matching expected patterns like "contacts" or "offers".

---

## Pre-Flight Checklist

### 1. Problem Validation

| Question | Answer | Confidence |
|----------|--------|------------|
| Is there a real problem? | **Yes** - Current detection returns UNKNOWN for all entities. API inspection shows `detect_by_name("offers")` expects literal match but actual holder names are `"Duong Chiropractic Inc - Chiropractic Offers [emoji]"` | **High** |
| Who experiences it? | SDK consumers attempting to traverse business hierarchies, construct typed models, or perform type-specific operations | **High** |
| What's the cost of not solving? | Business model layer is non-functional. Cannot reliably instantiate Contact, Offer, Unit, etc. from raw task data. Blocks all business-layer automation. | **High** |
| Is this the right time? | **Yes** - SaveSession and persistence layer are stable. Business models exist but are untestable without detection. This is the critical blocking piece. | **High** |

**Problem Statement Draft**:
> The current entity type detection system uses name-based heuristics that fundamentally fail because Asana holder names are decorated with business context (e.g., `"Duong Chiropractic Inc - Chiropractic Offers [emoji]"` vs expected `"offers"`). The actual Asana data model uses **project membership** as the canonical type indicator - each entity type lives in a dedicated project. Replacing name-based detection with project-membership detection will provide O(1), zero-API-call, 100% accurate type resolution.

### 2. Scope Boundaries

| Dimension | In Scope | Out of Scope | Decision Rationale |
|-----------|----------|--------------|-------------------|
| **Detection Mechanism** | Project membership lookup, fallback chain (name/parent/structure), confidence scoring | Machine learning approaches, fuzzy matching, external classification services | Project membership is deterministic and proven in legacy system |
| **Entity Types** | All BusinessEntity subclasses: Business, Contact, Unit, Offer, Location, Process, Hours, DNA, Reconciliation, AssetEdit, Videography + all Holder types | Custom entity types not in current hierarchy, third-party model extensions | Focus on existing hierarchy first; extensibility via registry pattern |
| **Configuration** | Hybrid ClassVar + environment override for multi-workspace support | GUI-based configuration, database-backed config, runtime project discovery | Maintains SDK simplicity while supporting multi-workspace via env vars |
| **Self-Healing** | Deferred healing via SaveSession with opt-in `auto_heal` flag | Immediate healing on detection, background healing jobs, healing webhooks | Aligns with Unit of Work pattern; avoids surprise API calls |
| **Caching** | Leverage existing cache protocol for project metadata | New cache backend implementations, cache warming strategies | Cache infrastructure already exists; detection reuses it |
| **Testing** | Unit tests for registry, integration tests for detection chain, accuracy validation against live API | Performance benchmarking harness, load testing, chaos testing | Focus on correctness first; performance is O(1) by design |

### 3. Complexity Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| **Scope** | **Module** | Primarily detection.py + model ClassVars; touches multiple files but contained to business/ |
| **Technical Risk** | **Medium** | Core algorithm is proven (legacy system works); risk is in edge cases (LocationHolder, multi-project) |
| **Integration Points** | **Medium** | Touches model instantiation, SaveSession healing, potentially factory methods |
| **Team Familiarity** | **High** | Legacy autom8 codebase has working implementation to reference |
| **Unknowns** | **Medium** | Need to confirm all project GIDs, validate multi-project membership handling |

**Recommended Complexity Level**: Module

**Workflow Recommendation**: Full 4-agent workflow

**Rationale**: This is a core SDK capability that affects all business model consumers. The detection system is foundational - getting it wrong cascades to all downstream functionality. The 4-agent workflow ensures proper requirements capture, architectural decisions are documented, and edge cases are validated.

### 4. Dependencies & Blockers

| Dependency | Status | Owner | Blocking? |
|------------|--------|-------|-----------|
| SaveSession exists and is stable | **Done** | SDK Team | No |
| BusinessEntity base class with ClassVars | **Done** | SDK Team | No |
| PRIMARY_PROJECT_GID ClassVar pattern | **Done** (stubbed) | SDK Team | No |
| Project GID mapping for all entity types | **Not Started** | SDK Team | **Yes** - need complete mapping |
| Legacy system reference (autom8) | **Available** | - | No |
| Multi-workspace project GID strategy | **Not Started** | SDK Team | No (can defer to Phase 2) |

**Blockers**:
1. **Need complete project GID mapping** - Must collect all project GIDs for every entity type from production Asana workspace. Architect's analysis identified most but flagged gaps for Contact, ContactHolder, Process, ProcessHolder.

### 5. Success Definition (Draft)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Detection accuracy (core entities) | ~0% | 100% | Run detection against 100 known entities, verify correct EntityType |
| Detection accuracy (edge cases) | ~0% | >95% | LocationHolder (no project), multi-project entities |
| API calls per detection | 0-1 (structure fallback) | 0 (Tier 1) | Profile detection code path |
| Detection latency | ~50ms (with API call) | <1ms | Benchmark O(1) lookup |
| Self-healing completion rate | N/A | >90% | Track SaveSession healing success for incorrectly-placed entities |

### 6. Rough Effort Estimate

| Phase | Effort | Confidence |
|-------|--------|------------|
| Discovery / Requirements | 1 session (2-4 hours) | **High** |
| Architecture / Design | 1 session (2-4 hours) | **High** |
| Implementation | 3 sessions (6-12 hours) | **Medium** |
| Validation / QA | 1 session (2-4 hours) | **Medium** |
| **Total** | 6-7 sessions (16-28 hours) | **Medium** |

### 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Missing project GIDs** | Medium | High | Discovery phase collects all GIDs; fallback chain handles unknowns |
| **LocationHolder has no project** | Known | Medium | Design parent-based inference as Tier 3 fallback |
| **Multi-project membership ambiguity** | Medium | Medium | First membership is canonical; document in ADR |
| **Dynamic membership changes** | Low | Medium | Self-healing corrects on save; modified_at cache invalidation |
| **Performance regression** | Low | Medium | O(1) by design; benchmark before/after |
| **Breaking existing consumers** | Medium | High | Maintain backward compatibility; deprecate name-based, don't remove |

---

## Open Questions to Resolve Before Prompt 0

### Must Answer (Blocking)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 1 | What are the project GIDs for Contact, ContactHolder, Process, ProcessHolder? | Query Asana API, check legacy config | Query API in Discovery phase | ? |
| 2 | How should multi-project membership be handled? | First membership wins, explicit primary flag, type-specific rules | **First membership** - simple, matches legacy behavior | ? |
| 3 | What is the self-healing trigger strategy? | Immediate on detection, deferred to SaveSession, explicit method | **Deferred to SaveSession** with `auto_heal=True` opt-in | ? |

### Should Answer (Informing)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 4 | Should registry be populated at class definition or client initialization? | ClassVar at import, lazy at first detection, client.configure() | **Hybrid**: ClassVar defaults + client config override | ? |
| 5 | What confidence threshold triggers self-healing? | 100% only, >80%, any mismatch | **100%** - only heal when certain of correct type | ? |
| 6 | Should detection expose confidence scores to consumers? | Yes with enum, yes with float, no (internal only) | **Yes with enum** (HIGH/MEDIUM/LOW) for debugging | ? |

### Nice to Answer (Context)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 7 | Should we support detection-only mode (no healing)? | Yes, No | **Yes** - useful for analysis/reporting use cases | ? |
| 8 | Should project GID mappings be logged at startup? | Debug level, Info level, Silent | **Debug level** - helps troubleshooting without noise | ? |

---

## Spike Recommendations (If Applicable)

### Spike 1: Project GID Collection (30 minutes)

**Goal**: Collect complete project GID mapping for all entity types.

**Tasks**:
1. Query Asana API for all projects in workspace
2. Match project names to entity types
3. Verify against legacy autom8 configuration
4. Document any projects without clear entity type mapping

**Output**: Complete `PROJECT_TYPE_MAP` dictionary for SDK configuration.

### Spike 2: Multi-Project Entity Analysis (30 minutes)

**Goal**: Understand which entities appear in multiple projects and how legacy handles this.

**Tasks**:
1. Identify entity types that can have multiple memberships
2. Review legacy autom8 `__post_init__` membership enforcement
3. Document "boy scout" pattern for membership correction

**Output**: ADR decision on multi-project membership handling.

---

## Go/No-Go Decision

### Criteria for "Go"

- [x] Problem is validated and worth solving
- [x] Scope is bounded and achievable
- [ ] No blocking dependencies (need project GID mapping)
- [x] Complexity level appropriate for chosen workflow
- [x] Success metrics are measurable
- [x] Rough effort estimate acceptable
- [x] High-risk items have mitigation plans

### Recommendation

**CONDITIONAL GO** - Proceed with Discovery phase to resolve blocking dependency

**Rationale**:
- Problem is critical and clearly understood
- Solution pattern is proven (legacy system works)
- Architecture has been analyzed; patterns identified
- Only blocking dependency is data collection (project GIDs), not architectural uncertainty

**Conditions (for full GO)**:
- Complete project GID mapping obtained in Discovery phase
- LocationHolder no-project case has confirmed fallback strategy
- Multi-project membership decision documented

---

## Next Steps

1. **Begin Discovery Phase** (1 session)
   - Collect all project GIDs from Asana API
   - Verify against legacy autom8 configuration
   - Document LocationHolder parent-based detection requirements

2. **Create PRD** (after Discovery)
   - Define requirements for registry, detection, fallback, healing
   - Include acceptance criteria for each tier

3. **Architecture Session** (after PRD)
   - TDD for detection system
   - ADR for registry pattern choice
   - ADR for self-healing integration

---

## Appendix: Quick Reference

### Detection Tier Hierarchy (from Architect Analysis)

```
Tier 1: Project Membership (100% accuracy, O(1), 0 API)
   |
Tier 2: Name Convention (~60% accuracy, O(1), 0 API)
   |
Tier 3: Parent Inference (~80% accuracy, O(1), 0 API)
   |
Tier 4: Structure Inspection (~90%, O(n), 1+ API calls)
   |
Tier 5: Unknown with self-healing flag
```

### Known Project Mappings (from Architect Analysis)

| Entity Type | Project Name | Project GID |
|-------------|--------------|-------------|
| Business | Businesses | `1200653012566782` |
| ContactHolder | Contact Holder | `1201500116978260` |
| Contact | Contacts | `1200775689604552` |
| UnitHolder | Units | `1204433992667196` |
| Unit | Business Units | `1201081073731555` |
| LocationHolder | *(No project)* | N/A |
| Location | Locations | `1200836133305610` |
| OfferHolder | Offer Holders | `1210679066066870` |
| Offer | Business Offers | `1143843662099250` |
| ReconciliationHolder | Reconciliations | `1203404998225231` |
| AssetEditHolder | Asset Edit Holder | `1203992664400125` |
| VideographyHolder | Videography Services | `1207984018149338` |

### Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Detection System Analysis | `/docs/analysis/DETECTION-SYSTEM-ANALYSIS.md` | Root cause analysis, proposed solution |
| Current Detection Code | `src/autom8_asana/models/business/detection.py` | Code to replace |
| BusinessEntity Base | `src/autom8_asana/models/business/base.py` | PRIMARY_PROJECT_GID ClassVar |
| SaveSession | `src/autom8_asana/persistence/session.py` | Self-healing integration point |
| Legacy Implementation | (external) autom8 repo | Reference implementation |

---

*This Prompt -1 **conditionally validates** that the initiative is ready for the full 4-agent workflow. Proceed to Discovery to resolve the project GID mapping dependency, then begin Prompt 0.*
