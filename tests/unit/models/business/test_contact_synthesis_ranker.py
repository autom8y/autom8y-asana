"""Tests for ``ContactHolder.ranked_contacts()`` — the pure deterministic ranker.

Per TDD-contact-card-on-play-phase1-2026-07-07 §4 + §12; ADR §6.

The ranker is a pure ordering over ``self.children``: no I/O, no client/SDK imports,
no rendering (ADR §10 AP-F). These tests exercise it with in-memory ``Contact``
entities built directly from custom-field dicts (the same construction idiom as
``test_contact.py``).
"""

from __future__ import annotations

from autom8_asana.models.business.contact import (
    Contact,
    ContactCard,
    ContactHolder,
    Provenance,
)


def _contact(
    *,
    name: str,
    email: str | None = None,
    position: str | None = None,
    nickname: str | None = None,
) -> Contact:
    """Build a ``Contact`` from the custom-field idiom used across the suite."""
    cfs: list[dict] = []
    if email is not None:
        cfs.append({"gid": "e", "name": "Contact Email", "text_value": email})
    if position is not None:
        cfs.append({"gid": "p", "name": "Position", "enum_value": {"name": position}})
    if nickname is not None:
        cfs.append({"gid": "n", "name": "Nickname", "text_value": nickname})
    return Contact(gid=f"c-{name}", name=name, custom_fields=cfs)


def _holder(children: list[Contact]) -> ContactHolder:
    holder = ContactHolder(gid="holder-1", name="X Contacts \U0001f9d1")
    holder._contacts = children  # bypass API population; children is a pure list
    return holder


class TestRankerTierOrdering:
    def test_owner_ranks_above_non_owner(self) -> None:
        owner = _contact(name="Bob Owner", email="bob@x.com", position="Owner")
        staff = _contact(name="Alice Staff", email="alice@x.com", position="Manager")
        cards = _holder([staff, owner]).ranked_contacts()
        assert [c.full_name for c in cards] == ["Bob Owner", "Alice Staff"]
        assert cards[0].rank == 1 and cards[1].rank == 2

    def test_position_weight_orders_non_owners(self) -> None:
        manager = _contact(name="M", email="m@x.com", position="Manager")  # weight 3
        director = _contact(name="D", email="d@x.com", position="Director")  # weight 3
        nobody = _contact(name="Z", email="z@x.com")  # weight 0
        cards = _holder([nobody, manager, director]).ranked_contacts()
        # Manager & Director (weight 3) precede the weight-0 contact; among equal
        # weight, alpha tie-break (D before M).
        assert [c.full_name for c in cards] == ["D", "M", "Z"]

    def test_has_email_breaks_tie_over_emailless(self) -> None:
        emailed = _contact(name="Same Name A", email="a@x.com")
        emailless = _contact(name="Same Name B")
        cards = _holder([emailless, emailed]).ranked_contacts()
        assert cards[0].contact_email == "a@x.com"

    def test_alpha_tiebreak_gives_total_order(self) -> None:
        c1 = _contact(name="Zed", email="z@x.com")
        c2 = _contact(name="Amy", email="a@x.com")
        c3 = _contact(name="Moe", email="m@x.com")
        cards = _holder([c1, c2, c3]).ranked_contacts()
        assert [c.full_name for c in cards] == ["Amy", "Moe", "Zed"]


class TestRankerDeterminism:
    def test_same_input_same_output_across_invocations(self) -> None:
        kids = [
            _contact(name="Zed", email="z@x.com"),
            _contact(name="Bob Owner", position="Owner", email="b@x.com"),
            _contact(name="Amy", email="a@x.com", position="Director"),
        ]
        holder = _holder(kids)
        run1 = [(c.rank, c.full_name) for c in holder.ranked_contacts()]
        run2 = [(c.rank, c.full_name) for c in holder.ranked_contacts()]
        assert run1 == run2  # inter-invocation reliability (ADR §6, P-03)


class TestRankReasonStrings:
    def test_owner_without_position(self) -> None:
        # is_owner is driven by the Position enum; force owner via position="Owner"
        c = _contact(name="O", email="o@x.com", position="Owner")
        card = _holder([c]).ranked_contacts()[0]
        assert card.rank_reason == "owner/Owner"

    def test_non_owner_position(self) -> None:
        c = _contact(name="M", email="m@x.com", position="Manager")
        assert _holder([c]).ranked_contacts()[0].rank_reason == "Manager"

    def test_has_email_reason(self) -> None:
        c = _contact(name="E", email="e@x.com")
        assert _holder([c]).ranked_contacts()[0].rank_reason == "has email on file"

    def test_sole_contact_reason_at_n1(self) -> None:
        # A contact with neither email nor position still gets a non-empty reason
        # (rank_reason is MANDATORY even at n=1; ADR §10 AP-E).
        c = _contact(name="Nobody")
        card = _holder([c]).ranked_contacts()[0]
        assert card.rank_reason == "sole contact on file"
        assert card.rank_reason  # never empty

    def test_every_card_has_nonempty_rank_reason(self) -> None:
        kids = [
            _contact(name="Bob", position="Owner", email="b@x.com"),
            _contact(name="Amy", email="a@x.com"),
            _contact(name="Zed"),
        ]
        for card in _holder(kids).ranked_contacts():
            assert card.rank_reason, f"empty rank_reason on {card.full_name}"


class TestCardShape:
    def test_provenance_always_asana_phase1(self) -> None:
        c = _contact(name="A", email="a@x.com")
        assert _holder([c]).ranked_contacts()[0].provenance is Provenance.ASANA

    def test_nickname_falls_back_to_preferred_name(self) -> None:
        # No explicit nickname -> preferred_name (first name) is used.
        c = _contact(name="Jane Roe", email="j@x.com")
        card = _holder([c]).ranked_contacts()[0]
        assert card.nickname == "Jane"

    def test_explicit_nickname_preferred(self) -> None:
        c = _contact(name="Jane Roe", email="j@x.com", nickname="Janie")
        assert _holder([c]).ranked_contacts()[0].nickname == "Janie"

    def test_returns_contact_card_instances(self) -> None:
        c = _contact(name="A", email="a@x.com")
        cards = _holder([c]).ranked_contacts()
        assert all(isinstance(x, ContactCard) for x in cards)

    def test_empty_holder_returns_empty_list(self) -> None:
        assert _holder([]).ranked_contacts() == []


def test_ranker_has_no_client_or_sdk_imports() -> None:
    """AP-F guard: the entity module must not import clients/SDK/rendering at all.

    TL-C-1 detection: any import of ``stories``, ``data_service``, ``subtasks``, or
    ``html`` in the contact entity module falsifies the F-2 split ruling.
    """
    import autom8_asana.models.business.contact as mod

    src = __import__("inspect").getsource(mod)
    for forbidden in ("import html", "data_service", "subtasks_async", "clients.stories"):
        assert forbidden not in src, f"entity module leaked a forbidden import: {forbidden}"
