---
schema_version: "1.0"
type: spec
spec_kind: tdd
slug: lockfile-propagator-source-stubbing
title: "Lockfile-propagator source stubbing — sub-clone altitude"
date: 2026-04-29
status: proposed
author_rite: 10x-dev
author_agent: architect
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y
target_module: autom8y/tools/lockfile-propagator
parent_artifacts:
  handoff: .ledge/handoffs/HANDOFF-sre-to-10x-dev-lockfile-propagator-fix-2026-04-28.md
  spike: .sos/wip/SPIKE-lockfile-propagator-tooling-fix.md
  adr: .ledge/decisions/ADR-lockfile-propagator-source-stubbing.md
  precedent_pattern: autom8y/.github/actions/api-schemas-stub/action.yml
authority: "10x-dev rite per HANDOFF authority boundary; spike Option A recommended"
disciplines:
  - option-enumeration-discipline
  - structural-verification-receipt
  - authoritative-source-integrity
  - telos-integrity-ref
---

# TDD: Lockfile-Propagator Source Stubbing

> Implementation design for the SRE→10x-dev handoff. Resolves the
> 5/5-satellites red-on-Notify failure mode by extending the existing
> `api-schemas-stub` precedent from publish-job altitude down to
> sub-clone altitude inside the lockfile-propagator tool.

## §1 Telos Restatement

Restore the `Notify Satellite Repos` job in `sdk-publish-v2.yml` to a
green verdict for ALL 5 satellites (autom8y-ads, autom8y-asana,
autom8y-data, autom8y-scheduling, autom8y-sms) on the next SDK publish
that triggers them. Each satellite's lockfile-bump PR auto-opens via the
propagator with the new SDK version pinned in `uv.lock`. User-visible
outcome: an SDK publish in the autom8y monorepo automatically lands a
lockfile-bump PR in every consuming satellite within the propagator's
60-second deadline budget, with no manual symlink workaround required.
Telos owner: 10x-dev rite per HANDOFF authority boundary
(`.ledge/handoffs/HANDOFF-sre-to-10x-dev-lockfile-propagator-fix-2026-04-28.md:113`).
Verification attester: rite-disjoint — SRE rite reviews workflow run
verdicts post-merge per HANDOFF §"Verification Attestation"
(`...HANDOFF-sre-to-10x-dev-lockfile-propagator-fix-2026-04-28.md:140`).

## §2 Architecture Summary

### 2.1 Propagation flow (SVR-anchored)

The propagator's per-satellite flow is documented at `propagator.py:13-22`
and implemented in `propagate_to_satellite()` at `propagator.py:89-325`:

1. **Clone** — `ctx.git_ops.clone_shallow(clone_spec)` at
   `propagator.py:132`. Production implementation at
   `repo_clone.py:99-125` shells out to `git clone --depth 1 --branch
   <ref> https://x-access-token:<token>@github.com/<owner>/<repo>.git
   <dest>`. The destination path is composed at `propagator.py:123`:
   `dest = ctx.work_root / satellite`.

2. **Constraint detection + bump classification** —
   `detect_constraint(pyproject_path, sdk)` at `propagator.py:146`,
   classification at `propagator.py:167`.

3. **Branch checkout** — `ctx.git_ops.checkout_branch(repo_dir, branch,
   ctx.base_ref)` at `propagator.py:182`.

4. **Optional pyproject rewrite** (MAJOR bumps only) —
   `rewrite_constraint(...)` at `propagator.py:191`.

5. **uv lock invocation** — `ctx.uv_runner.upgrade_package(repo_dir=...,
   sdk=..., version=...)` at `propagator.py:204`. Production runner at
   `lockfile_updater.py:85-117` shells out to `uv lock --upgrade-package
   <sdk>==<version>` with `cwd=repo_dir`.

6. **Change detection / commit / push / PR** —
   `propagator.py:210-325`.

### 2.2 Failure mode (SVR-anchored)

