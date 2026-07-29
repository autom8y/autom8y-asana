---
type: decision
decision_subtype: decision-packet
artifact_id: DP-2-v2-storage-shape
id: DP-2
title: "DP-2 — v2 storage-shape commitment: artifact-shape (F1) + key/schema (F3)"
created_at: "2026-07-29T08:52:09Z"
author: architect
status: accepted                       # recognized lifecycle value
lifecycle_status: RATIFIED-BY-OPERATOR
ratified: "2026-07-29 — operator in-channel one word ('ratified'), house one-word precedent = recommendations as staged: sub-1 shape C · sub-2 entity-after-project · sub-3 moot (C needs no bucket-versioning). S3-atomicity SVR discharged at ratification — see §Ratification record."
schema_version: "1.0"
rite: 10x-dev
initiative: substrate-v2-epoch
sprint: S1
door: "#2 (charter one-way-door register) — v2 key/schema shape; post-cutover load-bearing"
retitle_ack: "operator acknowledged the retitle 'storage-shape commitment: F1 artifact-shape + F3 key/schema' in the 2026-07-28 dispatch — recorded, not re-asked"
blocked_until_ratified: "S3 (storage/keys build)"
evidence_grade: MODERATE
context: >
  Door #2: the physical shape v2 stores each (project, entity) artifact in, and the
  key it is addressed by. Post-cutover this is load-bearing and a one-way door
  (charter). The Phase-1 draft chose a versioned-immutable artifact + atomic pointer
  (Option C) but rejected the simpler single-object Option A on a FACTUALLY WRONG S3
  atomicity premise (arch-adversary AV-4). This packet corrects that premise, extends
  the slate with the three options the adversary named (A-prime, C-prime, E),
  genuinely re-evaluates, and carries the adversary's F1/F3 dissent verbatim (C4).
decision: >
  RECOMMENDATION (operator rules): HOLD Option C (versioned-immutable + atomic CAS
  pointer) on CORRECTED grounds + C3 teeth — but Option A-prime (single object + proof
  in S3 object metadata) is now genuinely competitive and a legitimate ratification if
  simplicity is weighted over parity-version-pinning. Key schema: entity-segmented,
  entity_type REQUIRED (RC-C, not negotiable), segment order entity-after-project.
consequences:
  - type: positive
    description: "Whichever shape is ratified, the frozen Seam-2 semantics (read_current/stage_version/swap_pointer) hold — the seam is layout-stable; only the physical realization changes."
  - type: negative
    description: "One-way post-cutover: reversing the ratified shape after v1 deletion is expensive. Ratify with the corrected premise, not the draft's false one."
    mitigation: "S2 receipts the S3 atomicity claim (SVR bash-probe/docs-cite) before the build locks the shape; two-way during dark-build/parity."
related_artifacts:
  - TDD-substrate-v2
  - ADR-substrate-v2-fork-register
  - ADVERSARY-substrate-v2-design-s1
  - CHARTER-substrate-v2-epoch-2026-07-27
tags: [substrate-v2, one-way-door, storage, key-schema, operator-packet]
---

# DP-2 — v2 storage-shape commitment: artifact-shape (F1) + key/schema (F3)

