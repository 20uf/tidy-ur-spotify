#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "error: $PYTHON_BIN not found"
  exit 1
fi

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

export PYTHONUNBUFFERED=1
export TIDY_SPOTIFY_LOG_LEVEL="${TIDY_SPOTIFY_LOG_LEVEL:-INFO}"
echo "Running with logs: TIDY_SPOTIFY_LOG_LEVEL=$TIDY_SPOTIFY_LOG_LEVEL"
if [ "$TIDY_SPOTIFY_LOG_LEVEL" = "DEBUG" ] && [ -z "${TIDY_SPOTIFY_LOG_FILE:-}" ]; then
  export TIDY_SPOTIFY_LOG_FILE="logs/tidy-ur-spotify-debug.log"
fi
if [ -n "${TIDY_SPOTIFY_LOG_FILE:-}" ]; then
  echo "Debug log file: $TIDY_SPOTIFY_LOG_FILE"
fi

python main.py
