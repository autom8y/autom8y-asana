---
type: decision
artifact_subtype: adr
title: FORK-R — Token-Safe ASANA_PAT Read-Route Custody Option
initiative: asana-cutover-readiness-credential-topology
slug: asana-pat-read-route-forkR
created: 2026-07-02
status: proposed
decision_state: AWAITING-OPERATOR-RATIFICATION
station: architect (10x-dev, Potnia-gated)
companion_tdd: .ledge/specs/TDD-asana-pat-read-route-and-wreg.md
supersedes: null
evidence_grade: MODERATE
reversibility: two-way-door (route is additive READ-only; no schema/data migration)
---

# ADR — FORK-R: Token-Safe ASANA_PAT Read-Route Custody Option

## Status

**PROPOSED — AWAITING-OPERATOR-RATIFICATION.** The architect surfaces the option
slate and a default recommendation; the architect does **NOT** select. Two operator
inputs gate this decision (§Operator-Ratification Input). The FORK-R custody choice and
the construction that follows are **user-sovereign** (handoff §3; shape §10).

## Context

Security **designed + gated** (teeth-proven, MODERATE) a token-safe ASANA_PAT READ
route — the single credential seam gating W-IRIS → W-REG → SCAR-REG-001 closure. The
route is NOT constructed, minted, or deployed. iris preflight resolved the design
magnitude: the safe machinery already exists in-repo (a read-only section-list route +
brokered bot-PAT resolution), so the (b) proxy is a **THIN assembly, not from-scratch**.
The open decisions are (1) which credential-custody option to materialize (FORK-R) and
(2) whether the existing ECS route can be reused instead of building a proxy
(reachability + S2S-JWT-mint — the branch trigger in the companion TDD §3).

All options route the **EXISTING** PAT. **Minting a NEW scoped Asana token is OUT** —
it is the forbidden crusade (handoff §3 OUT-OF-BOUNDS; shape §10).

Full design of both branches, the 7 hard-gates, and the W-REG join lives in the
companion TDD. This ADR records ONLY the FORK-R custody decision and its ratification
inputs.

## Decision

**RECOMMENDED (default), NOT SELECTED:** Option **(b)** — a read-only proxy exposing
ONLY `GET /sections`, caller never touches the PAT — **or its REUSE-EXISTING collapse**
(reuse the existing `GET /api/v1/projects/{gid}/sections` in JWT mode + a hard-gate
conformance audit) IF the reachability + S2S-JWT-mint inputs confirm.

The recommendation is stamped **AWAITING-OPERATOR-RATIFICATION**. The operator selects
(a), (b)/REUSE-collapse, or (c2), and ratifies the two inputs below.

## Options Considered

### Option (b) — read-only proxy [DEFAULT RECOMMENDATION]

Single-route proxy (or REUSE-collapse of the existing route) exposing ONLY
`GET /sections`, pinned to project `1201081073731555`. The caller holds a short-lived
AWS/S2S identity; the proxy resolves the bot PAT server-side via `ASANA_PAT_ARN`. The
caller **never materializes the PAT**.

- **Pros:** thickest containment (PAT never leaves the server boundary); discharges F3
  (silent fail-open) + F4 (over-privilege) architecturally; THIN to build (reuses
  `clients/sections.py:301-380` + `get_bot_pat()`); collapses to grant+audit if the
  ECS route is reachable+brokered.
- **Cons:** requires a deployed reachable route (Lambda function-URL or ECS); the prod
  Lambda handler is currently a stub (operator-ratification input); more infra than (a)
  if nothing is deployed.
- **Containment:** caller identity is short-lived; PAT never in caller memory.

### Option (a) — scoped assume-role [LIGHTER RUNNER-UP]

Scoped IAM role + trust policy (`GetSecretValue` on the one `ASANA_PAT_ARN`) →
`aws sts assume-role` → the caller resolves the PAT itself via `ASANA_PAT_ARN` behind a
fail-closed wrapper.

- **Pros:** lightest infra (no proxy/route to deploy); the caller holds a **short-lived
  assumed-role identity, not the plaintext PAT** at rest; naturally fail-closed on
  absent-ARN.
- **Cons:** **thinner containment** — the caller process DOES materialize the PAT value
  in memory (resolved from the ARN), unlike (b)/(c2) where the caller never sees it. A
  compromised caller process at the moment of use can read the value; the blast radius
  is the same full-scope PAT (rotation-off).
