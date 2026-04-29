---
type: spec
spec_subtype: tdd
id: TDD-0001
artifact_id: TDD-0001-cli-preflight-contract
schema_version: "1.0"
status: proposed
lifecycle_status: proposed
date: "2026-04-20"
rite: hygiene
initiative: "Ecosystem env/secret platformization alignment"
session_id: session-20260415-010441-e0231c37
author: architect-enforcer (hygiene rite, sprint-B plan phase)
consulted:
  - code-smeller (smell inventory author)
informed:
  - janitor (downstream executor of CFG-006)
  - audit-lead (downstream verifier)
source_handoff: .ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md
source_smell_inventory: .ledge/reviews/smell-inventory-env-secrets-2026-04-20.md
covers_cfg_items: [CFG-006]
depends_on_cfg_items: [CFG-001, CFG-003]
links_to:
  - ADR-0001-env-secret-profile-split
source_artifacts:
  - src/autom8_asana/metrics/__main__.py
  - secretspec.toml
  - .env/defaults
  - .env/local.example
  - scripts/a8-devenv.sh (ecosystem; read-only reference)
evidence_grade: strong
supersedes: []
superseded_by: []
---

# TDD-0001 — CLI Preflight Contract for `python -m autom8_asana.metrics`

## Status

Proposed (hygiene rite sprint-B, 2026-04-20). Consumes `ADR-0001-env-secret-profile-split` (the `[profiles.cli]` section it validates against must exist before this preflight is wired). Awaiting janitor execution under CFG-006, pending completion of CFG-001 + CFG-003.

## Scope

### In scope

This TDD specifies the CLI startup preflight for the **single entrypoint** `python -m autom8_asana.metrics` (implemented at `src/autom8_asana/metrics/__main__.py`). The preflight validates that the `[profiles.cli]` contract defined in `ADR-0001` is satisfied *before* any code path that would touch S3 or file-system cache storage runs.

### Explicitly out of scope

- **FastAPI server** (entrypoints under `src/autom8_asana/api/` or equivalents). Lib-mode; validates under `[profiles.default]` only; this TDD does not introduce preflight there.
- **Lambda handlers** (entrypoints under `src/autom8_asana/lambdas/` or equivalents). Lib-mode; same rationale.
- **Other CLI-ish scripts**. `scripts/calc_mrr.py` is scheduled for deletion under CFG-007. If additional CLI entrypoints emerge in future sprints, each gets its own TDD referencing this one as precedent; this TDD does not pre-authorize generalization.
- **Runtime cache invalidation, retry, or circuit-breaker logic.** The preflight is a one-shot boundary check, not an ongoing validator. Runtime resilience is owned by the transport layer (`src/autom8_asana/dataframes/offline.py` and its collaborators).
- **`[profiles.default]` behavior.** This TDD does not inspect, invoke, or alter default-profile validation.

## Boundary where preflight runs

### Exact location

The preflight runs inside the `main()` function of `src/autom8_asana/metrics/__main__.py`:

- **After**: `args = parser.parse_args()` (currently line 47) completes and all argparse-derived branching decisions are known.
- **Before**: `df = load_project_dataframe(project_gid)` (currently line 83) executes.
- **Call-site**: approximately line 48 onward, but the precise line is a janitor determination driven by the decision tree below.

### Decision tree — when preflight should and should not fire

```
args.list_metrics == True              → SKIP preflight (args.list touches only registry; no S3 read/write)
args.metric is None                    → SKIP preflight (parser.error will exit shortly; no need to validate env first)
args.metric is set, registry lookup fails → SKIP preflight (KeyError path exits before S3)
args.metric is set, GID resolution fails → SKIP preflight (exit before S3)
args.metric is set, GID resolves       → RUN preflight (next code path is load_project_dataframe → S3)
```

The cleanest insertion point is **immediately before the `# Load data` block** (currently line 81). At that point all cheap prerequisites have been validated and the next call unconditionally hits S3. This is also the point of highest information: `metric`, `project_gid`, and `args` are all resolved, so preflight error messages can reference the attempted invocation.

### Rationale for this placement

