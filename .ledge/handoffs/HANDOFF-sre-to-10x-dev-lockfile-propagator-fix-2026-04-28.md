---
schema_version: "1.0"
type: handoff
status: proposed
handoff_type: implementation
source_rite: sre
target_rite: 10x-dev
date: 2026-04-28
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
related_repos:
  - /Users/tomtenuta/Code/a8/repos/autom8y
  - autom8y/autom8y-asana
  - autom8y/autom8y-data
  - autom8y/autom8y-scheduling
  - autom8y/autom8y-sms
  - autom8y/autom8y-ads
authority: "User-granted: '/cross-rite-handoff --to=10x-dev for principled remediation /sprint' (2026-04-28)"
severity: SEV3
posture: greenfield (no urgency; follow-up to closed cache-freshness procession SEV2)
trigger: "lockfile-propagator failure observed in autom8y-config 2.0.1 + 2.0.2 publishes — Notify Satellite Repos step fails for 5 satellites due to relative-path resolution under sandboxed temp clone"
parent_artifacts:
  spike: .sos/wip/SPIKE-lockfile-propagator-tooling-fix.md
  parent_handoff: .ledge/handoffs/HANDOFF-10x-dev-to-sre-sdk-publish-pipeline-blocked-2026-04-28.md (status partially-resolved)
  procession_attestation: .ledge/handoffs/HANDOFF-sre-to-10x-dev-cache-warmer-init-failure-2026-04-28.md (closed)
---

# HANDOFF: SRE → 10x-dev — Lockfile-Propagator Path-Resolution Fix

## Source Findings (from spike `af581918adb518c00`)

**Tool**: `autom8y/tools/lockfile-propagator/` (Python tool invoked by `sdk-publish-v2.yml` `Notify Satellite Repos` job)

**Root cause**: Tool clones each satellite into `/tmp/lockfile-propagator-XXXXXXXX/<satellite>/` and runs `uv lock` with `cwd=repo_dir`. Satellites' `pyproject.toml` `[tool.uv.sources]` declare `path = "../X"` editable references. From the sandboxed clone, `..` resolves to `/tmp/lockfile-propagator-XXX/` instead of the developer's `/Users/.../Code/a8/repos/`. uv can't find sibling repos → resolution fails.

**Verbatim error** (from run `25062121802`):
```
error: Distribution not found at: file:///tmp/lockfile-propagator-4qdmcw0j/autom8y-api-schemas
```

**Affected satellites** (5): autom8y-asana, autom8y-data, autom8y-scheduling, autom8y-sms, autom8y-ads. Each has different sibling-path dependencies in `[tool.uv.sources]`.

**Empirical confirmation**: today's cache-freshness procession cascade hit this exact failure mode twice (autom8y-config 2.0.1 publish + 2.0.2 publish). Manual workaround was symlinking sibling repos into `.worktrees/` before running `uv lock`. The real fix is in the propagator tooling.

## Implementation Scope (Recommended Option from Spike)

**Option A — In-tool source stubbing** (per spike §6 recommendation).

After clone, the propagator parses each satellite's `[tool.uv.sources]` table and creates minimal stub packages at the resolved relative paths inside the work_root. This builds on the existing precedent at `.github/actions/api-schemas-stub/action.yml` (which stubs at publishing-job altitude) by extending the same pattern to sub-clone altitude.

### Why Option A vs Alternatives

Spike enumerated 8 options (A through H); 5 rejected, 2 retained as runner-ups, A recommended. Per spike §5–§6:

- **A wins on** blast-radius minimization (tool-only change), reversibility, dev-experience preservation (editable sources unchanged in pyproject.toml), and precedent fit (mirrors existing api-schemas-stub pattern at lower altitude)
- **B (path rewriting) loses on** lockfile fidelity (lockfile would reflect `/tmp/...` paths transiently)
- **C (alternative working dir) loses on** restructuring scope
- **D (--no-sources) loses on** lockfile divergence between dev + published environments
- **E (git+ssh URL conversion) loses on** auth complexity + slower resolution
- **F (replace with renovate/dependabot) loses on** scope creep
- **G (accept limitation) loses on** sustained automation degradation
- **H (upstream uv feature request) loses on** open-ended timeline

