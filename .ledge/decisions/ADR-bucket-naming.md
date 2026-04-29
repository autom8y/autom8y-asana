---
type: decision
decision_subtype: adr
id: ADR-0002
artifact_id: ADR-0002-bucket-naming
schema_version: "1.0"
status: proposed
lifecycle_status: proposed
date: "2026-04-20"
rite: hygiene
initiative: "Ecosystem env/secret platformization alignment"
session_id: session-20260415-010441-e0231c37
deciders:
  - architect-enforcer (hygiene rite, sprint-C plan phase)
consulted:
  - code-smeller (smell inventory author)
  - eunomia-rite (upstream handoff source)
informed:
  - janitor (downstream executor of CFG-008 — `.know/` doc update)
  - audit-lead (downstream verifier)
  - SRE rite (potential future consumer if bucket-disposition action is opened)
source_handoff: .ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md
source_smell_inventory: .ledge/reviews/smell-inventory-env-secrets-2026-04-20.md
covers_cfg_items: [CFG-004]
enables_cfg_items: [CFG-008]
source_artifacts:
  - .env/defaults
  - docker-compose.override.yml
  - src/autom8_asana/lambda_handlers/checkpoint.py
  - src/autom8_asana/lambda_handlers/cache_warmer.py
  - /Users/tomtenuta/Code/a8/manifest.yaml (ecosystem monorepo service manifest; read-only reference)
  - /Users/tomtenuta/Code/a8/.a8/autom8y/ecosystem.conf (ecosystem; read-only reference)
  - /Users/tomtenuta/Code/a8/.a8/autom8y/env.defaults (ecosystem; read-only reference)
evidence_grade: strong
supersedes: []
superseded_by: []
---

# ADR-0002 — Canonicalize `autom8-s3` (legacy) as the dev/local S3 cache bucket name; document `autom8y-s3` as a non-canonical empty alias

## Status

Proposed (hygiene rite sprint-C, 2026-04-20). Awaiting audit-lead verification under CFG-004 acceptance criteria and downstream `.know/` reflection under CFG-008.

## Context

### The proximate drift

Two S3 bucket names appear in the autom8y orbit:

- `s3://autom8-s3/` (legacy, **no `y`**) — the known-working dev cache bucket. Prefixes like `dataframes/<project_gid>/…` are populated with live dev data (per handoff line 158 and prior `aws s3 ls` investigation).
- `s3://autom8y-s3/` (org-branded, **with `y`**) — the org-consistent name. Exists, returns empty from `aws s3 ls` (per handoff line 158). No data, no references from any in-repo code path.

The friction surfaced during an eunomia session (`session-20260415-010441-e0231c37`): a developer who guesses the "org-branded" name gets an empty bucket and silent-no-data rather than an actionable error (handoff line 158). No repo file documents which is canonical. Until this ADR, the post-CFG-001 `.env/defaults` header (lines 15-20) names `autom8-s3` as the "known-working dev" value and explicitly defers the canonical decision to this ADR.

### Load-bearing references (grep audit, 2026-04-20)

A whole-repo grep (`autom8-s3|autom8y-s3` across `*.py`, `*.yml`, `*.yaml`, `*.md`, `*.toml`, `*.tf`, `*.json`, `*.sh`) plus the ecosystem-level monorepo revealed the following **code-level** bindings to `autom8-s3`:

| Reference | Kind | Scope |
|-----------|------|-------|
| `docker-compose.override.yml:33` | runtime env | LocalStack dev bucket (single-repo) |
| `.env/defaults:21` | commit-layer env (post-CFG-001) | Layer 3 non-secret default (single-repo) |
| `src/autom8_asana/lambda_handlers/checkpoint.py:29` | hardcoded fallback constant `DEFAULT_BUCKET = "autom8-s3"` | production Lambda (cross-env) |
| `src/autom8_asana/lambda_handlers/checkpoint.py:11` | docstring stating default | production Lambda (cross-env) |
| `src/autom8_asana/lambda_handlers/checkpoint.py:148` | docstring example | production Lambda (cross-env) |
| `src/autom8_asana/lambda_handlers/cache_warmer.py:273` | `or "autom8-s3"` fallback expression | production Lambda (cross-env) |
| `/Users/tomtenuta/Code/a8/manifest.yaml:476` | ecosystem monorepo service manifest (`ASANA_CACHE_S3_BUCKET: "autom8-s3"`) | **ecosystem orchestration** (cross-repo) |

