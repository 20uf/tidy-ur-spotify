"""First-launch setup dialog for API keys configuration."""

import tkinter as tk
from tkinter import messagebox

from src.storage import user_config


class SetupDialog:
    """Modal dialog that collects API keys on first launch."""

    def __init__(self):
        self.result = False
        self.cfg = user_config.load()

    def show(self) -> bool:
        """Display the setup dialog. Returns True if config was saved."""
        self.root = tk.Tk()
        self.root.title("Spotify Ranger — Configuration")
        self.root.resizable(False, False)
        self.root.configure(bg="#191414")

        frame = tk.Frame(self.root, bg="#191414", padx=30, pady=20)
        frame.pack()

        tk.Label(
            frame, text="Spotify Ranger", font=("Helvetica", 18, "bold"),
            fg="#1DB954", bg="#191414",
        ).pack(pady=(0, 5))

        tk.Label(
            frame, text="Configure your API keys to get started",
            font=("Helvetica", 10), fg="#B3B3B3", bg="#191414",
        ).pack(pady=(0, 20))

        # Spotify section
        tk.Label(
            frame, text="Spotify API", font=("Helvetica", 12, "bold"),
            fg="#FFFFFF", bg="#191414", anchor="w",
        ).pack(fill="x")

        tk.Label(
            frame, text="Client ID", fg="#B3B3B3", bg="#191414", anchor="w",
        ).pack(fill="x", pady=(8, 0))
        self.client_id_var = tk.StringVar(value=self.cfg.get("spotify_client_id", ""))
        tk.Entry(frame, textvariable=self.client_id_var, width=50).pack(fill="x")

        tk.Label(
            frame, text="Client Secret", fg="#B3B3B3", bg="#191414", anchor="w",
        ).pack(fill="x", pady=(8, 0))
        self.client_secret_var = tk.StringVar(value=self.cfg.get("spotify_client_secret", ""))
        tk.Entry(frame, textvariable=self.client_secret_var, width=50, show="*").pack(fill="x")

        tk.Label(
            frame, text="Redirect URI", fg="#B3B3B3", bg="#191414", anchor="w",
        ).pack(fill="x", pady=(8, 0))
        self.redirect_var = tk.StringVar(value=self.cfg.get("spotify_redirect_uri", "http://localhost:8888/callback"))
        tk.Entry(frame, textvariable=self.redirect_var, width=50).pack(fill="x")

        # LLM section
        tk.Label(
            frame, text="LLM API", font=("Helvetica", 12, "bold"),
            fg="#FFFFFF", bg="#191414", anchor="w",
        ).pack(fill="x", pady=(20, 0))

        tk.Label(
            frame, text="API Key", fg="#B3B3B3", bg="#191414", anchor="w",
        ).pack(fill="x", pady=(8, 0))
        self.llm_key_var = tk.StringVar(value=self.cfg.get("llm_api_key", ""))
        tk.Entry(frame, textvariable=self.llm_key_var, width=50, show="*").pack(fill="x")

        # Buttons
        btn_frame = tk.Frame(frame, bg="#191414")
        btn_frame.pack(pady=(20, 0))

        tk.Button(
            btn_frame, text="Save & Start", command=self._on_save,
            bg="#1DB954", fg="white", font=("Helvetica", 11, "bold"),
            padx=20, pady=5, relief="flat", cursor="hand2",
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            btn_frame, text="Cancel", command=self._on_cancel,
            bg="#535353", fg="white", font=("Helvetica", 11),
            padx=20, pady=5, relief="flat", cursor="hand2",
        ).pack(side="left")

        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.root.mainloop()
        return self.result

    def _on_save(self):
        cid = self.client_id_var.get().strip()
        secret = self.client_secret_var.get().strip()
        llm_key = self.llm_key_var.get().strip()

        if not cid or not secret or not llm_key:
            messagebox.showwarning("Missing fields", "All fields are required.")
            return

        self.cfg["spotify_client_id"] = cid
        self.cfg["spotify_client_secret"] = secret
        self.cfg["spotify_redirect_uri"] = self.redirect_var.get().strip()
        self.cfg["llm_api_key"] = llm_key
        user_config.save(self.cfg)
        self.result = True
        self.root.destroy()

    def _on_cancel(self):
        self.result = False
        self.root.destroy()
