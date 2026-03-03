# Cross-Service Enrichment Spike

**Date**: 2026-02-24
**Type**: Architectural Spike (design only, no implementation)
**Scope**: Extending QueryEngine joins to include autom8y-data tables

---

## 1. Data Surface Map

### Endpoints and DataFrame Compatibility

| Data Source | Endpoint | HTTP | Join Key | Grain | Batch? | Polars Ready? |
|---|---|---|---|---|---|---|
| **Insights (spend, leads, appts, CPS, ROAS...)** | `POST /api/v1/data-service/insights` | POST | `office_phone` + `vertical` | Per (phone, vertical) pair | Yes (1-1000 PVPs) | Yes — `InsightsResponse.to_dataframe()` |
| **Appointments (detail rows)** | `GET /api/v1/data-service/appointments` | GET | `office_phone` | Per appointment row | No (single phone) | Partial — dict list needs `pl.from_dicts()` |
| **Leads (detail rows)** | `GET /api/v1/data-service/leads` | GET | `office_phone` | Per lead row | No (single phone) | Partial — dict list needs `pl.from_dicts()` |
| **Messages/Export** | `GET /api/v1/messages/export` | GET | `office_phone` | Per message row | No (single phone) | No — CSV bytes, needs parse |

### Grain Compatibility with Asana Entities

| Asana Entity | Grain | office_phone? | vertical? | Best Data Source Match |
|---|---|---|---|---|
| **offer** | One row per Asana task | Yes | Yes | Insights (1:1 — same composite key) |
| **unit** | One row per account | Yes | Yes | Insights (1:1 — same composite key) |
| **business** | One row per business entity | Yes | No (multi-vertical) | Insights (1:N — one phone, many verticals) |
| **contact** | One row per contact | Yes | Via parent offer | Insights (N:1 — many contacts per phone) |

### Key Insight: Grain Match Is Near-Perfect for Offers

An Asana **offer** DataFrame row has `office_phone` and `vertical`. A data-service **insights** response is keyed by `(office_phone, vertical)`. This is a natural 1:1 join. No aggregation or fan-out needed.

For **units**, the match is also 1:1 (units have phone+vertical). For **businesses**, it's 1:N (one phone maps to multiple verticals in data-service), requiring aggregation or filtering.

### FACTORY_TO_FRAME_TYPE Mapping (14 factories)

DataServiceClient already knows how to fetch these via `frame_type`:

| Factory | frame_type | Example Metrics |
|---|---|---|
| account | business | Account-level aggregates |
| ads | offer | Ad-level: spend, impressions, clicks |
| adsets | offer | Adset-level: spend, reach, frequency |
| campaigns | offer | Campaign-level: spend, leads, CPS |
| spend | offer | Spend breakdown by date |
| leads | offer | Lead counts, CPS, conversion rate |
| appts | offer | Appointment counts, booking rate |
| assets | asset | Creative performance |
| targeting | offer | Audience targeting metrics |
| payments | business | Payment/billing data |
| business_offers | offer | Business-offer metrics |
| ad_questions | question | Ad question responses |
| ad_tests | offer | A/B test results |
| base | unit | Base/raw unit metrics |

Each factory returns a different column set, but all are keyed by `(office_phone, vertical)` and all return `InsightsResponse` with `.to_dataframe()`.

---

## 2. Architecture Recommendation

### Options Evaluated

**Option A: DataServiceDataFrameProvider** — New DataFrameProvider implementation that fetches from data-service, converts to Polars DataFrames, plugs into existing join machinery.

**Option B: Cross-service JoinSpec extension** — Extend JoinSpec to support `source: "data-service"` with endpoint/period parameters.

**Option C: Saved query enrichment** — Post-processing step in saved queries that fetches and merges data-service metrics.

### Recommendation: Option B (Extended JoinSpec)

**Rationale:**

Option A (new DataFrameProvider) doesn't fit because DataFrameProvider is designed for entity-type-to-DataFrame mapping with cache lifecycle semantics. Data-service "entities" aren't entities in the same sense — they're metric aggregations parameterized by factory, period, and phone/vertical. A provider would need to know the factory, period, and the set of phone/vertical pairs to fetch *before* the join happens. That inverts the natural flow (you need the primary DataFrame's phone values to know *what* to fetch).

Option C (saved query post-processing) is too narrow — it only helps CLI saved queries, not the API surface.

Option B extends JoinSpec naturally:
1. JoinSpec already has `entity_type` (target) and `on` (explicit key). Add `source` and source-specific params.
2. The QueryEngine already loads the target DataFrame at step 7.5. The extension point is *how* that DataFrame is obtained — from the existing provider (Asana entity) or from a new fetcher (data-service HTTP call).
3. The join execution itself (`execute_join()`) is unchanged. It takes two DataFrames and a join key. It doesn't care where the DataFrames came from.

The key insight: **the join machinery is already source-agnostic**. Only the DataFrame *loading* step needs to dispatch differently based on source.

### Why Not a Full DataFrameProvider?

The DataFrameProvider protocol requires:
```python
async def get_dataframe(entity_type: str, project_gid: str, client: AsanaClient) -> pl.DataFrame
```

Data-service tables don't have a `project_gid` or `AsanaClient`. They need `(factory, period, phone_vertical_pairs)`. Forcing data-service into this interface would require:
- Ignoring `project_gid` and `client` (protocol violation)
- Threading factory/period through an out-of-band channel (fragile)
- Pre-fetching all possible phone/vertical pairs (wasteful)

Instead, a targeted `DataServiceJoinFetcher` that takes explicit parameters and returns a `pl.DataFrame` is cleaner. It's called *only* during join resolution (step 7.5), not as a general-purpose provider.

---

## 3. Gap Analysis

### What Exists (reusable as-is)

