---
type: handoff
artifact_type: HANDOFF
from_rite: 10x-dev (wave-2 dark build)
to: S8 cutover-gate session (10x-dev /qa ultracode) → then eunomia S12 attestation
initiative: substrate-v2-epoch
wave: WAVE-2 (dark build) → CLOSED; next = S8 (the P5 gate, LEG-1)
date: 2026-07-29
status: draft
close_state: "WAVE-2 CLOSED — substrate-v2 built DARK beside v1; all 6 modules + harness on main; S9 doctrine authored+adversary-cleared (landing held to S8-green). NEXT = S8 cutover gate."
session: session-20260729-115854-33485f6a
sprint: sprint-20260729-substrate-v2-wave2
main_sha: 7d963902
charter: .ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md
telos: .know/telos/substrate-v2-epoch.md
predecessor_handoff: .ledge/handoffs/HANDOFF-s1-substrate-v2-design-2026-07-28.md
staged_wave2_specs: .ledge/handoffs/STAGED-wave2-dispatch-specs-2026-07-29.md
---

# HANDOFF — Substrate-v2 Epoch · WAVE-2 (dark build) CLOSED → S8 cutover gate

The next session ignites **S8 (the P5 cutover gate)** from this document. Wave-2 built
substrate-v2 whole and dark beside v1; S8 is the single validation event (adversarial
fixture replay + bounded live-parity window) that carries the live leg.

## 1. Mission + Realization Predicate (operator verbatim — the exit-anchor)

**MISSION:** "every business number the asana dataframe substrate serves is provably
current or loudly refused — delivered by a substrate-v2 designed whole and small enough
that its correctness is legible, with v1 deleted and the doctrine packaged so any
autom8y-* repo can reconstruct the same guarantees as a template application, not a
research project."

**PREDICATE (NOT "PRs merged"):** "Verified-realized" = P5 cutover-gate receipts clean
(adversarial fixture replay + bounded live-parity window, every divergence explained)
AND a rite-disjoint attester re-derives active_mrr by their own hands matching live Asana
within freshness-SLA across >=2 warm cycles AND v1 planes/bridges/flags enumerate to zero
AND doctrine landed at fleet-constitution level.

**LEG status:** LEG-0 (legible whole-design) DONE at PT-01. **Dark-build substrate LANDED
(this wave).** LEG-1 (P5 gate) = S8, NEXT. LEG-2 (attester re-derives across >=2 warm
cycles) = post-cutover PT-04 → S12. LEG-3 (v1 → zero) = S11. LEG-4 (doctrine at
constitution) = S9 landing + S10 kit.

## 2. What landed on main (7d963902) — the dark build

| Sprint | RC | PR | Adversarial verdict trail |
|--------|----|----|---------------------------|
| SEAM-0 | contract pkg | #280 | fidelity ALL-MATCH; +SEAM-0b finding → architect ruled O2+O-b (no amendment; empty Protocols are build-drawn placeholders) |
| S2 freshness | RC-B | #281 | qa NO-GO (F1 missing-column silent-digest; F2/F3 decimal-context) → GO; byte-identity preserved, no scheme bump |
| S3 storage/keys | RC-A/C | #284 | qa CONDITIONAL-GO (F2 blank-if_match clobber; F3 gid-traversal; F4 pagination; N1 graft) → GO |
| S4 rebuild | RC-E | #285 | qa NO-GO (**F1 proof-provenance WOUND**) → architect **C15 Seam-2 v1.1** (proof-in-pointer) → DELTA GO (P1/P3/P4 closed, no false-serve); capacity GO-WITH-CONDITIONS |
| S5 serving | P2/RC-C | #286 | qa GO (C1 wound LOCKED) + security APPROVE-WITH-ADVISORIES + [H17] tooth-reachability hardening |
| S6 observability | RC-F | #282 | qa NO-GO (**F-1 tf↔emitter dead-metric** — DMS-24h class reborn) → GO + binding test |
| S7 gate-harness | P5 | #283 | qa (dual role) GO — 22/22 predicates, 100% saboteur-trip, $84,385 exemplar #1 |
| S9 doctrine | P11 | #279 | **DRAFT — landing HELD to S8-green**; arch-adversary PASS after 4 MF-fixes |

Every merged sprint: green CI + rite-appropriate adversarial review (qa-adversary per unit;
+capacity on S4; +security on S5; +arch-adversary on S9). Reviews on record at
`.ledge/reviews/{QA,CAPACITY,SEC,ADVERSARY}-s{2..9}-*-2026-07-29.md`.

## 3. Frozen seams (the S8/S11 contract) + build-notes

- **Seam-2 (storage) = v1.1** (F1/C15 amendment): `stage_version(aid, frame_bytes)`
  bytes-only; `swap_pointer(aid, to, proof, *, if_match)` publishes the validated proof;
  `refresh_pointer_proof`/`StaleProofRefused` RETIRED. Seams 1/3/4/5 = v1.0-frozen-2026-07-29.
