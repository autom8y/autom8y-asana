---
type: handoff
artifact_subtype: sre-close
initiative: asana-cutover-readiness-credential-topology
handoff_type: validation
from_rite: sre
to: operator + eunomia (verified_realized STRONG, fully rite-disjoint)
from_station: N5 seam (platform-engineer N1 + observability-engineer N2/N3 + incident-commander N4 disjoint critic)
created: 2026-07-02
status: proposed
rung: deployed-reachable ATTESTED (MODERATE) · verified_realized HELD-DEFER → eunomia
telos: root charge = .sos/wip/frames/asana-cutover-readiness-sequencing.shape.md
---

# HANDOFF: sre (close) — W-REG CONVERGED → deployed-reachable ATTESTED; verified_realized HELD

> **Boundary**: the W-REG live section-GID replacement (squash `2d7d39d9`, SCAR-REG-001 CLOSED) has
> **CONVERGED onto live `autom8y-asana-service`** (rev 600, steadyState). **deployed-reachable is
> ATTESTED (MODERATE)** by a station-disjoint SRE critic. **verified_realized is HELD-DEFER** — STRONG
> requires a fully rite-disjoint attester (eunomia) AND an end-to-end signal that exercises the
> account-classification path (user-sovereign-gated; a read-only watch-trigger is registered). Traffic
> cutover / `protecting-prod` is explicitly NOT this cycle. The live Asana WRITE, rollback,
> PAT-rotation, alarm-arming, and smoke-triggering remain the operator's.

## §1 · Receipts (Gate-C — deployed-reachable, re-verified by the disjoint N4 critic)
- **Deploy**: `autom8y/autom8y` "Satellite Receiver — asana" run **`28594805892`** = success (updatedAt `2026-07-02T14:01:39Z`).
- **ECS convergence** (`autom8y-asana-service`): task-def **rev 600**, image `…/autom8y/asana:2d7d39d` (SHA-bound to `2d7d39d9` = the W-REG merge = origin/main tip), `rolloutState=COMPLETED`, `running=1 == desired=1`, event **"(service autom8y-asana-service) has reached a steady state."**
- **Correctness chain** (why the converged data is right): W-IRIS live **200** proved the 17 GIDs ARE the real Asana section GIDs · `/review` **STRONG** proved the transcription 17/17 char-for-char · N1 proved rev 600 booted on the SHA-bound image + steadyState fired.

## §2 · What deployed-reachable means here
The W-REG live-GID replacement is **live and serving** on rev 600. Because the data sits behind an **import-time fail-closed gate** (`SectionRegistryError` on any undispositioned live section), steadyState + `running==desired` ⟹ the container booted ⟹ `section_registry` imported cleanly with the live GIDs ⟹ the gate PASSED (a bad join would crash-loop → no steadyState). The N4 critic graded this **GREEN-qualified (inference, not a boot-log receipt)** — sufficient for deployed-reachable at MODERATE, not for verified_realized.

## §3 · Honest rung ladder (position marked)
`authored < emitting < alerting < proven < merged < live < protecting-prod`
- **merged** ✓ (`2d7d39d9`, SCAR-REG-001 CLOSED) → **deploy-dispatched** ✓ → **deployed-reachable ✓ ATTESTED (MODERATE)** ◄── HERE
- **verified_realized (= live)** — **HELD-DEFER → eunomia**. Station-disjoint (SRE N4) caps at MODERATE per self-ref-evidence-grade-rule; STRONG needs a fully rite-disjoint attester + an end-to-end signal.
- **protecting-prod / traffic cutover** — LATER, user-sovereign, explicitly NOT this cycle (north-star = prod-readiness, no traffic move).

## §4 · verified_realized discharge path (watch-registered — read-only, non-sovereign)
The **next scheduled `Reconcile Drift Detection` run** (cadence ~45–60 min; the last one `28595428218` @ 13:53Z is PRE-convergence) will naturally post-date 14:01Z and exercise the section-registry join on rev 600 — a GREEN there is the end-to-end verified_realized signal, dischargeable **without any operator lever**. Alternatively, a live `GET /sections` on rev 600 (needs the user-sovereign S2S JWT mint). Either → route to **eunomia** for the fully-rite-disjoint STRONG attestation. Watch-registered in `.know/defer-watch.yaml`.

## §5 · DEFER register (watch-registered — NOT new incidents)
`#927` (metrics-export SEAL, `SERVICE_CLIENT_ID=asana`) · the Nightly CodeArtifact/S3-IAM infra flake (chronically RED, NOT a W-REG regression — its RED never reaches the section-registry path) · the 5 credential-topology DEFERs · the `:465` KeyError polish · **the verified_realized end-to-end DEFER** (this handoff, §4). No SEV declared; no page warranted.

## §6 · User-sovereign levers (surfaced, NONE pulled) + no telos flip
Live Asana section-GID WRITE · rollback (`ecs update-service` to a prior rev) · PAT-rotation · alarm-arming · deploy re-apply/promotion · triggering a fresh CON-2/Nightly/Reconcile smoke · the S2S mint for a live `GET /sections`. **No telos flip** — the disjoint critic did NOT attest verified_realized STRONG (correctly held); and there is no SCAR-REG-001-specific telos file — the handoff chain + memory are the record.

*SRE close. deployed-reachable ATTESTED (MODERATE, rev 600 steadyState); verified_realized HELD-DEFER → eunomia (+ the Reconcile-Drift-Detection watch-trigger). SCAR-REG-001 CLOSED + converged-and-serving. The asana-cutover-readiness LAST POLE is landed and live; its final `verified_realized` attestation awaits one rite-disjoint signal.*
