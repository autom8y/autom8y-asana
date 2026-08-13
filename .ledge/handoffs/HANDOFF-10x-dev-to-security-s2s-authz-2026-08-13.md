---
type: handoff
artifact_id: HANDOFF-10x-dev-to-security-s2s-authz-2026-08-13
schema_version: "1.0"
source_rite: 10x-dev
target_rite: security
handoff_type: assessment
priority: critical
blocking: false
initiative: exec-insight-delivery
created_at: "2026-08-13T08:56:13Z"
status: pending
session_id: session-20260813-104852-686d6d30
source_artifacts:
  - .ledge/decisions/RAILS-insight-delivery-verified-2026-08-12.md
  - .ledge/decisions/RULING-operator-morning-set-2026-08-13.md
  - .ledge/reviews/CRITIQUE-s3-delivery-rails-2026-08-12.md
  - .ledge/handoffs/IGNITION-exec-insight-delivery-wave-2026-08-13.md
provenance:
  - { source: "RAILS-insight-delivery-verified-2026-08-12.md §4.3 (:480-565)", type: artifact, grade: strong }
  - { source: "RULING-operator-morning-set-2026-08-13.md R-11 (:127-131)", type: adr, grade: strong }
  - { source: "src/autom8_asana/api/routes/internal.py:83-162 (require_service_claims)", type: code, grade: strong }
evidence_grade: strong
tradeoff_points:
  - attribute: "time-to-remediation"
    tradeoff: "routing (this artifact) is dispatched before, not after, the security rite executes"
    rationale: "operator ratified Q-9 E1 STANDS STRICT — routing precedes the EX-3 limb (ii) TemporalFilter fix; execution timing is a separate operator decision (see §5)"
response_due: null
response_artifact: null
---

# HANDOFF — 10x-dev → security · S2S authorization gap (Asana write surface)

**This is a routing/assessment handoff, not an execution order.** Its existence
discharges the exec-insight-delivery wave's PT-03 Q3.3 (security routing
dispatched). Whether the security rite executes this assessment **in-session or
out-of-band is UNRULED and operator-only** (kit §2 / C-9) — this artifact
records the routing, decides neither. See §5.

## §1 The finding — receipted, code-side, CLOSED half

**Claim (STRONG — direct inspection + independent corroboration in this repo's
own `.ledge/` record at `RAILS-…-2026-08-12.md:981`):** all three Asana write
classes on the autom8y-asana service are **authenticated but not authorized**. A
caller presenting any valid fleet service JWT (correct signature, issuer,
expiry, audience `https://api.autom8y.io`, and a passing tenant-scope) is handed
the **shared bot Asana credential** and may invoke any write class. Nothing
checks *which* service may invoke *which* write. `CR-1` — an operator process
fence reserving all three write classes — is currently the **only** control.

### 1a. The three write classes (entry → service → client call site)

| Write class | Route | Auth dependency | Service → client anchor |
|---|---|---|---|
| Comment create | `POST /v1/receipts` — `api/routes/receipts.py:99` | `require_service_claims` | `services/receipts_service.py:346` → `clients/stories.py:301`, HTTP at `:336` |
| Task create | `POST /v1/intake/business` — `api/routes/intake_create.py:73` | `require_service_claims` | `services/intake_create_service.py` (multiple) → `clients/tasks.py:375`, HTTP at `:475` |
| Task create/update (generic) | `POST/PUT /api/v1/tasks[/{gid}]` — `api/routes/tasks.py:197,:258` | dual-mode `get_auth_context` | `services/task_service.py:195,:244` → `clients/tasks.py:375/483` |
| Custom-field write | `PATCH /api/v1/entity/{type}/{gid}` — `api/routes/entity_write.py:195` | `require_service_claims` | `services/field_write_service.py:192` → `clients/tasks.py:545` |
| Custom-field write | `POST /v1/tasks/{task_gid}/custom-fields` — `api/routes/intake_custom_fields.py:57` | `require_service_claims` | `services/intake_custom_field_service.py:128` → `clients/tasks.py:545` |

All routes mount in one FastAPI app / one ECS process / one ALB target group
(`api/main.py:456-492`); no route-level network segmentation inside this repo.

### 1b. The gap, exactly

- `require_service_claims` (`api/routes/internal.py:83-162`) validates
  signature/issuer/expiry/audience via the SDK, rejects PAT-shaped tokens, then
  **returns the claims object without ever calling** `has_scope` /
  `has_permission`. It is authenticate-and-pass-through.
