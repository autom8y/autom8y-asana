---
type: handoff
artifact_type: HANDOFF
from_rite: 10x-dev
to: next-session (resume S1 Phase-2 arch-adversary onward)
initiative: substrate-v2-epoch
wave: WAVE-1 (S1 whole-design)
date: 2026-07-28
status: final
park_state: "RESUMED 2026-07-29 → CLOSED — S1 EXITED at PT-01 PASS; DP-2/DP-3 RATIFIED-BY-OPERATOR 2026-07-29 (NO open halts)"
resume_point: "wave-2 ignition — .ledge/handoffs/STAGED-wave2-dispatch-specs-2026-07-29.md; ALL doors ratified: S2/S3/S6/S7/S9 ignite on operator go; S4/S5 after {S2, S3}"
session: session-20260728-004509-215f7769
sprint: sprint-20260728-substrate-v2-wave1
charter: .ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md
telos: .know/telos/substrate-v2-epoch.md (RATIFIED — NOT mutated this session; see §15)
---

# HANDOFF — Substrate-v2 Epoch · WAVE-1 (S1 whole-design) · PARKED 2026-07-28

## 0. Why this is a PARK, not a wrap

The arch-adversary subagent (S1 Phase-2, rite-disjoint critique) terminated on a hard
external error: **"You've hit your monthly spend limit"** (Fable 5). Every subsequent
subagent dispatch will fail identically until the operator resolves it
(`/usage-credits`, top up, or switch model). The adversarial critique is a HARD gate
requirement (P8: door packets carry adversary dissent; PT-01·Q2: dissent recorded) — it
cannot be skipped, nor performed by the orchestrator (not rite-disjoint;
critic-substitution-rule requires a genuinely disjoint critic). WAVE-1 therefore parks.
**The next session ignites S1 Phase-2 from this document alone** (§11 is the resume
sequence).

**Operator action required to unblock:** resolve the spend limit, then run `/go` (or
`/sos start --initiative=substrate-v2-epoch`) and follow §11.

## 1. Mission + Realization Predicate (operator verbatim — carry into every artifact)

**MISSION:** "every business number the asana dataframe substrate serves is provably
current or loudly refused — delivered by a substrate-v2 designed whole and small enough
that its correctness is legible, with v1 deleted and the doctrine packaged so any
autom8y-* repo can reconstruct the same guarantees as a template application, not a
research project."

**PREDICATE (exit-anchor of EVERY sprint — NOT "PRs merged"):** "Verified-realized" =
P5 cutover-gate receipts clean (adversarial fixture replay + bounded live-parity window,
every divergence explained) AND a rite-disjoint attester re-derives active_mrr by their
own hands matching live Asana within freshness-SLA across >=2 warm cycles AND v1
planes/bridges/flags enumerate to zero AND doctrine landed at fleet-constitution level.

## 2. WAVE-1 progress ledger

| Stage | Status | Evidence |
|-------|--------|----------|
| Preflight (rite/roster/artifacts/telos/session) | ✅ COMPLETE | §5 |
| Tracked session + sprint | ✅ COMPLETE | session …215f7769, sprint …substrate-v2-wave1 (moirai) |
| Inaugural SVR fan-out (5 lanes, sonnet Explore) | ✅ COMPLETE — GATE PASS | §6 (0 falsifications, 18 HOLDS, 5 DRIFTED, 1 PARTIAL) |
| Meta-consult (potnia + pythia) | ✅ COMPLETE | §7 |
| Finding-#1 deciding fact | ✅ RESOLVED | §8 |
| S1 Phase-1 (architect ∥ requirements-analyst) | ✅ COMPLETE | §9 — 3 artifacts landed |
| S1 Phase-2 principal-engineer (feasibility + seams) | ✅ COMPLETE | §10 — BUILDABLE-AS-DRAWN |
| S1 Phase-2 arch-adversary (rite-disjoint critique) | ✅ COMPLETE 2026-07-29 (FRESH dispatch) — **PASS-WITH-CONDITIONS**: C1-C7 must-fix, C8-C11 carry, AV-1/AV-2/AV-3 constructions | §17; `.ledge/reviews/ADVERSARY-substrate-v2-design-s1.md` |
| S1 Phase-3 (finalize TDD + packets w/ dissent) | ✅ COMPLETE — all 12 items ACCEPT (zero rebuttals); seams FROZEN v1.0-frozen-2026-07-29; 3 packets authored | §17 |
| PT-01 hard gate | ✅ **PASS 2026-07-29** — S1 EXITED (LEG-0 certified); TDD `ratified` for the corridor | §17 |
| Wave-2 staging | ✅ STAGED (not fired) | `.ledge/handoffs/STAGED-wave2-dispatch-specs-2026-07-29.md` |
| Handoff + telos writeback + wrap | ✅ CLOSED 2026-07-29 — telos Gate-B S1 rows written (supersedes the §15 deferral); moirai tracker+wrap executed | §17 |

