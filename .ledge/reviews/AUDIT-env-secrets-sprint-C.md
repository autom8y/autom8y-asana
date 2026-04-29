---
type: review
review_subtype: audit
artifact_id: AUDIT-env-secrets-sprint-C-2026-04-20
schema_version: "1.0"
status: proposed
lifecycle: proposed
initiative: "Ecosystem env/secret platformization alignment"
sprint: Sprint-C
sprint_id: hygiene-env-secrets-sprint-C
branch: hygiene/sprint-env-secret-platformization
baseline_sha: e22cca21
audited_commits:
  - sha: 86087830
    cfg_id: CFG-007
    subject: "chore(scripts): delete calc_mrr.py — subsumed by metrics CLI [CFG-007]"
  - sha: 1a13cafe
    cfg_id: CFG-008
    subject: "docs(know): document 6-layer env loader contract in .know/env-loader.md [CFG-008]"
  - sha: 97aed1bf
    cfg_id: BOY-SCOUT
    subject: "style(secretspec): fix typo contact -> contract in [profiles.cli] comment"
  - sha: "(full chain)"
    cfg_id: CFG-004
    subject: "CFG-004 closure verified in-place: ADR-0002 authored; .know/env-loader.md documents canonical name + alias; .env/defaults header references CFG-004 (cites legacy staleness — advisory)"
references:
  handoff: .ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md
  before_state: .ledge/reviews/smell-inventory-env-secrets-2026-04-20.md
  adr_profile: .ledge/decisions/ADR-env-secret-profile-split.md
  adr_bucket: .ledge/decisions/ADR-bucket-naming.md
  tdd: .ledge/specs/TDD-cli-preflight-contract.md
  prior_audit_A: .ledge/reviews/AUDIT-env-secrets-sprint-A.md
  prior_audit_B: .ledge/reviews/AUDIT-env-secrets-sprint-B.md
audit_lead_role: audit-lead
created_at: "2026-04-20T00:00:00Z"
verdict: REVISION-REQUIRED
sprint_closure_blocked: true
blocker_count: 1
advisory_count: 3
---

# Audit: Sprint-C — env/secret platformization (CFG-004 closure, CFG-007, CFG-008, Boy-Scout typo)

## 1. Verdict

**REVISION REQUIRED.**

All three Sprint-C commits (`86087830`, `1a13cafe`, `97aed1bf`) and the
in-place CFG-004 closure satisfy their declared acceptance criteria in
isolation. The bucket-naming ADR exists, the 6-layer `.know/env-loader.md`
exists and cross-links ADR-0001 + ADR-0002, `scripts/calc_mrr.py` is gone
with zero residual live references, MRR parity holds at `$94,076.00 / 71
combos`, and the Boy-Scout typo `contact → contract` is fixed.

However, a **CI-breaking test regression** introduced by CFG-006 (Sprint-B)
surfaced only at this final audit — Sprint-B audit explicitly recorded
"pytest not run against this repo as part of Sprint-B" (AUDIT-B §6 L372),
so the regression was latent. It is not a Sprint-C-introduced defect, but
it is a Sprint-closure blocker: without remediation, the first push of this
branch will turn the `Tests` job red.

**Regression**: 5 tests in `tests/unit/metrics/test_main.py::TestCliCompute`
pass at baseline `e22cca21` but fail at HEAD `97aed1bf` under a no-env
subshell (CI parity). They pass under the direnv-loaded shell. The CI
workflow `.github/workflows/test.yml:58` injects only
`ASANA_WORKSPACE_GID`, not `ASANA_CACHE_S3_BUCKET`/`ASANA_CACHE_S3_REGION`.
The 5 tests mock `load_project_dataframe` but do not mock the preflight
added by CFG-006 (`__main__.py:64-85`), so preflight exits 2 before the
mocked loader is ever called.

Bounded fix (one of three, chosen by team):
- **Fix A** (test-level, preferred): monkeypatch `ASANA_CACHE_S3_BUCKET`
  + `ASANA_CACHE_S3_REGION` at class level in `TestCliCompute` (one
  autouse fixture, ~4 lines). Keeps production preflight behavior; isolates
  test concerns.
