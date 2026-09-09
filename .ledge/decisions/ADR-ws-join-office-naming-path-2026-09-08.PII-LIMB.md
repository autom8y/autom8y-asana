---
id: CS-001
slug: ws-join-office-naming-path-pii-limb
sprint: S-04b
initiative: name-the-client
wave: 0
rite: security
seat: compliance-architect
deploy_class: C-INERT
status: RULING — LIMB (incorporate by reference)
sibling_limb: .ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.md (architect, S-04a, authored in parallel)
consolidation: main thread at PT-01
frameworks: []          # see §9.0 — no external framework is asserted; the governing
                        # authorities here are C-15 (operator) and SPEC §6.1 (in-code)
evidence_grade: MODERATE
self_ref_cap: MODERATE  # single-seat authorship; no rite-disjoint corroboration yet
authored: 2026-09-08
---

# ADR — WS-JOIN office-naming path · **THE PII LIMB**

> **This is a limb, not an ADR.** It rules on **lawfulness only**. It selects no
> mechanism, sizes no work, and orders no sprint. The options/deploy-class ADR is
> the architect's (S-04a) and is being authored in parallel; incorporate this file
> **by reference**. Where the two disagree on whether a path is lawful, **this limb
> governs the lawfulness question and only that question**.

---

## §0 STANDING, AND THE THREE THINGS THIS LIMB WILL NOT DO

Frame §4.1 names the security seat **a participant in authoring, not an optional
reviewer**. This limb is written on that standing.

It will not:

1. **Re-litigate C-15.** The rejection of phone-in-structured-logs is ratified. It is
   applied here, never reopened.
2. **Annex the 1,252 office-blind residual.** Frame §10 row 6: it is a warden +
   security call, *adjacent* to WS-JOIN — and **adjacency is not inclusion**. It is
   cited below exactly once, as the measured cost of a control. No cure is proposed.
3. **Choose the mechanism.** Which lawful path WS-JOIN takes is the architect's and
   Pythia's (frame §9 M-2). This limb marks each path lawful, conditional, or refused.

---

---

## §0.5 ★ AMENDMENT A1 — POST-AUTHORSHIP, ON COORDINATOR CORRECTION (same sitting)

The coordinator transmitted a correction after this limb's body was authored, carrying
S-04a's parallel findings. **I re-took every affected measurement myself before accepting
any of it.** Five amendments follow. **One is a material self-correction against my own
ruling (A1.4) and it is the most important line in this section.**

### A1.1 — REF RE-PINNED to `883eb3bf`. This is move **SIX**, and my reads SURVIVE it

The coordinator reports `origin/main = 883eb3bf` and that `e292b616` (my §1 reading) "is
not origin/main". **Both are true, and both readings were correct when taken** — the label
moved between us. Re-resolved authoritatively at my own hand:

```
git -C <autom8y> fetch origin main            -> branch main -> FETCH_HEAD
git -C <autom8y> rev-parse origin/main        -> 883eb3bf
git -C <autom8y> merge-base --is-ancestor e292b616 883eb3bf   -> YES-ancestor
git -C <autom8y> rev-list --count e292b616..883eb3bf          -> 1
  883eb3bf docs(ledge): file the EBI operator-interview rulings in the precedent form
```

**★ THE DECISIVE CHECK — do my quotes still hold at the new ref?**

```
git -C <autom8y> diff --stat e292b616 883eb3bf -- <all 9 files I read>
  -> NO OUTPUT.  Byte-identical.
POSITIVE CONTROL (same diff form, unscoped):
  -> " .../RULINGS-ebi-operator-interview-2026-09-08.md | 98 ++++++++++++++++++++++"
     1 file changed, 98 insertions(+)      ← the form DOES produce output; the zero is TAKEN
```

**Every line number, every verbatim quote and every finding in this limb stands unchanged
at `883eb3bf`.** The one intervening commit is `docs(ledge)`. **Re-pin the ref; change
nothing else.** §1.1's count of FIVE was correct at my start; **the count is now SIX**, and
the label moved *during a single sprint's authorship* — which is itself the strongest
available argument for citing SHAs and never the label.

### A1.2 — The three-planes correction: **CONFIRMED, and independently reached**

