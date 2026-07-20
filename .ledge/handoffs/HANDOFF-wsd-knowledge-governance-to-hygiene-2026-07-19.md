---
type: handoff
status: staged   # awaiting hygiene/audit-lead critique; carried WS-E rows discharge at sprint-6
source_rite: docs (WS-D sprint-5, asana-mcp-postfelt-hardening)
target_rite: hygiene (audit-lead per-sprint .know-accuracy critique; janitor for the WS-E rows carried below)
initiative: asana-mcp-postfelt-hardening
date: 2026-07-20
author: tech-writer (WS-D s5 seat — single telos writer; doc-auditor rigor applied in-seat)
evidence_ceiling: MODERATE (self-ref authorship; self-ref-evidence-grade-rule — the audit-lead critique and eunomia PT-09 are the external legs)
telos: .know/telos/asana-mcp-postfelt-hardening.md   # carried per Gate C
vehicle: PR autom8y/autom8y-asana#247, branch docs/asana-mcp-postfelt-wsd (merge dispatcher-sequenced after #249; operator-reservation honored)
---

# HANDOFF — WS-D knowledge/governance reconciliation → hygiene

> Shape sprint-5 exit artifact (`asana-mcp-postfelt-hardening.shape.md` sprint-5
> `exit_artifacts`). Receipt grammar per telos-integrity-ref Gate C: every claim-token
> below carries a `{path}:{line}` anchor, a named receipt artifact, or an explicit
> `[UNATTESTED — DEFER-POST-HANDOFF]` tag. No wave-level CLOSED token appears; gates
> named here are closed only where the operator closed them.

## 1. Deliverables filed (all riding PR #247; anchors valid at its merge)

