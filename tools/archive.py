#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
ARCHIVE_DIR = PROJECT_DIR / "archive"
TEAMS_PATH = PROJECT_DIR / "teams" / "teams.json"
LIVE_SCOREBOARD_PATH = PROJECT_DIR / "live" / "scoreboard.json"
LIVE_PROBLEM_PATH = PROJECT_DIR / "live" / "problem.json"
VALID_CONTEST_TYPES = {"codeforces", "domjudge", "qoj"}

sys.path.insert(0, str(PROJECT_DIR))

from archive_utils import archive_name, write_archive
from scoreboard_parsers.codeforces import (
    load_team_filter as load_codeforces_team_filter,
)
from scoreboard_parsers.codeforces import (
    parse_scoreboard as parse_codeforces_scoreboard,
)
from scoreboard_parsers.io import load_json
from scoreboard_parsers.qoj import build_problem_map
from scoreboard_parsers.qoj import load_team_filter as load_qoj_team_filter
from scoreboard_parsers.qoj import parse_scoreboard as parse_qoj_scoreboard


def existing_html(value):
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"HTML file not found: {path}")
    return path


def add_common_archive_arguments(parser, include_html=True):
    parser.add_argument("archive_id", type=archive_name, help="archive folder name")
    parser.add_argument("title", help="scoreboard title")
    if include_html:
        parser.add_argument("html", type=existing_html, help="saved standings HTML")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create an archive from QOJ, Codeforces, or the current Live scoreboard."
    )
    subparsers = parser.add_subparsers(dest="source", required=True)

    qoj_parser = subparsers.add_parser(
        "qoj",
        help="archive a saved QOJ standings page",
    )
    add_common_archive_arguments(qoj_parser)
    qoj_parser.add_argument("id_l", type=int, help="QOJ problem ID for the first problem")
    qoj_parser.add_argument("id_r", type=int, help="QOJ problem ID for the last problem")

    codeforces_parser = subparsers.add_parser(
        "codeforces",
        help="archive a saved Codeforces standings page",
    )
    add_common_archive_arguments(codeforces_parser)

    live_parser = subparsers.add_parser(
        "live",
        help="archive the current Live scoreboard",
    )
    add_common_archive_arguments(live_parser, include_html=False)

    return parser.parse_args()


def archive_qoj(args):
    scoreboard = parse_qoj_scoreboard(
        args.html.read_text(encoding="utf-8"),
        args.title,
        load_qoj_team_filter(TEAMS_PATH),
        frozen=False,
    )
    problem_map = build_problem_map(
        scoreboard["problems"],
        scoreboard["contest-id"],
        args.id_l,
        args.id_r,
    )
    return write_archive(
        ARCHIVE_DIR,
        args.archive_id,
        scoreboard,
        problem_map,
    ), scoreboard


def archive_codeforces(args):
    scoreboard, problem_map = parse_codeforces_scoreboard(
        args.html.read_text(encoding="utf-8"),
        args.title,
        load_codeforces_team_filter(TEAMS_PATH),
    )
    return write_archive(
        ARCHIVE_DIR,
        args.archive_id,
        scoreboard,
        problem_map,
    ), scoreboard


def archive_live(args):
    scoreboard = load_json(LIVE_SCOREBOARD_PATH)
    problem_map = load_json(LIVE_PROBLEM_PATH)
    contest_type = scoreboard.get("contest-type")
    if contest_type not in VALID_CONTEST_TYPES:
        expected = ", ".join(sorted(VALID_CONTEST_TYPES))
        raise RuntimeError(
            f"Invalid live contest-type {contest_type!r}; expected one of: {expected}"
        )
    scoreboard["title"] = args.title
    return write_archive(
        ARCHIVE_DIR,
        args.archive_id,
        scoreboard,
        problem_map,
    ), scoreboard


def main():
    args = parse_args()
    archivers = {
        "qoj": archive_qoj,
        "codeforces": archive_codeforces,
        "live": archive_live,
    }
    try:
        destination, scoreboard = archivers[args.source](args)
    except (KeyError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        raise SystemExit(f"archive.py: error: {error}") from error

    print(f"[Archive] Saved to: {destination}")
    print(
        f"[Archive] Type: {scoreboard['contest-type']}; "
        f"{len(scoreboard['problems'])} problems, "
        f"{len(scoreboard['teams'])} teams."
    )


if __name__ == "__main__":
    main()
