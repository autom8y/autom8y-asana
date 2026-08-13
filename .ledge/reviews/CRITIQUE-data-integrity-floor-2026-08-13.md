---
type: review
status: complete
artifact_id: CRITIQUE-data-integrity-floor-2026-08-13
initiative: exec-insight-delivery
sprint: EX-3 (WS-5 limbs ii + iii — the data-integrity floor, offer-local)
author_of_work: 10x-dev / principal-engineer
critic: arch / structure-evaluator (rite-disjoint) + NCSR carrier (NR-3, §A.2)
disjointness: author=10x-dev, critic=arch — DISJOINT (Axiom 1 satisfied)
date: 2026-08-13
worktree: .knossos/worktrees/ex-3-data-integrity-floor (branch ex-3-data-integrity-floor, off origin/main afdad5ed)
verdict: PASS-WITH-ONE-CONCERN (published-contract surface not reconciled)
nr3_verdict: CONCUR — FALLS at the runtime wire; NARROWS (published-contract surface still stale)
self_attestation_cap: MODERATE, except teeth re-run own-hands = STRONG
---

# CRITIQUE — EX-3 the data-integrity floor (limbs ii + iii)

## 0. What was verified own-hands, and how the .pth trap was avoided

All pytest / import runs were executed inside the worktree with
`export PYTHONPATH="$PWD/src"`. Import provenance was confirmed before any test:
`autom8_asana` resolved to
`…/.knossos/worktrees/ex-3-data-integrity-floor/src/autom8_asana/__init__.py`,
NOT the main tree — the venv editable `.pth` trap named in the dispatch was
avoided. No worktree file was mutated by any probe; final `git status` is the
author's 8-file change set + 1 untracked test, unchanged. No git write/commit/
push was run; no live Asana/HTTP/authenticated call was issued; no K-lane
mutation; no infra touched; `s3://autom8y-asr-verdicts` not read; no credential
material encountered.

---

## 1. Exit-criterion verdicts

| # | Criterion | Verdict | Confidence |
|---|---|---|---|
| 1 | Limb (ii) guard-nesting defect fixed, proved TWO-SIDED (RED weekend shape / GREEN no-defect) | **PASS** | **High** (teeth re-run own-hands) |
| 2 | `moved_from` workaround NOT shipped; genuine first moves preserved | **PASS** | **High** |
| 3 | Limb (iii) discriminator reaches **the wire** (field/count on `OfferTimelineEntry`, serialization-mode) | **PASS at the runtime wire** + **1 CONCERN** (published OpenAPI contract not regenerated) | **High** (wire) / **High** (drift, own-hands) |
| 4 | A consumer **demonstrably branches** on the discriminator | **PASS** | **High** |
| 5 | Imputation rate reported **INFERRED**, never measured; no live authenticated call | **PASS** | **High** |

### Criterion 1 — two-sided teeth, re-run OWN-HANDS  [PASS · High]

GREEN (post-fix, real `pytest` against worktree code):
`tests/unit/query/test_temporal.py::TestImputedIntervalNotAMove` → **8 passed**.

RED (pre-fix): reproduced against the **real** module by neutralizing only the
new guard's trigger (`TemporalFilter._has_any_criterion → False` makes the branch
`if timeline.story_count == 0 and self._has_any_criterion(): return False` dead —
byte-equivalent to the guard being absent = pre-fix). Result: **exactly 4 FAIL /
8**, matching the author's reported RED=4-fail. The four reds are precisely the
negative-control assertions (never-moved imputed offer must NOT match a transition
query): `test_imputed_interval_rejected_by_weekend_move_query`,
`test_imputed_rejected_by_moved_to_only`, `test_imputed_rejected_by_since_only`,
`test_imputed_rejected_by_until_only`. Pre-fix each returns `True` (the false
positive the DEFECT describes: `moved_to`+`since`/`until` with `moved_from`
omitted → the imputed interval, whose `entered_at == created_at` falls in the
window and whose classification is current, matches).

**Teeth bite on substance, not shape** (discriminating-canary §2.3): both fixtures
call the same `_single_active_interval()` — a single open ACTIVE interval entered
on the weekend Saturday — so they are **byte-identical in interval shape**; the
ONLY difference is `story_count` (0 vs 1). The genuine fixtures PASS in BOTH
postures (tests 2, 7, 8), while the imputed fixtures flip match→reject across the
fix. A fixture matching on shape rather than the imputation discriminator could
not produce that flip. The teeth discriminate imputation, not interval geometry.

