"""Use case: classify the current track into a theme."""

import threading

from src.domain.model import ClassificationSession, Decision, Track
from src.domain.ports import ClassifierPort, PlaylistPort, ProgressPort


class ClassifyTrackUseCase:

    def __init__(
        self,
        classifier: ClassifierPort,
        playlist: PlaylistPort,
        progress: ProgressPort,
    ):
        self.classifier = classifier
        self.playlist = playlist
        self.progress = progress

    def execute(
        self,
        session: ClassificationSession,
        track: Track,
        theme_key: str,
    ) -> Decision:
        existing = session.decision_for(track.id)
        if existing:
            if theme_key not in existing.themes:
                existing.themes.append(theme_key)
            decision = existing
        else:
            decision = Decision(
                track_id=track.id,
                track_name=track.name,
                artist=track.artist,
                themes=[theme_key],
            )
            session.add_decision(decision)

        threading.Thread(
            target=self.playlist.add_track,
            args=(theme_key, track.id),
            daemon=True,
        ).start()

        self.progress.save(session)
        return decision

    def skip(self, session: ClassificationSession, track: Track) -> Decision:
        decision = Decision(
            track_id=track.id,
            track_name=track.name,
            artist=track.artist,
            skipped=True,
        )
        session.add_decision(decision)
        self.progress.save(session)
        return decision
