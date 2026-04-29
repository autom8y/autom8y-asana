---
type: decision
decision_subtype: adr
id: ADR-0001
artifact_id: ADR-0001-env-secret-profile-split
schema_version: "1.0"
status: proposed
lifecycle_status: proposed
date: "2026-04-20"
rite: hygiene
initiative: "Ecosystem env/secret platformization alignment"
session_id: session-20260415-010441-e0231c37
deciders:
  - architect-enforcer (hygiene rite, sprint-B plan phase)
consulted:
  - code-smeller (smell inventory author)
  - eunomia-rite (upstream handoff source)
informed:
  - janitor (downstream executor of CFG-003)
  - audit-lead (downstream verifier)
source_handoff: .ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md
source_smell_inventory: .ledge/reviews/smell-inventory-env-secrets-2026-04-20.md
covers_cfg_items: [CFG-003]
enables_cfg_items: [CFG-006]
source_artifacts:
  - secretspec.toml
  - .env/defaults
  - .env/local.example
  - src/autom8_asana/metrics/__main__.py
  - scripts/a8-devenv.sh (ecosystem; read-only reference)
evidence_grade: strong
supersedes: []
superseded_by: []
---

# ADR-0001 — Split `secretspec.toml` into `default` (lib-mode) and `cli` (CLI/offline) profiles

## Status

Proposed (hygiene rite sprint-B, 2026-04-20). Awaiting janitor execution under CFG-003 and downstream verification under CFG-006.

## Context

### The proximate defect

`secretspec.toml` today declares all environment variables under a single `[profiles.default]` block (`secretspec.toml:14`, sole profile section in a 138-line file — verified in smell inventory, Before-state Snapshot Manifest, line 225). Every variable in that block is tagged `required = false` (cross-cutting observation, smell inventory line 129). For the core S3 cache variable `ASANA_CACHE_S3_BUCKET` declared at `secretspec.toml:59`, `required = false` is defensible for **lib-mode consumers** (the FastAPI server, Lambda handlers, and embedded SDK paths can tolerate absence — they degrade to memory-only cache) but is a **false contract for CLI/offline-mode consumers** (`python -m autom8_asana.metrics`, `scripts/calc_mrr.py` before its planned deletion in CFG-007). These CLI paths hit S3 unconditionally on first call and fail with a generic transport error (`src/autom8_asana/metrics/__main__.py:84-86`, catch at load site) rather than a structured contract violation.

### Why this is architectural, not tactical

The smell inventory rates CFG-003 **High (P2)** (line 74) and flags it as the **keystone** for CFG-006's preflight work (line 129: "CFG-003 is the keystone of this inventory — CFG-006's preflight relies on a CLI profile existing to check against"). The compound-signal locus is the variable `ASANA_CACHE_S3_BUCKET` itself: CFG-001 (missing from Layer 3 defaults), CFG-003 (this ADR — no CLI profile), CFG-006 (no preflight that could check it), and CFG-007 (duplicate CLI script still references it inline) all converge on one variable. Per CS:SRC-005 Palomba et al. 2018 [STRONG | 0.72 @ 2026-04-20] and the hygiene agent's cumulative-smell principle [AQ:SRC-004 Mo et al. 2019] [STRONG | 0.75 @ 2026-04-01], this co-occurrence elevates the finding above routine config hygiene: the declared contract diverges from the real contract across **multiple consumption modes of the same variable**. Consolidating the fix into a profile-aware schema is architecture work — defining the *shape* of the validation contract — not a one-line edit.

### Handoff `tradeoff_points` that constrain this decision

From `HANDOFF-eunomia-to-hygiene-2026-04-20.md` lines 37-46:

- **`validation_strictness` tradeoff** (lines 41-43): "secretspec profile split makes some previously-optional vars required for CLI profile. […] Current `required=false` for `ASANA_CACHE_S3_BUCKET` is a lie for CLI/offline workflows. Making CLI-profile checks strict at startup trades lax documentation for actionable preflight failure." → This ADR explicitly accepts that trade. Loud, fail-fast CLI validation is preferred over silent runtime transport errors.
- **`scope_breadth` tradeoff** (lines 39-40): "Fleet-wide rationalization vs single-repo fix." → This ADR is **single-repo** (autom8y-asana). Fleet-wide profile conventions (if any) are CFG-005 / a separate cross-rite handoff. Janitor must not generalize the profile pattern to satellite repos during this sprint.

## Decision

