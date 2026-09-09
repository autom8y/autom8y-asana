---
title: "REGISTRY OF RECORD — name-the-client carried gates: owner · trigger · watcher"
type: decision
slug: REGISTRY-name-the-client-carried-gates
date: 2026-09-08
initiative: name-the-client
wave: 0
sprint: S-02 (WS-CARGO)
rite: eunomia
seat: verification-auditor (holding BOTH verification-auditor AND entropy-assessor roles)
deploy_class: C-INERT
status: accepted
content_status: measured-ground-truth
discharges: [C-9, C-12]
self_assessment_ceiling: MODERATE   # self-ref-evidence-grade-rule
aws_account: "696318…277 — 12-digit run withheld per merge-surface-sweep"
aws_region: us-east-1
substrate_at_authorship:
  autom8y_origin_main: 883eb3bf
  asana_origin_main: 389c59bc
  asana_local_HEAD: d75bfe1a   # BEHIND origin/main by 1 commit
skills:
  - "@structural-verification-receipt"
  - "@telos-integrity-ref"
  - "@defer-watch-manifest"
---

# REGISTRY OF RECORD — carried gates for `name-the-client`

**This is a registry of record, not a status board.** Every row carries **owner · trigger ·
watcher**. Where no watcher exists, the literal string **`NO WATCHER`** is written. **Inventing a
watcher is forbidden (C-12)** — a fabricated watcher is worse than an empty cell, because an empty
cell can be seen and a fabricated one cannot.

This artifact discharges **C-9** (name a holder for the inherited cargo) and **C-12** (inscribe the
carried gate registry). It advances **none** of clauses (a)–(d) of the realization predicate. It is
**custodial only** and must never be reported as progress toward the bar.

> **REALIZATION PREDICATE — VERBATIM, carried per C-7:** *"Verified-realized" = the operator's
> ratified receipt, carried VERBATIM into every sprint's exit criteria: a LIVE attributed booking
> naming that office, TWO-SIDED — a failure for the SAME office also names it, with its kind, never
> blank — held across the C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS
> A BAR, NOT A DATE.*

---

## §0 WHY ONE SEAT HOLDS BOTH ROLES — and why that is the point

The shape assigns S-02 to `verification-auditor` **and** `entropy-assessor`. `entropy-assessor`
carries `tools: Read, Write, Glob, Grep` — **no Bash**. It cannot run `gh`, `git`, `aws`, or any
live probe. Agents cannot spawn agents, and a sequential pairing does not fit a parallel wave.

**One seat therefore holds both roles: it ran every live probe AND authored this registry.**

This is deliberate and it is load-bearing. Handing the live re-verification to a Bash-less seat
would have produced **an unverifiable registry that looked complete** — a document whose every cell
was filled and whose every cell was inherited. That is precisely the failure class this initiative
is named for, and it is **face 7 of the observer law: a decision with no watcher.** A registry of
unwatched gates, itself unverified, would be the law's own counterexample.

**Method.** Every row below is marked with how it was obtained:
**`[OWN-HANDS]`** — this seat ran the probe and read the result.
**`[CITED]`** — read from a git-persistent artifact at an explicit ref; the artifact is named.
**`[ATTRIBUTED]`** — supplied by another session; source named; **not this seat's measurement**.
**`[UNVERIFIED]` / `[OPEN]` / `[UNSEARCHED]`** — not established. Never filled with plausible text.

**The four fences were applied, and one of them fired on this seat mid-run** (§6.6).

---

## §1 SUBSTRATE — re-resolved at this seat's start, and it moved twice DURING the run

**`[OWN-HANDS]`** Fence 2 (stale-tree trap) requires re-resolution at each seat's own start.

| repo | reading | note |
|---|---|---|
| `autom8y` `origin/main` @ 20:44Z | `e292b616` | **NOT `a4bc0e39`** as the charge stated — already +1 |
| `autom8y` `origin/main` @ 20:48Z | **`883eb3bf`** | moved **again, during this run** |
| `autom8y` local checkout | `fix/wss-wildcard-scope-bypass-closure` @ `29e59e81`, **352** dirty files | stale-tree trap ACTIVE; every read below used explicit refs |
| `autom8y-asana` `origin/main` | `389c59bc` | matches the charge |
| `autom8y-asana` local `HEAD` | `d75bfe1a` — **an ANCESTOR of `origin/main`** | **the working tree is BEHIND by one commit** (`389c59bc`), not ahead |

**Label-move count: six this arc** — `cc88b75e → 57e21107 → b2b4ae98 → a4bc0e39 → e292b616 → 883eb3bf`.
Two of those six happened inside this single sprint. **Cite no label; re-resolve at every seat.**

> **REGISTRY ROW — substrate label drift.** Owner: every seat. Trigger: any citation of `origin/main`.
> Watcher: **`NO WATCHER`** — nothing notifies a seat that the label it cited has moved. The only
> defence in service is fence 2, which is a discipline, not a mechanism.

---

## §2 HARD GATE 1 — #1941's head, re-verified LIVE. **FROZEN.**

**`[OWN-HANDS]`, 2026-09-08T20:44:54Z.** Inheritance was **not** assumed; the charge's reading was
**not** carried.

```
gh pr view 1941 →  state OPEN, isDraft false
                   headRefOid  b9bbfadc
                   baseRefName integration/name-the-zero
                   mergeable MERGEABLE   mergeStateStatus CLEAN
                   updatedAt 2026-09-05T14:51:37Z   33 files, +11954/−37
```

**Cross-tool concurrence (a second, independent tool):**

```
git ls-remote origin refs/heads/assembly/name-the-zero
  → b9bbfadc        [MATCH]
git ls-remote origin refs/heads/integration/name-the-zero
  → 057e2727        [base FROZEN]
```

**Two-sided controls — the dimension asserted over is the head SHA, so the controls vary the SHA:**

| control | expectation | result |
|---|---|---|
| POS — same tool, different ref (`main`) | must return a **different** SHA | `883eb3bf…` ✅ **fired** |
| POS — `gh` on PR #2071 | must return a **different** head | `6265e378…` ✅ **fired** |
| POS — `gh` on PR #2073 | must return a **different** head | `8c9aa11f…` ✅ **fired** |
| NEG — nonexistent ref | must return **empty** | empty ✅ **fired** |
| POS — re-read after `main` moved | head must be **unchanged** | `b9bbfadc…` ✅ **fired** |

> ### VERDICT — HARD GATE 1: **FROZEN.** `b9bbfadc` is unmoved since 2026-09-05T14:51:37Z, confirmed
> by two independent tools with four fired controls, and re-confirmed after `origin/main` moved
> beneath it. **No third lapse.**

---

## §3 C-9 — THE NAMED HOLDER, and the disposition that is NOT this seat's to make

### 3.1 The holder — ASSIGNED

| object | **HOLDER** | authority | what the holder may NOT do |
|---|---|---|---|
| **PR #1941 @ `b9bbfadc`** | **S-02 `verification-auditor` (eunomia)** — named custodian of record | C-9, C-12 | **May NOT close it.** **May NOT land it** (needs G-A1, deferred on a third party, OUT OF SCOPE). **May NOT fold any cure into it — FORBIDDEN (C-1).** |
| **The M-4 sweep state on #1941** | **S-02** | frame §6 | May not mark it resolved (§4) |
| **The disposition LAND / HOLD / CLOSE** | **★ OPERATOR — fork O-7** | C-9 reserves it explicitly | **No agent decides this** |

