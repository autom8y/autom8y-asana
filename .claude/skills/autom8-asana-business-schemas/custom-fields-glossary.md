# Custom Fields Glossary

> All custom field definitions by entity type

---

## Field Flow Annotations (ADR-0054)

Fields are annotated with their flow pattern and override behavior:

| Annotation | Meaning |
|------------|---------|
| **[C]** | **Cascading (no override)** - Owned by parent, ALWAYS overwrites descendants via `cascade_field()` |
| **[C+O]** | **Cascading (with override)** - Owned by parent, only overwrites if descendant is null |
| **[I]** | **Inherited** - Resolved from parent chain at read-time, can be overridden locally |
| (none) | Local field, no cross-entity behavior |

**Critical Design Constraint**: `allow_override=False` is the DEFAULT. Most cascading fields do NOT permit local overrides. Only fields explicitly configured with `allow_override=True` permit descendants to keep local values.

---

## Business Fields (19 Fields)

All Business cascading fields use `allow_override=False` (DEFAULT) - descendant values are ALWAYS overwritten.

| Field Name       | Type   | Flow | Description                 | Values/Format             |
| ---------------- | ------ | ---- | --------------------------- | ------------------------- |
| Aggression Level | Enum   |      | Campaign aggression level   | Enum options              |
| Booking Type     | Enum   |      | How leads schedule          | Tentative, Standard, etc. |
| Company ID       | Text   | [C]  | Internal company identifier | String (e.g., "ACME-001") |
| Facebook Page ID | Text   |      | Facebook page identifier    | String                    |
| Fallback Page ID | Text   |      | Fallback page identifier    | String                    |
| Google Cal ID    | Text   |      | Google Calendar ID          | String                    |
| Num Reviews      | Number |      | Number of reviews           | Integer                   |
| Office Phone     | Text   | [C]  | Main phone number           | Phone string              |
| Owner Name       | Text   |      | Business owner name         | String                    |
| Owner Nickname   | Text   |      | Owner preferred nickname    | String                    |
| Rep              | People |      | Sales representative        | List of user dicts        |
| Review 1         | Text   |      | First review text           | String                    |
| Review 2         | Text   |      | Second review text          | String                    |
| Reviews Link     | Text   |      | Link to reviews page        | URL string                |
| Stripe ID        | Text   |      | Stripe customer ID          | String                    |
| Stripe Link      | Text   |      | Link to Stripe dashboard    | URL string                |
| Twilio Phone Num | Text   |      | Twilio phone number         | Phone string              |
| VCA Status       | Enum   |      | VCA enabled status          | Enabled, Disabled         |
| Vertical         | Enum   |      | Business vertical           | Legal, Medical, etc.      |

**Business Cascading Fields** (`allow_override=False` - parent always wins):
- Office Phone -> Unit, Offer, Process, Contact
- Company ID -> All descendants

---

## Contact Fields (19 Fields)

| Field Name         | Type | Description                   | Values/Format  |
| ------------------ | ---- | ----------------------------- | -------------- |
| Build Call Link    | Text | Link to build call            | URL string     |
| Campaign           | Text | Marketing campaign source     | String         |
| City               | Text | City location                 | String         |
| Contact Email      | Text | Email address                 | Email string   |
| Contact Phone      | Text | Phone number                  | Phone string   |
| Contact URL        | Text | Personal website              | URL string     |
| Content            | Text | Content/notes                 | String         |
| Dashboard User     | Text | Dashboard user identifier     | String         |
| Employee ID        | Text | Employee identifier           | String         |
| Medium             | Text | Marketing medium              | String         |
| Nickname           | Text | Preferred nickname            | String         |
| Position           | Enum | Job title/position            | Enum options   |
| Prefix             | Text | Name prefix                   | String         |
| Profile Photo URL  | Text | Profile photo link            | URL string     |
| Source             | Text | Lead source                   | String         |
| Suffix             | Text | Name suffix                   | String         |
| Term               | Text | Marketing term                | String         |
| Time Zone          | Enum | Contact time zone             | IANA time zone |
| Text Communication | Enum | Text communication preference | Enum options   |

---

## Unit Fields (31 Fields)

**Unit Cascading Fields** (multi-level cascading from Unit to Offers/Processes):
- Platforms -> Offer (`allow_override=True` - Offers can keep local value if set)
- Vertical -> Offer, Process (`allow_override=False` - always overwrite)
- Booking Type -> Offer (`allow_override=False` - always overwrite)

**Inherited Fields**: Unit inherits Default Vertical from Business if not set locally.

### Financial (9 Fields)

