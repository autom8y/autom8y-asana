---
type: review
status: draft
artifact_id: RECON-gitleaks-enforcement-locus-2026-08-13
date: 2026-08-13
author: pipeline-cartographer (eunomia)
sprint: CC-6 (chain-of-custody-closure wave — perimeter recon)
self_assessment_cap: MODERATE
downstream: CC-7 (hard edge E1 — CC-7 depends on this artifact)
second_reader: threat-modeler (security rite) — rite-disjoint NR-5 second-read
---

# RECON — Gitleaks Enforcement Locus (external gate, own-eyes read)

## §0 Scope discipline

This is a PAPER sprint: recon + design input only. No git verbs, no writes
outside this file, no rotation, no upstream edit, no merge. Self-assessment
capped MODERATE per F-C. Terminal this wave per F-A (Q-4 HALT) — this artifact
rests authored-unmerged.

CR-5 compliance: the cred-t21 leak was consulted PATH+FACT ONLY from
`.know/defer-watch.yaml:382-392` (severity, commit SHAs, absent-at-HEAD
status). No credential material was read. No GitHub code-scanning-alert
detail endpoint was queried (a plausible next probe was deliberately skipped
because alert detail payloads can carry match snippets — out of envelope,
noted as an operator-only follow-on in §6).

---

## §1 UV-P-CoC-1 — CLOSED (external gate read own-eyes)

**Disposition: CLOSED.** The reusable workflow at the pinned SHA is fetchable
and was fetched. It is NOT unreadable; the prior "bypass lives in a repo I
cannot read" framing does not hold.

**Receipt (api-probe):**

```yaml
structural_verification_receipt:
  claim: "the security-gitleaks.yml reusable workflow at commit f5601acbe3905270dfcb9069854c78c0f940ad05 in autom8y/autom8y-workflows is fetchable via gh api and its 'Run gitleaks' step is suffixed with a shell '|| true'"
  verification_method: api-probe
  verification_anchor:
    source: "https://api.github.com/repos/autom8y/autom8y-workflows/contents/.github/workflows/security-gitleaks.yml?ref=f5601acbe3905270dfcb9069854c78c0f940ad05"
    request_method: GET
    request_payload: "(none — GET with ref query param)"
    response_snippet_verbatim: "gitleaks detect --source . --report-format sarif --report-path gitleaks-results.sarif --verbose || true"
    status_code: 200
    claim: "the decoded base64 content field of the 200 response contains the literal shell-swallowed run step, confirming the exit-code-discarding bypass lives in the pinned upstream commit, not in an unreadable location"
```

Command actually run (own-hands):

```
gh api "repos/autom8y/autom8y-workflows/contents/.github/workflows/security-gitleaks.yml?ref=f5601acbe3905270dfcb9069854c78c0f940ad05"
```
Exit code: `0`. HTTP status: `200`. Content decoded via `--jq '.content' | base64 -d`, exit code `0`.

**Full decoded workflow body** (verbatim, `.github/workflows/security-gitleaks.yml` @ `f5601acb…`):

```yaml
name: "Security: Gitleaks Secrets Scan"

on:
  workflow_call:

jobs:
  gitleaks:
    name: Secrets Scan
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd # v5.0.1 (node24)
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Install gitleaks
        run: |
          GITLEAKS_VERSION=8.24.3
          curl -sSfL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
            | tar xz -C /usr/local/bin gitleaks

      - name: Run gitleaks
        run: gitleaks detect --source . --report-format sarif --report-path gitleaks-results.sarif --verbose || true

      - name: Upload SARIF
        if: always() && github.event.repository.visibility == 'public'
        continue-on-error: true
        uses: github/codeql-action/upload-sarif@8aad20d150bbac5944a9f9d289da16a4b0d87c1e # v4.36.2 (node24)
        with:
          sarif_file: gitleaks-results.sarif
          category: gitleaks
```

