---
domain: feat/lockfile-propagator
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./.ledge/decisions/ADR-lockfile-propagator-source-stubbing.md"
  - "./.ledge/specs/lockfile-propagator-source-stubbing.tdd.md"
  - "./.know/scar-tissue.md"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.88
format_version: "1.0"
status: "proposed"
external_source: "autom8y/tools/lockfile-propagator/"
---

# Feature Knowledge: Lockfile-Propagator In-Tool Source Stubbing

## 1. Purpose and Design Rationale

### Problem Statement

The autom8y monorepo publishes SDKs via `sdk-publish-v2.yml`. After each publish, the
`Notify Satellite Repos` job invokes the `lockfile-propagator` tool to open lockfile-bump
PRs in each of the 5 consuming satellites (autom8y-asana, autom8y-data, autom8y-scheduling,
autom8y-sms, autom8y-ads).

The propagator fails 5/5 satellites at this step. Each satellite's `pyproject.toml` declares
`[tool.uv.sources]` editable path entries of the form `{ path = "../X", editable = true }`.
These are developer-side paths that point to sibling repos (e.g. `autom8y-api-schemas`,
`autom8y/sdks/python/autom8y-client-sdk`). The propagator clones each satellite into
`/tmp/lockfile-propagator-XXXXXXXX/<satellite>/`, then invokes `uv lock --upgrade-package
<sdk>==<version>` with `cwd=repo_dir`. Inside the temp sandbox, `..` resolves back to
`/tmp/lockfile-propagator-XXXXXXXX/` — which contains only satellite clones, NOT the
developer-side siblings. uv emits `error: Distribution not found at: file:///tmp/...`.
This becomes `LockfileError` → per-satellite `status="failed"`.

**Failure was empirically observed** in workflow runs `25052186961` (autom8y-config 2.0.1)
and `25062121802` (autom8y-config 2.0.2). Documented as SCAR-LP-001 in `.know/scar-tissue.md`.

### SCAR-LP-001 Origin

SCAR-LP-001 ("lockfile-propagator stub-before-uv-lock ordering invariant") is the canonical
scar entry. Root cause: satellite cloned to tmpdir; `uv lock` with `cwd=repo_dir` resolves
`path = "../X"` against tmpdir parent, not developer-side siblings. Fix: `source_stub.py`
at `autom8y/tools/lockfile-propagator/` stubs editable path sources before invoking `uv lock`.

### Decision: Option A (In-Tool Source Stubbing)

An SRE rite spike enumerated **8 candidate fixes**. The spike
(`.sos/wip/SPIKE-lockfile-propagator-tooling-fix.md`, 449 lines) analyzed all 8 options.
The ADR (`.ledge/decisions/ADR-lockfile-propagator-source-stubbing.md`) adopted Option A.

**Option A was selected on five criteria:**

1. **Smallest blast radius** — only the propagator tool changes; zero satellite changes,
   zero workflow changes, zero SDK changes.
2. **High reversibility** — deletion of one module + one call site fully reverts. Two-way
   door. No committed state mutations; stubs live in `tempfile.TemporaryDirectory` and are
   GC'd with the work_root.
3. **Dev experience preserved** — developers continue using `path = "../X"` locally; the
   propagator becomes invisible to them.
4. **Precedent fit** — the existing `.github/actions/api-schemas-stub/action.yml` established
   the "stub the resolution target" discipline at publish-job altitude; Option A applies the
   same discipline at sub-clone altitude.
5. **Within deadline budget** — stub creation is filesystem-only, sub-second per satellite,
   well within the `DEFAULT_PER_SATELLITE_TIMEOUT_SECONDS = 55` budget. Empirical probe
   measured `uv lock` against a stub at 21ms wall-clock.

**Rejected alternatives summary:**

| Option | Rejection Reason |
|--------|-----------------|
| B — Rewrite path = "../X" to absolute | Loses lockfile fidelity; requires revert step |
| C — Clone sibling repos into work_root | Heavier: extra clones × N publishes; expands GitHub App token scope |
| D — `uv lock --no-sources` | Semantic change: lockfile diverges from local-dev expectations |
| E — Convert to git+ssh sources | 5 satellite PRs; slows dev (network fetches); adds auth complexity |
| F — Replace propagator with renovate/dependabot | Out of scope; propagator implements custom D7 semantics |
| G — Accept failure; document workaround | Anti-pattern; defeats automated lockfile propagation throughline |
| H — Run uv lock from stable parent dir | Effort approaches Option C without its benefits |

