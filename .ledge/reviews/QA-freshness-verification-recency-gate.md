---
type: review
artifact_type: QA-gate
initiative_slug: freshness-last-verified-at
phase: pre-build-validation
authored_by: qa-adversary
authored_on: 2026-05-27
status: complete
validates:
  - ADR-006-freshness-equals-verification-recency.md
  - freshness-verification-recency.tdd.md
  - .sos/wip/SPIKE-freshness-last-verified-at.md
verdict: NO-GO (conditional — 2 must-fix-first design defects)
re_qa_revision_2_verdict: CONDITIONAL-GO for /build (D1 re-seed path is the sole remaining BLOCKING gap; one build-carried condition)
re_qa_revised_on: 2026-05-27
evidence_grade: MODERATE
evidence_rationale: >
  Findings are grounded in direct source inspection (file:line) and live prod
  S3 manifest probes (autom8-s3, offer 1143843662099250 + unit 1201081073731555).
  Self-ref ceiling per self-ref-evidence-grade-rule: this is a single QA pass,
  not multi-rite corroboration. The prod-manifest null-name finding is STRONG
  (deterministic, re-runnable probe, 100% across both prod entities); the
  design-soundness findings are MODERATE (source-grounded but single-reviewer).
---

# QA Gate — Verification-Recency Freshness Signal (ADR-006 / TDD)

## Verdict: NO-GO for /build (conditional)

**Two must-fix-first design defects** block proceeding to implementation as the
design currently stands. Both are *design* defects, not implementation bugs —
they cannot be discovered or fixed in code review of an implementation that
faithfully follows the TDD, because the TDD itself is internally consistent but
rests on a false premise about prod state and contains an unaddressed
architectural seam. Fixing them requires amending the ADR/TDD, then /build.

The redefinition is **directionally correct and worth shipping** — the spike's
core insight (verification-recency ≠ mutation-recency; dropped-coverage must be
visible) is sound and empirically demonstrated. This is not a NO-GO on the
*idea*. It is a NO-GO on the *current design* because the join the whole signal
depends on **does not resolve against any production manifest that exists today**.

---

## Defects (severity-ranked)

### D1 — CRITICAL — The name↔GID join resolves to ZERO sections on every production manifest. The feature is inert on prod.

**Severity: Critical. Priority: P0 (blocks /build).**

The TDD §2.3 step 3 scopes the `verification_age` denominator by joining the
classifier's active section *names* against `SectionInfo.name`:

> "a manifest entry is in-scope iff `info.name` (case-normalized) ∈ `active_names`.
> The manifest carries `SectionInfo.name` (`:90`), which is the join key."
> — TDD §2.3 step 3

**Live prod evidence (verify, don't trust):**

```
project 1143843662099250 (offer): total=34  name_present=0  name_null=34  (100%)
project 1201081073731555 (unit):  total=17  name_present=0  name_null=17  (100%)
```
(Probed 2026-05-27 against `s3://autom8-s3/dataframes/{gid}/manifest.json`.
last_verified_at present on 0/34 and 0/17, as expected pre-implementation.)

**Every section in both production entity manifests has `name: null`.** The join
key the entire denominator-scoping mechanism depends on is universally absent in
production.

**Root cause (file:line):** `SectionInfo.name` is populated *only* at manifest
creation (`progressive.py:407-415`, via `create_manifest_async` →
`section_persistence.py:372` `SectionInfo(name=names.get(gid))`). But every
subsequent section completion goes through `update_manifest_section_async` →
`mark_section_complete` (`section_persistence.py:163-178`), which **replaces**
`self.sections[section_gid]` with a brand-new `SectionInfo(...)` constructed
from `status, rows, written_at, watermark, gid_hash` — and **no `name`**. So the
first time any section is marked complete after creation (i.e. always, in steady
state), its `name` is wiped to the `None` default. This is a pre-existing
defect; the new feature is the first consumer to depend on the wiped field.

**Why this defeats the feature, not just an edge case:** the TDD's own degrade
path (§2.3 step 4 / T9) says: *"If no in-scope section can be resolved (... join
yields empty), degrade to the ADR-001 mutation-axis signal."* Because the join
yields empty on **100% of prod manifests**, the new `verification_age` signal
**never computes** in production. It silently degrades to exactly the `62d`
mutation signal ADR-006 set out to replace. The feature ships, passes its unit
tests (which build manifests with names populated), and does nothing on prod —
a false-GREEN of the worst kind: the alarmable SLI is permanently absent and the
operator sees the old false-stale number they were told would be fixed.

**The TDD mis-classifies this as a Medium risk.** TDD §5 row 1 lists "manifest
`info.name` null" with mitigation "sections with null name fall to the degrade
path ... log join-miss count." That mitigation IS the bug: it treats null-name
as a per-section exception when it is the *universal steady state*. The
"join-miss count" it proposes to log would read 34/34 and 17/17 — i.e. total
failure logged as observability rather than caught as a blocker.

**Must-fix-first.** The fix is not in the freshness reader — it is upstream:
either (a) preserve `name` across `mark_section_complete` (carry it forward from
the prior `SectionInfo`), or (b) re-point the join to a key that survives —
note `SectionManifest.get_section_name_index()` (`section_persistence.py:208-210`)
*also* depends on `info.name` and is therefore equally broken today. The clean
fix is (a): stop wiping `name` on completion. Until `name` is reliably present on
prod manifests, the join-based denominator cannot work. This must land **in the
same change** (or as a prerequisite) — shipping the reader re-point without it
produces a feature that is inert in production.

---

### D2 — HIGH — Reader re-point requires async manifest I/O in a synchronous CLI path; the TDD specifies no design for crossing that seam.

**Severity: High. Priority: P0 (blocks /build).**

The current freshness reader (`metrics/freshness.py:140-263`,
`FreshnessReport.from_s3_listing`) is **synchronous** — it lists S3 parquet keys
via the boto3 paginator and never reads the manifest. It is invoked from the
**synchronous** default-metric path `main()` (`__main__.py:490`, reader call at
`:826`). The only `asyncio.run` in `__main__.py` is the *force-warm* `_delegate`
path (`:376,:487`), which is a different code path.

The TDD §2.3 reader re-point requires the reader to newly:
1. Resolve the classifier (sync — `CLASSIFIERS.get`, fine),
2. **Load the manifest** — but the only manifest reader is `get_manifest_async`
   (`section_persistence.py:390`), which is **async**, and the underlying
   `storage.load_json` (`storage.py:192,:1119`) is async-only. No synchronous
   manifest reader exists.
3. Compute `min(last_verified_at)`.

The TDD does not address how an async manifest read is introduced into the
synchronous `main()` emission path at `__main__.py:826`. Options (wrap in
`asyncio.run`, add a sync manifest reader, refactor `main` to async) each carry
distinct risk and the TDD picks none. A principal engineer cannot implement
§2.3 "without architectural questions" (TDD §6 claims they can) — this is the
architectural question. Nesting `asyncio.run` inside an already-running loop
(if the metric path is ever invoked from async context) raises
`RuntimeError: asyncio.run() cannot be called from a running event loop`; the
TDD's silence here is a latent defect.

**Must-fix-first.** The TDD must specify the sync/async bridge for the reader.
This is a design gap, not an impl detail.

---

### D3 — HIGH — Prober content-detection blind spot makes the new signal *false-fresh* in the dangerous direction. Stamping a false-CLEAN claims verification that did not occur.

**Severity: High. Priority: P1 (see "blind-spot assessment" — gating analysis).**

**Empirically confirmed live** (spike Interop section; ADR-006 §Deferred;
`freshness.py:191-217`). The `modified_since` gate is `len(modified_tasks) > 1`
(`freshness.py:204`) with `limit=2` (`:198`). Because `modified_since` is
inclusive (`>=`), the watermark task is always returned as a false-positive, so
a single returned task is treated as CLEAN. Consequence: **editing the exact
watermark task, or any edit in a single-task section, returns exactly 1 task →
CLEAN → real change MISSED.** This bit the spike's own revert-heal (spike line
72-73).

