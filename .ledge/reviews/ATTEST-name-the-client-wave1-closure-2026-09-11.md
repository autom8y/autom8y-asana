# ATTEST — `name-the-client` wave 1 CLOSURE

**Clause (c2) is OPEN and is not attested here (R-141, carried into the READ epoch as item 3); clause (d) is attested PROBE LIVE / SUBJECT DARK and its disposition is REFUSED-CORRECTLY, concurred.**

**R3 · RITE-DISJOINT PRODUCT-ALTITUDE ATTESTATION.** Attester: eunomia / `verification-auditor`.
Invoked by seat `calendar-integration-locus` under sitting IX **R-138**, **R-141**, **R-147**.
Date: 2026-09-11. Read-only against production (CloudWatch reads; git reads at explicit refs).
Two local mutants applied inside a private probe worktree and reverted; **no repo code, config or
settings modified**. **Self-cap: MODERATE** per `self-ref-evidence-grade-rule`.

> Nothing below is inherited. The seat's framing, the seat's numbers, and every subagent report
> reaching me were treated as claims, not facts. Where I could not re-derive, I wrote NOT-ATTESTED
> or filed the gap in §UNVERIFIED.

---

## VERDICT

| leg | bar (as amended at `origin/main`) | verdict |
|---|---|---|
| **(a)** | a LIVE attributed booking line NAMING the office | **ATTESTED** |
| **(b)** | two-sided — a failure for the SAME office also names it, with its kind, never blank | **ATTESTED** (predecessor flag **F-3 DISCHARGED**; a residual is disclosed, see FLAG-A) |
| **(c1)** | anti-anecdote — ONE office carrying BOTH poles | **ATTESTED** (15 offices carry both poles in a single day) |
| **(c2)** | coverage over a ruled population | **NOT ATTESTED — CARRIED OPEN** per R-141. Not graded. |
| **(d)** | activation refusal, demonstrated two-sided | **ATTESTED — PROBE LIVE / SUBJECT DARK**; R-147's `REFUSED-CORRECTLY` disposition **CONCURRED** |

### **OVERALL: wave 1 is CLOSED-WITH-REFUSAL.**

(a), (b) and (c1) stand up on receipts I took today. (d) is attested in the only honest form the
substrate permits: **the probe is live and has teeth; the subject it would gate is dark.** (c2)
remains open and nothing here may be read as closing it.

---

## §1 — Bar and record: what I read, and at which ref

Every checkout on this machine is on a stale branch. Governance reads were taken at explicit refs.

| artifact | ref read | note |
|---|---|---|
| `.know/telos/name-the-client.md` | `origin/main` `1b7bf4fa` | the bar, as amended 2026-09-08 (R-17) + 2026-09-10 (R-78 split, RATIF-VI-D1 → (c1)=ONE office) |
| `RATIFICATION-decision-space-sitting-IX-2026-09-11.md` | `origin/docs/ratification-sitting-ix-2026-09-11` `ba8342a9` | **asana PR #438 is OPEN, not merged** — the record is NOT on `origin/main`; §6 and §7 (R-147) read there |
| `ATTEST-name-the-client-wave1-legs-abc1-2026-09-10.md` | `origin/main` | predecessor: (a) ATTESTED · (b) ATTESTED-WITH-FLAG (F-3) · (c1) ATTESTED · (d) UNBUILT · wave 1 NOT CLOSED |

`(c1)`'s operative bar is **ONE office carrying both poles** (RATIF-VI-D1). Anyone holding R-79's
`>= 2` is holding a superseded gate. I graded against ONE and report the margin.

---

## §2 — (a) LIVE ATTRIBUTED BOOKING NAMING THE OFFICE — **ATTESTED**

Fresh today. Not inherited.

**Receipt A1** — Logs Insights, `/aws/lambda/autom8-email-booking-intake`, query
`9461b49f-f87f-4f69-960c-2541716faf37`, window 2026-09-08T00:00:00Z → 2026-09-11T23:59:59Z,
recordsScanned **5,873**, recordsMatched **126**:

```
fields @timestamp, office_identity_kind, event
| filter event = "booking_completed"
| stats count(*) as n by bin(1d) as day, office_identity_kind | sort day asc
```

| day | `office_identity_kind` | n |
|---|---|---|
| 2026-09-08 | *(field absent from the line)* | 21 |
| 2026-09-09 | *(field absent)* | 26 |
| 2026-09-09 | `resolved` | 2 |
| **2026-09-10** | **`resolved`** | **39** |
| **2026-09-11** | **`resolved`** | **38** |

**The in-query control fires on the identical shape.** The 09-08 and 09-09 rows carry NO
`office_identity_kind` field at all — that is the ABSENT class, produced by the same query, in the
same group, over the same field. On 09-10 and 09-11 **every** `booking_completed` line carries the
field and every one reads `resolved`. Zero unresolved, zero field-absent, on both live days.

