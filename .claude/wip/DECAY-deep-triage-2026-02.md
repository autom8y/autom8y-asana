# Decay Report — Deep Slop Triage

Date: 2026-02-19
Scope: Full Codebase (`src/autom8y_asana/`)
Agent: cruft-cutter
Rite: slop-chop (MODULE complexity)

---

## Executive Summary

| Category | Finding Count | Provably Stale | Probably Stale |
|----------|--------------|----------------|----------------|
| Dead shims / compatibility code | 3 | 2 | 1 |
| Stale feature flags | 1 | 0 | 1 |
| Ephemeral comment artifacts | 7 | 3 | 4 |
| Deprecation cruft | 5 | 2 | 3 |
| Debt ledger cross-reference | 1 | 1 | 0 |
| **Total** | **17** | **8** | **9** |

All findings are ADVISORY. Temporal debt never blocks the quality gate.

**NOT flagged (intentional design):**
- `api/preload/legacy.py` — ADR-011 active degraded-mode fallback
- Cache divergence — ADR-0067 intentional
- SaveSession coordinator pattern — not a god object

---

## Dead Shims & Compatibility Code

### CC-001: `pipeline_templates` legacy shim in AutomationConfig (provably stale)

**File**: `src/autom8_asana/automation/config.py:144-181`
**Finding**: `pipeline_templates: dict[str, str]` field and its fallback path in `get_pipeline_stage()` are documented as legacy. The preferred `pipeline_stages: dict[str, PipelineStage]` field now takes precedence.
**Evidence**: The docstring at line 112 explicitly labels `pipeline_templates` as "ProcessType to target project GID mapping (legacy)." The fallback logic at lines 179-181 reads:
```python
# Fall back to pipeline_templates (legacy)
if process_type in self.pipeline_templates:
    return PipelineStage(project_gid=self.pipeline_templates[process_type])
```
`git blame` shows this shim dates to 2025-12-22 (commit `94faac00`). The migration path (`pipeline_stages`) is already built and documented. The example in `config.py:627` already uses the modern form. No external callers passing `pipeline_templates` were found in the source tree.
**Tier**: Provably stale — superseded by `pipeline_stages`, no removal date or owner on the shim.
**Caller analysis**: 8 references in source; all are the field definition, docstring, fallback path, and test example. No production caller was found passing `pipeline_templates` in preference over `pipeline_stages`.
**Severity**: TEMPORAL (advisory)

---

### CC-002: `autom8y_cache` defensive import guard in `cache/__init__.py` and `cache/models/freshness.py` (probably stale)

**Files**:
- `src/autom8_asana/cache/__init__.py:170-175`
- `src/autom8_asana/cache/models/freshness.py:13-25`

**Finding**: Both files contain `HOTFIX` guards that wrap `from autom8y_cache import ...` in a try/except ImportError, with fallbacks to local enum definitions. Comments read:
```python
# HOTFIX: Make import defensive for Lambda compatibility when autom8y_cache
# has missing modules (e.g., protocols.resolver in version mismatch scenarios)
```
**Evidence**: `git blame` shows both guards added on 2026-01-08 (commit `d64285cf`). The lockfile now pins `autom8y_cache==0.4.0`. The hotfix rationale was a version mismatch between what was installed in Lambda and the pinned SDK. The lockfile is now fixed at 0.4.0 and the mismatch scenario the hotfix guarded against cannot occur with a pinned lockfile. Runtime import from the project's local dev environment also fails (`ModuleNotFoundError: No module named 'autom8y_cache'`), confirming the package is only available in the Lambda/production environment — meaning the fallback path is exercised in local dev, which is a different concern.
**Escalation note**: Whether `autom8y_cache==0.4.0` contains `protocols.resolver` (the specific sub-module cited) cannot be verified without inspecting the package. If the version mismatch was resolved by pinning 0.4.0 and that version contains the module, the guards are dead. If the guard is still needed for local dev compatibility, it is not temporal debt but a genuine defensive pattern.
**Tier**: Probably stale — hotfix from 2026-01-08, lockfile now pinned, mismatch scenario may be resolved.
**Severity**: TEMPORAL (advisory)

