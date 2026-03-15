"""Tests for FieldResolver per TDD-ENTITY-WRITE-API Section 16.2.

18 tests covering:
- Core field resolution
- Descriptor name resolution
- Display name resolution (case-insensitive)
- Unknown field with fuzzy suggestions
- Enum by name, by GID passthrough, unknown enum value
- Multi-enum replace mode and append mode
- Text append (empty, dedup, list input)
- Date wrapping
- Null clears field
- Type validation (number rejects string, text rejects number)
- Mixed core + custom fields
"""

from __future__ import annotations

import pytest

from autom8_asana.resolution.field_resolver import FieldResolver

# ---------------------------------------------------------------------------
# Fixtures: shared custom field data mimicking Asana task response
# ---------------------------------------------------------------------------

CORE_FIELDS = frozenset({"name", "assignee", "due_on", "completed", "notes"})


def _make_custom_fields() -> list[dict]:
    """Build a representative set of custom field dicts.

    Mimics the shape returned by Asana GET /tasks/{gid} with opt_fields
    including custom_fields, enum_options, text_value, multi_enum_values.
    """
    return [
        {
            "gid": "CF_001",
            "name": "Weekly Ad Spend",
            "resource_subtype": "number",
            "number_value": 250,
        },
        {
            "gid": "CF_002",
            "name": "Status",
            "resource_subtype": "enum",
            "enum_options": [
                {"gid": "OPT_ACTIVE", "name": "Active", "enabled": True},
                {"gid": "OPT_PAUSED", "name": "Paused", "enabled": True},
                {"gid": "OPT_CLOSED", "name": "Closed", "enabled": False},
            ],
            "enum_value": {"gid": "OPT_ACTIVE", "name": "Active"},
        },
        {
            "gid": "CF_003",
            "name": "Platforms",
            "resource_subtype": "multi_enum",
            "enum_options": [
                {"gid": "OPT_FB", "name": "Facebook", "enabled": True},
                {"gid": "OPT_GOOG", "name": "Google", "enabled": True},
                {"gid": "OPT_TIKTOK", "name": "TikTok", "enabled": True},
            ],
            "multi_enum_values": [
                {"gid": "OPT_FB", "name": "Facebook"},
            ],
        },
        {
            "gid": "CF_004",
            "name": "Asset ID",
            "resource_subtype": "text",
            "text_value": "asset-123,asset-456",
        },
        {
            "gid": "CF_005",
            "name": "Launch Date",
            "resource_subtype": "date",
        },
        {
            "gid": "CF_006",
            "name": "Notes Field",
            "resource_subtype": "text",
            "text_value": "",
        },
        {
            "gid": "CF_007",
            "name": "MRR",
            "resource_subtype": "number",
            "number_value": None,
        },
    ]


def _make_descriptor_index() -> dict[str, str]:
    """Descriptor index: snake_case -> Asana display name."""
    return {
        "weekly_ad_spend": "Weekly Ad Spend",
        "status": "Status",
        "platforms": "Platforms",
        "asset_id": "Asset ID",
        "launch_date": "Launch Date",
        "mrr": "MRR",
    }


@pytest.fixture
def custom_fields() -> list[dict]:
    return _make_custom_fields()


@pytest.fixture
def descriptor_index() -> dict[str, str]:
    return _make_descriptor_index()


@pytest.fixture
def resolver(custom_fields, descriptor_index) -> FieldResolver:
    return FieldResolver(
        custom_fields_data=custom_fields,
        descriptor_index=descriptor_index,
        core_fields=CORE_FIELDS,
    )


# ---------------------------------------------------------------------------
# 1. Core field resolution
# ---------------------------------------------------------------------------


class TestCoreFieldResolution:
    """test_resolve_core_field_name: 'name' resolves as core with is_core=True."""

    def test_resolve_core_field_name(self, resolver: FieldResolver) -> None:
        results = resolver.resolve_fields({"name": "Updated Offer"})
        assert len(results) == 1
        rf = results[0]
        assert rf.input_name == "name"
        assert rf.matched_name == "name"
        assert rf.is_core is True
        assert rf.value == "Updated Offer"
        assert rf.status == "resolved"
        assert rf.gid is None