**Receipt A2 — shape of a live line** (query `42606579-018d-4a0c-9cef-c82ae2cc97e7`, 09-11, one
sample; client name elided per fence, guid8 retained):

```json
{"office_name": "<elided>", "chiropractor_guid": "83d69605-***", "office_identity_kind": "resolved",
 "status": "scheduled", "appointment_id": "…", "event": "booking_completed",
 "trace_id": "9591b51f912b65dc5e039db62ffd9459", "timestamp": "2026-09-11T21:04:11.666799Z"}
```

The line names the office on its own face — `office_name` plus a `chiropractor_guid` prefix plus an
explicit `office_identity_kind`. No cross-service join, no human lookup. **(a) is met.**

---

## §3 — (b) TWO-SIDED, WITH A KIND, NEVER BLANK — **ATTESTED**; F-3 DISCHARGED

**Receipt B1** — same log group, query `6a8c0f92-e50a-459f-9741-269eacf427b7`, same window,
recordsScanned **36,797**, recordsMatched **1,383**, over the four failure families:

| day | event | kind | n |
|---|---|---|---|
| 09-08 | `booking_gate_declined` / `stage_exception` / `ad_lead_gate_refused` | *(field absent)* | 70 / 243 / 84 |
| 09-09 | + `booking_intake_fault` | *(field absent)* | 63 / 225 / 83 / 90 |
| 09-10 | mixed — rollout day | `resolved` 192 · `absent` 46 · *(field absent)* 124 | |
| **09-11** | `stage_exception` | `resolved` **65** · `absent` **30** | |
| **09-11** | `booking_intake_fault` | `resolved` **14** · `absent` **24** | |
| **09-11** | `ad_lead_gate_refused` | `resolved` **29** | |
| **09-11** | `booking_gate_declined` | `resolved` **1** | |

**Receipt B2 — the never-blank probe, stated as a number.** Query
`15fd55ce-e5c3-46e7-835a-06d5d0faa4d0`, all five event families, 09-10 → 09-11:

```
| stats count(*) as total, sum(ispresent(office_identity_kind)) as has_kind,
        sum(office_identity_kind = "") as blank_kind by bin(1d) as day
```

| day | total | has_kind | **blank_kind** |
|---|---|---|---|
| 2026-09-10 | 401 | 277 | **0** |
| **2026-09-11** | **202** | **202** | **0** |

On 2026-09-11 the kind is present on **202 of 202** lines and blank on **zero**. The 09-10 row is
the paired control on the identical shape: 124 of 401 lines carry no kind field at all, so the
instrument demonstrably CAN produce the absent class — it simply stopped doing so.

**F-3 (predecessor, MEDIUM): DISCHARGED.** The flag was *"no direct synthetic-violation probe on
`booking_gate_declined`'s office fields; the pre-existing test stays GREEN if that site's cure is
reverted."* Re-derived own-hands in the `autom8y` repo:

- `git merge-base --is-ancestor d1ac56d5 origin/main` → **exit 0**; `origin/main` = `bb485521`.
- `d1ac56d5` = *"test(ebi): direct probe for booking_gate_declined office attribution (#2141)"*,
  2026-09-10 01:04:53 -0400, adding `services/email-booking-intake/tests/test_office_attribution_on_firing_failures.py` (+63).
- The probe is **on main**: `origin/main:services/email-booking-intake/tests/test_office_attribution_on_firing_failures.py:377`
  `async def test_booking_gate_declined_names_the_office(...)`, asserting via `_assert_names_the_office(kwargs, "booking_gate_declined")` at `:384`.

**(b) is met on the named pole. See FLAG-A for the disclosed residual.**

---

## §4 — (c1) ANTI-ANECDOTE: ONE OFFICE, BOTH POLES — **ATTESTED**

**Receipt C1** — query `130ed2c1-2a67-4bba-903c-59a5e28cf214`, **2026-09-11 alone**, all five event
families, recordsScanned **4,303**, recordsMatched **203**:

```
| stats sum(event="booking_completed") as pos, sum(event!="booking_completed") as neg,
        count(*) as tot by chiropractor_guid, office_identity_kind | sort pos desc
```

**Fifteen offices carry BOTH poles in that single day**, every one `office_identity_kind=resolved`:

| guid8 | pos | neg | | guid8 | pos | neg |
|---|---|---|---|---|---|---|
| `c2ab6637` | 8 | 11 | | `15caa02c` | 2 | 2 |
| `4ec260bf` | 4 | 2 | | `8e56f6e1` | 1 | 1 |
| `ca70baa8` | 4 | 3 | | `ccb52f4c` | 1 | 47 |
| `d167d635` | 3 | 4 | | `79be1b75` | 1 | 10 |
| `7a1e83fd` | 3 | 4 | | `9fcf1507` | 1 | 1 |
| `087d7de5` | 2 | 2 | | `83d69605` | 1 | 1 |
| `06a9afb0` | 2 | 1 | | `816db7b3` | 1 | 1 |
| | | | | `b1569808` | 1 | 1 |

**The bar needs one. Fifteen clear it, on one day, without reaching for a same-trace pairing.**
That margin also dissolves the predecessor's FLAG-c1 (the claimed pair was same-trace and therefore
narrower than it read): these fifteen are day-scoped and independent of trace coincidence.

**The in-query negative control is inside the same result set** — `chiropractor_guid=***` with
`office_identity_kind=absent`: **pos=0, neg=52**. The identical query shape still produces a
guid-less, kind=`absent` class. The zero is a measured zero, not a dead query.

---

## §5 — (c2) COVERAGE — **CARRIED OPEN, NOT ATTESTED**

Per **R-141**: *"Carried open into READ as item 3. Wave 1 closes on (d) built + R3 attesting; the
closure record's first line says (c2) is open."* Line one of this file says exactly that.

**What (c2) waits on**, re-derived from the bar and the record, not from the seat's summary:

1. **WS-JOIN plus an identity ruling.** The telos records that (c2) *"waits on WS-JOIN plus an identity ruling; two lanes independently proved the un-split form unfalsifiable"* — the universal quantifier over an unenumerable set was retired as a RENDERING by R-78, not as an INSTRUCTION.
2. **A ruled denominator.** BOOKED OPEN. Sitting IX §2 books the **identity one-pager (F-1..F-7) behind (c2)** as awaiting an **operator sitting (R-110)** — watcher: **operator**.
3. **The `kind=absent` residual** (FLAG-A below) is arithmetically inside any future coverage denominator; sitting IX §2 books its triage (**S-4 malformed-GUID**) as **not asked in this sitting**, watcher **NO WATCHER**.

I did not grade (c2) and I did not size it. **"All active clients" survives in full as the
operator's standing requirement.**

---

## §6 — (d) ACTIVATION REFUSAL — **ATTESTED: PROBE LIVE / SUBJECT DARK**

### §6.1 PROBE LIVE — re-derived by running it

