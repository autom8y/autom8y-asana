---
type: decision
status: accepted
---

# TELOS — Asana Data-Substrate Freshness Crusade (2026-07-13)

> **Status: RATIFIED 2026-07-13 — operator reply verbatim "ratified!", no amendments.
> This telos is the Grandeur Anchor of the substrate session's /goal charge.** Authored by the ASR arc as the
> intent-layer ABOVE the execution decomposition in
> `.ledge/handoffs/HANDOFF-asr-to-substrate-session-2026-07-13.md`. Self-authored; evidence
> grade capped MODERATE. Every factual claim below carries a same-day live receipt (2026-07-13)
> from the ASR reorientation rebase + glint scan; all are STALE at the fresh session's open —
> PV-pre-flight re-verify before they are load-bearing.

---

## The Prize

**The asana data substrate is fresh-by-construction and honest-when-it-is-not.** The offer and
entity frames the fleet depends on stay within their freshness contract; freshness becomes an
**owned surface** with detection at the granularity that actually starves (**per-GID**, not
per-entity-class); and any degradation **announces itself to a named owner before it silently
starves a consumer** — whether that consumer is ASR or a client-facing insights render. The
2026-07-10 asana 429 storm is the **founding ticket of that ownership**, not a one-off firefight.

## Why now — coherence with the standing telos

- **Q3 priority (consolidate > deepen > new):** this IS consolidation — paying down the substrate
  fragility (429 storm, 24h-stale frames, a dead-man that's blind to the failure it exists to
  catch) before more weight rides the machine. Hardening is the critical path to widening, not a
  competitor to it. [[q3-2026-quarterly-priority-ruling]]
- **Trust-first telos:** ASR is the fleet's **Pillar-7 instrument** (silent → loud) for the
  revenue-bearing three-axis seam, and the offer substrate is its **binding constraint (G2)**.
  Curing the substrate is what lets the trust instrument run at all. And the crusade's own prize —
  degradation announces itself — is Pillar 7 generalized onto the substrate itself.
  [[telos-ratification-trust-first-2026-07-04]]
- **Recurring-class evidence:** third eruption of one class — `CACHE_NOT_WARMED` P0 (2026-06-08) →
  warmer stall (2026-07-07) → the fleet 429 storm (2026-07-10→). A one-off cure each time has not
  held; the operator ruled it an **owned class with a standing owner + SLO** (ratified P3).

## The felt-line question (the load-bearing OPEN premise)

**Is the starved substrate client-felt, or internal-only?** This decides whether the crusade is
foundation-hardening (proceeds under the substrate telos) or a **Pillar-9 live-client fire**
(outranks nearly everything).

- **Circumstantial evidence it IS client-felt:** the insights RENDER lane
  (`automation/workflows/insights/{formatter,tables,workflow}.py`) reads offer data and, as of
  today's `#231`, discloses "offer table coverage" on a client-facing report; `#230` carries
  weights + asOf to that render. A client-facing surface that renders offer data demonstrably
  exists. `unit_holder` frames were observed ~74h stale under the same storm.
- **What is NOT proven:** whether that render reads the SAME frame-cache path the storm starves
  (offer frame project `1143843662099250`), or reaches offers by an independent path. The frame
  serve-consumers grep at origin/main surfaced the `api/*` layer, not the insights workflow —
  the coupling is unconfirmed either way.
- **Ruling posture until C1 resolves it:** treat the substrate as **potentially client-felt** —
  protect accordingly (below). If C1 proves a client render reads degraded offer data, this
  crusade re-classifies to Pillar-9 and the operator is notified immediately; a client seeing
  wrong coverage numbers is the **Pillar-5 silent-wrong-outcome**, the worst failure.

## Scope — the inaugural /sprint wave (the "entry crusades")

Decomposed in the handoff as W1–W4; as telos-level crusades:

- **C1 — Attribution (keystone, blocks all):** the dated WHO-is-consuming receipt for the shared
  Asana 1500/60s budget across the storm window (onset ≈ 2026-07-10T15:50Z; EBI-flip correlation
  is an UNVERIFIED hypothesis — attribute, don't assume). C1 also answers the felt-line question.
- **C2 — Freshness-class ownership:** the owned surface + SLO + **per-GID detection** that would
  have caught this storm (the granularity gap of SCAR-015 is the design constraint).
- **C3 — The ASR-GID cure:** restore the ASR offer frame to `< 3600s` sustained ≥2 warm cycles —
  the receipt the ASR arc resumes its canary on.
- **C4 — Warmer dead-man hygiene:** reconcile `autom8-asana-cache-warmer-DMS-24h` (ALARM since
  2026-06-04, ActionsEnabled:False, dark 5+ weeks).

**Explicitly OUT of scope** (owned elsewhere, do not scope-creep): node-4 schedule-enable
(operator + ASR arc); the ASR dry-run canary itself (ASR arc, main thread); the data-rite
`get_insight` 503 (data rite — `HANDOFF-asr-to-data-get-insight-503-2026-07-13.md`); the AMP
SLO-alert re-arm (a registered ASR-arc rung gated on (a)/(b)/(c)+soak).

## The done-bar (what makes "substrate landed" TRUE)

1. **C3 receipt:** ASR GID frame `< 3600s` sustained ≥2 cycles, dated serve-path receipts.
2. **C2 realized + PROVEN silent→loud:** a named owner, an SLO, and per-GID detection that a
   deliberately-starved GID actually trips (discriminating-canary teeth — a two-sided proof, not a
   green dashboard).
3. **C1 discharged:** dated per-consumer attribution receipt + the felt-line question answered
   (client-felt yes/no with a code-path receipt).
4. **C4 disposition:** warmer DMS re-armed / re-keyed / retired, with receipts.
5. **Rung honesty:** never rounded up — `attributed < cured < detecting < protecting-prod`.

## Priority & tolerance

- **Protect first:** client-felt render integrity. If the insights render reads degraded offer
  data, that is full-bar at ship (Pillar 4) and its detection is the non-negotiable fast-follow
  (Pillar 7).
- **Most tolerable failure:** the cure stalls, or the storm is **attributed-but-uncured this
  wave**. Stall is the most tolerable failure per telos — better to attribute-and-hold than to
  throttle blindly.
- **Intolerable:** (a) a silent GID-blind "all fresh" signal (SCAR-015 recurrence); (b)
  throttling a client-felt path to feed internal reconciliation on agent authority (→ ESCALATE,
  non-ruling #3); (c) a warmer-side patch shipped under an un-attributed fleet storm — it burns
  the wave without moving G2 (the adversary's corrected keystone).

## Ours vs handed-off

- **OURS (in-lane, this session, autom8y-asana):** warmer-side cure, freshness-class ownership +
  SLO + detection, warmer DMS hygiene. All within the four affirmed lane classes.
- **HANDED-OFF / ESCALATE:** cross-consumer Asana-budget arbitration **if** C1 attributes the
  storm to another initiative (e.g. EBI) — no cross-consumer allocator exists today (ADR-ASANA-003
  is per-client AIMD only); route to that owner, do not throttle unilaterally. The `get_insight`
  503 → data rite. node-4 → operator. Cross-session collision → ESCALATE (non-ruling #2).

## Inherited law (binds this crusade per R5 portability — no re-interview)

The ratified operator ledger travels intact:
`services/account-status-recon/.ledge/{decisions,shelf}/RULINGS-asr-operator-interview-2026-07-13.md`
(monorepo). Operative: the **four in-lane classes** (canary env-mutations, non-paging alarm
hygiene, artifact landings to origin/main, scoped-fix merge+deploy on green — receipts + ledger
mandatory); the **carve-outs** (anything that pages a human / new paging wiring, secrets, spend,
data deletion, client-visible risk, node-4 = confirm-first); the **two open non-rulings** (both
resolve to ESCALATE, never infer).

## Ratification

**RATIFIED 2026-07-13** — operator reply verbatim: "ratified!". No crusade or bound amended.
The `/goal` charge launching the fresh-session 10x-dev pantheon was issued same-turn.
