# Factory to frame_type Mapping

**Status**: Authoritative
**Created**: 2026-02-07
**Sprint**: Entity Resolution Hardening - Phase A Foundation
**Task**: TASK-002

## Purpose

This document provides the binding mapping between autom8_asana's 14 VALID_FACTORIES and autom8_data's 4 `frame_type` enum values. This mapping is critical for the entity resolution system to correctly route factory names to the appropriate frame_type parameter in autom8_data's InsightsRequest API.

## Source References

- **autom8_asana factories**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py` (lines 699-731)
- **autom8_data frame_type**: `/Users/tomtenuta/Code/autom8_data/src/autom8_data/api/data_service_models/_insights.py` (line 32)
- **frame_type semantics**: `/Users/tomtenuta/Code/autom8_data/src/autom8_data/api/services/frame_type_mapper.py` (lines 59-64, 175-210)

## frame_type Semantics

autom8_data defines 4 frame_type values with the following semantics:

| frame_type | Insight | Dimensions | Semantic Grouping |
|------------|---------|------------|-------------------|
| `"offer"` | `offer_level_stats` | `offer_id`, `offer_name`, `offer_cost`, `office_phone`, `vertical`, `office` | Metrics grouped by promotional offer |
| `"unit"` | `account_level_stats` | `office_phone`, `vertical`, `office` | Metrics grouped by account/unit (office_phone) |
| `"business"` | `account_level_stats` | `office_phone`, `vertical`, `office` | Alias for unit (1:1 mapping with office_phone) |
| `"asset"` | `asset_level_stats` | `asset_id`, `platform_id`, `asset_type`, `office_phone`, `vertical`, `office`, `asset_link`, `transcript`, `is_raw`, `is_generic`, `disabled` | Metrics grouped by creative asset |

**Note**: `"business"` and `"unit"` map to the same insight (`account_level_stats`) with identical dimensions and metrics. They are semantic aliases representing account-level aggregation.

## Factory to frame_type Mapping

| Factory Name | frame_type | Rationale | Source Evidence |
|--------------|------------|-----------|-----------------|
| `account` | `business` | Account-level aggregated metrics across all offers | Client.py line 701: "aggregated account metrics"; FrameTypeMapper line 62: "unit: Metrics grouped by office_phone (account/unit level)" |
| `ads` | `offer` | Individual ad performance is offer-scoped | Client.py line 702: "individual ad performance"; Ads are promotional units grouped by offer_id |
| `adsets` | `offer` | Ad set level metrics are offer-scoped | Client.py line 703: "ad set level metrics"; Ad sets organize ads within offers |
| `campaigns` | `offer` | Campaign level metrics are offer-scoped | Client.py line 704: "campaign level metrics"; Campaigns are offer-level constructs |
| `spend` | `offer` | Spend breakdown by offer | Client.py line 705: "spend breakdown"; Spend is tracked at offer granularity |
| `leads` | `offer` | Lead generation metrics by offer | Client.py line 706: "lead generation metrics"; Leads are offer-attributed |
| `appts` | `offer` | Appointment metrics by offer | Client.py line 707: "appointment metrics"; Appointments result from offer activity |
| `assets` | `asset` | Creative asset performance | Client.py line 708: "creative asset metrics"; FrameTypeMapper line 63: "asset: Metrics grouped by asset_id (creative asset level)" |
| `targeting` | `offer` | Audience targeting metrics by offer | Client.py line 709: "audience targeting metrics"; Targeting configurations are offer-specific |
| `payments` | `business` | Payment/billing metrics at business level | Client.py line 710: "payment/billing metrics"; Payments aggregate across offers |
| `business_offers` | `offer` | Offer metrics for business reporting | Client.py line 711: "offer metrics"; Despite "business" prefix, this is offer-scoped data |
| `ad_questions` | `offer` | Ad question responses by offer | Client.py line 712: "ad question responses"; Questions are embedded in offer creatives |
| `ad_tests` | `offer` | A/B test results by offer | Client.py line 713: "A/B test results"; Tests compare offer-level variants |
| `base` | `unit` | Base/raw metrics at unit level | Client.py line 714: "base/raw metrics"; Base data is account-level foundation |

## Summary Statistics

- **Total factories**: 14
- **Mapped to `offer`**: 10 (71%)
- **Mapped to `business`**: 2 (14%)
- **Mapped to `unit`**: 2 (14%)
- **Mapped to `asset`**: 1 (7%)
- **Ambiguous mappings**: 0

## Machine-Parseable Mapping

```python
# Factory to frame_type binding map
# Source: docs/design/factory-to-frame-type-mapping.md
FACTORY_TO_FRAME_TYPE: dict[str, str] = {
    "account": "business",
    "ads": "offer",
    "adsets": "offer",
    "campaigns": "offer",
    "spend": "offer",
    "leads": "offer",
    "appts": "offer",
    "assets": "asset",
    "targeting": "offer",
    "payments": "business",
    "business_offers": "offer",
    "ad_questions": "offer",
    "ad_tests": "offer",
    "base": "unit",
}
```

## Validation

To validate this mapping against VALID_FACTORIES:

```python
from autom8_asana.clients.data.client import DataServiceClient

# All factory names must be in VALID_FACTORIES
assert set(FACTORY_TO_FRAME_TYPE.keys()) == DataServiceClient.VALID_FACTORIES

# All frame_types must be valid per autom8_data
from autom8_data.api.services.frame_type_mapper import VALID_FRAME_TYPES
assert all(ft in VALID_FRAME_TYPES for ft in FACTORY_TO_FRAME_TYPE.values())
```

## Usage Notes

1. **`business` vs `unit`**: These are semantic aliases in autom8_data. Use `"business"` when the context is about business-level aggregation (payments, account summary) and `"unit"` when the context is about raw base data or account-level foundation.

2. **`business_offers` trap**: Despite the name containing "business", this factory is **offer-scoped**, not business-scoped. It provides offer metrics for business reporting purposes.

3. **Future factories**: When adding new factories to VALID_FACTORIES, determine frame_type by asking: "What is the primary dimension/entity this factory aggregates by?"
   - Offer-level constructs (campaigns, ads, spend) → `"offer"`
   - Account-level aggregations → `"business"` or `"unit"`
   - Creative assets → `"asset"`

## Open Questions

None. All 14 factories have deterministic mappings with clear rationale.

## Change History

| Date | Change | Author |
|------|--------|--------|
| 2026-02-07 | Initial mapping document created | Principal Engineer |
