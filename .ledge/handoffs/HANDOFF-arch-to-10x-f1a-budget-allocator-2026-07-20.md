---
type: handoff
artifact_id: HANDOFF-arch-to-10x-f1a-budget-allocator-2026-07-20
status: proposed
handoff_type: implementation (arch → 10x-dev, autom8y-asana)
procession_id: f1a-budget-allocator
source_rite: arch
source_station: arch (Phases 3–4)
target_rite: 10x-dev
target_station: 10x-dev (Phases 5–7, co-seat — already holds the substrate /goal charge)
initiative: F1a — asana cross-consumer rate-limit budget allocator (offer-substrate freshness cure)
telos: TELOS-asana-substrate-freshness-2026-07-13 (ratified)
charter: CHARTER-f1a-budget-allocator-2026-07-20 (verbatim-execute; DAG nodes 5–7 here)
date: 2026-07-20
adversary_gate: ADVERSARY-REPORT-f1a-1.md — PASS-WITH-CONDITIONS (6 conditions, ZERO blocking); shift-starvation DEFEATED → node-5 build UNBLOCKED
option_slate: ADJUDICATION-option-slate.md — pythia ruled ADVISORY published-floor + 5 HARD conditions (PC-1..PC-5)
grant: autonomous THROUGH live-leg-proven/INERT; node-5 BUILD is default-off behind kill-switch; GO-LIVE (node 8) OPERATOR-ONLY
max_rung_target: MERGED-INERT (5) → CANARY-PROVEN (6) → LIVE-LEG-PROVEN (7); GO-LIVE never in this grant
---

# HANDOFF-2 — arch → 10x-dev (autom8y-asana): F1a budget allocator — BUILD to PR/INERT

- **handoff_type**: implementation (arch → 10x-dev, autom8y-asana rite)
- **Date**: 2026-07-20
- **Fresh root (re-derive nothing; build here)**: `origin/main @ edaa9ddd or later` in an **isolated worktree**. **Local main is STALE at `f3d8eec1` — NEVER build on it.** `git fetch origin && git worktree add` off `edaa9ddd`+ before any edit.
- **Design authority**: `.sos/wip/thermia/f1a/architecture-assessment.md` (the adjudicated design) + `.sos/wip/thermia/f1a/killswitch-rollback-spec.md` (3d kill-switch/rollback) + `.sos/wip/thermia/f1a/ADJUDICATION-option-slate.md` (pythia ADVISORY published-floor + PC-1..PC-5) + `.sos/wip/thermia/f1a/ADVERSARY-REPORT-f1a-1.md` (6 conditions AC-1..AC-6 — **the AC source of truth**).
- **Upstream receipts (measured, adjudicated)**: `.ledge/handoffs/HANDOFF-thermia-to-arch-f1a-budget-allocator-2026-07-20.md` (C1 = ECS 100% of 429s; felt-line Branch B CLEAN; MALDISTRIBUTED both axes; floor = 110/60s from 3,291÷30min; ECS yields 142/min worst-minute = 1.54% of 3h).
- **Telos frame**: the offer substrate must be fresh-by-construction and honest-when-not; the storm needs partitioning, not a faster warmer. Every failure direction of this design is **fail-open** (a lane proceeds un-arbitrated), never a hard-block that makes the storm worse.
- **Evidence grade**: MODERATE (self-referential cap). External lifts: qa-adversary node-6 canary + node-7 live-leg.
- **Predictions discipline**: all TL-A predictions below are **BUILD-GATES — falsifiable at build/test time**, not horizon predictions. Each one, if falsified, HALTS its ITEM and returns to arch.
- **Receipt-grammar note (telos-integrity Gate C)**: attestation tokens below anchor to arch VERDICT/receipt artifacts in `.sos/wip/thermia/f1a/` (disjunct (b)) or to verified `{path}:{line}` from the fresh root; forward BUILD-GATE predictions are falsifiable claims, not attestations. Un-anchorable conditions carry an explicit `[DEFER-…]` tag; the verbatim text of PC-1..PC-5 and AC-1..AC-6 lives in the two named adjudication artifacts and MUST be transcribed into the ITEM ACs by principal-engineer.

## §1. ADJUDICATED DESIGN SUMMARY (build to THIS)

