---
type: handoff
handoff_type: strategic_evaluation
source_rite: eunomia
target: "operator (Q1-Q3 rulings) + Phase-2 cross-repo seat (autom8y-auth / autom8y-api-middleware / ui)"
initiative: fleet-delegation-portfolio
phase: 1-near-horizon (inaugural wave — CLOSE)
date: 2026-07-23
status: accepted
telos: .know/telos/fleet-delegation-portfolio.md   # Gate C — this HANDOFF carries the telos
governing_decision: .ledge/decisions/DECISION-fleet-delegation-inaugural-wave-forks-2026-07-23.md
source_anchor: "autom8y-asana origin/main 2c91a724 (post P0+D1 merge); autom8y monorepo origin/main a53288db (SDK)"
evidence_grade: "MODERATE (self-cap; corroborated by two rite-disjoint advisory consults + three rite-disjoint per-sprint critics — see §2)"
---

# HANDOFF — fleet-delegation inaugural wave CLOSE (eunomia → operator + Phase-2)

## 1. Wave outcome (said first)

The **in-repo floor landed**; the **keystone is HALTED at R4** and the realized bar
moves to a cross-repo Phase-2. This wave shipped **capability and provenance**, not
the mission — and says so honestly (no built-unconsumed overclaim). The operator's
CONSUMPTION predicate (audit-names-the-human) is **structurally unreachable inside
autom8y-asana**; the honest in-repo cap is **PT-04 (identity consumed)**, itself gated
on a species decision that is operator-reserved (R4).

## 2. Merge receipts (per-item — the landed floor)

| Sprint | Contribution | PR | State | Rite-disjoint critic |
|---|---|---|---|---|
| **P0** provenance-floor | ENABLE | #267 (squash) | **MERGED** → origin/main `1a3a3023` | qa-adversary (10x-dev ⟂ eunomia): **CONCUR** @ 6117dcdb |
| **D1** WS-7 actor-attribution seam | SHAPE | #266 (squash) | **MERGED** → origin/main `2c91a724` | qa-adversary (10x-dev ⟂ arch): **CONCUR-WITH-CONDITIONS** @ 07d709cd → corrections applied @ c3ca77ad (delta-guarded), re-verified green |
| **L1** light-the-rung / WS-5b | CAPABILITY-NOW / consumption-post-Phase-2 | #268 | **CONCUR'd, merge-in-flight** (updated `66a648ba`, delta-guarded, CI re-running) | security-reviewer (security ⟂ 10x-dev): **CONCUR @ STRONG** @ 7015a4fa (three non-substitutable legs) |

- P0 landed the 2 stranded ACCEPTED ADRs + 2 companion TDDs + 2 defer-watch entries → **§3 PREMISE-3 discharged**; DEFER-2026-051 watch-trigger resolved TRUE.
- D1 landed the actor-attribution seam ADR (the schema constraint Phase-2 K3 must honor).
- L1 disclosed the **registered report-workflow surface** via a pure-read MCP tool `list_report_workflows`; it did **not** expose the invoke/write path (see §6 R7 item).
- Attester-disjointness held: eunomia executed only P0 and never built/probed the keystone.

## 3. Fork resolutions (full detail in the governing DECISION)

- **FORK-C → HOLD autom8y-auth 4.1.0.** SDK 4.2.0 ships `OperatorClaims`, but that is the wrong vehicle (FORK-D); the pin-bump is deferred, not mission-needed. Residual: is 4.2.0 CodeArtifact-resolvable (needs valid creds — a critic hit a 401 on expired creds this wave).
- **FORK-D → R4 HALT.** `OperatorClaims.operator_sub` = a SigV4/STS ARN agency principal, not the human. The mission's `sub`=human/`act`=agent species is minted auth-server-side (`tokens.py:405 agent_token_exchange`) but **un-modeled by any SDK claims class**. Widening asana's ServiceClaims-only inbound = witness-credential species migration = **R4, operator-reserved.**
- **FORK-E → K3 realized bar is CROSS-REPO.** No `business_id` slot, no DB/ORM/migration layer, no `audit_logs` table in autom8y-asana. Human-named audit-of-record is written in autom8y-auth (`models/audit_log.py:45-46`).

## 4. Realized-bar status (evaluation_criteria — the go/no-go the next seat inherits)

