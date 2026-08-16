from datetime import datetime
from pathlib import Path

from scoreboard_parsers.io import write_json_atomic

LIVE_SCOREBOARD_TITLE = "NTU ICPC Live Scoreboard"


def set_live_status(path, enabled, platform=None):
    status = {
        "enabled": bool(enabled),
        "update-time": datetime.now().astimezone().strftime("%Y/%m/%d %H:%M:%S"),
    }
    if platform is not None:
        status["platform"] = platform
    write_json_atomic(Path(path), status)
    return status
