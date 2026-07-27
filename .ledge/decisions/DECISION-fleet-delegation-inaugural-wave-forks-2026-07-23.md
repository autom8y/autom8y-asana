---
type: decision
initiative: fleet-delegation-portfolio
phase: 1-near-horizon (inaugural wave)
date: 2026-07-23
author: main-thread dispatcher (eunomia seat) — synthesizing PT-00 (potnia) + fork adjudication (pythia), both rite-disjoint advisory
source_anchor: "autom8y-asana origin/main 8e77c9a0 (local main d544b094 FROZEN pre-epic); autom8y monorepo origin/main a53288db (SDK source)"
governing: R1-R23 (telos-ratification 2026-07-20 + fleet-halt 2026-07-22, @origin/main); telos .know/telos/fleet-delegation-portfolio.md (RATIFIED); shape .sos/wip/frames/fleet-delegation-portfolio.shape.md
evidence_grade: MODERATE (self-cap per self-ref-evidence-grade-rule; corroborated by TWO rite-disjoint advisory consults — potnia/eunomia-coordination + pythia/ecosystem-navigation — converging independently)
status: accepted
disposition: PT-00 CONDITIONAL-RATIFY; keystone HALTED at R4; three operator rulings SURFACED (Q1-Q3, §6)
---

# DECISION — fleet-delegation inaugural wave: PT-00, FORK-C/D/E, and the R4 keystone HALT

## 0. Executive ruling (said first)

The scope-fork (Option-B phased-meta) is **RATIFIED**. The off-critical-path floor
(**P0 ∥ L1 ∥ D1**) is cleared and **in flight** (PRs opening). The **keystone spine
(K1→K2→K3) is HALTED**: a pre-consult Explore fanout + a grounding probe proved the
mission's delegated-human species is **not consumable satellite-side today**, and the
mission-correct remedy **trips R4 (witness-credential species migration, operator-reserved)**.
**PT-05 REALIZED is not reachable in this in-repo wave** — the realized bar moves to a
cross-repo Phase-2. In-repo Phase-1 honest cap = **PT-04** (and that is itself gated).
Three rulings are surfaced to the operator (§6).

## 1. Pre-consult SVR vetting (5 Sonnet Explore agents @ origin/main)

The fanout re-verified every load-bearing platform premise. Confirmations and the
decision-changing drifts:

| Premise | Verdict | Receipt @ origin/main 8e77c9a0 |
|---|---|---|
| species-gate seam | CONFIRMED | `src/autom8_asana/auth/jwt_validator.py:24` (`from autom8y_auth import AuthClient, ServiceClaims`), `:83` (`validate_service_token(token, audience="https://api.autom8y.io")`) |
| AuthContext drop-site | CONFIRMED (shape's :58 correct; frame's :57 was ancestor drift) | `dependencies.py:58` — `__slots__ = ("mode", "asana_pat", "caller_service")` |
| bot-PAT substitution | DRIFT +23 (re-anchor for any K2 patch) | construction now `dependencies.py:263-267`; `get_bot_pat()` `:239`; pool seam `:270/:297/:303` (was 240-244/216/247-280 at ancestor 12876ee1) |
| **K1's chartered "500→401 fix"** | **ALREADY SHIPPED** | the `except ValidationError` "Leaky-SDK-contract" clean-401 defense is live at `dependencies.py ~215-233` (it is what caused the +23 drift). K1's charter collapses to "accept the species" only. |
| a8t sovereign edge | barred-from-REALIZED CONFIRMED | exactly 2 `a8t` hits, both noise: `tests/unit/.../test_deploy_root_guard.py:350` (local `~/Code/a8t/deck-host` path), `vendor/.../fonts.base64.css:16` (base64 substring). No zero-trust/cloudflare co-occurrence. |

## 2. FORK-C — species-widening locus → **RESOLVED: HOLD autom8y-auth 4.1.0**

The shape's binary (satellite-only vs SDK-source-change+republish) does not fit the ground.

