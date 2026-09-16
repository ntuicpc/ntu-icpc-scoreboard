#!/usr/bin/env python3

import argparse
import time
import webbrowser
from urllib.parse import urlencode


SUBMISSIONS_URL = "https://qoj.ac/submissions"


def submission_urls(username, problem_id_l, problem_id_r):
    urls = []
    for problem_id in range(problem_id_l, problem_id_r + 1):
        query = urlencode({"problem_id": problem_id, "submitter": username})
        urls.append(f"{SUBMISSIONS_URL}?{query}")
    return urls


def main():
    parser = argparse.ArgumentParser(
        description="Open a QOJ user's submissions for a range of problem IDs."
    )
    parser.add_argument("username", help="QOJ username (not the team's display name)")
    parser.add_argument("problem_id_l", type=int, help="first QOJ problem ID")
    parser.add_argument("problem_id_r", type=int, help="last QOJ problem ID (inclusive)")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="seconds to wait between opening tabs (default: 0.5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print submission URLs without opening the browser",
    )
    args = parser.parse_args()

    if not args.username.strip():
        parser.error("username cannot be empty")
    if args.problem_id_l <= 0:
        parser.error("problem_id_l must be positive")
    if args.problem_id_r < args.problem_id_l:
        parser.error("problem_id_r must be greater than or equal to problem_id_l")
    if args.delay < 0:
        parser.error("--delay cannot be negative")

    urls = submission_urls(args.username.strip(), args.problem_id_l, args.problem_id_r)

    for index, url in enumerate(urls):
        print(url, flush=True)
        if not args.dry_run:
            webbrowser.open_new_tab(url)
            if index < len(urls) - 1:
                time.sleep(args.delay)

    action = "Listed" if args.dry_run else "Opened"
    print(f"{action} {len(urls)} QOJ submission pages.")


if __name__ == "__main__":
    main()