| Component | Location | Status |
|---|---|---|
| `execute_join()` | `query/join.py` | No changes needed. Takes two DataFrames + join key. |
| `JoinResult` dataclass | `query/join.py` | No changes needed. |
| `DataServiceClient` | `clients/data/client.py` | Already fetches insights, appointments, leads. |
| `InsightsResponse.to_dataframe()` | `clients/data/` | Already converts to Polars. |
| Column prefixing (`{entity}_{col}`) | `execute_join()` | Works for data-service columns too. |
| Join metadata in `RowsMeta` | `query/models.py` | `join_entity`, `join_key`, `join_matched`, `join_unmatched` — works. |
| PII masking | `clients/data/_pii.py` | Already masks phone in logs. |
| Circuit breaker + retry | `clients/data/` | Production-grade resilience exists. |

### What Needs Extension (Small, <50 LOC each)

| Gap | Complexity | Description |
|---|---|---|
| **JoinSpec.source field** | S | Add `source: Literal["entity", "data-service"] = "entity"` to JoinSpec. Default preserves backward compat. |
| **JoinSpec.factory field** | S | Add `factory: str | None = None`. Required when source="data-service". |
| **JoinSpec.period field** | S | Add `period: str = "LIFETIME"`. Default for data-service joins. |
| **Engine step 7.5 dispatch** | M | ~30 LOC if/else: if source=="entity" use existing path; if "data-service" call fetcher. |
| **DataServiceJoinFetcher** | M | ~100-150 LOC. Takes (factory, period, phone_vertical_pairs), calls DataServiceClient, returns pl.DataFrame. |
| **Cross-service relationship registry** | S | ~20 LOC. Register known data-service "entities" (spend, leads, appts) with join keys. |
| **Introspection extension** | S | `list_relations()` should include data-service targets with `source: "data-service"` annotation. |
| **CLI --source flag** | S | `--join-source data-service` (or infer from entity_type). |

### What Needs New (Medium, 100-200 LOC)

| Gap | Complexity | Description |
|---|---|---|
| **DataServiceJoinFetcher** | M | Core new component. Extracts phone/vertical pairs from primary DataFrame, batch-fetches from DataServiceClient, converts to pl.DataFrame. |
| **Virtual entity type registry** | M | Maps logical names ("spend", "leads_detail", "appointments") to (factory, frame_type, endpoint_type, available_columns). |

### What's NOT Needed

- No changes to `execute_join()` (already source-agnostic)
- No changes to DataFrameProvider protocol
- No S3 caching of data-service results (data-service is source of truth)
- No model/ORM coupling between services
- No new authentication flow (DataServiceClient already handles JWT)

---

## 4. Proposed Interface

### Extended JoinSpec

```python
class JoinSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str                                          # Target (existing or virtual)
    select: list[str] = Field(min_length=1, max_length=10)
    on: str | None = None                                     # Explicit join key

    # Cross-service extension
    source: Literal["entity", "data-service"] = "entity"
    factory: str | None = None                                # data-service factory name
    period: str = "LIFETIME"                                  # T7, T30, LIFETIME, etc.

    @model_validator(mode="after")
    def validate_source_params(self) -> JoinSpec:
        if self.source == "data-service" and self.factory is None:
            raise ValueError("factory is required when source='data-service'")
        if self.source == "entity" and self.factory is not None:
            raise ValueError("factory is only valid when source='data-service'")
        return self
```

### DataServiceJoinFetcher

```python
class DataServiceJoinFetcher:
    """Fetches data-service metrics as a pl.DataFrame for join enrichment.

    Given a primary DataFrame with office_phone (and optionally vertical),
    batch-fetches metrics from DataServiceClient and returns a DataFrame
    suitable for left-join via execute_join().
    """

    def __init__(self, data_client: DataServiceClient) -> None:
        self._client = data_client

    async def fetch_for_join(
        self,
        primary_df: pl.DataFrame,
        factory: str,
        period: str,
        join_key: str = "office_phone",
    ) -> pl.DataFrame:
        """Extract phone/vertical pairs from primary, batch-fetch, return DataFrame.

        Args:
            primary_df: Filtered primary entity DataFrame (has office_phone column).
            factory: DataService factory name (e.g., "spend", "leads", "campaigns").
            period: Period filter (e.g., "T30", "LIFETIME").
            join_key: Column to extract phone/vertical pairs from.

        Returns:
            pl.DataFrame with office_phone, vertical, and metric columns.
        """
        # 1. Extract unique phone/vertical pairs from primary
        pairs = self._extract_pvps(primary_df, join_key)
        if not pairs:
            return pl.DataFrame()  # No data to fetch

        # 2. Batch fetch (DataServiceClient handles chunking at 1000)
        batch_response = await self._client.get_insights_batch_async(
            pvp_list=pairs,
            factory=factory,
            period=period,
        )

        # 3. Collect successful responses into a single DataFrame
        frames = []
        for result in batch_response.results.values():
            if result.success and result.response is not None:
                frames.append(result.response.to_dataframe())

        if not frames:
            return pl.DataFrame()

        return pl.concat(frames)

    def _extract_pvps(
        self, df: pl.DataFrame, join_key: str
    ) -> list[PhoneVerticalPair]:
        """Extract unique (phone, vertical) pairs from DataFrame."""
        if join_key not in df.columns:
            return []

        has_vertical = "vertical" in df.columns
        seen: set[tuple[str, str]] = set()
        pairs: list[PhoneVerticalPair] = []

        for row in df.select(
            [join_key] + (["vertical"] if has_vertical else [])
        ).to_dicts():
            phone = row.get(join_key)
            vertical = row.get("vertical", "unknown") if has_vertical else "unknown"
            if phone and (phone, vertical) not in seen:
                seen.add((phone, vertical))
                pairs.append(PhoneVerticalPair(phone=phone, vertical=vertical))

        return pairs
```

### Engine Step 7.5 Extension

