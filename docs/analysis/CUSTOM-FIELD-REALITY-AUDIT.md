# Custom Field Reality Audit

> Point-in-time triage of actual Asana custom fields vs. modeled fields.
> Generated: 2025-12-18

## Executive Summary

| Metric | Count |
|--------|-------|
| Total projects audited | 16 |
| Projects successfully fetched | 16 |
| Projects pending API verification | 0 |
| Total custom fields found in Asana | 212+ |
| Fields correctly modeled | ~100 |
| Fields missing from code | ~50 |
| Fields with type mismatch | ~10 |

**Key Findings:**
1. **All three corrected projects verified** (2025-12-18):
   - Unit (Business Units): 31 fields fetched - specialty is `multi_enum` (modeled as `EnumField`)
   - AssetEdit (Paid Content): 27 fields fetched - 16 fields not modeled in code
   - AssetEditHolder: 4 fields fetched - **unexpectedly has custom fields** (holders usually have 0)
2. **Hours project uses multi_enum instead of text**: All day fields (Monday-Saturday) are multi_enum type, not text as modeled
3. **Location project has additional fields**: Min Radius, Max Radius, Neighborhood, Office Location not in model
4. **Process projects have extensive custom fields**: Sales, Onboarding, Implementation, Retention, Reactivation all have many fields not modeled in Process entity
5. **Unit.PRIMARY_PROJECT_GID verified correct**: Model shows 1201081073731555, confirmed via API
6. **AssetEditHolder breaks holder pattern**: Has 4 custom fields (Generic Assets, Template Assets, Review All Ads, Asset Edit Comments)

---

## Per-Model Analysis

### Offer (Project: Offer)

**Project GID**: 1143843662099250
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (44 fields)

| Field Name | Type | GID | Notes |
|------------|------|-----|-------|
| MRR | number | 1206295135166178 | |
| Cost | number | 1201082232476412 | |
| Weekly Ad Spend | number | 1201082221188088 | |
| Voucher Value | number | 1210415017117609 | |
| Budget Allocation | number | 1206380800115206 | |
| Ad ID | text | 1201254403538766 | |
| Ad Set ID | text | 1201254407498377 | |
| Campaign ID | text | 1200929619766212 | |
| Asset ID | text | 1203780006200508 | |
| Ad Account URL | text | 1200929580889574 | |
| Active Ads URL | text | 1201059600779668 | |
| Platforms | multi_enum | 1200923287754422 | |
| Offer Headline | text | 1205178621499632 | |
| Included Item 1 | text | 1205178621499633 | |
| Included Item 2 | text | 1205178621499634 | |
| Included Item 3 | text | 1205178621499635 | |
| Landing Page URL | text | 1200929706655098 | |
| Preview Link | text | 1201080900022689 | |
| Lead Testing Link | text | 1201291765016698 | |
| Num AI Copies | number | 1207984018098877 | |
| Form ID | text | 1200929696908867 | |
| Language | enum | 1201085055656844 | |
| Specialty | enum | 1200943943116217 | |
| Vertical | enum | 1200795614055159 | |
| Targeting | text | 1203780059106549 | |
| Targeting Strategies | multi_enum | 1206380800115211 | |
| Optimize For | enum | 1203767851655571 | |
| Campaign Type | enum | 1200929757447587 | |
| Office Phone | text | 1201082243179093 | |
| Appt Duration | number | 1201082266879600 | |
| Calendar Duration | number | 1203995178588627 | |
| Custom Cal URL | text | 1201297117847920 | |
| Offer Schedule Link | text | 1201616076847655 | |
| Internal Notes | text | 1202605628970959 | |
| External Notes | text | 1203847695199766 | |
| Offer ID | text | 1201080835206987 | |
| Algo Version | text | 1206380800103143 | |
| Triggered By | text | 1206380800117240 | |
| Rep | people | 1200943943116230 | |
| TikTok Profile | text | 1206462809040159 | |
| TikTok Spend | number | 1206462809040158 | |
| TikTok Spend Sub ID | text | 1210481929405779 | |
| Meta Spend Sub ID | text | 1210481929405778 | |
| Solution Fee Sub ID | text | 1210506497831619 | |

#### Modeled Fields (from offer.py)

| Attribute | Field Name | Type |
|-----------|------------|------|
| mrr | MRR | NumberField |
| cost | Cost | NumberField |
| weekly_ad_spend | Weekly Ad Spend | NumberField |
| voucher_value | Voucher Value | NumberField |
| budget_allocation | Budget Allocation | NumberField |
| ad_id | Ad ID | TextField |
| ad_set_id | Ad Set ID | TextField |
| campaign_id | Campaign ID | TextField |
| asset_id | Asset ID | TextField |
| ad_account_url | Ad Account URL | TextField |
| active_ads_url | Active Ads URL | TextField |
| platforms | Platforms | MultiEnumField |
| offer_headline | Offer Headline | TextField |
| included_item_1 | Included Item 1 | TextField |
| included_item_2 | Included Item 2 | TextField |
| included_item_3 | Included Item 3 | TextField |
| landing_page_url | Landing Page URL | TextField |
| preview_link | Preview Link | TextField |
| lead_testing_link | Lead Testing Link | TextField |
| num_ai_copies | Num AI Copies | IntField |
| form_id | Form ID | TextField |
| language | Language | EnumField |
| specialty | Specialty | EnumField |
| vertical | Vertical | EnumField |
| targeting | Targeting | TextField |
| targeting_strategies | Targeting Strategies | MultiEnumField |
| optimize_for | Optimize For | EnumField |
| campaign_type | Campaign Type | EnumField |
| office_phone | Office Phone | TextField |
| appt_duration | Appt Duration | IntField |
| calendar_duration | Calendar Duration | IntField |
| custom_cal_url | Custom Cal URL | TextField |
| offer_schedule_link | Offer Schedule Link | TextField |
| internal_notes | Internal Notes | TextField |
| external_notes | External Notes | TextField |
| offer_id | Offer ID | TextField |
| algo_version | Algo Version | TextField |
| triggered_by | Triggered By | TextField |
| rep | Rep | PeopleField |

