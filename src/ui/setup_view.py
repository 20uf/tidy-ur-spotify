"""Flet-based 4-step onboarding wizard."""

import webbrowser

import flet as ft

from src.adapters.classifier import PROVIDERS
from src.domain.ports import ConfigPort
from src.ui.theme import (
    ACCENT,
    BG,
    BG_CARD,
    BG_INPUT,
    BORDER,
    DANGER,
    FG,
    FG_DIM,
    FG_LINK,
)
from src.version import __version__


class SetupView(ft.Column):
    """Multi-step onboarding wizard as a Flet view."""

    def __init__(self, page: ft.Page, config: ConfigPort, on_complete: callable):
        super().__init__()
        self.page = page
        self.config = config
        self.on_complete = on_complete
        self.cfg = config.load()
        self.current_step = 0
        self.step_builders = [
            self._build_welcome,
            self._build_spotify,
            self._build_ai,
            self._build_confirm,
        ]
        self.step_titles = ["Welcome", "Spotify", "AI Provider", "Ready"]

        # Input refs
        self.client_id = ft.TextField(
            label="Client ID",
            value=self.cfg.get("spotify_client_id", ""),
            bgcolor=BG_INPUT,
            color=FG,
            border_color=BORDER,
            focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=FG_DIM),
            cursor_color=FG,
        )
        self.client_secret = ft.TextField(
            label="Client Secret",
            value=self.cfg.get("spotify_client_secret", ""),
            password=True,
            can_reveal_password=True,
            bgcolor=BG_INPUT,
            color=FG,
            border_color=BORDER,
            focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=FG_DIM),
            cursor_color=FG,
        )
        self.provider_var = self.cfg.get("llm_provider", "openai")
        self.api_key = ft.TextField(
            label="API Key",
            value=self.cfg.get("llm_api_key", ""),
            password=True,
            can_reveal_password=True,
            bgcolor=BG_INPUT,
            color=FG,
            border_color=BORDER,
            focused_border_color=ACCENT,
            label_style=ft.TextStyle(color=FG_DIM),
            cursor_color=FG,
        )
        self.error_text = ft.Text("", color=DANGER, size=12)
        self.is_validating = False

        self._render()

    def _render(self):
        self.controls.clear()
        self.controls.append(self._build_indicator())
        self.controls.append(
            ft.Container(
                content=self.step_builders[self.current_step](),
                padding=ft.padding.symmetric(horizontal=30),
            )
        )
        self.controls.append(ft.Container(expand=True))
        self.controls.append(self._build_nav())

    def _build_indicator(self) -> ft.Container:
        circles = []
        for i, title in enumerate(self.step_titles):
            is_done = i < self.current_step
            is_current = i == self.current_step

            circle_bg = ACCENT if (is_done or is_current) else BG_INPUT
            circle_fg = BG if (is_done or is_current) else FG_DIM
            label = "\u2713" if is_done else str(i + 1)

            col = ft.Column(
                [
                    ft.Container(
                        content=ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color=circle_fg),
                        width=32,
                        height=32,
                        border_radius=16,
                        bgcolor=circle_bg,
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Text(title, size=11, color=FG if is_current else FG_DIM),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            )

            circles.append(col)

            if i < len(self.step_titles) - 1:
                line_color = ACCENT if is_done else BORDER
                circles.append(
                    ft.Container(width=50, height=2, bgcolor=line_color, margin=ft.margin.only(top=14))
                )

        return ft.Container(
            content=ft.Row(circles, alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.only(top=25, bottom=10, left=30, right=30),
        )

    def _build_nav(self) -> ft.Container:
        is_first = self.current_step == 0
        is_last = self.current_step == len(self.step_builders) - 1

        controls = []
        if not is_first:
            controls.append(
                ft.TextButton(
                    "\u2190  Back",
                    on_click=self._on_prev,
                    style=ft.ButtonStyle(color=FG_DIM),
                )
            )

        controls.append(ft.Container(expand=True))

        if is_last:
            controls.append(
                ft.ElevatedButton(
                    "Launch Tidy ur Spotify  \u2192",
                    on_click=self._on_finish,
                    bgcolor=ACCENT,
                    color=BG,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                )
            )
        else:
            controls.append(
                ft.ElevatedButton(
                    "Continue  \u2192",
                    on_click=self._on_next,
                    bgcolor=ACCENT,
                    color=BG,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                )
            )

        return ft.Container(
            content=ft.Row(controls),
            padding=ft.padding.only(left=30, right=30, bottom=20),
        )

    # ── Steps ───────────────────────────────────────────────────────

    def _build_welcome(self) -> ft.Column:
        return ft.Column(
            [
                ft.Text("\U0001F3B5", size=48, text_align=ft.TextAlign.CENTER),
                ft.Text(
                    "Tidy ur Spotify",
                    size=26,
                    weight=ft.FontWeight.BOLD,
                    color=FG,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Classify your Liked Songs into themed\nplaylists using AI.",
                    size=14,
                    color=FG_DIM,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=20),
                self._card(
                    ft.Column([
                        ft.Text("To get started, you'll need:", size=13, color=FG),
                        ft.Container(height=8),
                        self._checklist_item("\U0001F3A7", "A Spotify account (free or premium)"),
                        self._checklist_item("\U0001F511", "A Spotify Developer app (guided next step)"),
                        self._checklist_item("\U0001F916", "An AI provider API key (OpenAI, ...)"),
                    ])
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build_spotify(self) -> ft.Column:
        steps = [
            "Go to the Spotify Developer Dashboard",
            'Click "Create App"',
            "Name: anything you like  /  Redirect URI:",
            "Copy the Client ID and Client Secret below",
        ]

        step_items = []
        for i, txt in enumerate(steps):
            step_items.append(
                ft.Row([
                    ft.Text(f"{i + 1}.", size=12, weight=ft.FontWeight.BOLD, color=ACCENT, width=24),
                    ft.Text(txt, size=12, color=FG_DIM),
                ])
            )
            if i == 2:
                step_items.append(
                    ft.Container(
                        content=ft.Text("http://127.0.0.1:8888/callback", size=11, color=ACCENT, font_family="monospace"),
                        bgcolor=BG_INPUT,
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        border_radius=4,
                        margin=ft.margin.only(left=24),
                    )
                )

        return ft.Column(
            [
                ft.Text("Spotify Configuration", size=20, weight=ft.FontWeight.BOLD, color=FG),
                ft.Container(height=10),
                self._card(
                    ft.Column([
                        ft.Text("Create your Spotify Developer app:", size=13, weight=ft.FontWeight.BOLD, color=FG),
                        ft.Container(height=8),
                        *step_items,
                        ft.Container(height=10),
                        ft.TextButton(
                            "\U0001F517  Open Spotify Developer Dashboard",
                            on_click=lambda _: webbrowser.open("https://developer.spotify.com/dashboard"),
                            style=ft.ButtonStyle(color=FG_LINK),
                        ),
                    ])
                ),
                ft.Container(height=15),
                self.client_id,
                ft.Container(height=8),
                self.client_secret,
                self.error_text,
            ],
        )

    def _build_ai(self) -> ft.Column:
        provider_cards = []
        for key, info in PROVIDERS.items():
            is_selected = self.provider_var == key
            border_color = ACCENT if is_selected else BORDER
            bg = BG_CARD if is_selected else BG_INPUT
            indicator = "\u25C9" if is_selected else "\u25CB"

            badge = []
            if key == "openai":
                badge.append(
                    ft.Container(
                        content=ft.Text("Recommended", size=10, color=BG),
                        bgcolor=ACCENT,
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        border_radius=4,
                    )
                )

            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(indicator, size=16, color=ACCENT if is_selected else FG_DIM),
                        ft.Text(info["label"], size=14, weight=ft.FontWeight.BOLD, color=FG),
                        ft.Container(expand=True),
                        *badge,
                    ]),
                    ft.Text(f"Default model: {info['default_model']}", size=11, color=FG_DIM),
                ]),
                bgcolor=bg,
                border=ft.border.all(2, border_color),
                border_radius=8,
                padding=15,
                on_click=lambda _, k=key: self._select_provider(k),
            )
            provider_cards.append(card)

        key_link_url = PROVIDERS[self.provider_var]["url"]
        key_link_name = PROVIDERS[self.provider_var]["name"]

        return ft.Column(
            [
                ft.Text("AI Provider", size=20, weight=ft.FontWeight.BOLD, color=FG),
                ft.Text("Choose the AI service to classify your tracks:", size=13, color=FG_DIM),
                ft.Container(height=10),
                *provider_cards,
                ft.Container(height=15),
                self.api_key,
                ft.TextButton(
                    f"\U0001F511  Get a {key_link_name} key",
                    on_click=lambda _, url=key_link_url: webbrowser.open(url),
                    style=ft.ButtonStyle(color=FG_LINK),
                ),
                self.error_text,
            ],
        )

    def _build_confirm(self) -> ft.Column:
        provider_info = PROVIDERS.get(self.cfg.get("llm_provider", "openai"), PROVIDERS["openai"])

        rows = [
            ("Spotify", f"Client ID: {self.cfg.get('spotify_client_id', '')[:12]}..."),
            ("AI Provider", provider_info["label"]),
            ("Model", provider_info["default_model"]),
            ("API Key", "\u2022" * 16),
        ]

        summary_items = []
        for label, value in rows:
            summary_items.append(
                ft.Row([
                    ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color=FG_DIM, width=120),
                    ft.Text(value, size=12, color=FG),
                ])
            )

        return ft.Column(
            [
                ft.Text("\u2705", size=48, text_align=ft.TextAlign.CENTER),
                ft.Text("All set!", size=22, weight=ft.FontWeight.BOLD, color=FG, text_align=ft.TextAlign.CENTER),
                ft.Text(
                    "Your configuration is saved.\nHere's a summary:",
                    size=13, color=FG_DIM, text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=20),
                self._card(ft.Column(summary_items, spacing=8)),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # ── Navigation ──────────────────────────────────────────────────

    def _on_next(self, e):
        if self.is_validating:
            return
        self.error_text.value = ""

        if self.current_step == 1:
            if not self._validate_spotify_fields():
                self.page.update()
                return
            # Test Spotify credentials
            self.is_validating = True
            self.error_text.value = "Validating Spotify credentials..."
            self.error_text.color = FG_DIM
            self.page.update()

            if not self._test_spotify_credentials():
                self.is_validating = False
                self.error_text.color = DANGER
                self.page.update()
                return
            self.is_validating = False
            self.error_text.value = ""
            self.error_text.color = DANGER

        if self.current_step == 2:
            if not self._validate_ai_fields():
                self.page.update()
                return
            # Test AI credentials
            self.is_validating = True
            self.error_text.value = "Validating AI API key..."
            self.error_text.color = FG_DIM
            self.page.update()

            if not self._test_ai_credentials():
                self.is_validating = False
                self.error_text.color = DANGER
                self.page.update()
                return
            self.is_validating = False
            self.error_text.value = ""
            self.error_text.color = DANGER

        self.current_step += 1
        self._render()
        self.page.update()

    def _on_prev(self, e):
        if self.is_validating:
            return
        self.error_text.value = ""
        self.current_step -= 1
        self._render()
        self.page.update()

    def _on_finish(self, e):
        self.config.save(self.cfg)
        self.on_complete()

    def _select_provider(self, key: str):
        self.provider_var = key
        self._render()
        self.page.update()

    # ── Validation ──────────────────────────────────────────────────

    def _validate_spotify_fields(self) -> bool:
        cid = self.client_id.value.strip()
        secret = self.client_secret.value.strip()
        if not cid or not secret:
            self.error_text.value = "Client ID and Client Secret are required."
            return False
        self.cfg["spotify_client_id"] = cid
        self.cfg["spotify_client_secret"] = secret
        return True

    def _test_spotify_credentials(self) -> bool:
        """Test Spotify credentials by attempting to get an access token."""
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials

            auth_manager = SpotifyClientCredentials(
                client_id=self.cfg["spotify_client_id"],
                client_secret=self.cfg["spotify_client_secret"],
            )
            sp = spotipy.Spotify(auth_manager=auth_manager)
            # Simple API call to verify credentials
            sp.search(q="test", type="track", limit=1)
            return True
        except Exception as e:
            error_msg = str(e)
            if "Invalid client" in error_msg:
                self.error_text.value = "Invalid Client ID or Client Secret."
            elif "redirect" in error_msg.lower():
                self.error_text.value = "Invalid redirect URI. Use: http://127.0.0.1:8888/callback"
            else:
                self.error_text.value = f"Spotify error: {error_msg[:50]}"
            return False

    def _validate_ai_fields(self) -> bool:
        key = self.api_key.value.strip()
        if not key:
            self.error_text.value = "API Key is required."
            return False
        self.cfg["llm_provider"] = self.provider_var
        self.cfg["llm_api_key"] = key
        return True

    def _test_ai_credentials(self) -> bool:
        """Test AI provider credentials with a minimal API call."""
        provider = self.provider_var
        api_key = self.cfg["llm_api_key"]

        try:
            if provider == "openai":
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                # Minimal API call - list models
                client.models.list()
                return True
            elif provider == "anthropic":
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key)
                # Minimal API call - short message
                client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1,
                    messages=[{"role": "user", "content": "hi"}],
                )
                return True
            return True
        except Exception as e:
            error_msg = str(e)
            if "invalid" in error_msg.lower() or "auth" in error_msg.lower() or "key" in error_msg.lower():
                self.error_text.value = "Invalid API key."
            elif "rate" in error_msg.lower():
                self.error_text.value = "Rate limited. API key is valid but try again later."
                return True  # Key is valid, just rate limited
            else:
                self.error_text.value = f"API error: {error_msg[:50]}"
            return False

    # ── Helpers ─────────────────────────────────────────────────────

    def _card(self, content: ft.Control) -> ft.Container:
        return ft.Container(
            content=content,
            bgcolor=BG_CARD,
            border=ft.border.all(1, BORDER),
            border_radius=8,
            padding=18,
        )

    def _checklist_item(self, icon: str, text: str) -> ft.Row:
        return ft.Row([
            ft.Text(icon, size=16, color=ACCENT),
            ft.Text(text, size=12, color=FG_DIM),
        ], spacing=10)
