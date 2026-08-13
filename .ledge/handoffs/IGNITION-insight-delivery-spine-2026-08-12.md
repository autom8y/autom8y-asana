---
type: handoff
status: draft  # fires when pasted into the fresh session
handoff_type: execution
artifact_id: IGNITION-insight-delivery-spine-2026-08-12
initiative: asana-native-insight-delivery — SPRINT 1 of 3+ (shared spine)
source_rite: 10x-dev (this seam)
target_rite: 10x-dev (fresh session; pantheon already seeded, NO sync required)
created_at: "2026-08-12T14:05:00Z"
purpose: >-
  Paste-grade ignition kit for a FRESH CC session to fire the shared-spine sprint
  wave. Everything below the PASTE-BLOCK marker is the operator's copy&paste
  snippet. The authoritative DAG is the shape (§5 sprints, §7.1 command flow,
  §8 graph); this kit carries only what a COLD session cannot derive from it.
---

# IGNITION — asana-native-insight-delivery, shared spine (S1-S4)

## Pre-flight — VERIFY ONLY. Do NOT seed. (~20s)

```bash
cd ~/Code/a8/a8/repos/autom8y-asana
ari rite current                                  # EXPECT: 10x-dev
# the six seats Sprint 1 actually needs (row-counting the pantheon is brittle):
for a in architect requirements-analyst audit-lead structure-evaluator dependency-analyst entropy-assessor; do
  [ -f ".claude/agents/$a.md" ] && echo "OK   $a" || echo "MISS $a"
done
git fetch origin main -q && git rev-parse --short origin/main   # EXPECT: 4129ae7e (the shape's source_hash)
```

**`ari sync` is a CONFIRMED NO-OP here and `ari rite invoke` is REFUSED, not
omitted** — grounded on DURABLE ON-DISK FACTS, not on any session's budget
number: all four rites (`arch` / `eunomia` / `hygiene` / `sre`) appear in this
repo's `.claude/CLAUDE.md` §Borrowed Agents block, and every seat Sprint 1 needs
exists as a file in `.claude/agents/`. An invoke would re-borrow what is already
co-seated. Run one ONLY if a probe above prints `MISS`, and then only for the
rite that owns the missing seat — note the syntax is POSITIONAL, and `ari sync`
is not merely the wrong verb — it is **DESTRUCTIVE here**. Per `ari sync --help`
it *regenerates the channel directory from the active rite* and **auto-removes
orphans by default**; run against a channel carrying four borrowed rosters plus
locally-modified `.claude/` files it can STRIP the very seats S1-S4 need. Never
run it as a "fix" for a failed seat probe. (The shape carries a milder form of
the same defect at `shape:1060` — `ari rite invoke --rite=arch`; `--rite` is not
an `invoke` flag.)

```bash
# FALLBACK ONLY — if and only if a seat probe printed MISS.
ari rite invoke <rite-name> agents     # e.g. `ari rite invoke hygiene agents` — one rite per invocation
# ...then ONE Claude Code restart. Not required today.
```

**Freshness anchor:** the shape records `source_hash: 4129ae7e`. If the
`rev-parse` above does NOT print `4129ae7e`, the substrate has moved under the
shape — treat its code-level premises as VERIFY-not-BUILD and re-probe before
acting on them. (Verified equal at kit authoring, 2026-08-12.)

**On the inscription:** `.claude/CLAUDE.md` has been regenerated and now agrees
with the CLI (`5-agent workflow (10x-dev)` + the four borrows). An earlier
kit warned it was stale; that warning is now FALSE and has been removed. Standing
rule unchanged: **on any conflict, trust `ari rite current`** — the inscription
itself names the CLI authoritative.

---

## PASTE-BLOCK (copy everything below into the fresh session as message 1)

/sos start "asana-native-insight-delivery — SPRINT 1 (shared spine): say-able predicate · residue triage · rails · source-of-record"

CRUSADE INGEST — pre-adjudicated; execute, do not re-litigate. Orchestration:
@"potnia (agent)" is CONSULTED at each phase transition and RETURNS a gate
directive — it holds no Task tool and fires nothing; the main thread executes
what it returns. Forks touching an operator-ruled gate ESCALATE rather than
re-rule.

**The /sprint mechanic, stated so it cannot be misread:** issue ONE `/sprint`
planning invocation after /sos start, which then dispatches **S1-S4 as four
parallel Task calls in a single message** → four atomic PRs. One sprint record,
four concurrent authors. Do NOT mint four sprints; do NOT serialize the four.

★ SEAT REALITY — verify before routing, do not assume (three prompts today named
seats that do not resolve): **`myron`, `iris` AND `pythia` resolve in NEITHER
`ari rite pantheon` NOR `.claude/agents/`** (shape SVR-9). The live roster is
definitive: **pythia does NOT resolve here — do not attempt the dispatch.** Use
the ladder directly: design forks → `architect` · routing forks → `potnia` ·
operator-ruled forks → ESCALATE per the fences. Never invent a seat; flag the gap.

