---
type: decision
artifact_type: ADR
adr_id: ADR-006
initiative_slug: freshness-last-verified-at
phase: design
authored_by: architect
authored_on: 2026-05-27
revised_on: 2026-05-27
revision: 3
title: Metrics freshness signal measures verification-recency, not mutation-recency
status: proposed-revised
amends: ADR-001
companion_tdd: freshness-verification-recency.tdd.md
companion_spike: .sos/wip/SPIKE-freshness-last-verified-at.md
companion_qa_gate: .ledge/reviews/QA-freshness-verification-recency-gate.md
evidence_grade: MODERATE
evidence_rationale: >
  Primary evidence is a single self-authored throwaway spike exercised against
  live prod data (self-ref ceiling per self-ref-evidence-grade-rule). Revision 2
  incorporates an independent QA gate (rite-disjoint) that re-probed prod S3 and
  source-grounded six design defects; that external corroboration raises the
  empirical floor but the design grade remains MODERATE (single QA pass, not
  multi-rite + post-build re-probe). The named-section finding (D1) and the
  prober blind-spot (D3) are STRONG-within-gate (deterministic re-runnable
  probes); the design-soundness amendments here are MODERATE.
---

# ADR-006 — Metrics freshness signal measures verification-recency, not mutation-recency

## Status

**Proposed (Revised — revision 2)** — 2026-05-27. **Amends ADR-001**
(`metrics-cli-declares-freshness`, accepted 2026-04-27). ADR-001's *delivery
contract* — the CLI surfaces a freshness signal alongside every scalar, the
`--json` envelope, `--strict`, exit-code matrix — is **retained in full**. This
ADR amends only the **definition of the signal** and the **scope over which it is
computed**. The CLI surface, flags, and exit semantics established by ADR-001 are
unchanged.

**Revision 2 (2026-05-27)** clears the QA NO-GO gate
(`.ledge/reviews/QA-freshness-verification-recency-gate.md`). The
verification-recency *concept* is **validated by the live spike and not
re-litigated**. The revision is scoped to design-defect remediation, binding two
user decisions:

- **D1 (CRITICAL) — named sections are a FUNCTIONAL REQUIREMENT** (new
  §Decision-7). The QA-found `name=null` on 100% of prod sections is a
  contract violation to be healed at the source (`mark_section_complete` wipe),
  not masked by a GID-resolver. See §Decision-7.
- **D3 (HIGH) — the prober blind spot is fixed IN-SCOPE** (§Decision-4 amended).
  `verification_age` ships as the FULL alarmable `--strict` SLI; the advisory-only
  deferral is removed because the signal is now trustworthy enough to alarm.

Revision-2 amendment map: §Decision-4 (advisory-only posture removed),
§Decision-5 (stamp gates on delta-apply success), §Decision-7 (NEW — named-section
functional requirement + data-state assertion), §Decision-8 (NEW — sync→async
bridge), §Decision-9 (NEW — stamp-phase-failure metric), §Deferred (prober blind
spot promoted out of deferral into §Decision-4/TDD §2.5).

**Revision 3 (2026-05-27)** closes the single BLOCKING gap the QA re-QA (revision
2) left open — the D1/D7 re-seed for existing prod manifests was attributed to a
function (`_resolve_section_names`) that does not exist. This revision binds the
REAL re-seed mechanism (§Decision-7, source-verified) and adds §Decision-7a (the
re-seed-window alarm-suppression decision the re-QA flagged as a required
SRE-handoff item). It also folds in the two LOW re-QA items: D8 (the
"no remaining false-CLEAN channel" claim is narrowed to watermark-bearing
sections, §Revision-2-correction) and D9 (the §2.5 design removes the
non-existent `watermark_gid` reference). No revision-2 decision is reopened.

Revision-3 amendment map: §Decision-7 (re-seed mechanism made real + located),
§Decision-7a (NEW — re-seed-window alarm suppression), §Revision-2-correction
(D8 false-CLEAN wording narrowed + D9 `watermark_gid` reference removed).

## Context

ADR-001 shipped a freshness signal computed as:

```
max_age = now − min(parquet LastModified)   # over ALL parquets under the prefix
```

