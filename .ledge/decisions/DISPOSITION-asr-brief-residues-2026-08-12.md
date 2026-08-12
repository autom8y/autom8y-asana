---
type: decision
status: draft
artifact_id: DISPOSITION-asr-brief-residues-2026-08-12
initiative: asana-native-insight-delivery
sprint: S2 (WS-D — residue triage)
rite: 10x-dev
agent: architect
external_critic: null            # by design — shape §5.1 S2 `external_critic: null`; critique folded into PT-01
date: 2026-08-12
evidence_ceiling: MODERATE       # self-ref-evidence-grade-rule; no rite-disjoint attester on this sprint
supersedes: null
governed_by:
  - .ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md   # §7 at :57 — binding
---

# DISPOSITION — the seven un-fitted residues of the ASR team brief

**Sprint S2 of the `asana-native-insight-delivery` shared spine.** Bookkeeping
altitude. This artifact decides **nothing about the mission** (that is GATE-FORK,
operator-reserved) and **builds nothing**. It disposes seven items so that no
downstream sprint has to re-derive them and no item leaks into scope by default.

**The binding fence is charter §7** (`CHARTER-decision-space-of-record-2026-07-30.md:57`,
verbatim): *"never silently widen mandate (scope changes are surfaced as findings,
not absorbed)."* Four of the seven belong to someone else or are already answered.
A residue that is not this initiative's is **ROUTED with its owner named** — never
absorbed, and never quietly carried as "open work" so that it can be absorbed later.

---

## 0. Verification method, and what I did not inherit

The dispatch supplied a paraphrase of the four falsifying receipts. **I verified
each one against the source rather than inheriting it**, and three paraphrase
defects surfaced (§5). Method per `structural-verification-receipt` §2.2:

| claim class | method | substrate |
|---|---|---|
| ASR producer behaviour (FP-1, FP-2) | `file-read` @ **`origin/main`** | autom8y monorepo |
| ownership of FP-3 | `file-read` | `CARDS-follow-up-initiatives-2026-08-11.md` (this repo) |
| ownership of FP-4 | `file-read` | `ADR-007-verification-axis-gate-2026-08-12.md` (this repo) |
| items 1, 7 measured substrate | `file-read` | `.sos/wip/EVIDENCE-*.md` (this repo) |
| item 7 negative receipt | `bash-probe` (grep) | REPORT + both EVIDENCE files + frame |

**The autom8y-checkout-is-not-`origin/main` hazard fired on this sprint** and was
avoided. Probe at authoring time:

```
$ git -C .../repos/autom8y rev-parse --abbrev-ref HEAD
fix/wss-wildcard-scope-bypass-closure
$ git -C .../repos/autom8y rev-parse HEAD ; git -C .../repos/autom8y rev-parse origin/main
cd24d61f07fcb670472a60c55a95f1c57a29f786
0e60e0f530eea0f6bbee955b509dc0ce038b9d5c
```

Every `services/account-status-recon/...` anchor below was read via
`git show origin/main:<path>` at **`origin/main` = `0e60e0f5`** ("Merge pull
request #1554 from autom8y/fix/asr-success-deadman-fill", Wed Aug 12 21:32:47
2026 +0200), per ADR-007 §8 O-11 and shape §16 S5. A working-tree read on that
checkout would have reported a **different tree** and every FP-1/FP-2 anchor
would have been unsound. `[STRONG]` — direct probe, re-runnable.

---

## 1. The seven dispositions

Disposition vocabulary, closed set — no hybrids:

| token | meaning |
|---|---|
| **CLOSED-FALSIFIED** | the premise that made it a residue is false at `origin/main`; it is not carried forward as open work |
| **ROUTED** | real, and belongs to a **named** owner outside this initiative (charter §7) |
| **LIVE-IN-SCOPE** | real, unowned, and admissible to this initiative — but admissible ≠ scheduled; GATE-FORK still rules |

### Item 1 — board shape: 21 of 34 sections hold zero rows; one holds 2 802; INACTIVE holds 1 066

**Disposition: LIVE-IN-SCOPE → routed as candidate Mission-A content.**

**Measured substrate.** Latest per-section row counts on the offers project,
34 sections, taken from `section_status_updated.rows`:

- `.sos/wip/EVIDENCE-w1-cohort-spread-14day-2026-08-12.md:128` — verbatim:
  `2802, 1066, 169, 45, 38, 23, 22, 10, 7, 5, 3, 1, 1     (21 sections are 0-row)`
- `:123-125` — provenance of that list, naming the producer
  `src/autom8_asana/dataframes/section_persistence.py:551-559`
