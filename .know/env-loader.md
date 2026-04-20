---
domain: env-loader
generated_at: "2026-04-20T00:00:00Z"
expires_after: "90d"
source_scope:
  - "scripts/a8-devenv.sh"
  - ".env/defaults"
  - ".env/local.example"
  - "secretspec.toml"
  - "src/autom8_asana/metrics/__main__.py"
  - ".ledge/decisions/ADR-env-secret-profile-split.md"
  - ".ledge/decisions/ADR-bucket-naming.md"
generator: janitor
source_hash: "HEAD@hygiene/sprint-env-secret-platformization"
confidence: 0.92
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Env Loader Contract

**Project**: autom8y-asana  
**Canonical source**: `scripts/a8-devenv.sh:_a8_load_env` (ecosystem monorepo, `/Users/tomtenuta/Code/a8/scripts/a8-devenv.sh`, lines 310-417)  
**Sprint**: hygiene/sprint-env-secret-platformization, CFG-008

---

## 6-Layer Precedence Table

The `_a8_load_env` shell function (lines 327-417 of `a8-devenv.sh`) loads environment variables in a fixed 6-layer order. **Later layers override earlier layers.** The table below maps each layer to its file path, commit status, encryption status, typical contents, and the exact line range in the canonical loader where it is sourced.

| Layer | File path | Committed? | Encrypted? | Typical contents | `a8-devenv.sh` line |
|-------|-----------|-----------|-----------|-----------------|---------------------|
| 1 | `.a8/{org}/env.defaults` (e.g., `.a8/autom8y/env.defaults`) | Yes | No | Ecosystem-wide non-secrets: log level, debug flag, Grafana/Tempo/Loki endpoints. Shared across all autom8y-* satellites. | 364 |
| 2 | `.a8/{org}/secrets.shared` (e.g., `.a8/autom8y/secrets.shared`) | Yes | Yes (dotenvx) | Ecosystem-wide encrypted secrets: shared service tokens, cross-satellite credentials. | 374 |
| 3 | `{repo}/.env/defaults` | Yes | No | Project-specific non-secrets: S3 bucket name, S3 region, environment name. These are safe-to-commit defaults for fresh-clone ergonomics. | 377 |
| 4 | `{repo}/.env/secrets` | Yes | Yes (dotenvx) | Project-specific encrypted secrets: per-project tokens and credentials that are committed in encrypted form. | 385 |
| 5 | `{repo}/.env/{env}` (e.g., `.env/local`) | No (gitignored) | No | Developer-local overrides: personal PAT, workspace GID, bucket override for personal dev environments. Never committed. | 388 |
| 6 | `.envrc.local` | No (gitignored) | No | Shell-level overrides: sourced by direnv at the end of `.envrc` via `_a8_use_handler`. Last-writer wins. | 406 |

**Note on Layer 5 naming**: The env file loaded is `.env/${resolved}` where `resolved` is the active environment name (default: `local`). For most developer workflows, Layer 5 is `.env/local`. The `.env/local.example` file (committed) is the template devs copy to create their Layer-5 file.

**Note on the legacy `.env/shared` path**: Lines 397-404 of `a8-devenv.sh` source `.env/shared` if present for backward compatibility during satellite migration. This is not a numbered layer — it is a deprecated fallback sourced between Layers 5 and 6. New repos must not use `.env/shared`; existing repos using it should migrate to the defaults+secrets split.

---

## Cross-Links