---

### CC-003: `HierarchyTracker` fallback to `None` in `cache/__init__.py` (probably stale)

**File**: `src/autom8_asana/cache/__init__.py:172-175`
**Finding**: Same HOTFIX guard as CC-002, but for `HierarchyTracker`:
```python
try:
    from autom8y_cache import HierarchyTracker
except ImportError:
    HierarchyTracker = None  # type: ignore[misc, assignment]
```
**Evidence**: Same commit as CC-002 (2026-01-08, `d64285cf`). If `HierarchyTracker` is exported at None, any caller doing `if HierarchyTracker is not None` is dead-branched, but callers that attempt `HierarchyTracker(...)` directly would fail at runtime. The caller surface for `HierarchyTracker` is limited to advanced use cases per docstring.
**Tier**: Probably stale — same rationale as CC-002.
**Severity**: TEMPORAL (advisory)

---

## Stale Feature Flags

### CC-004: `AUTOM8_DATA_INSIGHTS_ENABLED` emergency kill switch (probably stale)

**File**: `src/autom8_asana/clients/data/client.py:473-499`
**Finding**: A `_check_feature_enabled()` method acts as an emergency kill switch via env var `AUTOM8_DATA_INSIGHTS_ENABLED`. The docstring evolution is revealing:
```
Per Story 1.7: Feature flag control for insights integration.
Per Story 2.7: Feature is now enabled by default.
Per Story 3.6: Retained as emergency kill switch (not for A/B testing).
```
The progression shows: originally a gate for a new feature, graduated to always-on default, but the flag infrastructure was not retired — it was repurposed as an emergency kill switch.
**Evidence**: No evidence found that the kill switch has ever been activated in git history. The feature has been enabled by default since Story 2.7. The flag exists in Settings as `insights_enabled` with `default=True`. The "emergency" justification is operational, not temporal — the question is whether runtime data shows this has been used. Cannot determine without production metrics.
**Escalation**: Requires production deployment telemetry to confirm the flag has never been set to `false` in any environment. If it has never been triggered, it qualifies as a dead feature gate. Externally controlled via env var — needs operator input.
**Tier**: Probably stale — default-always-on since Story 2.7, no evidence of activation, but emergency justification cannot be fully dismissed without runtime data.
**Severity**: TEMPORAL (advisory)

---

## Ephemeral Comment Artifacts

### CC-005: MVP-deferred TODO stubs in `UnitExtractor` — open-ended implementation deferral (probably stale)

**File**: `src/autom8_asana/dataframes/extractors/unit.py:66-118`
**Finding**: Two stub methods with explicit TODO comments:
```python
# Per MVP Note: Return None with TODO comments pending business logic input
# TODO: Implement vertical_id derivation from Vertical model
# TODO: Implement max_pipeline_stage derivation from UnitHolder
```
Both methods always return `None`. If these columns appear in schemas, they silently contain `None` for every row.
**Evidence**: `git blame` shows the "MVP Note" comment at line 66 dates to 2025-12-10 (commit `60957094`, over 70 days ago). The TODO at line 87 was touched 2026-02-07 (commit `7febdcae`) but only to add docstring text, not to implement. No ticket reference or owner. The comment "deferred pending autom8 team input" has no resolution signal.
**Type**: Resolved-condition TODO — the MVP has shipped (project is in active sprint 5+ of cleanup), but the business logic input was never received and no follow-up was filed.
**Tier**: Probably stale — 70+ days since initial deferral, no resolution signal, MVP context has passed.
**Severity**: TEMPORAL (advisory)

---

### CC-006: `metrics/definitions/__init__.py` commented-out future imports (probably stale)

