# RUNBOOK — GATE-1 landing-receipt certification harness

**You should not have to ask anyone a question to use this.** If you do, that is a
defect in this runbook — please record it, because "runnable without interviewing
the author" is this harness's actual acceptance test (edge H-3).

Nothing here writes. Every statement is gated to `SELECT`, the session is opened
`READ ONLY`, and credentials are never printed.

---

## 1. What this answers

> Has this clinic's integration **LANDED**?
> *"three ATTRIBUTED routed bookings observed clean"* — see
> [`predicate.toml`](predicate.toml) for the exact, editable definition and
> [`../../.sos/wip/SCHEMA-landing-receipt-2026-09-01.md`](../../.sos/wip/SCHEMA-landing-receipt-2026-09-01.md)
> for what every word of it means mechanically.

**Read §0 of the schema before you certify anything.** One-line version: under
the shipped default the `LANDED` verdict counts bookings from *every* writer, so
it is a reading of the **ad funnel**. The `ebi` number on every output is the
reading of the **forwarding integration**. As of 2026-09-01 those were **41** and
**3** clinics respectively. They answer different questions.

---

## 2. What you need

| | |
|---|---|
| Python | 3.12+ (uses `tomllib`) |
| Driver | `mysql-connector-python` |
| Credentials | a `.env` defining `DB_HOST`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DATABASE` — default location `/Users/tomtenuta/Code/a8/autom8/.env`, override with `--env` |
| Network | reachability to the production MySQL host (read-only) |

**Where the files are.** This harness is not on `main` yet — it lands with PR #400
(branch `feat/certification-harness`). Check that branch out before anything below
will resolve:

```bash
git -C /path/to/autom8y-asana fetch origin
git -C /path/to/autom8y-asana switch feat/certification-harness   # or use a worktree
cd /path/to/autom8y-asana
```

You do **not** need the repo's virtualenv, and you do not need to install
anything permanently:

```bash
uv run --with mysql-connector-python python scripts/certification/landing_receipt.py preflight
```

`pip install mysql-connector-python` then plain `python3` works equally well. Every
example below is written with the `uv` prefix; drop it if you have the driver.

If you have the repo's venv active, `uv run` prints a
`warning: VIRTUAL_ENV=… does not match the project environment path` line and
then proceeds. It is harmless — see §7.

---

## 3. Five minutes, in order

### Step 1 — prove the instrument works

```bash
uv run --with mysql-connector-python python scripts/certification/landing_receipt.py preflight
```

Expect `PREFLIGHT OK`. It prints the predicate it is operating under, that
predicate's fingerprint, any switches that have been disabled, and seven checks
including a live connection. **If any switch is listed as disabled, someone has
narrowed or widened the predicate — find out why before continuing.**

### Step 2 — prove the instrument has teeth

```bash
uv run --with mysql-connector-python python scripts/certification/landing_receipt.py selftest
```

Expect `SELFTEST: 12 passed, 0 failed`.

This is not a smoke test. It runs the live harness against **real production rows
with known verdicts**, in both directions:

* known-bad rows (an attorney-referral lead with nothing to do with our funnel; a
  2027 date-bug row) must be **REFUSED** — and refused on the *specific expected
  leg*. A harness that refuses everything for the wrong reason **fails** here.
* the known-good row (soak booking #1) must be **CERTIFIED**.
* the dedup rule must collapse a dual-write twin and must **not** collapse two
  genuinely different bookings.
* the scope filter must both keep and refuse the *same* row under different
  configurations — a knob that never refuses is decorative.
* the retired-substrate guard is fired **on purpose** and must raise.

Each line prints *why* the fixture exists. If a fixture row has been deleted from
production you will get an explicit `fixture rows … NOT FOUND` failure rather than
a silent pass.

### Step 3 — see the whole population

```bash
uv run --with mysql-connector-python python scripts/certification/landing_receipt.py survey --min-eligible 3
```

Two columns matter:

* `elig` — bookings counted from **any** writer. Ad-funnel reading.
* `ebi`  — bookings whose dedup cluster contains `email-booking-intake`.
  Forwarding-integration reading.

The footer prints both totals side by side. A survey is a population reading, not
a certificate.

### Step 4 — issue the receipt you will cite

```bash
uv run --with mysql-connector-python python scripts/certification/landing_receipt.py clinic --office-phone +14079068111
```

Add `--json` for the machine-readable form. Exit code is `0` when LANDED and `3`
when NOT-LANDED, so this is scriptable.

`--json`, `--env`, `--predicate` and `--timeout` may be placed either before or
after the subcommand and resolve identically. (In the first cut of this harness
they did not: a pre-subcommand flag was silently discarded and the receipt
printed the *default* predicate's fingerprint as authoritative. That is fixed —
see §4 — but if you are ever unsure which predicate a receipt was computed
under, the `predicate fingerpr.` line on the receipt is the answer, not the
command you think you typed.)

Every receipt carries, on its face: the predicate wording and its ratification
status, the predicate fingerprint, the attribution path and guard state, the
window and where the window came from, the count and shortfall, every member with
its full path-a chain, every refusal with its reason code, and a **BOUNDARY**
block naming what the receipt does not certify.

### Step 5 — interrogate any single row

```bash
uv run --with mysql-connector-python python scripts/certification/landing_receipt.py booking --appt-id 18229605 18229606
```

Prints every leg with `ok`/`NO`, the whole path-a chain, all flags, and any
absorbed duplicates. This is the tool for "why did that one refuse?".

---

## 4. Changing the predicate (you probably need to)

**Never edit the Python to change what the predicate means.** Everything is in
[`predicate.toml`](predicate.toml), and every receipt fingerprints that file.

### Prefer a copy over an in-place edit

You usually do **not** want to edit the shipped file. Copy it, edit the copy, and
point the harness at it with `--predicate`:

```bash
cp scripts/certification/predicate.toml /tmp/predicate.ebi.toml
$EDITOR /tmp/predicate.ebi.toml
uv run --with mysql-connector-python python scripts/certification/landing_receipt.py \
    --predicate /tmp/predicate.ebi.toml clinic --office-phone +14079068111