- **Containment:** short-lived identity; PAT transiently in caller memory (never
  plaintext-at-rest).

### Option (c2) — SSO/OIDC permission-set + proxy [HIGHER-INFRA PEER]

SSO/OIDC permission-set binding the section-read capability, fronting the (b) proxy
(`aws sso login` → permission-set → proxy).

- **Pros:** matches (b)'s containment (PAT never in caller); adds human-identity
  auditability + natural short-lived identity (satisfies H6 by construction).
- **Cons:** highest infra cost (SSO/OIDC permission-set provisioning); heaviest to stand
  up for a one-project READ capability.
- **Containment:** equals (b); PAT never in caller.

### Rejected (recorded, not re-litigated)

- **New scoped Asana token** — the forbidden crusade; OUT for every option (handoff §3;
  shape §10). All three options above route the EXISTING PAT.

## Tradeoff Summary

| Axis | (b) proxy / REUSE-collapse | (a) assume-role | (c2) SSO + proxy |
|---|---|---|---|
| PAT-in-caller | never | transiently in memory | never |
| Containment | thickest | thinner | thickest |
| Infra cost | medium (or ~0 if REUSE) | lowest | highest |
| H6 short-lived identity | yes | yes | yes (native) |
| Recommendation | **DEFAULT** | lighter runner-up | higher-infra peer |

## Operator-Ratification Input (design does NOT assume — the branch trigger)

Ratify these BEFORE construction; they select the TDD §3 branch and confirm the FORK-R
custody:

1. **ECS reachability + broker** — is the live ECS `/api/v1/projects/{gid}/sections`
   deployed, reachable, and JWT-brokered (resolves the bot PAT via `ASANA_PAT_ARN`)?
2. **S2S-JWT mint** — can the interactive caller mint a short-lived S2S JWT via
   `SERVICE_CLIENT_SECRET_ARN` token-exchange (the mechanism `insights-export` carries)?

- **BOTH YES** → REUSE-EXISTING collapse of (b): grant the caller S2S-JWT mint + run the
  hard-gate conformance audit (TDD §3.1). No new proxy.
- **EITHER NO** → BUILD branch: the thin (b) proxy — or (a)/(c2) per the operator's
  custody selection (TDD §3.2).

> **[UV-P: the prod Lambda handler `autom8y_asana_handler_prod` is a stub (Inactive,
> CodeSize=0, no Function URL) and the live API runs on ECS whose reachability config is
> not in this repo | METHOD: deferred-to-operator-ratification | REASON: this is an
> AWS-control-plane fact (an `aws lambda get-function` / ECS-service probe), an
> iris-preflight finding, not repo-inspectable; it is precisely input #1 above].**

## Consequences

- **Positive:** SCAR-REG-001's last pole is unblocked at design — construction can begin
  the instant FORK-R + the two inputs ratify. Both branches reuse existing safe
  machinery (THIN). The forbidden path (PAT-plaintext dual-mode) is structurally
  excludable via `require_service_claims` (TDD §3.1).
- **Negative / accepted:** the design ceiling is **route-constructed + qa-proven
  (pre-deploy)**; deploy, live receipt, merge, and cutover are all downstream and
  (deploy/merge/cutover) user-sovereign. `verified_realized` stays HELD.
- **Reversibility:** **two-way door.** The route is an additive, READ-only capability;
  no schema/data migration, no public-contract break for existing consumers (the
  general `list_sections` route is unchanged; the scoped capability is additive). It can
  be withdrawn without data consequence. The one-way-door elements (deploy, traffic
  cutover) are explicitly OUT of this cycle and user-sovereign.

## Compliance & Boundary

- No plaintext PAT in this ADR (ARN / secret-name only).
- No new token minted or designed.
- No cutover / traffic move designed.
- DEFER items (rotation, `-thnc`) untouched.
- The 7 hard-gates (H1–H6, GATE-GAP-1) are bound as constraints in the companion TDD §5,
  each with a build-deliverable and a qa-verification hook.

---

*Architect station. FORK-R surfaced with a default recommendation; NOT selected.
Stamped AWAITING-OPERATOR-RATIFICATION. Evidence grade MODERATE (self-ref ceiling).
Companion TDD: `.ledge/specs/TDD-asana-pat-read-route-and-wreg.md`.*
