# Stakeholder Context: Workflow Resolution Platform

**Created**: 2026-02-11
**Updated**: 2026-02-11 (post-spike + implementation interview, 28 rounds total)
**Source**: 28-round structured stakeholder interview (13 pre-spike + 7 post-spike + 8 implementation-specific)
**Stakeholder**: Tom Tenuta (sole developer)
**Purpose**: Seed the initiative with fully aligned understanding to minimize inference during design and implementation
**Spike Report**: `docs/spikes/SPIKE-workflow-resolution-platform-deep-dive.md` (675 lines, 3-phase deep dive)

---

## 1. Business Context & Strategic Intent

### 1.1 Driver
**Proactive architectural investment** — no immediate workflow #2 pressuring delivery, but the platform needs to support **8+ workflows** in the next 6 months. Building the right primitives now prevents compounding bespoke code.

### 1.2 Priority
High — close to Entity Resolution Hardening Phase B completion, and this initiative is fundamental to the platform's next phase. The resolution platform is the foundation everything else builds on.

### 1.3 Relationship to Existing Work
- Entity Resolution Hardening (INIT-ER-001) Phase A is COMPLETE, Phase B is near-done
- This initiative builds on top of the mature entity model layer (descriptors, hydration, ParentRef/HolderRef)
- Shares primitives with the existing **ActionExecutor** system (per-task pipeline automations)

### 1.4 Solo Developer Context
Optimize for velocity and personal understanding. No team onboarding concerns. The system should be clean and well-structured but doesn't need excessive documentation or abstraction for team scale.

---

## 2. Entity Hierarchy (Complete Inventory)

### 2.1 Standard Business Tree

```
Business (ROOT)
├── ContactHolder (HOLDER)
│   └── Contact (LEAF)
├── UnitHolder (HOLDER)
│   └── Unit (COMPOSITE)
│       ├── OfferHolder (HOLDER)
│       │   └── Offer (LEAF)
│       └── ProcessHolder (HOLDER)
│           └── Process (LEAF)
├── LocationHolder (HOLDER)
│   ├── Location (LEAF)
│   └── Hours (LEAF, sibling to Location)
├── DNAHolder (HOLDER)
│   └── DNA (LEAF, stub)
├── ReconciliationHolder (HOLDER)
│   └── Reconciliation (LEAF, stub)
├── AssetEditHolder (HOLDER)
│   └── AssetEdit (LEAF, extends Process)
└── VideographyHolder (HOLDER)
    └── Videography (LEAF, stub)
```

**Totals**: 9 holders, 1 root, 1 composite, 8 leaf models (3 are stubs)

### 2.2 Entity Classification

| Entity | Category | Base Class | Fully Modeled? | Warmable |
|--------|----------|-----------|----------------|----------|
| Business | ROOT | BusinessEntity + cascading/financial mixins | Yes | Yes (pri 2, TTL 3600s) |
| ContactHolder | HOLDER | HolderFactory | Yes | No |
| Contact | LEAF | BusinessEntity + UpwardTraversalMixin | Yes | Yes (pri 4, TTL 900s) |
| UnitHolder | HOLDER | HolderFactory | Yes | No |
| Unit | COMPOSITE | BusinessEntity + cascading/financial/upward mixins | Yes | Yes (pri 1, TTL 900s) |
| OfferHolder | HOLDER | UnitNestedHolderMixin + HolderFactory | Yes | No |
| Offer | LEAF | BusinessEntity + UnitNavigableEntityMixin + cascading/financial | Yes | Yes (pri 3, TTL 180s) |
| ProcessHolder | HOLDER | UnitNestedHolderMixin + HolderFactory | Yes | No |
| Process | LEAF | BusinessEntity + UnitNavigableEntityMixin + cascading/financial | Yes | No (TTL 60s) |
| LocationHolder | HOLDER | HolderFactory | Yes | No |
| Location | LEAF | BusinessEntity | Yes | No (TTL 3600s) |
| Hours | LEAF | BusinessEntity | Yes | No (TTL 3600s) |
| DNAHolder | HOLDER | HolderFactory | Yes | No |
| DNA | LEAF | BusinessEntity | Stub (no fields) | No |
| ReconciliationHolder | HOLDER | HolderFactory | Yes | No |
| Reconciliation | LEAF | BusinessEntity | Stub (no fields) | No |
| AssetEditHolder | HOLDER | HolderFactory | Yes | Yes (pri 5, TTL 300s) |
| AssetEdit | LEAF | Process (subclass) | Yes | Yes (pri 5, TTL 300s) |
| VideographyHolder | HOLDER | HolderFactory | Yes | No |
| Videography | LEAF | BusinessEntity | Stub (no fields) | No |

