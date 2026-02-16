# TDD: Runtime Remediation Sprint 3 -- Builder Infrastructure Section Filtering

```yaml
id: TDD-RUNTIME-REM-S3
initiative: INIT-RUNTIME-REM-001
rite: 10x-dev
agent: architect
upstream: PROMPT-0-runtime-remediation, SMELL-RUNTIME-EFF-001, TDD-RUNTIME-REM-S1, TDD-RUNTIME-REM-S2
downstream: principal-engineer
date: 2026-02-15
status: ready-for-review
```

---

## 1. Executive Summary

Two findings target section filtering in the builder infrastructure. After thorough codebase analysis, both are **NOT RECOMMENDED** for implementation. The decisive finding is that the SMELL report's dependency claim -- "AT1-001 delegates to ParallelSectionFetcher" -- is **factually incorrect**. The two builders have entirely separate code paths and independent `_list_sections()` methods. This changes the dependency chain, blast radius, and value calculation fundamentally.

| ID | Finding | Score | Decision |
|----|---------|:-----:|----------|
| AT1-002 | ParallelSectionFetcher fetches ALL sections | 47 | **NOT RECOMMENDED** -- zero production instantiations; dead infrastructure |
| AT1-001 | ProgressiveBuilder fetches ALL sections | 53 | **NOT RECOMMENDED** -- correct approach requires classifier injection into 8+ caller sites; high blast radius for moderate savings; resume/manifest logic incompatible with filtered section lists |

### Critical Discovery: ParallelSectionFetcher Has Zero Production Callers

A grep for `ParallelSectionFetcher(` across the entire `src/` tree returns exactly one match: the class definition itself (line 85 of `parallel_fetch.py`). No production code instantiates `ParallelSectionFetcher`. It is re-exported from `builders/__init__.py` and exercised in `tests/unit/dataframes/test_parallel_fetch.py`, but never used in any production workflow, preload, or builder path.

**Evidence:**

```
# Instantiation sites in src/
src/autom8_asana/dataframes/builders/parallel_fetch.py:85   class ParallelSectionFetcher:
src/autom8_asana/dataframes/builders/parallel_fetch.py:102  >>> fetcher = ParallelSectionFetcher(   # docstring example

# Import sites in src/
src/autom8_asana/dataframes/builders/__init__.py:58     ParallelSectionFetcher,  # re-export only

# Actual production callers: NONE
```

### Critical Discovery: ProgressiveProjectBuilder Does Not Delegate to ParallelSectionFetcher

The SMELL report states: "AT1-002 is shared infrastructure used by ProgressiveProjectBuilder" and PROMPT-0 states: "AT1-001 is blocked by AT1-002 -- progressive builder delegates to ParallelSectionFetcher."

This is incorrect. `ProgressiveProjectBuilder` has its own `_list_sections()` method at line 562 of `progressive.py`:

```python
async def _list_sections(self) -> list[Section]:
    """List sections for the project."""
    sections: list[Section] = await self._client.sections.list_for_project_async(
        self._project_gid
    ).collect()
    return sections
```

There is no import of `parallel_fetch` in `progressive.py`. There is no use of `ParallelSectionFetcher` anywhere in the progressive builder. The dependency chain asserted in the SMELL report does not exist.

---

## 2. Finding Analysis

### 2.1 AT1-002: ParallelSectionFetcher Fetches ALL Sections -- NOT RECOMMENDED

#### Analysis

**ParallelSectionFetcher** is a well-engineered class with caching layers (30-min section list, 5-min GID enumeration), parallel fetch via `asyncio.gather`, and deduplication. However, it has **zero production instantiations**.

All 8+ production sites that build DataFrames use `ProgressiveProjectBuilder` directly:

| Caller | File:Line | Uses ParallelSectionFetcher? |
|--------|-----------|:---:|
| `Project.to_dataframe_async` | `models/project.py:216` | No |
| `Project.to_dataframe_parallel_async` | `models/project.py:310` | No |
| `UniversalDataFrameStrategy._build_dataframe_async` | `services/universal_strategy.py:603` | No |
| `swr_build_dataframe_async` | `cache/dataframe/factory.py:73` | No |
| `ProgressivePreloader.process_project` | `api/preload/progressive.py:293` | No |
| `LegacyPreloader._preload_one` | `api/preload/legacy.py:488,591` | No |
| `AdminRoutes.rebuild_project` | `api/routes/admin.py:286` | No |

