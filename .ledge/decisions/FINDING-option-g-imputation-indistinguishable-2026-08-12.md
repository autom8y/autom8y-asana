---
type: decision
status: draft
artifact_id: FINDING-option-g-imputation-indistinguishable-2026-08-12
initiative: asana-native-insight-delivery
date: 2026-08-12
found_by: S4 (carried as a caveat) → verified and re-graded by the main thread
bears_on: GATE-FORK (OS-3), operator-reserved, free until 2026-08-18
routes_to: PT-02 fork briefing — MUST accompany option (g) wherever it is presented
---

# FINDING — option (g) reports "never moved" and "never observed" identically

## Why this is filed separately

S4 revision 2 carried this as one of four honest caveats on option (g). On
verification it is not a caveat. **It is an instance of this crusade's founding
defect class, living inside the endpoint now being proposed as Mission A's
retrospective source.** That changes how option (g) must be presented at
GATE-FORK, so it is filed where the fork briefing cannot miss it.

## The mechanism, verified end to end

`GET /api/v1/offers/section-timelines` derives each offer's history by replaying
Asana stories. When an offer has **zero cached stories**:

```
section_timeline_service.py:604      cache_misses += 1
                        :605-606     # Entity with zero cached stories.
                                     # Impute if task_created_at and current_section available.
                        :607-612     intervals = _build_imputed_interval(
                                         task_created_at, account_activity, section_name)
                        :614-623     timelines.append(SectionTimeline(..., story_count=0))
```

The offer is reported as having occupied its **current** section since
**creation** — i.e. as never having moved.

**And the caller cannot tell.** `_compute_day_counts` (`:675`) builds the
response model `OfferTimelineEntry` (`models/business/section_timeline.py:158`)
with exactly seven fields — `offer_gid`, `office_phone`, `offer_id`,
`active_section_days`, `billable_section_days`, `current_section`,
`current_classification` (`:728-736`).

**`story_count` is dropped at the boundary.** It exists on the internal
`SectionTimeline` object, where `story_count=0` marks precisely the imputed
entries — and it is not carried into the response. An imputed offer and a
genuinely-static offer are **identical in the payload**.

The evidence exists, but only server-side:
- `cache_hits` / `cache_misses` → the **cache store** (`:636-637`) and one **log
  line** (`:658-659`). Never the response.
- Above the threshold the gap is not even filled: `MAX_INLINE_STORY_FETCHES = 50`
  (`:502`); inline backfill runs only for `0 < len(misses) <= 50` (`:505`); above
  that, `elif len(misses) > MAX_INLINE_STORY_FETCHES:` emits
  `logger.warning("story_cache_gap_above_threshold")` (`:532-541`) **and
  proceeds**.

## Why it is the crusade's own defect

One quantity answering two questions — the exact shape named in the wave-close
ruling and recurring at `data_age_seconds`, at `content_age_seconds`, at AL-5,
and at the success-deadman. Here the two questions are:

> **"This offer has not moved."**   vs.   **"We have no record of this offer moving."**

A readout built on option (g) as it stands would tell the team an offer has sat
in one section for 40 days when the truth may be that its story history was
never cached. That is the *"authored ≠ true"* failure, and it would be delivered
to humans who act on it — precisely the rung-4 surface this initiative exists to
reach.

It is also the **inverse** of the `last_modified` property that made item 1a
say-able. There, quiet-time is **overstated, never understated** — the datum is
the board's own timestamp, so pipeline failure cannot manufacture a false
finding. Here, an observation gap **manufactures a positive claim about the
world**. Opposite error directions, and only one of them is safe under P-3.

## What this does NOT mean

**Option (g) is not refuted and should not be withdrawn.** Everything S4 and the
critic established about it holds: mounted unconditionally (`api/main.py:488`),
in the published contract (`openapi.json:3859`), arbitrary retrospective window,
no CloudWatch retention dependency, no K-lane contact, no producer deploy, and
better contracted than option (b) — whose route is `include_in_schema=False`.
The retrospective half of Mission A **is** reachable, and S4's corrected §11
stands.

What changes is the **cost line**. Option (g) is not *"already paid for."* It is
*"already built, and carrying an instance of the defect this crusade just spent
a wave closing."* The remedy is additive and small — surface `story_count` (or
an `imputed: bool`) per entry, and return the cache-gap counters — which is
consistent with S4's existing condition of "two additive disclosure fields." The
finding sharpens that condition from a nicety into a **precondition**.

## For PT-02 and the fork briefing

Present option (g) with this attached. The honest framing:

> The retrospective half is reachable via an endpoint that already exists — **on
> condition that its imputation is disclosed.** Without that disclosure the
> readout can assert an offer never moved when we merely never observed it,
> which is the failure this crusade closed at the substrate and would be
> re-opening at the readout.

**Nothing is ruled here.** GATE-FORK is operator-reserved and free until
2026-08-18. This finding constrains how option (g) is *described*, not which
option is *chosen*.

## ⚠ UV-P-10 CANNOT be sized — because the endpoint has never been called

I attempted exactly the sizing described below and got a result more consequential
than the measurement would have been.

```
log group : /ecs/autom8y-asana-service          window: 14 days → 2026-08-12T20:58Z
query 1   : filter @message like /timeline_computed_on_demand|
                                  story_cache_gap_above_threshold|timeline_derived/
            queryId ad7887db-c0de-4306-8d8c-be239d5ee635   →  0 rows
query 2   : filter @message like /timeline|section-timelines/ | stats count() by bin(1d)
            (deliberately broadest possible control)         →  0 rows
control   : log group IS live — most recent event 2026-08-12T20:38:30Z, ~20 min
            before the query. Not a dead-group false negative.
```

**`GET /v1/offers/section-timelines` has not been invoked once in fourteen days.**

Three consequences, in ascending order of importance:

1. **UV-P-10 is not answerable from logs.** There is no traffic to measure. It
   can only be sized by *calling* the endpoint — which is a live request against
   the Asana-backed service and was **not** done tonight.
2. **Another rung on the same ladder.** Mounted, published in the OpenAPI
   contract, spec-gated, fully implemented — and **never used**. Add it to the
   family: *merged ≠ deployed · authored ≠ delivered · delivered ≠ read · built ≠
   reachable · ratified ≠ durable* — and now **built ≠ exercised**. Every honest
   claim about this endpoint is a claim about code that has never run in anger.
3. **It may make the imputation hazard worse rather than better, and this is the
   part that matters for the fork.** The imputation path fires on offers with
   **zero cached stories**. If this endpoint is the only warm path for that
   cache, it is cold — and the **first real call would impute most heavily**,
   which is exactly the call someone would make while evaluating whether the
   endpoint is any good. A cold-cache first impression, rendered
   indistinguishably from "these offers never moved."

   **I am not asserting the cache is cold.** Stories may be warmed by other
   paths — `DEFAULT_STORY_TYPES` at `cache/integration/stories.py:26` includes
   `section_changed`, so a general warm path plausibly populates it. **I did not
   determine which.** That question — *is the story cache warm for the offers
   project independent of this endpoint?* — is now the load-bearing one for
   option (g), and it is cheaper than a build. It replaces UV-P-10 as the thing
   worth measuring first.

## ⚖ RECONCILIATION with S1 revision 3 — same code, two compatible readings

S1 revision 3 (`PREDICATE-sayable-set…` §7) reached the **same function
independently** and drew a *different* conclusion. Both hold, and the difference
is instructive enough that neither should be quietly dropped.

- **S1's reading**: `_build_imputed_interval` (`section_timeline_service.py:272-279`)
  imputes `[created_at, None]`, so an offer whose moves went unobserved has its
  dwell **counted from creation — overstated, never understated**. Bounded and
  directional, therefore **G4 passes**; DR-7 binds as a render duty.
- **This finding's reading**: the same imputation makes *"this offer never
  moved"* indistinguishable from *"we have no record of it moving"*.

**They are not in conflict — they are about different claims.** For a **dwell**
readout ("how long has this sat in ACTIVATING"), S1 is right and its analysis is
sharper than mine: the error has a known sign, and an overstatement that cannot
understate is exactly the property that made item 1a say-able. For a
**never-moved / quiet-corner** claim, this finding is right: the assertion is
manufactured from an observation gap, and no bound on its magnitude rescues a
claim about *whether an event occurred*.

**The synthesis, which is what PT-02 should carry:** option (g) is sound for
duration-shaped questions and unsound for occurrence-shaped ones, on the same
data, from the same call. That is a *sharper* condition than "add disclosure
fields" — it says which readouts may consume it, not merely how to annotate it.
The disclosure remedy stands; it is necessary and now demonstrably not
sufficient on its own.

*(Note: S1 also flagged, as a UV-P, that S4's option slate might predate
`section-timelines`. It does not — S4 revision 2 enumerates it as option (g),
dispositions it, and does not reject it. That UV-P is discharged.)*

## Verification scope

Read-only throughout: source read at this repo's `origin/main`; two CloudWatch
Logs Insights queries plus one `describe-log-streams` control. **No HTTP request
was issued to the endpoint**, no Asana call, no mutation of any kind. Whether the
story cache is warm by another path is **explicitly undetermined** and is not
inferred either way.