Grep for `autom8y-s3` returned **zero matches** anywhere in the monorepo, the ecosystem config, or this repo. The org-branded name exists only as a live bucket in AWS and as narrative references in the handoff and smell inventory documents.

### Ecosystem signal

`.a8/autom8y/ecosystem.conf:5` declares `A8_ORG_NAME=autom8y` (the "with-y" org convention). The ecosystem `env.defaults` file (`.a8/autom8y/env.defaults`) does **not** declare any bucket variable — it covers only log level, debug flag, and Grafana/Tempo/Loki observability endpoints. The ecosystem-level `autom8y-*` prefix convention therefore binds org name, SDK namespaces (`autom8y-auth`, `autom8y-cache`, etc. per `manifest.yaml:469`), and service identity — but it has never been extended to this specific dev S3 cache bucket, and the monorepo service manifest ratifies the `autom8-s3` name at the orchestration layer (`manifest.yaml:476`).

### Operational state

- Live dev dataframes live in `s3://autom8-s3/dataframes/` (populated).
- `s3://autom8y-s3/` is an empty AWS bucket. Owner/ownership tags not verified at ADR time; treated as a nice-to-have for any follow-up SRE action and not load-bearing for this decision.
- `docker-compose.override.yml:33` uses `autom8-s3` as the LocalStack bucket name so that dev-loop code paths and live AWS paths reference the same name (reducing off-by-one bugs between local and cloud).

### Why this is a naming/documentation drift, not architectural

Per the hygiene rite's own scope boundary: renaming internal symbols is hygiene; renaming exported symbols or crossing public API contracts is architecture (see architect-enforcer boundary heuristic on contract impact). `autom8-s3` is not a public API — it is a bucket name embedded in internal infrastructure config. But it **is** load-bearing across three boundaries (single-repo, cross-Lambda, cross-monorepo-manifest), and any rename would cross into SRE territory (live-data migration is explicitly scoped **out** of hygiene per handoff line 181). This decision records which name is canonical; it does not migrate data and does not change the name.

## Decision

**Option A — `autom8-s3` is canonical.** The naming is historical; the ecosystem-standard `autom8y-*` prefix is acknowledged as an unrealized convention for this one bucket. `autom8y-s3` is documented as a non-canonical empty alias that should not receive writes.

### Rationale (bound to acceptance criteria)

1. **Handoff acceptance criterion 2 (lines 79-80)** offers a binary: "If `autom8-s3` is canonical: note in `.env/defaults` header. If migration to `autom8y-s3` is planned: dated migration note with owner." The grep audit above establishes that Option A is the branch that matches observed reality:
   - Live data is in `autom8-s3`.
   - Every in-repo code reference points to `autom8-s3`.
   - The ecosystem-level service manifest (`manifest.yaml:476`) ratifies `autom8-s3` at the orchestration layer.
   - `autom8y-s3` has zero code references; it exists only as an empty AWS object.
2. **Sprint non-goal alignment**: Handoff line 181 explicitly declares "not migrating live data between buckets (ops/sre concern)." Option A requires no migration. Options B and C would require live-data migration or bucket-disposition action — both cross the handoff's explicit non-goal boundary.
3. **Blast radius**: Migration to `autom8y-s3` (Option B) would require coordinated edits to `docker-compose.override.yml`, `.env/defaults`, `src/autom8_asana/lambda_handlers/checkpoint.py` (hardcoded default + two docstrings), `src/autom8_asana/lambda_handlers/cache_warmer.py` (fallback expression), **and the ecosystem monorepo service manifest at `/Users/tomtenuta/Code/a8/manifest.yaml:476`** — which is outside this repo and therefore outside this sprint's commit boundary. A rename without ecosystem manifest update would silently diverge the service contract between single-repo code and the orchestration manifest.
4. **Reversibility**: Option A is the null action on real infrastructure. The decision can be reversed by a future ADR with no existing deployment to unwind. Option B creates a dated migration commitment that must either complete or be explicitly retracted.
5. **Value of the empty `autom8y-s3` bucket**: near-zero today; only disambiguation value. Option A addresses the disambiguation need via documentation (this ADR + the CFG-008 `.know/` update) rather than via infrastructure action.

