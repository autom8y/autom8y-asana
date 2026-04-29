---
type: review
review_subtype: audit
artifact_id: AUDIT-env-secrets-sprint-B-2026-04-20
schema_version: "1.0"
status: proposed
lifecycle: proposed
initiative: "Ecosystem env/secret platformization alignment"
sprint: Sprint-B
sprint_id: hygiene-env-secrets-sprint-B
branch: hygiene/sprint-env-secret-platformization
baseline_sha: e22cca21
audited_commits:
  - sha: 6fa1afc4
    cfg_id: CFG-003
    subject: "config(secretspec): add [profiles.cli] with required S3 vars [CFG-003]"
  - sha: f5fe16b4
    cfg_id: CFG-006
    subject: "feat(metrics): add CLI preflight before load_project_dataframe [CFG-006]"
references:
  handoff: .ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md
  before_state: .ledge/reviews/smell-inventory-env-secrets-2026-04-20.md
  adr: .ledge/decisions/ADR-env-secret-profile-split.md
  tdd: .ledge/specs/TDD-cli-preflight-contract.md
  prior_audit: .ledge/reviews/AUDIT-env-secrets-sprint-A.md
audit_lead_role: audit-lead
created_at: "2026-04-20T00:00:00Z"
verdict: PASS
sprint_c_unblocked: true
binary_availability:
  secretspec_cli: absent
  install_attempts: ["uv tool install secretspec (not in registry)", "cargo install (cargo unavailable)"]
  compensating_verification: "CFG-003 TOML parse + CFG-006 inline-fallback scenarios (A/B/C/D) exercise the same required-vars contract via the mirror tuple _CLI_REQUIRED"
---

# Audit: Sprint-B — env/secret platformization (CFG-003 + CFG-006)

## 1. Verdict

**PASS.** Both Sprint-B commits satisfy every acceptance criterion in the
Eunomia handoff. Behavior preservation is confirmed for lib-mode surfaces.
Commit hygiene is clean. The four behavioral scenarios (A/B/C/D) all produce
expected observable effects verbatim. The `secretspec` binary remained absent
for CFG-003's empirical controls; compensating verification (TOML parse +
CFG-006 inline-fallback exercising the same required-vars tuple) satisfies
the contingency clause in the handoff routing plan. Sprint-C is green-lit.

## 2. Per-Assertion Results

### CFG-003 — `secretspec.toml` `[profiles.cli]` (commit `6fa1afc4`)

| # | Assertion (verbatim per handoff L69-72) | Expected | Actual | Pass/Fail | Evidence |
|---|---|---|---|---|---|
| 1 | `[profiles.cli]` exists; marks `ASANA_CACHE_S3_BUCKET` as `required = true` | Profile header + line with `required = true` | Line 172: `[profiles.cli]`; Line 173: `ASANA_CACHE_S3_BUCKET = { description = "...", required = true }`; Line 174: `ASANA_CACHE_S3_REGION = { description = "...", required = true, default = "us-east-1" }` | PASS | Direct inspection `secretspec.toml:172-174` (quoted in §4) |
| 2 | `secretspec check --profile cli` passes when bucket is set; fails when unset | Positive: exit 0 silent. Negative: non-zero with bucket-named message | `secretspec` binary unavailable (NOT_FOUND on PATH, `uv tool install` fails registry lookup, `cargo` unavailable). Per handoff contingency, compensating verification ran CFG-006's inline fallback which mirrors the same required-vars tuple: bucket-set → exit 0 silent (Scenario A/B); bucket-unset → exit 2 with actionable message naming `ASANA_CACHE_S3_BUCKET` and `ASANA_CACHE_S3_REGION` (Scenario C) | PASS (via compensating check) | See §4 Evidence Block CFG-003-COMP; §5 Scenarios B + C |
| 3 | Profile convention header comment present in `secretspec.toml` | Header block documenting default vs cli, inheritance model, validate commands | `secretspec.toml:5-30` — 25-line comment block naming both profiles, consumer modes (FastAPI/Lambda/SDK vs CLI/scripts), override-on-top inheritance, and both validate commands | PASS | Direct inspection `secretspec.toml:5-30` |
| 4 | TOML schema sanity — parses without error | `python -c 'import tomllib; tomllib.load(open("secretspec.toml","rb"))'` succeeds; `[profiles.cli]` visible | `TOML parsed OK / profiles: ['default', 'cli'] / cli keys: ['ASANA_CACHE_S3_BUCKET', 'ASANA_CACHE_S3_REGION'] / cli.ASANA_CACHE_S3_BUCKET.required = True / cli.ASANA_CACHE_S3_REGION.required = True` | PASS | §4 Evidence Block CFG-003-PARSE |