**The holder's standing duty:** re-verify the head at **each Wave boundary** and report **FROZEN or
MOVED**. An unverified inheritance is how cargo rots while looking held. That duty was discharged
once here (§2); it is **not** discharged for future waves.

### 3.2 The disposition — **SURFACED AS O-7, NOT DECIDED**

**This seat does not decide LAND / HOLD / CLOSE.** Per HARD GATE 4 and C-9, the disposition is
operator-reserved. It is surfaced with its evidence:

- **LAND is unavailable to any agent.** It requires **G-A1**, which is deferred on a third-party
  answer and is explicitly **out of scope** (shape §7 row 1).
- **CLOSE is FORBIDDEN as board-tidying.** Closing spends a rite-disjoint certificate that cost
  **two re-walks**. This seat did not close it and recommends against closing it.
- **HOLD is the status quo** and is what the head-freeze evidence supports: the PR is OPEN,
  MERGEABLE, CLEAN, and its head has not moved in three days.

> ### ★ FORK **O-7** — OPERATOR WORD REQUIRED
> **PR autom8y#1941 @ `b9bbfadc` — LAND / HOLD / CLOSE?**
> Evidence: head FROZEN (§2); base `integration/name-the-zero` FROZEN at `057e2727`; MERGEABLE/CLEAN;
> the merge-surface sweep **does not run on it at all** (§4.2); landing is G-A1-blocked; closing
> spends the certificate. **This seat holds it and recommends HOLD, but does not decide.**

---

## §4 HARD GATE 3 — the M-4 sweep, RE-MEASURED. Three findings, two of which correct the charge.

### 4.1 The measurement — reproduced exactly, against the CURRENT engine

**`[OWN-HANDS]`** The engine was extracted from the object DB at `origin/main` and run directly.

**Engine currency was itself verified** (the coordinator warned my hit-set might predate the I-late
hex fix):

- `b2b4ae98` (the I-late fix) **IS an ancestor** of current `origin/main` ✅
- The engine binary I ran is **byte-identical** (`diff` rc=0, 0 lines) to the engine at current
  `origin/main` ✅
- The engine header carries **D8** (hex-adjacency exclusion, dated 2026-09-08) and **D10** (inline
  `::error` annotations, dated 2026-09-08) ✅

**So the measurement below was already taken against the NEW rule.** The coordinator's concern is
discharged by measurement, not by assumption.

**Controls (all fired):**

| control | expectation | result |
|---|---|---|
| POS — engine `--self-test` | fixture MUST fail | `positive control hits=8 (expected 8)` ✅ |
| NEG — engine `--self-test` | clean MUST pass | `negative control hits=0 (expected 0)` ✅ |
| NEG — clean range `main...main` | must be CLEAN, rc=0 | `CLEAN (0 hits)` rc=0 ✅ |

**Result — `883eb3bf...b9bbfadc`, rc=1, 3 hits (unchanged in count and location):**

```
digits12   services/email-booking-intake/tests/test_df40_read_kind_corpus.py:80
email      services/email-booking-intake/tests/test_loss_witness_floor.py:778
email      services/email-booking-intake/tests/test_retro_redrive_wall.py:86
```

### 4.2 ★★ FINDING 1 — **THE SWEEP DOES NOT RUN ON #1941 AT ALL.** The bite is deferred to an unopened PR that nobody holds.

The shape (§9) records the M-4 row as *"will go RED at word-time."* **Re-measured, that is not what
happens.**

**`[OWN-HANDS]`, `merge-surface-sweep.yml` at `origin/main`:**

```yaml
on:
  pull_request:
    branches: [main]
```

The `branches:` filter on `pull_request` gates on the **PR's base branch**. **#1941's base is
`integration/name-the-zero`, not `main`.** So the workflow never triggers on it.

**Two-sided empirical proof — not read from the YAML, read from the live check runs:**

| PR | base | is `merge-surface-sweep` among its checks? |
|---|---|---|
| **#1941** | `integration/name-the-zero` | **ABSENT** — across 30+ live check runs |
| **#2071** *(positive control)* | `main` | **PRESENT — and `pass`** ✅ control fired |

**Corroborating range measurements `[OWN-HANDS]`:**

