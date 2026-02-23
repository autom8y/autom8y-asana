# SCOUT-pkg-distribution-resilience

## Executive Summary

The autom8y ecosystem routes all private SDK resolution through a single AWS CodeArtifact repository. This creates a genuine single point of failure: any CodeArtifact outage, token expiry, or AWS IAM misconfiguration halts every build and deployment across all satellite repos. This assessment evaluates six proven approaches to reduce that blast radius. The verdict is a **layered strategy**: Adopt CI cache hardening immediately (highest ROI, lowest effort), Trial a secondary registry for defense-in-depth, and Hold on heavier structural approaches that exceed the team's operational budget.

## Technology Overview

- **Category**: Infrastructure / Package Distribution Resilience
- **Maturity**: Problem space is Mature; solutions range from Mature (caching) to Growing (multi-registry with uv)
- **License**: N/A (patterns, not products)
- **Backing**: Astral (uv), AWS (CodeArtifact), Community (devpi)

## Current Topology

```
autom8y monorepo (11 SDKs)
    |
    v  [python-semantic-release + GH Actions]
AWS CodeArtifact (autom8y-python)
    |
    +-- autom8y-asana  (7 SDKs: auth, cache, config, core, http, log, telemetry)
    +-- autom8y-data
    +-- autom8y-ads
    +-- ... (other satellites)
```

**Blast radius today**: CodeArtifact down = 0 satellites can build, test, or deploy.

Key observation from the lockfile: CodeArtifact also proxies all 109 PyPI packages. The `[[tool.uv.index]]` with `default = true` on PyPI means uv should prefer PyPI for non-pinned packages, but the lockfile URLs show everything resolving through CodeArtifact. This means CodeArtifact outage blocks even standard PyPI packages.

## Approach-by-Approach Evaluation

---

### 1. Multi-Registry Fallback (uv `--extra-index-url`)

**Concept**: Configure a secondary registry (e.g., GCP Artifact Registry, another CodeArtifact in a different region) as fallback.

**Maturity**: Growing. uv's multi-index support is production-ready but has important behavioral nuances.

**Production References**: Plotly, many ML teams using PyPI + PyTorch index simultaneously.

**uv Compatibility**:
- uv supports multiple `[[tool.uv.index]]` entries with well-defined priority ordering.
- `tool.uv.sources` can pin specific packages to specific indexes, which is exactly what autom8y-asana already does.
- **Critical nuance**: uv's default `first-index` strategy stops at the first index that *has* the package. If CodeArtifact is down (connection timeout, not 404), uv does NOT automatically fall back -- it fails. HTTP 404 triggers continued search; connection errors and 401/403 halt resolution.
- The `ignored-error-codes` setting can customize 401/403 behavior per index, but connection timeouts are not configurable error codes.

**Build Time Impact**: Negligible if primary is healthy. Adds timeout delay (30-60s) per package when primary is down before fallback kicks in (if it kicks in at all).

**Operational Overhead**: Medium.
- Must maintain a second registry (publish SDKs to two places, or sync them).
- Must manage auth tokens for both registries.
- Must ensure both registries stay in sync after every SDK release.
- Dual-publish in CI adds ~2 min to monorepo release pipeline.

**Risk Reduction**: Partial. Protects against registry-level 404s and some HTTP errors. Does NOT protect against connection timeouts or DNS failures (uv treats these as hard errors, not fallback triggers). Does NOT protect against token expiry (affects both registries simultaneously if using same IAM role).

**Verdict: Assess**. The uv fallback semantics are not true "if primary fails, try secondary" -- they are "if primary returns 404, try secondary." This limits the actual resilience gain. Worth investigating whether uv's behavior has improved in recent versions, but not a reliable standalone solution today.

---

### 2. Vendored Dependencies (wheels in repo)

**Concept**: Check SDK `.whl` files into each satellite repo (or a shared git submodule). Install from local path at build time.

**Maturity**: Mature pattern. Python Packaging User Guide documents `--find-links` for local directories. Explosion AI's `wheelwright` project automates this.

