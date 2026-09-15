#!/usr/bin/env python3
"""read-the-name S-1 -- the arming-receipt observers, committed (coordination hazard H-6).

Durable home of the session-scratch ``arm_observe.py`` and ``sender_join.py`` (seat d5861864,
2026-09-15) plus the guid8 -> clinic lookup. The scratch copies are session-isolated and do not
survive; ``.ledge/reviews/ARMING-RECEIPT-read-the-name-s1-2026-09-21.md`` cites THIS file.
Hardened on the way in: an AWS failure exits 1 instead of reading as a zero, and every Insights
read prints recordsScanned (an Insights zero without a scan count is UNTAKEN, not a reading).

READ-ONLY. Every call is a Describe / Get / List or a CloudWatch Logs Insights query. Nothing is
invoked, published, applied, re-pointed or armed.

usage (us-east-1; an AWS session with read on logs, cloudwatch, sns, lambda, events):
  python3 scripts/read_the_name/arm_observe.py all
  python3 scripts/read_the_name/arm_observe.py A | B | D | E | F
  python3 scripts/read_the_name/arm_observe.py C <guid8> [<guid8> ...]
  python3 scripts/read_the_name/arm_observe.py lookup <guid8> [--print-name]

exit: 0 every requested observer emitted | 2 an observer did not emit (UNTAKEN) | 1 AWS failure

FENCES: guid8 only (a full GUID is refused); ``office_phone`` rides the same intake line as
``office_name`` and is NEVER parsed or projected here; the account id is masked; ``lookup``
withholds the name unless --print-name is given, and --print-name is for the reader's own
terminal only -- never a page thread, a Slack reply, an email reply, a PR, or a ledger.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone

REGION = "us-east-1"
FLOOR_FN = "autom8-email-booking-intake-office-floor"
INTAKE_FN = "autom8-email-booking-intake"
FLOOR_LG = f"/aws/lambda/{FLOOR_FN}"
INTAKE_LG = f"/aws/lambda/{INTAKE_FN}"
# the five functions that share ONE image tag (autom8y scripts/apply-preserve-fuel-registry.tsv)
EBI_FNS = (
    INTAKE_FN,
    f"{INTAKE_FN}-contente-reconcile",
    f"{INTAKE_FN}-forwarding-nudge",
    f"{INTAKE_FN}-contente-retro-redrive",
    FLOOR_FN,
)
PLATFORM_TOPIC = "autom8y-platform-alerts"
SCRATCH_TOPIC = "autom8-ebi-office-floor-scratch"
NAME_BEARING_TAG = "21d4395"  # evaluator s1.3: office_name on the page. Never roll back to it after the arm.
DEFAULT_OFFICES = ("8a9b1a84", "e63bbbe0", "40f86e73")  # two lead-match-dominated, one genuine zero
ARRIVALS = (
    '["terminal_decline","ad_lead_gate_refused","booking_gate_declined",'
    '"booking_completed","contente_booking_booked","booking_intake_fault"]'
)
BOOKINGS = '["booking_completed","contente_booking_booked"]'
GUID8 = re.compile(r"^[0-9a-f]{8}$")
LEAD_MATCH_SHARE = 0.5  # PLATFORM-HEURISTIC (seat-authored, not operator-ruled); see the runbook s1.4 amendment


class Untaken(Exception):
    """An observer ran but did not emit. Never written down as a reading."""


def mask(s: object) -> str:
    return re.sub(r"\d{12}", "<ACCOUNT>", str(s))


def utc(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def utc_hour(cli_ts: str) -> str:
    """The AWS CLI renders metric Timestamps in the LOCAL offset (e.g. -04:00). Slicing the string
    compares local hours to UTC hours and manufactures missing buckets (caught 2026-09-15: four
    phantom gaps, 18Z-21Z, on a plane that sampled every hour). Normalise to UTC first."""
    return datetime.fromisoformat(cli_ts).astimezone(timezone.utc).strftime("%Y-%m-%dT%H")


def aws(*args: str) -> dict:
    r = subprocess.run(
        ["aws", *args, "--region", REGION, "--output", "json"],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        print(f"AWS CALL FAILED rc={r.returncode}: aws {' '.join(args[:2])}: {mask(r.stderr.strip()[:240])}")
        sys.exit(1)
    return json.loads(r.stdout) if r.stdout.strip() else {}


def insights(log_group: str, query: str, hours: float) -> list[dict]:
    end = int(time.time())
    start = int(end - hours * 3600)
    qid = aws("logs", "start-query", "--log-group-name", log_group, "--start-time", str(start),
              "--end-time", str(end), "--query-string", query).get("queryId")
    if not qid:
        raise Untaken("start-query returned no queryId")
    res: dict = {}
    for _ in range(40):
        time.sleep(3)
        res = aws("logs", "get-query-results", "--query-id", qid)
        if res.get("status") in ("Complete", "Failed", "Cancelled", "Timeout"):
            break
    st = res.get("statistics", {})
    print(f"   [insights {log_group.rsplit('/', 1)[-1]} {hours:g}h] status={res.get('status')} "
          f"recordsScanned={st.get('recordsScanned')} recordsMatched={st.get('recordsMatched')}")
    if res.get("status") != "Complete":
        raise Untaken(f"query status {res.get('status')}")
    if not st.get("recordsScanned"):
        raise Untaken("recordsScanned is zero -- an UNTAKEN zero, not a reading")
    return [{f["field"]: f["value"] for f in row if f["field"] != "@ptr"} for row in res.get("results", [])]


def s1_alarms() -> list[dict]:
    out: list[dict] = []
    for prefix in ("autom8-ebi-booking-floor", FLOOR_FN):
        out += aws("cloudwatch", "describe-alarms", "--alarm-name-prefix", prefix).get("MetricAlarms", [])
    return out


def topics_of(actions: list[str]) -> list[str]:
    return [a.rsplit(":", 1)[-1] for a in actions]


def observe_a() -> None:
    print("== (A) the evaluator STOPS -- run-line cadence + deadman state ==")
    rows = insights(FLOOR_LG, "fields @timestamp | filter @message like /office_floor_evaluated/ "
                    "| stats count(*) as runs, max(@timestamp) as last_run", 6)
    runs = int(float(rows[0].get("runs", 0))) if rows else 0
    last = rows[0].get("last_run") if rows else None
    print(f"   run lines, last 6h: {runs}  (healthy = 6, one per hour; 0 = STOPPED)  last_run={last}")
    fn_arn = aws("lambda", "get-function-configuration", "--function-name", FLOOR_FN)["FunctionArn"]
    for rule in aws("events", "list-rule-names-by-target", "--target-arn", fn_arn).get("RuleNames", []):
        d = aws("events", "describe-rule", "--name", rule)
        print(f"   schedule rule {rule}: {d.get('State')} {d.get('ScheduleExpression')}")
    for a in s1_alarms():
        print(f"   alarm {a['AlarmName']}: {a['StateValue']}  period={a.get('Period')}s "
              f"eval={a.get('EvaluationPeriods')} dta={a.get('DatapointsToAlarm')} "
              f"actions={topics_of(a.get('AlarmActions', []))}")
    print("   latency: the freshness alarm (P3600, 2 of 3, > 7200 s) reds at roughly the FOURTH missed hourly")
    print("   fire -- one to three missed fires are invisible to it. dlq-not-empty and lambda-errors (P300, 1 of 1)")
    print("   are the faster floor, but only for a CRASHING evaluator: a disabled rule raises no error and no DLQ.")
    if runs == 0:
        raise Untaken("zero run lines in 6h -- STOPPED, or the read did not see the plane; read the states above")


def observe_b() -> None:
    print("== (B) the evaluator RUNS but REFUSES -- control:failed + LastSuccessTimestamp hourly census ==")
    rows = insights(FLOOR_LG, 'fields @message | filter @message like /office_floor_evaluated/ '
                    '| stats count(*) as runs, sum(@message like /"control":\\s*"passed"/) as passed, '
                    'sum(@message like /"control":\\s*"failed"/) as refused', 24)
    d = rows[0] if rows else {}
    print(f"   last 24h: runs={d.get('runs')} passed={d.get('passed')} refused={d.get('refused')}")
    end = int(time.time()) // 3600 * 3600
    start = end - 24 * 3600
    m = aws("cloudwatch", "get-metric-statistics", "--namespace", "Autom8y/EbiOfficeFloor",
            "--metric-name", "LastSuccessTimestamp", "--start-time", utc(start), "--end-time", utc(end),
            "--period", "3600", "--statistics", "SampleCount")
    have = {utc_hour(p["Timestamp"]) for p in m.get("Datapoints", [])}
    missing = [utc(start + h * 3600)[11:13] + "Z" for h in range(24) if utc(start + h * 3600)[:13] not in have]
    print(f"   LastSuccessTimestamp: {24 - len(missing)} of 24 complete hourly buckets carry a sample; "
          f"missing hours (UTC): {missing or 'none'}")
    print("   a refusal is a MISSING bucket here and pages NOTHING until the success-gap alarm exists (S1.7)")
    if not have:
        raise Untaken("no LastSuccessTimestamp sample in 24h")


def _masked(domain: str | None) -> str:
    if domain is None:
        return "<unjoined>"
    return ("<" + hashlib.sha256(domain.encode()).hexdigest()[:8] + ">") if domain else "<empty>"


def observe_c(guids: list[str]) -> None:
    print("== (C) the MIRROR half -- a TRUE page about the WRONG THING: lead-match share of the office ==")
    for g in guids:
        if not GUID8.match(g):
            raise SystemExit(f"not a guid8: {g!r} (8 lowercase hex; a full GUID is refused)")
    gl = ",".join(f'"{g}"' for g in guids)
    base = ('fields @message | parse @message /"chiropractor_guid":\\s*"(?<g>[0-9a-fA-F]{8})/ '
            '| parse @message /"event":\\s*"(?<ev>[a-z_]+)"/ '
            '| parse @message /"error_type":\\s*"(?<et>[A-Za-z]+)"/ '
            '| parse @message /"trace_id":\\s*"(?<tid>[^"]+)"/ ')
    counts = {r.get("g"): r for r in insights(INTAKE_LG, base + f"| filter g in [{gl}] "
              f"| stats sum(ev in {ARRIVALS}) as arrivals, sum(ev in {BOOKINGS}) as bookings, "
              'sum(et="LeadMatchError") as lme by g', 72)}
    pairs = [(r.get("g"), r.get("tid")) for r in insights(INTAKE_LG, base +
             f'| filter et="LeadMatchError" and g in [{gl}] | display g, tid | limit 400', 72) if r.get("tid")]
    tids = sorted({t for _, t in pairs})
    dom: dict[str, str] = {}
    for i in range(0, len(tids), 100):  # Insights query-length ceiling: join in chunks
        tl = ",".join(f'"{t}"' for t in tids[i:i + 100])
        # from_domain is read on sender_auth_observed for COVERAGE: present on every message of every class
        # since 2026-09-05; intake_classified.from_domain exists only on unrecognised lines and only since v69
        # (2026-09-14T00:55Z). It is the PARSED HEADER From -- a header the sender controls, NOT an
        # authenticated identity, whatever the event is called.
        for r in insights(INTAKE_LG, 'fields @message | filter @message like /sender_auth_observed/ '
                          '| parse @message /"trace_id":\\s*"(?<tid>[^"]+)"/ '
                          '| parse @message /"from_domain":\\s*"(?<fd>[^"]*)"/ '
                          f"| filter tid in [{tl}] | display tid, fd | limit 1000", 72):
            dom[r.get("tid", "")] = r.get("fd", "")
    ok = True
    for g in guids:
        c = counts.get(g, {})
        arr, bk, lme = (int(float(c.get(k) or 0)) for k in ("arrivals", "bookings", "lme"))
        senders = Counter(_masked(dom.get(t)) for gg, t in pairs if gg == g)
        top, top_n = (senders.most_common(1) or [("<none>", 0)])[0]
        share = lme / arr if arr else 0.0
        if not arr:
            verdict, ok = "UNTAKEN -- no arrivals seen for this guid8 in 72 h", False
        elif share >= LEAD_MATCH_SHARE and lme and top_n / lme >= LEAD_MATCH_SHARE:
            verdict = "LEAD-MATCH-DOMINATED, ONE FROM DOMAIN -- DO NOT CALL THE CLINIC; route to the platform owner"
        elif share >= LEAD_MATCH_SHARE:
            verdict = "LEAD-MATCH-DOMINATED, several From domains -- do not call; route to the platform owner"
        else:
            verdict = "office-side -- a genuine not-booking signal; work the runbook s1.1 cell"
        print(f"   office {g}: arrivals={arr} bookings={bk} lead_match_errors={lme} share={share:.0%} "
              f"top_from_domain={top} x{top_n} (of {lme}; joined {sum(1 for gg, t in pairs if gg == g and t in dom)})")
        print(f"      -> {verdict}")
    if not ok:
        raise Untaken("an office had no arrivals in the window")


def observe_d() -> None:
    print("== (D) the DELIVERY half -- what the page reaches, and what nothing can observe ==")
    arn = next((t["TopicArn"] for t in aws("sns", "list-topics").get("Topics", [])
                if t["TopicArn"].endswith(":" + PLATFORM_TOPIC)), None)
    if not arn:
        raise Untaken(f"{PLATFORM_TOPIC} not found")
    subs = aws("sns", "list-subscriptions-by-topic", "--topic-arn", arn).get("Subscriptions", [])
    for s in subs:
        p = s["Protocol"]
        ep = s["Endpoint"].rsplit(":", 1)[-1] if p == "lambda" else f"<{p} endpoint, masked>"
        state = "PENDING" if s["SubscriptionArn"].startswith("Pending") else "confirmed"
        print(f"   {PLATFORM_TOPIC} <- {p} {ep} ({state})")
    print(f"   email endpoints={sum(s['Protocol'].startswith('email') for s in subs)} "
          f"sms endpoints={sum(s['Protocol'] == 'sms' for s in subs)} lambda={sum(s['Protocol'] == 'lambda' for s in subs)}")
    env = aws("lambda", "get-function-configuration", "--function-name", FLOOR_FN).get("Environment", {})
    for k, v in sorted(env.get("Variables", {}).items()):
        if str(v).startswith("arn:aws:sns:"):
            print(f"   DIGEST path: evaluator env {k} -> {v.rsplit(':', 1)[-1]}")
    for a in s1_alarms():
        print(f"   ALARM path:  {a['AlarmName']} -> {topics_of(a.get('AlarmActions', []))}")
    scratch = next((t["TopicArn"] for t in aws("sns", "list-topics").get("Topics", [])
                    if t["TopicArn"].endswith(":" + SCRATCH_TOPIC)), None)
    if scratch:
        n = len(aws("sns", "list-subscriptions-by-topic", "--topic-arn", scratch).get("Subscriptions", []))
        print(f"   {SCRATCH_TOPIC}: {n} subscription(s)")
    now = int(time.time())
    m = aws("cloudwatch", "get-metric-statistics", "--namespace", "AWS/SNS", "--metric-name",
            "NumberOfMessagesPublished", "--dimensions", f"Name=TopicName,Value={PLATFORM_TOPIC}",
            "--start-time", utc(now - 7 * 86400), "--end-time", utc(now), "--period", "86400", "--statistics", "Sum")
    print("   channel population, published/day 7d:",
          sorted((utc_hour(p["Timestamp"])[:10], int(p["Sum"])) for p in m.get("Datapoints", [])))
    e = aws("cloudwatch", "get-metric-statistics", "--namespace", "AWS/Lambda", "--metric-name", "Errors",
            "--dimensions", "Name=FunctionName,Value=autom8-slack-alert", "--start-time", utc(now - 86400),
            "--end-time", utc(now), "--period", "86400", "--statistics", "Sum")
    print("   autom8-slack-alert Errors 24h:", [int(p["Sum"]) for p in e.get("Datapoints", [])] or "no datapoint")
    al = aws("cloudwatch", "describe-alarms")
    states = Counter(a["StateValue"] for a in al.get("MetricAlarms", []) + al.get("CompositeAlarms", [])
                     if any(x.endswith(":" + PLATFORM_TOPIC) for x in a.get("AlarmActions", [])))
    print(f"   alarms whose AlarmActions include {PLATFORM_TOPIC}: {sum(states.values())} {dict(states)}")
    print("   READ: UNOBSERVED. Nothing in AWS records that a human opened the email or the Slack post.")
    print("   An unread inbox is silent and recorded nowhere; the reader's acknowledgement is the only observer.")


def observe_e() -> None:
    print("== (E) known residuals -- declared, not hidden ==")
    rows = insights(FLOOR_LG, 'fields @timestamp | filter @message like /office_floor_evaluated/ '
                    '| parse @message /"evaluator_version":\\s*"(?<ev>[^"]+)"/ '
                    '| parse @message /"offices_unclassified":\\s*(?<ou>[0-9]+)/ '
                    '| parse @message /"booking_attribution_floor_day":\\s*"(?<af>[^"]+)"/ '
                    '| parse @message /"booking_attribution_floor_age_days":\\s*(?<aa>[0-9]+)/ '
                    "| sort @timestamp desc | limit 1 | display @timestamp, ev, ou, af, aa", 3)
    r = rows[0] if rows else {}
    print(f"   latest run {r.get('@timestamp')}: evaluator={r.get('ev')} offices_unclassified={r.get('ou')} "
          f"attribution_floor_day={r.get('af')} age_days={r.get('aa')}  (the last three exist from s1.4)")
    rows = insights(FLOOR_LG, 'fields @message | filter @message like /office_floor_office/ '
                    '| parse @message /"chiropractor_guid":\\s*"(?<g>[0-9a-f]{8})/ '
                    '| parse @message /"floor_class":\\s*"(?<fc>[a-z]+)"/ '
                    '| parse @message /"offer_class":\\s*"(?<oc>[a-z_-]+)"/ '
                    '| filter fc = "zero" | stats count(*) as lines by g, oc', 2)
    for x in sorted(rows, key=lambda x: x.get("g", "")):
        flag = "ZERO-floor AND class unknown -> check (C) before acting" if x.get("oc") == "unknown" else ""
        print(f"   ZERO-floor office {x.get('g')} class={x.get('oc')} lines={x.get('lines')}  {flag}")
    print("   the misattribution signal is this ZERO-floor AND class-unknown intersection, NOT offices_unclassified")
    print("   (which counts every snapshot-absent office and reads >= 19 on today's traffic).")
    print("   residual: the lookback control reuses the primary query's offices_with_bookings -- a lookback that")
    print("   found NO bookings still passes and still stamps LastSuccessTimestamp (handler.py _lookback_control).")
    print("   residual: the attribution floor is the OLDEST attributed booking day in the lookback; a stamping")
    print("   regression today leaves it unchanged, so it cannot detect one.")


def observe_f() -> None:
    print("== (F) the recovery floor -- the image each EBI function SERVES ==")
    tags = {}
    for fn in EBI_FNS:
        aliases = {a["Name"]: a["FunctionVersion"] for a in aws("lambda", "list-aliases", "--function-name", fn).get("Aliases", [])}
        q = ["--qualifier", aliases["live"]] if "live" in aliases else []
        uri = aws("lambda", "get-function", "--function-name", fn, *q)["Code"]["ImageUri"]
        tags[fn] = uri.rsplit(":", 1)[-1]
        served = f"alias live -> v{aliases['live']}" if "live" in aliases else "no alias (unqualified IS served)"
        warn = "  <- NAME-BEARING image (s1.3): forbidden after the arm" if tags[fn] == NAME_BEARING_TAG else ""
        print(f"   {fn}: {tags[fn]}  [{served}]{warn}")
    print(f"   unanimous: {len(set(tags.values())) == 1}  (the preserve-fuel resolver requires all five to agree)")
    print("   no CI rollback button exists; the only failure response is roll-forward (a new merge + dispatch).")


def lookup(g: str, print_name: bool) -> None:
    if not GUID8.match(g):
        raise SystemExit(f"not a guid8: {g!r}")
    print(f"== guid8 -> clinic, out of band: office_resolved lines on {INTAKE_LG}, 30 d ==")
    rows = insights(INTAKE_LG, 'fields @timestamp | filter @message like /office_resolved/ '
                    '| parse @message /"guid":\\s*"(?<g>[0-9a-fA-F]{8})/ '
                    '| parse @message /"office_name":\\s*"(?<office_name>[^"]+)"/ '
                    f'| filter g = "{g}" and ispresent(office_name) '
                    "| stats count(*) as lines, max(@timestamp) as last_seen by office_name", 24 * 30)
    print(f"   guid8 {g}: {len(rows)} distinct office_name value(s)")
    for r in rows:
        shown = r.get("office_name") if print_name else "<withheld; --print-name at your own terminal only>"
        print(f"     {shown}  lines={r.get('lines')}  last_seen={r.get('last_seen')}")
    if len(rows) != 1:
        print("   ABSENT or AMBIGUOUS -- do not guess; ask the operator (runbook DW-9)")
        raise Untaken("lookup did not resolve to exactly one name")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    plan = {"A": [observe_a], "B": [observe_b], "D": [observe_d], "E": [observe_e], "F": [observe_f],
            "C": [lambda: observe_c([a for a in rest if not a.startswith("-")] or list(DEFAULT_OFFICES))],
            "lookup": [lambda: lookup(rest[0], "--print-name" in rest)],
            "all": [observe_a, observe_b, lambda: observe_c(list(DEFAULT_OFFICES)), observe_d, observe_e, observe_f]}
    if cmd not in plan:
        print(__doc__)
        return 2
    print(f"arm_observe {cmd} at {utc(time.time())}")
    rc = 0
    for step in plan[cmd]:
        try:
            step()
        except Untaken as exc:
            print(f"   UNTAKEN: {exc} -- do not write this observer's line into the receipt")
            rc = 2
        print()
    print("ALL REQUESTED OBSERVERS EMITTED:", "YES" if rc == 0 else "NO")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