- `:135` — the name anchor: `1143843662099257`=INACTIVE (1 066, *inactive* — **not a
  constituent** of either serving cohort)

**Why it is genuinely open.** 13 of 34 sections carry any rows at all; two
sections hold 3 868 of the ~4 190 rows. **No consumer has ever been shown this
shape.** It is a board-behaviour fact, not a verdict-class fact, so it is
**not gate-starved** (frame §6, `:488`) — it is say-able while P-3 holds.

**Routing.** Candidate content for **Mission A** (new insight class). It is
*candidate*, not *committed*: the mission fork is operator-reserved (frame §3,
`:635-639`) and WS-A can still falsify the demand (frame `:379-380`). This
disposition admits the item to the candidate set; it does not schedule it.

**One coherence note, carried forward rather than acted on.** The population
`min()` under ADR-007 P-5 runs over the same section set. Readout and gate would
share a denominator. That is an **opportunity** (two surfaces that cannot
disagree), not a coupling — and it must stay that way: this initiative acquires
**no dependency** on the ADR-007 §7.5 one-way-door meta contract
(`ADR-007-verification-axis-gate-2026-08-12.md:1228-1239`; frame `:489-496`). If a
readout wants a number that exists only on the K-lane, it **waits**.

Grade: `[STRONG]` on the row counts (wire-receipted, §1.2 of the evidence file).
`[MODERATE]` on "no consumer has ever seen it" — argued from the absence of any
published artifact carrying it, which is an absence-of-evidence claim.

---

### Item 2 — Slack silently truncated all 44 advisory findings on the 08-10 run

**Disposition: CLOSED-FALSIFIED (FP-1). The truncation persists; the SILENCE does not.**
**Residual = reachability → WS-C (in-initiative), not a new defect.**

Falsifying receipt, autom8y @ `origin/main` `0e60e0f5`,
`services/account-status-recon/src/account_status_recon/report.py`:

| anchor | what is there |
|---|---|
| `report.py:171` | `def _advisory_summary_line(count: int) -> str:` — docstring `:174-176` names the 08-10 run verbatim: *"In the live run of 2026-08-10 all 44 advisory findings were truncated away with no breadcrumb of any kind, and absence-of-breadcrumb is indistinguishable from absence-of-findings."* |
| `report.py:190-194` | the emitting `return` — `f":information_source: *Advisory -- stale / not evaluable*: {count} ASR-observed accounts · surfaced, not actionable this run · drill: the durable verdict surface `latest.json`"` |
| `report.py:344-345` | `if advisory:` → `summary_lines.append(_advisory_summary_line(len(advisory)))` — the call site |
| `report.py:321-326` | the region comment: `==== THE TRUNCATION-IMMUNE DISCLOSURE REGION (AMENDMENT-001 D-3) ====` … *"written into the block list BEFORE `available_blocks` is computed … outside the budgeted region entirely -- immune by construction, not by ordering"* |
| `report.py:76-82` | `_BODY_CAP_NOTE` — states the 50-block ceiling and points at the complete record |
| `report.py:353-354` | `if individually or advisory:` → `summary_lines.append(_BODY_CAP_NOTE)` — the cap-note call site |

**The mechanism, stated so a downstream author need not re-read the file**: the
count is computed from the **full** findings list before any budgeting and is
appended to `summary_lines`, which the SDK writes into the block list *before*
`available_blocks` is computed. It is therefore not merely early — it is outside
the budgeted region. The 08-10 failure mode (44 findings gone, no breadcrumb)
**cannot recur**: on that same input `len(advisory) == 44` renders in a region the
block budget never reaches.

**What is NOT closed**: the body sections are still cut, so the *per-finding
detail* remains unreachable from Slack. Both surfaces terminate in the same drill
pointer (`report.py:80-81`, `:192-193`) — CloudWatch `finding_detail` or `latest.json`,
both **operator-only**. That is the reachability problem, and it is
**WS-C's subject** (frame `:405-420`), which is the Mission-B limb and carries
**no clock** (frame `:418`). It is not re-filed as a defect here.

Grade: `[STRONG]` — code read at `origin/main` with call sites confirmed on both
sides (definition and invocation).

---

### Item 3 — the enrollment-condition cohort explainer

**Disposition: LIVE-IN-SCOPE — and it is CONTENT, not code.**