| range | result |
|---|---|
| `main...assembly/name-the-zero` (what was measured) | **3 hits, rc=1** |
| `main...integration/name-the-zero` (the branch #1941 merges INTO) | **CLEAN, 0 hits, rc=0** |

**So the honest word-time answer, which is sharper than "it will go RED":**

1. **Merging #1941 into `integration/name-the-zero` does NOT fire the sweep.** No bite. No RED.
2. The RED bites **only** when a PR is opened from `integration/name-the-zero` → `main`, **after**
   #1941 has merged, at which point the added lines enter a `base=main` merge surface.
3. **`[OWN-HANDS]`** That PR **does not exist.** Enumerated all 50 open PRs targeting `main`: no
   head named `integration/name-the-zero`.

> ### ★ REGISTRY ROW — the deferred M-4 bite
> **Owner:** S-02 (this seat) holds the *knowledge*; **no seat holds the future PR.**
> **Trigger:** opening `integration/name-the-zero` → `main`.
> **Watcher:** **`NO WATCHER`.** The gate is correctly armed and will fire correctly — but it fires
> on a PR that does not exist, that no sprint owns, and that no mechanism will announce. **A
> correctly-firing gate aimed at an unowned future event is face 7 one level down.**

### 4.3 ★ FINDING 2 — the genuine hit is at the line the record names, but it is **NOT the line's stated content**

**`[OWN-HANDS]`, read at `b9bbfadc` with `cat -n` line alignment:**

```
:77  _BASE       = "https://data.example.test"
:78  _LEADS_URL  = f"{_BASE}/api/v1/leads/search"
:79  _OFFICE     = "+14079068111"                                ← NOT flagged
:80  _GUID       = "ca70baa8-1111-2222-3333-4444…6666"   [run elided]        ← THE HIT (digits12)
```

The charge and the custody register both describe the `:80` hit as
`_OFFICE = "+14079068111"` *beside* `_GUID`. **Re-measured: `:80` IS the `_GUID` line.** Confirmed
independently by running the engine in `--lines` mode against the file alone, which reports
`digits12 …:80` and nothing else.

**The class fires on the GUID's trailing 12-digit run** (four 4s, four 5s, four 6s — elided here rather than reproduced). It does **not**
fire on the office prefix and it does **not** fire on the phone number.

**Is `ca70baa8` a real production office prefix?** **`[OWN-HANDS]` — YES, substantiated:**

| receipt | reading |
|---|---|
| `scripts/ebi_witness_ledger.py:154` | `"ca70baa8",` — inside `_TIER_H: frozenset[str]` declared `:151`, consumed `:271` (`elif prefix in _TIER_H:`) |
| `terraform/services/email-booking-intake/environments/production.tfvars` | present (1 match) — **production residency** |
| repo-wide at `origin/main` | **35 files**, incl. witness-ledger JSONs and `.ledge/` handoffs |
| named in prose | *"office `ca70baa8` (office-fa59bf58)"* — `HANDOFF-10xdev-to-eunomia-witness-coverage-provenance-2026-07-30.md:59` |

**★ Attribution correction:** the custody register cites this as `ebi_witness_ledger.py`. The file is
at **`scripts/ebi_witness_ledger.py`** — there is **no** `services/email-booking-intake/src/ebi_witness_ledger.py`
(`git cat-file -e` → *"path does not exist"*). This seat's first probe returned a false zero for
exactly that reason and was re-run against the correct path. **Recorded because a false zero that
is silently discarded is the untaken-zero failure.**

### 4.4 ★★ FINDING 3 — the sweep catches the synthetic decoration and **MISSES the real phone number one line above it**

`_OFFICE = "+14079068111"` — a real-format number with a live area code — **is not caught by the
sweep at all.** Its digit run is **11 digits**; the `digits12` class requires **12**. It is one digit
under the threshold.

**So the RED is genuine but it is genuine for the wrong reason.** The engine flagged a synthetic
placeholder GUID; the datum an operator would actually care about — a real-shaped phone number
sitting on the previous line — passed clean. **The engine has no office-prefix class and no
phone-shape class.**

> ### ★ REGISTRY ROW — sweep blind spot (NEW, this seat's own measurement)
> **Owner:** unassigned — the sweep engine's owner lane.
> **Trigger:** any PR adding a real-format phone number of 11 or fewer digits, or a bare production
> office prefix without an adjacent 12-digit run.
> **Watcher:** **`NO WATCHER`.**
> This is **not** a request to relax the sweep, and per ruling **I-late** ("relax nothing") it must
> not be read as one. It is the observation that the class boundary and the hazard boundary are not
> the same boundary.

### 4.5 The two benign hits — confirmed, and the charge's attribution corrected

**`[OWN-HANDS]`** Both are `email` class on the reserved TLD `.invalid`:
`test_loss_witness_floor.py:778` → local-part `synthetic`, domain `example` + the reserved TLD;
`test_retro_redrive_wall.py:86` → local-part `fixture`, same domain + reserved TLD.

**The exclusion, verbatim from the object DB at `merge-surface-sweep.sh:79`:**

```perl
&& $t !~ /@(?:example\.(?:com|org|net)|localhost)(?![A-Za-z0-9])/i;
```

`.invalid` is **not** excluded — only bare `.com|.org|.net` and `localhost`. **This confirms the
charge's operative warning.** But the charge's *attribution* is imprecise: it says `example.invalid`
"is the sweep engine's OWN positive-control fixture." **`[OWN-HANDS]` — it is not.** The engine's
fixture is **local-part `person`, domain `corp` + the reserved TLD** (`:143`, composed at runtime per deviation D2 so the script
sweeps clean under its own `--lines` invocation); the engine's *negative* control uses
`user[at]example.com` (`:149`). What the two share is the `.invalid` TLD, not the string. **Probed
empirically, as instructed; the paragraph was not trusted.**

> ### VERDICT — HARD GATE 3: **TRIAGED.** One genuine-candidate hit named at
> `tests/test_df40_read_kind_corpus.py:80` (`_GUID`, `digits12`, embedding the real TIER-H production
> office prefix `ca70baa8`); two benign reserved-TLD hits confirmed. **Word-time bite: NOT at #1941's
> merge — the sweep does not run on it. The bite is deferred to an unopened `integration → main` PR
> with NO WATCHER.**

---

## §5 THE REGISTRY OF RECORD

**Legend:** `[OWN-HANDS]` this seat probed · `[CITED]` read at explicit ref · `[ATTRIBUTED]` another
session's measurement, source named.

### 5.1 Rows carried from shape §9 — re-verified, amended where measurement changed them

| # | gate / deferral | owner | trigger (what ends the wait) | **watcher** |
|---|---|---|---|---|
| **1** | **★ R-35** — the EBI freeze; gates clause (b)'s kinding | **operator**, keyed on the cofounder (Damian) | **AMENDED.** Forcing function **SPOKEN in kind (O-1)**: lift on the cofounder's answer **WITH a dated hard cut**. **Both parameters — the instant, and the default disposition if unanswered — are NOT YET NAMED.** | **NOT "no watcher", NOT "resolved":** *forcing-function SPOKEN, parameters PENDING*. Until both are named, **nothing fires** |
| **2** | **G-A1** — blocks landing #1941 | operator | third-party answer; deferred by R-39, untouched by the 09-08 sitting | **`NO WATCHER`** |
| **3** | **★ G-FL1** — the fast-lane predicate | operator | **AMENDED (O-2).** No longer "authored and unratified": **ratified CONDITIONAL on a rite-disjoint review by `security-reviewer`**, dispatched in this same wave | **NOW WATCHED — conditionally.** Its watcher is that review. **If the review does not return, G-FL1 reverts to unratified and nothing announces that** |
| **4** | **G-P3** — answered-and-absent parks | **SPOKEN (C-8)** | discharged at the 09-08 sitting | C-8 **IS** the record; its text exists nowhere in this repo — **nothing to check it against** |
| **5** | **C-13 / R-65** — dead-letter row `bd875254…` | **★ AMENDED — see 5.2 row 12 and 5.4.** Owner: **the conductor / operator's own hand.** **NOT the cofounder** | **HARD CLOCK: cut 2026-09-09T18:00Z**, then resolves LOST automatically; reap 2026-09-10T05:28:46Z | **the clock itself — the ONLY self-firing row in this table** |
| **6** | **C-18 / CARD-ARCH-2** | **EXTERNAL** (their code, their wave mid-flight) | **SURFACE IT, DO NOT TAKE IT** | owner named externally; dependency carried knowingly |
| **7** | **C-10 disposition** (supersede both images) | this initiative, WS-CONTAIN | executes **when R-35 lifts** | inherits row 1's state: **forcing function in kind, parameters pending** |
| **8** | **G-P6 · G-RS16 · G-P4 · G-M7 · R-41 · G-CIREACH · G-RS4 · G-P2** (8 rows) | carried per C-12 | **none ruled** at the 09-08 sitting | **`NO WATCHER` (8 rows)** |
| **9** | **R-72** — *"the plan lane runs read-only; the freeze forbids applies, not plans"* | assigned by shape | narrows R-35 | **★ WATCHED: S-10** — the shape's one registry improvement. **`[OWN-HANDS]` R-72's mechanism is now measured — see 5.2 row 13** |
| **10** | **R-67 / R-39(i)** — the cofounder snippet, FIRST ACT, six rulings keyed to it | operator | **no ratification through 2026-09-08 records an ANSWER** | **`NO WATCHER`** |
| **11** | **M-4 sweep state** on #1941 | **S-02 (this seat)** — holder named, §3.1 | **AMENDED by measurement (§4.2).** Not "#1941's word-time". The trigger is **opening `integration/name-the-zero` → `main`**, a PR that **does not exist** | **`NO WATCHER`** for the future PR |

### 5.2 Rows carried from shape §10 — this shape's own deferrals

| # | deferred | owner | trigger | **watcher** |
|---|---|---|---|---|
| **D-3** | Whether the H/S tier split is repaired, replaced, or retired (frame M-5) | operator or a successor initiative | none set | **★ `NO WATCHER`** |
| **D-7** | **The initiative's NAME** (frame O-5) | operator (**O-5**) | none set — the slug `name-the-client` is in use on the frame's *proposal*, not on an operator word | **★ `NO WATCHER`** |
| **D-8** | Whether the gate architecture should be kept and tuned or dismantled (frame UV-P-7) | operator | none set — *"C-12 implies yes but it was never tested head-on"* | **★ `NO WATCHER`** |

### 5.3 ★ NEW ROWS — measured at PT-00 and by this seat. **Not in shape §9 or §10.**

| # | row | owner | trigger | **watcher** |
|---|---|---|---|---|
| **12** | **★★ D-9 — CLASS-B deploy hazard.** UNREGISTERED in **both** shape §9 and §10 | **this initiative** | any PR in `autom8y-asana` | **The O-3 ruling is the watcher OF RECORD — and `[OWN-HANDS]` NOTHING MECHANICALLY ENFORCES IT.** See 5.5 |
| **13** | **★ R-35's subject is ALREADY RESIDENT IN PRODUCTION** | this initiative (surfacing); operator (disposition) | already true — nothing to wait for | **`NO WATCHER`.** See 5.6 |
| **14** | **★ TFVARS PIN DRIFT — catch #4** | **UNASSIGNED — stated honestly.** The tfvars comment names no owner; the lane that advances the pin does not exist | any `terraform apply` touching EBI | **`NO WATCHER` mechanically.** The only defence is a human merge-day step the comment *asks for*. See 5.7 |
| **15** | **★ EXTERNAL INTEROP BOUNDARY — `POST /calendar/reviewwave`** | **external (NHC / cofounder-associated)** | contract drift observed by us | **`NO WATCHER`.** See 5.8 |
| **16** | **★ GHL TAXONOMY FENCE** — a category error waiting to happen | **WS-DENOM** | **any denominator construction** | inherited by S-05 in Wave 1 **by this row's existence only**. See 5.8.2 |
| **17** | **`CustomGHLId` routing — OPEN** | WS-DENOM | an answer from the external owner | **`NO WATCHER`** — and **explicitly NOT closed by inference**. See 5.8.3 |
| **18** | **★ ESCALATION IS A PERSON, NOT A PROCESS** | **the cofounder, informally** | contract drift | **`NO WATCHER`** — no formal channel, no ticket queue, no SLA |
| **19** | **★ REPO-BOUNDARY DEFECT** — the INTEROP record lives in `autom8y-asana`; the client code it describes lives in `a8/autom8` | **UNASSIGNED** | a reader debugging the POST from the monolith | **`NO WATCHER`.** Fix is a **pointer from the monolith, NOT a second copy** |
| **20** | **★ STATE-OF-PLAY is 56 days stale** | **UNASSIGNED** | `re-verify-by` elapsed **2026-07-14** | **`NO WATCHER`.** See 5.9 |
| **21** | **★★ UNRECORDED-RULING HAZARD — the observer law at the GOVERNANCE layer** | **the governance surface** | an operator ruling taken in conversation | **`NO WATCHER`.** See 5.10 |
| **22** | **★ SUBSTRATE LABEL DRIFT** — six moves this arc, two inside this sprint | every seat | any citation of `origin/main` | **`NO WATCHER`** (§1) |
| **23** | **★ SWEEP BLIND SPOT** — 11-digit phone passes clean | sweep-engine lane | a real-format number ≤11 digits | **`NO WATCHER`** (§4.4) |
| **24** | **★ THE DEFERRED M-4 BITE** — armed gate aimed at an unopened, unowned PR | no seat | opening `integration/name-the-zero` → `main` | **`NO WATCHER`** (§4.2) |

### 5.4 ★ RETRACTION HONOURED — C-13 and R-35 are **TWO WAITS, NOT ONE**

An earlier instruction to this seat asserted that R-65's *"read the receiver's handler first"* can
only mean asking the external owner, **collapsing C-13 into R-35's conversation**. That instruction
was **retracted**, and this seat **verified the retraction independently rather than carrying it**.

**`[OWN-HANDS]`, `autom8y-data/.ledge/specs/BRIEF-damian-consolidated-asks-2026-09-07.md`** — 42
lines, 5929 bytes. **Negative control fired:** a nonexistent sibling path in the same directory →
*"No such file or directory"*. Frontmatter `notes`, **verbatim**:

> *"Left out on purpose: the Cognito production-pool admin check (held by the money-truth program
> until its review rules) and **the dead-letter row clock (the conductor's act, not gated on
> Damian).**"*