| # | Deliverable | Receipt |
|---|---|---|
| 1 | .know witness-arc refresh, pass 1 (authored at `793e670b`) + pass 2 (re-verified at freshly-fetched `f6a72824`) | `.know/architecture.md:165` (§MCP Sidecar Surfaces — restated to the post-#242 UNIFIED island); `.know/design-constraints.md:226-245` (MCP-BUDGET-PARTITION/WRITE-FLAG/B1O1-COUPLING/REFERENCE-POSTURE-001, anchors re-pointed to `mcp/asana_mcp/*`); `.know/test-coverage.md:397` (§MCP Island Test Topology — island CI-gap now TOTAL, named) |
| 2 | Scar promotions (satellite-local branch per scar-tissue-promotion; H1/H3 receipted where promoted) | `.know/scar-tissue.md:342` SCAR-VOCAB-PARITY-001 (dyn-enum 3rd strike; CURED #245 `2eb830ca`; parity guard `tests/unit/services/test_entity_vocabulary_parity.py:73,:113,:126`); `:399` SCAR-AUTHSIG-001 (TEB 400/404/401 attribution table + species map + P4 rows); `:438` SCAR-TG-LIVENESS-001 (3rd strike of SCAR-011/011b class) — **CURED at refresh-2**: fleet #1157 `d502398d` + #1154 `e8079654` + a8 #104 `80402fd3` + satellite #248 `6edc83d5`; apply run 29753896034 SUCCESS; PT-04 receipt (activation ledger `:128-144`); candidates PLAY-CONSUMED-TRIGGER + OPTFIELDS filed at N=1 (not over-promoted) |
| 3 | C1 reconciliation + fork-(a) receipt FILED on the dossier record (limb (c) substrate) | `.ledge/decisions/DECISION-asana-mcp-v1-rulings-B1-B5-W5.md:856` ADDENDUM-1 (append-only; zero ratified text modified, zero checkboxes): C2 no-re-fire receipt (envelope §3.3 + `.sos/wip/asana-mcp-v1.c2-probe-evidence-2026-07-19.json`; UV-P #4 DISCHARGED-BY-PROBE) + Step-6.5 corroboration + the digest-§11 consumed-trigger scope split; the `tasks.py:254` ruling is STAGED at `:915` §A1.4 — **operator-only** |
| 4 | Defer-watch registrations (append-only; YAML parse-verified) | `.know/defer-watch.yaml`: `mcp-tag2-tag-only-play-verb-2026-07-20` (trigger = GATE-PROBE COMMIT on `repos/.ledge/decisions/PROBE-fleet-mcp-second-leg-2026-07-20.md`, due 2026-08-03; escalation = charter amendment; owner 10x-dev); `mcp-play3-automation-fire-confirmation-2026-07-20` (operator A1-Notes directive, envelope `:320-324`; owner WS-B2/production); `mcp-preload-duration-reduce-or-persist-2026-07-20` (PT-04 measured ≈29.5 min > 18-24 min band; owner sre; N=1 watch, no build) |
| 5 | Telos (SINGLE WRITER — both files landed tracked) | `.know/telos/asana-mcp-v1.md` — shipped LANDED (7 per-item anchors, historically pinned at their squashes with the #242-unification note); verified_realized REALIZED **citing** the operator's felt verdict at `.sos/wip/asana-mcp-v1.felt-gate-envelope.md:503-526` (§5.2 — not restated); eunomia advisory honestly null/PENDING. `.know/telos/asana-mcp-postfelt-hardening.md` — Gate-B rows at refresh-2: WS-A/WS-B1/WS-C/WS-D real anchors; WS-B2 recorded in-flight (#249 head `cb51833b`); WS-E (planned); status stays PROPOSED (A3 ratification is the operator's) |

CI on the vehicle: PR #247 was fully GREEN at pass-1 head `5a3572e9` (23 pass / 2 by-design skips); pass-2 head re-runs CI — see the PR checks tab for the live state. [UNATTESTED — DEFER-POST-HANDOFF: pass-2 CI outcome | watch: PR #247 checks]

## 2. For the audit-lead critique (known soft spots, surfaced honestly)

- Pass-1 §MCP content was verified at `793e670b` and went stale within hours when #242
  merged; pass-2 restated it at `f6a72824`. The refresh banners in all four .know files
  declare the two verification hashes — critique should check the pass-2 statements, not
  the superseded pass-1 framing preserved in banners for lineage.
- The island CI-gap claim (total; `.know/test-coverage.md` Knowledge Gap 7) rests on:
  root `testpaths = ["tests"]` (`pyproject.toml:113`), zero `mcp` references in
  `.github/workflows/` (grep at `f6a72824`), and `mcp/pyproject.toml` island-local
  testpaths. If a CI lane for `mcp/` exists elsewhere (org-level config), the claim
  narrows — none was found in-repo.
- The s4 critic DELTA PASS for #249 is dispatcher-reported (no critic artifact found in
  `.ledge/reviews/` at authoring) — the WS-B2 telos row says so explicitly.

## 3. Carried to WS-E (janitor) — residue rows this handoff does NOT discharge

| Residue | Detail |
|---|---|
| Untracked-file collision (operator's stale checkout) | The parent checkout at `f3d8eec1` holds UNTRACKED copies of `.know/telos/asana-mcp-v1.md`, `.know/telos/asana-mcp-postfelt-hardening.md`, and the dossier; after #247 merges, `git pull` there may refuse to overwrite. WS-E's local fast-forward row must reconcile (the tracked PR versions are the updated truth; parent copies predate the WS-D updates) |
| Worktree reap | `.knossos/worktrees/wt.docs.asana-mcp-wsd.20260720T140018.feeab7` (this seat's worktree; branch `docs/asana-mcp-postfelt-wsd`) — reap AFTER #247 merges. Other lane worktrees trail their own merges per the shape |
| C2 sandbox cleanup | Unchanged from the shape: project ZZ-MCP-C2-PROBE `1216706635260794`, tag SMOKE `1216701886984400`, task `1216701886984398` — delete Asana-side; the JSON evidence bundle is RETAINED (receipts are never cleanup targets) |
| Helper scripts | `repos/asana-mcp-v1.witness-crib.zsh` + `repos/asana-mcp-v1.witness-launch.zsh` disposition per shape WS-E |

## 4. Open operator items (HALT-grade none; all staged, none closed by any session)

1. `tasks.py:254` reconciliation ruling — dossier ADDENDUM-1 §A1.4 (`:915`): fork (a)
   flip vs fork (b′) keep-with-caveat; both receipts filed; the mark is the operator's.
   Limb (c) completes at that mark.
2. A3 telos ratification of `.know/telos/asana-mcp-postfelt-hardening.md` (status
   PROPOSED; deadline 2026-08-14 and eunomia attester amendable).
3. GATE-PROBE ruling (COMMIT / PARK / KILL) due **2026-08-03** — drives the TAG-2
   defer-watch trigger and the island's reference-posture horizon.

## 5. Contradictions found under verify-don't-trust (for the record)

- The dispatcher's refresh brief referenced "the preload reduce-OR-persist defer-watch
  you registered" — no such entry existed (not in this branch, not on main; grep-verified
  at `f6a72824`). Registered NOW as `mcp-preload-duration-reduce-or-persist-2026-07-20`
  with the PT-04 measurement as its evidence anchor.
- Fresh main carries SIX substrate-arc commits (ITEM-A..F, `4fd903ea..f6a72824`), not
  four; immaterial to any row here (recorded for census honesty).

# END — handoff staged for audit-lead critique; merge of the vehicle stays
# dispatcher-sequenced; the felt/probe/ruling gates remain the operator's alone.
