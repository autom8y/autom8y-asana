---
type: decision
artifact_kind: operator-slate
initiative: read-the-name
sprint: S1.6 (soak, day 1 closed)
rite: sre
station: calendar-integration-locus
created: 2026-09-16
status: recorded
supersedes: "the §3 word-list of RULING-pythia-read-the-name-grant-adjudication-2026-09-15.md, which this dates forward"
arming_state: NOT ARMED
evidence_grade: MODERATE
refs_read: autom8y-asana origin/main 19dab888 · autom8y origin/main c95c59bb
---

# SLATE — the operator's open words, dated 2026-09-16T00:45Z

**This slate decides nothing.** It carries forward pythia's §3 list with the night's measurements
folded in, marks two words discharged **by evidence rather than by assertion**, and adds five items
the evening produced. Every item is phrased to be answerable in one line. Nothing here is authority,
and no item may be treated as settled by a relay in either direction.

---

## §1 The arming gate — unchanged, and still the only thing that blocks the arm

**W-1**, verbatim from the ruling, in this seat's own room:

> *"For the 09-22 arm: the reader of S-1 pages on `autom8y-platform-alerts` is ___; the smoke-lead
> convention from then on is ___; disarm to scratch on a misfire is pre-authorised: yes/no."*

Three blanks, and all three are still open. Without them S1.7 does its scratch-topic half and ends
**REFUSED-CORRECTLY**. The re-point itself is class **(C)** in the ruling — a specific word the
standing grant does not supply.

One fact for the first blank, measured 2026-09-15: **the guid8 → clinic lookup exists and works**
(7 of 7 named offices resolve to exactly one name over 30 days), **but it requires AWS read on
`/aws/lambda/autom8-email-booking-intake`, which today means the operator.** A named reader without
that access can be paged but cannot resolve the code on the page. That is a property of the choice,
not an objection to it.

---

## §2 NEW — the arm date is no longer 2026-09-22, and the choice is yours

Soak row 1 (2026-09-15) **passes seven of eight §3 criteria and fails the `***` attribution residual**:
day max 0.1141 against a 10 % bar, `residual_share_high: true` on 4 of 24 run lines. §3 requires
*seven **consecutive** complete rows*, so on the plain reading consecutiveness breaks.

The cause is upstream and dated: a burst in the 19:00Z hour of 09-15 (110 office-bearing lines, **65
unattributable**, 40 × `WebhookValidationError` at `stage=parse`), which sits in the 3-day rolling
window until ≈ 2026-09-18T19:00Z.

Reconstructing the criterion across 30 days: **25 of 31 days would have passed, 6 breached, and the
longest actual consecutive pass run is 15 days (08-27 … 09-10).** A clean seven-row soak has happened
twice inside the last month. **The arm needs seven days without a burst, not the upstream defect
gone** — a probability over a date, not a wall.

> **The word:** *"On the residual breach — (a) wait for seven consecutive clean rows; or (b) a
> breached row annotates rather than resets, and the arm holds its date; or (c) ___."*

**CORRECTED 2026-09-16T16:15Z, AND CORRECTED AGAIN 16:40Z — the date stands after all; what was wrong
was this seat's second reading, not its first.** At 16:15Z this entry withdrew "≈ 09-25" and wrote *"the
soak is inside a multi-day run"*, on a reading that the residual's monotonic climb through day 2 (0.1136
→ 0.1390, high on 16 of 16 runs) was fed by a fresh no-body batch of 14 at 15Z. The EBI lane stopped it,
and splitting the `***` lines by `(stage, error_type)` per hour over 36 h shows they were right:

```
no-body (parse/WebhookValidationError), *** lines per hour:
  09-15 19Z  28    20Z  8    21Z  4
  09-16 00Z   4    03Z  4    06Z  4    09Z  4    12Z  4    15Z  4        total 64
```

**One batch, on SendGrid's redelivery schedule — deterministic failure, new trace id each pass — and
nothing new has entered the class since 19Z on 09-15.** The "14 at 15Z" was 4 retries + 2
`OfficeResolutionError` + their 8 paired fault/decline lines, an hourly `***` count mistaken for a
fresh arrival. The day-2 climb is **window arithmetic**: the 19Z burst and its flat tail accumulate
inside the 3-day window while the quieter hours before it age out. **The no-body batch ages out ≈
2026-09-18T19:00Z as first dated**, and option (a)'s earliest close remains **≈ 09-25**, *if no new batch
lands* — a probability over a date, exactly as §2 already says. The small steady second feeder is
`OfficeResolutionError` (15 `***` lines in 36 h), not anything new.