**Interaction with the new signal (the sharp issue):** under ADR-006 §Decision-1,
*every* verdict ≠ PROBE_FAILED stamps `last_verified_at = now`. A false-CLEAN is
a verdict of CLEAN — so the blind spot causes the section to be **stamped as
freshly verified** while its cached content is provably stale. The new
`verification_age` reports the section as minutes-fresh and alarmable-OK, when in
truth a genuine change went undetected.

This is **strictly worse than the old signal in this scenario.** The old
mutation signal (`parquet mtime`) is *honest about what it measures* — it never
claimed the data was verified-correct, only that bytes hadn't changed. The new
signal makes a positive *correctness* claim ("verified against Asana at HH:MM")
that the blind spot falsifies. ADR-006 §Why-this-matters names false-fresh as
"the dangerous direction"; this design introduces a new false-fresh channel that
did not exist before, and the ADR's §Neutral hand-wave ("even with the blind
spot, a CLEAN verdict is still a legitimate verification event worth stamping")
is **wrong**: a false-CLEAN is not a legitimate verification event — it is a
verification *failure* mis-recorded as success.

**Defect cluster (probing the neighborhood, not stopping at the first find):**
D3 has a sibling at the *delta-application* layer —

### D4 — MEDIUM — Stamp fires on `verdict ≠ PROBE_FAILED` even when delta application FAILED. Second false-fresh path; PROBE_FAILED invariant under-scoped.

**Severity: Medium. Priority: P1.**

ADR-006 §Decision-5 / TDD T3 protect against `PROBE_FAILED` advancing the stamp.
But the stamp logic (TDD §2.2) keys on `r.verdict`, computed at *probe* time,
**before** delta application. A `CONTENT_CHANGED` / `STRUCTURE_CHANGED` /
`NO_BASELINE` section is routed to `apply_deltas_async` (`progressive.py:356-365`),
which can **fail to apply** the delta — `_apply_section_delta` failures are caught
and logged (`freshness.py:270-281` `freshness_delta_section_failed`), the count
is simply not incremented, and **no exception propagates**. The TDD stamp loop
then stamps that section `last_verified_at = now` anyway, because its *verdict*
was not PROBE_FAILED.

Result: a section where a change WAS detected but the cache update FAILED gets
marked "verified-current." The load-bearing invariant (probe-failed ⇒ no stamp)
is too narrow: the real invariant should be **"a section is stamped only if its
cached content is confirmed to match live Asana at stamp time"** — which means a
failed delta-apply must also suppress the stamp (or stamp must move to *after*
successful persistence, gated on apply success). The TDD stamps on verdict, not
on reconciliation success. This is a design correction, cheap if made now.

---

### D5 — LOW — Re-load-authoritative-manifest no-clobber rationale (T8) rests on an imprecise model of `get_manifest_async`; verify the contract holds.

**Severity: Low. Priority: P2 (verify during impl, not a blocker).**

TDD §2.2 instructs: re-load via `get_manifest_async` to get a "fresh copy" so
stamping doesn't clobber delta writes. But `get_manifest_async`
(`section_persistence.py:402-403`) returns the **cached** object
(`self._manifest_cache`) when present — and `apply_deltas_async` →
`write_section_async` → `update_manifest_section_async` **mutates and re-stores
that same cached object** (`:479`). So the "re-loaded" manifest is (in the warm
process) the *same in-memory object* that already has delta updates applied —
not an independent S3 re-read. The no-clobber outcome is achieved, but for a
different reason than the TDD states (shared-cache mutation, not fresh S3 read).

Two consequences to verify in impl:
- The mechanism works **only** because of cache coherence within one process. If
  the cache were ever bypassed/cleared between delta-apply and stamp, the stamp
  would re-read pre-delta S3 state and clobber. Low likelihood (same call stack),
  but the TDD's stated rationale would not protect against it — the *real*
  protection is incidental.
- `mark_section_complete` (`:172-178`) constructs a fresh `SectionInfo` **without
  `last_verified_at`** (same wipe as D1's `name` wipe). So a section that is
  CONTENT_CHANGED in warm N has its prior `last_verified_at` **wiped** by the
  delta write, then re-stamped by the new stamp block in the same warm — net OK
  for that warm, but any code path that completes a section *without* reaching
  the stamp block (e.g. delta-apply path that marks complete then the stamp block
  is skipped by the BROAD-CATCH, see D6) loses the prior stamp silently.

---

### D6 — LOW/MEDIUM — Stamp block under the warm BROAD-CATCH: a stamp-phase exception silently zeroes ALL stamping for that warm while the warm reports success.

**Severity: Medium (observability/silent-degradation). Priority: P2.**

TDD §2.2 places the stamp block "inside the existing try/except (`:415`
BROAD-CATCH degrade)" — actually the relevant catch is `progressive.py:379`
(`_probe_freshness` BROAD-CATCH: degrade → `return 0, 0`). If `get_manifest_async`
or `_save_manifest_async` raises during the stamp phase (S3 5xx, throttling), the
catch swallows it and `_probe_freshness` returns `(0, 0)` — **no sections
stamped this cycle, warm reports success.** TDD T10 asserts "warm completes,
failure logged, not raised" — which is the *intended* graceful degrade, BUT the
consequence on the new signal is not analyzed: a stamp-phase failure means
`last_verified_at` does not advance for ANY section that warm, so on the *next*
read the `verification_age` will (correctly) climb — except that the operator
cannot distinguish "stamp write failed" from "genuinely not verified." The
degrade is acceptable *as long as* the stamp-failure is alarmable separately.
TDD §2.2 logs `section_last_verified_stamped` on success but specifies no log/
metric on the stamp-phase-failure branch. Add an explicit stamp-failure metric so
silent stamp starvation is observable. Low-cost; specify before /build.

---

## Adversarial Target Assessment (the 5 requested probes)

### Target 1 — Design soundness of the name↔GID join. **FAIL → D1 (Critical).**
The TDD correctly *flagged* the join as the primary risk, but mis-graded it
(Medium) and mis-modeled prod state (assumed names present-with-exceptions; prod
reality is names-universally-null). Sections present in classifier but absent
from manifest, or vice versa: with names null, *all* manifest entries are
"absent from the join" — the worst case is the only case. Null-name handling
exists (degrade) but the degrade is the steady state. **Join is not safe; it is
inert.**

### Target 2 — PROBE_FAILED invariant. **PARTIAL → D4, D6.**
The literal invariant (PROBE_FAILED verdict ⇒ no stamp) is correctly specified
and is honored by the verdict check (TDD §2.2 `if r.verdict == PROBE_FAILED:
continue`). BUT the invariant is **under-scoped**: (a) failed delta-application
still stamps (D4), and (b) a stamp-phase exception skips the whole save under the
BROAD-CATCH (D6) — not a wrong-stamp, but a silent no-stamp the warm reports as
success. The "whole manifest save skipped" path the prompt asked about is real
(D6): one exception in the stamp block degrades the entire stamp cycle to zero.

### Target 3 — Prober blind spot vs the new signal. **FAIL → D3 (High). See gating analysis below.**

### Target 4 — Legacy / empty / inactive / edge sections.
- **Missing `last_verified_at` (legacy):** handled — falls back to `written_at`
  (TDD §2.3 backfill), self-heals next probe. Verified prod manifests have
  `last_verified_at` absent on 100% of sections today, so **every section is on
  the legacy/backfill path at rollout** — meaning at first read post-deploy the
  signal is `now − min(written_at)` over in-scope sections... except in-scope is
  empty (D1), so it degrades to mutation-axis anyway. The two defects compound.
- **Empty (0-row) / inactive sections:** *intended* to be excluded via
  `active_sections()` scoping (T6). Mechanism is sound **in principle** but
  inoperative in practice because the join (D1) excludes everything. Cannot
  confirm exclusion works on prod until D1 is fixed — T6 passes only on
  synthetic name-populated manifests.
