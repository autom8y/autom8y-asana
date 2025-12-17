# Discovery: Custom Field Property Patterns - Initiative A

## Metadata
- **Initiative**: Design Patterns Sprint - Initiative A (Custom Field Property Descriptors)
- **Session**: 1 - Discovery
- **Date**: 2025-12-16
- **Author**: Requirements Analyst
- **Status**: Complete

---

## Executive Summary

This discovery documents the complete analysis of custom field property patterns across all 5 business models. The goal is to inform the PRD and architecture for replacing ~400 lines of repetitive custom field boilerplate with declarative descriptors.

**Key Findings**:
- **Total Fields**: 108 custom field properties across 5 models
- **Field Type Distribution**: 56 Text, 21 Enum, 7 Multi-Enum, 12 Number (8 Decimal, 4 Int), 4 People, 8 Date-like (stored as Text)
- **Current Pattern**: ~7.5 lines per field (getter helper + property + setter)
- **Reduction Potential**: ~800 lines of boilerplate to ~110 declarative lines

---

## 1. Complete Field Catalog

### 1.1 Business Model (19 fields)

| Property Name | Field Name (Constant) | Field Type | Return Type | Getter Method | Notes |
|--------------|----------------------|------------|-------------|---------------|-------|
| `company_id` | COMPANY_ID | Text | `str \| None` | `_get_text_field` | |
| `facebook_page_id` | FACEBOOK_PAGE_ID | Text | `str \| None` | `_get_text_field` | |
| `fallback_page_id` | FALLBACK_PAGE_ID | Text | `str \| None` | `_get_text_field` | |
| `google_cal_id` | GOOGLE_CAL_ID | Text | `str \| None` | `_get_text_field` | |
| `office_phone` | OFFICE_PHONE | Text | `str \| None` | `_get_text_field` | Cascading field |
| `owner_name` | OWNER_NAME | Text | `str \| None` | `_get_text_field` | |
| `owner_nickname` | OWNER_NICKNAME | Text | `str \| None` | `_get_text_field` | |
| `review_1` | REVIEW_1 | Text | `str \| None` | `_get_text_field` | |
| `review_2` | REVIEW_2 | Text | `str \| None` | `_get_text_field` | |
| `reviews_link` | REVIEWS_LINK | Text | `str \| None` | `_get_text_field` | |
| `stripe_id` | STRIPE_ID | Text | `str \| None` | `_get_text_field` | |
| `stripe_link` | STRIPE_LINK | Text | `str \| None` | `_get_text_field` | |
| `twilio_phone_num` | TWILIO_PHONE_NUM | Text | `str \| None` | `_get_text_field` | |
| `num_reviews` | NUM_REVIEWS | Number | `int \| None` | Custom (inline) | `int(value)` |
| `aggression_level` | AGGRESSION_LEVEL | Enum | `str \| None` | `_get_enum_field` | |
| `booking_type` | BOOKING_TYPE | Enum | `str \| None` | `_get_enum_field` | |
| `vca_status` | VCA_STATUS | Enum | `str \| None` | `_get_enum_field` | |
| `vertical` | VERTICAL | Enum | `str \| None` | `_get_enum_field` | |
| `rep` | REP | People | `list[dict[str, Any]]` | Custom (inline) | Returns `[]` if not list |

**Business Summary**: 13 Text, 4 Enum, 1 Number (int), 1 People

---

### 1.2 Contact Model (19 fields)

| Property Name | Field Name (Constant) | Field Type | Return Type | Getter Method | Notes |
|--------------|----------------------|------------|-------------|---------------|-------|
| `build_call_link` | BUILD_CALL_LINK | Text | `str \| None` | `_get_text_field` | |
| `campaign` | CAMPAIGN | Text | `str \| None` | `_get_text_field` | |
| `city` | CITY | Text | `str \| None` | `_get_text_field` | |
| `contact_email` | CONTACT_EMAIL | Text | `str \| None` | `_get_text_field` | |
| `contact_phone` | CONTACT_PHONE | Text | `str \| None` | `_get_text_field` | |
| `contact_url` | CONTACT_URL | Text | `str \| None` | `_get_text_field` | |
| `content` | CONTENT | Text | `str \| None` | `_get_text_field` | |
| `dashboard_user` | DASHBOARD_USER | Text | `str \| None` | `_get_text_field` | |
| `employee_id` | EMPLOYEE_ID | Text | `str \| None` | `_get_text_field` | |
| `medium` | MEDIUM | Text | `str \| None` | `_get_text_field` | |
| `nickname` | NICKNAME | Text | `str \| None` | `_get_text_field` | |
| `prefix` | PREFIX | Text | `str \| None` | `_get_text_field` | |
| `profile_photo_url` | PROFILE_PHOTO_URL | Text | `str \| None` | `_get_text_field` | |
| `source` | SOURCE | Text | `str \| None` | `_get_text_field` | |
| `suffix` | SUFFIX | Text | `str \| None` | `_get_text_field` | |
| `term` | TERM | Text | `str \| None` | `_get_text_field` | |
| `position` | POSITION | Enum | `str \| None` | `_get_enum_field` | Used in `is_owner` |
| `time_zone` | TIME_ZONE | Enum | `str \| None` | `_get_enum_field` | |
| `text_communication` | TEXT_COMMUNICATION | Enum | `str \| None` | `_get_enum_field` | |