Every single caller constructs a `ProgressiveProjectBuilder` and calls `build_progressive_async()`. The progressive builder calls its own `self._list_sections()` which calls `self._client.sections.list_for_project_async()` directly.

**Why optimization is not recommended:**

1. **Zero production impact**: Adding a `section_filter` parameter to a class that nobody instantiates saves zero API calls in production.

2. **The class may be vestigial infrastructure**: `ParallelSectionFetcher` appears to predate `ProgressiveProjectBuilder`. The progressive builder absorbed its functionality (section-by-section parallel fetch with bounded concurrency via `gather_with_limit`) while adding resume/manifest/S3 persistence capabilities. The `fetch_all()`, `fetch_section_task_gids_async()`, and `fetch_by_gids()` methods are public API surface with no callers.

3. **Modifying dead infrastructure is negative value**: Any change to `ParallelSectionFetcher` requires updating its tests, but produces no runtime benefit. It creates maintenance burden on code that is not exercised in production.

**Re-scored assessment:**

| Dimension | Weight | Original Score | Revised Score | Rationale |
|-----------|--------|:-:|:-:|-----------|
| API calls saved | 40% | 5 | 0 | Zero production instantiations. No API calls saved. |
| Execution frequency | 30% | 7 | 0 | Never executes in production. |
| Implementation complexity | 20% | 5 | 5 | Moderate -- adding optional filter parameter, updating cache logic. |
| Risk | 10% | 5 | 8 | Low risk (no production callers to break). |

**Revised weighted score**: (0 * 0.4) + (0 * 0.3) + (5 * 0.2) + (8 * 0.1) = 0 + 0 + 1.0 + 0.8 = **1.8**

A score of 1.8 makes this finding non-actionable. The correct future action is not optimization but a cleanup decision: either wire `ParallelSectionFetcher` into a production path, or remove it. That is a structural quality decision outside the scope of this runtime remediation initiative.

**ADR**: See ADR-S3-001 in Section 5.

---

### 2.2 AT1-001: ProgressiveBuilder Fetches ALL Sections -- NOT RECOMMENDED

#### Analysis

With the AT1-002 dependency removed (the progressive builder does not delegate to `ParallelSectionFetcher`), AT1-001 is now independent. The question becomes: should `ProgressiveProjectBuilder._list_sections()` filter by classifier ACTIVE status?

**Current behavior** (`progressive.py:562-567`):

```python
async def _list_sections(self) -> list[Section]:
    """List sections for the project."""
    sections: list[Section] = await self._client.sections.list_for_project_async(
        self._project_gid
    ).collect()
    return sections
```

The builder fetches ALL sections (36 for Offer, 14 for Unit). The section list is used in:

1. **Section GID enumeration** (line 402): `section_gids = [s.gid for s in sections]`
2. **Manifest creation** (line 342-348): `create_manifest_async(project_gid, entity_type, section_gids, ...)`
3. **Resume logic** (line 224): `manifest.get_incomplete_section_gids()` returns GIDs of sections not yet COMPLETE in the manifest
4. **Freshness probing** (line 238): Probes COMPLETE sections for staleness
5. **Section fetch loop** (line 454-466): Iterates `resume_result.sections_to_fetch`

**Estimated savings:**

| Project | Total Sections | ACTIVE Sections | Non-ACTIVE Skipped | Savings |
|---------|:---:|:---:|:---:|--------|
| Offer | 36 | 24 | 12 | 33% fewer section fetches on cold build |
| Unit | 14 | 3 | 11 | 79% fewer section fetches on cold build |

These savings apply only to **cold builds** (no manifest). On resume builds (the common path for the preload system), only incomplete sections are fetched regardless of ACTIVE status. On freshness probes (the most common production path), only the GID hash check fires -- no full section fetch occurs.

**Why optimization is not recommended:**

**1. Manifest/resume incompatibility creates a one-way door.**

The manifest tracks ALL section GIDs for the project. If the builder starts creating manifests that only track ACTIVE sections, existing manifests become incompatible:

- A manifest created before the change tracks 36 sections (Offer). After the change, the builder expects 24 sections. The resume logic (`get_incomplete_section_gids()`) would mark 12 formerly-tracked non-ACTIVE sections as "incomplete" because they are not in the new section list. The builder would attempt to fetch them -- defeating the optimization.