- **PENDING/FAILED/never-probed sections:** `probe_all_async` only probes
  `get_complete_section_gids()` (`freshness.py:121`). A never-completed section
  is never probed, never stamped — correctly ages if in-scope (good, this is the
  dropped-coverage signal). No defect; behaves as designed.

### Target 5 — Backward compatibility. **PASS.**
`SectionInfo.model_config = {"use_enum_values": True}` (`:98`) does **not** set
`extra="forbid"`; pydantic v2 default is `extra="ignore"`. Verified: old code
deserializing a manifest carrying `last_verified_at` ignores the unknown field
cleanly (no validation error). Mid-rollout, an old-code deploy reading a
new-code-written manifest will not break. The round-trip is lossy for old code
(old code re-saving drops the field), but new code self-heals it on next probe.
No `schema_version` bump on the manifest is needed (TDD §2.1 correct). **Safe.**
Minor smell (non-blocking): the field name `last_verified_at` collides
semantically with the unrelated `cache/models/freshness_stamp.py:64`
`FreshnessStamp.last_verified_at` — two freshness subsystems, identical field
name, different meaning. Cognitive-load risk for future maintainers; recommend a
disambiguating docstring on the manifest field.

---

## Blind-Spot Assessment (Target 3 — does the prober blind spot gate the redefinition?)

**Question:** can the freshness redefinition ship before the prober blind spot is
fixed, or must they ship together?

**Finding:** the blind spot **does not invalidate the verification-recency *signal
mechanism*** (stamp-at-probe, scope-to-active, dropped-coverage-visible all stand
on their own). The ADR is correct that the two are *orthogonal in mechanism*. But
the ADR's conclusion that the blind spot is therefore **safely deferrable is
wrong on the consequence axis**, for one specific reason:

> The redefinition changes the *meaning* of the signal from "bytes changed N ago"
> (a mutation claim, always honest) to "verified-correct N ago" (a correctness
> claim). The blind spot falsifies the *correctness* claim. Pre-redefinition, the
> blind spot caused a missed update but the freshness number never lied about
> correctness (it only ever claimed byte-recency). Post-redefinition, the same
> blind spot causes the freshness number to **assert a verification that did not
> happen.** The redefinition *promotes* the blind spot from "missed-update bug" to
> "the alarmable SLI is actively lying."

**Disposition: the blind spot is NOT a same-change must-fix, but it IS a
must-fix-before-the-signal-is-trusted-as-alarmable.** Concretely:

- The blind spot may remain a **tracked follow-up** (its own initiative, as
  ADR-006 §Deferred proposes) **IF** the redefinition ships `verification_age` as
  **non-alarmable / advisory** until the blind spot is closed. Stamping is fine;
  *alarming on it* is not, while a known false-CLEAN channel exists.
- The redefinition may NOT ship `verification_age` as the **alarmable** SLI
  (ADR-006 §Decision-4, `--strict` promotion TDD §2.4) while the blind spot is
  open. Doing so wires `--strict` exit codes and operator alarms to a signal with
  a known, live-confirmed false-fresh channel — alarm fatigue's evil twin:
  alarm *absence* on real staleness.

This is the sharpest interaction and it modifies the ADR's deferral decision:
**deferral is conditional on the signal being advisory-only at first ship.**

---

## Edge Cases Enumerated

| # | Edge case | Designed behavior | QA finding |
|---|-----------|-------------------|------------|
| E1 | All section names null (prod reality) | degrade to mutation-axis | **D1: feature inert; not an edge case, it's the prod baseline** |
| E2 | Classifier missing for entity_type | omit verification_age, exit 0 | OK (T9) — but masks D1 (same degrade output) |
| E3 | Manifest unavailable / parse fail | degrade | OK; `get_manifest_async` returns None on parse fail (`:415-417`) |
| E4 | last_verified_at None (legacy) | fall back to written_at | OK in principle; 100% of prod sections on this path at rollout |
| E5 | Single-task section content edit | should detect CONTENT_CHANGED | **D3: false-CLEAN → false stamp** |
| E6 | Edit to exact watermark task | should detect | **D3: false-CLEAN → false stamp** |
| E7 | CONTENT_CHANGED but delta apply fails | should NOT stamp | **D4: stamps anyway** |
| E8 | Stamp-phase S3 exception | graceful degrade | D6: degrades silently to 0 stamps, warm reports success, no failure metric |
| E9 | Concurrent warm between delta + stamp | last-writer on stamp; self-heal | Low risk; D5 notes the no-clobber is incidental (shared cache), not by S3 re-read |
| E10 | Empty/cold/inactive section with stale stamp | excluded by active scope | Mechanism sound, untestable on prod until D1 fixed |
| E11 | Old code reads new manifest (mid-rollout) | extra-ignore, no break | **PASS** (Target 5) |
| E12 | New field name collides with cache FreshnessStamp | n/a (separate module) | No code conflict; doc/cognitive smell only |

---

## Test-Coverage Assessment (Coverage Theater check)

The TDD's 10 test cases (T1-T10) are well-shaped as unit tests but **every one of
them constructs a manifest with `name` populated** (they must, to exercise the
join). None of them reproduce the prod state of `name = null` universally.
Per dk-testing-methodology: this is a **coverage-theater risk** — the suite would
report GREEN on a feature that is inert in production, because the test fixtures
encode an assumption (names present) that production violates 100%. **Add a test
case T11: "manifest with all names null (prod-realistic) → verification_age
absent, degrades to mutation-axis, AND a loud signal/metric fires that the
denominator resolved empty"** — so the inert-feature condition is a *detected,
alarmed* state rather than a silent degrade. Without T11, D1 would have shipped
GREEN.

---

## Self-Referential Evidence Discipline

- **D1 prod-manifest finding: STRONG within this gate** — deterministic,
  re-runnable probe (`aws s3 cp ... | python3`), 34/34 + 17/17, both prod
  entities. Not self-referential (probes external prod state, not this review's
  own claims).
- **D2-D6: MODERATE** — source-grounded with file:line anchors, but single-
  reviewer, single-pass. Per self-ref-evidence-grade-rule, a QA gate evaluating
  a design does not self-certify to STRONG; STRONG would require an independent
  re-probe (a second rite, or a principal-engineer dry-run that hits the
  sync/async seam D2 in code).
- The ADR's own grade (MODERATE, self-authored spike, N=1) is **correctly
  declared**. This gate does not upgrade it — it surfaces that the spike's
  evidence, while real, was gathered on a manifest path that masked D1 (the spike
  exercised live warm→probe, which re-creates name only if the build path passes
  section_names — and the spike's snapshot harness read its own freshly-written
  manifest, not a steady-state prod manifest where names are already wiped).

---

## GO / NO-GO

**NO-GO for /build** as the design currently stands.

**Conditions to convert to GO (must-fix-first, in priority order):**

1. **[BLOCKING — D1]** Amend the design to make the in-scope join resolvable on
   production manifests. Required: stop `mark_section_complete` /
   `update_manifest_section_async` from wiping `SectionInfo.name` (carry it
   forward), OR re-base the denominator on a key that survives completion. Add a
   data-state assertion / startup probe that the join resolves > 0 sections on a
   real manifest before the signal is considered live. Without this, the feature
   is inert in prod (degrades to the exact 62d signal it replaces).

2. **[BLOCKING — D2]** Specify the sync→async bridge for the reader manifest
   read in the synchronous `__main__.py:826` emission path. The TDD's "no
   architectural questions" claim (§6) is false until this is resolved.

3. **[CONDITIONAL — D3]** Either fix the prober blind spot in the same change,
   OR ship `verification_age` as **advisory-only / non-alarmable** (no `--strict`
   promotion, no CloudWatch alarm wiring) until the blind spot is closed in its
   tracked follow-up. The blind spot may be deferred; **alarming on a signal it
   can falsify may not.** This amends ADR-006 §Decision-4's "alarmable" framing.

4. **[SHOULD-FIX — D4]** Gate the stamp on delta-application success, not on
   probe verdict, so a failed reconciliation does not mark a section
   verified-current.

5. **[SHOULD-FIX — D6]** Add an explicit stamp-phase-failure metric so silent
   stamp starvation under the BROAD-CATCH is observable.

