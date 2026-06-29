---
type: decision
subtype: ic-readiness-checklist
status: accepted
title: "IC SOAK CLOCK-START READINESS — telos-soak (dataframe-resolution-coherence five-signal)"
station: R5 (incident-commander)
date: 2026-06-10
clock_state: NOT-STARTED   # the clock is the operator's + IC's; this artifact surfaces, it does not start
soak_subject: telos dataframe-resolution-coherence — five-signal verified_realized of the CONVERGED plane
blocking_gate: AC-6 (receiver_query_outcome_total present + nonzero) — #36/R2 cross-repo monolith→receiver cutover
evidence_grade: MODERATE   # self-ref ceiling; STRONG requires the rite-disjoint attester observing the live five-signal simultaneously
inputs:
  - .know/telos/dataframe-resolution-coherence.md
  - .ledge/reviews/EUNOMIA-VERDICT-coherent-node-strong-cert-2026-06-10.md
  - .ledge/handoffs/HANDOFF-eunomia-to-sre-verdict-and-reliability-frontier-2026-06-10.md
  - .ledge/handoffs/HANDOFF-10x-dev-to-sre-substrate-convergence-cr3close-amber-2026-06-09.md
  - .ledge/spikes/SCOUT-asana-r2-r3-disposition.md
authority: IC surfaces GO/NO-GO; START is operator+IC. Irreversibles (Stage-B, Secret-2) stay ARMED-AND-STAGED.
---

# IC SOAK CLOCK-START READINESS — telos-soak

> **Grandeur anchor.** The telos-soak measures the **CONVERGED plane** — the five-signal
> verified-realized of `dataframe-resolution-coherence` — **not credential plumbing**. The prior
> CR-3 soak ran against a substrate that never carried representative load; it is **superseded and
> invalid** for this purpose. This soak validly **STARTS only when**: (1) **AC-6 lands** —
> `receiver_query_outcome_total` is present + nonzero in AMP across the monolith→receiver cutover;
> (2) the **SLI is lit** with affirmative signal (not OK-on-absence silence); (3) the **guards are
> armed** (the R3 alarm bundle applied, the must-arm subset transitioned-able to ALARM). Until all
> three hold, **the clock does not start.** This artifact surfaces everything and **starts nothing.**

> **IC discipline.** "Root cause" is a misleading construct — the soak validity rests on multiple
> contributing conditions, all of which must hold [II:SRC-001 Cook 1998] [STRONG | 0.79]. GO/NO-GO
> criteria below are **falsifiable**, never vibes [Standing Grant]. Severity is tied to quantitative
> SLO impact, not team stress [SR:SRC-001 Beyer et al. 2016] [STRONG | 0.72].

---

## §0. State inherited (live receipts exist — cited, NOT re-verified this pass)

These are the upstream receipts this checklist stands on. The IC does not re-run them; it cites them
and tests only the **soak-START gate** (AC-6) and the **must-arm guard subset** as live conditions.

- **FPC node STRONG-GRANTED** (eunomia rite-disjoint, 2026-06-10 ~14:00Z): `coherent=561 / gun=10 /
  unit.mrr=723/3021`, **three consecutive autonomous warm writes bit-identical** (13:07 heal → 13:30
  POINT-1 independent invocation `cec62d91` denials=0 → 13:46 POINT-2). Receipt:
  `.ledge/reviews/EUNOMIA-VERDICT-coherent-node-strong-cert-2026-06-10.md` §STABILITY-POINT-1/2.
  **The NODE is STRONG; the TELOS is NOT verified-realized** — the verdict itself says do not round up
  (§Telos ADVISORY, lines 63-67).
- **active_mrr HEALED + LIVE**: first-party `$79,485` / 62 rows over `dataframes/1143843662099250/offer/sections/`
  (`.know/telos/dataframe-resolution-coherence.md` Rung Ladder, 2026-06-09 REALIZATION UPDATE).
