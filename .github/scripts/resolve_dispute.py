import os
import re
import sys
import csv
from pathlib import Path
from datetime import datetime

sys.path.insert(0, ".")
from ELO_Calculator import (
    update_elo,
    clean_sailranks_id,
    ensure_player_csv,
    FILE_PATH,
    PLAYER_FIELDS,
)

DISPUTES_PATH = Path("Disputes.csv")
HISTORY_PATH = Path("Match_History.csv")
MATCH_HISTORY_FIELDS = [
    "MatchID", "Event", "Date", "SailorA_ID", "SailorB_ID", "Winner_ID",
    "RatingA_Pre", "RatingB_Pre", "ExpectedA", "ExpectedB",
    "RatingA_Post", "RatingB_Post",
]
DISPUTE_FIELDS = [
    "DisputeIssue", "MatchID", "DisputedBy", "Reason", "Details",
    "Status", "RaisedAt", "ResolvedAt", "ResolvedBy", "ResolutionOutcome",
]


def extract_field(label: str, text: str) -> str | None:
    pattern = rf"### {re.escape(label)}[\r\n]+([\r\n]+)?(.+?)(?=[\r\n]|$)"
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(2).strip()
    if value.lower() == "_no response_" or value == "":
        return None
    return value


def load_players() -> dict:
    ensure_player_csv()
    players = {}
    with FILE_PATH.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["SailRanksID"]:
                players[row["SailRanksID"]] = row
    return players


def save_players(players: dict):
    with FILE_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PLAYER_FIELDS)
        writer.writeheader()
        writer.writerows(players.values())


def load_history() -> list:
    if not HISTORY_PATH.exists():
        return []
    with HISTORY_PATH.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_history(rows: list):
    with HISTORY_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MATCH_HISTORY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def revert_match(match_row: dict, players: dict):
    """Restore both sailors' ratings to their pre-match values."""
    id_a = match_row["SailorA_ID"]
    id_b = match_row["SailorB_ID"]
    if id_a in players:
        players[id_a]["Current"] = match_row["RatingA_Pre"]
    if id_b in players:
        players[id_b]["Current"] = match_row["RatingB_Pre"]


def rerecord_match(match_row: dict, players: dict, corrected_winner_id: str) -> dict:
    """Revert then re-apply with the corrected winner."""
    id_a = match_row["SailorA_ID"]
    id_b = match_row["SailorB_ID"]
    rating_a = float(match_row["RatingA_Pre"])
    rating_b = float(match_row["RatingB_Pre"])

    score_a = 1.0 if corrected_winner_id == id_a else 0.0
    k = 20.0  # use established K for corrections

    new_a, new_b = update_elo(rating_a, rating_b, score_a, k)

    if id_a in players:
        players[id_a]["Current"] = round(new_a, 2)
    if id_b in players:
        players[id_b]["Current"] = round(new_b, 2)

    return {
        **match_row,
        "Winner_ID": corrected_winner_id,
        "RatingA_Post": round(new_a, 2),
        "RatingB_Post": round(new_b, 2),
    }


# --- Parse issue ---
body = os.environ.get("ISSUE_BODY", "")
issue_number = os.environ.get("ISSUE_NUMBER", "0")

print("--- RAW ISSUE BODY ---")
print(repr(body))
print("--- END BODY ---")

dispute_issue = extract_field("Dispute Issue Number", body)
match_id = extract_field("Match ID", body)
outcome_raw = extract_field("Outcome", body)
corrected_winner_raw = extract_field("Corrected Winner SailRanks ID", body)
admin_raw = extract_field("Admin SailRanks ID", body)

if not all([dispute_issue, match_id, outcome_raw, admin_raw]):
    print("ERROR: Could not parse resolve body.")
    sys.exit(1)

try:
    admin_id = clean_sailranks_id(admin_raw)
except ValueError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

outcome = outcome_raw.strip().lower()

# --- Load data ---
players = load_players()
history = load_history()

match_row = next((r for r in history if r["MatchID"] == match_id), None)
if not match_row:
    print(f"ERROR: Match {match_id} not found in Match_History.csv.")
    sys.exit(1)

# --- Apply outcome ---
if "dismiss" in outcome:
    print(f"Dispute dismissed — result for {match_id} stands.")

elif "re-record" in outcome or "corrected winner" in outcome:
    if not corrected_winner_raw:
        print("ERROR: Corrected winner SailRanks ID is required for re-record outcome.")
        sys.exit(1)
    try:
        corrected_winner = clean_sailranks_id(corrected_winner_raw)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    updated_row = rerecord_match(match_row, players, corrected_winner)
    history = [updated_row if r["MatchID"] == match_id else r for r in history]
    save_history(history)
    save_players(players)
    print(f"Match {match_id} re-recorded with corrected winner {corrected_winner}.")

elif "revert" in outcome:
    revert_match(match_row, players)
    history = [r for r in history if r["MatchID"] != match_id]
    save_history(history)
    save_players(players)
    print(f"Match {match_id} reverted and removed from history.")

else:
    print(f"ERROR: Unrecognised outcome '{outcome_raw}'.")
    sys.exit(1)

# --- Update dispute log ---
if DISPUTES_PATH.exists():
    with DISPUTES_PATH.open("r", newline="", encoding="utf-8") as f:
        disputes = list(csv.DictReader(f))

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    for row in disputes:
        if row["DisputeIssue"] == dispute_issue or row["MatchID"] == match_id:
            row["Status"] = "Resolved"
            row["ResolvedAt"] = now
            row["ResolvedBy"] = admin_id
            row["ResolutionOutcome"] = outcome_raw

    with DISPUTES_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DISPUTE_FIELDS)
        writer.writeheader()
        writer.writerows(disputes)

print(f"SUCCESS: Dispute {dispute_issue} resolved by admin {admin_id}.")