The code half already exists. `report.py:133-168` (`_cohort_summary_line`) renders,
in the truncation-immune region, one line carrying: the count with its scope
qualifier **inside the number's own phrase** (`n=NN ASR-observed accounts`, the
ADR-C S5 denominator wall, `:145-150`), the condition (`campaign running, no active
offer; delivery consequent`), an *already-counted-above* clause when applicable,
the ownership statement — `report.py:165`, verbatim: *"tracked centrally by the
enrollment program — not an ASR work item"* — and a drill pointer.

**What is missing is not a renderer.** A reader who does not already know what the
enrollment program *is* learns from that line only that these items are not
theirs. The gap is an **explainer**: what the program is, why these accounts are
in that condition, and why they are correctly excluded from this team's work
queue. Writing it requires **no ASR change**.

**Consequence for routing**: this item does **not** belong in any code sprint. It
belongs to whatever produces readout copy. Filing it as an engineering task would
be a category error that guarantees it is never done.

**One fence it inherits.** The explainer must not restate or re-derive the count.
The denominator wall at `report.py:145-150` is BINDING (ADR-C S5): the line
*"asserts no equality with, correspondence to, or derivation from any other
program's denominators, and it mints no new population figure."* An explainer that
says "the enrollment program covers N accounts" mints exactly the second number
that wall exists to forbid. **Explain the condition; never re-count the population.**

Grade: `[STRONG]` on what the code renders. `[MODERATE]` on "content, not code" —
a design judgement, argued from the fact that every element the explainer needs
is prose about an external program.

---

### Item 4 — the 100-campaign fleet cap (`campaigns_truncated`)

**Disposition: CLOSED-FALSIFIED as unhandled (FP-2). Four operator-observable
surfaces exist. Residual — no LEADING headroom indicator — is ROUTED (see §2 and §6).**

Falsifying receipts, autom8y @ `origin/main` `0e60e0f5`:

| surface | anchor | what is there |
|---|---|---|
| Slack warning banner | `orchestrator.py:600` `def _truncation_warning`; string at `:633-637` | verbatim: `f"Campaigns truncated: {dropped} of {fleet_total} active campaigns dropped; reconciliation covered the first {returned} (server cap = 100). Verdicts for the dropped campaigns are ABSENT from this run."` |
| call site | `orchestrator.py:307-327` | `if campaigns_meta.get("truncated"):` → lifts `campaigns_returned` / `campaigns_fleet_total` (`:309-312`) → `_truncation_warning` (`:313`) → appends to the `#account-health` banner (`:325-327`) |
| CloudWatch structured log | `orchestrator.py:317-323` | `log.warning("campaigns_truncated", returned=…, fleet_total=…, dropped=…, invocation_id=…)` — alarm-keyable by event name |
| CloudWatch metric | `metrics.py:85-86` | `CustomMetric("CampaignsTruncated", 1 if result.campaigns_truncated else 0)` and `CustomMetric("CampaignsFleetTotal", result.campaigns_fleet_total)` |
| Grafana alert | `terraform/services/grafana/alerting.tf:1949-1972` | live alert rule, baseline 0, with a description naming the cap, the false-clear risk, and the remediation fork (cap-raise vs paginated fetch) |
| runbook | `docs/reliability/runbooks/RUNBOOK-account-status-recon-campaigns-truncated.md` | present at `origin/main` (`git ls-tree` → exists) |

The premise "un-fitted residue" is **false**: this is one of the better-instrumented
paths in the service.

**The residual, stated precisely — and it is narrower than the frame's wording.**
`CampaignsFleetTotal` *is* emitted every run (`metrics.py:86`), which reads like a
headroom trend. It is not. `result.campaigns_fleet_total` defaults to `0`
(`models.py:387`) and is assigned **only inside** the truncation branch
(`orchestrator.py:307,310-312`). On every non-truncated run the metric therefore
emits **0**, not the live fleet size.

> **The consequence, which is the whole residual**: every one of the four surfaces
> is a **coincident** indicator. They all fire on the run where the cap has
> *already* bitten and campaigns have *already* been dropped. Nothing emits the
> fleet's approach to 100. The `alerting.tf:1972` description concedes the
> position — *"Not a transient — it persists until the fleet shrinks below the cap
> or the ceiling is raised."*

**Routing of the residual**: producer-side observability on an ASR fetch path in
the **autom8y monorepo**. Absorbing it into an insight-delivery initiative in
**autom8y-asana** would be the mandate-widening charter §7 forbids, and would also
breach the frame's cross-repo atomicity fence (`:506-509`). It is **surfaced as a
finding for the operator to open as a card** (§6, §7-OP-2). I do not open it — the
CARDS register is opened by operator ruling (R-12), not by a sprint.

