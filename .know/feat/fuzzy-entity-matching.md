---
domain: feat/fuzzy-entity-matching
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/models/business/matching/"
  - "./src/autom8_asana/api/routes/matching.py"
  - "./src/autom8_asana/services/matching_service.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.93
format_version: "1.0"
---

# Fuzzy Entity Matching

## Purpose and Design Rationale

The fuzzy entity matching engine solves **business entity deduplication**: when an external consumer submits business identity data (name, phone, email, domain), the system determines whether that business already exists in the Asana project database without issuing a live Asana API call at query time.

The problem it solves: external seeding pipelines repeatedly inject the same businesses with minor variations in formatting, spelling, or completeness. Without probabilistic matching, each variant would create a duplicate Asana task hierarchy. The engine provides a principled, threshold-based deduplication gate.

### Design Decisions and Rationale

**Decision 1: Fellegi-Sunter probabilistic record linkage** (per TDD FR-M-001). Log-odds accumulate across independently-scored fields. This model was chosen over simpler string similarity because it handles partial information gracefully — null fields contribute 0.0 (neutral), not negative. Decision documented in `ADR-SEEDER-003`: log-odds are used internally, probability is exposed in the API.

**Decision 2: Blocking before scoring** (per TDD ADR-SEEDER-004). All candidates are first pruned to those likely to match using cheap heuristics (domain exact, phone prefix, name token overlap) before the scoring pass. This is a performance architectural decision — reduces comparison cost from O(n²) to O(n) for large DataFrame corpora.

**Decision 3: In-memory DataFrame source** (per ADR constraint in `matching_service.py` docstring). The engine reads exclusively from the cached Business DataFrame; it must NOT make direct Asana API calls during a matching query. This ensures query latency is bounded and cache-warm state is a hard prerequisite.

**Decision 4: Hidden endpoint** (`include_in_schema=False`, HD-01). `POST /v1/matching/query` is excluded from the public OpenAPI spec. S2S JWT is required, matching PAT-blocked internal service consumers only.

**Decision 5: PII stripping on projection** (HD-01). `MatchingService._project_result()` strips `left_value`, `right_value`, `raw_score`, and weight details before returning to the API layer. Callers see only `score`, `is_match`, `similarity`, and `contributed` flags.

**Known tradeoff**: `MatchingService` is instantiated per-request inside the route handler (`matching.py:171`), which means `MatchingConfig.from_env()` re-parses environment variables on every request. This is a known performance gap (not yet benchmarked).

**Rejected alternative**: Asynchronous batch matching or offline deduplication pipelines were not used — the engine is designed for synchronous, per-request query-time resolution to support interactive seeding flows.

**Design document**: `docs/guides/GUIDE-businessseeder-v2.md` — integration guide for BusinessSeeder v2 with composite matching.

---

## Conceptual Model

### Fellegi-Sunter Pipeline (5 stages)

```
BusinessData (query)
    │
    ▼
1. BLOCKING — CompositeBlockingRule
   OR of: DomainBlockingRule | PhonePrefixBlockingRule | NameTokenBlockingRule
   → Prunes ~90% of DataFrame rows cheaply
    │
    ▼
2. NORMALIZATION — per-field normalizers applied at comparison time
   PhoneNormalizer → E.164  (+ NumberParseException guard, SCAR-020/SCAR-CANDIDATE-B)
   EmailNormalizer → lowercase, trim, validate @
   BusinessNameNormalizer → strip legal suffixes, unicode NFD, lowercase
   DomainNormalizer → strip protocol/www/path, lowercase
    │
    ▼
3. FIELD COMPARISON — per-field comparator strategy
   email/phone/domain → ExactComparator: 1.0/0.0 binary match
   name → FuzzyComparator: Jaro-Winkler (rapidfuzz primary, difflib fallback)
       Graduated: ≥0.95 → 1.0x, ≥0.90 → 0.75x, ≥0.80 → 0.50x, <0.80 → 0.0x
    │
    ▼
4. LOG-ODDS ACCUMULATION
   email:  match +8.0 / non-match -4.0
   phone:  match +7.0 / non-match -4.0
   name:   match +6.0×multiplier / non-match -3.0
   domain: match +5.0×TF_adjust / non-match -2.0
   Null field → 0.0 (neutral, FR-M-004)
    │
    ▼
5. DECISION
   sigmoid(total_log_odds) → probability [0.0-1.0]
   Requires min_fields=2 non-null comparisons (FR-M-003)
   is_match = probability ≥ match_threshold (default 0.80)
```

### Term Frequency Adjustment (TermFrequencyAdjuster)