**File**: `src/autom8_asana/metrics/definitions/__init__.py:13-15`
**Finding**:
```python
# Future definition modules:
# from autom8_asana.metrics.definitions import unit  # noqa: F401
# from autom8_asana.metrics.definitions import business  # noqa: F401
```
**Evidence**: `git blame` shows this file has only one commit (`6e6d344`, "feat(metrics): add composable metrics layer (Phase 1)"). The "Phase 1" label suggests Phase 2 would implement `unit` and `business` metrics — but no subsequent phase commit exists. No ticket reference. The commented imports have never resolved to actual modules.
**Type**: Initiative tag — "Phase 1" implies future phases that have not materialized.
**Tier**: Probably stale — Phase 2 never commenced, no removal date or owner.
**Severity**: TEMPORAL (advisory)

---

### CC-007: `HOTFIX` narrative comments in `cache_warmer.py` describing a resolved import chain failure (provably stale)

**File**: `src/autom8_asana/lambda_handlers/cache_warmer.py:55-68`
**Finding**: The `_ensure_bootstrap()` function docstring reads:
```
HOTFIX: Moved from module-level import to avoid import chain failures
when autom8y_cache has missing modules.
```
Three separate HOTFIX comments (lines 58, 829, 902) reference the same resolved incident.
**Evidence**: `git blame` dates all three to 2026-01-08 (commit `d64285cf`). The `uv.lock` now pins `autom8y_cache==0.4.0`. The architectural problem (import chain failure) was resolved by converting to lazy initialization. The function itself is correct and non-temporal. The HOTFIX label, however, is an ephemeral incident marker that belongs in the commit message (which it is, in `d64285cf`), not in the source docstring.
**Type**: Architecture ghost comment — describes a system state (broken import chain) that no longer exists, using the temporal marker "HOTFIX" to denote an emergency fix that has been normalized.
**Tier**: Provably stale — the HOTFIX architectural condition is resolved; the function's lazy initialization pattern is now the intended design.
**Severity**: TEMPORAL (advisory)

---

### CC-008: `SPIKE-BREAK-CIRCULAR-DEP` references in `gid_push.py` and `cache_warmer.py` (provably stale)

**Files**:
- `src/autom8_asana/services/gid_push.py:3-8` (module docstring)
- `src/autom8_asana/lambda_handlers/cache_warmer.py:243,712`

**Finding**: The module docstring for `gid_push.py` reads:
```
Per SPIKE-BREAK-CIRCULAR-DEP Phase 3: After the cache warmer rebuilds
GID indexes, push the mapping snapshot to autom8_data's sync endpoint
```
And `cache_warmer.py:712` contains a comment: `# GID mapping push (Phase 3: SPIKE-BREAK-CIRCULAR-DEP)`.
**Evidence**: The feature (`gid_push.py`) was merged 2026-02-16 and is functioning production code. "SPIKE-BREAK-CIRCULAR-DEP" was an internal investigation spike whose Phase 3 produced this module. The spike has concluded; Phase 3 is shipped. The "Per SPIKE-BREAK-CIRCULAR-DEP Phase 3" reference in the module docstring is an initiative tag referencing a completed investigation. It belongs in the commit message, not in the module-level documentation.
**Type**: Initiative tag — references a completed spike/investigation phase.
**Tier**: Provably stale — the spike investigation is complete, the feature is shipped, the phase reference serves no current navigational purpose.
**Severity**: TEMPORAL (advisory)

---

### CC-009: `Migration Note (SDK-PRIMITIVES-001)` in `cache/models/freshness.py` (probably stale)

**File**: `src/autom8_asana/cache/models/freshness.py:1-7`
**Finding**: The module docstring is entirely a migration note:
```
Migration Note (SDK-PRIMITIVES-001):
    This module now re-exports autom8y_cache.Freshness which includes
    IMMEDIATE mode in addition to STRICT and EVENTUAL. The local enum
    is deprecated in favor of the SDK version.
```
**Evidence**: `git blame` shows this note added 2026-01-04 (commit `6c2c4b85`). The migration to `autom8y_cache.Freshness` is complete — the re-export is the implementation. The module docstring describes a migration that happened, not a migration that is in progress. This is a "migration stub" — a note that was accurate during the migration window but has outlived it.
**Type**: Migration stub — the migration is complete, the note describes a completed transition.
**Tier**: Probably stale — migration completed ~46 days ago; no "keep until" marker. Cannot confirm whether all consumers have been updated (requires caller audit).
**Severity**: TEMPORAL (advisory)

