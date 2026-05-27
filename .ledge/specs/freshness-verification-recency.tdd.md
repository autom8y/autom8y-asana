---
type: spec
artifact_type: TDD
initiative_slug: freshness-last-verified-at
phase: design
authored_by: architect
authored_on: 2026-05-27
revised_on: 2026-05-27
revision: 3
title: Verification-recency freshness signal — production change set
companion_adr: ADR-006-freshness-equals-verification-recency.md
companion_spike: .sos/wip/SPIKE-freshness-last-verified-at.md
companion_qa_gate: .ledge/reviews/QA-freshness-verification-recency-gate.md
status: proposed-revised
evidence_grade: MODERATE
impact: low
impact_rationale: >
  No auth/crypto/PII/external-integration/new-endpoint surface. One additive
  manifest field, one stamp site, one reader re-point. The `--json` envelope
  gains additive fields (schema_version bump) — backward-compatible. No
  cache_warmer modification beyond the existing probe site. Security gate not
  triggered (complexity below FEATURE auth/data-handling thresholds).
---

# TDD — Verification-recency freshness signal

> Production change set for ADR-006. The spike
> (`.sos/wip/SPIKE-freshness-last-verified-at.md`) validated the approach against
> live prod; this TDD is the production design. Evidence grade MODERATE (self-ref
> ceiling).
>
> **Revision 2 (2026-05-27)** clears the QA NO-GO gate
> (`.ledge/reviews/QA-freshness-verification-recency-gate.md`). It adds three
> change-set sections (§2.2.1 name/stamp carry-forward, §2.3.1 sync→async bridge,
> §2.5 prober-blind-spot fix, §2.6 data-state assertion), amends the stamp logic
> (§2.2), corrects the risk table (§5), removes the false "no architectural
> questions" claim (§6), amends T10, and adds tests T11–T15.
>
> **Revision 3 (2026-05-27)** closes the sole BLOCKING gap from the QA re-QA
> (revision 2): the D1/D7 re-seed mechanism. It (a) DELETES the fictional
> `_resolve_section_names` reference and replaces it with the real, located
> re-seed — thread `Section.name` from `_list_sections()` (`progressive.py:508`,
> `models/section.py:39`) through `_check_resume_and_probe` into `_probe_freshness`,
> re-seeding COMPLETE/null-name sections inside the existing stamp block; add an
> optional `name` param to `mark_section_complete` as the completion-path backstop
> (§2.2.1); (b) adds the **re-seed-window alarm-suppression decision** (§2.6 /
> ADR §Decision-7a) — advisory until first post-deploy warm, no backfill job;
> (c) folds in D8 (narrows the "no false-CLEAN channel" wording to watermark-bearing
> sections, §2.4) and D9 (removes the non-existent `watermark_gid` reference from
> the §2.5 block, making it internally consistent); (d) adds test T16 (re-seed of a
> `prior.name=None` COMPLETE section). No other revision-2 disposition is reopened.

## 1. Scope

In scope (revision 2):

1. `SectionInfo.last_verified_at` manifest field (§2.1).
2. **Carry `name` AND `last_verified_at` forward in `mark_section_complete`**, add
   an optional `name` re-seed param, AND thread `Section.name` from the warm-entry
   section list (`_list_sections()`, `progressive.py:508`) through
   `_check_resume_and_probe` into `_probe_freshness` to re-seed COMPLETE/null-name
   sections on the next warm (§2.2.1) — heals the QA-D1 / D5 wipe at the source AND
   re-seeds the existing prod fleet (whose names are already wiped to `null`).
3. Stamp logic at `progressive.py::_probe_freshness`, gated on **delta-apply
   success** for delta-requiring verdicts, with a stamp-phase-failure metric
   (§2.2).
4. **Sync→async bridge** for the reader manifest read in the synchronous
   `main()` path (§2.3.1).
5. Freshness reader re-point + classifier-scoped, **name-based** denominator
   (§2.3).
6. **Prober content-detection blind-spot fix** — watermark-task-identity test
   replacing the count gate (§2.5).
7. **Data-state assertion** — ≥2-section null-name join fires a loud error, not a
   silent degrade (§2.6).
8. Two-signal exposure (`verification_age` **full alarmable SLI**, `mutation_age`
   context) (§2.4).

Out of scope:

- Any `cache_warmer` Lambda change beyond the existing probe site.
- Migration tooling for legacy manifests (handled by self-heal/backfill +
  the §2.2.1 carry-forward, which self-heals `name` on the next completion).

**No longer out of scope (revision 2):** the prober single-task content-detection
blind spot, deferred in revision 1, is fixed in §2.5 per binding user decision D3.

## 2. Change set

### 2.1 Manifest model field

**File**: `src/autom8_asana/dataframes/section_persistence.py` (`SectionInfo`, `:81`).

Add one optional field:

```python
last_verified_at: datetime | None = None
```

Semantics: the instant the section's cached content was last confirmed against
Asana (any probe verdict ≠ `PROBE_FAILED`), **independent of byte changes**.
Distinct from `written_at` (mutation-recency). `None` = never verified (legacy
manifest or never-probed section).

Pydantic `extra` policy is unchanged; the field is additive and defaults to
`None`, so existing serialized manifests deserialize cleanly (missing key →
`None`). No `schema_version` bump on the *manifest* is required (the field is
optional and backward-compatible at the deserialization layer); the manifest
`version`/`schema_version` semantics (`:118-119`) are untouched.

**Reference**: prototype edit on `spike/freshness-last-verified-at` matches this
exactly.

### 2.2.1 Carry `name` and `last_verified_at` forward on completion (D1 + D5 root-cause fix)

**File**: `src/autom8_asana/dataframes/section_persistence.py`
(`SectionManifest.mark_section_complete`, `:168-184`).

**Problem (QA D1, source-grounded).** `mark_section_complete` replaces
`self.sections[section_gid]` with a brand-new `SectionInfo(...)` built only from
`status, rows, written_at, watermark, gid_hash`:

```python
# CURRENT (:177-183) — wipes name AND last_verified_at to their None defaults
self.sections[section_gid] = SectionInfo(
    status=SectionStatus.COMPLETE,
    rows=rows,
    written_at=datetime.now(UTC),
    watermark=watermark,
    gid_hash=gid_hash,
)
```

`name` is populated only at creation (`create_manifest_async`, `:372`
`SectionInfo(name=names.get(gid))`); the first completion after creation wipes it
to `None`. QA verified `name=null` on 34/34 (offer `1143843662099250`) and 17/17
(unit `1201081073731555`) prod sections. The same rebuild wipes any prior
`last_verified_at` (QA D5).

**Fix — carry both fields forward from the prior `SectionInfo`, AND accept an
optional fresh `name` (D1-a, ADR §Decision-7).** The carry-forward preserves an
already-present name; the optional `name` param is the re-seed channel for the
prod case where `prior.name is None` (see the re-seed plumbing below — the
carry-forward alone heals nothing on the existing fleet). The full code block
(with the `name` parameter and the prefer-supplied-else-carry-forward fallback) is
given in the **Re-seed for existing prod manifests** block below; the
field-preservation shape is:

```python
# SectionInfo construction inside mark_section_complete:
SectionInfo(
    status=SectionStatus.COMPLETE,
    rows=rows,
    written_at=datetime.now(UTC),
    watermark=watermark,
    gid_hash=gid_hash,
    name=name if name is not None else (prior.name if prior is not None else None),
    last_verified_at=prior.last_verified_at if prior is not None else None,
)
```

Constraints / rationale:
- **`name` is preserved** so the name-based denominator join (§2.3) resolves on
  prod manifests after the first warm post-deploy. `get_section_name_index()`
  (`:213-215`), which is also `info.name`-dependent, is healed by the same change.
- **`last_verified_at` is preserved** so a section that is `CONTENT_CHANGED` in
  warm N does not lose its prior stamp during the delta write before the stamp
  block re-stamps it (closes the D5 silent-loss path where a completion that does
  not reach the stamp block — e.g. under the D6 BROAD-CATCH — would otherwise zero
  the stamp).
- **`mark_section_failed` (`:186-195`) is NOT modified** (see "Out of scope" at
  the end of the re-seed block — a FAILED section is never in the verification
  denominator).

