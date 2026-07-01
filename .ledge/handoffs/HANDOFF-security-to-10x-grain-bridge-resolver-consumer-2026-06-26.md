---
type: handoff
status: accepted
handoff_type: implementation
from_rite: security
to_rite: 10x-dev
date: 2026-06-26
initiative: grain-bridge-resolver
node: G-SEC gate -> thin asana consumer (WS-CONSUMER + WS-SKIP + WS-CANARY)
rung: "SA decision = security-attested MODERATE; seal = pentest-proven (proven-by-RED, teeth); verified_realized = UNATTESTED"
seam_state: "G-SEC APPROVE (conditional). SECURITY-ATTESTABLE-WITH-OPERATOR-CONFIRM-AT-C1 (not now-blocking). Consumer is credential-agnostic -> buildable pre-C1."
authority_anchors:
  - "auth origin/main = 1ad88e87 (autom8y/autom8y monorepo, PR #779 auth-s1: ebid reverse-resolver + oracle seal + c1b)"
  - "data origin/main = 9555bff4 (autom8y-data, PR #203 data-s2: resolve_guid_or_raise)"
  - "THREAT: autom8y/.ledge/reviews/THREAT-grain-bridge-resolver-2026-06-26.md"
  - "SA-ADR: autom8y/.ledge/decisions/ADR-grain-bridge-resolver-sa-shape-2026-06-26.md (proposed; apply operator-sovereign)"
  - "VERDICT: autom8y/.ledge/reviews/SEC-grain-bridge-resolver-2026-06-26.md"
  - "CANARY (exists, RUN): autom8y origin/main:services/auth/tests/test_identity_resolver_and_ebid_seal.py:219-300"
  - "phantom (NEVER cite): auth working tree 3149f5d7 (pre-S1, lacks the seal test); data 92d3606d (lacks resolve_guid_or_raise)"
---

# HANDOFF — security -> 10x-dev — grain-bridge-resolver thin consumer

## Grandeur Anchor
grain-bridge-resolver makes each ACTIVE customer's nightly leads read a POSITIVE single-tenant
per-business call so the shared fleet token is RETIRED without re-opening DATA-VAL-003. The
resolver halves are already merged + S1-reviewed; the G-SEC gate adjudicated the SA shape and
proved the oracle seal holds under the per-business + Lever-C1 posture. THIS handoff carries the
**thin asana consumer** build. `built != verified_realized` — fleet-retire + Lever C1 + prod deploy
stay the operator's.

## §1 — G-SEC verdict (security-attested, MODERATE)
**APPROVE (conditional). No blocking findings.** Seal HOLDS under the per-business + Lever-C1
enumeration posture, **proven-by-RED with teeth**. Self-grade MODERATE — STRONG requires a
rite-disjoint `review` critic to RE-RUN the canary (parallel, NOT a seam-blocker).

| Claim | Receipt |
|---|---|
| Two-sided canary RAN | `test_identity_resolver_and_ebid_seal.py` 11 passed @ worktree 1ad88e87 (NON-EMPTY `authorized_organizations` = the C1 posture) |
| GREEN arm | owned ebid -> 200 + single-tenant mint; `create_service_token(...business_id == resolved UUID)` |
| RED arm (= DATA-VAL-003 non-regression) | cross-tenant ebid -> uniform `404 AUTH-TEB-005`, `create_service_token.assert_not_called()` (no FGA RTT, no mint) |
| Uniform 404 (no id leak) | miss == out-of-set byte-identical; error echoes only the caller's own input |
| TEETH (non-vacuous) | removed membership check `tokens.py:825` -> RED arm MINTED a cross-tenant token (canary bit: 200!=404) -> restored byte-identical (sha256 BEFORE==AFTER, worktree clean) |
| ebid off the wire | c1b I5 pins BOTH mint delegates (`c1b_external_business_id_gate.py:32-40`); resolver returns a UUID consumed in-process, never crosses the response boundary |
| rate-limit | per-IP + per-credential before the ebid fold; `config.py:85 OAUTH_TOKEN_RATE_LIMIT = 10/min/credential` |
| is_fleet_read | `fleet_read_admission.py:74` strict `is True` fail-closed (30 passed incl. anti-IDOR override `data_service.py:1009` — JWT tenant key dominates client `office_phone`) |
| c1b seal-proof CI | **posture-INDEPENDENT** — holds across the flip with no gate change |

## §2 — SA-shape decision: **Option B — dedicated `leads-resolver` SA** (security-attested)
`business_scoped:true`, `authorized_organizations:[~75 ACTIVE]`, `[data:read]` ONLY.

**Why O2 over O1 (flip-in-place) — the decisive GR-6/T2 finding:** the existing
`asana-insights-export` SA holds a **LIVE `bypass_scope_enforcement` tuple** (`service-accounts.yaml:480`)
and the reconciler is **additive-write-only — no delete/prune** (`sa_reconciler.py:795`). A
half-applied flip ORPHANS that tuple -> Ace-pattern precedence (bypass checked before business_id)
-> fleet read re-opens -> **DATA-VAL-003 regresses**. O2 is born `business_scoped:true`, **NEVER holds
a bypass tuple**, so the highest-leverage threat (T2/GR-6) is **structurally absent** at no
least-privilege or blast-radius cost. O1 also contradicts the insights SA's own exemption, which
states per-business scoping "break[s] the fleet-wide rollup" (`service-accounts.yaml:506-509`). The
grain-bridge owns the LEADS path only; non-leads tables are the predecessor's domain.
*Apply (flip/provision) is operator-sovereign at C1 — see §5.*

