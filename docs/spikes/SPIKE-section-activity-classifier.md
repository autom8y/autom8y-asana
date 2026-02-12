# SPIKE: Section Activity Classifier Primitive

**Date**: 2026-02-12
**Status**: Complete
**Decision Informs**: Workflow scoping (InsightsExport, ConversationAudit), metrics filtering, entity lifecycle state

## Question

What is the optimal strategy for introducing a reusable primitive that classifies Asana project sections into activity categories (active, activating, inactive, ignore) across multiple entity types?

## Context

### The Problem

Both `InsightsExportWorkflow` and `ConversationAuditWorkflow` enumerate **all** non-completed tasks from their respective projects. Neither filters by account activity status. This means paused, onboarding, error-state, and even template tasks get processed -- wasting API calls to autom8_data and producing reports for accounts that don't need them.

### Legacy Pattern

The legacy system solved this with per-entity section-to-category dicts:

```python
# Offer sections (BusinessOffers project, 21+ sections)
OFFER_SECTIONS = {
    "active":     {"ACTIVE", "STAGED", "STAGING", "PENDING APPROVAL", "CALL", ...},
    "activating": {"ACTIVATING", "IMPLEMENTING", "LAUNCH ERROR", ...},
    "inactive":   {"ACCOUNT ERROR", "AWAITING REP UPDATE", "INACTIVE"},
    "ignore":     {"sales_process", "complete", "plays", "performance_concerns"},
}

# Unit sections (Business Units project, 14+ sections)
UNIT_SECTIONS = {
    "active":     {"Month 1", "Consulting", "Active"},
    "activating": {"Onboarding", "Implementing", "Delayed", "Preview"},
    "inactive":   {"Unengaged", "Engaged", "Scheduled", "Paused", "Cancelled", "No Start"},
    "ignore":     {"Templates"},
}
```

### Current Codebase State

| Component | What it knows about sections | Gap |
|---|---|---|
| `OfferSection` enum | Only `ACTIVE` GID. PAUSED/CANCELLED/ONBOARDING are TODO comments | No grouping, 1 of 30+ sections |
| `ProcessSection` enum | 7 pipeline states (OPPORTUNITY..DID_NOT_CONVERT) | No activity categorization |
| `CascadingSectionConfig` | Per-stage section names for offer/unit/business | Produces state, doesn't classify it |
| `lifecycle_stages.yaml` | 10 stages with cascading section names | Source of truth for lifecycle transitions only |
| `Metrics Scope` | Filters by single section GID or name | No multi-section "group" concept |
| `_extract_section()` | Extracts section name from memberships | Raw extraction, no classification |
| `Process.pipeline_state` | Maps membership to `ProcessSection` enum | Closest to what we need but flat |

## Options Evaluated

### Option A: Enum + Frozen Config Dict (Recommended)

```python
# --- Universal vocabulary ---
class AccountActivity(str, Enum):
    ACTIVE = "active"
    ACTIVATING = "activating"
    INACTIVE = "inactive"
    IGNORED = "ignored"

# --- Frozen classifier ---
@dataclass(frozen=True)
class SectionClassifier:
    """Maps section names -> AccountActivity for a single entity type."""
    entity_type: str
    project_gid: str
    _mapping: dict[str, AccountActivity]  # lowercase name -> category

    def classify(self, section_name: str) -> AccountActivity | None:
        return self._mapping.get(section_name.lower())

    def active_sections(self) -> frozenset[str]:
        """Section names that count as 'active'."""
        return frozenset(k for k, v in self._mapping.items()
                         if v == AccountActivity.ACTIVE)

    def billable_sections(self) -> frozenset[str]:
        """Sections that represent billable state (active + activating)."""
        return frozenset(k for k, v in self._mapping.items()
                         if v in {AccountActivity.ACTIVE, AccountActivity.ACTIVATING})

    @classmethod
    def from_groups(cls, entity_type: str, project_gid: str,
                    groups: dict[str, set[str]]) -> SectionClassifier:
        mapping = {}
        for category_name, section_names in groups.items():
            category = AccountActivity(category_name)
            for name in section_names:
                mapping[name.lower()] = category
        return cls(entity_type=entity_type, project_gid=project_gid, _mapping=mapping)
```

**Pros:**
- Pure Python, no YAML indirection, no runtime I/O
- Immutable after construction -- safe for concurrent workflows
- `from_groups()` factory accepts the legacy dict format directly
- Classification is O(1) dict lookup, case-insensitive
- Composable: `billable_sections()` returns the set workflows need to filter by
- Testable: frozen dataclass, no side effects