Probe worktree `wt.eunomia.probe-activation-smoke.20260911T211009.a1b2`, detached at
`fe82e5ff` (`feat/activation-smoke-referent`), which has `900cb133`
(`feat/activation-smoke-module-land`, asana **#439**) as a **confirmed ancestor**
(`git merge-base --is-ancestor` → exit 0). The referent commit is **purely additive** — it touches
only `activation_referent.py` (+127) and `test_activation_referent.py` (+266) and does **not**
modify the smoke tests, so running both at `fe82e5ff` is equivalent to running each at its own head.

**Import-resolution proof** (a fresh worktree cannot sync a venv — CodeArtifact 401 — so the main
checkout's interpreter was used with `PYTHONPATH` pointed at the worktree):

```
autom8_asana.__file__        = .../wt.eunomia.probe-activation-smoke.20260911T211009.a1b2/src/autom8_asana/__init__.py
activation_smoke.__file__    = .../wt.eunomia.probe-activation-smoke.20260911T211009.a1b2/src/autom8_asana/lifecycle/activation_smoke.py
```

Imports resolve to the worktree, not to the main checkout. The runs below are of the PR code.

**Counts — exactly as claimed, exit codes measured unpiped:**

| file | result | rc |
|---|---|---|
| `tests/unit/lifecycle/test_activation_smoke.py` | **43 passed** in 0.81s | **0** |
| `tests/unit/lifecycle/test_activation_referent.py` | **32 passed** in 0.60s | **0** |
| both together | **75 passed** in 1.32s | 0 |

**Skip-evasion audit: zero.** `grep -c "@pytest.mark.skip|@pytest.mark.xfail|pytest.skip("` returns
**0** on both files. The 75 are 75 executed assertions' worth, not 75 collected-and-skipped.

**Mutant 1 — the one my dispatch named**: `activation_referent.py:102`,
`activating_buckets=frozenset({AccountActivity.ACTIVATING.value})` → `…ACTIVE.value`.

> **14 RED**, 61 passed, rc=1. Both poles bit:
> `test_healthy_pipe_activates_under_the_offer_referent` **RED** and all three parameterisations of
> `test_broken_pipe_is_refused_and_names_the_break[office_name… | failure_probe… | pipe_proof_at…]`
> **RED**, plus `test_the_two_sides_differ_only_in_facts`, `test_the_activating_group_is_the_activating_bucket[×3]`,
> `test_nothing_outside_the_activating_group_is_activating[×2]`, `test_crossing_into_activating_is_observed_with_the_referent_name`,
> `test_reentering_activating_from_active_is_an_activation_by_the_hook_law`,
> `test_a_non_activation_move_does_not_gate_even_with_no_facts`,
> `test_moves_that_do_not_enter_activating_are_not_observed[IMPLEMENTING-ACTIVE]`.

Reverted with `git checkout --`; `git status --porcelain` → 0 lines; re-run **75 passed, rc=0**.

**Mutant 2 — mine, chosen because mutant 1 leaves the smoke module's 43 untested for teeth.**
`activation_smoke.py:718`, `if report.passed:` → `if True:` — i.e. **fail-open: a smoke whose checks
FAILED permits activation anyway.** This is the exact defect clause (d) exists to refuse.

> **15 RED**, 60 passed, rc=1. **All seven** broken-pipe parameterisations went RED —
> `test_broken_pipe_refuses_activation_and_names_the_break[office-never-resolved | office-resolves-blank |
> failure-path-unproven | failure-path-goes-blank | failure-names-office-but-not-kind | no-proof-at-all |
> proof-is-stale]` — plus `test_the_two_sides_differ_only_in_facts` (both files),
> `test_a_raising_probe_is_a_failure_never_a_skip`, `test_a_probe_returning_an_undeclared_kind_is_refused`,
> `test_probes_cannot_name_themselves`, and the three referent broken-pipe params.

Reverted; `git status --porcelain` → 0 lines; re-run **75 passed, rc=0**.

**PROBE LIVE verdict: the instrument is real and two-sided.** The negative pole is not decorative —
a fail-open mutation is caught by seven independent parameterisations that each name a distinct
break. `43 + 32` is confirmed at the claimed counts with no skip evasions and demonstrated teeth on
both poles.

### §6.2 SUBJECT DARK — R-147's two load-bearing claims, re-derived by me

R-147 rests on two claims. I re-derived both and did **not** accept either from the seat.

**Claim (i) — `LifecycleEngine` has no production constructor on a live path. CONFIRMED.**

`git grep -n -E 'LifecycleEngine' origin/main -- src/` returns exactly **one** construction site:

- `src/autom8_asana/automation/workflows/pipeline_transition.py:196` — `self._engine = LifecycleEngine(self._client, self._config)`, inside `PipelineTransitionWorkflow` (`:64`).
- Every other `src/` hit is a docstring, a `TYPE_CHECKING` import, an `__init__` re-export, or an injected parameter (`lifecycle/dispatch.py:31`).

Tracing the owner across the **whole tree** at `origin/main`,
`git grep -n "PipelineTransitionWorkflow" origin/main` outside its own file yields **zero callers**:
3 hits in `.know/feat/automation-engine.md`, 5 in `docs/guides/`, and 19 in
`tests/unit/automation/workflows/test_pipeline_transition.py`. **No handler, no lambda, no CLI, no
route, no scheduler constructs it.** There is no workflow-registry entry either — the literal
`"pipeline-transition"` (its `workflow_id`) has **zero** `src/` references outside the file.

The webhook seam is likewise unwired:

- `origin/main:src/autom8_asana/api/routes/webhooks.py:184` — verbatim: `_dispatcher: WebhookDispatcher = NoOpDispatcher()`.
- `set_dispatcher` at `webhooks.py:187` has **no production caller**: the only other references are `docs/guides/webhooks.md` and `tests/unit/api/routes/test_webhooks.py`.
- The repo's own knowledge records why it cannot be wired as-is — `.know/feat/webhooks.md:100` names the signature mismatch (`dispatch(task)` vs `handle_event(...)`) and `ADR-ws7-actor-attribution-seam.md:152` carries it as PRECONDITION-4.

**Claim (ii) — zero lifecycle-family events over 30 days, against a positive control. CONFIRMED,
and I corrected the query shape to make the zero load-bearing.**

My first attempt used `filter event in [...]` and returned `matched=0` — but at
`recordsScanned=12,604`, against a control that scanned **7,145,170** on the same group and window.
**A zero drawn from a 12,604-record scan of a 7.1M-record corpus is not a receipt.** The `in [...]`
form is field-index-optimised and does not scan the corpus; I discarded it. Re-run on the shape
**identical to the control**:

| query | shape | window | recordsScanned | **recordsMatched** |
|---|---|---|---|---|
| `e917f02d-…` | `filter event like /^lifecycle_transition_｜^stage_transition_emitted｜^pipeline_transition_｜^webhook_task_dispatched_noop/` | last 30d | **7,281,524** | **0** |
| `5bc41fe0-…` **(control)** | `filter event like /^jwks_/` | last 30d | **7,145,170** | **17,773** (`jwks_fetch_start` 8,887 · `jwks_fetch_success` 8,886) |

Same log group `/ecs/autom8y-asana-service`, same 30-day window, same `like`-regex shape, full-corpus
scan on both. **The control fires 17,773 times; the lifecycle family fires zero.** Note the zero
covers `webhook_task_dispatched_noop` too — even the *no-op* leg of the inbound route emits nothing,
so the route is not merely unwired downstream, it is not being exercised at all.

**Supporting re-derivation — `activate_campaign` is DAG-unreachable and its handler is a stub:**

- `config/lifecycle_stages.yaml:166-167` — `init_actions:` / `- type: activate_campaign`, inside the `month1` stage.
- The literal `month1` occurs **exactly once** in the whole file, at `:149` — its own key. **No stage targets it.**
- `src/autom8_asana/lifecycle/init_actions.py:588` maps `"activate_campaign": CampaignHandler`, whose docstring reads verbatim: *"For now: log the action and return success. Actual campaign API integration is deferred to production implementation."*

### §6.3 The ruling I was asked to make — is `REFUSED-CORRECTLY` correct?

**Yes. I concur with R-147, and my own adversarial sweep for a missed activation path found none.**

I searched beyond the seat's frame for any other consumer of `OFFER_CLASSIFIER` activating sections
that **acts** on a transition. Three live candidates exist; **none acts**:

| candidate | keys on activating? | acts? | receipt |
|---|---|---|---|
| `reconciliation/processor.py` | **YES** — `OFFER_ACTIVITY_VALID_UNIT_SECTIONS[AccountActivity.ACTIVATING]` at `:69-71`; classify at `:602` | **NO** | `lambda_handlers/reconciliation_runner.py:125` hardcodes `ReconciliationConfig(dry_run=True)  # SHADOW MODE: always dry_run`; `:138` `execute_actions(..., dry_run=True)`; `:61` gates the whole handler on `ASANA_RECONCILIATION_SHADOW_ENABLED`. **Live check:** `/aws/lambda/autom8-asana-unit-reconciliation`, 30d (query `f7bf6fd4-…`): **553 `bootstrap_complete`, and ZERO reconciliation-family events.** It boots and emits nothing. |
| `lambda_handlers/traffic_offer_divergence_tripwire.py` | **YES** — `OFFER_CLASSIFIER.billable_sections()` = {active, activating} at `:458` | **NO** | Module docstring, verbatim: *"`cloudwatch:PutMetricData`. NO Asana write scope. NO DB write."* It alarms; it does not act. |
| `lambda_handlers/onboarding_walkthrough.py` | **NO** — `workflow.py:359` states it uses the section GID and *"never the Offers `OFFER_CLASSIFIER`"* | **NO (and it is itself dark)** | `/aws/lambda/autom8-asana-onboarding-walkthrough`, 30d (query `63b60140-…`): **23 `lambda_onboarding_walkthrough_started` and 23 `lambda_onboarding_walkthrough_validation_failed`.** The activation-adjacent path nearest to a real onboarding act is failing validation on **100% of its invocations**. |

**There is no live path on which an account is activated by this service.** Wiring a refusal gate
onto `LifecycleEngine` would have produced an instrument that can never fire — *a declared
instrument with no enforcement on the thing it protects*, which is the precise defect class
`name-the-client` exists to close. **Refusing to wire it is the correct act, and the refusal is
itself the honest form of clause (d).**

**A finding for the READ epoch, offered not adjudicated.** R-147 migrates (d) to R2 on *"a scheduled
sweep of the Offer project's section membership, diffed run-to-run, calling the hook in dry-run."*
**That substrate already exists in deployed form** — `/aws/lambda/autom8-asana-unit-reconciliation`
is a scheduled, deployed, dry-run-hardcoded consumer of `OFFER_CLASSIFIER` that already distinguishes
`ACTIVATING`. R2 may be a re-arming of an existing dark instrument rather than a new build. **This
is a finding, not a recommendation, and not a ruling.**

---

## §7 — FLAGS

**FLAG-A — the `kind=absent` residual is real, is inside any future (c2) denominator, and has NO
WATCHER.** On 2026-09-11, **54 of 202** failure lines carry `office_identity_kind=absent`
(`stage_exception` 30 + `booking_intake_fault` 24). `absent` is a **kind** and is **non-blank**, so
the bar's *"never blank"* holds and (b) is met as written — but these lines do **not** name an
office. Within Receipt C1 the residual resolves as `chiropractor_guid=***` / `absent` (52 lines) and
`e5a68603-***` / `absent` (2 lines). Sitting IX §2 books the triage (**S-4 malformed-GUID**,
*"not asked in this sitting"*) with **NO WATCHER**. Severity **MEDIUM** — it does not reduce (b),
it sizes (c2).

**FLAG-B — a guid8 present while the kind reads `absent`.** `e5a68603-***` carries a resolvable
8-hex prefix on 2 lines whose `office_identity_kind` is `absent`. Either the kind is computed from a
different field than the one carrying the prefix, or the prefix survives a resolution that failed.
**Not diagnosed by me.** Severity **LOW**, but it is a two-field disagreement inside the very
instrument this wave shipped, and it should not be inherited as noise.

**FLAG-C — the seat's lambda-group census is off by two.** Sitting IX §7 asserts *"the ten
`/aws/lambda/autom8-asana-*` groups (26.7M)."* `aws logs describe-log-groups
--log-group-name-prefix "/aws/lambda/autom8-asana"` returns **twelve** groups. The substance of
R-147 does not rest on this count and my `/ecs/` receipt is unaffected, but the number as written is
not what the platform returns. Severity **LOW**.

**FLAG-D — a `matched=0` in §7 was drawn from a shape that does not scan the corpus.** The
`filter event in [...]` form scans ~12.6k records where the `like` form scans ~7.28M on the same
group and window. §7's zero is **true** — I re-derived it on the full-scan shape — but had it been
false, the `in [...]` shape would not reliably have shown it. Any future dark-claim should pin the
scan shape to the control's shape. Severity **LOW (method, not conclusion)**.

**FLAG-E — the record authorising this closure is not on `origin/main`.** `.ledge/decisions/RATIFICATION-decision-space-sitting-IX-2026-09-11.md`
lives only on `origin/docs/ratification-sitting-ix-2026-09-11` (**PR #438 OPEN**). A reader taking
`origin/main` as the substrate of record will not find R-138/R-141/R-147. Severity **MEDIUM** for
provenance, not for substance.

**No overclaim found in R-147's two load-bearing claims.** Both were re-derived and both held.
The seat's control figure (*"positive controls of 8,889"*) reads against my `jwks_fetch_start`
8,887 / `jwks_fetch_success` 8,886 — a window-boundary delta of ≤3, non-material, recorded so it is
not mistaken for a discrepancy later.

---

## §8 — UNVERIFIED (what I could not or did not re-derive)

1. **The twelve `/aws/lambda/autom8-asana-*` groups were NOT swept for lifecycle events.** My dark receipt covers `/ecs/autom8y-asana-service` only, as dispatched. The seat's 26.7M-record figure across those groups is **NOT-ATTESTED**.
2. **Ground truth for `resolved`.** I verified that lines carry `office_identity_kind=resolved` and a guid8. I did **not** verify that any guid8 maps to the correct real-world office — no independent join was available to me. `resolved` is attested as an instrument state, not as a correctness proof.
3. **CI status of #439 and the referent branch.** I ran the tests myself, locally, at `fe82e5ff`. I did **not** inspect any CI run, required check, or merge-base green. My PROBE-LIVE verdict is a local-execution receipt only.
4. **Pythia's counts** (55/55 named bookings, 103/103 failures with a kind, 406 mails / 2 bookings for `ccb52f4c`) were **not** re-derived — different window, and sitting IX §3 already books them as unconfirmed. My 09-11 figures (38 bookings, 202 failure-family lines) are independent, not a check of hers. My C1 row for `ccb52f4c` (**pos=1, neg=47**) is adjacent to but not a replication of that claim.
5. **The two mutants are mine, not an exhaustive mutation sweep.** I established that both poles have teeth at two chosen sites. I did **not** compute mutation coverage over either module.
6. **`activate_campaign` DAG-unreachability was verified textually**, by exhaustive `month1` occurrence count in `config/lifecycle_stages.yaml`. I did **not** execute the stage resolver to confirm no dynamic target exists.
7. **Whether the reconciliation shadow flag is set in the deployed environment** was inferred from log silence (553 boots, zero reconciliation events), not read from the live lambda configuration.
8. **(c2) was not graded, sized, or bounded.** Carried open per R-141.

---

## §9 — EXACT COMMANDS RUN

```bash
# ── refs ────────────────────────────────────────────────────────────────────
git -C .../autom8y-asana fetch origin main && git rev-parse origin/main          # 1b7bf4fa
git fetch origin docs/ratification-sitting-ix-2026-09-11 \
                 feat/activation-smoke-module-land feat/activation-smoke-referent
gh pr view 438 --json state,mergedAt,headRefName    # OPEN, mergedAt null
gh pr view 439 --json state,mergedAt,headRefName    # OPEN, mergedAt null
git show "origin/main:.know/telos/name-the-client.md"
git show "origin/docs/ratification-sitting-ix-2026-09-11:.ledge/decisions/RATIFICATION-decision-space-sitting-IX-2026-09-11.md"
git show "origin/main:.ledge/reviews/ATTEST-name-the-client-wave1-legs-abc1-2026-09-10.md"

# ── (b) F-3 closure, autom8y repo ───────────────────────────────────────────
git -C .../autom8y fetch origin main && git rev-parse origin/main                # bb485521
git -C .../autom8y merge-base --is-ancestor d1ac56d5 origin/main                 # exit 0
git -C .../autom8y log -1 --format='%H%n%ci%n%s' d1ac56d5
git -C .../autom8y show --stat --format='' d1ac56d5
git -C .../autom8y grep -n "booking_gate_declined" origin/main -- '*test*'

# ── live receipts (all: aws logs start-query + get-query-results, polled) ────
#    group /aws/lambda/autom8-email-booking-intake
#    A1  9461b49f-f87f-4f69-960c-2541716faf37   booking_completed by day x kind      (09-08..09-11)
#    B1  6a8c0f92-e50a-459f-9741-269eacf427b7   4 failure families by day x event x kind
#    A2  42606579-018d-4a0c-9cef-c82ae2cc97e7   one raw booking_completed line       (09-11)
#    B2  15fd55ce-e5c3-46e7-835a-06d5d0faa4d0   total / has_kind / blank_kind by day (09-10..09-11)
#    C1  130ed2c1-2a67-4bba-903c-59a5e28cf214   pos/neg per chiropractor_guid        (09-11)
#    group /ecs/autom8y-asana-service, last 30d
#    Q6  59663cdb-…  lifecycle family, `in [...]` shape  -> scanned 12,604     matched 0   [DISCARDED]
#    Q7  5bc41fe0-…  control  event like /^jwks_/        -> scanned 7,145,170  matched 17,773
#    Q8  e917f02d-…  lifecycle family, `like` shape      -> scanned 7,281,524  matched 0   [LOAD-BEARING]
#    Q9  12168935-…  control, `in [...]` shape           -> scanned 517,628    matched 17,773
#    group /aws/lambda/autom8-asana-unit-reconciliation,   30d  f7bf6fd4-…
#    group /aws/lambda/autom8-asana-onboarding-walkthrough, 30d  63b60140-…
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/autom8-asana" \
    --query 'logGroups[].logGroupName' --output text                              # 12 groups

# ── (d) SUBJECT DARK, code re-derivation at origin/main ─────────────────────
git grep -n -E 'LifecycleEngine' origin/main -- src/
git grep -n "PipelineTransitionWorkflow" origin/main            # zero non-test/non-doc callers
git grep -n '"pipeline-transition"\|pipeline_transition' origin/main -- src/
git grep -n "set_dispatcher" origin/main
git grep -n "NoOpDispatcher" origin/main
git show "origin/main:src/autom8_asana/api/routes/webhooks.py" | sed -n '163,192p'
git grep -n "OFFER_CLASSIFIER" origin/main -- src/
git show "origin/main:src/autom8_asana/reconciliation/processor.py" | grep -n "dry_run"
git show "origin/main:src/autom8_asana/lambda_handlers/reconciliation_runner.py" | grep -n "dry_run|environ"
git show "origin/main:config/lifecycle_stages.yaml" | grep -n "month1"           # exactly 1 hit, :149
git show "origin/main:src/autom8_asana/lifecycle/init_actions.py"                # CampaignHandler stub

# ── (d) PROBE LIVE ──────────────────────────────────────────────────────────
git worktree add --detach .knossos/worktrees/wt.eunomia.probe-activation-smoke.20260911T211009.a1b2 fe82e5ff
export PYTHONPATH="$PWT/src"
.venv/bin/python -c "import autom8_asana, autom8_asana.lifecycle.activation_smoke as s; print(autom8_asana.__file__, s.__file__)"
.venv/bin/python -m pytest tests/unit/lifecycle/test_activation_smoke.py    -p no:randomly -q   # 43 passed, rc=0
.venv/bin/python -m pytest tests/unit/lifecycle/test_activation_referent.py -p no:randomly -q   # 32 passed, rc=0
grep -c "@pytest.mark.skip\|@pytest.mark.xfail\|pytest.skip(" <both files>                      # 0, 0
sed -i '' '102s/AccountActivity.ACTIVATING.value/AccountActivity.ACTIVE.value/' src/autom8_asana/lifecycle/activation_referent.py
.venv/bin/python -m pytest <both> -p no:randomly -q      # 14 failed, 61 passed, rc=1
git checkout -- src/autom8_asana/lifecycle/activation_referent.py   # restore -> 75 passed, rc=0
sed -i '' 's/^        if report\.passed:$/        if True:  # MUTANT fail-open/' src/autom8_asana/lifecycle/activation_smoke.py
.venv/bin/python -m pytest <both> -p no:randomly -q      # 15 failed, 60 passed, rc=1
git checkout -- src/autom8_asana/lifecycle/activation_smoke.py      # restore -> 75 passed, rc=0
git status --porcelain                                              # 0 lines, both times
```

---

## §10 — R1 EXTERNAL-AUDIT ATTESTATION

```yaml
r1_external_audit_attestation:
  attester_rite: eunomia
  attester_agent: verification-auditor
  target_initiative_slug: name-the-client
  target_initiative_owner_rite: 10x-dev          # != eunomia — Axiom 1 disjointness holds
  axiom_1_disjointness_verified: true
  axiom_1_evidence:
    seat_of_record: calendar-integration-locus (dispatching seat; NOT eunomia)
    eunomia_in_roster: false
  axiom_3_credential_scope:
    critic_credential: "eunomia verification-auditor product-altitude ADVISORY at telos-integrity-ref §1.4 gate-checklist"
    cumulative_residency_state: "N=2 product-altitude attestations on this initiative (2026-09-10 legs a/b/c1; 2026-09-11 closure)"
  evidence_anchors:
    inception_anchor: ".know/telos/name-the-client.md (origin/main 1b7bf4fa) — inception_anchor block"
    shipped_anchors:
      - "autom8y origin/main: services/email-booking-intake/tests/test_office_attribution_on_firing_failures.py:377"
      - "asana fe82e5ff: src/autom8_asana/lifecycle/activation_referent.py:102"
      - "asana fe82e5ff: src/autom8_asana/lifecycle/activation_smoke.py:718"
      - "asana origin/main: src/autom8_asana/api/routes/webhooks.py:184"
      - "asana origin/main: src/autom8_asana/automation/workflows/pipeline_transition.py:196"
      - "asana origin/main: src/autom8_asana/lambda_handlers/reconciliation_runner.py:125"
      - "asana origin/main: config/lifecycle_stages.yaml:166-167"
    verification_evidence_anchors:
      - "CloudWatch query 9461b49f-f87f-4f69-960c-2541716faf37 (booking_completed x kind)"
      - "CloudWatch query 15fd55ce-e5c3-46e7-835a-06d5d0faa4d0 (blank_kind = 0 of 202)"
      - "CloudWatch query 130ed2c1-2a67-4bba-903c-59a5e28cf214 (15 offices, both poles)"
      - "CloudWatch query e917f02d-d2c2-4ca9-b5ad-62c66aba8c55 (7,281,524 scanned / 0 matched)"
      - "CloudWatch query 5bc41fe0-cba2-401c-b510-6718035a5ccf (control, 17,773 matched)"
  scope_attestation: |
    This attestation is ADVISORY (non-blocking). Eunomia surfaces; the operator adjudicates.
    The dispatching seat has NOT self-attested verification-realized; this rite-disjoint check
    satisfies R1 binding. Every evidence anchor is EXTERNAL CODE or a live platform query —
    none cites eunomia's own DK, this agent's prompt, or a prior eunomia VERDICT unsupported
    by external code (Pythia §5.5 dispatcher-critic-degeneracy guard).
```

---

## §11 — CLOSURE

**Wave 1 of `name-the-client` is CLOSED-WITH-REFUSAL**, on these terms and no wider:

- **(a) ATTESTED** — 38 live `booking_completed` lines on 2026-09-11, every one `office_identity_kind=resolved`, against a same-shape control that still produces the absent class on 09-08/09-09.
- **(b) ATTESTED** — 202 of 202 failure-family lines carry a kind on 2026-09-11; **blank_kind = 0**; F-3 **DISCHARGED** at `autom8y` `d1ac56d5`, probe on main at `:377`.
- **(c1) ATTESTED** — **15 offices** carry both poles in a single day; the bar asks for one.
- **(c2) NOT ATTESTED — CARRIED OPEN** per R-141, into the READ epoch as item 3. *"All active clients"* is undiminished.
- **(d) ATTESTED — PROBE LIVE / SUBJECT DARK.** 43 + 32 green with zero skip evasions and teeth proven on both poles by two independent mutants; the subject it would gate is dark on a full-corpus scan (7,281,524 scanned, 0 matched) against a control firing 17,773 times. **`REFUSED-CORRECTLY` is the correct disposition and I concur.** No missed activation path was found; the three live `OFFER_CLASSIFIER` consumers were each checked and none acts.

**Evidence grade: MODERATE** (self-cap per `self-ref-evidence-grade-rule`). Five flags and eight
unverified items are recorded above so that no downstream reader inherits as fact anything I did not
measure.

*eunomia · verification-auditor · 2026-09-11*
