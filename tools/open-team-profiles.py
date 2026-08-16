#!/usr/bin/env python3

import argparse
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
TEAMS_PATH = PROJECT_DIR / "teams" / "teams.json"
PROFILE_URL = "https://qoj.ac/user/profile/{}"

sys.path.insert(0, str(PROJECT_DIR))

from scoreboard_parsers.teams import qoj_username_map

def load_usernames():
    return list(qoj_username_map(TEAMS_PATH).values())


def main():
    parser = argparse.ArgumentParser(
        description="Open every QOJ team profile listed in teams/teams.json."
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="seconds to wait between opening tabs (default: 0.5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print profile URLs without opening the browser",
    )
    args = parser.parse_args()

    if args.delay < 0:
        parser.error("--delay cannot be negative")

    usernames = load_usernames()
    if not usernames:
        parser.error(f"no non-empty usernames found in {TEAMS_PATH}")

    for index, username in enumerate(usernames):
        url = PROFILE_URL.format(quote(username, safe=""))
        print(url, flush=True)

        if not args.dry_run:
            webbrowser.open_new_tab(url)
            if index < len(usernames) - 1:
                time.sleep(args.delay)

    action = "Listed" if args.dry_run else "Opened"
    print(f"{action} {len(usernames)} QOJ team profiles.")


if __name__ == "__main__":
    main()
