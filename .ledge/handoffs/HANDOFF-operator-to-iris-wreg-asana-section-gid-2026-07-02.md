---
type: handoff
artifact_subtype: seam-handoff
initiative: asana-cutover-readiness-credential-topology
handoff_type: execution
from_rite: 10x-dev (post-merge, DEPLOY-DISPATCHED) + pythia seam adjudication
to: "/iris (W-IRIS live receipt) → /10x (W-REG-proper 19-GID replacement)"
created: 2026-07-02
status: proposed
rung: DEPLOY-DISPATCHED (route merged + dispatched; NOT yet deployed-reachable; SCAR-REG-001 OPEN)
telos: root charge = .sos/wip/frames/asana-cutover-readiness-sequencing.shape.md (§5 W-REG, PT-04)
---

# HANDOFF: the W-IRIS + W-REG seam — closing SCAR-REG-001 (asana-cutover-readiness LAST POLE)

> **Boundary**: the token-safe JWT-only `GET /sections` read-route is **MERGED to main + DEPLOY-DISPATCHED**.
> This handoff packages the two remaining legs — **W-IRIS** (iris fetches the live section-GID receipt) and
> **W-REG-proper** (10x replaces the 19 placeholder GIDs) — for the next session. It PAUSES here because
> W-IRIS is gated on iris activation (CC restart), deploy convergence, and a user-sovereign credential grant.
> Closing both legs closes SCAR-REG-001 — the last pole of the cutover-readiness charge.

## §1 · Confirmed receipts (Gate-C) — rung reached = DEPLOY-DISPATCHED
- **MERGED**: PR #184 squash **`16d281d6`** on `main` ("Token-safe scoped GET /sections read-route + W-REG join fix (FORK-R)"). Clean merge: CI 24-pass / mergeStateStatus CLEAN (OpenAPI-drift regenerated pre-merge; branch update-branched).
- **`Test@main`** run **`28577962102`** = success (2026-07-02 08:56Z).
- **`Satellite Dispatch`** run **`28578310750`** = success (2026-07-02 09:02Z) → deploy dispatched to the downstream a8 pipeline.
- **What DEPLOY-DISPATCHED does NOT mean**: the route is NOT yet proven deployed/converged/reachable. A merge is not a live route. The JWT-only route has **zero HTTP consumers**, so generic smoke proves only the *service* is up — the ONLY proof the *route* is reachable+functional is an authenticated S2S 200, which **is the W-IRIS call itself**.

## §2 · Preconditions before W-IRIS (all must hold; none is 10x's to force)
1. **[rite-disjoint]** Downstream a8 deploy CONVERGED — ECS steadyState on the new task-def revision + a GREEN health signal (asana `Nightly Live Smoke` / `CON-2 Freeze Smoke`). Attestable by eunomia/sre — OR folded into the W-IRIS 200 (movement §3). Currently **[UNATTESTED — deploy just dispatched]**.
2. **[user action]** iris ACTIVATED — `ari agent summon iris` then **CC restart** (iris is not summonable mid-session; per shape PV-preflight tooling note).
3. **[user-sovereign]** the AWS/Secrets-Manager grant enabling iris to READ `SERVICE_CLIENT_SECRET_ARN` for the S2S-JWT mint. Provisioning the grant is user-sovereign; exercising it once granted is iris's remit.

## §3 · LEG 1 — W-IRIS (`/iris`, via the iris-attestation procession: propose→emit→verify→audit)
- **Target**: live `GET /api/v1/projects/1201081073731555/sections` — the hardened JWT-only route on the deployed ECS service. READ-ONLY.
- **Auth**: mint a short-lived S2S JWT from `SERVICE_CLIENT_SECRET_ARN` (the mechanism `insights-export` already carries); the route's `require_service_claims` accepts it; the Asana PAT is resolved SERVER-SIDE via the brokered `_ARN` (`get_bot_pat()`) — iris never handles the plaintext PAT.
- **The 200 is dual-purpose**: it is BOTH the section data AND the route-reachability proof (closes the §2.1 gap).
- **Receipt spec (the W-REG denominator)**: `{ transaction-id, timestamp, status=200, disposition: name → live-section-GID map for ALL live sections of project 1201081073731555 }`.
- **Honest exits (G-RUNG — do NOT round up)**: connection-level failure (503 `BotPATError` / timeout / routing) → **deploy/reachability problem** → route to sre/deploy, record `BLOCKED-on-reachability`. 401/403 (claims mismatch) → **auth-config problem** → route to `/architect` or `/10x`, record `BLOCKED-on-auth`. Neither is a receipt. **No plaintext fallback, no WRITE** (the live Asana section-GID WRITE stays user-sovereign).

