# ADR-0058: Fellegi-Sunter Probabilistic Matching for Business Deduplication

## Metadata

- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-28
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: None (new decision)
- **Related**: PRD-06-business-domain (FR-M-001 through FR-M-012), TDD-08-business-domain (Section 8), ADR-0016 (Business Entity Seeding), REF-seeder-matching-config

## Context

BusinessSeeder v1 used a simple two-tier matching strategy for business deduplication:

1. **Exact company_id match**: If `company_id` is provided and matches, return existing business
2. **Exact name match**: If name matches exactly, return existing business
3. **Create new**: Otherwise create a new business

This approach has significant limitations:

**Forces at play:**

1. **Data Quality Variability**: Incoming data from webhooks, forms, and integrations varies in quality. Business names include typos ("Acme Corpp"), abbreviations ("Acme Corp" vs "Acme Corporation"), and legal suffix variations ("Acme LLC" vs "Acme, LLC").

2. **Duplicate Prevention**: Creating duplicate business records causes downstream problems: inaccurate MRR reporting, fragmented contact history, and manual cleanup burden.

3. **False Positive Prevention**: Incorrectly merging distinct businesses (e.g., "Smith LLC" in Chicago with "Smith LLC" in New York) corrupts data irreversibly.

4. **Multiple Corroborating Fields**: Real-world deduplication requires evaluating multiple fields (email, phone, name, domain, address) with varying reliability levels.

5. **Configurable Thresholds**: Different deployments have different tolerance for false positives vs false negatives. Financial data needs stricter matching; sales pipelines may prefer catching more duplicates.

6. **Operational Transparency**: Match decisions must be auditable. When a match occurs, operators need to understand why.

**Problem**: How should BusinessSeeder evaluate whether incoming business data represents an existing business, when exact matching is insufficient but probabilistic matching risks false positives?

## Decision

**Implement the Fellegi-Sunter probabilistic record linkage model for composite business matching.**

The matching engine uses log-odds accumulation across multiple fields to compute a match probability, with configurable thresholds for match/non-match decisions.

### Core Algorithm

```python
class MatchingEngine:
    """Fellegi-Sunter probabilistic matching engine.

    Uses log-odds accumulation for principled score combination.
    """

    def compute_match(
        self,
        query: BusinessData,
        candidate: Candidate,
    ) -> MatchResult:
        """Compute match score between query and candidate.

        Algorithm:
        1. Normalize fields (email, phone, name, domain)
        2. Compare each field, accumulating log-odds
        3. Convert sum to probability
        4. Apply minimum evidence threshold
        5. Compare against match threshold
        """
        total_log_odds = 0.0
        fields_compared = 0

        for field in [email, phone, name, domain]:
            comparison = self._compare_field(query, candidate, field)
            if comparison.contributed:
                total_log_odds += comparison.weight_applied
                fields_compared += 1

        probability = self._log_odds_to_probability(total_log_odds)

        # Minimum evidence threshold
        if fields_compared < self._config.min_fields:
            return MatchResult(is_match=False, ...)

        return MatchResult(
            is_match=probability >= self._config.match_threshold,
            score=probability,
            raw_score=total_log_odds,
            ...
        )
```

### Log-Odds Scale

The Fellegi-Sunter model uses log-odds rather than raw probabilities for score combination:

```
log_odds = log(P(match|agreement) / P(non-match|agreement))

# For multiple fields, log-odds are additive:
total_log_odds = email_log_odds + phone_log_odds + name_log_odds + ...

# Convert back to probability:
probability = exp(total_log_odds) / (1 + exp(total_log_odds))
```

**Default field weights (log-odds scale):**

| Field | Match Weight | Non-Match Weight | Rationale |
|-------|--------------|------------------|-----------|
| Email | +8.0 | -4.0 | Highly unique identifier |
| Phone | +7.0 | -4.0 | Unique but formatting varies |
| Name | +6.0 | -3.0 | Subject to abbreviation/typos |
| Domain | +5.0 | -2.0 | Multiple businesses share domains |

### Blocking Rules for Performance

Without optimization, comparing a query against N existing records requires N full comparisons. The engine uses blocking rules to reduce the candidate set:

```python
class CompositeBlockingRule:
    """Pass if ANY sub-rule matches (OR logic).

    Sub-rules:
    - DomainBlockingRule: Exact domain match required
    - PhonePrefixBlockingRule: First 6 digits must match
    - NameTokenBlockingRule: Shared significant tokens
    """
```

Blocking achieves O(n) performance by filtering candidates before expensive comparison.

### Minimum Evidence Threshold

To prevent false positives from insufficient data, the engine requires a minimum number of non-null field comparisons:

```python
# Default: Require at least 2 non-null field comparisons
if fields_compared < self._config.min_fields:
    return MatchResult(is_match=False, reason="insufficient_evidence")
```

This prevents matching two records solely because they share a common email domain like `gmail.com`.

### Asymmetric Weights

Match and non-match weights are intentionally asymmetric:

- **Email match (+8.0)** vs **Email non-match (-4.0)**
- **Name match (+6.0)** vs **Name non-match (-3.0)**