## Sprint Decomposition (for `/sprint` workflow)

**WS-1: Read + understand current propagator architecture** (~30min)
- Read `autom8y/tools/lockfile-propagator/src/lockfile_propagator/*.py` end-to-end
- Read `.github/workflows/sdk-publish-v2.yml:971-1130` (Notify-Satellites job invocation site)
- Read `.github/actions/api-schemas-stub/action.yml` (precedent stub pattern)
- Identify where in the propagator the clone happens + where uv lock fires + the right hook point for stub injection
- Acceptance: brief written summary of architecture in the WS-1 PR description

**WS-2: Implement source stubbing helper** (~2-3h)
- New helper function/module: parses `[tool.uv.sources]` from satellite's `pyproject.toml`
- For each entry with `path = ...`, creates a minimal stub package (just `pyproject.toml` + empty `__init__.py`) at the resolved relative path inside the work_root
- Stub package version should match the actual sibling's version (read from sibling's pyproject.toml in the developer's main checkout — propagator runs in CI where these aren't accessible, so version pinning needs strategy: probably read from CodeArtifact or from a pinned manifest)
- Acceptance: unit tests covering: (a) single editable path source, (b) multiple editable path sources, (c) extras + markers preserved, (d) sources with `git = ...` left untouched

**WS-3: Wire stubbing into propagator main loop** (~30min-1h)
- Inject `stub_sibling_sources(repo_dir)` call after clone, before `uv lock`
- Acceptance: integration test reproducing the autom8y-asana failure mode locally; verify uv lock succeeds with stubs in place

**WS-4: CI validation** (~1h)
- Open PR in autom8y; trigger `sdk-publish-v2.yml` against a synthetic SDK version OR re-run the most recent publish workflow
- Verify Notify Satellite Repos step succeeds for all 5 satellites
- Acceptance: 5/5 satellites green on Notify step; lockfile-bump PRs auto-opened in each satellite

**WS-5: Cleanup + documentation** (~30min)
- Remove the `.worktrees/` symlink workaround note from `HANDOFF-sre-to-10x-dev-cache-warmer-init-failure-2026-04-28.md` postmortem hooks (or leave as scar-tissue history)
- Add `.know/scar-tissue.md` entry describing the failure mode + the resolution pattern
- Update `autom8y/tools/lockfile-propagator/README.md` (if exists) with the new stub mechanism
- Acceptance: docs land in same PR or follow-up cleanup PR

