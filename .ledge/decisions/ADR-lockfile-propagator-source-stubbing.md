---
schema_version: "1.0"
type: decision
slug: lockfile-propagator-source-stubbing
title: "ADR — Lockfile-Propagator In-Tool Source Stubbing"
date: 2026-04-29
status: proposed
deciders: 10x-dev rite (architect)
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y
target_module: autom8y/tools/lockfile-propagator
parent_artifacts:
  spike: .sos/wip/SPIKE-lockfile-propagator-tooling-fix.md
  handoff: .ledge/handoffs/HANDOFF-sre-to-10x-dev-lockfile-propagator-fix-2026-04-28.md
  tdd: .ledge/specs/lockfile-propagator-source-stubbing.tdd.md
authority: "10x-dev rite per HANDOFF authority boundary; spike Option A recommended"
disciplines:
  - option-enumeration-discipline
  - structural-verification-receipt
  - authoritative-source-integrity
---

# ADR: Lockfile-Propagator In-Tool Source Stubbing

## Status

**Proposed.** Will flip to **accepted** when the implementation lands
and the post-merge `sdk-publish-v2.yml` workflow run records 5/5
satellites green at the `Notify Satellite Repos` step.

## Context

The `autom8y/tools/lockfile-propagator/` Python tool, invoked by
`sdk-publish-v2.yml:1051-1087` after every SDK publish, fails on the
`Notify Satellite Repos` step for 5/5 satellites (autom8y-asana,
autom8y-data, autom8y-scheduling, autom8y-sms, autom8y-ads).
Failure mode: each satellite's `pyproject.toml` declares
`[tool.uv.sources]` editable path entries of the form
`{ path = "../X", editable = true }` (verified at
`autom8y-asana/pyproject.toml:326-331` and the four sibling satellite
files). The propagator clones each satellite into
`/tmp/lockfile-propagator-XXXXXXXX/<satellite>/` via
`SubprocessGitOps.clone_shallow` (`repo_clone.py:99-125`), then
invokes `uv lock --upgrade-package <sdk>==<version>` with
`cwd=repo_dir` (`lockfile_updater.py:96-105`). uv resolves
`path = "../X"` relative to the satellite's clone, but `..` from
inside `/tmp/lockfile-propagator-XXX/<satellite>/` points back to the
work_root which contains only the OTHER satellite clones — not the
sibling repos `autom8y-api-schemas` or `autom8y/sdks/python/...` that
exist on the developer's machine. uv emits `error: Distribution not
found at: file:///tmp/...`, the propagator wraps it as
`LockfileError`, and the per-satellite verdict becomes
`status="failed"`.

The failure was empirically observed in workflow runs `25052186961`
(autom8y-config 2.0.1) and `25062121802` (autom8y-config 2.0.2). The
SRE rite produced a 449-line spike
(`.sos/wip/SPIKE-lockfile-propagator-tooling-fix.md`) that enumerated
8 candidate fixes and recommended Option A (in-tool source stubbing).
The spike's recommendation was accepted at handoff time
(`.ledge/handoffs/HANDOFF-sre-to-10x-dev-lockfile-propagator-fix-2026-04-28.md`).

This ADR records the architectural decision; the TDD at
`.ledge/specs/lockfile-propagator-source-stubbing.tdd.md` records
the implementation design.

## Decision

Inside the lockfile-propagator tool, after each satellite's clone is
materialized and before `uv lock` is invoked, parse the satellite's
`[tool.uv.sources]` table and create minimal stub packages — each
consisting of a single `pyproject.toml` with a `[project]` table —
at the resolved relative-path locations inside the work_root.

Specifically:

1. New module `autom8y/tools/lockfile-propagator/src/lockfile_propagator/source_stub.py`
   exporting `stub_editable_path_sources(repo_dir, work_root) ->
   list[StubbedSource]`.
2. Single integration call in `propagator.py` between the existing
   `checkout_branch` step (`propagator.py:182`) and the existing
   `pyproject_changed = False` line (`propagator.py:188`).
3. Stubs are written as `pyproject.toml`-only directories (no
   importable Python modules). The minimal `[project]` table
   declares `name`, `version = "0.0.0"`, `requires-python =
   ">=3.12"`, and a `[build-system]` block (hatchling).
4. Only entries with shape `{ path = ... }` (with or without
   `editable = true`) are stubbed. Entries with `git = ...`,
   `url = ...`, or `index = ...` are LEFT UNTOUCHED.
5. Failure to stub raises `SourceStubError`, which the propagator
   converts into a per-satellite `status="failed"` verdict via the
   existing `fail(reason, ...)` helper (`propagator.py:107-118`).

