---
type: handoff
handoff_type: execution
status: proposed
source_rite: 10x-dev
target_rite: sre
title: StorageNamespaceContract Phase-α MERGED — β-1/2/3 TF/IAM phases + γ-0 discovery + eunomia N=2 request
date: 2026-06-10
merged: autom8y-asana #123 → main 2f0e7dc0
rung: merged (Python boundary = structurally-unaddressable on the next deploy; TF/IAM = DETECTION-grade until β applies)
---

# HANDOFF — 10x-dev → sre — SNC β phases

## What merged (Phase-α, #123 → `2f0e7dc0`)
The StorageNamespaceContract registry (12 namespaces, import-time invariants, KNOWN_DRIFTS) ·
`terraform/services/asana/namespaces.gen.json` (deterministic, `--check`, **FP-2a byte-equal to the
current TF literals — including the fossil `asana-cache/project-frames/` value; Phase-α changed NO
values**) · `DurableTaskCacheReader` (the #121 pattern blessed; cure pin subsumed; FP-3 live MRR=1500)
· phantom S3 cold tier RETIRED · t1–t5 alignment tests each RED-fixture-proven · qa-adversary GO 9/9.
Behavior-neutral verified; the plane holds: **16:00Z cron warm → coherent=592, gun=11, unit.mrr=723/3021,
templates=3** (the eunomia belt-and-braces point, PASSED).

## β phases (each a separately operator-gated TF apply; sre executes the PRs, operator applies)
- **β-1**: refactor `autom8y/terraform/services/asana/main.tf` env blocks + warmer IAM resource lists to
  derive from `namespaces.gen.json` (`jsondecode(file(...))` locals). FP-2b: a NO-OP plan in the
  env/locals scope (IAM resources EXCLUDED from the no-op claim — see PV-DRIFT). Reversible.
- **β-2**: remove PUT/DELETE grants on the fossil `asana-cache/project-frames/` from the 3 warmer roles
  (registry target = GET-only; `KNOWN_DRIFTS` carries the pointer; t5 turns fully honest on apply).
- **β-3** (HIGH risk, LAST): narrow the ECS task role from `autom8-s3/*` to the declared namespace set.
  **PRECONDITIONS**: (a) enumerate the ECS receiver's live WRITE surface first; (b) reconcile
  **PV-DRIFT** — the LIVE deployed ECS policy is full-bucket while checked-in TF is ALREADY scoped
  (main.tf:955-959/1046-1050/1137-1140): determine which applied last and why live ≠ TF before touching it.

## γ-0 (operator assignment — the registry's one UNATTRIBUTED row)
Discover the active `asana-cache/tasks/` writer (385k keys, objects written 06-06/06-09): NOT in
autom8y-asana@HEAD (no prod `S3CacheProvider(` construction); A1's monolith attribution REFUTED; the
autom8 monolith repo is absent locally. Until pinned, `TASK_CACHE.writer_owner=UNATTRIBUTED` and t1
passes on the explicit declaration. No β-3 scoping decision should assume the writer's principal.

## eunomia request (rite-disjoint — surface, do not self-claim)
1. STRONG-cert of the Phase-α build (the t1–t5 contract + the FP receipts).
2. The **integration-boundary-fidelity N=2 promotion ruling**: this build applies the four-layer
   discipline at config altitude (layer mapping in the arch HANDOFF §N=2) — same satellite, different
   altitude; whether that satisfies "distinct incident at a distinct satellite" is the custodian's call.

## Watch-register (DEFER — unchanged owners)
PV-DRIFT/β-3 · γ-0 · the 128k legacy `task-cache/` disposition · t3's stated blind spots (concat/bytes
assembly) · the live-smoke forcing function (CHANGE-001, operator ack) · CHANGE-002..005 · UK-2 (#114) ·
SEAM-2/AC-6/CR-3 clocks · soak preconditions (IC checklist P1–P7) · Node20 non-deploy sweep (06-16) · #97.

## Rungs (never round up)
Phase-α = **merged** (deploys on the next satellite ride; the Python boundary becomes
structurally-unaddressable then). TF/IAM = detection-grade until β. The telos stays NOT
verified-realized (five-signal: SEAM-2, AC-6, valid soak, fallback flip).

Next `/frame` → `sre/framing`.
