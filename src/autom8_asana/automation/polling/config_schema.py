"""Configuration schema models for polling-based automation rules.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Pydantic v2 models for YAML configuration
validation with strict mode (extra="forbid").

Schema ownership: Devs own schema (this file), Ops own values (YAML files).

Example YAML structure:
    scheduler:
      time: "02:00"
      timezone: "UTC"
    rules:
      - rule_id: "escalate-triage"
        name: "Escalate stale triage tasks"
        project_gid: "1234567890123"
        conditions:
          - stale:
              field: "Section"
              days: 3
        action:
          type: "add_tag"
          params:
            tag: "escalate"
        enabled: true
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

__all__ = [
    "TriggerStaleConfig",
    "TriggerDeadlineConfig",
    "TriggerAgeConfig",
    "RuleCondition",
    "ActionConfig",
    "Rule",
    "SchedulerConfig",
    "AutomationRulesConfig",
]


class TriggerStaleConfig(BaseModel):
    """Stale detection trigger configuration.

    Monitors a field for tasks that haven't been modified in N days.

    Attributes:
        field: Field name or GID to monitor (e.g., "Section").
        days: Number of days threshold. Task is stale if modified_at >= N days ago.
            Must be >= 1.

    Example:
        stale:
          field: "Section"
          days: 3  # Task is stale if not modified in 3+ days
    """

    model_config = ConfigDict(extra="forbid")

    field: str
    days: int

    @field_validator("days")
    @classmethod
    def days_must_be_positive(cls, v: int) -> int:
        """Validate that days is at least 1."""
        if v < 1:
            raise ValueError("days must be >= 1")
        return v


class TriggerDeadlineConfig(BaseModel):
    """Deadline proximity trigger configuration.

    Matches tasks with due dates within N days from today.

    Attributes:
        days: Number of days from today. Task matches if due_date <= today + N days.
            Must be >= 1.

    Example:
        deadline:
          days: 7  # Task due within next 7 days
    """

    model_config = ConfigDict(extra="forbid")

    days: int

    @field_validator("days")
    @classmethod
    def days_must_be_positive(cls, v: int) -> int:
        """Validate that days is at least 1."""
        if v < 1:
            raise ValueError("days must be >= 1")
        return v


class TriggerAgeConfig(BaseModel):
    """Age since creation trigger configuration.

    Matches tasks created N+ days ago that are still open (not completed).

    Attributes:
        days: Number of days since creation. Task matches if created >= N days ago
            and is still open. Must be >= 1.

    Example:
        age:
          days: 90  # Task created 90+ days ago and still open
    """

    model_config = ConfigDict(extra="forbid")

    days: int

    @field_validator("days")
    @classmethod
    def days_must_be_positive(cls, v: int) -> int:
        """Validate that days is at least 1."""
        if v < 1:
            raise ValueError("days must be >= 1")
        return v


class RuleCondition(BaseModel):
    """A single condition in a rule (supports AND composition).

    At least one trigger type (stale, deadline, or age) must be specified.
    Multiple conditions in a rule are combined with AND logic.

    Attributes:
        stale: Optional stale detection trigger.
        deadline: Optional deadline proximity trigger.
        age: Optional age since creation trigger.
        field_whitelist: Optional list of custom field GIDs to monitor.
            When specified, only trigger on changes to these fields.
            When None or empty, trigger on any field changes.

    Example:
        conditions:
          - stale:
              field: "Section"
              days: 3
            field_whitelist:
              - "custom_gid_abc123"
    """

    model_config = ConfigDict(extra="forbid")

    stale: TriggerStaleConfig | None = None
    deadline: TriggerDeadlineConfig | None = None
    age: TriggerAgeConfig | None = None
    field_whitelist: list[str] | None = None

    @model_validator(mode="after")
    def at_least_one_trigger_required(self) -> "RuleCondition":
        """Validate that at least one trigger type is specified."""
        if self.stale is None and self.deadline is None and self.age is None:
            raise ValueError(
                "At least one trigger type (stale, deadline, or age) is required"
            )
        return self


class ActionConfig(BaseModel):
    """Action to execute when a rule matches.

    Attributes:
        type: Action type identifier (e.g., "add_tag", "add_comment", "change_section").
        params: Action-specific parameters as key-value pairs.

    Example:
        action:
          type: "add_tag"
          params:
            tag: "escalate"
    """

    model_config = ConfigDict(extra="forbid")

    type: str
    params: dict[str, Any]


class Rule(BaseModel):
    """A single automation rule definition.

    Attributes:
        rule_id: Unique identifier for this rule. Must be non-empty.
        name: Human-readable name for display and logging.
        project_gid: Asana project GID to evaluate this rule against.
        conditions: List of conditions (combined with AND logic).
        action: Action to execute when all conditions match.
        enabled: Whether this rule is active (default: True).

    Example:
        - rule_id: "escalate-triage"
          name: "Escalate stale triage tasks"
          project_gid: "1234567890123"
          conditions:
            - stale:
                field: "Section"
                days: 3
          action:
            type: "add_tag"
            params:
              tag: "escalate"
          enabled: true
    """

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    name: str
    project_gid: str
    conditions: list[RuleCondition]
    action: ActionConfig
    enabled: bool = True

    @field_validator("rule_id")
    @classmethod
    def rule_id_must_be_non_empty(cls, v: str) -> str:
        """Validate that rule_id is non-empty."""
        if not v or not v.strip():
            raise ValueError("rule_id must be non-empty")
        return v


class SchedulerConfig(BaseModel):
    """Polling scheduler configuration.

    Attributes:
        time: Time of day to run daily evaluation in 24-hour format "HH:MM".
        timezone: IANA timezone name (e.g., "UTC", "America/New_York").

    Example:
        scheduler:
          time: "02:00"
          timezone: "UTC"
    """

    model_config = ConfigDict(extra="forbid")

    time: str
    timezone: str

    @field_validator("time")
    @classmethod
    def time_must_be_valid_format(cls, v: str) -> str:
        """Validate that time is in HH:MM format (24-hour)."""
        pattern = r"^([01]\d|2[0-3]):([0-5]\d)$"
        if not re.match(pattern, v):
            raise ValueError(
                f"time must be in HH:MM format (24-hour), got '{v}'"
            )
        return v


class AutomationRulesConfig(BaseModel):
    """Top-level configuration for polling-based automation rules.

    This is the root schema for the YAML configuration file.

    Attributes:
        scheduler: Polling scheduler configuration (time and timezone).
        rules: List of automation rules to evaluate.

    Example YAML:
        scheduler:
          time: "02:00"
          timezone: "America/New_York"
        rules:
          - rule_id: "escalate-triage"
            name: "Escalate stale triage tasks"
            project_gid: "1234567890123"
            conditions:
              - stale:
                  field: "Section"
                  days: 3
            action:
              type: "add_tag"
              params:
                tag: "escalate"
            enabled: true
    """

    model_config = ConfigDict(extra="forbid")

    scheduler: SchedulerConfig
    rules: list[Rule]
