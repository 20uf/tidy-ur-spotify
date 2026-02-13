"""Utilities to inspect and manage local cache files."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from src.adapters.spotify.auth import SPOTIFY_CACHE_PATH

DEFAULT_CLASSIFIER_CACHE = "classification_cache.json"
LEGACY_SPOTIFY_CACHE_PATH = ".spotify_cache"


def _resolve(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def cache_paths(include_progress: bool = False) -> list[Path]:
    classifier_cache = os.getenv("TIDY_SPOTIFY_CACHE_FILE", DEFAULT_CLASSIFIER_CACHE)
    candidates = [classifier_cache, SPOTIFY_CACHE_PATH, LEGACY_SPOTIFY_CACHE_PATH]
    if include_progress:
        candidates.append("progress.json")

    paths: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = _resolve(candidate)
        key = str(resolved)
        if key in seen:
            continue
        paths.append(resolved)
        seen.add(key)
    return paths


def cache_root_dir(include_progress: bool = False) -> Path:
    paths = cache_paths(include_progress=include_progress)
    existing = [path for path in paths if path.exists()]
    if existing:
        return existing[0].parent
    if paths:
        return paths[0].parent
    return Path.cwd()


def cache_locations(include_progress: bool = False) -> list[tuple[Path, bool]]:
    return [(path, path.exists()) for path in cache_paths(include_progress=include_progress)]


def cache_total_size_bytes(include_progress: bool = False) -> int:
    total = 0
    for path in cache_paths(include_progress=include_progress):
        if not path.exists():
            continue
        if path.is_file():
            total += path.stat().st_size
            continue
        if path.is_dir():
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    total += file_path.stat().st_size
    return total


def clear_cache(include_progress: bool = False) -> int:
    removed = 0
    for path in cache_paths(include_progress=include_progress):
        if not path.exists():
            continue
        try:
            if path.is_file():
                path.unlink(missing_ok=True)
            else:
                shutil.rmtree(path, ignore_errors=True)
            removed += 1
        except OSError:
            continue
    return removed


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(max(size, 0))
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return "0 B"


def open_cache_folder(include_progress: bool = False) -> tuple[bool, str]:
    folder = cache_root_dir(include_progress=include_progress)
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(folder))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])
    except Exception as exc:
        return False, f"Unable to open cache folder: {exc}"
    return True, f"Cache folder opened: {folder}"
