---
type: handoff
status: draft
from_rite: review
to_rite: 10x-dev
initiative_slug: gfr
authored_at: 2026-06-25
code_truth_anchor: origin/main b59a35f6 (feat/gfr-engine HEAD 70c3e8c6)
realization_rung: PROVEN-candidate (CERT-1 STRONG, CERT-3 PROVEN-candidate re-attested, CERT-2 accepted; PROVEN-attested pending the user-gated live-against-prod run)
---

# Cross-Rite HANDOFF — GFR: review → 10x-dev (certification complete)

## What the review rite ratified (rite-disjoint critic of the 10x-dev engine)

All three certs advanced, each on an independently-fired mutation-probe (G-THEATER satisfied — no green-suite-alone):

- **CERT-1 → STRONG** (`gfr-seam1-critic-verdict.md`, status: accepted). GAP-1 CLOSED: the Vector-A guard is engine-owned (`guard.py:183` `assert_rows_tenant_identity`, called `engine.py:138` before any field read), every-row, fail-closed on missing gid. RED-on-bypass: disabling it → 4 tests RED (`DID NOT RAISE GuardViolationError`, leak `data[0]={B_WRONG,G_WRONG}`); restore → 44 GREEN, clean tree.
- **CERT-2 → ACCEPTED, Fork (a)** (`gfr-vectorB-discriminator-cert.md`, status: accepted). Vector-B is **type-routing-only** (gid→project_gid→entity_TYPE; project_gid tenant-shared across 12 entity types); tenant safety rests on **Vector-A, hardened by GAP-1**. A defective discriminator yields wrong-type or `UnresolvedError`, never cross-tenant. Detection-rite STRONG concurrence on Vector-B is **additive rigor, NOT load-bearing** — not a blocking gate.
- **CERT-3 → PROVEN-candidate re-attested** (`gfr-tenant-correctness-critic-verdict.md`, status: accepted). Anchor-spoof A→B → 2 tests RED (`UnresolvedError: business-row-not-found` + `v2 company_id == G_B`); restore → 9 GREEN, clean tree. `resolve_office_stage` called **unpatched** (6 sites; only the data-service + substrate seams mocked); real canary tenant `b167331c-…`; asserts on `ctx.chiropractor_guid`, never display fields.

Consolidated: `gfr-certification-case-file.md` (status: accepted, g_rung: PROVEN-candidate).

## Rung ledger
`authored < emitting < alerting < proven < merged < live < protecting-prod`
- **Now: PROVEN-candidate.** CERT-1 STRONG-ratified; CERT-3 PROVEN-candidate at integration altitude; CERT-2 accepted.
- **PROVEN-attested** is **USER-GATED** and additionally blocked on an external dependency (see below). `merged`/`live`/`protecting-prod` are MINE.

## Work routed to 10x-dev (deferred-buildable, none blocking)
1. **Enrichment (non-identity) field reads** — `office_phone`/`vertical`/`offer_id`/`asset_id` currently stub `UnresolvedError(no-identity-path)`. Build on the now-ratified identity foundation to complete the original POC field set. The hard/risky half (identity + cross-tenant correctness) is done; this is incremental, lower-risk reads off the resolved entity row.
2. **sprint-E** autom8y-core thin client (PROPOSE-only, PT-06 user-gated, separate repo). When it lands, delete the `sys.path` insert in `test_gfr_tenant_roundtrip.py` for a real dependency edge.
3. **Live-run harness prep** — wire the integration test so the only swap for the live run is `AsyncMock` → real `DataServiceClient` + real creds (the test is already structured for this).
4. Optional (LOW, not blocking): Vector-B STRONG candidate items for detection-rite (discriminator completeness, PT-05 adversarial fixture formalization, `_match_process_type_contains` scope); G-3/G-4 intake-path debt note.

## The PROVEN-attested gate (USER + external)
The live-against-prod run requires: real `DataServiceClient` against the live chiropractors table, real tenant creds, AND the **mint producer** that emits `{guid}@appointments.contenteapp.com` — which is **UNBUILT/external** (telos NOTE-4 / R-6). Until that producer lands and the user runs the live round-trip with creds, PROVEN-attested is unreachable. The integration test stubs the mint at that boundary; the gid→company_id→guid half is fully live.

## Stays user-gated (MINE — surface, do not execute)
`git push feat/gfr-engine`, PR open / merges to main (asana / EBI / core — separate PRs), autom8y-core contract freeze (PT-06), prod deploy, the live-against-prod attestation run, the rite-switch sync.

## Carried flags
- **Telos anchor amendment (user-sovereign):** `.know/telos/gfr.md` round-trip anchor names outbound `_resolve_office_phone`; real target is inbound `resolve_office_stage`. Amend at next `/frame`.
- **Pre-existing env gap (not GFR):** `tests/unit/lambda_handlers/test_workflow_handler.py` → `ModuleNotFoundError: autom8y_events`; and `uv run` is CodeArtifact-401-blocked this session (use `./.venv/bin/python -m pytest`).

## Operator-run rite-switch (surface only; do NOT execute)
```bash
ari sync --rite=10x-dev    # SINGULAR; then ONE Claude Code restart
```