**Re-seed for existing prod manifests — the carry-forward alone heals nothing
(QA re-QA rev-2 D1/D7).** Carrying `prior.name` forward is necessary but not
sufficient: on every current prod section `prior.name is None` (re-probed
2026-05-27: 34/34 offer, 17/17 unit), so the carry-forward propagates `None → None`
forever. A REAL re-seed must supply a non-null `name` from a live source on the
first post-deploy warm. The QA gate correctly flagged that the prior revision's
re-seed mechanism (`_resolve_section_names` "running at warm entry") was fictional
— **`grep -rn "_resolve_section_names" src/` returns nothing; no such function
exists, and no shipped path re-populates `name` on an existing (non-`None`)
manifest** (`create_manifest_async`'s `section_names` is threaded only inside
`_ensure_manifest`'s `if manifest is None:` branch, `progressive.py:442-452`). The
reference is deleted and replaced with the located, real mechanism below.

**The real name source at warm time (source-verified, file:line).** The section
names ARE available at warm entry: `build_progressive_async` calls
`sections = await self._list_sections()` (`progressive.py:508`), which returns
`list[Section]` from `self._client.sections.list_for_project_async(...)`
(`progressive.py:749-754`); `Section.name: str | None` (`models/section.py:39`).
This local `sections` list exists at `:508` — **before** the freshness probe runs
(`_check_resume_and_probe` → `_probe_freshness`, `progressive.py:531,304`). Today
`_check_resume_and_probe` (`:225-227`) is passed only `section_gids` (a
`list[str]`), NOT the `Section` objects, so `_probe_freshness` cannot see names.
The fix threads the names down.

**Re-seed plumbing (in-scope work item, three concrete edits):**

1. **Thread a `{gid: name}` map from the warm entry to the probe.** Build
   `section_names = {s.gid: s.name for s in sections if isinstance(s.name, str)}`
   at `build_progressive_async` (`:508`, reusing the exact pattern already at
   `_ensure_manifest` `:443-445`). Pass it through `_check_resume_and_probe(...)`
   (`:225`, add a `section_names` param) into `_probe_freshness(manifest,
   section_names)` (`:316`, add the param).

2. **Re-seed COMPLETE/null-name sections inside the existing stamp block.** The
   stamp block already re-loads the authoritative manifest
   (`fresh_manifest = await self._persistence.get_manifest_async(...)`,
   `progressive.py:388`) and iterates `fresh_manifest.sections` (`:393-401`). Add
   a re-seed pass there: for each `gid, info in fresh_manifest.sections.items()`
   where `info.status == SectionStatus.COMPLETE and info.name is None and gid in
   section_names`, set `info.name = section_names[gid]`. This runs in the SAME
   re-loaded manifest that the stamp block persists (`_save_manifest_async`,
   `:403`), so the re-seed lands in one write with the stamps — no extra S3 round-trip.

3. **Carry-forward backstop in `mark_section_complete` (§2.2.1 fix above).** Add an
   optional `name: str | None = None` parameter to `mark_section_complete`
   (`section_persistence.py:168`); when supplied use it, else fall back to
   `prior.name`:

```python
def mark_section_complete(self, section_gid, rows, *, watermark=None,
                          gid_hash=None, name=None):
    prior = self.sections.get(section_gid)
    self.sections[section_gid] = SectionInfo(
        status=SectionStatus.COMPLETE,
        rows=rows,
        written_at=datetime.now(UTC),
        watermark=watermark,
        gid_hash=gid_hash,
        name=name if name is not None else (prior.name if prior is not None else None),
        last_verified_at=prior.last_verified_at if prior is not None else None,
    )
    self.completed_sections = len(self.get_complete_section_gids())
```

   Its sole prod caller `update_manifest_section_async` (`section_persistence.py:437-476`,
   `mark_section_complete(...)` at `:474`) gains an optional `name` param threaded
   from `_fetch_and_persist_section`, which already holds the `Section` object
   (`section: Section | None`, `progressive.py:759`) and can pass `section.name`.
   This re-seeds names for sections that are RE-FETCHED/RE-COMPLETED (the
   delta-application and cold-build paths). It does NOT cover the steady-state warm
   where all sections are already COMPLETE and `sections_to_fetch` is empty
   (`_check_resume_and_probe` `:290`) — that case is covered by edit (2), which is
   why edit (2) is the load-bearing re-seed and (3) is the completion-path backstop.

**Re-seed window — coverage of the two completion modes:**
- **Steady-state warm (all sections already COMPLETE, none re-fetched):** edit (2)
  re-seeds inside `_probe_freshness`'s stamp block on the FIRST post-deploy warm.
  This is the dominant prod case (the re-probe shows all sections COMPLETE).
- **Delta/cold completion (a section is re-fetched and re-marked COMPLETE):**
  edit (3) supplies `section.name` at the completion site.

After ONE full post-deploy warm, both modes converge: `name_present == total` on
the manifest, the §2.3 join resolves > 0, and the §2.6 `section_name_contract_violation`
assertion goes silent. The re-seed is NOT a "verify during impl" footnote — it is
the load-bearing precondition for the feature to be non-inert on prod, and edits
(1)+(2) are required in-scope work. Covered by test T16.

**Out of scope (bounded):** `mark_section_failed` (`:186-195`) is NOT modified — a
FAILED section is not COMPLETE, is not in `get_complete_section_gids()`, and is
never in the verification denominator.

### 2.2 Stamp at probe site

**File**: `src/autom8_asana/dataframes/builders/progressive.py`
(`_probe_freshness`, `:316-413`).

After `apply_deltas_async`, stamp `last_verified_at` only on sections whose cached
content is **confirmed to match live Asana** at stamp time (ADR §Decision-5). This
is stricter than revision 1's "verdict ≠ PROBE_FAILED": a delta-requiring section
is stamped **only if its delta applied successfully**.

**Required change to `apply_deltas_async` return contract (D4).**
`apply_deltas_async` (`freshness.py:231-284`) today returns an `int` success
*count* and swallows per-section failures (`:270-281`
`freshness_delta_section_failed` is logged, the count simply not incremented, no
exception propagates). The stamp loop cannot tell *which* sections succeeded from
a count. Change the return to also surface the **set of successfully-applied
section GIDs** (e.g. return `tuple[int, frozenset[str]]`, or add an
`applied_gids: frozenset[str]` out-param). The success branch (`:282-283`
`elif outcome:`) already knows the per-index outcome — accumulate
`stale_results[i].section_gid` into the applied set there.

**Critical design point — re-load the authoritative manifest before stamping.**
`apply_deltas_async` mutates and persists the manifest for changed sections. The
`manifest` object held in `_probe_freshness` is stale w.r.t. those delta writes.
Stamping the in-memory `manifest` and re-persisting it would **clobber** the
delta-write updates (rows, written_at, watermark, gid_hash). Therefore: re-load
via `get_manifest_async`, stamp on the fresh copy, persist the fresh copy. (Spike
Approach step 2, validated.)

**Stamp-eligibility rule (per §Decision-5).** A section is stamp-eligible iff:
- its verdict is `CLEAN` (no delta needed; trustworthy because the prober blind
  spot is fixed in §2.5), OR
- its verdict required a delta (`CONTENT_CHANGED` / `STRUCTURE_CHANGED` /
  `NO_BASELINE`) AND its GID is in `applied_gids` (delta confirmed applied).

A `PROBE_FAILED` verdict is never stamp-eligible (§Decision-5a). A
delta-requiring verdict whose delta FAILED is **not** stamp-eligible (§Decision-5c,
D4) — its `last_verified_at` is left untouched, so `verification_age` correctly
climbs for that section.

Production logic (the prototype's `SPIKE_EXCLUDE_SECTION` env hook is REMOVED):

```python
# delta_applied: frozenset[str] of GIDs whose delta succeeded
#   (from the amended apply_deltas_async return contract)
DELTA_VERDICTS = {ProbeVerdict.CONTENT_CHANGED,
                  ProbeVerdict.STRUCTURE_CHANGED,
                  ProbeVerdict.NO_BASELINE}
try:
    fresh_manifest = await self._persistence.get_manifest_async(self._project_gid)
    if fresh_manifest is not None:
        now = datetime.now(UTC)
        stamped = 0
        for r in probe_results:
            if r.verdict == ProbeVerdict.PROBE_FAILED:
                continue
            # D4: a delta-requiring verdict stamps only if its delta applied
            if r.verdict in DELTA_VERDICTS and r.section_gid not in delta_applied:
                continue
            info = fresh_manifest.sections.get(r.section_gid)
            if info is not None:
                info.last_verified_at = now
                stamped += 1
        if stamped:
            await self._persistence._save_manifest_async(fresh_manifest)
            logger.info("section_last_verified_stamped",
                        extra={"project_gid": self._project_gid, "stamped": stamped})
except Exception as e:  # noqa: BLE001 — under the warm BROAD-CATCH semantics
    # D6: surface stamp-phase failure as an alarmable metric, then degrade.
    logger.error("section_last_verified_stamp_failed",
                 extra={"project_gid": self._project_gid,
                        "error": str(e), "error_type": type(e).__name__})
    # degrade per existing BROAD-CATCH; the warm still completes
```

Constraints:
- **Invariant** (§Decision-5): a section is stamped only if its cached content is
  confirmed to match live Asana — `PROBE_FAILED` never stamps (5a); `CLEAN` stamps
  because the prober is trustworthy after §2.5 (5b); a delta verdict stamps only
  on `applied_gids` membership (5c).
- **D6 — stamp-phase failures are now observable.** The stamp block remains under
  the warm BROAD-CATCH (`progressive.py:379`) so a stamp failure never breaks the
  warm, BUT it emits `section_last_verified_stamp_failed` on the failure branch so
  silent stamp starvation is alarmable separately. Revision 1 logged only the
  success path; this is the new failure-branch metric (ADR §Decision-9).
- `import os` and the `SPIKE_EXCLUDE_SECTION` branch are NOT in production.
  `datetime`/`UTC` should be module-level imports (the prototype imported them
  inline).

### 2.3 Reader re-point + active-section scoping

**File**: `src/autom8_asana/metrics/freshness.py`.

The reader currently derives `max_age` from `min(parquet mtime)` over all
parquets (`:191-204,250`). Re-point to compute **two** ages:

- **`verification_age`** (alarmable): `now − min(last_verified_at)` over the
  **in-scope** section set.
- **`mutation_age`** (context-only): the existing `now − min(parquet mtime)`,
  retained verbatim.

**In-scope set resolution** (denominator-integrity):

1. Resolve the classifier: `CLASSIFIERS.get(entity_type)`
   (`models/business/activity.py:317`). `entity_type` is the metric's
   `scope.entity_type` (already resolved in `__main__.py:674,717`).
2. `active_names = classifier.active_sections()` → `frozenset[str]` of **lowercase
   section names** (`activity.py:88`). NOTE: the classifier keys on section
   *name*, the manifest keys on section *GID*.
3. Load the manifest (`get_manifest_async`) and build the in-scope GID set by
   joining: a manifest entry is in-scope iff `info.name` (case-normalized) ∈
   `active_names`. The manifest carries `SectionInfo.name` (`:90`), which is the
   join key.
4. `verification_age = now − min(info.last_verified_at for in-scope info)`.

**Backfill / fallback (ADR-006 §Decision-6)**:
- For an in-scope section with `last_verified_at is None` (legacy / never-probed):
  fall back to that section's `written_at` for the `min` computation. It will be
  backfilled to a real stamp on the next probe.
- If **no** in-scope section can be resolved (classifier missing, manifest
  unavailable, or join yields empty), degrade to the ADR-001 mutation-axis signal
  (`verification_age` omitted; `mutation_age` reported). Never error.

**Threshold**: `verification_age` is compared against a cadence-tied threshold
sourced from the SLA-class machinery (`sla_profile.py:66-77`, `active=21600s`),
NOT a hard-coded 6h. `mutation_age` is NOT thresholded/alarmed.

### 2.3.1 Sync→async bridge for the reader manifest read (D2)

**Files**: `src/autom8_asana/metrics/freshness.py` (`from_s3_listing`, sync,
`:140`); `src/autom8_asana/metrics/__main__.py` (`main()`, sync, `:490`; reader
call at `:826`); `src/autom8_asana/dataframes/section_persistence.py`
(`get_manifest_async`, async, `:395`).

**The seam (QA D2).** The reader `from_s3_listing` is synchronous and is called
from the synchronous `main()` at `:826`. The §2.3 re-point requires it to read the
manifest, but the only manifest reader is `get_manifest_async` (async), and the
underlying `storage.load_json` (`storage.py`) is async-only. No synchronous
manifest reader exists. The only `asyncio.run` in `__main__.py` is in the
force-warm `_delegate` path (`:376,:487`), a different code path; the default
metric emission path at `:826` is fully synchronous.

**Decision — add a thin synchronous manifest-read helper that wraps the single
async call in `asyncio.run`, guarded against a running loop.** Chosen over the
alternatives below.

| Option | Verdict | Rationale |
|--------|---------|-----------|
| **(i) `asyncio.run`-wrapped sync helper** `read_manifest_sync(project_gid) -> SectionManifest \| None` that calls `asyncio.run(persistence.get_manifest_async(...))`, guarded by a running-loop check | **Chosen** | Smallest blast radius; the metric emission path stays synchronous (no refactor of `main()` and its many sync call sites). One bounded I/O call. The running-loop guard (below) makes the nested-loop `RuntimeError` impossible to hit silently. |
| (ii) Add a fully synchronous manifest reader (sync boto3 `get_object` + parse) | Rejected (for now) | Duplicates the manifest read/parse + caching logic that `get_manifest_async`/`storage.load_json` already own; a second code path for the same S3 object risks cache-coherence and parse-contract drift. Higher maintenance cost for no functional gain on this path. |
| (iii) Refactor `main()` to `async def` and `asyncio.run(main())` at the entry point | Rejected (for now) | Largest blast radius — `main()` (`:490`) has many synchronous call sites (`compute_metric`, `load_project_dataframe`, formatting); converting the whole emission path to async to serve one bounded manifest read is disproportionate and out of scope for a `low`-impact change. |

**Nested-event-loop safety (the `RuntimeError` QA flagged).**
`asyncio.run()` raises `RuntimeError: asyncio.run() cannot be called from a
running event loop` if invoked from within a running loop. The metric emission
path at `:826` is synchronous today, so no loop is running — but to make the
helper safe regardless of caller, it MUST detect a running loop and fail loudly
rather than nest:

```python
def read_manifest_sync(persistence, project_gid):
    import asyncio
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # no running loop — safe to drive our own
        return asyncio.run(persistence.get_manifest_async(project_gid))
    # a loop IS running: asyncio.run would raise. This path is not expected
    # on the synchronous main() emission path; surface it rather than nest.
    raise RuntimeError(
        "read_manifest_sync called from within a running event loop; "
        "the metric emission path must remain synchronous"
    )
```

The reader treats a `read_manifest_sync` failure (or `None` return) as the §2.3
degrade input — EXCEPT that the §2.6 data-state assertion governs whether degrade
is silent (0/1-section) or a loud error (≥2 sections). The "no architectural
questions" claim of revision-1 §6 is **false and removed** — this WAS the
architectural question; it is now answered here.

### 2.5 Prober content-detection blind-spot fix — watermark-task-identity test (D3)

**File**: `src/autom8_asana/dataframes/builders/freshness.py`
(`_probe_section`, Step 4 `modified_since` check, `:191-217`).

**The blind spot (QA D3, spike line 72-73, live-confirmed).** Step 4 issues
`tasks.list_async(modified_since=watermark_iso, opt_fields=["gid"], limit=2)`
(`:194-199`) and flags `CONTENT_CHANGED` only when `len(modified_tasks) > 1`
(`:204`). Because `modified_since` is inclusive (`>=`), the task at exactly the
watermark is always returned as a false-positive, so exactly one returned task is
read as `CLEAN`. Consequence: an edit to the exact watermark task, or any edit in
a single-task section, returns exactly 1 task → `CLEAN` → the real change is
MISSED. Under §2.2 / ADR §Decision-5b this false-`CLEAN` would falsely stamp the
section as verified.

**Fix — test the returned task's IDENTITY and `modified_at` against the stored
watermark task, not the result count.** Fetch `modified_at` (and `gid`) and
classify `CONTENT_CHANGED` when a genuine change is present even if only one task
is returned:

```python
if section_info.watermark is not None:
    watermark = section_info.watermark
    modified_tasks = await self._client.tasks.list_async(
        section=section_gid,
        modified_since=watermark.isoformat(),
        opt_fields=["gid", "modified_at"],   # was ["gid"]
        limit=2,
    ).collect()

    changed = False
    if len(modified_tasks) > 1:
        # more than the inclusive boundary task → real change(s) beyond it
        changed = True
    elif len(modified_tasks) == 1:
        t = modified_tasks[0]
        # The single returned task is the inclusive boundary task. It is a
        # genuine edit iff its modified_at is strictly AFTER the stored
        # watermark instant (the watermark task itself, or a single task,
        # edited after last build). An UNCHANGED boundary task returns
        # modified_at == watermark → strict > is False → stays CLEAN.
        t_modified = _parse_dt(getattr(t, "modified_at", None))
        if t_modified is not None and t_modified > watermark:
            changed = True
    if changed:
        return SectionProbeResult(section_gid, ProbeVerdict.CONTENT_CHANGED,
                                  current_gids=current_gids,
                                  current_gid_hash=current_hash)

return SectionProbeResult(section_gid, ProbeVerdict.CLEAN,
                          current_gids=current_gids,
                          current_gid_hash=current_hash)
```

Design notes / implementation seams (flagged, not hand-waved):
- **`modified_at > watermark` is the primary, robust signal.** It does not depend
  on knowing the watermark task's GID: any task whose `modified_at` is strictly
  after the watermark is a genuine edit, including the watermark task edited later.
  This alone closes both live-confirmed misses (single-task section edit;
  watermark-task edit).
- **`watermark_gid` branch (c) is REMOVED from the canonical block (QA re-QA rev-2
  D9).** `grep -rn "watermark_gid" src/` returns nothing — **no `watermark_gid`
  field exists on `SectionInfo` or anywhere in `src/`** — so the revision-1 block,
  which referenced `section_info.watermark_gid`, would have raised `AttributeError`
  if implemented literally. The canonical block above is the **minimal sufficient
  form**: the `modified_at > watermark` test (branch b) alone closes BOTH
  live-confirmed misses (single-task section edit; watermark-task edit) and does
  not depend on knowing the watermark task's GID. The block is now internally
  consistent — it references no field that does not exist.
- **If sub-second granularity ever requires GID disambiguation (deferred, OPTIONAL):**
  the only corner `modified_at > watermark` cannot resolve is a *different* single
  task whose `modified_at` equals the watermark instant exactly (same-second edit
  by a distinct task). If Asana's `modified_since` granularity is shown to admit
  this (verify during impl), the impl MAY add `SectionInfo.watermark_gid` as an
  additive field (same backward-compat posture as `last_verified_at`) and
  reinstate a `t.gid != section_info.watermark_gid` branch. This is explicitly
  out-of-scope for this change unless the granularity gap is demonstrated; do NOT
  ship a reference to `watermark_gid` without first adding the field.
- **`_parse_dt` / timezone:** `modified_at` arrives as an ISO string; parse to an
  aware `datetime` and compare against the aware `watermark`. Guard `None`.

### 2.6 Data-state assertion — named-section functional requirement (D1, ADR §Decision-7)

**Files**: reader (`metrics/freshness.py`, §2.3 in-scope join); warm entry
(`progressive.py` / `section_persistence.py` name-resolution path).

The in-scope join (§2.3 step 3) MUST resolve **> 0 sections** against a real
manifest before `verification_age` is considered live. Enforce the named-section
contract (ADR §Decision-7):

- **Trivial case (0 or 1 in-scope section):** a `null` `name` is acceptable. With
  ≤1 section there is no ambiguity about the denominator. Degrade silently to
  `mutation_age` if the single section's name does not join — no error.
- **≥2 in-scope sections with ANY null `name`:** this is a **contract violation**.
  Fire a **loud error** — `logger.error("section_name_contract_violation", ...)`
  with the project GID, the count of null-name sections, and the total — AND
  surface it as an assertion/metric (`section_name_contract_violation` count) so
  it alarms. Do **NOT** silently fall back to the mutation-axis 62d signal. The
  feature being inert is now a *detected, alarmed* state, not a silent false-GREEN.
- **≥2 sections, all named, join resolves > 0:** normal path; compute
  `verification_age`.

This assertion is the structural choice that converts QA's "false-GREEN of the
worst kind" into an observable failure. It is also what the §2.2.1 re-seed
plumbing services: the first warm post-deploy must re-seed `name` (edit (2) in the
re-seed block) or the assertion fires, making the inert condition impossible to
ship green. Covered by test T11.

**Re-seed window — alarm suppression until the first post-deploy warm completes
(ADR §Decision-7a; addresses QA re-QA rev-2 SRE-handoff item).** On first deploy,
every existing prod manifest carries `name=null` on 100% of sections (re-probed
2026-05-27). The §2.2.1 re-seed populates names on the FIRST post-deploy warm —
but until that warm runs, the §2.6 assertion's raw condition (≥2 sections, any
null name) is true fleet-wide. Firing `section_name_contract_violation` as a
hard alarm on every project at once would be an alarm storm during the expected,
benign re-seed window.

**Decision (chosen): suppress the contract-violation ALARM until the first
post-deploy warm completes for a given project; no one-time backfill job is
required.** The re-seed is self-healing on the normal warm cadence (edit (2) runs
inside `_probe_freshness` on every warm of a COMPLETE manifest), so a separate
backfill tool would duplicate the warm path for no gain. Mechanism:

- The assertion distinguishes **"never re-seeded yet" (window state)** from
  **"re-seeded and STILL null" (true violation)** using a per-section signal that
  the warm has run since deploy. Concretely: gate the *alarm* (not the log) on
  whether the manifest shows evidence of a post-deploy warm — the cleanest
  available signal is `last_verified_at is not None` on ≥1 in-scope section
  (the stamp block and the re-seed run in the SAME `_probe_freshness` pass and
  persist in the same write, so a manifest that has ANY stamped section has also
  been through the re-seed pass). Rule:
  - `null name` AND no in-scope section has `last_verified_at` (manifest never
    warmed post-deploy) → emit `section_name_contract_violation` at **WARN /
    advisory** level, tagged `reseed_window=true`; do NOT page.
  - `null name` AND ≥1 in-scope section HAS `last_verified_at` (manifest WAS
    warmed post-deploy, yet a name is still null) → emit at **ERROR / alarmable**
    level, tagged `reseed_window=false`. This is the true contract violation (the
    re-seed ran and failed to populate a name) and SHOULD page.
- The `verification_age` SLI itself degrades to `mutation_age` during the window
  (join still empty), which is the correct conservative posture — the operator is
  not shown a fabricated fresh number; they see the old mutation signal plus an
  advisory that re-seed is pending.

This bounds the deploy-time blast radius to advisory logs (observable, queryable)
while preserving a hard alarm for the genuine post-warm failure. The SRE handoff
must brief that `section_name_contract_violation` at `reseed_window=true` is
EXPECTED on first deploy and clears as warms roll through the fleet; only
`reseed_window=false` is an incident. Covered by test T11 (window) and the QA-gate-2
post-build re-probe (confirms `name_present == total` and the alarm is silent
after one warm).

### 2.4 Two-signal exposure (`--json` envelope)

**File**: `src/autom8_asana/metrics/__main__.py` + the `FreshnessReport`
dataclass in `freshness.py`.

Additive, backward-compatible:
- Default human-readable mode: keep the existing `parquet mtime: ... max_age=...`
  line (now labeled as `mutation_age`/context), add a `verification age:
  oldest=... max_age=... (N in-scope sections)` line below it.
- `--json` envelope: bump `schema_version` `1 → 2`; add a `verification` block
  alongside the existing `freshness` (mtime) block. Existing fields are
  unchanged (additive only — regex/path-anchored consumers of v1 fields keep
  working). The bump is gated by this ADR per ADR-001 §Consequences.
- `--strict` promotes a `verification_age` threshold breach to non-zero exit;
  `mutation_age` breaches are NOT promoted (context-only). **Revision 2:**
  `verification_age` ships as the **full alarmable SLI with `--strict` promotion
  and CloudWatch alarm wiring** — the revision-1 advisory-only deferral is
  withdrawn because the prober blind spot is closed in §2.5 (ADR §Decision-4).
  **Scope of the closure (QA re-QA rev-2 D8 — wording narrowed).** The §2.5 fix
  lives entirely inside the `if section_info.watermark is not None` branch
  (`freshness.py:192`). The re-probe (2026-05-27) found **21/34 offer + 4/17 unit
  sections carry `watermark=null`**, so the `modified_at > watermark` refinement
  does not run for them — those sections retain the **pre-existing hash-only
  detection** (a content edit that neither adds nor removes a task, leaving
  `gid_hash` unchanged, is read as `CLEAN`). The accurate claim is therefore:
  **there is no remaining known false-CLEAN channel *for watermark-bearing
  sections*; null-watermark sections retain the pre-existing hash-only detection
  (no regression — this is the behavior that predates this change, and the stamp
  such a section produces is no more false than the old mutation signal was for
  it).** This is a residual, not a new defect; it is documented rather than
  closed in this change. A future initiative to populate `watermark` (and/or add
  content-hash probing) for null-watermark sections would close it.

## 3. Data contract

| Field | Type | Axis | Alarmable | Source |
|-------|------|------|-----------|--------|
| `last_verified_at` | `datetime \| None` | verification | — | stamped at probe site |
| `written_at` | `datetime \| None` | mutation | — | existing; delta-write |
| parquet `LastModified` | `datetime` | mutation | no (`mutation_age`) | S3 |
| `verification_age` | seconds | verification | **yes** | `now − min(last_verified_at)` over in-scope |
| `mutation_age` | seconds | mutation | no | `now − min(parquet mtime)` (ADR-001 signal) |

## 4. Test cases

| # | Name | Setup | Expected |
|---|------|-------|----------|
| T1 | **CLEAN advances stamp** | Probe a section, verdict `CLEAN`, parquet NOT rewritten | `last_verified_at` advances to probe time; `written_at`/parquet mtime unchanged. (Spike Warm #1.) |
| T2 | **CONTENT_CHANGED advances stamp** | Probe, verdict `CONTENT_CHANGED`, delta applied | `last_verified_at` advances; `written_at` also advances (delta write). Both axes move. (Spike interop warm.) |
| T3 | **PROBE_FAILED does NOT advance** | Probe raises → verdict `PROBE_FAILED` | `last_verified_at` unchanged (stays at prior value / `None`). **Load-bearing invariant.** |
| T4 | **Dropped-coverage section ages and dominates** | Section in manifest but not probed this cycle (simulate dropped coverage); other sections probed `CLEAN` | dropped section's `last_verified_at` stale; `verification_age` pinned by it (becomes dominant). (Spike Warm #2.) |
| T5 | **Legacy-manifest backfill** | Manifest with `last_verified_at = None` on all sections | Reader falls back to `written_at` for `min`; next probe backfills real stamps; no error. |
| T6 | **Empty / inactive sections excluded from signal** | Manifest has empty + cold sections with stale stamps NOT in `active_sections()` | Those sections do NOT set the `verification_age` floor; only in-scope (active-classified) sections count. (Denominator-integrity.) |
| T7 | **Two-signal output** | Static-but-current project (parquet 62d old, stamps current) | `mutation_age ≈ 62d` (context, no alarm); `verification_age ≈ minutes` (alarmable, under threshold). `--strict` exits 0. (Spike signal-comparison table.) |
| T8 | **No clobber of delta writes** | Section A `CONTENT_CHANGED` (delta persisted), section B `CLEAN` (stamp only) | After stamping, A retains its delta-written rows/watermark/gid_hash AND has an advanced `last_verified_at`; B has advanced stamp only. (Re-load-authoritative-manifest contract.) |
| T9 | **Classifier-missing degrade** | `entity_type` not in `CLASSIFIERS` | `verification_age` omitted; `mutation_age` reported; exit 0. No error. |
| T10 | **Stamp failure degrades warm AND is observable** | `get_manifest_async`/`_save_manifest_async` raises during stamp | Warm completes; probe results returned; failure NOT raised AND `section_last_verified_stamp_failed` metric/log fires (D6, ADR §Decision-9). Asserting the metric — not just "logged, not raised" — is the revision-2 delta. |
| **T11** | **All-names-null prod-realistic fixture → loud violation, NOT silent inert signal** (anti-theater guard, QA test-contract) | Manifest with ≥2 in-scope sections, **all `name = null`** (the exact prod state: 34/34 offer, 17/17 unit) | `section_name_contract_violation` error log + metric/assertion FIRES; `verification_age` is NOT silently degraded to the mutation-axis 62d signal. **This is the load-bearing anti-theater test:** T1–T10 all build name-populated manifests and would ship GREEN on an inert feature; T11 fails if the feature is inert. Without T11, QA D1 would ship GREEN. (ADR §Decision-7, TDD §2.6.) |
| **T12** | **Single-task section content edit detected** (D3, §2.5) | Section with exactly 1 task; that task edited after the watermark; probe Step 4 returns exactly 1 task whose `modified_at > watermark` | Verdict `CONTENT_CHANGED`, NOT `CLEAN`. The section is NOT falsely stamped as verified. (Closes the live-confirmed single-task miss, spike line 72-73.) |
| **T13** | **Watermark-task edit detected** (D3, §2.5) | Multi-task section; the exact watermark task is edited after the watermark instant; `modified_since` returns exactly that 1 task with `modified_at > watermark` | Verdict `CONTENT_CHANGED`, NOT `CLEAN`. (Closes the live-confirmed watermark-task miss.) Contrast: an *unchanged* section where the boundary task's `modified_at == watermark` returns exactly 1 task and remains `CLEAN` (no false-positive `CONTENT_CHANGED`). |
| **T14** | **Delta-apply failure does NOT stamp** (D4, §2.2) | Section verdict `CONTENT_CHANGED`; `_apply_section_delta` raises (swallowed at `freshness.py:270-281`); GID absent from `applied_gids` | `last_verified_at` is NOT advanced for that section; `verification_age` correctly climbs. A `CLEAN` sibling in the same warm IS stamped. (Stamp gates on reconciliation success, not probe verdict.) |
| **T15** | **`name` + `last_verified_at` survive completion** (D1/D5, §2.2.1) | Section with `name="Active"` and a prior `last_verified_at`; call `mark_section_complete` | Resulting `SectionInfo` retains `name="Active"` AND the prior `last_verified_at` (not wiped to `None`). `mark_section_failed` is unchanged (not asserted to carry). |
| **T16** | **COMPLETE section with `prior.name=None` is RE-SEEDED from the section source on next warm** (D1/D7 re-seed, §2.2.1 edit (2)) | Prod-realistic manifest: ≥2 sections all COMPLETE with `name=None` (the exact prod state). Run `_probe_freshness` with a `section_names` map supplied from `_list_sections()` (the warm-entry `Section.name` source, `progressive.py:508` / `models/section.py:39`) | After the warm, `fresh_manifest.sections[gid].name == section_names[gid]` for each COMPLETE/null-name section — the name is re-seeded from the live section source, **NOT propagated as `None`**. The §2.6 join then resolves > 0 and `section_name_contract_violation` (alarmable tier) does NOT fire. **This is the test that fails on the D1 re-seed gap:** on a build that carries `prior.name` forward but does NOT thread `section_names` into `_probe_freshness`, the name stays `None` and T16's "re-seeded" assertion fails. T15 (carry-forward of a *non-null* prior name) does NOT exercise this — T16 covers the prod `prior.name is None` case that T15 leaves untested. |

## 5. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Name↔GID join resolves empty because `name` is null on prod (QA D1 — was the steady state, not an edge case)** | **was Critical → mitigated** | **Healed at the source** (§2.2.1 carry `name` forward in `mark_section_complete`), NOT degraded-around. A ≥2-section null-name join fires a **loud error** (§2.6 data-state assertion), never a silent fallback. T11 is the anti-theater guard (prod-realistic all-null fixture → loud violation). Revision 1 mis-graded this Medium and proposed logging the join-miss count as observability — that was the bug; corrected. |
| First-post-deploy re-seed: existing prod manifests have `name=null`, so the carry-forward's `prior.name` is null until names are re-populated (QA re-QA rev-2 D1/D7 — the prior revision's `_resolve_section_names` re-seed was fictional) | **was BLOCKING → in-scope fix** | §2.2.1 specifies the real, located re-seed (NOT a "verify during impl" footnote): thread `Section.name` from `_list_sections()` (`progressive.py:508`, `models/section.py:39`) through `_check_resume_and_probe` into `_probe_freshness`, re-seed COMPLETE/null-name sections in the existing stamp block (edit 2), plus an optional `name` param on `mark_section_complete` for the completion path (edit 3). The §2.6 assertion + the §2.6 re-seed-window alarm suppression make a failure-to-re-seed loud (post-warm) without an alarm storm (during the window). T16 fails on a build that omits the threading. |
| Re-seed window: first-deploy alarm storm — `section_name_contract_violation` true fleet-wide until each project's first post-deploy warm | Medium | §2.6 / ADR §Decision-7a: the contract-violation ALARM is gated on `last_verified_at is not None` (post-warm evidence). `reseed_window=true` (never warmed) → advisory WARN, no page; `reseed_window=false` (warmed, name still null) → alarmable ERROR, page. No one-time backfill job (self-heals on the warm cadence). SRE handoff briefs the expected window. |
| Null-watermark sections retain hash-only detection (QA re-QA rev-2 D8) — 21/34 offer, 4/17 unit prod-confirmed | Low (documented residual, no regression) | §2.4 wording narrowed: the false-CLEAN channel is closed for **watermark-bearing** sections only; null-watermark sections keep the pre-existing hash-only behavior (no worse than the old mutation signal for them). Documented, not closed in this change; a future watermark-population initiative would close it. |
| Prober false-CLEAN stamps a stale section as verified (QA D3, live-confirmed) | **was High → fixed** | §2.5 watermark-task-identity test (`modified_at > watermark`) replaces the count gate; a single-task or watermark-task edit is detected as `CONTENT_CHANGED`, never `CLEAN`. T12/T13 cover. |
| Delta-apply failure still stamps a section verified-current (QA D4) | **was Medium → fixed** | §2.2 gates the stamp on `applied_gids` membership for delta verdicts; a swallowed `_apply_section_delta` failure leaves `last_verified_at` untouched, so `verification_age` climbs correctly. T14 covers. |
| Stamp-phase exception silently zeroes all stamping for the warm (QA D6) | **was Medium → observable** | §2.2 emits `section_last_verified_stamp_failed` on the BROAD-CATCH failure branch (ADR §Decision-9) so stamp starvation alarms separately. T10 amended to assert the metric fires. |
| Sync→async seam: async manifest read in sync `main()` (QA D2); nested-loop `RuntimeError` | Medium | §2.3.1 `read_manifest_sync` wraps the single async call in `asyncio.run` guarded by a running-loop check that fails loudly rather than nesting. |
| Re-load race: a concurrent warm persists between `apply_deltas_async` and the stamp re-load | Low | Stamp is last-writer on `last_verified_at` only; delta fields are read fresh from the re-loaded manifest. Worst case: a stamp is one cycle behind — self-heals next probe. |
| `schema_version 1→2` breaks a v1 `--json` consumer | Low | Additive-only; v1 fields preserved byte-compatible. ADR-gated per ADR-001. T7 asserts v1 fields intact. |
| Extra manifest read+write per warm adds latency | Low | One `get` + one conditional `save` per `_probe_freshness`; spike showed no concern at 34 sections. |

## 6. Handoff readiness

- [x] Covers ADR-006 decision points 1–9 (revision 2 adds 7–9; revision 3 adds 7a
  re-seed-window alarm suppression).
- [x] Stamp site, reader, and model field each specified with file:line anchors.
- [x] Re-load-authoritative-manifest rationale captured (no-clobber, T8).
- [x] Denominator scoping specified via existing classifier (no new classifier).
- [x] **Named-section functional requirement + carry-forward fix specified**
  (§2.2.1, §2.6; D1) — name-based scoping retained, GID-resolver rejected.
- [x] **Stamp invariant broadened to reconciliation-success** (§2.2; D3/D4) —
  `PROBE_FAILED` no-stamp (T3) + delta-apply-success gate (T14) + trustworthy
  `CLEAN` (§2.5).
- [x] **Sync→async bridge specified** (§2.3.1; D2) — chosen option + nested-loop
  guard. The revision-1 "no architectural questions" claim is **removed**: this
  WAS the architectural question, now answered.
- [x] **Prober blind-spot fix designed** (§2.5; D3) — watermark-task-identity
  test, T12/T13. No longer deferred.
- [x] **Stamp-phase-failure metric specified** (§2.2; D6) — T10 amended.
- [x] Legacy backfill / degrade paths specified (T5, T9, T10).
- [x] Two-signal exposure + schema bump specified (T7, §2.4); `verification_age`
  is the full alarmable SLI (advisory-only posture withdrawn).
- [x] **Anti-theater test T11** — prod-realistic all-null fixture → loud
  violation, guarding against the inert-feature GREEN.
- [x] **D1/D7 re-seed mechanism is REAL and located** (revision 3; §2.2.1) — the
  fictional `_resolve_section_names` reference is DELETED; replaced with the
  source-verified path: `Section.name` from `_list_sections()` (`progressive.py:508`,
  `models/section.py:39`) threaded through `_check_resume_and_probe` (`:225`) into
  `_probe_freshness` (`:316`), re-seeding COMPLETE/null-name sections in the
  existing stamp block (`:388-403`). Backstop: optional `name` param on
  `mark_section_complete` (`section_persistence.py:168`). Covered by T16.
- [x] **Re-seed-window alarm suppression decided** (revision 3; §2.6 /
  ADR §Decision-7a) — advisory-until-first-warm, no backfill job, SRE-briefed.
- [x] **D8 wording narrowed** (revision 3; §2.4) — false-CLEAN closure scoped to
  watermark-bearing sections; null-watermark residual documented.
- [x] **D9 resolved** (revision 3; §2.5) — non-existent `watermark_gid` reference
  removed from the canonical block; block is internally consistent.

**Remaining non-obvious implementation seams (flagged, not hand-waved):**
(1) the `apply_deltas_async` return-contract change to surface `applied_gids`
(§2.2) — one caller (`progressive.py:362`), zero test callers; (2) `_parse_dt` /
timezone handling for `modified_at` comparison (§2.5). Each is a bounded
implementation decision within the design, not an unresolved architectural
question. The revision-2 D1 re-seed seam is **no longer a flagged seam — it is a
specified in-scope change** (§2.2.1 edits 1–3).
