import os
import re
import sys

sys.path.insert(0, ".")
from ELO_Calculator import add_player

body = os.environ.get("ISSUE_BODY", "")

print("--- RAW ISSUE BODY ---")
print(repr(body))
print("--- END BODY ---")


def extract_field(label: str, text: str) -> str | None:
    pattern = rf"### {re.escape(label)}\s*[\r\n]+(.*?)(?=\s*###|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped and stripped.lower() != "_no response_":
            return stripped
    return None


name = extract_field("Sailor Name", body)
sailranks_id = extract_field("SailRanks ID", body)

print(f"Parsed: name={name!r} sailranks_id={sailranks_id!r}")

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
