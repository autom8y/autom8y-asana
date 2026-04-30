---
type: triage
artifact_type: audit
rite: sre
session_id: session-20260430-203219-c8665239
task: SUB-SPRINT-A1
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3
evidence_grade: STRONG
authored_at: 2026-04-30
authored_by: platform-engineer
audit_target: "autom8y/autom8y-workflows@c88caabd:.github/workflows/satellite-ci-reusable.yml (1067 lines)"
runs_sampled: [25138295569, 25056961653, 25052268290, 25049988614, 25043033907]
runs_consumed_from_budget: 0
deliverable: ADR-012 readiness signal + cross-repo PR shape recommendation
---

# AUDIT: Path B per-step wallclock + cross-repo workflow surface

**Charter**: `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3.md` §4 Sub-sprint A.
**Branch**: `sre/sprint3-path-b-2026-04-30` HEAD `e3b5749e`.
**Authority**: Sprint-3 charter §1.1 cross-repo file access GRANTED.

---

## §1 Audit purpose

Sprint-2 closed three Path-A no-lever ADRs (ADR-008/009/010) diagnosing local-only
controls as exhausted: runner-tier (`runs-on: ubuntu-latest`) and worker-count
(`-n auto`) are hardcoded in the upstream reusable workflow at
`autom8y/autom8y-workflows`, with no caller-side override surface. Path B is the
cross-repo intervention path: parameterize the reusable workflow to accept
caller-provided `runner_size` and `test_workers` inputs, then enable the
satellite to thread them through.

This audit produces the substrate for ADR-012 (cross-repo PR-shape decision) by:

- Verifying the L393 / L527-528 line-anchors cited in Sprint-2 ADRs against the
  pinned-SHA file content (drift-audit).
- Inventorying the reusable workflow's full caller-input surface and step
  taxonomy.
- Capturing per-step wallclock from 5 successful CI runs (no probe-CI consumed).
- Re-attributing the "~463s/shard fixed-overhead" framing against direct-step
  measurement.
- Sketching the back-compat schema for two new caller inputs.
- Naming open questions for A2 (cross-repo PR authoring sub-sprint).

**Hard constraint honored**: NO files modified. Audit-only. 0 probe-CI runs
consumed (existing main runs reused).

---

## §2 Pre-flight drift-audit (L393 + L527-528 anchor verification)

Pinned SHA executing in CI per `autom8y-asana/.github/workflows/test.yml:45`:

```
uses: autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@c88caabd8d9bba883e6a42628bdc2bba6d30512b
```

Materialized-pinned source: `git show c88caabd8d9bba883e6a42628bdc2bba6d30512b:.github/workflows/satellite-ci-reusable.yml` → 1067 lines, saved at `/tmp/satellite-ci-reusable-pinned.yml`.

**Workflows-repo HEAD**: `72eaee8` (49 lines diff vs pinned SHA on this file — primarily a `astral-sh/setup-uv` v4.2.0 → v8.1.0 bump, NOT touching L393/L527-528). Path B authoring will land at workflows-repo HEAD; pinned-SHA execution is the present-tense substrate.

**Anchor verification** (against pinned SHA `c88caabd`):

| Anchor | ADR citation | Pinned-SHA content | Drift status |
|--------|--------------|--------------------|--------------|
| L393 | ADR-008 §263 — "test-job `runs-on: ubuntu-latest` (the directive Path B targets)" | `runs-on: ubuntu-latest` (verbatim, inside `test:` job at L390) | **CONFIRMED** — no drift |
| L527-528 | ADR-008 §265 / ADR-009 §135 — "`-n auto` resolution under `test_parallel: true`" | L527: `if [ "${{ inputs.test_parallel }}" = "true" ]; then` / L528: `ARGS="$ARGS -n auto"` | **CONFIRMED** — no drift |

**Verification methods**:
- file-read at `/tmp/satellite-ci-reusable-pinned.yml:393` and `:527-528`.
- substring match against ADR-009 `marker_token: "ARGS=\"$ARGS -n auto\""` (per receipt-quality predicate).

