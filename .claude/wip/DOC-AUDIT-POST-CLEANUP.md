# Doc Audit: Post-Cleanup v2 Reference Elimination

**Audit Date**: 2026-02-18
**Auditor**: doc-auditor
**Scope**: 12 files listed in the audit brief — v1/v2 staleness and inaccuracy only
**Excluded**: `docs/.archive/` — confirmed excluded from scope
**Triggered by**: Hygiene sprint that merged `query_v2.py` into `query.py`, unified error handling to dict-based `_ERROR_STATUS` mapping, unified DI to `Depends+Annotated` with `RequestId`, removed deprecated dependencies, and removed deprecated aliases. `src/autom8_asana/api/routes/query_v2.py` no longer exists. The unified router is imported in `routes/__init__.py`.

---

## Codebase Ground Truth (Reference Baseline)

Before per-file findings, the following current facts were confirmed by reading the actual source:

- **`src/autom8_asana/api/routes/query_v2.py`**: DOES NOT EXIST. Merged into `query.py`.
- **`src/autom8_asana/api/routes/query.py`**: EXISTS. Contains the unified router for all `/v1/query/*` endpoints: `POST /{entity_type}` (deprecated), `POST /{entity_type}/rows`, `POST /{entity_type}/aggregate`.
- **`src/autom8_asana/api/routes/__init__.py`**: Imports `from .query import router as query_router`. No reference to `query_v2`.
- **`docs/guides/patterns.md`**: EXISTS. See Section 12 for gap analysis.

---

## Per-File Findings

---

### File 1: `docs/api-reference/endpoints/query.md`

**Status: CLEAN — no stale v2 references**

This file was examined in full (835 lines). It does not use the terms "query v2," "v2 router," "v2 API," "query_v2.py," or "v1/v2 split." The document correctly presents the three endpoints as a unified API surface under a single router:

- `POST /v1/query/{entity_type}` (deprecated with sunset 2026-06-01)
- `POST /v1/query/{entity_type}/rows`
- `POST /v1/query/{entity_type}/aggregate`

**Sunset timeline**: Line 21 documents `Sunset: 2026-06-01`. This is present and accurate.

**cURL examples**: Multiple examples present at lines 97-104, 348-379, 384-397, 656-686, 670-686. All target `/v1/query/{entity_type}` or `/v1/query/{entity_type}/rows` or `/v1/query/{entity_type}/aggregate`. All endpoints reflect current behavior.

**Stale references found**: 0

**Action required**: None.

---

### File 2: `docs/api-reference/README.md`

**Status: CLEAN — no stale v2 references**

This file was examined in full (587 lines). The Query section at lines 480-485 reads:

```
### Query ([full reference](endpoints/query.md))

**Base path**: `/v1/query`
**Authentication**: S2S JWT

Entity querying operations.
```

No reference to a query split, `query_v2.py`, v1 router, v2 router, or any v1/v2 framing. The description is accurate and minimal.

**Sunset timeline**: Not mentioned in this file — this file is a route summary, not an endpoint reference. The sunset is documented in `endpoints/query.md`. No gap here.

**cURL examples**: This file contains examples for other route groups (tasks, resolver). The query section links to the full reference without its own example. No inaccurate examples.

**Stale references found**: 0

**Action required**: None.

---

### File 3: `docs/guides/entity-query.md`

**Status: MEDIUM — outdated framing in one section heading**

This file was examined in full (807 lines). It does not reference `query_v2.py`, the v2 router by name, or the v1/v2 split as a code-level concern. However, one section uses v2 framing in the deprecated-endpoint section:

**Line 160:**
```markdown
### POST /v1/query/{entity_type} (Deprecated)

Legacy query endpoint with flat equality filtering. Use `/rows` for new integrations.
```

This phrasing is accurate — the endpoint is deprecated — but the section does not use any "v2" label or reference removed code. The framing is therefore **not stale**; it is correct documentation of a still-existing deprecated endpoint.

**cURL examples**: Lines 125-134, 139-146, 151-158, 428-440 all target `/v1/query/{entity_type}/rows`. Lines 512-524 target `/v1/query/{entity_type}/aggregate`. All examples are accurate.

