---
type: decision
status: accepted
rung: rung-BUILT-DARK (job half) — see §7 for the honest exit rung of each half
landed: false — committed dark in an isolated worktree; un-pushed, un-PR'd, un-merged (F-4)
artifact_id: BUILD-cc7-gitleaks-biting-gate-2026-08-14
wave: chain-of-custody-closure
sprint: CC-7 (hard edge E1)
date: 2026-08-14
author: principal-engineer (10x-dev) — sole writer for CC-7
authority: operator ruling R-3 (AMENDED TWO-ACTION boundary); GATE-coc-phase2-entry-2026-08-14.md §3 CC-7 + BR-3
origin_main: d75601531edd220e693ce279f10b2a9b1d171f20
branch: coc-cc7-gitleaks-gate
commit: a922d8f9e6e712b4b18192b8b288712f888699a2
worktree: .knossos/worktrees/wt.10x-dev.coc-phase-2.20260814T090131.cc7b
self_assessment_cap: MODERATE (single seat, self-referential; receipts un-corroborated by a rite-disjoint second reader)
cr5_compliance: no credential value read, printed, reconstructed, or committed; scan reports written ONLY to an out-of-repo scratch path, fingerprint fields lifted via jq, reports deleted; no code-scanning-alert detail endpoint queried (CF-20 bounded)
git_discipline: commit only, path-scoped, in the isolated worktree. NO push, NO PR, NO merge, NO auto-merge (F-4)
paired_artifact: RUNBOOK-cc7-branch-protection-registration-2026-08-14.md (ACTION 2, rung-STAGED)
---

# BUILD — CC-7 gitleaks biting gate (ACTION 1 of a TWO-ACTION boundary)

## §0 The honest claim, stated first

**This session does NOT deliver a biting gate.** It delivers:

1. a local enforcing gitleaks job, **built and committed dark** in an isolated
   worktree — un-pushed, un-PR'd, un-merged; and
2. a fingerprint baseline that makes that job green on inherited history; and
3. **local two-sided proof** that the job trips on history without the baseline,
   passes with it, and still bites on a NEW secret-shaped instance; and
4. a **staged** runbook for the branch-protection registration that would make
   the red path actually block a merge.

The gate **bites only after ACTION 1 LANDS on main and ACTION 2 is EXECUTED by a
repo admin, in that order.** Any claim short of that ordering is the exact
silent-non-biting-gate class this wave exists to close. Per
`GATE-coc-phase2-entry-2026-08-14.md:62` and BR-3 (`:87`), CC-7's original shape
exit criterion 1 — "the red path reaches the surface that actually blocks a
merge" — is **structurally unreachable under F-4** (no merge word exists), and
the criteria are amended at dispatch accordingly.

---

## §1 Why ACTION 1 alone is not enough (the inherited correction)

The delegated check `gitleaks / Secrets Scan` is **always green**. The reusable
workflow it calls ends its scan step in `|| true`
(`CRITIQUE-cc6-gitleaks-recon-2026-08-13.md:49-51`, re-derived own-hands below at
§2 R0). It uploads SARIF; it cannot fail a merge.

`CRITIQUE-cc6…:99-149` (AR-1) establishes the load-bearing correction that
shapes this whole build: the `A / B` composite check name arises **only** from
reusable-workflow nesting (`{calling job id} / {called job name}`); a plain local
job reports a **simple** name (`CRITIQUE-cc6…:104-112`). Therefore a locally-added
enforcing job reports a NEW, UNREGISTERED context, and:

- **AR-1 mode 1** — added ALONGSIDE the delegated job: the old context stays green,
  the new job goes red under a name branch protection does not require → **red job
  does not block the merge → non-biting silent gate** (`CRITIQUE-cc6…:119-123`).
- **AR-1 mode 2** — added IN PLACE OF the delegated job: the required context
  `gitleaks / Secrets Scan` never reports → GitHub holds it PENDING → **every merge
  blocks indefinitely** (`CRITIQUE-cc6…:124-127`).

The only escape without a branch-protection edit is to hand-craft the local job's
`name:` as the literal `"gitleaks / Secrets Scan"` — named by the critic as **a
fragile spoof** (`CRITIQUE-cc6…:129-132`). **This build refuses the spoof.**

**Design consequence.** This build takes AR-1 **mode 1** deliberately (delegated job
untouched, enforcing job added alongside) and then discharges the mode-1 defect by
authoring ACTION 2 as a first-class, ordered, staged artifact rather than pretending
it does not exist. Mode 2 is refused outright: it would trade a silent gate for a
permanent merge block.