One claim from the correcting lane does **not** hold on this plane and is recorded so it is not carried
by inheritance: that `FieldExtractionError` feeds the residual. It feeds **zero** `***` lines in 36 h —
those failures occur after office resolution and carry a guid, so they are attributed. Their split was of
*all* stage exceptions (190 in 36 h); this seat's residual is of *unattributable* lines (64 + 15). Two
instruments, two populations, and each of us read one as the other for an hour. Same family as every
other error tonight.
---

## §3 NEW — the silent-loss class, which outranks everything else on this page

Measured on the EBI plane and **reproduced independently here, digit for digit**: the
`WebhookValidationError` class (the webhook carries neither an html nor a text body) rejected **568
deliveries across 17 of the last 30 days**. On 120 traces sampled by the EBI lane, **every one
authenticated and reached `pipeline_completed`, and not one produced a booking, a terminal decline,
or a park.**

Mail that arrives, authenticates, and vanishes leaving no record. Each delivery carries a fresh
trace id and no message id, so **568 deliveries represent an unknown, smaller number of real
emails** — the count cannot be recovered from the plane. It is the third silent-loss class found on
that service.

> **The word (EBI's lane, his to authorise):** *"Build the missing-body parse fix — yes / no / after
> ___."* It is a new build, outside the wave already approved, and the EBI seat has correctly
> declined to start it without this.

This seat's soak row is an inconvenience with a date on it. This is not.

---

## §4 Words carried forward, unchanged

| word | the question, in one line |
|---|---|
| **W-2** | *"Extend this grant to EBI `services/email-booking-intake/**` merges-on-green whose apply is image-only (pending set empty), for the S-1 follow-ups after the arm — yes / no / only ___."* |
| **W-7** | *"SEV1 SMS is sandboxed: request production access / verify a destination number / record SMS as dead."* |

W-3 and W-5 belong to the EBI locus's room and are not asked here.

---

## §5 Two words DISCHARGED by measurement, shown so they can be contradicted

**W-4 — *"unmute the SEV1 deadmen the triage proves real"* — the answer is NONE of the four.**
The read-only triage (`TRIAGE-asana-muted-sev1-deadmen-2026-09-15.md`, merged `18ec8f81`) found all
four **stale by design**: every watched series stops in the same hour, 2026-09-05T06:00Z, because a
human disabled three schedules at 06:24:56–06:25:01Z the morning after CI re-enabled them. Not one
REAL OUTAGE, not one STALE DRIFT. Unmuting any of them pages a human on a live SMS topic for a state
the fleet ruled into existence. **No word is needed to unmute nothing; the word is only needed if
this reading is wrong.**

**W-6 — *"drop the asana image pin"* — already gone, on both stacks.** Verified at
autom8y `c95c59bb` with a positive control: no non-comment `image_tag =` assignment exists in either
`terraform/services/asana/environments/production.tfvars` or the EBI one, while the same pattern
finds 10 and 32 real assignments in those files respectively — so the zero is a true absence and not
a broken pattern. **Nothing to drop.**

---

## §6 NEW — three findings that need a word but are not unmutes

| id | finding | the word |
|---|---|---|
| **S-1** | **`asana-PROV-9-offer-artifact-uncovered` has never once read provable**: 804 of 804 datapoints at 0.0 across the entire life of its producer (verified here by own hands, daily min = max = 0.0 on all ten days). The alarm also **predates its own producer by 8 days 2 hours**. Invisible today only because the sweep is paused; it will page the instant anyone restarts it without understanding this. | *"Route the offer-axis provability finding to ___ / park it."* |
| **S-2** | **The `autom8y-asana-story-warm-dead` mute is undeclared in its own IaC.** `actions_enabled` is absent from `terraform/services/asana/story_warm_dead_alarm.tf` while the live alarm is `ActionsEnabled=False`. Narrower than it first looks — that tree has **no wired apply pipeline** and the live resource was never imported, so the revert would come from a human re-applying by hand, not a pipeline. It routes to live SMS. | *"Declare the mute in the HCL / retire the alarm / leave it."* |
| **S-3** | **`[DO NOT MERGE]` reads like a gate and is not one.** Three commits carry the marker on `origin/main` since 2026-08-01 — `c91189b6` (#2071), `002316ca` (#2105), `5ca5642c` (#1601) — all merged through PRs, and **no workflow in `.github/` references the marker.** The uncomfortable part: `c91189b6` ignored it and was **right** — it is the commit that cured the silent-drop class. A gate whose only violations produce good outcomes is the least likely ever to be wired. | *"Wire the marker as a required check / retire it."* Wiring it changes branch protection, so it is operator-only either way. |


### §6a AMENDED 2026-09-16T02:30Z, CORRECTED 02:45Z — the prose-gate class is real, and this seat got one instance wrong

A peer lane reported a binding: *never set `vars.A8_VERSION` below `v1.4.1-patch.2`*, because 20 of the
21 a8 tags from v1.3.4 write a credential literal their cure removed. That tag measurement is theirs and
is carried as theirs.

**This seat first wrote that the floor is "named in seven workflows and enforced in none". That is
WRONG on the path that matters, and the error is this night's own law turned on its author.** I searched
for a *version comparison*, found none, and read the absence of the mechanism I expected as the absence
of enforcement. **I asked a narrower question than the one I answered, and the narrow answer was
well-formed.**

**What is actually true, re-measured after the peer's correction:**

- **Data's cure IS enforced, by a property guard rather than a version test.**
  `satellite-receiver.yml` runs `scripts/a8-data-floor-guard.sh` in its **validate** job, **with no
  `if:` — deliberately, so the step is visible in every run** ("the script decides applicability"), and
  every other job `needs: validate`. It refuses a data deploy when the manifest actually checked out at
  the pinned ref names data's `SERVICE_CLIENT_ID`. It carries its own positive control: the same parse
  must find the key in asana's block, and fails **loudly** if it does not — a parse that finds nothing
  never certifies.
- **There is no version-floor enforcement for any NON-data service**, and the two guards on the
  service-deploy path (`service-deploy-dispatch.yml`, `service-deploy-lambda.yml`) emit `::warning::`
  and say in their own text that the deploy is not gated on them. Those are advisory and honest about it.
- **The absence of a version comparison is the design, not the gap** — and the reason is worth recording
  precisely, because one step of the peer's account does not survive checking. They said semver ranks
  `v1.4.1-patch.2` *below* `v1.4.1`, so a `pin >= floor` test would reject the only safe tag. **Under
  strict semver that is right** (a pre-release ranks below its release). **Under `sort -V` it is not** —
  measured here: `sort -V` orders `v1.3.4 < v1.4.1 < v1.4.1-patch.2`, ranking the safe tag *above*. So
  the hazard's direction depends on which comparator you reach for, which is itself the argument: **the
  property is the thing that matters (does this manifest name the key?), and any version test is a proxy
  for it.** The guard checks the thing, not the proxy.

**What survives, and it is still slate-worthy:** no version floor exists for any non-data service; two
guards are advisory and say so; and **a8 #126's merged commit body still instructs a rollback to
`v1.4.1`, with nothing marking it superseded.** The peer notes their own receipt was an instance of the
class too — they wrote "the floor is now live" when what is live is a property guard on one service's
path.

**One scheduled collision, reported by the peer and carried here because it is dated, not hypothetical:**
the guard's positive control depends on asana's environment block being non-empty, and the a8
single-writer release empties it **by design**. When that release lands the control breaks and the guard
refuses **every** data deploy — correct behaviour, and it will block. **It must be re-anchored before
that release, not after.** The peer is telling the auth lane directly; it is named here so it is not
lost between three seats.

**The class, with its instances corrected:**

| thing | reads as | is |
|---|---|---|
| `[DO NOT MERGE]` in a commit subject | a merge gate | prose; no workflow references it; three such commits are on main |
| a8 #126's commit body | a live rollback instruction | superseded, and nothing marks it so |
| `A8_VERSION` "the floor", on non-data paths | a version floor | advisory warnings that say so, plus error-string text |
| the EBI redaction alarm | armed paging coverage | `notBreaching` on an unwritten metric; un-fireable for 109 days |
| **this seat's own first reading of the a8 floor** | **a measured absence of enforcement** | **a measured absence of one mechanism, mistaken for the absence of all of them** |

> **The word, replacing S-3's:** *"Gates that are prose — wire them, or retire the wording that claims
> they bite: (a) the `[DO NOT MERGE]` marker, (b) the non-data `A8_VERSION` wording, (c) a8 #126's
> superseded rollback instruction, (d) ___."* Wiring any of them changes branch protection or a deploy
> workflow, so they are operator-only.

**Not taken by this seat.** The pin is outside this wave. The peer lane has been told, and told that
this entry exists, so neither of us assumes the other is carrying it.

---

## §7 One item this seat is NOT taking, recorded so it is not lost

The EBI lane's redaction alarm is **armed, paging to live SMS, and structurally incapable of
firing**: it reads a metric nothing writes with `treat_missing_data = notBreaching`, and its state
has not moved in **109 days**. The re-point and the missing-data treatment must be decided **in the
same change** — once the alarm reads a live metric, `notBreaching` still converts a stopped writer
into permanent silence. **That card belongs to the EBI locus and is being carried there**, named here
only so it is not mistaken for something this seat is holding.