Grade: `[STRONG]` — six anchors across five files, each read at `origin/main`;
the default-`0` mechanism confirmed on both the declaration and the single
assignment site.

---

### Item 5 — the 02:42Z resolver cadence collapse

**Disposition: CLOSED-FALSIFIED as this initiative's (FP-3). ROUTED — already
owned as CARD-FU-1, sre/observability.**

Falsifying receipt: `.ledge/decisions/CARDS-follow-up-initiatives-2026-08-11.md:16-25`
— *"CARD-FU-1 · Cadence-absence alerting for scheduled internal consumers"*, whose
gap statement at `:19-22` names this exact event: the `asana-dataframe-resolver`
project-query cadence collapsing at **02:41:59.112Z** (caller-side, auth plane
clean, silent 7.8 h+ at last check), citing `.sos/wip/DIAG-S1-cadence-2026-08-11.md`
F2.1–F2.3. Routing is stated at `:25`: **sre/observability, non-blocking on the
origin crusade.** The card was opened by **operator ruling R-12**
(`CARDS…:5`, `RULING-operator-s5-gate-interview-2026-08-11.md`).

**Absorbing this would be a doubly-marked breach**: charter §7 (`:57`), and
re-opening an item an operator ruling already routed elsewhere.

**The one thread that legitimately reaches this initiative is not the item — it is
the CLASS.** A silently stopped scheduled consumer produces no failing call, so no
error-rate alarm can see it (`CARDS…:17-18`). If WS-F ever builds a scheduled
generator, that generator is a candidate **ninth instance** of the same class. The
shape already books this as **DEFER-WATCH-1** (shape `:1399`): trigger = SA-2
enters; action = the new schedule must ride FU-1's heartbeat, verified at PT-06.
**That is a coverage obligation on our own future artifact, not ownership of FU-1.**

Grade: `[STRONG]` — the card names the same service, the same timestamp to the
millisecond, and carries an operator-ruling provenance line.

---

### Item 6 — DEFECT-1 / DEFECT-2 odd last-modified behaviour

**Disposition: CLOSED-FALSIFIED as this initiative's (FP-4). ROUTED — ADR-007 §7.4
parallel producer tracks.**

Falsifying receipt: `.ledge/decisions/ADR-007-verification-axis-gate-2026-08-12.md:1207`
(`### 7.4 Parallel tracks (P-11)`), rows at:

- `:1211` — **DEFECT-1 / G-2** (optimistic concurrency on the manifest write):
  *"own PR, own attribution, producer correctness"*; *"blast radius wider than this
  gate (metrics CLI, resume path, checkpointing). Its absence **caps this gate's
  pass rate by an unknown amount**"*
- `:1212` — **DEFECT-2 root cause** (the write path permitting a backward stamp):
  *"own PR"*; *"G-1 neutralises the effect on this axis; the cause is producer
  correctness"*