- **SLI**: heartbeat/probe-class lit in AMP (226 obs) + business-class proven; **Grafana
  `EcsServiceDenominatorAbsent` state = UNVERIFIED** (requires Grafana access).
- **AC-6 = RED**: `receiver_query_outcome_total` **ABSENT** in AMP — the monolith→receiver cutover is
  **NOT live-flowing**. Owned by **#36/R2** (cross-repo monolith). **THIS is the soak-START gate.**
- **R3 alarm bundle MERGED-NOT-APPLIED** (`autom8y#486`): burn-rate SLO + probe dead-man (AMP, arm via
  `-var asana_receiver_slo_alerts_armed=true`); floor-breach + active-offer-collapse + resolver-loop
  CW alarms (`actions_enabled=false`). Operator apply/arm commands in the `autom8y#486` PR/report.
- **Deploy chain hardened** (`autom8y#485`/`#487`, `wf#25`, `asana#122`) — merged; **NEXT deploy proves
  in anger** (not yet observed post-merge).
- **CR-3 Stage-B → Secret-2 IRREVERSIBLE**, ARMED-AND-STAGED, soak-gated, HELD
  (`HANDOFF-10x-dev-to-sre-substrate-convergence-cr3close-amber-2026-06-09.md` §N9.b/N9.c).

---

## §1. PRECONDITIONS TABLE — soak-START gate

Each precondition carries its verification command and current state. **State legend:** RED = blocking;
GREEN = satisfied with a receipt; PENDING = mechanically reachable, not yet observed; AMBER = bounded,
does-not-block-START but logged. Commands surface intent; the operator/IC executes them at clock-start.