### 2.3 Critical Structural Insight: Unit is COMPOSITE

Unit is the only COMPOSITE entity — it has **nested holders** underneath it (OfferHolder, ProcessHolder). This creates a deeper tree than other branches:

```
Business → UnitHolder → Unit → ProcessHolder → Process (4 levels)
Business → ContactHolder → Contact (2 levels)
```

### 2.4 Asana Project Model (Key Conceptual Correction)

- A **Holder** (e.g., ContactHolder) MAY be in its own Asana project (required if it needs custom fields — project-level in Asana)
- **Entity** children (e.g., Contact) are always in their own separate entity-specific Asana project
- The project informs the entity type; the entity type informs the hierarchy position
- The hierarchy also informs entity type during seeding (e.g., Business → seed UnitHolder → seed BusinessUnit → seed ProcessHolder + OfferHolder beneath it)
- This is NOT "dual membership" — it's a consistent pattern where **project membership = type identity**

### 2.5 Process Subtypes

**Microservice ProcessType enum values**: SALES, IMPLEMENTATION, ONBOARDING, OUTREACH, REACTIVATION, RETENTION

**Legacy-only subtypes (not in microservice)**: Expansion, AccountError, Month1

**Consultation subtypes (18 classes, entirely absent from microservice)**: AdApproval, AudienceUpdate, ChangeOffer, ConfirmationCallQuality, ConfirmationCallQuantity, ConfirmationCallSpeed, ConfirmationCallTraining, Custom, DecreasePrice, FollowUp, IncreaseAvailability, LtvFeedback, NewContent, OriginalContent, PendingFeedback, PracticeOfTheWeek, StandardBooking, SubjectiveFeedback, VirtualCaSetup

**Service subtypes**: Service (base), SourceVideographer

**DNA/Play subtypes (7 classes in legacy, 1 stub in microservice)**: Play (Process+Dna multi-inherit), IsolatedPlay, PauseABusinessUnit, QuestionOnPerformance, BackendOnboardABusiness, CustomCalendarIntegration, MetaAdminAccess

**Full subclass behavior is in-scope** — the resolution system must handle subclass-specific fields and behaviors, not just ProcessType enum selection.

---

## 3. Resolution Patterns & Primitives

### 3.1 The Identified Smell

`ConversationAuditWorkflow._resolve_office_phone()` manually parses custom fields by string name:
```python
if cf_dict.get("name") == "Office Phone":
    return cf_dict.get("display_value") or cf_dict.get("text_value")
```

Meanwhile, `Business.office_phone = TextField(cascading=True)` already exists. `Business.from_gid_async(hydrate=False)` provides access to all 19 Business descriptors for the same 2 API calls.

### 3.2 Traversal Strategies (Priority Order)

1. **Dependency links first** (2 API calls: get deps → get target task)
   - Asana dependencies return compact objects: gid, resource_type, sometimes name
   - Enough for type identification, but NOT enough for custom field access — follow-up call needed
   - **Often missing** — hierarchy fallback is essential, not optional

2. **Hierarchy traversal fallback** (3-5+ API calls: up to Business → down to target holder → down to entity)
   - Always available as the reliable path
   - More expensive but guaranteed to work

### 3.3 Entity Selection Within Holders

Different holders require different selection strategies:

| Holder | Selection Strategy | Complexity |
|--------|-------------------|------------|
| LocationHolder | Type-based (Location vs Hours) | Simple |
| ContactHolder | Top-level default, custom field override (e.g., position="Owner") | Medium |
| OfferHolder | Offer Id match, top-level fallback | Medium |
| ProcessHolder | Most complex — see below | High |
| Other holders | Varies; many have single children | Low |

### 3.4 ProcessHolder Selection (Most Complex)

Three core selection modes:

**a) Get specific Process by model type** (e.g., "get the current Sales process"):
- Filter by ProcessType
- Newest `created_at` (native Asana field) wins
- Exception: if newer process is **completed** and older one is **incomplete**, the incomplete one wins (it represents active work)
- Business reasoning: Operations team may reopen older processes; system must be forgiving

