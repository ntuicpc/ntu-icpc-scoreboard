import re
from datetime import datetime

from bs4 import BeautifulSoup

from scoreboard_parsers.common import (
    mark_first_solves,
    sort_and_assign_ranks,
    time_to_minutes,
)
from scoreboard_parsers.teams import qoj_name_map


FREEZE_TIME_MINUTES = 240
QOJ_STANDINGS_URL = re.compile(
    r"^https://(?:www\.)?qoj\.ac/results/QOJ(\d+)/?(?:\?.*)?$"
)


def parse_standings_url(value):
    match = QOJ_STANDINGS_URL.fullmatch(value)
    if match is None:
        raise ValueError("expected a QOJ standings URL such as https://qoj.ac/results/QOJ1771")
    return int(match.group(1))


def load_team_filter(teams_path):
    return qoj_name_map(teams_path)


def match_team(name, team_filter):
    if team_filter is None:
        return name
    for original_name, teamname in team_filter.items():
        if original_name in name:
            return teamname
    return None


def parse_mark(mark):
    if mark.startswith("*+"):
        suffix = mark[2:]
        return "accepted", int(suffix) if suffix else 0
    if mark.startswith("+"):
        suffix = mark[1:]
        return "accepted", int(suffix) if suffix else 0
    if mark == "-":
        return "unattempted", 0
    if re.fullmatch(r"-\d+", mark):
        return "attempted", int(mark[1:])
    print(f"[QOJ] Warning: unrecognized scoreboard mark: {mark}")
    return "unattempted", 0


def parse_scoreboard(html, title, team_filter, frozen=False, update_time=None):
    soup = BeautifulSoup(html, "html.parser")
    contest_link = soup.find("a", href=re.compile(r"/contest/\d+"))
    if contest_link is None:
        raise RuntimeError("Cannot find QOJ contest link")
    contest_match = re.search(r"/contest/(\d+)", contest_link["href"])
    if contest_match is None:
        raise RuntimeError("Cannot parse QOJ contest ID")
    contest_id = int(contest_match.group(1))

    table = soup.select_one("table.standings")
    if table is None:
        raise RuntimeError("Cannot find QOJ standings table")
    rows = table.select("tbody > tr")
    if not rows:
        raise RuntimeError("QOJ standings table is empty")

    header_cells = rows[0].find_all(["th", "td"], recursive=False)
    headers = [cell.get_text("\n", strip=True) for cell in header_cells]
    try:
        solved_index = next(
            index for index, header in enumerate(headers)
            if header.splitlines()[0] == "Solved"
        )
    except StopIteration as error:
        raise RuntimeError("Cannot find Solved column") from error

    problems = [headers[index].splitlines()[0] for index in range(2, solved_index)]
    teams = []
    for row in rows[1:]:
        cells = row.find_all("td", recursive=False)
        if len(cells) != len(headers):
            continue
        rank_text = cells[0].get_text(" ", strip=True)
        if not rank_text.isdigit():
            continue
        teamname = match_team(cells[1].get_text(" ", strip=True), team_filter)
        if teamname is None:
            continue

        team = {
            "rank": int(rank_text), "name": teamname, "problems": {},
            "solved": 0, "penalty": 0,
        }
        for column, problem in enumerate(problems, start=2):
            parts = list(cells[column].stripped_strings)
            mark = parts[0] if parts else "-"
            submit_time = parts[1] if len(parts) >= 2 else None
            status, wrong_attempts = parse_mark(mark)
            if frozen and submit_time is not None and time_to_minutes(submit_time) >= FREEZE_TIME_MINUTES:
                if status == "accepted":
                    wrong_attempts += 1
                status = "frozen"
            team["problems"][problem] = {
                "status": status, "wrong_attempts": wrong_attempts,
                "time": submit_time,
            }

        for result in team["problems"].values():
            if result["status"] == "accepted":
                team["solved"] += 1
                team["penalty"] += (
                    time_to_minutes(result["time"]) + 20 * result["wrong_attempts"]
                )
        teams.append(team)

    mark_first_solves(teams, problems)
    sort_and_assign_ranks(teams)
    if update_time is None:
        update_time = datetime.now().astimezone().strftime("%Y/%m/%d %H:%M:%S")
    return {
        "problems": problems,
        "teams": teams,
        "update-time": update_time,
        "contest-id": contest_id,
        "contest-url": f"https://qoj.ac/contest/{contest_id}",
        "contest-type": "qoj",
        "title": title,
    }


def build_problem_map(problems, contest_id, id_l, id_r):
    if id_l > id_r:
        raise RuntimeError("id_l must be less than or equal to id_r")
    problem_ids = list(range(id_l, id_r + 1))
    if len(problem_ids) != len(problems):
        raise RuntimeError(
            f"Problem ID range contains {len(problem_ids)} IDs, "
            f"but the standings contains {len(problems)} problems"
        )
    return {
        problem: {
            "id": problem_id,
            "url": f"https://qoj.ac/contest/{contest_id}/problem/{problem_id}",
        }
        for problem, problem_id in zip(problems, problem_ids)
    }
