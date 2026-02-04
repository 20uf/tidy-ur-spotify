# Contributing

## Dev setup

```bash
git clone https://github.com/20uf/tidy-ur-spotify.git
cd tidy-ur-spotify
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run tests

```bash
python -m pytest tests/ -v
```

## Run the app locally

```bash
python main.py
```

On first launch, a setup wizard guides you through Spotify and AI provider configuration.

## Build a binary

```bash
flet pack main.py --name tidy-ur-spotify
```

Output goes to `dist/`.

## CI/CD workflow

Everything is handled by `.github/workflows/build.yml`:

### Automatic builds

Binaries (Linux, macOS, Windows) are compiled on:
- Every **push** to `main`
- Every **pull request** targeting `main`
- Every **tag** matching `v*`

### Stable release

Create a tag to publish a release:

```bash
git tag v1.0.0
git push --tags
```

All 3 binaries are automatically attached to the GitHub release.

### Alpha release (on-demand)

To test without creating a tag:

1. Go to **Actions** > **Build binaries**
2. Click **Run workflow**
3. Fill in the `alpha_tag` field (e.g. `alpha.1`, `alpha.3`)
4. Binaries are published as a **pre-release** on the Releases page

## Project structure (hexagonal architecture)

```
src/
├── domain/
│   ├── model.py              # Track, Decision, ClassificationSession, Theme, Suggestion
│   └── ports.py              # ClassifierPort, PlaylistPort, TrackSourcePort, ConfigPort, ProgressPort
├── adapters/
│   ├── classifier/
│   │   ├── _prompt.py        # Shared prompt building & parsing
│   │   ├── openai_adapter.py # OpenAI classifier
│   │   └── anthropic_adapter.py  # Anthropic classifier
│   ├── spotify/
│   │   ├── auth.py           # Spotify OAuth
│   │   ├── track_adapter.py  # Fetch liked songs
│   │   └── playlist_adapter.py   # Playlist management
│   ├── config/
│   │   └── json_config_adapter.py  # JSON config persistence
│   └── progress/
│       └── json_progress_adapter.py  # JSON progress persistence
├── usecases/
│   ├── classify_track.py     # Classify / skip a track
│   ├── undo_decision.py      # Undo last decision
│   ├── export_session.py     # Export to CSV
│   └── resume_session.py     # Resume or start session
├── ui/
│   ├── app.py                # Main Flet app
│   ├── theme.py              # UI color constants
│   ├── setup_view.py         # 4-step onboarding wizard
│   └── classify_view.py      # Classification sliding window
└── version.py
```

### Adding an AI provider

1. Create a new adapter in `src/adapters/classifier/` implementing `ClassifierPort`
2. Add an entry to `PROVIDERS` in `src/adapters/classifier/__init__.py`
3. Add the provider option in `src/ui/app.py` factory logic
4. The setup wizard picks it up automatically

## Commit conventions

Format: `type: description`

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Refactoring without functional change |
| `ci` | CI/CD changes |
| `chore` | Maintenance, cleanup |
| `docs` | Documentation |
