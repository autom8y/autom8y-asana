# BusinessSeeder v2 Integration Guide

> How to use composite matching for business deduplication.

**Module**: `autom8_asana.models.business.seeder`

**Version**: v2 (with composite matching)

---

## Overview

The BusinessSeeder creates business entity hierarchies with automatic deduplication. Version 2 introduces **Fellegi-Sunter probabilistic matching**, enabling robust duplicate detection even when data contains typos, abbreviations, or formatting variations.

**What you get**:
- Automatic duplicate detection using email, phone, name, and domain
- Configurable matching thresholds via environment variables
- Complete audit trail for every match decision
- Graceful degradation if matching components fail

**What you provide**:
- Business data (name required; email, phone, domain optional)
- Process data (type and name)
- Optional contact data

---

## Quick Start

### Basic Usage (5 minutes)

```python
from autom8_asana.client import AsanaClient
from autom8_asana.models.business.seeder import (
    BusinessSeeder,
    BusinessData,
    ProcessData,
)
from autom8_asana.models.business.process import ProcessType

# Initialize
client = AsanaClient.from_env()
seeder = BusinessSeeder(client)

# Seed with composite matching fields
result = await seeder.seed_async(
    business=BusinessData(
        name="Acme Corporation",
        email="info@acme.com",
        phone="555-123-4567",
        domain="acme.com",
    ),
    process=ProcessData(
        name="Demo Call - Acme",
        process_type=ProcessType.SALES,
    ),
)

# Check what happened
if result.created_business:
    print(f"Created new business: {result.business.gid}")
else:
    print(f"Matched existing business: {result.business.gid}")
```

### Synchronous API

```python
# Same API, synchronous version
result = seeder.seed(
    business=BusinessData(name="Acme Corp", email="info@acme.com"),
    process=ProcessData(name="Demo", process_type=ProcessType.SALES),
)
```

---

## When to Use v2 Matching

### Use Composite Matching (v2) When:

| Scenario | Why It Helps |
|----------|--------------|
| Input has name variations or typos | Fuzzy matching catches "Acme Corp" vs "Acme Corporation" |
| Multiple corroborating fields available | Email + phone + name together provide high confidence |
| Data comes from multiple sources | Calendly forms, Typeform, manual entry have inconsistent formatting |
| False positives are acceptable with review | Lenient threshold catches more duplicates for human review |

### Use Exact Matching (v1) When:

| Scenario | Why |
|----------|-----|
| `company_id` is reliable and always present | Tier 1 exact match is fastest and most reliable |
| Zero false positive tolerance | Financial or legal contexts where wrong merge is costly |
| Performance is critical | Composite matching adds search overhead; exact match is O(1) |
| Data is already clean and normalized | No benefit from fuzzy matching if input is consistent |

### Decision Tree

```
Do you have a reliable company_id?
  |
  +-- YES --> Use v1 (company_id only)
  |
  +-- NO --> Do you have email, phone, or domain?
               |
               +-- YES (2+ fields) --> Use v2 composite matching
               |
               +-- NO (name only) --> Consider v1, or v2 with higher threshold
```

---

## Matching Pipeline

The seeder uses a tiered matching strategy:

```
Input: BusinessData(name="Joe's Pizza", email="joe@joespizza.com", phone="555-555-1234")
                                |
                                v
+---------------------------------------------------------------+
| TIER 1: Exact company_id Match                                |
| - O(1) lookup via SearchService                               |
| - If company_id provided and found -> Return existing         |
+---------------------------------------------------------------+
                                | (no company_id or no match)
                                v
+---------------------------------------------------------------+
| TIER 2: Composite Matching                                    |
|                                                               |
|  1. Search for candidates by name tokens                      |
|  2. Apply blocking rules (domain, phone prefix, name tokens)  |
|  3. For each candidate:                                       |
|     - Normalize fields (phone -> E.164, email -> lowercase)   |
|     - Compare fields (exact or fuzzy)                         |
|     - Accumulate log-odds scores                              |
|  4. Convert to probability (0.0-1.0)                          |
|  5. If probability >= 0.80 threshold -> Match                 |
+---------------------------------------------------------------+
                                | (no match above threshold)
                                v
+---------------------------------------------------------------+
| TIER 3: Create New Business                                   |
| - Generate hierarchy: Business -> Unit -> Process             |
| - Return SeederResult with created_business=True              |
+---------------------------------------------------------------+
```