**b) Get current Process (type-agnostic)**:
- Newest `created_at` + completion status, independent of ProcessType subclass
- Same completion-status logic as above

**c) Additional edge cases**:
- To be evaluated from first principles during design
- Core principle: **forgiving system that doesn't punish users for doing their jobs without deep system knowledge**

### 3.5 Custom Field Predicate System

- **Compound predicates**: AND/OR logic (not just single-field matching)
- **Multi-result selection**: Not always resolving to a single entity — may need "all contacts where position != Owner" for batch operations (e.g., email blasts to client team)
- **Override mechanism**: Custom field predicates override the default top-level selection

### 3.6 Cross-Holder Resolution Paths (Examples)

```
ContactHolder ─^→ Business.office_phone                    (1 hop, Business-level)
ContactHolder ─^→ Business ─v→ LocationHolder ─v→ Address.time_zone  (cross-branch, 3 hops)
ContactHolder ─^→ Business ─v→ ContactHolder ─v→ Contact(is_owner=True).email  (same branch, filtered)
Unit ─^→ Business ─v→ ContactHolder ─v→ Contact(is_owner=True).email  (cross-branch, filtered)
AssetEdit ─dep→ Offer.included_item_1                      (dependency shortcut)
AssetEdit ─dep→ Offer ─^→ Unit.vertical                    (dependency + upward)
AssetEdit ─^→ Business ─v→ LocationHolder ─v→ Address.city  (hierarchy fallback for city)
```

### 3.7 Field Access Breadth

Workflows will need **all of the above**:
- Business-level fields (office_phone, vertical, company_id, stripe_id — 19 descriptors)
- Deep hierarchy fields (Address.time_zone, Contact.email, Offer.included_item_1/2/3)
- Cross-branch joins (Offer fields + Contact fields + Location fields in same resolution context)

---

## 4. Process Lifecycle & State Transitions

### 4.1 This Is the Primary Workflow Pattern

The most valuable and common workflow pattern is **process lifecycle automation** — creating entities and linking dependencies when processes transition states. This is fundamentally different from read-only CSV export.

### 4.2 State Signal: Section Membership

Asana Rules fire webhook POSTs to the legacy API when tasks move between sections. "CONVERTED" is detected via section membership change, not custom field updates.

### 4.3 The Lifecycle DAG (Not Linear)

Pipeline stages are NOT a simple linear chain. The **Products** custom field (MultiEnumField) on a Process determines which downstream entities get created:

**Example**: Products = ['Meta Marketing', 'Videography']

```
Sales (CONVERTED) → creates Onboarding
                     + creates Play: Backend Onboard a Business (DNAHolder)
                     + links Play as dependency on Onboarding

Onboarding (CONVERTED) → creates Implementation
                          + creates SourceVideographer (ProcessHolder)
                          + creates AssetEdit (AssetEditHolder)
                          + links SourceVideographer as dependent on Implementation
                          + links AssetEdit as dependent on Implementation
                          + links AssetEdit as dependent on SourceVideographer
                              (must film before editing)
```

The dependency graph is a **DAG**:
```
Implementation
├── SourceVideographer (dependent)
│   └── AssetEdit (dependent on BOTH Implementation and SourceVideographer)
└── AssetEdit (dependent)
```

### 4.4 Products-to-Process Mapping

- Products field is a **MultiEnumField** on Process entities
- The mapping from product selections to required downstream processes/entities lives in **code/config** (codified, not just institutional knowledge)
- Different product combinations create different process DAGs
- Core stages are fixed but optional stages vary by product offerings

### 4.5 Trigger Flow (Corrected by Spike)

The full trigger flow is a **single pipeline**, not two separate mechanisms:

```
Asana Rule fires (section change or tag + complete)
  → Webhook POST to service handler (full task object in payload)
    → Handler identifies entity type, section, tag
      → Internally routes via SaveSession + automation subsystems
```

- **ALL webhooks currently go to legacy monolith only** — microservice receives none yet
- Webhook payload includes the **full task object** (custom fields, section, projects) — enough for routing, but NOT subtasks/deps/stories (separate API calls)
- Existing microservice code already handles enrichment beyond the webhook payload
- Migration approach: **big bang per stage** — switch one pipeline stage's Asana Rule target at a time
- Legacy decommission: Asana Rule routing auto-handles this — just change the target URL

