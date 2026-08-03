---
type: decision
artifact_type: RULING
status: accepted
initiative: substrate-v2-epoch
wave: S8-2
date: 2026-08-03
session: session-20260803-220334-f2a75514
main_sha: 5d62d0b8e8ec18b82e9325ddc249c7a4c4296baf
author: pythia-adjudicator (standing seat, Task dispatch; inscribed verbatim by the main thread per Pythia non-authoring doctrine, DR-2 Option A)
ratification: P13 [A-2026-08-03] staged-auto — inscribed 2026-08-03T16:53:17Z
charter: .ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md (amended [A-2026-08-03])
companion: .ledge/decisions/RULING-potnia-s8-2-wave-entry-2026-08-03.md
consumes:
  - .ledge/reviews/RECEIPT-s8-0-fixture-recapture-2026-07-30.md
  - .ledge/handoffs/IGNITION-substrate-v2-epoch-s8-2-2026-08-03.md
---

> Provenance (P13 [A-2026-08-03]): auto-ratified STAGED on inscription;
> 24h operator amend window opens 2026-08-03T16:53:17Z; one word reverts.
> Pre-registered at N=0 observed divergences, BEFORE any parity evidence.

# ADJUDICATION RUBRIC — Substrate-v2 Epoch · S8-2 Live-Parity Window

**Standing-adjudicator ruling of record · pre-registered before evidence.** Authored by pythia-adjudicator for the S8-2 bounded live-parity window, session `session-20260803-220334-f2a75514`, main @ `5d62d0b8`, 2026-08-03. This rubric is a **P13 staged-auto (non-door) ruling** (Charter L152-158): it auto-ratifies on inscription under a standing 24h operator amend window; one operator word reverts any clause. It binds every subsequent divergence classification, wound-restart ruling, recapture-drift verdict, and cutover-timing counsel I issue for the life of this window. Pre-registration is deliberate: the criteria are fixed **before** any divergence arrives so that no benign-vs-wound call is a post-hoc rationalization of an already-observed number.

**Anchor discipline.** Every criterion below carries a mechanical anchor to charter text (`Charter L{n}`) or a named receipt (`RECEIPT` = `.ledge/reviews/RECEIPT-s8-0-fixture-recapture-2026-07-30.md`; `IGNITION` = `.ledge/handoffs/IGNITION-substrate-v2-epoch-s8-2-2026-08-03.md`). No free-floating thresholds: where a threshold is judgment, it is flagged `[JUDGMENT — amendable]`.

**Scope of my authority.** My rulings are non-door (P13). Doors **DP-1** (v1 deletion register) and **DP-4b** remain operator-halting and outside my authority (Charter L145-158; IGNITION L46). No ruling of mine closes a door, and no HOLD-counsel of mine gates the P9-autonomous auto-flip — it raises the flip's disagreement to operator visibility. EUNOMIA DORMANCY holds; I name no eunomia agents (IGNITION L33).

---

## Section 1 — Divergence Classification Criteria {explained-benign | wound}

**Governing posture.** The substrate's own truth posture governs the adjudicator: **refuse > wrong** (P2, Charter L55-57). The epoch exists because `$79,585` was served under a false-fresh "verified 1m ago" when truth was `$84,385` (Charter L23) — a number served that should have been refused. The classifier inherits that posture: a divergence is benign only when it is *affirmatively explained*, never by default.

**Classification-input contract (teeth).** A divergence is unclassifiable — and therefore defaults to WOUND (see below) — unless it arrives at my seat with all of: (a) both the v1 value and the v2 value; (b) both capture instants **plus** the v2 watermark provenance (BUILD instant, `saved_at`, `row_count`) per the RECEIPT snapshot idiom (RECEIPT L53-57); (c) a per-section decomposition attempt in the RC-A-2 ledger idiom (RECEIPT L112-123); (d) the per-touch budget receipt for the capture (P10, Charter L122-126). Missing any element → `insufficient-evidence, re-capture required` (not a benign pass).

### Expected benign classes {explained-benign}