### Field Comparison Details

| Field | Comparison Type | Normalization | Weight (Match) | Weight (Non-match) |
|-------|-----------------|---------------|----------------|-------------------|
| Email | Exact | Lowercase, trim | +8.0 | -4.0 |
| Phone | Exact | E.164 format | +7.0 | -4.0 |
| Name | Fuzzy (Jaro-Winkler) | Remove legal suffixes | +6.0 | -3.0 |
| Domain | Exact | Strip www, protocol | +5.0 | -2.0 |

**Null handling**: Fields with null values on either side contribute zero weight. The system never penalizes missing data.

---

## Configuration Examples

All configuration via environment variables with `SEEDER_` prefix.

### E-commerce (Strict)

Avoid false positives that could merge separate customer accounts.

```bash
# .env
SEEDER_MATCH_THRESHOLD=0.90    # High confidence required
SEEDER_MIN_FIELDS=3            # Need 3+ matching fields
SEEDER_FUZZY_EXACT_THRESHOLD=0.98  # Near-exact name required
```

```python
# Or configure in code
from autom8_asana.models.business.matching import MatchingConfig

config = MatchingConfig(
    match_threshold=0.90,
    min_fields=3,
    fuzzy_exact_threshold=0.98,
)
seeder = BusinessSeeder(client, matching_config=config)
```

### Professional Services (Standard)

Balanced approach for typical B2B deduplication.

```bash
# .env (defaults work well, but explicit for clarity)
SEEDER_MATCH_THRESHOLD=0.80
SEEDER_MIN_FIELDS=2
```

### Lead Aggregation (Lenient)

Catch as many duplicates as possible; human reviews before merge.

```bash
# .env
SEEDER_MATCH_THRESHOLD=0.70    # Lower bar
SEEDER_MIN_FIELDS=1            # Allow single-field match
SEEDER_FUZZY_MEDIUM_THRESHOLD=0.75  # Accept looser name matches
```

---

## Integration Patterns

### Webhook Handler (Calendly, Typeform)

```python
from fastapi import FastAPI, Request
from autom8_asana.client import AsanaClient
from autom8_asana.models.business.seeder import (
    BusinessSeeder,
    BusinessData,
    ProcessData,
    ContactData,
)
from autom8_asana.models.business.process import ProcessType

app = FastAPI()
client = AsanaClient.from_env()
seeder = BusinessSeeder(client)


@app.post("/webhooks/calendly")
async def handle_calendly(request: Request):
    payload = await request.json()

    # Extract fields from Calendly payload
    invitee = payload.get("payload", {}).get("invitee", {})

    result = await seeder.seed_async(
        business=BusinessData(
            name=invitee.get("name", "Unknown Business"),
            email=invitee.get("email"),
            phone=invitee.get("phone"),
            # Domain extracted from email if not provided
            domain=_extract_domain(invitee.get("email")),
        ),
        process=ProcessData(
            name=f"Demo Call - {invitee.get('name')}",
            process_type=ProcessType.SALES,
        ),
        contact=ContactData(
            full_name=invitee.get("name"),
            contact_email=invitee.get("email"),
            contact_phone=invitee.get("phone"),
        ),
    )

    return {
        "status": "ok",
        "matched": not result.created_business,
        "business_gid": result.business.gid,
    }


def _extract_domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return email.split("@")[1].lower()
```

### Batch Import

```python
import csv
from autom8_asana.models.business.seeder import BusinessData, ProcessData

async def import_leads_from_csv(filepath: str):
    """Import leads with deduplication."""
    results = {"created": 0, "matched": 0, "errors": []}

    with open(filepath) as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                result = await seeder.seed_async(
                    business=BusinessData(
                        name=row["company_name"],
                        email=row.get("email"),
                        phone=row.get("phone"),
                        domain=row.get("website"),
                        company_id=row.get("external_id"),  # Tier 1 if present
                    ),
                    process=ProcessData(
                        name=f"Import - {row['company_name']}",
                        process_type=ProcessType.SALES,
                    ),
                )

                if result.created_business:
                    results["created"] += 1
                else:
                    results["matched"] += 1

            except Exception as e:
                results["errors"].append({
                    "row": row,
                    "error": str(e),
                })

    return results
```

### Pipeline Operator Pattern

For operators who need simple boolean responses:

```python
async def seed_or_find_business(
    name: str,
    email: str | None = None,
    phone: str | None = None,
    domain: str | None = None,
) -> tuple[str, bool]:
    """
    Seed or find a business.

    Returns:
        Tuple of (business_gid, was_created)
    """
    result = await seeder.seed_async(
        business=BusinessData(
            name=name,
            email=email,
            phone=phone,
            domain=domain,
        ),
        process=ProcessData(
            name=f"Auto-process - {name}",
            process_type=ProcessType.SALES,
        ),
    )

    return result.business.gid, result.created_business
```

---

## Field Data Requirements

### Minimum Requirements

| Requirement | Notes |
|-------------|-------|
| `name` (required) | Business name. Used for fuzzy matching and candidate search. |
| At least 1 additional field | For reliable matching, provide email OR phone OR domain. |

### Field Quality Guidelines

| Field | Good | Acceptable | Poor |
|-------|------|------------|------|
| **Email** | `info@acme.com` | `john@acme.com` | `contact@gmail.com` |
| **Phone** | `+1-555-123-4567` | `5551234567` | `(main office)` |
| **Domain** | `acme.com` | `www.acme.com` | `facebook.com/acme` |
| **Name** | `Acme Corporation` | `ACME CORP` | `Acme` |

**Normalization handles**:
- Phone: Any format normalized to E.164 (+15551234567)
- Email: Case normalized, whitespace trimmed
- Domain: Strips `www.`, `http://`, trailing paths
- Name: Removes legal suffixes (Inc, LLC, Corp)

### Preventing False Matches

To prevent matching different businesses, ensure:

1. **Email is business-specific**, not generic (info@company.com better than contact@gmail.com)
2. **Phone is direct line**, not shared call center number
3. **Name includes differentiators** ("Joe's Pizza NYC" not just "Joe's Pizza")

---

## Debugging Match Decisions

### Enable Debug Logging

```python
import logging

# See field-level comparison details
logging.getLogger("autom8_asana.models.business.matching").setLevel(logging.DEBUG)

# See candidate retrieval
logging.getLogger("autom8_asana.models.business.seeder").setLevel(logging.DEBUG)
```

**Example debug output**:

```
DEBUG - Comparing email: 'info@acme.com' vs 'info@acme.com' -> match, weight=8.0
DEBUG - Comparing phone: '+15551234567' vs '+15551234999' -> non-match, weight=-4.0
DEBUG - Comparing name: 'acme corp' vs 'acme corporation' -> fuzzy 0.92, weight=4.5
DEBUG - Total log-odds: 8.5, probability: 0.9998
INFO - Business match found by composite matching: gid=123456, score=0.9998
```

### Inspecting Match Results

```python
from autom8_asana.models.business.matching import MatchingEngine, MatchingConfig

# Create engine to inspect comparisons
engine = MatchingEngine()

# Compare specific records
result = engine.compute_match(
    query=BusinessData(name="Acme Corp", email="info@acme.com"),
    candidate=Candidate(gid="123", name="Acme Corporation", email="info@acme.com"),
)

# Inspect decision
print(f"Match: {result.is_match}")
print(f"Score: {result.score:.3f}")
print(f"Threshold: {result.threshold}")
print(f"Fields compared: {result.fields_compared}")

# Per-field breakdown
for comp in result.comparisons:
    if comp.contributed:
        print(f"  {comp.field_name}: {comp.left_value} vs {comp.right_value}")
        print(f"    similarity={comp.similarity}, weight={comp.weight_applied}")
```

### Log Dict for Structured Logging

```python
# Get structured log data for monitoring systems
log_data = result.to_log_dict()
# Returns: {
#   "match_type": "composite",
#   "score": 0.999,
#   "threshold": 0.80,
#   "fields_compared": 3,
#   "weights": {"email": 8.0, "name": 4.5, "domain": 5.0},
#   "candidate_gid": "123456"
# }
```

---

## Troubleshooting

### No Match Found When Expected

**Symptoms**: Same business creates duplicates instead of matching.

**Checklist**:

1. **Check field availability**
   ```python
   # Ensure at least 2 fields have values
   print(f"Email: {business_data.email}")
   print(f"Phone: {business_data.phone}")
   print(f"Domain: {business_data.domain}")
   ```

2. **Verify normalization**
   ```python
   from autom8_asana.models.business.matching import PhoneNormalizer

   normalizer = PhoneNormalizer()
   print(normalizer.normalize("(555) 123-4567"))  # Should be +15551234567
   ```