```python
# In QueryEngine.execute_rows(), step 7.5:

if request.join is not None:
    if request.join.source == "entity":
        # Existing path (unchanged)
        rel = find_relationship(entity_type, request.join.entity_type)
        # ... existing code ...

    elif request.join.source == "data-service":
        # Cross-service path
        join_key = request.join.on or "office_phone"
        fetcher = DataServiceJoinFetcher(data_client)
        target_df = await fetcher.fetch_for_join(
            primary_df=df,
            factory=request.join.factory,
            period=request.join.period,
            join_key=join_key,
        )
        join_result = execute_join(
            primary_df=df,
            target_df=target_df,
            join_key=join_key,
            select_columns=request.join.select,
            target_entity_type=request.join.factory,  # prefix: spend_X, leads_X
        )
        df = join_result.df
        join_meta = {
            "join_entity": f"data-service:{request.join.factory}",
            "join_key": join_result.join_key,
            "join_matched": join_result.matched_count,
            "join_unmatched": join_result.unmatched_count,
        }
```

### Virtual Entity Registry (for introspection)

```python
# In query/data_service_entities.py (new, ~60 LOC)

DATA_SERVICE_ENTITIES: dict[str, DataServiceEntityInfo] = {
    "spend": DataServiceEntityInfo(
        factory="spend",
        frame_type="offer",
        description="Ad spend metrics by period",
        columns=["spend", "imp", "clicks", "ctr", "cps", "cpl"],
        default_period="T30",
        join_key="office_phone",
    ),
    "leads_metrics": DataServiceEntityInfo(
        factory="leads",
        frame_type="offer",
        description="Lead generation metrics by period",
        columns=["leads", "scheds", "cps", "conversion_rate", "booking_rate"],
        default_period="T30",
        join_key="office_phone",
    ),
    "campaigns": DataServiceEntityInfo(
        factory="campaigns",
        frame_type="offer",
        description="Campaign-level performance",
        columns=["spend", "leads", "scheds", "cps", "roas"],
        default_period="T30",
        join_key="office_phone",
    ),
    # ... other factories
}
```

---

## 5. Example Queries

### Saved Query: Active Offers with Trailing 30-Day Spend

```yaml
# queries/offers_with_spend.yaml
name: offers_with_spend
description: Active offers enriched with trailing 30-day ad spend metrics
command: rows
entity_type: offer
classification: active
select: [gid, name, mrr, office_phone, vertical]
join:
  source: data-service
  entity_type: spend          # virtual entity name
  factory: spend              # DataServiceClient factory
  period: T30
  select: [spend, cps, leads]
  on: office_phone
order_by: spend_spend
order_dir: desc
limit: 50
format: table
```

Output (table):
```
gid               name                    mrr      office_phone    vertical      spend_spend  spend_cps  spend_leads
1211403363567747  Brain-Body Insight...  2500.00  +17175558734    chiropractic  3200.00      267.00     12
1211403363567748  Dental Excellence...   1800.00  +14155551234    dental        2800.00      311.00     9
...
```

### CLI Invocation

```bash
# Inline (no saved query)
autom8-query rows offer \
  --classification active \
  --select gid,name,mrr,office_phone \
  --join spend:spend,cps,leads \
  --join-source data-service \
  --join-factory spend \
  --join-period T30 \
  --order-by spend_spend \
  --order-dir desc

# Or with shorthand (if we add factory-as-entity-type inference):
autom8-query rows offer \
  --classification active \
  --enrich spend:spend,cps,leads --period T30
```

### API Invocation

```json
POST /v1/query/offer/rows
{
  "classification": "active",
  "select": ["gid", "name", "mrr", "office_phone"],
  "join": {
    "source": "data-service",
    "entity_type": "spend",
    "factory": "spend",
    "period": "T30",
    "select": ["spend", "cps", "leads"],
    "on": "office_phone"
  },
  "limit": 50
}
```

### Offers with Appointment Counts

```yaml
# queries/offers_with_appts.yaml
name: offers_with_appts
description: Offers with appointment booking metrics (lifetime)
command: rows
entity_type: offer
classification: active
select: [gid, name, office_phone, vertical]
join:
  source: data-service
  entity_type: appts
  factory: appts
  period: LIFETIME
  select: [scheds, ns, nc, booking_rate]
  on: office_phone
limit: 100
format: table
```

### Units with Base Metrics

```yaml
# queries/units_with_metrics.yaml
name: units_with_metrics
description: Units enriched with base metrics
command: rows
entity_type: unit
select: [gid, name, office_phone, vertical]
join:
  source: data-service
  entity_type: base
  factory: base
  period: T30
  select: [spend, leads, scheds, ltv]
  on: office_phone
limit: 100
format: table
```

---

## 6. Risk Register

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | **Latency**: HTTP round-trip to data-service adds 100-500ms per join | Medium | Batch PVP requests (up to 1000/req). Data-service has L1+L2 cache. Accept latency for enrichment queries — users explicitly opt in via `source: data-service`. |
| R2 | **Data-service unavailability**: Circuit breaker trips, join fails | Medium | Return partial results with warning (join_matched=0, join_unmatched=N). Don't fail the entire query — the primary entity data is still valid. |
| R3 | **PII in join key**: `office_phone` traverses both services | Low | Already mitigated. DataServiceClient masks phone in all logs (`_pii.py`). Join key is in-memory only, never persisted to new locations. No new PII exposure surface. |
| R4 | **Column name collision**: Data-service columns may collide with Asana columns | Low | Already handled. `execute_join()` prefixes all target columns with `{entity_type}_`. Using factory name as prefix (e.g., `spend_spend`, `spend_cps`) avoids collision. |
| R5 | **Offline mode incompatible**: `--live` required for data-service joins | Medium | Clearly document that `source: data-service` requires network access (implicitly `--live` for data-service portion). CLI offline mode (S3 parquet) only works for Asana entities. Validate early: if source=data-service and no DataServiceClient configured, raise clear error. |
| R6 | **Fan-out for businesses**: Business has phone but no vertical, data-service requires both | Low | For business joins: use `vertical="*"` or aggregate across verticals. Or require explicit vertical filter in WHERE clause. Document this grain mismatch. |
| R7 | **Auth in CLI**: DataServiceClient requires JWT. CLI currently uses S3 (no auth) or `--live` (API auth) | Medium | Cross-service joins require `--live` mode or a DataServiceClient configured with ASANA_SERVICE_KEY. Add validation: if join.source="data-service" and not in --live mode and no DataServiceClient, fail with clear message. |
| R8 | **Schema discovery**: Data-service column names not known at JoinSpec validation time | Low | Virtual entity registry provides known column lists per factory. Validate `select` against registry. For unknown factories, skip validation (warn). |
| R9 | **Rate limiting**: Batch-fetching many PVPs could hit data-service rate limits | Low | DataServiceClient already supports batch (1000 PVPs/request). Asana offers are typically ~4000 max, so 4 batch requests worst case. Data-service handles this load routinely. |
| R10 | **Stale data mismatch**: Asana DataFrame from SWR cache (minutes old) joined with live data-service metrics | Low | Acceptable. Both sources have independent freshness. Document that join combines data from two cache domains. Freshness metadata already reported per-source. |

