---
type: decision
artifact_type: RULING
status: accepted
initiative: substrate-v2-epoch
wave: S8-2
date: 2026-08-03
session: session-20260803-220334-f2a75514
main_sha: 5d62d0b8e8ec18b82e9325ddc249c7a4c4296baf
author: potnia (10x-dev, Task dispatch; inscribed verbatim by the main thread)
ratification: P13 [A-2026-08-03] staged-auto — inscribed 2026-08-03T16:50:01Z
charter: .ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md (amended [A-2026-08-03])
consumes:
  - .ledge/handoffs/IGNITION-substrate-v2-epoch-s8-2-2026-08-03.md
  - .ledge/handoffs/HANDOFF-s8-0-complete-awaiting-operator-2026-07-30.md
---

> Provenance (P13 [A-2026-08-03]): auto-ratified STAGED on inscription;
> 24h operator amend window opens 2026-08-03T16:50:01Z; one word reverts.
> Recon substrate: 4-agent sonnet Explore fanout + SVR vet (35/40 anchors HOLD),
> preflight receipts discharged own-hands in-session (PROV sweep via CloudWatch
> describe-alarms; fixture-replay 285/285 re-run at HEAD).

# RULING OF RECORD — potnia S8-2 wave-ENTRY orchestration (substrate-v2-epoch)

session-20260803-220334-f2a75514 · main @ 5d62d0b8 · 2026-08-03 · rite 10x-dev

## (1) Wave-ENTRY verdict: **GO** (into the build-to-arm corridor, NOT into an immediate live touch)

