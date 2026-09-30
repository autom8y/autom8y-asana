---
domain: env-loader
generated_at: "2026-09-30T00:00:00Z"
expires_after: "90d"
source_scope:
  - "scripts/a8-devenv.sh"
  - ".a8-credentials"
  - ".env/defaults"
  - ".env/local.example"
  - "justfile"
  - "secretspec.toml"
  - "src/autom8_asana/metrics/__main__.py"
  - ".ledge/decisions/ADR-env-secret-profile-split.md"
  - ".ledge/decisions/ADR-bucket-naming.md"
generator: tech-writer
source_hash: "fdbf359f95115e6958c6c085b10ed9a2b36e6dda + stdlib a8-devenv@1162145dd"
confidence: 0.85
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Env Loader Contract

**Project**: autom8y-asana  
**Canonical source**: `scripts/a8-devenv.sh:_a8_load_env` (ecosystem stdlib, `/Users/tomtenuta/Code/a8/a8-devenv/scripts/a8-devenv.sh`). Line numbers are omitted on purpose: they drift. Search the file by function name.  
**Provenance**: hygiene/sprint-env-secret-platformization (CFG-008); rewritten for the declared credential loader by the worktree-credential-substrate initiative.

This file is the operator surface for asana credentials. Recipe output, runbooks and the `.a8-credentials` header all point here. It is deploy-exempt, so a prose fix costs no ECS roll.

---

## Start here: which credential path is this tree on?

asana reads `ASANA_PAT` and `ASANA_WORKSPACE_GID` from a **declared loader**. The older `.env/local` copy still exists and is **LEGACY**.