CHARTER — read in this order; these ARE the decision space, not the operator's
memory. Read each TO THE END: later sections routinely supersede earlier claims
here, receipted three times in 24h (STAGE1's "nothing applied" superseded by its
own APPLY RECEIPT; DETERMINATION-w2's "#339 has NOT merged" superseded by the
merge; the frame's "channel is dark" superseded by its own §1).
@.sos/wip/frames/asana-native-insight-delivery.shape.md   ← THE AUTHORITATIVE DAG. §5 sprint specs (entry/exit/seats/PR boundary) · §7.1 command flow · §8 graph + the deliberately-undrawn edges · §6 checkpoints · §10 operator surface · §13 falsifiers+kill-switches · **§16 CONTEXT LOADING ORDER — read this FIRST: it gives per-sprint read-lists and explicitly forbids preloading full ADR-007 (1300+ lines) or the full EVIDENCE-* files. Over-reading is the main way this sprint blows its bank.**
@.sos/wip/frames/asana-native-insight-delivery.md          ← the envelope: mission fork (HOLD), 4-rung predicate, workstreams, 7 premise events
@.know/telos/asana-native-insight-delivery.md              ← PROPOSED; ratification is OS-4 (operator)
@.ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md  ← ⚠ CITATION FORM: the operative core is DOCUMENT §3. "§4 priority domains" and "§5 the two gates" mean CORE ITEMS 4 and 5, which live at `:54` and `:55` INSIDE document §3. Document §4 is Transcription Fidelity and §5 is Provenance Lineage — a cold session following "§4" lands on a normalization ledger (adversary C-11)
@.ledge/decisions/RULING-operator-option4-interview-2026-08-12.md ← P-3 (payload withheld, NO clock) · P-4 · P-1 · P-12
@.ledge/decisions/ADR-007-verification-axis-gate-2026-08-12.md §7 ← the parallel K-lane this must NOT collide with
@.ledge/reviews/REPORT-asr-team-brief-2026-08-12.md        ← the first deliverable + its §6 five candidate asks (status: draft — delivery UNCONFIRMED, that is UV-P-1)
@.sos/wip/EVIDENCE-w1-cohort-spread-14day-2026-08-12.md · @.sos/wip/EVIDENCE-age-at-tick-v-sizing-2026-08-12.md · @.sos/wip/DIAG-S1-cadence-2026-08-11.md · @.ledge/decisions/CARDS-follow-up-initiatives-2026-08-11.md
@.know/scar-tissue.md  ← ⚠ EXPIRED: `generated_at 2026-07-23`, `expires_after: 7d` — ~20d stale; the read hook will fire on every open. Read it for the classes, re-verify any specific anchor before acting on it.

REPO GROUND TRUTHS (absolute paths; `git -C` everywhere — a seat miscut worktrees
into the wrong repo TWICE today relying on cwd):
- Producer / this repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana (SQUASH merges, verified 6/6 single-parent)
- Monorepo: /Users/tomtenuta/Code/a8/a8/repos/autom8y — ASR at services/account-status-recon, SDK at sdks/python/autom8y-core, ASR terraform at terraform/services/account-status-recon/ (merge-commit convention)
- ⚠ The monorepo working tree sits on `fix/wss-wildcard-scope-bypass-closure`, NOT an ancestor of origin/main. **PIN origin/main (fresh fetch) for every monorepo read.** A local read there produces false negatives that read like a falsification of landed work (ADR-007 §8 O-11). S5 lands there; S1-S4 do not.

SPRINT 1 SCOPE — the shared spine. Run S1-S4 **4-WIDE IN PARALLEL**; they are
mutually independent and serializing them is the over-sequencing the decomposition
exists to prevent (shape §8.2: S1↔S2↔S3↔S4 edges are DELIBERATELY NOT DRAWN).
All four are read-only `.ledge/` work, NO producer deploy, so **neither live
window binds them — they start today.** Four atomic PRs, one per sprint.
  S1  say-able-set predicate — 10x-dev: architect + requirements-analyst;
      critic `audit-lead` (hygiene — rite-disjoint). NOTE its charter is
      refactoring-QA; domain fit on charter-legal predicate reasoning is WEAK.
      Shape §19.3 names the alternative: escalate the critique to the operator.
  S2  residue triage (7 dispositions) — architect. **No critic BY DESIGN**
      (shape §5.1: "bookkeeping altitude; critique folded into PT-01") — this is
      deliberate, do not invent one.
  S3  rails, CR-1-bound — architect; critic `structure-evaluator` (arch — rite-disjoint)
  S4  source-of-record (NEW, shape-minted) — **runs in the ARCH rite**:
      dependency-analyst + structure-evaluator. Author the 10x→arch HANDOFF as
      its first act; the receiving seat stamps PV-PASS / PV-PARTIAL / PV-FALSE
      per shape §14.2.
      ⚠ **CRITIC CORRECTED (potnia D1, 2026-08-12):** shape §5.1 names
      `arch-adversary`, but author and critic would then BOTH be arch — a
      violation of this kit's own disjointness fence and of shape §15.1.
      **Use `entropy-assessor` (eunomia) or `audit-lead` (hygiene) as the
      rite-disjoint critic.** `arch-adversary` MAY additionally gate the outbound
      HANDOFF as an in-rite check — but it does not satisfy disjointness, and
      the blanket claim must not paper over that.
      ★ **A NEGATIVE result is a FIRST-CLASS EXIT.** Shape F-3 / K-SW-2 /
      DEFER-S-2: "no contractable source" plus a CARRIED UV-P-5 discharges S4.
      Do NOT chase a terraform log-group owner that does not exist at autom8y
      `origin/main`. S4 is the bank's long pole; this is the over-run valve.
Per-sprint entry criteria, exit criteria, PR boundary and mission statements are
in shape §5.1 — read them there; do not re-derive.

NOT IN THIS SPRINT: **S5** (the NF-1 pointer fix — monorepo, window-fenced) ·
**Branch A (SA-1..3)** and **Branch B (SB-1..3)**, both behind GATE-FORK. Do not
start them. Do not pre-position them.

CHECKPOINTS (potnia fires; shape §6): **PT-01 spine fan-in (HARD)** — is the fork
briefing complete? · **PT-02 GATE-FORK readiness (HARD)** — is the decision
surface honest and TWO-SIDED? Sprint 1 ENDS at PT-02 with a briefing handed to
the operator. It does not end with merges.
**PT-07 does NOT fire in Sprint 1** — shape §6 sets it after SA-3/SB-3, two
sprints downstream behind GATE-FORK. Sprint 1's only PT-07 obligation is to
PRESERVE the RF-2 attester scope-split in the PT-02 briefing.

EXIT CRITERIA — the rule that binds every sprint (shape §5.4): **a merge is NOT a
discharge.** The initiative's predicate is a four-rung ladder — authored →
delivered → read → **ACTED ON**. Where a leg's value only exists once consumed,
the exit is the **consumption receipt**, not the artifact. Rungs 1-3 attest to
eunomia verification-auditor; **rung 4 is OPERATOR-ONLY and felt — no agent
closes it, including the agent that authored the predicate.**
⚠ RF-2: the attester is rite-disjoint but **NOT author-disjoint** —
`verification-auditor` authored EVIDENCE-w1. The PT-07 scope-split remedy is in
the shape; honor it.

OPERATOR-RULED FENCES (violate → halt + escalate, never argue):
★ **CR-1 — ALL THREE Asana write classes are OPERATOR-RESERVED.** Comments,
  tasks, custom fields. The reasoning matters and must not be re-derived
  sloppily: charter gate (a) fires not because the *record* is irreversible (a
  comment deletes cleanly) but because **the notification is** — the broadcast
  cannot be retracted. Gate (b) fires CONDITIONALLY and is **not statically
  decidable**, because the follower set is mutable. ⚠ **Do not compress the
  three classes into one limb** (adversary C-8): shape §3.4 puts gate (a) on
  comments and tasks via the irretractable-NOTIFICATION limb, and on **custom
  fields via the ACQUIRED-DEPENDENCY limb** — a different mechanism. Task-creation
  additionally destroys rung 4's falsifiability. **No agent writes to the live
  board.**
  ⚠ **CR-1's stated PRINCIPLE is under external challenge — its OUTCOME is not.**
  The rite-disjoint adversary ruled the universal form ("you cannot take back a
  notification") **OVER-EXTENDED**: applied consistently it fires gate (a) on the
  Slack rail the shape itself endorses, and on every merge to `main`. CR-1 is
  **over-determined** — strike gate (a) entirely and comment-CREATE is still
  operator-reserved on two independent grounds (unbuilt per SVR-5; outside the
  ratified verb set at `asana-mcp-v1:209`). **So: obey CR-1, do not re-derive or
  extend its reasoning.** The narrowing is an OPERATOR ruling (see the addendum).
★ **CR-2** — Mission B's own deliverable (team reach into the verdict surface)
  crosses §5(b) security/credentials. B is MORE gated than the frame said.
★ **GATE-FORK is the operator's and is NOT to be pre-empted.** The shape ruled
  the fork REAL but MIS-PLACED: it gates the BUILD, not the LEARNING. S1-S4
  produce the ruling's own evidence. Brief it at PT-02; never pick it.
★ **P-3 stands**: the verdict payload is withheld — and note the exact wording,
  because "until K-4" reads as SCHEDULED and it is not. RULING P-3 verbatim:
  "honest aborts continue with **NO clock**; the successor's landing is the only
  exit." There is no date behind this. The #account-health
  channel is NOT dark (abort alerts post every 4h) — only the payload is held.
  Do not "fix" the aborts; they are ruled and expected.
★ **No K-lane collision**: read-only w.r.t. the combiner, the reducer,
  `RowsMeta`/`AggregateMeta`, the manifest write path, and `SectionInfo`. Nothing
  rides a K-lane PR. Acquire NO dependency on the one-way door.
★ **Window fence** — two live clocks share this substrate and a producer deploy
  inside either contaminates it (the V1-writer-changed-mid-window scar): the AL-5
  re-baseline sample opens ≥2026-08-14T11:04Z; the substrate-v2 parity window runs
  floor ~2026-08-14T10:58Z → ceiling Aug 18. S1-S4 are read-only and unaffected.
  Any producer deploy inside a window must be recorded as a DECLARED REGIME
  BOUNDARY, and that recording is an operator item.
★ Self-attestation caps MODERATE. The external critic is RITE-DISJOINT from the
  author. The shape's own CR-1/CR-2 charter reasoning is the part it flagged as
  most deserving an external critic — first opportunity is PT-01.

OPERATOR SURFACE — non-delegable (shape §10). Shortest list: **OS-1 + OS-3**.
  OS-1  UV-P-1 / UV-P-2 — was team brief #1 actually DELIVERED, and has the team
        asked for anything? The single hard input to the fork. A NULL on demand
        is legitimate and mission-reshaping. Phase 1 may start BEFORE this closes.
  OS-2  UV-P-4 — what non-engineering data surfaces does the team ALREADY have?
        ⚠ **This SOFT-BLOCKS S3's external half, and S3 is IN this sprint**
        (shape :1334). Sprint 1 may start before it closes; S3 cannot fully
        discharge without it. The kit previously jumped OS-1 → OS-3 (adversary C-5).
  OS-3  GATE-FORK — Mission A / Mission B / both. **FREE until 2026-08-18.**
  OS-4 telos ratify/amend (RF-2 attester split recommended) · OS-5 rung 4 (felt,
  unclocked) · OS-6 any Asana-native write rail (CR-1) · OS-7 the CR-2 §5(b)
  access ruling · OS-8 any P-3 posture amendment · OS-9 any declared regime
  boundary inside a live window.

UV-P REGISTER — these are EXIT CRITERIA, not background notes (adversary C-6):
  **UV-P-4** (what surfaces the team already has) is an **S3 exit criterion**
  (shape :666) and is gated on operator OS-2.
  **UV-P-5** (a contractable source for Mission A) is an **S4 exit criterion**
  (shape :694). ⚠ **S4 would otherwise inherit a FALSIFIED premise**: the shape
  states UV-P-5's reason as "`terraform/services/asana/` does not exist at
  autom8y origin/main" — **that is FALSE** (live probe: `git -C .../autom8y
  ls-tree --name-only origin/main terraform/services/asana/` → 17 entries,
  exit 0). UV-P-5 stands open for a DIFFERENT reason (`git grep retention_in_days`
  there → zero matches). Do not send S4 hunting for a directory that is right there.

SCARS (all receipted this arc):
- `git -C <abs-path>` everywhere; never rely on cwd.
- UTC only via `date -u`; epoch math in aws logs windows.
- Match each repo's merge convention; verify by parent-count, never assume.
- HOT main + strict branch protection: `gh pr update-branch` → `gh pr merge
  --squash --auto` → watcher; expect BEHIND re-staling; just re-update.
- **Subagent self-park is UNRELIABLE — a parked agent never resumes itself.**
  Every clock lives on the MAIN thread (background waker → SendMessage resume).
  "I'll wake at T" from a subagent means the work will not happen.
- A subagent may be harness-blocked from writing a deliverable file; when that
  happens it must RETURN the complete content for the caller to inscribe, never
  silently degrade. Fired twice today.
- NEVER bare `terraform apply` in terraform/services/asana (pre-existing drift +
  an untracked alarm file; always -target + BOTH -vars).
- .sos/wip frontmatter enum is **ROOT-SCOPED, not universal** (adversary): root
  files carry type ∈ {audit,triage,qa,spec,scratch,design}, but `.sos/wip/frames/`
  legitimately carries `type: frame` / `type: shape`. Match the directory.
- Artifacts carry stale premises their own later sections supersede — read to the
  END before acting on an early claim.

GRANT: comprehensive user-grade permission to the pantheon and borrowed seats on
my behalf, all repos on the filesystem (above, below, or across the tree), for
everything short of strict impossibilities — BOUNDED BY the operator rulings
above, which this grant does NOT override.

⚠ `/sprint`'s OWN pre-flight (`.claude/commands/sprint.md:26-30`) reads
`.ledge/reviews/STATE-OF-PLAY.md` and re-verifies on a passed stamp — the file
exists (written 2026-07-23) and the command WILL prompt. Expect it; it is not an
error.

Then fire /sprint (only after /sos start) scoped to S1-S4.

## END PASTE-BLOCK

---

## REVISION 2 — potnia routing validation absorbed (2026-08-12 ~14:35Z)

**Verdict received: PV-PARTIAL** — both load-bearing routing premises HELD (all
six Sprint-1 seats resolve as dispatchable files; `ari sync` genuinely a no-op,
independently re-derived), with 14 defects of which 3 were hard blockers on
cold-session executability. All 14 dispositioned below; the PASTE-BLOCK above is
REVISION 2.

| # | Defect | Disposition |
|---|---|---|
| **D1** | S4's critic `arch-adversary` is NOT rite-disjoint — author and critic both arch, violating this kit's own fence and shape §15.1. Compounded: arch-adversary's trigger is "arch OUTBOUND HANDOFF" but S4's artifact is an ADR returning to 10x-dev | **FIXED** — disjoint critic (`entropy-assessor`/eunomia or `audit-lead`/hygiene) named; arch-adversary retained only as an optional in-rite HANDOFF gate, explicitly NOT counted as disjointness |
| **D2** | Fallback used `ari sync --rite=` — wrong verb; `ari sync` does not co-seat | **FIXED** — `ari rite invoke <rite-name> agents`, POSITIONAL syntax verified live against `ari rite invoke --help` |
| **D3** | `/sprint` count self-contradictory: kit said ONCE, shape §7.1 lists four commands | **FIXED** — mechanic stated explicitly: one planning invocation → four parallel Task calls in a single message → four atomic PRs |
| **D4** | Budget grounds ("~97% of 50k") imported from the AUTHORING session; a fresh session reads ~0% and the stated reason evaporates | **FIXED** — refusal re-grounded on durable on-disk facts (CLAUDE.md borrowed block + `.claude/agents/` files) |
| **D5** | The ⚠ inscription-is-stale warning is now FALSE — CLAUDE.md has been regenerated and agrees with the CLI | **FIXED, verified independently**: `grep` returns `5-agent workflow (10x-dev)` + all four borrows. Warning removed; the standing trust-the-CLI-on-conflict rule kept |
| **D6** | PT-07 listed as a Sprint-1 checkpoint; shape §6 fires it after SA-3/SB-3 | **FIXED** — removed, with the RF-2 preserve-the-scope-split obligation kept |
| **D7** | Shape **§16 context loading order** omitted from the pointer list — the section that forbids preloading full ADR-007/EVIDENCE files | **FIXED** — added and flagged as read-FIRST; over-reading named as the main bank risk |
| **D8** | Claimed shape `source_hash: 4129ae7e` may have drifted (session snapshot showed `cc20772e`) | **REFUTED by live probe** — `git rev-parse origin/main` = **`4129ae7e`**, exactly equal. Potnia read a session-START snapshot. A freshness-anchor line was added anyway (cheap, and the next carrier may not be so lucky) |
| **D9** | S4's cross-rite envelope unnamed (arch rite; 10x→arch HANDOFF; §14.2 PV stamp) | **FIXED** |
| **D10** | S4's NEGATIVE result not pre-authorized — the session-sizing safety valve | **FIXED** — negative + carried UV-P-5 named as first-class exits |
| **D11** | `pantheon \| wc -l` is brittle (counts headers/blanks) | **FIXED** — replaced with a per-seat file probe over the six seats Sprint 1 needs |
| **D12** | "potnia fires the checkpoints" mis-states its agency — it is consultative and holds no Task tool | **FIXED** |
| **D13** | "try pythia" invites a failed dispatch | **FIXED** — roster is definitive; ladder used directly |
| **D14** | S2's null critic read as an oversight | **FIXED** — shape's own `# bookkeeping altitude; critique folded into PT-01` carried |

**Two soft notes carried, not fixed** (they are judgement, not defect): S1's
critic `audit-lead` is rite-disjoint but a weak DOMAIN fit for charter-legal
predicate reasoning — shape §19.3's alternative is escalation to the operator;
and `structure-evaluator` is an author on S4 while critic on S3 inside the same
fan-in bank — not a disjointness violation, but a load and independence note.

**Complexity gate: DO NOT SPLIT.** Potnia sized Sprint 1 at ~13-15 dispatches and
ruled it correctly one session **conditional on D10** — splitting would destroy
the 4-wide parallelism that justifies the decomposition. Pre-authorizing S4's
negative exit converts the only over-run risk into a first-class outcome.

**Still outstanding at revision 2:** the adversarial falsification of this kit and
the external critique of the CR-1/CR-2 charter reasoning. A first attempt died on
an external spend-limit stall; re-dispatched on Opus. Until it lands, **CR-1 and
CR-2 reach the fresh session as MODERATE self-attestation, not externally
challenged** — the shape's own PT-01 is their scheduled critique station either way.

---

## ADDENDUM — adversarial pre-carry challenge (APPEND-ONLY, 2026-08-12T16:41Z)

> Author: `arch-adversary` (rite-disjoint from the kit's author). Read-only against
> every target; this section is the ONLY mutation, and it is an append.
> **Verdict on this kit: CARRY-WITH-CORRECTIONS.** Every `@`-reference resolves
> (12/12). The CR-1 / CR-2 / RF-1 / RF-2 / P-3 / four-rung / window-fence citations
> are FAITHFUL to the shape and the rulings. The corrections below are line-edits;
> none changes the sprint plan, the seats, the fences, or the DAG.
> Self-attestation capped **MODERATE** (single adversary, no second grader).
>
> **HOW TO CARRY:** hand-apply C-1 and C-2 into the PASTE-BLOCK before pasting
> (they are inside it), then paste this addendum as **message 2**.

### C-1 — BLOCKING · the pre-flight probe mis-fires (off-by-one), and it routes into C-2

`ari rite pantheon` prints a **header row** (`NAME MODEL ROLE`). Live at 16:35Z:
`ari rite pantheon | wc -l` → **25**, not 24. The kit's `# EXPECT: 24 seats`
therefore reads as a MISMATCH on a healthy channel, and the kit's own text then
sends the reader to the FALLBACK — which is C-2. The two defects compound.

Replace the pre-flight block (kit `:21-25`) with:

```bash
cd ~/Code/a8/a8/repos/autom8y-asana
ari rite current                                   # EXPECT: 10x-dev + 4 borrows (sre, hygiene, arch, eunomia)
ari rite pantheon | tail -n +2 | wc -l             # EXPECT: 24  (tail strips the header row)
ls .claude/agents/ | wc -l                         # EXPECT: 24 — exact 1:1 with the pantheon
```

Verified live 2026-08-12T16:35Z: `10x-dev`; pantheon body **24**; agents dir **24**;
names match 1:1; budget `48500 / 50000 = 97.0% used`. The ~97% claim is **CONFIRMED**.

### C-2 — BLOCKING · the fallback command is the WRONG command and is hazardous

Kit `:37` says `ari sync --rite=<the-one-missing-rite>`. To **borrow** a missing rite
the command is `ari rite invoke <name>` — **positional**, and `--rite` is not an
`invoke` flag (`ari rite invoke --help`). `ari sync --rite=X` is a different
operation: it *"Generates the channel directory from the active rite"* with `--rite`
overriding which rite that is, and it auto-removes orphans by default
(`--keep-orphans` exists to suppress it). Running it against a channel that currently
carries four borrowed rosters and five locally-modified `.claude/` files can strip
seats this initiative needs. Replace with:

```bash
# FALLBACK ONLY — iff a rite is missing from the probe above. Positional, one per invocation.
ari rite invoke arch        # or sre / eunomia / hygiene
# ...then ONE Claude Code restart after the final invoke. Not required today.
```

(The shape's own `:1060` carries the same defect in milder form — `ari rite invoke
--rite=arch`. Positional is correct in both places.)

### C-3 — FLAG · the roster warning at `:41-44` is now STALE

Live `.claude/CLAUDE.md` at 16:35Z: `:12` = *"5-agent workflow (**10x-dev**)"*;
borrowed-agents block `:127-130` lists **four** rites (arch, eunomia, hygiene, sre).
`git diff --stat .claude/CLAUDE.md` → +27/-12, uncommitted. The inscription was
re-synced after this kit was authored (14:05Z) and **now AGREES with the CLI**. The
warning's particulars (*"declares a `releaser` rite with 2 borrows"*) are FALSIFIED.
The standing advice — **trust `ari rite current`, never the inscription** — is
unaffected and still correct. Carry the advice; drop the particulars.

### C-4 — FLAG · `ari sync` is "not required", not "a CONFIRMED NO-OP"

Shape `:1043` verifies: *"`ari sync` is NOT required for any sprint in this shape."*
"CONFIRMED NO-OP" is a strictly stronger, unprobed claim about what `ari sync` would
DO — and per C-2 it would do something. Likewise `ari rite invoke` is not "REFUSED";
nothing refuses it, it is simply unnecessary and would spend budget. Restate as:
**`ari sync` is NOT REQUIRED and `ari rite invoke` is UNNECESSARY — every seat S1-S4
needs already resolves.**

### C-5 — FLAG · OS-2 is missing from the OPERATOR SURFACE list, and it touches S3

Shape §10 carries **OS-2 — close UV-P-4** (*what non-engineering data surfaces the
team already has*), which **soft-blocks S3's external half**. S3 is IN this sprint.
The kit's list jumps OS-1 → OS-3. Add:

- **OS-2** UV-P-4 — what non-engineering data surfaces does the team already have?
  SOFT-blocks S3's external half only. S3 proceeds and CARRIES it; it is never guessed.

### C-6 — FLAG · the UV-P register is absent; two of them are Sprint-1 exit criteria

The kit names UV-P-1 and UV-P-2 only. Shape §18.1 carries five. Add:

| UV-P | status | binds |
|---|---|---|
| **UV-P-1** brief #1 delivered? | OPEN — operator (OS-1) | GATE-FORK |
| **UV-P-2** has the team asked for anything? | OPEN — operator (OS-1) | **hard-blocks GATE-FORK**; NULL is legitimate + mission-reshaping (K-SW-1) |
| **UV-P-3** verdict-bucket live state | ✅ DISCHARGED | — |
| **UV-P-4** non-engineering surfaces | OPEN — operator (OS-2) | **S3 exit criterion** — close or carry under the Gate-C DEFER-tag pattern |
| **UV-P-5** asana CloudWatch log retention | OPEN | **S4 exit criterion** (DEFER-S-2) — see C-7 |

### C-7 — FLAG · S4 would inherit a FALSIFIED premise. Live-probe receipt below.

Shape `:694` states UV-P-5's reason as *"terraform/services/asana/ **does not exist**
at autom8y origin/main"*. Live probe, 2026-08-12T16:38Z:

```
git -C /Users/tomtenuta/Code/a8/a8/repos/autom8y ls-tree --name-only origin/main terraform/services/asana/
  -> 17 entries (backend.tf, main.tf, variables.tf, s3.tf, environments/, outputs.tf, ...), exit 0
git -C .../autom8y grep -n retention_in_days origin/main -- terraform/services/asana/
  -> zero matches
```

**The directory EXISTS.** UV-P-5 itself still stands OPEN — retention is genuinely not
declared there — but the stated reason is false, and S4 must not go hunting for a
missing directory instead of reading the one that is there. S4: read
`terraform/services/asana/` at `origin/main` and resolve the real log-group owner from
it. (This repo also has its own `terraform/services/asana/` — do not conflate them.)

### C-8 — FLAG · CR-1's compressed reasoning drops the custom-field limb

Kit `:117-123` attributes gate (a) on **all three** classes to the irretractable
notification. Shape `:415-419` does not: *"Gate (a) fires on all three via the
irretractable-notification limb (comments, tasks) **or the acquired-dependency limb
(custom fields)**."* The CF ruling turns on shared machine-read state — this repo
already runs live Tier-2 CF writes, so a CF insight becomes an input to systems nobody
re-checked (the ADR-007 §7.5 one-way-door hazard, one layer out). The kit's own line
says this reasoning *"must not be re-derived sloppily"*; restore the second limb.

### C-9 — FLAG · PT-07 is not a Sprint-1 checkpoint

Shape §6: PT-07 fires `after: [SA-3, SB-3]` — branch attestation. The kit lists it
under Sprint-1 CHECKPOINTS while also stating (correctly) that **Sprint 1 ENDS at
PT-02**. Sprint 1 fires **PT-01 and PT-02 only**. RF-2's remedy is *designed* at PT-07
and merely *noted* now; nothing is attested in this sprint.

### C-10 — FLAG · `/sprint` ONCE vs the shape's four invocations

Kit `:54-55` and `:178` say fire `/sprint` **ONCE** scoped to S1-S4. Shape §7.1
`:1088-1091` — the flow the kit itself names authoritative — lists **four**
invocations, `/sprint S1` … `/sprint S4`. Resolve before pasting; do not let a cold
session guess. (Either is workable — four dispatches must still run 4-WIDE IN
PARALLEL; the shape's `:1260` S1↔S2↔S3↔S4 edge is DELIBERATELY NOT DRAWN.)

### C-11 — ADVISORY · citation form, staleness, and pre-flight the kit omits

- **`:72` charter citation.** *"§4 priority domains; §5 the two gates"* means the
  **core items 4 and 5**, which live INSIDE document **§3** at `:54` and `:55`. The
  document's own §4 is *Transcription Fidelity* and §5 is *Provenance Lineage*. Cite
  `:54` / `:55`; a cold session following "§4" lands on a normalization ledger.
- **`/sprint` pre-flight** (`.claude/commands/sprint.md:26-30`) reads
  `.ledge/reviews/STATE-OF-PLAY.md` and requires re-verification if its
  `re-verify-by` stamp has passed. The file exists; it was written 2026-07-23. Expect
  the prompt.
- **`.know/scar-tissue.md` is EXPIRED** — `generated_at 2026-07-23`, `expires_after:
  7d`, now 13d stale; the read hook says so on every open. Read it as history, not as
  current state.
- **`.sos/wip` frontmatter enum is root-scoped.** `type ∈ {audit,triage,qa,spec,
  scratch,design}` matches the wip ROOT files (`EVIDENCE-*` = `audit`, `DIAG-*` =
  `triage`), but `.sos/wip/frames/` carries `type: shape` / `type: frame`. The enum
  does not bind the frames/ subdir.
- **Window instants are CONFIRMED-BY-OPERATOR, not self-derived** (shape `:1581-1586`)
  — *"If a sprint needs to act at the boundary minute, re-derive first."* Immaterial
  to S1-S4 (read-only, unbound); material the moment S5 is pulled in.
- **P-3 has NO CLOCK.** The kit's *"withheld until K-4"* reads as scheduled. The
  ruling's words (`RULING…:21`): *"honest aborts continue with NO clock; the
  successor's landing is the only exit."*

### VERIFIED-AS-CORRECT (do not re-litigate)

12/12 `@`-refs resolve · seats S1-S4 match shape §5.1 exactly · `ADR-007 §7` IS the
K-lane build plan · four-rung predicate faithful to frame `:212-219` · RF-1 / RF-2 /
CR-2 / P-3-channel-not-dark faithful · window dates match shape `:1575-1576` exactly
and are internally coherent with a wound-restart at ~2026-08-11T10:58Z (floor +3d,
ceiling +7d) · monorepo IS on `fix/wss-wildcard-scope-bypass-closure` and is **NOT**
an ancestor of `origin/main` (probe: `merge-base --is-ancestor` → false) — the
PIN-origin/main instruction is **live and load-bearing** · asana squash convention
CONFIRMED 6/6 single-parent · the terraform scar is LIVE (`observability_alarms.tf`
modified, `warmer_cache_degraded_alarm.tf` untracked, right now) · myron / iris /
pythia resolve in neither list.

*Read-only against every target except this appended section. No existing line edited.
Falsification pathway for this addendum: re-run the four probes in C-1/C-2/C-3/C-7 at
paste time; if `ari rite pantheon | tail -n +2 | wc -l` ≠ 24, or `.claude/CLAUDE.md`
has reverted to the `releaser` roster, or `terraform/services/asana/` no longer
resolves at autom8y `origin/main`, the corresponding correction is void and the kit's
original line stands.*

---

## REVISION 3 — adversary corrections absorbed (2026-08-12 ~16:50Z)

The adversary's line citations (`:23`, `:37`, `:101`, `:178`) were taken against
the PRE-revision-2 file — a read/patch race, disclosed rather than hidden. Its
C-1 (brittle `wc -l` probe), C-2 (wrong fallback verb), C-9 (PT-07), C-10
(`/sprint` count) were ALREADY fixed at revision 2 and independently reproduce
potnia's D11/D2/D6/D3. Its **new** findings are absorbed at revision 3:

- **C-2 rationale upgraded** — `ari sync` is not merely the wrong verb, it is
  **destructive** (regenerates the channel dir, auto-removes orphans). Warning
  strengthened; the same defect flagged at `shape:1060`.
- **C-5** — OS-2 (UV-P-4) restored to the operator surface; it **soft-blocks
  S3's external half and S3 is in this sprint**.
- **C-6** — a UV-P register added: UV-P-4 = S3 exit criterion, UV-P-5 = S4 exit
  criterion. They are exit criteria, not background.
- **C-7** — **S4's inherited premise FALSIFIED at source.** The shape says
  `terraform/services/asana/` does not exist at autom8y `origin/main`; it does
  (17 entries). UV-P-5 stands open for a different reason. Carried so S4 does not
  hunt a directory that is right there.
- **C-8** — CR-1's custom-field limb restored (acquired-dependency, a *different*
  mechanism from the notification limb).
- **C-11 cluster** — charter citation form corrected (core items 4/5 live at
  `:54`/`:55` inside document §3); `.know/scar-tissue.md` marked EXPIRED (~20d,
  hook fires); P-3 restated as **NO clock** rather than "until K-4"; `/sprint`'s
  own STATE-OF-PLAY pre-flight prompt pre-announced.
- **Scar corrected** — the `.sos/wip` frontmatter enum is ROOT-scoped;
  `.sos/wip/frames/` legitimately carries `type: frame` / `type: shape`.

### ⚠ THE HAZARD A COLD SESSION MUST BE TOLD ABOUT

The frame and the shape — **both `@`-referenced above as "the decision space"** —
give **incompatible treatments of charter gate (b)**. Frame `:122-128` rules the
customers limb OUTSIDE-as-scoped and discharges it with a **named observable
tripwire** ("it becomes customer-facing the moment any delivery lands where a
client can see it — at that moment gate (b) fires and the work stops at the
operator"). Shape `:368-374` replaces that with an **undecidable modal** (the
follower set is mutable, therefore treat the gate as firing). The adversary ruled
the shape's form **OVER-EXTENDED — it proves too much**: the identical argument
applies to the Slack rail the shape endorses, and charter `:55`'s own
*"INCLUDING reversible decisions that set patterns others will copy"* clause
exists precisely to refuse the *"but it might matter later"* species of argument.

**RESOLVED 2026-08-12 by operator ruling — THE SHAPE'S MODAL GOVERNS.**
Record: `.ledge/decisions/RULING-operator-gate-b-modal-2026-08-12.md`. The
frame's tripwire structure at `:122-128` is SUPERSEDED as the governing reading
and remains as the historical of-record (charter §7: fresh ruling, never an edit).
The adversary's OVER-EXTENDED verdict is **overruled by operator word** — the
adjudicator's prerogative; the critique stands in the record, the ruling stands
over it. **Practical effect on outcomes: NONE** — all three Asana write classes
were reserved under both readings. Seats: obey the modal, do NOT re-derive it.

⚠ **STILL OPEN — the SCOPE question the ruling does not answer.** Applied
consistently, the modal keys on a property the `#account-health` Slack rail also
has (a workspace admin can add a guest exactly as an Asana admin can add a guest
follower) — and Slack is the ONLY delivery rail verified live. Two readings,
**neither recorded as decided**: (a) modal scoped to Asana writes, Slack
distinguished as an opted-in internally-controlled channel already carrying
automated posts 6×/day → delivery stays autonomous; (b) modal applied uniformly
→ **the only working rail becomes operator-gated**, one release per publication.
**S3 must present BOTH and assume NEITHER** — its subject is the rails. Carry it
to the PT-02 briefing beside the CR-2 §6-T1 under-call.

**Charter critique verdicts** (rite-disjoint adversary, self-attestation MODERATE
— single grader, no second): CR-1 gate-(a) principle **OVER-EXTENDED** (outcome
unaffected; over-determined) · gate-(b) undecidability **OVER-EXTENDED, proves
too much** (not load-bearing; strike it and all three rulings survive) · CR-2
**SOUND**, with an under-call — charter **§6 T1** (credential-gate breadth,
explicitly OPEN, broad reading STANDS) is uncited, and CR-2's outcome is robust
under **both** the broad and the narrow R29 reading. **That belongs in the PT-02
briefing**, because it is the difference between "SB-2 is fully reserved" and
"reserved down to a rendered view behind an auth boundary you already own" ·
frame §4 priority-domain ruling **SOUND**.
