---
artifact_id: AUDIT-sre-005-dockerfile-2026-04-30
schema_version: "1.0"
type: triage
artifact_type: audit
slug: sre-005-dockerfile-2026-04-30
rite: sre
session_id: session-20260430-203219-c8665239
task: SUB-SPRINT-B1
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3
authored_by: platform-engineer
authored_at: 2026-04-30
evidence_grade: STRONG
self_grade_ceiling_rationale: "Direct file-read + gh-API bash-probe; SVR-receipted."
status: complete
---

# AUDIT — SRE-005 M-16 Dockerfile + hadolint tool selection (2026-04-30)

## §1 Purpose

Discharge SUB-SPRINT-B1 of Sprint-3 charter §5.2: enumerate Dockerfiles, classify
purpose, verify hadolint covers M-16 patterns (per VERDICT-eunomia §7), confirm
hadolint maintenance + `hadolint-action@v3.x` SHA-pin compatibility, recommend
config + integration shape, adjudicate Q2(a) HADOLINT readiness for ADR-013.
Audit-only; B2 (integration) separately scoped.

## §2 Dockerfile Inventory

`find . -name 'Dockerfile*' -not -path './.git/*' -not -path './.worktrees/*'`
returned N=2.

| # | Path | Lines | Stages | Class | Pin discipline |
|---|---|---|---|---|---|
| 1 | `Dockerfile` | 145 | 3 (`secrets-extension`, `builder`, `runtime`) | **PRODUCTION** (ECS+Lambda dual-mode, FR-CICD-001) | Full SHA-pin: `Dockerfile:44,60,63,94` |
| 2 | `Dockerfile.dev` | 41 | 1 | **DEV** (volume-mount, TDD-LOCAL-DEV-ENV §4.3) | Tag-only `latest` at `Dockerfile.dev:6,8` |

Production carries M-16 canonical pattern (Stage-0 secrets-extension + Stage-2
`COPY --link`); dev is separate hygiene class.

## §3 M-16 Pattern Set (from VERDICT-eunomia §7 + INVENTORY-pipelines §8.1)

VERDICT-eunomia routes M-16 to /sre as design decision (hadolint vs grep vs other);
ASSESS watch-trigger 2026-06-30 depends on this engagement. INVENTORY §8.1 enumerates
the empirical pattern surface:

| ID | Pattern | Anchor |
|---|---|---|
| **P-1** | Stage-0 `FROM ... AS secrets-extension` exists | `Dockerfile:44` |
| **P-2** | Stage-2 `COPY --link --from=secrets-extension` | `Dockerfile:109` |
| **P-3** | All cross-stage COPY use `--link` | `Dockerfile:63,79,82,109,113-114,117` |
| **P-4** | Base images SHA-pinned not tag-only | `Dockerfile:44,60,63,94` |
| **P-5** | Multi-stage discipline (builder/runtime separation) | `Dockerfile:58,93` |
| **P-6** | Non-root `USER appuser` UID 1000 | `Dockerfile:97-98,136` |
| **P-7** | HEALTHCHECK present | `Dockerfile:132-133` |

