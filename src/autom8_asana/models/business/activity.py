"""Section activity classifier for entity-level account activity state.

Maps Asana project section names to AccountActivity categories (active,
activating, inactive, ignored) for Offer and Unit entity types.

Frozen, no I/O, O(1) lookup, case-insensitive matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# AccountActivity Enum
# ---------------------------------------------------------------------------


class AccountActivity(StrEnum):
    """Universal vocabulary for account activity state.

    Priority ordering (highest to lowest): ACTIVE > ACTIVATING > INACTIVE > IGNORED.
    Used by Business.max_unit_activity to aggregate across child Units.
    """

    ACTIVE = "active"
    ACTIVATING = "activating"
    INACTIVE = "inactive"
    IGNORED = "ignored"


# Priority ordering for aggregation (max_unit_activity).
# Index position determines priority: lower index = higher priority.
ACTIVITY_PRIORITY: tuple[AccountActivity, ...] = (
    AccountActivity.ACTIVE,
    AccountActivity.ACTIVATING,
    AccountActivity.INACTIVE,
    AccountActivity.IGNORED,
)


# ---------------------------------------------------------------------------
# SectionClassifier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SectionClassifier:
    """Maps section names to AccountActivity for a single entity type.

    Immutable after construction. Thread-safe for concurrent workflows.
    All lookups are O(1) dict access, case-insensitive.

    Attributes:
        entity_type: Entity type this classifier serves ("offer", "unit").
        project_gid: Asana project GID for this entity type.
        _mapping: Internal dict of lowercase section name -> AccountActivity.
    """

    entity_type: str
    project_gid: str
    _mapping: dict[str, AccountActivity] = field(repr=False)

    def classify(self, section_name: str) -> AccountActivity | None:
        """Classify a section name into an AccountActivity category.

        Args:
            section_name: Section name from Asana (e.g., "ACTIVE", "Onboarding").

        Returns:
            AccountActivity or None if the section is unknown.
        """
        return self._mapping.get(section_name.lower())

    def sections_for(self, *categories: AccountActivity) -> frozenset[str]:
        """Return section names matching any of the given categories.

        Args:
            categories: One or more AccountActivity values to filter by.

        Returns:
            Frozenset of lowercase section names.
        """
        cat_set = set(categories)
        return frozenset(k for k, v in self._mapping.items() if v in cat_set)

    def active_sections(self) -> frozenset[str]:
        """Section names classified as ACTIVE."""
        return self.sections_for(AccountActivity.ACTIVE)

    def billable_sections(self) -> frozenset[str]:
        """Section names that represent billable state (ACTIVE + ACTIVATING)."""
        return self.sections_for(AccountActivity.ACTIVE, AccountActivity.ACTIVATING)

    @classmethod
    def from_groups(
        cls,
        entity_type: str,
        project_gid: str,
        groups: dict[str, set[str]],
    ) -> SectionClassifier:
        """Factory accepting legacy dict format.

        Args:
            entity_type: Entity type name (e.g., "offer", "unit").
            project_gid: Asana project GID.
            groups: Dict mapping category name to set of section names.
                    Keys must be valid AccountActivity values.

        Returns:
            Frozen SectionClassifier instance.

        Raises:
            ValueError: If a category name is not a valid AccountActivity.
        """
        mapping: dict[str, AccountActivity] = {}
        for category_name, section_names in groups.items():
            category = AccountActivity(category_name)
            for name in section_names:
                mapping[name.lower()] = category
        return cls(
            entity_type=entity_type,
            project_gid=project_gid,
            _mapping=mapping,
        )


# ---------------------------------------------------------------------------
# extract_section_name
# ---------------------------------------------------------------------------


def extract_section_name(
    task: Any,
    project_gid: str | None = None,
) -> str | None:
    """Extract section name from task memberships.

    Canonical implementation of section name extraction. Handles both
    Task model objects (with .memberships attribute) and raw dicts
    (with "memberships" key).

    Args:
        task: Task instance or dict with memberships data.
        project_gid: Optional project GID to disambiguate multi-project tasks.
                     If provided, only memberships for that project are checked.

    Returns:
        Section name string or None if no section found.
    """
    # Duck-type: support both Task model (.memberships) and dict (.get("memberships"))
    memberships = (
        task.get("memberships")
        if isinstance(task, dict)
        else getattr(task, "memberships", None)
    )
    if not memberships:
        return None

    for membership in memberships:
        if not isinstance(membership, dict):
            continue

        if project_gid:
            project = membership.get("project", {})
            if isinstance(project, dict) and project.get("gid") != project_gid:
                continue

        section = membership.get("section")
        if section and isinstance(section, dict):
            name = section.get("name")
            if name is not None and isinstance(name, str):
                return str(name)

    return None


# ---------------------------------------------------------------------------
# Module-Level Classifier Instances
# ---------------------------------------------------------------------------

OFFER_CLASSIFIER: SectionClassifier = SectionClassifier.from_groups(
    entity_type="offer",
    project_gid="1143843662099250",
    groups={
        "active": {
            "PENDING APPROVAL",
            "CALL",
            "OPTIMIZE - Human Review",
            "OPTIMIZE QUANTITY - Request Asset Edit",
            "OPTIMIZE QUANTITY - Decrease Lead Friction",
            "OPTIMIZE QUANTITY - Update Offer Price Too High",
            "OPTIMIZE QUANTITY - Update Targeting of Proven Asset",
            "OPTIMIZE QUANTITY - Update Offer Name",
            "OPTIMIZE QUALITY - Update Targeting",
            "OPTIMIZE QUALITY - Poor Show Rates",
            "OPTIMIZE QUALITY - Pending Leads and/or Update Targeting",
            "RESTART - Request Testimonial",
            "RUN OPTIMIZATIONS",
            "STAGING",
            "STAGED",
            "ACTIVE",
            "RESTART - Pending Leads",
            "SYSTEM ERROR",
            "REJECTIONS / REVIEW",
            "REVIEW OPTIMIZATION",
            "MANUAL",
            "ONE-OFF",         # Per truth audit: active one-time campaigns
        },
        "activating": {
            "ACTIVATING",
            "LAUNCH ERROR",
            "IMPLEMENTING",
            "NEW LAUNCH REVIEW",
            "AWAITING ACCESS",
        },
        "inactive": {
            "ACCOUNT ERROR",
            "AWAITING REP UPDATE",
            "INACTIVE",
        },
        "ignored": {
            "Sales Process",
            "Complete",
            "Plays",
            "PLAYS",           # Per truth audit: template/reference section
            "Performance Concerns",
            "PERFORMANCE CONCERNS",
        },
    },
)

UNIT_CLASSIFIER: SectionClassifier = SectionClassifier.from_groups(
    entity_type="unit",
    project_gid="1201081073731555",
    groups={
        "active": {
            "Month 1",
            "Consulting",
            "Active",
        },
        "activating": {
            "Onboarding",
            "Implementing",
            "Delayed",
            "Preview",
            "Engaged",       # Per truth audit: forward momentum, not inactive
            "Scheduled",     # Per truth audit: scheduled interaction = activating
        },
        "inactive": {
            "Unengaged",
            "Paused",
            "Cancelled",
            "No Start",
            "Account Review",  # Per truth audit: moved from EXCLUDED to INACTIVE
            "Account Error",   # Per truth audit: moved from EXCLUDED to INACTIVE
        },
        "ignored": {
            "Templates",
        },
    },
)

# ---------------------------------------------------------------------------
# Process Pipeline Classifiers (TC-5)
# ---------------------------------------------------------------------------

# Per-pipeline-type section name -> AccountActivity mappings for process
# pipelines. Keyed by pipeline_type (matches PIPELINE_TYPE_BY_PROJECT_GID
# values in gid_push.py). Each value maps AccountActivity category name
# -> set of section names (case-insensitive at classify time).
#
# PROVISIONAL: Section names are educated guesses based on existing
# UNIT_CLASSIFIER / OFFER_CLASSIFIER patterns. These MUST be verified
# against live Asana project data (e.g. df["section_name"].value_counts()
# per project GID) before shipping to production.
# Verified against live Asana API (2026-03-29). Section names are ALL CAPS
# and highly standardized across process pipeline projects. Stakeholder
# classification decisions:
#   - OPPORTUNITY and CONTACTED are ACTIVE (not activating) in our business context
#   - VIDEO ONLY is IGNORED (not inactive)
#   - CONVERTED and COMPLETED are terminal end-states -> IGNORED
_DEFAULT_PROCESS_SECTIONS: dict[str, set[str]] = {
    "active": {"ACTIVE", "EXECUTING", "BUILDING", "PROCESSING", "OPPORTUNITY", "CONTACTED"},
    "activating": {"SCHEDULED", "REQUESTED", "DELAYED"},
    "inactive": {"INACTIVE", "DID NOT CONVERT", "MAYBE", "UNPROCESSED"},
    "ignored": {
        "TEMPLATE", "TEMPLATES", "COMPLETED", "CONVERTED", "TASKS",
        "FREE MONTH", "VIDEO ONLY", "Untitled section",
    },
}

PROCESS_PIPELINE_SECTIONS: dict[str, dict[str, set[str]]] = {
    "sales": _DEFAULT_PROCESS_SECTIONS,
    "onboarding": _DEFAULT_PROCESS_SECTIONS,
    "outreach": _DEFAULT_PROCESS_SECTIONS,
    "retention": _DEFAULT_PROCESS_SECTIONS,
    "reactivation": _DEFAULT_PROCESS_SECTIONS,
    "expansion": _DEFAULT_PROCESS_SECTIONS,
    "implementation": _DEFAULT_PROCESS_SECTIONS,
    "account_error": _DEFAULT_PROCESS_SECTIONS,
}

CLASSIFIERS: dict[str, SectionClassifier] = {
    "offer": OFFER_CLASSIFIER,
    "unit": UNIT_CLASSIFIER,
}

# Build process pipeline classifiers from config.
# project_gid is left empty to avoid circular imports with gid_push.py
# (PIPELINE_TYPE_BY_PROJECT_GID lives there). SectionClassifier.project_gid
# is informational only -- not used by classify().
for _pipeline_type, _groups in PROCESS_PIPELINE_SECTIONS.items():
    CLASSIFIERS[_pipeline_type] = SectionClassifier.from_groups(
        entity_type=_pipeline_type,
        project_gid="",
        groups=_groups,
    )


def get_classifier(entity_type: str) -> SectionClassifier | None:
    """Look up classifier by entity type.

    Args:
        entity_type: Entity type name (e.g., "offer", "unit").

    Returns:
        SectionClassifier or None if no classifier registered.
    """
    return CLASSIFIERS.get(entity_type)