The ruling that put them there is **P-11** (`ADR-007…:118` — *"DEFECT-1/2: G-1 in
design; defects parallel"*), and the ADR states the attribution rationale directly
at `:379`: bundling *"makes the gate change unattributable — the exact discipline
the sequencing ruling protects: never bundle the disclosure patch with a threshold
move; attribution loss is permanent."*

A reporting initiative taking either track would (a) breach charter §7, (b) join a
K-lane it is fenced out of (frame `:489-498`), and (c) destroy the attribution the
ADR protects. **Not this initiative's, on three independent grounds.**

Grade: `[STRONG]` — both defects booked by name, each with its own row, its own PR
boundary, and a ratified ruling ID.

---

### Item 7 — the 12:00/16:00 UTC "board most in sync" window

**Disposition: LIVE-IN-SCOPE, but recorded as an INFERENCE — publishable only as such.**

**What is measured** (two facts, both wire-grounded):

1. **The diurnal build profile.** `.sos/wip/EVIDENCE-age-at-tick-v-sizing-2026-08-12.md:388-399`
   — offer builds by UTC hour over 30 days. Verbatim, `:390-392`:
   ```
   hour   0    1    2    3    4    5    6    7    8    9   10   11   12   13   14   15   16   17   18   19   20   21   22   23
   all   30    5   11    9   30    5   11   11   36   15   20   19   61   32   29   28   45   17   11   11   31    7   11   10
   warm   6    5   11    9    7    5   11   11   11   13   19   18   36   31   29   28   20   17   11   11    7    7   11   10
   ```
   Hours **12** (`all`=61) and **16** (`all`=45) are the profile's top two slots.
   The file's own reading, `:395-397`: between 01:00 and 08:00 UTC *"the on-demand
   SWR path is not exercised because nothing is asking. This is what lets the gap
   reach its scheduled ceiling."*
2. **The Monday-maximum spread mechanism.**
   `.sos/wip/EVIDENCE-w1-cohort-spread-14day-2026-08-12.md:477` — *"The spread
   therefore reaches its **maximum** on Monday morning, not on Sunday night"*,
   because the active cohort receives sporadic weekend edits the activating cohort
   never does.

**What is NOT measured — the inferential step, named.** The measured quantity is
**builds per hour-slot**. "The board is most in sync at 12:00/16:00" is a claim
about **expected data age at a wall-clock hour**. Getting from one to the other
requires a step nothing in the corpus performs: build frequency is a *proxy* for
recency, not a measurement of it. Two specific reasons the proxy is loose:

- `:398-399` marks hours **0/4/8/20** as the tick hours where `all` ≫ `warm` and
  *"the ASR is a material contributor to build cadence there"* — so build counts at
  different hours are not the same kind of event, and the profile mixes tick-driven
  builds with demand-driven ones.
- The Monday-maximum mechanism is about the **spread between two cohorts**, not
  about either cohort's absolute age. A window can be the best hour of the day and
  still sit inside the 93.1 h activating dormancy the same corpus measures.

**Negative receipt — this claim has never been published anywhere.** A grep for
`most in sync` / `12:00` / `16:00 UTC` across
`.ledge/reviews/REPORT-asr-team-brief-2026-08-12.md`, both `.sos/wip/EVIDENCE-*.md`
files, and the frame returns **exactly one hit**: the frame's own residue row,
`.sos/wip/frames/asana-native-insight-delivery.md:438`. The team brief's §3
board-rhythm section (`:78-99`) makes **no** in-sync-window claim.

**Consequence.** This disposition is a **pre-emptive fence, not a retraction**.
Nothing has to be corrected. If a future readout publishes an in-sync window it
must carry the inference on its face — *"the board is built most often around
12:00 and 16:00 UTC"* is say-able (it is the measurement); *"the board is most in
sync at 12:00/16:00 UTC"* is not, unless age-at-hour is measured directly.

**This is charter §2 territory, and the reason it is worth a disposition at all.**
A friendly window is exactly the kind of number a team acts on. Publishing a proxy
as if it were a measurement is the **NEVER CONFIDENTLY WRONG** floor
(`CHARTER…:52`), and it is the same conflation pressure P-12 exists to resist
(frame `:559-563`) — do not blend two quantities into one friendly number.

Grade: `[STRONG]` on both measured facts and on the negative receipt.
`[MODERATE]` on the size of the inferential gap — the direction is certain
(more builds ⇒ lower expected age), the magnitude is unquantified.

---

## 2. The two caps are DIFFERENT CAPS — the named failure of this sprint

Conflating them is called out as a failure mode in three places
(frame `:435`, `:587-589`; shape `:1408`). Held apart explicitly:

| | **item 4's cap** | **CARD-FU-3's cap** |
|---|---|---|
| **the number** | **100** | **1 000** |
| **what it limits** | ADS campaigns returned by the campaigns fetch | rows returned per **offers status group** by the query surface |
| **whose ceiling** | the ads **server**'s cap — verbatim *"(server cap = 100)"*, `orchestrator.py:635` | the **query** row limit on the offers frame |
| **which repo** | **autom8y monorepo** — `services/account-status-recon/` | **autom8y-asana** — offers frame / query surface |
| **which entity** | campaigns | offers |
| **failure mode when it bites** | campaigns 101–N **dropped**; run proceeds PASS-with-warning; verdicts for dropped campaigns ABSENT (`orchestrator.py:634-636`) | T-GUARD **fails closed** — the completeness guard refuses (`CARDS…:37-38`) |
| **current headroom** | not computed on the non-truncated path (`models.py:387`, `orchestrator.py:310-312`) — **that is the residual** | ~15x — 67–68/1000 active, 48–49/1000 activating (`CARDS…:39`; `REPORT…:100-104`) |
| **leading indicator** | **none**; four coincident surfaces only (§1 item 4) | **none built**; `max_total > 700` named as the only candidate, and *"nothing emits it"* (`CARDS…:41-42`) |
| **owner** | **unopened** — routed to the operator as a finding (§6, OP-2) | **CARD-FU-3**, sre/observability + ASR, opened by operator ruling R-12 (`CARDS…:36-45`) |
| **disposition here** | CLOSED-FALSIFIED as unhandled; residual routed | OUT of scope, owned elsewhere (frame `:587-589`) |

**They share exactly one property**: both are *"a ceiling with no leading
indicator."* That shared *class* is what makes them easy to merge and expensive to
have merged — a single card covering "the caps" would land in one repo, on one
service, and silently leave the other uncovered.

**A verified non-finding, recorded so it is not re-raised.** The offers headroom
numerator differs across three artifacts — `68/48` wire-receipted
(`EVIDENCE-w1…:157-158`, `query_rows_complete active 68/68` / `activating 48/48`),
`67/48` in the team brief (`REPORT…:101-102`), `67/49` in the card (`CARDS…:39`). I
probed this as a possible confidently-wrong defect. **It is already disclosed as
tick drift**: `REPORT…:215-216`, verbatim — *"the '15x headroom' counts move
slightly day to day (67–68 active, 48–49 activating in the receipts)."* No defect.
Recorded because the next reader will notice the same discrepancy.

Grade: `[STRONG]` — every row anchored; the non-finding closed by a verbatim
in-artifact caveat.

---

## 3. FP-1..FP-4 — CLOSED register

Recorded **CLOSED**, not carried. This table answers PT-01's gate question
(shape `:917`) mechanically.

| FP | premise as charged | status | falsifying receipt (verified by me, not inherited) |
|---|---|---|---|
| **FP-1** | the Slack report's **silent** truncation of all 44 advisory findings on the 08-10 run is an open residue | **CLOSED — falsified as silent** | `report.py:171` + `:190-194` (`_advisory_summary_line`, docstring `:174-176` names the 08-10 run) · `:344-345` call site · `:321-326` immune-region proof · `:76-82` + `:353-354` cap note — all @ `origin/main` `0e60e0f5` |
| **FP-2** | the 100-campaign fleet cap `campaigns_truncated` is an un-fitted residue | **CLOSED — falsified as unhandled** | `orchestrator.py:600`,`:633-637` banner · `:307-327` call site · `:317-323` keyable log · `metrics.py:85-86` · `alerting.tf:1949-1972` · `RUNBOOK-account-status-recon-campaigns-truncated.md` (exists) — all @ `origin/main` `0e60e0f5` |
| **FP-3** | the 02:42Z resolver cadence collapse is this initiative's residue | **CLOSED — falsified as unowned** | `CARDS-follow-up-initiatives-2026-08-11.md:16-25`; same service, same timestamp `02:41:59.112Z` at `:20`; routing `:25`; operator ruling R-12 at `:5` |
| **FP-4** | DEFECT-1/DEFECT-2 odd last-modified behaviour is this initiative's residue | **CLOSED — falsified as unowned** | `ADR-007-verification-axis-gate-2026-08-12.md:1207` §7.4 heading; `:1211` DEFECT-1/G-2; `:1212` DEFECT-2; ruling P-11 at `:118`; attribution rationale `:379` |

**No wave-level CLOSED token is issued** (F-HYG-CF-A,
`RETROSPECTIVE-VD3-2026-04-18.md:145`). There is no "WS-D CLOSED" here. Each of
the four carries its own token, its own anchors, and — for FP-1 and FP-2 — its own
explicitly named **residual** that does *not* travel under the CLOSED token.

---

## 4. Residuals that survive a CLOSED disposition

A closed premise is not an empty item. Stated so neither can be lost, and neither
can be smuggled back in under the closed item's name:

| from | residual | disposition |
|---|---|---|
| item 2 (FP-1) | per-finding detail is still unreachable from Slack; both drill pointers are operator-only (`report.py:80-81`, `:192-193`) | **WS-C** — in-initiative, Mission-B limb, **no clock** (frame `:418`) |
| item 4 (FP-2) | no **leading** headroom indicator on the 100-campaign cap; the fleet total is not emitted on the non-truncated path (`models.py:387`; `orchestrator.py:310-312`) | **ROUTED to the operator** as a finding — a monorepo/ASR observability item, not absorbable here (§6, OP-2) |

---

## 5. Corrections to the frame's own paraphrases — surfaced, never papered

The dispatch instructed me to verify rather than inherit. Three defects surfaced.
**None overturns a disposition**; all three would have propagated as false premises
into PT-01 or a later readout.

| # | where | as written | as verified at `origin/main` `0e60e0f5` | consequence |
|---|---|---|---|---|
| **C-1** | frame `:433` (WS-D item 2) and `:622` (FP-1) — *"`_BODY_CAP_NOTE` (`:76-83`) states the cap **unconditionally**"* | "unconditionally" | **Conditional.** `report.py:353` gates it: `if individually or advisory:`. The gate is deliberate — the in-code comment at `:349-352` explains it is *"Deliberately NOT gated on `cohort`: a cohort-only run builds zero sections and has nothing to truncate, so a cap note there would be a **FALSE disclosure**."* | FP-1's conclusion **stands** — on the 08-10 input `advisory` is truthy (44 findings), so both lines render. But "unconditional" is wrong, and a downstream author reasoning from it would mis-model the all-clear and cohort-only paths. **The real design is better than the paraphrase**: it refuses to disclose a truncation that cannot occur. |
| **C-2** | frame `:433`, `:622` — `report.py:171-190` | the emitting `return` is at **`:190-194`**; `:190` is only `return (`. The function is `:171-194`. | anchor truncates one line before the string it cites. Cosmetic, but the cited range does not contain the quoted text. |
| **C-3** | frame `:435`, `:623` — `orchestrator.py:600-638` | `_truncation_warning` is **`:600-637`**; `:638` is blank. | off-by-one. Cosmetic. |

**One material understatement, in this initiative's favour** (recorded for the same
reason): the frame credits item 4 with a Slack warning and a runbook. There are in
fact **six** operator-observable surfaces including an alarm-keyable CloudWatch
log (`orchestrator.py:317-323`), two CloudWatch metrics (`metrics.py:85-86`), and a
**live Grafana alert rule** (`alerting.tf:1949-1972`). FP-2 is therefore *more*
firmly falsified than charged — and the residual is correspondingly **narrower**
than "no headroom trend": it is specifically the absence of a **leading** indicator
(§1 item 4).