- **After arg parsing** because `--list` legitimately has no S3 dependency. Forcing preflight before arg parsing would make `python -m autom8_asana.metrics --list` fail on fresh clones where `ASANA_CACHE_S3_BUCKET` is absent, regressing a usability case that currently works. Handoff acceptance criterion (line 104: "metrics/__main__.py runs a lightweight preflight before load_project_dataframe") is compatible with "after argparse, conditional on path".
- **Before `load_project_dataframe`** because any later placement concedes the ground: once the transport layer is invoked, the error surface reverts to the generic `"No S3 bucket configured. Pass bucket= or set ASANA_CACHE_S3_BUCKET."` that the handoff explicitly names as the anti-pattern to eliminate (handoff line 106; smell inventory line 95).
- **Does not duplicate the 6-layer loader.** The 6-layer env loader is an ecosystem-level concern owned by `scripts/a8-devenv.sh:_a8_load_env` (lines 310-417 in the ecosystem worktree per handoff line 24). By the time the Python process starts, the loader has already resolved Layers 1-6 into `os.environ`. The preflight READS `os.environ` only; it does not load, source, or modify env files.

## Contract

### Input

- **Environment (read-only)**: `os.environ` as populated by the 6-layer loader. The preflight does not care which layer sourced each variable; it only checks whether the CLI-profile-required vars are present and non-empty.
- **No filesystem reads** beyond what `secretspec` (if shelled out) performs on `secretspec.toml` itself. The preflight does not read `.env/*` directly.
- **No network calls.** Validation is local; no AWS / S3 / Asana API contact.

### Output

- **Pass**: preflight returns (no exception). `main()` continues to the `load_project_dataframe` call.
- **Fail**: preflight writes the structured error message (template below) to `stderr` and exits the process with a **non-zero exit code** (recommend exit code `2` — distinct from the existing `1` used for generic errors at lines 67, 78, 85 — to let CI gates distinguish "preflight contract violation" from "runtime failure").

### Side effects

- **None permitted on `os.environ`.** The preflight MUST NOT mutate, unset, or inject env vars. Read-only.
- **No filesystem writes.**
- **No retry loops, no sleeps, no network.**
- **Logging**: the only stderr output on failure is the structured error message itself. On success, the preflight is silent (it adds no new stdout/stderr lines to the existing CLI output).

### Definition of "pass"

Exactly one of the following must hold:

1. `secretspec check --config secretspec.toml --provider env --profile cli` returns exit code `0` (see Implementation Alternative A below).
2. An inline functional equivalent (see Implementation Alternative B below) confirms: for each variable declared `required = true` under `[profiles.cli]` in `secretspec.toml` (currently `ASANA_CACHE_S3_BUCKET` and `ASANA_CACHE_S3_REGION` per ADR-0001), `os.environ.get(var)` is a non-empty string.

"Pass" does NOT include: probing the S3 bucket's existence, validating AWS credentials, checking region reachability, or any other side-effecting confirmation. Those belong to runtime; preflight stays side-effect-free.

## Before/after table

| Aspect | Current state (before CFG-006) | Proposed state (after CFG-006) |
|---|---|---|
| Error surface on missing `ASANA_CACHE_S3_BUCKET` | Generic: `"No S3 bucket configured. Pass bucket= or set ASANA_CACHE_S3_BUCKET."` raised from deep inside `dataframes/offline.py`, caught by `except (ValueError, FileNotFoundError)` at `src/autom8_asana/metrics/__main__.py:84-86`, printed as `ERROR: <msg>` with no file pointers. | Structured: preflight fails at approximately `__main__.py:~48` (immediately before the `# Load data` block) with a message naming `.env/defaults`, `.env/local.example`, and `secretspec.toml` as configuration sources. See Error Message Template below. |
| Failure time | After: arg parse → registry lookup → GID resolve → S3 client construction → S3 transport call → transport-layer raise → main catch. Typical: hundreds of ms to seconds depending on AWS SDK init. | After: arg parse → registry lookup → GID resolve → **preflight fail here**. Typical: <10 ms. |
| Where developer looks to fix | Generic error is at line 85. Developer must read the error text and guess that `ASANA_CACHE_S3_BUCKET` is an env var belonging to… somewhere. No mention of `.env/` files. No mention of `secretspec.toml`. Smell inventory documents this failure mode at lines 95-99. | Error names the three config files with explicit paths. Developer can `cat .env/local.example` to see placeholders, `cat .env/defaults` to see committed defaults, and `grep ASANA_CACHE_S3_BUCKET secretspec.toml` to see the contract. |
| Side effects on failure | S3 client construction may have run (boto3 typically does not touch network at construction time, but any SDK-level env probing has already fired). | Zero side effects. No AWS/S3/Asana calls attempted. |
| Exit code on failure | `1` (generic) via `sys.exit(1)` at line 86. | `2` (preflight contract violation) — distinct from the `1` retained for post-preflight runtime errors. |
| Behavior for `--list` | Works: no S3 dependency. | Unchanged: preflight does not run on the `--list` path. |
| Behavior for `python -m autom8_asana.metrics active_mrr` in happy path | Works when env is fully set. | Works identically when env is fully set — preflight is a no-op on success. |