(`src/autom8_asana/metrics/freshness.py:191-204,250`). This was a correct and
valuable first step — it closed the *opaque-by-default* gap. But the spike
(`.sos/wip/SPIKE-freshness-last-verified-at.md`) demonstrates the signal is
**wrong on two independent axes**, and the second axis was not visible at
ADR-001 authoring time.

### Axis 1 — wrong timestamp (mutation-recency, not verification-recency)

Parquet `LastModified` is a **mutation-recency** axis: it advances only when
bytes change. Every persisted timestamp in the system today is on this axis —
parquet mtime, manifest `written_at` (`section_persistence.py:86`), and
`watermark` (`:88`). None of them record **when the data was last confirmed
still-correct against Asana**.

The freshness prober (`src/autom8_asana/dataframes/builders/freshness.py`)
*computes* a verification event on **every probe** — it calls Asana, compares
hashes and watermarks, and emits a `CLEAN` verdict when the cached section still
matches live state. That verification event is **discarded today**. A
genuinely-current but static section (no edits in 62 days) is re-confirmed
`CLEAN` on every warm, yet its parquet mtime never moves — so it pins the signal
to its ancient write time. Empirically: `active_mrr` reports `max_age=62d` while
its data is correct (spike Findings → Baseline; signal-comparison table rows
"baseline/warm #1/#3" all show CURRENT=62d).

### Axis 2 — wrong scope (denominator-integrity violation)

`min(...)` is taken over **ALL** parquets under the prefix, including sections
that are empty, near-empty, cold, or no longer classified as feeding the metric.
A single static, metric-irrelevant section sets the floor for the whole signal.
This is a **denominator-integrity** defect: the freshness denominator (the set of
sections the signal ranges over) is wrong. The signal is not scoped to the
sections that actually contribute to the metric it is reported against.

The metrics package already owns the in-scope set: `SectionClassifier`
(`src/autom8_asana/models/business/activity.py:49`) exposes `active_sections()`
(`:88`) and is registered per entity-type in `CLASSIFIERS`
(`:317`). `__main__.py` already resolves it for `SectionCoverageDelta`
(`__main__.py:289-296`). The freshness reader does not use it.

A signal correct on both axes is a real SLI: **max verification-age across the
in-scope (active-classified) sections that feed the metric**, with a threshold
tied to the warm cadence rather than the arbitrary 6h TTL ADR-001 inherited.

### Why this matters

