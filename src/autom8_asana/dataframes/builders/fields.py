"""Consolidated opt_fields for DataFrame extraction.

Per TDD-DATAFRAME-BUILDER-WATERMARK-001 Phase 1: Provides shared BASE_OPT_FIELDS
used by both ProjectDataFrameBuilder and ProgressiveProjectBuilder, including
the modified_at field required for watermark-based incremental processing.

This module eliminates duplication of _BASE_OPT_FIELDS across builders and
provides a single source of truth for the fields required during task fetching.
"""

from __future__ import annotations

# Base opt_fields required for DataFrame extraction.
#
# These fields are needed to populate the 12 base TaskRow fields plus
# the _modified_at watermark column for incremental processing.
#
# Field categories:
# - Core identity: gid, name, resource_subtype
# - Status: completed, completed_at, created_at, modified_at, due_on
# - Relationships: tags, memberships, parent
# - Custom fields: custom_fields with nested subfields
#
# Note: modified_at is required for watermark-based task filtering.
# The IncrementalFilter uses modified_at to determine whether a cached
# task needs reprocessing (PROCESS) or can be skipped (SKIP).

BASE_OPT_FIELDS: list[str] = [
    # Core identity fields
    "gid",
    "name",
    "resource_subtype",
    # Status fields
    "completed",
    "completed_at",
    "created_at",
    "modified_at",  # Required for watermark tracking
    "due_on",
    # Tag relationships
    "tags",
    "tags.name",
    # Section membership for project context
    "memberships.section.name",
    "memberships.project.gid",
    # Parent reference for cascade: field resolution
    # Per TDD-CASCADING-FIELD-RESOLUTION-001: CascadingFieldResolver needs parent.gid
    # to traverse the parent chain and resolve fields from ancestor tasks
    "parent",
    "parent.gid",
    # Custom fields for resolver-based extraction (cf:* sources)
    # Per TDD-0009.1: DefaultCustomFieldResolver needs custom_fields to build
    # the name->GID index and extract values for office_phone, vertical, etc.
    "custom_fields",
    "custom_fields.gid",
    "custom_fields.name",
    "custom_fields.resource_subtype",
    "custom_fields.display_value",
    "custom_fields.enum_value",
    "custom_fields.enum_value.name",
    "custom_fields.multi_enum_values",
    "custom_fields.multi_enum_values.name",
    "custom_fields.number_value",
    "custom_fields.text_value",
]


# Watermark column name for DataFrame storage
# Per ADR-001 in TDD: Stored as reserved column with underscore prefix
WATERMARK_COLUMN_NAME: str = "_modified_at"
