---
type: review
status: accepted
verdict: PASS-WITH-FLAGS — the gate's honest claim survives adversarial teeth; R-CC7-1 confirmed real-but-benign; two disclosed non-defect caveats
rung: QA-ADVERSARIAL-FALSIFICATION-COMPLETE (own-construction teeth, rite-disjoint from principal-engineer; MODERATE self-cap)
artifact_id: CRITIQUE-cc7-gitleaks-gate-2026-08-14
wave: chain-of-custody-closure
phase: Phase 2, session coc-phase-2
sprint: CC-7 (PHASE-3 falsification)
date: 2026-08-14
author: qa-adversary (10x-dev, borrowed) — rite-disjoint second reader
second_reads: BUILD-cc7-gitleaks-biting-gate-2026-08-14
self_assessment_cap: MODERATE (single QA seat; own-hands receipts un-corroborated by a third reader; rite-disjoint from the builder but not multi-seat)
under_test:
  branch: coc-cc7-gitleaks-gate
  commit: a922d8f9e6e712b4b18192b8b288712f888699a2
  worktree: .knossos/worktrees/wt.10x-dev.coc-phase-2.20260814T090131.cc7b
  files: [.github/workflows/gitleaks-enforcing.yml, .gitleaksignore]
cr5_compliance: no credential value read, printed, reconstructed, or committed; all fixtures synthetic and assembled from parts at runtime in a disposable clone only; --redact on every scan; reports written to out-of-repo scratch and deleted; clone + object store deleted; post-cleanup PAT-shape grep across scratch + both committed files returned ZERO
g_theater_check: PASS — every RED was a deliberately-broken INPUT the gate correctly rejected; NO defect was injected into the workflow code itself (the workflow files under test were never modified)
---

# CRITIQUE — CC-7 gitleaks biting gate — PHASE-3 independent falsification

## 2026-08-14 — QA adversary, rite-disjoint teeth

