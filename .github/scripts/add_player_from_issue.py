import os
import re
import sys
sys.path.insert(0, ".")
from ELO_Calculator import add_player

body = os.environ.get("ISSUE_BODY", "")

name_match = re.search(r"### Sailor Name\s+(.+)", body)
id_match = re.search(r"### SailRanks ID\s+(.+)", body)

if not name_match or not id_match:
    print("Could not parse issue body")
    sys.exit(1)

name = name_match.group(1).strip()
sailranks_id = id_match.group(1).strip()

result = add_player(name, sailranks_id)
if result:
    print(f"Added: {name} ({sailranks_id})")
else:
    print(f"Already exists: {sailranks_id}")