---

### CC-010: `Story X.Y` references as inline ticket citations in `clients/data/` modules (probably stale)

**Files**: Multiple files in `src/autom8_asana/clients/data/`
- `client.py:3-9` (module docstring: "Per Story 1.7", "Per Story 2.7", "Per Story 3.6", "Per Story 1.8", "Per Story 1.9")
- `_endpoints/insights.py:36-41`
- `__init__.py:22,24` ("per Story 1.5", "per Story 1.3")
- `models.py:135,155,197,242,283`

**Finding**: Dozens of inline `Per Story X.Y` references throughout the `clients/data/` module tree. Stories are work-item ticket references (presumably from a sprint planning system) that describe what motivated each implementation detail. Examples:
```python
# Per Story 1.7: Feature flag control for insights integration.
# Per Story 2.7: Feature is now enabled by default.
# Per Story 3.6: Retained as emergency kill switch (not for A/B testing).
# per Story 1.5
# per Story 1.3
```
**Evidence**: These are ticket references baked into source code. The stories have shipped — the code exists. The references belong in commit messages (which is where ADR and ticket references are tracked across the rest of this codebase). The `clients/data/` module was built as a self-contained story-driven initiative and inherited the habit of citing story numbers inline. No resolution date. Estimated 30+ inline story references across the `clients/data/` tree.
**Type**: Ticket reference — story identifiers embedded in source, not in commit messages.
**Tier**: Probably stale — the stories are completed; the code is shipped.
**Severity**: TEMPORAL (advisory)

---

### CC-011: `Per TDD-INSIGHTS-001` and `Per Story` references in `clients/data/__init__.py` comments (probably stale)

**File**: `src/autom8_asana/clients/data/__init__.py:3`
**Finding**: Module docstring:
```
Per TDD-INSIGHTS-001: Client and models for fetching analytics insights.
```
And inline comments in `__all__`:
```python
# Client class (per Story 1.5)
# Config classes (per Story 1.3)
```
**Evidence**: Same class of artifact as CC-010. The TDD document `TDD-INSIGHTS-001` was the design specification for the initial insights integration. The integration shipped. Comments in `__all__` that cite story numbers serve no ongoing navigational purpose. `__all__` member grouping comments should describe the logical grouping, not the historical ticket that drove the addition.
**Type**: Ticket reference / initiative tag in `__all__` grouping.
**Tier**: Probably stale — initiative completed.
**Severity**: TEMPORAL (advisory)

---

## Deprecation Cruft

### CC-012: `get_custom_fields()` deprecated method — 39 active call sites (provably stale)

**File**: `src/autom8_asana/models/task.py:256-281`
**Finding**: `Task.get_custom_fields()` is decorated with a `DeprecationWarning`:
```python
def get_custom_fields(self) -> CustomFieldAccessor:
    """.. deprecated::
        Use :meth:`custom_fields_editor` instead.
    """
    import warnings
    warnings.warn(
        "get_custom_fields() is deprecated. Use custom_fields_editor() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
```
**Evidence**: Despite the deprecation warning, 39 active call sites exist in production source (`src/`), including:
- `persistence/cascade.py:178`
- `resolution/selection.py:39`
- `models/business/descriptors.py` (14 call sites)
- `models/business/asset_edit.py` (12+ call sites)
- `models/business/fields.py` (4 call sites)

The deprecated method was introduced when `custom_fields_editor` was added as the canonical replacement. The deprecation warning has not triggered migration. The method fires a Python DeprecationWarning on every call — in production, this generates warning noise that is typically suppressed. The shim is a backward-compatibility wrapper that delegates to `_get_or_create_accessor()` (the same as `custom_fields_editor()`), so callers get the right behavior but also get deprecation noise.
**Tier**: Provably stale — replacement (`custom_fields_editor`) exists and is equivalent; 39 call sites in production code have not migrated despite the warning existing.
**Severity**: TEMPORAL (advisory)

