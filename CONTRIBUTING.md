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

Au premier lancement, un assistant de configuration guide l'utilisateur pour configurer Spotify et le fournisseur IA.

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
│   ├── llm_classifier.py        # Classification IA multi-provider
│   └── playlist_manager.py      # Gestion playlists Spotify
├── storage/
│   ├── progress_store.py        # Sauvegarde progression JSON
│   └── user_config.py           # Config persistante (config.json)
└── ui/
    ├── main_window.py           # GUI principale Tkinter
    └── setup_dialog.py          # Assistant de configuration 4 etapes
```

### Ajouter un fournisseur IA

1. Ajouter l'entree dans `PROVIDERS` dans `src/services/llm_classifier.py`
2. Creer la fonction `_call_<provider>` avec la meme signature
3. L'enregistrer dans `_PROVIDER_CALLERS`
4. Le wizard le detecte automatiquement

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
