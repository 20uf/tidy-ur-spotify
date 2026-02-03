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

- [ ] Extract ports: `ClassifierPort`, `PlaylistPort`, `TrackSourcePort`, `ConfigPort`
- [ ] Move current implementations to adapters: `OpenAIAdapter`, `AnthropicAdapter`, `SpotifyPlaylistAdapter`, `SpotifyTrackAdapter`, `JsonConfigAdapter`
- [ ] Introduce domain layer: `Track`, `Decision`, `ClassificationSession` as pure domain objects (no framework dependency)
- [ ] Create use cases: `ClassifyTrackUseCase`, `UndoDecisionUseCase`, `ExportSessionUseCase`, `ResumeSessionUseCase`
- [ ] UI becomes a driving adapter calling use cases, not services directly
- [ ] Tests run against ports with in-memory adapters (no Spotify/LLM calls)

## Auto-update

- [ ] Check latest GitHub release on startup (compare `__version__` vs remote tag)
- [ ] Notify user when a new version is available
- [ ] Download and replace binary in-place (or prompt user to download)