Per handoff-premise-validation §10.5: surfaced here, not papered. **Standing count
after S2: 7 premise events (4 falsified, 3 refined) — unchanged; plus 3 anchor
defects and 1 understatement in the frame's transcription of them.**

---

## 6. Routing table — who owns what after this sprint

| item | verdict | owner after S2 | may this initiative act on it? |
|---|---|---|---|
| 1 · board shape | LIVE-IN-SCOPE | **this initiative** — candidate Mission-A content | Yes, **after GATE-FORK**. Admitted to the candidate set, not scheduled |
| 2 · advisory truncation | CLOSED-FALSIFIED (FP-1) | — (premise closed) | No. Residual → **WS-C**, unclocked |
| 3 · cohort explainer | LIVE-IN-SCOPE | **this initiative** — as **readout copy**, never a code task | Yes, as content. **No ASR change is implied or permitted** |
| 4 · 100-campaign cap | CLOSED-FALSIFIED (FP-2) | — (premise closed); **residual → operator** (OP-2) | No. Monorepo/ASR observability; absorbing breaches charter §7 (`:57`) and the cross-repo fence (frame `:506-509`) |
| 5 · 02:42Z collapse | CLOSED-FALSIFIED (FP-3) | **CARD-FU-1** — sre/observability, ruling R-12 | No. Only obligation: **DEFER-WATCH-1** (shape `:1399`) — SA-2 must ride FU-1's heartbeat |
| 6 · DEFECT-1/2 | CLOSED-FALSIFIED (FP-4) | **ADR-007 §7.4** parallel producer tracks | No. Fenced out of the K-lane on three grounds (§1 item 6) |
| 7 · in-sync window | LIVE-IN-SCOPE, **inference-only** | **this initiative** — with a publication fence | Yes, **only as the inference it is** (§1 item 7) |