# ---------------------------------------------------------------------------
# 2. Descriptor name resolution
# ---------------------------------------------------------------------------


class TestDescriptorNameResolution:
    """test_resolve_descriptor_name: 'weekly_ad_spend' resolves via descriptor_index."""

    def test_resolve_descriptor_name(self, resolver: FieldResolver) -> None:
        results = resolver.resolve_fields({"weekly_ad_spend": 500})
        assert len(results) == 1
        rf = results[0]
        assert rf.input_name == "weekly_ad_spend"
        assert rf.matched_name == "Weekly Ad Spend"
        assert rf.gid == "CF_001"
        assert rf.value == 500
        assert rf.is_core is False
        assert rf.status == "resolved"


# ---------------------------------------------------------------------------
# 3-4. Display name resolution (exact + case-insensitive)
# ---------------------------------------------------------------------------


class TestDisplayNameResolution:
    """test_resolve_display_name + case-insensitive variant."""

    def test_resolve_display_name(self, resolver: FieldResolver) -> None:
        """Exact display name 'Weekly Ad Spend' resolves via display_index."""
        results = resolver.resolve_fields({"Weekly Ad Spend": 750})
        assert len(results) == 1
        rf = results[0]
        assert rf.matched_name == "Weekly Ad Spend"
        assert rf.gid == "CF_001"
        assert rf.value == 750
        assert rf.status == "resolved"

    def test_resolve_display_name_case_insensitive(
        self, resolver: FieldResolver
    ) -> None:
        """'weekly ad spend' (all lowercase) resolves via case-insensitive scan."""
        results = resolver.resolve_fields({"weekly ad spend": 800})
        assert len(results) == 1
        rf = results[0]
        assert rf.matched_name == "Weekly Ad Spend"
        assert rf.gid == "CF_001"
        assert rf.value == 800
        assert rf.status == "resolved"


# ---------------------------------------------------------------------------
# 5. Unknown field with fuzzy suggestions
# ---------------------------------------------------------------------------


class TestUnknownFieldFuzzy:
    """test_resolve_unknown_field_fuzzy: unrecognized field -> skipped + suggestions."""

    def test_resolve_unknown_field_fuzzy(self, resolver: FieldResolver) -> None:
        results = resolver.resolve_fields({"Weekly Ad Sped": 100})
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "skipped"
        assert rf.error is not None
        assert "not found" in rf.error
        # difflib should suggest "Weekly Ad Spend" as a close match
        assert rf.suggestions is not None
        assert "Weekly Ad Spend" in rf.suggestions


# ---------------------------------------------------------------------------
# 6-8. Enum resolution
# ---------------------------------------------------------------------------


class TestEnumResolution:
    """Enum by name, GID passthrough, and unknown value."""

    def test_resolve_enum_by_name(self, resolver: FieldResolver) -> None:
        """'Active' string resolves to option GID 'OPT_ACTIVE'."""
        results = resolver.resolve_fields({"status": "Active"})
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "resolved"
        assert rf.value == "OPT_ACTIVE"
        assert rf.gid == "CF_002"

    def test_resolve_enum_by_gid_passthrough(self, resolver: FieldResolver) -> None:
        """Numeric GID string 'OPT_ACTIVE' passes through when it matches a known GID."""
        # The GID passthrough works for numeric-looking GIDs.
        # Since our test GIDs are not numeric, test with a numeric option GID.
        custom_fields = [
            {
                "gid": "CF_ENUM",
                "name": "Priority",
                "resource_subtype": "enum",
                "enum_options": [
                    {"gid": "111222333", "name": "High", "enabled": True},
                    {"gid": "444555666", "name": "Low", "enabled": True},
                ],
            },
        ]
        r = FieldResolver(
            custom_fields_data=custom_fields,
            descriptor_index={"priority": "Priority"},
            core_fields=CORE_FIELDS,
        )
        results = r.resolve_fields({"priority": "111222333"})
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "resolved"
        assert rf.value == "111222333"

    def test_resolve_enum_unknown_value(self, resolver: FieldResolver) -> None:
        """Unknown enum value -> skipped with available options as suggestions."""
        results = resolver.resolve_fields({"status": "Nonexistent"})
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "skipped"
        assert rf.error is not None
        assert "not found" in rf.error.lower()
        # Suggestions should list available enum options (enabled only)
        assert rf.suggestions is not None
        assert "Active" in rf.suggestions
        assert "Paused" in rf.suggestions


