---
type: review
status: accepted
rung: rung-NCSR-PREMERGE-REVIEWED
verdict: GO-WITH-CONDITIONS
reviewer: observability-engineer[sre]
self_assessment_cap: MODERATE
subject: autom8y/autom8y-asana PR #369
subject_head: 6b75279fcfb9e71c40766bf6bf5d037ca7766ba6
initiative: chain-of-custody-closure
sprint: CC-5 (RE-1 Tier-1 offers-only story-warm priority pass)
rite_disjointness: sre/observability vs 10x-dev author — reviewer shaped none of this work
date: 2026-08-14
---

# NCSR PRE-MERGE REVIEW — PR #369 (CC-5 Tier-1 offers-only story-warm priority pass)

**VERDICT: GO-WITH-CONDITIONS**

All four conditions are operational or merge-hygiene. **No code change is
required.** No finding in this review asks the author to touch the diff.

---

## 0. Scope and disjointness

I am the rite-disjoint merge reviewer (sre/observability). I shaped none of
CC-5: not the slate, not the build, not the fence assessment, not the qa
critique. My axes are the ones the prior critics did not own — AL-5 adjacency,
metric/signal design, and the alerting consequence of what this PR ships.

Read-only throughout. No git write verbs, no `gh` write calls, no AWS
mutations. Self-assessment capped at MODERATE per `self-ref-evidence-grade-rule`;
no STRONG grade is issued on the author's work.

---

## 1. Diff conformance — VERIFIED

| Assertion under review | Result | Receipt |
|---|---|---|
| Head SHA `6b75279f` | **CONFIRMED** | `gh pr view 369 --json headRefOid` -> `6b75279fcfb9e71c40766bf6bf5d037ca7766ba6` |
| Exactly two files | **CONFIRMED** | `gh pr diff 369 --name-only` -> 2 paths; `changedFiles: 2` |
| `story_warmer.py` +406/-98 | **CONFIRMED** | totals `+845/-98`; 845 - 439 (new test) = 406 |
| New test file 439 lines | **CONFIRMED** | diff hunk header `@@ -0,0 +1,439 @@` |
| Zero `terraform/**` bytes | **CONFIRMED** | `grep -c 'terraform/' pr369.diff` -> `0` |

The two paths are `src/autom8_asana/lambda_handlers/story_warmer.py` and
`tests/unit/lambda_handlers/test_story_warm_priority_offer.py`. Nothing else.
The terraform fence holds at byte level.

---

## 2. AL-5 adjacency — THE LOAD-BEARING FINDING

**Question posed:** is there any path by which the priority pass increases
frame-warm starvation, given `asana-AL5-offer-frame-stale-1143843662099250`
has been IN ALARM since 2026-08-14T08:01Z?

**Answer: No. The claim is verified from the code, and the true decoupling is
two layers deeper than the builder claimed.**

The builder's stated ground ("same wall clock, unchanged frame budget") is
true but *understates* the separation. I found two independent structural
barriers, either of which alone is sufficient.

### Barrier 1 — story-warm is strictly downstream of the frame loop

`_warm_story_caches_for_completed_entities` has exactly ONE call site in the
codebase:

- `src/autom8_asana/lambda_handlers/cache_warmer.py:1159` (sole caller;
  confirmed by `grep -rn` across `src/` excluding the module itself)

That call site sits **after** the frame-warm loop has fully completed:

- `cache_warmer.py:1115` — `checkpoint_mgr.clear_async()` under the comment
  `# All entities completed - clear checkpoint`
- `cache_warmer.py:1123` — GID mapping push
- `cache_warmer.py:1137` — account status push
- `cache_warmer.py:1159` — **story warm enters here**

No reordering *inside* story warming can consume wall clock *before* the frame
path, because the frame path has already finished and checkpointed by the time
the story warmer is entered. The `_build_warm_order` reshuffle
(`story_warmer.py:115`) operates entirely within a budget that the frame warm
has already declined to use.

Corollary on hard-timeout risk: the checkpoint is cleared at `:1115`, i.e.
*before* story warming begins. A story-warm overrun that SIGKILLs the Lambda
therefore cannot strand or lose frame-warm work — the frame result is already
committed. This was worth checking and it comes out clean.

### Barrier 2 — AL-5's input is not emitted by this Lambda at all