## 3. Preflight receipts (all GREEN)

- `ari rite current` == **10x-dev**; arch/thermia/security co-seats already LIVE (no `ari rite invoke` needed).
- Roster: 18/18 repo-local agents present. **Labeled note (not a blocker):** `pythia` is a global agent type, not a repo-local `.claude/agents/` file — invocable.
- Founding artifacts readable; telos `status: RATIFIED` (Gate A CLOSED).
- L2 SVR: `gh pr view 276` → **MERGED**, mergeCommit **bdbf86cb**, 2026-07-27T16:00:18Z; `bdbf86cb` is ancestor of HEAD (`b9438e83`). HEAD delta vs bdbf86cb is doc-only (no src/ change) → code state == #276.

## 4. (reserved)

## 5. — see §3.

## 6. Inaugural SVR gate — PASS (0 falsifications)

24 items across 5 sonnet-Explore lanes: **18 HOLDS · 5 DRIFTED · 1 PARTIAL · 0 FALSIFIED.**
All DRIFTs are line-anchor drift (substance intact) or a partial-fix refinement; no
load-bearing premise collapsed. **8 material design-relevant findings** (verbatim into
S1 design):

1. **HALF-GUARDED SERVING (headline).** The P2 refuse-loud `PlaneDivergenceError` guard
   protects ONLY the offline/CLI path (`dataframes/offline.py`). The live-service + MCP
   `query_rows`/`query_aggregate` path (`api/routes/query.py` → `DataFrameCache`),
   `from_s3_resolved`, and the force-warm recheck are ALL unguarded. P2 is
   half-implemented at the v1 floor.
2. **F1/F3 layout split LIVE + unremediated.** Consolidated `{entity}/dataframe.parquet`
   vs per-section `{entity}/sections/*` are two independent write paths; the reader
   trusts only per-section. This is the exact defect #276 shipped AROUND (P7 unification
   operator-deferred). The F1 door evidence.
3. **D8 null-watermark residual survives but is now bounded/self-healing** (#276 P3 heal
   already shipped). v2 F2 brief = "retire the class via content-derived truth," NOT
   "add a heal."
4. **RC-E mid-fetch-persist hazard confirmed unremediated** (`progressive.py` writes
   sections mid-fetch, reached from full builder AND warm strategy). S4 target real.
5. **DMS-24h dead-man is a PARENT-repo terraform resource**
   (`autom8y/terraform/services/asana/main.tf:845`), not a local orphan → Door #4/DP-4b
   is genuinely cross-repo (corroborates DEFECT; reconciles the one cross-lane tension —
   Lane 3 saw only this-repo's runbook doc-ref + successor AL-5). Genuine
   plane-divergence alarm still UNBUILT.
6. **UV-P-3 refined (not discharged):** real substrate surfaces in `autom8y` (parent —
   incl. a pre-existing **`autom8y-cache` reusable-kit SDK** at
   `autom8y/sdks/python/autom8y-cache`), `autom8y-data`, `autom8y-ads`; ABSENT in
   scheduling/sms/hermes/api-schemas/tokens/frontends. S10 kit should COMPOSE with the
   existing SDK, not reinvent.
7. **UV-P-4 drifted:** charter's literal `.a8/knossos` is FALSIFIED (never exists
   nested). See §7 (pythia) for the resolved landing model.
8. **Hygiene (non-blocking):** ADR line-anchors drifted 39–473 lines across
   `progressive.py`/`storage.py` — RE-ANCHOR FRESH, never cite ADR line numbers; scar
   marker count is **45 not 46** (17 files correct; gap = a module-level `pytestmark` in
   `test_register_drift_guard.py`); `.know/feat/dataframe-layer.md` + `business-metrics.md`
   are STALE (generated 2026-05-08, expired) — a `/know` refresh is warranted (P6-honesty),
   not a wave-1 blocker.

