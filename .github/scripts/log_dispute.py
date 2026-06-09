import os
import re
import sys
import csv
from pathlib import Path
from datetime import datetime

sys.path.insert(0, ".")
from ELO_Calculator import clean_sailranks_id

DISPUTES_PATH = Path("Disputes.csv")
DISPUTE_FIELDS = [
    "DisputeIssue",
    "MatchID",
    "DisputedBy",
    "Reason",
    "Details",
    "Status",
    "RaisedAt",
    "ResolvedAt",
    "ResolvedBy",
    "ResolutionOutcome",
]


def ensure_disputes_csv():
    if not DISPUTES_PATH.exists():
        with DISPUTES_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=DISPUTE_FIELDS)
            writer.writeheader()


def extract_field(label: str, text: str) -> str | None:
    pattern = rf"### {re.escape(label)}[\r\n]+([\r\n]+)?(.+?)(?=[\r\n]|$)"
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(2).strip()
    if value.lower() == "_no response_" or value == "":
        return None
    return value


body = os.environ.get("ISSUE_BODY", "")
issue_number = os.environ.get("ISSUE_NUMBER", "0")

print("--- RAW ISSUE BODY ---")
print(repr(body))
print("--- END BODY ---")

match_id = extract_field("Match ID", body)
disputed_by_raw = extract_field("Your SailRanks ID", body)
reason = extract_field("Reason for Dispute", body)
details = extract_field("Details", body)

if not all([match_id, disputed_by_raw, reason, details]):
    print(f"ERROR: Could not parse dispute body.")
    sys.exit(1)

try:
    disputed_by = clean_sailranks_id(disputed_by_raw)
except ValueError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

ensure_disputes_csv()

# Check for duplicate dispute on same match by same person
with DISPUTES_PATH.open("r", newline="", encoding="utf-8") as f:
    existing = list(csv.DictReader(f))

for row in existing:
    if row["MatchID"] == match_id and row["DisputedBy"] == disputed_by and row["Status"] == "Open":
        print(f"SKIPPED: An open dispute for match {match_id} by sailor {disputed_by} already exists.")
        sys.exit(0)

row = {
    "DisputeIssue": issue_number,
    "MatchID": match_id,
    "DisputedBy": disputed_by,
    "Reason": reason,
    "Details": details.replace("\n", " ").replace("\r", ""),
    "Status": "Open",
    "RaisedAt": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    "ResolvedAt": "",
    "ResolvedBy": "",
    "ResolutionOutcome": "",
}

with DISPUTES_PATH.open("a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=DISPUTE_FIELDS)
    writer.writerow(row)

print(f"SUCCESS: Dispute logged for match {match_id} by sailor {disputed_by}.")
