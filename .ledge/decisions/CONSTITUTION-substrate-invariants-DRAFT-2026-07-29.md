---
type: decision
artifact_subtype: constitution
artifact_id: CONSTITUTION-substrate-invariants
title: "Substrate Constitution — the six RC invariants as standing fleet law (RC-A..F + F5-5)"
created_at: "2026-07-29"
authored_by: structure-evaluator (arch, co-seated 10x-dev) — S9 doctrine authoring, substrate-v2-epoch WAVE-2
status: draft
landing_status: "LANDING-HELD-TO-S8-GREEN — checkpoint-gated, NOT a door; do not arm auto-merge"
initiative: substrate-v2-epoch
sprint: S9
rite: arch (authoring) / 10x-dev (landing)
evidence_grade: MODERATE
evidence_grade_rationale: >
  Self-authored corridor doctrine; caps at MODERATE per self-ref-evidence-grade-rule.
  STRONG is the eunomia epoch-exit attestation (S12), after the cutover gate (S8/P5)
  proves the six constructions against live parity. Law is not enshrined before proof:
  landing is held to S8-green by potnia ruling.
constitution_of_record: "autom8y-asana/.ledge/decisions/ (where R24-R34 live); fleet inheritance rides the S10 template-kit, NOT a shared filesystem path (pythia UV-P-4)"
related_artifacts:
  - CHARTER-substrate-v2-epoch-2026-07-27
  - TDD-substrate-v2
  - DP-3-consumer-contracts
  - DP-2-v2-storage-shape
  - RULINGS-operator-interview-fleet-constitution-2026-07-24
  - DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27
companion_plan: PLAN-substrate-doctrine-memory-and-teeth-DRAFT-2026-07-29
tags: [substrate-v2, constitution, fleet-law, RC-invariants, by-construction, refuse-loud, DRAFT]
---

# Substrate Constitution — the six RC invariants (RC-A..F)

> **DRAFT — LANDING-HELD-TO-S8-GREEN.** This is standing fleet law *in draft*. It does
> NOT land in wave-2. Landing is checkpoint-gated on the S8 cutover gate rendering
> green (P5): the fleet does not enshrine law the proving ground has not yet proven.
> Authored by structure-evaluator; adversary review (arch-adversary) follows; landing
> PR (principal-engineer) opens only post-S8-green. No auto-merge armed.

## §0 — What this is

The 2026-07-27 wound: `active_mrr` served **$79,585 — 14 days stale — under a
false-fresh "verified 1m ago" signal**; the true value was **$84,385**. Root-cause
analysis found not N bugs but **six broken invariants** with N symptoms. Those six
become the acceptance invariants of substrate-v2 and, extracted here, the **standing
law every autom8y-\* substrate surface must satisfy**.

Asana is the proving ground; this doctrine + its reusable forms are the deliverable
that unblocks the same reconstruction across the fleet (charter P1/P12). "Unblocked"
means the next repo's substrate is a **template application**, not a research project.

**Enforcement posture (charter P3 + P11 — binding on every article below):**
- **Primarily by construction.** A violation is *unconstructable* — there is no path
  to author it — not *guarded against* after the fact. Subtraction of the hazard class
  beats proliferating guard machinery.
- **CI teeth used SPARINGLY, only where construction cannot reach** (e.g. bridge-sunset
  expiry, where time passing is not a code property). **No blanket repo-level guard
  suites** — the operator deliberately did not select them as the doctrine home.
- Each article states its construction AND, honestly, its floor where Python cannot make
  a thing compile-time impossible. The teeth are enumerated once, in §2 and the companion
  plan; they are not re-invented per article.

## §1 — The six laws

Each law is fleet-general (the invariant), then its **construction** (why the violation
is unbuildable), its **honest floor** (fail-loud or the one CI tooth where construction
cannot reach), and the **v1 wound it retires**. The asana realization is the frozen TDD
(seams v1.0-frozen-2026-07-29); the *law* is what a sibling repo inherits.

### RC-A — Single source of truth per (project, entity)

**LAW.** For each addressable unit `(project, entity)` there is exactly **one** artifact,
**one** writer, and **one** authority pointer. No second copy exists for another copy to
disagree with — agreement between copies is never *asserted*, it is *subtracted*.

