#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "Usage: bash release_new_version.sh 2.2.2"
  exit 1
fi
exec bash "$ROOT/scripts/release-termux.sh" "$VERSION"