pythia re-adjudicated the node-3d option-slate and ruled **ADVISORY published-floor** (anchor: `.sos/wip/thermia/f1a/ADJUDICATION-option-slate.md`) — NOT an in-path arbiter. This is the load-bearing decision: it **defeats C-10 (SPOF/single-writer)** because an advisory limiter is never in the request path, so its failure fails **open** to today's un-arbitrated behavior, not to total starvation. The design:

1. **Unified in-process singleton limiter** — ONE limiter instance per process reconciles the existing per-client AIMD (`adaptive_semaphore.py`) with the new budget floor. No second limiter; no per-lane instances.
2. **Advisory published-floor** — the limiter publishes a floor; consumers consult it advisorily. It bounds-and-telemeters overage; it does not hard-block.
3. **Config-published STATIC floor = 110/60s, C-11-DECOUPLED** — the floor ships as a static config value (`110/60s`, derived 3,291÷30min per capacity-specification.md). C-11's dynamic instrumentation is **decoupled to a RED-arm canary test** (ITEM-F), NOT a runtime prerequisite. The MVP floor is static.
4. **Per-lane fail-open (3d Axis-B)** — each consumer lane fails open independently; a limiter fault on one lane never blocks it and never cross-contaminates other lanes (anchor: `.sos/wip/thermia/f1a/killswitch-rollback-spec.md`).
5. **One knob: `ASANA_BUDGET_ALLOCATOR_ENABLED`, default FALSE** — the allocator merges **INERT** (node 5). The operator flips it at GO-LIVE (node 8, out of this grant).

**Node-4 adversary result:** PASS-WITH-CONDITIONS, ZERO blocking — shift-starvation DEFEATED (anchor: `.sos/wip/thermia/f1a/ADVERSARY-REPORT-f1a-1.md`). The 6 conditions (AC-1..AC-6) are folded into the ITEM ACs below; the report's **§strongest-surviving-attack** appears as the TL-C of the reconciliation item (ITEM-A).

## §2. REALIZATION RUNGS (name in every receipt; never round up)

`BUILT` → `MERGED-INERT` (node 5, green CI, ENABLED=false) → `CANARY-PROVEN` (node 6, 2-sided suite green incl. archived RED-before) → `LIVE-LEG-PROVEN` (node 7, qa-adversary vs live Asana) → **`[OPERATOR GO-LIVE]`** (node 8, HALT — grant stops) → `WATCHED-LIVE` (node 9). Telos ladder: `attributed < cured < detecting < protecting-prod` — current: `attributed` + `detecting`; this build advances toward `cured` but does not reach it (a cure is CANARY+LIVE-LEG+WATCHED, past the operator gate).

---

## ITEM-A (FLAGSHIP · RECONCILIATION ITEM): unified in-process singleton advisory limiter + static published floor + ENABLED knob

**Scope**: the allocator core — a process-singleton limiter unifying `adaptive_semaphore.py` (AIMD) with the static budget floor; advisory published-floor; `ASANA_BUDGET_ALLOCATOR_ENABLED` (default false); INERT at merge.

**Acceptance criteria**:
1. A single process-singleton limiter (identity-stable across lanes); constructed once at the client singleton seam.
2. Publishes a **static floor = 110/60s** from config, readable WITHOUT invoking any C-11 dynamic instrumentation (C-11-decoupled per §1.3).
3. Advisory semantics: consumers consult the floor; overage is telemetered (a structured `budget_floor_overage` metric), NOT hard-blocked.
4. `ASANA_BUDGET_ALLOCATOR_ENABLED` default false ⇒ limiter is a no-op passthrough (fail-open); explicit true ⇒ advisory-active.
5. Reconciles with the existing AIMD: the static floor OVERRIDES AIMD self-suppression for the floored lane (the warmer lane cannot be AIMD-suppressed below 110/60s).
6. **Fold pythia PC-1..PC-5 verbatim** from `ADJUDICATION-option-slate.md` and **adversary AC-1..AC-6 verbatim** from `ADVERSARY-REPORT-f1a-1.md` into these ACs (principal-engineer transcribes; do not paraphrase the HARD conditions).
7. INERT at merge: no activation, no unpin, in the build PR.

**Design references**: architecture-assessment.md (unified singleton); ADJUDICATION-option-slate.md (advisory published-floor, PC-1..PC-5).

