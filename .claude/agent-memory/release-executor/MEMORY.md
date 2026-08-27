# Release-Executor Memory

## Memory Index

- [Verification-report routing claims need re-verification](verification_report_routing_claims.md) — a downstream report's mechanism-finding prose can mislabel routing (composite vs inline) even when its bottom-line conclusion is right; re-derive from the merged file. Also: `gh api .../contents/action.yml?ref={sha}` technique for pinned-action input-schema verification.
- §-letter subsection notation ("C-3") in a dispatch can mean §3(c), not condition C-3 — grep the unique term to disambiguate (see "§-letter subsection notation" section below).
- md5-on-extracted-fence-block, merge-method parent-count check, `just -f/-d`, and CodeArtifact non-UTC timestamps — see the dedicated sections below (K-ASR/REL-3, offers-freshness-axis-contract, 2026-08-11).

## Key Patterns

- `.sos/wip/` files require YAML frontmatter at the top. The `type:` value is NOT
  fixed at `audit` fleet-wide — sibling artifacts in the SAME initiative set the
  precedent: match whatever `type:` the upstream artifacts in `.sos/wip/release/`
  for the current initiative use (e.g. `platform-state-map.yaml` / `release-plan.yaml`
  used `type: scratch` for aws-hygiene-push-2026-08 — execution-ledger-*.yaml/.md
  followed suit for consistency). Check a sibling file first rather than assuming.

## Artifact Locations

- All release artifacts written to `.sos/wip/release/`
- Inputs: `platform-state-map.yaml` (PATCH), `release-plan.yaml` + `dependency-graph.yaml` (RELEASE/PLATFORM)
- Outputs: `execution-ledger.yaml` + `execution-ledger.md` (or `execution-ledger-{branch}.yaml/.md`
  when the charge scopes execution to a named sub-branch of a larger multi-branch plan)

## Container Distribution + push_only

- `distribution_type: container` with `action: push_only` does NOT trigger the container escalation rule.
  The escalation rule only applies to `publish` actions. Push-only just pushes commits; CI handles the container build.

## Dependabot Advisories on Push

- GitHub may report pre-existing Dependabot vulnerabilities in push output. These are informational,
  not push failures. Log them in `output_summary` with a note that they are pre-existing.

## a8/a8 git-conventions PreToolUse hook — commit message footgun

- Commits in `a8/a8` (and any repo/worktree checked out under it, e.g. `repos/*`)
  pass through a PreToolUse hook (`ari hook git-conventions`) that rejects
  `git commit -m "..."` with a multi-line body: "Commit message does not follow
  conventional format." It appears to choke on the body blob in the `-m` path,
  even when the subject line itself is a valid `type(scope): subject`.
- **Fix**: write the full message (subject + blank line + body) to a file and
  use `git commit -F <file>`. This passes multi-line bodies reliably (verified
  this session on both autom8y-data and autom8y-asana worktrees, 6 commits, all
  first-try green via `-F`). Keep the subject line single-line, lowercase after
  the colon, conventional format, matching the `conventions` skill's plain rules.
- Per the platform `conventions` skill (`repos/.claude/skills/conventions`), git
  commit messages get NO AI attribution/Co-Authored-By — that's reserved for
  `gh pr create` bodies only. Don't add trailers to `-F` message files.

## Trust-but-verify the state-map's call-site enumeration

- `platform-state-map.yaml`'s per-repo evidence blocks (e.g. `rel005_evidence`)
  can UNDER-count call sites for a mechanical sweep task (found cache-suffix
  targets). On REL-005/aws-hygiene-push-2026-08, the state map listed 6
  `astral-sh/setup-uv` call sites for autom8y-asana; an independent
  `grep -rln "astral-sh/setup-uv" .github/` sweep found 8 (2 workflows —
  `aegis-synthetic-coverage.yml`, `post-merge-coverage.yml` — were missing
  from the state map entirely, and had zero cache config, not even a `with:`
  block). Always re-run the exhaustive grep yourself against the live worktree
  before treating a plan/state-map's enumerated list as complete, especially
  when the plan text itself says "release-executor reading each job's identity"
  is the finalization step (a signal the count is provisional, not authoritative).

## Worktree path WARN is non-blocking when the plan specifies the exact path

- If a release-plan.yaml step gives an explicit `git worktree add ... /path/to/repo-wt-slug`
  command outside the blessed `.knossos/worktrees` root, the worktree guard emits
  a WARN (not a hard block). Proceed per the plan's explicit instruction — this is
  a plan-author decision, not a deviation, and matches the "conventional -wt- ...
  naming per the worktree guard" allowance mentioned in dispatch instructions.

## §-letter subsection notation in dispatch instructions can mean "§3(c)", not "condition C-3"