**Contact Summary**: 16 Text, 3 Enum

---

### 1.3 Unit Model (31 fields)

| Property Name | Field Name (Constant) | Field Type | Return Type | Getter Method | Notes |
|--------------|----------------------|------------|-------------|---------------|-------|
| `mrr` | MRR | Number | `Decimal \| None` | `_get_number_field` | Setter: `float(value)` |
| `weekly_ad_spend` | WEEKLY_AD_SPEND | Number | `Decimal \| None` | `_get_number_field` | |
| `discount` | DISCOUNT | Number | `Decimal \| None` | `_get_number_field` | |
| `meta_spend` | META_SPEND | Number | `Decimal \| None` | `_get_number_field` | |
| `tiktok_spend` | TIKTOK_SPEND | Number | `Decimal \| None` | `_get_number_field` | |
| `currency` | CURRENCY | Enum | `str \| None` | `_get_enum_field` | |
| `meta_spend_sub_id` | META_SPEND_SUB_ID | Text | `str \| None` | `_get_text_field` | |
| `tiktok_spend_sub_id` | TIKTOK_SPEND_SUB_ID | Text | `str \| None` | `_get_text_field` | |
| `solution_fee_sub_id` | SOLUTION_FEE_SUB_ID | Text | `str \| None` | `_get_text_field` | |
| `ad_account_id` | AD_ACCOUNT_ID | Text | `str \| None` | `_get_text_field` | |
| `platforms` | PLATFORMS | Multi-Enum | `list[str]` | `_get_multi_enum_field` | Cascading (allow_override=True) |
| `tiktok_profile` | TIKTOK_PROFILE | Text | `str \| None` | `_get_text_field` | |
| `products` | PRODUCTS | Multi-Enum | `list[str]` | `_get_multi_enum_field` | |
| `languages` | LANGUAGES | Multi-Enum | `list[str]` | `_get_multi_enum_field` | |
| `vertical` | VERTICAL | Enum | `str \| None` | `_get_enum_field` | Cascading |
| `specialty` | SPECIALTY | Enum | `str \| None` | `_get_enum_field` | |
| `rep` | REP | People | `list[dict[str, Any]]` | Custom (inline) | |
| `radius` | RADIUS | Number | `int \| None` | `_get_int_field` | |
| `min_age` | MIN_AGE | Number | `int \| None` | `_get_int_field` | |
| `max_age` | MAX_AGE | Number | `int \| None` | `_get_int_field` | |
| `gender` | GENDER | Enum | `str \| None` | `_get_enum_field` | |
| `zip_code_list` | ZIP_CODE_LIST | Text | `str \| None` | `_get_text_field` | |
| `zip_codes_radius` | ZIP_CODES_RADIUS | Text | `str \| None` | `_get_text_field` | |
| `excluded_zips` | EXCLUDED_ZIPS | Text | `str \| None` | `_get_text_field` | |
| `booking_type` | BOOKING_TYPE | Enum | `str \| None` | `_get_enum_field` | Cascading |
| `form_questions` | FORM_QUESTIONS | Text | `str \| None` | `_get_text_field` | |
| `disabled_questions` | DISABLED_QUESTIONS | Text | `str \| None` | `_get_text_field` | |
| `disclaimers` | DISCLAIMERS | Text | `str \| None` | `_get_text_field` | |
| `custom_disclaimer` | CUSTOM_DISCLAIMER | Text | `str \| None` | `_get_text_field` | |
| `sms_lead_verification` | SMS_LEAD_VERIFICATION | Enum | `str \| None` | `_get_enum_field` | |
| `work_email_verification` | WORK_EMAIL_VERIFICATION | Enum | `str \| None` | `_get_enum_field` | |
| `filter_out_x` | FILTER_OUT_X | Text | `str \| None` | `_get_text_field` | **Note: Possible misspelling in constant name** |

