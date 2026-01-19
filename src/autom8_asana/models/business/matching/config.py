"""Configuration for composite matching engine.

Per TDD FR-M-012: 12-factor style configuration via environment variables.
All thresholds configurable via SEEDER_* environment variables.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MatchingConfig(BaseSettings):
    """Configuration for composite matching engine.

    All thresholds configurable via SEEDER_* environment variables.
    Per FR-M-012: 12-factor style configuration.

    Attributes:
        match_threshold: Probability threshold for match decision (0.0-1.0).
        min_fields: Minimum non-null field comparisons required.
        email_weight: Log-odds weight for email match.
        phone_weight: Log-odds weight for phone match.
        name_weight: Log-odds weight for name match.
        domain_weight: Log-odds weight for domain match.
        address_weight: Log-odds weight for address match.
        email_nonmatch: Negative weight for email non-match.
        phone_nonmatch: Negative weight for phone non-match.
        name_nonmatch: Negative weight for name non-match.
        domain_nonmatch: Negative weight for domain non-match.
        address_nonmatch: Negative weight for address non-match.
        fuzzy_exact_threshold: Jaro-Winkler score for full weight.
        fuzzy_high_threshold: Jaro-Winkler score for 75% weight.
        fuzzy_medium_threshold: Jaro-Winkler score for 50% weight.
        tf_enabled: Enable term frequency adjustment.
        tf_common_threshold: Frequency threshold for "common" values.

    Example:
        >>> config = MatchingConfig()  # Uses environment/defaults
        >>> config = MatchingConfig(match_threshold=0.85)  # Override
        >>> config = MatchingConfig.from_env()  # Explicit from environment
    """

    model_config = SettingsConfigDict(
        env_prefix="SEEDER_",
        extra="ignore",
        case_sensitive=False,
    )

    # Thresholds
    match_threshold: float = Field(
        default=0.80,
        description="Match probability threshold",
        ge=0.0,
        le=1.0,
    )
    min_fields: int = Field(
        default=2,
        description="Minimum non-null field comparisons",
        ge=1,
    )

    # Field weights (log-odds scale, positive)
    email_weight: float = Field(default=8.0, description="Email match weight")
    phone_weight: float = Field(default=7.0, description="Phone match weight")
    name_weight: float = Field(default=6.0, description="Name match weight")
    domain_weight: float = Field(default=5.0, description="Domain match weight")
    address_weight: float = Field(default=4.0, description="Address match weight")

    # Non-match weights (negative)
    email_nonmatch: float = Field(default=-4.0, description="Email non-match weight")
    phone_nonmatch: float = Field(default=-4.0, description="Phone non-match weight")
    name_nonmatch: float = Field(default=-3.0, description="Name non-match weight")
    domain_nonmatch: float = Field(default=-2.0, description="Domain non-match weight")
    address_nonmatch: float = Field(
        default=-2.0, description="Address non-match weight"
    )

    # Fuzzy thresholds (Jaro-Winkler similarity)
    fuzzy_exact_threshold: float = Field(
        default=0.95,
        description="Jaro-Winkler threshold for full weight",
        ge=0.0,
        le=1.0,
    )
    fuzzy_high_threshold: float = Field(
        default=0.90,
        description="Jaro-Winkler threshold for 75% weight",
        ge=0.0,
        le=1.0,
    )
    fuzzy_medium_threshold: float = Field(
        default=0.80,
        description="Jaro-Winkler threshold for 50% weight",
        ge=0.0,
        le=1.0,
    )

    # Term frequency adjustment
    tf_enabled: bool = Field(
        default=True,
        description="Enable term frequency adjustment",
    )
    tf_common_threshold: float = Field(
        default=0.01,
        description="Frequency threshold (>1% = common)",
        ge=0.0,
        le=1.0,
    )

    @classmethod
    def from_env(cls) -> MatchingConfig:
        """Create from environment variables.

        Convenience factory method that creates configuration from
        environment variables with SEEDER_ prefix.

        Returns:
            MatchingConfig populated from environment.
        """
        return cls()

    def get_field_weight(self, field_name: str) -> float:
        """Get match weight for a field.

        Args:
            field_name: Field name (email, phone, name, domain, address).

        Returns:
            Positive match weight for the field.
        """
        weight_map = {
            "email": self.email_weight,
            "phone": self.phone_weight,
            "name": self.name_weight,
            "domain": self.domain_weight,
            "address": self.address_weight,
        }
        return weight_map.get(field_name, 0.0)

    def get_nonmatch_weight(self, field_name: str) -> float:
        """Get non-match weight for a field.

        Args:
            field_name: Field name (email, phone, name, domain, address).

        Returns:
            Negative non-match weight for the field.
        """
        weight_map = {
            "email": self.email_nonmatch,
            "phone": self.phone_nonmatch,
            "name": self.name_nonmatch,
            "domain": self.domain_nonmatch,
            "address": self.address_nonmatch,
        }
        return weight_map.get(field_name, 0.0)
