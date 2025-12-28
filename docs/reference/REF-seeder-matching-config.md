# Seeder Matching Configuration Reference

Environment variable reference for BusinessSeeder v2 composite matching.

**Module**: `autom8_asana.models.business.matching.config`

**Class**: `MatchingConfig`

---

## Overview

The BusinessSeeder uses Fellegi-Sunter probabilistic matching for business deduplication. All matching parameters are configurable via environment variables with the `SEEDER_` prefix, following 12-factor app principles.

**Key characteristics**:
- Environment-based configuration (no code changes required)
- Changes take effect on application restart
- Sensible defaults work out-of-box without configuration
- All thresholds validate ranges at startup via Pydantic

```python
from autom8_asana.models.business.matching import MatchingConfig

# Load from environment (default)
config = MatchingConfig()

# Or explicit factory method
config = MatchingConfig.from_env()

# Override specific values
config = MatchingConfig(match_threshold=0.85, min_fields=3)
```

---

## Quick Reference

| Variable | Default | Range | Description |
|----------|---------|-------|-------------|
| `SEEDER_MATCH_THRESHOLD` | `0.80` | 0.0-1.0 | Probability threshold for match decision |
| `SEEDER_MIN_FIELDS` | `2` | >= 1 | Minimum non-null field comparisons required |
| `SEEDER_EMAIL_WEIGHT` | `8.0` | any | Log-odds weight for email match |
| `SEEDER_PHONE_WEIGHT` | `7.0` | any | Log-odds weight for phone match |
| `SEEDER_NAME_WEIGHT` | `6.0` | any | Log-odds weight for name match |
| `SEEDER_DOMAIN_WEIGHT` | `5.0` | any | Log-odds weight for domain match |
| `SEEDER_ADDRESS_WEIGHT` | `4.0` | any | Log-odds weight for address match |
| `SEEDER_EMAIL_NONMATCH` | `-4.0` | any | Negative weight for email non-match |
| `SEEDER_PHONE_NONMATCH` | `-4.0` | any | Negative weight for phone non-match |
| `SEEDER_NAME_NONMATCH` | `-3.0` | any | Negative weight for name non-match |
| `SEEDER_DOMAIN_NONMATCH` | `-2.0` | any | Negative weight for domain non-match |
| `SEEDER_ADDRESS_NONMATCH` | `-2.0` | any | Negative weight for address non-match |
| `SEEDER_FUZZY_EXACT_THRESHOLD` | `0.95` | 0.0-1.0 | Jaro-Winkler threshold for full weight |
| `SEEDER_FUZZY_HIGH_THRESHOLD` | `0.90` | 0.0-1.0 | Jaro-Winkler threshold for 75% weight |
| `SEEDER_FUZZY_MEDIUM_THRESHOLD` | `0.80` | 0.0-1.0 | Jaro-Winkler threshold for 50% weight |
| `SEEDER_TF_ENABLED` | `true` | boolean | Enable term frequency adjustment |
| `SEEDER_TF_COMMON_THRESHOLD` | `0.01` | 0.0-1.0 | Frequency threshold for "common" values (>1%) |

---

## Threshold Configuration

### Match Threshold

The `SEEDER_MATCH_THRESHOLD` determines when the matching engine declares a match. The engine computes a probability score (0.0-1.0) from accumulated log-odds; if this exceeds the threshold, the pair is considered a match.

```bash
# Default: 80% confidence required
export SEEDER_MATCH_THRESHOLD=0.80

# Stricter: 90% confidence (fewer matches, fewer false positives)
export SEEDER_MATCH_THRESHOLD=0.90

# Lenient: 70% confidence (more matches, more false positives)
export SEEDER_MATCH_THRESHOLD=0.70
```

**Guidance**:
- `0.90-0.95`: Strict matching. Use when false positives are costly (e.g., financial data).
- `0.75-0.85`: Balanced matching. Default operating range for general deduplication.
- `0.60-0.75`: Lenient matching. Use for catching more duplicates with manual review.

### Minimum Fields

The `SEEDER_MIN_FIELDS` setting prevents matching decisions based on insufficient evidence. If fewer than this many fields contribute to the comparison, the result is automatically "no match."

```bash
# Default: Require at least 2 non-null field comparisons
export SEEDER_MIN_FIELDS=2

# Stricter: Require 3 fields (more robust but may miss sparse records)
export SEEDER_MIN_FIELDS=3

# Lenient: Allow single-field matches (risky for common field values)
export SEEDER_MIN_FIELDS=1
```

A field "contributes" when both the query and candidate have non-null values for that field. Null fields are treated as neutral (zero weight).