## 7. Meta-consult rulings (integrated)

### Potnia (orchestration) — S1 DAG CONFIRMED + 3 refinements
- Phase-1 `{architect (lead) ∥ requirements-analyst}` → **single** whole-slate handoff
  (forks interact; do NOT dispatch fork-by-fork) → Phase-2 `{arch-adversary ∥
  principal-engineer}` (PE-infeasibility is a co-equal bounded re-enter trigger) →
  Phase-3 architect finalizes → **PT-01 hard gate**.
- **PT-01 = 5 structural YES/NO checks:** (1) each RC-A..F impossible-by-construction OR
  fail-loud IN the TDD; (2) F1-F6 each an enumerated slate + arch-adversary dissent
  recorded; (3) design is a legible whole; (4) 5 seams frozen as interfaces; (5)
  **[finding-#1 sub-check]** F5/RC-C enumerates ALL consumer paths (offline/CLI + live
  + MCP + from_s3_resolved + force-warm) so plane-blind serving is unconstructable.
- DP-2 + DP-3 authored compact + dissent-attached + HALT-pending-operator; **decoupled
  from S1 exit** (S1 exits at PT-01 regardless of operator door latency; doors gate
  wave-2 only).
- Finding routing: #1 = S1 design-obligation + S5 build, NOT v1-patch (P6-forbidden);
  #2 = F1/S3; #3 = F2/S2; #4 = S4; #5 = S6+Door#4; #6 = S10; #7 = S9; #8 = re-anchor
  discipline. **Zero scope-change escalations now** beyond the expected doors.

### Pythia (adjudication) — fork→door lattice + UV-P-4 + wave-2
- **Door count stays 4.** F1 (artifact shape) is NOT a new door — it **folds into a
  retitled DP-2**: *"v2 storage-shape commitment: artifact-shape + key/schema"* (F1+F3
  co-determine one physical thing), carrying adversary dissent on BOTH slates. F6 design
  auto-ratifies; its terraform limb is already Door #4. **Two SURFACE notes for
  operator:** (a) the DP-2 retitle must be stated, not silently ridden; (b) DP-4b must
  diff against DP-4a-applied state (same parent-repo surface).