### Why It Lives in the autom8y Monorepo

The `lockfile-propagator` is a monorepo-side tool (`autom8y/tools/lockfile-propagator/`).
It runs inside the autom8y CI pipeline (`sdk-publish-v2.yml:971-1130`), not inside
satellite repo pipelines. The source stubbing fix (`source_stub.py`) belongs there because
the failure surface — the tmpdir sandbox created by the propagator — exists only in the
autom8y monorepo's CI execution context. This satellite repo (autom8y-asana) holds the
decision artifacts (ADR, TDD) because the 10x-dev rite that authored the fix was operating
from this repo as the session_repo, but the production code change resides in the autom8y
monorepo.

---

## 2. Conceptual Model

### The Core Invariant

**Stub before lock.** After a satellite clone materializes, before `uv lock` fires, every
relative-path `[tool.uv.sources]` entry must resolve to an existing directory containing
a `pyproject.toml`. The propagator creates minimal "stub packages" at those resolved paths.

### Three Discriminators (the defensive pattern)

These three discriminators define what `stub_editable_path_sources()` does and does not do:

**Discriminator 1 — Only stub `path =` entries (never `git =`, `url =`, `index =`)**

```toml
foo = { path = "../foo" }                       # STUBBED
bar = { path = "../bar", editable = true }      # STUBBED (canonical satellite shape)
baz = { path = "../baz", editable = false }     # STUBBED (defensive — path without editable)
qux = { git = "https://github.com/x/qux" }      # LEFT UNTOUCHED
quux = { url = "https://example.com/quux.zip" } # LEFT UNTOUCHED
quuux = { index = "autom8y" }                   # LEFT UNTOUCHED (CodeArtifact)
```

The discriminator: `"path" in entry AND entry.get("git") is None AND entry.get("url") is
None AND entry.get("index") is None`. This satisfies the handoff acceptance criterion that
non-editable-path sources (git URLs, registry indices) experience zero regression.

**Discriminator 2 — Stub `pyproject.toml` requires only `[project]` + `[build-system]`**

