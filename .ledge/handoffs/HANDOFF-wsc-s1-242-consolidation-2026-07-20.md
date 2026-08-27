---
type: handoff
handoff_type: validation
status: draft
initiative: asana-mcp-postfelt-hardening
sprint: s1 (WS-C staged-surface-consolidation)
source_rite: hygiene (janitor seat)
target_rite: review (signal-sifter, rite-disjoint critic — PT-02)
date: 2026-07-20
pr: https://github.com/autom8y/autom8y-asana/pull/242
branch: feat/asana-mcp-v1-s6-assembly
old_head: b33cc1d9e039d8cae6cc400a0c97894525444247
new_head: 8cac6b9dfbeb79d83c783390a7c094753b6d36ce
base: origin/main 793e670b (four parent squashes 23440991/edaa9ddd/a0b7142d/793e670b present)
evidence_ceiling: MODERATE   # self-ref: janitor built, janitor attests; STRONG needs the critic
---

# HANDOFF — WS-C s1: #242 reconstructed as the assembly-only delta

## 1. What changed

PR #242 (s6 assembly, DRAFT, 9 commits, head `b33cc1d9`) predated the operator's
squash-merges of its parents (#239/#240/#238/#241) and main's pre-merge hygiene
wave. It was reconstructed — not rebased — as ONE commit atop fresh origin/main
`793e670b`: branch reset to main, unification + assembly delta re-materialized,
newest-of-each reconciliation applied, force-pushed to the PR's own branch
(sanctioned), checks watched to ALL GREEN, PR un-drafted.

Delta shape (24 files, +824/−53 vs origin/main, single commit `8cac6b9d`):

- **Unification move** (mirrors s6 `bec80158` atop the merged layout): deletes
  `src/asana_mcp/**`, `tests/asana_mcp/**`, `tests/mcp/**` in favor of the
  unified `mcp/asana_mcp` + `mcp/tests` tree. `timeouts.py` and
  `composite_write.py` land as byte-pure renames of main's hygiene'd copies;
  7 tests relocated: 1 byte-identical; 6 carry ONLY the mechanical I001 import re-sorts disclosed in §2 (first-party reclassification after the src/asana_mcp deletion) — corrected per PT-02 CONCUR-WITH-FLAGS(1), 2026-07-20.
- **Assembly surface** (from `b33cc1d9`): `mcp/asana_mcp/assembly.py` (+60),
  `mcp/serve_stdio.py` stdio launcher (+101), `mcp/probes/` C2 harness
  (+207/+72), `mcp/tests/test_assembly_floor.py` (+282), observability seam
  reconciliation (real fastmcp 3.4.4 registry, `_instrument_ctx_http` per
  FORK-D D3, settings-import fix), otel deps.
- **No new feature surface**: WS-B2 sidecar tag_name work absent (shape §5
  ride-vs-follow = FOLLOWS honored). Write flag stays OFF; no satellite
  `src/autom8_asana` surface touched; merges remain operator-reserved.

## 2. Newest-of-each reconciliation receipts

| Item | Ruling | Receipt |
|---|---|---|
| MCP-1 errors passthrough | main == b33cc1d9 byte-identical | `mcp/asana_mcp/errors.py` (git diff empty) |
| S105 false-positive annotation | main's two-line form kept | `mcp/asana_mcp/observability.py:143-144` (`# noqa: S105`) |
| Fence scanner (CodeQL cure) | main's regex form kept + s6 path fix + rglob | `mcp/tests/test_fences.py:13` (unified `_SRC`), `:21` (`_ASANA_ENDPOINT = re.compile`), `:25-26` (rglob) |
| mcp-island `[tool.ruff]` boundary | DROPPED — main's root config + `pyproject.toml:247` `"mcp/**"` per-file-ignores govern | `mcp/pyproject.toml` carries no `[tool.ruff]` at `8cac6b9d` |
| otel deps (assembly-semantic) | carried from b33cc1d9 | `mcp/pyproject.toml:36-37,49` |
| Unification path fixes | carried from b33cc1d9 | `mcp/tests/test_import_safety_obs.py:19`, `mcp/tests/test_composite_write_s3.py:33` |
| tools/__init__ docstring (composite_write + assembly note) | carried from b33cc1d9 | `mcp/asana_mcp/tools/__init__.py:8-13` |
| s2-newer main files (conftest, schemas, server, context, discovery, resolve, 5 tests) | main's copies kept wholesale | not branch-touched post `9003fa23` (s2 merge) — main strictly newer |
| Stale island-era noqa (`F821` on `instrument`) | removed; proven unnecessary under root config | `ruff check .` green without it |
| NEW: T201 for operator CLI entry points | narrow per-file-ignores added (launcher `--smoke` inventory + probe evidence bundle print by design) | `pyproject.toml:259-260` |
| NEW: I001 re-sorts (8 files) | mechanical `ruff --fix`: deleting `src/asana_mcp` flips `asana_mcp` first-party→third-party classification | e.g. `mcp/tests/test_seam_conformance.py` (−1 line) — pre-cures main's own post-merge lint state |

## 3. Verification (all BEFORE push; satellite venv ruff 0.15.4 == CI pin)

- `ruff format . --check` → **1331 files already formatted** (the "14 files would
  be reformatted" REBASE-F3 failure dissolved)
- `ruff check .` → All checks passed
- `ruff check --select BLE001,E722 .` (convention gate) → All checks passed
- `ruff check src/ --extend-select RUF100` (drift-guard sim) → All checks passed
- mcp suite: `PYTHONPATH=mcp … pytest mcp/tests -q` → **98 passed** in 1.66s
  (92 assembly + 6 MCP-1 passthrough)
- satellite unit spot-set (`tests/unit/services` + `tests/unit/api`,
  `PYTHONPATH=<wt>/src`) → **2207 passed, 1 deselected**. The deselected case
  (`test_query_service.py::TestEntityServiceValidateAdversarial::test_project_gid_none_raises_service_not_configured`)
  fails byte-identically on a PRISTINE origin/main control worktree with the
  same venv → pre-existing local-env divergence, NOT this delta (CI shards
  green both on main and on `8cac6b9d`).

## 4. CI receipts (post-push, head `8cac6b9d`)

`gh pr checks 242 --watch` exit 0 — ALL GREEN, no overrides, no dismissals:

- ci pipeline: https://github.com/autom8y/autom8y-asana/actions/runs/29741492158
  (Lint & Type Check PASS 46s; Test shards 1-4 PASS; Aggregate Coverage PASS;
  Fleet Conformance, OpenAPI Drift, Spectral, Semantic Score, Fuzz, RUF100 PASS)
- CodeQL: https://github.com/autom8y/autom8y-asana/actions/runs/29741488827
  (Analyze actions/js-ts/python PASS; CodeQL check PASS — the regex fence
  scanner reconciliation held; both known pre-cure failures dissolved)
- gitleaks + dependency-review PASS.
- PR state: OPEN, isDraft **false** (un-drafted this session), mergeable
  MERGEABLE, mergeStateStatus CLEAN.

## 5. Validation scope (for signal-sifter, PT-02)

1. Verify checks actually GREEN on head `8cac6b9d` (re-run `gh pr checks 242`,
   don't trust this file).
2. Verify assembly-only: `git diff origin/main..8cac6b9d` contains no WS-B2/tag
   surface, no satellite `src/autom8_asana` mutation, no write-flag persistence
   (`git grep ASANA_MCP_ENABLE_WRITE_SURFACE` — env-read sites only).
3. Verify the unification is loss-free: `git diff b33cc1d9..8cac6b9d -- mcp/`
   divergences confined to the §2 reconciliation classes.

## 6. Operator ask

**#242 is GREEN, un-drafted, and collapsed to the assembly-only delta — ready
for YOUR merge. The merge is operator-reserved (charter §5:96-98); this session
stopped at un-draft.** Post-merge: sprint-4 (WS-B2) unblocks per the shape's
hard edge; the s1/s6 worktree reaps trail per WS-E.

Ledger-worthy residuals (no action needed for merge):
- The pre-existing local-env unit failure (§3) — candidate for the WS-E/local
  hygiene sweep (stale main-checkout venv vs main-tip test expectations).
- The I001 first-party-classification flip (§2) is a latent lint landmine this
  PR pre-cures; any future deletion of a `src/`-rooted package dir will re-fire
  the same class.
- Worktree `wt.hygiene.asana-mcp-wsc.20260720T140021.3125cb` holds the branch;
  reap after merge (WS-E). Legacy `autom8y-asana-wt-mcp-s6` still hosts the mcp
  venv used by the suite command; dispose at WS-E per the frame.

Discharges REBASE §d POST-FELT item 1 (WS-C ledger criterion — supports the
predicate; NOT a predicate limb; no wave-level CLOSED token).