`RECON-gitleaks-enforcement-locus-2026-08-13.md:192` asserted the narrower position —
that branch protection is "ALREADY correctly wired … fixing (a) or (c) alone is
sufficient". That is TRUE for locus (a) (upstream `|| true` removal, same job, same
registered name) and **FALSE for locus (c)**, the locus R-3 selected. This build
implements the corrected two-action reading.

---

## §2 Receipts (own-hands; command + exit code)

Scan engine: **gitleaks v8.24.3**, the same version the upstream reusable workflow
installs, verified by sha256 before use.

### R0 — upstream `|| true` re-derived own-hands

```
gh api "repos/autom8y/autom8y-workflows/contents/.github/workflows/security-gitleaks.yml?ref=f5601acbe3905270dfcb9069854c78c0f940ad05" --jq '.content' | base64 -d
```
Exit `0`. Decoded body carries verbatim
`run: gitleaks detect --source . --report-format sarif --report-path gitleaks-results.sarif --verbose || true`
and installs `GITLEAKS_VERSION=8.24.3`. The critic's §1 quote reproduces
byte-identically at the pinned SHA.

### R0b — pinned binary provenance

```
curl -sSfL -o checksums.txt https://github.com/gitleaks/gitleaks/releases/download/v8.24.3/gitleaks_8.24.3_checksums.txt
```
Exit `0`. Published checksums, both assets:

| asset | sha256 |
|---|---|
| `gitleaks_8.24.3_linux_x64.tar.gz` (CI) | `9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c` |
| `gitleaks_8.24.3_darwin_arm64.tar.gz` (this seat) | `b90f13bb8c90ab72083d9b0c842e39dafb82c0e5c3f872f407366b7a58909013` |

```
shasum -a 256 -c -   # against the darwin_arm64 asset
```
Exit `0`, `OK`. `gitleaks version` → `8.24.3`, exit `0`. The linux_x64 checksum is
the value pinned in the workflow's `GITLEAKS_SHA256`.

### R1 — enforcement TRIPS on history WITHOUT the baseline (F-7 evidence reproduced)

Two independent runs, one pre-commit and one at the shipped commit.

**R1a (pre-commit, no `.gitleaksignore` anywhere in the tree):**
```
gitleaks detect --source . --redact --no-banner --report-format json --report-path <scratch>/report.json
```
run at branch head `d7560153` → **exit `1`**; `49` findings; `1924 commits scanned`.

**R1b (at the shipped commit `a922d8f9`, baseline file REMOVED from the working
tree, exact shipped command):**
```
gitleaks detect --source . --gitleaks-ignore-path .gitleaksignore --redact --no-banner --exit-code 1
```
→ **exit `1`**; `leaks found: 49`; `1838 commits scanned`.

`UV-P-CoC-4` is therefore not merely argued but **executed**: an enforcing run does
trip on this repo's history. Rotation would not change this — gitleaks pattern-matches
immutable history, not token liveness (`RECON…:166`).

### R2 — the baseline UNBLOCKS (same commit, same command, only the file differs)

```
gitleaks detect --source . --gitleaks-ignore-path .gitleaksignore --redact --no-banner --exit-code 1
```
at `a922d8f9` with `.gitleaksignore` present → **exit `0`**, `no leaks found`.

R1b and R2 are a **matched pair at one commit with one command**: the sole variable
is the presence of the baseline file. That isolates the baseline as the cause and
rules out "the commit somehow fixed history."

**R2 also closes the chicken-and-egg risk.** The finding count with the baseline
removed is `49` at `a922d8f9` — *identical* to the pre-commit count at `d7560153`.
The commit that ADDS `.gitleaksignore` and the new workflow introduces **zero new
findings**: neither the fingerprint list nor the workflow body trips a rule. Had it
done so, its own fingerprint would not be in the baseline and the gate would be red
on day one.

### R3 — the gate still BITES on a NEW instance (two-sided teeth)

Run in a **disposable clone** in scratch (never on the branch, never pushed), so that
no secret-shaped string is ever committed to `coc-cc7-gitleaks-gate` — committing one
would poison the future gate. Both legs carry the baseline; the ONLY difference
between them is the defect.

