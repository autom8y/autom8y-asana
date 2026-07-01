---
type: handoff
status: accepted
handoff_type: execution
from_rite: review
to_rite: releaser
date: 2026-06-26
initiative: grain-bridge-resolver
node: consumer seal STRONG-attested -> operator-walked merge of PR #160
rung: "consumer seal = STRONG (rite-disjoint, independently re-run); verified_realized = [UNATTESTED — DEFER-POST-HANDOFF]"
seam_state: "STRONG-path. Merge of PR #160 is operator-held; this handoff requests scheduling/sequencing, NOT auto-merge."
authority_anchors:
  - "VERDICT: autom8y-asana/.ledge/reviews/grain-bridge-consumer-strong-verdict.md (review-rite, rite-disjoint; Grade A; cross_stream_concurrence: true)"
  - "PR autom8y/autom8y-asana#160 OPEN @ 10ff40f2 MERGEABLE, base main, 16 files 2032+/157- (re-verified live this seam)"
  - "independent re-run worktree: /tmp/wt-review-grain-bridge-canary @ 10ff40f2 (fresh, disjoint from the builder's wt)"
  - "TEETH sha256 BEFORE==AFTER 3164b34eace5a32763412ceecd144950673137b3846bbb10f2d100e7d8f3e39c (tree clean post-restore)"
  - "consumed contract: auth autom8y/autom8y origin/main f2a95959 (moved 1ad88e87->f2a95959; consumed seal surface diff EMPTY = byte-stable); autom8y-data origin/main dd4566e5"
  - "G-SEC verdict (cross-repo): autom8y origin/main:.ledge/reviews/SEC-grain-bridge-resolver-2026-06-26.md (SA=Option B dedicated leads-resolver SA)"
---

# HANDOFF — review -> releaser — grain-bridge consumer merge (STRONG-path)

## Grandeur Anchor
grain-bridge-resolver makes each ACTIVE customer's nightly leads read a POSITIVE single-tenant
per-business call so the shared fleet token is RETIRED without re-opening DATA-VAL-003. The consumer
seal is now **STRONG** — independently re-run rite-disjoint. THIS handoff requests the operator-walked
merge of PR #160. `built != verified_realized`; this is NOT the gfr telos proof; Lever C1, fleet-retire,
prod deploy, and the merge lever itself stay the operator's.

## §1 — Gate-passed: consumer seal STRONG (review-rite, rite-disjoint, independently re-run)
The review pantheon (disjoint from the 10x-dev builder AND the security pantheon) RE-FIRED the
two-sided canary first-party in a fresh worktree (`/tmp/wt-review-grain-bridge-canary @ 10ff40f2`) —
it did NOT read qa's run. All five STRONG criteria cleared (verdict: `grain-bridge-consumer-strong-verdict.md`):

| Criterion | Receipt |
|---|---|
| RED (= DATA-VAL-003 non-regression) | `test_tc_red_cross_tenant_refused_no_mint_no_read` PASSED — cross-tenant -> 404 AUTH-TEB-005 -> `MintResolutionMiss` -> `succeeded==0`, `get_leads_async.calls==[]` |
| GREEN | `test_tc_green_owned_resolves_and_reads` PASSED — owned -> mint + `get_leads_async` -> `succeeded==1` |
| TEETH (discriminating power) | mutated the seal gate (404->200 leaked token) -> `3 failed` (RED/minter-RED/TEETH bit); restored byte-identical (sha256 `3164b34e…` pre==post; tree clean) |
| SCOPE | `test_tc_scope_no_arm_ever_requests_read_pii` PASSED — `["data:read"]` only, never `read:pii` |
| FINDING-2 anti-IDOR | `data_service.py:1009` @ dd4566e5 — JWT tenant key dominates client `office_phone`; consumer authors no competing resolver (G-PROPAGATE) |

Plus: auth seal surface byte-stable (`git diff 1ad88e87..f2a95959 -- identity_resolver.py tokens.py service-accounts.yaml` = empty); no orphan resolver. Grade **A**; `cross_stream_concurrence: true`.

## §2 — Acceptance criteria for the merge (operator-walked)
- **Merge PR #160** (`feat/grain-bridge-leads-consumer` @ 10ff40f2) to `main` — the lever is the operator's; this handoff requests scheduling, not auto-merge.
- Pre-merge: re-confirm PR #160 OPEN/MERGEABLE + CI green (the build's local gate was green: pytest spine + mypy --strict + ruff + the two-sided canary; CI re-runs on merge per repo convention). Squash per the #158/#114 precedent.
- The lambda entrypoint is **flag-gated + not prod-scheduled** — merging does NOT activate the consumer; activation is downstream (Lever C1 + scheduling), operator-held.

## §3 — Rungs (G-RUNG — Gate C honored)
- consumer = **built** (PR #160 OPEN @ 10ff40f2 — `gh pr view 160`).
- in-rite verification = **MODERATE** (qa 14/14).
- consumer seal = **STRONG** (verdict `grain-bridge-consumer-strong-verdict.md`, re-run receipts §1).
- **`verified_realized` = [UNATTESTED — DEFER-POST-HANDOFF]** — eunomia, LIVE, post-C1 + post-fleet-retire. The STRONG canary certifies the cross-tenant-refusal *control* on independent evidence; it does NOT certify live realized value.
- **NOT the gfr telos proof** — gfr `verified_realized` (`.know/telos/gfr.md:79-89`) is the send-origination `{guid}@appointments.contenteapp.com` round-trip at a distinct altitude, eunomia's to close. Do NOT round.

## §4 — Operator-held / downstream of the merge (surface, do not auto-walk)
- **Lever C1 apply** — SC-C1-1 (GR-6 bypass-tuple DELETION assertion) + SC-C1-2 (F-001 frozenset fast-follow as a C1 precondition). Gates fleet-token retirement.
- **Dedicated `leads-resolver` SA provisioning** (Option B, per the G-SEC verdict) — lead-time; precedes fleet-retire; start early.
- **Fleet-token retirement, prod deploy, consumer scheduling/activation** — operator-sovereign.
- **UV-P-DBCLEAN** — DATA-VAL-003 live re-probe at C1; eunomia/live.

## §5 — FINDING-1 (LOW, non-blocking — parallel route to 10x-dev/principal-engineer)
`collision_conflict` is the only WS-SKIP class without a consumer-altitude counted-emit test (the
production path `leads_consumer.py:223-225` is present + correct; the gap is test coverage of a
non-cross-tenant skip class). Author a consumer-loop test driving 409 -> `MintCollision` -> counted
`skipped_by_class[COLLISION_CONFLICT]` to close the 4/4 EMIT matrix. **Does NOT block STRONG or the merge.**

## §6 — Next step
Operator walks `ari sync --rite=releaser` + CC restart to schedule/execute the PR #160 merge (the merge
lever stays operator-held). FINDING-1 routes in parallel to 10x-dev/principal-engineer. The
post-merge realization (Lever C1 -> dedicated-SA -> fleet-retire -> live DATA-VAL-003 re-probe ->
eunomia `verified_realized`) is the operator's downstream ladder.
