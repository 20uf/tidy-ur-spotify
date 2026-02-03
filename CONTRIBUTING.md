# Contribuer

## Setup dev

```bash
git clone https://github.com/20uf/tidy-ur-spotify.git
cd tidy-ur-spotify
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Lancer les tests

```bash
python -m pytest tests/ -v
```

## Lancer l'app en local

```bash
python main.py
```

Au premier lancement, une fenetre de configuration s'ouvre pour les cles API.

## Builder un binaire

```bash
pyinstaller --onefile --name spotify-ranger --windowed main.py
```

Le binaire est genere dans `dist/`.

## Workflow CI/CD

Le fichier `.github/workflows/build.yml` gere tout le pipeline :

### Build automatique

Les binaires (Linux, macOS, Windows) sont compiles automatiquement sur :
- Chaque **push** sur `main`
- Chaque **pull request** vers `main`
- Chaque **tag** `v*`

### Release stable

Creer un tag pour publier une release :

```bash
git tag v1.0.0
git push --tags
```

Les 3 binaires sont attaches automatiquement a la release GitHub.

### Release alpha (a la volee)

Pour tester sans creer de tag :

1. Va sur **Actions** > **Build binaries**
2. Clique **Run workflow**
3. Remplis le champ `alpha_tag` (ex: `alpha.1`, `alpha.3`)
4. Les binaires sont publies en **pre-release** sur la page Releases

### Arborescence

```
src/
├── auth/spotify_oauth.py        # OAuth Spotify
├── config.py                    # Themes, constantes
├── services/
│   ├── track_fetcher.py         # Recuperation liked songs
│   ├── llm_classifier.py        # Classification IA par batch
│   └── playlist_manager.py      # Gestion playlists Spotify
├── storage/
│   ├── progress_store.py        # Sauvegarde progression JSON
│   └── user_config.py           # Config persistante (config.json)
└── ui/
    ├── main_window.py           # GUI principale Tkinter
    └── setup_dialog.py          # Dialog config premier lancement
```

## Convention de commits

Format : `type: description`

| Type | Usage |
|------|-------|
| `feat` | Nouvelle fonctionnalite |
| `fix` | Correction de bug |
| `refactor` | Refactoring sans changement fonctionnel |
| `ci` | Changements CI/CD |
| `chore` | Maintenance, nettoyage |
| `docs` | Documentation |
