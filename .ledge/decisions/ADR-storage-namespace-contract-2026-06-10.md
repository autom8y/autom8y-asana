---
type: decision
status: proposed
date: 2026-06-10
author: arch remediation-planner (A4)
title: "Storage Namespace Contract: O-C (SSOT registry + phantom-retire)"
initiative: storage-namespace-contract
companion_tdd: .ledge/specs/TDD-storage-namespace-contract-2026-06-10.md
upstream_assessments:
  - .ledge/reviews/storage-topology-census-2026-06-10.md          # A1
  - .ledge/reviews/storage-config-consumer-graph-2026-06-10.md    # A2
  - .ledge/reviews/storage-config-antipattern-assessment-2026-06-10.md  # A3
evidence_grade: MODERATE  # self-ref ceiling; A1/A2/A3 specific findings carry HIGH
throughline_registration:
  throughline: integration-boundary-fidelity
  n_applied_before: 1
  n_applied_after: 2
  layer_mapping: "TDD §6 — four layers at config altitude"
  caveat: "[UV-P: distinct-satellite gate deferred to eunomia Pythia-custodian ruling]"
arch_ref_citations:
  - "DP:SRC-003 Martin 2017 [MODERATE | 0.70] — Dependency Rule: config contracts point inward toward namespace definitions, not outward toward env-var consumers"
  - "AQ:SRC-006 Martin 2002 [STRONG | 0.75] — Acyclic Dependencies Principle: namespace registry is the dependency inversion point; no namespace may circularly depend on a consumer's env"
  - "AQ:SRC-008 Ford et al. 2017 [MODERATE | 0.75] — fitness functions: t1..t5 alignment tests ARE the fitness functions encoding the namespace contract as executable checks"
---

# ADR — Storage Namespace Contract: O-C (SSOT registry + phantom-retire)

## Status

Proposed. Pending arch-adversary challenge and operator acceptance of Phase-β
IAM tightening decision points.

## Context

