import argparse
import shutil
from pathlib import Path

from scoreboard_parsers.io import write_json_pair_atomic


def archive_name(value):
    if not value or value in {".", ".."} or Path(value).name != value:
        raise argparse.ArgumentTypeError(
            "archive ID must be a single directory name without path separators"
        )
    return value


def write_archive(archive_root, name, scoreboard, problem_map):
    destination = Path(archive_root) / name
    if destination.exists():
        raise RuntimeError(f"archive already exists: {destination}")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        write_json_pair_atomic(
            destination / "problem.json", problem_map,
            destination / "scoreboard.json", scoreboard,
        )
    except Exception:
        shutil.rmtree(destination)
        raise
    return destination