I shaped none of this build. I installed the pinned engine independently, built my
OWN discriminating fixtures from scratch (I did not replay the builder's R3 legs),
and ran every attack in a disposable `--no-local` clone of `a922d8f9` with the
origin removed. The committed worktree branch was never mutated. The gitleaks
binary was verified against the officially-published checksum before first use.

### Setup receipt (own-hands)

- Arch `arm64`. Downloaded `gitleaks_8.24.3_darwin_arm64.tar.gz`; the builder's
  pinned darwin sha `b90f13bb…909013` matched the official published checksum AND
  the downloaded asset (`shasum -a 256 -c -` → `OK`, exit 0). `gitleaks version` →
  `8.24.3`, exit 0.
- The CI-axis pin `9991e0b2…4ee29c` (`GITLEAKS_SHA256` in the workflow) matches the
  official published `gitleaks_8.24.3_linux_x64.tar.gz` checksum I fetched from the
  gitleaks release. **Dual-pin (version + sha256) is real and correct on both axes;
  no platform mismatch — not a finding.**
- Clone verified complete: `git rev-list --count HEAD` = **1591**, identical to the
  source worktree's HEAD count. My teeth ran on the full inherited history, not a
  truncated subset.

### Per-attack verdict

| # | Attack | Verdict | Decisive receipt (command → exit) |
|---|--------|---------|-----------------------------------|
| 1 | Independent teeth (own construction, two-sided) | **PASS** | uncommitted planted `1/…:hex`+`2/…/…:hex` → enforcing cmd exit **0** (untracked not scanned); committed → exit **1**, exactly 2 findings both `asana-native-pat` at my new commit, ZERO historical re-trips; defect removed → exit **1** on nothing-of-mine; benign new commit → exit **0** |
| 2 | Over-suppression probe (load-bearing) | **PASS** | new `asana-native-pat` at a FRESH path → exit **1**; new `asana-native-pat` appended to an EXISTING baselined file (`src/autom8_asana/client.py`, new line 1120) → exit **1**. Baseline suppresses the exact `commit:file:rule:line` tuple ONLY, never the file or the rule |
| 3 | R-CC7-1 / false-green hunt | **NARROWING — real exposure, benign in the security-critical class; already disclosed** | working-tree-only scan (`--no-git`, no baseline) at HEAD → exit **1**, **31** secret-shaped strings LIVE in the HEAD tree, all masked by the enforcing gate. BUT **0** are `asana-native-pat` (the real-PAT / cred-t21 class) → Phase-1 "cred-t21 fossils absent at HEAD" **CONFIRMED**. The 31 are `generic-api-key`/`asana-client-id`/1×`jwt`, overwhelmingly test fixtures |
| 4 | Bypass probes (masking / redaction / skip surface) | **PASS** (with one disclosed non-defect caveat) | enforcing workflow has zero `needs:`/dependency on the delegated `\|\| true` job (separate file, separate concurrency group, distinct check-run) → delegated-green cannot mask enforcing-red. `--redact` on a real trip → report `Secret`/`Match` = `REDACTED`, ZERO value fragments in log or JSON. YAML re-parse: no `if:`, no `continue-on-error` (job or any of 4 steps), no `strategy/matrix`, no `\|\| true`, `--exit-code 1` present |
| 5 | Pin integrity (fail-closed) | **PASS** | faithful workflow construct (`set -euo pipefail`; single `sha256sum -c -`, no `\|\|`) with a tampered expected hash → `FAILED` / exit **1**, extract step NEVER reached; correct hash → `OK` / exit 0 |

### Attack 1 — independent teeth (PASS)

My fixture is not the builder's. I assembled a `1/{6+digit gid}:{32-hex}` and a
`2/{gid}/{sub}:{32-hex}` from runtime parts in a scratch-only file. Four legs, all
carrying the baseline, the only variable the defect:

- staged UNCOMMITTED → exit **0** (`gitleaks detect` walks committed history; an
  untracked file is not scanned — a subtle property worth stating: the gate bites
  on *commit*, not on working-tree presence);
- committed → exit **1**, `leaks found: 2`, both `asana-native-pat`, both at my new
  commit, both in the new file, **zero historical re-trips**;
- defect commit removed (detached back to `a922d8f9`) → the gate is quiet on my
  content;
- benign new commit on top → exit **0**, `no leaks found`.

Two-sided and discriminating by my own hand: the gate bites ONLY on the defect.

### Attack 2 — over-suppression (PASS, two forms)

The load-bearing question: does the baseline suppress a NEW instance of an
already-baselined RULE at a NEW location? No. `asana-native-pat` is baselined (5
fingerprints in `.claude/settings.local.json`), yet a fresh instance at a brand-new
path tripped (exit 1), and a fresh instance appended to an existing baselined file
at a new line tripped (exit 1). Fingerprints are `commit:file:rule:line`; a new
location is a new fingerprint, never covered. **The baseline is narrow by
construction — confirmed adversarially.**

### Attack 3 — R-CC7-1 false-green hunt (the result)

**R-CC7-1 is a REAL exposure, not hypothetical — and it is BENIGN in the one class
that would be alarming, and the builder already filed it honestly as a named
residual.**

- A working-tree-only scan at HEAD (`--no-git`, baseline removed) reports **31**
  secret-shaped strings that are LIVE in the current tree of files that still exist
  at HEAD. Because the enforcing gate (full-history + baseline) is green, these 31
  are permanently masked going forward. That is a genuine false-green surface: the
  gate will read green while 31 secret-shaped strings sit in the tree.
- **BUT the discriminator that matters:** **0 of the 31 are `asana-native-pat`** —
  the real Asana-PAT rule, the cred-t21 locus this whole wave was seeded by. Both
  `.claude/settings.local.json` and the session `events.jsonl` (the PAT-bearing
  files) are **ABSENT at HEAD**. **Phase-1's "cred-t21 fossils are absent at HEAD"
  claim is verified, not assumed.**
- The 31 are `generic-api-key` (gitleaks' notoriously high-false-positive
  heuristic), `asana-client-id` (a semi-public OAuth client identifier — the client
  *secret* is the sensitive half), and one `jwt` — sitting in `tests/**`, one
  `.ledge/reviews/…md`, and `src/autom8_asana/client.py`. These are near-certainly
  test fixtures / example values, but **UNADJUDICATED by value under CR-5**.
- This is EXACTLY the builder's `R-CC7-1` residual ("suppressed, not triaged …
  whether any is a live exposure is unadjudicated"). My probe **confirms and
  quantifies** it (31 live-at-HEAD masked; 0 in the PAT class) rather than refuting
  it. Disposition: **real-but-benign; warrants the follow-on triage pass the builder
  already scoped out of CC-7.** Not a FALL of the gate — the gate does exactly what
  a suppress-not-triage baseline is documented to do, and the dangerous class is
  clean.

### Attack 4 — bypass probes (PASS + one honest caveat)

- **Masking:** the enforcing workflow is a physically separate file with its own
  concurrency group and NO `needs:`/`workflow_call`/reference to the delegated job
  (every mention of `gitleaks.yml`/`Secrets Scan` in it is an explanatory comment).
  GitHub reports the two as independent check-runs; the always-green delegated
  `gitleaks / Secrets Scan` cannot mask a red `Secrets Scan (enforcing)`.
- **Redaction:** on a real trip the JSON report's `Secret` and `Match` are
  `REDACTED` and a grep of both the log and the report for my synthetic hex
  fragments returned zero. `--redact` holds.
- **Skip surface:** YAML re-parse found no `if:`, no `continue-on-error`, no matrix,
  no `|| true`.
- **DISCLOSED CAVEAT (not a defect):** the check-run context `Secrets Scan
  (enforcing)` is NOT in branch protection's required contexts, so a RED run does
  not *block* a merge until ACTION 2 (registration) runs. "Reports independently"
  ≠ "blocks merge." The build note's §0/§7 state this precisely; it is the honest
  rung-STAGED gap, not a bypass I found.

### Attack 5 — pin integrity (PASS)

A tampered expected hash under the exact workflow construct (`set -euo pipefail`,
single `sha256sum -c -`, no `|| true`) exits 1 and the extract/`tar` step is never
reached — fail-closed. The correct hash passes. Supply-chain pin is enforced, not
decorative.

### My own method self-corrections (disclosed for auditability)

1. **5-digit-gid miss:** my first over-suppression fixture used a 5-digit gid; the
   rule requires `[0-9]{6,}` so it (correctly) did not fire. I re-ran with a
   6-digit gid → trip. This independently **corroborates the builder's CF-4
   one-sided residual**: the rule fires LESS than reality on out-of-shape tokens,
   never more.
2. **Auto-loaded baseline:** my first "no-baseline" history run still exited 0
   because gitleaks **auto-loads `.gitleaksignore` from the source root even without
   `--gitleaks-ignore-path`**. I re-ran the true no-baseline leg by REMOVING the
   file → exit **1**, 46 findings. This independently **reproduces the builder's
   R-CC7-2 observation**; the decisive leg must remove the file, not drop the flag.

### NARROWING — finding count 46 (mine) vs 49 (builder R1b)

On the identical 1591-commit history, my true no-baseline history scan found **46**
findings, all covered by the baseline (**0 uncovered → gate green on inherited
history**), leaving **3** baseline entries unmatched. Those 3 are the first member
of 3 duplicate `file:rule:line` pairs that differ only in commit SHA (in
`.ledge/reviews/DEFECT-…md:80`, `tests/integration/test_gfr_tenant_roundtrip.py:404`,
`tests/unit/api/routes/test_projects_sections_hardened.py:57`). The 46/49 gap is
environment-sensitive (git rename/diff presentation for those 3 dup-commit pairs).
**Direction of imprecision is SAFE:** the baseline is a *superset* of current-history
findings, so it cannot blind the gate to a genuinely new secret (proved in Attacks
1 and 2). The builder's 49 is a conservative superset; my 46 is the live subset.
Not a FALL.

### G-THEATER confirmation

Every RED I produced was a deliberately-broken INPUT the live gate correctly
rejected (planted synthetic secrets in a disposable clone), paired with a GREEN
no-defect variant. **I injected NO defect into the workflow code itself — the two
committed files under test were read, parsed, and executed, never modified.**
Consistent with `discriminating-canary-doctrine` mode 1 (test-only canary on a
working surface).

### CR-5 hygiene check (post-run)

Final sweep after deleting the clone (working tree AND `.git` object store) and all
reports/logs: `grep -rE '[12]/[0-9]{6,}(/[0-9]{6,})?:[0-9a-f]{32,}'` across the
entire scratch tree **and** both committed files under test → **zero matches**
(exit 1). Synthetic-fragment grep → zero. Only the verified binary and the public
`checksums.txt` remain in scratch. No credential value was ever read or written.

### Overall verdict

**The "authored + two-sided-proven, bites only after land + registration" claim
SURVIVES my teeth.** The gate is engine-sound (dual-pinned, fail-closed on hash
mismatch), the baseline is narrow (over-suppression refuted in two forms), the teeth
are genuinely two-sided by my own construction, redaction holds, and there is no
skip/masking surface in the YAML. The non-biting-until-registered property is a
disclosed design honesty, not a defect. **R-CC7-1 is a REAL false-green surface (31
live-at-HEAD masked strings) but BENIGN in the security-critical dimension (0 live
native PATs; cred-t21 confirmed absent at HEAD) and already filed as a scoped
residual.** No G-THEATER. Recommendation: **GO for the land + registration ordering
as authored; open the R-CC7-1 triage follow-on before treating the suppressed
history as certified-clean.**