| leg | new commit on top of `a922d8f9` | exit | findings |
|---|---|---|---|
| **control (no defect)** | `0c87b30a` — benign text file | **0** | `no leaks found` |
| **defect** | `6e681dce` — synthetic fixture, documented `1/{gid}:{hex}` + `2/{gid}/{sub}:{hex}` shapes assembled from parts at runtime | **1** | exactly `2`, both `asana-native-pat`, both at commit `6e681dce`, both in the new file |

Two-sided and discriminating: the no-defect variant passes, the defect variant fails,
**and the defect run reports ONLY the new findings** — zero historical re-trips, so
the baseline is not silently eroding under new commits either.

### R4 — structural assertions on the shipped workflow

Parsed with `yaml.safe_load`, keys asserted programmatically, exit `0`:
- job-level `continue-on-error` key: **absent**; per-step `continue-on-error`: **absent** on all four steps.
- job-level `if:` key: **absent**.
- the scan step's `run:` body contains **no** `|| true`.
- `jobs.gitleaks-enforcing.name` == `Secrets Scan (enforcing)` — this string IS the
  derived check-run context (§4).
- workflow-level `permissions:` == `{contents: read}`; job-level identical.
- triggers == `push` + `pull_request`, matching the delegated caller
  (`.github/workflows/gitleaks.yml:7-11`).

### R5 — branch protection, READ ONLY (no write of any kind)

```
gh api repos/autom8y/autom8y-asana/branches/main/protection
```
Exit `0`. `strict: true`, `enforce_admins: true`, `required_linear_history: true`,
**9** required contexts, 8 pinned to `app_id 15368` (GitHub Actions) and `CodeQL`
pinned to `app_id 57789`. `required_pull_request_reviews` and `restrictions` are
**absent from the response entirely** (unconfigured). Full current state and its
consequences for the PATCH shape are carried in the paired runbook §3.

---

## §3 What was built

### 3.1 `.github/workflows/gitleaks-enforcing.yml` (new file, 106 lines)

A standalone workflow rather than a second job inside `gitleaks.yml`. Rationale:
the existing caller is a pure 19-line delegation and is left byte-untouched, so when
the upstream `|| true` is eventually removed (locus (a)) this local fork retires by
deleting **one file** plus de-registering **one context** — a clean two-step
retirement rather than an unpick. A separate file also gets its own concurrency group
(`gitleaks-enforcing-${{ github.ref }}`), so the enforcing leg's cancellation is not
coupled to the advisory leg's.

Load-bearing properties (all asserted in R4):

| property | value | why |
|---|---|---|
| job `name:` | `Secrets Scan (enforcing)` | simple, honest, NOT the `gitleaks / Secrets Scan` spoof |
| checkout | `actions/checkout@93cb6efe…` (v5.0.1), `fetch-depth: 0`, `persist-credentials: false` | full history — a shallow checkout silently scans almost nothing; repo-standard pin |
| gitleaks install | version `8.24.3` **and** `sha256` of the linux_x64 asset, verified with `sha256sum -c -` under `set -euo pipefail` | supply-chain pin on both axes; same engine as the delegated leg so the two cannot diverge |
| baseline guard | `test -f .gitleaksignore` as its own step | a missing/renamed baseline fails loud and early instead of surfacing as an opaque scan failure |
| scan | `gitleaks detect --source . --gitleaks-ignore-path .gitleaksignore --redact --no-banner --exit-code 1` | **no `|| true`, no `continue-on-error`, no `if:` guard**; `--exit-code 1` states the enforcing intent rather than inheriting a default |
| reporting | **no report file written at all** | report bodies carry secret VALUES; the delegated job already owns SARIF upload. CR-5 by construction |
| `permissions:` | `contents: read` at workflow AND job level | minimal; no `security-events: write` needed since nothing is uploaded |
| interpolation | none inside any `run:`; version/sha passed via `env:` | avoids the template-injection class the repo's `zizmor` workflow lints for |

### 3.2 `.gitleaksignore` (new file, 130 lines, **49 fingerprints**)

Keyed on FINGERPRINTS (`commit:file:rule:startline`), per CF-5 — not bare commit
SHAs, not path globs, and never a secret value.

**Tripping-set shape** (counts and identifiers only; no values):

| axis | value |
|---|---|
| fingerprints | **49** |
| distinct commits spanned | **26** |
| distinct files spanned | **22** |
| rule breakdown | `generic-api-key` 28 · `asana-client-id` 15 · `asana-native-pat` 5 · `jwt` 1 |
| largest single commit | `eff1d0d2` (14 findings) |