- **Construction (impossible-by-construction).** One typed identity → one artifact → one
  pointer. The pointer swap is a true compare-and-swap; version-IDs are collision-free;
  the "N copies / M writers / nothing asserts agreement" state cannot be built because
  there is no second copy and no second writer.
- **Honest floor.** Absence raises loudly (`ArtifactMissing`), never a silent null-pair.
  Two concurrent rebuilders cannot silently clobber — the CAS loser is rejected, not
  overwritten. (CAS is a construction property; no CI tooth is added for RC-A.)
- **Retires.** The double-write cache-location; the consolidated-vs-per-section duality.

### RC-B — Freshness is content-derived truth, not write-time metadata

**LAW.** A number's freshness is a **pure function of the content it was built from** —
the instant real content was last fetched, and a digest of the value-bytes — never a
write-time stamp, mtime, or probe signal. **A probe may schedule a re-fetch but can never
advance freshness.** Under incremental reuse, an artifact ages by its **stalest**
constituent (a MIN-fold over per-section content-fetch instants); it is never re-stamped
whole-fresh.

- **Construction.** Freshness = f(`built_from_live_at` = MIN over section content-fetch
  instants, `content_digest` over canonicalized value-bytes). The re-stamp field and the
  probe-to-stamp bridge are **deleted** — no CLEAN-stamps-fresh path exists, so the
  null-watermark false-CLEAN class is unconstructable at both artifact and section
  altitude.
- **Honest floor (fail-loud).** Serving refuses past SLA (`STALE`) or on digest mismatch
  (`CORRUPT`). **SLA governance is the whole truth-content of RC-B**: an ungoverned SLA
  re-serves the wound with a green proof — SLA values are operator-visible and their
  change is a governed act, not a config edit.
- **Retires.** The "verified 1m ago" false-fresh signal on 14-day-stale data.

### RC-C — Plane-correctness by construction

**LAW.** The plane/address discriminator is **required and non-defaultable**: a
plane-blind write is a **type error, not a runtime accident**. Refuse-loud is a property
of **one read choke-point**, never per-call-site discipline. An explicitly non-servable
member fails loud **at construction**; the servable set is **registry-derived** (single
source), never a hand-maintained second enum that can drift.

- **Construction (omission unconstructable).** The discriminator has no `None` default and
  no legacy key-builder to fall through to; under mypy-strict an omitted/mistyped
  discriminator is a static type error. A writer that never mentions the discriminator
  cannot construct an identity.
- **Honest floor (disclosed, per OQ-2).** An explicitly non-servable member is
  **fail-loud-at-construction** (`__post_init__` raises), **NOT** labeled by-construction —
  mypy is satisfied by any enum member. Boundary string-coercions must **coerce-or-refuse**
  (unknown string → refused, never silent legacy). Teeth: mypy-strict; the exhaustiveness
  tooth; the import-forbid tooth (§2).
- **Retires.** The enumerated call-site guard that drifted and missed a whole persistence
  layer (SCAR-SEAM1-PROBER-001).

### RC-D — No immortal bridges; every migration has a forcing function

**LAW.** The substrate has **no dual-read / dual-plane fallback**. A migration is a
**scheduled cutover event with an operator door**, never a lever left open. Any bounded
bridge (e.g. a parity harness) is **test-scoped**, deleted with its harness, and carries a
`SUNSET_AFTER` date that **fails CI past expiry**. Extending a `SUNSET_AFTER` requires an
**operator-visible ruling** — a serial date-bump is the immortal bridge re-entering with
receipts.

- **Construction.** The legacy-fallback capability does not exist in the substrate package;
  there is no code path to a second plane to keep alive.
- **Honest floor (the one canonical tooth).** `SUNSET_AFTER` expiry is enforced by a CI
  tooth because **time passing is not a code property** — construction cannot reach it.
  This is P11's named example of "teeth where construction cannot."
- **Retires.** The dual-plane bridge that has been "temporary" and immortal since
  2026-06-09.

### RC-E — Atomic, side-effect-explicit, rate-safe rebuild

**LAW.** Building **never mutates the live artifact**. A rebuilder writes only to a
**staging** version, validates it, then performs **one atomic pointer swap LAST**; a
partial or failed build leaves live untouched (**partial ≠ corrupt**). The read capability
has **no write method** — a "read-only recompute" cannot persist. Every live fetch routes a
**paced primitive** (AIMD / 429-banking, bounded concurrency, per-day budget); no un-paced
path exists.

