---
type: handoff
status: accepted
artifact_id: HANDOFF-coc-phase2-close-2026-08-14
wave: chain-of-custody-closure
phase: 2
seam: PT-04 fan-in → operator
session: coc-phase-2 (session-20260814-090131-e69a1273)
date: 2026-08-14T07:52Z
origin/main: d7560153 (autom8y-asana — identical to the Phase-1 handoff pin; local main carries the Phase-2 paper commits, un-pushed)
landing: EVERYTHING AUTHORED-UNMERGED. Code sprints (CC-5, CC-7) built dark in isolated worktrees, no PR opened; paper committed to LOCAL main only. Nothing merged, nothing deployed, AL-5 window untouched, F-4 fence unbreached.
governs: NOTHING — records Phase-2's honest exit and the operator's decision surface. No operator fork ruled.
self_assessment_cap: MODERATE
---

# HANDOFF — chain-of-custody-closure, Phase 2 close to operator

Phase 2 ran the three OPEN sprints (CC-5 ∥ CC-7 ∥ SEC-002) three-wide, verified every one with a rite-disjoint second read (NCSR 5/5, no critic graded its author STRONG), and halted at PT-04 with **PASS-WITH-CARRIES**. Everything rests authored-unmerged; the two code sprints sit built-dark in isolated worktree branches, PRs **not** opened. Nothing counted done that is not done.

## §1 Rung roll-call — honest exit rung per sprint

