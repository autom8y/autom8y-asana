---
domain: feat/fuzzy-entity-matching
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/models/business/matching/**/*.py"
  - "./src/autom8_asana/services/matching_service.py"
  - "./src/autom8_asana/api/routes/matching.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# Fuzzy Matching Engine for Entity Deduplication

## Purpose and Design Rationale

The fuzzy matching engine solves deduplication: when an external consumer submits business identity data (name, phone, email, domain), the system determines whether that business already exists in the Asana project database without executing a live Asana API call at query time.

The engine reads exclusively from the cached Business DataFrame held in memory from warm-up. It is hidden from the public OpenAPI schema (`include_in_schema=False`) and restricted to S2S JWT authentication.

## Conceptual Model

**Fellegi-Sunter probabilistic record linkage** is the framework. Log-odds accumulate across fields:

1. **Blocking** (candidate pruning): `CompositeBlockingRule` with OR logic -- domain exact, phone prefix (6 digits), name token overlap
2. **Normalization**: `PhoneNormalizer` (E.164), `EmailNormalizer`, `BusinessNameNormalizer`, `DomainNormalizer`
3. **Comparison**: `ExactComparator` (email, phone, domain) and `FuzzyComparator` (Jaro-Winkler for name, `rapidfuzz` with `difflib` fallback)
4. **Log-odds accumulation**: email +8/-4, phone +7/-4, name +6/-3, domain +5/-2. Null fields contribute 0.0 (neutral)
5. **Term frequency adjustment**: Domain field weight reduced for common domains (gmail.com, yahoo.com)
6. **Decision**: Sigmoid of log-odds >= `match_threshold` (0.80), minimum 2 non-null fields

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/models/business/matching/engine.py` | `MatchingEngine.compute_match()`, `find_best_match()` |
| `src/autom8_asana/models/business/matching/blocking.py` | `CompositeBlockingRule` with 3 rule implementations |
| `src/autom8_asana/models/business/matching/comparators.py` | `ExactComparator`, `FuzzyComparator`, `TermFrequencyAdjuster` |
| `src/autom8_asana/models/business/matching/normalizers.py` | 5 normalizer classes |
| `src/autom8_asana/models/business/matching/models.py` | `FieldComparison`, `MatchResult`, `Candidate` |
| `src/autom8_asana/models/business/matching/config.py` | `MatchingConfig` with `env_prefix="SEEDER_"` |
| `src/autom8_asana/services/matching_service.py` | `MatchingService.query()` orchestration |
| `src/autom8_asana/api/routes/matching.py` | `POST /v1/matching/query` (hidden, S2S JWT) |

**Test coverage**: 7 test files covering engine, blocking, comparators, normalizers, service, route, and models.

## Boundaries and Failure Modes

**No Asana API calls at query time**: The service receives a pre-fetched DataFrame.

**Scar intersections**: SCAR-020/SCAR-024 (PhoneNormalizer), SCAR-024 (PhoneTextField descriptor parallel implementation).

**DataFrame column contract**: `_dataframe_to_candidates()` assumes specific column names; missing columns silently become `None`.

**Per-request config**: `MatchingConfig.from_env()` re-parses env vars on every request.

## Knowledge Gaps

1. **Address comparison dead code**: `AddressNormalizer` defined but not wired into `engine.py:compute_match()`.
2. **`TermFrequencyAdjuster.update_frequencies()` has no observed call site**.
3. **Blocking false-pass rate under null-heavy data** not characterized.
4. **Per-request `MatchingConfig.from_env()` cost** not benchmarked.
