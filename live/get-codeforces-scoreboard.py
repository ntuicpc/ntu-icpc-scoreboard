#!/usr/bin/env python3

import argparse
import sys
from datetime import datetime
from pathlib import Path

LIVE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = LIVE_DIR.parent
HTML_PATH = LIVE_DIR / "standings.html"
TIMESTAMP_PATH = LIVE_DIR / "standings.timestamp"
STANDINGS_WAIT_SECONDS = 90

sys.path.insert(0, str(PROJECT_DIR))

from scoreboard_parsers.io import write_text_atomic
from scoreboard_parsers.codeforces import is_standings_url, public_standings_url
from browser import download_html

def standings_url(value):
    if not is_standings_url(value):
        raise argparse.ArgumentTypeError(
            "expected a Codeforces contest, gym, or group standings URL"
        )
    return value


def main():
    parser = argparse.ArgumentParser(
        description="Download a Codeforces contest scoreboard."
    )
    parser.add_argument("url", type=standings_url, help="Codeforces standings URL")
    args = parser.parse_args()

    url = public_standings_url(args.url)
    if url != args.url:
        print(
            "[Codeforces] Using the public standings URL; "
            "team filtering is handled locally.",
            flush=True,
        )

    download_time = datetime.now().astimezone()
    html = download_html(
        "Codeforces", url, ready_selector="table.standings",
        ready_timeout=STANDINGS_WAIT_SECONDS,
    )
    write_text_atomic(HTML_PATH, html)
    write_text_atomic(
        TIMESTAMP_PATH, download_time.strftime("%Y/%m/%d %H:%M:%S")
    )

    print(
        "[Codeforces] Download completed at "
        f"{download_time.strftime('%Y/%m/%d %H:%M:%S')}.",
        flush=True,
    )


if __name__ == "__main__":
    main()