---

## 7. Implementation Phases

### Phase 1: Insights Join (MVP) — ~0.5 day

**Value**: Highest. Covers the primary use case: "show me Asana entities with their analytics metrics."

**Scope**:
1. Extend `JoinSpec` with `source`, `factory`, `period` fields (backward-compatible defaults)
2. Create `DataServiceJoinFetcher` (~120 LOC) using existing `DataServiceClient.get_insights_batch_async()`
3. Add dispatch in `QueryEngine.execute_rows()` step 7.5 (~30 LOC)
4. Register virtual entity info for top 5 factories (spend, leads, appts, campaigns, base)
5. Add `queries/offers_with_spend.yaml` example
6. Unit tests for fetcher + extended JoinSpec validation (~15 tests)

**Delivers**:
- `autom8-query rows offer --classification active --join spend:spend,cps --join-source data-service --join-period T30`
- API: `POST /v1/query/offer/rows` with extended JoinSpec

**Dependencies**: DataServiceClient with valid auth (production JWT or `--live` mode).

### Phase 2: CLI Ergonomics — ~0.5 day

**Value**: Medium. Makes cross-service joins first-class in CLI.

**Scope**:
1. `--enrich FACTORY:col1,col2 --period T30` shorthand (desugars to JoinSpec with source=data-service)
2. `autom8-query data-sources` introspection command (lists available factories with columns)
3. `autom8-query fields --source data-service spend` (columns for a factory)
4. Extend `list_relations()` to include data-service targets
5. Saved query YAML support for `source: data-service` in join block

### Phase 3: Detail Row Joins (Appointments, Leads) — ~1 day

**Value**: Medium. Different join pattern — detail rows, not aggregated metrics.

**Scope**:
1. Extend `DataServiceJoinFetcher` with `fetch_detail_rows()` for appointments/leads endpoints
2. Handle per-phone fetching (no batch API — need async gather with concurrency limit)
3. Aggregate detail rows to match Asana entity grain (e.g., "appointment count by phone" for offer join)
4. Or expose raw detail rows with N:1 fan-out warning
5. Add `queries/offers_with_appt_count.yaml`

**Complexity**: Higher than Phase 1 because:
- Appointments/leads endpoints are per-phone (no batch), requiring fan-out
- Grain is row-level (many appointments per phone), requiring aggregation before join
- Column set is different from insights response

### Phase 4: API Introspection — ~0.5 day

**Value**: Low-medium. Completes the discovery surface.

**Scope**:
1. `GET /v1/query/data-sources` — list available data-service factories
2. `GET /v1/query/data-sources/{factory}/fields` — columns for a factory
3. Extend `GET /v1/query/{entity_type}/relations` response to include data-service targets
4. OpenAPI schema updates

---

## Appendix A: What the Simplest Cross-Service Join Looks Like

The single simplest join is **offer + spend (T30)**:

1. **offer** DataFrame has `office_phone` and `vertical` columns (always present).
2. DataServiceClient's `get_insights_batch_async(pvp_list, factory="spend", period="T30")` returns `BatchInsightsResponse`.
3. Each successful result has `.response.to_dataframe()` → Polars DataFrame with `office_phone`, `vertical`, `spend`, `imp`, `clicks`, etc.
4. Concatenate batch results → single target DataFrame.
5. `execute_join(offer_df, spend_df, "office_phone", ["spend", "cps"], "spend")` → enriched DataFrame.

The glue code is ~120 lines: extract PVPs from primary → batch fetch → concat → return DataFrame. Everything else already exists.

## Appendix B: Why entity_type and factory Are Both Needed

In Phase 1, `entity_type` and `factory` could be the same string (e.g., "spend"). But they serve different purposes:

- `entity_type` is the **logical name** used for column prefixing and introspection (e.g., `spend_spend`, `spend_cps`).
- `factory` is the **DataServiceClient parameter** that determines which data-service factory to invoke.

They diverge when we want friendlier names: `entity_type: "ad_performance"` with `factory: "ads"`. For MVP, keeping them identical is fine. The separation future-proofs without adding complexity.

## Appendix C: Composite Join Key Consideration

The natural join key between Asana entities and data-service is `(office_phone, vertical)` — a composite key. The current `execute_join()` supports only a single join column.

**For offer and unit joins**, `office_phone` alone is sufficient because each offer/unit row has a unique (phone, vertical) combination in practice. The deduplication in `execute_join()` (take first) handles any edge cases.

**For business joins**, the composite key matters because one phone maps to multiple verticals. Options:
1. Join on `office_phone` only, accepting that deduplicated metrics may pick an arbitrary vertical's data.
2. Extend `execute_join()` to support composite keys (`on: ["office_phone", "vertical"]`).
3. Require a WHERE filter on vertical before the join.

