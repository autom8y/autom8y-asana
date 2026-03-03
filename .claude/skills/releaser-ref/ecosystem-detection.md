---
name: ecosystem-detection
description: "Ecosystem Detection Matrix and Publish Order Protocol for the releaser rite. Covers manifest-to-ecosystem mapping (Python/Node/Go/Rust), publish commands, and topological sort rules for multi-repo publish ordering. Read when: detecting package ecosystems from manifest files, determining publish order across repos, or reasoning about parallel vs sequential publish phases."
---

# Ecosystem Detection Matrix

| Manifest File | Ecosystem | Package Manager | Publish Command (typical) | Distribution Type (default) |
|---------------|-----------|-----------------|--------------------------|----------------------------|
| `pyproject.toml` | Python | uv | `uv publish` or justfile target | registry |
| `package.json` | Node | npm | `npm publish` or justfile target | registry |
| `go.mod` | Go | go | `git tag v{version} && git push origin v{version}` | registry (default; binary when `.goreleaser.yaml` present) |
| `Cargo.toml` | Rust | cargo | `cargo publish` or justfile target | registry |

Multiple manifest files in one repo = ambiguous ecosystem; escalate to Pythia.
Always detect ecosystem per-repo from manifest files. Never assume uniformity.

> **Go binary vs Go module**: Both use `go.mod` as the manifest and are classified as `go_mod` ecosystem. The distinction is `distribution_type`, not ecosystem. `go.mod` + `.goreleaser.yaml` present = `distribution_type: binary` (binary distribution via GoReleaser to GitHub Releases + Homebrew). `go.mod` alone = `distribution_type: registry` (Go module proxy — push a tag and the proxy indexes it automatically; verify with `go list -m -versions {module}@{version}`). These are the same ecosystem with different distribution types — do NOT create a separate ecosystem for binary Go repos.

# Distribution Type Detection

`distribution_type` is orthogonal to ecosystem. It governs HOW artifacts reach consumers, not what language they use.

| Condition | Distribution Type | Notes |
|-----------|------------------|-------|
| `.goreleaser.yaml` or `.goreleaser.yml` present | `binary` | GoReleaser takes precedence over registry publish |
| Manifest file present + no goreleaser | `registry` | Default; existing publish command model unchanged |
| Manifest + goreleaser | `binary` | GoReleaser overrides ecosystem default |
| Dockerfile + GHCR/DockerHub publish target | `container` | Stub — not yet supported; escalate to user |

Detection priority: `binary` (goreleaser present) > `container` (Dockerfile + publish target) > `registry` (default).

All existing `registry` behavior is unchanged. Distribution type only adds conditional logic for `binary` and `container` paths.

# Publish Order Protocol

Topological sort rules:
1. Foundations (no cross-repo dependencies) publish first, in parallel
2. Each subsequent phase depends on all repos in prior phases being published
3. Within a phase, repos with no dependency relationship may publish in parallel
4. Consumer version bumps happen AFTER the dependency's publish is confirmed — never before

Parallel group constraints:
- Two repos may share a phase only if neither depends on the other (directly or transitively)
- If uncertain, be conservative: sequential is safe, incorrect parallel causes failures
