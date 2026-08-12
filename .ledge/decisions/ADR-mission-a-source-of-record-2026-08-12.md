---
type: decision
status: draft
revision: 2
remediates: CRITIQUE-s4-mission-a-source-of-record-2026-08-12
initiative: asana-native-insight-delivery
sprint: S4
name: Mission-A source-of-record decision
rite: arch
seat: dependency-analyst
co_seat: structure-evaluator
external_critic: arch-adversary
date: 2026-08-12
repo: autom8y-asana
cross_repo_reads:
  - "autom8y @ origin/main 0e60e0f530eea0f6bbee955b509dc0ce038b9d5c (rev-1); RE-VERIFIED at rev-2 against origin/main a5c98f9cfccba2837eac3b26d1ac2b64c7cb8d74 — every §4 hop reproduces at both refs (ADR-007 §8 O-11 discipline)"
  - "a8 @ 0fb9527b (pinned module ref, read-only)"
  - "AWS us-east-1 696318035277 (read-only Logs API)"
fences:
  - READ-ONLY across all repos — no code change, no infra mutation, no AWS writes
  - No producer deploy
  - "Zero K-lane dependency — inherited from shape §15.1 PRESCRIBED (`shape:1501-1504`), NOT from the S4 sprint block, which declares no `fences:` key (`shape:672-703`). The fence's own operative words bar a number that ONLY EXISTS on the K-lane. See §9.3 — rev-1 mis-sourced this fence to an exit criterion and over-read it."
