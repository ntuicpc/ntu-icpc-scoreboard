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
CODEFORCES_PROFILE_PATTERN = re.compile(r"^/profile/([^/]+)$")
CONTEST_SOLVED_STATUSES = {"accepted", "first-solve"}

sys.path.insert(0, str(PROJECT_DIR))

from archive_utils import archive_name
from scoreboard_parsers.io import load_json, write_json_atomic
from scoreboard_parsers.teams import codeforces_username_map, qoj_username_map


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


def require_team_accounts(accounts, teamnames, field_name):
    missing = sorted(teamname for teamname in teamnames if teamname not in accounts)
    if missing:
        raise RuntimeError(
            f"The following teams do not have {field_name} in teams.json: "
            + ", ".join(missing)
        )
    return accounts


def parse_codeforces_accepted_by_username(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.standings")
    if table is None:
        raise RuntimeError("Cannot find Codeforces standings table")

    show_unofficial = soup.select_one("#showUnofficial")
    if show_unofficial is not None and not show_unofficial.has_attr("checked"):
        raise RuntimeError(
            "The saved Codeforces standings does not include unofficial "
            "participants; enable 'show unofficial' before saving the HTML"
        )

    accepted_by_username = {}
    for row in table.select("tr[participantid]"):
        usernames = set()
        for link in row.select('a[href^="/profile/"]'):
            match = CODEFORCES_PROFILE_PATTERN.fullmatch(link.get("href", ""))
            if match:
                usernames.add(match.group(1).casefold())

        accepted = {
            int(cell["problemid"])
            for cell in row.select("td[problemid]")
            if cell.select_one(".cell-accepted") is not None
        }
        for username in usernames:
            accepted_by_username.setdefault(username, set()).update(accepted)

    problem_ids = {
        int(cell["problemid"])
        for cell in table.select("td[problemid]")
    }
    return accepted_by_username, problem_ids


def build_qoj_accepted_by_team(scoreboard):
    teamnames = [team["name"] for team in scoreboard["teams"]]
    team_accounts = require_team_accounts(
        qoj_username_map(TEAMS_PATH), teamnames, "qoj-username"
    )
    accepted_by_username = {}
    accepted_by_team = {}
    for teamname in teamnames:
        username = team_accounts[teamname]
        if username not in accepted_by_username:
            accepted_by_username[username] = parse_accepted_problems(
                TEAMS_DIR / f"{username}.html"
            )
        accepted_by_team[teamname] = accepted_by_username[username]
    return accepted_by_team


def build_codeforces_accepted_by_team(html_path, problem_map):
    try:
        html = html_path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError(
            f"Cannot read Codeforces standings HTML: {html_path}"
        ) from error
    except UnicodeDecodeError as error:
        raise RuntimeError(
            f"Codeforces standings HTML is not valid UTF-8: {html_path}"
        ) from error

    team_accounts = codeforces_username_map(TEAMS_PATH)
    accepted_by_username, standings_problem_ids = (
        parse_codeforces_accepted_by_username(html)
    )
    archive_problem_ids = {
        int(problem["id"]) for problem in problem_map.values()
    }
    if standings_problem_ids != archive_problem_ids:
        raise RuntimeError(
            "The saved Codeforces standings does not match this archive's problems"
        )

    accepted_by_team = {}
    for teamname, usernames in team_accounts.items():
        accepted = set()
        for username in usernames:
            accepted.update(
                accepted_by_username.get(username.casefold(), set())
            )
        accepted_by_team[teamname] = accepted
    return accepted_by_team

def build_upsolve(archive_path, codeforces_html_path=None):
    scoreboard = load_json(archive_path / "scoreboard.json")
    problem_map = load_json(archive_path / "problem.json")
    contest_type = scoreboard.get("contest-type")

    if contest_type == "qoj":
        if codeforces_html_path is not None:
            raise RuntimeError(
                "A standings HTML file should only be provided for "
                "Codeforces archives"
            )
        accepted_by_team = build_qoj_accepted_by_team(scoreboard)
    elif contest_type == "codeforces":
        if codeforces_html_path is None:
            raise RuntimeError(
                "Codeforces archives require a saved standings HTML file"
            )
        accepted_by_team = build_codeforces_accepted_by_team(
            codeforces_html_path, problem_map
        )
    else:
        raise RuntimeError(
            "Upsolve generation is only supported for QOJ and Codeforces archives: "
            f"{scoreboard.get('contest-url', 'unknown contest')}"
        )

    problems = scoreboard["problems"]
    missing_problems = [problem for problem in problems if problem not in problem_map]
    if missing_problems:
        raise RuntimeError(
            "Missing problem data in problem.json: " + ", ".join(missing_problems)
        )

    archived_teams = {team["name"]: team for team in scoreboard["teams"]}
    if contest_type == "codeforces":
        teamnames = accepted_by_team
    else:
        teamnames = archived_teams

    upsolve_teams = []
    for teamname in teamnames:
        archived_team = archived_teams.get(teamname)
        accepted = accepted_by_team[teamname]
        problem_results = {}
        contest_solved = 0
        upsolved = 0

        for problem in problems:
            problem_data = problem_map[problem]
            problem_id = int(problem_data["id"])
            problem_url = problem_data["url"]
            if archived_team is None:
                contest_result = {"status": "unattempted"}
            else:
                contest_result = archived_team["problems"].get(
                    problem, {"status": "unattempted"}
                )

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

        total_solved = contest_solved + upsolved
        if total_solved == 0:
            continue

        upsolve_teams.append(
            {
                "rank": 0,
                "name": teamname,
                "problems": problem_results,
                "contest-solved": contest_solved,
                "upsolved": upsolved,
                "total-solved": total_solved,
                "contest-rank": archived_team["rank"] if archived_team else None,
            }
        )

    upsolve_teams.sort(
        key=lambda team: (
            -team["total-solved"],
            -team["upsolved"],
            team["contest-rank"] is None,
            team["contest-rank"] or 0,
            team["name"].casefold(),
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
        "contest-type": contest_type,
        "title": f"{scoreboard['title']} - Upsolve",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Build an upsolve scoreboard for a QOJ or Codeforces archive."
    )
    parser.add_argument(
        "archive_name",
        type=archive_name,
        help="folder name under archive, for example 20251129",
    )
    parser.add_argument(
        "scoreboard_html",
        type=Path,
        nargs="?",
        help="saved Codeforces standings HTML (required for Codeforces archives)",
    )
    args = parser.parse_args()

    archive_path = ARCHIVE_DIR / args.archive_name
    if not archive_path.is_dir():
        parser.error(f"archive directory not found: {archive_path}")

    try:
        result = build_upsolve(archive_path, args.scoreboard_html)
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        parser.error(str(error))

    output_path = archive_path / "upsolve.json"
    write_json_atomic(output_path, result)

    print(f"Upsolve scoreboard saved to {output_path}")
    print(f"Processed {len(result['teams'])} teams.")


if __name__ == "__main__":
    main()