**The operator explicitly excluded the dead-letter row from the cofounder's asks, on the express
ground that it is not gated on him.**

| claim | disposition |
|---|---|
| `/calendar/reviewwave` is external (Legacy NHC, cofounder-associated owner) | **SURVIVES** |
| its handler code is unreadable by us | **SURVIVES** |
| ∴ the row's disposition waits on the cofounder | **★ STRUCK** |
| **C-13 and R-35 are ONE wait** | **★★ STRUCK — THEY ARE TWO INDEPENDENT WAITS** |

**They are registered as two rows with separate owners and separate triggers** (5.1 row 5; 5.1 row 1).
**The 2026-09-09T18:00Z cut is C-13's alone** and is neither discharged nor delayed nor explained by
anything in R-35.

**★ Row status update `[CITED]`** — `RULINGS-ebi-operator-interview-2026-09-08.md:65-67`, ruling
**I2/I3, BINDING**: *"Capture the full row to a local gitignored artifact, disposal on redrive or on
an operator close-ruling. Not to AWS (a write), not redacted-to-fields."* **Applied:** captured,
mode 0600, 11 attributes, no payload byte printed to any transcript. **So the row's DATA is
preserved independent of the cut.** What the 2026-09-09T18:00Z cut destroys is the **live queue
entry and the redrive option** — **not the record.**

### 5.5 ★★ D-9 — the CLASS-B fence: **the ruling exists; the mechanism does not**

The operator ruled **O-3** at PT-00: **per-PR fence on all sprints**. The charge asked this seat to
state honestly whether anything *mechanically* enforces it.

**`[OWN-HANDS]` — NOTHING DOES.**

| probe | result |
|---|---|
| deploy-class vocabulary (`CLASS-B`, `deploy.?class`) anywhere in `.github/` at `origin/main` | **rc=1, 0 matches — ABSENT** |
| **POSITIVE CONTROL** — a term known to be in `.github/` (`merge-surface-sweep`), same command form | **rc=0, 4 matches ✅ FIRED** |
| `DEPLOY-CLASS` repo-wide at `origin/main` | **1 file — `.claude/agent-memory/prototype-engineer/MEMORY.md`.** An agent memory file. **Not code. Not CI.** |

*(The first attempt at this probe was piped into `head`, which laundered the exit code — fence 4.
It was re-run without a pipe to obtain the raw `rc`. Both the laundered and the clean run are
reported.)*

