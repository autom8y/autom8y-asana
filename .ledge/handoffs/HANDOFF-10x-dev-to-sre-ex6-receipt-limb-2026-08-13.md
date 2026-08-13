---
type: handoff
artifact_id: HANDOFF-10x-dev-to-sre-ex6-receipt-limb-2026-08-13
schema_version: "1.0"
source_rite: 10x-dev
target_rite: sre
handoff_type: implementation
priority: high
blocking: false
initiative: exec-insight-delivery
created_at: "2026-08-13T10:57:05Z"
status: pending
session_id: session-20260813-104852-686d6d30
source_artifacts:
  - .ledge/reviews/GATE-pt07-phase3-2026-08-13.md
  - .knossos/worktrees/ex-6-rail-distinguishability/.ledge/reviews/CRITIQUE-rail-distinguishability-2026-08-13.md (lands with PR #363)
  - .ledge/reviews/CRITIQUE-recurring-readout-build-2026-08-13.md
provenance:
  - { source: "GATE-pt07-phase3-2026-08-13.md (Phase-3 held on operator+monorepo)", type: artifact, grade: moderate }
  - { source: "CRITIQUE-rail-distinguishability-2026-08-13.md hop-one-past #1/#2", type: artifact, grade: strong }
evidence_grade: moderate
---

# HANDOFF — 10x-dev → sre · EX-6 receipt limb (UV-P-C-3 discharge, monorepo-bound)

**Routing, not an execution order.** The exec-insight-delivery wave built EX-6's
DESIGN limb (rail distinguishability, block budget, overflow, delivery-receipt
shape) and EX-5's generation mechanism (readout + `report_generated`), both landed
in autom8y-asana (PRs #362, #363). The **RECEIPT limb** — the actual live delivery
and UV-P-C-3 discharge — **cannot complete in this wave**: it requires changes to
the **monorepo** ASR service, which the wave kit places OUT OF SCOPE ("all six
sprints land in autom8y-asana; no monorepo PR"), plus an operator-gated live render
and a live Slack post. It routes here to the sre receipt-limb owner
(`observability-engineer` + whoever owns `services/account-status-recon` in the
monorepo). Whether it executes now or later is the operator's call — this artifact
records the routing.

## §1 What is already built (autom8y-asana, landed)

- **EX-6 `rail_delivery/`** (PR #363): D-1..D-4 distinguishability (D-4 at the
  fallback-`text` notification surface), per-message block budget with a never-silent
  overflow marker, and a `DeliveryReceipt` shape that mirrors `report_posted` **plus a
  real `content_hash`** (canonical sorted-key sha256 over `{blocks,text}`).
- **EX-5 `readout/`** (PR #362): the generation mechanism produces a postable
  `GeneratedOccurrence` and emits `report_generated` with a real `content_hash`
  (sha256 over the assembled **blocks**), `assembled_by`/`human_in_loop` as structural
  constants, keyed on `invocation_id`. Joins GREEN with EX-4's `rung_receipts`
  (landed PR #361) over synthetic data.

## §2 Assessment / implementation items

```yaml
items:
  - id: REC-001
    summary: >-
      LOAD-BEARING ENTRY CONDITION — reconcile the content_hash canonicalization
      between EX-5 (hashes blocks) and EX-6 (hashes {blocks,text}). If they differ,
      EX-4's join reads EVERY honest delivery as a swap (content_hash_mismatch).
    priority: critical
    design_references:
      - src/autom8_asana/readout/generation.py (EX-5 content_hash over blocks)
      - src/autom8_asana/observability/rail_delivery/delivery_receipt.py (EX-6 content_hash over blocks,text)
    notes: >-
      Pick ONE canonicalization (recommend: the delivery-side {blocks,text} form,
      since text is the D-4 notification surface and is part of what was delivered)
      and make both sides call it. This must land BEFORE the live join is trusted.
  - id: REC-002
    summary: >-
      Wire the EX-5 readout into the ASR delivery egress (send_blocks) and emit
      report_generated + content_hash on the report_posted event. MONOREPO change.
    priority: high
    design_references:
      - src/autom8_asana/readout/generation.py (the payload + report_generated emission)
      - "monorepo origin/main:services/account-status-recon/... (send_blocks / report_posted — cite via git show origin/main only)"
    notes: >-
      MONOREPO TRAP: /Users/tomtenuta/Code/a8/a8/repos/autom8y is on a divergent
      branch (281 files differ from origin/main) with a sibling session actively
      committing. Always `git show origin/main:<path>` for any monorepo read. This
      item is the out-of-scope-for-this-wave work; a monorepo PR is {strict:true,
      enforce_admins:false} — an armed MERGE auto-merge silently never fires there.
  - id: REC-003
    summary: >-
      Splice content_hash into EX-4's RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA.delivery so
      the join can actually check machine-vs-human assembly (today it falls back to
      block_count — EX-4's documented CONCERN-1 delivery-side residual).
    priority: high
    design_references:
      - src/autom8_asana/observability/rung_receipts/schema.py (EX-4 delivery schema, landed)
      - src/autom8_asana/observability/rail_delivery/delivery_receipt.py (the field to consume)
    notes: >-
      This is the observability-engineer edit the EX-6 critic named (hop-one-past #2).
      autom8y-asana-local (EX-4 schema is in this repo) — not a monorepo change.
  - id: REC-004
    summary: >-
      Discharge UV-P-C-3 — one readout-class payload (SDK-built, multi-block,
      approaching the 50-block ceiling) posts to #account-health and is observed via
      report_posted / block_count. Needs EX-5's real live render + a live post.
    priority: high
    design_references:
      - .knossos/worktrees/ex-6-rail-distinguishability/.ledge/specs/SPEC-ex6-rail-distinguishability-design-2026-08-13.md (exit crit 3)
    notes: >-
      OPERATOR-GATED: the live render is a real POST /v1/query/offer/rows call
      (CR-5, operator/credential-gated), and the Slack post to #account-health is a
      live delivery. R-7 makes Slack delivery autonomous for the machine rail, but
      the live render (credential) and the real occurrence are the operator's. The
      tick census proves the transport for a hand-built 3-block abort that bypasses
      report.py — that is NOT the same proof (a real readout-class payload is required).
```

## §3 Fences that bind (kit §3, verbatim where load-bearing)

1. **CR-1** — all three Asana write classes are operator-reserved. No agent writes
   to the live board.
2. **CR-5** — no credential material. On encountering it, stop, report path+fact
   only. The live render (REC-004) is credential-bearing and operator-only.
3. **MONOREPO TRAP** — `/Users/tomtenuta/Code/a8/a8/repos/autom8y` is on a divergent
   branch (281 files differ from origin/main) with a sibling session actively
   committing. Always `git show origin/main:<path>` for any monorepo read.
4. **C-7 / R-7** — Slack delivery to `#account-health` is autonomous for the machine
   rail (R-7); addressing the CEO/cofounder is operator-performed. The rail autonomy
   is the producer's, not authority to address a reader.

## §4 The critical ordering

REC-001 (content_hash parity) is the entry condition: without it, REC-002/003/004
produce a join that reads every honest delivery as a swap. Do REC-001 first, then
REC-003 (schema splice, in-repo), then REC-002 (monorepo wiring), then REC-004 (the
live discharge, operator-gated).

## §5 Response

Response artifact: `HANDOFF-RESPONSE-sre-to-10x-dev-2026-08-13.md`. Status:
pending → in_progress (accept) → completed (UV-P-C-3 discharged with an observed
`report_posted`/`block_count`).