**Recommendation**: Start with single-key (`office_phone`) for Phase 1. The offer/unit use case works correctly. Add composite key support if business joins prove important.

---

## 8. Post-Spike Status: Architecture Deep-Dive & Phase 0 Complete

**Updated**: 2026-02-24
**Analysis performed in**: autom8y-data repo (arch rite, 4-phase deep-dive)
**Implementation performed in**: both repos (10x-dev rite, Phase 0 prerequisites)

### What Happened After This Spike

This spike was picked up by a full architecture analysis in the autom8y-data repo. A 4-phase deep-dive (topology mapping, dependency tracing, structural evaluation, remediation planning) produced a 754-line architecture report that validated the spike's core recommendation while surfacing three issues the spike did not identify.

**Full artifacts** (in autom8y-data):
- `autom8y-data/.claude/wip/CROSS-SERVICE-ENRICHMENT/architecture-report.md` -- Final report with executive summary, risk re-ratings, phased roadmap
- `autom8y-data/.claude/wip/CROSS-SERVICE-ENRICHMENT/topology-inventory.md` -- Integration boundary map
- `autom8y-data/.claude/wip/CROSS-SERVICE-ENRICHMENT/dependency-map.md` -- Cross-service data flow analysis
- `autom8y-data/.claude/wip/CROSS-SERVICE-ENRICHMENT/architecture-assessment.md` -- Anti-patterns, SPOFs, risk register
- `autom8y-data/.claude/wip/CROSS-SERVICE-ENRICHMENT/TDD-phase0-prerequisites.md` -- Lightweight TDD for Phase 0

### Verdict on the Spike

**Option B (Extended JoinSpec) is confirmed as the correct architectural choice.** The analysis agrees with the spike's reasoning: Option A inverts the data flow, Option C is too narrow, and the join dispatch at step 7.5 is the natural extension point.

**However, the spike's Phase 1 estimate of 0.5 days was too optimistic.** Three structural blockers had to be resolved first, raising the total to 1.0-1.25 days for Phase 0 + Phase 1.

### What the Spike Missed (3 Findings)

#### Finding 1: meta/metadata Wire Mismatch (Production Bug)

The server's `InsightsResponse` serializes its metadata field as `"meta"` in the wire JSON. The client reads `body.get("metadata", {})`. Every `InsightsResponse` object built by the client has empty metadata -- no column types, no cache signals, no factory identification. This is a confirmed production bug that has gone undetected because the data path works via Polars type inference even without server-specified dtypes.

**Enrichment impact**: DataFrames built for joins would have Polars-inferred types instead of server-specified types. A `spend` column might be `Utf8` instead of `Float64`, causing silent arithmetic errors.

#### Finding 2: max_batch_size=50 (Not 1000)

The spike states "batch PVP requests (up to 1000/req)" and estimates 4 HTTP requests for 4000 offers. The actual `max_batch_size` default is 50, producing 80 HTTP requests (~8 seconds) and 80 circuit-breaker failure opportunities. The spike's `DataServiceJoinFetcher.fetch_for_join()` would raise `InsightsValidationError` for any query with >50 unique PVPs -- a hard blocker.

#### Finding 3: CLI --live Targets Non-Existent Endpoint

The `--live` flag sends to `/v1/query/{entity_type}/rows` which doesn't exist in autom8y-data (all routes are `/api/v1/...`). This is a pre-existing broken feature, not an enrichment concern, but it shares the step 7.5 code path.

### Risk Re-Ratings

The architecture analysis re-rated several spike risks and added 5 new ones:

| Risk | Spike Rating | Revised | Why |
|------|-------------|---------|-----|
| R1 (Latency) | Medium (100-500ms) | **High (up to 8s)** | 80 requests at 50 PVPs, not 4 at 1000 |
| R9 (Rate limiting) | Low (4 requests) | **Medium (80 requests)** | 80 requests changes the rate limit calculus |
| R10 (Stale data) | Low | **Medium** | is_stale flag not reaching client (Finding 1) |
| R11 (NEW) | N/A | **High / Certain** | max_batch_size blocks enrichment for >50 PVPs |
| R12 (NEW) | N/A | High | CB sensitivity with small chunks |
| R13 (NEW) | N/A | **Medium / Certain** | meta/metadata degrades DataFrame dtypes |
| R14 (NEW) | N/A | Medium | No client-side contract test |

### Phase 0 Prerequisites: COMPLETE

All blockers have been resolved. The doors are open for Phase 1.

| Prereq | Description | Status | Commit |
|--------|-------------|--------|--------|
| **P1** | Fix meta/metadata wire mismatch | DONE | `autom8y-data@0ad3c65` -- Added `alias="metadata"` + `by_alias=True` to server serialization. Wire key is now `"metadata"`. Client parsers already read `"metadata"`. |
| **P2** | Increase max_batch_size 50 -> 500 | DONE | `autom8y-asana@993f1f6` -- Default raised to 500, upper-bound validator rejects >1000. 4000 offers = 8 HTTP requests (~800ms), not 80 (~8s). |
| **P3** | Fix DataServiceJoinFetcher PVP chunking | DEFERRED | Not needed with P2 done. If batch_size is lowered below 500 in the future, the fetcher must implement pre-chunking. Guard comment added. |
| **P4** | Add bilateral contract test | DONE | `autom8y-asana@993f1f6` -- 22 tests in `test_server_contract.py` validating client parses post-P1 wire format. Documents field gaps (factory="unknown", missing row_count/insights_period/metric_types). |

Additionally, 10 pre-existing semgrep violations were fixed in autom8y-asana as part of the same commit (2 genuine fixes, 8 suppression/relocation of false positives).

### What's Open Now: Phase 1 Implementation Path

With Phase 0 complete, the spike's Phase 1 plan is viable as written (with minor adjustments):

