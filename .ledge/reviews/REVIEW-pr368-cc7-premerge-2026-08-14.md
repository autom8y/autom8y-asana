---
type: review
status: accepted
artifact_id: REVIEW-pr368-cc7-premerge-2026-08-14
rung: VERIFIED-MECHANISM-OWN-HANDS
verdict: GO-WITH-CONDITIONS
reviewer: platform-engineer[sre]
self_assessment_cap: MODERATE
subject_pr: autom8y/autom8y-asana#368
subject_head: a922d8f9e6e712b4b18192b8b288712f888699a2
rite_disjointness: sre reviewing 10x-dev authorship; reviewer shaped none of CC-7
date: 2026-08-14
cr5_compliance: >-
  No credential value read, printed, or reconstructed. All gitleaks invocations ran with
  --redact and WITHOUT --verbose, so only finding COUNTS were emitted, never values. No
  SARIF/JSON report written at any point. The one synthetic fixture used is an all-zeros
  string that is structurally rule-matching but is not a credential.
---

# REVIEW — PR #368 (CC-7 gitleaks enforcing job + baseline), pre-merge NCSR

**Verdict: GO-WITH-CONDITIONS.** Zero conditions block the merge. All conditions bind
ACTION 2 (registration) and post-land operation.

The headline supply-chain question — is the pinned sha256 the LINUX asset the ubuntu
runner downloads, or the darwin asset a local proof would have used? — resolves
**CORRECT**. The NO-GO-level defect is not present.

---

## §1 Scope and disjointness

| Item | Value | Receipt |
|---|---|---|
| Head SHA | `a922d8f9e6e712b4b18192b8b288712f888699a2` | `gh pr view 368 --json headRefOid` |
| Files | exactly 2, both `ADDED` | `gh pr diff 368 --name-only` |
| | `.github/workflows/gitleaks-enforcing.yml` +106 | |
| | `.gitleaksignore` +130 | |
| Base | `main` | |
| Author rite | 10x-dev | reviewer rite = sre → disjoint |

Confirmed: the diff touches EXACTLY those two files and nothing else.

---

## §2 BLOCKING-CLASS CHECKS — all clear

### V-1 — Linux-asset sha256 pin is CORRECT (the named NO-GO risk)

The workflow constructs the asset name at `:79` as
`gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz` and pins `GITLEAKS_SHA256` at `:76`.

Upstream release manifest `gitleaks_8.24.3_checksums.txt`:

```
9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c  gitleaks_8.24.3_linux_x64.tar.gz   <-- PINNED
41c44ae8ad1d6eef57d4526ad0fd67d8129eee9a856f55c2b3b9395fd3d9ec0f  gitleaks_8.24.3_darwin_x64.tar.gz
b90f13bb8c90ab72083d9b0c842e39dafb82c0e5c3f872f407366b7a58909013  gitleaks_8.24.3_darwin_arm64.tar.gz
```

The pinned value is byte-identical to the **linux_x64** digest. It is NOT the darwin_x64
digest. Asset name and hash agree; the fail-closed `sha256sum -c -` at `:83` therefore
verifies rather than trips.

**Confirmed live, not merely by manifest arithmetic** — the job's own run log:

```
/home/runner/work/_temp/gitleaks_8.24.3_linux_x64.tar.gz: OK
8.24.3
```

Run `31785159015` job `94719333969`, `head_sha=a922d8f9…`, `event=pull_request`,
`conclusion=success`. The dual-pin is sound for the ubuntu-latest runner.

### V-2 — AR-1 mode-1 preserved: delegated caller UNTOUCHED

`git diff origin/main a922d8f9 -- .github/workflows/gitleaks.yml` → **empty**. The file is
byte-identical to main. The registered required context `gitleaks / Secrets Scan`
retains its reporter; the mode-2 "unreportable required context hangs PENDING forever"
hazard is not created.

### V-3 — Founding premise verified by direct probe (Gate A.1 provenance-root)

The PR's entire rationale rests on the claim that the pinned upstream reusable workflow
swallows its exit code. Probed directly at
`autom8y/autom8y-workflows/.github/workflows/security-gitleaks.yml@f5601acb…`:

- `:27` — `run: gitleaks detect --source . --report-format sarif --report-path gitleaks-results.sarif --verbose || true`

The `|| true` is **real**. The founding claim resolves to a live source; it is not an
inherited premise. `:8` `name: Secrets Scan` inside job id `gitleaks` also confirms the
composite context derivation `gitleaks / Secrets Scan`.

### V-4 — No check-run context collision

Empirically distinct in `gh pr checks 368`:

- `Secrets Scan (enforcing)` — NEW (this PR)
- `Secrets Scan (Gitleaks)` workflow → context `gitleaks / Secrets Scan` — pre-existing
- `TruffleHog Secrets Scan (Scheduled)` — schedule + workflow_dispatch only, no PR trigger

Fleet-wide workflow-name sweep over all 14 workflows at head shows no duplicate `name:`.
The honest non-spoofed job name is preserved as the BUILD note requires.

### V-5 — No merge-queue starvation hazard

Zero `merge_group:` triggers across all 14 workflows. The repo does not use a merge queue,
so the classic "required context registered but not firing on merge_group → queue hangs
forever" failure mode is **not reachable**. This is the one registration-adjacent NO-GO
class that could have bitten at ACTION 2; it is ruled out.

### V-6 — Action pinned by SHA, resolves honestly

`actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd # v5.0.1`. GitHub API:
tag `v5.0.1` → `93cb6efe18208431cddfb8368fd83d5badbf9bfd`. Pin and comment agree.

### V-7 — Failure semantics sound

- No `|| true`, no `continue-on-error` anywhere in the file.
- `set -euo pipefail` on both `run:` blocks; exit propagates unswallowed.
- Baseline guard `test -f .gitleaksignore` (`:68`) under default `bash -e` → fails loud
  and early, before the opaque-scan-failure path. Observed executing in the run log.
- `--redact` on, `--verbose` absent, no `--report-path` → no report file is written at all.
- `fetch-depth: 0` is effective: the run reports `1621 commits scanned` (a shallow
  checkout would have silently scanned almost nothing).
- Least privilege: `permissions: contents: read` at both workflow and job scope;
  `persist-credentials: false`; zero `${{ }}` interpolation inside any `run:` block
  (no template-injection surface). `pull_request`, not `pull_request_target`.

---

## §3 OWN-HANDS EMPIRICAL LEGS (rite-disjoint; none inherited from author or qa)

### L-1 — Two-sided teeth proof, my own construction

Ran the **exact shipped command shape** against fixtures I built myself.

| Arm | Input | Result |
|---|---|---|
| A (broken) | synthetic all-zeros string structurally matching `asana-native-pat` | `leaks found: 1` → **EXIT=1** |
| B (near-miss) | same shape, hex segment shortened below the `{32,}` floor | `no leaks found` → **EXIT=0** |

The gate **bites on the defect and passes the no-defect variant**. Teeth are
discriminating, not a blanket-red no-op. Additionally, ARM A printed **only the count** —
the value never appeared in output, confirming the `--redact` + no-`--verbose` CR-5
posture on the failure path that CI has never exercised (CI has only ever run green).

### L-2 — Baseline is exactly load-bearing, 1:1, no dead entries

History scan of the repo, `--redact`, count-only:

| Condition | Result |
|---|---|
| WITHOUT baseline (empty ignore file) | `1933 commits scanned` → **`leaks found: 49`** |
| WITH PR baseline | `1933 commits scanned` → **`no leaks found`** |

49 findings suppressed by exactly 49 fingerprint entries — 1:1, no over-suppression
margin, no dead weight. All 49 entries are well-formed 4-field `commit:path:rule:line`
tuples (zero malformed).

Methodology note: I defeated the baseline by pointing at an **empty file**, not by
redirecting the flag at a directory. This sidesteps the engine behaviour the builder
recorded as R-CC7-2 (directory redirect does not disable baseline application). The A/B is
clean — `.gitleaksignore` is absent from `origin/main` and absent from my working tree, so
no root-level auto-discovery contaminated either arm.

### L-3 — POST-MERGE main-leg proven green (forward receipt no prior critic could produce)

`mergeStateStatus: BEHIND` — the PR head is 1 commit behind main. Because this scan is
**history-wide**, a PR-leg green does not by itself prove the post-merge main-leg green:
main's extra commit is content the PR-branch scan never saw. That commit adds 15 `.ledge/`
markdown files — including the CC-7 security documents *about secret findings*, which is
exactly the content class that could plausibly trip `generic-api-key`.

Tested directly. Materialised main's 15 delta files at their real paths plus the PR's
config and baseline, scanned with the repo `.gitleaks.toml`:

```
scanned ~243613 bytes (243.61 KB) in 158ms
no leaks found          EXIT=0
```