6. **[SHOULD-FIX — test]** Add T11 (all-names-null prod-realistic fixture +
   empty-denominator alarm) to prevent the coverage-theater GREEN that would
   otherwise hide D1.

**Acid test:** *"If this goes to production and fails in a way I didn't test,
would I be surprised?"* — No. It would ship GREEN, emit the old 62d number under
a new label, and the alarmable SLI the ADR promised would silently never exist.
That is precisely the false-fresh / false-stale failure the ADR set out to
prevent, reintroduced by an untested premise about prod manifest state.

---

## Documentation / Cross-Rite Handoff Impact

- **Documentation impact:** YES — user-facing `--json` envelope gains a
  `verification` block + `schema_version 1→2` bump (TDD §2.4). The
  default-mode stdout gains a `verification age:` line. Docs for the metrics CLI
  must be updated. Gate D3 affects what operators are told to alarm on — docs
  must NOT instruct alarming on `verification_age` until D3 is resolved.
- **Security handoff:** NOT required — TDD `impact: low` is correct
  (no auth/PII/crypto/external-integration/new-endpoint; one additive manifest
  field, one stamp site, one reader re-point). Verified against the change set.
- **SRE handoff:** RECOMMENDED — the change adds one manifest read + conditional
  write per warm (per-warm S3 I/O increase, bounded), introduces a new alarmable
  SLI with cadence-tied thresholds, and D6 introduces a new silent-degradation
  mode worth a CloudWatch alarm. This crosses the SERVICE-altitude line for SRE
  awareness even though complexity is otherwise low.

---

*QA gate authored by qa-adversary, 2026-05-27. Evidence: direct source
inspection (file:line anchors throughout) + live prod S3 manifest probes
(autom8-s3, offer 1143843662099250 + unit 1201081073731555). Verdict NO-GO
(conditional). MODERATE grade per self-ref-evidence-grade-rule; D1 prod-state
finding is STRONG-within-gate (deterministic external probe).*

---

# Re-QA (revision 2) — 2026-05-27

Re-gate of ADR-006 revision 2 + TDD revision 2 against the revision-1 defect
baseline above. Mandate: attack the revision, do not rubber-stamp. All findings
re-grounded against live source (verified file:line) and a fresh live prod S3
re-probe. Evidence discipline: prod-state findings are STRONG-within-gate
(deterministic re-runnable probe); design-soundness dispositions are MODERATE
(single-reviewer, single-pass, per self-ref-evidence-grade-rule).

## Fresh prod re-probe (2026-05-27, re-run of the D1 baseline)

```
offer (1143843662099250): total=34 complete=34 name_present=0 name_null=34  last_verified_at_null=34   schema_version=1.4.0
unit  (1201081073731555): total=17 complete=17 name_present=0 name_null=17  last_verified_at_null=17   schema_version=1.5.0
```
(probe: `aws s3 cp s3://autom8-s3/dataframes/{gid}/manifest.json | python3`.)
**The prod fleet is UNCHANGED from the revision-1 baseline.** Both entities still
carry `name=null` on 100% of sections, ≥2 sections each, all COMPLETE. This is
the surface every revision-2 claim must survive. Additional probe finding (NEW,
material to D3): **watermark coverage is partial** — offer has 21/34 sections
with `watermark=null`; unit has 4/17. The §2.5 prober fix lives entirely inside
the `if section_info.watermark is not None` branch (`freshness.py:192`), so it is
inert for those 21+4 sections (see D3 disposition).

## Per-defect disposition

### D1 (was CRITICAL) — PARTIAL. The design is correct-by-intent but the carry-forward heals NOTHING on the existing prod fleet, and the TDD's re-seed mechanism cites a function that does not exist. This is the sole remaining BLOCKING gap.

**Design direction: ACCEPTED.** Healing the wipe at the source (carry `name` +
`last_verified_at` forward in `mark_section_complete`), keeping name-based scoping,
rejecting the GID-resolver, and the ≥2-section loud-error data-state assertion
(§2.6, ADR §Decision-7) are all the right calls. The `mark_section_complete`
wipe is verified real: `section_persistence.py:177-183` constructs a fresh
`SectionInfo` from only `status, rows, written_at, watermark, gid_hash` — `name`
and `last_verified_at` default to `None`. `get_section_name_index`
(`:213-215`) is confirmed `info.name`-dependent. The carry-forward edit in TDD
§2.2.1 is correctly shaped.

**BUT the carry-forward is inert on the existing prod fleet, and the TDD's escape
hatch is fictional.** The carry-forward reads `prior.name`. On every current prod
section `prior.name is None` (re-probed above), so the first post-deploy
completion carries `None → None`. The signal stays inert until `name` is
re-seeded from a real source. TDD §2.2.1 claims the re-seed is "automatic" because
"`_resolve_section_names` runs at warm entry (see §2.6 assertion, which forces
this path)." **Three source-grounded problems:**

1. **`_resolve_section_names` does not exist.** `grep -rn "_resolve_section_names"
   src/` returns only the two TDD-quoted mentions inside
   `section_persistence.py` *docstring/param* lines (`:358,:367,:372`) for the
   UNRELATED `create_manifest_async(section_names=...)` param — there is no
   function by that name and no warm-entry name-resolution pass.
2. **The only name-population path fires solely on first creation.**
   `create_manifest_async` (`:352-377`, `SectionInfo(name=names.get(gid))` at
   `:377`) is called from exactly one site — `_ensure_manifest`
   (`progressive.py:442-452`) — and only inside `if manifest is None:`. For an
   existing prod manifest, `manifest` is NOT None, so `create_manifest_async` is
   never called again and `section_names` (built from `s.name` at
   `progressive.py:443-445`) is never re-threaded.
3. **`mark_section_complete` takes no `name` argument.** Its sole prod caller
   (`update_manifest_section_async`, `section_persistence.py:473-476`) passes only
   `rows, watermark, gid_hash`. There is no plumbing to deliver a fresh name to
   the completion site. The §2.6 assertion *detects* the null-name state and fires
   `section_name_contract_violation` — but **detection is not a re-seed.** It
   converts the silent false-GREEN into a loud alarm (good, and exactly what the
   prior gate demanded), but it does not by itself make the signal compute.

**Prod-fleet alarm-storm assessment (THE gate condition, item 1).** With the
design as written and no additional re-seed plumbing:

- On the CURRENT prod manifest (≥2 sections, all `name=null`), the §2.6 assertion
  **correctly fires the loud `section_name_contract_violation`** rather than
  silently degrading to the 62d mutation signal. The original D1 false-GREEN
  ("alarmable SLI permanently absent, operator sees old number") is **defeated** —
  this is a genuine improvement and the single most important thing the revision
  got right.
- **However, the violation will fire on EVERY metrics invocation until a re-seed
  lands**, because no shipped code path re-populates `name` on an existing
  manifest. `mark_section_complete`'s carry-forward propagates `None` indefinitely.
  This is a **NEW operational landmine the revision introduces**: trading a silent
  false-GREEN for a persistent alarm-storm that no warm can clear on its own.
  It is the better failure (loud beats silent), but it is not "fixed" — it is
  "fail loud, forever, until a separate re-seed is built."