self_attestation_cap: MODERATE
verdict: QUALIFIED-RECOMMENDATION + NARROWED-NEGATIVE-RESULT (rev-1's BOUNDED-NEGATIVE-RESULT is WITHDRAWN)
uvp_status:
  UV-P-5: CLOSED (stated reason FALSIFIED; real owner resolved; independently re-verified at rev-2)
  UV-P-6: RETIRED as non-load-bearing (rev-2)
  UV-P-7: OPEN (named human owner)
  UV-P-8: OPEN (Logs Insights dollar cost)
  UV-P-9-NEW: OPEN (Asana story retention — vendor property; bounds option (g)'s depth)
  UV-P-10-NEW: OPEN (option (g) story-cache coverage on the offers board)
  UV-P-11-NEW: OPEN (last_modified non-null in practice, not merely declared)
---

# ADR — Mission-A source-of-record for board-behaviour metrics

> **Sprint S4, asana-native-insight-delivery.** Decide and contract the
> source-of-record for board-behaviour metrics BEFORE any Mission-A build.
> A negative result is a first-class outcome and is decision-grade input to
> GATE-FORK.

---

## REVISION 2 — what changed under BLOCK

> Rite-disjoint critic: **eunomia `entropy-assessor`**, verdict **BLOCK**,
> `.ledge/reviews/CRITIQUE-s4-mission-a-source-of-record-2026-08-12.md`.
> Every finding below was **re-verified own-hands at source in this dispatch**;
> I did not accept the critique's receipts on trust any more than it accepted mine.

### The headline

**The recommendation did NOT change. The §11 scope ruling DID.**

- **§7.1's recommendation of option (b) STANDS UNCHANGED.** The critic attacked it
  on all six grounds and could not break it; I re-verified every column
  declaration and route flag again here.
- **§11's *"if and only if"* is WITHDRAWN.** It was a **false biconditional**, and
  it was feeding a live, date-bounded, operator-reserved decision (GATE-FORK, free
  until 2026-08-18). It told the operator that Mission A is buildable as framed
  *only if* they rule the readout may begin its history at first run. **That is
  false. A third path exists, it is already built and already deployed, and it is
  better contracted than the source this ADR recommends.** The corrected statement
  is at §11.

**I state this plainly because the direction of the error is the worst one
available: rev-1 would have told the operator they cannot do something they can.**

### Disposition of every critic finding

| # | Finding | Disposition | What moved |
|---|---|---|---|
| **F-1** | Option space asserted complete at six; a seventh exists | **ACCEPTED** | **§5 option (g)** added and dispositioned; **§6** coupling row added; **§7.2** re-derived; **§7.3** row added; **§11** rewritten; **§16** exit criterion 1 re-stamped **NOT MET → MET at rev-2** |
| **F-2** | "The retrospective spine is `SectionInfo`-derived, decisively" | **ACCEPTED on substance; REJECTED on one premise** | The watermark **is** `max(last_modified)` — four write-path receipts + the docstring, all verified here (§9.3). Leg 3 withdrawn as decisive. **But the critic is wrong that no fence existed** (§9.3, receipt `shape:1501-1504`) |
| **F-3** | `last_modified` is modification, not movement | **ACCEPTED** | §3, §5(b), §7.2 corrected everywhere the word "move" appeared. The move record lives in **Asana stories** — §5(g) |
| **F-4** | Dual classification semantics; `section` alone is insufficient | **ACCEPTED-WITH-NARROWING** | §5(b) and §8.4 precondition 4. **Narrowing**: the divergence is *closable consumer-side* — `is_completed` is in the same row payload (`base.py:54-59`) |
| **F-5** | `OFFER_CLASSIFIER` staleness worse than stated | **ACCEPTED** | §8.3 gains an **added-section** row (distinct from renamed); §8.5 sharpened |
| **F-6** | `last_modified` non-null declared, not probed | **ACCEPTED** | Opened as **UV-P-11**. I did not probe it either |
| **F-7** | `RowsMeta` is `extra="forbid"` and growing → strict-parser break | **ACCEPTED, and EXTENDED** | §8.4 precondition 5; §9.2. **Extended**: I found `honest_empty` is itself a `RowsMeta` field *derived from the manifest* (`query/models.py:466-478`) — a tension the critic missed (§9.2) |
| **F-8** | "The spec contains no `/rows` path" | **ACCEPTED** | §5(b) Weakness 1 and §8.2 restated: documented-but-**unschematized** (`openapi.json:9689-9695`, `"in_schema": false`) |
| **F-9** | Three refusal causes → two are failures | **ACCEPTED** | §5(b) Weakness 3 |
| **F-10** | Empty-serve indistinguishability | **ACCEPTED-WITH-NARROWING** | §8.4 precondition 6. **Narrowing**: the clean fix reads `meta.honest_empty`, a K-lane field — so the precondition is stated as a *fork*, not a free action (§9.2) |
| **F-11** | Grade inflation on the negative result | **ACCEPTED** | §15 re-graded |
| **F-12** | Receipt-precision drift, eight sites | **ACCEPTED** | All corrected in place; §14 SVR ledger re-anchored |
| **F-13** | §8.3 ratio is worse than 4:3 | **ACCEPTED; recount differs in binning** | §8.3 recounted to **7 silent : 3 loud : 1 partial**. Same ratio as the critic's, reached by a different binning — I place F-7 as **loud** (a `ValidationError` is loud) and `project_gid` as **partial**, and add the added-section mode |
| **§3 (S1 convergence)** | Shared inherited chain, not corroboration | **ACCEPTED** | §5(a) now credits S1's routing by name; §12 discharges both routed UV-Ps |
| **§5.2 (fence audit)** | `ref=0fb9527b` could not be checked (UV-P-C-2) | **DISCHARGED IN S4's FAVOUR** | Verified own-hands at `origin/main`. **And it is better evidence than rev-1 claimed** — §4.1 |
| **UV-P-C-3** | Live AWS readings unverifiable in the critic's seat | **DISCHARGED — and it costs me one grade** | Re-probed live. Retention 30 **confirmed**. But I also found the `storedBytes` corroboration argument is **weaker than rev-1 stated** — §4 |

### Where the critic is wrong, with receipts

1. **"The S4 sprint block declares no `fences:` key at all… an exit criterion is
   not a prohibition you were operating under."** The first clause is **true and I
   verified it** (`shape:672-703` — no `fences:` key). The inference is **false**.
   The shape carries an initiative-level fence register at **§15.1 PRESCRIBED —
   must follow**, `shape:1501-1503`: *"**Zero K-lane dependency**: no touch on the
   offer-axis combiner, the freshness-meta reducer, `RowsMeta` / `AggregateMeta`,
   the manifest write path, or `SectionInfo`."* Corroborated by success criterion
   `shape:82` and failure signal `shape:88`. **The fence is real and binding.**
   The critic checked only the sprint block.
   **The critic's substantive correction survives anyway, and lands harder** — see
   §9.3, where the fence's *own next sentence* (`shape:1504`) is the ground that
   dissolves the over-read, and it is a better ground than the exit-criterion
   argument the critic offered.
2. **F-13's binning.** F-7 (strict-parser break on additive `RowsMeta`) is a **loud**
   failure — a `ValidationError` raises. The critic binned it silent. The 7:3 ratio
   is right; the arithmetic behind it was not (§8.3).
3. **Line-number drift in the critique's S1 citations.** `PREDICATE-sayable-set…`
   was revised at 22:56, after the critique's read at 22:52. The critic's `:338-343`
   / `:516-518` no longer resolve; the same text is now at `:615-624` and `:797-799`.
   **Not a critic error — a moving substrate.** I re-anchor to the current lines and
   flag the class: a citation into a live sibling artifact decays.

### What I own, in one sentence

I had `openapi.json` open — I counted its six `/v1/query/*` paths for SVR-4 and
asserted the absence of a `/rows` path from that same read. `/api/v1/offers/section-timelines`
sits at `:3859` of the file I was reading. **That is a hard miss inside a read I
performed, not an unlucky one.** The lesson, encoded so the next seat inherits it:

> **Enumerating options from the surfaces you already know is not the same as
> enumerating from the published contract.** An option-enumeration sprint must
> sweep the contract artifact for *candidate surfaces*, not merely query it to
> confirm facts about surfaces already in hand. The two reads look identical and
> are not.

### What survived and is preserved unweakened

- **§4's retention chain** — reproduces **byte-exactly at line level** at
  `origin/main`, re-verified here at a *later* origin/main (`a5c98f9c`) than rev-1
  read. All ten sibling-Lambda sites at exactly the cited line numbers; both a8
  module hops; zero `log_retention_days` inside the module block; zero
  `retention_in_days` in the whole directory.
- **§4.1 is genuinely bigger than Mission A** — and rev-2 makes it **stronger**.
- **§7.1's option (b) recommendation** — unchanged.
- **§9's five per-item K-lane attestations** — confirmed at source, twice.
- **§10's ADR-007 §7.5 symmetry table** — defensible row by row.
- **PV-PARTIAL** — the honest stamp. Unchanged.

---

## §0 Verdict in one paragraph

**QUALIFIED RECOMMENDATION with a NARROWED negative result** *(rev-2: rev-1 said
"bounded"; that scope claim is withdrawn).* For the *recurring, forward-looking*
readout that Mission A actually is, a contractable source exists and is
recommended: **option (b), the offers frame read through the rows query surface,
aggregated into a self-owned snapshot series** — it depends on declared schema
columns, carries no CloudWatch retention dependency, and touches no ADR-007 K-lane
surface. For the *retrospective* half, the negative result **narrows to the log
surfaces only**: no *log-derived* backward-looking source is contractable, because
every one is 30-day-capped and uncontracted. **But the retrospective half is
reachable by two other routes** — option (b)'s own series run forward (which
reproduces brief #1's spine exactly, because that spine *is* `max(last_modified)`),
and **option (g), `GET /api/v1/offers/section-timelines`**, an already-deployed,
already-published endpoint that replays Asana section history over an arbitrary
past window. **Mission A is NOT shown to be more expensive than framed.** What the
operator is choosing between has changed — see §11 and §13.

---

## §1 The question, stated precisely

Shape §2.3 (NF-2) named the hazard: a recurring team-facing readout built on
CloudWatch Logs Insights acquires three uncontracted dependencies (retention,
query cost/latency, schema). This sprint answers: **what should Mission A read
from, and what is the contract?**

Three sub-questions, separated because they have different answers:

| # | Sub-question | Answer (rev-2) |
|---|---|---|
| Q1 | Is there a contractable source for the **forward-looking recurring** readout? | **YES** — §7 option (b) |
| Q2 | Is there a contractable source for a **retrospective 14-day backfill**? | **YES, CONDITIONALLY** — §7 option (g), already deployed and in the published contract, subject to four named caveats. **Rev-1 answered NO; that answer was wrong.** What remains true: no *log-derived* retrospective source is contractable |
| Q3 | Who owns the log retention that NF-2 could not resolve? | **Resolved** — §4, and the answer is worse than NF-2 assumed |

---

## §2 Premise validation of the inbound charge

Per shape §14.2 the receiving seat runs premise-validation before consuming and
surfaces any falsified premise rather than papering it (§14.2 item 5). Full stamp
lives in the companion HANDOFF. One premise **FAILED**:

### FP-S4-1 (FALSIFICATION) — NF-2's stated reason for UV-P-5 is false

Shape §2.3 states: *"I could **not** resolve the asana service's own value
(`terraform/services/asana/` does not exist in the monorepo at `origin/main`)"*.

**That directory exists.** At `autom8y@origin/main` (`0e60e0f5` at rev-1;
re-verified at `a5c98f9c` at rev-2) it holds **17 entries** including `main.tf`,
`variables.tf`, `environments/`, and `s3.tf`.

```
$ git -C .../autom8y ls-tree --name-only origin/main terraform/services/asana/
terraform/services/asana/apply-output.txt
terraform/services/asana/backend.tf
... (17 entries) ...
terraform/services/asana/variables.tf
exit 0
```

**UV-P-5 nonetheless stood open, for a different and more interesting reason**:
`git grep retention_in_days` scoped to that directory returns **zero matches**
(exit 1, re-verified at rev-2). The retention is not absent from the world; it is
**absent from this repo**. §4 resolves where it actually lives.

**Disposition**: the falsified premise does **not** overturn NF-2's conclusion.
NF-2's *finding* (Logs Insights is an uncontracted surface) survives intact and is
in fact **strengthened** by §4 and §5. Only the stated reason for the UV-P is
withdrawn. Recorded here, not papered.

> **Rev-2 addendum — the same false premise propagated through S1, and rev-1 did
> not say so.** `PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12.md:799`
> carries it verbatim (*"REASON: terraform/services/asana/ does not exist at
> autom8y origin/main"*), inherited from `shape:694`. Rev-1 attributed the premise
> to the shape alone. Credit for the propagation path belongs to the critic (§3 of
> the critique).

### Premises that HELD

| Premise | Source | Status |
|---|---|---|
| `query_rows_complete` fires from the asana query surface, not ASR | `query.py:548` | **HELD** — re-read at `4129ae7e`; re-read again at rev-2 |
| `filter-log-events` times out; Logs Insights was used | `EVIDENCE-w1:629` | **HELD** — live-read |
| The emitter carries `classification` + counts | `EVIDENCE-w1:669` / `query.py:556-558` | **HELD** — both re-read. **Rev-2 refinement**: `query.py:557-558` shows `section` and `classification` are **request-filter echoes** (`request_body.section`, `request_body.classification`), not properties of the returned rows |
| ADR-007 §7.5 names the one-way-door hazard class | `ADR-007:1228-1239` | **HELD** — live-read |

---

## §3 What Mission A actually needs — the observables

Derived from EVIDENCE-w1, not assumed. Brief #1's board-behaviour numbers came
from **two** log-derived inputs, not one — the shape named only the second:

| Observable | Brief #1's actual source | Anchor |
|---|---|---|
| **Per-section watermark series** (the cohort-spread spine; 10 239 records over 5 chunks) | `modified_since=` emission from the freshness builder | `EVIDENCE-w1:629-640`; emitter `freshness.py:298-306` |
| **Classification + counts** | `query_rows_complete` | `EVIDENCE-w1:669`; emitter `query.py:548-559` |
| Section → classification mapping | `OFFER_CLASSIFIER` (in-code, static) | `models/business/activity.py:181-230` |

**The shape's NF-2 fenced `query_rows_complete`. But the *spine* of brief #1 was
the watermark series**, and:

```python
# src/autom8_asana/dataframes/builders/freshness.py:298-300
if section_info.watermark is not None:
    watermark = section_info.watermark
    watermark_iso = watermark.isoformat()
```

`section_info` is a **`SectionInfo`** — `dataframes/section_persistence.py:83`.

### §3.1 THE ROOT CORRECTION (rev-2) — modification is not movement

**Rev-1 conflated two different things throughout, and the conflation was
load-bearing.**

`last_modified` is **not a move tracker**. Its declared source is `modified_at`
(`dataframes/schemas/base.py:76-81` — `source="modified_at"`, description
*"Last modification timestamp"*). **It advances on any edit** — a comment, a
custom-field change, an assignee change — not on section movement. Rev-1 called it
*"time-since-last-move"* (§5 option (b) table), *"`last_modified` records the most
recent **move** only"* (Weakness 4), and *"An offer that moved three times in 14
days is one row with one timestamp"* (§7.2). **All three sentences are wrong in the
same way**, and every one is corrected in this revision.

**Why the conflation mattered.** Because rev-1 believed `last_modified` *was* the
move record, it never asked the obvious next question: **where does the move record
actually live?** It lives in **Asana stories** — `resource_subtype ==
"section_changed"`, carrying `new_section.name`, `old_section.name`, `created_at`
(`services/section_timeline_service.py:87-93` opt_fields;
`:245-267` interval construction). **This repo already reads them**, through a
published endpoint. That is option (g), §5.

**And the watermark is not what rev-1 thought either.** `SectionInfo.watermark` is
**`max(last_modified)` over the section's rows** — see §9.3 for the four write-path
receipts and the module's own docstring. It is a *content* quantity derivable from
the row payload, not a *verification* quantity. Rev-1 imported the one-way-door
gravity of `RowsMeta` onto a field ADR-007 classes `+0 fields … two-way — semantics
only` (`ADR-007:1219`).

---

## §4 UV-P-5 — RESOLVED. The real log-group retention owner

The asana ECS log group's retention is **not owned in this repo, and not owned in
the autom8y monorepo either.** It is inherited from a **module default in a third
repo, pinned at a commit ref.** The full chain, each hop receipted, and each hop
**re-verified at rev-2 against `origin/main` = `a5c98f9c`** (a *later* origin/main
than rev-1 read — the chain is stable across both):

```
autom8y@origin/main : terraform/services/asana/main.tf:88   module "service" {
                    : terraform/services/asana/main.tf:101    source = git::.../a8.git//terraform/modules/stacks/service-stateless?ref=0fb9527b
                    :                                          ⟂ block passes NO log_retention_days   (lines 88–350: zero matches)
        │
        ▼  (out of monorepo — terraform/modules/stacks/ DOES NOT EXIST at autom8y origin/main)
a8@0fb9527b         : modules/stacks/service-stateless/variables.tf:422-426   default = 30
                    : modules/stacks/service-stateless/main.tf:615            log_retention_days = var.log_retention_days
                    : modules/stacks/service-stateless/main.tf:527-528        module "ecs" → ../../primitives/ecs-fargate-service
        │
        ▼
a8@0fb9527b         : modules/primitives/ecs-fargate-service/main.tf:111-113
                    :   resource "aws_cloudwatch_log_group" "service" {
                    :     name              = "/ecs/${local.name_prefix}"
                    :     retention_in_days = var.log_retention_days
                    : variables.tf:192-195  default = 30
        │
        ▼
LIVE (read-only)    : /ecs/autom8y-asana-service  →  retentionInDays: 30
                    :                                storedBytes: 1 554 135 548
```

> **Rev-2 correction to the block extent (critic F-12).** The `module "service"`
> block closes at `main.tf:350`, not `:361` — `:362` opens `module "asana_redis"`.
> The zero-match conclusion is unaffected and was re-run against the corrected
> range: `sed -n '88,350p' | grep -c log_retention_days` → **0**.

### §4.0 Live corroboration — and an honest downgrade of rev-1's inference

Re-probed at rev-2, read-only:

```
$ aws logs describe-log-groups --log-group-name-prefix /ecs/autom8y-asana-service
{"name": "/ecs/autom8y-asana-service", "retentionInDays": 30, "storedBytes": 1554135548}
```

`retentionInDays: 30` is **directly confirmed for the third time** (EVIDENCE-w1,
rev-1, rev-2). That is the load-bearing datum and it is solid.

**But rev-1's corroboration *argument* was inflated, and I am withdrawing it.**
Rev-1 wrote: *"`storedBytes` = 1 554 135 548 — byte-for-byte the figure recorded at
`EVIDENCE-w1:626`. Two independent readings of the same group, eleven days apart in
authorship, agree exactly. `[STRONG]`"* I probed the group's write activity:

```
$ aws logs describe-log-streams --log-group-name /ecs/autom8y-asana-service \
    --order-by LastEventTime --descending --max-items 3
  most recent lastEventTimestamp = 1786567110377   (≈ 21.5 minutes before the probe)
```

**The group is actively written.** A `storedBytes` figure that is byte-identical
across three readings spanning eleven days on an actively-written group is
therefore **not three converging measurements** — it is a cached or
slowly-refreshed API field. The agreement establishes that all three readings
address the **same log group**, and nothing more. **It does not corroborate
liveness or freshness, and rev-1's `[STRONG]`-on-convergence reasoning is
withdrawn.** UV-P-5 remains **CLOSED** on two genuinely disjoint methods — the
four-hop terraform chain and the direct retention read — not three. §15 is
re-graded accordingly.

*(This is a finding against my own prior work that the critic could not have made:
its seat had no Bash. It is recorded here rather than left for someone else.)*

### §4.1 The finding NF-2 was reaching for, stated properly — and it now demonstrates itself

> **Every Lambda in the asana Terraform stack declares its log retention
> explicitly (`log_retention_days = 30`, ten sites). The ECS service — the one
> that emits `query_rows_complete` — declares nothing and inherits a default from
> a different repository at a pinned ref.**

Ten explicit declarations, **each re-verified at `origin/main` = `a5c98f9c` at
exactly the cited line number**:
`main.tf:568, 737, 912, 1866, 2088, 2217, 2298, 2423`,
`enrollment_intent_bridge_lambda.tf:342`, `traffic_offer_divergence_lambda.tf:190`.
`git grep retention_in_days` across the whole directory returns **exit 1**.

**Consequence for Mission A**: today's headroom is real — 30 days retained against
a 14-day lookback, 16 days of slack. But the number is an *inherited default*,
changeable by a `ref=` bump in `terraform/services/asana/main.tf:101` that produces
**zero diff in any asana-owned file**. A readout with a 14-day window would silently
truncate on the first bump that lowers the default, with no signal in this repo's
diff.

#### §4.1.1 The finding demonstrating itself, in its own source file (NEW at rev-2)

Rev-1 asserted this coupling as a *mechanism*. It is not a mechanism; it is a
**live, present-tense condition in the file that carries it**, and the
documentation is **already out of sync with the pin it documents**.

At `origin/main` (`a5c98f9c`), `terraform/services/asana/main.tf`:

| line | content | what it shows |
|---|---|---|
| `:88` | `module "service" {` | the block |
| `:89-100` | a twelve-line comment block documenting the bump chain, whose **terminal named value is `80402fd3`** (`:96` *"Bumped a28fa33 -> 80402fd3 (a8 #104…)"*; `:99` *"a28fa33..80402fd3 carries ONLY that clamp … (re-verified 2026-07-20 at bump time)"*) | the prose record |
| `:101` | `source = "git::…/service-stateless?ref=0fb9527b"` | **the live pin** |

`grep -c '0fb9527b'` over that file at `origin/main` returns **1** — the single
occurrence is the `ref=` on `:101` itself. **The effective pin is named in no
comment anywhere in the file.** A sixth bump was applied and the twelve lines of
prose documenting the bump chain were not updated.

**And the divergent branch carries a different value at the same line.** Read
explicitly and labelled — `git show HEAD:terraform/services/asana/main.tf | sed -n '101p'`
at `fix/wss-wildcard-scope-bypass-closure` (`58c5eb92`, **not** an ancestor of
`origin/main`) — returns `ref=80402fd3`. Two refs of the same repo carry two
different pins of the same module, and the bump between them leaves **no diff in
any asana-owned file**.

> **Restated at full strength.** This is not "an ECS module inherits a default."
> It is: *a cross-repo, cross-org retention floor is set by a value that (i) is
> declared in neither consuming repo, (ii) contradicts an explicit ten-site local
> convention in its own directory, (iii) is currently undocumented in the twelve
> lines of prose written specifically to document it, and (iv) differs across two
> live refs of the consuming repo.* Every future log-derived readout in this stack
> inherits that floor. **This is materially worse than NF-2's framing of "finite
> and variable-driven," and it is bigger than Mission A.** Routed, not decided —
> §13 item 2.

**UV-P-5: CLOSED.** Value = 30 days. Owner = `autom8y/a8`,
`terraform/modules/stacks/service-stateless` + `.../primitives/ecs-fargate-service`,
consumed at pin `0fb9527b`. Not `terraform/services/asana/`, and not any file in
either repo the shape searched.

---

## §5 Options — ENUMERATED BEFORE RECOMMENDATION

Per `option-enumeration-discipline`. **Seven options** at rev-2; the charge named
four, the dependency trace surfaced two, and the rite-disjoint critique surfaced
the seventh. **No recommendation appears in this section.**

> **Rev-2 enumeration-method note, recorded so the failure is inheritable.**
> Rev-1's enumeration was built by tracing *from the surfaces already in hand*
> (the emission, the schema, the forwarder, the S3 layout). It was **not** built by
> sweeping the **published contract artifact** for candidate surfaces — even though
> that artifact (`docs/api-reference/openapi.json`) was open and being queried for
> SVR-4. Option (g) sits at `:3859` of that file. The two reads look identical and
> are not: *querying a contract to confirm a fact about a known surface* is not
> *sweeping a contract to discover unknown surfaces*. **Rev-1's exit criterion 1
> self-attestation of MET was wrong** (§16).

### Option (a) — CloudWatch Logs Insights over `query_rows_complete`
*(the shape's default; the status quo of brief #1)*

Read `/ecs/autom8y-asana-service` via Logs Insights on a schedule, parsing
`query_rows_complete` for `classification` and counts, plus the `modified_since=`
lines for the watermark series.

- **Surface**: `query.py:548-559`, an observability emission. `freshness.py:298-306`.
- **Retention**: 30 days, inherited cross-repo default (§4). 16 days of headroom
  against a 14-day window, undeclared and externally mutable.
- **Cost / latency**: `filter-log-events` times out over multi-day windows
  (`EVIDENCE-w1:629`); Logs Insights was required, and brief #1 needed **five
  chunked queries** to cover 14 days. Scan cost is proportional to bytes scanned
  over a group currently holding ~1.55 GB. *(Dollar figure not receipted — UV-P-8.)*
- **Schema**: uncontracted. Nothing versions the log line; no test fails if a
  field is renamed.
- **⚠ Coverage dependency — ROUTED TO THIS SPRINT BY S1, and rev-1 failed to
  credit it.** `query_rows_complete` fires **only when a caller queries.** Its
  counts are *query-result* counts, not board state. **This finding is S1's, not
  mine**: `PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12.md:619-624`
  derives it and closes *"`query_rows_complete` … emits `entity_type`,
  `total_count`, `returned_count`, `query_ms`, `caller_service`, `predicate_depth`,
  `section`, `classification` — **request-shaped, with no edit-time field**. A
  section appears in that stream iff some caller queried it. **Routed to S4** as a
  named option-enumeration input; **not decided here.**"* Rev-1 presented it as
  *"⚠ Coverage dependency the shape did not name"* — as its own discovery — and
  cited neither S1 nor the routing. **That was a provenance elision**, and its cost
  was real: it made one reading look like two agreeing readings (see §12).
  - **What I add own-hands** (verified at `query.py:557-558`): `section` and
    `classification` in that emission are **request-filter echoes** —
    `"section": request_body.section` and
    `"classification": request_body.classification`. They are *authored by the
    caller*, not properties of the returned rows. A caller querying without a
    classification filter emits `classification: null`; and `RowsRequest` enforces
    the two mutually exclusive (`query/models.py:379-384`), so **one call can never
    carry both**. The dependency is therefore worse than "coverage is hostage to
    call patterns": the readout's *dimensions* are hostage to call shape.
  - Today's declared consumers are the monolith's
    (`consumer_column_requirements.vendored.json:9-16`,
    `business_offers.active_offers_frame` → `/v1/query/project/rows`;
    `:17-24` `fetch_section_rows` → `/v1/query/section/rows`). **No consumer is
    declared against `entity_type=offer` rows at all.** *(That file is an FM-5 seed,
    not a caller census; I do not treat it as one.)*
- **K-lane contact**: the logged counts are read from `result.meta.*` = **`RowsMeta`**
  (`query.py:552-554`; `query/models.py:387-398`). The watermark series is read
  from **`SectionInfo.watermark`** (`freshness.py:298-300`). Both are named K-lane
  surfaces. Not a *contract* dependency — a **derived-value** dependency, which is
  the same hazard with weaker guarantees. *(Rev-2: see §9.3 — the fact that the
  watermark's **value** is independently derivable does not make **mining it from
  this log line** any less a derived-value dependency on an uncontracted surface.
  Option (a) is rejected on that ground, which is unaffected.)*

### Option (b) — the offers frame, read through the rows query surface
*(the charge's option (b))*

Read the offers frame per-row via `POST /v1/query/{entity_type}/rows` and
aggregate locally into a self-owned snapshot series.

- **Surface**: `BASE_SCHEMA` (`dataframes/schemas/base.py:107`) + `OFFER_SCHEMA`
  (`dataframes/schemas/offer.py`) — **declared `ColumnDef`s with name, dtype,
  nullability, and source**.
- **The observables are all present in the row payload**:

| Column | Declaration | Yields |
|---|---|---|
| `section` (Utf8, nullable, from memberships) | `base.py:83-88` | board position |
| `last_modified` (Datetime, non-null declared, ← `modified_at`) | `base.py:76-81` | **time since last *modification of any kind*** — see §3.1; **not** time-since-move |
| `created` (Datetime, non-null, ← `created_at`) | `base.py:41-47` | cohort age |
| `is_completed` (Boolean, non-null, ← `completed`) / `completed_at` | `base.py:54-59`, `:61-66` | terminal state |

- **⚠ `classification` is derivable from the payload, but NOT from `section` alone
  (rev-2 correction, critic F-4).** Rev-1 said *"`section` is sufficient."* **It is
  not.** Two classification semantics are live in this codebase and they disagree:
  - the **query surface's own** classification filter is **section-only** —
    `query/engine.py:153-161`, `pl.col("section").str.to_lowercase().is_in(...)`;
  - the **service's resolution path** applies an **`is_completed` terminal override
    → INACTIVE *before* the section lookup** — `services/universal_strategy.py:510-513`
    (*"Per SD-6: is_completed=True is terminal override -> INACTIVE"*), with null
    section → UNKNOWN (`:515-518`) and unrecognized section → UNKNOWN
    (`:521-524`, EC-9).

  A `section`-only readout will classify **completed** offers into their section's
  group while other surfaces call them INACTIVE. **Narrowing in option (b)'s
  favour**: the divergence is *closable consumer-side at zero cost*, because
  `is_completed` is in the same row payload (`base.py:54-59`). What is **not**
  optional is **declaring which semantic the readout implements** — §8.4
  precondition 4. `OFFER_CLASSIFIER` remains a pure static map from section *name*
  → group (22 active / 5 activating / 3 inactive / 6 ignored,
  `models/business/activity.py:181-230`), and `classify()` is
  `self._mapping.get(section_name.lower())` returning `None` for any unknown name
  (`activity.py:66-74`).
- **Retention dependency**: **NONE.** The frame is current state; no log group is read.
- **Coverage**: complete by construction — every row, every run. No dependency on
  third-party call patterns.
- **⚠ Weakness 1 — the route is excluded from the published *schema*** *(rev-2
  restatement, critic F-8)*: `query.py:83-84` declares two routers; the
  introspection router is `include_in_schema=True`, and **the execution router —
  which carries the rows POST at `query.py:321` — is `include_in_schema=False`**.
  Rev-1 said *"the spec contains no `/rows` path."* **More precisely**: the spec
  contains six `/v1/query/*` **schematized** paths and none for `/rows`, **but the
  rows route is present in the artifact as a non-schema annotation** —
  `openapi.json:9689-9695`, under `x-query-method-candidates`, with
  `"in_schema": false` (`:9692`) and `"path": "/v1/query/{entity_type}/rows"`
  (`:9694`). The route is **documented-but-unschematized**, not absent.
  **The operative conclusion is unchanged**: the CI spec drift check
  (`.github/workflows/test.yml:77-79`) validates the schema and therefore does
  **not** cover the route Mission A would consume.
- **⚠ Weakness 2 — the column contract registry is half-armed**: a consumer-column
  contract mechanism exists (`consumer_column_requirements.vendored.json`,
  `schema_version: 1`), but its own note says the drift check asserts vendored ==
  source *"once the source path is handed back (telos DEFER). Until then the
  freshness guard runs in schema-only mode."* (`:6`). The guard that would protect
  a registered consumer is not fully armed.
- **⚠ Weakness 3 — serve-path availability coupling** *(rev-2 correction, critic
  F-9)*: reading the rows endpoint is a live request against the asana serve path,
  which refuses when the frame is not warm. Three causes are enumerated in code
  (`api/metrics.py:114-147`), but **only two are serve-path failures**:
  `cadence_503` (`:120-122`, coalesced request waited past
  `CACHE_BUILD_WAIT_TIMEOUT`) and `capacity_502` (`:124-128`, request-time build
  failed/timed out). The third, `honest_refusal`, is described in code as
  *"an attested honest-empty 200 … **NOT a failure**"* (`:130-135`). Logs are
  passive; this is not. A scheduled readout inherits warm-state coupling **on two
  causes**. *(But `honest_refusal` is a hazard for a different reason — §8.4
  precondition 6.)*
- **⚠ Weakness 4 — snapshot-only history** *(rev-2 correction, critic F-3)*:
  a snapshot carries no history. **Rev-1 stated this correctly but justified it
  wrongly**, writing *"`last_modified` records the most recent **move** only. An
  offer that moved three times in 14 days is one row with one timestamp."* That
  sentence is false about `last_modified` (§3.1): the column advances on any edit,
  so it is not a record of moves at all — not even of the most recent one. **The
  weakness itself stands and is simply more basic**: one row carries one
  point-in-time state; a series must be accumulated forward, not recovered
  backward. **What rev-1 concluded from this is what changes** — a snapshot's
  inability to look backward is *not* the same as no retrospective source existing.
  See §5 option (g).
- **K-lane contact**: **none** in the row payload. See §9.

### Option (c) — a new purpose-built emission

Either (c1) a new structured log event designed as a data contract, or (c2) a new
Prometheus counter/gauge with a `classification` (and possibly `section`) label
remote-written to AMP, or (c3) a scheduled job that computes the aggregate and
writes a versioned artifact with an explicit `schema_version`.

- **(c2) is not free-riding on what exists**: the current metric surface carries
  **no classification dimension**. `RECEIVER_QUERY_OUTCOME` labels are
  `["entity_type", "outcome"]` (`api/metrics.py:108-112`);
  `RECEIVER_QUERY_FALLBACK_CAUSE` labels are `["entity_type", "cause"]`
  (`api/metrics.py:140-147`). A grep for `classification` across `api/metrics.py`
  returns one prose comment and zero label declarations. A new label is a new
  emission, and a per-section label on a 36-section board is a real cardinality
  decision.
- **Cost**: this is the only option requiring **new code and a producer deploy** —
  outside S4's fence entirely, and colliding with the shape §17 window register.
- **Contractability**: **highest of any option.** A purpose-built emission can carry
  a `schema_version`, a named owner, and a RED-on-drift test by construction.
- **Verdict on cost**: genuinely more expensive than framed. Mission A was framed as
  buildable-and-deliverable under P-3; (c) makes it a deploy-bearing change.

### Option (d) — NO contractable source; Mission A is more expensive than framed

The stated negative outcome. **Rev-1 found this option FIRES on the retrospective
half. Rev-2 WITHDRAWS that finding.** It fires **only on the log-derived
retrospective surfaces**, which is a much narrower claim and does **not** support a
Mission-A cost conclusion. See §7.2.

### Option (e) — Grafana Cloud Logs (Loki), via the live forwarder
*(NEW at rev-1 — not in the charge's enumeration; surfaced by the dependency trace)*

A **live, second, independent copy** of every `/ecs/autom8y-asana-service` event
already exists outside CloudWatch.

- **Receipted live**: `describe-subscription-filters` on the group returns filter
  `loki-forwarder-asana`, pattern `""` (all events), destination
  `arn:aws:lambda:us-east-1:696318035277:function:autom8y-cw-loki-forwarder-production`.
- **Terraform**: `terraform/services/log-forwarder/subscriptions.tf:22-40` — the
  `log_groups` map is *"the single source of truth for which log groups are
  subscribed"*; asana is one of 13.
- **Fidelity**: the forwarder is stated to preserve the **full message verbatim** —
  `forwarder.py:169` `streams[key].append([ts_ns, message])`. **Rev-2 honesty
  note**: the critic could not locate the forwarder source to re-verify this, and
  I did not re-read it in this dispatch either. It is not load-bearing — option (e)
  is rejected on independent grounds — but it is **single-seat-attested only** and
  is flagged as such rather than presented as corroborated.
- **Retention**: **UNKNOWN** — governed by the Grafana Cloud plan, not by any file
  in any of the three repos. *(Rev-1 carried this as UV-P-6; rev-2 RETIRES it as
  non-load-bearing — §12.)*
- **Delivery guarantee is weaker, not stronger**: `MAX_ATTEMPTS = 3` with backoff
  (`forwarder.py:56`), and on final failure the exception propagates to a DLQ
  (`log-forwarder/main.tf:206-214`, `maximum_retry_attempts = 0`). A DLQ'd batch is
  absent from Loki but present in CloudWatch. Loki is therefore a *lossier* copy.
  *(Same single-seat-attestation caveat as above.)*
- **K-lane contact**: identical to option (a) — same lines, same origin.

### Option (f) — the S3 dataframe substrate, read directly
*(NEW at rev-1 — not in the charge's enumeration)*

Read `dataframes/{project_gid}/dataframe.parquet` (or `sections/{gid}.parquet`)
straight from S3, bypassing the serve path.

- **Layout** (`section_persistence.py:8-19`):
  `dataframes/{project_gid}/{manifest.json, sections/*.parquet, dataframe.parquet,
  watermark.json, gid_lookup_index.json}`.
- **Attraction**: full frame, no serve-path warm coupling, no HTTP.
- **⚠ Disqualifying**: the key layout is **owned by `section_persistence.py`** — the
  same module that defines `SectionInfo` (`:83`), `SectionManifest` (`:117`), and
  the manifest write path (`:480` `_save_manifest_async` def, `:549` call site).
  `manifest.json` sits in the same prefix as the parquet. Nothing versions the key
  structure. Consuming it is a dependency on a K-lane module's private storage
  layout. **This is a dependency on the module, not merely on a value it computes**
  — the distinction §9.3 draws, and it is why (f) is disqualified where the
  watermark's *value* is not.
- **Also**: EVIDENCE-w1's own fence explicitly excluded S3 object reads
  (`EVIDENCE-w1:675-679`), which is a signal about the intended posture toward this
  surface.

### Option (g) — `GET /api/v1/offers/section-timelines`, the published section-history endpoint
*(NEW at rev-2 — surfaced by the rite-disjoint critique, F-1. **This is the option
rev-1's negative result was refuted by.** Every receipt below re-verified
own-hands in this dispatch.)*

A live, mounted, **published** endpoint that reconstructs offer section history by
replaying Asana's own story feed over an **arbitrary caller-specified past window**.

**What it is:**

| property | receipt |
|---|---|
| Route declared with Pydantic `response_model`, `summary`, `response_description` | `src/autom8_asana/api/routes/section_timelines.py:75-82` |
| Takes an arbitrary **retrospective window** — `period_start`, `period_end`, both inclusive dates | `section_timelines.py:86-93` |
| Optional `classification` filter (`active`/`activating`/`inactive`/`ignored`) | `section_timelines.py:94-98` |
| *"Computes `active_section_days` and `billable_section_days` for each offer by **replaying its Asana section history within the specified date range**"* | `section_timelines.py:100-106` |
| Imported and **unconditionally mounted** — no feature flag, no gate | `api/main.py:76` (import), `api/main.py:488` (mount), `api/routes/__init__.py:50` |
| **In the published OpenAPI contract** — therefore covered by the CI spec-drift check that option (b)'s route is NOT | path `docs/api-reference/openapi.json:3859`; schemas `OfferTimelineEntry` `:1106`, `SectionTimelinesResponse` `:1907`, `SuccessResponse_SectionTimelinesResponse_` `:2061`, `$ref` `:3912`; gate `.github/workflows/test.yml:77-79` |
| **Same board** as `OFFER_CLASSIFIER` | `section_timeline_service.py:84` `BUSINESS_OFFERS_PROJECT_GID = "1143843662099250"` == `models/business/activity.py:183` |
| Classification applied via the same classifier registry | `section_timeline_service.py:422-429`, `:232-233` |
| Intervals built from `section_changed` stories with real `entered_at` / `exited_at` | `section_timeline_service.py:87-93` (opt_fields), `:197` (`_build_intervals_from_stories`), `:245-267` (interval close/open); `models/business/section_timeline.py:21-40` |
| Day-counting **clamps to the requested (past) period** | `models/business/section_timeline.py:145-153` |
| **NO CloudWatch retention dependency** — Asana is the store | `section_timeline_service.py:87-93` |
| **NO K-lane contact** — reads `AsanaClient` stories + `CacheProvider`; no `SectionInfo`, no `RowsMeta`, no `AggregateMeta`, no manifest read, no freshness-meta field | `section_timeline_service.py:422-443`, `:477-481`, `:495-496` |
| **NO producer deploy** — already built, already mounted | `api/main.py:488` |

**Contract wrinkle**: the route carries `openapi_extra={"x-fleet-envelope-exempt": True}`
(`section_timelines.py:81`). It does not affect reachability or schema coverage, but
a consumer must handle a response envelope that is declared exempt from the fleet
envelope convention. Named so it is not discovered later.

**⚠ The four honest caveats — this option is CONDITIONED, not free:**

1. **It is not brief #1's statistic.** The HTTP response model
   (`models/business/section_timeline.py:158-226`, `extra: "forbid"` at `:212`)
   exposes only `offer_gid`, `office_phone`, `offer_id`, `active_section_days`,
   `billable_section_days`, `current_section`, `current_classification`. The raw
   `SectionInterval` list and `story_count` stay on the in-process `SectionTimeline`
   dataclass (`:42-62`) and are **not returned**. A readout wanting per-move
   intervals needs an **additive field on an already-published model** —
   option-(c)-class work, but an order of magnitude smaller than a new emission,
   and **covered** by the spec-drift gate rather than uncovered.
2. **`current_section` is current, not as-of-period-end** (`section_timeline.py:200-203`,
   from the last interval). Per-day occupancy is nonetheless reconstructible by
   sweeping single-day windows, since the day-count clamps per call
   (`section_timeline.py:145-153`) — 14 calls for a 14-day window.
3. **A real silent-degradation defect.** `read_stories_batch` is pure-read
   (`section_timeline_service.py:495-496`). Gaps up to
   `MAX_INLINE_STORY_FETCHES = 50` (`:502`) are self-healed inline (`:505-531`);
   **beyond 50, the gap is logged and NOT filled** (`:532-541`,
   `story_cache_gap_above_threshold`). Cache-missed offers then fall through to
   `_build_imputed_interval` (`:603-623`, via `:272-300`) and are returned **as if
   they had never moved**, with `story_count=0`. `cache_hits` / `cache_misses` are
   computed (`:546-547`, `:560`, `:604`) and are passed to the derived-cache store
   (`:637-638`) and logged (`:658-659`) — but are **not returned to the consumer**.
   **A consumer cannot distinguish a never-moved offer from a cache miss.** And a
   client with no resolvable cache provider returns `[]` **silently**
   (`:430-443`).
4. **Coverage is current-membership-scoped.** It enumerates tasks *currently* in
   the project (`section_timeline_service.py:477-481`). **An offer removed from the
   board mid-window is absent from the result.** For a retrospective cohort measure
   this is a real denominator hazard and is the mirror image of option (a)'s
   caller-hostage denominator.

**Two additive-disclosure preconditions** *(the same class §8.4 already imposes on
option (b); stated here, not decided)*: surface `cache_hits` / `cache_misses` on
the response, and either surface `story_count` per entry or otherwise mark imputed
entries, so caveat 3 becomes visible rather than silent.

**What I could not verify** — carried honestly, not filled with plausible
reasoning:

- **Asana's own story retention** — whether `section_changed` stories persist
  beyond any vendor window. This bounds option (g)'s retrospective **depth** and
  is a vendor property not resolvable from any repo. **UV-P-9.**
- **The live story-cache hit rate on the offers board** — which decides whether
  caveat 3 is a footnote or a disqualifier. **UV-P-10.** It is cheaply answerable:
  the emissions already exist (`story_cache_gap_above_threshold`,
  `inline_story_fetch_complete`, `timeline_computed_on_demand` at `:532-541`,
  `:522-531`, `:656-661`).
- **That the endpoint is live and correct in production.** It is mounted
  (`api/main.py:488`) and published (`openapi.json:3859`); **that is
  code-and-contract attestation, not live attestation.** I made no HTTP request to
  the serve path (§16 fence row).

---

## §6 Coupling analysis — the three-check gate, per option

Coupling context checks (bounded context / intentionality / directionality) applied
**before** any severity is assigned, per the coupling-context discipline
[AQ:SRC-006 Martin 2002] [STRONG], [DP:SRC-005 Evans 2003] [MODERATE].

| Option | Bounded context | Intentionality | Directionality | Coupling type | Score | Confidence |
|---|---|---|---|---|---|---|
| **(a) Logs Insights** | **CROSSES** — product/reporting context reading the observability context | **INCIDENTAL** — nothing designed this emission as a data contract | Unidirectional | **Stamp + content** (reads fields of an internal object via a log line) | **HIGH — hotspot** | **High** (manifest + code + live probe) |
| **(b) rows query surface** | **ALIGNED** — asana board data read by an asana board readout | **DESIGNED** — `s2s_router`, JWT, an FM-5 consumer registry exists for exactly this | Unidirectional | **Data** (declared columns) | **MODERATE — not a hotspot** | **High** (schema decls + route decls + spec artifact) |
| **(c) new emission** | ALIGNED (by construction) | DESIGNED (by construction) | Unidirectional | **Data** | **LOW** | **High** (would be authored) |
| **(e) Loki** | CROSSES + **adds a vendor boundary** | INCIDENTAL | Unidirectional, **two hops** | Stamp + content, lossy | **HIGH — hotspot** | **High** (live filter probe + forwarder source) |
| **(f) S3 substrate** | CROSSES — reaches into a K-lane module's private storage | INCIDENTAL | Unidirectional | **Content coupling** (the worst grade — reaching into internal representation) | **HIGH — hotspot** | **High** (docstring + code) |
| **(g) section-timelines endpoint** *(NEW rev-2)* | **ALIGNED** — asana board history read by an asana board readout, same project GID (`section_timeline_service.py:84` == `activity.py:183`) | **DESIGNED** — declared `response_model`, published schema, authenticated route, explicit period parameters | Unidirectional; **adds a vendor hop** (Asana stories) that (b) does not have | **Data** (declared response model, `extra="forbid"`) — but **stamp** for any consumer that must infer coverage from an absent field (caveat 3) | **MODERATE — not a hotspot**, with a **named degradation risk** | **High** on structure (route + schema + service code); **UNKNOWN** on operational coverage (UV-P-10) |

**The gate is doing real work here.** Options (b) and (g) both score high on raw
surface area yet neither is a hotspot: both couplings are bounded-context-aligned
and intentional — the natural domain shape, not incidental coupling. Options
(a)/(e)/(f) score as hotspots not because the numbers are larger but because all
three fail the intentionality check and cross a context boundary. Flagging (b) or
(g) as a hotspot on raw score alone would be the *coupling-score-without-context*
anti-pattern.

**Rev-2 addendum on (g)'s distinctive shape.** (g) is the only option whose
coupling is **strongest at the contract layer and weakest at the operational
layer** — it is *better* contracted than (b) (in-schema vs.
`include_in_schema=False`) while carrying an *operational* silent-degradation mode
(caveat 3) that (b) does not. That inversion is the thing structure-evaluator
should adjudicate: **whether contract quality or operational determinism is the
binding constraint for a recurring readout is not this seat's call.**

---

## §7 Recommendation

### §7.1 For the recurring, forward-looking readout — **ADOPT OPTION (b)** *(UNCHANGED at rev-2)*

**Source-of-record: the offers frame, read per-row through
`POST /v1/query/{entity_type}/rows`, with `classification` derived locally from
`section` **and `is_completed`** via the `OFFER_CLASSIFIER` map, aggregated into a
snapshot series the readout itself owns.**

*(Rev-2 amends only the derivation input, per §5(b) / critic F-4. The
recommendation itself is unchanged, and the rite-disjoint critic attacked all six
grounds and could not break it.)*

Grounds, in order of weight:

1. **It reads declared schema, not an observability side-effect.** `section`,
   `last_modified`, `created`, `is_completed` are `ColumnDef`s with declared dtype,
   nullability and source (`base.py:41-89`) — a versioned schema object.
   `query_rows_complete` is a `logger.info` call.
2. **It carries no retention dependency.** §4's cross-repo, externally-defaulted,
   undeclared 30-day value becomes irrelevant. This alone answers NF-2's hazard 1.
3. **It carries no query-cost or timeout fragility.** NF-2 hazard 2 dissolves;
   `filter-log-events` timing out is not this option's problem.
4. **Its coverage is complete by construction** and does not depend on a third
   party's call pattern — the defect in option (a) that **S1 named and routed here**
   (`PREDICATE…:619-624`).
5. **It touches no K-lane surface** (§9), where (a), (e) and (f) all do.
6. **The coupling is bounded-context-aligned and intentional** (§6) — recommending
   it does not create an incidental cross-context dependency.

**Rev-2 addition — ground 7, which rev-1 had the receipts for and did not draw:**

7. **It reproduces brief #1's spine forward, with zero K-lane contact.** The
   per-section watermark that carried brief #1's cohort spread **is
   `max(last_modified)` over the section's rows** (four write-path receipts, §9.3).
   `last_modified` is a declared column in the payload option (b) already returns.
   **The forward series therefore needs no new observable at all** — it is a
   consumer-side reduction over columns already contracted. This is exactly the
   pattern ADR-007 itself names: *"The content axis shipped consumer-side with
   **zero** producer work because `content_watermark_returned` is derivable from
   the returned rows"* (`ADR-007:1198-1200`).

### §7.2 For the retrospective half — **NARROWED NEGATIVE RESULT** *(rev-1's finding is WITHDRAWN)*

> **WITHDRAWN (rev-1 §7.2):** *"There is no contractable source for a 14-day
> retrospective board-behaviour series, at any acceptable cost."*
>
> **That statement is false.** It rested on three legs; one is refuted, one was
> reasoned from a misdescribed observable, and the class conclusion is refuted by
> option (g).

**What survives, precisely scoped:**

> **No *log-derived* retrospective source is contractable.** Options (a) and (e)
> can look backward at most **30 days**, on an **undeclared, externally-defaulted,
> cross-repo-mutable** retention value (§4, §4.1.1), through an **uncontracted
> schema** with **no version and no consumer registry**, with **coverage and
> dimensionality hostage to caller behaviour** (§5(a)). That remains a correct and
> load-bearing rejection, and it is the whole of NF-2's original hazard.

**What is now known to be reachable, and by which route:**

| Route | Retrospective reach | Cost | Retention dep. | K-lane contact | Contract status |
|---|---|---|---|---|---|
| **(b) run forward** | none backward; full series from first run | **zero** — the recommended source already returns the columns | **none** | **none** | declared columns; route **not** schematized |
| **(g) section-timelines** | **arbitrary past window**, bounded by Asana story retention (UV-P-9) | **zero producer cost** — already built and mounted; two additive disclosure fields wanted | **none** — Asana is the store | **none** | **published + spec-gated** — better contracted than (b) |
| **(a)/(e) log mine** | ≤ 30 days | query cost + chunking | **yes, and mutable cross-repo** | **yes** (derived-value) | **none** |

**Leg-by-leg accounting of the withdrawal:**

- **Leg 1 — "a snapshot cannot reconstruct cohort spread."** *Conclusion stands;
  premise corrected.* A snapshot carries no history — trivially true. But rev-1
  justified it with *"`last_modified` records the most recent move only,"* which is
  false (§3.1). **That false premise is what concealed option (g)**: believing
  `last_modified` *was* the move record, rev-1 never asked where the move record
  lives. It lives in Asana stories, and this repo reads them through a published
  endpoint.
- **Leg 2 — "(a)/(e) cap at 30 days on an uncontracted schema."** **CONFIRMED and
  retained.** Independently re-verified at rev-2 (§4, §4.1.1, `query.py:548-560`).
- **Leg 3 — "decisively: the retrospective spine is `SectionInfo.watermark`, and
  reproducing it breaches this sprint's own K-lane fence."** **WITHDRAWN AS
  DECISIVE.** The watermark **is** `max(last_modified)` — derivable from the row
  payload with zero K-lane contact (§9.3, four receipts + a docstring +
  `ADR-007:1198-1200`). The fence exists (`shape:1501-1504`) but bars *"a number
  that **only exists** on the K-lane"* (`shape:1504`), which this number is not.
  **Rev-1 read a dependency-prohibition as an observable-prohibition.** The residue
  worth keeping is a different and narrower distinction, stated below.
- **Leg 3, restated at the right altitude (the part worth keeping):** the operative
  line is **standing dependency vs. one-off read**, and **module vs. value**.
  Consuming `SectionInfo` — importing it, reading the manifest, or reaching into
  `section_persistence.py`'s storage layout — is a K-lane dependency and is barred
  (that is why option (f) is disqualified). Computing `max(last_modified)` over
  declared columns you already receive is **not** a dependency on `SectionInfo`; it
  is an independent derivation of the same quantity. Rev-1's own §7.3 already
  implied this by retaining option (a) for a one-off retrospective — an internal
  inconsistency the critic correctly caught.
- **(c) cannot manufacture history.** Unchanged and true: a new emission starts
  emitting today.
- **(f) is disqualified on K-lane grounds** (§5f) and holds current state anyway.

**Therefore — the corrected cost conclusion**: Mission A is **not** shown to be
more expensive than framed on the retrospective half. Both reachable routes cost
**zero producer deploy** and sit inside S4's fence. What retrospective history
costs is **disclosure work and one open vendor question (UV-P-9)**, not a new
emission and not an uncontracted dependency. **This, not rev-1's negative result,
is the decision-grade input to GATE-FORK.**

### §7.3 What is NOT recommended, and why — stated so it cannot be re-proposed silently

| Option | Disposition | One-line reason |
|---|---|---|
| (a) Logs Insights | **REJECTED as source-of-record** | Uncontracted schema + externally-defaulted retention + caller-hostage coverage **and dimensionality** (`query.py:557-558` are request echoes) + K-lane-derived values |
| (c) new emission | **NOT NOW** | Requires a producer deploy; outside S4's fence and the §17 window. Revisit only if (b) proves insufficient in anger — **and rev-2 lowers the odds of that**, since (g) covers the retrospective half without one |
| (e) Loki | **REJECTED** | Same content as (a), plus a vendor boundary, plus a lossier delivery path, plus unknown retention |
| (f) S3 substrate | **REJECTED — hard** | Content coupling into a K-lane **module's** private storage layout — a dependency on the module, not on a value |
| **(g) section-timelines** | **NOT REJECTED — ENUMERATED, RECOMMENDED FOR THE RETROSPECTIVE HALF, CONDITIONED** | Already built, published, spec-gated, no retention dep, no K-lane contact, no producer deploy. **Adoption is conditional on**: UV-P-10 (story-cache coverage) answered, the two additive disclosure fields, and acceptance of the current-membership denominator (caveat 4). **It does NOT displace option (b)** for the forward series — it complements it |

Option (a) retains **one** legitimate role: a **one-off, human-run, explicitly-
labelled retrospective** — exactly what EVIDENCE-w1 was. That is not a
source-of-record and must not become one by habit. *(Rev-2: this carve-out is now
consistent with §7.2's restated leg 3 — the distinction is standing-dependency vs.
one-off read, and rev-1 stated the carve-out without stating the principle.)*

---

## §8 Contract statement for the recommended source

Required by exit criterion 3: *who owns it, what versions it, what breaks if it is
refactored.*

### §8.1 Who owns it

| Element | Owner (code location) |
|---|---|
| Column declarations (`section`, `last_modified`, `created`, `is_completed`) | asana service — `src/autom8_asana/dataframes/schemas/base.py:107` (`BASE_SCHEMA`) |
| Offer-specific columns | asana service — `src/autom8_asana/dataframes/schemas/offer.py` |
| Section → classification map | asana service — `src/autom8_asana/models/business/activity.py:181-230` (`OFFER_CLASSIFIER`, `project_gid="1143843662099250"`) |
| The `is_completed` terminal-override semantic | asana service — `src/autom8_asana/services/universal_strategy.py:510-513` (SD-6) |
| The rows route + response envelope | asana service — `src/autom8_asana/api/routes/query.py:84` (router), `:321` (route) |
| **Option (g)'s route + response model** *(rev-2)* | asana service — `src/autom8_asana/api/routes/section_timelines.py:75-82`; `src/autom8_asana/models/business/section_timeline.py:158-226`; service `src/autom8_asana/services/section_timeline_service.py` |
| Consumer-column contract registry | **`autom8-monolith`** (`declared_by`), vendored here at `dataframes/contracts/consumer_column_requirements.vendored.json:1-6` |

> **Named human owner: NOT RESOLVED from code.** Code ownership is unambiguous;
> the accountable person/team is not derivable from the repo. Operator surface (§13).

### §8.2 What versions it — honestly, and it is partial

| Mechanism | Covers | Armed? |
|---|---|---|
| `DataFrameSchema` / `ColumnDef` declarations | column name, dtype, nullability, source | **Yes** — but it is a declaration, not a gate |
| `docs/api-reference/openapi.json` + CI spec-check (`.github/workflows/test.yml:77-79`) | the query API contract | **NO for option (b)** — `query.py:84` sets `include_in_schema=False`; the rows route appears only as a non-schema annotation (`openapi.json:9689-9695`, `"in_schema": false`). **YES for option (g)** — path `:3859`, schemas `:1106` / `:1907` / `:2061` |
| `consumer_column_requirements.vendored.json` (`schema_version: 1`) | per-consumer `required_columns` with population expectations | **PARTIALLY** — its own note: *"the freshness guard runs in schema-only mode"* pending the monolith source binding (`:6`). No consumer is declared against `entity_type=offer` at all (`:8-24`) |
| `OFFER_CLASSIFIER` group membership | section-name → classification | **NO gate.** A section renamed **or newly added** on the Asana board silently falls out of / never enters its group |

**The honest summary: the recommended source is *better*-contracted than every
alternative and is *not yet fully* contracted.** Recommending it without saying so
would be the exact failure this sprint exists to prevent.

> **Rev-2 addendum, which is uncomfortable and belongs here.** On the versioning
> axis specifically, **option (g) is better contracted than the source this ADR
> recommends.** (g)'s route and response model are in the published schema and
> under the CI drift gate; (b)'s are not. That does not overturn §7.1 — (b) wins on
> coverage determinism, absence of a vendor hop, and absence of the silent
> story-cache degradation — but the asymmetry is real and rev-1 never surfaced it
> because rev-1 never enumerated (g). **Stated, not papered.**

### §8.3 What breaks if it is refactored — the enumerated blast radius *(recounted at rev-2)*

Rev-1 counted **4 silent : 3 loud**. That was wrong in both directions: it omitted
three modes and mis-binned one. The recount, with each mode classified and
receipted:

| # | Change | Effect on the readout | Detectable today? | Bin |
|---|---|---|---|---|
| 1 | `last_modified` renamed/removed (`base.py:76-81`) | **Total loss** of the time axis | Only via the FM-5 guard, which runs in **schema-only mode** (`consumer_column_requirements.vendored.json:6`) and lists **no offer consumer** (`:8-24`) → **not today** | **SILENT** |
| 2 | `section` extraction changed (`source=None`, "Extracted from memberships", `base.py:83-88`) | Silent misclassification of every row | **No** | **SILENT** |
| 3 | A section **renamed** on the Asana board | That section's offers silently drop out of their group — `classify()` returns `None` (`activity.py:66-74`) → UNKNOWN (`universal_strategy.py:521-524`) | **No** (see §8.5) | **SILENT** |
| 4 | A section **newly added** to the board *(NEW rev-2, critic F-5)* | **Every offer in it enters as UNKNOWN**; the readout's denominator shrinks with no signal. Distinct from #3: nothing was removed, so a rename-diff would not catch it | **No** at this layer. *(Note: option (g)'s path **does** log `unknown_section_in_timeline` with `section_name`/`story_gid`/`offer_gid` — `section_timeline_service.py:235-243`. That existing warning is the ready-made hook for §8.4 precondition 2)* | **SILENT** |
| 5 | `OFFER_CLASSIFIER` group membership edited (`activity.py:181-230`) | Cohort definitions shift under the readout with no version bump | **No** | **SILENT** |
| 6 | Classification semantic diverges — `is_completed` override applied on one surface, not the other *(NEW rev-2, critic F-4)* | Completed offers counted in their section's cohort by the readout while `universal_strategy.py:510-513` calls them INACTIVE | **No** | **SILENT** |
| 7 | An honest-empty 200 is rendered as an empty board *(NEW rev-2, critic F-10)* | Readout shows **zero offers**, indistinguishable from a genuinely empty board. The distinguishing signal exists (`api/metrics.py:130-135`; `meta.honest_empty`, `query/models.py:470-478`) but is a producer counter or a K-lane meta field — see §9.2 | **No**, unless the readout takes the §9.2 fork | **SILENT** |
| 8 | Rows response **envelope** changed | Parse failure — immediate | **Yes** | **LOUD** |
| 9 | Route path/prefix changed, or router hidden→visible | 404 | **Yes** | **LOUD** |
| 10 | K-lane K-2 adds 3 fields to `RowsMeta` *(NEW rev-2, critic F-7)* | A hand-rolled **strict** parser raises on the unknown keys (`RowsMeta` is `extra="forbid"`, `query/models.py:390`; K-lane adds +3 to both meta models, `ADR-007:1223`) | **Yes** — a `ValidationError` is loud, and the timing is **predictable** (it lands when K-2 lands) | **LOUD** |
| 11 | `project_gid` `"1143843662099250"` changes | Empty or wrong board | **Partially** (row-count collapse is visible; wrong-board is not) | **PARTIAL** |

**Recount: 7 silent : 3 loud : 1 partial.**

> **Rev-2 note against the critique.** The critic reached the same **7:3** by a
> different route, binning F-7 as *silent*. I bin it **loud** — a `ValidationError`
> raises, which is the same class as row 8, and rev-1's own table correctly called
> envelope changes "loud, not silent." The critic also left `project_gid` in the
> loud column, which rev-1 had already hedged as "Partially." Same ratio, corrected
> arithmetic. **Rev-1's own verdict — *"That asymmetry is the thing to fix before
> build, not after"* — is right and becomes more so: silent modes now outnumber
> loud ones better than two to one.**

### §8.4 The preconditions — binding on SA-1, not on this sprint

S4 is read-only; these are a **charge**, not work done here. **Rev-1 stated three;
rev-2 states six.**

1. **Register the readout as a named consumer** in
   `dataframes/contracts/consumer_column_requirements.vendored.json` with
   `required_columns: ["section", "last_modified", "created", "is_completed"]` and a
   stated `population_expectation` — or record in writing why not. This is the
   already-built, already-versioned mechanism; not using it is a choice that must
   be made explicitly. *(Note the vendored file's own instruction: "Do NOT edit by
   hand once the source binding lands" — the registration route may be the
   monolith-side source, which is a cross-repo question for SA-1.)*
2. **A drift test with two-sided teeth**: RED when any required column is absent
   from the frame **or** when `OFFER_CLASSIFIER` group membership changes without a
   corresponding readout-side acknowledgement; GREEN on the current shape. A
   deliberately-broken *input* the surface correctly rejects — never a defect
   injected into working production code. *(Rev-2: `unknown_section_in_timeline`,
   `section_timeline_service.py:235-243`, is an existing emission this test can
   assert against rather than inventing a new signal.)*
3. **A named human owner** recorded in the SA-1 ADR (§13).
4. **DECLARE WHICH CLASSIFICATION SEMANTIC THE READOUT IMPLEMENTS, and disclose
   the divergence** *(NEW rev-2, critic F-4)*. Two semantics are live:
   section-only (`query/engine.py:153-161`) and `is_completed`-terminal-override
   (`services/universal_strategy.py:510-513`). The readout must pick one, say which,
   and — if it picks section-only — disclose that completed offers will be counted
   in their section's cohort while other surfaces call them INACTIVE. **The cheap
   correct choice is to consume `is_completed` from the same payload
   (`base.py:54-59`) and match the service semantic**; that is a recommendation to
   SA-1, not a decision this seat makes.
5. **PARSE THE ROWS RESPONSE PERMISSIVELY — ignore unknown `meta` keys — or consume
   via the SDK** *(NEW rev-2, critic F-7)*. `RowsMeta` is `extra="forbid"`
   (`query/models.py:390`) and **actively growing**: `stale_served` was added by
   ADR-serve-stale-within-bound (`:428-444`) on top of the LKG freshness block
   (`:415-426`), and the K-lane adds **+3 fields to both meta models**
   (`ADR-007:1223`). A hand-rolled strict mirror of `RowsMeta` would break the week
   K-2 lands **without ever gating on a K-lane field**. The SDK path is safe —
   `QueryMeta` is `extra="ignore"` (`ADR-007:1224`) — and there is in-repo precedent
   for the permissive discipline: `query/models.py:468-469` records that
   *"the bridge reads meta by key and ignores unknowns (verified: bridge_response_to_df
   does not strict-reject extra meta keys)."* **Without this precondition, §9's
   attestation is true today and false the week K-2 lands.**
6. **REFUSE OR LABEL A ZERO-ROW READOUT — never render it as "the board is empty"**
   *(NEW rev-2, critic F-10)*. An honest-empty 200 is an attested empty response
   whose whole purpose is that it *"MUST be distinguished from a real-data 2xx so a
   liveness-masquerade (empty 2xx counted as a healthy serve) cannot read green at
   the gate"* (`api/metrics.py:130-135`). Option (g) has the same shape
   (`section_timeline_service.py:430-443` returns `[]` silently with no cache
   provider). This is the P-1/P-12 disclosure class §9.2 invokes.
   **⚠ This precondition is a FORK, not a free action — see §9.2.**

### §8.5 One residual coupling that cannot be contracted away — disclosed, not papered

`OFFER_CLASSIFIER` maps **section names as strings** (`"PENDING APPROVAL"`,
`"OPTIMIZE - Human Review"`, …, `activity.py:181-230`). The Asana board is
operator-editable, and `classify()` is a case-insensitive dict lookup returning
`None` on any miss (`activity.py:66-74`). **A human renaming a section silently
reclassifies every offer in it, in both the frame and any readout built on it —
and a human *adding* a section silently drops every offer in it into UNKNOWN,
shrinking the readout's denominator with no signal at all** *(rev-2 sharpening,
critic F-5)*. This is not introduced by option (b) — it is a standing property of
the board-as-substrate that options (a) and (g) share. It is named here so the
readout's disclosure text can carry it rather than discover it.

---

## §9 K-lane non-dependency attestation — EXPLICIT, per item

> **ATTESTATION.** The recommended source-of-record (§7.1) depends on **no**
> ADR-007 K-lane surface. Per item, with the anchor for each surface and the
> specific reason the dependency is absent:

| K-lane surface | Anchor | Depended on? | Basis |
|---|---|---|---|
| **`RowsMeta`** | `src/autom8_asana/query/models.py:387-398` | **NO** | The readout consumes the **row payload** (`section`, `last_modified`, `created`, `is_completed`), never the `meta` object. It **counts rows itself** rather than reading `meta.total_count` / `meta.returned_count`. **Subject to precondition 5 (§8.4)** — see §9.2 |
| **`AggregateMeta`** | `src/autom8_asana/query/models.py:225` | **NO** | The `/aggregate` endpoint (`query.py:565`) is not used. Aggregation happens consumer-side over rows. |
| **`SectionInfo`** | `src/autom8_asana/dataframes/section_persistence.py:83` | **NO** | The readout never reads the manifest and never consumes `SectionInfo.watermark`. It derives board position from the frame's own `section` column (`base.py:83-88`), extracted from task memberships, not from `SectionInfo`. **And where it wants the watermark *quantity*, it derives it independently — §9.3.** |
| **Freshness-meta reducer** | `src/autom8_asana/query/models.py:415-426`, `src/autom8_asana/query/engine.py` | **NO** | `meta.freshness`, `meta.data_age_seconds`, `meta.staleness_ratio`, `meta.stale_served` are **not read**. The readout does not gate on, branch on, or publish any freshness-meta field. |
| **Manifest write path** | `section_persistence.py:480` (`_save_manifest_async` def), `:549` (call site), S3 `dataframes/{project_gid}/manifest.json` | **NO** | No S3 read of the manifest; no consumption of `section_status_updated` (`:551-559`) — the emission that fires **inside** the manifest write path and publishes `manifest.completed_sections` / `manifest.total_sections` plus its call arguments (`:558`). |

**Option (g) carries the same attestation, independently**: it reads
`AsanaClient` stories and a `CacheProvider` and touches none of the five surfaces
(`section_timeline_service.py:422-443`, `:477-481`, `:495-496`).

### §9.1 The two negative attestations that make this non-trivial

An attestation that is only true because nothing was examined is worthless. Two
specific K-lane dependencies were **found in the rejected options** and are the
reason those options are rejected:

- **Option (a) consumes `RowsMeta` values.** `query.py:552-554` logs
  `result.meta.total_count`, `result.meta.returned_count`, `result.meta.query_ms`
  — `RowsMeta` fields at `query/models.py:392`, `:393`, `:398`. A consumer of
  `query_rows_complete` reads `RowsMeta` values through a log line.
- **Options (a) and (e) consume `SectionInfo` values.** Brief #1's watermark spine
  is `section_info.watermark` (`freshness.py:298-300`), a `SectionInfo` field —
  **read from the object**, which is different from deriving the same number
  independently (§9.3).

**Classification** — the distinction is load-bearing and is offered for
structure-evaluator's adjudication:

- **Contract dependency** — a consumer gates on a declared field of a versioned,
  fleet-visible contract. This is what ADR-007 §7.5 names the one-way door.
- **Derived-value dependency** — a consumer reads a value that *happens to be
  computed from* an internal object, through a surface with **no** contract, **no**
  version, and **no** consumer registry.
- **Independent derivation** *(NEW rev-2)* — a consumer computes the same
  *quantity* from data it is separately contracted to receive, never touching the
  internal object or the uncontracted surface. **This is not a dependency at all**,
  and conflating it with the first two is the error §9.3 corrects.

The second is **not safer than the first. It is the same coupling with every guard
removed.** The recommended option has neither.

### §9.2 Residuals — disclosed

**(i) Warm-state / freshness coupling** *(rev-1, unchanged).* Option (b) has **no
contract dependency** on the K-lane and **one indirect operational dependency**:
the frame it reads is built and refreshed by the same warming machinery that
maintains the section manifest. If warming degrades, the frame is stale and the
readout reads stale numbers. This is an availability/freshness coupling, not a
contract coupling; it is disclosable under the S1 disclosure rule (P-1
both-disclosed-separately, P-12 non-aliasing) and must not be collapsed into the
readout's headline figure. **Named, not papered.**

**(ii) The attestation is a consumer *discipline*, not a mechanism** *(rev-2,
critic F-7 — CONCEDED).* `RowsResponse` carries `meta: RowsMeta` alongside `data`
(`query/models.py:523`, `:554-557`); `AggregateResponse` likewise (`:265`).
Nothing in the surface **prevents** a consumer from reading `meta`. §9's force
depends on the readout keeping a rule. **I judge that acceptable on ADR-007's own
terms** — the one-way door triggers on *gating*: *"once any consumer **gates on**
`verification_age_seconds`, withdrawing the field is a breaking change to that
consumer"* (`ADR-007:1233-1236`) — receiving-then-ignoring creates no dependency.
But it should be stated as a discipline and not dressed as a mechanism.

**(iii) The reverse-direction hazard: strict parsing** *(rev-2, critic F-7).*
`RowsMeta` is `extra="forbid"` (`query/models.py:390`) and growing; the K-lane adds
+3 to both meta models (`ADR-007:1223`). **A hand-rolled strict parser breaks when
K-2 lands even without gating on anything.** That is a real coupling to the K-lane
and §9 names it here rather than omitting it. Mitigation: §8.4 precondition 5.

**(iv) THE HONEST-EMPTY FORK — a tension the critique did not name (rev-2, mine).**
Precondition 6 asks the readout to distinguish an attested honest-empty 200 from a
genuinely empty board. **The clean way to do that is to read `meta.honest_empty` —
and that field is a `RowsMeta` field, at `query/models.py:470-478`, whose own
comment records it is *"DERIVED from `SectionPersistence.get_manifest_async()` via
`is_honest_complete()`"* (`:466-467`).** So the tidiest satisfaction of
precondition 6 would acquire exactly the dependency §9 attests is absent. The fork,
stated and **not decided here**:

- **Branch A — refuse on zero rows, without explanation.** Zero K-lane contact;
  §9's attestation holds unqualified; the readout is coarser (it cannot tell the
  operator *why* it refused).
- **Branch B — read `meta.honest_empty`.** Informative and precise; **acquires a
  `RowsMeta` field dependency**, which is the surface `shape:1501-1503` names and
  `ADR-007:1223` marks as the one-way door. Note the door's trigger is *gating*, and
  branch B **does** gate (it branches on the field) — so this is the real thing, not
  a technicality.

**This is a genuine quality-attribute trade-off (disclosure precision vs. K-lane
non-dependency) and it belongs to structure-evaluator and the operator, not to
this seat** [AQ:SRC-003 Kazman et al. 2000] [STRONG]. Recorded because rev-1's §9
would otherwise read as if precondition 6 were free.

### §9.3 THE FENCE, CORRECTLY SOURCED AND CORRECTLY READ (rev-2)

**Rev-1 got the fence's provenance wrong, and then over-read it. Both are
corrected here. The critique got the second half right and the first half wrong;
both are receipted.**

**(a) Where the fence actually comes from.** Rev-1's frontmatter listed *"No
dependency on any ADR-007 K-lane surface"* under `fences:`. The critique argued
this was manufactured from an exit criterion (`shape:696`) and noted — **correctly,
and I verified it** — that the S4 sprint block (`shape:672-703`) **declares no
`fences:` key at all**; its only stated boundaries are `pr_boundary` (`:679`) and
`producer_deploy: false` (`:680`).

**But the fence is real.** It is declared at **initiative level**, in the shape's
§15.1 **PRESCRIBED — must follow** register, `shape:1501-1503`:

> *"**Zero K-lane dependency**: no touch on the offer-axis combiner, the
> freshness-meta reducer, `RowsMeta` / `AggregateMeta`, the manifest write path, or
> `SectionInfo`."*

corroborated by success criterion `shape:82` (*"Zero dependency acquired on the
ADR-007 K-lane meta contract"*) and failure signal `shape:88` (*"A sprint touches
the K-lane, or rides a K-lane PR"*). **The critique checked only the sprint block
and concluded no prohibition existed. That inference is wrong.** `shape:696` is
indeed an exit criterion (an obligation to *state*), but the prohibition it asks
the seat to attest to is separately and bindingly declared at `:1501-1503`.

**(b) What the fence actually bars — and this is the critique's point, on better
ground than the critique used.** The very next sentence of the same fence,
`shape:1504`, supplies the operative test:

> *"**If a readout wants a number that only exists on the K-lane, it WAITS.**"*

**A per-section `max(last_modified)` does not only exist on the K-lane.** It exists
on the row payload option (b) already receives. Four write-path receipts, each
verified own-hands in this dispatch, establish that `SectionInfo.watermark` **is**
that reduction:

| receipt | text |
|---|---|
| `dataframes/builders/freshness.py:536-540` | `new_watermark` ← `merged_df["last_modified"].max()` (delta-apply path) |
| `dataframes/builders/freshness.py:645-648` | `max_val = section_df["last_modified"].max()` (full re-fetch path) |
| `dataframes/builders/progressive.py:1729-1731` | `max_val = section_df["last_modified"].max()` (build path) |
| `dataframes/builders/progressive.py:676-681` | `_heal_null_watermark` — *"Derive a watermark for a null-watermark section from its cached parquet's `last_modified` column"*; `:680` `max_val = df["last_modified"].max()` |

**And the module rev-1 cites for `SectionInfo` says it in its own docstring** —
`dataframes/section_persistence.py:521`: `watermark: Max modified_at timestamp
(for complete status).`

**ADR-007 says the same thing about this class of value, in the section rev-1
read** (`:1198-1200`): *"The content axis shipped consumer-side with **zero**
producer work because `content_watermark_returned` is derivable from the returned
rows. **Verification recency is not consumer-derivable**…"* The K-lane is about
**verification** recency. The watermark is the **content** axis. ADR-007's own
blast-radius table classes `SectionInfo` / manifest JSON as **`+0 fields` …
two-way — semantics only** (`:1219`); the one-way door is `RowsMeta` /
`AggregateMeta` alone (`:1223`).

**(c) The correction, stated plainly.** Rev-1 imported the one-way-door gravity of
`RowsMeta` onto a field the K-lane does not change, and then read a
**dependency**-prohibition as an **observable**-prohibition. The fence bars
*depending on* `SectionInfo` — importing it, reading the manifest, reaching into
`section_persistence.py`'s storage layout (which is why option (f) is disqualified,
and that disqualification stands). It does not bar independently computing a
quantity from declared columns you already receive. **§9's five per-item
attestations are unaffected and stand; the inference rev-1 drew from them in §7.2
does not.**

---

## §10 The NF-2 hazard, named as exit criterion 5 requires

> **CloudWatch Logs Insights over `query_rows_complete` (`src/autom8_asana/api/routes/query.py:549`)
> is an UNCONTRACTED surface. Building a recurring, team-facing readout on it
> acquires exactly the dependency class ADR-007 §7.5 fences against for the K-lane
> — one layer down, and on a surface with strictly weaker guarantees.**

ADR-007 §7.5 (`:1233-1236`) names the mechanism:

> *"once any consumer gates on `verification_age_seconds`, withdrawing the field is
> a breaking change to that consumer. The public meta contract is fleet-visible,
> and this crusade's whole history is of consumers acquiring dependencies on fields
> whose meaning nobody re-checked."*

The symmetry, with the asymmetry made explicit:

| | ADR-007 K-lane (`RowsMeta`) | `query_rows_complete` |
|---|---|---|
| Declared contract | **Yes** — Pydantic model, `extra="forbid"` (`query/models.py:390`) | **No** — a `logger.info` `extra` dict |
| Fleet-visible | **Yes** | No — invisible until someone greps a log |
| Versioned | Partially | **Not at all** |
| Breaks loudly on change | Sometimes | **Never** — a renamed field yields an empty result set, not an error |
| Retention-bounded | No | **Yes — 30 days, externally defaulted (§4)** |
| Coverage design | Complete per response | **Hostage to caller traffic** |
| Dimensionality *(rev-2)* | Properties of the response | **Request echoes** — `section` / `classification` are `request_body.*` (`query.py:557-558`), mutually exclusive (`query/models.py:379-384`) |

ADR-007 §7.5 asks for the one-way door to be **acknowledged explicitly rather than
absorbed**. The same standard is applied here and the answer is: **do not walk
through the lower door either.** The recommendation in §7.1 exists to avoid it.

*(Rev-2: the critic re-read `ADR-007:1228-1239` and every row of this table
independently and found it defensible. It is preserved unchanged, with one row
added.)*

---

## §11 Negative-result accounting — RE-DERIVED AT REV-2

Per the mission, a negative result is first-class. **Rev-1's accounting is
superseded. The prior GATE-FORK sentence was a false biconditional and is
withdrawn in full.**

| Question | Result (rev-2) |
|---|---|
| Contractable source for the **recurring forward-looking** readout? | **YES** — option (b), with §8.4's six preconditions |
| Contractable source for **retrospective 14-day history**? | **YES, CONDITIONALLY** — option (g), already deployed and in the published contract, subject to §5(g)'s four caveats and UV-P-9/UV-P-10. **Rev-1 answered NO** |
| Contractable **log-derived** retrospective source? | **NO** — this is what survives of the negative result, and it is the whole of NF-2's original hazard |
| Is Mission A more expensive than framed? | **NOT SHOWN TO BE.** Both retrospective routes cost **zero producer deploy** and sit inside S4's fence. The cost of retrospective history is **disclosure work plus one open vendor question**, not a new emission and not an uncontracted dependency |
| Does any option require a producer deploy? | Only (c). Neither (b) nor (g) does |
| Does the recommendation collide with the shape §17 window fence? | **No** — read-only consumers, no producer deploy |

### §11.1 GATE-FORK input — the corrected statement

> **WITHDRAWN (rev-1):** *"Mission A is buildable as framed **if and only if** the
> operator rules that its readout may start its history at first run; otherwise
> Mission A acquires either a 30-day-capped uncontracted K-lane-derived dependency,
> or a new-emission cost the frame did not budget."*
>
> **That biconditional is FALSE.** It presented a two-branch choice where three
> branches exist, and it excluded the branch that is already paid for. **Had it
> reached the operator unrevised, it would have foreclosed a real capability on a
> live, date-bounded, operator-reserved decision.**

**The corrected input:**

> **The retrospective half is REACHABLE. Three paths exist, not two.**
>
> 1. **Begin the series at first run under option (b)** — **zero additional cost**,
>    and it reproduces brief #1's per-section spine *going forward*, because that
>    spine — `SectionInfo.watermark` — **is** `max(last_modified)` over the
>    section's rows (`freshness.py:536-540`, `:645-648`; `progressive.py:680`,
>    `:1729-1731`; docstring `section_persistence.py:521`), a reduction over
>    declared columns the recommended source already returns. **Zero K-lane
>    contact** (§9.3).
> 2. **Consume `GET /api/v1/offers/section-timelines`** (option (g)) for historical
>    per-offer classification occupancy over an arbitrary past window — **already
>    built, already mounted (`api/main.py:488`), already in the published contract
>    (`openapi.json:3859`), no producer deploy, no CloudWatch retention dependency,
>    no K-lane contact**, and **better contracted than the source this ADR
>    recommends** (in-schema and spec-gated, where option (b)'s route is
>    `include_in_schema=False`). **Conditional on**: two additive disclosure fields
>    (`cache_hits` / `cache_misses`), the day-sweep reconstruction for per-day
>    occupancy, acceptance of a current-membership denominator, and the two open
>    questions UV-P-9 (Asana story retention) and UV-P-10 (story-cache coverage).
> 3. **The 30-day-capped, uncontracted log mine** (options (a)/(e)) — still
>    correctly **REJECTED** as a source-of-record.
>
> **Mission A is NOT shown to be more expensive than framed on the retrospective
> half.** What the operator is choosing between has changed: the fork is no longer
> *"history, or no history"* — it is *"which already-paid-for retrospective
> surface, at what disclosure cost, with which open vendor question accepted."*
>
> **The fork itself is operator-reserved, free until 2026-08-18, and is NOT decided
> here.** Option (g) changes what is being chosen between; that is precisely why it
> must reach the operator **accurately and unresolved**.

---

## §12 UV-P register

**CLOSED by this sprint:**

- **UV-P-5** — *asana service CloudWatch log retention*. **CLOSED**, §4.
  Value **30 days**. Owner: `autom8y/a8` module default at pin `0fb9527b`
  (`stacks/service-stateless/variables.tf:422-426` →
  `primitives/ecs-fargate-service/main.tf:111-113`), consumed at
  `autom8y@origin/main:terraform/services/asana/main.tf:101` **without declaration**.
  Live-corroborated at `retentionInDays: 30`, three readings. The shape's stated
  reason for the UV-P is **falsified** (§2 FP-S4-1); the UV-P itself was real for a
  different reason. *(Rev-2: the terraform chain re-verified at a later
  `origin/main`; the `storedBytes` corroboration argument downgraded — §4.0.)*

**DISCHARGED at rev-2 — the two enumeration questions S1 routed to this sprint:**

Rev-1 answered neither and did not acknowledge that they had been routed. Both are
answered now, with the honest narrowing each requires:

- **`PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12.md:797`** —
  *"whether any per-section or per-offer observation series can be reconstructed
  from an existing emission | METHOD: deferred-to-S4-source-of-record"*.
  **DISCHARGED — YES, with a narrowing.** A per-offer observation series **can** be
  reconstructed from an **existing published endpoint** — option (g),
  `openapi.json:3859` — which replays `section_changed` stories over an arbitrary
  window (`section_timeline_service.py:245-267`). **NO** if "emission" is read
  strictly as *log emission*: the only per-section series in the log stream is the
  `modified_since=` watermark line, which is 30-day-capped and uncontracted (§5a).
  The narrowing is stated because the UV-P said "emission" and the answer is an
  endpoint.
- **`PREDICATE…:798`** — *"whether mean dwell is derivable from cohort counts via a
  queueing identity | REASON: the identity needs gross transition flow, and counts
  yield only net change; feasibility unassessed"*. **DISCHARGED BY OBVIATION,
  CONDITIONALLY.** The queueing identity is **not needed**: **gross transition flow
  is exactly what Asana `section_changed` stories carry**, with real `entered_at` /
  `exited_at` per interval (`section_timeline_service.py:245-267`;
  `models/business/section_timeline.py:21-40`). Dwell can be **measured**, not
  inferred from net change. **The condition**: the raw `SectionInterval` list is
  **not returned** over the wire (`OfferTimelineEntry`, `section_timeline.py:158-226`,
  `extra="forbid"` at `:212`), so dwell is available *in-process* today and requires
  an **additive field on an already-published model** to reach a consumer. That is
  §5(g) caveat 1.

> **Provenance correction, on the record.** Rev-1 presented the caller-hostage
> coverage finding as its own (*"⚠ Coverage dependency the shape did not name"*)
> when S1 had **derived it and routed it to S4 by name** (`PREDICATE…:619-624`).
> The substance was true — I re-verified it at `query.py:557-558` — but **one
> reading was counted twice**, which is what made an inherited chain look like
> independent corroboration, and the two questions routed alongside it went
> undischarged for a full revision. §5(a) now credits it. *(Line numbers: the
> critique cited `:338-343` / `:516-518`; that artifact was revised at 22:56, after
> the critique's read, and the same text now sits at `:619-624` / `:797-799`. Not a
> critic error — a moving substrate. **Class lesson: a citation into a live sibling
> artifact decays; anchor by quoted text as well as by line.**)*

**RETIRED at rev-2:**

- **UV-P-6** *(Grafana Cloud Loki retention)* — **RETIRED as non-load-bearing.**
  Option (e) is rejected on independent grounds, and rev-2 opens two UV-Ps that
  **are** load-bearing on a **recommended** option, which UV-P-6 never was on a
  rejected one. Recorded so a future reader does not assume Loki is a
  longer-retention archive.

**OPEN, carried per Gate-C DEFER-tag pattern:**

```
[UV-P-7: named human/team owner of BASE_SCHEMA + OFFER_CLASSIFIER + the rows route
+ the section-timelines route | METHOD: deferred-to-operator | REASON: code
ownership is unambiguous (§8.1) but the accountable party is not derivable from the
repo; exit criterion 3's "who owns it" is answered at code altitude and OPEN at
human altitude]
```

```
[UV-P-8: dollar cost of a scheduled Logs Insights query over a 14-day window on a
~1.55 GB group | METHOD: deferred — AWS pricing probe not run under this sprint's
read-only-and-minimal fence | REASON: option (a) is REJECTED on contract grounds
that hold at any price; the figure is not load-bearing. Stated qualitatively only:
scan cost is proportional to bytes scanned]
```

**OPENED at rev-2 — and unlike UV-P-6, these ARE load-bearing, because they bound
a RECOMMENDED option:**

```
[UV-P-9: Asana's own retention of `section_changed` stories — whether they persist
beyond any vendor window | METHOD: deferred-to-vendor-documentation-or-live-probe |
REASON: option (g)'s retrospective DEPTH is bounded by this, and it is a vendor
property not resolvable from any of the three repos. Load-bearing: (g) is
recommended for the retrospective half, not rejected]
```

```
[UV-P-10: option (g)'s real story-cache hit rate on the offers board | METHOD:
a Logs Insights query on `story_cache_gap_above_threshold` /
`inline_story_fetch_complete` / `timeline_computed_on_demand`
(`section_timeline_service.py:522-541`, `:656-661`) | REASON: caveat 3 (§5g) is a
footnote if the hit rate is high and a disqualifier if it is low. NOT probed under
this sprint's minimal-AWS fence. This is the single most important open question on
option (g) and it is cheaply answerable — the emissions already exist]
```

```
[UV-P-11: whether `last_modified` is non-null IN PRACTICE, not merely declared |
METHOD: a null-count over the live offers frame, or a probe of
`coerce_rows_to_schema` enforcement | REASON: `nullable=False` at `base.py:79` is a
ColumnDef DECLARATION; I found no runtime gate that fails a build on a null, and
the write paths defend against nulls (`freshness.py:539`, `progressive.py:678`).
The existence of `_heal_null_watermark` (`progressive.py:657-681`) shows the
codebase treats absent watermarks as a live condition. Rev-1 asserted
non-nullability from the declaration without probing; NEITHER rev-1, rev-2, NOR the
critic has probed it. A probe not run, honestly labelled]
```

**INHERITED, untouched** (per shape §14.3): UV-P-1, UV-P-2, UV-P-4 remain live and
are not this sprint's to resolve. UV-P-3 remains DISCHARGED.

---

## §13 Operator surface — what does NOT belong to any agent

1. **THE SCOPE RULING (blocking on GATE-FORK) — RESTATED AT REV-2.** Rev-1 put the
   question as *"Must Mission A's readout include retrospective history?"* with a
   YES branch that reopened Mission A's cost estimate. **That framing is
   withdrawn.** The corrected question is:

   > *Given that retrospective history is reachable at zero producer cost by two
   > distinct routes, which route should Mission A take — option (b)'s series run
   > forward, option (g)'s Asana-story replay, or both — and is the operator
   > willing to accept option (g)'s current-membership denominator and its open
   > vendor question (UV-P-9) in exchange for immediate history?*

   **No agent should infer this.** The fork is operator-reserved and free until
   **2026-08-18**. Option (g) does not decide the fork; it **changes what the fork
   is between**, which is why it is surfaced unresolved.
2. **The cross-repo retention coupling (§4.1) is bigger than Mission A — and rev-2
   strengthens it.** The asana ECS log group's retention is undeclared in either
   repo while all ten sibling Lambda groups declare it explicitly; the effective pin
   at `origin/main:main.tf:101` (`0fb9527b`) is **named in no comment in the file**,
   while the twelve lines of prose written to document the bump chain terminate at a
   different value (`80402fd3`, `:96`/`:99`) — which is also the value the divergent
   branch carries at the same line. Whether to (i) declare `log_retention_days` on
   `module "service"` in `autom8y:terraform/services/asana/main.tf`, and/or (ii) add
   a **retention-delta check to the a8 `ref=` bump procedure**, is an **SRE-lane
   infra decision outside this sprint's read-only fence.** It affects every future
   log-derived readout, not just this one. **Recommended for routing, not decided
   here.** *(The critic, holding no SRE authority, observed that (ii) is the remedy
   that generalises because (i) fixes this group while leaving the mechanism intact.
   Recorded as an observation, not adopted as a recommendation by this seat.)*
3. **Named owner for the §8 contract** (UV-P-7).
4. **The §8.4 preconditions are a charge on SA-1** — **now six, not three** —
   requiring code changes S4 may not make. If SA-1 proceeds without them, that is a
   deliberate acceptance to be recorded, not a silent omission. **Precondition 6
   carries a fork with a K-lane consequence (§9.2 item iv) that is itself an
   operator/structure-evaluator call.**
5. **arch-adversary has not run.** Exit criterion 5 of the sprint block
   ("arch-adversary verdict returned and dispositioned") is **OPEN** — subagents
   cannot dispatch subagents. Dispatch belongs to the main thread. **This ADR is
   `status: draft` and is not exit-complete until that verdict is returned and
   dispositioned.** *(Rev-2 note: a rite-disjoint eunomia `entropy-assessor`
   critique HAS now run and returned BLOCK; this revision remediates it. That
   critique is **not** the arch-adversary verdict the exit criterion names, and
   this seat does not clear its own BLOCK.)*
6. **UV-P-9 and UV-P-10** are the two questions that decide how much of option (g)
   is real. UV-P-10 is answerable with one Logs Insights query against emissions
   that already exist.

---

## §14 SVR ledger

Structural-verification receipts for the load-bearing platform-behaviour claims.
Design-choice / estimative rows correctly carry **no** receipt.

> **Rev-2: all eight rev-1 receipts re-verified; four re-anchored for line
> precision (critic F-12); two new receipts added for option (g) and the watermark
> derivation; one claim's grade lowered by my own probe (§4.0).**

**SVR-1** — `terraform/services/asana/` exists at autom8y origin/main
```yaml
verification_method: git-ls-files
verification_anchor:
  source: "git -C .../autom8y ls-tree --name-only origin/main terraform/services/asana/"
  path_or_glob: "terraform/services/asana/"
  result: matched-N-files
  result_count: 17
  claim: "the shape's stated reason for UV-P-5 — that this directory is absent at
    origin/main — is falsified by a present-tense tree probe; the UV-P was real for
    a different reason, namely that retention is declared nowhere inside it"
```

**SVR-2** — live retention of the asana ECS log group *(re-run at rev-2)*
```yaml
verification_method: bash-probe
verification_anchor:
  source: "aws logs describe-log-groups --log-group-name-prefix /ecs/autom8y-asana-service"
  command_output_verbatim: '{"name": "/ecs/autom8y-asana-service", "retentionInDays": 30, "storedBytes": 1554135548}'
  exit_code: 0
  claim: "the effective retention against which a 14-day lookback must fit is 30
    days, read directly from the live control plane rather than inferred from the
    terraform chain, which is what makes the chain's conclusion falsifiable rather
    than merely internally consistent"
```

**SVR-2b** *(NEW rev-2)* — the log group is actively written, which downgrades rev-1's `storedBytes` corroboration argument
```yaml
verification_method: bash-probe
verification_anchor:
  source: "aws logs describe-log-streams --log-group-name /ecs/autom8y-asana-service --order-by LastEventTime --descending --max-items 3"
  command_output_verbatim: '{"stream": "ecs/autom8y-asana-service/bf72abaad0b34aa086341ea839d4a0cc", "last": 1786567110377}'
  exit_code: 0
  claim: "the most recent event predates the probe by roughly twenty-one minutes, so
    a storedBytes figure identical across three readings eleven days apart cannot be
    three converging live measurements; the field is cached or slowly refreshed, and
    rev-1's inference that the agreement independently corroborates the reading is
    withdrawn — only same-group identity is established"
```

**SVR-3** — the retention default lives in a third repo at a pinned ref
```yaml
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/a8 @ 0fb9527b : terraform/modules/stacks/service-stateless/variables.tf"
  line_range: "L422-L426"
  marker_token: 'description = "CloudWatch log retention in days"'
  claim: "the value governing the asana ECS log group originates outside both the
    consuming repo and the monorepo, as an unoverridden module default reachable
    only through a pinned git ref, making it mutable without any diff in either repo"
```

**SVR-3b** *(NEW rev-2)* — the effective pin is documented nowhere in the file that carries it
```yaml
verification_method: bash-probe
verification_anchor:
  source: "git -C .../autom8y show origin/main:terraform/services/asana/main.tf | grep -c '0fb9527b'"
  command_output_verbatim: "1"
  exit_code: 0
  claim: "the single occurrence of the effective ref is the source= assignment itself,
    so the twelve-line comment block written specifically to record the bump chain
    terminates at a different value than the pin it sits above — the coupling named
    in section 4.1 is demonstrating itself in its own source file, with the prose
    record already out of sync"
```

**SVR-4** — the rows route is excluded from the published schema
```yaml
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/api/routes/query.py"
  line_range: "L83-L84"
  marker_token: 'router = s2s_router(prefix="/v1/query", tags=["query"], include_in_schema=False)'
  claim: "option (b)'s consumption surface is not covered by the CI OpenAPI drift
    check, which is why §8.4 makes FM-5 consumer registration a precondition rather
    than relying on the spec gate that appears to exist"
```

**SVR-5** — the board-behaviour observables are declared columns *(re-anchored rev-2)*
```yaml
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/dataframes/schemas/base.py"
  line_range: "L76-L81"
  marker_token: 'source="modified_at",'
  claim: "the column rev-1 described as time-since-last-MOVE is declared against
    Asana's modification timestamp and therefore advances on any edit, which both
    corrects the observable's description and removes the reasoning that led rev-1
    to stop searching for where section movement is actually recorded"
```

**SVR-6** — a second live copy of the same events exists outside CloudWatch
```yaml
verification_method: bash-probe
verification_anchor:
  source: "aws logs describe-subscription-filters --log-group-name /ecs/autom8y-asana-service"
  command_output_verbatim: '{"name": "loki-forwarder-asana", "pattern": "", "dest": "arn:aws:lambda:us-east-1:696318035277:function:autom8y-cw-loki-forwarder-production"}'
  exit_code: 0
  claim: "an option absent from the charge's enumeration is live in production; the
    empty filter pattern establishes that every event is forwarded, not a subset,
    which is why option (e) had to be enumerated and explicitly rejected rather than
    omitted"
```

**SVR-7** — the rejected option consumes K-lane values *(re-anchored rev-2)*
```yaml
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/api/routes/query.py"
  line_range: "L552-L558"
  marker_token: '"section": request_body.section,'
  claim: "the emission's counts are read off the RowsMeta object while its two
    dimensional fields are echoes of the caller's own request body, so a consumer of
    this log line acquires both a derived-value dependency on a K-lane surface and a
    denominator whose shape is authored by whoever happened to call"
```

**SVR-8** — the retrospective spine's value is `max(last_modified)`, not a `SectionInfo`-only quantity *(REPLACES rev-1's SVR-8, whose claim is withdrawn)*
```yaml
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/dataframes/section_persistence.py"
  line_range: "L521"
  marker_token: 'watermark: Max modified_at timestamp (for complete status).'
  claim: "the module that defines SectionInfo documents its watermark as the maximum
    of a column the rows payload already returns, which is why reproducing brief #1's
    per-section spine forward is an independent derivation rather than a dependency
    on the K-lane object, and why rev-1's decisive third leg is withdrawn"
```

**SVR-9** *(NEW rev-2)* — a seventh option exists, published and mounted
```yaml
verification_method: bash-probe
verification_anchor:
  source: "grep -n 'section-timelines' docs/api-reference/openapi.json"
  command_output_verbatim: '3859:    "/api/v1/offers/section-timelines": {'
  exit_code: 0
  claim: "the option space rev-1 self-attested complete at six omitted a path object
    present in the very contract artifact rev-1 queried for SVR-4, which falsifies
    exit criterion 1's MET stamp and is the finding that moved the negative result"
```

**SVR-10** *(NEW rev-2)* — the seventh option replays section history over a caller-specified past window
```yaml
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/api/routes/section_timelines.py"
  line_range: "L100-L106"
  marker_token: 'replaying its Asana section history within the specified'
  claim: "the retrospective capability rev-1 declared unavailable at any acceptable
    cost is the documented purpose of a route that is already mounted and already in
    the published contract, so the cost of retrospective history is disclosure work
    rather than a producer deploy"
```

**Non-SVR rows** (correctly unreceipted — trigger table rows 5/6):
the §7 recommendation is a **design choice**; §8.4's six preconditions are
**forward-looking**; §11's cost conclusion is **conditional on an operator ruling**;
§13's routing recommendations are **design choices in another lane**.

---

## §15 Evidence grade

**MODERATE — self-attestation ceiling, per the sprint's binding fence.**

| Dimension | Grade (rev-1) | Grade (rev-2) | Basis |
|---|---|---|---|
| UV-P-5 resolution (§4) | STRONG | **STRONG** (held, on narrowed grounds) | Four-hop terraform chain **re-verified at a second, later `origin/main`** plus an independent live AWS probe. **Two** disjoint methods, not three — rev-1's third (`storedBytes` byte-agreement) is withdrawn as uninformative (§4.0). The grade holds because the two surviving methods are independently sufficient |
| §4.1 cross-repo retention coupling | *(not separately graded)* | **STRONG** | Ten sibling sites at exact line numbers; zero in-block matches; effective pin absent from all prose in its own file (`grep -c` = 1); divergent-branch value differs at the same line. Four independent structural facts |
| Option-space completeness (§5) | MODERATE | **WEAK at rev-1 (falsified); MODERATE at rev-2** | Rev-1's six were **proven incomplete** by a rite-disjoint critic. Rev-2's seven include one found only by external challenge. **An eighth is not proven absent** — and rev-1's identical hedge turned out to be the correct instinct, under-weighted. I decline to grade this above MODERATE for exactly that reason |
| K-lane attestation (§9) | MODERATE-to-STRONG | **MODERATE-to-STRONG** (held) | Per-item, with anchors, made falsifiable by §9.1's two *positive* findings in the rejected options, and **independently re-traced by the critic across all five surfaces with none found**. Held down from STRONG by §9.2: it is a consumer discipline, not a mechanism, and item (iv)'s honest-empty fork can convert it into a real dependency |
| Recommendation (§7.1) | MODERATE | **MODERATE** (held, strengthened) | Sound on structural grounds; **not** validated in anger. No readout has been built against option (b). Strengthened by surviving a rite-disjoint attack on all six grounds, and by ground 7 (§7.1) |
| Negative result (§7.2) | **STRONG on the mechanism** | **WITHDRAWN as stated; WEAK-to-MODERATE as narrowed** | Rev-1's three grounds were declared *"each independently sufficient"*: one is **refuted** (leg 3, §9.3), one rested on a **misdescribed observable** (leg 1's premise, §3.1), and the **class conclusion is refuted** by option (g). What survives — no *log-derived* retrospective source is contractable — is **MODERATE**, resting on the verified retention chain and the uncontracted emission. The **scope** claim ("at any acceptable cost") is withdrawn outright |
| Option (g) structural claims (§5g) | — | **MODERATE** | Route, mount, schema publication, service internals and classifier identity all verified own-hands. **Code-and-contract attested, NOT live-attested**: I made no HTTP request, did not measure story-cache coverage (UV-P-10), and cannot verify Asana story retention (UV-P-9) |
| §11 GATE-FORK input | *(implicitly STRONG)* | **MODERATE** | The three-path structure is receipted; the *relative cost* of path 2 depends on two open UV-Ps. Deliberately graded no higher, because this is the sentence the operator consumes |