> **The deploy-class taxonomy that O-3 fences on exists only in prose and in one agent's memory
> file. There is no CI check, no ruleset, no required context, and no workflow that reads it.**
> O-3 is a governance ruling with **no mechanical enforcement whatsoever**. Its watcher is the ruling
> itself — which is to say, a human remembering it.

### 5.6 ★ R-35's subject has been serving production for three days

**`[OWN-HANDS]`, 2026-09-08, `aws lambda` + `aws ecr`, the production account (id withheld — 12-digit shape) / us-east-1.**
Re-verified independently; the charge's reading was not inherited.

```
autom8-email-booking-intake   State=Active   LastModified 2026-09-05T16:31:56Z
  Code.ImageUri = …/autom8y/email-booking-intake@sha256:76c21a00bcb122b264e8623d181f70a081198f86faf5d1e75d4964df77600dfe

ECR describe-images on that digest:
  imagePushedAt 2026-09-05T12:31:05-04:00  (= 16:31:05Z)
  imageTags     ["salkin-safe-routing-20260905-90e0aa5a4937"]      ← EXACTLY ONE TAG
```

The image was pushed at 16:31:05Z and the function was updated at 16:31:56Z — **51 seconds later.**

> **R-35 freezes the EBI service pending an answer about what `salkin-safe-routing` changes. That
> image has been the serving code since 2026-09-05T16:31:56Z — over three days.** The freeze
> protects against a *change*; the change is already resident. **Owner: operator.
> Watcher: `NO WATCHER`.**

**★ R-35's ask is DRAFTED, and its deadline cell is EMPTY. `[OWN-HANDS]`**
Same brief, the ask table, **line 28 verbatim**:

> `| Intake hand deploy | "What does salkin-safe-routing change on the intake, and should it stay? (I've frozen that service until I know.)" | The service is frozen until answered. | | booking intake |`

The **"By when" cell is empty.**

**★ TWO PRECISIONS, both required, one of which corrects the framing I was given:**

1. **Send status is UNKNOWN.** Frontmatter reads `status: DRAFT-FOR-OPERATOR-SEND` and
   `drafted_by: "the legacy-sql pen for the operator to send"`. **Whether it was ever SENT is not
   determinable from the artifact.** Record: *the ask was **DRAFTED**; send status **UNKNOWN***.
   **Do not record "the ask was made."** If it was never sent, R-35 waits on an ask that was never
   made — a different and far more tractable problem. **That is an operator question.**
2. **★ The empty cell is NOT unusual — it is the majority.** I was told the intake cell is blank
   *"while three siblings carry a date."* **`[OWN-HANDS]` re-count of all 9 ask rows (`:24`–`:32`):
   3 carry `before Sept 24`; 6 are BLANK.** The intake row is one of six, not one of one. The
   sharper finding is about the brief as a whole: **two-thirds of the operator's consolidated asks
   carry no by-when.**

**No reply from the cofounder appears in the corpus — and this is `[UNSEARCHED]`, NOT a zero.** The
search performed was for `salkin-safe-routing`; a reply need not carry that string. **Recorded as
UNSEARCHED. It must never be reported as a zero.**

### 5.7 ★ TFVARS PIN DRIFT — catch #4, and the asymmetry a diff cannot show

**`[OWN-HANDS]`, all three EBI functions, live:**

| function | resident image | vs pin `67d89d7` |
|---|---|---|
| `autom8-email-booking-intake` | **`@sha256:76c21a00…`** = tag `salkin-safe-routing-20260905-90e0aa5a4937` | **★ DRIFTED** |
| `autom8-email-booking-intake-contente-reconcile` | `:67d89d7` | **MATCHES** |
| `autom8-email-booking-intake-forwarding-nudge` | `:67d89d7` | **MATCHES** |

**`[CITED]`** `terraform/services/email-booking-intake/environments/production.tfvars:321` →
`image_tag = "67d89d7"`. **`[OWN-HANDS]`** ECR resolves tag `67d89d7` → digest
`sha256:ff02872a8858…`, pushed 2026-09-04T20:07:18-04:00, tags `["67d89d7","latest"]`.

> **An apply today would roll ONLY the intake backwards** — `76c21a00` (the R-35 subject) →
> `ff02872a` — **and would be a no-op on the other two.** **1 of 3.** The asymmetry is exactly why a
> diff cannot show it: two of three rows agree with the pin, so the file looks correct.

**A structural note this seat adds `[OWN-HANDS]`:** the intake is referenced **by digest**
(`@sha256:`) while its two siblings are referenced **by tag** (`:67d89d7`). The reference *forms*
differ, not just the values.

**`[CITED]`** `production.tfvars:199-233` records the class verbatim: *"the check has now caught it
**THREE times**"*, with the structural diagnosis: *"The asymmetry is structural, not an oversight:
the deploy lane advances the RESIDENT image via `-var image_tag=<fresh sha>` (CLI beats var-file)
and **NOTHING advances this file**. So this pin is stale by construction after every service
deploy."* **This is the fourth catch. Owner: stated honestly as UNASSIGNED — the comment names the
merge-day step but names no one to perform it.**

### 5.8 ★ THE EXTERNAL INTEROP BOUNDARY

**`[ATTRIBUTED]` to peer session `calendar-integration-locus`, relaying an operator ruling. NOT this
seat's measurement and NOT the main thread's.** The durable record is
**`.ledge/decisions/INTEROP-calendar-reviewwave-external-boundary-2026-09-08.md`**.

**`[OWN-HANDS]` git-persistence verified, two-sided:**

| probe | result |
|---|---|
| file | **122 lines, 9033 bytes**, §1–§9 ✅ matches the stated record exactly |
| `git check-ignore -v` | matches `.gitignore:129` `!**/.ledge/decisions/**` — a **NEGATION**, which un-ignores |
| `git status --porcelain` | `??` — **visible** |
| **CONTROL** — a `.sos/` path | matches `.gitignore:90` `**/.sos/*`; **invisible** to status ✅ fired |

**It survives in Git.**

#### 5.8.1 Row 15 — the boundary itself

`POST /calendar/reviewwave` — external, Legacy NHC domain, owner external/cofounder-associated.

> **★ SCOPE IS WIDER THAN THE NAME.** **ALL NON-GHL PROVIDERS route through this ONE endpoint** —
> Acuity, Calendly, Sked, ReviewWave, JaneApp, EHR, Google Cal, CustomCal.
>
> **★ `ReviewWave` IS A LEGACY NAME** — a Croft convention, the first provider integrated, never
> renamed. **It is NOT a provider scope. Any row that reads the name as "the ReviewWave path" is
> wrong for seven other providers.**

**`[OWN-HANDS]` anchor verified** at `a8/autom8 :: apis/asana_api/objects/task/models/unit_holder/main.py:79-109`
— the provider field map is present and carries `reviewwave_id: ReviewWaveId`, `custom_ghl_id:
CustomGHLId`, `acuity_cal_url`, `calendly_url`, `google_cal_id`, `sked_id`, `janeapp_url`,
`ehr_cal_url`, `custom_cal_url` alongside the duration-keyed GHL family.