SVR (own-hands):
```
structural_verification_receipt:
  claim: "pre-fix the four negative-control assertions fail (imputed timeline matches a transition query = false positive); post-fix all 8 pass; genuine fixtures pass in both postures"
  verification_method: bash-probe
  verification_anchor:
    source: "PYTHONPATH=$PWD/src python3 red_repro.py  (guard active vs _has_any_criterion→False), and pytest …::TestImputedIntervalNotAMove"
    command_output_verbatim: "POST-FIX: 0 FAIL / 8 total ; PRE-FIX: 4 FAIL / 8 total ; pytest: 8 passed in 0.32s"
    exit_code: 0
    claim: "the two-sided teeth bite only on the story_count discriminator, not on interval shape"
```

### Criterion 2 — the `moved_from` workaround is not the fix  [PASS · High]

The shipped fix keys on `timeline.story_count == 0`, NOT on `moved_from`. The
DEFECT artifact's own analysis is preserved by the code: `moved_from` engages the
`idx == 0` guard, and `_build_intervals_from_stories`
(`section_timeline_service.py:231-269`) synthesises **no** pre-first interval, so
`intervals[0]` for a story-derived timeline is a **genuine first move** — matching
on `moved_from` would drop it. Own-hands: `test_moved_from_workaround_drops_
genuine_first_move` confirms the genuine first move MATCHES the correct fix
(`moved_to`+`since`/`until`, no `moved_from`) → `True`, and that adding
`moved_from` drops it → `False`. The fix is single-signed correct: it rejects
imputed (false-positive class) while preserving genuine first moves (the
false-negative class the workaround would have opened).

### Criterion 3 — discriminator reaches the wire  [PASS at runtime wire · High] + [CONCERN]

**PASS at the runtime response boundary.** `story_count` is a required scalar on
`OfferTimelineEntry`; `imputed` is a `@computed_field @property`. Own-hands
serialization probe:
- `imputed` appears in **serialization-mode** JSON (`model_dump_json()` →
  `"imputed":true` / `"imputed":false`) and in the serialization schema, but NOT
  the validation schema — correct output-only computed-field behavior. It is on
  the real wire, not merely the validation surface.
- End-to-end via `TestClient` (`test_endpoint_emits_imputation_block`): the live
  endpoint response body carries per-entry `imputed`/`story_count` AND a
  response-level `imputation` block. Re-ran own-hands: **91 passed** across all
  changed suites.

This satisfies the exit-criterion literal: "a flag or count on `OfferTimelineEntry`,
not a log line." The negative "unmeasurable from the payload" no longer holds for
the runtime payload.

**CONCERN (boundary-alignment, my specialty as the response-boundary critic):**
the **published** contract artifact was not reconciled with the model. The
committed `docs/api-reference/openapi.json` `OfferTimelineEntry` still lists only
the seven original scalars (`additionalProperties: false`); `story_count`,
`imputed`, `ImputationSummary`, and the envelope `imputation` field are absent.
Own-hands, `scripts/generate_openapi.py --check` **exits 1 — spec drift detected**
(the check did not mutate the committed file). Two consequences:
1. The published contract that **SDK codegen and the API-reference surface**
   consume does not yet expose the discriminator; a contract-consuming client
   reading `openapi.json:1106` still sees the seven-scalar shape.
2. The repo's drift gate (`just spec-check` → `generate_openapi.py --check`)
   fails until `openapi.json` is regenerated. Whether this **hard-blocks landing**
   is UNKNOWN from this repo alone: `test.yml:78-79` wires the CI `spec_check` to
   `scripts/validate_openapi.py` (which regenerates in-memory and validates
   structure — it does NOT diff against the committed file), so the blocking-CI
   path may pass while the committed contract ships stale. The reusable workflow
   that could also invoke the drift check is monorepo-side and out of this
   review's read-surface. **Routed as a pre-landing CONCERN, not a criterion-3
   failure** — the discriminator does reach the runtime wire; the published static
   contract simply has not been regenerated to match. (Observation for the landing
   thread / remediation-planner; I do not prescribe the mechanism.)