- Conversely, if a manifest was created with filtered sections and the classifier is later updated (section reclassified from IGNORED to ACTIVE), the new ACTIVE section would not be in the manifest, requiring a full rebuild.

Solving this requires manifest schema versioning, migration logic, or a manifest flag indicating whether the section list was filtered. This is significant new infrastructure for a moderate savings that only applies to cold builds.

**2. Classifier injection into 8+ caller sites is high blast radius.**

The builder currently takes `entity_type: str` in its constructor. Looking up a classifier requires `get_classifier(entity_type)`, which returns `None` for entity types without classifiers (e.g., "contact", "task"). The caller sites do not currently pass classifiers:

```python
# Current: 8+ sites look like this
builder = ProgressiveProjectBuilder(
    client=client,
    project_gid=project_gid,
    entity_type=entity_type,
    schema=schema,
    persistence=persistence,
    ...
)
```

Adding a `section_classifier: SectionClassifier | None = None` parameter is safe from a signature perspective (optional, defaults to None). But the **correct behavior** depends on the caller's intent:

- Preload builds (progressive.py, legacy.py) want ALL data for completeness -- downstream consumers may filter differently
- Cache warming (factory.py) wants ALL data for the DataFrame cache
- User queries (project.py, universal_strategy.py) serve multiple consumers, some of which need non-ACTIVE sections for historical analysis

Only ONE of the 8+ callers (the preload system) might genuinely benefit from section filtering, and even that is questionable: if a consumer requests data for an INACTIVE section (e.g., for churn analysis), the cached DataFrame would be missing it.

**3. The savings are moderate and apply only to the cold-build path.**

Cold builds are the least common execution mode in production. The preload system's primary path is:
1. Check S3 parquet (pre-warmed by Lambda) -- most common, zero API calls
2. Resume from manifest (partial build) -- second most common, fetches only incomplete sections
3. Full cold build -- least common, only on first deployment or manifest corruption

For Offer (the larger project), the saving is 12 section fetches out of 36 -- each section fetch is a paginated `list_async(section=section_gid)` call. At ~100-300ms per section, this saves 1.2-3.6 seconds on a cold build that takes 30-60 seconds total. The percentage improvement is 4-12% on a path that rarely fires.

For Unit, the saving is more dramatic (79%) but Unit has only 14 sections with 3 ACTIVE, meaning the total section data volume is much smaller to begin with.

**4. The proven pattern operates at a different layer.**

The existing section-targeted fetch pattern (in `insights_export.py` and `pipeline_transition.py`) works at the **workflow** layer, not the builder layer. These workflows know their specific classification requirements (e.g., "I only need ACTIVE offers") and use `resolve_section_gids()` + per-section `list_async(section=gid)`. They do NOT use `ProgressiveProjectBuilder` at all -- they build targeted task lists for specific workflow operations.

The builder, by contrast, is a **data infrastructure** component that builds complete DataFrames for caching and serving. Its job is to produce a complete view of the project's data. Filtering at the builder level conflates two concerns: "what sections exist" (infrastructure) with "which sections matter for this use case" (business logic).

**5. The anti-pattern warning from PROMPT-0 is directly relevant.**

> "Do not break the ParallelSectionFetcher contract carelessly -- it is shared infrastructure used by multiple callers"

While ParallelSectionFetcher turned out to have zero callers, the spirit of this warning applies to `ProgressiveProjectBuilder`, which genuinely IS shared infrastructure with 8+ callers. Changing the section enumeration behavior of the builder affects all callers, and the "right" filtering behavior differs per caller.

**Re-scored assessment:**

| Dimension | Weight | Original Score | Revised Score | Rationale |
|-----------|--------|:-:|:-:|-----------|
| API calls saved | 40% | 5 | 2 | Saves section fetches only on cold builds (rare path). Resume and freshness probe paths are unaffected. |
| Execution frequency | 30% | 7 | 2 | Cold builds are the least common execution mode. Preload primarily uses S3 parquet or resume. |
| Implementation complexity | 20% | 4 | 2 | Manifest incompatibility, 8+ caller sites, classifier injection, consumer intent divergence. |
| Risk | 10% | 5 | 3 | High blast radius. Manifest migration needed. Consumer data completeness risk. |

