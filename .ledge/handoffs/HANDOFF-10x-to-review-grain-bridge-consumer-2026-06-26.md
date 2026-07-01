---
type: handoff
status: accepted
handoff_type: validation
from_rite: 10x-dev
to_rite: review
date: 2026-06-26
initiative: grain-bridge-resolver
node: thin asana leads consumer (WS-CONSUMER + WS-SKIP + WS-CANARY) -> rite-disjoint STRONG canary re-run
rung: "consumer = built (PR #160 opened, not merged); in-rite verification = MODERATE (14/14); seal STRONG-elevation = PENDING review critic; verified_realized = UNATTESTED"
seam_state: "BUILT + PR opened. Disjoint review critic RUNs the authored two-sided canary for STRONG. Lever C1 + merge + fleet-retire stay operator-held."
validation_scope:
  - "RUN the two-sided discriminating canary rite-disjoint (GREEN owned->mint+leads / RED cross-tenant->404+no-mint = DATA-VAL-003 non-regression / TEETH gate-disable flips RED->mint then restores byte-identical / SCOPE data:read-only). It is AUTHORED + in-rite GREEN; the STRONG seal requires the disjoint RUN."
  - "FINDING-2 (UV-P): the SC-BUILD-3 anti-IDOR JWT-dominance anchor (data_service.py:1009) is CROSS-REPO; verify it live against the MERGED auth(1ad88e87)+data(dd4566e5) surface (asana consumes, does not enforce)."
authority_anchors:
  - "PR autom8y/autom8y-asana#160 OPEN, base main, head feat/grain-bridge-leads-consumer @ 10ff40f2, MERGEABLE, 16 files 2032+/157- (verified live; zero stowaways)"
  - "consumed contract (MERGED): auth autom8y/autom8y origin/main 1ad88e87 (PR #779); autom8y-data origin/main dd4566e5 (moved 9555bff4->dd4566e5 mid-build, #206 binding-verify endpoint; re-verified)"
  - "asana origin/main b9648de4 (build base)"
  - "TDD: autom8y-asana/.ledge/specs/TDD-grain-bridge-leads-consumer-2026-06-26.md ; ADR: autom8y-asana/.ledge/decisions/ADR-grain-bridge-leads-consumer-2026-06-26.md"
  - "G-SEC verdict (cross-repo): autom8y origin/main:.ledge/reviews/SEC-grain-bridge-resolver-2026-06-26.md (SA=Option B; the seal proof)"
  - "seal canary mirrored from: autom8y origin/main:services/auth/tests/test_identity_resolver_and_ebid_seal.py:219-300"
  - "phantom (NEVER cite): auth working tree 3149f5d7; data 92d3606d"
---

# HANDOFF — 10x-dev -> review — grain-bridge thin leads consumer (validation)