**Sunset timeline**: Line 166-167 documents `Sunset date: 2026-06-01`. Present and accurate.

**Stale references found**: 0 that reference removed code. The "Deprecated" section label is factually correct.

**Action required**: None.

---

### File 4: `docs/guides/patterns.md`

**Status: GAP — file exists but contains no canonical query patterns section**

`docs/guides/patterns.md` EXISTS (confirmed by filesystem check). The file was read in full (447 lines). It covers SDK-level patterns: relationship fields, change tracking, session lifecycle, positioning operations, partial failure handling, dependency cycles, parameter types, comment validation, thread safety, rate limiting, retry behavior, and exception hierarchy.

**v1/v2 references**: None. The file does not discuss the query API at all — not stale references, but an absence of coverage.

**Gap**: The file contains no section covering:
- When to use `/rows` vs. the deprecated `POST /{entity_type}` endpoint
- Predicate composition patterns (canonical AND/OR/NOT examples)
- Section scoping patterns
- Join patterns
- Aggregation patterns
- Error handling patterns specific to query (503 retry, 422 unknown field)

This gap is notable because the audit brief specifically flagged this file as "needs canonical patterns section (may not exist yet)." The section does not exist.

**Stale references found**: 0

**Action required**: ADD a query patterns section. This is a gap, not a staleness fix.

---

### File 5: `docs/examples/06-query-entities.py`

**Status: CRITICAL — docstring explicitly names removed "v2 API"**

This file was read in full (196 lines).

**Line 23:**
```python
async def main():
    """Query entities using the query v2 API."""
```

This docstring inside `main()` says "query v2 API." `query_v2.py` no longer exists. The unified endpoint is served from `query.py`. The term "v2 API" actively misleads engineers reading this example — they may search for `query_v2.py` or assume there is a versioned API distinction that no longer exists.

**Additional inaccuracies (not v1/v2 framing but factual errors in the example code):**

- **Line 59**: `for row in data["rows"][:3]:` — The response key is `data`, not `rows`. The current API returns `{"data": [...], "meta": {...}}`. This key name is wrong and would raise `KeyError` at runtime.
- **Line 90**: `for row in data["rows"]:` — Same incorrect key `"rows"` instead of `"data"`.
- **Lines 115-116** (`"op": "and"`, `"predicates": [...]`): Wrong predicate format. Current API uses `{"and": [...]}` not `{"op": "and", "predicates": [...]}`. This predicate would be rejected by the validator.
- **Line 138**: `if data["rows"]:` — Same wrong key.
- **Line 139**: `for row in data["rows"]:` — Same wrong key.

These additional errors are not v1/v2 framing issues per se, but they compound the staleness of this file. However, the scope of this audit is v1/v2 references. The `"query v2 API"` docstring is the in-scope finding.

**cURL examples**: No cURL examples in this file. It is a Python example.

**Sunset timeline**: Not mentioned. Not required in an example file.

**Stale references found**: 1 critical — line 23 docstring.

**Severity: CRITICAL** — Actively misleads engineers. The docstring identifies the API by a version designation that refers to removed code.

**Action required**: UPDATE line 23. Remove "v2" from the docstring. Replace with accurate description.

---

### File 6: `docs/design/TDD-dynamic-query-service.md`

**Status: HIGH — references `query_v2.py` as a rejected alternative and as a design option**

This file was read in full (1,040 lines). It is a Technical Design Document for Sprint 1 of the query engine. It pre-dates the cleanup sprint and contains v1/v2 framing throughout as design context.

**Key findings:**

**Line 173 (ADR-DQS-004, "Options Considered"):**
```markdown
3. **New module in `services/`** (e.g., `services/query_v2.py`)
```
This references `query_v2.py` as a design option that was considered and rejected. The file was eventually created as `api/routes/query_v2.py` (not `services/query_v2.py`), and is now removed.

**Lines 163-181 (ADR-DQS-004, decision rationale):**
```markdown
A separate `query_v2.py` would require a second router import and
registration, adding mechanical complexity for no architectural benefit.
```
This directly references `query_v2.py` by name as the rejected alternative. Now that the file has been merged, this rationale is historically accurate but forward-looking readers may be confused about the file's existence.

