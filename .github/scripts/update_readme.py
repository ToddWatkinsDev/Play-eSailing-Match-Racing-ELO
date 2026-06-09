import csv
import re
from pathlib import Path
from datetime import datetime

DB_PATH = Path("ELO_Database.csv")
HISTORY_PATH = Path("Match_History.csv")
README_PATH = Path("README.md")

TOP_N = 10
RECENT_N = 2


def load_players() -> dict:
    players = {}
    if not DB_PATH.exists():
        return players
    with DB_PATH.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["SailRanksID"] and row["Current"]:
                players[row["SailRanksID"]] = row
    return players


def load_history() -> list:
    if not HISTORY_PATH.exists():
        return []
    with HISTORY_PATH.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def medal(rank: int) -> str:
    return ["🥇", "🥈", "🥉"].get(rank - 1, f"{rank}")


def build_leaderboard(players: dict) -> str:
    if not players:
        return "_No players with ratings yet._"

    ranked = sorted(
        players.values(),
        key=lambda r: float(r["Current"]),
        reverse=True,
    )[:TOP_N]

    lines = [
        "| Rank | Sailor | Rating | Highest | Lowest |",
        "|------|--------|--------|---------|--------|",
    ]
    for i, row in enumerate(ranked, 1):
        rating = float(row["Current"])
        highest = float(row["Highest"]) if row["Highest"] else rating
        lowest = float(row["Lowest"]) if row["Lowest"] else rating
        lines.append(
            f"| {medal(i)} | {row['Name']} | **{rating:.0f}** | {highest:.0f} | {lowest:.0f} |"
        )

    updated = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
    lines.append(f"")
    lines.append(f"_Last updated: {updated}_")
    return "\n".join(lines)


def build_recent_matches(history: list, players: dict) -> str:
    if not history:
        return "_No matches recorded yet._"

    recent = history[-RECENT_N:]
    recent.reverse()  # most recent first

    def name(sid: str) -> str:
        return players.get(sid, {}).get("Name", sid)

    def delta(pre: str, post: str) -> str:
        d = float(post) - float(pre)
        return f"+{d:.0f}" if d >= 0 else f"{d:.0f}"

    lines = [
        "| Match | Event | Date | Winner | Result |",
        "|-------|-------|------|--------|--------|",
    ]
    for row in recent:
        a = name(row["SailorA_ID"])
        b = name(row["SailorB_ID"])
        winner = name(row["Winner_ID"])
        loser = b if row["Winner_ID"] == row["SailorA_ID"] else a
        da = delta(row["RatingA_Pre"], row["RatingA_Post"])
        db = delta(row["RatingB_Pre"], row["RatingB_Post"])
        a_part = f"{a} ({da})"
        b_part = f"{b} ({db})"
        result = f"🏆 **{winner}** def. {loser}"
        lines.append(
            f"| {row['MatchID']} | {row['Event']} | {row['Date']} | {result} | {a_part} vs {b_part} |"
        )

    return "\n".join(lines)


def inject_section(content: str, start_tag: str, end_tag: str, new_body: str) -> str:
    pattern = rf"({re.escape(start_tag)}).*?({re.escape(end_tag)})"
    replacement = rf"\1\n{new_body}\n\2"
    return re.sub(pattern, replacement, content, flags=re.DOTALL)


players = load_players()
history = load_history()

readme = README_PATH.read_text(encoding="utf-8")

readme = inject_section(
    readme,
    "<!-- LEADERBOARD_START -->",
    "<!-- LEADERBOARD_END -->",
    build_leaderboard(players),
)

readme = inject_section(
    readme,
    "<!-- RECENT_MATCHES_START -->",
    "<!-- RECENT_MATCHES_END -->",
    build_recent_matches(history, players),
)

README_PATH.write_text(readme, encoding="utf-8")
print("README updated successfully.")
