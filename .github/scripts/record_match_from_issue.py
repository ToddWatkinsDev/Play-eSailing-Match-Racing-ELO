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

STARTING_ELO = 1500.0
MATCH_HISTORY_PATH = Path("Match_History.csv")
MATCH_HISTORY_FIELDS = [
    "MatchID",
    "Event",
    "Date",
    "SailorA_ID",
    "SailorB_ID",
    "Winner_ID",
    "RatingA_Pre",
    "RatingB_Pre",
    "ExpectedA",
    "ExpectedB",
    "RatingA_Post",
    "RatingB_Post",
]


def ensure_match_history_csv():
    if not MATCH_HISTORY_PATH.exists():
        with MATCH_HISTORY_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MATCH_HISTORY_FIELDS)
            writer.writeheader()


def load_players():
    ensure_player_csv()
    players = {}
    with FILE_PATH.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["SailRanksID"]:
                players[row["SailRanksID"]] = row
    return players


def save_players(players: dict):
    with FILE_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PLAYER_FIELDS)
        writer.writeheader()
        writer.writerows(players.values())


def get_or_init_elo(player_row: dict) -> float:
    val = player_row.get("Current", "").strip()
    return float(val) if val else STARTING_ELO


def k_factor(player_row: dict) -> float:
    return 32.0 if not player_row.get("Current", "").strip() else 20.0


def update_tracking(player_row: dict, new_rating: float, now: datetime):
    lowest = float(player_row["Lowest"]) if player_row["Lowest"] else new_rating
    highest = float(player_row["Highest"]) if player_row["Highest"] else new_rating
    player_row["Lowest"] = round(min(lowest, new_rating), 2)
    player_row["Highest"] = round(max(highest, new_rating), 2)
    player_row["Current"] = round(new_rating, 2)
    pm_high = float(player_row["PastMonthHigh"]) if player_row["PastMonthHigh"] else new_rating
    pm_low = float(player_row["PastMonthLow"]) if player_row["PastMonthLow"] else new_rating
    player_row["PastMonthHigh"] = round(max(pm_high, new_rating), 2)
    player_row["PastMonthLow"] = round(min(pm_low, new_rating), 2)


def extract_field(label: str, text: str) -> str | None:
    pattern = rf"### {re.escape(label)}[\r\n]+([\r\n]+)?(.+?)(?=[\r\n]|$)"
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(2).strip()
    if value.lower() == "_no response_" or value == "":
        return None
    return value


# --- Parse issue body ---
body = os.environ.get("ISSUE_BODY", "")
issue_number = os.environ.get("ISSUE_NUMBER", "0")

print("--- RAW ISSUE BODY ---")
print(repr(body))
print("--- END BODY ---")

id_a_raw = extract_field("Sailor A SailRanks ID", body)
id_b_raw = extract_field("Sailor B SailRanks ID", body)
winner_raw = extract_field("Winner", body)
event = extract_field("Event Name", body)
date_str = extract_field("Date", body)

if not all([id_a_raw, id_b_raw, winner_raw, event, date_str]):
    print(f"ERROR: Could not parse issue body.")
    print(f"  id_a={id_a_raw!r} id_b={id_b_raw!r} winner={winner_raw!r} event={event!r} date={date_str!r}")
    sys.exit(1)

try:
    id_a = clean_sailranks_id(id_a_raw)
    id_b = clean_sailranks_id(id_b_raw)
except ValueError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

winner_normalised = winner_raw.strip().lower()
if winner_normalised == "sailor a":
    score_a = 1.0
elif winner_normalised == "sailor b":
    score_a = 0.0
else:
    print(f"ERROR: Unrecognised winner value '{winner_raw}'.")
    sys.exit(1)

winner_id = id_a if score_a == 1.0 else id_b

# --- Load players and validate both exist ---
players = load_players()

if id_a not in players:
    print(f"ERROR: Sailor A (ID {id_a}) not found in ELO_Database.csv. Add them first.")
    sys.exit(1)

if id_b not in players:
    print(f"ERROR: Sailor B (ID {id_b}) not found in ELO_Database.csv. Add them first.")
    sys.exit(1)

row_a = players[id_a]
row_b = players[id_b]

rating_a_pre = get_or_init_elo(row_a)
rating_b_pre = get_or_init_elo(row_b)
k = (k_factor(row_a) + k_factor(row_b)) / 2

expected_a = 1 / (1 + 10 ** ((rating_b_pre - rating_a_pre) / 400))
expected_b = 1 - expected_a

rating_a_post, rating_b_post = update_elo(rating_a_pre, rating_b_pre, score_a, k)

now = datetime.utcnow()
update_tracking(row_a, rating_a_post, now)
update_tracking(row_b, rating_b_post, now)

save_players(players)

# --- Append to match history ---
ensure_match_history_csv()
match_id = f"M{issue_number.zfill(5)}"

match_row = {
    "MatchID": match_id,
    "Event": event,
    "Date": date_str,
    "SailorA_ID": id_a,
    "SailorB_ID": id_b,
    "Winner_ID": winner_id,
    "RatingA_Pre": round(rating_a_pre, 2),
    "RatingB_Pre": round(rating_b_pre, 2),
    "ExpectedA": round(expected_a, 4),
    "ExpectedB": round(expected_b, 4),
    "RatingA_Post": round(rating_a_post, 2),
    "RatingB_Post": round(rating_b_post, 2),
}

with MATCH_HISTORY_PATH.open("a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=MATCH_HISTORY_FIELDS)
    writer.writerow(match_row)

print(f"SUCCESS: Match {match_id} recorded.")
print(f"  {id_a}: {round(rating_a_pre,2)} -> {round(rating_a_post,2)}")
print(f"  {id_b}: {round(rating_b_pre,2)} -> {round(rating_b_post,2)}")