| System | Location | Role |
|--------|----------|------|
| Canonical loader | `/Users/tomtenuta/Code/a8/scripts/a8-devenv.sh:310-417` | Defines the 6-layer load order (`_a8_load_env`) |
| Layer 3 defaults | `.env/defaults` | Committed project non-secrets; S3 cache vars live here (post CFG-001). Header comment at lines 1-9 cites layer number and `a8-devenv.sh` line ranges. |
| Layer 5 template | `.env/local.example` | Developer onboarding template (copy to `.env/local`). Header block at lines 16-28 renders the full 6-layer table for devs. |
| Secret contract (default profile) | `secretspec.toml:[profiles.default]` | Lib-mode (FastAPI, Lambda, embedded SDK): all S3 cache vars optional. |
| Secret contract (CLI profile) | `secretspec.toml:[profiles.cli]` | CLI/offline mode (`python -m autom8_asana.metrics`): S3 bucket and region promoted to `required = true`. Defined under ADR-0001. |
| Validate lib-mode | `secretspec check --config secretspec.toml --provider env` | Checks `[profiles.default]` contract |
| Validate CLI mode | `secretspec check --config secretspec.toml --provider env --profile cli` | Checks `[profiles.cli]` contract |
| CLI preflight | `src/autom8_asana/metrics/__main__.py:18-60` | Subprocess-first `secretspec check --profile cli` with inline fallback when binary absent. Exit code 2 on contract violation. |
| Profile split ADR | `.ledge/decisions/ADR-env-secret-profile-split.md` (ADR-0001) | Architectural decision authorizing the default/cli profile split. |
| Bucket naming ADR | `.ledge/decisions/ADR-bucket-naming.md` (ADR-0002) | Canonical decision: `autom8-s3` is the dev/local S3 cache bucket. See section below. |
| Smell inventory | `.ledge/reviews/smell-inventory-env-secrets-2026-04-20.md` | Original detection document surfacing Drifts 1-3. |
| Upstream handoff | `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md` | Root cause analysis and CFG item descriptions. |

---

## Worked Example: `ASANA_CACHE_S3_BUCKET`

This variable is the compound-signal locus of the Sprint-C platformization work — it appears in four distinct configuration concerns simultaneously. Walking through each layer explains why the current placement is correct and what would break if the variable were moved.

### Layer 3: `.env/defaults` (the right layer for this variable)

`ASANA_CACHE_S3_BUCKET=autom8-s3` lives at `.env/defaults:21` (post CFG-001). This is Layer 3 in the loader.

**Why Layer 3 and not Layer 1** (`.a8/autom8y/env.defaults`): Layer 1 is for ecosystem-wide non-secrets shared across all autom8y-* satellites. `ASANA_CACHE_S3_BUCKET` is specific to autom8y-asana's S3 cache subsystem. Placing it in Layer 1 would incorrectly propagate a project-specific bucket name to every satellite that sources the ecosystem defaults. Layer 3 is the correct boundary for project-specific committed defaults.

**Why Layer 3 and not Layer 4** (`.env/secrets`, encrypted): The bucket name is not a secret. It is safe-to-commit configuration that belongs alongside `ASANA_CW_ENVIRONMENT` in the plain-text committed defaults file. Layer 4 is reserved for credentials (tokens, keys) that require dotenvx encryption.

**Fresh-clone ergonomics**: After a `git clone` + `direnv allow`, Layer 3 auto-exports `ASANA_CACHE_S3_BUCKET=autom8-s3` to the shell environment without any manual `export` statement or `.env/local` edit. This makes `python -m autom8_asana.metrics active_mrr` work zero-touch for non-secret paths (the original motivation for CFG-001).

### Layer 5: `.env/local` (developer override path)

`.env/local.example:51` shows the commented-out override:

```sh
# Uncomment to override Layer 3 default `autom8-s3` -- see .env/defaults
# ASANA_CACHE_S3_BUCKET=your-personal-dev-bucket
```

