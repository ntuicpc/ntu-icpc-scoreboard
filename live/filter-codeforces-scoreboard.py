#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path


LIVE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = LIVE_DIR.parent
HTML_PATH = LIVE_DIR / "standings.html"
TIMESTAMP_PATH = LIVE_DIR / "standings.timestamp"
SCOREBOARD_PATH = LIVE_DIR / "scoreboard.json"
PROBLEM_PATH = LIVE_DIR / "problem.json"
TEAMS_PATH = PROJECT_DIR / "teams" / "teams.json"
UNOFFICIAL_TEAMS_PATH = PROJECT_DIR / "teams" / "unofficial.json"

sys.path.insert(0, str(PROJECT_DIR))

from scoreboard_parsers.io import write_json_pair_atomic
from scoreboard_parsers.codeforces import parse_scoreboard
from scoreboard_parsers.teams import codeforces_live_team_filter
from state import LIVE_SCOREBOARD_TITLE


def main():
    parser = argparse.ArgumentParser(
        description="Filter the downloaded Codeforces scoreboard."
    )
    args = parser.parse_args()

    html = HTML_PATH.read_text(encoding="utf-8")
    timestamp = TIMESTAMP_PATH.read_text(encoding="utf-8").strip()
    team_filter, unofficial_teamnames = codeforces_live_team_filter(
        TEAMS_PATH, UNOFFICIAL_TEAMS_PATH
    )
    scoreboard, problem_map = parse_scoreboard(
        html,
        LIVE_SCOREBOARD_TITLE,
        team_filter,
        update_time=timestamp,
    )
    for team in scoreboard["teams"]:
        team["unofficial"] = team["name"] in unofficial_teamnames
    write_json_pair_atomic(
        PROBLEM_PATH, problem_map, SCOREBOARD_PATH, scoreboard
    )
    print(
        f"[Codeforces] Live scoreboard updated: "
        f"{len(scoreboard['problems'])} problems, {len(scoreboard['teams'])} teams.",
        flush=True,
    )


if __name__ == "__main__":
    main()