Rationale: Legitimate variation exists (businesses have multiple emails, DBAs, abbreviations). We penalize disagreement less than we reward agreement.

### Configuration via Environment

All parameters are configurable via `SEEDER_*` environment variables:

```bash
export SEEDER_MATCH_THRESHOLD=0.80    # Probability threshold
export SEEDER_MIN_FIELDS=2            # Minimum evidence
export SEEDER_EMAIL_WEIGHT=8.0        # Field weights
export SEEDER_FUZZY_EXACT_THRESHOLD=0.95  # Jaro-Winkler thresholds
```

See [REF-seeder-matching-config](../reference/REF-seeder-matching-config.md) for complete reference.

## Rationale

### Why Fellegi-Sunter Model

1. **Mathematical Foundation**: Fellegi-Sunter (1969) is the foundational theory of probabilistic record linkage. It provides theoretical optimality guarantees under certain assumptions.

2. **Log-Odds Additivity**: Unlike raw probabilities (which multiply and quickly approach zero), log-odds are additive. This makes score combination mathematically sound and numerically stable.

3. **Principled Weight Assignment**: Weights represent likelihood ratios between match and non-match populations. This has clear statistical interpretation.

4. **Industry Standard**: Used by census bureaus (U.S. Census, Statistics Canada), healthcare systems (patient matching), and financial institutions (anti-money laundering). Well-studied properties and failure modes.

5. **Explainability**: Each field's contribution to the final score is explicit. Audit logs can show exactly why a match was (or wasn't) made.

### Why Log-Odds Instead of Probability Multiplication

Consider matching on email and phone:

**Probability multiplication approach:**
```
P(match|email) = 0.99
P(match|phone) = 0.98
P(match|both) = 0.99 * 0.98 = 0.9702
```

Problems:
- Probabilities multiply toward zero with more fields
- Numerical underflow with many weak signals
- No principled way to combine match/non-match evidence

**Log-odds approach:**
```
log_odds(email) = log(0.99/0.01) = 4.6
log_odds(phone) = log(0.98/0.02) = 3.9
total_log_odds = 4.6 + 3.9 = 8.5
probability = exp(8.5) / (1 + exp(8.5)) = 0.9998
```

Benefits:
- Additive combination is mathematically correct
- Numerically stable across any number of fields
- Non-match evidence subtracts naturally

### Why Blocking Rules

Without blocking, comparing a query against 10,000 existing businesses requires 10,000 full comparisons. With domain blocking:

```
Query: domain = "acme.com"
Candidates with "acme.com": ~5-10
Comparisons needed: 5-10 (not 10,000)
```

Blocking provides O(n) performance while preserving recall (OR logic ensures candidates matching any rule are compared).

### Why Minimum Field Requirement

Two businesses might both have:
- Email: `info@gmail.com` (common)
- Phone: `null`
- Name: `null`
- Domain: `gmail.com` (common)

Without minimum evidence, the matching engine would compare only email, and `gmail.com` matches `gmail.com`. Result: false positive.

The minimum field requirement ensures sufficient evidence before declaring a match.

## Alternatives Considered

### Alternative 1: Machine Learning Classification

- **Description**: Train a binary classifier (logistic regression, random forest, neural network) on labeled match/non-match pairs
- **Pros**: Can learn complex patterns; may achieve higher accuracy with sufficient training data; adapts to domain-specific patterns
- **Cons**: Requires labeled training data (expensive to create); model drift requires retraining; less interpretable; deployment complexity
- **Why not chosen**: Our scale (~10,000 businesses) doesn't justify ML complexity. Fellegi-Sunter achieves good accuracy with transparent, configurable rules. ML can be added later if needed.

### Alternative 2: Rule-Based Exact Matching (Status Quo)

- **Description**: Match on exact company_id, then exact name, then create new
- **Pros**: Simple implementation; deterministic behavior; no configuration needed; fast execution
- **Cons**: Misses duplicates with typos, abbreviations, or variations; no confidence scoring; binary match/no-match with no gradations
- **Why not chosen**: Insufficient for real-world data quality. "Acme Corp" vs "Acme Corporation" creates duplicates, causing downstream data quality issues.

### Alternative 3: Edit Distance Only (Levenshtein)

- **Description**: Compute Levenshtein distance between business names; match if distance below threshold
- **Pros**: Simple to implement; handles typos well; single metric to tune
- **Cons**: No field-specific weighting (email typo treated same as name typo); sensitive to string length; doesn't handle abbreviations well; no principled way to combine multiple fields
- **Why not chosen**: Single-field approach ignores valuable corroborating evidence. "Acme" matching "Beta" with similar email/phone should match; pure edit distance would reject.

### Alternative 4: Commercial Data Quality Platform

- **Description**: Integrate with platforms like Informatica, Talend, or Melissa Data for matching
- **Pros**: Enterprise-grade accuracy; handles address standardization; maintained by vendor; compliance certifications
- **Cons**: Licensing cost ($10K-100K+/year); external dependency; data leaves our systems; vendor lock-in; integration complexity
- **Why not chosen**: Cost disproportionate to scale. Self-hosted Fellegi-Sunter provides sufficient accuracy for current needs without external dependencies.