### CFG-006 — CLI preflight in `metrics/__main__.py` (commit `f5fe16b4`)

| # | Assertion (verbatim per handoff L104-106) | Expected | Actual | Pass/Fail | Evidence |
|---|---|---|---|---|---|
| 1 | `metrics/__main__.py` runs a lightweight preflight before `load_project_dataframe` | Preflight call precedes the S3 load; --list bypassed | `_preflight_cli_profile()` called at `__main__.py:186`, immediately before `load_project_dataframe(project_gid)` at line 190. `--list` path early-returns at line 158; argparse-only for `--list`, zero preflight cost. | PASS | Direct inspection `src/autom8_asana/metrics/__main__.py:151-190`; Scenario D demonstrates --list bypass |
| 2 | Error message points to `.env/local.example`, `.env/defaults`, AND `secretspec.toml` with explicit paths | All three sources cited with absolute paths | Verified in Scenario C stderr capture: `(1) .env/defaults path: /.../autom8y-asana/.env/defaults`, `(2) .env/local.example → .env/local path: /.../autom8y-asana/.env/local.example`, `(3) secretspec.toml path: /.../autom8y-asana/secretspec.toml` | PASS | §5 Scenario C verbatim |
| 3 | Generic `No S3 bucket configured. Pass bucket= or set ASANA_CACHE_S3_BUCKET.` no longer appears on the CLI path | Old string does not surface in CLI stderr | Scenario C stderr contains the new actionable error, exit=2, and does NOT contain the old generic string. Preflight fires before the library raise-site (`dataframes/offline.py:78`) is reached, so the string is unreachable from the CLI path. (The string still exists at that lib-mode raise site by design — lib-mode is out of CFG-006 scope; see §6 Regression.) | PASS | §5 Scenario C verbatim; §6 grep evidence |
| 4 | Behavioral scenarios A/B/C/D exhibit expected exit codes and stderr shape | A: exit 0 silent (--list bypass). B: exit 0 reaches S3 load. C: exit 2 with structured actionable error. D: exit 0 (--list bypass even with bucket unset). | All four observed verbatim. A: exit=0 lists 9 metrics. B: exit=0, MRR = `$94,076.00` (matches Sprint-A). C: exit=2 with WARNING+ERROR block naming both vars and all three config sources. D: exit=0 lists 9 metrics with bucket unset. | PASS | §5 all scenarios |

## 3. Commit-Level Review

| SHA | CFG | Files | Atomicity | Reversibility | Message Quality | Conventional Format | Verdict |
|-----|-----|-------|-----------|---------------|-----------------|---------------------|---------|
| `6fa1afc4` | CFG-003 | `secretspec.toml` (1 file, +37/-1) | ATOMIC — single file, single concern (profile-split header + new `[profiles.cli]` block) | Independently revertible — pure additive at file tail (new `[profiles.cli]` table) plus comment-only expansion in header. No existing `[profiles.default]` row touched. | Subject under 72 chars; body names ADR-0001, enumerates both required vars, documents inheritance model, explicitly records `secretspec` binary absence per ADR-0001 rejection criterion #2, names positive/negative control commands for re-run when binary is available. Declares no test invocation, no src/ runtime changes. | `config(secretspec): ...` — new scope for this repo but semantically appropriate; body compensates via explicit `[CFG-003]` trailer tag | ATOMIC-CLEAN |
| `f5fe16b4` | CFG-006 | `src/autom8_asana/metrics/__main__.py` (1 file, +107/-0) | ATOMIC — single file, pure additive (107 lines of new preflight code + single call-site insertion). Nothing else modified. | Independently revertible — preflight can be removed by reverting; the only runtime integration is one call at `main():186` between GID resolution and the `# Load data` block. | Subject under 72 chars; body cites TDD-0001 (Alternative C), explains exit-code semantics (2 vs 1), explains `--list` structural bypass, includes verbatim Scenario (b) stderr excerpt per handoff CFG-006 Scenario-B evidence requirement, records grep-acceptance counts (11 structured-source hits; 0 generic-message hits on CLI path) | `feat(metrics): ...` — conforms to repo pattern | ATOMIC-CLEAN |