- **Fix B** (test-level, alternative): patch
  `autom8_asana.metrics.__main__._preflight_cli_profile` in each
  `TestCliCompute` test's `with` stack. More invasive per-test, less
  recommended.
- **Fix C** (CI-level): add `ASANA_CACHE_S3_BUCKET=autom8-s3`
  `ASANA_CACHE_S3_REGION=us-east-1` to `test_env` in
  `.github/workflows/test.yml:58`. Solves CI but leaves the subshell
  regression unfixed for fresh-clone developers.

Route: back to **Janitor** for a one-commit fix (Fix A recommended). The
fix is bounded enough that no architect-enforcer revision is required; no
plan flaw is present. Upon janitor completion, re-audit the fix commit
only (delta audit), then proceed to sprint closure.

All other Sprint-C deliverables are clean. CFG-005 remains deferred per
the original handoff partitioning plan.

## 2. Per-Assertion Results

### CFG-004 — Bucket naming decision (commits: `1a13cafe` + ADR authored separately 18:24)

| # | Assertion | Expected | Actual | Pass/Fail | Evidence |
|---|-----------|----------|--------|-----------|----------|
| 1 | ADR exists at `.ledge/decisions/ADR-bucket-naming.md` | File present; 21 KB; documents Option A | `.rw-r--r-- 21k 20 Apr 18:24 .ledge/decisions/ADR-bucket-naming.md` | PASS | `ls -la` output §4-A |
| 2 | `.env/defaults` header reflects canonical decision | Header cites `autom8-s3` as canonical with ADR reference | Lines 12-21 cite `autom8-s3` as the dev bucket, explicitly warn against changing to `autom8y-s3`, and name CFG-004. Semantic staleness: header text says "until that decision is recorded" but the decision IS recorded (ADR-0002 dated same day). Advisory, not blocking. | PASS (with advisory — see §8 A-1) | `grep -n "autom8-s3\|autom8y-s3\|ADR-bucket-naming\|CFG-004" .env/defaults` — 6 hits at L15, L16, L18, L19, L20, L21 |
| 3 | `.know/` reflects canonical name + legacy alias; cites ADR-0002 | `.know/env-loader.md` names `autom8-s3` as canonical, `autom8y-s3` as non-canonical empty alias, cites ADR path | `.know/env-loader.md:117-148` — "Canonical S3 Bucket Name" section: "`autom8-s3` is canonical" (L121), "`autom8y-s3` is a non-canonical empty alias" (L129), explicit ADR path citation at L119 (`ADR-0002 (\`.ledge/decisions/ADR-bucket-naming.md\`)`) and again at L62 in cross-links table | PASS | Direct inspection |

### CFG-007 — Delete `scripts/calc_mrr.py` (commit `86087830`)

| # | Assertion | Expected | Actual | Pass/Fail | Evidence |
|---|-----------|----------|--------|-----------|----------|
| 1 | Parity: canonical metrics CLI returns `$94,076.00 / 71 combos` | Matches audit-B baseline | `active_mrr: $94,076.00 / Unique (office_phone, vertical) combos: 71` | PASS | §5 E2E Step 3 verbatim |
| 2 | `scripts/calc_mrr.py` deleted | `test ! -f scripts/calc_mrr.py` | `DELETED` | PASS | §4-B evidence |
| 3 | No residual live references (excl. `.ledge/`, `.sos/`) | `grep -rn calc_mrr --include=*.py/*.md/*.yml/*.yaml/*.toml/*.sh` returns zero after excluding audit trail | Zero hits | PASS | §4-C evidence |
| 4 | Tests pass — janitor reported 109/109 | Reproduce count | Three files modified by CFG-007 (`test_adversarial.py`, `test_compute.py`, `test_edge_cases.py`) pass 109/109 under both env conditions. The 109/109 count in the janitor commit body is scoped to these three files, not the full `tests/unit/metrics/` directory. | PASS (at stated scope) | §4-D evidence; §3 test result table |

### CFG-008 — `.know/env-loader.md` (commit `1a13cafe`)