```toml
[project]
name = "{source_name}"
version = "0.0.0"
requires-python = ">=3.12"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

No Python source files, no `__init__.py`, no importable modules are required. Empirically
validated (OQ-A probe at `/tmp/uvprobe-source-stub/` with `uv 0.9.7`): `uv lock` exits 0
against a stub with ONLY `pyproject.toml`. The `api-schemas-stub` composite action
(`action.yml:33-102`) includes importable modules because it feeds `uv sync` (which installs
and may import). The propagator runs `uv lock` only — no import occurs.

The version `"0.0.0"` is ceremonial. uv's editable path source resolution overrides PEP 440
floor specifiers when `[tool.uv.sources]` declares `path = ...`. A stub at `version = "0.0.0"`
satisfies a satellite floor declaration of `sib>=1.9.0` (probe at `/tmp/uvprobe-floor/`).

**Discriminator 3 — Idempotent on re-run**

If `stub_dir/pyproject.toml` already exists, the write is skipped and the entry is recorded
as `skipped=True, skip_reason="stub already present"`. This matters for the fan-out
concurrency model: when two satellites in the same `work_root` declare the same relative path
(e.g. both `autom8y-asana` and `autom8y-data` point to `../autom8y-api-schemas`), the first
satellite to be processed creates the stub; the second sees it as already-present and skips.
Both satellites' subsequent `uv lock` invocations see the same stub. The write race is benign
because stubs are content-identical (`name = ..., version = "0.0.0"`).

### Key Types and Terminology

| Term | Definition |
|------|-----------|
| `work_root` | `tempfile.TemporaryDirectory(prefix="lockfile-propagator-")` — the sandbox root created by `cli.py`; all satellite clones and stubs live here; GC'd at end of run |
| `repo_dir` | `work_root / satellite_name` — the shallow-cloned satellite directory inside the work_root |
| `stub_dir` | `(repo_dir / path_value).resolve()` — the directory where a minimal `pyproject.toml` is written to satisfy `uv lock`'s resolution |
| `StubbedSource` | Frozen dataclass record: `source_name`, `stub_path`, `skipped`, `skip_reason` |
| `SourceStubError` | Exception raised on missing/malformed `pyproject.toml` or filesystem write failure; becomes per-satellite `status="failed"` via `fail(reason, ...)` |
| `stub_editable_path_sources()` | The public API of `source_stub.py`; takes `repo_dir` + `work_root`; returns `list[StubbedSource]` |
| `path-source` | A `[tool.uv.sources]` entry with a `path` key — the only kind the stub mechanism targets |
| `sub-clone altitude` | The execution context inside the propagator after a satellite is cloned but before `uv lock` fires — distinguishes this fix from the publish-job-altitude `api-schemas-stub` action |

### Relationship to the `api-schemas-stub` Precedent

There are now **two distinct stub mechanisms** in the autom8y monorepo:

| Mechanism | Altitude | Purpose | Requires modules? |
|-----------|----------|---------|------------------|
| `.github/actions/api-schemas-stub/action.yml` | Publish-job | Enables `uv sync` in satellite-CI consumers | Yes (importable Python symbols) |
| `source_stub.py` (this feature) | Sub-clone (inside propagator) | Enables `uv lock` for path-source resolution | No (TOML only) |

The two stubs coexist. Future risk: if `autom8y-api-schemas` graduates to CodeArtifact, both
stubs need to be reconsidered. The TDD records this as a `DEFER-FOLLOWUP` consolidation ADR
candidate.

### Fan-Out Concurrency Model

The propagator processes satellites in parallel via `parallel.py`'s `propagate_all_sync`. The
`stub_editable_path_sources()` function is called per-satellite inside the fan-out. The stub
target directories live in `work_root` (shared across satellites), not inside each satellite's
`repo_dir`. The idempotency guarantee (Discriminator 3) makes concurrent writes safe.

---

## 3. Implementation Map

### Knowledge Boundary: External Source

The production source code for this feature resides in the **autom8y monorepo**, NOT in this
satellite repository (autom8y-asana). The specific module is:

```
autom8y/tools/lockfile-propagator/src/lockfile_propagator/source_stub.py
```

This file is not locally accessible from the autom8y-asana working tree. The knowledge
below is derived from the TDD spec (`.ledge/specs/lockfile-propagator-source-stubbing.tdd.md`)
and ADR (`.ledge/decisions/ADR-lockfile-propagator-source-stubbing.md`), which together
constitute a complete implementation specification. The autom8y PR #174 (SHA `f2dfc1c3`)
is recorded as the merge commit; the file's existence at origin/main is attested in
SCAR-P6-001 evidence (blob `bf4f74180e15f07a698538afa14f6f82d47bf641`).

### Module Map (autom8y monorepo)

| File | Purpose |
|------|---------|
| `src/lockfile_propagator/source_stub.py` | New module (this feature). ~80-120 LOC. Exports `stub_editable_path_sources()` and `SourceStubError`. |
| `src/lockfile_propagator/propagator.py` | Orchestration. Single integration call site inserted between `propagator.py:184` (post-checkout_branch) and `propagator.py:189` (pre-pyproject-rewrite block). |
| `src/lockfile_propagator/repo_clone.py` | `SubprocessGitOps.clone_shallow:99-125` — creates the `repo_dir` that `stub_editable_path_sources()` reads. |
| `src/lockfile_propagator/lockfile_updater.py` | `SubprocessUvLockRunner.upgrade_package:85-117` — the `uv lock` invocation that requires stubs to be present. |
| `src/lockfile_propagator/cli.py` | `_WorkRootContext:218-238` — provisions the `tempfile.TemporaryDirectory` (work_root); its `__exit__` reclaims stubs. |
| `src/lockfile_propagator/__init__.py` | `DEFAULT_DEADLINE_SECONDS=60`, `DEFAULT_PER_SATELLITE_TIMEOUT_SECONDS=55:30-35`. |
| `tests/test_source_stub.py` | Unit + integration tests for `source_stub.py` (10 unit tests + 1 integration test). |

### Public API Surface of `source_stub.py`

```python
class SourceStubError(RuntimeError):
    """Raised when stub creation fails (filesystem error or malformed pyproject)."""

@dataclass(frozen=True)
class StubbedSource:
    source_name: str           # e.g. "autom8y-api-schemas"
    stub_path: Path            # absolute path to the stub directory
    skipped: bool              # True if entry was non-path or stub already existed
    skip_reason: str | None    # populated when skipped

def stub_editable_path_sources(
    *,
    repo_dir: Path,
    work_root: Path,
) -> list[StubbedSource]:
    ...