Introduce a `[profiles.cli]` section in `secretspec.toml` that represents the **CLI/offline-mode contract**. This profile promotes S3 cache variables from optional to required, without altering the `[profiles.default]` (lib-mode) contract.

### Profile partition

| Profile | Consumer | Contract attitude | S3 bucket var | S3 region var |
|---|---|---|---|---|
| `[profiles.default]` (existing) | FastAPI server (`API_HOST`/`API_PORT`), Lambda handlers, embedded SDK, unit tests | Permissive. Absent cache vars are acceptable; SDK degrades to memory-only cache. | `required = false` (unchanged) | `required = false` with default `"us-east-1"` (unchanged) |
| `[profiles.cli]` (new) | `python -m autom8_asana.metrics`, `scripts/calc_mrr.py` (until deleted in CFG-007), any future CLI/offline data-workflow entrypoint | Strict. CLI paths unconditionally read/write S3 cache. Absence at validation time = contract violation. | `required = true` (**promoted from false**) | `required = true` (**promoted; retain default `"us-east-1"` for fresh-clone ergonomics**) |

### Variables whose `required` flag changes under `[profiles.cli]`

- **`ASANA_CACHE_S3_BUCKET`** — `required = true` under `[profiles.cli]`. This is the variable cited in the handoff acceptance criterion (line 69) and is the compound-signal locus.
- **`ASANA_CACHE_S3_REGION`** — `required = true` under `[profiles.cli]`, retaining the Layer-3 default `"us-east-1"` (populated by CFG-001). Rationale: region has a sane default, but the CLI profile's contract is that the full S3 addressing triple (bucket, region, optional endpoint) is *declared intentionally*, not inherited silently from a library default. Making region `required=true` with a default satisfies `secretspec check --profile cli` as long as CFG-001 populates `.env/defaults`; it fails loudly if a developer clears the var to an empty string.
- **`ASANA_CACHE_S3_ENDPOINT_URL`** — remains `required = false` under `[profiles.cli]`. LocalStack endpoints are dev-environment-specific; docker-compose overrides handle them (`docker-compose.override.yml:33-50`). The CLI profile does not require an endpoint override for host-side usage.

All other variables — Redis, pacing, rate-limit, observability, webhook, project-override, and the six `ASANA_PACING_*`/`ASANA_S3_RETRY_*`/`ASANA_CACHE_DF_*` tuning knobs — remain under `[profiles.default]` only, with `required = false` unchanged. CLI paths inherit these from default implicitly (see Schema Decision).

### What this ADR does NOT do

- Does not change any variable's `required` flag under `[profiles.default]`. Lib-mode consumers see identical validation behavior before and after.
- Does not remove or rename any variable.
- Does not introduce runtime behavior change in `src/` — the ADR only changes the declarative contract file. Preflight wiring is CFG-006 / the companion TDD.
- Does not apply the profile convention to other satellite repos' `secretspec.toml` files — `scope_breadth` tradeoff constrains this to autom8y-asana only.

## Schema decision — how `secretspec` handles profile inheritance

**Assumption (load-bearing, janitor must verify before execution)**: `secretspec check --profile cli` evaluates variables declared under `[profiles.cli]` strictly, and inherits variables declared only under `[profiles.default]` with their default-profile attributes. That is, the CLI profile is an **override-on-top** of the default profile, not a redeclaration replacement.

Under this assumption, the janitor only needs to **redeclare** the two variables whose `required` flag differs (`ASANA_CACHE_S3_BUCKET`, `ASANA_CACHE_S3_REGION`) inside `[profiles.cli]`, leaving every other variable in `[profiles.default]` where it sits today. The TOML looks like:

```toml
[profiles.default]
# … existing 60+ variable block, unchanged …
ASANA_CACHE_S3_BUCKET = { description = "S3 bucket name for cache storage", required = false }
ASANA_CACHE_S3_REGION = { description = "AWS region for S3 bucket", required = false, default = "us-east-1" }
# … rest unchanged …

[profiles.cli]
# Overrides for CLI/offline consumers (python -m autom8_asana.metrics and equivalents).
# Only variables whose contract differs from profiles.default are redeclared here.
ASANA_CACHE_S3_BUCKET = { description = "S3 bucket name for cache storage (CLI paths unconditionally hit S3)", required = true }
ASANA_CACHE_S3_REGION = { description = "AWS region for S3 bucket", required = true, default = "us-east-1" }
```

### Pre-execution verification step for janitor