**Line 219 (Module Structure table):**
```markdown
api/routes/
    query.py    # MODIFIED: add /rows endpoint, deprecation headers
```
This is accurate — `query.py` was the target. No mention of `query_v2.py` in the module structure table.

**Line 239 (Modified Files table):**
```markdown
| `api/routes/__init__.py` | No changes (same router) |
```
This is now inaccurate — `__init__.py` currently imports from `query.py` (which it did before), but the cleanup sprint's unification of DI may have involved changes not reflected here.

**Lines 43-44 (architectural diagram, Section 1.2):**
```
POST /v1/query/{et}          POST /v1/query/{et}/rows
(existing, deprecated)       (new, Sprint 1)
```
This framing is still accurate in terms of endpoint behavior, though it reflects a pre-cleanup state.

**Assessment**: This is a historical TDD. It documents the design decisions made before `query_v2.py` existed, including the explicit rejection of `query_v2.py` as a module path. The references to `query_v2.py` in this document are design history, not forward-facing documentation. However, they could cause confusion for engineers who do not know the file no longer exists.

**Stale references found**: 2
- Line 173: `services/query_v2.py` (design option, now also removed)
- Lines 163-181: `query_v2.py` named as rejected alternative (now moot — both options are resolved)

**Severity: HIGH** — References removed code by name. Not actively dangerous (it is a design doc, not a runbook or guide), but creates confusion about the current state.

**Action required**: ADD a note at the top of the document marking it as superseded by the cleanup sprint. Or annotate the specific references to indicate the file no longer exists and the merged design is now in `query.py`.

---

### File 7: `docs/design/TDD-aggregate-endpoint.md`

**Status: HIGH — references `query_v2.py` as the active route file throughout**

This file was read in full (1,188 lines). It is the TDD for Sprint 2 of the query engine (aggregate endpoint). Unlike the Sprint 1 TDD which rejected `query_v2.py`, this TDD assumes `query_v2.py` was created and actively uses it as the route handler location.

**Critical references:**

**Line 170 (Modified Files, Section 3.2):**
```markdown
src/autom8_asana/api/routes/
    query_v2.py       # + POST /{entity_type}/aggregate route handler
```
`query_v2.py` does not exist. The aggregate handler now lives in `query.py`.

**Line 745 (Section 8.2, `_ERROR_STATUS` mapping):**
```markdown
The `_ERROR_STATUS` mapping in `query_v2.py` is extended:
```
`query_v2.py` does not exist. The `_ERROR_STATUS` dict-based mapping now lives in `query.py` per the cleanup sprint description.

**Line 810 (Section 10, Route Handler Design heading):**
```markdown
## 10. Route Handler Design (`api/routes/query_v2.py`)
```
The section heading names a file that does not exist.

**Line 813 (route handler code snippet):**
```python
@router.post("/{entity_type}/aggregate", response_model=AggregateResponse)
async def query_aggregate(
    entity_type: str,
    request_body: AggregateRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> AggregateResponse:
```
The DI pattern shown (`Annotated[ServiceClaims, Depends(require_service_claims)]`) matches the current post-cleanup canonical form, but the file attribution (`query_v2.py`) is wrong.

**Line 841 (import additions):**
```python
from autom8_asana.query.errors import AggregateGroupLimitError
from autom8_asana.query.models import AggregateRequest, AggregateResponse
```
Import target modules do not depend on `query_v2.py`, so these lines are accurate in isolation.

**Line 1069 (implementation task, Phase 3):**
```markdown
| 10 | Add POST /{entity_type}/aggregate handler | `api/routes/query_v2.py` | 8 | 70 |
```
File target in the task table is wrong.

**Line 1071 (implementation task, Phase 3):**
```markdown
| 12 | Integration tests for /aggregate route | `tests/api/test_routes_query_aggregate.py` | 10 | 200 |
```
Test file reference is not a v2 reference — this is fine.