**Drift status**: BOTH anchors CONFIRMED at pinned SHA. ADR-008/009 line-anchors are valid for ADR-012 inheritance.

---

## §3 Reusable workflow surface inventory (jobs, steps, line numbers)

**File**: `/tmp/satellite-ci-reusable-pinned.yml` (`autom8y/autom8y-workflows@c88caabd:.github/workflows/satellite-ci-reusable.yml`)

**Top-level structure** (1067 lines):

| Section | Line range | Purpose |
|---------|-----------|---------|
| `name: Satellite CI` | L23 | Workflow identity |
| `run-name:` | L30-35 | Dynamic naming for consumer-gate dispatch correlation |
| `on.workflow_call.inputs:` | L37-217 | Caller-input schema (33 inputs) |
| `jobs.lint:` | L219-358 | Lint & type check (mypy, ruff) |
| `jobs.matrix-prep:` | L360-388 | Shard list emission |
| `jobs.test:` | L390-~640 | Parameterized test job (the Path-B target) |
| (other jobs: integration, conformance, spec-check, semantic-score, etc.) | L640-1067 | Out of scope for Path B |

**`test:` job step inventory** (the Path-B target — L390-onward):

| # | Step | Line range (approx) | Caller-overridable? |
|---|------|---------------------|---------------------|
| 1 | Set up job (GHA implicit) | n/a | No (GHA primitive) |
| 2 | `actions/checkout@34e114876b` | L404-406 | No (pinned SHA inside workflow) |
| 3 | Generate App token (governance) | L408-416 | Conditional on `governance_repo_root` input |
| 4 | Checkout governance repo | L418-430 | Conditional on `governance_repo_root` input |
| 5 | Set `GOVERNANCE_REPO_ROOT` | L432-435 | Conditional on `governance_repo_root` input |
| 6 | `astral-sh/setup-uv@38f3f104` | L437-441 | No (pinned SHA) |
| 7 | Set up Python | L443-446 | Yes via `python_version` input (default `3.12`) |
| 8 | Configure AWS credentials (OIDC) | L448-452 | No (uses `vars.AWS_ACCOUNT_ID`) |
| 9 | Get CodeArtifact auth token | L454-462 | No |
| 10 | Configure uv for CodeArtifact | L464-467 | No |
| 11 | Set test environment variables | L469-474 | Yes via `test_env` input |
| 12 | Install dependencies (`uv sync`) | L476-477 | Yes via `test_extras` input |
| 13-15 | Cross-repo wheel candidate path | L481-512 | Conditional on `candidate_*` inputs |
| 16 | Build pytest arguments | L514-558 | Yes via `test_*` inputs |
| 17 | **Run tests with coverage** | ~L560-580 | Indirectly via L527-528 (`-n auto` is hardcoded) |
| 18 | Upload shard durations | (post-test) | No |
| 19 | Upload coverage | (post-test) | No |
| 35-39 | Post-* teardown (GHA implicit) | n/a | No (GHA primitive) |

**Caller-input surface** (L37-217 — 33 inputs):

| Class | Inputs |
|-------|--------|
| Required | `mypy_targets`, `coverage_package`, `autom8y_workflows_sha` (R1-v3 canonical) |
| Test execution | `test_extras`, `test_markers_exclude`, `test_ignore`, `test_parallel`, `test_dist_strategy`, `test_splits`, `test_durations_path`, `test_env`, `test_timeout` |
| Coverage / mypy | `coverage_threshold`, `mypy_strict`, `mypy_advisory_targets`, `python_version` |
| Optional features | `run_integration`, `integration_timeout`, `semgrep_config`, `convention_check`, `convention_check_test_*`, `run_configspec`, `spectral_*`, `openapi_spec_path`, `spec_check_*`, `semantic_score_*`, `conformance_gate` |
| Consumer-gate | `candidate_sdk_name`, `candidate_sdk_version`, `candidate_wheel_run_id`, `dispatch_correlation_id` |
| Governance | `governance_repo_root` |