**Revised weighted score**: (2 * 0.4) + (2 * 0.3) + (2 * 0.2) + (3 * 0.1) = 0.8 + 0.6 + 0.4 + 0.3 = **21**

A score of 21 is well below the PROMPT-0 threshold of 40. The finding should be documented and deferred.

**ADR**: See ADR-S3-002 in Section 5.

---

## 3. Before/After Contract

Neither finding is recommended for implementation. No before/after contracts are required.

---

## 4. Sequencing and Risk

### 4.1 Sprint 3 Outcome

Both findings assigned to this sprint (AT1-002 and AT1-001) are NOT RECOMMENDED after analysis. The sprint produces two ADRs documenting the analysis and decisions, plus this TDD.

### 4.2 Revised Status of All Deferred Findings

With Sprint 3 complete, the full initiative status is:

| ID | Finding | Original Score | Sprint | Outcome |
|----|---------|:-:|:---:|---------|
| AT2-003 | Freshness delta sequential added GID fetch | 57 | S1 | **SHIPPED** (parallelized via gather) |
| DRY-001 | Section extraction 4x duplication | 55 | S1 | **SHIPPED** (canonical wired) |
| AT2-005 | Lifecycle init sequential dep check | 42 | S1 | **NOT RECOMMENDED** (ADR-S1-001) |
| AT2-001 | DependencyShortcut sequential dep fetch | 65 | S2 | **NOT RECOMMENDED** (ADR-S2-001, score revised to 35) |
| AT3-002 | Resolution cross-context cache miss | 50 | S2 | **NOT RECOMMENDED** (ADR-S2-002, score revised to 17) |
| AT1-002 | ParallelSectionFetcher fetches ALL sections | 47 | S3 | **NOT RECOMMENDED** (ADR-S3-001, score revised to 1.8) |
| AT1-001 | ProgressiveBuilder fetches ALL sections | 53 | S3 | **NOT RECOMMENDED** (ADR-S3-002, score revised to 21) |
| AT2-004 | AssetEdit 3-hop chain walk | 42 | TBD | Deferred -- low frequency (10-20/day), needs Asana API experiment for `parent.parent.gid` opt_fields |

### 4.3 Remaining Work

**AT2-004** (score 42) is the only unaddressed finding. It requires an Asana API experiment to verify whether `opt_fields=["parent.parent.gid"]` works for nested parent references. This is a low-frequency path (10-20 AssetEdit operations per day) with 3 sequential API calls reducible to 1-2. Given the low frequency and experimental dependency, it should be addressed as a separate spike + implementation, not within this sprint cadence.

**Recommended disposition**: Defer AT2-004 to a future spike. Document the API experiment requirement in the deferred work roadmap.

**ParallelSectionFetcher cleanup**: The discovery that `ParallelSectionFetcher` has zero production callers should be logged as a structural quality finding for the deferred work roadmap. The class and its 700 lines of code (including caching infrastructure) are either:
- Vestigial infrastructure that should be removed
- Infrastructure that was never wired after being built, and should be evaluated for wiring or removal

This is NOT a runtime efficiency concern -- it is a dead code concern. It belongs in a hygiene pass, not this initiative.

### 4.4 Risk Assessment

| Item | Risk | Mitigation |
|------|------|------------|
| False negative on AT1-001 | If cold builds become more frequent (e.g., Lambda warming is disabled), the unfiltered section fetch becomes more costly | Monitor cold build frequency. If cold builds exceed 10% of total builds, revisit section filtering with a builder-level approach that does not break manifest compatibility. |
| ParallelSectionFetcher becomes wired | If future work wires ParallelSectionFetcher into a production path, section filtering should be reconsidered for that class | ADR-S3-001 documents the zero-caller finding. Any future wiring should evaluate filtering at that time. |
| Initiative ROI perception | 5 of 8 deferred findings declined after analysis. Only 2 shipped. | The initiative surfaced critical codebase knowledge: (a) resolution pipeline callers all use the business_gid fast path, (b) ParallelSectionFetcher is dead code, (c) the progressive builder's manifest system is incompatible with filtered section lists. These discoveries have architectural value beyond API call savings. |

---

## 5. Architecture Decision Records

### ADR-S3-001: Do Not Optimize ParallelSectionFetcher Section Filtering

**Status**: Accepted

