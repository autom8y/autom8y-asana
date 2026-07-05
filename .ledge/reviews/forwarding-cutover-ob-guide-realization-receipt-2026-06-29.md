---
type: review
status: accepted
date: 2026-06-29
initiative: forwarding-cutover-first-value
sprint: sprint-3 OB-GUIDE
predicate: "(a) — the guide leg"
rung: "e2e-/qa-confirmed (render-proven) — predicate (a) pillar CLOSED"
anchor: autom8y-asana feat/fcfv-sprint3-ob-guide-attestation (build 174518c7 + FV-3 cert ff97d4ec) · autom8y origin/main f1f54612 (autom8y-core 4.9.0)
halt_above: PT-02
closes_watch_item: "G-A (FV-3 cert) — artifact-correct → delivered-correct"
---

# Realization Receipt — Predicate (a): OB-Guide Delivered (North Star Family Chiropractic)

> Closes the FV-3 certification's **G-A** watch-item (artifact-correct → *delivered*-correct). Records the operator-authorized live attach + the three-way byte identity + the e2e /qa that lifts predicate (a) to **render-proven**. The first genuine production write of the forwarding-cutover arc. **PT-02 HALT stands for predicate (b).**

## What was realized
**Predicate (a) — the guide leg — is REALIZED.** North Star Family Chiropractic's personalized onboarding walkthrough deck, carrying the byte-exact routing address `d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com` (≡ `format_routing_address("d167d635-1468-4ad5-9f88-8d44c8a4d1a9")`), is attached **live** to the pilot clinic's Asana onboarding record.

## G-A audit trail (the attach)
| Field | Value |
|---|---|
| attachment GID | `1216128125285279` |
| parent task | `1210776074464695` — "PLAY: Custom Calendar Integration — North Star Family Chiropractic" (Calendar Integrations, gid `1209442849265632`) |
| attachment name | `walkthrough_1210776074464695_20260629T184926Z.html` |
| created_at | `2026-06-29T18:50:29.463Z` |
| size | `1047203` bytes |
| method | operator-authorized **manual render + direct Asana attachments-API POST** (NOT the gated workflow/Lambda; `AUTOM8_WALKTHROUGH_ENABLED` unset) |
| idempotency (MM-003) | first/non-duplicate — zero prior walkthrough decks on the task (8 prior unrelated attachments) |
| executor | iris (operational bot), operator-authorized; Asana tokens by sha256 prefix only, read inline, never echoed/persisted/staged |

## Three-way byte identity (the delivery chain)
`sha256 cc1702124d3af095288da75c37596cf7760f6b302c442485cf47665ba74f2644` / `1047203` bytes — **IDENTICAL** across all three hops:
1. **rendered** — local, node ≥22 + autom8y-core 4.9.0 + the vendored deck-producer @ `6551aee0`
2. **in-Asana** — re-downloaded by iris immediately post-attach
3. **operator-downloaded** — `~/Downloads/walkthrough_1210776074464695_20260629T184926Z.html`, e2e-/qa byte-verified this session

## Tenant-isolation oracle — PASS at every hop
`harvest_appointment_addresses(bytes) == { d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com }` — North Star's address **ONLY**, zero wrong-tenant — on all three artifacts. The §6 placeholder `xxxx-xxxx@appointments.contenteapp.com` is raw-present but harvester-invisible (`x ∉ hex`, by design). The harvester is strictly weaker than the producer's `CANONICAL_ADDR_RE` (a superset → not a reimplementation; G-PROPAGATE).

## Provenance + certification chain (re-derive, don't trust)
- **build:** `feat/fcfv-sprint3-ob-guide-attestation` @ `174518c7` — the `freeze_walkthrough_deck` invocation + the byte-diff oracle + AC-1..AC-7 (two-sided).
- **FV-3 cert:** @ `ff97d4ec` — **security-FV-3-corroborated (STRONG)**, rite-disjoint (security-reviewer N1 CONVERGE — a fourth-hand re-mint reproduced the byte-identical sha256; the AC-3 tautology mutation proved the oracle teeth **producer-independent**; threat-modeler + penetration-tester + compliance-architect all CORROBORATE). `CERTIFICATION-security-fcfv-sprint3-FV3-2026-06-29.md`.
- **CRR-1:** operator-discharged at the substrate of record (direct `nhc_db` read of `chiropractors.guid`, 2026-06-29) — right-clinic verified, NOT name/offer-title-resolved.
- **mint authority:** `autom8y-core 4.9.0` `format_routing_address` (#719), autom8y origin/main `f1f54612`.

## Honest rung
```
byte-exact-verified (qa MODERATE)
  → security-FV-3-corroborated (STRONG)
    → attached-live
      → e2e-/qa-confirmed (render-proven)  ← HERE = predicate-(a) pillar CLOSED
```
**Predicate (b) — the booking-render leg** (the EBI reviewwave delegate rendering a real forwarded booking via the *new fleet*, monolith out of the path) — remains **AHEAD**: wired-INERT (sprint-2, dre-STRONG, DARK), gated by **sprint-5 FLIP-GATE** + the operator flip-prep (CONTENTE secret → `_secrets.py` bridge → P1/P2 → populate → `dry_run=false` → SendGrid flip → RR-1 live render). **PT-02 HALT STANDS for predicate (b); only a real-client booking render lifts it.** The full first-value loop needs both legs.

## Carried (watch-registered)
- **T7** — the live phone-resolve fleet tenant-selection path (`workflow.py:221`, no runtime oracle; the EBI F-002 `.first()` collision substrate) → **sprint-5** (the runtime tenant-binding assertion is the headline pre-fleet-flip trigger). Out-of-N=1-scope (MC-2 #725 opt-in-OFF; resolver mocked).
- The merge of `feat/fcfv-sprint3-ob-guide-attestation` to main (operator-terminal).
- MC-2 #725 broad rollout · sprint-7 greenfield glue · compliance G-B..G-E · C-1/C-2 reproducibility.

---

## ⚠️ FAULT-13 ANNOTATION (2026-07-02/03)

The "personalized onboarding walkthrough deck … REALIZED" claim was over-broad: fault 13
(2026-07-02, operator-caught) showed the personalization line bound the RAW internal Asana
task name (`workflow.py "client_name": task.name`), so "personalized" held only for the
ADDRESS leg; the CRR-1 discharge here was right-CLINIC only. Remediated: asana #196
(provenance rebind to `BusinessRecord.business_name` + fallback deleted, merge `8f41bcfc`)
+ #197 (fail-closed `personalization_gate`, merge `934dd7a0`); all 7 live decks restored
2026-07-03 (7× C-BN1-05 with masked client_name). The right-CONTENT leg is now a standing
CRR-1 requirement per `.ledge/decisions/fault13-personalization-ruling-2026-07-02.md` §3.
