"""Unit tests for the typed vocabulary-sync contract models.

Covers the three compose-up locks that live in the envelope:
* Lock-2 -- ``field_key: Literal["vertical"]`` + ``extra="forbid"``.
* Lock-3 -- the NAME-key ``vertical_key`` (no gid / vertical_id surface).
And the ``enabled`` observability-only field + additive-only Response accounting.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autom8_asana.contracts.vocabulary_sync import (
    RefusedRow,
    VocabularyOption,
    VocabularySyncRequest,
    VocabularySyncResponse,
)


class TestVocabularyOption:
    """VocabularyOption -- the Lock-3 NAME-keyed leaf."""

    def test_minimal_construction_enabled_defaults_none(self) -> None:
        """vertical_key + name are required; enabled defaults to None."""
        opt = VocabularyOption(vertical_key="dental", name="Dental")
        assert opt.vertical_key == "dental"
        assert opt.name == "Dental"
        assert opt.enabled is None

    def test_enabled_carried_for_observability(self) -> None:
        """enabled rides the envelope when provided (drift-observability)."""
        opt = VocabularyOption(vertical_key="dental", name="Dental", enabled=False)
        assert opt.enabled is False

    def test_no_gid_or_vertical_id_surface(self) -> None:
        """Lock-3: the wire leaf exposes NEITHER enum_option.gid NOR vertical_id."""
        fields = set(VocabularyOption.model_fields)
        assert "gid" not in fields
        assert "vertical_id" not in fields
        assert fields == {"vertical_key", "name", "enabled"}


class TestVocabularySyncRequest:
    """VocabularySyncRequest -- Lock-2 discriminator + extra=forbid."""

    def test_field_key_literal_accepts_vertical(self) -> None:
        """field_key="vertical" is the one accepted discriminator value."""
        req = VocabularySyncRequest(
            field_key="vertical",
            options=[VocabularyOption(vertical_key="dental", name="Dental")],
        )
        assert req.field_key == "vertical"
        assert len(req.options) == 1

    def test_field_key_rejects_other_value(self) -> None:
        """A non-"vertical" discriminator is a validation error (Lock-2)."""
        with pytest.raises(ValidationError):
            VocabularySyncRequest(field_key="offer", options=[])  # type: ignore[arg-type]

    def test_extra_forbid_rejects_unknown_field(self) -> None:
        """extra="forbid" -> unknown fields raise (NFR-003 / BC-1 -> 422)."""
        with pytest.raises(ValidationError):
            VocabularySyncRequest(
                field_key="vertical",
                options=[],
                unexpected="x",  # type: ignore[call-arg]
            )

    def test_empty_options_is_structurally_valid(self) -> None:
        """The MODEL permits an empty option list -- the producer guard, not the
        schema, is what hard-REFUSES an empty read."""
        req = VocabularySyncRequest(field_key="vertical", options=[])
        assert req.options == []

    def test_model_dump_wire_shape(self) -> None:
        """The JSON dump is the exact wire payload the consumer parses."""
        req = VocabularySyncRequest(
            field_key="vertical",
            options=[VocabularyOption(vertical_key="dental", name="Dental", enabled=True)],
        )
        assert req.model_dump(mode="json") == {
            "field_key": "vertical",
            "options": [{"vertical_key": "dental", "name": "Dental", "enabled": True}],
        }


class TestVocabularySyncResponse:
    """VocabularySyncResponse -- additive-only accounting + extra=forbid."""

    def test_construction_with_refused_rows(self) -> None:
        """inserted/updated/refused model the additive-only accounting."""
        resp = VocabularySyncResponse(
            inserted=2,
            updated=1,
            refused=[RefusedRow(vertical_key="dental", reason="name_collision")],
        )
        assert resp.inserted == 2
        assert resp.updated == 1
        assert resp.refused[0].vertical_key == "dental"

    def test_empty_refused_list(self) -> None:
        """A clean sync has an empty refused list."""
        resp = VocabularySyncResponse(inserted=0, updated=0, refused=[])
        assert resp.refused == []

    def test_extra_forbid_rejects_unknown_field(self) -> None:
        """extra="forbid" on the Response too (SDK-atomic-bump discipline)."""
        with pytest.raises(ValidationError):
            VocabularySyncResponse(
                inserted=0,
                updated=0,
                refused=[],
                deleted=3,  # type: ignore[call-arg]  # a DELETE count would be a red flag
            )


class TestRefusedRow:
    """RefusedRow -- the per-row WARN+refuse leaf (FR-007)."""

    def test_construction(self) -> None:
        row = RefusedRow(vertical_key="dental", reason="name_collision")
        assert row.vertical_key == "dental"
        assert row.reason == "name_collision"
