---
type: review
status: rendered
artifact_id: ADVERSARY-substrate-v2-design-s1
title: "Adversarial challenge — Substrate-v2 whole design + F1-F6 fork register (S1 Phase-2)"
created_at: "2026-07-29T00:00:00Z"
author: arch-adversary
rite: arch (rite-disjoint critic; design author is 10x-dev architect — critic-substitution-rule holds)
initiative: substrate-v2-epoch
sprint: S1
phase: "Phase-2 (adversary track, parallel to principal-engineer feasibility)"
iter: 1
verdict: PASS-WITH-CONDITIONS
prod_touch: NONE
evidence_grade: MODERATE
evidence_grade_rationale: >
  Adversary self-assessment caps at MODERATE per self-ref-evidence-grade-rule.
  All grounding below is file-read of the S1 artifact set + the DEFECT/charter,
  read in full this dispatch. No AWS/Asana/network probes performed (prod_touch NONE);
  S3-semantics claims are marked DOMAIN-PRIOR and carry their own falsification hooks.
targets:
  - .ledge/specs/TDD-substrate-v2.md
  - .ledge/decisions/ADR-substrate-v2-fork-register.md
cross_references_read_in_full:
  - .ledge/specs/RC-acceptance-predicates-substrate-v2.md
  - .ledge/reviews/FEASIBILITY-substrate-v2-seams-s1.md
  - .ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md
  - .ledge/reviews/DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27.md
citations:
  - "assessment-methodology P-01/P-08 (Messick 1989: construct validity; underrepresentation) — frames AV-1/AV-8"
  - "assessment-methodology P-02 (Kane 2006: argument-based validity) — frames the F2 'current vs <=SLA-old' challenge"
  - "option-enumeration-discipline (slate-truncation checks) — frames AV-4/AV-5/AV-10"
  - "critique-iteration-protocol §3.4 (structural BLOCKING test) — severity calibration throughout"
---

# ADVERSARY — Substrate-v2 whole design + fork register (S1 Phase-2)

> Rite-disjoint falsification pass. The architect pre-named four attack seams (F5
> cross-process refuse; F1/F3 over-engineering + GC; F2 current-vs-SLA-old; F4 Python
> honest floor). Those were treated as FLOOR. The findings below include five surfaces
> the architect did NOT flag (AV-1, AV-2, AV-3, AV-6, AV-7) — the common-mode hunt.

## 1. Verdict

**PASS-WITH-CONDITIONS.**

No fork's provisional choice requires reversal. The whole design (6 modules / 5 seams /
one inward arrow / one read gate / one freshness predicate) survives genuine attack: I
attempted a construction of a silently-wrong-serve under each RC and found **zero silent-
wrong constructions that survive the design as INTENDED** — but I found **one seam whose
DRAWN text permits a D8-class false-fresh (AV-1)**, one under-specified check-binding
point that lets an implementation re-create false-fresh from memory (AV-2), one door
packet whose central technical premise is factually wrong about S3 (AV-4), and material
slate truncations on both operator doors. All are Phase-3-repairable without re-entering
the design; none reverses a choice. Conditions in §5: 7 MUST-FIX-PHASE-3, 4 CARRY-TO-BUILD.

Severity calibration: a finding is MUST-FIX-PHASE-3 when shipping the seam/packet
as-written would embed the defect into the frozen build contract or put a false premise
in front of the operator at a one-way door (critique-iteration-protocol §3.4 structural
test). Stylistic and residual-risk items are CARRY-TO-BUILD or noted inline as advisory.

## 2. Per-fork dissent register (F1-F6)

### F1+F3 — artifact shape + key schema → DP-2 (PACKET-GRADE DISSENT, carry verbatim)

**Slate exhaustive?** NO — three real variants missing:

1. **Option A-prime — single object, proof embedded in S3 object metadata.** One atomic
   PUT carries frame AND proof; no pointer, no versions, no GC, no torn window between
   frame and sidecar. Strictly simpler than enumerated Option A and immune to A's stated
   two-object incoherence. Its only deficits vs Option C are: no rollback, no retained
   history, no version-pinned parity reads.