1. **JoinSpec extension** -- Add `source`, `factory`, `period` fields (spike Section 4, unchanged)
2. **DataServiceJoinFetcher** -- The ~120 LOC glue class (spike Section 4, no longer needs pre-chunking since P2 raised batch size to 500)
3. **Engine step 7.5 dispatch** -- ~30 LOC if/else in QueryEngine.execute_rows() (spike Section 4, unchanged)
4. **Virtual entity registry** -- Register top 5 factories (spike Section 4, unchanged)
5. **Example saved query** -- `offers_with_spend.yaml` (spike Section 5, unchanged)
6. **Tests** -- Unit tests for fetcher + extended JoinSpec validation

**Revised Phase 1 estimate**: 0.5-0.75 days (original 0.5 was correct once blockers are resolved).

### Known Gaps Still Open (Not Blockers)

These were documented but are not required for Phase 1:

| Gap | Severity | Notes |
|-----|----------|-------|
| `factory` field missing from server metadata | Low | Client reads `metadata.get("factory", "unknown")`. Server's `InsightsResponseMeta` has no `factory` field. Phase 1 fetcher knows the factory from the JoinSpec, so this doesn't block joins -- it only affects introspection/debugging. |
| Token refresh on 401 | Medium | DataServiceClient reads API key once at init. Long CLI sessions may hit expired tokens. Tracked as REC-SI2 in arch report. |
| Shared circuit breaker | Medium | Enrichment and normal operations share one CB instance. 8 requests (post-P2) is manageable; was critical at 80 requests. Tracked as REC-SI3. |
| `--live` mode broken | Medium | Pre-existing, unrelated to enrichment. Shares step 7.5 code path. Tracked as AP-4. |
| Composite join keys | Low | `office_phone` alone works for offer/unit. Business joins need `(phone, vertical)`. Deferred per spike recommendation. |

### Summary

The spike's architectural design (Option B) is validated and the implementation path is clear. Phase 0 removed the three structural blockers. Phase 1 can begin with confidence that the wire format is correct, the batch size is adequate, and the contract is tested bilaterally.

---

## 9. Production Regression Audit (2026-02-25)

**Date**: 2026-02-25
**Trigger**: Smoke test regression from 11/12 tables (2026-02-24) to 7/12 tables (2026-02-25)
**Scope**: All INTERNAL_ERROR failures from `data.api.autom8y.io` in the insights export pipeline
**Method**: Direct API probing, commit archaeology, code path tracing

### 9.1 Executive Summary

**Initial audit (2026-02-25 morning)**: 5 of 12 insights export tables were failing with HTTP 500 (INTERNAL_ERROR) from the production data service — a regression from 11/12 (2026-02-24).

**Root cause identified**: Sprint 2 (`b32ce8b`) added `calls` fact table metrics to `account_level_stats`. The `calls` Parquet materialization failed silently in production (OOM during seed with 5-year lookback via in-memory DuckDB JOIN). Additionally, a rolling window date filter bug caused spend/cps/cpl to disappear from split queries with trailing periods.

**Post-hotfix (2026-02-25 afternoon)**: Two hotfixes deployed — **11/12 tables now pass**. Only T14 RECONCILIATIONS remains failing, identified as a server-side timeout under concurrent load.

| Severity | Tables Affected | Status |
|----------|----------------|--------|
| **P0 — RESOLVED** | 4 of 12 (SUMMARY, BY QUARTER, BY MONTH, BY WEEK) | Fixed by `b700128` (chunked seed materialization + graceful degradation) and `65f187e` (rolling window date filter + canonical date dimension) |
| **P2 — Pre-existing** | 1 of 12 (T14 RECONCILIATIONS) | Server-side timeout under concurrent load. Returns 200 in isolation (12s). Fails in concurrent batch (74s → INTERNAL_ERROR). |

### 9.2 Regression Timeline

| Date | Smoke Result | Commits Deployed | Key Changes |
|------|-------------|------------------|-------------|
| 2026-02-24 AM | 11/12 pass, 1 fail (T14 RECON) | Pre-Sprint 1 | Baseline after Phase 0 + ASANA-HYGIENE |
| 2026-02-24 PM | Not tested | Sprint 1 (`e1e5f50`), Sprint 2 (`b32ce8b`), Sprint 3 (`c69e0b0`) | MetricType enum, calls domain, adset/ad insights |
| 2026-02-25 AM | **7/12 pass, 5 fail** | All 3 sprints + CI fixes | Regression confirmed |
| 2026-02-25 PM | **11/12 pass, 1 fail (T14 RECON)** | Hotfixes `b700128` + `65f187e` | P0 regression resolved |

### 9.3 Root Cause Analysis

#### PRIMARY (RESOLVED): `account_level_stats` Crash (4 tables)

**Affected tables**: SUMMARY, BY QUARTER, BY MONTH, BY WEEK
**Affected endpoints**: `POST /api/v1/data-service/insights` with `frame_type=unit` or `frame_type=business`

**Two interrelated defects were identified and fixed:**

**Defect 1: OOM during calls seed materialization** (`b700128`)

Sprint 2 added the `calls` fact table with `seed_lookback_days=1825` (5 years). The materializer tried to load all records through an in-memory DuckDB `business_phone` JOIN on ECS → OOM → silent failure → missing `calls.parquet` → 500 on `account_level_stats` split queries.

Fix: Per-table seed configuration (`seed_lookback_days`, `seed_chunk_days` on `TableMaterializationConfig`) with chunked seed execution (90-day windows). Also added `on_error="skip"` to `execute_split_queries()` for graceful degradation when a fact table is absent.

**Defect 2: Rolling window date filter skip** (`65f187e`)

`TimeResolver` was skipping ALL SQL date filters for rolling windows (`trailing_n_days/weeks/months`), causing full Parquet scans back to `analytics_min_date` (2020-01-01). Additionally, `rolling_date_column` was resolved from a single base table (majority vote), producing table-specific names like `"created"` that failed in cross-table split queries.