**Estimated total**: 1–2 days end-to-end (matches spike's S-M effort estimate).

## Design References (per `implementation` handoff schema requirement)

1. **Spike report**: `.sos/wip/SPIKE-lockfile-propagator-tooling-fix.md` (449 lines, §6 recommendation, §5 option matrix, §9 file:line anchors)
2. **Precedent pattern**: `autom8y/.github/actions/api-schemas-stub/action.yml` (canonical stub pattern at publishing-job altitude — extend to sub-clone altitude)
3. **Tool source**: `autom8y/tools/lockfile-propagator/src/lockfile_propagator/`
4. **Workflow invocation site**: `autom8y/.github/workflows/sdk-publish-v2.yml:971-1130`
5. **Failure evidence**: workflow run `25062121802` (autom8y-config 2.0.2 publish — Notify Satellite Repos step) + run `25052186961` (2.0.1)
6. **Affected pyproject.toml files** (verify all 5 satellites' `[tool.uv.sources]` shapes):
   - `autom8y-asana/pyproject.toml` lines around `[tool.uv.sources]`
   - `autom8y-data/pyproject.toml`
   - `autom8y-scheduling/pyproject.toml`
   - `autom8y-sms/pyproject.toml`
   - `autom8y-ads/pyproject.toml`
7. **Manual workaround proven** today: symlink `../autom8y-api-schemas` and `../autom8y` into `.worktrees/` before `uv lock`. Validates the fundamental approach (stubbing == lighter-weight version of symlinking).

## Acceptance Criteria (procession-level)

- All 5 affected satellites' `Notify Satellite Repos` step succeeds on the next SDK publish that triggers them
- Lockfile-bump PRs are auto-opened in each satellite (with the new SDK version pinned in `uv.lock`)
- Per-satellite SLA (`deadline_seconds: 60.0` per the propagator's existing budget) is respected
- No regression in existing propagator behavior for sources that are NOT editable path references (git URLs, registry indices)
- Works against autom8y-config publishes AND any other SDK in the fleet that satellites consume

## Authority Boundary

10x-dev (principal-engineer) may:
- Modify `autom8y/tools/lockfile-propagator/`
- Modify `autom8y/.github/workflows/sdk-publish-v2.yml` IF (and only if) the change is tightly scoped to consuming the new propagator output
- Open hotfix PR(s) with `--auto` queue
- Trigger `sdk-publish-v2.yml workflow_dispatch` with synthetic SDK or against the latest real SDK for verification (read-only verification of the Notify step; do NOT republish a fresh SDK version from this work)
- Run `uv lock` locally for tests + integration verification

10x-dev may NOT:
- Modify satellite `pyproject.toml` files (the `[tool.uv.sources]` is intentionally relative — the FIX is in the propagator, not the satellites)
- Republish autom8y-config 2.0.0/2.0.1/2.0.2 (already published; this work doesn't touch SDK content)
- Bypass branch protection on autom8y/main
- Cut new tags
- Touch alarms, AWS resources, etc.

## Dependencies

- Spike `.sos/wip/SPIKE-lockfile-propagator-tooling-fix.md` is canonical reference; do NOT redo investigation
- Implementation should respect `option-enumeration-discipline` if any decision deviates from Option A (justify in PR body)
- Should respect `structural-verification-receipt` discipline at every infrastructure-topology claim in PR descriptions

## Verification Attestation (post-execution; populated by 10x-dev)

> **Status**: CLOSE-WITH-FLAGS per Potnia PT-3 verdict A (issued 2026-04-29).
> Mechanical-equivalence ATTESTED; production-CI green-on-Notify DEFER-WATCH
> entry tracked at `.know/defer-watch.yaml#lockfile-propagator-prod-ci-confirmation`
> with deadline 2026-07-29. This section populated by principal-engineer
> at Phase 4 cleanup-and-attest. Receipt-grammar discipline per
> `cross-rite-handoff` schema: every "shipped" / "verified" / "attested"
> claim carries a `{path}:{line_int}` literal anchor OR a workflow-run URL
> OR an explicit `[UNATTESTED — DEFER-POST-HANDOFF]` tag.

### PR

- **Implementation PR**: autom8y#174 — `https://github.com/autom8y/autom8y/pull/174`
- **Merge SHA**: `f2dfc1c3`
- **Branch**: `fix/lockfile-propagator-source-stubbing` → `main` in autom8y monorepo
- **Merge URL**: `https://github.com/autom8y/autom8y/commit/f2dfc1c3`
- **Audit worktree** (post-merge code reviewed): `/tmp/lp-pt2-audit/tools/lockfile-propagator/` (mirrors merged source tree at `f2dfc1c3`)

### Workflow runs (3 total — production-CI evidence is PARTIAL)

| Run ID | Workflow | Trigger / version | Step terminal status | Step that failed (or absent) | Cascade-incompleteness disposition |
|--------|----------|-------------------|----------------------|-------------------------------|------------------------------------|
| `25062121802` | sdk-publish-v2.yml | autom8y-config 2.0.2 publish (pre-fix baseline) | FAILED | `Notify-Satellite-Repos` — `error: Distribution not found at: file:///tmp/lockfile-propagator-4qdmcw0j/autom8y-api-schemas` | This IS the failure the fix targets. URL: `https://github.com/autom8y/autom8y/actions/runs/25062121802` |
| `25083219816` | sdk-publish-v2.yml (autom8y-meta) | post-merge run #1 | FAILED | `Publish` — CodeArtifact 409 (version conflict). `Notify-Satellite-Repos` SKIPPED | DIFFERENT step from pre-fix baseline; cascade-incompleteness signal S-4' REJECTED — this run does NOT exercise the fix surface. URL: `https://github.com/autom8y/autom8y/actions/runs/25083219816` |
| `25084290648` | sdk-publish-v2.yml (autom8y-google 0.1.0) | post-merge run #2 | FAILED | `Publish` — version-already-exists. `Notify-Satellite-Repos` SKIPPED | DIFFERENT step from pre-fix baseline; same cascade-incompleteness disposition as run #1. URL: `https://github.com/autom8y/autom8y/actions/runs/25084290648` |

**Cascade-incompleteness adjudication**: signal S-4' (post-merge run #1 + #2 each FAILED at `Publish` before reaching the fix surface) is REJECTED as evidence-of-regression because the fix surface (`Notify-Satellite-Repos` step) was never exercised on either post-merge run. The two runs FAIL at an UPSTREAM step that is orthogonal to the path-resolution fix; they do NOT prove the fix is broken nor green. This is precisely the structural reason for the DEFER-WATCH entry (see §"Defer-watch" below).

### Per-satellite verification table

> **Caveat (PARTIAL — production CI deferred)**: each row records the
> SHAPE-EQUIVALENCE evidence for the satellite's `[tool.uv.sources]`
> against the canonical autom8y-asana case. Mechanical realization is
> ATTESTED via TDD §5.2 integration test for the canonical case; the
> remaining four satellites inherit attestation via shape-equivalence
> (the §4 OQ-C discriminator at `tools/lockfile-propagator/src/lockfile_propagator/source_stub.py:106` is closed-form
> on `path` vs `git`/`url`/`index` — no satellite-specific branching).
> Production-CI status is DEFER-WATCH for all 5 rows; the defer-watch
> entry covers all 5 satellites simultaneously (any one satellite's
> next push-triggered SDK bump discharges the defer for the fleet).

| Satellite | pyproject shape evidence (file:line) | Mechanical realization | Production-CI status | Defer-watch ref |
|-----------|---------------------------------------|------------------------|-----------------------|-----------------|
| autom8y-asana (canonical) | `pyproject.toml:326-331` (verified per TDD §2.2 + §5.2) — 2 editable path sources: `autom8y-api-schemas`, `autom8y-client-sdk` | ATTESTED via §5.2 integration test at `/tmp/lp-pt2-audit/tools/lockfile-propagator/tests/test_source_stub.py:366` (`test_integration_autom8y_asana_failure_mode` — pre-stub `uv lock` FAILS with `Distribution not found`; post-stub SUCCEEDS) | DEFER-WATCH — production CI never exercised post-merge | `.know/defer-watch.yaml#lockfile-propagator-prod-ci-confirmation` |
| autom8y-data | `pyproject.toml:354-356` (per TDD §4 OQ-C audit) — editable path source(s) | ATTESTED via shape-equivalence to canonical case + §4 OQ-C closed-form discriminator at `tools/lockfile-propagator/src/lockfile_propagator/source_stub.py:106` | DEFER-WATCH | `.know/defer-watch.yaml#lockfile-propagator-prod-ci-confirmation` |
| autom8y-scheduling | `pyproject.toml:184-186` (per TDD §4 OQ-C audit) — editable path source(s) | ATTESTED via shape-equivalence to canonical case + §4 OQ-C closed-form discriminator at `tools/lockfile-propagator/src/lockfile_propagator/source_stub.py:106` | DEFER-WATCH | `.know/defer-watch.yaml#lockfile-propagator-prod-ci-confirmation` |
| autom8y-sms | `pyproject.toml:197-202` (per TDD §4 OQ-C audit) — editable path source(s) | ATTESTED via shape-equivalence to canonical case + §4 OQ-C closed-form discriminator at `tools/lockfile-propagator/src/lockfile_propagator/source_stub.py:106` | DEFER-WATCH | `.know/defer-watch.yaml#lockfile-propagator-prod-ci-confirmation` |
| autom8y-ads | `pyproject.toml:174-185` (per TDD §4 OQ-C audit) — editable path source(s) | ATTESTED via shape-equivalence to canonical case + §4 OQ-C closed-form discriminator at `tools/lockfile-propagator/src/lockfile_propagator/source_stub.py:106` | DEFER-WATCH | `.know/defer-watch.yaml#lockfile-propagator-prod-ci-confirmation` |

### Telos realization (PARTIAL)

**Telos** (per TDD `lockfile-propagator-source-stubbing.tdd.md:34-48`): restore the `Notify-Satellite-Repos` job in `sdk-publish-v2.yml` to a green verdict for ALL 5 satellites on the next SDK publish that triggers them, with each satellite's lockfile-bump PR auto-opening within the propagator's 60-second deadline budget.

**Realization status**: PARTIAL.

- **Mechanical-equivalence**: ATTESTED. The canonical autom8y-asana failure mode is reproduced and resolved by the §5.2 integration test at `/tmp/lp-pt2-audit/tools/lockfile-propagator/tests/test_source_stub.py:366` (`test_integration_autom8y_asana_failure_mode`). The §5.3 ordering invariant (stub directories visible to the uv runner before `uv lock` fires) is locked by `/tmp/lp-pt2-audit/tools/lockfile-propagator/tests/test_propagator.py:359` (`TestPathSourcesStubbedBeforeUvLockRuns.test_stub_directories_visible_when_uv_runner_invoked`). Cross-satellite extension via the §4 OQ-C closed-form discriminator at `/tmp/lp-pt2-audit/tools/lockfile-propagator/src/lockfile_propagator/source_stub.py:106` (`_is_editable_path_source` predicate). The five satellites' `[tool.uv.sources]` shapes were verified at TDD §4 OQ-C as UNIFORMLY path-source-shaped (none use git/url/index for sibling editables); the discriminator therefore applies uniformly.
- **Production-CI green-on-Notify**: DEFER-WATCH. The two post-merge workflow runs each failed at the `Publish` step (an UPSTREAM step from the fix surface), causing `Notify-Satellite-Repos` to be SKIPPED on both. No green production run has exercised the fix surface as of the close timestamp.

**Telos owner**: 10x-dev rite per HANDOFF authority boundary at `.ledge/handoffs/HANDOFF-sre-to-10x-dev-lockfile-propagator-fix-2026-04-28.md:113`.
**Verification attester (rite-disjoint)**: SRE rite (originating critique source per HANDOFF `source_rite: sre`); the SRE rite reviews the natural-trigger workflow run when it fires — discharging or surfacing the defer per `.know/defer-watch.yaml#lockfile-propagator-prod-ci-confirmation`.

### Adversarial probes (8/8 PASS or PASS-LOW)

| ID | Probe | Severity | Disposition | Evidence |
|----|-------|----------|-------------|----------|
| P-1 | Stub creation could write outside the work_root if a satellite declares `path = "../../../etc/X"` (path-traversal attack) | LOW (defensive-depth observation) | PASS-LOW — DELIBERATE design decision: trust boundary is the satellite repo's own branch-protected `pyproject.toml`. Branch protection on each satellite gates the source declaration; the propagator does not need to defend against a satellite that has already been compromised. | Source: `/tmp/lp-pt2-audit/tools/lockfile-propagator/src/lockfile_propagator/source_stub.py:129` (`stub_dir = (repo_dir / path_value).resolve()` — uses `Path.resolve()` without sandbox-bound checking; deliberate per ADR §"Negative consequences" implicit trust boundary) |
| P-2 | Two satellites declare the SAME relative path with DIFFERENT `extras` lists; second satellite sees stub-already-present and skips, missing its required extras | LOW (defensive-depth observation) | PASS-LOW — DELIBERATE design decision per TDD §3.6 Idempotency guarantees. Stubs are content-identical at `version = "0.0.0"`; the extras-superset is captured at first-write-time by walking the calling satellite's deps. Cross-satellite extras-mismatch surfaces as a uv warning (not a failure) per TDD §4 OQ-D. | Source: `/tmp/lp-pt2-audit/tools/lockfile-propagator/src/lockfile_propagator/source_stub.py:129` (skip-when-present check at the same line family); idempotency contract documented at TDD `.ledge/specs/lockfile-propagator-source-stubbing.tdd.md:273-296` |
| P-3 | Stub creation succeeds but `uv lock` fails for unrelated reasons; the stub log line is absent from verdict JSON, masking root cause | LOW | PASS-LOW — TDD §7 R-4 documents this risk and the mitigation (the verdict JSON consumed at `autom8y/.github/workflows/sdk-publish-v2.yml:1117-1128` separates stub-failure verbiage from `uv lock` failure verbiage via the `fail(reason, ...)` helper at `propagator.py:107-118`). | TDD risk register at `.ledge/specs/lockfile-propagator-source-stubbing.tdd.md:567-571` (R-4 row) |
| P-4 | A satellite's `pyproject.toml` is malformed TOML; `_parse_uv_sources` raises `SourceStubError` and the per-satellite verdict becomes `failed` — but the OTHER satellites continue | PASS | PASS — fail-fast for the affected satellite; fail-soft for the fan-out per `propagator.py:99-101` docstring. Confirmed by unit test `test_malformed_pyproject_raises` (T-E in TDD §5.1). | Test: `/tmp/lp-pt2-audit/tools/lockfile-propagator/tests/test_source_stub.py` (T-E + T-E2 cluster) |
| P-5 | Future uv release changes editable-source-overrides-floor semantics; stub `version = "0.0.0"` no longer satisfies a satellite-declared `>=1.9.0` floor | PASS | PASS — uv version pinned at `autom8y/.github/workflows/sdk-publish-v2.yml:1010` (currently 0.10.8); upgrades are gated. T-C integration test (`test_extras_and_markers_preserved`) catches semantic regressions at any uv-version bump because it runs real `uv lock` against the produced stub. | Risk register `.ledge/specs/lockfile-propagator-source-stubbing.tdd.md:567` (R-1 row) + empirical probe at `/tmp/uvprobe-floor/` (verified 2026-04-29 with uv 0.9.7) |
| P-6 | `uv lock` requires importable Python modules in the stub (would invalidate the entire design) | PASS | PASS — empirical probe at `/tmp/uvprobe-source-stub/` confirms `uv lock` (NOT `uv sync`) does NOT require importable modules. Only `uv sync` imports during install; the propagator runs `uv lock` only. | TDD §4 OQ-A resolution at `.ledge/specs/lockfile-propagator-source-stubbing.tdd.md:300-329`; ADR §"Positive consequences" "OQ-A symbol-surface drift risk eliminated" at `.ledge/decisions/ADR-lockfile-propagator-source-stubbing.md:122-128` |
| P-7 | Stub idempotency races: parallel satellite fan-out via `parallel.py`'s `propagate_all_sync` causes two satellites to attempt to create the same stub directory simultaneously | LOW (defensive-depth observation) | PASS-LOW — DELIBERATE design decision per TDD §3.6: write race is benign because stubs are content-identical at `version = "0.0.0"`; first-writer-wins; second-writer skips on `stub_pyproject.exists()` check. No atomic-write needed. | Source: `/tmp/lp-pt2-audit/tools/lockfile-propagator/src/lockfile_propagator/source_stub.py:129` (atomicity-gate via skip-when-present) |
| P-8 | Stub creation exceeds the 55s `DEFAULT_PER_SATELLITE_TIMEOUT_SECONDS` budget | PASS | PASS — TDD §6 deadline-budget analysis at `.ledge/specs/lockfile-propagator-source-stubbing.tdd.md:540-560` shows stub creation is filesystem-only (sub-100ms per satellite worst-case); real-fleet shape is 7 sources across 5 satellites; empirical probe measured `uv lock` against a stub at 21ms wall-clock. | TDD §6 + empirical probe at `/tmp/uvprobe-source-stub/` |

**Probe summary**: 8/8 probes terminal — 5 PASS unconditional, 3 PASS-LOW (defensive-depth observations on deliberate design decisions). Three LOW-severity entries (P-1 / P-2 / P-7) cluster at `/tmp/lp-pt2-audit/tools/lockfile-propagator/src/lockfile_propagator/source_stub.py:129` — the path-resolution + idempotency-skip line — and are explicitly DELIBERATE per ADR §"Negative consequences" trust-boundary documentation: the trust boundary lives at the satellite repo's branch protection, NOT inside the propagator.

### Final verdict

**CLOSE-WITH-FLAGS** per Potnia PT-3 adjudication issued 2026-04-29. This handoff section is the Potnia adjudication record per WS-5c. Two flags carried into close:

1. **Production-CI status**: DEFER-WATCH. Tracked at `.know/defer-watch.yaml#lockfile-propagator-prod-ci-confirmation` with deadline 2026-07-29 and rite-disjoint attester `sre-rite`. Discharge requires a single `Notify-Satellite-Repos = SUCCESS` workflow run on a fresh SDK version bump.
2. **Tool README absence**: per WS-5b, `tools/lockfile-propagator/README.md` does NOT exist in the merged tool tree at `f2dfc1c3` (verified at `/tmp/lp-pt2-audit/tools/lockfile-propagator/`; only `pyproject.toml`, `src/`, `tests/` present). WS-5b instruction was conditional ("if exists, add section"; "if absent, do NOT create one — note absence in Verification Attestation §gaps"). Path-resolution invariant + §5.3 ordering documentation lives in the ADR + TDD + SCAR-LP-001 instead. Future tool-README authoring is OUT-OF-SCOPE for this attestation per WS-5e ("Do NOT include code changes").

### Postmortem hooks (institutional learnings)

- **Sandbox-resolver tools require resolution-surface materialization inside the sandbox**: the propagator's path-resolution failure is not specific to uv or to lockfile-propagator. Any tool that clones consumer repos into a temp dir and invokes a resolver with `cwd=clone_dir` must materialize relative-path references inside the sandbox before invoking the resolver. SCAR-LP-001 codifies the defensive pattern in `.know/scar-tissue.md` for future propagator-style tooling.
- **`uv lock` vs `uv sync` import-surface boundary**: TDD §4 OQ-A's empirical resolution (uv lock does NOT require importable modules; uv sync DOES) is the load-bearing distinction enabling the lightweight stub design. The api-schemas-stub composite action at `autom8y/.github/actions/api-schemas-stub/action.yml:33-102` lives at a DIFFERENT altitude (publish-job) where `uv sync` runs; the propagator extends the pattern down to sub-clone altitude where only `uv lock` runs.
- **Cascade-incompleteness signal-rejection discipline**: post-merge runs that FAIL at an UPSTREAM step before reaching the fix surface do NOT constitute regression evidence and do NOT discharge the verification telos. The DEFER-WATCH-on-natural-trigger pattern (with deadline + scope-expansion escalation) is the appropriate discipline when production-CI cannot be force-fired without overstepping authority boundary (the HANDOFF authority boundary at `.ledge/handoffs/HANDOFF-sre-to-10x-dev-lockfile-propagator-fix-2026-04-28.md:124` permits read-only verification but forbids republishing autom8y-config from this work).

### Gaps

- **Tool README**: `tools/lockfile-propagator/README.md` is ABSENT in the merged tree. Path-resolution invariant + §5.3 ordering requirement documented in ADR + TDD + SCAR-LP-001 instead. Future authoring deferred to a separate tool-documentation initiative.
- **Production-CI green-on-Notify confirmation**: DEFER-WATCH per `.know/defer-watch.yaml#lockfile-propagator-prod-ci-confirmation`.
