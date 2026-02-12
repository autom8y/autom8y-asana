"""Diagnostic spike: trace the exact write pipeline — ALL field types.

Target: Task 1213235375126350 (leftover E2E proof offer)

Tests: text, number, enum, multi_enum, and core fields.
Leaves fields set for manual verification in Asana UI.

Run: ASANA_PAT=... .venv/bin/python tests/integration/spike_write_diagnosis.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

ASANA_PAT = os.getenv("ASANA_PAT")
TARGET_GID = "1213235375126350"

if not ASANA_PAT:
    print("ERROR: ASANA_PAT not set")
    sys.exit(1)

FULL_OPT_FIELDS = [
    "name", "notes",
    "custom_fields",
    "custom_fields.name",
    "custom_fields.gid",
    "custom_fields.resource_subtype",
    "custom_fields.text_value",
    "custom_fields.number_value",
    "custom_fields.display_value",
    "custom_fields.enum_value",
    "custom_fields.enum_options",
    "custom_fields.multi_enum_values",
    "memberships.project.gid",
]


def extract_value(cf: dict) -> object:
    """Extract display-ready value from a custom field dict."""
    subtype = cf.get("resource_subtype", "?")
    if subtype == "text":
        return cf.get("text_value")
    elif subtype == "number":
        return cf.get("number_value")
    elif subtype == "enum":
        ev = cf.get("enum_value")
        return ev.get("name") if isinstance(ev, dict) else None
    elif subtype == "multi_enum":
        mv = cf.get("multi_enum_values") or []
        return [m.get("name") for m in mv if isinstance(m, dict)]
    else:
        return cf.get("display_value")


def dump_fields(task_data: dict, label: str, fields_of_interest: list[str]):
    """Print custom field values from task data."""
    print(f"\n  [{label}] Task: {task_data.get('name')}")
    for cf in task_data.get("custom_fields", []):
        name = cf.get("name", "?")
        if name not in fields_of_interest:
            continue
        subtype = cf.get("resource_subtype", "?")
        gid = cf.get("gid", "?")
        val = extract_value(cf)
        print(f"    [{subtype:12s}] {name:30s} GID={gid}  value={val!r}")


async def main():
    from autom8_asana.cache.models.entry import EntryType
    from autom8_asana.client import AsanaClient
    from autom8_asana.core.entity_registry import get_registry
    from autom8_asana.resolution.write_registry import EntityWriteRegistry
    from autom8_asana.services.field_write_service import FieldWriteService

    # =========================================================
    # PHASE 0: Discover enum/multi_enum options
    # =========================================================
    print("=" * 70)
    print("PHASE 0: Discover available enum/multi_enum options")
    print("=" * 70)

    client_0 = AsanaClient(token=ASANA_PAT)
    task_data = await client_0.tasks.get_async(
        TARGET_GID, raw=True, opt_fields=FULL_OPT_FIELDS,
    )

    # Find enum and multi_enum fields with their options
    enum_fields = {}
    multi_enum_fields = {}
    for cf in task_data.get("custom_fields", []):
        name = cf.get("name", "")
        subtype = cf.get("resource_subtype", "")
        if subtype == "enum":
            options = [
                {"name": o.get("name"), "gid": o.get("gid"), "enabled": o.get("enabled", True)}
                for o in (cf.get("enum_options") or [])
                if o.get("name")
            ]
            enabled = [o for o in options if o["enabled"]]
            if enabled:
                enum_fields[name] = enabled
                print(f"\n  ENUM: {name} ({len(enabled)} options)")
                for o in enabled[:8]:
                    print(f"    - {o['name']!r} (GID: {o['gid']})")
                if len(enabled) > 8:
                    print(f"    ... and {len(enabled) - 8} more")
        elif subtype == "multi_enum":
            options = [
                {"name": o.get("name"), "gid": o.get("gid"), "enabled": o.get("enabled", True)}
                for o in (cf.get("enum_options") or [])
                if o.get("name")
            ]
            enabled = [o for o in options if o["enabled"]]
            if enabled:
                multi_enum_fields[name] = enabled
                print(f"\n  MULTI_ENUM: {name} ({len(enabled)} options)")
                for o in enabled[:8]:
                    print(f"    - {o['name']!r} (GID: {o['gid']})")
                if len(enabled) > 8:
                    print(f"    ... and {len(enabled) - 8} more")

    # Pick test values
    # Enum: Language (common offer field)
    enum_field = None
    enum_value = None
    for candidate in ["Language", "Campaign Type", "Optimize For", "Vertical"]:
        if candidate in enum_fields and len(enum_fields[candidate]) >= 2:
            enum_field = candidate
            enum_value = enum_fields[candidate][0]["name"]
            break

    # Multi-enum: Platforms or Targeting Strategies
    multi_field = None
    multi_values = None
    for candidate in ["Platforms", "Targeting Strategies", "Specialty"]:
        if candidate in multi_enum_fields and len(multi_enum_fields[candidate]) >= 2:
            multi_field = candidate
            multi_values = [
                multi_enum_fields[candidate][0]["name"],
                multi_enum_fields[candidate][1]["name"],
            ]
            break

    print(f"\n  Selected enum test:       {enum_field} = {enum_value!r}")
    print(f"  Selected multi_enum test: {multi_field} = {multi_values!r}")

    if not enum_field:
        print("\n  FATAL: No suitable enum field found!")
        return
    if not multi_field:
        print("\n  FATAL: No suitable multi_enum field found!")
        return

    # Map display names to descriptor names for FieldWriteService
    descriptor_map = {
        "Language": "language",
        "Campaign Type": "campaign_type",
        "Optimize For": "optimize_for",
        "Vertical": "vertical",
        "Platforms": "platforms",
        "Targeting Strategies": "targeting_strategies",
        "Specialty": "specialty",
    }

    INTEREST = [
        "Asset ID", "Campaign ID", "Weekly Ad Spend", "Offer Headline",
        "Internal Notes", enum_field, multi_field,
    ]

    # =========================================================
    # PHASE A: Baseline
    # =========================================================
    print("\n" + "=" * 70)
    print("PHASE A: Baseline read")
    print("=" * 70)

    client_a = AsanaClient(token=ASANA_PAT)
    baseline = await client_a.tasks.get_async(
        TARGET_GID, raw=True, opt_fields=FULL_OPT_FIELDS,
    )
    dump_fields(baseline, "BASELINE", INTEREST)

    # =========================================================
    # PHASE B: Write ALL types via FieldWriteService
    # =========================================================
    print("\n" + "=" * 70)
    print("PHASE B: FieldWriteService — text + number + enum + multi_enum + core")
    print("=" * 70)

    client_b = AsanaClient(token=ASANA_PAT)
    write_registry = EntityWriteRegistry(get_registry())
    service = FieldWriteService(client_b, write_registry)

    fields_to_write = {
        # Text
        "asset_id": "SPIKE-ENUM-PROOF-001",
        "campaign_id": "CAMP-ENUM-TEST",
        "offer_headline": "Spike Enum+MultiEnum Write Verified",
        "internal_notes": "All field types verified by spike_write_diagnosis.py",
        # Number
        "weekly_ad_spend": 1234.56,
        # Enum (by option NAME, not GID)
        descriptor_map[enum_field]: enum_value,
        # Multi-enum (by option NAMES, not GIDs)
        descriptor_map[multi_field]: multi_values,
        # Core
        "name": "[E2E Proof] NOW - ALL FIELD TYPES VERIFIED",
    }

    print(f"\n  Writing {len(fields_to_write)} fields:")
    for k, v in fields_to_write.items():
        print(f"    {k}: {v!r}")

    client_b.tasks._cache_invalidate(TARGET_GID, [EntryType.TASK])

    result = await service.write_async(
        entity_type="offer",
        gid=TARGET_GID,
        fields=fields_to_write,
        include_updated=True,
    )

    print(f"\n  Result: {result.fields_written} written, {result.fields_skipped} skipped")
    for rf in result.field_results:
        icon = "OK" if rf.status == "resolved" else "SKIP" if rf.status == "skipped" else "ERR"
        gid_str = rf.gid or "(core)"
        print(f"    [{icon:4s}] {rf.input_name:25s} -> {rf.matched_name!r:30s} gid={gid_str} val={rf.value!r}")
        if rf.error:
            print(f"           ERROR: {rf.error}")
        if rf.suggestions:
            print(f"           SUGGESTIONS: {rf.suggestions}")

    print(f"\n  include_updated response:")
    if result.updated_fields:
        for k, v in result.updated_fields.items():
            print(f"    {k}: {v!r}")
    else:
        print("    None!")

    # =========================================================
    # PHASE C: Fresh client verification
    # =========================================================
    print("\n" + "=" * 70)
    print("PHASE C: Fresh client verification")
    print("=" * 70)

    client_c = AsanaClient(token=ASANA_PAT)
    verify = await client_c.tasks.get_async(
        TARGET_GID, raw=True, opt_fields=FULL_OPT_FIELDS,
    )
    dump_fields(verify, "POST-WRITE", INTEREST)

    # =========================================================
    # PHASE D: Raw httpx verification
    # =========================================================
    print("\n" + "=" * 70)
    print("PHASE D: Raw httpx GET (SDK bypass)")
    print("=" * 70)

    import httpx

    async with httpx.AsyncClient() as http:
        resp = await http.get(
            f"https://app.asana.com/api/1.0/tasks/{TARGET_GID}",
            headers={"Authorization": f"Bearer {ASANA_PAT}"},
            params={
                "opt_fields": ",".join([
                    "name",
                    "custom_fields.name",
                    "custom_fields.text_value",
                    "custom_fields.number_value",
                    "custom_fields.resource_subtype",
                    "custom_fields.display_value",
                    "custom_fields.enum_value",
                    "custom_fields.multi_enum_values",
                ])
            },
        )
        print(f"  HTTP {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            print(f"  name: {data.get('name')}")
            for cf in data.get("custom_fields", []):
                name = cf.get("name", "")
                if name in INTEREST:
                    val = extract_value(cf)
                    st = cf.get("resource_subtype", "?")
                    print(f"    [{st:12s}] {name:30s} = {val!r}")

    # =========================================================
    # PHASE E: Before/after comparison
    # =========================================================
    print("\n" + "=" * 70)
    print("PHASE E: Before/After comparison")
    print("=" * 70)

    def extract_cf_map(td):
        m = {}
        for cf in td.get("custom_fields", []):
            m[cf.get("name", "")] = extract_value(cf)
        return m

    before = extract_cf_map(baseline)
    after = extract_cf_map(verify)

    print(f"\n  {'Field':30s}  {'BEFORE':35s}  {'AFTER':35s}  CHANGED")
    print(f"  {'-'*30}  {'-'*35}  {'-'*35}  -------")
    for field in INTEREST:
        b = repr(before.get(field))
        a = repr(after.get(field))
        ch = "YES" if before.get(field) != after.get(field) else ""
        print(f"  {field:30s}  {b:35s}  {a:35s}  {ch}")

    print(f"\n  Core 'name':")
    print(f"    BEFORE: {baseline.get('name')!r}")
    print(f"    AFTER:  {verify.get('name')!r}")

    # =========================================================
    # Verdict
    # =========================================================
    print("\n" + "=" * 70)
    all_changed = all(
        before.get(f) != after.get(f)
        for f in INTEREST
    )
    if all_changed and result.fields_written == len(fields_to_write):
        print("VERDICT: ALL FIELD TYPES WRITE CORRECTLY")
        print(f"  text:       OK (4 fields)")
        print(f"  number:     OK (1 field)")
        print(f"  enum:       OK ({enum_field} = {enum_value!r})")
        print(f"  multi_enum: OK ({multi_field} = {multi_values!r})")
        print(f"  core:       OK (name)")
    else:
        failed = [f for f in INTEREST if before.get(f) == after.get(f)]
        print(f"VERDICT: FAILURES DETECTED")
        print(f"  Written: {result.fields_written}/{len(fields_to_write)}")
        print(f"  Unchanged fields: {failed}")

    print(f"\nVerify in Asana: https://app.asana.com/0/1143843662099250/{TARGET_GID}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