- The JWT caller is then lent the **shared** bot Asana credential
  (`auth/bot_pat.py`, sourced from the `ASANA_PAT` env key — key named, **value
  never read or transcribed**, per CR-5). Writes execute with that credential
  (`entity_write.py:271`, `receipts.py:163`). `caller_service` is captured but
  used **only for logging** (`entity_write.py:231,:362`; `intake_create.py`;
  `intake_custom_fields.py:96,:157`).
- **Proof the pattern exists and is simply unused on writes:** the *only*
  permission gate in the whole surface is `api/routes/admin.py:456`
  (`SUPER_ADMIN_PERMISSION not in claims.permissions`) — and it guards a
  cache-refresh route, **not** an Asana write. Fine-grained authz is available
  in-codebase and not applied to the write routes.
- **Corrects a stale inherited premise (surfaced, not absorbed):** prior
  fleet-delegation notes asserted audit fields `acting_agent` /
  `delegating_user` already ride the token, merely unconsumed. A grep across
  `src/` and the installed `autom8y_auth` SDK returns **zero hits** for those
  fields in `ServiceClaims` / `UserClaims` / `BaseClaims`. There is no delegation
  identity in the claim at all — the gap is deeper than "identity present but
  unread."
- **Deeper than a missing check — the scope vocabulary does not exist upstream
  either.** `git show origin/main:services/auth/service-accounts.yaml` carries no
  `asana:*` write scope anywhere; the `asana-onboarding-walkthrough` service
  account self-documents *"no data:write (the sweep writes to Asana via
  ASANA_PAT, not the caller token)."* Even if this repo added `has_scope("asana:write")`,
  there is nothing at the minting layer to check against. Remediation is a
  **two-layer** problem: a scope taxonomy at `autom8y-auth`, and enforcement here.

## §2 The OPEN half — carried verbatim for the security rite to resolve

These two UV-Ps are the reason this is a security-rite question and not a
10x-dev fix: both require probing **live credential distribution** (CR-5
forbidden to this seat) or **AWS/ALB inspection** (CR-2 / an external module not
checked out). They are quoted verbatim from
`RAILS-insight-delivery-verified-2026-08-12.md` §8, both **OPEN — carried
forward UNCLOSED, deliberately unprobed**.

### UV-P-C-1 — `RAILS-…-2026-08-12.md:944`

