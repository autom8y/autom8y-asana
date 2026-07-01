---
type: handoff
status: draft
from: review
to: iris-sre
created: 2026-06-24
initiative: asana-coherence
finding: SCAR-REG-001
rung_current: proven-in-code-only
rung_target: proven-by-live-receipt
blocked_on: token-safe-iris-asana-route
---

# Cross-Rite Handoff: review → iris-sre
## SCAR-REG-001 — Section GID Live Verification

---

## 1. Grandeur Anchor

Pick up the torch on autom8y-asana — the ecosystem's CRM-UI / datastore-frontend / workflow-orchestration layer composing into autom8y-{data,ads,sms,scheduling} flows — by driving the review-rite deep-dive from glint-detected signal to a graded, cross-rite-routed case file, advancing the two production-blockers (SCAR-REG-001; SCAR-IDEM-001) from `authored` toward `proven`; proven ONLY by a live receipt — never by a green dashboard or an optimistic merge. Production-mutating levers stay the user's.

Source: `PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md` grandeur anchor block.

---

## 2. Finding: SCAR-REG-001 — Placeholder GIDs Never Verified vs. Live Asana

**Location**: `src/autom8y_asana/reconciliation/section_registry.py:94–107` (EXCLUDED_SECTION_GIDS), `:128–150` (UNIT_SECTION_GIDS)

**What the code contains** (proven by PV-PREFLIGHT live read — `section_registry.py:94-99`, `:100-107`, `:128-131`, `:132-150`):
- `EXCLUDED_SECTION_GIDS = {1201081073731600..1603}` at `:100-107` — visibly sequential, 4 GIDs
- `UNIT_SECTION_GIDS = {1201081073731610..1624}` at `:132-150` — visibly sequential, 15 GIDs
- Both blocks carry inline annotation: `VERIFY-BEFORE-PROD (SCAR-REG-001)`
- In-code verify command named at `:94`: `GET /projects/1201081073731555/sections`

**Total unverified GIDs**: 19 sequential placeholder constants shipping in production-bound reconciliation routing code.

**Failure mode if wrong**: units are silently misrouted — either processed under excluded sections (Templates, Account Error) or skipped when active processing sections are unmatched. No CloudWatch metric surfaces the mismatch. Silent non-emission is the failure mode (coherence decay pattern per case file §Coherence Decay).

**Severity**: HIGH — correctness risk at reconciliation routing boundary; silent failure mode [STRUCTURAL | MODERATE per G-CRITIC ceiling — self-assessed; external corroboration PENDING]

### iris Attestation: BLOCKED-on-auth

The review rite has confirmed that NO token-safe iris→Asana route exists today:

- The Asana PAT is stored in AWS Secrets Manager at `autom8y/asana/asana-pat` [PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md: tooling state block] — Lambda-runtime-only access. The PAT is NOT available to `ari` or any present-session tooling.
- `ari` exposes no Asana caller. The `/iris` command, once activated (iris agent file was MISSING at review time — `~/.claude/agents/iris.md` MISSING per PV-PREFLIGHT tooling state), operates against AWS/CloudWatch surfaces; it has no direct Asana API surface registered.
- **The live-diff is BLOCKED-on-auth, not merely pending.** A pending state implies the route exists and has not yet been traversed. The auth surface does not exist yet in any iris-reachable form.

---

## 3. Suggested Command (Surface Only — Do NOT Run)

```
/iris (after building a token-safe route)
```

**Target call once route exists**:
```
GET /projects/1201081073731555/sections
Authorization: Bearer <asana-pat>
```

**Do not run** until a token-safe iris→Asana surface is minted. Premature execution with an unavailable or improperly scoped credential would either fail silently or expose the PAT outside the Lambda runtime boundary. The user is sovereign over when and how the Asana PAT is surfaced to an interactive session.

---

## 4. Realization Rung

**Current rung**: `proven-in-code-only`
The defect is proven in code (`section_registry.py:94-150` — sequential GIDs, `VERIFY-BEFORE-PROD` annotations confirmed by PV-PREFLIGHT live read). The rung cannot advance further without a live receipt.

**Target rung**: `proven` (by live receipt)
Per G-RUNG discipline (`authored < emitting < alerting < proven < merged < live < protecting-prod`): the rung advances from `proven-in-code-only` to `proven` only by live receipt — a live API response from `GET /projects/1201081073731555/sections` diffed against the EXCLUDED and UNIT GID sets.

**Blocker**: The rung is BLOCKED until a read-only autom8y-asana Lambda or server-side S2S surface mints the token in a form reachable by an interactive agent session. No current iris surface satisfies this. A purpose-built Lambda invocation (read-only, scoped to GET /sections on this project), a developer workstation credential rotation, or a server-side S2S caller are the three structural paths to unblocking.

G-RUNG is honored: the rung is named at `proven-in-code-only` and NOT rounded up to `proven` or `live` without the live receipt.

---

## 5. Acceptance Receipt

**What would advance the rung** from `proven-in-code-only` to `proven`:

A pasted live Asana section-list response from `GET /projects/1201081073731555/sections`, diffed against the in-code GID sets:

