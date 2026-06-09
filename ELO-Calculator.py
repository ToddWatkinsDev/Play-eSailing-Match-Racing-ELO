

def update_elo(rating_a: float, rating_b: float, score_a: float, k: float = 20) -> tuple[float, float]:
    """
    Update Elo ratings for a 1v1 match.

    Args:
        rating_a: Current Elo rating for sailor A
        rating_b: Current Elo rating for sailor B
        score_a: Actual result for sailor A
                 1.0 = A wins
                 0.5 = draw
                 0.0 = A loses
        k: K-factor controlling rating sensitivity

    Returns:
        (new_rating_a, new_rating_b)
    """
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1 - expected_a

    score_b = 1 - score_a

    new_rating_a = rating_a + k * (score_a - expected_a)
    new_rating_b = rating_b + k * (score_b - expected_b)

    return new_rating_a, new_rating_b


import csv
from pathlib import Path

FILE_PATH = Path("ELO-Database.csv")

PLAYER_FIELDS = [
    "Name",
    "SailRanksID",
    "Lowest",
    "Highest",
    "PastMonthHigh",
    "PastMonthLow",
    "Current",
]

def clean_sailranks_id(sailranks_id: str) -> str:
    """
    Keep only numeric characters from a SailRanksID.
    Example: 'SR12345' -> '12345'
    """
    cleaned = "".join(char for char in str(sailranks_id) if char.isdigit())

    if not cleaned:
        raise ValueError("SailRanksID must contain at least one number")

    return cleaned

def ensure_player_csv() -> None:
    if not FILE_PATH.exists():
        with FILE_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=PLAYER_FIELDS)
            writer.writeheader()

def player_exists(sailranks_id: str) -> bool:
    ensure_player_csv()
    cleaned_id = clean_sailranks_id(sailranks_id)

    with FILE_PATH.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing_id = clean_sailranks_id(row["SailRanksID"]) if row["SailRanksID"] else ""
            if existing_id == cleaned_id:
                return True

    return False

def add_player(name: str, sailranks_id: str) -> bool:
    ensure_player_csv()
    cleaned_id = clean_sailranks_id(sailranks_id)

    if player_exists(cleaned_id):
        return False

    row = {
        "Name": name.strip(),
        "SailRanksID": cleaned_id,
        "Lowest": "",
        "Highest": "",
        "PastMonthHigh": "",
        "PastMonthLow": "",
        "Current": "",
    }

    with FILE_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PLAYER_FIELDS)
        writer.writerow(row)

    return True