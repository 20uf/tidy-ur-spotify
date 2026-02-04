"""Use case: undo the last classification decision."""

import threading
from typing import Optional

from src.domain.model import ClassificationSession, Decision
from src.domain.ports import PlaylistPort, ProgressPort


class UndoDecisionUseCase:

    def __init__(self, playlist: PlaylistPort, progress: ProgressPort):
        self.playlist = playlist
        self.progress = progress

    def execute(self, session: ClassificationSession) -> Optional[Decision]:
        last = session.undo_last()
        if last is None:
            return None

        if last.themes:
            for theme_key in last.themes:
                threading.Thread(
                    target=self.playlist.remove_track,
                    args=(theme_key, last.track_id),
                    daemon=True,
                ).start()

        self.progress.save(session)
        return last
