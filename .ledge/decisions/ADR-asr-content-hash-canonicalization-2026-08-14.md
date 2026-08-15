---
type: decision
status: proposed
---

# ADR — ASR content-hash canonicalization: one service-internal function, mirrored not shared

| | |
|---|---|
| **Status** | PROPOSED (owner-of-record ratification pending — §5) |
| **Date** | 2026-08-14 |
| **Wave** | `coc-arm-the-instrument`, PHASE A-1 — REC-002 conjunct (b) |
| **Companion** | `DESIGN-rec002-asr-content-hash-2026-08-14.md` (the build design) |
| **Evidence cap** | **MODERATE** — self-referential authorship per `self-ref-evidence-grade-rule` |

---

## 1. Context

Arming the swap detector (REC-002(b)) requires the autom8y ASR service
(`services/account-status-recon`) to stamp a `content_hash` on both halves of a joined
occurrence: the `report_generated` provenance event and the `report_posted` delivery event.

The instrument that consumes those hashes lives in a **different repository**
(`autom8y-asana`), which already holds THE canonical hash function —
`canonical_payload_hash(blocks, text)` at
`src/autom8_asana/observability/payload_hash.py:38`. That function exists because of REC-001:
two *independent* canonicalizations of the same payload produced different digests, and a
swap-check spanning them could never fire — the RED capture recorded *"two canonicalizations
agree? False"* (`payload_hash.py:3-13`).

ASR has no canonicalization of any kind today: `git grep -c content_hash` across
`services/account-status-recon/**` at autom8y `origin/main` 5f554d60 returns **zero hits**.
So the question is not *which* canonicalization ASR should adopt, but *how ASR should come to
have one* without recreating REC-001's founding wound.

---

## 2. Decision

**Option (iv): ONE ASR-internal canonicalization function, used by BOTH the
`report_generated` and `report_posted` emissions.**

A new module `services/account-status-recon/src/account_status_recon/payload_hash.py` exposes
`canonical_payload_hash(blocks, text)` that **semantically mirrors**
`autom8_asana/observability/payload_hash.py:38-55`: identical key set `{blocks, text}`,
identical `sort_keys=True`, identical `separators=(",", ":")`, identical `list(blocks)`
normalisation, identical `"sha256:" + hexdigest` output form. Same module name, same symbol
name, same signature — deliberately, so the migration in §4 is a mechanical import swap.

**REC-001 is satisfied.** The invariant is *no second **independent** canonicalization of the
same logical payload **within a comparison pair***. Both ASR hash points call the **one** ASR
function; the pair the join compares is internally consistent by construction. Two invocations
of one function are not two canonicalizations.

**What this decision explicitly does NOT claim: cross-repo byte-parity.** The ASR function and
the autom8y-asana function are never compared against each other by any test, in either
repository. They are *designed* to agree and are *not verified* to agree. Nothing in the
current system requires them to — the join only ever compares an ASR hash to an ASR hash. The
moment that stops being true is the trip-wire in §4.

---

## 3. Alternatives considered and rejected

### (i) Dependency edge — ASR imports `autom8_asana.observability.payload_hash` · REJECTED

- **Pro**: literally one function; byte-parity is guaranteed rather than hoped for.
- **Con — dependency inversion.** ASR is a platform reconciliation service; `autom8y-asana` is
  a *consumer-side* satellite that observes ASR's output. This edge would make the observed
  service depend on its observer, pointing the dependency graph the wrong way. Under the
  Dependency Rule, source dependencies must point inward toward higher-level policy
  [DP:SRC-003 Martin 2017] [MODERATE | 0.70]; a direction violation is structural and is not
  redeemed by testing or convenience [DP:SRC-002 Martin 2003] [MODERATE | 0.70].
- **Con — deployment coupling.** ASR is a Lambda container built from the autom8y monorepo. A
  cross-repo package edge would put the observer in the observed service's deploy path and
  release cadence.

### (ii) Vendoring that *presents itself* as parity · REJECTED

- **Pro**: no dependency edge; the code is right there.
- **Con — the confidently-wrong shape.** Copying the bytes and then *asserting* cross-repo
  parity claims a guarantee nothing tests. A later edit to either copy would silently break the
  claimed invariant while the paper still asserted it. This is refused on the charter's hard
  floor: **NEVER CONFIDENTLY WRONG**
  (`CHARTER-decision-space-of-record-2026-07-30.md:52`, Operative Core §2).
