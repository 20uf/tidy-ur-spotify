# Contributing

## Dev setup

```bash
git clone https://github.com/20uf/tidy-ur-spotify.git
cd tidy-ur-spotify
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Or use the one-command bootstrap:

```bash
./scripts/dev.sh
```

## Run tests

```bash
python3 -m pytest tests/ -v
```

### Test strategy

- Prioritize **user journey/business workflow tests** (`tests/user_journeys/`)
- Add **integration tests** only where adapters or persistence behavior must be validated
- Keep **unit tests** for non-trivial logic only (e.g. parsing/version comparison)

## Run the app locally

```bash
python3 main.py
```

On first launch, a setup wizard guides you through Spotify and AI provider configuration.

To run safely in audit mode without touching Spotify playlists:

```bash
TIDY_SPOTIFY_SIMULATION=1 python3 main.py
```

## Build a binary

```bash
flet pack main.py --name tidy-ur-spotify
```

Output goes to `dist/`.

## CI/CD workflow

Release automation is split across:
- `.github/workflows/release-please.yml` for automated versioning + release PRs
- `.github/workflows/build.yml` for tests + binary builds

### Automatic builds

Binaries (Linux, macOS, Windows) are compiled on:
- Every **push** to `main`
- Every **pull request** targeting `main`
- Every **tag** matching `v*`

### Automated releases

Releases are automated via **Release Please**:
1. Merge commits to `main` using Conventional Commits (`feat:`, `fix:`, etc.)
2. Release Please updates or opens a release PR with version bump + changelog
3. Merge that PR to publish a GitHub release and tag (`v*`)
4. Build workflow attaches platform binaries to the release

For full automation of downstream workflows on release tags, configure a repository secret:
- `RELEASE_PLEASE_TOKEN` (GitHub PAT with `contents`, `pull_requests`, `issues`)

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
