#!/usr/bin/env python3
"""GATE-1 landing-receipt certification harness.

Answers one question, mechanically, against real production data:

    Has THIS clinic's forwarding integration LANDED?
    ("three ATTRIBUTED routed bookings observed clean" -- see predicate.toml)

This harness is built to be run by someone who has never spoken to its author.
If you had to ask a question to run it, that is a defect in the harness -- please
file it. Start with:

    python3 scripts/certification/landing_receipt.py --help
    python3 scripts/certification/landing_receipt.py preflight

Read scripts/certification/RUNBOOK.md first if you have five minutes.

SAFETY PROPERTIES (all enforced at runtime, all self-tested):
  * READ ONLY. The session is opened READ ONLY and every statement is gated:
    it must begin with SELECT and must not contain a DML/DDL token.
  * PATH-A ONLY. `ad_accounts` is RETIRED attribution substrate. Any statement
    mentioning it raises RetiredSubstrateError before it reaches the server.
    The guard is FIRED ONCE ON PURPOSE at every preflight and selftest -- an
    unfired guard does not count as armed.
  * PII-FENCED. Patient names are reduced to initials, phones to a masked tail,
    emails to a masked local part. There is no unmask flag. Certifiers re-derive
    from appt_id / lead_id, which are carried on every receipt.
  * NO SECRETS IN OUTPUT. Credentials are read from a .env file and never
    printed, not even in error paths.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import sys
import tomllib
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

HERE = Path(__file__).resolve().parent
DEFAULT_PREDICATE = HERE / "predicate.toml"
DEFAULT_ENV = Path("/Users/tomtenuta/Code/a8/autom8/.env")
ENV_KEYS = ("DB_HOST", "DB_USERNAME", "DB_PASSWORD", "DB_DATABASE")

# Rows are fetched in ID batches of this size. The naive 7-table join grinds on
# the latin1 <-> utf8mb3 collation clash between campaigns.chiropractor_id
# (latin1_swedish_ci) and chiropractors.guid (utf8mb3_general_ci); the staged
# pattern below never joins across that boundary at all -- it carries identifiers
# through Python, where the comparison is plain byte equality. This is a
# CORRECTNESS device, not only a performance one.
CHUNK = 500

# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #

RETIRED_TABLES = ("ad_accounts",)
FORBIDDEN_TOKENS = (
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "replace", "grant", "revoke", "call", "load_file", "into outfile",
)


class RetiredSubstrateError(RuntimeError):
    """Raised when a query would walk retired attribution substrate (path-b)."""


class ReadOnlyViolation(RuntimeError):
    """Raised when a statement is not a bare SELECT."""


def assert_query_is_legal(sql: str) -> None:
    """Gate every statement. Raises before the statement reaches the server."""
    stripped = sql.strip()
    if not stripped:
        raise ReadOnlyViolation("empty statement")
    if stripped.split(None, 1)[0].upper() != "SELECT":
        raise ReadOnlyViolation(f"not a SELECT: {stripped.split(None, 1)[0]!r}")
    low = " " + re.sub(r"\s+", " ", stripped.lower()) + " "
    for table in RETIRED_TABLES:
        if re.search(rf"\b{re.escape(table)}\b", low):
            raise RetiredSubstrateError(
                f"query references RETIRED attribution substrate {table!r}. "
                "Path-b is not merely discouraged, it is unreachable: ad_account_id "
                "is non-unique (one agency master carries 857 office phones "
                "including the internal +12488025832), so a receipt walking it is "
                "vacuous. Attribution walks PATH-A ONLY "
                "(campaigns.chiropractor_id -> chiropractors.office_phone)."
            )
    for tok in FORBIDDEN_TOKENS:
        if re.search(rf"\b{re.escape(tok)}\b", low):
            raise ReadOnlyViolation(f"forbidden token {tok!r} in statement")


# --------------------------------------------------------------------------- #
# PII fence
# --------------------------------------------------------------------------- #

def initials(full_name: str | None) -> str:
    name = (full_name or "").strip()
    if not name:
        return "?.?."
    parts = [p for p in re.split(r"\s+", name) if p]
    first = parts[0][0].upper() if parts else "?"
    last = parts[-1][0].upper() if len(parts) > 1 else "?"
    return f"{first}.{last}."


def mask_phone(phone: str | None) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return f"***{digits[-4:]}" if len(digits) >= 4 else "***"


def mask_email(email: str | None) -> str:
    e = (email or "").strip()
    if "@" not in e:
        return "***" if e else ""
    local, _, domain = e.partition("@")
    return f"{local[:1]}***@{domain}"


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

@dataclasses.dataclass(frozen=True)
class Predicate:
    raw: dict[str, Any]
    fingerprint: str
    source_path: str

    @property
    def wording(self) -> str:
        return self.raw["predicate"]["wording_of_record"]

    @property
    def wording_status(self) -> str:
        return self.raw["predicate"]["wording_status"]

    @property
    def required_count(self) -> int:
        return int(self.raw["predicate"]["required_count"])

    def leg(self, name: str) -> bool:
        return bool(self.raw["legs"][name]["enabled"])

    def clean(self, name: str) -> dict[str, Any]:
        return self.raw["clean"][name]

    def window_for(self, office_phone: str) -> str:
        overrides = self.raw["window"].get("overrides", {})
        return overrides.get(office_phone, self.raw["window"]["default_since"])

    @property
    def disabled_switches(self) -> list[str]:
        off = [f"legs.{k}" for k, v in self.raw["legs"].items() if not v["enabled"]]
        off += [f"clean.{k}" for k, v in self.raw["clean"].items() if not v["enabled"]]
        return off


def load_predicate(path: Path) -> Predicate:
    blob = path.read_bytes()
    raw = tomllib.loads(blob.decode("utf-8"))
    if raw["attribution"]["path"] != "path-a":
        raise SystemExit(
            f"FATAL: attribution.path is {raw['attribution']['path']!r}. "
            "'path-a' is the only legal value; path-b is retired substrate (R-2)."
        )
    fp = hashlib.sha256(blob).hexdigest()[:16]
    return Predicate(raw=raw, fingerprint=fp, source_path=str(path))


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        raise SystemExit(
            f"FATAL: credentials file not found at {path}.\n"
            "Pass --env /path/to/.env . The file must define "
            f"{', '.join(ENV_KEYS)}. Values are never printed by this harness."
        )
    vals: dict[str, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in ENV_KEYS:
            vals[k] = v
    missing = [k for k in ENV_KEYS if not vals.get(k)]
    if missing:
        raise SystemExit(f"FATAL: {path} is missing {', '.join(missing)}.")
    return vals


# --------------------------------------------------------------------------- #
# Read-only DB session (staged-lookup pattern)
# --------------------------------------------------------------------------- #

class Reader:
    def __init__(self, env: dict[str, str], timeout: int = 30) -> None:
        try:
            import mysql.connector  # noqa: PLC0415
        except ModuleNotFoundError:
            raise SystemExit(
                "FATAL: the 'mysql-connector-python' driver is not installed.\n"
                "Either:  uv run --with mysql-connector-python python "
                "scripts/certification/landing_receipt.py <command>\n"
                "or:      pip install mysql-connector-python"
            ) from None
        try:
            self.conn = mysql.connector.connect(
                host=env["DB_HOST"], user=env["DB_USERNAME"],
                password=env["DB_PASSWORD"], database=env["DB_DATABASE"],
                connection_timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 - message is redacted below
            raise SystemExit(
                "FATAL: could not connect to the database. "
                f"({type(exc).__name__}: {_redact(str(exc), env)})\n"
                "Check network reachability and that the credentials file is current."
            ) from None
        self.cur = self.conn.cursor()
        self.cur.execute("SET SESSION TRANSACTION READ ONLY")
        self.cur.execute("START TRANSACTION READ ONLY")
        self.statements = 0

    def q(self, sql: str, params: Sequence[Any] = ()) -> list[tuple]:
        assert_query_is_legal(sql)
        self.statements += 1
        self.cur.execute(sql, tuple(params))
        return self.cur.fetchall()

    def staged_in(self, tmpl: str, values: Iterable[Any], chunk: int = CHUNK) -> list[tuple]:
        """The staged-lookup primitive: never join, carry IDs through Python."""
        out: list[tuple] = []
        vals = list(values)
        for i in range(0, len(vals), chunk):
            part = vals[i:i + chunk]
            ph = ",".join(["%s"] * len(part))
            out.extend(self.q(tmpl.format(ph=ph), part))
        return out

    def close(self) -> None:
        try:
            self.cur.close()
            self.conn.close()
        except Exception:  # noqa: BLE001, S110
            pass


def _redact(text: str, env: dict[str, str]) -> str:
    for key in ("DB_PASSWORD", "DB_USERNAME", "DB_HOST", "DB_DATABASE"):
        val = env.get(key)
        if val:
            text = text.replace(val, f"<{key}>")
    return text


def guard_selftest(reader: Reader | None) -> list[tuple[str, bool, str]]:
    """Fire every guard once ON PURPOSE. An unfired guard is not an armed guard.

    (Adopted cross-arc from the 33/33 never-authenticated witness lesson, and
    from the ad-lead-gate sitting's deploy rule: "the burst alarm must be FIRED
    ONCE ON PURPOSE before it counts as armed.")
    """
    results: list[tuple[str, bool, str]] = []

    try:
        assert_query_is_legal("SELECT aa.office_phone FROM ad_accounts aa LIMIT 1")
        results.append(("path-b query is refused", False,
                        "GUARD DID NOT BITE -- an ad_accounts query was accepted"))
    except RetiredSubstrateError:
        results.append(("path-b query is refused", True, "RetiredSubstrateError raised"))

    try:
        assert_query_is_legal("SELECT c.campaign_id FROM campaigns c LIMIT 1")
        results.append(("path-a query is accepted", True, "accepted"))
    except Exception as exc:  # noqa: BLE001
        results.append(("path-a query is accepted", False, f"wrongly refused: {exc}"))

    try:
        assert_query_is_legal("UPDATE leads SET status='x'")
        results.append(("write statement is refused", False, "GUARD DID NOT BITE"))
    except ReadOnlyViolation:
        results.append(("write statement is refused", True, "ReadOnlyViolation raised"))

    if reader is not None:
        try:
            reader.q("SELECT office_phone FROM ad_accounts LIMIT 1")
            results.append(("live reader refuses path-b", False, "GUARD DID NOT BITE"))
        except RetiredSubstrateError:
            results.append(("live reader refuses path-b", True, "RetiredSubstrateError raised"))

    return results


# --------------------------------------------------------------------------- #
# start_datetime parsing -- all three observed dialects
# --------------------------------------------------------------------------- #

_OFFSET_RE = re.compile(r"(Z|[+-]\d{2}:?\d{2})$")


def parse_start(raw: str | None) -> tuple[datetime | None, str]:
    """Return (naive datetime, dialect). Dialects: naive | utc-z | offset | unparseable."""
    if not raw or not raw.strip():
        return None, "empty"
    s = raw.strip().replace("T", " ")
    m = _OFFSET_RE.search(s)
    dialect = "naive"
    if m:
        dialect = "utc-z" if m.group(1) == "Z" else "offset"
        s = s[: m.start()]
    s = s.split(".")[0].strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt), dialect
        except ValueError:
            continue
    return None, "unparseable"


def norm_status(status: str | None) -> str:
    return (status or "").strip().lower().replace("-", "_")


# --------------------------------------------------------------------------- #
# Booking evaluation
# --------------------------------------------------------------------------- #

@dataclasses.dataclass
class Booking:
    appt_id: int
    created: datetime
    appt_office_phone: str | None
    contact_phone: str | None
    start_raw: str | None
    start_dt: datetime | None
    start_dialect: str
    status: str | None
    source: str | None
    # lead side
    lead_id: int | None = None
    lead_office_phone: str | None = None
    lead_initials: str = "?.?."
    lead_email_masked: str = ""
    lead_platform: str | None = None
    source_id: str | None = None
    # path-a chain
    ad_id: str | None = None
    adset_id: str | None = None
    campaign_id: str | None = None
    chiro_guid: str | None = None
    campaign_office_phone: str | None = None
    # verdicts
    legs: dict[str, bool] = dataclasses.field(default_factory=dict)
    failures: list[str] = dataclasses.field(default_factory=list)
    flags: list[str] = dataclasses.field(default_factory=list)
    absorbed: list[int] = dataclasses.field(default_factory=list)
    # Every `source` seen across this booking's whole dedup cluster. Collapsing
    # the dual-write twin must not destroy the evidence of which stack wrote it.
    cluster_sources: list[str] = dataclasses.field(default_factory=list)

    @property
    def eligible(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict[str, Any]:
        return {
            "appt_id": self.appt_id,
            "created": self.created.isoformat(sep=" "),
            "start_verbatim": self.start_raw,
            "start_dialect": self.start_dialect,
            "status": self.status,
            "booking_source": self.source,
            "cluster_booking_sources": self.cluster_sources,
            "clinic_office_phone": self.appt_office_phone,
            "contact": mask_phone(self.contact_phone),
            "lead_id": self.lead_id,
            "lead_initials": self.lead_initials,
            "lead_email": self.lead_email_masked,
            "lead_platform": self.lead_platform,
            "ad_id": self.ad_id,
            "adset_id": self.adset_id,
            "campaign_id": self.campaign_id,
            "chiropractor_guid": self.chiro_guid,
            "campaign_office_phone": self.campaign_office_phone,
            "legs": self.legs,
            "refusal_reasons": self.failures,
            "flags": self.flags,
            "absorbed_duplicate_appt_ids": self.absorbed,
            "eligible": self.eligible,
        }


# Stable reason codes. These are the R-4 refusal grammar for this harness: a
# refusal is always reason-coded, never a bare "no".
LEG_ROUTED = ("R1-appt-type", "R2-contact-present", "R3-lead-resolves",
              "R4-start-parseable-and-future")
LEG_ATTRIBUTED = ("A1-source-id-present", "A2-ad-join", "A3-path-a-chain-complete",
                  "A4-path-a-office-congruent")
LEG_CLEAN = ("C1-status-real", "C2-not-duplicate", "C3-clinic-identity-coherent",
             "C4-clinic-not-internal", "C5-clinic-resolves", "C6-within-window")
# Scope is not a "clean" property of the row -- it is which booking PATH the
# certifier has chosen to count. Separated so a scope refusal never reads as a
# defect in the booking.
LEG_SCOPE = ("S1-booking-source-in-scope",)


class Harness:
    def __init__(self, reader: Reader, pred: Predicate) -> None:
        self.r = reader
        self.p = pred

    # -- staged lookups ---------------------------------------------------- #

    def fetch_appointments(self, since: str, office_phone: str | None = None,
                           appt_ids: Sequence[int] | None = None) -> list[tuple]:
        cols = ("id, created, office_phone, phone, start_datetime, status, source, type")
        if appt_ids:
            return self.r.staged_in(
                f"SELECT {cols} FROM appointments WHERE id IN ({{ph}})", appt_ids)
        if office_phone:
            return self.r.q(
                f"SELECT {cols} FROM appointments "
                "WHERE office_phone = %s AND type = 'appt' AND created >= %s "
                "ORDER BY created", (office_phone, since))
        return self.r.q(
            f"SELECT {cols} FROM appointments WHERE type = 'appt' AND created >= %s "
            "ORDER BY created", (since,))

    def build(self, appt_rows: Sequence[tuple]) -> list[Booking]:
        bookings: list[Booking] = []
        for aid, created, office, phone, start_raw, status, source, atype in appt_rows:
            dt, dialect = parse_start(start_raw)
            b = Booking(appt_id=aid, created=created, appt_office_phone=office,
                        contact_phone=phone, start_raw=start_raw, start_dt=dt,
                        start_dialect=dialect, status=status, source=source)
            b.legs["R1-appt-type"] = (atype == "appt")
            bookings.append(b)

        # Stage 1: contact -> leads
        phones = sorted({b.contact_phone for b in bookings if b.contact_phone})
        lead_rows = self.r.staged_in(
            "SELECT phone, id, office_phone, email, source_id, full_name, platform "
            "FROM leads WHERE phone IN ({ph})", phones)
        leads_by_phone: dict[str, tuple] = {}
        for row in lead_rows:
            leads_by_phone.setdefault(row[0], row)

        for b in bookings:
            lead = leads_by_phone.get(b.contact_phone or "")
            if lead:
                b.lead_id, b.lead_office_phone = lead[1], lead[2]
                b.lead_email_masked = mask_email(lead[3])
                b.source_id = lead[4] or None
                b.lead_initials = initials(lead[5])
                b.lead_platform = lead[6]

        # Stage 2: source_id -> ads
        src_ids = sorted({b.source_id for b in bookings if b.source_id})
        ads = dict(self.r.staged_in(
            "SELECT ad_id, adset_id FROM ads WHERE ad_id IN ({ph})", src_ids))
        # Stage 3: adset -> campaign
        adsets = dict(self.r.staged_in(
            "SELECT adset_id, campaign_id FROM adsets WHERE adset_id IN ({ph})",
            sorted({v for v in ads.values() if v})))
        # Stage 4: campaign -> chiropractor guid   (PATH-A; ad_accounts never read)
        camps = dict(self.r.staged_in(
            "SELECT campaign_id, chiropractor_id FROM campaigns WHERE campaign_id IN ({ph})",
            sorted({v for v in adsets.values() if v})))
        # Stage 5: guid -> office phone.
        # NB: campaigns.chiropractor_id is latin1_swedish_ci and chiropractors.guid
        # is utf8mb3_general_ci. Joining them server-side is the clash that grinds;
        # here the identifiers have already come back to Python and the comparison
        # is byte equality inside an IN() list.
        chiros = dict(self.r.staged_in(
            "SELECT guid, office_phone FROM chiropractors WHERE guid IN ({ph})",
            sorted({v for v in camps.values() if v})))

        for b in bookings:
            if b.source_id and b.source_id in ads:
                b.ad_id = b.source_id
                b.adset_id = ads[b.source_id]
                b.campaign_id = adsets.get(b.adset_id)
                b.chiro_guid = camps.get(b.campaign_id) if b.campaign_id else None
                b.campaign_office_phone = chiros.get(b.chiro_guid) if b.chiro_guid else None
        return bookings

    def resolve_clinics(self, office_phones: Iterable[str]) -> dict[str, list[tuple]]:
        rows = self.r.staged_in(
            "SELECT office_phone, guid, office, status FROM chiropractors "
            "WHERE office_phone IN ({ph})", sorted({p for p in office_phones if p}))
        out: dict[str, list[tuple]] = defaultdict(list)
        for r in rows:
            out[r[0]].append(r)
        return out

    # -- evaluation -------------------------------------------------------- #

    def evaluate(self, bookings: list[Booking], since: str,
                 clinic_index: dict[str, list[tuple]]) -> None:
        p = self.p
        since_dt = datetime.strptime(since, "%Y-%m-%d %H:%M:%S")
        internal = set(p.clean("clinic_not_internal")["internal_office_phones"])
        excluded_statuses = {norm_status(s)
                             for s in p.clean("status_real")["excluded_statuses"]}
        synthetic = set(p.raw["non_exclusions"]["synthetic_lead"]["synthetic_platforms"])

        for b in bookings:
            # ---- ROUTED
            b.legs["R2-contact-present"] = bool(b.contact_phone) or bool(b.lead_email_masked)
            b.legs["R3-lead-resolves"] = b.lead_id is not None
            b.legs["R4-start-parseable-and-future"] = (
                b.start_dt is not None and b.start_dt > b.created)

            # ---- ATTRIBUTED (path-a only)
            b.legs["A1-source-id-present"] = bool(b.source_id)
            b.legs["A2-ad-join"] = b.ad_id is not None
            b.legs["A3-path-a-chain-complete"] = all(
                (b.adset_id, b.campaign_id, b.chiro_guid, b.campaign_office_phone))
            b.legs["A4-path-a-office-congruent"] = (
                b.campaign_office_phone is not None
                and b.lead_office_phone is not None
                and b.campaign_office_phone == b.lead_office_phone)

            # ---- CLEAN (C2 is assigned later, after clustering)
            b.legs["C1-status-real"] = norm_status(b.status) not in excluded_statuses
            b.legs["C3-clinic-identity-coherent"] = (
                b.appt_office_phone is not None
                and b.lead_office_phone is not None
                and b.appt_office_phone == b.lead_office_phone)
            b.legs["C4-clinic-not-internal"] = (b.appt_office_phone not in internal)
            b.legs["C5-clinic-resolves"] = (
                len(clinic_index.get(b.appt_office_phone or "", [])) == 1)
            b.legs["C6-within-window"] = b.created >= since_dt

            # ---- provenance flags (never refusals)
            if b.lead_platform in synthetic:
                b.flags.append(p.raw["non_exclusions"]["synthetic_lead"]["flag"])
            if b.start_dialect == "naive":
                b.flags.append(p.raw["non_exclusions"]["timezone_representation"]["flag"])

        self._mark_duplicates(bookings)

        # ---- SCOPE (evaluated after clustering: matches the whole cluster)
        scope = p.raw["scope"]["booking_source"]
        allow = {s.lower() for s in scope.get("include", [])}
        for b in bookings:
            if scope["mode"] == "all":
                b.legs["S1-booking-source-in-scope"] = True
            else:
                b.legs["S1-booking-source-in-scope"] = bool(
                    allow & {s.lower() for s in b.cluster_sources})

        self._collect_failures(bookings)

    def _mark_duplicates(self, bookings: list[Booking]) -> None:
        cfg = self.p.clean("not_duplicate")
        if not cfg["enabled"]:
            for b in bookings:
                b.legs["C2-not-duplicate"] = True
            return
        ctol = timedelta(seconds=int(cfg["created_tolerance_seconds"]))
        stol = timedelta(hours=int(cfg["start_tolerance_hours"]))
        clusters: dict[tuple[str, str], list[Booking]] = defaultdict(list)
        for b in bookings:
            clusters[(b.appt_office_phone or "", b.contact_phone or "")].append(b)
        for group in clusters.values():
            group.sort(key=lambda b: (b.created, b.appt_id))
            kept: list[Booking] = []
            for b in group:
                absorber = None
                for k in kept:
                    if abs(b.created - k.created) > ctol:
                        continue
                    if b.start_dt is None or k.start_dt is None:
                        if b.start_raw == k.start_raw:
                            absorber = k
                            break
                        continue
                    if abs(b.start_dt - k.start_dt) <= stol:
                        absorber = k
                        break
                if absorber is None:
                    b.legs["C2-not-duplicate"] = True
                    b.cluster_sources = [b.source or "(null)"]
                    kept.append(b)
                else:
                    b.legs["C2-not-duplicate"] = False
                    b.cluster_sources = [b.source or "(null)"]
                    absorber.absorbed.append(b.appt_id)
                    src = b.source or "(null)"
                    if src not in absorber.cluster_sources:
                        absorber.cluster_sources.append(src)
        for b in bookings:
            if b.absorbed:
                b.flags.append(f"F-DEDUP-ABSORBED-{len(b.absorbed)}")

    def _collect_failures(self, bookings: list[Booking]) -> None:
        p = self.p
        active: list[str] = list(LEG_ROUTED) if p.leg("routed") else []
        if p.leg("attributed"):
            active += list(LEG_ATTRIBUTED)
        if p.leg("clean"):
            active += [code for code in LEG_CLEAN if _clean_enabled(p, code)]
        active += list(LEG_SCOPE)
        for b in bookings:
            b.failures = [code for code in active if not b.legs.get(code, False)]


# C6 (window) has no [clean.*] switch: a receipt is always scoped to its window,
# and a window-less receipt would be an unbounded claim.
_CLEAN_SWITCH = {
    "C1-status-real": "status_real",
    "C2-not-duplicate": "not_duplicate",
    "C3-clinic-identity-coherent": "clinic_identity_coherent",
    "C4-clinic-not-internal": "clinic_not_internal",
    "C5-clinic-resolves": "clinic_resolves",
}


def _clean_enabled(p: Predicate, code: str) -> bool:
    key = _CLEAN_SWITCH.get(code)
    return True if key is None else bool(p.clean(key).get("enabled", True))


# --------------------------------------------------------------------------- #
# Receipts
# --------------------------------------------------------------------------- #

def build_receipt(pred: Predicate, office_phone: str, since: str,
                  clinic_rows: list[tuple], bookings: list[Booking],
                  guards: list[tuple[str, bool, str]]) -> dict[str, Any]:
    eligible = [b for b in bookings if b.eligible]
    refused = [b for b in bookings if not b.eligible]
    n = len(eligible)
    verdict = "LANDED" if n >= pred.required_count else "NOT-LANDED"
    first_fail = Counter(b.failures[0] for b in refused if b.failures)
    clinic = clinic_rows[0] if clinic_rows else (office_phone, None, None, None)

    synthetic = [b.appt_id for b in eligible if any(f.startswith("F-SYNTHETIC") for f in b.flags)]
    tz_amb = [b.appt_id for b in eligible if "F-TZ-AMBIGUOUS-START" in b.flags]
    sources = sorted({s for b in eligible for s in (b.cluster_sources or ["(null)"])})
    scope = pred.raw["scope"]["booking_source"]
    # The forwarding-integration subset, ALWAYS computed and ALWAYS shown, even
    # under mode="all" -- so a reader can never mistake an ad-funnel reading for
    # a forwarding-integration reading.
    ebi_members = [b.appt_id for b in eligible
                   if "email-booking-intake" in {s.lower() for s in b.cluster_sources}]

    return {
        "receipt_kind": "landing-receipt",
        "schema": "SCHEMA-landing-receipt-2026-09-01",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "predicate": {
            "id": pred.raw["predicate"]["id"],
            "wording_of_record": pred.wording,
            "wording_status": pred.wording_status,
            "ratification_anchor": pred.raw["predicate"]["ratification_anchor"] or None,
            "required_count": pred.required_count,
            "fingerprint": pred.fingerprint,
            "config_source": pred.source_path,
            "disabled_switches": pred.disabled_switches,
        },
        "attribution": {
            "path": pred.raw["attribution"]["path"],
            "chain": pred.raw["attribution"]["chain"],
            "retired_substrate": list(RETIRED_TABLES),
            "guard": "ARMED" if all(ok for _, ok, _ in guards) else "NOT-ARMED",
            "guard_checks": [{"check": c, "passed": ok, "detail": d} for c, ok, d in guards],
        },
        "clinic": {
            "office_phone": clinic[0],
            "guid": clinic[1],
            "office": clinic[2],
            "account_status": clinic[3],
            "resolves_to_n_rows": len(clinic_rows),
        },
        "window": {
            "since": since,
            "since_provenance": ("per-clinic override in predicate.toml"
                                 if office_phone in pred.raw["window"].get("overrides", {})
                                 else "window.default_since in predicate.toml"),
        },
        "scope": {
            "booking_source_mode": scope["mode"],
            "booking_source_include": list(scope.get("include", [])),
            "note": ("mode='all' counts bookings from ANY writer, including the "
                     "legacy monolith (reviewwave) and GHL/dashboard/calendar. It "
                     "is a reading of the AD FUNNEL. To read the FORWARDING "
                     "INTEGRATION, set mode='include' with ['email-booking-intake']."),
        },
        "verdict": verdict,
        "counts": {
            "rows_scanned": len(bookings),
            "eligible": n,
            "required": pred.required_count,
            "shortfall": max(0, pred.required_count - n),
            "refused": len(refused),
            "refused_by_first_failing_leg": dict(first_fail.most_common()),
            "eligible_via_email_booking_intake": len(ebi_members),
            "eligible_via_email_booking_intake_appt_ids": ebi_members,
        },
        "members": [b.to_dict() for b in eligible],
        "refusals": [
            {"appt_id": b.appt_id, "created": b.created.isoformat(sep=" "),
             "first_failing_leg": b.failures[0], "all_failing_legs": b.failures,
             "status": b.status, "booking_source": b.source,
             "lead_id": b.lead_id, "lead_initials": b.lead_initials}
            for b in refused
        ],
        "boundary": {
            "headline": "What this receipt does NOT certify.",
            "synthetic_lead_members": {
                "count": len(synthetic), "appt_ids": synthetic,
                "note": ("Leads with platform='test'. The ratified gate has no "
                         "platform leg and the activation apparatus mints attributed "
                         "test leads by design, so these COUNT. A claim that excludes "
                         "synthetic bookings is a NARROWER claim than this receipt "
                         "makes; subtract this count to make it."),
            },
            "timezone_ambiguous_members": {
                "count": len(tz_amb), "appt_ids": tz_amb,
                "note": ("start_datetime stored without an offset. The future-check "
                         "compares a local wall-clock string against a UTC `created`. "
                         "Ratified semantics, implemented verbatim, flagged not fixed."),
            },
            "booking_sources_observed": {
                "values": sources,
                "note": ("appointments.source is a PROXY, NOT the provider dialect. "
                         "The provider dialect lives in the source email's format and "
                         "is not represented in this database. S-10's '>=3 distinct "
                         "provider dialects' criterion CANNOT be discharged from this "
                         "receipt."),
            },
            "forwarding_integration_subset": {
                "eligible_total": n,
                "eligible_via_email_booking_intake": len(ebi_members),
                "appt_ids": ebi_members,
                "note": ("THE MOST LIKELY OVER-CERTIFICATION IN THIS HARNESS. The "
                         "predicate of record has no booking-source leg, so under "
                         "scope.mode='all' this receipt counts bookings written by "
                         "ANY stack -- including the legacy monolith path, which "
                         "runs whether or not a clinic's email forwarding has ever "
                         "worked. If your claim is about the FORWARDING "
                         "INTEGRATION, the number that supports it is "
                         f"eligible_via_email_booking_intake = {len(ebi_members)}, "
                         f"not eligible = {n}."),
            },
            "not_certified": [
                "That the booking was KEPT. Status is read at query time; a later "
                "cancellation is not retro-applied to an issued receipt.",
                "That these bookings arrived VIA the email-forwarding integration, "
                "unless scope.booking_source.mode='include' was set. See "
                "boundary.forwarding_integration_subset.",
                "That the clinic's forwarding integration was ACTIVE for the whole "
                "window. The window is an operator-supplied parameter; the database "
                "carries no per-clinic activation date.",
                "That the EBI witness ledger ran. This harness reads the booking "
                "substrate only. Witness evidence is S-1's, and is a separate leg.",
                "That the provider-format rule library handled these mails "
                "correctly. Parser correctness is not observable from these rows.",
                "Any refused row's real-world truth. A refusal here means 'not "
                "usable as landing evidence', NOT 'not a real appointment'.",
            ],
        },
    }


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def render_receipt(rc: dict[str, Any]) -> str:
    L: list[str] = []
    p, a, c = rc["predicate"], rc["attribution"], rc["clinic"]
    L.append("=" * 78)
    L.append(f"LANDING RECEIPT -- {c['office'] or '(unnamed clinic)'}  {c['office_phone']}")
    L.append("=" * 78)
    L.append(f"  verdict            : {rc['verdict']}")
    L.append(f"  predicate          : \"{p['wording_of_record']}\"")
    L.append(f"  predicate status   : {p['wording_status']}")
    if p["ratification_anchor"]:
        L.append(f"  ratification anchor: {p['ratification_anchor']}")
    L.append(f"  predicate fingerpr.: {p['fingerprint']}  ({p['config_source']})")
    if p["disabled_switches"]:
        L.append(f"  !! DISABLED SWITCHES: {', '.join(p['disabled_switches'])}")
    L.append(f"  attribution path   : {a['path']}  (guard {a['guard']}; "
             f"{sum(1 for g in a['guard_checks'] if g['passed'])}/"
             f"{len(a['guard_checks'])} guard checks passed)")
    L.append(f"  clinic guid        : {c['guid']}   account status: {c['account_status']}")
    L.append(f"  window since       : {rc['window']['since']}  "
             f"[{rc['window']['since_provenance']}]")
    sc = rc["scope"]
    L.append(f"  booking-source scope: {sc['booking_source_mode']}"
             + (f" {sc['booking_source_include']}"
                if sc["booking_source_mode"] != "all" else
                "  <- counts EVERY writer, not only the forwarding integration"))
    L.append("")
    k = rc["counts"]
    L.append(f"  ELIGIBLE {k['eligible']} of {k['required']} required"
             + (f"   (shortfall {k['shortfall']})" if k["shortfall"] else "   -- MET"))
    n_syn = rc["boundary"]["synthetic_lead_members"]["count"]
    if n_syn:
        qualifier = "ALL of them" if n_syn == k["eligible"] else f"{n_syn} of them"
        L.append(f"  !! {qualifier} rest on a SYNTHETIC (platform='test') lead -- "
                 "see BOUNDARY below")
    L.append(f"  of which via email-booking-intake (the forwarding integration): "
             f"{k['eligible_via_email_booking_intake']}")
    if k["eligible"] >= rc["predicate"]["required_count"] > k["eligible_via_email_booking_intake"]:
        L.append("  !! THIS CLINIC IS 'LANDED' ONLY BECAUSE NON-FORWARDING WRITERS "
                 "ARE COUNTED.")
        L.append("     A forwarding-integration claim is NOT supported by this "
                 "receipt as configured.")
    L.append(f"  scanned {k['rows_scanned']} rows; refused {k['refused']}")
    if k["refused_by_first_failing_leg"]:
        L.append("  refused by first failing leg:")
        for leg, n in k["refused_by_first_failing_leg"].items():
            L.append(f"      {leg:34s} {n}")
    L.append("")
    if rc["members"]:
        L.append("  MEMBERS (each one counts toward the predicate):")
        for m in rc["members"]:
            flags = (" [" + ",".join(m["flags"]) + "]") if m["flags"] else ""
            L.append(f"      appt {m['appt_id']}  created {m['created']}  "
                     f"start {m['start_verbatim']}  status={m['status']}  "
                     f"src={m['booking_source']}")
            L.append(f"          lead {m['lead_id']} ({m['lead_initials']} "
                     f"{m['contact']}) platform={m['lead_platform']}  "
                     f"ad {m['ad_id']} -> campaign {m['campaign_id']} -> "
                     f"chiro {m['campaign_office_phone']}{flags}")
            if m["absorbed_duplicate_appt_ids"]:
                L.append(f"          absorbed duplicate rows: "
                         f"{m['absorbed_duplicate_appt_ids']}")
    else:
        L.append("  MEMBERS: none")
    L.append("")
    b = rc["boundary"]
    L.append("  BOUNDARY -- what this receipt does NOT certify")
    L.append(f"      synthetic-lead members    : {b['synthetic_lead_members']['count']} "
             f"{b['synthetic_lead_members']['appt_ids'] or ''}")
    L.append(f"      tz-ambiguous members      : {b['timezone_ambiguous_members']['count']} "
             f"{b['timezone_ambiguous_members']['appt_ids'] or ''}")
    L.append(f"      booking sources (PROXY)   : "
             f"{', '.join(b['booking_sources_observed']['values']) or '(none)'}")
    L.append(f"        {b['booking_sources_observed']['note']}")
    fis = b["forwarding_integration_subset"]
    L.append(f"      forwarding-integration    : "
             f"{fis['eligible_via_email_booking_intake']} of "
             f"{fis['eligible_total']} eligible {fis['appt_ids'] or ''}")
    L.append(f"        {fis['note']}")
    for item in b["not_certified"]:
        L.append(f"      - {item}")
    L.append("=" * 78)
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# Teeth
# --------------------------------------------------------------------------- #

# Real production rows with known verdicts. These are DELIBERATELY-BROKEN INPUTS
# that the live harness must correctly reject, paired with a real good input that
# must pass -- never a defect injected into working code.
TEETH: list[dict[str, Any]] = [
    {
        "name": "T1 U.E. attorney-referral (lead 336056) -- email-booking-intake row",
        "appt_id": 18231179,
        "expect": "REFUSE",
        "expect_first_failing_leg": "A1-source-id-present",
        "why": ("A Personal-Injury attorney referral with nothing to do with our "
                "funnel. Its lead carries no source_id, so it is unattributed. "
                "ad-lead-gate sitting §3 teeth cluster 1."),
    },
    {
        "name": "T2 U.E. attorney-referral (lead 336056) -- reviewwave twin",
        "appt_id": 18231180,
        "expect": "REFUSE",
        "expect_first_failing_leg": "A1-source-id-present",
        "why": "The dual-write twin of T1. Must refuse for the same reason.",
    },
    {
        "name": "T3 Mansour 2027 date-bug row (appt 18197931 -> 2027-01-04)",
        "appt_id": 18197931,
        "expect": "REFUSE",
        "expect_first_failing_leg": "A1-source-id-present",
        "why": ("Refused on ATTRIBUTION, never on its date. R-3 forbids a horizon "
                "filter: the 2027 dates are a parser defect to be cured at the "
                "parser. If this row ever refuses on a date leg, the harness has "
                "grown the filter R-3 prohibits."),
    },
    {
        "name": "T4 soak booking #1 (appt 18229605, lead 329753, Nation of Wellness)",
        "appt_id": 18229605,
        "expect": "CERTIFY",
        "expect_first_failing_leg": None,
        "why": ("The known-good row. Machine-driven full-stack E2E validation "
                "2026-08-27 16:30-16:46Z. Path-a congruence verified end-to-end "
                "(CONSULT ADDENDUM A Collision 2). It MUST certify -- and it must "
                "carry F-SYNTHETIC-LEAD, because its lead is platform='test'."),
        "expect_flags": ["F-SYNTHETIC-LEAD"],
    },
    {
        "name": "T5 dedup: soak booking #1 absorbs its reviewwave twin 18229606",
        "appt_id": 18229605,
        "expect": "CERTIFY",
        "expect_first_failing_leg": None,
        "with_ids": [18229605, 18229606],
        "expect_absorbs": [18229606],
        "why": ("One booking, two rows, two timestamp dialects (10:00:00 naive and "
                "14:00:00Z). Counting both would put Nation at 2-of-3 on a single "
                "booking."),
    },
    {
        "name": "T7 scope filter keeps a booking whose CLUSTER carries the EBI source",
        "appt_id": 18229605,
        "expect": "CERTIFY",
        "expect_first_failing_leg": None,
        "with_ids": [18229605, 18229606],
        "scope": {"mode": "include", "include": ["email-booking-intake"]},
        "why": ("Under a forwarding-integration reading, soak booking #1 must still "
                "count. Its surviving row IS the email-booking-intake row here, but "
                "the match is made against the whole dedup cluster so it would hold "
                "even if the reviewwave twin had won the absorber slot."),
    },
    {
        "name": "T8 scope filter BITES -- same row refused under a source it lacks",
        "appt_id": 18229605,
        "expect": "REFUSE",
        "expect_first_failing_leg": "S1-booking-source-in-scope",
        "with_ids": [18229605, 18229606],
        "scope": {"mode": "include", "include": ["ghl"]},
        "why": ("The negative control for T7. A scope knob that never refuses is a "
                "decorative knob. The SAME row that certifies under T7 must refuse "
                "here, and on the scope leg specifically -- not on some other leg."),
    },
    {
        "name": "T6 dedup does NOT over-collapse two genuinely different bookings",
        "appt_id": 18194750,
        "expect": "ANY",
        "with_ids": [18194750, 18194751],
        "expect_absorbs": [],
        "why": ("Created 56 seconds apart (inside the created tolerance) but for "
                "appointments 15 days apart. The start-proximity condition must "
                "keep them separate. Without this the dedup rule would be a "
                "blanket collapse and the harness would under-count silently."),
    },
]


def run_teeth(reader: Reader, pred: Predicate) -> tuple[int, int, str]:
    lines: list[str] = []
    passed = failed = 0
    h = Harness(reader, pred)

    lines.append("GUARD SELF-TEST (fired on purpose -- an unfired guard is not armed)")
    for check, ok, detail in guard_selftest(reader):
        lines.append(f"  [{'PASS' if ok else 'FAIL'}] {check}: {detail}")
        passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    lines.append("")

    lines.append("TEETH -- known-refused rows must NOT certify; known-good rows MUST")
    for t in TEETH:
        ids = t.get("with_ids", [t["appt_id"]])
        rows = h.fetch_appointments(since="1970-01-01 00:00:00", appt_ids=ids)
        if not rows:
            lines.append(f"  [FAIL] {t['name']}: fixture rows {ids} NOT FOUND in the database")
            failed += 1
            continue
        # A tooth may pin a scope other than the configured one; the point of the
        # scope teeth is that the knob bites in BOTH directions.
        t_pred = pred
        if "scope" in t:
            raw = json.loads(json.dumps(pred.raw))
            raw["scope"]["booking_source"] = t["scope"]
            t_pred = dataclasses.replace(pred, raw=raw)
        h = Harness(reader, t_pred)
        bookings = h.build(rows)
        clinics = h.resolve_clinics({b.appt_office_phone for b in bookings})
        h.evaluate(bookings, since="1970-01-01 00:00:00", clinic_index=clinics)
        target = next(b for b in bookings if b.appt_id == t["appt_id"])

        problems: list[str] = []
        if t["expect"] == "REFUSE":
            if target.eligible:
                problems.append("row CERTIFIED but must be REFUSED")
            elif target.failures[0] != t["expect_first_failing_leg"]:
                problems.append(
                    f"refused on {target.failures[0]!r}, expected "
                    f"{t['expect_first_failing_leg']!r} -- a refusal for the wrong "
                    "reason is a blanket refusal, not a discriminating one")
        elif t["expect"] == "CERTIFY":
            if not target.eligible:
                problems.append(f"row REFUSED on {target.failures} but must CERTIFY")
        for f in t.get("expect_flags", []):
            if f not in target.flags:
                problems.append(f"missing expected flag {f}")
        if "expect_absorbs" in t and sorted(target.absorbed) != sorted(t["expect_absorbs"]):
            problems.append(f"absorbed {target.absorbed}, expected {t['expect_absorbs']}")

        if problems:
            failed += 1
            lines.append(f"  [FAIL] {t['name']}")
            for pb in problems:
                lines.append(f"           {pb}")
        else:
            passed += 1
            verdict = "CERTIFIED" if target.eligible else f"REFUSED on {target.failures[0]}"
            extra = f"  absorbed={target.absorbed}" if target.absorbed else ""
            flags = f"  flags={target.flags}" if target.flags else ""
            lines.append(f"  [PASS] {t['name']}")
            lines.append(f"           -> {verdict}{extra}{flags}")
        lines.append(f"           why: {t['why']}")
    return passed, failed, "\n".join(lines)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_preflight(args, pred: Predicate) -> int:
    print("PREFLIGHT")
    print(f"  python              : {sys.version.split()[0]}")
    print(f"  predicate config    : {pred.source_path}")
    print(f"  predicate           : \"{pred.wording}\"  [{pred.wording_status}]")
    print(f"  predicate fingerpr. : {pred.fingerprint}")
    print(f"  required count      : {pred.required_count}")
    print(f"  attribution path    : {pred.raw['attribution']['path']}")
    if pred.disabled_switches:
        print(f"  !! DISABLED SWITCHES : {', '.join(pred.disabled_switches)}")
    print("\n  offline guard checks (no database needed):")
    ok_all = True
    for check, ok, detail in guard_selftest(None):
        print(f"    [{'PASS' if ok else 'FAIL'}] {check}: {detail}")
        ok_all &= ok
    try:
        import mysql.connector  # noqa: F401,PLC0415
        print("    [PASS] mysql-connector-python importable")
    except ModuleNotFoundError:
        print("    [FAIL] mysql-connector-python NOT installed -- run with:")
        print("           uv run --with mysql-connector-python python "
              "scripts/certification/landing_receipt.py preflight")
        return 2
    env = load_env(Path(args.env))
    print(f"    [PASS] credentials file readable at {args.env} "
          f"({len(ENV_KEYS)} keys present, values not printed)")
    reader = Reader(env, timeout=args.timeout)
    try:
        ver = reader.q("SELECT VERSION()")[0][0]
        print(f"    [PASS] connected; server {ver}; session is READ ONLY")
        for check, ok, detail in guard_selftest(reader)[-1:]:
            print(f"    [{'PASS' if ok else 'FAIL'}] {check}: {detail}")
            ok_all &= ok
    finally:
        reader.close()
    print("\nPREFLIGHT " + ("OK -- the harness is ready to run." if ok_all else "FAILED."))
    return 0 if ok_all else 1


def cmd_selftest(args, pred: Predicate) -> int:
    env = load_env(Path(args.env))
    reader = Reader(env, timeout=args.timeout)
    try:
        passed, failed, body = run_teeth(reader, pred)
    finally:
        reader.close()
    print(body)
    print("\n" + "=" * 78)
    print(f"SELFTEST: {passed} passed, {failed} failed")
    print("=" * 78)
    return 0 if failed == 0 else 1


def cmd_clinic(args, pred: Predicate) -> int:
    env = load_env(Path(args.env))
    reader = Reader(env, timeout=args.timeout)
    try:
        h = Harness(reader, pred)
        since = args.since or pred.window_for(args.office_phone)
        rows = h.fetch_appointments(since=since, office_phone=args.office_phone)
        bookings = h.build(rows)
        clinics = h.resolve_clinics({args.office_phone}
                                    | {b.appt_office_phone for b in bookings})
        h.evaluate(bookings, since=since, clinic_index=clinics)
        guards = guard_selftest(reader)
        rc = build_receipt(pred, args.office_phone, since,
                           clinics.get(args.office_phone, []), bookings, guards)
    finally:
        reader.close()
    print(json.dumps(rc, indent=2, default=str) if args.json else render_receipt(rc))
    return 0 if rc["verdict"] == "LANDED" else 3


def cmd_survey(args, pred: Predicate) -> int:
    env = load_env(Path(args.env))
    reader = Reader(env, timeout=args.timeout)
    try:
        h = Harness(reader, pred)
        since = args.since or pred.raw["window"]["default_since"]
        rows = h.fetch_appointments(since=since)
        bookings = h.build(rows)
        clinics = h.resolve_clinics({b.appt_office_phone for b in bookings})
        h.evaluate(bookings, since=since, clinic_index=clinics)
        guards = guard_selftest(reader)
    finally:
        reader.close()

    per: dict[str, list[Booking]] = defaultdict(list)
    for b in bookings:
        per[b.appt_office_phone or "(null)"].append(b)
    receipts = [build_receipt(pred, phone, since, clinics.get(phone, []), bs, guards)
                for phone, bs in per.items()]
    receipts.sort(key=lambda r: -r["counts"]["eligible"])

    if args.json:
        print(json.dumps({"survey": receipts}, indent=2, default=str))
        return 0

    landed = [r for r in receipts if r["verdict"] == "LANDED"]
    print(f"SURVEY -- predicate \"{pred.wording}\" [{pred.wording_status}] "
          f"fp={pred.fingerprint}")
    print(f"  window since {since}; {len(receipts)} clinics with rows; "
          f"{len(landed)} LANDED (>= {pred.required_count} eligible)")
    print(f"  attribution path-a only; retired-substrate guard "
          f"{receipts[0]['attribution']['guard'] if receipts else 'n/a'}")
    print()
    ebi_landed = [r for r in receipts
                  if r["counts"]["eligible_via_email_booking_intake"]
                  >= pred.required_count]
    print(f"  scope.booking_source mode={pred.raw['scope']['booking_source']['mode']}")
    print()
    print(f"  {'clinic':36s} {'phone':15s} {'elig':>5s} {'ebi':>4s} {'scan':>5s} "
          f"{'synth':>5s}  verdict")
    for r in receipts:
        if r["counts"]["eligible"] < args.min_eligible:
            continue
        print(f"  {(r['clinic']['office'] or '?')[:36]:36s} "
              f"{r['clinic']['office_phone'] or '?':15s} "
              f"{r['counts']['eligible']:5d} "
              f"{r['counts']['eligible_via_email_booking_intake']:4d} "
              f"{r['counts']['rows_scanned']:5d} "
              f"{r['boundary']['synthetic_lead_members']['count']:5d}  "
              f"{r['verdict']}")
    print()
    print(f"  READ THE 'ebi' COLUMN. 'elig'/'verdict' count EVERY writer -- the "
          f"legacy monolith\n  included -- and are an AD-FUNNEL reading. 'ebi' is "
          f"the forwarding-integration\n  reading. {len(landed)} clinics reach "
          f"{pred.required_count} on 'elig'; {len(ebi_landed)} reach it on 'ebi'.")
    print("\n  A survey is a population reading, not a certificate. Issue a "
          "per-clinic receipt\n  with `clinic --office-phone ...` for anything you "
          "intend to certify.")
    return 0


def cmd_booking(args, pred: Predicate) -> int:
    env = load_env(Path(args.env))
    reader = Reader(env, timeout=args.timeout)
    try:
        h = Harness(reader, pred)
        rows = h.fetch_appointments(since="1970-01-01 00:00:00", appt_ids=args.appt_id)
        if not rows:
            print(f"no appointment rows found for {args.appt_id}")
            return 4
        bookings = h.build(rows)
        clinics = h.resolve_clinics({b.appt_office_phone for b in bookings})
        h.evaluate(bookings, since="1970-01-01 00:00:00", clinic_index=clinics)
    finally:
        reader.close()
    if args.json:
        print(json.dumps([b.to_dict() for b in bookings], indent=2, default=str))
        return 0
    for b in bookings:
        print("-" * 78)
        print(f"appt {b.appt_id}  ->  "
              f"{'ELIGIBLE' if b.eligible else 'REFUSED: ' + ', '.join(b.failures)}")
        print(f"  clinic {b.appt_office_phone}  contact {mask_phone(b.contact_phone)}  "
              f"lead {b.lead_id} ({b.lead_initials}) platform={b.lead_platform}")
        print(f"  start {b.start_raw!r} ({b.start_dialect})  created {b.created}  "
              f"status={b.status}  source={b.source}")
        print(f"  path-a: ad {b.ad_id} -> adset {b.adset_id} -> campaign "
              f"{b.campaign_id} -> chiro {b.chiro_guid} -> "
              f"{b.campaign_office_phone}")
        print("  legs:")
        for code in LEG_ROUTED + LEG_ATTRIBUTED + LEG_CLEAN + LEG_SCOPE:
            if code in b.legs:
                print(f"    [{'ok ' if b.legs[code] else 'NO '}] {code}")
        if b.flags:
            print(f"  flags: {', '.join(b.flags)}")
        if b.absorbed:
            print(f"  absorbed duplicate rows: {b.absorbed}")
    return 0


# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="landing_receipt.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
        epilog=(
            "TYPICAL SESSION FOR A CERTIFIER\n"
            "  1. preflight                      -- prove the instrument works\n"
            "  2. selftest                       -- prove it has teeth (both sides)\n"
            "  3. survey                         -- see the whole clinic population\n"
            "  4. clinic --office-phone +1...    -- issue the receipt you will cite\n"
            "  5. booking --appt-id N            -- inspect any single row's legs\n"
            "\nExit codes: 0 ok | 1 selftest/preflight failed | 3 clinic NOT-LANDED "
            "| 4 no rows\n"),
    )
    # Common flags are attached BOTH to the top-level parser and to every
    # subcommand, so `--json survey` and `survey --json` both work. A certifier
    # should never lose a five-minute run to argparse ordering.
    common = argparse.ArgumentParser(add_help=False)
    for parser in (ap, common):
        parser.add_argument("--env", default=str(DEFAULT_ENV),
                            help="path to the .env holding DB_* credentials "
                                 "(default: %(default)s). Never printed.")
        parser.add_argument("--predicate", default=str(DEFAULT_PREDICATE),
                            help="path to predicate.toml (default: %(default)s)")
        parser.add_argument("--timeout", type=int, default=30,
                            help="DB connect timeout seconds")
        parser.add_argument("--json", action="store_true",
                            help="emit machine-readable JSON")
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("preflight", parents=[common],
                   help="check env, driver, connectivity and guards")
    sub.add_parser("selftest", parents=[common],
                   help="THE TEETH: known-bad rows must refuse, known-good must certify")

    c = sub.add_parser("clinic", parents=[common],
                       help="issue a landing receipt for one clinic")
    c.add_argument("--office-phone", required=True,
                   help="clinic office phone, e.g. +14079068111")
    c.add_argument("--since", help="override the window start "
                                   "('YYYY-MM-DD HH:MM:SS')")

    s = sub.add_parser("survey", parents=[common],
                       help="eligible-count for every clinic with rows")
    s.add_argument("--since", help="window start ('YYYY-MM-DD HH:MM:SS')")
    s.add_argument("--min-eligible", type=int, default=1,
                   help="hide clinics below this eligible count (default 1)")

    b = sub.add_parser("booking", parents=[common],
                       help="per-leg verdict for specific appointment rows")
    b.add_argument("--appt-id", type=int, nargs="+", required=True)

    args = ap.parse_args(argv)
    pred = load_predicate(Path(args.predicate))
    return {
        "preflight": cmd_preflight, "selftest": cmd_selftest,
        "clinic": cmd_clinic, "survey": cmd_survey, "booking": cmd_booking,
    }[args.command](args, pred)


if __name__ == "__main__":
    sys.exit(main())