> [UV-P: whether an agent seat in this fleet can obtain a valid service JWT
> (audience https://api.autom8y.io) by following existing documented patterns,
> and therefore reach POST /v1/receipts, PATCH /api/v1/entity/{type}/{gid} or
> POST /v1/tasks/{task_gid}/custom-fields without an operator | METHOD:
> credential-distribution audit across the fleet's service-account issuance path
> (autom8y-auth), plus a review of agent-seat runtime env injection | REASON:
> this is a fact about credential distribution, not about this repo's code.
> Probing it means handling live credentials, which neither the critic nor this
> seat will do. **This is the open half of the §4.3 security question**: §4.3
> establishes the code-side gate is fleet-membership-only; whether fleet
> membership is reachable from an agent seat is UNESTABLISHED. Route: security
> rite (O-H).]

### UV-P-C-2 — `RAILS-…-2026-08-12.md:945`

> [UV-P: the network reachability of the autom8y-asana API — whether the
> ALB/listener is internal-only or internet-facing, and what SG/WAF sits in
> front | METHOD: read terraform/services/asana/{alb,ecs,service}.tf in the
> autom8y monorepo at origin/main, or aws elbv2 describe-load-balancers |
> REASON: terraform/services/asana/ in THIS repo contains only observability
> alarm definitions; the service's network infra is defined elsewhere. Bounds
> the blast radius of §4.3 but does not change the code-side finding. Route:
> security rite (O-H).]

**Partial grounding this seat could reach without crossing a fence:**
`git show origin/main:terraform/services/asana/main.tf` shows the service on ECS
Fargate behind a **shared** `platform` remote-state ALB (`listener_rule_priority
= 120`; shared with priority 10=auth, 110=data), `domain = asana.api.autom8y.io`,
`subnet_ids = …private_subnet_ids`. The `internal = true/false` attribute for
that shared ALB is declared inside the external `a8` module repo
(`…/stacks/service-stateless`), **not checked out anywhere accessible** — so
UV-P-C-2 remains genuinely open. A private-subnet placement is suggestive but
not dispositive of the listener's `internal` flag.

## §3 Assessment items

```yaml
items:
  - id: SEC-001
    summary: >-
      Confirm/refute the code-side S2S authorization gap on the three Asana
      write classes and specify the two-layer remediation (scope taxonomy at
      autom8y-auth + enforcement at autom8y-asana write routes).
    priority: critical
    assessment_questions:
      - Does the finding in §1 hold under your review — is require_service_claims
        (internal.py:83-162) authenticate-and-pass-through with no write-class
        authorization, and admin.py:456 the only permission gate?
      - What is the correct remediation shape — a per-service->write-class scope
        vocabulary minted at autom8y-auth (service-accounts.yaml) plus has_scope
        enforcement on the write routes, or a different control (e.g. mTLS
        service allowlist, per-write-class bot-credential partition)?
      - Given no acting_agent/delegating_user claim exists, is a delegation
        identity required before enforcement is meaningful, or is caller_service
        (already captured, currently log-only) a sufficient authorization key?
    notes: >-
      Code-side finding is STRONG and independently corroborated at
      RAILS-...:981. CR-1 process fence is the only control today. No agent
      writes to the live board (CR-1 operator-reserved) — do not exercise any
      write path to test.
  - id: SEC-002
    summary: >-
      Resolve UV-P-C-1 — is a valid fleet service JWT reachable from an agent
      seat by documented patterns, making the write routes reachable without an
      operator?
    priority: critical
    assessment_questions:
      - Following only existing documented issuance patterns, can an agent seat
        obtain a service JWT with audience https://api.autom8y.io that clears
        require_service_claims?
      - Is any agent-seat runtime env injected with such a credential today?
    notes: >-
      Requires a credential-distribution audit across autom8y-auth issuance +
      agent-seat env injection. This handling of LIVE credentials is exactly
      what CR-5 forbids the 10x-dev seat — it is why the question routes here.
      Report the fact and path only; never transcribe credential material.
  - id: SEC-003
    summary: >-
      Resolve UV-P-C-2 — is the autom8y-asana ALB internal-only or
      internet-facing, and what SG/WAF sits in front? Bounds the blast radius.
    priority: high
    assessment_questions:
      - Reading the external a8 service-stateless module (or aws elbv2
        describe-load-balancers), is the shared platform ALB listener that
        serves asana.api.autom8y.io internal=true or internet-facing?
      - What security group / WAF sits in front of listener_rule_priority 120?
    notes: >-
      Partial grounding in §2 (private-subnet placement, shared ALB) is
      suggestive, not dispositive. The internal flag lives in an external module
      not checked out here. Does not change the code-side finding; bounds
      exploitability.
```

## §4 Fences that bind any work on this handoff (verbatim, from the wave kit §3)

1. **CR-1** — all three Asana write classes are OPERATOR-RESERVED. The S2S
   authorization gap means this process fence is the ONLY control. **No agent
   writes to the live board, ever** — do not exercise a write path to reproduce
   the finding.
2. **CR-2** — `s3://autom8y-asr-verdicts` is operator-reserved. Not read, not
   listed.
3. **CR-5 — credentials.** No agent mints, extracts, copies or logs credential
   material. On ENCOUNTERING credential material in any file, history object,
   config or output — stop reading, do not quote it, do not transcribe it;
   report only the path and the fact. **Specific live hazard:** a Critical,
   unrotated `ASANA_PAT` is reachable in this repo's git history
   (`.know/defer-watch.yaml:382-403`; commits `a578ca85`, `525431de`,
   `15cffee1`, path `.claude/settings.local.json` — gitignored at HEAD, live in
   history). A task requiring credential material STOPS and reports what it
   would need.
4. **Monorepo trap:** `/Users/tomtenuta/Code/a8/a8/repos/autom8y` is on a
   divergent branch (281 files differ from origin/main) with a sibling session
   actively committing. Always `git show origin/main:<path>` for any monorepo
   read.

## §5 Operator-reserved (recorded, not decided — C-9)

- **Execution locus is UNRULED.** Q-9 ratified only the *sequencing* (E1 STANDS
  STRICT — security routing precedes the EX-3 limb (ii) TemporalFilter fix).
  Whether the security rite runs this assessment **IN-SESSION** (borrow already
  co-seated: `inv-20260813-41bc318aeb4c` — threat-modeler, compliance-architect,
  penetration-tester, security-reviewer) **or OUT-OF-BAND** is the operator's
  call. This handoff decides neither; it makes the routing exist.
- **The remediation itself is operator-gated.** Any fix touching the write
  surface or the minting-layer scope taxonomy is a design→operator-review→land
  sequence, not an autonomous change. CR-1 stays the control until an operator
  rules otherwise.

## §6 Response

Response artifact (if/when the security rite acts):
`HANDOFF-RESPONSE-security-to-10x-dev-2026-08-13.md` in `.ledge/handoffs/` or the
session dir. Status transitions: pending → in_progress (accept) → completed.
