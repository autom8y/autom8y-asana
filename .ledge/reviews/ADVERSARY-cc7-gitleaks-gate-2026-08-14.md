---
type: adversary-report
subtype: arch-adversary-challenge
challenger_agent: arch-adversary
rite_disjoint: true
initiative: chain-of-custody-closure
session: coc-phase-2
sprint: CC-7 (hard edge E1)
date: "2026-08-14"
iter: 1
delta_scope_attested: false
status: complete
verdict: PASS
adversary_disposition: CONCUR
self_assessment_cap: MODERATE
target_commit: a922d8f9e6e712b4b18192b8b288712f888699a2
origin_main_pin: d75601531edd220e693ce279f10b2a9b1d171f20
target_artifacts:
  - path: ".ledge/decisions/BUILD-cc7-gitleaks-biting-gate-2026-08-14.md"
    sha256: "c865ed3d166e5df3a3e690ff0ce5776b9c4d69590f95f1e03b77d97bea15c2c3"
  - path: ".ledge/decisions/RUNBOOK-cc7-branch-protection-registration-2026-08-14.md"
    sha256: "6cb92e9426046eb5ca74d2002d06200070ae2f40752669f0a814c6f0586dfc75"
  - path: ".knossos/worktrees/wt.10x-dev.coc-phase-2.20260814T090131.cc7b/.github/workflows/gitleaks-enforcing.yml"
    sha256: "4f61142723335e598a93300c7a7532ac536411db9dcbad9a32a60751257bf17e"
  - path: ".knossos/worktrees/wt.10x-dev.coc-phase-2.20260814T090131.cc7b/.gitleaksignore"
    sha256: "f5bd23a9c6085259e7da13dba1246efb783cf7d2b0cd7b5ad671b6590dc17800"
# Axis mapping (parent-supplied reframe of TL-A/B/C for this build-artifact review):
tl_a_status: PASS              # rung honesty
tl_b_status: PASS              # AR-1 two-action correctness (mode 1, delegated untouched)
tl_c_status: PASS              # false-green / baseline integrity disclosure
registration_safety_status: PASS
# Own-hands rite-disjoint corroborations (headline):
delegated_caller_untouched: true      # git diff d7560153..a922d8f9 -- .github/workflows/gitleaks.yml == EMPTY
commit_path_scoped: true              # a922d8f9 touches ONLY the 2 intended files
no_write_executed_evidence: consistent # clean tree; 1-ahead/0-behind local origin/main; zero write evidenced
cr5_compliance: "no credential value read, printed, or reconstructed; git/grep/shasum ran only over workflow YAML, fingerprint-only .gitleaksignore, and markdown — none carry secret values; no scan re-executed; no report written; no network"
challenges_raised:
  - id: CH-01
    taxonomy_id: AC-UNMAPPED
    axis: rung-honesty/receipt-integrity
    severity: ADVISORY
    target_element: "BUILD §2 R1a (:125) '1924 commits scanned' vs R1b (:132) '1838 commits scanned'"
    rationale: "a922d8f9's parent IS d7560153 (own-hands git log). The child commit's ancestry is a superset of the parent's, yet the enforcing run at the child reports 86 FEWER scanned commits (1838 < 1924). Anomalous and unexplained. Does NOT touch the load-bearing finding-count logic (49==49) that R2 rests on."
    falsification_pathway: "Re-run both scans own-hands and reconcile the commit-scan counts, OR annotate the gitleaks counting behaviour that produces the delta. If reconciliation shows the two runs scanned materially different trees, the R1a/R1b 'identical-49' comparison weakens and this escalates to FLAG."
    remediation_hint: "One-line note in R1 reconciling 1924 vs 1838; the finding-count claim itself is independently sound."
    know_candidate_filed: true
  - id: CH-02
    taxonomy_id: AC-UNMAPPED
    axis: rung-honesty/terminology-integrity
    severity: ADVISORY
    target_element: "BUILD §0 pt3 (:31-32) 'still bites on a NEW secret-shaped instance' + R3 header (:156) 'the gate still BITES on a NEW instance'"
    rationale: "'bite/BITES' is reused for the LOCAL scan exit-1 trip, while §7 (:339) reserves 'biting' for the merge-block sense ('The gate is NOT biting'). The scan-trip-vs-merge-block distinction IS the load-bearing distinction of this wave; reusing 'bite' for the scan-trip erodes it and invites out-of-context extraction. Mitigated by the forceful §0/§7 denials."
    falsification_pathway: "If any downstream artifact cites R3's 'the gate still bites' as evidence the gate merge-blocks, this ADVISORY becomes a FLAG. Reword R3 to 'the scan trips (exit 1)'."
    remediation_hint: "Reserve 'bite' for merge-block; use 'the scan trips' for exit-code behaviour."
    know_candidate_filed: false
  - id: CH-03
    taxonomy_id: AC-UNMAPPED
    axis: false-green/baseline-integrity
    severity: ADVISORY
    target_element: "BUILD §6 R-CC7-1 (:326) + §3.2 (:257-260); .gitleaksignore header (:22-28)"
    rationale: "A fingerprint keys on (commit,file,rule,line) and suppresses regardless of whether the value is still LIVE at HEAD; a still-live secret whose introducing-commit fingerprint is baselined would be silently greened. The build DISCLOSES this ('suppressed, not triaged'; 'whether any is a live exposure is unadjudicated') — so it is NOT an overclaim. But the disclosure is load-bearing: any future 'history is clean' claim that drops R-CC7-1 becomes the false-green overclaim this wave exists to close."
    falsification_pathway: "If a downstream artifact cites the green enforcing CI as evidence the history contains no live secret, that IS the false-green overclaim and revises the disposition on THAT artifact to BLOCK. The R-CC7-1 triage pass must run before any clean-history claim."
    remediation_hint: "Keep R-CC7-1 attached to every downstream citation of the green gate; schedule the triage pass."
    know_candidate_filed: false