| # | Precondition | Verification command | State | Blocks START? |
|---|---|---|---|---|
| P1 | **AC-6 lit** — `receiver_query_outcome_total` PRESENT + nonzero, sustained ≥N hours | `awscurl --service aps --region us-east-1 "$AMP_QUERY_URL/api/v1/query?query=sum(increase(receiver_query_outcome_total[1h]))"` → expect series, value>0; then `.../query_range?query=sum(rate(receiver_query_outcome_total[5m]))&start=...&end=...&step=300` over ≥N h, non-empty | **RED** | **YES — THE gate** |
| P2 | **R3 TF applied** (`autom8y#486`) — bundle live in prod, plan = intended diff | (autom8y worktree off origin/main) `terraform plan -var asana_receiver_slo_alerts_armed=true` → diff matches #486 report; `terraform apply` per #486 operator commands; `terraform state list \| grep -E 'burn_rate\|probe_dead_man\|floor_breach\|active_offer_collapse\|resolver_loop'` | **PENDING** | **YES** (must be applied) |
| P3a | **Alarms armed — MUST-arm subset** (probe dead-man + burn-rate SLO) | apply with `-var asana_receiver_slo_alerts_armed=true`; `aws cloudwatch describe-alarms --alarm-name-prefix asana-receiver --query 'MetricAlarms[].{n:AlarmName,enabled:ActionsEnabled,state:StateValue}'` → dead-man + burn-rate `ActionsEnabled=true` | **PENDING** | **YES** (these two) |
| P3b | **Alarms — MAY stay dark** (floor-breach, active-offer-collapse, resolver-loop CW: `actions_enabled=false`) | same describe-alarms; these MAY remain `ActionsEnabled=false` at START (positive-signal observability, not paging gate) | **PENDING (dark-OK)** | **NO** |
| P4 | **Heartbeat dead-man GREEN** — probe firing, transitions on absence | `aws cloudwatch describe-alarms --alarm-names asana-receiver-probe-dead-man --query 'MetricAlarms[0].StateValue'` → `OK` (probe alive); confirm `treat_missing_data=breaching` (NOT notBreaching — AMBER-1 lesson) via `...--query 'MetricAlarms[0].TreatMissingData'` | **PENDING** | **YES** |
| P5 | **Deploy-chain proven-in-anger** — one post-`#485` deploy observed clean | observe next `satellite-receiver.yml` run: `gh run list --workflow=satellite-receiver.yml -L 3 --json conclusion,headSha,createdAt`; confirm deploy job released concurrency lock (no 30-min `satellite-deploy-asana` hang) + metrics-smoke-gate passed | **PENDING** | **YES** |
| P6 | **Stability holding** — 3-warm series + the next entity-cron point | cited GREEN (3 autonomous warms bit-identical, eunomia verdict §STABILITY-POINT-1/2); the **next entity-cron** (`cron(0 */4 * * ? *)`, ~16:00Z / ~20:00Z) re-measure holds band: `coherent≥500±10%, gun≤~15, Templates≤~5, unit.mrr no re-clobber` | **GREEN (3-warm)** / **PENDING (next cron belt-and-braces)** | **NO** (3-warm discharges; cron is confirmatory) |
| P7 | **SLI affirmative** — receiver SLI/EMF emitting, scrape live (not OK-on-absence) | `awscurl --service aps "$AMP_QUERY_URL/api/v1/query?query=up{job=\"asana\"}"` → `1`; confirm `RECEIVER_SLI_EMF_ENABLED` ON (env on deployed task-def: `aws ecs describe-task-definition --task-definition autom8y-asana-service --query 'taskDefinition.containerDefinitions[0].environment'`); Grafana `EcsServiceDenominatorAbsent` state | **AMBER→PENDING** (probe-class lit; business-denominator + Grafana state unverified) | **YES** (a dark SLI cannot certify the soak — eunomia item #4) |
| P8 | **UK-2 / #114 disposition** — confirm NOT a soak blocker | `gh issue view 114 --json title,state,labels`; cross-check eunomia note (`discount:335` healing live = the drift cell surfacing) | **CONFIRMED NOT-A-BLOCKER** | **NO** |

**P8 disposition (explicit):** UK-2/#114 (dtype-parity / drift cell) is **NOT a soak blocker.** The eunomia
verdict records `discount:335` healing live (the drift cell already surfacing through the FPC node), and #114
is a parity/observability follow-up, not a five-signal serving-correctness gate. **Refuted as a blocker;
logged as a watch item**, not a clock-stop.

---

## §2. THE FIVE-SIGNAL OBSERVATION PLAN

The soak's subject is the telos five-signal verified_realized. Per signal: query/command, cadence, owner,
PASS band, and the **rite-disjoint attester** requirement. The attester (per telos-integrity-ref §2 R1
binding: **eunomia, ≠ SRE/releaser**) must observe the live five-signal **simultaneously** with the IC's
soak monitor — a same-rite self-certification is structurally refused (telos-integrity-ref §4 R1).

| Sig | Signal (telos verified_realized def) | Query / command | Cadence | Owner | PASS band | Rite-disjoint attester |
|---|---|---|---|---|---|---|
| S1 | **active_mrr denominator stable** = 62/$79,485 over ACTIVE offer subset, no collapse on entity=project warm | `metrics --entity-type offer` (auto-routes `_ACTIVE_OFFER_SCOPE`) → rows=62, $79,485; AMP: `active_offer_mrr_rows` G-DENOM-correct (SRE-N6 telos metric, once wired) | every entity-cron warm (~4h) + on-demand at each warm | IC (monitor) | rows=62 ± 0 over ACTIVE subset; $79,485 ±0; **no collapse to ~7** on any same-GID entity=project warm | eunomia re-pulls the offer frame independently each measure |
| S2 | **ad_reporting offer-entity economics** — ECS controller returns offer-entity (not project-entity $0) economics | (autom8 monolith) ad_reporting controller live read → offer-entity economics non-zero; **SEAM-2-gated** (consumers DEFERRED) | per cutover + daily | IC + autom8-owner | offer-entity economics non-zero; NOT project-entity zero-filled | eunomia confirms entity-binding = offer, not project |
| S3 | **payments/mrr matching denominator** — active unit count matches the warmed-correct 62-row denominator | (autom8 monolith) payments/mrr unit count vs S1 denominator; **SEAM-2-gated** | daily | IC + autom8-owner | unit count == S1 ACTIVE denominator (congruent, no drift) | eunomia cross-checks the two denominators are the same number |
| S4 | **population WARN absent in steady-state** — non-null rate ≥0.80 over ACTIVE subset; `population_receipt_below_floor` never fires | AMP: `population_receipt_below_floor` alarm state == OK across window; `post_build_population_receipt` non-null ≥0.80 | continuous (alarm) + per warm | observability-engineer | alarm OK entire window; non-null ≥0.80; **zero** WARN fires in steady-state | eunomia confirms the floor alarm is affirmative-signal (not OK-on-absence) |
| S5 | **rite-disjoint attester observing simultaneously** — the meta-signal | eunomia re-derives S1–S4 from origin/main + own AMP pulls **concurrently** with IC monitor; receipts pasted into a co-located VERDICT | once at clock-start + at each GO/NO-GO checkpoint | eunomia (attester) | eunomia's independent numbers == IC's numbers (bit-exact where applicable) | **this IS the attester requirement** — S5 is satisfied only by eunomia's simultaneous observation |

**S2/S3 caveat (do not round up):** S2 and S3 are **SEAM-2-gated** — the autom8 monolith consumers are
DEFERRED, not certified (`telos` DEFER manifest, `HANDOFF-eunomia-...` line 47). The receiver-side
verified_realized (S1, S4) is STRONG; **full-telos five-signal verified_realized requires SEAM-2 rebind**
and stays MODERATE / PENDING until then. The soak may run on the receiver-side plane (S1, S4, S5) and
**log S2/S3 as DEFERRED-NOT-OBSERVED** — but the **full-telos GO** in §3 is not reachable without S2/S3.

---

## §3. GO/NO-GO + SOAK DURATION + WHAT BREAKS THE SOAK

### GO criteria (ALL must hold — falsifiable)
1. **AC-6 lit** (P1 GREEN): `receiver_query_outcome_total` present + **nonzero**, sustained **≥N hours**
   where **N ≥ 6h** (one full entity-cron quarter-day cycle: covers ≥1 scheduled warm at `cron(0 */4)`).
2. **R3 TF applied** (P2) + **must-arm subset armed** (P3a: probe dead-man + burn-rate SLO `ActionsEnabled=true`).
3. **Heartbeat dead-man GREEN** with `treat_missing_data=breaching` (P4) — affirmative, not OK-on-absence.
4. **Deploy-chain proven-in-anger** (P5): one post-`#485` deploy observed clean (no 30-min lock hang).
5. **SLI affirmative** (P7): `up{job=asana}=1`, EMF on, business-denominator emitting (a dark SLI is NO-GO).
6. **Stability holding** (P6): 3-warm series discharged (cited GREEN); next entity-cron belt-and-braces logged.
7. **S5 attester armed**: eunomia confirmed available to observe S1–S4 simultaneously at clock-start.

### NO-GO if ANY of {1,2,3,4,5} is not GREEN. (6 is discharged by the cited 3-warm series; 7 is a coordination precondition.)

### Soak duration recommendation: **7 days** (matches prior CR-3 soak) — argued, not inherited
The prior CR-3 soak was 7d [PLATFORM-HEURISTIC: CR-3 convention]. The **telos-soak should also be 7d**, on
three independent grounds:
- **Warm-cadence coverage**: the entity-cron is `cron(0 */4 * * ? *)` → **6 warms/day × 7d = 42 warm cycles**.
  The soak's load-bearing question is "does the 62-row denominator survive repeated autonomous warms without
  re-clobber?" — a 7d window observes 42 independent re-clobber opportunities, vastly exceeding the N=3 that
  granted the node. A 1–2d window would under-sample the re-clobber risk.
- **Error-budget framing** [SR:SRC-001 Beyer et al. 2016] [STRONG | 0.72]: a 7d window at the receiver SLO
  gives a measurable error budget (1−SLO over 7d) against which burn-rate (P3a) can be evaluated — a shorter
  window cannot establish a credible burn-rate denominator.
- **Boundary-case discipline** [II:SRC-001 Cook 1998] [STRONG | 0.79]: complex systems run degraded as normal;
  latent re-clobber conditions need a multi-day window for multiple latent failures to *align or fail to align*.
  7d is the floor that lets a non-event be evidence.

**Recommendation: 7d minimum, completing one full week of the entity-cron cadence. Do not shorten below 7d
to "save time" — the prior CR-3 soak length is the calibrated floor for this load class.**

### What BREAKS the soak (RESETS the clock) vs merely LOGS
| Event | Verdict | Rationale |
|---|---|---|
| active_mrr denominator collapses (62 → ~7) on any warm | **RESET** | S1 PASS-band violation; the exact failure the telos exists to prevent |
| `receiver_query_outcome_total` goes absent/zero mid-window (AC-6 regresses) | **RESET** | the soak subject stops flowing; window is invalid from the gap |
| `population_receipt_below_floor` fires in steady-state (S4) | **RESET** | non-null <0.80 over ACTIVE subset = serving-correctness regression |
| burn-rate SLO ALARM (P3a) under real traffic | **RESET** | SLO breach; the soak cannot certify protecting-prod through a breach |
| SLI goes dark mid-window (`up{job=asana}≠1`, EMF stops) | **RESET** | cannot certify a window you cannot observe (eunomia item #4) |
| a deploy occurs mid-window (new task-def) | **RESET** | new substrate = new soak; the window must observe a stable artifact |
| floor/active-offer-collapse/resolver-loop CW alarm fires (dark, P3b) | **LOG** (investigate) | positive-signal observability; investigate but does not auto-reset unless it corroborates an S1/S4 break |
| next entity-cron belt-and-braces measure (P6) | **LOG** | confirmatory, not gating; the 3-warm series already discharged stability |
| UK-2/#114 drift-cell surfacing (`discount` etc.) | **LOG** | watch item, not a serving-correctness gate (§1 P8) |
| S2/S3 (SEAM-2 consumers) not yet observed | **LOG (DEFERRED)** | SEAM-2-gated; receiver-side soak proceeds, full-telos GO deferred |

**Acid test (IC):** *"If the denominator collapses again next month, does this soak window prove the heal is
durable?"* — Only a clean 7d window across ≥42 warm cycles with affirmative SLI + armed dead-man answers YES.

---

## §4. STAGE-B SEQUENCING — AFTER soak-clear (ordered, gated, IRREVERSIBLE)

These fire **ONLY** after a clean soak-clear, each on its empirical gate GREEN with a pasted receipt — never
speculatively (`HANDOFF-10x-dev-...-cr3close-amber` §Authority, line 52). The soak gate is **NOT met this
window**; these stay **ARMED-AND-STAGED**.

| Step | Action | Gate (must be GREEN + receipted) | Operator sign-off point | Reversible? |
|---|---|---|---|---|
| **B0** | Soak-clear declaration | clean 7d window, GO criteria §3 all held, **eunomia S5 attestation pasted** | **IC + operator** co-sign the soak-clear | — (gate) |
| **B1** | CR-3 **Stage-B** (RB-1 boundary) | clean-soak-complete + Platform §9.3 headroom + IC sign-off, all receipted (`§N9.b`) | **operator** explicit GO before apply | **HARD / IRREVERSIBLE** |
| **B2** | **Secret-2 decommission** (retire auth fallback, **LAST**) | PDG-2/3 + task-#73 + **monolith-not-orphaned** (credential-topology verified) + access-stopped (`§N9.c`) | **operator** explicit GO; verify monolith credential-topology FIRST | **HARD / IRREVERSIBLE** |
| **B3** | `legacy_fallback_enabled = False` flip + legacy S3 key delete | dual-read window clean, v2 keys serving, copy-forward NOT needed (live legacy frame is `entity_type:"project"` — copy REFUSED) | **operator** GO; this is a CODE change, not env | reversible-until-delete; delete is IRREVERSIBLE |

**Ordering invariant:** B1 → B2 → B3, each gated independently. **B2 is LAST among the auth irreversibles**
(retiring the fallback before the monolith credential-topology is verified-not-orphaned would orphan the
consumer). The IC does **not** let a green soak dashboard substitute for the per-step empirical gate.

---

## §5. THE SINGLE BLOCKING DEPENDENCY CHAIN

```
AC-6 (receiver_query_outcome_total present + nonzero, ≥N≥6h)
   ↑  owned by #36 / R2 — CROSS-REPO (autom8 monolith → receiver cutover)
   │  needs: the monolith's read path to route through the receiver (not the legacy SDK),
   │         so the receiver emits receiver_query_outcome_total under real consumer traffic
   │
   └─► without AC-6 lit, the soak HAS NO SUBJECT — the converged plane is not live-flowing,
       so the five-signal cannot be observed, so the clock CANNOT start.
```

**Owner:** #36 / R2 — **cross-repo, autom8 monolith team.** This is NOT inside autom8y-asana; the IC cannot
land it from this station. **What it needs:** the monolith consumer cutover that drives real query traffic
through the receiver path so `receiver_query_outcome_total` populates in AMP.

### Decision list — what the IC needs from the OPERATOR **TODAY**

1. **AC-6 ownership confirmation** — confirm **#36/R2 (autom8 monolith)** is the owner and is in-flight, OR
   route a cross-rite HANDOFF to the autom8-owner to drive the cutover. **Without this, the soak cannot start
   — full stop.** (Decision: who drives #36, and by when?)
2. **R3 bundle apply authorization** (`autom8y#486`) — authorize the `terraform apply -var
   asana_receiver_slo_alerts_armed=true` in the autom8y worktree (must-arm subset: probe dead-man + burn-rate).
   (Decision: apply now to pre-stage P2/P3a, or hold until AC-6 is imminent?)
3. **SLI lit-up confirmation** (P7) — authorize the work to flip `RECEIVER_SLI_EMF_ENABLED` (a deploy) + wire
   the business-denominator scrape + verify Grafana `EcsServiceDenominatorAbsent` state. (Decision: who has
   Grafana access to verify the denominator-absent state the IC cannot see from here?)
4. **Deploy-in-anger window** (P5) — authorize/observe one post-`#485` deploy to prove the hardened chain
   (no 30-min lock hang). (Decision: trigger a deliberate proving deploy, or wait for the next organic one?)
5. **Soak duration ratification** — ratify **7d** (or set an alternate with rationale). (Decision: 7d?)
6. **Soak-START co-sign** — the clock is the operator's + IC's. When P1–P5 + P7 are GREEN and eunomia (S5) is
   armed, **operator + IC co-sign the START**. (Decision: confirm the co-sign protocol and the START timestamp
   ownership — this artifact deliberately does NOT start it.)
7. **Irreversibles stay HELD** — confirm Stage-B / Secret-2 / fallback-flip remain ARMED-AND-STAGED until a
   clean soak-clear (§4). (Decision: acknowledge HELD; no speculative fire.)

---

## §6. CLOCK STATE — explicit

**THE CLOCK IS NOT STARTED.** This artifact surfaces every precondition, command, signal, and decision. It
**starts nothing.** The benign dirty tree is **not staged.** START is the operator's + IC's co-signed action,
reachable only when §3 GO criteria are GREEN with pasted receipts and the §5 single blocking dependency
(AC-6) is cleared.

*Authored by sre/incident-commander (station R5), 2026-06-10. Evidence grade MODERATE (self-ref ceiling);
STRONG requires the rite-disjoint attester (eunomia) observing the live five-signal simultaneously (S5).
Falsifiable GO/NO-GO held per Standing Grant — never vibes.*