### Canonical-name declaration

For all autom8y-asana consumers (dev/local, CI, Lambda staging, Lambda production, LocalStack), the S3 cache bucket name is:

> **`autom8-s3`** (legacy, no `y`) — canonical

The bucket `autom8y-s3` is a **non-canonical empty alias**. It should not receive new writes. Developers who discover it should consult this ADR, not guess that it is the "correct" org-branded target.

### What this ADR does NOT do

- Does not migrate any data.
- Does not rename any bucket.
- Does not delete or tag the empty `autom8y-s3` bucket (that is SRE territory — see Consequences).
- Does not change any code reference to `autom8-s3`.
- Does not change the `.env/defaults` header that already ratifies `autom8-s3` as the dev value (post-CFG-001 header lines 15-20 already align with this decision — no edit required).
- Does not edit `.know/architecture.md` or `.know/conventions.md` — that reflection is CFG-008's scope.

## Consequences

### What changes

- A decision artifact exists (this ADR) that names `autom8-s3` canonical and `autom8y-s3` a non-canonical empty alias.
- CFG-008 (the `.know/` reflection task later in this sprint) will add the canonical name + legacy-alias note to `.know/conventions.md` or `.know/architecture.md`, cross-linking this ADR. That edit is mandatory for CFG-004 acceptance criterion 3 (handoff line 81).

### What stays the same

- `.env/defaults:21` — already `ASANA_CACHE_S3_BUCKET=autom8-s3` (post-CFG-001). No change.
- `.env/defaults` header comment (lines 15-20) — already names `autom8-s3` as "known-working dev" and references this CFG. No change. The CFG-008 `.know/` update is the only doc edit this ADR generates; the `.env/defaults` header is already aligned.
- `docker-compose.override.yml:33` — no change.
- `src/autom8_asana/lambda_handlers/checkpoint.py` (DEFAULT_BUCKET constant, docstrings) — no change.
- `src/autom8_asana/lambda_handlers/cache_warmer.py` (fallback expression) — no change.
- `/Users/tomtenuta/Code/a8/manifest.yaml:476` — no change; ecosystem manifest already names `autom8-s3`.

### Follow-up work that crosses rite boundaries

**Cross-rite handoff to SRE is OPTIONAL and explicitly deferred.** Option A does not require SRE action to be valid — the documentation-only decision stands without any infrastructure change. However, the empty `autom8y-s3` bucket remains in AWS as a latent confusion source. Two possible SRE actions are worth noting (but **this ADR does not open a handoff**):

1. **Tag-and-warn** (lower blast radius): apply AWS bucket tags to `autom8y-s3` such as `Status: DEPRECATED`, `CanonicalAlternative: autom8-s3`, `ReferenceADR: ADR-0002-bucket-naming`. This makes the non-canonical status visible in the AWS console without any destructive action.
2. **Delete-if-ownership-permits** (higher blast radius): if AWS account ownership confirms `autom8y-s3` is owned by the autom8y AWS account and has zero non-ADR references, delete it. Requires SRE to verify ownership and access patterns first.

**Handoff stub (to be opened separately, post-sprint-close, if SRE capacity permits)**:

- **Owner**: TBD by SRE rite lead
- **Sequencing**: After autom8y-asana hygiene sprint closes (i.e., after CFG-004 and CFG-008 land). Not blocking for this sprint.
- **Scope**: Tag or dispose `s3://autom8y-s3/`. Reference this ADR in the handoff body. Confirm AWS account ownership and the empty state (via `aws s3 ls` and `aws s3api get-bucket-tagging`) before taking destructive action.
- **Out of scope for SRE handoff**: any change to `autom8-s3` itself, any data migration, or any rename of the canonical bucket.

This follow-up is **optional** and does not gate sprint-C closure. Creating the handoff artifact is a future decision that the audit-lead or session owner may open after sprint close if useful; this ADR does not obligate that creation.

### What newly becomes possible

- A future ADR can revisit this decision (e.g., if the ecosystem decides to enforce the `autom8y-*` prefix convention fleet-wide) and supersede ADR-0002 with a migration plan. The load-bearing reference table in the Context section above serves as the migration-cost audit for any such future decision.
- CFG-008's worked example (where does `ASANA_CACHE_S3_BUCKET` belong, and why) can name `autom8-s3` without further investigation and cross-link ADR-0002 for the canonical-name rationale.