A developer targeting a personal bucket (e.g., a LocalStack instance with a different name, or a team-member's isolated dev bucket) can override the Layer-3 default by editing their `.env/local` without touching the committed `.env/defaults`. Layer 5 wins over Layer 3 because later layers override earlier ones.

### secretspec.toml: profile split (ADR-0001)

The variable appears twice in `secretspec.toml`, once per profile:

- **`[profiles.default]`** — `required = false`. Lib-mode callers (FastAPI server, Lambda handlers, embedded SDK) degrade to memory-only cache when the bucket is absent. This is correct and intentional: absent S3 config is not a contract violation for lib-mode.
- **`[profiles.cli]`** — `required = true`. CLI paths (`python -m autom8_asana.metrics`) hit S3 unconditionally on first call. Absence at this layer is a contract violation, not a graceful degradation.

The promotion from optional to required under the CLI profile is the architectural decision from ADR-0001 (`.ledge/decisions/ADR-env-secret-profile-split.md`). It trades lax documentation (the old `required = false` was a lie for CLI workflows) for actionable preflight failure.

### CFG-006 preflight: fail-fast at the CLI boundary

`src/autom8_asana/metrics/__main__.py:18-60` implements the CLI preflight (Alternative C, per TDD-0001-cli-preflight-contract). Before `load_project_dataframe` is called, the entrypoint runs:

1. `secretspec check --config secretspec.toml --provider env --profile cli` via subprocess.
2. If the `secretspec` binary is absent, falls back to the inline `_preflight_inline_fallback()` check against `_CLI_REQUIRED = ("ASANA_CACHE_S3_BUCKET", "ASANA_CACHE_S3_REGION")`.

If `ASANA_CACHE_S3_BUCKET` is unset or empty, the preflight exits with code 2 and emits a structured error pointing to `.env/defaults`, `.env/local.example`, and `secretspec.toml` with explicit file paths. This replaces the previous opaque transport error (`No S3 bucket configured. Pass bucket= or set ASANA_CACHE_S3_BUCKET.`) that surfaced deep in the S3 transport layer rather than at the CLI boundary.

### Why the value is `autom8-s3` and not `autom8y-s3`

See the canonical bucket naming decision below and ADR-0002 (`.ledge/decisions/ADR-bucket-naming.md`). Short answer: `autom8-s3` is the legacy, load-bearing, live-data bucket. `autom8y-s3` is an empty sibling that has zero code references and no data.

---

## Canonical S3 Bucket Name

**Decision**: ADR-0002 (`.ledge/decisions/ADR-bucket-naming.md`), adopted 2026-04-20.

### `autom8-s3` is canonical

For all autom8y-asana consumers (dev/local, CI, Lambda staging, Lambda production, LocalStack), the S3 cache bucket name is:

> **`autom8-s3`** (legacy, no `y`) — canonical

The naming predates the `autom8y-*` ecosystem-prefix convention. The canonical decision was ratified by the ecosystem monorepo service manifest at `/Users/tomtenuta/Code/a8/manifest.yaml:476` (`ASANA_CACHE_S3_BUCKET: "autom8-s3"`) and is consistent with every in-repo code reference (grep audit at ADR authorship time found zero references to `autom8y-s3` in any code path).

### `autom8y-s3` is a non-canonical empty alias

The bucket `autom8y-s3` exists in AWS but is empty and has zero code references. It should **not** receive new writes. A developer who discovers it and assumes it is the "org-branded correct target" will get an empty result set rather than an actionable error. This is the latent confusion source that ADR-0002 documents and this `.know/` entry disambiguates.

Do not change `ASANA_CACHE_S3_BUCKET` to `autom8y-s3` without first superseding ADR-0002.

### Load-bearing references for `autom8-s3`

Future architects planning any bucket rename must update all of these sites:

| Reference | Kind | Scope |
|-----------|------|-------|
| `docker-compose.override.yml:33` | Runtime env | LocalStack dev bucket (single-repo) |
| `.env/defaults:21` | Layer 3 committed default | Single-repo |
| `src/autom8_asana/lambda_handlers/checkpoint.py:29` | `DEFAULT_BUCKET = "autom8-s3"` constant | Production Lambda (cross-env) |
| `src/autom8_asana/lambda_handlers/checkpoint.py:11,148` | Docstring references | Production Lambda (cross-env) |
| `src/autom8_asana/lambda_handlers/cache_warmer.py:273` | `or "autom8-s3"` fallback expression | Production Lambda (cross-env) |
| `/Users/tomtenuta/Code/a8/manifest.yaml:476` | Ecosystem monorepo service manifest | Cross-repo (outside this repo's commit boundary) |

These were surfaced by the ADR-0002 investigation (grep audit, 2026-04-20). Any future rename crosses into SRE territory (live-data migration) which is explicitly out of hygiene scope per the upstream handoff (`HANDOFF-eunomia-to-hygiene-2026-04-20.md:181`).

---

## Knowledge Gaps

1. **Layer 2 (`secrets.shared`) contents for autom8y-asana**: The encrypted `.a8/autom8y/secrets.shared` file is not decryptable in a read-only audit. Its contents are treated as opaque ecosystem-shared secrets. If a developer needs to know which secrets are injected at Layer 2, they must decrypt locally with the dotenvx key.
2. **Layer 4 (`.env/secrets`) contents**: Same constraint as Layer 2. The encrypted project secrets file is not auditable without the dotenvx key.
3. **`.env/current` interaction**: The `_a8_load_env` function reads `.env/current` (line 337) to determine the active environment name, which in turn determines the Layer-5 file path. This file is not described above because it is not one of the 6 loading layers — it is an environment selector, not a value source. However, devs who rename their environment (e.g., to `staging`) must be aware that Layer 5 becomes `.env/staging`, not `.env/local`.
