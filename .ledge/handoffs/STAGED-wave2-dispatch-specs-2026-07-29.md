---
type: handoff
artifact_type: STAGED-DISPATCH-SPECS
initiative: substrate-v2-epoch
wave: WAVE-2 (dark build — 5-wide fan)
staged: 2026-07-29
status: draft
stage_state: "STAGED — NOT FIRED. Ignition per the matrix below; nothing builds behind an unratified door (P8)."
authority: "PT-01 PASS 2026-07-29 (S1 exit, LEG-0 certified) + pythia door-independence adjudication 2026-07-28"
build_contract: ".ledge/specs/TDD-substrate-v2.md §4 (seams v1.0-frozen-2026-07-29) + .ledge/reviews/FEASIBILITY-substrate-v2-seams-s1.md ([H1]-[H23] hardened contracts)"
charter: .ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md
telos: .know/telos/substrate-v2-epoch.md
---

# STAGED — Wave-2 dispatch specs (substrate-v2-epoch)

The next session ignites wave-2 from this file + the frozen TDD alone. Every sprint below
builds AGAINST the frozen seams (TDD §4) — no seam renegotiation; a seam-change request is a
finding routed back to the architect, never absorbed into a build sprint.

## 0. Ignition matrix (pythia ruling + PT-01 advisory #1)

| Sprint | Door status | Ignites |
|--------|-------------|---------|
| S2 freshness | DOOR-INDEPENDENT | on operator go (PT-01 passed) — after its 4 entry UV-Ps discharge (§S2) |
| S6 observability (build) | DOOR-INDEPENDENT | on operator go; cross-repo terraform APPLY limb waits on DP-4a |
| S7 gate-harness | DOOR-INDEPENDENT | on operator go |
| S9 doctrine (authoring) | DOOR-INDEPENDENT | on operator go; constitution LANDING checkpoint-gated on S8-green |
| S3 storage/keys | **DP-2 RATIFIED 2026-07-29** (shape C · entity-after-project) | on operator go |
| S4 rebuild | build-dependent | after {S2, S3} DONE (composes real freshness + storage) |
| S5 serving | **DP-3 RATIFIED 2026-07-29** (424+refusal-SLI · F5-5 law · supersession executed) | after {S2, S3} DONE |