| # | Assertion | Expected | Actual | Pass/Fail | Evidence |
|---|-----------|----------|--------|-----------|----------|
| 1 | Proper frontmatter (`domain`, `source_scope`, etc.) | Standard `.know/` schema | L1-20: `domain: env-loader`, `generated_at`, `expires_after`, `source_scope` (7 paths), `generator: janitor`, `source_hash`, `confidence: 0.92`, `format_version: "1.0"`, `update_mode: full`, incremental cycle keys | PASS | Direct inspection |
| 2 | 6-layer table with required columns | Layer / File path / Committed? / Encrypted? / Typical contents / a8-devenv.sh line range | L34-41: 6-row table with 6 columns: Layer, File path, Committed?, Encrypted?, Typical contents, `a8-devenv.sh` line. Row count = 6 (Layers 1-6) | PASS | Direct inspection |
| 3 | Cross-link section cites `scripts/a8-devenv.sh:_a8_load_env` AND `secretspec.toml` | Both referenced with line ranges | L53: `/Users/tomtenuta/Code/a8/scripts/a8-devenv.sh:310-417` (ecosystem-monorepo absolute path). L56-57: two `secretspec.toml` references — `[profiles.default]` and `[profiles.cli]`. L58-59: both validate commands. | PASS | Direct inspection |
| 4 | Worked example names `ASANA_CACHE_S3_BUCKET`; explains Layer placement, CLI profile promotion, ADR-0001 + ADR-0002 ties | All four elements present | L68-113: "Worked Example: `ASANA_CACHE_S3_BUCKET`". Layer 3 placement rationale (L72-80). Layer 5 override path (L82-91). Profile split (L93-100) explicitly cites ADR-0001. CFG-006 preflight integration (L102-109). Bucket-naming tie to ADR-0002 (L111-113). | PASS | Direct inspection |

### Boy-Scout typo fix (commit `97aed1bf`)

| # | Assertion | Expected | Actual | Pass/Fail | Evidence |
|---|-----------|----------|--------|-----------|----------|
| 1 | `secretspec.toml:19` now reads `contract` | No "contact" residual in header block | `grep -n "contact\|contract" secretspec.toml` — five hits, all `contract`; zero `contact`. L19: "degradation. Validates the contract defined in" | PASS | §4-E |

## 3. Commit-Level Review (7 commits, baseline → HEAD)

| SHA | CFG | Files (insertions/deletions) | Atomicity | Reversibility | Message Quality | Conventional Format | Verdict |
|-----|-----|------------------------------|-----------|---------------|-----------------|---------------------|---------|
| `b231314b` | CFG-001 | `.env/defaults` (+19/-0) | ATOMIC — single file, single concern | Pure additive | Body explains Layer 3 role, cites `a8-devenv.sh` line range | `chore(env): ...` | ATOMIC-CLEAN |
| `8f9a2fd2` | CFG-002 | `.env/local.example` (+60/-3) | ATOMIC — single file, single concern | Revertible — new header block + placeholder additions | Documents 6-layer precedence, lists placeholders | `docs(config): ...` | ATOMIC-CLEAN |
| `6fa1afc4` | CFG-003 | `secretspec.toml` (+37/-1) | ATOMIC | Pure additive at tail (`[profiles.cli]` table) + comment-only header | Body cites ADR-0001, enumerates required vars, records binary absence, names positive/negative controls | `config(secretspec): ...` | ATOMIC-CLEAN |
| `f5fe16b4` | CFG-006 | `src/autom8_asana/metrics/__main__.py` (+107/-0) | ATOMIC | Revertible — single call-site insertion | Cites TDD-0001 Alt-C, exit-code semantics, `--list` bypass, grep counts | `feat(metrics): ...` | ATOMIC-CLEAN (but see §6 regression — tests left broken; a test-update companion commit was omitted) |
| `86087830` | CFG-007 | `scripts/calc_mrr.py` (-196), 3 test-comment lines (+3/-3) | ATOMIC — deletion + tightly-coupled comment updates in 3 test files (total 3 insertions, 3 deletions, all comment-only) | Revertible — single `git revert` restores file and comments | Excellent body: parity verification output, delta note on section classification, reference cleanup enumerated, tests-pass claim (109/109 at 3-file scope) | `chore(scripts): ...` | ATOMIC-CLEAN |
| `1a13cafe` | CFG-008 | `.know/env-loader.md` (+156/-0) | ATOMIC — new file | Pure additive | Documents table, cross-links, worked example | `docs(know): ...` | ATOMIC-CLEAN |
| `97aed1bf` | BOY-SCOUT | `secretspec.toml` (+1/-1) | ATOMIC — 1-char typo fix | Revertible | One-line, addresses Sprint-B §8 advisory #2 | `style(secretspec): ...` | ATOMIC-CLEAN |