### 4.6 Tag-Based Routing Vocabulary

The `route_*` / `request_*` / `play_*` tag vocabulary is a proven, valuable mechanism:

**User-initiated flow**: User adds tag → marks task complete → Asana Rule fires (marks task incomplete + dispatches webhook) → tag determines which automation runs

**System-initiated flow**: Internal automation adds tag → same Asana Rule evaluates → routes internally using the same primitives

The architect should evaluate whether to preserve this vocabulary in the microservice. The tag mechanism is **shared between manual user triggers and automatic internal routing**.

### 4.7 Spike Finding: 3 Distinct Microservice Automation Subsystems

The spike discovered the microservice actually has **three** automation subsystems, not one:

1. **PipelineConversionRule** (event-driven, commit-triggered) — Sales→Onboarding only
2. **Polling ActionExecutor** (scheduled, condition-driven) — add_tag, add_comment, change_section
3. **WorkflowAction** (batch, schedule-driven) — ConversationAuditWorkflow

The legacy has ~30+ route/request actions; the microservice covers exactly 1 route.
**PipelineConversionRule should be refactored into the new lifecycle engine** — no separate code paths.

---

## 5. Design Philosophy & Constraints

### 5.1 Core Principles

1. **Forgiving system** — don't punish users for not knowing about underlying systems; handle edge cases gracefully
2. **First-principles primitives** — build composable primitives, not bespoke per-workflow code
3. **Shared primitives** — Actions and Workflows MUST share the same resolution/selection primitives
4. **Bidirectional triggers** — Workflows can trigger Actions AND Actions can trigger Workflows (architect evaluates optimal interaction model)
5. **Leverage existing investment** — use warm cache, entity model, descriptors; don't leave value on the table
6. **Optimal and correct** — lean toward the right solution even if more investment upfront; we want to get this right
7. **Let vocabulary emerge** — don't force naming; let the right terms come from the design

### 5.2 Anti-Patterns to Avoid

- **Bespoke per-workflow code** (PRIMARY concern) — no more `_resolve_office_phone()` style one-off methods
- **String-based field matching** — use the descriptor system, not `cf_dict.get("name") == "Office Phone"`
- **Over-abstraction** — open to architect's guidance on the right level of abstraction
- **QUIET flag pattern** (legacy cautionary tale) — silently suppressing errors instead of structured degradation
- **Unbounded API chains** — legacy has multi-step fallback chains with no depth limit; bound explicitly
- **isinstance dispatch** — legacy routes by `isinstance(process, Sales)`; use registry/strategy pattern instead
- **Sleep retries** — legacy uses `time.sleep()` retries; use existing async retry infrastructure

### 5.3 Error Handling Philosophy

- Use existing central API retry mechanisms — no bespoke retry logic
- Non-rate-limit API failures indicate fundamental flaws — retrying won't help
- Cascading degradation: partial result where possible → skip as last resort
- Errors are captured per-item; batch continues (established pattern from ConversationAuditWorkflow)

### 5.4 Technical Constraints

- **API rate limits**: Well-handled by existing infrastructure; not a design concern for this initiative
- **Dependency links**: Often missing — hierarchy fallback is essential
- **Cache**: Should be leveraged — existing warming system with TTLs and priorities per entity type. Architect decides session-level vs shared-level cache for workflow execution.
- **Hydration**: Architect should evaluate whether to extend `Business.from_gid_async()` with selective hydration or work around current all-or-nothing model. Lean toward optimal/correct.
- **Dependency wiring constraint**: Entity MUST be created (valid GID from Asana API) before dependency link API calls can reference it — dependency wiring is a SEPARATE phase from entity creation, not atomic

### 5.5 Entity Creation Patterns (Post-Spike)

**Mixed approach** — not one-size-fits-all:
- **Templates** for processes: Processes have subtasks, structure, and embedded configuration that justify template-based creation
- **Direct creation with field seeding** for simpler entities: Address, Hours, Offer use direct API creation with standardized field copying from parent/sibling entities
- **Field seeding** is simple — shared fields are copied from source entity to target using the descriptor system

### 5.6 Self-Loop Transitions & Delay Scheduling

