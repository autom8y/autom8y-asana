---
type: decision
status: accepted
rung: rung-STAGED — authored, never executed. NOT executed this session and NOT executable this session (F-4)
artifact_id: RUNBOOK-cc7-branch-protection-registration-2026-08-14
wave: chain-of-custody-closure
sprint: CC-7 (hard edge E1) — ACTION 2 of the TWO-ACTION boundary
date: 2026-08-14
author: principal-engineer (10x-dev) — sole writer for CC-7
authority: operator ruling R-3 (AMENDED TWO-ACTION boundary); GATE-coc-phase2-entry-2026-08-14.md §3 CC-7 (:60-:61) + §4 wall 7 (:80)
executor: REPO ADMIN — operator-reserved. NO AGENT SEAT MAY EXECUTE ANY COMMAND IN THIS FILE.
paired_artifact: BUILD-cc7-gitleaks-biting-gate-2026-08-14.md (ACTION 1, rung-BUILT-DARK)
depends_on: ACTION 1 must LAND on main AND be OBSERVED reporting before step 3 runs
self_assessment_cap: MODERATE (single seat, self-referential; branch-protection state read own-hands, un-corroborated)
cr5_compliance: no credential value handled; branch-protection READS only were performed in authoring this file — zero WRITE calls
---

# RUNBOOK — CC-7 branch-protection registration (ACTION 2, STAGED)

> **DO NOT EXECUTE ANY COMMAND IN THIS FILE FROM AN AGENT SEAT.**
> Every command below is a WRITE to branch protection on `main`. Branch-protection
> registration **execution** is operator-reserved (`GATE-coc-phase2-entry-2026-08-14.md:80`),
> and no merge word exists (F-4), so ACTION 1 cannot have landed yet — which means the
> precondition for step 3 is, by construction, **not satisfiable this session**.

---

## §1 What this registers, and why it is a separate action

`.github/workflows/gitleaks-enforcing.yml` (ACTION 1) adds a **plain local job**. A
plain local job reports a **simple** check-run name, not the `X / Y` composite that
reusable-workflow nesting produces (`CRITIQUE-cc6-gitleaks-recon-2026-08-13.md:104-112`).
So the enforcing job reports a NEW context that branch protection does not require.

Until this runbook executes, the enforcing job is **red-but-non-blocking** — AR-1 mode 1,
the exact silent non-biting gate this wave exists to close
(`CRITIQUE-cc6…:119-123`). Shipping ACTION 1 alone and calling it a gate would
reproduce the failure class, not fix it.

**Context to register:**

```
Secrets Scan (enforcing)
```

**app_id to pin it to:** `15368` (GitHub Actions) — matching all eight existing
Actions-sourced contexts. See §4 for why the app pin matters.

---

## §2 ORDERING LAW — the one thing that must not be got wrong

> **REGISTER ONLY AFTER THE JOB HAS LANDED ON `main` AND HAS BEEN OBSERVED REPORTING.**
> Never before.

This is AR-1 **mode 2** inverted (`CRITIQUE-cc6…:124-127`;
`GATE-coc-phase2-entry-2026-08-14.md:60`). GitHub holds a required status check that
has nothing to report in the **PENDING** state indefinitely. Register
`Secrets Scan (enforcing)` before the workflow exists on `main`, and:

- every open PR immediately shows an unsatisfiable required check;
- every merge blocks, with no run that can ever turn it green;
- `enforce_admins: true` is set on this branch (§3 step 1), so **admins cannot merge
  past it either**;
- recovery requires a second branch-protection write to remove the context — i.e. the
  rollback in §5, executed under merge-freeze pressure.

The ordering is not a preference. It is the difference between a gate and an outage.

---

## §3 Procedure

### Step 0 — PRECONDITION GATE (all four must be TRUE; if any is FALSE, STOP)

1. ACTION 1 is **merged to `main`** — `.github/workflows/gitleaks-enforcing.yml` and
   `.gitleaksignore` are present at `origin/main`.
2. At least one CI run of the workflow has **completed on `main`** (not queued, not
   cancelled).
3. Step 1 below has been run and its output shows the exact context string.
4. The executor is a **repo admin** with branch-protection write scope, acting on the
   operator's word.

### Step 1 — READ the observed check-run name (do not trust the derivation)

