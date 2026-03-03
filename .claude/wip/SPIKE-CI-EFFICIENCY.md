# SPIKE: CI Pipeline Efficiency

**Date**: 2026-02-24
**Timebox**: 30 min
**Decision**: What optimizations reduce wasted CI minutes and cascade latency?

## Current Pipeline

```
Push to main
  └─ Test (~5.5min wall clock)
       ├─ lint-check: format + ruff + mypy --strict (~35s)
       ├─ unit-tests: pytest -n auto (fast subset) (~4min)
       ├─ full-regression: pytest -n auto (all non-integration) (~5min)
       └─ integration-tests: pytest tests/integration/ (~1min)
  └─ Satellite Dispatch (~15s, triggers on Test success)
       └─ Satellite Receiver in autom8y/autom8y (~8.5min)
            ├─ Validate Payload (~10s)
            ├─ Checkout Satellite Code (~15s)
            ├─ Build and Push (Docker → ECR, ~5min)
            ├─ Deploy to ECS (~3min, rolling + health check)
            └─ Deploy Lambda via Terraform (~1min)

Total end-to-end: ~14 minutes per green push
```

## Measured Data (2026-02-24)

| Metric | Value |
|--------|-------|
| Test runs today (last 10) | 2 success, 5 failure, 3 cancelled |
| Satellite Dispatches today | 2 success, 8 skipped (correct: only fires on green) |
| Satellite Receiver runs today | 2 (both success) |
| Test run wall clock | 5.5 min (331s) |
| Receiver wall clock | 8.6 min (517s) |
| GH Actions cache (autom8y-asana) | **0 active caches** (broken) |
| GH Actions cache (autom8y) | 12 caches, 968 MB |
| Billable minutes | 0 (included in plan) |

## Findings

### F-1: GH Actions Cache is Broken (HIGH IMPACT)

autom8y-asana has **zero active caches**. Every run shows `Failed to restore: Cache service responded with 400`. The `setup-uv` action has `enable-cache: true` but nothing persists. This means:

- **Every test job reinstalls all dependencies from scratch** via CodeArtifact
- `uv sync --all-extras` downloads ~200+ packages every run
- Estimated 60-90s wasted per job × 4 jobs = **4-6 min per run**

The monorepo (autom8y/autom8y) has working caches (12 active, 968MB). The satellite repo's cache likely expired or was evicted. GitHub's cache has a 7-day eviction policy for unused caches — if the repo went a week without pushes, all caches died.

**Fix**: Force a cache prime by running `gh cache delete --all` then a fresh push. Or add a `cache-suffix` to bust stale keys.

### F-2: Pre-commit Hooks Exist but Aren't Installed (HIGH IMPACT)

`.pre-commit-config.yaml` has ruff-format, ruff-check, AND mypy --strict. All the checks that failed in CI today would have been caught locally:
- `ruff format` (formatting)
- `ruff check` (linting)
- `mypy --strict` (type checking)

But the hooks are **not installed** — `.git/hooks/` contains only `.sample` files.

**Fix**: `uv run pre-commit install`. This catches 100% of today's lint/format/type failures before push.

### F-3: Docker Build Has No Layer Cache (MEDIUM IMPACT)

`service-build.yml` uses `docker/build-push-action@v5` with **no cache configuration**. No `cache-from`/`cache-to` with `type=gha` or `type=registry`. Every build pulls the base image and reinstalls all dependencies.

The Dockerfile has good layer structure (`COPY pyproject.toml uv.lock` before `COPY src`) but this only helps with local Docker cache, which doesn't exist in ephemeral CI runners.

**Fix**: Add `cache-from: type=gha` and `cache-to: type=gha,mode=max` to the build-push-action. Estimated savings: 2-3 min per build when only src/ changes (dependencies cached).

### F-4: satellite-gate-reusable.yml is Dead Code (LOW IMPACT)

Exists but never called. The current flow uses `workflow_run` trigger directly. The gate workflow would add a re-check of test status before dispatching — useful if dispatch could be triggered manually without a preceding green test run. Currently redundant because the `if: conclusion == 'success'` guard on Satellite Dispatch already handles this.

**Disposition**: Leave it. It's a safety net for manual `workflow_dispatch` scenarios and costs nothing when unused.

### F-5: No Dispatch Debouncing (LOW IMPACT TODAY)

Rapid-fire pushes generate multiple Test runs but Satellite Dispatch correctly skips on failure. Only the last green push actually deploys. Today's pattern: 10 Test runs → 2 dispatches → 2 deploys. The waste is in Test runs, not deploys.

GitHub's `concurrency: cancel-in-progress: true` on the Test workflow already cancels superseded runs. 3 of today's 10 runs were cancelled — the mechanism works.

**Disposition**: Already handled well. No action needed.

## Options Matrix

| Option | Impact | Effort | Risk | Savings/run |
|--------|--------|--------|------|-------------|
| **O-1: Install pre-commit hooks** | HIGH | 5 min | None | Prevents bad pushes entirely |
| **O-2: Fix GH Actions cache** | HIGH | 15 min | Low | ~60-90s × 4 jobs = 4-6 min |
| **O-3: Docker build cache (type=gha)** | MEDIUM | 30 min | Low | ~2-3 min per build |
| **O-4: Path-based test skipping** | MEDIUM | 1 hr | Medium | Skip full suite for docs/config |
| **O-5: Debounce dispatch (wait N min)** | LOW | 2 hr | Medium | Reduces deploy churn |
| **O-6: Remove dead gate workflow** | NONE | 5 min | None | Cleanup only |

## Recommendation

**Do O-1 + O-2 now** (20 min total, highest ROI):

1. `uv run pre-commit install` — prevents the entire class of "push → fail on lint → fix → push again" cycles that burned 5 runs today
2. Investigate and fix the GH Actions cache — saves ~4 min per run and reduces CodeArtifact load

**Do O-3 next** (30 min, medium ROI):
3. Add Docker build cache to `service-build.yml` — saves ~2-3 min per deploy when only source code changes

**Defer O-4 and O-5** — complexity vs. benefit ratio isn't justified yet. The concurrency cancellation already handles the rapid-fire case well.

## Follow-up Actions

- [ ] Run `uv run pre-commit install` locally (O-1)
- [ ] Debug GH Actions cache 400 errors — check `gh cache list` and cache key format (O-2)
- [ ] Add `cache-from: type=gha` to service-build.yml in autom8y/autom8y (O-3)
- [ ] Document pre-commit requirement in CLAUDE.md or CONTRIBUTING.md