| sprint | what | exit rung (honest) | on GitHub? |
|---|---|---|---|
| **CC-5** | RE-1 Tier-1 offers-only warm (lever O-A, priority-first) | **rung-BUILT** (dark @ `6b75279f`, worktree `coc-cc5-tier1-warm`) — merge-ready artifact, NOT a clean AL-5 regime (Amdt A) | no — worktree branch, no PR |
| **CC-7** job | gitleaks local enforcing job (AR-1 mode-1, delegated caller untouched) | **rung-BUILT-DARK** (@ `a922d8f9`, worktree `coc-cc7-gitleaks-gate`) — one rung *under* PR-UP-MERGE-HELD (a PR is a push, F-4 forbids) | no — worktree branch, no PR |
| **CC-7** registration | branch-protection contexts registration | **rung-STAGED** — runbook authored, ordering law (register-AFTER-land), NOT executed and not executable this session | — |
| **SEC-002** | RE-2 grant-chain trace + CF-1 widening | **STRUCTURALLY-VERIFIED** (committed @ `24a52c52`) — RE-2 F-001 stays **HIGH**, un-re-graded per R-2 | committed to local main |
| **CC-1** (carried in) | swap-detector closure (predicate i) | **rung-PR-UP-MERGE-HELD** — advanced from BUILT-DARK on CI observation (R-4); PR #365 OPEN, un-armed, CLEAN | **yes** — PR #365 @ `79d9f4a1` |
| **CC-8** | attest limbs (i)+(iii) | **NOT REACHED — DEFERRED** (limb-iii rides un-landed CC-7; limb-(a) is eunomia's, blocked until both WS-A halves LAND; unreachable under F-4) | — |

PT-04 verdict: **PASS-WITH-CARRIES** (`GATE-coc-pt04-2026-08-14.md`). Entry gate: **PASS-WITH-CORRECTIONS** (`GATE-coc-phase2-entry-2026-08-14.md`).

## §2 AL-5 clock — RE-PRICED at handoff (2026-08-14T07:52Z)

Window opens **~2026-08-15T12:45Z (UV-P — never re-verified own-hands)**. Runway ≈ **28h53m**. **The "one clean regime" prize is almost certainly unpurchasable inside it**: it requires an operator merge word + merge + producer-deploy + a warm cycle, while **F-4 is unlifted and no merge word exists**. CC-5 is merge-**ready**, not merged. Expected outcome absent an early operator merge+deploy word: **O-7a segmentation** — in which case CC-5 stands on its engineering merits (it fixes the receipted zero regardless of clock), not its AL-5 timing. R-9 trap carried: a post-deploy AL-5 green may be the warm fix OR the deploy, not the regime. **This is the operator's runway decision; this session ruled nothing on it.**

## §3 The operator's next-word menu

| word | effect |
|---|---|
| **lift F-4** (fence lift) | permits merges — but re-price against the AL-5 window first (any merge+producer-deploy re-arms it) |
| **"open the held PRs"** (CC-5 / CC-7 / CC-1) | main thread pushes the branch(es) + opens the UN-ARMED PR(s) → PR-UP-MERGE-HELD; never `--auto` (enforce_admins fires on #365 and would on the others) |
| **rule the AL-5 runway** (merge+deploy now, or accept O-7a segmentation) | determines whether CC-5 buys a clean regime or lands on merit |
| **CC-7 registration** (repo-admin) | after the CC-7 job LANDS + is observed reporting, execute `RUNBOOK-cc7-branch-protection-registration-2026-08-14.md` — the second action that makes the gate BITE. Never before land (AR-1 mode-2: a registered-but-unreportable context blocks every merge) |
| **rule the RE-2 remediation** | the `(f) in-repo caller_service allowlist bridge + (a) scope-vocab durable fix` recommendation stays unratified; the exemption-path-has-no-filter framing (below) is the sharpened target |
| **open the governance-integrity finding** (iris scope divergence) | adjacent to SEC-002, NOT self-assigned; the shipped hermes docstring advertises a scope set the runtime token lacks |
| **F-2 (cred-t21 rotation)** | operator-only, runbook-ready, disabled — orthogonal to CC-7 (the BASELINE greens CI, not rotation) |
| **word to eunomia** | limb-(a) Phase-4 attestation — BLOCKED until both WS-A halves LAND (not merely build) |
| **triage R-CC7-1** | the 31 live-at-HEAD baseline-masked findings (0 asana-native-pat) — a follow-on pass, CR-5-bound; out of CC-7's scope |

**Nothing operator-reserved was ruled by any seat.** F-2, F-4, GATE-FORK, the RE-2 remediation + any severity re-grade, the AL-5 runway, the branch-protection registration execution, and every merge word remain yours.

## §4 Load-bearing carries (move a fork or a rung)

- **R-CC7-1 / CH-03** — CC-7's baseline masks 31/49 live-at-HEAD secret-shaped strings, but **0 are `asana-native-pat`** and cred-t21 fossils are **CONFIRMED absent at HEAD** — benign NOW. It **BLOCKS any future "history is clean" claim that drops R-CC7-1**. Attach it to every downstream citation of the green gate.
- **RE-2 stays HIGH (R-2)**; rationale sharpened: the exemption path is one unfiltered `if !business_scoped` (NF-1, population-level not two-SA), a **second boot-time tuple emitter** (`sa_reconciler.py`) restores the bypass every boot (weakens "revocable via tuple removal"), and the 300s D5 TTL is the **sole** revocation bound (no `check_revocation` backstop). Remediation target shifts "review two SAs" → "the exemption path has no filter."
- **CF-1** — determinant YES at registry, now chain-traced registry→OpenFGA(two emitters)→issuance→claim. The "second uncounted population" **inverts** to a population-of-one (`iris`≡`autom8y-hermes`); its OAuth `asana:read` grant is **inert** (iris mints on the SA path). Net: a **governance-integrity defect** (divergent scope truth), not an access-control differential — adjacent finding to open at the operator's word.

## §4b Bounded carries (named, not dropped)

- **FLAG-1 (CC-5)** — the Tier-2 multi-entity mechanism now RESIDES in code (`_resolve_priority_entities`/`_build_warm_order`), fenced by default `("offer",)` + one pinning test + an operator-reserved env lever. The Tier-1/Tier-2 line moved from **structural** ("not built") to **configuration**. Watch-item; keep the lever reserved. `ASANA_STORY_WARM_PRIORITY_ENTITIES` set to a multi-entity list would silently run a fleet reorder.
- **N-1 (CC-5)** — "budget-neutral" is **Asana-scoped only**: 4 net-new CloudWatch `put_metric_data` calls/run. (N-2 one absent-offer cache read; N-3 "success" includes fetch-without-persist in pre-existing untouched files — receipt closes absent-vs-zero, not imputed-vs-fresh.)
- **FLAG-2 (CC-5)** — offer-first roughly halves entities-1–4 coverage (UV-P figures); that cost is emitted log-only, not on an alarmable series. No named-consumer analysis → operator Unknown.
- **gitleaks finding-count instability** — 49/46 findings + a 1924-vs-1838 scan-count anomaly (CH-01): environment-sensitive, direction **SAFE** (baseline is a superset; over-suppression refuted two ways). A future re-run seeing a different count is expected, not a regression.
- **NF-1 fact→UV-P** — "18 of 18 SAs exempt" → "≥18 exempt / 0 business-scoped as of `2159f967`, drifting upward" (origin/main already enrolled `calendly-intake-service`). Property stands; does not move severity.
- **SH-1 DISCHARGED-CLEAN** — six F-001 anchors byte-identical vs origin/main; the branch closure targets a different (`has_scope` wildcard) axis and is ahead of main. Thin fetch-fenced residual: ace/iris registry byte-confirmation on the read surface only (additive drift).
- **CF-4** (regex one-sided, CR-5-uncloseable), **CF-2** (hashless-emitter census UV-P), **CF-7** (mutation-surface UNKNOWN, not entered), **CH-02** (reserve "bite" for merge-block sense) — carried unchanged.

## §5 Deviations from brief (recorded for lineage — pythia seating adjudication)

The brief's Phase-2 seating named `platform-engineer`, `observability-engineer`, `security-reviewer`, `threat-modeler`, `penetration-tester`. None materialised on this seat (pythia diagnosis: **unprojected**, not phantom — they exist in knossos source but a mid-session `ari rite invoke` + CC restart was unavailable). Pythia's fall-through map (a) applied:

- **DEV-1** — SEC-002 bench substituted: `dependency-analyst` (arch) sole writer; threat-modeler STRIDE-lite duty FOLDED into its charge; `penetration-tester` **DROPPED-BY-SCOPE** (SEC-002 is read-only static trace — an active-exploitation seat would breach its own fence; disposition, not a coverage gap).
- **DEV-2** — CC-5/CC-7 advisory seats (platform/observability/security-reviewer) FOLDED as named builder duties, not separate agents.
- **DEV-3** — `penetration-tester` dropped-by-scope (see DEV-1).
- **DEV-4** — the co-seat + restart that would have materialised the real bench was NOT fired (unavailable to this seat); the (a) map is complete without it. Complaint corroboration appended to `.sos/wip/complaints/COMPLAINT-20260813-204500-pythia.yaml` (projection-state diagnosis + ancestor-inscription-bleed vector).

NCSR discipline held despite the substitution: 5/5 rite-disjoint, no author self-graded STRONG (see PT-04 §2).

## §6 Defer registry delta

Fleet pegs `DW-COC-01..04` (`/Users/tomtenuta/Code/a8/a8/repos/.know/defer-watch-manifest.md`) UNCHANGED in structure; Phase-2 outcomes update their state:
- **DW-COC-01** (RE-1 fleet starvation) — CC-5 addresses the **offers** slice only (Tier-1, ruled); entities 5–16 remain starved and unowned (Tier-2 FORBIDDEN, still operator's F-1-tier). Peg stands.
- **DW-COC-02** (RE-2 authz gap) — chain-traced; stays High; determinant-YES receipts + the sharpened "exemption-path-has-no-filter" framing + the two-emitter/no-backstop findings attach here.
- **DW-COC-03** (gitleaks fleet gap) — CC-7 built the in-repo biting gate (dark) + STAGED registration; the fleet `|| true` in `autom8y-workflows` is untouched (locus (a), operator's).
- **DW-COC-04** (bare ASANA_PAT live-env) — untouched (operator-sovereign rotation, F-2).
- **NEW watch — R-CC7-1** (31 live-at-HEAD baseline-masked findings, triage-pending, CR-5-bound).
- **NEW watch — CC-5 FLAG-1** (Tier-2 config-capability now resident; keep env lever reserved).

## §7 Lineage ledger

`464266a5` land rulings → `b76424cc` Phase-2 entry gate → CC-5 build `6b75279f` (worktree) + CC-7 build `a922d8f9` (worktree) + SEC-002 dossier → `24a52c52` SEC-002 dossier+critique → `3e8eda86` CC-5 paper → `1003941c` CC-7 paper → `1c5a3f3f` PT-04 gate → this handoff. Worktrees under `.knossos/worktrees/wt.10x-dev.coc-phase-2.20260814T090131.{cc5a,cc7b}` preserved for the operator's merge word (CC-1's `…reconverge` worktree also preserved). Local main is 1-ahead+paper / behind origin by the exec-wave corpus; **un-pushed**.

## §8 What this handoff did NOT do

No merge, no push, no PR opened, no deploy, no branch-protection write, no credential read (CR-5), no cross-repo write, no git verb beyond the isolated worktrees + local paper commits, no AL-5 disturbance, no RE-2 re-grade, no operator fork ruled, no CC-8 attest, no limb-(a) self-attestation. CC-8 deferred to co-schedule with a post-land attest once F-4 lifts.