- A dispatch instruction referencing "the CERT's C-3 ... section" was ambiguous
  against a CERT artifact that had BOTH a numbered `§5 Conditions` list (C-1..C-7)
  AND lettered subsections inside `§3 PREMISE RE-LITIGATION` ((a)/(b)/(c)/(d)/(e)).
  On REL-3/K-ASR (offers-freshness-axis-contract, 2026-08-11), "read the CERT's
  C-3 and refinement-7 sections" only made sense as "§3(c)" — that's literally
  where the "refinement #7" text lived (Lane-B admission ground / FIX-N-B
  context), whereas numbered "condition C-3" was a one-line pointer about the
  K-ASR signature staying open until the PR link exists — no refinement-#7
  content there at all. Resolution: grep the artifact for the unique term
  ("refinement #7") first; let where it actually lives disambiguate the
  notation, rather than assuming "C-3" always means the numbered list. Content
  that belongs to a DIFFERENT PR/repo (here: asana #338, FIX-N-B) can still be
  worth citing as wave-context in your own PR body — but label it explicitly
  as context-not-implemented so the PR body doesn't misattribute guards your
  diff doesn't actually carry.

## Byte-fidelity fence re-check: md5 on the extracted block is a fast complement to a documented diff-command

- When a frozen-contract artifact's own `§B` fence-check section documents a
  `diff <(sed -n 'N,Mp' source) <(awk '/BEGIN.../{f=1;next}/END.../{f=0}f' target)`
  command (not an md5 command) but the dispatch asks for "md5 must remain
  {hash}", just pipe the same `awk` extraction into `md5` (macOS) — no need to
  invent a different extraction. Run it BEFORE and AFTER your edit; an
  unchanged hash plus `diff ... ; echo exit=$?` → `exit=0` is a stronger
  double-receipt than either check alone. Confirmed safe pattern: editing a
  `§F SIGNATURES` section (well outside the `§C` verbatim-core fence, which
  ends where `§D` begins) leaves the fence md5 untouched — sections outside
  the BEGIN/END markers are always safe to edit without touching fence
  integrity, but re-run the check anyway rather than assuming from line
  numbers alone.

## Matching merge method (merge-commit vs squash) to precedent: check parent count, not just PR title text

- To decide whether `gh pr merge --merge` vs `--squash` matches an existing
  precedent PR, don't just read the precedent's title in `git log --oneline`
  ("Merge pull request #N from ..." strongly suggests merge-commit, but
  confirm). Run `git log --pretty="%H %P" -1 {merge_sha}` — 2 parent SHAs
  confirms a real merge commit (not a squash, which has exactly 1 parent
  identical in tree-shape to a single new commit on top of base). Also check
  `gh api repos/{owner}/{repo} --jq '{allow_merge_commit,allow_squash_merge,allow_rebase_merge}'`
  to confirm the target method is actually enabled repo-side before choosing it.

## `just -f <justfile> -d <workdir> <target>` avoids cwd-reliance when running tests in a worktree

- `just` (>=1.43) supports `-f/--justfile` + `-d/--working-directory` (the
  latter requires the former to also be set) to run a recipe against an
  explicit path without `cd`-ing into the worktree first. This is the
  cwd-independent equivalent of `git -C` for test-suite execution — use it
  when a dispatch explicitly warns against relying on cwd (worktree miscut
  scars). Verified working on autom8y's account-status-recon service
  (`just -f {wt}/services/account-status-recon/Justfile -d {wt}/services/account-status-recon test`)
  despite that Justfile importing several relative-path modules
  (`import "../../just/_globals.just"` etc.) — `just`'s working-directory flag
  resolves those relative imports correctly against `-d`, not the shell's cwd.

## CodeArtifact `describe-package-version` returns local-zone time, not UTC — always convert before ledgering

- `aws codeartifact describe-package-version ... --query 'packageVersion.publishedTime'`
  returned `2026-08-11T18:46:41.720000+02:00` (CEST) on this session's host,
  NOT a `Z`-suffixed UTC string. Converting by hand (`18:46:41+02:00` →
  `16:46:41Z`) before writing it into a ledger is mandatory — this is the same
  class of bug the platform's existing CEST-mislabeled-as-Z scar warns about,
  just triggered by an AWS CLI response instead of a local `date` call. Always
  check the raw string's UTC offset suffix before trusting it as `Z`.

## Splitting one logical change into multiple plan-specified commits

- When a release-plan lists >1 commit message for what reads as one contiguous
  code edit (e.g. "add cache-suffix input" + "set prune-cache:false" touching
  adjacent lines in the same `with:` blocks), build it as ordered snapshots:
  write final state once, snapshot it, then progressively strip the
  not-yet-committed layers back out (write phaseN, commit, restore phaseN+1,
  commit, ...) rather than trying to hand-split file-by-file. Cheap in Python via
  string/line removal on a saved final-content dict; keeps each commit's diff
  exactly matching its message without manual patch surgery.