- The TDD half-acknowledges this in §2.2.1 ("a one-time re-seed is needed" +
  "Verify during impl: confirm the warm path … has the section name available …
  the impl MUST thread the name through `mark_section_complete`'s caller") and
  §5 risk row 2. But it is filed as a flagged impl seam, while it is in fact the
  **load-bearing precondition for the entire feature to be non-inert on prod.**
  A principal engineer who implements §2.2.1 literally (carry `prior.name`
  forward) and trusts the fictional `_resolve_section_names` will ship a feature
  that alarm-storms `section_name_contract_violation` on the live fleet from the
  first invocation and never computes `verification_age`.

**Disposition: PARTIAL — BLOCKING for /build until the re-seed path is named as
an explicit, in-scope work item with a concrete source for the name.** The
re-seed is not optional and is not a "verify during impl" footnote; it is a
required change. The cheapest correct form: thread the section name into
`mark_section_complete` (add a `name` param, default to carry-forward
`prior.name` when not supplied) AND have `update_manifest_section_async`'s caller
(or `_probe_freshness` / the warm loop) supply the classifier/section-listing
name on completion so the first post-deploy warm re-seeds. The §2.6 assertion is
the correct backstop, but the build MUST deliver the re-seed, not just the
detector. Without it, GO is unsafe.

### D3 (was HIGH) — RESOLVED on the watermark branch; residual coverage gap flagged (not a regression).

The §2.5 watermark-task-identity fix is **correct for the two live-confirmed
misses** and does NOT introduce a false-positive storm:

- **Catch (single-task edit / watermark-task edit):** verified against
  `freshness.py:191-204`. Current gate is `len(modified_tasks) > 1` with `limit=2`
  and inclusive `modified_since` (`>=`), so the boundary task alone → CLEAN
  (the bug). The fix fetches `opt_fields=["gid","modified_at"]` and flags
  `CONTENT_CHANGED` when the single returned task's `modified_at > watermark`
  (strict). An edited watermark task gets a new `modified_at` strictly after the
  stored watermark → caught. Correct.
- **Negative case (no storm), traced explicitly:** `watermark` is the max
  `modified_at` at last build (set by `apply_deltas_async` step 6, manifest
  `SectionInfo.watermark`). An UNCHANGED boundary task returns `modified_at ==
  watermark`. The fix uses strict `>`, so `==` → `changed=False` → stays CLEAN.
  **No false-positive `CONTENT_CHANGED` on the steady-state boundary task.** This
  is the critical no-storm property and it holds. T13's contrast assertion
  (unchanged boundary stays CLEAN) is the right guard.
- **`watermark_gid` (branch c):** `grep` confirms NO `watermark_gid` field exists
  on `SectionInfo` anywhere in `src/`. The TDD correctly marks branch (c) as
  OPTIONAL and says the `modified_at > watermark` test (branch b) alone closes
  both confirmed misses. **Impl caveat (flag, not block):** the §2.5 code block as
  written references `section_info.watermark_gid` — if a principal engineer copies
  it verbatim without adding the field, it raises `AttributeError`. The TDD says
  to "pick the minimal sufficient form" and omit branch (c). Build must either
  add the field or delete the branch; do not ship the literal block.
- **RESIDUAL GAP (NEW, MEDIUM-LOW, prod-grounded):** the §2.5 fix is entirely
  inside `if section_info.watermark is not None`. The re-probe shows **21/34
  offer + 4/17 unit sections have `watermark=null`.** For those sections the
  modified_since refinement never runs at all (pre-existing) — a content edit
  that does not add/remove tasks (so the gid_hash is unchanged) is still read as
  CLEAN and would stamp `last_verified_at`. This is NOT a regression (it is the
  pre-existing hash-only behavior for null-watermark sections), and the stamp it
  produces is no more false than the old mutation signal for those sections — but
  it means the "no remaining known false-CLEAN channel" claim in ADR §Decision-4
  / TDD §2.4 is **slightly overstated**: the channel is closed for
  watermark-bearing sections, not universally. **Disposition: acceptable to ship
  alarmable, but the ADR's absolute "no remaining false-CLEAN channel" wording
  should be narrowed to "no false-CLEAN channel for watermark-bearing sections;
  null-watermark sections retain the pre-existing hash-only detection."** This is
  a documentation-accuracy fix, not a blocker — the prior gate's alarmability
  concern (D3) is materially resolved for the dominant case.

### D2 (was HIGH) — RESOLVED.

The sync→async bridge is correctly specified and the entry-point premise is
verified. `main()` is a synchronous `def main()` (`__main__.py:490`), invoked
directly at `:932` (`main()`) with **no `asyncio.run` wrapper** at the entry.
The only `asyncio.run` is inside `_delegate` (`:487`), a separate force-warm
code path. The reader call (`FreshnessReport.from_s3_listing`, `:826`) is in the
synchronous body. **Confirmed: no running event loop exists at the reader's
emission path**, so `asyncio.run(get_manifest_async(...))` is safe there. The
§2.3.1 guard (`asyncio.get_running_loop()` → if it raises `RuntimeError`, no loop
is running → `asyncio.run`; if a loop IS running, raise loudly rather than nest)
behaves correctly on this path: `get_running_loop()` raises → caught → `asyncio.run`
proceeds. The nested-loop `RuntimeError` the prior gate flagged is now impossible
to hit silently. Bridge choice (i) (thin sync wrapper, smallest blast radius) is
the right call over (ii)/(iii). **Fully resolved.**

### D4 (was MEDIUM) — RESOLVED.

The stamp now gates on `applied_gids` membership for delta-requiring verdicts
(§2.2, ADR §Decision-5c). Verified the underlying mechanics: `apply_deltas_async`
(`freshness.py:231-284`) swallows per-section failures (`:270-281`
`freshness_delta_section_failed`, count not incremented, no raise); the success
branch (`:282-283 elif outcome:`) knows the per-index outcome and can accumulate
applied GIDs. `_apply_section_delta` returns True only after
`update_manifest_section_async` (`:477,:485`) or returns False / raises on failure
(`:495`). So a failed delta → GID ∉ `applied_gids` → stamp block skips →
`last_verified_at` not advanced → `verification_age` correctly climbs. **Contract
change blast radius verified SAFE:** `apply_deltas_async` has exactly ONE caller
(`progressive.py:362`) and zero test callers; its return is used only for a log
field (`sections_delta_updated`). Changing `int → tuple[int, frozenset[str]]`
touches one site. T14 is a real guard. Resolved.

### D6 (was MEDIUM) — RESOLVED.

The stamp block stays under the warm BROAD-CATCH (`progressive.py:415`, verified
`return 0, 0` degrade) but now emits `section_last_verified_stamp_failed` on the
failure branch (§2.2, ADR §Decision-9). T10 is amended to assert the metric fires
(not merely "logged, not raised"). This makes silent stamp starvation alarmable
separately from the `verification_age` climb. Resolved.

### D5 (was LOW) — RESOLVED by the D1-a carry-forward.

Carrying `last_verified_at` forward in `mark_section_complete` (§2.2.1) closes the
silent-loss path: a CONTENT_CHANGED section's prior stamp survives the delta
write, and the stamp block re-stamps stamp-eligible sections. **Double-stamp /
stale-carry check (item 4): no leak.** For CLEAN sections, no `mark_section_complete`
runs (no delta), so carry-forward is irrelevant; stamp block stamps directly. For
applied-delta sections, carry-forward preserves the floor and the stamp block
overwrites to `now`. For failed-delta sections, carry-forward preserves the
last-known-good stamp and the stamp block correctly skips — the desired behavior.
No path produces a stale-but-advanced stamp. Resolved.

## NEW defects surfaced in revision 2

- **D7 (MEDIUM → BLOCKING-in-aggregate) — The D1 re-seed mechanism is fictional.**
  TDD §2.2.1 attributes the prod re-seed to `_resolve_section_names` "running at
  warm entry"; that function does not exist and no shipped path re-populates
  `name` on an existing manifest (see D1). Folded into the D1 BLOCKING condition.
- **D8 (LOW) — ADR/TDD overstate "no remaining false-CLEAN channel."** Null-
  watermark sections (21/34 offer, 4/17 unit, prod-confirmed) bypass the §2.5 fix.
  Narrow the wording; not a blocker (pre-existing behavior, no regression).
- **D9 (LOW) — §2.5 code block references a non-existent `watermark_gid` field.**
  Build must add the field or delete branch (c); shipping the literal block
  raises `AttributeError`. Impl seam, TDD already says "pick minimal sufficient
  form."

## Test-contract honesty (item 5) — would T11–T15 FAIL on unfixed code?

T11–T15 are specified but not yet implemented (this is a pre-build gate; tests
land in /build). Assessed as contracts against verified source:

- **T11 (all-null prod fixture → loud violation): REAL guard, load-bearing.** On
  unfixed code (no §2.6 assertion), an all-null ≥2-section manifest silently
  degrades to mutation-axis → T11's "violation FIRES" assertion fails. Genuinely
  catches the inert-feature GREEN. **Caveat:** T11 tests the *detector*, not the
  *re-seed* — it will pass once §2.6 fires the alarm, even if D1's re-seed is
  never built. So T11 GREEN does NOT prove the feature computes on prod; it proves
  the feature fails LOUD on prod. The build must not read T11-GREEN as
  "feature works on prod."
- **T12/T13 (watermark fixes): REAL.** On unfixed code (`len > 1` gate), a
  single-task / watermark-task edit returns 1 task → CLEAN → T12/T13's
  "CONTENT_CHANGED" assertion fails. T13's negative contrast (unchanged boundary
  stays CLEAN) guards against the no-storm property. Honest.