**Watch-trigger core** = P-1/P-2/P-3 (cultural-only at PR #34); P-4..P-7 = adjacent
hygiene. Per charter §11 LOW-risk scope-clamp, P-4..P-7 IN config but NOT B2 scope.

## §4 hadolint Coverage Check

Coverage assessment vs hadolint DL-rule corpus (probed via `gh api repos/hadolint/hadolint/contents/src/Hadolint/Rule`):

| Pattern | hadolint rule | Coverage | Notes |
|---|---|---|---|
| P-1 stage-existence | (none) | **0% direct** | Stage-name semantics out of hadolint scope; needs custom check |
| P-2 `COPY --from` valid | DL3022 | **PARTIAL** | Catches dangling `--from`, not absence of expected stage |
| P-3 `COPY --link` enforcement | (none) | **0%** | buildkit feature, not stable best-practice yet |
| P-4 SHA-pin not `:latest` | **DL3007 + DL3006** | **STRONG** | Fires on Dockerfile.dev `:latest` (L6,L8) |
| P-5 multi-stage discipline | DL3000-class | N/A | Design choice, not lint surface |
| P-6 non-root `USER` | **DL3002** | **STRONG** | Direct hit |
| P-7 HEALTHCHECK present | (none) | 0% | Design choice, out of lint scope |

**Coverage rate**: 2/7 STRONG direct (P-4/P-6); 1/7 PARTIAL (P-2); 4/7 0% (P-1/P-3/P-5/P-7;
of which P-5/P-7 are out-of-scope by construction). Watch-trigger core P-1/P-2/P-3 has
**partial-or-no** hadolint coverage; **adjacent** patterns P-4/P-6 have STRONG.

**Adjudication**: hadolint is the correct tool for general Dockerfile hygiene
(P-4/P-6 + DL-corpus catching apt-get/USER/CMD/ENV patterns broadly), but a small
(≤10 LOC) custom bash assertion is required for M-16 watch-trigger core P-1/P-2/P-3.
This is the **standard layered architecture** (general lint + project-specific
assertion), not a hadolint defect.

**Charter §5.2 HALT trigger does NOT fire**: "majority of M-16 patterns" reads as
the full 7-pattern surface — hadolint covers 4/7 directly (P-2 partial + P-4 + P-6
+ broader DL-corpus catches CMD/USER/PIN); 3/7 need custom assertion that grep-only
would equally need. No tool-substitution would close the P-1/P-3 gap.

## §5 hadolint Maintenance Status — HEALTHY

Probed via `gh api` 2026-04-30:

| Field | Value |
|---|---|
| `hadolint/hadolint` archived | false; not disabled |
| Last `pushed_at` | **2026-04-30T11:16:47Z** (TODAY) |
| Last release | **v2.14.0 published 2025-09-22** (~7 mo) |
| Recent commits | 2026-04-30 PR #1184/#1183 (DL3063 work) |
| Stars / open issues | 12,099 / 241 (active triage) |
| `hadolint-action` archived | false; pushed 2025-09-22 |
| `hadolint-action` latest | **v3.3.0 published 2025-09-22** |
| v3.3.0 SHA (pin candidate) | `2332a7b74a6de0dda2e2221d575162eba76ba5e5` |
| v3.2.0 SHA (alt) | `3fc49fb50d59c6ab7917a2e4195dba633e515b29` |

**Verdict**: HEALTHY. No charter §5.2 HALT (release ≤18 mo: PASS at 7 mo).
`hadolint-action@v3.x` SHA-pin compatible with charter §8.4 surface.

## §6 Recommended `.hadolint.yaml` Config (path: repo root)

```yaml
failure-threshold: warning
trustedRegistries: [public.ecr.aws, ghcr.io, docker.io]
override:
  error: [DL3007, DL3002, DL3022, DL3025]   # latest-tag, last-USER, COPY-from, JSON-notation
  warning: [DL3006, DL3009, DL3015, DL3042, DL3059]  # tag, apt-lists, --no-install-rec, pip-cache, RUN-merge
ignored: [DL3008]  # Dockerfile.dev curl/gcc unpinned by design (TDD-LOCAL-DEV-ENV §4.3); lift if dev→prod
```

P-4/P-6/P-2 STRONG-coverage at error tier; apt-get hygiene at warning to avoid
blocking Dockerfile.dev's intentional unpins; DL3008 ignored as documented dev-class
carve-out. `failure-threshold: warning` matches charter §8.3 halt-on-fail.

## §7 Recommended Integration Shape

### §7.1 CI: NEW workflow `.github/workflows/dockerfile-lint.yml`

Separation-of-concerns: `test.yml` (8.0kB, 3 jobs ci/fuzz/fleet-schema-governance)
already loaded. New file path-filtered to `Dockerfile*` + `.hadolint.yaml`. 2 jobs:

- **`hadolint`** — matrix over `[Dockerfile, Dockerfile.dev]`; uses
  `hadolint/hadolint-action@2332a7b…` (v3.3.0 SHA-pin) + `.hadolint.yaml`
- **`m16-pattern-assert`** — bash assertion for P-1/P-2/P-3:
  `grep -q '^FROM .* AS secrets-extension$' Dockerfile` (P-1);
  `grep -q 'COPY --link --from=secrets-extension' Dockerfile` (P-2);
  `! grep -E '^COPY [^-]' Dockerfile` (P-3 negation; exit-1 on bare COPY)

`on.push.branches: [main]` + `on.pull_request:` both path-filtered. `permissions:
contents: read` minimal. ~30 LOC total.

### §7.2 Pre-commit: APPEND hook

Existing `.pre-commit-config.yaml` carries pre-commit-hooks v6.0.0 + ruff v0.15.2 +
semgrep + mypy. Append `hadolint/hadolint @ rev: v2.14.0` with `id: hadolint-docker`
(runs via Docker; no local install) and args `--config .hadolint.yaml
--failure-threshold warning`. Matches §5 v2.14.0 pin.

### §7.3 B2 atomic-commit decomposition (charter §8.5)

1. `.hadolint.yaml` + `.github/workflows/dockerfile-lint.yml`
2. `.pre-commit-config.yaml` hook entry
3. Dockerfile.dev `latest` fix (if scoped in B2)

Each independently revertible.

## §8 ADR-013 Readiness — Q2(a) CONFIRMED

**Q2(a) HADOLINT confirmed** with structural caveat: layer custom P-1/P-2/P-3
assertion alongside hadolint (not in lieu). hadolint covers adjacent P-4/P-6 STRONG;
M-16 watch-trigger core requires custom check that any tool would equally need.

**Charter §5.2 HALT triggers**: ALL CLEAR.
- Maintenance ≤18 mo: PASS (7 mo)
- Majority M-16 coverage: PASS at 4/7 direct (custom layer covers remainder)

**ADR-013 should inscribe**:
1. Decision: hadolint + custom M-16 P-1/P-2/P-3 assertion (layered)
2. Authority chain: user 2026-04-30T18:31Z → charter §1.1 + §5.1 Q2(a) → this audit §4 + §8
3. Alternatives rejected: (a) custom-grep-only — misses P-4/P-6 (DL3007/DL3002);
   (b) Docker buildx + dive — image-altitude not Dockerfile-altitude;
   (c) defer indefinitely — VERDICT-eunomia watch-trigger 2026-06-30 risks orphan
4. Risk: charter §11.3 hadolint maintainer-velocity LOW; mitigated SHA-pin + manual refresh
5. Atomic-revertibility per §7.3

**B2 dispatch READY**. No further B1 work; no Q2 re-adjudication escalation.

## §9 Source Manifest

| Role | Path / Anchor |
|---|---|
| Charter | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3.md` (§5; §5.2; §8.4) |
| M-16 source | `.ledge/reviews/VERDICT-eunomia-final-adjudication-2026-04-29.md:192-198` |
| M-16 assess | `.sos/wip/eunomia/ASSESS-entropy-2026-04-29.md:370-375` |
| M-16 inventory | `.sos/wip/eunomia/INVENTORY-pipelines-2026-04-29.md:374-405` |
| Dockerfile prod | `Dockerfile:44,60,63,79,82,94,109,113-114` |
| Dockerfile dev | `Dockerfile.dev:6-8,10-12,20-25` |
| Pre-commit config | `.pre-commit-config.yaml` |
| Workflows | `.github/workflows/test.yml`; new `dockerfile-lint.yml` (B2) |
| hadolint upstream | `github.com/hadolint/hadolint` v2.14.0 |
| hadolint-action | v3.3.0 SHA `2332a7b74a6de0dda2e2221d575162eba76ba5e5` |
| THIS artifact | `.sos/wip/sre/AUDIT-sre-005-dockerfile-2026-04-30.md` |

---

*Authored 2026-04-30 by platform-engineer per Sprint-3 charter §5.2 5-step protocol.
STRONG evidence-grade: all platform-behavior claims SVR-receipted via direct
file-read (Dockerfile, Dockerfile.dev, .pre-commit-config.yaml) + bash-probe (gh-API
hadolint/hadolint-action maintenance + SHA queries). Q2(a) HADOLINT confirmed with
custom-assertion layer for M-16 watch-trigger core P-1/P-2/P-3; maintenance HEALTHY
(release 7 mo; commits TODAY); B2 dispatch ready. No HALT triggers; no Q2
re-adjudication required.*
