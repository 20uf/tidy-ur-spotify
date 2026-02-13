"""Flet-based 3-step configuration wizard."""

import asyncio
import webbrowser
from typing import Callable, Optional

import flet as ft

from src.adapters.cache.local_cache import (
    cache_locations,
    cache_root_dir,
    cache_total_size_bytes,
    clear_cache,
    format_bytes,
    open_cache_folder,
)
from src.adapters.classifier import PROVIDERS
from src.domain.ports import ConfigPort
from src.ui.branding import build_logo
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
from src.ui.workflow_header import build_workflow_header

CONFIG_WORKFLOW_STEPS = ["Spotify", "AI", "Validation"]


class SetupView(ft.Column):
    """Multi-step onboarding wizard as a Flet view."""

    def __init__(
        self,
        page: ft.Page,
        config: ConfigPort,
        on_complete: Callable[[], None],
        start_step: int = 0,
        on_cancel: Optional[Callable[[], None]] = None,
    ):
        super().__init__()
        self._page = page
        self.config = config
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.cfg = config.load()
        self.current_step = max(0, min(start_step, 2))
        self.step_builders = [
            self._build_spotify,
            self._build_ai,
            self._build_confirm,
        ]
        self._content_width = 820
        self._form_width = 760
        self._is_closing = False
        self._cache_feedback = ""
        self._cache_feedback_color = FG_DIM

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
        self.busy_label = ft.Text("", color=FG_DIM, size=11, visible=False)
        self.step_activity = ft.ProgressRing(width=14, height=14, color=ACCENT, visible=False)
        self.is_validating = False

        self.expand = True
        self.width = float("inf")
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 0
        self._page.on_resized = self._on_resize
        self._render()

    def _render(self):
        self._sync_layout_metrics()
        self.controls.clear()
        self.controls.append(
            ft.Container(
                content=build_workflow_header(
                    page=self._page,
                    current_step=self.current_step + 1,
                    subtitle=f"Local configuration - Step {self.current_step + 1}/3",
                    step_labels=CONFIG_WORKFLOW_STEPS,
                    width=float("inf"),
                ),
                width=float("inf"),
                padding=ft.padding.only(top=12, bottom=6),
            )
        )
        self.controls.append(
            self._build_setup_layer()
        )
        self.controls.append(
            ft.Container(
                content=self.step_builders[self.current_step](),
                width=self._content_width,
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
            )
        )
        self.controls.append(ft.Container(expand=True))
        self.controls.append(self._build_nav())

    def _sync_layout_metrics(self):
        width = int(getattr(self._page.window, "width", 0) or 980)
        usable_width = max(width - 48, 320)
        self._content_width = min(usable_width, 1080)
        self._form_width = max(min(self._content_width - 24, 980), 300)
        self.client_id.width = self._form_width
        self.client_secret.width = self._form_width
        self.api_key.width = self._form_width

    def _build_setup_layer(self) -> ft.Control:
        compact = self._content_width < 980
        logo_size = 168 if compact else 232
        logo_width = self._content_width if compact else max(300, int(self._content_width * 0.30))
        status_width = self._content_width if compact else max(420, self._content_width - logo_width - 12)
        spotify_ready = bool(self.cfg.get("spotify_client_id") and self.cfg.get("spotify_client_secret"))
        ai_ready = bool(self.cfg.get("llm_api_key"))
        cache_size = format_bytes(cache_total_size_bytes(include_progress=False))
        cache_dir = cache_root_dir(include_progress=False)
        cache_files = cache_locations(include_progress=False)

        connection_controls: list[ft.Control] = [
            ft.Text(
                f"Spotify credentials: {'configured' if spotify_ready else 'missing'}",
                size=12,
                color=FG if spotify_ready else FG_DIM,
            ),
            ft.Text(
                f"AI provider: {self.provider_var.upper()} ({'key configured' if ai_ready else 'key missing'})",
                size=12,
                color=FG if ai_ready else FG_DIM,
            ),
        ]
        cache_controls: list[ft.Control] = [
            ft.Text(f"Local cache: {cache_size}", size=11, color=FG_DIM),
            ft.Text(f"Cache folder: {cache_dir}", size=11, color=FG_DIM),
            ft.Text("Cache files:", size=11, color=FG),
            *[
                ft.Text(
                    f"- {path.name} ({'present' if exists else 'missing'})",
                    size=11,
                    color=FG_DIM,
                )
                for path, exists in cache_files
            ],
            ft.Row(
                [
                    ft.OutlinedButton("Clear cache", on_click=self._on_clear_cache),
                    ft.OutlinedButton("Open cache folder", on_click=self._on_open_cache_folder),
                ],
                spacing=8,
                wrap=True,
            ),
        ]
        if self._cache_feedback:
            cache_controls.append(ft.Text(self._cache_feedback, size=11, color=self._cache_feedback_color))

        connection_card = ft.Container(
            width=status_width,
            bgcolor=BG_CARD,
            border=ft.border.all(1, BORDER),
            border_radius=10,
            padding=14,
            content=ft.Column(
                [
                    ft.Text("Connection status", size=14, weight=ft.FontWeight.BOLD, color=FG),
                    ft.Container(height=1, bgcolor=BORDER),
                    *connection_controls,
                ],
                spacing=8,
            ),
        )

        cache_card = ft.Container(
            width=status_width,
            bgcolor=BG_CARD,
            border=ft.border.all(1, BORDER),
            border_radius=10,
            padding=14,
            content=ft.Column(
                [
                    ft.Text("Local cache", size=14, weight=ft.FontWeight.BOLD, color=FG),
                    ft.Container(height=1, bgcolor=BORDER),
                    *cache_controls,
                ],
                spacing=8,
            ),
        )

        logo_block = ft.Container(
            width=logo_width,
            alignment=ft.Alignment(0, 0),
            content=build_logo(logo_size),
        )

        if compact:
            return ft.Container(
                width=self._content_width,
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                content=ft.Column(
                    [logo_block, connection_card, cache_card],
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )

        return ft.Container(
            width=self._content_width,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            content=ft.Row(
                [
                    logo_block,
                    ft.Column(
                        [connection_card, cache_card],
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        )

    def _build_nav(self) -> ft.Container:
        is_first = self.current_step == 0
        is_last = self.current_step == len(self.step_builders) - 1

        controls = []
        if self.on_cancel:
            controls.append(
                ft.TextButton(
                    "Closing..." if self._is_closing else "Close configuration",
                    on_click=self._on_cancel,
                    disabled=self._is_closing or self.is_validating,
                    style=ft.ButtonStyle(color=FG_DIM),
                )
            )
        if not is_first:
            controls.append(
                ft.TextButton(
                    "\u2190  Back",
                    on_click=self._on_prev,
                    style=ft.ButtonStyle(color=FG_DIM),
                )
            )

        controls.append(ft.Container(expand=True))
        controls.append(self.busy_label)
        controls.append(self.step_activity)

        if is_last:
            controls.append(
                ft.ElevatedButton(
                    "Open application  \u2192",
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
            width=self._content_width,
            padding=ft.padding.only(left=12, right=12, bottom=20),
        )

    # ── Steps ───────────────────────────────────────────────────────

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
                ft.Text("Spotify configuration", size=22, weight=ft.FontWeight.BOLD, color=FG),
                ft.Text("Enter your Spotify Developer app credentials.", size=12, color=FG_DIM),
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
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
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
                width=self._form_width,
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
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
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
                    "Your configuration is saved.\nHere is the summary:",
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
        self.busy_label.visible = False
        self.step_activity.visible = False

        if self.current_step == 0:
            if not self._validate_spotify_fields():
                self._page.update()
                return
            # Test Spotify credentials
            self.is_validating = True
            self.busy_label.value = "Validating Spotify..."
            self.busy_label.visible = True
            self.step_activity.visible = True
            self.error_text.value = "Validating Spotify credentials..."
            self.error_text.color = FG_DIM
            self._page.update()

            if not self._test_spotify_credentials():
                self.is_validating = False
                self.step_activity.visible = False
                self.error_text.color = DANGER
                self._page.update()
                return
            self.is_validating = False
            self.step_activity.visible = False
            self.error_text.value = ""
            self.error_text.color = DANGER

        if self.current_step == 1:
            if not self._validate_ai_fields():
                self._page.update()
                return
            # Test AI credentials
            self.is_validating = True
            self.busy_label.value = "Validating AI..."
            self.busy_label.visible = True
            self.step_activity.visible = True
            self.error_text.value = "Validating AI API key..."
            self.error_text.color = FG_DIM
            self._page.update()

            if not self._test_ai_credentials():
                self.is_validating = False
                self.step_activity.visible = False
                self.error_text.color = DANGER
                self._page.update()
                return
            self.is_validating = False
            self.step_activity.visible = False
            self.error_text.value = ""
            self.error_text.color = DANGER

        self.busy_label.visible = False
        self.step_activity.visible = False
        self.current_step += 1
        self._render()
        self._page.update()

    def _on_prev(self, e):
        if self.is_validating:
            return
        self.error_text.value = ""
        self.current_step -= 1
        self._render()
        self._page.update()

    def _on_resize(self, _e: ft.ControlEvent):
        self._render()
        self._page.update()

    def _on_finish(self, e):
        self.busy_label.value = "Opening application..."
        self.busy_label.visible = True
        self.step_activity.visible = True
        self._page.update()
        self.config.save(self.cfg)
        self.on_complete()

    def _on_cancel(self, _e):
        if self.is_validating or self._is_closing or not self.on_cancel:
            return
        self._is_closing = True
        self.busy_label.value = "Closing configuration..."
        self.busy_label.visible = True
        self.step_activity.visible = True
        self._render()
        self._page.update()
        self._page.run_task(self._on_cancel_async)

    async def _on_cancel_async(self):
        await asyncio.sleep(0)
        try:
            if self.on_cancel:
                self.on_cancel()
        except Exception:
            self._is_closing = False
            self._render()
            self._page.update()

    def _select_provider(self, key: str):
        self.provider_var = key
        self.cfg["llm_provider"] = key
        self._render()
        self._page.update()

    def _on_clear_cache(self, _e: ft.ControlEvent):
        removed = clear_cache(include_progress=False)
        self._cache_feedback = (
            "No cache file to delete."
            if removed == 0
            else f"Cache cleared ({removed} item(s) removed)."
        )
        self._cache_feedback_color = FG_DIM
        self._render()
        self._page.update()

    def _on_open_cache_folder(self, _e: ft.ControlEvent):
        ok, message = open_cache_folder(include_progress=False)
        self._cache_feedback = message
        self._cache_feedback_color = FG_DIM if ok else DANGER
        self._render()
        self._page.update()

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
            width=self._form_width,
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