## §4 · LEG 2 — W-REG-proper (`/10x`, active rite already 10x-dev — NO rite-switch)
- **Entry gate (PT-04, HARD)**: the W-IRIS receipt must be **PRESENT** as a file:line anchor. G-RUNG forbids starting W-REG on a PENDING receipt (shape failure-signal). Fresh worktree off origin/main.
- **The join** (`join_section_registry`, `section_registry.py:249`): **live-GID (iris receipt) × monolith `BusinessUnits.SECTIONS` name→bucket taxonomy** (`/Users/tomtenuta/code/autom8/apis/asana_api/objects/project/models/business_units/main.py:18-39`, READ-only). GID-match alone re-risks the original silent-miscategorization SCAR — the dual-anchor is mandatory.
- **Replace** the 19 sequential placeholders at `section_registry.py:105` (4 EXCLUDED) + `:137-155` (15 UNIT) with the joined live GIDs; **remove the 5 `VERIFY-BEFORE-PROD` markers**.
- **Two LOAD-BEARING constraints (from /qa — non-negotiable)**:
  1. **Gate live-wiring on `blocks_live_wiring`/`blocking_findings`** — the three-tier Tier-3 fail-closed guarantee is advisory-to-caller today (`join_section_registry` has zero live callers); the W-REG wiring MUST actually gate on it, else the guarantee is inert.
  2. **Wire `assert_no_plaintext_pat_in_caller` (`bot_pat.py:107`) into the W-IRIS/caller startup** — else the H5/V6 guarantee is inactive (no production call site exists yet).
- **Proof**: RED-first two-sided **wrong-BUCKET** misroute fixture (already scaffolded in commit `bd6adbc6`); rite-disjoint critic clean. PR for operator review — agent never merges.

## §5 · Honest rung ladder (position marked)
```
MERGED ✓ → CI-GREEN@main ✓ → DEPLOY-DISPATCHED ✓   ◄── HANDOFF POINT (10x/releaser CAP)
  ‖ ‖ RITE BOUNDARY ‖ ‖  (below: rite-disjoint / user-sovereign)
   → DEPLOY-COMPLETED → PROD-CONVERGED → PROD-HEALTHY   (eunomia/sre ADVISORY; §2.1)
      → W-IRIS RECEIPT   (authenticated S2S 200 = route reachability + name→GID map; §3)
         → W-REG PROVEN  (19 GIDs replaced, dual-anchored, RED-first, critic-clean; §4)
            → SCAR-REG-001 CLOSED  (+ rite-disjoint attester)
               → VERIFIED-REALIZED
· · · protecting-prod / TRAFFIC CUTOVER — LATER, user-sovereign, NOT this cycle
```

## §6 · User-sovereign levers (agents MUST NOT exercise)
The Secrets-Manager grant for the S2S mint · deploy/prod-apply/rollback · the live Asana section-GID **WRITE** · merges to main · arming CloudWatch alarms · any traffic cutover · the leaked-PAT rotation (operator ruled ephemeral — recorded in `.know/defer-watch.yaml`, not blocking).

## §7 · Anchors
- Build: PR #184 (`16d281d6`) · TDD `.ledge/specs/TDD-asana-pat-read-route-and-wreg.md` · ADR `.ledge/decisions/ADR-asana-pat-read-route-forkR-2026-07-02.md`.
- Prior handoffs: `.ledge/handoffs/HANDOFF-10x-to-operator-asana-pat-read-route-2026-07-02.md` (§4 constraints), `.ledge/handoffs/HANDOFF-security-to-operator-asana-pat-read-route-2026-07-02.md`.
- Shape: `.sos/wip/frames/asana-cutover-readiness-sequencing.shape.md` (§5 sprint-4-reg, PT-04) · iris receipt spec `.ledge/reviews/handoffs/cross-rite-handoff-iris-section-gid-verify.md`.
- Code: `section_registry.py:105,137-155` (19 placeholders) · `:249` (`join_section_registry`) · `bot_pat.py:107` (`assert_no_plaintext_pat_in_caller`) · `api/routes/projects.py` (hardened route).

*Seam handoff. Rung = DEPLOY-DISPATCHED. Resume: (1) let the a8 deploy converge; (2) `ari agent summon iris` + CC restart + grant the S2S-mint; (3) `/iris` W-IRIS → receipt; (4) `/10x` W-REG-proper → SCAR-REG-001 CLOSED. Do NOT round DISPATCHED up to reachable — the W-IRIS 200 is the reachability proof.*