**Critical observation**: NO `runner_size` input. NO `test_workers` input. The `runs-on: ubuntu-latest` directive at L393 and the `-n auto` literal at L528 are hardcoded with no caller-side path. Path-A no-lever ADRs (008/009) confirmed.

---

## §4 Per-step wallclock measurement (5-run sample)

**Sampling protocol**: 5 successful Test runs from autom8y-asana main, captured via `gh run view --json jobs`. No probe-CI runs consumed (existing successful runs reused per charter §11.5 budget discipline).

**Run sample**:

| run_id | createdAt | headSha | conclusion |
|--------|-----------|---------|------------|
| 25138295569 | 2026-04-29T23:01Z | 40cec309 | success |
| 25056961653 | 2026-04-28T13:53Z | 3d06ed12 | success |
| 25052268290 | 2026-04-28T12:16Z | d0903cb2 | success |
| 25049988614 | 2026-04-28T11:24Z | d0903cb2 | success |
| 25043033907 | 2026-04-28T08:44Z | d0903cb2 | success |

**Per-shard total wallclock** (job-level, 4 shards × 5 runs = 20 datapoints):

| run_id | shard 1 | shard 2 | shard 3 | shard 4 | mean |
|--------|---------|---------|---------|---------|------|
| 25138295569 | 506s | 432s | **561s** | 355s | 463.5s |
| 25056961653 | 447s | 413s | 401s | 433s | 423.5s |
| 25052268290 | 441s | 394s | 397s | 471s | 425.8s |
| 25049988614 | 442s | 411s | 415s | 371s | 409.8s |
| 25043033907 | 437s | 396s | 400s | 428s | 415.3s |
| **mean** | **454.6s** | **409.2s** | **434.8s** | **411.6s** | **427.6s** |

Aggregate: mean shard duration **427.6s ± 50s**, max observed **561s** (the 002a outlier referenced in ADR-010).

**Per-step breakdown — sample shard 1/4 of run 25138295569** (506s total):

| step # | step name | duration | category |
|--------|-----------|----------|----------|
| 1 | Set up job | 6s | GHA setup |
| 2 | actions/checkout | 3s | repo setup |
| 3-5 | governance App-token + checkout | 0s (skipped) | conditional |
| 6 | setup-uv | 1s | toolchain |
| 7 | Set up Python | 0s | toolchain |
| 8 | Configure AWS credentials (OIDC) | 1s | auth |
| 9 | Get CodeArtifact auth token | 2s | auth |
| 10 | Configure uv for CodeArtifact | 0s | env |
| 11 | Set test environment variables | 0s | env |
| 12 | Install dependencies | 11s | toolchain |
| 13-15 | Consumer-gate wheel | 0s (skipped) | conditional |
| 16 | Build pytest arguments | 0s | env |
| **17** | **Run tests with coverage** | **474s** | **execution** |
| 18 | Upload shard durations | 0s | post |
| 19 | Upload coverage | 2s | post |
| 35-39 | Post-* teardown | ~3s | GHA teardown |

**Setup pre-test (steps 1-12+16)**: 24s. **Test execution (step 17)**: 474s. **Post-test/teardown (18-19+35-39)**: 5s. **Total**: 503s (matches job-level 506s within GHA queueing noise).

**Per-step breakdown — sample shard 3/4 of run 25138295569** (561s total — the outlier):

| step # | step name | duration |
|--------|-----------|----------|
| 1-12,16 (setup) | (sum) | 16s |
| **17** | **Run tests with coverage** | **539s** |
| 18-19,35-39 (teardown) | (sum) | 4s |

**Cross-shard per-step durations >1s** (3 runs × 2 shards = 6 samples confirm pattern):

```
Setup steps (1-12, 16): 16-30s total, dominated by step 12 (Install dependencies, 7-15s)
Step 17 (Run tests with coverage): 316-539s — DOMINANT cost, accounts for 89-96% of shard wallclock
Teardown (18-19, 35-39): 3-5s
```

---

## §5 ~463s fixed-overhead attribution (RE-INTERPRETATION)

