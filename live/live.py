#!/usr/bin/env python3

import argparse
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


LIVE_DIR = Path(__file__).resolve().parent
UPDATE_INTERVAL_SECONDS = 60

QOJ_FROZEN_DURATION = timedelta(hours=5)
PROBLEM_PATH = LIVE_DIR / "problem.json"
STATUS_PATH = LIVE_DIR / "status.json"

sys.path.insert(0, str(LIVE_DIR.parent))

from state import set_live_status
from scoreboard_parsers.io import write_json_atomic
from scoreboard_parsers.codeforces import is_standings_url
from scoreboard_parsers.qoj import build_problem_map, parse_standings_url


def qoj_url(value):
    try:
        parse_standings_url(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error
    return value


def start_time(value):
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "expected ISO 8601 time, for example 2026-08-12T18:25:00+08:00"
        ) from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone(timedelta(hours=8)))
    return parsed

def codeforces_url(value):
    if not is_standings_url(value):
        raise argparse.ArgumentTypeError(
            "expected a Codeforces contest, gym, or group standings URL"
        )
    return value


def parse_args():
    parser = argparse.ArgumentParser(
        description="Start the QOJ or Codeforces Live scoreboard updater."
    )
    subparsers = parser.add_subparsers(dest="platform", required=True)

    qoj_parser = subparsers.add_parser(
        "qoj",
        help="use a QOJ standings URL",
    )
    qoj_parser.add_argument("url", type=qoj_url, help="QOJ standings URL")
    qoj_parser.add_argument(
        "start_time", type=start_time,
        help=(
            "contest start time in ISO 8601 format; timezone defaults to UTC+8, "
            "for example 2026-08-12T18:25:00"
        ),
    )
    qoj_parser.add_argument("id_l", type=int, help="first QOJ problem ID")
    qoj_parser.add_argument("id_r", type=int, help="last QOJ problem ID")

    codeforces_parser = subparsers.add_parser(
        "codeforces",
        help="use a Codeforces standings URL",
    )
    codeforces_parser.add_argument(
        "url",
        type=codeforces_url,
        help="Codeforces standings URL",
    )
    return parser.parse_args()


def enable_live(platform):
    set_live_status(STATUS_PATH, True, platform=platform)
    print("[Live] Live scoreboard is now enabled.", flush=True)


def create_qoj_problem_map(contest_id, id_l, id_r):
    if id_l > id_r:
        raise ValueError(
            "id_l must be less than or equal to id_r"
        )

    problem_count = id_r - id_l + 1
    if problem_count > 26:
        raise ValueError("at most 26 problems (A-Z) are supported")

    problems = [chr(ord("A") + index) for index in range(problem_count)]
    problem_map = build_problem_map(
        problems, contest_id, id_l, id_r
    )
    write_json_atomic(PROBLEM_PATH, problem_map)

    print(
        f"[QOJ] Problem map saved to {PROBLEM_PATH} "
        f"(A-{next(reversed(problem_map))}: "
        f"{id_l}-{id_r}).",
        flush=True,
    )


def run_qoj_update(url, contest_start_time):
    current_time = datetime.now().astimezone()
    frozen = int(current_time <= contest_start_time + QOJ_FROZEN_DURATION)

    print(
        f"[{current_time.isoformat(timespec='seconds')}] Updating QOJ scoreboard "
        f"(frozen={frozen})...",
        flush=True,
    )
    subprocess.run(
        [
            "xvfb-run",
            "-a",
            sys.executable,
            "get-qoj-scoreboard-data.py",
            url,
        ],
        cwd=LIVE_DIR,
        check=True,
    )
    subprocess.run(
        [sys.executable, "filter-qoj-scoreboard.py", str(frozen)],
        cwd=LIVE_DIR,
        check=True,
    )


def run_codeforces_update(url):
    current_time = datetime.now().astimezone()
    print(
        f"[{current_time.isoformat(timespec='seconds')}] "
        "Updating Codeforces scoreboard...",
        flush=True,
    )
    subprocess.run(
        [
            "xvfb-run",
            "-a",
            sys.executable,
            "get-codeforces-scoreboard.py",
            url,
        ],
        cwd=LIVE_DIR,
        check=True,
    )
    subprocess.run(
        [sys.executable, "filter-codeforces-scoreboard.py"],
        cwd=LIVE_DIR,
        check=True,
    )


def main():
    args = parse_args()

    if args.platform == "qoj":
        contest_id = parse_standings_url(args.url)
        create_qoj_problem_map(contest_id, args.id_l, args.id_r)
        update = lambda: run_qoj_update(args.url, args.start_time)
        description = (
            f"QOJ contest {contest_id}; "
            f"start time {args.start_time.isoformat(timespec='seconds')}"
        )
    else:
        update = lambda: run_codeforces_update(args.url)
        description = f"Codeforces standings {args.url}"

    enable_live(args.platform)
    print(
        f"[Live] Starting updater for {description}. "
        f"Interval: {UPDATE_INTERVAL_SECONDS} seconds. Press Ctrl+C to stop.",
        flush=True,
    )

    try:
        while True:
            try:
                update()
                print("[Live] Scoreboard update finished.", flush=True)
            except subprocess.CalledProcessError as error:
                print(
                    f"[Live] Update failed: {error.cmd} "
                    f"exited with code {error.returncode}; keeping previous data.",
                    file=sys.stderr,
                    flush=True,
                )

            time.sleep(UPDATE_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[Live] Updater stopped.")


if __name__ == "__main__":
    main()