- **B1 — Capture-skew within one warm cadence.** v2's rebuild instant differs from v1's read instant, and the entire delta is attributable to real Asana state that changed between the two capture instants, with the two snapshots each internally time-ordered. *Anchor:* RECEIPT TORN-READ GUARD ordering (sections `< build < saved_at < write`, RECEIPT L64-78) — a skew that is internally consistent and time-ordered is a real-world capture artifact, not a defect; P5 explicitly runs "v2 … beside v1 against live prod" (Charter L72), so they are not co-instant and bounded skew is expected.
- **B2 — Real-edit section-composition churn, per-section-decomposable.** The **leg-1 precedent class**: rows moved between sections, or mrr changed on real offers, such that the delta decomposes per-section into individually-attributable real edits. *Anchor:* RECEIPT decomposition ledger — `−$3,400 / −4.03%` decomposed to ACTIVE `−$1,500`, OPTIMIZE `+$3,000`, STAGED `$0`, synthetic OTHER `−$4,900`, each line explained (RECEIPT L106-123). The load-bearing property is **per-section decomposability with every line attributable**, not the magnitude.
- **B3 — Freshness-proof-metadata delta (no composition/digest touch).** A divergence purely in proof-metadata (e.g. `sla_seconds`) that leaves the served value, composition, and content digest byte-unchanged. *Anchor:* RECEIPT Amendment C17 — `sla_seconds` 180→3600 with "VALUE, composition, and content digest are byte-unchanged … sla_seconds is proof-metadata, not a composition/digest input," proven by `test_fixture_parquet_bytes_rederive_the_pinned_constants` (RECEIPT L146-156).
- **B4 — Section-name normalization / encoding.** A divergence explained wholly by a known encoding/normalization difference where rows and value reconcile. *Anchor:* RECEIPT — prod section uses plain hyphen U+002D where exemplar #1's synthetic fixture used en-dash U+2013 (RECEIPT L84, L117); the +$3,000 OPTIMIZE line traced to exactly this.
- **B5 — Fixture-side synthetic construct with no prod analogue.** A divergence attributable to a fixture-only synthetic bucket that has no S3 analogue — **benign only when the synthetic construct is on the fixture side, never the live side.** *Anchor:* RECEIPT synthetic OTHER `$4,900` bucket, "exemplar #1 synthetic bucket; no S3 analogue" (RECEIPT L118, L122-123).

### Wound classes {wound}

- **W1 — Digest-inconsistent / determinism break.** Same source bytes yielding a different served number, or the same composition digest yielding a different value, or a re-derivation producing an unstable digest. *Anchor:* RECEIPT "drift tripwire: same bytes → same digest" (RECEIPT L96); this is the serialization-determinism invariant broken — the substrate cannot prove its number (P2).
- **W2 — Over-refusal by v2.** v2 refuses a number that is *provably current* and that v1 correctly serves. *Anchor:* north star "a number served is a number the system can prove" (Charter L44) — a provable number must be servable; a v2 that refuses provable numbers recreates signal-fatigue in the opposite direction (Charter L100 "false-staleness is the alarm-fatigue direction that buried the original wound"). **Carve-out:** an over-refusal / false-signal emitted by the **v1 #276-era honesty-floor machinery itself** is NOT a v2 wound — it is a P6-floor-integrity fix (FIX-1 class, Charter L93-103), handled as a scoped adversarially-reviewed micro-packet, and does not restart the v2 clock unless it contaminated the v1 baseline (see Section 2).
- **W3 — Non-decomposable delta.** A v1-vs-v2 delta that does **not** decompose per-section into attributable real edits — the direct inverse of B2. *Anchor:* P5 "every divergence is explained before the flip" (Charter L73); an undecomposable delta is by definition unexplained.
- **W4 — Silent-serve where refuse was required (cardinal wound).** Any case where v2 serves a number that failed a provability predicate — torn read, stale-beyond-SLA, plane-blind key, or missing verification — without loud refusal. *Anchor:* P2 (Charter L55-57), RC-F "observability can read green while broken" (Charter L35), and the original wound itself (Charter L23). This is the class the entire epoch was chartered to make impossible-by-construction.
- **W5 — Budget/pacing violation during capture.** Any ad-hoc/unpaced pull, per-day budget overshoot, cross-process lock failure, or 429-storm during a window capture. *Anchor:* P10 "ad-hoc unpaced pulls are banned for everyone, agents included; the 2026-07-27 429-storm during ad-hoc validation is the counterexample on record" (Charter L122-126); RC-E (Charter L34); IGNITION L40 "per-day budget ENFORCED." A pacing violation corrupts capture provenance and is separately an operator-visibility interrupt trigger (Charter L81).
- **W6 — Torn read / internal inconsistency.** A snapshot whose watermark does not post-date its section artifacts, or whose `row_count`/column-set is inconsistent, used as parity data. *Anchor:* RECEIPT TORN-READ GUARD (RECEIPT L64-78) — a torn snapshot is unprovable and must never enter the ledger as a clean observation.

### Default for unclassifiable divergence