**Cons:**
- Section names hardcoded in Python (but they're already hardcoded in OfferSection, ProcessSection, lifecycle YAML)
- Adding a new Asana section requires a code change (acceptable -- new sections are rare and have lifecycle implications)

### Option B: YAML-Driven Config

Define section groups in a new YAML file loaded at startup like `lifecycle_stages.yaml`.

**Pros:** Non-code config change for new sections.
**Cons:** Adds another config file dependency. Section names change rarely enough that the YAML indirection isn't justified. The lifecycle YAML already exists -- two competing config sources for section knowledge is worse than one Python module.

### Option C: Custom Field Enum on Asana Tasks

Add an "Account Status" dropdown custom field to Offer/Unit tasks in Asana, set by the lifecycle engine alongside section cascading.

**Pros:** Single field to query. Independent of board layout.
**Cons:** Requires Asana admin changes. Duplicates section state (two sources of truth). Every lifecycle transition must update both section AND custom field. Migration effort for 1000+ existing tasks. The section IS the state in this system -- adding a parallel field creates drift risk.

### Option D: Derive from Lifecycle YAML

Parse `lifecycle_stages.yaml` to auto-build the mapping: each stage's `cascading_sections.offer` value maps to a category derived from the stage name.

**Pros:** Single source of truth with lifecycle config.
**Cons:** Only covers sections touched by lifecycle transitions. The Offer project has 30+ sections (OPTIMIZE QUANTITY variants, RESTART variants, etc.) that are operational states within the "active" category -- the lifecycle engine never touches these. Lifecycle YAML knows about ~8 offer section names; the real mapping has ~30. Coverage gap is fatal.

## Recommendation: Option A

### Module Location

```
src/autom8_asana/models/business/activity.py
```

Co-located with entity models (same package), not in lifecycle/ (which is about transitions, not classification) or config/ (no runtime loading needed).

### Registry Pattern

```python
# activity.py

OFFER_CLASSIFIER = SectionClassifier.from_groups(
    entity_type="offer",
    project_gid="1143843662099250",
    groups={
        "active": {
            "PENDING APPROVAL", "CALL", "OPTIMIZE - Human Review",
            "OPTIMIZE QUANTITY - Request Asset Edit",
            "OPTIMIZE QUANTITY - Decrease Lead Friction",
            "OPTIMIZE QUANTITY - Update Offer Price Too High",
            "OPTIMIZE QUANTITY - Update Targeting of Proven Asset",
            "OPTIMIZE QUANTITY - Update Offer Name",
            "OPTIMIZE QUALITY - Update Targeting",
            "OPTIMIZE QUALITY - Poor Show Rates",
            "OPTIMIZE QUALITY - Pending Leads and/or Update Targeting",
            "RESTART - Request Testimonial",
            "RUN OPTIMIZATIONS", "STAGING", "STAGED", "ACTIVE",
            "RESTART - Pending Leads", "SYSTEM ERROR",
            "REJECTIONS / REVIEW", "REVIEW OPTIMIZATION", "MANUAL",
        },
        "activating": {
            "ACTIVATING", "LAUNCH ERROR", "IMPLEMENTING",
            "NEW LAUNCH REVIEW", "AWAITING ACCESS",
        },
        "inactive": {
            "ACCOUNT ERROR", "AWAITING REP UPDATE", "INACTIVE",
        },
        "ignored": {
            "Sales Process", "Complete", "Plays", "Performance Concerns",
        },
    },
)

UNIT_CLASSIFIER = SectionClassifier.from_groups(
    entity_type="unit",
    project_gid="1201081073731555",
    groups={
        "active": {"Month 1", "Consulting", "Active"},
        "activating": {"Onboarding", "Implementing", "Delayed", "Preview"},
        "inactive": {
            "Unengaged", "Engaged", "Scheduled", "Paused",
            "Cancelled", "No Start",
        },
        "ignored": {"Templates"},
    },
)

# Registry for lookup by entity type
CLASSIFIERS: dict[str, SectionClassifier] = {
    "offer": OFFER_CLASSIFIER,
    "unit": UNIT_CLASSIFIER,
}

def get_classifier(entity_type: str) -> SectionClassifier | None:
    return CLASSIFIERS.get(entity_type)
```

### Integration Points

#### 1. Workflow Enumeration (Primary Use Case)

**InsightsExportWorkflow._enumerate_offers()** -- change from project-wide to section-filtered:

```python
async def _enumerate_offers(self) -> list[dict[str, Any]]:
    from autom8_asana.models.business.activity import OFFER_CLASSIFIER, AccountActivity

    billable = OFFER_CLASSIFIER.billable_sections()  # active + activating

    page_iterator = self._asana_client.tasks.list_for_project_async(
        OFFER_PROJECT_GID,
        opt_fields=["name", "completed", "parent", "parent.name",
                     "memberships.section.name"],
        completed_since="now",
    )
    tasks = await page_iterator.collect()
    return [
        {"gid": t.gid, "name": t.name,
         "parent_gid": t.parent.gid if t.parent else None}
        for t in tasks
        if not t.completed and _section_name(t) in billable
    ]
```

**ConversationAuditWorkflow** -- similar pattern, but scoping depends on whether ContactHolders have their own section classification or derive activity from parent Business/Unit.

#### 2. Entity Property (Optional Convenience)

Add to `Offer` model:

```python
@property
def account_activity(self) -> AccountActivity | None:
    from autom8_asana.models.business.activity import OFFER_CLASSIFIER
    section_name = self._extract_own_section()
    if section_name is None:
        return None
    return OFFER_CLASSIFIER.classify(section_name)
```

#### 3. Metrics Scope (Future Enhancement)

Current `Scope` filters by single section GID. Could extend to accept `AccountActivity`:

```python
_ACTIVE_OFFER_SCOPE = Scope(
    entity_type="offer",
    activity=AccountActivity.ACTIVE,  # replaces section= / section_name=
    dedup_keys=["office_phone", "vertical"],
)
```

The metrics resolver would expand `activity=ACTIVE` to the set of section GIDs via the classifier. This replaces the current single-section-GID limitation.

#### 4. DataFrame Extraction (Future Enhancement)

Add `account_activity` column alongside existing `section` column in TaskRow:

```python
class TaskRow(BaseModel):
    section: str | None = None
    account_activity: str | None = None  # "active", "activating", "inactive", "ignored"
```

### What This Replaces

| Current | After |
|---|---|
| `OfferSection` enum (1 member) | Subsumed by `OFFER_CLASSIFIER` -- the classifier knows all sections |
| `has_active_ads` property | Kept but complementary -- `has_active_ads` is ad-platform truth, `account_activity` is lifecycle truth |
| Project-wide enumeration in workflows | Section-filtered enumeration |
| Metrics `Scope(section=GID)` | `Scope(activity=ACTIVE)` expanding to multiple GIDs |

### Relationship to Lifecycle Engine

The classifier and lifecycle engine are **complementary, not competing**:

- **Lifecycle engine** (producer): Moves entities between sections via `CascadingSectionConfig`
- **Classifier** (consumer): Reads current section and categorizes it

The cascading section names in `lifecycle_stages.yaml` are a subset of sections the classifier knows about. Validation at startup can verify that every `cascading_sections.offer` value in the YAML is a known section in `OFFER_CLASSIFIER`, catching drift early.

### Migration Path

1. **Phase 1**: `activity.py` module with `AccountActivity`, `SectionClassifier`, `OFFER_CLASSIFIER`, `UNIT_CLASSIFIER`
2. **Phase 2**: Update `InsightsExportWorkflow._enumerate_offers()` to filter by billable sections
3. **Phase 3**: Update `ConversationAuditWorkflow` (requires deciding scoping strategy for ContactHolders)
4. **Phase 4**: Entity `.account_activity` property, DataFrame column extraction
5. **Phase 5**: Metrics `Scope` integration, replace `OfferSection` enum usages

### Risk Areas

- **Unknown sections**: An Asana section not in the classifier returns `None`. Workflows should treat unknown as "skip with warning" (safe default) rather than "include" (unsafe) or "crash" (disruptive).
- **ContactHolder scoping**: ContactHolders don't have their own section semantics. Their activity is derived from parent Business/Unit. The ConversationAudit workflow needs to resolve the parent and check the *parent's* activity, not the ContactHolder's section. This is a second-order integration.
- **Section name drift**: If someone renames a section in Asana, the classifier won't match it. Mitigation: startup validation that compares classifier section names against live Asana sections (optional, adds API call).

## Follow-Up Actions

- [ ] Implement `activity.py` with `AccountActivity`, `SectionClassifier`, per-entity instances
- [ ] Add `_section_name()` helper for extracting section from task memberships (project-scoped)
- [ ] Update `InsightsExportWorkflow._enumerate_offers()` to filter by `billable_sections()`
- [ ] Update `ConversationAuditWorkflow._enumerate_contact_holders()` with parent-derived scoping
- [ ] Tests: classifier construction, case-insensitive matching, unknown section handling, workflow filtering
- [ ] Decide: startup validation of classifier vs live Asana sections (optional hardening)
- [ ] Future: Metrics `Scope(activity=...)` expansion, DataFrame `account_activity` column
