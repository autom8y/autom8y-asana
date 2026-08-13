---
type: decision
status: draft
artifact_id: DEFECT-temporal-filter-imputed-false-move-2026-08-12
initiative: asana-native-insight-delivery (found by), but the DEFECT is not this initiative's
date: 2026-08-12
severity: correctness — silent false positives on a shipped query surface
found_by: the rite-disjoint hygiene critic at delta pass 3, going one hop past where the sprint stopped
verified_by: main thread, independently, at origin/main
routes_to: OPERATOR — this is a product defect, not a say-ability question
discharged: 2026-08-13 by PR #360 (commit 49cf12ca) — see banner
---

> ## ✅ DISCHARGED — fixed by PR #360 (`49cf12ca`, merged 2026-08-13, on `origin/main` @ `d45aa305`)
>
> The EX-3 sprint added the imputed-interval guard (`timeline.story_count == 0`
> never satisfies a non-empty transition filter) plus the `imputed`/`story_count`
> wire discriminator, with two-sided teeth (RED on the natural weekend-query
> shape, GREEN on the no-defect variant). The `routes_to: OPERATOR` above is the
> historical routing; no operator action remains on the acute defect. The
> imputation *rate* question (Q-8) is separate and still open.

# DEFECT — the temporal filter reports never-moved offers as having moved

## Why this is filed separately from the say-ability work

It was found while adjudicating whether a readout could be stated honestly. But
the defect is **in shipped code, on a consumable surface, today** — independent
of whether any readout is ever built. It should not be buried in a predicate
artifact.

## The mechanism, verified end to end at `origin/main`

`TemporalFilter.matches` (`src/autom8_asana/query/temporal.py`) returns True if
**any** interval satisfies **all specified** criteria — criteria are conjunctive
over *specified* fields only:

| criterion | what it consults |
|---|---|
| `moved_to` | the interval's **own** `section_name` / `classification`. **No predecessor required.** |
| `since` / `until` | `interval.entered_at` |
| `moved_from` | the **only** predecessor-consulting criterion — and its `idx == 0` guard is reached **only if `moved_from` is specified** |

Now recall what an imputed interval is
(`services/section_timeline_service.py:272-300`): for an offer with **zero cached
stories**, exactly one interval is synthesised, carrying `entered_at =
task_created_at` and the offer's **current** classification.

**Compose them.** A natural weekend query — *"what moved into ACTIVE between
Saturday and Sunday"* — specifies `moved_to` and `since`/`until` and **not**
`moved_from`. The `idx == 0` guard is therefore never reached. The imputed
interval's `entered_at` is the offer's **creation** timestamp, which falls in the
window, and its classification is the offer's **current** one, which matches.

> **An offer that was merely created over the weekend, and never moved at all,
> is returned as having moved.**

**This is not a corner case.** The population most likely to be imputed — offers
with no surviving story history — is disproportionately the **newly created**
population, whose `created_at` is exactly what lands in recent windows. The
defect is concentrated precisely where the query is aimed.

**Reachable from a shipped consumer**: `query/__main__.py:875` imports it, `:893`
constructs the filter, `:920` applies it to the timelines.

## The workaround inverts the sign rather than fixing it

Specifying `moved_from` engages the `idx == 0` guard — but
`_build_intervals_from_stories` (`section_timeline_service.py:231-267`) creates
one interval **per story** with **no synthesised pre-first interval**, so
`intervals[0]` is a **genuine first move**. Specifying `moved_from` therefore
**drops every offer's first real move.**

**False positives without it; false negatives with it. No formulation is
single-signed.**

## Relation to the night's other findings

This is the same root as
`FINDING-option-g-imputation-indistinguishable-2026-08-12.md` — imputation
collapsing an offer's unknown history into its present state — surfacing on a
*third* consumer. Three consumers of one imputation, three different wrong
answers:

| consumer | what imputation does to it |
|---|---|
| day-count difference (`billable − active`) | **sign flips by sub-population** — understates for offers currently ACTIVE, overstates for currently ACTIVATING |
| the raw response (`OfferTimelineEntry`) | **indistinguishable** — `story_count` dropped at the boundary, so a 100%-imputed payload looks identical to a 0%-imputed one |
| `TemporalFilter` | **false positives** — never-moved offers reported as moved |

**The remedy is one thing, not three**: an imputed-vs-observed discriminator must
reach the consumable surface. Every downstream defect here is a consequence of
that one omission.

## What is NOT claimed

- **No live query was run.** This is a code-path derivation, verified
  independently by two readers at `origin/main`, not an observed wrong answer.
- **The imputed fraction in production is unknown.** It depends on story-cache
  warmth for offer tasks, which is the night's standing open probe. If no offer
  is ever imputed, the defect is latent rather than active. **Nobody has
  measured this**, and it is the same probe that gates option (g).
- **Severity is not assessed here.** Whether this is urgent depends on who uses
  the temporal filter and for what — which is an operator question, not a sprint
  one. **Not ruled in any direction.**

## Routing

**Operator.** It is a product-correctness defect on a shipped surface, found by
an initiative that is fenced from fixing it. It belongs to whoever owns
`query/temporal.py` and the section-timeline service. It does **not** block
GATE-FORK, and GATE-FORK does not gate it.