## §3 — CONSUMER BUILD CONSTRAINTS (10x-dev MUST satisfy — verbatim)
- **SC-BUILD-1** — pin the consumer's requested scope to **`[data:read]` ONLY**, never `read:pii`
  (adjacency proof: `meta-lead-service` @ `service-accounts.yaml:392-434` carries `read:pii` ->
  unmasks PII on the leads surface). The leads read must not request `read:pii`.
- **SC-BUILD-2** — author the **two-sided discriminating canary** per the §4 RED-arm spec; the RED
  arm is a broken INPUT correctly refused, NEVER an injected defect; complete frame GREEN.
- **SC-BUILD-3** — pin the resolved key: the JWT tenant key dominates the client `office_phone`
  param (`data_service.py:1009`); the consumer must not assume its `office_phone` param controls the
  served tenant (anti-IDOR).
- **SC-BUILD-4** — secrets process-env-only (`SERVICE_CLIENT_ID`/`SERVICE_CLIENT_SECRET`,
  client_credentials grant); the consumer authenticates as the delegator and exchanges for the
  per-business token; **no re-mint**, no client_secret on disk.

## §4 — Canary RED-arm spec (for the consumer's two-sided canary)
- **RED**: a cross-tenant / un-owned `office_phone` -> the resolve+exchange path returns uniform
  `404` and **no per-business token is minted** (`create_service_token.assert_not_called()`) =
  DATA-VAL-003 non-regression. Pair with a TEETH probe (transiently disable the membership gate ->
  RED must flip to a mint -> restore byte-identical) to prove non-vacuity.
- **GREEN**: an owned (`authorized_organizations`-member) `office_phone` -> resolves -> single-tenant
  per-business token -> leads read succeeds.
- The skip taxonomy (WS-SKIP) must EMIT (log+metric+skipped-count), never silent-drop:
  `resolution_miss` (404 / the 116 numeric cohort) · `collision_conflict` (409) · `inactive_or_empty`
  · `mint_unavailable` (transient 429/5xx). `mint_unavailable` handles either SA rate-limit bucket
  identically (the consumer is credential-agnostic).

## §5 — Operator-held at C1 (NOT this build; surface, do not walk)
**Gate-placement: SECURITY-ATTESTABLE-WITH-OPERATOR-CONFIRM-AT-C1 (not operator-confirm-now).** The
consumer is credential-agnostic -> buildable pre-C1. The only "now" action is a **NON-BLOCKING NOTIFY:
dedicated-SA (Option B) provisioning carries lead-time — start it early so it does not block C1.**
C1-apply binds to the operator:
- **SC-C1-1 (BLOCKING at C1)** — GR-6 **bypass-tuple DELETION assertion**: the additive-write-only
  reconciler will NOT prune; the deletion of any orphaned `bypass_scope_enforcement` tuple must be
  *asserted*, not assumed. (Structurally absent under O2; re-arms if the operator deviates to O1.)
- **SC-C1-2 (C1 precondition)** — F-001 frozenset timing fast-follow: C1 widens the ~943ns out-of-set
  tuple-scan oracle (0->75 entries); pull the `frozenset` O(1) + branch-uniform-return fast-follow
  FORWARD as a C1 precondition. Bug-Bar LOW, eunomia-owned.
- flip-vs-dedicate execution, the ~75-org enumeration, fleet-token retirement, prod deploy, merge.

## §6 — Rungs (G-RUNG — not rounded)
`authored < emitting < alerting < proven < merged < live < protecting-prod`. SA decision =
**security-attested MODERATE**; seal = **pentest-proven MODERATE**; **verified_realized = UNATTESTED**
(eunomia's, rite-disjoint, LIVE, post-C1-apply + post-fleet-retire). STRONG on the SA decision + the
seal requires the rite-disjoint `review` critic to re-run the canary (RED+GREEN+teeth) and concur.

## §7 — DEFER watch-register (none scope-crept into the build)
- **DEFER-C1** (operator, BLOCKING at C1): GR-6 bypass-tuple DELETION assertion (SC-C1-1).
- **DEFER-C1** (precondition): F-001 frozenset timing fast-follow (SC-C1-2).
- **UV-P-DBCLEAN** (live): DATA-VAL-003 live re-probe at C1 — the RED arm is fixture-proven, not yet
  live-proven; 0 normalized collisions / `office_phone` UNIQUE PK re-probe at deploy.
- **WATCH SA-DEFERRAL**: if the operator defers dedicated-SA provisioning, the lead-time NOTIFY
  escalates — flag back before C1.
- **PARALLEL G-CRITIC**: rite-disjoint `review` canary re-run for STRONG elevation (does NOT gate the
  10x-dev build).
- verified_realized -> eunomia ADVISORY (post-fleet-retire, live).

## §8 — Next step
Operator walks `ari sync --rite=10x-dev` + CC restart for the thin consumer build (WS-CONSUMER +
WS-SKIP + WS-CANARY), built from `origin/main` (auth 1ad88e87 / data 9555bff4), honoring SC-BUILD-1..4.
Security does NOT dispatch 10x-dev specialists from here.