- SDK source = `autom8y/sdks/python/autom8y-auth/`, monorepo origin/main version **4.2.0**;
  autom8y-asana pins `autom8y-auth>=3.3.0` **open** (`pyproject.toml:68`) but `uv.lock` locks
  **4.1.0** (`uv.lock:288-289`).
- v4.2.0 added a third species `OperatorClaims` (`claims.py:401`), `TokenType.OPERATOR`, and a
  generic `validate_token()` dispatch (commit `ce2c2eca` #822, "machine-operator token capability").
- The ONLY reason to pin-bump 4.1.0→4.2.0 was to widen K1 onto `OperatorClaims` — and **FORK-D
  rules that widen mission-wrong** (it names an agency, not the human). autom8y-asana's outbound
  operator-plane already treats the operator token as an **opaque Bearer** and never deserializes
  `OperatorClaims` (`clients/data/_endpoints/operator.py:5-19`), so it does not need 4.2.0 either.

**Ruling: hold 4.1.0. The pin-bump is DEFERRED** (not mission-needed; re-evaluate only on a real
consumer need). Residual (reduced, not eliminated): whether `autom8y-auth 4.2.0` is actually
resolvable from the CodeArtifact index — command surfaced in §7. The 4.1.0 SDK already fails-closed
on an unrecognized species (`client.py:336` isinstance → `InvalidTokenTypeError` → clean 401), so
no live break exists.

## 3. FORK-D — species-identity → **R4 HALT (operator-reserved)**

The deepest fork, unresolved by the shape, resolved by the grounding probe:

- `OperatorClaims.operator_sub` returns `self.sub`, resolved from a **SigV4/STS ARN allowlist**
  (`operator_identity.py resolve_operator_sub`) — an **agency/machine principal, NOT the invoking
  human**. `operator_sub` (`claims.py:466-468`) names the agency.
- **No SDK claims class models an `act`/actor field.** The SDK models exactly
  BaseClaims/ServiceClaims/UserClaims/OperatorClaims (`claims.py:133/165/295/401`) — none carries
  a delegating-user/actor claim.
- The mission's correct species **is** minted auth-server-side: `services/auth/autom8y_auth_server/
  routers/tokens.py:405 agent_token_exchange` mints `sub`=delegating_user (human) + `act`={sub:agent};
  audit substrate `models/audit_log.py:45 acting_agent_id` / `:46 delegating_user_id`. But it is
  **un-modeled by any SDK claims class** → a **fleet token-contract gap**: the satellite (an SDK
  consumer) cannot witness the human-delegation as a first-class species.
- autom8y-asana's inbound boundary is **contractually ServiceClaims-only** (tested invariant
  `tests/contracts/test_contract_auth.py`). Widening it to witness/authorize on `sub`=human/`act`=agent
  **breaks that invariant** → **witness-credential species migration** → **R4, operator-reserved.**

**Ruling: K1 cannot self-authorize the widen.** Adding `OperatorClaims` to an isinstance tuple stays
inside K1's O4-MINIMAL charter but is telos-forbidden (names the agency). The mission-realizing move
(a satellite-consumable human-delegation species) is R4. **HALT → operator.**

## 4. FORK-E — K3 walkability → **realized bar is CROSS-REPO; in-repo caps at PT-04**

- autom8y-asana has **no `business_id` slot** (enforcement delegated to external pinned
  `autom8y-api-middleware>=0.3.0`, not vendored) and **no DB/ORM/migration layer at all** —
  `audit_logs.delegating_user_id` does **not exist** in this repo (the "migration 028 column in prod"
  premise points at a different service). `S2SAuditLogger` exists but is **DORMANT** (`audit.py:99`;
  zero callers outside `audit.py`).
- The human-named audit-of-record is written **cross-repo** (autom8y-auth mints + writes the row at
  exchange time; autom8y-api-middleware enforces business-scope).

**Ruling (K3 disposition):** primary = **hold K3 human-grain to Phase-2** (cross-repo); Phase-1 K3 =
attest the consumption socket + the D1 fail-closed seam only. Optional in-repo `enable/partial` = wire
the dormant `S2SAuditLogger` to a **service/tenant-grain** line (names `caller_service`/tenant, NEVER
the human — must not be reported as REALIZE). Per telos-integrity, every leg is labeled enable/partial.

## 5. The re-scoped DAG

```
IN-REPO PHASE-1 (walkable NOW — in flight):
  P0 provenance-floor [eunomia]      → ENABLE   (discharges PREMISE-3)   ── PR opening
  L1 workflow disclosure [10x-dev]   → CAPABILITY-NOW / consumption-post-Phase-2 ── PR opening
  D1 actor-attribution seam [arch]   → SHAPE    (design-only ADR)        ── PR opening

KEYSTONE (HALTED):
  K1 accept-species  ── BLOCKED at R4 (FORK-D): mission species un-modeled SDK-side; widen = R4
  K2 consumption-socket ── depends on K1
  K3 audit-names-human ── realized bar is CROSS-REPO (FORK-E)

  In-repo honest cap = PT-04 (identity consumed) — itself gated on the R4 species decision.
  PT-05 REALIZED = CROSS-REPO Phase-2 (autom8y-auth mint+audit; autom8y-api-middleware scope;
                    + a fleet SDK actor-modeling contract). NOT this wave.
```

## 6. Operator rulings SURFACED (do NOT block the P0∥L1∥D1 floor; needed at the keystone/Phase-2 gate)

- **Q1 — keystone re-scope (scope change):** Accept that in-repo Phase-1 caps at **PT-04** (identity
  consumed) and **PT-05 REALIZED lands cross-repo** (autom8y-auth + autom8y-api-middleware)?
- **Q2 — R4 contingency:** The grounding probe already shows `OperatorClaims` does NOT carry the human.
  The mission-realizing fix is a **witness-credential species migration (R4)**. Default = HOLD for your
  ruling. Alternatively, pre-authorize a scoped **read-only** auth-server investigation to spec the
  actor-modeling claims contract (no mint changes)?
- **Q3 — cross-repo continuations:** Authorize (a) a K3 audit-substrate continuation charter in the
  auth-server / autom8y-api-middleware, and (b) the U1 consent-journey **ui-rite switch** (a8 repo,
  operator-run)?

## 7. Surfaced commands (operator-run; NOT executed by this seat)

```bash
# FORK-C residual — is autom8y-auth 4.2.0 resolvable from CodeArtifact (vs only git-tagged)?
aws codeartifact list-package-versions --domain autom8y \
  --repository autom8y-python --format pypi --package autom8y-auth | grep '"version": "4.2.0"'

# U1 cross-repo ui-rite switch (run in the a8 repo, then restart CC once):
#   cd /Users/tomtenuta/Code/a8/a8 && ari sync --rite=ui
```

## 8. DEFER register (carry — expanded by the fanout)

| Item | Watch trigger | Owner |
|---|---|---|
| V-13 monolith write-plane identity fork | K3 consumption receipts land | operator (registered at P0) |
| R22 2026-07-28 transport gate (WS-6 build held) | gate date resolves | auto per ruling |
| a8t sovereign-edge grounding | operator produces org/repo or CF config/CI receipt | sre/operator |
| **SDK actor-modeling contract gap (NEW)** | a satellite must witness `sub`=human/`act`=agent | fleet auth-SDK seat (R4-gated) |
| **K3 cross-repo audit substrate (NEW)** | Q3(a) authorized | 10x-dev @ auth-server / api-middleware |
| **FORK-C pin-bump 4.1.0→4.2.0 (DEFERRED)** | a real OperatorClaims consumer need in asana | 10x-dev @ autom8y-asana |
| stranded-ADR landing | — | DISCHARGED at P0 landing |

Self-grade MODERATE. No wave-level CLOSED token (Gate B / F-HYG-CF-A). Per-item receipts above.