```

Why this matters: the shipped file's fingerprint is the one every previously
issued receipt cites. Editing in place silently re-points that fingerprint at
different content, so an old receipt and a new one can claim the same predicate
while meaning different things. A copy keeps both readings citable side by side —
each receipt names its own file path *and* its own fingerprint, so two receipts
under two predicates are trivially told apart.

Verify you got the file you meant: the `predicate fingerpr.` line on the receipt
prints the hash and the resolved path. If it shows the shipped path when you
passed `--predicate`, stop and re-read the command.

### Common edits

| you want | edit |
|---|---|
| the ratified wording, once G-3 is spoken | `predicate.wording_of_record` (verbatim), `wording_status = "RATIFIED"`, `ratification_anchor = "<path:line>"` |
| a ROUTED-only reading (drop "ATTRIBUTED") | `legs.attributed.enabled = false` |
| a count other than three | `predicate.required_count` |
| **the forwarding-integration reading** | `scope.booking_source.mode = "include"` and `include = ["email-booking-intake"]` |
| a different window for one clinic | add to `[window.overrides]` with a provenance comment |

`attribution.path` is **not** a knob. `"path-a"` is the only legal value and
anything else aborts the harness. Path-b (`ad_accounts`) is retired substrate:
`ad_account_id` is non-unique — one agency master carries 857 office phones
including an internal one — so a receipt walking it is vacuous. Any query
mentioning `ad_accounts` raises before it reaches the server, and the guard is
proven to bite at every `preflight` and `selftest`.

---

## 5. Reading a refusal

Refusals are reason-coded. The first failing leg is the headline; all failing legs
are listed.

| prefix | family | meaning |
|---|---|---|
| `R…` | ROUTED | not a real booking, or its contact is not in our funnel |
| `A…` | ATTRIBUTED | no ad attribution, or the ad's campaign does not belong to this clinic |
| `C…` | CLEAN | duplicate, cancelled/no-show, incoherent clinic identity, internal, or outside the window |
| `S…` | SCOPE | the booking is fine — *you* asked for a narrower booking path |

An `S1` refusal is **not** a data-quality finding. It means the certifier chose a
narrower claim.

A refusal means "not usable as landing evidence". It does **not** mean "not a real
appointment".

---

## 6. Flags (never refusals, always shown)

| flag | means |
|---|---|
| `F-SYNTHETIC-LEAD` | the lead is `platform='test'`. The activation apparatus mints attributed test leads by design, so these count — but a claim that excludes them is a narrower and possibly more honest claim. Every receipt reports the count; the renderer shouts if *all* members are synthetic. |
| `F-TZ-AMBIGUOUS-START` | `start_datetime` stored with no offset, so the future-check compares local wall-clock against a UTC `created`. Ratified semantics, implemented verbatim, flagged rather than silently corrected. |
| `F-DEDUP-ABSORBED-N` | this booking absorbed N duplicate rows (the dual-write twin). |

---

## 7. Troubleshooting

| symptom | do this |
|---|---|
| `warning: VIRTUAL_ENV=… does not match the project environment path` | Harmless. `uv` is telling you it is ignoring your active venv and using its own ephemeral one, which is what you want here. Output after the warning is valid. Silence it with `--active` if it bothers you |
| `No module named 'mysql'` | prefix with `uv run --with mysql-connector-python`, or `pip install mysql-connector-python` |
| a path in this runbook does not exist | you are probably on `main`. This harness lands with PR #400 — see §2 |
| `FATAL: credentials file not found` | pass `--env /path/to/.env` |
| `FATAL: <KEY> missing` | the `.env` lacks one of the four `DB_*` keys |
| `FATAL: could not connect` | network/VPN. The message is redacted — it will never contain a credential |
| `fixture rows … NOT FOUND` in selftest | a teeth fixture row has left production. Do **not** proceed; the teeth are no longer proving anything |
| `RetiredSubstrateError` from normal use | someone added an `ad_accounts` query. That is the guard working. Remove the query |
| `!! DISABLED SWITCHES` in the header | the predicate has been narrowed or widened relative to the shipped default. Establish why before citing the receipt |
| exit code 3 | the clinic is NOT-LANDED. Not an error |

---

## 8. Provenance

* Predicate legs P1–P5 and the path-a-only ruling: ad-lead-gate sitting
  ratification, 2026-09-01, R-2/R-3/R-4.
* Staged-lookup pattern: that sitting's `audit2.py` / `audit3.py`.
* Predicate wording and its parameterisation: `close-the-activation-loop` frame
  §1–2 and shape CE-4 / FORK-4.
* Everything mechanical: the schema at
  [`../../.sos/wip/SCHEMA-landing-receipt-2026-09-01.md`](../../.sos/wip/SCHEMA-landing-receipt-2026-09-01.md).
