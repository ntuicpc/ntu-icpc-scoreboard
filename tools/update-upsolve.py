#!/usr/bin/env python3

import argparse
import sys
from datetime import datetime
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
ARCHIVE_DIR = PROJECT_DIR / "archive"

sys.path.insert(0, str(PROJECT_DIR))

from archive_utils import archive_name
from scoreboard_parsers.io import load_json, write_json_atomic


def update_upsolve(upsolve, team_name, problem_id):
    if upsolve.get("contest-type") != "qoj":
        raise RuntimeError("Upsolve updates are only supported for QOJ archives")

    teams = [team for team in upsolve["teams"] if team["name"] == team_name]
    if not teams:
        raise RuntimeError(f"Team not found in upsolve scoreboard: {team_name}")
    if len(teams) != 1:
        raise RuntimeError(f"Duplicate team in upsolve scoreboard: {team_name}")

    team = teams[0]
    matches = [
        (label, result)
        for label, result in team["problems"].items()
        if int(result["problem-id"]) == problem_id
    ]
    if not matches:
        raise RuntimeError(f"Problem ID {problem_id} not found for team {team_name}")
    if len(matches) != 1:
        raise RuntimeError(f"Duplicate problem ID {problem_id} for team {team_name}")

    label, result = matches[0]
    old_status = result["status"]
    if old_status == "contest-solved":
        return label, old_status, old_status
    if old_status not in {"unsolved", "upsolved"}:
        raise RuntimeError(f"Unsupported upsolve status: {old_status}")
    new_status = "upsolved" if old_status == "unsolved" else "unsolved"
    result["status"] = new_status

    for current_team in upsolve["teams"]:
        results = current_team["problems"].values()
        current_team["contest-solved"] = sum(
            result["status"] == "contest-solved" for result in results
        )
        current_team["upsolved"] = sum(
            result["status"] == "upsolved" for result in current_team["problems"].values()
        )
        current_team["total-solved"] = (
            current_team["contest-solved"] + current_team["upsolved"]
        )

    upsolve["teams"].sort(
        key=lambda current_team: (
            -current_team["total-solved"],
            -current_team["upsolved"],
            current_team["contest-rank"] is None,
            current_team["contest-rank"] or 0,
            current_team["name"].casefold(),
        )
    )
    for rank, current_team in enumerate(upsolve["teams"], start=1):
        current_team["rank"] = rank

    upsolve["update-time"] = datetime.now().astimezone().strftime("%Y/%m/%d %H:%M:%S")
    return label, old_status, new_status


def main():
    parser = argparse.ArgumentParser(
        description="Toggle one problem between unsolved and upsolved, then rerank a QOJ upsolve scoreboard."
    )
    parser.add_argument("archive_name", type=archive_name, help="folder name under archive")
    parser.add_argument("team_name", help="team name shown on the upsolve scoreboard")
    parser.add_argument("problem_id", type=int, help="QOJ problem ID")
    args = parser.parse_args()

    archive_path = ARCHIVE_DIR / args.archive_name
    if not archive_path.is_dir():
        parser.error(f"archive directory not found: {archive_path}")

    output_path = archive_path / "upsolve.json"
    try:
        upsolve = load_json(output_path)
        label, old_status, new_status = update_upsolve(
            upsolve, args.team_name, args.problem_id
        )
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        parser.error(str(error))

    if old_status == "contest-solved":
        print(
            f"Skipped {args.team_name} problem {label} ({args.problem_id}): "
            "already contest-solved"
        )
        return

    write_json_atomic(output_path, upsolve)
    print(
        f"Updated {args.team_name} problem {label} ({args.problem_id}): "
        f"{old_status} -> {new_status}"
    )
    print(f"Reranked {len(upsolve['teams'])} teams in {output_path}")


if __name__ == "__main__":
    main()