This is the finding the prior critics did not surface. `OfferFrameAgeSeconds`
is **not** a code-level `emit_metric` call. It is a CloudWatch **log-metric
filter**:

- `terraform/services/asana/observability_alarms.tf:446-461`
- `:450` — `log_group_name = var.asana_service_log_group`
  (default `/ecs/autom8y-asana-service`, `:441`)
- `:451` — `pattern = "{ ($.event = \"dataframe_cache_memory_lkg_serve\") && ($.extra.project_gid = \"...\") }"`
- `:456` — `value = "$.extra.age_seconds"`

AL-5's metric is synthesized from the **ECS service's serve-path log events**
on the **ECS log group**. PR #369 changes a **Lambda handler**. Different
process, different log group, different event name. There is no direct edge
from this diff to AL-5's input series.

The alarm description at `:531` independently corroborates the axis:
`AXIS: BUILD/SERVE (dataframe_cache_memory_lkg_serve extra.age_seconds = age
of the frame), NOT content.` The story warmer populates the **story** cache
(`client.stories.list_for_task_cached_async`), which is a different cache from
the DataFrame LKG frame the serve path reads.

### The one residual coupling, stated honestly

The only remaining channel is **shared Asana API pressure**: if the priority
pass raised the Asana call rate, 429s could delay frame builds and indirectly
raise served-frame age.

Assessment: **rate is unchanged.** The pass is gated by `_should_exit_early`
per chunk (`story_warmer.py`, chunk loop) and bounded by an unchanged
`_STORY_WARM_CONCURRENCY = 3` (`story_warmer.py:79`). In a fixed wall clock at
fixed concurrency, the call rate is the same; the pass changes *which* tasks
are fetched, not *how many* can be.

The subtler version of the worry — "pre-CC-5 entities 1-4 were largely
cache-warm short-circuits, so the same wall clock now buys MORE real API
calls" — is **contradicted by the receipted production evidence**: the warmer
never got past ~8,527 of ~14,808 tasks. Had entities 1-4 been predominantly
API-free short-circuits, the warmer would have blown through them and reached
offer. It did not. The pre-CC-5 rate was therefore already at the
concurrency bound, and substitution is genuinely neutral.

**Grade on the API-rate-neutrality inference: [MODERATE].** It is a reasoned
inference from the receipted zero, not a measured before/after call-rate
comparison. I did not run one and none exists. This is the weakest link in the
AL-5 analysis and I name it as such. It does not change the verdict, because
Barriers 1 and 2 are each independently sufficient and both are structural.

**Net: the diff cannot increase frame-warm starvation. The AL-5 ALARM state is
not attributable to this change and will not be worsened by it.**

---

## 3. Metric and signal design — SOUND

### 3.1 Namespace consistency — CORRECT, with a dashboard note

- New `StoryWarmEntity*` metrics call `emit_metric(...)` with **no namespace
  override** (`story_warmer.py:210-217`), so they land in
  `settings.observability.cloudwatch_namespace`, default `autom8/lambda`
  (`src/autom8_asana/settings.py:788-791`).
- AL-5's `OfferFrameAgeSeconds` lives in `Autom8y/AsanaSubstrateFreshness`
  (`observability_alarms.tf:429`).

This is the **right** call, not a defect: the new metrics are namespace-
consistent with their own siblings (`StoryWarmSuccess`, `StoryWarmFailure`,
`StoriesWarmed`, `StoryWarmDuration` all use the same default namespace). They
belong with the Lambda warmer family, not the substrate-freshness family.

*Note for whoever builds the dashboard:* correlating story-warm coverage
against AL-5 frame age is a cross-namespace widget. CloudWatch supports this;
it just needs to be known up front.

### 3.2 Cardinality — TIGHTLY BOUNDED

`emit_metric` always prepends an `environment` dimension
(`cloudwatch.py:52-57`) and appends caller dimensions. So each new series is
`{environment, entity_type}`.

With the default priority set `("offer",)` (`story_warmer.py:68`):
**1 environment x 1 entity_type x 4 metric names = 4 new custom metric series.**

The bounding mechanism is the priority gate at `story_warmer.py:204`
(`if not receipt.get("priority"): return`), which is *before* any
`emit_metric` call. Non-priority entities get the structured log only. This is
a deliberate and correct cardinality fence — without it the fleet would mint a
dimensioned series per entity.