The work_root is provisioned by `_WorkRootContext.__enter__` at
`cli.py:225-230`, which calls `tempfile.TemporaryDirectory(prefix=
"lockfile-propagator-")`. So `ctx.work_root` =
`/tmp/lockfile-propagator-XXXXXXXX/` and clones land at
`/tmp/lockfile-propagator-XXXXXXXX/<satellite>/` (composed at
`propagator.py:123`).

When `uv lock` runs at `lockfile_updater.py:96-105` with
`cwd=repo_dir`, it parses the satellite's `[tool.uv.sources]` and
resolves `path = "../X"` entries relative to `repo_dir`. For the
satellite at `/tmp/lockfile-propagator-XXX/autom8y-asana/`, `..`
resolves to `/tmp/lockfile-propagator-XXX/`, which contains only
satellite clones — NOT the developer-side siblings
(`autom8y-api-schemas`, `autom8y/sdks/python/autom8y-client-sdk`). uv
emits exit-2 with `error: Distribution not found at: file:///tmp/...`
(`SPIKE...md:107-109`). Wrapped as `LockfileError` at
`lockfile_updater.py:113-117`, becomes per-satellite `status="failed"`.

### 2.3 Hook point (right altitude)

The right hook is **after `clone_shallow()` succeeds, before the uv
lock invocation runs** — i.e. between `propagator.py:132` and
`propagator.py:204`. Concretely: immediately after constraint
detection and branch checkout, just prior to the
`pyproject_changed`/uv-lock block. This altitude is correct because:

- The clone has materialized `repo_dir/pyproject.toml`, so
  `[tool.uv.sources]` is parseable.
- The work_root parent directory exists and is writable (it's the
  `tempfile.TemporaryDirectory` from `cli.py:229`).
- All stub creation happens before uv lock fires — uv sees a fully
  populated relative-path resolution surface when it runs at
  `lockfile_updater.py:96-105`.
- The work_root cleanup at `cli.py:233-234` reclaims the stubs along
  with the clones; no separate cleanup branch is needed.

### 2.4 Precedent: api-schemas-stub

The composite action at `.github/actions/api-schemas-stub/action.yml:1-103`
establishes the pattern this design extends. The action creates a fake
`autom8y-api-schemas` package at
`${{ github.workspace }}/../autom8y-api-schemas` with:

- A minimal `[project]` table (`action.yml:22-31`): name + version +
  `requires-python` + `[build-system]` (hatchling).
- Importable Python modules with placeholder symbols
  (`action.yml:33-102`) so that `uv sync` (which actually installs
  packages and may import them) can satisfy the satellite-CI
  consumers.

This TDD's stub does NOT need the Python module surface — see §4 OQ-A.
Only the `pyproject.toml` `[project]` table is required for `uv lock`'s
resolution path.

## §3 Component Design — `source_stub.py`

### 3.1 Module location

New module: `autom8y/tools/lockfile-propagator/src/lockfile_propagator/source_stub.py`.

Sized at ~80–120 LOC matching the spike estimate
(`SPIKE...md:204-206`). Plus tests at
`autom8y/tools/lockfile-propagator/tests/test_source_stub.py`.

### 3.2 Public API

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

class SourceStubError(RuntimeError):
    """Raised when stub creation fails (filesystem error or malformed
    pyproject)."""

@dataclass(frozen=True)
class StubbedSource:
    """Record of one stub that was created (or skipped)."""
    source_name: str           # e.g. "autom8y-api-schemas"
    stub_path: Path            # absolute path to the stub directory
    skipped: bool              # True if entry was non-path or stub already existed
    skip_reason: str | None    # populated when skipped

