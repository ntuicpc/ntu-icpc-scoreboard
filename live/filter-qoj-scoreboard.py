#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

LIVE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = LIVE_DIR.parent
HTML_PATH = LIVE_DIR / "standings.html"
TIMESTAMP_PATH = LIVE_DIR / "standings.timestamp"
SCOREBOARD_PATH = LIVE_DIR / "scoreboard.json"
TEAMS_PATH = PROJECT_DIR / "teams" / "teams.json"
UNOFFICIAL_TEAMS_PATH = PROJECT_DIR / "teams" / "unofficial.json"
sys.path.insert(0, str(PROJECT_DIR))

from scoreboard_parsers.io import write_json_atomic
from scoreboard_parsers.qoj import parse_scoreboard
from scoreboard_parsers.teams import qoj_live_team_filter
from state import LIVE_SCOREBOARD_TITLE


def main():
    parser = argparse.ArgumentParser(description="Filter the downloaded QOJ scoreboard.")
    parser.add_argument("frozen", type=int, choices=(0, 1), help="apply freeze (0 or 1)")
    parser.add_argument(
        "contest_elapsed_minutes",
        type=int,
        help="elapsed time of the current contest in minutes",
    )
    args = parser.parse_args()
    if args.contest_elapsed_minutes < 0:
        parser.error("contest_elapsed_minutes cannot be negative")

    print(
        f"[QOJ] Filtering live scoreboard (frozen={args.frozen}, "
        f"elapsed={args.contest_elapsed_minutes}m)...",
        flush=True,
    )
    team_filter, unofficial_teamnames = qoj_live_team_filter(
        TEAMS_PATH, UNOFFICIAL_TEAMS_PATH
    )
    scoreboard = parse_scoreboard(
        HTML_PATH.read_text(encoding="utf-8"),
        LIVE_SCOREBOARD_TITLE,
        team_filter,
        frozen=bool(args.frozen),
        update_time=TIMESTAMP_PATH.read_text(encoding="utf-8").strip(),
        unofficial_teamnames=unofficial_teamnames,
        contest_elapsed_minutes=args.contest_elapsed_minutes,
    )
    write_json_atomic(SCOREBOARD_PATH, scoreboard)
    print(
        f"[QOJ] Live scoreboard updated: {len(scoreboard['problems'])} problems, "
        f"{len(scoreboard['teams'])} teams.", flush=True,
    )


if __name__ == "__main__":
    main()