**Line 1187 (Attestation Table):**
```markdown
| Route handler (query_v2) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query_v2.py` | Yes |
```
The attested file does not exist.

**Stale references found**: 6
- Line 170: `query_v2.py` in modified files table
- Line 745: `_ERROR_STATUS mapping in query_v2.py`
- Line 810: Section heading names `query_v2.py`
- Line 1069: Task table names `query_v2.py`
- Line 1187: Attestation table attests a non-existent file

**Severity: HIGH** — This TDD describes a component whose implementation file no longer matches the documented location. Engineers using this as a reference for the aggregate endpoint will look for `query_v2.py` and not find it.

**Action required**: UPDATE multiple locations to replace `query_v2.py` with `query.py`. Add a note that the cleanup sprint unified the routers.

---

### File 8: `src/autom8_asana/api/routes/__init__.py`

**Status: CLEAN — no stale v2 references**

This file was read in full (52 lines). The docstring at lines 1-22 lists current routes:

```python
"""API route aggregation.

...
Current routes:
- Health router (/health) - unauthenticated
- Users router (/api/v1/users) - authenticated
- Workspaces router (/api/v1/workspaces) - authenticated
- DataFrames router (/api/v1/dataframes) - authenticated
- Tasks router (/api/v1/tasks) - authenticated
- Projects router (/api/v1/projects) - authenticated
- Sections router (/api/v1/sections) - authenticated
- Internal router (/api/v1/internal) - S2S only (service token required)
- Resolver router (/v1/resolve) - S2S only (entity resolution)
- Query router (/v1/query) - S2S only (entity query)
- Entity write router (/api/v1/entity) - S2S only (entity write)
"""
```

No mention of `query_v2`, a "v2 router," or a split query router. Line 30 confirms the import: `from .query import router as query_router`. This is accurate — the unified router comes from `query.py`.

There is no `query_v2_router` import or reference anywhere in this file.

**Stale references found**: 0

**Action required**: None.

---

### File 9: `.claude/wip/q1_arch/docs/TOPOLOGY-AUTOM8Y-ASANA.md`

**Status: HIGH — router table lists both "Query v1" and "Query v2" as distinct active routers**

This file was read in full (569 lines). The API surface map at lines 236-248 contains a router table with an explicit v1/v2 split:

**Lines 236-248:**
```markdown
#### Query v1 (`/v1/query`, `include_in_schema=False`)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| POST | `/v1/query/{entity_type}` | Query entities (predicate DSL) | S2S JWT | High |
| POST | `/v1/query/{entity_type}/rows` | Query entity rows | S2S JWT | High |

#### Query v2 (`/v1/query`, `include_in_schema=False`)

| Method | Path | Summary | Auth | Confidence |
|--------|------|---------|------|------------|
| POST | `/v1/query/{entity_type}/rows` | Query rows (v2) | S2S JWT | High |
| POST | `/v1/query/{entity_type}/aggregate` | Aggregate query (v2) | S2S JWT | High |
```

This describes two separate routers — "Query v1" and "Query v2" — as distinct registered components. After the cleanup sprint, there is one router (`query.py`) serving all four endpoints. The "Query v2" section corresponds to routes that no longer come from a separate file.

**Additionally, lines 521-525 (Unknowns section):**
```markdown
### Unknown: Query v1 vs v2 coexistence

- **Question**: Are both query router versions (`query.py` at `/v1/query` and `query_v2.py` at `/v1/query`) active simultaneously?...
- **Evidence**: Both routers are imported and included in `api/main.py`.
```

This unknown was written when `query_v2.py` existed. The unknown is now resolved: `query_v2.py` has been deleted and merged into `query.py`. The unknowns section should be updated to reflect the resolved state.

**Stale references found**: 2
- Lines 243-248: "Query v2" router table entry (separate router no longer exists)
- Lines 521-525: Unknown about v1/v2 coexistence (now resolved)

**Severity: HIGH** — This topology document is authoritative for understanding the API surface. The split router table misrepresents the current architecture.

**Action required**: UPDATE the router table to consolidate "Query v1" and "Query v2" into a single "Query" section. UPDATE or REMOVE the unknown about v1/v2 coexistence — it is now resolved.

---

### File 10: `.claude/wip/q1_arch/docs/DEPENDENCY-MAP-AUTOM8Y-ASANA.md`

**Status: HIGH — critical path trace names `query_v2.py` as the active route file**

This file was read in full (816 lines). The critical path analysis at Section 6.1 (lines 554-606) describes the entity query critical path. Lines 554 and 600 reference `query_v2.py`:

**Line 554:**
```markdown
[1] api/routes/query_v2.py: POST /v1/query/{entity_type}/rows
```

**Lines 598-606 (Key files section):**
```markdown
**Key files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query_v2.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/engine.py`
...
```