```bash
gh api repos/autom8y/autom8y-asana/commits/main/check-runs \
  --jq '.check_runs[] | {name, app: .app.slug, conclusion}'
```

**Expected:** a row whose `name` is exactly `Secrets Scan (enforcing)` with
`app: "github-actions"`.

**This step exists because the string is a UV-P until a run reports it**
(`BUILD-cc7-gitleaks-biting-gate-2026-08-14.md` §4). The derivation is mechanically
grounded, but the observed name is authoritative. If the observed name differs in ANY
byte — spacing, capitalisation, parentheses, a matrix suffix — **register the observed
string, not the string in this document**, and correct this runbook. A one-byte
mismatch produces a permanently-PENDING context: the §2 outage.

### Step 2 — RE-READ current protection immediately before writing

```bash
gh api repos/autom8y/autom8y-asana/branches/main/protection \
  --jq '{strict: .required_status_checks.strict, checks: .required_status_checks.checks, enforce_admins: .enforce_admins.enabled, linear: .required_linear_history.enabled}'
```

**State observed own-hands 2026-08-14** (`gh api …/branches/main/protection`, exit `0`):

- `strict: true`
- `enforce_admins: true`
- `required_linear_history: true`
- `required_pull_request_reviews`: **absent from the response** (unconfigured)
- `restrictions`: **absent from the response** (unconfigured)
- `required_status_checks.checks` — **9 contexts**:

| # | context | app_id |
|---|---|---|
| 1 | `gitleaks / Secrets Scan` | 15368 |
| 2 | `dependency-review / Dependency Review` | 15368 |
| 3 | `ci / Test (shard 1/4)` | 15368 |
| 4 | `ci / Test (shard 2/4)` | 15368 |
| 5 | `ci / Test (shard 3/4)` | 15368 |
| 6 | `ci / Test (shard 4/4)` | 15368 |
| 7 | `ci / Lint & Type Check` | 15368 |
| 8 | `ci / Fleet Conformance Gate` | 15368 |
| 9 | `CodeQL` | 57789 |

If step 2's live output differs from this table, **do not paste the payload in step 3
blindly** — rebuild it from the live output. The payload is a full replacement of the
`required_status_checks` sub-object.

`gitleaks / Secrets Scan` (row 1) is **KEPT**. It is the delegated always-green job;
ACTION 1 was added alongside it precisely so this context keeps reporting
(`CRITIQUE-cc6…:124-127`). Do not remove it here. Its retirement belongs to fix
locus (a) — see §6.

### Step 3 — THE WRITE (primary form)

Sub-resource PATCH. Touches **only** `required_status_checks`; cannot clobber
`enforce_admins`, `required_linear_history`, reviews, or restrictions.

```bash
gh api --method PATCH \
  repos/autom8y/autom8y-asana/branches/main/protection/required_status_checks \
  --input - <<'JSON'
{
  "strict": true,
  "checks": [
    { "context": "gitleaks / Secrets Scan",              "app_id": 15368 },
    { "context": "dependency-review / Dependency Review", "app_id": 15368 },
    { "context": "ci / Test (shard 1/4)",                 "app_id": 15368 },
    { "context": "ci / Test (shard 2/4)",                 "app_id": 15368 },
    { "context": "ci / Test (shard 3/4)",                 "app_id": 15368 },
    { "context": "ci / Test (shard 4/4)",                 "app_id": 15368 },
    { "context": "ci / Lint & Type Check",                "app_id": 15368 },
    { "context": "ci / Fleet Conformance Gate",           "app_id": 15368 },
    { "context": "CodeQL",                                "app_id": 57789 },
    { "context": "Secrets Scan (enforcing)",              "app_id": 15368 }
  ]
}
JSON
```

All 9 pre-existing contexts are re-listed with their original `app_id` values; the
10th line is the only addition. `strict: true` is re-asserted explicitly.

### Step 4 — VERIFY (mandatory; the write is not done until this passes)

```bash
gh api repos/autom8y/autom8y-asana/branches/main/protection \
  --jq '{strict: .required_status_checks.strict, n: (.required_status_checks.checks|length), enforce_admins: .enforce_admins.enabled, linear: .required_linear_history.enabled, checks: .required_status_checks.checks}'
```

