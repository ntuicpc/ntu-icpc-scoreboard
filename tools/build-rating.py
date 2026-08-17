#!/usr/bin/env python3

import argparse
import json
import sys
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
ARCHIVE_DIR = PROJECT_DIR / "archive"
ALPHA = 1.07
GP5_BONUS = {
    1: 10,
    2: 6,
    3: 3,
    4: 2,
    5: 1,
}
RATING_PRECISION = Decimal("0.01")

sys.path.insert(0, str(PROJECT_DIR))

from archive_utils import archive_name
from scoreboard_parsers.io import load_json, write_json_atomic


def load_scoreboard(archive_path):
    scoreboard_path = archive_path / "scoreboard.json"
    try:
        return load_json(scoreboard_path)
    except RuntimeError as error:
        raise RuntimeError(f"Cannot load scoreboard: {error}") from error


def build_rating(scoreboard):
    teams = scoreboard.get("teams")
    if not isinstance(teams, list) or not teams:
        raise RuntimeError("Scoreboard does not contain any teams")

    try:
        first_solved = max(int(team["solved"]) for team in teams)
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Every team must have an integer solved value") from error

    minimum_penalty = {}
    normalized_teams = []
    for team in teams:
        try:
            solved = int(team["solved"])
            penalty = int(team["penalty"])
            name = team["name"]
            rank = int(team["rank"])
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(
                "Every team must have name, rank, solved, and penalty values"
            ) from error

        if solved < 0 or penalty < 0:
            raise RuntimeError(f"Team {name!r} has a negative solved or penalty value")

        normalized_teams.append(
            {
                "name": name,
                "rank": rank,
                "solved": solved,
                "penalty": penalty,
            }
        )
        minimum_penalty[solved] = min(
            minimum_penalty.get(solved, penalty),
            penalty,
        )

    rating_teams = []
    for team in normalized_teams:
        penalty = team["penalty"]
        group_minimum = minimum_penalty[team["solved"]]
        if penalty == 0:
            penalty_ratio = 1.0
        else:
            penalty_ratio = group_minimum / penalty

        exponent = team["solved"] - first_solved + penalty_ratio - 1
        rating = (
            90 * pow(ALPHA, exponent)
            + GP5_BONUS.get(team["rank"], 0)
        )

        rating_teams.append(
            {
                **team,
                "rating": float(
                    Decimal(str(rating)).quantize(
                        RATING_PRECISION,
                        rounding=ROUND_DOWN,
                    )
                ),
            }
        )

    return {
        "archive-id": scoreboard.get("archive-id"),
        "contest-id": scoreboard.get("contest-id"),
        "title": scoreboard.get("title"),
        "update-time": datetime.now().astimezone().strftime("%Y/%m/%d %H:%M:%S"),
        "teams": rating_teams,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Build team ratings for an archived scoreboard."
    )
    parser.add_argument(
        "archive_id",
        type=archive_name,
        help="folder name under archive, for example 20251129",
    )
    args = parser.parse_args()

    archive_path = ARCHIVE_DIR / args.archive_id
    if not archive_path.is_dir():
        parser.error(f"archive directory not found: {archive_path}")

    try:
        scoreboard = load_scoreboard(archive_path)
        rating = build_rating(scoreboard)
        rating["archive-id"] = args.archive_id
        output_path = archive_path / "rating.json"
        write_json_atomic(output_path, rating)
    except RuntimeError as error:
        parser.error(str(error))

    print(f"Rating saved to {output_path}")
    print(
        f"Processed {len(rating['teams'])} teams; "
        f"highest solved count: {max(team['solved'] for team in rating['teams'])}."
    )


if __name__ == "__main__":
    main()