- **T14 (delta-fail no stamp): REAL.** On unfixed code (stamp on verdict), a
  failed-delta section is stamped → T14's "not advanced" assertion fails. Honest.
- **T15 (carry-forward survives completion): REAL.** On unfixed
  `mark_section_complete`, name/`last_verified_at` are wiped → T15's "retains"
  assertion fails. Honest. **Gap:** T15 asserts carry-forward of a *prior non-null*
  name; it does NOT cover the prod case where `prior.name is None` and a re-seed
  must supply it. Recommend a T16: "completion on a manifest with `prior.name=None`
  re-seeds `name` from the section source" — this is the test that would actually
  fail on the D1 re-seed gap. Without it, the suite can go GREEN while the feature
  alarm-storms on prod.

No coverage-theater in the specified contracts themselves; the theater risk is at
the boundary — T11/T15 as written do not exercise the prod re-seed, so they could
pass on a build that is still inert/alarm-storming. T16 closes that.

## GO / NO-GO for /build (revision 2)

**CONDITIONAL-GO for /build.** Five of six original defects (D2, D3, D4, D5, D6)
are resolved or materially resolved; the redefinition concept remains sound and
worth shipping. The revision converted the worst original failure (D1 silent
false-GREEN) into a loud, detected state — a real improvement. **One BLOCKING gap
remains:** the D1 prod re-seed path is fictional in the TDD, so as-written the
feature will alarm-storm `section_name_contract_violation` on the live fleet
forever and never compute `verification_age`.

**MUST-FIX-FIRST (BLOCKING — convert to clean GO):**

1. **[BLOCKING — D1/D7] Specify and build the `name` re-seed for existing prod
   manifests as an explicit in-scope work item.** Delete the reference to the
   non-existent `_resolve_section_names`. Concretely: add a `name` parameter to
   `mark_section_complete` (carry `prior.name` when not supplied), and have the
   completion caller (`update_manifest_section_async` / the warm probe loop)
   thread the classifier/section-listing name so the first post-deploy warm
   re-seeds null names. The §2.6 assertion stays as the backstop. Acceptance:
   after one full warm post-deploy on a prod-shaped (all-null) manifest, the join
   resolves >0 sections and `section_name_contract_violation` does NOT fire.

**BUILD-CARRIED CONDITIONS (must be satisfied during /build, verified at QA-gate-2):**

2. **[D9] Resolve the `watermark_gid` reference** in the §2.5 block — add the
   field or delete branch (c). Do not ship the literal block (AttributeError).
3. **[D8] Narrow the ADR/TDD "no remaining false-CLEAN channel" wording** to
   scope it to watermark-bearing sections; document the null-watermark hash-only
   residual (21/34 offer, 4/17 unit prod-confirmed).
4. **[test] Add T16** (completion with `prior.name=None` re-seeds name from the
   section source) so the suite fails on the D1 re-seed gap rather than going
   GREEN on an alarm-storming build. T11/T15 alone do not exercise the prod
   re-seed.

**CONDITIONS QA-GATE-2 MUST CARRY (post-build re-probe — this gate's STRONG
upgrade per self-ref-evidence-grade-rule):**

- Re-probe a real prod (or prod-shaped) manifest AFTER a full warm on the built
  code and confirm `name_present == total` (re-seed actually fired) and
  `verification_age` computes (join resolves >0). This is the deterministic
  external probe that upgrades the D1 disposition from PARTIAL to RESOLVED.
- Confirm `section_name_contract_violation` is wired to a metric/alarm and is
  silent on a healthy re-seeded manifest (no alarm-storm).
- Confirm T11–T16 actually fail on a deliberately-unfixed checkout (anti-theater).

**Acid test re-run:** *"If this goes to production and fails in a way I didn't
test, would I be surprised?"* — With condition 1 met: No surprise. With condition
1 unmet (build follows §2.2.1 literally): the feature would alarm-storm
`section_name_contract_violation` on the live fleet from the first invocation and
never emit `verification_age` — a loud failure, not the silent false-GREEN of
revision 1, but still a non-functional feature. That is why D1 remains BLOCKING.

## Documentation / Cross-Rite Handoff Impact (revision 2 delta)

- **Documentation:** unchanged from prior gate — `--json` envelope + schema_version
  1→2, default-mode `verification age:` line. ADD: docs must state that
  `verification_age` is alarmable only for watermark-bearing sections (D8).
- **Security handoff:** NOT required (impact: low correct — additive manifest
  field, no auth/PII/crypto/endpoint surface; re-confirmed against the rev-2
  change set).
- **SRE handoff:** NOW REQUIRED (upgraded from RECOMMENDED). Revision 2 ships
  `verification_age` as the FULL alarmable `--strict` SLI with CloudWatch wiring,
  AND adds two new alarmable metrics (`section_name_contract_violation`,
  `section_last_verified_stamp_failed`). The D1 re-seed gap means
  `section_name_contract_violation` could fire fleet-wide on first deploy —
  SRE must be briefed that this alarm is EXPECTED to fire until the re-seed warm
  completes, and must not be paged as an incident during the re-seed window.
  This is a SERVICE-altitude operational concern.

*Re-QA (revision 2) authored by qa-adversary, 2026-05-27. Evidence: live source
re-inspection (file:line) + fresh prod S3 re-probe (autom8-s3, offer
1143843662099250 + unit 1201081073731555). Verdict CONDITIONAL-GO for /build:
D2/D3/D4/D5/D6 resolved or materially resolved; D1 re-seed path is the sole
BLOCKING gap (fictional `_resolve_section_names`, no shipped re-seed for existing
prod manifests). MODERATE grade per self-ref-evidence-grade-rule; prod re-probe
and source-existence findings are STRONG-within-gate (deterministic). STRONG
upgrade requires the QA-gate-2 post-build prod re-probe specified above.*

---

# Final QA (revision 3) — 2026-05-27

Final gate of ADR-006 revision 3 + TDD revision 3 against the revision-2
CONDITIONAL-GO baseline (sole BLOCKING gap: D1/D7 re-seed mechanism fictional).
Mandate: verify the architect's D1 closure is source-real and the D8/D9 LOW items
are honestly closed; surface any new issues the threading introduces; quantify
prod-fleet alarm behavior under the new §Decision-7a tier. Evidence discipline:
all platform-behavior claims verified by direct file:line inspection (SVR-class)
at this gate's authoring time.

## Per-claim disposition

### Claim 1 — Re-seed plumbing (D1/D7 closure). **PASS.**

Every named site verified by direct inspection at this gate's authoring time:

- **`progressive.py:508` (`sections = await self._list_sections()`):** verified
  present. `_list_sections()` returns `list[Section]`; subsequent line builds
  `section_gids = [s.gid for s in sections]`. The `{gid: name}` map the TDD
  proposes (`{s.gid: s.name for s in sections if isinstance(s.name, str)}`) is the
  exact pattern already at `progressive.py:443-445` inside `_ensure_manifest` —
  verified, reusable, not invented.
- **`Section.name: str | None`:** verified at `models/section.py:39`
  (`name: str | None = Field(default=None, ...)`). Returns string when Asana
  provides one.