## Implementation alternatives

### Alternative A — Shell out to `secretspec check --profile cli`

Invoke the `secretspec` binary as a subprocess, capture exit code and stderr, propagate failure.

**Pseudocode**:
```python
import subprocess
result = subprocess.run(
    ["secretspec", "check", "--config", "secretspec.toml", "--provider", "env", "--profile", "cli"],
    capture_output=True, text=True, check=False,
)
if result.returncode != 0:
    # format error and exit 2
```

**Trade-offs**:
- **Pro**: Guaranteed parity with `secretspec.toml`. When a future edit to the TOML adds or removes a `required = true` field under `[profiles.cli]`, the preflight picks it up with no Python-side change.
- **Pro**: The validator IS the authoritative source. No drift.
- **Con**: Requires `secretspec` binary in PATH at CLI invocation time. On dev machines this is routinely available (the header of `secretspec.toml:5` documents the command); in minimal containers it may not be.
- **Con**: Subprocess launch adds ~20-50 ms to happy-path CLI startup. Acceptable for interactive CLI usage; worth noting.

### Alternative B — Inline Python check mirroring the profile

Hard-code the CLI-profile-required variable names in Python and check `os.environ` directly.

**Pseudocode**:
```python
CLI_REQUIRED = ("ASANA_CACHE_S3_BUCKET", "ASANA_CACHE_S3_REGION")
missing = [v for v in CLI_REQUIRED if not os.environ.get(v)]
if missing:
    # format error and exit 2
```

**Trade-offs**:
- **Pro**: Zero external dependency. Works in any environment with Python.
- **Pro**: Instant (<1 ms).
- **Con**: **Drift hazard.** If a future edit to `secretspec.toml` adds a new `required = true` field under `[profiles.cli]` and forgets to update `CLI_REQUIRED` in Python, the preflight silently misses the new contract. This is the exact anti-pattern CFG-003 was designed to eliminate — duplicating validation contracts across files.
- **Mitigation if adopted alone**: add a test that parses `secretspec.toml` and asserts `CLI_REQUIRED` matches the TOML's `[profiles.cli]` required set. This restores single-source-of-truth at test time but still allows drift to reach production if the test is skipped.

### Alternative C — Subprocess with graceful fallback **[RECOMMENDED]**

Try Alternative A (shell out to `secretspec`). If the binary is missing (`FileNotFoundError` on subprocess launch, or `PermissionError`), fall back to Alternative B's inline check with a visible stderr note that fallback is in effect.

**Pseudocode**:
```python
def _preflight_cli_profile() -> None:
    try:
        result = subprocess.run(
            ["secretspec", "check", "--config", "secretspec.toml", "--provider", "env", "--profile", "cli"],
            capture_output=True, text=True, check=False, timeout=10,
        )
    except (FileNotFoundError, PermissionError):
        # secretspec binary unavailable; fall back to inline
        print("WARNING: secretspec binary not found; using inline preflight check.", file=sys.stderr)
        _preflight_inline_fallback()
        return
    if result.returncode != 0:
        _emit_structured_error(result.stderr)
        sys.exit(2)

def _preflight_inline_fallback() -> None:
    cli_required = ("ASANA_CACHE_S3_BUCKET", "ASANA_CACHE_S3_REGION")
    missing = [v for v in cli_required if not os.environ.get(v)]
    if missing:
        _emit_structured_error(f"Missing required CLI-profile variables: {', '.join(missing)}")
        sys.exit(2)
```

**Trade-offs**:
- **Pro**: Combines A's parity guarantee (when `secretspec` is available — the common dev-machine case) with B's dependency-free fallback (for minimal containers, CI jobs without the binary, etc.).
- **Pro**: Fallback is announced on stderr, making the regression from parity to hard-coded list visible to the developer.
- **Con**: Two code paths to maintain. Test coverage must exercise both.
- **Con**: Fallback still has the Alternative-B drift hazard. Mitigation: same test as B — parse `secretspec.toml` at test time and assert the inline `cli_required` tuple matches.

**Why recommended**: pragmatic. Dev machines get parity. CI without the binary still gets a preflight (degraded but present). The fallback warning is an observable signal rather than silent degradation.

### Rejected fourth alternative — Do nothing at the Python level, rely on a shell wrapper

Someone could propose wrapping `python -m autom8_asana.metrics` in a shell script that pre-runs `secretspec check --profile cli`. Rejected: users invoke the module directly, IDE run configs invoke it directly, Docker `CMD` invokes it directly. Any wrapper is bypassable and its absence is silent.