**Lean WOUND.** A divergence that resists classification — because evidence is incomplete, because decomposition does not close, or because the explanation rests on an unconfirmed assumption — is treated as a wound until affirmatively explained. *Anchor:* P2 "refuse > wrong" (Charter L55-57); the adjudicator applies at the ruling layer the exact posture the substrate applies at the serving layer. Benign is never the default; an unexplained number is a wounded number.

---

## Section 2 — Wound-Restart Rule (the P5 clock)

**Authority.** "A wound-class divergence restarts the clock per pythia's ruling" (Charter L80). The restart is my ruling; this section fixes how I rule it before any wound arrives.

- **Default: FULL restart of the parity count.** On a wound classification, the ≥2-warm-cycle count and the ~3-day floor both reset to zero. Warm cycles banked *before* the wound are invalidated for the parity count. *Rationale, anchored:* the ≥2-cycle + ~3-day-floor bar (Charter L76-78) exists to prove **sustained clean parity**; a wound is proof parity was not sustained, so cycles observed under a now-known-defective substrate cannot count toward "sustained clean." Cadence diversity must be re-observed post-fix.

- **Partial credit — narrow, affirmatively-gated exception.** Banked warm cycles retain credit only IFF the DELTA fix is proven **orthogonal** to the banked cycles' evidence — i.e. the wound mechanism could not have been latent in those observations, proven by a **two-sided teeth proof** (the fix's discriminating test bites only on the defect; the no-defect variant, including the banked-cycle inputs, passes GREEN). *Anchor:* discriminating-canary two-sided-teeth doctrine; and the P6-floor-integrity logic of a scoped, adversarially-reviewed, bounded-blast-radius fix (Charter L93-103). If orthogonality is proven, only the fix's own re-observation is required; if not proven, FULL restart. Default is full restart; partial credit requires affirmative proof, never assumption. `[JUDGMENT — amendable]`: the orthogonality bar (two-sided teeth + latency-impossibility argument) is the threshold; loosening it is an operator/amend decision.

