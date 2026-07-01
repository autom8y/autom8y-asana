---
type: handoff
status: draft
from_rite: 10x-dev
to_rite: review
initiative_slug: gfr
authored_at: 2026-06-25
code_truth_anchor: origin/main b59a35f6 (feat/gfr-engine HEAD 70c3e8c6)
realization_rung: PROVEN-candidate (in-session integration GREEN + RED-firing cross-tenant negative, mutation-verified; PROVEN-attested pending review re-attestation + user-gated live-against-prod)
---

# Cross-Rite HANDOFF — GFR: 10x-dev → review (proof-hardening return)

## What this return delivered

The two items the prior review handoff routed back to 10x-dev are **done and in-rite-validated** (qa-adversary GO on both), advancing the engine from proven-PENDING to **PROVEN-candidate**.

### GAP-1 — Vector-A tenant safety is now ENGINE-OWNED (unlocks CERT-1 STRONG)
- `resolution/gfr/guard.py::assert_rows_tenant_identity(rows, business_gid)` — asserts **every** returned row's `gid == business_gid`; **fail-closed** on a missing gid key; raises `GuardViolationError`. Called from `engine.py::_resolve_identity_plan_async` after `execute_rows`, after the empty-frame check, before reading `response.data[0]`. Defense-in-depth **above** the frozen `query/engine.py:169` `df.filter` — never a replacement.
- **Independently proven non-vacuous:** qa disabled the guard → direct probe returned `company_id=G_WRONG` **silently** (the leak demonstrated); restored → `GuardViolationError`. Guard-removed → 3 bypass tests RED; reverted → green.
- Commit `b15c5259`. Suite 96 passed, 97.04%. Zero frozen/scar diff.

### sprint-F — tenant-identity round-trip (PROVEN-candidate)
- `tests/integration/test_gfr_tenant_roundtrip.py` (9 tests): Offer gid → `resolve_async` → `company_id == G_correct` → mint `{G_correct}@appointments.contenteapp.com` → **real** `resolve_office_stage` (imported byte-for-byte from co-located EBI src via existence-guarded `sys.path` insert; `pytest.skip` if absent) → `ctx.chiropractor_guid == G_correct`.
- **Negative (RED-firing, mutation-verified):** tenant B positively seeded as the `keep='first'` dedup-winner; DELTA `broken==G_B != v2==G_A` via the **real frozen `execute_join`**; round-trip of `{G_A}@…` resolves to A, never B. qa spoofed the anchor A→B → negative went RED (`G_B` observed); reverted → green.
- **Real, not theater:** `resolve_office_stage`/`resolve_async`/`execute_join`/mint all run unpatched; only the data-service network + substrate seams mocked. Real canary tenant `b167331c-…` (override-safe). Defenses D1 (override-key, mutation-verified), D3 (by-guid HIT not fallback), D4 (assert `chiropractor_guid`, never display fields) all hold.
- Commit `70c3e8c6`. Build-on-top pristine: 21 net-new Added files, zero modifications; 12 scar files + frozen `query/` untouched (scar suite 67 passed).

## Rung ledger (what review must now discharge)

| Cert | Prior | Now | Review action |
|---|---|---|---|
| CERT-1 Option E / Vector-A guard | CONDITIONAL | **STRONG-eligible** — the implicit-filter gap is closed; the guard is engine-owned + test-guaranteed | Issue STRONG on `gfr-seam1-critic-verdict.md` |
| CERT-2 Vector-B discriminator | CONDITIONAL | unchanged — confirmed type-routing-only; tenant safety is Vector-A (now hardened) | STRONG concurrence (or confirm Vector-A carries it); detection-rite concurrence optional |
| CERT-3 PT-05 tenant-correctness | DESIGN-SOUND (pre-review) | **PROVEN-candidate** — the live test design is now built + RED-verified at integration altitude | Re-attest to **PROVEN** after the user-gated live-against-prod run |

## What remains BEYOND review (do not round up)

- **User-gated live-against-prod run** (the input to PROVEN-attested): on a positively-selected REAL tenant, the round-trip with a **real `DataServiceClient`** (not AsyncMock) against live `get_business_by_guid_async`, real tenant creds so the asana side reads `company_id` from the live multi-tenant Business frame, and the real mint producer once NOTE-4/R-6's send-origination producer lands (stubbed until then). Assert the minted address resolves to the real tenant's guid; a different-tenant gid never mints this tenant's address.
- **PROVEN-attested** is the rite-disjoint review rite's (CERT-3 close), never the author's, never a green suite alone.

## DEFER registry (G-DEFER — carried, not scope-crept)
- **Enrichment (non-identity) field reads** — only `company_id` (identity) resolves; office_phone/vertical/offer_id/asset_id stub `UnresolvedError(no-identity-path)`. Build on the return after PROVEN.
- **sprint-E** autom8y-core thin client (PROPOSE-only, PT-06 user-gated, separate repo) — when it lands, the sprint-F `sys.path` insert is deleted for a real dependency edge.
- G-3/G-4 intake-path legacy-fallback debt note; reverse/writes/optimizer (permanent).

## Carried flags
- **Cosmetic provenance:** `test_gfr_tenant_roundtrip.py` docstring cites `.ledge/specs/gfr-sprintF-test-design.md`, which lives in the main tree `.ledge/` (where review reads), not on `feat/gfr-engine` (consistent with `.ledge`-in-main convention). Informational; test logic is self-documenting.
- **Telos anchor amendment (user-sovereign):** `.know/telos/gfr.md` round-trip anchor still names outbound `_resolve_office_phone`; real target is inbound `resolve_office_stage`. Amend at next `/frame`.
- **Pre-existing env gap (not GFR):** `tests/unit/lambda_handlers/test_workflow_handler.py` → `ModuleNotFoundError: autom8y_events`. Outside the changeset.

## Stays user-gated (MINE — surface, do not execute)
`git push feat/gfr-engine`, PR open, merges to main (asana / EBI / core — separate PRs), autom8y-core contract freeze (PT-06), prod deploy, the live-against-prod attestation run, the rite-switch sync.

## Operator-run rite-switch (surface only; do NOT execute)
```bash
ari sync --rite=review    # SINGULAR; then ONE Claude Code restart
```
