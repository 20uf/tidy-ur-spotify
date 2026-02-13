"""User journey: classify, undo, resume and export flows."""

from src.adapters.progress.json_progress_adapter import JsonProgressAdapter
from src.usecases.classify_track import ClassifyTrackUseCase
from src.usecases.export_session import ExportSessionUseCase
from src.usecases.resume_session import ResumeSessionUseCase
from src.usecases.undo_decision import UndoDecisionUseCase


def test_user_can_complete_a_classification_journey(liked_songs, classifier, playlist, progress):
    resume_uc = ResumeSessionUseCase(progress)
    classify_uc = ClassifyTrackUseCase(classifier, playlist, progress)
    undo_uc = UndoDecisionUseCase(playlist, progress)
    export_uc = ExportSessionUseCase(progress)

    session = resume_uc.execute(liked_songs)
    classify_uc.execute(session, liked_songs[0], "ambiance")
    classify_uc.execute(session, liked_songs[1], "lets_dance")
    undone = undo_uc.execute(session)
    classify_uc.skip(session, liked_songs[1])
    classify_uc.execute(session, liked_songs[2], "lets_dance")
    export_path = export_uc.execute(session, "journey.csv")

    assert undone is not None
    assert undone.track_id == liked_songs[1].id
    assert export_path == "journey.csv"
    assert session.current_index == 3
    assert len(session.decisions) == 3
    assert session.decisions[0].themes == ["ambiance"]
    assert session.decisions[1].skipped is True
    assert session.decisions[2].themes == ["lets_dance"]


def test_user_can_resume_exact_state_after_pause(tmp_path, liked_songs, classifier, playlist):
    progress = JsonProgressAdapter(path=str(tmp_path / "progress.json"))
    resume_uc = ResumeSessionUseCase(progress)
    classify_uc = ClassifyTrackUseCase(classifier, playlist, progress)

    session = resume_uc.execute(liked_songs)
    classify_uc.execute(session, liked_songs[0], "ambiance")
    classify_uc.skip(session, liked_songs[1])

    resumed = resume_uc.execute(liked_songs)

    assert resumed.current_index == 2
    assert len(resumed.decisions) == 2
    assert resumed.decisions[0].track_id == liked_songs[0].id
    assert resumed.decisions[1].track_id == liked_songs[1].id
    assert resumed.decisions[1].skipped is True