- **Self-loops** (Outreach, Reactivation) are intentional — a process can transition back to its own stage
- Need **max-iteration guard** to prevent infinite loops
- **Graduated delay scheduling** is a new requirement: 90 → 180 → 360 days between re-entries
- This creates a scheduling requirement: delayed future actions that fire after N days

---

## 6. Cross-Service Integration

### 6.1 External Service Dependencies

Workflows have **varied** external dependencies:
- autom8_data is a primary dependency (CSV export, insights, gid-map)
- Other services will be involved (specifics vary per workflow)
- Some workflows are pure Asana-to-Asana operations
- DataServiceClient integration is well-established with circuit breaker + retry + stale cache fallback

### 6.2 autom8_data Changes

Likely **not required** for this initiative — autom8_data's API surface appears stable. TBD pending architect evaluation.

### 6.3 Legacy Codebase Reference

Location: `~/code/autom8/apis/asana_api`

**Mixed value** — some patterns worth extracting (resolution strategies, entity creation), others are cautionary tales (section/tag routing complexity). Should be explored during the deep spike.

---

## 7. Definition of Done & Scope

### 7.1 Done = Full Resolution Platform

- Complete resolution system with all traversal strategies (dependency shortcut + hierarchy fallback)
- Cache integration (leverage existing warm cache)
- Shared primitives usable by both Actions and Workflows
- Process subclass handling with full subclass behavior
- Entity selection strategies (top-level default, custom field predicate overrides, compound AND/OR)
- ConversationAuditWorkflow refactored to use the new primitives (proves the pattern)
- 2+ workflows functional on the platform

### 7.2 Explicitly Out of Scope

- **Legacy migration** — migrating Pipeline/Consultation/Service subtypes to microservice
- **New entity modeling** — modeling stub entities (DNA, Reconciliation, Videography) with full fields (unless architect determines minimum viable modeling is needed for lifecycle workflows, e.g., Play under DNAHolder)
- **Scheduling infrastructure** — monthly scheduling, CLI workflow execution, generic Lambda dispatcher
- **Workflow #2 as separate initiative** — AssetEdit workflow will be a follow-on initiative scoped to actual business context
- **Campaign management** — entirely separate initiative; a completely new microservice replacing legacy ads API integrations (Google, Meta, Yelp). Model pipeline stages WITHOUT campaign side effects.
- **Consultation routing** — migrating to n8n integrations; not a priority for this initiative. Lifecycle engine and n8n should stay independent.
- **Stripe payment processing** — AccountError stage is in scope for lifecycle modeling, but the Stripe SDK integration (available in `autom8y` via CodeArtifact) is a potential follow-on, not this initiative

### 7.3 Decisions Deferred to Architect

- Pull vs push resolution model (lazy vs eager field fetching)
- Read-only vs read+write resolution (or unified interface)
- Selective hydration strategy (extend Business.from_gid_async or work around it)
- Play entity: minimum viable modeling needed for lifecycle workflows
- ActionExecutor integration model (shared code + bidirectional triggering architecture)
- Resolution depth — extract legacy principles and apply first-principles design (legacy chains go 6-7 levels)
- Strategy registration pattern — how resolution strategies register themselves for entity types
- Workflow-level cache — session-scoped vs shared cache during multi-step workflow execution
- Products field expansion — design for future product additions beyond current enum values
- Tag vocabulary — whether to preserve `route_*`/`request_*`/`play_*` convention in microservice

---

## 8. Deep Exploration Spike (COMPLETED)

The 3-phase deep spike has been executed. Full report: `docs/spikes/SPIKE-workflow-resolution-platform-deep-dive.md`

### 8.1 Spike Phases Completed
1. **Phase 1 — Core System Mapping**: ActionExecutor ↔ legacy routing, cache granularity, dependency inventory
2. **Phase 2 — Legacy Pattern Extraction**: 6 good patterns, 7 cautionary tales, Products routing, per-stage behaviors
3. **Phase 3 — Entity Modeling Gaps + Synthesis**: DNA/Play modeling, consolidated recommendations

### 8.2 Key Spike Corrections
- Microservice has **3 distinct automation subsystems** (not 1): PipelineConversionRule, ActionExecutor, WorkflowAction
- Cache is **task-GID-level** granularity (not entity-level or Business-level)
- Process is **NOT warmable** (TTL=60s, warmable=False) — always fetched fresh
- Dependencies are **never created** by the microservice (only read via add/remove primitives that are unused)
- DNA stub has **zero custom fields** (legacy has only dna_priority + intercom_link)
- ProcessType enum is **missing 3 subtypes**: Month1, AccountError, Expansion

