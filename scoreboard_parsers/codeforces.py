import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from scoreboard_parsers.common import mark_first_solves, sort_and_assign_ranks
from scoreboard_parsers.teams import codeforces_team_id_map


CODEFORCES_ORIGIN = "https://codeforces.com"
CODEFORCES_STANDINGS_URL = re.compile(
    r"^https://(?:www\.)?codeforces\.com/"
    r"(?:group/[^/]+/contest/\d+|contest/\d+|gym/\d+)/standings"
    r"(?:/groupmates/true)?/?(?:\?.*)?$"
)
TEAM_URL_PATTERN = re.compile(r"^/team/(\d+)$")
PROBLEM_URL_PATTERNS = (
    re.compile(r"^/group/[^/]+/contest/(\d+)/problem/([^/]+)$"),
    re.compile(r"^/contest/(\d+)/problem/([^/]+)$"),
    re.compile(r"^/gym/(\d+)/problem/([^/]+)$"),
)


def is_standings_url(value):
    return CODEFORCES_STANDINGS_URL.fullmatch(value) is not None


def public_standings_url(url):
    return url.replace("/standings/groupmates/true", "/standings", 1)


def load_team_filter(teams_path):
    return codeforces_team_id_map(teams_path)


def parse_problem_url(href):
    parsed = urlparse(href)
    path = parsed.path if parsed.scheme or parsed.netloc else href

    for pattern in PROBLEM_URL_PATTERNS:
        match = pattern.fullmatch(path)
        if match is None:
            continue

        return {
            "contest-id": int(match.group(1)),
            "problem": match.group(2),
            "url": urljoin(CODEFORCES_ORIGIN, path),
            "contest-url": urljoin(
                CODEFORCES_ORIGIN,
                path.rsplit("/problem/", 1)[0],
            ),
        }

    raise RuntimeError(f"Unsupported Codeforces problem URL: {href}")


def parse_rank(value):
    match = re.match(r"^\s*(\d+)", value)
    if match is None:
        raise ValueError(f"Cannot parse rank: {value!r}")
    return int(match.group(1))


def parse_scoreboard(html, title, team_filter, update_time=None):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.standings")
    if table is None:
        raise RuntimeError("Cannot find Codeforces standings table")

    rows = table.find_all("tr", recursive=False)
    if not rows:
        rows = table.select("tr")
    if not rows:
        raise RuntimeError("Codeforces standings table is empty")

    header_cells = rows[0].find_all("th", recursive=False)
    if len(header_cells) < 5:
        raise RuntimeError("Unexpected Codeforces standings header")

    problems = []
    problem_map = {}
    contest_id = None
    contest_url = None

    for header in header_cells[4:]:
        link = header.find("a", href=True)
        if link is None:
            continue

        problem_link = parse_problem_url(link["href"])
        label = problem_link["problem"]
        current_contest_id = problem_link["contest-id"]
        if contest_id is None:
            contest_id = current_contest_id
            contest_url = problem_link["contest-url"]
        elif (
            current_contest_id != contest_id
            or problem_link["contest-url"] != contest_url
        ):
            raise RuntimeError("Problem links belong to different contests")

        problems.append(label)
        problem_map[label] = {
            "id": label,
            "url": problem_link["url"],
        }

    if not problems or contest_id is None:
        raise RuntimeError("Cannot find Codeforces problems")

    for row in rows[1:]:
        cells = row.find_all("td", recursive=False)
        if len(cells) != 4 + len(problems):
            continue
        for index, problem in enumerate(problems, start=4):
            if cells[index].get("problemid") is not None:
                problem_map[problem]["id"] = int(cells[index]["problemid"])
        break

    teams = []
    expected_cell_count = 4 + len(problems)

    for row in rows[1:]:
        cells = row.find_all("td", recursive=False)
        if len(cells) != expected_cell_count:
            continue

        team_link = cells[1].select_one('a[href^="/team/"]')
        if team_link is None:
            continue
        team_match = TEAM_URL_PATTERN.fullmatch(team_link["href"])
        if team_match is None:
            continue

        team_id = int(team_match.group(1))
        if team_id not in team_filter:
            continue

        rank_text = cells[0].get_text(" ", strip=True)
        solved_text = cells[2].get_text(" ", strip=True)
        penalty_text = cells[3].get_text(" ", strip=True)
        if not (solved_text.isdigit() and penalty_text.isdigit()):
            continue

        try:
            original_rank = parse_rank(rank_text)
        except ValueError:
            continue

        team = {
            "rank": original_rank,
            "name": team_filter[team_id],
            "codeforces-team-id": team_id,
            "problems": {},
            "solved": int(solved_text),
            "penalty": int(penalty_text),
        }

        for index, problem in enumerate(problems, start=4):
            cell = cells[index]
            accepted = cell.select_one(".cell-accepted")
            rejected = cell.select_one(".cell-rejected")
            time_element = cell.select_one(".cell-time")

            if accepted is not None:
                mark = accepted.get_text(strip=True)
                status = "accepted"
                wrong_attempts = int(mark[1:]) if mark[1:] else 0
                submit_time = (
                    time_element.get_text(strip=True) if time_element else None
                )
            elif (
                rejected is not None
                and re.fullmatch(r"-\d+", rejected.get_text(strip=True))
            ):
                mark = rejected.get_text(strip=True)
                status = "attempted"
                wrong_attempts = int(mark[1:])
                submit_time = None
            else:
                status = "unattempted"
                wrong_attempts = 0
                submit_time = None

            team["problems"][problem] = {
                "status": status,
                "wrong_attempts": wrong_attempts,
                "time": submit_time,
            }

        teams.append(team)

    mark_first_solves(teams, problems)
    sort_and_assign_ranks(teams)

    if update_time is None:
        update_time = datetime.now().astimezone().strftime("%Y/%m/%d %H:%M:%S")

    scoreboard = {
        "problems": problems,
        "teams": teams,
        "update-time": update_time,
        "contest-id": contest_id,
        "contest-url": contest_url,
        "contest-type": "codeforces",
        "title": title,
    }
    return scoreboard, problem_map