---

## Field Weights

The matching engine uses log-odds weights from the Fellegi-Sunter model. Positive weights increase match probability when fields agree; negative weights decrease it when fields disagree.

### Weight Scale Reference

Log-odds weights map to probability impact:

| Log-Odds | Probability Impact |
|----------|-------------------|
| +8.0 | Strong evidence for match (~99.97%) |
| +6.0 | Good evidence for match (~99.75%) |
| +4.0 | Moderate evidence (~98.2%) |
| +2.0 | Weak evidence (~88%) |
| 0.0 | Neutral (no impact) |
| -2.0 | Weak evidence against (~12%) |
| -4.0 | Moderate evidence against (~1.8%) |

### Match Weights (Positive)

These weights apply when field values match (or meet fuzzy threshold):

| Variable | Default | Rationale |
|----------|---------|-----------|
| `SEEDER_EMAIL_WEIGHT` | `8.0` | Highly unique identifier. Exact email match is strong evidence. |
| `SEEDER_PHONE_WEIGHT` | `7.0` | Unique but formatting varies. Slightly less discriminative than email. |
| `SEEDER_NAME_WEIGHT` | `6.0` | Common names reduce uniqueness. Fuzzy matching adds uncertainty. |
| `SEEDER_DOMAIN_WEIGHT` | `5.0` | Less unique than email. Multiple businesses share domains. |
| `SEEDER_ADDRESS_WEIGHT` | `4.0` | Often incomplete or abbreviated. Multi-tenant buildings reduce uniqueness. |

### Non-Match Weights (Negative)

These weights apply when field values differ:

| Variable | Default | Rationale |
|----------|---------|-----------|
| `SEEDER_EMAIL_NONMATCH` | `-4.0` | Different emails strongly suggest different businesses. |
| `SEEDER_PHONE_NONMATCH` | `-4.0` | Different phones suggest different businesses. |
| `SEEDER_NAME_NONMATCH` | `-3.0` | Names may differ (DBA, abbreviation) even for same business. |
| `SEEDER_DOMAIN_NONMATCH` | `-2.0` | Businesses may have multiple domains. |
| `SEEDER_ADDRESS_NONMATCH` | `-2.0` | Businesses may have multiple locations. |

**Key principle**: Non-match weights are asymmetric. We penalize disagreement less than we reward agreement because legitimate variation exists.

---

## Fuzzy Matching Thresholds

Name comparison uses Jaro-Winkler similarity with graduated weight levels. The fuzzy thresholds determine how much of the field weight applies based on similarity score.

| Threshold | Weight Applied | Example Similarity |
|-----------|---------------|-------------------|
| >= `SEEDER_FUZZY_EXACT_THRESHOLD` (0.95) | 100% of field weight | "Acme Corp" vs "Acme Corp" |
| >= `SEEDER_FUZZY_HIGH_THRESHOLD` (0.90) | 75% of field weight | "Acme Corp" vs "Acme Corporation" |
| >= `SEEDER_FUZZY_MEDIUM_THRESHOLD` (0.80) | 50% of field weight | "Acme Corp" vs "Acme Incorporated" |
| < `SEEDER_FUZZY_MEDIUM_THRESHOLD` | 0% (non-match) | "Acme Corp" vs "Beta Industries" |

```bash
# Example: Tighten fuzzy matching (require higher similarity)
export SEEDER_FUZZY_EXACT_THRESHOLD=0.98
export SEEDER_FUZZY_HIGH_THRESHOLD=0.95
export SEEDER_FUZZY_MEDIUM_THRESHOLD=0.85
```

**Implementation note**: Uses `rapidfuzz.distance.JaroWinkler` when available; falls back to `difflib.SequenceMatcher` otherwise. Install `rapidfuzz` for better performance.

---

## Term Frequency Adjustment

Common values (like `gmail.com` for domains) provide less discriminating power. Term frequency adjustment reduces weights for commonly occurring values.

### Configuration

```bash
# Enable/disable TF adjustment (default: enabled)
export SEEDER_TF_ENABLED=true

# Threshold for "common" classification (default: 1% frequency)
export SEEDER_TF_COMMON_THRESHOLD=0.01
```

### Built-in Common Values

The engine pre-loads frequency data for known common values:

**Common email domains** (5% frequency):
- gmail.com, yahoo.com, hotmail.com, outlook.com, aol.com
- icloud.com, live.com, msn.com, mail.com, protonmail.com

**Common US cities** (2% frequency):
- new york, los angeles, chicago, houston, phoenix
- philadelphia, san antonio, san diego, dallas, austin
- (and 10 more major cities)