- **Floor-integrity carve-out.** A P6-floor-integrity fix (false-signal in v1's honesty-floor machinery, FIX-1 class) is not a v2 wound and does not by itself restart the v2 parity clock (Charter L93-103) — **unless** the false signal contaminated the v1 baseline that v2 was compared against. If contaminated, the affected comparisons are void and must be re-observed; cleanly-compared cycles survive. This is the one place a non-wound event can partially reset the ledger, and only the contaminated comparisons.

- **Re-arm evidence after a DELTA fix lands.** The window re-arms only on all of: (a) the DELTA merged on green with adversarial review (P7, Charter L106); (b) a two-sided teeth proof that the wound class is now unconstructable-by-construction or fail-loud (P3, discriminating-canary doctrine); (c) the re-armed window rides the S4 rebuild primitive **exclusively** with per-day budget enforced (IGNITION L40); (d) the restarted count begins at the first post-fix warm cycle.

- **7-day hard ceiling under restart.** `[JUDGMENT — amendable]` I rule the 7-day **hard** ceiling (Charter L78) is measured from the **original** window arm and is **not** reset by a wound restart — otherwise "hard" is meaningless and the RC-D immortality class (Charter L33, L68) creeps back in through repeated restarts. Consequence: if a wound restart cannot complete the ≥2-cycle + ~3-day-floor requirement within the original 7-day ceiling, the window converts from auto-close to an **operator-surfaced decision** (extend-or-hold) — a wound-driven ceiling breach is exactly the signal that must reach the operator, not auto-extend. This surfacing rides the wound-class interrupt (Charter L81).

---

## Section 3 — Recapture-Drift Verdict Protocol (O4 leg-2)

**The comparison.** The window-open S3-only re-snapshot of the offer plane (project `1143843662099250`, `EntityType.OFFER`; `+unit`/`+siblings` EXCLUDED per O4 scope, RECEIPT L17-18) is compared against the **S8-0 leg-1 pin**, which has two pinned surfaces (both to be re-derived):
- **Full-plane projection pin:** `offer_plane_section_mrr.parquet`, sha256 `614c9ab8…` — the `(section, mrr)` projection of the whole offer frame (the dispatch's `614c9ab8 / ~22-section` surface; RECEIPT L130-131).
- **In-scope served-aggregate pin:** `$80,985` = 61 in-scope rows over the 3 offer-lifecycle sections {ACTIVE 47/$60,085, OPTIMIZE - Human Review 7/$10,900, STAGED 7/$10,000}; composition digest sha256 `4e711a7a…` (RECEIPT L86-95).

*Reconciliation note (surfaced, not silent):* the 61 in-scope served rows are concentrated in 3 sections **within** the ~22-section projection; leg-2 MUST re-report both the full-plane section cardinality and the in-scope 3-section aggregate against S3 ground truth. Any change to the in-scope section *set* (a section entering/leaving the served aggregate) is itself a composition change requiring decomposition, even at zero net value.

### Decision rule

- **{no-drift}** — the re-snapshot re-derives **byte-identically**: same served value `$80,985`, same composition digest `4e711a7a…`, same projection sha `614c9ab8…`. *Anchor:* "same bytes → same digest" (RECEIPT L96). Verdict issued; the exemplar pin holds unchanged.
- **{delta+explanation}** — any change in value/composition/digest that **decomposes per-section** into individually-attributable real Asana edits, exactly as leg-1's `−$3,400` decomposed (RECEIPT L112-123). The verdict carries the full decomposition ledger with each line's attribution, and the exemplar is **re-pinned** to the new snapshot with the drift ledger inscribed (a P13 non-door staged re-pin; 24h amend).

### Decomposition-depth trigger

- Digest-identical → no decomposition (no-drift).
- **Any digest change requires decomposition**, including value-identical-but-digest-changed (a zero-net composition change — e.g. a row moved between two sections — is precisely where a wound hides and must be traced).
- **Any value change requires per-section decomposition regardless of magnitude.** There is no "small enough to skip": the original wound was a `$4,800` / ~6% delta that green signals missed (Charter L23). P5 requires *every* divergence explained (Charter L73).
- `[JUDGMENT — amendable]` **Prominence threshold** (governs handoff emphasis, not the decomposition requirement): an explained drift of `|Δvalue| ≥ 5%` **OR** `|Δvalue| ≥ $4,800` **OR** any change to the in-scope section set is flagged prominently in the daily parity handoff rather than riding quietly. The `$4,800` anchors to the original-wound magnitude (Charter L23); the 5% is set just above leg-1's benign `−4.03%` (RECEIPT L109) so a leg-1-like benign drift does not trip it. Below threshold **and** fully decomposed → rides the daily handoff as routine delta+explanation.

### What makes the drift verdict FAIL outright

- **Torn-read / internal inconsistency** in the re-snapshot (watermark does not post-date sections; `row_count`/column mismatch) → the snapshot is not a valid pin candidate; **no drift verdict issues** until a clean snapshot is captured and the torn-read guard passes (RECEIPT L64-78). This is a W6 wound if the torn snapshot was nonetheless used.
- **Value/composition delta that does not decompose per-section** → this is a **W3 wound**, not a benign drift. The verdict is `DELTA-UNEXPLAINED`; it routes to Section 2 wound handling and the exemplar is **NOT** re-pinned. Re-pinning to an unexplained snapshot would launder a wound into the baseline — forbidden.
- **Digest instability** (same bytes, different digest across two derivations) → **W1 wound**; the verdict FAILS and the snapshot cannot be trusted as a pin at all.

### Re-pin rule

The exemplar re-pins **only** on a `{delta+explanation}` verdict where the new snapshot passes the torn-read guard AND decomposes fully. A re-pin inscribes, in the RECEIPT's own format: new served value, new composition digest, new projection sha, the decomposition ledger, and full snapshot provenance (ETag / VersionId / BUILD instant / `saved_at`). The re-pin is a P13 non-door staged ruling (24h amend), never a door.

---

## Section 4 — Cutover-Timing Counsel Shape

**Standing.** The auto-flip is **P9-autonomous**, not a door: trigger re-confirmed as "PT-03 PASS + rollback-drill green → the flip fires P9-autonomously; rollback stays armed through PT-04" (Charter L83-85; IGNITION L44 step 7). My counsel is advisory — I do **not** gate the flip (gating would make me a door, which P13 forbids). My HOLD-counsel is a staged non-door ruling the corridor should honor; a HOLD I issue that the corridor overrides is itself a divergence that surfaces to operator visibility via the 24h amend lever.

### What I require to counsel PROCEED (the four-conjunct evidence test, receipts not attestation)

All of the P5 [A-2026-08-03] conjuncts GREEN with receipts (Charter L76-78):
1. **≥2 distinct warm cycles observed in parity** — distinct, not two cycles in one burst.
2. **Every ledger divergence explained** — each classified `{explained-benign}` by me; zero divergences in pending-classification.
3. **Zero open wounds.**
4. **Budget honored** — per-touch receipts, per-day cap respected, zero ad-hoc pulls (P10).

Plus the timing/gate conditions:
5. **~3-day floor elapsed with genuine cadence diversity** (Charter L78) — the ≥2 cycles span ≥2 distinct cadence points, not a monoculture.
6. **7-day hard ceiling not breached** (Charter L78; and per Section 2 not reset by restart).
7. **PT-03 PASS** — the HARD, de-novo, fresh-instance gate, Q1-Q6 (IGNITION L43 step 6).
8. **Rollback drill GREEN in the strong sense** — "prove the v1 restore *actually serves*," not merely that rollback is armed (IGNITION L44 step 7; P5 "Rollback = restore v1," Charter L73). If the restore does not actually serve, the flip is irreversible-in-practice and becomes a de-facto door.

### What makes me counsel HOLD despite formal satisfaction

`[JUDGMENT — amendable]` — these are discretionary adjudicator HOLDs beyond the binding conjuncts; each raises to operator visibility if overridden:

- **Thin-margin benign residue.** Any divergence classified benign only on borderline evidence (decomposition closed only to rounding; a section attribution rested on an unconfirmed assumption) → HOLD for one more clean warm cycle. *Anchor:* P2; the original wound passed green signals (Charter L23, L35).
- **Cadence monoculture.** The ≥2 warm cycles were observed under the same cadence conditions (both off-peak, both low-churn) such that parity was never exercised under high-churn / on-peak load — the ~3-day floor's *cadence-diversity purpose* (Charter L78) is formally-but-not-substantively met → HOLD.
- **Alarm anomaly unresolved.** PROV-2 (expected to clear at first sweep, IGNITION L32 preflight 4) has not cleared, or any PROV-1..6 alarm is anomalous → the RC-F "green while broken" risk is live (Charter L35) → HOLD. Alarm anomaly is a standing interrupt trigger (Charter L81; IGNITION L42).
- **Restore-fidelity unproven under representative read.** Rollback drill green only under trivial conditions → HOLD until v1-restore-serves is proven under a representative read (P5, Charter L73).
- **Ceiling-pressure fake-complete.** Approaching the 7-day hard ceiling with any temptation to classify a borderline divergence benign to close before it → HOLD and surface to operator; "Never calendar-close thin; never fake-complete" (IGNITION L41 step 4). A ceiling breach converts the auto-close to an operator decision (Section 2).
- **Doctrine-not-yet-legible FLAG.** If the divergence ledger required so many bespoke explanations that parity is defensible only by an expert reading the full ledger — not legibly self-evident — that signals v2 is not yet "small enough that the proof is legible" (north star, Charter L44-47). This is a named FLAG in my cutover counsel to the operator, not a hard block.

---

## Section 5 — Provenance Line (carried by every ruling I issue)

Every divergence classification, wound-restart ruling, recapture-drift verdict, and cutover-timing counsel I issue in this window carries, verbatim:

```
Ruling:        {classification | wound-restart | drift-verdict | cutover-counsel}
Adjudicator:   pythia-adjudicator (standing seat, substrate-v2-epoch S8-2 parity window)
Session:       session-20260803-220334-f2a75514
Main @:        5d62d0b8   Date: {ISO-8601}
Ruling class:  P13 staged-auto (NON-DOOR) — auto-ratifies on inscription;
               standing 24h operator amend window (one word reverts);
               this provenance disclosed in-record (Charter L152-158).
Anchors:       {charter clause(s) L{n} and/or named receipt(s) this ruling rests on}
Door note:     Doors DP-1 / DP-4b remain operator-halting and outside this seat's
               authority; no ruling here closes a door, and no HOLD-counsel here
               gates the P9-autonomous auto-flip — it raises disagreement to
               operator visibility (Charter L145-158; IGNITION L46).
```

---

### Provisional flags (pre-registration honesty)

This rubric is authored at N=0 observed divergences. The `[JUDGMENT — amendable]` thresholds — partial-credit orthogonality bar (§2), 7-day-ceiling-from-original-arm (§2), the 5% / $4,800 / section-set-change prominence trigger (§3), and the discretionary HOLD triggers (§4) — are the surfaces most likely to need amendment once real divergences land; each is revisable within the standing 24h operator amend window without re-authoring the rubric. The classification-input contract (§1 teeth) and the lean-wound default (§1) are structural and should not be loosened without an explicit operator ruling, since they encode the P2 refuse->wrong posture the epoch exists to install.

---

**Files referenced (absolute paths):**
- `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md` (binding; [A-2026-08-03] blocks P5 L76-85, P6 L93-103, P12 L145-150, P13 L152-158)
- `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/reviews/RECEIPT-s8-0-fixture-recapture-2026-07-30.md` (O4 leg-1 precedent; pins, decomposition ledger, torn-read guard)
- `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/handoffs/IGNITION-substrate-v2-epoch-s8-2-2026-08-03.md` (window sequence, operator-visibility law, PT-03/cutover/PT-04 flow)