## Alternatives Considered

### Option A — Canonize `autom8-s3` (CHOSEN)

**Proposal**: State that the naming is historical, `autom8-s3` is authoritative. Document the ecosystem-standard `autom8y-*` prefix as an unrealized convention for this one bucket.

**Pros**:
- Zero migration cost. Live data, Lambda fallbacks, docker-compose, `.env/defaults`, and the monorepo service manifest already agree.
- Respects handoff non-goal line 181 (no live-data migration in hygiene scope).
- Reversible by future ADR with no existing deployment to unwind.

**Cons**:
- Empty `autom8y-s3` bucket remains in AWS as a latent confusion source. Mitigated by documentation (this ADR + CFG-008 `.know/` update) and by the optional SRE follow-up above.
- Perpetuates a minor ecosystem-naming inconsistency (one of many in any evolving monorepo; the ecosystem tolerates several such legacy names today per grep audit).

### Option B — Declare `autom8y-s3` canonical + plan migration

**Proposal**: State that `autom8y-s3` is the target (ecosystem-consistent), `autom8-s3` is legacy. Record a dated migration plan with owner. Migration executed by SRE (cross-rite handoff required). Interim state: `autom8-s3` remains live; devs continue using it until migration completes.

**Pros**:
- Ecosystem-naming consistency with the `autom8y-*` prefix convention.
- Resolves the org-branding drift at source.

**Cons**:
- Requires coordinated edits across **at least seven code sites** (see Context table: docker-compose, `.env/defaults`, two Lambda docstrings, one Lambda constant, one Lambda fallback expression, the ecosystem monorepo service manifest). The last of these is outside this repo's commit boundary, requiring an ecosystem-rite handoff in addition to the SRE live-data migration handoff.
- Live-data migration (`s3://autom8-s3/dataframes/…` → `s3://autom8y-s3/dataframes/…`) is explicitly out of hygiene scope per handoff line 181. Planning it without executing it creates an open, dated commitment that would need to be tracked to completion — a governance burden this sprint is not positioned to assume.
- Introduces a window during which code and data disagree on the canonical name. Either the code rename or the data migration must land first, and the other side must tolerate both names during the window — structurally complex for a decision that delivers only consistency value.
- **Rejected because**: the benefit (naming consistency) does not outweigh the coordination cost (ecosystem manifest edit + SRE migration handoff + dated commitment tracking) for a bucket that is internal infrastructure, not a public contract. The handoff's 30-minute-investigation + 15-minute-docs effort estimate (line 82) explicitly scopes this as a decision task, not a migration-planning task.

### Option C — Canonize `autom8-s3` but rename/dispose `autom8y-s3`

**Proposal**: Same as Option A plus an action to delete or aggressively tag the empty `autom8y-s3` bucket.

**Pros**:
- Eliminates the latent confusion source (empty org-branded bucket that devs might guess toward).
- Smaller blast radius than Option B (no live-data migration; only destructive action on an empty bucket).

**Cons**:
- Still requires SRE cross-rite handoff for the bucket-disposition action. This sprint cannot close the action itself; at best it opens a ticket.
- Destructive action on an AWS resource requires ownership verification that this sprint is not positioned to perform.
- Aggressive tagging (the non-destructive variant of Option C) is captured in Option A's optional SRE follow-up stub, so Option C's non-destructive benefit collapses into Option A.

**Rejected because**: Option C's destructive sub-variant introduces SRE dependency without giving this sprint a way to verify completion; its non-destructive variant (tag-and-warn) is already available as an optional follow-up under Option A. Option C offers no advantage over Option A + optional follow-up.

## Acceptance-criteria mapping

Mapping to CFG-004 acceptance criteria (handoff lines 78-82):