The triple-defect saga (PRs #119 → #120 → #121 → autom8y#481) cost four deploy
cycles before coherent values reached production (coherent 0→561 confirmed
2026-06-10 13:07Z). A1/A2/A3 arch analysis identified ONE structural root
wearing three masks:

> **The storage prefix and the principal grant are not derived from a single
> canonical namespace registry.**

Seven anti-patterns were graded (A3):

| AP | Severity | Status before this ADR |
|---|---|---|
| AP-1: env-var overload | HIGH | Latent; zero live readers but structurally re-triggerable |
| AP-2: phantom cold tier | HIGH | Dead config + false docstring |
| AP-3: IAM↔namespace drift | CRITICAL | Reactive #481 grant; full-bucket ECS |
| AP-4: writer-unknown | CRITICAL | 385k live keys; writer unlocatable from this repo |
| AP-5: fossil + live grants | HIGH | `project-frames/` PUT/DELETE grants on fossil |
| AP-6: scattered prefix literals | MED | 3+ hardcoded prefix strings across files |
| AP-7: 128k-key orphan task-cache | LOW | Canary for AP-4 registry test |

The FPC (Field Provenance & Population Contract, TDD-field-provenance-population-contract-2026-06-09.md)
established the derivation model template: one frozen dataclass SSOT, everything
derived from it, generated tests make drift unrepresentable. This ADR applies
that pattern to the storage/config layer.

## Decision

**Adopt O-C: StorageNamespaceContract SSOT module + phantom-RETIRE (sub-option ii).**

Introduce `src/autom8_asana/storage_namespace.py` as the single write point for
all 11 S3 namespaces. Derive Python settings defaults, TF env blocks, TF IAM
Resource ARNs, the #121 cure's prefix constant, and a generated t1..t5 alignment
test suite from this registry. Retire the phantom S3 cold tier (delete `s3_enabled`,
false docstring, dead gate code). Introduce `DurableTaskCacheReader` as the
blessed explicit-read API for the `asana-cache/tasks/` namespace.

Phase the deployment in three independently-revertible phases (α/β/γ) to
maintain CR-3 safety throughout.

## Rationale

### Why O-C over O-B

O-B and O-C are identical except for the phantom-retire component. The phantom
tier (AP-2) carries a false docstring claiming an env var binding that does not
exist (`tiered.py:49` "Environment variable: ASANA_CACHE_S3_ENABLED" — refuted
by A2 §1E, `TieredConfig` is a plain `@dataclass`, not `BaseSettings`). A
registry entry of `lifecycle=PHANTOM` would represent the phantom honestly, but
the correct disposition for dead code with a false docstring is deletion, not
documentation. The `DurableTaskCacheReader` wrapper formalizes what production
already does (#121 cure, coherent=561 live) at near-zero cost (~20 LOC). O-B's
t4 alignment test would catch the phantom and require its disposal anyway — O-C
makes the disposal the design decision, not the test result.

### Why O-C over O-A

O-A (env split only) splits `ASANA_CACHE_S3_PREFIX` into two purpose-scoped vars
but leaves AP-2 through AP-7 structurally re-triggerable. A new ECS consumer
with access to `get_settings().task_cache_prefix` and the full-bucket ECS grant
can land in any unguarded namespace. The grandeur anchor requires STRUCTURAL
UNADDRESSABILITY — a property only t1..t5 CI tests provide.

O-A is useful as an interim lint-gate during Phase-α build (see O-D interim use).
The env split itself is subsumed by O-C: Phase-α derives the split vars from the
registry rather than introducing them as independent env names.

### Why not O-D

O-D (lint only) is the minimal intervention and is appropriate only as a
temporary gate. It does not make the wrong-prefix read structurally unaddressable;
it discourages it. The saga cost four deploy cycles; the recurrence risk is a
structural property of the current codebase, not a developer discipline problem.

### Phantom-RETIRE (ii) vs wire S3 read tier (i)

Option (i) — wiring S3 as a first-class read tier — requires:
(a) a prod `TieredConfig(s3_enabled=True)` construction site (none exists today);
(b) re-coupling to `S3Settings.prefix`, the exact surface this contract quarantines;
(c) a new prod `S3CacheProvider(` call site (zero exist today).

Option (ii) — retire the phantom — requires:
(a) delete dead gates (`tiered.py:57, :120, :126, :168, :211, :264, :302, :364, :430, :492`);
(b) write `DurableTaskCacheReader` (~20 LOC wrapping the existing `null_number_recovery.py:495` pattern);
(c) update the factory comment and stale doc.

The existing cure works. Coherent=561 is live evidence that the explicit-read
pattern (`DurableTaskCacheReader` formalized) is the correct production model.
Option (i) would re-introduce the exact coupling class this contract exists to
eliminate.

### Fitness function alignment (AQ:SRC-008)

The t1..t5 alignment tests are evolutionary architecture fitness functions:

- t1 encodes the "every namespace has a named owner" invariant
- t2 encodes the "every IAM grant maps to a registered namespace" invariant
- t3 encodes the "no prefix literal outside the registry" invariant
- t4 encodes the "no phantom tier in config" invariant
- t5 encodes the "no write grants on fossil namespaces" invariant

These tests make the architecture self-enforcing. A developer cannot introduce a
new AP-3 class drift without failing CI.

## Consequences

### Positive

- **AP-1..AP-7 all addressed**: the registry + t1..t5 makes every identified
  anti-pattern a CI failure.
- **CR-3 safety preserved throughout**: Phase-α defaults match live values exactly;
  Phase-β/γ are operator-gated with pre-conditions.
- **`_DURABLE_TASK_CACHE_PREFIX` pin retired**: the ad-hoc decoupling in
  `null_number_recovery.py:148` becomes a derived value from the registry, not a
  hand-pinned literal. The cure's mechanism is formalized, not papered over.
- **WRITER-UNKNOWN surfaced explicitly**: the registry declares the unknown as
  `writer_owner.code_anchor=None` rather than leaving it implicit. Phase-γ makes
  its resolution a first-class deliverable.
- **N=2 throughline registration**: this contract is the integration-boundary-fidelity
  discipline applied at config altitude.

### Negative / risks

- **TF derivation is detection-grade, not prevention-grade**: the diff-test catches
  a stale `.gen.json` in CI, not at `terraform plan` time. A pre-commit hook closes
  most of this window but is not in scope for Phase-α.
- **Phase-β IAM tightening has operator decision points**: narrowing the ECS
  full-bucket grant requires confirming the ECS receiver's full WRITE surface —
  an enumeration task that is a Phase-β pre-condition, not a Phase-α deliverable.
  Until β-3 lands, the ECS task role retains its full-bucket grant.
- **WRITER-UNKNOWN persists into Phase-γ**: the 385k live `asana-cache/tasks/`
  keys have an unconfirmed writer. The registry declares this honestly; the contract
  is correct whether the writer is the ECS receiver Python path or an as-yet-unlisted
  source, because the #121 cure's read path (`"asana-cache"`) is verified live
  regardless of which writer produces the keys.
- **Physical fossil deletion deferred**: `asana-cache/project-frames/` (2,243 keys)
  and `asana-cache/task-cache/` (128,583 pickle keys) remain in the bucket. The
  contract quarantines them structurally (no new grants possible after β-2) but
  physical deletion is an operator decision outside this ADR's scope.

### Accepted trade-offs (preserved from A3)

These are NOT reclassified by this ADR:

- `CACHE_WARMER_CHECKPOINT_PREFIX` per-lane disjoint values — intentional per #96,
  bounded-context-aligned. The registry represents them as separate per-lane
  contracts (or as a single CHECKPOINTS namespace with per-lane env_var overrides)
  without challenging the design.
- `ASANA_CACHE_S3_BUCKET` single value at 5+ sites — not overloaded; the bucket
  consistency test (a new t6 candidate post Phase-α) is sufficient.
- Redis as the real hot tier — the Phase-1 architecture is correct; AP-2 is the
  false docstring, not the Redis decision.

## Alternatives Considered

### Alternative: FPC-style generated schema files (full prevention-grade)

The FPC generates schema ColumnDefs and model field-classes from one SSOT. The
SNC could similarly generate Python constants AND TF HCL (not just a JSON
intermediate). This would achieve prevention-grade enforcement at the TF boundary.

Rejected because TF HCL generation from Python requires a more complex build step
(templating engine, HCL formatting, TF module structure constraints). The diff-test
+ generator pattern is the minimum viable prevention mechanism; it can be upgraded
to full HCL generation in a post-Phase-β improvement cycle.

### Alternative: HashiCorp Sentinel / OPA policy for IAM enforcement

Sentinel or OPA could enforce "IAM Resource ARN must be in an approved set" as a
TF policy. This is prevention-grade at the plan level but requires the Sentinel/OPA
infrastructure to be available in the CI pipeline (currently not present).

Accepted as a future upgrade path (post-Phase-γ). The t2 alignment test is the
equivalent in the Python test layer; the Sentinel policy would add enforcement at
the TF plan layer. Both can coexist.

## Cross-Rite Referrals

### Cross-Rite Referral: SNC-REF-001
- **Target Rite**: security
- **Concern**: ECS task role holds full-bucket `autom8-s3/*` grant (no prefix
  scoping). This is the current blast radius for any credential compromise or
  misconfigured consumer in the ECS receiver. Phase-β β-3 narrows this, but the
  scoping decision requires security review of the narrowed set before TF apply.
- **Evidence**: A1 IAM column R-IAM-ECS: `"Resource":["arn:aws:s3:::autom8-s3","arn:aws:s3:::autom8-s3/*"]`
- **Suggested Scope**: verify the proposed narrowed ARN list (from `namespaces.gen.json`
  post-Phase-α) covers all legitimate ECS receiver S3 operations and does not
  expose the ECS role to SSRF-based bucket enumeration via the overly-broad resource.
- **Priority**: Medium — no current breach; the risk is latent. Phase-β pre-condition.

### Cross-Rite Referral: SNC-REF-002
- **Target Rite**: security
- **Concern**: two FOSSIL namespaces store pickled Python objects written by the
  `autom8` IAM super-user: `asana-cache/task-cache/` (128,583 keys, `data.pkl`)
  and `asana-cache/task-data-cache-v3/` (342 keys, pickle format). If any future
  consumer reads these, it deserializes untrusted monolith-authored bytes.
- **Evidence**: A1 rows 6/7: R-TASKCACHE-LIVE (128k keys, pickle format);
  R-V3-LIVE (342 keys, pickle). A3 cross-rite observation.
- **Suggested Scope**: confirm no current or planned code path deserializes these
  objects. If the namespaces are quarantined (Phase-β β-2 removes warmer grants),
  verify the quarantine is complete. Flag for physical deletion review.
- **Priority**: Low — no current reader; the risk fires only if a consumer is added.
  Elevates to Medium if physical deletion is deferred beyond 2026-Q3.

### Cross-Rite Referral: SNC-REF-003
- **Target Rite**: debt-triage
- **Concern**: `docs/guides/cache-system.md:140` contains stale documentation
  (`s3_enabled=True`) describing a Phase-3 S3 cold tier that does not exist and
  will be deleted in Phase-α. Other doc-drift: `lambda_handlers/cache_warmer.py:18`
  documents default prefix as `"cache/"` vs actual `"asana-cache"` (R-DOC-DRIFT).
- **Evidence**: A2 §1E E6 + A1 R-DOC-DRIFT.
- **Suggested Scope**: update `docs/guides/cache-system.md` to reflect the
  `DurableTaskCacheReader` pattern as the blessed task-cache read API. Update
  `cache_warmer.py:18` doc default. Both are Phase-α deliverables; flagged here
  so debt-triage tracks the doc debt.
- **Priority**: Low — stale docs; no runtime effect. Phase-α includes the fix.

## Implementation Notes

See companion TDD §5 for the full phase plan with RED-fixture designs, CR-3
safety analysis per phase, falsifiable predictions with expiry dates, and the
five alignment test specifications (t1..t5).

The WRITER-UNKNOWN is the roadmap's first discovery task (Phase-γ γ-0). It is
explicitly NOT resolved in this ADR. Any claim that the writer is confirmed
must carry a file:line anchor in the receiver code path before the registry's
`TASK_CACHE.writer_owner.code_anchor` is set to a non-None value.

---

*Artifact: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/decisions/ADR-storage-namespace-contract-2026-06-10.md`*
*No target repo modified. Design-only. Rung: designed, pending adversary challenge.*