Decision-grade financial metrics ride on this signal (ADR-001 Context). A signal
stuck at 62d when the data is current is *false-stale* (operators learn to ignore
it — alarm fatigue); a signal that cannot see a silently dropped-from-coverage
section is *false-fresh* (the dangerous direction). The spike proved the proposed
signal fixes both: it tracked verification liveness AND surfaced a dropped
section as the dominant age (spike Findings → Warm #2).

## Decision

**Freshness is verification-recency, scoped to active-classified sections.**

1. **Persist per-section `last_verified_at`** on the manifest
   (`SectionInfo`, `section_persistence.py:81`), stamped at the existing probe
   site (`progressive.py::_probe_freshness`, `:316-413`) on **every probe verdict
   ≠ `PROBE_FAILED`**, regardless of byte changes.

2. **Reader re-point**: the metrics freshness signal computes
   `verification_age = now − min(last_verified_at)` over the in-scope section
   set, NOT `now − min(parquet mtime)`.

3. **Scope to active-classified sections** (denominator-integrity correction):
   the `min` ranges only over sections in `CLASSIFIERS[entity_type].active_sections()`,
   resolved against the manifest. Empty / near-empty / cold / unclassified
   sections do not set the floor.

4. **Expose two signals; `verification_age` is the FULL alarmable SLI**
   (**amended in revision 2 — advisory-only posture REMOVED**):
   - `verification_age` — **alarmable** SLI; `now − min(last_verified_at)` over
     in-scope sections; threshold tied to warm cadence. **It ships as the full
     `--strict`-promotable, CloudWatch-alarmable SLI with no advisory-only
     gating.** Revision 1 deferred the prober content-detection blind spot and
     the QA gate consequently required `verification_age` to ship *advisory-only*
     (no `--strict`, no alarm) while a known false-CLEAN channel existed. **The
     user has chosen to CLOSE the blind spot within this change** (§Decision-5
     prober fix + TDD §2.5). With the blind spot closed for **watermark-bearing
     sections**, a `CLEAN` verdict on such a section is a trustworthy verification
     event, so the signal is trustworthy enough to alarm. The advisory-only
     deferral is therefore **withdrawn**. **Scope caveat (revision 3 — QA re-QA
     rev-2 D8):** the §2.5 fix runs only inside the `watermark is not None` branch;
     null-watermark sections (21/34 offer, 4/17 unit, prod-confirmed 2026-05-27)
     retain the pre-existing hash-only detection. The false-CLEAN channel is closed
     for watermark-bearing sections, NOT universally — null-watermark sections are
     a documented residual (no regression; no worse than the old mutation signal
     was for them). See §Revision-2-correction.
   - `mutation_age` — **context-only**; the existing `now − min(parquet mtime)`,
     retained for diagnostics (e.g. "data is current but hasn't changed in 62d"
     is a legitimate, non-alarming observation). NOT alarmable.

5. **Stamp invariant — `last_verified_at` records confirmed reconciliation, not
   merely a probe verdict** (**amended in revision 2 — broadened from
   "PROBE_FAILED ⇒ no stamp"; D3 + D4**):

   The load-bearing invariant is now: **a section is stamped
   `last_verified_at = now` only if its cached content is confirmed to match live
   Asana at stamp time.** This decomposes into three sub-rules:

   5a. **`PROBE_FAILED` MUST NOT advance the stamp.** Unchanged — this is the
   mechanism by which dropped-coverage and probe-broken sections surface (their
   stamp ages and becomes the dominant `verification_age`).

   5b. **A verdict ≠ `PROBE_FAILED` that required no delta (i.e. `CLEAN`) stamps
   directly** — but only because the prober's `CLEAN` is now trustworthy. The
   QA gate (D3) and the spike (line 72-73) live-confirmed that the prober's
   `modified_since` gate (`freshness.py:204`, `len(modified_tasks) > 1`)
   mis-classifies as `CLEAN` when `modified_since` returns exactly the
   watermark/edited task — so single-task-section edits AND edits to the exact
   watermark task were MISSED, and a false-`CLEAN` would falsely stamp the
   section as verified. **The prober is fixed in-scope** so that a genuine edit is
   never read as `CLEAN`: the content-change test compares the returned task's
   identity / `modified_at` against the stored watermark task rather than counting
   results (TDD §2.5). Only after this fix is `CLEAN` a legitimate stamp.

   5c. **A verdict that required a delta (`CONTENT_CHANGED` / `STRUCTURE_CHANGED`
   / `NO_BASELINE`) stamps only on delta-apply SUCCESS** (D4). The stamp must
   key on *reconciliation success*, not the probe-time verdict.
   `apply_deltas_async` (`progressive.py:231-284`) swallows per-section delta
   failures: `_apply_section_delta` exceptions are caught and logged
   (`freshness.py:270-281` `freshness_delta_section_failed`), the success count is
   simply not incremented, and no exception propagates. Revision 1 stamped any
   verdict ≠ `PROBE_FAILED`, which would mark a section "verified-current" even
   when its delta failed to apply — a second false-fresh channel. The stamp now
   fires for a delta-requiring section **only if that section is in the set
   `apply_deltas_async` reports as successfully applied** (TDD §2.2 returns the
   applied-GID set, not just a count).

6. **Backward-compatibility**: legacy manifests lack the field. Missing
   `last_verified_at` is treated as **"never verified"**; on read it falls back
   to the section's `written_at`, and is backfilled on the next probe. A manifest
   where *no* in-scope section has been stamped yet degrades to the ADR-001
   mutation-axis signal rather than erroring. **Note:** this graceful-degrade path
   is constrained by §Decision-7 — it MUST NOT silently absorb the named-section
   contract violation; with ≥2 in-scope sections an empty/null-name join fires a
   loud error rather than degrading quietly.

7. **Named sections are a FUNCTIONAL REQUIREMENT; the `name` wipe is healed at
   the source** (**NEW in revision 2 — D1, binding user decision**):

   A section MUST be named. A `null` `name` is acceptable ONLY in the trivial
   0-or-1-section case (a single section needs no name to be unambiguously the
   denominator). With **≥2 sections**, a `null` `name` is a **contract violation
   that MUST be surfaced loudly** (error log + assertion/alarm) — never silently
   tolerated, never degraded-around.

   - **Root cause (QA D1, source-grounded):** `SectionInfo.name` is populated only
     at manifest creation (`section_persistence.py:372`,
     `SectionInfo(name=names.get(gid))`). Every subsequent section completion goes
     through `mark_section_complete` (`section_persistence.py:168-184`), which
     **replaces** `self.sections[section_gid]` with a brand-new `SectionInfo(...)`
     built from `status, rows, written_at, watermark, gid_hash` — carrying
     **neither `name` nor `last_verified_at`**. So the first completion after
     creation wipes `name` to its `None` default. QA verified `name=null` on
     34/34 (offer) and 17/17 (unit) prod sections.

   - **Fix at the source (chosen):** `mark_section_complete` (and any sibling that
     rebuilds `SectionInfo` — `mark_section_failed` rebuilds too, but a failed
     section is not in the verification denominator) MUST **carry `name` forward**
     from the prior `SectionInfo` for `section_gid`. This **simultaneously heals
     the `last_verified_at` carry-forward** (same mechanism, same wipe — the prior
     stamp must also survive completion). One fix, two fields preserved.

   - **Re-seed for the EXISTING prod fleet — the carry-forward alone heals nothing
     (revision 3; QA re-QA rev-2 D1/D7).** On every current prod section
     `prior.name is None` (re-probed 2026-05-27: 34/34 offer, 17/17 unit), so the
     carry-forward propagates `None → None` indefinitely. A REAL re-seed must
     supply a non-null `name` from a live source. **Revision 2 attributed this to
     `_resolve_section_names` running at warm entry — that function DOES NOT EXIST**
     (`grep -rn "_resolve_section_names" src/` returns nothing; no shipped path
     re-populates `name` on a non-`None` manifest — `create_manifest_async`'s
     `section_names` is threaded only inside `_ensure_manifest`'s `if manifest is
     None:` branch, `progressive.py:442-452`). The fictional reference is **deleted**
     and replaced with the source-verified mechanism:

     **The name source is `Section.name` at warm entry.** `build_progressive_async`
     calls `sections = await self._list_sections()` (`progressive.py:508`),
     returning `list[Section]` with `Section.name: str | None`
     (`models/section.py:39`); this list exists *before* the freshness probe runs.
     The re-seed threads those names down: build a `{gid: name}` map at `:508`
     (reusing the `_ensure_manifest` pattern, `:443-445`), pass it through
     `_check_resume_and_probe` (`:225`, currently passed only `section_gids`) into
     `_probe_freshness` (`:316`), and re-seed COMPLETE/null-name sections inside
     the existing stamp block (`progressive.py:388-403`) — which already re-loads
     the authoritative manifest and persists it, so the re-seed lands in the SAME
     write as the stamps. A backstop adds an optional `name` param to
     `mark_section_complete` (`section_persistence.py:168`, threaded from
     `_fetch_and_persist_section` which holds the `Section` object) for sections
     that are re-fetched/re-completed. TDD §2.2.1 gives the three concrete edits.
     This is an in-scope work item, NOT a "verify during impl" footnote.

   - **The GID-based-resolver alternative (QA option b) is REJECTED.** Re-pointing
     the join to a GID key that survives completion would mask the
     functional-requirement violation: the signal would resolve, but a manifest
     with unnamed sections — which a human operator cannot interpret and which
     indicates the upstream wipe is still happening — would pass silently.
     Name-based scoping STAYS; the bug is that names were being wiped, not that
     names were the wrong join key.

   - **Data-state assertion (load-bearing):** the active-section join MUST resolve
     **> 0 sections** against a real manifest before `verification_age` is
     considered live. A manifest with **≥2 sections where any in-scope section has
     a null `name`** fires a **loud error** (error log + metric/assertion), NOT a
     silent fallback to the mutation-axis 62d signal. The trivial 0-or-1-section
     case is exempt. This converts the QA-named "false-GREEN of the worst kind"
     (feature inert in prod, emitting the old number under a new label) into a
     detected, alarmed state. See the §Alternatives table row D1 and TDD §2.6 +
     test T11.

7a. **Re-seed-window alarm suppression — advisory until first post-deploy warm; no
   backfill job** (**NEW in revision 3 — QA re-QA rev-2 required SRE-handoff item**):

   On first deploy, every existing prod manifest carries `name=null` fleet-wide, so
   the §Decision-7 data-state assertion's raw condition is true on every project
   until that project's first post-deploy warm runs the re-seed. Firing
   `section_name_contract_violation` as a hard alarm everywhere at once would be an
   alarm storm during the expected, benign re-seed window.

   **Decision (chosen): the contract-violation ALARM is gated on evidence of a
   post-deploy warm; no one-time backfill job is required.** The re-seed self-heals
   on the normal warm cadence (it runs inside `_probe_freshness` on every warm of a
   COMPLETE manifest), so a backfill tool would duplicate the warm path for no gain.
   The alarm tiers on `last_verified_at is not None` (the stamp and the re-seed run
   in the SAME `_probe_freshness` pass and persist in the same write, so any stamped
   section proves the re-seed pass ran):
   - **`null name` AND no in-scope section stamped** (`reseed_window=true`, never
     warmed post-deploy) → advisory **WARN**, do NOT page. `verification_age`
     degrades to `mutation_age` (conservative — no fabricated fresh number).
   - **`null name` AND ≥1 in-scope section stamped** (`reseed_window=false`, warmed
     yet a name is still null) → alarmable **ERROR**, SHOULD page. This is the true
     contract violation (re-seed ran and failed).

   **Backfill explicitly NOT required** — the warm cadence is the backfill. The SRE
   handoff (TDD §Documentation) must brief that `section_name_contract_violation` at
   `reseed_window=true` is EXPECTED on first deploy and clears as warms roll through
   the fleet; only `reseed_window=false` is an incident. See TDD §2.6.

8. **Sync→async bridge for the reader is specified** (**NEW in revision 2 —
   D2**): the freshness reader (`metrics/freshness.py from_s3_listing`,
   synchronous, `:140`) is invoked from the synchronous `main()`
   (`__main__.py:490`, reader call at `:826`) and must newly read the manifest,
   whose only reader is `get_manifest_async` (`section_persistence.py:395`, async;
   underlying `storage.load_json` is async-only). The chosen bridge and its
   nested-event-loop safety are specified in TDD §2.3.1; the false "no
   architectural questions" claim (TDD §6) is removed.

9. **Stamp-phase failures are observable** (**NEW in revision 2 — D6**): the
   stamp block lives under the warm BROAD-CATCH (`progressive.py:379`,
   `_probe_freshness` degrade → `return 0, 0`). A stamp-phase exception (S3 5xx,
   throttling during `get_manifest_async` / `_save_manifest_async`) is currently
   swallowed: no sections stamped that warm, warm reports success, and the
   operator cannot distinguish "stamp write failed" from "genuinely not verified."
   An explicit stamp-phase-failure metric (`section_last_verified_stamp_failed`)
   is emitted on the failure branch so silent stamp starvation is alarmable
   separately from the `verification_age` climb it would otherwise cause. See
   TDD §2.2.

The threshold default of `6h` (ADR-001 §Decision-2, `__main__.py:164`) is
**re-grounded**: it should track the warm cadence (the interval at which the
Lambda re-verifies). The SLA-class machinery (`sla_profile.py`, `active=21600s`)
already models per-class thresholds; the verification-age threshold reuses it
rather than inventing a new arbitrary constant.

## Alternatives considered

| # | Alternative | Verdict | Why it loses |
|---|-------------|---------|--------------|
| a | Project-level heartbeat `last_warm_completed_at` (one timestamp per project, stamped when a full warm finishes) | Rejected | Loses **per-section dropped-coverage detection**. A single project-level timestamp advances whenever *any* warm completes, so a section that silently fell out of coverage (probe never runs for it) is invisible — its staleness is masked by the project heartbeat. The spike's Warm #2 result (excluded section becomes dominant age) is impossible to reproduce with a project-scalar. False-fresh in the dangerous direction. |
| b | Touch the parquet on `CLEAN` (rewrite bytes / re-PUT to bump `LastModified`) | Rejected | **Defeats the CLEAN optimization and abuses mtime as a semantic channel.** The whole point of `CLEAN` is to *avoid* rewriting unchanged data; touching the object on every clean probe re-introduces the write cost the delta-merge path was built to avoid, and inflates S3 PUT volume across the fleet. It also conflates the two axes back together — mtime would no longer mean mutation-recency, breaking any consumer (and `mutation_age` itself) that reads it as such. Overloading a storage primitive's metadata to carry application semantics is a structural smell. |
| c | **Per-section `last_verified_at` on the manifest** [CHOSEN] | Accepted | Decouples the two axes with zero new storage (one field on an existing manifest), stamped at the existing probe site. Per-section granularity is exactly what dropped-coverage detection needs. Proven empirically (spike, all three warms). Self-healing (backfills on next probe). |
| d | Two-signal model: `verification_age` (alarmable) + `mutation_age` (context-only) | Accepted as the **exposed shape** | Not mutually exclusive with (c) — (c) is the *storage/stamp* mechanism, (d) is the *exposure* mechanism. Keeping `mutation_age` as non-alarmable context preserves the ADR-001 signal for diagnostics and backward-compat (a legacy consumer still sees a mtime-derived age) while making `verification_age` the thing operators alarm on. Recommended. |

Alternative (a) is the strongest rejected option — it is cheaper (one scalar) and
genuinely different in decomposition (project-altitude vs section-altitude). It
loses on a single but decisive axis: it cannot express the dropped-coverage
signal the spike proved is the highest-value output. We document that as the
binding constraint that makes the section-altitude decomposition non-negotiable.

### D1 — How to make the name↔GID join resolvable on prod (revision 2)

The QA gate found the join key (`SectionInfo.name`) is `null` on 100% of prod
sections. Three ways to make the join resolve; this is the load-bearing
design choice of revision 2.

| # | Option | Verdict | Rationale |
|---|--------|---------|-----------|
| D1-a | **Carry `name` forward in `mark_section_complete`** (heal the wipe at the source); keep name-based scoping; add a ≥2-section null-name loud-error assertion | **Accepted [CHOSEN]** | Fixes the actual bug (the wipe), not the symptom. Heals `last_verified_at` carry-forward by the same mechanism (§Decision-7). Preserves the functional requirement that sections are named — operators and the join both depend on it. The data-state assertion converts the inert-feature condition into a detected, alarmed state. |
| D1-b | **Re-point the join to a GID-stable key** (e.g. classifier name → GID via a separate stable index), bypassing `info.name` | **Rejected** | Masks the functional-requirement violation: the signal would resolve even on manifests whose sections are unnamed, hiding that the upstream wipe is still happening and leaving a human-uninterpretable manifest. `get_section_name_index()` (`section_persistence.py:213-215`) *also* depends on `info.name` and would remain broken — option b does not heal it. Treats names as an incidental join key when they are a contract. |
| D1-c | **Accept null names; degrade to mutation-axis whenever the join is empty** (revision-1 behavior) | **Rejected** | This IS the false-GREEN bug. The degrade path is the *steady state* on prod (null-name is universal), so `verification_age` never computes and the feature silently emits the 62d mutation number under a new label. The "join-miss count" logged for observability would read 34/34 — total failure recorded as telemetry rather than caught as a violation. |

Option D1-a is binding. The named-section requirement (§Decision-7) and the
≥2-section loud-error data-state assertion are the design's structural choices,
not mitigations. **Revision 3 makes D1-a complete:** the carry-forward (which heals
nothing on a fleet whose names are already `null`) is paired with a REAL,
source-located re-seed (`Section.name` from `_list_sections()` threaded into
`_probe_freshness`, §Decision-7) and a re-seed-window alarm-suppression decision
(§Decision-7a). The revision-2 reference to the nonexistent `_resolve_section_names`
is deleted.

## Consequences

### Positive

- Freshness tracks **verification liveness**, not write churn — the 62d
  false-stale floor disappears (spike: PROPOSED=9m where CURRENT=62d).
- **Dropped coverage becomes visible** — a section that falls out of the probe
  loop ages and dominates the signal (spike Warm #2).
- **Denominator-integrity restored** — the signal ranges over the sections that
  actually feed the metric, not every parquet under the prefix.
- **Zero new storage** — one field on an existing manifest object.
- **Self-healing** — legacy manifests backfill on the next probe; no migration.
- **Backward-compatible exposure** — `mutation_age` preserves the ADR-001 number
  for any consumer that depended on it.

### Negative

- The probe site now performs **one extra manifest read + conditional write**
  per warm (re-load authoritative manifest, stamp, persist). Bounded: one
  `get_manifest_async` + one `_save_manifest_async` per `_probe_freshness` call,
  only when ≥1 section was stamped. (Spike ran this on a 34-section project with
  no observed latency concern.)
- The **two-signal output is a wider contract**. The `--json` envelope
  (ADR-001 `schema_version: 1`) gains fields → a `schema_version` bump is
  required, gated by an ADR per ADR-001 §Consequences. The TDD specifies the
  additive, non-breaking shape.
- The reader now depends on the **classifier↔manifest join** (active section
  *names* → manifest entries by `SectionInfo.name`). This couples the freshness
  reader to the classifier registry — an acceptable coupling (the metric is
  *defined* by that classifier) but a new dependency edge.

### Neutral

- The added per-section preservation in `mark_section_complete` (`name` +
  `last_verified_at` carry-forward, §Decision-7) is a strict superset of the
  prior write — no field is dropped that was previously retained, so the change
  is backward-compatible at the manifest layer (QA Target 5 PASS retained).

### Revision-2 correction — prober content-detection blind spot is now IN SCOPE

**Revision 1 deferred this; revision 2 fixes it (binding user decision D3).**

`freshness.py:191-217`. The `modified_since` step (`section_info.watermark`
branch) issues `tasks.list_async(modified_since=watermark_iso, opt_fields=["gid"],
limit=2)` (`:194-199`) and flags `CONTENT_CHANGED` only when
`len(modified_tasks) > 1` (`:204`). Because `modified_since` is inclusive (`>=`),
the task at exactly the watermark is always returned as a false-positive, so a
single returned task is read as `CLEAN`. **Live-confirmed** (spike line 72-73; QA
D3): editing the exact watermark task, or any edit in a single-task section,
returns exactly 1 task → `CLEAN` → the real change is MISSED.

Under §Decision-5b, a `CLEAN` verdict stamps `last_verified_at = now` — so a
false-`CLEAN` stamps the section as freshly verified while its content is provably
stale. Once `verification_age` is the alarmable SLI (§Decision-4), this is the
alarmable SLI actively lying in the dangerous (false-fresh) direction. That is
why the fix is in-scope and not deferrable: the signal cannot be trusted to alarm
while this channel is open.

**Fix (designed in TDD §2.5):** replace the count-based gate with a
**watermark-task-identity test**. Fetch `opt_fields=["gid", "modified_at"]` and
treat the section as `CONTENT_CHANGED` if EITHER (a) more than one task is
returned, OR (b) exactly one task is returned and its `modified_at` is strictly
greater than the stored watermark (i.e. the watermark task itself was edited after
the watermark instant). A genuine edit — single-task section or watermark-task
edit — is then never read as `CLEAN`. Test cases: TDD §4 T12 (single-task section
edit detected) and T13 (watermark-task edit detected).

**D9 correction (revision 3).** Revision 2 listed a third branch (c) "the single
returned task's `gid` does not match the expected watermark task." That branch
referenced `SectionInfo.watermark_gid`, which **does not exist** (`grep -rn
"watermark_gid" src/` returns nothing). The §2.5 code block as written would have
raised `AttributeError`. Branch (c) is **removed**: branch (b) (`modified_at >
watermark`) alone closes BOTH live-confirmed misses and does not depend on the
watermark task's GID. If sub-second granularity is later shown to require GID
disambiguation, `SectionInfo.watermark_gid` may be added as an additive field
(deferred, OPTIONAL) — but the shipped block references no non-existent field. See
TDD §2.5.

**D8 residual (revision 3).** The §2.5 fix runs only inside `if
section_info.watermark is not None`. Prod re-probe (2026-05-27) found 21/34 offer
+ 4/17 unit sections carry `watermark=null`; for those the fix is inert and the
pre-existing hash-only detection (a content edit that does not change the task GID
set is read as `CLEAN`) persists. This is a **documented residual, not a
regression** — the §Decision-4 "no remaining false-CLEAN channel" claim is
accordingly scoped to **watermark-bearing sections**. Closing the null-watermark
case (by populating `watermark` and/or adding content-hash probing) is a future
initiative, out of scope here.

## Anchors

- Spike: `.sos/wip/SPIKE-freshness-last-verified-at.md` (full empirical results)
- Reference prototype: branch `spike/freshness-last-verified-at` (uncommitted
  edits to `section_persistence.py` + `progressive.py`)
- Current (wrong) reader: `src/autom8_asana/metrics/freshness.py:191-204,250`
- Probe site (stamp location): `src/autom8_asana/dataframes/builders/progressive.py:316-413`
- Prober (verification event source): `src/autom8_asana/dataframes/builders/freshness.py`
- Manifest model: `src/autom8_asana/dataframes/section_persistence.py:81-103`
- Classifier (in-scope set): `src/autom8_asana/models/business/activity.py:49,88,317`
- Coverage-delta precedent (classifier already used here):
  `src/autom8_asana/metrics/__main__.py:289-296`
- SLA-class thresholds (cadence-tied threshold source):
  `src/autom8_asana/metrics/sla_profile.py:66-77`
- Prober blind spot (IN SCOPE, revision 2): `src/autom8_asana/dataframes/builders/freshness.py:191-217`
- `name`/`last_verified_at` wipe site (D1/D5 root cause): `src/autom8_asana/dataframes/section_persistence.py:168-184` (`mark_section_complete`)
- **Re-seed name source at warm time (D1/D7 revision 3):** `src/autom8_asana/dataframes/builders/progressive.py:508` (`sections = await self._list_sections()`) → `Section.name` at `src/autom8_asana/models/section.py:39`; threaded via `_check_resume_and_probe` (`progressive.py:225`) into `_probe_freshness` stamp block (`progressive.py:388-403`)
- **Confirmed-nonexistent (deleted references, revision 3):** `_resolve_section_names` (`grep -rn "_resolve_section_names" src/` → empty); `SectionInfo.watermark_gid` (`grep -rn "watermark_gid" src/` → empty)
- Name-index helper (also `name`-dependent): `src/autom8_asana/dataframes/section_persistence.py:213-215` (`get_section_name_index`)
- Delta-apply failure swallow (D4): `src/autom8_asana/dataframes/builders/freshness.py:270-281`
- Warm BROAD-CATCH (D6): `src/autom8_asana/dataframes/builders/progressive.py:379`
- Sync reader / sync `main()` (D2): `src/autom8_asana/metrics/freshness.py:140`, `src/autom8_asana/metrics/__main__.py:490,826`
- Async manifest reader (D2): `src/autom8_asana/dataframes/section_persistence.py:395` (`get_manifest_async`)
- Superseded definition: ADR-001 §Decision (delivery contract retained)
- QA gate (revision-2 driver): `.ledge/reviews/QA-freshness-verification-recency-gate.md`

---

*Authored by architect, 2026-05-27. Revised (revision 2) 2026-05-27 to clear the
QA NO-GO gate. Revised (revision 3) 2026-05-27 to close the sole BLOCKING gap from
the QA re-QA (revision 2): the D1/D7 re-seed. The fictional `_resolve_section_names`
reference is deleted and replaced with a source-verified re-seed (`Section.name`
from `_list_sections()`, `progressive.py:508` / `models/section.py:39`, threaded
into `_probe_freshness`); the re-seed-window alarm-suppression decision is added
(§Decision-7a, advisory-until-first-warm, no backfill); D8 (false-CLEAN wording
narrowed to watermark-bearing sections) and D9 (`watermark_gid` reference removed)
are folded in. Amends ADR-001. Evidence grade MODERATE (self-authored spike N=1 +
rite-disjoint QA gate corroboration; the named-section, re-seed-source, prober-blind-spot,
and nonexistent-symbol findings are STRONG-within-gate via deterministic prod/source
probes — `grep` exit codes + file:line reads; full STRONG requires the QA-gate-2
post-build prod re-probe per self-ref-evidence-grade-rule). Revision 3 makes the D1
re-seed real and located; revision 2 bound D1 (named sections functional requirement)
and D3 (prober blind spot fixed in-scope) and resolved QA D2/D4/D6.*
