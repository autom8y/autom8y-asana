"""Unit tests for patterns module.

Per FR-DET-005/ADR-0117: Tests for word boundary-aware pattern matching.

Test cases:
1. PatternSpec creation and attributes
2. Pattern config contains all expected holder types
3. Pattern priority ordering
4. Decoration stripping
5. Word boundary matching (false positive prevention)
"""

from __future__ import annotations

import pytest

from autom8_asana.models.business.detection import (
    CONFIDENCE_TIER_2,
    EntityType,
    _compile_word_boundary_pattern,
    _matches_pattern_with_word_boundary,
    _strip_decorations,
    detect_entity_type,
)
from autom8_asana.models.business.patterns import (
    STRIP_PATTERNS,
    PatternSpec,
    get_pattern_config,
    get_pattern_priority,
)
from autom8_asana.models.task import Task

# --- Fixtures ---


def make_task(gid: str = "task_gid", name: str | None = "Test Task") -> Task:
    """Create a Task with specified attributes."""
    return Task(gid=gid, name=name)


# --- Test: PatternSpec ---


class TestPatternSpec:
    """Tests for PatternSpec dataclass."""

    def test_creation_with_defaults(self) -> None:
        """PatternSpec can be created with default values."""
        spec = PatternSpec(patterns=("contacts", "contact"))

        assert spec.patterns == ("contacts", "contact")
        assert spec.word_boundary is True
        assert spec.strip_decorations is True

    def test_creation_with_custom_values(self) -> None:
        """PatternSpec can be created with custom values."""
        spec = PatternSpec(
            patterns=("custom",),
            word_boundary=False,
            strip_decorations=False,
        )

        assert spec.patterns == ("custom",)
        assert spec.word_boundary is False
        assert spec.strip_decorations is False

    def test_frozen_immutability(self) -> None:
        """PatternSpec is immutable (frozen)."""
        spec = PatternSpec(patterns=("test",))

        with pytest.raises(AttributeError):
            spec.word_boundary = False  # type: ignore[misc]


# --- Test: Pattern Config ---


class TestPatternConfig:
    """Tests for get_pattern_config()."""

    def test_contains_all_holder_types(self) -> None:
        """Pattern config contains all expected holder entity types."""
        config = get_pattern_config()

        expected_holders = [
            EntityType.CONTACT_HOLDER,
            EntityType.UNIT_HOLDER,
            EntityType.OFFER_HOLDER,
            EntityType.PROCESS_HOLDER,
            EntityType.LOCATION_HOLDER,
            EntityType.DNA_HOLDER,
            EntityType.RECONCILIATIONS_HOLDER,
            EntityType.ASSET_EDIT_HOLDER,
            EntityType.VIDEOGRAPHY_HOLDER,
        ]

        for holder in expected_holders:
            assert holder in config, f"Missing {holder} in pattern config"
            assert isinstance(config[holder], PatternSpec)

    def test_contact_holder_patterns(self) -> None:
        """CONTACT_HOLDER has correct patterns."""
        config = get_pattern_config()
        spec = config[EntityType.CONTACT_HOLDER]

        assert "contacts" in spec.patterns
        assert "contact" in spec.patterns
        assert spec.word_boundary is True

    def test_unit_holder_patterns(self) -> None:
        """UNIT_HOLDER has correct patterns."""
        config = get_pattern_config()
        spec = config[EntityType.UNIT_HOLDER]

        assert "units" in spec.patterns
        assert "unit" in spec.patterns
        assert "business units" in spec.patterns

    def test_asset_edit_holder_patterns(self) -> None:
        """ASSET_EDIT_HOLDER has multi-word pattern."""
        config = get_pattern_config()
        spec = config[EntityType.ASSET_EDIT_HOLDER]

        assert "asset edit" in spec.patterns
        assert "asset edits" in spec.patterns


# --- Test: Pattern Priority ---


class TestPatternPriority:
    """Tests for get_pattern_priority()."""

    def test_asset_edit_holder_first(self) -> None:
        """ASSET_EDIT_HOLDER is first in priority (most specific)."""
        priority = get_pattern_priority()

        assert priority[0] == EntityType.ASSET_EDIT_HOLDER

    def test_contains_all_configured_types(self) -> None:
        """Priority list contains all configured types."""
        config = get_pattern_config()
        priority = get_pattern_priority()

        for entity_type in config:
            assert entity_type in priority, f"Missing {entity_type} in priority"


# --- Test: Strip Patterns ---


class TestStripPatterns:
    """Tests for STRIP_PATTERNS and _strip_decorations()."""

    def test_strip_patterns_defined(self) -> None:
        """STRIP_PATTERNS contains expected patterns."""
        # Should have patterns for common decorations
        assert len(STRIP_PATTERNS) >= 5

    @pytest.mark.parametrize(
        ("input_name", "expected"),
        [
            # Prefix decorations
            ("[URGENT] Contacts", "Contacts"),
            ("[Important] Units", "Units"),
            (">> Contacts", "Contacts"),
            (">>> Priority Offers", "Priority Offers"),
            # Suffix decorations
            ("Contacts (Primary)", "Contacts"),
            ("Units (Main)", "Units"),
            ("Offers <<", "Offers"),
            # Numbered prefixes
            ("1. Contacts", "Contacts"),
            ("2. Units", "Units"),
            ("10. Offers", "Offers"),
            # Bullet prefixes
            ("- Contacts", "Contacts"),
            ("* Units", "Units"),
            # Multiple decorations
            ("[URGENT] Contacts (Primary)", "Contacts"),
            (">> 1. Units <<", "Units"),
            # No decorations
            ("Contacts", "Contacts"),
            ("Plain Name", "Plain Name"),
        ],
    )
    def test_strip_decorations(self, input_name: str, expected: str) -> None:
        """_strip_decorations removes common prefixes/suffixes."""
        result = _strip_decorations(input_name)
        assert result == expected