- **`_check_resume_and_probe(:225)`:** verified — signature is
  `(self, section_gids: list[str], resume: bool)`. The new `section_names`
  parameter is additive. Single caller at `progressive.py:531`
  (`resume_result = await self._check_resume_and_probe(section_gids, resume)`),
  zero test callers reference its positional signature (`test_computation_spans.py:365`
  mocks it with `AsyncMock`, signature-agnostic). Call-site churn is minimal and
  bounded.
- **`_probe_freshness(:316)`:** verified — signature is
  `(self, manifest: SectionManifest) -> tuple[int, int]`. Single caller at
  `:304` (`probed, delta_updated = await self._probe_freshness(manifest)`).
  The new `section_names` parameter is additive; single internal call site,
  zero test callers. Call-site churn bounded.
- **Stamp block `:388-403` is a single-write pass:** verified by direct read —
  `fresh_manifest = await get_manifest_async(...)` at `:388`, mutate-in-loop at
  `:393-401`, single `_save_manifest_async(fresh_manifest)` at `:403`. The
  architect's claim that **re-seed + stamp share ONE write** is structurally
  correct: a re-seed pass added inside this block at `:393-401` lands in the
  exact same `_save_manifest_async` call as the stamps. **No two-write race.
  No additional S3 round-trip.** The architect-claimed property holds.
- **`mark_section_complete` backstop (`:168-184`):** verified — current signature
  has the `*,` keyword-only separator already (`:173`), so adding
  `name: str | None = None` is a non-breaking additive change. The sole prod
  caller is `update_manifest_section_async` at `:474`
  (`manifest.mark_section_complete(...)`); single test caller at
  `test_freshness.py:327` uses only existing keyword args. **No call-site
  breakage from the backstop.**

The architect's source-grounded plumbing is REAL, LOCATED, and INTERNALLY
CONSISTENT. The BLOCKING gap is closed.

### Claim 2 — Alarm tiering (§Decision-7a) — `last_verified_at is not None` as discriminator. **PASS.**

The architect's reasoning: stamp block and re-seed run in the SAME
`_probe_freshness` pass and persist in the SAME write
(`_save_manifest_async(fresh_manifest)` at `:403`). Therefore any in-scope section
with `last_verified_at is not None` proves the re-seed pass ran on that manifest.

**Traced state combinations:**

| Pre/post-warm | Re-seed ran? | Stamp landed? | name | last_verified_at | Tier |
|----|----|----|----|----|----|
| Pre-warm (fleet today) | No | No | null | null | reseed_window=true → WARN advisory (correct) |
| Post-warm, healthy | Yes | Yes | populated | populated | join resolves >0 → SILENT (correct) |
| Post-warm, Asana returned null name for section X | Yes (skipped X) | Yes | null on X | populated on other in-scope sections | reseed_window=false → ERROR alarmable (correct — true contract violation) |
| Post-warm, all sections PROBE_FAILED | Yes | No (PROBE_FAILED never stamps, §Decision-5a) | populated | null | reseed_window=true → WARN (false negative possible) |

**Third-state edge case — partially re-seeded across multiple warms:** the
re-seed map is `{s.gid: s.name for s in sections if isinstance(s.name, str)}`
(skips Asana-null names). A section whose `Section.name` is null on warm N but
populated on warm N+1 stays null-named after warm N, then re-seeds on warm N+1.
During warm N→N+1 it would be in the ERROR tier if any in-scope section
stamped. **This is correct behavior:** if the re-seed pass had its chance and
left a section null while other sections stamped, that IS the true contract
violation tier; it should page. The architect's discriminator is honest about
this case.

**Edge case — all-PROBE_FAILED warm:** the re-seed runs over all
COMPLETE/null-name sections regardless of probe verdict (re-seed is unconditional
on `info.status == COMPLETE and info.name is None and gid in section_names`,
TDD §2.2.1 edit 2). Stamps skip PROBE_FAILED. So a fleet-wide PROBE_FAILED warm
populates names but leaves `last_verified_at=null` — the discriminator reads this
as `reseed_window=true` (WARN advisory), even though re-seed actually ran. **This
is a benign false-WARN, not a false-clear:** the operator sees `verification_age`
degrade to `mutation_age` (correct — no fresh verification happened) and an
advisory log. No paging missed because PROBE_FAILED on every section is itself
the operational signal the freshness-prober is broken (worth a separate alarm
the existing prober telemetry already provides). **Acceptable.**

No third state breaks tiering. The discriminator is sound.

### Claim 3 — D8 null-watermark residual wording. **PASS.**

ADR §Decision-4 wording is now scoped: *"The false-CLEAN channel is closed for
watermark-bearing sections, NOT universally — null-watermark sections are a
documented residual."* The §2.5 fix at `freshness.py:191-217` lives inside
`if section_info.watermark is not None`; null-watermark sections (21/34 offer,
4/17 unit, prod-confirmed re-probe 2026-05-27) retain pre-existing hash-only
detection. The ADR/TDD now name this honestly as a documented residual, not a
hidden one. Behavior for null-watermark sections is specified: they take the
pre-existing path (hash-only on `gid_hash` change), produce stamps no more false
than the old mutation signal was for them — explicitly **NOT** specified as
"force re-fetch" or "NO_BASELINE" (which would be a behavior change beyond the
narrow design). The residual is bounded; closure deferred to a future
watermark-population initiative.

### Claim 4 — D9 `watermark_gid` removal. **PASS.**

The §2.5 canonical code block now omits any reference to `section_info.watermark_gid`.
Direct probe: `grep -rn "watermark_gid" src/` returns empty (no field exists),
and the TDD §2.5 block shows the minimal `len(modified_tasks) == 1 and
t_modified > watermark` path with branch (c) deleted. The TDD explicitly states
*"do NOT ship a reference to `watermark_gid` without first adding the field."*
Genuinely removed from the load-bearing code block (not renamed, not deferred,
not "marked optional" while still appearing in the literal block). A principal
engineer who copies §2.5 verbatim now ships a block that runs without
AttributeError.

### Claim 5 — T16 contract honesty. **PASS.**

T16's setup REQUIRES `_probe_freshness` to accept a `section_names` argument.
A build that omits the threading cannot even compile T16 (the test invokes
`_probe_freshness(manifest, section_names=...)`). A build that adds the param
but ignores it inside the function fails T16's assertion
(`fresh_manifest.sections[gid].name == section_names[gid]`): `prior.name is None`
+ no consumption of `section_names` inside the stamp block → name stays None →
assertion fails. **No stub can pass T16 without doing the actual threading
through both signature and consumption.** Not test theater.

### Claim 6 — New issues from the threading. **NONE BLOCKING.**

Call-site churn audit:

- `_check_resume_and_probe`: single internal call at `:531`; one test (`AsyncMock`)
  positional-agnostic. Adding `section_names` parameter is purely additive at
  the one prod call site (`progressive.py:531`).
- `_probe_freshness`: single internal call at `:304`. Same shape — additive.
- `mark_section_complete`: existing keyword-only signature absorbs the new
  optional `name=None` kwarg without breakage; sole prod caller at `:474` and
  sole test caller at `tests/unit/dataframes/test_freshness.py:327` keep working.
- `update_manifest_section_async` (`:437-476`): the optional name pass-through
  per TDD §2.2.1 edit 3 is also additive — sole call site is
  `_fetch_and_persist_section`, which already holds the `Section` object
  (`progressive.py:759`, `section: Section | None`).

**Minor flag (NOT blocking):** the TDD §2.2.1 spec adds `section_names` as a new
parameter to two private methods — `_check_resume_and_probe` and
`_probe_freshness`. If `section_names` is `None`/empty (e.g. cold-build path
where `sections` returns empty), the re-seed loop is a no-op (the predicate
`gid in section_names` is False). No NPE, no AttributeError. The `dict.get(gid)`
or `gid in dict` semantics handle the empty case naturally. Build engineer
should pass `section_names={}` (not `None`) to keep the predicate semantics
clean — flagged as a minor implementation seam, not a blocker.

### Claim 7 — Prod-fleet alarm-storm assessment. **PASS.**

