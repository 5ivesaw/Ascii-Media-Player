#!/usr/bin/env sh
set -eu
REPO="${AMP_REPO:-5ivesaw/Ascii-Media-Player}"
API="https://api.github.com/repos/$REPO/releases/latest"
ARCH_RAW="$(uname -m)"
case "$ARCH_RAW" in
  x86_64|amd64) ARCH=x64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) printf 'Unsupported Linux architecture: %s\n' "$ARCH_RAW" >&2; exit 1 ;;
esac
command -v curl >/dev/null 2>&1 || { echo 'curl is required.' >&2; exit 1; }
command -v tar >/dev/null 2>&1 || { echo 'tar is required.' >&2; exit 1; }
JSON="$(curl -fsSL -H 'Accept: application/vnd.github+json' "$API")"
URL="$(printf '%s\n' "$JSON" | sed -n 's/.*"browser_download_url": "\([^"]*Linux-'"$ARCH"'\.tar\.gz\)".*/\1/p' | head -n 1)"
[ -n "$URL" ] || { echo "No Linux $ARCH release asset was found." >&2; exit 1; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT INT TERM
ARCHIVE="$TMP/package.tar.gz"
curl -fL "$URL" -o "$ARCHIVE"
tar -xzf "$ARCHIVE" -C "$TMP"
PACKAGE_DIR="$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[ -n "$PACKAGE_DIR" ] || { echo 'Release archive was empty.' >&2; exit 1; }
sh "$PACKAGE_DIR/install.sh"
