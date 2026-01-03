#!/usr/bin/env python3
"""Simple debug script to check Vertical field presence."""
import os
import sys
import requests

pat = os.environ.get("TF_VAR_asana_pat")
if not pat:
    print("ERROR: TF_VAR_asana_pat not set")
    sys.exit(1)

project_gid = "1201081073731555"

headers = {
    "Authorization": f"Bearer {pat}",
    "Content-Type": "application/json"
}

# Get sections
url = f"https://app.asana.com/api/1.0/projects/{project_gid}/sections"
resp = requests.get(url, headers=headers)
sections = resp.json()["data"]
print(f"Found {len(sections)} sections")

# Get tasks from first non-template section
for section in sections:
    if "template" in section["name"].lower():
        continue

    print(f"\nChecking section: {section['name']}")

    # Get tasks with custom fields
    url = f"https://app.asana.com/api/1.0/sections/{section['gid']}/tasks"
    params = {
        "opt_fields": "name,parent.gid,parent.name,custom_fields,custom_fields.name,custom_fields.display_value,custom_fields.enum_value.name,custom_fields.resource_subtype",
        "limit": 5
    }
    resp = requests.get(url, headers=headers, params=params)
    tasks = resp.json()["data"]

    print(f"Got {len(tasks)} tasks")

    for task in tasks:
        print(f"\n--- {task['name']} ---")
        if task.get("parent"):
            print(f"Parent: {task['parent'].get('name', 'N/A')}")

        # Check for Vertical field
        vertical_found = False
        office_phone_found = False

        for cf in task.get("custom_fields", []):
            cf_name = cf.get("name", "")
            cf_value = cf.get("display_value")

            if "vertical" in cf_name.lower():
                vertical_found = True
                enum_val = cf.get("enum_value")
                enum_name = enum_val.get("name") if enum_val else None
                print(f"  VERTICAL: {cf_name} = display:{cf_value} enum:{enum_name}")

            if "office" in cf_name.lower() and "phone" in cf_name.lower():
                office_phone_found = True
                print(f"  OFFICE PHONE: {cf_name} = {cf_value}")

        if not vertical_found:
            print("  [NO Vertical field on task]")
        if not office_phone_found:
            print("  [NO Office Phone field on task]")

    # Only check first real section
    break