### Criterion 4 — a consumer demonstrably branches  [PASS · High]

`summarize_imputation` (`api/routes/section_timelines.py`) iterates entries and
branches `if entry.imputed:` to partition observed vs imputed and derive the rate.
Own-hands: `test_branch_flips_readout` flips a single entry `story_count 5→0` and
the summary changes (`inferred_imputation_rate` 0.0→0.5, `imputed_offers`
differs) — output that co-varies with imputation, which a non-branching consumer
(constant, or one keyed only on the seven original scalars, all identical between
the two entries) could not produce. The branch runs on the **live endpoint path**
(`get_offer_section_timelines` constructs `SectionTimelinesResponse(…,
imputation=summarize_imputation(entries))`), confirmed by the `TestClient` test —
not dead code.

### Criterion 5 — rate is INFERRED, never measured  [PASS · High]

The field is named `inferred_imputation_rate`; a `basis:
Literal["inferred-from-story-cache-warmth"]` provenance tag is emitted; docstrings
on `ImputationSummary` and `summarize_imputation` state "INFERRED, not measured"
and name UV-P-E-3 (a live authenticated Asana re-query) as the operator-reserved
path that would convert it. Own-hands: `type(summary).model_fields` has no
`measured_imputation_rate`; the endpoint test patches `get_or_compute_timelines`
with an `AsyncMock` and uses a `MagicMock(spec=AsanaClient)` — **no live Asana /
HTTP / authenticated call fires** in any test. UV-P-E-3 / Q-8 not exercised.

---

## 2. BINDING NCSR — NR-3 (§A.2)

**Negative under test:** *"the contaminated fraction is UNMEASURABLE from the
payload."* Author's returned verdict: FALLS-for-inferred / NARROWS-in-scope.

### §A.3 (1) — refuters swept, and what each returned (incl. NULLs)

- **(a) Any OTHER shipped field correlating with cache-miss count?**  **NULL —
  confirmed.** The seven original scalars (`offer_gid`, `office_phone`,
  `offer_id`, `active_section_days`, `billable_section_days`, `current_section`,
  `current_classification`) carry no imputation signal: an imputed 40-day dwell is
  arithmetically indistinguishable from a genuine 40-day dwell (that indistinguish-
  ability IS the founding defect). No pre-existing field discriminates.
- **(b) `extra="forbid"` on the ENTRY only, or the ENVELOPE too — a pre-existing
  legal slot?**  **BOTH forbid — confirmed own-hands.** `OfferTimelineEntry`,
  `ImputationSummary`, and `SectionTimelinesResponse` all carry `extra="forbid"`.
  There was NO pre-existing legal slot to smuggle a discriminator through; the fix
  had to ADD declared fields. (Attempting to pass `imputed=…` as input →
  `ValidationError`; the computed field is not settable.)
- **(c) "not on wire" ≠ "not obtainable" — log line queryable from a durable
  sink?**  **NARROWS — confirmed.** The server-side signal exists in principle
  (`cache_hits`/`cache_misses` → cache store + one log line at
  `section_timeline_service.py:658-659`), but the PROBE
  (`PROBE-story-cache-warmth-2026-08-13.md`; `FINDING-option-g…:110-127`) shows
  **0 endpoint invocations in 14 days** — the sink is empty. The signal is
  obtainable-in-theory, absent-in-practice, and in no case is it the payload. The
  payload-level negative held until this sprint; the fix now places it ON the
  payload.
- **(d) Is `OfferTimelineEntry`'s 7-scalar shape CONTRACTUALLY FROZEN or merely
  current?**  **MERELY CURRENT — confirmed, with a citation NARROW (see §3).**
- **(e) [author-added] Is the discriminator SILENTLY DROPPABLE at the construction
  site?**  **NO — confirmed own-hands.** `story_count` is required (omission →
  `ValidationError`); `imputed` is computed from it and cannot be overridden
  (rejected under `extra="forbid"`); the sole endpoint construction site
  (`_compute_day_counts`, `section_timeline_service.py:736-739`) passes
  `story_count=timeline.story_count`, and `SectionTimeline.story_count` is a
  required int set to `0` on every imputation path and `len(filtered_stories) ≥ 1`
  on every observed path (lines 363 / 591 / 621). The invariant
  `story_count == 0 ⇔ imputed` holds across all three construction paths.