**TL-A falsifiable prediction (BUILD-GATE)**: with the limiter constructed as a process singleton and `ENABLED=true` in test, two lanes concurrently requesting budget observe ONE instance (`id(limiter_a) == id(limiter_b)`); the 110/60s floor reads from config with ZERO calls into C-11 instrumentation; with `ENABLED=false` the limiter is byte-for-byte a passthrough. If the limiter is per-lane (not singleton), or the floor-read triggers dynamic instrumentation, or the AIMD can still drive the floored lane below 110/60s, the design premise is falsified — HALT and return to arch.

**TL-B SRC citations (verify on fresh root `edaa9ddd`+)**: client.py singleton seam (client.py:121 default `AsanaConfig()`, :140-143 provider construction — verified on sibling-substrate fresh root `5b5c249a` per `.ledge/reviews/HANDOFF-arch-to-10xdev-sibling-substrate-2026-07-08.md`; exact limiter-attach line per architecture-assessment.md); `adaptive_semaphore.py` AIMD limiter (anchor per architecture-assessment.md; the ADR-ASANA-003 per-client AIMD is the reconciliation counterpart per TELOS-asana-substrate-freshness-2026-07-13:110); config precedent config.py:855 (`field(default_factory=…)`), from_env :781-816 (fresh-construction), documented knobs :651-652 — verified on sibling-substrate fresh root.

**TL-C adversarial disposition (carries §strongest-surviving-attack)**: transcribe `ADVERSARY-REPORT-f1a-1.md` §strongest-surviving-attack VERBATIM here. Design-consistent framing: an advisory limiter cannot HARD-prevent an **ephemeral-bypass cap-leak** — a consumer that constructs its own transport outside the singleton leaks past the floor. This is BOUNDED-and-telemetered, NOT eliminated; canary-pair (a) is its teeth and the residual is `[DEFER-WATCH-CAP-LEAK]`. The unified-singleton-vs-AIMD reconciliation is load-bearing: any "just add a second limiter" review suggestion is REJECTED — it re-introduces the non-unified drift the design exists to close.

---

## ITEM-B: client singleton-seam wiring + per-lane fail-open across the ~55–57 site census

**Scope**: route the ~55–57 Asana call-sites through the singleton limiter's advisory check; per-lane fail-open (3d Axis-B).

**Acceptance criteria**:
1. All ~55–57 call-sites (enumerated in `topology-inventory.md`) consult the singleton limiter; census grep-assertion covers every site outside test fixtures.
2. Per-lane fail-open: a limiter-internal exception on one lane leaves that lane PROCEEDING; other lanes unaffected; never fail-closed.
3. Structured `budget_lane_failopen` metric emitted on any fail-open (the tripwire).

**Design references**: topology-inventory.md (the census); killswitch-rollback-spec.md (3d Axis-B fail-open).

**TL-A falsifiable prediction (BUILD-GATE)**: a census grep proves ZERO un-routed Asana call-sites outside fixtures; injecting a limiter exception on one lane leaves it proceeding while siblings are unaffected. If any site bypasses the limiter, or a limiter fault blocks a lane (fail-closed) instead of failing open, HALT — fail-closed would make the allocator WORSE than today (the exact shift-starvation the node-4 gate defeated).

**TL-B SRC citations**: the ~55–57 site census scope enumerated in topology-inventory.md; client.py request path (client.py:121/:140-143 seam).

**TL-C adversarial disposition**: expect qa to grep for un-routed sites — the census is the control (grep-assert zero). Fail-open is DELIBERATE and load-bearing: the opposite failure (fail-closed) is the "shift starvation" direction; any review suggestion to "block on limiter uncertainty for safety" is REJECTED.

---

## ITEM-C: warmer floor-admission (hierarchy_warmer) — the 110/60s claim + ≤1800s sweep gate

**Scope**: the warmer lane claims its static 110/60s floor and completes its gap-sweep under it; AIMD-override proven.

