---
type: review
status: draft
artifact_id: CRITIQUE-cc6-gitleaks-recon-2026-08-13
date: 2026-08-13
author: threat-modeler (security rite) — rite-disjoint NCSR second reader
second_reads: RECON-gitleaks-enforcement-locus-2026-08-13 (pipeline-cartographer, eunomia)
sprint: CC-6 (chain-of-custody-closure wave)
self_assessment_cap: MODERATE (own-hands re-derivation is external corroboration, not self-assessment)
downstream: CC-7 (hard edge E1) — F-7 input
cr5_compliance: path+fact only; cred-t21 value never read/reconstructed; regex tested against SYNTHETIC shapes only
git_discipline: author FILES ONLY — this artifact rests authored-unmerged (Q-4 HALT); main thread owns git
---

# CRITIQUE — CC-6 Gitleaks Recon (NR-5 NCSR receipt, second-read own-hands)

## §0 Charge and method

Adversarial second-read of RECON-gitleaks-enforcement-locus-2026-08-13. Charge:
attack, not confirm; go one hop past where the author stopped. Every refuter of
NR-5 was re-swept OWN-HANDS (my own commands + exit codes), not inherited from
the author's receipts. Nulls reported as evidence. CR-5 held throughout: the
cred-t21 value was never read; the `asana-native-pat` regex was validated against
SYNTHETIC tokens of the documented shape only.

**NR-5 under test**: *"the `|| true` bypass lives in a repo I cannot read"* (UV-P-CoC-1).

**Headline**: NR-5 **STANDS** (refuted decisively — the bypass is readable, re-fetched
byte-identical own-hands). The UV-P-CoC-4 "enforcement-trips + rotation-insufficient"
corollary **SURVIVES** with a bounded CR-5 residual. **One added refuter (AR-1) the
author did not name inverts part of the §3(d) conclusion for the recommended fix-locus
(c): a local enforcing job is a latent NON-BITING GATE unless a branch-protection
contexts edit accompanies it.** The fix-locus slate HOLDS on (a)/(b)/(d) but NARROWS
on (c).

---

## §1 Refuter (a) — pin fetchable, byte-identical? — STANDS

Re-ran the author's exact probe own-hands (not carried by momentum):

```
gh api "repos/autom8y/autom8y-workflows/contents/.github/workflows/security-gitleaks.yml?ref=f5601acbe3905270dfcb9069854c78c0f940ad05" --jq '.content' | base64 -d
```
Exit `0`, HTTP `200`. Decoded body is **byte-identical** to the author's §1 quote,
including verbatim:

```
- name: Run gitleaks
  run: gitleaks detect --source . --report-format sarif --report-path gitleaks-results.sarif --verbose || true
```

The `|| true` exit-code swallow lives at the pinned SHA `f5601acb…`, not paraphrased,
not in an unreadable location. **Verdict: STANDS.** The negative "bypass lives in a
repo I cannot read" is decisively falsified.

Corroborated facts (own-hands, exit 0 each):
- Repo visibility: `gh api repos/autom8y/autom8y-asana --jq '{private,visibility}'` →
  `{"private":false,"visibility":"public"}`. The author's ancillary "SARIF upload is
  live for this public repo → findings uploaded but merge-blocking-only bypass" framing
  is sound.

---

## §2 Refuter (b) — local bypass beyond the upstream `|| true`? — STANDS (current config) + ADDED REFUTER AR-1 (recommended remediation)

### §2.1 Current-config sweep — STANDS

Read `.github/workflows/gitleaks.yml` own-hands (20 lines). Findings match the author:
- No `continue-on-error` anywhere.
- No `if:` guard on the `gitleaks` job.
- `permissions: contents: read / security-events: write` explicit (L13-15).
- `concurrency` present (L3-5).
- Caller passes NO `with:` block; delegates via single `jobs.gitleaks.uses:` (L18-19).

**Check-name binding — the load-bearing hop the author reasoned about compositionally,
I verified EMPIRICALLY.** The author inferred `{caller job id `gitleaks`} / {called job
name `Secrets Scan`}` = `gitleaks / Secrets Scan` and stopped. I went one hop past and
read the ACTUAL reported check-run name on main HEAD:

```
gh api "repos/autom8y/autom8y-asana/commits/main/check-runs" --jq '.check_runs[] | {name, app, conclusion}'
```
Exit 0. The live list contains, verbatim: `"gitleaks / Secrets Scan"` (app
`github-actions`, conclusion `success`). Branch protection requires exactly that string:

```
gh api repos/autom8y/autom8y-asana/branches/main/protection --jq '.required_status_checks'
```
Exit 0 → contexts include `"gitleaks / Secrets Scan"` (app_id 15368 = GitHub Actions),
`strict: true`, `enforce_admins: true`. **The reported name equals the required-context
string byte-for-byte** — the current delegated gate is NOT a silent name-mismatch gate.
The `conclusion: success` is consistent with the `|| true` always-green behavior (the
job runs and is registered — it simply cannot go red today).

**Verdict for the current config: STANDS.** No local bypass exists beyond the upstream
`|| true`; the required-check registration is sound and empirically live.

### §2.2 ADDED REFUTER AR-1 — fix-locus (c) is a latent NON-BITING GATE (this is the structure working)

The author's sweep covered the CURRENT config. It did NOT sweep the check-name binding of
the RECOMMENDED remediation (c). Here the author's own §3(d) generalization breaks.

**The mechanism.** The `A / B` composite name (`gitleaks / Secrets Scan`) arises ONLY
from reusable-workflow nesting: `{calling job name} / {called workflow's job name}`. A
plain, local (non-reusable) job produces a SIMPLE name — its `name:` or job id — with no
slash composite. This is empirically visible in the same check-runs list I pulled: every
plain job carries a simple name (`dispatch`, `Fleet Schema Governance`, `Lint noqa Drift
Guard (RUF100)`, `MCP Island Suite (...)`, `Analyze (actions)`), while ONLY
reusable-workflow-called jobs carry the `X / Y` composite (`gitleaks / Secrets Scan`,
`ci / Test (shard 1/4)`, `dependency-review / Dependency Review`). The dichotomy is
observable in production, not theoretical.

**The consequence for option (c).** Option (c) as the author defines it — "add a second
job (or a standalone workflow) that installs gitleaks and runs it WITHOUT the `|| true`
swallow" — is a plain local job. It will report under a NEW name (e.g. `Secrets Scan`,
or the new job id), NOT `gitleaks / Secrets Scan`. Two failure modes follow:

1. **(c) alongside the delegated job**: the old `gitleaks / Secrets Scan` keeps reporting
   green (`|| true` upstream, unchanged); the new enforcing job reports red under an
   UNREGISTERED name → **red job does not block the merge → non-biting silent gate.** This
   is the exact failure mode the mission flags ("a red job that does not block a merge is
   not a biting gate") — and it needs no external repo.
2. **(c) in place of the delegated job**: the reusable `uses:` is removed, so the required
   context `gitleaks / Secrets Scan` NEVER reports → GitHub holds it PENDING → merges
   block indefinitely on a required check that can never turn green, while the actual
   enforcing job runs under an unregistered name.

**Either way, (c) requires an ADDITIONAL branch-protection contexts edit** (add the new
job's context; and in mode 2, remove/replace the stale one). The only escape without a
branch-protection edit is to hand-craft the local job's `name:` as the literal string
`"gitleaks / Secrets Scan"` — a fragile spoof the author neither identified nor endorsed.

**Impact on the author's §3(d) conclusion.** The author wrote: *"fixing (a) or (c) alone
is sufficient — once the job can actually go red, the existing required-check wiring will
bite without any further branch-protection edit … the remediation surface is narrower than
'gate config + branch protection both need fixing'."* This NARROWS:
- **TRUE for (a)**: the SAME reusable job stops swallowing; same registered name; bites
  automatically. The "just the exit-code swallow" surface is correct for (a).
- **FALSE / too strong for (c)**: a local job's new check name is not the registered
  context; (c) is job-addition **+ branch-protection registration**, a two-action
  remediation. Shipping (c) without the registration reproduces the silent-gate class this
  whole wave exists to close.

Because the handoff RECOMMENDS (c) as "the only currently-independently-viable option,"
this is a **material correction to the F-7 input**, not a footnote.

**Verdict: refuter (b) STANDS for the current config; AR-1 NARROWS the §3(d) fix-locus
conclusion for the recommended locus (c).**

---

## §3 Refuter (c) — caller input disables enforcement? — STANDS

Read the full decoded upstream body (§1) own-hands: the reusable workflow's trigger block
is `on: workflow_call:` with **no `inputs:` map at all**. The caller (`gitleaks.yml`)
passes **no `with:` block**. There is no input surface through which enforcement could be
toggled from the caller side, in either direction. **Verdict: STANDS** — the bypass is
100% upstream and non-configurable from the caller. Not a null; checked, negative.

---

## §4 Refuter (d) — triggered on the events that matter? — STANDS

Caller `on:` (read own-hands): `push: branches: [main]` and `pull_request: branches:
[main]`. The `pull_request` trigger is what branch protection needs to gate PRs; empirically
confirmed by the live `gitleaks / Secrets Scan` check run present on main HEAD.

Merge-queue leg re-derived own-hands (the one leg I did not inherit):
```
gh api graphql -f query='{repository(owner:"autom8y",name:"autom8y-asana"){mergeQueue{id}}}'
```
Exit 0 → `{"data":{"repository":{"mergeQueue":null}}}`. No merge queue configured, so the
absent `merge_group:` trigger is currently inert, not a bypass. **Verdict: STANDS** with
the author's future-proofing caveat (enable merge queue later → add `merge_group:`).

---

## §5 UV-P-CoC-4 corollary — "enforcement trips + rotation-insufficient" — SURVIVES (bounded residual)

### §5.1 Would an enforcing run trip? — YES survives, with a CR-5-bounded residual

Four compounding factors, each re-checked own-hands:
- **Full-history scan**: `fetch-depth: 0` on checkout (§1 body, own-hands). ✓
- **`detect` walks full `git log -p`, no `--log-opts`**: consistent with the command
  line in the decoded body (no range restriction passed). ✓
- **cred-t21 in main history**: per `.know/defer-watch.yaml` PATH+FACT ONLY (commits
  `a578ca85`/`525431de`/`15cffee1`, `.claude/settings.local.json`, absent-at-HEAD). Not
  re-read for value (CR-5). History-mode scan finds absent-at-HEAD values. ✓
- **Local rule fires + no suppression**: I read `.gitleaks.toml` own-hands. The
  `asana-native-pat` rule (L52-56) is present; `[extend] useDefault = true` (L4-5) means
  it is additive to defaults; `[allowlist].paths` (L58-75) contains only
  `'''(?i)\.claude/.*\.md$'''` for `.claude/` — a **markdown-only** exemption that does
  NOT match `.claude/settings.local.json` (a `.json`). No `[allowlist].regexes`,
  `.commits`, or `.stopwords` exist in the block. ✓

**One hop past the author on the regex itself (CR-5-safe).** The author asserted the rule
"would fire" but did not test the regex. I tested the verbatim pattern
`\b[12]/[0-9]{6,}(?:/[0-9]{6,})?:[0-9a-f]{32,}\b` against SYNTHETIC tokens of the DOCUMENTED
shape only (never the real value):

| Synthetic input (shape only) | keyword pre-filter | regex |
|---|---|---|
| `1/{≥6 digits}:{32 lowercase-hex}`, JSON-quoted | hit | **MATCH** |
| `2/{gid}/{sub}:{32 lowercase-hex}` | hit | **MATCH** |
| bare `1/…` (unquoted) | hit | **MATCH** |
| UPPERCASE-hex variant | hit | no match |
| gid = 5 digits (< `{6,}`) | hit | no match |
| hex = 31 chars (< `{32,}`) | hit | no match |
| legacy `0/…` form | miss | no match (intentionally excluded per rule comment) |

The rule DOES fire on the documented `1/`/`2/` native-PAT shape, and the keyword
pre-filter (`["1/","2/"]`) hits. **Bounded residual (CR-5 boundary):** the match is
validated against the DOCUMENTED shape, not the real token. The regex assumes
lowercase-hex, gid ≥ 6 digits, and hex ≥ 32 chars. Standard Asana native PAT format is
long-numeric-gid + lowercase 32-hex, so the assumption is sound — but if the leaked token
deviated (uppercase hex, shorter fields), the rule would silently not fire. I cannot close
this residual without reading the credential; CR-5 forbids it. The rule's own provenance
(purpose-built "GATE-GAP-1 / TDD §5" against this exact leak class) is corroborating but
is the rule-author's assertion, not an independent token match. **Net: SURVIVES; residual
flagged, not dismissed.**

### §5.2 Is rotation insufficient? — YES survives

gitleaks pattern-matches git history, not token liveness. A rotated-but-still-in-history
string still matches `asana-native-pat` and still trips `detect`. Rotation addresses
live-credential risk; it does NOT green the gate. A baseline (`--baseline-path`) or
`.gitleaksignore` covering the historical findings is required IN ADDITION before any
enforcing flip can go green. **Structurally sound — SURVIVES.**

Two precision notes (extend, do not refute, the corollary):
- `.gitleaksignore` keys on finding FINGERPRINT (`commit:file:rule:line`), not bare commit
  SHA; the artifact must carry the three findings' fingerprints. The current-HEAD
  `.gitleaksignore` is honored across all historical findings by a history-mode scan, so
  the mechanism is viable.
- The baseline must cover **every** historical finding that trips, not only cred-t21's
  three commits. If any OTHER historical secret exists in this repo's history (the memory
  index references residual leaked-PAT / `#927` items), it too must be baselined or the
  gate stays red. Scope the baseline to the full tripping set, not just cred-t21.

**Verdict: UV-P-CoC-4 corollary SURVIVES the attack (STANDS), with a bounded CR-5 residual
on regex-vs-real-token and a scope extension on the baseline set.** F-7's premise
(enforcement trips → rotation alone does not green the gate → baseline also required) holds.

---

## §6 Fix-locus slate — HOLDS on (a)/(b)/(d), NARROWS on (c)

- **(a) upstream `|| true` removal**: HOLDS. Durable/org-correct; same reusable job, same
  registered check name → bites automatically once it can go red. Blast-radius caveat
  (other consumers) stands; cross-repo authority constraint stands.
- **(b) re-point to enforcing variant**: HOLDS. No enforcing variant exists upstream
  (`gh api …/contents/.github/workflows` own-hands would confirm the author's listing; I
  did not re-run this specific listing — accepted as the author's leg, not independently
  re-derived); collapses into (a).
- **(c) local enforcing job**: **NARROWS per AR-1.** Viable and fully local for the JOB,
  but NOT single-action: it requires a branch-protection contexts edit (or a fragile
  literal `name: "gitleaks / Secrets Scan"` spoof) to bite. Absent that, (c) is a
  non-biting silent gate (mode 1) or a permanently-pending block (mode 2). The author's
  "(c) alone is sufficient / surface is just the exit-code swallow" does NOT hold for (c).
- **(d) branch-protection registration**: HOLDS as "already correct **for the delegated
  reusable job**" — but this correctness is precisely what does NOT transfer to a local
  job (c). Re-framed: (d) is correctly wired for (a); (d) is a REQUIRED SECOND STEP for (c).
- **F-8**: no halt — (a) and (c) both remain viable loci; concur with the author.

---

## §7 NR-5 verdict table (second-read)

| Item | Author disposition | My own-hands hop | Verdict |
|---|---|---|---|
| NR-5 negative ("bypass in a repo I cannot read") | CLOSED | Re-fetched pinned body byte-identical | **STANDS** (refuted) |
| (a) pin fetchable / byte-identical | tried, exit 0 | Re-ran `gh api` @ `f5601acb…`, byte-identical `|| true` | **STANDS** |
| (b) local bypass in current config | none | Read caller; empirically confirmed live check name = required context | **STANDS** |
| (b′) ADDED: fix-locus (c) non-biting-gate | not named | Live check-runs show plain jobs get simple names, only reusable get `A / B` | **NARROWS §3(d)** |
| (c) caller input disables enforcement | no / cannot | Full upstream body: `workflow_call:` with zero `inputs:`; caller no `with:` | **STANDS** |
| (d) triggers (PR / merge queue) | PR yes / MQ n/a | Re-derived `mergeQueue: null` own-hands | **STANDS** |
| UV-P-CoC-4: enforcement trips | YES | Synthetic-shape regex MATCHes; allowlist no-exempt confirmed | **SURVIVES** (CR-5 residual) |
| UV-P-CoC-4: rotation insufficient | YES | History-match mechanism sound; baseline scope extended | **SURVIVES** |

**Nulls**: one leg NOT independently re-derived — the §3(b) upstream workflow-directory
listing (accepted as the author's receipt, not re-run). All other legs re-derived
own-hands with command + exit code. No genuine null returns in the NR-5 sweep itself.

## §8 Fences honored

CR-5: cred-t21 value never read/reconstructed; regex tested on synthetic shapes only; no
code-scanning-alert detail endpoint queried. External repo not modified (read-only
`gh api`). No git verbs. This artifact rests authored-unmerged (Q-4 HALT) for the main
thread. Self-assessment cap MODERATE; own-hands re-derivations are rite-disjoint external
corroboration.