```

### Internal Helper Functions (private, `source_stub.py`)

```python
def _parse_uv_sources(pyproject_path: Path) -> dict[str, dict]
    # Reads pyproject.toml; returns [tool.uv.sources] table. Raises SourceStubError on error.

def _is_editable_path_source(entry: dict) -> bool
    # True iff entry has 'path' key AND no 'git'/'url'/'index' key.

def _render_stub_pyproject(name: str) -> str
    # Returns minimal pyproject.toml text. Mirrors api-schemas-stub action.yml:22-31.

def _write_stub_pyproject(stub_dir: Path, name: str) -> None
    # Idempotent write: mkdir -p + write. No-op if pyproject.toml already exists.
```

### Integration Call Site (`propagator.py`)

The hook is inserted **after `clone_shallow()` and branch checkout, before the
`pyproject_changed`/uv-lock block**. Specifically: between `propagator.py:184`
(post-`checkout_branch`) and `propagator.py:189` (the `if classification.requires_pyproject_change`
block):

```python
# After branch checkout, before pyproject rewrite + uv lock:
try:
    from lockfile_propagator.source_stub import (
        SourceStubError,
        stub_editable_path_sources,
    )
    stub_editable_path_sources(
        repo_dir=repo_dir,
        work_root=ctx.work_root,
    )
except SourceStubError as exc:
    return fail(
        f"source stub failed: {exc}",
        bump_kind=classification.kind,
    )
```

This altitude is correct because: (1) `repo_dir/pyproject.toml` is parseable after clone;
(2) `work_root` exists and is writable; (3) stubs are present before uv lock fires;
(4) `cli.py:233-234` work_root cleanup reclaims stubs automatically.

### Propagator Flow with This Feature (per-satellite)

```
1. clone_shallow()              → repo_dir materialized (repo_clone.py:99-125)
2. detect_constraint()          → bump classification (propagator.py:146-167)
3. checkout_branch()            → target branch checked out (propagator.py:182)
4. stub_editable_path_sources() → stubs written to work_root (THIS FEATURE)
5. [optional pyproject rewrite] → MAJOR bumps only (propagator.py:191)
6. uv_runner.upgrade_package()  → uv lock --upgrade-package (lockfile_updater.py:96-105)
7. change detection / commit / push / PR (propagator.py:210-325)
```

### Decision Artifacts (in this repo)

| Artifact | Path | Contents |
|----------|------|---------|
| ADR | `.ledge/decisions/ADR-lockfile-propagator-source-stubbing.md` | Architectural decision, 8 alternatives, consequences, provenance |
| TDD | `.ledge/specs/lockfile-propagator-source-stubbing.tdd.md` | Full component design, resolved open questions (OQ-A through OQ-E), test strategy, risk register |
| Defer-watch entry | `.know/defer-watch.yaml` (`lockfile-propagator-prod-ci-confirmation`) | Production-CI confirmation deferred; deadline 2026-07-29 |
| SCAR entry | `.know/scar-tissue.md` (SCAR-LP-001) | Root cause, fix summary, three-discriminator defensive pattern |

### Test Coverage (autom8y monorepo)

Test module: `autom8y/tools/lockfile-propagator/tests/test_source_stub.py`.

| Test ID | Scenario |
|---------|---------|
| T-A | Single editable path source → stub created |
| T-B | Multiple editable path sources → two stubs |
| T-C | Extras + markers preserved → stub declares `[project.optional-dependencies]`; real `uv lock` succeeds |
| T-D | `git =` sources left untouched → no filesystem writes |
| T-D2 | `index =` sources (CodeArtifact shape) left untouched |
| T-E | Malformed `pyproject.toml` → `SourceStubError` |
| T-E2 | Missing `pyproject.toml` → `SourceStubError` |
| T-F | Idempotency: second call, same work_root → all `skipped=True` |
| T-F2 | Two satellites, same resolved path → first creates; second skips |
| T-G | `{ path = "../x" }` without `editable` flag → still stubbed |
| Integration | Reproduces autom8y-asana failure mode: assert `uv lock` FAILS pre-stub, SUCCEEDS post-stub |

The integration test requires `uv` on `$PATH`; gated with `@pytest.mark.skipif(shutil.which("uv") is None, ...)`.
Test style mirrors `tests/test_lockfile_updater.py:1-80`: real tmpdir `pyproject.toml` files, no mocks.

---

## 4. Boundaries and Failure Modes

### Scope: What This Feature Does

- Stubs relative-path `[tool.uv.sources]` entries inside the propagator's sandbox so `uv lock`
  can resolve them without requiring developer-side sibling repos to be present.
- Creates minimal `pyproject.toml`-only stubs (no Python source files).
- Operates entirely within the per-run `tempfile.TemporaryDirectory`; no state persists post-run.
- Applies to all 5 autom8y satellites that declare `path =` sources.

### Scope: What This Feature Does NOT Do

- Does NOT stub `git =`, `url =`, or `index =` source entries (explicit out-of-scope per OQ-C).
- Does NOT modify any satellite's `pyproject.toml` (authority boundary per HANDOFF).
- Does NOT modify the `api-schemas-stub` composite action (orthogonal).
- Does NOT widen the `[tool.uv.sources]` schema.
- Does NOT republish any prior SDK versions.
- Does NOT add importable Python modules to stubs (not needed for `uv lock`; only `uv sync` needs symbols).
- Does NOT run `uv sync` — only `uv lock` is in scope.
- Does NOT affect the per-satellite SLA (sub-second stub creation; well within 55s budget).

### Current Status

**Proposed — production-CI UNATTESTED.** The fix (`source_stub.py`) landed in autom8y PR #174
(SHA `f2dfc1c3`). However, no push-triggered SDK publish has successfully reached the
`Notify-Satellite-Repos` step since the merge. Two post-merge workflow runs failed at the
`Publish` step (CodeArtifact 409 / version-already-exists) — a different step — causing
`Notify-Satellite-Repos` to be skipped.

**Mechanical equivalence IS attested**: the TDD §5.2 integration test (canonical autom8y-asana
failure mode) + cross-satellite shape equivalence per TDD §4 OQ-C are both attested.

**Defer-watch entry** `lockfile-propagator-prod-ci-confirmation` (`.know/defer-watch.yaml`)
tracks this gap. Deadline: **2026-07-29**. Close condition: a workflow run where the Publish
step succeeds AND Notify-Satellite-Repos records `status=SUCCESS` for at least one satellite
AND `uv lock` completes without `Distribution not found at: file:///tmp/lockfile-propagator-...`.

