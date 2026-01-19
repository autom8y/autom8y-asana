"""Unit tests for blocking rules.

Per TDD-BusinessSeeder-v2 ADR-SEEDER-004: Tests for blocking rules.
"""

from __future__ import annotations

from autom8_asana.models.business.matching.blocking import (
    CompositeBlockingRule,
    DomainBlockingRule,
    NameTokenBlockingRule,
    PhonePrefixBlockingRule,
)
from autom8_asana.models.business.matching.models import Candidate
from autom8_asana.models.business.seeder import BusinessData


class TestDomainBlockingRule:
    """Tests for DomainBlockingRule."""

    def test_same_domain_matches(self) -> None:
        """Same domain passes blocking."""
        rule = DomainBlockingRule()
        query = BusinessData(name="Acme Corp", domain="acme.com")
        candidate = Candidate(gid="123", name="Acme Inc", domain="acme.com")

        assert rule.matches(query, candidate) is True

    def test_different_domain_blocks(self) -> None:
        """Different domain blocks."""
        rule = DomainBlockingRule()
        query = BusinessData(name="Acme Corp", domain="acme.com")
        candidate = Candidate(gid="123", name="Other Co", domain="other.com")

        assert rule.matches(query, candidate) is False

    def test_null_query_domain_passes(self) -> None:
        """Null query domain passes through."""
        rule = DomainBlockingRule()
        query = BusinessData(name="Acme Corp")  # No domain
        candidate = Candidate(gid="123", domain="acme.com")

        assert rule.matches(query, candidate) is True

    def test_null_candidate_domain_passes(self) -> None:
        """Null candidate domain passes through."""
        rule = DomainBlockingRule()
        query = BusinessData(name="Acme Corp", domain="acme.com")
        candidate = Candidate(gid="123")  # No domain

        assert rule.matches(query, candidate) is True

    def test_case_insensitive(self) -> None:
        """Domain matching is case-insensitive."""
        rule = DomainBlockingRule()
        query = BusinessData(name="Acme", domain="ACME.COM")
        candidate = Candidate(gid="123", domain="acme.com")

        assert rule.matches(query, candidate) is True


class TestPhonePrefixBlockingRule:
    """Tests for PhonePrefixBlockingRule."""

    def test_same_prefix_matches(self) -> None:
        """Same phone prefix passes blocking."""
        rule = PhonePrefixBlockingRule()
        query = BusinessData(name="Acme", phone="+15551234567")
        candidate = Candidate(gid="123", phone="+15551234999")

        assert rule.matches(query, candidate) is True

    def test_different_prefix_blocks(self) -> None:
        """Different phone prefix blocks."""
        rule = PhonePrefixBlockingRule()
        query = BusinessData(name="Acme", phone="+15551234567")
        candidate = Candidate(gid="123", phone="+19991234567")

        assert rule.matches(query, candidate) is False

    def test_null_query_phone_passes(self) -> None:
        """Null query phone passes through."""
        rule = PhonePrefixBlockingRule()
        query = BusinessData(name="Acme")  # No phone
        candidate = Candidate(gid="123", phone="+15551234567")

        assert rule.matches(query, candidate) is True

    def test_null_candidate_phone_passes(self) -> None:
        """Null candidate phone passes through."""
        rule = PhonePrefixBlockingRule()
        query = BusinessData(name="Acme", phone="+15551234567")
        candidate = Candidate(gid="123")  # No phone

        assert rule.matches(query, candidate) is True

    def test_handles_different_formats(self) -> None:
        """Handles different phone formats."""
        rule = PhonePrefixBlockingRule()
        query = BusinessData(name="Acme", phone="(555) 123-4567")
        candidate = Candidate(gid="123", phone="+1 555 123 9999")

        assert rule.matches(query, candidate) is True