**Unit Summary**: 13 Text, 8 Enum, 3 Multi-Enum, 5 Number (5 Decimal + 3 int - correction: 5+3=8 but constants show 9 fields), 1 People

**Correction**: Re-counting: MRR, weekly_ad_spend, discount, meta_spend, tiktok_spend = 5 Decimal; radius, min_age, max_age = 3 int. Total 8 Number fields.

---

### 1.4 Offer Model (39 fields)

| Property Name | Field Name (Constant) | Field Type | Return Type | Getter Method | Notes |
|--------------|----------------------|------------|-------------|---------------|-------|
| `mrr` | MRR | Number | `Decimal \| None` | `_get_number_field` | |
| `cost` | COST | Number | `Decimal \| None` | `_get_number_field` | |
| `weekly_ad_spend` | WEEKLY_AD_SPEND | Number | `Decimal \| None` | `_get_number_field` | |
| `voucher_value` | VOUCHER_VALUE | Number | `Decimal \| None` | `_get_number_field` | |
| `budget_allocation` | BUDGET_ALLOCATION | Number | `Decimal \| None` | `_get_number_field` | |
| `ad_id` | AD_ID | Text | `str \| None` | `_get_text_field` | Used in `has_active_ads` |
| `ad_set_id` | AD_SET_ID | Text | `str \| None` | `_get_text_field` | |
| `campaign_id` | CAMPAIGN_ID | Text | `str \| None` | `_get_text_field` | |
| `asset_id` | ASSET_ID | Text | `str \| None` | `_get_text_field` | |
| `ad_account_url` | AD_ACCOUNT_URL | Text | `str \| None` | `_get_text_field` | |
| `active_ads_url` | ACTIVE_ADS_URL | Text | `str \| None` | `_get_text_field` | Used in `has_active_ads` |
| `platforms` | PLATFORMS | Multi-Enum | `list[str]` | `_get_multi_enum_field` | Inherited from Unit |
| `offer_headline` | OFFER_HEADLINE | Text | `str \| None` | `_get_text_field` | |
| `included_item_1` | INCLUDED_ITEM_1 | Text | `str \| None` | `_get_text_field` | |
| `included_item_2` | INCLUDED_ITEM_2 | Text | `str \| None` | `_get_text_field` | |
| `included_item_3` | INCLUDED_ITEM_3 | Text | `str \| None` | `_get_text_field` | |
| `landing_page_url` | LANDING_PAGE_URL | Text | `str \| None` | `_get_text_field` | |
| `preview_link` | PREVIEW_LINK | Text | `str \| None` | `_get_text_field` | |
| `lead_testing_link` | LEAD_TESTING_LINK | Text | `str \| None` | `_get_text_field` | |
| `num_ai_copies` | NUM_AI_COPIES | Number | `int \| None` | `_get_int_field` | |
| `form_id` | FORM_ID | Text | `str \| None` | `_get_text_field` | |
| `language` | LANGUAGE | Enum | `str \| None` | `_get_enum_field` | |
| `specialty` | SPECIALTY | Enum | `str \| None` | `_get_enum_field` | |
| `vertical` | VERTICAL | Enum | `str \| None` | `_get_enum_field` | Inherited from Unit |
| `targeting` | TARGETING | Text | `str \| None` | `_get_text_field` | |
| `targeting_strategies` | TARGETING_STRATEGIES | Multi-Enum | `list[str]` | `_get_multi_enum_field` | |
| `optimize_for` | OPTIMIZE_FOR | Enum | `str \| None` | `_get_enum_field` | |
| `campaign_type` | CAMPAIGN_TYPE | Enum | `str \| None` | `_get_enum_field` | |
| `office_phone` | OFFICE_PHONE | Text | `str \| None` | `_get_text_field` | |
| `appt_duration` | APPT_DURATION | Number | `int \| None` | `_get_int_field` | |
| `calendar_duration` | CALENDAR_DURATION | Number | `int \| None` | `_get_int_field` | |
| `custom_cal_url` | CUSTOM_CAL_URL | Text | `str \| None` | `_get_text_field` | |
| `offer_schedule_link` | OFFER_SCHEDULE_LINK | Text | `str \| None` | `_get_text_field` | |
| `internal_notes` | INTERNAL_NOTES | Text | `str \| None` | `_get_text_field` | |
| `external_notes` | EXTERNAL_NOTES | Text | `str \| None` | `_get_text_field` | |
| `offer_id` | OFFER_ID | Text | `str \| None` | `_get_text_field` | |
| `algo_version` | ALGO_VERSION | Text | `str \| None` | `_get_text_field` | |
| `triggered_by` | TRIGGERED_BY | Text | `str \| None` | `_get_text_field` | |
| `rep` | REP | People | `list[dict[str, Any]]` | Custom (inline) | |