**Assert all four:**
- `n == 10`
- `strict == true`
- `enforce_admins == true`
- `linear == true`
- `checks` contains `{"context": "Secrets Scan (enforcing)", "app_id": 15368}` **and**
  still contains all 9 rows from the §3 step-2 table.

If any assertion fails, execute §5 rollback immediately.

### Step 5 — CONFIRM IT BITES (the point of the whole exercise)

The registration is not attested until a red enforcing run is observed **blocking** a
merge, or a green one is observed **required**. Open a scratch PR and read
`mergeStateStatus` / the required-checks list on it. Until that is observed, the
biting claim is `[UV-P: the registered context actually blocks a merge | METHOD:
observe a PR's required-checks list and mergeStateStatus after registration | REASON:
registration has not been executed]`.

---

## §4 Why NOT the other two write forms

| form | endpoint | verdict |
|---|---|---|
| **Append-contexts** | `POST …/protection/required_status_checks/contexts` | **REJECTED.** Structurally cannot clobber, which is attractive — but the legacy `contexts` surface registers the new check with **`app_id: null` (any app)**, while all 8 existing Actions contexts are pinned to `15368`. That would let any app satisfy the secrets-scan gate: a weakening, on the one context whose whole purpose is integrity. |
| **Full-object PATCH** | `PATCH …/branches/main/protection` | **NOT RECOMMENDED** (offered only as a documented fallback). This endpoint **replaces the entire protection object**. Every field omitted from the payload is reset. It would require correctly re-supplying `enforce_admins: true`, `required_linear_history: true`, `required_pull_request_reviews: null`, and `restrictions: null` — and the last two are *absent from the GET response entirely*, so they must be supplied as explicit `null`s that a careless copy of the GET output would omit. The blast radius of one dropped key is the branch's whole protection posture. If it must be used, diff the post-write GET against the §3 step-2 table field by field before declaring done. |

---

## §5 Rollback

Single action: re-run the §3 step-3 PATCH with the `Secrets Scan (enforcing)` line
**removed**, restoring the 9-context state, then re-run §3 step 4 asserting `n == 9`.

Rollback conditions:
- step 4 verification fails;
- the observed check-run name did not match and was registered anyway;
- merges block on a PENDING `Secrets Scan (enforcing)` that never reports.

Rollback is cheap and complete: de-registering the context returns the branch to its
pre-CC-7 posture exactly. It does **not** remove the enforcing workflow — the job keeps
running and keeps reporting, just non-blocking (back to AR-1 mode 1). Removing the job
too is a separate code change.

---

## §6 Retirement path (when upstream is fixed)

If the upstream `|| true` is ever removed from
`autom8y/autom8y-workflows/.github/workflows/security-gitleaks.yml` (fix locus (a),
`RECON-gitleaks-enforcement-locus-2026-08-13.md:172-174`), the delegated
`gitleaks / Secrets Scan` context becomes enforcing on its own and this local fork is
redundant. Retire in this order — **de-register before deleting**, the mirror of §2:

1. PATCH `required_status_checks` back to the 9-context list (§5).
2. Delete `.github/workflows/gitleaks-enforcing.yml`.
3. Keep `.gitleaksignore` — the upstream enforcing job needs the same baseline.

Deleting the workflow first would leave a registered, unreportable context: the §2
outage again, arrived at from the other end.

---

## §7 Fences

- **NOT EXECUTED.** Zero `gh api` WRITE calls were made in authoring this file. The
  §3 step-2 state table came from READ calls only (`gh api …/branches/main/protection`,
  exit `0`).
- **NOT EXECUTABLE THIS SESSION.** F-4 holds; no merge word exists; ACTION 1 cannot
  land; step 0's precondition 1 is therefore unsatisfiable. This is a consequence of
  the fence, not a limitation of the work (`GATE-coc-phase2-entry-2026-08-14.md:61`).
- **Operator-reserved.** Branch-protection registration execution is named
  operator-reserved and untouchable by any seat (`GATE…:80`).
- **MODERATE self-cap.** Single seat; the state table is this seat's own-hands read,
  un-corroborated by a rite-disjoint second reader; re-read it at step 2 rather than
  trusting this snapshot.

**Rung: `rung-STAGED`.**