This extends the precedent established by the in-repo composite
action `.github/actions/api-schemas-stub/action.yml` (which stubs at
publish-job altitude) downward to sub-clone altitude, where it
solves the propagator's specific failure surface.

## Consequences

### Positive

- **Smallest blast radius**: only the propagator tool changes. Zero
  satellite changes, zero workflow changes, zero SDK changes.
- **High reversibility**: removing the new module + its single call
  site fully reverts behavior to today's broken state. No committed
  state mutations during normal operation; stubs live in
  `tempfile.TemporaryDirectory` (`cli.py:229`) and are GC'd with
  the work_root.
- **Dev experience preserved**: developers continue using
  `path = "../X"` editable sources locally; the propagator becomes
  invisible to them.
- **Within deadline budget**: stub creation is filesystem-only,
  sub-second per satellite — well within the
  `DEFAULT_PER_SATELLITE_TIMEOUT_SECONDS = 55` budget at
  `__init__.py:35`. Empirical probe measured `uv lock` against a
  stub at 21ms wall-clock.
- **Extends existing pattern**: the api-schemas-stub composite
  action already established the stub-the-resolution-target
  discipline; this decision applies the same discipline at a
  lower altitude.
- **OQ-A symbol-surface drift risk eliminated**: empirically
  validated that `uv lock` does NOT require importable modules in
  the stub (probe at `/tmp/uvprobe-source-stub/`, exit 0). The
  api-schemas-stub action declares Python modules because `uv
  sync` imports during install; the propagator runs `uv lock` only.
  Future symbol additions at the satellites do NOT impose stub
  edits at the propagator.

### Negative

- **Drift risk between this stub and the api-schemas-stub action**:
  there are now two distinct stub mechanisms in the autom8y
  monorepo. Each stubs `autom8y-api-schemas` for a different
  altitude. If `autom8y-api-schemas` graduates to CodeArtifact in
  the future, both stubs need to be reconsidered. The TDD
  records this as `DEFER-FOLLOWUP` (consolidation ADR candidate).
- **Pattern multiplication if more SDKs adopt editable cross-repo
  sources**: every new editable path source declared in any
  satellite's `[tool.uv.sources]` will be auto-stubbed by the
  propagator. This is intended behavior, but it makes the
  propagator implicitly responsible for the cross-repo source
  topology in a way it isn't today. Mitigation: the discriminator
  at TDD §4 OQ-C is a closed-form rule (path-source vs.
  git/url/index); no human judgment required.
- **`version = "0.0.0"` in stubs**: the resulting `uv.lock` will
  encode `editable = "../X"` source records; the version field is
  ceremonial under uv's editable-source semantics (verified via
  `/tmp/uvprobe-floor/` probe, where `>=1.9.0` floor was satisfied
  by a `0.0.0` editable stub). Reviewers reading lockfile diffs
  may need a one-line orientation comment in the propagator's PR
  body.
- **Failure-mode masking risk** (low): if `uv lock` fails for a
  reason unrelated to source resolution after a successful stub
  step, the existing failure verbiage at `propagator.py:206`
  ("uv lock failed: ...") may not surface that the stubs were in
  fact present. The TDD §7 R-4 records this; mitigation is the
  stub log line in the verdict JSON.

### Neutral

- **Test surface grows by ~10 unit tests + 1 integration test**
  (TDD §5). The integration test requires `uv` on `$PATH`; gated
  by `pytest.mark.skipif`. Existing test fixture style at
  `tests/conftest.py:78-84` is reused.
- **Documentation footprint**: WS-5 of the handoff schedules a
  `.know/scar-tissue.md` entry and a brief README note. Not
  load-bearing on the architectural decision.

## Alternatives Considered

The spike enumerated 8 options at recommendation altitude. This ADR
acknowledges them; the spike's analysis at
`.sos/wip/SPIKE-lockfile-propagator-tooling-fix.md:177-313` is
canonical and is not reproduced here.

### Option A — In-tool source stubbing (RECOMMENDED, ADOPTED)

The decision recorded in this ADR. Spike §5.1 + §6 cover the
detailed rationale. Selected on the basis of (1) smallest blast
radius, (2) high reversibility, (3) dev-experience preservation,
(4) precedent fit with api-schemas-stub, (5) within deadline
budget. Empirical probes (TDD §4 OQ-A, OQ-B, OQ-D) closed the
remaining open questions in favor of viability.

### Option B — Rewrite path = "../X" to absolute paths

Spike §5.2. Loses on lockfile fidelity: rewriting before `uv lock`
produces a lockfile keyed against absolute paths that don't match
the satellite's checked-in version, requiring a revert step. Option
A avoids this branch entirely — uv resolves via the stub but
records the relative-path source in `uv.lock`.