## Error message template

The preflight's stderr output on failure must be **exactly**:

```
ERROR: CLI preflight failed — [profiles.cli] contract in secretspec.toml requires the following env var(s) but they are unset or empty:
  - <VAR_NAME_1>
  - <VAR_NAME_2>   (if more than one)

This CLI entrypoint (python -m autom8_asana.metrics) runs under the 'cli' profile of secretspec.toml,
which is strict about S3 cache configuration. See:

  1. .env/defaults                (committed, Layer 3) — set committed project defaults here
     path: <REPO_ROOT>/.env/defaults
  2. .env/local.example → .env/local  (example committed; .env/local is gitignored, Layer 5)
     path: <REPO_ROOT>/.env/local.example
     copy: cp .env/local.example .env/local   # then edit .env/local with real values
  3. secretspec.toml              (the contract itself — declares which vars are required under --profile cli)
     path: <REPO_ROOT>/secretspec.toml
     validate: secretspec check --config secretspec.toml --provider env --profile cli

Typical fix: ensure .env/defaults contains ASANA_CACHE_S3_BUCKET and ASANA_CACHE_S3_REGION,
then re-run 'direnv allow' (or source the env manually) and retry.
```

**Machine-readability**: each of the three numbered config sources appears on its own line prefixed by the numeric index. CI gates parsing the error can regex-match `^\s+\d+\. \.env/` and `^\s+\d+\. secretspec\.toml` to count file-path mentions (the audit command in the smell inventory at line 99 expects ≥2 file-path mentions; this template emits 3). `<REPO_ROOT>` should be resolved to the absolute path at message-emit time so developers can copy-paste.

**Layer-path hints**: each config source carries its 6-layer-loader-contract position (`Layer 3`, `Layer 5`) and committed/gitignored status inline. This is the anchoring the smell inventory recommended at CFG-008 (loader documentation) prefigures — the error message doubles as a pointer back to the loader contract even before CFG-008's documentation lands.

**Variable-name listing**: each missing variable appears on its own indented line. When `secretspec` shells out (Alternative A), `result.stderr` is parsed for variable names; when the inline fallback runs (Alternative B), the variable names come from the hard-coded tuple. Both paths produce the same bulleted shape.

## Test points for audit-lead

Audit-lead must verify, in the CFG-006 gate, both the pass and fail paths. The handoff acceptance criteria at lines 104-107 define the pass/fail expectations; these test points translate them into concrete verification:

### Test point 1 — Preflight fires before `load_project_dataframe` on missing-bucket path

- **Setup**: start from a shell where `ASANA_CACHE_S3_BUCKET` is unset (or empty string).
- **Invoke**: `unset ASANA_CACHE_S3_BUCKET && python -m autom8_asana.metrics active_mrr 2>&1`
- **Expected**: non-zero exit (recommend `2`). Stderr contains at least the three file-path mentions (`.env/defaults`, `.env/local.example`, `secretspec.toml`).
- **Auditable command** (from smell inventory line 99): `unset ASANA_CACHE_S3_BUCKET && python -m autom8_asana.metrics active_mrr 2>&1 | grep -cE '\.env/(defaults|local\.example)|secretspec\.toml'` (expect ≥ 2; our template emits 3).
- **Source-attestation**: `grep -nE 'preflight|secretspec|check_cli_profile' src/autom8_asana/metrics/__main__.py` expect ≥1 match at a line number less than the current line 83 (the `load_project_dataframe` call site).

### Test point 2 — Preflight is silent on happy path

- **Setup**: start from a shell where CFG-001 has populated `.env/defaults` with bucket + region.
- **Invoke**: `python -m autom8_asana.metrics --list` (fast path, bypasses S3).
- **Expected**: exit `0`. Stdout shows the metric list as it does today. Stderr is empty (no preflight announcement).

### Test point 3 — `--list` bypasses preflight even when env is broken

- **Setup**: `unset ASANA_CACHE_S3_BUCKET`.
- **Invoke**: `python -m autom8_asana.metrics --list`
- **Expected**: exit `0`. List prints. No preflight error.
- **Why**: the `--list` path does not hit S3; forcing preflight here would regress usability.

### Test point 4 — Fresh-clone integration (keystone, handoff line 53)

- **Setup**: `( cd "$(mktemp -d)" && git clone <repo> repo && cd repo && direnv allow && python -m autom8_asana.metrics active_mrr )`
- **Expected**: exit `0`. No `export` statements needed by the developer.
- **Dependencies**: this test point requires CFG-001 (env defaults populated), CFG-003 (CLI profile declared), and CFG-006 (preflight wired) all landed. It is the integration test for the sprint's Wave 2, not for CFG-006 alone. Audit-lead should run it at the sprint gate, not at the CFG-006 gate in isolation.