2. **Option C-prime — S3 bucket-versioning-native implementation of the SAME chosen
   shape.** Overwrite + native VersionId + lifecycle-rule GC: removes the app-level
   `v{N}/` key machinery and the `gc_versions` code entirely, at the cost of opaque
   version IDs and terraform coupling (rides Door #4 surface).
3. **Option E — versioned manifest over immutable per-section objects** (Iceberg/Delta
   table-format pattern; the B+C hybrid). Directly removes RK1's whole-frame write
   amplification (only changed sections re-staged; the manifest version is the atomic
   unit). The ADR's anti-B argument (reader-side concat + `(office_phone, vertical)`
   cross-section dedup = the DEFECT's vintage-mixing locus) transfers and likely still
   defeats it — but the option is real, addresses the register's own RK1, and was not
   named.

**Choice defensible?** YES — but **on corrected grounds only**. The register's central
argument against Option A is factually wrong about S3 semantics: *"overwrite of a large
parquet on S3 is not truly atomic under multipart — a failed multipart PUT can leave a
corrupt object; a reader mid-overwrite has no consistent pointer"* (ADR :138-141).
S3 object replacement is atomic at the object level: an incomplete multipart upload is
never visible to readers, a failed PUT leaves the prior object intact, and a reader
mid-overwrite reads the complete OLD object (read-after-write strong consistency,
no torn reads). [DOMAIN-PRIOR: S3 documented consistency + multipart semantics;
falsifiable by an AWS-docs cite or an integration probe — see §6.] The TRUE case for
Option C is: (a) rollback primitive; (b) proof + version-name published atomically in
ONE small object (Option A's sidecar variant has a loud-but-real CORRUPT window; A-prime
closes it); (c) version-pinned reads for the S7/S8 parity harness; (d) retained history.
**An operator ratifying a one-way door on a false atomicity premise is a premise-
integrity failure. The DP-2 packet MUST carry the corrected ledger** (condition C4).

**Residual risks of the chosen shape (carry into the packet):**
- **Pointer swap is not yet a real CAS.** H6's "version-monotonicity check" is
  read-then-check-then-PUT — a cross-process TOCTOU. The coalescer (feasibility G7,
  [H12]) is in-process only; two rebuilders in distinct processes (scheduled Lambda +
  force-warm CLI) race legally. Freeze S3 conditional writes (`If-Match` ETag CAS on
  `current.json`) as the swap mechanism. (Condition C3.)
- **Version-ID allocation can collide.** If VersionId is derived `max(list_versions)+1`,
  two concurrent stagers both compute `v6`; [H7]'s letter forbids overwriting only a
  *pointed-to* version, so the second `stage_version` may overwrite the first's staged
  bytes; the first then swaps, writing ITS proof over the second's bytes →
  `Refused(CORRUPT)` on every read until next rebuild. Fail-loud, not silent-wrong — but
  a self-inflicted outage class. Freeze collision-free version IDs (UUID / timestamp /
  content-digest-addressed). (Condition C3; a digest-addressed VersionId also makes
  identical rebuilds idempotent — advisory.)
- **GC verdict (architect's pre-named attack): GC does NOT introduce a worse failure
  than the duality it removes.** Every GC failure mode terminates loud: over-deletion or
  a reader holding a reaped version → `ArtifactMissing` → `Refused(MISSING)`; GC-not-
  running → cost, not correctness. The duality it replaces produced SILENT divergence.
  The tradeoff genuinely favors C. Steel-man residual: the version+GC machinery is
  permanent operational surface purchased mainly for rollback — and RC-B partially
  neuters rollback (a rolled-back older version is older; near/past SLA it refuses).
  The operator should ratify knowing rollback's value window is bounded by the SLA.

### F2 — freshness model → auto-ratify

**Slate exhaustive?** YES, materially. (Asana events-API cursor polling is a mechanism
variant inside F2-4's "webhooks/events" umbrella; TTL-per-criticality is SLA
parametrization already in the model.)

**Choice defensible?** YES. F2-1 is the only option that is simultaneously P10-safe,
D8-subtracting, and legible; F2-2 institutionalizes the 429-storm; F2-3/F2-4 are
correctly deferred behind named rot-triggers (economical per P7).

**The architect's pre-named attack, answered honestly:** "build-from-live age" delivers
**"provably ≤ SLA-old," not "provably CURRENT."** This reframe is LEGITIMATE — currency
without a bound is unachievable for any cache (even F2-2 has verify-to-serve TOCTOU);
every option only bounds staleness; the charter expressly delegates the freshness model.
BUT the reframe concentrates the mission's entire truth-content into one number —
`sla_seconds` — and **the design nowhere governs that number** (AV-3, §3 RC-B). The
semantic delta ("current" → "≤ SLA-old at these SLA values") must be surfaced to the
operator WITH the per-entity SLA values at a door or the cutover gate; an ungoverned SLA
is an unratified narrowing of a ratified charter phrase. (Condition C8.) F2-3-in-the-
floor is NOT required: within-SLA staleness is bounded risk the operator already
implicitly ran at daily-warm cadence; the rot-trigger is the right instrument — but its
"[gate-tuned threshold]" placeholder must be quantified at S8 (advisory).

### F4 — atomic rebuild → auto-ratify

**Slate exhaustive?** Effectively yes at mechanism altitude (F4-2 and F4-3 are real
foils; S3-native versioning noted under F1/F3 is shape, not mechanism).

**Choice defensible?** YES — stage-validate-swap + capability-typed reader is the only
enumerated option making side-effect-freedom a type property. I CONCUR with the
feasibility finding that the 3-tooth honest floor is reachable, and with the honest
labeling (not compile-absolute).

**Surviving counter-constructions:**
- **Swap-before-validate is convention, not construction.** The `Rebuilder` holds an
  `ArtifactStore` that exposes `swap_pointer` at all times; [H10]'s "swap LAST and
  conditional" is prose. Construction sketch: a rebuilder impl calls
  `swap_pointer(aid, staged)` then `validate` — satisfies every type, violates RC-E-1
  intent. Cheap construction-level fix consistent with P3: `swap_pointer(aid, to,
  receipt: ValidationReceipt)` where only `AcceptancePredicates.validate()` mints the
  receipt. (Condition C9, CARRY-TO-BUILD — the fail-loud backstop plus a discriminating
  ordering test is an acceptable floor if the capability change is declined.)
- The cross-process pointer race and version-ID collision (above, F1/F3) are REBUILD-
  seam facts as much as store facts; they ride condition C3.

### F5 — consumer contracts → DP-3 (PACKET-GRADE DISSENT, carry verbatim)

**Slate exhaustive?** NO — one structurally distinct option missing, and it is the ONLY
one that reaches inside the remote process (the exact gap RK5 names):

1. **Option F5-5 — mandated typed client SDK.** Fleet-constitution law (P11's doctrine
   home): delegated-fleet consumers consume ONLY through the sanctioned client library,
   which raises on `Refused` in the CONSUMER's process. Server-side design (F5-2 + non-
   2xx) can only make refusal maximally loud AT the boundary; it cannot construct
   correctness into a process it does not own. F5-5 is the sole mechanism that does, and
   it composes with (does not replace) F5-2. The MCP island's raising client
   (feasibility G10) is a de-facto instance of it for ONE consumer; the packet should
   generalize it as constitutional law rather than leave it an accident of the island's
   implementation.

**Choice defensible?** YES in-process — F5-2 is the RC-C construction applied to
serving; F5-1 is the documented failure; F5-3 misplaces policy; F5-4 covers one
transport. The architect's own honesty about the cross-process boundary ("across the
wire `Refused` is just bytes") is correct and correctly door-routed.

**Packet-grade dissent items for DP-3:**
1. **Refusal envelope must be shape-hostile.** "non-2xx or explicit refusal envelope"
   (TDD RK5) under-specifies: a sloppy remote client that ignores status and parses the
   body must get a PARSE failure, not an empty list. Freeze: refusal bodies carry NO
   data-shaped fields (no `rows: []`, no zero-value aggregate) — refusal is structurally
   unparseable as success. (Condition C5.)
2. **The STALE→5xx-class recommendation is contestable — present it two-sided** (full
   argument in §4a). Un-enumerated middle option: **424 Failed Dependency** + dedicated
   refusal-count SLI + RC-F alarms.
3. **Retiring ADR-serve-stale-within-bound must be an EXPLICIT supersession
   disposition** in the packet — a ratified ADR (2026-06-03) dying as an implicit
   casualty of a seam invariant is silent supersession (AC-03 class). (Condition C5.)
4. Steel-man of the recommendation, honestly rendered: for every consumer that checks
   status codes — which includes the entire currently-shipped consumer surface (G9/G10)
   — F5-2 + non-2xx IS unbypassable today, and no enumerated alternative beats it
   server-side. The dissent is about the un-owned future consumer and the status-class
   semantics, not about the choke-point.

### F6 — observability → auto-ratify (terraform limb = Door #4)

**Slate exhaustive?** YES at alarm-source altitude, with one advisory gap: the slate
frames RC-F as DATA-provability only. A serve-path defect (choke-point/adapter bug
post-deploy) leaves all artifacts provable → evaluator green → consumers get 5xx: the
system is "broken" at the mission altitude while F6 reads green. This is covered — but
only by the receiver 5xx SLI, which is a DIFFERENT instrument owned by no seam. Name
the division of labor explicitly (evaluator = data provability; receiver SLI = serve
health; BOTH constitute "cannot read green while broken") so neither instrument is
retired believing the other covers it. (Advisory, fold into Seam-5 notes.)

**Choice defensible?** YES — F6-1 is the only option firing on all three
green-while-broken modes. The deeper holes are in §4b (evaluated-set drift, alarm-action
void); they harden the choice rather than reverse it.

## 3. RC-discharge attack results (A-F) — construction sketches

The strongest critique is a construction. For each RC I attempted to CONSTRUCT a
violation the design still permits. Result: no SILENT-wrong-serve construction survives
the design-as-intended; two constructions survive the design-as-DRAWN (AV-1, AV-2); the
rest terminate loud or are config/packet-altitude.

**RC-A — no surviving silent construction; one loud-outage construction.**
The version-ID collision race (F1/F3 above): two stagers → overwritten staging → proof/
bytes mismatch at swap → `Refused(CORRUPT)` storm. Loud, self-announcing, but a real
availability wound the seam can close cheaply (C3). The memory-tier copy (CP-5) is NOT a
second source of truth PROVIDED condition C2's binding rules are frozen — see RC-B.
Dark-build dual-state is by-design and bounded by cutover. RC-A discharge: **REAL**.

**RC-B — TWO surviving constructions; this is where the report's weight lands.**

- **AV-1 (MUST-FIX; the sharpest finding, un-flagged by architect or PE): the
  incremental rebuild resurrects D8 inside the Rebuilder.** Seam 3 as drawn: step 1
  "fetch content from live Asana ... **incremental allowed**, materializes a WHOLE
  version"; step 2 "compute content_digest + FreshnessProof(**built_from_live_at =
  fetch_instant**)" (TDD :322-323). The RK1 mitigation makes incremental reuse
  load-bearing ("reuse content-verified sections, re-fetch changed" — TDD :412, ADR
  :188-193). Construction: a rebuild re-fetches 2 changed sections, REUSES 31 cached
  sections, stamps the whole artifact `built_from_live_at = now`. The 31 reused
  sections' bytes were last verified against live Asana N days ago — yet the proof now
  asserts live-fetch-instant = now for ALL of them. "Verified-unchanged" by WHAT? If by
  a structural proxy (GID set / modified_since — the only P10-cheap options), a content
  edit invisible to the proxy is stamped live-fresh: **this is v1's probe-refreshes-
  freshness pattern, verbatim, relocated into the rebuilder** — the exact class RC-B
  exists to make unconstructable, and it violates the seam's own frozen invariant
  ("only a content-bearing rebuild advances freshness") for a path the seam explicitly
  authorizes. Honest fixes (either restores RC-B): (i) **per-section live-fetch
  provenance: artifact `built_from_live_at` = MIN over constituent sections' last
  live-fetch instants** — reused content keeps its old instant; the artifact honestly
  ages by its oldest section and forces full re-fetch cadence ≥ SLA (budget-
  quantifiable); or (ii) forbid content-reuse (incremental = write-side only), reviving
  the RK1 budget attack, which must then be answered with numbers. (Condition C1.)
- **AV-2 (MUST-FIX): check-binding points are unfrozen — a result-cache re-creates
  false-fresh from memory.** [H16] puts the gate inside `read`; CP-5 says the
  `SubstrateReader` "wraps the memory→S3 tier." Nothing freezes WHERE the two
  `is_provable` arms bind. Construction: a builder caches the `Provable(frame, proof)`
  RESULT in the memory tier; a frame validated at T0 with 10 minutes of SLA left is
  served at T0+2h, from memory, as Provable — stale-served with a green proof, no S3
  read, no gate. Simultaneously, the digest arm literally-per-read is a real cost
  (parse + canonical-serialize + sha256 per query) that tempts builders to skip it for
  the memory tier — silent divergence of the exact class [H1] was frozen to prevent.
  Freeze BOTH bindings: **age arm (time comparison) executes on EVERY logical read;
  digest arm binds at bytes-ingress from store; caching of `ServedNumber`/`Provable`
  results above the gate is FORBIDDEN — only proof-validated bytes may be tiered.**
  (Condition C2.)
- **AV-3 (CARRY): the SLA is the whole truth-content of RC-B and is ungoverned.**
  Construction: `sla_seconds` for offer set (by config drift, registry default, or an
  unreviewed edit) to 14 days → the wound scenario verbatim ($79,585, 14d old) is
  served PROVABLE with a green proof. Every mechanism works; the config defeats the
  mission. No artifact records who sets SLA values, where they are ratified, or that
  the operator ever sees them. (Condition C8; RC-F's absolute-age emission is the
  partial mitigant — an absurd SLA is at least visible.)

RC-B discharge: **REAL after C1+C2**; as drawn, FALSIFIED by AV-1.

**RC-C — no surviving plane-blind construction; one labeling defect.**
`EntityType.UNKNOWN` (cross-check d, §4d): an `ArtifactId(gid, UNKNOWN)` passes mypy
and dies at `__post_init__` — loud, at object birth, un-bypassable, but RUNTIME. It
cannot RESOLVE to a plane (it raises), so RC-C-1's falsification clause ("omits the
discriminator and still resolves to a plane") is not met — the closed-enum argument
survives. But RC-C-1's stated mode is BY-CONSTRUCTION ("compile/type error ... NOT a
runtime lint") and for the UNKNOWN branch that claim is not true. RC-acceptance OQ-2
already provides the disclosure valve. Either upgrade (a servable-subset type — noting
its real cost: a second enum that can drift from `EntityType`) or disclose the UNKNOWN
branch as FAIL-LOUD-at-construction per OQ-2. Truth-in-labeling, not redesign.
(Condition C6.) The str→EntityType boundary chain holds: `EntityType("unknown")` parses
to the UNKNOWN member and is then rejected by [H4] — loud at the adapter. RC-C
discharge: **REAL** (with C6 relabeling).

**RC-D — no surviving construction; one honesty note.**
The SUNSET_AFTER CI tooth converts immortality into a visible, auditable date-bump
commit. Residual: serial date-bumping IS the immortal bridge re-entering with receipts.
One doctrine line closes it: SUNSET_AFTER extensions require an operator-visible ruling.
(Condition C11.) RC-D discharge: **REAL**.

**RC-E — no surviving silent construction; two convention gaps.**
Swap-before-validate (F4 above, C9) and the cross-process race (C3). The P4
counterexample (read path writes prod) is genuinely unconstructable through the serve
capability — CONCUR with feasibility §2. Parity-window doubling of prod reads is named
and RC-E-4-covered in the acceptance doc. RC-E discharge: **REAL** (C3/C9 harden it).

**RC-F — one surviving green-while-broken construction.**
- **AV-6 (MUST-FIX): expected-set drift — the DMS-24h orphan class, one level up.**
  [H20]'s completeness metric compares `evaluated_count` vs `len(expected)` where
  `expected` is sourced from the warm-target registry. Construction: a (project,
  entity) is built and served but absent from the registry (refactor, new project
  onboarded by hand, registry edit) → evaluator never expects it → counts match →
  green, while that artifact rots and serves refusals (or worse, pre-C1, stale-
  provables). This is the SAME failure shape as the orphaned dead-man: the alarm's
  DOMAIN configured independently of the serving domain. Close two-sided: `expected` =
  registry (catches should-exist-but-missing) AND store enumeration under
  `dataframes-v2/` (catches exists-but-unregistered); a member of either set absent
  from the other fires. (Condition C7.)
- **AV-7 (CARRY): the alarm-action void.** The evaluator→metric→alarm chain terminates
  at a CloudWatch alarm whose ACTIONS are terraform (Door #4). A firing alarm routed to
  an empty/broken SNS target is green-while-broken at the human altitude — and this
  fleet has a live SNS-gap precedent on record. The cutover gate's evidence must
  include ONE observed end-to-end fired alarm (synthetic unprovability → operator-
  visible notification). (Condition C10.)

RC-F discharge: **REAL after C7**; heartbeat-only completeness is FALSIFIED by AV-6
(concurring with and extending PE's C5/[H20] — H20 is necessary, not sufficient).

## 4. Cross-check results (a)-(d) — attacks on the principal-engineer's findings

**(a) G11 collision routing + STALE→5xx-class recommendation.** The ROUTING is sound:
the collision is real (grounded at `query/models.py` :249/:428), retiring stale-200 is
charter-mandated (P2 + Non-goals; RC-acceptance :105), and it is a consumer-contract
change → the EXISTING DP-3 door, no new fork. CONCUR. The STATUS-CLASS recommendation I
CONTEST as presented:
- *Retry-amplification:* 5xx is retry-coded by default across HTTP clients AND by the
  island's own classifier (503 → retryable-warming, G10 note). STALE persists for
  minutes-to-hours (until next rebuild) — not a retry-clearable condition. 5xx without
  a distinct non-retryable code + `Retry-After` bound to the rebuild schedule, shipped
  on BOTH sides simultaneously, invites hot-retry storms and tells the remote LLM
  "retry" when the truth is "wait for rebuild." Sequencing constraint: consumer-side
  classification must land WITH or BEFORE the server flip.
- *SLO attribution:* refusal is "a feature, not an outage" (charter P2) — mapping it to
  5xx burns receiver availability-SLO for correct behavior and trains operators to read
  substrate staleness as receiver failure.
- *The visibility argument is weakened by the design's own RC-F:* PE argues 409 hides
  staleness from the receiver SLI. But F6-1 exists precisely to make staleness visible
  WITHOUT queries; the receiver SLI need not carry substrate health. A dedicated
  refusal-count metric (emitted at the choke-point) + RC-F alarms covers visibility
  with clean attribution.
- *Un-enumerated option:* **424 Failed Dependency** — semantically exact (request
  failed because a dependency's state is unprovable), non-retry-coded by default.
  VERDICT: PE's 5xx-class is DEFENSIBLE (one merged health signal, zero new metrics)
  but NOT dominant; DP-3 must present 5xx-class vs 424/409-class with the retry/SLO/
  attribution ledger above and the sequencing constraint. (Condition C5.)

**(b) [H20] completeness metric.** Necessary, NOT sufficient — see AV-6 (expected-set
drift construction) and AV-7 (action void). "Who watches the evaluator's own schedule"
IS adequately terminated by heartbeat + CloudWatch native no-data ([H23]) — that
terminal is real; the un-faked residuals are alarm-resource existence and action
routing, both Door-#4 surface, both covered by C10's end-to-end fired-alarm evidence.

**(c) [H1] digest canonicalization + [H5] raise-not-(None,None).** Both close REAL
divergence risks; neither masks a gap. [H1] is the correct freeze for RK2 — but it is
INCOMPLETE without a binding-point rule (AV-2): freezing WHAT is hashed while leaving
WHERE/WHEN unhashed invites the exact per-builder divergence it exists to prevent, plus
a per-read cost incentive to silently skip. [H5] is a clean hard-break from v1's
silent-(None,None) and correctly feeds both `Refused(MISSING)` and `provable=0`. One
alignment nit: TDD §3 RC-B says "serving re-hashes the served bytes" — under [H1] it
re-canonicalizes the parsed frame, not the parquet bytes; align the TDD text (folds
into C2).

**(d) EntityType.UNKNOWN vs impossible-by-construction.** `__post_init__` rejection
SUFFICES to keep plane-blind RESOLUTION unconstructable (UNKNOWN raises; it never
resolves to a plane; there is no legacy plane to default into — the closed-enum
argument survives because the hole terminates loud, not silent). It does NOT suffice
for the BY-CONSTRUCTION label on that branch: mypy is satisfied by any member, so the
UNKNOWN path is fail-loud-at-runtime, and RC-acceptance OQ-2 requires that degradation
be disclosed. Disclose or upgrade via a servable-subset type — noting the subset type's
own drift cost. (Condition C6.) The living coercion boundary (G12: URL `str`,
`matching.py` bare `"business"`) is correctly closed by [H4]-at-adapters; verified
chain: unknown string → UNKNOWN member → constructor raises → adapter refuses.

## 5. Conditions

**MUST-FIX-PHASE-3** (before seams freeze at PT-01 / packets go to operator):

- **C1 [AV-1, RC-B]** Seam 3: pin freshness provenance for incremental rebuilds.
  Either per-section live-fetch provenance with artifact `built_from_live_at` = MIN
  over constituent sections' last live-fetch instants, or forbid content-reuse and
  answer RK1's budget attack with numbers. As drawn, `built_from_live_at=fetch_instant`
  on an incremental rebuild stamps unre-fetched content live-fresh (D8 resurrected).
- **C2 [AV-2, RC-B/RC-C-serve]** Seam 4: freeze check-binding points — age arm on
  EVERY logical read; digest arm at bytes-ingress from store; FORBID caching of
  `ServedNumber`/`Provable` results above the gate (only proof-validated bytes tier).
  Align TDD §3 RC-B "re-hashes the served bytes" wording with [H1].
- **C3 [RC-A/RC-E]** Seam 2: `swap_pointer` is a true CAS (S3 conditional write,
  `If-Match` ETag) — not read-check-PUT; version-ID allocation is collision-free
  (UUID / timestamp / digest-addressed). Amend [H6]/[H7].
- **C4 [F1/F3]** DP-2 packet: correct the false S3-atomicity premise against Option A;
  add Option A-prime (proof-in-object-metadata) and Option C-prime (S3-native
  versioning) to the slate; present the TRUE C-vs-A ledger (rollback + atomic
  proof/version co-publication + parity version-pinning vs simplicity); carry this
  register's F1/F3 dissent verbatim.
- **C5 [F5]** DP-3 packet: enumerate Option F5-5 (mandated typed client SDK,
  constitution-homed per P11); present STALE status-class two-sided (5xx-class vs
  424/409 + dedicated refusal-count SLI) with the retry/SLO/attribution ledger and the
  both-sides sequencing constraint (+ `Retry-After`); freeze refusal bodies carry NO
  data-shaped fields; record an EXPLICIT SUPERSEDED disposition on
  ADR-serve-stale-within-bound (2026-06-03); carry this register's F5 dissent verbatim.
- **C6 [AV-cross-check-d, RC-C]** Either add a servable-subset key type (making
  UNKNOWN-in-ArtifactId a static type error) or disclose the UNKNOWN branch as
  FAIL-LOUD-at-construction per RC-acceptance OQ-2. No silent BY-CONSTRUCTION claim on
  a runtime-guarded branch.
- **C7 [AV-6, RC-F]** Seam 5: two-sided expected-set derivation — registry (catches
  missing) AND store enumeration (catches unregistered-but-served); either-side
  mismatch is a firing condition. Extends [H20].

**CARRY-TO-BUILD:**

- **C8 [AV-3, F2/RC-B]** SLA governance: declare where `sla_seconds` per (project,
  entity) lives, who may change it, and surface the values + the "provably ≤ SLA-old"
  semantic delta to the operator no later than the cutover gate (a door packet line is
  cheaper). Quantify the F2-3 rot-trigger threshold at S8.
- **C9 [F4/RC-E]** Gate the swap capability on a `ValidationReceipt` minted only by
  `AcceptancePredicates` (construction-enforces validate-before-swap), or lock the
  ordering with a discriminating test if the capability change is declined.
- **C10 [AV-7, RC-F]** Cutover-gate evidence includes ONE observed end-to-end fired
  alarm (synthetic unprovability → operator-visible notification) — closes the
  alarm-action void; SNS-gap precedent on record in this fleet.
- **C11 [RC-D]** One doctrine line: SUNSET_AFTER extensions require an operator-visible
  ruling (keeps the forcing function honest against serial date-bumps).

## 6. Falsification of this report

This verdict and its findings are falsifiable; concrete observations that would revise
them:

- **AV-1 dissolves** if the architect shows "reuse content-verified sections" means
  per-section verification against LIVE content bytes at rebuild time (in which case
  the fetch IS content-bearing per section and `fetch_instant` is honest — but then
  the RK1 API-budget savings claim must be re-derived, since content verification
  costs the fetch). Either the finding stands or RK1's mitigation weakens; both cannot
  hold as drawn.
- **The DP-2 dissent's S3 claim inverts** if an authoritative AWS citation or an
  integration probe demonstrates that a reader can observe a torn/partial object
  during overwrite of a non-versioned S3 object, or that a failed multipart upload
  corrupts the prior object. My claim is DOMAIN-PRIOR (no live probe run;
  prod_touch NONE); it is a present-tense probeable fact and S2 should receipt it
  (SVR bash-probe/docs-cite) before the DP-2 packet ships.
- **AV-2 downgrades to advisory** if the drawn seam already forbids result-caching
  above the gate somewhere I did not find — cite the line.
- **AV-6 downgrades** if the warm-target registry is shown to be derived FROM the same
  declaration that creates artifacts (single source, drift impossible by
  construction) — cite the mechanism.
- **The C5 status-class contest resolves for 5xx** if evidence shows the receiver SLI
  is the operator's ONLY consumed health surface (making RC-F-based visibility
  arguments moot in practice) — an operator statement suffices.
- **The verdict escalates to BLOCK** if Phase-3 freezes Seam 3 without C1 or ships
  either door packet without C4/C5's corrections — those would embed a false-fresh
  class in a frozen contract and a false premise in a one-way-door ratification,
  respectively.

Self-assessment ceiling: MODERATE (self-ref rule). STRONG on any finding here requires
the architect's Phase-3 disposition + a second rite-disjoint reading (eunomia at S12).

---

*arch-adversary (arch rite, borrowed seat), 2026-07-29. Read in full: TDD, fork
register, RC predicates, feasibility, charter, DEFECT. prod_touch NONE. Verdict:
PASS-WITH-CONDITIONS — 7 MUST-FIX-PHASE-3, 4 CARRY-TO-BUILD. No fork choice reversed.*