### Option C — Clone sibling repos into work_root

Spike §5.3. Heavier: two extra clones per satellite × N SDKs
publishes; large repos at `--depth 1` are still costly; the
GitHub App token at `sdk-publish-v2.yml:1027` would need
`autom8y` and `autom8y-api-schemas` added to its scope.
Considered as fallback if Option A's stub-surface drift becomes
operationally untenable; OQ-A's empirical resolution makes this
unlikely.

### Option D — `uv lock --no-sources`

Spike §5.4. Risky semantic change: produces a lockfile that
diverges from local-dev expectations (developers' local
`uv lock` honors sources; `--no-sources` does not). The propagator
would propose lockfile diffs that look wrong to reviewers.

### Option E — Convert satellites to git+ssh sources

Spike §5.5. Rejected: 5 satellite PRs to change `pyproject.toml`,
slows local dev (network fetches on every `uv sync`), adds auth
complexity. Fix-cost greatly exceeds problem-cost.

### Option F — Replace propagator with renovate/dependabot

Spike §5.6. Rejected: out of scope. The propagator implements
custom D7 semantics (constraint detection, bump classification,
MAJOR-bump pyproject rewrites at `propagator.py:189-197`).
Reproducing in renovate/dependabot is multi-week with regression
risk.

### Option G — Accept failure; document workaround

Spike §5.7. Anti-pattern; defeats the throughline of automated
lockfile propagation. Symlink-based developer workaround was
validated but is not a fix.

### Option H — Run uv lock from a stable parent dir mirroring the
developer layout

Spike §5.8. Rejected: requires either developer-ergonomic-coupled
CI layout (fragile) or per-runner-job filesystem prep (effort
approaches Option C without its benefits).

## Provenance

- **Spike**: `.sos/wip/SPIKE-lockfile-propagator-tooling-fix.md`
  (449 lines, dated 2026-04-29, status complete; §5 option matrix,
  §6 recommendation, §9 file:line anchors).
- **Handoff**: `.ledge/handoffs/HANDOFF-sre-to-10x-dev-lockfile-propagator-fix-2026-04-28.md`
  (148 lines, dated 2026-04-28; SRE→10x-dev cross-rite handoff
  granting authority to implement Option A).
- **TDD**: `.ledge/specs/lockfile-propagator-source-stubbing.tdd.md`
  (this ADR's implementation companion).
- **Failure evidence**: workflow runs `25052186961` and
  `25062121802` (verbatim error logs verified per
  `SPIKE...md:127-129`).
- **Tool source verified at**:
  - `autom8y/tools/lockfile-propagator/src/lockfile_propagator/propagator.py`
    (orchestration; uv lock invocation at line 204)
  - `autom8y/tools/lockfile-propagator/src/lockfile_propagator/repo_clone.py`
    (`SubprocessGitOps.clone_shallow:99-125`)
  - `autom8y/tools/lockfile-propagator/src/lockfile_propagator/lockfile_updater.py`
    (`SubprocessUvLockRunner.upgrade_package:85-117`)
  - `autom8y/tools/lockfile-propagator/src/lockfile_propagator/cli.py`
    (`_WorkRootContext:218-238`)
  - `autom8y/tools/lockfile-propagator/src/lockfile_propagator/__init__.py`
    (`DEFAULT_DEADLINE_SECONDS=60`,
    `DEFAULT_PER_SATELLITE_TIMEOUT_SECONDS=55:30-35`)
- **Workflow invocation site**:
  `autom8y/.github/workflows/sdk-publish-v2.yml:971-1130`.
- **Precedent stub pattern**:
  `autom8y/.github/actions/api-schemas-stub/action.yml:1-103`.
- **Empirical probes** (run 2026-04-29 with `uv 0.9.7`):
  - `/tmp/uvprobe-source-stub/` — minimal stub viability (OQ-A).
    Exit 0; no Python sources required.
  - `/tmp/uvprobe-extras-markers/` — extras + markers preservation
    (OQ-D). Exit 0; `uv.lock` records extras and markers.
  - `/tmp/uvprobe-missing-extra/` — undeclared extra warning
    semantics. Exit 0 with warning (resolution succeeds).
  - `/tmp/uvprobe-floor/` — version-floor override semantics
    (OQ-B). Exit 0; editable source overrides PEP 440 floor.

## Reversibility Property

This is a TWO-WAY door. Rollback path: delete the
`source_stub.py` module + the integration call block at
`propagator.py:188`. No state mutations outside the per-run
`tempfile.TemporaryDirectory` (`cli.py:229`); nothing persists
post-run. The decision can be reversed by code deletion.