### 8.3 Production Data Verification (COMPLETED)

All 3 open questions resolved via Asana API queries. Full report: `docs/spikes/SPIKE-production-asana-verification.md`

1. **Dependency count distribution**: SPARSE — 0-1 deps per process. Play→Implementation is the only pattern. 40-item overflow threshold is wildly oversized.
2. **DNA/Play usage frequency**: BackendOnboardABusiness is dominant (100+ instances). DNAHolder is a general-purpose interaction container — 93% PLAYs, most are ad-hoc, not lifecycle-automated.
3. **Products enum values**: 6 active — Meta Marketing, TikTok Marketing, Newsletter Product, Videography, Video Session, FB & IG Marketing. Only Videography/Video Session trigger non-standard entity creation.

### 8.4 Migration Strategy (From Spike + Rounds 14-20)

- **Approach**: Big bang per pipeline stage — switch one stage's Asana Rule webhook target at a time
- **Legacy decommission**: Asana Rules auto-handle this — change the target URL from legacy to microservice
- **Webhook routing**: Currently ALL webhooks go to legacy only; microservice receives none
- **Asana Rules**: Per-project rules (1-2 per project), configured in Asana UI
- **Webhook payload**: Full task object (custom fields, section, projects) — sufficient for routing but NOT subtasks/deps/stories
- **Testing strategy**: Follow existing test patterns (unit + integration, mock Asana API responses)

### 8.5 Initiative Coordination

- **Pythia coordinates** initiative phasing — the rnd rite's orchestrator manages sprint planning, phase gates, and specialist handoffs
- **Production verification** can happen now using direnv-loaded Asana API key (no deployment needed)
- **Phased approach**: Resolution primitives first → lifecycle engine → webhook migration → workflow #2+

---

## 9. Key Files Reference

| File | Relevance |
|------|-----------|
| **Microservice — Automation** | |
| `automation/workflows/conversation_audit.py` | Current workflow with raw resolution (the smell) |
| `automation/workflows/base.py` | WorkflowAction ABC, WorkflowResult, WorkflowItemError |
| `automation/pipeline.py` | PipelineConversionRule (Sales→Onboarding only) — refactor target |
| `automation/polling/action_executor.py` | Polling ActionExecutor (3 action types: add_tag, add_comment, change_section) |
| **Microservice — Entity Model** | |
| `models/business/business.py` | Business entity with 19 descriptors + hydration |
| `models/business/descriptors.py` | CustomFieldDescriptor system (TextField, EnumField, etc.) |
| `models/business/base.py` | BusinessEntity base, HolderMixin, `_populate_children()` |
| `models/business/holder_factory.py` | Declarative holder configuration |
| `models/business/fields.py` | CascadingFieldDef, InheritedFieldDef |
| `models/business/contact.py` | ContactHolder + Contact entities |
| `models/business/location.py` | LocationHolder + Location (time_zone, address) |
| `models/business/unit.py` | Unit (COMPOSITE) + nested holder pattern |
| `models/business/offer.py` | OfferHolder + Offer (included items) |
| `models/business/process.py` | ProcessHolder + Process (lifecycle entity) — missing Month1/AccountError/Expansion |
| `models/business/asset_edit.py` | AssetEditHolder + AssetEdit (Process subclass) |
| `models/business/dna.py` | DNA stub (zero custom fields) |
| `models/business/hydration.py` | Hydration utilities, opt_fields |
| **Microservice — Cache & Persistence** | |
| `cache/backends/s3.py` | S3 cache with task-GID-level key structure |
| `cache/models/entry.py` | EntryType enum, cache entry hierarchy |
| `cache/models/settings.py` | Overflow thresholds (40 deps), TTL settings |
| `cache/integration/hierarchy_warmer.py` | Ancestor chain warming |
| `core/entity_registry.py` | TTLs and warm priorities per entity type |
| `persistence/actions.py` | SaveSession add/remove dependency primitives (unused) |
| **Microservice — Integration** | |
| `clients/data/client.py` | DataServiceClient integration |
| `lambda_handlers/conversation_audit.py` | Lambda entry point |
| **Legacy Codebase** (`~/code/autom8/apis/asana_api/`) | |
| `objects/task/main/actions.py` | Tag-based routing dispatch (route_*, request_*, play_*) |
| `objects/task/managers/process_manager/main.py` | ProcessManager routing lifecycle |
| `objects/task/managers/process_manager/dna_manager/` | DnaManager for play routing |
| `objects/task/managers/process_manager/asset_manager/` | AssetManager for asset edit routing |
| `objects/task/models/process/main.py` | Process base with 6-7 step resolution chains |
| `objects/task/models/process/pipeline/main.py` | Pipeline base with auto-completion |
| `objects/task/models/process/pipeline/{stage}/main.py` | Per-stage behaviors (9 stages) |
| `objects/task/models/dna/play/isolated_play/` | 5 IsolatedPlay subtypes |
| `objects/custom_field/models/multi_enum/products.py` | Products MultiEnumField routing |
| `objects/dependency/main.py` | Dependency CRUD operations |
| **Spike Reports** | |
| `docs/spikes/SPIKE-workflow-resolution-platform-deep-dive.md` | Consolidated 3-phase spike report (674 lines) |
| `.claude/.wip/SPIKE-phase1-core-system-mapping.md` | Phase 1: Core system mapping (472 lines) |
| `.claude/.wip/SPIKE-phase2-legacy-pattern-extraction.md` | Phase 2: Legacy pattern extraction (758 lines) |

