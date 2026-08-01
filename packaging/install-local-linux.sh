#!/usr/bin/env sh
set -eu
BASE="${XDG_DATA_HOME:-$HOME/.local/share}/ascii-media-player"
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BASE" "$BIN_DIR"
cp "$(dirname "$0")/ascii-media-player" "$BASE/ascii-media-player"
chmod 755 "$BASE/ascii-media-player"
ln -sf "$BASE/ascii-media-player" "$BIN_DIR/ascii-media-player"
printf 'Installed: %s\n' "$BIN_DIR/ascii-media-player"
printf 'Run: ascii-media-player ~/Music\n'
case ":$PATH:" in
  *":$BIN_DIR:"*) : ;;
  *) printf 'Add %s to PATH if the command is not found.\n' "$BIN_DIR" ;;
esac