Before committing the split, the janitor must empirically verify the inheritance assumption. Two commands, run in this order:

1. **Negative control** (with the split applied, bucket unset):
   ```
   unset ASANA_CACHE_S3_BUCKET
   secretspec check --config secretspec.toml --provider env --profile cli
   ```
   Expected: non-zero exit, error message names `ASANA_CACHE_S3_BUCKET`. If exit is zero, the inheritance assumption is **wrong** — `secretspec` treats profile sections as additive unions rather than overrides-on-top, and the janitor must pause and escalate (see Rejection Criteria).

2. **Positive control** (with the split applied, bucket set via `.env/defaults` from CFG-001):
   ```
   secretspec check --config secretspec.toml --provider env --profile default
   ```
   Expected: exit 0. Lib-mode callers must still pass with zero `required=true` enforcement on the cache vars. If this fails, profile-scoped override is not behaving as assumed, and the janitor must pause and escalate.

If either verification command produces an unexpected outcome, the janitor **does not commit** and routes back to architect-enforcer for schema redesign. An alternative schema (each profile declares its full variable set, sharing nothing) is documented in Alternatives Considered as fallback.

## Consequences

### What breaks (intentional)

- **Any CLI invocation that runs `secretspec check --profile cli` without `ASANA_CACHE_S3_BUCKET` set will fail.** This is the explicit goal. Fresh-clone developers who haven't completed CFG-001 (i.e., `.env/defaults` still omits the bucket) will see the preflight surface a loud, actionable error instead of the current silent success followed by a deep runtime transport failure.
- **CI jobs (if any) that invoke `secretspec check --profile cli`** must ensure the CLI profile contract is satisfied in CI environment variables. Current CI (verified indirectly via handoff — no explicit secretspec CI gate documented) does not yet invoke `--profile cli`, so this is prospective, not retroactive breakage.

### What is newly possible

- **Machine-checkable CLI contract**. CFG-006's preflight can now shell out to `secretspec check --profile cli` and get a structured pass/fail, rather than inventing an inline ad-hoc validator that would inevitably drift from the authoritative `secretspec.toml`.
- **Documentation truthfulness**. `required = true` in `[profiles.cli]` becomes self-documenting: a developer reading the file learns which vars are non-negotiable for CLI usage without having to cross-reference `metrics/__main__.py` internals.
- **Future second-profile expansion**. If a `[profiles.test]` or `[profiles.lambda]` contract emerges (not in scope here), the override-on-top pattern extends cleanly.

### Backward-compat implications