### §A.3 (2) — the hop ONE PAST where the argument stopped, named concretely

The author's argument stopped at *"the fix makes the contaminated fraction
measurable-as-inference on the payload."* The hop one past: **measurable on the
RUNTIME payload ≠ measurable from the PUBLISHED contract.** Concretely —
`docs/api-reference/openapi.json` `OfferTimelineEntry` (still the seven scalars,
`additionalProperties: false`) and `generate_openapi.py --check` (exit 1). A
client that consumes the **published** schema (SDK codegen, the API reference)
still cannot see `story_count`/`imputed` until `openapi.json` is regenerated. The
discriminator reaches the wire the service **emits**; it has not yet reached the
contract the fleet **publishes**.

### §A.3 (3) — refuter I ADDED

Refuter (f): **"is the additive extension not merely sanctioned-in-principle but
propagated to the frozen published surface?"** → **NO.** The published OpenAPI
contract drifts (own-hands, exit 1). Sanction of additive extension (§3) is
necessary but not sufficient; propagation to the published artifact was not
performed. This is the concrete basis for the NARROW below.

### §A.3 (4) — NR-3 verdict: CONCUR — FALLS + NARROWS, corrected scope

I **CONCUR** with the author and sharpen the scope:
- **FALLS at the runtime wire.** The negative "unmeasurable from the payload" is
  refuted for the actual HTTP response body: `story_count` + computed `imputed`
  serialize per-entry, a `SectionTimelinesResponse.imputation` block reports the
  inferred fraction, and a consumer branches on it — all verified own-hands.
- **NARROWS at two edges that must travel with the verdict:**
  1. **Published-contract surface.** The negative STILL HOLDS for any consumer
     reading `openapi.json` until the spec is regenerated (drift check red,
     own-hands). Measurability is on the emitted wire, not yet the published
     contract.
  2. **Inferred, not measured (criterion 5, intact).** What reaches the payload is
     a contamination **estimate** derived from story-cache warmth, not a measured
     rate. "Measurable from the payload" means "the imputed fraction is now
     *disclosed and branchable*," NOT "the true contaminated fraction is *known*."
     Under `FINDING-option-g` the endpoint has never run (0 calls/14d), so in
     production today the payload's imputed fraction is **untested live** — the
     cold-cache first-call hazard (the first real call imputes most heavily) is
     un-refuted and remains an operator-reserved measurement (UV-P-E-3 / the
     story-cache-warmth probe). This is not a defect in the fix; it is the honest
     ceiling the fix correctly labels.

The DISSENT-if-any is not softened: the fix is sound at the wire, but the verdict
"the fraction is measurable from the payload" must not be stated unqualified — it
is *disclosed-as-inference on the emitted response*, with the published contract
still stale and the live rate still unmeasured.

---

## 3. CONTRACT frozen-vs-current — verified own-hands

**Confirmed: MERELY CURRENT, not contractually frozen — with a citation NARROW.**

- No artifact declares `OfferTimelineEntry`'s seven-scalar shape *frozen against
  additive extension*. It is a **published** OpenAPI schema
  (`openapi.json:1106`, `additionalProperties: false`) — "published" ≠ "frozen."
- The **direct governing authority** for additive extension of this surface is the
  Mission-A source-of-record ADR
  (`.ledge/decisions/ADR-mission-a-source-of-record-2026-08-12.md`), which
  explicitly prescribes **"two additive disclosure fields"** — surface
  `story_count` per entry / mark imputed — as the remedy for option (g)
  (§ option-(g) disposition; "an additive field on an already-published model").
  The governing ADR *sanctions exactly this extension*.
- **NARROW on the author's citation.** The author cited `CONTRACT §1.5/NOTE-1`.
  The freshness-axis contract's §1.5 ("Response-meta schema addition — additive,
  backward-compatible", `CONTRACT-offers-freshness-axis-frozen-2026-08-11.md:536`)
  establishes additive-on-`extra="forbid"` as backward-compatible **for the
  query-lane META models (`RowsMeta`/`QueryMeta`)**, evidenced by the
  `stale_served` precedent — it is NOT literally about `OfferTimelineEntry`. The
  load-bearing sanction for THIS surface is the Mission-A ADR, not §1.5. The
  author's conclusion (MERELY CURRENT, additive sanctioned) is **correct**; the
  precise citation is adjacent-lane. Additionally, §1.5's own analysis names the
  **strict-consumer break** hazard (a hand-rolled `extra="forbid"` parser raises
  on unknown keys — the F-7 class in the Mission-A ADR). For `section-timelines`
  that hazard is **latent, not active**: the endpoint has zero known SDK
  strict-parser consumers and has not been called in 14 days — so additive
  extension is safe in practice here, but the safety rests on the *empty consumer
  set*, not on a contractual guarantee.