- **Construction.** Reader and rebuilder are distinct capability types (the reader exposes
  no write; never the same object). Writes are staging-only until one atomic monotonic CAS
  swap after validation. All live I/O delegates the paced fetcher — the rebuilder never
  re-implements pacing.
- **Honest floor.** validate-before-swap is construction-enforced (a swap consumes a
  `ValidationReceipt` mintable only by `validate()`, or an ordering test locks it). The
  capability separation is enforced in CI by mypy-strict. Rate-safety is a delegation
  property, not a tooth.
- **Retires.** The "read-only path writes prod mid-fetch"; the rebuild-429-storm.

### RC-F — Observability that cannot read green while broken

**LAW.** Provability is evaluated on a schedule **independent of both serving and
warming**, through the **same predicate serving uses**. The expected-set is **two-sided**
(registry ∪ store enumeration) so an unregistered-but-served artifact cannot rot green.
**Absence fires** (never silence); incompleteness fires; the evaluator's **own silence
fires** (self-heartbeat). **Alarms assert provability, not liveness** (P2).

- **Construction.** A scheduled evaluator reads each artifact's proof via the identical
  `is_provable` predicate serving calls — the mechanical basis of "cannot read green while
  serving refuses." Missing artifact → `provable=0`, never silence.
- **Honest floor (fail-loud).** Heartbeat proves the evaluator RAN; completeness (two-sided)
  proves it COVERED every artifact; native no-data covers the evaluator dying. Division of
  labor: the evaluator asserts *data* provability; a serve-path defect is caught by a
  distinct receiver-refusal/health SLI — neither is retired believing the other covers it.
- **Cutover obligation.** Cutover evidence must include **≥1 observed end-to-end FIRED
  alarm** (synthetic unprovability → operator-visible notification) — closes the
  alarm-action void (SNS-gap precedent on record).
- **Retires.** Query-gated alarms; the dead-man on a dead metric.

### Article F5-5 — Mandated typed client SDK (ratified P11 constitutional law, 2026-07-29)

**LAW.** Delegated-fleet consumers consume a refuse-loud substrate **ONLY through a
sanctioned client library that raises on `Refused` inside the consumer's own process.**
Server-side construction (typed choke-point + non-2xx refusal) makes refusal maximally loud
*at the boundary* but cannot construct correctness into a process the substrate does not
own; the mandated SDK is the **sole mechanism that reaches inside**. This generalizes the
MCP island's raising client from an *implementation accident* to *fleet law*.

- **Ratification.** DP-3 §Ratification record, 2026-07-29 — operator ruled `ratify`; F5-5
  is P11 constitutional law and is carried here.
- **Asana realization (the proving-ground shape, not the fleet-universal law).** Refusals
  cross the wire as **424 Failed Dependency + `Retry-After`** (bound to the rebuild
  schedule) + a dedicated **`substrate_refusal_count` SLI** + RC-F alarms; refusal bodies
  are **shape-hostile** (a sloppy client that ignores status and parses the body gets a
  PARSE failure, not an empty success); **no `Refused` is ever a 200**. The v1
  `ADR-serve-stale-within-bound` (200-with-a-stale-flag — the exact confidence-labelled
  stale number RC-B forbids) is **SUPERSEDED, executed** 2026-07-29.

## §2 — Enforcement: construction-first, teeth sparingly

The doctrine home is **not** a blanket guard suite (P3/P11). Enforcement is the
constructions in §1. Where construction genuinely cannot reach, exactly **four sparing
teeth** apply — transcribed from the frozen TDD (§3/§4/§11), not invented here. The full
register, with the false-positive gate each tooth passes, is in the companion plan.

