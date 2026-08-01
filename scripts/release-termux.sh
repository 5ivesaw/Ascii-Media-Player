#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-$(python3 "$ROOT_DIR/scripts/set-version.py" --print)}"
REPO_URL="${2:-$(git -C "$ROOT_DIR" remote get-url origin 2>/dev/null || echo 'https://github.com/5ivesaw/Ascii-Media-Player.git')}"
python3 "$ROOT_DIR/scripts/set-version.py" "$VERSION" >/dev/null
exec bash "$ROOT_DIR/scripts/publish-termux.sh" "$REPO_URL"