- **Distinction from the adopted option.** (iv) *is* a mirror, and the difference is entirely
  in what is claimed: (iv) states in the module docstring and here that parity is **untested and
  unclaimed**, and books it as a named gap (§4, and the companion design's E4 register).
  Option (ii) is the same code with a false guarantee attached. The code is not the decision —
  the claim is.

### (iii) Shared platform package (e.g. an `autom8y-observability` SDK) · DEFERRED, not rejected

- **This is the correct end-state.** It is the only option that makes cross-repo byte-parity a
  *mechanical* property rather than a coordinated intention.
- **Why not now**: premature. Nothing in the current system compares an ASR hash to an
  autom8y-asana hash, so a shared package would today buy zero verified invariants while adding
  a new SDK, its versioning, its release cadence, and a cross-repo upgrade lockstep to a wave
  whose entire charge is *additive observability*. Building the coupling before the coupling is
  load-bearing would be gold-plating against the charter's delivery floor
  (`CHARTER-…-2026-07-30.md:53`, Operative Core §3: ship the honest version, write down the
  known gaps).
- **It is deferred with a firing condition, not shelved.** See §4.

---

## 4. Migration trip-wire — (iv) → (iii)

> **TRIGGER: the first EX-5-rendered payload entering ASR's egress. That event is REC-004.**

Today the two functions hash *different products*: ASR hashes its account-findings payload
(`ReconciliationReportBuilder`); autom8y-asana's `render()` hashes the item-1a offer readout and
has **zero production callers**. Their digests are never compared, so divergence is inert.

REC-002 conjunct **(a)** — wiring `render()` into ASR's egress — is operator-reserved and is
**not** performed in this wave. When it *is* performed, a payload generated by autom8y-asana
code will be delivered through ASR's egress, and a hash stamped in one repository will be
compared against a hash stamped in the other. At that instant:

- byte-parity between the two canonicalizations becomes **load-bearing**;
- any divergence — a key-order change, a separator change, a `list()` normalisation change, a
  digest-prefix change — reproduces REC-001's founding wound **across a repository boundary**,
  where it is far harder to see;
- **option (iv) becomes insufficient by construction**, and the migration to (iii) is required
  before that path carries traffic.

**Trip-wire discharge conditions (all three):**

1. The shared platform package exists and exports the single `canonical_payload_hash`.
2. **Both** repositories import it; **neither** retains a local definition.
3. A test asserts byte-identical digests across both call sites for a shared fixture — the
   assertion that (iv) deliberately cannot make.

**Watch mechanics.** The trip-wire is carried as `E4-b` in the companion design's residuals
register (§10) and is named in the ASR module docstring, so a reader arriving at the mirrored
function from either side finds the firing condition without reading this ADR.

---

## 5. Owner-of-record

| Role | Assignment | Standing |
|---|---|---|
| **Trip-wire owner-of-record** | the **autom8y-asana 10x-dev rite, architect seat** — as instrument owner | **PROPOSED — operator ratification pending** |
| Build owner (this wave) | principal-engineer, path `services/account-status-recon/**` | assigned |

**Rationale for the seat.** The trip-wire fires on an *instrument-side* event (an EX-5-rendered
payload entering ASR egress), and the migration target is a *cross-repo architecture* decision.
Both sit with the seat that owns the instrument, not with the ASR service owner who would merely
consume the shared package.

**Honest limitation, stated rather than papered.** An agent seat cannot appoint a durable human
owner-of-record, and this wave's charge does not include doing so. The assignment above is a
**proposal**. The open question the operator must answer:

> *Is the autom8y-asana 10x-dev architect seat the durable owner-of-record for the (iv)→(iii)
> trip-wire, or does this belong to a named human/seat outside the rite — and who watches the
> trigger between now and REC-004?*

Until that is answered, the trip-wire is **recorded and unwatched**: it will be visible to
anyone who reads the ADR, the design's residuals register, or the ASR module docstring, but no
one is on the hook to notice the trigger firing. This is the same unowned-flag class already
open on this wave's telos and is surfaced here rather than absorbed
(`CHARTER-…-2026-07-30.md:57`, Operative Core §7).

---

## 6. Consequences

**Positive**

- ASR gains a hash with **no** new cross-repo dependency and **no** new deploy coupling.
- REC-001's invariant holds within every comparison pair the join actually evaluates.
- Mirroring module name, symbol name, and signature makes the §4 migration a mechanical import
  swap rather than a redesign.
- The change is fully reversible and touches no customer-visible surface, keeping it inside the
  charter's autonomous band.

**Negative**

- **Two definitions of one canonical form now exist in the fleet**, and nothing mechanically
  prevents them from drifting. This is a real cost, accepted knowingly, bounded by §4, and
  recorded as gap `E4-b`.
- The trip-wire depends on a human noticing REC-004 begin — see the §5 limitation.

**Neutral**

- No behavioural change to any delivered payload. The bytes handed to Slack are byte-identical
  to today (companion design §3.2).
- If the shared package (iii) is built earlier for unrelated reasons, this ADR is superseded
  early and harmlessly: the ASR module is deleted and its import re-pointed.

---

## 7. Structural-verification receipts

```yaml
claim: "the canonical form this ADR instructs ASR to mirror binds blocks and fallback text together in one sorted, whitespace-free JSON document under a sha256 prefix"
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/observability/payload_hash.py"
  line_range: "L50-L55"
  marker_token: "canonical = json.dumps( {\"blocks\": list(blocks), \"text\": text}, sort_keys=True, separators=(\",\", \":\"), )"
  claim: "the mirrored ASR function must reproduce this exact document shape and separator choice, since any deviation would be invisible today and would become a cross-repo digest split at REC-004"
```

```yaml
claim: "ASR holds no canonicalization of any kind at the substrate of record, so this ADR introduces a first definition rather than reconciling competing ones"
verification_method: bash-probe
verification_anchor:
  source: "git -C /Users/tomtenuta/Code/a8/a8/repos/autom8y grep -c content_hash origin/main -- 'services/account-status-recon/**'"
  command_output_verbatim: "ZERO HITS — confirmed"
  exit_code: 1
  claim: "the absence is total across the service tree, so no pre-existing ASR digest scheme constrains the mirrored form and no migration of existing hashes is required"
```

> `[UV-P: the two canonicalizations produce byte-identical digests for the same {blocks, text} input | METHOD: deferred-to-REC-004 | REASON: option (iv) deliberately does not test cross-repo parity, and nothing in the current system compares an ASR digest to an autom8y-asana digest — §4 is the discharge site and the migration to option (iii) is the discharge mechanism]`

> `[UV-P: the autom8y-asana 10x-dev architect seat is the durable owner-of-record for the (iv)→(iii) trip-wire | METHOD: deferred-to-operator-ruling | REASON: an agent seat cannot appoint a durable owner; §5 states the assignment as a proposal and names the exact question the operator must answer]`