---

## 10. Implementation Specifics (Rounds 21-28)

### 10.1 Initiative Scope (Committed)

**In scope**: Phases 1 (Resolution Primitives) + 2 (Lifecycle Engine) + 4 (Workflow #2+)
**Out of scope**: Phase 3 (Webhook Migration) and Phase 5 (Legacy Decommission) — separate follow-up initiative

### 10.2 Execution Sequence

1. **Production data verification** — resolve 3 open questions (dep counts, Play usage, Products enum) BEFORE architect designs
2. **Resolution primitives** — read-first (architect may adjust), async-native, automatic session caching (architect confirms)
3. **ConversationAuditWorkflow refactor** — first proof point. Direct replacement, no feature flag. Same behavior + test parity. May include minimal fixes.
4. **Lifecycle engine** — absorbs PipelineConversionRule. Sales→Onboarding as first route.
5. **Workflow #2+** — additional workflows on the platform

### 10.3 Resolution System Preferences (Deferred to Architect)

| Decision | Stakeholder Lean | Final Authority |
|----------|-----------------|-----------------|
| API surface | Entity-native (`ctx.business.office_phone`) sounds ideal | Architect |
| Async model | Async-native (matches existing `from_gid_async`) | **Confirmed** |
| Session caching | Automatic (no duplicate API calls within a run) sounds ideal | Architect |
| Path resolution | Both: composable low-level + declarative high-level sugar | **Confirmed** |
| Read vs write | Read-first, write layer on top | Architect (may adjust) |

### 10.4 Lifecycle Engine Preferences (Deferred to Architect)

| Decision | Stakeholder Lean | Final Authority |
|----------|-----------------|-----------------|
| Stage registration | Strategy registry sounds optimal | Architect |
| DAG model | Static base + dynamic overrides (maybe) | Architect |
| Entity creation | Engine delegates to entity model layer sounds correct | Architect |
| Multi-phase orchestration | Core design decision needing first-principles thought | Architect |
| Automation unification | Lean toward unified from start while full context is fresh | Architect |
| Tag vocabulary | No preference — architect decides | Architect |
| Webhook handler | FastAPI route sounds correct | Architect |

### 10.5 Validation & Success Criteria

**ConversationAuditWorkflow refactor**:
- Same business behavior (improvements allowed, not new features)
- All existing tests pass with new implementation
- Direct replacement — no feature flag, no shadow mode

**Lifecycle engine (Sales→Onboarding)**:
- Actually creates real Asana entities (Onboarding process, Play, dependencies)
- Test business GID: `1201774764681405`
- Clean up/delete phantom entities after validation
- Validates against production project structure

### 10.6 Foundation Work

- **Add missing ProcessType enums immediately**: Month1, AccountError, Expansion
- **Stub entity modeling**: Architect evaluates minimum viable DNA/Play modeling
- **Annotated code walkthrough**: Balance of spike reports + targeted source annotations for architect

### 10.7 Architect Context & Process

- **Production Asana access**: Direct (direnv-loaded PAT), not pre-gathered only
- **Design artifacts**: Full TDD + ADRs (architect's judgment on exact depth)
- **Decision capture**: ADRs in `docs/adr/` for all deferred decisions
- **Sprint phasing**: Large sprints (~2-3), Pythia has ultimate authority over scope/coordination
- **POC**: Architect decides if one is needed based on risk assessment
- **Risk tolerance**: Balanced — validate hard parts, move fast on obvious parts
- **Vocabulary**: Let architect name things; prefer existing codebase terms over inventing new ones; don't rename unnecessarily

### 10.8 Hard Constraints

- **None** — proactive work, no external deadlines or dependencies
- **No hard constraints** on timeline, technology choices, or external approvals

---

## 11. Interview Metadata

| Round | Theme | Key Decisions |
|-------|-------|---------------|
| 1 | Business context & priority | Proactive investment, 8+ workflows, high priority |
| 2 | AssetEdit resolution & shortcuts | Dependency links, fallback chains, vertical matching |
| 3 | Entity selection & overrides | Top-level-with-override, compound predicates, multi-result |
| 4 | Resolution primitives & deps | Compact dep objects, fixed tree (evolving), native created_at |
| 5 | Entity landscape & field access | Full hierarchy inventory, similar-core/varied-edges workflows |
| 6 | Actions integration & design | Shared primitives, cache leverage, architect decides pull/push |
| 7 | Error handling & scope | Existing retry infra, legacy/stubs/scheduling out of scope |
| 8 | Cross-service & naming | autom8_data primary, let naming emerge, deps often missing |
| 9 | Fallback chains & done criteria | Dep-first, full platform, lean toward optimal/correct |
| 10 | Legacy & constraints | Mixed legacy reference, solo dev, likely autom8_asana-only |
| 11 | Workflow vision & cache | Process lifecycle = primary pattern, explore cache in code |
| 12 | Lifecycle & state transitions | Section-based triggers, Products-driven DAG routing |
| 13 | Event detection & gaps | Asana Rules webhook, deep exploration spike recommended |
| 14 | Trigger flow & scope corrections | Webhook→handler→SaveSession is ONE pipeline; campaign mgmt OUT OF SCOPE; refactor PipelineConversionRule into engine |
| 15 | AccountError, consultations, self-loops | AccountError active (Stripe), n8n for consultations, self-loops intentional with graduated delay |
| 16 | Resolution architecture decisions | Architect decides depth/cache/registration; dependency wiring MUST be separate phase |
| 17 | Webhook details & scheduling | ALL webhooks to legacy only, full task payload, per-project rules, delay scheduling is new requirement |
| 18 | Entity creation & production access | Mixed template/direct creation, field seeding is simple copying, CAN query production via direnv |
| 19 | Migration & decommission strategy | Big bang per stage, Asana Rules auto-handle decommission, n8n stays independent |
| 20 | Products expansion & testing | Design for expansion, follow existing test patterns, Stripe SDK in autom8y, coverage confirmed |
| **Implementation-Specific (Rounds 21-28)** | | |
| 21 | Initiative scope & sequencing | Phases 1-2+4, ConversationAudit then lifecycle, read-first, absorb PCR into engine |
| 22 | Resolution API design | Entity-native aspiration, async-native confirmed, auto session cache, both composable+declarative |
| 23 | Lifecycle engine design | Strategy registry lean, static+dynamic DAG, engine delegates creation, multi-phase needs first-principles |
| 24 | CAW refactor & testing | Refactor+minimal fixes, follow test patterns, add 3 missing enums immediately, architect evaluates stubs |
| 25 | Webhook & automation integration | FastAPI route lean, unified from start lean, tag vocab architect decides, prod verify before design |
| 26 | Sprint structure & design depth | Large sprints (Pythia manages), full TDD+ADRs, POC architect decides, balanced risk |
| 27 | Validation & success criteria | CAW=behavior+test parity, lifecycle=real Asana entities (GID:1201774764681405), direct replacement, no constraints |
| 28 | Architect context & process | Direct prod access, source+spike+annotated walkthrough, ADRs for decisions, existing vocabulary preferred |