# ---------------------------------------------------------------------------
# 9-10. Multi-enum resolution
# ---------------------------------------------------------------------------


class TestMultiEnumResolution:
    """Multi-enum replace mode and append mode."""

    def test_resolve_multi_enum_replace(self, resolver: FieldResolver) -> None:
        """Replace mode: list of names resolves to list of GIDs."""
        results = resolver.resolve_fields(
            {"platforms": ["Facebook", "Google"]}, list_mode="replace"
        )
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "resolved"
        assert rf.gid == "CF_003"
        assert set(rf.value) == {"OPT_FB", "OPT_GOOG"}

    def test_resolve_multi_enum_append(self, resolver: FieldResolver) -> None:
        """Append mode: merges with existing multi_enum_values."""
        # Existing: [Facebook (OPT_FB)]. Appending: [Google, Facebook].
        # Result should be: [OPT_FB, OPT_GOOG] (deduped, FB not duplicated).
        results = resolver.resolve_fields(
            {"platforms": ["Google", "Facebook"]}, list_mode="append"
        )
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "resolved"
        # Existing OPT_FB first, then newly added OPT_GOOG
        assert rf.value == ["OPT_FB", "OPT_GOOG"]

    def test_resolve_multi_enum_all_unresolved_skipped(
        self, resolver: FieldResolver
    ) -> None:
        """All values unresolved -> skipped with error and suggestions.

        Per WS-4 hardening: prevents silent field-clear when all option names
        mismatch (the independent T3 failure mode).
        """
        results = resolver.resolve_fields(
            {"platforms": ["Nonexistent1", "Nonexistent2"]}, list_mode="replace"
        )
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "skipped"
        assert rf.error is not None
        assert "No multi-enum values resolved" in rf.error
        assert "Nonexistent1" in rf.error
        assert "Nonexistent2" in rf.error
        # Suggestions list available enabled options
        assert rf.suggestions is not None
        assert "Facebook" in rf.suggestions
        assert "Google" in rf.suggestions
        assert "TikTok" in rf.suggestions

    def test_resolve_multi_enum_partial_unresolved_writes_resolved(
        self, resolver: FieldResolver
    ) -> None:
        """Some values unresolved -> resolved with only matched GIDs.

        When at least one option matches, the field is written with the
        matched values. Unresolved values are logged but do not block
        the write of matched values.
        """
        results = resolver.resolve_fields(
            {"platforms": ["Facebook", "Nonexistent"]}, list_mode="replace"
        )
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "resolved"
        assert rf.value == ["OPT_FB"]
        # Partial success -- one matched, one dropped

    def test_resolve_multi_enum_single_string_all_unresolved(
        self, resolver: FieldResolver
    ) -> None:
        """Single string value (not list) that fails resolution -> skipped."""
        results = resolver.resolve_fields(
            {"platforms": "NotARealPlatform"}, list_mode="replace"
        )
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "skipped"
        assert rf.error is not None
        assert "No multi-enum values resolved" in rf.error


# ---------------------------------------------------------------------------
# 11-13. Text append
# ---------------------------------------------------------------------------


