from flask import Flask, abort, render_template_string, request
import argparse
import json
import re
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
ARCHIVE_NAME_PATTERN = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
YEAR_PATTERN = re.compile(r"^\d{4}$")

app = Flask(__name__)

with (PROJECT_DIR / "template" / "home.html").open("r", encoding="utf-8") as f:
    home_html = f.read()
with (PROJECT_DIR / "template" / "live-unavailable.html").open(
    "r", encoding="utf-8"
) as f:
    live_unavailable_html = f.read()
with (PROJECT_DIR / "template" / "scoreboard.html").open("r", encoding="utf-8") as f:
    scoreboard_html = f.read()
with (PROJECT_DIR / "template" / "upsolve-scoreboard.html").open("r", encoding="utf-8") as f:
    upsolve_scoreboard_html = f.read()
with (PROJECT_DIR / "template" / "year.html").open("r", encoding="utf-8") as f:
    year_html = f.read()


def format_contest_type(contest_type):
    normalized = str(contest_type or "").strip().lower()
    if normalized == "codeforces":
        return "Codeforces"
    if normalized == "domjudge":
        return "DOMjudge"
    if normalized == "qoj":
        return "QOJ"
    return "Unknown"


def render_scoreboard(html, scoreboard_path):
    try:
        with scoreboard_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        with (scoreboard_path.parent / "problem.json").open(
            "r", encoding="utf-8"
        ) as f:
            problem_map = json.load(f)
    except FileNotFoundError:
        abort(404)

    return render_template_string(
        html,
        problems=data["problems"],
        teams=data["teams"],
        last_update=data["update-time"],
        contest_id=data["contest-id"],
        title=data["title"],
        contest_url=data["contest-url"],
        problem_map=problem_map,
    )


def validate_archive_name(archive_name):
    if archive_name in {".", ".."} or Path(archive_name).name != archive_name:
        abort(404)


def is_live_enabled():
    try:
        with (PROJECT_DIR / "live" / "status.json").open(
            "r", encoding="utf-8"
        ) as f:
            return json.load(f).get("enabled") is True
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def load_archives():
    archive_dir = PROJECT_DIR / "archive"
    archives = []

    if not archive_dir.is_dir():
        return archives

    for archive_path in sorted(archive_dir.iterdir(), reverse=True):
        scoreboard_path = archive_path / "scoreboard.json"
        if not archive_path.is_dir() or not scoreboard_path.is_file():
            continue

        try:
            with scoreboard_path.open("r", encoding="utf-8") as f:
                scoreboard = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        name_match = ARCHIVE_NAME_PATTERN.fullmatch(archive_path.name)
        archives.append(
            {
                "name": archive_path.name,
                "title": scoreboard.get("title", archive_path.name),
                "has_upsolve": (archive_path / "upsolve.json").is_file(),
                "contest_type": format_contest_type(
                    scoreboard.get("contest-type")
                ),
                "year": name_match.group(1) if name_match else None,
                "date": (
                    f"{name_match.group(2)}/{name_match.group(3)}"
                    if name_match
                    else archive_path.name
                ),
                "scoreboard": scoreboard,
            }
        )

    return archives


@app.route("/")
def home():
    archives = load_archives()
    years = sorted(
        {archive["year"] for archive in archives if archive["year"]},
        reverse=True,
    )

    return render_template_string(
        home_html,
        archives=archives,
        years=years,
    )


@app.route("/year/<year>")
def year_scoreboard(year):
    if not YEAR_PATTERN.fullmatch(year):
        abort(404)

    mode = request.args.get("mode", "rank")
    if mode not in {"rank", "rating"}:
        abort(404)

    archives = [
        archive for archive in load_archives() if archive["year"] == year
    ]
    if not archives:
        abort(404)

    archives.reverse()
    teams = {}
    for archive in archives:
        for archived_team in archive["scoreboard"].get("teams", []):
            team_name = archived_team["name"]
            team = teams.setdefault(
                team_name,
                {
                    "name": team_name,
                    "ranks": {},
                    "ratings": {},
                    "first": 0,
                    "second": 0,
                    "third": 0,
                    "contests": 0,
                    "rating_sum": 0.0,
                    "rating_contests": 0,
                },
            )
            rank = archived_team["rank"]
            team["ranks"][archive["name"]] = rank
            team["contests"] += 1
            if rank == 1:
                team["first"] += 1
            elif rank == 2:
                team["second"] += 1
            elif rank == 3:
                team["third"] += 1

        rating_path = (
            PROJECT_DIR / "archive" / archive["name"] / "rating.json"
        )
        try:
            with rating_path.open("r", encoding="utf-8") as f:
                rating_data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        for rated_team in rating_data.get("teams", []):
            team_name = rated_team.get("name")
            if team_name not in teams:
                continue
            try:
                rating = float(rated_team["rating"])
            except (KeyError, TypeError, ValueError):
                continue
            team = teams[team_name]
            team["ratings"][archive["name"]] = rating
            team["rating_sum"] += rating
            team["rating_contests"] += 1

    yearly_teams = list(teams.values())
    for team in yearly_teams:
        if team["rating_contests"]:
            team["average_rating"] = round(
                team["rating_sum"] / team["rating_contests"],
                2,
            )
        else:
            team["average_rating"] = None
        del team["rating_sum"]

    if mode == "rating":
        yearly_teams.sort(
            key=lambda team: (
                team["average_rating"] is None,
                -(team["average_rating"] or 0),
                team["name"].casefold(),
            )
        )
    else:
        yearly_teams.sort(
            key=lambda team: (
                -team["first"],
                -team["second"],
                -team["third"],
                team["name"].casefold(),
            )
        )

    return render_template_string(
        year_html,
        year=year,
        archives=archives,
        teams=yearly_teams,
        mode=mode,
    )


@app.route("/live")
def scoreboard():
    if not is_live_enabled():
        return render_template_string(live_unavailable_html)

    scoreboard_path = PROJECT_DIR / "live" / "scoreboard.json"
    return render_scoreboard(scoreboard_html, scoreboard_path)


@app.route("/archive/<archive_name>")
def archived_scoreboard(archive_name):
    validate_archive_name(archive_name)

    scoreboard_path = (
        PROJECT_DIR / "archive" / archive_name / "scoreboard.json"
    )
    return render_scoreboard(scoreboard_html, scoreboard_path)


@app.route("/upsolve/<archive_name>")
def upsolve_scoreboard(archive_name):
    validate_archive_name(archive_name)

    scoreboard_path = (
        PROJECT_DIR / "archive" / archive_name / "upsolve.json"
    )
    return render_scoreboard(upsolve_scoreboard_html, scoreboard_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the QOJ scoreboard website."
    )
    parser.add_argument(
        "port",
        type=int,
        nargs="?",
        default=5000,
        help="port to listen on (default: 5000)",
    )
    args = parser.parse_args()

    app.run(
        host="0.0.0.0",
        port=args.port,
    )