**ADR-010 framing** (cited at `.ledge/decisions/ADR-010-shard-expansion-stay-at-4-2026-04-30.md:204`):
> "~463s CI fixed-overhead (within 449.5s ± 3% envelope)"

The 449.5s figure was derived in ADR-010 §40 by `561s observed - 111.5s theoretical pytest pure-time = 449.5s`, treating the residual as "fixed overhead per shard." This produced the recommendation that shard expansion (N=5..8) cannot reduce wallclock below ~500s because fixed overhead dominates pure-time.

**Direct-measurement re-attribution** (from §4 above):

| Component | ADR-010 estimate | Direct measurement (run 25138295569 shard 3/4) | Re-attribution |
|-----------|------------------|------------------------------------------------|----------------|
| GHA setup + checkout + toolchain (steps 1-12, 16) | (subsumed in 449.5s) | **16s** | NOT the bottleneck |
| Test execution (step 17 wallclock) | 111.5s pure-time + 449.5s overhead | **539s** (single step) | The 449.5s "fixed overhead" was ALREADY pytest wallclock |
| GHA teardown (post-steps) | (subsumed in 449.5s) | **~4s** | NOT the bottleneck |

**The "~463s/shard fixed-overhead" framing is misattributed**:

- True GHA-substrate fixed overhead (setup + teardown + checkout + toolchain) is **~20-25s/shard**, not 449.5s.
- The remaining ~440s is **pytest wallclock under `-n auto`** (worker-count constrained by 2-vCPU `ubuntu-latest`), NOT GHA infrastructure overhead.
- Pytest "pure time" theoretical estimates that subtract 449.5s as overhead were treating xdist worker-bottleneck wallclock AS overhead.

**Implication for Path B**:

- Path B targets the actual bottleneck: test execution wallclock (step 17), which is the 89-96% dominant component.
- Two levers, both reachable only via cross-repo PR:
  1. **`runner_size` upgrade** (L393): `ubuntu-latest` (2 vCPU) → `ubuntu-latest-large` (8 vCPU) lets `-n auto` resolve to 8 workers instead of 2, reducing pytest wallclock proportionally.
  2. **`test_workers` override** (L527-528): replace `-n auto` with `-n ${{ inputs.test_workers }}` so callers can tune worker count independent of vCPU detection.
- These are **multiplicative**: 8-vCPU runner with `-n 8` gives 4x wallclock reduction headroom for the dominant 440s component, NOT for the 20s setup overhead.

**Sprint-2 ADR-010 status**: the ratification (stay at N=4 shards) STANDS — shard expansion does not reduce step-17 wallclock under fixed `-n auto` on 2-vCPU. Path B's runner+worker upgrade is the orthogonal lever ADR-010 explicitly named at line 296: "what specific steps in the reusable workflow contribute most to the 449.5s — checkout, setup-uv, [...]". Direct measurement now answers: **none of those — it's pytest itself**.

---

## §6 Caller-input surface (current vs proposed)

**Current relevant inputs** (L201-205 + L79-90):

```yaml
test_timeout:
  description: 'Timeout in minutes for the test job (default: 20)'
  type: number
  default: 20
test_parallel:
  description: 'Enable pytest-xdist parallel execution (-n auto)'
  type: boolean
  default: false
test_splits:
  description: 'Number of pytest-split matrix shards for the test job (1 = disable sharding, default: 1)'
  type: number
  default: 1
```

**Hardcoded directives** (need parameterization for Path B):

- L393: `runs-on: ubuntu-latest` (no input variable)
- L528: `ARGS="$ARGS -n auto"` (no input variable; only a `test_parallel` boolean gate at L527)

**Proposed Path-B inputs** (back-compat schema, default-preserves-status-quo):

```yaml
runner_size:
  description: 'GitHub-hosted runner tier for test job. "standard" = ubuntu-latest (2 vCPU). "large" = ubuntu-latest-large (8 vCPU; org-billed).'
  type: string
  default: 'standard'
test_workers:
  description: 'pytest-xdist worker count override for test job. 0 = use "-n auto" (default; xdist auto-detects vCPU). N>0 = use "-n N" (explicit worker count).'
  type: number
  default: 0
```

