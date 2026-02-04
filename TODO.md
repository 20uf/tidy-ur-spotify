# TODO

## Business-oriented tests (intent & workflow)

- [ ] Test full classification workflow: fetch → classify → assign → export
- [ ] Test pause/resume preserves exact state (index, decisions, playlist assignments)
- [ ] Test undo reverts both local state and Spotify playlist
- [ ] Test multi-theme assignment (same track in multiple playlists)
- [ ] Test skip behavior (track marked skipped, not added to any playlist)
- [ ] Test export CSV matches all decisions taken during a session
- [ ] Test LLM suggestion fallback when provider is unreachable
- [ ] Test onboarding wizard produces a valid config.json for each provider

## Hexagonal architecture

- [x] Extract ports: `ClassifierPort`, `PlaylistPort`, `TrackSourcePort`, `ConfigPort`, `ProgressPort`
- [x] Move current implementations to adapters: `OpenAIAdapter`, `AnthropicAdapter`, `SpotifyPlaylistAdapter`, `SpotifyTrackAdapter`, `JsonConfigAdapter`, `JsonProgressAdapter`
- [x] Introduce domain layer: `Track`, `Decision`, `ClassificationSession`, `Theme`, `Suggestion` as pure domain objects
- [x] Create use cases: `ClassifyTrackUseCase`, `UndoDecisionUseCase`, `ExportSessionUseCase`, `ResumeSessionUseCase`
- [x] UI becomes a driving adapter calling use cases, not services directly
- [x] Tests run against ports with in-memory adapters (no Spotify/LLM calls)

## UI migration

- [x] Replace Tkinter with Flet (Flutter-based native window)
- [x] Setup wizard as Flet view
- [x] Classification view as Flet view
- [ ] Audio preview (Flet audio support)
- [ ] Mobile support (iOS/Android via Flet)

## Auto-update

- [x] Check latest GitHub release on startup (compare `__version__` vs remote tag)
- [x] Notify user when a new version is available (banner with download link)
- [ ] Download and replace binary in-place (or prompt user to download)
