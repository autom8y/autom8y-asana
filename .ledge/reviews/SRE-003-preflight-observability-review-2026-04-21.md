---
type: review
review_subtype: observability-review
status: accepted
lifecycle_state: accepted
rite: sre
agent: observability-engineer
disposition: skip-with-rationale
handoff_item: SRE-003
links_to: HANDOFF-hygiene-asana-to-sre-2026-04-21
schema_version: "1.0"
date: "2026-04-21"
evidence_grade: moderate
source_artifacts:
  - .ledge/reviews/HANDOFF-hygiene-asana-to-sre-2026-04-21.md
  - .ledge/specs/TDD-cli-preflight-contract.md
  - .ledge/decisions/ADR-env-secret-profile-split.md
  - src/autom8_asana/metrics/__main__.py
provenance:
  - source: "Repo-wide grep for `python -m autom8_asana.metrics` and `autom8_asana.metrics.__main__` on HEAD ac71e942 2026-04-21"
    type: code
    grade: strong
  - source: ".github/workflows/ enumeration 2026-04-21 — zero matches for CLI entrypoint module"
    type: code
    grade: strong
  - source: "Dockerfile CMD inspection — lambda_handlers.cache_warmer.handler (lib-mode), not the metrics CLI"
    type: code
    grade: strong
  - source: "TDD-0001-cli-preflight-contract §Scope — explicit out-of-scope for FastAPI + Lambda + other CLI-ish scripts"
    type: artifact
    grade: strong
---

# SRE-003 — Observability review: CFG-006 CLI preflight exit-code-2

## Disposition

**SKIP-WITH-RATIONALE.** The CFG-006 CLI preflight is a dev/IDE/interactive-shell hygiene gate that never runs in a production-runtime context. There is no SLI/SLO worth here; instrumenting it would manufacture a synthetic signal disconnected from user impact and violate the symptom-based alerting principle [SR:SRC-001 Beyer et al. 2016] [STRONG | 0.72 @ 2026-04-01].

## Question-by-question findings

### Q1 — Where does the CLI run?

**Evidence (STRONG):** Repo-wide grep (`python -m autom8_asana\.metrics|autom8_asana\.metrics\.__main__|metrics/__main__`) on HEAD `ac71e942` returns hits only in:
- `.know/env-loader.md`, `.know/feat/INDEX.md`, `.know/feat/business-metrics.md`, `.know/architecture.md` — documentation
- `src/autom8_asana/metrics/__main__.py` itself (module docstring + error template)
- `secretspec.toml:15` — header comment describing the profile split
- `pyproject.toml:276` — ruff per-file-ignore for `T201` (print-statement allowance)
- `tests/unit/metrics/test_main.py`, `tests/unit/metrics/test_compute.py` — unit tests

**Zero hits** in `.github/workflows/` (8 workflow files enumerated: `aegis-synthetic-coverage.yml`, `dependency-review.yml`, `gitleaks.yml`, `satellite-dispatch.yml`, `scorecard.yml`, `test.yml`, `trufflehog-scan.yml`, `zizmor.yml`), `Dockerfile`, `Dockerfile.dev`, `docker-compose*.yml`, `scripts/*.sh`, `src/autom8_asana/lambda_handlers/*.py`.

Dockerfile `CMD` is `["autom8_asana.lambda_handlers.cache_warmer.handler"]` — lib-mode, not the metrics CLI. Per ADR-0001 §Profile partition, Lambda handlers validate against `[profiles.default]` and never invoke `_preflight_cli_profile()`.

**Conclusion:** operational-runtime surface area is zero. This is a dev/IDE interactive CLI, confirmed by the handoff's stated context.

### Q2 — Blast radius of a preflight failure

**Evidence (STRONG):** Reading `src/autom8_asana/metrics/__main__.py:64-114`:
- Preflight is fail-fast by design (exit code 2, structured stderr with 3 config-file pointers).
- No retry, no network call, no filesystem write; TDD-preflight §Side-effects explicitly forbids all three.
- Downstream code path (`load_project_dataframe`) never executes when preflight fails.

There is **no silent-failure path** where exit-2 would mask a production issue. Exit-2 exclusively means "dev env misconfigured before any S3 call was attempted." The alternative-to-preflight is a deep transport exception with an unhelpful message — that was the smell CFG-006 was designed to fix.

### Q3 — Does any consumer treat exit-2 as a signal?

**Evidence (STRONG):** Zero programmatic consumers of the module exit code. No CI workflow, shell script, Makefile target, or Lambda handler invokes `python -m autom8_asana.metrics` and parses its exit code. The only consumers are:
- Human operators reading stderr (the intended audience — the error message is optimized for copy-paste remediation)
- Unit tests that import functions directly (not subprocess-invoke the module)

No SLI-worthy consumer exists.

### Q4 — Precedent for dev-config-preflight SLOs in the fleet

**Evidence (STRONG):** `ls .ledge/specs/SLO-*.md` returns zero files. The fleet has no precedent for SLO tracking on dev-config gates. The existing `.ledge/specs/` artifacts are all ADRs, TDDs, playbooks, and coordination dashboards — no SLO specs at all, let alone for dev-tooling gates.

