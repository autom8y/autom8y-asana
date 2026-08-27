---
type: review
status: accepted
title: "CRITIC — rite-disjoint certification of DIAG-offers-watermark-advance; A5 refused on live data"
critic: dre/change-warden
critic_rite: dre
producing_lineage: 10x-dev/architect + 10x-dev/principal-engineer (autom8y-asana, SPR-A1)
disjointness: rite-disjoint (dre != 10x-dev); critic-never-author; no code modified
subject: .ledge/reviews/DIAG-offers-watermark-advance-2026-08-17.md
authored_at: 2026-08-18T04:55Z
pins:
  autom8y-asana: 8e1b3964 (origin/main 844bbde5 — cited files byte-identical)
  autom8y: origin/main 676ec9be
production_change: NONE
verdict: CERTIFIED-WITH-FLAGS
self_assessment_grade: MODERATE (self-ref-evidence-grade-rule; no external corroboration)
headline: >-
  V-1, V-2, V-3 all CONFIRMED by independent own-hands re-derivation, and V-3 is
  strengthened (0 PASS of 39 ticks on a deploy-bounded denominator, replacing the
  DIAG's window selected on the dependent variable). The DIAG is FIT to be
  re-framed upon. But the chosen cure path A5 is REFUSED: under its literal
  reading it routes the whole source to a no-tooth build clock (silent
  false-GREEN); under its intended reading it delivers PASS on 0 of 7 observed
  ticks. The operator's two-clause cure test is INSUFFICIENT and A5 walks
  through the hole.
---

# CRITIC — certification of DIAG-offers-watermark-advance

## §0 — Disjointness Attestation (GATE-2)

**Producing lineage this verdict is disjoint from**: `10x-dev/architect` +
`10x-dev/principal-engineer`, SPR-A1, operating in `autom8y-asana`. The DIAG's
mechanism leg and live-producer leg were both authored inside that lineage.

**My position**: `dre/change-warden`, dispatched rite-disjoint from the
`autom8y` monorepo root (FORK-BETA Option 2). I did not author the DIAG, did not
build the offers content axis, did not author the frame, and I am not authoring
any cure. **Critic-never-author is intact**: the only file I wrote in this
dispatch is this artifact. No code, no config, no fixture was modified.

GATE-2 is **SATISFIED**. No `CERTIFICATION-REFUSED` condition obtains: I am not
in the producing lineage, and I am not author-of-the-fix.

**Disclosed residual (honest, not disqualifying)**: I share an operator session
root with the producing lineage — I was dispatched by the orchestrating session,
not by the builder agent. `critic-substitution-rule` §8 names exactly this as a
limitation the rule does not reach: it addresses STRUCTURAL degeneracy (same rite
in multiple roles), not COGNITIVE adjacency. Structural disjointness holds.
I disclose the adjacency and cap my own attestation at **MODERATE** per
`self-ref-evidence-grade-rule`. STRONG is prohibited to me here.

**Counter-case check (rite-in-lineage)**: the dre rite did not produce the
artifact under certification. No escalation to critic-substitution is triggered.

## §1 — GATE-1 Posture

The DIAG declares `production_change: NONE`, and I verified that: nothing in the
cure path has been activated. GATE-1 therefore **does not gate this verdict** —
there is no realized output to demand a landing receipt on, because nothing
landed. Accordingly **this artifact emits no GO**; it certifies fitness-to-be-
re-framed-upon only.

**Forward-binding notice**: when a cure is proposed (A5 or A1/Option-7), GATE-1
binds in full and will require an end-to-end landing receipt on production-scale
real data asserting the completeness invariant on the REALIZED OUTPUT. I record
here that **A5 already fails a pre-emptive real-data check** (§5) — I hold the
receipt showing 0/7 GREEN — so A5 cannot reach GO on the evidence as it stands.

## §2 — Substrate-of-record receipts (read before anything else)

The SCAR named in my charge is live in this repo and I confirmed it mechanically.

| Probe | Result |
|---|---|
| `git rev-parse origin/main` (autom8y) | `676ec9be`; session branch `7ddbd46c`, **178 behind / 89 ahead** |
| `readiness.py` line count at `origin/main` | **574** |
| `readiness.py` line count at session HEAD == working tree | **129** |
| merge-base of HEAD and origin/main | `a668975b` (2026-08-08), where the file was **129** lines |
| commits on `origin/main` touching it since | `d3072c02`, `c730bc5a`, **`2910fc24 feat(asr): gate offers freshness on the content axis`**, `7d634c1a` |
| commits on the session branch touching it since | **none** |
| autom8y-asana HEAD `8e1b3964` vs `origin/main` `844bbde5` | `8e1b3964` is an ancestor; the two cited files (`activity.py`, `engine.py`) are **byte-identical**; only delta is a CI chore |

So the 129-line file is not merely "a stale branch copy" — it is the
**pre-content-axis** file, frozen at the 2026-08-08 fork point. Every claim below
is read from `origin/main` via `git show`, never from a working tree.

## §3 — Q1: Is the §5.7 falsification SOUND? **YES — confirmed on ground truth.**

I did not accept the claim. I computed the constant and read the live records.

**Own-hands computation**:
```
python3 -c "import hashlib; print(hashlib.sha256(b'').hexdigest()[:16])"
  -> e3b0c44298fc1c14
```
And the generator at `origin/main:src/autom8_asana/dataframes/builders/freshness.py:57`
is `hashlib.sha256("|".join(sorted(gids)).encode()).hexdigest()[:16]`, so
`compute_gid_hash([])` is `sha256(b"")[:16]` exactly. **SVR-5 independently
reproduced.**

**Own-hands ground-truth read** — I pulled the live manifest myself
(`s3://autom8-s3/dataframes/1143843662099250/offer/manifest.json`,
LastModified 2026-08-18T04:17:16Z, 15185 bytes) and inspected the realized
records, not a label:

| Assertion | My measurement |
|---|---|
| total sections | **34** |
| null-watermark sections | **20** |
| of those, `rows == 0` AND `gid_hash == e3b0c44298fc1c14` | **20 / 20** |
| null-watermark sections that are NON-empty (the live-defect population) | **0** |
| incoherent-empty (`rows == 0` but hash != empty) | **0** |
| sections carrying `last_verified_at` (the stamped claim) | **34 / 34** |
| section `status` values | `complete` × 34 |

V-1 is **SOUND**. The §5.7 residual is real in code
(`freshness.py:298 if section_info.watermark is not None:`) but has an empty
population today, and the FIX-1 coherently-empty exemption at
`progressive.py:561-567` is firing exactly as the DIAG describes — I read the
branch and confirmed that `rows==0 AND gid_hash==EMPTY` falls through the
heal-path `continue` to the stamp at `:573`. "Card as latent, do not spend on
it" is the correct disposition.

**FLAG C-1 (do not inherit a point-in-time count as a standing fact).** The
code's own comment at `freshness.py:294-297` records "**~21/34** offer" per QA
2026-05-27; today it is 20/34. The population **drifts**. The latent card must
be a standing tripwire (assert `non-empty AND null-watermark == 0` on every
manifest write), not a one-time observation. The DIAG's own re-check condition
is right; it must be *armed*, not merely written down.

## §4 — Q2: Is the mechanism SOUND, and is it over-fitted? **SOUND. NOT over-fitted — I strengthened it 5 points → 33.**

### 4.1 The code path produces the claimed conjunction (read at origin/main)

| Claim | Verified at | Verbatim |
|---|---|---|
| two constituents | `readiness.py:44` | `OFFER_CONSTITUENTS = ("active", "activating")` |
| combination is max | `readiness.py:~205-213` | "**GATE on max(age). Max, not min and not mean: the oldest constituent governs**" |
| the arithmetic | `readiness.py:362` | `content_age_seconds=max(ages),` |
| three-branch switch | `readiness.py:522-557` | GATE→`decision.content_age_seconds`; REFUSE→`refusal_staleness_seconds`; else→`data_age` |
| refusal sentinel is exact | `readiness.py:387-395` | `threshold * warn_multiplier + 1.0` = **7201.0** |
| activating = 5 sections | asana `activity.py:209-215` | `{ACTIVATING, LAUNCH ERROR, IMPLEMENTING, NEW LAUNCH REVIEW, AWAITING ACCESS}` |
| active = 22 sections | asana `activity.py:185-208` | counted 22 |
| group → IN predicate | asana `engine.py:153-161` | `pl.col("section").str.to_lowercase().is_in(list(classification_sections))` |

The conjunction is real. `max(ages)` over two constituents is `now − min(watermarks)`,
so the gate pins to whichever pool has been quiet longest. Confirmed.

### 4.2 The over-fitting attack, and why it fails

The DIAG rests on 5 points. That *is* thin. So I ran the strongest available
adversarial test: **a zero-free-parameter prediction over every tick in the
pinned era**, with the anchors taken from my own live S3 manifest read rather
than fitted to the data.

Anchors (read by me from S3, **not** fitted):
`IMPLEMENTING = 2026-08-12T11:33:40.703Z`, `ACTIVATING = 2026-08-17T21:41:07.639Z`.

Observations: pulled by me from the real emitter
(`/aws/lambda/autom8y-account-status-recon`, `readiness_check*`, `source=offers`).

Result over **33 ticks** (2026-08-12T20:01Z → 2026-08-18T04:01Z):

```
n = 33
residual (observed − predicted): min -40.23 s, max -11.68 s
mean -17.86 s, stdev 6.55 s, band width 28.56 s
dynamic range of the predicted quantity: 8,379 s → 462,425 s  (55x)
```

A model with **zero free parameters** tracks a 55× dynamic range to within a
28.6-second band, with residuals systematically single-signed in the physically
correct direction (ASR samples at the ECS serve and logs later, so observed
staleness is *less* than the log-timestamp prediction). This is not a fit; it is
a **prediction**, and it is corroborated on 28 points the DIAG never used.

**Competing quantities, excluded by my own probes:**
- `data_age_seconds` (S3 frame watermark): I head-object'd the parquet twice-removed
  from the DIAG's observation — LastModified **2026-08-18T04:23:05Z**, user-metadata
  `watermark=2026-08-18T04:23:04.855847+00:00`, `row-count 4191`. The DIAG saw
  03:15:22Z / 4191. The watermark advanced ~68 minutes with **row-count identically
  4191**. So this quantity is bounded by ~1 h and cannot pin for 5 days. **Excluded**
  — and this is my own independent replication of the DIAG's load-bearing code
  prediction.
- Refusal sentinel: exactly `7201.0` by code. Observed values are 8,379.6 and
  462,425.4. **Excluded.**
- Serving-cache entry age: oscillates; would not pin. **Excluded.**
- "Some other frozen instant": would have to sit within ~25 s of the IMPLEMENTING
  watermark for five days **and then step, at the same moment, to within ~40 s of
  the ACTIVATING watermark**. Two independent coincidences at 20–40 s precision
  against a 5-day baseline. Not credible.

**Verdict: the identification of the QUANTITY is sound and is not over-fitted.**

### 4.3 The +0.55 s vs +40.23 s discrepancy — adjudicated

**The DIAG is right; the relayed +0.55 s is wrong.** My independent arithmetic:
`04:01:26.069 − 22778.197727 s = 2026-08-17T21:41:47.871Z`, which is **+40.23 s**
past the attested ACTIVATING watermark. A +0.55 s residual would require an
ACTIVATING watermark of `21:41:47.321Z` — **39.68 s later** than the value I read
directly from the live manifest. It is not reproducible. The architect was right
to state it rather than smooth it.

**Does it weaken the identification? No — but it falsifies a claim the DIAG still
carries.** The residual band is genuinely ~12–40 s, not sub-second. Both
large-magnitude residuals (12:01:24 at −38.6 s, 04:01:26 at −40.2 s) belong to
ticks with unusually late sub-minute start offsets, i.e. slower invocations —
a coherent physical explanation for a longer serve-to-log gap.

**FLAG C-2 (must not be inherited).** The DIAG's own §1 reconciliation table
(line 112) still carries the live leg's claim "**4/4 ticks ≤0.6 s residual**".
My 33-point analysis falsifies that: the true band is 28.6 s wide. The DIAG
corrects the substance in §2.3 but left the "≤0.6 s" figure standing upstream.
**The re-frame must not carry "≤0.6 s".** It is the kind of over-tight number
that later gets used to reject a correct hypothesis for missing a false bar.

**FLAG C-3 (scope of the identification).** The arithmetic pins *the pool
watermark*, not *which section holds it*, because the 28.6 s residual band
exceeds the spacing between some candidate section watermarks. The DIAG already
says this in §2.3; the re-frame must not re-tighten it into a section-level claim.

## §5 — Q3: Is the REACHABILITY claim sound? **YES — and I replaced its justification with a stronger one.**

### 5.1 Schedule verified

`origin/main:terraform/services/account-status-recon/main.tf:108` reads verbatim
`schedule_expression = "cron(0 */4 * * ? *)"` — 6 ticks/day at 00/04/08/12/16/20
UTC = 17/21/01/05/09/13 PT. Confirmed. It is the only schedule expression in the
file.

### 5.2 The DIAG's denominator is selected on the dependent variable — and I found the passes it omits

The DIAG defines its window as `2026-08-12T11:33:40.703Z → 2026-08-18T04:25Z` —
i.e. **the window begins at the onset of the freeze it is measuring**. That is
selection on the dependent variable, and it is a real methodological weakness: it
invites the rebuttal "but it passed recently."

**And it did.** I pulled the real emitter back to 2026-08-11 and found **three
PASS ticks the DIAG does not mention**:

```
2026-08-11T00:01:01Z  readiness_check_pass  staleness=1022.9
2026-08-11T12:01:02Z  readiness_check_pass  staleness=2343.4
2026-08-11T16:00:59Z  readiness_check_pass  staleness=1478.3
```

Had the re-frame shipped on the DIAG's stated denominator, this was the loose
thread that would have unravelled it in front of the operator.

### 5.3 But the conclusion survives — on a *principled* denominator

I pinned the deploy boundary rather than guessing:

| Image | ECR pushed | contains `2910fc24` (content axis)? |
|---|---|---|
| `f1b430b` | 2026-08-10T16:53Z | **NO** |
| `c21cab9` | **2026-08-11T19:54:44Z** | **YES** ← boundary |
| `3dde20e` | 2026-08-14T20:01Z | YES (currently deployed; Lambda LastModified 2026-08-14T20:04:16Z) |

All three PASS ticks precede `2026-08-11T19:54:44Z`. **They were produced by the
superseded `data_age_seconds` axis** — and their values (1022.9 / 1478.3 / 2343.4)
sit squarely inside the serving-cache oscillation band the DIAG reports
(1063–9522 s), which is exactly what that axis measures. They are not evidence
about the gate under test.

Partitioning on the boundary:

```
PRE-boundary  (superseded data_age axis) : 5 ticks,  3 PASS, 2 FAIL
POST-boundary (content axis LIVE)        : 39 ticks, 0 PASS, 39 FAIL   over 152.0 h
first post-boundary tick 2026-08-11T20:01:22Z -> readiness_check_fail  83123.29 s
```

**0 PASS of 39 ticks over 152.0 hours on the axis actually under test.** This is
a *stronger* result than the DIAG's "zero of ~34 over 136.9 h", and its
denominator is defined by a deploy event rather than by the outcome being
measured.

**V-3 is CONFIRMED. The "42 tick opportunities" refutation stands.** I also
confirm the sole-blocker claim at the latest tick from the emitter: billing
PASS 310.938172, campaigns PASS 532, offers FAIL 22778.197727.

**FLAG C-4 (the re-frame must swap the justification, not just the conclusion).**
Carry the **deploy-bounded denominator (0/39 since 2026-08-11T19:54:44Z)** and
carry the three pre-boundary passes *explicitly*, with the reason they do not
count. Do **not** carry "zero pass-eligible ticks" unqualified.

**FLAG C-5 (grade the arguments differently).** §6.4(d) (the deterministic count)
is a receipt. §6.4(c) ("three of six ticks dead by construction") is a judgement
about human working hours, not a measurement. §6.4(f) (the ≤25 % structural
ceiling) is arithmetically correct (1 h pass window / 4 h period) but bounds a
different quantity than the observed pass rate. All three point the same way;
only (d) should be load-bearing. The DIAG already labels (e) WEAK — extend the
same honesty to (c) and (f).

## §6 — Q4: THE PREMISE RE-LITIGATION

### 6.1 (a) Was "cure the producer, never the consumer" premised on the misreading?

**Partly — and the split is the whole answer.**

I proved the misreading line-for-line rather than asserting it. Frame §4.4 cites
`readiness.py:91-121`, specifically `:94` and `:112-121`:

**In the 129-line stale tree** (session HEAD == working tree):
```
:94          data_age = meta.get("data_age_seconds")
:112-121     sources.append(SourceMetadata(name="offers",
                 staleness_seconds=data_age,
                 staleness_check=StalenessCheck(threshold_seconds=...), ...))
```
The frame's words — "reads `meta.get("data_age_seconds")` verbatim (:94) into
`StalenessCheck` (:112-121) and **computes nothing**" — are a *perfect,
line-exact* description of this file.

**At `origin/main`, the same line numbers** land in the middle of a comment block
about F-GUARD clamp bands (`:113 age < -allowance -> REFUSE...`). The citation is
nonsense against the merged tree.

So the frame's founding premise was read off the pre-content-axis file. Confirmed.

**Now the litigation.** The doctrine has two separable components, and only one
of them rests on the misreading:

1. **The anti-fabrication CORE — "never loosen a threshold to force a pass."**
   This is a value commitment about refusing to manufacture green. It does not
   depend on any claim about what `readiness.py` computes. **It survives intact
   and must not be weakened.** This is the load-bearing safety the rite exists to
   protect, and I explicitly decline to erode it.

2. **The SCOPE EXTENSION — "ASR-side behavior is CORRECT; the defect is upstream;
   never touch the gate."** This *is* premised on §4.4's "computes nothing", and
   it is **FALSIFIED**. At `origin/main` the gate selects the constituent set,
   expands classification groups, applies F-GUARD per constituent, combines with
   `max()`, and chooses among three dispositions. **The consumer is precisely
   where the construct is chosen.** A gate that picks *which quantity to measure*
   is not a pass-through, and "the defect is upstream" does not follow.

**Therefore the operator's ruling — that frame §8.1's `readiness.py` freeze
"targets fabrication, not correctness" — is CORRECT, and it is a restoration
rather than a loosening.** It returns the doctrine to the scope that was ever
justified. This re-litigation is *not* an application of D3 (waste-is-safety): the
safety here is the anti-fabrication core, and it is preserved untouched. What is
being removed is an over-broad scope that was an artifact of reading the wrong
file.

### 6.2 (b) Is the operator's test sufficient? **NO. It has no GREEN arm and no discrimination clause.**

The test as stated: *{it must change the measured QUANTITY, and the new quantity
must still go RED on a genuinely-halted warmer}*.

**Reductio**: the constant `999999` changes the measured quantity, and it goes RED
on a genuinely-halted warmer. It passes both clauses. It is a stuck alarm. Any
permanently-RED quantity satisfies clause (ii) *trivially*, because clause (ii)
only ever probes one arm.

This is not hypothetical — **A5 walks straight through the hole** (§6.3). A5
changes the quantity, and it does still go RED on a halted warmer. It passes the
test, and it is still wrong.

The test is therefore exactly the failure mode the charge feared: it permits the
anti-fabrication wall to be rebuilt in a new hat, because it never asks whether
the new quantity is *about the pipeline*. Minimum additions:

- **(iii) GREEN arm, on real data.** The new quantity must be *observed* PASS on a
  healthy production system, with a receipt on real ticks — not a fixture, not a
  unit test. (Had this clause existed, A5 would have been refused on sight: 0/7.)
- **(iv) Discrimination / construct validity.** RED must fire *for the
  halted-warmer reason and not for an exogenous business reason*. Operationally:
  there must exist an observable state in which the warmer is healthy, the
  business is quiet, and the quantity is GREEN. This is the clause that actually
  separates a freshness axis from a business KPI, and it is the clause `A1 /
  verification_age_seconds` passes by construction while every business-activity
  proxy fails.

Clauses (i)+(ii) alone certify a stuck alarm. Clauses (i)–(iv) do not.

### 6.3 (c) THE A5 ADJUDICATION — **REFUSED. Both readings fail, in opposite directions.**

A5 is specified as: *demote the "activating" constituent GATE→DORMANT-with-
disclosure, using the existing branch at `readiness.py:551-556`.* Those two halves
describe **two different changes**, and the conflation is where the danger is.

#### Reading 1 — A5-LITERAL (actually use the `:551-556` branch)

`readiness.py:551-556` is the **DORMANT** arm of the axis switch, and it sets
`offer_staleness = data_age`. Critically, `combine_offer_axis` at
`origin/main:readiness.py:334-344` reads verbatim:

> `constituents {dormant} reported no content-axis projection; the axis is
> dormant for **the whole source** and **the legacy age governs**`

So marking *one* constituent DORMANT does not gate on the other pool — it turns
**the entire offers source** DORMANT and routes it to `data_age_seconds`, the
build clock.

And the build clock has **no tooth at all**. I re-proved this myself, twice over:
- parquet watermark advanced **03:15:22Z → 04:23:04Z with `row-count` identically
  4191** — a warm that fetched nothing still stamped a fresh instant;
- the only armed offer-staleness alarm, `asana-AL5-offer-frame-stale-1143843662099250`,
  watches `OfferFrameAgeSeconds` at **threshold 7200.0** — the same bar as the gate —
  and has read **OK** continuously *through all 39 consecutive gate failures*.

That is a live, armed, two-sided demonstration that this quantity cannot carry a
RED tooth. **A5-literal is a silent, permanent false-GREEN.** It trades a loud
wrong failure for a quiet one — precisely the trade the charge asked me to test
for, and precisely what the DIAG's own §5 already names as "*worse*". Under D3
this is the load-bearing-safety case: the noisy RED is the only thing currently
telling anyone that offers is unreconciled. Removing it removes the safety.

#### Reading 2 — A5-AS-INTENDED (drop `activating`; gate on the active pool alone)

This is a *different* edit (it changes `OFFER_CONSTITUENTS`, not the DORMANT
branch). It does retain a RED tooth: a halted warmer freezes the frame, so
`max(last_modified)` freezes, wall-clock `axis_now` keeps advancing, and the age
climbs past 7200 s → ABORT. So it **passes the operator's two-clause test**.

**And it is still useless.** I computed the counterfactual from the live manifest —
active-pool max as a function of time, evaluated at every observed tick:

| tick (UTC) | active-pool max | held by | age (s) | **A5 verdict** | observed today |
|---|---|---|---|---|---|
| 08-17T04:01 | 08-16T16:59:06.770 | STAGED | 39 713.2 | **ABORT** | ABORT |
| 08-17T08:01 | 08-16T16:59:06.770 | STAGED | 54 113.2 | **ABORT** | ABORT |
| 08-17T12:01 | 08-16T16:59:06.770 | STAGED | 68 537.2 | **ABORT** | ABORT |
| 08-17T16:01 | 08-16T16:59:06.770 | STAGED | 82 924.2 | **ABORT** | ABORT |
| 08-17T20:01 | 08-17T16:43:49.745 | ACTIVE | 11 839.3 | **ABORT** | ABORT |
| 08-18T00:01 | 08-17T22:15:50.608 | OPTIMIZE QUALITY - Update Targeting | 6 317.4 | **WARN** | ABORT |
| 08-18T04:01 | 08-17T22:15:50.608 | OPTIMIZE QUALITY - Update Targeting | 20 735.4 | **ABORT** | ABORT |

> **A5-as-intended delivers PASS on 0 of 7 observed ticks and ABORT on 6 of 7.**
> Its entire benefit is moving one tick from ABORT to WARN.

It does not unblock CONJUNCT-1. It is not interim relief. It is the same
construct-invalid business-activity proxy with a slightly shorter lever arm — the
22-section pool is busier than the 5-section pool, so it trips a little less
often, and it still trips essentially always.

#### Adjudication

**A5 is REFUSED as an interim cure**, on the record, on live data:

- Under Reading 1 it **loses the tooth entirely** and converts a loud wrong
  failure into a silent one. Worse than the status quo.
- Under Reading 2 it **keeps a non-discriminating tooth and delivers no GREEN**
  (0/7). It buys nothing, while spending the wave's credibility on a change that
  the next quiet weekend will re-break.
- Both readings leave the DIAG's §2.4 row-1 finding untouched: the quantity still
  cannot separate "quiet business" from "halted warmer" at any threshold.

The answer to the question as posed — *does A5 retain a genuine RED tooth, or does
it trade a loud wrong failure for a quiet one?* — is: **Reading 1 trades it for a
quiet one; Reading 2 retains a tooth that is always biting, which is not a tooth
but a stuck alarm.** Neither is fit.

**Sequencing I endorse instead**: L6 (alarm re-home) first — I independently
confirmed the blindness (no alarm on `readiness_check_fail`; the one offer-staleness
alarm watches the build clock and read OK through 39 consecutive failures), and it
is zero-risk. Then A1/Option-7 as the only lever that can satisfy clauses (i)–(iv).
Do not serialize L6 behind A1. Accept the aborts in the interim: they are the
honest signal, and they are currently the *only* signal.

## §7 — Findings the re-frame MUST NOT inherit

| # | Finding | Action |
|---|---|---|
| **C-1** | Null-watermark count drifts (code comment says ~21/34; live is 20/34). | Arm the latent card as a standing invariant, not a one-time note. |
| **C-2** | DIAG §1 table still carries "4/4 ticks ≤0.6 s residual". My 33-point analysis gives a **28.6 s** band. | Strike "≤0.6 s". Carry the real band. |
| **C-3** | Arithmetic pins the *pool* watermark, not the *section*. | Do not re-tighten §2.3 into a section-level claim. |
| **C-4** | "Zero pass-eligible ticks" rests on a window selected on the dependent variable; **3 PASS ticks exist on 08-11** and are unmentioned. | Carry the deploy-bounded denominator **0/39 since 2026-08-11T19:54:44Z**, and name the 3 pre-boundary passes with the reason they do not count. |
| **C-5** | §6.4(c) and §6.4(f) are judgement/ceiling arguments presented alongside the deterministic count. | Grade them below (d); only (d) is load-bearing. |
| **C-6** | Frame §4.4's `readiness.py:91-121` / `:94` / `:112-121` citation resolves **only** against the stale 129-line tree. | Retract the citation explicitly in the re-frame. Any inherited conclusion resting on "the gate computes nothing" must be re-derived. |
| **C-7** | **A5 is refused** (§6.3). Both readings fail; the "gating on active alone" framing is not what `:551-556` does. | Do not adopt A5 as interim relief. Do not conflate the two edits. |
| **C-8** | The operator's two-clause cure test is insufficient; A5 passes it. | Add clause (iii) GREEN-arm-on-real-data and clause (iv) discrimination before any cure is measured against it. |
| **C-9** | **NEW (mine)**: `NEW LAUNCH REVIEW` carries **rows=3 with watermark 2026-05-26T00:38:22.870Z** — 84 days stale. It does not bind today only because the pool combination is `max()`. | Card it. If ACTIVATING and IMPLEMENTING ever empty, the activating-pool max falls back to an 84-day-old watermark and the gate pins permanently at ~84 days. It is also a data-quality signal in its own right, adjacent to R-2. |

I additionally confirm, by direct read, the DIAG's §3 grain finding:
`metrics/freshness.py:785` uses `classifier.active_sections()`, while
`activity.py:92-94` provides `billable_sections()` = ACTIVE ∪ ACTIVATING. A1
must select the grain from the request's classification set. This is correct and
should be carried.

## §8 — Verdict

# **CERTIFIED-WITH-FLAGS**

The DIAG is **FIT to be re-framed upon**. Its two-valued verdict survives
independent, rite-disjoint re-derivation on ground truth:

- **V-1 (§5.7 falsified)** — CONFIRMED. 20/20 null-watermark sections empty-by-
  construction; 0 non-empty; constant recomputed by my own hands.
- **V-2 (mechanism)** — CONFIRMED and **strengthened**: zero-free-parameter
  prediction over 33 ticks, 28.6 s residual band across a 55× dynamic range,
  anchors read from live S3 rather than fitted. Not over-fitted. The +40.23 s
  figure is correct; +0.55 s is not reproducible.
- **V-3 (reachability)** — CONFIRMED and **re-founded**: 0 PASS of 39 ticks over
  152.0 h on a deploy-bounded denominator, replacing a window that was selected
  on the dependent variable.

The flags are not cosmetic. **C-4 and C-6 are corrections to the reasoning the
re-frame would otherwise inherit**, and **C-7/C-8 are a refusal**: the chosen
interim cure path A5 must not be adopted. The premise was re-litigated
independently and the founding "inefficiency" — the noisy, wrong, six-times-daily
RED — turns out to be, in its present form, the **only live signal that offers is
unreconciled**. Removing it without replacing the construct removes the safety.
That is the D3 finding, and it is why A5-literal in particular is refused.

**Evidence grade of this certification: MODERATE** (`self-ref-evidence-grade-rule`;
in-fleet rite-disjointness is not external corroboration; STRONG prohibited).

---

## §9 — Own-hands receipts

All commands run by me in this dispatch. Nothing inherited from the DIAG's fixtures.

```
# empty-GID constant
python3 -c "import hashlib;print(hashlib.sha256(b'').hexdigest()[:16])"   -> e3b0c44298fc1c14

# substrate-of-record
git rev-parse origin/main                                      -> 676ec9be...
git show origin/main:.../readiness.py | wc -l                  -> 574
git show HEAD:.../readiness.py | wc -l                         -> 129
git merge-base HEAD origin/main                                -> a668975b (2026-08-08)
git log --oneline a668975b..origin/main -- .../readiness.py    -> 4 commits incl 2910fc24
git log --oneline a668975b..HEAD -- .../readiness.py           -> (empty)

# the axis switch and the whole-source dormancy rule
git show origin/main:.../readiness.py | sed -n '334,344p'
  -> "the axis is dormant for the whole source and the legacy age governs"
git show origin/main:.../readiness.py | sed -n '551,557p'
  -> else: offer_staleness = data_age ; log.info("offer_freshness_axis_dormant", ...)

# schedule
git show origin/main:terraform/services/account-status-recon/main.tf | sed -n '108p'
  -> schedule_expression = "cron(0 */4 * * ? *)"

# live ground truth (read-only)
aws s3api head-object --bucket autom8-s3 --key dataframes/1143843662099250/offer/dataframe.parquet
  -> LastModified 2026-08-18T04:23:05Z ; watermark 2026-08-18T04:23:04.855847+00:00 ; row-count 4191
aws s3api get-object --bucket autom8-s3 --key dataframes/1143843662099250/offer/manifest.json
  -> 34 sections; 20 null-watermark, ALL rows=0 & gid_hash=e3b0c44298fc1c14; 34/34 last_verified_at
aws logs filter-log-events --log-group-name /aws/lambda/autom8y-account-status-recon
  -> 44 offers readiness ticks 08-11T00:01 .. 08-18T04:01; 3 PASS (all pre-deploy), 39 FAIL post-deploy
aws ecr describe-images --repository-name autom8y/account-status-recon
  -> c21cab9 pushed 2026-08-11T19:54:44Z (first image containing 2910fc24)
aws cloudwatch describe-alarms --alarm-names asana-AL5-offer-frame-stale-1143843662099250
  -> MetricName OfferFrameAgeSeconds, Threshold 7200.0, State OK since 2026-08-17T19:10Z
```

*Authored by dre/change-warden, rite-disjoint from 10x-dev. Critic-never-author:
no code, config, or fixture modified in this dispatch. No GO emitted; nothing was
activated. Self-assessment capped at MODERATE.*