- **MATCH** (all 19 GIDs confirmed present and correctly categorized): rung advances to `proven` — reconciliation routing is verified correct. `VERIFY-BEFORE-PROD` annotation may be retired; 10x-dev can proceed to constant hardening.
- **MISMATCH** (one or more GIDs absent, renamed, or miscategorized): rung advances to `proven` — confirmed misroute. 10x-dev receives a specific diff identifying which constants require correction before routing can be trusted.

**Format required for receipt**:
```
# Live receipt — section GID verification
# Source: GET /projects/1201081073731555/sections
# Date: <ISO-8601>
# Attester: <rite-name or user>

sections_live: [
  { gid: "...", name: "...", resource_type: "section" },
  ...
]

EXCLUDED_SECTION_GIDS (in-code): {1201081073731600, 1201081073731601, 1201081073731602, 1201081073731603}
UNIT_SECTION_GIDS (in-code): {1201081073731610, ..., 1201081073731624}

diff_result: MATCH | MISMATCH
mismatched_gids: [] | [<list>]
```

**The live section-GID WRITE remains user-sovereign.** This handoff requests only a read (`GET`). No section creation, modification, or deletion is in scope. The decision to correct GID constants in code is a 10x-dev action gated on this receipt; the decision to commit and deploy is user-sovereign.

---

## 6. Inherited Live Receipts

### PV-PREFLIGHT Evidence (file:line anchors)

The following receipts were established by the PV-PREFLIGHT live read and are inherited verbatim by this handoff. No re-evaluation by case-reporter.

| Claim | Source anchor | Rung |
|-------|--------------|------|
| EXCLUDED_SECTION_GIDS visibly sequential (1201081073731600..603) | `PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:31` — `reconciliation/section_registry.py:100-107` | `proven` (code-read) |
| UNIT_SECTION_GIDS visibly sequential (1201081073731610..624) | `PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:31` — `reconciliation/section_registry.py:132-150` | `proven` (code-read) |
| VERIFY-BEFORE-PROD annotations present at both blocks | `PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:31` — `section_registry.py:94-99` + `:128-131` | `proven` (code-read) |
| In-code verify command: `GET /projects/1201081073731555/sections` | `PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:31` — `section_registry.py:94` | `authored` (in-code doc) |
| iris agent file MISSING at session time | `PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:45` — tooling state block | `proven` (filesystem check) |
| Asana PAT location: `autom8y/asana/asana-pat` (Secrets Manager) | `PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:45` — tooling state block | `proven` (operational knowledge) |
| `Autom8y/AsanaWorkflows` namespace: 0 metrics published | `PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md:33` — `list-metrics count=0` | `proven` (live AWS receipt) |

### iris Attestation Evidence

| Claim | Evidence form | Grade |
|-------|--------------|-------|
| No token-safe iris→Asana route exists today | iris agent MISSING at PV-PREFLIGHT time; `ari` has no Asana caller registered; PAT is Lambda-runtime-only | [PLATFORM-HEURISTIC: operational state at 2026-06-24; subject to change when iris is activated and a route is built] |
| BLOCKED-on-auth, not merely PENDING | Auth surface does not exist in any iris-reachable form — structural gap, not traversal gap | [STRUCTURAL | MODERATE per G-CRITIC ceiling] |

---

## 7. Out-of-Scope / User-Sovereign Levers

The following are explicitly outside the scope of this handoff. G-DEFER applies: these items are watch-registered, not scope-crept into this iris-sre route.

| Item | Why out-of-scope | Defer-watch |
|------|-----------------|-------------|
| GID constant correction in `section_registry.py` | 10x-dev action; requires live receipt first; routing is `10x-dev` per case file cross-rite table | Post-receipt; route to 10x-dev |
| Asana PAT credential rotation or surfacing to interactive session | User-sovereign; production secret management is not a review-rite or iris-sre decision | User decides when/how to surface |
| Section creation, modification, or deletion in Asana | Explicitly excluded; this handoff requests read-only GET only | User-sovereign; not in scope |
| SCAR-IDEM-001 (idempotency finalize) | Separate HIGH finding with separate routing (sre + 10x-dev); distinct blocker character | See case file H-2; separate handoff if needed |
| Building the token-safe iris→Asana route itself | Platform infrastructure decision; requires user or platform-ops authorization | User-sovereign; this handoff surfaces the need, does not prescribe the implementation |
| Deploy or merge of corrected constants | User-sovereign; post-receipt, post-10x-dev implementation | User decides deploy timing |

**G-DEFER binding**: this handoff surfaces the SCAR-REG-001 live-verification gap and names the structural auth blocker. It does not scope-creep into credential management, route infrastructure, or the GID correction implementation. Those remain deferred items in the watch register pending user authorization and route construction.

---

*Handoff authored by: case-reporter (review rite) | 2026-06-24 | HEAD: f4f924d2*
*G-RUNG honored: rung named at `proven-in-code-only`; NOT rounded up*
*G-DEFER honored: out-of-scope items watch-registered, not scope-crept*
*Evidence ceiling: [MODERATE] per G-CRITIC — self-assessed; external corroboration PENDING*
