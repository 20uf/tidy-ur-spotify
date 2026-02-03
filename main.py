"""Entry point for Spotify Ranger — classify liked songs into themed playlists."""

import sys


def main():
    # Lazy imports to allow fast --help / error messages
    from src.auth.spotify_oauth import get_spotify_client
    from src.services.llm_classifier import LLMClassifier
    from src.services.playlist_manager import PlaylistManager
    from src.services.track_fetcher import fetch_liked_songs
    from src.storage.progress_store import ProgressStore
    from src.ui.main_window import MainWindow

    print("Authenticating with Spotify...")
    try:
        sp = get_spotify_client()
        user = sp.current_user()
        print(f"Logged in as: {user['display_name']}")
    except Exception as e:
        print(f"Spotify auth failed: {e}")
        print("Check your .env file (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)")
        sys.exit(1)

    print("Fetching liked songs...")
    tracks = fetch_liked_songs(sp)
    print(f"Found {len(tracks)} liked songs.")

    if not tracks:
        print("No liked songs found. Nothing to classify.")
        sys.exit(0)

    # Initialize services
    classifier = LLMClassifier()
    playlist_mgr = PlaylistManager(sp)
    store = ProgressStore()

    # Optional: audio player
    audio_player = _init_audio()

    # Check for existing progress
    if store.exists():
        print("Found saved progress. Resuming...")

    # Launch GUI
    print("Launching Spotify Ranger GUI...")
    window = MainWindow(
        tracks=tracks,
        classifier=classifier,
        playlist_manager=playlist_mgr,
        progress_store=store,
        audio_player=audio_player,
    )
    window.run()


def _init_audio():
    """Try to initialize pygame for audio preview. Returns None if unavailable."""
    try:
        import io
        import urllib.request

        import pygame

        pygame.mixer.init()

        class AudioPlayer:
            def play(self, url: str):
                pygame.mixer.music.stop()
                response = urllib.request.urlopen(url)
                data = response.read()
                pygame.mixer.music.load(io.BytesIO(data))
                pygame.mixer.music.play()

            def stop(self):
                pygame.mixer.music.stop()

        return AudioPlayer()
    except Exception:
        return None


if __name__ == "__main__":
    main()
