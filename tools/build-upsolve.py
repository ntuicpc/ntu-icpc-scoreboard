#!/usr/bin/env python3

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
ARCHIVE_DIR = PROJECT_DIR / "archive"
TEAMS_DIR = PROJECT_DIR / "teams"
TEAMS_PATH = TEAMS_DIR / "teams.json"
PROBLEM_URL_PATTERN = re.compile(r"^/problem/(\d+)$")
CONTEST_SOLVED_STATUSES = {"accepted", "first-solve"}

sys.path.insert(0, str(PROJECT_DIR))

from archive_utils import archive_name
from scoreboard_parsers.io import load_json, write_json_atomic
from scoreboard_parsers.teams import qoj_username_map


def parse_accepted_problems(path):
    try:
        html = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise RuntimeError(f"User profile HTML not found: {path}") from error

    soup = BeautifulSoup(html, "html.parser")
    page_title = soup.title.get_text(" ", strip=True) if soup.title else ""
    if " - User profile - QOJ.ac" not in page_title:
        raise RuntimeError(f"Saved HTML is not a QOJ user profile: {path}")

    heading = next(
        (
            element
            for element in soup.select("h4.list-group-item-heading")
            if element.get_text(" ", strip=True).startswith("Accepted problems")
        ),
        None,
    )
    if heading is None:
        return set()

    problem_list = heading.find_next_sibling("p")
    if problem_list is None:
        raise RuntimeError(f"Cannot find Accepted problems list in {path}")

    accepted = set()
    for link in problem_list.find_all("a", href=True):
        match = PROBLEM_URL_PATTERN.fullmatch(link["href"])
        if match:
            accepted.add(int(match.group(1)))

    return accepted


def load_team_accounts():
    return qoj_username_map(TEAMS_PATH, require_all=True)


def ensure_qoj_archive(scoreboard):
    if scoreboard.get("contest-type") != "qoj":
        raise RuntimeError(
            "Upsolve generation is only supported for QOJ archives: "
            f"{scoreboard.get('contest-url', 'unknown contest')}"
        )


def build_upsolve(archive_path):
    scoreboard = load_json(archive_path / "scoreboard.json")
    ensure_qoj_archive(scoreboard)
    problem_map = load_json(archive_path / "problem.json")
    team_accounts = load_team_accounts()

    problems = scoreboard["problems"]
    missing_problems = [problem for problem in problems if problem not in problem_map]
    if missing_problems:
        raise RuntimeError(
            "Missing QOJ problem IDs in problem.json: " + ", ".join(missing_problems)
        )

    accepted_by_username = {}
    upsolve_teams = []

    for archived_team in scoreboard["teams"]:
        teamname = archived_team["name"]
        if teamname not in team_accounts:
            raise RuntimeError(f"Team {teamname!r} is missing from teams.json")

        username = team_accounts[teamname]
        if username not in accepted_by_username:
            accepted_by_username[username] = parse_accepted_problems(
                TEAMS_DIR / f"{username}.html"
            )
        accepted = accepted_by_username[username]

        problem_results = {}
        contest_solved = 0
        upsolved = 0

        for problem in problems:
            problem_data = problem_map[problem]
            problem_id = int(problem_data["id"])
            problem_url = problem_data["url"]
            contest_result = archived_team["problems"][problem]

            if contest_result["status"] in CONTEST_SOLVED_STATUSES:
                status = "contest-solved"
                contest_solved += 1
            elif problem_id in accepted:
                status = "upsolved"
                upsolved += 1
            else:
                status = "unsolved"

            problem_results[problem] = {
                "problem-id": problem_id,
                "url": problem_url,
                "status": status,
            }

        upsolve_teams.append(
            {
                "rank": 0,
                "name": teamname,
                "username": username,
                "problems": problem_results,
                "contest-solved": contest_solved,
                "upsolved": upsolved,
                "total-solved": contest_solved + upsolved,
                "contest-rank": archived_team["rank"],
            }
        )

    upsolve_teams.sort(
        key=lambda team: (
            -team["total-solved"],
            -team["upsolved"],
            team["contest-rank"],
        )
    )
    for rank, team in enumerate(upsolve_teams, start=1):
        team["rank"] = rank

    return {
        "problems": problems,
        "teams": upsolve_teams,
        "update-time": datetime.now().astimezone().strftime("%Y/%m/%d %H:%M:%S"),
        "contest-id": scoreboard["contest-id"],
        "contest-url": scoreboard["contest-url"],
        "title": f"{scoreboard['title']} - Upsolve",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Build an upsolve scoreboard from saved QOJ user profiles."
    )
    parser.add_argument(
        "archive_name",
        type=archive_name,
        help="folder name under archive, for example 20251129",
    )
    args = parser.parse_args()

    archive_path = ARCHIVE_DIR / args.archive_name
    if not archive_path.is_dir():
        parser.error(f"archive directory not found: {archive_path}")

    try:
        result = build_upsolve(archive_path)
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        parser.error(str(error))

    output_path = archive_path / "upsolve.json"
    write_json_atomic(output_path, result)

    print(f"Upsolve scoreboard saved to {output_path}")
    print(f"Processed {len(result['teams'])} teams.")


if __name__ == "__main__":
    main()
