---
type: spec
status: draft
name: integration-boundary-fidelity
throughline_status: CANDIDATE
origin: "2026-06-10 triple-defect saga (autom8y-asana null_number_recovery / DataFrame hot-store heal path): #119 hot-store-only stub-green → #120 prefix-pollution (ASANA_CACHE_S3_PREFIX overload) + cache-envelope mismatch → #121 AccessDenied → IAM grant (live alpha-pattern + autom8y#481 codified). Node fired 2026-06-10 13:07Z: coherent 0→561, gun 571→10, unit.mrr 723/3021. Independently re-derived bit-exact by eunomia E1."
custodian_of_record: "eunomia governance rite (autom8y-asana residency at mint); fleet-index candidate per @throughlines:index conventions"
custodian_primary: [eunomia]
custodian_meta: Pythia
evidence_grade: "[MODERATE, self-ref-capped]"
evidence_annotation: "N_applied=1 (this repo, null_number_recovery hot-store heal path). Self-ref cap per self-ref-evidence-grade-rule: the discipline is minted by the same governance rite that observed the saga. Promotion to MODERATE-external gated on N>=2 (a SECOND satellite applying the four-layer discipline). See §N-Applied + §Promotion. CORROBORATION (non-promoting): StorageNamespaceContract #123 (autom8y-asana main 2f0e7dc0, 2026-06-10) demonstrates four-layer generalization at CONFIG altitude within this same satellite; custodian ruling O-2 (2026-06-11) holds this as same-satellite corroborating evidence — gate requires DISTINCT satellite; SNC does not clear the N>=2 threshold. N>=2 gate preserved intact; awaiting a genuinely distinct satellite."
n_applied: "1 (+1 same-satellite corroboration, non-promoting)"
n_prevented_incidents: 0
siblings: [premise-integrity, premise-validation-discipline, structural-verification-receipt, telos-integrity, authoritative-source-integrity]
user-invocable: false
---

> **Frontmatter note**: `type: spec` + `status: draft` satisfy the `.ledge/`
> shelf lifecycle convention. The throughline-registry lifecycle is carried
> separately in `throughline_status: CANDIDATE` (the @throughlines:index schema
> value), since the ledge `status` enum (accepted/proposed/superseded/rejected/
> stale/deprecated/draft) has no `CANDIDATE` member. `draft` is the honest
> ledge-shelf state: this is a candidate registration awaiting N>=2 + Pythia
> ruling before active-table promotion.

# Throughline (candidate): integration-boundary-fidelity

> Registration spec authored per @throughlines:index Extension Protocol
> (`.claude/commands/throughlines/index.md:67-75`): required frontmatter
> (name, origin, throughline_status, evidence_grade, n_applied) + required body
> sections (Statement · Why · Application Classes · Canonical Protocol ·
> N-Applied Evidence · Promotion Gate · Siblings · Pythia Custodianship). Shape
> mirrors `discipline-propagation-integrity.md`. This is a CANDIDATE
> registration at N=1; it does NOT add a row to the INDEX.md table until N>=2
> lands (per index.md:62 "N_applied >= 3 across at least two distinct
> incidents" — this candidate is pre-threshold and registers as a fleet-index
> *candidate*, not an active throughline).

## §1 Statement (the discipline)

**Tests guarding a production integration boundary MUST stub ONLY the lowest
client boundary (raw transport), use REAL object shapes at REAL keys with
exact-key assertions, include at least one live read-only smoke through the
unit's own code path, AND verify the EXECUTING principal's permissions (IAM) —
a dev-credential smoke proves nothing about the runtime role.**

A test that stubs *above* the transport boundary (returning a hand-rolled
stand-in object, or pre-populating an in-memory store the production code path
never reaches) is *stub-theater*: it goes green while the integration it
purports to guard is inert in production. Boundary fidelity has four
independently-falsifiable layers; a test suite that omits any one of them
leaves a production defect class undetected. The saga that minted this
discipline shipped TWO stub-green cures inert before the third fired — and even
the third required a fourth fix layer (IAM) that NO test in the suite could
catch.