- **Build-notes (TDD §11):** C12 (S4 forward-only monotonicity) · C13 (RefuseReason closed;
  sunset→STALE + `sunset_breach` payload field) · C14 (byte-stable proof-advance; SUPERSEDED
  by C15) · **C15 (proof-in-pointer-only; graft-coherence at S4 `_publish` + serve-ingress
  re-derivation, NOT the store — DIP)** · C16 (fetch-completeness-by-construction; `min_rows>=1`
  ctor guard, no shrink threshold).
- **Invariant that carries into S8/S11:** every consumer reads the proof FROM the pointer
  (unchanged shape); no false-serve is reachable because C2/[H16] re-derive the digest per-read
  (serve-ingress terminal).

## 4. S8 ENTRY — requirements + the FULL carry stack

### 4a. HARD S8-preconditions (must clear before the live-parity leg arms)
- **[LOUD — 429 scar] AIMD signal-blindness:** the S7 parity source
  `tests/harness/substrate_gate/parity.py::PacedLiveParitySource` (merged #283) **never calls
  `slot.reject()`** — a 429 is invisible to AIMD (window grows, never shrinks), unlike the true
  v1 path (`asana_http.py::_request`). FIX before arming any live fetcher (capacity condition 1).
- **UV-P-1: DISCHARGED 2026-07-29** (operator re-authed AWS post-close; read-only probe). Prod
  warmer image `696318035277.dkr.ecr.us-east-1.amazonaws.com/autom8y/asana:2201db2` = git
  `2201db21` (S5 merge, a descendant of #276 `bdbf86cb`), ECR-pushed 15:19 UTC, Lambda
  `autom8-asana-cache-warmer{,-bulk,-section}` deployed 15:24 UTC — **the prod warmer contains the
  #276 P1 entity-aware prober fix** (and S2/S3/S5/S6/S7 of the dark build). No live parity residual.
- **UV-P-2 baseline: DISCHARGED 2026-07-29** (read-only S3 probe). The v2 offer plane
  `s3://autom8-s3/dataframes/1143843662099250/offer/sections/` received **fresh warm writes today
  at 15:08 / 15:25 / 15:50 UTC** (+ `watermark.json` 15:26 UTC) — **the #276 write-path split is
  CLOSED in prod: the v2 entity plane is no longer frozen; the entity-aware prober writes to it
  live.** This is the S8 parity BASELINE; the full **>=2-warm-cycle LEG-2** is still eunomia's
  own-hands re-derivation at S12 (do NOT treat this as LEG-2 satisfied).
- **Process-singleton `PacedAsanaFetcher`** (not fresh-per-call) before any K>1 concurrent
  rebuild (capacity condition 2). In-flight ceiling = `K × min(S_aid, G, C_aimd)` (G=gather
  width 10, C_aimd=read_limit 12); [H12] single-flight dedupes same-ArtifactId only.

### 4b. S8 build/wire carries
- **Per-day budget counter (net-new):** none exists — `BudgetAllocator`/`RetryBudget` are 60s
  windows, advisory/fail-open; `rebuild()` takes no budget param. Build a cross-invocation-durable
  per-day cap that the rebuild can REFUSE/defer against (capacity condition 3). Real section
  counts for the model = an open UV-P (S2/S4 entry, still open).
- **`FetchTelemetry` receipt** rides `RebuildResult` (requests/429s/retries) — S8's P10-budget
  evidence consumes it (landed in S4 #285).
- **BudgetAllocator.Lane** a rebuild registers under (fair-share pool shared with ECS) — confirm
  (capacity condition 5).
- **D6b rider (S4 DELTA):** an out-of-contract, digest-COHERENT future-dated proof serves at
  negative age (unconstructable through the rebuild flow); S6's `FutureDatedProofCount` fires on
  it — **bind an alarm to that metric** at S8.
- **Serialization determinism** (S4/S5): the writer/reader frame codec (`digest_of_frame` =
  parse + `canonical_digest`) is wired at S8 — the real encoding (parquet/arrow) must round-trip
  deterministically or C3 idempotency is theater. Named S8 obligation.
- **canonical value-digest column set** prod corroboration (S2 [H1]): schema-membership verified
  by direct read of `schemas/offer.py`; prod value-stability confirm rides here (DuckDB MCP).

### 4c. C8 SLA-governance (AV-3 — the highest-residual carry, operator-facing by S8)
`sla_seconds` binds to the entity registry's `default_ttl_seconds`, which is documented as
"Cache TTL" (`entity_registry.py`, dual-role annotation added S2 #281). An ungoverned 14d
value re-serves the wound with a green proof (AV-3). **Surface to the operator NO LATER than the
S8 gate:** the per-entity SLA values + the "provably ≤ SLA-old, not 'current'" semantic delta.

### 4d. S5 security carries (all LOW, S8-cutover)
- **A1:** bound/sanitize `per_section_delta` KEYS (Asana section names → LLM via MCP) before the
  DIVERGENT refusal path is wired live (prompt-injection-shaped; empty on every live path today).
- **A2:** jitter `Retry-After` (synchronized-retry-storm on rebuild schedule).
- **A3:** make the enumeration-safety upstream-auth contingency explicit at cutover; every
  external CP adapter behind the v1 auth context.

### 4e. INFO/tooth carries
- S5 F-5 (FutureDatedProofCount namespace attribution for S8 receipts), F-6 (sunset runtime
  backstop → RC-D), F-7 (`Provable(frame=None)` mypy-guarded; runtime guard = a seam change,
  deliberately not made), F-8 (retry_after clamp).
- S5 F-2 residual: the [H17] privacy tooth catches reachability drift; importlib-string
  dynamic-getattr is a documented KNOWN limitation (targets drift, not sabotage).
- S6: alarm terraform is AUTHORED-NOT-APPLIED (`substrate_v2_provability_alarms.tf`, PROV-1..6) —
  **APPLY = Door #4 / DP-4a (operator)**; C10 (>=1 observed FIRED alarm) is S8 cutover evidence.

## 5. S8 execution plan (the P5 gate)

1. **Fixture replay** (S7 corpus, `tests/harness/substrate_gate/`): 22/22 predicates, two-sided
   teeth, 100% saboteur-trip — run as the gate's deterministic leg.
2. **Bounded live-parity window (DAYS, not weeks):** v2 computes real numbers beside v1 against
   live prod; **every divergence explained before the flip**; rollback = restore v1. Rides the S4
   rebuild primitive (the ONLY P10-safe channel: AIMD/429-banking, per-day budget, off-peak,
   receipts). Encode the **$84,385-vs-$79,585 re-baseline as parity exemplar #1** (already in the
   S7 corpus via the RefusePayload observable).
3. **Rite-disjoint critics (security):** threat-modeler + penetration-tester hunt common-mode
   fixture blindness (shape §2:S8 roster) + capacity-engineer for the live-leg 429-pacing receipts.
4. **PT-03 (HARD):** all divergences explained; two-sided teeth bite; critic sign-off; P10 budget
   receipts. On fail → back to build. On pass → cutover armed (reversible = restore v1).
5. **PT-CUTOVER (reversible flip, P9 autonomous) → PT-04 (>=2 warm cycles, UV-P-2 full) → S11
   extinction** (DP-1 v1-deletion + DP-4b warmer-DMS terraform, operator doors) → **S9 doctrine
   LANDS** (post-S8-green, PR #279) → **S10 kit** (UV-P-3 sibling census) → **S12 eunomia
   attestation** (rite-disjoint; `ari sync --rite=eunomia`; re-derives all 4 predicate legs).

## 6. Infra + SVR/UV-P deltas

- **AWS creds RE-AUTHED by operator 2026-07-29 (post-close).** The dark build itself touched NO
  prod (P10 honored). After re-auth, **UV-P-1 and UV-P-2-baseline were DISCHARGED live** via
  read-only, P10-safe probes ONLY — AWS control-plane (`lambda get-function`, `ecr describe-images`)
  + S3 LIST (`aws s3 ls`); NO Asana pull, NO warm trigger, NO write, NO terraform. Receipts in §4a.
  Bonus finding: the prod warmer is **live and healthy** — image `2201db21` (contains #276) running,
  and the v2 offer plane is receiving fresh warm writes today (the wound's frozen-plane condition is
  gone). **REMAINING deferred:** the S2 DuckDB value-stability probe (MCP server not connected this
  session) → S8; and the full >=2-warm-cycle LEG-2 → eunomia S12 (own-hands, not inheritable).
- **UV-P-3** (sibling substrate surfaces): refined last session (autom8y/autom8y-data/autom8y-ads
  + the `autom8y-cache` SDK); full census at S10.
- **UV-P-4** (constitution path): resolved-model = in-repo `autom8y-asana/.ledge/decisions/` of
  record + S10 kit propagation (S9 doctrine draft bakes it in; two operator SURFACE items — P11
  `.a8/knossos` literal amendment, T3 same-repo-disjoint-files).
- **S9 doctrine** carries its own MF-4 landing-hold sunset (S8-RED escalates to an operator ruling).

## 7. Discipline carried (binding on S8)

- P5: the gate carries the live leg; every divergence explained before the flip.
- P10: prod-touch only via the S4 paced primitive; per-day budget; off-peak; receipts; ad-hoc
  unpaced pulls BANNED (the 429-storm is on record — and the AIMD-reject fix in §4a is load-bearing).
- P8: doors are operator (DP-1 v1-deletion, DP-4a alarm-apply, DP-4b warmer-DMS) — packets with
  dissent; nothing crosses on auto-ratify.
- T2 disjointness: S8 runs active-rite 10x-dev with rite-disjoint SECURITY critics; **S12 final
  attestation runs active-rite eunomia** (`ari sync --rite=eunomia`) — NO eunomia agent authored
  any corridor work this wave (holds).
- Seams FROZEN — a seam-change is an architect finding, never absorbed (held all wave: SEAM-0b,
  [H6], RC-D, F1/C15, F3/C16 all routed + ruled).
- Telos: shipped = LANDED per-sprint (real {path}:{line}); verified_realized stays UNATTESTED
  (eunomia's at S12 — no wave-2 attestation claims STRONG; self-assessment caps MODERATE).
