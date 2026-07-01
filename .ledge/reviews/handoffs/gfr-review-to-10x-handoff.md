---
type: handoff
status: draft
from_rite: review
to_rite: 10x-dev
initiative_slug: gfr
authored_at: 2026-06-25
code_truth_anchor: origin/main b59a35f6 (engine commit 9a49a842 on feat/gfr-engine)
realization_rung: proven-PENDING (3 certs CONDITIONAL/DESIGN-SOUND; none RED; none STRONG yet)
---

# Cross-Rite HANDOFF — GFR: review → 10x-dev

## Verdict of the rite-disjoint certification

Three certs discharged by the review rite (rite-disjoint critic of the 10x-dev engine). **Overall: CONDITIONAL — no cert RED.** The engine's identity-resolution architecture is structurally sound for the current GFR call trace. STRONG/PROVEN is blocked only by named, cheap, in-scope work. Verdict artifacts: `.ledge/reviews/gfr-seam1-critic-verdict.md`, `gfr-vectorB-discriminator-cert.md`, `gfr-tenant-correctness-critic-verdict.md`, consolidated `gfr-certification-case-file.md`.

## The load-bearing reframe (changes the risk model)

The handoff into review treated **Vector B** (the gid→project_gid discriminator) as an open cross-tenant certification. The review **disproved that framing, in the engine's favor**: the discriminator routes gid→entity-**TYPE** only (all tenants of a type share one project GID — `entity_registry.py:445`). It is **orthogonal** to tenant selection. **Tenant safety rests on Vector A** — the gid-exact `RowsRequest(where=gid==business_gid, join=None)` whose `business_gid` comes from the parent-chain anchor (`entry.py:66-126`, `engine.py:85-89`). Because Asana gids are globally unique, that predicate matches ≤1 row. Vector B cannot, on its own, produce a cross-tenant leak (a failure yields wrong-entity-type or `UnresolvedError`, never wrong-tenant data).

## Rung ledger (what this rite ratified vs left pending)

| Cert | Verdict | Rung | Why not STRONG/PROVEN |
|---|---|---|---|
| CERT-1 Option E | CONDITIONAL | proven-PENDING | Safe today, but the re-assertion is **implicit** in the frozen query filter, not engine-owned. **GAP-1** closes it. |
| CERT-2 Vector-B | CONDITIONAL | proven-PENDING | Tenant safety confirmed on Vector A (sound). STRONG needs detection-rite concurrence on the structural argument **+** the RED fixture. |
| CERT-3 PT-05 | DESIGN-SOUND (pre-review) | proven-PENDING | Design passes all 4 anti-theater criteria; PROVEN needs the sprint-F **live** test + post-build re-attestation. |

## Work routed to 10x-dev (the return)

1. **GAP-1 (unlocks CERT-1 STRONG; ~1 hour):** add an explicit post-execute guard in `resolution/gfr/engine.py::_resolve_identity_plan_async` (or `guard.py`) asserting **every** row in `response.data` has `gid == anchor.business_gid` — making Vector A's tenant safety engine-owned and test-guaranteed, not borrowed from `query/engine.py:169`. Add a test that fires RED if a mock provider returns an unfiltered multi-tenant frame.
2. **sprint-F (the PROVEN gate; gates CERT-2 + CERT-3):** build `tests/integration/test_gfr_tenant_roundtrip.py` per `gfr-tdd.md` §12, MUST include:
   - Positive: positively-selected REAL tenant, a-priori-known `G_correct`; `resolve_async(O_correct,[company_id])==G_correct`; round-trip via `resolve_office_stage`, assert on `ctx.chiropractor_guid==G_correct` (`resolve_office.py:92`), **never** display fields (`office_name`/`office_phone`, set at `:141/:169-170`).
   - Negative (anti-vacuity): collision frame with tenant B positively ordered as the `keep='first'` dedup-winner; broken-path companion via real `execute_join` returns `G_B` (RED); v2 path returns `G_A`; DELTA assertion `broken==G_B != v2==G_A`; QA gate INSPECTS dedup ordering, not assertion text.
   - Defenses: override-key on BOTH `_DEFAULT_OVERRIDES` (U+200B-prefixed key, `:46-50`, applied to full address at `:80` BEFORE `@`-split) and injected `guid_overrides` (`:55`); `guid_phone_mapping` neutralized (empty / `G_correct`-absent), assert clean by-guid HIT at `:111` (not the `:121` fallback).
3. **Deferred (G-DEFER — build on the ratified base, do not scope-creep):** enrichment (non-identity) field reads (only `company_id` wired today); sprint-E autom8y-core thin client (PROPOSE, PT-06 MINE); G-3/G-4 intake-path legacy-fallback debt note (real if `legacy_fallback_enabled=True` on the intake path; out of GFR scope); reverse/writes/optimizer (permanent).
4. **Operator-sovereign:** telos round-trip anchor amendment (names outbound `_resolve_office_phone`; real target inbound `resolve_office_stage`) — amend at next `/frame`.

## Optional parallel branch — detection-rite (CERT-2 STRONG concurrence)
Detection-rite owner reviews `gfr-vectorB-discriminator-cert.md`, confirms Vector B is type-routing-only (can't misroute a Business/Unit task cross-tenant), issues a concurrence artifact. **Not load-bearing for tenant safety** (Vector A + GAP-1 carry that); it is added rigor. A rite-switch (MINE lever).

## Stays user-gated (MINE — surface, do not execute)
`git push feat/gfr-engine`, PR open, autom8y-core contract freeze (PT-06), prod deploy, the rite-switch sync.

## Operator-run rite-switch (surface only; do NOT execute)
```bash
ari sync --rite=10x-dev    # SINGULAR; then ONE Claude Code restart
```
