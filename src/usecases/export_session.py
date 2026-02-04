"""Use case: export session decisions to CSV."""

from src.domain.model import ClassificationSession
from src.domain.ports import ProgressPort


class ExportSessionUseCase:

    def __init__(self, progress: ProgressPort):
        self.progress = progress

    def execute(self, session: ClassificationSession, path: str = "export.csv") -> str:
        return self.progress.export_csv(session.decisions, path)
