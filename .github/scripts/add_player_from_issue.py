import os
import re
import sys

sys.path.insert(0, ".")
from ELO_Calculator import add_player

body = os.environ.get("ISSUE_BODY", "")

name_match = re.search(r"### Sailor Name\s+([^\n]+)", body)
id_match = re.search(r"### SailRanks ID\s+([^\n]+)", body)

if not name_match or not id_match:
    print("ERROR: Could not parse issue body.")
    print("Body received:")
    print(body)
    sys.exit(1)

name = name_match.group(1).strip()
sailranks_id = id_match.group(1).strip()

try:
    result = add_player(name, sailranks_id)
except ValueError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if result:
    print(f"SUCCESS: Added player '{name}' with SailRanks ID '{sailranks_id}'.")
else:
    print(f"SKIPPED: Player with SailRanks ID '{sailranks_id}' already exists.")