Applies to domain field only in current engine wiring. Pre-loaded `COMMON_DOMAINS` frozenset (gmail.com, yahoo.com, etc.) and `COMMON_CITIES` frozenset (20 entries). When a domain frequency exceeds `tf_common_threshold` (1%), weight is reduced proportionally: `reduction = min(frequency × 10, 0.8)`. Gmail.com frequency is hardcoded to 0.05 (5%), resulting in a 50% weight reduction: 5.0 → 2.5.

`update_frequencies()` method exists to allow runtime corpus-based frequency updates but has **no observed call site** (confirmed by grep). The city-based TF adjustment is also configured but city is not a comparison field in the current engine.

### Key Terminology

| Term | Meaning |
|------|---------|
| `BusinessData` | Query object (from `models/business/seeder.py`) representing the entity being searched for |
| `Candidate` | Row from the cached Business DataFrame, converted to a typed dataclass |
| `MatchResult` | Internal decision record: `is_match`, `score`, `raw_score`, `threshold`, `comparisons` list |
| `MatchCandidate` | API-safe projection of `MatchResult` (PII stripped) |
| `CompositeBlockingRule` | OR-combination of 3 blocking rules for candidate pruning |
| `MatchingConfig` | Pydantic settings sourced from `SEEDER_*` env vars |
| `log_odds_to_probability()` | Sigmoid converting total log-odds to 0.0-1.0 (clamps at ±20 to avoid overflow) |
| TENSION-002 | Documented architecture violation: `matching_service.py` imports `api/routes/matching_models.py` |

### Inter-Feature Relationships

| Direction | Feature/Layer | Nature |
|-----------|---------------|--------|
| **Consumed by** | `models/business/seeder.py` | `BusinessSeeder._find_by_composite_match()` uses `MatchingEngine` + `CompositeBlockingRule` directly (Tier 2 seeder path) |
| **Consumed by** | `api/routes/matching.py` | S2S API surface for external consumers |
| **Provides to** | Service layer | `MatchingService.query()` returns `MatchingQueryResponse` |
| **Depends on** | `cache/dataframe/` | Route fetches Business DataFrame from `get_dataframe_cache_provider()` |
| **Depends on** | `services/resolver.py` | Route resolves business project GID from `EntityProjectRegistry` |
| **Depends on** | `autom8y_api_schemas` | `LeadPhoneField`, `OfficePhone` types for phone contract |

---

## Implementation Map

| File | Role | Key Exports |
|------|------|-------------|
| `src/autom8_asana/models/business/matching/__init__.py` | Public API re-export surface | All 20 symbols in `__all__` |
| `src/autom8_asana/models/business/matching/engine.py` | Fellegi-Sunter scoring core | `MatchingEngine`, `log_odds_to_probability()` |
| `src/autom8_asana/models/business/matching/blocking.py` | Candidate pruning | `CompositeBlockingRule`, `DomainBlockingRule`, `PhonePrefixBlockingRule`, `NameTokenBlockingRule` |
| `src/autom8_asana/models/business/matching/comparators.py` | Field comparison strategies | `ExactComparator`, `FuzzyComparator`, `TermFrequencyAdjuster` |
| `src/autom8_asana/models/business/matching/normalizers.py` | Field value canonicalization | `PhoneNormalizer`, `EmailNormalizer`, `BusinessNameNormalizer`, `DomainNormalizer`, `AddressNormalizer` |
| `src/autom8_asana/models/business/matching/models.py` | Internal typed results | `FieldComparison`, `MatchResult`, `Candidate` |
| `src/autom8_asana/models/business/matching/config.py` | 12-factor configuration | `MatchingConfig` (Pydantic, `SEEDER_*` prefix) |
| `src/autom8_asana/services/matching_service.py` | Orchestration service | `MatchingService.query()` |
| `src/autom8_asana/api/routes/matching.py` | Hidden S2S route | `POST /v1/matching/query` |
| `src/autom8_asana/api/routes/matching_models.py` | API-safe request/response models | `MatchingQueryRequest`, `MatchingQueryResponse`, `MatchCandidate`, `MatchFieldComparison` |

### Data Flow: POST /v1/matching/query

```
HTTP POST /v1/matching/query (S2S JWT)
  → matching_query() route handler
  → validate ≥1 identity field present (else 400 INVALID_QUERY)
  → get_dataframe_cache_provider() (else 503 CACHE_UNAVAILABLE)
  → EntityProjectRegistry.get_project_gid("business") (else 503 PROJECT_NOT_CONFIGURED)
  → cache.get_async(project_gid, "business") (else 503 CACHE_UNAVAILABLE)
  → MatchingService().query(
        name, phone, email, domain,
        dataframe=entry.dataframe,
        limit=body.limit,
        threshold=body.threshold
    )
      → _dataframe_to_candidates(df) → list[Candidate]
      → CompositeBlockingRule.filter_candidates(query_data, candidates)
      → for candidate in pruned: engine.compute_match(query, candidate)
      → sort by score desc → apply limit
      → _project_result() × N → list[MatchCandidate]
  → MatchingQueryResponse(candidates, total_candidates_evaluated, query_threshold)
  → build_success_response(data=response, request_id=request_id)
```