---

### CC-013: `expected_type` deprecated parameter in DataFrame resolver (probably stale)

**Files**:
- `src/autom8_asana/dataframes/resolver/protocol.py:72,81-92`
- `src/autom8_asana/dataframes/resolver/default.py:153,162-170`

**Finding**: Both the protocol and default implementation carry the `expected_type: type | None = None` parameter with explicit deprecation:
```python
expected_type: Optional type for value coercion (deprecated, use column_def)
The expected_type parameter is deprecated in favor of column_def.
```
**Evidence**: `git blame` on `resolver/default.py` shows last change 2026-01-07 (commit from 2026-01-07). No callers in `src/` were found passing `expected_type=` at a call site (search returned only definition sites). The `column_def` replacement exists and is in use. The deprecated parameter is dead — no active callers.
**Tier**: Probably stale — no callers found, replacement parameter in use; cannot fully confirm no test or external caller passes it.
**Severity**: TEMPORAL (advisory)

---

### CC-014: `DEPRECATED` annotation on `Business.HOLDER_KEY_MAP` — detection system supersedes it (probably stale)

**File**: `src/autom8_asana/models/business/business.py:235-245`
**Finding**:
```python
# DEPRECATED: Use detection system (EntityTypeInfo) for new code.
# This map is kept for fallback when detection fails.
HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
    "contact_holder": ("Contacts", "busts_in_silhouette"),
    ...
}
```
**Evidence**: The detection system (tiered, project-based, name-pattern-based) is now the primary path. `HOLDER_KEY_MAP` is described as a fallback. The deprecation comment has no removal trigger. The map is referenced in business model hydration logic. Its exact usage cannot be determined without runtime data.
**Escalation**: Cannot determine if the "fallback when detection fails" scenario is exercised in production without metrics on detection failure rates. Needs runtime data before classifying as dead.
**Tier**: Probably stale — marked DEPRECATED with no removal trigger; replacement (detection system) is the primary path.
**Severity**: TEMPORAL (advisory)

---

### CC-015: `normalize=False` deprecated parameter in `CustomFieldAccessor` (probably stale)

**File**: `src/autom8_asana/models/custom_field_accessor.py:52`
**Finding**: The `strict` parameter docstring says:
```
If False, return name as-is (legacy, deprecated).
```
**Evidence**: The parameter `strict` (initialized as `True` by default) with value `False` providing legacy deprecated behavior. `git blame` shows file last modified 2026-02-16. No callers in source were found explicitly passing `strict=False`. The default-`True` branch is the canonical path.
**Tier**: Probably stale — legacy `strict=False` behavior documented as deprecated, no callers found passing `False`.
**Severity**: TEMPORAL (advisory)

---

### CC-016: `ValidationError` deprecated alias in `persistence/__init__.py` — D-017 item (provably stale)

**File**: `src/autom8_asana/persistence/__init__.py`
**Finding**: Per the debt ledger (D-017), `persistence/__init__.py:104` re-exports `ValidationError` as a deprecated alias for backward compatibility. The deprecation alias is kept to avoid breaking callers who import `ValidationError` from `persistence`.
**Evidence**: D-017 documents this as accumulated deprecated alias debt with "requires consumer audit" note. The original `ValidationError` alias was identified in D-017 as having a "deprecated alias with custom metaclass" (persistence/exceptions.py:256-303). The metaclass implementation adds complexity specifically to emit deprecation warnings. The debt ledger has not closed D-017.
**Cross-reference**: Debt ledger D-017 (open). The ledger estimates ~150 LOC collective removal across all D-017 items.
**Tier**: Provably stale — explicitly marked deprecated in the debt ledger with no planned removal date.
**Severity**: TEMPORAL (advisory)

---

## Debt Ledger Cross-Reference

### CC-017: D-014 (`PipelineAutoCompletionService` backward-compatible wrapper) — already cleaned up, ledger not updated