### 3.3 Cost and quota (N-1) — NEGLIGIBLE, no concern

4 net-new `put_metric_data` calls/run, confirmed against the critique's
independent count (`CRITIQUE...:121` — BEFORE 4/run, AFTER 8/run).

At the receipted cadence (324+ runs / 14 days ~= 23 runs/day):
~92 extra PutMetricData requests/day (~2.8k/month). At CloudWatch's
$0.01/1,000 requests that is cents/month; 4 custom series at $0.30/series is
~$1.20/month. Default PutMetricData quota is far above this. **No cost or
quota concern.**

### 3.4 Failure-path emission (partial-pass honesty) — CONFIRMED AT THE SITE

I verified the emission sites directly rather than inheriting qa's three-
altitude finding.

`_emit_entity_receipt(receipt, invocation_id)` is called at
`story_warmer.py:453`, in the outer loop, **unconditionally after**
`_warm_entity_stories` returns. `_warm_entity_stories` (`:220`) is documented
and implemented as never-raising: it carries a broad-catch that converts a
per-entity failure into `skip_reason = "entity_error"` and returns the receipt.

Consequently a receipt is emitted — with explicit zeros and a populated
`task_count` denominator — on **every** terminal path:
`no_project_gid`, `no_cache_entry`, `no_gid_column`, `entity_error`,
budget-exhausted, and full success. The denominator-first ordering at
`:210` (`StoryWarmEntityTaskCount` emitted before `StoryWarmEntitySuccess`)
is the correct choice: a success count without its denominator cannot be read
as coverage.

`emit_metric` itself degrades gracefully (`cloudwatch.py:59-80`, broad-catch
around client creation *and* the call), so a metric failure cannot abort the
warm cycle. Observability never fails the handler. Correct.

**This satisfies the partial-pass honesty requirement.** The absent-vs-zero
defect the receipt exists to close is genuinely closed on the emission path.

### 3.5 One new observation the prior critics did not cost — operator-lever scaling

`_emit_entity_receipt` is a **synchronous** function issuing **blocking**
boto3 `put_metric_data` calls, invoked from inside the async warm loop at
`story_warmer.py:453`. Each call blocks the event loop for a network round
trip (~20-50ms typical), interleaved *between entities* rather than batched at
the end.

At the default `("offer",)` this is 4 blocking calls once per run — immaterial,
and it mirrors the pre-existing aggregate-emit pattern.

**But it scales linearly with the priority set.** If the operator ever widens
`ASANA_STORY_WARM_PRIORITY_ENTITIES` to N entities, that becomes 4N blocking
event-loop stalls interleaved mid-warm, consuming story-warm budget that would
otherwise fetch stories. This is a genuine (if modest) argument *reinforcing*
why the lever is OPERATOR-RESERVED, and it belongs in the lever's operating
notes. It is **not** a defect in the Tier-1 default and requires no change now.

---

## 4. Regression surface — CLEAN

| Check | Result | Receipt |
|---|---|---|
| Default is `("offer",)` | **CONFIRMED** | `story_warmer.py:68` |
| Default pinned by test | **CONFIRMED** | `test_default_priority_is_offers_only` asserts both the constant and `_resolve_priority_entities({}) == ("offer",)` |
| Concurrency unchanged | **CONFIRMED** | `story_warmer.py:79` `= 3`; tripwire test `test_concurrency_envelope_is_not_raised` |
| Empty-string revert lever | **CONFIRMED** | `_resolve_priority_entities` returns `()` for `""`; `test_empty_env_var_is_the_revert_lever` |
| No additional config surfaces read | **CONFIRMED** | only `os.environ` read is `STORY_WARM_PRIORITY_ENV_VAR` (`:74`); `grep` for other env reads in the module returns nothing else |
| `__all__` underscore exposure | **DISCLOSED SMELL, accepted** | exports `_build_warm_order`, `_resolve_priority_entities`, `_warm_entity_stories`; needed for the test import; lint-clean in CI |

### 4.1 A raise-path I chased down and cleared

`get_project_gid(entity_type)` is invoked at `story_warmer.py:433` as an
argument expression — i.e. **outside** the per-entity broad-catch inside
`_warm_entity_stories`. If that resolver raised, the whole loop would abort
into the outer handler and **no** receipts would be emitted for any entity —
reintroducing the exact absent-vs-zero defect this PR closes, on one path, for
a metric that has no alarm on it.