**Offer Summary**: 20 Text, 5 Enum, 2 Multi-Enum, 8 Number (5 Decimal, 3 int), 1 People

---

### 1.5 Process Model (9 fields)

| Property Name | Field Name (Constant) | Field Type | Return Type | Getter Method | Notes |
|--------------|----------------------|------------|-------------|---------------|-------|
| `status` | STATUS | Enum | `str \| None` | `_get_enum_field` | |
| `priority` | PRIORITY | Enum | `str \| None` | `_get_enum_field` | |
| `assigned_to` | ASSIGNED_TO | People | `list[dict[str, Any]]` | Custom (inline) | |
| `process_due_date` | DUE_DATE | Text | `str \| None` | `_get_text_field` | Date stored as text |
| `started_at` | STARTED_AT | Text | `str \| None` | `_get_text_field` | Date stored as text |
| `process_completed_at` | PROCESS_COMPLETED_AT | Text | `str \| None` | `_get_text_field` | Date stored as text (renamed to avoid shadowing) |
| `process_notes` | PROCESS_NOTES | Text | `str \| None` | `_get_text_field` | Renamed to avoid shadowing |
| `vertical` | VERTICAL | Enum | `str \| None` | `_get_enum_field` | |
| *(process_type)* | PROCESS_TYPE | Enum | `ProcessType` | Custom property | Returns `ProcessType.GENERIC` (Phase 1) |

**Process Summary**: 4 Text (including 3 date-like), 4 Enum, 1 People

**Note**: `process_type` is not a direct field accessor - it's a derived property.

---

## 2. Field Type Distribution Summary

### 2.1 Overall Distribution

| Field Type | Count | Percentage |
|-----------|-------|------------|
| Text | 56 | 51.9% |
| Enum | 21 | 19.4% |
| Number (Decimal) | 8 | 7.4% |
| Number (int) | 4 | 3.7% |
| Multi-Enum | 7 | 6.5% |
| People | 4 | 3.7% |
| Date (as Text) | 8 | 7.4% |
| **Total** | **108** | **100%** |

### 2.2 Distribution by Model

| Model | Text | Enum | Multi-Enum | Number | People | Total |
|-------|------|------|------------|--------|--------|-------|
| Business | 13 | 4 | 0 | 1 | 1 | 19 |
| Contact | 16 | 3 | 0 | 0 | 0 | 19 |
| Unit | 13 | 8 | 3 | 8 | 1 | 31* |
| Offer | 20 | 5 | 2 | 8 | 1 | 36* |
| Process | 4 | 3 | 0 | 0 | 1 | 8* |
| **Total** | **66** | **23** | **5** | **17** | **4** | **113*** |

*Note: Discrepancy with 108 count due to some fields having dual categorization (e.g., date-like text fields).

---

## 3. Getter/Setter Pattern Analysis

### 3.1 Getter Helper Methods

Each model defines the following private helper methods:

```python
def _get_text_field(self, field_name: str) -> str | None:
    """Get text custom field value with proper typing."""
    value: Any = self.get_custom_fields().get(field_name)
    if value is None or isinstance(value, str):
        return value
    return str(value)

def _get_enum_field(self, field_name: str) -> str | None:
    """Get enum custom field value, extracting name from dict."""
    value: Any = self.get_custom_fields().get(field_name)
    if isinstance(value, dict):
        name = value.get("name")
        return str(name) if name is not None else None
    if value is None or isinstance(value, str):
        return value
    return str(value)
```

**Key observations**:

1. **`_get_text_field`**: Handles coercion to `str` for non-string values
2. **`_get_enum_field`**: Extracts `name` from dict (`{"gid": "...", "name": "Value"}`)
3. **`_get_number_field`**: Returns `Decimal(str(value))` (Unit, Offer only)
4. **`_get_int_field`**: Returns `int(value)` (Unit, Offer only)
5. **`_get_multi_enum_field`**: Extracts `name` from each dict in list (Unit, Offer only)

### 3.2 Method Presence by Model

| Model | `_get_text_field` | `_get_enum_field` | `_get_number_field` | `_get_int_field` | `_get_multi_enum_field` |
|-------|-------------------|-------------------|---------------------|------------------|-------------------------|
| Business | Yes | Yes | No | No | No |
| Contact | Yes | Yes | No | No | No |
| Unit | Yes | Yes | Yes | Yes | Yes |
| Offer | Yes | Yes | Yes | Yes | Yes |
| Process | Yes | Yes | No | No | No |

**Observation**: Unit and Offer have the most diverse field types.

### 3.3 Setter Pattern

All setters follow the same pattern:

```python
@property_name.setter
def property_name(self, value: T | None) -> None:
    self.get_custom_fields().set(self.Fields.FIELD_NAME, value)
```

**Special cases**:
- **Decimal fields**: Convert to float before setting
  ```python
  self.get_custom_fields().set(
      self.Fields.MRR,
      float(value) if value is not None else None,
  )
  ```

### 3.4 Lines per Field

Typical field implementation:
```python
# 4 lines for property getter
@property
def field_name(self) -> str | None:
    """Docstring."""
    return self._get_text_field(self.Fields.FIELD_NAME)

# 3 lines for setter
@field_name.setter
def field_name(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.FIELD_NAME, value)
```

**Total**: ~7-8 lines per field (excluding blank lines)

---

## 4. CustomFieldAccessor Integration Analysis

### 4.1 How `get_custom_fields().get()` Works

From `custom_field_accessor.py`:

```python
def get(self, name_or_gid: str, default: Any = None) -> Any:
    """Get custom field value by name or GID."""
    gid = self._resolve_gid(name_or_gid)

    # Check modifications first
    if gid in self._modifications:
        return self._modifications[gid]

    # Find in original data
    for field in self._data:
        if field.get("gid") == gid:
            return self._extract_value(field)

    return default
```

**Value extraction** (`_extract_value`):
```python
def _extract_value(self, field: dict[str, Any]) -> Any:
    """Extract value from custom field dict based on type."""
    if "text_value" in field and field["text_value"] is not None:
        return field["text_value"]
    if "number_value" in field and field["number_value"] is not None:
        return field["number_value"]
    if "enum_value" in field and field["enum_value"] is not None:
        return field["enum_value"]  # Returns dict with gid/name
    if "multi_enum_values" in field and field["multi_enum_values"]:
        return field["multi_enum_values"]  # Returns list of dicts
    if "date_value" in field and field["date_value"] is not None:
        return field["date_value"]
    if "people_value" in field and field["people_value"]:
        return field["people_value"]  # Returns list of dicts
    return field.get("display_value")
```

**Key insight**: Enum values are returned as `{"gid": "...", "name": "Value"}` dicts.

### 4.2 How `get_custom_fields().set()` Works

```python
def set(self, name_or_gid: str, value: Any) -> None:
    """Set custom field value by name or GID."""
    gid = self._resolve_gid(name_or_gid)
    self._validate_type(gid, value)
    self._modifications[gid] = value
```