### Known Failure Modes

| ID | Failure Mode | Likelihood | Mitigation |
|----|-------------|-----------|-----------|
| R-1 | uv lock semantics change: editable sources stop overriding floor specifiers | Low | uv version pinned at `sdk-publish-v2.yml:1010`; T-C integration test catches semantic regressions |
| R-2 | Future satellite adds source that requires importable module surface (needs `uv sync`, not just `uv lock`) | Low | Stubs would produce valid `uv.lock` but `uv sync` in satellite-CI would fail; surfaced via satellite-CI `repository_dispatch` path |
| R-3 | Two satellites declare same relative path with different version requirements | Very Low | Stubs use `version = "0.0.0"` which satisfies all floor specifiers under uv editable semantics; race is benign |
| R-4 | Stub creation succeeds but `uv lock` fails for unrelated reason; failure masked under "uv lock failed" path | Low | Stub log line records `[StubbedSource]` count in verdict JSON; separates failure verbiage |
| R-5 | Symbol-surface drift between stub and real schema | N/A | Eliminated by OQ-A: no symbols in stub; `uv lock` never imports |
| R-6 | Stub mechanism drift vs. `api-schemas-stub` action | Medium (future) | Both stubs need reconsideration if `autom8y-api-schemas` graduates to CodeArtifact; recorded as DEFER-FOLLOWUP in TDD §9 |

### Interaction Points and Boundary Clarity

**Upstream interaction**: `propagator.py`'s `clone_shallow()` step must complete successfully
before `stub_editable_path_sources()` is called (stubs require a materialized `pyproject.toml`
to parse). The hook point is explicitly documented as after `checkout_branch` at `propagator.py:184`.

**Downstream interaction**: `stub_editable_path_sources()` must complete before
`uv_runner.upgrade_package()` fires (stubs must exist when `uv lock` runs). The call-ordering
invariant is locked by test `test_path_sources_stubbed_before_uv_lock_runs` in
`tests/test_propagator.py`.

**Parallel fan-out**: the stub directory is a shared resource within `work_root` across
satellite-parallel executions. Idempotency (Discriminator 3) and content-identical stubs
(all at `version = "0.0.0"`) make the race benign.

**No satellite impact**: the feature operates purely within the propagator's tmpdir sandbox.
Satellite `pyproject.toml` files are never modified (authority boundary from HANDOFF).