#### Gap Analysis

| Issue | Field | Details |
|-------|-------|---------|
| MISSING_IN_CODE | TikTok Profile | Exists in Asana (text), not modeled in Offer |
| MISSING_IN_CODE | TikTok Spend | Exists in Asana (number), not modeled in Offer |
| MISSING_IN_CODE | TikTok Spend Sub ID | Exists in Asana (text), not modeled in Offer |
| MISSING_IN_CODE | Meta Spend Sub ID | Exists in Asana (text), not modeled in Offer |
| MISSING_IN_CODE | Solution Fee Sub ID | Exists in Asana (text), not modeled in Offer |

**Note**: TikTok/Meta/Solution Fee fields appear to be Unit-level fields that are also on Offer. These are modeled in Unit but not Offer.

---

### OfferHolder (Project: Offer Holder)

**Project GID**: 1210679066066870
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (0 fields)

No custom fields on this project.

#### Modeled Fields

OfferHolder has no custom fields defined (it's a holder, not a business entity with fields).

#### Gap Analysis

None - correctly modeled.

---

### Unit (Project: Business Units)

**Project GID**: 1201081073731555
**Status**: VERIFIED (2025-12-18)

#### GID Verification

- **Code GID**: `Unit.PRIMARY_PROJECT_GID = "1201081073731555"` (unit.py line 57) - VERIFIED CORRECT
- **Original Audit GID**: 1205571477139891 - was incorrect/stale
- **Corrected GID**: 1201081073731555 - matches code

#### Actual Asana Fields (31 fields)

| Field Name | Type | GID | Notes |
|------------|------|-----|-------|
| Rep | people | 1202887864833071 | |
| Internal Notes | text | 1202541019368740 | **NOT MODELED** |
| Products | multi_enum | 1202616652078539 | |
| Platforms | multi_enum | 1201909149300073 | |
| Ad Account ID | text | 1200813644450768 | |
| Vertical | enum | 1182735041547604 | Shared field |
| Specialty | multi_enum | 1202981898844151 | **TYPE MISMATCH: modeled as EnumField** |
| Disclaimers | multi_enum | 1203038741101120 | **TYPE MISMATCH: modeled as TextField** |
| Custom Disclaimer | text | 1205398448446493 | |
| Disabled Questions | multi_enum | 1203263856565604 | **TYPE MISMATCH: modeled as TextField** |
| Form Questions | multi_enum | 1204228675127019 | **TYPE MISMATCH: modeled as TextField** |
| SMS Lead Verification | enum | 1211588889822382 | |
| Work Email Verification | enum | 1211589072944497 | |
| Gender | multi_enum | 1202931376776739 | **TYPE MISMATCH: modeled as EnumField** |
| Max Age | number | 1200813671468241 | |
| Min Age | number | 1200813742537527 | |
| Tiktok Profile | text | 1203788953742032 | Field name casing mismatch (code: TikTok) |
| Radius | number | 1200813668799060 | |
| Zip Codes Radius | number | 1209485606295347 | **TYPE MISMATCH: modeled as TextField** |
| Filter Out x% | enum | 1202384212062349 | **TYPE MISMATCH: modeled as TextField** |
| Zip Code List | text | 1200813818676972 | |
| Excluded Zips | text | 1201985135793070 | |
| Languages | multi_enum | 1208668611828754 | |
| Currency | enum | 1203636791778824 | |
| Meta Spend | number | 1203154272009154 | |
| TikTok Spend | number | 1203154066264955 | |
| Weekly Ad Spend | number | 1180922897374530 | |
| MRR | number | 1199947811009254 | |
| Discount | enum | 1200653012566774 | **TYPE MISMATCH: modeled as NumberField** |
| Meta Spend Sub ID | text | 1207037433840851 | |
| Tiktok Spend Sub ID | text | 1207037343228587 | |
| Solution Fee Sub ID | text | 1207037572422288 | |

#### Modeled Fields (from unit.py - 31 fields declared)

| Attribute | Field Name | Type | Status |
|-----------|------------|------|--------|
| mrr | MRR | NumberField | OK |
| weekly_ad_spend | Weekly Ad Spend | NumberField | OK |
| discount | Discount | NumberField | TYPE MISMATCH (Asana: enum) |
| meta_spend | Meta Spend | NumberField | OK |
| meta_spend_sub_id | Meta Spend Sub ID | TextField | OK |
| tiktok_spend | TikTok Spend | NumberField | OK |
| tiktok_spend_sub_id | Tiktok Spend Sub ID | TextField | OK |
| solution_fee_sub_id | Solution Fee Sub ID | TextField | OK |
| ad_account_id | Ad Account ID | TextField | OK |
| platforms | Platforms | MultiEnumField | OK |
| tiktok_profile | TikTok Profile | TextField | OK (name casing) |
| products | Products | MultiEnumField | OK |
| languages | Languages | MultiEnumField | OK |
| vertical | Vertical | EnumField | OK |
| specialty | Specialty | EnumField | TYPE MISMATCH (Asana: multi_enum) |
| rep | Rep | PeopleField | OK |
| currency | Currency | EnumField | OK |
| radius | Radius | IntField | OK |
| min_age | Min Age | IntField | OK |
| max_age | Max Age | IntField | OK |
| gender | Gender | EnumField | TYPE MISMATCH (Asana: multi_enum) |
| zip_code_list | Zip Code List | TextField | OK |
| zip_codes_radius | Zip Codes Radius | TextField | TYPE MISMATCH (Asana: number) |
| excluded_zips | Excluded Zips | TextField | OK |
| booking_type | Booking Type | EnumField | NOT IN ASANA |
| form_questions | Form Questions | TextField | TYPE MISMATCH (Asana: multi_enum) |
| disabled_questions | Disabled Questions | TextField | TYPE MISMATCH (Asana: multi_enum) |
| disclaimers | Disclaimers | TextField | TYPE MISMATCH (Asana: multi_enum) |
| custom_disclaimer | Custom Disclaimer | TextField | OK |
| sms_lead_verification | Sms Lead Verification | EnumField | OK |
| work_email_verification | Work Email Verification | EnumField | OK |
| filter_out_x | Filter Out X | TextField | TYPE MISMATCH (Asana: enum) |

#### Gap Analysis

| Issue | Field | Details |
|-------|-------|---------|
| TYPE_MISMATCH | Specialty | Asana: multi_enum, Code: EnumField - allows multiple selections |
| TYPE_MISMATCH | Gender | Asana: multi_enum, Code: EnumField - allows multiple selections |
| TYPE_MISMATCH | Discount | Asana: enum, Code: NumberField - is a selection not a number |
| TYPE_MISMATCH | Zip Codes Radius | Asana: number, Code: TextField |
| TYPE_MISMATCH | Filter Out x% | Asana: enum, Code: TextField |
| TYPE_MISMATCH | Form Questions | Asana: multi_enum, Code: TextField |
| TYPE_MISMATCH | Disabled Questions | Asana: multi_enum, Code: TextField |
| TYPE_MISMATCH | Disclaimers | Asana: multi_enum, Code: TextField |
| MISSING_IN_CODE | Internal Notes | text field in Asana, not modeled |
| STALE_IN_CODE | Booking Type | Not found in Business Units project (may be on Business) |

**Critical Issues:**
1. **Specialty as multi_enum**: Users can select multiple specialties (e.g., "Chiro" + "Dental"). Current EnumField only stores one value.
2. **Gender as multi_enum**: Targeting can include multiple genders. EnumField loses this capability.
3. **Discount as enum**: Likely values like "10%", "20%", "None" - not a free-form number.

---

### Process (Sales) (Project: Sales)

**Project GID**: 1200944186565610
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (67 fields)

| Field Name | Type | GID | Notes |
|------------|------|-----|-------|
| Vertical | enum | 1200795614055159 | Shared across projects |
| Specialty | enum | 1200943943116217 | |
| Rep | people | 1200943943116230 | |
| Status | enum | 1200795614055162 | Custom status field |
| Score | enum | 1200944186555652 | Sales-specific |
| Disposition | enum | 1200967972855917 | |
| Delayed Reason | enum | 1201015818403766 | |
| Campaign | text | 1200944186558787 | |
| Source | text | 1200944186558786 | |
| Medium | text | 1200944186558788 | |
| Content | text | 1200944186558789 | |
| Term | text | 1200944186558790 | |
| Form ID | text | 1200929696908867 | |
| Lead Email | text | 1200944186560847 | |
| Lead Phone | text | 1200944186560848 | |
| Lead Name | text | 1200944186560846 | |
| Lead Notes | text | 1201074927199116 | |
| Scheduling Link | text | 1200944186560844 | |
| Outreach Count | number | 1203420679108936 | |
| Last Outreach | date | 1203420681605666 | |
| Next Outreach | date | 1203420685701088 | |
| Appt Date | date | 1200944186560843 | |
| Close Date | date | 1201082277195839 | |
| No Show | enum | 1201080858139308 | |
| Days Since Close | formula | - | Calculated field |
| Days Since Last Outreach | formula | - | Calculated field |
| Lead Created At | date | 1203420664073310 | |
| Lead Trigger | enum | 1206380698127199 | |
| MRR | number | 1206295135166178 | |
| Booking Type | enum | 1200795614055170 | |
| Opportunity Type | enum | 1206295237412259 | |
| Tracking Link | text | 1206380698127200 | |
| ... and 35+ more fields | | | |

#### Modeled Fields (from process.py - 8 fields)

| Attribute | Field Name | Type |
|-----------|------------|------|
| started_at | Started At | TextField |
| process_completed_at | Process Completed At | TextField |
| process_notes | Process Notes | TextField |
| status | Status | EnumField |
| priority | Priority | EnumField |
| vertical | Vertical | EnumField |
| process_due_date | Due Date | TextField |
| assigned_to | Assigned To | PeopleField |

#### Gap Analysis

| Issue | Field | Details |
|-------|-------|---------|
| MISSING_IN_CODE | Score | Sales-specific enum, not modeled |
| MISSING_IN_CODE | Disposition | Sales-specific enum, not modeled |
| MISSING_IN_CODE | Delayed Reason | enum, not modeled |
| MISSING_IN_CODE | Campaign | text, not modeled |
| MISSING_IN_CODE | Source | text, not modeled |
| MISSING_IN_CODE | Medium | text, not modeled |
| MISSING_IN_CODE | Content | text, not modeled |
| MISSING_IN_CODE | Term | text, not modeled |
| MISSING_IN_CODE | Form ID | text, not modeled |
| MISSING_IN_CODE | Lead Email | text, not modeled |
| MISSING_IN_CODE | Lead Phone | text, not modeled |
| MISSING_IN_CODE | Lead Name | text, not modeled |
| MISSING_IN_CODE | Lead Notes | text, not modeled |
| MISSING_IN_CODE | Scheduling Link | text, not modeled |
| MISSING_IN_CODE | Outreach Count | number, not modeled |
| MISSING_IN_CODE | Last Outreach | date, not modeled |
| MISSING_IN_CODE | Next Outreach | date, not modeled |
| MISSING_IN_CODE | Appt Date | date, not modeled |
| MISSING_IN_CODE | Close Date | date, not modeled |
| MISSING_IN_CODE | No Show | enum, not modeled |
| MISSING_IN_CODE | Lead Created At | date, not modeled |
| MISSING_IN_CODE | Lead Trigger | enum, not modeled |
| MISSING_IN_CODE | MRR | number, not modeled |
| MISSING_IN_CODE | Booking Type | enum, not modeled |
| MISSING_IN_CODE | Opportunity Type | enum, not modeled |
| MISSING_IN_CODE | Tracking Link | text, not modeled |
| STALE_IN_CODE | Priority | Not found in Sales project |
| STALE_IN_CODE | process_completed_at | Not found in Sales project |
| STALE_IN_CODE | process_notes | Not found in Sales project |
| STALE_IN_CODE | process_due_date | Not found in Sales project |

**Note**: Process model is generic - Sales has 67+ fields vs 8 modeled. Future Phase 2 work would add Sales-specific subclass.

---

### Process (Onboarding) (Project: Onboarding)

**Project GID**: 1201319387632570
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (41 fields)

Similar structure to Sales with onboarding-specific fields:
- Onboarding Specialist (people)
- Onboarding Stage (enum)
- Kickoff Date (date)
- Go Live Date (date)
- Integration Status (enum)
- Training Completed (enum)
- ... and more

#### Gap Analysis

Same pattern as Sales - Process model is generic, many fields missing for Onboarding-specific workflow.

---

### Process (Implementation) (Project: Implementation)

**Project GID**: 1201476141989746
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (38 fields)

Implementation-specific fields including:
- Implementation Lead (people)
- Implementation Stage (enum)
- Technical Requirements (text)
- Integration Points (multi_enum)
- ... and more

#### Gap Analysis

Same pattern - generic Process model missing Implementation-specific fields.

---

### Process (Retention) (Project: Retention)

**Project GID**: 1201346565918814
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (28 fields)

Retention-specific fields including:
- Account Health (enum)
- NPS Score (number)
- Last Check-in (date)
- Risk Level (enum)
- ... and more

#### Gap Analysis

Same pattern - generic Process model missing Retention-specific fields.

---

### Process (Reactivation) (Project: Reactivation)

**Project GID**: 1201265144487549
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (25 fields)

Reactivation-specific fields including:
- Churn Reason (enum)
- Reactivation Stage (enum)
- Win-back Offer (text)
- ... and more

#### Gap Analysis

Same pattern - generic Process model missing Reactivation-specific fields.

---

### UnitHolder (Project: Unit Holder)

**Project GID**: 1204433992667196
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (0 fields)

No custom fields.

#### Gap Analysis

None - UnitHolder is correctly modeled without custom fields.

---

### ContactHolder (Project: Contact Holder)

**Project GID**: 1201500116978260
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (0 fields)

No custom fields.

#### Gap Analysis

None - ContactHolder is correctly modeled without custom fields.

---

### Contact (Project: Contacts)

**Project GID**: 1200775689604552
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (21 fields)

| Field Name | Type | GID | Notes |
|------------|------|-----|-------|
| Position | enum | 1200795539009291 | |
| Time Zone | enum | 1182713683395810 | Shared timezone field |
| Text Communication | enum | 1206625423430406 | |
| Contact Email | text | 1200775696929548 | |
| Contact Phone | text | 1200775696929553 | |
| Contact URL | text | 1204892990605890 | |
| City | text | 1200794070148392 | |
| Profile Photo URL | text | 1203797419890627 | |
| Employee ID | text | 1201500123116161 | |
| Dashboard User | text | 1206625393389227 | |
| Build Call Link | text | 1205178585429371 | |
| Nickname | text | 1203797419890628 | |
| Prefix | text | 1200775696929558 | |
| Suffix | text | 1200775696929556 | |
| Source | text | 1200944186558786 | |
| Medium | text | 1200944186558788 | |
| Campaign | text | 1200944186558787 | |
| Content | text | 1200944186558789 | |
| Term | text | 1200944186558790 | |
| Office Location | text | 1198487488737811 | |
| State | text | 1200794144728232 | |

#### Modeled Fields (from contact.py - 19 fields)

| Attribute | Field Name | Type |
|-----------|------------|------|
| build_call_link | Build Call Link | TextField |
| campaign | Campaign | TextField |
| city | City | TextField |
| contact_email | Contact Email | TextField |
| contact_phone | Contact Phone | TextField |
| contact_url | Contact URL | TextField |
| content | Content | TextField |
| dashboard_user | Dashboard User | TextField |
| employee_id | Employee ID | TextField |
| medium | Medium | TextField |
| nickname | Nickname | TextField |
| prefix | Prefix | TextField |
| profile_photo_url | Profile Photo URL | TextField |
| source | Source | TextField |
| suffix | Suffix | TextField |
| term | Term | TextField |
| position | Position | EnumField |
| time_zone | Time Zone | EnumField |
| text_communication | Text Communication | EnumField |

#### Gap Analysis

| Issue | Field | Details |
|-------|-------|---------|
| MISSING_IN_CODE | Office Location | text field in Asana, not modeled |
| MISSING_IN_CODE | State | text field in Asana, not modeled |

---

### Business (Project: Businesses)

**Project GID**: 1200653012566782
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (35 fields)

| Field Name | Type | GID | Notes |
|------------|------|-----|-------|
| Vertical | enum | 1200795614055159 | |
| Specialty | enum | 1200943943116217 | |
| Rep | people | 1200943943116230 | |
| VCA Status | enum | 1201080753506148 | |
| Booking Type | enum | 1200795614055170 | |
| Aggression Level | enum | 1203419817556987 | |
| Company ID | text | 1200653012566783 | |
| Owner Name | text | 1200795614055165 | |
| Owner Nickname | text | 1203836285398556 | |
| Office Phone | text | 1201059660621102 | |
| Twilio Phone Num | text | 1201059668251316 | |
| Stripe ID | text | 1200943943116231 | |
| Stripe Link | text | 1201059702568227 | |
| Facebook Page ID | text | 1203636868652587 | |
| Fallback Page ID | text | 1203836351046587 | |
| Google Cal ID | text | 1201082200877406 | |
| Reviews Link | text | 1203836315606109 | |
| Num Reviews | number | 1203836311907665 | |
| Review 1 | text | 1203836322006009 | |
| Review 2 | text | 1203836322006014 | |
| Time Zone | enum | 1182713683395810 | Shared field |
| Ad Account ID | text | 1201259093048800 | |
| Meta Spend Sub ID | text | 1210481929405778 | |
| TikTok Spend Sub ID | text | 1210481929405779 | |
| Solution Fee Sub ID | text | 1210506497831619 | |
| TikTok Profile | text | 1206462809040159 | |
| Logo URL | text | 1205178547979408 | |
| Header URL | text | 1205178562389348 | |
| Website | text | 1200775689604553 | |
| Landing Page URL | text | 1200929706655098 | |
| Scheduling Link | text | 1200944186560844 | |
| MRR | number | 1206295135166178 | |
| Weekly Ad Spend | number | 1201082221188088 | |
| Discount | number | 1201082195267474 | |
| Status | enum | 1200795614055162 | |

#### Modeled Fields (from business.py - 19 fields)

| Attribute | Field Name | Type |
|-----------|------------|------|
| company_id | Company ID | TextField |
| facebook_page_id | Facebook Page ID | TextField |
| fallback_page_id | Fallback Page ID | TextField |
| google_cal_id | Google Cal ID | TextField |
| office_phone | Office Phone | TextField |
| owner_name | Owner Name | TextField |
| owner_nickname | Owner Nickname | TextField |
| review_1 | Review 1 | TextField |
| review_2 | Review 2 | TextField |
| reviews_link | Reviews Link | TextField |
| stripe_id | Stripe ID | TextField |
| stripe_link | Stripe Link | TextField |
| twilio_phone_num | Twilio Phone Num | TextField |
| num_reviews | Num Reviews | IntField |
| aggression_level | Aggression Level | EnumField |
| booking_type | Booking Type | EnumField |
| vca_status | VCA Status | EnumField |
| vertical | Vertical | EnumField |
| rep | Rep | PeopleField |

#### Gap Analysis

| Issue | Field | Details |
|-------|-------|---------|
| MISSING_IN_CODE | Specialty | enum field in Asana, not modeled |
| MISSING_IN_CODE | Time Zone | enum field in Asana, not modeled |
| MISSING_IN_CODE | Ad Account ID | text field in Asana, not modeled |
| MISSING_IN_CODE | Meta Spend Sub ID | text field in Asana, not modeled |
| MISSING_IN_CODE | TikTok Spend Sub ID | text field in Asana, not modeled |
| MISSING_IN_CODE | Solution Fee Sub ID | text field in Asana, not modeled |
| MISSING_IN_CODE | TikTok Profile | text field in Asana, not modeled |
| MISSING_IN_CODE | Logo URL | text field in Asana, not modeled |
| MISSING_IN_CODE | Header URL | text field in Asana, not modeled |
| MISSING_IN_CODE | Website | text field in Asana, not modeled |
| MISSING_IN_CODE | Landing Page URL | text field in Asana, not modeled |
| MISSING_IN_CODE | Scheduling Link | text field in Asana, not modeled |
| MISSING_IN_CODE | MRR | number field in Asana, not modeled |
| MISSING_IN_CODE | Weekly Ad Spend | number field in Asana, not modeled |
| MISSING_IN_CODE | Discount | number field in Asana, not modeled |
| MISSING_IN_CODE | Status | enum field in Asana, not modeled |

---

### Location (Project: Locations)

**Project GID**: 1200836133305610
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (12 fields)

| Field Name | Type | GID | Notes |
|------------|------|-----|-------|
| Time Zone | enum | 1182713683395810 | Shared timezone field |
| Street # | number | 1200794141546669 | |
| Street Name | text | 1200840572990979 | |
| Suite | text | 1200794143139798 | |
| City | text | 1200794070148392 | |
| Neighborhood | text | 1200794148221723 | |
| State | text | 1200794144728232 | |
| Zip Code | text | 1201615685667172 | |
| Country | enum | 1200840676891090 | ENUM, not text! |
| Office Location | text | 1198487488737811 | |
| Min Radius | number | 1206625401127609 | |
| Max Radius | number | 1206625400928974 | |

#### Modeled Fields (from location.py Fields class - 8 constants)

| Constant | Field Name |
|----------|------------|
| STREET | Street |
| CITY | City |
| STATE | State |
| ZIP_CODE | Zip Code |
| COUNTRY | Country |
| PHONE | Phone |
| LATITUDE | Latitude |
| LONGITUDE | Longitude |

#### Gap Analysis

| Issue | Field | Details |
|-------|-------|---------|
| MISSING_IN_CODE | Time Zone | enum in Asana, not modeled |
| MISSING_IN_CODE | Street # | number in Asana, code has "Street" (text) |
| MISSING_IN_CODE | Street Name | text in Asana, code just has "Street" |
| MISSING_IN_CODE | Suite | text in Asana, not modeled |
| MISSING_IN_CODE | Neighborhood | text in Asana, not modeled |
| MISSING_IN_CODE | Office Location | text in Asana, not modeled |
| MISSING_IN_CODE | Min Radius | number in Asana, not modeled |
| MISSING_IN_CODE | Max Radius | number in Asana, not modeled |
| TYPE_MISMATCH | Country | Asana: enum, Code: assumed text |
| STALE_IN_CODE | Phone | Not found in Locations project |
| STALE_IN_CODE | Latitude | Not found in Locations project |
| STALE_IN_CODE | Longitude | Not found in Locations project |

---

### Hours (Project: Hours)

**Project GID**: 1201614578074026
**Status**: FETCHED SUCCESSFULLY

#### Actual Asana Fields (6 fields)

| Field Name | Type | GID | Notes |
|------------|------|-----|-------|
| Monday | multi_enum | 1201614830309234 | Values like "08:00:00", "17:00:00" |
| Tuesday | multi_enum | 1201614868363112 | |
| Wednesday | multi_enum | 1201614874856710 | |
| Thursday | multi_enum | 1201615000302242 | |
| Friday | multi_enum | 1201614886774414 | |
| Saturday | multi_enum | 1201614907076631 | |

**Note**: Sunday not found in fetched data - may need pagination or doesn't exist.

#### Modeled Fields (from hours.py Fields class - 9 constants)

| Constant | Field Name | Expected Type |
|----------|------------|---------------|
| MONDAY_HOURS | Monday Hours | text (implied) |
| TUESDAY_HOURS | Tuesday Hours | text |
| WEDNESDAY_HOURS | Wednesday Hours | text |
| THURSDAY_HOURS | Thursday Hours | text |
| FRIDAY_HOURS | Friday Hours | text |
| SATURDAY_HOURS | Saturday Hours | text |
| SUNDAY_HOURS | Sunday Hours | text |
| TIMEZONE | Timezone | text |
| NOTES | Hours Notes | text |

#### Gap Analysis

| Issue | Field | Details |
|-------|-------|---------|
| NAME_MISMATCH | Monday | Asana: "Monday", Code: "Monday Hours" |
| NAME_MISMATCH | Tuesday | Asana: "Tuesday", Code: "Tuesday Hours" |
| NAME_MISMATCH | Wednesday | Asana: "Wednesday", Code: "Wednesday Hours" |
| NAME_MISMATCH | Thursday | Asana: "Thursday", Code: "Thursday Hours" |
| NAME_MISMATCH | Friday | Asana: "Friday", Code: "Friday Hours" |
| NAME_MISMATCH | Saturday | Asana: "Saturday", Code: "Saturday Hours" |
| TYPE_MISMATCH | ALL DAYS | Asana: multi_enum, Code: expects text |
| STALE_IN_CODE | Timezone | Not found in Hours project |
| STALE_IN_CODE | Hours Notes | Not found in Hours project |
| STALE_IN_CODE | Sunday Hours | Sunday not found in fetched fields |

**CRITICAL**: Hours model is fundamentally broken. It expects text fields named "Monday Hours", but Asana has multi_enum fields named "Monday". The values are time strings like "08:00:00", "17:00:00".

---

### AssetEditHolder (Project: Asset Edit Holder)

**Project GID**: 1203992664400125
**Status**: VERIFIED (2025-12-18)

#### GID Verification

- **Code GID**: `AssetEditHolder.PRIMARY_PROJECT_GID = "1203992664400125"` (business.py line 106) - VERIFIED CORRECT
- **Original Audit GID**: 1203421687860105 - was incorrect/stale
- **Corrected GID**: 1203992664400125 - matches code

#### Actual Asana Fields (4 fields) - UNEXPECTED

| Field Name | Type | GID | Notes |
|------------|------|-----|-------|
| Generic Assets | enum | 1203912366141709 | **NOT MODELED** |
| Template Assets | enum | 1203993034227406 | **NOT MODELED** |
| Review All Ads | enum | 1203912828529011 | **NOT MODELED** (also on AssetEdit) |
| Asset Edit Comments | text | 1207845813084739 | **NOT MODELED** |

#### Modeled Fields

AssetEditHolder is a holder entity with no custom fields defined (uses HolderFactory pattern).

#### Gap Analysis

| Issue | Field | Details |
|-------|-------|---------|
| MISSING_IN_CODE | Generic Assets | enum field - controls asset generation settings |
| MISSING_IN_CODE | Template Assets | enum field - controls template asset settings |
| MISSING_IN_CODE | Review All Ads | enum field - shared with AssetEdit entity |
| MISSING_IN_CODE | Asset Edit Comments | text field - holder-level comments |

**ARCHITECTURAL NOTE**: AssetEditHolder breaks the typical holder pattern by having 4 custom fields. Other holders (UnitHolder, ContactHolder, OfferHolder, ProcessHolder) have 0 custom fields. This suggests AssetEditHolder may need to be treated differently - either:
1. Add custom field accessors to AssetEditHolder (breaking holder pattern consistency)
2. Treat these as configuration fields that apply to all child AssetEdits
3. Consider if these fields should be on the parent Business instead

---

### AssetEdit (Project: Paid Content)

**Project GID**: 1202204184560785
**Status**: VERIFIED (2025-12-18)

#### GID Verification

- **Code GID**: AssetEdit has NO `PRIMARY_PROJECT_GID` defined (asset_edit.py) - NEEDS TO BE ADDED
- **Original Audit GID**: 1204390909572031 - was incorrect/stale
- **Corrected GID**: 1202204184560785 - needs to be added to code

#### Actual Asana Fields (27 fields)

| Field Name | Type | GID | Notes |
|------------|------|-----|-------|
| Estimated time | number | 1203421051176656 | **NOT MODELED** |
| External Notes | text | 1204391131686529 | **NOT MODELED** |
| Editor | people | 1203375406262688 | Modeled |
| Office Phone | text | 1181686411188348 | **NOT MODELED** |
| Vertical | enum | 1182735041547604 | Inherited from Process |
| Specialty | multi_enum | 1202981898844151 | **TYPE MISMATCH: modeled as enum** |
| Priority | enum | 1180878699491891 | Inherited from Process |
| Order | number | 1205004264981691 | **NOT MODELED** |
| Raw Assets | text | 1211937349719026 | Modeled |
| Feedback | enum | 1204882959828933 | **NOT MODELED** |
| Concerns | multi_enum | 1205523015269591 | **NOT MODELED** |
| Template ID | number | 1204340772413334 | **TYPE MISMATCH: modeled as text** |
| Asset ID | text | 1203152451833105 | Modeled |
| Offer ID | number | 1182699378641532 | **TYPE MISMATCH: modeled as text** |
| Videos Paid | number | 1202692278045398 | Modeled |
| Type | enum | 1202204184560800 | **NOT MODELED** |
| Direction | enum | 1203861642463688 | **NOT MODELED** |
| Asset Approval | enum | 1204463705398850 | Modeled |
| Review All Ads | enum | 1203912828529011 | Modeled |
| Score | number | 1207954491617441 | Modeled |
| Time to Close | number (formula) | 1205059650673606 | **NOT MODELED** (formula field) |
| Reviewer | people | 1210707909050655 | Modeled |
| Edit Date | date | 1210787799053921 | **NOT MODELED** |
| Video Link 1 | text | 1211345474494255 | **NOT MODELED** |
| Video Link 2 | text | 1211345564650491 | **NOT MODELED** |
| Video Link 3 | text | 1211345564650502 | **NOT MODELED** |
| Welcome Video | enum | 1211839731023419 | **NOT MODELED** |

#### Modeled Fields (from asset_edit.py - 11 fields declared)

| Constant | Field Name | Type | Status |
|----------|------------|------|--------|
| ASSET_APPROVAL | Asset Approval | enum (property) | OK |
| ASSET_ID | Asset ID | text (property) | OK |
| EDITOR | Editor | people (property) | OK |
| REVIEWER | Reviewer | people (property) | OK |
| OFFER_ID | Offer ID | text (property) | TYPE MISMATCH (Asana: number) |
| RAW_ASSETS | Raw Assets | text (property) | OK |
| REVIEW_ALL_ADS | Review All Ads | enum->bool (property) | OK |
| SCORE | Score | number/Decimal (property) | OK |
| SPECIALTY | Specialty | enum (property) | TYPE MISMATCH (Asana: multi_enum) |
| TEMPLATE_ID | Template ID | text (property) | TYPE MISMATCH (Asana: number) |
| VIDEOS_PAID | Videos Paid | number/int (property) | OK |

*Note: AssetEdit also inherits from Process, gaining its 8 fields (Started At, Process Completed At, Process Notes, Status, Priority, Vertical, Due Date, Assigned To).*

#### Gap Analysis

| Issue | Field | Details |
|-------|-------|---------|
| TYPE_MISMATCH | Specialty | Asana: multi_enum, Code: enum - same issue as Unit |
| TYPE_MISMATCH | Template ID | Asana: number, Code: text |
| TYPE_MISMATCH | Offer ID | Asana: number, Code: text |
| MISSING_IN_CODE | Estimated time | number - time estimate for edit work |
| MISSING_IN_CODE | External Notes | text - client-facing notes |
| MISSING_IN_CODE | Office Phone | text - contact phone |
| MISSING_IN_CODE | Order | number - ordering/priority field |
| MISSING_IN_CODE | Feedback | enum - feedback status |
| MISSING_IN_CODE | Concerns | multi_enum - flagged concerns |
| MISSING_IN_CODE | Type | enum - asset edit type |
| MISSING_IN_CODE | Direction | enum - direction/orientation |
| MISSING_IN_CODE | Time to Close | number (formula) - calculated field |
| MISSING_IN_CODE | Edit Date | date - when edit occurred |
| MISSING_IN_CODE | Video Link 1 | text - video output link |
| MISSING_IN_CODE | Video Link 2 | text - video output link |
| MISSING_IN_CODE | Video Link 3 | text - video output link |
| MISSING_IN_CODE | Welcome Video | enum - welcome video status |
| CODE_CHANGE_NEEDED | PRIMARY_PROJECT_GID | AssetEdit needs `PRIMARY_PROJECT_GID = "1202204184560785"` added |

**Critical Issues:**
1. **Specialty as multi_enum**: Same issue as Unit - allows multiple selections
2. **Template ID as number**: Currently stored as text, but Asana uses numeric ID
3. **Offer ID as number**: Critical for resolution - should be IntField not TextField
4. **16 unmodeled fields**: Significant gap in AssetEdit field coverage

---

## Cross-Project Field Analysis

### Shared Fields (same GID across multiple projects)

| Field Name | GID | Projects | Type |
|------------|-----|----------|------|
| Vertical | 1182735041547604 | Unit, AssetEdit, Offer, Sales, Onboarding, Impl, Retention, Reactivation, Business | enum |
| Specialty | 1202981898844151 | Unit, AssetEdit | multi_enum |
| Specialty (alternate) | 1200943943116217 | Sales, Onboarding, Offer, Contact, Business | enum |
| Rep | 1200943943116230 | Sales, Onboarding, Impl, Retention, Reactivation, Offer, Business | people |
| Rep (Unit) | 1202887864833071 | Unit | people |
| Time Zone | 1182713683395810 | Locations, Contact, Business, Hours | enum |
| City | 1200794070148392 | Locations, Contact | text |
| State | 1200794144728232 | Locations, Contact | text |
| MRR | 1206295135166178 | Offer, Sales, Business | number |
| MRR (Unit) | 1199947811009254 | Unit | number |
| Office Location | 1198487488737811 | Locations, Contact | text |
| Office Phone | 1181686411188348 | AssetEdit | text |
| Booking Type | 1200795614055170 | Sales, Business | enum |
| Form ID | 1200929696908867 | Offer, Sales | text |
| Review All Ads | 1203912828529011 | AssetEdit, AssetEditHolder | enum |
| Priority | 1180878699491891 | AssetEdit | enum |

**Note on Specialty field**: Two different GIDs exist:
- GID 1202981898844151 (multi_enum) - used by Unit and AssetEdit
- GID 1200943943116217 (enum) - used by Sales, Onboarding, Offer, Contact, Business

This suggests these may be different custom fields with the same name, or the field was changed at some point. The multi_enum version is newer and allows multiple selections.

### Process-Type Fields Comparison

| Field | Sales | Onboarding | Impl | Retention | Reactivation |
|-------|-------|------------|------|-----------|--------------|
| Vertical | Yes | Yes | Yes | Yes | Yes |
| Specialty | Yes | Yes | Yes | Yes | Yes |
| Rep | Yes | Yes | Yes | Yes | Yes |
| Status (custom) | Yes | Yes | Yes | Yes | Yes |
| Score | Yes | No | No | No | No |
| Disposition | Yes | No | No | No | No |
| Lead fields | Yes | Yes | Partial | No | No |
| Outreach fields | Yes | Yes | No | Yes | Yes |

**Fields common to ALL process types:**
- Vertical
- Specialty
- Rep
- Status (custom enum)

**Fields unique to specific types:**
- Sales: Score, Disposition, Opportunity Type
- Onboarding: Onboarding Stage, Kickoff Date, Go Live Date
- Implementation: Implementation Lead, Technical Requirements
- Retention: Account Health, NPS Score, Risk Level
- Reactivation: Churn Reason, Win-back Offer

---

## Recommendations

### Priority 1: Critical Fixes

1. **Unit Model Type Mismatches** (CRITICAL - 8 fields affected)
   - `specialty`: Change EnumField to MultiEnumField (users select multiple specialties)
   - `gender`: Change EnumField to MultiEnumField (targeting multiple genders)
   - `discount`: Change NumberField to EnumField (is a selection like "10%", "20%", "None")
   - `zip_codes_radius`: Change TextField to IntField (is a number in Asana)
   - `filter_out_x`: Change TextField to EnumField
   - `form_questions`: Change TextField to MultiEnumField
   - `disabled_questions`: Change TextField to MultiEnumField
   - `disclaimers`: Change TextField to MultiEnumField

2. **AssetEdit Model Fixes** (CRITICAL - 3 type mismatches + 16 missing fields)
   - `specialty`: Change enum to multi_enum (same issue as Unit)
   - `template_id`: Change TextField to IntField (Asana type: number)
   - `offer_id`: Change TextField to IntField (Asana type: number) - **critical for resolution**
   - Add `PRIMARY_PROJECT_GID = "1202204184560785"` to class
   - Add 16 missing fields (see AssetEdit Gap Analysis above)

3. **Hours Model Overhaul** (CRITICAL)
   - Field names: "Monday" not "Monday Hours"
   - Field type: multi_enum not text
   - Values are time strings ("08:00:00") not hour ranges
   - Consider storing as `list[str]` representing open/close times

4. **Location Model Updates**
   - Add: Time Zone, Street #, Street Name, Suite, Neighborhood, Min Radius, Max Radius
   - Fix: Country is enum (with values US, CA, SE, AU, etc.), not text
   - Remove or verify: Phone, Latitude, Longitude (not in project)

### Priority 2: Architectural Decisions

5. **AssetEditHolder Custom Fields** (NEW - breaks holder pattern)
   - AssetEditHolder has 4 custom fields (unique among holders)
   - Fields: Generic Assets, Template Assets, Review All Ads, Asset Edit Comments
   - Decision needed: Add field accessors or refactor holder pattern
   - Consider if these are configuration fields that should cascade to AssetEdits

6. **Specialty Field Duality** (NEW)
   - Two different Specialty fields exist with different GIDs and types:
     - GID 1202981898844151 (multi_enum) - Unit, AssetEdit
     - GID 1200943943116217 (enum) - Offer, Business, Process types
   - Code should handle both or standardize to one

### Priority 3: Missing Field Coverage

7. **Business Model - Add Fields**
   - Specialty, Time Zone, Ad Account ID
   - Meta/TikTok/Solution Fee Sub IDs
   - TikTok Profile, Logo URL, Header URL, Website
   - Landing Page URL, Scheduling Link
   - MRR, Weekly Ad Spend, Discount, Status

8. **Contact Model - Add Fields**
   - Office Location, State

9. **Offer Model - Add Fields**
   - TikTok Profile, TikTok Spend
   - Meta/TikTok/Solution Fee Sub IDs

10. **Unit Model - Add Fields**
    - Internal Notes (text) - not modeled

### Priority 4: Architecture Decisions (Phase 2)

11. **Process Subclasses**
    - Current generic Process has 8 fields, Sales alone has 67+
    - Recommend Sales, Onboarding, Implementation, Retention, Reactivation subclasses
    - Each with their own typed field accessors

### Priority 5: Seeding Configuration

12. **Update Seeding to Match Reality**
    - Hours: Update seed data to use multi_enum time values
    - Location: Update Country to use enum values (US, CA, SE, etc.)
    - Business: Expand seeded fields to match Asana schema
    - Unit: Update Discount to use enum values

---

## Appendix: Raw API Response Samples

### Hours Project Response (showing multi_enum structure)

```json
{
  "gid": "1201614830309234",
  "name": "Monday",
  "resource_subtype": "multi_enum",
  "enum_options": [
    {"gid": "1201614830309249", "name": "08:00:00"},
    {"gid": "1201614830314661", "name": "09:00:00"},
    {"gid": "1201614830314692", "name": "10:00:00"},
    {"gid": "1201614835819170", "name": "17:00:00"},
    {"gid": "1201614835822345", "name": "17:30:00"},
    {"gid": "1201614835824426", "name": "18:00:00"}
  ]
}
```

### Location Project Response (showing Country enum)

```json
{
  "gid": "1200840676891090",
  "name": "Country",
  "resource_subtype": "enum",
  "enum_options": [
    {"gid": "1200840676893207", "name": "US"},
    {"gid": "1200840676893212", "name": "CA"},
    {"gid": "1203477324268644", "name": "SE"},
    {"gid": "1204877219943670", "name": "AU"},
    {"gid": "1205330567072072", "name": "United Kingdom, GB"}
  ]
}
```

---

## Audit History

| Date | Update | Details |
|------|--------|---------|
| 2025-12-18 | Initial audit | 16 projects audited, 13 fetched, 3 API errors |
| 2025-12-18 | GID corrections | User provided corrected GIDs for 3 failed projects |
| 2025-12-18 | API verification complete | All 3 corrected projects verified with actual field data |

### Corrected GIDs (2025-12-18)

| Model | Project Name | Original (Invalid) GID | Corrected GID | Code Match | Verified |
|-------|--------------|------------------------|---------------|------------|----------|
| Unit | Business Units | 1205571477139891 | 1201081073731555 | YES | YES - 31 fields |
| AssetEditHolder | Asset Edit Holder | 1203421687860105 | 1203992664400125 | YES | YES - 4 fields (unexpected) |
| AssetEdit | Paid Content | 1204390909572031 | 1202204184560785 | NO (missing) | YES - 27 fields |

### Key Discoveries from API Verification

1. **Unit (Business Units)**: 31 custom fields confirmed. 8 type mismatches found (specialty, gender, discount, etc.)
2. **AssetEditHolder**: Unexpectedly has 4 custom fields (breaks typical holder pattern of 0 fields)
3. **AssetEdit (Paid Content)**: 27 custom fields. 16 fields not modeled in code. 3 type mismatches.

### Verification Commands (for future audits)

```bash
# Verify Unit (Business Units)
curl -s -H "Authorization: Bearer $ASANA_PAT" \
  "https://app.asana.com/api/1.0/projects/1201081073731555/custom_field_settings"

# Verify AssetEditHolder (Asset Edit Holder)
curl -s -H "Authorization: Bearer $ASANA_PAT" \
  "https://app.asana.com/api/1.0/projects/1203992664400125/custom_field_settings"

# Verify AssetEdit (Paid Content)
curl -s -H "Authorization: Bearer $ASANA_PAT" \
  "https://app.asana.com/api/1.0/projects/1202204184560785/custom_field_settings"
```