**Version-skew check (pin vs. HEAD)**: fetched the same path with no `ref=` (default-branch HEAD) — content is byte-identical to the pinned-SHA content. No drift; the pin is current. Receipt:

```
gh api "repos/autom8y/autom8y-workflows/contents/.github/workflows/security-gitleaks.yml" --jq '.content' | base64 -d
```
Exit code `0`; output matches the block above verbatim (confirmed by direct comparison of both decoded bodies during this recon).

**What the gate actually does, structurally:**
1. Checks out the CALLING repo (no `repository:` override on the checkout step — `actions/checkout` defaults to `github.repository`, which in a `workflow_call` context is the caller's repo, i.e. `autom8y/autom8y-asana`) with `fetch-depth: 0` — **full git history**, not shallow.
2. Installs gitleaks 8.24.3 from the upstream release tarball.
3. Runs `gitleaks detect --source . ... || true` — **the shell `|| true` unconditionally forces exit code 0**, regardless of what `gitleaks detect`'s own exit code was (gitleaks exits 1 on any leak found, per its own `--exit-code` default documented behavior). This is the asserted bypass, confirmed own-eyes.
4. Uploads the SARIF report to GitHub code scanning — but ONLY if `github.event.repository.visibility == 'public'`, and this step itself is `continue-on-error: true`.

**Ancillary finding — the SARIF upload is NOT dead code for this repo.** `autom8y-asana` is a PUBLIC repo (verified: `gh api repos/autom8y/autom8y-asana --jq '{private,visibility}'` → `{"private":false,"visibility":"public"}`, exit 0). This means the "Upload SARIF" step's condition IS satisfied on every run — gitleaks findings for this repo ARE currently uploaded to GitHub's Security → Code scanning alerts, even though the job itself always reports green. The bypass is **merge-blocking-only**, not **visibility-only** — findings are not fully silent, they just don't gate. Whether any code-scanning alert currently exists for the cred-t21 leak was NOT probed (CR-5 boundary discipline — see §0); this is flagged as an operator-only follow-on in §6, not asserted as fact.

---

## §2 UV-P-CoC-4 — ANSWERED: YES, an enforcing run would trip on cred-t21

This is the load-bearing determination gating whether F-7 fires at all.

**Answer: YES — with high confidence, structurally derived (not empirically run).** Four independent factors compound toward a trip, and none of the factors that would suppress it are present:

1. **Scan depth = full history.** `fetch-depth: 0` on checkout means the full commit graph is present in the runner's working copy, not a shallow/single-commit checkout.

2. **`gitleaks detect` scans full git log by default, not a diff.** Verified against the upstream gitleaks README at the pinned tool version:
   ```yaml
   structural_verification_receipt:
     claim: "gitleaks 'detect' (git-scanning mode) uses 'git log -p' under the hood and scans the full accessible history unless --log-opts restricts the range; the reusable workflow passes no --log-opts"
     verification_method: docs-cite-verbatim
     verification_anchor:
       source: "https://api.github.com/repos/gitleaks/gitleaks/contents/README.md?ref=v8.24.3"
       line_range: "L191-L196 (rendered Usage/Commands/Git section)"
       marker_token: "gitleaks uses the `git log -p` command to scan patches"
       claim: "absent an explicit --log-opts commit-range restriction (none is passed in security-gitleaks.yml), gitleaks detect will walk the full reachable git history of the checked-out branch, which per fetch-depth:0 is the complete history — this is the mechanism by which a diff-only or PR-only scan would NOT catch cred-t21, and it is NOT the configuration in force here"
   ```
   Command: `gh api "repos/gitleaks/gitleaks/contents/README.md?ref=v8.24.3" --jq '.content' | base64 -d`. Exit code `0`, status `200`.

3. **cred-t21 is in MAIN branch history, reachable from HEAD.** Per `.know/defer-watch.yaml:388-391` (path+fact only, no credential material read): *"T21 leaked native ASANA_PAT present in autom8y-asana MAIN git history (commits a578ca85, 525431de, 15cffee1; `.claude/settings.local.json`). ABSENT + gitignored at HEAD."* Absent-at-HEAD does not matter for `gitleaks detect` in `git` mode — it walks history via `git log -p`, so a value present in an old commit's diff is found even if the current tree no longer contains it.

4. **No baseline or ignore-file suppression is configured, and the LOCAL detection RULE for this exact leak class already exists and would fire.** No `--baseline-path` flag is passed by the reusable workflow (confirmed: absent from the "Run gitleaks" step's full command line, read above). Because no `--config`/`GITLEAKS_CONFIG*` override is passed either, gitleaks falls to its 4th-precedence default: **the target path's own `.gitleaks.toml`** — verified against upstream docs:
   ```yaml
   structural_verification_receipt:
     claim: "with no -c/--config flag and no GITLEAKS_CONFIG* env var, gitleaks resolves configuration from a .gitleaks.toml file in the scanned target path before falling back to the built-in default config"
     verification_method: docs-cite-verbatim
     verification_anchor:
       source: "https://api.github.com/repos/gitleaks/gitleaks/contents/README.md?ref=v8.24.3"
       line_range: "L154-L162 (Flags block, -c/--config precedence order)"
       marker_token: "order of precedence: 1. --config/-c 2. env var GITLEAKS_CONFIG 3. env var GITLEAKS_CONFIG_TOML with the file content 4. (target path)/.gitleaks.toml"
       claim: "since the security-gitleaks.yml step passes none of the first three precedence options, gitleaks auto-discovers autom8y-asana's own .gitleaks.toml at repo root — meaning THIS repo's custom rules are already in force whenever the scan runs, enforcing or not"
   ```
   And this repo's `.gitleaks.toml` (read own-eyes, `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.gitleaks.toml`) already contains a **purpose-built rule for exactly this leak class**, with its own comment naming the gap:
   ```toml
   # GATE-GAP-1 (TDD §5): native Asana Personal Access Token formats. Without this
   # rule the S3 gitleaks teeth are unsound for native PAT leaks — the default and
   # custom rules above cover client secrets / presigned URLs but not the raw
   # `1/{gid}:{hex}` and `2/{gid}/{sub}:{hex}` native token forms the read-route
   # brokers.
   [[rules]]
   id = "asana-native-pat"
   description = "Asana native Personal Access Token (1/gid:hex, 2/gid/sub:hex)"
   regex = '''\b[12]/[0-9]{6,}(?:/[0-9]{6,})?:[0-9a-f]{32,}\b'''
   keywords = ["1/", "2/"]
   tags = ["asana", "pat", "credential"]
   ```
   (`.gitleaks.toml:44-56`, read own-eyes — no credential value copied, rule text only.) The `[allowlist].paths` block (`.gitleaks.toml:58-75`) does not exempt `.claude/settings.local.json` — the only `.claude/` allowlist entry is `'''(?i)\.claude/.*\.md$'''` (markdown-only), which does not match a `.json` path. **The suppressing conditions that would make the answer NO — diff-only scanning, a baseline file, a rule gap, or a path allowlist covering the leaked file — are all structurally absent.**

**Corollary this determination forces onto F-7 (stated because it changes the fork, not because grading it is my lane):** rotation of cred-t21 (F-2, operator-only) addresses the *live-credential-risk* half but does **not by itself** make an enforcing gate pass — gitleaks is pattern-matching git history, not validating token liveness, so a rotated-but-still-present-in-history string still matches the `asana-native-pat` regex and still trips the scan. **A baseline/ignore mechanism (`--baseline-path` or `.gitleaksignore`) covering the three known historical commits is required in addition to (or independent of) rotation before ANY enforcing flip — local or upstream — can go green without perpetually red-blocking on the known-and-presumably-accepted historical finding.** This is a correction worth carrying forward explicitly: "rotate-then-enforce" as a two-step sequence is incomplete as stated; it is really "rotate + baseline-then-enforce," and the baseline step is the one that actually unblocks CI, not the rotation.

---

## §3 Fix locus — enumerated, then priced

### (a) Change upstream in `autom8y/autom8y-workflows`
**Change**: remove `|| true` from the "Run gitleaks" step (or replace with explicit `--exit-code 1` handling and no swallow), publish a new commit, and let it be adopted.
**Price**: cheapest single point of truth — fixes the class for every consumer of `security-gitleaks.yml`, not just this repo. But: (1) blast radius is unknown from this envelope — the number and identity of other repos pinning this reusable workflow was not enumerated (out of scope; a topology/dependency-analyst concern, not mine); (2) any OTHER consuming repo with its own unaddressed historical leak would go instantly CI-red on adoption of the new pin — this is an org-wide coordination problem, not a single-repo edit; (3) requires a PR + review + merge in a repo this agent does not own and cannot write to (read-only cross-repo constraint, confirmed via `gh api` read access only — no write attempted, none permitted). **This is a cross-repo land. Per mission instruction, I checked whether this is the ONLY viable locus before considering an F-8 halt — it is NOT the only viable locus (see (c) below is fully local and viable), so F-8 is NOT triggered.** (a) remains enumerable and prices as the durable/organization-correct fix, just not the fastest or lowest-authority one.

### (b) Re-point this repo's caller to an enforcing variant
**Checked directly**: listed `autom8y/autom8y-workflows/.github/workflows/` — receipt:
```
gh api "repos/autom8y/autom8y-workflows/contents/.github/workflows" --jq '.[].name'
```
Exit 0. Contents: `gitleaks.yml`, `security-gitleaks.yml`, `security-dependency-review.yml`, `security-scorecard.yml`, `security-trufflehog.yml`, `security-zizmor.yml`. **No enforcing variant of the gitleaks workflow currently exists upstream.** (b) is therefore **not independently viable today** — it collapses into a special case of (a) (someone would first have to author the enforcing variant upstream, which is the (a) work), so it does not offer a cheaper path than (a) and should not be priced as a separate line item.

### (c) Add a local enforcing job in this repo
**Change**: in `autom8y-asana`, add a second job (or a standalone workflow) that installs gitleaks and runs it WITHOUT the `|| true` swallow, targeting the same `.gitleaks.toml` already at repo root (auto-discovered, no config change needed) — either alongside the existing delegated job or in place of it.
**Price**: fully local, zero cross-repo dependency, zero coordination with other consuming repos, immediately deployable by this repo's own PR process. **Cost**: duplicates the install-gitleaks + run-gitleaks step sequence that already lives in the upstream reusable workflow (SCAR-PC-002/SCAR-PC-004-shaped: a near-identical multi-step sequence, independently maintained, diverges from the shared component the org otherwise standardizes on) — this repo would be carrying its own fork of logic the org pattern says should be centralized. **Hard prerequisite, independent of locus choice**: per §2's corollary, this cannot simply be turned on — it needs a baseline/ignore artifact for the three known cred-t21 commits or it goes permanently red on day one, blocking every future merge to `main` (branch protection already requires `gitleaks / Secrets Scan` strictly — see §4). This is the fastest-to-ship option but the one that most directly needs the F-7 rotate/baseline sequencing resolved first.

### (d) Branch-protection / required-check registration
**Checked directly** — receipt:
```
gh api repos/autom8y/autom8y-asana/branches/main/protection
```
Exit 0. `required_status_checks.contexts` includes the literal string `"gitleaks / Secrets Scan"` (with `strict: true` and `enforce_admins: true`). **This is ALREADY correctly wired — (d) is not a gap and needs no fix.** The context name format (`{caller job id} / {called job name}`) matches the caller's job id `gitleaks` (`.github/workflows/gitleaks.yml:19` — job key `gitleaks:`) composed with the called workflow's job `name: Secrets Scan`. Because branch protection is already pointed at the right check, **fixing (a) or (c) alone is sufficient** — once the job can actually go red, the existing required-check wiring will bite without any further branch-protection edit. This is a materially important finding: the remediation surface is narrower than "gate config + branch protection both need fixing" — it is just the exit-code swallow.

### (e) No additional option identified
No fifth locus was found. A `--baseline-path`/`.gitleaksignore` addition is not a distinct LOCUS (it doesn't decide where enforcement lives) — it is a PREREQUISITE that applies identically inside (a) or (c), noted in §2's corollary and priced there, not re-priced as its own row.

**No F-8 halt fires.** (c) is a fully viable, fully local, lower-authority-envelope option; (a) is not the only viable locus, so this recon does not need to escalate a cross-repo-only finding.

---

## §4 Local-surface sweep (NR-5(b)) — no local bypass found beyond the upstream `|| true`

| Local surface checked | Command (own-hands) | Exit | Finding |
|---|---|---|---|
| `continue-on-error` on the caller job/steps | `Read(.github/workflows/gitleaks.yml)` | n/a (file read) | **Absent.** The 19-line caller file has no `continue-on-error` anywhere. It contains only `name`, `concurrency`, `on`, `permissions`, and a single `jobs.gitleaks.uses:` delegation — no step-level content to carry a bypass locally. |
| `if:` guard on the job | same read | n/a | **Absent.** No `if:` condition on the `gitleaks` job; it runs unconditionally on the two declared triggers. |
| Missing `permissions:` block (defaults to write-all) | same read | n/a | **Not a gap.** `permissions: contents: read, security-events: write` is explicitly declared at workflow level (`.github/workflows/gitleaks.yml:13-15`). |
| Missing `concurrency:` control | same read | n/a | **Not a gap.** `concurrency: group: gitleaks-${{ github.ref }}, cancel-in-progress: true` is present (`.github/workflows/gitleaks.yml:3-5`). |
| Trigger gap — merge queue not covered | `gh api graphql -f query='{repository(owner:"autom8y",name:"autom8y-asana"){mergeQueue{id}}}'` | 0 | **Not a live gap.** Result: `mergeQueue: null` — this repo has no merge queue configured, so the absence of a `merge_group:` trigger on `gitleaks.yml` is currently inert, not a bypass. (Flagged for future-proofing only: if a merge queue is enabled later, `merge_group:` would need adding — not a present-tense finding.) |
| Missing required-status-check registration | `gh api repos/autom8y/autom8y-asana/branches/main/protection` | 0 | **Not a gap — see §3(d).** `gitleaks / Secrets Scan` IS a required, strict, admin-enforced check. |
| Input passed by caller that disables enforcement | `Read(.github/workflows/gitleaks.yml)` cross-checked against the called workflow's `on: workflow_call:` block (read in §1 — no `inputs:` declared at all) | n/a | **Not applicable / absent.** The caller passes no `with:` block, and the called workflow declares zero `workflow_call.inputs`, so there is no input surface through which the caller could toggle enforcement even if it wanted to. The bypass is 100% upstream and non-configurable from the caller side. |
| Event coverage (PR + push to main) | same read | n/a | **Correct for a non-merge-queue repo.** `on: push: branches: [main]; pull_request: branches: [main]` covers both the PR-gate path (which branch protection needs) and post-merge push. No fork-PR nuance investigated further (out of scope; `pull_request` vs `pull_request_target` semantics for forked-PR secrets access is a separate GUARD-class question not raised by the mission). |

**Conclusion: the ONLY bypass found, local or external, is the single `|| true` at `security-gitleaks.yml`'s "Run gitleaks" step, upstream in `autom8y/autom8y-workflows` at the pinned SHA.** Every local surface this repo controls (permissions, concurrency, required-check registration, trigger coverage, input plumbing) is already correctly configured to make the gate biting, once the upstream job can actually report a non-zero exit.

---

## §5 NR-5 first-sweep returns (state + first-sweep; `threat-modeler` second-reads)

**Negative under test**: *"the `|| true` bypass lives in a repo I cannot read"* (UV-P-CoC-1).

| Return | Answer | Null? |
|---|---|---|
| (a) Was the pinned SHA fetchable via `gh api` — did I actually try, with a command and exit code, or carry the UV-P by momentum? | **Tried and succeeded.** `gh api "repos/autom8y/autom8y-workflows/contents/.github/workflows/security-gitleaks.yml?ref=f5601acbe3905270dfcb9069854c78c0f940ad05"` → exit `0`, HTTP `200`, content decoded and quoted in full at §1. The UV-P is **CLOSED**, not carried. | No — non-null, resolved. |
| (b) Is there a LOCAL bypass too (continue-on-error, if: guard, trigger gap, missing required-status-check registration)? | **No.** Full sweep at §4: none of continue-on-error / if-guard / trigger-gap / missing-required-check is present locally. The sole bypass is upstream. | No — checked, negative result, not a null. |
| (c) Does the caller pass an INPUT that disables enforcement? | **No — and cannot.** The called workflow declares zero `workflow_call.inputs`; the caller passes no `with:` block. No input surface exists either way. | No — checked, negative result. |
| (d) Is the job triggered on the events that matter (PR, merge queue)? | **PR: yes** (`pull_request: branches: [main]`). **Merge queue: not applicable** — this repo has no merge queue configured (`mergeQueue: null` via GraphQL probe), so there is nothing for a `merge_group:` trigger to cover today. Flagged as a future-proofing note only, not a present-tense gap. | No — resolved with a scoped caveat, not a genuine null. |

**No nulls in this sweep** — all four NR-5 questions resolved to a checked, receipted answer (own-hands command + exit code for each). Reported honestly rather than defaulted-to-clean: each row above carries its own command/receipt, not an unverified "assume fine."

---

## §6 Out-of-envelope follow-ons (not performed, noted for the operator/downstream — not asserted as fact)

- Whether a GitHub code-scanning alert already exists for the cred-t21 pattern (the SARIF upload runs on every scan for this public repo per §1) was **not queried** — CR-5 boundary discipline; the alert-detail endpoint can surface match content. If pursued, use `gh api repos/autom8y/autom8y-asana/code-scanning/alerts` with tool filter and read only alert STATE/COUNT metadata, never `most_recent_instance` detail, to stay inside CR-5.
- The blast radius of option (a) — how many other repos pin `security-gitleaks.yml` and whether any of them have their own unaddressed historical leaks — was not enumerated; this sits with topology-cartographer/dependency-analyst territory, not pipeline-cartographer's.
- F-2 (rotation) remains strictly operator-only per the fence; nothing above performs or schedules it. The §2 corollary is offered so the operator does not assume rotation alone unblocks an enforcing gate.

---

## §7 Handoff summary (for CC-7 / entropy-assessor consumption)

- UV-P-CoC-1: **CLOSED** — external gate read own-eyes, full body quoted at §1.
- UV-P-CoC-4: **ANSWERED YES** — an enforcing run would trip on cred-t21 (full-history scan + no baseline + local rule already covers the exact leak class + no allowlist exemption). Rotation alone does not discharge this; a baseline/ignore artifact is also required.
- Fix locus: **(c) local enforcing job is the only currently-independently-viable option**; (a) upstream fix is the durable org-correct fix but not solo-viable from this envelope (no F-8 halt — (c) exists); (b) is not independently available (no enforcing variant exists upstream today); (d) is already correctly configured, not a gap.
- Local bypass: **none found beyond the single upstream `|| true`.** Every local control surface (permissions, concurrency, required-check registration, input plumbing, trigger coverage) is already sound.
- NR-5: **zero nulls**, all four returns receipted.
