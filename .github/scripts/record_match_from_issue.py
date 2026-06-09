from __future__ import annotations

import os
import re
import sys
import csv
from pathlib import Path

sys.path.insert(0, ".")
from ELO_Calculator import (
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
        for row in csv.DictReader(f):
            if row["SailRanksID"]:
                players[row["SailRanksID"].strip()] = row
    return players


def save_players(players):
    with FILE_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PLAYER_FIELDS)
        writer.writeheader()
        writer.writerows(players.values())


def str_val(v):
    """Safely convert a field value (may be float or str) to a stripped string."""
    return str(v).strip() if v is not None else ""


def get_or_init_elo(player_row):
    val = str_val(player_row.get("Current", ""))
    return float(val) if val else STARTING_ELO


def k_factor(player_row):
    return 32.0 if not str_val(player_row.get("Current", "")) else 20.0


def update_tracking(player_row, new_rating):
    lowest  = float(str_val(player_row["Lowest"]))       if str_val(player_row["Lowest"])       else new_rating
    highest = float(str_val(player_row["Highest"]))      if str_val(player_row["Highest"])      else new_rating
    pm_high = float(str_val(player_row["PastMonthHigh"])) if str_val(player_row["PastMonthHigh"]) else new_rating
    pm_low  = float(str_val(player_row["PastMonthLow"]))  if str_val(player_row["PastMonthLow"])  else new_rating
    player_row["Lowest"]        = str(round(min(lowest,  new_rating), 2))
    player_row["Highest"]       = str(round(max(highest, new_rating), 2))
    player_row["Current"]       = str(round(new_rating, 2))
    player_row["PastMonthHigh"] = str(round(max(pm_high, new_rating), 2))
    player_row["PastMonthLow"]  = str(round(min(pm_low,  new_rating), 2))


def extract_field(label, text):
    pattern = r"### " + re.escape(label) + r"\s*[\r\n]+(.*?)(?=\s*###|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped and stripped.lower() != "_no response_":
            return stripped
    return None


def parse_score(score_str):
    score_str = score_str.strip()
    m = re.match(r"^(\d+)\s*[-:]\s*(\d+)$", score_str)
    if not m:
        raise ValueError("Invalid score format '{}'. Expected e.g. '2-1' or '2:1'.".format(score_str))
    a, b = int(m.group(1)), int(m.group(2))
    if a == 0 and b == 0:
        raise ValueError("Score 0-0 is not valid - at least one race must have been sailed.")
    return a, b


def expand_score_to_races(a_pts, b_pts, id_a, id_b):
    if a_pts > b_pts:
        return [id_a] * a_pts + [id_b] * b_pts
    elif b_pts > a_pts:
        return [id_b] * b_pts + [id_a] * a_pts
    else:
        winners = []
        for i in range(a_pts + b_pts):
            winners.append(id_a if i % 2 == 0 else id_b)
        return winners


def elo_expected(ra, rb):
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def elo_update(ra, rb, score_a, k):
    ea = elo_expected(ra, rb)
    eb = 1.0 - ea
    return round(ra + k * (score_a - ea), 2), round(rb + k * ((1.0 - score_a) - eb), 2)


# ---------------------------------------------------------------------------
# Parse issue
# ---------------------------------------------------------------------------
body         = os.environ.get("ISSUE_BODY", "")
issue_number = os.environ.get("ISSUE_NUMBER", "1")

print("--- RAW ISSUE BODY ---")
print(repr(body))
print("--- END BODY ---")

id_a_raw  = extract_field("Sailor A SailRanks ID", body)
id_b_raw  = extract_field("Sailor B SailRanks ID", body)
score_raw = extract_field("Score (Sailor A - Sailor B)", body)
event     = extract_field("Event Name", body)
date_str  = extract_field("Date", body)

print("Parsed: id_a={!r} id_b={!r} score={!r} event={!r} date={!r}".format(
    id_a_raw, id_b_raw, score_raw, event, date_str))

if not all([id_a_raw, id_b_raw, score_raw, event, date_str]):
    print("ERROR: Could not parse all required fields from issue body.")
    sys.exit(1)

try:
    id_a = clean_sailranks_id(id_a_raw)
    id_b = clean_sailranks_id(id_b_raw)
except ValueError as e:
    print("ERROR: {}".format(e))
    sys.exit(1)

try:
    a_pts, b_pts = parse_score(score_raw)
except ValueError as e:
    print("ERROR: {}".format(e))
    sys.exit(1)

total_races = a_pts + b_pts
print("Score: {}-{} -> {} race(s)".format(a_pts, b_pts, total_races))

# ---------------------------------------------------------------------------
# Load players
# ---------------------------------------------------------------------------
players = load_players()

if id_a not in players:
    print("ERROR: Sailor A (ID {}) not found in ELO_Database.csv. Add them first.".format(id_a))
    sys.exit(1)
if id_b not in players:
    print("ERROR: Sailor B (ID {}) not found in ELO_Database.csv. Add them first.".format(id_b))
    sys.exit(1)

row_a = players[id_a]
row_b = players[id_b]

# ---------------------------------------------------------------------------
# Determine next match ID
# ---------------------------------------------------------------------------
ensure_match_history_csv()
existing_ids = []
with MATCH_HISTORY_PATH.open("r", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        m = re.match(r"M(\d+)", row.get("MatchID", ""))
        if m:
            existing_ids.append(int(m.group(1)))
next_num = (max(existing_ids) + 1) if existing_ids else 1

# ---------------------------------------------------------------------------
# Expand score into races and apply ELO updates
# ---------------------------------------------------------------------------
race_sequence = expand_score_to_races(a_pts, b_pts, id_a, id_b)
new_rows = []

for winner_id in race_sequence:
    score_a = 1.0 if winner_id == id_a else 0.0

    ra_pre = get_or_init_elo(row_a)
    rb_pre = get_or_init_elo(row_b)
    k = (k_factor(row_a) + k_factor(row_b)) / 2.0

    ea = elo_expected(ra_pre, rb_pre)
    eb = 1.0 - ea
    ra_post, rb_post = elo_update(ra_pre, rb_pre, score_a, k)

    mid = "M{}".format(str(next_num).zfill(5))
    next_num += 1

    new_rows.append({
        "MatchID":      mid,
        "Event":        event,
        "Date":         date_str,
        "SailorA_ID":   id_a,
        "SailorB_ID":   id_b,
        "Winner_ID":    winner_id,
        "RatingA_Pre":  ra_pre,
        "RatingB_Pre":  rb_pre,
        "ExpectedA":    round(ea, 4),
        "ExpectedB":    round(eb, 4),
        "RatingA_Post": ra_post,
        "RatingB_Post": rb_post,
    })

    update_tracking(row_a, ra_post)
    update_tracking(row_b, rb_post)

save_players(players)

with MATCH_HISTORY_PATH.open("a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=MATCH_HISTORY_FIELDS)
    writer.writerows(new_rows)

winner_name = row_a["Name"] if a_pts > b_pts else (row_b["Name"] if b_pts > a_pts else "Tied")
print("SUCCESS: {} race(s) recorded ({} - {}).".format(total_races, new_rows[0]["MatchID"], new_rows[-1]["MatchID"]))
print("  Result: {} {} - {} {} | Overall winner: {}".format(
    row_a["Name"], a_pts, b_pts, row_b["Name"], winner_name))
print("  {}: {} -> {}".format(row_a["Name"], new_rows[0]["RatingA_Pre"], str_val(row_a["Current"])))
print("  {}: {} -> {}".format(row_b["Name"], new_rows[0]["RatingB_Pre"], str_val(row_b["Current"])))