| Criterion | Satisfied by | Verification |
|-----------|-------------|--------------|
| 1. "Decision recorded (ADR or `.ledge/decisions/`) on canonical bucket name for dev/local" | **This ADR** — `.ledge/decisions/ADR-bucket-naming.md`, filename slug `ADR-bucket-naming`, id `ADR-0002`. Declares `autom8-s3` canonical. | `ls .ledge/decisions/ \| grep -i 'bucket'` returns ≥1 match (this file). |
| 2. "If `autom8-s3` is canonical: note in `.env/defaults` header. If migration to `autom8y-s3` is planned: dated migration note with owner." | Option A selected → first branch applies. **`.env/defaults` header (lines 15-20) already contains the note** (added during CFG-001). No additional edit required by this ADR. | `sed -n '15,20p' .env/defaults` shows the bucket-naming note pointing to CFG-004. |
| 3. "`.know/architecture.md` or `.know/conventions.md` reflects the canonical name and the legacy alias" | **Deferred to CFG-008** (handoff lines 118-126). CFG-008 is the `.know/` documentation task that includes, per its scope, the worked example of `ASANA_CACHE_S3_BUCKET`. Janitor must add a canonical-name + legacy-alias paragraph citing ADR-0002 when executing CFG-008. | `grep -cE 'autom8-s3\|autom8y-s3' .know/conventions.md .know/architecture.md` expected ≥1 after CFG-008 lands. Audit-lead verifies at CFG-008 audit gate, not here. |

### Follow-up required for janitor in CFG-008 scope

CFG-008 janitor instructions must include the following **mandatory** content additions:

1. In the worked example for `ASANA_CACHE_S3_BUCKET`, state the canonical name (`autom8-s3`) and identify `autom8y-s3` as a non-canonical empty alias.
2. Cross-link this ADR by path (`.ledge/decisions/ADR-bucket-naming.md`) and by ID (`ADR-0002`).
3. Do **not** introduce any other bucket-name assertions in `.know/` beyond what this ADR establishes. In particular, do not state migration plans or future renames — the canonical decision is stable as of this date.

The janitor's CFG-008 commit can reference `See ADR-0002 for canonical bucket name rationale` as the doc-link text.

### No `.env/defaults` edit required

Because Option A was selected, the `.env/defaults` header (already added in CFG-001) satisfies criterion 2 with no further edit. **Janitor does not touch `.env/defaults` for CFG-004.** If a future audit finds the header text drifts from ADR-0002's canonical declaration, that is a CFG-001-regression issue, not a CFG-004 issue.

## Rejection criteria for janitor / audit-lead

The following conditions should **pause CFG-004 acceptance** and trigger a re-review:

1. **Live-data evidence contradicts this ADR.** If `aws s3 ls autom8-s3` is empty and `aws s3 ls autom8y-s3` is populated (inverse of the documented state), the canonical decision is wrong — escalate to architect-enforcer for a superseding ADR.
2. **A new code reference to `autom8y-s3` is discovered** (missed by the grep audit in the Context section) and that reference is load-bearing for any production path. Escalate; the load-bearing reference table must be updated before the ADR can be accepted.
3. **Ecosystem rite or SRE rite opens a cross-rite handoff declaring `autom8y-s3` canonical** during the review window. Escalate to user — this ADR's decision would then need to be superseded rather than accepted.
4. **The `.env/defaults` header (post-CFG-001) does not actually contain the note claimed in acceptance-criterion 2 mapping.** If CFG-001's header text was reverted or never landed, audit-lead must require it to land before CFG-004 accepts. (Confirmed present at `.env/defaults:15-20` at ADR authorship time.)

## Links

- Upstream handoff: `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-20.md` (CFG-004 at lines 75-82; "Drift 3: Bucket naming conflict" at lines 156-158; non-goal line 181)
- Smell inventory: `.ledge/reviews/smell-inventory-env-secrets-2026-04-20.md` (CFG-004 row at lines 77-87; escalation note on SRE at line 150)
- Companion ADR in this sprint: `.ledge/decisions/ADR-env-secret-profile-split.md` (ADR-0001 — secretspec profile split; same initiative, different CFG scope)
- Source file already aligned (no edit required by this ADR): `.env/defaults:15-22`
- Code sites that bind `autom8-s3` (read-only reference, not edited): `src/autom8_asana/lambda_handlers/checkpoint.py:11,29,148`, `src/autom8_asana/lambda_handlers/cache_warmer.py:273`, `docker-compose.override.yml:33`
- Ecosystem monorepo reference (read-only, outside this repo's commit boundary): `/Users/tomtenuta/Code/a8/manifest.yaml:476`
- Downstream `.know/` consumer: CFG-008 (handoff lines 118-126) — will cite this ADR when executed
