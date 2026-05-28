---
type: decision
artifact_id: ADR-007-verify-denominator-congruence
schema_version: "1.0"
status: accepted
disposition_weight: MEDIUM   # advisory weight; not load-bearing
authored_by: architect-enforcer (hygiene rite)
authored_at: 2026-05-27
initiative: freshness-verification-recency
upstream_handoff: .ledge/spikes/HANDOFF-10x-dev-to-hygiene-pr67-ruff-format-2026-05-27.md
upstream_item: HYG-002
evidence_grade: MODERATE   # self-authored disposition; self-ref ceiling per self-ref-evidence-grade-rule
disposition_kind: process-boundary   # NOT a code edit; advisory per HYG-002 AC
implements_in_pr67: false   # per handoff AC: if accepted, spawns a SEPARATE work item
---

# ADR-007 — Verify-Denominator Congruence (local-verify ⊇ CI-verify)

> Disposition for **HYG-002** from
> `HANDOFF-10x-dev-to-hygiene-pr67-ruff-format-2026-05-27.md` (items[1]).
> Process/boundary decision — NOT a code edit. HYG-001 fixed the symptom
> (PR #67 `ci / Lint & Type Check` green); this is the durable systemic call.

## 1. The boundary framed as a contract

Two verification surfaces exist for every change to this repo:

- **local-verify** — what a developer/agent runs before push.
- **CI-verify** — what `ci / Lint & Type Check` runs as a required check.

The invariant that MUST hold: **local-verify ⊇ CI-verify** (local is a superset of,
or congruent with, the CI command set). When local-verify is a *strict subset* of
CI-verify, a violation can pass local and fail CI — which is exactly the PR #67
failure: local ran `ruff check` + `mypy` but NOT `ruff format --check`; CI ran all
three. The durable fix must make this divergence **structurally hard to introduce**,
not memory-dependent.

## 2. Repo reality (SVR — direct inspection, claim-assertion-time)

The spike's option framing ("(b) = add a recipe", "(a) = add a hook") is
**falsified by repo state**. Both mechanisms already exist. The real defect is
narrower: the existing aggregate recipe is **not CI-congruent**.

**SVR-1 — `just fmt-check` already exists (formatter check IS available locally)**
```yaml
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/repos/autom8y-asana/justfile"
  line_range: "L79-L81"
  marker_token: "fmt-check:\n    uv run ruff format . --check"
  claim: "a canonical local recipe for the CI formatter-check command already exists; option (b) is NOT 'add a recipe' — the formatter-check target is already present and runnable as `just fmt-check`"
```

**SVR-2 — the `check` aggregate calls the MUTATING `fmt`, not `fmt-check`**
```yaml
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/repos/autom8y-asana/justfile"
  line_range: "L127-L129"
  marker_token: "# Full CI-equivalent check\n[group('quality')]\ncheck: fmt lint typecheck test"
  claim: "the aggregate `check` recipe depends on `fmt` (which mutates files via `ruff format .`) rather than `fmt-check` (which fails on drift); a mutating step cannot detect-and-fail, so the aggregate SILENTLY rewrites formatting locally instead of surfacing the violation CI would surface — this is the precise congruence break"
```

**SVR-3 — `check`'s typecheck/lint flags diverge from CI**
```yaml
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/repos/autom8y-asana/justfile"
  line_range: "L85-L91"
  marker_token: "lint:\n    uv run ruff check . --fix"
  claim: "`lint` runs with `--fix` (mutating) and `typecheck` runs `mypy src/ --strict` without `--no-sources`; CI runs ruff check non-mutating + mypy on `src/autom8_asana` with `--no-sources` (test.yml:47 mypy_targets + the satellite reusable workflow), so even the aggregate's lint/type legs are not byte-congruent with CI"
```

**SVR-4 — pre-commit ALREADY has `ruff-format` (option (a) substantially exists)**
```yaml
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/repos/autom8y-asana/.pre-commit-config.yaml"
  line_range: "L23-L24"
  marker_token: "- id: ruff-format\n        types_or: [python, pyi]"
  claim: "a pre-commit `ruff-format` hook is already configured; option (a) is NOT 'add a hook' — it exists. The PR #67 failure therefore implies pre-commit was not installed/run in the engineer's loop (a hook that is skippable with `--no-verify` or simply not `pre-commit install`-ed), which is why it did not catch the drift"
```

**SVR-5 — CI's Lint & Type Check lives in an external pinned reusable workflow**
```yaml
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/repos/autom8y-asana/.github/workflows/test.yml"
  line_range: "L44-L48"
  marker_token: "uses: autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml@cbc3c58e"
  claim: "the authoritative CI command set is defined in an external SHA-pinned reusable workflow, NOT in this repo; the local-verify surface must be hand-maintained to mirror a definition that lives in another repo — this is the structural reason denominator drift recurs and the reason a self-checking local mirror (not memory) is required"
```

**SVR-6 — CI formatter actually fired on PR #67 (the failure denominator)**
```yaml
verification_method: docs-cite-verbatim
verification_anchor:
  source: ".ledge/spikes/HANDOFF-10x-dev-to-hygiene-pr67-ruff-format-2026-05-27.md"
  line_range: "L27"
  marker_token: "uv run --no-sources ruff format . --check` exits 0 on the branch (currently exits 1 with `2 files would be reformatted`)"
  claim: "the CI-verify surface includes `ruff format --check` with `--no-sources`; this is the exact command absent from local-verify that produced the subset-not-superset failure"
```

## 3. Disposition per option

Boundary test applied to each: *does it make local-verify ⊇ CI-verify structurally,
or does it paper over the gap with memory/opt-in?*

| Opt | Spike framing | Repo reality | Boundary verdict | Disposition |
|-----|---------------|-------------|------------------|-------------|
| (a) pre-commit `ruff format --check` on staged files | "add a hook" | **Already exists** (SVR-4). Gap is install/run-discipline, not absence. Skippable with `--no-verify`; staged-only ≠ whole-repo `.` ; depends on `pre-commit install`. | Enforced-at-commit but **opt-in + skippable + staged-scope-narrower-than-CI**. Closes part of the gap only if installed AND not bypassed. | **ACCEPT (already-present; recommend "ensure-installed" doc, not new config)** |
| (b) single `just verify` recipe mirroring EXACT CI set | "add a recipe" | A `check` aggregate **exists but is NOT CI-congruent** (SVR-2/SVR-3): calls mutating `fmt`, lint `--fix`, mypy without `--no-sources`. | A **single canonical, NON-mutating, CI-byte-congruent** target is the strongest structural mirror. Still opt-in (must be run), but it is the one command an engineer/agent dispatch can name, and it cannot *silently rewrite* drift the way today's `check` does. | **ACCEPT — primary recommendation** (fix existing aggregate, do not add a parallel one) |
| (c) add `ruff format --check` to principal-engineer agent build-checklist | doc fix | Agent-prompt edit; no repo artifact. | **Memory/documentation-dependent.** Closes nothing structurally — relies on the agent reading and obeying the checklist. Necessary as a *pointer* to (b), not a fix in itself. | **ACCEPT (subordinate to (b): the checklist should say "run `just verify`", not re-enumerate commands)** |
| (d) CI `--fix` autocommit on PR branches | heavier | Would change review semantics; bot commits to PR head. | Enforced-in-CI but **mutates review surface, breaks atomic-commit/Boy-Scout discipline, can race with author pushes**. Over-engineered for a whitespace gate. | **REJECT** |

## 4. Recommendation

**Accept (b) as the primary durable fix, with (c) subordinate to it, and (a) as a
pre-existing belt-and-suspenders that needs install-discipline — not new config.**

Concretely, the follow-up work item should:

1. **Make local-verify CI-congruent (the actual fix).** Add/repair a single
   canonical **non-mutating** target — name it `verify` (distinct from the
   developer-convenience mutating `fmt`/`lint`) — composed of exactly:
   `fmt-check` (`ruff format . --check`) + non-mutating `ruff check .` +
   `mypy src/autom8_asana` mirroring CI's flags (incl. `--no-sources` where CI
   uses it). The defect is that today's `check` aggregate (justfile:129) calls
   the **mutating** `fmt` and `--fix` lint, so it cannot fail on drift — it hides
   it (SVR-2/SVR-3). `verify` MUST be the detect-and-fail mirror.
2. **Point the agent checklist at the target, not the commands (c).** The
   principal-engineer build-checklist should read "before push, run `just verify`
   and require exit 0" — a single named target, so the checklist cannot itself
   drift out of sync with CI the way an enumerated command list would.
3. **Ensure pre-commit is installed (a).** `ruff-format` is already configured
   (SVR-4); the durable action is documenting/enforcing `pre-commit install` in
   onboarding so the existing hook actually fires. No config change required.

Why this closes the boundary rather than papering it: (b)+(c) collapse the
local-verify surface to a **single named, non-mutating, CI-byte-congruent
command**. The recurring root cause (SVR-5: CI's command set lives in an external
pinned reusable workflow the local repo can't see) means a hand-maintained local
mirror is unavoidable — but a *single* mirror target is auditable in one place and
nameable in dispatch, whereas memory (c-alone) and skippable hooks (a-alone) are not.

**Residual divergence risk (named, not hidden):** because CI's authoritative
definition is in `autom8y-workflows@<sha>` (SVR-5), `just verify` can still drift
when that pinned SHA bumps. The follow-up should add a one-line comment in the
`verify` recipe citing the reusable-workflow SHA it mirrors, so the next SHA bump
has a visible re-sync anchor. This is the structural limit of option (b): it
mirrors, it does not derive. Full derivation (CI and local sourcing one command
list) is an architecture-level change crossing the repo boundary into
autom8y-workflows — **out of hygiene scope; route to arch/SRE if ever pursued.**

## 5. Scope & routing (per HYG-002 AC)

- **IN SCOPE for a follow-up work item / own PR — NOT folded into PR #67.**
  Per the handoff AC ("If accepted, hygiene routes a separate work item (own PR)
  to implement — not folded into PR #67") and the tradeoff_points scope-discipline
  fence. PR #67 ships HYG-001 only.
- **Work item shape:** single hygiene PR — `chore(justfile): add CI-congruent
  non-mutating `verify` target + doc pre-commit install + agent-checklist pointer`.
  Small, atomic, behavior-preserving (no `src/` changes).
- **NOT a load-bearing architectural decision.** Advisory/MEDIUM weight. The
  cross-boundary derivation option (CI ↔ local single-source) is explicitly
  fenced out of this disposition and would require arch/SRE if pursued.

### Defer-watch (the one piece that is genuinely deferred)

The **external-reusable-workflow re-sync** concern (SVR-5 residual) is deferred,
not fixed, by this disposition. Watch-trigger for `.know/defer-watch.yaml`:

```yaml
- id: verify-denominator-resync
  rationale: >
    `just verify` mirrors CI's command set by hand; CI's authoritative set lives
    in autom8y-workflows@<sha> (SVR-5). A SHA bump can silently re-open denominator
    drift.
  watch_trigger: >
    Any bump of the satellite-ci-reusable.yml pin in .github/workflows/test.yml
    (currently @cbc3c58e, test.yml:45) OR any new lint/format/type step added to
    that reusable workflow.
  escalation_path: hygiene follow-up PR to re-sync `just verify`; if CI grows a
    step class local cannot mirror, route to arch/SRE.
  owner_rite: hygiene
```

## 6. Acid test

If a follow-up PR implements §4, then a developer or agent running `just verify`
gets exit 1 on the *exact* condition CI would fail on (formatter drift included),
**without rewriting files behind their back** — the local surface becomes a true
superset of CI. That is the measurable boundary closure; everything else
(checklist text, pre-commit install) is a pointer to it.

---

**Evidence ceiling: MODERATE** (self-authored disposition; `self-ref-evidence-grade-rule`).
All repo-state claims carry SVR receipts (§2) verified by direct file-read at
authorship time. Disposition is advisory; implementation is a separate work item.
