"""Bounded context: Session Management

Business rules for starting, resuming, pausing and exporting a classification session.
"""

import csv
import os

import pytest

from src.adapters.progress.json_progress_adapter import JsonProgressAdapter
from src.domain.model import ClassificationSession, Decision
from src.usecases.classify_track import ClassifyTrackUseCase
from src.usecases.export_session import ExportSessionUseCase
from src.usecases.resume_session import ResumeSessionUseCase


class TestStartNewSession:
    """As a user opening the app for the first time, I start with a fresh session."""

    def test_new_session_starts_at_index_zero(self, liked_songs, progress):
        uc = ResumeSessionUseCase(progress)
        session = uc.execute(liked_songs)

        assert session.current_index == 0
        assert session.decided_count == 0

    def test_new_session_contains_all_track_ids(self, liked_songs, progress):
        uc = ResumeSessionUseCase(progress)
        session = uc.execute(liked_songs)

        assert session.track_ids == [t.id for t in liked_songs]


class TestResumeInterruptedSession:
    """As a user who paused earlier, I resume where I left off."""

    def test_resume_preserves_current_index(self, liked_songs, progress):
        existing = ClassificationSession(
            current_index=2,
            track_ids=["t1", "t2", "t3"],
            decisions=[
                Decision(track_id="t1", track_name="A", artist="A", themes=["ambiance"]),
                Decision(track_id="t2", track_name="B", artist="B", skipped=True),
            ],
        )
        progress.save(existing)

        uc = ResumeSessionUseCase(progress)
        session = uc.execute(liked_songs)

        assert session.current_index == 2
        assert session.decided_count == 2

    def test_resume_preserves_decisions(self, liked_songs, progress):
        existing = ClassificationSession(
            current_index=1,
            track_ids=["t1"],
            decisions=[
                Decision(track_id="t1", track_name="A", artist="A", themes=["lets_dance"]),
            ],
        )
        progress.save(existing)

        uc = ResumeSessionUseCase(progress)
        session = uc.execute(liked_songs)

        assert session.decisions[0].themes == ["lets_dance"]


class TestPauseAndSave:
    """Progress is automatically saved so the user can quit at any time."""

    def test_progress_is_saved_after_each_action(self, liked_songs, classifier, playlist, progress):
        session = ClassificationSession(track_ids=[t.id for t in liked_songs])
        uc = ClassifyTrackUseCase(classifier, playlist, progress)

        uc.execute(session, liked_songs[0], "ambiance")

        saved = progress.load()
        assert saved is not None
        assert saved.current_index == 1

    def test_clear_progress_removes_all_data(self, liked_songs, progress):
        session = ClassificationSession(current_index=2, track_ids=["t1", "t2"])
        progress.save(session)

        progress.clear()

        assert not progress.exists()
        assert progress.load() is None


class TestExportDecisions:
    """As a user who finished classifying, I export a CSV of all decisions."""

    def test_export_creates_csv_file(self, tmp_path):
        adapter = JsonProgressAdapter(path=str(tmp_path / "progress.json"))
        decisions = [
            Decision(track_id="t1", track_name="Chill Vibes", artist="DJ Smooth", themes=["ambiance"]),
            Decision(track_id="t2", track_name="Party Starter", artist="MC Hype", themes=["lets_dance"]),
            Decision(track_id="t3", track_name="Slow Motion", artist="The Drifters", skipped=True),
        ]
        csv_path = str(tmp_path / "export.csv")

        result = adapter.export_csv(decisions, path=csv_path)

        assert os.path.exists(result)
        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert rows[0] == ["track_id", "track_name", "artist", "themes", "skipped"]
        assert len(rows) == 4  # header + 3 decisions

    def test_export_contains_all_decisions(self, tmp_path):
        adapter = JsonProgressAdapter(path=str(tmp_path / "progress.json"))
        decisions = [
            Decision(track_id="t1", track_name="A", artist="A", themes=["ambiance"]),
            Decision(track_id="t2", track_name="B", artist="B", themes=["ambiance", "lets_dance"]),
        ]
        csv_path = str(tmp_path / "export.csv")
        adapter.export_csv(decisions, path=csv_path)

        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert rows[1][3] == "ambiance"
        assert rows[2][3] == "ambiance|lets_dance"

    def test_export_via_use_case(self, progress):
        session = ClassificationSession(
            decisions=[Decision(track_id="t1", track_name="A", artist="A", themes=["ambiance"])]
        )
        uc = ExportSessionUseCase(progress)
        path = uc.execute(session, "out.csv")

        assert path == "out.csv"


class TestSessionPersistence:
    """The JSON progress adapter correctly serializes and deserializes sessions."""

    def test_save_and_load_round_trip(self, tmp_path):
        adapter = JsonProgressAdapter(path=str(tmp_path / "progress.json"))
        session = ClassificationSession(
            current_index=5,
            track_ids=["t1", "t2", "t3", "t4", "t5", "t6"],
            decisions=[
                Decision(track_id="t1", track_name="Song A", artist="Artist A", themes=["ambiance"]),
                Decision(track_id="t2", track_name="Song B", artist="Artist B", themes=["lets_dance"]),
                Decision(track_id="t3", track_name="Song C", artist="Artist C", skipped=True),
                Decision(track_id="t4", track_name="Song D", artist="Artist D", themes=["ambiance", "lets_dance"]),
            ],
        )

        adapter.save(session)
        loaded = adapter.load()

        assert loaded.current_index == 5
        assert len(loaded.decisions) == 4
        assert loaded.decisions[0].themes == ["ambiance"]
        assert loaded.decisions[2].skipped is True
        assert loaded.decisions[3].themes == ["ambiance", "lets_dance"]
        assert loaded.track_ids == ["t1", "t2", "t3", "t4", "t5", "t6"]

    def test_load_nonexistent_returns_none(self, tmp_path):
        adapter = JsonProgressAdapter(path=str(tmp_path / "nonexistent.json"))
        assert adapter.load() is None

    def test_empty_session_round_trip(self, tmp_path):
        adapter = JsonProgressAdapter(path=str(tmp_path / "progress.json"))
        adapter.save(ClassificationSession())
        loaded = adapter.load()

        assert loaded.current_index == 0
        assert loaded.decisions == []
        assert loaded.track_ids == []