**Dependency ordering**: CFG-001 → CFG-002 → CFG-003 → CFG-006 → CFG-007 → CFG-008 → Boy-Scout. Every declared dependency edge in the handoff (`dependencies: [CFG-001]`, `[CFG-003]`, `[CFG-001, CFG-002, CFG-003]`) is respected by commit order.

**Working-tree hygiene across sprint**: Harness drift (`.claude/*`, `.gemini/*`, `.knossos/*`, `.know/aegis/baselines.json`, `.ledge/reviews/WS5-asana-convergence-report.md`, `.sos/sessions/.locks/__create__.lock`, `aegis-report.json`) is pre-existing ambient state per Sprint-A+B audits. `git log --oneline e22cca21..HEAD` shows exactly 7 commits touching exactly 9 distinct file paths (`.env/defaults`, `.env/local.example`, `secretspec.toml`, `src/autom8_asana/metrics/__main__.py`, `scripts/calc_mrr.py`, `tests/unit/metrics/test_adversarial.py`, `tests/unit/metrics/test_compute.py`, `tests/unit/metrics/test_edge_cases.py`, `.know/env-loader.md`). No sprint-introduced pollution.

### Unit-test regression state by commit

| Commit | `tests/unit/metrics/test_main.py::TestCliCompute` under no-env subshell | Under direnv-loaded shell |
|--------|-----|-----|
| baseline `e22cca21` | 5/5 pass | 5/5 pass |
| through `6fa1afc4` (CFG-003) | 5/5 pass | 5/5 pass |
| **`f5fe16b4` (CFG-006) onward** | **0/5 pass** | 5/5 pass |
| HEAD `97aed1bf` | 0/5 pass | 5/5 pass |

Regression introduced by `f5fe16b4`; carried forward unchanged in all subsequent commits (Sprint-C commits do not touch this test file). The regression is **latent in CI-equivalent environments** and hidden in developer shells.

## 4. Empirical Evidence Blocks

### §4-A — ADR-0002 existence

```
$ ls -la .ledge/decisions/ADR-bucket-naming.md
.rw-r--r--@ 21k tomtenuta 20 Apr 18:24 .ledge/decisions/ADR-bucket-naming.md
```

### §4-B — `calc_mrr.py` deletion

```
$ test ! -f scripts/calc_mrr.py && echo DELETED || echo STILL-EXISTS
DELETED
```

### §4-C — Zero live `calc_mrr` references

```
$ grep -rn "calc_mrr" . --include="*.py" --include="*.md" --include="*.yml" \
    --include="*.yaml" --include="*.toml" --include="*.sh" 2>/dev/null \
    | grep -v "^\./\.git" | grep -v "^\./\.ledge" | grep -v "^\./\.sos"
(no output)
```

Zero hits in live code / config / docs. `.ledge/` and `.sos/` historical audit references are preserved as immutable evidence per convention.

### §4-D — Three-file test subset (janitor's 109/109 scope)

```
$ uv run pytest tests/unit/metrics/test_adversarial.py \
      tests/unit/metrics/test_compute.py \
      tests/unit/metrics/test_edge_cases.py -q --tb=line
........................................................................ [ 66%]
.....................................                                    [100%]
109 passed in 8.76s
```

### §4-E — Typo fix

```
$ grep -n "contact\|contract" secretspec.toml
18:#                         absence is a contract violation, not a graceful
19:#                         degradation. Validates the contract defined in
23:# Only vars whose contract differs from the default are redeclared under [profiles.cli].
166:# CLI/offline profile — strict S3 cache contract
173:ASANA_CACHE_S3_BUCKET = { description = "...absence is a contract violation...", required = true }
```