## §2 The four defect layers (each anchored to this arc's receipts)

The discipline guards four orthogonal failure layers. Each layer is named, each
is anchored to a receipt from the 2026-06-10 saga, and each maps to a
falsifiable test obligation.

### Layer 1 — Population-mechanism fidelity
**Defect**: the test pre-populates the store the production read path never
populates the same way; the cure goes green because the test supplied the data
the runtime cannot.
**Receipt**: #119 "hot-store-only" stub — the v1 cure pre-populated an in-memory
hot store as a stand-in; production never reached that population path, so the
cure deployed inert.
**Test obligation**: data under test must arrive via the SAME population
mechanism production uses (real serialize → real key → real backend put), not
via a test-only injection seam.

### Layer 2 — Key-construction + config-pollution fidelity
**Defect**: the test writes/reads at a key the production code does not
construct, OR a shared config knob is overloaded so the effective key diverges
between test and runtime.
**Receipt**: #120 prefix-pollution — `ASANA_CACHE_S3_PREFIX` was overloaded such
that the effective S3 key the producer wrote and the consumer read diverged;
the v2 `CacheEntry`-stub backend hid the divergence behind a stand-in.
**Test obligation**: exact-key assertions. The test must assert the literal key
string the production code constructs (no glob, no "matched-N", no prefix-
agnostic stand-in). E3a mutation proof: a prefix mutation produces **5 RED** —
the suite mechanically catches key divergence post-#121.

### Layer 3 — Deserialization-shape fidelity
**Defect**: the test deserializes a hand-rolled envelope shape; the real backend
returns a different envelope (extra wrapping, versioned header, different field
nesting); the unwrap path is never exercised.
**Receipt**: #120 cache-envelope mismatch — the stand-in `CacheEntry` returned a
shape the real deserialize/unwrap path did not produce; the envelope mismatch
hid behind the stub until #121 used the real shape.
**Test obligation**: real object shapes at the boundary. E3a mutation proof: an
unwrap mutation produces **exactly 1 RED** (the designed guard) — the suite
catches deserialization-shape drift with a single targeted assertion.

### Layer 4 — Runtime-principal-permission fidelity
**Defect**: the test runs under dev credentials (or no credential boundary at
all); the runtime executes under a different IAM role that lacks the grant; the
suite is structurally incapable of catching the AccessDenied.
**Receipt**: #121 AccessDenied → IAM grant (live alpha-pattern applied; codified
at autom8y#481). NO test in the suite caught this; it required a fourth fix
layer outside the test boundary entirely.
**Test obligation**: the live read-only smoke must execute (or assert against)
the EXECUTING principal's permissions, not a dev-cred proxy. This layer is
*partially* un-unit-testable by construction — its forcing function is the live
smoke + an IAM-policy assertion, NOT a mock. This is precisely why Layer-4 is
the discipline's hardest and most load-bearing clause: a green unit suite is
not evidence of Layer-4 health.

## §3 Application Classes

This discipline applies any time a unit/integration test guards a production
integration boundary where data crosses a serialization + transport + principal
seam. Canonical surfaces:

1. **Object-store-backed cache reads** (the mint instance): S3/Redis-backed
   DataFrame or entry cache where producer and consumer cross a key + envelope +
   IAM seam.
2. **Cross-service HTTP/RPC reads** where the client library is stubbed: stub
   ONLY the transport (e.g. the `httpx`/`boto3` client), never the response
   model the unit deserializes.
3. **Queue/stream consumers** deserializing a wire envelope: assert the real
   envelope shape and the real partition/topic key.
4. **Any read path whose runtime principal differs from the test principal**:
   Lambda execution role, ECS task role, CI OIDC role — the dev-cred smoke is
   Layer-4-blind by construction.

