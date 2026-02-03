"""Multi-step onboarding wizard for first-launch configuration.

Step 1: Welcome
Step 2: Spotify Developer setup (guided)
Step 3: AI provider selection + API key
Step 4: Confirmation
"""

import tkinter as tk
from tkinter import messagebox
import webbrowser

from src.services.llm_classifier import PROVIDERS
from src.storage import user_config
from src.version import __version__

# ── Theme ──────────────────────────────────────────────────────────

BG = "#0D1117"
BG_CARD = "#161B22"
BG_INPUT = "#21262D"
FG = "#E6EDF3"
FG_DIM = "#8B949E"
FG_LINK = "#58A6FF"
ACCENT = "#1DB954"
ACCENT_HOVER = "#1ED760"
BORDER = "#30363D"
DANGER = "#F85149"
FONT = "Segoe UI"
FONT_MONO = "Consolas"


class SetupDialog:
    """Multi-step onboarding wizard."""

    def __init__(self):
        self.result = False
        self.cfg = user_config.load()
        self.current_step = 0
        self.steps = [
            self._build_welcome,
            self._build_spotify_step,
            self._build_ai_step,
            self._build_confirm_step,
        ]
        self.step_titles = ["Welcome", "Spotify", "AI Provider", "Ready"]

    def show(self) -> bool:
        self.root = tk.Tk()
        self.root.title(f"Spotify Ranger {__version__}")
        self.root.geometry("620x520")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        # ── Step indicator bar ─────────────────────────────
        self.indicator_frame = tk.Frame(self.root, bg=BG, height=60)
        self.indicator_frame.pack(fill=tk.X, padx=30, pady=(25, 0))
        self.indicator_frame.pack_propagate(False)

        # ── Content area ───────────────────────────────────
        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)

        # ── Bottom nav ─────────────────────────────────────
        self.nav_frame = tk.Frame(self.root, bg=BG, height=50)
        self.nav_frame.pack(fill=tk.X, padx=30, pady=(0, 20))
        self.nav_frame.pack_propagate(False)

        self._show_step(0)

        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.root.mainloop()
        return self.result

    # ── Navigation ─────────────────────────────────────────────────

    def _show_step(self, idx: int):
        self.current_step = idx
        self._draw_indicator()

        for w in self.content.winfo_children():
            w.destroy()
        for w in self.nav_frame.winfo_children():
            w.destroy()

        self.steps[idx]()
        self._draw_nav()

    def _draw_indicator(self):
        for w in self.indicator_frame.winfo_children():
            w.destroy()

        container = tk.Frame(self.indicator_frame, bg=BG)
        container.pack(expand=True)

        for i, title in enumerate(self.step_titles):
            # Circle
            is_done = i < self.current_step
            is_current = i == self.current_step
            circle_bg = ACCENT if (is_done or is_current) else BG_INPUT
            circle_fg = BG if (is_done or is_current) else FG_DIM
            text = "\u2713" if is_done else str(i + 1)

            circle = tk.Label(
                container, text=text, font=(FONT, 10, "bold"),
                bg=circle_bg, fg=circle_fg, width=3, height=1,
            )
            circle.grid(row=0, column=i * 2, padx=(0, 0))

            label = tk.Label(
                container, text=title, font=(FONT, 9),
                bg=BG, fg=FG if is_current else FG_DIM,
            )
            label.grid(row=1, column=i * 2, padx=(0, 0))

            # Connector line
            if i < len(self.step_titles) - 1:
                line_color = ACCENT if is_done else BORDER
                line = tk.Frame(container, bg=line_color, height=2, width=50)
                line.grid(row=0, column=i * 2 + 1, padx=5, sticky="ew")

    def _draw_nav(self):
        is_first = self.current_step == 0
        is_last = self.current_step == len(self.steps) - 1

        if not is_first:
            self._btn(self.nav_frame, "\u2190  Back", self._prev, style="ghost").pack(side=tk.LEFT)

        if is_last:
            self._btn(self.nav_frame, "Launch Spotify Ranger  \u2192", self._on_finish, style="accent").pack(side=tk.RIGHT)
        else:
            self._btn(self.nav_frame, "Continue  \u2192", self._next, style="accent").pack(side=tk.RIGHT)

    def _next(self):
        if self.current_step == 1 and not self._validate_spotify():
            return
        if self.current_step == 2 and not self._validate_ai():
            return
        self._show_step(self.current_step + 1)

    def _prev(self):
        self._show_step(self.current_step - 1)

    # ── Step 0: Welcome ────────────────────────────────────────────

    def _build_welcome(self):
        f = self.content

        tk.Label(f, text="\U0001F3B5", font=(FONT, 40), bg=BG, fg=ACCENT).pack(pady=(20, 5))
        tk.Label(
            f, text="Spotify Ranger", font=(FONT, 24, "bold"), bg=BG, fg=FG,
        ).pack()
        tk.Label(
            f, text="Classe tes Liked Songs dans des playlists\nthematiques grace a l'IA.",
            font=(FONT, 12), bg=BG, fg=FG_DIM, justify="center",
        ).pack(pady=(8, 25))

        card = self._card(f)
        tk.Label(
            card, text="Pour commencer, tu auras besoin de :",
            font=(FONT, 11), bg=BG_CARD, fg=FG, anchor="w",
        ).pack(fill=tk.X, pady=(0, 10))

        for icon, text in [
            ("\U0001F3A7", "Un compte Spotify (gratuit ou premium)"),
            ("\U0001F511", "Une app Spotify Developer (guide a l'etape suivante)"),
            ("\U0001F916", "Une cle API d'un fournisseur IA (OpenAI, ...)"),
        ]:
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill=tk.X, pady=3)
            tk.Label(row, text=icon, font=(FONT, 13), bg=BG_CARD, fg=ACCENT).pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(row, text=text, font=(FONT, 10), bg=BG_CARD, fg=FG_DIM, anchor="w").pack(side=tk.LEFT)

    # ── Step 1: Spotify ────────────────────────────────────────────

    def _build_spotify_step(self):
        f = self.content

        tk.Label(
            f, text="Configuration Spotify", font=(FONT, 18, "bold"), bg=BG, fg=FG,
        ).pack(anchor="w", pady=(5, 15))

        # Instructions card
        card = self._card(f)
        tk.Label(
            card, text="Cree ton app Spotify Developer :", font=(FONT, 11, "bold"),
            bg=BG_CARD, fg=FG, anchor="w",
        ).pack(fill=tk.X, pady=(0, 8))

        steps = [
            "Va sur le Spotify Developer Dashboard",
            "Clique sur \"Create App\"",
            "Nom : ce que tu veux  /  Redirect URI :",
            "http://localhost:8888/callback",
            "Copie le Client ID et Client Secret ci-dessous",
        ]
        for i, txt in enumerate(steps):
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill=tk.X, pady=1)
            if txt.startswith("http"):
                tk.Label(row, text="     ", bg=BG_CARD).pack(side=tk.LEFT)
                tk.Label(
                    row, text=txt, font=(FONT_MONO, 9), bg=BG_INPUT, fg=ACCENT,
                    padx=8, pady=2, relief="flat",
                ).pack(side=tk.LEFT)
            else:
                tk.Label(
                    row, text=f"  {i + 1}.", font=(FONT, 10, "bold"), bg=BG_CARD, fg=ACCENT, width=4, anchor="e",
                ).pack(side=tk.LEFT)
                tk.Label(row, text=txt, font=(FONT, 10), bg=BG_CARD, fg=FG_DIM).pack(side=tk.LEFT)

        link = tk.Label(
            card, text="\U0001F517  Ouvrir le Spotify Developer Dashboard",
            font=(FONT, 10, "underline"), bg=BG_CARD, fg=FG_LINK, cursor="hand2",
        )
        link.pack(anchor="w", pady=(10, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open("https://developer.spotify.com/dashboard"))

        # Input fields
        fields = tk.Frame(f, bg=BG)
        fields.pack(fill=tk.X, pady=(15, 0))

        self.client_id_var = tk.StringVar(value=self.cfg.get("spotify_client_id", ""))
        self._field(fields, "Client ID", self.client_id_var)

        self.client_secret_var = tk.StringVar(value=self.cfg.get("spotify_client_secret", ""))
        self._field(fields, "Client Secret", self.client_secret_var, show="*")

    def _validate_spotify(self) -> bool:
        cid = self.client_id_var.get().strip()
        secret = self.client_secret_var.get().strip()
        if not cid or not secret:
            messagebox.showwarning("Champs requis", "Le Client ID et le Client Secret sont obligatoires.")
            return False
        self.cfg["spotify_client_id"] = cid
        self.cfg["spotify_client_secret"] = secret
        return True

    # ── Step 2: AI Provider ────────────────────────────────────────

    def _build_ai_step(self):
        f = self.content

        tk.Label(
            f, text="Fournisseur IA", font=(FONT, 18, "bold"), bg=BG, fg=FG,
        ).pack(anchor="w", pady=(5, 15))

        tk.Label(
            f, text="Choisis le service IA pour classer tes titres :",
            font=(FONT, 11), bg=BG, fg=FG_DIM, anchor="w",
        ).pack(fill=tk.X, pady=(0, 10))

        # Provider radio cards
        self.provider_var = tk.StringVar(value=self.cfg.get("llm_provider", "openai"))
        self.provider_cards_frame = tk.Frame(f, bg=BG)
        self.provider_cards_frame.pack(fill=tk.X)

        self._provider_cards = {}
        for key, info in PROVIDERS.items():
            self._provider_cards[key] = self._provider_card(
                self.provider_cards_frame, key, info,
            )

        # API key field
        key_frame = tk.Frame(f, bg=BG)
        key_frame.pack(fill=tk.X, pady=(15, 0))

        self.llm_key_var = tk.StringVar(value=self.cfg.get("llm_api_key", ""))
        self._field(key_frame, "API Key", self.llm_key_var, show="*")

        # Link to get key (updates with provider)
        self.key_link_frame = tk.Frame(f, bg=BG)
        self.key_link_frame.pack(fill=tk.X, pady=(5, 0))
        self._update_key_link()

    def _provider_card(self, parent, key: str, info: dict) -> tk.Frame:
        is_selected = self.provider_var.get() == key

        card = tk.Frame(
            parent, bg=BG_CARD if is_selected else BG_INPUT,
            highlightbackground=ACCENT if is_selected else BORDER,
            highlightthickness=2, padx=15, pady=10, cursor="hand2",
        )
        card.pack(fill=tk.X, pady=3)

        row = tk.Frame(card, bg=card["bg"])
        row.pack(fill=tk.X)

        indicator = "\u25C9" if is_selected else "\u25CB"
        ind_color = ACCENT if is_selected else FG_DIM
        tk.Label(
            row, text=indicator, font=(FONT, 14), bg=card["bg"], fg=ind_color,
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            row, text=info["label"], font=(FONT, 12, "bold"),
            bg=card["bg"], fg=FG,
        ).pack(side=tk.LEFT)

        if key == "openai":
            tk.Label(
                row, text="Recommande", font=(FONT, 9),
                bg=ACCENT, fg=BG, padx=6, pady=1,
            ).pack(side=tk.RIGHT)

        model_text = f"Modele par defaut : {info['default_model']}"
        tk.Label(
            card, text=model_text, font=(FONT, 9), bg=card["bg"], fg=FG_DIM, anchor="w",
        ).pack(fill=tk.X, pady=(4, 0))

        for widget in [card, row] + list(row.winfo_children()) + list(card.winfo_children()):
            widget.bind("<Button-1>", lambda e, k=key: self._select_provider(k))

        return card

    def _select_provider(self, key: str):
        self.provider_var.set(key)
        # Rebuild cards
        for w in self.provider_cards_frame.winfo_children():
            w.destroy()
        self._provider_cards = {}
        for k, info in PROVIDERS.items():
            self._provider_cards[k] = self._provider_card(
                self.provider_cards_frame, k, info,
            )
        self._update_key_link()

    def _update_key_link(self):
        for w in self.key_link_frame.winfo_children():
            w.destroy()
        provider = self.provider_var.get()
        info = PROVIDERS[provider]
        link = tk.Label(
            self.key_link_frame,
            text=f"\U0001F511  Obtenir une cle {info['name']}",
            font=(FONT, 10, "underline"), bg=BG, fg=FG_LINK, cursor="hand2",
        )
        link.pack(anchor="w")
        link.bind("<Button-1>", lambda e, url=info["url"]: webbrowser.open(url))

    def _validate_ai(self) -> bool:
        key = self.llm_key_var.get().strip()
        if not key:
            messagebox.showwarning("Champ requis", "La cle API est obligatoire.")
            return False
        self.cfg["llm_provider"] = self.provider_var.get()
        self.cfg["llm_api_key"] = key
        return True

    # ── Step 3: Confirm ────────────────────────────────────────────

    def _build_confirm_step(self):
        f = self.content

        tk.Label(f, text="\u2705", font=(FONT, 40), bg=BG, fg=ACCENT).pack(pady=(20, 5))
        tk.Label(
            f, text="Tout est pret !", font=(FONT, 20, "bold"), bg=BG, fg=FG,
        ).pack()
        tk.Label(
            f, text="Ta configuration est enregistree.\nVoici un recap :",
            font=(FONT, 11), bg=BG, fg=FG_DIM, justify="center",
        ).pack(pady=(5, 20))

        card = self._card(f)
        provider_info = PROVIDERS[self.cfg.get("llm_provider", "openai")]

        rows = [
            ("Spotify", f"Client ID: {self.cfg.get('spotify_client_id', '')[:12]}..."),
            ("Fournisseur IA", provider_info["label"]),
            ("Modele", provider_info["default_model"]),
            ("API Key", "\u2022" * 16),
        ]
        for label, value in rows:
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill=tk.X, pady=3)
            tk.Label(
                row, text=label, font=(FONT, 10, "bold"), bg=BG_CARD, fg=FG_DIM, width=16, anchor="w",
            ).pack(side=tk.LEFT)
            tk.Label(
                row, text=value, font=(FONT, 10), bg=BG_CARD, fg=FG, anchor="w",
            ).pack(side=tk.LEFT)

    # ── Finish / Cancel ────────────────────────────────────────────

    def _on_finish(self):
        user_config.save(self.cfg)
        self.result = True
        self.root.destroy()

    def _on_cancel(self):
        self.result = False
        self.root.destroy()

    # ── UI helpers ─────────────────────────────────────────────────

    def _card(self, parent) -> tk.Frame:
        card = tk.Frame(
            parent, bg=BG_CARD,
            highlightbackground=BORDER, highlightthickness=1,
            padx=18, pady=14,
        )
        card.pack(fill=tk.X, pady=3)
        return card

    def _field(self, parent, label: str, var: tk.StringVar, show: str = ""):
        tk.Label(
            parent, text=label, font=(FONT, 10, "bold"), bg=BG, fg=FG_DIM, anchor="w",
        ).pack(fill=tk.X, pady=(8, 3))
        entry = tk.Entry(
            parent, textvariable=var, font=(FONT_MONO, 11),
            bg=BG_INPUT, fg=FG, insertbackground=FG,
            relief="flat", highlightbackground=BORDER, highlightthickness=1,
            show=show,
        )
        entry.pack(fill=tk.X, ipady=6)
        return entry

    def _btn(self, parent, text: str, command, style: str = "accent") -> tk.Button:
        if style == "accent":
            bg, fg_c, font_w = ACCENT, BG, "bold"
        else:
            bg, fg_c, font_w = BG, FG_DIM, "normal"

        btn = tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg_c, font=(FONT, 11, font_w),
            relief="flat", padx=18, pady=6, cursor="hand2",
            activebackground=ACCENT_HOVER if style == "accent" else BG_INPUT,
            activeforeground=BG if style == "accent" else FG,
            borderwidth=0,
        )
        return btn