The first entry in the key files list — `query_v2.py` — does not exist. The critical path trace is the most practically useful section of the dependency map for engineers debugging the query path. An engineer following this trace to debug a query issue will look for `query_v2.py` and find nothing.

**Stale references found**: 2
- Line 554: `api/routes/query_v2.py` in the critical path trace narrative
- Line 601: `query_v2.py` in the key files list

**Severity: HIGH** — The critical path trace is a navigation aid. Pointing to a deleted file actively misguides engineers.

**Action required**: UPDATE lines 554 and 601 to reference `api/routes/query.py`.

---

### File 11: `.claude/wip/q1_arch/docs/ARCHITECTURE-REPORT-AUTOM8Y-ASANA-Q1-2026.md`

**Status: HIGH — multiple references to `query_v2.py` as the active v2 route file, and to the routing conflict as unresolved**

This file was read in full (826 lines). It contains four categories of stale reference:

**Category A — `query_v2.py` named as the active v2 route file:**

**Line 150:**
```markdown
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query_v2.py` (active v2 query route)
```

**Category B — routing conflict described as active:**

**Lines 140-141:**
```markdown
A versioning seam creates a routing risk. Two query router versions (`query.py` and `query_v2.py`) share the prefix `/v1/query`. Both register `POST /{entity_type}/rows`. FastAPI registers routes in registration order; the second handler for a duplicate path is silently ignored.
```

This entire paragraph describes a problem that no longer exists. `query_v2.py` has been deleted and merged into `query.py`.

**Lines 271-274 (QW-6 recommendation):**
```markdown
**QW-6: Resolve query v1/v2 routing ambiguity and begin v1 consumer inventory**
...
**Action**: Confirm which `/rows` handler wins (add a distinguishing field to v1 and v2 responses in a dev environment and call the endpoint). If v1 is shadowing v2, reorder router registration in `api/main.py`.
```

This quick-win recommendation describes work that has already been completed by the cleanup sprint.

**Lines 442-449 (XR-004 cross-rite referral):**
```markdown
### Cross-Rite Referral: XR-004
...
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query.py` (v1 router, deprecated)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query_v2.py` (v2 router, active)
- Both routers registered in `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/main.py`
- Route collision: both routers register `POST /{entity_type}/rows` at prefix `/v1/query`
```

All four bullets reference the split-router state. The route collision is resolved.

**Lines 539-544 (Unknown U-006):**
```markdown
### Unknown: U-006 — Query v1 traffic volume and consumer list
...
- v1 router imported and registered in `api/main.py`. v2 router also registered.
- Route collision: both v1 and v2 register `/rows` at prefix `/v1/query`
```

The route collision part of this unknown is now resolved.

**Lines 708-710 (Phase 1 roadmap):**
```markdown
| QW-6 | Resolve query v1/v2 routing ambiguity; begin consumer inventory | 1 day | API owner |
```

QW-6 is resolved by the cleanup sprint. This roadmap item should be marked complete.

**Stale references found**: 6
- Line 150: `query_v2.py` listed as active v2 route file
- Lines 140-141: Routing conflict described as active problem
- Lines 271-274: QW-6 recommendation (already completed)
- Lines 442-449: XR-004 cross-rite referral evidence (route collision resolved)
- Lines 539-544: Unknown U-006 (route collision aspect resolved)
- Lines 708-710: QW-6 in Phase 1 roadmap (completed item)

**Severity: HIGH** — This is the terminal architecture report. Engineers reading it will see QW-6 (routing ambiguity fix) as an open action item and XR-004 as an open referral, when both are resolved. The report's recommendation section contains completed work described as future work.

**Action required**: ADD a post-cleanup note at the top of the report marking QW-6 as completed and noting that `query_v2.py` has been merged into `query.py`. UPDATE or annotate lines 140-141, 150, 271-274, 442-449, 539-544, 708-710 to reflect resolved state.

---

### File 12: `.claude/wip/q1_arch/docs/ARCHITECTURE-ASSESSMENT-AUTOM8Y-ASANA.md`

**Status: HIGH — has an explicit "Unknown: Query v1 vs v2 coexistence" section that is now resolved**

This file was read in full (476 lines). The Unknowns section at lines 419-424 contains:

**Lines 419-424:**
```markdown
### Unknown: Query v1 vs v2 coexistence

