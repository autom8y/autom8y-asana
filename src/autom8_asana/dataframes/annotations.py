"""Semantic annotation registry for ColumnDef description enrichment.

Per ADR-omniscience-semantic-introspection (D1, D2):
- Centralized annotation registry keyed by "{schema_name}.{column_name}"
- enrich_schema() produces a NEW DataFrameSchema with enriched descriptions
- Enrichment appends YAML after a ``\\n---\\n`` delimiter in ColumnDef.description
- Backward compatible: ``description.split("---")[0]`` returns human-readable text

Annotation data sourced from:
- Sprint 7 Enum Glossary (.ledge/spikes/omniscience-enum-glossary.md)
- Sprint 7 Numeric Ranges (.ledge/spikes/omniscience-numeric-ranges.md)
- Sprint 9 Cascade Semantics (.ledge/spikes/omniscience-cascade-semantics.md)
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema

# ---------------------------------------------------------------------------
# Closed vocabularies from the annotation schema v1.0
# ---------------------------------------------------------------------------

VALID_SEMANTIC_TYPES: frozenset[str] = frozenset(
    {
        "currency",
        "percentage",
        "identifier",
        "enum",
        "multi_enum",
        "phone",
        "email",
        "url",
        "timestamp",
        "count",
        "score",
        "text",
        "boolean",
        "person",
        "duration",
        "version",
    }
)

VALID_VALUES_SOURCES: frozenset[str] = frozenset({"hardcoded", "asana_configured", "mixed"})

VALID_NULL_SEVERITIES: frozenset[str] = frozenset({"expected", "warning", "error"})

# ---------------------------------------------------------------------------
# YAML delimiter used to separate human-readable description from metadata
# ---------------------------------------------------------------------------

YAML_DELIMITER = "\n---\n"

# ---------------------------------------------------------------------------
# SEMANTIC_ANNOTATIONS: The single source of truth for all annotations.
#
# Keyed by "{schema_name}.{column_name}".
# Each value is a dict suitable for YAML serialization under a "semantic:" key.
#
# Scope: 19 column-schema combinations per ADR implementation plan.
# - 12 cascade column entries (from Sprint 9 cascade semantics)
# - 7 HD-02 priority non-cascade field entries (from Sprint 7 research)
# ---------------------------------------------------------------------------

SEMANTIC_ANNOTATIONS: dict[str, dict[str, Any]] = {
    # =======================================================================
    # CASCADE COLUMNS (12 entries)
    # =======================================================================
    #
    # --- 9.1: office_phone (Cascade: Office Phone, Source: Business) ---
    "unit.office_phone": {
        "business_meaning": (
            "Office phone number for the Business entity. Cascades from the "
            "Business ancestor to all descendant entity types. Primary lookup "
            "key for resolution. Null office_phone causes the entity to be "
            "invisible to resolution queries, returning NOT_FOUND."
        ),
        "data_type_semantic": "phone",
        "resolution_impact": (
            "CRITICAL. Key column for unit (office_phone, vertical), offer "
            "(office_phone, vertical, offer_id), contact, asset_edit, and "
            "asset_edit_holder resolution. Null office_phone = entity excluded "
            "from DynamicIndex = silent NOT_FOUND."
        ),
        "cascade_behavior": {
            "source_entity": "Business",
            "target_entities": [
                "Unit",
                "Offer",
                "Process",
                "Contact",
                "AssetEdit",
                "AssetEditHolder",
            ],
            "allow_override": False,
            "warm_priority": 1,
        },
        "agent_discoverable": True,
    },
    "offer.office_phone": {
        "business_meaning": (
            "Office phone number for the Business entity. Cascades from the "
            "Business ancestor to all descendant entity types. Primary lookup "
            "key for resolution. Null office_phone causes the entity to be "
            "invisible to resolution queries, returning NOT_FOUND."
        ),
        "data_type_semantic": "phone",
        "resolution_impact": (
            "CRITICAL. Key column for offer (office_phone, vertical, offer_id) "
            "resolution. Null office_phone = entity excluded from DynamicIndex "
            "= silent NOT_FOUND."
        ),
        "cascade_behavior": {
            "source_entity": "Business",
            "target_entities": [
                "Unit",
                "Offer",
                "Process",
                "Contact",
                "AssetEdit",
                "AssetEditHolder",
            ],
            "allow_override": False,
            "warm_priority": 1,
        },
        "agent_discoverable": True,
    },
    "contact.office_phone": {
        "business_meaning": (
            "Office phone number for the Business entity. Cascades from the "
            "Business ancestor. Primary lookup key for contact resolution."
        ),
        "data_type_semantic": "phone",
        "resolution_impact": (
            "CRITICAL. Key column for contact (office_phone, contact_phone, "
            "contact_email) resolution. Null office_phone degrades contact "
            "lookup reliability."
        ),
        "cascade_behavior": {
            "source_entity": "Business",
            "target_entities": [
                "Unit",
                "Offer",
                "Process",
                "Contact",
                "AssetEdit",
                "AssetEditHolder",
            ],
            "allow_override": False,
            "warm_priority": 1,
        },
        "agent_discoverable": True,
    },
    "asset_edit.office_phone": {
        "business_meaning": (
            "Office phone number for the Business entity. Cascades from the "
            "Business ancestor. Key column for asset_edit resolution."
        ),
        "data_type_semantic": "phone",
        "resolution_impact": (
            "CRITICAL. Key column for asset_edit (office_phone, vertical, "
            "asset_id, offer_id) resolution. Null office_phone = entity "
            "excluded from DynamicIndex."
        ),
        "cascade_behavior": {
            "source_entity": "Business",
            "target_entities": [
                "Unit",
                "Offer",
                "Process",
                "Contact",
                "AssetEdit",
                "AssetEditHolder",
            ],
            "allow_override": False,
            "warm_priority": 1,
        },
        "agent_discoverable": True,
    },
    "asset_edit_holder.office_phone": {
        "business_meaning": (
            "Office phone number for the Business entity. Cascades from the "
            "Business ancestor. AssetEditHolder has 100% cascade dependency "
            "on this single field -- if cascade fails, entity is entirely "
            "unlookable."
        ),
        "data_type_semantic": "phone",
        "resolution_impact": (
            "CRITICAL. Sole key column for asset_edit_holder (office_phone) "
            "resolution. 100% cascade dependency."
        ),
        "cascade_behavior": {
            "source_entity": "Business",
            "target_entities": [
                "Unit",
                "Offer",
                "Process",
                "Contact",
                "AssetEdit",
                "AssetEditHolder",
            ],
            "allow_override": False,
            "warm_priority": 1,
        },
        "agent_discoverable": True,
    },
    # --- 9.2: vertical (Cascade: Vertical, Source: Unit) ---
    "offer.vertical": {
        "business_meaning": (
            "Business vertical classifying the client's industry. Cascades "
            "from the Unit ancestor to Offer. Determines ad targeting "
            "parameters, compliance requirements, landing page templates, "
            "and optimization strategy."
        ),
        "data_type_semantic": "enum",
        "valid_values": "dynamic",
        "valid_values_note": (
            "50+ enabled enum options on the Asana Vertical custom field "
            "(GID 1182735041547604). Values are snake_case healthcare verticals "
            "(e.g. chiropractic, dentistry, weight_loss, aesthetics, neuropathy). "
            "Canonical source: Asana workspace custom field enum_options. "
            "Per truth audit 2026-03-29: previous annotation of only "
            "'Medical/Dental/General' was incorrect — 'General' does not exist "
            "as an enum option."
        ),
        "values_source": "asana_configured",
        "resolution_impact": (
            "CRITICAL. Key column for offer (office_phone, vertical, offer_id) "
            "and asset_edit resolution. Null vertical makes Unit disambiguation "
            "impossible when multiple Units exist under one Business."
        ),
        "cascade_behavior": {
            "source_entity": "Unit",
            "target_entities": ["Offer", "Process", "Contact"],
            "allow_override": False,
            "warm_priority": 2,
        },
        "agent_discoverable": True,
    },
    "contact.vertical": {
        "business_meaning": (
            "Business vertical classifying the client's industry. Cascades "
            "from the Unit ancestor to Contact."
        ),
        "data_type_semantic": "enum",
        "valid_values": "dynamic",
        "valid_values_note": (
            "50+ enabled enum options on the Asana Vertical custom field "
            "(GID 1182735041547604). Values are snake_case healthcare verticals "
            "(e.g. chiropractic, dentistry, weight_loss, aesthetics, neuropathy). "
            "Canonical source: Asana workspace custom field enum_options. "
            "Per truth audit 2026-03-29: previous annotation of only "
            "'Medical/Dental/General' was incorrect — 'General' does not exist "
            "as an enum option."
        ),
        "values_source": "asana_configured",
        "resolution_impact": (
            "Not a resolution key column for contact. Contact uses "
            "(office_phone, contact_phone, contact_email) for resolution."
        ),
        "cascade_behavior": {
            "source_entity": "Unit",
            "target_entities": ["Offer", "Process", "Contact"],
            "allow_override": False,
            "warm_priority": 2,
        },
        "agent_discoverable": True,
    },
    "asset_edit.vertical": {
        "business_meaning": (
            "Business vertical classifying the client's industry. Cascades "
            "from the Unit ancestor to AssetEdit."
        ),
        "data_type_semantic": "enum",
        "valid_values": "dynamic",
        "valid_values_note": (
            "50+ enabled enum options on the Asana Vertical custom field "
            "(GID 1182735041547604). Values are snake_case healthcare verticals "
            "(e.g. chiropractic, dentistry, weight_loss, aesthetics, neuropathy). "
            "Canonical source: Asana workspace custom field enum_options. "
            "Per truth audit 2026-03-29: previous annotation of only "
            "'Medical/Dental/General' was incorrect — 'General' does not exist "
            "as an enum option."
        ),
        "values_source": "asana_configured",
        "resolution_impact": (
            "CRITICAL. Key column for asset_edit (office_phone, vertical, "
            "asset_id, offer_id) resolution."
        ),
        "cascade_behavior": {
            "source_entity": "Unit",
            "target_entities": ["Offer", "Process", "Contact"],
            "allow_override": False,
            "warm_priority": 2,
        },
        "agent_discoverable": True,
    },
    # --- 9.3: office (Cascade: Business Name, Source: Business) ---
    "unit.office": {
        "business_meaning": (
            "Office name derived from the Business ancestor's Task.name "
            "property. Uses the source_field mechanism (source_field='name') "
            "rather than a custom field. Display-only column."
        ),
        "data_type_semantic": "text",
        "resolution_impact": (
            "Not a resolution key column. Display-only. Null office degrades "
            "report readability but does not affect entity lookup."
        ),
        "cascade_behavior": {
            "source_entity": "Business",
            "target_entities": ["Unit", "Offer"],
            "allow_override": False,
            "warm_priority": 1,
        },
        "agent_discoverable": True,
    },
    "offer.office": {
        "business_meaning": (
            "Office name derived from the Business ancestor's Task.name "
            "property. Display-only column for human readability."
        ),
        "data_type_semantic": "text",
        "resolution_impact": ("Not a resolution key column. Display-only."),
        "cascade_behavior": {
            "source_entity": "Business",
            "target_entities": ["Unit", "Offer"],
            "allow_override": False,
            "warm_priority": 1,
        },
        "agent_discoverable": True,
    },
    # --- 9.4: mrr (Cascade: MRR, Source: Unit) ---
    "offer.mrr": {
        "business_meaning": (
            "Monthly Recurring Revenue in USD. Cascades from the Unit ancestor "
            "to Offer. Represents the contracted monthly payment amount for "
            "the client's service package. Primary financial metric for account "
            "sizing, resource allocation, and optimization priority."
        ),
        "data_type_semantic": "currency",
        "typical_range": {
            "min": 0,
            "max": 100000,
            "unit": "usd",
        },
        "anomaly_threshold": {
            "low": None,
            "high": 100000,
            "null_severity": "warning",
        },
        "resolution_impact": (
            "Not a resolution key column. Cascaded from Unit to Offer for "
            "financial reporting consistency."
        ),
        "cascade_behavior": {
            "source_entity": "Unit",
            "target_entities": ["Offer"],
            "allow_override": False,
            "warm_priority": 2,
        },
        "agent_discoverable": True,
    },
    # --- 9.5: weekly_ad_spend (Cascade: Weekly Ad Spend, Source: Unit) ---
    "offer.weekly_ad_spend": {
        "business_meaning": (
            "Weekly advertising spend budget in USD. Cascades from the Unit "
            "ancestor to Offer. Used for budget allocation, pacing, and "
            "spend optimization."
        ),
        "data_type_semantic": "currency",
        "typical_range": {
            "min": 0,
            "max": 50000,
            "unit": "usd",
        },
        "anomaly_threshold": {
            "low": None,
            "high": 50000,
            "null_severity": "expected",
        },
        "resolution_impact": (
            "Not a resolution key column. Cascaded from Unit to Offer for "
            "financial reporting consistency."
        ),
        "cascade_behavior": {
            "source_entity": "Unit",
            "target_entities": ["Offer"],
            "allow_override": False,
            "warm_priority": 2,
        },
        "agent_discoverable": True,
    },
    # =======================================================================
    # HD-02 PRIORITY NON-CASCADE FIELDS (7 entries)
    # =======================================================================
    #
    # --- unit.mrr (direct custom field, not cascade) ---
    "unit.mrr": {
        "business_meaning": (
            "Monthly Recurring Revenue in USD. Direct custom field on the Unit. "
            "Represents the contracted monthly payment amount. Primary owner "
            "of MRR -- cascades down to Offer with allow_override=False."
        ),
        "data_type_semantic": "currency",
        "typical_range": {
            "min": 0,
            "max": 100000,
            "unit": "usd",
        },
        "anomaly_threshold": {
            "low": None,
            "high": 100000,
            "null_severity": "warning",
        },
        "resolution_impact": (
            "Not a resolution key column. However, null MRR on a Unit may "
            "indicate an incomplete business setup."
        ),
        "agent_discoverable": True,
    },
    # --- unit.weekly_ad_spend (direct custom field, not cascade) ---
    "unit.weekly_ad_spend": {
        "business_meaning": (
            "Weekly advertising spend budget in USD. Direct custom field on "
            "the Unit. Primary owner -- cascades down to Offer with "
            "allow_override=False."
        ),
        "data_type_semantic": "currency",
        "typical_range": {
            "min": 0,
            "max": 50000,
            "unit": "usd",
        },
        "anomaly_threshold": {
            "low": None,
            "high": 50000,
            "null_severity": "expected",
        },
        "resolution_impact": (
            "Not a resolution key column. Operational field for resource "
            "allocation and financial reporting."
        ),
        "agent_discoverable": True,
    },
    # --- unit.vertical (direct custom field, Unit OWNS vertical) ---
    "unit.vertical": {
        "business_meaning": (
            "Business vertical classifying the client's industry. Direct "
            "custom field on the Unit (source=cf:Vertical). The Unit OWNS "
            "this field and cascades it to Offer, Process, and Contact."
        ),
        "data_type_semantic": "enum",
        "valid_values": "dynamic",
        "valid_values_note": (
            "50+ enabled enum options on the Asana Vertical custom field "
            "(GID 1182735041547604). Values are snake_case healthcare verticals "
            "(e.g. chiropractic, dentistry, weight_loss, aesthetics, neuropathy). "
            "Canonical source: Asana workspace custom field enum_options. "
            "Per truth audit 2026-03-29: previous annotation of only "
            "'Medical/Dental/General' was incorrect — 'General' does not exist "
            "as an enum option."
        ),
        "values_source": "asana_configured",
        "resolution_impact": (
            "CRITICAL. Key column for unit (office_phone, vertical). "
            "Null vertical makes Unit disambiguation impossible when "
            "multiple Units exist under one Business."
        ),
        "agent_discoverable": True,
    },
    # --- offer.cost (direct custom field, Utf8 dtype discrepancy) ---
    "offer.cost": {
        "business_meaning": (
            "Price of the individual Offer in USD. Used for financial "
            "analysis, pricing comparison across Offers, and revenue "
            "forecasting."
        ),
        "data_type_semantic": "currency",
        "typical_range": {
            "min": 0,
            "max": 50000,
            "unit": "usd",
        },
        "anomaly_threshold": {
            "low": None,
            "high": 50000,
            "null_severity": "expected",
        },
        "resolution_impact": "Not a resolution key column.",
        "schema_discrepancy": (
            "Schema declares dtype=Utf8 but model uses NumberField(). "
            "DataFrame layer stores raw string; model layer extracts "
            "numeric value. Non-numeric strings (e.g., 'TBD') will "
            "cause silent None on model access."
        ),
        "agent_discoverable": True,
    },
    # --- offer.platforms (direct custom field, multi-enum) ---
    "offer.platforms": {
        "business_meaning": (
            "Advertising platforms (Google, Facebook, etc.) available for "
            "the Offer. Multi-enum field. The ONLY cascade field with "
            "allow_override=True at the model layer (Offers can keep "
            "their own non-null Platforms value)."
        ),
        "data_type_semantic": "multi_enum",
        "values_source": "asana_configured",
        "resolution_impact": "Not a resolution key column.",
        "agent_discoverable": True,
    },
    # --- offer.language (direct custom field, enum) ---
    "offer.language": {
        "business_meaning": (
            "Language targeting for the Offer's ad campaigns. Determines "
            "which language the ad creative and landing pages are "
            "produced in."
        ),
        "data_type_semantic": "enum",
        "values_source": "asana_configured",
        "resolution_impact": "Not a resolution key column.",
        "agent_discoverable": True,
    },
    # --- offer.offer_id (direct custom field, identifier) ---
    "offer.offer_id": {
        "business_meaning": (
            "Unique identifier for the Offer. Used as a resolution key "
            "column to disambiguate Offers within the same Unit when "
            "office_phone and vertical match."
        ),
        "data_type_semantic": "identifier",
        "resolution_impact": (
            "CRITICAL. Key column for offer (office_phone, vertical, offer_id) resolution."
        ),
        "agent_discoverable": True,
    },
}


# ---------------------------------------------------------------------------
# Enrichment Functions
# ---------------------------------------------------------------------------


def enrich_description(schema_name: str, col: ColumnDef) -> str:
    """Merge human-readable description with YAML semantic annotation.

    If no annotation exists for ``{schema_name}.{col.name}``, returns the
    original description unchanged.

    Args:
        schema_name: Schema name (e.g., "unit", "offer").
        col: ColumnDef instance to enrich.

    Returns:
        Enriched description string with YAML after ``---`` delimiter,
        or the original description if no annotation exists.
    """
    key = f"{schema_name}.{col.name}"
    annotation = SEMANTIC_ANNOTATIONS.get(key)
    if annotation is None:
        return col.description or ""

    human_text = col.description or ""
    yaml_block = yaml.dump(
        {"semantic": annotation},
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    return f"{human_text}{YAML_DELIMITER}{yaml_block}"


def enrich_schema(
    schema: DataFrameSchema,
    *,
    include_semantic: bool = True,
) -> DataFrameSchema:
    """Produce a NEW DataFrameSchema with enriched ColumnDef descriptions.

    Per ADR D2: Enrichment is applied lazily at introspection time, not at
    schema definition time. The original schema is never modified.

    Args:
        schema: Original DataFrameSchema instance.
        include_semantic: When True (default), append YAML annotations.
            When False, return the schema unchanged.

    Returns:
        A new DataFrameSchema with enriched descriptions. The original
        schema instance is not modified.
    """
    if not include_semantic:
        return schema

    enriched_columns: list[ColumnDef] = []
    for col in schema.columns:
        new_desc = enrich_description(schema.name, col)
        if new_desc != (col.description or ""):
            enriched_columns.append(replace(col, description=new_desc))
        else:
            enriched_columns.append(col)

    # Create a new DataFrameSchema -- do not mutate the original
    from autom8_asana.dataframes.models.schema import DataFrameSchema as DFSchema

    return DFSchema(
        name=schema.name,
        task_type=schema.task_type,
        columns=enriched_columns,
        version=schema.version,
    )


def parse_semantic_metadata(description: str | None) -> dict[str, Any] | None:
    """Parse structured metadata from an enriched description.

    Args:
        description: Enriched description string, possibly containing
            a ``---`` delimiter followed by YAML.

    Returns:
        Parsed dict from the YAML block (the ``semantic:`` key's value),
        or None if no metadata is present.
    """
    if not description or YAML_DELIMITER not in description:
        return None

    parts = description.split("---", 1)
    if len(parts) < 2:
        return None

    try:
        parsed = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None

    if isinstance(parsed, dict) and "semantic" in parsed:
        result: dict[str, Any] = parsed["semantic"]
        return result
    return None


def get_semantic_type(description: str | None) -> str | None:
    """Extract data_type_semantic from an enriched description.

    Convenience function for filtering columns by semantic type.

    Args:
        description: Enriched description string.

    Returns:
        The data_type_semantic value (e.g., "phone", "enum"), or None.
    """
    metadata = parse_semantic_metadata(description)
    if metadata is None:
        return None
    return metadata.get("data_type_semantic")
