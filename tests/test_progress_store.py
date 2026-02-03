"""Tests for ProgressStore: save, load, clear, export CSV."""

import csv
import os
import tempfile

import pytest

from src.storage.progress_store import ProgressState, ProgressStore, TrackDecision


@pytest.fixture
def tmp_progress_file(tmp_path):
    return str(tmp_path / "progress.json")


@pytest.fixture
def store(tmp_progress_file):
    return ProgressStore(path=tmp_progress_file)


@pytest.fixture
def sample_state():
    return ProgressState(
        current_index=5,
        track_ids=["t1", "t2", "t3", "t4", "t5", "t6"],
        decisions=[
            TrackDecision(track_id="t1", track_name="Song A", artist="Artist A", themes=["ambiance"]),
            TrackDecision(track_id="t2", track_name="Song B", artist="Artist B", themes=["lets_dance"]),
            TrackDecision(track_id="t3", track_name="Song C", artist="Artist C", skipped=True),
            TrackDecision(track_id="t4", track_name="Song D", artist="Artist D", themes=["ambiance", "lets_dance"]),
        ],
    )


class TestProgressStore:
    def test_save_and_load(self, store, sample_state):
        store.save(sample_state)
        loaded = store.load()
        assert loaded is not None
        assert loaded.current_index == 5
        assert len(loaded.decisions) == 4
        assert loaded.decisions[0].track_name == "Song A"
        assert loaded.decisions[0].themes == ["ambiance"]
        assert loaded.decisions[3].themes == ["ambiance", "lets_dance"]
        assert loaded.track_ids == ["t1", "t2", "t3", "t4", "t5", "t6"]

    def test_load_nonexistent(self, store):
        assert store.load() is None

    def test_clear(self, store, sample_state):
        store.save(sample_state)
        assert store.exists()
        store.clear()
        assert not store.exists()
        assert store.load() is None

    def test_clear_nonexistent(self, store):
        store.clear()  # should not raise

    def test_exists(self, store, sample_state):
        assert not store.exists()
        store.save(sample_state)
        assert store.exists()

    def test_skipped_track(self, store, sample_state):
        store.save(sample_state)
        loaded = store.load()
        assert loaded.decisions[2].skipped is True
        assert loaded.decisions[2].themes == []

    def test_multiple_themes(self, store, sample_state):
        store.save(sample_state)
        loaded = store.load()
        d = loaded.decisions[3]
        assert d.themes == ["ambiance", "lets_dance"]

    def test_export_csv(self, tmp_path, sample_state):
        csv_path = str(tmp_path / "export.csv")
        result = ProgressStore.export_csv(sample_state.decisions, path=csv_path)
        assert result == csv_path
        assert os.path.exists(csv_path)

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert rows[0] == ["track_id", "track_name", "artist", "themes", "skipped"]
        assert len(rows) == 5  # header + 4 decisions
        assert rows[1][3] == "ambiance"  # themes joined with |
        assert rows[4][3] == "ambiance|lets_dance"

    def test_empty_state(self, store):
        empty = ProgressState()
        store.save(empty)
        loaded = store.load()
        assert loaded.current_index == 0
        assert loaded.decisions == []
        assert loaded.track_ids == []