# --- Test: Word Boundary Matching ---


class TestWordBoundaryMatching:
    """Tests for word boundary pattern matching."""

    def test_compile_word_boundary_pattern(self) -> None:
        """_compile_word_boundary_pattern creates correct regex."""
        pattern = _compile_word_boundary_pattern("contacts")

        # Should match standalone word
        assert pattern.search("Contacts") is not None
        assert pattern.search("My Contacts List") is not None

        # Should NOT match partial words
        assert pattern.search("Recontact") is None

    def test_compile_pattern_cached(self) -> None:
        """Compiled patterns are cached."""
        pattern1 = _compile_word_boundary_pattern("contacts")
        pattern2 = _compile_word_boundary_pattern("contacts")

        # Same object due to caching
        assert pattern1 is pattern2

    @pytest.mark.parametrize(
        ("name", "patterns", "use_word_boundary", "expected_match"),
        [
            # Word boundary matching
            ("Contacts", ("contacts",), True, "contacts"),
            ("My Contacts Here", ("contacts",), True, "contacts"),
            ("CONTACTS", ("contacts",), True, "contacts"),
            # No match with word boundary (false positive prevention)
            ("Community", ("unit",), True, None),
            ("Recontact", ("contact",), True, None),
            ("Prooffer", ("offer",), True, None),
            # Without word boundary (legacy contains matching)
            ("Community", ("unit",), False, "unit"),
            ("Recontact", ("contact",), False, "contact"),
            # Multi-word patterns
            ("Asset Edit", ("asset edit",), True, "asset edit"),
            ("My Asset Edit Task", ("asset edit",), True, "asset edit"),
        ],
    )
    def test_matches_pattern_with_word_boundary(
        self,
        name: str,
        patterns: tuple[str, ...],
        use_word_boundary: bool,
        expected_match: str | None,
    ) -> None:
        """_matches_pattern_with_word_boundary works correctly."""
        result = _matches_pattern_with_word_boundary(name, patterns, use_word_boundary)
        assert result == expected_match


# --- Test: Tier 2 Detection with Word Boundaries ---


class TestTier2DetectionWithWordBoundaries:
    """Tests for Tier 2 detection with word boundary enhancement.

    Per ADR-0117: False positives should be prevented by word boundary matching.
    """

    @pytest.mark.parametrize(
        ("name", "expected_type"),
        [
            # Standard matches
            ("Contacts", EntityType.CONTACT_HOLDER),
            ("Contact", EntityType.CONTACT_HOLDER),
            ("My Contacts List", EntityType.CONTACT_HOLDER),
            ("Units", EntityType.UNIT_HOLDER),
            ("Unit 1", EntityType.UNIT_HOLDER),
            ("Business Units", EntityType.UNIT_HOLDER),
            ("Offers", EntityType.OFFER_HOLDER),
            ("Special Offer", EntityType.OFFER_HOLDER),
            ("Processes", EntityType.PROCESS_HOLDER),
            ("Process", EntityType.PROCESS_HOLDER),
            # With decorations
            ("[URGENT] Contacts", EntityType.CONTACT_HOLDER),
            (">> Units (Primary)", EntityType.UNIT_HOLDER),
            ("1. Offers", EntityType.OFFER_HOLDER),
            # Multi-word patterns
            ("Asset Edit", EntityType.ASSET_EDIT_HOLDER),
            ("Asset Edits", EntityType.ASSET_EDIT_HOLDER),
        ],
    )
    def test_standard_name_patterns_match(self, name: str, expected_type: EntityType) -> None:
        """Name containing pattern at word boundary matches correctly."""
        task = make_task(gid="task1", name=name)

        result = detect_entity_type(task)

        assert result.entity_type == expected_type
        assert result.confidence == CONFIDENCE_TIER_2
        assert result.tier_used == 2
        assert result.needs_healing is True

    @pytest.mark.parametrize(
        "name",
        [
            # Words that contain patterns but shouldn't match
            "Community",  # Contains "unit"
            "Recontact",  # Contains "contact"
            "Prooffer",  # Contains "offer"
            "Subprocess",  # Contains "process"
            "Relocation",  # Contains "location"
            # Random names
            "Random Task",
            "Some Business Task",
            "Meeting Notes",
        ],
    )
    def test_false_positives_avoided(self, name: str) -> None:
        """Words containing patterns as substrings do NOT match."""
        task = make_task(gid="task1", name=name)

        result = detect_entity_type(task)

        # Should fall through to UNKNOWN, not match a holder type
        assert result.entity_type == EntityType.UNKNOWN
        assert result.tier_used == 5

    def test_case_insensitive_matching(self) -> None:
        """Pattern matching is case-insensitive."""
        for name in ["CONTACTS", "Contacts", "contacts", "CoNtAcTs"]:
            task = make_task(gid="task1", name=name)
            result = detect_entity_type(task)
            assert result.entity_type == EntityType.CONTACT_HOLDER

    def test_decorated_names_stripped_and_matched(self) -> None:
        """Decorated names are stripped before matching."""
        # This name has decorations that might interfere
        task = make_task(gid="task1", name="[Priority] Contacts (Main)")

        result = detect_entity_type(task)

        assert result.entity_type == EntityType.CONTACT_HOLDER
        assert result.tier_used == 2
