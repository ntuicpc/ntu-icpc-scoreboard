#!/usr/bin/env python3

import argparse
import sys
from datetime import datetime
from pathlib import Path

LIVE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = LIVE_DIR.parent
HTML_PATH = LIVE_DIR / "standings.html"
TIMESTAMP_PATH = LIVE_DIR / "standings.timestamp"

sys.path.insert(0, str(PROJECT_DIR))

from browser import download_html
from scoreboard_parsers.io import write_text_atomic
from scoreboard_parsers.qoj import parse_standings_url


def standings_url(value):
    try:
        parse_standings_url(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error
    return value


def main():
    parser = argparse.ArgumentParser(description="Download a QOJ contest scoreboard.")
    parser.add_argument("url", type=standings_url, help="QOJ standings URL")
    args = parser.parse_args()

    download_time = datetime.now().astimezone()
    html = download_html("QOJ", args.url, ready_selector="table.standings")
    write_text_atomic(HTML_PATH, html)
    write_text_atomic(
        TIMESTAMP_PATH, download_time.strftime("%Y/%m/%d %H:%M:%S")
    )
    print(
        f"[QOJ] Download completed at "
        f"{download_time.strftime('%Y/%m/%d %H:%M:%S')}.",
        flush=True,
    )


if __name__ == "__main__":
    main()