**Context**:
AT1-002 identified that `ParallelSectionFetcher.fetch_all()` (lines 124-202 of `parallel_fetch.py`) fetches ALL sections without ACTIVE filtering. The smell report rated this MEDIUM severity with a score of 47, noting it is "shared infrastructure used by ProgressiveProjectBuilder."

**Decision**:
Do not add section filtering to `ParallelSectionFetcher`. The class has zero production instantiations and is not used by `ProgressiveProjectBuilder` or any other production code path.

**Alternatives Considered**:

**Option A: Add optional `section_filter` parameter to `fetch_all()`**
- Pros: Clean API extension; backward-compatible (optional parameter defaults to None)
- Cons: Optimizes dead code; no production runtime improvement; increases maintenance burden on unused infrastructure

**Option B: Optimize now for future use**
- Pros: Ready when/if the class is wired into a production path
- Cons: YAGNI; the class may be removed rather than wired; investment in speculative optimization

**Option C: Do nothing (chosen)**
- Pros: No code change, no regression risk, no maintenance of dead optimization paths
- Cons: If the class is later wired without filtering, the optimization opportunity is deferred

**Rationale**:
1. **Zero production instantiations**: A comprehensive grep of `ParallelSectionFetcher(` across the entire `src/` tree returns zero production construction sites. The class is re-exported from `builders/__init__.py` and tested in `tests/unit/dataframes/test_parallel_fetch.py`, but never used.
2. **The SMELL report's dependency claim is incorrect**: `ProgressiveProjectBuilder` does NOT delegate to `ParallelSectionFetcher`. The progressive builder has its own `_list_sections()` method that calls `self._client.sections.list_for_project_async()` directly. There is no import of `parallel_fetch` in `progressive.py`.
3. **Revised score of 1.8 is below any action threshold**: With zero API calls saved and zero execution frequency, the finding's value is effectively zero.
4. **The class may be vestigial**: `ParallelSectionFetcher` appears to predate `ProgressiveProjectBuilder`, which absorbed its parallel fetch functionality while adding resume, manifest, and S3 persistence capabilities.

**Consequences**:

Positive:
- No regression risk
- No maintenance of unused optimization code
- Discovery documented for future structural cleanup

Negative:
- If `ParallelSectionFetcher` is wired into a production path in the future, it will fetch all sections without ACTIVE filtering. This is a known, accepted trade-off that should be revisited at wiring time.

Neutral:
- The zero-caller finding should be added to the deferred work roadmap as a structural quality item (dead code candidate)

---

### ADR-S3-002: Do Not Add Section Filtering to ProgressiveProjectBuilder

**Status**: Accepted

**Context**:
AT1-001 identified that `ProgressiveProjectBuilder._list_sections()` (line 562 of `progressive.py`) fetches ALL sections without ACTIVE filtering. The smell report rated this MEDIUM severity with a score of 53, noting that for Offer projects, 12 of 36 sections are non-ACTIVE, and for Unit projects, 11 of 14 sections are non-ACTIVE. The SMELL report stated this was "blocked by AT1-002" due to delegation to `ParallelSectionFetcher`, which was found to be incorrect.

**Decision**:
Do not add section classifier filtering to `ProgressiveProjectBuilder`. The manifest/resume system is incompatible with filtered section lists, the savings apply only to the rare cold-build path, and the builder serves as shared data infrastructure where completeness is more important than per-section selectivity.

**Alternatives Considered**:

**Option A: Add `section_classifier: SectionClassifier | None = None` constructor parameter**
- Filter `_list_sections()` results to ACTIVE-only when classifier is provided
- Pros: Backward-compatible; opt-in filtering; 12-11 fewer section fetches on cold builds
- Cons: Manifest incompatibility (manifests track section GIDs; changing the section list creates mismatches with existing manifests); 8+ caller sites must be evaluated for correct classifier injection; consumers expecting complete data (all sections) would silently receive incomplete DataFrames; savings apply only to cold builds (rare production path)

**Option B: Filter at the caller level after listing**
- Progressive builder lists ALL sections; callers filter before passing to the builder
- Pros: Builder stays complete; filtering is explicit at the call site
- Cons: The builder's `build_progressive_async()` is the entry point -- there is no intermediate step where the caller provides a section list. The builder calls its own `_list_sections()` internally. Implementing this would require a new `section_gids: list[str] | None = None` parameter on `build_progressive_async()`, which changes the public API of the most widely-used builder method.