**Ledger claim**: D-014 states:
```
PipelineAutoCompletionService is a backward-compatible wrapper around CompletionService.
It exists only because engine.py still imports the old class name.
Location: src/autom8_asana/lifecycle/completion.py:102-135
Estimated LOC impact: ~35 (remove class + update import)
```
**Evidence**: `src/autom8_asana/lifecycle/completion.py` was read in full. It contains only `CompletionService` — no `PipelineAutoCompletionService` class exists. A codebase-wide grep for `PipelineAutoCompletionService` returned zero results. The class was removed (likely during the `f6e08e5` hygiene sprint on 2026-02-18) but the debt ledger item D-014 was not closed.
**Tier**: Provably stale — the remediation was completed; the ledger entry is a documentation ghost.
**Recommendation for remedy-smith**: Close D-014 in the debt ledger. No code action required.
**Severity**: TEMPORAL (advisory) — ledger artifact only.

---

## Advisory Notes

All temporal findings in this report are ADVISORY. They never block the quality gate. The decision to remove any item belongs to the engineering team.

**Escalation items requiring external data before classification:**
- CC-002/CC-003: Whether `autom8y_cache==0.4.0` contains `protocols.resolver` (needs package inspection or deployment confirmation)
- CC-004: Whether `AUTOM8_DATA_INSIGHTS_ENABLED=false` has ever been set in any environment (needs production config audit)
- CC-014: Whether `Business.HOLDER_KEY_MAP` fallback path is exercised in production (needs detection failure metrics)

---

## Methodology

1. **Prior artifact ingestion**: Read `docs/debt/LEDGER-cleanup-modernization.md` (35 items, fully reviewed). Cross-referenced D-017 deprecated aliases, D-014 backward-compat wrapper, D-007 deprecated DI dependencies, D-015 TODO stubs.

2. **Dead shim scan**: Read `clients/data/__init__.py` (no shim layer — clean). Searched `automation/config.py` for `pipeline_templates` (legacy fallback shim found). Confirmed `PipelineAutoCompletionService` (D-014) does not exist.

3. **Ephemeral comment scan**: Grep for `TODO|FIXME|HACK|XXX|TEMP|remove after|cleanup|deprecated|HOTFIX|SPIKE|Story` across all Python source files. 590-line result processed; signals filtered for temporality vs. permanence.

4. **Feature flag scan**: `os.environ.get|os.getenv` across source. Identified 20+ sites. Classified by purpose: Lambda runtime detection (legitimate), ECS metadata (legitimate), EVENTS_ENABLED (active, env-controlled), GID_PUSH_ENABLED (kill switch), AUTOM8_DATA_INSIGHTS_ENABLED (kill switch, CC-004). Only the insights kill switch showed signs of being probably stale.

5. **Deprecation scan**: Grep for `DEPRECATED|deprecated|DeprecationWarning|warnings.warn`. Identified 15 matches. Classified: query endpoint (intentional, calendar-gated to 2026-06-01 per D-002, not temporal debt — it has a clear removal trigger); `get_custom_fields()` (CC-012, 39 active callers); `expected_type` parameter (CC-013); `HOLDER_KEY_MAP` (CC-014); freshness module migration note (CC-009); `normalize=False` (CC-015); `ValidationError` alias (CC-016).

6. **Git blame dating**: Used `git blame --date=short` to date all flagged findings. Used `git log --format="%ad %s" --date=short` to establish context on when surrounding changes occurred.

7. **Caller analysis**: Searched for active call sites for all deprecated items. `get_custom_fields()` found 39 callers. `expected_type=` found 0 callers at call sites. `pipeline_templates` found 0 production callers.

8. **Debt ledger cross-reference**: Each open ledger item was checked against current source. D-014 found fully remediated without ledger update (CC-017). D-007 deprecated DI dependencies (`get_asana_pat`, `get_asana_client`) confirmed absent from current `dependencies.py` — those were also cleaned up in prior sprints without ledger update (not reported here as the ledger simply has stale-open status; the finding matches CC-017 category).

**Staleness threshold applied**: 90-day default for "probably stale" with no resolution signal. Items with explicit resolution evidence (code removed, ADR referenced, migration confirmed) classified as "provably stale."