> **Operator decision-packet. Door #2. RATIFIED-BY-OPERATOR 2026-07-29** (in-channel one-word
> precedent — recommendations as staged; §Ratification record). The retitle ("storage-shape
> commitment: F1 + F3") was acknowledged by the operator on 2026-07-28. **S3 (storage/keys build)
> is UNBLOCKED.**

## The question

For each `(project, entity)`, what PHYSICAL shape does v2 store the single canonical artifact in,
and what KEY addresses it? Two coupled sub-decisions:

1. **Artifact shape (F1):** how the materialized frame + its freshness proof + per-section
   provenance are physically laid out and atomically published.
2. **Key/schema (F3):** the addressing key. **This half is settled by RC-C and is NOT negotiable:**
   `entity_type` is a REQUIRED, non-defaultable component of the key (no `str | None` default, no
   legacy entity-agnostic key-builder — the exact hole that caused the wound). The only open F3
   question is segment ORDER (entity-after-project vs entity-before-project).

## Why this is a one-way door

Post-cutover, every consumer, the rebuild, the observability evaluator, and the fleet-unblock kit
depend on this shape. Changing it after v1 deletion (S11) means re-migrating live prod data with no
v1 fallback. Charter registers it as Door #2. It is TWO-WAY during dark-build + the parity window
(v1 still exists) and ONE-WAY once v1 is deleted.

## CORRECTED premise (C4 — the draft was factually wrong about S3)

The Phase-1 draft rejected Option A arguing *"overwrite of a large parquet on S3 is not truly
atomic under multipart — a failed multipart PUT can leave a corrupt object; a reader mid-overwrite
has no consistent pointer."* **This is false.** S3 object replacement is **atomic at the object
level**: a GET during an overwrite returns the complete OLD object (strong read-after-write
consistency, no torn reads); an incomplete/failed multipart upload is NEVER visible as the object;
a failed PUT leaves the prior object intact. [VERIFIED 2026-07-29 — the SVR docs-cite was discharged
AT ratification (§Ratification record, verbatim AWS quotes): the premise is no longer DOMAIN-PRIOR.
An S2 integration-probe corroboration remains welcome but is optional.] The TRUE reasons to prefer a versioned shape are rollback, atomic
proof+version co-publication, and version-pinned parity reads — NOT atomicity. **An operator
ratifying a one-way door on a false atomicity premise is a premise-integrity failure; this packet
carries the corrected ledger.**

## Corrected + extended option slate

| Option | Shape | Atomicity (corrected) | Rollback | Parity version-pin | App machinery | Terraform coupling |
|--------|-------|-----------------------|----------|--------------------|---------------|--------------------|
| **A** consolidated single object, overwrite | one `frame.parquet`; proof sidecar | atomic at object level (P12) — but proof-sidecar is a SECOND object → torn window between frame + proof | none | none | least | none |
| **A-prime** single object, proof in S3 object metadata | one object; proof in object metadata + per-section provenance in parquet file-metadata; one atomic PUT | atomic; **closes A's sidecar torn window** (proof co-published in the one PUT) | none | none (or via S3-native versioning) | least | none (metadata) |
| **C** versioned-immutable + app pointer **[DRAFT CHOICE]** | `v{N}/frame` immutable + `current` pointer carrying proof | atomic (small-object pointer CAS) | yes (SLA-bounded) | yes (pin `v{N}`) | `v{N}/` + `gc_versions` | none |
| **C-prime** S3-native bucket versioning of the same shape | overwrite + native VersionId + lifecycle-rule GC | atomic; **dissolves C3 version-ID collision** (S3 assigns IDs) | yes (native VersionId) | yes (native VersionId) | none (removes `gc_versions`) | **yes — bucket versioning is terraform (Door #4 surface)** |
| **E** versioned manifest over immutable per-section objects (Iceberg/Delta) | manifest names immutable section objects; version = manifest | atomic (manifest swap) | yes | yes | manifest + section GC | none |
| **D** null — keep dual layout | — | — | — | — | — | — REJECTED (the disease: the DEFECT's second split + RC-D immortal bridge) |

**E note (RK1):** E is the only shape that removes the whole-frame write amplification (only changed
sections re-staged). But the reader-side concat + `(office_phone, vertical)` cross-section dedup is
exactly the DEFECT's vintage-mixing locus (`$83,385`/63-combos artifact). The anti-B argument
transfers and likely still defeats E. RK1 is instead answered at the FETCH layer by C1 (per-section
provenance — re-fetch only stale sections), so E's write-amplification win is largely moot.

## Recommendation + rationale (genuinely re-evaluated — HELD at C, but the choice is close)

**HOLD Option C** (versioned-immutable + atomic CAS pointer) **on the corrected grounds + C3 teeth
(collision-free version-IDs + `If-Match` CAS)**, with **Option A-prime named as the strongest simpler
alternative and a legitimate operator ratification.**

I genuinely re-evaluated whether to FLIP to A-prime (the coordinator invited it). With the false
atomicity premise removed, A-prime is much stronger than the draft implied — it is strictly simpler
(no `v{N}/`, no `gc_versions`, no pointer indirection), and proof-in-object-metadata + provenance-in-
parquet-metadata closes A's sidecar torn window in one atomic PUT. The three reasons I hold C rather
than flip:

1. **Terraform-independence (P9).** C's versioning is pure S3 keys — no terraform. A-prime's
   rollback/parity-pinning needs S3-native bucket versioning (C-prime), which is a terraform apply
   coupling storage to Door #4 under an operator reservation. C keeps the storage shape
   terraform-independent.
2. **PE-validated.** The principal-engineer rendered C BUILDABLE-AS-DRAWN; A-prime's
   parquet-metadata-provenance + object-metadata-proof mechanism is unvalidated (would be S2's to prove).
3. **Cleanest RC-E.** C's stage-validate-swap never mutates a served object (immutable versions +
   pointer flip); A-prime overwrites the live object in place (atomic, but a mutation of the served
   artifact). Immutable-served-objects is the more legible RC-A/RC-E realization.

**Honest counter-weight (do not discount):** the draft's rejection of A rested on a FALSE premise;
A/A-prime are genuinely viable and SIMPLER (P3 — "small enough to be obviously correct"). C's unique
wins are parity-version-pinning (valuable only at the one-time S8 gate, then permanent GC machinery)
+ immutable-served-objects + terraform-independence. **If the operator weights P3 simplicity over
those, A-prime is a legitimate ratification.** **C-prime is the synthesis** if the operator accepts
bucket-versioning terraform: it keeps C's semantics, DISSOLVES the C3 version-ID collision (S3
assigns IDs natively), and SUBTRACTS the `gc_versions` app code (lifecycle rule) — at the cost of
opaque IDs + Door-#4 coupling.

Key/schema (F3): entity-segmented, `entity_type` REQUIRED (RC-C — not negotiable); segment order
**entity-after-project** (`dataframes-v2/{project_gid}/{entity_type}/`) — preserves project-GID as
the primary partition (existing enumeration semantics), recommend CONFIRM.

## ADVERSARY DISSENT (verbatim — arch-adversary, rite-disjoint, ADVERSARY-substrate-v2-design-s1 §2)

> **Slate exhaustive?** NO — three real variants missing:
>
> 1. **Option A-prime — single object, proof embedded in S3 object metadata.** One atomic PUT
>    carries frame AND proof; no pointer, no versions, no GC, no torn window between frame and
>    sidecar. Strictly simpler than enumerated Option A and immune to A's stated two-object
>    incoherence. Its only deficits vs Option C are: no rollback, no retained history, no
>    version-pinned parity reads.
> 2. **Option C-prime — S3 bucket-versioning-native implementation of the SAME chosen shape.**
>    Overwrite + native VersionId + lifecycle-rule GC: removes the app-level `v{N}/` key machinery
>    and the `gc_versions` code entirely, at the cost of opaque version IDs and terraform coupling
>    (rides Door #4 surface).
> 3. **Option E — versioned manifest over immutable per-section objects** (Iceberg/Delta table-format
>    pattern; the B+C hybrid). Directly removes RK1's whole-frame write amplification (only changed
>    sections re-staged; the manifest version is the atomic unit). The ADR's anti-B argument
>    (reader-side concat + `(office_phone, vertical)` cross-section dedup = the DEFECT's vintage-mixing
>    locus) transfers and likely still defeats it — but the option is real, addresses the register's
>    own RK1, and was not named.
>
> **Choice defensible?** YES — but **on corrected grounds only**. The register's central argument
> against Option A is factually wrong about S3 semantics: *"overwrite of a large parquet on S3 is not
> truly atomic under multipart — a failed multipart PUT can leave a corrupt object; a reader
> mid-overwrite has no consistent pointer"* (ADR :138-141). S3 object replacement is atomic at the
> object level: an incomplete multipart upload is never visible to readers, a failed PUT leaves the
> prior object intact, and a reader mid-overwrite reads the complete OLD object (read-after-write
> strong consistency, no torn reads). [DOMAIN-PRIOR: S3 documented consistency + multipart semantics;
> falsifiable by an AWS-docs cite or an integration probe — see §6.] The TRUE case for Option C is:
> (a) rollback primitive; (b) proof + version-name published atomically in ONE small object (Option
> A's sidecar variant has a loud-but-real CORRUPT window; A-prime closes it); (c) version-pinned reads
> for the S7/S8 parity harness; (d) retained history. **An operator ratifying a one-way door on a
> false atomicity premise is a premise-integrity failure. The DP-2 packet MUST carry the corrected
> ledger** (condition C4).
>
> **Residual risks of the chosen shape (carry into the packet):**
> - **Pointer swap is not yet a real CAS.** H6's "version-monotonicity check" is read-then-check-then-PUT
>   — a cross-process TOCTOU. The coalescer (feasibility G7, [H12]) is in-process only; two rebuilders
>   in distinct processes (scheduled Lambda + force-warm CLI) race legally. Freeze S3 conditional
>   writes (`If-Match` ETag CAS on `current.json`) as the swap mechanism. (Condition C3.)
> - **Version-ID allocation can collide.** If VersionId is derived `max(list_versions)+1`, two
>   concurrent stagers both compute `v6`; [H7]'s letter forbids overwriting only a *pointed-to*
>   version, so the second `stage_version` may overwrite the first's staged bytes; the first then
>   swaps, writing ITS proof over the second's bytes → `Refused(CORRUPT)` on every read until next
>   rebuild. Fail-loud, not silent-wrong — but a self-inflicted outage class. Freeze collision-free
>   version IDs (UUID / timestamp / content-digest-addressed). (Condition C3; a digest-addressed
>   VersionId also makes identical rebuilds idempotent — advisory.)
> - **GC verdict (architect's pre-named attack): GC does NOT introduce a worse failure than the
>   duality it removes.** Every GC failure mode terminates loud: over-deletion or a reader holding a
>   reaped version → `ArtifactMissing` → `Refused(MISSING)`; GC-not-running → cost, not correctness.
>   The duality it replaces produced SILENT divergence. The tradeoff genuinely favors C. Steel-man
>   residual: the version+GC machinery is permanent operational surface purchased mainly for rollback
>   — and RC-B partially neuters rollback (a rolled-back older version is older; near/past SLA it
>   refuses). The operator should ratify knowing rollback's value window is bounded by the SLA.

## Consequences / reversibility per option

- **A / A-prime:** simplest; no rollback (accept: cutover rollback = restore v1; post-cutover a bad
  rebuild is fixed by the next rebuild). Two-way pre-cutover; one-way post.
- **C (recommended):** rollback (SLA-bounded) + parity-pinning + immutable served objects; needs C3
  teeth. Terraform-independent. Two-way pre-cutover.
- **C-prime:** C's semantics minus `gc_versions` + C3 collision; requires a bucket-versioning
  terraform apply (Door #4). Two-way pre-cutover.
- **E:** delta-write-efficient but re-introduces the concat/dedup vintage-mixing fragility (the DEFECT
  class). Not recommended.

## Requested ruling (one word per sub-decision)

1. **Artifact shape:** `A-prime` | **`C`** (recommended) | `C-prime` | `E`
2. **Segment order (F3):** `entity-after-project` (recommended CONFIRM) | `entity-before-project`
3. **(if C-prime or A-prime chosen)** accept S3-native bucket versioning as a Door-#4 terraform
   apply: `yes` | `no`

`entity_type`-required (RC-C) is not a ruling item — it is the non-negotiable substrate of the whole
epoch. **On ratification, S3 unblocks.**

## Ratification record — 2026-07-29

**Ruling received:** operator in-channel, one word — "ratified" — per the house one-word precedent
(telos-ratification pattern: recommendations as staged, unamended). Recorded by the orchestrator;
the operator was invited to flag if a narrower ruling was intended.

| Sub-decision | Ruling |
|---|---|
| 1 · Artifact shape | **C — versioned-immutable + atomic CAS pointer**, with the C3 teeth (If-Match ETag CAS on `current.json`; collision-free version-IDs) |
| 2 · Segment order (F3) | **entity-after-project** (`dataframes-v2/{project_gid}/{entity_type}/`) |
| 3 · Bucket-versioning terraform | moot — C chosen; not required |

**SVR discharge (the packet's own falsification hook — verified at ratification, read-only docs-cite):**

- **Atomicity:** "Updates to a single key are atomic. For example, if you make a PUT request to an
  existing key from one thread and perform a GET request on the same key from a second thread
  concurrently, you will get either the old data or the new data, but never partial or corrupt
  data." — AWS S3 User Guide, data-consistency model
  (docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html#ConsistencyModel, fetched 2026-07-29).
- **Read-after-write:** "Amazon S3 provides strong read-after-write consistency for PUT and DELETE
  requests of objects in your Amazon S3 bucket in all AWS Regions. This behavior applies to both
  writes to new objects as well as PUT requests that overwrite existing objects" (ibid.).
- **Concurrent writers (why C3's CAS is required — confirmed):** "Amazon S3 does not support object
  locking for concurrent writers. If two PUT requests are simultaneously made to the same key, the
  request with the latest timestamp wins... you must build an object-locking mechanism into your
  application." (ibid.)
- **The CAS mechanism exists:** `If-Match` ETag conditional writes are documented on PutObject,
  CompleteMultipartUpload, and CopyObject; ETag mismatch → `412 Precondition Failed`; concurrency
  edges → `409 Conflict` / `404 Not Found`; AWS Signature Version 4 required
  (docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html, fetched 2026-07-29).
- **Multipart:** an in-progress multipart upload is "not yet [a] fully written object" — never
  visible as the object before CompleteMultipartUpload (ibid.).

**Build notes handed to S3/S4:** the pointer swap must handle `412` (CAS lost — re-read, re-derive,
retry-or-refuse), `409` (concurrent-delete race), `404` (If-Match on an absent key); SigV4 is
mandatory for conditional writes.

**Consequence:** S3 (storage/keys build) is **UNBLOCKED**. The shape is TWO-WAY until v1 deletion
(S11 / DP-1); ONE-WAY after.