Zero `contact` hits; five `contract` hits. Sprint-B advisory #2 closed.

### §4-F — Regression reproduction (BLOCKING evidence)

**At baseline `e22cca21`** (Sprint-C's __main__.py replaced with pre-sprint file):

```
$ git checkout e22cca21 -- src/autom8_asana/metrics/__main__.py
$ uv run pytest tests/unit/metrics/test_main.py::TestCliCompute -q --tb=line
.....                                                                    [100%]
5 passed in 0.33s
```

**At HEAD `97aed1bf`** (no env):

```
$ uv run pytest tests/unit/metrics/ -q --tb=no
FAILED tests/unit/metrics/test_main.py::TestCliCompute::test_compute_with_mocked_loader
FAILED tests/unit/metrics/test_main.py::TestCliCompute::test_compute_ad_spend
FAILED tests/unit/metrics/test_main.py::TestCliCompute::test_loader_error_exits
FAILED tests/unit/metrics/test_main.py::TestCliCompute::test_count_metric_formats_as_integer
FAILED tests/unit/metrics/test_main.py::TestCliCompute::test_mean_metric_empty_dataframe_shows_no_data
5 failed, 184 passed in 9.05s
```

**At HEAD `97aed1bf`** (env set, simulating direnv-loaded shell):

```
$ ASANA_CACHE_S3_BUCKET=autom8-s3 ASANA_CACHE_S3_REGION=us-east-1 \
    uv run pytest tests/unit/metrics/ -q --tb=no
189 passed in 8.86s
```

**CI environment audit** (`.github/workflows/test.yml:58`):

```
test_env: 'ASANA_WORKSPACE_GID=${{ vars.ASANA_WORKSPACE_GID }}'
```

CI injects `ASANA_WORKSPACE_GID` only. Neither `ASANA_CACHE_S3_BUCKET` nor
`ASANA_CACHE_S3_REGION` are set. CI will reproduce the 5-failure mode on
first push. The affected tests carry no `@pytest.mark.integration` /
`@pytest.mark.slow` / `@pytest.mark.fuzz` markers and so are NOT excluded
by `test_markers_exclude` at L56.

## 5. End-to-End Verification — 6-Step Chain

Run from a subshell where `.env/defaults` was sourced manually
(`set -a && . .env/defaults && set +a`), simulating the direnv happy
path for a fresh-cloned repo.

### Step 1: env check

```
$ env | grep ASANA_CACHE_S3
ASANA_CACHE_S3_BUCKET=autom8-s3
ASANA_CACHE_S3_REGION=us-east-1
```

PASS.

### Step 2: `--list` (exit 0, metric list)

```
$ uv run python -m autom8_asana.metrics --list
Available metrics:
  active_ad_spend           Total weekly ad spend for ACTIVE offers, deduped ...
  active_mrr                Total MRR for ACTIVE offers, deduped by phone+vertical...
  onboarding_to_implementation_conversion ...
  outreach_to_sales_conversion ...
  sales_to_onboarding_conversion ...
  stage_duration_median     Median days spent in a stage (configurable via filter)
  stage_duration_p95        95th percentile days spent in a stage
  stalled_entities          Count of entities stuck in current stage beyond 30-day threshold
  weekly_transitions        Count of stage transitions (total pipeline throughput)

exit=0
```

PASS.

### Step 3: `active_mrr`

```
$ uv run python -m autom8_asana.metrics active_mrr
WARNING: secretspec binary not found; using inline preflight check.
Loaded 3856 rows from project 1143843662099250
Unique (office_phone, vertical) combos: 71

  active_mrr: $94,076.00

exit=0
```

PASS. Matches Sprint-B audit baseline and CFG-007 parity commit body.

### Step 4: `active_ad_spend`

```
$ uv run python -m autom8_asana.metrics active_ad_spend
WARNING: secretspec binary not found; using inline preflight check.
Loaded 3856 rows from project 1143843662099250
Unique (office_phone, vertical) combos: 72

  active_ad_spend: $29,990.00

exit=0
```

PASS. Matches prior recorded value.

### Step 5: Missing bucket with metric invocation (expect exit 2 + actionable error)

```
$ (unset ASANA_CACHE_S3_BUCKET; unset ASANA_CACHE_S3_REGION;
    uv run python -m autom8_asana.metrics active_mrr; echo "INNER_EXIT=$?")
WARNING: secretspec binary not found; using inline preflight check.
ERROR: CLI preflight failed — [profiles.cli] contract in secretspec.toml requires the following env var(s) but they are unset or empty:
  - ASANA_CACHE_S3_BUCKET
  - ASANA_CACHE_S3_REGION

This CLI entrypoint (python -m autom8_asana.metrics) runs under the 'cli' profile of secretspec.toml,
which is strict about S3 cache configuration. See:

  1. .env/defaults                (committed, Layer 3) — set committed project defaults here
     path: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.env/defaults
  2. .env/local.example → .env/local  (example committed; .env/local is gitignored, Layer 5)
     path: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.env/local.example
     copy: cp .env/local.example .env/local   # then edit .env/local with real values
  3. secretspec.toml              (the contract itself — declares which vars are required under --profile cli)
     path: /Users/tomtenuta/Code/a8/repos/autom8y-asana/secretspec.toml
     validate: secretspec check --config secretspec.toml --provider env --profile cli

Typical fix: ensure .env/defaults contains ASANA_CACHE_S3_BUCKET and ASANA_CACHE_S3_REGION,
then re-run 'direnv allow' (or source the env manually) and retry.
INNER_EXIT=2
```

PASS. Exit code 2 confirmed; error cites all three config sources with
absolute paths; old generic message `No S3 bucket configured.` is NOT
present on the CLI path.

### Step 6: Missing bucket with `--list` (expect exit 0, bypass)

```
$ (unset ASANA_CACHE_S3_BUCKET; unset ASANA_CACHE_S3_REGION;
    uv run python -m autom8_asana.metrics --list; echo "INNER_EXIT=$?")
Available metrics:
  active_ad_spend           ...
  [9 metrics listed]
  weekly_transitions        ...
INNER_EXIT=0
```

PASS. `--list` structurally bypasses preflight; preflight cost is zero
on discovery path. Identical behavior to Sprint-B Scenario D.

### Summary

| Step | Expected | Observed | Verdict |
|------|----------|----------|---------|
| 1 | Env vars loaded | `BUCKET=autom8-s3 REGION=us-east-1` | PASS |
| 2 | `--list` exit 0 | exit 0, 9 metrics listed | PASS |
| 3 | `active_mrr = $94,076.00` | `$94,076.00`, 71 combos | PASS |
| 4 | `active_ad_spend = $29,990.00` | `$29,990.00`, 72 combos | PASS |
| 5 | exit 2 + actionable error w/ 3 sources | exit 2, all three sources cited | PASS |
| 6 | exit 0 on `--list` with env unset | exit 0, 9 metrics listed | PASS |

All 6 E2E steps pass. The sprint's core product-behavior goals are met.

## 6. Regression Assessment — Behavior Preservation

### Lib-mode surfaces — UNAFFECTED (confirmed)

```
$ grep -rn "secretspec\|_preflight\|_CLI_REQUIRED" \
    src/autom8_asana/ --include="*.py" \
    | grep -v "metrics/__main__.py"
(no output)
```

Zero non-CLI imports or references. Lib-mode consumers
(`lambda_handlers/*`, `cache/backends/s3.py`, `cache/dataframe/factory.py`,
`dataframes/offline.py`, `query/offline_provider.py`,
`config.py`, `settings.py`) only READ the `ASANA_CACHE_S3_BUCKET` env
var; none invokes `secretspec` or the preflight. Sprint-B's explicit
"no lib-mode change" claim (AUDIT-B §6) is upheld at Sprint-C HEAD.

| Surface | Affected at Sprint-C HEAD? | Rationale |
|---------|----|-----------|
| FastAPI server (`app/`) | NO | No preflight import; reads var via `CacheSettings(required=False)` aligned with `[profiles.default]` |
| Lambda handlers (`lambda_handlers/*.py`) | NO | Library path; no CLI dependency |
| Embedded SDK consumers | NO | Library path exclusively |
| `python -m autom8_asana.metrics <metric>` | CHANGED-BY-DESIGN (Sprint-B) | Preflight at `__main__.py:186` before S3 load — intended contract |
| `python -m autom8_asana.metrics --list` | UNCHANGED | Structurally bypasses preflight (Step 6 exit 0) |
| `scripts/calc_mrr.py` | DELETED (Sprint-C) | Subsumed — parity verified |
| **`tests/unit/metrics/test_main.py::TestCliCompute`** | **BROKEN (5 tests) in no-env CI** | Tests mock loader but not preflight; no env in CI |
| `tests/unit/metrics/test_{adversarial,compute,edge_cases}.py` | UNAFFECTED | 109/109 pass in both env modes |
| `tests/unit/metrics/` aggregate | 184/189 no-env; 189/189 env-set | Reflects the 5-test regression |

### Branch linearity

```
$ git status --short
(clean)
$ git log --oneline e22cca21..HEAD | wc -l
7
```

Branch is linearly mergeable onto main. Working tree has no residuals
from this sprint. Harness-level unstaged files reported at sprint start
(`.claude/*`, `.gemini/*`, `.knossos/*`, `.know/aegis/baselines.json`,
etc.) reset cleanly via `git checkout HEAD -- uv.lock` after `uv sync`.
No sprint commit carries harness drift.

## 7. Hygiene-11-Check Rubric Application

Minimum set (§3) for a mixed PATCH+MODULE sprint: Lenses 1, 3, 5, 9, 11.
Also applying 2, 4, 6, 7, 8 because the sprint spans multiple deletions,
new `.know/` files, and touches cross-cutting test references.

| # | Lens | Verdict | Note |
|---|------|---------|------|
| 1 | Boy Scout | CLEANER — typo fix (Sprint-B advisory #2 closed), new `.know/` knowledge, deletion of 196 dead lines (`calc_mrr.py`), ADR-0002 authored. One tracked advisory: `.env/defaults:17` semantic staleness re CFG-004 (see §8 A-1). | Count: +4 improvements, 0 regressions at the doc/config layer |
| 2 | Atomic-Commit Discipline | ATOMIC-CLEAN across all 7 commits (§3 table). CFG-007's deletion + 3 test-comment touch is tightly coupled (same commit subject reference). | — |
| 3 | Scope Creep | SCOPE-DISCIPLINED — every commit maps to a CFG-id or declared Boy-Scout advisory close. No deltas outside the handoff list. | CFG-004 closed via cross-artifact (ADR + .know/ + header) — in-scope |
| 4 | Zombie Config | NO-ZOMBIES on `calc_mrr` (§4-C: zero live hits); `.ledge/`/`.sos/` hits are preserved audit trail, not zombies. | — |
| 5 | Self-Conformance | SELF-CONFORMANT — audit-lead standard met (verbatim evidence, bounded verdict, explicit remediation). | Ironic corollary: the audit-lead's "evidence over trust" principle is what surfaced the regression; Sprint-B's "pytest not run" declaration was the gap |
| 6 | CC-ism Discipline | CONCUR — no CC-ism additions; the typo fix reduces one. | — |
| 7 | HAP-N Fidelity | n/a — this sprint does not operate in the HAP-N space | — |
| 8 | Path C Migration Completeness | PASS — `scripts/calc_mrr.py` deletion is complete (zero live refs); three touchpoints (test comments) migrated | — |
| 9 | Architectural Implication | STRUCTURAL-CHANGE-DOCUMENTED — ADR-0002 for bucket naming, `.know/env-loader.md` for loader contract. ADR-0001 tie-in consistent. | — |
| 10 | Preload Chain Impact | n/a — no agent preload contracts modified | — |
| 11 | Non-Obvious Risks | 3 advisories (§8). None individually blocking. The test regression is escalated above advisory to **BLOCKING** because it is a reproducible CI failure mode, not a latent operational hazard. | — |

### Aggregation

- No BLOCKING-tier lens verdict fires from the rubric directly.
- One **out-of-band BLOCKING finding**: test regression at §6 / §4-F.
- Flag-tier: 3 advisories.

**CRITIC VERDICT**: BLOCKING (external finding, outside standard lens taxonomy but materially CI-breaking).

## 8. Advisories (Non-Blocking)

### A-1. `.env/defaults` header semantic staleness

File: `.env/defaults:17-18`. Text: "CFG-004 in the sprint ADR trail
records the canonical decision; until that decision is recorded,
`autom8-s3` is the authoritative dev value ...". ADR-0002 exists and was
authored 2026-04-20 18:24 — same day as the header write. The phrase
"until that decision is recorded" is now literally false. Mechanical
fix: replace with "ADR-0002 (`.ledge/decisions/ADR-bucket-naming.md`)
records the canonical decision: `autom8-s3` is the authoritative dev
value ...".

Severity: editorial. Not a runtime concern. Suggest including in the
bounded revision pass alongside the test fix (same commit, or a trailing
style-scoped commit).

### A-2. Inline-fallback parity test still absent (Sprint-B advisory #3 carried forward)

`src/autom8_asana/metrics/__main__.py:27` still promises "A companion
test asserts parity" between `_CLI_REQUIRED` and `[profiles.cli]`
`required = true` entries. Sprint-B audit §8 advisory #3 flagged this
and it remains unaddressed. Low operational risk (mitigated by fallback
tuple); surfaces only if `secretspec.toml` `[profiles.cli]` acquires a
new `required = true` entry in the future. Carry to next hygiene sprint.

### A-3. Companion `secretspec` binary integration test (Sprint-B advisory #1 carried forward)

When `secretspec` binary becomes available (devbox/nix pin), stderr
parity between subprocess path and inline fallback should be asserted
in a targeted integration test. Degradation-to-inline is already a
working fallback. Not blocking.

## 9. Sprint Closure Decision

**Sprint closure is BLOCKED pending Janitor revision.**

### Required before sprint closure (re-audit scope)

One commit, one concern, one file (or two files if closing A-1 in the
same commit):

1. **MUST**: Fix the 5-test regression in `tests/unit/metrics/test_main.py::TestCliCompute`.
   Recommended approach (Fix A, §1): add an autouse fixture to
   `TestCliCompute` that monkeypatches the two env vars for the duration
   of the class. Zero production code change.

2. **SHOULD** (same commit, optional): Fix A-1 editorial staleness in
   `.env/defaults:17-18`.

3. **MUST**: Re-run `uv run pytest tests/unit/metrics/ -q` in a shell
   where `ASANA_CACHE_S3_BUCKET` and `ASANA_CACHE_S3_REGION` are UNSET
   (CI parity check). Expected result: `189 passed`. Include the
   verbatim output in the commit body.

### Not required before closure

- CFG-005 fleet fanout — correctly deferred; awaits next cross-rite handoff.
- Advisories A-2, A-3 — carry forward to next hygiene sprint.
- Any change to production `__main__.py` preflight behavior — not the fix site.

### Re-audit scope

Delta audit of the fix commit only. Verify:
- Bounded scope (only the 1-2 files identified).
- 189/189 passing under no-env subshell.
- 189/189 passing under env-loaded subshell.
- E2E 6-step chain still passes at post-fix HEAD.

Upon delta-audit PASS, the sprint becomes closure-eligible and
HANDOFF-RESPONSE-hygiene-to-eunomia-2026-04-20 can be emitted with a
green-light body. The response artifact is **authored in advance of the
fix** under this audit's schedule so that when the Janitor completes
the bounded fix, the only remaining step is a re-audit + response
submission.

### Route

**Janitor**. Bounded test-fix commit. No architect-enforcer revision; no
plan flaw. This is a test-suite integration oversight from Sprint-B
that was undetectable at Sprint-B audit time because pytest was not run.

## 10. Evidence Ceiling

Self-referential evidence grade rule (`self-ref-evidence-grade-rule`
legomena) caps this audit's self-asserted grades at **MODERATE**. The
regression finding (§4-F) is at **STRONG** grade because it is
externally reproducible — any observer running the same commands in the
same subshell will reproduce the 5-failure output. All other findings
are at MODERATE per the ceiling rule.