**PT-05 REALIZED = UNMET (and unreachable in-repo).** The three non-substitutable Phase-2 legs:

1. **Fleet/SDK** — mint an actor-modeling claims class (or a satellite-consumable RFC-8693 delegation contract). **R4-gated (operator).**
2. **autom8y-auth** — `agent_token_exchange` (built) writes the human-named audit row (`delegating_user_id`/`acting_agent_id`; FK integrity pending migration 028).
3. **autom8y-asana** — deliberately widen the inbound ServiceClaims-only contract to witness/authorize on the human-delegation species (breaks `test_contract_auth`). **Operator-reserved.**

Vendor ceiling carried, not papered: even with perfect in-fleet consumption, Asana's own API acts as the bot until a separate per-user-Asana-OAuth decision (R20 caveat i, unscoped).

## 5. DEFER register (carry — the drift-free seam)

| Item | Watch trigger | Owner |
|---|---|---|
| V-13 monolith write-plane identity fork | K3 consumption receipts land | operator (registered at P0: DEFER-2026-050) |
| R22 2026-07-28 transport gate (WS-6 build held) | gate date resolves | auto per ruling |
| a8t sovereign-edge grounding | operator produces org/repo or CF config/CI receipt | sre/operator (barred-from-REALIZED, confirmed) |
| **SDK actor-modeling contract gap** | a satellite must witness `sub`=human/`act`=agent | fleet auth-SDK seat (R4-gated) |
| **K3 cross-repo audit substrate** | Q3(a) authorized | 10x-dev @ autom8y-auth / api-middleware |
| **FORK-C pin-bump 4.1.0→4.2.0** | a real OperatorClaims consumer need in asana | 10x-dev @ autom8y-asana |
| **mcp/-island CI-coverage gap** (L1 critic) | any future edit to the mcp/ island | operator — track as separate charter item; compensated this wave by the critic's rite-disjoint local re-run (158 passed) |
| **P0 depth-2 references** (P0 critic advisory) | a stream follows the ADRs' still-untracked References | next retrospective — land the 4 refs or open a live DEFER (DEFER-2026-051 is terminal/DISCHARGED, no live watch fires) |
| **contract_complete unconditional True** (L1 critic) | oracle gains pagination/truncation | drift-watch only |
| stranded-ADR landing | — | DISCHARGED at P0 merge |

## 6. Operator decisions SURFACED (operator-reserved; do NOT execute)

- **Q1 (scope):** Accept the keystone re-scope — in-repo Phase-1 caps at PT-04; PT-05 REALIZED lands cross-repo (autom8y-auth + api-middleware)?
- **Q2 (R4 contingency):** The probe shows OperatorClaims ≠ human. HOLD for a fresh ruling (default), or pre-authorize a scoped **read-only** auth-server actor-contract spike (no mint changes)?
- **Q3 (cross-repo continuations):** Authorize (a) the K3 audit-substrate continuation charter, and (b) the U1 consent-journey **ui-rite switch** (`cd /Users/tomtenuta/Code/a8/a8 && ari sync --rite=ui`, operator-run)?
- **NEW R7 item (from L1):** The report-workflow **invoke** path (`POST /api/v1/workflows/{id}/invoke`) writes to Asana (uploads/deletes attachments; `idempotent:false`; consumed-trigger scar). L1 deliberately did **not** disclose it. Ruling needed to disclose any invoke verb (reviewed+guarded=go, R7). `payment-reconciliation` is scoped out for the same reason.
- **FORK-C residual (creds):** the `aws codeartifact list-package-versions ... autom8y-auth | grep 4.2.0` check needs refreshed CodeArtifact creds (a critic hit a 401 this wave).

## 7. Phase-2 inheritance (clean · attested · drift-free)

The next seat inherits: a discharged provenance floor (P0), a ratified actor-attribution schema constraint (D1 — the Phase-2 K3 schema MUST carry `sub`=human + `act`=agent for BOTH request- and event-triggered actions, and MUST NOT lock until the SDK models the actor claim), a disclosed read surface (L1), and the DEFER register above. The keystone is a **cross-repo Phase-2 /shape** gated on the operator's Q1-Q3. Re-run the §3 premise probes at Phase-2 entry (SDK line numbers move on release). No wave-level CLOSED token issued (Gate B).
