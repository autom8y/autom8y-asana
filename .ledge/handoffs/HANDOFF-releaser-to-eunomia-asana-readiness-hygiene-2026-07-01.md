---
type: handoff
artifact_subtype: releaser-to-eunomia
initiative: asana-readiness-hygiene
handoff_type: validation
from_rite: releaser
to_rite: eunomia
from_station: pipeline-monitor (landing close)
created: 2026-07-01
status: proposed
rung_cap: DEPLOY-DISPATCHED
telos: .know/telos/asana-readiness-hygiene.md (verification_deadline 2026-07-15)
---

# HANDOFF: releaser → eunomia — asana-readiness-hygiene (landing close, 2026-07-01)

> **Who reads this**: eunomia (prod-health verification) + the verified-realized attester.
> **Boundary**: releaser drove BOTH landings to **DEPLOY-DISPATCHED** (its honest cap). Everything
> past the `‖` — deploy-completed, prod-converged, prod-healthy — is **UNATTESTED**, eunomia's. Do NOT
> read DEPLOY-DISPATCHED as prod-healthy.

## §1 · What LANDED (receipts — Gate-C anchored)

Two independent PATCH landings into `autom8y/autom8y-asana`, both merged to `main`:

| Landing | merged (squash) | CI-GREEN@main | DEPLOY-DISPATCHED |
|---|---|---|---|
| **docs #177** — 102 `.know/.ledge` telos/ADR/review docs | `243351b9` | Test@main success | Satellite Dispatch run **`28523841726`** success @14:10:52Z |
| **hygiene #176** — 36 dead-noqa removal + RUF100/lint-noqa-drift drift-guard | `dd63e667` | Test@main run **`28524604303`** success @14:28:39Z | Satellite Dispatch run **`28524983437`** success @14:28:50Z |

- **D2 resolved**: `secretspec.toml` kept **TRACKED** (the untrack was dropped — a pre-existing parity test `tests/unit/metrics/test_main.py::TestPreflightParity::test_inline_and_secretspec_enforce_same_required_vars` `open()`s it; a fresh CI checkout without it → FileNotFoundError). Confirmed re-tracked + the test PASSED on the fixed head `f8b1fc96`.
- Hygiene `/files` = 24 (22 src comment-only + `pyproject.toml` RUF100 per-file-ignore + `justfile` lint-noqa-drift); KEEP-floor (`idempotency.py` 7×BLE001 incl `:770`) untouched.

## §2 · Rungs achieved + the ‖ boundary

`merged` ✓ (both) < `CI-GREEN@main` ✓ (both) < **`DEPLOY-DISPATCHED` ✓ (both) ‖** `deploy-completed` · `prod-converged` · `prod-healthy` · `verified-realized` — **ALL UNATTESTED (eunomia / telos)**. Releaser self-attestation caps at DEPLOY-DISPATCHED; the Satellite-Dispatch success is the dispatch of the downstream a8 deploy, NOT its completion or health.

## §3 · What eunomia verifies (prod-health — ADVISORY)

- **Nightly Live Smoke / CON-2 Freeze Smoke** on the new `main` (`dd63e667`). `[UNATTESTED — eunomia]`.
- **⚠️ Pre-existing signal**: `Nightly Live Smoke` was **RED on `cb4b4201`** (run on the pre-landing main, scheduled) — this PREDATES both landings (the cleanup is comment-only + docs-only, no runtime change; it cannot be the cause). Eunomia to assess whether it clears or persists on `dd63e667` and triage independently. `[prod-health-NEGATIVE, pre-existing — eunomia's]`.

## §4 · verified-realized → telos 2026-07-15

The telos `verified_realized` (drift-guarded-over-time: no dead-noqa re-accretion) is attested by the rite-disjoint attester by **2026-07-15**. **⚠️ weakened by L-001**: the `lint-noqa-drift` RUF100 drift-guard runs in local `just check` but is **NOT wired into the CI Lint job** (`ci / Lint & Type Check` runs `ruff check .` WITHOUT `--extend-select RUF100`) — so the drift-guard does NOT enforce in CI. Until L-001 is fixed, "drift-guarded-over-time" holds only for developers who run `make lint-noqa-drift` locally. The attester should note this gap.

## §5 · DEFER register (watch-registered, named)

| Item | Route | Note |
|---|---|---|
| **L-001** — RUF100 drift-guard not in CI lint | **sre / 10x-dev** | wire `ruff check src/ --extend-select RUF100` (or add RUF100 to the CI lint select, `--fix`-safe) into the CI Lint job so the drift-guard enforces on PRs |
| **67 narrowings** (62 multi-code `type:ignore` + 5 file-blanket E402) | **hygiene-pass-2** (`/frame`) | manual mypy bisection on the now-landed vacancy-free floor |
| **ASANA_PAT** `_ARN`-first vs `--provider env` coherence gap | **arch / security** | separate initiative |
| ~~secretspec.toml.example~~ | **CLOSED** | resolved by keeping `secretspec.toml` tracked (D2) — the manifest stays version-controlled + diff-reviewable; no `.example` needed |

## §6 · Levers + boundary

- Worktree `/private/tmp/hygiene-readiness` removed post-merge (ref merged, durable). The merged branches (`hygiene/asana-readiness`, `docs/telos-ledge-sweep-preserve`) may be GitHub-auto-deleted or operator-pruned.
- Do NOT dispatch eunomia specialists from releaser — the operator switches rites (`ari sync --rite=eunomia`).

*Releaser landing close. Both landings DEPLOY-DISPATCHED (honest cap). Prod-health + verified-realized are eunomia's / the telos attester's. Production levers were DELEGATED for landing this session; the D2 CI-read RED was correctly re-gated to + resolved by the operator.*
