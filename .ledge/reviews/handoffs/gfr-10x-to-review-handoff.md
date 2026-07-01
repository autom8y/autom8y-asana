---
type: handoff
status: open
from_rite: 10x-dev
to_rite: review
initiative_slug: gfr
authored_at: 2026-06-25
code_truth_anchor: origin/main b59a35f6 (engine commit 9a49a84 on feat/gfr-engine, worktree off origin/main)
realization_rung: proven-PENDING (engine code-complete + in-rite-validated; PROVEN unearned)
---

# Cross-Rite HANDOFF — GFR: 10x-dev → review

## Why this handoff exists

The GFR engine (identity-resolution core) is **code-complete and in-rite-validated** (qa-adversary GO, A-). Three certifications remain that a 10x-dev author **cannot self-issue** — they require a **rite-disjoint review-rite critic** (per `critic-substitution-rule` + `self-ref-evidence-grade-rule`; self-assessment caps MODERATE, STRONG needs the disjoint attester). This handoff routes those three to `review`. Do **not** dispatch review-rite specialists from 10x-dev; the operator runs the sync (below).

## What landed (the certifiable surface)

- Engine: `resolution/gfr/` (8 modules, 2549 LOC) + `tests/unit/resolution/gfr/` (88 tests, 96.94% cov, ruff+mypy clean). Commit `9a49a84` on `feat/gfr-engine` (worktree `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr`, off fresh `origin/main` b59a35f6). **Not pushed; no PR.**
- Cross-tenant collision (v1's CRITICAL PHI-leak) **closed by construction**: gid-exact `RowsRequest` with `join=None` structurally cannot reach `query/join.py:157` `keep='first'` dedup. Verified non-vacuous by 3 independent qa source-mutation probes.
- Build-on-top: zero diff to `query/{engine,join,compiler}.py`, `hydration.py`, and all 12 `@pytest.mark.scar` files (byte-identical to origin/main).
- Design artifacts: `.ledge/specs/gfr-tdd.md` (v2, GO-WITH-FIXES), `.ledge/decisions/ADR-gfr-seam1-ride-options.md`, `.know/telos/gfr.md` (ratified).

## The three certifications for review-rite (rite-disjoint)

### CERT-1 — PT-01: SEAM1 Option E ride ratification
- **Charge:** Option E (dual-read v2-first + on-fallback gid-identity re-assertion) is ADOPTED but **PROPOSED/UNRATIFIED** and **not yet built** in the engine. Enumerate each storage read-gate (`storage.py:1010,1195,1291,1372`) and confirm **no legacy-fallback path can serve a row WITHOUT the gid re-assertion firing**. The legacy project-only partition is multi-tenant — this is the Vector-A close.
- **Verdict artifact:** `.ledge/reviews/gfr-seam1-critic-verdict.md`
- **Gate:** must ratify before the storage-fallback wiring is built and before any cross-tenant-safe claim on the legacy path.

### CERT-2 — Vector B: gid→project_gid discriminator certification
- **Charge:** `_extract_project_gid` (`tier1.py:38`, reads `task.memberships[0].project.gid`) → `registry.lookup` (`tier1.py:117`) maps gid→project_gid→entity **TYPE**, NOT gid→tenant. `project_gid 1200653012566782` is **shared across tenants** (`entity_registry.py:445`). Certify the discriminator's tenant-discrimination under multi-tenant frames + lazy workspace discovery (ADR-0109) + registry bootstrap. **No ride option closes Vector B** — it is upstream of the entire fork.
- **Owner:** detection-rite / ProjectTypeRegistry maintainer.
- **Verdict artifact:** `.ledge/reviews/gfr-vectorB-discriminator-cert.md`

### CERT-3 — PT-05: tenant-correctness PROVEN (design pre-review now; full attestation post-sprint-F)
- **Charge:** the realization predicate — Offer gid → `company_id` (==`chiropractors.guid`) → minted `{guid}@appointments.contenteapp.com` round-trips through inbound `resolve_office_stage` (`email-booking-intake/.../resolve_office.py:53`) to the **CORRECT tenant**, with a **deliberately-broken cross-tenant fixture firing RED**. The unit-level anti-vacuity gate is GREEN; the **live** positive (real tenant, known-a-priori guid) + the live RED negative are a **sprint-F** build obligation (test `tests/integration/test_gfr_tenant_roundtrip.py` absent). PROVEN is **not** claimable until sprint-F lands AND this critic attests it is a real live test, not theater.
- **Verdict artifact:** `.ledge/reviews/gfr-tenant-correctness-critic-verdict.md`

## Realization rungs (G-RUNG; never round up)
`authored < emitting < alerting < proven < merged < live < protecting-prod`
- **Now: proven-PENDING.** Engine is in-rite-validated; PROVEN needs sprint-F + CERT-3. `merged`/`live`/`protecting-prod` are operator MINE levers.

## Defer registry (do not scope-creep; carried for the return to 10x-dev)
- **Enrichment (non-identity) field reads** — only `company_id` resolves today; office_phone/vertical/offer_id/asset_id stubbed (`UnresolvedError(no-identity-path)`). Build on the return, on a ratified foundation.
- **sprint-F** dogfood (PROVEN) — after CERT-1/CERT-2 ratify.
- **sprint-E** autom8y-core thin client — PROPOSE-only, PT-06 user-gated, separate repo (`repos/autom8y/sdks/python/autom8y-core`).
- Reverse resolution (DynamicIndex), writes (FieldResolver), bespoke optimizer — permanently out of scope.

## Carried flags
- **Telos anchor amendment (user-sovereign):** `.know/telos/gfr.md` round-trip anchor names outbound `_resolve_office_phone`; correct target is inbound `resolve_office_stage`. Predicate substance unchanged. Recommend amendment at next `/frame` — operator's call.
- **Minting producer UNBUILT** (R-6): `{guid}@appointments...` mint is external/unbuilt; sprint-F stubs at the boundary; GFR supplies the gid→guid half only.
- **Scar drift:** 44 markers / 12 files at HEAD (TDD said 42, original .know said 35). File count + zero-diff hold; `.know/design-constraints.md` refresh advised.
- **Pre-existing env gap (not GFR):** `tests/unit/lambda_handlers/test_workflow_handler.py` → `ModuleNotFoundError: autom8y_events`. Not a scar file; GFR has zero dependency. Flag to deps owner.

## Operator-run rite-switch (surface only; do NOT execute)
```bash
ari sync --rite=review   # SINGULAR; then ONE Claude Code restart
```