Fix: Removed the date filter skip (TimePeriod.start/end already encode the correct outer data boundary). Changed to canonical `"date"` dimension which `adapt_dimensions_for_fact_table()` resolves per sub-query.

**Pre-hotfix API evidence** (probed 2026-02-25 AM):

| Request | Pre-Fix | Post-Fix | Notes |
|---------|---------|----------|-------|
| `frame_type=unit, period=LIFETIME` | **500** | **200** (6.3s) | SUMMARY table |
| `frame_type=unit, period=T30` | **500** | **200** | — |
| `frame_type=unit, period=QUARTER` | **500** | **200** | BY QUARTER table |
| `frame_type=business, period=T30` | **500** | **200** | Both map to `account_level_stats` |
| `frame_type=offer, period=LIFETIME` | 200 | 200 | Unaffected (no call metrics) |
| `frame_type=asset, period=T30` | 200 | 200 | Unaffected |

#### SECONDARY (PRE-EXISTING): T14 RECONCILIATIONS (1 table)

**Affected table**: T14 RECONCILIATIONS (method="reconciliation", window_days=14)
**Status**: Fails in concurrent smoke test, succeeds in isolation. Pre-existing since 2026-02-24 baseline.

**Evidence**:
- Direct API probe (2026-02-25 PM): `POST /api/v1/insights/reconciliation/execute` with `window_days=14` → **200 OK** in 12.2s (no cache).
- Smoke test (2026-02-25 PM): Failed at 74.3s with INTERNAL_ERROR — during a batch where 11 concurrent requests were running, including newly-uncached unit queries taking 20-56s each.

**Root cause**: Server-side timeout under concurrent load. The reconciliation insight requires a heavyweight query (`payments` + `ads_insights` JOIN with window aggregation, ~12s). When the smoke test fires all 11 API calls concurrently, the data service server is saturated by the unit/business queries (which are all cache misses post-fix). The reconciliation request either:
1. Hits a server-side request timeout (likely 60-75s) after queuing behind heavier queries
2. Gets rejected by the `LIMIT_HEAVY_ANALYTICS` rate limiter

**Assessment**: P2 pre-existing issue. The reconciliation insight itself is correct. The fix is either:
- Reduce concurrent smoke test parallelism (stagger heavy queries)
- Increase server-side timeout for the reconciliation/execute endpoint
- Wait for cache warm-up — subsequent runs will hit L1/L2 cache for the unit queries, freeing server capacity

### 9.4 Latent Issues Surfaced

Beyond the immediate regression, the investigation surfaced several latent issues in the data service:

#### L-1: No Integration Test Gate for New Fact Tables — PARTIALLY ADDRESSED

Sprint 2 added call metrics to `account_level_stats` without a CI gate that validates the full split-merge path with all referenced fact tables materialized. The hotfix `b700128` added `on_error="skip"` to `execute_split_queries()` for graceful degradation and 20 new tests in `test_chunked_seed.py`. However, there is still no CI gate that validates the end-to-end split-merge path with absent tables in a production-like environment.

**Severity**: Medium (mitigated by graceful degradation, but the gap remains)
**Remaining**: Add integration test for `account_level_stats` with `calls` table absent → should return metrics from the other 3 fact tables with null call columns.

#### L-2: `vertical_summary` Also References Call Metrics

`vertical_summary` (lines 89-92 in library.py) includes the same `in_calls`, `out_calls`, `time_on_call` metrics. It's not currently exposed via any `frame_type` mapping, but if it's used by any other code path (e.g., the reconciliation post-processor or a future frame_type), it will hit the same crash.

**Severity**: Medium (latent — not currently triggered via the insights API)

#### L-3: `call_volume` and `call_health` Standalone Insights

Sprint 2 registered two standalone call insights: `call_volume` and `call_health`. These are callable via `POST /api/v1/insights/call_volume/execute` and `call_health/execute`. If these are also failing (likely, since they reference the `calls` fact table), they represent additional broken endpoints.

**Severity**: Medium (no known consumer, but discoverable via the API)

#### L-4: Materializer Error Handling Is Silent

The materializer's `_resolve_business_phone_for_table()` for calls includes graceful degradation (returns DataFrame with NULL business_phone when chiropractors not available). But if the materializer itself fails to run (e.g., scheduler not configured for calls, or `call_type IS NOT NULL` filter removes all rows), there is no alert or health check endpoint that surfaces "table X has no materialized data."

**Severity**: Medium (operational gap — no visibility into materializer health)

#### L-5: `from __future__ import annotations` in `period_aggregator.py`

Sprint 1 added `from __future__ import annotations` to `period_aggregator.py`. This makes all type annotations lazy (strings). While this is fine for most cases, it can break runtime type inspection if any code does `isinstance()` checks on annotation values or if Pydantic model validators reference annotations from this module at runtime. No evidence of current breakage, but it's a fragile pattern in FastAPI/Pydantic codebases.

**Severity**: Low (no current evidence of breakage)

#### L-6: `ProbabilisticDenominatorFormula` in Period Aggregation