Matching on `gmail.com` receives reduced weight (~1.0 instead of 5.0) because many unrelated businesses use Gmail.

---

## Configuration Profiles

### Strict Matching (Avoid False Positives)

Use when duplicate creation is preferable to false matches.

```bash
export SEEDER_MATCH_THRESHOLD=0.90
export SEEDER_MIN_FIELDS=3
export SEEDER_FUZZY_EXACT_THRESHOLD=0.98
export SEEDER_FUZZY_HIGH_THRESHOLD=0.95
export SEEDER_FUZZY_MEDIUM_THRESHOLD=0.90
```

**Effect**: Requires high confidence across multiple fields. Reduces merging of similar but distinct businesses.

### Lenient Matching (Catch More Duplicates)

Use when missing duplicates is costly and manual review is available.

```bash
export SEEDER_MATCH_THRESHOLD=0.70
export SEEDER_MIN_FIELDS=1
export SEEDER_FUZZY_EXACT_THRESHOLD=0.90
export SEEDER_FUZZY_HIGH_THRESHOLD=0.85
export SEEDER_FUZZY_MEDIUM_THRESHOLD=0.75
```

**Effect**: Lower bar for match declaration. More aggressive duplicate detection.

### High-Precision Mode (Exact Fields Only)

Disable fuzzy matching for stricter control.

```bash
export SEEDER_MATCH_THRESHOLD=0.85
export SEEDER_NAME_WEIGHT=2.0       # Reduce name importance
export SEEDER_FUZZY_MEDIUM_THRESHOLD=0.99  # Effectively require exact
```

**Effect**: Reduces impact of fuzzy name matching. Relies more on email/phone.

---

## Validation

Configuration validates at instantiation. Invalid values raise `ValidationError`:

```python
from pydantic import ValidationError
from autom8_asana.models.business.matching import MatchingConfig

try:
    config = MatchingConfig(match_threshold=1.5)  # Invalid: > 1.0
except ValidationError as e:
    print(e)
    # match_threshold: Input should be less than or equal to 1.0
```

Range constraints:
- `match_threshold`: 0.0-1.0
- `min_fields`: >= 1
- `fuzzy_*_threshold`: 0.0-1.0
- `tf_common_threshold`: 0.0-1.0
- Weight fields: no constraints (log-odds can be any float)

---

## Runtime Access

Access current configuration from the matching engine:

```python
from autom8_asana.models.business.matching import MatchingEngine

engine = MatchingEngine()

# Read current thresholds
print(f"Match threshold: {engine.config.match_threshold}")
print(f"Email weight: {engine.config.email_weight}")

# Get weight by field name
email_weight = engine.config.get_field_weight("email")  # 8.0
email_nonmatch = engine.config.get_nonmatch_weight("email")  # -4.0
```

---

## Environment File Example

Complete `.env` configuration with all defaults:

```bash
# Seeder Matching Configuration
# All values shown are defaults - only override what you need

# Decision thresholds
SEEDER_MATCH_THRESHOLD=0.80
SEEDER_MIN_FIELDS=2

# Match weights (log-odds, positive)
SEEDER_EMAIL_WEIGHT=8.0
SEEDER_PHONE_WEIGHT=7.0
SEEDER_NAME_WEIGHT=6.0
SEEDER_DOMAIN_WEIGHT=5.0
SEEDER_ADDRESS_WEIGHT=4.0

# Non-match weights (log-odds, negative)
SEEDER_EMAIL_NONMATCH=-4.0
SEEDER_PHONE_NONMATCH=-4.0
SEEDER_NAME_NONMATCH=-3.0
SEEDER_DOMAIN_NONMATCH=-2.0
SEEDER_ADDRESS_NONMATCH=-2.0

# Fuzzy thresholds (Jaro-Winkler similarity)
SEEDER_FUZZY_EXACT_THRESHOLD=0.95
SEEDER_FUZZY_HIGH_THRESHOLD=0.90
SEEDER_FUZZY_MEDIUM_THRESHOLD=0.80

# Term frequency adjustment
SEEDER_TF_ENABLED=true
SEEDER_TF_COMMON_THRESHOLD=0.01
```

---

## Related Documentation

- [BusinessSeeder v2 Guide](../guides/GUIDE-businessseeder-v2.md): End-to-end seeding workflow
- [TDD-08 Business Domain](../design/TDD-08-business-domain.md): Architecture and design rationale
- [PRD-06 Business Domain](../requirements/PRD-06-business-domain.md): Functional requirements
- [ADR-0016 Business Entity Seeding](../decisions/ADR-0016-business-entity-seeding.md): Seeding architecture decision