## Grandeur Anchor
grain-bridge-resolver makes each ACTIVE customer's nightly leads read a POSITIVE single-tenant
per-business call so the shared fleet token is RETIRED without re-opening DATA-VAL-003. The consumer
is BUILT (PR #160). THIS handoff hands the **authored two-sided canary** to the rite-disjoint `review`
critic to RUN for the STRONG seal. `built != verified_realized`; Lever C1, fleet-retire, prod deploy,
merge stay the operator's.

## §1 — What's built (consumer = `built`, PR #160 opened, not merged)
PR `autom8y/autom8y-asana#160` @ `10ff40f2` (OPEN, base main, MERGEABLE, 16 files 2032+/157-, no
stowaways). New `BusinessTokenMinter` + `PerBusinessTokenProvider` + the leads orchestrator
(`leads_consumer.py`) + `leads_ebid.py` + `leads_skip.py` + the flag-gated lambda entrypoint +
6 test files. New dep `autom8y-guid>=0.1.0` (pinned, published to CodeArtifact, third consumer).

| Gate | Receipt |
|---|---|
| Two-sided canary (in-rite) | `5 passed` — GREEN owned->200 mint+leads · RED cross-tenant->404 + `get_leads_async.assert_not_called()` · minter-RED · TEETH (gate-disable flips 404->200, restored byte-identical) · SCOPE data:read-only |
| TEETH mutation-kill (qa-adversary) | mutated 404->"MUTANT-LEAKED-TOKEN" -> `3 failed` (RED/minter-RED/TEETH bit); restored byte-identical `sha256 f3536e49…` pre==post, tree clean |
| New-test spine | `45 passed` |
| mypy --strict | `Success: no issues found` | 
| ruff check + format --check | `All checks passed!` / formatted |
| strictly-additive | `17 failed, 13474 passed` — the 17 are PRE-EXISTING env gaps (secretspec CLI; missing bot-PAT/workspace env), import none of the new modules; touched surface `701/672 passed` |

## §2 — The chain, resolved live (no HALT; bootstrap intact)
- **ebid derivation RESOLVED against the code:** `external_business_id = normalize_chiropractor_guid(business.company_id)` where `company_id == chiropractors.guid` (`gfr/truth_source.py:52`), held LOCALLY on the resolved Business (`models/business/business.py:263,304`). **No guid fetch -> bootstrap INTACT.** office_phone = the read key + report label; `company_id`(==guid) = the ebid input. (Resolves the prose ambiguity: the SA-ADR's `normalize(guid)` is authoritative; the threat-model's "office_phone->normalize" was loose shorthand.)
- **leads read = `get_leads_async(office_phone)` (`clients/data/client.py:1245`)** — NOT `get_insights_async` (grandeur shorthand corrected; that serves the other insights-factory tables).
- **exchange-business** `tokens.py:524-530`/`:808-814`(ebid fold)/`:825-857`(oracle seal->404 AUTH-TEB-005, no mint)/`:762-779`(429 TEB-006).
- **SDK gap (honest):** `token_manager.py:355-368` exchange sends an EMPTY body = the FLEET path; business-scoped exchange is a future SDK API absent at the pin -> the build authored a thin `BusinessTokenMinter` (no fleet fallback).
- **G-PREMISE catch:** `autom8y-data` main moved `9555bff4 -> dd4566e5` mid-build (#206); every depended-on element re-verified present.

## §3 — Validation scope for the review critic (RUN, rite-disjoint)
1. **RUN the two-sided canary** disjoint from this builder AND the security pantheon: GREEN owned ->
   mint + `get_leads_async` succeeds; RED cross-tenant -> uniform 404 + `get_leads_async` NOT called
   (= DATA-VAL-003 non-regression); TEETH (transient gate-disable flips RED->mint, restore byte-identical);
   SCOPE (`data:read` only, never `read:pii`). Mirror `test_identity_resolver_and_ebid_seal.py:219-300`.
2. **FINDING-2 cross-repo JWT-dominance**: verify the anti-IDOR `data_service.py:1009` (JWT tenant key
   dominates client `office_phone`) live against the MERGED auth `1ad88e87` + data `dd4566e5` surface —
   asana consumes this guard (G-PROPAGATE), it does not enforce it.

## §4 — SC-BUILD-1..4 satisfaction (security-attested constraints, bound)
- **SC-BUILD-1** `requested_scopes` frozen `["data:read"]` per mint (fresh list, never `read:pii`) — asserted at the minter + the canary SCOPE arm.
- **SC-BUILD-2** the two-sided discriminating canary is authored (RED a broken INPUT correctly refused; GREEN owned passes) — §3.
- **SC-BUILD-3** `PerBusinessTokenProvider`; the consumer never assumes `office_phone` controls the served tenant; `test_leads_path_uses_per_business_provider_never_fleet` asserts NOT `ServiceTokenAuthProvider`. (Cross-repo JWT-dominance = FINDING-2, review RUNs it.)
- **SC-BUILD-4** `SERVICE_CLIENT_ID` + `resolve_secret_from_env("SERVICE_CLIENT_SECRET")`, Basic-auth exchange; secret never on disk/logs; single POST per mint = no re-mint.

## §5 — QA findings (no HIGH/CRITICAL; release-eligible at this rung)
- **FINDING-1 [LOW, test-gap -> principal-engineer]**: `collision_conflict` is the only WS-SKIP class not driven to a counted emit at consumer altitude (verified by inspection `leads_consumer.py:223-225,256-258` + minter altitude `test_mint_409_raises_collision`). Add a consumer test driving a 409 -> counted `collision_conflict` skip to close the 4/4 EMIT matrix. NOT a HALT.
- **FINDING-2 [INFO, UV-P]**: cross-repo anti-IDOR anchor -> folded into §3 validation_scope.
- **FINDING-3 [INFO, defensive]**: reconciliation invariant `leads_consumer.py:165` is a bare `assert` (stripped under `-O`); correctness structurally guaranteed by the counting loop. No action.

## §6 — Rungs (G-RUNG — not rounded)
- consumer = **built** (PR #160 opened, not merged).
- in-rite verification = **MODERATE** (qa 14/14; self-grade cap honored, G-CRITIC).
- seal STRONG-elevation = **PENDING** — the rite-disjoint `review` critic must RUN the canary.
- **`verified_realized` = [UNATTESTED — DEFER-POST-HANDOFF]** — eunomia, LIVE, post-C1 + post-fleet-retire (`.know/telos/gfr.md`; attester = review-rite critic). The in-rite GREEN canary does NOT discharge it.

## §7 — Telos-scoping caveat (load-bearing — do NOT over-claim)
This leads-consumer is built ON the gfr substrate but is **NOT** the gfr telos proof. The gfr realization
predicate (`.know/telos/gfr.md:79-89`) is the send-origination `{guid}@appointments.contenteapp.com`
round-trip-to-correct-tenant (sprint-F dogfood) — a DISTINCT altitude from this leads-read. Do NOT claim
gfr `verified_realized` on the strength of this canary.

## §8 — DEFER watch-register (operator/critic-held; none scope-crept into the build)
- **Lever C1 apply** — SC-C1-1 (GR-6 bypass-tuple DELETION assertion) + SC-C1-2 (F-001 frozenset fast-follow). Operator; gates fleet-token retirement.
- **Dedicated leads-resolver SA provisioning** (Option B) — lead-time NOTIFY; operator; precedes fleet-retire.
- **UV-P-DBCLEAN** — DATA-VAL-003 live re-probe; post-C1; eunomia/live.
- **FINDING-1** — `collision_conflict` consumer test gap -> principal-engineer (4/4 EMIT matrix).
- fleet-token retirement, prod deploy, merge, `verified_realized` — all the user's; eunomia live.
- **PARALLEL G-CRITIC** — the review canary re-run elevates the seal to STRONG (does not gate anything downstream of itself).

## §9 — Next step
Operator walks `ari sync --rite=review` + CC restart for the rite-disjoint STRONG canary re-run +
the FINDING-2 cross-repo JWT-dominance verification. 10x-dev does NOT dispatch review specialists from here.
