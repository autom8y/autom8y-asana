---
title: "ADR — FORK-1 Inheritance Mechanism (decision-charter-inheritance S2)"
id: ADR-fork-1-inheritance-mechanism-2026-07-30
type: ADR
initiative: decision-charter-inheritance
sprint: S2 (WS-B inheritance-wiring)
status: accepted
ratification: AUTO-RATIFY (charter §5 + substrate P8 adversarial-delegation corridor; reversible + non-sensitive per the CORRECTED arm-scoped reversibility table §5)
route: AUTO-RATIFY (dissent archived VERBATIM §11; surfaced as HEADS-UP, not an operator gate)
date: 2026-07-30
author: architect (10x-dev)
rite_disjoint_critic: arch-adversary (arch) — VERDICT PASS-WITH-CONDITIONS, iter 1
budget_pricer: capacity-engineer (thermia)
self_grade: MODERATE  # self-ref-evidence-grade-rule; reach beyond CC is UNVERIFIED per DEFER-2
supersedes: none
resolves_fork: FORK-1 (inheritance mechanism — the initiative's one genuine architecture decision)
references:
  - .ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md   # S1 record; fence L48-65 (merging via PR #290)
  - .sos/wip/frames/decision-charter-inheritance.md                    # frame §4 WS-B, §5 FORK-1, §8 T5
  - .sos/wip/frames/decision-charter-inheritance.shape.md              # shape S2 block L148-194
---

# ADR — FORK-1 Inheritance Mechanism

> **Route note (read first):** This ADR is ratified by the AUTO-RATIFY corridor,
> not by an operator gate. FORK-1 is reversible (git-revertible for every arm this
> ADR actually selects — see §5 erratum) and non-sensitive (no customer-visible
> surface, no credential/security touch, no spend). Escalating a reversible +
> non-sensitive decision to an operator gate would itself contradict the charter §5
> this initiative ships. The auto-ratified packet — with the arch-adversary dissent
> archived VERBATIM (§11) — is surfaced as a HEADS-UP, not a gate.

## §1 Context

**The question (FORK-1):** By what mechanism do future sessions and agent dispatches
AUTOMATICALLY inherit the ratified decision-space charter with ZERO per-prompt
inlining, referencing the S1 charter-of-record as single source of truth — never the
private memory?

**Why now:** The decision-space charter was ratified 2026-07-29 and, until S1, lived
ONLY in the operator's private auto-memory (single-operator, single-harness,
un-versioned). S1 landed the charter-of-record at
`.ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md` (commit `7cbacb70`,
153L/10706B; byte-verbatim core fence **L48–65**, core body L49–64 = 3001B / 16 lines;
merging via PR #290 at authorship). FORK-1 wires the mechanism by which that record —
NOT the private memory — is auto-inherited.

**North Star (realization predicate, verbatim from shape L184):** "A fresh
session/dispatch containing NO charter text in its prompt demonstrably operates under
the charter — honors the two gates, escalates per the sensitive list — because
inheritance carried it (a BEHAVIORAL receipt, observed on a real dispatch, not a
file-exists check); AND the charter-of-record is landed at constitution level; AND at
least one surface beyond this repo consumes it."

**Q2-CRUX ruling (steers the recommendation):** the predicate polices "NO charter text
in its **prompt**" — charter text arriving in **context via inheritance** is the
SUCCESS condition, not contamination. Verbatim-inline (C2) and transclusion (C3) do
NOT trivialize LEG 1. Pointer under-drive is empirically decidable at S4 (PT-04
discriminating canary). A STAGED ratification — pointer-first with verbatim/transclusion
as the S4-falsification fallback — is legitimate; do not anchor to a-priori conviction
in either direction.

## §2 The Completed Slate (3 bases + C1–C5 composites + X1 + CH-01 dispositions)

Evidence-grade legend (reach-census vocabulary): **VERIFIED** = directly probed this
initiative; **OBSERVED** = present live in the S2 dispatch but not independently
census-probed; **UNVERIFIED** = no census proved it.

### BASE MECHANISM 1 — INSCRIPTION (CLAUDE.md / GEMINI.md chain)

Carry the charter (as pointer / verbatim core / digest — see C1–C3) in the harness
inscription chain, which loads system-injected into every session and dispatched agent.

| Axis | Pricing | Grade |
|---|---|---|
| REACH | Every CC session + every CC Task-dispatched agent (this S2 dispatch is the self-witness — the full 5-level chain is in the dispatched agent's context). Gemini needs the separate GEMINI.md surface. iris / non-operator seats / other harnesses: UNVERIFIED per DEFER-2. | OBSERVED (CC) / UNVERIFIED (beyond-CC) |
| DURABILITY | Survives clone + kit propagation **only for git-tracked, regeneration-preserved levels**. Levels 2 (`a8/`) and 4 (`repos/`) are gitignored-by-policy (VERIFIED). Level 5 (autom8y-asana) is tracked, BUT is a **generated, rite-dependent** artifact — "tracked" is necessary, NOT sufficient (CH-02). The durable locus is the satellite-owned `user-content` region (VERIFIED preserved — §6/§7). | VERIFIED |
| BUDGET (T5) | Chain baseline ≈622L / 31,091B / 7,773 tok. Added cost is arm-dependent — see §3. Record-as-SoT permits pointer-referencing. | VERIFIED (sizes) |
| GOVERNANCE | Human edits are git-diffable on tracked levels; BUT the dominant overwrite risk is **`ari sync` / rite-switch regeneration**, which clobbers directly-inserted lines outside satellite-owned regions (CH-02). Frame §7 fences out linters/hooks/CI policing charter conformance → drift management is manual vigilance for non-preserve placements. | VERIFIED |

**Failure modes:** (a) placement in a gitignored level → silent non-durability; (b)
placement in a `regenerate=true` / `knossos`-owned region → silent regeneration-clobber
(the sre-vs-10x-dev roster variance the adversary witnessed at V7); (c) harness-specific:
a CC-only edit silently fails the Gemini seat (C7); (d) pointer arm guarantees the line
LOADS, not that the agent ACTS on it — behavioral efficacy is S4-decidable.

**What would have to be true to win:** the North Star's BEHAVIORAL bar is met by a
regeneration-safe chain line a charter-naive dispatch reliably honors, at a
git-revertible + preserve-owned locus.

### BASE MECHANISM 2 — MEMORY (auto-memory 2a / agent-memory 2b)

Two structurally distinct sub-surfaces; must not be conflated.

- **2a auto-memory** — where the charter lived pre-S1 (`~/.claude/projects/.../memory/`).
  The status-quo surface the initiative exists to retire.
- **2b agent-memory** — VC-shared, per-agent (`.claude/agent-memory/{agent}/`).

| Axis | Pricing (2a / 2b) | Grade |
|---|---|---|
| REACH | 2a: main CC session index (MEMORY.md) AND — per census UNKNOWN-1 (dependency-analyst own-observed 2026-07-30) — the operator's 22-entry memory index was ALSO carried into a Task-dispatched agent's context. Treat 2a reach into dispatched agents as **OBSERVED-PRESENT** under current harness behavior; this **SUPERSEDES** the earlier "does not reach dispatched agents" verification (stale-verification correction, never-confidently-wrong). 2b: only the specific agent whose dispatch loads it. Both CC-only. | OBSERVED-PRESENT (2a→dispatch; supersedes stale VERIFIED) |
| DURABILITY | 2a: NOT git-tracked (VERIFIED not-a-repo) → no clone/kit/diff, **not git-revertible** (§5 erratum). 2b: TRACKED, git-diffable, but per-agent, N-way (N=22 agent-memory dirs this repo). | VERIFIED |
| BUDGET (T5) | 2a MEMORY.md index loads per-session already; 2b loads on the agent's dispatch. | OBSERVED |
| GOVERNANCE | 2a: operator-private, not team-reviewable, amendment reaches one seat. 2b: git-diffable but N-way sync. | VERIFIED (2a) |

**Failure modes:** 2a directly contradicts the mandate ("never the private memory") and
is the anti-pattern being retired; 2b spreads N-way with no single SoT. Standalone,
both fail the single-source-of-truth requirement. **Downstream (UNKNOWN-1):** because 2a
now demonstrably reaches Task-dispatched agents, it contaminates the S4 two-sided-teeth
FAIL leg for BOTH workflow classes (not just sessions) — the C4 sequencing consequence
broadens accordingly (§6 C4).

**What would have to be true to win:** the target is scoped to one operator + one harness
(contradicts the frame's reach ambition); OR 2b is reframed as pointer-only reinforcement
layered on another mechanism (→ C4, not standalone).

### BASE MECHANISM 3 — DISPATCH-TEMPLATE (GOVERNING block in prompt templates)

The demonstrated manual workaround.

| Axis | Pricing | Grade |
|---|---|---|
| REACH | Exactly the dispatches the dispatcher templates; any harness IF wired each. Not automatic. | OBSERVED |
| DURABILITY | Zero as a live prompt block; versioned only if the template is a tracked file. | OBSERVED |
| BUDGET (T5) | Whatever is inlined per dispatch — verbatim core 3001B every dispatch. | VERIFIED (core size) |
| GOVERNANCE | Dispatcher controls entirely; drift undetectable; amendment reaches only updated templates. | OBSERVED |

**Failure mode (structural):** as SOLE mechanism it **definitionally violates the North
Star** — "zero per-prompt inlining" — because it IS per-prompt inlining. It can only
serve as a fallback or a template that references the record.

**What would have to be true to win:** the mandate's "zero per-prompt inlining" is
relaxed to permit automated template-injection — a predicate redefinition only the
operator/frame can authorize (not an architect call).

### COMPOSITES (each distinct on ≥1 axis; map onto frame §8 T5 sub-options)

- **C1 — Inscription-POINTER → record.** Level-5 `user-content` region carries a 1-line
  path + fence citation to the record; the record holds the verbatim core. *Distinct:*
  cheapest budget arm; AP#3-clean (no duplication — record is sole SoT); satisfies
  "never the private memory" cleanly. *Cost:* behavioral efficacy depends on the agent
  actively Reading the pointer (S4-decidable).
- **C2 — Inscription-VERBATIM-CORE-inline.** The 16-line/3001B core placed directly in
  the level-5 `user-content` region. *Distinct:* zero-indirection — behavior-driving text
  in-context without a Read. *Cost:* third byte-source vs the record fence → drift risk,
  and frame §7 fences out the enforcement tooling that would manage it → manual vigilance
  only (C3/CH-03); MATERIAL budget, amplified ×(1+N) per sub-agent dispatch.
- **C3 — Inscription-@import / transclusion of record.** CLAUDE.md transcludes the record
  via harness import syntax — single source, auto-loaded, zero-Read. *Distinct:* combines
  C1's single-SoT with C2's zero-Read. *Cost:* **viability is a platform-behavior claim
  (UNVERIFIED)** — whether the CC loader `@import`s a `.ledge/` file must be probed
  (SVR row-1) BEFORE any use. UV-P-labeled below (§6 C3).
- **C4 — Inscription-pointer + agent-memory (2b) reinforcement.** Universal pointer in
  CLAUDE.md PLUS a pointer entry in dispatched agents' VC-shared agent-memory. *Distinct:*
  redundant reinforcement. *Cost:* N-way (N=22 dirs); mandate-compatible ONLY as
  pointer-only, reinforcement-never-load-bearing (adversary Q6).
- **C5 — Multi-harness inscription (CLAUDE.md + GEMINI.md).** Wire the pointer into both
  observed chains. *Distinct:* extends reach to the Gemini seat (dual-harness measured
  1.957× by capacity-engineer). *Cost:* DEFER-2-held; two surfaces to sync; iris/other
  still UNVERIFIED.

### CANDIDATE-BEYOND-SLATE — X1 (hook-injected charter pointer), COMPLETE 4-axis row (C6)

A session-start hook (settings.json, git-tracked) programmatically injects the charter
pointer — the vector `inscription-architecture` uses for git-state injection.

| Axis | Pricing | Grade |
|---|---|---|
| REACH | Fires on CC SessionStart → reaches fresh top-level CC sessions (good for the OS-2 {B} session class). Whether SessionStart re-fires for Task-dispatched sub-agents is UNVERIFIED (mirror-image of the agent-def-file gap). Beyond-CC UNVERIFIED. | UNVERIFIED (sub-agent + beyond-CC) |
| DURABILITY | settings.json is git-trackable → survives clone, git-diffable, git-revertible. Whether the hooks block is regeneration-preserved (channel-regenerated?) is UNVERIFIED. Harness-specific (CC hooks ≠ Gemini). | OBSERVED / UNVERIFIED (regen) |
| BUDGET (T5) | Injects once per session at start; cost = emitted payload (pointer ~51 tok or core ~750 tok), NOT amplified per sub-agent (unlike C2). Programmatic → can be conditional. Potentially cheapest-at-scale. | OBSERVED |
| GOVERNANCE | Edited in settings.json (git-diffable, drift-detectable). BUT hook logic is code → higher failure surface; a broken hook fails silently/noisily. Frame §7 may fence a *drift-checking* hook out of the S2 envelope (a *delivery* hook is the receipt's enabler, not conformance policing — the adversary's CH-03 distinction). | OBSERVED |

**Disposition:** DISTINCT 4th base primitive. Enters the slate for ENUMERATION; its
SELECTION requires frame confirmation (the frame fixed the pre-authorized decision space
at three) AND frame §7 may fence hooks out of the tooling envelope. **Not selected**;
enumerated complete per C6.

### CH-01 / C1 — Two further static-text vectors, enumerated-and-disposed

- **Y1 — Agent-definition files** (`.claude/agents/*.md`, system-injected per dispatch):
  DISPOSED-OUT standalone — reaches Task-dispatched agents but NOT fresh top-level
  sessions (fails OS-2 {B} session class alone); N-way fanout across every agent file;
  same channel-regeneration clobber class as CLAUDE.md rite blocks. Could serve C4-style
  reinforcement but dominated by 2b for that role.
- **Y2 — Preloaded skills** (agent-frontmatter `skills:` lists / `skill_policies`):
  DISPOSED-OUT standalone — automatic only for agents whose preload list names it (N-way
  config fanout, not universal-by-default); mixing a governance-charter into the
  reference-knowledge substrate is a category error against the skills' own boundary
  statements; heaviest authoring ceremony (SKILL.md + manifest) for a 1-line pointer.
  Genuinely distinct; loses on simplicity (charter §1) + category-cleanliness. Possible
  ecosystem-altitude fleet reinforcement vector (out of this repo-scoped S2's scope).

## §3 T5 Budget Pricing (capacity-engineer, thermia; tokens ≈ bytes/4 ±20–30%)

Baseline chain: **31,091 B / 7,773 tok** (the denominator for all percentages).

| Arm | Marginal cost | % of baseline | Note |
|---|---|---|---|
| C1 pointer (1-line) | 51 tok | 0.66% | NEGLIGIBLE |
| C1 pointer (2-line) | 77 tok | 0.99% | edge |
| C1 pointer (3-line) | 97 tok | 1.25% | |
| C1 conditional record-Read | +2,944 tok | — | **UNRESOLVED 20× probability spread**: P=5% → +147 tok amortized; P=100% → +2,944 tok. This is the pointer-under-drive fulcrum S4 decides. |
| C2 verbatim-core | 750 tok | 9.65% | MATERIAL; ×(1+N) per sub-agent dispatch (10-dispatch session = 8,250 tok); 3-site amendment fanout |
| C3(a) core-import | 750 tok | 9.65% | same as C2, 2-site fanout; **viability UNVERIFIED** |
| C3(b) whole-record import | 2,677 tok | 34.4% | |
| C4 marginal | 51–97 tok/dispatch | — | N=22 agent-memory dirs; dispatch-ratio unpriced |
| C5 dual-harness | 1.957× | — | GEMINI chain VERIFIED 95.7% parity; C2-dual = 1,500 tok (19.3%) |
| Digest 8-line | 222 tok | 2.85% | drops RATIFIED-INFERENCES + watch-triggers → re-litigation risk |
| Digest ultra | 148 tok | 1.90% | same re-litigation risk; neither digest is <1% |

**Digest caveat (capacity-engineer):** both digest floors drop the RATIFIED-INFERENCES
line + watch-triggers, reopening "is §6 hard?" — exactly the frame §8 T5 re-litigation
risk. Neither digest beats C1 pointer on cost OR on fidelity.

## §4 Decision — STAGED RATIFICATION

**Selected: C1 (inscription pointer) as the ratified S2 build, staged with C2 as the
pre-authorized S4-falsification fallback.**

1. **Primary (S2 build):** **C1 — inscription POINTER, 1-line**, placed in the
   satellite-owned `user-content` region of level-5
   `.claude/CLAUDE.md`, referencing the record fence
   `CHARTER-decision-space-of-record-2026-07-30.md` **L48–65** (never `memory/`, C7
   standing). Cheapest (51 tok / 0.66%, NEGLIGIBLE), AP#3-clean (record is sole SoT),
   regeneration-safe (VERIFIED slot §7). **Charter-coherent by construction** — it
   dogfoods the charter it ships: §1 (simplicity as the route to trust), §2 (a simpler
   thing needs less proof), §3 (ship the honest version, do not gold-plate).

2. **Independent verification that licenses autonomy (charter §6):** the **S4 PT-04
   discriminating canary** empirically decides whether pointer-drive is sufficient — a
   charter-naive dispatch that Reads the pointer and then honors the two gates. C1 is
   ratified as *testable-at-S4*, NOT *assumed-sufficient*. Autonomy is void without this
   verification (shape L182).

3. **Pre-authorized S4-falsification fallback (decisive runner-up):** **C2 —
   verbatim-core inline** (same `user-content` slot), VERIFIED-viable, triggered IFF
   PT-04's PASS leg falsifies pointer-drive (agent loads the pointer but does not act on
   it). No re-ratification needed — this ADR pre-authorizes the fallback. C2 carries the
   §7-fenced drift cost (manual vigilance; third byte-source vs the record fence) —
   priced plainly per C3/CH-03.

4. **Conditional secondary fallback (UV-P, NOT ratified):** **C3 — @import/transclusion**,
   usable ONLY after a build-time CC-loader probe (docs-cite + live fixture) proves
   `@import` of a `.ledge/` target works through the chain. C3 is **eliminated as the
   decisive runner-up** (C2 dominates: VERIFIED-viable, same 750 tok as C3(a); C3(b)
   whole-record 2,677 tok/34.4% is worse) — therefore per C3/CH-05 a UV-P label suffices
   and NO pre-ratification loader probe is required. **C3 is NOT ratified on any unprobed
   premise** (this keeps the dissent's BLOCK-trigger un-tripped).

   `[UV-P: the CC CLAUDE.md loader @imports a .ledge/ target file through the inscription chain | METHOD: deferred-to-build-loader-probe (docs-cite + live fixture) | REASON: C3 is eliminated as decisive runner-up on budget+viability axes (C2 dominates); C3 loader viability need not be probed pre-ratification per CH-05, but MUST be probed before ANY future C3 use]`

**Staged-fallback ladder:** C1 pointer → [S4 PT-04 falsifies pointer-drive] → C2
verbatim-core (decisive, pre-authorized) → [only if a zero-Read single-SoT arm is later
wanted AND the loader probes viable] → C3 transclusion.

**Rejected / held:** digest floors (dominated by pointer on cost AND fidelity;
re-litigation risk); C4 (optional pointer-only reinforcement, never load-bearing);
C5/Gemini (DEFER-2-held; named as silent-failure in §9); X1 hook (enumerated; selection
needs frame-confirmation + §7 envelope check); BASE 2 standalone (contradicts mandate);
BASE 3 standalone (IS the per-prompt inlining the mandate retires).

## §5 Reversibility Erratum (C5 / CH-06) — arm-scoped table

**Erratum:** shape L646 ("ALL THREE legs are REVERSIBLE — git-revertible at one-surface
scope") and the S2 irreversibility gate that repeats it (shape L180) are **FALSE for the
2a auto-memory arm**: 2a is not in git (VERIFIED not-a-repo) → **not git-revertible**;
reversal depends on a pre-edit backup that nothing currently mandates. Corrected by this
ledgered citation.

| Arm | Git-revertible? | Auto-ratify corridor? |
|---|---|---|
| Inscription tracked+preserve (C1/C2, `user-content`) | YES | YES |
| Inscription templates/kit-side | YES | YES |
| Agent-memory 2b (C4) | YES | YES |
| X1 settings.json hook | YES | YES |
| **2a operator auto-memory** | **NO (backup-only take-back)** | **NO — requires pre-edit backup receipt to re-qualify under charter gate (a); else out-of-corridor** |

**Auto-ratify re-derivation on the corrected table:** the mechanism this ADR selects
(C1, with C2 fallback) touches ONLY git-revertible + preserve-owned inscription arms →
the reversible + non-sensitive predicate holds → the AUTO-RATIFY route survives intact.
The single 2a-touching step (the C4/CH-04 digest pointer-ization, §6) is reclassified as
requiring a pre-edit backup receipt, keeping even that step honest under charter gate (a).

## §6 Binding Build Constraints on principal-engineer (conditions C1–C7, authoritative numbering)

- **C1 — vectors disposed.** Agent-definition-files (Y1) + preloaded-skills (Y2)
  enumerated-and-disposed above (§2). Satisfied in-ADR.
- **C2 — regeneration-safe slot NAMED + survival-SVR build-blocking.** The insertion locus
  is the **satellite-owned `user-content` region** of level-5 `.claude/CLAUDE.md`
  (`KNOSSOS:START user-content` … `KNOSSOS:END`). Preservation is VERIFIED at the design
  level (§7 SVR-2/3/4: manifest declares `user-content: owner: satellite`; `pipeline.go:292`
  routes satellite-owned regions to `wouldPreserve`; template stamps "preserved during
  sync"). **BUILD-BLOCKING receipt:** before opening the S2 PR, principal-engineer runs an
  actual `ari sync` / rite-switch regeneration cycle and produces an SVR bash-probe that the
  wired charter line SURVIVES verbatim in the `user-content` region. "Tracked at level 5"
  alone is NOT sufficient. **Reach caveat (name in the receipt):** worktree sessions load
  the *branch's* committed CLAUDE.md; a line landed on the target repo's level-5
  `user-content` reaches worktree dispatches via the parent-repo ancestor chain (OBSERVED
  this dispatch) but a worktree's own checkout carries the line only once its branch does.
- **C3 — drift pricing / loader probe.** C2 is the recommended fallback (not C3), so state
  plainly (done, §4): frame §7 excludes drift-enforcement tooling → C2's residual cost is
  manual vigilance + a third byte-source vs the record fence. C3 is UV-P-labeled and NOT
  ratified; ANY future C3 use requires the CC `@import` loader probe (docs-cite + live
  fixture) FIRST.
- **C4 — control-contamination sequencing (main-thread ruling + UNKNOWN-1 delta, recorded).**
  OS-2 {B} requires N=2 across BOTH Task-dispatch AND fresh-session classes → "Task-dispatch-only"
  is NOT an available discharge. **UNKNOWN-1 delta (census, 2026-07-30):** the adversary's
  CH-04(iii) proposed a clean control class of "Task-dispatched agents (2a does not reach them)"
  — that route is now **FALSIFIED by fresh observation**: 2a reaches dispatched agents too. The
  adversary's *second* horn survives and is now the SOLE discharge: **the 2a operator-auto-memory
  charter digest MUST be pointer-ized/retired BEFORE ALL S4 control runs — BOTH the session class
  AND the Task-dispatch class** (either would otherwise inherit the charter digest via the memory
  index and false-GREEN the FAIL leg). **This edit is the MAIN THREAD's standing memory-maintenance
  duty, NOT an agent edit and NOT an operator gate** (the memory directory is main-thread-maintained
  by standing instruction; the memory file's own lineage line "NOT yet landed as a shared repo
  artifact" becomes FALSE at S1 merge, so the update is due as truthfulness-hygiene regardless).
  **Sequence (binding):** S1 merged → S2 wiring landed → main-thread 2a digest pointer-ization
  (+ pre-edit backup receipt per C5) → S4 controls (both classes). This binds FORK-3's
  observation-class choice.
  - **Clean-control construction available (design input to FORK-3, NOT a mandate — census
    class-3 receipt):** worktree sessions fork SEPARATE, fresh auto-memory directories (observed:
    a `-wt-mcp-s5pr` worktree forked its own memory dir; parent memory does not cross). So S4 MAY
    instead construct control-vs-treatment as two worktree checkouts — one on a branch WITHOUT the
    wiring commit (control) and one WITH it (treatment) — memory-clean by construction on both
    arms, sidestepping the 2a-retirement dependency for the experiment itself. Recorded as an
    option for FORK-3 protocol design; the 2a pointer-ization remains due as wiring hygiene
    regardless.
- **C5 — reversibility erratum carried.** §5 table + auto-ratify re-derivation. Satisfied
  in-ADR.
- **C6 — X1 row completed.** §2 X1 four-axis row complete; X1 not selected; had it been,
  the frame-confirmation surface would precede ratification. Satisfied in-ADR.
- **C7 — DEFER-2 Gemini silent-failure named.** §9 census names it explicitly as
  UNVERIFIED-reach (not merely "beyond-CC unverified").

## §7 SVR Receipts (load-bearing platform-behavior claims, co-emitted)

```yaml
# SVR-1 — charter record form + fence
structural_verification_receipt:
  claim: "the S1 charter-of-record at commit 7cbacb70 is 153 lines / 10706 bytes with a byte-verbatim core fenced at L48-65, core body L49-64 measuring 3001 bytes"
  verification_method: bash-probe
  verification_anchor:
    source: "git show 7cbacb70:.ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md | wc; awk 'NR>=49&&NR<=64' | wc -c"
    command_output_verbatim: "lines=153 bytes=10706 ... core fence lines 49-64 byte size: 3001"
    exit_code: 0
    claim: "the record's size and fence coordinates are present-tense facts of the landed git object, grounding the pointer target and the T5 verbatim-core cost"
```

```yaml
# SVR-2 — user-content region declared satellite-owned in the live manifest
structural_verification_receipt:
  claim: "the autom8y-asana live inscription manifest declares the user-content region as owner satellite, the preserve class"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.knossos/KNOSSOS_MANIFEST.yaml"
    line_range: "L40-L41"
    marker_token: "user-content:\n        owner: satellite"
    claim: "the manifest assigns the charter's intended insertion region to the satellite owner class, the precondition for regeneration-preservation"
```

```yaml
# SVR-3 — pipeline routes satellite-owned regions to preservation
structural_verification_receipt:
  claim: "the inscription sync pipeline routes satellite-owned regions to the preserve set rather than regenerating them"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8t/knossos/internal/inscription/pipeline.go"
    line_range: "L292-L293"
    marker_token: "if region.Owner == OwnerSatellite {\n\t\t\twouldPreserve = append(wouldPreserve, name)"
    claim: "the code path establishes that a charter line inside a satellite-owned region is preserved across a sync cycle, not clobbered — the mechanism C2 depends on"
```

```yaml
# SVR-4 — chain levels 2/4 gitignored-by-policy (durability trap)
structural_verification_receipt:
  claim: "inscription chain levels 2 and 4 are gitignored by enclosing-repo policy, not merely untracked"
  verification_method: bash-probe
  verification_anchor:
    source: "sed -n '1p' Code/.gitignore ; sed -n '1,6p' a8/a8/repos/.gitignore"
    command_output_verbatim: "/*\n# KNOSSOS:START channel-ignores ... .claude/"
    exit_code: 0
    claim: "the two mid-chain levels are affirmatively excluded from version control, so a charter line placed there would be non-durable and non-diffable — the trap the recommendation avoids by selecting level 5 user-content"
```

```yaml
# SVR-5 — BUILD-BLOCKING SURVIVAL RECEIPT (§6 C2, adversary CH-02) — principal-engineer, S2 build, 2026-07-30
# The wired C1 pointer SURVIVES an actual ari inscription rite-regeneration cycle byte-verbatim in the satellite-owned user-content region.
structural_verification_receipt:
  claim: "the C1 charter pointer wired into the level-5 .claude/CLAUDE.md user-content region SURVIVES an actual `ari inscription sync` regeneration cycle byte-verbatim — the satellite-owned region is PRESERVED while the regenerate-owned regions are rewritten. 'Tracked at level 5' is proven sufficient AT the user-content locus specifically, not merely necessary."
  verification_method: bash-probe
  verification_anchor:
    source: "cd <WT>; grep -n 'Governing decision-space charter' .claude/CLAUDE.md  [PRE] ; ari inscription sync --channel claude --project-dir <WT> ; grep -n ... [POST] ; awk '/START user-content/,/END user-content/' | shasum -a 256  [region-body hash, PRE vs POST]"
    command_output_verbatim: |
      PRE-SYNC grep  → 101:**Governing decision-space charter (ratified 2026-07-29):** ... never the operator's private memory.
      SYNC           → "Synced context file (v326)  Regions updated: 11 (execution-mode, model-override, el-primo-status, quick-start, agent-routing, commands, agent-configurations, platform-infrastructure, know, hierarchy-map, user-content)  Backup: .knossos/backups/CLAUDE.md.2026-07-30T13-03-54Z"  exit_code 0
      POST-SYNC grep → 68:**Governing decision-space charter (ratified 2026-07-29):** ... never the operator's private memory.
      user-content region-body sha256 PRE == POST == d80fe3b21823fbe96f6ab72e95bfef9187ebd82cc4b9e26e0cedeb312b47d1ab
    exit_code: 0
    claim: "empirical discharge of the §6 C2 BUILD-BLOCKING receipt and the adversary's CH-02 BLOCK-trigger: the pointer line is present PRE (L101) and POST (L68, line-shift = regenerate regions above it changing size) and the region body hash is IDENTICAL across the cycle → byte-verbatim preservation. The C2 falsification pathway (line clobbered → STOP, no commit) did NOT fire. Pre-edit dry-run corroborates the mechanism: 'Would preserve 1 regions: ~ user-content'."
  sandbox_discipline:
    probe_scope: "run INSIDE the worktree ONLY — the worktree carries its OWN scoped .knossos (ACTIVE_RITE=sre, NOT a symlink to the main tree). Verified before probing: `ari rite current` from the worktree root == 'sre' ≠ main tree's '10x-dev'; --project-dir pinned to the worktree. The live main-tree rite state was NEVER touched; no `ari sync` was ever run against the main tree."
  regeneration_side_effects_reverted:
    - ".claude/CLAUDE.md — regenerate-owned regions rewritten + model-override/el-primo-status regions added + version 325→326. REVERTED: restored to the pre-sync {HEAD + pointer} snapshot; final `git diff` = the single pointer-line insertion ONLY."
    - ".knossos/KNOSSOS_MANIFEST.yaml — region defs updated by sync. REVERTED: `git restore` to HEAD."
    - ".knossos/backups/CLAUDE.md.2026-07-30T13-03-54Z — sync-created backup. REMOVED (targeted `rm -f`); empty backups dir removed."
    - "NOT touched by sync: .knossos/sync/state.json (clean), .gemini/GEMINI.md (--channel claude scoped Gemini out per C7/DEFER-2). Final `git status --short` = ` M .claude/CLAUDE.md` + `?? ADR-fork-1-...` ONLY."
```

**Carry receipt (S2 exit criterion — "a fresh dispatch carries the charter reference with zero prompt inlining"):**

- **STRUCTURAL at commit time.** The pointer sits in the level-5 satellite-owned `user-content` region. Level-5 injection into sessions **and** Task-dispatches is OBSERVED P9-class this session — the full 5-level inscription chain reached this dispatched agent's context (the §2 BASE-1 REACH self-witness). The wiring is therefore structurally positioned to be carried by inheritance with zero per-prompt inlining.
- **LIVE-PROBE-PENDING-MERGE.** At this commit the wiring exists ONLY on the S2 branch (`docs/dci-s2-inheritance-wiring`); the target repo's level-5 `user-content` carries the line only once the branch lands on main (merge chain S1→S2, PR #290 → S2). A LIVE carry probe — a fresh context-grep dispatch confirming the pointer arrives with ZERO prompt inlining — is a **MAIN-THREAD post-merge step**, run after S2 lands and the live tree reconciles. Honest status: **structural now, behaviorally-observed-post-merge** — NOT overclaimed as live at commit time. (Note the §6 C2 reach caveat: a worktree's own checkout carries the line only once its branch does; the parent-repo ancestor chain still injects the target-repo level-5 into worktree dispatches.)

## §8 Consequences

- **Positive:** the charter auto-inherits at NEGLIGIBLE budget (0.66%) from a single
  source of truth; the placement is regeneration-safe and git-revertible; the design
  dogfoods the very charter it ships; the pointer-under-drive risk is not assumed away but
  handed to an empirical S4 canary with a pre-authorized fallback.
- **Negative / accepted:** if S4 falsifies pointer-drive, the fallback (C2) costs MATERIAL
  budget (9.65%, ×(1+N) per sub-agent) and reintroduces a third byte-source under manual
  vigilance (§7 fences enforcement tooling). This is an accepted, pre-priced contingency.
- **Deferred:** Gemini parity (C5), iris/other-harness reach (DEFER-2), C3 loader viability
  (UV-P), fleet-beyond-repo consumption (WS-C / S10 kit seam).

## §9 DEFER-2 Reach Census (MARKED — dependency-analyst appends)

> **Partial census folded in 2026-07-30 (dependency-analyst delta).** The architect asserts
> the floor; the dependency-analyst census fills the matrix. The full census is appended by
> the build leg below the marker; the delta findings below already change binding conditions
> (UNKNOWN-1 → §6 C4).

- **Honest floor (proven reach, CC-only):** the selected C1 mechanism's proven reach is
  **CC-only — CC main session + CC dispatched-agent, this-repo** — carried via inscription +
  dispatch-template + git-tracked `.ledge`/agent-memory. Auto-memory (2a) is main-session +
  path-keyed, and — per UNKNOWN-1 — **ALSO observed in dispatches** (forward-carry this
  observation; do NOT claim its absence anywhere downstream). This satisfies the predicate's
  "one observed real dispatch" at the CC floor.
- **UNKNOWN-1 (census own-observed, binding-condition-changing):** the census agent's OWN
  Task-dispatched context carried the operator's 22-entry memory index — CONTRADICTING the
  prior "2a does not reach Task-dispatched agents" verification that the slate's 2a REACH row
  and the adversary's C4 discharge route both rested on. Superseded per never-confidently-wrong;
  consequence recorded at §6 C4 (2a pointer-ization now precedes ALL S4 controls, both classes).
- **Gemini silent-failure mode (C7, now HARD-RECEIPTED):** a CC-only `user-content` edit to
  `.claude/CLAUDE.md` does NOT reach the Gemini seat — the parallel `.gemini/GEMINI.md` chain is
  a separate, separately-maintained surface. Census receipts: **GEMINI.md carries a 2-day mtime
  drift vs CLAUDE.md; 86.6% byte-parity at this node; 66 diverging lines; the divergence is
  semantically load-bearing (Task-tool vs auto-activation semantics); and nothing fires when
  regeneration is skipped.** A Gemini session would silently inherit NOTHING. Reach: **UNVERIFIED**
  for Gemini until C5 wires the GEMINI.md `user-content` equivalent. Silent (no error), not loud —
  named per C7. (Note: capacity-engineer's earlier 95.7% dual-harness parity figure was a
  chain-composition measurement; the census's 86.6% byte-parity is a node-level file diff — both
  stand, at different altitudes.)
- **Worktree memory isolation (census class-3, design input):** worktree sessions fork SEPARATE
  fresh auto-memory directories (parent memory does not cross) — the construction basis for the
  clean control-vs-treatment S4 option recorded at §6 C4.
- **iris peer-dispatch / non-operator seats / other harnesses (Codex, OpenCode):**
  **UNVERIFIED** — no census proved reach; DEFER-2 stands.

### Full reach matrix (dependency-analyst, arch co-seat, appended by the S2 build leg 2026-07-30)

Reach matrix (class × mechanism → OBSERVED / VERIFIED / PLAUSIBLE-UNVERIFIED / PROVEN-ABSENT):

| Class | inscription | memory-2a | agent-memory-2b | dispatch-template | hook-X1 |
|---|---|---|---|---|---|
| CC main session (this repo) | OBSERVED | OBSERVED (index injected) | PROVEN-ABSENT | PROVEN-ABSENT | OBSERVED (SessionStart, settings.local.json ×3) |
| CC Task-dispatched agent | OBSERVED (5 levels, P9) | **OBSERVED-PRESENT (Unknown-1: census dispatch's own context carried the 22-entry memory index — supersedes prior verified-absent)** | VERIFIED (git-tracked per-agent) | OBSERVED (this dispatch is proof) | PROVEN-ABSENT |
| CC worktree session/dispatch | PLAUSIBLE-UNVERIFIED (partial; branch-state CLAUDE.md; ancestor chain injects) | PROVEN-ABSENT (path-keyed; -wt-mcp-s5pr forked its OWN memory dir) | PLAUSIBLE-UNVERIFIED (branch-carries) | OBSERVED-by-design | PLAUSIBLE (ancestor settings) |
| Gemini session | PLAUSIBLE-UNVERIFIED (chain present 5 levels; sessions ran Jul-09, stale, a8-keyed) | PROVEN-ABSENT | PROVEN-ABSENT | PLAUSIBLE-UNVERIFIED | PROVEN-ABSENT (different settings schema) |
| iris peer-dispatch | PLAUSIBLE-UNVERIFIED (host-inherited only; bot-native PROVEN-ABSENT — carries SKILL not charter; no iris.md) | PROVEN-ABSENT | PROVEN-ABSENT | OBSERVED (/iris-attestation template) | OBSERVED-conditional (CC host frontmatter) |
| Sibling fleet repo | PROVEN-ABSENT repo-level (shared-ancestor levels DO reach) | PROVEN-ABSENT (per-repo path keys) | PROVEN-ABSENT cross-repo | PLAUSIBLE-UNVERIFIED | PLAUSIBLE (untracked settings.local.json — durability unresolved, Unknown-3) |
| Non-operator seat | PROVEN-ABSENT (untestable; single-operator fleet, 3 Tom email identities; one legacy Contente commit) | — | — | — | — |

HONEST FLOOR: proven reach is CC-only — CC main + CC Task-dispatched agents, this repo, via inscription + dispatch-template + git-tracked .ledge//agent-memory. Auto-memory (2a) is path-keyed, main-session + (per Unknown-1) currently forwarded into dispatched agents; it does NOT cross worktrees, siblings, or harnesses. Everything beyond CC is UNVERIFIED or PROVEN-ABSENT — named, never claimed.

GEMINI SILENT-FAILURE (condition C7, hard receipts): GEMINI.md mtime Jul-28 vs CLAUDE.md Jul-30 (2-day drift, nothing fires when regen skipped); this node 5085B vs 4403B (86.6% parity), 66 diverging lines; divergence is semantic and load-bearing (Task-tool dispatch semantics vs "agents activate automatically"). A CC-only CLAUDE.md edit silently fails the Gemini seat — the confidently-wrong class the charter forbids.

UNKNOWN-1 (supersedes a slate row): the census agent's own Task-dispatched context carried the operator memory index, contradicting prior "2a does not reach dispatches." Consequence absorbed into condition C4: 2a digest pointer-ization precedes ALL S4 control runs (both classes). Clean-control construction available: worktree sessions fork SEPARATE fresh memory dirs (class-3 receipt) — control/treatment as worktree checkouts on branches without/with the wiring.
UNKNOWN-2: Gemini regen trigger unidentified (manual/kit-driven; no automatic firing observed). UNKNOWN-3: settings.local.json is local-only by naming — hook-X1 fleet durability unresolved.

SIBLING CENSUS (UV-P-3 groundwork; S3 shortlist): 12 siblings; all have inscription; 9 have tracked .ledge/decisions. S3 targets — 1. autom8y-data (PRIMARY: most active, 42 recent commits, tracked .ledge, genuine cross-domain consume), 2. autom8y-ads (SECONDARY: tracked CLAUDE.md + tracked .ledge — durable inscription-carry proof case), 3. autom8y-asana-mcp-mount (TERTIARY: tightest coupling, both tracked, low blast radius). Avoid: autom8y-contente-tokens (no ledge, legacy non-Tom seat), autom8y-hermes/-sms (no .ledge/decisions).

## §10 Provenance

- Slate authored 2026-07-30 (architect, 10x-dev), enumeration-only, no recommendation.
- Challenged 2026-07-30 by arch-adversary (arch, rite-disjoint): **VERDICT
  PASS-WITH-CONDITIONS, iter 1**, 7 binding conditions (C1–C7). Full dissent archived
  VERBATIM §11.
- T5 pricing by capacity-engineer (thermia), §3.
- Resolution + recommendation + this ADR authored 2026-07-30 under the 7 conditions + the
  main-thread CH-04 composition ruling.
- **Census delta folded in 2026-07-30 (dependency-analyst, partial):** UNKNOWN-1 (2a reaches
  Task-dispatched agents — supersedes stale verification; broadens C4 sequencing to ALL S4
  control classes, §6 C4 + §2 BASE-2 REACH); Gemini silent-failure hard receipts + worktree
  memory-isolation clean-control option + honest CC-only floor (§9). The recommendation (C1
  pointer + C2 fallback) and the auto-ratify basis are UNCHANGED — the delta moves a build
  constraint and the census, not the mechanism selection. Full census appended by the build leg.
- Auto-ratify basis: reversible (§5 corrected arm-scoped table — selected arms all
  git-revertible) + non-sensitive (no customer surface / credential / spend) → charter §5 +
  substrate P8 corridor. Escalation declined as charter-§5-contradictory.
- Self-grade: **MODERATE** (self-ref-evidence-grade-rule; reach beyond CC UNVERIFIED per
  DEFER-2).
- **Not committed by the architect** — principal-engineer commits the atomic S2 PR with the
  C2 survival-SVR build receipt attached.

## §11 Dissent — arch-adversary Challenge (archived VERBATIM)

> The following is the arch-adversary's FINAL archive-bound dissent, reproduced
> byte-exact. It is the authoritative critique record; the conditions C1–C7 in §6 are
> reconciled against it.

---

# ADVERSARY DISSENT — FORK-1 Slate Challenge (decision-charter-inheritance S2, iter 1)

**Challenger**: arch-adversary (arch, rite-disjoint from 10x-dev authors)
**Target**: FORK-1 pre-recommendation slate (architect, 2026-07-30)
**Scope attestation**: Full slate read end-to-end; frame §4/§5/§8 + UV-P rows, shape S2 block + PT-02 + PT-04 + FORK-1 routing, landed record, and live inscription chain all re-derived by my own probes — no builder receipt inherited. Self-attestation capped MODERATE per self-ref-evidence-grade-rule.

## VERDICT: PASS-WITH-CONDITIONS

The slate is a ratifiable basis for a recommendation **only if** the seven binding conditions in §4 are absorbed into the FORK-1 decision packet. No evidence-grade falsification was found (the BLOCK-class trigger); every VERIFIED claim I spot-checked reproduced exactly under independent probes. The gaps are completeness- and interaction-class, not honesty-class.

## §1 Independent Verification Ledger (own hands, 2026-07-30)

| # | Slate claim | My probe | Result |
|---|---|---|---|
| V1 | 5-level chain sizes 125L/8825B, 121L/5122B, 129L/6901B, 118L/5158B, 129L/5085B | wc -l -c per level | **EXACT MATCH**, total 622L/31091B |
| V2 | Levels 2 and 4 UNTRACKED | git ls-files --error-unmatch + git check-ignore -v | **CONFIRMED — and stronger**: both are actively **gitignored** inside enclosing repos (Code/.gitignore:1 rule /*; a8/a8/repos/.gitignore:4 rule .claude/). Not merely untracked: tracking them would require ignore-rule surgery |
| V3 | Auto-memory not a git repo | git rev-parse in memory dir | **CONFIRMED** (fatal: not a git repository) |
| V4 | Record 153L/10706B at 7cbacb70; fences L48/L65; core L49-64 = 16L/3001B byte-verbatim | wc, sed -n '48p;65p', sed -n '49,64p' | wc + git log | **ALL CONFIRMED**, record TRACKED |
| V5 | Agent-memory (architect/MEMORY.md) tracked in-repo | git ls-files | **CONFIRMED** |
| V6 | Inscription-architecture legomenon path | ls | **CONFIRMED** (INDEX.lego.md + anti-patterns.md + ownership-model.md + content-tone-guide.md + first-principles.md + boundary-test.md present) |
| V7 | *(new, not in slate)* Same-path .claude/CLAUDE.md divergence across checkouts | grep -m1 "agent workflow" in worktree vs main tree | **Worktree = "5-agent workflow (sre)"; main tree = "5-agent workflow (10x-dev)"** — the file is rite-dependent generated content, committed differently per branch state |

Evidence-grade verdict: the slate's VERIFIED/OBSERVED/UNVERIFIED legend is **honest and correctly applied**. Where it errs, it errs conservative (C3 @import marked UNVERIFIED rather than asserted from harness documentation) — the safe direction.

## §2 Challenges

### CH-01 [COMPLETENESS | FLAG] — Two static-text delivery vectors unenumerated and undisposed

The true option space is "any surface the harness auto-loads," and two members are neither in the 3 bases, C1-C5, nor X1: **(a) agent-definition files** (.claude/agents/*.md — system-injected per-dispatch, git-tracked, kit-generated; reaches dispatched agents but NOT main sessions) and **(b) preloaded skills** (agent-frontmatter skills: lists — automatic for listed agents only; bare skills are on-demand and fail "automatic"). Both are probably REJECT-as-standalone (session non-reach; N-way drift — same class as 2b), but option-enumeration-discipline requires them named-and-disposed, not absent. The shape's PT-02 floor ("ALL THREE") is met; the discipline's ceiling is not.
**Falsification pathway**: one line of disposition each in the packet dissolves this challenge.

### CH-02 [GOVERNANCE-DURABILITY | FLAG, condition-carrying — the coordinator's fold-in, independently corroborated] — The inscription arm's primary drift vector is the platform's own sync tooling, and the slate's GOVERNANCE row missed it

My probe V7 + the coordinator's main-thread receipts establish: level-5 .claude/CLAUDE.md is a **generated, rite-dependent artifact** (source declared in the file itself: knossos/templates/; roster block flips 10x-dev<->sre across checkouts; ari rite invoke mutates the Borrowed Agents section; main tree shows it locally modified right now). The slate's GOVERNANCE row ("edited by anyone with write; drift git-diffable + hook-checkable") models **human** edits; the dominant overwrite risk is ari sync/rite-switch **regeneration**, which can silently clobber a directly-inserted charter line. This **does reclassify the inscription arm's durability/governance pricing**: "TRACKED level 5" is necessary but NOT sufficient for durability. The durable insertion locus is one of: (i) the knossos template/kit side (which composes cleanly with UV-P-4's "S10 kit propagation" model and with the frame's "fleet-reachable via kit"), (ii) a sync-preserved section (e.g. ## Project-Specific Instructions — preservation behavior **UNVERIFIED**, SVR-class), or (iii) a chain level ari does not regenerate (which-levels-sync-touches **UNVERIFIED**). A worktree wrinkle sharpens it: worktree sessions load the *branch's* committed CLAUDE.md — a charter line landed on main does not reach a worktree checkout until its branch carries it (the ancestor chain partially mitigates: the parent-repo level 5 still injects into worktree dispatches, as this very dispatch demonstrates — OBSERVED, P9-class).
**Binding condition C2 (below)**: any inscription arm must resolve WHERE the line survives a rite sync before ratification, with an SVR survival receipt at build.

### CH-03 [PREDICATE FIT | FLAG] — C2's drift-management cost is understated because §7 fences out its own mitigation

The slate correctly names C2's third-byte-source risk but prices its mitigation as "git-diffable + hook-checkable." Frame §7 explicitly excludes "linters, hooks, CI gates policing charter conformance." So the tooling that would make a third byte-source safe is out-of-scope by the frame's own line — C2's real governance cost is *manual vigilance only*, which strengthens C1/C3 relative to C2 on the governance axis. (X1-as-delivery is distinguishable: a delivery hook is the receipt's enabler, not conformance policing — but a *drift-checking* hook is squarely excluded.)

### CH-04 [PREDICATE FIT / GATE INTEGRITY | FLAG, condition-carrying — deepest finding] — The two-sided-teeth FAIL leg is contaminated by the status-quo memory surface, and neither slate nor shape names it

On the architect's Q2 crux, both attack directions partially fail as attacks, and a third, unnamed problem emerges:

- **(i) "Verbatim-inline trivializes the S4 receipt" is WRONG as a block.** The predicate's condition is "NO charter text **in its prompt**" — charter text arriving in *context via inheritance* is the SUCCESS condition, not contamination ("because inheritance carried it"). C2 does not defeat LEG 1; T4 polices the observed *prompt*, not the wiring's own payload.
- **(ii) "Pointer under-drives behavior" is REAL but dischargeable.** Inscription guarantees line-load, not action; whether a charter-naive dispatch Reads the pointer and then honors the gates is exactly what PT-04's discriminating canary exists to falsify. Pointer is ratifiable as *testable-at-S4*, not as *assumed-sufficient*.
- **(iii) The unnamed problem — control-arm contamination.** PT-04 requires the no-wiring control to FAIL ("no manufactured RED, no no-op GREEN"). But the operator's auto-memory MEMORY.md index — which loads into every **main session** — *already carries a compressed charter digest including the two gates* (the status-quo surface this initiative exists to retire). For the session workflow-class, the without-wiring control cannot be made charter-naive while 2a persists: the FAIL leg is unconstructible or false-GREEN. The clean discriminating class is **Task-dispatched agents** (2a does not reach them — slate's own VERIFIED reach row). This binds FORK-3's observation-class choice and belongs in the FORK-1 packet as a stated constraint, plus a decommission note: the mandate's "never the private memory" implies pointer-izing/retiring the 2a digest as wiring hygiene (an operator surface — agents do not edit operator auto-memory).

### CH-05 [EVIDENCE-DISCIPLINE | FLAG, condition-carrying] — C3's viability probe must precede ratification, not "defer to build"

C3's whole distinction (single-source + zero-Read) rests on an UNVERIFIED platform-behavior claim: whether the CC loader @imports a .ledge/ file through the chain. That is a cheap, present-tense, deterministic probe (SVR row-1, file-read/bash-probe class). Ratifying C3 — or ranking it as runner-up — on an unprobed premise is exactly the premise-propagation class SVR exists to kill. Deferring to build is acceptable **only** if C3 is eliminated on other axes first.

### CH-06 [GATE INTEGRITY | FLAG, condition-carrying — architect's Q7 confirmed] — The shape's FORK-1 reversibility_ruling is FALSIFIED for the memory arm; the ADR must carry the erratum

Shape L646 rules "ALL THREE legs are REVERSIBLE (git-revertible at one-surface scope)"; S2's irreversibility gate (L180) repeats it. My probe V3: 2a auto-memory is not in git — **not git-revertible**; reversal depends on a pre-edit backup that nothing currently mandates. The slate *caught* this (its DURABILITY row + Q7) — credit where due — but the ruling underwrites the AUTO-RATIFY route, so silent inheritance of the false blanket claim into the ADR would be a gate-integrity defect. Downstream lean: the auto-ratify license survives **only** for arms that are actually git-revertible (tracked-inscription, templates, 2b, X1/settings.json). Any arm touching 2a requires either a pre-edit backup receipt to re-qualify under charter gate (a), or reclassification out of the auto-ratify corridor. Since BASE 2 standalone already contradicts the mandate, the practical cost is one erratum paragraph — but it is mandatory.

### CH-07 [SCOPE | ADVISORY] — No scope creep found; two watch-notes

C5 (Gemini parity) is correctly held at the DEFER-2 boundary — it must not silently absorb into S2 (predicate needs only the observed dispatch class). X1 as handled does not widen scope. The only §7 friction is CH-03's "hook-checkable" phrasing. Fleet-wide rollout: absent. Clean.

## §3 Answers to the Architect's Seven Questions

**Q1 (truncation)**: The slate is not truncated in the shape's sense (PT-02's three-mechanism floor is met with all four axes) but is truncated in the discipline's sense — agent-definition files and preloaded skills need name-and-dispose (CH-01). **X1 handling ruling**: hybrid. X1 MUST sit inside the *challengeable* slate for enumeration completeness (it does, and this challenge has now challenged it), but selecting X1 as the ratified mechanism requires the frame-confirmation surface first, because the frame's fork question fixes the pre-authorized decision space at three. Complete X1's four-axis row now (its BUDGET/DURABILITY entries are sketched, not priced); gate its *selection*, not its *enumeration*. C3 (@import) is correctly in-slate as a composite of BASE 1 — no frame amendment needed for it.

**Q2 (pointer vs behavioral North Star — CRUX)**: Neither arm is disqualified a priori. Verbatim-inline does NOT trivialize the receipt (prompt != context; inheritance-carried text is the success condition) — but it carries the CH-03-priced drift cost. Pointer MAY under-drive — but that is precisely what S4's two-sided canary measures, so pointer is ratifiable as a staged bet with verbatim/transclusion as the pre-named fallback if the canary's PASS leg fails. What actually threatens the S4 receipt is CH-04(iii): the *control* arm, not the treatment arm. The packet must bind the observation class to Task-dispatch (or an operator-scrubbed seat) for the FAIL leg to discriminate.

**Q3 (untracked trap / kit path)**: Confirmed and sharpened — levels 2/4 are not just untracked but *gitignored* (V2): the trap is enforced, not accidental. Level 5 is the only tracked repo-scoped locus. But CH-02 shows "tracked" is not the end of the question: level 5 is a *generated* surface. Whether kit propagation sources from the repo file or regenerates from knossos/templates/ is the real Q3, and it is UNVERIFIED — resolve it (one probe into the template/kit source) before ratification.

**Q4 (harness parity)**: DEFER-2-defer it. Wire CC now; name the GEMINI.md silent-failure mode in the DEFER-2 census with a pointer to C5 as the future hardening arm. Parity is not predicate-required (the predicate needs one observed real dispatch, which is CC-class today). Pulling C5 into S2 would be silent scope absorption.

**Q5 (third byte-source)**: Yes — C2 creates an unmanaged third source, and §7 forbids the enforcement tooling that would manage it (CH-03), so C2's cost is higher than the slate prices. C3 is the only zero-Read arm preserving single-SoT; its viability is a five-minute probe that must precede any ratification in which C3 places (CH-05). If C3 probes viable, the C1-vs-C3 choice becomes the real fulcrum, with C2 dominated on governance.

**Q6 (does agent-memory violate "never the private memory")**: No, on the mandate's letter and provenance. The frame's problem statement defines the anti-pattern as "private single-operator session memory" — that is 2a. 2b is VC-shared, tracked, diffable (V5) — not "private." C4's 2b layer is therefore mandate-compatible **only as pointer-only reinforcement** (any verbatim core in agent-memory files recreates N-way byte-drift, violating single-SoT the same way C2 does, without C2's reach). Never load-bearing.

**Q7 (reversibility-class mismatch)**: Confirmed — the shape's blanket ruling is falsified for 2a (CH-06). It reclassifies the memory arm out of the "git-revertible" class; the auto-ratify route survives unchanged for every arm that is actually in git; the ADR must carry the erratum explicitly so the shape's false blanket claim does not propagate as ratified fact.

## §4 Binding Conditions (become ratification-binding per the intra-sprint gate)

1. **C1 (from CH-01)**: The decision packet enumerates-and-disposes agent-definition-file injection and preloaded-skills as candidate vectors (one-line dispositions suffice).
2. **C2 (from CH-02)**: Any inscription-arm recommendation names the exact regeneration-safe insertion locus (template/kit-side vs sync-preserved section vs non-regenerated level), and the S2 wiring receipt includes an SVR probe that the charter line **survives an ari sync/rite-switch regeneration cycle**. "Tracked at level 5" alone is insufficient.
3. **C3 (from CH-03/CH-05)**: If C3-transclusion places first or second in the recommendation, the CC @import loader behavior against a .ledge/ target is probed pre-ratification (SVR tuple in the packet). If C2-verbatim is recommended, the packet states plainly that §7 excludes drift-enforcement tooling and names the residual manual-vigilance cost.
4. **C4 (from CH-04)**: The packet records the control-contamination constraint: the PT-04 FAIL leg must be constructed on a workflow class the operator auto-memory does not reach (Task dispatch), OR the 2a charter digest is pointer-ized/retired first — surfaced as an operator item, since 2a is operator-private.
5. **C5 (from CH-06)**: The ADR carries the reversibility erratum: shape L646/L180 "all three git-revertible" is corrected to an arm-scoped table; auto-ratify license restated as holding only for in-git arms; any 2a-touching step requires a pre-edit backup receipt.
6. **C6 (from Q1)**: X1's four-axis row is completed; if the recommendation would select X1, the frame-confirmation surface is placed BEFORE ratification, not after.
7. **C7 (from Q4)**: DEFER-2 census in the packet names the Gemini silent-failure mode explicitly (CC-only edit fails the Gemini seat silently) as UNVERIFIED-reach, not merely "beyond-CC unverified."

## §5 Falsification of This Dissent

This verdict revises to **PASS (clean)** if: conditions C1-C7 are shown already satisfied by packet content I have not seen, or the ari sync regeneration probe demonstrates direct level-5 edits are preserved verbatim across rite switches (collapsing CH-02 to ADVISORY). It revises to **BLOCK** if: any spot-checked VERIFIED grade had failed reproduction (none did); the recommendation is issued before the slate absorbs C2/C4/C5 (the three conditions whose omission would embed a defect — a clobbered wiring line, an unconstructible FAIL leg, or a falsified reversibility basis — into the ratified mechanism); or a genuinely distinct load-bearing mechanism surfaces that the slate+X1+CH-01 dispositions do not cover. Concrete re-challenge trigger: present the packet with any of C2/C4/C5 unaddressed and this dissent's severity for that item escalates to BLOCKING at iter 2 (DELTA-scope).

**Grades on my own findings**: CH-02 [STRUCTURAL | MODERATE — self-ref cap; probes V7 + coordinator main-thread receipts are two same-session witnesses, not rite-disjoint corroboration]; CH-04 [STRUCTURAL | MODERATE]; all others [TACTICAL | MODERATE]. Grounding: assessment-methodology P-01/P-08 (construct: "ratifiable slate" = complete option space + honest evidence + gate-compatible interactions; CH-01/CH-04 are underrepresentation findings), P-02 (the slate's validity argument differs for enumeration-use vs ratification-use — hence PASS-WITH-CONDITIONS, not PASS); SVR §1 rows 1/3/4 (probes V1-V7); critique-iteration-protocol §3.4 (no finding here is stylistic; none meets the embed-the-defect BLOCKING bar *at slate altitude* — three would at packet altitude, hence the conditions).

---

*End of archived dissent. Conditions reconciled in §6 (authoritative FINAL numbering C1–C7). The dissent's BLOCK-trigger — "recommendation issued before the slate absorbs C2/C4/C5" — is un-tripped: C2 slot named + preservation VERIFIED + survival-SVR set BUILD-BLOCKING (§6 C2); C4 control-contamination sequencing recorded with the main-thread composition ruling (§6 C4); C5 reversibility erratum carried (§5). C3 is UV-P-labeled and NOT ratified, keeping the "C3 on unprobed premise" BLOCK-trigger un-tripped.*