**Gate-of-record statement.** S8-2 entry is admitted on the discharged-own-hands conjunction: gates OPEN (DP-4a applied · C8/C17 merged `86aeb0d3`) AND main Test GREEN at `5d62d0b8` (at/after `86aeb0d3`) AND FIX-1 MERGED (#299) AND #298 amendments MERGED (`9797579c`) AND #279 held-draft (correct) AND fixture-replay 285/285 re-run at HEAD AND PROV-1..6 live with PROV-2 ALARM-as-predicted since 2026-07-30T13:57Z (C10 fires-side banked, clears at first sweep). **The window does NOT open on entry.** Entry authorizes corridor work only; the first armed prod touch is itself gated behind WU-2 (budget-ledger hardening landed) AND WU-3 (arming past P7) — this preserves P10 (no ad-hoc unpaced pulls) and G3 ordering. G1-G5 are decompose-and-sequence findings, not entry blockers.

## (2) Sequenced work-unit list (P7 economy — rigor concentrates at the window (P5) and doors (P8) ONLY; corridor stays un-gold-plated)

| # | Unit | Owner | Exit bar | Receipt artifact |
|---|------|-------|----------|------------------|
| WU-1 | O4 leg-2 window-open re-snapshot (S3-only, receipted) + UV-P-6 discharge | principal-engineer; **pythia** rules drift {no-drift \| delta+explanation} | Real section counts captured; drift verdict appended; budget-cap + asset_edit/process SLA re-ratification data produced | append to `RECEIPT-s8-0-fixture-recapture-2026-07-30.md` + UV-P-6 discharge note |
| WU-2 | Budget-ledger hardening (BEFORE any armed touch — G3): corrupt-JSON fail-loud, cross-process flock lock, multi-unit overshoot close | principal-engineer implements (reuse proven flock `polling_scheduler.py:569-621`); **qa-adversary** = P7 adversarial gate | All three closed; per-day cap calibrated from WU-1 data; **ledger path PINNED**; discriminating tests green + adversarial GO | PR + green CI + `.ledge/reviews/` qa-adversary GO |
| WU-3 | ARM the window — minimal path only (G1): 3a v1 Materialization prod constructor · 3b SubstrateRebuilder prod caller (rides S4 primitive EXCLUSIVELY) · 3c PacedLiveParitySource outbound arm (concrete callable + armed=True) · 3d per-touch receipt writer (persist FetchTelemetry, P10) · 3e PROV-2 in-process sweep driver (G2-a) | principal-engineer; **qa-adversary** P7 gate per unit | Dark→armed transition proven; **NO general-purpose rebuild framework** (only what the ledger requires); PROV-2 clears on first sweep, RECORDED as RC-F-2 quiet-side evidence | PR(s) + green CI + qa-adversary review + CloudWatch PROV-2-clear receipt |
| WU-4 | Run the window (P5 [A-2026-08-03] window-law) | principal-engineer runs paced parity; **pythia** classifies each divergence {explained-benign \| wound} | ≥2 distinct warm cycles in parity AND every divergence explained AND zero open wounds AND budget honored; 3-day floor / 7-day ceiling; wound → DELTA to owning module + **clock restart** | daily `HANDOFF-s8-parity-<date>.md` (ledger + receipts + budget state); full ledger → PT-03 |
| WU-5 | PT-03 HARD gate (fresh-instance potnia, de novo, per-question receipts) | **fresh potnia**; **cross-rite security critics** (threat-modeler + penetration-tester) for Q3 | Q1-Q6 all PASS w/ per-question receipts; FAIL → back to build, no cutover | PT-03 packet |
| WU-6 | On PASS, in order: rollback drill → PT-CUTOVER auto-flip (P9-autonomous) → PT-04 (≥2 warm cycles v2-serving, MODERATE cap) → un-hold #279 → author DP-1 + DP-4b door packets at PT-04 close | fresh potnia; DP-1/DP-4b **HALT for operator word** | rollback proven-serving; cutover receipt; PT-04 warm-cycle receipts; DP-1 register + adversary dissent staged | cutover receipt + DP-1/DP-4b packets |

**Conditional back-route:** if WU-3c/3d surface a *seam-change* (not seam-use), back-route to **architect** as a finding per handoff §6 ("a seam-change is an architect finding"). Arming an already-designed dark seam is seam-USE → stays with principal-engineer.

## (3) G1-G5 rulings

- **G1 — ARM decomposes as WU-3 (5 minimal build units), each P7-gated.** Rationale: arming is net-new production wiring, so it is a build task under P7 (discriminating tests + adversarial review), not a config flip — but scoped to the minimal live-number path the ledger requires; a general-purpose rebuild framework is gold-plating and is rejected.
- **G2 — Option (a): drive PROV-2 sweeps in-process from the window loop THIS wave; DEFER option (b) terraform EventBridge to a post-window packet.** Rationale: (a) is a staged/reversible CloudWatch write (P9-autonomous, no door); (b) is a cross-repo terraform apply (operator-reserved under P9) and durable-scheduler scope that P7 forbids smuggling into the corridor — defer it explicitly rather than inflate the wave.
- **G3 — CONFIRMED: WU-2 lands BEFORE any armed prod touch, cap calibrated from WU-1 UV-P-6, ledger path pinned.** Rationale: an unhardened budget ledger under a live paced touch is the P10 failure surface the 2026-07-27 429-storm already put on record; harden the meter before energizing the line.
- **G4 — dispositions:** (i) DP-4a-READY terraform `-target=` name errors → **P13-staged correction micro-packet** (internal self-contradiction vs its own §Ratification; correctness-of-record). (ii) C8 freshness.py/entity_registry.py anchor drift is **by-design via C17 → ledger note only** (no packet; the drift is the intended C17 landing). (iii) "#292 24 CI checks" unverifiable-locally → **ledger note, low danger** (historical, non-load-bearing). Rationale: only the operator-facing lever error is load-bearing; the other two are provenance hygiene.
- **G5 — CONFIRMED as the binding window operating contract:** daily `HANDOFF-s8-parity-<date>.md`; park-per-day with preflight re-verify on resume; operator interrupts ONLY {wound, budget exhaustion, alarm anomaly incl. PROV-2 failing to clear}; EUNOMIA DORMANCY (zero eunomia agents pre-S12); doors DP-1/DP-4b HALT for operator word; P13 non-door rulings auto-ratify staged on inscription with 24h amend window + provenance disclosure. Rationale: verbatim from P5/P12/P13 [A-2026-08-03] — I affirm, I do not widen.

## (4) Inscription plan (P13 staged-auto — main thread inscribes; I hold Read only)

Every record below carries the P13 provenance line: *"Auto-ratified staged on inscription per P13 [A-2026-08-03]; 24h operator amend window; one word reverts."*

- **This ruling** → `.ledge/decisions/RULING-potnia-s8-2-wave-entry-2026-08-03.md` (verbatim). Provenance line appended.
- **G4(i) correction** → `.ledge/decisions/CORRECTION-dp4a-terraform-target-names-2026-08-03.md` — pin the four real resources (`prov2_heartbeat_absence`, `prov3_incomplete`, `prov4_expected_set_mismatch`, `prov5_expected_floor`); provenance line.
- **G4(ii) ledger note** → append to the C8/C17 record noting the by-design anchor drift; no new packet.
- **G4(iii) ledger note** → SVR/UV-P bank entry, low-danger historical.
- **Daily** → `HANDOFF-s8-parity-<date>.md`. **Arc close / any park** → `HANDOFF-s8-2-<state>-<date>.md` (predicate verbatim, ledger, PT-03/cutover/PT-04 state, DP-1/DP-4b status, SVR/UV-P deltas, exact S11+S12 ignite) + telos Gate-B writeback + `/sos wrap`.

**Cross-rite dependency to surface now:** PT-03 Q3 requires rite-disjoint **security critics (threat-modeler + penetration-tester)** for the common-mode hunt — stage a `cross-rite-handoff` (type: assessment) at WU-5, not at wave-entry. No ADR-0040 security-verdict envelope is in play at entry.

---

**throughline.rationale:** Entry is GO because every entry receipt is discharged own-hands and the gates are open; the G1-G5 findings sharpen decomposition, they do not block. The load-bearing move is separating *corridor-entry* from *window-open* — the first live touch stays gated behind WU-2+WU-3 P7 bars, honoring P10/G3. Scope discipline held on G2 (defer the terraform durable scheduler; it is operator-reserved cross-repo apply, not corridor work) and on the seam-use-vs-seam-change back-route (arming ≠ redesign). All authority calls respect P9 doors (DP-1/DP-4b HALT) and P13 auto-ratify. **NEXT:** main thread inscribes this ruling + G4(i) correction, then dispatches WU-1 (principal-engineer probe + pythia drift verdict).

**MISSION (carried verbatim):** "every business number the asana dataframe substrate serves is provably current or loudly refused — delivered by a substrate-v2 designed whole and small enough that its correctness is legible, with v1 deleted and the doctrine packaged so any autom8y-* repo can reconstruct the same guarantees as a template application, not a research project."

**PREDICATE (carried verbatim, NOT "PRs merged"):** "Verified-realized" = P5 cutover-gate receipts clean (adversarial fixture replay + bounded live-parity window, every divergence explained) AND a rite-disjoint attester re-derives active_mrr by their own hands matching live Asana within freshness-SLA across >=2 warm cycles AND v1 planes/bridges/flags enumerate to zero AND doctrine landed at fleet-constitution level.