**Non-application**: pure-function unit tests with no transport/serialization/
principal seam (e.g. a phone-number normalizer). These have no integration
boundary to be faithful to; the discipline does not apply and forcing a live
smoke onto them is ceremony.

## §4 Canonical Protocol (the four-step boundary-fidelity check)

Any test author guarding a production integration boundary MUST satisfy all four
before declaring the guard complete:

1. **Stub only the lowest client boundary.** Replace the raw transport client
   (`boto3` S3 client, `httpx` client) with a boundary-level stub/stubber.
   Do NOT replace the store, the entry object, or the deserialize path with a
   stand-in. (Refutes Layer-1 + Layer-3.)
2. **Use real object shapes at real keys.** Construct the production object type
   (e.g. `DataFrameCacheEntry`) with its real freshness/schema-version fields;
   write/read at the literal key the production code constructs. (Refutes
   Layer-2 + Layer-3.)
3. **Exact-key assertions.** Assert the literal key string and the literal
   unwrapped values — no globs, no count-only, no shape-agnostic stand-in.
   (Refutes Layer-2. E3a: prefix-mutation → 5 RED.)
4. **At least one live read-only smoke through the unit's own code path, plus a
   runtime-principal-permission assertion.** The smoke calls the unit's real
   read function (not a re-implementation) against a real backend, read-only,
   and asserts the executing principal can read. (Refutes Layer-4. The dev-cred
   smoke is insufficient — assert the runtime role's grant.)

If any of the four cannot be satisfied at unit altitude (Layer-4 typically
cannot), the unsatisfiable layer's forcing function MUST be a live smoke with a
scheduled run / deploy-gate / pre-land hook (see §6 PERMANENT-SKIP-RISK).

## §5 N-Applied Evidence

### N=1 — autom8y-asana null_number_recovery hot-store heal path (2026-06-10)

- **Arc**: triple-defect saga #119 → #120 → #121 → IAM grant.
- **Node receipt**: fired 2026-06-10 13:07Z — coherent 0→561, gun 571→10,
  unit.mrr 723/3021. Independently re-derived bit-exact by eunomia E1.
- **Layer coverage achieved at #121**:
  - Layer-1 (population): real serialize→key→backend path exercised.
  - Layer-2 (key/config): exact-key assertions; E3a prefix-mutation → 5 RED.
  - Layer-3 (envelope): real `DataFrameCacheEntry` shape; E3a unwrap-mutation
    → exactly 1 RED (designed guard).
  - Layer-4 (principal): IAM grant applied live + codified autom8y#481; NO unit
    test caught it — Layer-4 is the un-unit-testable clause, guarded only by the
    live smoke + IAM-policy codification.
- **Boundary-fidelity test substrate** (verified file:line, this repo):
  - `src/autom8_asana/cache/integration/dataframe_cache.py:68` —
    `class DataFrameCacheEntry` is the REAL entry shape (project_gid,
    entity_type, dataframe, watermark, created_at, schema_version, row_count,
    build_quality + `is_stale` / `is_fresh_by_watermark`). This is the shape
    Layer-3 fidelity requires tests to use, NOT a stand-in.
  - `src/autom8_asana/cache/dataframe/factory.py:261` —
    `get_dataframe_cache_provider()` is the production provider seam consumers
    patch; the boundary-level stub must sit below this, not replace it.
- **Self-ref grade**: MODERATE per `self-ref-evidence-grade-rule`. eunomia
  observing an autom8y-asana saga and minting the discipline within the same
  governance arc is self-referential authorship; cap holds at MODERATE.

[UV-P: the dedicated live read-only smoke file (E3a-cited: hardcoded gid
1207519540893045 / MRR=1500, zero references outside the file, hot-store read
through the unit's own code path) exists at a path in the fpc-phase2 worktree
not pinnable from the main tree at this altitude | METHOD: bash-probe |
REASON: E3a inspected it directly and supplied the receipt; the executor's
CHANGE-001 first step (PLAN §CHANGE-001 step 0) re-pins the exact path via
`grep -rln 1207519540893045` before authoring the forcing function. Re-derivation
deferred to execution-time probe rather than manufactured here.]

### N=1+corr — StorageNamespaceContract #123 (autom8y-asana, CONFIG altitude, 2026-06-10) — SAME-SATELLITE CORROBORATION, NON-PROMOTING

- **Custodian ruling**: O-2 (2026-06-11). This instance does NOT satisfy the
  N>=2 gate. Gate requires "a SECOND satellite repo" / "DISTINCT satellite."
  SNC is the same satellite (autom8y-asana), same governance session, and shares
  triple-defect saga parentage with N=1. Real generalization evidence recorded
  here; non-promoting because it cannot provide the satellite-disjointness the
  gate requires.
- **Arc**: StorageNamespaceContract — config-topology defect class. #123 merged
  to autom8y-asana main at commit 2f0e7dc0 (2026-06-10); deployed to ECS
  :506+warmer.
- **Altitude**: CONFIG (not test-guard). The four-layer discipline generalized
  beyond test altitude to config-topology enforcement.
- **Four-layer mapping at CONFIG altitude** (per arch HANDOFF §N=2):
  - L1 (population-mechanism): registry declares writer-owner; population path
    for namespace keys is owned at the registry declaration site (t1 mechanism).
  - L2 (key/config-pollution): t3 no-literal-outside-registry — the #120
    mechanism (ASANA_CACHE_S3_PREFIX overload) killed; config literals outside
    the registry are the L2 analogue at config altitude.
  - L3 (envelope): t2 IAM-grant ↔ namespace mapping — the config envelope that
    binds a namespace declaration to its IAM grant; shape fidelity at config
    altitude requires the grant-to-namespace mapping be explicit and registry-
    owned, not constructed ad-hoc.
  - L4 (runtime-principal): Phase-β derives IAM from the registry — the runtime
    principal's permissions flow from the registry declaration; ad-hoc out-of-band
    IAM grants (as occurred in the L4 N=1 arc) are prevented by the registry
    ownership constraint.
- **Receipts**: PR #123 → autom8y-asana main 2f0e7dc0. Phases β-1/#490 and
  β-2/#491 plan-validated PRs held at the prod gate (operator). PV-DRIFT RESOLVED
  (ECS task-s3 policy TF-NEVER-OWNED, out-of-band). β-3 spec staged for rollback.
- **Why non-promoting**: The gate text is unambiguous — "DISTINCT satellite."
  The anti-self-confirmation intent of the gate is to prevent the same session
  from supplying both the discipline and its second node. SNC: same satellite,
  same session, shared saga origin. The config-altitude generalization is genuine
  and is recorded here as corroborating evidence. It does not clear the gate.
  N>=2 gate intact; awaits a genuinely distinct satellite as the next anchor.

## §6 PERMANENT-SKIP-RISK clause (forcing-function obligation)

**Every live-smoke this discipline mandates MUST carry a forcing function: a
pre-land checklist hook, a scheduled CI run, OR a deploy-gate step.** A live
smoke with no forcing function is a permanently-skipped test that confers false
confidence — structurally identical to the stub-theater this discipline exists
to eliminate, just one altitude up.

**Named gap (FIRST remediation, this repo)**: the E3a census records the current
live smoke as skip-gated correctly in CI BUT with **no forcing function** — zero
references outside the file, a hardcoded gid (1207519540893045) and MRR (1500)
whose staleness the smoke cannot self-verify, and no scheduled run / deploy-gate
/ pre-land hook compelling it to execute. It can silently skip forever. This is
the discipline's own Layer-4 forcing function being absent on the very arc that
minted it.

**Remediation**: PLAN-eunomia-stub-theater-remediation-2026-06-10.md CHANGE-001
specs the forcing function (recommended: scheduled nightly CI job with AWS OIDC
running ONLY the live-smoke file; alternatives + tradeoffs enumerated there).
Until CHANGE-001 lands, Layer-4 of this discipline is UNGUARDED on its own mint
instance — the candidate registration explicitly carries this debt.

## §7 Promotion Gate

Per CANDIDATE status and @throughlines:index conventions
(`.claude/commands/throughlines/index.md:60-66`):

- **N>=2 (MODERATE-external)**: a SECOND satellite repo applies the four-layer
  discipline to a production integration boundary (object-store cache, HTTP
  read, queue consumer) where the boundary-fidelity check catches OR would have
  caught a stub-theater defect. The second anchor MUST be a DISTINCT incident at
  a DISTINCT satellite — not a second surface of the null_number_recovery arc.
- **N>=3 (INDEX row)**: third distinct incident; only then does this candidate
  earn a row in the INDEX.md Active Throughlines table per index.md:62
  ("N_applied >= 3 across at least two distinct incidents").
- **STRONG**: at least one anchor must be rite-disjoint AND must demonstrate the
  forcing function (§6) *preventing* a stub-green cure from deploying inert —
  not merely detecting it post-hoc. (Mirrors discipline-propagation-integrity's
  "channel prevents the gap, not merely detects it" STRONG bar,
  `discipline-propagation-integrity.md:105-109`.)

Until N>=2: `[MODERATE, self-ref-capped]` holds; this file is a fleet-index
*candidate*, not an active-table entry.

## §8 Siblings

- **premise-integrity** — validates architectural premises against production
  before design freeze; integration-boundary-fidelity validates *test fidelity*
  against the production boundary at test-authoring time. Premise covers the
  assumption; boundary-fidelity covers the guard.
- **premise-validation-discipline** — production-database schema premises
  (DuckDB ATTACH / query sequence). Boundary-fidelity is the broader transport+
  envelope+principal sibling; PVD remains canonical for DB schema premises.
- **structural-verification-receipt** — claim-truth-at-assertion-time for
  platform-behavior claims in planning artifacts. Boundary-fidelity is the
  test-altitude analogue: object-truth-at-test-time for integration boundaries.
  This spec dogfoods SVR (see §5 UV-P + the verified file:line anchors).
- **telos-integrity** — verifies user-visible outcome realized. The Layer-4
  live smoke is a telos-grade forcing function: it asserts the integration is
  *realized in production*, not merely *coded*.
- **authoritative-source-integrity** — file:line receipt grammar; this spec's
  N=1 evidence anchors trace to verified file:line.

See: [discipline-propagation-integrity.md](../../.claude/commands/throughlines/index/discipline-propagation-integrity.md) · [index.md](../../.claude/commands/throughlines/index.md)

## §9 Pythia Custodianship (deferred)

No Pythia ruling has yet ratified this candidate. Per index.md:63 a verbatim
Pythia promotion ruling is required before active-table registration. At N=1
self-ref-capped, this spec stands as a CANDIDATE registration awaiting (a) the
N>=2 second-satellite anchor and (b) a Pythia ruling. Custodianship of record:
eunomia governance rite.

---

*Authored 2026-06-10 by eunomia consolidation-planner (station E5), PLAN-ONLY.
No tests/src modified; no commits. Evidence grade MODERATE per
self-ref-evidence-grade-rule. N=1; fleet-index candidate, not active-table
entry.*

*Custodian ruling applied 2026-06-11 by eunomia entropy-assessor (station E2):
N=2 promotion claim (StorageNamespaceContract #123) evaluated as O-2 (HOLD).
SNC recorded as same-satellite corroboration in §5; frontmatter n_applied and
evidence_annotation updated. §7 gate text unchanged. No other edits.*