SVR (own-hands):
```
structural_verification_receipt:
  claim: "published OfferTimelineEntry is the seven original scalars with additionalProperties:false and no story_count/imputed; the models now drift from it"
  verification_method: bash-probe
  verification_anchor:
    source: "python3 (json.load docs/api-reference/openapi.json) + scripts/generate_openapi.py --check"
    command_output_verbatim: "properties: ['active_section_days','billable_section_days','current_classification','current_section','offer_gid','offer_id','office_phone'] ; additionalProperties: False ; generate_openapi.py --check EXIT=1"
    exit_code: 1
    claim: "the 7-scalar shape is current-and-published, not frozen; additive extension is sanctioned by the Mission-A ADR but was not propagated to the published spec"
```

---

## 4. Unknowns (structural decisions requiring human context)

### Unknown: Does the stale `openapi.json` hard-block the EX-3 landing?
- **Question**: Is `generate_openapi.py --check` (or an equivalent committed-vs-
  generated drift gate) in the blocking CI path for this branch, or only the
  in-memory `validate_openapi.py`?
- **Why it matters**: Determines whether "regenerate `openapi.json`" is a landing
  prerequisite (CI-red) or a follow-up (silent published-contract staleness).
- **Evidence**: `test.yml:78-79` wires `spec_check` → `validate_openapi.py` (no
  committed diff); the drift check lives in `justfile` (`spec-check`); the
  reusable workflow that may also run it is monorepo-side and out of read-surface.
- **Suggested source**: the landing thread (runs CI) / release-executor; or a
  read of the monorepo `satellite-ci-reusable.yml` via `git show origin/main:…`.

### Unknown: DEFECT severity and cold-cache live exposure (already operator-routed)
- **Question**: How heavily is `TemporalFilter` / `section-timelines` actually
  used, and how cold is the offer-project story cache on first real call?
- **Why it matters**: Sets the true in-production contaminated fraction, which the
  fix can only report as INFERRED. The DEFECT artifact routes severity to OPERATOR
  and UV-P-E-3 to operator-reserved; noted here for completeness, not re-opened.
- **Evidence**: `FINDING-option-g…:110-152` (0 calls/14d; cold-first-call hazard);
  DEFECT artifact "Severity is not assessed here."
- **Suggested source**: OPERATOR (owns `query/temporal.py` + section-timeline
  service; the story-cache-warmth probe is the cheaper prerequisite measurement).

---

## 5. Cross-domain observations (for remediation-planner, not referrals I author)

- **Published-contract reconciliation** (boundary/contract): regenerate
  `docs/api-reference/openapi.json` so the emitted-wire discriminator also reaches
  the published contract surface (SDK codegen / API reference). Concrete, bounded.
- No security, no K-lane mutation, no infra surface touched by this change set.

---

## 6. Summary verdict

**PASS-WITH-ONE-CONCERN.** All five exit criteria are met at the code/runtime
altitude, verified own-hands (two-sided teeth RED=4 / GREEN=8 on the real module;
serialization + branch + inferred-labeling + required-field invariants). The one
concern is a response-boundary reconciliation gap: the discriminator reaches the
**emitted** wire but the **published** OpenAPI contract was not regenerated
(`generate_openapi.py --check` exit 1, own-hands) — routed as a pre-landing
CONCERN with an open question about whether it blocks CI. NR-3: **CONCUR** with
the author's FALLS/NARROWS — the negative FALLS at the runtime wire and NARROWS at
(1) the still-stale published contract and (2) the inferred-not-measured ceiling
that the never-called endpoint leaves un-refutable without an operator live probe.

Self-attestation: MODERATE overall; **STRONG** on the teeth re-run, serialization,
branch-flip, required-field, and spec-drift checks (each executed own-hands in the
worktree with verified import provenance).