### Test point 5 — Graceful fallback visibility (Alternative C specific)

- **Setup**: a shell with `ASANA_CACHE_S3_BUCKET` set but `secretspec` binary hidden via `PATH=/tmp python -m …` or equivalent.
- **Expected**: exit `0` (bucket is set, so inline fallback passes). Stderr contains the `WARNING: secretspec binary not found; using inline preflight check.` line.
- **Purpose**: verifies the fallback path is reachable and advertised.

## Rejection criteria (structural objections that send this back to architect)

The janitor should pause and route back to architect-enforcer if any of the following conditions holds during CFG-006 execution:

1. **Preflight cannot be placed where this TDD specifies without triggering an AWS/S3/Asana network call first.** The whole value of a preflight is zero-side-effect validation; if the import chain or module-level code in `autom8_asana.metrics` performs S3 probes at import time (before `main()` even begins), the preflight is structurally too late. Reject and escalate — fix the import-time side effect first.
2. **ADR-0001's profile split has not landed or failed empirical verification** (see ADR-0001 "Rejection criteria for janitor"). Without `[profiles.cli]` in `secretspec.toml`, Alternative A produces meaningless output (shells out to a check that has no strict vars) and Alternative B has no TOML ground truth to mirror. Pause CFG-006 execution and coordinate with CFG-003 status.
3. **The `--list` path cannot be structurally distinguished from the data-loading path at the insertion point.** If argparse branching has already been restructured such that `--list` and the default path converge before S3, the preflight would have to fire on `--list` too (regressing usability) or be pushed past the point of first S3 call (defeating the purpose). Reject — fix the branching structure, then apply preflight.
4. **The error-message template must emit a non-deterministic repo-root path that breaks CI parsing.** If resolving `<REPO_ROOT>` at message-emit time produces different output in CI vs local (e.g., container paths vs dev paths) such that CI gates parsing the error cannot rely on a stable regex, reject and escalate — the template needs redesign.
5. **Any proposed change would require modifications outside `src/autom8_asana/metrics/__main__.py`.** This TDD is boundary-scoped to the single entrypoint file. If the preflight logic belongs in a shared module (e.g., `src/autom8_asana/_cli_preflight.py`), that is an architectural choice beyond CFG-006's scope and must be escalated — not silently broadened.
6. **Exit code `2` collides with an existing convention in the repo.** If there is an undocumented convention that `exit(2)` means something specific (e.g., argparse's auto-generated error exit), the chosen exit code must be reconsidered. Janitor should `grep -rn 'sys\.exit(2)' src/` before committing; if collisions exist, escalate.

## Acceptance criteria (from handoff lines 103-107, translated to verification)

- [ ] `grep -nE 'preflight|secretspec|check_cli_profile' src/autom8_asana/metrics/__main__.py` matches ≥1 line at a position before the current line 83 equivalent (the `load_project_dataframe` call). **Source of truth**: handoff line 104.
- [ ] Error message on missing bucket surfaces ≥3 distinct file-path mentions (`.env/defaults`, `.env/local.example`, `secretspec.toml`). **Source of truth**: handoff line 105; smell inventory line 99.
- [ ] Generic `No S3 bucket configured. Pass bucket= or set ASANA_CACHE_S3_BUCKET.` no longer surfaces on the CLI path. Verified by: running the missing-bucket integration test and confirming the output does NOT contain that exact string (grep -c). **Source of truth**: handoff line 106.
- [ ] Happy-path invocation (with env set) is behaviorally identical to pre-CFG-006 state — same stdout, same exit code `0`, same computation. Verified by diff against a recorded happy-path output.
- [ ] `--list` path untouched: exit `0`, same stdout as pre-change, no preflight output.

## Links

- Companion ADR: `.ledge/decisions/ADR-env-secret-profile-split.md` (ADR-0001)
- Upstream handoff: `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md` (CFG-006 at lines 100-108)
- Smell inventory: `.ledge/reviews/smell-inventory-env-secrets-2026-04-20.md` (CFG-006 finding at lines 89-99)
- Source file to be edited: `src/autom8_asana/metrics/__main__.py` (lines 47-86 are the affected region; insertion point ~line 48-80)
- Reference-only files (not edited by CFG-006): `secretspec.toml`, `.env/defaults`, `.env/local.example`, `scripts/a8-devenv.sh`
