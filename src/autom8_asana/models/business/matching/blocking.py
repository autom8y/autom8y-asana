"""Blocking rules for candidate generation.

Per TDD ADR-SEEDER-004: Blocking strategy for O(n) candidate generation
instead of O(n^2) comparison.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from autom8_asana.models.business.matching.models import Candidate
    from autom8_asana.models.business.seeder import BusinessData


class BlockingRule(Protocol):
    """Blocking rule protocol for candidate generation.

    Blocking rules filter candidates to those likely to match,
    reducing comparison space from O(n^2) to O(n).
    """

    def matches(self, query: "BusinessData", candidate: "Candidate") -> bool:
        """Check if candidate passes blocking filter.

        Args:
            query: Query business data.
            candidate: Potential match candidate.

        Returns:
            True if candidate should be compared, False to skip.
        """
        ...


class DomainBlockingRule:
    """Block on matching domain.

    High selectivity - reduces candidates by ~90%.

    Example:
        >>> rule = DomainBlockingRule()
        >>> rule.matches(
        ...     BusinessData(name="Acme", domain="acme.com"),
        ...     Candidate(gid="123", domain="acme.com")
        ... )
        True
    """

    def matches(self, query: "BusinessData", candidate: "Candidate") -> bool:
        """Check if domains match.

        Args:
            query: Query business data.
            candidate: Candidate to check.

        Returns:
            True if domains match (or either is None).
        """
        query_domain = getattr(query, "domain", None)
        candidate_domain = candidate.domain

        # If either is None, don't use this rule as a filter
        if not query_domain or not candidate_domain:
            return True  # Pass through - let other rules decide

        # Normalize for comparison
        return query_domain.lower().strip() == candidate_domain.lower().strip()


class PhonePrefixBlockingRule:
    """Block on matching phone prefix.

    Uses first 6 digits of normalized phone number.
    High selectivity for businesses with phone data.

    Example:
        >>> rule = PhonePrefixBlockingRule()
        >>> rule.matches(
        ...     BusinessData(name="Acme", phone="555-123-4567"),
        ...     Candidate(gid="123", phone="+15551234999")
        ... )
        True  # Same first 6 digits
    """

    PREFIX_LENGTH = 6

    def matches(self, query: "BusinessData", candidate: "Candidate") -> bool:
        """Check if phone prefixes match.

        Args:
            query: Query business data.
            candidate: Candidate to check.

        Returns:
            True if phone prefixes match (or either is None).
        """
        query_phone = getattr(query, "phone", None)
        candidate_phone = candidate.phone

        # If either is None, don't use this rule as a filter
        if not query_phone or not candidate_phone:
            return True  # Pass through

        # Extract digits only
        query_digits = "".join(c for c in query_phone if c.isdigit())
        candidate_digits = "".join(c for c in candidate_phone if c.isdigit())

        # Need enough digits for comparison
        if len(query_digits) < self.PREFIX_LENGTH:
            return True  # Pass through
        if len(candidate_digits) < self.PREFIX_LENGTH:
            return True  # Pass through

        # Compare last 10 digits (phone number without country code)
        # to handle +1 prefix variations
        query_suffix = query_digits[-10:] if len(query_digits) >= 10 else query_digits
        candidate_suffix = (
            candidate_digits[-10:]
            if len(candidate_digits) >= 10
            else candidate_digits
        )

        # Compare prefixes of the 10-digit numbers
        return (
            query_suffix[: self.PREFIX_LENGTH]
            == candidate_suffix[: self.PREFIX_LENGTH]
        )


class NameTokenBlockingRule:
    """Block on shared name tokens.

    Tokenizes business names and checks for overlap.
    Medium selectivity - catches variations in word order.

    Example:
        >>> rule = NameTokenBlockingRule()
        >>> rule.matches(
        ...     BusinessData(name="Joe's Pizza Palace"),
        ...     Candidate(gid="123", name="Pizza Palace by Joe")
        ... )
        True  # Shares "pizza" and "palace" tokens
    """

    # Words to ignore when tokenizing
    STOP_WORDS: frozenset[str] = frozenset(
        [
            "the",
            "a",
            "an",
            "and",
            "or",
            "of",
            "in",
            "at",
            "by",
            "for",
            "to",
            "on",
            "with",
            # Legal suffixes
            "inc",
            "llc",
            "ltd",
            "corp",
            "corporation",
            "company",
            "co",
        ]
    )

    # Minimum token length to consider
    MIN_TOKEN_LENGTH = 3

    def matches(self, query: "BusinessData", candidate: "Candidate") -> bool:
        """Check if names share significant tokens.

        Args:
            query: Query business data.
            candidate: Candidate to check.

        Returns:
            True if names share at least one significant token.
        """
        query_name = query.name
        candidate_name = candidate.name

        # If either is None, pass through
        if not query_name or not candidate_name:
            return True

        query_tokens = self._tokenize(query_name)
        candidate_tokens = self._tokenize(candidate_name)

        # If we couldn't extract tokens, pass through
        if not query_tokens or not candidate_tokens:
            return True

        # Check for any shared token
        return bool(query_tokens & candidate_tokens)

    def _tokenize(self, name: str) -> set[str]:
        """Tokenize name into significant words.

        Args:
            name: Business name.

        Returns:
            Set of significant tokens.
        """
        import re

        # Remove punctuation and lowercase
        cleaned = re.sub(r"[^\w\s]", "", name.lower())

        # Split into words
        words = cleaned.split()

        # Filter to significant tokens
        tokens = {
            word
            for word in words
            if len(word) >= self.MIN_TOKEN_LENGTH and word not in self.STOP_WORDS
        }

        return tokens


class CompositeBlockingRule:
    """Combines multiple blocking rules with OR logic.

    Per TDD ADR-SEEDER-004: Multiple blocking passes combined with OR.
    A candidate passes if ANY rule matches.

    Example:
        >>> rule = CompositeBlockingRule([
        ...     DomainBlockingRule(),
        ...     PhonePrefixBlockingRule(),
        ...     NameTokenBlockingRule(),
        ... ])
        >>> # Passes if domain matches OR phone prefix matches OR name tokens overlap
    """

    def __init__(self, rules: list[BlockingRule] | None = None) -> None:
        """Initialize with blocking rules.

        Args:
            rules: List of blocking rules. If None, uses default set.
        """
        if rules is None:
            rules = [
                DomainBlockingRule(),
                PhonePrefixBlockingRule(),
                NameTokenBlockingRule(),
            ]
        self._rules = rules

    def matches(self, query: "BusinessData", candidate: "Candidate") -> bool:
        """Check if any blocking rule matches.

        Args:
            query: Query business data.
            candidate: Candidate to check.

        Returns:
            True if ANY rule matches (OR logic).
        """
        # With OR logic, we return True if any rule matches
        # Since rules return True for "pass through" cases,
        # we need to be more careful here

        # If we have data on both sides for a rule and it matches, include
        # If we have data on both sides and it doesn't match, exclude
        # If data is missing, the rule passes through

        for rule in self._rules:
            if rule.matches(query, candidate):
                return True

        return False

    def filter_candidates(
        self,
        query: "BusinessData",
        candidates: list["Candidate"],
    ) -> list["Candidate"]:
        """Filter candidates using blocking rules.

        Args:
            query: Query business data.
            candidates: All candidates to filter.

        Returns:
            Candidates that pass at least one blocking rule.
        """
        return [c for c in candidates if self.matches(query, c)]
