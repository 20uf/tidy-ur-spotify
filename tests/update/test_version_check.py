"""Bounded context: Auto-update

Business rules for version comparison and update notification.
"""

from src.usecases.check_update import parse_semver


class TestSemverComparison:
    """The app compares versions to decide if an update is available."""

    def test_release_version_parsing(self):
        assert parse_semver("1.2.3") == (1, 2, 3, 1, "")

    def test_v_prefix_is_ignored(self):
        assert parse_semver("v1.2.3") == (1, 2, 3, 1, "")

    def test_prerelease_is_lower_than_release(self):
        pre = parse_semver("1.0.0-alpha.1")
        rel = parse_semver("1.0.0")
        assert pre < rel

    def test_alpha_ordering(self):
        a1 = parse_semver("0.1.0-alpha.1")
        a2 = parse_semver("0.1.0-alpha.2")
        assert a1 < a2

    def test_major_minor_patch_ordering(self):
        assert parse_semver("0.1.0") < parse_semver("0.2.0")
        assert parse_semver("0.2.0") < parse_semver("1.0.0")
        assert parse_semver("1.0.0") < parse_semver("1.0.1")

    def test_same_version_is_not_newer(self):
        v = parse_semver("0.2.0-alpha.1")
        assert not (v > v)

    def test_next_minor_alpha_is_newer(self):
        current = parse_semver("0.1.0-alpha.1")
        newer = parse_semver("0.2.0-alpha.1")
        assert newer > current

    def test_invalid_version_returns_zero_tuple(self):
        assert parse_semver("not-a-version") == (0, 0, 0, 0, "")