### Data Flow: BusinessSeeder Tier 2 (seeder.py)

```
BusinessSeeder._find_by_composite_match(data: BusinessData)
  → _get_match_candidates(data) → list[Candidate]
  → CompositeBlockingRule().filter_candidates(data, candidates)
  → MatchingEngine.find_best_match(data, pruned)
      → compute_match() for each candidate
      → return best MatchResult above threshold
  → Return matched Business entity or None
```

### Test Locations

| Test File | Coverage |
|-----------|---------|
| `tests/unit/models/business/matching/test_engine.py` | Engine scoring, log-odds accumulation, threshold logic |
| `tests/unit/models/business/matching/test_blocking.py` | All 3 blocking rules + composite |
| `tests/unit/models/business/matching/test_comparators.py` | ExactComparator, FuzzyComparator graduated levels, TermFrequencyAdjuster |
| `tests/unit/models/business/matching/test_normalizers.py` | All normalizers incl. SCAR regression at lines 64-70 (`@pytest.mark.scar`) |
| `tests/unit/services/test_matching_service.py` | MatchingService.query(), _dataframe_to_candidates(), _project_result() |
| `tests/unit/api/routes/test_matching.py` | Route handler, auth enforcement, error paths |
| `tests/unit/api/routes/test_matching_models.py` | Pydantic model validation, field constraints |

---

## Boundaries and Failure Modes

### Explicit Scope Boundaries

- **Does NOT make Asana API calls at query time.** The ADR constraint in `matching_service.py` docstring is explicit. The cached Business DataFrame is the only data source during a match query.
- **Does NOT compare address fields in the engine.** `AddressNormalizer` is defined and exported but `engine.py` contains no `_compare_address()` method and no `address_weight` is applied in `compute_match()`. The `address_weight` and `address_nonmatch` fields in `MatchingConfig` are dead configuration.
- **Does NOT expose internal scoring internals to API callers.** `_project_result()` strips `raw_score`, `left_value`, `right_value`, and per-field `weight_applied`. This is security constraint HD-01.
- **Does NOT return all matches above threshold.** Results are capped at `limit` (default 10, max 100). Total evaluated count is reported separately as `total_candidates_evaluated`.
- **Does NOT pre-normalize candidates at indexing time.** Normalization happens at comparison time for each field. `normalize_candidate()` in the engine populates `normalized_*` fields but is not called during `compute_match()` itself; it is an optional pre-normalization utility.

### Failure Modes and Error Paths

**Cache unavailable (503 CACHE_UNAVAILABLE)**: If `get_dataframe_cache_provider()` returns None or raises, or if `cache.get_async()` returns None, the route raises 503. This is the expected early-startup failure mode before cache warm completes. The `/ready` endpoint returns 503 until warm; `/health` returns 200 immediately.

**Project not configured (503 PROJECT_NOT_CONFIGURED)**: If `EntityProjectRegistry` cannot resolve "business" project GID, the route raises 503. Indicates incomplete service initialization.

**No identity fields (400 INVALID_QUERY)**: Route validates `any([name, phone, email, domain])` before calling the service. Empty requests are rejected immediately.

**Matching error (500 MATCHING_ERROR)**: Broad-catch on the `MatchingService().query()` call. Any unhandled exception inside the engine/service produces a 500 with opaque error message — no internal details leak to the caller.

**Scar intersections**:
- **SCAR-020**: `PhoneNormalizer` is wired into the matching engine but NOT into the reconciliation read path — a documented reconciliation blindness for phone fields.
- **SCAR-CANDIDATE-B** (uncatalogued, commit `0f18f4e8`): `PhoneNormalizer.normalize()` previously lacked `NumberParseException` in its except tuple (`normalizers.py:77-82`). The fix catches `phonenumbers.phonenumberutil.NumberParseException` explicitly. Regression test at `tests/unit/models/business/matching/test_normalizers.py:64-70` (`@pytest.mark.scar`).
- **SCAR-024**: Phone field contract gap related to SCAR-020 (historical).

**DataFrame column contract**: `_dataframe_to_candidates()` defensively checks `if "column_name" in columns` before reading. Missing columns silently become `None` on the resulting `Candidate` object. No schema validation or hard error is raised on column mismatch.