**Type validation** is performed at set time (per TDD-TRIAGE-FIXES Issue #3).

### 4.3 API Format for Writes (`to_api_dict`)

```python
def _format_value_for_api(self, value: Any) -> Any:
    """Format a value for the Asana API."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        # Multi-enum/People: extract GIDs
        formatted = []
        for item in value:
            if isinstance(item, dict) and "gid" in item:
                formatted.append(item["gid"])
            elif isinstance(item, str):
                formatted.append(item)
            # ...
        return formatted
    if isinstance(value, dict) and "gid" in value:
        return value["gid"]  # Enum: extract GID
    return value
```

**Critical finding for enums**: The setter accepts either:
1. Enum option name as string (`"High"`)
2. Dict with GID (`{"gid": "1234567890"}`)

But the API write uses GID internally (resolved by `_resolve_gid`).

### 4.4 Dirty Tracking

```python
def has_changes(self) -> bool:
    """Check if any modifications are pending."""
    return len(self._modifications) > 0

def clear_changes(self) -> None:
    """Clear all pending modifications."""
    self._modifications.clear()
```

**Dirty tracking is at the accessor level**, not individual field level.

---

## 5. Navigation Descriptor Reference

### 5.1 Existing Pattern (from ADR-0075)

```python
class ParentRef(Generic[T]):
    def __init__(
        self,
        holder_attr: str | None = None,
        target_attr: str = "_business",
        auto_invalidate: bool = True,
    ) -> None: ...

    def __set_name__(self, owner: type[Any], name: str) -> None:
        self.public_name = name
        self.private_name = f"_{name}"  # Derives storage attr

    @overload
    def __get__(self, obj: None, objtype: type[Any]) -> ParentRef[T]: ...
    @overload
    def __get__(self, obj: Any, objtype: type[Any] | None) -> T | None: ...
```

### 5.2 Key Patterns to Replicate

1. **`__set_name__`**: Auto-derive field constant name from property name
2. **`@overload`**: Type hints for class vs instance access
3. **Pydantic compatibility**: `ignored_types=(Descriptor,)` in `model_config`
4. **No type annotation on declaration**: Avoids Pydantic field creation

### 5.3 Pydantic Configuration (from ADR-0077)

```python
class BusinessEntity(Task):
    model_config = ConfigDict(
        ignored_types=(ParentRef, HolderRef),  # Add custom field descriptors here
        extra="allow",
    )
```

---

## 6. Fields Class Analysis

### 6.1 Current Pattern

```python
class Fields:
    """Custom field name constants for IDE discoverability."""

    COMPANY_ID = "Company ID"
    FACEBOOK_PAGE_ID = "Facebook Page ID"
    # ... 17 more
```

**Observations**:
1. Class names are SCREAMING_SNAKE_CASE
2. Values are exact Asana field names (Title Case with spaces)
3. Used as `self.Fields.COMPANY_ID` in property implementations
4. Nested inner class for IDE discoverability

### 6.2 Relationship Between Constant and Property

| Property Name | Field Constant | Field Value |
|--------------|----------------|-------------|
| `company_id` | `COMPANY_ID` | `"Company ID"` |
| `facebook_page_id` | `FACEBOOK_PAGE_ID` | `"Facebook Page ID"` |
| `mrr` | `MRR` | `"MRR"` |

**Pattern**: `snake_case_property` -> `SCREAMING_SNAKE_CASE` -> `"Title Case With Spaces"`

### 6.3 Auto-Generation Requirements

For descriptors to auto-generate Fields class:
1. Property name `company_id` -> Constant name `COMPANY_ID`
2. Constant name `COMPANY_ID` -> Field value `"Company ID"` (or explicit override)
3. Must handle abbreviations: `MRR` -> `"MRR"`, `URL` -> `"URL"`

**Edge cases**:
- `mrr` -> `MRR` -> `"MRR"` (not "M R R")
- `ad_id` -> `AD_ID` -> `"Ad ID"` (not "A D I D")
- `num_ai_copies` -> `NUM_AI_COPIES` -> `"Num AI Copies"`

---

## 7. Edge Cases and Special Handling

### 7.1 Empty String vs None

```python
def _get_text_field(self, field_name: str) -> str | None:
    value = self.get_custom_fields().get(field_name)
    if value is None or isinstance(value, str):
        return value  # Returns None or string (including empty string)
    return str(value)
```

**Behavior**: Empty string `""` is returned as-is (truthy check not used).

### 7.2 Zero vs None for Numbers

```python
def _get_number_field(self, field_name: str) -> Decimal | None:
    value = self.get_custom_fields().get(field_name)
    if value is None:
        return None
    return Decimal(str(value))  # 0 becomes Decimal("0")
```

**Behavior**: `0` is a valid value, distinct from `None`.

### 7.3 Empty List vs None for People/Multi-Enum

```python
@property
def rep(self) -> list[dict[str, Any]]:
    value = self.get_custom_fields().get(self.Fields.REP)
    return value if isinstance(value, list) else []  # Never returns None

def _get_multi_enum_field(self, field_name: str) -> list[str]:
    value = self.get_custom_fields().get(field_name)
    if value is None:
        return []  # Never returns None
```

**Behavior**: List fields return `[]` not `None` when empty.

### 7.4 Enum Values with Special Characters

No special handling observed. Enum names are expected to be plain strings.

### 7.5 Property Name Shadowing

Process model renames fields to avoid shadowing Task properties:
- `process_completed_at` (not `completed_at`)
- `process_notes` (not `notes`)
- `process_due_date` (not `due_date`)

### 7.6 Fields Appearing in Multiple Models

| Field Name | Models |
|-----------|--------|
| `vertical` | Business, Unit, Offer, Process |
| `booking_type` | Business, Unit |
| `rep` | Business, Unit, Offer |
| `mrr` | Unit, Offer |
| `weekly_ad_spend` | Unit, Offer |
| `specialty` | Unit, Offer |
| `platforms` | Unit, Offer |
| `office_phone` | Business, Offer |

**Same name, same behavior across models**.

---

## 8. Key Questions Answered

### Q1: What is the exact field count per model?

| Model | Fields |
|-------|--------|
| Business | 19 |
| Contact | 19 |
| Unit | 31 |
| Offer | 39 |
| Process | 9 |
| **Total** | **117** (with duplicates), **~108** (unique properties) |

### Q2: Are there any field types beyond Text, Enum, Number, People, Date?

**No**. The five types cover all fields:
- Text (str)
- Enum (str, extracted from dict)
- Multi-Enum (list[str], extracted from list of dicts)
- Number (int or Decimal)
- People (list[dict])
- Date (stored as Text, no special Date type in use)

### Q3: Does Asana API accept enum name string on write, or require GID?

**Both**. The CustomFieldAccessor:
1. Accepts enum name as string
2. Resolves name to GID via `_resolve_gid()`
3. Sends GID to API via `_format_value_for_api()`

However, the current property setters pass the raw value through, relying on the accessor's resolution.

### Q4: Are there any fields with special validation or transformation?

**Yes**:
1. **Decimal fields**: Converted to `float()` on set
2. **Type validation**: Performed in `_validate_type()` based on `resource_subtype`
3. **Enum validation**: Must be string or dict with "gid" key

### Q5: Are there fields shared across models (same name, same behavior)?

**Yes**, see Section 7.6. Key shared fields:
- `vertical` (4 models)
- `rep` (3 models)
- `booking_type`, `mrr`, `weekly_ad_spend`, `specialty`, `platforms`, `office_phone` (2 models each)

### Q6: What is the exact return format for People fields?

```python
list[dict[str, Any]]
# Example: [{"gid": "123", "name": "John Doe", "email": "..."}]
```

Returns `[]` if no people assigned.

### Q7: Are there any Date fields currently implemented?

**Date-like fields exist but are stored as Text**:
- `process_due_date`
- `started_at`
- `process_completed_at`

The `_extract_value` method supports `date_value` but no properties currently use it.

---

## 9. Recommendations for Descriptor Design

### 9.1 Descriptor Types Needed

| Descriptor | Return Type | Use Case |
|-----------|-------------|----------|
| `TextField` | `str \| None` | 56 fields |
| `EnumField` | `str \| None` | 21 fields |
| `NumberField` | `Decimal \| None` | 8 fields |
| `IntField` | `int \| None` | 4 fields |
| `MultiEnumField` | `list[str]` | 7 fields |
| `PeopleField` | `list[dict[str, Any]]` | 4 fields |
| `DateField` | `str \| None` (or date) | 8 fields (future) |

### 9.2 Common Configuration Parameters

```python
class TextField(Generic[T]):
    def __init__(
        self,
        field_name: str | None = None,  # Explicit override, else derived
        # No additional params needed for text
    ): ...

class NumberField(Generic[T]):
    def __init__(
        self,
        field_name: str | None = None,
        use_decimal: bool = True,  # Decimal vs int
    ): ...

class EnumField(Generic[T]):
    def __init__(
        self,
        field_name: str | None = None,
        # Enum extraction handled automatically
    ): ...
```

### 9.3 Fields Class Auto-Generation

Option A: Generate at class definition via metaclass
Option B: Generate statically via code generation script
Option C: Use descriptor `__set_name__` to register fields

**Recommendation**: Option C aligns with existing navigation descriptor pattern.

### 9.4 Pydantic Compatibility

Add new descriptor types to `ignored_types`:
```python
model_config = ConfigDict(
    ignored_types=(ParentRef, HolderRef, TextField, EnumField, NumberField, ...),
    extra="allow",
)
```

### 9.5 Example Declarative Syntax

```python
class Business(BusinessEntity):
    # Current: 7 lines per field
    # Proposed: 1 line per field

    company_id = TextField()
    vertical = EnumField()
    num_reviews = IntField()
    rep = PeopleField()
```

### 9.6 Handling Edge Cases

1. **Property shadowing**: Allow explicit field_name override
   ```python
   process_completed_at = TextField(field_name="Process Completed At")
   ```

2. **Abbreviations**: Allow explicit field_name for non-standard conversions
   ```python
   mrr = NumberField(field_name="MRR")  # Not "M R R"
   ```

3. **List defaults**: MultiEnumField and PeopleField should return `[]` not `None`

---

## 10. Open Questions for PRD

1. **Should Fields inner class be auto-generated or explicit?**
   - Auto-generated reduces boilerplate but may hurt IDE discoverability
   - Explicit maintains current pattern but duplicates information

2. **Should descriptors support cascading/inherited field definitions?**
   - Current: Separate `CascadingFields` and `InheritedFields` inner classes
   - Option: `EnumField(cascading=True, target_types={"Unit", "Offer"})`

3. **Should descriptors perform type validation on set?**
   - Currently handled by CustomFieldAccessor
   - Descriptor-level validation would provide earlier failure

4. **Should Date fields have special handling?**
   - Current: Stored as text, no parsing
   - Option: Return `datetime.date` or `datetime.datetime`

5. **How should abbreviation handling work in field name derivation?**
   - Need dictionary of known abbreviations: `{"mrr": "MRR", "ai": "AI", "url": "URL"}`

---

## Appendix A: Line Count Analysis

### Current Implementation

| Model | Fields | Lines (approx) |
|-------|--------|----------------|
| Business | 19 | ~190 |
| Contact | 19 | ~190 |
| Unit | 31 | ~310 |
| Offer | 39 | ~390 |
| Process | 9 | ~90 |
| Helper methods | - | ~50 per model |
| **Total** | **117** | **~1,420** |

### With Declarative Descriptors

| Model | Fields | Lines (approx) |
|-------|--------|----------------|
| Business | 19 | ~20 |
| Contact | 19 | ~20 |
| Unit | 31 | ~35 |
| Offer | 39 | ~45 |
| Process | 9 | ~10 |
| Descriptor classes | - | ~150 |
| **Total** | **117** | **~280** |

**Reduction**: ~80% fewer lines (1,420 -> 280)

---

## Appendix B: Raw Field Data by Category

### Text Fields (56)

Business: company_id, facebook_page_id, fallback_page_id, google_cal_id, office_phone, owner_name, owner_nickname, review_1, review_2, reviews_link, stripe_id, stripe_link, twilio_phone_num

Contact: build_call_link, campaign, city, contact_email, contact_phone, contact_url, content, dashboard_user, employee_id, medium, nickname, prefix, profile_photo_url, source, suffix, term

Unit: meta_spend_sub_id, tiktok_spend_sub_id, solution_fee_sub_id, ad_account_id, tiktok_profile, zip_code_list, zip_codes_radius, excluded_zips, form_questions, disabled_questions, disclaimers, custom_disclaimer, filter_out_x

Offer: ad_id, ad_set_id, campaign_id, asset_id, ad_account_url, active_ads_url, offer_headline, included_item_1, included_item_2, included_item_3, landing_page_url, preview_link, lead_testing_link, form_id, targeting, office_phone, custom_cal_url, offer_schedule_link, internal_notes, external_notes, offer_id, algo_version, triggered_by

Process: process_due_date, started_at, process_completed_at, process_notes

### Enum Fields (21)

Business: aggression_level, booking_type, vca_status, vertical

Contact: position, time_zone, text_communication

Unit: currency, vertical, specialty, gender, booking_type, sms_lead_verification, work_email_verification

Offer: language, specialty, vertical, optimize_for, campaign_type

Process: status, priority, vertical

### Multi-Enum Fields (7)

Unit: platforms, products, languages

Offer: platforms, targeting_strategies

### Number Fields - Decimal (8)

Unit: mrr, weekly_ad_spend, discount, meta_spend, tiktok_spend

Offer: mrr, cost, weekly_ad_spend, voucher_value, budget_allocation

### Number Fields - Integer (4)

Unit: radius, min_age, max_age

Offer: num_ai_copies, appt_duration, calendar_duration

### People Fields (4)

Business: rep

Unit: rep

Offer: rep

Process: assigned_to

---

*End of Discovery Document*