**Option C: Filter only for observability (log skipped sections) but still fetch all**
- Pros: No behavioral change; observability into potential savings
- Cons: Additional complexity for zero runtime benefit; logging non-ACTIVE section counts without acting on them adds noise

**Option D: Do nothing (chosen)**
- Pros: No manifest incompatibility; no blast radius across 8+ callers; complete DataFrames for all consumers; no risk of missing data for historical/analytical queries
- Cons: 12 extra section fetches for Offer and 11 for Unit on cold builds

**Rationale**:
1. **Manifest incompatibility is a one-way door**: The manifest system tracks section GIDs and uses them for resume, freshness probing, and completion tracking. Changing the section list without manifest migration creates inconsistencies that are hard to diagnose and recover from.
2. **Cold builds are the least common path**: The preload system primarily uses S3 parquet (pre-warmed by Lambda) or resumes from existing manifests. Cold builds occur on first deployment or manifest corruption -- not the steady-state path.
3. **Savings are moderate**: 12 section fetches at ~100-300ms each = 1.2-3.6 seconds saved on a 30-60 second cold build. This is 4-12% improvement on the rare path.
4. **The builder is data infrastructure, not business logic**: `ProgressiveProjectBuilder` serves 8+ callers with different data needs. Some need complete section data for analytics. Embedding classification logic (which sections are "important") into the builder conflates infrastructure and business concerns.
5. **The proven pattern works at the workflow layer**: `insights_export.py` and `pipeline_transition.py` demonstrate that section-targeted fetch is best done at the workflow level where the specific data requirements are known. The builder's job is to provide a complete, cached DataFrame that workflows query against.
6. **Revised score of 21 is below the 40 threshold**: The combination of rare-path savings, manifest incompatibility, and high blast radius makes this finding non-actionable under PROMPT-0's scoring framework.

**Consequences**:

Positive:
- Manifest system integrity preserved
- All 8+ callers continue to receive complete DataFrames
- No risk of incomplete data for analytical consumers
- No blast radius across caller sites

Negative:
- Cold builds for Offer and Unit projects continue to fetch all sections including non-ACTIVE ones
- If cold build frequency increases, the savings gap widens

Neutral:
- If a future "lightweight build" mode is needed (e.g., for a new caller that explicitly wants only ACTIVE sections), a new builder method or parameter can be added at that time with manifest awareness built in from the start
- The classifier infrastructure (`get_classifier()`, `SectionClassifier.sections_for()`) is ready and tested whenever filtering becomes justified at the builder layer

---

## 6. Principal-Engineer Notes

This sprint produces ADRs only, not code changes. No implementation, no test changes, no commits.

### Key Codebase Knowledge Gained

1. **`ParallelSectionFetcher` has zero production callers**: It is exported and tested but never instantiated in production. This is a dead code candidate for the deferred work roadmap.

2. **`ProgressiveProjectBuilder` is the sole production builder**: All 8+ DataFrame construction sites use it. Changes to its behavior affect every preload, cache warming, user query, and admin rebuild path.

3. **The manifest system creates coupling between section lists and persistence state**: Any change to which sections are tracked requires manifest migration or versioning. This is a structural constraint that must be respected in any future section filtering work.

4. **Section-targeted optimization is proven at the workflow layer**: `insights_export.py` and `pipeline_transition.py` demonstrate the correct pattern: resolve target section GIDs, fetch per-section with bounded concurrency, fall back to project-level fetch on failure. This pattern does NOT go through the builder -- it operates directly against the Asana API client.

5. **Classifier lookup is ready**: `get_classifier(entity_type)` at `activity.py:268` returns `SectionClassifier | None`. It returns classifiers for "offer" and "unit" only. All other entity types return `None`.

### No Test Changes Required

Since no code changes are being made, the test baseline (>= 8781) is unaffected.

---

## 7. Attestation