| Field Name          | Type   | Flow | Description               | Values/Format       |
| ------------------- | ------ | ---- | ------------------------- | ------------------- |
| MRR                 | Number |      | Monthly recurring revenue | Decimal             |
| Weekly Ad Spend     | Number |      | Weekly ad budget          | Decimal             |
| Discount            | Number |      | Discount percentage       | Decimal (0-100)     |
| Currency            | Enum   |      | Currency code             | USD, CAD, EUR, etc. |
| Meta Spend          | Number |      | Meta/Facebook ad spend    | Decimal             |
| Meta Spend Sub ID   | Text   |      | Meta subscription ID      | String              |
| Tiktok Spend        | Number |      | TikTok ad spend           | Decimal             |
| Tiktok Spend Sub ID | Text   |      | TikTok subscription ID    | String              |
| Solution Fee Sub ID | Text   |      | Solution fee sub ID       | String              |

### Ad Account / Platform (3 Fields)

| Field Name     | Type       | Flow  | Description           | Values/Format   |
| -------------- | ---------- | ----- | --------------------- | --------------- |
| Ad Account ID  | Text       |       | Primary ad account ID | String          |
| Platforms      | Multi-enum | [C+O] | Active platforms      | List of strings |
| Tiktok Profile | Text       |       | TikTok profile link   | String          |

### Product/Service (5 Fields)

| Field Name | Type       | Flow | Description          | Values/Format                 |
| ---------- | ---------- | ---- | -------------------- | ----------------------------- |
| Products   | Multi-enum |      | Products offered     | List of product names         |
| Languages  | Multi-enum |      | Supported languages  | List: English, Spanish, etc.  |
| Vertical   | Enum       | [C]  | Business vertical    | Legal, Medical, Home Services |
| Specialty  | Text       |      | Sub-specialty        | String                        |
| Rep        | Text       |      | Sales representative | String                        |

### Demographics / Targeting (7 Fields)

| Field Name       | Type       | Description           | Values/Format     |
| ---------------- | ---------- | --------------------- | ----------------- |
| Radius           | Number     | Target radius (miles) | Integer           |
| Min Age          | Number     | Minimum target age    | Integer           |
| Max Age          | Number     | Maximum target age    | Integer           |
| Gender           | Enum       | Target gender         | All, Male, Female |
| Zip Code List    | Multi-text | Target zip codes      | List of strings   |
| Zip Codes Radius | Text       | Radius per zip code   | String            |
| Excluded Zips    | Multi-text | Excluded zip codes    | List of strings   |

### Form / Lead Settings (7 Fields)

| Field Name              | Type       | Description              | Values/Format   |
| ----------------------- | ---------- | ------------------------ | --------------- |
| Form Questions          | Multi-enum | Active form questions    | List of strings |
| Disabled Questions      | Multi-enum | Disabled questions       | List of strings |
| Disclaimers             | Multi-enum | Active disclaimers       | List of strings |
| Custom Disclaimer       | Text       | Custom disclaimer text   | String          |
| Sms Lead Verification   | Boolean    | SMS verification enabled | True/False      |
| Work Email Verification | Boolean    | Work email required      | True/False      |
| Filter Out X            | Number     | Filter out percentage    | Decimal (0-100) |

---

## Address Fields (12 Fields)

Address is a sibling of Hours under LocationHolder.

| Field Name      | Type   | Description             | Values/Format |
| --------------- | ------ | ----------------------- | ------------- |
| City            | Text   | City name               | String        |
| Country         | Text   | Country                 | String        |
| Max Radius      | Number | Maximum service radius  | Number        |
| Min Radius      | Number | Minimum service radius  | Number        |
| Neighborhood    | Text   | Neighborhood name       | String        |
| Office Location | Text   | Office location details | String        |
| State           | Text   | State/province          | String        |
| Street Name     | Text   | Street name             | String        |
| Street Num      | Text   | Street number           | String        |
| Suite           | Text   | Suite/unit number       | String        |
| Time Zone       | Text   | Time zone               | String        |
| Zip Code        | Text   | ZIP/postal code         | String        |

---

## Hours Fields (7 Fields)

| Field Name | Type | Description     | Values/Format                   |
| ---------- | ---- | --------------- | ------------------------------- |
| Monday     | Text | Monday hours    | "9:00 AM - 5:00 PM" or "Closed" |
| Tuesday    | Text | Tuesday hours   | Same format                     |
| Wednesday  | Text | Wednesday hours | Same format                     |
| Thursday   | Text | Thursday hours  | Same format                     |
| Friday     | Text | Friday hours    | Same format                     |
| Saturday   | Text | Saturday hours  | Same format                     |
| Sunday     | Text | Sunday hours    | Same format                     |

---

## Offer Fields (39 Fields)

Offers are the unit of work for ad status (under Unit > OfferHolder).

**Cascaded Fields Received** (from Unit via `cascade_field()`):
- Platforms: `[C+O]` - can be overwritten if Offer has null, OR Offer can keep local value
- Vertical: `[C]` - always overwritten from Unit (no local override)
- Booking Type: `[C]` - always overwritten from Unit (no local override)

**Inherited Fields**: Offer inherits Manager from Unit (read-time resolution).

