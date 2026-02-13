"""Simulation mode playlist behavior."""

from src.adapters.spotify.dry_run_playlist_adapter import DryRunPlaylistAdapter
from src.domain.model import ClassificationSession
from src.usecases.classify_track import ClassifyTrackUseCase
from src.usecases.undo_decision import UndoDecisionUseCase


def test_simulation_mode_records_add_without_touching_spotify(track_a, classifier, progress):
    playlist = DryRunPlaylistAdapter()
    session = ClassificationSession(track_ids=[track_a.id])

    classify = ClassifyTrackUseCase(classifier, playlist, progress)
    classify.execute(session, track_a, "ambiance")

    assert playlist.added == [("ambiance", track_a.id)]
    assert playlist.removed == []


def test_simulation_mode_records_remove_on_undo(track_a, classifier, progress):
    playlist = DryRunPlaylistAdapter()
    session = ClassificationSession(track_ids=[track_a.id])
    classify = ClassifyTrackUseCase(classifier, playlist, progress)
    undo = UndoDecisionUseCase(playlist, progress)

    classify.execute(session, track_a, "ambiance")
    undo.execute(session)

    assert ("ambiance", track_a.id) in playlist.removed
