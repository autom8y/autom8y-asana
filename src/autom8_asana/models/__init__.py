"""Pydantic models for Asana API resources.

Per ADR-0005: All models use extra="ignore" for forward compatibility with API changes.
Per TDD-0002: NameGid for typed resource references, PageIterator for pagination.
Per TDD-0003: Tier 1 resource models (Project, Section, CustomField, User, Workspace).
Per TDD-0004: Tier 2 resource models (Webhook, Team, Attachment, Tag, Goal, Portfolio, Story).
"""

from autom8_asana.models.attachment import Attachment
from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid, PageIterator
from autom8_asana.models.custom_field import (
    CustomField,
    CustomFieldEnumOption,
    CustomFieldSetting,
)
from autom8_asana.models.custom_field_accessor import CustomFieldAccessor
from autom8_asana.models.goal import Goal, GoalMembership, GoalMetric
from autom8_asana.models.portfolio import Portfolio
from autom8_asana.models.project import Project
from autom8_asana.models.section import Section
from autom8_asana.models.story import Story
from autom8_asana.models.tag import Tag
from autom8_asana.models.task import Task
from autom8_asana.models.team import Team, TeamMembership
from autom8_asana.models.user import User
from autom8_asana.models.webhook import Webhook, WebhookFilter
from autom8_asana.models.workspace import Workspace

__all__ = [
    # Base
    "AsanaResource",
    "NameGid",
    "PageIterator",
    # Accessors
    "CustomFieldAccessor",
    # Tier 1 models
    "CustomField",
    "CustomFieldEnumOption",
    "CustomFieldSetting",
    "Project",
    "Section",
    "Task",
    "User",
    "Workspace",
    # Tier 2 models
    "Attachment",
    "Goal",
    "GoalMembership",
    "GoalMetric",
    "Portfolio",
    "Story",
    "Tag",
    "Team",
    "TeamMembership",
    "Webhook",
    "WebhookFilter",
]