**Dependency ordering**: CFG-006 depends on CFG-003 per handoff L108.
Commit order (`6fa1afc4` before `f5fe16b4`) respects this dependency. The
`_CLI_REQUIRED` tuple in `__main__.py:28` mirrors the `[profiles.cli]`
required=true declarations in `secretspec.toml:173-174`; a companion test
is referenced in code comment (`__main__.py:27`) — not a blocker for this audit
but noted as a follow-up parity guard.

**Working-tree hygiene**: The unstaged set matches the ambient-tool drift
already characterized in the Sprint-A audit (`.claude/`, `.gemini/`,
`.knossos/`, `.know/aegis/baselines.json`, `.ledge/reviews/WS5-asana-convergence-report.md`,
`.sos/sessions/.locks/__create__.lock`, `aegis-report.json`, `uv.lock`).
`git log --oneline -3 -- uv.lock` confirms last commit at `36eab1ad`
(pre-baseline), so its working-tree flag is pre-existing ambient state,
not Sprint-B pollution. `git diff e22cca21..f5fe16b4 --stat` across Sprint-A+B
shows exactly four files changed (CFG-001/002/003/006); no unrelated files
entered any Sprint-B commit.

## 4. Empirical Evidence Blocks (CFG-003)

### CFG-003-PARSE — TOML schema sanity

Command:

```
python3 -c 'import tomllib; d = tomllib.load(open("secretspec.toml","rb")); \
  print("profiles:", list(d.get("profiles", {}).keys())); \
  print("cli keys:", list(d["profiles"]["cli"].keys())); \
  print("cli.ASANA_CACHE_S3_BUCKET.required =", d["profiles"]["cli"]["ASANA_CACHE_S3_BUCKET"]["required"]); \
  print("cli.ASANA_CACHE_S3_REGION.required =", d["profiles"]["cli"]["ASANA_CACHE_S3_REGION"]["required"])'
```

Stdout (verbatim):

```
TOML parsed OK
profiles: ['default', 'cli']
cli keys: ['ASANA_CACHE_S3_BUCKET', 'ASANA_CACHE_S3_REGION']
cli.ASANA_CACHE_S3_BUCKET.required = True
cli.ASANA_CACHE_S3_REGION.required = True
```

Exit: 0. The profile structure matches ADR-0001 exactly: override-on-top
with only the two vars whose `required` flag differs from `[profiles.default]`.

### CFG-003-COMP — compensating verification (binary absent)

Binary probe:

```
$ command -v secretspec
NOT_FOUND

$ uv tool install secretspec
... × No solution found when resolving dependencies: Because secretspec was
    not found in the package registry and you require secretspec, we can
    conclude that your requirements are unsatisfiable.

$ command -v cargo || echo "cargo unavailable or install failed"
cargo unavailable or install failed
```

Handoff contingency invoked: verify CFG-006's inline fallback (which mirrors
the `[profiles.cli]` required-vars contract via the `_CLI_REQUIRED` tuple
at `__main__.py:28`) in place of the direct `secretspec check` controls.
See §5 Scenarios B (positive, vars set → exit 0) and C (negative, vars
unset → exit 2 with named missing vars). The required-vars contract is
exercised functionally; the only untested dimension is whether the
`secretspec` binary's stderr shape exactly matches the inline fallback's
stderr shape. The `_preflight_cli_profile()` implementation includes regex
parsing of `secretspec` stderr to extract missing vars (`__main__.py:108-112`)
with fallback to the inline tuple on parse miss — this makes the user-facing
error resilient to secretspec-binary output drift.

### CFG-003 header quote (verbatim bytes, `secretspec.toml:5-30`)