arch_ref_citations:
  - "AQ:SRC-010"   # Cohen 1960 — inter-rater reliability; rite-disjoint challenge carries a challenger distinct from the author
  - "AV:SRC-001"   # Messick 1989 — construct validity; each axis names the specific construct (rung honesty / two-action / false-green) it verifies
  - "P-02"         # Kane 2006 (assessment-methodology) — argument-based validity; UV-P labels are the artifact's falsification-condition analog
---

# ADVERSARY-REPORT — CC-7 gitleaks biting gate (rite-disjoint second-read, iter 1)

Rite-disjoint adversarial second-read of CC-7's outbound build artifacts. This seat
shaped none of the target work (arch, disjoint from the 10x-dev principal-engineer that
authored CC-7). Read-only against all targets; the only write is this report. Every
challenge carries a file:line anchor and a falsification pathway. Self-assessment capped
at MODERATE per `self-ref-evidence-grade-rule` — my own re-derivations below are
rite-disjoint corroboration of the author's receipts, not a STRONG self-grade.

## §1 Challenge Summary

**Verdict: PASS** (adversary_disposition: CONCUR). This is an overclaim hunt, and the
hunt came up **negative**: no sentence in either artifact implies a biting/closed gate
the session did not achieve. The artifacts lead with the honest denial ("This session
does NOT deliver a biting gate", BUILD §0 :26), carry every forward claim as a UV-P with
METHOD+REASON, refuse the name-spoof, refuse AR-1 mode 2, and disclose every residual.
The rung claims are not merely honest — they **under-claim** (the job half stops at
`rung-BUILT-DARK`, one rung *below* the authorised `PR-UP-MERGE-HELD` ceiling, BUILD §7
:336). PASS is the result of a rigorous negative hunt, not a rubber-stamp; §2–§6 enumerate
every check, including nine own-hands corroborations.

Three **ADVISORY** observations (none verdict-driving; all AC-UNMAPPED, ADVISORY-only per
the arch-adversary taxonomy §6f — a build-artifact secrets-gate review is outside the
native AC-01..AC-05 arch-HANDOFF surface):

- **CH-01 (ADVISORY)** — R1a/R1b report an unexplained commit-scan-count delta (1924 vs
  1838) where the child commit scans *fewer* than its parent. Receipt-integrity note;
  does not touch the load-bearing 49==49 logic.
- **CH-02 (ADVISORY)** — "bite/BITES" is reused for the scan-trip (R3) vs the merge-block
  sense denied in §7; a terminology-integrity erosion of the wave's load-bearing
  distinction.
- **CH-03 (ADVISORY)** — the R-CC7-1 "suppressed ≠ triaged / live-exposure unadjudicated"
  residual is correctly disclosed (not an overclaim) but is load-bearing: any future
  clean-history claim that drops it becomes the false-green overclaim.

## §2 TL-A Analysis — rung honesty (is any biting/closed gate implied?)

**Status: PASS.** Hunted every forward-looking / completion-shaped sentence for an implied
biting gate. Findings:

- Frontmatter is honest at the top: `rung: rung-BUILT-DARK (job half)`, `landed: false —
  committed dark ... un-pushed, un-PR'd, un-merged (F-4)` (BUILD :4-5). Runbook frontmatter:
  `rung: rung-STAGED — authored, never executed. NOT executed this session and NOT
  executable this session (F-4)` (RUNBOOK :4).
- §0 (:26): **"This session does NOT deliver a biting gate."** §7 (:339): **"The gate is
  NOT biting."** BR-3's "highest over-claim risk in Phase 2" (GATE :87) is met head-on:
  the build explicitly states exit-criterion-1 ("red path reaches the merge-blocking
  surface") is **structurally unreachable under F-4** (BUILD §0 :36-42, citing GATE :62 +
  BR-3 :87) — the limitation is stated plainly, not papered.
- **Under-claim, own-hands confirmed.** The GATE authorised a job-half ceiling of
  `PR-UP-MERGE-HELD` (GATE :61). The build stops one rung *below* it at `rung-BUILT-DARK`
  because "opening a PR is a push and F-4 forbids it" (BUILD §7 :336). I corroborated the
  F-4 posture own-hands: branch `coc-cc7-gitleaks-gate` is **1-ahead / 0-behind** the local
  `origin/main` ref (`git rev-list --left-right --count origin/main...HEAD` → `0  1`), the
  working tree is **clean** (`git status --porcelain` → empty), and the single commit
  a922d8f9 sits directly on d7560153 (= origin_main pin). Conservative, not inflated.
- The R4 "enforcing" structural claims (BUILD §2 :172-183) are the load-bearing "the scan
  can actually go red" evidence, and I re-derived them own-hands from the shipped file:
  no `continue-on-error` (job or step), no job-level `if:`, no `|| true` in the scan
  `run:` (the only `|| true`/`continue-on-error` tokens in the file are in *comments* at
  :8/:29/:88 — `grep -nE` confirmed), `--exit-code 1` present (:106), workflow+job
  `permissions: {contents: read}` (:43-44, :54-55), triggers `push[main]+pull_request[main]`
  (:37-41) matching the delegated caller's `:7-11` (Read own-hands). The enforcing intent
  is real in the YAML.

No overclaim on this axis. The single ADVISORY here is **CH-01** (receipt-count delta) and
the terminology note **CH-02** — neither implies a biting gate.

## §3 TL-B Analysis — AR-1 two-action correctness (mode 1, delegated untouched)

**Status: PASS.** The load-bearing correctness question — did the build take AR-1 mode 1
(enforcing job ALONGSIDE the delegated one, delegated left byte-untouched) and NOT mode 2
(replacement → permanent PENDING)? — I answered **own-hands**, not by trusting the artifact:

- `git diff d7560153 a922d8f9 -- .github/workflows/gitleaks.yml` → **EMPTY**. The delegated
  caller is byte-identical to origin/main. **Confirmed: delegated caller NOT modified.**
- `git show --stat a922d8f9` → the commit touches **exactly two files**:
  `.github/workflows/gitleaks-enforcing.yml` (+106) and `.gitleaksignore` (+130). The
  enforcing leg is a *new standalone file added alongside*, never an edit of `gitleaks.yml`.
  This is AR-1 **mode 1**, exactly as claimed (BUILD §1 :70-74; workflow header :12-16).
- The delegated caller (Read own-hands, 19 lines) is a pure delegation: job id `gitleaks`
  `uses:` the reusable `security-gitleaks.yml@f5601acb...` (:18-19). The composite required
  context `gitleaks / Secrets Scan` = {caller job id}/{reusable job name} — the exact
  mechanism the critic established (CRITIQUE :104-112, Read own-hands). Mode 2 is refused
  in prose *and* in structure (delegation left intact so the required context keeps
  reporting).
- **The name-spoof is refused.** The job `name:` is the honest `Secrets Scan (enforcing)`
  (:1, :51), NOT the literal `gitleaks / Secrets Scan` spoof the critic named as fragile
  (CRITIQUE :129-132). Refusing the spoof is what *forces* ACTION 2 to exist — correct.
- **Derived context string correctly carried UV-P, NOT asserted as fact.** BUILD §4
  (:283-288) labels `Secrets Scan (enforcing)` a UV-P with METHOD (observe the check-run
  name after land via `gh api .../check-runs`) and REASON (the job has never executed —
  committed dark under F-4). RUNBOOK Step 1 (:84-99) operationalises it: "READ the observed
  check-run name (do not trust the derivation) ... If the observed name differs in ANY byte
  ... register the observed string, not the string in this document." This is textbook
  UV-P discipline [P-02 Kane — the UV-P is the artifact's falsification-condition analog].
- **Ordering law prevents the mode-2 hazard.** RUNBOOK §2 (:51-68): "REGISTER ONLY AFTER
  THE JOB HAS LANDED ON main AND HAS BEEN OBSERVED REPORTING. Never before." Registering an
  unreportable context before the job lands would hold it PENDING and block every merge
  (with `enforce_admins: true`, even admins) — the ordering correctly inverts AR-1 mode 2.

No overclaim on this axis.

## §4 TL-C Analysis — false-green / baseline integrity

**Status: PASS.** The baseline greens CI by suppressing 49 findings. The adversarial
question: does the artifact anywhere conflate "CI is green" with "no secret exists," or
silently allowlist a still-live secret?

- **Could a fingerprint-keyed baseline silently allowlist a live secret at HEAD?** Yes, in
  principle — a fingerprint suppresses its (commit,file,rule,line) tuple regardless of
  whether the value is still live at HEAD. **This is CH-03.** But the build does not conceal
  it: §3.2 (:257-260) "The baseline does NOT triage ... some may not be [fixtures]"; §6
  R-CC7-1 (:326) "suppressed, not triaged ... whether any is a live exposure is
  unadjudicated ... Suppression greens CI; it does not certify the history clean"; the
  `.gitleaksignore` header (:22-28) states exactly what it does and does NOT do. **No
  clean-history claim is made. No green==no-secret conflation exists.** Disclosure, not
  overclaim. CH-03 is ADVISORY: the residual is load-bearing for any *future* citation.
- **CF-4 carried, not dropped.** §6 CF-4 (:323): the `asana-native-pat` regex is validated
  against the DOCUMENTED `1/`/`2/` shape only; deviation → the rule silently under-fires;
  "One-sided: it can trip LESS than reality, never more"; "UNCLOSEABLE under CR-5." This is
  the CR-5-uncloseable residual the GATE required (GATE §3 CC-7 :59) — present and honest.
- **Baseline scope corroborated own-hands.** `grep -cE '^[0-9a-f]{40}:' .gitleaksignore` →
  **49** fingerprints; distinct-commit count → **26**. Both match BUILD §3.2 (:230-236)
  exactly. The CF-5 "cover the FULL tripping set, not only cred-t21's three commits"
  requirement (GATE :58) is met: 44/49 findings sit outside cred-t21 (BUILD :239-242).
- **Two-sidedness argued, not disproven.** R3 (:156-170) shows control-passes / defect-fails
  in a disposable clone. I did not re-execute the scan (CR-5 risk + cost; the finding-count
  logic is independently coherent and structurally corroborated by §2 R4). The 49==49
  matched-pair logic (R1b/R2, one commit, one command, sole variable = baseline presence)
  is internally sound; the *commit-scan-count* footnote is CH-01.

No overclaim on this axis.

## §5 Registration-Safety Analysis (parent axis 4)

**Status: PASS.** (This section stands in for the schema's Remediation Pathway slot, which
is BLOCK/PASS-WITH-CONDITIONS-only; there is nothing to remediate for a PASS.)

- **No write executed this session — evidence consistent.** RUNBOOK frontmatter + §7 (:241)
  claim zero `gh api` WRITE calls. My own-hands local state fully corroborates F-4: clean
  working tree, single path-scoped commit, branch 1-ahead/0-behind local origin/main. I
  found **zero evidence of any write.** I did NOT re-read live branch-protection state
  (network is out-of-scope for this seat), so "the remote protection object is unchanged"
  is carried as a **bounded corroboration**, not asserted — consistent with the artifact's
  own MODERATE self-cap.
- **Operator/repo-admin-reserved, unambiguous.** RUNBOOK frontmatter `executor: REPO ADMIN
  — operator-reserved. NO AGENT SEAT MAY EXECUTE ANY COMMAND IN THIS FILE`; §0 banner
  "DO NOT EXECUTE ANY COMMAND IN THIS FILE FROM AN AGENT SEAT"; §7 (:247) operator-reserved
  per GATE :80. Multiply-redundant and correct.
- **Correct PATCH form.** Step 3 (:143-163) PATCHes the **sub-resource**
  `.../branches/main/protection/required_status_checks` with all checks **app-pinned**
  (15368 / CodeQL 57789), adding `Secrets Scan (enforcing)` at 15368. §4 (:198-201)
  correctly **REJECTS** the append form (`POST .../required_status_checks/contexts` →
  registers at `app_id: null` = any-app weakening) and correctly relegates the whole-object
  `PATCH .../protection` to NOT-RECOMMENDED fallback (resets every omitted field). The right
  primary form is chosen for the right reason.
- **Rollback present** (§5 :206-217): re-PATCH with the enforcing line removed → assert
  n==9. Cheap, complete, returns pre-CC-7 posture. Anti-dogma satisfied on the runbook's own
  terms.

## §6 Falsification of This Report (self-referential challenge)

Per the arch-adversary acid test — an adversary of *this* report must be able to falsify my
PASS with a concrete observation. Here is exactly what would revise it:

1. **Revises PASS → BLOCK:** a live check-run observation after ACTION 1 lands shows the job
   reports a check-run name **other than** `Secrets Scan (enforcing)` AND the runbook's
   Step-1 "read the observed name" guard is skipped, registering the derived string blindly →
   permanent-PENDING outage. (My PASS rests on the UV-P + Step-1 guard being honoured; it is
   authored, but unexecuted.)
2. **Revises PASS → BLOCK:** any downstream artifact cites the green enforcing CI as evidence
   the repo history holds no live secret (CH-03 realised) — that is the false-green overclaim,
   and I would BLOCK that artifact.
3. **Revises PASS → PASS-WITH-CONDITIONS (escalates CH-01 to FLAG):** re-running R1a/R1b
   own-hands shows the 1924-vs-1838 delta reflects materially different scanned trees (not a
   gitleaks counting artefact), weakening the "identical-49 matched pair" evidence.
4. **Revises PASS → BLOCK:** a `git diff` at a later commit shows `.github/workflows/gitleaks.yml`
   (the delegated caller) was in fact modified, or a branch-protection WRITE was executed this
   session. My own-hands checks (empty caller diff; clean tree; zero write evidenced) found the
   opposite — but I could not probe remote protection state (no network), so #4 is the live
   residual gap in my own corroboration.

**Corroboration boundaries (honest limits of this second-read):** I did NOT re-execute
gitleaks over history (the 49/2/0 counts are carried at the author's own-hands MODERATE,
uncorroborated by me on the scan itself); I did NOT re-read live branch-protection state
(network out-of-scope). Everything else load-bearing was re-derived own-hands: caller
untouched (empty diff), commit path-scoped (2 files), no-swallow structure (grep), SHA pin
match (grep), baseline 49/26 (grep), trigger parity + UV-P discipline + runbook PATCH form
(Read). Self-cap MODERATE — no STRONG grade asserted on any claim, including my own.

**AC-UNMAPPED note (§6f):** all three challenges are AC-UNMAPPED because a chain-of-custody
secrets-gate build-artifact review is outside the native arch-HANDOFF AC-01..AC-05 surface.
Per taxonomy, they are ADVISORY-only and drive no verdict escalation. [KNOW-CANDIDATE:
arch-adversary AC taxonomy has no entry for receipt-integrity / numeric-consistency
challenges on build-artifact receipts (CH-01 class); candidate for §6f calibration.]