class TestTextAppend:
    """Text append: new on empty, dedup, list input."""

    def test_resolve_text_append_new(self, resolver: FieldResolver) -> None:
        """Append on empty text field sets the new value."""
        # "Notes Field" (CF_006) has text_value=""
        results = resolver.resolve_fields(
            {"Notes Field": "first-item"}, list_mode="append"
        )
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "resolved"
        assert rf.value == "first-item"

    def test_resolve_text_append_dedup(self, resolver: FieldResolver) -> None:
        """Append deduplicates values already present in text_value."""
        # "Asset ID" (CF_004) has text_value="asset-123,asset-456"
        results = resolver.resolve_fields({"asset_id": "asset-123"}, list_mode="append")
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "resolved"
        # asset-123 already exists, should not be duplicated
        assert rf.value == "asset-123,asset-456"

    def test_resolve_text_append_list_input(self, resolver: FieldResolver) -> None:
        """Append accepts a list of strings."""
        # "Asset ID" (CF_004) has text_value="asset-123,asset-456"
        results = resolver.resolve_fields(
            {"asset_id": ["asset-789", "asset-123"]}, list_mode="append"
        )
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "resolved"
        # asset-123 already exists, asset-789 is new
        assert rf.value == "asset-123,asset-456,asset-789"


# ---------------------------------------------------------------------------
# 14. Date wrapping
# ---------------------------------------------------------------------------


class TestDateWrapping:
    """test_resolve_date_wrapping: date string wrapped in {"date": "..."}."""

    def test_resolve_date_wrapping(self, resolver: FieldResolver) -> None:
        results = resolver.resolve_fields({"launch_date": "2026-03-15"})
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "resolved"
        assert rf.value == {"date": "2026-03-15"}
        assert rf.gid == "CF_005"


# ---------------------------------------------------------------------------
# 15. Null clears field
# ---------------------------------------------------------------------------


class TestNullClears:
    """test_resolve_null_clears_field: None passes through as None."""

    def test_resolve_null_clears_field(self, resolver: FieldResolver) -> None:
        results = resolver.resolve_fields({"weekly_ad_spend": None})
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "resolved"
        assert rf.value is None
        assert rf.gid == "CF_001"
        assert rf.matched_name == "Weekly Ad Spend"


# ---------------------------------------------------------------------------
# 16-17. Type validation
# ---------------------------------------------------------------------------


class TestTypeValidation:
    """Type validation: number rejects string, text rejects number."""

    def test_type_validation_number_rejects_string(
        self, resolver: FieldResolver
    ) -> None:
        """Number field with string value returns type error."""
        results = resolver.resolve_fields({"weekly_ad_spend": "not-a-number"})
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "error"
        assert rf.error is not None
        assert "number" in rf.error.lower()

    def test_type_validation_text_rejects_number(self, resolver: FieldResolver) -> None:
        """Text field with raw number returns type error."""
        results = resolver.resolve_fields({"Asset ID": 12345})
        assert len(results) == 1
        rf = results[0]
        assert rf.status == "error"
        assert rf.error is not None
        assert "text" in rf.error.lower()


# ---------------------------------------------------------------------------
# 18. Mixed core + custom fields
# ---------------------------------------------------------------------------


class TestMixedFields:
    """test_mixed_core_and_custom: request with both types resolves correctly."""

    def test_mixed_core_and_custom(self, resolver: FieldResolver) -> None:
        fields = {
            "name": "New Offer",
            "weekly_ad_spend": 999,
            "Status": "Paused",
            "due_on": "2026-04-01",
        }
        results = resolver.resolve_fields(fields)
        assert len(results) == 4

        by_name = {rf.input_name: rf for rf in results}

        # Core: name
        rf_name = by_name["name"]
        assert rf_name.is_core is True
        assert rf_name.value == "New Offer"
        assert rf_name.status == "resolved"

        # Custom via descriptor: weekly_ad_spend
        rf_spend = by_name["weekly_ad_spend"]
        assert rf_spend.is_core is False
        assert rf_spend.value == 999
        assert rf_spend.gid == "CF_001"
        assert rf_spend.status == "resolved"

        # Custom via display name: Status
        rf_status = by_name["Status"]
        assert rf_status.is_core is False
        assert rf_status.value == "OPT_PAUSED"
        assert rf_status.gid == "CF_002"
        assert rf_status.status == "resolved"

        # Core: due_on
        rf_due = by_name["due_on"]
        assert rf_due.is_core is True
        assert rf_due.value == "2026-04-01"
        assert rf_due.status == "resolved"