The coordinator states my charge conflated three PII planes and that the
`ebi_witness_ledger.py:21/:394` drop is renderer-side, not the plane WS-JOIN would trade.
**Confirmed, and this limb reached it independently before the correction arrived** — see
**§3.1** (which separates the *patient-data* control from the *account-primary-key*
control) and **§2** (which scopes the `:21`/`:394` drop to *"a per-post record"* and *"the
renderer never emits the raw payload string"*, i.e. explicitly renderer-side). **F-2 is
this limb's own finding, taken own-hands at `resolve_office.py`, and it converges
line-for-line with S-04a's independent measurement** — including the asymmetry the
coordinator calls the finding (`redact_uuid(guid)` beside a clear-text phone on the same
call), which this limb records at **§3 F-2** and again at **§5 P-3**.

**Two seats, disjoint probes, same five line numbers.** That is corroboration, not echo.

**One qualification I decline to drop.** The coordinator writes *"there is nothing to
reintroduce — it is already there."* **True of the plane; false of the record.** The
`ebi_witness_ledger` drop remains a real, test-pinned control over the **git-tracked
witness artifact** (`tests/test_ebi_witness_ledger.py:434`), and **PR-8 remains REFUTED**.
A design that pushes the phone into the *witness JSON* would still be breaking a live
control, even though the *log plane* is already open. **The two surfaces must be ruled
separately, and this limb does.**

### A1.3 — Q1 RESTATED, as instructed: ADD / LEAVE / INDEPENDENT

Q1 is no longer hypothetical. Re-ruled on the factual basis:

| id | mechanism | Q1 restated | verdict unchanged? |
|---|---|---|---|
| **P-1** = S-04a **H** | raw phone as join key | **ADDS** — new emission sites on top of an existing exposure | REFUSED |
| **P-2** | truncation / last-4 | **ADDS** | REFUSED |
| **P-3** | unsalted digest (`office_phone_hash`) | **ADDS** a second, *differently-shaped* exposure — and F-3 shows this one is already live on the EventBridge plane too | REFUSED |
| **P-4** | keyed PRF, co-resident key | **ADDS** | REFUSED |
| **P-5** | keyed PRF, disjoint key custody | **ADDS** a derivative | NOT CLEARED → O-4(c) |
| **P-6** = S-04a **C** | read-time resolution | **LEAVES UNTOUCHED** — emits nothing | **CLEARED** |
| **P-6-naive** | reader that consumes the *leaked* phone field | **LEAVES the exposure in place AND MAKES THE PRODUCT DEPEND ON IT** | **REFUSED — see below** |
| **P-7** = S-04a **F** | minted opaque token | **INDEPENDENT** — zero mutual information with the phone | CLEARED, minted form only (§6) |

**★ "Already exposed" strengthens the P-6-naive refusal rather than weakening it.** When
the exposure was hypothetical, a reader consuming the phone field was merely inelegant.
Now that the exposure is **real, standing, and owed to a remediation owner**, a reader
built on it would make the bar **structurally dependent on a condition someone is
expected to remove** — so remediating the leak would *break the product*, and the leak
would acquire a defender. **That is how a temporary exposure becomes permanent.** This is
the single sharpest instruction this limb issues, and the coordinator's finding makes it
sharper, not softer.

### A1.4 — ★★ MATERIAL SELF-CORRECTION: **P-6′ IS WITHDRAWN FROM THE CLEARED SET**

**§5 clears "P-6′" (P-6 *plus removing* `office_phone` from the five extant sites) and
calls it "the PII-optimal path". That clearance was WRONG and I withdraw it.**

The removal half touches
`services/email-booking-intake/src/email_booking_intake/pipeline/stages/resolve_office.py`
⇒ **`services/**` ⇒ DEPLOY-CLASS A ⇒ R-35-frozen**. Performing it inside this envelope
is **BUNDLING**, which **C-1 makes a REFUSAL**. I reached the right *security* conclusion
and attached it to the wrong *envelope* — the exact error my own §8 fence exists to
prevent, committed one section earlier in the same document. **Recorded rather than
quietly patched.**

**The correction splits P-6′ in two, and only the first half is mine to clear:**

- **P-6 (read-time resolution, plane untouched) — ★ CLEARED, and it is the whole of
  WS-JOIN's lawful path.** It lands C-INERT and is **not R-35-blocked**.
- **THE REMOVAL — PII-lawful as a posture, but OUT OF THIS ENVELOPE. Not cleared, not
  scheduled, not adjudicated. SURFACED as NEW MATTER to O-4(b) and routed to
  `change-warden` + security.** I state the *finding* (the five sites, the asymmetry,
  the three open gates at §3.2) and **stop at the surfacing.** No cure is proposed here.

**What survives the withdrawal, and it is the substantive point:** the observation at §5
P-6′ that **`office_name` is ALREADY emitted beside the redacted GUID at
`resolve_office.py:263`** stands, is untouched by R-35, and matters — **the log plane
already names the office.** That is evidence *for* the read-time option's feasibility. It
is **not** a licence to edit the file.

### A1.5 — Mapping to S-04a's eight options, and the rider on its recommendation

| S-04a | this limb | ruling |
|---|---|---|
| **C** — read-time via `prefix →[RegistryPort]→ guid →[NamePort]→ name` | **P-6** | **★ CLEARED.** The phone appears at no step; nothing is emitted. C-16-strongest for the reason at §5 P-6 (records carry only the GUID, so the DB-status-read successor swaps the adapter and **no historical record breaks**). |
| **H** — phone as join key | **P-1** | **REFUSED** (both seats, independently). |
| **F** — minted non-reversible token | **P-7** | **CLEARED in the MINTED form only.** §6 stands in full and is **retained deliberately as the fallback ruling**: if C fails later, F's salt custody / minting locus / rotation are **already ruled** and need not be re-litigated under time pressure. **§6.1's core holds: strike the word "derived."** |

**★ BINDING RIDER ON OPTION C — this is a condition of the clearance, not a comment.**
The `NamePort` adapter **MUST resolve from the GUID** via the join proven live at
`resolve_office.py:1,:171` (`get_business_by_guid_async`). It **MUST NOT** read the
`office_phone` field present at `:204/:214/:233/:248/:262`. A `NamePort` that shortcuts to
the already-leaked phone field is **P-6-naive and is REFUSED** (A1.3). **The port
abstraction makes this easy to violate invisibly — the adapter boundary is exactly where
"just read the field that's already there" looks like a performance win.** Pin it.

**Injectivity, noted and handed back.** S-04a's `RegistryPort` is *injectivity-asserted*
(8-hex prefix → guid). This limb takes no position on the injectivity mechanism — it is a
correctness question, not a PII question. **But note the collision arithmetic at §4 (iii)
transfers directly:** over N ≈ 10²–10³ offices in a 2³² space, expected collisions ≈ 10⁻⁴.
Injectivity will hold in practice; **assert it rather than assume it**, because the failure
mode is a booking attributed to the *wrong named client* — which is worse for this
initiative's bar than no attribution at all.

### A1.6 — Retention bound on P-6's retroactivity

The coordinator states **log retention is 90 days**. **[MODERATE — attributed to the
coordinator; not measured by this seat.]** §5 P-6 claims read-time resolution is *"the
only option that is retroactively effective … within their retention window."* **That
window is 90 days.** Beyond it, P-6 is forward-only, exactly like every emit-time option.
The claim is bounded, not withdrawn — and the bound is consistent with DIAGNOSIS §3's
89-day continuous-zero observation.

### A1.7 — The coordinator's disclosed vacuous zero: a THIRD instance this sprint

The coordinator discloses that its **first** probe used a wrong path, returned zero, and
**would have reported this limb's premise refuted on that vacuous zero** — corrected by a
non-empty-corpus control plus a `zzz_not_a_real_token_zzz` negative control. **Logged as a
third instance in this sprint alone**, alongside the two that fired on me (§1.2: fence 3
on a `"$REF:path"` read; fence 1 on a dead `.semgrep-security.yml` control). **Three
untaken-or-nearly-untaken zeros, three seats, one sitting — and 3/3 pointed in the
safe-looking direction: two would have reported "nothing there", one would have reported
"premise refuted".** N=14 across the arc is not an abstraction; **it is the base rate, and
it held again today.**

---

## §1 SUBSTRATE — RE-RESOLVED AT MY OWN START (fence 2)

| repo | branch | HEAD | origin/main | dirty |
|---|---|---|---|---|
| `autom8y` (code, read-only) | `fix/wss-wildcard-scope-bypass-closure` | `29e59e81` | **`e292b616`** | 352 |
| `autom8y-asana` (session) | `main` | `d75bfe1a` | `389c59bc` | — |

### ⚠ 1.1 `origin/main` MOVED AGAIN — this is the **FIFTH** move this arc

The charge records the main thread's 2026-09-08T20:33Z resolution as **`a4bc0e39`** and
counts **four** moves. At my start it is **`e292b616`**.

```
git -C <autom8y> merge-base --is-ancestor a4bc0e39 e292b616   -> YES-ancestor
git -C <autom8y> rev-list --count a4bc0e39..e292b616          -> 1
git -C <autom8y> log --oneline -3 e292b616
  e292b616 docs(ledge): disposition — the wave-1 ordering question and eleven unrecorded operator rulings
  a4bc0e39 docs(ledge): land the OW-1 ruling and its telos line
```

`a4bc0e39` is a clean ancestor and the delta is **one `docs(ledge)` commit**, so nothing
in this limb's code substrate changed. **Every code read below is pinned at
`e292b616`.** The count stands at **FIVE**; T-1 remains ACTIVE.

### 1.2 Fences fired on me, recorded

- **FENCE 3 FIRED.** My first read used `"$REF:services/..."`. zsh's `:s` modifier fired
  *inside the double quotes* and mangled the path to
  `...3cmail-booking-intake/...` → `fatal: ambiguous argument`. Re-taken with
  `"${REF}:services/..."`. **The trap is real and it caught me on the first attempt.**
- **FENCE 1 FIRED.** My probe for PII rules in `.semgrep-security.yml` returned a zero
  whose positive control (`grep -n "  - id:"`) produced **no output — control DEAD**. The
  zero was **untaken** and I did not report it. Re-taken in §3.2 with a control that fires.

---

## §2 THE LOAD-BEARING FACT — READ AT AN EXPLICIT REF, QUOTED FROM WHAT I READ

Not inherited from the charge. `git -C <autom8y> show
e292b616:scripts/ebi_witness_ledger.py` (942 lines), lines **21** and **394**, verbatim:

> **`:20-22`**
> ```
>       {pk, lead_id, appt_time, status, created_at}. The raw email / phone /
>       office_phone in the payload are DROPPED (not hashed, not truncated —
>       dropped). The renderer never emits the raw ``payload`` string.
> ```

> **`:393-395`**
> ```
>             # ★ PII-MINIMIZATION: ONLY these five fields. email / phone /
>             # office_phone are DROPPED (not hashed). The raw payload string is
>             # never carried forward.
> ```

`grep -n office_phone` over that file returns **exactly 2 hits, both comments** — `:21`,
`:394`. **The charge's quotation is accurate.** The drop is real, it is deliberate, it is
labelled a binding PII-minimisation, and it is **pinned by a test**
(`tests/test_ebi_witness_ledger.py:434` — `assert "+15559876543" not in blob  # office_phone dropped`).

**PR-8 stands REFUTED. The drop is a control, not sloppiness.** Everything below is
built on that, not against it.

---

## §3 ★★ THE STATE IS NOT WHAT THE OPTION SLATE ASSUMES — FOUR FINDINGS

The charge frames WS-JOIN as *asking permission to add* an identifier to a plane that
does not have one. **Read at the ref, the plane already has it.** Four findings, each
receipted. They do not weaken the control; they relocate the decision.

### F-1 — The GUID→office join **ALREADY EXISTS, LIVE, ON THE BOOKING PATH**

`services/email-booking-intake/src/email_booking_intake/pipeline/stages/resolve_office.py:1`,
verbatim:

> `"""Resolve office stage -- resolves chiropractor GUID to office phone.`

`:171` — `business = await data_read_client.get_business_by_guid_async(guid)`.
`:229` — `full_business = await data_read_client.get_business_by_phone_async(office_phone)`.

The join is not missing. It is a **data-service call executed on every piece of mail that
reaches this stage.** RATIFICATION §3:44's *"nobody holds the join"* is true of a
*durable artifact*; it is **not** true of the running pipeline. **WS-JOIN does not need
to build a join. It needs a lawful place to stand while reading one that already runs.**

### F-2 — Raw `office_phone` is **ALREADY ON THE LOG PLANE**, at five sites, ungated

`resolve_office.py`, structured-log emissions, verbatim field spellings:

| line | event | fields as emitted |
|---|---|---|
| `:202-206` | `guid_resolved_via_data_service` | `guid=redact_uuid(guid)`, **`office_phone=office_phone`**, `source`, `resolve_source` |
| `:212-216` | `guid_resolved_via_override` | `guid=redact_uuid(guid)`, **`office_phone=office_phone`**, `source`, `resolve_source` |
| `:231-235` | `business_lookup_failed` | **`office_phone=office_phone`**, `error` |
| `:248` | `business_not_found` | **`office_phone=office_phone`** |
| `:259-263` | `office_resolved` | `guid=redact_uuid(guid)`, **`office_phone=full_business.office_phone`**, **`office_name=full_business.business_name`**, `resolve_source` |

Also `:270` — `message=f"Resolved to {full_business.business_name} ({full_business.office_phone})"`,
and `orchestrator.py:180` forwards `message=result.message` into a log call.

**Nothing redacts these.** Established by direct read, each with a firing positive control
(§3.2). At `:259-263` the *same log line* carries the redacted GUID prefix **and** the raw
phone **and** the plaintext business name — **the join, materialised in plaintext, on the
log plane, today.**

> **This is not a licence.** "Already broken" authorises nothing. It changes *what O-4 is a
> fork about* (§7), and it disqualifies one option that would otherwise look free (§5, P-6-naive).

### F-3 — ★ An **unsalted SHA-256 of `office_phone`** is already emitted — *as the PII remediation*

`services/email-booking-intake/src/email_booking_intake/events.py`:

> `:14` — ``- ``office_phone_hash``: SHA-256 prefix of the office phone.``
> `:19-21` — ``* EXCLUDED (PII): ... - ``office_phone`` in plaintext.``
> `:25-26` — `Downstream EventBridge consumers therefore never receive plaintext PII from this event bus.`

The construction, `:51-53`, verbatim and complete:

```python
def _hash_prefix(value: str, *, length: int = 8) -> str:
    """Return the first ``length`` hex chars of SHA-256 of ``value``."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]
```

`:140` — `"office_phone_hash": _hash_prefix(office_phone) if office_phone else "",`

**Unsalted. Unkeyed. Truncated to 8 hex (32 bits).** Its own docstring calls it the
DEF-4 PII remediation (`tests/test_events.py:5`). §4 shows it is **a reversible
identifier**, and the "never receive plaintext PII" claim is true of the *encoding* and
vacuous as to the *information*.

**This is the single largest mis-design risk on the slate.** Any option phrased as
"emit a derived/hashed office token" will be pattern-matched to this **live, blessed-looking,
already-shipped precedent** and reproduced. The mission brief anticipated the trap; the
trap is not hypothetical — **it is already in the tree.**

### F-4 — ★★ A written in-code spec **PERMITS** what C-15 **REJECTED**

`services/email-booking-intake/src/email_booking_intake/ad_lead_gate/observe.py:33-37`,
verbatim:

> ```
> PII FENCE (SPEC §6.1, and ``contente_booking_client``'s existing constraint):
> ``payload.phone``, ``payload.email``, any person name and any BasicAuth / bearer
> value MUST NOT be logged. ``guid`` is redacted to its 8-hex prefix via the
> service's existing ``redact_uuid``. ``office_phone`` is a BUSINESS phone and is
> permitted. ``lead_id`` is an opaque row id, not PII.
> ```

Corroborated at `tests/fixtures/ad_lead_gate/C15-live-row-redacted.json:20`:
*"office_phone is a BUSINESS phone and is permitted verbatim by the SPEC 6.1 PII fence."*

**SPEC §6.1 permits `office_phone` in logs. C-15 rejects it.** They are in direct conflict.
C-15 is the operator's ratified word and is later; **C-15 governs.** But the *codebase is
built to SPEC §6.1* and will keep drifting toward it — every new log site written by an
engineer reading that fence will add the phone, correctly, per the spec in front of them.

**A ruling that does not reach the in-code spec does not bind the code.**

### §3.1 The engineering position, stated fairly before it is set aside

SPEC §6.1's distinction is not stupid: a clinic's published main line is not personal
data in the ordinary sense, and it separates *patient* `payload.phone` (protected) from
*business* `office_phone` (permitted). Two things nevertheless answer it:

1. **C-15 rejected it.** Applied, not reopened.
2. **`office_phone` is not merely a contact — it is the account model's PRIMARY KEY**, at
   grain `(office_phone, vertical, pipeline_type)` (RATIFICATION §3:44). Emitting a primary
   key into logs does not leak a phone number; **it turns the log store into a de-facto
   copy of the customer account index, joinable by anyone with log read.** That is a
   different and larger claim than "is a business phone PII", and it is the one that
   makes the ledger's drop (§2) the correct instinct.

### §3.2 Why nothing catches any of this — three gates, all open, each zero taken with a control

| # | gate that would catch it | positive control (FIRED) | assertion |
|---|---|---|---|
| G-a | `autom8y-log` auto-redaction | `processors.py:139-157` — `DEFAULT_SENSITIVE_FIELDS` enumerated in full: `authorization, token, access_token, refresh_token, pat, password, secret, api_key, apikey, cookie, set_cookie, x_api_key, x_auth_token, credentials, private_key` (**15 members, all present and visible**) | **no `phone`, no `office_phone`, no PII field of any kind.** It is a *secrets* filter, not a PII filter. Confirms `parser.py:126` verbatim: *"autom8y-log does not redact arbitrary fields."* |
| G-b | service-level extension of that set | EBI **does** configure the logger: `handler.py:27` imports `configure_logging`, `handler.py:52` calls it; `get_logger` appears **88×** across EBI src (corpus live) | `handler.py:52` is **`configure_logging()` — no arguments.** Zero `additional_fields` / sensitive-field extensions anywhere in `services/email-booking-intake/**` (7 grep hits, **all in `tests/`**, all unrelated HTML-body assertions). EBI runs the 15 credential names verbatim. |
| G-c | **SRE-001** — the named semgrep gate for raw PII → `log.*` | `.semgrep.yml` exists and parses: **1 rule id present and named** — `autom8y.no-logger-positional-args` (`:11`). `.semgrep-security.yml` exists, 35 lines, `grep -c "id"` → **2** (control fires) | `.semgrep.yml` holds **one rule, and it is a positional-args lint.** `.semgrep-security.yml` declares **`rules: []`** and is self-described *"TRIAL (non-blocking) ... These rules are NOT blocking CI."* **Neither file contains any `pii` / `redact` / `phone` token. SRE-001 is named in four docstrings and is NOT IMPLEMENTED.** |

Fourth, and the reason a phone redactor was never reached for: `utils/redact.py` defines
**seven** helpers — `redact_email`, `redact_gmail`, `redact_uuid`, `redact_uuid_mailbox`,
`redact_guid`, `redact_url`, `sha256_token` (positive control: all seven definitions
visible). **`grep -i phone` over that file returns nothing. There is no phone redactor in
the canonical redaction substrate.** The zero is taken on a dimension that demonstrably
varies — email, UUID, URL and token helpers *are* present; phone is not.

> **Bounded by PR-6.** `origin/main` is *not established* to describe what production runs
> (production runs hand-deployed `salkin-safe-routing-20260905-90e0aa5a4937`, no commit or
> branch). **F-1..F-4 are findings about the source of record at `e292b616`.** Their
> production status is **UV-P-P1** (§10).

---

## §4 THE REVERSIBILITY RULE — why "hashed phone" is not a control

A hash is a control **only when the preimage space is large enough that enumeration is
infeasible.** `office_phone` fails that test three times over, and the third failure is
fatal on its own.

**(i) The space is small.** NANP: NPA ∈ {2-9}{0-9}{0-9} ≤ 800; NXX ≤ 800; line ∈ 10⁴.
Upper bound **≤ 6.4 × 10⁹ ≈ 2³²·⁶**. Formatting variants multiply by a small constant.
Enumerating 2³³ SHA-256 candidates is a commodity-GPU job measured in seconds.
*[Engineering estimate — I did not benchmark. **PLATFORM-HEURISTIC**. It is the weakest of
the three arguments and the ruling does not rest on it.]*

**(ii) The identifiers are PUBLISHED.** A chiropractic clinic's main line is on the
clinic's own website. **The adversary does not brute-force 6.4 × 10⁹ — they scrape a
directory and compute N hashes**, where N is the office population: **42** on the
allowlist (DIAGNOSIS §0.1), **144** rows (frame §4.3). *A few hundred hashes.* This is a
**hand-calculator attack**. It needs no GPU, no rainbow table, and no assumption about
hash rates. **[STRONG — it follows from the public availability of business phone numbers
and requires no unverified premise.]**

**(iii) The anonymity set is 1.** Truncation to 8 hex gives a 2³² output space. Over an
office population N ≈ 10²–10³, expected collisions ≈ N²/2³³ ≈ **10⁻⁴**. So
`office_phone_hash` is, with probability ≈ 0.9999, a **unique, stable, permanent office
identifier** — while providing an anonymity set of **one**. Truncation removes no
reversibility (you enumerate and compare 8 hex chars just as easily) and confers no
anonymity. **It is a rename, not a redaction.**

### ★ THE STRUCTURAL THEOREM — the governing rule for the whole option slate

> **A deterministic function of a low-entropy, publicly-enumerable identifier cannot
> simultaneously be (a) a stable join key and (b) non-reversible.**
>
> Determinism is exactly what makes it joinable. Determinism is exactly what makes it
> enumerable. They are the same property. You cannot keep one and lose the other.
>
> There are **only two escapes**, and every lawful derived-token design is one of them:
>
> - **Move the secret out of the input and into the FUNCTION** — a keyed PRF (HMAC) whose
>   key lives outside the trust boundary of everyone who can read the output. The control
>   is then **entirely key custody**. It is not cryptographic hardness; the hardness is
>   *zero* the instant the key is co-resident or leaks — **retroactively, totally, for
>   every record ever written.**
> - **Abandon derivation entirely** — a randomly-minted surrogate carrying **zero mutual
>   information** with the phone. Non-reversible *by construction*, information-
>   theoretically, with no key to protect and no retroactive-break mode.
>
> **Salting does not rescue the middle ground.** A per-deployment-constant salt readable
> by log readers is a keyed PRF with a co-resident key (escape 1, failed). A per-record
> random salt destroys determinism and therefore destroys the join (not a join key at all).

---

## §5 THE OPTION SPACE, RULED

Options are keyed by **MECHANISM, not by number**, so this limb maps onto the architect's
slate regardless of its numbering. Each is ruled on all five mission questions.

| id | mechanism | Q1 reintroduces phone / reversible derivative? | Q3 needs O-4? | Q4 survives C-16? | **VERDICT** |
|---|---|---|---|---|---|
| **P-1** | raw `office_phone` on the log plane | **YES — the rejected act itself** | — | — | **REFUSED** |
| **P-2** | truncation / prefix / last-4 of the phone | **YES — directly readable** | — | — | **REFUSED** |
| **P-3** | unsalted/unkeyed digest (**= extant `office_phone_hash`**) | **YES — reversible; anonymity set 1 (§4)** | — | no | **REFUSED** |
| **P-4** | keyed PRF, key co-resident with log readers | **YES — key co-residency (§4 escape 1, failed)** | — | no | **REFUSED** |
| **P-5** | keyed PRF, key in disjoint custody + rotation | not by a log reader — **but it remains a derivative**, retroactively reversible on key compromise | **YES** | **poorly** | **NOT CLEARED — SURFACED TO O-4** |
| **P-6** | **read-time resolution in a reader; plane unchanged** (frame M-2, 2nd horn) | **NO — nothing new is emitted** | **NO** | **best** | **★ CLEARED** |
| ~~**P-6′**~~ | ~~P-6 + REMOVE `office_phone` from the five extant emissions~~ | no — a net SUBTRACTION | — | — | **⚠ CLEARANCE WITHDRAWN — see §0.5 A1.4.** The removal touches `services/**` ⇒ DEPLOY-CLASS A ⇒ R-35-frozen ⇒ **BUNDLING (C-1 REFUSAL)**. **PII-lawful as a posture; OUT OF THIS ENVELOPE.** Surfaced to O-4(b) + `change-warden`; **not cleared, not scheduled, not cured.** |
| **P-7** | **randomly-MINTED opaque office token at onboarding, zero derivation** | **NO — zero mutual information** | **NO** | good, with conditions | **★ CLEARED, subject to §6 construction** |
| **P-8** | add a redacted GUID-prefix field to currently office-blind lines | no (no phone involved) | n/a | n/a | **PII-LAWFUL but SCOPE-REFUSED — §8** |

### Per-option rulings

**P-1 · RAW PHONE — REFUSED.** The act C-15 rejected. **Q2 cost↔integrity:** spends the
control described at §2 and buys a join that F-1 shows already exists off-plane; it
purchases nothing that P-6 does not purchase for free. **Note it is the status quo ante at
five sites (F-2)** — which makes it a *remediation* subject, never a *forward option*.

**P-2 · TRUNCATION — REFUSED.** Reversible on its face. Last-4 is worse than it sounds:
over a population sharing few NPA-NXX pairs, last-4 is near-unique, so it is a
full-strength office identifier wearing a partial-redaction costume.

**P-3 · UNSALTED DIGEST — REFUSED, and flagged as the live trap.** §4 (ii)+(iii) are
dispositive: reversible by a scraped directory, anonymity set 1. **Q2:** spends the entire
control and buys *the appearance* of having kept it — the worst trade on the board,
because it also **manufactures false assurance** (`events.py:25-26` already asserts
"never receive plaintext PII" on the strength of it). **Q4 C-16:** fails — see P-5.
**This is compliance theatre in the precise sense: a control that passes inspection and
mitigates no risk.**

**P-4 · CO-RESIDENT KEY — REFUSED.** If the key is readable by anyone who can read the
logs, the log reader holds both halves. Equivalent to P-3 with extra steps.

**P-5 · KEYED PRF, DISJOINT KEY CUSTODY — NOT CLEARED; SURFACED TO O-4.**
This is the strongest *derived* construction and it is genuinely defensible engineering.
I do not clear it, for three reasons, and per the hard gate I surface rather than trade:

- It **is** a derivative of `office_phone`. Its non-reversibility is **not a property of
  the construction** but of an operational fact (where the key lives) that no code review
  can pin and no test can assert. **The control is key custody, and it must be named that
  way, never as "we hash it."**
- **Compromise is retroactive and total.** One key leak de-pseudonymises **every record
  ever emitted**, back to the beginning of retention. The minted alternative (P-7) has no
  such mode. This asymmetry is the whole reason to prefer minting.
- **Q4 — it fails C-16 structurally.** A derived token welds the log plane to the
  *current* account model's primary key. Rotate the key → historical records become
  unjoinable or require a key-epoch field on every record. Re-source office identity from
  the DB successor (the explicit C-16 future) → the derivation input changes → the token
  changes → **history silently breaks.** *A PII posture that only holds for the current
  adapter is not a posture* — and a derived token is exactly that.

  **Q2:** spends key-custody discipline forever, in perpetuity, on every rotation, to buy
  a join that P-6 already has for nothing.

**P-6 · READ-TIME RESOLUTION — ★ CLEARED, unconditionally, on the PII question.**
The plane keeps emitting what it emits. A reader — outside the log plane — takes the
already-emitted 8-hex GUID prefix and resolves the office through the join F-1 proves is
live. **Q1: nothing whatever is added to the log plane, so the rejected act cannot occur.**
**Q3: it needs no O-4 — it routes around the ruling entirely, lawfully.** That is the
mission's stated best available outcome, and it is available.
**Q4: it is the C-16-strongest option by construction** — the emitted record carries only
the GUID, so swapping Asana → DB-status-read changes the *adapter behind the reader* and
touches neither the log plane nor a single historical record. **Records emitted today
remain resolvable under tomorrow's source of truth**, which is precisely the property
C-16 demands and the property P-5 destroys.
**Q2:** it spends a reader (frame M-4 already suspects a READER is the missing primitive)
and buys the naming with **zero** PII expenditure. **It is the only option that is
retroactively effective** — already-written records inside their retention window carry
the GUID prefix and become nameable the day the reader exists. Every emit-time option
works only forward.

> **⚠ P-6-naive is REFUSED.** A reader that satisfies WS-JOIN *by reading the raw
> `office_phone` already present at the five F-2 sites* is **NOT cleared.** It would make
> the product **structurally dependent on a control violation**, converting an unnoticed
> leak into a load-bearing dependency that can no longer be remediated without breaking
> the bar. **The reader must resolve from the GUID, never from the leaked phone field.**
> This is the sharpest single instruction in this limb.

**P-6′ · P-6 PLUS REMOVING THE PHONE FROM THE FIVE EXTANT EMISSIONS — ⚠ CLEARANCE
WITHDRAWN (§0.5 A1.4). The removal is R-35-frozen `services/**` work; clearing it here
would be BUNDLING. Read the rest of this paragraph as a SURFACED FINDING routed to
O-4(b) + `change-warden` — NOT as a path WS-JOIN may take.** *(Retained rather than
deleted, so the correction is auditable.)* The observation that follows survives the
withdrawal and is evidence for P-6's feasibility:** The finding that makes this available: at `:259-263` the
`office_resolved` event **already carries `office_name` (the plaintext business name)
beside the redacted GUID.** The log plane *already names the office.* So the naming
capability WS-JOIN needs is obtainable by **subtraction**: drop `office_phone` from the
five sites, keep `office_name` + `redact_uuid(guid)`.
- **Q1: a net reduction** in identifier exposure. It moves *toward* C-15, not away.
- A **business name is not the rejected identifier** and is not the account primary key;
  it is the very thing the bar asks for (*"attributed to them by name"*).
- **Q2:** the rare option that spends nothing and buys both the naming *and* a
  remediation. **The lawful path here is a removal, not an addition** — which is why the
  slate must not be framed as "what may we add."
- **Q3:** proceeds without O-4; O-4 remains owed for the *scope and clock* of the removal
  (§7), not as a precondition.
- ⚠ **Two named hazards for the architect, not resolved here:** (a) `resolve_office.py:238`
  and `:247` set **`ctx.office_name = "Unknown"`** on the partial paths while a valid
  GUID/phone is in hand — **"Unknown" is blank-equivalent, and the bar says *never
  blank***; (b) `office_resolved` fires only at/after the resolve stage, so mail failing
  *upstream* of it is not named by this path — that boundary is the two-sidedness
  question and it belongs to the architect.

**P-7 · RANDOMLY-MINTED OPAQUE TOKEN — ★ CLEARED, subject to §6.** See §6; the word
**"derived"** in the option's usual phrasing is the defect.

**P-8 · REDACTED GUID-PREFIX ON OFFICE-BLIND LINES — PII-LAWFUL, SCOPE-REFUSED.** See §8.

---

## §6 ★ SHARPEST SCRUTINY — the "derived non-reversible office token minted at onboarding"

The charge is right that this is the option most likely to be mis-designed into a
reversible identifier. **The defect is in the word `DERIVED`, and F-3 proves the failure
is not hypothetical — the codebase already contains a "derived non-reversible token" that
is trivially reversible and is documented as a PII remediation.**

### 6.1 The ruling

> **DERIVED and NON-REVERSIBLE are, for this input, mutually exclusive** — §4's structural
> theorem. A token *derived* from `office_phone` is non-reversible only relative to an
> operational secret, never by construction. **The option must be re-specified as MINTED,
> not DERIVED.** So re-specified, it can be made genuinely non-reversible within this
> envelope. Left as "derived", **it cannot**, and it will be built as `_hash_prefix` again.

### 6.2 The construction that makes it genuinely non-reversible

Five conditions. **All five are load-bearing; dropping any one collapses it to P-3 or P-5.**

1. **MINTING — no functional dependence on `office_phone`, at all.**
   `token = base32(CSPRNG(160 bits))`. Not a hash of the phone. Not a hash of the phone
   plus salt. **The phone is not an input to the mint.** Mutual information with
   `office_phone` is **zero**, so no key compromise, no directory, and no future
   cryptanalysis can reverse it. This is the condition that buys everything else; the
   remaining four only protect the mapping.
2. **MINTING LOCUS — at onboarding, once, by the account-lifecycle owner.**
   The mint belongs where the account is created. **This converges with C-17**, which puts
   a hook on the lifecycle transition — the same transition is the natural mint point, and
   an account that activates without a token is exactly the "activated without an
   end-to-end proof" C-17 forbids. *Convergence noted; C-17's hook design is WS-SMOKE's,
   not mine.*
3. **MAPPING CUSTODY — `token ↔ office` lives OFF the log plane, read-gated separately.**
   With minting, there is **no salt and no key to protect** — the entire secret is the
   mapping table. It must not be readable by log-read alone, or the token is a plaintext
   office identifier for anyone holding logs. **State it as an access-control requirement,
   because that is exactly and only what it is.**
4. **ROTATION — the token is STABLE; rotation is re-mint + a dated mapping generation.**
   Rotating a *minted* token is not a security operation (nothing is derived, so nothing
   leaks by staleness) — it is a **re-identification event**. Historical records keep the
   old token, so the mapping must be **generation-stamped**, never overwritten, or history
   becomes unreadable. **Rotation here protects the mapping's blast radius, not the
   token's secrecy.** Contrast P-5, where key rotation *is* a security operation and
   *does* break history.
5. **NEGATIVE INVARIANT — pinned by a test that would fail if violated.**
   `office_phone` must not be an input to the mint and must not appear in any emitted
   record. Given §3.2 (G-a/G-b/G-c all open, SRE-001 not implemented, no phone redactor),
   **an unpinned invariant here is an unenforced one.** The pin already has a working
   exemplar to copy: `tests/test_ebi_witness_ledger.py:434`.

### 6.3 What P-7 costs, honestly (Q2)

It spends a mint, a mapping store, its access control, a generation-stamped rotation
story, and a durable new identifier in the account model — **materially more than P-6/P-6′,
which spend a reader and nothing else.** It buys one thing P-6 does not: an office handle
that is **independent of the GUID**, and therefore survives a future where the routing
GUID changes or disappears. **Whether that independence is worth the cost is the
architect's call, not mine.** My ruling is only that P-7 *can* be made lawful, and *only*
in the minted form.

### 6.4 Q4 — C-16 extensibility

**Good, with one condition.** A minted token is an opaque surrogate with its own lifecycle,
independent of whether office identity is sourced from Asana today or the DB tomorrow —
so it does not weld (unlike P-5). **The condition:** the mint must be owned by the
account-lifecycle boundary, **not** by the Asana adapter. A token minted *by the Asana
adapter* welds the account model to Asana and reproduces the exact C-16 failure the seam
exists to prevent (frame §4.3).

---

## §7 ★ O-4 IS NOT THE FORK THE FRAME DESCRIBES — RESTATED

Frame §9 records **O-4** as *"The PII ruling WS-JOIN transits — trades the office-blindness
that IS the integrity control; consequence if unspoken: WS-JOIN either stalls or quietly
re-introduces the dropped identifier."*

**Under F-1..F-4 that framing is superseded in two ways, one relieving and one worsening.**

**Relieving — O-4 IS NO LONGER A BLOCKER ON WS-JOIN.** O-4 was framed as permission
WS-JOIN needs before it can proceed. **P-6 and P-6′ clear unconditionally and need no
permission**, because they add nothing to the log plane. **WS-JOIN can proceed today
without O-4 being spoken.** The frame's stated consequence-if-unspoken — *"WS-JOIN either
stalls or quietly re-introduces the dropped identifier"* — **is now a false dilemma: there
is a third door, and it is open.** Per the mission, routing around a ruling lawfully is
the best outcome available, and **it is achieved.**

**Worsening — O-4 is still owed, and it is a bigger question than permission.** It is
three questions, none of which WS-JOIN can answer and none of which WS-JOIN created:

- **O-4(a) — AUTHORITY CONFLICT.** `observe.py:33-37` **SPEC §6.1 permits** `office_phone`
  in logs; **C-15 rejects** it. C-15 governs, but the *in-code spec is what engineers
  read*. Does SPEC §6.1 get amended to match C-15 — and who owns that edit? **Until it is,
  every future log site is written against a fence that contradicts the ratified ruling,**
  and the drift is silent by construction.
- **O-4(b) — PRE-EXISTING STATE, and whose clock.** Five raw-phone emission sites (F-2),
  one reversible-hash site presented as a remediation (F-3), and three open gates (§3.2:
  no PII field in `DEFAULT_SENSITIVE_FIELDS`; `configure_logging()` unargumented; SRE-001
  named-but-not-implemented) exist **today**, at `e292b616`, **and predate this
  initiative.** Is remediation owed, at what severity, and on whose clock? **It is
  emphatically NOT WS-JOIN's clock** — WS-JOIN did not create it and must not be made to
  carry it, or the initiative absorbs an unbounded remediation it was not scoped for.
- **O-4(c) — FORWARD PERMISSION.** Is WS-JOIN restricted to P-6/P-6′/P-7, or may it use a
  keyed derivative (P-5)? **This limb does not clear P-5 and surfaces it here.** Given
  P-6′ is available at lower cost and higher C-16 fitness, my read is that O-4(c) may
  never need to be reached — **but it is the operator's to reach or not.**

**Consequence if O-4 stays unspoken, restated:** WS-JOIN does **not** stall (P-6′ is open)
— but SPEC §6.1 keeps licensing new phone-in-log sites, and the F-2/F-3 state persists
unowned and unmeasured.

---

## §8 SCOPE FENCE — WHAT I DID NOT ANNEX

- **The 1,252 office-blind residual is OUT (frame §10 row 6).** It is cited exactly once
  in this limb, at §4 (ii), as the *population size* that makes a phone hash enumerable —
  not as a defect and not as a target. **DIAGNOSIS §6's redacted-prefix-only idea (my P-8)
  is PII-lawful on its face — and I decline to clear it into this envelope, because
  clearing it is the annexation frame §10 row 6 forbids.** Adjacency is not inclusion.
  It goes to the warden + security seat with O-4(b), unchanged.
- **C-15 is applied, never reopened.** §3.1 states the contrary engineering position only
  to set it aside under C-15.
- **No mechanism selected, no sprint ordered, no sizing given.** Frame §9 M-2 is the
  architect's and Pythia's.
- **No code changed. Nothing merged, deployed, or applied.** C-INERT.

---

## §9 CONTROL SPECIFICATION — envelope

### §9.0 Schema conformance note

The security-rite handoff schemas (`control-spec.schema.yaml`,
`threat-model.schema.yaml`) were **not located in this satellite repo** (see UV-P-S1). The
envelope below therefore conforms to the schema **as specified in this seat's contract**,
not to a file I read. **`frameworks: []` is deliberate and is not an omission:** no
external framework (SOC 2 / HIPAA / PCI-DSS / GDPR) has been established as in-scope for
this system by any ratified artifact I read, and **asserting one would be exactly the
compliance theatre this seat exists to refuse.** The governing authorities are **C-15
(operator, ratified)** and **SPEC §6.1 (in-code, conflicting — O-4(a))**.

`risk_reference` values point at the **frame's** named risks and premises rather than a
`threat-model.schema.yaml` that does not exist here. **No control below is orphaned** —
the compliance-without-risk-diagnosis-is-theater rule is honoured in substance.

### §9.1 Controls

| id | requirement | status | risk_reference | evidence_path |
|---|---|---|---|---|
| **CS-001.1** | No WS-JOIN path may place `office_phone`, or any deterministic derivative of it, on the log plane. | **Gap** — violated today at 5 sites | C-15; frame §4.1; DIAGNOSIS §12 PR-8 | `resolve_office.py:204,214,233,248,262` |
| **CS-001.2** | A digest of `office_phone` is **not** a redaction: anonymity set ≈ 1 over the real population (§4). | **Gap** — `office_phone_hash` live | §4 (ii)(iii); F-3 | `events.py:51-53,140`; claim at `events.py:25-26` |
| **CS-001.3** | The naming reader must resolve from the **GUID**, never from a leaked `office_phone` field. | **Planned** — binds WS-JOIN | F-2; P-6-naive refusal §5 | this limb §5 |
| **CS-001.4** | A minted office token must take `office_phone` as **no** input, and the invariant must be test-pinned. | **Planned** — applies only if P-7 chosen | §6.2 cond. 1 & 5 | exemplar `tests/test_ebi_witness_ledger.py:434` |
| **CS-001.5** | The in-code PII fence must not contradict the ratified ruling. | **Gap** — SPEC §6.1 vs C-15 | F-4; O-4(a) | `ad_lead_gate/observe.py:33-37` |
| **CS-001.6** | SRE-001 (raw PII → `log.*`) must be operative if it is to be relied upon. | **Gap** — named, not implemented | §3.2 G-c | `.semgrep.yml:11`; `.semgrep-security.yml` (`rules: []`) |
| **CS-001.7** | The office name emitted for a resolved office must never be blank-equivalent. | **Gap** — `"Unknown"` on 2 paths | realization predicate (*"never blank"*) | `resolve_office.py:238,247` |

**Severity:** deliberately **not** scored. The seat's severity taxonomy
(`rites/security/mena/severity-taxonomy.lego.md`) was **not located in this repo**
(UV-P-S1); per that skill's own discipline I **cite it rather than restate it**, and since
I cannot cite a file I did not read, **I assert no Bug Bar / CVSS / EPSS / KEV / SSVC
rating.** Severity for CS-001.1/.2/.5/.6 is **owed to O-4(b)** with the taxonomy in hand.

---

## §10 UV-P LEDGER

```
[UV-P-P1: F-1..F-4 describe origin/main @ e292b616; whether the five raw-phone emission
 sites and the office_phone_hash site are present in what PRODUCTION runs is NOT
 established | METHOD: deferred — requires reading the hand-deployed artifact
 salkin-safe-routing-20260905-90e0aa5a4937 | REASON: DIAGNOSIS §12 PR-6 records that no
 commit or branch exists for the deployed revision; every code-based claim in this limb is
 bounded by that, and the bound is stated at §3.2]

[UV-P-S1 — UPGRADED, zero now TAKEN: control-spec.schema.yaml, threat-model.schema.yaml,
 severity-taxonomy.lego.md and coverage-matrix.lego.md are ABSENT from the session repo |
 METHOD: three probes, each with a FIRING positive control — (i) repo-wide `find` returned
 nothing while the SAME find form located
 .ledge/decisions/RATIFICATION-client-outcome-decision-space-2026-09-08.md (control fired);
 (ii) `git ls-files` matched none while the same pipeline counted 32 tracked .yaml files
 (control fired); (iii) `ls .claude/skills` matched none while listing 106 entries (control
 fired) | REASON: the first attempt TIMED OUT and I refused to report its silence as a zero
 (fence 1); re-taken to completion. The zero is now taken and the claim is ABSENCE, not
 absence-of-location. CONSEQUENCE UNCHANGED: §9.0's envelope conforms to the contract, not
 to a file I read, and NO severity rating (Bug Bar / CVSS / EPSS / KEV / SSVC) is asserted
 anywhere in this limb — severity for CS-001.1/.2/.5/.6 is owed to O-4(b) with the taxonomy
 in hand.]

[UV-P-S2: whether `guid` on autom8y-data's LeadCrudRecord / EmployeeCrudRecord
 (activation_read_client.py:104,:117) is the OFFICE guid or a lead/employee guid | METHOD:
 deferred — the cited authority is autom8y-data@3288bd74, a repo not in my read scope |
 REASON: the field is present on the wire but NEVER READ in that module (grep "guid" over
 activation_read_client.py returns exactly 2 hits, both docstring wire-shapes). F-1 does
 NOT rest on this — it rests on resolve_office.py:1 and :171, which are unambiguous.]

[UV-P-S3: whether the "C15" in tests/fixtures/ad_lead_gate/C15-live-row-redacted.json is
 the same C-15 as the operator ruling | METHOD: deferred | REASON: almost certainly an
 unrelated in-service contract numbering; I make NO identity claim, and F-4 does not
 depend on the fixture — it rests on observe.py:33-37, which the fixture merely echoes.]
```

---

## §11 ATTESTATION

**Everything below was read by this seat, at the pinned ref, with the command shown.**
No quotation in this limb is inherited from the charge.

| # | artifact (absolute / ref-pinned) | how read | what it established |
|---|---|---|---|
| 1 | `autom8y@e292b616:scripts/ebi_witness_ledger.py` `:20-22`, `:393-395` | `git show` → 942 lines; `grep -n office_phone` → 2 hits, both comments | §2 — the drop, verbatim, own-hands |
| 2 | `…:services/email-booking-intake/src/email_booking_intake/pipeline/stages/resolve_office.py` `:1,:171,:202-206,:212-216,:229,:231-235,:238,:247,:248,:259-263,:270` | `git show` → 273 lines, read `:190-273` in full | **F-1, F-2**, CS-001.7 |
| 3 | `…/events.py` `:8-26,:51-53,:139-140` | `git show` → read verbatim | **F-3** — the unsalted truncated SHA-256 |
| 4 | `…/ad_lead_gate/observe.py` `:33-37` | `git show` → `sed -n '28,55p'` | **F-4** — SPEC §6.1 permits |
| 5 | `…/parser.py` `:121-132` | `git show` → `sed -n '120,135p'` | *"autom8y-log does not redact arbitrary fields"*, verbatim |
| 6 | `…/pipeline/stages/classify.py` `:88-95` | `git show` → `sed -n '88,97p'` | `mailbox=redact_uuid(ctx.to)` — the redacted-prefix precedent |
| 7 | `autom8y@e292b616:sdks/python/autom8y-log/src/autom8y_log/processors.py` `:134-222` | `git show` → read the frozenset in full | **G-a** — 15 credential names, no PII field |
| 8 | `…/autom8y-log/src/autom8y_log/config.py` `:78-81` | grep | `redact_sensitive_fields` default-on, but over the set in #7 |
| 9 | `…/email_booking_intake/handler.py` `:27,:52` | grep | **G-b** — `configure_logging()`, no arguments |
| 10 | `autom8y@e292b616:.semgrep.yml`, `.semgrep-security.yml` | `git show` → 1 rule id / 35 lines, `rules: []` | **G-c** — SRE-001 not implemented |
| 11 | `…/utils/redact.py` | `git show` → 7 defs visible; `grep -i phone` → nothing | no phone redactor exists |
| 12 | `…/activation_read_client.py` `:104,:117` | `git show` → 1431 lines, read `:95-130` | wire shapes; **UV-P-S2** |
| 13 | `…/tests/test_ebi_witness_ledger.py:434`, `tests/test_events.py:5`, `tests/fixtures/ad_lead_gate/C15-live-row-redacted.json:20` | grep | the drop is test-pinned; DEF-4; the SPEC §6.1 echo |
| 14 | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/DIAGNOSIS-verified-not-enabled-2026-09-08.md` §6, §12 | `sed -n` | cost↔integrity coupling; PR-8 REFUTED; PR-6 bound |
| 15 | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/decisions/RATIFICATION-client-outcome-decision-space-2026-09-08.md` `:24-25` | grep | C-15, C-16 verbatim |
| 16 | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/frames/name-the-client.md` §3.E, §4.1, §4.3, §5 WS-JOIN, §9, §10 | `sed -n` | envelope, O-4, M-2, scope fence |
| 17 | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.github/workflows/test.yml` `:20-36` | `sed -n`, live | **O-3 fence** — §11.2 |

### §11.1 Positive controls — every zero in this limb, and its firing control

| zero asserted | control that FIRED (varies the asserted dimension) | verdict |
|---|---|---|
| no PII field in `DEFAULT_SENSITIVE_FIELDS` | all **15** members enumerated and visible — `token`, `password`, `secret`, … ARE present | **TAKEN** — membership varies; `phone` absent |
| EBI adds no sensitive fields | EBI **does** configure logging: `get_logger` **88×**, `configure_logging` at `handler.py:52` | **TAKEN** |
| no PII rule in `.semgrep.yml` | **1 rule id present and named**: `autom8y.no-logger-positional-args` | **TAKEN** |
| no PII rule in `.semgrep-security.yml` | first control (`grep -n "  - id:"`) **DIED — no output**; **re-taken**: file shown, 35 lines, `grep -c "id"` → **2** | **TAKEN on re-run** (fence 1 fired on me) |
| no phone redactor in `redact.py` | **7** helper definitions visible (email / uuid / url / token) | **TAKEN** — helper-class dimension varies |
| `guid` unread in `activation_read_client.py` | file shown, **1431 lines**; `grep guid` → 2 docstring hits | **TAKEN** → UV-P-S2 |
| `office_phone` absent from `ebi_witness_ledger.py` code | file shown, **942 lines**; 2 hits, both comments | **TAKEN**; matches §2 |

### §11.2 O-3 per-PR fence — DISCHARGED, deny-list READ LIVE

**Positive control FIRED:** `.github/workflows/test.yml` exists (30720 bytes); `paths-ignore`
present at **`:29`**, under the `push:` trigger (`pull_request:` begins at `:36`); **6
entries visible**.

```
paths-ignore:
  - '.ledge/**'      ← my only changed path is covered by entry 1
  - '.sos/**'
  - '.claude/**'
  - '.gemini/**'
  - '.knossos/**'
  - '.know/**.md'
```

- **Changed paths this sprint: exactly one** —
  `.ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.PII-LIMB.md`.
- **Asserted against the live deny-list: MATCHES `.ledge/**`. Does not trigger the push
  workflow. C-INERT confirmed by reading, not by assumption.**
- **Two-sided control (the word's own hazard, and it is real here):** `.know/**.md` is
  listed but `.know/**` is not — a `.know/*.json` **would** deploy, and the file's own
  comment at `:26-28` says so deliberately (`.know/cache-freshness-ttl-manifest.yaml` is a
  runtime input). **The deny-list has genuine gaps by design.** Mine is not one of them.
- **Recorded asymmetry:** the `pull_request:` trigger at `:36` carries **no**
  `paths-ignore`. The fence covers `push` only.

---

## §12 HANDOFF

**To the architect (S-04a), for incorporation by reference:**

1. Options mapping to **P-1/P-2/P-3/P-4** are **REFUSED**; do not carry them forward as
   live candidates. **P-3 is the live trap — `_hash_prefix` at `events.py:51-53` is
   already in the tree and looks blessed.**
2. **P-5 (keyed PRF) is NOT CLEARED and is surfaced to O-4(c).** Do not treat this limb's
   silence as permission.
3. **P-6 is CLEARED unconditionally** (≡ your **Option C**) and is the C-16-strongest.
   **⚠ P-6′'s clearance is WITHDRAWN (§0.5 A1.4)** — the removal half is R-35-frozen
   `services/**` work and clearing it would be BUNDLING. What survives: **`office_name` is
   already on the log plane at `resolve_office.py:263`**, which is *evidence for* Option C's
   feasibility and **not** a licence to edit that file. **Binding rider on C: the `NamePort`
   must resolve from the GUID, never from the leaked `office_phone` field (§0.5 A1.5).**
4. **P-6-naive is REFUSED**: a reader must resolve from the **GUID**, never from the raw
   `office_phone` present at the five F-2 sites.
5. **P-7 is CLEARED only in its MINTED form**, under all five §6.2 conditions. **Strike
   the word "derived."**
6. **WS-JOIN is not blocked on O-4.** O-4 is owed as **authority-conflict + remediation**
   (§7), not as permission-to-proceed.

**To the penetration-tester (downstream):** CS-001.1/.2/.5/.6/.7 are asserted **Gap** at
`e292b616` and are falsifiable at that ref. **CS-001.2 is the one to attack first** — the
claim under test is `events.py:25-26` (*"never receive plaintext PII"*) against the
construction at `:51-53`. The two-sided control is a directory of published clinic phone
numbers; the predicted result is de-pseudonymisation of `office_phone_hash` in **N hashes,
N ≈ the office population**, with no cryptanalysis. **All of it is bounded by UV-P-P1
(PR-6): production is not established to run this source.**

**Nothing here authorises a merge, deploy, or apply. Ruled; not built.**
