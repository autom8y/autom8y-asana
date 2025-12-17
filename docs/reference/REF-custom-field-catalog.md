# Reference: Custom Field Catalog

> Extracted from: DISCOVERY-PATTERNS-A-CUSTOM-FIELDS.md (Section 1)
> Date: 2025-12-17
> Related: PRD-PATTERNS-A.md, TDD-PATTERNS-A.md

---

## Summary Statistics

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

---

## Distribution by Model

| Model | Text | Enum | Multi-Enum | Number | People | Total |
|-------|------|------|------------|--------|--------|-------|
| Business | 13 | 4 | 0 | 1 | 1 | 19 |
| Contact | 16 | 3 | 0 | 0 | 0 | 19 |
| Unit | 13 | 8 | 3 | 8 | 1 | 31 |
| Offer | 20 | 5 | 2 | 8 | 1 | 36 |
| Process | 4 | 3 | 0 | 0 | 1 | 8 |
| **Total** | **66** | **23** | **5** | **17** | **4** | **113** |

---

## Complete Field Catalog by Model

### Business Model (19 fields)

| Property Name | Field Name (Constant) | Field Type | Return Type |
|--------------|----------------------|------------|-------------|
| `company_id` | COMPANY_ID | Text | `str \| None` |
| `facebook_page_id` | FACEBOOK_PAGE_ID | Text | `str \| None` |
| `fallback_page_id` | FALLBACK_PAGE_ID | Text | `str \| None` |
| `google_cal_id` | GOOGLE_CAL_ID | Text | `str \| None` |
| `office_phone` | OFFICE_PHONE | Text | `str \| None` |
| `owner_name` | OWNER_NAME | Text | `str \| None` |
| `owner_nickname` | OWNER_NICKNAME | Text | `str \| None` |
| `review_1` | REVIEW_1 | Text | `str \| None` |
| `review_2` | REVIEW_2 | Text | `str \| None` |
| `reviews_link` | REVIEWS_LINK | Text | `str \| None` |
| `stripe_id` | STRIPE_ID | Text | `str \| None` |
| `stripe_link` | STRIPE_LINK | Text | `str \| None` |
| `twilio_phone_num` | TWILIO_PHONE_NUM | Text | `str \| None` |
| `num_reviews` | NUM_REVIEWS | Number | `int \| None` |
| `aggression_level` | AGGRESSION_LEVEL | Enum | `str \| None` |
| `booking_type` | BOOKING_TYPE | Enum | `str \| None` |
| `vca_status` | VCA_STATUS | Enum | `str \| None` |
| `vertical` | VERTICAL | Enum | `str \| None` |
| `rep` | REP | People | `list[dict[str, Any]]` |

---

### Contact Model (19 fields)

| Property Name | Field Name (Constant) | Field Type | Return Type |
|--------------|----------------------|------------|-------------|
| `build_call_link` | BUILD_CALL_LINK | Text | `str \| None` |
| `campaign` | CAMPAIGN | Text | `str \| None` |
| `city` | CITY | Text | `str \| None` |
| `contact_email` | CONTACT_EMAIL | Text | `str \| None` |
| `contact_phone` | CONTACT_PHONE | Text | `str \| None` |
| `contact_url` | CONTACT_URL | Text | `str \| None` |
| `content` | CONTENT | Text | `str \| None` |
| `dashboard_user` | DASHBOARD_USER | Text | `str \| None` |
| `employee_id` | EMPLOYEE_ID | Text | `str \| None` |
| `medium` | MEDIUM | Text | `str \| None` |
| `nickname` | NICKNAME | Text | `str \| None` |
| `prefix` | PREFIX | Text | `str \| None` |
| `profile_photo_url` | PROFILE_PHOTO_URL | Text | `str \| None` |
| `source` | SOURCE | Text | `str \| None` |
| `suffix` | SUFFIX | Text | `str \| None` |
| `term` | TERM | Text | `str \| None` |
| `position` | POSITION | Enum | `str \| None` |
| `time_zone` | TIME_ZONE | Enum | `str \| None` |
| `text_communication` | TEXT_COMMUNICATION | Enum | `str \| None` |

---

### Unit Model (31 fields)

| Property Name | Field Name (Constant) | Field Type | Return Type |
|--------------|----------------------|------------|-------------|
| `mrr` | MRR | Number | `Decimal \| None` |
| `weekly_ad_spend` | WEEKLY_AD_SPEND | Number | `Decimal \| None` |
| `discount` | DISCOUNT | Number | `Decimal \| None` |
| `meta_spend` | META_SPEND | Number | `Decimal \| None` |
| `tiktok_spend` | TIKTOK_SPEND | Number | `Decimal \| None` |
| `radius` | RADIUS | Number | `int \| None` |
| `min_age` | MIN_AGE | Number | `int \| None` |
| `max_age` | MAX_AGE | Number | `int \| None` |
| `currency` | CURRENCY | Enum | `str \| None` |
| `vertical` | VERTICAL | Enum | `str \| None` |
| `specialty` | SPECIALTY | Enum | `str \| None` |
| `gender` | GENDER | Enum | `str \| None` |
| `booking_type` | BOOKING_TYPE | Enum | `str \| None` |
| `sms_lead_verification` | SMS_LEAD_VERIFICATION | Enum | `str \| None` |
| `work_email_verification` | WORK_EMAIL_VERIFICATION | Enum | `str \| None` |
| `platforms` | PLATFORMS | Multi-Enum | `list[str]` |
| `products` | PRODUCTS | Multi-Enum | `list[str]` |
| `languages` | LANGUAGES | Multi-Enum | `list[str]` |
| `meta_spend_sub_id` | META_SPEND_SUB_ID | Text | `str \| None` |
| `tiktok_spend_sub_id` | TIKTOK_SPEND_SUB_ID | Text | `str \| None` |
| `solution_fee_sub_id` | SOLUTION_FEE_SUB_ID | Text | `str \| None` |
| `ad_account_id` | AD_ACCOUNT_ID | Text | `str \| None` |
| `tiktok_profile` | TIKTOK_PROFILE | Text | `str \| None` |
| `zip_code_list` | ZIP_CODE_LIST | Text | `str \| None` |
| `zip_codes_radius` | ZIP_CODES_RADIUS | Text | `str \| None` |
| `excluded_zips` | EXCLUDED_ZIPS | Text | `str \| None` |
| `form_questions` | FORM_QUESTIONS | Text | `str \| None` |
| `disabled_questions` | DISABLED_QUESTIONS | Text | `str \| None` |
| `disclaimers` | DISCLAIMERS | Text | `str \| None` |
| `custom_disclaimer` | CUSTOM_DISCLAIMER | Text | `str \| None` |
| `rep` | REP | People | `list[dict[str, Any]]` |

