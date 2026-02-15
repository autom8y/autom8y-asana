# SPIKE: ContactHolder Section-to-Activity Mapping

```yaml
id: SPIKE-CH-SECTIONS-001
status: COMPLETE
date: 2026-02-15
author: spike-investigator
upstream: PRD-SECTION-ENUM-001 (FR-4.1)
decision: OPTION (b) — No clean mapping; retain current pattern
```

---

## Question

Do the sections in the ContactHolder Asana project (`1201500116978260`) map to
activity categories (ACTIVE, ACTIVATING, INACTIVE, IGNORED), enabling section-
targeted fetch for `ConversationAuditWorkflow._enumerate_contact_holders()`?

## Decision This Informs

PRD-SECTION-ENUM-001, FR-4.2 vs FR-4.3:
- **FR-4.2**: If sections map to activity → create `CONTACT_HOLDER_CLASSIFIER`, implement section-targeted fetch
- **FR-4.3**: If sections do NOT map to activity → document finding, define alternative optimization or accept current pattern

---

## Findings

### Finding 1: ContactHolder Activity Is DERIVED, Not Section-Based

Unlike Offer and Unit entities where activity state is determined by which
**section** the task resides in:

| Entity | Activity Source | Mechanism |
|--------|---------------|-----------|
| **Offer** | Own section membership | `OFFER_CLASSIFIER.classify(section_name)` → `AccountActivity` |
| **Unit** | Own section membership | `UNIT_CLASSIFIER.classify(section_name)` → `AccountActivity` |
| **ContactHolder** | **Parent Business's child Unit activity** | `Business.max_unit_activity` via depth=2 hydration |

The activity gate in `_process_holder()` (conversation_audit.py:308-324) calls
`_resolve_business_activity(parent_gid)`, which hydrates the parent Business
to depth=2 (Business → UnitHolder → Units), then reads `max_unit_activity`.

**This is a fundamentally different activity model.** A ContactHolder's "active"
status depends on its parent Business's Unit children's section placements —
not on the ContactHolder's own section. Even if ContactHolder sections exist
and have activity-like names, they would NOT reflect the true activity state
(which is computed from a different project's section structure).

### Finding 2: No Section Infrastructure Exists for ContactHolder

Exhaustive codebase search found zero evidence of ContactHolder section structure:

| Evidence Type | Found? | Details |
|---------------|--------|---------|
| Classifier instance (`CONTACT_HOLDER_CLASSIFIER`) | No | Only `OFFER_CLASSIFIER` and `UNIT_CLASSIFIER` exist in `activity.py:255-258` |
| Section names in config/YAML | No | `lifecycle_stages.yaml` has no `contact_holder` key |
| Section properties on model | No | `ContactHolder` class has no section-related properties |
| Test fixtures with sections | No | `test_conversation_audit.py` mocks omit `memberships` entirely |
| Section references in workflow code | No | `_enumerate_contact_holders()` does not request `memberships.section.name` in `opt_fields` |

### Finding 3: Current Optimization Is Already Effective

The `_activity_map` dedup cache (conversation_audit.py:261-262) ensures each
unique parent Business is hydrated **at most once** per workflow cycle:

```python
if business_gid in self._activity_map:
    return self._activity_map[business_gid]
```

If N ContactHolders share M unique parent Businesses (N >> M typically, since
each Business has multiple ContactHolders), the hydration cost is O(M), not O(N).

### Finding 4: Section-Targeted Fetch Would Not Help

Even IF ContactHolder sections existed and mapped to activity states:

1. **Section-level filtering is wrong for this entity type.** Activity is
   derived from the parent Business, not from the ContactHolder's own section.
   A ContactHolder in an "Active" section whose parent Business became inactive
   (because its Units moved sections) would be incorrectly included.

2. **No mechanism moves ContactHolders between sections based on Business
   activity.** Unlike Offers and Units (which are manually/automatically moved
   between sections by the automation system), ContactHolders have no section
   lifecycle tied to their parent Business's activity state.

3. **The only remaining waste is the initial enumeration API call.** Fetching
   ALL non-completed ContactHolders from the project-level endpoint. This is
   a single paginated API call — the actual cost is small compared to the
   per-holder processing cost that the `_activity_map` already optimizes.

---

## Recommendation

**OPTION (b): No clean mapping exists. Accept the current pattern as optimal.**

The ConversationAudit workflow's activity-gating model is fundamentally different
from Offer/Unit section-based classification. Section-targeted fetch is not
applicable here because:

1. Activity is derived from the parent Business hierarchy, not ContactHolder sections
2. No section infrastructure exists (or should exist) for this entity type
3. The `_activity_map` dedup cache already provides effective optimization
4. The single project-level enumeration call is low-cost relative to per-holder processing

### Alternative Optimizations (Deferred — Not This Initiative)

For future consideration if ContactHolder enumeration latency becomes a concern:

| Optimization | Description | Complexity | Benefit |
|-------------|-------------|------------|---------|
| **Bulk Business pre-resolution** | Extract unique `parent_gid` set from enumeration, batch-resolve Business activities via a single multi-GID query, then filter holder list before `_process_holder()` | Medium | Eliminates individual hydration calls; replaces O(M) sequential hydrations with 1 bulk query |
| **Business activity caching** | Persist last-known `max_unit_activity` on Business entity via cache layer, read from cache instead of depth=2 hydration | High | Sub-millisecond activity lookup; but requires cache invalidation when Unit sections change |
| **Lazy enumeration with early termination** | Stream ContactHolders instead of `collect()`, skip holders lazily during iteration | Low | Avoids materializing full list in memory; but still fetches all pages from API |

None of these are in scope for the Section-Targeted Enumeration initiative.

---

## Impact on PRD-SECTION-ENUM-001

| Requirement | Impact |
|-------------|--------|
| **FR-4.1** (spike) | COMPLETE — this document |
| **FR-4.2** (section-targeted fetch if sections map) | NOT APPLICABLE — sections do not map to activity |
| **FR-4.3** (alternative optimization if no mapping) | Current `_activity_map` pattern is accepted as the baseline; no implementation change needed |
| **FR-4.4** (preserve `_resolve_business_activity()`) | Preserved — no changes to ConversationAudit |
| **US-3** (ConversationAudit migration) | CLOSED — not viable for section-targeted enumeration |
| **SC-7** (spike completed with documented recommendation) | SATISFIED — this document |

---

## Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| ConversationAudit workflow | `src/autom8_asana/automation/workflows/conversation_audit.py` | Read (lines 221-284) |
| ContactHolder model | `src/autom8_asana/models/business/contact.py` | Read (lines 206-237) |
| Activity classifiers | `src/autom8_asana/models/business/activity.py` | Read (lines 178-258) |
| Project registry | `src/autom8_asana/core/project_registry.py` | Read (line 33) |
| Workflow config | `config/rules/conversation-audit.yaml` | Read |
| Lifecycle stages | `config/lifecycle_stages.yaml` | Searched (no contact_holder entries) |
| Test fixtures | `tests/unit/automation/workflows/test_conversation_audit.py` | Searched (no section mocks) |
| PRD | `.claude/artifacts/PRD-section-targeted-enumeration.md` | Read (FR-4.1 through FR-4.4) |
| TDD | `.claude/artifacts/TDD-section-targeted-enumeration.md` | Read (Section 3.4) |