def stub_editable_path_sources(
    *,
    repo_dir: Path,
    work_root: Path,
) -> list[StubbedSource]:
    """Parse repo_dir/pyproject.toml [tool.uv.sources] and create
    minimal stub packages at the resolved relative-path locations
    inside work_root.

    Stubbing rules:
      - Only entries with shape ``{ path = "...", editable = true }``
        AND/OR ``{ path = "..." }`` are stubbed. Entries with shape
        ``{ git = ... }`` or ``{ index = ... }`` are LEFT UNTOUCHED.
      - The resolved stub path is computed as
        ``(repo_dir / path_value).resolve()``. If the resolved path
        already exists as a directory containing a pyproject.toml,
        the entry is SKIPPED (idempotency: a previous stub run on the
        same work_root MUST be safe to re-execute).
      - For each new stub, ``stub_path/pyproject.toml`` is written
        with a minimal [project] table; no Python source files are
        created.

    Returns a list of StubbedSource records describing every entry
    inspected (created or skipped).

    Raises:
      SourceStubError if repo_dir/pyproject.toml is missing, malformed,
      or if a stub-write fails for filesystem reasons.

    Side effects:
      Creates directories under work_root containing pyproject.toml
      files. Does NOT modify repo_dir or any file inside it.
    """
```

### 3.3 Internal helpers (private)

```python
def _parse_uv_sources(pyproject_path: Path) -> dict[str, dict]:
    """Read pyproject.toml; return [tool.uv.sources] table as dict.

    Empty dict if [tool.uv.sources] is absent.
    Raises SourceStubError on TOMLDecodeError or missing file."""

def _is_editable_path_source(entry: dict) -> bool:
    """True iff entry has 'path' key AND no 'git'/'url'/'index' key.
    Treats { path = "..." } and { path = "...", editable = true }
    identically for stubbing purposes."""

def _render_stub_pyproject(name: str) -> str:
    """Return the minimal pyproject.toml text for a stub package.
    Mirrors api-schemas-stub action.yml:22-31 shape."""

def _write_stub_pyproject(stub_dir: Path, name: str) -> None:
    """Idempotent write: mkdir -p stub_dir; write pyproject.toml.
    No-op if pyproject.toml already exists at stub_dir."""
```

### 3.4 Stub `pyproject.toml` content (verbatim)

```toml
[project]
name = "{source_name}"
version = "0.0.0"
requires-python = ">=3.12"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Empirically validated — see §4 OQ-A and OQ-B.

### 3.5 Integration call site in `propagator.py`

Insert ONE call between `propagator.py:184` (post-checkout_branch) and
`propagator.py:189` (the `if classification.requires_pyproject_change`
block). Concretely the new code lives just before the existing
`pyproject_changed = False` line at `propagator.py:188`:

```python
# After branch checkout, before pyproject rewrite + uv lock:
# stub any [tool.uv.sources] editable path entries inside the
# work_root so uv lock's relative-path resolution succeeds.
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

The fail-fast semantic mirrors every other error path in
`propagator.py:131-300` — every subprocess or parsing error becomes a
per-satellite `status="failed"` verdict via `fail(reason, ...)` per
the docstring at `propagator.py:99-101`.

### 3.6 Idempotency guarantees

The function is RE-RUNNABLE in the same `work_root` without side
effects:

- If `stub_dir/pyproject.toml` already exists, `_write_stub_pyproject`
  is a no-op and the entry is recorded as `skipped=True`,
  `skip_reason="stub already present"`.
- The stub-path is computed by `(repo_dir / path).resolve()`. Two
  satellites in the same work_root may declare the SAME relative path
  (e.g. both `autom8y-asana` and `autom8y-data` declare
  `autom8y-api-schemas = { path = "../autom8y-api-schemas", ...
  }`). The first satellite to be processed creates the stub; the
  second sees it as already-present and skips. Both satellites'
  subsequent `uv lock` invocations see the same stub. This is the
  expected concurrency model — fan-out is per-satellite via
  `parallel.py`'s `propagate_all_sync`, but the stub directory is a
  shared resource within the work_root.
- Atomic write is NOT required at the satellite-fan-out level
  because each satellite's `[tool.uv.sources]` resolves to paths
  outside its own clone (they live in `work_root` peers, not inside
  `repo_dir`). However, two satellites' stub entries for the same
  resolved-path are content-identical (same name, same version
  `0.0.0`), so a write race is benign.

## §4 Resolved Design Decisions

### OQ-A — Minimum viable stub shape

**RESOLVED via empirical probe.** Run on autom8y-asana session repo
2026-04-29 with `uv 0.9.7`:

A stub containing ONLY `pyproject.toml` with a minimal `[project]`
table (name, version, requires-python, plus `[build-system]` for
PEP-517 compliance) and NO `src/` directory and NO `__init__.py`
SUCCEEDS at `uv lock`. Empirical evidence:

- Probe at `/tmp/uvprobe-source-stub/`: stub `pyproject.toml`
  with no Python sources; satellite `pyproject.toml` declaring
  `[tool.uv.sources] fake-sibling-pkg = { path = "../sibling-stub",
  editable = true }`. `uv lock` exit 0; `uv.lock` produced;
  resolved-package count 2 in 21ms.

This confirms the spike's hypothesis at `SPIKE...md:225-232`. The
api-schemas-stub action's importable-module surface
(`action.yml:33-102`) is required by `uv sync`, NOT by `uv lock`.
The propagator runs `uv lock` only.

**Decision**: Minimum viable stub = `pyproject.toml` with
`[project]` (name, version, requires-python) + `[build-system]`
(hatchling). No Python sources.

**Operational consequence**: The stub-symbol-surface drift risk noted
in `SPIKE...md:225-232` does NOT apply to this design. New symbols
consumed by satellites do NOT require stub edits, because the stubs
are never imported.

### OQ-B — Sibling-version pinning under CI

Strategies considered:

- (a) Hardcode `version = "0.0.0"`.
- (b) Read from CodeArtifact at stub-creation time.
- (c) Read from sibling repo's `pyproject.toml` via additional clone.
- (d) Pin from a manifest checked into the propagator.

**RESOLVED: (a) Hardcode `version = "0.0.0"`.** Empirical evidence:

- Probe at `/tmp/uvprobe-floor/`: stub at `version = "0.0.0"`
  satisfies satellite floor declaration `sib>=1.9.0` because uv's
  editable path source RESOLUTION OVERRIDES PEP 440 specifier
  matching when `[tool.uv.sources]` declares `path = ...`. The
  resulting `uv.lock` records `source = { editable = "../sib" }`
  with `version = "0.0.0"` and treats the floor as satisfied via
  the editable override.
- This is consistent with the precedent at `action.yml:7` which
  pins `version = "1.6.0"` purely as a floor-satisfaction value;
  the importable module surface, not the version, was the load-bearing
  contract there. The version field is ceremonial under uv's
  editable-source semantics.

**Justification vs. alternatives**:

- (b) CodeArtifact reads add a network call inside the per-satellite
  loop, eat into the 55s `DEFAULT_PER_SATELLITE_TIMEOUT_SECONDS`
  budget at `__init__.py:35`, and require auth scoping that the
  propagator does not currently hold (the GitHub App token at
  `sdk-publish-v2.yml:1027` is GitHub-only).
- (c) Cloning two extra repos (`autom8y` + `autom8y-api-schemas`)
  per fan-out adds ~5–10s and grows the GitHub App token's repo
  scope — equivalent to Option C in the spike, which the spike
  rejected as "heavier".
- (d) A pinned manifest in the propagator drifts. Whoever lands a
  sibling repo bump must remember to update the manifest; this is
  exactly the "manual gate" the propagator exists to eliminate.

**Decision**: Stub `version = "0.0.0"`. This is intentional.

### OQ-C — Source-type discrimination

Stubbed: entries whose value is an inline-table containing a `path`
key, regardless of `editable` flag presence. Concretely:

```toml
[tool.uv.sources]
foo = { path = "../foo" }                       # STUBBED
bar = { path = "../bar", editable = true }      # STUBBED (canonical satellite shape)
baz = { path = "../baz", editable = false }     # STUBBED (defensive — uv treats path-only as resolution-bearing)
qux = { git = "https://github.com/x/qux" }      # LEFT UNTOUCHED
quux = { url = "https://example.com/quux.zip" } # LEFT UNTOUCHED
quuux = { index = "autom8y" }                   # LEFT UNTOUCHED (CodeArtifact)
```

The discriminator: `"path" in entry AND entry.get("git") is None AND
entry.get("url") is None AND entry.get("index") is None`. This matches
the handoff acceptance criterion at
`HANDOFF...md:115` ("No regression in existing propagator behavior
for sources that are NOT editable path references (git URLs, registry
indices)").

Verified against all 5 satellite `[tool.uv.sources]` shapes
(`autom8y-asana/pyproject.toml:326-331`,
`autom8y-data/pyproject.toml:354-356`,
`autom8y-scheduling/pyproject.toml:184-186`,
`autom8y-sms/pyproject.toml:197-202`,
`autom8y-ads/pyproject.toml:174-185`): all path-source entries today
use `editable = true`; none use git or url. No production satellite
will be affected by the `editable=false` defensive case, but the rule
is correct for it.

### OQ-D — Extras + markers preservation

Empirically validated: extras and environment markers declared by the
satellite on a stubbed source are preserved through to the resulting
`uv.lock` because `uv lock` reads them from the satellite's
`pyproject.toml` `[project.dependencies]`, NOT from the source itself.

Probe at `/tmp/uvprobe-extras-markers/` 2026-04-29:

- Satellite declares `'sib-b[fastapi]; python_version >= "3.12"'` in
  `[project.dependencies]`.
- Stub for `sib-b` declares `[project.optional-dependencies] fastapi
  = []`.
- Resulting `uv.lock`:
  `{ name = "sib-b", extras = ["fastapi"], marker = "python_full_version
  >= '3.12'", editable = "../sib-b" }`.

**Stub-side requirement**: when the satellite consumes an extra of a
stubbed source, the stub's `pyproject.toml` SHOULD declare the extra
in `[project.optional-dependencies]` with an empty deps list. uv emits
a warning `does not have an extra named X` if absent, but `uv lock`
still succeeds (probe at `/tmp/uvprobe-missing-extra/`: exit 0 with
warning). This makes extras-declaration a CORRECTNESS-OF-DIFF concern,
not a CORRECTNESS-OF-RESOLUTION concern. The Mauritian-warning-free
stub is preferred.

**Decision**: Walk the satellite's `[project.dependencies]` and
`[project.optional-dependencies]` strings; extract any
`name[extra-list]` patterns where `name` is a stubbed source; render
those extras in the stub's
`[project.optional-dependencies]` with empty dep lists. Use the
existing requirement-parser at `lockfile_updater.py:129-137`
(`_REQUIREMENT_RE`) to extract the extras blocks. This adds ~15 LOC
to the stub renderer.

If extras-extraction fails or the requirement is unparseable, fall
back to a stub with NO `[project.optional-dependencies]` (the
warning is acceptable; resolution still succeeds).

### OQ-E — Failure mode

Existing failure semantic in `propagator.py`: every error path becomes
a per-satellite `status="failed"` SatelliteResult via the `fail(reason,
...)` helper at `propagator.py:107-118`. The fan-out aggregator rolls
this into the overall verdict.

`SourceStubError` follows that pattern. The propagator catches it and
returns `fail(f"source stub failed: {exc}", ...)` — same shape as
`fail("clone failed: ...")` at `propagator.py:134`,
`fail("constraint detection failed: ...")` at `propagator.py:148`,
`fail("uv lock failed: ...")` at `propagator.py:206`. The other 4
satellites continue propagating; the failed satellite shows up in the
verdict JSON for visibility.

This is fail-fast for the affected satellite, fail-soft for the
fan-out. Matches the docstring contract at `propagator.py:99-100`:
"NEVER raises — every error path becomes a `status='failed'`
verdict."

## §5 Test Strategy

Test module: `autom8y/tools/lockfile-propagator/tests/test_source_stub.py`.
Style mirrors `tests/test_lockfile_updater.py:1-80`: real tmpdir
pyproject.toml files, no mocks; the propagator's `make_satellite_skeleton`
helper at `tests/conftest.py:78-84` is reused via fixture composition.

### 5.1 Unit tests

| ID | Test name | Scenario | Expected |
|----|-----------|----------|----------|
| T-A | `test_single_editable_path_source` | Satellite declares one `{ path = "../x", editable = true }`; stub created | `stub_path/pyproject.toml` exists with name "x", version "0.0.0"; `StubbedSource(skipped=False)` |
| T-B | `test_multiple_editable_path_sources` | Satellite declares 2 path sources; stubs created | Two `pyproject.toml` files written; both records `skipped=False` |
| T-C | `test_extras_and_markers_preserved` | Satellite declares `foo[bar]; python_version >= "3.12"` with `foo = { path = "../foo", editable = true }` | Stub declares `[project.optional-dependencies] bar = []`; `uv lock` succeeds without warning (validated by running real `uv lock` against the produced stub in tmpdir) |
| T-D | `test_git_sources_left_untouched` | Satellite declares `{ git = "https://..." }` entry; no path sources | Returns empty `[StubbedSource]` list; no filesystem writes |
| T-D2 | `test_index_sources_left_untouched` | Satellite declares `{ index = "autom8y" }` entries (real-fleet-shape — most autom8y entries are index-based) | Index entries SKIPPED; only path entries stubbed |
| T-E | `test_malformed_pyproject_raises` | `pyproject.toml` is not valid TOML | `SourceStubError` raised with TOMLDecodeError context |
| T-E2 | `test_missing_pyproject_raises` | `repo_dir/pyproject.toml` does not exist | `SourceStubError` raised |
| T-F | `test_idempotency_rerun_same_work_root` | Call `stub_editable_path_sources` twice with the same args | Second call records all entries as `skipped=True`, `skip_reason="stub already present"`; no filesystem mutation between calls (mtime-stable) |
| T-F2 | `test_idempotency_two_satellites_same_path` | Two satellite skeletons in the same work_root, both declaring the same `../autom8y-api-schemas` path | First satellite creates stub; second satellite sees `skipped=True`; both downstream `uv lock` invocations succeed |
| T-G | `test_path_only_no_editable_flag_stubbed` | Satellite declares `{ path = "../x" }` without `editable` | Defensive: still stubbed |

### 5.2 Integration test reproducing the autom8y-asana failure mode

`test_integration_autom8y_asana_failure_mode` (in
`tests/test_source_stub.py` or a new `tests/test_integration_propagator.py`):

1. Set up a tmpdir work_root.
2. Create a satellite skeleton at `work_root/autom8y-asana/` with
   `pyproject.toml` declaring two editable path sources mirroring the
   real shape at `autom8y-asana/pyproject.toml:328,331`:
   - `autom8y-api-schemas = { path = "../autom8y-api-schemas",
     editable = true }`
   - `autom8y-client-sdk = { path =
     "../autom8y/sdks/python/autom8y-client-sdk", editable = true }`
3. Add `autom8y-api-schemas>=1.9.0` and
   `autom8y-client-sdk>=3.0.0` to `[project.dependencies]`.
4. Pre-stub-call: assert `uv lock` (via
   `subprocess.run(["uv", "lock"], cwd=satellite_dir)`) FAILS with
   `Distribution not found at: file:///...autom8y-api-schemas`.
5. Call `stub_editable_path_sources(repo_dir=satellite_dir,
   work_root=work_root)`.
6. Post-stub-call: assert `uv lock` SUCCEEDS (exit 0).
7. Inspect `uv.lock`: assert it contains
   `source = { editable = "../autom8y-api-schemas" }` for the
   stubbed packages.

This test requires `uv` available on `$PATH`. Mark with
`@pytest.mark.skipif(shutil.which("uv") is None, ...)` to keep
hermetic-CI-without-uv runners green.

### 5.3 Test for `propagator.propagate_to_satellite` integration

Add a single test to `tests/test_propagator.py`:

`test_path_sources_stubbed_before_uv_lock_runs` — uses the existing
`FakeUvRunner` at `tests/conftest.py:244-283` (records every
`upgrade_package` call); registers a satellite skeleton whose
`pyproject.toml` declares an editable path source; asserts that
before `FakeUvRunner.upgrade_package` is invoked, the stub directory
exists at the resolved path. This locks the call-ordering invariant
("stub before lock") that §3.5 specifies.

### 5.4 Test plan summary mapping to handoff acceptance

| Handoff acceptance | Test(s) |
|--------------------|---------|
| WS-2 (a) single editable path source | T-A |
| WS-2 (b) multiple editable path sources | T-B |
| WS-2 (c) extras + markers preserved | T-C |
| WS-2 (d) sources with `git = ...` left untouched | T-D, T-D2 |
| WS-3 integration test reproducing autom8y-asana failure | §5.2 integration test |
| Procession-level: 5/5 satellites green on Notify | WS-4 (CI validation, post-merge) |
| Procession-level: no regression on git/index sources | T-D, T-D2 |
| Procession-level: per-satellite SLA respected | §6 deadline-budget analysis |

## §6 Deadline-Budget Impact Analysis

`DEFAULT_DEADLINE_SECONDS = 60`,
`DEFAULT_PER_SATELLITE_TIMEOUT_SECONDS = 55`
(`__init__.py:30,35`).

Stub creation is filesystem-only:

- Per-source: 1× TOML parse of `pyproject.toml` (already in memory
  via `tomllib.loads` if we share with `lockfile_updater.py:154`),
  N× `os.makedirs(...,  exist_ok=True)` calls, N× `Path.write_text`
  calls. Each is single-digit milliseconds on local filesystem.

- 5 satellites × max 2 sources each (autom8y-asana and autom8y-ads
  have 2; the others have 1) = 10 sources max, 7 in practice
  (2+1+1+1+2). Real-fleet shape per §4 OQ-C verification.

Worst-case wall-clock: <100ms per satellite for stub creation.
Comfortably inside the 55s per-satellite budget. The probe above
showed `uv lock` completing in 21ms on the 2-package case, suggesting
the overall per-satellite path remains sub-second on the GitHub
Actions runner.

No deadline change at `sdk-publish-v2.yml:1077` is required.

## §7 Risk Register & Rollback Path

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-1 | uv lock semantics change in a future uv release such that editable sources stop overriding floor specifiers | Low | High | Pin uv version at `sdk-publish-v2.yml:1010` (already pinned to 0.10.8); upgrades are gated. T-C integration test catches semantic regressions. |
| R-2 | A future satellite adds a source that consumes Python module surface (not just resolution) | Low | Medium | Stubs would silently produce a working `uv.lock` but `uv sync` in the satellite's CI would fail. Mitigation: T-D documents the "lock-only" boundary; satellite CI failures are surfaced via the existing satellite-CI repository_dispatch path at `sdk-publish-v2.yml:1029-1049`. |
| R-3 | Two satellites declare the SAME relative path with DIFFERENT versions | Very Low | Low | Stubs are content-identical at version `0.0.0`; race is benign per §3.6. |
| R-4 | Stub creation succeeds but uv lock fails for unrelated reasons; the failure surfaces under the "uv lock failed" path at `propagator.py:206`, masking the true cause | Low | Low | The stub log line records `[StubbedSource]` count for visibility. The verdict JSON consumed by the workflow summary at `sdk-publish-v2.yml:1117-1128` already separates failure verbiage. |
| R-5 | Symbol-surface drift between stub and real schema | N/A | N/A | Eliminated by §4 OQ-A (no symbols in stub). Listed for explicit-acknowledgment per ADR Consequences. |

### Rollback path

The reversibility property is single-call-site removal. To revert:

1. Delete the new import + call block at `propagator.py:188`
   (the §3.5 insertion).
2. Optionally delete `source_stub.py` and `tests/test_source_stub.py`.
3. `uv lock` against the propagator's own clone resumes failing in
   the exact way it does today; the satellite-clone-altitude
   resolution returns to its prior broken-state.

No state mutations outside `/tmp/lockfile-propagator-XXX/` occur
during normal operation; nothing persists post-run; rollback is
literal code deletion.

## §8 Acceptance Traceability

| Acceptance criterion (from HANDOFF) | TDD section + test |
|--------------------------------------|--------------------|
| All 5 satellites' Notify Satellite Repos step succeeds (`HANDOFF...md:113`) | §5.2 integration test + WS-4 post-merge CI validation |
| Lockfile-bump PRs auto-opened in each satellite (`HANDOFF...md:114`) | Existing propagator commit/push/PR flow at `propagator.py:241-300` is unchanged; §3.5 hook adds NO mutation to the post-stub flow |
| Per-satellite SLA respected (60s deadline) (`HANDOFF...md:115`) | §6 deadline-budget analysis |
| No regression for git URLs / registry indices (`HANDOFF...md:116`) | T-D, T-D2 |
| Works against autom8y-config AND any other SDK (`HANDOFF...md:117`) | Stubbing is SDK-agnostic; the `[tool.uv.sources]` parsing logic does not branch on SDK identity |
| WS-1: read+understand current architecture | §2 architecture summary (this section) |
| WS-2: implement source stubbing helper | §3 component design |
| WS-2 (a) single editable path source | T-A |
| WS-2 (b) multiple editable path sources | T-B |
| WS-2 (c) extras + markers preserved | T-C |
| WS-2 (d) git sources left untouched | T-D |
| WS-3: wire stubbing into propagator main loop | §3.5 integration call site + §5.3 ordering test |
| WS-4: CI validation (5/5 satellites green) | Post-merge SDK publish run; tracked in verification attestation per `HANDOFF...md:140` |
| WS-5: cleanup + documentation | §9 DEFER-POST-IMPL note |

## §9 Open Questions / Out of Scope

### DEFER-POST-IMPL

- **WS-5 docs and scar-tissue entry** (`HANDOFF...md:88-91`) — text
  authoring is bounded sprint work; tracked as part of the
  implementation PR or a follow-up cleanup PR per
  `HANDOFF...md:92`.

### DEFER-FOLLOWUP

- **Stub-policy consolidation between api-schemas-stub action and
  source_stub.py** (`SPIKE...md:391-396`) — the api-schemas-stub
  action remains in place for the publishing-job's own `uv sync`
  needs (different altitude). A future ADR may consolidate when
  `autom8y-api-schemas` graduates to CodeArtifact. Out of scope for
  this initiative per HANDOFF authority boundary.
- **OQ-3 deadline-seconds raise** (`SPIKE...md:411-415`) — not
  needed under §6 analysis; revisit only if a future satellite adds
  6+ editable sources.
- **OQ-4 cross-monorepo consolidation** (`SPIKE...md:416-420`) —
  architectural ADR candidate; out of scope.
- **OQ-5 SQ-3 consumer-gate redesign** (`SPIKE...md:421-422`) —
  parent-handoff-orthogonal; out of scope.

### Out of scope (authority boundary)

- Modifying any satellite `pyproject.toml` (`HANDOFF...md:128`).
- Republishing autom8y-config 2.0.0/2.0.1/2.0.2
  (`HANDOFF...md:129`).
- Bypassing branch protection on autom8y/main (`HANDOFF...md:130`).
- Touching alarms / AWS resources (`HANDOFF...md:132`).
- Modifying the api-schemas-stub action (orthogonal).
- Widening the `[tool.uv.sources]` schema.

### No STOP conditions hit

The empirical probes resolved OQ-A in favor of viability (uv lock
does NOT require importable modules); the spike's structural claims
about the propagator architecture were verified file:line by reading
the source. Recommendation: PROCEED to principal-engineer.