### Financial (5 Fields)

| Field Name        | Type   | Flow | Description               | Values/Format |
| ----------------- | ------ | ---- | ------------------------- | ------------- |
| MRR               | Number |      | Monthly recurring revenue | Decimal       |
| Cost              | Number |      | Cost amount               | Decimal       |
| Weekly Ad Spend   | Number |      | Weekly ad budget          | Decimal       |
| Voucher Value     | Number |      | Voucher/discount value    | Decimal       |
| Budget Allocation | Number |      | Budget allocation         | Decimal       |

### Ad Platform (7 Fields)

| Field Name     | Type       | Description          | Values/Format   |
| -------------- | ---------- | -------------------- | --------------- |
| Ad ID          | Text       | Ad identifier        | String          |
| Ad Set ID      | Text       | Ad set identifier    | String          |
| Campaign ID    | Text       | Campaign identifier  | String          |
| Asset ID       | Text       | Creative asset ID    | String          |
| Ad Account URL | Text       | Ad account dashboard | URL string      |
| Active Ads URL | Text       | Active ads link      | URL string      |
| Platforms      | Multi-enum | Active platforms     | List of strings |

### Content (8 Fields)

| Field Name        | Type   | Description          | Values/Format |
| ----------------- | ------ | -------------------- | ------------- |
| Offer Headline    | Text   | Main headline        | String        |
| Included Item 1   | Text   | First included item  | String        |
| Included Item 2   | Text   | Second included item | String        |
| Included Item 3   | Text   | Third included item  | String        |
| Landing Page URL  | Text   | Landing page link    | URL string    |
| Preview Link      | Text   | Ad preview link      | URL string    |
| Lead Testing Link | Text   | Lead test form link  | URL string    |
| Num AI Copies     | Number | Number of AI copies  | Integer       |

### Configuration (9 Fields)

| Field Name           | Type       | Flow | Description           | Values/Format   |
| -------------------- | ---------- | ---- | --------------------- | --------------- |
| Form ID              | Text       |      | Form identifier       | String          |
| Language             | Enum       |      | Ad language           | Enum options    |
| Specialty            | Text       |      | Business specialty    | String          |
| Vertical             | Enum       | [I]  | Business vertical     | Enum options    |
| Targeting            | Text       |      | Targeting description | String          |
| Targeting Strategies | Multi-enum |      | Targeting strategies  | List of strings |
| Optimize For         | Enum       |      | Optimization goal     | Enum options    |
| Campaign Type        | Enum       |      | Type of campaign      | Enum options    |
| Office Phone         | Text       |      | Contact phone         | Phone string    |

### Scheduling (4 Fields)

| Field Name          | Type   | Description           | Values/Format |
| ------------------- | ------ | --------------------- | ------------- |
| Appt Duration       | Number | Appointment duration  | Minutes       |
| Calendar Duration   | Number | Calendar block length | Minutes       |
| Custom Cal URL      | Text   | Custom calendar URL   | URL string    |
| Offer Schedule Link | Text   | Scheduling link       | URL string    |

### Notes (2 Fields)

| Field Name     | Type | Description    | Values/Format |
| -------------- | ---- | -------------- | ------------- |
| Internal Notes | Text | Internal notes | String        |
| External Notes | Text | External notes | String        |

### Metadata (4 Fields)

| Field Name   | Type   | Description          | Values/Format      |
| ------------ | ------ | -------------------- | ------------------ |
| Offer ID     | Text   | Unique offer ID      | String             |
| Algo Version | Text   | Algorithm version    | String             |
| Triggered By | Text   | What triggered offer | String             |
| Rep          | People | Sales representative | List of user dicts |

---

## Field Type Patterns

### Enum Fields

```python
# Asana returns: {"gid": "123", "name": "Active", "enabled": true}
# Property should extract "name"
@property
def unit_status(self) -> str | None:
    value = self.get_custom_fields().get(self.Fields.UNIT_STATUS)
    if isinstance(value, dict):
        return value.get("name")
    return value
```

### Multi-Enum Fields

```python
# Asana returns: [{"gid": "1", "name": "Google"}, {"gid": "2", "name": "Meta"}]
# Property should extract list of names
@property
def products(self) -> list[str]:
    value = self.get_custom_fields().get(self.Fields.PRODUCTS)
    if value is None:
        return []
    if isinstance(value, list):
        return [v.get("name") if isinstance(v, dict) else v for v in value]
    return []
```

### Number Fields

```python
# Asana returns: 5000.0 (float)
# Property can return as Decimal for precision
@property
def mrr(self) -> Decimal | None:
    value = self.get_custom_fields().get(self.Fields.MRR)
    return Decimal(str(value)) if value is not None else None
```

---

## Related

- [patterns-schemas.md](patterns-schemas.md) - Implementation patterns
- [autom8-asana-business-fields](../autom8-asana-business-fields/) - Field accessor details