**Caller migration shape** (autom8y-asana `test.yml:46-72` after Path B lands):

```yaml
uses: autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@<NEW_SHA>
with:
  # ... existing inputs unchanged ...
  runner_size: 'large'      # NEW: 8-vCPU upgrade
  test_workers: 8           # NEW: explicit -n 8 override
  # autom8y_workflows_sha must be re-pinned to <NEW_SHA>
```

**Other satellites** (autom8y-data, etc.) NOT passing the new inputs receive `default: 'standard'` + `default: 0` → preserves `runs-on: ubuntu-latest` + `-n auto` behavior. Zero behavior change for non-opt-in callers.

---

## §7 Back-compat schema for proposed parameters

**Schema design constraints**:

1. **No breaking change to existing satellites** — autom8y-data, autom8y-ads, etc. consume the same reusable workflow and must continue to work without modification.
2. **Sentinel-default for opt-in** — `default: 'standard'` (string) and `default: 0` (sentinel integer) match current hardcoded behavior; callers opt-in by passing non-default values.
3. **Type-safe matrix expansion (if needed)** — single satellite opt-in to `runner_size: 'large'` does not affect the `runs-on:` directive of OTHER satellites' invocations because each `workflow_call` is per-caller-context.

**Implementation sketch** (Path-B PR shape):

| File | Edit | Type |
|------|------|------|
| `.github/workflows/satellite-ci-reusable.yml` L37-217 | Add `runner_size` and `test_workers` input declarations | Schema addition |
| `.github/workflows/satellite-ci-reusable.yml` L393 | `runs-on: ubuntu-latest` → `runs-on: ${{ inputs.runner_size == 'large' && 'ubuntu-latest-large' \|\| 'ubuntu-latest' }}` | Expression substitution |
| `.github/workflows/satellite-ci-reusable.yml` L527-528 | `if [ "${{ inputs.test_parallel }}" = "true" ]; then ARGS="$ARGS -n auto"; fi` → conditional on `test_workers` value | Multi-line script edit |

**Worker-count expression at L527-528** (proposed):

```yaml
if [ "${{ inputs.test_parallel }}" = "true" ]; then
  if [ "${{ inputs.test_workers }}" -gt 0 ]; then
    ARGS="$ARGS -n ${{ inputs.test_workers }}"
  else
    ARGS="$ARGS -n auto"
  fi
fi
```

**Matrix/strategy considerations** (for `runs-on:` expression at L393):

- `runs-on:` accepts GHA expressions; the conditional `${{ inputs.runner_size == 'large' && 'ubuntu-latest-large' || 'ubuntu-latest' }}` resolves at workflow-call time per the matrix shard.
- Each shard in the `strategy.matrix.shard` (L398-401) inherits the same `runs-on:` expression — uniform behavior across shards within a single caller invocation.
- No matrix expansion needed for `runner_size` itself (caller passes a single value, not a matrix).

**Risk: `ubuntu-latest-large` org-billing impact**:

- 8-vCPU runner is org-billed at higher per-minute rate (per GitHub pricing: 4x cost vs `ubuntu-latest`).
- Single satellite opt-in (autom8y-asana only) is bounded; runner-min impact is the area for ADR-012 cost-benefit analysis.

---

## §8 ADR-012 readiness — recommended PR shape, blast radius, risks

**Recommendation: SINGLE-BUNDLE PR** at `autom8y/autom8y-workflows`.

**Rationale**:

1. The two parameters (`runner_size`, `test_workers`) are **co-designed**: `runner_size: large` without `test_workers > 0` underutilizes the 8-vCPU runner because `-n auto` may not detect all cores reliably under all GHA runner-image versions; `test_workers: 8` without `runner_size: large` over-subscribes the 2-vCPU `ubuntu-latest` (xdist contention).
2. **Splitting introduces a transitive-bug window**: a satellite opting into one parameter without the other is a configuration-error class with no detection — bundling makes the two-input opt-in atomic.
3. **Charter §4.3 Q1(a) BUNDLED PR is locked** by Pythia inaugural consult — recommendation aligns with charter governance.