Adjacent and untouched, restated so no reader infers otherwise: **CARD-FU-2**
(abort forensics parity, `CARDS…:27-34`) and **CARD-FU-4** (ASR `image_tag` pin
invariant, `CARDS…:54-71`, opened 2026-08-12) were never in the residue set and
are not dispositioned here. Naming them is not adopting them.

---

## 7. For the OPERATOR

**OP-1 — nothing in this artifact needs a ruling to be correct.** S2 is
bookkeeping. Items 1, 3 and 7 are *admitted to the candidate set*; whether any is
built is **GATE-FORK**, which is yours (frame `:635-639`). If the fork rules
Mission B only, items 1 and 7 stay recorded and unbuilt — no rework, no
re-derivation.

**OP-2 — one finding is yours to route (or to decline).** The 100-campaign cap has
**no leading headroom indicator**: four coincident surfaces fire the run the cap
has already bitten, and `CampaignsFleetTotal` emits `0` on every healthy run
(`models.py:387`; `orchestrator.py:310-312`). This is the **same class** as
CARD-FU-3 and a **different cap, different repo, different entity** (§2). The
symmetric fix is small — emit the live fleet total on the non-truncated path, then
one alarm below 100. **I have not opened a card**: the CARDS register is opened by
operator ruling (R-12), and opening one myself is the mandate-widening §7 forbids.
Suggested slug if you want it: **CARD-FU-5 · capacity early-warning for the
100-campaign fleet cap** — sre/observability + ASR, monorepo.

