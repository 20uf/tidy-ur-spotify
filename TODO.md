# TODO

## P1 - Blocking UX / stability (next)

- [ ] Fix intermittent **gray qualification screen** after pre-analysis transition
  - expected: full qualification UI rendered (left/current/right + actions)
  - actual: large gray surface with header only in some runs
- [ ] Ensure transition reliability between pages (close setup, step 1 -> step 2, pre-analysis -> qualification)
- [ ] Add a consistent, modern loader overlay for all async transitions
- [ ] Improve live event visibility in pre-analysis (no silent periods, clearer stage messages)

## P1 - Pre-analysis UX coherence

- [x] Remove manual "Open classification" action
- [x] Auto-open qualification when pre-analysis completes
- [x] Lock mode switch while analysis is running
- [x] Make Pause/Cancel actions visually explicit (orange/red)
- [x] Emphasize "current batch" lane with stronger visual contrast
- [ ] Fine-tune color contrast/accessibility for all status colors

## P1 - Configuration UX coherence

- [x] Dedicated configuration workflow (separate from global workflow)
- [x] Cache management only in configuration
- [x] Display cache size + cache files + clear/open actions
- [x] Improve copy consistency across setup texts
- [ ] Add explicit validation status chips (Spotify OK / AI OK)

## Business-oriented tests (intent & workflow)

- [ ] Test full classification workflow: fetch -> classify -> assign -> export
- [ ] Test pause/resume preserves exact state (index, decisions, playlist assignments)
- [ ] Test undo reverts both local state and Spotify playlist
- [ ] Test multi-theme assignment (same track in multiple playlists)
- [ ] Test skip behavior (track marked skipped, not added to any playlist)
- [ ] Test export CSV matches all decisions taken during a session
- [ ] Test LLM suggestion fallback when provider is unreachable
- [ ] Test onboarding wizard produces a valid config.json for each provider
- [ ] Add regression tests for UI transitions (including known gray-screen scenario)

## Architecture and maintainability

- [x] Extract ports: `ClassifierPort`, `PlaylistPort`, `TrackSourcePort`, `ConfigPort`, `ProgressPort`
- [x] Move implementations to adapters
- [x] Introduce domain layer entities
- [x] Create use cases
- [x] UI as driving adapter (use-case orchestration)
- [ ] Introduce Atomic Design structure for UX maintainability (`atoms/`, `molecules/`, `organisms/`, `views/`)
- [ ] Add UI component tests for shared workflow/header and lane components

## Auto-update

- [x] Check latest GitHub release on startup
- [x] Notify user when a new version is available
- [ ] Download and replace binary in-place (or guided download/update flow)