- **Lib-mode callers see zero behavioral change.** The FastAPI server, Lambda handlers, and embedded SDK paths invoke (or should invoke) `secretspec check` without `--profile cli` (or with `--profile default`, which is also the default when flag is omitted — assumption for janitor to verify during pre-execution step). Their validation surface is identical to pre-ADR state.
- **Any documentation or runbook** that cites `secretspec check --config secretspec.toml --provider env` (including `secretspec.toml:5` header comment) continues to work unchanged for lib-mode. A new canonical command `secretspec check --config secretspec.toml --provider env --profile cli` is added to the header comment in the CFG-003 edit.
- **No existing test is expected to break.** The smell inventory does not report any test that asserts specific `secretspec` profile shape, and no test in the repository invokes `secretspec` at test time (verified by the smell inventory's silence on that point; janitor should confirm via `grep -rn 'secretspec' tests/` as a final check before commit).

### Explicit boundary: lib-mode consumers must not be forced into CLI validation

A known failure mode would be: someone, in a later sprint, changes a shared startup script so that the FastAPI server or a Lambda handler begins invoking `secretspec check --profile cli` at boot. That would extend CLI strictness to lib-mode callers and **break the explicit consequence boundary set by this ADR**. Janitor and audit-lead should both watch for this anti-pattern during execution and downstream code review.

## Alternatives Considered

### Alternative A — Keep the flat `[profiles.default]` profile, rely solely on runtime check

**Proposal**: Leave `secretspec.toml` unchanged. CFG-006's preflight inspects `os.environ["ASANA_CACHE_S3_BUCKET"]` directly at CLI startup and raises with a pointer to config files if absent.

**Rejected because**: this preserves the root contract divergence (the declaration file says "optional" when it is not, for one consumer class). It also duplicates validation logic between `secretspec.toml` and the Python preflight, which will drift. Per the handoff `validation_strictness` tradeoff (lines 41-43), the entire point of this work is to make contracts machine-checkable in a single authoritative place. Runtime check alone misses fail-fast for CI gates and misses documentation truthfulness.

### Alternative B — Split `secretspec.toml` into multiple config files (e.g., `secretspec.cli.toml`, `secretspec.lib.toml`)

**Proposal**: Produce two separate files, one per consumer mode, each with its own `[profiles.default]` block. Invoke `secretspec check --config secretspec.cli.toml` for CLI and `… --config secretspec.lib.toml` for lib.

**Rejected because**: the `secretspec` tool convention (per its header comment at `secretspec.toml:5` — `secretspec check --config secretspec.toml --provider env`) is single-config-file. Splitting fragments the declaration surface and doubles the synchronization burden for the ~60 variables that are identical across both modes. The profile feature (`[profiles.NAME]`) inside a single file is exactly the tool's intended answer to this question. Using two files would be fighting the tool's grain.

### Alternative C — Add a runtime mode switcher env var (`ASANA_MODE=cli|lib`)

**Proposal**: Introduce a new env var read at Python import time. When `ASANA_MODE=cli`, the SDK asserts on missing bucket. When `ASANA_MODE=lib`, it tolerates absence.

**Rejected because**: validation selection belongs at **tool invocation time** (how you called the process), not at **runtime config time** (what env var you exported). A CLI invocation IS the selector — using argv/entrypoint routing to pick a profile is structurally cleaner than an out-of-band env var that has to be remembered and whose wrong value produces confusing errors. Also: `ASANA_MODE` becomes a new variable that itself has to be declared in `secretspec.toml`, which is circular.

### Alternative D — Make `ASANA_CACHE_S3_BUCKET` globally `required = true`

**Proposal**: Skip profiles entirely. Set `required = true` on the variable under the single existing `[profiles.default]`.

**Rejected because**: this breaks **lib-mode** consumers (the very tradeoff the handoff `validation_strictness` clause is designed to surface and prevent). The FastAPI server in a test or staging environment may intentionally run without S3 cache; the Lambda runtime may rely on in-memory cache only. Globally requiring the bucket forces a lie in the opposite direction — claiming required for cases where it is genuinely optional.

## Rejection criteria for janitor

The janitor should **pause and escalate back to architect-enforcer** (not proceed with commit) if any of the following hold during CFG-003 execution:

1. **Schema inheritance does not work as assumed.** If the pre-execution verification commands (negative control / positive control, above) produce unexpected exit codes, the override-on-top model is wrong for `secretspec`. Escalate with the actual observed behavior so architect-enforcer can redesign.
2. **`secretspec` binary is unavailable in the environment where the ADR's verification commands must run.** If the tool is not installable or not in PATH, the ADR's acceptance criterion (handoff line 70: "`secretspec check […] --profile cli` passes on a shell where CFG-001 is applied") cannot be verified. Escalate to user — this would necessitate switching the CFG-006 preflight recommendation from Alternative A (shell out) to Alternative B (inline) permanently, which is a separate design decision.
3. **`[profiles.cli]` edit would force changes under `[profiles.default]` to keep lib-mode behavior stable.** This would be an inheritance-semantics surprise — the override-on-top assumption fails. Escalate.
4. **Any runtime code in `src/` would need to change to absorb the profile split.** This ADR is strictly about the declarative contract. If runtime code must change to accommodate it (beyond CFG-006's preflight wiring, which is itself a separate ticket), that is scope creep and should be escalated rather than silently broadened.
5. **The `.env/defaults` population required by CFG-001 has not landed yet.** The positive-control verification depends on CFG-001 being complete. Janitor must sequence CFG-003 after CFG-001 (handoff explicitly declares `CFG-003 dependencies: [CFG-001]` at line 74). If CFG-001 is not in, CFG-003 cannot be verified — pause and coordinate sprint ordering.

## Links

- Upstream handoff: `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md` (CFG-003 at lines 65-74; CFG-006 at lines 100-108; tradeoff_points at lines 37-46)
- Smell inventory: `.ledge/reviews/smell-inventory-env-secrets-2026-04-20.md` (CFG-003 finding at lines 65-75; cross-cutting observation #1 at line 129)
- Companion TDD: `.ledge/specs/TDD-cli-preflight-contract.md` (CFG-006 — consumes the profile defined here)
- Source file affected: `secretspec.toml`
- Source files consuming the contract (reference only, not edited by this ADR): `src/autom8_asana/metrics/__main__.py`, `scripts/calc_mrr.py` (pending deletion under CFG-007)