Corroborated at full scale by L-2: the with-baseline history scan over my local
**1933-commit superset** (vs CI's 1621) is green.

**The enforcing gate will be green on main immediately after merge.** No self-inflicted
red on a security-critical context.

### L-4 — R-CC7-3's UV-P is DISCHARGED

BUILD `:328` filed R-CC7-3: *"The workflow has never executed. zizmor has never seen it…"*
with `[UV-P: the new workflow passes zizmor and all repo CI gates | METHOD: observe the CI
matrix on the first PR run | REASON: F-4 — nothing is pushed]`.

I am the first reviewer with a CI matrix. Discharging by observation:

- `zizmor / Actions Security Audit` — **pass**; run log shows
  `zizmor v1.23.1 … completed ./.github/workflows/gitleaks-enforcing.yml`. The new file
  was audited by name, not merely present during a passing run.
- `zizmor` — pass · `Analyze (actions)` (CodeQL) — pass · `Secrets Scan (enforcing)` — pass

**UV-P R-CC7-3 → DISCHARGED.** The design-conformance claim is now an observed-run claim.

### L-5 — Fingerprint anchoring: 46 on-main, 3 inert (SAFE direction)

The 49 fingerprints resolve to 26 distinct commits (matching ADVERSARY `:194`). Of those,
**23 are ancestors of `origin/main`; 3 are not**:

| Commit | Lives on | Rule class |
|---|---|---|
| `20e92a6c…` | `fix/seam1-entity-blind-prober-plane-split` (local) | `generic-api-key` |
| `48f54bcf…` | `feat/gfr-engine` (local) | `generic-api-key` |
| `51cc12fe…` | `chore/preserve-cutover-and-windowed-mrr-receipts` (**has origin/ counterpart**) | `generic-api-key` |

Consequence: **46 of 49** fingerprints are load-bearing on main; 3 are inert there. This is
the concrete mechanism behind the disclosed finding-count-instability carry — the baseline
was generated from a clone whose scan reached side-branch commits.

Direction is **SAFE**, three ways:
1. Inert entries cannot un-suppress and cannot cause a red.
2. All 3 are `generic-api-key` — the high-false-positive class — and **zero** are
   `asana-native-pat`, so the off-main residue sits entirely in the benign class. This
   *narrows* R-CC7-1's live-exposure surface rather than widening it.
3. One (`51cc12fe…`) is pre-covering a **live remote branch**: if a PR opens from
   `chore/preserve-cutover-and-windowed-mrr-receipts`, the gate scans that history, hits
   the finding, and the baseline already covers it → green rather than a surprise red.

Independent corroboration of the carry: the finding count held at **49** across three
different commit denominators (CI 1621 / builder-local 1924 per BUILD `:125` / my local
1933). The instability is in the denominator; the numerator is stable.

### L-6 — Squash-merge cannot stale any fingerprint

The PR introduces exactly 1 commit. **Zero** baseline fingerprints reference it (or any
PR-introduced commit). All 49 anchor to pre-existing history. If the repo merges by squash
— which rewrites PR commits into a new SHA — no fingerprint goes stale. Merge strategy is
therefore not a correctness variable here.

### L-7 — The enforcing leg is a supply-chain IMPROVEMENT over the delegated leg

Worth crediting explicitly. Upstream `security-gitleaks.yml@f5601acb` `:22-24` installs the
same version by piping `curl` **straight into `tar` under `/usr/local/bin` with no checksum
at all**. The enforcing leg pins version AND sha256 and fails closed. Upstream also writes
a `--verbose` SARIF report (report bodies carry secret values); the enforcing leg writes no
report. On both supply-chain and CR-5 axes the new job is strictly better than the leg it
sits alongside.

---

## §4 Disclosed carries — CONFIRMED PRESENT, NOT DROPPED (not re-litigated)

| Carry | Disclosure anchor | Status |
|---|---|---|
| R-CC7-1 suppressed-not-triaged (31 live-at-HEAD masked, 0 `asana-native-pat`) | BUILD `:326`; ADVERSARY CH-03 `:102`, `:184`; CRITIQUE attack 3 `:53`, `:86` | Present, load-bearing, with a named follow-on triage pass |
| Finding-count instability, SAFE direction | BUILD `:125`, `:150` | Present; independently corroborated and mechanistically explained at L-5 |
| CF-4 regex residual (one-sided: trips LESS than reality, never more) | BUILD `:323`; ADVERSARY `:189`; CRITIQUE `:140-142` (5-digit-gid miss) | Present; marked UNCLOSEABLE under CR-5, carried not dismissed |
| Registration deliberately absent from this PR | BUILD `:337` `rung-STAGED`; workflow header `:18-27`; RUNBOOK `:22`, `:247` operator-reserved | Present; ACTION 2 authored, never executed, ordered strictly after land |

The baseline's own composition corroborates the R-CC7-1 shape: 28 `generic-api-key`,
15 `asana-client-id`, 5 `asana-native-pat`, 1 `jwt`. The 5 `asana-native-pat` suppressions
are historical-only, consistent with the critique's **0 live at HEAD** finding.

---

## §5 CONDITIONS (none block the merge; all bind ACTION 2 / post-land)

### C-1 — `cancel-in-progress: true` also governs the `push: main` leg (ADVISORY)

`:33-35` sets `group: gitleaks-enforcing-${{ github.ref }}` with `cancel-in-progress: true`.
This conforms to house convention — it mirrors `gitleaks.yml` `:3-5` exactly and matches 6
sibling workflows — so it is **not drift**, and the PR leg is unaffected (cancelling a
superseded PR-head scan is correct).

But the repo already demonstrates the discriminator: `post-merge-coverage.yml` uses
`cancel-in-progress: false  # let post-merge gates run to completion`.

The interaction that matters: the RUNBOOK requires the job be **observed reporting on main**
before registration. If two commits land on main in close succession, the earlier main-run
is cancelled — and pre-registration, the main-push leg is the *only* leg that demonstrates
the gate operating. An operator could register against an observation window whose run was
cancelled.

**Condition**: before executing ACTION 2, confirm the observed main-branch run reached
`conclusion: success` and was not `cancelled`. Optionally adopt
`cancel-in-progress: ${{ github.event_name == 'pull_request' }}`, matching the
post-merge-coverage precedent. Not merge-blocking.

### C-2 — Trigger scope is main-only; name the coverage boundary (ADVISORY)

`:37-41` scopes both triggers to `branches: [main]`. A PR targeting any non-main base
(stacked branch, release branch) does **not** run the enforcing gate. This is coherent with
registering the context on main only, but the boundary is currently implicit. **Condition**:
state it explicitly in the RUNBOOK so the gate's coverage limit is a documented property
rather than a discovered one.

### C-3 — Keep R-CC7-1 attached downstream (inherited, restated)

Per ADVERSARY CH-03's falsification pathway: any future artifact citing this green gate as
evidence that history contains no live secret converts a disclosed residual into a
false-green overclaim. The gate proves *"no unbaselined finding"*, never *"history clean"*.
**Condition**: R-CC7-1 travels with every downstream citation until the triage pass runs.

### C-4 — Merge hygiene (INFORMATIONAL, no action required)

`mergeStateStatus: BEHIND`, `mergeable: MERGEABLE`. If branch protection requires
up-to-date branches, an update-branch will re-trigger checks. Outcome is already proven
green either way (L-3, L-6), so this is a process step, not a risk.

---

## §6 CI STATE AT VERDICT TIME

Polled to completion. **27 pass / 3 skipping / 0 pending / 0 failing** at head `a922d8f9`.

Relevant contexts: `Secrets Scan (enforcing)` **pass** (15s) · `gitleaks / Secrets Scan`
**pass** · `zizmor / Actions Security Audit` **pass** · `Analyze (actions)` **pass** ·
`CodeQL` **pass** · all 4 `ci / Test` shards **pass** · `ci / Lint & Type Check` **pass** ·
`ci / Aggregate Coverage Gate` **pass** · `dependency-review` **pass**.

Skipping (path/conditional, benign): `[code]smith`, `ci / Convention Check`,
`ci / Integration Tests`.

No verdict is rendered on a pending check.

---

## §7 VERDICT

**GO-WITH-CONDITIONS.**

Merge #368 to main. Nothing in §5 blocks the merge; every condition binds ACTION 2 or
post-land operation.

The change is a well-behaved pipeline citizen: correct triggers, house-conventional
concurrency, least-privilege permissions, SHA-pinned action, fail-closed dual-pinned binary
on the correct architecture, unswallowed exit propagation, no report artifact, a loud
baseline guard, and no interaction hazard with the other 13 workflows. The delegated leg is
untouched, so AR-1 mode-1 holds. The gate has two-sided teeth I proved with my own
fixtures, the baseline is exactly load-bearing with no dead entries, and the post-merge
main-branch run is proven green in advance. It is honestly non-biting until registration,
and it says so in its own header.

Evidence ceiling **MODERATE** — self-ref cap per `self-ref-evidence-grade-rule`. I do not
grade the author STRONG. Every finding above carries a file:line or command receipt.

### Handoff

- **To operator**: ACTION 2 per RUNBOOK, gated on C-1 (verify the observed main run
  succeeded and was not cancelled).
- **To chaos-engineer** (rite-disjoint resilience verification, per sre routing): the
  registered-and-biting state is unproven by construction — the RUNBOOK's own
  `[UV-P: … observe a PR's required-checks list and mergeStateStatus after registration]`
  is the open leg. A post-registration failure-injection (deliberately-broken input on a
  throwaway PR, confirming the merge is actually *blocked*, then confirming clean revert)
  closes it. That is the only remaining rung between "reports" and "bites".