class TestNameTokenBlockingRule:
    """Tests for NameTokenBlockingRule."""

    def test_shared_token_matches(self) -> None:
        """Shared name token passes blocking."""
        rule = NameTokenBlockingRule()
        query = BusinessData(name="Joe's Pizza Palace")
        candidate = Candidate(gid="123", name="Pizza Palace by Joe")

        assert rule.matches(query, candidate) is True

    def test_no_shared_tokens_blocks(self) -> None:
        """No shared tokens blocks."""
        rule = NameTokenBlockingRule()
        query = BusinessData(name="Acme Corporation")
        candidate = Candidate(gid="123", name="Widget Factory")

        assert rule.matches(query, candidate) is False

    def test_stop_words_ignored(self) -> None:
        """Stop words are ignored in token matching."""
        rule = NameTokenBlockingRule()
        query = BusinessData(name="The Acme Company Inc")
        candidate = Candidate(gid="123", name="The Widget Corporation")

        # Only shared tokens are "the" and stop words - should block
        assert rule.matches(query, candidate) is False

    def test_null_query_name_passes(self) -> None:
        """Null query name passes through."""
        rule = NameTokenBlockingRule()
        query = BusinessData(name="")  # Empty name
        candidate = Candidate(gid="123", name="Acme Corp")

        assert rule.matches(query, candidate) is True

    def test_null_candidate_name_passes(self) -> None:
        """Null candidate name passes through."""
        rule = NameTokenBlockingRule()
        query = BusinessData(name="Acme Corp")
        candidate = Candidate(gid="123")  # No name

        assert rule.matches(query, candidate) is True

    def test_short_tokens_ignored(self) -> None:
        """Short tokens (< 3 chars) are ignored."""
        rule = NameTokenBlockingRule()
        query = BusinessData(name="AI ML Lab")
        candidate = Candidate(gid="123", name="AI ML Lab Different")

        # "AI" and "ML" are too short (2 chars), "lab" should match
        assert rule.matches(query, candidate) is True


class TestCompositeBlockingRule:
    """Tests for CompositeBlockingRule."""

    def test_any_rule_matches_passes(self) -> None:
        """Passes if any rule matches (OR logic)."""
        rule = CompositeBlockingRule()
        query = BusinessData(
            name="Acme Corp",
            phone="+15551234567",  # Matches phone
        )
        candidate = Candidate(
            gid="123",
            name="Different Business",  # Name doesn't match
            phone="+15551234999",  # Phone prefix matches
            domain="other.com",  # Domain doesn't match
        )

        assert rule.matches(query, candidate) is True

    def test_no_rules_match_blocks(self) -> None:
        """Blocks if no rules match."""
        rule = CompositeBlockingRule()
        query = BusinessData(name="Acme Corp", phone="+15551234567", domain="acme.com")
        candidate = Candidate(
            gid="123",
            name="Completely Different",
            phone="+19999999999",
            domain="other.com",
        )

        assert rule.matches(query, candidate) is False

    def test_filter_candidates(self) -> None:
        """filter_candidates filters correctly."""
        rule = CompositeBlockingRule()
        query = BusinessData(
            name="Joe's Pizza", domain="joespizza.com", phone="+15551234567"
        )

        candidates = [
            # Shares "pizza" token with query
            Candidate(
                gid="1",
                name="Pizza Palace",
                domain="pizzapalace.com",
                phone="+19999999999",  # Different phone
            ),
            # Shares domain with query
            Candidate(
                gid="2",
                name="Joe's Restaurant",
                domain="joespizza.com",
                phone="+18888888888",  # Different phone
            ),
            # No matches - different name tokens, domain, phone
            Candidate(
                gid="3",
                name="Taco Bell",
                domain="tacobell.com",
                phone="+17777777777",  # Different phone
            ),
        ]

        filtered = rule.filter_candidates(query, candidates)

        # Candidate 1: shares "pizza" token
        # Candidate 2: shares domain
        # Candidate 3: no matches (completely different)
        assert len(filtered) == 2
        assert any(c.gid == "1" for c in filtered)  # Shares "pizza"
        assert any(c.gid == "2" for c in filtered)  # Shares domain
        assert not any(c.gid == "3" for c in filtered)  # No matches

    def test_custom_rules(self) -> None:
        """Custom rules are used."""
        # Only use domain rule
        rule = CompositeBlockingRule(rules=[DomainBlockingRule()])
        query = BusinessData(name="Acme", domain="acme.com")

        candidate_match = Candidate(gid="1", name="Different", domain="acme.com")
        candidate_no_match = Candidate(gid="2", name="Acme Corp", domain="other.com")

        assert rule.matches(query, candidate_match) is True
        assert rule.matches(query, candidate_no_match) is False
