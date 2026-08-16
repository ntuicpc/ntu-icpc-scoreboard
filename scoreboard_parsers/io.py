import json
import os
from pathlib import Path


def load_json(path):
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as error:
        raise RuntimeError(f"Required file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid JSON file: {path}: {error}") from error


def write_json_atomic(path, data):
    path = Path(path)
    temporary_path = path.with_name(path.name + ".tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
            file.write("\n")
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def write_text_atomic(path, content):
    path = Path(path)
    temporary_path = path.with_name(path.name + ".tmp")
    try:
        temporary_path.write_text(content, encoding="utf-8")
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def write_json_pair_atomic(first_path, first_data, second_path, second_data):
    paths_and_data = (
        (Path(first_path), first_data),
        (Path(second_path), second_data),
    )
    temporary_paths = []
    try:
        for path, data in paths_and_data:
            temporary_path = path.with_name(path.name + ".tmp")
            with temporary_path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
                file.write("\n")
            temporary_paths.append((temporary_path, path))
        for temporary_path, path in temporary_paths:
            os.replace(temporary_path, path)
    except Exception:
        for temporary_path, _ in temporary_paths:
            temporary_path.unlink(missing_ok=True)
        raise
