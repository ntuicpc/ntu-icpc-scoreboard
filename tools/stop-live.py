#!/usr/bin/env python3

import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
STATUS_PATH = PROJECT_DIR / "live" / "status.json"
sys.path.insert(0, str(PROJECT_DIR))

from live.state import set_live_status

def main():
    set_live_status(STATUS_PATH, False)

    print("[Live] Live scoreboard is now disabled.")


if __name__ == "__main__":
    main()