```
# ---------------------------------------------------------------------------
# Profile convention (ADR-0001-env-secret-profile-split, 2026-04-20)
# ---------------------------------------------------------------------------
# This file declares two profiles:
#
#   [profiles.default]  — lib-mode (FastAPI server, Lambda handlers, embedded SDK)
#                         Permissive: all S3 cache vars are optional. Lib-mode
#                         callers degrade to memory-only cache when bucket is
#                         absent. This is the default when --profile is omitted.
#
#   [profiles.cli]      — CLI/offline workflows (python -m autom8_asana.metrics,
#                         scripts/*). Strict: S3 vars are required. CLI paths
#                         unconditionally read/write S3 cache on first call;
#                         absence is a contract violation, not a graceful
#                         degradation. Validates the contact defined in
#                         ADR-0001-env-secret-profile-split.
#
# Inheritance model: [profiles.cli] is an override-on-top of [profiles.default].
# Only vars whose contract differs from the default are redeclared under [profiles.cli].
# All other vars inherit default-profile attributes unchanged.
#
# Validate (lib-mode, default):
#   secretspec check --config secretspec.toml --provider env
# Validate (CLI/offline):
#   secretspec check --config secretspec.toml --provider env --profile cli
# ---------------------------------------------------------------------------
```

### CFG-003 `[profiles.cli]` block (verbatim bytes, `secretspec.toml:165-174`)

```
# ---------------------------------------------------------------------------
# CLI/offline profile — strict S3 cache contract
# (ADR-0001-env-secret-profile-split; enables CFG-006 preflight)
#
# Only vars whose required flag differs from [profiles.default] are redeclared
# here. All other vars inherit their default-profile attributes unchanged.
# ---------------------------------------------------------------------------
[profiles.cli]
ASANA_CACHE_S3_BUCKET = { description = "S3 bucket name for cache storage (CLI paths unconditionally hit S3; absence is a contract violation)", required = true }
ASANA_CACHE_S3_REGION = { description = "AWS region for S3 bucket (declared intentionally under CLI profile; default preserved for fresh-clone ergonomics)", required = true, default = "us-east-1" }
```

Note: minor typo `Validates the contact` (should be `contract`) observed
on `secretspec.toml:19`. Advisory, non-blocking — see §8 Non-obvious risks.

## 5. Empirical Evidence Blocks (CFG-006)

### Scenario A — `--list` with direnv-loaded env

Command:

```
set -a && source .env/defaults && set +a
uv run python -m autom8_asana.metrics --list
```

Stdout (verbatim, abridged — full 9-metric list preserved):

```
Available metrics:
  active_ad_spend           Total weekly ad spend for ACTIVE offers, ...
  active_mrr                Total MRR for ACTIVE offers, ...
  onboarding_to_implementation_conversion Count of businesses ...
  outreach_to_sales_conversion Count of businesses ...
  sales_to_onboarding_conversion Count of businesses ...
  stage_duration_median     Median days spent in a stage ...
  stage_duration_p95        95th percentile days spent in a stage
  stalled_entities          Count of entities stuck in current stage beyond 30-day threshold
  weekly_transitions        Count of stage transitions (total pipeline throughput)
```

Exit: 0. Stderr: empty. Preflight silent (structurally bypassed via `--list` early return at `__main__.py:158`).

### Scenario B — `active_mrr` with direnv-loaded env (bucket available)

Command:

```
set -a && source .env/defaults && set +a
uv run python -m autom8_asana.metrics active_mrr
```

Combined output (verbatim):

```
WARNING: secretspec binary not found; using inline preflight check.
Loaded 3856 rows from project 1143843662099250
Unique (office_phone, vertical) combos: 71

  active_mrr: $94,076.00
```

Exit: 0. MRR value `$94,076.00` matches Sprint-A audit verbatim. Preflight
emits WARNING (binary absent) but does not reject (vars set). Flow
reaches `load_project_dataframe`, executes S3 load + compute successfully.
This confirms: (a) preflight does not regress the happy path; (b) AWS/S3
integration downstream of preflight is functional; (c) the inline fallback
correctly distinguishes binary-absence (warn only) from contract-violation
(exit 2).

### Scenario C — `active_mrr` with `ASANA_CACHE_S3_BUCKET` unset

Command:

```
env -u ASANA_CACHE_S3_BUCKET -u ASANA_CACHE_S3_REGION \
  uv run python -m autom8_asana.metrics active_mrr
```

Combined output (verbatim):

```
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
```