This matters more than usual here because `"offer"` is now injected into the
order **unconditionally**, whether or not it appears in `completed_entities`.

I traced the injected callable and it is **safe**:

- `cache_warmer.py:879-880` injects a closure over
  `registry.get_project_gid`, where `registry` is an `EntityProjectRegistry`.
- `src/autom8_asana/services/resolver.py:168-190` — that method returns
  `str | None` and **returns `None`** for an unregistered entity type. It does
  not raise.

So the worst case is `skip_reason = "no_project_gid"` with an explicit,
emitted zero — the honest path, exactly as designed.

Worth recording for future readers: there is a **different**, same-named
`get_project_gid` at `src/autom8_asana/core/project_registry.py:115-133` which
**does** raise `KeyError` on an unknown name. It is *not* the one injected
here. Anyone who later rewires this parameter to the `project_registry`
variant would silently convert the safe path into a total story-warm abort.
That is a latent trap worth a comment, not a blocker for this merge.

### 4.2 Precondition that makes the PR non-vacuous — CONFIRMED

`"offer"` resolves. `src/autom8_asana/core/entity_registry.py:540` declares
the descriptor with `primary_project_gid = "1143843662099250"` (`:545`) —
**the same GID in the AL-5 alarm name**
`asana-AL5-offer-frame-stale-1143843662099250`. The pass targets precisely the
project the live alarm watches, and it resolves the GID through the registry
rather than hardcoding it in `src/`, as the module docstring claims.

### 4.3 Changed field semantics — no consumer, safe

`stats["skipped"]` was initialized but never incremented pre-CC-5 (always 0);
it now counts non-enumerated entities. The return value is **discarded** at
the sole call site (`cache_warmer.py:1159` — `await` with no assignment), and
no other consumer exists. No downstream breakage.

---

## 5. Carries — ALL DISCLOSED (confirmed, not re-litigated)

Per instruction I confirm disclosure only and take no position on the merits.

| Carry | Disclosed at |
|---|---|
| FLAG-1 config-boundary / Tier-2 affordance | `ASSESSMENT-cc5-tier1-fence-2026-08-14.md:225` |
| FLAG-2 log-only cost signal for entities 1-4 | `ASSESSMENT...:243` |
| FLAG-3 starvation redistribution | `ASSESSMENT...:266` |
| N-1 4 net-new put_metric_data/run | `CRITIQUE...:127`, `:190` |
| N-2 1 net-new cache read on absent-offer path | `CRITIQUE...:136`, `:191` |
| N-3 fetch-without-persist residual | `CRITIQUE...:173`, `:192` |
| R-9 trap carried verbatim | `BUILD-cc5-tier1-offers-warm-2026-08-14.md:34` |
| No clean-regime claim | `BUILD...:41`, `:309`; `CRITIQUE...:218`; PR body ("no clean-regime claim is made") |

I independently confirm **FLAG-2 is accurate**: the displacement cost to
entities 1-4 is log-only and not alarmable, enforced by the priority gate at
`story_warmer.py:204`. I also confirm **no clean-regime claim appears anywhere
in the PR body or the build note** — the PR body explicitly states the
opposite and carries the R-9 segmentation warning.

---

## 6. CI state — ALL GREEN

Polled to settlement (`gh pr checks 369`, 3 polls over ~90s):

**25 pass / 0 fail / 0 pending / 3 skipping.**

All four required test shards green (`ci / Test (shard 1..4/4)`), plus
`ci / Aggregate Coverage Gate`, `ci / Lint & Type Check`, `Analyze (python)`,
`CodeQL`, `gitleaks`, `Aegis Memory & Coverage Gate`, `Fleet Schema
Governance`, `RUF100 Drift Guard`, `MCP Island Suite`.

Skipping (non-required, path-filtered): `ci / Convention Check`,
`ci / Integration Tests`, `[code]smith`.

Green CI also independently clears the pre-existing
`tests/unit/lambda_handlers/test_story_warming.py`, which this PR does not
modify but whose subject behavior it changes (`story_warm_complete` became
unconditional).

**No GO is being rendered on a pending check.**

---

