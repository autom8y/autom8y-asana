"""Virtual entity registry for data-service join targets.

Maps logical data-service entity names to their DataServiceClient factory,
available columns, and join configuration. Used for:
- Validating JoinSpec.select columns when source="data-service"
- Introspection (list available data-service join targets)
- Default join key resolution

These are NOT Asana entities. They represent analytics data from autom8y-data
that can be joined onto Asana entity DataFrames via the QueryEngine.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DataServiceEntityInfo:
    """Metadata for a data-service virtual entity (join target).

    Attributes:
        factory: DataServiceClient factory name.
        frame_type: autom8_data frame_type value.
        description: Human-readable description.
        columns: Known column names returned by this factory.
        default_period: Default period if not specified in JoinSpec.
        join_key: Default join column (typically office_phone).
    """

    factory: str
    frame_type: str
    description: str
    columns: list[str] = field(default_factory=list)
    default_period: str = "LIFETIME"
    join_key: str = "office_phone"


# Top factories registered for Phase 1.
# Column lists are representative, not exhaustive — actual columns depend on
# the autom8_data factory configuration and may evolve independently.
DATA_SERVICE_ENTITIES: dict[str, DataServiceEntityInfo] = {
    "spend": DataServiceEntityInfo(
        factory="spend",
        frame_type="offer",
        description="Ad spend metrics by period",
        columns=[
            "office_phone",
            "vertical",
            "spend",
            "imp",
            "clicks",
            "ctr",
            "cpc",
            "cpm",
        ],
        default_period="T30",
    ),
    "leads": DataServiceEntityInfo(
        factory="leads",
        frame_type="offer",
        description="Lead generation metrics by period",
        columns=[
            "office_phone",
            "vertical",
            "leads",
            "scheds",
            "cps",
            "cpl",
            "conversion_rate",
            "booking_rate",
        ],
        default_period="T30",
    ),
    "appts": DataServiceEntityInfo(
        factory="appts",
        frame_type="offer",
        description="Appointment booking metrics by period",
        columns=[
            "office_phone",
            "vertical",
            "scheds",
            "ns",
            "nc",
            "booking_rate",
        ],
        default_period="T30",
    ),
    "campaigns": DataServiceEntityInfo(
        factory="campaigns",
        frame_type="offer",
        description="Campaign-level performance metrics",
        columns=[
            "office_phone",
            "vertical",
            "spend",
            "leads",
            "scheds",
            "cps",
            "roas",
        ],
        default_period="T30",
    ),
    "base": DataServiceEntityInfo(
        factory="base",
        frame_type="unit",
        description="Base unit-level metrics",
        columns=[
            "office_phone",
            "vertical",
            "spend",
            "leads",
            "scheds",
            "ltv",
        ],
        default_period="T30",
    ),
}


def get_data_service_entity(name: str) -> DataServiceEntityInfo | None:
    """Look up a data-service entity by name.

    Args:
        name: Logical entity name (e.g., "spend", "leads").

    Returns:
        DataServiceEntityInfo if found, None otherwise.
    """
    return DATA_SERVICE_ENTITIES.get(name)


def list_data_service_entities() -> list[dict[str, object]]:
    """List all registered data-service entities for introspection.

    Returns:
        List of dicts with keys: name, factory, frame_type, description,
        columns, default_period, join_key.
    """
    return [
        {
            "name": name,
            "factory": info.factory,
            "frame_type": info.frame_type,
            "description": info.description,
            "columns": info.columns,
            "default_period": info.default_period,
            "join_key": info.join_key,
        }
        for name, info in sorted(DATA_SERVICE_ENTITIES.items())
    ]