**PR contents** (single bundle):

- Schema addition: 2 new inputs at L37-217 with back-compat defaults.
- Expression substitution at L393.
- Multi-line script edit at L527-528 (4 lines added — outer `if` + inner `if` + 2 `ARGS=` lines).
- Total LOC: ~12 lines added, ~1 line modified.

**Blast radius** (consumers of `satellite-ci-reusable.yml@*`):

- Satellites pinning to specific SHAs (the autom8y-asana pattern at L45 of `test.yml`) are **isolated** from upstream changes until they re-pin. Path B PR landing does NOT auto-roll out.
- Satellites using `@main` or `@v1` floating refs (if any exist) inherit the change on next run. Audit of pinning patterns across satellites is OUT OF SCOPE for this audit and should be checked at A2 authoring time (see §9 OQ-3).
- Default behavior: `runner_size: 'standard'` + `test_workers: 0` = identical to current hardcoded `runs-on: ubuntu-latest` + `-n auto`. Zero-behavior-change guarantee for all non-opt-in callers.

**Risks**:

| Risk | Severity | Mitigation |
|------|----------|-----------|
| YAML expression parser rejects compound `${{ }}` ternary | MEDIUM | GHA documents the form; precedent in autom8y-workflows already exists at L33-35 (run-name expression); validate at PR draft via `act` or workflow_dispatch dry-run |
| `ubuntu-latest-large` not enabled at autom8y org level | HIGH | Verify org-runner-tier availability BEFORE landing PR — check GHA settings or run a test workflow. If unavailable, request enablement ahead of A2. |
| Satellite breakage if `test_workers` accepts negative integers | LOW | Schema declares `type: number` + script does `[ -gt 0 ]` check; negative values fall through to `-n auto` (graceful) |
| Cost surprise from satellites silently flipping to `runner_size: 'large'` | LOW | Default is `'standard'`; opt-in is explicit via caller `with:` block edit. ADR-012 should require per-satellite opt-in adoption note. |

**Verification steps post-merge**:

1. autom8y-asana re-pins `test.yml:45,71` to new workflow SHA + adds `runner_size: 'large'` + `test_workers: 8` to caller `with:` block.
2. Probe-CI run on a feature branch in autom8y-asana validates both shard wallclock reduction AND coverage parity.
3. Compare measured shard duration against §4 baseline (mean 427.6s) — Path-B target is to bring slowest-shard wallclock from observed 561s outlier toward ~150s headroom (4x runner upgrade × n=8 worker exploit on the ~440s pytest component).

---

## §9 Open questions for A2 (cross-repo PR authoring)

**OQ-1**: Is `ubuntu-latest-large` (8-vCPU GitHub-hosted runner) enabled at the `autom8y` org level, OR does it require GHA settings activation? **Discharge**: A2 sub-sprint MUST verify before authoring PR. If unavailable, this is a HARD-HALT for Path B until enablement is granted.

**OQ-2**: Does the existing CI infrastructure already use any `large` runner tier for any other workflow (security-scorecard, dependency-review, etc.)? **Discharge**: A2 should grep autom8y-workflows for `runs-on: ubuntu-latest-large` to confirm precedent + cost-band history.

**OQ-3**: How many satellites consume `satellite-ci-reusable.yml`? **Discharge**: A2 should enumerate via `gh search code 'satellite-ci-reusable.yml' --owner=autom8y` to confirm blast-radius assumption (only autom8y-asana + autom8y-data + autom8y-ads identified at sprint-2 substrate; verify exhaustive list).

**OQ-4**: Is there a precedent for adding new optional inputs to `satellite-ci-reusable.yml` WITHOUT bumping a major version tag? **Discharge**: A2 reviews the workflows-repo CHANGELOG (if present) or recent git log for "breaking-change discipline" — additive optional inputs are conventionally non-breaking, but the workflows-repo may have stricter conventions.