**OP-3 — item 3 needs a content owner, not an engineer.** The enrollment-cohort
explainer requires **no code**. Left in an engineering queue it will not be
written. It also inherits a hard fence: **explain the condition, never re-count the
population** (denominator wall, `report.py:145-150`).

**OP-4 — item 7 is a publication fence you may want to know exists.** No artifact
has ever published the 12:00/16:00 "most in sync" window (negative receipt, §1
item 7), so **nothing needs correcting**. The fence binds only future readouts.

**OP-5 — a live hazard this sprint tripped, relevant to the other three sprints
running in parallel.** The `autom8y` checkout is on
`fix/wss-wildcard-scope-bypass-closure` @ `cd24d61f`, **not** `origin/main` @
`0e60e0f5`. Every FP-1/FP-2 anchor here was read via `git show origin/main:…`. Any
sibling sprint reading the monorepo working tree — **S5 is explicitly instructed to
read `report.py` and `config.py` there** (shape `:1557`) — will read a different
tree. This is ADR-007 §8 O-11 in live form.

---

## 8. Evidence, grades, and what I could not verify

**Self-attestation ceiling: MODERATE** (`self-ref-evidence-grade-rule`). S2 carries
**no external critic by design** (shape `:617` — `external_critic: null`, *"bookkeeping
altitude; critique folded into PT-01"*). I did not invent one and did not lower
rigor for its absence: every FP receipt was re-derived from source at `origin/main`
rather than inherited, which is what surfaced C-1..C-3. **The individual receipts
grade STRONG on their own probes; this artifact's overall disposition grades
MODERATE until PT-01 concurs.**

**UV-P register.** Two carries, per the frozen syntax:

```
[UV-P: no ADS fleet campaign count was observed live, so the 100-campaign cap's
CURRENT headroom is unknown — only that nothing computes it | METHOD:
deferred-to-operator-or-FU-5-owner; one ads-service active-campaign count |
REASON: read-only sprint, .ledge/ only; no AWS or ads-service reach in this seat]
```

```
[UV-P: the size of item 7's inferential gap — how much lower expected data age
actually is at 12:00/16:00 UTC than at other hours | METHOD:
deferred-to-a-direct-age-at-hour measurement, which the corpus does not contain |
REASON: the measured quantity is builds-per-hour-slot; age-at-hour was never
computed. The DIRECTION is certain; the MAGNITUDE is not]
```

Both persist past this sprint. Per SVR §1 RULE-2 they are carried, not dropped;
per RULE-3 they surface at the close gate if never discharged. Neither blocks any
disposition: item 4's residual is *"nothing computes the margin"* (which is proved
by the code, not by the margin's value), and item 7's disposition is *"publishable
only as an inference"* (which holds at any magnitude).

**Nothing in this sprint touched code, the K-lane, or any ADR-007 surface.**
Exit artifact is this file. Scope: `.ledge/decisions/` only.

---

## 9. Exit-criteria self-check (mechanical)

| S2 exit criterion (shape `:631-636`) | met | where |
|---|---|---|
| Seven written dispositions with per-item `{path}:{line}` anchors | ✅ | §1, items 1–7 — each carries ≥2 anchors |
| FP-1..FP-4 recorded **CLOSED with their falsifying receipt**, not carried | ✅ | §3 register; receipts re-verified at `origin/main` `0e60e0f5`, not inherited |
| Item 1 routed as **candidate Mission-A content** | ✅ | §1 item 1; §6 |
| Item 3 recorded as **CONTENT-not-code** | ✅ | §1 item 3; §6 (*"never a code task"*) |
| Item 7 recorded as an **INFERENCE, publishable only as such** | ✅ | §1 item 7; §7 OP-4 |
| The 100-campaign cap and CARD-FU-3's 1 000-row cap remain **textually distinguished** | ✅ | §2 — 11-row discriminating table; the shared class named explicitly |
| **No wave-level CLOSED token** without per-item anchors (F-HYG-CF-A) | ✅ | §3 — stated; no "WS-D CLOSED" appears anywhere in this artifact |
| Charter §7: residues not ours are ROUTED **with owner named**, never absorbed | ✅ | §6 routing table — every non-ours item names its owner and its ruling |