There is no alignment benefit to introducing the first fleet SLO on a dev-only surface.

### Q5 — Hypothetical SLI/SLO if opt-in chosen

For completeness, a hypothetical opt-in would look like:
- **SLI**: `count(cli_preflight_pass) / count(cli_preflight_invocations)` over a 7-day rolling window
- **SLO**: >=99% pass rate
- **Instrumentation**: OTel span event or Prometheus counter emission inside `_preflight_cli_profile` success branch + exit-2 branch
- **Additional artifacts**: dashboard config + multi-burn-rate alerting rule [SR:SRC-002 Beyer et al. 2018] [STRONG | 0.72 @ 2026-04-01]

**Cost**: ~60-90 minutes instrumentation + ~30 minutes dashboard + ~30 minutes alert tuning = ~2-2.5 hours.

**Value analysis**: The SLI would measure "how often do developers have a properly-configured dev env when they run a CLI command?" This is a **cause-based metric**, not a symptom-based one — a preflight failure correlates with zero user impact because no user-facing traffic ever flows through this CLI. Per the symptom-based alerting principle [SR:SRC-001 Beyer et al. 2016], alerting on this would be a textbook cause-based anti-pattern.

Worse: a low pass rate would be ambiguous signal (fresh clones before `direnv allow`? intentional negative-path testing in CI? a developer typo?) with no clear operational response. This is the "Unactionable alerts" anti-pattern.

## Rationale for SKIP

Four independent signals all point to SKIP:

1. **No operational surface** — Q1 confirms zero production-runtime invocation.
2. **No programmatic consumer** — Q3 confirms no caller treats exit-2 as a signal.
3. **Cause-based, not symptom-based** — a preflight-pass-rate metric measures dev-env hygiene, not user-facing reliability. Symptom-based alerting principle forbids paging on cause [SR:SRC-001 Beyer et al. 2016] [STRONG | 0.72 @ 2026-04-01].
4. **No fleet precedent** — Q4 confirms no SLO tradition for dev-tooling gates; opt-in would create precedent for a problematic pattern (SLOs on developer ergonomics).

ADR-0001 itself frames the CLI/lib-mode split as a **developer ergonomics** concern ("fresh-clone developers who haven't completed CFG-001 [...] see the preflight surface a loud, actionable error"). The error template is optimized for human-readability (3 file-path pointers, copy-paste fix hints), not machine-parseability. An SLI layer on top would be retrofitting operational signal onto a humane dev-UX surface — the wrong tool for the wrong layer.

The handoff tradeoff_points §sre_scope_boundary explicitly framed SRE-003 as a deferred-opt-in with skip as the expected default. The evidence corroborates that expectation.

## Conditions that would change this disposition

Revisit SRE-003 IF any of the following become true:

1. **CLI becomes operationally invoked.** If a future cron job, scheduled Lambda, GitHub Actions workflow, deploy script, or Makefile target begins invoking `python -m autom8_asana.metrics <metric>` and consuming its output, the exit code transitions from human-readable error to machine-consumed signal. At that point, preflight-pass-rate becomes a legitimate operational SLI.
2. **Exit-code-2 parsing appears in any caller.** If any consumer (CI gate, orchestration script, downstream tool) begins branching on exit-2 vs exit-1, the preflight becomes a contract between services rather than a human-facing check. Treat as SLI-worthy.
3. **Multiple CLI entrypoints emerge with divergent preflight behavior.** TDD-preflight §Explicitly-out-of-scope anticipates "other CLI-ish scripts" would each get their own TDD. If 2+ CLI entrypoints with preflight checks exist, a shared SLI across them may become worthwhile for regression detection.
4. **Fleet adopts SLO discipline for dev-tooling generally.** If the fleet establishes a pattern of SLOs on dev-environment ergonomics (e.g., developer-facing dashboard measuring fresh-clone-to-first-successful-invocation time), CLI preflight could join that family with aligned measurement semantics.

None of the above are projected for the current or next sprint horizon.

## Scope confirmation

- No instrumentation added; no metrics emission code written; no preflight implementation touched.
- No SLO spec authored (not warranted under SKIP disposition).
- Review bounded strictly to CFG-006 CLI preflight; no cross-service scope expansion.
- Throughline `canonical-source-integrity` N_applied remains 1 (untouched; this review is pure `.ledge/` disposition documentation).
- Evidence grade capped at MODERATE per `self-ref-evidence-grade-rule`: this is an intra-rite review without external corroboration, and STRONG would require independent SRE peer review.

## Links

- Handoff: `.ledge/reviews/HANDOFF-hygiene-asana-to-sre-2026-04-21.md` §items[SRE-003]
- TDD: `.ledge/specs/TDD-cli-preflight-contract.md`
- ADR: `.ledge/decisions/ADR-env-secret-profile-split.md`
- Implementation (read-only reference): `src/autom8_asana/metrics/__main__.py:17-114`
- Evidence citations: `.claude/skills/sre-ref/INDEX.md` (SR:SRC-001 Beyer 2016, SR:SRC-002 Beyer 2018)