**CF-5 confirmed empirically, and in BOTH directions.** The critic's warning that the
baseline must cover the full tripping set rather than only cred-t21's three commits is
not hypothetical: **44 of the 49 findings have nothing to do with cred-t21**, sitting
in 24 other commits across `tests/`, `src/autom8_asana/client.py`,
`.github/workflows/test.yml`, a `.ledge/reviews/` markdown, and a `.claude/sessions/`
JSONL. Scoping the baseline to cred-t21 alone would have left the gate permanently red.

The unexpected direction: of cred-t21's three named commits
(`a578ca85`/`525431de`/`15cffee1`), only **two** produce findings — `15cffee1` (3) and
`525431de` (2), all `asana-native-pat` in `.claude/settings.local.json`. **`a578ca85`
produces zero findings.** Consistent with `detect` scoring diff ADDITIONS: a commit
that removes the value adds nothing to match. Recorded as an observation, not a
re-grade — the cred-t21 record is not this sprint's to amend.

**The baseline is narrow by construction.** A fingerprint pins one
`(commit, file, rule, line)` tuple. A new secret in any new commit produces a
fingerprint absent from the list, and the gate goes red — proved in R3. The header
comment in the file states this, states that the report body must never be committed
or printed, and states that the baseline is orthogonal to rotation.

**The baseline does NOT triage.** Several of the 49 findings are visibly test
fixtures; some may not be. This sprint's charge was to make the enforcing gate
green on inherited history, not to adjudicate which historical findings are real.
Carried forward at §6 as a named residual.

---

## §4 The derived registration context string

**`Secrets Scan (enforcing)`**

Derivation (this is a platform-behavior claim; grounded, not assumed):
- The composite `X / Y` form arises **only** from reusable-workflow nesting
  (`CRITIQUE-cc6…:104-112`); a plain local job reports a simple name.
- Empirical corroboration in this very repo's live check-runs, per the critic's
  own-hands pull: plain jobs report `dispatch`, `Fleet Schema Governance`,
  `Lint noqa Drift Guard (RUF100)`, `Analyze (actions)` — all simple, and one of
  them carries a parenthetical, so `(enforcing)` is not a novel shape here
  (`CRITIQUE-cc6…:107-112`).
- Corroborated again in branch protection itself (R5): the required context
  `CodeQL` is a bare simple name, so simple-name contexts are already precedented
  in this repo's protection config.
- The check-run name for a plain job is the job's `name:` when set. R4 asserts
  `jobs.gitleaks-enforcing.name == "Secrets Scan (enforcing)"`. No `strategy.matrix`
  is present, so no matrix suffix is appended.

`[UV-P: the check-run context reported by the new job is exactly the string
"Secrets Scan (enforcing)" | METHOD: observe the check-run name on the first CI run
after the job LANDS on main — `gh api repos/autom8y/autom8y-asana/commits/main/check-runs --jq '.check_runs[].name'`
| REASON: the job has never executed — it is committed dark in an isolated worktree,
un-pushed under F-4, so no check run exists to read. The derivation above is
mechanically grounded but the string cannot be read off a live run at this altitude.]`

**This UV-P is the exact reason ACTION 2 is ordered AFTER the land.** The runbook's
first step is to READ the observed name, not to trust this derivation.

---

## §5 Fences honored

- **F-4** — one commit, path-scoped, in the isolated worktree. No push, no PR, no
  merge, no auto-merge. Zero `gh api` WRITE calls of any kind; the only `gh` calls
  were reads (upstream workflow body, branch protection). PR #365 untouched.
- **CR-5** — no credential value read, printed, reconstructed, or committed. Every
  scan report was written to an out-of-repo scratch path, `--redact` was passed on
  every run, only `.Fingerprint`/`.RuleID`/`.File`/`.StartLine`/`.Commit` fields were
  ever lifted (via `jq`), and all reports, logs, and probe clones were deleted at
  close. A post-cleanup `grep -rE` for the PAT shape across the scratch tree returned
  **no matches**. No code-scanning-alert detail endpoint was queried (CF-20 stands bounded).
- **Secret-shaped strings never touch the branch.** The R3 defect leg ran in a
  disposable clone; the synthetic fixture is assembled from parts at runtime by a
  scratch-only script and no literal token string exists on disk anywhere.
