import os
import re
import sys

sys.path.insert(0, ".")
from ELO_Calculator import add_player

body = os.environ.get("ISSUE_BODY", "")

# Debug: always print the raw body so failures are easy to diagnose
print("--- RAW ISSUE BODY ---")
print(repr(body))
print("--- END BODY ---")

# GitHub forms use CRLF and insert a blank line between the heading and value
# Pattern: ### Field Name\r\n\r\nValue  (or \n\n)
def extract_field(label: str, text: str) -> str | None:
    pattern = rf"### {re.escape(label)}[\r\n]+([\r\n]+)?(.+?)(?=[\r\n]|$)"
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(2).strip()
    if value.lower() == "_no response_" or value == "":
        return None
    return value

name = extract_field("Sailor Name", body)
sailranks_id = extract_field("SailRanks ID", body)

if not name or not sailranks_id:
    print(f"ERROR: Could not parse issue body. name={name!r} sailranks_id={sailranks_id!r}")
    sys.exit(1)

try:
    result = add_player(name, sailranks_id)
except ValueError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if result:
    print(f"SUCCESS: Added player '{name}' with SailRanks ID '{sailranks_id}'.")
else:
    print(f"SKIPPED: Player with SailRanks ID '{sailranks_id}' already exists.")