## 7. Merge-hygiene finding — branch is BEHIND

`mergeStateStatus: BEHIND`, `mergeable: MERGEABLE`.

Main is ahead by exactly **one** commit: `2ea46474 docs(coc): land
chain-of-custody paper lineage + phase-2 rulings (#367)` — **15 files, all
under `.ledge/**`, zero overlap** with either PR file (verified by
`git show --name-only 2ea46474 | grep -E "story_warmer|test_story_warm"` ->
no match).

So BEHIND is benign in content. The operational consequence is procedural:
if the branch is updated before merge, the head SHA changes from `6b75279f`
and **CI must re-green at the new head** before the merge word is spoken.

---

## 8. Conditions on the GO

None require a code change.

1. **AL-5 reading discipline (R-9).** Record the merge and deploy timestamps
   and segment AL-5 readings at that boundary. A post-deploy green may be the
   warm fix, the deploy, or neither — it is not evidence of regime change.
   This PR does not address frame-warm and makes no regime claim; do not let
   one be inferred downstream. Note additionally that per
   `observability_alarms.tf:495-503` AL-5 is *already* pending a re-baseline
   behind FIX-N-C1 (#339), so no AL-5 trend reading is comparable across that
   boundary either.

2. **The new series has no alarm.** `StoryWarmEntity{TaskCount,Success,
   Failure,Reached}` ship with **zero** terraform consumers (verified:
   `grep -rn "StoryWarm" terraform/` returns nothing). The RED/GREEN
   discriminator this PR builds is *observable but not alerting*. If the pass
   silently regresses — e.g. offer stops resolving and every run emits
   `StoryWarmEntityReached = 0` — nothing pages. This is correctly sequenced
   (terraform is fenced out of this PR by design, and zero terraform bytes was
   a review requirement), so it is a condition, not a blocker. Recommended
   follow-on: alarm on `StoryWarmEntityReached{entity_type=offer}` sustained
   at 0, and on `StoryWarmEntitySuccess` flatlining at 0 while
   `StoryWarmEntityTaskCount > 0`. Route to Platform Engineer.

3. **Operator-lever operating note (§3.5).** Widening
   `ASANA_STORY_WARM_PRIORITY_ENTITIES` to N entities multiplies blocking,
   event-loop-stalling `put_metric_data` calls to 4N, interleaved mid-warm.
   Record this alongside FLAG-1/DW-COC-05 in the lever's operator notes.

4. **Re-green if updated.** If the branch is brought up to date to clear
   BEHIND, re-confirm all required contexts green at the new head SHA before
   merging. This GO is scoped to `6b75279f`.

---

## 9. Acid test

> *"Can we catch degradation before customers do with this monitoring?"*

**For the specific degradation this PR targets: yes, and that is the point of
the PR.** The per-entity receipt converts an *inferred* zero into a *measured*
one, and makes the two negatives distinguishable
(`enumerated=True, success=0` = starvation; `enumerated=False` = never
reached). That is a real observability improvement over the aggregate counter,
which — as the test suite demonstrates — reads identically (200) across the
broken and fixed orderings.

**For the alerting half: not yet**, per Condition 2. Detection exists; paging
does not. The gap is known, correctly sequenced behind the terraform fence,
and does not warrant blocking a merge that strictly increases observability.

---

## 10. Verdict

**GO-WITH-CONDITIONS** for merging PR #369 at head `6b75279f` to `main`.

- Diff conforms exactly to the declared scope; terraform fence holds at byte level.
- The frame-warm starvation hypothesis is **structurally refuted** on two
  independent grounds (§2), verified from code rather than inherited from the
  build note.
- Metric design is sound: bounded cardinality, namespace-consistent with its
  own family, denominator-first, honest on every failure path, negligible cost.
- Regression surface is clean; the one raise-path worth chasing was chased and
  cleared (§4.1).
- CI is fully green with zero pending.
- All carries disclosed; no clean-regime claim anywhere.

Conditions 1-4 are operational/merge-hygiene and none block the merge word.

Evidence grade on this review: **[MODERATE]** per `self-ref-evidence-grade-rule`
and the reviewer's declared cap. Findings rest on direct file:line inspection
and command receipts reproduced inline; the single inference not backed by a
present-tense probe (Asana API-rate neutrality, §2) is labelled as such at its
assertion site.
