"""User journey: app views can be instantiated at first launch."""

from types import SimpleNamespace

from src.domain.model import Theme
from src.ui.classify_view import ClassifyView
from src.ui.setup_view import SetupView


class DummyPage:
    def __init__(self):
        self.overlay = []
        self.window = SimpleNamespace(close=lambda: None)

    def update(self):
        return None


class DummyConfig:
    def __init__(self):
        self._cfg = {
            "spotify_client_id": "",
            "spotify_client_secret": "",
            "llm_provider": "openai",
            "llm_api_key": "",
            "llm_model": "",
        }

    def load(self) -> dict:
        return dict(self._cfg)

    def save(self, cfg: dict) -> None:
        self._cfg = dict(cfg)

    def is_configured(self) -> bool:
        return False


def test_setup_view_instantiates_without_page_setter_error():
    page = DummyPage()
    cfg = DummyConfig()

    view = SetupView(page=page, config=cfg, on_complete=lambda: None)

    assert view._page is page


def test_classify_view_instantiates_without_page_setter_error(
    monkeypatch, track_a, classifier, playlist, progress
):
    monkeypatch.setattr(ClassifyView, "_preload_llm", lambda self: None)

    page = DummyPage()
    themes = {
        "ambiance": Theme(
            key="ambiance",
            name="Ambiance",
            description="Chill and melodic tracks",
            shortcut="1",
        ),
        "lets_dance": Theme(
            key="lets_dance",
            name="Let's Dance",
            description="Upbeat and danceable tracks",
            shortcut="2",
        ),
    }

    view = ClassifyView(
        page=page,
        tracks=[track_a],
        themes=themes,
        classifier=classifier,
        playlist=playlist,
        progress=progress,
    )

    assert view._page is page

