#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$ROOT/scripts/publish-termux.sh" "${1:-https://github.com/5ivesaw/Ascii-Media-Player.git}"