---

### Offer Model (39 fields)

| Property Name | Field Name (Constant) | Field Type | Return Type |
|--------------|----------------------|------------|-------------|
| `mrr` | MRR | Number | `Decimal \| None` |
| `cost` | COST | Number | `Decimal \| None` |
| `weekly_ad_spend` | WEEKLY_AD_SPEND | Number | `Decimal \| None` |
| `voucher_value` | VOUCHER_VALUE | Number | `Decimal \| None` |
| `budget_allocation` | BUDGET_ALLOCATION | Number | `Decimal \| None` |
| `num_ai_copies` | NUM_AI_COPIES | Number | `int \| None` |
| `appt_duration` | APPT_DURATION | Number | `int \| None` |
| `calendar_duration` | CALENDAR_DURATION | Number | `int \| None` |
| `language` | LANGUAGE | Enum | `str \| None` |
| `specialty` | SPECIALTY | Enum | `str \| None` |
| `vertical` | VERTICAL | Enum | `str \| None` |
| `optimize_for` | OPTIMIZE_FOR | Enum | `str \| None` |
| `campaign_type` | CAMPAIGN_TYPE | Enum | `str \| None` |
| `platforms` | PLATFORMS | Multi-Enum | `list[str]` |
| `targeting_strategies` | TARGETING_STRATEGIES | Multi-Enum | `list[str]` |
| `ad_id` | AD_ID | Text | `str \| None` |
| `ad_set_id` | AD_SET_ID | Text | `str \| None` |
| `campaign_id` | CAMPAIGN_ID | Text | `str \| None` |
| `asset_id` | ASSET_ID | Text | `str \| None` |
| `ad_account_url` | AD_ACCOUNT_URL | Text | `str \| None` |
| `active_ads_url` | ACTIVE_ADS_URL | Text | `str \| None` |
| `offer_headline` | OFFER_HEADLINE | Text | `str \| None` |
| `included_item_1` | INCLUDED_ITEM_1 | Text | `str \| None` |
| `included_item_2` | INCLUDED_ITEM_2 | Text | `str \| None` |
| `included_item_3` | INCLUDED_ITEM_3 | Text | `str \| None` |
| `landing_page_url` | LANDING_PAGE_URL | Text | `str \| None` |
| `preview_link` | PREVIEW_LINK | Text | `str \| None` |
| `lead_testing_link` | LEAD_TESTING_LINK | Text | `str \| None` |
| `form_id` | FORM_ID | Text | `str \| None` |
| `targeting` | TARGETING | Text | `str \| None` |
| `office_phone` | OFFICE_PHONE | Text | `str \| None` |
| `custom_cal_url` | CUSTOM_CAL_URL | Text | `str \| None` |
| `offer_schedule_link` | OFFER_SCHEDULE_LINK | Text | `str \| None` |
| `internal_notes` | INTERNAL_NOTES | Text | `str \| None` |
| `external_notes` | EXTERNAL_NOTES | Text | `str \| None` |
| `offer_id` | OFFER_ID | Text | `str \| None` |
| `algo_version` | ALGO_VERSION | Text | `str \| None` |
| `triggered_by` | TRIGGERED_BY | Text | `str \| None` |
| `rep` | REP | People | `list[dict[str, Any]]` |

---

### Process Model (9 fields)

| Property Name | Field Name (Constant) | Field Type | Return Type |
|--------------|----------------------|------------|-------------|
| `status` | STATUS | Enum | `str \| None` |
| `priority` | PRIORITY | Enum | `str \| None` |
| `vertical` | VERTICAL | Enum | `str \| None` |
| `process_due_date` | DUE_DATE | Text | `str \| None` |
| `started_at` | STARTED_AT | Text | `str \| None` |
| `process_completed_at` | PROCESS_COMPLETED_AT | Text | `str \| None` |
| `process_notes` | PROCESS_NOTES | Text | `str \| None` |
| `assigned_to` | ASSIGNED_TO | People | `list[dict[str, Any]]` |

---

## Fields Shared Across Models

| Field Name | Models |
|-----------|--------|
| `vertical` | Business, Unit, Offer, Process |
| `rep` | Business, Unit, Offer |
| `booking_type` | Business, Unit |
| `mrr` | Unit, Offer |
| `weekly_ad_spend` | Unit, Offer |
| `specialty` | Unit, Offer |
| `platforms` | Unit, Offer |
| `office_phone` | Business, Offer |

---

*Reference document. Source: .archive/discovery/DISCOVERY-PATTERNS-A-CUSTOM-FIELDS.md*
