#!/usr/bin/env sh
# video-watch installer for macOS / Linux.
#   curl -fsSL https://raw.githubusercontent.com/vamsireddy4/claude-watch/main/install.sh | sh
# or, from a clone:  sh install.sh
set -e
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "Python 3 is required. Install it from https://www.python.org/downloads/ (or: brew install python) and run this again."
  exit 1
fi
DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo "")"
if [ -n "$DIR" ] && [ -f "$DIR/install.py" ] && [ -f "$DIR/SKILL.md" ]; then
  exec "$PY" "$DIR/install.py" "$@"
fi
curl -fsSL https://raw.githubusercontent.com/vamsireddy4/claude-watch/main/install.py | "$PY" - "$@"