**Ceiling holds regardless**: a rite-disjoint **arch-adversary** has not run. A
rite-disjoint eunomia critique HAS run and returned **BLOCK**; this revision
remediates it and **does not clear it** — that is not this seat's to do. Nothing
here should be consumed as certified. **This is a `draft`.**

---

## §16 Handoff criteria — self-audit against the sprint's exit criteria

| # | Exit criterion | rev-1 | rev-2 |
|---|---|---|---|
| 1 | Options enumerated before recommendation | **MET** *(self-attested — and WRONG)* | **NOT MET at rev-1 → MET at rev-2.** Rev-1 enumerated six and asserted completeness; a seventh existed in the contract artifact rev-1 had open. Rev-2 enumerates **seven**, dispositions each, and records the enumeration-method failure that caused the miss (§5 preamble). **An eighth is not proven absent** — §15 |
| 2 | UV-P-5 closed or carried | MET — CLOSED | **MET — CLOSED**, §4; re-verified at a second `origin/main`; stated reason falsified and surfaced, §2 |
| 3 | Contract statement (owner / versioning / refactor blast radius) | MET at code altitude | **MET at code altitude**, §8; human owner carried as UV-P-7; §8.3 recounted; §8.2 now discloses that option (g) is better-versioned than the recommended source |
| 4 | Explicit K-lane non-dependency attestation | MET | **MET**, §9 — per item, five surfaces, two counter-findings, **independently re-traced by the critic with none found**; §9.2 adds three residuals rev-1 omitted; §9.3 corrects the fence's provenance and its over-reading |
| 5 | NF-2 hazard named | MET | **MET** — §10, preserved, one row added |
| 6 | arch-adversary verdict returned and dispositioned | OPEN | **OPEN** — §13 item 5; not dispatchable from this seat. A eunomia BLOCK has been dispositioned here; that is a different critic and does not satisfy this criterion |
| — | Read-only fence honoured | MET | **MET** — zero writes outside `.ledge/`; **zero git operations** (no add/commit/branch/checkout/stash/push); AWS calls **read-only only**: rev-1 `sts get-caller-identity` ×1, `logs describe-log-groups` ×1, `logs describe-subscription-filters` ×1; rev-2 `logs describe-log-groups` ×1, `logs describe-log-streams` ×1. **No** `start-query`, **no** Lambda invoke, **no** S3 object read, **no** request to the asana serve path, **no** Asana API call |
| — | autom8y read at `origin/main` only (ADR-007 §8 O-11) | MET | **MET, and independently corroborated.** Every autom8y fact read via `git show/grep/ls-tree origin/main:`. The **only** working-tree-adjacent read in rev-2 was an explicit `git show HEAD:…` used **to demonstrate the divergence** (§4.1.1) and labelled as the divergent branch at every mention. The critic corroborated rev-1's compliance by the one datum that differs: rev-1 reported `ref=0fb9527b`, a value that **does not appear anywhere in the trap surface** — §4.1.1 |
