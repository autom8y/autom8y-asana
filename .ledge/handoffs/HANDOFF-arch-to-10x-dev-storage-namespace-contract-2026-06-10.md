---
type: handoff
handoff_type: implementation
status: proposed   # DRAFT pending arch-adversary verdict (A5); ready_for_downstream only on PASS
source_rite: arch
target_rite: 10x-dev
title: StorageNamespaceContract (O-C, phantom-RETIRE) — Phase-α implementation
date: 2026-06-10
design_references:
  - .ledge/specs/TDD-storage-namespace-contract-2026-06-10.md
  - .ledge/decisions/ADR-storage-namespace-contract-2026-06-10.md
  - .ledge/reviews/storage-topology-census-2026-06-10.md            # A1
  - .ledge/reviews/storage-config-consumer-graph-2026-06-10.md      # A2
  - .ledge/reviews/storage-config-antipattern-assessment-2026-06-10.md  # A3
rung: designed   # NOT built / NOT live; "structurally unaddressable" is FALSE until a misconfigured consumer cannot pass CI
evidence_grade: MODERATE (self-ref; arch-adversary = in-rite challenge, eunomia STRONG later at build)
adversary_verdict: PASS-WITH-CONDITIONS (CONCUR-WITH-FLAGS) — conditions CH-01..CH-03 remediated below; formal PASS conversion available via DELTA re-challenge
adversary_report: .ledge/reviews/ADVERSARY-REPORT-storage-namespace-contract-1.md
arch_ref_citations: mirrored from ADR-storage-namespace-contract-2026-06-10.md (SRC-001..SRC-003, all resolving)   # CH-04 advisory
---

# HANDOFF — arch → 10x-dev — StorageNamespaceContract Phase-α

## The decision (ADR, option-enumerated O-A/O-B/O-C/O-D)
**O-C: StorageNamespaceContract SSOT + phantom-tier RETIRE.** One registry module declares every
autom8-s3 namespace (prefix · semantic-plane · writer-owner · reader-APIs · env-var · IAM
principals+verbs · lifecycle{LIVE,FOSSIL,QUARANTINED}); settings defaults, TF env/IAM (via checked-in
`namespaces.gen.json` + diff-test), the cure's pinned constant, and the t1–t5 alignment tests ALL
derive from it. The phantom S3 cold tier (TieredConfig.s3_enabled, set NOWHERE; tiered.py:49 docstring
FALSE) is RETIRED, not wired: the durable task-cache becomes an explicit WRITE-durable/explicit-read
namespace via a ~20-LOC `DurableTaskCacheReader` formalizing the live #121 cure pattern (coherent=561).
Rejected: O-A (env split cures only latent AP-1; zero live readers today per A2), O-B-without-retire
(leaves the false docstring + dead gates), O-D (lint detects, never prevents), and wiring the read
tier (re-couples to the quarantined S3Settings.prefix surface).

## Load-bearing premises (TL-B — re-verify at build entry; receipts in A1/A2/A3)
| id | premise | receipt |
|---|---|---|
| P1 | `ASANA_CACHE_S3_PREFIX` is set at 4 TF sites (autom8y asana/main.tf:213/321/436/590, value `asana-cache/project-frames/`) and read by ZERO live consumers | A2 §core; live grep 2026-06-10 |
| P2 | The DF plane prefix is hardcoded: `storage.py:342` default `"dataframes/"` + `section_persistence.py:295`; `S3LocationConfig` (config.py:419) has NO prefix field | A2 §1 |
| P3 | The phantom: `TieredConfig.s3_enabled=False` (tiered.py:57), constructed with defaults only in prod; tiered.py:49 docstring claims an env binding that does not exist (plain dataclass, not BaseSettings); factory.py:209 maps tiered→Redis | A2 §1E; A3 AP-2 (spot-checked) |
| P4 | 11 live namespaces (incl. tasks/=385k keys, legacy task-cache/=128k, fossil project-frames/=2,243 newest 2025-10-02) vs 4 scoped warmer grants + 2 full-bucket principals (ECS task role, IAM user `autom8`) | A1 census + live listings |
| P5 | **WRITER-UNKNOWN — UNATTRIBUTED, γ-0 discovery** [CH-01 remediated]: the active `asana-cache/tasks/` writer is NOT in autom8y-asana@8f9051b1 (no prod `S3CacheProvider(` construction; objects written 06-06/06-09). A1's `autom8_adapter.py:300` attribution REFUTED by A2 (provider-agnostic set_versioned; prod provider=Redis). The `main.tf:1218`-comment provenance handle cited in A2/TDD is a PHANTOM ANCHOR (adversary-verified absent from live TF — strike it at build entry); the only honest tag is UNATTRIBUTED. Cross-repo; autom8 monolith repo absent locally | A2 §monolith + main-thread grep + ADVERSARY-REPORT CH-01 |
| P6 | The #121 cure reads via pinned `_DURABLE_TASK_CACHE_PREFIX="asana-cache"` (null_number_recovery.py:148) — correct locally, an orphan if not subsumed (G-PROPAGATE) | PV-PINNED, live |

