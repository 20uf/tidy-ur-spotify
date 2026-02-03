# Spotify Ranger

Classe automatiquement tes titres Spotify "Liked Songs" dans des playlists thematiques grace a l'IA.

| Playlist | Style |
|----------|-------|
| Ambiance | Mid-tempo, groovy, warm, melodic |
| Let's Dance | Upbeat, danceable, hits de soiree |

## Installation

### Telecharger le binaire

Rendez-vous sur la page [Releases](../../releases) et telecharge le fichier correspondant a ton systeme :

| Systeme | Fichier |
|---------|---------|
| Windows | `spotify-ranger.exe` |
| macOS   | `spotify-ranger-macos` |
| Linux   | `spotify-ranger-linux` |

> Les versions **alpha** (pre-release) sont disponibles pour tester les dernieres fonctionnalites.

### Pre-requis

Avant de lancer l'application, tu as besoin de deux choses :

**1. Une app Spotify Developer**

- Va sur [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
- Cree une nouvelle application
- Ajoute `http://localhost:8888/callback` comme Redirect URI
- Note le **Client ID** et le **Client Secret**

**2. Une cle API LLM**

- Va sur [console.anthropic.com](https://console.anthropic.com)
- Cree une cle API

## Utilisation

### Premier lancement

Lance le binaire. Une fenetre de configuration s'ouvre pour saisir tes cles API :

- Spotify Client ID
- Spotify Client Secret
- Cle API LLM

Les cles sont sauvegardees dans un fichier `config.json` a cote de l'executable. Tu n'auras pas a les re-saisir.

### Flux de travail

1. **Connexion** — Un navigateur s'ouvre pour autoriser l'acces a ton compte Spotify
2. **Chargement** — L'app recupere tous tes titres "Liked Songs"
3. **Classification** — Pour chaque titre, l'IA propose une playlist

### Interface

```
  [3 titres passes]     <- historique
  > Titre actuel        <- avec suggestion IA
  [3 titres a venir]    <- preview
```

### Raccourcis clavier

| Touche | Action |
|--------|--------|
| `1` | Ajouter a **Ambiance** |
| `2` | Ajouter a **Let's Dance** |
| `S` | Skip (passer) |
| `<-` | Undo (annuler la derniere action) |
| `Echap` | Pause (sauvegarde et quitte) |

- Un titre peut etre dans **plusieurs playlists** (appuie sur `1` puis `2`)
- La progression est sauvegardee automatiquement — tu peux reprendre plus tard
- Un fichier `export.csv` est genere a la fin avec toutes les decisions

### Versions

- **Stable** (`v1.0.0`, `v1.1.0`...) : versions testees et validees
- **Alpha** (`alpha-xxx`) : versions de test, peuvent contenir des bugs

## Licence

MIT
