---
type: decision
artifact_type: defer-watch-discharge
artifact_id: DISCHARGE-dw-coc-03-locus-a-2026-08-14
status: accepted
wave: coc-arm-the-instrument
session: session-20260814-210158-d6cdff92
self_assessment_cap: MODERATE
discharges: DW-COC-03 locus (a)
---

# DISCHARGE — DW-COC-03 locus (a): the fleet `|| true` swallow is retired at source

## 1. What was open

DW-COC-03 (gitleaks fleet gap) pegged the fleet reusable workflow
`autom8y/autom8y-workflows/.github/workflows/security-gitleaks.yml:27`, whose
`gitleaks detect … || true` unconditionally discarded the scanner's exit code —
making the delegated `gitleaks / Secrets Scan` check ALWAYS-GREEN in every
consuming repo since the file's creation (2026-04-01). Locus lettering per
`.ledge/reviews/RECON-gitleaks-enforcement-locus-2026-08-13.md` §3; the peg
restated at `.ledge/handoffs/HANDOFF-coc-landing-close-2026-08-14.md:68` and
`HANDOFF-coc-phase2-close-2026-08-14.md:85`.

## 2. Before-side evidence (the wave's cited canary)

`VERDICT-cc8-partial-attest-2026-08-14.md` §5.4 (origin/main @ f6de435f): on the
attester's own secret-bearing canary commit (autom8y-asana PR #374, head
`39aa4240`), the two legs disagreed — `Secrets Scan (enforcing)` = **FAILURE**
while the delegated fleet `gitleaks / Secrets Scan` = **SUCCESS**. Own-hands
empirical proof the delegated leg was non-biting; DW-COC-03 locus (a) OPEN from
observation, not just record.

## 3. The cure

autom8y-workflows **PR #30**, squash-merged to `main` as **`6753f943`**
(2026-08-14T19:32Z). One file, one concern: ` || true` removed from the run
line (gitleaks defaults `--exit-code 1`, verified v8.24.3 `cmd/root.go:57`);
SARIF generation/upload untouched (already `if: always()`); explanatory comment
added.

**Rejected alternative — baseline-path `workflow_call` input:** unnecessary.
gitleaks v8.24.3 auto-discovers a repo-root `.gitleaksignore` with no flag
(`cmd/root.go` sites `:249/:255/:261`), empirically corroborated by the
reusable's own ingested SARIF reporting `results_count: 0` at autom8y-asana HEAD
`f6de435f` despite the cred-t21 history findings — the committed baseline is
honored by the un-swallowed scan with zero consumer config.

## 4. After-side proof (two-sided, single-variable — B-2 receipts)

| Arm | Branch (base) | Head sha | Run id | `gitleaks / Secrets Scan` | UTC |
|---|---|---|---|---|---|
| RED (bite) | `canary/b2-red` (6753f943) | `5151629b` | 31834106067 | **FAILURE** — `leaks found: 2`, exit 1 | 19:37:33–52Z |
| HONEST-NEGATIVE (guard) | `canary/b2-blind` (6753f943, workflow byte-restored to c824da59) | `7ae9d883` | 31834109249 | **SUCCESS** — identical `leaks found: 2`, swallowed | 19:37:35–50Z |
| GREEN-1 (clean, PR #30) | `ci/retire-gitleaks-exit-swallow` | `4c7f466a` | 31833523709 | SUCCESS — "no leaks found", 91 commits | 19:30Z |
| GREEN-2 (clean, post-merge main) | `main` | `6753f943` | 31833724353 | SUCCESS — "no leaks found" | 19:32Z |

Single-variable causation: fixture byte-identical across RED/BLIND (`git diff`
empty; identical two `aws-access-token` fingerprints in both runs); the only
executable delta is the swallow itself. Doctrine held — no defect injected into
working code: RED is input-only against unmodified production `main`; BLIND is a
verbatim restoration of the historical workflow version. Method note: the naive
blind design (branch from pre-merge base) is defeated by `pull_request` running
the **merge-commit** workflow; proven via `git merge-tree` before spending a PR
cycle, then designed around by basing both arms on `6753f943`. Cleanup verified
via API: PRs #31/#32 closed unmerged, branches 404, zero open alerts, fixture
unreachable from `main`.

## 5. Scope — what this discharge does and does not claim

- **Retired at source; INERT downstream.** All 9 external consumers pin
  immutable SHAs (`44b771e5` ×7, `f5601acb` ×2 — B-0 census, 217/217 workflow
  files across all 24 org repos). Each consumer arms only at a deliberate
  re-pin. The only immediately-armed surface is autom8y-workflows itself
  (mutable local-path self-consumption), proven green at HEAD.
- **Consumer re-pins: NOT-DONE this wave — operator lever.** Evidence staged
  for the asana re-pin: it would arm **GREEN** (auto-discovered 49-entry
  baseline; both the enforcing leg and the reusable's SARIF report zero findings
  at `f6de435f`). Fingerprint fence, verbatim per
  `TRIAGE-r-cc7-1-baseline-findings-2026-08-14.md` §7: "All 31 baseline-masked
  live-at-HEAD findings are dispositioned (0 rotate-recommended, 28
  false-positive, 3 accepted-with-owner under DW-COC-06-proposed); 44 of 49
  baseline fingerprints anchor HEAD-surviving content, 5 of 49 are history-only
  and all 5 are the cred-t21 `asana-native-pat` entries." The gate proves "no
  unbaselined finding", never "history clean" — cred-t21 rotation (F-2) remains
  operator-pending. The 8 private consumers carry **no baseline at all** (4 also
  no `.gitleaks.toml`): their first un-swallowed run is unbaselined by
  construction — honest RED is possible there and is the point, but re-pinning
  them blind violates the verification rule; per-repo enumeration first.
  Monorepo re-pin is a **two-file change** (`.github/workflows/gitleaks.yml:13`
  + `.github/required-contexts.expected.txt:34` parity guard).
- **Enforcing-fork retirement: operator/admin-reserved, ordered.** De-register
  `Secrets Scan (enforcing)` from branch protection FIRST, THEN delete
  `gitleaks-enforcing.yml` — order corrected on the record by autom8y-asana
  PR #377 (`f6dbb7b8`); the inverse order freezes all merges with no bypass
  under `enforce_admins: true`.

## 6. New findings surfaced by this discharge (routed onward)

- **GHAS SARIF leg does not gate** (MODERATE): gitleaks SARIF lands at severity
  `warning`; code-scanning checks fail only on `error`. During RED, two genuine
  open alerts existed while the `github-advanced-security` check reported
  SUCCESS. The exit code is the only biting instrument; check color on the GHAS
  leg is not evidence of a clean scan.
- `fetch-depth: 0` means a run scans all fetched refs — findings on other live
  branches can surface in unrelated runs.

Evidence grade: MODERATE (self-assessment cap); the run receipts in §4 are
mechanical and independently re-queryable by run id.