3. **Check threshold settings**
   ```bash
   # Current threshold
   echo $SEEDER_MATCH_THRESHOLD

   # Lower if too strict
   export SEEDER_MATCH_THRESHOLD=0.70
   ```

4. **Enable debug logging** to see actual comparison values.

### Too Many False Positives

**Symptoms**: Different businesses being matched together.

**Solutions**:

1. **Raise threshold**
   ```bash
   export SEEDER_MATCH_THRESHOLD=0.90
   ```

2. **Require more fields**
   ```bash
   export SEEDER_MIN_FIELDS=3
   ```

3. **Tighten fuzzy matching**
   ```bash
   export SEEDER_FUZZY_MEDIUM_THRESHOLD=0.90
   ```

4. **Check for shared generic domains** (gmail.com, yahoo.com). Term frequency adjustment reduces weight, but very common domains may still cause issues.

### Matching Fails Silently

**Symptoms**: Always creates new business, never matches.

**Check**:

1. **SearchService availability**
   ```python
   # Test search independently
   result = await client.search.find_async(
       project_gid=Business.PRIMARY_PROJECT_GID,
       query={"name": "test"},
       entity_type="Business",
   )
   print(f"Found {len(result.hits)} candidates")
   ```

2. **Error logs** - matching fails gracefully and logs warnings:
   ```python
   logging.getLogger("autom8_asana.models.business.seeder").setLevel(logging.WARNING)
   ```

3. **Configuration validation**
   ```python
   from autom8_asana.models.business.matching import MatchingConfig

   config = MatchingConfig()  # Raises ValidationError if env vars invalid
   print(f"Threshold: {config.match_threshold}")
   ```

### Performance Issues

**Symptoms**: Seeding is slow with large datasets.

**Solutions**:

1. **Provide company_id when available** - Tier 1 is O(1), skips composite matching
2. **Limit candidates** - Search returns max 50 candidates by default
3. **Install rapidfuzz** - Faster Jaro-Winkler implementation:
   ```bash
   pip install rapidfuzz
   ```

---

## Error Handling

The seeder uses graceful degradation. If composite matching fails, it falls back to creating a new business rather than failing the entire operation.

```python
try:
    result = await seeder.seed_async(
        business=BusinessData(name="Acme Corp"),
        process=ProcessData(name="Demo", process_type=ProcessType.SALES),
    )
except Exception as e:
    # Seeder errors are rare - usually infrastructure issues
    logger.error(f"Seeder failed: {e}")
    raise
```

### Expected Warnings

These are informational, not errors:

```
WARNING - Composite matching failed, will create new business
WARNING - Search by company_id failed: [connection error]
WARNING - Multiple businesses found with same company_id
```

The seeder continues operating by creating new businesses when matching fails.

---

## API Reference

### BusinessData

```python
class BusinessData(BaseModel):
    """Input data for business creation and matching."""

    name: str                              # Required
    company_id: str | None = None          # Tier 1 exact match key
    email: str | None = None               # High-weight matching field
    phone: str | None = None               # High-weight matching field
    domain: str | None = None              # Medium-weight matching field
    business_address_line_1: str | None = None
    business_city: str | None = None
    business_state: str | None = None
    business_zip: str | None = None
    vertical: str | None = None
```

### SeederResult

```python
@dataclass
class SeederResult:
    """Result of seeding operation."""

    business: Business           # The found or created business
    unit: Unit                   # The unit under the business
    process: Process             # The created process
    contact: Contact | None      # Optional created contact
    created_business: bool       # True if new, False if matched
    created_unit: bool           # True if new unit created
    created_contact: bool        # True if contact was created
    warnings: list[str]          # Any non-fatal warnings
```

### MatchingConfig

See [Configuration Reference](../reference/REF-seeder-matching-config.md) for complete environment variable documentation.

---

## See Also

- **Configuration**: [REF-seeder-matching-config](../reference/REF-seeder-matching-config.md) - All environment variables
- **Architecture**: [TDD-08 Section 8](../design/TDD-08-business-domain.md#8-composite-matching-architecture) - Design rationale
- **Search API**: [REF-search-api](../reference/REF-search-api.md) - Underlying search capabilities
- **Query Builder**: [GUIDE-search-query-builder](./search-query-builder.md) - Building search queries

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-28 | Initial guide for v2 composite matching |