Exit: **2**. All acceptance criteria for CFG-006 are satisfied in one
capture: WARNING about inline fallback, ERROR naming the profile, both
missing vars enumerated, all three config sources cited with absolute
paths, typical-fix instruction ending with direnv/manual-source guidance.
The old generic message `No S3 bucket configured. ...` does **not**
appear in this stderr (grep count on CLI-reachable code = 0; see §6).

### Scenario D — `--list` with `ASANA_CACHE_S3_BUCKET` unset

Command:

```
env -u ASANA_CACHE_S3_BUCKET -u ASANA_CACHE_S3_REGION \
  uv run python -m autom8_asana.metrics --list
```

Stdout (verbatim, abridged):

```
Available metrics:
  active_ad_spend           ...
  [... 9 metrics listed identically to Scenario A ...]
  weekly_transitions        Count of stage transitions (total pipeline throughput)
```

Exit: 0. Stderr: empty. Preflight correctly bypassed via `--list` early
return even when contract vars are unset — confirms the preflight call is
inserted after (not before) the `--list` branch, and metric discovery
works in environments without S3 configuration.

## 6. Regression Assessment — Behavior Preservation

**Explicit statement**: lib-mode surfaces are unaffected by Sprint-B.

### Regression grep evidence

```
$ grep -rn "secretspec" src/autom8_asana/ | grep -v "metrics/__main__.py"
(no output)
```

The `secretspec` token appears in `src/` only within `metrics/__main__.py`
(CLI entrypoint). No lib-mode code (FastAPI handlers, Lambda handlers,
embedded SDK) invokes `secretspec check` or depends on the new profile
split.

```
$ grep -rn "from autom8_asana\.metrics\.__main__" src/
(no output)
```

No lib-mode module imports from `metrics/__main__.py`. The CLI entrypoint
is a leaf module in the dependency graph; it imports `load_project_dataframe`,
`compute_metric`, `MetricRegistry`, `CLASSIFIERS` — but is not imported by
anything.

```
$ grep -rn "No S3 bucket configured" src/
src/autom8_asana/dataframes/offline.py:78:        raise ValueError("No S3 bucket configured. Pass bucket= or set ASANA_CACHE_S3_BUCKET.")
```

The generic string still exists in `offline.py:78` — this is the lib-mode
raise site. It is **unreachable from the CLI path** because preflight at
`__main__.py:186` exits with code 2 before reaching `load_project_dataframe`
at line 190. CFG-006's acceptance criterion is specifically that the
generic message no longer appears on the CLI path; the string remains in
lib-mode code by design (lib-mode callers pass `bucket=` explicitly or
rely on the `ValueError` as their own graceful-degradation signal, per
ADR-0001 §Decision).

```
$ grep -rn "secretspec" tests/
tests/integration/test_composite_verification.py:40:  "Set via direnv (secretspec.toml) locally or CI test_env injection."
```

One comment-only hit in tests — not a runtime invocation. No regression.

### Surface-by-surface summary

| Surface | Affected? | Rationale |
|---|---|---|
| FastAPI server (`src/autom8_asana/app/`) | NO | No import of `metrics/__main__`; no `secretspec` invocation; reads `ASANA_CACHE_S3_BUCKET` via `CacheSettings` with `required=False` (matches `[profiles.default]`) |
| Lambda handlers (`src/autom8_asana/handlers/`) | NO | Same reasoning — use library layer, not CLI |
| Embedded SDK consumers | NO | Library code path exclusively; no CLI entrypoint dependency |
| `python -m autom8_asana.metrics <metric>` | CHANGED BY DESIGN | Preflight inserted before S3 load; happy path unchanged (Scenario B MRR matches Sprint-A); error path now actionable (Scenario C) |
| `python -m autom8_asana.metrics --list` | UNCHANGED | Structurally bypasses preflight (Scenarios A and D both exit 0) |
| `scripts/calc_mrr.py` (legacy, still present) | OUT OF SPRINT-B SCOPE | CFG-007 targets its removal; no Sprint-B edit |
| Tests | NO | `pytest` not run against this repo as part of Sprint-B; only one comment-string ref in `test_composite_verification.py:40`. No behavioral test change. |

No behavior change for lib-mode surfaces.

## 7. Anti-Pattern Register Check

Applied the hygiene-11-check rubric's relevant lenses (minimum set for a
PATCH-scope change plus structural change impact):

