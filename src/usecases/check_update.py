"""Use case: check for newer release on GitHub via semver comparison."""

import json
import re
import urllib.request
from dataclasses import dataclass
from typing import Optional

from src.version import __version__

GITHUB_REPO = "20uf/tidy-ur-spotify"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class UpdateInfo:
    current: str
    latest: str
    download_url: str
    release_url: str


def parse_semver(version: str) -> tuple:
    """Parse a semver string into a comparable tuple.

    Supports: 1.2.3, 1.2.3-alpha.1, v1.2.3, etc.
    Pre-release versions sort lower than release versions.
    """
    v = version.lstrip("v")
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", v)
    if not match:
        return (0, 0, 0, 0, "")
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    pre = match.group(4)
    if pre is None:
        # Release version sorts higher than any pre-release
        return (major, minor, patch, 1, "")
    # Pre-release: extract numeric suffix for ordering (alpha.1 < alpha.2)
    pre_num = 0
    num_match = re.search(r"(\d+)$", pre)
    if num_match:
        pre_num = int(num_match.group(1))
    return (major, minor, patch, 0, pre_num)


class CheckUpdateUseCase:

    def execute(self, timeout: float = 5.0) -> Optional[UpdateInfo]:
        """Check GitHub releases for a newer version. Returns None if up-to-date or on error."""
        try:
            req = urllib.request.Request(
                RELEASES_URL,
                headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "TidyUrSpotify"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

        tag = data.get("tag_name", "")
        if not tag:
            return None

        current_tuple = parse_semver(__version__)
        latest_tuple = parse_semver(tag)

        if latest_tuple <= current_tuple:
            return None

        # Find a download asset or fall back to the release page
        release_url = data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest")
        download_url = release_url

        assets = data.get("assets", [])
        if assets:
            # Pick first asset as the main download
            download_url = assets[0].get("browser_download_url", release_url)

        return UpdateInfo(
            current=__version__,
            latest=tag.lstrip("v"),
            download_url=download_url,
            release_url=release_url,
        )