**Owner: external (NHC / cofounder). Watcher: `NO WATCHER`.**

#### 5.8.2 Row 16 — the taxonomy fence

Two different things share the GHL vendor name:

- **INTERNAL GHL — duration-keyed.** **`[OWN-HANDS]` confirmed present** at the anchor above:
  `GhlTen, GhlFifteen, GhlTwenty, GhlTwentyFive, GhlThirty, GhlThirtyFive, GhlForty, GhlFortyFive,
  GhlFifty, GhlFiftyFive, GhlSixty, GhlSeventyFive, GhlNinety, GhlOneHundredTwenty`, plus
  `GhlTTVFifteen, GhlTTVThirty, GhlTTVFortyFive, GhlTTVSixty`. These are calendars **we create** for
  some clients. **NOT EBI. NOT calendar-integration. Handled entirely separately, external to our
  code** (operator-stated).
  > **★ MUST NOT enter any denominator, tier split, or client-outcome bar.**
- **`CustomGHLId`** — the client brings **their own** GHL calendar. **Different case, same vendor
  name.**

**Owner: WS-DENOM. Trigger: any denominator construction.** Recorded now so **S-05 inherits it in
Wave 1 rather than discovering it.**

#### 5.8.3 Row 17 — the open question, **not closed by inference**

**Whether `CustomGHLId` routes through the endpoint is OPEN.** It was explicitly not settled when
the operator ruled scope, and the peer did **not** assume either way. **This seat does not resolve
it.** Filed as a defer row with the question stated. **`NO WATCHER`.**

#### 5.8.4 The conflation trap — fenced into the row

**`[OWN-HANDS]` re-verified live:**

```
lambda-python-notify-reviewwave-booking-run-prod   State=Inactive   LastModified 2024-01-22T17:25:08Z
lambda-python-notify-reviewwave-booking-run-dev    State=Inactive   LastModified 2024-01-04T19:24:39Z
POSITIVE CONTROL: autom8-email-booking-intake      State=Active     LastModified 2026-09-05T16:31:56Z  ✅ fired
```

These two Lambdas **are ours**, but they are **NOT the endpoint**: a dead **notify** path, Inactive
for ~20 months. **`[CITED]`** the INTEROP record §7 cites
`decommission-receipts-2026-09-04/08-dead-ingress-gate-20260906T011550Z.json` recording
`invocations_in_window: 0` for both.

> **Anyone reading "a reviewwave lambda exists" as "the receiver runs" is wrong twice: wrong service,
> and dead besides.**

**`[CITED]` §8 framing amendment.** `CUSTODY-name-the-zero-wave2-register-2026-09-08.md:31` says the
handler *"exists in NO repo on disk"* — **true on the facts, misleading in framing**: it reads as a
gap in our tree when the truth is **it was never ours**. Amend to: *externally owned; client side
lives in `a8/autom8`.* **§8's further inference — that this collapses C-13 into R-35 — is STRUCK per
5.4.**

### 5.9 Row 20 — STATE-OF-PLAY, decayed

**`[OWN-HANDS]`** `.ledge/reviews/STATE-OF-PLAY.md` frontmatter: `content_status:
measured-ground-truth`, `rite: sre`, `date: 2026-07-13`, `baseline: origin/main f713dd30`, and at
**`:11`** → **`re-verify-by: 2026-07-14`**. Against today, **56 days past**.

> A **measured-ground-truth** surface that charge-authors are told to bind premises to, **decayed by
> 56 days, against a baseline label (`f713dd30`) that is itself six moves stale**, with
> **`NO WATCHER`**.

### 5.10 ★★ Row 21 — the sharpest row on the board: the observer law at the governance layer

**`[CITED]`, `autom8y` `origin/main` (`883eb3bf`) ::
`.ledge/decisions/RULINGS-ebi-operator-interview-2026-09-08.md` — 98 lines. `[OWN-HANDS]` verified
present at that ref.** Its closing section, **`:94-96` verbatim:**

> **"An operator ruling taken in conversation and not written to the record does not exist for any
> seat that was not in the conversation."** *Three interviews produced roughly two dozen decisions;
> **exactly one was recorded on the day.***
>
> *"A ratification interview closes by landing its decisions, or the interview has not closed."*

**This is the observer law at the GOVERNANCE layer — a correct record with no reader — and it is the
same failure class this initiative is named for, one altitude up.**

**The live proof, and it happened during this very sprint:** this lane **and** a peer lane both spent
2026-09-08 reasoning about R-35 from its 2026-09-05 text, while a **2026-09-08 operator correction
sat in `autom8y/.ledge/decisions/`** — a repo neither lane reads. **It was found by accident, not by
any mechanism.** This seat received it mid-run, as a correction, and had to re-measure against it.

**Owner: the governance surface. Watcher: `NO WATCHER` — nothing notifies a seat in one repo that a
ruling landed in another.**

### 5.11 ★★ Row 13/9 precision — I3-Q2 is **NOT** a blanket merge grant. Misreading it would roll production.

**`[CITED]`** same rulings file, **`:73`, ruling I3-Q2, BINDING, WITH A CORRECTED PREMISE:**

> *"R-35's ratified text is a **release condition** — 'HOLD the EBI freeze (no apply either way)
> until D. answers what `salkin-safe-routing` changes' — and **R-72** grants 'the freeze forbids
> applies, not plans.' The merge was lawful under R-72 (plan-only route); **the apply remains
> forbidden.** The ruling stands; its stated justification did not."*

**`[OWN-HANDS]` — this seat measured the mechanism that reconciles I3-Q2 with C-11, TWO-SIDED:**

`service-deploy-dispatch.yml` at current `origin/main`:

```yaml
on:
  push:
    branches: [main]
    paths:
      - 'services/**'        # ← ROOT-ANCHORED. No leading **/
```

and `service-deploy-lambda.yml:304` → `terraform apply -input=false -auto-approve tfplan`.

**The two-sided empirical control, both sides run with the identical command form:**