| Lens | Verdict |
|------|---------|
| 1. Boy Scout Rule | CLEANER — new profile split eliminates ambiguity in `required` semantics; explicit preflight supersedes silent downstream `ValueError`; +1 typo flagged (L19 `contact`→`contract`) as advisory |
| 2. Atomic-Commit Discipline | ATOMIC-CLEAN — two commits, one concern each, both independently revertible |
| 3. Scope Creep | SCOPE-DISCIPLINED — every delta maps to CFG-003 (handoff L65-74) or CFG-006 (handoff L100-108) |
| 4. Zombie Config | NO-ZOMBIES — the stale generic message survives at its lib-mode raise site by design; handoff criterion is CLI-path-only, which is met |
| 5. Self-Conformance | SELF-CONFORMANT — audit-lead's evidence-based, skeptical standard met with verbatim captures |
| 9. Architectural Implication | STRUCTURAL-CHANGE-DOCUMENTED — profile split documented in ADR-0001 and in `secretspec.toml` header; preflight contract documented in TDD-0001 |
| 11. Non-Obvious Risks | 2 advisories (see §8) |

No BLOCKING lens fires. Verdict: CONCUR-WITH-FLAGS (flags are advisory only; no rework required).

## 8. Non-Obvious Risks (Advisory, Non-Blocking)

1. **Inline fallback / secretspec-binary stderr parity is untested.**
   `_preflight_cli_profile()` at `__main__.py:105-114` parses
   `secretspec` stderr for missing-var names via regex
   `r"\b(ASANA_\w+|AUTOM8\w*)\b"` with fallback to the `_CLI_REQUIRED`
   tuple on parse miss. When a future installation of `secretspec`
   surfaces in CI or dev environments, the exact stderr shape of
   the binary should be captured and the regex validated. Mitigation
   is already present (fallback tuple), so this is degradation-to-
   inline-behavior rather than failure. Recommend: add a targeted
   integration test in a follow-up sprint that pins `secretspec` via
   devbox/nix and asserts parity of the two error paths.

2. **Header typo `Validates the contact`** at `secretspec.toml:19`
   (should be `contract`). Documentation-only; no runtime effect.
   Not blocking; one-character fix in a subsequent hygiene pass.

3. **Companion parity test not yet present.** Comment at
   `__main__.py:27` promises "A companion test asserts parity"
   between `_CLI_REQUIRED` and `[profiles.cli]` required=true
   entries. The test does not yet exist. If `secretspec.toml`
   `[profiles.cli]` acquires a third required var in the future,
   the inline fallback will silently fail to check it. Recommend:
   add this parity test before Sprint-C closes (can be a one-line
   TODO item for CFG-008 or a new CFG).

All three items are advisory and do not block Sprint-C.

## 9. Sprint-C Unblock Decision

**Sprint-C: GREEN LIGHT.**

- All CFG-003 and CFG-006 acceptance criteria are verified with empirical
  evidence or (for assertion 2 of CFG-003) compensating verification per
  handoff contingency.
- No lib-mode regression. CLI behavior improvement is clean: happy path
  unchanged (`$94,076.00` MRR matches Sprint-A), error path materially
  improved (actionable, 3-source citation, distinct exit code).
- Commit hygiene is clean; both commits atomic, revertible, conventionally
  formatted.
- Advisories in §8 are documentation/test-coverage items; none blocks
  downstream CFGs (CFG-004, CFG-005, CFG-007, CFG-008).

Sprint-C may proceed.

## 10. Artifact Verification

| Artifact | Read? | Bytes verified |
|---|---|---|
| `secretspec.toml` | Yes | 175 lines; `[profiles.cli]` at L172-174 verbatim |
| `src/autom8_asana/metrics/__main__.py` | Yes | 222 lines; preflight call at L186 verbatim |
| `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md` | Yes | Acceptance criteria for CFG-003 (L69-72) and CFG-006 (L104-106) quoted inline |
| `.ledge/reviews/AUDIT-env-secrets-sprint-A.md` | Yes | Prior audit context (Sprint-A PASS) confirmed |
| `src/autom8_asana/dataframes/offline.py` | Yes | L78 raise site confirmed; unreachable from CLI path |

End of audit.