| Source Artifact | Verified Via | Findings |
|-----------------|-------------|----------|
| `src/autom8_asana/dataframes/builders/parallel_fetch.py` | Read tool (full file) | Lines 85-700: `ParallelSectionFetcher` class with `fetch_all()`, `_list_sections()`, caching, dedup. No production callers. |
| `src/autom8_asana/dataframes/builders/progressive.py` | Read tool (full file) | Lines 562-567: Independent `_list_sections()`. No import of `parallel_fetch`. Lines 381-547: `build_progressive_async()` with manifest/resume/freshness logic. |
| `src/autom8_asana/dataframes/builders/__init__.py` | Read tool (full file) | Lines 55-59: `ParallelSectionFetcher` re-exported but never used in production. |
| `src/autom8_asana/models/business/activity.py` | Read tool (full file) | Lines 185-231: `OFFER_CLASSIFIER` (36 sections, 24 ACTIVE). Lines 233-259: `UNIT_CLASSIFIER` (14 sections, 3 ACTIVE). Lines 262-277: `CLASSIFIERS` dict and `get_classifier()`. |
| `src/autom8_asana/models/project.py` | Read tool (lines 200-340) | Lines 216-226, 310-321: Two `ProgressiveProjectBuilder` instantiation sites. Neither uses `ParallelSectionFetcher`. |
| `src/autom8_asana/services/universal_strategy.py` | Read tool (lines 590-630) | Lines 603-613: `ProgressiveProjectBuilder` instantiation. No `ParallelSectionFetcher`. |
| `src/autom8_asana/cache/dataframe/factory.py` | Read tool (lines 60-100) | Lines 73-82: `ProgressiveProjectBuilder` instantiation. No `ParallelSectionFetcher`. |
| `src/autom8_asana/api/preload/progressive.py` | Read tool (lines 270-400) | Lines 293-384: `ProgressiveProjectBuilder` instantiation. No `ParallelSectionFetcher`. |
| `src/autom8_asana/automation/workflows/section_resolution.py` | Read tool (full file) | Lines 19-64: `resolve_section_gids()` -- the proven section-targeted pattern. Works at workflow layer, not builder layer. |
| `src/autom8_asana/automation/workflows/insights_export.py` | Read tool (lines 270-320) | Lines 277-319: Section-targeted fetch using `resolve_section_gids()` + `OFFER_CLASSIFIER`. Reference pattern that works at workflow layer. |
| Grep: `ParallelSectionFetcher(` in `src/` | Grep tool | Returns 1 match: class definition only. Zero production instantiations. |
| Grep: `from.*parallel_fetch.*import` in `src/` | Grep tool | Returns 1 match: `builders/__init__.py` re-export only. |
| Grep: `ProgressiveProjectBuilder(` in `src/` | Grep tool | Returns 8+ matches across models, services, cache, preload, admin routes. |
| SMELL report (`SMELL-runtime-efficiency-audit.md`) | Read tool (full file) | AT1-001 and AT1-002 findings confirmed. Dependency claim ("AT1-001 delegates to ParallelSectionFetcher") found to be incorrect. |
| PROMPT-0 (`PROMPT-0-runtime-remediation.md`) | Read tool (full file) | Section 2 dependency notes: "AT1-001 is blocked by AT1-002" -- incorrect per codebase analysis. Anti-patterns confirmed: "Do not break the ParallelSectionFetcher contract carelessly." |
| Prior TDD S1 | Read tool (full file) | Format and conventions used as template. Sprint 1 shipped AT2-003 and DRY-001. |
| Prior TDD S2 | Read tool (full file) | Sprint 2 declined AT2-001 and AT3-002 with ADRs. |

---

## Handoff Checklist

- [x] AT1-002 analyzed: zero production callers discovered; NOT RECOMMENDED (score 1.8)
- [x] AT1-001 analyzed: manifest incompatibility, rare-path savings, high blast radius; NOT RECOMMENDED (score 21)
- [x] Critical discovery documented: ParallelSectionFetcher has zero production instantiations
- [x] Critical discovery documented: ProgressiveProjectBuilder does NOT delegate to ParallelSectionFetcher
- [x] SMELL report dependency claim corrected (AT1-001 is NOT blocked by AT1-002)
- [x] ADR-S3-001 captures ParallelSectionFetcher analysis and decision
- [x] ADR-S3-002 captures ProgressiveProjectBuilder analysis and decision
- [x] All alternatives evaluated with explicit pros/cons
- [x] Re-scoring uses PROMPT-0 dimensions with revised evidence
- [x] Full initiative status table with all 8 findings and their dispositions
- [x] Risk assessment identifies monitoring points for both decisions
- [x] AT2-004 disposition documented (defer to spike)
- [x] ParallelSectionFetcher dead code finding flagged for deferred work roadmap
- [x] All source artifacts verified via Read/Grep tools with attestation table