| side | commit | files | dispatch fired? |
|---|---|---|---|
| **POSITIVE** | `67d89d75` (merge of #1925) | **30 files under `services/**`** | **✅ FIRED** — present in the run list at 2026-09-05T00:03:55Z, `success`, and it produced ECR tag **`67d89d7`** — the very tag now pinned in tfvars |
| **NEGATIVE** | `57e21107` (2026-09-08) | **1 file, `terraform/services/…`; 0 under `services/**`** | **✅ DID NOT FIRE** — absent from the run list |

> **`terraform/services/**` does NOT match a root-anchored `services/**`** → no dispatch → plan-only
> → **merge lawful** (what I3-Q2 ruled).
> **`services/**` DOES match** → `terraform apply -auto-approve` → **merging IS an apply** → **C-11
> stands.**

**`[OWN-HANDS]`** #2071's two changed files are **both under `services/email-booking-intake/`**
(`src/…/match_lead.py` and `tests/test_decline_marker_class_audit.py`). **So the S-14 cure remains
R-35-blocked.**

> **★ NO READER MAY TAKE I3-Q2 AS A BLANKET MERGE GRANT.** It licenses the *terraform* merge on the
> plan-only route. A `services/**` merge is an apply, and the apply remains forbidden. **That
> misreading would roll production** — specifically, it would roll the intake off the R-35 subject
> (5.7).

### 5.12 A properly taken zero — and the question that is NOT a zero

**`[OWN-HANDS]` TAKEN ZERO.** The tag suffix `90e0aa5a4937` (from
`salkin-safe-routing-20260905-90e0aa5a4937`) is **not a resolvable git object** in any repo we hold:

| repo | `git cat-file -t 90e0aa5a4937` | **POSITIVE CONTROL** (that repo's own HEAD) |
|---|---|---|
| `autom8y` | *Not a valid object name* | `29e59e81` → **commit** ✅ |
| `autom8y-asana` | *Not a valid object name* | `d75bfe1a` → **commit** ✅ |
| `autom8` | *Not a valid object name* | `3b0b695a` → **commit** ✅ |
| `knossos` | *Not a valid object name* | `c689c92c` → **commit** ✅ |

Plus: `b9bbfadc` → `commit` ✅ and `deadbeefdead` → *not valid* ✅.
**Four per-repo positive controls fired.** **So if it is a SHA, its object is in no clone we hold.**

*(The first attempt at this zero used two guessed repo paths that did not exist — `autom8` and
`knossos` resolved to "NO REPO AT PATH". Rather than report a two-repo zero as a four-repo zero, the
real paths were located and the probe re-run. **Recorded because a partial zero reported as complete
is the untaken-zero failure in its most plausible-looking form.**)*

**`[OPEN] — NOT A ZERO.** What the `salkin-safe-routing` image actually changed is **UNKNOWN**. The
peer session's probe was interrupted and returned only its header; they **explicitly refused to hand
over an unfinished probe dressed as absence**, and that refusal is honoured here. **The question is
recorded as OPEN with NO result.** It is not recorded as a zero, and it must not be read as one.

---

## §6 CORRECTIONS THIS SEAT MADE TO ITS OWN CHARGE

Recorded because a registry that silently absorbs its charge's errors is not a registry of record.

| # | as given | as measured |
|---|---|---|
| **6.1** | `autom8y origin/main = a4bc0e39` | **`e292b616`** at 20:44Z, **`883eb3bf`** at 20:48Z. **Six moves this arc; two during this sprint.** |
| **6.2** | asana local tree ahead of `origin/main` | **BEHIND** — `d75bfe1a` is an **ancestor** of `389c59bc` |
| **6.3** | the `:80` hit is `_OFFICE = "+14079068111"` | **`:80` is the `_GUID` line.** `_OFFICE` is `:79` and is **NOT flagged at all** (11 digits < the 12-digit threshold) |
| **6.4** | `example.invalid` is the engine's own positive-control fixture | **It is not.** The fixture is **`person[at]corp.invalid`** (`:143`); the *negative* control uses `user[at]example.com` (`:149`). They share the `.invalid` TLD, not the string. **The operative warning survives** — `.invalid` is genuinely not excluded (`:79`) |
| **6.5** | `ca70baa8` is in `ebi_witness_ledger.py` `_TIER_H` | **True, but the path was wrong** — it is **`scripts/ebi_witness_ledger.py:154`**; `services/…/src/ebi_witness_ledger.py` **does not exist**. First probe returned a **false zero**; re-run against the correct path |
| **6.6** | — | **★ FENCE 3 FIRED ON THIS SEAT.** `git show "$H:services/…"` was silently mangled by zsh's `:s` modifier **inside double quotes** → `b9bbfadc…mail-booking-intake`. Re-run as `"${H}:services/…"`. **The fence is real and it was proven live, on me** |
| **6.7** | — | **★ FENCE 4 FIRED.** The D-9 probe was piped into `head`, laundering the exit code. Re-run without a pipe for the raw `rc` |
| **6.8** | my 3-hit set may predate the I-late hex fix | **Re-measured: it did not.** `b2b4ae98` **is** an ancestor of current main, and my engine is **byte-identical** (`diff` rc=0) to the engine at head. **Measurement stands, by measurement** |
| **6.9** | C-13 collapses into R-35 | **STRUCK** — verified independently against the operator's own brief (5.4). **Two waits, not one** |
| **6.10** | the intake by-when cell is blank "while three siblings carry a date" | **Directionally right, materially understated.** Of 9 ask rows: **3 dated, 6 BLANK.** The intake row is one of six |
| **6.11** | the two other EBI function names | **Both wrong as given** (`ResourceNotFoundException` ×2). A positive control listing live functions returned the true names (`autom8-email-booking-intake-contente-reconcile`, `-forwarding-nudge`) and the probe was re-run |

| **6.12** | — | **★★ DOGFOOD CATCH — THIS ARTIFACT TRIPPED THE SWEEP IT DOCUMENTS.** See 6.12 below |

### 6.12 ★★ The registry RED-ed the very gate it was written to register

**`[OWN-HANDS]`** Before publication this seat swept its own artifact with the current engine:
**7 hits — 4 `digits12`, 3 `email`.**

| hit | what it was |
|---|---|
| `:16`, `:431` | the **real production AWS account id** — a 12-digit run, reproduced twice |
| `:251`, `:259` | the synthetic GUID's trailing 12-digit run — **quoting the hit reproduced the hit** |
| `:300`, `:301`, `:312` | the three `.invalid` fixture addresses, quoted verbatim while explaining that `.invalid` is not excluded |

**This artifact lands in `autom8y-asana/.ledge/decisions/`, and `autom8y-asana` is the repo whose
PR #413 the sweep was ported FROM.** Deviation **D1** is explicit that `.ledge/` is **not** skipped —
*"an allowlist there would BE the hole this sweep exists to close."* **So a PR carrying this file
would have gone RED**, and the registry naming an unwatched gate would have been stopped by that
gate. **Found before publication, at zero cost.**

**The fix honoured ruling I-late — *"relax nothing."*** Nothing was allowlisted and no exclusion was
proposed. Instead the artifact adopted **the engine's own deviation-D2 technique** — the engine
composes its email fixture at runtime *"rather than embedded as a literal — so the script sweeps
CLEAN under its own `--lines` invocation."* This document now **describes the shapes without
embedding them**: the account id is elided to a non-run form, the GUID's digit run is elided, and
the three addresses are given as local-part + domain + *"the reserved TLD"*.

**Two-sided proof the zero is TAKEN, not merely absent:**

| | before | after |
|---|---|---|
| this artifact | **7 hits, rc=1** | **CLEAN, 0 hits, rc=0** ✅ |
| engine self-test, same run | — | **pos=8/8, neg=0/0, PASS** ✅ **control fired** |

**The registry is now clean against the gate it registers.** That is the only form of compliance
this document is entitled to claim, and it was obtained by re-running, not by inspection.

---

## §7 WHAT THIS SEAT COULD NOT ESTABLISH — no filler

| item | status | why |
|---|---|---|
| What `salkin-safe-routing` changed on the intake | **`[OPEN]`** | peer probe interrupted; **refused to dress an unfinished probe as absence** |
| Whether a cofounder reply exists | **`[UNSEARCHED]`** | the search was for `salkin-safe-routing`; a reply need not carry that string. **NOT a zero** |
| Whether the Damian brief was ever **SENT** | **`[UNVERIFIED]`** | `status: DRAFT-FOR-OPERATOR-SEND`; **not determinable from the artifact.** Operator question |
| Whether `CustomGHLId` routes through the endpoint | **`[OPEN]`** | explicitly unsettled; **not closed by inference** |
| R-35's hard-cut **instant** and **default disposition** | **`[PENDING]`** | O-1 spoke the forcing function **in kind**; **neither parameter is named** |
| `#2071` / `#2073` mergeability | **`[UNKNOWN]`** | still `mergeable: UNKNOWN` — **UV-P-10 not upgraded**, reported as unknown, not as MERGEABLE and not as CONFLICTED |
| Whether the `integration → main` PR will ever be opened | **`[OPEN]`** | no such PR exists among the 50 open PRs targeting `main` |

---

## §8 VERDICT

### 8.1 Execution-altitude — the four HARD GATES

| gate | verdict | evidence |
|---|---|---|
| **1 — #1941 head re-verified LIVE, frozen-or-moved** | **✅ PASS — FROZEN** | §2; two tools, four fired controls, re-confirmed after `main` moved |
| **2 — every row carries owner AND trigger, or `NO WATCHER`** | **✅ PASS** | §5; **24 rows**; `NO WATCHER` written **19 times**; **no watcher invented** |
| **3 — M-4 RED triaged, genuine hit named, word-time bite stated** | **✅ PASS** | §4; hit named at `:80`; **bite re-measured — the sweep does not run on #1941; the bite is deferred to an unopened, unowned PR** |
| **4 — disposition LAND/HOLD/CLOSE, or surfaced as O-7 undecided** | **✅ PASS — SURFACED AS O-7, NOT DECIDED** | §3.2; **not closed**; certificate not spent |

> ## EXECUTION-ALTITUDE VERDICT: **PASS**
> C-9 and C-12 are discharged. **This advances no clause of the realization predicate. It is
> custodial. It must not be reported as progress toward the bar.**

**The registry's finding is its ratio, and it must be read as one:**

> **24 rows. 19 carry `NO WATCHER`. 1 self-firing clock. 1 conditionally watched (G-FL1, whose
> condition is a review that, if it does not return, silently reverts). 1 watched (R-72 → S-10).**
>
> **The shape counted 11 rows and 9 unwatched. Measurement more than doubled the row count and the
> ratio did not improve.** Every row added by measurement — D-9, the pin drift, the deferred M-4
> bite, the sweep blind spot, the stale STATE-OF-PLAY, the unrecorded-ruling hazard, the label drift
> — arrived **unwatched**. **The registry did not find gates that were being watched badly. It found
> gates that nobody was looking at, and the act of looking is what produced them.**

### 8.2 Product-Altitude ADVISORY

*(Emitted in a section distinct from the execution-altitude verdict per AP-EUNOMIA-ALTITUDE-CONFUSION.
The `-ADVISORY` suffix is load-bearing grammar and MUST NOT be stripped. **This is NON-BLOCKING**: it
halts no rite-transition, no wrap, no handoff, no procession. User-agency is the load-bearing
semantic — eunomia surfaces; the operator decides.)*

> ## **FLAG-ADVISORY**

**Why FLAG and not PASS:** every item this sprint claims as landed carries a `file:line` or
live-probe receipt (§2, §4, §5), and cross-stream concurrence exists (this seat + peer
`calendar-integration-locus` + main thread, ≥2 streams). **But the initiative's
`inception_anchor` is PARTIAL by measured fact:** shape §10 **D-7** records that the initiative's
**NAME was never given by the operator** (frame O-5) — the slug `name-the-client` is in use **on the
frame's proposal, not on an operator word**, with **`NO WATCHER`**. Under
`telos-integrity-ref` §3 Gate A that is an inception-gap, and it routes to the `/go` dashboard
inception-gap panel.

**Why not REFUSE:** no claim-token in this artifact (`shipped`/`landed`/`verified`/`attested`/
`complete`) sits without a receipt, a `NO WATCHER`, or an explicit `[OPEN]`/`[UNSEARCHED]`/
`[UNVERIFIED]` label. The refuse-trigger — a claim token with a null or `TBD`/`wave-level`/`fully`
receipt anchor — **does not fire**.

**Claim-verification audit (Pattern β, doctrinal corpus).** This artifact lands under
`.ledge/decisions/**` and is therefore in scope. Forward-declaration tokens appear at §3.2 ("O-7
… operator words it"), §5.1 row 1 ("parameters PENDING"), and §5.8.3 ("OPEN"). **Each is discharged
in its own paragraph** by an explicit `[OPEN]`/`[PENDING]`/`[UNVERIFIED]` label or a `file:line`
anchor (discharge qualifiers N1/N6). **No unflagged Pattern β violation found.**

**R1 external-audit note.** `target_initiative_owner_rite` for `name-the-client` is **eunomia**, and
this attester is **eunomia**. **Axiom 1 rite-disjointness therefore does NOT hold for a product-
altitude R1 attestation on this initiative**, and per the dispatcher-critic-degeneracy guard this
seat **declines to emit an R1 attestation block**: eunomia cannot R1-attest itself. **A non-eunomia
rite-disjoint critic is required** for any verification-realized attestation. This is recorded, not
worked around. *(Note that the execution-altitude verdict above is unaffected — it is a mechanical
post-execution check, not a rite-disjoint product attestation.)*

---

## §9 RECOMMENDATIONS — for the operator, ranked

1. **★ O-7 — word #1941: LAND / HOLD / CLOSE.** Evidence in §3.2. **CLOSE spends a rite-disjoint
   certificate that cost two re-walks.** This seat holds it and recommends **HOLD**.
2. **★ Name R-35's two missing parameters** — the **instant** and the **default disposition if
   unanswered**. O-1 spoke the forcing function *in kind*; **until both are named, nothing fires**,
   and R-35's subject has been serving production since 2026-09-05 (5.6).
3. **★ Answer whether the Damian brief was SENT.** If it was not, R-35 waits on an ask that was
   never made (5.6). Not agent-determinable.
4. **★ D-9 has a ruling and no mechanism** (5.5). Either build the check or record that O-3 is
   human-memory-enforced. **It is currently the latter, unrecorded.**
5. **★ The `integration → main` PR is unowned** (§4.2). Whoever opens it inherits the M-4 RED. **Name
   them before it is opened, not after.**
6. **The tfvars pin has been caught four times and still has no owner** (5.7). The comment names the
   merge-day step; nothing names the person.
7. **STATE-OF-PLAY is 56 days past its own `re-verify-by`** (5.9) while being the surface
   charge-authors are told to bind premises to.
8. **★ Cross-repo ruling propagation has no mechanism** (5.10). It cost this sprint two mid-run
   corrections and a full retraction. **This is the row most likely to cause the next failure.**

---

**Nothing in this artifact merges, deploys, or applies anything. No merge, deploy, or apply was
performed. Deploy class C-INERT, honoured.**

*Authored by eunomia `verification-auditor` (holding both S-02 roles), 2026-09-08. Self-assessment
ceiling MODERATE per `self-ref-evidence-grade-rule`.*