| Tooth | Serves | Why construction cannot reach it |
|-------|--------|----------------------------------|
| **mypy-strict** (repo-wide `strict = true`) | RC-C (required discriminator), RC-E (capability separation), RC-B (frozen value types) | Python has no compile step; without CI running mypy-strict a type-level "impossible" is only an editor hint |
| **Exhaustiveness tooth** — `typing.assert_never` on every `Provable\|Refused` consumer | RC-C (serving) | The sum type makes a bare value unobtainable *in principle*, but a consumer can still fail to handle the `Refused` arm; only mypy exhaustiveness catches the unhandled arm (net-new; zero uses today) |
| **Import-forbid tooth** — raw reads private to `{serve, rebuild}`; core imports no infra | RC-A / RC-C (no gate-bypass), whole-design dependency legality | Python has no true module-private / dependency-direction enforcement; only an import-layer lint/mypy tooth forbids the import |
| **`SUNSET_AFTER` expiry tooth** | RC-D | Time passing is not a code property; only a CI check comparing `now()` to the sunset date can make an immortal bridge fail. Extension requires an operator ruling (C11) |

Everything else is construction or fail-loud. No per-call-site guard, no query-gated alarm,
no re-consolidation step, no result-cache above the freshness gate — each such absence is a
broken v1 invariant made unconstructable, not guarded.

## §3 — Landing model (pythia UV-P-4 resolution)

- **Constitution-of-record = `autom8y-asana/.ledge/decisions/`** — the same home where the
  fleet constitution R24–R34 already lives (`RULINGS-operator-interview-fleet-constitution-2026-07-24.md`).
  This doctrine lands there as a sibling on landing (post-S8-green).
- **Fleet inheritance rides the S10 template-kit** (template application per charter P12),
  **NOT a shared filesystem path.** Sibling autom8y-\* repos inherit these invariants by
  applying the kit and re-constructing their substrate against them — not by reading a
  cross-repo mount. "The next repo's reconstruction is a template application."

## §4 — Operator surface items (non-blocking — for the operator, not landing blockers)

Recorded here per the pythia UV-P-4 resolution; neither blocks this draft.

### SURFACE-i — Charter P11's literal `.a8/knossos` is falsified on disk

Charter P11 names the doctrine home as "the fleet-constitution level (`.a8/knossos`)".
Direct probe (2026-07-29): `/Users/tomtenuta/Code/a8/.a8/knossos` → **No such file or
directory**; `.a8/` contains only `autom8y/`; zero git-tracked `a8/knossos` path exists.
The on-disk `.knossos/` directories are **runtime/orchestration state** (`ACTIVE_RITE`,
`INVOCATION_STATE.yaml`, `PROVENANCE_MANIFEST_*.yaml`, `sync/`, `worktrees/`), **not
doctrine homes**. P11's own hedge — *"if wrong, amend here"* — invites the amendment: the
real constitution-of-record is `.ledge/decisions/` (§3), and P11 should be amended to say
so. **Non-blocking**: this draft already lands at the correct home; the amendment is a
charter-hygiene act for the operator.

### SURFACE-ii — T3 note: same repo, disjoint files (not disjoint repos)

The shape's T3 implied a cross-repo split (law in one place, kit in another). The pythia
UV-P-4 resolution collapses that: **the law (this constitution) and the S10 template-kit
land in the SAME repo (`autom8y-asana`) on DISJOINT files** — the law at
`.ledge/decisions/CONSTITUTION-substrate-invariants-*.md`, the kit as the S10 deliverable.
Fleet inheritance is by kit application, not by a shared path. **Non-blocking**: a framing
correction for the operator's model; it changes no artifact location in this wave.

## §5 — Provenance and grade

- **Grade: MODERATE** (self-ref ceiling; self-authored corridor doctrine). STRONG is the
  eunomia epoch-exit attestation (S12) after the S8 cutover gate proves the six
  constructions against live parity (P5). Law is not enshrined before proof — hence the
  landing hold.
- **Sources (transcribed, not re-derived):** the six invariants + P1–P12 —
  `CHARTER-substrate-v2-epoch-2026-07-27`; the RC constructions, five frozen seams, and the
  four teeth — `TDD-substrate-v2` §3/§4/§11 (seams v1.0-frozen-2026-07-29); F5-5 + the 424
  status class + the stale-200 supersession — `DP-3-consumer-contracts` §Ratification record;
  the constitution-of-record home + numbering precedent —
  `RULINGS-operator-interview-fleet-constitution-2026-07-24` (R24–R34).
- **Companion:** the scar/ADR-memory update plan and the sparse-CI-teeth register are in
  `PLAN-substrate-doctrine-memory-and-teeth-DRAFT-2026-07-29.md`.