**OQ-5**: Should the Path-B PR also expose a `python_version` matrix-expansion lever? **Out of scope for Sprint-3** — explicitly excluded per charter §4. Park as future-deferred work via `defer-watch-manifest` if surfaced.

**OQ-6**: Does the re-attribution finding (§5: ~463s is pytest wallclock, NOT GHA overhead) require an addendum to ADR-010? **Recommended**: yes — ADR-010's "fixed-overhead" framing should be amended with a forward-pointer to this audit's §5, preserving the ratification (stay at N=4) while correcting the diagnostic premise. ADR-012 authoring (sub-sprint A3 / shape-pending) can carry the addendum as a §References-update.

**OQ-7**: A2 PR-authoring sequence — does the workflows-repo PR land FIRST, then the autom8y-asana caller-update PR follow, OR are they prepared in parallel and merged in lockstep? **Recommendation**: workflows-repo PR lands first (CI-green at default-preserves-status-quo behavior); autom8y-asana caller-update PR opens against a re-pinned SHA after merge. This is the safe-rollback ordering — autom8y-asana never breaks because the workflows-repo change is back-compat, and the caller-update PR can be reverted independently.

---

## §10 Audit checkpoints

**Pre-flight drift-audit**: PASS — L393 + L527-528 anchors CONFIRMED at pinned SHA `c88caabd` (no drift from Sprint-2 ADR-008/009 citations).

**Per-step measurement**: PASS — 5 successful runs (20 shard datapoints + 6 detailed step-breakdowns) captured WITHOUT consuming the §11.5 probe-CI budget.

**Re-attribution finding**: NEW — direct measurement contradicts ADR-010's "449.5s fixed-overhead" framing. The dominant ~440s/shard component is pytest wallclock under `-n auto` on 2-vCPU, NOT GHA infrastructure setup overhead (which is ~20-25s/shard). Path B targets the actual bottleneck.

**Back-compat schema**: DRAFTED — `runner_size: 'standard'` + `test_workers: 0` sentinel-defaults preserve status quo for non-opt-in callers; opt-in is explicit per caller.

**PR shape**: SINGLE-BUNDLE recommended — co-designed parameters; charter §4.3 Q1(a) BUNDLED PR locked; blast radius bounded by per-satellite SHA-pinning.

**ADR-012 readiness**: READY-TO-DISPATCH-A2 conditional on **OQ-1 (`ubuntu-latest-large` enablement verification)**. If OQ-1 returns negative, HALT and re-route Path B.

---

## §11 Receipt-grammar appendix

**Anchor citations** (file:line + run-id + measured timing):

- Pinned SHA `c88caabd8d9bba883e6a42628bdc2bba6d30512b` of `autom8y-workflows:.github/workflows/satellite-ci-reusable.yml` (1067 lines)
- L393: `runs-on: ubuntu-latest` (verbatim, inside `test:` job declared at L390)
- L527-528: `if [ "${{ inputs.test_parallel }}" = "true" ]; then` / `ARGS="$ARGS -n auto"` (verbatim)
- L37-217: `on.workflow_call.inputs:` schema block (33 inputs declared)
- L390-401: `test:` job declaration with `runs-on: ubuntu-latest` + `strategy.matrix.shard: ${{ fromJson(needs.matrix-prep.outputs.shard_list) }}`
- L514-558: `Build pytest arguments` step at the heart of L527-528 hardcoded behavior

**Measured run-IDs**: `25138295569`, `25056961653`, `25052268290`, `25049988614`, `25043033907` (5 successful Test runs, autom8y-asana main, sampled 2026-04-30).

**Mean per-shard wallclock**: 427.6s (n=20). Max observed: 561s (run 25138295569 shard 3/4 — the ADR-010 outlier referenced at line 39 of ADR-010).

**Budget consumed**: 0 probe-CI runs (existing main runs reused per charter §11.5).

---

END AUDIT. Sub-sprint A1 deliverable complete. ADR-012 readiness signal: **CONDITIONAL READY** pending OQ-1 (`ubuntu-latest-large` org enablement). Recommendation: A2 dispatch authorized after OQ-1 discharge.
