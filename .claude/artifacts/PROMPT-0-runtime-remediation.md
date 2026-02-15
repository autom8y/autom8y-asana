# PROMPT-0: Runtime Efficiency Remediation

```yaml
id: INIT-RUNTIME-REM-001
rite: 10x-dev
complexity: REMEDIATION
upstream: INIT-RUNTIME-EFF-001 (hygiene, completed)
test_baseline: 8781 passed
date: 2026-02-15
```

---

## Executive Summary

A completed hygiene audit (INIT-RUNTIME-EFF-001) identified 11 runtime efficiency findings across the codebase. Three high-scoring fixes were shipped. Eight findings scored 40-69 and were deferred -- they require design decisions, contract changes, or new infrastructure that exceed hygiene scope. This initiative picks up those 8 deferred findings as optimization work under the 10x-dev rite.

**What shipped (DO NOT re-do):**

| ID | Fix | Commit | Score |
|----|-----|--------|:-----:|
| BUG-001 | TTL constant fix in `sections.py` | `fix(clients)` | 71 |
| AT2-002 | Hierarchy traversal double-fetch elimination in `strategies.py` | `perf(resolution)` | 73 |
| AT3-001 | Business dedup cache in `insights_export.py` | `perf(workflows)` | 83 |

**What remains (this initiative's scope):**

8 deferred findings, detailed in Section 2 below.

---

## 1. Objective

Reduce redundant Asana API calls and eliminate structural inefficiencies identified by the upstream audit, while preserving all existing behavioral contracts and maintaining zero test regressions.

**Success looks like:**
- Each addressed finding reduces API calls or eliminates structural waste (measurable via logging)
- Every optimization has a fallback path to the original behavior
- No public API or contract changes unless explicitly designed and approved
- Test baseline holds at >= 8781 passed

**This is NOT:**
- A greenfield optimization project -- the audit is done, findings are cataloged
- A codebase-wide performance initiative -- scope is limited to the 8 cataloged findings
- A hygiene pass -- the DRY and correctness items here have design implications

---

## 2. Deferred Findings (Work Scope)

Sorted by original weighted score. The orchestrator may re-sequence based on dependencies, risk, or strategic value.

| ID | Finding | Score | Category | Key Constraint |
|----|---------|:-----:|----------|----------------|
| AT2-001 | DependencyShortcut sequential dep fetch (`strategies.py:140-172`) | 65 | N+1 | Parallelization changes first-match ordering semantics; budget consumption semantics need verification |
| AT2-003 | Freshness delta sequential added GID fetch (`freshness.py:340-346`) | 57 | N+1 | Typically small N; simple gather batching with `return_exceptions=True` |
| DRY-001 | Section extraction 4x duplication (`activity.py:138` + 3 locations) | 55 | DRY | Dict vs Task model divergence; orphaned canonical exists but needs protocol or overload |
| AT1-001 | ProgressiveBuilder fetches ALL sections (`progressive.py:562-567`) | 53 | Section targeting | Needs classifier injection into builder; blocked by AT1-002 |
| AT3-002 | Resolution cross-context cache miss (`strategies.py:244-248`) | 50 | Dedup cache | Needs shared cache infra with lifecycle management; session isolation is intentional |
| AT1-002 | ParallelSectionFetcher fetches ALL sections (`parallel_fetch.py:144,164`) | 47 | Section targeting | Contract change on shared infrastructure; multiple callers |
| AT2-004 | AssetEdit 3-hop chain walk (`asset_edit.py:645-663`) | 42 | N+1 | Low frequency (10-20/day); Asana nested `opt_fields` support for `parent.parent.gid` not verified |
| AT2-005 | Lifecycle init sequential dep check (`init_actions.py:199-204`) | 42 | N+1 | Low frequency (5-15/day); bounded by early return |

### Dependency Notes

- **AT1-001 is blocked by AT1-002**: Progressive builder delegates to ParallelSectionFetcher. Fix the shared infra first.
- **AT2-001 and AT3-002 share the resolution pipeline**: Both touch `strategies.py`. Consider whether a shared resolution cache (AT3-002) changes the value calculation for parallelizing dependency fetch (AT2-001).
- **DRY-001 is independent**: Touches 4 files across 3 packages but has no runtime dependency on other findings.
- **AT2-004 requires an Asana API experiment**: Verify whether `opt_fields=["parent.parent.gid"]` works before committing to an approach.

---

## 3. Proven Patterns (Reuse These)

The upstream initiative established patterns already in the codebase. Specialists should study these as reference implementations, not re-invent.

| Pattern | Reference Implementation | What It Does |
|---------|------------------------|--------------|
| Section-targeted fetch | `automation/workflows/insights_export.py:299`, `pipeline_transition.py:302` | Resolve section GIDs via `section_resolution.py`, parallel fetch per section, dedup by GID, project-level fallback on failure |
| Bulk pre-resolution | `automation/workflows/conversation_audit.py:272` | Extract unique GIDs, Semaphore(8) parallel resolve, instance-level `_activity_map` dedup cache, pre-filter before processing |
| Dedup cache | `conversation_audit.py:83` (`_activity_map`), `insights_export.py` (`_business_cache` -- just shipped) | `dict[gid, result]` at instance level, per-execution lifetime, no TTL needed |
| Section resolution | `automation/workflows/section_resolution.py` | `resolve_section_gids(sections_client, project_gid, target_names)` -- case-insensitive, logs warnings for missing sections |
| Classifier filtering | `models/business/activity.py` | `OFFER_CLASSIFIER` (24 ACTIVE of 36), `UNIT_CLASSIFIER` (3 ACTIVE of 14), `SectionClassifier` with `AccountActivity` enum |

---

## 4. Constraints and Anti-Patterns

### Hard Constraints

1. **Every optimization MUST have a fallback** -- if the optimized path fails, fall back to the original behavior verbatim
2. **Every optimization MUST log savings** -- total items, filtered items, cache hits, API calls saved
3. **Every optimization MUST preserve test compatibility** -- no public API signature changes without explicit design approval
4. **Concurrency limits**: Semaphore(5) for processing, Semaphore(8) for resolution/enumeration
5. **No new modules** unless architecturally justified -- prefer adding methods/attributes to existing classes
6. **Zero test regressions** -- baseline is 8781 passed

### Anti-Patterns (DO NOT)

- **Do not optimize fallback paths** -- fallbacks exist for resilience, not performance
- **Do not add section-targeted fetch where there's no classifier** -- only Offer and Unit projects have classifiers; ContactHolder is not viable (see `docs/spikes/SPIKE-contact-holder-section-mapping.md`)
- **Do not break the `ParallelSectionFetcher` contract carelessly** -- it is shared infrastructure used by multiple callers
- **Do not remove project-level fetch entirely** -- always keep it as fallback
- **Do not over-cache** -- session-level dedup (per-execution) is cheap and safe; persistent caching needs TTL, invalidation strategy, and lifecycle management
- **Do not change resolution ordering semantics without analysis** -- `DependencyShortcutStrategy` returns first match; parallelizing with `gather` changes this to any-match

### Test Command

```bash
.venv/bin/pytest tests/unit/ --ignore=tests/unit/api/ -x -q --timeout=60
# Expected: >= 8781 passed
```

Pre-existing failures (not ours): `test_adversarial_pacing.py`, `test_paced_fetch.py` (checkpoint assertions), `test_parallel_fetch.py::test_cache_errors_logged_as_warnings` (caplog vs structured logging).

---

## 5. Upstream Artifacts (Load On-Demand)

These contain the full evidence, code snippets, and analysis. Specialists should read them when working on specific findings.

| Artifact | Path | Contents |
|----------|------|----------|
| Smell report | `docs/hygiene/SMELL-runtime-efficiency-audit.md` | 11 findings with code evidence, blast radius analysis, severity ratings, caller context |
| TDD / Refactoring plan | `docs/hygiene/TDD-runtime-efficiency-audit.md` | Scoring derivation, before/after contracts for shipped fixes, sequencing rationale, deferral reasons |
| Original PROMPT-0 | `.claude/artifacts/PROMPT-0-runtime-efficiency-audit.md` | Audit methodology, pattern definitions, file index, key file locations |
| Deferred work roadmap | `.claude/artifacts/deferred-work-roadmap.md` | 7 initiatives across 4 waves (this initiative is a companion, not part of that roadmap) |
| Contact holder spike | `docs/spikes/SPIKE-contact-holder-section-mapping.md` | Why ContactHolder is not viable for section-targeted fetch |
| Activity gap analysis | `docs/spikes/SPIKE-workflow-activity-gap-analysis.md` | Phantom method bug (fixed), orphaned module (wired), 4x section extraction duplication |

---

## 6. Key File Index

### Resolution Pipeline (AT2-001, AT3-002)
| File | Relevant Lines |
|------|---------------|
| `src/autom8_asana/resolution/strategies.py` | :140-172 (DependencyShortcut), :244-284 (HierarchyTraversal -- already fixed) |
| `src/autom8_asana/resolution/context.py` | :74, :86-88 (`_session_cache`, cleared on `__aexit__`) |

### Dataframe Builders (AT1-001, AT1-002, AT2-003)
| File | Relevant Lines |
|------|---------------|
| `src/autom8_asana/dataframes/builders/progressive.py` | :454-466 (section iteration), :562-567 (`_list_sections`) |
| `src/autom8_asana/dataframes/builders/parallel_fetch.py` | :144,164 (`fetch_all`), :204-226 (`_list_sections`) |
| `src/autom8_asana/dataframes/builders/freshness.py` | :340-346 (sequential added GID fetch) |

### Section Extraction DRY (DRY-001)
| File | Notes |
|------|-------|
| `src/autom8_asana/models/business/activity.py:138-171` | Canonical `extract_section_name()` -- orphaned, never called |
| `src/autom8_asana/dataframes/extractors/base.py:488-521` | Duplicate (operates on Task model) |
| `src/autom8_asana/dataframes/views/dataframe_view.py:835-870` | Duplicate (operates on dict, missing `isinstance(str)` check) |
| `src/autom8_asana/models/business/process.py:414-430` | Simplified variant returning `ProcessSection` enum |

### Low-Frequency Paths (AT2-004, AT2-005)
| File | Relevant Lines |
|------|---------------|
| `src/autom8_asana/models/business/asset_edit.py` | :645-663 (3-hop chain walk) |
| `src/autom8_asana/lifecycle/init_actions.py` | :199-204 (sequential dep check with early return) |

### Classifiers
| File | What |
|------|------|
| `src/autom8_asana/models/business/activity.py` | `OFFER_CLASSIFIER` (36 sections, 24 ACTIVE), `UNIT_CLASSIFIER` (14 sections, 3 ACTIVE) |

---

## 7. Scoring Context

The original scoring used these weights. The orchestrator may adjust weighting for the 10x-dev context (e.g., weighting implementation complexity higher now that design work is expected).

| Dimension | Weight | Scale |
|-----------|--------|-------|
| API calls saved per execution | 40% | High (8-10), Medium (5-7), Low (1-4) |
| Execution frequency | 30% | High (8-10: daily+), Medium (5-7: per-event), Low (1-4: rare) |
| Implementation complexity | 20% | Easy reuse (8-10), Moderate adaptation (5-7), New infra (1-4) |
| Risk | 10% | Low blast radius (8-10), Medium (5-7), High (1-4) |

The orchestrator is free to re-score, re-phase, or defer findings further based on new information discovered during design. Findings scoring below 40 after re-analysis should be documented and deferred rather than forced.

---

## 8. Session Boundary Notes

This PROMPT-0 is a **cross-session handoff** from a completed hygiene initiative. Key context that must not be lost:

1. **The audit is complete** -- all `list_async(project=...)` and `get_async` calls in the codebase have been classified. No further audit sweep is needed.
2. **Three fixes are shipped and committed** -- do not re-analyze BUG-001, AT2-002, or AT3-001.
3. **The test baseline advanced** from 8588 to 8781 during the upstream initiative and the entity resolution hardening that preceded it.
4. **The deferred-work-roadmap** (`.claude/artifacts/deferred-work-roadmap.md`) is a separate initiative covering structural quality. This runtime remediation is a companion that can run in parallel -- it touches different files.
5. **DRY-001's canonical function exists but is orphaned** -- `activity.py:138` was written during a spike but never wired. The spike documented this at `docs/spikes/SPIKE-workflow-activity-gap-analysis.md`.
