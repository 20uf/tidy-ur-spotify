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

- Un compte Spotify (gratuit ou premium)
- Une cle API d'un fournisseur IA (OpenAI recommande, ou Anthropic)

Pas besoin de creer l'app Spotify Developer a l'avance : **l'assistant de configuration te guide a chaque etape**.

## Utilisation

### Premier lancement

Lance le binaire. Un assistant de configuration s'ouvre en 4 etapes :

```
  1. Welcome     →  Presentation
  2. Spotify     →  Guide pas-a-pas pour creer ton app Developer
  3. AI Provider →  Choix du fournisseur IA + cle API
  4. Ready       →  Recap et lancement
```

Les liens vers les dashboards s'ouvrent directement depuis l'assistant. Tout est sauvegarde dans `config.json` a cote de l'executable.

### Fournisseurs IA supportes

| Fournisseur | Modele par defaut | Lien |
|-------------|------------------|------|
| **OpenAI** (recommande) | `gpt-4o-mini` | [platform.openai.com](https://platform.openai.com/api-keys) |
| Anthropic | `claude-3-haiku` | [console.anthropic.com](https://console.anthropic.com) |

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
