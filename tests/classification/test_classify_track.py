"""Bounded context: Classification

Business rules for assigning a Liked Song to one or more themed playlists.
"""

import pytest

from src.domain.model import ClassificationSession, Decision, Track
from src.usecases.classify_track import ClassifyTrackUseCase
from src.usecases.undo_decision import UndoDecisionUseCase


class TestUserClassifiesATrack:
    """As a user, I classify a track into a themed playlist so it gets organized."""

    def test_track_is_added_to_the_chosen_playlist(self, track_a, classifier, playlist, progress):
        session = ClassificationSession(track_ids=[track_a.id])
        uc = ClassifyTrackUseCase(classifier, playlist, progress)

        uc.execute(session, track_a, "ambiance")

        assert ("ambiance", track_a.id) in playlist.added

    def test_decision_is_recorded_with_the_chosen_theme(self, track_a, classifier, playlist, progress):
        session = ClassificationSession(track_ids=[track_a.id])
        uc = ClassifyTrackUseCase(classifier, playlist, progress)

        decision = uc.execute(session, track_a, "ambiance")

        assert decision.themes == ["ambiance"]
        assert decision.track_id == track_a.id
        assert decision.track_name == track_a.name
        assert decision.skipped is False

    def test_session_advances_to_the_next_track(self, track_a, track_b, classifier, playlist, progress):
        session = ClassificationSession(track_ids=[track_a.id, track_b.id])
        uc = ClassifyTrackUseCase(classifier, playlist, progress)

        uc.execute(session, track_a, "ambiance")

        assert session.current_index == 1
        assert session.decided_count == 1

    def test_progress_is_saved_after_each_classification(self, track_a, classifier, playlist, progress):
        session = ClassificationSession(track_ids=[track_a.id])
        uc = ClassifyTrackUseCase(classifier, playlist, progress)

        uc.execute(session, track_a, "lets_dance")

        assert progress.exists()


class TestUserSkipsATrack:
    """As a user, I skip a track I don't want to classify right now."""

    def test_skipped_track_is_not_added_to_any_playlist(self, track_a, classifier, playlist, progress):
        session = ClassificationSession(track_ids=[track_a.id])
        uc = ClassifyTrackUseCase(classifier, playlist, progress)

        uc.skip(session, track_a)

        assert playlist.added == []

    def test_skip_is_recorded_as_a_decision(self, track_a, classifier, playlist, progress):
        session = ClassificationSession(track_ids=[track_a.id])
        uc = ClassifyTrackUseCase(classifier, playlist, progress)

        decision = uc.skip(session, track_a)

        assert decision.skipped is True
        assert decision.themes == []

    def test_session_advances_after_skip(self, track_a, track_b, classifier, playlist, progress):
        session = ClassificationSession(track_ids=[track_a.id, track_b.id])
        uc = ClassifyTrackUseCase(classifier, playlist, progress)

        uc.skip(session, track_a)

        assert session.current_index == 1


class TestUserUndoesLastDecision:
    """As a user, I undo my last action to correct a mistake."""

    def test_undo_removes_track_from_playlist(self, track_a, classifier, playlist, progress):
        session = ClassificationSession(track_ids=[track_a.id])
        classify = ClassifyTrackUseCase(classifier, playlist, progress)
        undo = UndoDecisionUseCase(playlist, progress)

        classify.execute(session, track_a, "ambiance")
        undo.execute(session)

        assert ("ambiance", track_a.id) in playlist.removed

    def test_undo_restores_session_index(self, track_a, classifier, playlist, progress):
        session = ClassificationSession(track_ids=[track_a.id])
        classify = ClassifyTrackUseCase(classifier, playlist, progress)
        undo = UndoDecisionUseCase(playlist, progress)

        classify.execute(session, track_a, "ambiance")
        undo.execute(session)

        assert session.current_index == 0
        assert session.decided_count == 0

    def test_undo_on_empty_session_does_nothing(self, playlist, progress):
        session = ClassificationSession()
        undo = UndoDecisionUseCase(playlist, progress)

        result = undo.execute(session)

        assert result is None
        assert playlist.removed == []

    def test_undo_after_skip_does_not_touch_playlists(self, track_a, classifier, playlist, progress):
        session = ClassificationSession(track_ids=[track_a.id])
        classify = ClassifyTrackUseCase(classifier, playlist, progress)
        undo = UndoDecisionUseCase(playlist, progress)

        classify.skip(session, track_a)
        undo.execute(session)

        assert playlist.removed == []


class TestAiSuggestion:
    """The AI suggests a theme for each track to help the user decide faster."""

    def test_ai_provides_suggestion_after_preload(self, track_a, classifier):
        classifier.preload([track_a], batch_size=10)
        suggestions = classifier.get_suggestions(track_a.id)

        assert len(suggestions) >= 1
        assert suggestions[0].theme_key == "ambiance"
        assert 0.0 <= suggestions[0].confidence <= 1.0

    def test_no_suggestion_for_unknown_track(self, classifier):
        suggestions = classifier.get_suggestions("unknown_track_id")
        assert suggestions == []