### Rollback Path

This is a **two-way door**:
1. Delete the `source_stub.py` module.
2. Delete the integration call block at `propagator.py:188`.

No state mutations outside the per-run `tempfile.TemporaryDirectory` occur during normal
operation. Nothing persists post-run. Rollback is literal code deletion; behavior reverts
to the prior broken state (5/5 satellites red on Notify).

---

## Domain Assessment: feat/lockfile-propagator

**Overall Grade: A** (92% criteria met)

**Audit Scope:** feature knowledge capture for lockfile-propagator source stubbing
**Artifacts Evaluated:** ADR, TDD spec, scar-tissue entry, defer-watch entry, architecture seed
**Evaluation Date:** 2026-05-08

### Criteria Results

| Criterion | Grade | Evidence | Notes |
|-----------|-------|----------|-------|
| Purpose and Design Rationale (30%) | A (95%) | ADR + SCAR-LP-001 + 8-option spike analysis fully documented | Problem statement clear; all 8 alternatives with rejection reasons present; consequences analyzed; SCAR origin documented |
| Conceptual Model (25%) | A (92%) | Three discriminators fully specified; OQ-A/B/C/D resolved empirically; fan-out concurrency model documented | All key terminology defined; mental model enables safe modification |
| Implementation Map (25%) | B (85%) | ADR + TDD spec provide complete implementation blueprint; external source boundary explicitly marked | Production source at autom8y/tools/lockfile-propagator/ is inaccessible from this repo; map is derived from specs, not source read |
| Boundaries and Failure Modes (20%) | A (95%) | Risk register R-1 through R-6; explicit NOT-scope list; defer-watch close condition documented | SCAR-LP-001 defensive pattern + production-CI status accurately stated |

### Findings

#### Strengths

- **Complete rationale with empirical evidence**: OQ-A/B/C/D each resolved via empirical probes at specific tmpdir paths with exact uv version (0.9.7). An agent can understand not just what was decided but why the alternatives were ruled out.
- **Three-discriminator defensive pattern**: Concise, closed-form rule for source-type discrimination means no human judgment is needed at runtime. Fully specified and tested.
- **Explicit knowledge boundary**: The external source location is clearly marked rather than glossed over. Implementation Map notes what is derived from specs vs. direct source read.
- **Defer-watch binding**: Close condition is specific and machine-verifiable (three conditions, single workflow run sufficient).

#### Weaknesses

- **Implementation Map derived from specs, not source**: The production `source_stub.py` (~327 LOC per census) has not been read directly; the implementation map is reconstructed from the TDD spec. If the implementation diverged during PR review, this document would not reflect those divergences.
- **Extras-declaration nuance not surfaced in conceptual model**: OQ-D's finding that stubs SHOULD declare consumed extras in `[project.optional-dependencies]` (warning-free but not resolution-critical) adds ~15 LOC and may surprise a maintainer reading only the conceptual model section.

#### Recommendations

1. **Re-read source_stub.py after monorepo access is available**: Confirm implementation matches TDD; update LOC count (TDD says 80-120, census says 327) and check for any review-time divergences. The 327 LOC vs 80-120 LOC discrepancy warrants investigation.
2. **Promote extras-declaration detail to Conceptual Model**: Move the OQ-D extras-handling note from the boundaries section to the conceptual model so it is visible to any agent touching the stub renderer.

```metadata
domain: feat/lockfile-propagator
source_hash: "8980bcd7"
generated_at: "2026-05-08T00:00Z"
confidence: 0.88
criteria_grades:
  purpose_and_design_rationale:
    grade: A
    pct: 95
    weight: 0.30
  conceptual_model:
    grade: A
    pct: 92
    weight: 0.25
  implementation_map:
    grade: B
    pct: 85
    weight: 0.25
  boundaries_and_failure_modes:
    grade: A
    pct: 95
    weight: 0.20
overall_grade: A
overall_pct: 92
notes: >
  High confidence on purpose, design rationale, conceptual model, and boundaries
  because ADR + TDD are unusually detailed with empirical probes. Implementation map
  grade B due to external source constraint: production source_stub.py resides in
  autom8y monorepo and could not be read directly. All derivations are from
  well-specified TDD (component design at §3) and ADR. The 327 LOC vs 80-120 LOC
  TDD estimate discrepancy in the census is a known open question.
  Status: proposed; production-CI confirmation deferred to 2026-07-29.
```