- **Question**: Are both query router versions (`query.py` at `/v1/query` and `query_v2.py` at `/v1/query`) active simultaneously? Do their routes conflict?
- **Why it matters**: Both share the same prefix `/v1/query`. The v1 router has `POST /{entity_type}` and `POST /{entity_type}/rows`. The v2 router has `POST /{entity_type}/rows` and `POST /{entity_type}/aggregate`. The `/rows` path overlaps.
- **Evidence**: Both routers are imported and included in `api/main.py`. FastAPI will register both, but overlapping paths may cause routing ambiguity.
- **Suggested source**: Migration plan or deprecation timeline for query v1
```

This unknown is resolved. `query_v2.py` no longer exists. The routing ambiguity is eliminated by the cleanup sprint.

**No other v1/v2 stale references were found in this file.** The rest of the document uses "query.py" and "query_v2.py" only in the context of this unknowns section.

**Stale references found**: 1
- Lines 419-424: "Unknown: Query v1 vs v2 coexistence" (now resolved)

**Severity: HIGH** — An open unknown in the architecture assessment is now factually incorrect. Engineers reading this assessment will see a known unknown that has been resolved.

**Action required**: UPDATE lines 419-424 to mark the unknown as resolved, citing the cleanup sprint commit.

---

## Gap Analysis: `docs/guides/patterns.md`

`docs/guides/patterns.md` exists and contains 447 lines covering SDK patterns. It does NOT contain a canonical query patterns section.

**Missing content:**
1. When to use `POST /{entity_type}/rows` vs. the deprecated `POST /{entity_type}` endpoint
2. Canonical predicate composition patterns (AND/OR/NOT with concrete examples)
3. Section scoping pattern
4. Cross-entity join pattern
5. Aggregation pattern
6. Error handling patterns (503 retry logic, 422 field validation)
7. Pagination pattern for query results

This is a documentation gap, not a staleness issue. It should be added, not repaired.

---

## Quantitative Summary

| Metric | Count |
|--------|-------|
| Files audited | 12 |
| Files with stale v1/v2 references | 6 |
| Files clean (no stale references) | 5 |
| Files with gaps (not staleness) | 1 |
| Total stale reference instances found | 18 |
| By severity: Critical | 1 |
| By severity: High | 14 |
| By severity: Medium | 0 |
| By severity: Medium (outdated framing — patterns gap) | 3 gap instances |
| Files referencing `query_v2.py` by name | 4 |
| Files where routing conflict described as unresolved | 3 |
| Files where `query v2 API` label used | 1 |

**Breakdown by file:**

| File | Stale Refs | Severity |
|------|-----------|----------|
| `docs/api-reference/endpoints/query.md` | 0 | — |
| `docs/api-reference/README.md` | 0 | — |
| `docs/guides/entity-query.md` | 0 | — |
| `docs/guides/patterns.md` | 0 (GAP) | Gap only |
| `docs/examples/06-query-entities.py` | 1 | Critical |
| `docs/design/TDD-dynamic-query-service.md` | 2 | High |
| `docs/design/TDD-aggregate-endpoint.md` | 6 | High |
| `src/autom8_asana/api/routes/__init__.py` | 0 | — |
| `.claude/wip/q1_arch/docs/TOPOLOGY-AUTOM8Y-ASANA.md` | 2 | High |
| `.claude/wip/q1_arch/docs/DEPENDENCY-MAP-AUTOM8Y-ASANA.md` | 2 | High |
| `.claude/wip/q1_arch/docs/ARCHITECTURE-REPORT-AUTOM8Y-ASANA-Q1-2026.md` | 6 | High |
| `.claude/wip/q1_arch/docs/ARCHITECTURE-ASSESSMENT-AUTOM8Y-ASANA.md` | 1 | High |

---

## Prioritized Action List

### Must Update (Critical — actively misleads)

1. **`docs/examples/06-query-entities.py`, line 23** — Remove "query v2 API" from the `main()` docstring. Replace with a description of the current unified query API.

### Must Update (High — references removed code)

2. **`docs/design/TDD-aggregate-endpoint.md`** — Update 6 locations (lines 170, 745, 810, 1069, 1187) to replace `query_v2.py` with `query.py`. Add a header note that the cleanup sprint merged the router.

3. **`.claude/wip/q1_arch/docs/ARCHITECTURE-REPORT-AUTOM8Y-ASANA-Q1-2026.md`** — Add a post-cleanup header note. Mark QW-6 as completed in the Phase 1 roadmap. Annotate lines 140-141, 150, 271-274, 442-449, 539-544 to reflect the resolved routing state.

4. **`.claude/wip/q1_arch/docs/TOPOLOGY-AUTOM8Y-ASANA.md`** — Consolidate the "Query v1" and "Query v2" router sections into a single "Query" router section. Update the Unknowns section (lines 521-525) to mark the v1/v2 coexistence question as resolved.

5. **`.claude/wip/q1_arch/docs/DEPENDENCY-MAP-AUTOM8Y-ASANA.md`** — Update the critical path trace (lines 554, 601) to reference `api/routes/query.py` instead of `api/routes/query_v2.py`.

6. **`.claude/wip/q1_arch/docs/ARCHITECTURE-ASSESSMENT-AUTOM8Y-ASANA.md`** — Update the "Unknown: Query v1 vs v2 coexistence" section (lines 419-424) to mark it as resolved.

7. **`docs/design/TDD-dynamic-query-service.md`** — Add a note at the document top or annotate lines 173 and 163-181 to clarify that `query_v2.py` was ultimately created then removed, and that the aggregate endpoint lives in `query.py`.

### Must Add (Gap)

8. **`docs/guides/patterns.md`** — Add a query patterns section covering: endpoint selection (rows vs. deprecated), predicate composition, section scoping, joins, aggregation, error handling, and pagination.

### No Action Required

- `docs/api-reference/endpoints/query.md` — Clean.
- `docs/api-reference/README.md` — Clean.
- `docs/guides/entity-query.md` — Clean.
- `src/autom8_asana/api/routes/__init__.py` — Clean.

---

## Confirmation: `docs/.archive/` Excluded

`docs/.archive/` was not scanned. Confirmed excluded from scope per audit brief instructions.

---

## Handoff Notes for Information Architect

The 12 files fall into four categories:

1. **Current public API docs** (files 1-3, 8): All clean. No structural changes needed here. These accurately reflect the post-cleanup state.

2. **Example file** (file 5): One critical inaccuracy in the docstring, plus additional inaccuracies in the code body (wrong response key `"rows"` instead of `"data"`, wrong predicate format) that are out of scope for this v1/v2 audit but compound the staleness.

3. **Design TDDs** (files 6-7): Historical documents that pre-date the cleanup sprint. Both need annotation or update to clarify that `query_v2.py` has been merged. These are not public-facing docs; they are WIP design artifacts. A light-touch annotation approach may be preferable to full rewrites.

4. **Architecture WIP docs** (files 9-12): These are arch-rite outputs (`q1_arch/docs/`). All four contain stale references to the v1/v2 split. The most impactful is the architecture report (file 11), which contains QW-6 as an open action item — an action that has already been completed.

The patterns gap (file 4) is the only pure gap: no stale content to remove, only missing content to add.