**Null-heavy data behavior**: When `fields_compared < min_fields` (default 2), the engine returns `MatchResult(is_match=False)` immediately. Null fields contribute 0.0 log-odds, not negative. If all fields are null, `fields_compared = 0` and no match can ever be declared. Blocking pass behavior under null-heavy data (false-pass rate) is not characterized.

**Per-request engine instantiation**: `MatchingService()` is constructed at `matching.py:171` on every request. This instantiates `MatchingEngine`, which calls `MatchingConfig.from_env()` (full pydantic env parse) and constructs 4 normalizers, 2 comparators, and 1 `TermFrequencyAdjuster` per request. No benchmark of this overhead exists.

### Interaction Points and Boundary Blur

**TENSION-002** (documented, architecture.md line 175): `services/matching_service.py` imports `api/routes/matching_models.py` — a layer boundary violation where the service layer imports from the API layer. This is the same pattern as `intake_resolve_service.py` etc. The tension is accepted and documented.

**Two consumers of MatchingEngine**: The engine is used both by `MatchingService` (API path) and directly by `BusinessSeeder._find_by_composite_match()` (seeder path). This means matching behavior and configuration changes affect two code paths. The seeder path does NOT go through `MatchingService` and therefore does not apply the PII stripping or response model projection.

**`TermFrequencyAdjuster.update_frequencies()` is dead code** (confirmed by grep): No call site exists outside the class definition. The method is tested in `test_comparators.py` but is not wired into any runtime path. If corpus-based frequency updates were intended, the call site was never built.

**`AddressNormalizer` is exported but dead**: `__init__.py` exports `AddressNormalizer` in `__all__`, but `engine.py` has no address comparison. The `address_weight` / `address_nonmatch` fields in `MatchingConfig` configure a capability that the engine does not exercise.

### Configuration Boundaries

All config via `SEEDER_*` environment variables (Pydantic `env_prefix`):

| Variable | Default | Constraint |
|----------|---------|------------|
| `SEEDER_MATCH_THRESHOLD` | 0.80 | ge=0.0, le=1.0 |
| `SEEDER_MIN_FIELDS` | 2 | ge=1 |
| `SEEDER_EMAIL_WEIGHT` | 8.0 | — |
| `SEEDER_PHONE_WEIGHT` | 7.0 | — |
| `SEEDER_NAME_WEIGHT` | 6.0 | — |
| `SEEDER_DOMAIN_WEIGHT` | 5.0 | — |
| `SEEDER_ADDRESS_WEIGHT` | 4.0 | dead — address comparison not wired |
| `SEEDER_EMAIL_NONMATCH` | -4.0 | — |
| `SEEDER_PHONE_NONMATCH` | -4.0 | — |
| `SEEDER_NAME_NONMATCH` | -3.0 | — |
| `SEEDER_DOMAIN_NONMATCH` | -2.0 | — |
| `SEEDER_FUZZY_EXACT_THRESHOLD` | 0.95 | ge=0.0, le=1.0 |
| `SEEDER_FUZZY_HIGH_THRESHOLD` | 0.90 | ge=0.0, le=1.0 |
| `SEEDER_FUZZY_MEDIUM_THRESHOLD` | 0.80 | ge=0.0, le=1.0 |
| `SEEDER_TF_ENABLED` | true | — |
| `SEEDER_TF_COMMON_THRESHOLD` | 0.01 | ge=0.0, le=1.0 |

---

```metadata
source_files_read: 10
key_artifacts:
  - src/autom8_asana/models/business/matching/engine.py
  - src/autom8_asana/models/business/matching/blocking.py
  - src/autom8_asana/models/business/matching/comparators.py
  - src/autom8_asana/models/business/matching/normalizers.py
  - src/autom8_asana/models/business/matching/models.py
  - src/autom8_asana/models/business/matching/config.py
  - src/autom8_asana/models/business/matching/__init__.py
  - src/autom8_asana/services/matching_service.py
  - src/autom8_asana/api/routes/matching.py
  - src/autom8_asana/api/routes/matching_models.py
scar_references:
  - SCAR-020 (PhoneNormalizer reconciliation blindness)
  - SCAR-CANDIDATE-B (NumberParseException fix, commit 0f18f4e8, uncatalogued)
  - SCAR-024 (phone field contract gap)
tension_references:
  - TENSION-002 (services→api co-located model import)
dead_code_confirmed:
  - AddressNormalizer (exported, not wired in engine)
  - TermFrequencyAdjuster.update_frequencies() (no call site in src/)
  - address_weight / address_nonmatch (MatchingConfig fields, engine does not exercise)
two_consumers:
  - MatchingService (API path via matching.py route)
  - BusinessSeeder._find_by_composite_match() (seeder path, direct engine use)
```