- **F-2 (rotation)** — untouched, unscheduled, unprepared. Operator-only. Per CF-5
  the BASELINE greens CI; the rotation does not, and this artifact discharges
  nothing about it.
- **Single writer** — this seat is the sole writer for CC-7, on paths disjoint from
  CC-5 (`src/`) and SEC-002 (cross-repo read-only), per `GATE…:40`.
- **MODERATE self-cap** — every receipt above is this seat's own hands, single-seat,
  un-corroborated by a rite-disjoint second reader.

---

## §6 Residuals carried (named, not dismissed)

| id | residual | disposition |
|---|---|---|
| **CF-4** | The `asana-native-pat` regex is validated against the DOCUMENTED `1/`/`2/` shape only. R3 proves it fires on that shape. If the real leaked token deviated (uppercase hex, gid < 6 digits, hex < 32 chars), the rule silently does not fire. **One-sided: it can trip LESS than reality, never more.** | **UNCLOSEABLE under CR-5** — closing it requires reading the credential. Carried, not dismissed. |
| **CF-20** | Whether a GitHub code-scanning alert already exists for the cred-t21 pattern. | NOT queried — CR-5 boundary (the alert-detail endpoint can surface match content). Stands bounded. |
| **CF-19** | Blast radius of upstream locus (a) — how many other repos pin `security-gitleaks.yml`. | Out of locus per R-3; unenumerated. |
| **R-CC7-1** | The 49 baselined findings are **suppressed, not triaged.** Some are plainly test fixtures; whether any is a live exposure is unadjudicated by this sprint. | **NEW residual, filed here.** Suppression greens CI; it does not certify the history clean. Warrants a follow-on triage pass, out of CC-7 scope. |
| **R-CC7-2** | Observed engine behaviour: pointing `--gitleaks-ignore-path` at a directory containing no `.gitleaksignore` did **not** suppress baseline application (exit `0`, `no leaks found`) — the baseline was still honoured from the source root. | Recorded so the receipt method is auditable: the decisive no-baseline leg (R1b) was therefore run by **removing the file**, not by redirecting the flag. Does not affect the shipped command, which points at the real file. |
| **R-CC7-3** | The workflow has **never executed**. `zizmor` (which lints `.github/workflows/**`) has never seen it; no CI run of any kind exists. | Design follows the repo's zizmor-safe conventions (SHA-pinned action, `persist-credentials: false`, explicit minimal `permissions`, zero `${{ }}` in `run:`), but that is a design claim, not a green run. `[UV-P: the new workflow passes zizmor and all repo CI gates \| METHOD: observe the CI matrix on the first PR run \| REASON: F-4 — nothing is pushed, so no CI has run]` |

---

## §7 Exit rungs — both halves, honestly

| half | artifact | rung | what it means |
|---|---|---|---|
| **ACTION 1 — the job** | `.github/workflows/gitleaks-enforcing.yml` + `.gitleaksignore` @ `a922d8f9` | **`rung-BUILT-DARK`** | Committed in an isolated worktree; two-sided locally proven. NOT pushed, NOT PR'd, NOT merged. The ceiling named at `GATE…:61` is `PR-UP-MERGE-HELD`; this build stops one rung **below** it, because opening a PR is a push and F-4 forbids it. Advancing to `PR-UP-MERGE-HELD` is a main-thread action, not this seat's. |
| **ACTION 2 — the registration** | `RUNBOOK-cc7-branch-protection-registration-2026-08-14.md` | **`rung-STAGED`** | Authored, exact commands carried, never executed. Repo-admin + operator-reserved. Ordered strictly AFTER ACTION 1 lands and is observed reporting. |

**The gate is NOT biting.** It is *authored and locally proven two-sided*; it bites
only after land + registration, in that order.

## §8 Verified artifacts

| artifact | absolute path | verified |
|---|---|---|
| enforcing workflow | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.knossos/worktrees/wt.10x-dev.coc-phase-2.20260814T090131.cc7b/.github/workflows/gitleaks-enforcing.yml` | YES (Read + `yaml.safe_load` assertions, R4) |
| baseline | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.knossos/worktrees/wt.10x-dev.coc-phase-2.20260814T090131.cc7b/.gitleaksignore` | YES (Read; 49 fingerprints; R2 proves it applies) |
| this build note | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/decisions/BUILD-cc7-gitleaks-biting-gate-2026-08-14.md` | YES |
| registration runbook | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/decisions/RUNBOOK-cc7-branch-protection-registration-2026-08-14.md` | YES |
