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
pyinstaller --onefile --name spotify-ranger --windowed main.py
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

### Project structure

```
src/
├── auth/spotify_oauth.py        # Spotify OAuth
├── config.py                    # Themes, constants
├── services/
│   ├── track_fetcher.py         # Fetch liked songs
│   ├── llm_classifier.py        # AI classification, multi-provider
│   └── playlist_manager.py      # Spotify playlist management
├── storage/
│   ├── progress_store.py        # Progress save/load (JSON)
│   └── user_config.py           # Persistent config (config.json)
└── ui/
    ├── main_window.py           # Main Tkinter GUI
    └── setup_dialog.py          # 4-step setup wizard
```

### Adding an AI provider

1. Add an entry to `PROVIDERS` in `src/services/llm_classifier.py`
2. Create a `_call_<provider>` function with the same signature
3. Register it in `_PROVIDER_CALLERS`
4. The wizard picks it up automatically

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