Sprint 1 added the `solid_scheds` two-phase recomputation to the period aggregation path. The `pre_recomputation_formulas` dict is passed through `aggregate_by_period()` → `recompute_rate_metrics()`. If the formula's `get_dependencies()` returns metric names that don't exist in the aggregated DataFrame (e.g., `pen` and `fut` are missing because the engine query didn't select them), the dependency check `all(dep in df.columns for dep in deps)` silently skips the recomputation. This means `solid_scheds` is silently stale in period tables when its dependencies are absent — correct behavior by design, but undocumented and untested in the degenerate case.

**Severity**: Low (silent correctness issue — `solid_scheds` falls back to raw `scheds`)

#### L-7: Sprint 3 Adset/Ad Insights Have No Smoke Test Coverage

Sprint 3 added `adset_level_stats` and `ad_level_stats` insight definitions. These are not exposed via the insights export pipeline (no `frame_type` mapping) and have no smoke test or production validation beyond unit tests. They may have undiscovered production issues similar to the calls problem.

**Severity**: Low (no known consumer, tested in CI only)

### 9.5 Hotfixes Applied (2026-02-25)

**Two commits deployed to resolve the P0 regression:**

#### Fix 1: `b700128` — Chunked seed materialization with graceful degradation

- Added per-table `seed_lookback_days` and `seed_chunk_days` to `TableMaterializationConfig`
- Calls table now seeds in 90-day chunks instead of loading 5 years into memory
- Added `on_error="skip"` to split query execution — if a fact table is absent, remaining fact tables still produce results (null columns for missing table)
- 20 new tests in `test_chunked_seed.py`
- Spike report: `docs/spikes/SPIKE-calls-materialization-root-cause.md`

#### Fix 2: `65f187e` — Rolling window date filter + canonical date dimension

- Removed unnecessary date filter skip in `TimeResolver` for rolling windows
- Changed `rolling_date_column` to canonical `"date"` dimension (adapted per sub-query)
- Fixed health endpoint tests crashing from `SDKAuthSettings` env validation
- ADR-RW-001, ADR-RW-002 documenting the design decisions

#### Post-Hotfix Smoke Test Results

| Table | Pre-Hotfix | Post-Hotfix | Duration |
|-------|-----------|-------------|----------|
| LEADS | PASS (100 rows) | PASS (100 rows) | 609ms |
| APPOINTMENTS | PASS (100 rows) | PASS (100 rows) | 903ms |
| LIFETIME RECONCILIATIONS | PASS (2 rows) | PASS (2 rows) | 11.9s |
| ASSET TABLE | PASS (6 rows) | PASS (6 rows) | 14.2s |
| **SUMMARY** | **FAIL** | **PASS (1 row)** | 20.5s |
| AD QUESTIONS | PASS (9 rows) | PASS (9 rows) | 21.8s |
| **BY MONTH** | **FAIL** | **PASS (6 rows)** | 44.6s |
| **BY WEEK** | **FAIL** | **PASS (23 rows)** | 45.7s |
| OFFER TABLE | PASS (1 row) | PASS (1 row) | 53.8s |
| **BY QUARTER** | **FAIL** | **PASS (3 rows)** | 56.5s |
| T14 RECONCILIATIONS | FAIL | FAIL (74.3s → timeout) | 74.3s |
| HTML Upload | PASS | PASS (211.6 KB) | — |

**Total**: 11/12 pass, 1 fail. Matches 2026-02-24 baseline.

#### Remaining Issue: T14 RECONCILIATIONS Timeout

The T14 RECONCILIATIONS failure persists as a pre-existing P2 issue. Direct API probes confirm the endpoint works (200 OK in 12.2s). The failure occurs only under concurrent smoke test load where 11 simultaneous heavy queries saturate the server. This will self-resolve as caches warm (the post-fix unit queries are 20-56s uncached but should be <1s cached).

**Next action**: Re-run smoke test after cache warm-up to confirm T14 RECONCILIATIONS passes.

### 9.6 Broader Architecture Observations

#### O-1: Insight Definition Changes Are Production-Breaking

Adding a metric from a new fact table to an existing insight definition is a **breaking change** in production, even though it's additive from a schema perspective. The split query mechanism silently depends on all referenced fact tables being materialized. There is no schema validation or graceful degradation at the insight execution layer — if one split query fails, the entire insight fails.

**Recommendation**: Implement a "soft metric" concept where insight definitions can declare optional metrics that are included only when their fact table is available. The split query planner should skip queries for unmaterialized tables rather than crashing.

#### O-2: `account_level_stats` Is the Most Critical Insight

`account_level_stats` is the single insight behind 2 of 5 frame_types (unit, business). It currently references metrics from 4 fact tables with ~40 metrics. It's the "god insight" — any addition to it carries outsized risk. Consider splitting it into:
- `core_performance` (ads_insights metrics: spend, imp, clicks, ctr, etc.)
- `lead_activity` (leads + appointments metrics: leads, scheds, booking_rate, etc.)
- `call_activity` (calls metrics: in_calls, out_calls, time_on_call)
- The `unit` frame_type would execute all three and merge, but each sub-insight would be independently resilient.

#### O-3: No Production Canary for New Fact Tables

The deploy pipeline (CI → ECS) has no canary step that validates new fact tables are materialized and queryable. A simple health-check probe per registered fact table (e.g., `SELECT 1 FROM <table> LIMIT 1` or Parquet file existence check) would catch this class of regression before it reaches production traffic.

### 9.7 Summary

| ID | Finding | Severity | Category | Status |
|----|---------|----------|----------|--------|
| **REG-1** | `account_level_stats` broken by calls OOM + date filter | **P0** | Regression | **RESOLVED** — `b700128` + `65f187e` |
| **REG-2** | T14 RECONCILIATIONS timeout under concurrent load | P2 | Pre-existing | Open — likely self-resolves with cache warm-up |
| L-1 | No integration test for split-merge with absent tables | Medium | Structural | Partially addressed (`on_error="skip"` + tests) |
| L-2 | `vertical_summary` also has call metrics | Medium | Latent | Open |
| L-3 | `call_volume`/`call_health` standalone insights may fail | Medium | Latent | Open (depends on calls materialization status) |
| L-4 | Materializer health not observable | Medium | Operational | Open |
| L-5 | `__future__ annotations` in period_aggregator | Low | Fragility | Open |
| L-6 | `solid_scheds` silent fallback in period tables | Low | Correctness | Open |
| L-7 | Sprint 3 adset/ad insights no production validation | Low | Coverage | Open |
| O-1 | New fact table metrics are breaking changes | — | Architecture | Mitigated by `on_error="skip"` |
| O-2 | `account_level_stats` is a god insight (4 fact tables) | — | Architecture | Recommendation |
| O-3 | No production canary for new fact tables | — | Architecture | Recommendation |
