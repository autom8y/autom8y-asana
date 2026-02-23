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

# ---------------------------------------------------------------------------
# Resolve NameGid forward references for all models.
#
# All model files use `from __future__ import annotations` which defers
# annotation evaluation.  NameGid is imported under TYPE_CHECKING only, so
# it is absent from each module's runtime globals.  Pydantic cannot resolve
# the forward reference string "NameGid" without an explicit rebuild.
#
# Calling model_rebuild() here -- after NameGid and every model are imported
# -- resolves the deferred annotations deterministically, regardless of
# which module is imported first by test collection or application code.
#
# Task is rebuilt first because BusinessEntity (and all business models)
# inherit from it; Pydantic propagates the rebuild to subclasses.
# ---------------------------------------------------------------------------
_NAMEGID_NS: dict[str, type] = {"NameGid": NameGid}

# Tier 0 -- base model that business models inherit from
Task.model_rebuild(_types_namespace=_NAMEGID_NS)

# Tier 1 resource models
Attachment.model_rebuild(_types_namespace=_NAMEGID_NS)
CustomField.model_rebuild(_types_namespace=_NAMEGID_NS)
CustomFieldSetting.model_rebuild(_types_namespace=_NAMEGID_NS)
Project.model_rebuild(_types_namespace=_NAMEGID_NS)
Section.model_rebuild(_types_namespace=_NAMEGID_NS)
User.model_rebuild(_types_namespace=_NAMEGID_NS)
Workspace.model_rebuild(_types_namespace=_NAMEGID_NS)

# Tier 2 resource models
Goal.model_rebuild(_types_namespace=_NAMEGID_NS)
GoalMembership.model_rebuild(_types_namespace=_NAMEGID_NS)
GoalMetric.model_rebuild(_types_namespace=_NAMEGID_NS)
Portfolio.model_rebuild(_types_namespace=_NAMEGID_NS)
Story.model_rebuild(_types_namespace=_NAMEGID_NS)
Tag.model_rebuild(_types_namespace=_NAMEGID_NS)
Team.model_rebuild(_types_namespace=_NAMEGID_NS)
TeamMembership.model_rebuild(_types_namespace=_NAMEGID_NS)
Webhook.model_rebuild(_types_namespace=_NAMEGID_NS)
WebhookFilter.model_rebuild(_types_namespace=_NAMEGID_NS)

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