Re-probe baseline (revision 2, re-confirmed 2026-05-27): offer 34/34
`name=null` + `last_verified_at=null`, all COMPLETE; unit 17/17
`name=null` + `last_verified_at=null`, all COMPLETE.

**Expected behavior on first metrics emission post-deploy (before first warm):**

Per §Decision-7a + §2.6 alarm tier:
- Condition `null name AND no in-scope section has last_verified_at` is true
  for BOTH entities on every metrics invocation between deploy and first warm.
- Tier: `reseed_window=true` → emit `section_name_contract_violation` at
  **WARN/advisory level**, tagged `reseed_window=true`. **Do NOT page.**
- `verification_age` degrades to `mutation_age` (conservative — no fabricated
  fresh number; operator sees the old 62d mutation signal with an advisory log
  that re-seed is pending).

**Expected behavior after one warm cycle per project:**

- Warm runs `_list_sections()` → `Section.name` populated by Asana → re-seed
  fills 34/34 (offer) and 17/17 (unit) names in the same `_save_manifest_async`
  call that stamps non-PROBE_FAILED sections.
- Next metrics emission: `name_present == total` on both manifests; the §2.6
  raw condition (any null name with ≥2 sections) becomes false; no alarm fires;
  `verification_age` computes from `min(last_verified_at)` over in-scope active
  sections.
- The advisory WARN clears for that project on its FIRST post-deploy warm.

**Fleet-wide rollout:** every project's WARN clears on its first post-deploy
warm independently. No alarm-storm at deploy time (because WARN is advisory,
not pageable). No false-GREEN (because `verification_age` degrades to
`mutation_age` rather than fabricating a fresh number). No persistent landmine
(because the warm cadence self-heals on the normal schedule; no backfill job
needed). **Cleanly bounded behavior.**

**The one paging path remaining:** if a section's `Section.name` is null at
Asana's source AND another in-scope section stamps in the same warm → ERROR
tier fires for the null-named section. This is the genuine contract violation
that SHOULD page. Acceptable.

## Self-referential evidence discipline

- **Claim 1 (re-seed plumbing source verification): STRONG-within-gate** —
  deterministic, re-runnable probes (file:line reads via direct file inspection;
  `grep` exit codes for the negative existence claims). External-to-the-design
  in the sense that the gate verifies the architect's claims against the live
  codebase, not the design's own self-claims.
- **Claims 2-7: MODERATE** — single-reviewer, single-pass; source-grounded with
  file:line anchors but no second-rite corroboration. Per
  `self-ref-evidence-grade-rule`. STRONG-track requires QA-gate-2 post-build
  prod re-probe (specified as a carry condition below).
- The ADR/TDD evidence grade (MODERATE) is correctly declared and is NOT
  upgraded by this gate. The QA-gate-2 post-build re-probe is the deterministic
  external probe that converts the design-soundness disposition to STRONG.

## GO / NO-GO for /build (revision 3)

**GO for /build.** All seven claims attacked at this gate pass. The single
BLOCKING gap from re-QA revision 2 is closed by source-real, source-located
plumbing (`Section.name` from `_list_sections()` at `progressive.py:508`,
threaded through `_check_resume_and_probe` at `:225` into `_probe_freshness` at
`:316`, re-seeding inside the existing stamp block at `:388-403` in a
single-write pass). D8/D9 LOW items are honestly closed: D8 wording narrowed
to watermark-bearing sections with the null-watermark residual documented; D9
`watermark_gid` reference removed from the canonical block. T16 is a real
guard, not test theater — it forces both the signature change and the
in-function consumption. The §Decision-7a alarm tier discriminates the
reseed-window state from the true contract violation soundly; the prod-fleet
behavior under the tier is benign on first deploy (WARN advisory, no page)
and self-heals on the warm cadence (no backfill required).

The design is internally consistent, source-verified, and ready for
implementation. No further design loop required.

## Conditions QA-gate-2 (post-build) MUST carry

These conditions discharge during the post-build QA gate; they are the
STRONG-upgrade path per `self-ref-evidence-grade-rule`:

1. **[MUST] Re-probe a prod (or prod-shaped) manifest AFTER one full warm post-
   deploy.** Confirm:
   - `name_present == total` on both offer (1143843662099250) and unit
     (1201081073731555) manifests — re-seed actually fired on the live fleet.
   - `last_verified_at` populated on the same set of in-scope sections that
     stamps cover (non-PROBE_FAILED, delta-applied) — stamp block ran in the
     same write.
   - `verification_age` computes from `min(last_verified_at)` over in-scope
     active sections, not silently degraded to `mutation_age`.

2. **[MUST] Confirm `section_name_contract_violation` alarm wiring is correct:**
   - Fires at WARN tier (`reseed_window=true`) BEFORE the first post-deploy
     warm — captured in CloudWatch logs but NOT pageable.
   - Silent AFTER the first post-deploy warm clears the fleet — no
     alarm-storm, no lingering advisory.
   - Fires at ERROR tier (`reseed_window=false`) only if a section's name is
     null AND ≥1 in-scope section has `last_verified_at` populated (true
     post-warm contract violation).

3. **[MUST] Confirm T11–T16 actually fail on a deliberately-unfixed checkout
   (anti-theater).** Concretely:
   - T11 fails on a build without §2.6 assertion.
   - T15 fails on a build without `mark_section_complete` carry-forward.
   - **T16 fails on a build that adds carry-forward but omits the
     `section_names` threading through `_check_resume_and_probe` /
     `_probe_freshness`.** This is the load-bearing anti-theater test for the
     revision-3 closure — verify it fails on a build that "looks like" it
     fixed the issue but didn't thread the signature.

4. **[SHOULD] Confirm `read_manifest_sync` running-loop guard fails loudly**
   when invoked from within an async context (synthetic test or refactor
   experiment) — not just silently in the existing synchronous path.

5. **[SHOULD] Confirm SRE handoff briefing covers the re-seed window
   (§Decision-7a):** `section_name_contract_violation` at `reseed_window=true`
   is EXPECTED on first deploy and clears as warms roll through the fleet;
   only `reseed_window=false` is an incident. Document this in the CloudWatch
   alarm description so the on-call engineer reads it on first page.

## Acid test re-run

*"If this goes to production and fails in a way I didn't test, would I be
surprised?"* — **No.** With revision 3:

- First deploy: WARN advisory fleet-wide for the re-seed window; expected,
  briefed, non-pageable.
- First warm per project: re-seed lands names + stamps land in one write;
  `verification_age` computes thereafter.
- If an unexpected failure surfaces, it surfaces LOUDLY: ERROR-tier
  `section_name_contract_violation` (post-warm name-null) or
  `section_last_verified_stamp_failed` (stamp-phase exception) — both are
  observable, alarmable, and documented in this gate's carry conditions. The
  silent false-GREEN of revision 1 is gone. The fictional re-seed of
  revision 2 is gone. The signal asserts what it measures and what it does
  not measure honestly.

## Verdict

**GO for /build.** No further design loop. The four carry conditions above
move to QA-gate-2 (post-build) and discharge the STRONG-upgrade per
`self-ref-evidence-grade-rule`.

*Final QA (revision 3) authored by qa-adversary, 2026-05-27. Evidence:
direct source inspection at this gate's authoring time
(`progressive.py:225,304,316,388-403,443-445,508,531,749-754`;
`section_persistence.py:81-103,168-184,213-215,474`;
`models/section.py:39`; `tests/test_computation_spans.py:365`;
`tests/unit/dataframes/test_freshness.py:323-327`) + grep-zero exit codes for
`_resolve_section_names` and `watermark_gid` negative-existence claims +
inherited fresh prod S3 re-probe from re-QA revision 2 (offer 34/34
name_null + last_verified_at_null; unit 17/17 same). MODERATE design-
soundness grade per self-ref-evidence-grade-rule; source-existence and
file:line claims are STRONG-within-gate (deterministic, re-runnable).
STRONG upgrade discharges at the QA-gate-2 post-build prod re-probe per
the carry conditions above.*