## Phase-α scope (10x-dev — Python only, no TF, no prod mutation)
1. `src/autom8_asana/storage_namespace.py` — the registry (all 11 namespaces; `TASK_CACHE.writer_owner.code_anchor=None` DECLARED-UNKNOWN, not fabricated).
2. `scripts/gen_namespace_config.py` → checked-in `terraform/services/asana/namespaces.gen.json` (initially byte-equal to current TF literals → β-1 is a no-op refactor).
3. `DurableTaskCacheReader` (wraps the null_number_recovery raw-boto3 pattern; prefix from `TASK_CACHE.prefix`); the cure's pin derives from the registry (subsumed).
4. RETIRE the phantom: delete `s3_enabled` + dead cold-path gates + the FALSE tiered.py:49 docstring; factory comment updated.
5. `tests/arch/test_namespace_contract.py` — t1 writer-owner-or-EXTERNAL · t2 IAM↔namespace+verbs · t3 no-literal-outside-registry · t4 no-phantom-backend-config · t5 FOSSIL⇒no-PUT/DELETE. **Each with a G-THEATER RED fixture** (e.g. add an unregistered literal → t3 RED; grant on unmapped prefix in the .gen.json → t2 RED).
6. `tests/arch/test_namespace_gen.py` — the .gen.json regeneration diff-test.

## TL-A falsifiable predictions (each w/ expiry)
- **FP-1**: post-Phase-α merge, introducing a NEW S3 prefix literal in src/ outside the registry fails CI (t3 RED) — demonstrate by committing the broken fixture in a test branch. Falsified-if: such a literal passes CI. Expiry: 2026-09-30.
- **FP-2a** [CH-02 remediated]: at Phase-α merge, `namespaces.gen.json` is byte-equal to the values
  currently in the checked-in TF env blocks (falsifiable NOW by diff). Expiry: 2026-09-30.
- **FP-2b** [CH-02 remediated]: the β-1 refactor (env/locals derivation only — IAM resources EXCLUDED)
  produces a no-op plan against the then-current TF state. Falsified-if: any resource diff in the
  env/locals scope. Expiry: 2026-12-07 (≤180d). **CONCEDED (adversary CH-02 finding): deployed-vs-TF
  IAM drift EXISTS today** — checked-in TF scopes the ECS S3 grant (main.tf:955-959/1046-1050/1137-1140)
  while the LIVE deployed policy is full-bucket `autom8-s3/*`; reconciling that drift is a β-3
  PRECONDITION (enumerate the receiver write-surface first), not part of the β-1 no-op claim.
- **FP-3**: post-Phase-α, `DurableTaskCacheReader` returns MRR=1500 for gid 1207519540893045 via the registry-derived prefix (live smoke parity with the cure). Falsified-if: ≠1500 or AccessDenied. Expiry: 2026-09-30.
- **FP-4** [CH-03 remediated, narrowed]: the t1 test's ASSERTION MECHANICS are RED-proven by the broken
  fixture (an unregistered namespace entry injected at the test boundary fails t1). The LIVE "12th
  namespace appears in S3" claim is NOT falsified by the stub (per integration-boundary-fidelity
  Layer-1 — a stub cannot prove live enumeration): the live falsifier is a separate, registry-vs-bucket
  reconciliation PROBE (read-only `aws s3api list-objects-v2 --delimiter /` diffed against the registry),
  specced in TDD as a scheduled/manual check, not claimed as CI coverage. Expiry: 2026-09-30.

## TL-C adversarial dispositions
- **"Zero live readers ⇒ why bother?"** — The saga's #120 died on a then-latent surface; AP-1 latency is the hazard class. The contract is cheap insurance (Phase-α ≈ 1 build) against a proven-fatal class. DISPOSED: build.
- **"The .gen.json could drift from the registry"** — that IS t-gen (the diff-test); drift fails CI. The TF side still requires a human apply (β) — named as detection-grade, not prevention-grade, at the TF boundary; prevention lands only at the Python boundary. HONEST LIMIT.
- **"N=2 might not satisfy the throughline's 'distinct satellite' gate"** — same-satellite/different-altitude; promotion ruling DEFERRED to the eunomia/Pythia custodian (UV-P in TDD §6). Not claimed.
- **"IAM tightening could break the receiver"** — β-3 (ECS full-bucket → scoped) is HIGH-risk and gated on enumerating the receiver's actual WRITE surface first; explicitly an operator-gated apply with rollback. Not in Phase-α.

## Operator decision points (surfaced, NOT executed)
β-1/β-2/β-3 TF applies (each separately gated; β-3 needs the ECS write-surface enumeration first) ·
the γ-0 writer-discovery task assignment (autom8 monolith owner) · the eunomia N=2 promotion ruling.

## DEFER watch-register (not scope-crept)
CHANGE-001..005 · UK-2 · SEAM-2/AC-6/CR-3 clocks · Node20 non-deploy sweep (06-16) · #97 · the
128k-key legacy task-cache disposition (AP-7; registry lists it FOSSIL-candidate, owner TBD at γ).

## Rungs (never round up)
This is **designed** (pending A5 adversary verdict). NOT built. "Structurally unaddressable" becomes
TRUE only when a misconfigured consumer cannot pass CI (post-Phase-α merge) — and at the TF/IAM
boundary only detection-grade until β applies land. Next `/frame` → `10x-dev/framing`.
