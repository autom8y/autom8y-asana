---
name: release-platform-profile-criteria
description: "Criteria for release platform profile knowledge capture. Use when: release specialists (cartographer, dependency-resolver) are producing .know/release/platform-profile.md documenting cached stable platform state. Triggers: release platform profile, release knowledge criteria, platform state caching, release reconnaissance."
---

# Release Platform Profile Criteria

> Grades the completeness of cached platform state knowledge. This is agent-produced knowledge (by release specialists, not theoros). The goal is to cache the stable 80% of platform reconnaissance so subsequent `/release` invocations skip redundant discovery.

## Scope

**Producer agents**: cartographer, dependency-resolver (release rite specialists)

**Target sources** (what specialists observe and cache):
- Repository manifests: `go.mod`, `package.json`, `pyproject.toml`, `Cargo.toml`
- Build/release configs: `.goreleaser.yaml`, `justfile`, `Makefile`, `Taskfile.yml`
- CI pipeline definitions: `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`
- Distribution metadata: npm registry configs, Go module proxy, container registries
- Cross-repo dependency declarations: workspace files, go.work, pnpm-workspace.yaml

**Knowledge focus**: Produce a platform profile that enables a release specialist to skip reconnaissance of stable platform state. The profile must answer: What repos exist? What ecosystem is each repo? What are the distribution channels? What pipeline chains exist?

**NOTE**: This domain uses knowledge-capture grading. Grade the COMPLETENESS of the cached state, NOT the quality of the platform itself. A = "a release specialist reading only this file could skip full reconnaissance." F = "the specialist must re-discover platform state from scratch."

## Criteria

### Criterion 1: Repository Ecosystem Map (weight: 35%)

**What to capture**: Every repo in the platform with its detected ecosystem type, primary language, build system, and distribution type.

**Evidence required**:
- Repo name/path and ecosystem classification (Go module, npm package, Python package, container, static site, etc.)
- Build tool detection (goreleaser, npm publish, twine, docker build, etc.)
- Distribution channel (npm registry, Go proxy, container registry, GitHub releases, etc.)
- Version strategy (semver, calver, git tag, etc.)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All repos enumerated with ecosystem, build tool, distribution channel, and version strategy. Cross-validated against actual configs. |
| B | 80-89% | Most repos enumerated with ecosystem. Some missing build tool or distribution detail. |
| C | 70-79% | Repos listed but ecosystem classification incomplete for several. |
| D | 60-69% | Partial repo list. Several repos missing or misclassified. |
| F | < 60% | Repo enumeration too incomplete for release planning. |

---

### Criterion 2: Pipeline Chain Discovery (weight: 25%)

**What to capture**: CI/CD pipeline definitions for each repo — what triggers builds, what stages exist, what artifacts are produced, what deployment targets are configured.

**Evidence required**:
- Pipeline file paths and trigger conditions (push, tag, release, manual)
- Stage/job names and their purposes
- Artifact outputs (binaries, packages, containers, checksums)
- Cross-repo pipeline dependencies (repo A's pipeline triggers repo B's)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All pipeline files discovered with triggers, stages, artifacts, and cross-repo dependencies mapped. |
| B | 80-89% | Pipeline files discovered for most repos. Triggers and stages documented. Some artifact or cross-repo gaps. |
| C | 70-79% | Pipeline files listed but stages or triggers incomplete for several repos. |
| D | 60-69% | Partial pipeline discovery. Major repos missing. |
| F | < 60% | Pipeline discovery too incomplete for release orchestration. |

---

### Criterion 3: Dependency Topology (weight: 25%)

**What to capture**: The directed acyclic graph (DAG) of cross-repo dependencies — which repos depend on which, what the publish order must be, where parallel groups exist.

**Evidence required**:
- Dependency edges with version constraints (repo A depends on repo B at version range X)
- Topologically sorted publish order
- Parallel group identification (repos at the same DAG level can release simultaneously)
- Circular dependency detection (if any, with severity assessment)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | Complete DAG with all edges, publish order, parallel groups, and cycle detection. Cross-validated against actual dependency declarations. |
| B | 80-89% | DAG mostly complete. Publish order correct. Some parallel grouping gaps. |
| C | 70-79% | Major dependencies captured but DAG has gaps. Publish order approximate. |
| D | 60-69% | Partial dependency map. Publish order unreliable. |
| F | < 60% | Dependency topology too incomplete for safe release ordering. |

---

### Criterion 4: Configuration Artifacts (weight: 15%)

**What to capture**: Build configuration details that are stable between releases — justfile targets, goreleaser config structure, makefile targets, environment requirements.

**Evidence required**:
- Justfile/Makefile target inventory per repo (build, test, lint, release targets)
- Goreleaser config structure (builds, archives, release settings)
- Required environment variables for release (tokens, registry credentials — names only, not values)
- Pre-release checks or gates (test suites, lint passes, changelog requirements)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All build configs inventoried with targets, settings, and environment requirements. |
| B | 80-89% | Most build configs documented. Some environment requirements missing. |
| C | 70-79% | Build configs listed but target inventory incomplete. |
| D | 60-69% | Partial config documentation. Major repos missing. |
| F | < 60% | Config documentation too sparse to avoid re-scanning. |
