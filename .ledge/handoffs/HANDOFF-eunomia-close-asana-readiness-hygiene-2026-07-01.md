---
type: handoff
artifact_subtype: eunomia-close
initiative: asana-readiness-hygiene
handoff_type: validation
from_rite: eunomia
to: operator (merge + required-check + telos-flip) + follow-on {hygiene-pass-2, SRE-watch}
from_station: verification-auditor (S5, rite-disjoint external critic)
created: 2026-07-01
status: proposed
rung: verified_realized PROVEN-PENDING-MERGE (rite-disjoint PASS-ADVISORY; realization pending operator merge + required-check + flip)
telos: .know/telos/asana-readiness-hygiene.md (verified_realized still UNATTESTED — operator lever)
---

# HANDOFF: eunomia (close) — asana-readiness-hygiene · L-001 CI-drift-guard-closure

> **Boundary**: eunomia CLOSED L-001 (the RUF100 drift-guard now has PROVEN teeth in CI) and rite-
> disjointly attested `verified_realized` as **PROVEN-PENDING-MERGE**. The ENFORCING state on `main`
> + the telos `ATTESTED` flip await the operator's levers (below). Prod-health (Nightly Smoke) is
> still `UNATTESTED`, SRE's — past the `‖`.

## §1 · What eunomia PROVED (receipts — Gate-C anchored, S5-independently-re-pulled)

L-001 was: the RUF100 drift-guard enforced in **0 of 3** CI ruff paths (local `just check` only). eunomia
wired a satellite-local CI job and PROVED its teeth with a two-sided real-CI canary:

| Receipt | Anchor | `Lint noqa Drift Guard (RUF100)` |
|---|---|---|
| CHANGE (the job) | commit `0793be60` — `.github/workflows/test.yml` +52/−0, single file, revert-clean, actionlint-clean | — |
| Closure PR (clean tree) | **PR #178** (OPEN) · run `28529541036` | **success** (no false-RED) |
| **Canary RED** (dead `# noqa: F401` on used `FastAPI`, `main.py:49`) | run `28530472880` job `84578316603` | **failure** — step log `RUF100 Unused noqa directive (unused: F401)` at `main.py:49:30`, exit 1, SOLE failing job |
| **Canary GREEN** (reverted) | run `28530879958` job `84579750422` | **success** |

- **`--extend-select RUF100`** (not `--select` — the 314-false-positive trap; confirmed at real-CI altitude: RED = "Found 1 error", not a 314-storm). KEEP-floor honored (`pyproject:293` idempotency.py per-file-ignore; SCAR-IDEM-001 intact). `ruff@0.15.4` pinned to `uv.lock:2438` (local/CI lockstep). Throwaway #179 deleted; PR #178 pristine.

## §2 · Verdict (S5, rite-disjoint external critic — eunomia ≠ hygiene)

- **EXECUTION altitude: PASS** (BLOCKING contract cleared) — 7/7 matrix (atomic, rendered-not-comment-only, pinned SHAs, `--fix`-safe, independently revert-safe, KEEP-floor intact, deterministic surface unbroken).
- **PRODUCT altitude: PASS-ADVISORY** (the STRONG grade; rite-disjoint + agent-disjoint from the executor) — drift-guard-CI-enforced is PROVEN for the noqa/RUF100 class. G-THEATER passes (real teeth).
- **Entropy delta: F → A** (canary-proven), honest-scoped.

## §3 · Rung ladder (honest)

`merged` ✓ (#176) < `CI-green@main` ✓ < `deploy-dispatched` ✓ < **`drift-guard-CI-enforced` PROVEN-PENDING-MERGE** < **`verified_realized` PROVEN-PENDING-MERGE**. The evidence is complete + rite-disjoint-attested STRONG; the REALIZED/ENFORCING state + the telos flip await the operator (§4). Do NOT read PROVEN-PENDING-MERGE as merged/enforcing/ATTESTED.

## §4 · Operator levers (surfaced — eunomia pulled NONE) — in sequence

1. **Merge PR #178** — lands the drift-guard job on `main`:
   `gh pr merge 178 --repo autom8y/autom8y-asana --squash`
   *(Optional first: rework to Alternative-A — the `uv run --no-sources` + CodeArtifact mirror — if exact reusable-toolchain fidelity is wanted over the minimal-ruff design. The minimal design is more robust: ruff resolves from PyPI either way, so Alternative-A only adds the CodeArtifact auth-flake surface. Recommend keep-as-is.)*
2. **Register the required check** — makes the guard BLOCK merges (full enforcement). Add `Lint noqa Drift Guard (RUF100)` to `main` branch-protection required status checks (repo-admin). **Sequence: canary-proven ✓ → register now.** **Revert-coupling (loud):** once required, deleting the job leaves the check permanently PENDING → all merges wedge — so any future job removal MUST de-register the check FIRST.
3. **Flip the telos** (only AFTER 1+2 — enforcement must be real before `verified_realized: ATTESTED`) — edit `.know/telos/asana-readiness-hygiene.md`:
   - `attestation_status.verified_realized: UNATTESTED → ATTESTED`
   - `attestation_status.last_review_verdict: .sos/wip/eunomia/VERDICT-l001-ci-drift-guard-closure.md (S5 PASS-ADVISORY)`
   - `verified_realized_definition.rite_disjoint_attester:` reconcile "review-rite critic" → "eunomia verification-auditor (rite-disjoint from hygiene; product-altitude R1 PASS-ADVISORY) — legitimate /review substitution per @critic-substitution-rule"
   - `receipt_grammar.cross_stream_concurrence: false → true`

## §5 · DEFER register (watch-registered; route via a fresh /frame or /sre — NOT actioned here)

| Item | Route | Trigger |
|---|---|---|
| **67 narrowings** (62 multi-code `type:ignore` + 5 file-blanket E402) | **hygiene-pass-2** (`/frame`) | manual mypy bisection on the now-vacancy-free + CI-drift-guarded floor |
| **Nightly Live Smoke** (6-night RED streak, all pre-dd63e667; NONE on dd63e667 yet) | **SRE** (`/sre`) | IFF it persists RED on `dd63e667`'s nightly run (prod-health, `‖`-past, UNATTESTED — not eunomia's) |
| **ASANA_PAT** `_ARN`-first vs `--provider env` gap | **arch / security** | separate initiative |
| **`fleet-schema-governance:` job has no `permissions:` block** (test.yml ~L326 → write-all default) | **security-review** | out-of-scope for L-001; recorded by S2 |
| ~~secretspec.toml.example~~ / ~~L-001~~ | **CLOSED** | secretspec kept tracked (D2); L-001 proven (this phase) |

*Eunomia close. L-001 proven-pending-merge; verified_realized rite-disjoint-attested (PASS-ADVISORY). Merge + required-check + telos-flip are the operator's. Prod-health is SRE's, past the `‖`. Do NOT dispatch SRE/hygiene-pass-2 specialists from eunomia — the operator routes via /frame or /sre.*
