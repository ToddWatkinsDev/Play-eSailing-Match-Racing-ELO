# Play eSailing Match Racing ELO

Elo rating system for Play eSailing match racing. Ratings are updated automatically via GitHub Actions each time a match result is submitted.

---

## 🏆 Top 10 Leaderboard

<!-- LEADERBOARD_START -->
_No matches recorded yet._
<!-- LEADERBOARD_END -->

---

## 🕒 Recent Matches

<!-- RECENT_MATCHES_START -->
_No matches recorded yet._
<!-- RECENT_MATCHES_END -->

---

## How to use

- **Add a player** — open an issue using the [Add Player]( https://github.com/ToddWatkinsDev/Play-eSailing-Match-Racing-ELO/issues/new?template=add-player.yml) template
- **Record a match** — open an issue using the [Record Match](https://github.com/ToddWatkinsDev/Play-eSailing-Match-Racing-ELO/issues/new?template=record-match.yml) template
- Ratings update automatically within ~2 minutes of submission

## Rating system

- Starting rating: **1500**
- K-factor: **32** (provisional, first 10 matches) → **20** (established)
- Formula: standard Elo with pairwise 1v1 match racing results
