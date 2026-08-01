#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
exec "$DIR/ascii-media-player" "$@"