| You see | It means | Go to |
|---|---|---|
| `just check-env` prints `ASANA_PAT: set (substrate-marked)` | The loader served the value (set and not `0`, possibly expired, which is what the recipe prints), or the process inherited a companion from a parent | [Reading the companion](#reading-the-companion-fresh-eval) |
| `... set (not substrate: withheld or shadowed)` | The loader withheld the value, a pre-existing value accompanies a withhold, or a later layer overrode a served value | [Who fixes what](#who-fixes-what-the-owner-and-producer-map). Only for `not-found` before the mint, also [Legacy path and bridge window](#legacy-path-fetch-secrets-and-layer-5) |
| `... set (not substrate: no companion)` | The value came from somewhere else (legacy copy, hand export, or the tree is out of scope) | The [fresh-eval check](#reading-the-companion-fresh-eval) first, then [Legacy path and bridge window](#legacy-path-fetch-secrets-and-layer-5) |
| `ASANA_PAT: missing` | Nothing supplied the value | [Reading the companion](#reading-the-companion-fresh-eval), then [Who fixes what](#who-fixes-what-the-owner-and-producer-map) |
| A withhold line on stderr naming a cause (exact wording: the rendering from the a8-devenv stdlib at commit `1162145dd`, provisional until the stdlib release is pinned, and re-verified then; golden `test/devenv/fixtures/voice/c3-voice.golden`, sha256 prefix `3929407c`. Line shape: `<org>: WARNING: CREDENTIAL WITHHELD: <VAR> (<cause>) -- <fix> (DC-n)`) | The loader refused to export one variable | [Who fixes what](#who-fixes-what-the-owner-and-producer-map) |
| `fetch-secrets: REFUSED` | The legacy recipe found `A8_CRED_VERSION_ASANA_PAT` set and not `0` in its own environment, and stopped | [Legacy path and bridge window](#legacy-path-fetch-secrets-and-layer-5) |
| `Written: .env/local (1 name; skipped, companion set and not 0: ASANA_WORKSPACE_GID)` | The legacy recipe wrote the PAT only. The GID is served here, so it was skipped | [Legacy path and bridge window](#legacy-path-fetch-secrets-and-layer-5) |

**Two rules that prevent the common mistakes:**
1. Agents never run `direnv exec` and never run `direnv allow`. Steps marked **OPERATOR** are the operator's.
2. **Never delete your `.env/local` credential until a fresh eval in that tree reads `<v>:<exp>` with `exp` in the future.** Until then it is the only working copy, even when a line reads `(<cause>, shadowed)`. See [Do not delete your `.env/local` until the fresh eval serves](#do-not-delete-your-envlocal-until-the-fresh-eval-serves).

---

## The declared loader: `.a8-credentials`

asana declares its credentials in one committed file at the repo root: **`.a8-credentials`**.

```text
# Credential coordinates for this repo, never values. Owner and producer: see .know/env-loader.md
ASANA_PAT|ssm|asana/asana-pat
ASANA_WORKSPACE_GID|ssm|asana/asana-workspace-gid
```

**What it declares.** Two names and two SSM coordinates. It never holds a value.

| ENV_VAR | Store | Coordinate (relative to `${_A8_SSM_PREFIX}/platform/`) |
|---|---|---|
| `ASANA_PAT` | `ssm` | `asana/asana-pat` |
| `ASANA_WORKSPACE_GID` | `ssm` | `asana/asana-workspace-gid` |

The TTL field is omitted, so the effective TTL is 86400 seconds (24 hours). The stdlib applies no clamp. The rotation overlap is an operator record (at least 24 h, which is at least the TTL), not something the stdlib enforces.

**How it loads.** Inside `use autom8y`, right after the org-secrets loader. **No `.envrc` change is needed or made.** The stdlib reads exactly `<repo root>/.a8-credentials`. It never globs and never walks above the repo root.

**Rules for the file:**
- **Maintainer rule (provisional; it binds once the `--check` lint is built and the stdlib release is pinned).** `--check` also fails a `#` comment line that contains `=` (a URL with a query string, for example). Keep the header of `.a8-credentials` free of `=`.
- The stdlib rejects malformed lines as `declaration-invalid` (fields, separator, `#` placement, BOM, trailing whitespace). Fields are `ENV_VAR|STORE|SOURCE_COORD` with an optional fourth `|TTL`; the separator is `|`. Line 1 is a `#` comment pointing here. Use LF endings and a final newline (a CR is stripped, not rejected).
- The loader accepts only a regular, non-symlink file at the exact name and ignores the execute bit. Keep mode 100644. `--check` enforces it once that check is built.
- Do not add other trust-checked files in the same change. `.a8-credentials` is one of the files the worktree trust check compares (see `ari worktree trust show <path>`): editing it (or `.env/defaults`, `.env/local.example`, `devbox.json`, `devbox.lock`, mise config, `.envrc`) changes what every pre-merge tree must re-allow.

**Where values come from.** `ASANA_PAT` is production's Secrets Manager secret `autom8y/asana/asana-pat`, mirrored by its rotation authority to the SSM coordinate above. The GID is the same, from `autom8y/asana/asana-workspace-gid`. The coordinate must be a `SecureString`; anything else is withheld as `insecure-type`.

---

## 6-Layer Precedence Table

The `_a8_load_env` shell function loads environment variables in a fixed 6-layer order. **Later layers override earlier layers.** The declared loader above runs after layer 5 (which `_a8_load_env` sources) and before layer 6 (`.envrc.local`). Inside the TTL, a served declared value overrides layer 5 and any inherited value.

| Layer | File path | Committed? | Encrypted? | Typical contents |
|-------|-----------|-----------|-----------|-----------------|
| 1 | `.a8/{org}/env.defaults` (e.g., `.a8/autom8y/env.defaults`) | Yes | No | Ecosystem-wide non-secrets: log level, debug flag, Grafana/Tempo/Loki endpoints. Shared across all autom8y-* satellites. |
| 2 | `.a8/{org}/secrets.shared` (e.g., `.a8/autom8y/secrets.shared`) | Yes | Yes (dotenvx) | Ecosystem-wide encrypted secrets: shared service tokens, cross-satellite credentials. |
| 3 | `{repo}/.env/defaults` | Yes | No | Project-specific non-secrets: S3 bucket name, S3 region, environment name. Safe-to-commit defaults for fresh-clone ergonomics. |
| 4 | `{repo}/.env/secrets` | Yes | Yes (dotenvx) | Project-specific encrypted secrets committed in encrypted form. |
| 5 | `{repo}/.env/{env}` (e.g., `.env/local`) | No (gitignored) | No | Developer-local overrides. **For credentials this layer is LEGACY (pre-substrate):** asana's PAT and workspace GID now come from the declared loader. Non-credential overrides (for example a personal S3 bucket) remain valid here. Never committed. |
| 6 | `.envrc.local` | No (gitignored) | No | Shell-level overrides: sourced by direnv at the end of `.envrc` via `_a8_use_handler`. Last-writer wins. |

**Note on Layer 5 naming**: The env file loaded is `.env/${resolved}` where `resolved` is the active environment name (default: `local`). For most developer workflows, Layer 5 is `.env/local`.

**Layer 5 is legacy for asana credentials.** The committed `.env/local.example` template still tells developers to paste a PAT and GID into `.env/local`. That guidance is the pre-substrate path. It stays in place for now because the template is one of the files the worktree trust check compares (editing it re-opens every tree's allow). Do not paste credentials; `.a8-credentials` supplies them. On a withhold, see [Who fixes what](#who-fixes-what-the-owner-and-producer-map). Use the [legacy recipe](#legacy-path-fetch-secrets-and-layer-5) only in the bridge window.

**Shadowing.** The loader reports `shadowed` in two forms, and the companion reads `0` for both. (1) A withhold finds a value already present (layer 5, the org layer, or the inherited environment): the cause reads `(<cause>, shadowed)` and the fix slot is that cause's own fix. (2) A later layer (`tf-bridge`, `tool-tokens`, `venv` or `.envrc.local`; only `.envrc.local` is layer 6) overrides a served value: a bare `shadowed` that names the layer to remove the name from. After a serve, layer 5 is overridden silently and prints nothing. A `(<cause>, shadowed)` line during the bridge window is expected; see the warning below.

---

## Reading the companion (fresh eval)

For every declared name, the loader exports a **version companion**: `A8_CRED_VERSION_<ENV_VAR>`. For the PAT it is `A8_CRED_VERSION_ASANA_PAT`.

- Served: `<ssm-version>:<expiry-epoch>`.
- Every withhold, and `shadowed`: exactly `0`.
- The companion is not a secret. It never contains a value.

**A companion in your shell is not proof about your current tree.** A process launched in a declaring primary checkout carries its companion into a hand-typed worktree, and a running process keeps its launch environment. To decide for one tree, run a fresh evaluation in that tree with the variable and its companion unset first.

> **OPERATOR ACTION.** Agents never run `direnv exec`.
>
> ```bash
> env -u ASANA_PAT -u A8_CRED_VERSION_ASANA_PAT direnv exec . printenv A8_CRED_VERSION_ASANA_PAT
> ```
>
> Run it from the tree's root. Compare the expiry epoch to `date +%s`.

| Output | Meaning | What to do |
|---|---|---|
| `<v>:<exp>` and `exp` **greater than** now | **Served.** The loader supplied a live value in this tree, as of the loader's exit; a later `.envrc` line, mise `[env]` or hook is outside that attestation. | Nothing. Do not run `fetch-secrets`. |
| `<v>:<exp>` and `exp` **at or before** now | **Stale.** Treat as **not served.** | Refresh with the verify verb ([below](#operator-verbs-verify-and-fill)), then `direnv reload` (**OPERATOR**) and this check. |
| `0` | **Withheld in scope.** The loader tried and withheld the value, or served it and a later layer then overrode it. | Read the withhold line for the cause; see [Who fixes what](#who-fixes-what-the-owner-and-producer-map). |
| unset or empty | **Out of scope or not declared.** | Check the caveat below before concluding. |

**Caveat: a blocked `.envrc` reads the same as unset.** When direnv has not allowed the tree, `direnv exec` exits 1 with empty stdout. Empty output then means the **trust gate refused**, not "out of scope". Do not follow direnv's suggested fix. Trust is the operator's decision, made on the tree's contents.

---

## Operator verbs: verify and fill

The stdlib runs as a script to refresh a declared credential. Both are **OPERATOR** actions and may call AWS.

```bash
/bin/bash <resolved a8.sh path> --verify <unit root> [ENV_VAR ...]
/bin/bash <resolved a8.sh path> --fill   <unit root> [ENV_VAR ...]
```

For asana, `<unit root>` is the repo root (the directory holding `.a8-credentials`). Name `ASANA_PAT` and `ASANA_WORKSPACE_GID` to limit the run, or omit the names.

| Verb | What it does | Use it when |
|---|---|---|
| `--verify` | Compares the cached version with a live metadata call. On STALE it drops the cache entry **and refetches in the same call**. It ignores any backoff marker. | The value looks stale, after a rotation, or after a withhold whose cause names verify (`store-unreachable`, `expired-unrefreshable`). |
| `--fill` | Fills the cache **only when the entry is expired or absent**. It makes no network call for an unexpired entry. | You need a value cached without forcing a live compare. |

**Argument grammar and exit codes.** Stdout is one `<ENV_VAR>: FRESH|STALE|UNKNOWN` line per reported variable. It never carries a value or a cache path. Stderr is fixed text only. These are from the stdlib at commit `1162145dd`, provisional until the stdlib release is pinned, and re-verified then.

| Exit | Meaning |
|---|---|
| 0 | Every reported variable is FRESH |
| 1 | `--verify` busted and refetched a STALE entry, and none is UNKNOWN |
| 2 | At least one variable is UNKNOWN |
| 64 | Usage: no unit root, a unit root starting with `-`, or an ENV_VAR argument that is not a valid name |
| 65 | No loadable declaration at the unit root: absent, not a regular file, a symlink, or the tree is outside the loader's scope rule |
| 66 | The unit root is not an accessible directory |
| 78 | Config resolution or the profile gate failed |

Exit 69 is reserved for `--check`, which fails closed until the `--check` lint lands. It is not a verb result.

**Locating `a8.sh`** (`<resolved a8.sh path>`). Resolve this path through symlinks:

```text
${DIRENV_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/direnv}/lib/a8.sh
```

`DIRENV_CONFIG` replaces the `.../direnv` directory itself, not the config root. Illustration only (the expression above is the pinned rule):

```bash
A8_LINK="${DIRENV_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/direnv}/lib/a8.sh"
A8_SH="$(/usr/bin/readlink -f "$A8_LINK")"
```

---

## Who fixes what: the owner and producer map

A withhold prints one line per variable. The line names the cause and, for some causes, a fix slot that reads **`operator: owner of <unit root>/.a8-credentials (DC-9)`**. The stdlib cannot print a producer name, because the declaration has no owner field. This table is where you resolve that line.

The path in that slot is printed with shell `%q` quoting. A plain path prints bare. A space prints as `\ `. A path containing a control byte prints whole as `$'…'`. Rendering depends on the locale, so never key a script on the quoting.

**Producer of both declared credentials:** the **rotation authority** that writes the SSM mirror. Under the dual-write rule it writes Secrets Manager first and the SSM mirror second, at mint and on every rotation, then reads the mirror back (metadata only).

| ENV_VAR (exact name in `.a8-credentials`) | Producer | Source, then mirror |
|---|---|---|
| `ASANA_PAT` | The rotation authority (dual-write) | Secrets Manager `autom8y/asana/asana-pat`, mirrored to `asana/asana-pat` |
| `ASANA_WORKSPACE_GID` | The same rotation authority | Secrets Manager `autom8y/asana/asana-workspace-gid`, mirrored to `asana/asana-workspace-gid` |

**"Owner of" means the declaration's owner, not the file's filesystem owner.** The owner is the producer above.

**Fix by cause** (the causes are a closed set; read your line's cause):

| Cause | First step | Then |
|---|---|---|
| `auth-expired` | **OPERATOR:** sign in to the resolved profile's SSO session, then reload the tree | Re-run the fresh-eval check |
| `store-unreachable`, `expired-unrefreshable` | **OPERATOR:** run the [verify verb](#operator-verbs-verify-and-fill) | Then `direnv reload` (OPERATOR) and the fresh-eval check |
| `not-found` | The `operator: owner of ... (DC-9)` line: the producer has not minted the mirror coordinate, or wrote it elsewhere. Ask the producer. | Pre-mint this is expected: see the [bridge window](#the-bridge-window-pre-mint) |
| `access-denied` | **First check the resolved profile's permission set (the profile `ecosystem.conf` selects); then the producer.** | The producer only fixes a wrong grant on the mirror side |
| `insecure-type` | The owner slot `operator: owner of <unit root>/.a8-credentials (DC-9): coordinate is not SecureString`. Ask the producer to rewrite it as `SecureString` under the mirror's KMS key. | Then run the verify verb, `direnv reload` (OPERATOR) and the fresh-eval check |
| `declaration-invalid` | Fix `.a8-credentials` at the line and field named. Check the [rules](#the-declared-loader-a8-credentials). | Editing that file re-opens the trust gate: this is a reviewed change, not a local tweak |
| bare `shadowed` | Arises only after a serve. The line names one layer (`.envrc.local`, `tf-bridge`, `tool-tokens` or `venv`). Remove the declared name from that layer. | Re-run the fresh-eval check |
| `(<any withhold cause>, shadowed)` | Take that cause's own fix slot (for `not-found`, the DC-9 owner slot; a duplicate declaration can print `(declaration-invalid, shadowed)`). It never names a layer. **Do not delete your `.env/local` value until a fresh eval reads `<v>:<exp>` with `exp` in the future**: see [Do not delete your `.env/local` until the fresh eval serves](#do-not-delete-your-envlocal-until-the-fresh-eval-serves). | Re-run the fresh-eval check |

**Exact wording of each line:** see the rendering from the a8-devenv stdlib at commit `1162145dd`, provisional until the stdlib release is pinned, and re-verified then (golden `test/devenv/fixtures/voice/c3-voice.golden`, sha256 prefix `3929407c`). This file does not reproduce the stdlib's full voice text. It quotes only the fixed fix slots below, and they match that golden.

| Cause | Fix slot printed after `--` |
|---|---|
| `auth-expired`, or `(auth-expired, shadowed)` | `aws sso login --profile <PROFILE> && direnv reload (DC-7)` |
| `store-unreachable`, `expired-unrefreshable` (bare, or as `expired-unrefreshable: store-unreachable`) | `/bin/bash <resolved a8.sh path> --verify <unit root> <VAR> (DC-8)` |
| bare `shadowed` | `operator: remove <VAR> from <layer> (DC-5)`, where `<layer>` is `.envrc.local`, `tf-bridge`, `tool-tokens` or `venv` |
| `declaration-invalid` | `.a8-credentials:<line> field <n> (DC-2)` for a duplicate, or, when the line's ENV_VAR is unvalidated or reserved, instead a standalone `<org>: WARNING: DECLARATION INVALID: .a8-credentials:<line> field <n>` line |

`expired-unrefreshable` prints as `(expired-unrefreshable: store-unreachable)`, or bare when another process holds the lock. Both take the verify fix.

**Credential values never appear** in any withhold line, in `check-env`, or in this file. Coordinates are named here because they are declared names.

---

## Legacy path: `fetch-secrets` and layer 5

Before the declared loader, developers ran `just fetch-secrets` to write the PAT and GID into `.env/local` (layer 5). That path is **LEGACY (pre-substrate)**. It is now guarded, writes per name, and is scheduled for retirement.

**The guard (operator word OW-3).** The recipe checks the companion by name. It refuses (exit 3, writes nothing, calls no AWS) when `A8_CRED_VERSION_ASANA_PAT` is **set and not exactly `0`**. An empty value counts as set. The check never reads a credential and never reads an expiry.

The guard reads the environment of **whoever runs the recipe**, not the tree. A served tree run from a shell without the direnv hook has no companion in that shell, so the recipe writes.

| Companion in the invoking environment | `just fetch-secrets` does |
|---|---|
| unset | Writes `.env/local` (mode 600). No note. |
| exactly `0` | Prints a NOTE that `.env/local` is a fallback copy, then writes it. |
| anything else (`<v>:<exp>`, expired or not, or empty) | **Refuses.** |

**Per-name write (OW-12).** When the recipe runs, it checks each name's own companion. It writes the PAT every time. It **skips the GID** when `A8_CRED_VERSION_ASANA_WORKSPACE_GID` is set and not exactly `0` (an empty value counts as set).

| PAT companion | GID companion | Prints |
|---|---|---|
| unset or `0` | unset or `0` | `Written: .env/local (2 names)` |
| unset or `0` | set and not `0` (served, or any other value, empty included) | `Written: .env/local (1 name; skipped, companion set and not 0: ASANA_WORKSPACE_GID)` |
| set and not `0` | any | Refuses before any write (see above) |

The recipe replaces the whole file, so an older copy's GID line is dropped when the GID is skipped. The NOTE prints only when the **PAT** companion is `0`. A GID companion of `0` gets no NOTE. An unset companion gets no NOTE either: the recipe's own `LEGACY:` line and this section disclose that case.

A refusal can be false only when the companion is inherited (it fails safe). The opposite error is a run from an environment without the companion, which writes a second copy in a served tree. To decide for the tree, do the [fresh-eval check](#reading-the-companion-fresh-eval) (OPERATOR).

**Bypass rule.** Run the legacy recipe with the companion removed from its environment **only after** the fresh-eval check reads `0` or unset, and the blocked-`.envrc` caveat does not apply. Never remove the companion on a guess.

**What `check-env` prints.** It names states only, never a length, suffix or hash.

| Companion | `just check-env` prints |
|---|---|
| set, not exactly `0` (including empty) | `ASANA_PAT: set (substrate-marked)` plus a note to decide per this file |
| exactly `0` | `ASANA_PAT: set (not substrate: withheld or shadowed)` |
| unset | `ASANA_PAT: set (not substrate: no companion)` |
| variable itself unset | `ASANA_PAT: missing` (exit 1) |

`ASANA_WORKSPACE_GID` uses the same states with its own companion. When the state is substrate-marked and `.env/local` also exists, `check-env` adds a note that a legacy copy exists. It tests that the file exists and never reads it.

### The bridge window (pre-mint)

The **bridge window** is any period when the loader is live in a declaring tree but the producer has not yet minted the SSM mirror.

- The loader cannot find the coordinate, so it withholds (`not-found`), and the companion is `0`.
- Your layer-5 `.env/local` value is still there, so the line reads `(not-found, shadowed)`. Its fix slot is the `not-found` owner slot (DC-9), not a layer removal.
- The PAT companion is `0`, so **`just fetch-secrets` works** and is the supported path in this window. It prints the NOTE. With the GID companion unset or `0`, it writes both names.
- The window is empty if the mint precedes the loader. It closes at the mint plus the tree's next fresh eval (the companion becomes `<v>:<exp>`).

### Do not delete your `.env/local` until the fresh eval serves

> **WARNING.** During the bridge window, on a `(<cause>, shadowed)` line, **do not delete your layer-5 `.env/local` value until a fresh eval in that tree reads `<v>:<exp>` with `exp` in the future.** That holds after the mint too: a line such as `(access-denied, shadowed)` still means the loader is withholding. The line's fix slot is the cause's fix, never a layer removal. Your `.env/local` value is the **only working copy** of the credential. Removing it leaves the tree with nothing: the loader is still withholding.
>
> Wait until the [fresh-eval check](#reading-the-companion-fresh-eval) reads `<v>:<exp>` with `exp` in the future. After a fresh eval serves the value, layer 5 is overridden silently and the `(<cause>, shadowed)` line disappears.

### Retirement (A3(d), OW-4)

The legacy recipe and layer-5 credentials **retire together**, in one act, at the A3(d) event (operator word OW-4):
- the recipe `fetch-secrets` and its references are removed;
- main's `.env/local` is deleted by the operator.

The trigger has two parts: (1) `.a8-credentials` is present both on the main checkout's HEAD and on the fetched default branch; **and** (2) a fresh eval in main (the [check above](#reading-the-companion-fresh-eval)) reads a served companion (`<v>:<exp>`, exp in the future). Until then the guard applies, and any withhold or `shadowed` re-opens the recipe. A shell without the direnv hook also lets it write. After A3(d) this section is deleted, and layer 5 keeps only non-credential overrides.

---

## Cross-Links

| System | Location | Role |
|--------|----------|------|
| Canonical loader | `/Users/tomtenuta/Code/a8/a8-devenv/scripts/a8-devenv.sh` (function `_a8_load_env`) | Defines the 6-layer load order |
| Declaration | `.a8-credentials` (repo root) | Names and SSM coordinates for `ASANA_PAT`, `ASANA_WORKSPACE_GID`; see above |
| Layer 3 defaults | `.env/defaults` | Committed project non-secrets; S3 cache vars live here (post CFG-001). Header comment cites the layer number. |
| Layer 5 template | `.env/local.example` | Developer template. Its credential lines are the LEGACY path (see above); the file is one of the files the worktree trust check compares and is not edited here. |
| Legacy recipe | `justfile` recipe `fetch-secrets` (group `legacy`) | Guarded on the PAT companion in its own environment; skips a served GID (OW-12); retires at A3(d) |
| Presence check | `justfile` recipe `check-env` | Prints the states in the table above |
| Secret contract (default profile) | `secretspec.toml:[profiles.default]` | Lib-mode (FastAPI, Lambda, embedded SDK): all S3 cache vars optional. |
| Secret contract (CLI profile) | `secretspec.toml:[profiles.cli]` | CLI/offline mode (`python -m autom8_asana.metrics`): S3 bucket and region promoted to `required = true`. Defined under ADR-0001. |
| Validate lib-mode | `secretspec check --file secretspec.toml --provider env --reason "<reason>"` | Checks `[profiles.default]` contract |
| Validate CLI mode | `secretspec check --file secretspec.toml --provider env --profile cli --reason "<reason>"` | Checks `[profiles.cli]` contract |
| CLI preflight | `src/autom8_asana/metrics/__main__.py` (`_preflight_cli_profile`, `_emit_preflight_error`) | Subprocess-first `secretspec check --profile cli` with inline fallback when the binary is absent, exits non-zero, or times out. Exit code 2 on contract violation. |
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

**Fresh-clone ergonomics**: After a `git clone` + `direnv allow` (**OPERATOR**, a primary-checkout act), Layer 3 auto-exports `ASANA_CACHE_S3_BUCKET=autom8-s3` to the shell environment without any manual `export` statement or `.env/local` edit. This makes `python -m autom8_asana.metrics active_mrr` work zero-touch for non-secret paths (the original motivation for CFG-001).

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

`src/autom8_asana/metrics/__main__.py` implements the CLI preflight in `_preflight_cli_profile` (Alternative C, per TDD-0001-cli-preflight-contract). Before `load_project_dataframe` is called, the entrypoint runs:

1. `secretspec check --file <repo root>/secretspec.toml --provider env --profile cli --reason "<preflight reason>"` via subprocess. The `--file` flag replaced `--config`, and the policy requires a `--reason`.
2. If the `secretspec` binary is absent, exits non-zero, or times out (5 s), falls back to the inline `_preflight_inline_fallback()` check against `_CLI_REQUIRED = ("ASANA_CACHE_S3_BUCKET", "ASANA_CACHE_S3_REGION")`.

If `ASANA_CACHE_S3_BUCKET` is unset or empty, the preflight exits with code 2 and emits a structured error. It points to `.env/defaults` (where the S3 cache vars belong) and `secretspec.toml`, with explicit file paths. It also names `.a8-credentials` as where the credentials are declared, and states that the S3 vars do not belong there. The fix tail says to reload the environment (`direnv reload`). If direnv reports the `.envrc` is blocked, in a knossos worktree check `ari worktree trust show <root>`. This replaces the previous opaque transport error (`No S3 bucket configured. Pass bucket= or set ASANA_CACHE_S3_BUCKET.`) that surfaced deep in the S3 transport layer rather than at the CLI boundary.

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
3. **`.env/current` interaction**: The `_a8_load_env` function reads `.env/current` to determine the active environment name, which in turn determines the Layer-5 file path. This file is not described above because it is not one of the 6 loading layers — it is an environment selector, not a value source. However, devs who rename their environment (e.g., to `staging`) must be aware that Layer 5 becomes `.env/staging`, not `.env/local`.
4. **Verify and fill: argument grammar and exit codes**: RESOLVED. Filled from the stdlib at `1162145dd`, re-checked when the stdlib release is pinned.
5. **Exact stdlib voice text for withhold lines**: RESOLVED. Filled from the stdlib at `1162145dd`, re-checked when the stdlib release is pinned. The full text stays in the golden, not here.
6. **Mint status and operating mode**: when the SSM mirror exists, and whether the producer runs an overlap or a window, are operator records.

---

## Stakeholder Affirmation Addendum (2026-04-27)

**Source**: stakeholder affirmation by user `tom@tenuta.io`, captured during session `session-20260427-154543-c703e121` (initiative `verify-active-mrr-provenance`, PRD G5).

### Affirmed facts

1. **`autom8-s3` is the production cache bucket.** All autom8y-asana cache reads and writes — including the metrics CLI (`python -m autom8_asana.metrics active_mrr`), the cache_warmer Lambda, the dataframe-loader code path (`src/autom8_asana/dataframes/offline.py`), and the freshness signal added under PRD `verify-active-mrr-provenance` — target `autom8-s3` as the canonical, sole production bucket.

2. **No multi-environment cache buckets exist.** The ecosystem is standardized on a canary-in-production deployment topology. There is no `autom8-s3-staging`, `autom8-s3-dev`, or analogous environment-specific cache bucket. `autom8-s3` is the one bucket; production data flows through it under the canary discipline.

3. **`AUTOM8Y_ENV=local` is legacy cruft.** The `AUTOM8Y_ENV` environment variable is a vestige of a prior multi-environment intention that was never realized. It does not currently gate behavior in any load-bearing code path of autom8y-asana. Its continued presence in tooling, scripts, or documentation is residual; it carries no live semantics for the cache bucket → environment mapping.

### Architectural implication

The freshness signal emitted by `python -m autom8_asana.metrics active_mrr` reports `provenance.env = "production"` unconditionally. This is correct under the affirmed topology: there is one bucket, one environment, one canary, one production. The PRD G5 evidence token for this binding is `stakeholder-affirmation-2026-04-27`, which propagates verbatim into the JSON envelope's `provenance.evidence` field per TDD freshness-module §4.

### Remediation scope (NOT this addendum)

This addendum **documents** the affirmed state. It does **not propose** remediation for `AUTOM8Y_ENV` cruft removal, multi-environment scaffolding cleanup, or any related hygiene work. Those concerns are owned by the **thermia rite** per:

- PRD `verify-active-mrr-provenance` D7 (deferred-not-disposed defects)
- T10 handoff dossier (10x-dev → thermia, this initiative's terminal handoff): section 7 carries the `AUTOM8Y_ENV` legacy-cruft remediation as a thermia-scope item

The metrics CLI is correct as-implemented under the canary-in-production topology. Cleanup of legacy multi-environment scaffolding is downstream of this initiative.