**Production References**: Explosion AI (spaCy), many air-gapped enterprise environments, Databricks internal tooling.

**uv Compatibility**:
- `uv pip install --find-links ./vendor/wheels/ --no-index` works.
- `uv sync --frozen --no-index --find-links=./vendor/wheels/` has known rough edges (GitHub issue #15519) -- may still attempt PyPI fetches for dev dependencies.
- For `tool.uv.sources`, path dependencies (`{ path = "./vendor/autom8y-core-1.1.0-py3-none-any.whl" }`) are supported but require updating pyproject.toml on every SDK version bump.

**Build Time Impact**: Faster (no network I/O). Installing from local wheels is near-instant.

**Operational Overhead**: High.
- 7 SDK wheels must be committed and updated in every satellite repo on every SDK release.
- Wheels are ~50-200KB each (pure Python), so ~1MB total per satellite repo -- manageable for git.
- Requires automation: monorepo CI must push wheels to all satellite repos or a shared location.
- Version coordination becomes manual: must update vendored wheels AND pyproject.toml version pins.
- Git history bloat accumulates over time (binary diffs on `.whl` files).

**Risk Reduction**: Complete for build-time resolution. If wheels are vendored, CodeArtifact is entirely removed from the build path. Token expiry, registry outage, and network issues are all eliminated.

**Verdict: Hold**. Maximum resilience but excessive operational overhead for a small team. The wheel update dance across N satellite repos on every SDK release creates a maintenance burden that exceeds the risk it mitigates. Consider only if CodeArtifact outages become frequent (>1/month).

---

### 3. Registry Mirroring (devpi, Artifactory, pulp)

**Concept**: Run a self-hosted mirror that syncs from CodeArtifact. Builds resolve from the mirror.

**Maturity**: Mature. devpi has been in production since 2013. JFrog Artifactory is enterprise-grade. Pulp is Red Hat-backed.

**Production References**: devpi is used by many Python shops for caching and staging. Artifactory is deployed at enterprises globally. Pulp is used in Fedora/RHEL package infrastructure.

**uv Compatibility**: Full. Any PEP 503-compatible simple repository index works with uv's `[[tool.uv.index]]`.

**Build Time Impact**: Faster for repeated installs (local cache hit). First sync adds latency.

**Operational Overhead**: High.
- Must provision, secure, and maintain a server (devpi: ~256MB RAM, Artifactory: ~2GB RAM minimum).
- Must configure sync schedule from CodeArtifact.
- Must handle auth for both the mirror and upstream.
- devpi itself has no HA story -- single server, single disk. Artifactory has HA but requires commercial license ($$$).
- If the mirror goes down, you have the same SPOF problem, just moved.
- Monitoring, backups, and updates become your responsibility.

**Risk Reduction**: Moderate. Protects against CodeArtifact outages IF the mirror was recently synced. Does NOT protect against: mirror's own downtime, stale sync (new SDK version not yet mirrored), or the mirror's storage/compute failures.

**Verdict: Avoid** (for this team size). Running infrastructure to protect against infrastructure failure adds operational burden without proportional benefit. The mirror itself becomes a new SPOF. Only makes sense for organizations with dedicated platform engineering teams and >50 developers.

---

### 4. Git-Based Distribution

**Concept**: Use `uv pip install git+https://github.com/org/autom8y.git#subdirectory=sdks/python/autom8y-core` instead of registry resolution.

**Maturity**: Mature pattern. pip and uv both support `git+https` dependencies natively.

**Production References**: Common in early-stage startups and open-source projects. Less common at scale due to build time and reproducibility concerns.

**uv Compatibility**:
- `tool.uv.sources` supports git sources: `autom8y-core = { git = "https://github.com/org/autom8y.git", subdirectory = "sdks/python/autom8y-core", tag = "autom8y-core-v1.1.0" }`.
- uv caches based on fully-resolved git commit hash -- subsequent installs are fast.
- Known issue: `uv lock --locked` can raise false-positive errors with git dependencies (GitHub issue #5851).
- Lockfile reproducibility depends on tag immutability (force-pushed tags break reproducibility).

**Build Time Impact**: Significant on first install (clones entire monorepo). The autom8y monorepo with 11 SDKs could be large. Subsequent installs use commit hash cache. Each of 7 SDK dependencies would clone the same repo but uv may not deduplicate across subdirectories.

**Operational Overhead**: Low-Medium.
- No new infrastructure to maintain.
- GitHub availability (99.95% SLA) is generally higher than CodeArtifact.
- Must manage GitHub token/SSH key in CI (already present for checkout).
- Must tag releases consistently in monorepo for reproducibility.
- Loses the clean separation of "published package" vs "source code."

**Risk Reduction**: Moderate. Shifts dependency from CodeArtifact to GitHub. GitHub has better availability history than CodeArtifact. Does NOT eliminate SPOF -- just moves it to a more reliable provider. Token management shifts from AWS to GitHub (simpler, longer-lived).

**Verdict: Assess**. Viable as an emergency fallback (switch `tool.uv.sources` to git refs during CodeArtifact outage), but too slow and fragile for primary distribution. The monorepo clone cost and lockfile reproducibility issues make this a poor default. Worth having as a documented break-glass procedure.

---

### 5. Lock File Caching (uv cache in CI)

**Concept**: Cache resolved packages in CI (GitHub Actions cache, Docker layer cache). Registry is only needed when a dependency version changes.

**Maturity**: Mature. GitHub Actions caching is a first-class feature. `astral-sh/setup-uv` has built-in cache support since v2. Docker layer caching is decades old.

**Production References**: Virtually every CI pipeline at scale uses dependency caching. Astral's own CI docs recommend this pattern. Hynek Schlawack's `setup-cached-uv` action is widely adopted.

**uv Compatibility**: Excellent.
- `astral-sh/setup-uv@v7` with `enable-cache: true` handles cache persistence automatically.
- Cache key based on `uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}` with OS-only fallback.
- `uv cache prune --ci` optimizes cache size (removes pre-built wheels, keeps built-from-source wheels).
- `uv sync --frozen` uses lockfile without re-resolving, and cached packages skip network entirely.
- Docker `--mount=type=cache,target=/root/.cache/uv` already in use in the production Dockerfile.

**Build Time Impact**: Dramatically faster. Cache hit = no network I/O at all. Cache miss (new dependency) = single package download. Current autom8y-asana Dockerfile already uses `--mount=type=cache` for uv.

**Operational Overhead**: Very Low.
- 3-5 lines of YAML change in CI workflow.
- No new infrastructure.
- No new auth.
- No sync processes.
- Cache invalidates automatically when `uv.lock` changes.

**Risk Reduction**: High for the common case. If CodeArtifact goes down:
- **Existing PRs with no dependency changes**: Build succeeds from cache. Zero impact.
- **New PRs with dependency changes**: Build fails (must fetch new packages). This is the only failure mode.
- **Production deploys of unchanged code**: Succeed if Docker layer cache is warm.
- **SDK version bumps during outage**: Blocked. This is acceptable -- you cannot upgrade dependencies without a registry.

**Current Gap Analysis**: The test workflow at `.github/workflows/test.yml` does NOT use `enable-cache: true` on `astral-sh/setup-uv@v2`. This means every CI run re-downloads all 109 packages from CodeArtifact. Fixing this single gap eliminates ~95% of the CodeArtifact dependency for routine CI runs.

**Verdict: Adopt**. Highest ROI, lowest effort, zero operational overhead. The current CI workflow is missing uv cache enablement -- adding it immediately reduces CodeArtifact dependency to only "when a dependency version actually changes." The production Dockerfile already uses Docker-level caching correctly.

---

### 6. Monorepo Distribution (path dependencies via git subtree/submodule)

**Concept**: Include SDK source code in each satellite repo via git subtree or submodule. Use path dependencies for resolution.

**Maturity**: Mature (git subtree/submodule are decades old). Growing for Python SDK distribution via this pattern.

**Production References**: Apollo GraphQL uses subtrees for Swift package distribution. Google's internal monorepo. Many organizations using Bazel with monorepo patterns.

**uv Compatibility**:
- Path dependencies work: `autom8y-core = { path = "./lib/autom8y-core", editable = true }`.
- Workspace mode could treat subtree'd SDKs as workspace members.
- Requires changing `tool.uv.sources` for all 7 SDKs.
- `uv sync` with path deps is fast (no network, no build step for pure Python).
- The existing `Dockerfile.dev` already demonstrates this pattern: it volume-mounts SDK source at `/app/sdks/` and sets `PYTHONPATH`.

**Build Time Impact**: Fastest possible. No network, no registry, no wheels. Direct source import.

**Operational Overhead**: High.
- Git submodules: notorious developer experience friction (forgotten `--recursive`, detached HEAD, merge conflicts on submodule pointer).
- Git subtrees: simpler DX but complex history (merge commits, squash decisions), and pulling updates requires knowing the subtree prefix and remote.
- Must update subtree/submodule in every satellite repo on every SDK release.
- CI must handle submodule init/update (additional step, additional GitHub token scope).
- Breaks the published-package abstraction: satellite repos now depend on SDK source structure, not just the published interface.
- Version pinning becomes "which commit of the monorepo" rather than "which published version."

**Risk Reduction**: Complete. Eliminates CodeArtifact entirely from build path. All source is local.

**Verdict: Hold**. Same problem as vendored wheels but worse: higher git complexity, worse developer experience, and breaks the clean separation between SDK producer and consumer. The `Dockerfile.dev` pattern (volume-mount SDKs for local dev) is the right scope for this approach -- extending it to CI and production creates more problems than it solves.

---

## Comparison Matrix

| Criteria | Status Quo (CodeArtifact only) | 5. CI Cache (Adopt) | 1. Multi-Registry (Assess) | 4. Git-Based (Assess) | 2. Vendored Wheels (Hold) | 6. Path Deps (Hold) | 3. Registry Mirror (Avoid) |
|----------|-------------------------------|---------------------|---------------------------|----------------------|--------------------------|---------------------|---------------------------|
| **Resilience: CodeArtifact down** | Total failure | Builds with no dep changes succeed | Partial (404 only, not timeouts) | Full (GitHub as provider) | Full (no network needed) | Full (no network needed) | Partial (if mirror synced) |
| **Resilience: Token expiry** | Total failure | Builds with cached deps succeed | Fails (same IAM role) | Unaffected (GitHub token) | Unaffected | Unaffected | Unaffected |
| **Implementation effort** | N/A | 1-2 hours | 2-3 days | 1 day (break-glass doc) | 3-5 days + ongoing | 3-5 days + ongoing | 1-2 weeks + ongoing |
| **Ongoing maintenance** | None | None | Dual-publish CI, dual auth | Tag discipline | Wheel update automation | Subtree/submodule sync | Server ops, monitoring |
| **Build time impact** | Baseline (re-downloads every run) | Much faster (cache hit) | Same or slower (fallback delay) | Slower (git clone) | Faster (local wheels) | Fastest (local source) | Same or faster (local mirror) |
| **uv compatibility** | Native | Native | Native with caveats | Native with known issues | Supported, rough edges | Native | Native |
| **Team size fit (small)** | Acceptable | Excellent | Acceptable | Acceptable | Poor | Poor | Poor |
| **New infrastructure** | None | None | Second registry | None | Automation scripts | None | Server + monitoring |

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CodeArtifact outage blocks all builds | Low (1 known incident Feb 2025) | Critical (all repos blocked) | Adopt CI caching to reduce surface; document break-glass git fallback |
| CodeArtifact token expiry blocks installs | Medium (12-hour token lifetime) | High (all CI jobs fail until refresh) | CI caching means token only needed for cache misses; consider longer-lived tokens |
| uv cache miss during CodeArtifact outage | Low (only when deps change + outage) | Medium (single PR blocked) | Acceptable risk -- cannot upgrade deps without a registry |
| CI cache eviction (10GB GitHub limit) | Low-Medium | Low (re-downloads once) | Use `uv cache prune --ci`; key on `uv.lock` hash for efficient invalidation |
| CodeArtifact proxying all PyPI packages | Medium (current lockfile shows this) | High (PyPI packages also blocked) | Ensure `default = true` on PyPI index; verify uv resolves non-pinned packages from PyPI directly |

## Fit Assessment

- **Philosophy Alignment**: The layered approach (cache first, assess fallback) matches the "reality-scoped, proven patterns, small team" constraint. No new infrastructure, no new operational burden.
- **Stack Compatibility**: All recommended changes work with existing uv configuration. The `tool.uv.sources` pinning pattern already in pyproject.toml is the correct foundation.
- **Team Readiness**: CI cache configuration is a YAML change, not a new technology to learn. Break-glass documentation is a 1-page runbook.

## Recommendation

### Verdict: Adopt (CI Cache Hardening) + Assess (Multi-Registry Fallback + Git Break-Glass)

### Rationale

The risk is real but infrequent. The highest-ROI mitigation is enabling uv caching in CI, which:
1. Eliminates 95%+ of CodeArtifact requests (only cache misses hit the registry).
2. Makes routine builds immune to CodeArtifact outages.
3. Significantly speeds up CI (no re-downloading 109 packages every run).
4. Costs nothing in operational overhead.
5. Can be implemented in under 2 hours.

### Next Steps

1. **Immediate (Adopt)**: Enable `enable-cache: true` in `astral-sh/setup-uv` across all workflows. Add `uv cache prune --ci` step. Verify cache hit rates after 1 week.

2. **Short-term (Assess, 1-2 days)**: Investigate whether the lockfile resolving ALL packages through CodeArtifact (including PyPI packages) is intentional or a misconfiguration. If CodeArtifact is configured as an upstream proxy for PyPI, consider whether to keep that or split resolution so only autom8y-* packages go through CodeArtifact.

3. **Short-term (Assess, 1 day)**: Write a break-glass runbook documenting how to switch `tool.uv.sources` to git-based resolution if CodeArtifact is down for an extended period. This is a documented procedure, not a permanent configuration change.

4. **Deferred (Assess trigger: >2 CodeArtifact outages in 90 days)**: Evaluate dual-publishing to a second registry. Only worth the ongoing maintenance cost if outages become frequent enough to justify it.

### What We Explicitly Do NOT Recommend

- Self-hosted mirrors (operational burden exceeds risk for this team size).
- Vendored wheels (maintenance overhead across N satellite repos is unsustainable).
- Git subtrees/submodules for production builds (breaks producer/consumer separation).
- Changing the primary distribution mechanism away from CodeArtifact (it works, it just needs a safety net).

---

## Sources

- [uv Package Indexes Documentation](https://docs.astral.sh/uv/concepts/indexes/)
- [uv Managing Dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/)
- [uv GitHub Actions Integration](https://docs.astral.sh/uv/guides/integration/github/)
- [uv Caching](https://docs.astral.sh/uv/concepts/cache/)
- [astral-sh/setup-uv GitHub Action](https://github.com/astral-sh/setup-uv)
- [AWS CodeArtifact SLA](https://aws.amazon.com/codeartifact/sla/)
- [AWS CodeArtifact Status History](https://statusgator.com/services/amazon-web-services/aws-codeartifact)
- [uv Issue #15519: Offline sync with --frozen --no-index](https://github.com/astral-sh/uv/issues/15519)
- [uv Issue #5851: Lock --locked false positives with git deps](https://github.com/astral-sh/uv/issues/5851)
- [uv Issue #12362: Prevent fallback to PyPI on 401/403](https://github.com/astral-sh/uv/issues/12362)
- [devpi-server on PyPI](https://pypi.org/project/devpi-server/)
- [hynek/setup-cached-uv](https://github.com/hynek/setup-cached-uv)
- [Plotly: uv Package Manager Quirks](https://plotly.com/blog/uv-python-package-manager-quirks/)