- **UV-P-4 resolved (does NOT block S1 — S9 concern):** `.a8/knossos` FALSIFIED; the raw
  `.knossos/` dirs are **per-project RUNTIME STATE, not doctrine homes** (best-fit
  `repos/.knossos` as a file-drop target is a category error). `KNOSSOS_HOME` =
  `/Users/tomtenuta/Code/a8t/knossos` (a8t platform org, distinct from the autom8y
  product fleet). **De-facto fleet-constitution-of-record already lives IN-REPO** at
  `autom8y-asana/.ledge/decisions/` (where R24–R34 landed, #270 dfdb84a3).
  **S9 recommendation:** land doctrine in `autom8y-asana/.ledge/decisions/` as the
  fleet-constitution-of-record; fleet inheritance rides the **S10 kit** (template
  application, P12), NOT a shared `.a8/knossos` path. **Two non-blocking operator SURFACE
  items:** (i) charter P11's `.a8/knossos` model is aspirational/unbuilt — amend the
  literal; (ii) T3 re-examination — law + kit both land in autom8y-asana (disjoint
  files, same repo), not the cross-repo split T3 implies.
- **Wave-2 door-independence:** S2/S6/S7/S9 door-INDEPENDENT (flow on PT-01 pass); **S3
  held on DP-2**; **S5 held on DP-3** (S5 not in the first fan). Since DP-2/DP-3 batch at
  S1 exit, practical fan = **4-wide-immediate {S2,S6,S7,S9} + S3-on-DP-2-ratify**; S6
  terraform-apply limb waits on DP-4a but the build lands ahead.

## 8. Finding-#1 deciding fact — RESOLVED → DP-1F recommendation

Grep (read-only): `active_mrr` lives ONLY in `metrics/**` (+ `builders/post_build_population_receipt.py`);
the service/MCP layer has **no** `active_mrr` computation. MCP tools = query/resolve/
discovery/composite_write/confirm_gate/tag_resolve/workflows — the live path serves
generic `query_rows`/`query_aggregate`, not the metric. **So:** the operator-facing
`active_mrr` is CLI-only and *that* path is #276-guarded; the residual is that the
live/MCP path can serve stale **MRR-equivalent aggregates** to secondary consumers,
unguarded — lower severity, cured at cutover by S5's whole-design.

**DP-1F (emergent operator decision-packet) recommendation: (c-i) HOLD P6** — no v1
live-path retrofit; log the residual live/MCP aggregate exposure as an
**extinction-urgency accelerant** (fast-path S8→cutover→S11). Rationale: the exact wound
metric is CLI-only and already floor-guarded; retrofitting v1's live path is new v1 code
(P6 non-goal / DEFER-2). This is NOT a pre-registered door; surface it to the operator at
the close alongside DP-2/DP-3 for a one-word ratify/amend.

## 9. S1 Phase-1 artifacts (LANDED — drafts pending gate)

- **`.ledge/specs/TDD-substrate-v2.md`** (architect) — whole-design: *one small store of
  one thing*. 6 modules, 5 frozen seams, one inward dependency arrow to two pure-core
  types (`ArtifactId`, `FreshnessProof`). Each RC discharged BY SUBTRACTION (no second
  layout, no dual-read bridge, no probe-that-stamps, no per-call-site guard, no
  query-gated alarm). RC-table: A=one ArtifactId→one artifact→one `current.json` pointer;
  B=`built_from_live_at` + value-`content_digest`, no probe-stamp; C=`entity_type`
  REQUIRED in the key type + one read choke-point; D=no dual-read bridge + CI sunset;
  E=staging-only writes, reader has no write method, atomic pointer-flip; F=scheduled
  evaluator on the shared proof + self-heartbeat.
- **`.ledge/decisions/ADR-substrate-v2-fork-register.md`** (architect) — F1-F6 slates +
  provisional rulings + door routing. **F1+F3→DP-2** (versioned immutable artifact +
  atomic `current.json` pointer; typed required `entity_type` key — kills v1's
  `_entity_segment(entity_type: str|None=None)` + `legacy_fallback_enabled=True`). **F2
  auto-ratify** (content-digest + build-from-live age, no probe-stamp; D8 retired by
  DELETING the re-stamp). **F4 auto-ratify** (stage-validate-swap + capability-typed
  reader). **F5→DP-3** (single typed read choke-point returning `Provable | Refused`;
  raw `storage.load_dataframe` made private). **F6 auto-ratify** (query-independent
  scheduled provability evaluator + self-heartbeat; terraform limb = existing Door #4).
  Architect's two non-obvious findings: (a) v1's `_guard_plane_divergence` is a
  *divergence detector* that **goes blind once v1 is deleted** — structural reason F2
  must be content-derived + absolute-age, not divergence-based; (b) F5 guard covers only
  CLI (re-confirms finding #1).
- **`.ledge/specs/RC-acceptance-predicates-substrate-v2.md`** (requirements-analyst) —
  22 falsifiable predicates (A:4 B:4 C:3 D:3 E:4 F:4). RC-C consumer-exhaustive (6-path
  inventory CP-1..6). $84,385-vs-$79,585 encoded as the parity exemplar. Root defect
  named: `entity_type: str | None = None` (storage.py). **Two non-blocking OQs for
  Phase-3 reconciliation:** OQ-1 (RC-A-2 "explained divergence" refusal payload schema
  must reconcile with the architect's wire format, and must not be narrowed); OQ-2 (if
  the architect's chosen surface can't make the discriminator a static type error, RC-C-1
  degrades to FAIL-LOUD for that path and the P3 weakening must be DISCLOSED).

## 10. S1 Phase-2 status

- **principal-engineer — ✅ COMPLETE.** `.ledge/reviews/FEASIBILITY-substrate-v2-seams-s1.md`.
  Verdict: **BUILDABLE-AS-DRAWN** (no hard infeasibility; feasibility does NOT co-trigger
  a re-enter). RC-C typed-key REACHABLE (`EntityType` closed Enum `core/types.py:13`;
  mypy strict already repo-wide — but `EntityType.UNKNOWN` is typed-world plane-blindness,
  `__post_init__` must reject it). RC-E reader-no-write REACHABLE at
  deleted-method+mypy-strict+type-separation floor. 5 hardened seam contracts (deltas
  [H1]-[H23]); highest divergence risks: **[H1]** digest canonicalization must be frozen
  in `substrate.freshness` (column set/row order/parquet-independent encoding/null/float);
  **[H5]** `read_current` raises `ArtifactMissing`, does NOT return `(None,None)`.
  Cross-process refuse contract: **every `Refused` is a non-2xx; NO `Refused` is a 200**
  (server envelope `api/errors.py:92`; MCP consumer already raises on non-200
  `mcp/asana_mcp/tools/_common.py:63`). **[H20]** F6 hole: a partial evaluator run that
  emits a heartbeat but skips a broken artifact still reads green → seam needs a
  completeness metric (`evaluated_count` vs expected), not just a heartbeat.
  **LOAD-BEARING COLLISION (feeds DP-3):** ratified `ADR-serve-stale-within-bound
  (2026-06-03)` serves STALE on a **200 with `stale_served=true`** (`query/models.py:249,
  :428`) — the exact confidence-labelled-stale number RC-B/P2 forbids. v2's serving seam
  retires it (STALE → non-2xx `Refused`); PE recommends **STALE→5xx-class** (not 409) so
  substrate-unprovability stays visible to the receiver SLI (which ignores 4xx) — aligns
  RC-F. `map_http_error` has no "stale, needs rebuild" branch today.
- **arch-adversary — ❌ BLOCKED (spend limit).** Produced only a partial read before
  termination. The rite-disjoint fork critique + {BLOCK/PASS-WITH-CONDITIONS/PASS}
  verdict + per-fork dissent register are MISSING. **This is the resume point.**

## 11. EXACT RESUME SEQUENCE (ignite from here)

1. **Operator:** resolve spend limit (`/usage-credits` or switch model), then `/go`.
2. **Re-dispatch arch-adversary** (arch rite, rite-disjoint) on the Phase-1 slate. Prompt
   already composed — re-use the §10 charge: challenge every F1-F6 slate under
   option-enumeration-discipline (slate-exhaustiveness, choice-defensibility,
   RC-discharge integrity); treat the architect's 4 pre-named seams (F5 cross-process, F1/F3
   versioning+GC, F2 build-from-live-age vs "provably current", F4 impossible-in-Python
   honesty) as a FLOOR not ceiling (find un-flagged attack surface — common-mode blindness
   is the risk); render {BLOCK/PASS-WITH-CONDITIONS/PASS} + per-fork dissent (make F1/F3
   and F5 dissent operator-legible — DP-2/DP-3 carry it verbatim); self-assessment caps
   MODERATE; P7 economical. Targets: `.ledge/specs/TDD-substrate-v2.md`,
   `.ledge/decisions/ADR-substrate-v2-fork-register.md`, cross-ref the acceptance
   predicates + PE feasibility (§10) — esp. the serve-stale-on-200 collision and [H20].
3. **Phase-3 — architect finalizes:** reconcile the acceptance predicates (OQ-1/OQ-2) +
   PE seam hardening ([H1],[H5],[H20], the STALE→5xx recommendation) + adversary dissent;
   finalize `TDD-substrate-v2.md` + ADR set; author the operator decision-packets:
   - **DP-2** → `.ledge/decisions/DP-2-v2-storage-shape.md` (retitled per pythia:
     artifact-shape F1 + key/schema F3), adversary dissent on BOTH slates attached; STATE
     the retitle to the operator.
   - **DP-3** → `.ledge/decisions/DP-3-consumer-contracts.md` (F5), dissent attached;
     MUST carry the serve-stale-on-200 retirement decision + the STALE→5xx-vs-409
     sub-decision (PE §10).
   - **DP-1F** (emergent) → `.ledge/decisions/DP-1F-v1-live-path-p6-boundary.md`, carrying
     the §8 fact + the (c-i) HOLD-P6 recommendation.
   HALT all three threads pending operator ratification (P8 — nothing crosses on auto-ratify).
4. **PT-01 hard gate** (potnia): the 5 structural checks (§7). On pass → S1 EXIT (LEG-0).
   On fail → bounded architect re-enter (DELTA), no build begins.
5. **Wave-2 staging** (prepare, do NOT fire until PT-01 pass + door ratification per §12).
6. **Close:** update the moirai sprint tracker (§13); telos writeback at genuine S1-exit
   (§15); `/sos wrap`.

## 12. Wave-2 staged specs (per shape §4 phase-2 + pythia)

On PT-01 pass, 5-wide fan via `workflow:sprint-parallel-worktrees`, one atomic PR/sprint:
- **S2 freshness** (RC-B, F2) — DOOR-INDEPENDENT, flows immediately. Retire D8 by
  construction (content-derived truth); do NOT re-heal.
- **S3 storage/keys** (RC-A/C, F1+F3) — **HELD on DP-2 ratification.** Unify the
  consolidated-vs-per-section split; entity-blind write path unconstructable (type error).
- **S6 observability** (RC-F, F6) — build DOOR-INDEPENDENT (flows on PT-01); cross-repo
  terraform APPLY limb held on DP-4a. Include the [H20] completeness metric.
- **S7 gate-harness** (P5) — DOOR-INDEPENDENT. Encode the $84,385 parity exemplar;
  two-sided teeth.
- **S9 doctrine** (P11) — authoring DOOR-INDEPENDENT (constitution LANDING checkpoint-gated
  on S8-green). Target `autom8y-asana/.ledge/decisions/` per pythia's UV-P-4 resolution.
- (Second wave) **S4 rebuild** + **S5 serving** gated on S2+S3; S5 held on DP-3.

## 13. Moirai sprint-tracker — intended update (apply via Task(moirai) next session)

`sprint-20260728-substrate-v2-wave1`: mark COMPLETE — S1-explore-svr-vetting,
S1-design-tdd, S1-acceptance-predicates; mark COMPLETE (PE half) + BLOCKED (adversary
half) — S1-feasibility-seams / S1-adversarial-critique; PENDING — S1-decision-packets,
S1-gate. (Not applied this session: moirai is a subagent — would fail on the spend limit.)

## 14. SVR / UV-P deltas carried

- UV-P-1 (warmer Lambda image has #276 P1 fix) — STILL DEFERRED (prod: deploy-dispatch
  receipt + ECR digest; discharges at S6/S8, off the P10-paced primitive).
- UV-P-2 (post-#276 warm writes v2 plane) — STILL DEFERRED (prod: S3 probe ≥1 warm cycle;
  S8 baseline / PT-04 full).
- UV-P-3 — REFINED (§6.6): real surfaces in autom8y/autom8y-data/autom8y-ads + the
  autom8y-cache SDK; discharges fully at S10.
- UV-P-4 — RESOLVED-MODEL (§7 pythia): in-repo `.ledge/decisions/` of-record + S10
  propagation; exact path formality at S9 entry (`ari home`/`ari org`).
- UV-P-5 (co-seat CC-restart heuristic) — moot; co-seats already live this session.
- NEW UV-P candidate: the live/MCP aggregate exposure (§8) — watch-trigger = v1-live
  window extends; owner = DP-1F / WS-C extinction urgency.

## 15. Telos writeback — intentionally DEFERRED (not mutated)

The RATIFIED telos (`.know/telos/substrate-v2-epoch.md`) was NOT mutated this session.
The Phase-1/Phase-2 artifacts are DRAFTS pending PT-01, not gate-passed realizations;
per F-HYG-CF-A, Gate B refuses wave-level tokens without genuinely-landed realization,
and S1 has not exited. `attestation_status` correctly remains `shipped: MISSING`,
`verified_realized: UNATTESTED`. Writeback fires at genuine S1 exit (PT-01 pass) with the
real `{path}` anchors for the ratified TDD + ADR set. (Recorded here so the deferral is
deliberate, not an omission.)

## 16. Discipline carried (binding on resume)

- P8: nothing crosses a door on auto-ratify; DP-2/DP-3/DP-1F carry dissent, HALT for operator.
- P7: rigor concentrates at PT-01 + the doors ONLY; do NOT gold-plate the corridor.
- P10: prod-touch is paced/budgeted/off-peak/receipted; ad-hoc unpaced pulls BANNED
  (S1 required none; S6/S8/S11/S12 do — ride the S4 primitive).
- Re-anchor ADR claims FRESH (drift 39–473 lines); never cite ADR line numbers.
- T2 disjointness: attested streams run active-rite 10x-dev; final attestation (S12) runs
  active-rite eunomia. NO eunomia agent authors corridor work.
- Main thread is the SOLE dispatcher (agents cannot spawn agents).

## 17. CLOSE 2026-07-29 — S1 EXITED (resume executed per §11; supersedes §13/§15 deferrals)

**Resume charge executed in full** (operator /go dispatch 2026-07-29): fresh arch-adversary →
Phase-3 finalize → PT-01 → staging → close. The only open halts are DP-2 and DP-3.

### PT-01 verdict (fresh-instance potnia, de novo, per-question receipts)

**PASS.** Q1-Q5 all YES (RC constructions `TDD:302-309`; slates+dissent `ADR-fork-register:82-88`
+ `ADVERSARY:62-220`; legible-whole `FEASIBILITY:320-326`; seams frozen `TDD:311-503`;
consumer-exhaustive CP-1..6 `FEASIBILITY:273-283` + `RC-acceptance:204`). Supplementary S-a..S-d
all clean: adversary BLOCK-triggers cleared (C1∈Seam-3 `TDD:403,418-419`; C4∈`DP-2:73-96`;
C5∈`DP-3:76,146-161`); C1-C7 dispositioned `TDD:587-606` (zero rebuttals); doors AWAITING-OPERATOR
with dissent verbatim; the PE-5xx-vs-adversary-424 conflict carried TWO-SIDED in `DP-3:85-137`
(surfaced, not absorbed). The TDD did not self-ratify — this gate flipped it.

### Adversarial critique (the resume point — now discharged)

PASS-WITH-CONDITIONS. Sharpest finding **AV-1**: the drawn Seam-3 incremental rebuild resurrected
D8 inside v2 (reused sections stamped live-fresh) — fixed by C1: per-section live-fetch provenance,
artifact `built_from_live_at` = MIN over sections; a probe may decide a re-fetch but never advances
an instant. Also: DP-2's draft carried a FALSE S3-atomicity premise (corrected, P12); both door
slates were truncated (A-prime/C-prime/E added to DP-2; F5-5 typed-client-SDK added to DP-3);
PE's STALE→5xx contested → carried two-sided.

### Operator ballot (the two open halts + one pre-ruled record)

| Packet | Status | Decision awaited |
|---|---|---|
| **DP-2** `.ledge/decisions/DP-2-v2-storage-shape.md` | **RATIFIED 2026-07-29** | ruling: shape **C** (versioned-immutable + If-Match CAS pointer, C3 teeth) · segment **entity-after-project** · sub-3 moot. S3-atomicity SVR **DISCHARGED at ratification** (AWS docs-cite verbatim — packet §Ratification record). **S3 UNBLOCKED.** |
| **DP-3** `.ledge/decisions/DP-3-consumer-contracts.md` | **RATIFIED 2026-07-29** | ruling: **424 + Retry-After + refusal-SLI** (PE's 5xx preserved as the unadopted alternative) · F5-5 SDK = P11 law · ADR-serve-stale-within-bound supersession **EXECUTED** (frontmatter marked). Consumer-side classification lands WITH-OR-BEFORE the server flip. **S5 door satisfied** (awaits {S2, S3}). |
| **DP-1F** `.ledge/decisions/DP-1F-v1-live-path-p6-boundary.md` | **RATIFIED-BY-OPERATOR** (c-i HOLD P6, pre-ruling 2026-07-28) | none — inscribed for the record; live/MCP stale-aggregate residual logged as WS-C extinction-urgency accelerant |

### PT-01 advisories carried into wave-2 (non-blocking)

(1) door-gated sprints stage-don't-build; (2) discharge the S3-atomicity UV-P BEFORE DP-2
ratification; (3) four S2-entry UV-Ps (`TDD:135-140`); (4) **C8 SLA-governance is the
highest-residual carry** — AV-3: an ungoverned 14d `sla_seconds` re-serves the wound with a green
proof; surface per-entity SLA values + the "provably ≤ SLA-old" semantic delta no later than S8;
(5) DP-1F residual = extinction-priority signal, not an S5 dependency.

### Close receipts

- TDD `status: accepted / lifecycle_status: ratified` + §9 PT-01 box checked.
- Telos Gate-B: five `(landed S1 2026-07-29)` rows with real `{path}:{line}` anchors written to
  `.know/telos/substrate-v2-epoch.md` (mission/predicate untouched; `attestation_status` unchanged
  — shipped stays MISSING at epoch level, correctly).
- Wave-2 staged: `.ledge/handoffs/STAGED-wave2-dispatch-specs-2026-07-29.md` (ignition matrix,
  7 sprint specs, C8-C11 routed, UV-P duties).
- Sprint tracker + session wrap: via moirai (see SPRINT_CONTEXT for final task states).
- Git: S1 artifacts intentionally UNCOMMITTED pending operator word (docs-only delta; no src
  change; branch `docs/substrate-v2-epoch-founding`).
