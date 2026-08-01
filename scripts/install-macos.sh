#!/usr/bin/env sh
set -eu
REPO="${AMP_REPO:-5ivesaw/Ascii-Media-Player}"
API="https://api.github.com/repos/$REPO/releases/latest"
ARCH_RAW="$(uname -m)"
case "$ARCH_RAW" in
  arm64) LABEL='Apple-Silicon' ;;
  x86_64) LABEL='Intel' ;;
  *) printf 'Unsupported macOS architecture: %s\n' "$ARCH_RAW" >&2; exit 1 ;;
esac
JSON="$(curl -fsSL -H 'Accept: application/vnd.github+json' "$API")"
URL="$(printf '%s\n' "$JSON" | sed -n 's/.*"browser_download_url": "\([^"]*macOS-'"$LABEL"'\.zip\)".*/\1/p' | head -n 1)"
[ -n "$URL" ] || { echo "No macOS $LABEL release asset was found." >&2; exit 1; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT INT TERM
curl -fL "$URL" -o "$TMP/package.zip"
unzip -q "$TMP/package.zip" -d "$TMP/app"
BASE="${HOME}/.local/share/ascii-media-player"
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BASE" "$BIN_DIR"
cp "$TMP/app/ascii-media-player" "$BASE/ascii-media-player"
chmod 755 "$BASE/ascii-media-player"
xattr -dr com.apple.quarantine "$BASE/ascii-media-player" 2>/dev/null || true
ln -sf "$BASE/ascii-media-player" "$BIN_DIR/ascii-media-player"
printf 'Installed: %s\nRun: ascii-media-player ~/Music\n' "$BIN_DIR/ascii-media-player"