### Alternative 5: Hash-Based Deduplication

- **Description**: Generate normalized hashes of business records; exact hash match indicates duplicate
- **Pros**: O(1) lookup; deterministic; simple implementation; works well for exact duplicates
- **Cons**: Any variation (typo, formatting) produces different hash; all-or-nothing matching; no fuzzy tolerance; no confidence scoring
- **Why not chosen**: Too brittle for real-world data. Minor variations in input would miss obvious duplicates.

## Consequences

### Positive

1. **Catches duplicates with variations**: "Acme Corp" matches "Acme Corporation" via fuzzy name matching
2. **Configurable per deployment**: Strict matching for financial data (threshold=0.90), lenient for sales pipelines (threshold=0.70)
3. **Explainable decisions**: MatchResult includes field-by-field comparison detail for audit
4. **Graceful degradation**: Falls back to creating new business if matching fails
5. **Backward compatible**: Existing API unchanged; new fields optional
6. **O(n) performance**: Blocking rules prevent quadratic explosion
7. **12-factor configuration**: All thresholds via environment variables, no code changes needed

### Negative

1. **Threshold tuning required**: Default thresholds work for general cases but may need adjustment for specific domains
2. **False positives possible**: Lenient thresholds or insufficient minimum evidence could merge distinct businesses
3. **Complexity added**: MatchingEngine, normalizers, comparators, blocking rules add ~500 lines of code
4. **Configuration surface area**: 17 environment variables to understand and potentially tune
5. **Fuzzy matching overhead**: Jaro-Winkler comparison is more expensive than exact matching (~10x per comparison)

### Neutral

1. **Audit logging**: Match decisions logged with field details (respects PII controls)
2. **Term frequency adjustment**: Common values (gmail.com) contribute less weight
3. **Requires search API**: Candidate retrieval uses Asana search, adding API dependency
4. **Three-tier matching**: Exact company_id still takes priority over composite matching

## Compliance

### Code Location

Implementation lives in the matching module:

```
src/autom8_asana/models/business/matching/
    __init__.py      # Public exports
    engine.py        # MatchingEngine.compute_match()
    config.py        # MatchingConfig (pydantic-settings)
    models.py        # MatchResult, FieldComparison, Candidate
    normalizers.py   # Phone, Email, BusinessName, Domain normalizers
    comparators.py   # ExactComparator, FuzzyComparator
    blocking.py      # BlockingRule implementations
```

### Enforcement Mechanisms

1. **Type Safety**: All matching components use type hints; mypy enforced
2. **Configuration Validation**: Pydantic validates thresholds at startup (fail-fast)
3. **Unit Tests**: `tests/unit/models/business/matching/` covers all components
4. **Integration Tests**: End-to-end seeder tests verify matching behavior
5. **Audit Logging**: All match decisions logged with structured fields

### Test Requirements

```python
# Required test coverage per this ADR:

def test_fuzzy_name_matching():
    """'Acme Corp' matches 'Acme Corporation'."""

def test_minimum_evidence_prevents_false_positive():
    """Two gmail.com addresses alone do not match."""

def test_asymmetric_weights():
    """Non-match penalty is less than match reward."""

def test_blocking_reduces_candidates():
    """Domain blocking filters non-matching candidates."""

def test_log_odds_to_probability():
    """Verify conversion formula is correct."""

def test_graceful_degradation():
    """Matching failure proceeds to create new business."""
```

### Documentation Requirements

- REF-seeder-matching-config: Complete configuration reference
- TDD-08-business-domain Section 8: Architecture overview
- PRD-06-business-domain FR-M-*: Functional requirements

## Implementation Guidance

### When to Tune Thresholds

1. **False positives observed**: Increase `SEEDER_MATCH_THRESHOLD` to 0.85-0.90
2. **Missing obvious duplicates**: Decrease `SEEDER_MATCH_THRESHOLD` to 0.70-0.75
3. **Matching on sparse data**: Decrease `SEEDER_MIN_FIELDS` to 1 (risky)
4. **Common value pollution**: Ensure `SEEDER_TF_ENABLED=true`

### When to Add New Fields

To add a new comparison field (e.g., address):

1. Add normalizer in `normalizers.py`
2. Add comparison method in `engine.py`
3. Add weight configuration in `config.py`
4. Add environment variables to documentation
5. Update tests

### Monitoring

Watch these metrics:

- `seeder.match_rate`: Percentage of seeds finding existing business
- `seeder.match_type_distribution`: Breakdown by exact/composite/no_match
- `seeder.average_score`: Mean probability score for matches
- `seeder.blocking_reduction`: Candidate count before/after blocking

---

## References

- Fellegi, I. P., & Sunter, A. B. (1969). A Theory for Record Linkage. *Journal of the American Statistical Association*, 64(328), 1183-1210.
- Winkler, W. E. (2006). Overview of Record Linkage and Current Research Directions. *U.S. Census Bureau*.
- Christen, P. (2012). *Data Matching: Concepts and Techniques for Record Linkage, Entity Resolution, and Duplicate Detection*. Springer.