**Pre-ratification duty (PT-01 advisory #2) — DISCHARGED 2026-07-29:** the S3-atomicity SVR was
verified by AWS-docs cite at ratification (receipt: DP-2 §Ratification record — single-key updates
atomic, "never partial or corrupt data"; strong read-after-write for overwrite PUTs, all regions;
If-Match ETag CAS documented on PutObject/CompleteMultipartUpload/CopyObject with 412-on-mismatch,
409/404 concurrency edges, SigV4 required). Optional S2 integration-probe corroboration remains
welcome; the premise is no longer DOMAIN-PRIOR.

## 1. Global discipline (binds every sprint)

- Pattern: `workflow:sprint-parallel-worktrees` — one worktree per sprint, ONE atomic PR per
  sprint, merge-on-green autonomous (P9).
- Proof bar (P7): green CI + one qa-adversary pass per sprint. Do NOT gold-plate; rigor
  concentrates at S8 + the doors.
- Exit anchor: the §1 verbatim realization predicate (shape) — no sprint exits on "PR merged".
- prod_touch: NONE for S2/S3/S7/S9 builds; S6 alarm deploy is paced+receipted. Ad-hoc unpaced
  prod pulls BANNED (P10).
- Re-anchor discipline: ADR line numbers are stale (drift 39–473L) — re-anchor fresh, always.
- D14: each sprint preloads ONLY charter + its slice below + the frozen seam it builds.
- Emergent findings are reported as findings; scope is governed by charter non-goals + shape §10.

## 2. Sprint specs

### S2 — freshness (WS-A · RC-B · F2 RATIFIED-AUTO) — rite 10x-dev
- **Agents**: principal-engineer (build), qa-adversary (P7 pass).
- **Mission**: content-derived truth per the frozen F2 ruling — `canonical_digest()` ([H1]: five
  pins frozen in `substrate.freshness`) + `built_from_live_at` = MIN over per-section live-fetch
  instants (C1: a probe may DECIDE re-fetch but NEVER advances an instant — only a content fetch
  does). The D8 null-watermark false-CLEAN class becomes UNCONSTRUCTABLE (no probe-stamp path
  exists to author). Do NOT re-heal — the v1 heal already shipped (#276 P3); v2 retires the class.
- **Entry UV-Ps (discharge before build locks — TDD §1 premise ledger)**: (1) #276 prober-fix
  deploy receipt (UV-P-1, paced); (2) canonical value-digest column set via DuckDB MCP prod probe;
  (3) incremental-rebuild API-budget model with real section counts; (4) S3 atomicity/read-after-write
  SVR — docs-cite leg DISCHARGED 2026-07-29 (DP-2 §Ratification record); only the optional
  integration-probe corroboration remains.
- **Carried**: C8 (SLA governance — `sla_seconds` is the whole truth-content of RC-B; AV-3 shows an
  ungoverned 14d value re-serves the wound with a green proof. Surface per-entity SLA values + the
  "provably ≤ SLA-old, not 'current'" semantic delta to the operator NO LATER than the S8 gate).
- **Exit**: freshness module vs frozen Seam-1; D8-class unconstructable proven two-sided; green CI + adversary pass.

### S3 — storage/keys (WS-A · RC-A/RC-C · F1+F3 per DP-2) — rite 10x-dev — **DP-2 RATIFIED: shape C · entity-after-project**
- **Agents**: principal-engineer (build), qa-adversary (entity-blind regression lock), topology-cartographer (arch, co-seated — 4-copy map).
- **Mission**: implement the operator-ratified DP-2 storage shape (RATIFIED 2026-07-29: **Option
  C** — versioned-immutable artifact + CAS `current.json` pointer w/ If-Match + collision-free
  version-IDs, the C3 teeth; segment order **entity-after-project**; the swap handles 412/409/404
  preconditions per the AWS conditional-write contract, SigV4 required — DP-2 §Ratification record
  build notes). One canonical layout — the
  consolidated-vs-per-section split (DEFECT :74) is UNIFIED AWAY. `ArtifactId` requires `entity_type`
  (closed enum; UNKNOWN rejected at `__post_init__` — C6 posture: omission BY-CONSTRUCTION,
  explicit-UNKNOWN FAIL-LOUD-at-construction). No dual-read bridge exists (RC-D).
- **Carried**: C11 (any SUNSET_AFTER extension requires an operator-visible ruling — also binds S11).
- **Exit**: single-source storage vs frozen Seam-2; entity-blind write unconstructable (type error,
  not lint); green CI + adversary pass.

### S6 — observability (WS-D · RC-F · F6 RATIFIED-AUTO) — rite 10x-dev + thermia lens
- **Agents**: principal-engineer (build), thermal-monitor + heat-mapper (thermia, co-seated).
- **Mission**: query-independent scheduled provability evaluator over the SAME `FreshnessProof` the
  serving gate reads; self-heartbeat; C7 two-sided expected-set (registry ∪ store enumeration — an
  unregistered-but-served artifact cannot rot green); alarm FIRES on unprovability, does NOT fire on
  a provable number (two-sided teeth). Stage DMS-24h dead-man retirement (execution = DP-4b at S11).
- **Doors**: cross-repo alarm terraform APPLY = DP-4a (operator; parent repo `autom8y`). The
  autom8y-asana build lands ahead of the apply. PT-T1 default: BUILD (observability ABOUT v1 ≠ code IN v1).
- **Carried**: C10 (cutover evidence must include ≥1 observed end-to-end FIRED alarm — feeds S8).
- **Prod**: alarm deploy paced + receipted; UV-P-1 warmer-image confirm rides here.
- **Exit**: truthful-observability vs frozen Seam-5; two-sided proof; green CI + adversary pass.

### S7 — gate-harness (WS-B · P5) — rite 10x-dev
- **Agents**: principal-engineer (replay harness + P10-paced parity runner), qa-adversary (fixture corpus, two-sided).
- **Mission**: the S8 machinery — adversarial fixture replay corpus (deliberately-broken variants
  v2 must REJECT; real inputs GREEN) + bounded live-parity scaffold (v2 beside v1 vs live prod,
  every divergence explained; rollback = restore v1). Encode the $84,385-vs-$79,585 re-baseline
  (DEFECT :64-71) as parity exemplar #1, expressed through the RC-A-2 `RefusePayload` observable
  (plane · absolute age · +$4,800/+6% magnitude · per-section delta). Fixture requirements = the 22
  predicates in RC-acceptance-predicates-substrate-v2.md.
- **Exit**: every broken variant REJECTED, every real input GREEN (teeth proven); harness EXECUTES
  at S8, not here; green CI.

### S9 — doctrine authoring (WS-E · P11) — rite arch (authoring) + 10x-dev (landing)
- **Agents**: structure-evaluator (doctrine author), remediation-planner (scar/ADR memory + sparse
  CI teeth), arch-adversary (critic), principal-engineer (landing PR post-S8-green).
- **Mission**: the six RC invariants as standing fleet law. **Landing target per pythia's UV-P-4
  resolution**: `autom8y-asana/.ledge/decisions/` as the fleet-constitution-of-record (where R24-R34
  live); fleet inheritance rides the S10 kit (template application), NOT a shared `.a8/knossos` path
  (literal FALSIFIED — the `.knossos/` dirs are runtime state, not doctrine homes).
- **Carries to operator (non-blocking SURFACE items)**: (i) charter P11 `.a8/knossos` literal needs
  amendment; (ii) T3 note — law + kit land in the same repo on disjoint FILES, not disjoint repos.
- **Exit**: doctrine authored + adversary-reviewed; LANDING gated on S8-green (checkpoint, not door).

### S4 — rebuild (WS-A · RC-E · F4 RATIFIED-AUTO) — rite 10x-dev + thermia — after {S2, S3}
- **Agents**: principal-engineer, qa-adversary, capacity-engineer + systems-thermodynamicist (thermia).
- **Mission**: stage-validate-swap composing real freshness (S2) + storage (S3): staging-only
  writes; capability-typed reader (no write method — RC-E); swap = true CAS; partial ≠ corrupt;
  rate-safe (AIMD/429-banking, per-day budget). The DEFECT :76 "read-only path writes prod"
  counterexample becomes a passing test. This primitive IS the P10-safe channel every later
  prod-touch (S8/S11/S12) rides.
- **Carried**: C9 (ValidationReceipt-gated swap or an ordering test — swap unreachable before validate).
- **Exit**: atomicity + side-effect-free-read proven two-sided; green CI + adversary pass.

### S5 — serving (WS-A/consumers · P2 · F5 per DP-3) — rite 10x-dev + security lens — after {S2, S3} · **DP-3 RATIFIED**
- **Agents**: principal-engineer, qa-adversary (stale-but-present NEVER silently served), security-reviewer (co-seated, consumer auth surface).
- **Mission**: implement the operator-ratified DP-3 consumer contract: single typed read
  choke-point returning `Provable | Refused` (raw `storage.load_dataframe` private); refuse-loud
  across ALL SIX consumer paths (CP-1..6 — CLI, force-warm/`from_s3_resolved`, MCP rows/aggregate,
  DataFrameCache, persistence wrappers); cross-process refuse per the RATIFIED status class
  (**424 Failed Dependency + Retry-After bound to the rebuild schedule + `substrate_refusal_count`
  SLI + RC-F alarms**, ruled 2026-07-29; PE's 5xx preserved in DP-3 as the unadopted alternative); refusal bodies shape-hostile; `RefusePayload` = the frozen OQ-1 observable.
  **Sequencing (hard)**: consumer-side classification lands WITH-OR-BEFORE the server flip.
  Retire ADR-serve-stale-within-bound via its explicit SUPERSEDED disposition (no 200-with-stale, ever).
- **Exit**: provable-or-refuse on every path; C1-regression (silent stale serve) locked; green CI + adversary pass.

## 3. What wave-2 must NOT do

- No v1 hardening (P6; DP-1F ruled c-i HOLD — the live/MCP stale-aggregate residual is an
  extinction-urgency signal for WS-C, not a build item).
- No strangler shapes (P4); no stale-with-labels serving (P2); no guard suites where construction
  subtracts the hazard (P3); no fork re-opening — door changes are NEW operator packets (DEFER-4).
- No sprint exits on "PR merged" — predicate-leg receipts only.
