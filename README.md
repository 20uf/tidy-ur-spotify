# Tidy ur Spotify

> **Prototype (v0.2.0-alpha)** — This project is in early development and open to everyone. Feedback, ideas and contributions are welcome!

<p align="center">
  <img src="assets/branding/logo-in-app.png" alt="Tidy ur Spotify logo" width="320" />
</p>

Automatically classify your Spotify "Liked Songs" into themed playlists using AI.

**Current slogan:** `Sort your liked songs with AI, keep full control.`

### Slogan candidates

- `From liked chaos to playlist clarity.`
- `Classify faster, listen smarter.`
- `Your taste, organized with AI.`
- `Clean up likes, keep the vibe.`

## Disclaimer

This project is an experimental tool for advanced users. It is provided as-is, with no warranty of availability, reliability, or outcome.
You are solely responsible for actions performed on your Spotify account (playlist creation/modification, classification, deletion, etc.).
Use Audit mode to validate runs without writing playlist changes.

| Playlist | Style |
|----------|-------|
| Ambiance | Mid-tempo, groovy, warm, melodic |
| Let's Dance | Upbeat, danceable, party hits |
| Original Soundtracks | Film/series OST, cinematic and orchestral tracks |

## Installation

### Download the binary

Head to the [Releases](../../releases) page and download the file matching your system:

| System  | File |
|---------|------|
| Windows | `tidy-ur-spotify.exe` |
| macOS   | `tidy-ur-spotify-macos` |
| Linux   | `tidy-ur-spotify-linux` |

> **Alpha** (pre-release) builds are available to test the latest features.

### Run locally (dev)

Python `3.11` is recommended (CI baseline).

```bash
./scripts/dev.sh
```

Equivalent manual steps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Prerequisites

- A Spotify account (free or premium)
- An AI provider API key (OpenAI recommended, or Anthropic)

No need to create a Spotify Developer app beforehand — **the setup wizard guides you through every step**.

## Usage

### First launch

Run the binary. The onboarding flow is:

```
  0. Legal gate (mandatory acknowledgement)
  1. Configuration wizard (3 steps):
     - Spotify credentials
     - AI provider and key
     - Validation and launch
  2. Pre-analysis screen (batch processing + live event stream)
  3. Qualification screen (manual decision with AI suggestions)
```

Dashboard links open directly from the wizard. Everything is saved to `config.json` next to the executable.

Sensitive credentials (`spotify_client_secret`, `llm_api_key`) are stored in your OS secure keychain when available.
If no keychain backend is available, the app falls back to local file storage.

### Auto-update

On startup, the app checks GitHub for newer releases. If a new version is available, a banner appears with a download link. No action is required — you choose when to update.

### Supported AI providers

| Provider | Default model | Link |
|----------|--------------|------|
| **OpenAI** (recommended) | `gpt-4o-mini` | [platform.openai.com](https://platform.openai.com/api-keys) |
| Anthropic | `claude-3-haiku` | [console.anthropic.com](https://console.anthropic.com) |

### Workflow

1. **Login** — A browser opens to authorize access to your Spotify account
2. **Loading** — The app fetches all your "Liked Songs"
3. **Classification** — For each track, the AI suggests a playlist

### Audit mode (safe)

If you want to test without modifying any Spotify playlist, enable **Audit mode** from the post-login pre-analysis screen, or force it via env var:

```bash
TIDY_SPOTIFY_SIMULATION=1 python main.py
```

In audit mode, classification/export/resume still work, but playlist add/remove calls are no-op.

The classifier uses Spotify metadata available in development mode, including title/artist/album plus `release_date`, `duration_ms`, and `explicit`.

### Persistent cache

To avoid re-calling AI for tracks already analyzed, suggestions are cached locally in `classification_cache.json`.
Cache keys include provider/model + theme config + track metadata fingerprint.

Spotify auth token cache is stored in `spotify_auth_cache.json`.

Optional env vars:

```bash
TIDY_SPOTIFY_CACHE_FILE=logs/my-cache.json
TIDY_SPOTIFY_DISABLE_PERSISTENT_CACHE=1
```

### Local cache management

In the configuration view, a dedicated **Local cache** section lets you:

- see total cache size,
- see cache file presence,
- clear cache,
- open cache folder.

Default cache files (in project/app folder):

- `classification_cache.json`
- `spotify_auth_cache.json`

Legacy `.spotify_cache` is still read/cleaned for compatibility.

## Known issues (alpha)

- Qualification screen can occasionally render as a large gray area after transition from pre-analysis.
- Perceived latency can happen during screen transitions (config close, step change, pre-analysis to qualification), even with loader feedback.
- UI polish is still in progress (button hierarchy, color balance, responsive behavior consistency).

See `TODO.md` for current priority fixes and remaining work.

### Interface

```
  [3 past tracks]       ← history
  > Current track       ← with AI suggestion
  [3 upcoming tracks]   ← preview
```

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `1` | Add to **Ambiance** |
| `2` | Add to **Let's Dance** |
| `3` | Add to **Original Soundtracks** |
| `S` | Skip |
| `←` | Undo last action |
| `Esc` | Pause (save & quit) |

- A track can be in **multiple playlists** (press `1` then `2`)
- Progress is saved automatically — resume anytime
- An `export.csv` file is generated at the end with all decisions

### Versions

- **Stable** (`v1.0.0`, `v1.1.0`…): tested and validated releases
- **Alpha** (`alpha-xxx`): test builds, may contain bugs

### Automated versioning

Versioning and release PRs are automated via **Release Please** based on Conventional Commits (`feat:`, `fix:`, etc.).  
The application version source of truth is [`src/version.py`](src/version.py).

## Architecture

The project uses a **hexagonal architecture** (ports & adapters):

```
src/
├── domain/          # Pure domain: Track, Decision, Session, Ports
├── adapters/        # Infrastructure implementations
│   ├── classifier/  # OpenAI, Anthropic LLM adapters
│   ├── spotify/     # Spotify API (auth, tracks, playlists)
│   ├── config/      # JSON config persistence
│   └── progress/    # JSON progress persistence
├── usecases/        # Application use cases
└── ui/              # Flet UI (driving adapter)
```

## License

MIT