**Acceptance criteria**:
1. The warmer lane admits at 110/60s when `ENABLED=true`, queue-position-independent (the offer key at position 17–18 of 68 is served despite sitting past the 16-key budget — per capacity-specification.md).
2. **Adversary AC-3 (verbatim from ADVERSARY-REPORT-f1a-1.md)**: floor-admission completes a full **3,291-GET sweep in ≤1800s (30 min)** at the 110/60s grant.
3. Static floor OVERRIDES AIMD self-suppression: under simulated storm/AIMD pressure the floored warmer holds 110/60s (does not oscillate to ~0 as observed 2026-07-14).

**Design references**: architecture-assessment.md (floor-admission); capacity-specification.md (110/60s = 3,291÷30min; position 17–18/68); ADVERSARY-REPORT-f1a-1.md AC-3.

**TL-A falsifiable prediction (BUILD-GATE)**: floor-admission drives a full 3,291-GET sweep in ≤1800s at 110/60s; if the sweep exceeds 1800s, the 110 floor is UNDER-DERIVED → re-derive (HALT to capacity re-sizing, do NOT fudge the number). AND under simulated AIMD self-suppression the floored lane holds 110/60s; if AIMD still suppresses it to ~0, the reconciliation is falsified — HALT.

**TL-B SRC citations**: hierarchy_warmer floor path (anchor per topology-inventory.md / architecture-assessment.md); hierarchy_warmer.py:246 already threads `opt_fields=_HIERARCHY_OPT_FIELDS` via `unified_store.put_async` (the warmer's existing honest-write path — verified on sibling-substrate fresh root); the 3,291 gap-set + 30-min window in capacity-specification.md.

**TL-C adversarial disposition**: expect qa to attack the 1800s bound (AC-3) — an un-meetable sweep means the floor is under-sized and MUST be re-derived, not accepted with a fudge. The AIMD-override is load-bearing: the static floor must WIN over AIMD self-suppression, else the 2026-07-14 oscillation-to-~0 recurs and the cure is theatrical.

---

## ITEM-D: kill-switch build-gate — `ASANA_BUDGET_ALLOCATOR_ENABLED=false` byte-identical (ITEM-D-style)

**Scope**: the default-off kill-switch; ENABLED=false ⇒ byte-identical to the pre-allocator path.

**Acceptance criteria**:
1. Regression test: `ASANA_BUDGET_ALLOCATOR_ENABLED=false` ⇒ the request path is byte-identical to origin/main pre-allocator (no limiter interposition at the seam).
2. Unset env ⇒ default false (INERT); explicit true ⇒ advisory-active; precedence tested both ways.
3. CI env asserted clean of `ASANA_BUDGET_ALLOCATOR_*`; changelog callout of the knob.
4. Rollback = flip ENABLED=false OR symmetric revert (no schema migration; config-only).

**Design references**: killswitch-rollback-spec.md; ADR fork precedent (F-2 bind pattern, sibling-substrate ITEM-D).

**TL-A falsifiable prediction (BUILD-GATE)**: on origin/main (`edaa9ddd`+), `ENABLED=false` then default client construction yields a request path byte-identical to pre-allocator (no interposition); `ENABLED=true` interposes the advisory check. If `ENABLED=false` leaves ANY allocator interposition in the hot path, the kill-switch is unreliable — HALT (this is the ITEM-D lesson from the sibling-substrate F-2 dead-knob).

**TL-B SRC citations**: config.py:855 (`field(default_factory=…)`), from_env :781-816 — the exact ITEM-D precedent, verified on sibling-substrate fresh root; NullCacheProvider passthrough `_defaults/cache.py:25` (set-op no-op :60) — the "disabled ⇒ no-op" pattern.

**TL-C adversarial disposition**: the tempting shortcut is interposing the limiter unconditionally and branching on a flag deep in the path — REFUSED. `ENABLED=false` must be byte-identical AT THE SEAM (no interposition), so the kill-switch is a true revert, not a runtime branch that can drift.

---

## ITEM-E: AL-5 sparsity-fix Terraform codification — INDEPENDENTLY-REVERTIBLE commit (DEFER-BUILD-TF-AL5)

**Scope**: codify the node-0 AL-5 alarm reconfig (already teeth-proven 2-sided per `.sos/wip/thermia/f1a/EXECUTION-RECEIPT-al5-reconfig.md`) as Terraform, in a SEPARATE commit.

**Acceptance criteria**:
1. The AL-5 sparsity reconfig (Period/EvaluationPeriods/M-of-N per the node-0 receipt) lands as an **independently-revertible Terraform commit** — reverting it alone restores the prior alarm config, touching nothing else.
2. `terraform plan` shows ONLY the AL-5 alarm delta; zero collateral resource drift.
3. Carry the **SNS gap** surfaced at node-0 as `[DEFER-WATCH-SNS]` (alarm fires but SNS may not deliver — watch owner thermal-monitor at node 9).

**Design references**: EXECUTION-RECEIPT-al5-reconfig.md (the alarm delta + SNS gap).

**TL-A falsifiable prediction (BUILD-GATE)**: `terraform plan` on the AL-5 commit shows exactly the alarm delta and nothing else; reverting that one commit restores the prior config byte-identical. If the TF change couples to other resources, split it until it doesn't — HALT.

**TL-B SRC citations**: node-0 receipt `.sos/wip/thermia/f1a/EXECUTION-RECEIPT-al5-reconfig.md` (reconfig spec; SNS gap; 2-sided teeth already proven).

**TL-C adversarial disposition**: the trap is folding AL-5 TF into the allocator PR — REFUSED. It must be independently-revertible so AL-5 detection (rung `detecting`) can land or roll back without touching the allocator; AL-5 GREEN gates node-6 canary but is orthogonal to the allocator's own merge.

---

## ITEM-F: 2-sided canary suite + C-11 RED-arm (feeds node-6 CANARY-PROVEN)

**Scope**: the discriminating-canary suite proving the allocator reprioritizes correctly and reproducing the pre-fix starvation RED-before; the C-11 RED-arm.

**Acceptance criteria**:
1. Both node-6 canary pairs land with ARCHIVED RED-before + GREEN-after (see § Node-6 spec).
2. **C-11 RED-arm reproduces production suppression**: on the pre-floor path the offer key (position 17–18 of 68) is suppressed past the 16-key budget (RED); on the floored path it is claimable at 110/60s (GREEN).
3. RED-before is CURRENT unguarded behavior failing a NEW test — NOT an injected defect (discriminating-canary doctrine).

**Design references**: capacity-specification.md (position 17–18/68; 16-key budget); ADVERSARY-REPORT-f1a-1.md (AC-1..AC-6, §strongest-surviving-attack).

**TL-A falsifiable prediction (BUILD-GATE)**: the C-11 RED-arm reproduces suppression on pre-floor and GREEN on floored; both canary pairs archive a genuine RED-before. If any RED-before is an injected defect rather than current unguarded behavior failing a new test, the discriminating-canary doctrine is violated (G-THEATER) — HALT.

**TL-B SRC citations**: capacity-specification.md (suppression arithmetic); ADVERSARY-REPORT-f1a-1.md (conditions + strongest-surviving-attack).

**TL-C adversarial disposition**: the killer failure is a RED-before that is an injected defect — the RED-before MUST be current unguarded behavior failing a new test (discriminating-canary mode 2: genuine production gap under an architect ruling). No prod defect-injection anywhere in the suite.

---

## §3. NODE-6 CANARY SPEC (2-sided; CANARY-PROVEN gate — needs AL-5 GREEN + ITEM-A..F)

**Pair (a) — ephemeral-bypass cap-leak** (bounds the §strongest-surviving-attack):
- RED-before: current unguarded behavior — an ephemeral consumer (transport constructed outside the singleton) leaks past the budget, silent and unbounded.
- GREEN-after: the advisory limiter detects and telemeters the leak; overage is bounded + `budget_floor_overage` fires. (Advisory cannot hard-block; GREEN = bounded-and-loud, not zero-leak.)

**Pair (b) — warmer self-suppression re-arm**:
- RED-before: under storm/AIMD pressure the warmer self-suppresses to ~0 (the observed 2026-07-14 oscillation → 0 warm events).
- GREEN-after: with the static published floor, the warmer proceeds at **110/60s** while AIMD suppresses everyone else — the static-floor-overrides-AIMD reconciliation, proven.

**Plus**:
- **Rollback rehearsal**: flip `ASANA_BUDGET_ALLOCATOR_ENABLED=false` mid-canary; assert byte-identical revert to un-arbitrated behavior (ITEM-D).
- **Discriminating-canary doctrine**: every RED-before = current unguarded behavior failing a NEW test; NO prod defect-injection; teeth arm + ping-pong bound where applicable.

## §4. NODE-7 LIVE-LEG SPEC (LAST autonomous rung; F-b)

qa-adversary runs the allocator against LIVE Asana, **read-only OR bounded strictly inside the allocator's OWN protected 110/60s quota** — proving the advisory limiter behaves on the real 1500/60s budget (floor claimable, fail-open intact, ECS 1.54% yield real). **F-b: NO fault-injection or load-probe into a producer in a 429 storm; own-quota-bounded only.** On green → LIVE-LEG-PROVEN, then HALT + surface to operator (node 8).

## §5. FENCES (restated — bind the build)

- **F-a — GO-LIVE is OPERATOR-ONLY.** NEVER activate, unpin, or set `ASANA_BUDGET_ALLOCATOR_ENABLED=true` in the build PR or any autonomous leg. The grant STOPS at LIVE-LEG-PROVEN/INERT (node 7) and surfaces.
- **F-b — no budget-consuming experiment.** node-6 canary is discriminating (no prod defect-injection); node-7 live-leg is read-only / own-quota-bounded. No load-probe into ECS or the warmer under storm.

## §6. BUILD ROOT (mandatory)

Build in an **isolated worktree off `origin/main @ edaa9ddd` or later**. **Local main is STALE at `f3d8eec1`.** `git fetch origin` then `git worktree add {path} edaa9ddd`+ before any edit; re-verify every TL-B anchor on THIS root (line numbers may have moved from the sibling-substrate `5b5c249a` root).

## §7. RESUME ANCHOR

- **Node**: HANDOFF-2 authored → next = node 5 (principal-engineer BUILD to MERGED-INERT) → node 6 (CANARY-PROVEN, principal-engineer + qa-adversary; needs AL-5 GREEN) → node 7 (LIVE-LEG-PROVEN, qa-adversary) → **HALT node 8 (operator GO-LIVE)**.
- **Last HANDOFF artifact**: `.ledge/handoffs/HANDOFF-arch-to-10x-f1a-budget-allocator-2026-07-20.md`
- **Rung reached**: `attributed` + `detecting`; allocator design adjudicated + adversary-passed → BUILD-READY (pre-BUILT).

## §8. DEFER-WATCH REGISTRY (carried forward + new)

| ID | Item | Watch-trigger | Escalation / owner |
|---|---|---|---|
| DEFER-WATCH-FELT-ADJ | `/section-timelines` client-felt-ADJACENT (HANDOFF-1 §2) | node-6/7 shows allocator touches `/section-timelines` | F-c → operator; re-rank |
| DEFER-BUILD-C11 | claimable-floor → C-11 RED-arm (decoupled from runtime; ITEM-F) | RED-arm fails to reproduce suppression | re-derive floor / arch |
| DEFER-BUILD-TF-AL5 | AL-5 TF as independently-revertible commit (ITEM-E) | `terraform plan` shows collateral drift | split commit / 10x-dev |
| DEFER-WATCH-CAP-LEAK | ephemeral-bypass cap-leak (advisory residual; ITEM-A TL-C) | `budget_floor_overage` shows a hot recurring bypass | thread through singleton / 10x-dev |
| DEFER-WATCH-SNS | SNS delivery gap at AL-5 (ITEM-E) | AL-5 fires but SNS does not deliver | thermal-monitor / node 9 |
| DEFER-OP-ESCALATION ×3 | 3 operator escalations (capacity-specification.md) | any client-felt trade-off adjudication | OPERATOR (F1a mandate) |
| DEFER-CONSTRAINTS | pythia PC-1..PC-5 + adversary AC-1..AC-6 (verbatim in the two adjudication artifacts) | any ITEM AC drift from the verbatim condition | principal-engineer transcribes verbatim; arch on drift |

---

*Authored by potnia (single throughline, thermia→arch→10x seam) per CHARTER-f1a-budget-allocator-2026-07-20 HANDOFF-2 contract. arch Phases 3–4 COMPLETE; adversary shift-starvation DEFEATED (ADVERSARY-REPORT-f1a-1.md, PASS-WITH-CONDITIONS, zero blocking). Build default-off behind kill-switch; grant autonomous through node 7; GO-LIVE (node 8) operator-only.*
