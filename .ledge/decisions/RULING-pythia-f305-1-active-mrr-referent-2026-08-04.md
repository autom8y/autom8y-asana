---
type: decision
artifact_type: RULING
status: accepted
initiative: substrate-v2-epoch
wave: S8-2
date: 2026-08-04
session: session-20260803-220334-f2a75514
main_sha: e1600ff8 (ruling derived at 5d62d0b8 anchors; serving-code lines verified unchanged through #301/#302/#303 which touch no metrics/models code)
author: pythia-adjudicator (standing seat, Task dispatch; inscribed verbatim by the main thread per Pythia non-authoring doctrine, DR-2 Option A)
ratification: P13 [A-2026-08-03] staged-auto — inscribed 2026-08-03T18:53:32Z (UTC)
charter: .ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md (amended [A-2026-08-03])
rubric: .ledge/decisions/RULING-pythia-s8-2-adjudication-rubric-2026-08-03.md
resolves: qa-adversary blocking finding F-305-1 (PR #305 NO-GO, QA-s8-2-budget-hardening-pr301-2026-08-03.md WU-3 section)
consumed_by: WU-3 iteration-2 (feat/s8-2-arm-parity-window)
---

> Provenance (P13 [A-2026-08-03]): auto-ratified STAGED on inscription;
> 24h operator amend window opens 2026-08-03T18:53:32Z; one word reverts.

# pythia referent ruling — F-305-1: what "active_mrr" DENOTES in the S8-2 parity predicate

**Ruling in one line:** the referent is **Option (a)** — active_mrr denotes the **production-served number**; the instrument architecture is **Option (c)** — both legs are ledgered, with the served-definition leg the one PT-03 Q1 and the auto-flip hang on. **Option (b) is REJECTED.** I am ruling the REFERENT of the operator-verbatim term, anchored to the serving code; I am not amending the predicate.

### 1. Own-hands code confirmation — the referent, pinned with file:line anchors

I verified the serving definition directly (not from paraphrase). **active_mrr** is the scalar produced by the registered `Metric(name="active_mrr")` — computed as:

- **Section set = the OFFER_CLASSIFIER "active" group — 22 sections** (`src/autom8_asana/models/business/activity.py:181-208`; I counted the group members: 22, exactly as qa reported). Applied in `src/autom8_asana/metrics/compute.py:66-79` via `classifier.sections_for(AccountActivity("active"))`, matched **case-insensitively** (`.str.to_lowercase().is_in(...)`, compute.py:79).
- **Filter `mrr` not-null AND `mrr > 0`** (`src/autom8_asana/metrics/definitions/offer.py:40`; applied compute.py:105-107).
- **Dedup by `(office_phone, vertical)`, keep="first"** (`offer.py:20-24, 42`; applied compute.py:114-116). The dedup is load-bearing and semantically necessary — offer.py:29-33 states MRR lives at the Unit level and sibling offers share it, so **without dedup the sum is inflated proportional to offers-per-unit.**
- **Cast `mrr`→Float64, then sum** (offer.py:35-39; compute.py:100-103; caller sums per compute.py:50-52).

**The WU-3 build pinned instead** the 3-section receipted set {ACTIVE, OPTIMIZE - Human Review, STAGED}, **raw — no dedup, no mrr>0 filter.** All three are members of the 22-section active group (activity.py:188, 200, 201), so the 3-section set is a strict subset; **19 active sections are omitted.**

**The blind spot is structurally confirmed by me; its magnitude by qa.** I verified own-hands that qa's three named sections — "OPTIMIZE QUALITY - Update Targeting" (activity.py:194), "OPTIMIZE QUANTITY - Request Asset Edit" (activity.py:189), "OPTIMIZE QUANTITY - Update Offer Name" (activity.py:193) — are in the classifier active set and outside the 3-section pin, so they ARE structurally omitted from the as-built comparison. qa's **$14,360** figure (from the leg-2 fixture bytes) is the dollar weight; note it is a **lower bound** — it covers 3 of the 19 omitted active sections, and the raw 3-section sum ALSO lacks dedup, so its relationship to the served number carries **two offsetting errors** (omission pushes it down, missing-dedup pushes it up) whose net **varies with the data**. That instability is decisive below.

### 2. Why Option (b) is REJECTED — it would reinstall the founding wound in the gate

Ruling (b) would require me to declare the 3-section exemplar definition authoritative **over the production serve**, and to name why the $14,360-plus blind spot is acceptable. **I cannot name an acceptable rationale, because there is none:** a v2 fetch-plan that omits any of the 19 uncovered active sections would read **CLEAN** against a 3-section anchor while the served number silently loses value. That is the exact **silent-loss shape of the founding wound** ($79,585 served while truth was $84,385, Charter L23) and the exact **RC-C failure** — "plane-correctness is per-call-site manual discipline; the enumerated guard drifted and missed a whole layer" (Charter L32). Ruling (b) makes RC-C **constructable inside the parity gate itself**, violating the epoch's own acceptance bar (Charter L37-39: v2 is not done until each RC is impossible-by-construction or fail-loud) and P2 (refuse > wrong). A gate that cannot see the wound it exists to prevent is not a gate. **REJECT.**

### 3. Why Option (a) is the faithful referent — it respects the operator's verbatim term

The predicate names **"active_mrr"** — a term with a **single authoritative referent in the serving code**: the registered metric of that exact name (offer.py:27). The 3-section sum is named "active_mrr" **nowhere** in the code; the recapture receipts LABELED it "served_value," which qa has shown is a **misnomer**. Ruling (a) pins active_mrr to what the system actually serves under that name — the number a consumer receives, and the number the founding wound corrupted. Ruling (b), by contrast, would have me **substitute** a fixture aggregate for the operator's term — redefining the predicate's referent to a number the system never serves. That substitution is outside my authority and would corrupt the operator-verbatim predicate. **(a) is the only reading that respects the operator's term rather than replacing it.**

### 4. Exemplar-role disposition — the 3-section corpus RETAINS its role; do NOT rip out the re-pin

**The corpus exemplar and the parity anchor are DIFFERENT INSTRUMENTS measuring DIFFERENT things.** Stated explicitly so iteration-2 does not tear out the re-pin:

- **The 3-section exemplar corpus** is a **byte-determinism / serialization fixture** (its role is `test_fixture_parquet_bytes_rederive_the_pinned_constants`: same retained bytes → same pinned constant; guards W1 non-determinism) **and** the O4 **corpus-continuity / drift tripwire** (its aggregate over live re-snapshots drifts with real motion, as leg-2 showed). **Neither role requires it to equal active_mrr.** Any stable deterministic aggregate over a fixed byte corpus serves both roles. **It RETAINS its role; the PR #303 re-pin STANDS.**
- **active_mrr (22-section + dedup + filter)** is the **served-number parity anchor** — the LEG-2 / predicate referent, the leg PT-03 Q1 and the auto-flip hang on.

**Label correction (non-door, P13 staged):** the O4 receipts' "served_value" label for the 3-section sums ($80,985 / $75,985) is a **misnomer** and should be re-labeled **"exemplar / corpus aggregate (3-section raw)"** going forward, so the fixture aggregate is never again mistaken for the served number. **My leg-2 drift verdict is UNAFFECTED:** it compared the 3-section exemplar aggregate to itself across two time-points (like-to-like), so the drift ruling (real-motion, explained, decomposed) stands as a corpus-continuity ruling; it never claimed the exemplar aggregate was active_mrr. Only the LABEL is corrected, not the ruling.

### 5. The $79,585 coincidence — UV-P, falsified as an identity, NOT to be chased

The receipts note $79,585 = exemplar #1's 3-section stale sum, and a 2026-07-13 CLI showed value=$79,585 with in_scope_count=22. That the two definitions coincided at one stale instant is **UV-P** (unverified from code) and is **falsified as a definitional identity** by today's ~$14,360 divergence between the 3-section-raw and 22-section-deduped numbers. It was a **historical coincidence, not an identity** — and the coincidence is precisely how the misnomer survived unquestioned (RC-B: correctness by matching green signals, not content-derived truth). Resolving whether the coincidence was real is **not load-bearing** — ruling (a) holds either way — and it **must NOT be chased via an ad-hoc Asana pull** (P10, Charter L122-126). It is resolvable later from retained historical fixtures if ever needed. Marked UV-P; parked.

### 6. Capture-mechanics conditions attached to Option (a) (BINDING on iteration-2)

The served-definition parity is valid only if the served number is computed **identically on both v1 and v2 sides, in-memory at capture**, per these conditions — each anchored to the serving code:

1. **Section set sourced FROM THE CLASSIFIER, never hardcoded.** Both sides derive the active set from `OFFER_CLASSIFIER.sections_for(AccountActivity("active"))` (activity.py:181-208 via compute.py:78), NOT a hardcoded list. **A hardcoded subset is the RC-C drift vector that produced this very defect.**
2. **Fetch-plan coverage assertion — fail-closed (anti-RC-C keystone).** v2's fetch-plan section set MUST be a **superset of the classifier active set**; if ANY classifier-active section is absent from the fetch plan, **REFUSE LOUDLY — do not serve a partial sum.** This is the "impossible-by-construction or fail-loud" wiring (Charter L37-39). This condition is what makes the $14,360 silent-loss shape unconstructable.
3. **Dedup by `(office_phone, vertical)`, keep="first", identical both sides** (offer.py:23, compute.py:114-116). Same column tuple, same keep semantics; dedup-key columns present and identically typed on both sides.
4. **Filter `mrr` not-null AND `mrr > 0`, identical both sides** (offer.py:40, compute.py:105-107).
5. **Cast `mrr`→Float64 before aggregation, identical both sides** (offer.py:38, compute.py:100-103) — no dtype-driven aggregation drift.
6. **Section-name matching case-insensitive (lowercased both sides)** (compute.py:79) — verified own-hands; both sides apply the same `.str.to_lowercase()`.
7. **Aggregation = sum of `mrr` post-filter-post-dedup** (compute.py:50-52) — identical both sides.
8. **PII discipline preserved.** Dedup + filter computed **in-memory at capture on both sides**; only the **scalar active_mrr** and a **PII-safe per-classification composition digest** are committed to the ledger. Dedup keys (`office_phone`) are PII and NEVER land in a committed receipt (extends the leg-1/leg-2 PII-projection discipline, RECEIPT L127-137, to the served definition).
9. **Refusal semantics (P2 crux).** The served leg's provability predicate = **every classifier-active section present AND fresh-within-SLA AND torn-read-clean.** If any fails → active_mrr is **REFUSED, not partially served.** In the parity comparison, refuse-vs-serve is a **first-class outcome**, never coerced to zero or skipped: v2 refusing where v1 serves a provable number is over-refusal (W2); v2 refusing where a section is genuinely unavailable is CORRECT (and v1 serving a partial/stale number there is the wound). At an identical capture instant the two computed scalars must match **penny-exact** (deterministic function of the frame bytes); any nonzero delta at identical instant is W1/W3; a delta from differing instants is benign B1 only if it decomposes (rubric §1).

### §5 Provenance block

```
Ruling:        referent-definition (F-305-1) — active_mrr referent PINNED to the served number
Disposition:   Option (a) referent + Option (c) instrument architecture; Option (b) REJECTED
Adjudicator:   pythia-adjudicator (standing seat, substrate-v2-epoch S8-2 parity window)
Session:       session-20260803-220334-f2a75514
Main @:        5d62d0b8   Date: 2026-08-04
Ruling class:  P13 staged-auto (NON-DOOR) — auto-ratifies on inscription;
               standing 24h operator amend window (one word reverts);
               this provenance disclosed in-record (Charter L152-158).
Rubric:        RULING-pythia-s8-2-adjudication-rubric-2026-08-03.md (P13); §1 (P2/RC-C wound classes),
               §3 (drift-verdict integrity confirmed unaffected).
Code anchors:  activity.py:181-208 (22-section classifier active set); offer.py:20-43
               (active_mrr: dedup (office_phone,vertical) + mrr>0 filter + Float64 sum);
               compute.py:66-79/100-107/114-116 (classification+filter+dedup pipeline).
               Read own-hands at HEAD 5d62d0b8; F-305-1 structurally confirmed.
Predicate:     operator-verbatim, NOT amended — REFERENT pinned only, anchored to serving code.
Door note:     Doors DP-1 / DP-4b remain operator-halting and outside this seat. This ruling,
               the label correction, and the capture-mechanics conditions are all non-door.
```

**Ruling: active_mrr denotes the production-served number — 22-section classifier active set, deduped by (office_phone, vertical), mrr>0-filtered (offer.py:20-43 / compute.py:66-116). Option (b) rejected (reinstalls the founding wound). The 3-section exemplar corpus retains its role as a distinct byte-determinism / corpus-continuity instrument — PR #303 re-pin STANDS, "served_value" label corrected to "exemplar aggregate." Iteration-2 builds the served-definition parity harness under the 9 capture-mechanics conditions, fail-closed refusal being the anti-RC-C keystone.**
