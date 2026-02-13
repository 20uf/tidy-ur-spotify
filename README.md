# Tidy ur Spotify

> **Prototype (v0.2.0-alpha)** — This project is in early development and open to everyone. Feedback, ideas and contributions are welcome!

> ⚠️ **On hold** — Spotify has temporarily disabled new Developer app registrations. The project is functional but new users cannot create the required Spotify credentials until Spotify re-enables registrations. [Check status](https://developer.spotify.com/dashboard)

Automatically classify your Spotify "Liked Songs" into themed playlists using AI.

| Playlist | Style |
|----------|-------|
| Ambiance | Mid-tempo, groovy, warm, melodic |
| Let's Dance | Upbeat, danceable, party hits |

## Installation

### Download the binary

Head to the [Releases](../../releases) page and download the file matching your system:

| System  | File |
|---------|------|
| Windows | `tidy-ur-spotify.exe` |
| macOS   | `tidy-ur-spotify-macos` |
| Linux   | `tidy-ur-spotify-linux` |

> **Alpha** (pre-release) builds are available to test the latest features.

### Prerequisites

- A Spotify account (free or premium)
- An AI provider API key (OpenAI recommended, or Anthropic)

No need to create a Spotify Developer app beforehand — **the setup wizard guides you through every step**.

## Usage

### First launch

Run the binary. A setup wizard opens in 4 steps:

```
  1. Welcome     →  Overview
  2. Spotify     →  Step-by-step guide to create your Developer app
  3. AI Provider →  Pick your AI provider + enter API key
  4. Ready       →  Summary and launch
```

Dashboard links open directly from the wizard. Everything is saved to `config.json` next to the executable.

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
| `S` | Skip |
| `←` | Undo last action |
| `Esc` | Pause (save & quit) |

- A track can be in **multiple playlists** (press `1` then `2`)
- Progress is saved automatically — resume anytime
- An `export.csv` file is generated at the end with all decisions

### Versions

- **Stable** (`v1.0.0`, `v1.1.0`…): tested and validated releases
- **Alpha** (`alpha-xxx`): test builds, may contain bugs

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
